---
parent: context-epic-29.md
---

# Story 29-1: ASCII Grid Parser

## Business Context

The ASCII grid in `rooms.yaml` is the source of truth for room geometry. Before anything
else can work -- validation, rendering, layout, pathfinding -- there must be a parser
that converts the multiline ASCII string into a structured `TacticalGrid` with typed
cells, legend resolution, and exit extraction from wall gaps.

## Technical Approach

### Step 1: Add tactical module to sidequest-game

Create `sidequest-game/src/tactical/mod.rs` with submodules for grid types and parsing.
This is a new domain module alongside combat, chase, encounter, etc.

New types:
- `TacticalCell` enum: `Floor`, `Wall`, `Void`, `DoorClosed`, `DoorOpen`, `Water`, `DifficultTerrain`, `Feature(char)`
- `CellProperties` struct: `walkable: bool`, `blocks_los: bool`, `movement_cost: f64`
- `GridPos` struct: `x: u32`, `y: u32` (with PartialEq, Eq, Hash for use as map keys)
- `FeatureDef` struct: `feature_type: FeatureType`, `label: String` (from legend)
- `FeatureType` enum: `Cover`, `Hazard`, `DifficultTerrain`, `Atmosphere`, `Interactable`, `Door`
- `ExitGap` struct: `wall: CardinalDirection`, `cells: Vec<u32>`, `width: u32`, `exit_index: usize`
- `TacticalGrid` struct: `width: u32`, `height: u32`, `cells: Vec<Vec<TacticalCell>>`, `legend: HashMap<char, FeatureDef>`, `exits: Vec<ExitGap>`

### Step 2: Implement glyph parser

Parse function: `fn parse_grid(raw: &str, legend: &HashMap<char, LegendEntry>) -> Result<TacticalGrid, GridParseError>`

Glyph vocabulary (from ADR-071):
- `.` -> Floor, `#` -> Wall, `_` -> Void
- `+` -> DoorClosed, `/` -> DoorOpen
- `~` -> Water, `,` -> DifficultTerrain
- `A-Z` -> Feature(char), resolved via legend

Error on: unknown glyphs, legend entries not found, uneven row lengths.

### Step 3: Implement exit extraction

Scan the grid perimeter (all four edges). Identify contiguous runs of non-wall,
non-void cells along wall edges. Each run is an `ExitGap`. Match gaps to exits
list by clockwise order (north edge left-to-right, east edge top-to-bottom,
south edge right-to-left, west edge bottom-to-top).

### Step 4: Add grid and legend fields to RoomDef

In `sidequest-genre/src/models/world.rs` (line 137), add optional fields to `RoomDef`:
- `grid: Option<String>` -- the raw ASCII grid
- `tactical_scale: Option<u32>` -- cells per grid unit
- `legend: Option<HashMap<char, LegendEntry>>` -- feature definitions

`LegendEntry` struct in genre models: `type: String`, `label: String`.

### Step 5: Wire parser into RoomDef loading

When `RoomDef` has a `grid` field, parse it eagerly during genre pack load
(in `sidequest-genre/src/loader.rs` or a new tactical module in genre crate).
Store the parsed `TacticalGrid` alongside the raw data. Fail loudly on parse errors.

## Acceptance Criteria

- AC-1: `TacticalCell` enum covers all 8 glyph types from ADR-071 vocabulary table
- AC-2: Parser correctly handles non-rectangular rooms (void cells carve irregular shapes)
- AC-3: Parser rejects unknown glyphs with descriptive error (glyph, position, room_id)
- AC-4: Parser rejects uneven row lengths (all rows must be same width)
- AC-5: Exit gaps extracted from wall perimeter match clockwise ordering
- AC-6: Legend glyphs (A-Z) resolve to FeatureDef with type and label
- AC-7: `RoomDef` gains optional `grid`, `tactical_scale`, `legend` fields (serde deserialization)
- AC-8: Parser has unit tests for: rectangular room, oval room (void cells), room with features, room with multiple exits
- AC-9: Integration test: parse the example grid from ADR-071 ("The Mouth")
- AC-10: Wiring test: parser is callable from non-test code path (genre loader or validate)

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/tactical/mod.rs` | NEW: module root, re-exports |
| `sidequest-game/src/tactical/grid.rs` | NEW: TacticalGrid, TacticalCell, GridPos types |
| `sidequest-game/src/tactical/parser.rs` | NEW: parse_grid(), exit extraction |
| `sidequest-genre/src/models/world.rs` | ADD: grid, tactical_scale, legend fields to RoomDef (line 137) |
| `sidequest-genre/src/models/world.rs` | ADD: LegendEntry struct |
| `sidequest-game/src/lib.rs` | ADD: pub mod tactical |
