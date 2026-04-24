---
id: 71
title: "Tactical ASCII Grid Maps — Deterministic Room Layout via ASCII Art"
status: superseded
date: 2026-04-07
deciders: [Keith Avery]
supersedes: []
superseded-by: 86
related: [86]
tags: [room-graph, game-systems]
implementation-status: retired
implementation-pointer: 86
---

# ADR-071: Tactical ASCII Grid Maps — Deterministic Room Layout via ASCII Art

> **Superseded by ADR-086 (Image-Composition Taxonomy) on 2026-04-24.**
>
> ASCII rendering of tactical maps is being removed from SideQuest. The
> tactical layer moves to image-native rendering via
> `ILLUSTRATION + CAMERA.TOPDOWN_90` (ADR-086 story 4). Spatial data
> (entity positions, AoE overlays, hazard zones) rides alongside as
> structured metadata rather than as a text grid.
>
> The requirements enumerated below (deterministic layout,
> non-rectangular rooms, Jaquayed topology, shared walls) remain real —
> they are now satisfied by the structured spatial metadata that
> accompanies the rendered map, not by ASCII art. The
> deterministic-visualization property shifts from "same ASCII every
> time" to "same spatial data every time, rendered by Z-Image with the
> TOPDOWN_90 camera."

## Context

SideQuest's dungeon crawl experience (particularly Caverns & Claudes) lacks visual tactical
maps. The current Automapper (story 19-8) renders room-to-room topology as labeled rectangles
connected by lines — useful for navigation but useless for tactical play. Players cannot see:

- Room geometry (shape, size, chokepoints)
- Entity positions (PC, NPC, creature locations on a grid)
- Hazard zones (traps, difficult terrain, environmental effects)
- Spell/ability radii and areas of effect
- Cover positions (pillars, furniture, rubble)

This forces players to interrogate the narrator over multiple turns just to understand spatial
layout — "how big is this room?", "where is the goblin?", "are there pillars?" The narrator
(Claude) knows the room description but has no structured spatial data to reference, so answers
are approximate and inconsistent.

### Requirements

1. **Deterministic** — same room data produces the same visual map every time
2. **Tactical** — grid squares with entity tokens, AoE overlays, hazard zones
3. **Non-rectangular rooms** — caverns are not conference rooms
4. **Jaquayed topology** — dungeon graphs with loops, not just trees
5. **Shared walls** — adjacent rooms share wall segments at exits
6. **No AI generation** — the map IS the data, not an interpretation of it
7. **Authorable at scale** — World Builder generates grids for hundreds of rooms

### Alternatives Considered

| Approach | Deterministic | Asset Cost | Non-Rect | Jaquayed | Scalable |
|----------|:---:|:---:|:---:|:---:|:---:|
| **LoRA-generated map images** | No | Low | Yes | No | Yes |
| **Canvas + PNG tileset** | Yes | High (per-genre spritesheet) | Limited | Yes | No |
| **Server-side tile composition (Rust)** | Yes | Medium | Limited | Yes | No |
| **ASCII grid → SVG (this ADR)** | Yes | Zero | Yes | Yes | Yes |

LoRA maps fail on determinism and can't do fog of war or token placement. Canvas tilesets
require per-genre spritesheet authoring — 11 genre packs × custom art = untenable. Server-side
composition adds daemon/infrastructure complexity for marginal visual benefit over SVG.

## Decision

### 1. ASCII Grid as Source of Truth

Each room in `rooms.yaml` gains an optional `grid` field — a multiline ASCII string
encoding the room's tactical floor plan at cell-level resolution.

```yaml
- id: mouth
  name: "The Mouth"
  room_type: entrance
  size: [3, 3]
  tactical_scale: 4  # cells per grid unit → 12×12 tactical grid
  grid: |
    ______####..####______
    ____##..........##____
    __##..............##__
    _#..................#_
    _#....PP............#_
    #....................#
    #....................#
    _#....PP............#_
    _#..................#_
    __##..............##__
    ____####..####________
    ______####..####______
  legend:
    P: { type: cover, label: "Worn tooth stumps" }
  exits:
    - type: corridor
      target: throat
    - type: corridor
      target: antechamber
```

#### Glyph Vocabulary

| Glyph | Meaning | Walkable | Blocks LOS |
|:---:|---------|:---:|:---:|
| `.` | Floor | Yes | No |
| `#` | Wall | No | Yes |
| `_` | Void (outside room bounds) | No | N/A |
| `+` | Door (closed) | Conditional | Conditional |
| `/` | Door (open) | Yes | No |
| `~` | Water/liquid | Conditional | No |
| `,` | Difficult terrain | Yes (half speed) | No |
| A-Z | Legend-defined feature | Per legend | Per legend |

Single uppercase letters are reserved for the feature legend. The legend maps each
glyph to a type, label, and optional mechanical properties.

#### Feature Types

| Type | Meaning | Example |
|------|---------|---------|
| `cover` | Provides cover, blocks movement | Pillar, overturned table |
| `hazard` | Damages or debuffs on entry/turn | Lava, poison gas, trap |
| `difficult_terrain` | Half movement speed | Rubble, thick undergrowth |
| `atmosphere` | Visual/narrative only, no mechanical effect | Ribbed walls, bloodstain |
| `interactable` | Player can interact (examine, use) | Lever, chest, altar |
| `door` | Blocks passage until opened | Locked door, portcullis |

