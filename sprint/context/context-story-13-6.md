---
parent: context-epic-13.md
---

# Story 13-6: DM Override for Turn Resolution

## Business Context

The DM shouldn't be hostage to a slow or AFK player. They need the ability to force-resolve
a turn (taking whatever actions are in) or extend the timeout when the party legitimately
needs more time to discuss strategy.

**Playtest evidence:** Keith had to use DM teleport hacks to work around system limitations.
DM tools need to cover turn management too.

**Depends on:** 13-2 (sealed collection must exist to override)

## Technical Approach

### New Protocol Message: DM_TURN_CONTROL

```rust
// Client → Server (DM only)
DmTurnControl {
    action: String,    // "force_resolve" | "extend_timeout"
    seconds: Option<u64>,  // for extend_timeout, how many seconds to add
}

// Server → All Clients (acknowledgment)
DmTurnControl {
    action: String,
    detail: String,  // "Turn force-resolved by DM" | "Timeout extended by 30s"
}
```

### Server-Side

- Validate sender is DM (check player role)
- `force_resolve`: call `TurnBarrier::force_resolve_turn()` immediately
- `extend_timeout`: reset the timeout timer with current + added seconds
- Broadcast acknowledgment to all players

### UI: DM Tool Panel Additions

Two buttons in the DM tools area (only visible to DM):
- **"Resolve Turn"** — force-resolve with confirmation dialog
- **"Extend Time" (+30s)** — extends timeout, shows countdown

## Scope Boundaries

**In scope:**
- DM_TURN_CONTROL message type
- Force-resolve and extend-timeout server handlers
- DM-only UI buttons
- Acknowledgment broadcast

**Out of scope:**
- DM setting custom timeout durations for the whole session
- DM pausing/unpausing the turn timer
- Non-DM players requesting extensions

## Acceptance Criteria

| AC | Detail |
|----|--------|
| DM-only | Non-DM players cannot send DM_TURN_CONTROL |
| Force works | Force-resolve collects available actions and triggers narration |
| Extend works | Timeout resets to current time + specified seconds |
| Broadcast | All players see DM action notification |
| UI buttons | DM sees resolve/extend buttons during Structured mode |
| Confirmation | Force-resolve requires confirmation click |
