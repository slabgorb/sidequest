---
story_id: "67-3"
jira_key: "67-3"
epic: "epic-67"
workflow: "trivial"
---
# Story 67-3: MP peer-visibility consolidation + slow-typist reassurance (one canonical surface, Composing/Sealed/Resolving)

## Story Details
- **ID:** 67-3
- **Jira Key:** 67-3
- **Epic:** epic-67 (Multiplayer resilience & presence)
- **Workflow:** trivial
- **Type:** bug
- **Points:** 3
- **Priority:** p2
- **Repos:** ui
- **Stack Parent:** none

## Story Context

This story is part of **Epic 67: Multiplayer resilience & presence** (Playtest-3 findings). See `sprint/context/context-epic-67.md` for full epic context and architecture.

**Problem:** Shared-turn / peer-visibility status was scattered across surfaces, and slow typists (like Alex) had no reassurance the table was waiting *with* them, not *on* them. This story consolidates peer-visibility/shared-turn status into ONE canonical surface with the Composing/Sealed/Resolving status the table reads, plus slow-typist reassurance messaging.

**Related ADR:** ADR-036 (Multiplayer Turn Coordination) — submit-and-wait barrier, peer action text visible during wait phase per 2026-05-03 amendment.

**Tech foundation:**
- WebSocket lifecycle: `hooks/useWebSocket.ts` and `hooks/useGameSocket.ts`
- GameBoard turn state: `components/GameBoard.tsx`
- ADR-036 turn states: Composing (collecting player inputs), Sealed (all inputs locked), Resolving (narration in progress)

## Workflow Tracking

**Workflow:** trivial  
**Phase:** setup  
**Phase Started:** 2026-05-28T13:26:45Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T13:26:45Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement  
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
