---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-2: Validated room movement — location constrained to room_id with exit check

## Business Context

The key mechanical enforcement story. When `navigation_mode` is `RoomGraph`, the narrator can't invent rooms — `WorldStatePatch.location` must be a valid room_id reachable via an exit from the current room. This is the "no silent fallbacks" principle applied to dungeon topology. Invalid moves are rejected, not silently corrected.

## Technical Guardrails

- `GameSnapshot.location` is currently a `String`. In room_graph mode it must match a room_id from the loaded room graph. In region mode, no change.
- Add `discovered_rooms: HashSet<String>` to `GameSnapshot` in `state.rs`. Rooms are discovered on entry. Starting room is the room with `room_type: entrance`.
- Validation happens in the dispatch pipeline when `WorldStatePatch.location` is applied. The validator needs access to the room graph (already on `DispatchContext.rooms`).
- Starting location set during `dispatch_connect` when session initializes — find the entrance room.
- OTEL event on valid room transition: `room.transition` with from_room, to_room, exit_type.
- OTEL event on rejected move: `room.invalid_move` with attempted_room, reason.

## Scope Boundaries

**In scope:**
- Location validation in room_graph mode (reject rooms without exit from current)
- `discovered_rooms` populated on room entry
- Starting location set to entrance room on session create
- Region mode behavior unchanged
- OTEL events for transitions and rejections

**Out of scope:**
- Trope tick on transition (19-3)
- MAP_UPDATE (19-4)
- Resource depletion (19-5)

## AC Context

1. Location validation in room_graph mode rejects rooms without exit from current
2. `discovered_rooms: HashSet<String>` populated on room entry
3. Starting location set to entrance room on session create
4. Region mode behavior unchanged
5. Integration test: move through 3-room sequence, reject invalid move
