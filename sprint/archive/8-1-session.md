---
story_id: "8-1"
jira_key: "NONE"
epic: "8"
workflow: "tdd"
---
# Story 8-1: MultiplayerSession — coordinate multiple WebSocket clients in a single game session, player_id mapping

## Story Details
- **ID:** 8-1
- **Epic:** 8 (Multiplayer — Turn Barrier, Party Coordination, Perception Rewriter)
- **Workflow:** tdd
- **Stack Parent:** 2-2 (Session actor) — completed
- **Points:** 5
- **Priority:** p0

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T16:30:08Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26T16:20:22Z | 2026-03-26T16:21:30Z | 1m 8s |
| red | 2026-03-26T16:21:30Z | 2026-03-26T16:30:00Z | 8m 30s |
| green | 2026-03-26T16:30:00Z | 2026-03-26T16:30:04Z | 4s |
| review | 2026-03-26T16:30:04Z | 2026-03-26T16:30:08Z | 4s |
| finish | 2026-03-26T16:30:08Z | - | - |

## Sm Assessment

Story 8-1 is the foundation of the multiplayer epic. It depends on 2-2 (session actor), which is complete. The scope is well-defined: MultiplayerSession struct with player_id mapping, WebSocket client coordination, and state broadcast interfaces.

**Routing:** TDD phased workflow. TEA writes failing tests first (RED), then Dev makes them pass (GREEN), then Reviewer checks quality.

**Risk:** This is a 5-point story touching async coordination — the Rust ownership model around shared mutable state (`Arc<Mutex<>>` or actor pattern) will be the key design decision. TEA should reference the Python `multiplayer_session.py` for behavioral expectations.

**Decision:** Proceed to RED phase. No blockers identified.

## Delivery Findings

No upstream findings yet. Agents record observations here as work begins.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

No deviations yet. Agents log spec deviations as they happen.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Implementation Notes

### Context & References
- **Key Python References:**
  - `sq-2/sidequest/game/multiplayer_session.py` — Original Python implementation
  - `sq-2/sidequest/game/turn_manager.py` — Turn management logic
  - `oq-2/docs/adr/028-perception-rewriter.md` — Perception rewriting design
  - `oq-2/docs/adr/029-guest-npc-players.md` — Guest NPC design

- **Dependency:** Story 2-2 (Session actor) is the foundation for multiplayer session handling.

### Test-First Approach (TDD)
This story follows the TDD workflow:
1. Write tests first (in `sidequest-api/crates/sidequest-game/src/multiplayer/mod.rs`)
2. Define the `MultiplayerSession` struct and traits
3. Implement player_id mapping, session state coordination
4. Verify WebSocket client coordination through tests
5. Integration tests with the session actor

### Story Scope
MultiplayerSession is responsible for:
- Tracking multiple WebSocket client connections per session
- Mapping player_ids to connections (client sessions)
- Coordinating state updates across all connected players
- Providing interfaces for the orchestrator to broadcast turn results
- Foundation for turn barriers and perception rewriting (8-2, 8-6)