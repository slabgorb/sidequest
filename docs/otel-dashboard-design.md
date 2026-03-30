# SideQuest OTEL Dashboard — Redesign Spec

**Date:** 2026-03-30
**Author:** UX Design Agent
**Target:** Replace the flat log stream in `scripts/playtest.py::DASHBOARD_HTML` with a tabbed, visualization-first developer telemetry tool.

---

## Problem Statement

The current dashboard is a vertical log stream. Everything arrives in time order — a preprocess span open, a raw event, a turn complete, another span — with no way to answer the actual questions:

- *How long did the LLM call take compared to the preprocessor?*
- *What is the current game state right now?*
- *Is the trope engine actually firing, or has it gone silent?*
- *What's my p95 agent duration over the last 20 turns?*

Visualizations are not cosmetic. They're the reason you run a dashboard instead of tailing a log file.

---

## Tab Structure

Four tabs. Each is a focused view. The header bar (always visible) shows live counters and connection status.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ SideQuest OTEL   ●Connected   Turns: 12   Errors: 0   [Pause] [Clear]   │
├──────────────┬──────────────────┬─────────────────┬──────────────────── │
│  ① Timeline  │  ② State         │  ③ Subsystems    │  ④ Timing          │
└──────────────┴──────────────────┴─────────────────┴──────────────────── │
│                                                                           │
│                        [ tab content ]                                   │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

Tab badges: ① shows active turn number. ③ flashes red on error events. ④ shows current p95.

---

## Tab 1 — Turn Timeline (Flame Chart)

**The #1 priority.** Answers: *where did the time go?*

### Layout

```
┌─ Turn List ──────┐  ┌─ Flame Chart ──────────────────────────────────────┐
│ #12 narrator 8.2s│  │ Turn 12 · Exploration → narrator · 8,241 ms total  │
│ #11 combat  4.1s │  │                                                      │
│ #10 narrator 9.8s│  │ preprocessor  ████ 312ms                            │
│ #9  narrator 7.3s│  │ intent_route  █ 14ms                                │
│ #8  narrator 6.1s│  │ agent_llm     ██████████████████████████████ 7,820ms│
│ #7  DEGRADED 12s │  │ extraction    █ 8ms                                 │
│ ...              │  │ state_patch   ██ 74ms                               │
│                  │  │ broadcast     █ 13ms                                │
│                  │  │                                                      │
│                  │  │ ├──0ms──────────2000ms──────────5000ms──────8241ms─┤│
│                  │  └──────────────────────────────────────────────────────┘
│                  │  ┌─ Turn Metadata ─────────────────────────────────────┐
│                  │  │ Input: "I approach the glowing door"                │
│                  │  │ Intent: exploration  Agent: narrator                │
│                  │  │ Tokens: 1,842 in / 412 out  Tier: 1  Degraded: no  │
│                  │  │ Patches: world (location, atmosphere)               │
│                  │  │ Beats fired: wanderer_curse @0.62                   │
└──────────────────┘  └──────────────────────────────────────────────────────┘
```

### Flame Chart Rendering (D3.js)

- **X axis:** time in ms (0 → turn total duration). Labeled at 0, midpoint, end.
- **Y axis:** one lane per subsystem span, top-to-bottom in pipeline order.
- **Bars:** filled rect, width = `(duration_ms / total_ms) * chart_width`.
- **Color coding:**
  - `preprocessor` → `#03dac6` (teal)
  - `intent_route` → `#4fc3f7` (sky blue — fast, cheap)
  - `agent_llm` → `#bb86fc` (purple — the expensive one)
  - `extraction` → `#81c784` (green)
  - `state_patch` → `#ffb74d` (amber)
  - `broadcast` → `#90a4ae` (gray)
  - `music_director` → `#f06292` (pink — media layer)
- **Hover tooltip:** `span_name | duration_ms | component`
- **Degraded turns:** entire chart has red left border + DEGRADED badge overlay.

### Turn List (Left Sidebar)

- Scrollable, newest at top.
- Each row: `#N  agent  Xs  [badge]`
  - Badge: `DEGRADED` (red), `COMBAT` (orange), `CHASE` (yellow), `BEAT` (teal) if a trope fired.
- Click row → load that turn's flame chart.
- Auto-follows latest turn unless user has manually selected a turn (pause indicator).

### Interaction

- Click any span bar → expand to show full fields for that span's `AgentSpanOpen`/`AgentSpanClose` events in a drawer below.
- Turn list rows are keyboard-navigable (up/down arrow).

### Data Consumed

- `TurnComplete` events with `fields.spans[]` (**new field — see Data Requirements**).
- Existing: `fields.turn_id`, `fields.classified_intent`, `fields.agent_name`, `fields.agent_duration_ms`, `fields.is_degraded`, `fields.patches`, `fields.beats_fired`, `fields.player_input`, `fields.token_count_in/out`, `fields.extraction_tier`.

