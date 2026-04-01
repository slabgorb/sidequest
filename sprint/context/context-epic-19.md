# Epic 19: Dungeon Crawl Engine — Room Graph Navigation & Resource Pressure

## Overview

Engine support for the Caverns & Claudes genre pack. The genre pack content (28 YAML
files, 3,245 lines) is complete but the engine can't run it — it lacks room-level
navigation, consumable depletion, and weight-based encumbrance.

**Core architectural addition:** Room graph navigation mode (ADR-055). Extends
CartographyConfig with a `NavigationMode::RoomGraph` discriminant. When active,
locations become validated room IDs, movement checks exits, and trope ticks fire
per room transition.

**Everything else reuses existing systems:**
- Keeper awareness = trope engine escalation ("Keeper Stirs" trope)
- Hireling morale = NPC disposition + OCEAN neuroticism
- Boss encounters = ConfrontationDef content flag, narrator framing
- Resource pressure = ResourceDeclaration.decay_per_turn (exists, needs wiring)

**ADR:** 055-room-graph-navigation.md

## Background

### Why Room Graph Navigation

The existing location system is a freeform `String` set by the narrator via
`WorldStatePatch.location`. CartographyConfig defines regions and routes as
**metadata for context** — the narrator reads topology but isn't constrained by it.

This breaks dungeon crawling because:
1. The narrator fabricates rooms, exits, and connections that don't exist
2. There's no "room transition" event to trigger resource depletion or trope escalation
3. The automapper UI has no structured data to render

ADR-055 adds `NavigationMode::RoomGraph` where locations are validated room IDs with
checked exits. Region mode (default) is unchanged for all other genre packs.

### Existing Systems Being Reused

| System | Exists In | Reused For |
|--------|-----------|------------|
| Trope engine (rate_per_turn, accelerators) | sidequest-game/src/trope.rs | Keeper awareness, extraction panic |
| NPC disposition + OCEAN | sidequest-game/src/disposition.rs, npc.rs | Hireling morale breaks |
| ConfrontationDef + StructuredEncounter | sidequest-genre/src/models.rs, sidequest-game/src/encounter.rs | Boss encounters |
| ResourceDeclaration (decay_per_turn) | sidequest-genre/src/models.rs | Resource depletion rate |
| Inventory (Item.weight) | sidequest-game/src/inventory.rs | Encumbrance basis |
| MAP_UPDATE / ExploredLocation | sidequest-protocol/src/message.rs | Automapper data |

### The Caverns & Claudes Genre Pack

- **Genre:** `caverns_and_claudes` — OSR dungeon crawler
- **First world:** `mawdeep` — The Glutton Below, a hungry dungeon
- **19 rooms** across 2 levels, Jaquayed layout with loops and one-way drops
- **Core loop:** Town → Delve → Fight the Maw (boss) → Loot → Extract → Repeat
- **Key mechanics:** Treasure-as-XP, resource ticks per room, Keeper awareness via tropes

Content lives in `sidequest-content/genre_packs/caverns_and_claudes/` on branch
`feat/caverns-and-claudes-genre-pack`.

## Dependency Chain

```
19-1 (RoomDef structs) → 19-2 (Validated movement) → 19-3 (Trope tick on transition)
                                                   → 19-4 (MAP_UPDATE for rooms)
19-3 → 19-5 (Item depletion) → 19-7 (Encumbrance)
19-3 → 19-6 (Wire decay_per_turn)
19-4 → 19-8 (Automapper UI)
19-2 → 19-9 (Treasure-as-XP)
```

**Phase 1 (19-1 through 19-4):** Room graph navigation + protocol. Blocks everything.
**Phase 2 (19-5, 19-6):** Resource depletion. Core gameplay loop.
**Phase 3 (19-7, 19-9):** Encumbrance and treasure-as-XP. Enhancement.
**Phase 5 (19-8):** Automapper UI. Independent parallel work.

## Key Files

### sidequest-genre (data model)
- `crates/sidequest-genre/src/models.rs` — CartographyConfig (~line 680), RoomDef, NavigationMode, ResourceDeclaration (~line 395), ConfrontationDef (~line 609)

### sidequest-game (engine logic)
- `crates/sidequest-game/src/state.rs` — GameSnapshot.location (~line 54), WorldStatePatch, apply_resource_deltas (~line 600)
- `crates/sidequest-game/src/trope.rs` — TropeEngine::tick(), rate_per_turn (~line 150)
- `crates/sidequest-game/src/inventory.rs` — Item struct, Inventory, weight field
- `crates/sidequest-game/src/disposition.rs` — Disposition, Attitude thresholds
- `crates/sidequest-game/src/npc.rs` — NPC, effective_disposition()
- `crates/sidequest-game/src/affinity.rs` — AffinityState, check_affinity_thresholds()

### sidequest-protocol (messages)
- `crates/sidequest-protocol/src/message.rs` — GameMessage::MapUpdate, ExploredLocation, ChapterMarker

### sidequest-ui (frontend)
- New: `src/components/Automapper.tsx` — room graph renderer
- Existing: MAP_UPDATE handler in WebSocket provider

### sidequest-content (genre pack)
- `genre_packs/caverns_and_claudes/` — 19 genre-level YAML files
- `genre_packs/caverns_and_claudes/worlds/mawdeep/` — 9 world-level YAML files including rooms.yaml

## Story Points

| Story | Title | Points | Priority | Depends On |
|-------|-------|--------|----------|------------|
| 19-1 | RoomDef + RoomExit structs | 5 | p0 | — |
| 19-2 | Validated room movement | 5 | p0 | 19-1 |
| 19-3 | Trope tick on room transition | 3 | p0 | 19-2 |
| 19-4 | MAP_UPDATE for room graph | 3 | p1 | 19-2 |
| 19-5 | Consumable item depletion | 5 | p0 | 19-3 |
| 19-6 | Wire decay_per_turn | 2 | p1 | 19-3 |
| 19-7 | Weight-based encumbrance | 3 | p1 | 19-5 |
| 19-8 | Automapper UI component | 8 | p1 | 19-4 |
| 19-9 | Treasure-as-XP | 3 | p2 | 19-2 |
| **Total** | | **37** | | |

## Scope Boundaries

**IN scope:**
- Room graph navigation mode in CartographyConfig
- Validated movement with exit checking
- Trope tick per room transition
- Consumable item depletion (uses_remaining)
- Weight-based encumbrance mode
- Automapper React component
- Treasure-as-XP affinity progression

**OUT of scope:**
- Procedural dungeon generation (hand-authored rooms.yaml only)
- Custom Keeper awareness subsystem (trope engine handles this)
- Custom hireling morale system (disposition handles this)
- Custom boss encounter system (ConfrontationDef handles this)
- Sound effects / ambient audio system (content-level)
- Conlang / voice systems for this genre
