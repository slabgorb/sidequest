# Genre Pack Filesystem Schema

**Date:** 2026-05-25
**Status:** Draft
**Scope:** sidequest-content file structure standardization, server loader validation, audit tooling

## Problem

Genre pack file structure has drifted across 10 active packs:

- 17 files are universal but nothing enforces that; heavy_metal is missing `client_theme.css`
- Genre-specific files (spellbook.yaml, chassis_classes.yaml, powers.yaml) appear ad-hoc with no declaration of what's intentional vs accidental
- Asset directories are split between `images/` and `assets/` with no consistent layout
- World-level files use `cultures.yaml` (single file) in some worlds and `cultures/` (directory) in others
- Audio has `set-1/`, `set-2/`, `music-set-1/`, `themed/` subdirectory drift
- Corpus word lists are scattered across per-pack `corpus/` dirs and the centralized `sidequest-content/corpus/`
- `genre_workshopping/` conflates deprecated packs, in-progress packs, and unfinished worlds for live packs
- No way to validate a pack without booting the game server

**Pain points:** loader brittleness on missing files, no authoring template for new packs, no machine-readable completeness checks.

## Design

### Pack Schema File

`sidequest-content/pack_schema.yaml` defines the canonical structure. Single source of truth for the loader, audit tooling, and pack scaffolding.

```yaml
schema_version: "1.0"

genre_pack:
  required_files:
    - pack.yaml
    - theme.yaml
    - archetypes.yaml
    - tropes.yaml
    - lore.yaml
    - visual_style.yaml
    - audio.yaml
    - rules.yaml
    - cultures.yaml
    - char_creation.yaml
    - inventory.yaml
    - lethality_policy.yaml
    - power_tiers.yaml
    - progression.yaml
    - prompts.yaml
    - axes.yaml
    - visibility_baseline.yaml
    - client_theme.css

  required_dirs:
    - audio/music
    - assets/fonts
    - assets/images/portraits
    - assets/images/poi
    - worlds

  extensions:
    magic:
      files: [magic.yaml]
    classes:
      files: [classes.yaml]
    spellbook:
      files: [spellbook.yaml]
      dirs: [spells]
    openings:
      files: [openings.yaml]
    projection:
      files: [projection.yaml]
    beat_vocabulary:
      files: [beat_vocabulary.yaml]
    archetype_constraints:
      files: [archetype_constraints.yaml]
    achievements:
      files: [achievements.yaml]
    powers:
      files: [powers.yaml]
    chassis_classes:
      files: [chassis_classes.yaml]
    calendar:
      files: [calendar.yaml]
    weather:
      files: [weather.yaml]
    history:
      files: [history.yaml]
    dogfight:
      dirs: [dogfight]
    pacing:
      files: [pacing.yaml]
    seed_tropes:
      files: [seed_tropes.yaml]
    equipment_tables:
      files: [equipment_tables.yaml]
    backstory_tables:
      files: [backstory_tables.yaml]

world:
  required_files:
    - world.yaml
    - cartography.yaml
    - history.yaml
    - lore.yaml
    - openings.yaml
    - portrait_manifest.yaml
    - tropes.yaml
    - visual_style.yaml
    - archetypes.yaml

  required_dirs:
    - cultures
    - legends
    - assets/images/portraits
    - assets/images/poi

  extensions:
    archetype_funnels:
      files: [archetype_funnels.yaml]
    npcs:
      files: [npcs.yaml]
    creatures:
      files: [creatures.yaml]
    magic:
      files: [magic.yaml]
    confrontations:
      files: [confrontations.yaml]
    encounter_tables:
      files: [encounter_tables.yaml]
    calendar:
      files: [calendar.yaml]
    demographics:
      files: [demographics.yaml]
    rooms:
      dirs: [rooms]
    cookbook:
      dirs: [cookbook]
    world_register:
      files: [world_register.yaml]
    faction_agendas:
      files: [faction_agendas.yaml]
    orbits:
      files: [orbits.yaml]
    rigs:
      files: [rigs.yaml]
    inventions:
      files: [inventions.yaml]
```

