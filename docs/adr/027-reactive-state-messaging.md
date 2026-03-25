# ADR-027: Reactive State Messaging

> Ported from sq-2. Adapted for WebSocket delivery.

## Status
Accepted

## Context
In Python, GameState emitted typed events via callback for TUI widgets. In the Rust port, the WebSocket replaces the callback — state changes are pushed to clients as typed messages.

## Decision
When game state changes, the server emits typed WebSocket messages to all connected clients:

| Event | Message Type | Trigger |
|-------|-------------|---------|
| Party changed | `PARTY_STATUS` | Character HP/status/level change |
| Sheet updated | `CHARACTER_SHEET` | Stats, abilities, or backstory change |
| Inventory changed | `INVENTORY` | Items added/removed/promoted |
| Map updated | `MAP_UPDATE` | New region discovered or location changed |
| Combat state | `COMBAT_EVENT` | Combat starts/ends, turn changes |

### Pattern
```rust
fn emit_state_changes(pre: &GameState, post: &GameState, ws: &WsSender) {
    if pre.characters != post.characters {
        ws.send(GameMessage::PartyStatus { ... });
    }
    if pre.combat != post.combat {
        ws.send(GameMessage::CombatEvent { ... });
    }
    // etc
}
```

State comparison happens after every turn. Only changed subsystems emit messages.

## Consequences
- Client overlays update in real-time without polling
- Server controls which changes are significant enough to push
- Bandwidth-efficient — only changed state is sent
