# Genre Pack Status Matrix

> Per-world asset status. Source of truth: `sidequest-content/r2_manifest.json`
> (full R2 bucket scan — see "Asset Hosting" in `sidequest-content/CLAUDE.md`).
> Counts below are R2 object counts per world, regenerated from the manifest.
> **Last refreshed: 2026-06-12.** To refresh: rebuild the manifest with
> `uv run python scripts/r2_manifest_from_bucket.py`, then recount.
>
> This file is referenced by `docs/architecture.md` and
> `docs/feature-inventory.md` as "the current matrix."

## Summary

- **11 packs, 22 worlds, all live** — no world sets `draft: true` as of 2026-06-12.
- **Every world has POI landscapes on R2 — zero POI gaps across all packs.**
  The old "asset gate" framing (worlds held back pending renders) currently
  gates nothing.
- **Portraits are complete except 7 errored `heavy_metal` pickers** that failed
  during render and were never uploaded: 5 in `evropi` (`picker_antman_scoutdrone_m01`,
  `picker_gnome_tunnelwise_f01`, `picker_half_orc_minehand_m01`,
  `picker_vaermm_copyist_f01`, `picker_zked_daggereye_f01`) and 2 in `long_foundry`
  (`picker_astran_feed_keeper_f01`, `picker_kragmoor_thaumaturge_m01`). These need a
  re-render. `heavy_metal/barsoom` is **complete** — no outstanding portrait gap.
- Otherwise the only remaining unrendered assets are authored-but-not-rendered music
  variations (see below); R2 holds a surplus of objects, not a deficit.

## Per-world matrix

POI / portrait counts are R2 objects under `worlds/<world>/assets/`. Music is
pack-level (`genre_packs/<pack>/audio/music/`, ADR-095) unless noted.

| Pack | World | POIs | Portraits | Notes |
|------|-------|-----:|----------:|-------|
| caverns_and_claudes | beneath_sunden | 5 | 18 | +7 creature images; WWN port + 105-2 seam registry (entrance room) landed 2026-06-12 |
| elemental_harmony | burning_peace | 8 | 22 | |
| elemental_harmony | shattered_accord | 19 | 26 | |
| heavy_metal | evropi | 43 | 44 | 5 picker portraits errored at render, not yet uploaded |
| heavy_metal | long_foundry | 25 | 7 | 2 picker portraits errored at render, not yet uploaded |
| heavy_metal | barsoom | 17 | 13 | WWN ruleset; live 2026-06-05; portraits complete |
| mutant_wasteland | flickering_reach | 20 | 5 | fully spoilable (only world that is) |
| mutant_wasteland | seaboard_of_saints | 18 | 51 | leitmotif music tracks on R2 |
| neon_dystopia | franchise_nations | 8 | 27 | |
| pulp_noir | annees_folles | 12 | 12 | |
| road_warrior | the_circuit | 22 | 32 | |
| space_opera | aureate_span | 21 | 7 | baroque corona megastation |
| space_opera | coyote_star | 15 | 19 | former "coyote_star POI gap" closed |
| space_opera | perseus_cloud | 10 | 23 | Jade's world (homebrew via PR path) |
| spaghetti_western | dust_and_lead | 16 | 6 | |
| spaghetti_western | five_points | 12 | 32 | |
| spaghetti_western | the_real_mccoy | 13 | 12 | |
| tea_and_murder | glenross | 14 | 31 | |
| tea_and_murder | blackthorn_moor | 8 | 23 | live (was the last draft world; promoted by 2026-06-12) |
| wry_whimsy | oz | 12 | 32 | shared PD music via `assets/` prefix (whole pack) |
| wry_whimsy | wonderland | 14 | 22 | |
| wry_whimsy | gulliver | 18 | 19 | |

## Pack music on R2 (track counts)

caverns_and_claudes 33 · elemental_harmony 187 · heavy_metal 41 ·
mutant_wasteland 195 · neon_dystopia 54 · pulp_noir 42 · road_warrior 150 ·
space_opera 86 · spaghetti_western 58 · wry_whimsy uses shared PD music under
the `assets/` prefix.

### Authored-but-unrendered music

`audio.yaml` authors 126 music tracks (a2a / leitmotif variations) that have no
rendered `.ogg` on R2: **60 in elemental_harmony, 60 in space_opera, 6 in
tea_and_murder**. The tea_and_murder 6 are a bookkeeping artifact — they *are*
rendered, but under the legacy `victoria/` pack key (see "Known legacy R2 keys"
below), so the manifest sees them as unrendered against the `tea_and_murder/`
prefix. The elemental_harmony and space_opera variations are genuinely
unrendered. These are the only authored-asset gaps outside the 7 errored
heavy_metal pickers; every POI landscape and (other than those 7) every portrait
is rendered.

## Known legacy R2 keys (not worlds)

- `genre_packs/victoria/audio/music/` — 6 tracks under the pre-rename pack name
  (`victoria` → `tea_and_murder`, 2026-05). tea_and_murder has **no** music keys
  under its own pack name; if those 6 tracks are still referenced, they ride the
  legacy prefix.
- `genre_packs/caverns_and_claudes/worlds/{caverns_sunden,dungeon_survivor,grimvault,horden,mawdeep}/`
  — 1 stray POI each from retired world experiments; only `beneath_sunden`
  exists in git.
