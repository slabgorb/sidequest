"""playtest.py — Headless playtest driver for SideQuest.

Runs a YAML scenario against a live sidequest-server. Mints a fresh game via
the REST API, opens a WebSocket, auto-completes character creation, then
drains the scenario's scripted actions one per player turn — printing every
inbound message via :mod:`playtest_messages` for mechanical inspection.

Use this when you need to iterate on mechanics (combat, confrontation,
dice resolution, trope ticks, scenario hooks) without spinning up the React
client and the Playwright harness.

Usage:
    just playtest-scenario smoke_test
    python3 scripts/playtest.py --scenario scenarios/combat_otel.yaml
    python3 scripts/playtest.py --scenario scenarios/combat_otel.yaml --keep

OTEL span-tree capture (Phase E SDK parity gate):
    --span-jsonl PATH dumps every span the run produced (one JSON object
    per line) so the new Anthropic-SDK ``narration.turn`` spans — and
    their ``narration.turn.tool_calls_json`` lie-detector ledger — can be
    eyeballed. Spans are pulled from Jaeger's HTTP query API (default
    http://localhost:16686, override with --jaeger-url), so the server
    MUST be running with OTEL→Jaeger export enabled:

        just jaeger          # stand up Jaeger v2 (gRPC :4317, UI :16686)
        just up-traced       # boot with SIDEQUEST_OTLP_ENDPOINT=localhost:4317
        python3 scripts/playtest.py --scenario scenarios/combat_otel.yaml \\
            --span-jsonl /tmp/combat_otel.spans.jsonl

    This capture path deliberately does NOT reuse scripts/playtest_otlp.py.
    That buffer is the ADR-058 Claude-subprocess HTTP/JSON telemetry
    stream — a *different* telemetry path. The ``narration.turn`` spans
    this gate inspects come from the server's own OTEL tracer, exported
    via gRPC to Jaeger per ADR-103 (the load-bearing ADR for the SDK
    migration). Jaeger is the real, working sink for these spans.

Scenario shape (see ``scenarios/*.yaml``)::

    name: My Test
    genre: mutant_wasteland
    world: flickering_reach
    mode: solo           # or "shared" — default "solo"
    character:
      strategy: auto     # only strategy implemented today
    actions:
      - "look around"
      - "talk to the nearest person"

Exit codes:
    0 — scenario completed (all actions sent + final turn resolved)
    1 — protocol error, server unreachable, chargen got stuck, OR
        --span-jsonl was requested but Jaeger was unreachable / produced
        zero narration.turn spans for the run (fail loud — an empty
        capture means the run wasn't traced; no file is written)
    2 — scenario invalid

A successful scenario whose span capture then fails downgrades the exit
to 1: the scenario "passing" while the parity-gate artifact is missing
is exactly the silent-success this gate exists to prevent.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import websockets
import yaml
from rich.console import Console

# Local helpers — kept as siblings for the existing module split.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playtest_messages import (  # noqa: E402
    make_action_msg,
    make_arrange_assign,
    make_arrange_confirm,
    make_chargen_confirm,
    make_chargen_continue,
    make_chargen_freeform,
    make_chargen_scene_choice,
    make_dice_throw,
    make_slug_connect_msg,
    make_story_autogen,
    make_story_confirm,
    render_message,
)

console = Console()


# ── Scenario loading ────────────────────────────────────────────────────────


class ScenarioError(Exception):
    pass


def load_scenario(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ScenarioError(f"scenario not found: {path}")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ScenarioError(f"scenario {path} must be a mapping")
    # Two shapes survive in the tree: top-level ``genre``/``world`` (smoke_test,
    # combat_otel) and the newer ``pack``/``world`` used by ADR-099 fixtures.
    genre = data.get("genre") or data.get("pack")
    world = data.get("world")
    if not genre or not world:
        raise ScenarioError(f"scenario {path} requires genre/pack + world")
    data["_genre_slug"] = genre
    data["_world_slug"] = world
    data.setdefault("mode", "solo")
    data.setdefault("character", {"strategy": "auto"})
    data.setdefault("actions", [])
    return data


# ── OTEL span-tree capture via Jaeger (Phase E SDK parity gate) ─────────────
#
# These spans (narration.turn + its llm.request / tool.* children) are
# emitted by the SERVER's own OpenTelemetry tracer and gRPC-exported to
# Jaeger (ADR-103). We pull them back out of Jaeger's HTTP query API
# rather than from scripts/playtest_otlp.py — that buffer is the ADR-058
# Claude-subprocess HTTP/JSON stream, a different telemetry path that the
# SDK migration supersedes. See the module docstring.
#
# Service name comes from sidequest-server/sidequest/telemetry/setup.py:
# init_tracer(service_name="sidequest-server"), called unconditionally at
# server/app.py startup.

# OTEL service.name the server registers (telemetry/setup.py default).
JAEGER_SERVICE = "sidequest-server"

# The span we gate on. If zero of these are present for the run after the
# settle window, the run was not traced — fail loud, never an empty file.
NARRATION_TURN_SPAN = "narration.turn"


class SpanCaptureEmpty(RuntimeError):
    """Raised when a --span-jsonl capture would be empty.

    An empty capture is never written silently: it means the run wasn't
    traced (operator forgot ``just up-traced`` / wrong --jaeger-url /
    Jaeger down). Per CLAUDE.md "No Silent Fallbacks" this is surfaced
    loudly and maps to exit code 1.
    """


def flatten_jaeger_tags(tags: list[dict[str, Any]]) -> dict[str, Any]:
    """Flatten a Jaeger span ``tags`` array into a plain dict.

    Jaeger v2's query API emits each tag as ``{key, type, value}`` with
    the value already typed (int64/float64/bool/string). We keep the
    native Python value so ``narration.turn.total_input_tokens`` stays an
    int and ``narration.turn.tool_calls_json`` stays its JSON string
    verbatim (it is double-decoded by the consumer, not here).
    """
    flat: dict[str, Any] = {}
    for tag in tags or []:
        key = tag.get("key")
        if key is None:
            continue
        flat[key] = tag.get("value")
    return flat


def _parent_span_id(span: dict[str, Any]) -> str | None:
    """Return the CHILD_OF parent spanID, or None for a root span."""
    for ref in span.get("references") or []:
        if ref.get("refType") == "CHILD_OF" and ref.get("spanID"):
            return ref["spanID"]
    return None


def jaeger_span_to_record(span: dict[str, Any]) -> dict[str, Any]:
    """Convert one Jaeger query-API span into a JSONL record.

    Preserves name, span/trace/parent ids, start (μs since epoch) and
    duration (μs), plus the full flattened attribute dict — so a
    ``narration.turn`` record carries ``narration.turn.tool_calls_json``,
    ``.model_chosen``, the token rollups and ``.tool_call_count``.
    """
    return {
        "name": span.get("operationName", ""),
        "span_id": span.get("spanID", ""),
        "trace_id": span.get("traceID", ""),
        "parent_span_id": _parent_span_id(span),
        "start_us": int(span.get("startTime", 0)),
        "duration_us": int(span.get("duration", 0)),
        "attributes": flatten_jaeger_tags(span.get("tags") or []),
    }


def traces_to_jsonl_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a Jaeger ``/api/traces`` payload to a flat span-record list.

    Jaeger groups spans under traces (``payload["data"][].spans[]``); the
    JSONL is one object per span across every trace in the payload, so the
    parent/child tree is reconstructable downstream from
    ``span_id``/``parent_span_id``.
    """
    records: list[dict[str, Any]] = []
    for trace in payload.get("data") or []:
        for span in trace.get("spans") or []:
            records.append(jaeger_span_to_record(span))
    return records


