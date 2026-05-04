# Caverns & Claudes — Hamlet of Sünden Design

**Date:** 2026-05-04
**Status:** Draft (pending user spec review)
**Author:** Brainstormed with Keith
**Scope:** Content + minimal schema reorganization. Engine/persistence/UI changes called out but specified separately.

---

## Summary

Consolidate four `caverns_and_claudes` worlds into one. Drop `dungeon_survivor/` and `primetime/` entirely (the reality-TV concept is shelved). Merge `grimvault/`, `horden/`, and `mawdeep/` into a single Darkest-Dungeon-shaped world: one persistent Hamlet (**Sünden**) with three dungeon entrances reachable from it. Each dungeon's existing Keeper is reframed as one of the Seven Deadly Sins. Lore frame is loose thematic kinship — three of seven sins woke close together; the other four are stories told elsewhere (future expansion hooks).

Player loop: roll/recruit hirelings in Sünden → pick a dungeon → delve → survivors return to roster → spend currency on stress relief → repeat.

## Goals

1. Replace the world-pick menu's three near-identical Caverns & Claudes entries with one canonical world.
2. Preserve the load-bearing creative work in each Keeper (monologues, awareness ladders, trap aesthetics, topology).
3. Establish a Hamlet hub that feels like *home* — recurring named NPCs, a wall of memory, characterful stress relief.
4. Set up a "wounded but not killed" loop so successful delves change a dungeon permanently without removing it from play.

## Non-Goals

- Tier 2 narrative scars / Tier 3 town building upgrades / heirlooms / provisions loadouts.
- The other four Deadly Sins (envy, wrath, lust, sloth). Future packs.
- Reviving any concept from `dungeon_survivor/` or `primetime/`.
- Engine changes for roster/stress/currency persistence — separate spec(s).
- New UI screens (dungeon picker, Hamlet view) — separate spec(s).

## The Three Sins

Each existing dungeon keeps its Keeper, monologue style, awareness mechanics, trap aesthetic, and topology. The reframe is purely lore-level.

| Dungeon | Keeper | Sin | Domain |
|---|---|---|---|
| Grimvault | The Patient Butcher | **Pride** | clinical separation; things taken apart |
| Horden | The Hoarder | **Greed** | retention; nothing leaves |
| Mawdeep | The Glutton Below | **Gluttony** | hunger; consumption |

Pride for the Butcher because the work is meticulous, *better-than-yours*, treating you as material to be improved by reduction. (Wrath was considered and rejected — the Butcher is never angry, never hurried.)

## Sünden — the Hamlet

A permanent settlement at the regional center, equidistant from the three dungeon entrances. Sünden is *the* town now — the existing per-dungeon towns (Ashgate / Copperbridge / Gristwell) demote to **dungeon approaches**: hollowed-out hamlets, half-abandoned, where the dungeon's pull is already strong. The party stages out of Sünden, walks through an approach to enter a dungeon, and (if they survive) returns to Sünden.

### Recurring NPCs

Sünden has named individuals the roster *knows*. A small, fixed cast — every hireling sees them between delves. Authoring exercise: 6–10 named NPCs covering the recruiter, the keeper of the wall, the three stress-service operators, an innkeeper, a market vendor, an itinerant preacher, etc. Voice and detail consistent across delves; tone shifts are the *drift* layer (next).

### Sin-Drift on Returning NPCs (Idea #3)

When the party returns from a delve, the **same NPCs are present but slightly off in a way the visited dungeon predicts.** This is the single biggest "Sünden feels alive" lever and the smallest implementation cost.

- Returned from **Grimvault (Pride)** — the innkeeper's voice doesn't carry. The market vendor sorts goods by material, not value. Conversations feel clinical, distant; people seem *evaluated* rather than greeted.
- Returned from **Horden (Greed)** — coins won't change hands. Shopkeepers add to piles they're not counting. The recruiter quotes prices but doesn't take payment. People won't release things — sentences trail unfinished, doors stay half-closed.
- Returned from **Mawdeep (Gluttony)** — someone is always eating. The innkeeper talks with her mouth full; the preacher's sermon has crumbs. Appetite drips into every interaction; nobody appears full.

