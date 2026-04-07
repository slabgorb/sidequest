---
parent: context-epic-29.md
---

# Story 29-3: Author ASCII Grids for Mawdeep (18 Rooms)

## Business Context

Mawdeep is the first C&C world and the initial testbed for tactical grids. Its 18 rooms
have descriptions, sizes, and exits already defined in rooms.yaml. This story adds ASCII
grids to every room, making Mawdeep the first fully tactical dungeon. The grids must
express the organic, biological horror aesthetic (The Glutton Below) through non-rectangular
shapes -- ovals, irregular caverns, constricted passages.

## Technical Approach

### Step 1: Review room descriptions and sizes

Each room in `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml`
has a `size` field (grid units) and a `description` with spatial information. The grid
must match both. Key spatial details from descriptions:

- **mouth** (3x3): "Sixty feet across", oval/circular, two exits
- **throat** (2x1): "Wide enough for three abreast", corridor, ribbed walls
- **antechamber** (2x2): "Roughly circular", three archways
- **cistern** (2x2): Domed, sunken pool center feature
- **junction** (3x3): High vaulted ceiling, crossroads, four exits
- **gallery** (3x2): "Long rectangular room", alcoves
- **pantry** (2x1): "Low-ceilinged", narrow
- **hall** (3x3): "Vast hall with domed ceiling", stone well center feature
- **chute** (1x1): Steep, smooth, one-way
- **stairs_down** (1x2): Carved staircase, uneven steps

Level 2 rooms follow the same pattern with increasing organic/biological shapes.

### Step 2: Choose tactical_scale

Use `tactical_scale: 4` (4 cells per grid unit) as default. A 3x3 room becomes 12x12
cells -- enough resolution for tactical play without overwhelming the ASCII. Corridors
(2x1) become 8x4.

### Step 3: Author grids with non-rectangular shapes

Every room should use void cells (`_`) to create organic shapes. No rectangular rooms
in Mawdeep -- it's a living dungeon, not a conference center. Use:
- Ovals for natural caverns (mouth, antechamber, landing)
- Irregular shapes for organic rooms (belly, acid_pool)
- Narrow irregular corridors (throat, gullet_passage)
- L-shapes or T-shapes for junctions

### Step 4: Add legend entries for features

Map uppercase letters to features described in room descriptions:
- `P` for pillars/stumps (cover)
- `W` for well/pool (interactable or hazard)
- `A` for alcoves (atmosphere)
- `S` for shelves/supplies (interactable)

### Step 5: Validate with sidequest-validate --tactical

After all grids are authored, run validation (story 29-2) to catch structural errors.

## Acceptance Criteria

- AC-1: All 18 Mawdeep rooms have `grid`, `tactical_scale`, and `legend` fields
- AC-2: No rectangular rooms -- every room uses void cells for organic shapes
- AC-3: Exit gaps in grids match existing exit definitions (count, position)
- AC-4: Legend entries match spatial features described in room descriptions
- AC-5: Grids pass all 8 validation rules from story 29-2
- AC-6: Level 1 rooms (mouth through stairs_down) complete
- AC-7: Level 2 rooms (landing through belly) complete
- AC-8: `sidequest-validate --tactical --genre caverns_and_claudes` exits 0

## Key Files

| File | Action |
|------|--------|
| `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml` | ADD: grid, tactical_scale, legend to all 18 rooms |
