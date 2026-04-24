---
id: 20
title: "NPC Disposition System"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: drift
implementation-pointer: 87
---

# ADR-020: NPC Disposition System

> Ported from sq-2. Language-agnostic game mechanic.

## Decision
NPCs have a numeric `disposition` (integer) that maps to a qualitative `attitude` string. Agents see only the attitude; the world_state agent patches disposition with numeric deltas.

### Mapping
| Disposition | Attitude |
|------------|----------|
| > 10 | friendly |
| -10 to 10 | neutral |
| < -10 | hostile |

### Why Split
- **World state agent** thinks numerically: "player helped NPC, +5 disposition"
- **Narrator/NPC agents** think qualitatively: "the innkeeper is friendly"
- Threshold crossings create meaningful narrative moments without exposing math

### Rust Pattern
```rust
impl NPC {
    pub fn attitude(&self) -> &str {
        match self.disposition {
            d if d > 10 => "friendly",
            d if d < -10 => "hostile",
            _ => "neutral",
        }
    }
}
```

### Future
Thresholds should move to genre pack config. More granular attitudes (wary, grateful, terrified) are a known gap.

## Consequences
- NPCs evolve relationships naturally over time
- Trope beats can drive disposition changes between sessions
- Automatic re-derivation on every access ensures consistency
