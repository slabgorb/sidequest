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
    1 — protocol error, server unreachable, or chargen got stuck
    2 — scenario invalid
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import random
import sys
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
    return await pt.run()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    with contextlib.suppress(KeyboardInterrupt):
        return asyncio.run(amain(args))
    return 130


if __name__ == "__main__":
    sys.exit(main())
