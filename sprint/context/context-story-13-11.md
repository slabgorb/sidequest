---
parent: context-epic-13.md
---

# Story 13-11: Activate Sealed-Letter Mode for Multiplayer — Flip Barrier On, Remove Timeout

## Business Context

All the sealed-letter infrastructure exists (TurnBarrier, MultiplayerSession, claim election,
TurnStatusPanel) but is disabled at runtime. `should_use_barrier()` returns false in FreePlay,
and the FSM transition to Structured mode is commented out. This story flips it on.

The original reason for disabling was "the submitting player's experience freezes while
waiting for others." That's solved by the player panel showing submission status and the
removal of the timeout — the round simply waits for all connected players. If someone
disconnects, the developer reboots the server (acceptable for the 2026-04-13 playtest).

## Technical Guardrails

- **`should_use_barrier()`** must return true when multiplayer session has >1 connected player
- **Remove adaptive timeout entirely** — `wait_for_turn()` blocks until barrier met, no deadline
- **On WebSocket disconnect:** remove player from the round's expected set so the barrier
  can still resolve. Basic implementation: WebSocket close event triggers removal from
  `MultiplayerSession.players` for the current round.
- **TURN_STATUS broadcast** on each player submission — the UI components already handle this
- **Preserve FreePlay for single-player** — solo sessions should not use the barrier
- **OTEL spans:** `barrier.activated` (on round start), `barrier.resolved` (all submitted),
  `barrier.player_disconnected` (removal from round)

## Scope Boundaries

**In scope:**
- Flip `should_use_barrier()` or remove the FreePlay guard for multiplayer
- Remove `AdaptiveTimeout` from the barrier wait path
- Handle WebSocket disconnect by removing player from current round
- Verify TURN_STATUS messages broadcast correctly on each submission
- Verify existing TurnStatusPanel renders submission state

**Out of scope:**
- Prompt changes (that's 13-12)
- Initiative or genre pack changes (that's 13-13)
- Player panel redesign (that's 13-14)
- Heartbeat-based disconnect detection (deferred)
- Mid-session join protocol (deferred)

## AC Context

| AC | Detail |
|----|--------|
| Barrier activates for multiplayer | >1 connected player → barrier mode, solo → no barrier |
| No timeout | `wait_for_turn()` blocks indefinitely until all players submit |
| Disconnect removes from round | WebSocket close → player removed from expected set → barrier can resolve |
| TURN_STATUS broadcast | Each submission broadcasts status to all clients |
| TurnStatusPanel works | UI shows pending/submitted per player |
| OTEL telemetry | `barrier.activated`, `barrier.resolved` spans emitted |
| Single-player unaffected | Solo sessions skip barrier entirely |

## Key Files

| File | Change |
|------|--------|
| `sidequest-game/src/turn_mode.rs` | `should_use_barrier()` logic |
| `sidequest-game/src/barrier.rs` | Remove timeout, disconnect handling |
| `sidequest-server/src/dispatch/mod.rs` | Barrier activation in dispatch flow |
| `sidequest-server/src/lib.rs` | WebSocket disconnect → remove from round |
| `sidequest-game/src/multiplayer.rs` | `remove_player()` for disconnect |
