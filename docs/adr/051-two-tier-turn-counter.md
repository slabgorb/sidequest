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

## Context
A single turn counter conflates two distinct concerns: mechanical tracking (every player-narrator
exchange) and narrative progress (meaningful beats that advance the story). Players who type 50
backstory questions should not see "Round 50" — they've had one story moment. Meanwhile, the
engine needs a monotonic sequence for fact chronology, NPC last-seen timestamps, and KnownFact
accumulation ordering. These requirements are incompatible under a single counter.

Additionally, the server needs to track where in the processing pipeline a turn currently sits,
independent of either counter.

## Decision
`TurnManager` (in `sidequest-game/src/turn.rs`) maintains two independent counters:

- **`interaction`** — monotonic, increments on every player-narrator exchange. Used internally
  for lore fact chronology, NPC last-seen tracking, and KnownFact accumulation timestamps.
  Players never see this number.

- **`round`** — display counter, increments only on meaningful narrative beats: location changes,
  chapter markers, and trope escalations. This is the number shown to players and reflects
  narrative progress, not raw action count.

Neither counter ever resets, including across save/load cycles. Both are persisted in
`GameSnapshot`.

Turn processing state is tracked via a five-phase `TurnPhase` enum:

```rust
pub enum TurnPhase {
    InputCollection,
    IntentRouting,
    AgentExecution,
    StatePatch,
    Broadcast,
}
```

This tracks where in the processing pipeline the current turn sits, separate from the counters.

## Alternatives Considered

- **Single counter** — rejected because it conflates mechanical and narrative tracking, producing
  meaningless round numbers for players who ask many questions without advancing the story.

- **Reset on chapter** — rejected because it breaks chronological ordering of lore facts and
  NPC encounter history. "Last seen at interaction 12" loses meaning if counters reset.

- **Client-side counting** — rejected because the server emits events (trope activations, NPC
  arrivals) that must be counted even when not triggered by player input. Only the server has
  the full event stream.

## Consequences

**Positive:**
- Players see a round number that tracks story progress, not keyboard activity.
- Internal systems (lore, NPC tracking) have a stable monotonic sequence for ordering facts.
- Save/load preserves both counters, so chronological ordering is consistent across sessions.
- `TurnPhase` enables observability into pipeline position — useful for OTEL tracing and
  deadlock diagnosis.

**Negative:**
- Two counters must be kept in sync conceptually. New code touching turns must decide which
  counter to use and use it consistently.
- The criteria for "meaningful narrative beat" are encoded as rules (location change, chapter
  marker, trope escalation) — edge cases may need to be added over time.
