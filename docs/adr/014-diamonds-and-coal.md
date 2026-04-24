---
id: 14
title: "Diamonds and Coal"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: not-applicable
implementation-pointer: null
---

# ADR-014: Diamonds and Coal

> Ported from sq-2. Language-agnostic game design principle.

## Context
Not everything in a game deserves equal detail. A legendary sword's description should be richer than a ration pack's. This principle must scale across all output systems.

## Decision
`narrative_weight` (0.0-1.0) is a first-class mechanic that controls detail depth across inventory, rendering, audio, and narration.

### Inventory: Dual Representation
- **Coal items:** Bare strings, zero token cost (`"rope"`, `"rations"`)
- **Diamond items:** Full `Item` structs with lore, stats, history

### Promotion
Items promote from coal to diamond when:
- Player shows genuine interest (examines, asks about it)
- Item reaches `narrative_weight >= 0.5` (gets a proper name)
- Item reaches `narrative_weight >= 0.7` (gains mechanical power)

### Cross-System Scaling

| System | Low Weight | High Weight |
|--------|-----------|-------------|
| Narration | Brief mention | Detailed description |
| Rendering | Skip or sketch | Full scene illustration |
| Audio | Ambient only | Mood-matched music + SFX |
| Voice | Narrator voice | Character-specific voice |

```rust
pub enum InventoryEntry {
    Coal(String),                    // "50 feet of rope"
    Diamond(Item),                   // Full item with stats and lore
}
```

## Consequences
- Mundane items are nearly free (string storage, zero render cost)
- Important items get rich treatment automatically
- Players can promote items by engaging with them
