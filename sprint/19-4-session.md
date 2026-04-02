---
story_id: "19-4"
epic: "19"
jira_key: null
workflow: "tdd"
repos: "sidequest-api"
---

# Story 19-4: MAP_UPDATE for room graph — send discovered rooms with exits to UI

## Story Details

- **ID:** 19-4
- **Epic:** 19 — Dungeon Crawl Engine — Room Graph Navigation & Resource Pressure
- **Jira Key:** N/A (personal project)
- **Workflow:** tdd
- **Repos:** sidequest-api
- **Points:** 3
- **Priority:** p1
- **Stack Parent:** none (standalone story)

## Acceptance Criteria

- ExploredLocation includes exits, room_type, size fields
- MAP_UPDATE only includes discovered rooms
- Current room flagged in payload
- Protocol types updated in sidequest-protocol
- Test: discover 3 rooms, verify MAP_UPDATE contains exactly 3 with correct exits

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T18:10:00Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T18:10:00Z | - | - |

## Context & Dependencies

### Upstream Work

- **19-1** (DONE): RoomDef + RoomExit structs — room graph data model in sidequest-genre
- **19-2** (DONE): Validated room movement — location constrained to room_id with exit check
- **19-3** (DONE): Trope tick on room transition — fire trope engine per room move

All upstream stories are complete. RoomDef, RoomExit, and discovered_rooms tracking are in place. This story wires the discovered room graph into the MAP_UPDATE protocol message.

### Feature Description

Extend the MAP_UPDATE message in sidequest-protocol to include room graph metadata for automapper rendering. When navigation_mode is RoomGraph:
1. Each ExploredLocation includes: room_exits, room_type, size, is_current_room
2. MAP_UPDATE contains only discovered rooms (fog of war)
3. UI receives structured data to render a dungeon floorplan

Data flow:
```
GameSnapshot.discovered_rooms (HashSet<String>)
  ↓
IntentRouter/WorldStatePatch.location
  ↓
GameMessage::MAP_UPDATE with ExploredLocation[]
  ↓
sidequest-ui receives structured room graph
  ↓
Automapper component renders dungeon floorplan
```

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
