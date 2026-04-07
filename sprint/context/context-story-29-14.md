---
parent: context-epic-29.md
---

# Story 29-14: StructuredEncounter Grid Binding

## Business Context

StructuredEncounter (Epic 28) tracks encounter state -- beats, metrics, actors, phases.
The tactical grid tracks spatial state -- positions, zones, terrain. This story binds
them: EncounterActor gains a GridPos, encounter beats can target spatial areas, and
the encounter system knows where entities are on the grid. This is what makes combat
tactical rather than just narrated.

## Technical Approach

### Step 1: Add GridPos to EncounterActor

In `sidequest-game/src/encounter.rs` (line 148), add an optional grid position to
EncounterActor:

```rust
pub struct EncounterActor {
    pub name: String,
    pub role: String,
    pub grid_pos: Option<GridPos>,  // NEW: tactical position
    pub entity_id: Option<String>,  // NEW: links to TacticalEntity
}
```

`grid_pos` is `Option` because not all encounters happen in tactical rooms (region-based
genres, rooms without grids).

### Step 2: Spatial beat targeting

Extend BeatDef (in `sidequest-genre/src/models/rules.rs`) with optional spatial
targeting:

```rust
pub struct BeatDef {
    // existing fields...
    pub targeting: Option<BeatTargeting>,  // NEW
}

pub enum BeatTargeting {
    Single,           // one entity at a position
    Area(ZoneShape),  // area effect at a position
    Self_,            // centered on the actor
}
```

When a beat has targeting, the narrator's beat selection includes a target position.
The dispatch pipeline creates an EffectZone for area beats.

### Step 3: Sync encounter actors with tactical entities

When an encounter starts in a tactical room:
1. Create TacticalEntity for each EncounterActor that has a grid_pos
2. Set faction based on actor role ("combatant" on hostile side = Hostile)
3. When actors are added/removed from the encounter, update tactical entities

When a tactical entity moves:
1. Update the corresponding EncounterActor's grid_pos

Function: `fn sync_encounter_to_tactical(encounter: &StructuredEncounter, entities: &mut Vec<TacticalEntity>)`

### Step 4: Range-based beat validation

Some beats should only be available within range. A melee attack beat requires
adjacency (Manhattan distance 1). A ranged attack beat has a max range.

Add to BeatDef: `pub range: Option<u32>` (in cells). The dispatch pipeline checks
distance between the actor's grid_pos and the target's grid_pos before allowing
the beat.

### Step 5: Wire into apply_beat

In `sidequest-game/src/encounter.rs`, `apply_beat()` (line 446) gains an optional
`target_pos: Option<GridPos>` parameter. If the beat has spatial targeting, the
target position is recorded and used for:
- Area damage: entities in the EffectZone take damage
- Single target: the entity at the target position is affected
- Range validation: reject beats where target is out of range

## Acceptance Criteria

- AC-1: EncounterActor has optional `grid_pos` and `entity_id` fields
- AC-2: BeatDef has optional `targeting` and `range` fields
- AC-3: Encounter actors sync to tactical entities on encounter start
- AC-4: Tactical entity movement updates EncounterActor grid_pos
- AC-5: Range validation rejects beats when target is beyond range
- AC-6: Area beats create EffectZones centered on target position
- AC-7: Encounter in non-tactical room works without grid_pos (graceful None handling)
- AC-8: OTEL: `encounter.spatial_beat` with beat_id, target_pos, range, affected_entities
- AC-9: Unit test: melee beat within range succeeds, out of range fails
- AC-10: Wiring test: encounter with tactical entities flows through apply_beat with spatial targeting

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/encounter.rs` | MODIFY: add grid_pos/entity_id to EncounterActor, spatial params to apply_beat |
| `sidequest-genre/src/models/rules.rs` | ADD: BeatTargeting, targeting/range fields to BeatDef |
| `sidequest-game/src/tactical/entity.rs` | ADD: sync_encounter_to_tactical() |
| `sidequest-server/src/dispatch/tactical.rs` | MODIFY: sync encounter actors after beat application |
