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
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
  :root {
    --bg: #1a1a2e; --surface: #16213e; --border: #333; --accent: #00d4ff;
    --purple: #bb86fc; --teal: #03dac6; --green: #4caf50; --amber: #ff9800;
    --red: #f44336; --text: #e0e0e0; --muted: #888; --pink: #f06292;
    --sky: #4fc3f7;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'JetBrains Mono','Fira Code',monospace; font-size: 13px; }

  /* Header */
  #header { display: flex; align-items: center; gap: 16px; padding: 10px 16px; background: var(--surface); border-bottom: 1px solid var(--border); }
  #header .title { color: var(--accent); font-weight: bold; font-size: 15px; }
  #header .dot { font-size: 10px; color: var(--muted); }
  #header .dot.on { color: var(--green); }
  #header .stat { color: var(--muted); font-size: 12px; }
  #header .stat b { color: var(--text); }
  #header button { background: var(--border); color: var(--text); border: none; padding: 4px 10px; border-radius: 3px; cursor: pointer; font-size: 11px; }

  /* Tabs */
  #tabs { display: flex; border-bottom: 2px solid var(--border); background: var(--surface); }
  .tab { padding: 8px 20px; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -2px; font-size: 12px; }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab .badge { font-size: 10px; margin-left: 4px; padding: 1px 5px; border-radius: 8px; background: var(--border); }
  .tab .badge.err { background: var(--red); color: white; }

  /* Tab content */
  .tab-content { display: none; padding: 16px; height: calc(100vh - 82px); overflow-y: auto; }
  .tab-content.active { display: block; }

  /* Cards */
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin-bottom: 12px; }
  .card-title { color: var(--accent); font-size: 12px; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }

  /* Flame chart */
  .flame-row { display: flex; align-items: center; margin-bottom: 4px; }
  .flame-label { width: 110px; text-align: right; padding-right: 8px; color: var(--muted); font-size: 11px; flex-shrink: 0; }
  .flame-bar-wrap { flex: 1; position: relative; height: 20px; }
  .flame-bar { height: 20px; border-radius: 2px; display: inline-flex; align-items: center; padding-left: 6px; font-size: 10px; color: rgba(255,255,255,0.8); min-width: 2px; position: absolute; top: 0; }
  .flame-dur { color: var(--muted); font-size: 11px; margin-left: 8px; width: 60px; text-align: right; flex-shrink: 0; }

  /* Turn list */
  .turn-list { max-height: calc(100vh - 130px); overflow-y: auto; }
  .turn-item { padding: 6px 10px; cursor: pointer; border-left: 3px solid transparent; font-size: 12px; display: flex; justify-content: space-between; }
  .turn-item:hover { background: rgba(0,212,255,0.05); }
  .turn-item.selected { border-left-color: var(--accent); background: rgba(0,212,255,0.08); }
  .turn-item .ti-badge { font-size: 9px; padding: 1px 5px; border-radius: 8px; }
  .ti-degraded { background: var(--red); color: white; }
  .ti-combat { background: var(--amber); color: black; }

  /* Summary stats row */
  .stats-row { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 12px 20px; text-align: center; min-width: 100px; }
  .stat-val { font-size: 28px; font-weight: bold; color: var(--accent); }
  .stat-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; margin-top: 2px; }

  /* Health grid */
  .health-grid { display: grid; gap: 2px; font-size: 11px; }
  .hg-row { display: contents; }
  .hg-label { padding: 4px 8px; text-align: right; color: var(--muted); background: var(--surface); }
  .hg-cell { width: 24px; height: 24px; border-radius: 3px; display: flex; align-items: center; justify-content: center; font-size: 9px; }
  .hg-ok { background: rgba(76,175,80,0.3); color: var(--green); }
  .hg-warn { background: rgba(255,152,0,0.3); color: var(--amber); }
  .hg-err { background: rgba(244,67,54,0.3); color: var(--red); }
  .hg-empty { background: rgba(51,51,51,0.3); }
  .hg-silent { color: var(--amber); font-size: 10px; margin-left: 8px; }

  /* Event log */
  .evt-row { padding: 3px 8px; font-size: 11px; border-left: 3px solid var(--border); margin-bottom: 1px; }
  .evt-row .comp { color: var(--purple); }
  .evt-row .etype { color: var(--teal); }

  /* Charts */
  .chart-container { width: 100%; }
  .chart-container svg { width: 100%; }
  svg text { fill: var(--muted); font-family: inherit; font-size: 11px; }
  svg .axis line, svg .axis path { stroke: var(--border); }
  svg .bar { rx: 2; }
  svg .dot { stroke: var(--bg); stroke-width: 1; }

  /* Layout helpers */
  .split { display: flex; gap: 16px; }
  .split-left { width: 220px; flex-shrink: 0; }
  .split-right { flex: 1; min-width: 0; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
</head>
<body>
<div id="header">
  <span class="title">SideQuest OTEL</span>
  <span class="dot" id="dot">●</span>
  <span id="conn-status" style="color:var(--muted);font-size:12px">Connecting...</span>
  <span class="stat">Turns: <b id="hdr-turns">0</b></span>
  <span class="stat">Errors: <b id="hdr-errors">0</b></span>
  <span class="stat">p95: <b id="hdr-p95">—</b></span>
  <button onclick="togglePause()">Pause</button>
  <button onclick="clearAll()">Clear</button>
</div>
<div id="tabs">
  <div class="tab active" onclick="switchTab(0)">① Timeline <span class="badge" id="tab0-badge">0</span></div>
  <div class="tab" onclick="switchTab(1)">② State</div>
  <div class="tab" onclick="switchTab(2)">③ Subsystems <span class="badge" id="tab2-badge"></span></div>
  <div class="tab" onclick="switchTab(3)">④ Timing</div>
  <div class="tab" onclick="switchTab(4)">⑤ Console <span class="badge" id="tab4-badge">0</span></div>
</div>

<!-- Tab 0: Timeline / Flame Chart -->
<div class="tab-content active" id="tc0">
  <div class="split">
    <div class="split-left">
      <div class="card"><div class="card-title">Turns</div><div class="turn-list" id="turn-list"></div></div>
    </div>
    <div class="split-right">
      <div class="card" id="flame-card">
        <div class="card-title" id="flame-title">Select a turn</div>
        <div id="flame-chart"></div>
      </div>
      <div class="card" id="turn-meta" style="display:none">
        <div class="card-title">Turn Details</div>
        <div id="turn-meta-body"></div>
      </div>
    </div>
  </div>
</div>

<!-- Tab 1: Game State Explorer -->
<div class="tab-content" id="tc1">
  <div id="state-body" style="color:var(--muted)">Waiting for GameStateSnapshot event...</div>
</div>

<!-- Tab 2: Subsystem Health -->
<div class="tab-content" id="tc2">
  <div class="card"><div class="card-title">Activity Grid (last 20 turns)</div><div id="health-grid"></div></div>
  <div class="card"><div class="card-title">Component Summary</div><div id="health-table"></div></div>
  <div class="card" id="comp-detail" style="display:none"><div class="card-title" id="comp-detail-title"></div><div id="comp-detail-body"></div></div>
</div>

<!-- Tab 3: Timing Analysis -->
<div class="tab-content" id="tc3">
  <div class="stats-row" id="timing-summary"></div>
  <div class="grid-2">
    <div class="card"><div class="card-title">Agent Duration Histogram</div><div class="chart-container" id="hist-chart"></div></div>
    <div class="card"><div class="card-title">Per-Agent Breakdown</div><div id="agent-breakdown"></div></div>
  </div>
  <div class="card"><div class="card-title">Turn Duration Over Time</div><div class="chart-container" id="scatter-chart"></div></div>
  <div class="grid-2">
    <div class="card"><div class="card-title">Token Usage (in/out per turn)</div><div class="chart-container" id="token-chart"></div></div>
    <div class="card"><div class="card-title">Extraction Tier Distribution</div><div class="chart-container" id="tier-chart"></div></div>
  </div>
</div>

<!-- Tab 4: Console (raw event log) -->
<div class="tab-content" id="tc4">
  <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
    <span style="color:var(--muted);font-size:11px">Filter:</span>
    <select id="console-comp-filter" onchange="renderConsole()" style="background:var(--surface);color:var(--text);border:1px solid var(--border);padding:2px 6px;font-size:11px;font-family:inherit">
      <option value="">All components</option>
    </select>
    <select id="console-type-filter" onchange="renderConsole()" style="background:var(--surface);color:var(--text);border:1px solid var(--border);padding:2px 6px;font-size:11px;font-family:inherit">
      <option value="">All types</option>
    </select>
    <label style="color:var(--muted);font-size:11px"><input type="checkbox" id="console-auto-scroll" checked> Auto-scroll</label>
  </div>
  <div class="card" style="max-height:calc(100vh - 150px);overflow-y:auto;padding:4px" id="console-log"></div>
</div>

<script>
// ── State ──
const S = {
  turns: [], allEvents: [], componentMap: {}, latestSnapshot: null,
  selectedTurn: null, paused: false, activeTab: 0
};

const SPAN_COLORS = {
  prompt_build:'#4fc3f7', barrier:'#ffcc02', preprocess:'#03dac6',
  agent_llm:'#bb86fc', state_update:'#81c784', system_tick:'#f06292',
  media:'#e57373', persist:'#80cbc4',
  // Legacy / subsystem fallbacks
  preprocessor:'#03dac6', intent_route:'#4fc3f7', state_patch:'#ffb74d',
  extraction:'#81c784', broadcast:'#90a4ae', music_director:'#f06292',
  render_pipeline:'#e57373', tts_pipeline:'#ce93d8', prerender_scheduler:'#80cbc4'
};
const COMP_COLORS = {
  game:'#4fc3f7', agent:'#bb86fc', state:'#81c784', trope:'#ffb74d',
  combat:'#e57373', music_director:'#f06292', multiplayer:'#ce93d8',
  orchestrator:'#03dac6'
};
const AGENT_COLORS = { narrator:'#bb86fc', creature_smith:'#e57373', ensemble:'#81c784', dialectician:'#4fc3f7' };

function esc(s) { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

// ── Tab switching ──
function switchTab(i) {
  document.querySelectorAll('.tab').forEach((t,j) => t.classList.toggle('active', j===i));
  document.querySelectorAll('.tab-content').forEach((t,j) => t.classList.toggle('active', j===i));
  S.activeTab = i;
  if (i===2) renderHealth();
  if (i===3) renderTiming();
  if (i===4) renderConsole();
}
function togglePause() { S.paused = !S.paused; }
function clearAll() { S.turns.length=0; S.allEvents.length=0; Object.keys(S.componentMap).forEach(k=>delete S.componentMap[k]); S.selectedTurn=null; updateAll(); }

// ── Header update ──
function updateHeader() {
  document.getElementById('hdr-turns').textContent = S.turns.length;
  document.getElementById('hdr-errors').textContent = S.allEvents.filter(e=>(e.severity||'info')==='error').length;
  const durs = S.turns.map(t=>t.fields.agent_duration_ms||0).filter(d=>d>0).sort((a,b)=>a-b);
  const p95 = durs.length ? (durs[Math.floor(durs.length*0.95)] / 1000).toFixed(1) + 's' : '—';
  document.getElementById('hdr-p95').textContent = p95;
  document.getElementById('tab0-badge').textContent = S.turns.length;
  const errs = S.allEvents.filter(e=>(e.severity||'info')==='error').length;
  const b2 = document.getElementById('tab2-badge');
  if (errs > 0) { b2.textContent = errs; b2.className = 'badge err'; } else { b2.textContent = ''; b2.className = 'badge'; }
}

// ── Event dispatch ──
function dispatch(ev) {
  if (S.paused) return;
  S.allEvents.push(ev);
  const comp = ev.component || 'unknown';
  if (!S.componentMap[comp]) S.componentMap[comp] = [];
  S.componentMap[comp].push(ev);

  if (ev.event_type === 'turn_complete') {
    S.turns.push(ev);
    if (S.activeTab === 0) { renderTurnList(); if (!S.selectedTurn) selectTurn(S.turns.length - 1); }
  }
  if (ev.event_type === 'game_state_snapshot') {
    S.latestSnapshot = ev.fields.snapshot || ev.fields;
    if (S.activeTab === 1) renderState();
  }
  updateHeader();
  if (S.activeTab === 0 && ev.event_type === 'turn_complete') renderTurnList();
  if (S.activeTab === 4) renderConsole();
}

// ── Tab 0: Timeline ──
function renderTurnList() {
  const el = document.getElementById('turn-list');
  el.innerHTML = S.turns.map((t, i) => {
    const f = t.fields || {};
    const dur = ((f.agent_duration_ms||0)/1000).toFixed(1);
    const agent = f.agent_name || '?';
    const sel = S.selectedTurn === i ? ' selected' : '';
    let badge = '';
    if (f.is_degraded) badge = '<span class="ti-badge ti-degraded">DEGRADED</span>';
    else if ((f.classified_intent||'') === 'Combat') badge = '<span class="ti-badge ti-combat">COMBAT</span>';
    return `<div class="turn-item${sel}" onclick="selectTurn(${i})">#${f.turn_id||i+1} ${esc(agent)} ${dur}s ${badge}</div>`;
  }).reverse().join('');
}

function selectTurn(i) {
  S.selectedTurn = i;
  renderTurnList();
  const t = S.turns[i];
  if (!t) return;
  const f = t.fields || {};
  const dur = f.total_duration_ms || f.agent_duration_ms || 1;

  // Flame chart
  document.getElementById('flame-title').textContent = `Turn ${f.turn_id||'?'} · ${f.classified_intent||'?'} → ${f.agent_name||'?'} · ${(dur/1000).toFixed(1)}s`;

  const spans = f.spans || [
    { name: 'agent_llm', component: f.agent_name||'narrator', start_ms: 0, duration_ms: dur }
  ];

  const fc = document.getElementById('flame-chart');
  fc.innerHTML = '';
  const total = Math.max(dur, ...spans.map(s=>(s.start_ms||0)+(s.duration_ms||0)));
  spans.forEach(s => {
    const pctLeft = total > 0 ? ((s.start_ms||0)/total*100) : 0;
    const pctW = total > 0 ? (Math.max(s.duration_ms||1, 1)/total*100) : 100;
    const color = SPAN_COLORS[s.name] || SPAN_COLORS[s.component] || '#666';
    fc.innerHTML += `<div class="flame-row">
      <div class="flame-label">${esc(s.name||s.component)}</div>
      <div class="flame-bar-wrap"><div class="flame-bar" style="left:${pctLeft}%;width:${pctW}%;background:${color}" title="${s.name}: ${s.duration_ms}ms">${s.duration_ms>50?s.duration_ms+'ms':''}</div></div>
      <div class="flame-dur">${s.duration_ms}ms</div>
    </div>`;
  });
  // Axis
  fc.innerHTML += `<div style="display:flex;justify-content:space-between;color:var(--muted);font-size:10px;margin-top:4px;padding-left:118px"><span>0ms</span><span>${Math.round(total/2)}ms</span><span>${total}ms</span></div>`;

  // Meta
  const meta = document.getElementById('turn-meta');
  meta.style.display = 'block';
  const patches = (f.patches||[]).map(p=>`${p.patch_type}(${(p.fields_changed||[]).join(',')})`).join(', ') || 'none';
  const beats = (f.beats_fired||[]).map(b=>`${b.trope}@${(b.threshold||0).toFixed(1)}`).join(', ') || 'none';
  document.getElementById('turn-meta-body').innerHTML = `
    <div style="color:var(--muted);font-size:12px;line-height:1.8">
    · <b>Input:</b> ${esc(f.player_input||'')}
    <br>· <b>Intent:</b> ${f.classified_intent||'?'} &rarr; <b>Agent:</b> ${f.agent_name||'?'}
    <br>· <b>Tokens:</b> ${f.token_count_in||0} in / ${f.token_count_out||0} out &nbsp; <b>Tier:</b> ${f.extraction_tier||'?'} &nbsp; <b>Degraded:</b> ${f.is_degraded?'<span style="color:var(--red)">YES</span>':'no'}
    <br>· <b>Patches:</b> ${esc(patches)}
    <br>· <b>Beats:</b> ${esc(beats)}
    <br>· <b>Delta empty:</b> ${f.delta_empty}
    </div>`;
}

// ── Tab 1: State ──
function renderState() {
  const el = document.getElementById('state-body');
  const s = S.latestSnapshot;
  if (!s) { el.innerHTML = '<span style="color:var(--muted)">Waiting for GameStateSnapshot...</span>'; return; }

  let html = '';

  // Location & World
  html += `<div class="card"><div class="card-title">Location</div>
    <div style="font-size:14px;color:var(--accent);margin-bottom:4px">${esc(s.location || 'Unknown')}</div>
    <div style="font-size:11px;color:var(--muted)">${esc(s.genre_slug||'')} / ${esc(s.world_slug||'')}${s.current_region ? ' · Region: '+esc(s.current_region) : ''}${s.time_of_day ? ' · '+esc(s.time_of_day) : ''}</div>
    ${(s.discovered_regions||[]).length ? '<div style="margin-top:6px;font-size:11px;color:var(--muted)">Discovered: '+(s.discovered_regions||[]).map(r=>'<span style="color:var(--teal)">'+esc(r)+'</span>').join(', ')+'</div>' : ''}
  </div>`;

  // Characters
  (s.characters || []).forEach(c => {
    const hpPct = c.max_hp ? Math.round(c.hp / c.max_hp * 100) : 100;
    const hpColor = hpPct > 60 ? 'var(--green)' : hpPct > 30 ? 'var(--amber)' : 'var(--red)';
    const items = (c.inventory?.items || []);
    const gold = c.inventory?.gold || 0;
    const facts = c.known_facts || [];
    const stats = c.stats ? Object.entries(c.stats).map(([k,v])=>`${k}:${v}`).join(' · ') : '';

    html += `<div class="card"><div class="card-title">${esc(c.name)} — ${esc(c.race||'')} ${esc(c.char_class||'')} (Lv${c.level||1})</div>
      <div style="display:flex;gap:24px;align-items:center;margin-bottom:8px">
        <div>HP: <span style="color:${hpColor};font-weight:bold">${c.hp}/${c.max_hp}</span></div>
        <div style="flex:1;max-width:200px;height:6px;background:var(--border);border-radius:3px"><div style="width:${hpPct}%;height:100%;background:${hpColor};border-radius:3px"></div></div>
        ${c.pronouns ? '<div style="color:var(--muted);font-size:11px">'+esc(c.pronouns)+'</div>' : ''}
        ${gold > 0 ? '<div style="color:var(--amber)">'+gold+' gold</div>' : ''}
      </div>
      ${stats ? '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">'+esc(stats)+'</div>' : ''}`;

    // Inventory
    if (items.length) {
      html += '<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--purple);margin-bottom:4px;font-weight:bold">INVENTORY</div><table style="width:100%;font-size:11px;border-collapse:collapse">';
      html += '<tr style="color:var(--muted)"><th style="text-align:left;padding:2px 8px">Item</th><th style="text-align:left;padding:2px 8px">Weight</th><th style="text-align:left;padding:2px 8px">Stage</th></tr>';
      items.forEach(item => {
        const w = item.narrative_weight || 0;
        const stage = w >= 0.7 ? '<span style="color:var(--accent)">evolved</span>' : w >= 0.5 ? '<span style="color:var(--green)">named</span>' : '<span style="color:var(--muted)">unnamed</span>';
        html += `<tr><td style="padding:2px 8px">${esc(item.name||item)}</td><td style="padding:2px 8px">${w.toFixed(2)}</td><td style="padding:2px 8px">${stage}</td></tr>`;
      });
      html += '</table></div>';
    }

    // Known Facts
    if (facts.length) {
      html += '<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--purple);margin-bottom:4px;font-weight:bold">KNOWN FACTS (' + facts.length + ')</div>';
      facts.forEach(f => {
        const srcColor = f.source === 'Backstory' ? 'var(--pink)' : f.source === 'Discovery' ? 'var(--teal)' : 'var(--muted)';
        html += `<div style="font-size:11px;padding:3px 0;border-bottom:1px solid var(--border)"><span style="color:${srcColor};font-size:10px">[${esc(f.source||'?')} T${f.learned_turn||'?'}]</span> ${esc(f.content)}</div>`;
      });
      html += '</div>';
    }

    html += '</div>';
  });

  // NPC Registry
  const npcs = s.npc_registry || [];
  if (npcs.length) {
    html += '<div class="card"><div class="card-title">NPC Registry (' + npcs.length + ')</div>';
    html += '<table style="width:100%;font-size:11px;border-collapse:collapse">';
    html += '<tr style="color:var(--muted)"><th style="text-align:left;padding:4px 8px">Name</th><th style="text-align:left;padding:4px 8px">Role</th><th style="text-align:left;padding:4px 8px">Location</th><th style="text-align:left;padding:4px 8px">Last Seen</th><th style="text-align:left;padding:4px 8px">Pronouns</th></tr>';
    npcs.forEach(n => {
      html += `<tr><td style="padding:4px 8px;color:var(--text)">${esc(n.name)}</td><td style="padding:4px 8px;color:var(--muted)">${esc(n.role||'')}</td><td style="padding:4px 8px;color:var(--teal)">${esc(n.location||'')}</td><td style="padding:4px 8px;color:var(--muted)">T${n.last_seen_turn||'?'}</td><td style="padding:4px 8px;color:var(--muted)">${esc(n.pronouns||'')}</td></tr>`;
    });
    html += '</table></div>';
  }

  // Active Tropes
  const tropes = s.active_tropes || [];
  if (tropes.length) {
    html += '<div class="card"><div class="card-title">Active Tropes (' + tropes.length + ')</div>';
    tropes.forEach(t => {
      const pct = Math.round((t.progression || 0) * 100);
      const beats = (t.fired_beats || []).length;
      html += `<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;font-size:11px">
        <span style="color:var(--amber);min-width:140px">${esc(t.trope_definition_id)}</span>
        <span style="color:var(--muted)">${esc(t.status||'?')}</span>
        <div style="flex:1;max-width:120px;height:4px;background:var(--border);border-radius:2px"><div style="width:${pct}%;height:100%;background:var(--amber);border-radius:2px"></div></div>
        <span style="color:var(--muted)">${pct}%</span>
        ${beats ? '<span style="color:var(--muted)">'+beats+' beats</span>' : ''}
      </div>`;
    });
    html += '</div>';
  }

  // Quest Log
  const quests = Object.entries(s.quest_log || {});
  if (quests.length) {
    html += '<div class="card"><div class="card-title">Quest Log</div>';
    quests.forEach(([name, desc]) => {
      html += `<div style="font-size:11px;margin-bottom:4px"><span style="color:var(--green);font-weight:bold">${esc(name)}</span> — ${esc(desc)}</div>`;
    });
    html += '</div>';
  }

  // Raw JSON (collapsible)
  html += `<div class="card"><div class="card-title" style="cursor:pointer" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">Raw JSON ▸</div>
    <pre style="white-space:pre-wrap;font-size:10px;max-height:400px;overflow:auto;display:none">${esc(JSON.stringify(s, null, 2))}</pre>
  </div>`;

  el.innerHTML = html;
}

// ── Tab 2: Health ──
function renderHealth() {
  const comps = Object.keys(S.componentMap).sort();
  const turnIds = S.turns.map(t => t.fields?.turn_id || 0);
  const last20 = turnIds.slice(-20);

  // Build per-component per-turn severity map
  const grid = {};
  comps.forEach(c => { grid[c] = {}; });
  S.allEvents.forEach(ev => {
    const c = ev.component || 'unknown';
    const tid = ev.fields?.turn_number || ev.fields?.turn_id || 0;
    if (!grid[c]) grid[c] = {};
    const cur = grid[c][tid] || 'info';
    const sev = ev.severity || 'info';
    if (sev === 'error' || (sev === 'warn' && cur !== 'error')) grid[c][tid] = sev;
    else if (!grid[c][tid]) grid[c][tid] = sev;
  });

  const cols = last20.length || 1;
  const el = document.getElementById('health-grid');
  let html = `<div class="health-grid" style="grid-template-columns: 130px repeat(${cols}, 24px) auto">`;
  // Header
  html += `<div class="hg-label"></div>`;
  last20.forEach(t => { html += `<div class="hg-cell" style="color:var(--muted);font-size:9px">${t}</div>`; });
  html += '<div></div>';

  comps.forEach(c => {
    html += `<div class="hg-label" style="cursor:pointer" onclick="showCompDetail('${esc(c)}')">${esc(c)}</div>`;
    const lastSeen = Math.max(...Object.keys(grid[c]).map(Number).filter(n=>n>0), 0);
    const maxTurn = last20.length ? last20[last20.length-1] : 0;
    last20.forEach(tid => {
      const sev = grid[c][tid];
      if (!sev) html += '<div class="hg-cell hg-empty">·</div>';
      else if (sev === 'error') html += '<div class="hg-cell hg-err">✗</div>';
      else if (sev === 'warn') html += '<div class="hg-cell hg-warn">⚠</div>';
      else html += '<div class="hg-cell hg-ok">●</div>';
    });
    const gap = maxTurn - lastSeen;
    html += gap > 5 ? `<div class="hg-silent">SILENT ${gap}t</div>` : '<div></div>';
  });
  html += '</div>';
  el.innerHTML = html;

  // Summary table
  const tbl = document.getElementById('health-table');
  let t = '<table style="width:100%;font-size:11px;border-collapse:collapse"><tr style="color:var(--muted)"><th style="text-align:left;padding:4px">Component</th><th>Events</th><th>Errors</th><th>Warns</th><th>Last Seen</th></tr>';
  comps.forEach(c => {
    const evts = S.componentMap[c] || [];
    const errs = evts.filter(e=>(e.severity||'info')==='error').length;
    const warns = evts.filter(e=>(e.severity||'info')==='warn').length;
    const last = Math.max(...evts.map(e=>e.fields?.turn_number||e.fields?.turn_id||0).filter(n=>n>0), 0);
    t += `<tr style="border-top:1px solid var(--border);cursor:pointer" onclick="showCompDetail('${esc(c)}')"><td style="padding:4px">${esc(c)}</td><td style="text-align:center">${evts.length}</td><td style="text-align:center;color:${errs?'var(--red)':'inherit'}">${errs}</td><td style="text-align:center;color:${warns?'var(--amber)':'inherit'}">${warns}</td><td style="text-align:center">T#${last}</td></tr>`;
  });
  t += '</table>';
  tbl.innerHTML = t;
}

function showCompDetail(comp) {
  const el = document.getElementById('comp-detail');
  el.style.display = 'block';
  document.getElementById('comp-detail-title').textContent = comp;
  const evts = (S.componentMap[comp] || []).slice(-20);
  document.getElementById('comp-detail-body').innerHTML = evts.map(e => {
    const sev = e.severity || 'info';
    const fields = Object.entries(e.fields||{}).filter(([k])=>k!=='timestamp').map(([k,v])=>`${k}=${typeof v==='string'?v:JSON.stringify(v)}`).join(', ');
    return `<div class="evt-row"><span class="comp">[${esc(e.component)}]</span> <span class="etype">${esc(e.event_type)}</span> ${esc(fields)}</div>`;
  }).join('');
}

// ── Tab 3: Timing ──
function renderTiming() {
  if (!S.turns.length) return;
  const durs = S.turns.map(t => t.fields?.agent_duration_ms || 0);
  const sorted = [...durs].sort((a,b) => a-b);
  const p = (pct) => sorted.length ? (sorted[Math.min(Math.floor(sorted.length*pct), sorted.length-1)]/1000).toFixed(1) : '?';
  const degraded = S.turns.filter(t => t.fields?.is_degraded).length;

  // Summary
  document.getElementById('timing-summary').innerHTML = [
    ['p50', p(0.5)+'s'], ['p95', p(0.95)+'s'], ['p99', p(0.99)+'s'],
    ['Degraded', `${degraded}/${S.turns.length} (${S.turns.length?(degraded/S.turns.length*100).toFixed(0):0}%)`]
  ].map(([l,v]) => `<div class="stat-card"><div class="stat-val">${v}</div><div class="stat-lbl">${l}</div></div>`).join('');

  // Agent breakdown
  const byAgent = {};
  S.turns.forEach(t => {
    const a = t.fields?.agent_name || '?';
    if (!byAgent[a]) byAgent[a] = [];
    byAgent[a].push(t.fields?.agent_duration_ms || 0);
  });
  document.getElementById('agent-breakdown').innerHTML = Object.entries(byAgent).map(([a, ds]) => {
    const avg = (ds.reduce((s,d)=>s+d,0)/ds.length/1000).toFixed(1);
    const color = AGENT_COLORS[a] || 'var(--accent)';
    return `<div style="padding:4px 0;font-size:12px"><span style="color:${color}">■</span> ${esc(a)} &mdash; avg: ${avg}s (${ds.length} turns)</div>`;
  }).join('');

  // Histogram (D3)
  renderHistogramD3();
  // Scatter
  renderScatterD3();
  // Token bars
  renderTokenBars();
  // Tier donut
  renderTierDonut();
}

function renderHistogramD3() {
  const el = document.getElementById('hist-chart');
  el.innerHTML = '';
  const w = el.clientWidth || 400, h = 180, m = {t:10,r:20,b:30,l:40};
  const durs = S.turns.map(t => (t.fields?.agent_duration_ms||0)/1000);
  if (!durs.length) return;
  const svg = d3.select(el).append('svg').attr('width',w).attr('height',h);
  const x = d3.scaleLinear().domain([0, d3.max(durs)*1.1]).range([m.l, w-m.r]);
  const bins = d3.bin().domain(x.domain()).thresholds(x.ticks(15))(durs);
  const y = d3.scaleLinear().domain([0, d3.max(bins, d=>d.length)]).range([h-m.b, m.t]);
  svg.append('g').attr('transform',`translate(0,${h-m.b})`).call(d3.axisBottom(x).ticks(6).tickFormat(d=>d+'s')).attr('class','axis');
  svg.append('g').attr('transform',`translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4)).attr('class','axis');
  svg.selectAll('.bar').data(bins).join('rect').attr('class','bar')
    .attr('x', d=>x(d.x0)+1).attr('y', d=>y(d.length))
    .attr('width', d=>Math.max(0,x(d.x1)-x(d.x0)-2))
    .attr('height', d=>y(0)-y(d.length))
    .attr('fill','#bb86fc');
}

function renderScatterD3() {
  const el = document.getElementById('scatter-chart');
  el.innerHTML = '';
  const w = el.clientWidth || 600, h = 180, m = {t:10,r:20,b:30,l:50};
  const data = S.turns.map((t,i) => ({i, dur:(t.fields?.agent_duration_ms||0)/1000, agent:t.fields?.agent_name||'?', degraded:t.fields?.is_degraded}));
  if (!data.length) return;
  const svg = d3.select(el).append('svg').attr('width',w).attr('height',h);
  const x = d3.scaleLinear().domain([0, data.length]).range([m.l, w-m.r]);
  const y = d3.scaleLinear().domain([0, d3.max(data,d=>d.dur)*1.1]).range([h-m.b, m.t]);
  svg.append('g').attr('transform',`translate(0,${h-m.b})`).call(d3.axisBottom(x).ticks(Math.min(data.length,10)).tickFormat(d=>'T'+(d+1))).attr('class','axis');
  svg.append('g').attr('transform',`translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(d=>d+'s')).attr('class','axis');
  svg.selectAll('.dot').data(data).join('circle').attr('class','dot')
    .attr('cx', d=>x(d.i)).attr('cy', d=>y(d.dur)).attr('r', 5)
    .attr('fill', d=>d.degraded?'#f44336':(AGENT_COLORS[d.agent]||'#00d4ff'));
  // Moving average
  if (data.length >= 3) {
    const win = 3;
    const avg = data.map((d,i) => {
      const slice = data.slice(Math.max(0,i-win+1),i+1);
      return {i:d.i, dur: slice.reduce((s,d)=>s+d.dur,0)/slice.length};
    });
    const line = d3.line().x(d=>x(d.i)).y(d=>y(d.dur)).curve(d3.curveMonotoneX);
    svg.append('path').datum(avg).attr('d',line).attr('fill','none').attr('stroke','rgba(255,255,255,0.3)').attr('stroke-width',1.5);
  }
}

function renderTokenBars() {
  const el = document.getElementById('token-chart');
  el.innerHTML = '';
  const w = el.clientWidth || 400, h = 140, m = {t:10,r:20,b:30,l:50};
  const data = S.turns.map((t,i) => ({i, tin:t.fields?.token_count_in||0, tout:t.fields?.token_count_out||0}));
  if (!data.length) return;
  const svg = d3.select(el).append('svg').attr('width',w).attr('height',h);
  const x = d3.scaleBand().domain(data.map(d=>d.i)).range([m.l,w-m.r]).padding(0.3);
  const maxT = d3.max(data, d=>Math.max(d.tin,d.tout)) || 1;
  const y = d3.scaleLinear().domain([0,maxT]).range([h-m.b,m.t]);
  svg.append('g').attr('transform',`translate(0,${h-m.b})`).call(d3.axisBottom(x).tickFormat(d=>'T'+(d+1))).attr('class','axis');
  svg.append('g').attr('transform',`translate(${m.l},0)`).call(d3.axisLeft(y).ticks(3)).attr('class','axis');
  const bw = x.bandwidth()/2;
  svg.selectAll('.bin').data(data).join('rect').attr('x',d=>x(d.i)).attr('y',d=>y(d.tin)).attr('width',bw).attr('height',d=>y(0)-y(d.tin)).attr('fill','#4fc3f7').attr('rx',1);
  svg.selectAll('.bout').data(data).join('rect').attr('x',d=>x(d.i)+bw).attr('y',d=>y(d.tout)).attr('width',bw).attr('height',d=>y(0)-y(d.tout)).attr('fill','#03dac6').attr('rx',1);
}

function renderTierDonut() {
  const el = document.getElementById('tier-chart');
  el.innerHTML = '';
  const tiers = {};
  S.turns.forEach(t => { const tier = t.fields?.extraction_tier ?? '?'; tiers[tier] = (tiers[tier]||0)+1; });
  const data = Object.entries(tiers).map(([k,v])=>({label:'Tier '+k, value:v}));
  if (!data.length) return;
  const w = 180, h = 180, r = 70;
  const svg = d3.select(el).append('svg').attr('width',w).attr('height',h);
  const g = svg.append('g').attr('transform',`translate(${w/2},${h/2})`);
  const color = d3.scaleOrdinal(['#4caf50','#ff9800','#f44336','#bb86fc']);
  const pie = d3.pie().value(d=>d.value);
  const arc = d3.arc().innerRadius(r*0.5).outerRadius(r);
  g.selectAll('path').data(pie(data)).join('path').attr('d',arc).attr('fill',(_,i)=>color(i));
  g.selectAll('text').data(pie(data)).join('text').attr('transform',d=>`translate(${arc.centroid(d)})`)
    .attr('text-anchor','middle').attr('font-size','10px').text(d=>d.data.label+' ('+d.data.value+')');
}

function renderConsole() {
  const el = document.getElementById('console-log');
  const compFilter = document.getElementById('console-comp-filter').value;
  const typeFilter = document.getElementById('console-type-filter').value;
  let evts = S.allEvents;
  if (compFilter) evts = evts.filter(e=>e.component===compFilter);
  if (typeFilter) evts = evts.filter(e=>e.event_type===typeFilter);
  const last200 = evts.slice(-200);
  el.innerHTML = last200.map(e => {
    const sev = e.severity || 'info';
    const sevColor = sev==='error'?'var(--red)':sev==='warn'?'var(--amber)':'inherit';
    const compColor = COMP_COLORS[e.component] || 'var(--purple)';
    const fields = Object.entries(e.fields||{})
      .filter(([k])=>!['turn_number','turn_id'].includes(k))
      .map(([k,v])=>`<span style="color:var(--muted)">${esc(k)}</span>=<span style="color:var(--sky)">${typeof v==='string'?esc(v):esc(JSON.stringify(v))}</span>`)
      .join(' ');
    const turn = e.fields?.turn_number || e.fields?.turn_id || '';
    return `<div class="evt-row" style="border-left-color:${compColor};color:${sevColor}">` +
      `<span style="color:var(--muted);font-size:10px">${turn?'T'+turn+' ':''}</span>` +
      `<span style="color:${compColor}">[${esc(e.component)}]</span> ` +
      `<span style="color:var(--teal)">${esc(e.event_type)}</span> ${fields}</div>`;
  }).join('');
  document.getElementById('tab4-badge').textContent = S.allEvents.length;
  // Update filter dropdowns with known values
  const compSel = document.getElementById('console-comp-filter');
  const knownComps = new Set(compSel.querySelectorAll('option').values().map(o=>o.value).filter(Boolean));
  Object.keys(S.componentMap).sort().forEach(c => {
    if (!knownComps.has(c)) { const o = document.createElement('option'); o.value=c; o.textContent=c; compSel.appendChild(o); }
  });
  if (document.getElementById('console-auto-scroll').checked) el.scrollTop = el.scrollHeight;
}
function updateAll() { updateHeader(); renderTurnList(); if(S.activeTab===2)renderHealth(); if(S.activeTab===3)renderTiming(); if(S.activeTab===4)renderConsole(); }

// ── WebSocket ──
function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.onopen = () => { document.getElementById('dot').classList.add('on'); document.getElementById('conn-status').textContent='Connected'; };
  ws.onmessage = (e) => { try { dispatch(JSON.parse(e.data)); } catch {} };
  ws.onclose = () => { document.getElementById('dot').classList.remove('on'); document.getElementById('conn-status').textContent='Reconnecting...'; setTimeout(connect, 2000); };
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
    async with websockets.serve(_dashboard_handler, "0.0.0.0", ws_port, ping_timeout=None):
        console.print(
            f"[bold green]OTEL Dashboard: http://localhost:{dashboard_port}/[/bold green]"
            f"[dim] (ws: :{ws_port})[/dim]"
        )
        # Connect to API watcher and proxy events
        api_uri = f"ws://{api_host}:{api_port}/ws/watcher"
        while True:
            try:
                async with websockets.connect(api_uri, ping_timeout=None) as ws:
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
                    state["chargen_prompt"].set()  # unblock loop to re-check has_character
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

                # Wait for either the next scene prompt or character complete
                # chargen_prompt fires for scene/confirmation, chargen_done fires for complete
                state["chargen_prompt"].clear()
                done_task = asyncio.create_task(state["chargen_done"].wait())
                prompt_task = asyncio.create_task(state["chargen_prompt"].wait())
                await asyncio.wait(
                    [done_task, prompt_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                # Cancel the loser
                done_task.cancel()
                prompt_task.cancel()

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

                state["chargen_prompt"].clear()
                done_task = asyncio.create_task(state["chargen_done"].wait())
                prompt_task = asyncio.create_task(state["chargen_prompt"].wait())
                await asyncio.wait(
                    [done_task, prompt_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                done_task.cancel()
                prompt_task.cancel()

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
                state["chargen_prompt"].clear()
                done_task = asyncio.create_task(state["chargen_done"].wait())
                prompt_task = asyncio.create_task(state["chargen_prompt"].wait())
                await asyncio.wait(
                    [done_task, prompt_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                done_task.cancel()
                prompt_task.cancel()

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
