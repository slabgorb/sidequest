---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-4: MAP_UPDATE for room graph — send discovered rooms with exits to UI

## Business Context

The automapper UI (19-8) needs structured room graph data. This story extends the existing MAP_UPDATE protocol message to include room exits, room_type, size, and a current_room flag. Only discovered rooms are sent (fog of war). The UI receives everything it needs to render a dungeon map.

## Technical Guardrails

- `GameMessage::MapUpdate` and `ExploredLocation` already exist in `sidequest-protocol/src/message.rs`. Extend — don't replace.
- New fields on ExploredLocation: `exits: Vec<ExitInfo>`, `room_type: Option<String>`, `size: Option<String>`, `is_current: bool`. All optional so region-mode MAP_UPDATEs still work.
- `ExitInfo` struct: `direction: String`, `exit_type: String`, `target_discovered: bool` (whether the exit leads to a discovered room — for partial fog of war on exits).
- MAP_UPDATE fires after a valid room transition (after 19-2). Sends the full `discovered_rooms` set with their metadata.
- Undiscovered rooms are omitted entirely. Exits to undiscovered rooms show direction and type but `target_discovered: false`.

## Scope Boundaries

**In scope:**
- Extend ExploredLocation with exits, room_type, size, is_current
- New ExitInfo protocol type
- MAP_UPDATE sends discovered room graph after room transition
- Fog of war: undiscovered rooms omitted, exits to them flagged

**Out of scope:**
- Automapper UI rendering (19-8)
- Region mode MAP_UPDATE changes (keep existing behavior)

## AC Context

1. ExploredLocation includes exits, room_type, size fields
2. MAP_UPDATE only includes discovered rooms
3. Current room flagged in payload
4. Protocol types updated in sidequest-protocol
5. Test: discover 3 rooms, verify MAP_UPDATE contains exactly 3 with correct exits
