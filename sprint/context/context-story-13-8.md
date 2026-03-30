# Story 13-8: Fix Barrier Single Narrator Call Per Turn

## Critical Bugs Being Fixed

### Bug 1: Wrong MultiplayerSession Read (named_actions() Race)

**Location:** The barrier turn handler calls `ss.multiplayer.named_actions()` to get the combined action string for the narrator prompt.

**Problem:** The handler reads from `ss.multiplayer` (the SharedGameSession's multiplayer field), which is the SHARED session across ALL barriers in the game — not the barrier's internal `MultiplayerSession`. This causes:
- `named_actions()` returns empty or stale data
- The narrator prompt receives an empty PARTY ACTIONS block
- The combined action context never includes what the players actually submitted

**Root Cause:** `ss.multiplayer` and the `TurnBarrier`'s internal `MultiplayerSession` are separate objects. The barrier collects actions into its own session; the handler looks at the wrong place.

**Fix:** Read `result.narration` from `TurnBarrierResult` instead. The barrier resolves and returns the composed narration directly — don't try to re-compose it from the wrong session.

**Code Path:**
- `lib.rs`: `handler_process_barrier()` or equivalent
- Reads: `ss.multiplayer.named_actions()` ← WRONG
- Should read: `TurnBarrierResult::narration` or compose from `barrier.session.named_actions()`

### Bug 2: N Divergent Narrator Calls (Race on Handler Resume)

**Location:** When the barrier resolves, all N player handlers waiting in `wait_for_turn()` resume simultaneously.

**Problem:** Each handler independently calls the narrator with the combined action. This produces:
- N separate narrator requests for the same turn
- N divergent narrations (each one uses the same prompt but different model state)
- Last-write-wins race on shared world state (`npc_registry`, `trope_states`, `narration_history`)
- Players see inconsistent narrations

**Root Cause:** `wait_for_turn()` returns to all waiters without coordination. There's no elected handler — everyone tries to narrate.

**Fix:** Implement handler election using a resolution lock (e.g., `AtomicBool` or `tokio::sync::Mutex`):
1. First handler to acquire the lock runs the narrator and stores the result in a shared channel/Arc
2. Other handlers receive the narration via broadcast and skip their own narrator call
3. All handlers proceed with animation/UI updates once the single narration is available

**Code Path:**
- `barrier.rs`: `wait_for_turn()` return + handler coordination
- `lib.rs`: Handler election before `call_narrator()`
- `multiplayer.rs`: Add resolution lock or broadcast channel for narration result

## Expected Behavior After Fix

### Single Narration Per Turn
- Exactly one narrator call per barrier resolution
- Result stored in shared state accessible to all handlers
- All players receive identical narration (no race conditions)

### Correct Combined Action Context
- Narrator prompt includes "PARTY ACTIONS:" block with all submitted actions
- Actions taken from the barrier's internal MultiplayerSession, not the shared session
- Each character's action is visible to narrator for coherent world state updates

### Handler Coordination
- First handler to acquire lock runs narrator
- Other handlers receive result via broadcast/channel
- All handlers proceed in parallel after narration available
- No orphaned narrator calls, no duplicate writes to world state

## Test Approach (TDD)

### Test 1: Single Narrator Call
Create a multiplayer session with 2 players. Submit actions simultaneously, await barrier resolution. Verify:
- Narrator was called exactly once
- Result contains all submitted actions
- Both handlers received the same narration

### Test 2: Correct Action Context
Verify the narrator received the full PARTY ACTIONS block:
- "PARTY ACTIONS:"
- "Player A: their action text"
- "Player B: their action text"

### Test 3: No World State Race
Run 5 turns with 4 players, injecting side effects in narrator (e.g., increment a counter). Verify:
- Counter incremented exactly N times (not 4N)
- All handlers observed the same final state

### Test 4: Handler Coordination
Mock narrator with artificial delay. Verify all handlers waited for the same result before proceeding.

## Key Files to Touch

- `sidequest-api/crates/sidequest-game/src/barrier.rs` — Resolution lock, broadcast coordination
- `sidequest-api/crates/sidequest-game/src/multiplayer.rs` — Session data structure, action collection
- `sidequest-api/crates/sidequest-server/src/shared_session.rs` — Handler dispatch, narrator call site
- `sidequest-api/crates/sidequest-game/src/lib.rs` — Main handler loop, narrator invocation

## Acceptance Criteria

1. Narrator is called exactly once per barrier resolution (verified via mock counter)
2. Narrator receives correct PARTY ACTIONS block from barrier's internal session (not shared session)
3. All handlers receive the same narration via broadcast/shared result
4. No duplicate writes to `npc_registry`, `trope_states`, or `narration_history`
5. All multiplayer tests pass (existing + new ones)
6. Lint and clippy pass with no warnings

## Upstream Observations

- Epic 8 infrastructure (TurnBarrier, MultiplayerSession) is solid — just has coordination gaps
- Named action composition already exists in `MultiplayerSession` — just need to use the right instance
- Broadcast channel exists in SharedGameSession — can reuse for narration result propagation
