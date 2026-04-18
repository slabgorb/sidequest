# Story 34-11: OTEL dice spans — request_sent, throw_received, result_broadcast

## Overview

Add structured WatcherEvent emissions to the three dice dispatch decision points. The GM panel needs visibility into dice engagement — without these spans, there's no way to distinguish "dice worked" from "Claude improvised dice results."

**Status:** Ready for TEA (RED phase).

## Story Scope

### What Gets Built
- Three WatcherEvent emissions at dice dispatch points
- Uses existing WatcherEventBuilder pattern (no new infrastructure)
- New "dice" channel on the GM panel

### What Stays Unchanged
- Dispatch flow (34-4 complete)
- Protocol types (34-2 complete)
- Dice resolution (34-3 complete)
- Narrator injection (34-9 complete)
- Existing tracing::info! calls (preserved alongside WatcherEvents)

### Dependency
- **Blocks on:** 34-4 (Dispatch integration) — COMPLETE
- **Unblocks:** 34-12 (Playtest validation) — needs OTEL visibility to verify

## Three Dispatch Points

### 1. dice.request_sent

**When:** DiceRequest is composed and broadcast to all clients after beat selection triggers a stat check.

**Where:** `sidequest-api/crates/sidequest-server/src/lib.rs` — in the dispatch pipeline where DiceRequest is created and broadcast. This may be in `dispatch/mod.rs` or `dispatch/beat.rs` depending on where the request originates.

**Fields:**
- `event`: "dice.request_sent"
- `request_id`: The unique request identifier
- `rolling_player`: Player ID of the actor
- `stat`: The stat being checked
- `difficulty`: The DC value
- `dice_count`: Number of dice in the pool

**Type:** `SubsystemExerciseSummary` — normal dispatch flow

### 2. dice.throw_received

**When:** The rolling player's DiceThrow message arrives with gesture parameters.

**Where:** `sidequest-api/crates/sidequest-server/src/lib.rs` — DiceThrow handler (~line 2229), after the pending request is looked up but before resolution.

**Fields:**
- `event`: "dice.throw_received"
- `request_id`: The request being resolved
- `rolling_player`: Player ID of the thrower
- `has_throw_params`: Whether gesture params were included

**Type:** `SubsystemExerciseSummary` — normal dispatch flow

### 3. dice.result_broadcast

**When:** DiceResult is resolved and broadcast to all connected players.

**Where:** `sidequest-api/crates/sidequest-server/src/lib.rs` — DiceThrow handler, after resolve_dice() succeeds and compose_dice_result() returns.

**Fields:**
- `event`: "dice.result_broadcast"
- `request_id`: The request that was resolved
- `rolling_player`: Player ID
- `total`: The roll total (i32)
- `outcome`: RollOutcome variant name (CritSuccess/Success/Fail/CritFail)
- `seed`: The deterministic seed used

**Type:** `StateTransition` — the outcome changes narrator context

## WatcherEvent Pattern Reference

From existing codebase (e.g., trope, encounter, combat channels):

```rust
WatcherEventBuilder::new("dice", WatcherEventType::SubsystemExerciseSummary)
    .field("event", "dice.request_sent")
    .field("request_id", &request_id)
    .field("rolling_player", &rolling_player_id)
    .field("stat", &stat)
    .field("difficulty", difficulty)
    .send();
```

## Acceptance Criteria (RED Phase Gate)

### Unit Tests
- [ ] dice.request_sent WatcherEvent contains required fields (request_id, rolling_player, stat, difficulty, dice_count)
- [ ] dice.throw_received WatcherEvent contains required fields (request_id, rolling_player, has_throw_params)
- [ ] dice.result_broadcast WatcherEvent contains required fields (request_id, rolling_player, total, outcome, seed)
- [ ] All three events use "dice" channel
- [ ] dice.request_sent and dice.throw_received use SubsystemExerciseSummary type
- [ ] dice.result_broadcast uses StateTransition type

### Integration Tests
- [ ] Full dice round-trip emits all three events in order
- [ ] Events are visible to watcher subscribers

### No Regressions
- [ ] Existing tracing::info! calls preserved
- [ ] No dispatch flow changes
- [ ] Existing dice tests still pass

## Design Constraints

1. **Additive only.** This is pure observability — no behavior changes.
2. **Existing tracing stays.** WatcherEvents layer on top, they don't replace tracing::info!
3. **"dice" channel.** All three events share the same GM panel channel.
4. **Field types.** Use string fields for WatcherEventBuilder (it takes &str / impl Display).

## Key References

- **Epic context:** `sprint/context/context-epic-34.md` — guardrail #5 (OTEL on every dispatch decision)
- **WatcherEvent infra:** `sidequest-api/crates/sidequest-server/src/watcher.rs`
- **DiceThrow handler:** `sidequest-api/crates/sidequest-server/src/lib.rs` (~line 2229)
- **Existing patterns:** grep for `WatcherEventBuilder::new` in dispatch/ for style reference
