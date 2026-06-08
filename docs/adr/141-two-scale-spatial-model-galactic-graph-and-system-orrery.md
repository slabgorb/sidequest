---
id: 141
title: "Two-Scale Spatial Model — Galactic Graph (cartography) as Campaign View, Per-System Orrery as Local View; One File Per System"
status: accepted
date: 2026-06-08
deciders: ["Keith Avery", "Architect"]
supersedes: null
superseded-by: null
related: [55, 94, 117, 121, 130, 140]
tags: [game-systems, room-graph]
implementation-status: deferred
implementation-pointer: "NOT YET BUILT. Target seams: sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/{cartography.yaml, systems/<system>.yaml} (delete monolithic orbits.yaml fake root); sidequest-server/sidequest/orbital/{course.py scope selection, models.py loader}; sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx (cluster-graph default + orrery drill-down, retire the orbital:boolean whole-Map toggle)."
---

# ADR-141: Two-Scale Spatial Model — Galactic Graph as Campaign View, Per-System Orrery as Local View

> **Amends the wiring from playtest fix #748** (server PR #748 + ui PR #355),
> which made an orbital world render its orrery *as the entire Map tab* via a
> single `GameResponse.orbital: bool`. That was correct for a single-system
> world (`coyote_star`) and wrong for a *cluster* world (`perseus_cloud`): it
> suppressed the galactic graph and rendered 34 star systems as if they were
> planets orbiting one star. The orrery itself stays verified — it renders. This
> ADR re-scopes *what the Map tab shows at which scale*.

## Context

`perseus_cloud` is a **star cluster** — ~34 independent star systems connected by
jump points. Its `orbits.yaml`, however, models the cluster as a *single solar
system*: a fabricated primary body `perseus_cloud` (`type: star`, label "PERSEUS
CLOUD") with all 34 real systems hung off it as children at `semi_major_au` of
5–11. Astrophysically this is a set of stars "orbiting" each other at planet
distances — a dramatic but **remarkably brief** multiple-star configuration. The
orrery renderer faithfully drew exactly that: 34 stars-as-planets on one disc,
an unreadable knot with edge-stacked labels.

The fault is **one unwarranted tier of hierarchy** in the content, plus **one
overloaded boolean** in the UI. The orrery is not broken; it is *too obliging* —
`orbital/course.py` resolves `parent` recursively, so it renders the spurious
tier instead of rejecting it.

### Reuse-first inventory (what already exists)

| Concern | Canonical source | Wired into | Status |
|---|---|---|---|
| Galactic graph (nodes + edges) | `worlds/<world>/cartography.yaml` — `regions` (nodes), `routes` (edges), `navigation_mode: region`, fog discovery | `dungeon/region_projection.py`, `agents/subsystems/movement.py`, `agents/tools/resolve_location_entity.py` | **live** — this *is* "the usual mapping system" |
| System orrery (AU bodies) | `worlds/<world>/orbits.yaml` | `orbital/course.py`, `orbital/clock.py`, `OrbitalChartView` | **live**, fed malformed data |
| Drill-down scope | `orbital/course.py` (`system_root` = lone parent-less primary + direct children; drilled-in = any center + its direct children) | — | **live** — per-system orreries already work when drilled in |
| Game calendar / phase | ADR-130 orbital clock (`clock.epoch_days`, per-body `period_days`, `epoch_phase_deg`) | `orbital/clock.py` | **live** |
| `perseus_cloud.sector.json` | — | **nothing (zero code consumers)** | dormant 2018 SWN export — *not canonical* |

Two renderers, the galactic data, the drill-down scope, and the calendar clock
**all already exist.** No new rendering or navigation infrastructure is required.

## Decision

Adopt an explicit **two-scale spatial model**. Every spatial world has exactly
two views, drilled one into the other:

1. **Galactic / campaign view — the World Map.** An **SVG nodes-and-edges
   graph**, one per world, sourced from `cartography.yaml`. Nodes are star
   systems; edges are **jump points**, and the *edges carry the jump mechanics*
   (the campaign-scale movement layer). This is the top-level Map tab for a
   cluster world.

2. **Local view — the Orrery.** The orbital chart for the **current system**,
   drilled into from the node the party occupies. Each star system has its own
   orbital system, calendar-driven so body positions advance with the shared
   game clock.

**World map → local map. Campaign view → local view.** The orrery is a
*drill-down*, never the cluster's top-level view.

### Authoring unit: one file per system

The per-system orbital data is authored as **one file per star system**, not one
monolith for the whole cluster. A 140-body single file is overwhelming for a
content author (including future homebrew authors per ADR-140); a single system's
bodies are a tractable unit.

```
worlds/<world>/
  cartography.yaml              # galactic graph: nodes (systems) + edges (jump links) + jump mechanics — ONE per world
  systems/
    yula.yaml                  # one orrery file per system: primary star + bodies + orbital elements + calendar epoch
    forma.yaml
    …                          # authored on demand (see Consequences)
```

The fabricated `perseus_cloud` primary tier is **deleted**. Each system file has
its **own single primary** (one parent-less body), which preserves the existing
`course.py` `system_root()` contract verbatim — the strongest reuse available.

### Source of truth (resolves the standing question)

- `cartography.yaml` — **canonical galactic graph.** System nodes + jump edges +
  jump mechanics. Already wired to navigation.
- `systems/<system>.yaml` — **canonical per-system orbital motion** for the
  orrery, calendar-linked.
- `orbits.yaml` (monolith) — **retired** for cluster worlds; split into the
  per-system files above with the fake root removed.
- `perseus_cloud.sector.json` — **dormant.** Zero runtime consumers. Kept, if at
  all, as an *authoring reference* for regenerating the canonical files — never
  promoted to a runtime source (No Silent Fallbacks: a runtime must not read an
  unwired, unvalidated artifact).

### Calendar linkage

Every system file's bodies carry `period_days` + `epoch_phase_deg` and are
evaluated against the **single shared game calendar** (ADR-130 clock). The clock
is global; each system computes its own angular positions from it. "All orreries
connected to the game calendar" therefore needs no new mechanism — only that the
periods/phases live in the per-system file and are resolved through the existing
`orbital/clock.py` against the campaign day count.

### Jump mechanics live on the galactic edges

Inter-system travel is a **campaign-scale jump** (distinct from ADR-130's
intra-system approximate-Hohmann transit). Jump cost/time/hazard are properties
of `cartography.yaml` `routes` edges, adjudicated through the bound ruleset
(ADR-117; space_opera → SWN drive/fuel/transit). Intra-system movement stays the
orrery's course model (ADR-130). The two movement scales are separate and must
not be conflated, exactly as the two *view* scales are.

## Single-system worlds are unaffected

`coyote_star` is a genuine single system: one real primary (`coyote`) + habitat
bodies. It has no cluster scale, so its Map tab stays **orrery-as-Map** — the
top-level view *is* the local view because there is only one system. The model
degrades cleanly: a world with a single system-node collapses the two scales
into one. The distinguishing fact ("single system" vs "cluster of systems") is
derivable from the graph (one node vs many), so no new world-level flag is
strictly required, though an explicit declaration may be added for legibility
during implementation.

## Consequences

**Positive**
- Reuses both existing renderers, the existing galactic graph, the existing
  drill-down scope, and the existing calendar clock. Minimal new code.
- Restores the legible campaign map; the orrery becomes readable (one system at a
  time, not 34).
- Authoring unit is tractable and homebrew-friendly (one file = one system).
- Honors **Cost Scales with Drama / Diamonds and Coal**: systems are graph nodes
  by default and earn an orrery file *only when play reaches them* — `yula`
  first, the rest on demand. A node with no system file is still a navigable
  jump destination; it simply has no local orrery until authored.

**Negative / costs**
- Content migration: split `perseus_cloud/orbits.yaml` into per-system files and
  delete the fake root. The 97 correctly-parented bodies are salvageable
  (re-homed into their system files), so this is restructuring, not rewriting.
- Server: a loader change to resolve `systems/<system>.yaml` by the current
  region id, and to drive orrery scope from the current node rather than a single
  world-level `orbits.yaml`.
- UI: `MapWidget` must stop treating `orbital: bool` as a whole-Map toggle.
  Cluster world → cartography SVG graph as default Map; selecting/entering a node
  → that system's orrery. The `orbital` boolean is replaced by (or reinterpreted
  as) a scale/drill state.

