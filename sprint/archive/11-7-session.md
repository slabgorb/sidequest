---
story_id: "11-7"
epic: "11"
epic_title: "Lore & Language — RAG Retrieval, Conlang Name Banks"
workflow: "tdd"
---
# Story 11-7: Morpheme glossary schema — conlang morphemes with meaning and pronunciation rules in genre pack

## Story Details
- **ID:** 11-7
- **Title:** Morpheme glossary schema — conlang morphemes with meaning and pronunciation rules in genre pack
- **Points:** 2
- **Priority:** p1
- **Epic:** 11 — Lore & Language
- **Workflow:** tdd
- **Stack Parent:** 11-1 (LoreFragment model foundation)

## Story Description

The morpheme glossary schema defines the data model for constructed language (conlang) morphemes—
the building blocks of linguistically consistent names and terms in genre packs. A morpheme is an
atomic unit of meaning: a prefix, root, suffix, or particle that carries semantic and phonetic
information. Genre packs define their own morpheme glossaries, and name generation (11-8) uses
these glossaries to compose names with decomposition and pronunciation hints.

**Core responsibility:** Define the Morpheme and MorphemeGlossary structs, support serde for YAML
loading, and provide lookup/filtering methods for name generation downstream.

## Implementation Context

### Core Model Structure

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Morpheme {
    pub morpheme: String,           // The actual word fragment (e.g., "val", "eth", "mir")
    pub meaning: String,            // Semantic meaning (e.g., "strong", "fire", "bright")
    pub pronunciation_hint: String, // IPA or informal hint (e.g., "/vɑl/", "VAHL")
    pub category: MorphemeCategory, // prefix, suffix, root, particle
    pub language_id: String,        // Which language this belongs to (e.g., "elvish", "draconic")
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum MorphemeCategory {
    Prefix,
    Suffix,
    Root,
    Particle,
    Custom(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MorphemeGlossary {
    pub language_id: String,
    pub language_name: String,
    pub morphemes: Vec<Morpheme>,
}
```

### Key Methods for MorphemeGlossary

```rust
impl MorphemeGlossary {
    /// Look up a morpheme by its string form
    pub fn lookup(&self, morpheme: &str) -> Option<&Morpheme> { }

    /// Get all morphemes of a specific category
    pub fn by_category(&self, category: &MorphemeCategory) -> Vec<&Morpheme> { }

    /// Get all roots for random name generation
    pub fn roots(&self) -> Vec<&Morpheme> { }

    /// Get all prefixes
    pub fn prefixes(&self) -> Vec<&Morpheme> { }

    /// Get all suffixes
    pub fn suffixes(&self) -> Vec<&Morpheme> { }
}
```

### YAML Genre Pack Integration

Glossaries are loaded from genre pack YAML:

```yaml
# In a genre pack's rules.yaml or languages.yaml:
conlangs:
  elvish:
    language_name: "Elvish"
    morphemes:
      - morpheme: "val"
        meaning: "strong"
        pronunciation_hint: "/vɑl/"
        category: root
      - morpheme: "eth"
        meaning: "fire"
        pronunciation_hint: "/ɛθ/"
        category: root
      - morpheme: "mir"
        meaning: "bright"
        pronunciation_hint: "/mɪr/"
        category: root
      - morpheme: "a"
        meaning: "the"
        pronunciation_hint: "/ə/"
        category: particle
      - morpheme: "el"
        meaning: "one"
        pronunciation_hint: "/ɛl/"
        category: prefix
```

### Module Organization

- `crates/sidequest-game/src/conlang.rs` — Morpheme, MorphemeCategory, MorphemeGlossary definitions
- `crates/sidequest-game/src/lib.rs` — Module exposure and public exports

### Architecture Notes

- This is a pure data model with no state mutation or external I/O
- Foundation for downstream story 11-8 (name bank generation)
- Custom category variant allows genre packs to define domain-specific morpheme types
- Glossaries are loaded at game startup from genre pack YAML
- No in-game morpheme creation; all morphemes come from genre packs

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Morpheme struct | All fields compile; derives Serialize/Deserialize |
| MorphemeCategory enum | Prefix, Suffix, Root, Particle, Custom(String) variants |
| MorphemeGlossary struct | Holds language_id, language_name, and Vec<Morpheme> |
| lookup() method | Returns Option<&Morpheme> for a given morpheme string |
| by_category() method | Returns Vec<&Morpheme> filtered by category |
| Helper methods | roots(), prefixes(), suffixes() convenience methods work |
| YAML round-trip | Serialized→deserialized glossaries preserve all fields |
| Custom categories | Custom(String) variant usable in genre packs |
| Module exposure | Morpheme, MorphemeCategory, MorphemeGlossary exported from lib.rs |

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None recorded yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
