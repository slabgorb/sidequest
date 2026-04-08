# ADR-072: System/Milieu Decomposition — Separating Mechanics from Aesthetic

## Status

Proposed

## Context

ADR-003 established genre packs as monolithic YAML directories that configure all game
personality. In practice, genre packs bundle three orthogonal concerns:

1. **Mechanics (system)** — stats, classes, combat model, progression, tropes, archetypes
2. **Aesthetic (milieu)** — visual style, audio, narrator voice, cultures, naming, UI theme
3. **World instances** — geography, NPCs, rooms, factions, history

This coupling prevents reuse. Pirate boarding mechanics can't be paired with a Spelljammer
milieu without duplicating an entire genre pack. Gangster territory mechanics are forced into
the pulp noir detective pack. Dueling mechanics can't serve both Revolutionary France and
Revolutionary Boston.

The problem is compounded by world-level overrides. Files like `tropes.yaml`,
`archetypes.yaml`, `visual_style.yaml`, and `cultures.yaml` appear at both genre and world
level with implicit inheritance/merge semantics. A content author cannot look at a single
layer and know what it owns.

### Current state (11 genre packs)

Each pack is a monolith: `caverns_and_claudes`, `elemental_harmony`, `low_fantasy`,
`mutant_wasteland`, `neon_dystopia`, `pulp_noir`, `road_warrior`, `space_opera`,
`spaghetti_western`, `star_chamber`, `victoria`.

Each world (16 total) duplicates 5-8 genre-level files with additive or replacement
semantics resolved by the loader at runtime.

## Decision

Decompose genre packs into three composable layers with strict ownership boundaries.

### New directory structure

```
sidequest-content/
  systems/                          # MECHANICS — the game
    pirate/
      rules.yaml                    # stats, classes, HP formula
      progression.yaml              # leveling, advancement
      combat_design.md              # combat model and lethality
      tropes.yaml                   # mechanical narrative beats
      archetypes.yaml               # NPC mechanical templates (stat ranges, dispositions)
      char_creation.yaml            # chargen flow
      axes.yaml                     # tuning knobs
      inventory.yaml                # item categories, economy

  milieus/                          # AESTHETIC — the setting wrapper
    caribbean/
      theme.yaml                    # visual/audio tone
      visual_style.yaml             # Flux prompt style, LoRA refs
      audio.yaml                    # music mood mapping
      cultures.yaml                 # naming conventions, social norms
      names/                        # corpus for name generation
      prompts.yaml                  # narrator voice, prose style
      client_theme.css              # UI chrome
      lore.yaml                     # general setting knowledge
      personas.yaml                 # milieu-flavored character types (non-mechanical)

  genre_packs/                      # COMPOSITION — thin manifest + worlds
    pirates_caribbean/
      pack.yaml                     # name, description, system ref, milieu ref, creative brief
      worlds/
        tortuga/
          world.yaml                # geography, time, axis_snapshot
          cartography.yaml          # room graph
          rooms.yaml                # tactical grids
          history.yaml              # world-specific lore
          legends.yaml              # world-specific legends
          factions.yaml             # world-specific factions
          openings.yaml             # session openers
          portrait_manifest.yaml    # character portrait specs
          creatures.yaml            # bestiary (if applicable)
          encounter_tables.yaml     # encounter generation
```

### pack.yaml schema extension

```yaml
# genre_packs/pirates_caribbean/pack.yaml
name: "Pirates of the Caribbean"
version: "1.0.0"
system: pirate              # resolves to systems/pirate/
milieu: caribbean           # resolves to milieus/caribbean/
description: >-
  Swashbuckling adventure on the high seas...
inspirations:
  - name: "Pirates of the Caribbean"
    element: "Supernatural piracy, comedic action"
core_vibe: >-
  The sea doesn't care about your plans.
```

Legacy packs without `system:` and `milieu:` fields continue to work — the loader
falls back to loading all files from the pack directory as today.

### Responsibility contract

| Layer | Owns | Does NOT own |
|-------|------|-------------|
| **System** | rules, progression, combat_design, tropes, archetypes, char_creation, axes, inventory | Visual style, narrator voice, cultures, names, audio, theme |
| **Milieu** | theme, visual_style, audio, cultures, names, prompts, client_theme, lore, personas | Rules, stats, combat, progression, archetypes |
| **Genre Pack** | pack.yaml (composition manifest + creative brief) | No other YAML files |
| **World** | world, cartography, rooms, history, legends, factions, openings, portrait_manifest, creatures, encounter_tables | No tropes, no archetypes, no visual_style, no cultures, no personas |

