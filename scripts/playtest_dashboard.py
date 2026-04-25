"""playtest_dashboard.py — OTEL telemetry dashboard server.

Browser-based dashboard for game watcher telemetry.
Extracted from playtest.py (story 21-1).
"""

import asyncio

import websockets
from rich.console import Console

console = Console()

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
  <div class="tab" onclick="switchTab(5)">⑥ Prompt <span class="badge" id="tab5-badge">0</span></div>
  <div class="tab" onclick="switchTab(6)">⑦ Lore <span class="badge" id="tab6-badge">0</span></div>
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
  <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
    <span style="color:var(--muted);font-size:11px">Search:</span>
    <input id="state-filter" type="text" placeholder="Filter NPCs, items..." oninput="renderState()" style="background:var(--surface);color:var(--text);border:1px solid var(--border);padding:2px 6px;font-size:11px;font-family:inherit;width:200px">
  </div>
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

<!-- Tab 5: Prompt Inspector -->
<div class="tab-content" id="tc5">
  <div id="prompt-select-row" style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
    <span style="color:var(--muted);font-size:11px">Turn:</span>
    <select id="prompt-turn-select" onchange="renderPrompt()" style="background:var(--surface);color:var(--text);border:1px solid var(--border);padding:2px 6px;font-size:11px;font-family:inherit">
      <option value="">Select a turn</option>
    </select>
  </div>
  <div id="prompt-summary" class="card" style="display:none">
    <div class="card-title">Zone Breakdown</div>
    <div id="prompt-zones"></div>
  </div>
  <div id="prompt-detail" class="card" style="display:none">
    <div class="card-title">Full Prompt</div>
    <pre id="prompt-text" style="white-space:pre-wrap;word-break:break-word;color:var(--text);font-size:12px;max-height:calc(100vh - 300px);overflow-y:auto"></pre>
  </div>
</div>

<!-- Tab 6: Lore -->
<div class="tab-content" id="tc6">
  <div id="lore-select-row" style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
    <span style="color:var(--muted);font-size:11px">Turn:</span>
    <select id="lore-turn-select" onchange="renderLore()" style="background:var(--surface);color:var(--text);border:1px solid var(--border);padding:2px 6px;font-size:11px;font-family:inherit">
      <option value="">Select a turn</option>
    </select>
    <span style="color:var(--muted);font-size:11px;margin-left:8px">Filter:</span>
    <input id="lore-filter" type="text" placeholder="Search fragments..." oninput="renderLore()" style="background:var(--surface);color:var(--text);border:1px solid var(--border);padding:2px 6px;font-size:11px;font-family:inherit;width:200px">
  </div>
  <div id="lore-budget" class="card" style="display:none">
    <div class="card-title">Budget</div>
    <div id="lore-budget-body"></div>
  </div>
  <div id="lore-fragments" class="card" style="display:none">
    <div class="card-title">Fragments</div>
    <div id="lore-fragments-body" style="max-height:calc(100vh - 280px);overflow-y:auto"></div>
  </div>
</div>

