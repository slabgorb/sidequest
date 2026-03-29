---
parent: context-epic-13.md
---

# Story 13-5: Turn Mode Indicator in UI

## Business Context

Players don't know what turn rules are active. When combat starts and the mode switches
from FreePlay to Structured, nothing tells them. A small indicator with tooltip explains
the current mode and helps players understand why their input behavior changed.

## Technical Approach

### New Component: TurnModeIndicator

Small badge in the game header or sidebar:
- **Free Play** (green) — "Actions resolve immediately"
- **Structured** (blue) — "All players submit before the narrator responds"
- **Cinematic** (purple) — "The narrator sets the pace"

### WebSocket Integration

The server already sends mode transitions implicitly via TURN_STATUS messages. May need
an explicit TURN_MODE message or include `turn_mode` in TURN_STATUS payloads.

Check existing TURN_STATUS payload — if it doesn't include mode, add `mode: String` field.

### Animation

Smooth transition animation when mode changes (fade/slide). Brief highlight to draw
attention to the change.

## Scope Boundaries

**In scope:**
- TurnModeIndicator component with three mode states
- Tooltip explaining each mode
- Transition animation
- Mode field in protocol if not already present

**Out of scope:**
- Player ability to change modes (DM only)
- Mode history

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Indicator visible | Badge shows current turn mode in game UI |
| Three modes | Free Play, Structured, Cinematic each have distinct appearance |
| Tooltip | Hovering explains what the mode means |
| Transitions | Mode change animates to draw attention |
| Real-time | Updates within 1s of server mode change |
