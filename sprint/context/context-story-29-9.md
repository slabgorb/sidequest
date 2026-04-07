---
parent: context-epic-29.md
---

# Story 29-9: Author ASCII Grids for Grimvault (18 Rooms)

## Business Context

Grimvault is the second C&C world -- The Patient Butcher's workshop. Its aesthetic is
the opposite of Mawdeep: precise, geometric, deliberately constructed. This provides
variety in grid shapes and validates that the system handles both organic and constructed
room styles. It also exercises the validator and layout engine on a second complete dungeon.

## Technical Approach

### Step 1: Review Grimvault room descriptions

Grimvault's rooms are functional spaces in a workshop/processing facility:
- **threshold** (3x2): Rectangular, polished stone, tool marks
- **receiving** (3x3): Wide, low ceiling, hundreds of small niches
- **sorting_floor**: Processing area with stations
- Rooms have a clinical, precise aesthetic -- more rectangular shapes, clean angles

### Step 2: Choose appropriate shapes

Unlike Mawdeep's organic caverns, Grimvault rooms should be:
- More angular but not all rectangles (L-shapes, alcoves, stepped walls)
- Some rooms nearly rectangular with deliberate imperfections
- Processing rooms with internal features (tables, stations as cover/interactable)
- Corridors that are wider and more uniform than Mawdeep's

### Step 3: Author grids with tactical_scale: 4

Same scale as Mawdeep for consistency. Apply legend entries for Grimvault-specific
features:
- `T` for tables/workstations (cover, interactable)
- `N` for niches (atmosphere)
- `G` for grates/drains (hazard or atmosphere)
- `L` for lecterns/pedestals (interactable)

### Step 4: Validate

Run `sidequest-validate --tactical --genre caverns_and_claudes` covering both worlds.

### Step 5: Test layout

Run the layout engine (29-6/29-7) on Grimvault's room graph. Verify it produces a
valid DungeonLayout with shared walls and no overlaps.

## Acceptance Criteria

- AC-1: All 18 Grimvault rooms have `grid`, `tactical_scale`, and `legend` fields
- AC-2: Room shapes reflect the clinical/geometric aesthetic (angular, deliberate)
- AC-3: Exit gaps match existing exit definitions
- AC-4: Legend entries match Grimvault's workshop features
- AC-5: All grids pass 8 validation rules
- AC-6: Layout engine produces valid DungeonLayout for Grimvault
- AC-7: `sidequest-validate --tactical --genre caverns_and_claudes` exits 0 (both worlds)

## Key Files

| File | Action |
|------|--------|
| `sidequest-content/genre_packs/caverns_and_claudes/worlds/grimvault/rooms.yaml` | ADD: grid, tactical_scale, legend to all 18 rooms |
