---
parent: context-epic-13.md
---

# Story 13-2: Server-Side Sealed Collection — Hold Actions Until Barrier Met

## Business Context

This is the core behavioral change. Currently each PLAYER_ACTION independently triggers
the orchestrator, meaning the first player to submit gets narrated and everyone else waits.
The sealed letter pattern requires holding all actions until the barrier resolves, then
submitting them as a single batch.

**Depends on:** 13-1 (UI must show submission status)

## Technical Approach

### Modify `dispatch_player_action()` in `lib.rs`

Current flow:
```
PLAYER_ACTION → dispatch_player_action() → orchestrator.process_turn() → narration
```

Target flow (Structured mode):
```
PLAYER_ACTION → dispatch_player_action()
    │
    ├─ if FreePlay mode: orchestrator.process_turn() (unchanged)
    │
    └─ if Structured mode:
        ├─ session.submit_action(player_id, action)
        ├─ broadcast TURN_STATUS {player, status: "submitted"}
        ├─ if barrier NOT met: return (hold)
        └─ if barrier met:
            ├─ compose_party_actions() (already exists from 8-4)
            └─ orchestrator.process_turn(batched_actions)
```

### Key Code Locations

- **Action dispatch:** `sidequest-server/src/lib.rs` → `dispatch_player_action()` (~line 2051)
- **Action hold:** `sidequest-game/src/multiplayer.rs` → `submit_action()` returns `TurnStatus`
- **Barrier check:** `sidequest-game/src/barrier.rs` → `wait_for_turn()` with tokio::Notify
- **Batch compose:** `sidequest-game/src/multiplayer.rs` → `named_actions()`

### Concurrency Considerations

- `MultiplayerSession` is behind `Arc<Mutex<>>` via `TurnBarrier` — thread-safe
- Multiple WebSocket tasks will call `submit_action()` concurrently — mutex handles this
- The task that resolves the barrier (last submitter or timeout) is responsible for
  triggering the orchestrator call
- Use `tokio::Notify` to wake the barrier-holding task, not polling

### Timeout Integration

The adaptive timeout from Epic 8 (8-3) already exists. When it fires:
- Auto-fill missing players with default action ("waits and observes")
- Proceed as if barrier met
- (Notification of who was auto-filled is 13-4, not this story)

## Scope Boundaries

**In scope:**
- Modify dispatch_player_action to branch on turn mode
- Hold actions in Structured mode until barrier resolves
- Trigger orchestrator with batched actions on barrier resolution
- TURN_STATUS broadcast on each submission

**Out of scope:**
- ACTION_REVEAL broadcast (13-3)
- Timeout notification UI (13-4)
- DM force-resolve (13-6)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Actions held | In Structured mode, first player's action does NOT trigger narration |
| Barrier triggers | When all players submit, orchestrator receives all actions as batch |
| Status broadcast | Each submission triggers TURN_STATUS message to all players |
| FreePlay unchanged | Solo / FreePlay mode continues to resolve immediately |
| Timeout resolves | If timeout fires, missing players auto-filled and turn resolves |
| No double-process | Submitting twice in same turn is idempotent (first wins) |
| Concurrency safe | 4 simultaneous submissions don't deadlock or race |
