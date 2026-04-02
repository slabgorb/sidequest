#!/usr/bin/env python3
"""playtest.py — Headless playtest driver for SideQuest.

Connects to the SideQuest API server via WebSocket and drives gameplay
without a UI. Supports interactive mode (human types actions), scripted
mode (YAML scenario files), and multiplayer simulation.

Run via `just playtest` from the orchestrator root, or:
  python3 scripts/playtest.py                                     # interactive
  python3 scripts/playtest.py --genre mutant_wasteland --world flickering_reach
  python3 scripts/playtest.py --scenario scenarios/smoke_test.yaml
  python3 scripts/playtest.py --players 2                         # multiplayer
"""

import argparse
import asyncio
import json
import signal
import sys
import textwrap
from pathlib import Path

import websockets
import yaml

from playtest_dashboard import run_dashboard_server
from playtest_messages import (
    console,
    make_action_msg,
    make_chargen_choice,
    make_chargen_confirm,
    make_connect_msg,
    render_message,
)

# ── Receiver task ───────────────────────────────────────────────────────────


async def receiver(ws, state: dict) -> None:
    """Background task that receives and renders all messages from the server."""
    try:
        async for raw in ws:
            msg = json.loads(raw)
            render_message(msg)

            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            # Track state for the driver
            if msg_type == "SESSION_EVENT":
                event = payload.get("event", "")
                if event == "connected":
                    state["connected"] = True
                    state["has_character"] = payload.get("has_character", False)
                    state["chargen_done"].set()
                elif event == "ready":
                    state["ready"] = True
                    state["ready_event"].set()
            elif msg_type == "CHARACTER_CREATION":
                phase = payload.get("phase", "")
                if phase == "complete":
                    state["has_character"] = True
                    state["chargen_done"].set()
                elif phase in ("scene", "confirmation"):
                    state["chargen_pending"] = payload
                    state["chargen_done"].set()
                    state["chargen_prompt"].set()
            elif msg_type == "NARRATION":
                state["last_narration"] = payload.get("text", "")
                state["narration_event"].set()
            elif msg_type == "NARRATION_END":
                state["narration_event"].set()
    except websockets.ConnectionClosed:
        console.print("[bold red]Connection closed by server[/bold red]")
        state["disconnected"] = True


# ── Interactive mode ────────────────────────────────────────────────────────


