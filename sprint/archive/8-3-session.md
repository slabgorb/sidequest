---
story_id: "8-3"
jira_key: "NONE"
epic: "8"
workflow: "tdd"
---
# Story 8-3: Adaptive action batching

## Story Details
- **ID:** 8-3
- **Epic:** 8 (Multiplayer — Turn Barrier, Party Coordination, Perception Rewriter)
- **Workflow:** tdd
- **Stack Parent:** 8-2 (feat/8-2-turn-barrier) — COMPLETE
- **Points:** 3
- **Priority:** p0

## Story Context

Adaptive action batching scales the turn collection window based on player count:
- 2-3 players: 3 second collection window
- 4+ players: 5 second collection window

The TurnBarrier from story 8-2 already has configurable timeout support. This story
adds the adaptive logic to scale the timeout based on the number of active players in
the multiplayer session.

**Reference:** `sq-2/sidequest/game/turn_manager.py` (Python implementation)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T17:23:50Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26 | 2026-03-26T17:18:20Z | 17h 18m |
| red | 2026-03-26T17:18:20Z | 2026-03-26T17:23:49Z | 5m 29s |
| green | 2026-03-26T17:23:49Z | 2026-03-26T17:23:49Z | 0s |
| review | 2026-03-26T17:23:49Z | 2026-03-26T17:23:50Z | 1s |
| finish | 2026-03-26T17:23:50Z | - | - |

## Sm Assessment

Small story (3 pts) — extends TurnBarrierConfig with adaptive scaling based on player count. The TurnBarrier from 8-2 already accepts a Duration config. This adds a strategy/policy layer that adjusts that Duration dynamically.

**Design options:** Either a callback/closure on TurnBarrierConfig, or an `AdaptiveBatchConfig` that the barrier queries on each turn. TEA defines the API through tests.

**Risk:** Very low — pure logic on top of 8-2's existing infrastructure.

**Decision:** Proceed to RED. No blockers.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings yet.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No deviations logged yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->