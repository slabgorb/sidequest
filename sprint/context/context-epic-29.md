# Epic 29: Tactical ASCII Grid Maps

## Why This Epic Exists

SideQuest's dungeon crawl experience lacks spatial tactical information. The Automapper
(story 19-8) renders room-to-room topology as labeled rectangles connected by lines --
useful for navigation but useless for tactical play. Players cannot see room geometry,
entity positions, hazard zones, cover positions, or spell radii. This forces multi-turn
interrogation of the narrator just to understand spatial layout, and the narrator (Claude)
has no structured spatial data to reference -- answers are approximate and inconsistent.

ASCII grids stored in `rooms.yaml` become the deterministic source of truth for room
geometry. The UI renders them as interactive SVG with tokens, zones, and fog of war.
The narrator interacts with the grid via tool calls (`tactical_place`, `tactical_hazard`,
`tactical_remove`), not prose. Server-side A* pathfinding validates movement.

This is a zero-asset-cost solution: no tilesets, no spritesheets, no daemon rendering.
ASCII is human-readable, LLM-authorable, and git-diffable. The same format works across
all genre packs (dungeons, starships, saloons, back alleys).

## Architecture

### Data Flow
```
rooms.yaml (grid: field) → ASCII parser → TacticalGrid (Rust struct)
                                              ↓
                             Layout engine (shared-wall placement)
                                              ↓
                             Global dungeon grid (all rooms positioned)
                                              ↓
                             TACTICAL_STATE message → WebSocket → UI
                                              ↓
                             SVG renderer (cells, tokens, zones, fog)
```

### New Types (sidequest-game)
- `TacticalGrid` -- parsed grid with cells, dimensions, legend, extracted exits
- `TacticalCell` -- enum: Floor, Wall, Void, Door(open/closed), Water, DifficultTerrain, Feature(char)
- `GridPos` -- (x, y) coordinate
- `TacticalEntity` -- entity on grid (id, name, position, size, faction)
- `EffectZone` -- area overlay (Circle/Cone/Line/Rect variants)
- `DungeonLayout` -- all rooms positioned in global coordinates

### New Protocol Messages (sidequest-protocol)
- `TACTICAL_STATE` (server -> client): room grid, entity positions, zone overlays, fog state
- `TACTICAL_ACTION` (client -> server): Move, Target, Inspect actions

### New Narrator Tools (sidequest-agents)
- `tactical_place` -- place/move NPC/creature entities
- `tactical_hazard` -- create dynamic hazard zones
- `tactical_remove` -- remove entities or zones

### Graceful Degradation
`tactical_scale` and `grid` are optional on RoomDef. Rooms without a grid field use
the existing Automapper schematic view. Genres that don't need tactical maps never
adopt the feature. The Automapper component checks for grid presence and delegates
to the tactical renderer or the existing schematic renderer accordingly.

## Guardrails

1. **Corridors are rooms** -- no auto-generated connectors. Every passageway is a RoomDef with its own grid.
2. **Non-rectangular rooms supported** -- void cells (`_`) carve any shape. Never assume rectangles.
3. **Shared walls** -- adjacent rooms share wall segments at exit gaps. One wall, not two.
4. **tactical_scale is optional** -- rooms without a grid field use the existing Automapper.
5. **Exit positions extracted from grid** -- parser scans wall perimeter for gaps, matches to exits list.
6. **Validation at authoring time** -- grid errors caught by sidequest-validate, not at runtime.
7. **OTEL on every subsystem decision** -- per project rules.
8. **No silent fallbacks** -- if a grid is malformed, fail loudly.

## Story Dependency Chain

```
Phase 1: Foundation
29-1  ASCII grid parser ──────────┬──→ 29-2  Tactical grid validation
                                  ├──→ 29-3  Author Mawdeep grids (needs parser for format)
                                  ├──→ 29-4  Single-room SVG renderer
                                  └──→ 29-5  TACTICAL_STATE protocol message

Phase 2: Layout Engine
29-1 + 29-2 ──→ 29-6  Shared-wall layout engine (tree topology)
29-6 ──────────→ 29-7  Jaquayed layout (cycle detection + ring placement)
29-5 + 29-6 ──→ 29-8  Multi-room SVG dungeon map
29-1 + 29-2 ──→ 29-9  Author Grimvault grids

Phase 3: Tokens + Interaction
29-4 + 29-5 ──→ 29-10 TacticalEntity + token rendering
29-10 ─────────→ 29-11 Narrator tactical_place tool
29-10 ─────────→ 29-12 Click-to-move + A* pathfinding
29-10 ─────────→ 29-13 EffectZone overlays + tactical_hazard tool

Phase 4: Integration + Authoring
29-10 + 29-11 → 29-14 StructuredEncounter grid binding
29-1 ──────────→ 29-15 Template library (20 reusable shapes)
29-15 ─────────→ 29-16 World Builder tactical grid generation
29-4 ──────────→ 29-17 Browser grid editor
29-all ────────→ 29-18 OTEL for tactical system
```

## Key Files

| File | Role |
|------|------|
| `docs/adr/071-tactical-ascii-grid-maps.md` | Complete technical spec (ADR) |
| `sidequest-api/crates/sidequest-genre/src/models/world.rs` | RoomDef, RoomExit (line 137) -- gains `grid`, `tactical_scale`, `legend` fields |
| `sidequest-api/crates/sidequest-game/src/encounter.rs` | StructuredEncounter, EncounterActor -- gains GridPos |
| `sidequest-api/crates/sidequest-game/src/room_movement.rs` | Room transition validation |
| `sidequest-api/crates/sidequest-protocol/src/message.rs` | GameMessage enum (line 98) -- gains TACTICAL_STATE, TACTICAL_ACTION |
| `sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` | Dispatch pipeline -- sends tactical state on room entry |
| `sidequest-api/crates/sidequest-agents/src/orchestrator.rs` | Narrator tool call framework |
| `sidequest-api/crates/sidequest-validate/src/main.rs` | Genre pack validation -- gains --tactical flag |
| `sidequest-ui/src/components/Automapper.tsx` | Current room graph SVG renderer (300 LOC) -- delegates to tactical renderer |
| `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml` | 18 rooms -- gains grid fields |
| `sidequest-content/genre_packs/caverns_and_claudes/worlds/grimvault/rooms.yaml` | 18 rooms -- gains grid fields |