---

## Tab 2 — Game State Explorer

**Answers:** *What does the world look like right now?*

### Layout

```
┌─ Nav ───────────────┐  ┌─ Detail Panel ────────────────────────────────────┐
│ ● Characters (2)    │  │                                                    │
│   Kira Valdez       │  │  Kira Valdez  ·  Scavenger                        │
│   Tomás Rue         │  │  ──────────────────────────────────────            │
│ ● NPCs (4)          │  │  HP  ████████████████░░░░ 18/24                   │
│   Toggler Copperjaw │  │                                                    │
│   The Rust Oracle   │  │  Disposition to player: ──●──────── Friendly (+14)│
│   Mira              │  │                                                    │
│   Carrion Bishop    │  │  OCEAN: O:0.82  C:0.41  E:0.65  A:0.77  N:0.23   │
│ ─────────────────── │  │                                                    │
│ ○ Location          │  │  Abilities:                                        │
│ ○ Quests (3 active) │  │  · Scrap Intuition (passive)                      │
│ ○ Tropes (2 active) │  │  · Patch Job (involuntary)                        │
│ ○ Combat [inactive] │  │                                                    │
│ ○ Inventory         │  │  Inventory (4 items):                             │
│                     │  │  · Rusted Pipe Wrench                             │
│ ──────────────── ↻  │  │  · Flickering Headlamp (named)                   │
│ Last update: T#12   │  │  · Rad-Away Vial                                  │
│                     │  │  · The Sorrow Compass (evolved ★)                 │
└─────────────────────┘  └────────────────────────────────────────────────────┘
```

### Sub-panels

**Characters:** HP bar, inventory, abilities, known facts count. Click character for full detail.

**NPCs:** Name, role, disposition bar (−20 to +20 mapped to Hostile/Neutral/Friendly gradient), OCEAN scores as a small bar chart, appearance, last interaction turn.

**Location & World:**
- Current location (large, prominent), time of day, atmosphere paragraph.
- Campaign maturity badge: `FRESH` / `EARLY` / `MID` / `VETERAN`.
- Discovered regions as a tag cloud (click = filter event log for that region).

**Quests:** Active quests as cards (quest name header, description body). Empty state: "No active quests."

**Tropes:** Each active trope as a progress widget:
```
wanderer_curse  ████████████░░░░░░░  0.62 / 1.0   Next: 0.75 (escalate)
```
Shows last beat fired and threshold.

**Combat** (conditional, highlighted in red border when `combat.in_combat = true`):
- Enemy list with HP bars, status effects.
- Turn order, round counter, drama weight.
- Combat log (last 5 entries).

**Inventory:** Full item list for selected character. Items display tier (unnamed / named / evolved) with visual weight indicator.

### Interaction

- Left nav is a tree. Categories are collapsible.
- Clicking any NPC or Character highlights their events in Tab 3's timeline.
- `↻` refresh icon (bottom of nav) forces re-emit request — no WebSocket command needed, just marks state as stale visually.
- State persists between tab switches.

### Data Consumed

- New `WatcherEventType::GameStateSnapshot` event with `fields.snapshot` (full serialized `GameSnapshot`). Dashboard stores only the latest snapshot — does not accumulate.
- Fires once per turn, after `TurnComplete`.

---

## Tab 3 — Subsystem Health

**Answers:** *Which components are active? Which have gone silent? Where are the errors?*

### Layout

```
┌─ Activity Grid (last 20 turns) ────────────────────────────────────────────┐
│              T1  T2  T3  T4  T5  T6  T7  T8  T9  T10 ... T20              │
│ game          ●   ●   ●   ●   ●   ●   ●   ●   ●   ●       ●              │
│ narrator      ●   ●   ●   ●   ●   ●       ●   ●   ●       ●  ← gap T7!   │
│ preprocessor  ●   ●   ●   ●   ●   ●   ●   ●   ●   ●       ●              │
│ trope         ●       ●       ●       ●       ●       ●       ●           │
│ combat            ●       ●                                                │
│ music_director●   ●   ●   ●   ●   ●   ●   ●   ●   ●       ●              │
│ validation    ●       ●       ●                               ← SILENT 8t  │
└────────────────────────────────────────────────────────────────────────────┘
● green=info  ◆ yellow=warn  ✕ red=error  · gray=no events this turn
```

**Silence detector:** A component that hasn't emitted in >5 turns gets an amber "SILENT Nt" badge. This catches broken wiring (e.g., the music director stopped emitting because a media daemon crashed).

### Component Detail Drawer

Click a row to expand an inline event log filtered to that component, showing last 20 events with timestamp, event_type, severity, and key fields. Same key=value compact format as the old dashboard, but scoped.

