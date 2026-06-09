# Genre Pack Gap Report

Generated 2026-06-09 from `sidequest-content/genre_packs`.
Scope: 11 genre packs, 21 worlds. Flags files/dirs that exist in *some* but not *all* siblings — the outlier pattern (`combat_design.md`, `magic_design.md`, etc.).

**Companion spreadsheets:**
- `genre_pack_gaps_pack_level.csv` — full pack × file matrix (36 distinct files)
- `genre_pack_gaps_world_level.csv` — full world × file matrix, world-root depth (40 distinct files)

Status legend: `universal` = in all siblings · `near-universal-gap` = missing from exactly 1 (likely accidental) · `partial` = scattered · `singleton` = in exactly 1.

---

## 1. Pack level (11 packs)

Packs: caverns_and_claudes, elemental_harmony, heavy_metal, mutant_wasteland, neon_dystopia, pulp_noir, road_warrior, space_opera, spaghetti_western, tea_and_murder, wry_whimsy.

### Universal (11/11) — the expected baseline
`audio.yaml`, `axes.yaml`, `client_theme.css`, `lethality_policy.yaml`, `pack.yaml`, `progression.yaml`, `prompts.yaml`, `rules.yaml`, `theme.yaml`, `visibility_baseline.yaml`

### Near-universal gap (10/11) — likely accidental
| file | missing from |
|------|--------------|
| `power_tiers.yaml` | **elemental_harmony** |

### Partial
| file | count | present in |
|------|-------|-----------|
| `archetypes.yaml` | 8 | cav, ele, hea? — all except heavy_metal, spaghetti_western, tea_and_murder |
| `tropes.yaml` | 8 | all except heavy_metal, space_opera, spaghetti_western |
| `achievements.yaml` | 7 | mut, neo, pul, roa, spaW, tea, wry |
| `archetype_constraints.yaml` | 7 | cav, ele, hea, neo, pul, spaO, wry |
| `classes.yaml` | 7 | cav, ele, hea, roa, spaO, spaW, wry |
| `inventory.yaml` | 7 | cav, mut, neo, pul, roa, tea, wry |
| `visual_style.yaml` | 7 | cav, mut, neo, pul, roa, spaW, tea |
| `char_creation.yaml` | 6 | cav, mut, neo, pul, roa, wry |
| `magic.yaml` | 6 | cav, mut, roa, spaO, spaW, tea |
| `projection.yaml` | 6 | cav, hea, mut, roa, spaO, spaW |
| `beat_vocabulary.yaml` | 5 | cav, hea, roa, tea, wry |
| `cultures.yaml` | 5 | cav, mut, neo, pul, roa |
| **`combat_design.md`** | 4 | neon_dystopia, pulp_noir, road_warrior, space_opera |
| `openings.yaml` | 4 | neo, pul, roa, wry |
| **`magic_design.md`** | 3 | neon_dystopia, pulp_noir, space_opera |
| `bestiary.yaml` | 2 | mutant_wasteland, neon_dystopia |
| `equipment_tables.yaml` | 2 | caverns_and_claudes, tea_and_murder |
| `spells_wwn.yaml` | 2 | elemental_harmony, heavy_metal |

### Singletons (1/11)
| file | only in |
|------|---------|
| `backstory_tables.yaml` | caverns_and_claudes |
| `spellbook.yaml` | caverns_and_claudes |
| `pacing.yaml` | mutant_wasteland |
| `powers.yaml` | road_warrior |
| `seed_tropes.yaml` | wry_whimsy |
| `witnessed_acts.yaml` | wry_whimsy |
| `weather.yaml` | tea_and_murder |

---

## 2. World level (21 worlds, world-root depth)

### Universal (21/21) — the expected baseline
`world.yaml`, `archetypes.yaml`, `bestiary.yaml`, `cartography.yaml`, `history.yaml`, `lore.yaml`, `openings.yaml`, `portrait_manifest.yaml`, `tropes.yaml`, `visual_style.yaml`