def write_span_jsonl(records: list[dict[str, Any]], path: Path) -> int:
    """Write span records to ``path`` as JSONL. Returns the count written.

    Refuses to write an empty file: zero records means the run wasn't
    traced and a 0-byte success artifact would silently pass the parity
    gate. Raises :class:`SpanCaptureEmpty` instead (no file touched).
    """
    if not records:
        raise SpanCaptureEmpty(
            "refusing to write an empty span JSONL — zero spans captured"
        )
    lines = "\n".join(json.dumps(rec, sort_keys=True) for rec in records)
    path.write_text(lines + "\n")
    return len(records)


async def _query_jaeger_traces(
    jaeger_url: str,
    *,
    service: str,
    start_us: int,
    end_us: int,
    limit: int = 200,
) -> dict[str, Any]:
    """GET Jaeger's /api/traces scoped to one service + wall-clock window.

    Jaeger's classic query API (Jaeger v2 keeps it UI-compatible) takes
    ``start``/``end`` in microseconds since epoch. Scoping by both the
    service name AND the run's time window keeps stale traces from
    previous runs out of the capture.
    """
    params = {
        "service": service,
        "start": str(start_us),
        "end": str(end_us),
        "limit": str(limit),
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{jaeger_url.rstrip('/')}/api/traces", params=params)
        resp.raise_for_status()
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            # A reverse proxy / wrong --jaeger-url can answer HTTP 200 with
            # an HTML error page. That is NOT an httpx.HTTPError, so a raw
            # JSONDecodeError would escape amain's handler as a traceback.
            # Re-raise as httpx.HTTPError so the existing fail-loud path
            # (clean "[span-jsonl] Jaeger query failed" + exit 1, no file)
            # handles it identically to an unreachable Jaeger — no silent
            # fallback.
            raise httpx.HTTPError(
                f"Jaeger returned non-JSON from {resp.request.url} "
                f"(HTTP {resp.status_code}, content-type "
                f"{resp.headers.get('content-type', '?')!r}): {exc}"
            ) from exc


async def capture_run_spans(
    jaeger_url: str,
    *,
    run_start_us: int,
    run_end_us: int,
    settle_attempts: int = 8,
    settle_interval: float = 1.5,
) -> list[dict[str, Any]]:
    """Poll Jaeger until this run's narration.turn spans land, then return all.

    The server's gRPC OTLP exporter batches with a ~2 s schedule delay
    (telemetry/setup.py: schedule_delay_millis=2000), so a single query
    fired the instant the scenario ends races the export. We poll with a
    bounded settle (default ~12 s total) until at least one
    ``narration.turn`` span for the window appears, then return every span
    in the window so children (llm.request / tool.*) ride along.

    Raises :class:`SpanCaptureEmpty` if no narration.turn span ever
    appears, and lets ``httpx`` errors propagate (Jaeger unreachable is a
    loud failure, not a silent empty capture).
    """
    last_records: list[dict[str, Any]] = []
    for attempt in range(1, settle_attempts + 1):
        # Re-read the window end each poll so spans that close *after* the
        # scenario loop exits (trailing narration flush) are still caught.
        # max() guards a backward wall-clock step (NTP slew); _now_us()
        # normally wins so run_end_us is the floor, not the typical value.
        payload = await _query_jaeger_traces(
            jaeger_url,
            service=JAEGER_SERVICE,
            start_us=run_start_us,
            end_us=max(run_end_us, _now_us()),
        )
        last_records = traces_to_jsonl_records(payload)
        has_turn = any(r["name"] == NARRATION_TURN_SPAN for r in last_records)
        if has_turn:
            console.print(
                f"[dim][span-jsonl] {len(last_records)} spans "
                f"({sum(1 for r in last_records if r['name'] == NARRATION_TURN_SPAN)} "
                f"narration.turn) after {attempt} poll(s)[/dim]"
            )
            return last_records
        if attempt < settle_attempts:
            await asyncio.sleep(settle_interval)

    raise SpanCaptureEmpty(
        f"no {NARRATION_TURN_SPAN!r} spans found in Jaeger ({jaeger_url}) "
        f"for service {JAEGER_SERVICE!r} in the run window after "
        f"{settle_attempts} polls (~{settle_attempts * settle_interval:.0f}s). "
        f"Saw {len(last_records)} other span(s). The run was not traced — "
        f"start Jaeger ('just jaeger') and the server with OTEL export "
        f"('just up-traced', SIDEQUEST_OTLP_ENDPOINT=localhost:4317)."
    )


def _now_us() -> int:
    """Wall-clock microseconds since epoch (Jaeger query time unit)."""
    return int(time.time() * 1_000_000)


# ── REST: mint a game slug ──────────────────────────────────────────────────


async def _post_for_slug(
    url: str,
    *,
    json: dict[str, Any] | None = None,
    not_found_hint: str | None = None,
) -> str:
    """POST to ``url`` and extract a ``slug`` from the JSON response.

    Shared helper for :func:`mint_game_slug` (POST /api/games) and
    :func:`mint_via_scene_harness` (POST /dev/scene/{name}). When
    ``not_found_hint`` is provided, a 404 response raises with that
    hint instead of falling through ``raise_for_status`` — the dev-only
    /dev/scene route returns 404 when DEV_SCENES is unset and the hint
    points the operator at the missing env var.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=json)
        if not_found_hint is not None and resp.status_code == 404:
            raise RuntimeError(f"POST {url} returned 404 — {not_found_hint}. Body: {resp.text}")
        resp.raise_for_status()
        body = resp.json()
    slug = body.get("slug")
    if not slug:
        raise RuntimeError(f"POST {url} returned no slug: {body}")
    return slug


async def mint_game_slug(
    rest_base: str,
    genre_slug: str,
    world_slug: str,
    mode: str,
    player_name: str,
    force_new: bool,
) -> str:
    return await _post_for_slug(
        f"{rest_base}/api/games",
        json={
            "genre_slug": genre_slug,
            "world_slug": world_slug,
            "mode": mode,
            "player_name": player_name,
            "force_new": force_new,
        },
    )


async def mint_via_scene_harness(rest_base: str, fixture_name: str) -> str:
    """POST /dev/scene/{name} and return the slug the server minted.

    Counterpart to :func:`mint_game_slug` for ADR-092's scene-harness flow.
    Requires the server to be running with ``DEV_SCENES=1``; absent that,
    the route 404s and we raise loudly so the dev fixes their environment.
    """
    return await _post_for_slug(
        f"{rest_base}/dev/scene/{fixture_name}",
        not_found_hint=(
            "check that the server is running with DEV_SCENES=1 and "
            f"the fixture exists at scenarios/fixtures/{fixture_name}.yaml"
        ),
    )


# ── Auto chargen strategy ───────────────────────────────────────────────────


class AutoChargen:
    """Greedy auto-strategy for CHARACTER_CREATION messages.

    - ``input_type=select`` / standard scene → pick choice 1
    - ``input_type=text`` (freeform) → submit "1" as the default
    - ``input_type=stat_arrange`` → assign pool to slots in order, then confirm
    - ``input_type=story`` → run autogen, wait for autogen_result, then confirm
    - ``phase=confirmation`` → accept
    - ``phase=complete`` → mark done
    """

    def __init__(self) -> None:
        self.done: bool = False
        self._pending_story_confirm: bool = False
        # Cache pronouns when the_story arrives so the eventual story_confirm
        # carries something other than the empty string.
        self._story_pronouns: str = "they/them"

    def respond(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Return zero or more outbound messages for one CHARACTER_CREATION payload."""
        phase = payload.get("phase") or ""
        if phase == "complete" or payload.get("character"):
            self.done = True
            return []
        if phase == "confirmation":
            return [make_chargen_confirm()]
        if phase != "scene":
            # Unknown phase — log and continue without sending anything; the
            # server will either time out or re-send.
            return []

        input_type = (payload.get("input_type") or "select").lower()

        if input_type == "stat_arrange":
            return self._respond_arrange(payload)

        if input_type == "story":
            return self._respond_story(payload)

        choices = payload.get("choices") or []
        if choices:
            # Pick the first available option (1-based).
            return [make_chargen_scene_choice(1)]

        if payload.get("allows_freeform") or input_type == "text":
            # Freeform-only scene with no choices. Submit a benign default —
            # most freeform chargen prompts (player name) accept any string.
            return [make_chargen_freeform("Pilot")]

        # Scene with no actionable fields. Try a continue to nudge.
        return [make_chargen_continue()]

    def _respond_arrange(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        pool: list[int] = list(payload.get("pool") or [])
        assignment: dict[str, int | None] = dict(payload.get("assignment") or {})

        # Find the first unassigned slot.
        unfilled = [stat for stat, v in assignment.items() if v is None]
        if not unfilled or not pool:
            # All slots filled (or empty pool — shouldn't happen). Confirm.
            return [make_arrange_confirm()] if payload.get("confirm_enabled") else []

        # Assign the highest remaining pool value to the first unfilled slot.
        # This is "greedy and dumb" — fine for getting through chargen, not
        # for class-optimization. The qualifying_classes panel will sort itself
        # out as we fill in.
        value = max(pool)
        stat = unfilled[0]
        return [make_arrange_assign(stat, value)]

    def _respond_story(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        autogen_result = payload.get("autogen_result")
        if autogen_result:
            # Server has finished filling in background/description for us.
            background = (autogen_result.get("background") or "").strip() or "Drifter."
            description = (autogen_result.get("description") or "").strip() or "Travel-worn."
            self._pending_story_confirm = False
            return [make_story_confirm(self._story_pronouns, background, description)]

        if not self._pending_story_confirm and payload.get("autogen_available"):
            self._pending_story_confirm = True
            return [make_story_autogen()]

        # Either autogen isn't available or we've already requested it and
        # the result hasn't landed yet. If autogen isn't available, submit
        # benign placeholders so the scene resolves.
        if not payload.get("autogen_available"):
            return [
                make_story_confirm(
                    self._story_pronouns,
                    "A drifter with calloused hands and not much to say.",
                    "Lean build, weathered jacket, eyes that have seen things.",
                )
            ]

        # Waiting for autogen_result — do nothing this tick.
        return []


# ── Dice auto-throw ─────────────────────────────────────────────────────────


def auto_dice_faces(dice_request: dict[str, Any], *, rng: random.Random) -> list[int]:
    """Roll random faces for each die in the requested pool.

    Headless playtest doesn't run the 3D physics overlay — we synthesize a
    fair roll. Each ``DieSpec`` carries ``count`` and ``sides``.
    """
    faces: list[int] = []
    for spec in dice_request.get("dice") or []:
        count = int(spec.get("count", 1))
        sides = int(spec.get("sides", 6))
        for _ in range(count):
            faces.append(rng.randint(1, sides))
    return faces


# ── Main driver ─────────────────────────────────────────────────────────────


class Playtest:
    def __init__(
        self,
        scenario: dict[str, Any],
        *,
        server: str,
        rest_base: str,
        player_name: str,
        force_new: bool,
        idle_timeout: float,
        seed: int,
        fixture: str | None = None,
    ) -> None:
        self.scenario = scenario
        self.server = server
        self.rest_base = rest_base
        self.player_name = player_name
        self.force_new = force_new
        self.idle_timeout = idle_timeout
        self.rng = random.Random(seed)
        # When set, the driver mints the slug via POST /dev/scene/{fixture}
        # (ADR-092 scene harness) and skips chargen — the fixture YAML
        # has already hydrated a character into the save.
        self.fixture: str | None = fixture

        self.slug: str = ""
        self.actions: list[str] = list(scenario.get("actions") or [])
        self.actions_sent: int = 0
        self.chargen = AutoChargen()
        # Fixture mode: the save already has a character; the slug-connect
        # handshake will report has_character=True and AutoChargen never
        # runs. Mark done at construction so the idle-timeout fallback
        # doesn't think we're stuck mid-chargen.
        self.chargen_done: bool = fixture is not None
        self.session_ready: bool = False
        # Server's view of who *we* are. The connect handler assigns a UUID
        # if the client didn't send one; we get it back in TURN_STATUS as
        # ``player_name`` (display name, not UUID), which matches what we
        # POSTed to /api/games.
        self.my_turn: bool = False
        self.last_inbound_msg_type: str = ""

    async def run(self) -> int:
        console.rule(f"[bold green]Playtest: {self.scenario.get('name', '?')}[/bold green]")
        console.print(
            f"[dim]genre={self.scenario['_genre_slug']} world={self.scenario['_world_slug']} "
            f"mode={self.scenario['mode']} actions={len(self.actions)}[/dim]"
        )

        try:
            if self.fixture is not None:
                self.slug = await mint_via_scene_harness(self.rest_base, self.fixture)
                console.print(
                    f"[green]Scene-harness loaded {self.fixture} → slug:[/green] {self.slug}"
                )
            else:
                self.slug = await mint_game_slug(
                    self.rest_base,
                    self.scenario["_genre_slug"],
                    self.scenario["_world_slug"],
                    self.scenario["mode"],
                    self.player_name,
                    self.force_new,
                )
                console.print(f"[green]Minted game slug:[/green] {self.slug}")
        except httpx.HTTPError as exc:
            console.print(f"[bold red]REST error: {exc}[/bold red]")
            return 1

        try:
            async with websockets.connect(self.server, max_size=8 * 1024 * 1024) as ws:
                return await self._loop(ws)
        except (OSError, websockets.exceptions.WebSocketException) as exc:
            console.print(f"[bold red]WebSocket error: {exc}[/bold red]")
            return 1

    async def _send(self, ws: Any, msg: dict[str, Any]) -> None:
        await ws.send(json.dumps(msg))
        # Mirror outbound so the trace is symmetric.
        render_message(msg)

    async def _loop(self, ws: Any) -> int:
        # Send the slug-connect handshake first.
        await self._send(ws, make_slug_connect_msg(self.slug, self.player_name))

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=self.idle_timeout)
            except asyncio.TimeoutError:
                # Idle. If we're past chargen and still have actions to
                # send, push the next one — the turn-status signal may have
                # been lost or the game is waiting on us in a way we can't
                # detect from message traffic alone.
                if self.session_ready and self.actions:
                    console.print("[yellow][idle] nudging next action[/yellow]")
                    await self._send_next_action(ws)
                    continue
                if self.session_ready and not self.actions:
                    console.rule("[bold green]Scenario complete[/bold green]")
                    return 0
                console.print(
                    f"[bold red]Idle timeout while waiting for "
                    f"{self.last_inbound_msg_type or 'first message'} — giving up[/bold red]"
                )
                return 1
            except websockets.exceptions.ConnectionClosed:
                console.print("[yellow]Server closed the connection[/yellow]")
                return 0 if not self.actions else 1

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                console.print(f"[red]non-JSON frame: {raw!r}[/red]")
                continue

            msg_type = msg.get("type", "UNKNOWN")
            self.last_inbound_msg_type = msg_type
            render_message(msg)

            await self._react(ws, msg)

            # Hard stop: scenario exhausted and no further turn activity is
            # pending. We give the server one idle window after the last
            # action to flush trailing NARRATION/IMAGE/AUDIO_CUE traffic.
            if (
                self.session_ready
                and not self.actions
                and msg_type == "TURN_STATUS"
                and (msg.get("payload") or {}).get("status") == "resolved"
            ):
                console.rule("[bold green]Scenario complete[/bold green]")
                return 0

    async def _react(self, ws: Any, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type", "")
        payload = msg.get("payload") or {}

        if msg_type == "SESSION_EVENT":
            event = payload.get("event")
            if event == "connected":
                # If the player already has a character, chargen is skipped.
                if payload.get("has_character"):
                    self.chargen_done = True
            elif event == "ready":
                self.session_ready = True
                # Kick off the action drain by sending the first action.
                await self._send_next_action(ws)
            return

        if msg_type == "CHARACTER_CREATION":
            outbound = self.chargen.respond(payload)
            for out in outbound:
                await self._send(ws, out)
            if self.chargen.done and not self.chargen_done:
                self.chargen_done = True
                # Fresh chargen never emits SESSION_EVENT{ready} — only the
                # resume path does (handlers/connect.py line 977-993). Use
                # chargen completion as the equivalent "playing now" signal.
                self.session_ready = True
                # Don't preemptively fire an action; wait for the first
                # TURN_STATUS{me, active} or the idle nudge to push it.
            return

        if msg_type == "TURN_STATUS":
            who = payload.get("player_name", "")
            status = payload.get("status", "")
            if who == self.player_name:
                if status == "active" and self.session_ready:
                    await self._send_next_action(ws)
                self.my_turn = status == "active"
            return

        if msg_type == "NARRATION_END" and self.session_ready and self.actions:
            # Canonical narration finished — the server is now awaiting the
            # next player input (there's no explicit "your turn" signal in
            # solo flow). Send the next scripted action.
            await self._send_next_action(ws)
            return

        if msg_type == "DICE_REQUEST":
            # Only respond if we're the rolling player. Server includes
            # rolling_player_id (UUID) — but we don't always have ours
            # cached. Throw whenever the request arrives; the server's
            # request_id keying makes duplicate throws idempotent (last
            # one wins or error out — both are loud).
            faces = auto_dice_faces(payload, rng=self.rng)
            await self._send(ws, make_dice_throw(payload.get("request_id", ""), faces))
            return

        # Most other messages are informational — already rendered above.

    async def _send_next_action(self, ws: Any) -> None:
        if not self.actions:
            return
        action = self.actions.pop(0)
        self.actions_sent += 1
        # Slash-commands (/status, /inventory, etc.) ride the same channel
        # as freeform narration.
        await self._send(ws, make_action_msg(action))


# ── CLI ─────────────────────────────────────────────────────────────────────


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="playtest",
        description="Headless playtest driver for SideQuest.",
    )
    # One of --scenario or --fixture is required, but never both. Scenario
    # mode drives a scripted action sequence; fixture mode (ADR-092)
    # POSTs /dev/scene/{name} to land directly in a pre-hydrated scene
    # and exercises whatever the scenario then sends.
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--scenario",
        type=Path,
        help="Path to a scenario YAML file (e.g. scenarios/smoke_test.yaml).",
    )
    source.add_argument(
        "--fixture",
        type=str,
        help=(
            "ADR-092 scene-harness fixture name (e.g. combat_test). POSTs "
            "/dev/scene/{name} to the running server (requires DEV_SCENES=1) "
            "to skip chargen and land directly in a hydrated scene. "
            "Mutually exclusive with --scenario."
        ),
    )
    parser.add_argument(
        "--server",
        default="ws://localhost:8765/ws",
        help="WebSocket URL of the running sidequest-server (default: %(default)s).",
    )
    parser.add_argument(
        "--rest",
        default="http://localhost:8765",
        help="REST base URL of the running sidequest-server (default: %(default)s).",
    )
    parser.add_argument(
        "--player-name",
        default="Playtest",
        help="Display name used for the player (default: %(default)s).",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Do not pass force_new=true when minting the game — resume an existing slug if one matches.",
    )
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=60.0,
        help="Seconds with no inbound message before nudging/giving up (default: %(default)s).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="RNG seed for auto-dice faces (default: 0).",
    )
    # Phase E SDK parity gate. Purely additive — absent, behaviour and
    # exit codes are byte-for-byte unchanged. Requires the server to be
    # running with OTEL→Jaeger export (`just up-traced`); see the module
    # docstring. Does NOT reuse playtest_otlp.py (ADR-058 vs ADR-103).
    parser.add_argument(
        "--span-jsonl",
        type=Path,
        default=None,
        help=(
            "After the scenario completes, dump every OTEL span the run "
            "produced (one JSON object per line) to this path by querying "
            "Jaeger. Captures the SDK narration.turn spans + tool_calls_json "
            "ledger. Fails loud (exit 1, no file) if Jaeger is unreachable "
            "or zero narration.turn spans are found for the run."
        ),
    )
    parser.add_argument(
        "--jaeger-url",
        default="http://localhost:16686",
        help=(
            "Jaeger HTTP query API base URL for --span-jsonl "
            "(default: %(default)s)."
        ),
    )
    return parser.parse_args(argv)


