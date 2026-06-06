---
id: 140
title: "Genre Is the Rulebook Only; the World Owns the Cast and Catalog — Supersedes ADR-120's Mechanics-in-Genre"
status: accepted
date: 2026-06-06
deciders: ["Keith Avery", "Dev (implementation)"]
supersedes: [120]
superseded-by: null
related: [3, 4, 79, 117, 120, 121, 126]
tags: [core-architecture]
implementation-status: partial
implementation-pointer: "sidequest-server/sidequest/genre/loader.py (_load_single_world world-tier classes/spells_wwn/seed_tropes loads + pack-level world-first aggregation), sidequest/server/dispatch/{class_resolve,char_creation_resolve,wwn_spell_catalog_resolve}.py (world-first resolvers), sidequest/genre/models/pack.py (World.classes / World.wwn_spell_catalog / World.chassis_classes / World.seed_tropes). Delivered by epic 94 stories 94-1..94-3."
---

# ADR-140: Genre Is the Rulebook Only; the World Owns the Cast and Catalog

> **Supersedes ADR-120's "mechanics-in-genre" framing.** ADR-120 correctly
> moved *flavor* (lore, theme, audio, visual style, history, named cast) down to
> the world tier and made genre-tier flavor optional. But it drew the line in
> the wrong place: it kept declaring **archetype templates, classes/callings,
> spell catalogs, and "mechanical" tropes as genre-tier scaffolding** (ADR-120
> §"Invariants/Contracts": *"Genre root = mechanical + genre-generic scaffolding
> only (rules, archetype templates, …, mechanical tropes)"*). Playtesting and
> the homebrew-authoring requirement (Jade, 2026-05-29) proved that line wrong.
> This ADR redraws it: **the genre tier is the RULEBOOK only; the world tier
> owns the cast and the catalog.**

## Context

SideQuest's old shorthand was *"Crunch in the Genre, Flavor in the World"*
(SOUL.md, ADR-003, restated by ADR-120). ADR-120 operationalized the *flavor*
half: it made genre-root `lore.yaml` / `theme.yaml` / `audio.yaml` /
`visual_style.yaml` / `cultures.yaml` optional, made the world tier
authoritative for those surfaces, elevated theme to a world-required loud-fail,
and added per-load OTEL spans. That half was right and stands.

The *crunch* half was wrong in one specific, load-bearing way. ADR-120 lumped
**three different kinds of thing** under "mechanics" and parked all of them at
the genre tier:

1. **The rulebook** — resolution rules (`rules.yaml`: confrontations, beats,
   resolution modes, ability-score names), progression, tone/voice axes, the
   narrator voice, lethality/visibility policy, the bound ruleset module
   (`ruleset:` → native / swn / wwn / cwn). These *are* genre-generic: a genre
   is "how this kind of story resolves," independent of any one setting.

2. **The cast** — the roster of playable archetypes a setting ships: classes
   and callings (C&C kits, Victoria callings, the WWN Guardian / Channeler /
   Spirit Medium), the archetype funnels, the NPC roster, the trope deck a
   world plants, the rigs/chassis a world fields.

3. **The catalog** — the content tables the cast draws on: the WWN spell
   catalog, the item catalog, the bestiary, the concrete (specialized) tropes a
   table actually sees.

ADR-120 treated #2 and #3 as if they were #1. Two facts broke that:

- **Worlds diverge in cast and catalog, not just flavor.** The same problem
  ADR-120 named for tropes ("`dust_and_lead` tropes are wrong for
  `the_real_mccoy`") applies to *every* cast/catalog surface. `space_opera`'s
  `perseus_cloud` and `aureate_span` want different class rosters and different
  spell/ability catalogs, not one genre-wide list. A genre-tier roster is, at
  best, redundant with every world that overrides it and, at worst, setting-wrong
  bleed — exactly ADR-120's own argument, under-applied.

- **Homebrew must not require engine changes.** As of 2026-05-29 Jade is the
  first non-Keith content author, extending `perseus_cloud` on a paste-in /
  pull-request path. The load-bearing requirement she stands for: *anyone* can
  add worlds, classes, spells, NPCs, tropes, and rigs **as content** (world
  YAML) without touching server code. If adding the cast a table wants forces a
  class or spell into a *genre*-tier file shared by sibling worlds — or worse,
  into engine code — the content surface has failed. Cast and catalog must be
  expressible at the **world** tier.

The migration branch (`feat/content-flavor-world-migration`) had already begun
moving cast/catalog files down to worlds, but left **holes**: some consumers
still read the genre tier, and the genre-tier `tropes.yaml` (the abstract
macro-trope inheritance base) was deleted out from under world tropes that still
`extends:` it — which failed the *entire* pack load
(`GenreMissingParentError`). Epic 94 closes those holes and records this ADR.

## Decision

**The genre tier is the rulebook only. The world tier owns the cast and the
catalog. Consumers read cast/catalog surfaces world-first.**

### D1 — Tier ownership, redrawn

| Surface | Tier | Why |
| --- | --- | --- |
| `rules.yaml` (confrontations, beats, **resolution modes**, ability scores), `ruleset:`, progression, axes, prompts, lethality/visibility policy, narrator voice | **genre (rulebook)** | genre-generic resolution behavior; one rulebook hosts many settings |
| WWN magic *block* (`rules.wwn` — attribute map, effort, casts-per-day) | **genre (rulebook)** | the *economy* is a rule; the *spells* are catalog |
| classes / callings, archetypes, archetype funnels, NPC roster, the trope deck a world plants, chassis/rig classes | **world (cast)** | the roster a setting fields; diverges per world; must be homebrewable |
| WWN spell catalog (`spells_wwn.yaml`), item catalog, bestiary, concrete (specialized) tropes | **world (catalog)** | the content tables the cast draws on; diverges per world; must be homebrewable |
| abstract macro-tropes (`abstract: true`, the `extends:` inheritance base) | **genre (rulebook scaffolding)** | universal narrative patterns ("The Mentor", "The Prophecy") every world *specializes*; never emitted directly — only a parent pool for world tropes |

The one subtlety: an **abstract macro-trope** (`abstract: true`) is rulebook
scaffolding, not cast. It is never shown to the table; it exists only as the
parent that a world's concrete trope `extends:`. It belongs at the genre tier
exactly as the un-migrated `mutant_wasteland/tropes.yaml` keeps Dead Signal /
Mutation Tide as the base for `flickering_reach`'s children. The migration
over-deleted these; epic 94 story 94-3 recovers them.

### D2 — World-first loading + aggregation in the loader

`_load_single_world` (`loader.py`) loads each world-tier cast/catalog surface
from `worlds/<slug>/<surface>.yaml`, exposes it on the `World` model
(`World.classes`, `World.wwn_spell_catalog`, `World.chassis_classes`,
`World.seed_tropes`), and emits a `state_transition` OTEL span (op `loaded`,
component `genre`) so the GM panel can prove the world read fired.

`load_genre_pack` then **aggregates world rosters up** into the pack-level
field (`GenrePack.classes`, `GenrePack.wwn_spell_catalog`, …) **only when the
genre tier ships none** — the union of every world's surface. When a genre tier
*does* ship the surface (e.g. `elemental_harmony` keeps one shared
`spells_wwn.yaml` for both worlds; `space_opera`/`heavy_metal`/C&C keep genre
class rosters), that genre default is authoritative and worlds are not
aggregated up — the genre default is an intentional shared catalog, not a hole.
Worlds that share an id (class / spell) must agree on its definition; a genuine
divergence **fails loud** (No Silent Fallbacks).

### D3 — World-first resolvers, with OTEL resolve spans

Production consumers resolve a surface for a connection/turn through a
world-first resolver that returns the bound world's surface when present, else
the genre-tier/aggregate default, emitting a `state_transition` span (op
`resolved`, `tier` ∈ {`world`, `genre`}):

- `resolve_classes(pack, world_slug)` — chargen class roster
  (`dispatch/class_resolve.py`, epic 94-2)
- `resolve_char_creation_scenes(pack, world_slug)` — chargen scenes
  (`dispatch/char_creation_resolve.py`)
- `resolve_wwn_spell_catalog(pack, world_slug)` — WWN spell catalog
  (`dispatch/wwn_spell_catalog_resolve.py`, epic 94-3), read by the cast
  pipeline (`narration_apply._resolve_wwn_cast_for_beat`) and the `long_rest`
  reprepare tool
- chassis/rig and seed-trope draw sites read `World.chassis_classes` /
  `World.seed_tropes` directly (epic 94-1)

The `tier` field is the lie detector: it proves the cast/catalog the engine used
came from the world tier, not improvised from a removed genre default.

### D4 — The rulebook stays genre-tier; resolution modes do not move

`ConfrontationDef.resolution_mode` (ADR-077) and the rest of `rules.yaml`
remain genre-tier. Resolution *rules* are the rulebook. What moves world-first
is the *spell catalog the cast resolution reads* — not the resolution rule
itself. This keeps the WWN `rules.wwn` economy block (a rule) at the genre tier
while the spell catalog (a table) is world-first.

## Invariants / Contracts

- **Genre = rulebook only.** Genre root holds resolution rules, the bound
  ruleset, progression, tone/voice axes, narrator voice, lethality/visibility
  policy, and the abstract macro-trope inheritance base. It holds **no** world
  cast and **no** catalog by mandate (a shared genre-tier roster/catalog is a
  permitted *default*, not a requirement — see D2).
- **World = cast + catalog.** Classes/callings, archetypes, NPC roster, the
  planted trope deck, rigs, the spell catalog, items, and bestiary are
  world-tier and homebrewable without engine changes.
- **World-first resolution, fail-loud on divergence.** Consumers read the bound
  world's surface first; same-id surfaces that disagree across worlds fail loud
  (No Silent Fallbacks). A required surface that resolves from *neither* tier
  fails loud, named.
- **Cast/catalog loads and resolutions are observable.** Every world-tier
  cast/catalog load emits a `loaded` span; every resolution emits a `resolved`
  span stamped with the tier it read.
- **ADR-120's "mechanics-in-genre" is INVALIDATED** for cast and catalog. The
  flavor-in-world half of ADR-120 stands and is subsumed here; the
  archetype-templates / classes / spell-catalogs / mechanical-tropes-as-genre
  claim is replaced by D1.

## Consequences

- ADR-120 is marked **superseded** (`superseded-by: 140`). Its flavor decisions
  (D1–D5 of ADR-120) remain accurate and live; this ADR widens the boundary from
  flavor to cast+catalog and is the architecture-of-record going forward.
- Packs may keep a shared genre-tier catalog where worlds genuinely share one
  (elemental_harmony's spell catalog) — D2's "genre default is authoritative
  when present" makes that a first-class, non-hole choice rather than a
  violation.
- Homebrew authors can add a world's classes/spells/tropes/rigs as world YAML.
  The loader aggregates and the resolvers read world-first; no server change is
  required to field a new world's cast.
- Known partial: not every catalog surface has a dedicated world-first resolver
  yet (items/bestiary read pack-level today); they are covered by the same
  aggregation and are slated to grow resolvers as consumers need per-world
  divergence. Tracked under epic 94 follow-ups.

## Implementation notes (epic 94)

- **94-1** — chassis/rig classes + seed-trope deck loaded world-first; consumers
  (`init_chassis_registry`, interior dispatch, seed-deck draw sites) repointed.
- **94-2** — class roster + char_creation scenes loaded world-first + aggregated;
  `resolve_classes` wired into the connect chargen builder.
- **94-3** — WWN spell catalog loaded world-first + aggregated;
  `resolve_wwn_spell_catalog` wired into the cast pipeline and long_rest;
  recovered the deleted `elemental_harmony` abstract macro-tropes (The Mentor,
  The Corruption, The Prophecy, The Coming of Age, The Resistance, The Spirit
  Crisis) to the genre tier as the `extends:` inheritance base, unblocking the
  whole pack load.