Drift is **a flag set on the Hamlet at delve-end** keyed to the visited dungeon. It persists until the next delve overwrites it. Drift is consumed by the narrator via a Hamlet-specific prompt zone that reads the flag and the relevant per-sin drift profile. Drift profiles live alongside the dungeon (`dungeons/<name>/drift_profile.yaml` or in `dungeon.yaml`).

This replaces a more ambitious **#1/#2 numeric regional-drift** idea (weighted moving average across all recent delves). That's deferred — drift-of-the-most-recent-delve is enough to make the world feel responsive without a new world-axis abstraction.

### The Wall (carried inside Sünden)

A physical monument near the recruiter. Every successful delve carves a party's names into the wall under the sin they delved. Every failure leaves a cenotaph: names of those who didn't return. The narrator references the wall in town scenes ("you pass the wall — your name is on it twice now"). Implementation: append-only ledger keyed to `(sin, party_names, outcome, delve_number, timestamp)`; written at delve-end. Consumed by the narrator via a Hamlet prompt-zone snippet that pulls the most relevant wall entries (party member's prior wins/losses, sin's most recent victors, etc).

### Three Stress-Relief Services (Idea #8)

Stress reduction in Sünden is **three characterful services keyed to opposing virtues, not one generic tavern.** Each service is best at curing stress accrued from its opposing sin; *all* services work for *all* sins, but at different rates / costs / risks. This turns stress relief from a flat sink into a characterful, replayable choice.

| Service | Opposing Virtue | Cures | Mechanic flavor |
|---|---|---|---|
| **The Confessional** | Generosity (vs. Greed) | Best vs. Horden stress | Hireling gives away currency to the poor; cost scales with current wealth, not fixed |
| **The Workhouse** | Temperance (vs. Gluttony) | Best vs. Mawdeep stress | Hireling labors for a season-tick; takes time, not just money |
| **The Masquerade** | Humility (vs. Pride) | Best vs. Grimvault stress | Hireling becomes someone else briefly — adopts a false identity at a town festival; there is a small chance the false identity *sticks* and rewrites a flavor trait |

The off-axis cure ratios (e.g. Confessional vs. Mawdeep stress) are tunable later; the spec only commits to "three services, each best against one sin." Numeric balance is a follow-on.

## Wounded Sins (Idea #6)

Sins are **wounded, not killed**. Each dungeon has at least one boss-floor / culminating delve outcome. A successful boss delve flips a **permanent flag on that dungeon** that:

1. Applies a tone-override modifier (Patient Butcher comes back colder, slower, more distributed; Hoarder becomes paranoid; Glutton becomes slower-but-larger). Each post-wound profile is authored once per dungeon.
2. Adjusts the dungeon's awareness ladder thresholds (the dungeon "knows" it lost something).
3. Adds a new entry to the Wall under that sin: the party that wounded it.

The dungeon **stays delvable**. Player gets the campaign payoff of victory; world stays a campaign, not a checklist. Subsequent delves into a wounded dungeon are different, not easier.

A dungeon can only be wounded once in this design. (A v2 could add re-wounding with stacked profiles. Out of scope.)

The wound flag and post-wound profile are content-side; the engine just needs a flag-flip on a recognized outcome event. Engine spec separate.

## File Structure (target)

