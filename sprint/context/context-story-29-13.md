---
parent: context-epic-29.md
---

# Story 29-13: EffectZone Overlays + tactical_hazard Tool

## Business Context

Spell radii, trap areas, environmental hazards, and ability targeting all need visual
representation on the tactical grid. EffectZones are semi-transparent SVG overlays in
four shapes (circle, cone, line, rect). The narrator creates them via the `tactical_hazard`
tool call.

## Technical Approach

### Step 1: Define EffectZone in sidequest-game

In `sidequest-game/src/tactical/zone.rs`:

```rust
pub struct EffectZone {
    pub id: String,
    pub label: String,
    pub shape: ZoneShape,
    pub color: String,       // hex color for overlay
    pub opacity: f32,        // 0.0-1.0
    pub is_hazard: bool,     // affects entities inside
    pub damage_per_turn: Option<i32>,
}

pub enum ZoneShape {
    Circle { center: GridPos, radius: u32 },
    Cone { origin: GridPos, direction: CardinalDirection, angle: u32 },
    Line { start: GridPos, end: GridPos, width: u32 },
    Rect { x: u32, y: u32, w: u32, h: u32 },
}
```

### Step 2: SVG zone rendering

Add zone layer to TacticalGridRenderer (above tokens):
```
<g class="zone-layer" style="pointer-events: none">
  {zones.map -> zone-shape SVG element with semi-transparent fill}
</g>
```

Shape rendering:
- Circle: `<circle cx cy r fill-opacity="0.3">`
- Cone: `<path>` with arc (origin + direction + angle)
- Line: `<line>` with stroke-width
- Rect: `<rect x y width height fill-opacity="0.3">`

### Step 3: Define tactical_hazard tool

In `sidequest-agents/src/tools/tactical_hazard.rs`:

Tool call schema:
```json
{
  "tool": "tactical_hazard",
  "id": "poison_cloud_1",
  "label": "Poison Cloud",
  "shape": "circle",
  "center": [6, 6],
  "radius": 2,
  "color": "#00FF00",
  "is_hazard": true,
  "damage_per_turn": 2
}
```

### Step 4: Define tactical_remove tool

In `sidequest-agents/src/tools/tactical_remove.rs`:

Removes entities or zones by ID. Used for: death, flee, spell expiry.
```json
{
  "tool": "tactical_remove",
  "id": "poison_cloud_1"
}
```

### Step 5: Wire into dispatch

Same pattern as tactical_place (29-11):
1. Extract from narrator game_patch in assemble_turn
2. Apply to tactical zone/entity registry
3. Send updated TACTICAL_STATE
4. OTEL: `tactical.zone_created`, `tactical.entity_removed`, `tactical.zone_removed`

### Step 6: Add to narrator prompt schema

Add `tactical_hazard` and `tactical_remove` to the narrator's game_patch output format
in `narrator.rs`, alongside `tactical_place` from 29-11.

## Acceptance Criteria

- AC-1: EffectZone struct with 4 shape variants (Circle, Cone, Line, Rect)
- AC-2: SVG renders circle zones as semi-transparent circles at correct position/radius
- AC-3: SVG renders rect zones as semi-transparent rectangles
- AC-4: SVG renders line zones with correct width
- AC-5: SVG renders cone zones with correct origin, direction, and angle
- AC-6: `tactical_hazard` tool creates EffectZone from narrator game_patch
- AC-7: `tactical_remove` tool removes entities or zones by ID
- AC-8: Updated TACTICAL_STATE sent after zone creation/removal
- AC-9: OTEL events for zone_created, zone_removed, entity_removed
- AC-10: Wiring test: narrator game_patch with tactical_hazard flows through to SVG render

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/tactical/zone.rs` | NEW: EffectZone, ZoneShape |
| `sidequest-game/src/tactical/mod.rs` | ADD: pub mod zone |
| `sidequest-agents/src/tools/tactical_hazard.rs` | NEW: hazard tool handler |
| `sidequest-agents/src/tools/tactical_remove.rs` | NEW: remove tool handler |
| `sidequest-agents/src/tools/mod.rs` | ADD: pub mod tactical_hazard, tactical_remove |
| `sidequest-agents/src/agents/narrator.rs` | MODIFY: add tactical_hazard, tactical_remove to schema |
| `sidequest-ui/src/components/TacticalGridRenderer.tsx` | ADD: zone layer rendering |