**Enforcement:** No file name may appear at more than one layer. The validator
(`sidequest-validate`) checks that system directories contain only mechanics files,
milieu directories contain only aesthetic files, and world directories contain only
instance files. Violation is a build error.

### Loader resolution

```
1. Read pack.yaml from genre_pack directory
2. If system: and milieu: refs present:
   a. Load mechanics from systems/{system_ref}/
   b. Load aesthetics from milieus/{milieu_ref}/
   c. Load worlds from genre_packs/{pack}/worlds/
   d. Assemble into GenrePack struct (unchanged)
3. If refs absent (legacy pack):
   a. Load everything from genre_packs/{pack}/ (current behavior)
```

No merge, no inheritance, no override chains. Each file has exactly one source.
If both `systems/pirate/rules.yaml` and `milieus/caribbean/rules.yaml` exist,
the loader returns an error — not a merge.

### Archetype vs. Persona distinction

- **Archetypes** (system) — mechanical templates: stat ranges, typical classes,
  disposition defaults, combat behavior. "The Quartermaster: Savvy 14-16, loyal,
  inventory-focused."
- **Personas** (milieu) — flavored character types: cultural role, dialogue quirks,
  visual description. "The Port Royal Governor: powdered wig, imperious manner,
  speaks in proclamations."

The NPC generator composes them: pick a mechanical archetype from the system,
dress it with a persona from the milieu, instantiate with world-specific names
and history.

### Migration strategy

1. **Phase 0** — Add `system:` and `milieu:` fields to `pack.yaml` schema.
   Loader recognizes but doesn't require them. Zero breakage.
2. **Phase 1** — Extract first milieu: pull aesthetic files from `pulp_noir` into
   `milieus/jazz_age/`. Update `pulp_noir/pack.yaml` to ref it. Validate.
3. **Phase 2** — Extract first system: pull mechanics files from `pulp_noir` into
   `systems/noir_detective/`. Update pack.yaml. Now `pulp_noir` is fully decomposed.
4. **Phase 3** — Create `gangsters_prohibition` as `system: gangster, milieu: jazz_age`.
   First new combination from shared milieu.
5. **Phase 4** — Migrate remaining packs, one at a time. Each is a 2-point chore.
6. **Phase 5** — Remove legacy fallback from loader. All packs use refs.

### Existing pack decomposition map

| Current Pack | System | Milieu |
|-------------|--------|--------|
| caverns_and_claudes | dungeon_crawl | high_fantasy |
| elemental_harmony | elemental | eastern_fantasy |
| low_fantasy | gritty_adventure | low_fantasy |
| mutant_wasteland | wasteland_survival | postapocalyptic |
| neon_dystopia | cyberpunk | cyberpunk_noir |
| pulp_noir | noir_detective | jazz_age |
| road_warrior | vehicular_combat | automotive_wasteland |
| space_opera | space_adventure | space_opera |
| spaghetti_western | gunslinger | old_west |
| star_chamber | political_intrigue | renaissance |
| victoria | gothic_mystery | victorian |

Some of these will discover shared milieus or systems as content grows.

## Consequences

### Positive
- Any system can pair with any milieu — combinatorial content creation
- Content authors work in one layer at a time with clear ownership
- Worlds become lightweight (geography + instances only)
- No more implicit inheritance or "which layer did this rule come from?"
- Validation gate enforces boundaries mechanically
- Community contributions become possible at the system or milieu level independently
- LoRAs can be trained per milieu (aesthetic) rather than per genre pack

### Negative
- Migration effort for 11 existing packs (~22 chores at 2 points each)
- Loader gains complexity (three-path resolution vs. single directory)
- `GenrePack` struct construction becomes an assembly step, not a direct deserialize
- Content authors must understand the three-layer model
- Some files may need splitting (cultures.yaml has both naming conventions and social mechanics)

### Neutral
- `GenrePack` struct itself is unchanged — downstream code (narrator, chargen, combat) unaffected
- ADR-003 is superseded for directory structure but its design principles remain valid
- ADR-052 (narrative axis system) unaffected — axes stay in systems as tuning knobs
- ADR-056 (script tool generators) unaffected — generators read the assembled GenrePack
