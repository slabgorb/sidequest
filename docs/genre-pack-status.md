# Genre Pack Status Guide

> **Last updated:** 2026-06-03 (genre_workshopping tree retired; low_fantasy removed; staging is now per-world `draft: true`)
> **Source:** `sidequest-content` — `genre_packs/` (every pack lives here)
>
> One tree. `SIDEQUEST_GENRE_PACKS` points at `genre_packs/`. There is **no
> separate staging tree** — the `genre_workshopping/` directory was deleted
> 2026-06-03. In-progress worlds live in `genre_packs/` and set `draft: true` in
> `world.yaml` to stay out of lobby selection until their asset gate is met. See
> `sidequest-content/genre_packs/README.md` for the readiness gate.

> **2026-06-03 update — read this first; it supersedes every "workshop" framing below.**
> The `genre_workshopping/` staging tree has been **deleted**, and the
> `low_fantasy` pack with it (retired — not coming back). Staging is now a
> per-world `draft: true` flag inside `genre_packs/`. Treat every
> "genre_workshopping" / "workshop" / "parked in workshopping" mention below as
> historical: the world either lives in `genre_packs/` (sometimes `draft: true`)
> or — in low_fantasy's case — no longer exists at all. The only current draft
> world is `tea_and_murder/blackthorn_moor`.

> **2026-05-28 reconciliation note.** This guide's earlier snapshots described a
> 5-production-pack world. That is stale. As of 2026-05-28 there are **10 pack
> directories in `genre_packs/`**, and a filesystem check (`find
> genre_packs/*/worlds/*/openings.yaml`) confirms **all 10 have at least one
> world with an authored `openings.yaml`**: caverns_and_claudes (beneath_sunden),
> elemental_harmony (burning_peace, shattered_accord), heavy_metal (evropi,
> long_foundry), mutant_wasteland (flickering_reach), neon_dystopia
> (franchise_nations), pulp_noir (annees_folles), road_warrior (the_circuit),
> space_opera (aureate_span, coyote_star), spaghetti_western (dust_and_lead,
> five_points, the_real_mccoy), tea_and_murder (glenross). This matches the root
> `CLAUDE.md` framing: heavy_metal was re-promoted 2026-05-23 (loads clean);
> neon_dystopia + pulp_noir were promoted 2026-05-23 and now have world-tier
> openings authored — but the **asset gate** (portraits, POI landscapes,
> generated OGG) is not yet met for those three. spaghetti_western recently
> gained a third world, `five_points`. The older "production-shell" /
> "parked-in-workshopping" narrative below predates this and is preserved as
> dated history; treat the per-row counts as superseded by this note where they
> conflict.

