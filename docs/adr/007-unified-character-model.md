# ADR-007: Unified Character Model

> Ported from sq-2 (Pydantic) → Rust (serde struct) → back to Python per
> ADR-082 (pydantic v2 model). The decision is language-agnostic; only the
> type-declaration syntax below is a historical Rust artifact. Current home:
> `sidequest-server/sidequest/game/character.py`.

## Status
Accepted

## Context
Characters need both narrative identity (name, backstory, personality, relationships) and mechanical stats (class, level, HP, AC, inventory). Splitting these creates synchronization problems.

## Decision
A single `Character` struct combines both concerns, with narrative fields first.

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Character {
    // Narrative identity (primary)
    pub name: String,
    pub description: String,
    pub backstory: String,
    pub personality: String,
    pub relationships: Vec<Relationship>,
    pub narrative_state: String,
    pub hooks: Vec<NarrativeHook>,

    // Mechanical stats
    pub char_class: String,
    pub race: String,
    pub level: u32,
    pub hp: i32,
    pub max_hp: i32,
    pub ac: i32,
    pub stats: HashMap<String, i32>,
    pub inventory: Vec<Item>,
    pub statuses: Vec<String>,
    pub progression: Progression,
}
```

### Why Unified
1. Agents need both simultaneously — narrator reads personality AND HP
2. World state agent patches both in one turn
3. Character builder outputs one object
4. Save/load serializes one struct

### Philosophy
Narrative-first in field ordering and design. The mechanical stats serve the narrative, not the other way around (SOUL principle: Tabletop First).

## Consequences
- Single source of truth for each character
- No synchronization between "narrative character" and "stat block"
- Struct is larger but coherent
