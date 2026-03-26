#!/usr/bin/env python3
"""watch.py — Live telemetry viewer for SideQuest Game Watcher.

Connects to the /ws/watcher WebSocket endpoint and renders a color-coded
stream of agent decisions, validation results, and subsystem activity
per turn. Run via `just watch` from the orchestrator root.
"""

import argparse
import asyncio
import json
import signal
import sys

import websockets
from rich.console import Console

console = Console()

# ── Severity styles ──────────────────────────────────────────────────────────

SEVERITY_STYLES = {
    "info": "white",
    "pass": "green",
    "warn": "yellow",
    "error": "red",
}

SEVERITY_PREFIXES = {
    "pass": "\u2713",
    "warn": "\u26a0",
    "error": "\u2717",
}

# ── Heatmap constants ────────────────────────────────────────────────────────

BAR_WIDTH = 11


# ── Rendering ────────────────────────────────────────────────────────────────

def render_turn_separator(event: dict) -> None:
    """Render a prominent separator line for a new turn."""
    turn_id = event.get("turn_id", "?")
    intent = event.get("classified_intent", "unknown")
    agent = event.get("agent_name", "unknown")
    duration_ms = event.get("agent_duration_ms", 0)
    duration = duration_ms / 1000
    line = f"\u2550\u2550\u2550 Turn {turn_id} | {intent} \u2192 {agent} | {duration:.1f}s "
    console.print(line.ljust(60, "\u2550"), style="bold cyan")


def render_event_line(line: dict) -> None:
    """Render a single sub-event line with severity coloring."""
    severity = line.get("severity", "info")
    style = SEVERITY_STYLES.get(severity, "white")
    prefix = SEVERITY_PREFIXES.get(severity, " ")
    text = line.get("text", "")
    console.print(f"  {prefix} {text}", style=style)


def render_heatmap(histogram: dict[str, int]) -> None:
    """Render a horizontal bar chart of subsystem invocation counts."""
    if not histogram:
        return
    console.print(
        "\u2500\u2500\u2500 Subsystem Activity "
        + "\u2500" * 37,
        style="dim",
    )
    max_count = max(histogram.values()) if histogram else 1
    for name, count in sorted(histogram.items(), key=lambda x: -x[1]):
        filled = round(count / max_count * BAR_WIDTH) if max_count > 0 else 0
        empty = BAR_WIDTH - filled
        bar = "\u2588" * filled + "\u2591" * empty
        label = f"  {name:<14}{bar} {count:>3}"
        if count == 0:
            console.print(f"{label}  \u26a0 unused", style="yellow")
        else:
            console.print(label)
    console.print()


def render_event(event: dict) -> None:
    """Dispatch rendering for a single WebSocket message."""
    event_type = event.get("type", "")

    if event_type == "turn_complete":
        render_turn_separator(event)
        for line in event.get("events", []):
            render_event_line(line)
        histogram = event.get("histogram")
        if histogram:
            render_heatmap(histogram)
    else:
        # Unknown event type — render raw for forward compatibility
        console.print(f"  [dim]{event_type}:[/dim] {json.dumps(event)}", style="dim")


# ── WebSocket client ─────────────────────────────────────────────────────────

async def watch(port: int) -> None:
    """Connect to the watcher WebSocket and stream events to the terminal."""
    uri = f"ws://localhost:{port}/ws/watcher"
    console.print(f"Connecting to [bold]{uri}[/bold] ...", style="dim")

    try:
        async with websockets.connect(uri) as ws:
            console.print("Connected. Streaming telemetry.\n", style="green")
            async for raw in ws:
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    console.print(f"  [red]malformed JSON:[/red] {raw!r}")
                    continue
                render_event(event)
    except websockets.exceptions.ConnectionClosedOK:
        console.print("\nWebSocket closed by server.", style="dim")
    except websockets.exceptions.ConnectionClosedError as exc:
        console.print(f"\nWebSocket closed unexpectedly: {exc}", style="yellow")
    except OSError as exc:
        console.print(f"\nCould not connect to {uri}: {exc}", style="red")
        console.print(
            "Is the API server running? Try [bold]just api-run[/bold] first.",
            style="dim",
        )
        sys.exit(1)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live telemetry viewer for SideQuest Game Watcher",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="API server port (default: 8765)",
    )
    args = parser.parse_args()

    # Clean exit on Ctrl-C
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    try:
        asyncio.run(watch(args.port))
    except KeyboardInterrupt:
        pass
    finally:
        console.print("\nWatcher stopped.", style="dim")


if __name__ == "__main__":
    main()
