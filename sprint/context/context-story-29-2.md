---
parent: context-epic-29.md
---

# Story 29-2: Tactical Grid Validation in sidequest-validate

## Business Context

Grid errors must be caught at authoring time, not runtime. The 8 validation rules from
ADR-071 ensure every tactical grid is structurally sound before it reaches the game
engine. This is the quality gate for all content authored in stories 29-3, 29-9, and 29-15.

## Technical Approach

### Step 1: Add --tactical flag to sidequest-validate CLI

In `sidequest-validate/src/main.rs` (line 19), add a `--tactical` flag to Cli struct.
When present, run tactical validation on all rooms that have a `grid` field in addition
to the existing YAML schema validation.

### Step 2: Implement the 8 validation rules

Create `sidequest-validate/src/tactical.rs` with a function:
`fn validate_tactical_grid(room: &RoomDef, grid: &TacticalGrid) -> Vec<ValidationError>`

Rules (from ADR-071 section 9):
1. **Dimensions match** -- grid rows/cols == `size * tactical_scale`
2. **Exit coverage** -- every exit in `exits[]` has a matching wall gap
3. **No orphan gaps** -- no wall gaps exist without a corresponding exit
4. **Perimeter closure** -- no floor cells adjacent to void cells without wall between
5. **Flood fill connectivity** -- all interior floor cells mutually reachable from any floor cell
6. **Legend completeness** -- all uppercase glyphs in grid have a legend entry
7. **Legend placement** -- no legend glyphs placed on wall or void cells
8. **Exit gap width compatibility** -- between connected rooms (requires room graph context)

Rules 1-7 are per-room. Rule 8 requires cross-room context (pairs of connected rooms).

### Step 3: Integrate into validate_world()

In `sidequest-validate/src/main.rs`, `validate_world()` (line 189) already loads
`Vec<RoomDef>` for rooms.yaml. After YAML schema validation passes, parse each room's
grid (if present) using the parser from 29-1, then run tactical validation.

### Step 4: Cross-room exit compatibility check

After all rooms in a world are validated individually, run pairwise exit gap width
checks for connected rooms. If Room A's exit to Room B has width 2 and Room B's
exit to Room A has width 3, emit a warning (the narrower determines passage width).

## Acceptance Criteria

- AC-1: `--tactical` flag accepted by CLI (backwards-compatible: without flag, existing behavior unchanged)
- AC-2: Perimeter closure check catches floor cells adjacent to void without wall
- AC-3: Flood fill catches disconnected floor regions within a single room
- AC-4: Exit matching validates every exit has a corresponding wall gap
- AC-5: Orphan gap detection catches wall gaps with no exit definition
- AC-6: Legend validation catches undefined glyphs and misplaced legend features
- AC-7: Dimension check validates grid size against `size * tactical_scale`
- AC-8: Cross-room exit width compatibility check runs for connected room pairs
- AC-9: Each validation rule has unit test with known-bad input
- AC-10: Wiring test: `sidequest-validate --tactical --genre caverns_and_claudes` runs end-to-end after 29-3 content exists

## Key Files

| File | Action |
|------|--------|
| `sidequest-validate/src/main.rs` | ADD: --tactical flag, wire tactical validation into validate_world() |
| `sidequest-validate/src/tactical.rs` | NEW: 8 validation rules, ValidationError type |
| `sidequest-validate/Cargo.toml` | ADD: sidequest-game dependency (for TacticalGrid types) |
