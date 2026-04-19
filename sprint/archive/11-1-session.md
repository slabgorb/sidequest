---
story_id: "11-1"
epic: "11"
epic_title: "Lore & Language — RAG Retrieval, Conlang Name Banks"
workflow: "tdd"
---
# Story 11-1: LoreFragment model — indexed narrative fact with category, token estimate, metadata

## Story Details
- **ID:** 11-1
- **Title:** LoreFragment model — indexed narrative fact with category, token estimate, metadata
- **Points:** 3
- **Priority:** p0
- **Epic:** 11 — Lore & Language
- **Workflow:** tdd
- **Stack Parent:** none (foundation story)

## Story Description

The narrator suffers from "context amnesia" — it only sees the current game snapshot, not the
history of what happened. LoreFragment is the atomic unit of memory: a single indexed fact
("the merchant guild declared war on the thieves' quarter") with category, token cost, and
source tracking. This model is the foundation for the entire lore system.

**Core responsibility:** Define the LoreFragment struct with typed enums for category and source,
implement token estimation, and ensure serialize/deserialize round-trip compatibility.

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-27T00:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T00:00:00Z | - | - |

## Implementation Context

### Core Model Structure

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoreFragment {
    pub id: String,
    pub category: LoreCategory,
    pub content: String,
    pub token_estimate: usize,
    pub source: LoreSource,
    pub turn_created: Option<u64>,
    pub metadata: HashMap<String, String>,
}
```

### Category Enum

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum LoreCategory {
    History,
    Geography,
    Faction,
    Character,
    Item,
    Event,
    Language,
    Custom(String),
}
```

The `Custom(String)` variant lets genre packs define domain-specific categories without
changing the core enum.

### Source Tracking

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LoreSource {
    GenrePack,
    CharacterCreation,
    GameEvent,
}
```

### Implementation Notes

- Token estimation uses a rough heuristic: ~4 chars per token for English
- `new()` constructor auto-computes token_estimate from content
- Metadata is a HashMap<String, String> for arbitrary key-value pairs
- All derives include Serialize/Deserialize for round-trip compatibility

### Target Files

- `crates/sidequest-game/src/lore/models.rs` — LoreFragment, LoreCategory, LoreSource definitions
- `crates/sidequest-game/src/lore/mod.rs` — Module exposure

### Architecture Notes

- This is a pure data model with no state mutation or external dependencies
- Foundation for downstream stories: 11-2 (LoreStore indexing), 11-3 (seeding), 11-4+ (retrieval and injection)
- No embedding vectors or semantic features in scope — that's 11-6
- Token estimation is a simple heuristic; exact tokenizer integration is out of scope

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Struct compiles | `LoreFragment` with all fields derives Serialize/Deserialize |
| Category enum | All 7 fixed variants + Custom(String) usable |
| Source enum | GenrePack, CharacterCreation, GameEvent variants |
| Token estimate | 100-char string estimates ~25 tokens |
| Metadata | Arbitrary key-value pairs stored in HashMap |
| Round-trip | Serialize → deserialize preserves all fields including Custom category |
| Constructor | `new()` auto-computes token estimate |

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None recorded yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
