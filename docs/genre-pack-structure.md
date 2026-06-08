# Genre Pack Filesystem Structure

> Authoritative reference for how genre packs are laid out on disk. Audience:
> content authors (Jade, Keith, future table members) **and** devs. Everything
> here is grounded in the live repo (`sidequest-content/genre_packs/`) and the
> server loader (`sidequest-server/sidequest/genre/loader.py`) as of 2026-06-08.
> Where the loader and the scaffold/audit schema disagree on "required", this doc
> calls it out explicitly.

## The core idea: genre = rulebook, world = setting

A **genre pack** is the *rulebook*: resolution rules, progression math,
tone/voice axes, narrator voice, lethality and visibility policy, and the
theme/audio "chrome." A **world** is a *campaign setting* that the rulebook is
played in: the cast (NPCs, cultures, creatures), the catalog (items, rigs,
classes/callings), the geography (cartography, orbits), and the world's lore,
tropes, openings, and visual prompts. **A single genre hosts many worlds** —
`space_opera` hosts `aureate_span`, `coyote_star`, and `perseus_cloud`; they
share one rulebook but own completely different casts and maps.

This boundary is **ADR-140** ("Genre Is the Rulebook Only; the World Owns the
Cast and Catalog," supersedes ADR-120) and **ADR-121** (layered content
resolution). It was enforced through Epic 74 and Epic 94, which moved cast/catalog
flavor (archetypes, tropes, char_creation, inventory, lore, classes, bestiary,
seed-tropes, spell catalogs) down to the world tier. See
[Genre-vs-world boundary](#genre-vs-world-boundary--layered-resolution) below.

Packs are discovered by the server's `GenreLoader` along a search-path list
(`DEFAULT_GENRE_PACK_SEARCH_PATHS`), the first of which is
`<orchestrator-root>/sidequest-content/genre_packs/`. The
`SIDEQUEST_GENRE_PACKS` environment variable is the canonical pointer at the
packs directory used by the asset-URL layer and the daemon (see ADR-003 / ADR-004
for lazy genre binding). A pack is a directory; its directory name is the
**genre code** (e.g. `space_opera`).

## Two contracts: "loads" vs "well-formed"

There are **two** different bars a pack/world can be measured against, and they
are not the same:

1. **Loader hard-requirements** — the minimal set of files the runtime loader
   (`load_genre_pack`) *must* read or it raises `GenreLoadError` and the pack
   refuses to load. This is the "will it boot" bar.
2. **Scaffold / audit contract** — `sidequest-content/pack_schema.yaml`, the
   machine-readable template the pack validator (`sidequest validate`) and the
   `sq-audit` tooling enforce for a *complete, well-formed* pack. This is the
   "is it production-ready" bar, and it is stricter (it requires asset dirs,
   `client_theme.css`, `theme.yaml`, etc. that the loader tolerates as absent).

The annotated trees below show the **full, well-formed** layout. The
[Minimum viable pack / world](#minimum-viable-pack-and-world) section at the end
gives the much smaller **loader hard-requirement** set.

> **Media is NOT in the repo.** Rendered images (PNG) and audio (OGG) are
> canonical in **R2**, indexed by `sidequest-content/r2_manifest.json`. The repo
> holds only the *specs* that regenerate them (prompts, manifests,
> `*_input_params.json`). See [Media: repo holds specs, R2 holds renders](#media-repo-holds-specs-r2-holds-renders).

---

## Pack-level layout (annotated)

This is the layout at the **root** of a genre pack directory
(`genre_packs/<pack>/`). Modeled on `space_opera` and `caverns_and_claudes`,
both live. `[req]` = loader hard-requirement, `[req*]` = required by the
audit/scaffold contract but tolerated-absent by the loader, `[opt]` = optional,
`[ext]` = extension (only present for packs that use the feature).

```text
genre_packs/<pack>/
├── pack.yaml                    # [req]  Pack manifest: name, version, description,
│                                #        lobby_blurb, recommended_players, inspirations,
│                                #        core_vibe, emotional_tone, extensions[]. THE manifest
│                                #        the loader keys on (PackMeta).
├── rules.yaml                   # [req]  THE RULEBOOK. ruleset: binding (native/swn/wwn/cwn),
│                                #        confrontations, beats, allowed_classes, resolution dials.
│                                #        Confrontation interaction_table can use _from: pointers
│                                #        to sibling files (e.g. dogfight/interactions_mvp.yaml).
├── progression.yaml             # [req]  Advancement / progression math (ADR-021).
├── axes.yaml                    # [req]  Tone/voice axes (narrative<->mechanical, verbosity, etc).
├── prompts.yaml                 # [req]  Narrator prompt scaffolding for the genre.
├── visibility_baseline.yaml     # [req]  Perception/visibility defaults; read at session init.
├── lethality_policy.yaml        # [req]  LethalityArbiter policy; read every turn.
│
├── theme.yaml                   # [req*] Genre theme chrome (colors/tone). World theme.yaml
│                                #        overrides; a world with no theme falls back to this.
├── audio.yaml                   # [req*] Genre audio config (mood_tracks, sfx_library, themes).
│                                #        Paths are pack-relative and rewritten to R2 URLs at load.
├── client_theme.css             # [req*] ADR-079 genre CSS theme served to the UI at connect.
├── visual_style.yaml            # [opt]  Z-Image prompt style (ADR-086). As of 2026-05-29 visual
│                                #        prompts live at WORLD level; pack-level is optional.
│
├── archetypes.yaml              # [opt]  Genre-tier NPC archetype defaults (CAST → world-authoritative).
├── tropes.yaml                  # [opt]  Genre-tier trope inheritance BASE (CAST → world-authoritative).
├── cultures.yaml                # [opt]  Genre-tier cultures (single-file form; CAST → world-authoritative).
├── char_creation.yaml           # [opt]  Genre-tier chargen scenes (CATALOG → world-authoritative).
│                                #        A world's char_creation REPLACES this wholesale (no merge).
├── inventory.yaml               # [opt]  Genre-tier inventory config (CATALOG → world-authoritative).
├── power_tiers.yaml             # [opt]  Power-tier ladder (ADR taxonomy).
├── classes.yaml                 # [ext]  Class definitions (caverns_and_claudes, space_opera).
├── magic.yaml                   # [ext]  Genre magic system. WORLD magic.yaml composes over it;
│                                #        BOTH genre+world files must exist for magic to load.
├── projection.yaml              # [ext]  Projection rules (validated at load if present).
├── beat_vocabulary.yaml         # [ext]  Beat vocabulary overrides.
├── archetype_constraints.yaml   # [ext]  Constraints on archetype selection.
├── achievements.yaml            # [ext]  Achievement definitions.
├── backstory_tables.yaml        # [ext]  Backstory roll tables.
├── equipment_tables.yaml        # [ext]  Starting-equipment roll tables.
├── seed_tropes.yaml             # [ext]  Seed-trope deck (per-pack; ADR-128 / Epic 22).
├── weather.yaml                 # [ext]  Weather model (tea_and_murder).
├── spellbook.yaml               # [ext]  Spell list (caverns_and_claudes); pairs with spells/ dir.
├── spells_wwn.yaml              # [ext]  WWN spell catalog — REQUIRED when ruleset: wwn AND any
│                                #        caster class declares casts_per_day_by_level (fail-loud).
├── lethality_design.md / *.md   # [opt]  Design notes (combat_design.md, magic_design.md). Docs only.
│
├── spells/                      # [ext]  Spell definition files (presence triggers saving_throws check).
├── dogfight/                    # [ext]  Dogfight subsystem tables (space_opera, ADR-077):
│   ├── descriptor_schema.yaml   #          schema, maneuvers, interactions, pilot skills.
│   ├── interactions_mvp.yaml    #          referenced from rules.yaml via _from: pointers.
│   ├── maneuvers_mvp.yaml
│   └── pilot_skills.yaml
│
├── audio/                       # [req* dir: audio/music]  Audio SPECS (renders live in R2).
│   ├── music/                   #        *_input_params.json — canonical ACE-Step gen params
│   │   ├── combat_input_params.json        per track (ADR-095). The OGG is in R2, not here.
│   │   ├── exploration_input_params.json
│   │   └── …                              (one *_input_params.json per mood/intensity track)
│   └── sfx/                     # [opt]  SFX cue specs.
│
└── worlds/                      # [req dir]  One subdirectory per world (see next section).
    ├── <world-a>/
    ├── <world-b>/
    └── <world-c>/
```

### Pack-root asset directories (specs only)

`pack_schema.yaml` also lists these asset dirs as required for a well-formed
pack. They hold `.gitkeep` placeholders and (historically) local render output;
**the canonical renders live in R2**, not here:

```text
genre_packs/<pack>/
└── assets/
    ├── fonts/                   # [req* dir]  Genre fonts (.gitkeep when none yet).
    └── images/
        ├── portraits/           # [req* dir]  Portrait render workspace (R2 is canonical).
        └── poi/                 # [req* dir]  POI-landscape render workspace (R2 is canonical).
```

> Historical drift: some packs also have `images/<type>/` or per-world
> `assets/<type>/`. These are render-output residue. The **canonical** location
> of any rendered asset is whatever key holds it in `r2_manifest.json` — not a
> repo folder.

---

## World-level layout (annotated)

Every world is a leaf directory under `worlds/<slug>/`. The world is **the
authoritative tier for cast, catalog, geography, lore, and visual prompts**.
Modeled on `space_opera/worlds/coyote_star` (the richest live world) plus
`perseus_cloud`, `aureate_span`, and `caverns_and_claudes/worlds/beneath_sunden`.

```text
genre_packs/<pack>/worlds/<slug>/
├── world.yaml                   # [req]  World manifest. draft: true HIDES the world from
│                                #        selection (and the loader skips it). See draft gate below.
├── lore.yaml                    # [req]  World lore. MUST carry seedable content (at least one of
│                                #        history / geography / cosmology / factions) or load fails —
│                                #        an empty LoreStore is forbidden (Epic 74, ADR-118).
├── cartography.yaml             # [req]  Geography / region graph. navigation_mode: room_graph
│                                #        pulls in a sibling rooms.yaml (or rooms/ dir).
├── openings.yaml                # [req]  Canned openings. MUST declare >=1 solo and >=1 MP opening
│                                #        (triggers.mode solo|multiplayer|either). Cross-validated
│                                #        against rigs/npcs/cartography at load.
│
├── theme.yaml                   # [req*] World theme chrome. Overrides genre theme.yaml. A world
│                                #        with NEITHER its own nor a genre theme fails load (named).
├── visual_style.yaml            # [req*] Z-Image visual prompt style for this world (ADR-086).
├── history.yaml                 # [req*] World history (free-form; loaded raw).
├── portrait_manifest.yaml       # [req*] Portrait spec: characters[] with id + prompt fields.
│                                #        The render spec — PNGs live in R2.
├── tropes.yaml                  # [req*] World tropes; inherit from genre tropes if present.
├── archetypes.yaml              # [req*] World NPC archetypes (CAST).
│
├── audio.yaml                   # [opt]  World audio hard-override (e.g. five_points). Falls back
│                                #        to genre audio.yaml when absent.
├── char_creation.yaml           # [opt]  World chargen scenes. REPLACES genre scenes wholesale
│                                #        (bare list; no per-scene merge, no inherit-key).
├── npcs.yaml                    # [ext]  AuthoredNpc list (npcs: [...]). ids must be unique;
│                                #        referenced by rigs crew_npcs and opening present_npcs.
├── bestiary.yaml                # [ext]  World creature stat blocks (CATALOG). REPLACES the
│                                #        genre-tier bestiary for ruleset-module packs.
├── creatures.yaml               # [ext]  Creature roster (caverns_and_claudes/beneath_sunden).
├── inventory.yaml               # [ext]  World inventory.
├── items.yaml                   # [ext]  Named/modifier/reliquary/consumable item catalog (CATALOG);
│                                #        item ids must be globally unique within the file.
├── magic.yaml                   # [ext]  World magic layer (composes over genre magic.yaml).
├── confrontations.yaml          # [ext]  World-specific confrontation defs (coyote_star).
├── rigs.yaml                    # [ext]  Chassis/rig instances (ADR-125). crew_npcs must resolve
│                                #        to npcs.yaml ids; chassis-anchored openings reference these.
├── chassis_classes.yaml         # [ext]  World chassis class roster (CATALOG; coyote_star).
├── chart.yaml / orbits.yaml     # [ext]  Orrery / orbital model (ADR-130; coyote_star, perseus_cloud).
├── <slug>.sector.json           # [ext]  Sector map data (perseus_cloud).
├── archetype_funnels.yaml       # [ext]  Archetype funnels (chargen routing).
├── premises.yaml                # [ext]  Political premises + blocs (wry_whimsy uprising substrate).
├── seed_tropes.yaml             # [ext]  World seed-trope deck (CAST; Epic 94).
├── classes.yaml                 # [ext]  World class/calling roster (CATALOG; Epic 94).
├── spells_wwn.yaml              # [ext]  World WWN spell catalog (CATALOG; Epic 94).
├── client_theme.css             # [ext]  Per-world CSS override (ADR-079); replaces genre CSS.
├── CAMPAIGN_NOTES.md / *.md     # [opt]  Author notes (players-guide.md, CAMPAIGN_NOTES.md). Docs.
│
├── cultures/                    # [opt dir]  Per-culture files (name + namegen). Preferred over the
│   ├── <culture>.yaml           #            single-file cultures.yaml form. Files without a `name`
│   ├── <culture>_namegen.yaml   #            key (visual-token overlays) are skipped by the loader.
│   └── …
├── legends/                     # [opt dir]  One Legend per file; optional _meta.yaml. Alternative
│   └── <legend>.yaml            #            to a single legends.yaml.
├── scenarios/                   # [ext dir]  ADR-053 mystery scenarios; one subdir per scenario:
│   └── <scenario>/
│       ├── scenario.yaml        #              [req in scenario] scenario manifest (ScenarioPack)
│       ├── clue_graph.yaml      #              clue graph
│       ├── assignment_matrix.yaml
│       ├── atmosphere_matrix.yaml
│       └── npcs.yaml            #              scenario NPCs
├── rooms/                       # [ext dir]  Room-graph nodes (caverns_and_claudes; ADR-055/106).
│   └── <exp###.r#>.yaml
├── cookbook/                    # [ext dir]  Procedural-gen recipes (beneath_sunden megadungeon):
│   ├── races/<race>.yaml        #              races, affinities, looks, special_rooms.
│   └── …
├── corpus/                      # [ext dir]  Per-world conlang word lists for Markov naming (ADR-091).
└── assets/                      # [req* dir]  Render workspace (R2 is canonical):
    └── images/
        ├── portraits/.gitkeep   #              [req* dir]
        └── poi/.gitkeep         #              [req* dir]
```

---

## Reference table

| File / dir | Level | Required? | Purpose |
|---|---|---|---|
| `pack.yaml` | pack | **loader-required** | Pack manifest (PackMeta): name, version, description, extensions. |
| `rules.yaml` | pack | **loader-required** | The rulebook: `ruleset:` binding, confrontations, beats, dials. |
| `progression.yaml` | pack | **loader-required** | Advancement / progression math. |
| `axes.yaml` | pack | **loader-required** | Tone/voice axes. |
| `prompts.yaml` | pack | **loader-required** | Narrator prompt scaffolding. |
| `visibility_baseline.yaml` | pack | **loader-required** | Perception/visibility defaults. |
| `lethality_policy.yaml` | pack | **loader-required** | LethalityArbiter policy. |
| `theme.yaml` | pack | audit-required | Genre theme chrome (world can override). |
| `audio.yaml` | pack | audit-required | Genre audio config (mood/sfx/themes). |
| `client_theme.css` | pack | audit-required | ADR-079 genre CSS. |
| `visual_style.yaml` | pack | optional | Z-Image style (visual prompts now live at world tier). |
| `archetypes.yaml` / `tropes.yaml` / `cultures.yaml` / `char_creation.yaml` / `inventory.yaml` / `power_tiers.yaml` | pack | optional | Genre-tier cast/catalog defaults; world-authoritative. |
| `classes.yaml` | pack | extension | Class definitions. |
| `magic.yaml` | pack | extension | Genre magic system (needs world `magic.yaml` to load). |
| `spells/`, `spellbook.yaml`, `spells_wwn.yaml` | pack | extension | Spell catalogs (`spells_wwn.yaml` fail-loud-required for caster wwn packs). |
| `dogfight/` | pack | extension | Dogfight subsystem tables (ADR-077). |
| `projection.yaml`, `beat_vocabulary.yaml`, `archetype_constraints.yaml`, `achievements.yaml`, `backstory_tables.yaml`, `equipment_tables.yaml`, `seed_tropes.yaml`, `weather.yaml` | pack | extension | Optional subsystems. |
| `audio/music/*_input_params.json` | pack | spec | Canonical ACE-Step gen params (OGG in R2, ADR-095). |
| `assets/fonts`, `assets/images/{portraits,poi}` | pack | audit-required dir | Render workspace (R2 canonical). |
| `worlds/` | pack | **loader-required dir** | One subdir per world. |
| `world.yaml` | world | **loader-required** | World manifest; `draft: true` hides + skips it. |
| `lore.yaml` | world | **loader-required** | World lore; must have seedable content. |
| `cartography.yaml` | world | **loader-required** | Region graph / geography. |
| `openings.yaml` | world | **loader-required** | Canned openings; ≥1 solo + ≥1 MP. |
| `theme.yaml` | world | required-or-genre | Theme chrome; world OR genre must supply one. |
| `visual_style.yaml`, `history.yaml`, `portrait_manifest.yaml`, `tropes.yaml`, `archetypes.yaml` | world | audit-required | Visual prompts, history, portrait spec, tropes, cast. |
| `npcs.yaml` | world | extension | AuthoredNpc list (unique ids). |
| `bestiary.yaml` / `creatures.yaml` | world | extension | Creature catalog (replaces genre bestiary). |
| `items.yaml`, `inventory.yaml` | world | extension | Item catalog / inventory. |
| `magic.yaml` | world | extension | World magic layer over genre magic. |
| `rigs.yaml`, `chassis_classes.yaml` | world | extension | Rig instances + chassis classes (ADR-125). |
| `orbits.yaml` / `chart.yaml` / `<slug>.sector.json` | world | extension | Orrery / orbital model (ADR-130). |
| `confrontations.yaml`, `archetype_funnels.yaml`, `premises.yaml`, `seed_tropes.yaml`, `classes.yaml`, `spells_wwn.yaml`, `client_theme.css` | world | extension | World subsystems / catalogs. |
| `cultures/`, `legends/` | world | optional dir | Per-culture / per-legend files (or single-file form). |
| `scenarios/<name>/` | world | extension dir | ADR-053 mystery scenarios. |
| `rooms/`, `cookbook/`, `corpus/` | world | extension dir | Room graph, procedural recipes, naming corpus. |
| `assets/images/{portraits,poi}` | world | audit-required dir | Render workspace (R2 canonical). |

---

## Genre-vs-world boundary + layered resolution

Per **ADR-140** and **ADR-121**, resolution layers world-over-genre:

- **Genre tier = rulebook only.** Resolution rules, progression, axes, narrator
  prompts, lethality + visibility policy, theme/audio chrome. The genre tier
  *may* ship cast/catalog defaults (archetypes, tropes, cultures, char_creation,
  inventory) as a shared base, but none are required there anymore.
- **World tier = cast + catalog + geography + lore + visual prompts**, and it is
  **authoritative**. Where both tiers supply a surface:
  - **Tropes** — world tropes inherit from genre tropes (per-field resolution).
  - **char_creation** — world scenes **REPLACE** genre scenes wholesale (no
    per-scene merge; the on-disk shape is a bare list; an
    `inherits_scenes_from_genre_pack` key is unsupported and fails loud).
  - **bestiary / cultures / archetypes** — world set replaces the genre pool.
  - **theme / audio / visual_style** — world value overrides genre; genre is a
    transitional fallback (a world with no theme at either tier fails load).
  - **magic** — composed: genre `magic.yaml` + world `magic.yaml`; **both must
    exist** for the magic system to load.
- **lore is world-only** — a genre-tier `lore.yaml` is *forbidden* by the
  validator (Epic 74 / story 74-3); only the world's `lore.yaml` seeds the
  LoreStore.

Every world-tier flavor/catalog load emits a `state_transition` OTEL span
(`world_lore`, `world_items`, `world_classes`, `world_chassis_classes`,
`world_seed_tropes`, `world_spell_catalog`) so the GM panel can prove the world
tier was read rather than the engine improvising from a removed genre default.

## Ruleset binding (`ruleset:` in rules.yaml)

A pack binds exactly one pluggable ruleset module via `ruleset:` in its
`rules.yaml` (ADR-117 / ADR-033):

| Value | Module | Used by |
|---|---|---|
| `native` (default) | ADR-033 dial/confrontation engine | most packs |
| `swn` | Stars Without Number | `space_opera` |
| `wwn` | Worlds Without Number | `elemental_harmony` |
| `cwn` | Cities Without Number | `neon_dystopia` |

An unknown `ruleset:` value raises `UnknownRulesetError` — fail loud, no silent
fallback. A `wwn` pack with caster classes that declare `casts_per_day_by_level`
**must** ship a `spells_wwn.yaml` catalog or the load fails.

## The `draft: true` world gate

A world's `world.yaml` may set `draft: true`. The loader **skips** draft worlds
entirely (`_load_single_world` returns `None`), so they never appear in
selection. This is how in-progress worlds stay hidden until their asset gate
(portraits + POI landscapes rendered to R2) is met — `tea_and_murder/blackthorn_moor`
is the current example. The old `genre_workshopping/` staging tree was retired
on 2026-06-03; `draft: true` replaces it.

## Media: repo holds specs, R2 holds renders

**Rendered images (PNG) and audio (OGG) are NOT canonical in this repo.** They
are canonical in **R2** (`cdn.slabgorb.com`), and the authoritative index of what
exists and where is **`sidequest-content/r2_manifest.json`** (a full bucket scan:
`key` / `md5` / `size_bytes` / `uploaded_at` per object). When a local file and
R2 disagree, **R2 wins**.

What git holds is the **spec** — the inputs that regenerate a binary:

| Asset | Spec in repo | Render in R2 |
|---|---|---|
| Music | `audio/music/*_input_params.json` (ACE-Step params, ADR-095) | `genre_packs/<pack>/audio/music/<track>.ogg` |
| Portraits | `worlds/<slug>/portrait_manifest.yaml` + `visual_style.yaml` prompt text | `genre_packs/<pack>/...` PNG |
| POI landscapes | POI yaml + `visual_style.yaml` (ADR-086) | `genre_packs/<pack>/...` PNG |

Render scripts (`scripts/generate_portrait_images.py`, `generate_poi_images.py`,
`generate_music.py`) write **locally**; `scripts/r2_sync_packs.py` uploads, and
`scripts/r2_manifest_from_bucket.py` rebuilds the index — those are **separate
manual steps**. Forgetting them is the classic cause of "the game serves an old
image." Do **not** treat local PNGs as canonical and do **not** commit fresh ones
(the `*.png filter=lfs` rules + historical LFS PNGs predate the R2 migration).

## Minimum viable pack and world

### Minimum pack (loads, not "complete")

The smallest set the **loader** needs to load a pack without raising:

```text
genre_packs/<pack>/
├── pack.yaml
├── rules.yaml                   # with a valid ruleset: value
├── progression.yaml
├── axes.yaml
├── prompts.yaml
├── visibility_baseline.yaml
├── lethality_policy.yaml
├── theme.yaml                   # OR a theme.yaml in every world (see below)
└── worlds/
    └── <slug>/                  # at least one non-draft world (see minimum world)
```

> To pass the **audit/scaffold** contract (`pack_schema.yaml`, `sq-audit`,
> `sidequest validate`) you additionally need `audio.yaml`, `client_theme.css`,
> and the `audio/music`, `assets/fonts`, `assets/images/{portraits,poi}` dirs.

### Minimum world (loads, not "complete")

The smallest set the **loader** needs for a world to load:

```text
worlds/<slug>/
├── world.yaml                   # draft: false (or omit draft)
├── lore.yaml                    # MUST have seedable history/geography/cosmology/factions
├── cartography.yaml
├── openings.yaml                # >=1 solo AND >=1 MP opening
└── theme.yaml                   # OR rely on the genre-tier theme.yaml
```

> To pass the audit contract, add `visual_style.yaml`, `history.yaml`,
> `portrait_manifest.yaml`, `tropes.yaml`, `archetypes.yaml`, and the
> `cultures/`, `legends/`, `assets/images/{portraits,poi}` dirs.

## Validate a pack

```bash
# From sidequest-server:
uv run python -m sidequest.cli.validate /path/to/genre_packs/<pack>
```

## Reference links

- **ADR-003** Genre Pack Architecture
- **ADR-004** Lazy Genre Binding
- **ADR-121** Layered Content Resolution — per-field merge strategies and provenance
- **ADR-140** Genre Is the Rulebook Only; the World Owns the Cast and Catalog (supersedes ADR-120)
- **ADR-117** Pluggable Ruleset Module System
- **ADR-086** Image-Composition Taxonomy (portraits / POIs / illustrations)
- **ADR-095** Daemon Music Tier via ACE-Step
- **ADR-053** Scenario System (clue graph, belief state)
- **ADR-091** Culture-Corpus + Markov Naming
- Spec: `docs/superpowers/specs/2026-05-25-genre-pack-filesystem-schema-design.md`
- Plan: `docs/superpowers/plans/2026-05-25-genre-pack-filesystem-schema.md`
- Canonical machine-readable schema: `sidequest-content/pack_schema.yaml`
- Loader (ground truth): `sidequest-server/sidequest/genre/loader.py`
- Repo overview: `sidequest-content/README.md`