### Extension Declaration

`pack.yaml` gains an `extensions` key:

```yaml
# pack.yaml (example: caverns_and_claudes)
name: "Caverns & Claudes"
version: "1.1.0"
extensions:
  - magic
  - classes
  - spellbook
  - projection
  - beat_vocabulary
  - archetype_constraints
  - backstory_tables
  - equipment_tables
```

`world.yaml` gains the same key:

```yaml
# world.yaml (example: beneath_sunden)
name: "Beneath Sünden"
extensions:
  - creatures
  - rooms
  - cookbook
  - world_register
```

**Rules:**
- Declared extension: its files/dirs MUST exist
- Undeclared: its files/dirs MUST NOT exist (no orphans)
- The schema maps each extension name to expected files and directories

**Orphan detection:** A file in a pack or world directory is an orphan if it is not: (a) a required file, (b) a declared extension's file, or (c) at world level, a valid override of a genre-level file (any file whose name matches a genre-level required file or declared extension file). Orphans are reported as warnings, not errors — they may indicate a missing extension declaration or dead content.

### World Overrides

Any genre-level file (required or extension) can be overridden at world level by placing a same-named file in the world directory. No declaration needed. The loader picks the world version over the genre version.

This is implicit — if `worlds/the_real_mccoy/audio.yaml` exists, it overrides `audio.yaml` from the genre root. The override must validate against the same Pydantic model as its genre-level counterpart.

### Asset Directory Structure

Single `assets/` tree at both genre and world level. Identical structure:

```
assets/
├── fonts/
├── documents/
└── images/
    ├── portraits/
    └── poi/
```

Genre-level and world-level are mirrors. World assets override or supplement genre assets.

**Migration from current state:**
- `images/` at genre root → `assets/images/`
- Loose images at `assets/` root → proper subdirs
- `names/` (pulp_noir) → centralized corpus
- `_drafts/` (heavy_metal) → genre_workshopping or delete
- `themes/` (caverns_and_claudes) → audit and remove if dead

### Audio Directory Structure

Genre-level:
```
audio/
├── music/
│   └── {mood}_{density}_input_params.json
│   └── {mood}_{density}_alt{N}_input_params.json    # variants by filename suffix
├── sfx/
└── pd/
    └── LICENSE.md
```

World-level mirrors without `pd/`:
```
audio/
├── music/
│   └── {mood}_{density}_input_params.json
└── sfx/
```

**Migration:** `set-1/`, `set-2/`, `music-set-1/`, `themed/` subdirectories flatten into the parent `music/` directory. Multiple tracks for the same mood+density are distinguished by `_alt1`, `_alt2` etc. filename suffixes.

### Corpus Centralization

`sidequest-content/corpus/` is the single location for conlang word lists (per ADR-091).

**Migration:** Per-pack `corpus/` directories and `names/` directories merge into `sidequest-content/corpus/`. Duplicate entries across packs consolidate. Culture-specific files keep their culture name as the key.

Genre-level and world-level `corpus/` directories are eliminated after migration.

### World-Level Directory Files

World-level `cultures` and `legends` are always directories, not single files:

```
worlds/{world}/
├── cultures/
│   ├── {culture_name}.yaml
│   └── ...
└── legends/
    ├── {legend_name}.yaml
    └── ...
```

**Migration:** Existing `cultures.yaml` files split into per-culture files under `cultures/`. Same for `legends.yaml` → `legends/`.

### Pack Lifecycle: Workshopping and Drafts

**`genre_workshopping/`** holds full packs in progress. Same schema as `genre_packs/`, same validation. The loader does not serve workshopping packs to players.

**Draft worlds** are unfinished worlds inside a live pack. Declared with `draft: true` in `world.yaml`:

```yaml
# world.yaml
name: "Some Unfinished World"
draft: true
```

- Loader skips draft worlds
- Audit reports completeness gaps as warnings, not errors
- Same schema, same validation, just not served

