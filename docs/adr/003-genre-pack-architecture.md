# ADR-003: Genre Pack Architecture

> Ported from sq-2. Rust adaptation: Pydantic models become serde structs.

## Status
Accepted

## Context
Genre packs are swappable YAML directories that configure all game personality: lore, rules, prompt extensions, UI theming, audio, visual styles, voice presets, inventory, progression, topology, and tropes.

## Decision
Each genre pack is a directory of YAML files loaded by a `GenrePackLoader` and deserialized into typed Rust structs via `serde_yaml`.

### Directory Structure
```
genre_packs/{genre_name}/
├── pack.yaml              # Metadata: name, description, version
├── lore.yaml              # World lore fragments
├── rules.yaml             # Game mechanics and constraints
├── prompts.yaml           # Agent prompt extensions per genre
├── char_creation.yaml     # Character creation scenes and choices
├── archetypes.yaml        # Character class/archetype definitions
├── theme.yaml             # UI CSS theming
├── audio.yaml             # Music moods and SFX mappings
├── visual_style.yaml      # Image generation style prompts
├── voice_presets.yaml     # TTS voice mappings per archetype
├── inventory.yaml         # Item catalogs and economy rules
├── progression.yaml       # Leveling, affinities, milestones
├── topology.yaml          # World map regions and routes
├── tropes.yaml            # Narrative trope definitions
└── assets/                # Images, audio files
```

### Design Principles
1. **Convention over configuration** — sensible defaults; minimal packs are easy
2. **One file per concern** — each YAML file maps to one subsystem
3. **Assets with pack** — images/audio live alongside YAML
4. **Load-time validation** — serde deserialization catches schema errors early
5. **No code in packs** — YAML and assets only

### Rust Implementation
```rust
#[derive(Debug, Deserialize)]
pub struct GenrePack {
    pub pack: PackMeta,
    pub lore: LoreConfig,
    pub rules: RulesConfig,
    pub prompts: PromptsConfig,
    pub char_creation: CharCreationConfig,
    // ... etc
}
```

## Consequences
- Genre packs are shared between Rust API and Python daemon via `genre_packs/` in orchestrator
- Format cannot change unilaterally — both consumers must agree
- Adding a new YAML file requires a new struct and loader update
