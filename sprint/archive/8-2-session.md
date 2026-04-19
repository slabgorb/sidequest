---
story_id: "8-2"
jira_key: "NONE"
epic: "8"
workflow: "tdd"
---
# Story 8-2: Turn barrier — wait for all players before resolving turn, configurable timeout

## Story Details
- **ID:** 8-2
- **Jira Key:** NONE (personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** 8-1 (feat/8-1-multiplayer-session)
- **Points:** 5
- **Priority:** p0

## Context

This story implements the turn barrier mechanism for multiplayer games. In a multi-player session, the system must wait for all connected players to submit their actions before proceeding to the next turn. A configurable timeout ensures the game doesn't hang indefinitely if a player becomes unresponsive.

**Key references:**
- sq-2/sidequest/game/turn_manager.py — Python implementation
- sq-2/sidequest/game/multiplayer_session.py — Session coordination
- Story 8-1 (MultiplayerSession) — now COMPLETE, provides the multi-client coordination layer

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T17:17:06Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26 | 2026-03-26T16:32:28Z | 16h 32m |
| red | 2026-03-26T16:32:28Z | 2026-03-26T17:17:06Z | 44m 38s |
| green | 2026-03-26T17:17:06Z | 2026-03-26T17:17:06Z | 0s |
| review | 2026-03-26T17:17:06Z | 2026-03-26T17:17:06Z | 0s |
| finish | 2026-03-26T17:17:06Z | - | - |

## Sm Assessment

Story 8-2 builds directly on 8-1's MultiplayerSession. The barrier-sync logic already exists in `submit_action()` → `TurnStatus::Waiting|Resolved`. This story adds the **timeout** dimension: if a player doesn't submit within a configurable window, the turn auto-resolves without them.

**Key design concern:** The timeout mechanism requires async (tokio timer or similar) even though MultiplayerSession is synchronous. TEA should design tests that capture timeout behavior — likely a `TurnBarrier` wrapper or `TimeoutConfig` struct that composes with MultiplayerSession.

**Risk:** Low — 8-1 already proved out the barrier pattern. This extends it with time-based auto-resolution.

**Decision:** Proceed to RED phase. No blockers.

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

No design deviations yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->