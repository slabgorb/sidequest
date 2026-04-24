---
id: 19
title: "Cartography Discovery"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-019: Cartography Discovery

> Ported from sq-2. Language-agnostic world topology.

## Decision
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
