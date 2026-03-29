---
parent: context-epic-13.md
---

# Story 13-7: Sealed Letter Integration Test — 4-Player Flow

## Business Context

The sealed letter system touches barrier, session, orchestrator, protocol, and broadcast.
An integration test with multiple simulated WebSocket clients validates the full flow
end-to-end: submit, hold, reveal, narrate.

**Depends on:** 13-3 (action reveal must be wired)

## Technical Approach

### Test Setup

4 simulated WebSocket clients connecting to the same session. Use `tokio-tungstenite`
for WebSocket test clients (same pattern as existing integration tests in sidequest-server).

### Test Scenarios

**Scenario 1: Happy path — all submit before timeout**
1. 4 clients connect, session enters Structured mode
2. Client A submits action → receives TURN_STATUS for A (submitted)
3. Client B submits → TURN_STATUS for B
4. Client C submits → TURN_STATUS for C
5. Client D submits → barrier met
6. All clients receive ACTION_REVEAL with 4 actions
7. All clients receive NARRATION referencing all 4 actions
8. Turn counter increments

**Scenario 2: Timeout — 1 player missing**
1. 4 clients connect
2. Clients A, B, C submit
3. Timeout fires
4. All clients receive ACTION_REVEAL with D marked as auto-resolved
5. Narration proceeds with 3 real actions + D's default

**Scenario 3: DM force-resolve**
1. 4 clients connect
2. Only Client A submits
3. DM sends force_resolve
4. Turn resolves with 1 real action + 3 auto-filled
5. All clients notified

**Scenario 4: Idempotent submission**
1. Client A submits twice in same turn
2. Second submission ignored
3. Turn proceeds normally

## Scope Boundaries

**In scope:**
- 4-client WebSocket integration test
- Happy path, timeout, force-resolve, and idempotency scenarios
- Verify message ordering (TURN_STATUS → ACTION_REVEAL → NARRATION)

**Out of scope:**
- UI-level testing (Playwright)
- Performance/load testing
- Network failure scenarios

## Acceptance Criteria

| AC | Detail |
|----|--------|
| 4 clients | Test creates 4 concurrent WebSocket connections to same session |
| Happy path | All-submit scenario passes with correct message sequence |
| Timeout | Missing player auto-resolved, party notified |
| Force-resolve | DM control resolves partial turn |
| Idempotent | Duplicate submission silently ignored |
| Message order | ACTION_REVEAL always precedes first NARRATION_CHUNK |
| Turn counter | Increments exactly once per resolved turn |
