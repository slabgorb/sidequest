---
story_id: "13-3"
jira_key: "none"
epic: "13"
workflow: "tdd"
---
# Story 13-3: Action reveal broadcast — show each player's submitted action to the full party alongside narration

## Story Details
- **ID:** 13-3
- **Jira Key:** none (personal project)
- **Epic:** 13 — Sealed Letter Turn System
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Priority:** P0

## Scope

Broadcast each player's submitted action to the full party, displayed alongside narration. During the sealed-letter turn system, players submit actions simultaneously without seeing others' choices. Once all actions are submitted, the game reveals each player's action as part of the turn narration.

**Acceptance criteria:**
1. Server tracks submitted actions per player per turn
2. Upon action reveal (all players ready or timeout), sends ActionReveal message to all clients
3. Each ActionReveal includes player ID, submitted action text, and timing metadata
4. UI displays action in the narration sequence with visual distinction
5. Protocol defines ActionReveal message shape (serde serialization)

## Workflow Tracking
**Workflow:** tdd
**Phase:** review
**Phase Started:** 2026-03-30T13:03:06Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-30T13:00:00Z | - | - |

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-protocol/src/message.rs` — Added ActionReveal variant to GameMessage, ActionRevealPayload and PlayerActionEntry structs with deny_unknown_fields
- `sidequest-ui/src/types/protocol.ts` — Added ACTION_REVEAL to MessageType enum
- `sidequest-ui/src/screens/NarrativeView.tsx` — Added action-reveal segment type, buildSegments handler (with chunk flushing), and renderSegment display with character names and auto-resolved indicators

**Tests:** 64/64 Rust protocol, 38/38 UI (23 NarrativeView + 15 ActionReveal) — all GREEN
**Branch:** feat/13-3-action-reveal-broadcast (pushed in both repos)

**Handoff:** To next phase (review)