### 2. Non-Rectangular Room Support

Rooms are NOT assumed rectangular. The `_` (void) glyph marks cells outside the room's
bounds within the bounding box. The room shape is defined by the wall (`#`) perimeter
enclosing floor (`.`) cells. Ovals, L-shapes, kidney shapes, and irregular caverns are
all supported naturally.

A "nearly circular" room in ASCII:

```
____####____
__##....##__
_#........#_
#..........#
#..........#
_#........#_
__##....##__
____####____
```

This reads as circular at any reasonable rendering scale. Tabletop RPG players have
mapped circles on square grids for 50 years.

### 3. Corridors Are Rooms

Every passageway is a `RoomDef` with its own grid, description, exits, and features.
There are no auto-generated connector segments between rooms. "The Throat" is not a
hallway between rooms — it's an ambush site, a chokepoint, a room in its own right.

This means:
- Adjacent rooms share walls directly
- Every cell in the dungeon belongs to exactly one room
- The room graph IS the dungeon graph — no separate corridor data structure

### 4. Shared-Wall Placement

Adjacent rooms share a wall segment. The exit gap in Room A's wall and the exit gap
in Room B's wall are the same physical opening. In the global dungeon grid, shared
walls merge — one row of `#` with a gap, not two.

The parser extracts exit positions from wall gaps in each room's grid perimeter. The
layout engine aligns rooms such that connected exit gaps face each other at the shared
wall boundary.

#### Exit Position Extraction

The parser scans the grid perimeter and identifies contiguous gaps (non-wall, non-void
cells along a wall edge). Each gap is matched to an exit in the `exits` list by order
(clockwise from north). The extracted data:

```
{ wall: "north", cells: [2, 3], width: 2 }
```

#### Alignment Constraint

For two rooms A and B connected by an exit:
- A's exit gap faces B (correct wall side)
- B's corresponding exit gap faces A
- Gap widths are compatible (equal, or the narrower determines the passage width)
- Gap positions align when rooms are placed in global coordinates

### 5. Jaquayed (Cyclic) Layout Algorithm

Dungeon graphs with loops (jaquayed topology) require a layout algorithm that goes
beyond BFS tree placement. Adopting the hierarchical decomposition approach from
Enter the Gungeon's procedural system:

1. **Detect cycles** in the room graph (DFS back-edge detection)
2. **Lay out cycles first** — rooms on each cycle placed as a ring with shared walls
3. **Lay out tree branches** — rooms hanging off cycle nodes placed via BFS
4. **Validate cycle closure** — verify the last connection in each cycle can close
   (exit positions are compatible at the loop-closing shared wall)
5. **Resolve overlaps** — nudge rooms if irregular shapes cause floor-on-floor collision

If the constraint solver cannot place all rooms without overlap while closing all
cycles, that is a **content authoring error** caught by validation at authoring time,
not a runtime failure.

### 6. SVG Tactical Renderer

The UI renders the dungeon as interactive SVG:

- **`<defs>`** — `<symbol>` elements for each cell type (wall, floor, feature types)
- **`<g>` per room** — positioned at global coordinates, contains cell instances via `<use>`
- **Token layer** — PC/NPC/creature entities as positioned SVG groups with faction coloring
- **Zone layer** — spell radii, hazard overlays as semi-transparent SVG shapes
  - `Circle { center, radius }`
  - `Cone { origin, direction, angle }`
  - `Line { start, end, width }`
  - `Rect { x, y, w, h }`
- **Fog of war** — undiscovered rooms hidden, discovered-but-not-current at reduced opacity
- **Zoom transition** — zoomed out shows dungeon overview (room shapes + corridors),
  zoomed in shows tactical grid (individual cells, tokens, features)

SVG is chosen over Canvas for:
- DOM event handling (click-to-move, hover tooltips)
- Resolution independence (crisp at any zoom)
- Accessibility (screen readers can inspect elements)
- Scale appropriateness (18-40 rooms, not thousands of sprites)

### 7. Protocol Extensions

Two new message types in `sidequest-protocol`:

```
TACTICAL_STATE — server → client
  room_id: String
  global_grid: { width, height, cells: Vec<CellType> }
  rooms: Vec<{ id, offset_x, offset_y, discovered, is_current }>
  entities: Vec<TacticalEntity>
  zones: Vec<EffectZone>

TACTICAL_ACTION — client → server
  Move { entity_id, to: GridPos }
  Target { cell: GridPos, ability: String }
  Inspect { cell: GridPos }
```

### 8. Narrator Integration

The narrator interacts with the tactical grid via tool calls:

- **`tactical_place`** — place or move NPC/creature entities on room entry or during narration
- **`tactical_hazard`** — create dynamic hazard zones (spell effects, environmental changes)
- **`tactical_remove`** — remove entities (death, flee) or zones (spell expiry)