**Migration from current workshopping:**
- `low_fantasy/` stays in `genre_workshopping/`
- `caverns_sunden/` is deprecated — delete or archive
- Alternate-world subdirs (elemental_harmony, space_opera, tea_and_murder workshopping entries) move into their parent pack's `worlds/` as draft worlds

### Validate Command

Runs without booting the game server. Uses the same Pydantic models as the loader.

```bash
just content-validate caverns_and_claudes       # one pack
just content-validate-all                       # all packs + workshopping
just content-validate caverns_and_claudes --verbose
```

**Validation gates (in order):**

1. **Presence** — required files exist, declared extensions exist, no orphan files
2. **Schema** — every YAML file passes Pydantic model validation
3. **Override consistency** — world-level overrides validate against the same model as their genre-level counterpart
4. **Assets** — portraits have image files, POI entries in cartography have images in `assets/images/poi/`, fonts in `client_theme.css` exist in `assets/fonts/`
5. **Corpus** — cultures reference entries that exist in `sidequest-content/corpus/`
6. **World completeness** — non-draft worlds have all required files; draft worlds report gaps as warnings
7. **Cross-references** — tropes reference valid archetypes, archetype_funnels reference valid archetypes, openings reference valid cartography locations

**Output:**
```
caverns_and_claudes .............. PASS (2 warnings)
  ⚠ orphan file: backstory_tables.yaml (not required, not declared as extension)
  ⚠ world beneath_sunden: assets/images/poi/ missing 3 of 12 declared POIs

heavy_metal ...................... FAIL (1 error, 1 warning)
  ✗ missing required: client_theme.css
  ⚠ world long_foundry: draft world, 4 required files missing
```

**Exit codes:** errors = nonzero, warnings only = zero. Warnings don't block CI.

## Canonical Genre Pack Tree

After migration, every genre pack looks like this:

```
{genre}/
├── pack.yaml                    # required — includes extensions: list
├── theme.yaml                   # required
├── archetypes.yaml              # required
├── tropes.yaml                  # required
├── lore.yaml                    # required
├── visual_style.yaml            # required
├── audio.yaml                   # required
├── rules.yaml                   # required
├── cultures.yaml                # required
├── char_creation.yaml           # required
├── inventory.yaml               # required
├── lethality_policy.yaml        # required
├── power_tiers.yaml             # required
├── progression.yaml             # required
├── prompts.yaml                 # required
├── axes.yaml                    # required
├── visibility_baseline.yaml     # required
├── client_theme.css             # required
├── {extension}.yaml             # declared extensions only
├── audio/
│   ├── music/
│   │   └── {mood}_{density}[_alt{N}]_input_params.json
│   ├── sfx/
│   └── pd/
│       └── LICENSE.md
├── assets/
│   ├── fonts/
│   ├── documents/
│   └── images/
│       ├── portraits/
│       └── poi/
└── worlds/
    └── {world}/
        ├── world.yaml           # required — includes extensions: list, optional draft: true
        ├── cartography.yaml     # required
        ├── history.yaml         # required
        ├── lore.yaml            # required
        ├── openings.yaml        # required
        ├── portrait_manifest.yaml  # required
        ├── tropes.yaml          # required
        ├── visual_style.yaml    # required
        ├── archetypes.yaml      # required
        ├── {extension}.yaml     # declared extensions only
        ├── {override}.yaml      # genre-level file override, no declaration needed
        ├── cultures/
        │   └── {culture}.yaml
        ├── legends/
        │   └── {legend}.yaml
        ├── audio/               # mirrors genre audio structure (no pd/)
        │   ├── music/
        │   └── sfx/
        └── assets/              # mirrors genre assets structure
            ├── fonts/
            ├── documents/
            └── images/
                ├── portraits/
                └── poi/
```

## Out of Scope

- Changing the Pydantic models themselves — they're already correct
- Rewriting the loader — it adds schema-file awareness, not a new architecture
- Content quality auditing (lore depth, NPC diversity) — that's the GM audit skill, not the schema validator
- Music generation pipeline — audio structure changes are file renames, not daemon changes
