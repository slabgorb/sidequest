---
id: 19
title: "Cartography Discovery"
status: superseded
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: 82
related: [55, 82]
tags: [game-systems]
implementation-status: retired
implementation-pointer: null
---

# ADR-019: Cartography Discovery

> Ported from sq-2. Language-agnostic world topology.

## Status

**Superseded 2026-04-28.** The live cartography subsystem — render tier
`cartography`, `MAP_UPDATE` wire message, `MapUpdatePayload`,
`CartographyMetadata` wire DTO, `MapOverlay` / `MapWidget` UI, and the
daemon Z-Image cartography tier — did not survive the Rust → Python port
formalized in [ADR-082](082-port-sidequest-api-rust-to-python.md). After
the port, only protocol shells (the `MAP_UPDATE` enum and a stub
`MapUpdatePayload`) remained; the construction sites, the daemon tier
config, and the live UI consumers were re-implemented as port-debt slices
but never wired into a turn-by-turn flow that delivered useful map state
to players.

This ADR is retired in full. The implementation has been removed across
the four repos (server, daemon, UI, docs) on 2026-04-28. Region-and-route
*world authoring* — `world.cartography.yaml`, `CartographyConfig`, the
`world.cartography.starting_region` chargen seed, and the room graph
config — is unaffected; that surface is owned by
[ADR-055](055-room-graph-navigation.md), which uses the same
`CartographyConfig` pydantic model purely as a static world-topology
config and does not depend on any of the runtime delivery machinery
removed here.

If a future story revives a live world map, it should be designed
fresh against the current architecture, not by porting the original
sketch below.

## Original decision (historical)

World is a directed graph of regions connected by routes, defined in `topology.yaml`.

### Graph Structure
```yaml
regions:
  - id: dark_forest
    name: "The Dark Forest"
    description: "Ancient trees block the sun"
    origin: ranger  # characters with ranger origin know this region
    adjacent: [village, mountains]

routes:
  - from: village
    to: dark_forest
    name: "Forest Trail"
    distance: short
    danger: moderate
```

### Discovery State
Characters discover regions through exploration. Origin-seeded knowledge means a soldier knows the heartland, a merchant knows the coast, etc.

```rust
pub struct CartographyState {
    pub discovered_regions: HashSet<String>,
    pub current_region: String,
}
```

### Narrator Integration
`format_topology_context()` produces a text summary for the narrator prompt: current region, adjacent known regions, available routes, and undiscovered hints.

### Validation
At load time, validate that all route references point to existing regions and origin IDs match character creation scenes.

## Consequences
- World feels expansive but discoverable
- Character backstory affects geographic knowledge
- Narrator knows the world topology and can describe paths naturally
