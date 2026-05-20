# Genre Pack Status Guide

> **Last updated:** 2026-05-19
> **Source:** `sidequest-content` — `genre_packs/` (production) + `genre_workshopping/` (staging)
>
> Two trees. `SIDEQUEST_GENRE_PACKS` always points at `genre_packs/`. The
> `genre_workshopping/` tree is a staging area; the server never loads from it.
> See `sidequest-content/genre_workshopping/README.md` for the promotion gate.

### Reshuffles since 2026-04-30

Four changes since the prior snapshot are load-bearing for reading the tables below:

- **M2 world parking** — `aureate_span` (space_opera), `burning_peace` + `shattered_accord` (elemental_harmony), and `blackthorn_moor` (tea_and_murder) were moved into `genre_workshopping/<pack>/worlds/` pending completeness review (commits `e2356c7`, `6a94881`). Their pack-level YAML and assets remain in production; only the worlds are parked.
- **caverns_and_claudes → procedural megadungeon (ADR-106, closed 2026-05-17).** The prior `caverns_sunden` hamlet world is **deprecated** (content PR #228, commit `67dee9c`). The new live world is `beneath_sunden` — a single shaft into Sünden Deep — and authors only the static surface anchor (Ropefoot waiting-camp + Dropmouth shaft head). The dungeon below is generated unbounded at runtime by the ADR-106 contiguous-edge-expansion engine plus Complication Ledger. The prior five hamlet-nested dungeons (grimvault, mawdeep, primetime, dungeon_survivor, horden) are off the active world list. Four genre-level set-piece tropes (Plan 7 §14.A, content PR #227) anchor the procedural deep.
- **victoria → tea_and_murder rename** (chore commits across all repos, completed 2026-05). The pack and all references rename from `victoria` to `tea_and_murder`.
- **Audio assets moved to R2** (story 45-49, ADR-095). Per-track ACE-Step `*_input_params.json` files remain in the repo as the canonical regeneration spec; OGG playback files now live in R2 (`cdn.slabgorb.com`). The "Audio" column below counts in-repo audio files (mostly params); track counts are higher because each params file generates multiple takes.
- **spaghetti_western promoted to production 2026-05-19.** Full pack (worlds `dust_and_lead` + `the_real_mccoy`) moved from `genre_workshopping/` to `genre_packs/`. Music generation, portraits, and POIs in flight. Server load is blocked by 10 schema-drift fields (`docs/content-drift-triage.md`) — 9 require Python model wiring (`StandoffRules`, `ReputationConfig`, `LuckConfig`, per-tier `ProgressionUnlock`) before the lobby can serve this pack.

## Pack Overview

### Production — `genre_packs/` (loadable by server)

| Genre Pack | Worlds (lobby-selectable) | Genre YAMLs | Audio (in-repo) | Images (in-repo) | Tier | Notes |
|-----------|---------------------------|-------------|-----------------|------------------|------|-------|
| caverns_and_claudes | 1 (**beneath_sunden** — single-shaft procedural megadungeon, ADR-106; surface anchor authored, deep is runtime) | 27 | 24 | 19 | 1 | Reference pack; only pack with portrait images committed locally. The prior `caverns_sunden` hamlet world is deprecated (PR #228) |
| elemental_harmony | **0** (worlds parked in workshopping pending review) | 20 | 121 | LFS-only | 2 | Pack runtime present; no lobby-selectable world. Most ACE-Step params (121); gold-standard variation coverage |
| mutant_wasteland | 1 (flickering_reach — fully spoilable) | 22 | 96 | LFS-only | 1 | Mutation / flickering theme |
| space_opera | 1 (coyote_star — flagship for magic + rig MVP; aureate_span parked) | 22 | 62 | LFS-only | 2 | coyote_star is the Epic 47 flagship; missing archetype/trope coverage |
| tea_and_murder | 1 (`glenross` — Highland village Edwardian Scotland c. 1908; blackthorn_moor parked) | 22 | 1 | LFS-only | 1 | Public-domain classical music served from R2, no ACE-Step params; full world file set |
| **spaghetti_western** ⚠️ | 0 (server load blocked by drift) | 26 | 54 params (OGG in flight) | 16 portraits + 28 POIs in flight | drift-blocked | **Promoted 2026-05-19** from workshopping. Worlds `dust_and_lead` (Mexican border town) + `the_real_mccoy` (1878 industrial Pittsburgh). Server load blocked by 9 wire-required drift fields (standoff, reputation, luck, per-tier unlocks) — see `docs/content-drift-triage.md`. |
| **heavy_metal** ⚠️ | none in production | **0** | 0 | 0 | shell | **State inconsistency:** production directory is an empty shell. Actual content still in `genre_workshopping/heavy_metal/`. |

**Functionally loadable today.** Five packs have pack-level YAML and load cleanly; the lobby world picker shows **4 worlds** (`beneath_sunden`, `flickering_reach`, `coyote_star`, `glenross`). `elemental_harmony` has no lobby-selectable world (both worlds parked). `spaghetti_western` was promoted 2026-05-19 with full content but is server-load-blocked by 9 wire-required schema-drift fields. The `heavy_metal` production directory remains an empty shell.

### Workshopping — `genre_workshopping/` (NOT loaded at runtime)

| Pack | Worlds | Status |
|------|--------|--------|
| elemental_harmony | burning_peace, shattered_accord | **Parked from production 2026-05** (M2 reshuffle). Pack runtime still in production; worlds awaiting completeness review |
| space_opera | aureate_span | **Parked from production 2026-05** (M2). coyote_star remains in production |
| tea_and_murder | blackthorn_moor | **Parked from production 2026-05** (M2). Pack runtime still in production |
| low_fantasy | shattered_reach | Active workshop — gritty medieval; substantive YAML, audio, images |
| neon_dystopia | franchise_nations | Active workshop — cyberpunk |
| pulp_noir | annees_folles | Active workshop — 1930s detective |
| road_warrior | the_circuit | Active workshop — vehicular post-apocalypse |
| heavy_metal | evropi, long_foundry | Full YAML set lives here; production shell exists but is empty |

### Tiers

- **Tier 1** — Genre + world + music + images all present. Playable.
- **Tier 2** — Genre complete, world needs work or assets missing.
- **Tier 3** — Significant gaps in genre or world files.
- **shell** — Production directory exists but is empty; not loadable.

### Pack churn since the port

Four packs that appeared in earlier (Sprint 2-era) audits — `low_fantasy`,
`neon_dystopia`, `pulp_noir`, `road_warrior` — were moved into
`genre_workshopping/` during the port era. They are not removed; they simply
do not meet the production gate yet (full YAML set, generated portraits +
POI landscapes, indexed audio, end-to-end playtest). `heavy_metal` was added
during the port era; promotion is incomplete.

The **2026-05 M2 reshuffle** parked four formerly-production worlds back
into workshopping — `aureate_span`, `burning_peace`, `shattered_accord`, and
`blackthorn_moor`. The pack-level runtime YAML for `elemental_harmony`,
`space_opera`, and `tea_and_murder` remains in production; only their worlds
moved. `caverns_and_claudes` was subsequently restructured again on
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
| tea_and_murder/**glenross** | + | + | + | — | — | + | + |

`beneath_sunden` deliberately authors **only** the surface anchor; the deep
is generated at runtime by the ADR-106 expansion engine. The prior hamlet
world `caverns_sunden` (and its nested grimvault/mawdeep/primetime/
dungeon_survivor/horden dungeons) is deprecated and removed from the
lobby. Old dungeon directories may persist on disk for fixture reference
but are not registered as worlds.

### Parked worlds (workshopping, formerly in production)

| World | history | carto | cultures | archetypes | tropes | visual_style | legends |
|-------|---------|-------|----------|-----------|--------|-------------|---------|
| elemental_harmony/burning_peace | + | + | + | + | + | + | + |
| elemental_harmony/shattered_accord | + | + | + | — | + | — | + |
| space_opera/aureate_span | + | + | + | — | — | — | + |
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
| space_opera | Physique, Reflex, Intellect, Cunning, Resolve, Influence | Ship Block, Ship Combat, Crew Bonds, Found Family | LLM-interpreted |
| tea_and_murder | **Angst, Pride, Humour, Nerve, Cunning, Passion** | Emotional ability scores, class-stratified society | LLM-interpreted |

### Workshop genres (mechanics designed but pack not in production)

| Genre | Custom Stats | Unique Mechanics | Engine Support |
|-------|-------------|-----------------|----------------|
| heavy_metal | per pack.yaml in workshop | per workshop rules.yaml | Pack not loaded |
| low_fantasy | Standard D&D 6 | Banned spells, gritty realism, lingering injuries | LLM-interpreted (workshop only) |
| neon_dystopia | Body, Reflex, Tech, Net, Cool, Edge | Humanity Tracker, Street Cred, Net Combat | LLM-interpreted (workshop only) |
| pulp_noir | Brawn, Finesse, Grit, Savvy, Nerve, Charm | Contacts, Heat Tracker (0-5), Occult Exposure | LLM-interpreted (workshop only) |
| road_warrior | Grip, Iron, Nerve, Scrap, Road Sense, Swagger | Rig HP/damage tiers, Fuel, Chase beats, Dismounted | **Engine GAP** — `chase_depth` was Rust-only and did not port. ADR-087 verdict: **RESTORE P2** (ADR-017). Currently zero engine implementation. |
| spaghetti_western | GRIT, DRAW, NERVE, CUNNING, PRESENCE, LUCK | Standoff system, Luck resource, Bounty board, 5-faction rep | LLM-interpreted (production shell empty) |

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
| *(workshop)* heavy_metal | per workshop YAML | per workshop YAML |
| *(workshop)* low_fantasy | negotiation | — |
| *(workshop)* neon_dystopia | negotiation, net_combat | humanity |
| *(workshop)* pulp_noir | negotiation, interrogation, roulette, craps | heat |
| *(workshop)* road_warrior | negotiation | fuel |
| *(workshop)* spaghetti_western | standoff, negotiation, poker | luck |

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
| Ship Block (separate HP pool) | space_opera | Like Rig HP but for ships | RESTORE P2 (after chase engine pattern lands) |
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

## Music Strategy by Genre (Production + Workshop)

| Genre | Strategy | Track Count | Tree |
|-------|---------|-------------|------|
| elemental_harmony | ACE-Step generated, 2 sets, all 6 variations | 252 | production |
| mutant_wasteland | ACE-Step generated, all 6 variations | 212 | production |
| space_opera | ACE-Step generated | 85 | production |
| caverns_and_claudes | ACE-Step generated (sparse set) | 26 | production |
| **tea_and_murder** | **Curated public-domain classical (Chopin, Strauss)** | 42 | production |
| road_warrior | ACE-Step generated + 10 faction themes | ~147 | workshop |
| low_fantasy | ACE-Step generated, all 6 variations | ~137 | workshop |
| neon_dystopia | ACE-Step generated (needs more) | ~48 | workshop |
| pulp_noir | ACE-Step generated (needs more) | ~42 | workshop |
| spaghetti_western | ACE-Step generating (target: 54) | varies | workshop |
| heavy_metal | ACE-Step in progress | varies | workshop / shell |

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
- **Zero lobby-selectable worlds post-M2.** Pack-level YAML and audio remain in production; both worlds (burning_peace, shattered_accord) are parked in workshopping pending completeness review.
- Musically richest pack — 121 in-repo ACE-Step params (gold standard for variation coverage). OGGs in R2.
- Missing genre-level inventory, voice_presets.
- 9 corpus files covering Asian linguistic traditions.

### mutant_wasteland (production)
- `flickering_reach` (the spoilable world) — recently authored world-level `visual_style.yaml` (content PR #206); still needs history and world archetypes.
- 96 in-repo ACE-Step params (strong); OGGs in R2.

### space_opera (production)
- **One lobby-selectable world** post-M2: `coyote_star` (renamed from coyote_reach 2026-05-01; flagship for Epic 47 magic + rig MVP). `aureate_span` is parked in workshopping.
- Chapter→trope wiring engaged for coyote_star (content PR #209).
- Ship Block mechanic mirrors road_warrior's Rig HP pattern. Both ride on the absent chase engine.
- 62 in-repo ACE-Step params; OGGs in R2.

### tea_and_murder (production — `glenross` live; `blackthorn_moor` parked)
- **One lobby-selectable world:** `glenross` — a fictional Highland village in Edwardian Scotland c. 1908, post-Victorian, pre-Great-War, "the long warm afternoon of empire." No swords, no séances by default, no fist-fights in the kirk yard. Currency is standing, gossip, observation, and a steady noticing eye. River Allt Ross threads through the glen; the kirk on its mound, Castle Ross on the rise above the burn, the distillery smoking faintly. Cover POI: `the_glenross_arms`. Full world file set (history, cartography, cultures, lore, NPCs, openings, portrait manifest, visual style).
- `blackthorn_moor` parked in workshopping pending M2 review — one of the strongest completeness profiles among parked worlds, promotion candidate if you want a second tea_and_murder world.
- **Unique architecture:** emotional ability scores (Angst, Pride, Passion), class-stratified society (Gentry, Trade, Servant, Clergy, Bohemian, Colonial).
- **Public-domain classical music** — Chopin and Strauss recordings mapped to game moods; served from R2. No ACE-Step generation needed (hence near-zero in-repo audio).
- Playfair Display font. 10 class-stratified naming corpus files.
- Extra YAML files unique to tea_and_murder: achievements, beat_vocabulary, power_tiers, magic, classes, equipment_tables.
- The `victoria` → `tea_and_murder` rename completed 2026-05; all references should use the new slug.

### heavy_metal (production shell + workshop)
- **Production state inconsistency.** `genre_packs/heavy_metal/` exists with empty `images/` and `worlds/` only — no `pack.yaml`, no rules. The actual content is in `genre_workshopping/heavy_metal/` with two worlds (evropi, long_foundry) and full YAML set.
- Either complete the promotion or remove the empty production directory; current state is a footgun for the genre loader.

### spaghetti_western (production shell + workshop)
- **Same inconsistency as heavy_metal.** Production directory empty; workshop has dust_and_lead and the_real_mccoy plus 16/16 genre files.
- Standoff system is the signature mechanic — no engine enforcement; awaits Confrontation Engine restoration.

### road_warrior (workshop)
- the_circuit fully developed at world level.
- Was the **most engine-supported genre** pre-port (Rust `chase_depth` implemented Rig HP, fuel, damage tiers, chase beats). **Did not port.** ADR-087 verdict: RESTORE P2.
- 10 faction music themes (Bosozoku through Dekotora) tracked in `audio.yaml`.

### low_fantasy / neon_dystopia / pulp_noir (workshop)
- All have a full primary world but await production promotion (full YAML set + image/audio coverage + playtest).
- Mechanics noted in the table above remain LLM-interpreted; engine restoration deferred to per-genre work after the Confrontation Engine port-drift verdict lands.

## Promotion Checklist

A pack is ready to move from `genre_workshopping/` to `genre_packs/` when:

- All 15 standard genre-level YAML files validate against the loader
- Each declared world has `world.yaml` + `lore.yaml` minimum
- Portrait + POI landscape generation has run; images committed via Git LFS
- Audio set covers at least the 7 core moods (target: full 6-variation set)
- A successful end-to-end playtest run exists in the session archive
- `cd sidequest-server && uv run pytest tests/test_content_audit.py` passes with the pack on path

The two production-shell packs (heavy_metal, spaghetti_western) violate this
gate by being half-promoted. Decide per-pack: complete or roll back.
