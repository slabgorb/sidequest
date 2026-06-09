# Epic 98: ADR-141 Two-Scale Spatial Model — Galactic Graph + Per-System Orrery

## Overview

Implement [ADR-141](../../docs/adr/141-two-scale-spatial-model-galactic-graph-and-system-orrery.md)
(accepted 2026-06-08): give every spatial world **two views drilled one into the
other** — a galactic/campaign **nodes-and-edges graph** (`cartography.yaml`,
systems=nodes, jumps=edges) and a local **per-system orrery** drilled into from
the occupied node. The fabricated single-star-cluster hierarchy in
`perseus_cloud/orbits.yaml` is deleted; orbital data is re-authored **one file
per system** (`systems/<id>.yaml`), and the UI stops treating `orbital: bool` as
a whole-Map toggle. The decision is settled — this epic is the build plan, not a
re-litigation.

**Priority:** P3
**Repo:** content, server, ui (orchestrator owns the ADR, already done)
**Stories:** 5 (20 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-141 — Two-Scale Spatial Model** (`docs/adr/141-two-scale-spatial-model-galactic-graph-and-system-orrery.md`) | Decision (two-scale model); Authoring unit (one file per system); Source of truth; Calendar linkage; Jump mechanics on galactic edges; Single-system worlds; Migration/work split; 2026-06-08 d3-dag amendment |
| **Epic design spec** (`docs/superpowers/specs/2026-06-08-two-scale-spatial-model-epic-design.md`) | §2 Seam corrections; §3 Edge wrinkle (adjacency vs routes); §4 Story breakdown + ACs; §5 Dependency/sequencing; §6 Out-of-scope; §7 Verification spine |
| **ADR-130 — Orbital Story-Time Clock** (`docs/adr/130-*.md`) | Shared game-calendar clock that drives per-system body angular positions |
| **ADR-117 — Pluggable Ruleset Module System** (`docs/adr/117-*.md`) | SWN seam for inter-system jump cost/fuel/transit adjudication |
| **ADR-140 — Genre Is the Rulebook; World Owns the Cast/Catalog** (`docs/adr/140-*.md`) | Homebrew-author authoring tractability (one file = one system) |
| **Reference-pages React migration spec** (`docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md`) | Shared d3-dag Map component (epic 100 / 100-10) — U1's render substrate |

## Background

### The problem: a cluster modeled as a single solar system

`perseus_cloud` is a **star cluster** — ~34 independent star systems linked by
jump points. Its `orbits.yaml`, however, models the whole cluster as *one solar
system*: a fabricated primary body `perseus_cloud` (`type: star`, label "PERSEUS
CLOUD") with all 34 real systems hung off it as children at `semi_major_au` of
5–11. The orrery renderer faithfully drew exactly that — 34 stars-as-planets on
one disc, an unreadable knot of edge-stacked labels.

The fault is **one unwarranted tier of hierarchy** in the content (the fake
`perseus_cloud` primary) plus **one overloaded boolean** in the UI. Playtest fix
#748 (server PR #748 + ui PR #355) introduced a single `GameResponse.orbital:
bool` that renders an orbital world's orrery *as the entire Map tab*. That was
correct for a single-system world (`coyote_star`) and wrong for a cluster: it
suppressed the galactic graph entirely. **The orrery itself is verified — it
renders (#748).** This epic re-scopes *what the Map tab shows at which scale*; it
does not rebuild the renderer.

### Why this is low-risk, reuse-first work

Per the ADR's reuse inventory, **everything needed already exists and is live**:

- The **galactic graph** (`cartography.yaml` regions+routes, fog discovery) — already
  wired to `dungeon/region_projection.py`, `agents/subsystems/movement.py`,
  `agents/tools/resolve_location_entity.py`.
- The **system orrery** renderer (`orbital/render.py`, `OrbitalChartView`) — live,
  merely fed malformed data.
- The **drill-down scope** (`system_root()` = lone parent-less primary + direct
  children) — already works when drilled in.
- The **shared game calendar** (ADR-130 clock) — global, drives angular positions.

No new rendering or navigation infrastructure is required. The work is
restructuring content, a loader change, a ruleset-seam call, and a UI view-model
change. This is why it sits at **P3**: the orrery already renders (#748 verified);
this is *legibility* + *per-system structure*, below the P1 backlog.

### What "done" delivers

The core slice (C1 + S1 + U1) restores a legible campaign map and a readable
per-system orrery for `yula` (current play). The second increment (S2 + C2)
layers campaign-scale **jump crunch** (fuel/transit/hazard via the SWN ruleset) —
the mechanical payoff Sebastien and Jade ask for. Systems become graph nodes by
default and earn an orrery file *only when play reaches them* (Diamonds-and-Coal):
`yula` first, the rest on demand. A node with no system file is still a navigable
jump destination.

## Technical Architecture

### Two-scale model

```
World Map (campaign view)              Local view
┌────────────────────────────┐        ┌─────────────────────────┐
│  cartography.yaml graph     │ drill  │  systems/<region>.yaml  │
│  nodes = star systems       │ ─────► │  one parent-less primary│
│  edges = jumps (mechanics)  │ ◄───── │  + bodies (orbital)     │
│  ONE file per world         │  back  │  calendar-driven (130)  │
└────────────────────────────┘        └─────────────────────────┘
   region_projection.py /                 orbital/loader.py →
   movement.py (live)                      render.py system_root() (verbatim)
```

**World map → local map. Campaign view → local view.** The orrery is always a
drill-down, never the cluster's top-level view. A single-system world
(`coyote_star`) has one node, so the two scales collapse to one — its Map stays
orrery-as-Map. The single-vs-cluster distinction is derivable from node count;
no new world-level flag is required (add only if implementation finds it
materially clearer).

### Key files

| File | Repo | Change |
|------|------|--------|
| `worlds/perseus_cloud/orbits.yaml` | content | **Delete** the fake `perseus_cloud` primary (orbits.yaml:17); retire the monolith for cluster worlds |
| `worlds/perseus_cloud/systems/yula.yaml` | content | **New** — `yula`'s real primary as single parent-less root + re-homed children, `clock.epoch_days` + per-body `period_days`/`epoch_phase_deg` |
| `worlds/perseus_cloud/cartography.yaml` | content | `routes:` entries carry authored jump mechanics on reached edges (`yula` neighbors first) |
| `orbital/loader.py` (`:42`) | server | Resolve `worlds/<world>/systems/<region_id>.yaml` keyed to current region, replacing hard-coded `world_dir / "orbits.yaml"`; fail loud on missing (No Silent Fallbacks) |
| `orbital/render.py` (`:132`) | server | `system_root()` used **verbatim** — read-only confirm; one parent-less primary per file satisfies the existing contract |
| `agents/subsystems/movement.py` + ruleset module | server | Inter-system jump adjudication via the bound SWN ruleset (ADR-117); explicit OTEL-logged default for unrouted edges |
| `components/GameBoard/widgets/MapWidget.tsx` (`:20`, `:65`) + `components/MapOverlay.tsx` | ui | Retire `orbital: boolean` whole-Map toggle → campaign↔local **scale/drill state**; render via the shared d3-dag component |

> **Seam correction (epic spec §2):** the ADR pointer names `course.py` for scope
> selection, but `system_root()` actually lives in **`orbital/render.py:132`** and
> the hard-coded path is **`orbital/loader.py:42`**. The per-system resolution change
> is principally a **loader.py** change. `system_root()` stays verbatim — that *is*
> the reuse argument: one parent-less primary per file means the contract holds
> unmodified once the fake root is gone.

### Edge model — connectivity vs mechanics (epic spec §3)

Graph **connectivity** stays on each region's `adjacent:` list (already feeds
`region_projection.py` + `movement.py` — do not fork it). **Jump mechanics** are
authored as `routes:` entries, one per traversable `adjacent` pair *that play
reaches*. An `adjacent` pair with no matching `routes` entry is a **navigable
edge with a ruleset-derived default jump cost** — explicit and OTEL-logged, never
a silent zero or a dropped edge. A `routes` entry whose endpoints aren't in any
`adjacent` list is a route-level anomaly (drop + WARN), never promoted to
connectivity. New `routes` fields (additive, optional) — `jump_fuel`,
`transit_days`, `drive_rating_min`, `hazard` — are finalized in S2 against the
SWN seam and documented for C2.

### Two movement scales, kept separate

Inter-system **jump** (campaign scale, `cartography.yaml` edges, SWN
drive/fuel/transit) is distinct from intra-system **course** (ADR-130 approximate
Hohmann transit, the orrery). The two movement scales must not be conflated —
exactly as the two *view* scales must not. S2 leaves the ADR-130 course model
untouched.

### Verification spine (OTEL — the lie detector)

Every subsystem decision emits a watcher event so the GM panel verifies the fix,
not Claude's prose:

- **S1 AC4** — system-file resolution: region → file → hit/miss.
- **S2 AC2** — default jump-cost computation: explicit ruleset default, logged.
- **S2 AC5** — jump adjudication: from/to region, fuel spent, transit days, hazard roll.

Each story carries a **wiring test** (CLAUDE.md mandate): S1 asserts the loader is
hit from a production path for `yula`; U1 asserts the cartography graph mounts as
default Map for a cluster world; S2 asserts jump adjudication is reached from
`movement.py`, not merely unit-testable in isolation.

### Story breakdown & sequencing

```
C1 ──► S1 ──► U1        (critical path: orrery becomes legible per-system)
        │
        └──► S2 ──► C2  (jump-mechanics layer; follows once region-scoped)
```

- **98-1 (C1, content, 3pts):** split `orbits.yaml` → `systems/yula.yaml`, delete fake root, preserve calendar linkage. Other ~33 systems NOT authored (on demand).
- **98-2 (S1, server, 5pts):** per-region system-file resolution in `loader.py`; `system_root()` unchanged; fail loud on missing; OTEL on resolution; `coyote_star` regression.
- **98-3 (U1, ui, 5pts):** two-scale `MapWidget` — cartography graph default + orrery drill-down; retire `orbital: bool`. **Depends on epic 100 / story 100-10 (shared d3-dag Map component).**
- **98-4 (C2, content, 2pts):** jump mechanics on reached `yula`-neighbor edges, in S2-finalized field names. **Depends on S2 schema.**
- **98-5 (S2, server, 5pts):** inter-system jump adjudication via SWN ruleset seam; OTEL-logged default cost; finalizes `routes` field names; ADR-130 course untouched. **Depends on S1.**

The C1+S1+U1 slice delivers core ADR value first; S2+C2 can be a second
increment if scope pressure demands.

### Out of scope (epic spec §6)

- Authoring all 34 system files (on demand — Diamonds-and-Coal).
- Promoting `perseus_cloud.sector.json` to a runtime source (stays a dormant authoring reference — No Silent Fallbacks).
- Touching `coyote_star` content (genuine single system; regression-tested only).
- A new world-level "cluster vs single" flag (derivable from node count; add only if materially clearer).

## Cross-Epic Dependencies

**Depends on:**
- **Epic 100 — Reference pages → React SPA migration (story 100-10):** provides the shared **d3-dag cartography-layout module + Map component** consumed by both the reference page and the in-game `MapOverlay`. Story 98-3 (U1) renders via this component and **must not** build against the retired `cartographyLayout.ts` SVG path. 100-10 (P2) lands first; 98-3 (P3) owns only the campaign↔local scale/drill view-model.
- **ADR-130 (Orbital Story-Time Clock) — live:** the shared game calendar drives per-system body positions; per-system files carry `period_days`/`epoch_phase_deg` resolved through `orbital/clock.py`.
- **ADR-117 (Pluggable Ruleset Module System) — live:** the space_opera→SWN binding adjudicates inter-system jump cost/fuel/transit on `cartography.yaml` edges.
- **Playtest fix #748 (server PR #748 + ui PR #355) — merged:** established the verified "orrery renders" behavior this epic re-scopes (must not regress).

**Depended on by:**
- **Future cluster worlds** — any multi-system spatial world reuses the two-scale model and the one-file-per-system authoring unit established here.
- **Campaign-scale jump crunch** — the S2/C2 jump-mechanics layer is the mechanical-engagement payoff (Sebastien/Jade) built on top of the restructured graph.
