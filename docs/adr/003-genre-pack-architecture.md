---
id: 3
title: "Genre Pack Architecture"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [82, 91]
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-003: Genre Pack Architecture

## Implementation status (2026-05-02)

**The filesystem is the source of truth for genre-pack layout.** Look at any pack under `sidequest-content/genre_packs/` (e.g. `caverns_and_claudes/`) for the canonical structure — this ADR does not enumerate the file list, because the list grows and decays faster than ADR maintenance can keep up.

Live wiring (Python, post-ADR-082):
- **Loader:** `sidequest-server/sidequest/genre/loader.py` — `load_genre_pack(path) -> GenrePack` (line 753), with a cached variant `load_genre_pack_cached` (line 1032) backed by `sidequest-server/sidequest/genre/cache.py`.
- **Models:** `sidequest-server/sidequest/genre/models/` — Pydantic models (frozen where appropriate). Deserialization is via PyYAML + Pydantic, not `serde_yaml`.
- **Pack root:** `sidequest-content/genre_packs/` — `caverns_and_claudes`, `elemental_harmony`, `heavy_metal`, `mutant_wasteland`, `space_opera`, `spaghetti_western`, `victoria` are the seven live packs as of this writing.
- **Both consumers Python.** Post-port, `sidequest-server` and `sidequest-daemon` both load from the same `genre_packs/` tree. The "shared between Rust API and Python daemon" wording in the original Consequences below is doubly obsolete (Rust is gone; both consumers are Python).

### Genre vs world (the second axis)

Each pack hosts a `worlds/<world>/` subdirectory holding world-specific data. The split tracks SOUL.md's "Crunch in the Genre, Flavor in the World" principle: a genre is the rulebook (mechanics, archetypes, tone axes); a world is the campaign setting (factions, geography, named NPCs, legends). One genre, many worlds — swap the world, keep the rules. Loader handles both layers.

### Load-bearing core files

A genre pack's identity is established by a small set of always-required files. Beyond these, additional YAML files come and go as subsystems are added (see ADR-091 for `corpus/` + `cultures.yaml`, ADR-053 for scenarios, etc.).

- `pack.yaml` — metadata
- `archetypes.yaml` — character classes / archetypes
- `prompts.yaml` — agent prompt extensions
- `rules.yaml` — game mechanics and constraints
- `tropes.yaml` — narrative trope definitions

Drift watch — if any of the following happens, this ADR is wrong:
- A genre pack starts shipping executable code (Python/JS), not YAML + assets.
- A consumer bypasses `load_genre_pack` and parses pack YAML directly.
- The `worlds/<world>/` split is collapsed back into a flat single-world-per-pack layout.

The original 2026-03-25 decision is preserved below for historical context.

## Context
Genre packs are swappable YAML directories that configure all game personality: lore, rules, prompt extensions, UI theming, audio, visual styles, inventory, progression, world topology, and tropes.

## Decision
Each genre pack is a directory of YAML files plus assets, loaded at startup into typed structs by a single loader. No code in packs — YAML and assets only.

### Design Principles
1. **Convention over configuration** — sensible defaults; minimal packs are easy
2. **One file per concern** — each YAML file maps to one subsystem
3. **Assets with pack** — images/audio live alongside YAML
4. **Load-time validation** — deserialization catches schema errors early
5. **No code in packs** — YAML and assets only

> **Historical context (port era).** The original 2026-03-25 form of this ADR specified Rust + `serde_yaml` deserialization. After ADR-082 the implementation is Python + Pydantic; the loader function name and shape carry over but the type system changed. The Rust struct sketch below is preserved as a record of the original decision.

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
- Genre packs are loaded by `sidequest-server` at startup and by `sidequest-daemon` when generating media — both reach into the same `sidequest-content/genre_packs/` tree.
- Pack format is governed by Pydantic models in `sidequest-server/sidequest/genre/models/`. Schema changes require a model update and load-time validation continues to catch malformed YAML.
- Adding a new subsystem to packs is an additive change: drop in a new YAML file, add a Pydantic model, wire it into the loader. No other consumer is forced to read it.