async def amain(args: argparse.Namespace) -> int:
    if args.fixture is not None:
        # Fixture mode (ADR-092): no scenario YAML needed. Synthesize a
        # minimal scenario shape so the existing driver loop has the
        # fields it reads (mode, actions). The genre/world slugs come
        # from the hydrated save on the server side — not used by the
        # client driver in fixture mode.
        scenario: dict[str, Any] = {
            "name": f"fixture:{args.fixture}",
            "_genre_slug": "",
            "_world_slug": "",
            "mode": "solo",
            "actions": [],
        }
    else:
        try:
            scenario = load_scenario(args.scenario)
        except ScenarioError as exc:
            console.print(f"[bold red]Scenario error: {exc}[/bold red]")
            return 2

    pt = Playtest(
        scenario,
        server=args.server,
        rest_base=args.rest,
        player_name=args.player_name,
        force_new=not args.keep,
        idle_timeout=args.idle_timeout,
        seed=args.seed,
        fixture=args.fixture,
    )

    # No-flag path: behaviour, output and exit code byte-for-byte
    # unchanged — capture is strictly additive.
    if args.span_jsonl is None:
        return await pt.run()

    # Mark the run window *before* the scenario starts so the Jaeger
    # query can scope to this run's spans only.
    run_start_us = _now_us()
    rc = await pt.run()
    run_end_us = _now_us()

    # A failed scenario (server unreachable, protocol error, stuck
    # chargen) typically produced zero narration.turn spans. Entering the
    # ~12s Jaeger settle here would raise SpanCaptureEmpty whose message
    # tells the operator "the run was not traced — start Jaeger" — that
    # misdiagnoses the real root cause (the scenario/server failure) and
    # wastes the settle window. A failed run's span artifact is
    # meaningless anyway: short-circuit and preserve the true signal.
    # (Successful-scenario fail-loud-on-empty stays exactly as spec'd
    # below — that is the gate this whole feature exists for.)
    if rc != 0:
        msg = f"scenario failed (rc={rc}); skipping span capture"
        console.print(f"[bold yellow][span-jsonl] {msg}[/bold yellow]")
        print(f"span-jsonl: {msg}", file=sys.stderr)
        return rc

    try:
        records = await capture_run_spans(
            args.jaeger_url,
            run_start_us=run_start_us,
            run_end_us=run_end_us,
        )
        written = write_span_jsonl(records, args.span_jsonl)
    except SpanCaptureEmpty as exc:
        console.print(f"[bold red][span-jsonl] {exc}[/bold red]")
        print(f"span-jsonl capture failed (empty): {exc}", file=sys.stderr)
        # A "passing" scenario with no parity artifact is the silent
        # success this gate exists to prevent — downgrade to 1.
        return 1
    except httpx.HTTPError as exc:
        console.print(
            f"[bold red][span-jsonl] Jaeger query failed "
            f"({args.jaeger_url}): {exc}[/bold red]"
        )
        print(
            f"span-jsonl capture failed (Jaeger unreachable at "
            f"{args.jaeger_url}): {exc}",
            file=sys.stderr,
        )
        return 1

    console.print(
        f"[green][span-jsonl] wrote {written} span(s) → "
        f"{args.span_jsonl}[/green]"
    )
    # Preserve the scenario's own non-zero exit (protocol error etc.); a
    # successful capture never *upgrades* a failed scenario to 0.
    return rc


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    with contextlib.suppress(KeyboardInterrupt):
        return asyncio.run(amain(args))
    return 130


if __name__ == "__main__":
    sys.exit(main())