<script>
// ── State ──
const S = {
  turns: [], allEvents: [], componentMap: {}, latestSnapshot: null,
  selectedTurn: null, paused: false, activeTab: 0, promptEvents: [], loreEvents: [],
  npcSort: { col: 'name', asc: true }, expandedNpcs: {}, expandedItems: {},
  _placeholder: null
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
  if (i===5) renderPrompt();
  if (i===6) renderLore();
  if (i===4) renderConsole();
  // Tab 7 (Claude) removed — ADR-059
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
  if (ev.event_type === 'prompt_assembled') {
    S.promptEvents.push(ev);
    document.getElementById('tab5-badge').textContent = S.promptEvents.length;
    // Update turn selector
    const sel = document.getElementById('prompt-turn-select');
    const f = ev.fields || {};
    const opt = document.createElement('option');
    opt.value = S.promptEvents.length - 1;
    opt.textContent = `T${f.turn_number||'?'} · ${f.agent||'?'} · ${f.total_tokens||0} tokens`;
    sel.appendChild(opt);
    if (S.activeTab === 5) renderPrompt();
  }
  if (ev.event_type === 'lore_retrieval') {
    S.loreEvents.push(ev);
    document.getElementById('tab6-badge').textContent = S.loreEvents.length;
    const sel = document.getElementById('lore-turn-select');
    const f = ev.fields || {};
    const opt = document.createElement('option');
    opt.value = S.loreEvents.length - 1;
    opt.textContent = `T${S.turns.length} · ${f.selected_count||0}/${f.total_fragments||0} frags · ${f.tokens_used||0}/${f.budget||0} tok`;
    sel.appendChild(opt);
    if (S.activeTab === 6) renderLore();
  }
  // Claude tab removed (ADR-059 — tool infrastructure replaced by Monster Manual)
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
  document.getElementById('flame-title').textContent = `Turn ${f.turn_id||'?'} → ${f.agent_name||'?'} · ${(dur/1000).toFixed(1)}s`;

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
    <br>· <b>Agent:</b> ${f.agent_name||'?'}
    <br>· <b>Tokens:</b> ${f.token_count_in||0} in / ${f.token_count_out||0} out &nbsp; <b>Tier:</b> ${f.extraction_tier||'?'} &nbsp; <b>Degraded:</b> ${f.is_degraded?'<span style="color:var(--red)">YES</span>':'no'}
    <br>· <b>Patches:</b> ${esc(patches)}
    <br>· <b>Beats:</b> ${esc(beats)}
    <br>· <b>Delta empty:</b> ${f.delta_empty}
    </div>`;
}

// ── Tab 1: State ──
function npcDispositionColor(d) {
  if (d > 10) return 'var(--green)';
  if (d < -10) return 'var(--red)';
  return 'var(--muted)';
}
function npcDispositionLabel(d) {
  if (d > 10) return 'Friendly';
  if (d < -10) return 'Hostile';
  return 'Neutral';
}
function sortNpcs(col) {
  if (S.npcSort.col === col) { S.npcSort.asc = !S.npcSort.asc; }
  else { S.npcSort.col = col; S.npcSort.asc = true; }
  renderState();
}
function toggleNpcExpand(name) {
  S.expandedNpcs[name] = !S.expandedNpcs[name];
  renderState();
}
function toggleItemExpand(charName, itemName) {
  const key = charName + '::' + itemName;
  S.expandedItems[key] = !S.expandedItems[key];
  renderState();
}

function renderState() {
  const el = document.getElementById('state-body');
  const s = S.latestSnapshot;
  if (!s) { el.innerHTML = '<span style="color:var(--muted)">Waiting for GameStateSnapshot...</span>'; return; }

  const filter = (document.getElementById('state-filter').value || '').toLowerCase();
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

    // Filter: if searching, only show characters with matching items
    const filteredItems = filter ? items.filter(item => (item.name||'').toLowerCase().includes(filter)) : items;
    if (filter && filteredItems.length === 0) return; // skip character if no matching items

    html += `<div class="card"><div class="card-title">${esc(c.name)} — ${esc(c.race||'')} ${esc(c.char_class||'')} (Lv${c.level||1})</div>
      <div style="display:flex;gap:24px;align-items:center;margin-bottom:8px">
        <div>HP: <span style="color:${hpColor};font-weight:bold">${c.hp}/${c.max_hp}</span></div>
        <div style="flex:1;max-width:200px;height:6px;background:var(--border);border-radius:3px"><div style="width:${hpPct}%;height:100%;background:${hpColor};border-radius:3px"></div></div>
        ${c.pronouns ? '<div style="color:var(--muted);font-size:11px">'+esc(c.pronouns)+'</div>' : ''}
        ${gold > 0 ? '<div style="color:var(--amber)">'+gold+' gold</div>' : ''}
      </div>
      ${stats ? '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">'+esc(stats)+'</div>' : ''}`;

    // Inventory — clickable rows with expansion
    if (filteredItems.length) {
      html += '<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--purple);margin-bottom:4px;font-weight:bold">INVENTORY</div><table style="width:100%;font-size:11px;border-collapse:collapse">';
      html += '<tr style="color:var(--muted)"><th style="text-align:left;padding:2px 8px">Item</th><th style="text-align:left;padding:2px 8px">Weight</th><th style="text-align:left;padding:2px 8px">Stage</th><th style="text-align:left;padding:2px 8px">Description</th></tr>';
      filteredItems.forEach(item => {
        const w = item.narrative_weight || 0;
        const stage = w >= 0.7 ? '<span style="color:var(--accent)">evolved</span>' : w >= 0.5 ? '<span style="color:var(--green)">named</span>' : '<span style="color:var(--muted)">unnamed</span>';
        const itemKey = esc(c.name) + '::' + esc(item.name||item);
        const expanded = S.expandedItems[c.name + '::' + (item.name||item)];
        const desc = item.description || '';
        const truncDesc = desc.length > 40 ? esc(desc.slice(0, 40)) + '…' : esc(desc);
        html += `<tr style="cursor:pointer" onclick="toggleItemExpand(${JSON.stringify(c.name)},${JSON.stringify(item.name||String(item))})"><td style="padding:2px 8px">${esc(item.name||item)}</td><td style="padding:2px 8px">${w.toFixed(2)}</td><td style="padding:2px 8px">${stage}</td><td style="padding:2px 8px;color:var(--muted)">${truncDesc}</td></tr>`;
        if (expanded) {
          html += `<tr><td colspan="4" style="padding:4px 8px"><pre style="white-space:pre-wrap;font-size:10px;color:var(--muted);margin:0">${esc(JSON.stringify(item, null, 2))}</pre></td></tr>`;
        }
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

  // NPC Registry — enriched with disposition + HP from s.npcs, sortable, expandable
  const registry = s.npc_registry || [];
  // Build lookup from full NPC data for enrichment
  const npcLookup = {};
  (s.npcs || []).forEach(n => { npcLookup[(n.name||'').toLowerCase()] = n; });
  // Enrich registry entries
  let enriched = registry.map(n => {
    const full = npcLookup[(n.name||'').toLowerCase()];
    return {
      name: n.name, role: n.role||'', location: n.location||'', last_seen_turn: n.last_seen_turn,
      pronouns: n.pronouns||'', age: n.age||'', appearance: n.appearance||'', ocean_summary: n.ocean_summary||'',
      disposition: full ? (typeof full.disposition === 'number' ? full.disposition : 0) : null,
      hp: full ? full.hp : null, max_hp: full ? full.max_hp : null,
      _full: full || n
    };
  });
  // Apply filter
  if (filter) {
    enriched = enriched.filter(n => n.name.toLowerCase().includes(filter) || n.role.toLowerCase().includes(filter) || n.location.toLowerCase().includes(filter));
  }
  // Apply sort
  const sortCol = S.npcSort.col;
  const sortAsc = S.npcSort.asc;
  enriched.sort((a, b) => {
    let va, vb;
    if (sortCol === 'disposition') { va = a.disposition ?? 0; vb = b.disposition ?? 0; }
    else if (sortCol === 'location') { va = a.location; vb = b.location; }
    else { va = a.name; vb = b.name; }
    if (typeof va === 'number') return sortAsc ? va - vb : vb - va;
    return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
  });

  if (enriched.length) {
    const arrow = (col) => S.npcSort.col === col ? (S.npcSort.asc ? ' ▲' : ' ▼') : '';
    html += '<div class="card"><div class="card-title">NPC Registry (' + enriched.length + ')</div>';
    html += '<table style="width:100%;font-size:11px;border-collapse:collapse">';
    html += `<tr style="color:var(--muted)"><th style="text-align:left;padding:4px 8px;cursor:pointer" onclick="sortNpcs('name')">Name${arrow('name')}</th><th style="text-align:left;padding:4px 8px">Role</th><th style="text-align:left;padding:4px 8px;cursor:pointer" onclick="sortNpcs('location')">Location${arrow('location')}</th><th style="text-align:left;padding:4px 8px;cursor:pointer" onclick="sortNpcs('disposition')">Disposition${arrow('disposition')}</th><th style="text-align:left;padding:4px 8px">HP</th><th style="text-align:left;padding:4px 8px">Last Seen</th><th style="text-align:left;padding:4px 8px">Pronouns</th></tr>`;
    enriched.forEach(n => {
      const dispVal = n.disposition;
      const dispColor = dispVal !== null ? npcDispositionColor(dispVal) : 'var(--muted)';
      const dispText = dispVal !== null ? npcDispositionLabel(dispVal) + ' (' + dispVal + ')' : '—';
      let hpHtml = '—';
      if (n.hp !== null && n.max_hp !== null) {
        const hpPct = n.max_hp > 0 ? Math.round(n.hp / n.max_hp * 100) : 100;
        const hpColor = hpPct > 60 ? 'var(--green)' : hpPct > 30 ? 'var(--amber)' : 'var(--red)';
        hpHtml = `<span style="color:${hpColor}">${n.hp}/${n.max_hp}</span>`;
      }
      const expanded = S.expandedNpcs[n.name];
      html += `<tr style="cursor:pointer;border-bottom:1px solid var(--border)" onclick="toggleNpcExpand(${JSON.stringify(n.name)})"><td style="padding:4px 8px;color:var(--text);font-weight:bold">${esc(n.name)}</td><td style="padding:4px 8px;color:var(--muted)">${esc(n.role)}</td><td style="padding:4px 8px;color:var(--teal)">${esc(n.location)}</td><td style="padding:4px 8px;color:${dispColor}">${dispText}</td><td style="padding:4px 8px">${hpHtml}</td><td style="padding:4px 8px;color:var(--muted)">T${n.last_seen_turn||'?'}</td><td style="padding:4px 8px;color:var(--muted)">${esc(n.pronouns)}</td></tr>`;
      if (expanded) {
        html += `<tr><td colspan="7" style="padding:8px"><pre style="white-space:pre-wrap;font-size:10px;color:var(--muted);margin:0">${esc(JSON.stringify(n._full, null, 2))}</pre></td></tr>`;
      }
    });
    html += '</table></div>';
  } else if (!filter) {
    html += '<div class="card"><div class="card-title">NPC Registry</div><div style="font-size:11px;color:var(--muted)">No NPCs in registry yet.</div></div>';
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
// ── Tab 5: Prompt Inspector ──
const ZONE_COLORS = { Primacy:'var(--accent)', Early:'var(--teal)', Valley:'var(--amber)', Late:'var(--pink)', Recency:'var(--purple)' };
function renderPrompt() {
  const sel = document.getElementById('prompt-turn-select');
  const idx = sel.value;
  if (idx === '' || !S.promptEvents[idx]) {
    document.getElementById('prompt-summary').style.display = 'none';
    document.getElementById('prompt-detail').style.display = 'none';
    return;
  }
  const ev = S.promptEvents[idx];
  const f = ev.fields || {};
  const zones = f.zones || [];
  const totalTokens = f.total_tokens || 0;

  // Zone breakdown bars
  const zonesHtml = zones.map(z => {
    const pct = totalTokens > 0 ? (z.total_tokens / totalTokens * 100) : 0;
    const color = ZONE_COLORS[z.zone] || 'var(--muted)';
    const sections = (z.sections || []).map(s =>
      `<div style="margin-left:24px;font-size:11px;color:var(--muted)">${esc(s.name)} <span style="color:var(--sky)">${s.token_estimate} tok</span> <span style="color:var(--border)">${s.category}</span></div>`
    ).join('');
    return `<div style="margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:8px">
        <span style="width:70px;text-align:right;color:${color};font-size:12px;font-weight:bold">${esc(z.zone)}</span>
        <div style="flex:1;background:var(--border);border-radius:2px;height:18px;position:relative">
          <div style="width:${pct}%;background:${color};height:100%;border-radius:2px;opacity:0.7"></div>
        </div>
        <span style="width:80px;font-size:11px;color:var(--text)">${z.total_tokens} tok</span>
      </div>
      ${sections}
    </div>`;
  }).join('');

  document.getElementById('prompt-zones').innerHTML =
    `<div style="margin-bottom:8px;font-size:12px">Agent: <b style="color:var(--accent)">${esc(f.agent||'?')}</b> · Total: <b>${totalTokens}</b> tokens · Sections: <b>${f.section_count||0}</b></div>` +
    zonesHtml;
  document.getElementById('prompt-summary').style.display = 'block';

  // Full prompt text
  if (f.full_prompt) {
    document.getElementById('prompt-text').textContent = f.full_prompt;
    document.getElementById('prompt-detail').style.display = 'block';
  } else {
    document.getElementById('prompt-detail').style.display = 'none';
  }
}

// ── Tab 6: Lore ──
const LORE_CAT_COLORS = { history:'var(--amber)', geography:'var(--teal)', faction:'var(--red)', character:'var(--purple)', item:'var(--green)', event:'var(--pink)', language:'var(--sky)' };
function renderLore() {
  const sel = document.getElementById('lore-turn-select');
  const idx = sel.value;
  if (idx === '' || !S.loreEvents[idx]) {
    document.getElementById('lore-budget').style.display = 'none';
    document.getElementById('lore-fragments').style.display = 'none';
    return;
  }
  const ev = S.loreEvents[idx];
  const f = ev.fields || {};
  const budget = f.budget || 0;
  const tokensUsed = f.tokens_used || 0;
  const pctUsed = budget > 0 ? (tokensUsed / budget * 100) : 0;
  const hint = f.context_hint || 'none';
  const filter = (document.getElementById('lore-filter').value || '').toLowerCase();

  // Budget bar
  document.getElementById('lore-budget-body').innerHTML =
    `<div style="margin-bottom:8px;font-size:12px">Budget: <b>${tokensUsed}</b> / <b>${budget}</b> tokens (${pctUsed.toFixed(0)}%) · Hint: <b style="color:var(--accent)">${esc(hint)}</b> · Total fragments: <b>${f.total_fragments||0}</b></div>` +
    `<div style="background:var(--border);border-radius:2px;height:18px;position:relative">` +
    `<div style="width:${pctUsed}%;background:var(--green);height:100%;border-radius:2px;opacity:0.7"></div></div>`;
  document.getElementById('lore-budget').style.display = 'block';

  // Fragment list — selected then rejected
  const allFrags = [
    ...(f.selected||[]).map(s => ({...s, status:'selected'})),
    ...(f.rejected||[]).map(s => ({...s, status:'rejected'}))
  ].filter(frag => !filter || frag.id.toLowerCase().includes(filter) || frag.category.toLowerCase().includes(filter));

  document.getElementById('lore-fragments-body').innerHTML = allFrags.map(frag => {
    const color = LORE_CAT_COLORS[frag.category] || 'var(--muted)';
    const statusColor = frag.status === 'selected' ? 'var(--green)' : 'var(--red)';
    const statusIcon = frag.status === 'selected' ? '✓' : '✗';
    return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid var(--border);font-size:12px">
      <span style="color:${statusColor};width:16px;text-align:center;font-weight:bold">${statusIcon}</span>
      <span style="color:${color};width:80px">${esc(frag.category)}</span>
      <span style="flex:1;color:var(--text)">${esc(frag.id)}</span>
      <span style="color:var(--sky);width:60px;text-align:right">${frag.tokens} tok</span>
    </div>`;
  }).join('');
  document.getElementById('lore-fragments').style.display = 'block';
}

