---
parent: context-epic-13.md
---

# Story 13-1: Turn Collection UI — Show Pending/Submitted Status Per Player

## Business Context

Players have zero visibility into the turn cycle. They don't know who's submitted, who's
still thinking, or whether the system is waiting on them. This makes multiplayer feel
chaotic and unresponsive. A turn status panel is the minimum viable feedback loop.

**Playtest evidence:** "It's a free-for-all. Whoever wants to type in first and get the
narrator again, everybody else has to wait."

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

## Scope Boundaries

**In scope:**
- TurnStatusPanel component with per-player status indicators
- Input disable after local submission
- TURN_STATUS message handling
- Show/hide based on turn mode

**Out of scope:**
- Action reveal (13-3)
- Timeout notifications (13-4)
- Server-side changes to hold actions (13-2)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Panel renders | In Structured mode, panel shows all party members with status |
| Real-time updates | When another player submits, their status changes within 1s |
| Input locks | After submitting, input field is disabled with waiting message |
| Input unlocks | After narration completes, input re-enables for next turn |
| Mode-aware | Panel hidden in FreePlay, visible in Structured/Cinematic |
| Names shown | Displays character names, not player IDs |