```
genre_packs/caverns_and_claudes/worlds/
  caverns_three_sins/                  # NEW — replaces grimvault/horden/mawdeep
    world.yaml                         # describes Sünden + region; no Keeper at this level
    hamlet.yaml                        # NEW — Sünden POIs, NPC roster, services, the Wall
    archetypes.yaml                    # WORLD-LEVEL hireling roster (merged from the three)
    archetype_funnels.yaml             # WORLD-LEVEL
    lore.yaml                          # regional cosmology — three sins of seven
    history.yaml                       # regional history; sin-Keepers as load-bearing
    legends.yaml                       # regional + per-sin legends
    factions.yaml                      # regional factions (per-dungeon factions stay below)
    visual_style.yaml                  # world-level base; per-dungeon overrides below
    portrait_manifest.yaml             # world-level cast — Sünden NPCs + hireling archetypes
    pacing.yaml                        # world-level
    audio.yaml                         # Sünden music + per-dungeon overrides
    assets/                            # world-level images
    audio/                             # world-level audio
    dungeons/
      grimvault/
        dungeon.yaml                   # was world.yaml — Keeper, axis_snapshot, cover_poi
        drift_profile.yaml             # how Sünden NPCs read after a Grimvault delve
        wound_profile.yaml             # post-wound tone-override + awareness changes
        approach.yaml                  # NEW — describes Ashgate as a hollowed-out approach
        rooms.yaml
        cartography.yaml
        creatures.yaml
        encounter_tables.yaml
        tropes.yaml
        openings.yaml                  # delve-specific openings (the descent into THIS dungeon)
        legends.yaml                   # dungeon-local legends
        factions.yaml                  # dungeon-local cults/inhabitants
        visual_style.yaml              # OPTIONAL override
      horden/                          # same shape; approach = Copperbridge
      mawdeep/                         # same shape; approach = Gristwell
```

The flat-with-`world.yaml` layout the loader currently expects becomes "world dir with optional `dungeons/` subdirectory." That's a loader change, but a small one — see Engine Surface below.

### Three structural alternatives considered