### Partial
| file | count | present in |
|------|-------|-----------|
| `char_creation.yaml` | 13 | all elemental_harmony, heavy_metal, space_opera, spaghetti_western, tea_and_murder worlds — **missing from every caverns, mutant, neon, pulp, road_warrior, wry_whimsy world** |
| `inventory.yaml` | 13 | (identical set to char_creation.yaml) |
| `npcs.yaml` | 12 | barsoom, the_circuit, all space_opera, five_points, the_real_mccoy, both tea_and_murder, all wry_whimsy |
| `archetype_funnels.yaml` | 10 | both elemental_harmony, evropi, long_foundry, aureate_span, coyote_star, five_points, all wry_whimsy |
| `cultures.yaml` (root) | 3 | burning_peace, blackthorn_moor, glenross — **redundant: `cultures/` dir is 21/21** |
| `calendar.yaml` | 3 | dust_and_lead, the_real_mccoy, glenross |
| `audio.yaml` (world) | 3 | barsoom, five_points, the_real_mccoy |
| `creatures.yaml` | 2 | beneath_sunden, flickering_reach |
| `classes.yaml` | 2 | blackthorn_moor, glenross |
| `magic.yaml` | 2 | long_foundry, coyote_star |
| `orbits.yaml` | 2 | coyote_star, perseus_cloud (space_opera only) |
| `premises.draft.yaml` | 2 | gulliver, wonderland |

### Singletons (1/21) — structural one-offs at world root
| file | only in | likely nature |
|------|---------|---------------|
| `world_register.yaml` | (1) | one-off |
| `seed_tropes.yaml` | (1) | one-off |
| `rigs.yaml` | the_circuit | road_warrior vehicles |
| `chassis_classes.yaml` | the_circuit | road_warrior vehicles |
| `projection.yaml` | (1) | one-off |
| `premises.yaml` | (1) | non-draft premise |
| `power_tiers.yaml` | (1) | world override of pack file |
| `players-guide.md` | (1) | stray doc |
| `perseus_cloud.sector.json` | perseus_cloud | space_opera sector data |
| `magic.yaml.draft` | (1) | **draft artifact, should not ship** |
| `items.yaml` | (1) | vs. `inventory.yaml` naming drift |
| `inventions.yaml` | (1) | one-off |
| `faction_agendas.yaml` | (1) | one-off |
| `encounter_tables.yaml` | (1) | one-off |
| `demographics.yaml` | (1) | one-off |
| `confrontations.yaml` | (1) | one-off |
| `chart.yaml` | (1) | one-off |
| `CAMPAIGN_NOTES.md` | (1) | **stray dev note, should not ship** |

### Subdirectories per world
| subdir | count | note |
|--------|-------|------|
| `assets/` | 21/21 | universal |
| `cultures/` | 21/21 | universal |
| `legends/` | 20/21 | **missing from perseus_cloud** (near-universal gap) |
| `scenarios/` | 3 | annees_folles, blackthorn_moor, glenross (mystery worlds) |
| `_drafts/` | 1 | evropi |
| `cookbook/` | 1 | beneath_sunden |
| `corpus/` | 1 | beneath_sunden |
| `rooms/` | 1 | beneath_sunden |

---

## 3. Findings worth action

1. **`*_design.md` are inconsistent dev notes.** `combat_design.md` (4 packs) and `magic_design.md` (3) cluster in neon_dystopia / pulp_noir / space_opera (+ road_warrior for combat). Either authoritative (backfill to all) or scratch (don't ship in `genre_packs/`). Decide and normalize.

2. **`power_tiers.yaml` missing only from elemental_harmony** (10/11) — almost certainly an accidental gap.

3. **`legends/` missing only from perseus_cloud** (20/21) — accidental gap.

4. **Draft / stray artifacts shipping in content:** `magic.yaml.draft`, `CAMPAIGN_NOTES.md`, `players-guide.md`, the `exp001.*`/`exp002.*` experiment files (in benchmark dirs), `AUDIT-2026-04-18.md`, `sunday-progression.md`. Candidates for cleanup.

5. **Naming drift:** world-root `items.yaml` (1) vs `inventory.yaml` (13); `creatures.yaml`/`creatures.json`/`monsters.yaml`/`monsters.json` all coexist alongside the universal `bestiary.yaml`. Consolidate to one canonical creature file.

6. **Redundant world-root `cultures.yaml`** (3 worlds) duplicates the universal `cultures/` directory — legacy leftovers.

7. **`char_creation.yaml` + `inventory.yaml` move together** (same 13 worlds). The 8 worlds missing both span caverns, mutant, neon, pulp, road_warrior, and all wry_whimsy — worth confirming these inherit from pack level rather than silently lacking the feature.
