---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-1: RoomDef + RoomExit structs — room graph data model in sidequest-genre

## Business Context

Foundation for the entire dungeon crawl engine. Without the room graph data model, nothing else in Epic 19 can start. RoomDef/RoomExit/NavigationMode types already exist in `sidequest-genre/src/models.rs` — this story is about verifying they're complete, loading rooms.yaml from world directories, and validating the graph (exit targets exist, bidirectional routes except chutes, no orphans).

## Technical Guardrails

- Types already exist: `NavigationMode` (line ~1765), `RoomExit` (line ~1781), `RoomDef` (line ~1796) in `models.rs`. Tests exist in `room_graph_story_19_1_tests.rs`. Verify completeness before writing new code.
- Rooms loaded from `worlds/{world}/rooms.yaml` alongside `cartography.yaml`. The genre loader (`loader.rs`) already handles CartographyConfig.
- `navigation_mode` defaults to `Region`. Existing genre packs must be unaffected.
- Validation in `validate.rs`: all exit targets reference existing room IDs, bidirectional exits (except `chute_down`), no orphaned rooms.
- `serde(deny_unknown_fields)` already on both structs — good.

## Scope Boundaries

**In scope:**
- Verify/complete RoomDef, RoomExit, NavigationMode structs
- rooms.yaml loading in genre loader
- Room graph validation (exits, bidirectional, orphan detection)
- Unit tests for deserialization and validation
- All existing genre packs continue to work (navigation_mode defaults to Region)

**Out of scope:**
- Movement validation (19-2)
- Room transition events (19-3)
- Any server/dispatch changes

## AC Context

1. RoomDef, RoomExit, NavigationMode structs in models.rs — complete with all fields from ADR-055
2. rooms.yaml loaded and parsed alongside cartography.yaml via genre loader
3. Validation rejects invalid exit targets, missing bidirectional routes (non-chute), orphaned rooms
4. Existing genre packs unaffected (navigation_mode defaults to Region)
5. Unit tests for deserialization and validation