async def run_interactive(
    host: str, port: int, genre: str, world: str, player_name: str,
    watch: bool = True, dashboard_port: int = 9765,
) -> None:
    """Interactive playtest — human types actions, sees narration."""
    uri = f"ws://{host}:{port}/ws"
    console.print(f"[bold]Connecting to {uri}...[/bold]")

    async with websockets.connect(uri, ping_timeout=None) as ws:
        state = {
            "connected": False,
            "has_character": False,
            "ready": False,
            "disconnected": False,
            "last_narration": "",
            "chargen_pending": None,
            "chargen_done": asyncio.Event(),
            "chargen_prompt": asyncio.Event(),
            "ready_event": asyncio.Event(),
            "narration_event": asyncio.Event(),
        }

        # Start receiver
        recv_task = asyncio.create_task(receiver(ws, state))

        # Start watcher telemetry (OTEL dashboard)
        watcher_task = None
        if watch:
            watcher_task = asyncio.create_task(run_dashboard_server(host, port, dashboard_port))

        # Connect to session
        console.print(f"[bold]Joining {genre}/{world} as {player_name}...[/bold]")
        await ws.send(json.dumps(make_connect_msg(genre, world, player_name)))

        # Wait for connection ack
        await state["chargen_done"].wait()

        # Character creation (if needed)
        if not state["has_character"]:
            console.print(
                "\n[bold yellow]Character creation — type choices or 'auto' for defaults[/bold yellow]"
            )
            while not state["has_character"]:
                # Wait for either a chargen prompt (scene/confirmation) or
                # chargen complete — must wait on BOTH events because
                # "complete" only sets chargen_done, not chargen_prompt.
                state["chargen_prompt"].clear()
                state["chargen_done"].clear()
                done_task = asyncio.create_task(state["chargen_done"].wait())
                prompt_task = asyncio.create_task(state["chargen_prompt"].wait())
                await asyncio.wait(
                    [done_task, prompt_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                done_task.cancel()
                prompt_task.cancel()

                # "complete" may have fired — check before prompting
                if state["has_character"]:
                    break

                pending = state["chargen_pending"]
                if not pending:
                    continue

                phase = pending.get("phase", "")
                if phase == "confirmation":
                    console.print(
                        "\n[yellow]Confirm character? (yes/no):[/yellow] ", end=""
                    )
                    choice = await asyncio.get_event_loop().run_in_executor(
                        None, input
                    )
                    if choice.strip().lower() in ("y", "yes", "auto", ""):
                        await ws.send(json.dumps(make_chargen_confirm()))
                    else:
                        await ws.send(json.dumps(make_chargen_choice("no")))
                elif phase == "scene":
                    choices = pending.get("choices", [])
                    allows_freeform = pending.get("allows_freeform", False)

                    prompt_text = "[yellow]Choice:[/yellow] "
                    console.print(f"\n{prompt_text}", end="")
                    choice = await asyncio.get_event_loop().run_in_executor(
                        None, input
                    )
                    choice = choice.strip()

                    if choice.lower() == "auto":
                        # Pick first choice or send generic response
                        if choices:
                            first = choices[0]
                            auto_choice = (
                                first.get("label", first)
                                if isinstance(first, dict)
                                else first
                            )
                        else:
                            auto_choice = "A wanderer with no past."
                        await ws.send(json.dumps(make_chargen_choice(auto_choice)))
                    elif choice.isdigit() and choices:
                        idx = int(choice) - 1
                        if 0 <= idx < len(choices):
                            c = choices[idx]
                            label = (
                                c.get("label", c) if isinstance(c, dict) else c
                            )
                            await ws.send(json.dumps(make_chargen_choice(label)))
                        else:
                            console.print("[red]Invalid choice number[/red]")
                    else:
                        await ws.send(json.dumps(make_chargen_choice(choice)))

        # Wait for ready
        if not state["ready"]:
            await state["ready_event"].wait()

        console.print(
            "\n[bold green]Ready! Type actions, /commands, or 'quit' to exit.[/bold green]\n"
        )

        # Main action loop
        while not state["disconnected"]:
            try:
                action = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("> ")
                )
            except (EOFError, KeyboardInterrupt):
                break

            action = action.strip()
            if not action:
                continue
            if action.lower() in ("quit", "exit", "q"):
                break

            state["narration_event"].clear()
            await ws.send(json.dumps(make_action_msg(action)))

            # Wait for narration response (with timeout)
            try:
                await asyncio.wait_for(state["narration_event"].wait(), timeout=120)
            except asyncio.TimeoutError:
                console.print("[red]Timed out waiting for narration[/red]")

        recv_task.cancel()
        if watcher_task:
            watcher_task.cancel()
        console.print("[bold]Session ended.[/bold]")


# ── Scripted mode ───────────────────────────────────────────────────────────


async def run_scripted(
    host: str, port: int, scenario_path: str, watch: bool = True,
    dashboard_port: int = 9765,
) -> None:
    """Run a YAML scenario file against the server."""
    path = Path(scenario_path)
    if not path.exists():
        console.print(f"[red]Scenario file not found: {path}[/red]")
        sys.exit(1)

    with open(path) as f:
        scenario = yaml.safe_load(f)

    name = scenario.get("name", path.stem)
    genre = scenario.get("genre", "mutant_wasteland")
    world = scenario.get("world", "flickering_reach")
    actions = scenario.get("actions", [])
    player_name = scenario.get("character", {}).get("name", "Playtest Runner")

    console.print(f"[bold]Running scenario: {name}[/bold]")
    console.print(f"  genre: {genre}, world: {world}, actions: {len(actions)}")

    uri = f"ws://{host}:{port}/ws"
    async with websockets.connect(uri, ping_timeout=None) as ws:
        state = {
            "connected": False,
            "has_character": False,
            "ready": False,
            "disconnected": False,
            "last_narration": "",
            "chargen_pending": None,
            "chargen_done": asyncio.Event(),
            "chargen_prompt": asyncio.Event(),
            "ready_event": asyncio.Event(),
            "narration_event": asyncio.Event(),
        }

        recv_task = asyncio.create_task(receiver(ws, state))

        watcher_task = None
        if watch:
            watcher_task = asyncio.create_task(run_dashboard_server(host, port, dashboard_port))

        # Connect
        await ws.send(json.dumps(make_connect_msg(genre, world, player_name)))
        await state["chargen_done"].wait()

        # Auto character creation
        if not state["has_character"]:
            console.print("[yellow]Auto-creating character...[/yellow]")
            while not state["has_character"]:
                # Wait for either a new chargen prompt or chargen completion
                state["chargen_prompt"].clear()
                state["chargen_done"].clear()
                done_task = asyncio.create_task(state["chargen_done"].wait())
                prompt_task = asyncio.create_task(state["chargen_prompt"].wait())
                await asyncio.wait(
                    [done_task, prompt_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                done_task.cancel()
                prompt_task.cancel()

                # Re-check — "complete" may have fired
                if state["has_character"]:
                    break

                pending = state["chargen_pending"]
                if not pending:
                    continue

                phase = pending.get("phase", "")
                if phase == "confirmation":
                    await ws.send(json.dumps(make_chargen_confirm()))
                elif phase == "scene":
                    choices = pending.get("choices", [])
                    if choices:
                        first = choices[0]
                        auto_choice = (
                            first.get("label", first)
                            if isinstance(first, dict)
                            else first
                        )
                    else:
                        auto_choice = "A wanderer with no past."
                    await ws.send(json.dumps(make_chargen_choice(auto_choice)))

        # Wait for ready
        if not state["ready"]:
            await state["ready_event"].wait()

        console.print(f"\n[bold green]Session ready. Running {len(actions)} actions...[/bold green]\n")

        # Execute actions
        passed = 0
        failed = 0
        for i, entry in enumerate(actions):
            if isinstance(entry, str):
                action = entry
                assertions = {}
            else:
                action = entry.get("action", "")
                assertions = {
                    k: v for k, v in entry.items() if k.startswith("assert")
                }

            console.print(f"\n[bold cyan]--- Action {i + 1}/{len(actions)}: {action} ---[/bold cyan]")
            state["narration_event"].clear()
            await ws.send(json.dumps(make_action_msg(action)))

            try:
                await asyncio.wait_for(state["narration_event"].wait(), timeout=120)
                passed += 1
            except asyncio.TimeoutError:
                console.print(f"[red]TIMEOUT on action {i + 1}: {action}[/red]")
                failed += 1

        recv_task.cancel()
        if watcher_task:
            watcher_task.cancel()

        console.print(f"\n[bold]{'=' * 40}[/bold]")
        console.print(f"[bold]Scenario: {name}[/bold]")
        console.print(f"  [green]Passed: {passed}[/green]")
        if failed:
            console.print(f"  [red]Failed: {failed}[/red]")
        console.print(f"[bold]{'=' * 40}[/bold]")

        if failed:
            sys.exit(1)


# ── Multiplayer mode ────────────────────────────────────────────────────────


async def run_player(
    host: str, port: int, genre: str, world: str,
    player_name: str, actions: list[str], player_num: int,
) -> dict:
    """Run a single player through a sequence of actions."""
    uri = f"ws://{host}:{port}/ws"
    results = {"player": player_name, "passed": 0, "failed": 0}

    async with websockets.connect(uri, ping_timeout=None) as ws:
        state = {
            "connected": False,
            "has_character": False,
            "ready": False,
            "disconnected": False,
            "last_narration": "",
            "chargen_pending": None,
            "chargen_done": asyncio.Event(),
            "chargen_prompt": asyncio.Event(),
            "ready_event": asyncio.Event(),
            "narration_event": asyncio.Event(),
        }

        recv_task = asyncio.create_task(receiver(ws, state))

        await ws.send(json.dumps(make_connect_msg(genre, world, player_name)))
        await state["chargen_done"].wait()

        # Auto character creation
        if not state["has_character"]:
            while not state["has_character"]:
                # Wait for either prompt or complete — same pattern as run_scripted
                state["chargen_prompt"].clear()
                state["chargen_done"].clear()
                done_task = asyncio.create_task(state["chargen_done"].wait())
                prompt_task = asyncio.create_task(state["chargen_prompt"].wait())
                await asyncio.wait(
                    [done_task, prompt_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                done_task.cancel()
                prompt_task.cancel()

                if state["has_character"]:
                    break

                pending = state["chargen_pending"]
                if not pending:
                    continue
                phase = pending.get("phase", "")
                if phase == "confirmation":
                    await ws.send(json.dumps(make_chargen_confirm()))
                elif phase == "scene":
                    choices = pending.get("choices", [])
                    if choices:
                        first = choices[0]
                        auto_choice = (
                            first.get("label", first)
                            if isinstance(first, dict)
                            else first
                        )
                    else:
                        auto_choice = "A wanderer seeking purpose."
                    await ws.send(json.dumps(make_chargen_choice(auto_choice)))

        if not state["ready"]:
            await state["ready_event"].wait()

        console.print(
            f"[bold green]Player {player_num} ({player_name}) ready[/bold green]"
        )

        for action in actions:
            state["narration_event"].clear()
            await ws.send(json.dumps(make_action_msg(action)))
            try:
                await asyncio.wait_for(state["narration_event"].wait(), timeout=120)
                results["passed"] += 1
            except asyncio.TimeoutError:
                console.print(
                    f"[red]Player {player_num} TIMEOUT: {action}[/red]"
                )
                results["failed"] += 1

        recv_task.cancel()

    return results


async def run_multiplayer(
    host: str, port: int, genre: str, world: str, num_players: int,
    watch: bool = True, dashboard_port: int = 9765,
) -> None:
    """Spawn N players concurrently."""
    console.print(
        f"[bold]Multiplayer playtest: {num_players} players in {genre}/{world}[/bold]"
    )

    default_actions = [
        "look around",
        "examine the surroundings carefully",
        "talk to anyone nearby",
    ]

    # One watcher connection for all players (server-wide telemetry)
    watcher_task = None
    if watch:
        watcher_task = asyncio.create_task(run_dashboard_server(host, port, dashboard_port))

    tasks = []
    for i in range(num_players):
        name = f"Player {i + 1}"
        tasks.append(
            run_player(host, port, genre, world, name, default_actions, i + 1)
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    if watcher_task:
        watcher_task.cancel()

    console.print(f"\n[bold]{'=' * 40}[/bold]")
    console.print(f"[bold]Multiplayer Results ({num_players} players)[/bold]")
    total_passed = 0
    total_failed = 0
    for r in results:
        if isinstance(r, Exception):
            console.print(f"  [red]Error: {r}[/red]")
            total_failed += 1
        else:
            console.print(
                f"  {r['player']}: [green]{r['passed']} passed[/green]"
                + (f", [red]{r['failed']} failed[/red]" if r["failed"] else "")
            )
            total_passed += r["passed"]
            total_failed += r["failed"]
    console.print(f"\n  Total: [green]{total_passed} passed[/green]", end="")
    if total_failed:
        console.print(f", [red]{total_failed} failed[/red]")
    else:
        console.print()
    console.print(f"[bold]{'=' * 40}[/bold]")

    if total_failed:
        sys.exit(1)


# ── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SideQuest headless playtest driver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              %(prog)s                                        interactive mode
              %(prog)s --genre mutant_wasteland --world flickering_reach
              %(prog)s --scenario scenarios/smoke_test.yaml   scripted mode
              %(prog)s --players 2                            multiplayer test
              %(prog)s --dashboard-only                       OTEL dashboard only
              %(prog)s --dashboard-only --port 8080           dashboard for custom port
        """),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument(
        "--genre", default="mutant_wasteland", help="Genre pack slug"
    )
    parser.add_argument(
        "--world", default="flickering_reach", help="World slug"
    )
    parser.add_argument(
        "--name", default="Playtest Runner", help="Player name"
    )
    parser.add_argument(
        "--scenario", help="Path to YAML scenario file"
    )
    parser.add_argument(
        "--players",
        type=int,
        default=0,
        help="Number of simultaneous players (multiplayer mode)",
    )
    parser.add_argument(
        "--watch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run OTEL dashboard server (default: on)",
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=9765,
        help="Port for the OTEL dashboard web server (default: 9765)",
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Run only the OTEL dashboard (no playtest). Connects to a running server.",
    )

    args = parser.parse_args()

    # Handle ctrl-c gracefully
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    dp = args.dashboard_port

    if args.dashboard_only:
        console.print(
            f"[bold]OTEL Dashboard — connecting to ws://{args.host}:{args.port}/ws/watcher[/bold]"
        )
        asyncio.run(run_dashboard_server(args.host, args.port, dp))
    elif args.scenario:
        asyncio.run(run_scripted(args.host, args.port, args.scenario, watch=args.watch, dashboard_port=dp))
    elif args.players > 1:
        asyncio.run(
            run_multiplayer(
                args.host, args.port, args.genre, args.world, args.players,
                watch=args.watch, dashboard_port=dp,
            )
        )
    else:
        asyncio.run(
            run_interactive(
                args.host, args.port, args.genre, args.world, args.name,
                watch=args.watch, dashboard_port=dp,
            )
        )


if __name__ == "__main__":
    main()
