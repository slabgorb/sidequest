# Story 19-10: Wire deplete_light_on_transition into room transition dispatch

## Summary

Wire the `deplete_light_on_transition()` method (implemented in 19-5) into the room
transition handler in the server dispatch layer. Add `GameMessage::ItemDepleted`
protocol variant and OTEL span for observability.

## Technical Approach

1. **Protocol:** Add `GameMessage::ItemDepleted { item_name, remaining_before }` to
   `sidequest-protocol/src/message.rs`
2. **Dispatch:** In the room transition handler (dispatch layer), call
   `inventory.deplete_light_on_transition()` after successful room movement
3. **Message firing:** If depletion returns `Some(exhausted_item)`, fire `ItemDepleted`
   message to all session participants
4. **OTEL:** Emit `inventory.light_depleted` span with `item_name` and `remaining_before`
   attributes

## Acceptance Criteria

- Room transition handler calls `deplete_light_on_transition()` with current inventory
- `deplete_light_on_transition()` decrements uses_remaining for active light source, returns `Option<Item>` if exhausted
- `GameMessage::ItemDepleted` variant added to protocol with item name + previous uses
- Dispatch fires `ItemDepleted` message when light source exhausted
- OTEL span `inventory.light_depleted` emitted with item_name, remaining_before
- Full wiring: room transition → deplete_light → inventory mutation → GameMessage → UI notification
- Test: room transition with 6-use torch, verify depletion at step 6, GameMessage fires, OTEL span recorded

## Dependencies

- **19-5** (DONE): Consumable item depletion — `uses_remaining`, `consume_use()`, `deplete_light_on_transition()`
- **19-1** (DONE): RoomDef + RoomExit structs
- **19-2** (DONE): Validated room movement
- **19-3** (DONE): Trope tick on room transition

## Key Files (Expected)

- `sidequest-protocol/src/message.rs` — GameMessage enum
- `sidequest-game/src/inventory.rs` — deplete_light_on_transition()
- `sidequest-server/src/dispatch/` — room transition handler
- `sidequest-game/src/` — state mutation layer
