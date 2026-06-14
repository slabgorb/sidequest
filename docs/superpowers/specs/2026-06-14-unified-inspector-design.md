# Unified Inspector — One Pane of Glass over Two Pipes

**Date:** 2026-06-14
**Status:** Design (brainstorm output, pre-plan)
**Author:** Architect (Atlas)
**Related ADRs:** 090 (OTEL Dashboard Restoration), 124 (Save-Forensics Architecture), 031 (Game Watcher semantic telemetry), 132 (WatcherHub infrastructure), 103 (Native OTEL via tool registry — partial)

## Problem

What looks like "two tools" (the live OTEL/GM dashboard and the save-forensics
tool) is really **four frontends over one data substrate**, and they have already
drifted apart:

| Surface | Stack | Served at | State |
|---|---|---|---|
| GM/OTEL dashboard | React (8 tabs) | Vite app | Canonical, maintained |
| GM/OTEL dashboard | server HTML + vanilla D3 (7 tabs) | `/dashboard` (FastAPI) | **Drifted** — missing Encounters tab, "Rust memory" tooltip |
| Save-forensics | server HTML | `/forensics` (FastAPI) | Live, no React twin |
| Save-forensics | *(none)* | — | React version never built |

The duplication is the bug. The server-HTML dashboard has already fallen behind
the React one (it lacks the Encounters tab) — exactly the split-brain failure
mode we want to delete. Maintaining parallel renderers guarantees ongoing drift.

Underneath, both tools already read the **same** `turn_telemetry` table. The
mechanical census the forensics tool diffs is just `component='mechanical'` rows
in the stream the live panel broadcasts. So the two tools are not two data
worlds — they are **two reader patterns over one substrate.**

## The framing (load-bearing)

> **Forensics and OTEL are different pipes. We want one pane of glass.**

- **Two pipes (kept separate, by design):** live telemetry is *lossy, real-time,
  WebSocket, drop-oldest* (ADR-090); forensics is *durable, retroactive, REST,
  strict read-only* (ADR-124). These are genuinely different reader contracts and
  **must stay separate at the data layer.** Unifying the plumbing would
  reintroduce the exact problem each contract was designed around.
- **One pane of glass (the merge):** a single React tool. The unification happens
  at the **UX and navigation layer**, not the plumbing.

## Decision

1. **React is the single stack.** Delete the server-HTML dashboard and forensics
   pages and their FastAPI HTML routes. The merged inspector lives only in the
   React app (`sidequest-ui`).
2. **One pane of glass via a `SessionSource` abstraction.** The tabs read from a
   source-agnostic interface with two implementations (live / forensic). The tabs
   never know which pipe backs them.