## Migration / work split

1. **Content (GM/World-Builder lane):** for `perseus_cloud`, author
   `cartography.yaml` as the galactic graph (it already holds regions+routes;
   add jump mechanics to edges) and split orbital data into
   `systems/<system>.yaml`, primary-per-system, fake root deleted. Start with
   `yula` (current play); other systems on demand.
2. **Server (Dev lane):** per-region resolution of system orrery files; scope
   selection keyed to the current node; retain the single-primary `system_root()`
   contract per file. Jump mechanics on `routes` via the ruleset seam (ADR-117).
3. **UI (Dev lane):** `MapWidget` two-scale rendering — cartography SVG graph at
   campaign scale, orrery on drill-down; retire the orbital-as-whole-Map toggle.
4. **Cleanup:** mark `perseus_cloud.sector.json` as a non-runtime authoring
   reference (or remove); document that monolithic `orbits.yaml` is retired for
   cluster worlds.

## Alternatives considered

- **One `orbits.yaml`, multiple primaries, system-keyed (Option B).** Less
  content churn but breaks `system_root()`'s "single parent-less body" assumption
  (needs scope-selection by region) and gives up the clean one-file-per-system
  authoring unit. **Rejected** — the authoring overwhelm and loss of the existing
  scope contract outweigh the smaller diff.
- **Promote `sector.json` to a runtime source.** It is richer (coords, full
  hierarchy) but unwired, externally-sourced, and unvalidated. **Rejected** per
  No Silent Fallbacks; it may serve as an authoring aid only.
- **Keep `orbital: bool` and just fix labels (ADR-094 tuning).** Treats the
  symptom (noisy labels) not the disease (a cluster modeled as a system).
  **Rejected.**
