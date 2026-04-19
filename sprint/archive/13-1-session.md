---
story_id: "13-1"
jira_key: "none"
epic: "13"
workflow: "tdd"
---
# Story 13-1: Turn collection UI — show pending/submitted status per player, disable input after submit

## Story Details
- **ID:** 13-1
- **Epic:** 13 (Sealed Letter Turn System — Simultaneous Input Collection with Player Visibility)
- **Workflow:** tdd
- **Stack Parent:** none (independent UI feature)
- **Points:** 5
- **Priority:** p0
- **Repos:** sidequest-ui

## Business Context

Players have zero visibility into the turn cycle. They don't know who's submitted, who's still thinking, or whether the system is waiting on them. This makes multiplayer feel chaotic and unresponsive. A turn status panel is the minimum viable feedback loop.

**Playtest evidence:** "It's a free-for-all. Whoever wants to type in first and get the narrator again, everybody else has to wait."

## Technical Approach

### New Component: TurnStatusPanel

```tsx
// Renders in the game sidebar during Structured/Cinematic mode
interface TurnStatusEntry {
  player_id: string;
  character_name: string;
  status: 'pending' | 'submitted' | 'auto_resolved';
}

// Listen for TURN_STATUS messages from WebSocket
// Update local state per player as submissions arrive
```

### WebSocket Integration

The server already sends TURN_STATUS messages (defined in Epic 8). The UI needs to:
1. Listen for TURN_STATUS with `status: "active"` (new turn started, all pending)
2. Listen for TURN_STATUS with `status: "submitted"` (individual player submitted)
3. Listen for TURN_STATUS with `status: "resolved"` (turn complete, narration incoming)

### Input Lock After Submit

After the local player submits their action:
- Disable the input field
- Show "Waiting for other players..." message
- Re-enable when the next turn begins (after narration)

### Visibility Rules

- Panel only visible in Structured and Cinematic modes
- In FreePlay mode (solo or non-combat), no panel — actions resolve immediately
- Panel auto-appears on mode transition

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Panel renders | In Structured mode, panel shows all party members with status |
| Real-time updates | When another player submits, their status changes within 1s |
| Input locks | After submitting, input field is disabled with waiting message |
| Input unlocks | After narration completes, input re-enables for next turn |
| Mode-aware | Panel hidden in FreePlay, visible in Structured/Cinematic |
| Names shown | Displays character names, not player IDs |

## Workflow Tracking
**Workflow:** tdd
**Phase:** review
**Phase Started:** 2026-03-30T12:43:11Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-30T12:32:33Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Test fix: AC-4 "clears waiting message" used single-player scenario**
  - Spec source: TurnStatusPanel.test.tsx, AC-4 test "clears waiting message when local player returns to pending"
  - Spec text: Original test rendered `entries={[LYRA_SUBMITTED]}` with `localPlayerId="p2"` and expected "Waiting for other players"
  - Implementation: Test updated to `entries={[LYRA_SUBMITTED, KAEL_PENDING]}` — adding a peer in pending state
  - Rationale: Single submitted player triggers `allSubmitted=true` → renders "Resolving turn..." not "Waiting for other players...". The test was exercising the wrong state. Fix adds a pending peer so the waiting path is actually tested.
  - Severity: minor
  - Forward impact: none — test now correctly validates the intended behavior

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/components/TurnStatusPanel.tsx` — Full presentational component: dedup entries, status indicators, waiting/resolving messages, mode-aware visibility, local player highlighting, onLocalStatusChange callback
- `src/components/__tests__/TurnStatusPanel.test.tsx` — Minor fix to AC-4 test scenario (see deviations)

**Tests:** 32/32 passing (GREEN)
**Branch:** feat/13-1-turn-collection-ui (pushed)

**Handoff:** To next phase (verify)