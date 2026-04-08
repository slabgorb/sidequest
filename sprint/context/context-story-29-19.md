---
parent: context-epic-29.md
---

# Story 29-19: Wire Tactical Grid into MAP_UPDATE

## Business Context

Story 29-8 built the DungeonMapRenderer — multi-room SVG dungeon maps with fog of war,
zoom, shared-wall dedup. Story 29-5 defined the TACTICAL_STATE protocol payload. But
the pipe between them is missing: the server never sends grid data in MAP_UPDATE, and
the UI never reads it. The DungeonMapRenderer is dead code in production.

This story wires the full pipe so tactical grids appear in-game when a player explores
rooms that have `grid` fields in rooms.yaml.

## Technical Approach

### Wire 1: Protocol — Add tactical_grid to ExploredLocation

File: `sidequest-api/crates/sidequest-protocol/src/message.rs`
Struct: `ExploredLocation` (line ~1124)

Add field:
```rust
#[serde(default, skip_serializing_if = "Option::is_none")]
pub tactical_grid: Option<TacticalGridPayload>,
```

`TacticalGridPayload` already exists in the same file (line ~1348). It has `width`,
`height`, `cells: Vec<Vec<String>>`, `legend`, `exits`.

### Wire 2: Game — Populate tactical_grid in build_room_graph_explored

File: `sidequest-api/crates/sidequest-game/src/room_movement.rs`
Function: `build_room_graph_explored` (line ~171)

Currently builds `ExploredLocation` at line ~192 without a `tactical_grid` field.
Add: parse `room.grid` (the raw ASCII string from RoomDef) using the tactical grid
parser, convert to `TacticalGridPayload`, and set on the ExploredLocation.

The parser lives in `sidequest-game/src/tactical/grid.rs` — `TacticalGrid::parse()`.
The conversion from `TacticalGrid` to `TacticalGridPayload` needs a small helper
(TacticalGrid has typed cells, TacticalGridPayload has string cells for JSON).

`RoomDef.grid` is `Option<String>` (raw ASCII). `RoomDef.legend` provides the feature
legend. If `room.grid` is None, set `tactical_grid: None`.

### Wire 3: UI — Consume tactical_grid in useAutomapperData

File: `sidequest-ui/src/components/OverlayManager.tsx`
Function: `useAutomapperData` (line ~38)

Currently builds `ExploredRoom[]` without a `grid` field (lines 54-61). Add: read
`tactical_grid` from the MapState location data and convert to `TacticalGridData`
(the TypeScript type from `@/types/tactical`).

The conversion: `TacticalGridPayload` comes over the wire as JSON with string cell
types. `TacticalGridData` uses typed `TacticalCell` objects. Map each cell string
("floor", "wall", etc.) to the corresponding `TacticalCell` type.

## Acceptance Criteria

- AC-1: ExploredLocation has `tactical_grid: Option<TacticalGridPayload>` field
- AC-2: build_room_graph_explored parses RoomDef.grid and sets tactical_grid
- AC-3: Rooms without grid field produce tactical_grid: None (not an error)
- AC-4: useAutomapperData reads tactical_grid from MapState and sets ExploredRoom.grid
- AC-5: In a playtest with caverns_and_claudes/mawdeep, opening the map (M key) shows
  the tactical grid renderer instead of schematic rectangles
- AC-6: OTEL span emitted when tactical_grid is populated (subsystem: tactical)

## Key Files

| File | Action |
|------|--------|
| `sidequest-api/crates/sidequest-protocol/src/message.rs` | ADD: tactical_grid field to ExploredLocation |
| `sidequest-api/crates/sidequest-game/src/room_movement.rs` | MODIFY: build_room_graph_explored to populate tactical_grid |
| `sidequest-api/crates/sidequest-game/src/tactical/grid.rs` | READ: TacticalGrid::parse() for grid parsing |
| `sidequest-ui/src/components/OverlayManager.tsx` | MODIFY: useAutomapperData to consume tactical_grid |

## Dependencies

- **29-1** (done): ASCII grid parser
- **29-3** (done): Mawdeep room grids authored
- **29-5** (done): TacticalGridPayload protocol type
- **29-8** (done): DungeonMapRenderer + Automapper three-way delegation