### Summary Table (below grid)

| Component | Events | Errors | Warns | Last Seen | Status |
|-----------|--------|--------|-------|-----------|--------|
| game | 84 | 0 | 2 | T#12 | ✓ OK |
| narrator | 11 | 0 | 0 | T#12 | ✓ OK |
| validation | 4 | 0 | 0 | T#4 | ⚠ SILENT 8t |

Sortable by any column. Click row = same component detail drawer.

### Data Consumed

- All `WatcherEvent` types. Tracks `component`, `event_type`, `severity`, `timestamp`.
- Turn number inferred from TurnComplete counter (events between two TurnComplete = same turn bucket).

---

## Tab 4 — Timing Analysis

**Answers:** *What's my latency distribution? Is performance degrading over time?*

### Layout

```
┌─ Summary Row ────────────────────────────────────────────────────────────── ┐
│   p50: 6.2s    p95: 11.4s    p99: 14.1s    Degraded: 1/12 (8%)            │
└────────────────────────────────────────────────────────────────────────────  ┘
┌─ Agent Duration Histogram ──────────────┐  ┌─ Per-Agent Breakdown ─────────┐
│  Count                                  │  │  narrator       avg: 7.1s     │
│    8 │     ██                           │  │  creature_smith avg: 4.3s     │
│    4 │  ██ ██ ██                        │  │  ensemble       avg: 6.8s     │
│    2 │  ██ ██ ██ ██ ██                  │  │  dialectician   avg: 5.2s     │
│      └──────────────────────────────── │  └───────────────────────────────┘
│         2s  4s  6s  8s  10s  12s       │
└─────────────────────────────────────────┘
┌─ Turn Duration Over Time ───────────────────────────────────────────────────┐
│                                                                              │
│  14s │                        ●                                             │
│  10s │          ●    ●    ●       ●   ●  ●                                 │
│   6s │   ●  ●       ●   ● ●          ●      ●  ●  ●                        │
│      └──────────────────────────────────────────────────────────────────── │
│          T1  T2  T3  T4  T5  T6  T7  T8  T9 T10 T11 T12                   │
└──────────────────────────────────────────────────────────────────────────── ┘
┌─ Token Usage ───────────────────────────────────────────────────────┐  ┌─ Extraction Tier ─────┐
│  Bar chart: in (blue) vs out (teal) per turn                        │  │  ■ Direct    9  (75%) │
│                                                                     │  │  ■ Fenced    2  (17%) │
│  in  █████████████████████████████████████████                    │  │  ■ Regex     1  (8%)  │
│  out ██████████████                                                │  └───────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
```

### Visualizations (all D3.js)

**Agent Duration Histogram:**
- Bin width: 1 second. Colored by dominant agent in each bin.
- Hover: exact bucket range + count.

**Turn Duration Over Time (scatter/line):**
- X = turn number, Y = agent_duration_ms.
- Points colored by agent type.
- Degraded turns rendered as red ✕.
- Moving average line (window = 5 turns) overlaid in white.

**Token Usage Bar:**
- Grouped bars per turn: `token_count_in` (blue), `token_count_out` (teal).
- Running total in corner.

**Extraction Tier Distribution:**
- Donut chart. Click slice = filter turn list in Tab 1 to that tier.

**Degraded Rate Gauge:**
- Circular gauge 0–100%. Red zone > 10%.

### Data Consumed

- `TurnComplete` events: `fields.agent_duration_ms`, `fields.token_count_in`, `fields.token_count_out`, `fields.extraction_tier`, `fields.agent_name`, `fields.is_degraded`.
- All data accumulates for the session (no eviction — playtests are bounded).

---

## Data Requirements — New Events / Fields

### 1. `fields.spans[]` on `TurnComplete` (highest priority)

Add a `spans` array to the fields HashMap of every `TurnComplete` WatcherEvent:

```json
"spans": [
  { "name": "preprocess",   "component": "preprocessor",  "start_ms": 0,    "duration_ms": 312 },
  { "name": "intent_route", "component": "intent_router", "start_ms": 312,  "duration_ms": 14  },
  { "name": "agent_llm",    "component": "narrator",      "start_ms": 326,  "duration_ms": 7820},
  { "name": "extraction",   "component": "extractor",     "start_ms": 8146, "duration_ms": 8   },
  { "name": "state_patch",  "component": "game",          "start_ms": 8154, "duration_ms": 74  },
  { "name": "broadcast",    "component": "server",        "start_ms": 8228, "duration_ms": 13  }
]
```

All `start_ms` values are relative to turn start. Assembled from `Instant::now()` snapshots recorded at each phase boundary in `process_turn()` in `lib.rs`. The existing `agent_duration_ms` from `ActionResult` already gives us the LLM span — the others require adding timing captures at the call sites for preprocess, state_patch, and broadcast.

