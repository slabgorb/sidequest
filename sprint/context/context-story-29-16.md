---
parent: context-epic-29.md
---

# Story 29-16: World Builder Tactical Grid Generation

## Business Context

The World Builder agent generates world content (rooms, descriptions, exits) for genre
packs. With the template library (29-15), it needs to also generate tactical grids for
each room -- select a template by room_type and size, customize exits, add legend features,
and produce the grid field for rooms.yaml. This scales grid authoring from manual to
automated.

## Technical Approach

### Step 1: Add grid generation to World Builder skill

The sq-world-builder skill (referenced in the skills list) handles world content
generation. Add a tactical grid generation step to the room authoring pipeline.

When generating a room, the World Builder:
1. Reads `sidequest-content/templates/tactical/index.yaml`
2. Queries for templates matching the room's `room_type`, `size`, and exit count
3. Selects the best-fit template
4. Customizes the template:
   - Adjust exit positions to match the room's exits list
   - Add legend features based on room description (e.g., "pillar" -> P cover feature)
   - Mirror/rotate if needed for exit alignment

### Step 2: Template customization logic

Create a script or Rust utility: `scripts/tactical_grid_from_template.py` or
integrate into the existing World Builder flow.

Customization steps:
1. **Exit positioning**: Find exit gaps in the template, remap to match the room's
   exit targets and directions
2. **Feature injection**: Parse room description for spatial keywords ("pillar",
   "pool", "altar", "chest") and place corresponding legend entries
3. **Mirror/rotate**: Templates may need horizontal/vertical mirroring or 90-degree
   rotation to align exits with the dungeon layout

### Step 3: Batch generation

Add a justfile recipe: `just tactical-grids genre world` that runs the World Builder
grid generation for all rooms in a world that don't already have grids. Non-destructive --
only adds grids to rooms missing them.

### Step 4: Validation integration

After grid generation, automatically run `sidequest-validate --tactical` on the
modified rooms.yaml. If validation fails, log the error and skip that room (don't
write a broken grid).

## Acceptance Criteria

- AC-1: World Builder selects template by room_type, size, and exit count
- AC-2: Template exits customized to match room's exit targets
- AC-3: Legend features injected based on room description keywords
- AC-4: Mirror/rotate support for exit alignment
- AC-5: Generated grids pass all 8 validation rules
- AC-6: Batch generation via justfile recipe for entire world
- AC-7: Non-destructive: rooms with existing grids are not overwritten
- AC-8: Validation runs automatically after generation

## Key Files

| File | Action |
|------|--------|
| `scripts/tactical_grid_from_template.py` | NEW: template selection + customization script |
| `justfile` | ADD: `tactical-grids` recipe |
| `sidequest-content/templates/tactical/index.yaml` | Reference: template metadata |
