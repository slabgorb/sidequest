---
id: 51
title: "Two-Tier Turn Counter (Interaction vs. Round)"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [turn-management]
implementation-status: live
implementation-pointer: null
---

# ADR-051: Two-Tier Turn Counter (Interaction vs. Round)

> Retrospective — documents a decision already implemented in the codebase.
> **Amended 2026-05-09** (story 45-34): the two-tier model collapsed to lockstep
> in PR #101 (story 45-11). See *Amendment* below for the post-Playtest 3 history.

## Context
A single turn counter conflates two distinct concerns: mechanical tracking (every player-narrator
exchange) and narrative progress (meaningful beats that advance the story). Players who type 50
backstory questions should not see "Round 50" — they've had one story moment. Meanwhile, the
engine needs a monotonic sequence for fact chronology, NPC last-seen timestamps, and KnownFact
accumulation ordering. These requirements are incompatible under a single counter.

Additionally, the server needs to track where in the processing pipeline a turn currently sits,
independent of either counter.

## Decision
`TurnManager` (in `sidequest-server/sidequest/game/turn.py`) maintains two counters that
**advance in lockstep**:

- **`interaction`** — monotonic, increments on every player-narrator exchange. Used internally
  for lore fact chronology, NPC last-seen tracking, and KnownFact accumulation timestamps.
  Players never see this number.

- **`round`** — display counter, increments on every interaction together with `interaction`.
  Shown to players as the round number. Naming is preserved for downstream consumers
  (UI, OTEL, narrative log) even though the mechanical/narrative distinction is no longer
  enforced at the counter level. See *Amendment* for why the original two-tier model was
  collapsed.

Both counters advance via `record_interaction()`. Neither counter ever resets, including across
save/load cycles. Both are persisted in `GameSnapshot`.

A legacy `advance_round()` method remains on `TurnManager` for reference but has zero
production callers — it pre-dates the lockstep collapse and is retained for migration history.
New code must call `record_interaction()` at turn boundaries.

Turn processing state is tracked via a five-phase `TurnPhase` enum:

```python
class TurnPhase(StrEnum):
    InputCollection = "InputCollection"
    IntentRouting = "IntentRouting"
    AgentExecution = "AgentExecution"
    StatePatch = "StatePatch"
    Broadcast = "Broadcast"
```

This tracks where in the processing pipeline the current turn sits, separate from the counters.

## Amendment (2026-05-09 — story 45-34)

The original two-tier aspiration described above was **never wired into the live resolution
pipeline**. `advance_round()` existed but had zero production callers; only
`record_interaction()` ran at turn boundaries, and it only advanced `interaction`. As a result:

- `turn_manager.round` lagged behind `interaction` for entire sessions because no live
  caller advanced it on the per-interaction path.
- `narrative_log` entries were keyed by `interaction` (write site
  `websocket_session_handler.py:1525`), so `MAX(narrative_log.round_number)` tracked
  `interaction` while `turn_manager.round` did not.
- Felix's Playtest 3 ended with `turn_manager.round = 65` and
  `MAX(narrative_log.round_number) = 72` — a 7-round gap. Round-keyed gating (e.g., trope
  cooldowns, encounter pacing) operated on stale round data.

**Story 45-11 (PR #101, merged 2026-05-07)** identified the divergence and selected
**Strategy A: turn-manager authoritative**. The fix lifts `round` advancement into
`record_interaction()` so both counters move together every interaction, keeping
`turn_manager.round` in sync with `MAX(narrative_log.round_number)`. An invariant OTEL
span (`turn_manager.round_invariant`) emits `round`, `interaction`, `max_narrative_round`,
`divergence`, and `divergence_direction` every tick as a GM-panel lie-detector metric
(see `sidequest-server/sidequest/telemetry/spans/turn.py`).

**Net effect:** the *rule* in this ADR (two counters, one mechanical and one narrative)
is downgraded to a *historical aspiration*. The implemented model is effectively
single-counter in behaviour — both `interaction` and `round` are persisted and exposed,
but they always hold the same value because both advance only via `record_interaction()`.
The field name `round` is preserved for backward compatibility with consumers
(UI, OTEL, narrative log). The original
"meaningful narrative beat" promotion criteria (location changes, chapter markers, trope
escalations) are no longer used to gate round advancement; if a future feature wants
narrative-only pacing, it can layer a third counter on top rather than re-splitting these
two.

## Alternatives Considered

- **Single counter** — rejected at design time because it conflates mechanical and narrative
  tracking, producing meaningless round numbers for players who ask many questions without
  advancing the story. *Note (2026-05-09):* the lockstep collapse described in the
  *Amendment* above means we are effectively running this alternative. The original
  rejection rationale is preserved here as design history; the lived counter-argument is
  that the two-counter rule was never wired and the divergence between `turn_manager.round`
  and `narrative_log.round_number` caused real GM-panel and gating bugs.

- **Reset on chapter** — rejected because it breaks chronological ordering of lore facts and
  NPC encounter history. "Last seen at interaction 12" loses meaning if counters reset.

- **Client-side counting** — rejected because the server emits events (trope activations, NPC
  arrivals) that must be counted even when not triggered by player input. Only the server has
  the full event stream.

- **Strategy B (reconcile-on-read)** — considered in story 45-11 as an alternative to
  Strategy A. Would have added a getter returning `max(turn_manager.round, narrative_log.max_round)`
  and routed all round-keyed gating through it, leaving `turn_manager.round` itself
  unchanged. Rejected because it leaves the underlying field misleading for any consumer
  (OTEL, snapshots, debug dumps) that reads `turn_manager.round` directly without the
  reconcile getter.

## Consequences

**Positive:**
- `turn_manager.round` is once again a meaningful number — it tracks the running interaction
  count and matches `MAX(narrative_log.round_number)` at every turn boundary.
- Internal systems (lore, NPC tracking) have a stable monotonic sequence for ordering facts.
- Save/load preserves both counters, so chronological ordering is consistent across sessions.
- `TurnPhase` enables observability into pipeline position — useful for OTEL tracing and
  deadlock diagnosis.
- The `turn_manager.round_invariant` span surfaces any future regression of the lockstep
  immediately, instead of silently drifting until a playtest exposes it.

**Negative:**
- The display counter no longer reflects "narrative progress" in the original sense —
  players who type 50 backstory questions will see Round 50. The fix here, if desired,
  belongs upstream of the counter (e.g., a narrator-driven chapter/beat marker that the UI
  displays *instead of* the raw round number) rather than re-splitting the counters.
- `advance_round()` remains in the codebase as legacy with no callers. New contributors may
  reach for it; the docstring and this ADR are the only signals that it should not be used.
  Removal is bounded (one method, one private helper) and could land in a follow-up cleanup.