1. **Extend `world.yaml` with a `dungeons[]` array.** Single big YAML. Rejected — invasive to the existing schema and to every other world that doesn't have multiple dungeons.
2. **Introduce a "campaign" / "world group" layer above `worlds/`.** A new top-level genre-pack concept. Rejected — too much new abstraction for one world's needs; if a future genre pack wants the same shape it can adopt this design.
3. **Hub world directory; dungeons as a subdirectory under it.** *Selected.* Lowest disruption to existing per-dungeon authoring (each dungeon's rooms/cartography/creatures stay as-is, just relocated and with `world.yaml` slimmed to `dungeon.yaml`). Forces an explicit hub layer where the roster and Sünden live. Loader gets a small recursion change.

## What Survives, What Dies, What's Net-New

### Survives intact (per dungeon)

- Keeper definition (name, personality, obsession, monologue_style, trap_aesthetic, topology_tendency, awareness ladder).
- `rooms.yaml`, `cartography.yaml`, `creatures.yaml`, `encounter_tables.yaml`, `tropes.yaml`.
- Existing portrait/asset work for that dungeon.

### Slimmed or repurposed

- Each `world.yaml` → `dungeon.yaml` — drops world-level fields (`pacing`, `archetypes` references, world-level `visual_style` defaults) the parent now owns; keeps Keeper + axis_snapshot + cover_poi + dungeon-specific tone.
- Each existing town (Ashgate / Copperbridge / Gristwell) → an `approach.yaml` describing it as a half-abandoned hamlet at the dungeon mouth. Town as full POI demotes to "sin-touched outpost." Lore in those towns survives but is reframed as *symptoms of being too close to a sin* rather than *normal places*.
- `archetypes.yaml` from each of the three worlds merges into the world-level `caverns_three_sins/archetypes.yaml`. Duplicate archetypes deduplicated; near-duplicates kept and renamed where the variant is meaningful.
- `audio/` and `assets/` dirs consolidate at world level; per-dungeon overrides only where the existing audio/visual material is dungeon-specific.

### Net-new authoring

- `caverns_three_sins/world.yaml` — regional frame, Sünden description, three-of-seven cosmology pointer.
- `caverns_three_sins/hamlet.yaml` — Sünden POIs, the recurring NPC cast (6–10 named individuals), the three stress services, the Wall.
- Regional `lore.yaml` / `history.yaml` / `legends.yaml` / `factions.yaml` — braids the three sins thematically without committing to a strict cosmology.
- Per-dungeon `drift_profile.yaml` × 3 — how Sünden NPCs read post-delve.
- Per-dungeon `wound_profile.yaml` × 3 — tone-override + awareness-ladder changes after the dungeon is wounded.
- Per-dungeon `approach.yaml` × 3 — the demoted dungeon-mouth town.
- Updated `portrait_manifest.yaml` — adds the recurring Sünden NPCs.

### Dies (deleted entirely)

- `worlds/dungeon_survivor/` — full directory.
- `worlds/primetime/` — full directory.
- `worlds/grimvault/`, `worlds/horden/`, `worlds/mawdeep/` — directories deleted *after* their content has been folded into `worlds/caverns_three_sins/dungeons/<name>/`.

## Engine Surface (called out, NOT specified here)

This design is content-shaped. Each item below is a separate spec/plan:

1. **Genre-pack loader** — recurse one level for `worlds/<world>/dungeons/<dungeon>/`; recognize `dungeon.yaml` as a slim variant of `world.yaml`; return a world record with embedded dungeon records.
2. **World save persistence layer** — roster, currency, per-hireling stress, the Wall ledger, the wound flag per dungeon, the most-recent-delve drift flag — all persist between delves in the world's save file (not the per-delve session).
3. **Stress field on character model** — numeric, accrual events from delve telemetry, exposed to narrator.
4. **Sünden / dungeon-pick UI** — new screen. Selecting a world that has dungeons routes through the Hamlet first; selecting a dungeon from the Hamlet starts a delve with the persistent roster.
5. **Drift consumption** — narrator prompt-zone for Sünden scenes that reads `latest_delve_sin` flag and pulls the matching `drift_profile.yaml`.
6. **Wound consumption** — Keeper prompt-zone reads `is_wounded` flag and merges `wound_profile.yaml` overrides into the Keeper definition.
7. **Wall consumption** — narrator prompt-zone for Sünden scenes that pulls relevant Wall entries (current party member's prior wins/losses, sin's most recent victors).

## Risks

- **Authoring volume.** Net-new content is meaningful — Sünden, ~6–10 named NPCs with portraits, three drift profiles, three wound profiles, three approach files, plus regional lore consolidation. Possibly multi-sprint authoring.
- **Engine prerequisites.** Until the persistence layer exists, the Tier 1.5 mechanics (stress accrual + currency + Wall) are paper. The content design can be authored ahead of engine work, but playtest gating depends on engine.
- **Tone coherence.** Three independently-authored worlds had subtle inconsistencies (e.g. how each dungeon's town treats "outsiders"). The merge will surface them. Plan to do a single-pass consolidation read of all three sources before authoring the regional `lore.yaml`.
- **Drift profile balance.** "Sünden feels alive" depends on the drift being *legible* to players without being heavy-handed. Easy to over-write. Author tight, expect playtest revisions.

## Open Questions (deferred)

- Names of the recurring Sünden NPCs (authoring task, not design).
- How the four absent sins surface — are they *named* in lore (so players notice three of seven), or only implied? *Lean: named in passing, not detailed.*
- Currency name and per-dungeon loot character (Mawdeep loot is half-digested, Horden loot is half-rotted, Grimvault loot is dis-assembled into separated qualities).

## v2 Hooks (deliberately deferred)

- **Numeric regional drift** (Idea #1/#2) — weighted moving average across recent delves driving a Sünden world-axis. Deferred: most-recent-delve drift is enough.
- **Hireling shared history strings** (Idea #5) — pairs/trios who've delved together carrying a thin relational string. Deferred: needs prototype before schema commitment.
- **Re-wounding** — stacked wound profiles, multiple boss-delve outcomes per dungeon.
- **Tier 2 scars** — characters return permanently changed by a delve, not just stressed.
- **Tier 3 town upgrades** — Sünden buildings improve, services unlock.
- **The other four sins** — envy, wrath, lust, sloth as future dungeons or future packs.
