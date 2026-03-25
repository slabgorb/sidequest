---
parent: context-epic-1.md
---

# Story 1-3: Genre Loader — Full Model Hierarchy, Real YAML Loading, deny_unknown_fields

## Business Context

Port `genre/models.py`, `genre/loader.py`, and `genre/resolve.py` completely. The Python
genre system has 50+ Pydantic models that define everything from world lore to combat
rules to trope definitions. These models are battle-tested — 7 genre packs with 174 YAML
files load through them. The Rust version must load the same YAML files successfully.

**Python sources:**
- `sq-2/sidequest/genre/models.py` — all Pydantic models (GenrePack, TropeDefinition, etc.)
- `sq-2/sidequest/genre/loader.py` — YAML loading with file map
- `sq-2/sidequest/genre/resolve.py` — trope inheritance resolution

**Test data:** `sq-2/genre_packs/mutant_wasteland/flickering_reach/` (fully spoilable)

## Technical Guardrails

- **Port all models:** GenrePack, PackMeta, Lore, RulesConfig, TropeDefinition,
  NpcArchetype, CharCreationScene, VisualStyle, GenreTheme, AudioConfig, InventoryConfig,
  ProgressionConfig, CartographyConfig, AxisConfig, BeatVocabulary, WorldHistory, etc.
- **Port lesson #16 (deny_unknown_fields):** Python has `extra="allow"` on all 52 models,
  silently accepting typos. Rust uses `#[serde(deny_unknown_fields)]`
- **Port lesson #15 (no untyped data):** Python has 6 locations using `dict[str, Any]`
  (HistoryChapter, level_bonuses, voice_presets, etc.). Define explicit Rust structs
- **Port lesson #14 (trope inheritance):** Resolve multi-level extends chains with cycle
  detection. Python only resolves one level
- **Port lesson #13 (consistent loader):** Python has 4 different loading patterns plus
  special cases. Rust uses a single unified loader
- **Port lesson #17 (two-phase loading):** Separate deserialization from cross-reference
  validation. Return typed structs from phase 1; validate references in phase 2
- **Real YAML:** Tests must load at least one complete real genre pack, not synthetic fixtures

### Scenario packs

Port `scenario/engine.py` models (ScenarioPack, AssignmentMatrix, ClueGraph, etc.)
using the same loader pattern as genre packs. Python has a separate ad-hoc loader for
scenarios — unify them in Rust.

## Scope Boundaries

**In scope:**
- All genre pack model structs with serde derives
- Unified loader function: `fn load_genre_pack(path: &Path) -> Result<GenrePack>`
- Trope inheritance resolution with multi-level extends and cycle detection
- Scenario pack models and loading
- Two-phase validation (deserialize, then validate cross-references)
- Tests loading real genre packs from `genre_packs/`
- All `dict[str, Any]` replaced with explicit types

**Out of scope:**
- Lore RAG system (embedding/retrieval — future epic)
- Corpus text file loading (used by RAG, not by core loader)
- Runtime genre pack switching

## AC Context

| AC | Detail |
|----|--------|
| Full model hierarchy | All 50+ Python models have Rust equivalents with serde derives |
| Real YAML loads | mutant_wasteland/flickering_reach loads without error |
| deny_unknown_fields | YAML typos produce clear errors |
| No untyped catchalls | No serde_yaml::Value fields — all data has explicit types |
| Trope inheritance | Multi-level extends resolved with cycle detection |
| Scenario packs | ScenarioPack loads through unified loader |
| Two-phase validation | Loader returns typed structs; validate() checks cross-refs |