> **2026-05-29 update (supersedes the 2026-05-28 note and all rows below where
> they conflict).** Verified against a fresh `origin/develop` (commit `c64f5ba`):
>
> - **space_opera now has three live (`draft: false`) worlds**, not one. The
>   per-pack notes and "Parked worlds" table below that still call `aureate_span`
>   "parked in workshopping" are **stale**:
>   - `coyote_star` — live (cover_poi `mendes_post`); SWN ruleset flagship.
>   - `aureate_span` — **promoted out of draft** (`draft: false`, cover_poi
>     `the_calcifiers_chamber`; PRs #290/#291/#292). Camp-cosmic painterly visual
>     redirect; **7 portraits + 21 POI landscapes rendered @40 steps and synced to
>     R2.** No longer parked.
>   - `perseus_cloud` — **new live world** (`draft: false`, cover_poi `new_kowloon`;
>     PRs #286/#288). Authored POI visual prompts, vault NPC import,
>     `aristocratic_reaction` trope. **Absent from every table below** — add it
>     mentally to the space_opera row.
> - **spaghetti_western is fully live with three worlds** (`dust_and_lead`,
>   `the_real_mccoy`, `five_points`). The "Server load blocked by 10 schema-drift
>   fields" line in the *Reshuffles* section below is **superseded** — the pack
>   loads. `five_points` now has **12 distinct POI visual prompts authored and
>   rendered @40** (PR #296) and hero cover_poi `where_rynders_was_stoned` (#297).
> - **`blackthorn_moor` (tea_and_murder) remains `draft: true`** — but its asset
>   gate is now being met: **5 portraits + 8 POIs rendered 2026-05-29**. "Draft"
>   here means *not yet promoted*, not *no assets*. Do not flip `draft: false`
>   without Keith's go — it may be deliberately in-progress.
> - **neon_dystopia gained CWN content** — Cities-Without-Number-derived combat
>   lethality (weapons, armor, HP/AC; PRs #283/#284) and a `net_run` hacking
>   confrontation with a `cwn.hacking` ladder (#287). Its Humanity/Net-Combat
>   mechanics are no longer a pure LLM-interpreted shell; the "workshop only /
>   LLM-interpreted" labels in the mechanics tables below understate this.
> - **Table confrontations collapsed (#294):** spaghetti_western poker and
>   tea_and_murder auction now resolve through a unified free-for-all
>   `table_resolution` path.
>
> The **flagship asset+playtest gate** still distinguishes the fullest worlds;
> with this session's renders, `aureate_span` and `five_points` have closed their
> POI/portrait gaps, and the gap-closing render run also covered
> `tea_and_murder/blackthorn_moor`, `space_opera/coyote_star` (full POI
> re-render), and `heavy_metal/long_foundry` (portraits).

### Reshuffles since 2026-04-30

Four changes since the prior snapshot are load-bearing for reading the tables below:

- **M2 world parking** — `aureate_span` (space_opera), `burning_peace` + `shattered_accord` (elemental_harmony), and `blackthorn_moor` (tea_and_murder) were moved into `genre_workshopping/<pack>/worlds/` pending completeness review (commits `e2356c7`, `6a94881`). Their pack-level YAML and assets remain in production; only the worlds are parked.
- **caverns_and_claudes → procedural megadungeon (ADR-106, closed 2026-05-17).** The prior `caverns_sunden` hamlet world is **deprecated** (content PR #228, commit `67dee9c`). The new live world is `beneath_sunden` — a single shaft into Sünden Deep — and authors only the static surface anchor (Ropefoot waiting-camp + Dropmouth shaft head). The dungeon below is generated unbounded at runtime by the ADR-106 contiguous-edge-expansion engine plus Complication Ledger. The prior five hamlet-nested dungeons (grimvault, mawdeep, primetime, dungeon_survivor, horden) are off the active world list. Four genre-level set-piece tropes (Plan 7 §14.A, content PR #227) anchor the procedural deep.
- **victoria → tea_and_murder rename** (chore commits across all repos, completed 2026-05). The pack and all references rename from `victoria` to `tea_and_murder`.
- **Audio assets moved to R2** (story 45-49, ADR-095). Per-track ACE-Step `*_input_params.json` files remain in the repo as the canonical regeneration spec; OGG playback files now live in R2 (`cdn.slabgorb.com`). The "Audio" column below counts in-repo audio files (mostly params); track counts are higher because each params file generates multiple takes.
- **spaghetti_western promoted to production 2026-05-19.** Full pack (worlds `dust_and_lead` + `the_real_mccoy`) moved from `genre_workshopping/` to `genre_packs/`. Music generation, portraits, and POIs in flight. ~~Server load is blocked by 10 schema-drift fields~~ — **superseded (2026-05-29):** the pack loads, now with a third world `five_points` (12 POI prompts authored + rendered, #296/#297). Any remaining `StandoffRules`/`ReputationConfig`/`LuckConfig`/`ProgressionUnlock` work is engine-enforcement debt, **not** a load blocker (see `docs/content-drift-triage.md`).

## Pack Overview

### Production — `genre_packs/` (10 pack dirs; all have world openings as of 2026-05-28)

> Counts/tiers in the original (2026-05-19) snapshot below are preserved where
> still accurate. The **Worlds (filesystem)** column was refreshed 2026-05-28
> against `find genre_packs/*/worlds/*/openings.yaml` and supersedes the stale
> 2026-05-19 "Worlds (lobby-selectable)" claims for elemental_harmony,
> heavy_metal, spaghetti_western, and the three newly-promoted packs.

| Genre Pack | Worlds (filesystem, with openings.yaml) | Genre YAMLs | Audio (in-repo) | Images (in-repo) | Tier | Notes |
|-----------|------------------------------------------|-------------|-----------------|------------------|------|-------|
| caverns_and_claudes | 1 (**beneath_sunden** — single-shaft procedural megadungeon, ADR-106; surface anchor authored, deep is runtime) | 27 | 24 | 19 | 1 | Reference pack; only pack with portrait images committed locally. The prior `caverns_sunden` hamlet world is deprecated (PR #228) |
| elemental_harmony | 2 (**burning_peace**, **shattered_accord** — both have openings.yaml in genre_packs as of 2026-05-28; *2026-05 "parked" note below is stale*) | 20 | 121 | LFS-only | 2 | Most ACE-Step params (121); gold-standard variation coverage |
| mutant_wasteland | 1 (flickering_reach — fully spoilable) | 22 | 96 | LFS-only | 1 | Mutation / flickering theme |
| space_opera | 2 (**coyote_star** — Epic 47 magic+rig flagship, now **SWN ruleset** for combat; **aureate_span** also has openings.yaml as of 2026-05-28) | 22 | 62 | LFS-only | 2 | coyote_star binds `ruleset: swn` (combat live, e2e green 2026-05-27); see Per-Pack Notes for caveats |
| tea_and_murder | 1 (`glenross` — Highland village Edwardian Scotland c. 1908; blackthorn_moor still workshop-parked) | 22 | 1 | LFS-only | 1 | Public-domain classical music served from R2, no ACE-Step params; full world file set |
| spaghetti_western | 3 (**dust_and_lead** — Mexican border town; **the_real_mccoy** — 1878 industrial Pittsburgh; **five_points** — new world) | 26 | 54 params (OGG in flight) | 16 portraits + 28 POIs in flight | 2 | **Promoted 2026-05-19**; new `five_points` world added since. Earlier "drift-blocked / 0 worlds" status is superseded — all three worlds have openings.yaml. If standoff/reputation/luck engine wiring is still owed, that is an engine-enforcement gap, not a load blocker (see `docs/content-drift-triage.md`) |
| heavy_metal | 2 (**evropi**, **long_foundry**) | — | varies | gate pending | 2 | **Re-promoted 2026-05-23** (loads clean per root CLAUDE.md). Earlier "empty shell" status is superseded. Asset gate (portraits, POIs, OGG) not yet met |
| neon_dystopia | 1 (**franchise_nations**) | — | ~48 | gate pending | 3 | **Promoted 2026-05-23**; world-tier openings.yaml now authored. Asset gate (portraits, POIs, OGG) not yet met |
| pulp_noir | 1 (**annees_folles**) | — | ~42 | gate pending | 3 | **Promoted 2026-05-23**; world-tier openings.yaml now authored. Asset gate (portraits, POIs, OGG) not yet met |
| road_warrior | 1 (**the_circuit**) | — | ~147 | gate pending | 3 | In `genre_packs/` with world openings. Engine GAP: `chase_depth` (Rig HP, fuel, damage tiers) was Rust-only and did not port — ADR-087 RESTORE P2 |

**Filesystem reality (verified 2026-05-28).** All **10** pack directories in
`genre_packs/` have at least one world with an authored `openings.yaml`. The
fullest production worlds remain `beneath_sunden`, `flickering_reach`,
`coyote_star`, and `glenross` (tier-1/2 with assets); heavy_metal,
neon_dystopia, pulp_noir, and road_warrior load but have not cleared the asset
gate (portraits / POI landscapes / generated OGG — see each pack's README).
spaghetti_western has three worlds with openings. The **distinction that still
matters** is no longer "directory exists vs empty shell" — it is **"loads with
world openings" (all 10) vs "cleared the full asset + playtest promotion gate"
(the 4 flagship worlds)**.

### Draft & retired worlds (historical — was "Workshopping / `genre_workshopping/`")

> **2026-06-03.** The `genre_workshopping/` tree is gone, and `low_fantasy` (its
> last resident) was deleted. The only world still gated is
> `tea_and_murder/blackthorn_moor` — now via `draft: true` inside `genre_packs/`,
> not a separate tree. The rows below are retained as M2-era history.

| Pack | Worlds | Status |
|------|--------|--------|
| ~~low_fantasy~~ | ~~shattered_reach~~ | **Deleted 2026-06-03** — pack retired along with the `genre_workshopping/` tree; no longer exists |
| tea_and_murder | blackthorn_moor | **Draft** (`draft: true` in `genre_packs/`) — pack runtime live; this world not yet lobby-promoted. `glenross` is the live tea_and_murder world |
| ~~elemental_harmony~~ | ~~burning_peace, shattered_accord~~ | **Moved to `genre_packs/`** — both worlds now have openings.yaml (was: parked 2026-05 M2) |
| ~~space_opera~~ | ~~aureate_span~~ | **Moved to `genre_packs/`** — aureate_span now has openings.yaml (was: parked 2026-05 M2) |
| ~~neon_dystopia~~ | ~~franchise_nations~~ | **Promoted to `genre_packs/` 2026-05-23** (asset gate pending) |
| ~~pulp_noir~~ | ~~annees_folles~~ | **Promoted to `genre_packs/` 2026-05-23** (asset gate pending) |
| ~~road_warrior~~ | ~~the_circuit~~ | **Moved to `genre_packs/`** — the_circuit has openings.yaml (chase engine still unported) |
| ~~heavy_metal~~ | ~~evropi, long_foundry~~ | **Re-promoted to `genre_packs/` 2026-05-23** (loads clean; asset gate pending) |

### Tiers

- **Tier 1** — Genre + world + music + images all present. Playable.
- **Tier 2** — Genre complete, world needs work or assets missing.
- **Tier 3** — Significant gaps in genre or world files.
- **shell** — Production directory exists but is empty; not loadable.

### Pack churn since the port

During the port era, four packs — `low_fantasy`, `neon_dystopia`, `pulp_noir`,
`road_warrior` — were moved into `genre_workshopping/`, and `heavy_metal` was
added there. **That has since fully unwound:** `neon_dystopia`, `pulp_noir`,
`road_warrior`, and `heavy_metal` returned to `genre_packs/` (2026-05-23) with
authored world `openings.yaml`, and `low_fantasy` was **deleted outright
2026-06-03** (retired — not coming back). The `genre_workshopping/` tree is now
empty and gone. The four returned packs still owe the **asset gate** (generated
portraits + POI landscapes + OGG) and an end-to-end playtest before they reach
flagship tier, but they load.

The **2026-05 M2 reshuffle** had parked four formerly-production worlds into
workshopping — `aureate_span`, `burning_peace`, `shattered_accord`, and
`blackthorn_moor`. **As of 2026-05-28 the first three are back in
`genre_packs/`** with `openings.yaml` (only `blackthorn_moor` remains parked).
The pack-level runtime YAML for `elemental_harmony`, `space_opera`, and
`tea_and_murder` was always in production. `caverns_and_claudes` was subsequently restructured again on
2026-05-17 by **ADR-106**: the briefly-consolidated `caverns_sunden` hamlet
(commit `fe09971`) was deprecated (PR #228) in favor of `beneath_sunden`,
a single-shaft procedural-megadungeon world whose deep is runtime-generated.

## Genre-Level File Coverage (Production)

Standard set: `pack`, `rules`, `axes`, `lore`, `cultures`, `archetypes`,
`char_creation`, `progression`, `inventory`, `tropes`, `prompts`,
`voice_presets`, `theme`, `visual_style`, `audio`. Recently introduced:
`lethality_policy`, `power_tiers`, `beat_vocabulary`, `archetype_constraints`,
`projection`, `visibility_baseline`. The historical `cartography` genre
file is no longer required as a runtime asset for the live world-map view
(removed 2026-04-28; ADR-019 superseded). World-level `cartography.yaml`
still seeds `snap.current_region` at chargen as a `CartographyConfig`.

| Pack | Notes on coverage |
|------|-------------------|
| caverns_and_claudes | 25 yamls — fullest set; includes voice_presets |
| elemental_harmony | 21 yamls — missing voice_presets, inventory |
| mutant_wasteland | 23 yamls — missing voice_presets |
| space_opera | 23 yamls — missing voice_presets |
| tea_and_murder | 23 yamls — full standard set + emotional axes additions |

## World-Level Completeness

Required: `world.yaml`, `lore.yaml`. Optional: `history`, `cartography`,
`cultures`, `archetypes`, `tropes`, `visual_style`, `legends`.

### Production worlds (lobby-selectable)

| World | history | carto | cultures | archetypes | tropes | visual_style | legends |
|-------|---------|-------|----------|-----------|--------|-------------|---------|
| caverns_and_claudes/**beneath_sunden** | + | + (surface only — Ropefoot + Dropmouth) | + | + | + (4 set-piece, anchor the procedural deep) | + | + |
| mutant_wasteland/flickering_reach | — | + | + | — | — | + | + |
| space_opera/coyote_star | + | + | + | — | — | — | + |
| space_opera/**aureate_span** (now live, `draft: false` — #290/#291/#292) | + | + | + | — | + (5, #290) | + (#290) | + |
| space_opera/**perseus_cloud** (now live, `draft: false` — #286/#288) | + | + | + | — | — | + | — |
| tea_and_murder/**glenross** | + | + | + | — | — | + | + |

`beneath_sunden` deliberately authors **only** the surface anchor; the deep
is generated at runtime by the ADR-106 expansion engine. The prior hamlet
world `caverns_sunden` (and its nested grimvault/mawdeep/primetime/
dungeon_survivor/horden dungeons) is deprecated and removed from the
lobby. Old dungeon directories may persist on disk for fixture reference
but are not registered as worlds.

### Draft / formerly-parked worlds (historical)

| World | history | carto | cultures | archetypes | tropes | visual_style | legends |
|-------|---------|-------|----------|-----------|--------|-------------|---------|
| elemental_harmony/burning_peace | + | + | + | + | + | + | + |
| elemental_harmony/shattered_accord | + | + | + | — | + | — | + |
| ~~space_opera/aureate_span~~ | | | | | | | **Promoted 2026-05-29 — now live (`draft: false`); see Production worlds table above** |
| tea_and_murder/blackthorn_moor | + | + | + | + | + | + | + |

**Promotion candidates:** `burning_peace` and `blackthorn_moor` have full
optional file sets — they are gated only on the M2 review, not on missing
content. `blackthorn_moor` would give `tea_and_murder` a second selectable
world alongside the live `glenross`.

## Unique Genre Mechanics

Each genre defines custom mechanics in `rules.yaml`. The engine provides
generic subsystems (combat, chase shell, tropes, factions); genre-specific
rules are LLM-interpreted at narration time unless noted.

| Genre | Custom Stats | Unique Mechanics | Engine Support |
|-------|-------------|-----------------|----------------|
| caverns_and_claudes | Standard fantasy 6 | Dungeon crawl, room graph navigation, **procedural megadungeon (ADR-106)** | Room graph engine (`game/room_movement.py`, ADR-055) + Sünden Deep expansion engine + Complication Ledger (ADR-106, closed 2026-05-17) |
| elemental_harmony | Harmony, Spirit + 4 | High magic, martial arts | LLM-interpreted |
| mutant_wasteland | Brawn, Reflexes, Toughness, Wits, Instinct, Presence | Mutation system, no magic | LLM-interpreted |
| space_opera | Physique, Reflex, Intellect, Cunning, Resolve, Influence (SWN-mapped: Physique→STR, Resolve→CON, Reflex→DEX, Intellect→INT, Cunning→WIS, Influence→CHA; SWN modifier curve) | **SWN ruleset** (`ruleset: swn`): ablative HP (HpPool current/max/base_max), Firefight + Ship Combat both resolve d20 + attack_bonus + combat_skill + attr_mod vs Armor Class → damage ablates HP, 0 HP = `hp_depletion` victory. Crew Bonds (advantage on bond-protect actions), Found Family | **SWN engine for combat** (personal + ship; hull = HP, ship AC 14, flat armor soak). Caveats: SWN skill checks (2d6), saves, initiative (1d8) coded in the `swn` module but **not yet routed from the orchestrator**; chargen has no per-class HP tables yet (defaults to 10 HP); non-combat confrontations (negotiation, pursuit, dogfight) still use native dial rules |
| tea_and_murder | **Angst, Pride, Humour, Nerve, Cunning, Passion** | Emotional ability scores, class-stratified society | LLM-interpreted |

### Non-flagship genres (in production, asset/engine gaps)

> **2026-06-03:** this table was once titled "Workshop genres (... not in
> production)." Every pack listed loads from `genre_packs/`; they just haven't
> cleared the full asset + playtest (and in some cases engine-enforcement) gate.
> (`low_fantasy`, formerly the lone workshop holdout, was deleted 2026-06-03.)

| Genre | Custom Stats | Unique Mechanics | Engine Support |
|-------|-------------|-----------------|----------------|
| heavy_metal | per pack.yaml | per `rules.yaml` | In production (loads); asset gate pending |
| neon_dystopia | Body, Reflex, Tech, Net, Cool, Edge | Humanity Tracker, Street Cred, Net Combat | **CWN content live** — combat lethality (weapons/armor/HP/AC, #283/#284) + `net_run` hacking confrontation with `cwn.hacking` ladder (#287); Humanity/Street Cred still LLM-interpreted |
| pulp_noir | Brawn, Finesse, Grit, Savvy, Nerve, Charm | Contacts, Heat Tracker (0-5), Occult Exposure | In production (loads); LLM-interpreted; asset gate pending |
| road_warrior | Grip, Iron, Nerve, Scrap, Road Sense, Swagger | Rig HP/damage tiers, Fuel, Chase beats, Dismounted | **Engine GAP** — `chase_depth` was Rust-only and did not port. ADR-087 verdict: **RESTORE P2** (ADR-017). Currently zero engine implementation. |
| spaghetti_western | GRIT, DRAW, NERVE, CUNNING, PRESENCE, LUCK | Standoff system, Luck resource, Bounty board, 5-faction rep | In production (3 worlds load); standoff/luck engine enforcement still owed |

## Confrontation & Resource Coverage

The Confrontation Engine (Epic 16/28, ADR-033) declared genre-typed
confrontation variants and resource pools. **Port-drift status (ADR-082 →
ADR-087):** `game/resource_pool.py` ported cleanly; the broader Confrontation
Engine is **VERIFY → likely RESTORE (P0)** per ADR-087 — Epic 28 was the
largest body of work immediately before port cutover and the audit did not
verify per-story landing. Restoration scheduling lives in ADR-087.

| Genre Pack | Declared Confrontation Types | Declared Resources |
|-----------|-------------------------------|---------------------|
| caverns_and_claudes | negotiation | — |
| elemental_harmony | negotiation | — |
| mutant_wasteland | negotiation | — |
| space_opera | negotiation, ship_combat | — |
| tea_and_murder | negotiation, trial, auction | standing |
| heavy_metal | per `rules.yaml` | per `rules.yaml` |
| neon_dystopia | negotiation, net_combat | humanity |
| pulp_noir | negotiation, interrogation, roulette, craps | heat |
| road_warrior | negotiation | fuel |
| spaghetti_western | standoff, negotiation, poker | luck |

**Validation:** `cd sidequest-server && uv run pytest tests/test_content_audit.py`
verifies all loadable packs parse, confrontation structure, beat/ability score
consistency, and resource range validity. (Was `cargo test` pre-port; see
ADR-082.)

## Content vs Engine Gap Map

Features defined in content YAML that have no engine-level enforcement.
These work via LLM prompt interpretation — the narrator reads `rules.yaml`
and applies them narratively. Risk: LLM may forget or drift mid-session.

### Gaps where engine COULD enforce but doesn't

| Feature | Content Pack | Why It Matters | ADR-087 Verdict |
|---------|-------------|---------------|------------------|
| Standoff state machine | spaghetti_western (workshop) | Pre-combat NERVE check ritual with no mechanical guardrail | Bundled into Confrontation Engine restoration |
| Luck resource pool | spaghetti_western (workshop) | Spendable resource with no engine tracking | Confrontation Engine restoration |
| Humanity Tracker | neon_dystopia (workshop) | Degrades at thresholds (50/25/0) — engine could enforce | Confrontation Engine restoration |
| Heat Tracker | pulp_noir (workshop) | 0-5 scale affecting faction behavior | Confrontation Engine restoration |
| ~~Ship Block (separate HP pool)~~ — superseded | space_opera | Ship Combat now resolves on the **SWN engine** (hull = ablative HP, AC 14, flat armor soak, `hp_depletion` victory) rather than an LLM-interpreted separate pool. The old "Ship Block" RESTORE-P2 item is closed for combat. Non-combat ship maneuvers (pursuit, dogfight) still use native dials | **Closed for combat** (SWN, e2e green 2026-05-27) |
| Rig HP / damage tiers / Fuel | road_warrior (workshop) | All `chase_depth` mechanics | **RESTORE P2** per ADR-087 (ADR-017 still accepted) |

### Gaps where engine has data but UI doesn't show

| Feature | Engine Module (Python) | What UI Needs |
|---------|------------------------|---------------|
| Confrontation momentum | `game/encounter.py`, `game/resource_pool.py` | ConfrontationOverlay reads via state mirror (story 45-3 done) |

The pre-port `chase_depth.rs` (RigStats, fuel, fuel_warning) and `chase.rs`
(ChaseState) modules **did not port**. There is no `chase_depth.py` or
`chase.py` in `sidequest-server/sidequest/game/`. `encounter.py` carries
string references to chase concepts only.

## MusicDirector Mood Coverage

The engine uses string-keyed `MoodKey` rather than a hardcoded enum (story
16-14, ported intact). Genre packs declare `mood_aliases` in `audio.yaml` to
map custom mood strings to core moods or mood tracks. 7 core moods remain
as constants; any string is valid as a mood key.

| Core Mood | Constant |
|----------|---------|
| combat | `MoodKey.COMBAT` |
| exploration | `MoodKey.EXPLORATION` |
| tension | `MoodKey.TENSION` |
| triumph | `MoodKey.TRIUMPH` |
| sorrow | `MoodKey.SORROW` |
| mystery | `MoodKey.MYSTERY` |
| calm | `MoodKey.CALM` |

**Custom moods** resolve through `mood_aliases` chain or direct track lookup.
Genre packs can declare any mood string and map it to tracks or core moods.

## Music Strategy by Genre

> "Tree" is now always `genre_packs/` — the workshop tree is gone. The column
> below reads **asset gate met** (music coverage adequate for flagship play) vs
> **gate pending** (generation still owed).

| Genre | Strategy | Track Count | Asset gate |
|-------|---------|-------------|------------|
| elemental_harmony | ACE-Step generated, 2 sets, all 6 variations | 252 | met |
| mutant_wasteland | ACE-Step generated, all 6 variations | 212 | met |
| space_opera | ACE-Step generated | 85 | met |
| caverns_and_claudes | ACE-Step generated (sparse set) | 26 | met |
| **tea_and_murder** | **Curated public-domain classical (Chopin, Strauss)** | 42 | met |
| road_warrior | ACE-Step generated + 10 faction themes | ~147 | pending |
| neon_dystopia | ACE-Step generated (needs more) | ~48 | pending |
| pulp_noir | ACE-Step generated (needs more) | ~42 | pending |
| spaghetti_western | ACE-Step generating (target: 54) | varies | pending |
| heavy_metal | ACE-Step in progress | varies | pending |

## Per-Pack Notes

### caverns_and_claudes (production)
- **One lobby-selectable world** post-ADR-106: `beneath_sunden` — a single shaft into Sünden Deep. **Procedural megadungeon** pack as of 2026-05-17. The world manifest authors only the surface anchor (`ropefoot` waiting-camp + `the_dropmouth` shaft head); the deep is generated unbounded at runtime by the contiguous-edge-expansion engine (Python port of the maze-maker family) plus the Complication Ledger. Genre truth — grave, lethal, Moria-as-tragedy, gravity ≥ 0.85, no winking — is fixed by `world_register.yaml`.
- The prior `caverns_sunden` hamlet world is **deprecated** (content PR #228); its nested grimvault/mawdeep/primetime/dungeon_survivor/horden dungeons are off the active world list.
- Four genre-level set-piece tropes (Plan 7 §14.A, content PR #227) anchor the procedural deep — the expansion engine threads them rather than improvising every encounter.
- The `claude -p` "curate" stage is the only LLM call in the megadungeon expansion loop (everything else moved to the Anthropic SDK with ADR-101).
- Sparse music (24 in-repo params, OGGs in R2) — candidate for next ACE-Step pass.
- Reference pack for shape and conventions; ships the four classic C&C B/X classes (fighter / mage / cleric / thief), B26 saving throws, learned_v1 memorization, morale, and class signature abilities (Taunt / Turn Undead / Backstab).
- Room graph wired in Python (`game/room_movement.py`, ADR-055) — paired with the ADR-106 expansion engine on the runtime path.

### elemental_harmony (production runtime, worlds parked)
- **Two worlds back in `genre_packs/` with openings.yaml** (`burning_peace`, `shattered_accord`) as of the 2026-05-28 reconciliation — the earlier "zero worlds / parked in workshopping post-M2" status is **stale**. Pack-level YAML and audio were always in production. Asset + playtest gate status still varies per world.
- Musically richest pack — 121 in-repo ACE-Step params (gold standard for variation coverage). OGGs in R2.
- Missing genre-level inventory, voice_presets.
- 9 corpus files covering Asian linguistic traditions.

### mutant_wasteland (production)
- `flickering_reach` (the spoilable world) — recently authored world-level `visual_style.yaml` (content PR #206); still needs history and world archetypes.
- 96 in-repo ACE-Step params (strong); OGGs in R2.

### space_opera (production)
- **Three live (`draft: false`) worlds** as of 2026-05-29 (the earlier "one world / aureate_span parked" status is **stale**):
  - `coyote_star` (renamed from coyote_reach 2026-05-01; flagship for Epic 47 magic + rig MVP; binds SWN — see below).
  - `aureate_span` — promoted out of draft 2026-05-29 (#290/#291/#292), camp-cosmic painterly redirect, 7 portraits + 21 POIs rendered and synced to R2; cover_poi `the_calcifiers_chamber`.
  - `perseus_cloud` — live (#286/#288); authored POI prompts, vault NPC import, `aristocratic_reaction` trope; cover_poi `new_kowloon`.
- Chapter→trope wiring engaged for coyote_star (content PR #209).
- **Now binds the SWN (Stars Without Number) ruleset** (`ruleset: swn` in `rules.yaml`; e2e tests green 2026-05-27). The six native attributes survive but are SWN-mapped (Physique→STR, Resolve→CON, Reflex→DEX, Intellect→INT, Cunning→WIS, Influence→CHA) and use the SWN modifier curve. Combat — **both personal (Firefight) and Ship Combat** — resolves d20 + attack_bonus + combat_skill + attr_mod vs Armor Class; damage ablates first-class HP (HpPool current/max/base_max), 0 HP = `hp_depletion` victory. Ship hull is the HP pool (ship AC 14, flat `armor` soak). `stat_display_fields` exposes hp/max_hp/armor to players.
  - **Honest caveats:** (a) SWN skill checks (2d6+skill+attr), the 3-category saves, and 1d8+DEX initiative are coded in the `swn` module but **not yet routed from the narrator orchestrator** (deferred). (b) Chargen does not yet author per-class HP tables (`base_max_by_class`), so characters currently default to **10 HP**. (c) Non-combat confrontations (negotiation, pursuit, dogfight) still use the **native dial rules**, not SWN resolution.
  - Note: the descriptive `custom_rules.ship_combat` prose in `rules.yaml` ("Ships don't have HP") predates the SWN wiring; the live combat path is the `confrontations` block, where ship_combat resolves via attack-vs-AC + `hp_depletion`.
- 62 in-repo ACE-Step params; OGGs in R2.

### tea_and_murder (production — `glenross` live; `blackthorn_moor` parked)
- **One lobby-selectable world:** `glenross` — a fictional Highland village in Edwardian Scotland c. 1908, post-Victorian, pre-Great-War, "the long warm afternoon of empire." No swords, no séances by default, no fist-fights in the kirk yard. Currency is standing, gossip, observation, and a steady noticing eye. River Allt Ross threads through the glen; the kirk on its mound, Castle Ross on the rise above the burn, the distillery smoking faintly. Cover POI: `the_glenross_arms`. Full world file set (history, cartography, cultures, lore, NPCs, openings, portrait manifest, visual style).
- `blackthorn_moor` remains `draft: true` (in `genre_packs/`, not lobby-promoted) — one of the strongest completeness profiles, a promotion candidate for a second tea_and_murder world. **Asset gate now being met (2026-05-29): 5 portraits + 8 POIs rendered.** Do not flip `draft: false` without Keith's go — may be deliberately in-progress.
- **Unique architecture:** emotional ability scores (Angst, Pride, Passion), class-stratified society (Gentry, Trade, Servant, Clergy, Bohemian, Colonial).
- **Public-domain classical music** — Chopin and Strauss recordings mapped to game moods; served from R2. No ACE-Step generation needed (hence near-zero in-repo audio).
- Playfair Display font. 10 class-stratified naming corpus files.
- Extra YAML files unique to tea_and_murder: achievements, beat_vocabulary, power_tiers, magic, classes, equipment_tables.
- The `victoria` → `tea_and_murder` rename completed 2026-05; all references should use the new slug.

### heavy_metal (production — re-promoted 2026-05-23)
- **Re-promoted to `genre_packs/` 2026-05-23** (per root CLAUDE.md: loads clean). Two worlds, **evropi** and **long_foundry**, both with `openings.yaml`. The earlier "empty production shell" state is resolved.
- **Asset gate not yet met** — portraits, POI landscapes, and generated OGG still owed before this counts as a flagship-tier playable world.
- Push-currency / pact_working magic references live here.

### spaghetti_western (production — promoted 2026-05-19, +five_points since)
- **Three worlds with openings.yaml:** `dust_and_lead` (Mexican border town), `the_real_mccoy` (1878 industrial Pittsburgh), and the newer `five_points`. The earlier "production shell / drift-blocked / 0 worlds" status is superseded.
- Standoff system + Luck resource are the signature mechanics — engine enforcement is still owed (Confrontation Engine restoration); that is an enforcement gap, not a load blocker.

### road_warrior (production — has world openings; chase engine unported)
- In `genre_packs/` with `the_circuit` world openings authored.
- Was the **most engine-supported genre** pre-port (Rust `chase_depth` implemented Rig HP, fuel, damage tiers, chase beats). **Did not port.** ADR-087 verdict: RESTORE P2.
- 10 faction music themes (Bosozoku through Dekotora) tracked in `audio.yaml`. Asset gate still pending.

### neon_dystopia / pulp_noir (production — promoted 2026-05-23, asset gate pending)
- Both promoted to `genre_packs/` 2026-05-23; world-tier `openings.yaml` now authored (`franchise_nations` and `annees_folles` respectively), so both load.
- **Asset gate not yet met** (portraits, POI landscapes, generated OGG) — not yet flagship-playable.
- Genre mechanics (Humanity/Net Combat; Heat/Occult) remain LLM-interpreted pending Confrontation Engine restoration.

### low_fantasy (removed 2026-06-03)
- **Retired and deleted** along with the `genre_workshopping/` tree. The
  `shattered_reach` world and all pack YAML / audio params / image specs are
  gone from the repo. Not returning.

## Readiness Checklist

A draft world is ready to clear `draft: true` (become lobby-selectable) when:

- All standard genre-level YAML files validate against the loader
- Each declared world has `world.yaml` + `lore.yaml` minimum
- Portrait + POI landscape generation has run and synced to R2
- Audio set covers at least the 7 core moods (target: full 6-variation set)
- A successful end-to-end playtest run exists in the session archive
- `cd sidequest-server && uv run pytest tests/test_content_audit.py` passes with the pack on path

As of 2026-05-28 the "empty production shell" problem is gone — all 10 packs in
`genre_packs/` load with world openings. The remaining promotion work is the
**asset + playtest gate** (portraits, POI landscapes, generated OGG, e2e run)
for heavy_metal, neon_dystopia, pulp_noir, and road_warrior, plus the
engine-enforcement debt (standoff/luck for spaghetti_western; chase engine for
road_warrior). These are completeness gaps, not load blockers.
