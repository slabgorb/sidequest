# Epic 18: OTEL Dashboard — Granular Instrumentation & Rich State Views

## Overview

Improve the OTEL dashboard (inline HTML/JS in `scripts/playtest.py`) with
sub-span instrumentation for flame chart granularity and structured state
views for NPCs, inventory, lore, and prompts. Fix the State tab which shows
raw JSON instead of usable structured panels.

**Priority:** p1
**Repos:** api (instrumentation), orchestrator (dashboard UI in scripts/playtest.py)
**Stories:** 6 (20 pts total)

## Background

### The Dashboard

The OTEL dashboard is a single-file inline HTML/JS app embedded as the
`DASHBOARD_HTML` string in `scripts/playtest.py` (starts at line 216). It's
served by a minimal async HTTP server when playtest runs with `--dashboard-only`.
The dashboard connects to the API's `/ws/watcher` WebSocket via a proxy in
playtest.py and renders 5 tabs:

| Tab | Purpose | Current State |
|-----|---------|--------------|
| Timeline | Flame chart + turn list | Working, but spans are coarse |
| State | Game state explorer | Raw JSON dump only |
| Subsystems | Activity grid per component | Working |
| Timing | Duration histograms, token usage | Working |
| Console | Raw event log with filters | Working |

**Key file:** `scripts/playtest.py` — the `DASHBOARD_HTML` string contains
all HTML, CSS, and JavaScript for the dashboard. Changes to the dashboard
UI are changes to this string.

**Event flow:** API emits `WatcherEvent` → `/ws/watcher` WebSocket → playtest.py
proxy → browser WebSocket → `dispatch(ev)` function in inline JS.

### Current Instrumentation Gap

The flame chart shows per-turn timing across 8 pipeline phases but three
phases are opaque single spans:

| Phase | Typical Duration | What's Hidden Inside |
|-------|-----------------|---------------------|
| `preprocess` | ~7.2s | Haiku LLM call for STT cleanup |
| `agent_llm` | ~7.9s | Prompt assembly + Opus inference + extraction |
| `system_tick` | ~6.1s | Combat processing + trope engine ticking |

### State Tab Limitations

The State tab (line 520-526 of playtest.py) renders `S.latestSnapshot` as
raw `JSON.stringify` output. The GM needs structured views for:
- NPC registry (who's in play, where, disposition)
- Inventory (items, evolution stage, gold)
- Known facts (what Claude remembers)
- Lore budget (what made it into the prompt vs what got cut)

### Key Reference Files

| File | Role |
|------|------|
| `scripts/playtest.py` | Dashboard HTML/JS (line 216+), proxy server, event dispatch |
| `sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` | Turn pipeline spans |
| `sidequest-api/crates/sidequest-agents/src/preprocessor.rs` | Preprocess phase |
| `sidequest-api/crates/sidequest-agents/src/orchestrator.rs` | Agent LLM phase |
| `sidequest-api/crates/sidequest-server/src/lib.rs` | WatcherEventType enum |

## Technical Architecture

### Dashboard Architecture

```
API (/ws/watcher) → playtest.py proxy → Browser WebSocket
                                        ↓
                                   dispatch(ev) in DASHBOARD_HTML JS
                                        ↓
                                   S.turns[] / S.latestSnapshot / S.allEvents[]
                                        ↓
                                   render functions per tab
```

All dashboard UI is vanilla JS + HTML + CSS in the `DASHBOARD_HTML` string.
No React, no build step, no npm. D3.js loaded via CDN for charts.

### Sub-Span Instrumentation (18-1) — DONE

Added child spans inside preprocess, agent_llm, and system_tick. The API
now emits granular timing data. The flame chart will automatically show
these if the `turn_complete` event's `spans` array includes them.

### State Tab Enhancement (18-2 retarget + 18-5)

The State tab currently does:
```javascript
el.innerHTML = `<pre>${JSON.stringify(s, null, 2)}</pre>`;
```

Replace with structured panels that parse `S.latestSnapshot`:
- NPC table from `snapshot.npc_registry[]`
- Inventory panel from `snapshot.characters[].inventory`
- Known facts list from `snapshot.characters[].known_facts[]`
- Quest log from `snapshot.quest_log`
- Location + discovered regions

### New Event Types for 18-4 and 18-6

**LoreSelection** — emitted from `select_lore_for_prompt()` in lore.rs:
```json
{ "event_type": "lore_selection", "fields": {
    "turn_number": 18, "selected": [...], "rejected": [...],
    "budget_tokens": 2000, "tokens_used": 1847
}}
```

**PromptAssembled** — emitted after ContextBuilder assembly:
```json
{ "event_type": "prompt_assembled", "fields": {
    "turn_number": 18, "agent": "narrator", "total_tokens": 4200,
    "zones": [{ "name": "Primacy", "token_count": 800 }, ...]
}}
```

Both need new `WatcherEventType` variants in the API and new `dispatch(ev)`
handlers + render functions in the dashboard JS.

### Parallelization (18-3)

After sub-spans confirm timing, `tokio::join!` prompt context build and
preprocess Haiku call. Pure API change, no dashboard work.

## Story Dependency Graph

```
18-1 (sub-spans) ──→ 18-3 (parallelize)    [both DONE or API-only]
18-2 (retarget State tab) ──→ 18-5 (structured panels)
18-4 (lore browser) ── standalone
18-6 (prompt inspector) ── standalone
```

## Acceptance Criteria Summary

| Story | Key ACs |
|-------|---------|
| 18-1 | Sub-spans visible in flame chart. DONE. |
| 18-2 | State tab shows game state after a turn (retarget to playtest.py). Verify `game_state_snapshot` event is handled correctly. |
| 18-3 | Preprocess and prompt build overlap in flame chart. Turn time reduced. |
| 18-4 | Lore tab shows fragments with search/filter. Per-turn budget visualization. |
| 18-5 | NPC table, inventory panel, known facts list in State tab. |
| 18-6 | Prompt tab shows zone-labeled prompt with per-zone token counts. |

## Planning Documents

| Document | Path |
|----------|------|
| OTEL Principle | CLAUDE.md (OTEL Observability Principle section) |
| Epic YAML | sprint/epic-18.yaml |
| Dashboard source | scripts/playtest.py (DASHBOARD_HTML at line 216) |
| LoreStore | sidequest-game/src/lore.rs (2,746 LOC) |
| Prompt Framework | sidequest-agents/src/prompt_framework/ (1,484 LOC) |
