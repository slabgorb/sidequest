# Genre Pack Gap Report

Generated 2026-06-09 from `sidequest-content/genre_packs`.
Scope: 11 genre packs, 21 worlds. Flags files/dirs that exist in *some* but not *all* siblings — the outlier pattern (`combat_design.md`, `magic_design.md`, etc.).

> **Update 2026-06-09 (GM pass) — resolutions & corrections.** Several outliers
> were actioned and two findings in this report were proven wrong against the live
> loader (`sidequest-server/sidequest/genre/loader.py`). This block is authoritative
> where it conflicts with the tables below; inline notes (`✅ RESOLVED` / `⚠ CORRECTION`)
> mark the affected rows.
>
> **Resolved:**
> - **`power_tiers.yaml` genre gap (elemental_harmony).** The world-level
>   `burning_peace/power_tiers.yaml` was a *misfiled genre file* (header reads
>   `# Power Tiers — elemental_harmony`, keyed by the 6 class names, no world flavor).
>   `git mv`'d to `elemental_harmony/power_tiers.yaml` — genre row now 11/11 universal,
>   and the dead world-level singleton is gone.
> - **`legends/` missing from perseus_cloud.** Authored 3 legends inferred from the
>   world's own history/lore (`the_last_lane`, `the_coelitha_survey`,
>   `the_lazzaro_compact`). Subdir now 21/21.
> - **Stray artifacts deleted:** `flickering_reach/magic.yaml.draft`,
>   `perseus_cloud/CAMPAIGN_NOTES.md`, `coyote_star/players-guide.md`.
> - **World-root `cultures.yaml` (burning_peace, glenross, blackthorn_moor) deleted** —
>   but see the correction below: they were *shadowed*, not redundant, and **glenross
>   was silently broken**. Its 6 naming cultures were migrated into
>   `glenross/cultures/*_names.yaml` (the documented blackthorn_moor pattern) *before*
>   deleting the root. glenross now loads 6 name-gen cultures (was **0**).
>
> **Corrections (this report had these wrong):**
> - **⚠ World-level `inventory.yaml` is NOT dead.** Epic 94 added a world-tier read
>   in `_load_single_world` (loader.py:1479) with world-first resolution; verified by
>   loading coyote_star (`credits` currency, 16 catalog items). The 13 world inventory
>   files are live, intended content (per ADR-140) — do **not** delete. Finding §3.7
>   below is superseded.
> - **⚠ World-root `cultures.yaml` was never "redundant."** The loader is
>   `if cultures/ dir exists: read dir, else read cultures.yaml` (loader.py:1144-1163) —
>   the dir *shadows* the root. The three root files held unique content the dir did not.
>   Finding §3.6 is corrected, not merely resolved.
>
> **Left as-is (correctly):** `premises.draft.yaml` (gulliver/wonderland) carry an
> explicit author header — *"Do NOT rename to premises.yaml until the engine schema
> lands"* (oq-3 engine work in flight; draft field shapes differ from oz's live v1).
> The `.draft` suffix is load-bearing, not an accidental gap.

**Companion spreadsheets:**
- `genre_pack_gaps_pack_level.csv` — full pack × file matrix (36 distinct files)
- `genre_pack_gaps_world_level.csv` — full world × file matrix, world-root depth (40 distinct files)

Status legend: `universal` = in all siblings · `near-universal-gap` = missing from exactly 1 (likely accidental) · `partial` = scattered · `singleton` = in exactly 1.

---

## 1. Pack level (11 packs)

Packs: caverns_and_claudes, elemental_harmony, heavy_metal, mutant_wasteland, neon_dystopia, pulp_noir, road_warrior, space_opera, spaghetti_western, tea_and_murder, wry_whimsy.

### Universal (11/11) — the expected baseline
`audio.yaml`, `axes.yaml`, `client_theme.css`, `lethality_policy.yaml`, `pack.yaml`, `progression.yaml`, `prompts.yaml`, `rules.yaml`, `theme.yaml`, `visibility_baseline.yaml`, `power_tiers.yaml` ✅