3. **Phase 1 is consolidation.** Port forensics into React, merge navigation,
   delete the duplicates, fix the handful of stale items. The deeper "lie-detector
   verdict as headline / prune the span firehose" signal rework is **Phase 2**,
   decided *after* the unified tool is standing (we'll "see where we are design-wise").

## Architecture

### The core abstraction: `SessionSource`

A single interface the tabs consume, with two implementations behind it:

- **`LiveSource`** — backed by the WebSocket stream (`/ws/watcher`) plus the
  existing reducer/accumulators (today's `DashboardApp`). "Live" is simply *the
  session currently being written.*
- **`ForensicSource`** — backed by REST per-round bundles
  (`/api/debug/save/{slug}/turn/{round}`, lazy-fetched per round), plus
  `/timeline` and `/snapshot`.

Both expose the **same shape** to the tabs:

- an ordered list of turns/rounds, and
- per-turn lenses: state snapshot, events, telemetry-by-component, mechanical
  census, encounter timeline, prompt, lore.

Each source advertises **capability flags** for any lens it cannot provide for a
given turn; the tab renders a clean "live-only" / "not stored for this save"
state rather than breaking. This abstraction is what actually deletes the
split-brain — it removes the *conceptual* split, not just the code duplication.

### Navigation: source selector + shared lenses

Top of the app, a session picker:

```
● Live: {current session}            ▾
  ─────────────────────────────────
  perseus_cloud · 142 turns · 3.1k telemetry · 142 census
  coyote_star  · 88 turns  · 1.9k telemetry · 0 census ⚠
  ...
```

Saved sessions come from `/api/debug/saves`, which already surfaces telemetry and
mechanical row counts per ADR-124 — so an empty mechanical stream is visible *at
selection time* (the ⚠ above). Pick live → WebSocket subscription. Pick a save →
REST lazy fetch. Same tab bar either way.

### The unified lens set

Reconciling the 8 React dashboard tabs with the forensics panels into one set.
"Both" lenses are the merge payoff; capability flags handle the asymmetric ones.

| Lens | Live source | Forensic source | Availability |
|---|---|---|---|
| **Timeline** | span flame chart (`turn_complete` spans) | per-round narrative/event boundaries (`/timeline`) | both, different render |
| **State** | `game_state_snapshot` event | `/snapshot` + per-round bundle | both |
| **Subsystems** | rolling 20-turn activity grid | `fold_turn_telemetry` (whole save) | both |
| **Console** | event firehose | `turn_telemetry` rows | both |
| **Encounters** | `encounter_events` (REST) | `encounter_events` (REST) | both — *already identical* |
| **Mechanical** | latest census rows | `fold_mechanical_census` diff + truth-tier badging | both (forensic-rich) |
| **Timing** | live percentiles, histograms | replay from stored telemetry | both |
| **Prompt** | `prompt_assembled` event | from stored `turn_telemetry` (persists — not ephemeral) | both |
| **Lore** | `lore_retrieval` event | from stored `turn_telemetry` (persists — not ephemeral) | both |

Notes:

- **Encounters is free** — it's already a REST tab in the React dashboard,
  identical for live and saved.
- **Prompt/Lore are forensic-capable.** Only `action_reveal.composing` and
  `action_reveal.dropped_rate_limit` are ephemeral (ADR-132); `prompt_assembled`
  and `lore_retrieval` persist to `turn_telemetry`. They already ride inside the
  forensic bundle's telemetry fold — surfacing them as first-class forensic panels
  is a reader/frontend concern, **no backend persistence change required.**
- **Truth-tier amber-badging** (derived KnownFacts vs stored vs absent, ADR-124)
  folds into the Mechanical and State lenses for the forensic source.

### What gets deleted

- `sidequest-server/sidequest/server/static/dashboard.html`
- `sidequest-server/sidequest/server/static/forensics.html`
- `sidequest-server/sidequest/server/dashboard.py` (the `GET /dashboard` HTML route)
- `sidequest-server/sidequest/server/forensics.py` (the `GET /forensics` HTML route)
- The two dead Rust-port span constants: `SPAN_MUSIC_EVALUATE` /
  `SPAN_MUSIC_CLASSIFY_MOOD` (`telemetry/spans/audio.py`) and
  `SPAN_INVENTORY_EXTRACTION` (`telemetry/spans/inventory.py`) — no emitters exist
- The "Rust memory" tooltip (`DashboardHeader.tsx`) — stale wording

### What stays (this is the data API now)

- **Every WS/REST endpoint:** `/ws/watcher`, `/api/debug/state`,
  `/api/debug/saves`, `/api/debug/save/{slug}/timeline`,
  `/api/debug/save/{slug}/turn/{round}`, `/api/debug/save/{slug}/snapshot`,
  `/api/sessions/{slug}/encounter_events`.
- The forensic readers (`forensic_query.py` SQLite for import/test, `pg/forensic.py`
  Postgres for production), the three pure folds, the mechanical census.

### Access-path change (accepted, flagged for record)

Today `/dashboard` and `/forensics` are served standalone by FastAPI on `:8765`
with the React app *not* running. After this change, the inspector lives only in
the React app — reaching it requires the UI built/served (dev: `just client` on
`:5173`). This was explicitly accepted ("get rid of the rest completely"). Knock-on
effects to update: the `just otel` recipe and the playtest access workflow should
point at the React route, not the server HTML page.

## Non-goals (out of scope for Phase 1)

- **No plumbing unification.** Live (lossy/WS) and forensic (durable/REST) stay
  two pipes. We unify the glass, not the pipes.
- **No span-firehose audit.** Pruning the 280+ routed / 51 flat-only span types
  down to "what you actually read" is Phase 2.
- **No lie-detector headline rework.** Surfacing a top-level "did the mechanics
  back the narration this turn?" verdict (ADR-031 Layer 3) as the front-page signal
  is Phase 2, evaluated once the unified tool exists.
- **No ADR-103 work.** Narrator tool-dispatch span coverage (Phase E) is unrelated.

## Risks / watch-fors

- **The `SessionSource` shape is the hard 20%.** If the interface isn't genuinely
  source-agnostic, we rebuild split-brain *inside* React. The two existing data
  shapes (live WS reducer state vs forensic per-round REST bundle) must be
  reconciled into one tab-facing contract before tabs are ported.
- **Don't merge the two contracts to "simplify."** That's the ADR-090↔124 tension;
  collapsing them recreates the lossy-vs-read-only conflict each was built to solve.
- **Per-round lazy fetch** for the forensic source must stay read-only (ADR-124
  RO discipline) — no accidental writes when "scrubbing" through a save.

## Deliverables / phasing

- **Phase 1 (this design):** `SessionSource` abstraction; session picker; port
  forensics lenses into React; capability-flag the asymmetric lenses; delete the
  server-HTML surfaces + routes + stale items; repoint `just otel`.
- **Phase 2 (deferred, decide later):** lie-detector verdict headline; span-set
  audit / prune; whatever "capturing the right stuff" turns out to mean once the
  one pane of glass is standing.
- **ADR:** this change deletes architecture-of-record surfaces (server-served
  dashboards) and establishes React-only single-pane inspection. It warrants an
  ADR that extends ADR-090 and ADR-124's UI sections; to be authored at planning.
