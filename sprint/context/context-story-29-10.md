---
parent: context-epic-29.md
---

# Story 29-10: TacticalEntity Model + Token Rendering

## Business Context

A tactical map without tokens is a floor plan, not a game. This story adds the entity
model (PC, NPC, creature positioned on the grid) and renders them as SVG tokens with
faction coloring. This is the foundation for narrator placement (29-11), click-to-move
(29-12), and encounter binding (29-14).

## Technical Approach

### Step 1: Define TacticalEntity in sidequest-game

In `sidequest-game/src/tactical/entity.rs`:

```rust
pub struct TacticalEntity {
    pub id: String,
    pub name: String,
    pub position: GridPos,
    pub size: EntitySize,  // Medium(1), Large(2), Huge(3)
    pub faction: Faction,  // Player, Hostile, Neutral, Ally
    pub icon: Option<String>,  // optional custom icon identifier
}

pub enum EntitySize {
    Medium,  // 1x1 cell
    Large,   // 2x2 cells
    Huge,    // 3x3 cells
}

pub enum Faction {
    Player,
    Hostile,
    Neutral,
    Ally,
}
```

### Step 2: Entity registry on game state

Add `tactical_entities: Vec<TacticalEntity>` to the tactical state that travels with
the room. When a room is entered, entities are initialized from:
1. PC position (placed at entrance exit gap)
2. Pre-placed NPCs (from encounter data or narrator tool calls)
3. Dynamic placement via narrator `tactical_place` tool (story 29-11)

### Step 3: SVG token rendering in TacticalGridRenderer

Add a token layer to the SVG (above grid, below zones):
```
<g class="token-layer">
  {entities.map -> <g transform="translate(x*cellSize, y*cellSize)">
    <circle r={size*cellSize/2} fill={factionColor} />
    <text>{initial or icon}</text>
  </g>}
</g>
```

Faction colors:
- Player: blue (#2563EB)
- Hostile: red (#DC2626)
- Neutral: gray (#6B7280)
- Ally: green (#16A34A)

Large/Huge entities span multiple cells (circle radius scales with size).

### Step 4: Token tooltips

Hover over a token to see: name, faction, HP if visible (PC and known NPCs).
Use SVG `<title>` elements for native browser tooltips, or a custom positioned
tooltip component for richer info.

### Step 5: Wire entity data into TACTICAL_STATE

Extend the `TacticalStatePayload` from 29-5 to include entities. When building
the tactical state on room entry, populate the entity list from game state.

## Acceptance Criteria

- AC-1: TacticalEntity struct with id, name, position, size, faction
- AC-2: EntitySize enum covers Medium (1x1), Large (2x2), Huge (3x3)
- AC-3: Faction enum covers Player, Hostile, Neutral, Ally with distinct colors
- AC-4: SVG tokens render at correct grid positions
- AC-5: Large/Huge tokens span multiple cells visually
- AC-6: Faction colors are visually distinct and accessible
- AC-7: Hover tooltip shows entity name and faction
- AC-8: TACTICAL_STATE payload includes entity list
- AC-9: PC automatically placed at entrance exit gap on room entry
- AC-10: Wiring test: entity data flows from game state through TACTICAL_STATE to SVG render

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/tactical/entity.rs` | NEW: TacticalEntity, EntitySize, Faction |
| `sidequest-game/src/tactical/mod.rs` | ADD: pub mod entity |
| `sidequest-ui/src/components/TacticalGridRenderer.tsx` | ADD: token layer rendering |
| `sidequest-protocol/src/message.rs` | MODIFY: ensure TacticalEntityPayload in TacticalStatePayload |
| `sidequest-server/src/dispatch/tactical.rs` | MODIFY: populate entities in tactical state |