function updateAll() { updateHeader(); renderTurnList(); if(S.activeTab===2)renderHealth(); if(S.activeTab===3)renderTiming(); if(S.activeTab===4)renderConsole(); if(S.activeTab===5)renderPrompt(); if(S.activeTab===6)renderLore(); }

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
    otlp_port: int | None = None,
) -> None:
    """
    Proxy: connects to API /ws/watcher as client, re-serves events on dashboard_port.
    HTTP dashboard on dashboard_port, WebSocket on dashboard_port+1.
    OTLP receiver on otlp_port (defaults to dashboard_port+2).
    """
    from playtest_otlp import run_otlp_receiver

    ws_port = dashboard_port + 1
    otlp = otlp_port if otlp_port is not None else dashboard_port + 2

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

    # Start OTLP receiver as a background task
    otlp_task = asyncio.create_task(run_otlp_receiver(otlp, _broadcast_to_dashboards))

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SideQuest OTEL dashboard server.")
    parser.add_argument("--dashboard-port", type=int, default=9765,
                        help="Port for the HTTP dashboard (default: 9765).")
    parser.add_argument("--api-host", default="localhost",
                        help="Game server host (default: localhost).")
    parser.add_argument("--api-port", type=int, default=8765,
                        help="Game server WebSocket port (default: 8765).")
    parser.add_argument("--otlp-port", type=int, default=None,
                        help="OTLP receiver port (default: dashboard-port+2).")
    args = parser.parse_args()

    asyncio.run(run_dashboard_server(
        api_host=args.api_host,
        api_port=args.api_port,
        dashboard_port=args.dashboard_port,
        otlp_port=args.otlp_port,
    ))