The narrator's prompt context includes a compact grid summary:
```
TACTICAL: The Mouth (12×12). PC "Grimjaw" at (2,5). 
Hostile: "Goblin Scout" at (9,3), "Tunnel Spider" at (1,6). 
Cover: Worn tooth stumps at (4,4)(4,8). 
Hazard: Slippery moss circle r=2 at (6,6).
```

### 9. Content Authoring Pipeline

```
World Builder generates room + ASCII grid (from template library)
    ↓
sidequest-validate --tactical (8-point grid validation)
    ↓
Layout solver validates dungeon-wide placement + cycle closure
    ↓
Human reviews ASCII (fastest spatial review format)
    ↓
Optional: browser grid editor for refinement (tactical renderer in edit mode)
    ↓
Commit to rooms.yaml
    ↓
CI runs validation on every PR touching rooms.yaml
```

#### Template Library

`sidequest-content/templates/tactical/` contains ~20 reusable room shapes:

- `corridor_straight_Nx1.ascii` — various lengths
- `corridor_bent_NxN.ascii` — L-shaped passages
- `chamber_oval_NxN.ascii` — various sizes
- `chamber_rect_NxN.ascii` — rectangular rooms
- `chamber_irregular_NxN.ascii` — natural cave shapes
- `room_L_NxN.ascii` — L-shaped rooms
- `room_T_NxN.ascii` — T-intersections

The World Builder selects a template by room_type and size, then customizes:
adds features, adjusts exit positions, mirrors/rotates as needed.

#### Validation Rules (sidequest-validate --tactical)

1. Grid dimensions match `size × tactical_scale`
2. Every exit in `exits[]` has a matching wall gap
3. No wall gaps exist that aren't in `exits[]`
4. Perimeter is closed (no floor cells adjacent to void cells without a wall between)
5. All interior floor cells are mutually reachable (flood fill from any floor cell)
6. All legend glyphs in grid have a legend entry
7. No legend glyphs placed on wall or void cells
8. Exit gap widths are compatible between connected rooms

### 10. Phased Rollout

| Phase | Scope | Genre Packs |
|-------|-------|-------------|
| **Phase 1** | ASCII format + parser + validator + SVG renderer + basic tokens | caverns_and_claudes |
| **Phase 2** | StructuredEncounter grid integration + AoE zones + narrator tools | caverns_and_claudes + low_fantasy |
| **Phase 3** | Template library + World Builder integration + grid editor | All combat-heavy genres |
| **Phase 4** | Click-to-move + pathfinding + multiplayer tactical view | All genres (optional per room) |

`tactical_scale` being optional means the system gracefully degrades: rooms without
a `grid` field use the existing Automapper schematic view. Genres that don't need
tactical maps (purely narrative, no positional combat) never adopt the feature.

## Consequences

### Positive

- **Deterministic** — ASCII grid IS the map, no generation step
- **Zero asset cost** — no tilesets, no spritesheets, no daemon rendering
- **Human-readable** — ASCII is the fastest spatial review format
- **LLM-authorable** — Claude generates ASCII maps reliably with tight constraints
- **Git-diffable** — room layout changes visible in plain text diffs
- **Genre-agnostic** — same format works for dungeons, starships, saloons, back alleys
- **Mechanically truthful** — the map IS the room graph rendered directly, no LLM interpretation

### Negative

- **Content authoring burden** — every tactical room needs an ASCII grid (mitigated by templates + World Builder generation)
- **Layout complexity** — jaquayed constraint solver is non-trivial to implement
- **ASCII aesthetic limitations** — "nearly circular" is the best circles get (acceptable per stakeholder)
- **Shared-wall constraints** — room grids must be authored with neighbor compatibility in mind

### Risks

- **Layout solver failure modes** — complex jaquayed topologies may be unsolvable with certain room sizes. Mitigation: validation catches this at authoring time, never at runtime
- **Narrator spatial awareness** — Claude must accurately reference grid positions in narration. Mitigation: compact grid summary in prompt context, `tactical_place` tool for structured entity placement
- **Scale of grid authoring** — 200+ rooms across all genre packs. Mitigation: template library covers 90% of shapes, World Builder batch generation, phased rollout

## Prior Art

- **NetHack des-file format** — ASCII room definitions with `MAP`/`ENDMAP` blocks and `GEOMETRY` placement (30+ years of proven use)
- **Unexplored cyclic dungeon generator** — graph rewriting rules with cyclic backbone for jaquayed topology
- **Enter the Gungeon composite layout** — hierarchical decomposition (cycles first, trees second) for room placement with variable sizes
- **Foundry VTT tile system** — coordinate-based tile management with z-index layering and grid-scale abstraction
- **Cogmind ASCII art philosophy** — glyph weight and negative space principles for spatial communication
- **Dwarf Fortress** — multi-layer ASCII spatial representation at massive scale

## References

- ADR-019: Cartography (room graph navigation)
- ADR-033: Confrontation Resource Pools (StructuredEncounter)
- ADR-055: Room Graph Navigation (RoomDef, RoomExit)
- Story 19-8: Automapper UI component (current schematic renderer)
- Epic 28: Unified Encounter Engine (StructuredEncounter integration surface)