**Server changes needed:**
- Record `Instant` at turn start, preprocess start/end, intent_route start/end, agent call start/end (already have), extraction start/end (already have extraction_tier, need timing), state_patch start/end, broadcast start/end.
- Assemble spans vec and serialize as `serde_json::Value` into TurnComplete fields.

### 2. `WatcherEventType::GameStateSnapshot` (new variant)

New event emitted after each `TurnComplete`, containing the full post-patch game snapshot:

```json
{
  "component": "server",
  "event_type": "game_state_snapshot",
  "severity": "info",
  "timestamp": "...",
  "fields": {
    "turn_id": 12,
    "snapshot": { /* full GameSnapshot serialized */ }
  }
}
```

Emit via `send_watcher_event()` after `send_turn_record()` in the turn loop. GameSnapshot is `Serialize` — just call `serde_json::to_value(&snapshot_after)` and insert into fields.

Note: GameSnapshot can be 5–50KB depending on lore accumulation. The dashboard discards all but the latest. This is fine for single-developer playtesting over localhost — it's not a production telemetry pipeline.

### 3. Music Director spans (existing Task #1)

Add `AgentSpanOpen`/`AgentSpanClose` events from `MusicDirector` with a `span_name: "music_director"` field, so Tab 3 can track media subsystem health independently of game logic spans. These events slot naturally into Tab 3's activity grid with no additional schema changes.

---

## Implementation Notes — Single HTML File

**No build step. No npm. Just inline HTML/CSS/JS + D3 from CDN.**

### D3 usage

```html
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
```

Use D3 for:
- Flame chart (`d3.scaleBand()` for Y lanes, `d3.scaleLinear()` for X time axis, `selection.append("rect")` for bars)
- Histograms (`d3.bin()` + bar chart)
- Scatter plot for turn duration over time (`d3.scaleLinear()`, circle elements)
- Donut chart for extraction tier (`d3.pie()` + `d3.arc()`)

D3 v7 is ~240KB minified. Acceptable for a dev tool.

### State Model (in-page JS)

```js
const state = {
  turns: [],          // Array of TurnComplete event fields, newest last
  latestSnapshot: {}, // Latest GameStateSnapshot fields.snapshot
  allEvents: [],      // All WatcherEvents (for Tab 3 grid)
  componentMap: {},   // component → [events] (for health grid)
  selectedTurn: null  // For Tab 1 flame chart
};
```

### Tab Switching

Pure CSS visibility toggle. No routing, no state reset on switch. A tab that hasn't received data renders an empty state message ("Waiting for first turn...").

### Global Header (always visible)

```html
<div id="header">
  <span class="title">SideQuest OTEL</span>
  <span class="dot connected" id="dot">●</span>
  <span id="conn-status">Connected</span>
  <span class="stat">Turns: <b id="turn-count">0</b></span>
  <span class="stat">Errors: <b id="error-count">0</b></span>
  <span class="stat">p95: <b id="p95">—</b></span>
  <button onclick="paused=!paused">Pause</button>
  <button onclick="clearState()">Clear</button>
</div>
```

### WebSocket handler

```js
ws.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  if (paused) return;
  dispatch(ev); // routes to tab-specific update functions
};
```

`dispatch()` reads `ev.event_type` and calls the appropriate updater. Each tab registers an updater that runs only if that tab is active (for performance — re-render is cheap, but D3 updates on every event would be wasteful).

---

## Color Palette

Dark theme. Consistent with existing dashboard.

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg` | `#1a1a2e` | Page background |
| `--surface` | `#16213e` | Cards, panels |
| `--border` | `#333` | Borders |
| `--accent` | `#00d4ff` | Headers, links, primary action |
| `--purple` | `#bb86fc` | Agent LLM spans, narrator |
| `--teal` | `#03dac6` | Preprocessor, extraction |
| `--green` | `#4caf50` | OK status, pass events |
| `--amber` | `#ff9800` | Warnings, silent components |
| `--red` | `#f44336` | Errors, degraded |
| `--text-primary` | `#e0e0e0` | Primary text |
| `--text-muted` | `#888` | Labels, secondary text |

---

## Delivery Order

1. **Tab structure + header** — skeleton with tab switching, connection status, global counters. No D3 yet.
2. **Tab 4 (Timing)** — purely additive, works with existing `TurnComplete` fields. D3 histogram + scatter.
3. **Tab 1 (Flame Chart)** — after `fields.spans[]` lands on the server side.
4. **Tab 3 (Health)** — works with existing events, just needs grid rendering.
5. **Tab 2 (State Explorer)** — after `GameStateSnapshot` event lands on server side.

Tabs 4 and 3 can ship with zero server changes. Tabs 1 and 2 each require one server-side addition.
