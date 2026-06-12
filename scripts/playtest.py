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
    python3 scripts/playtest.py --scenario scenarios/combat_otel.yaml          # reuses same-day session (warm cache)
    python3 scripts/playtest.py --scenario scenarios/combat_otel.yaml --fresh  # cache-bust: new COLD session, re-bills prefix

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
import math
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
    make_chargen_portrait_confirm,
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

    When ``class_pref`` is set (scenario ``character.class``), a scene whose
    choices include a label matching it (e.g. "Mage", "Cleric") picks that
    choice instead of choice 1 — so validation scenarios can pin a caster for
    the magic leg. Non-class scenes are unaffected (no label matches).
    """

    def __init__(self, class_pref: str | None = None) -> None:
        self.done: bool = False
        self._pending_story_confirm: bool = False
        # Cache pronouns when the_story arrives so the eventual story_confirm
        # carries something other than the empty string.
        self._story_pronouns: str = "they/them"
        self.class_pref: str | None = (class_pref or "").strip().lower() or None

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

        if input_type == "pick_portrait":
            # Epic-66 portrait picker, interposed once at the Confirmation
            # boundary. The driver always skips (portraits are cosmetic). Answer
            # with phase=portrait_confirm so the server clears the
            # portrait_step_shown gate — a generic continue/scene-choice does
            # not, leaving chargen stalled until the next action trips
            # WrongPhaseError.
            return [make_chargen_portrait_confirm()]

        choices = payload.get("choices") or []
        if choices:
            return [make_chargen_scene_choice(self._preferred_choice(choices))]

        if payload.get("allows_freeform") or input_type == "text":
            # Freeform-only scene with no choices. Submit a benign default —
            # most freeform chargen prompts (player name) accept any string.
            return [make_chargen_freeform("Pilot")]

        # Scene with no actionable fields. Try a continue to nudge.
        return [make_chargen_continue()]

    def _preferred_choice(self, choices: list[Any]) -> int:
        """1-based index of the choice to pick. Defaults to 1, but when
        ``class_pref`` matches a choice label (the class-selection scene),
        returns that choice so a caster can be pinned for the magic leg."""
        if self.class_pref:
            for i, c in enumerate(choices):
                label = (c.get("label", "") if isinstance(c, dict) else str(c)).strip().lower()
                if label == self.class_pref:
                    return i + 1
        return 1

    def _respond_arrange(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        pool: list[int] = list(payload.get("pool") or [])
        assignment: dict[str, int | None] = dict(payload.get("assignment") or {})

        # Find the first unassigned slot.
        unfilled = [stat for stat, v in assignment.items() if v is None]
        if not unfilled or not pool:
            # All slots filled (or empty pool — shouldn't happen). Confirm.
            return [make_arrange_confirm()] if payload.get("confirm_enabled") else []

        # Assign the highest remaining pool value to the best unfilled slot.
        # With no class_pref this is "greedy and dumb" (first unfilled in dict
        # order — STR-first). With a class_pref, route the high rolls to that
        # class's key stat so the class actually QUALIFIES and is offered on
        # the next scene — otherwise a caster (high INT/WIS) never appears on
        # the menu and the magic leg can't be exercised.
        value = max(pool)
        stat = self._arrange_stat(unfilled)
        return [make_arrange_assign(stat, value)]

    # Stat priority per caverns_and_claudes class — highest pool rolls flow to
    # the front of the list. Keyed by lowercased class label (matches
    # class_pref). Classes absent here fall back to dict-order (STR-first).
    _CLASS_STAT_PRIORITY: dict[str, list[str]] = {
        "mage": ["INT", "CON", "DEX", "WIS", "STR", "CHA"],
        "cleric": ["WIS", "CON", "STR", "INT", "DEX", "CHA"],
        "fighter": ["STR", "CON", "DEX", "WIS", "INT", "CHA"],
        "thief": ["DEX", "CON", "INT", "STR", "WIS", "CHA"],
    }

    def _arrange_stat(self, unfilled: list[str]) -> str:
        """Pick which unfilled stat slot to fill next. Honors the class_pref
        stat priority so a requested caster qualifies; otherwise first-unfilled."""
        priority = self._CLASS_STAT_PRIORITY.get(self.class_pref or "")
        if priority:
            for stat in priority:
                if stat in unfilled:
                    return stat
        return unfilled[0]

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
        collect_renders: bool = True,
        render_drain_timeout: float = 120.0,
    ) -> None:
        self.scenario = scenario
        self.server = server
        self.rest_base = rest_base
        self.player_name = player_name
        self.force_new = force_new
        self.idle_timeout = idle_timeout
        self.rng = random.Random(seed)
        # Daemon image renders complete asynchronously, well after the final
        # turn resolves — so the driver drains pending renders (tracked by
        # render_id from RENDER_QUEUED, cleared on the matching IMAGE) before
        # disconnecting, up to render_drain_timeout, so the end-of-run contact
        # sheet captures them instead of racing the disconnect.
        self.collect_renders = collect_renders
        self.render_drain_timeout = render_drain_timeout
        self.pending_renders: set[str] = set()
        # One-action-per-resolved-turn gate. Set True when an action is
        # submitted, cleared on the turn's NARRATION_END (the canonical
        # "turn done, send next" signal in solo). Without this, the server's
        # TURN_STATUS{active} for an in-flight turn would trigger a premature
        # next-action send — actions outran turn resolution and validation
        # runs under-captured turns (only 2 of 4 actions producing spans).
        self.turn_in_flight: bool = False
        # When set, the driver mints the slug via POST /dev/scene/{fixture}
        # (ADR-092 scene harness) and skips chargen — the fixture YAML
        # has already hydrated a character into the save.
        self.fixture: str | None = fixture

        self.slug: str = ""
        self.actions: list[str] = list(scenario.get("actions") or [])
        self.actions_sent: int = 0
        self.chargen = AutoChargen(
            class_pref=(scenario.get("character") or {}).get("class")
        )
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
        # Best-known round, latched from any inbound payload that carries one
        # (server stamps round on broadcasts). PLAYER_ACTION requires round
        # (ge=0, Story 71-10); the server validates but doesn't read it.
        self.current_round: int = 0
        # Rendered images this run produced (IMAGE messages). Even headless
        # runs queue daemon renders; collecting them lets the driver assemble
        # an end-of-run contact sheet so the visual output is reviewable
        # without a UI. Each entry: {url, caption, tier, render_id}.
        self.images: list[dict[str, str]] = []

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
            except TimeoutError:
                # Idle. If we're past chargen and still have actions to
                # send, push the next one — the turn-status signal may have
                # been lost or the game is waiting on us in a way we can't
                # detect from message traffic alone.
                if self.session_ready and self.actions:
                    console.print("[yellow][idle] nudging next action[/yellow]")
                    # Force past the in-flight gate: an idle window means the
                    # turn's NARRATION_END was lost or the server is silently
                    # waiting on us.
                    await self._send_next_action(ws, force=True)
                    continue
                if self.session_ready and not self.actions:
                    console.rule("[bold green]Scenario complete[/bold green]")
                    await self._drain_renders(ws)
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
                await self._drain_renders(ws)
                return 0

    async def _react(self, ws: Any, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type", "")
        payload = msg.get("payload") or {}

        # Latch the authoritative round whenever a message carries one, so the
        # next PLAYER_ACTION stamps a current value (default 0 pre-first-turn).
        _r = payload.get("round")
        if isinstance(_r, int) and _r >= self.current_round:
            self.current_round = _r

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
            # Canonical narration finished — the turn is done and the server is
            # awaiting the next player input (there's no explicit "your turn"
            # signal in solo flow). Clear the in-flight gate, then send the
            # next scripted action. This is the ONE place the gate clears, so
            # exactly one action goes out per resolved turn.
            self.turn_in_flight = False
            await self._send_next_action(ws)
            return

        if msg_type == "RENDER_QUEUED":
            # The render is in flight on the daemon; remember it so the drain
            # phase waits for the matching IMAGE before disconnecting.
            rid = payload.get("render_id") or ""
            if rid and self.collect_renders:
                self.pending_renders.add(rid)
            return

        if msg_type == "IMAGE":
            # ImagePayload.url (served by the server's /renders/* mount or an
            # absolute R2 URL). Collected for the end-of-run contact sheet.
            rid = payload.get("render_id") or ""
            self.pending_renders.discard(rid)
            url = payload.get("url") or ""
            if url:
                self.images.append(
                    {
                        "url": url,
                        "caption": payload.get("caption")
                        or payload.get("alt")
                        or "",
                        "tier": payload.get("tier") or "",
                        "render_id": rid,
                    }
                )
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

    async def _send_next_action(self, ws: Any, *, force: bool = False) -> None:
        if not self.actions:
            return
        # One action per resolved turn: if a submitted action's turn hasn't
        # finished (no NARRATION_END yet), don't pile another on. ``force``
        # (the idle nudge) overrides — a stalled turn that never emits
        # NARRATION_END must still make progress.
        if self.turn_in_flight and not force:
            return
        self.turn_in_flight = True
        action = self.actions.pop(0)
        self.actions_sent += 1
        # Slash-commands (/status, /inventory, etc.) ride the same channel
        # as freeform narration.
        await self._send(ws, make_action_msg(action, round_=self.current_round))

    async def _drain_renders(self, ws: Any) -> None:
        """After the scenario completes, wait (bounded) for in-flight daemon
        renders to arrive as IMAGE messages so the end-of-run contact sheet
        captures them. Daemon image generation runs well behind the turn that
        queued it, so without this drain the driver disconnects first and the
        renders are lost."""
        if not self.collect_renders or not self.pending_renders:
            return
        n0 = len(self.pending_renders)
        console.print(
            f"[cyan][render-drain] waiting for {n0} pending render(s) "
            f"(≤{self.render_drain_timeout:.0f}s)…[/cyan]"
        )
        deadline = time.monotonic() + self.render_drain_timeout
        while self.pending_renders and time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 15.0))
            except TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                console.print("[yellow][render-drain] connection closed early[/yellow]")
                break
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            render_message(msg)
            await self._react(ws, msg)
        drained = n0 - len(self.pending_renders)
        if self.pending_renders:
            console.print(
                f"[yellow][render-drain] {drained}/{n0} render(s) landed; "
                f"{len(self.pending_renders)} still pending at timeout "
                f"(abandoned)[/yellow]"
            )
        else:
            console.print(f"[green][render-drain] all {n0} render(s) landed[/green]")


# ── CLI ─────────────────────────────────────────────────────────────────────


# ── Story 61-4 — Preflight cost guard ───────────────────────────────────────
#
# Defense against the 2026-05-23 $313 runaway. ``preflight_cost_check``
# runs BEFORE any scenario action fires, prints a cache-aware projection
# and refuses to proceed past ``--max-projected-cost-usd`` (default $0.50
# ≈ 16x the per-turn target) unless ``--confirm-cost`` is supplied. The
# May 23 incident happened because nothing was ever printed; loud is the
# point.
#
# Architect spec-check D (2026-05-23): the original worst-case math
# (``N × 12_000 × 4 × $3/MTok = N × $0.144``) crossed $0.50 at N≥4 actions
# — every real scenario except 1-3-action fixtures was refused by default.
# Operators would alias ``--confirm-cost=$true`` within a day and the cap
# would go silent — exactly the failure this story exists to prevent.
# Cache-aware math (ADR-101: action 1 pays full input, actions 2+ ride
# cache-read at $0.30/MTok) makes a 50-action scenario project ~$0.83
# instead of $7.20 — preserves the cap as a real signal for runaway-shaped
# scenarios while not false-positiving healthy multi-action playtests.
#
# Architect spec-check E (2026-05-23): the SDK-replay sidecar writer
# (``write_meta_sidecar``) was cut — no producer of ``/tmp/real_req_*.json``
# exists in tree today and no near-term consumer in the epic context, so
# the writer was a textbook CLAUDE.md "No Stubbing" violation. The
# capture path is its own story; re-implement the sidecar writer when the
# SDK-replay capture path lands.

# Conservative defaults for the preflight worst-case projection. Hard-coded
# rather than imported from sidequest_server.agents.anthropic_cost so this
# script stays runnable without the server venv (matches the rest of
# playtest.py's "no server imports" stance — scenarios load standalone).
_PREFLIGHT_INPUT_TOKENS_PER_ACTION = 12_000
_PREFLIGHT_OUTPUT_TOKENS_PER_ACTION = 200
_PREFLIGHT_ITERS_ASSUMED = 4
_SONNET_INPUT_PER_MTOK_USD = 3.0
_SONNET_OUTPUT_PER_MTOK_USD = 15.0
_SONNET_CACHED_READ_PER_MTOK_USD = 0.30


def _project_preflight_cost_usd(n_actions: int) -> float:
    """Cache-aware projection for ``n_actions`` scenario actions.

    Per ADR-101's four-region cache layout: action 1 pays the full Sonnet
    input rate ($3/MTok); actions 2+ ride the cache-read rate
    ($0.30/MTok) for the bulk of the prompt prefix (system + tools +
    stable session blocks). Output is billed at the full rate every iter.

    Math, per action × ``_PREFLIGHT_ITERS_ASSUMED`` (4) tool-loop iters:
    - Action 1: ``12_000 × 4 × $3/MTok + 200 × 4 × $15/MTok ≈ $0.156``
    - Actions 2..N: ``12_000 × 4 × $0.30/MTok + 200 × 4 × $15/MTok ≈ $0.0264`` each

    This makes the canonical 7-action smoke_test scenario project ~$0.34
    (under the $0.50 default cap) and a 50-action stress scenario
    ~$1.45 — both legitimate signals: the cap fires on actual runaway
    shapes, not on healthy multi-action playtests.

    Architect spec-check D (2026-05-23): the prior worst-case-no-rebate
    math made the default cap refuse smoke_test.yaml itself, which would
    have driven operators to alias ``--confirm-cost`` permanently and
    silenced the cap. Cache-aware math preserves the cap as a real signal.

    Assumes the cache TTL exceeds inter-action latency; otherwise actions
    land cold and projection underestimates. The default 1h TTL
    (``SIDEQUEST_ANTHROPIC_CACHE_TTL``) covers typical playtests.
    """
    if n_actions <= 0:
        return 0.0
    per_iter_full_input_usd = (
        _PREFLIGHT_INPUT_TOKENS_PER_ACTION * _SONNET_INPUT_PER_MTOK_USD / 1_000_000
    )
    per_iter_cached_input_usd = (
        _PREFLIGHT_INPUT_TOKENS_PER_ACTION
        * _SONNET_CACHED_READ_PER_MTOK_USD
        / 1_000_000
    )
    per_iter_output_usd = (
        _PREFLIGHT_OUTPUT_TOKENS_PER_ACTION * _SONNET_OUTPUT_PER_MTOK_USD / 1_000_000
    )
    first_action_usd = _PREFLIGHT_ITERS_ASSUMED * (
        per_iter_full_input_usd + per_iter_output_usd
    )
    cached_action_usd = _PREFLIGHT_ITERS_ASSUMED * (
        per_iter_cached_input_usd + per_iter_output_usd
    )
    return first_action_usd + (n_actions - 1) * cached_action_usd


def preflight_cost_check(
    scenario: dict[str, Any],
    *,
    max_projected_cost_usd: float,
    confirm_cost: bool,
) -> bool:
    """Print projected cost; refuse if projection > cap without confirm.

    AC4 + AC7: operator-facing cost guard. Returns ``True`` when the run
    should proceed; returns ``False`` (after printing the loud refusal)
    when the projection exceeds the cap and ``confirm_cost`` is False.

    The projection is ALWAYS printed (even when under cap and even when
    bypassed via ``confirm_cost``) so every run has an audit trail.

    :param scenario: Loaded scenario dict (output of ``load_scenario``).
    :param max_projected_cost_usd: Refuse threshold; the run halts when
        the worst-case projection exceeds this.
    :param confirm_cost: When True, bypasses the cap (still prints the
        projection for the audit trail).
    """
    actions = scenario.get("actions") or []
    n_actions = len(actions)
    projected = _project_preflight_cost_usd(n_actions)

    # Loud: top + bottom rule so a tailed log can't miss it.
    rule = "=" * 68
    print(rule, file=sys.stderr)
    print(
        f"[61-4 preflight] projected cost: ${projected:.2f} USD "
        f"(N={n_actions} actions × "
        f"{_PREFLIGHT_INPUT_TOKENS_PER_ACTION:,} input × "
        f"{_PREFLIGHT_ITERS_ASSUMED} iters @ Sonnet rates; "
        f"action 1 full-rate input, actions 2+ cached-read per ADR-101)",
        file=sys.stderr,
    )
    print(
        f"[61-4 preflight] cap: ${max_projected_cost_usd:.2f} USD "
        f"(--max-projected-cost-usd; bypass with --confirm-cost)",
        file=sys.stderr,
    )

    over_cap = projected > max_projected_cost_usd
    if over_cap and not confirm_cost:
        print(
            f"[61-4 preflight] REFUSED — projected ${projected:.2f} USD "
            f"exceeds cap ${max_projected_cost_usd:.2f} USD. "
            "Re-run with --confirm-cost to override, or shrink the scenario.",
            file=sys.stderr,
        )
        print(rule, file=sys.stderr)
        return False

    if over_cap and confirm_cost:
        print(
            f"[61-4 preflight] OVER CAP — proceeding (--confirm-cost supplied). "
            f"projected ${projected:.2f} USD > cap ${max_projected_cost_usd:.2f} USD",
            file=sys.stderr,
        )
    else:
        print(
            f"[61-4 preflight] OK — projected ${projected:.2f} USD ≤ cap "
            f"${max_projected_cost_usd:.2f} USD",
            file=sys.stderr,
        )
    print(rule, file=sys.stderr)
    return True


# ── Contact sheet — end-of-run render montage ───────────────────────────────
#
# Headless playtests still queue daemon image renders (there's no UI to show
# them, but the render pipeline runs end-to-end). Rather than waste that work,
# the driver collects every IMAGE the run produced and montages them into a
# single contact-sheet PNG at the end, so the visual output of a headless run
# is reviewable at a glance. Requires Pillow (run with ``uv run --with pillow``).


class ContactSheetError(RuntimeError):
    """Raised when a contact sheet was requested but cannot be built."""


def _fetch_image_bytes(url: str, rest_base: str) -> bytes:
    """Fetch one render. Relative ``/renders/*`` URLs are resolved against the
    server's REST base; absolute http(s) URLs (e.g. R2) are fetched directly."""
    full = url if url.startswith(("http://", "https://")) else f"{rest_base.rstrip('/')}{url}"
    resp = httpx.get(full, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def build_contact_sheet(
    images: list[dict[str, str]],
    out_path: Path,
    *,
    rest_base: str,
    thumb_px: int = 320,
    cols: int | None = None,
) -> int:
    """Montage ``images`` into a captioned grid PNG at ``out_path``.

    Returns the number of tiles successfully placed. Raises
    ``ContactSheetError`` if Pillow is missing (loud — No Silent Fallbacks:
    a requested sheet that silently no-ops would hide the missing dep) or if
    no tile could be fetched/decoded.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # noqa: BLE001
        raise ContactSheetError(
            "Pillow is required for the contact sheet — re-run with "
            "`uv run --with pillow ...` or `uv pip install pillow`."
        ) from exc

    import io

    tiles: list[tuple[Image.Image, str]] = []
    for img in images:
        try:
            raw = _fetch_image_bytes(img["url"], rest_base)
            pil = Image.open(io.BytesIO(raw)).convert("RGB")
        except (httpx.HTTPError, OSError) as exc:  # unreachable render / bad bytes
            console.print(
                f"[yellow][contact-sheet] skipped {img.get('url', '?')}: {exc}[/yellow]"
            )
            continue
        label = img.get("tier") or ""
        cap = (img.get("caption") or "").strip().replace("\n", " ")
        if cap:
            label = f"{label}: {cap}" if label else cap
        tiles.append((pil, label[:90]))

    if not tiles:
        raise ContactSheetError(
            f"no renders could be fetched/decoded (had {len(images)} IMAGE url(s))"
        )

    caption_h = 22
    pad = 8
    cell = thumb_px + caption_h + pad
    n = len(tiles)
    ncols = cols or min(4, max(1, math.ceil(math.sqrt(n))))
    nrows = math.ceil(n / ncols)

    sheet = Image.new("RGB", (ncols * cell + pad, nrows * cell + pad), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None

    for idx, (pil, label) in enumerate(tiles):
        r, c = divmod(idx, ncols)
        x = pad + c * cell
        y = pad + r * cell
        pil.thumbnail((thumb_px, thumb_px))
        # Center the thumbnail in its cell column width.
        ox = x + (thumb_px - pil.width) // 2
        sheet.paste(pil, (ox, y))
        if font is not None:
            draw.text((x, y + thumb_px + 4), label, fill=(210, 210, 215), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return n


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
        "--fresh",
        action="store_true",
        help=(
            "Force a brand-new session (cache-bust / clean slate). By DEFAULT "
            "the playtest REUSES an existing same-day slug so the 1h prompt "
            "cache stays warm across runs (ADR-101) — repeated runs are cheap. "
            "Pass --fresh to mint a new session: it starts COLD and re-bills the "
            "full stable prefix. Note reuse resumes the existing character/state "
            "(chargen is skipped); use --fresh when a scenario must replay from "
            "chargen on a clean slate."
        ),
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
    # Story 61-4 — Preflight cost guard (defense against the 2026-05-23
    # $313 runaway). Prints worst-case projected cost before the scenario
    # runs and refuses to proceed past the cap unless --confirm-cost is
    # supplied. See sprint/context/context-story-61-4.md decision D.
    parser.add_argument(
        "--contact-sheet",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "After the run, montage every IMAGE the scenario produced into a "
            "captioned contact-sheet PNG at PATH (requires Pillow: run with "
            "`uv run --with pillow ...`). When omitted, a sheet is still "
            "written next to --span-jsonl (or to ./<slug>-contact-sheet.png) "
            "if the run produced any renders. Headless runs queue daemon "
            "renders end-to-end; this makes that visual output reviewable "
            "without a UI."
        ),
    )
    parser.add_argument(
        "--no-contact-sheet",
        action="store_true",
        help="Disable the end-of-run contact sheet even if renders were produced.",
    )
    parser.add_argument(
        "--render-drain-timeout",
        type=float,
        default=120.0,
        metavar="SECONDS",
        help=(
            "Max seconds to wait after the scenario completes for in-flight "
            "daemon renders to land as IMAGE messages (default: %(default)s). "
            "Daemon image generation runs behind the turn that queued it; "
            "this drain lets the contact sheet capture them. Ignored when "
            "--no-contact-sheet is set."
        ),
    )
    parser.add_argument(
        "--max-projected-cost-usd",
        type=float,
        default=0.50,
        help=(
            "Refuse scenarios whose projected cost exceeds this USD cap "
            "(default: %(default)s ≈ 16x the per-turn target). Projection "
            "assumes cache-read on iters 2+ per ADR-101 (action 1 pays "
            "full input rate; actions 2..N ride cache-read at $0.30/MTok). "
            "Bypass with --confirm-cost. Story 61-4 defense against the "
            "2026-05-23 runaway."
        ),
    )
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help=(
            "Bypass the --max-projected-cost-usd cap for this run. The "
            "projection is still printed for the audit trail. Use when "
            "you've eyeballed the cost and accept it."
        ),
    )
    return parser.parse_args(argv)


def _emit_contact_sheet(pt: Playtest, args: argparse.Namespace) -> None:
    """Build the end-of-run contact sheet from the renders the run captured.

    Best-effort post-run artifact: a missing Pillow dep or unreachable render
    is logged loudly but never changes the scenario's exit code (the span
    capture / validation is the primary artifact). Disabled by
    ``--no-contact-sheet``.
    """
    if args.no_contact_sheet:
        return
    if not pt.images:
        console.print(
            "[dim][contact-sheet] no IMAGE renders captured this run — "
            "nothing to montage.[/dim]"
        )
        return

    if args.contact_sheet is not None:
        target = args.contact_sheet
    elif args.span_jsonl is not None:
        target = args.span_jsonl.with_name(f"{args.span_jsonl.stem}-contact-sheet.png")
    else:
        target = Path(f"{pt.slug or 'playtest'}-contact-sheet.png")

    try:
        n = build_contact_sheet(pt.images, target, rest_base=args.rest)
    except ContactSheetError as exc:
        console.print(f"[bold yellow][contact-sheet] {exc}[/bold yellow]")
        print(f"contact-sheet skipped: {exc}", file=sys.stderr)
        return
    console.print(
        f"[green][contact-sheet] {n} render(s) → {target.resolve()}[/green]"
    )


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

        # Story 61-4 preflight cost guard: refuse to spin up the WS
        # session if the worst-case projection exceeds the cap. Skipped in
        # fixture mode because fixtures don't carry a scripted action list
        # (their cost shape is driven by the harness, not by --scenario).
        if not preflight_cost_check(
            scenario,
            max_projected_cost_usd=args.max_projected_cost_usd,
            confirm_cost=args.confirm_cost,
        ):
            return 2

    pt = Playtest(
        scenario,
        server=args.server,
        rest_base=args.rest,
        player_name=args.player_name,
        force_new=args.fresh,
        idle_timeout=args.idle_timeout,
        seed=args.seed,
        fixture=args.fixture,
        collect_renders=not args.no_contact_sheet,
        render_drain_timeout=args.render_drain_timeout,
    )

    # No-flag path: span capture is strictly additive. The contact sheet is
    # likewise additive — it never changes the scenario exit code.
    if args.span_jsonl is None:
        rc = await pt.run()
        _emit_contact_sheet(pt, args)
        return rc

    # Mark the run window *before* the scenario starts so the Jaeger
    # query can scope to this run's spans only.
    run_start_us = _now_us()
    rc = await pt.run()
    run_end_us = _now_us()
    _emit_contact_sheet(pt, args)

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