### Near-universal gap (10/11) — likely accidental
| file | missing from | status |
|------|--------------|--------|
| `power_tiers.yaml` | ~~**elemental_harmony**~~ | ✅ RESOLVED — genre file restored from misfiled world copy; now 11/11 universal |

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
| `cultures.yaml` (root) | ~~3~~ → 0 | ~~burning_peace, blackthorn_moor, glenross — **redundant**~~ ⚠ CORRECTION: **not redundant — shadowed.** Loader reads `cultures/` dir *instead of* the root when the dir exists. glenross's 6 name-gen cultures lived only in the shadowed root → **0 cultures loaded** until migrated to `cultures/*_names.yaml`. All 3 roots now deleted (content migrated/preserved). ✅ RESOLVED |
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
| ~~`power_tiers.yaml`~~ | ~~(1)~~ | ~~world override of pack file~~ ✅ RESOLVED — was a misfiled genre file (burning_peace); moved to `elemental_harmony/power_tiers.yaml`. World-level power_tiers is genre-only at runtime (never read), so a true world copy would have been dead anyway. |
| ~~`players-guide.md`~~ | ~~(1)~~ | ~~stray doc~~ ✅ DELETED (coyote_star) |
| `perseus_cloud.sector.json` | perseus_cloud | space_opera sector data |
| ~~`magic.yaml.draft`~~ | ~~(1)~~ | ~~**draft artifact, should not ship**~~ ✅ DELETED (flickering_reach) |
| `items.yaml` | (1) | vs. `inventory.yaml` naming drift |
| `inventions.yaml` | (1) | one-off |
| `faction_agendas.yaml` | (1) | one-off |
| `encounter_tables.yaml` | (1) | one-off |
| `demographics.yaml` | (1) | one-off |
| `confrontations.yaml` | (1) | one-off |
| `chart.yaml` | (1) | one-off |
| ~~`CAMPAIGN_NOTES.md`~~ | ~~(1)~~ | ~~**stray dev note, should not ship**~~ ✅ DELETED (perseus_cloud) |

### Subdirectories per world
| subdir | count | note |
|--------|-------|------|
| `assets/` | 21/21 | universal |
| `cultures/` | 21/21 | universal |
| `legends/` | ~~20/21~~ → 21/21 | ~~**missing from perseus_cloud**~~ ✅ RESOLVED — 3 legends authored for perseus_cloud |
| `scenarios/` | 3 | annees_folles, blackthorn_moor, glenross (mystery worlds) |
| `_drafts/` | 1 | evropi |
| `cookbook/` | 1 | beneath_sunden |
| `corpus/` | 1 | beneath_sunden |
| `rooms/` | 1 | beneath_sunden |

---

## 3. Findings worth action

1. **`*_design.md` are inconsistent dev notes.** `combat_design.md` (4 packs) and `magic_design.md` (3) cluster in neon_dystopia / pulp_noir / space_opera (+ road_warrior for combat). Either authoritative (backfill to all) or scratch (don't ship in `genre_packs/`). Decide and normalize.

2. **`power_tiers.yaml` missing only from elemental_harmony** (10/11) — almost certainly an accidental gap. ✅ **RESOLVED:** the burning_peace world copy was a misfiled genre file; `git mv`'d to genre level. Now 11/11.

3. **`legends/` missing only from perseus_cloud** (20/21) — accidental gap. ✅ **RESOLVED:** 3 legends authored from the world's own history/lore.

4. **Draft / stray artifacts shipping in content:** `magic.yaml.draft`, `CAMPAIGN_NOTES.md`, `players-guide.md`, the `exp001.*`/`exp002.*` experiment files (in benchmark dirs), `AUDIT-2026-04-18.md`, `sunday-progression.md`. Candidates for cleanup. ✅ **PARTIAL:** the three named genre-pack files (`magic.yaml.draft`, `CAMPAIGN_NOTES.md`, `players-guide.md`) deleted. The benchmark-dir experiment files / audit notes were out of this pass's scope. ⚠ Note: `premises.draft.yaml` is **not** in this category — it is *deliberately* unshipped pending an engine schema (explicit do-not-rename header); leave it.

5. **Naming drift:** world-root `items.yaml` (1) vs `inventory.yaml` (13); `creatures.yaml`/`creatures.json`/`monsters.yaml`/`monsters.json` all coexist alongside the universal `bestiary.yaml`. Consolidate to one canonical creature file.

6. ~~**Redundant world-root `cultures.yaml`** (3 worlds) duplicates the universal `cultures/` directory — legacy leftovers.~~ ⚠ **CORRECTED:** not redundant — *shadowed*. The loader reads the `cultures/` dir **instead of** the root `cultures.yaml` when the dir exists (`if/else`, loader.py:1144-1163). The three root files held content the dir did not. **glenross loaded 0 name-gen cultures** as a result (its dir had only `visual_tokens` overlays, which the loader skips for naming — they lack a `name:` key — and tea_and_murder has no genre-level cultures fallback). ✅ **RESOLVED:** glenross's 6 cultures migrated to `cultures/*_names.yaml` (the documented blackthorn_moor pattern); burning_peace's stale 8-nation root and blackthorn_moor's stale generic root deleted (content preserved in their dirs / sibling worlds). Verified post-fix: glenross 6, blackthorn_moor 3, burning_peace 3.

7. ~~**`char_creation.yaml` + `inventory.yaml` move together** (same 13 worlds)... worth confirming these inherit from pack level rather than silently lacking the feature.~~ ⚠ **CORRECTED (inventory half):** world-level `inventory.yaml` is **read and resolved world-first** (epic 94, `_load_single_world` loader.py:1479) — it is *not* dead and is *not* a silent gap. Verified by loading coyote_star (`credits` currency, 16 catalog items). The 13 world inventory files are intended, live per-world catalogs (ADR-140). `char_creation.yaml` world-vs-genre inheritance was not separately re-verified in this pass.
