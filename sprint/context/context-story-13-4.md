---
parent: context-epic-13.md
---

# Story 13-4: Timeout Fallback with Player Notification

## Business Context

When a player goes AFK or is slow, the timeout auto-fills their action. But currently
this happens silently — nobody knows who timed out or that a default action was used.
Players need to see who held up the turn and what happened.

**Depends on:** 13-2 (sealed collection with timeout)

## Technical Approach

### Server-Side Changes

When `TurnBarrier::force_resolve_turn()` fires on timeout:
1. Identify players who haven't submitted via `pending_players()`
2. Auto-fill with contextual default: `"{character_name} hesitates, waiting to see what happens."`
3. Include auto-resolved player names in the ACTION_REVEAL message's `auto_resolved` field
4. Broadcast a TURN_STATUS with status `"auto_resolved"` for each timed-out player

### UI Changes

- TurnStatusPanel: timed-out players show a distinct "timed out" indicator (yellow/amber)
- ActionRevealBlock: auto-resolved actions render differently ("waited" vs actual action text)
- Optional: brief toast notification "Brak's turn was auto-resolved"

### Configurable Default Action

The default action should be configurable per turn mode:
- Structured: "hesitates, waiting to see what happens"
- Cinematic: "remains silent"
- Combat: "takes a defensive stance" (dodge/defend equivalent)

## Scope Boundaries

**In scope:**
- Identify and track auto-resolved players
- Notify party via TURN_STATUS and ACTION_REVEAL
- UI indicators for timed-out players
- Contextual default actions per mode

**Out of scope:**
- Kicking AFK players
- Adjusting timeout duration dynamically based on player behavior
- Per-player timeout settings

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Auto-resolved tracked | Server records which players timed out per turn |
| TURN_STATUS sent | Auto-resolved players get status "auto_resolved" |
| ACTION_REVEAL includes | auto_resolved field lists character names |
| UI indicator | Timed-out player shown differently in TurnStatusPanel |
| Default action | Auto-filled action is contextual to current mode |
| Notification | Party sees who was auto-resolved in the reveal block |
