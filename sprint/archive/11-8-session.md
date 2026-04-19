---
story_id: "11-8"
epic: "11"
epic_title: "Lore & Language — RAG Retrieval, Conlang Name Banks"
workflow: "tdd"
---
# Story 11-8: Name bank generation — produce glosses/names from morpheme combinations per genre pack

## Story Details
- **ID:** 11-8
- **Title:** Name bank generation — produce glosses/names from morpheme combinations per genre pack
- **Points:** 3
- **Priority:** p1
- **Epic:** 11 — Lore & Language
- **Workflow:** tdd
- **Stack Parent:** 11-7 (Morpheme glossary schema)

## Story Description

The name bank generation system extends the morpheme glossary (11-7) to produce pre-generated collections of linguistically consistent names. A NameBank is populated by combining morphemes according to configurable patterns and weights, generating names with semantic glosses (decomposed meanings) and optional pronunciation guides.

Use cases:
- NPC name generation for a genre pack
- Dialogue reference: narrator can speak about "the fire-walker" (zar'kethi) with semantic grounding
- World building: consistent naming conventions across regions/factions

**Core responsibility:** Define NameBank and name generation logic that combines morphemes into complete names with glosses, supports multiple naming patterns, uses deterministic generation with a seed for reproducibility, and allows configurable name counts and pattern weights.

## Implementation Context

### Core Model Structure

```rust
/// A generated name with its semantic decomposition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneratedName {
    /// The complete name, e.g., "zar'kethi"
    pub name: String,
    /// Decomposition gloss, e.g., "fire-walker" or "great dragon"
    pub gloss: String,
    /// Optional pronunciation hint, e.g., "zahr-KEH-thee"
    pub pronunciation: Option<String>,
}

/// A pattern for name generation.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NamePattern {
    /// Just a root, e.g., "zar"
    Root,
    /// Prefix + root, e.g., "vor-zar"
    PrefixRoot,
    /// Root + suffix, e.g., "zar-thi"
    RootSuffix,
    /// Prefix + root + suffix, e.g., "vor-zar-thi"
    PrefixRootSuffix,
}

/// Configuration for name generation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NameGenConfig {
    /// How many names to generate
    pub count: usize,
    /// Relative weights for patterns: (Root, PrefixRoot, RootSuffix, PrefixRootSuffix)
    pub pattern_weights: (u32, u32, u32, u32),
    /// Separator between morpheme parts, e.g., "-" or "'"
    pub separator: String,
    /// Random seed for reproducibility
    pub seed: u64,
}

/// A collection of pre-generated names for a language.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NameBank {
    /// Unique identifier for the language
    pub language_id: String,
    /// Human-readable language name
    pub language_name: String,
    /// All generated names
    pub names: Vec<GeneratedName>,
    /// Configuration used for generation
    pub config: NameGenConfig,
}
```

### Key Methods

```rust
impl NameBank {
    /// Create a new name bank by generating from a morpheme glossary.
    pub fn generate(
        glossary: &MorphemeGlossary,
        config: NameGenConfig,
    ) -> Self { }

    /// Look up a generated name by its string form.
    pub fn lookup(&self, name: &str) -> Option<&GeneratedName> { }

    /// Return all generated names.
    pub fn names(&self) -> &[GeneratedName] { }

    /// Return the number of names in the bank.
    pub fn len(&self) -> usize { }

    /// Return true if the bank contains no names.
    pub fn is_empty(&self) -> bool { }
}
```

### YAML Genre Pack Integration

Name banks are generated at game startup:

```yaml
# In a genre pack's conlang section:
conlangs:
  draconic:
    language_name: "Draconic"
    morphemes: [...]
    name_generation:
      count: 50
      pattern_weights:
        root: 10
        prefix_root: 20
        root_suffix: 20
        prefix_root_suffix: 30
      separator: "'"
      seed: 12345
```

### Module Organization

- `crates/sidequest-game/src/conlang.rs` — NameBank, NamePattern, NameGenConfig, GeneratedName definitions and generation logic
- `crates/sidequest-game/src/lib.rs` — Module exposure

### Architecture Notes

- Generation is deterministic: same seed + glossary → same NameBank
- Glosses are composites of morpheme meanings joined by "-"
- Pronunciation is optional; if all component morphemes have hints, concatenate with separator
- Pattern weighting uses cumulative probability; sampling uses a seeded RNG (e.g., `rand::thread_rng` with seed)
- No mutation of MorphemeGlossary; NameBank is a separate, immutable collection
- NameBank is typically created once at game startup and kept in memory

## Acceptance Criteria

| AC | Detail |
|----|--------|
| GeneratedName struct | name, gloss, pronunciation fields; derives Serialize/Deserialize |
| NamePattern enum | Root, PrefixRoot, RootSuffix, PrefixRootSuffix variants |
| NameGenConfig struct | count, pattern_weights, separator, seed fields |
| NameBank struct | language_id, language_name, names, config; derives Serialize/Deserialize |
| generate() method | Takes MorphemeGlossary + NameGenConfig; returns populated NameBank |
| Deterministic generation | Same seed + glossary → identical NameBank (bit-for-bit) |
| Pattern weighting | Weights control relative frequency of name patterns |
| Gloss composition | Morpheme meanings joined by "-" (e.g., "fire-walker") |
| Pronunciation chaining | If all components have hints, concatenate with separator |
| lookup() method | Returns Option<&GeneratedName> by name string |
| names() / len() / is_empty() | Collection access methods work as expected |
| YAML round-trip | NameBank serializes/deserializes correctly |
| Module exposure | NameBank, NamePattern, NameGenConfig, GeneratedName exported from lib.rs |
| Edge cases | Handles glossaries with no prefixes/suffixes gracefully |

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None recorded yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-27T22:07:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T22:07:00Z | - | - |
