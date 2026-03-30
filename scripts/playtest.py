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
from rich.console import Console
from rich.text import Text

console = Console()

# ── Color coding by message type ────────────────────────────────────────────

MSG_STYLES = {
    "NARRATION": "white",
    "NARRATION_CHUNK": "white",
    "NARRATION_END": "dim",
    "THINKING": "dim cyan",
    "SESSION_EVENT": "bold green",
    "CHARACTER_CREATION": "bold yellow",
    "TURN_STATUS": "cyan",
    "PARTY_STATUS": "cyan",
    "COMBAT_EVENT": "bold red",
    "IMAGE": "magenta",
    "AUDIO_CUE": "blue",
    "INVENTORY": "yellow",
    "MAP_UPDATE": "green",
    "CHARACTER_SHEET": "yellow",
    "CHAPTER_MARKER": "bold magenta",
    "ERROR": "bold red",
    "TTS_START": "dim",
    "TTS_CHUNK": "dim",
    "TTS_END": "dim",
}

# ── Message rendering ───────────────────────────────────────────────────────


def render_message(msg: dict) -> None:
    """Render a GameMessage to the console with color coding."""
    msg_type = msg.get("type", "UNKNOWN")
    payload = msg.get("payload", {})
    style = MSG_STYLES.get(msg_type, "white")

    if msg_type == "NARRATION":
        text = payload.get("text", "")
        console.print()
        console.print(Text(text, style="white"), width=80)
        delta = payload.get("state_delta")
        if delta:
            console.print(f"  [dim][STATE] {json.dumps(delta, indent=None)}[/dim]")
        footnotes = payload.get("footnotes", [])
        for fn in footnotes:
            marker = fn.get("marker", "?")
            summary = fn.get("summary", "")
            cat = fn.get("category", "")
            new = " NEW" if fn.get("is_new") else ""
            console.print(f"  [dim][{marker}] {cat}{new}: {summary}[/dim]")

    elif msg_type == "NARRATION_CHUNK":
        text = payload.get("text", "")
        console.print(text, end="", style="white")

    elif msg_type == "NARRATION_END":
        console.print()
        delta = payload.get("state_delta")
        if delta:
            console.print(f"  [dim][STATE] {json.dumps(delta, indent=None)}[/dim]")

    elif msg_type == "THINKING":
        console.print("[dim]...[/dim]", end="")

    elif msg_type == "SESSION_EVENT":
        event = payload.get("event", "")
        console.print(f"[{style}][SESSION] {event}[/{style}]")
        if event == "connected":
            has_char = payload.get("has_character", False)
            console.print(f"  has_character: {has_char}")
        elif event == "ready":
            state = payload.get("initial_state", {})
            loc = state.get("location", "unknown")
            console.print(f"  location: {loc}")

    elif msg_type == "CHARACTER_CREATION":
        phase = payload.get("phase", "")
        scene = payload.get("scene_index", "?")
        total = payload.get("total_scenes", "?")
        prompt_text = payload.get("prompt", "")
        choices = payload.get("choices", [])
        console.print(f"[{style}][CHARGEN] phase={phase} ({scene}/{total})[/{style}]")
        if prompt_text:
            console.print(f"  {prompt_text}")
        if choices:
            for i, c in enumerate(choices):
                label = c.get("label", c) if isinstance(c, dict) else c
                console.print(f"  [{i + 1}] {label}")
        if payload.get("character"):
            console.print(f"  [bold green]Character created![/bold green]")

    elif msg_type == "IMAGE":
        url = payload.get("image_url", "")
        tier = payload.get("tier", "")
        gen_ms = payload.get("generation_ms", 0)
        console.print(
            f"[{style}][RENDER] {tier} — {url} ({gen_ms}ms)[/{style}]"
        )

    elif msg_type == "AUDIO_CUE":
        mood = payload.get("mood", "")
        track = payload.get("track", "")
        console.print(f"[{style}][AUDIO] mood={mood} track={track}[/{style}]")

    elif msg_type == "COMBAT_EVENT":
        console.print(f"[{style}][COMBAT] {json.dumps(payload, indent=None)}[/{style}]")

    elif msg_type == "INVENTORY":
        items = payload.get("items", [])
        gold = payload.get("gold", 0)
        console.print(f"[{style}][INVENTORY] {len(items)} items, {gold} gold[/{style}]")
        for item in items[:5]:
            name = item.get("name", "???")
            console.print(f"  - {name}")
        if len(items) > 5:
            console.print(f"  ... and {len(items) - 5} more")

    elif msg_type == "MAP_UPDATE":
        loc = payload.get("current_location", "")
        regions = payload.get("explored_locations", [])
        console.print(f"[{style}][MAP] {loc} ({len(regions)} explored)[/{style}]")

    elif msg_type == "CHAPTER_MARKER":
        title = payload.get("title", "")
        console.print(f"\n[{style}]{'=' * 60}[/{style}]")
        console.print(f"[{style}]  {title}[/{style}]")
        console.print(f"[{style}]{'=' * 60}[/{style}]\n")

    elif msg_type == "TURN_STATUS":
        name = payload.get("player_name", "")
        status = payload.get("status", "")
        console.print(f"[{style}][TURN] {name}: {status}[/{style}]")

    elif msg_type == "PARTY_STATUS":
        members = payload.get("members", [])
        names = [m.get("name", "?") for m in members]
        console.print(f"[{style}][PARTY] {', '.join(names)}[/{style}]")

    elif msg_type == "ERROR":
        error = payload.get("message", payload.get("error", str(payload)))
        console.print(f"[{style}][ERROR] {error}[/{style}]")

    elif msg_type in ("TTS_START", "TTS_CHUNK", "TTS_END"):
        pass  # Silently skip TTS in headless mode

    else:
        console.print(f"[dim][{msg_type}] {json.dumps(payload, indent=None)}[/dim]")


# ── Watcher dashboard (OTEL telemetry WebSocket server) ─────────────────────

# Connected browser clients
_dashboard_clients: set = set()

# Event history for late-joining browsers (ring buffer)
_event_history: list[str] = []
_MAX_HISTORY = 200


async def _dashboard_handler(websocket) -> None:
    """Handle a browser connecting to the dashboard WebSocket."""
    _dashboard_clients.add(websocket)
    console.print(f"[dim]Dashboard client connected ({len(_dashboard_clients)} total)[/dim]")
    try:
        # Send event history so late joiners see context
        for raw in _event_history:
            await websocket.send(raw)
        # Keep alive until client disconnects
        async for _ in websocket:
            pass  # Browser doesn't send us anything
    except websockets.ConnectionClosed:
        pass
    finally:
        _dashboard_clients.discard(websocket)
        console.print(f"[dim]Dashboard client disconnected ({len(_dashboard_clients)} remaining)[/dim]")


async def _broadcast_to_dashboards(raw: str) -> None:
    """Fan out a raw JSON event to all connected browser clients."""
    _event_history.append(raw)
    if len(_event_history) > _MAX_HISTORY:
        del _event_history[: len(_event_history) - _MAX_HISTORY]
    if _dashboard_clients:
        await asyncio.gather(
            *(client.send(raw) for client in _dashboard_clients),
            return_exceptions=True,
        )


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SideQuest OTEL Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1a2e; color: #e0e0e0; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; padding: 16px; }
  h1 { color: #00d4ff; font-size: 16px; margin-bottom: 12px; }
  .status { color: #666; margin-bottom: 12px; font-size: 12px; }
  .status.connected { color: #4caf50; }

  #events { max-height: calc(100vh - 120px); overflow-y: auto; }
  .turn { border-left: 3px solid #00d4ff; padding: 8px 12px; margin-bottom: 8px; background: #16213e; border-radius: 0 4px 4px 0; }
  .turn-header { color: #00d4ff; font-weight: bold; margin-bottom: 4px; }
  .event-line { padding: 1px 0; }
  .sev-info { color: #888; }
  .sev-pass { color: #4caf50; }
  .sev-warn { color: #ff9800; }
  .sev-error { color: #f44336; font-weight: bold; }

  .raw-event { padding: 4px 12px; margin-bottom: 2px; background: #16213e; border-radius: 4px; border-left: 3px solid #333; }
  .component { color: #bb86fc; }
  .event-type { color: #03dac6; }

  .histogram { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 6px; padding: 6px 0; border-top: 1px solid #333; }
  .hist-bar { display: flex; align-items: center; gap: 6px; }
  .hist-label { width: 100px; text-align: right; color: #888; }
  .hist-fill { height: 12px; background: #00d4ff; border-radius: 2px; min-width: 2px; transition: width 0.3s; }
  .hist-count { color: #666; font-size: 11px; width: 30px; }

  .stats { display: flex; gap: 24px; margin-bottom: 12px; padding: 8px 12px; background: #16213e; border-radius: 4px; }
  .stat { text-align: center; }
  .stat-value { font-size: 24px; color: #00d4ff; font-weight: bold; }
  .stat-label { font-size: 11px; color: #666; }
</style>
</head>
<body>
<h1>SideQuest OTEL Dashboard</h1>
<div class="status" id="status">Connecting...</div>
<div class="stats">
  <div class="stat"><div class="stat-value" id="turns">0</div><div class="stat-label">Turns</div></div>
  <div class="stat"><div class="stat-value" id="events-count">0</div><div class="stat-label">Events</div></div>
  <div class="stat"><div class="stat-value" id="errors">0</div><div class="stat-label">Errors</div></div>
  <div class="stat"><div class="stat-value" id="components">0</div><div class="stat-label">Components</div></div>
</div>
<div id="events"></div>

<script>
const eventsEl = document.getElementById('events');
const statusEl = document.getElementById('status');
const turnsEl = document.getElementById('turns');
const eventsCountEl = document.getElementById('events-count');
const errorsEl = document.getElementById('errors');
const componentsEl = document.getElementById('components');

let turnCount = 0;
let eventCount = 0;
let errorCount = 0;
const componentSet = new Set();
const histogram = {};

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function sevClass(severity) {
  return 'sev-' + (severity || 'info');
}

function sevPrefix(severity) {
  return { pass: '\\u2713', warn: '\\u26a0', error: '\\u2717', info: '\\u00b7' }[severity] || '\\u00b7';
}

function renderHistogram() {
  const entries = Object.entries(histogram).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return '';
  const max = Math.max(...entries.map(e => e[1]));
  return '<div class="histogram">' + entries.map(([name, count]) => {
    const pct = max > 0 ? (count / max * 100) : 0;
    return `<div class="hist-bar"><span class="hist-label">${escapeHtml(name)}</span><div class="hist-fill" style="width:${pct}px"></div><span class="hist-count">${count}</span></div>`;
  }).join('') + '</div>';
}

function updateStats() {
  turnsEl.textContent = turnCount;
  eventsCountEl.textContent = eventCount;
  errorsEl.textContent = errorCount;
  componentsEl.textContent = componentSet.size;
}

function addEvent(event) {
  eventCount++;

  // Raw WatcherEvent (component/event_type/severity/fields)
  if (event.component && event.event_type) {
    const comp = event.component;
    const etype = event.event_type;
    const severity = event.severity || 'info';
    const fields = event.fields || {};
    componentSet.add(comp);
    histogram[comp] = (histogram[comp] || 0) + 1;
    if (severity === 'error') errorCount++;

    const detail = Object.entries(fields)
      .filter(([k]) => k !== 'timestamp')
      .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
      .join(', ');

    const div = document.createElement('div');
    div.className = 'raw-event';
    div.innerHTML = `<span class="${sevClass(severity)}">${sevPrefix(severity)}</span> <span class="component">[${escapeHtml(comp)}]</span> <span class="event-type">${escapeHtml(etype)}</span>: ${escapeHtml(detail)}`;
    eventsEl.appendChild(div);
  }
  // Structured turn_complete
  else if (event.type === 'turn_complete') {
    turnCount++;
    const dur = ((event.agent_duration_ms || 0) / 1000).toFixed(1);
    const div = document.createElement('div');
    div.className = 'turn';
    let html = `<div class="turn-header">Turn ${event.turn_id || '?'} | ${escapeHtml(event.classified_intent || '?')} \\u2192 ${escapeHtml(event.agent_name || '?')} | ${dur}s</div>`;
    for (const line of (event.events || [])) {
      const sev = line.severity || 'info';
      if (sev === 'error') errorCount++;
      html += `<div class="event-line ${sevClass(sev)}">${sevPrefix(sev)} ${escapeHtml(line.text || '')}</div>`;
    }
    if (event.histogram) {
      for (const [k, v] of Object.entries(event.histogram)) {
        componentSet.add(k);
        histogram[k] = (histogram[k] || 0) + v;
      }
      html += renderHistogram();
    }
    div.innerHTML = html;
    eventsEl.appendChild(div);
  }
  else {
    const div = document.createElement('div');
    div.className = 'raw-event';
    div.innerHTML = `<span class="sev-info">\\u00b7</span> ${escapeHtml(JSON.stringify(event))}`;
    eventsEl.appendChild(div);
  }

  updateStats();
  eventsEl.scrollTop = eventsEl.scrollHeight;
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.onopen = () => {
    statusEl.textContent = 'Connected';
    statusEl.className = 'status connected';
  };
  ws.onmessage = (e) => {
    try { addEvent(JSON.parse(e.data)); } catch {}
  };
  ws.onclose = () => {
    statusEl.textContent = 'Disconnected — reconnecting...';
    statusEl.className = 'status';
    setTimeout(connect, 2000);
  };
}
connect();
</script>
</body>
</html>"""


async def _serve_dashboard_http(reader, writer):
    """Minimal async HTTP server for the dashboard HTML page."""
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5)
        # Read remaining headers (discard)
        while True:
            line = await reader.readline()
            if line == b"\r\n" or line == b"\n" or not line:
                break

        # Serve HTML for any GET request
        body = DASHBOARD_HTML.encode()
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Connection: close\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body
        writer.write(response)
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()


async def run_dashboard_server(
    api_host: str, api_port: int, dashboard_port: int,
) -> None:
    """
    Proxy: connects to API /ws/watcher as client, re-serves events on dashboard_port.
    HTTP dashboard on dashboard_port, WebSocket on dashboard_port+1.
    """
    ws_port = dashboard_port + 1

    # Inject the correct WebSocket port into the HTML
    global DASHBOARD_HTML
    DASHBOARD_HTML = DASHBOARD_HTML.replace(
        "${proto}//${location.host}/ws",
        f"${{proto}}//localhost:{ws_port}/ws",
    )

    # Start HTTP server for the dashboard page
    http_server = await asyncio.start_server(
        _serve_dashboard_http, "0.0.0.0", dashboard_port,
    )

    # Start WebSocket server for browser clients
    async with websockets.serve(_dashboard_handler, "0.0.0.0", ws_port):
        console.print(
            f"[bold green]OTEL Dashboard: http://localhost:{dashboard_port}/[/bold green]"
            f"[dim] (ws: :{ws_port})[/dim]"
        )
        # Connect to API watcher and proxy events
        api_uri = f"ws://{api_host}:{api_port}/ws/watcher"
        while True:
            try:
                async with websockets.connect(api_uri) as ws:
                    console.print(f"[dim]Watcher proxy connected to {api_uri}[/dim]")
                    async for raw in ws:
                        await _broadcast_to_dashboards(raw)
            except (websockets.ConnectionClosed, OSError) as e:
                console.print(f"[dim]Watcher proxy disconnected: {e} — reconnecting in 2s[/dim]")
                await asyncio.sleep(2)


# ── Session connect message ─────────────────────────────────────────────────


def make_connect_msg(genre: str, world: str, player_name: str) -> dict:
    return {
        "type": "SESSION_EVENT",
        "payload": {
            "event": "connect",
            "genre": genre,
            "world": world,
            "player_name": player_name,
        },
        "player_id": "",
    }


def make_action_msg(action: str) -> dict:
    return {
        "type": "PLAYER_ACTION",
        "payload": {"action": action, "aside": False},
        "player_id": "",
    }


def make_chargen_choice(choice: str) -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "scene", "choice": choice},
        "player_id": "",
    }


def make_chargen_confirm() -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "confirmation", "choice": "yes"},
        "player_id": "",
    }


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

    async with websockets.connect(uri) as ws:
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
                state["chargen_prompt"].clear()
                await state["chargen_prompt"].wait()

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

                state["chargen_done"].clear()
                await state["chargen_done"].wait()

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
    async with websockets.connect(uri) as ws:
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
                state["chargen_prompt"].clear()
                await state["chargen_prompt"].wait()

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

                state["chargen_done"].clear()
                await state["chargen_done"].wait()

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

    async with websockets.connect(uri) as ws:
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
                state["chargen_prompt"].clear()
                await state["chargen_prompt"].wait()
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
                state["chargen_done"].clear()
                await state["chargen_done"].wait()

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

    args = parser.parse_args()

    # Handle ctrl-c gracefully
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    dp = args.dashboard_port

    if args.scenario:
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
