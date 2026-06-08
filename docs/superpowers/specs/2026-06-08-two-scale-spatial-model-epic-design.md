# ADR-141 Implementation Epic — Two-Scale Spatial Model

**Date:** 2026-06-08
**Author:** Architect (Ministry of Silly Walks)
**ADR:** [141 — Two-Scale Spatial Model](../../adr/141-two-scale-spatial-model-galactic-graph-and-system-orrery.md) (accepted, implementation deferred)
**Status:** Draft epic spec — ready for PM/SM to file
**Repos:** content, server, ui (orchestrator for the ADR itself, done)

---

## 1. Purpose

ADR-141 is accepted and its work split is sound. This spec turns the ADR's
four-part §Migration into a fileable epic: concrete stories, real seam names,
acceptance criteria, dependency order, and two precision corrections to the
ADR's `implementation-pointer` discovered during seam verification.

**Do not re-litigate the decision.** The design is settled. This is the
build plan.

## 2. Seam corrections to the ADR pointer

The ADR's `implementation-pointer` names `course.py` for scope selection. Seam
verification (2026-06-08) found the real targets:

| ADR pointer says | Actual seam | Evidence |
|---|---|---|
| `course.py system_root scope selection` | **`orbital/render.py:132`** `system_root()` | grep: `system_root` defined in `render.py`, not `course.py` |
| (unstated) file resolution | **`orbital/loader.py:42`** `world_dir / "orbits.yaml"` → `OrbitalContentMissingError` (loader.py:47) | this is the single hard-coded path that must become per-system |
| `models.py loader` | `orbital/models.py` `OrbitsConfig` (unchanged shape per file) | each per-system file still parses to one `OrbitsConfig` |

The per-system resolution change is **principally a loader.py change** (which
file to load for the current region), not a render.py change. `system_root()`
stays **verbatim** — that is the whole reuse argument: one parent-less primary
per file means the existing contract holds unmodified once the fake root is gone.

## 3. The edge wrinkle (authoring decision the ADR left implicit)

ADR §"Jump mechanics live on the galactic edges" says mechanics ride
`cartography.yaml` `routes` edges. But the live file's **graph connectivity is
carried on each region's `adjacent:` list**, not on `routes:`. `routes:`
currently holds exactly **one** entry — *The Black Door* (`zephyr → ceron`), a
special narrative link — with fields `distance / danger / terrain / from_id /
to_id` but **no jump mechanics** (no fuel, drive rating, or transit time).

So "put jump mechanics on the edges" forces a content-model choice. **Decision
for this epic (Architect):**

- **Connectivity stays on `adjacent:`** (it already feeds
  `dungeon/region_projection.py` + `movement.py`; do not fork it).
- **Jump mechanics are authored as `routes:` entries**, one per traversable
  `adjacent` pair *that play actually reaches* (Diamonds-and-Coal: author the
  edge mechanics on demand, exactly as system orrery files are authored on
  demand). An `adjacent` pair with no matching `routes` entry is a **navigable
  edge with default/ruleset-derived jump cost** — NOT a hard error (the graph
  must stay whole). The route entry, when present, **overrides** the default
  with authored fuel/time/hazard.
- New `routes` fields (additive, all optional): `jump_fuel`, `transit_days`,
  `drive_rating_min`, `hazard` (reuse existing `danger` if preferred — Dev/SWN
  seam call). Exact field names finalized in the server story against the
  ADR-117 SWN ruleset seam so they map to real drive/fuel mechanics.

This keeps **No Silent Fallbacks** honest: the *default jump cost* is an
explicit, ruleset-owned computation (logged via OTEL), not a silent zero.

## 4. Story breakdown

Five stories. Content-1 and Server-1 are the critical path; UI-1 depends on
Server-1's response shape. Content-2/Server-2 (jump mechanics) can follow.

### Story C1 — Content: split orbits.yaml, delete fake root, author `yula`
**Lane:** GM/World-Builder (YAML only)
**Repo:** content · **Files:** `worlds/perseus_cloud/orbits.yaml` (delete),
`worlds/perseus_cloud/systems/yula.yaml` (new)

- AC1: `systems/yula.yaml` exists; contains `yula`'s real primary as the **single
  parent-less body** plus its directly-parented children re-homed from
  `orbits.yaml` (strip the `parent: perseus_cloud` linkage; `yula` becomes the
  root).
- AC2: The fabricated `perseus_cloud` primary (orbits.yaml:17, `type: star`,
  label "PERSEUS CLOUD") is **deleted** — no body parents to it anywhere.
- AC3: `yula.yaml` carries `clock.epoch_days` and per-body `period_days` +
  `epoch_phase_deg` (calendar linkage preserved — ADR-130).
- AC4: Monolithic `orbits.yaml` removed for perseus_cloud (or emptied to a
  retirement stub documenting the split — Server story decides which the loader
  tolerates; prefer outright removal).
- AC5: The other ~33 systems are **not** authored now (Diamonds-and-Coal —
  on demand). A node with no `systems/<id>.yaml` is a valid jump destination.

### Story S1 — Server: per-region system-file resolution
**Lane:** Dev · **Repo:** server · **Files:** `orbital/loader.py`,
`orbital/scope_bind.py`, `orbital/render.py` (read-only confirm)

- AC1: `loader.py` resolves `worlds/<world>/systems/<region_id>.yaml` keyed to
  the **party's current region**, replacing the hard-coded
  `world_dir / "orbits.yaml"` (loader.py:42).
- AC2: `system_root()` (render.py:132) is used **unchanged** — one parent-less
  primary per file satisfies the existing contract. (Wiring test: assert the
  drilled-in scope for `yula` returns `yula` as root.)
- AC3: Current-region has **no** `systems/<id>.yaml` → fail loud with a clear
  error naming the missing path (No Silent Fallbacks — do NOT fall back to a
  cluster-wide chart). The galactic graph still renders that node; only the
  orrery drill-down is unavailable until authored.
- AC4: OTEL span on system-file resolution: which region, which file, hit/miss.
- AC5: `coyote_star` (single-system) regression: its orrery still loads as
  before (its lone-system path must collapse the two scales cleanly).

### Story U1 — UI: two-scale MapWidget, retire the `orbital: bool` whole-Map toggle
**Lane:** Dev · **Repo:** ui · **Files:**
`components/GameBoard/widgets/MapWidget.tsx` (`orbital?: boolean` at :20,
`orbitalEnabled` at :65)

- AC1: Cluster world (perseus_cloud) default Map = **cartography SVG
  nodes-and-edges graph** (regions=nodes, `adjacent`/`routes`=edges) — NOT the
  orrery.
- AC2: Selecting/entering a node drills into **that system's orrery**; a back
  affordance returns to the galactic graph.
- AC3: The `orbital: boolean` whole-Map toggle is replaced by a **scale/drill
  state** (campaign ↔ local). Amends playtest fix #748 — do not regress #748's
  verified "orrery renders" behavior, only re-scope *when* it renders.
- AC4: Single-system world (`coyote_star`) shows **orrery-as-Map** (two scales
  collapse to one — derivable from one graph node).
- AC5: A node with no authored orrery shows a legible "no local chart" state on
  drill-down, not a crash or blank.

### Story C2 — Content: jump mechanics on reached edges (`yula` neighbors first)
**Lane:** GM/World-Builder (YAML) · **Repo:** content · **Files:**
`worlds/perseus_cloud/cartography.yaml` (`routes:`)
**Depends on:** S2 field schema

- AC1: For each `adjacent` edge out of `yula` that play reaches, a `routes`
  entry carries authored jump mechanics in the S2-finalized field names.
- AC2: Unreached edges carry **no** routes entry and rely on the ruleset default
  (valid, not an error).
- AC3: *The Black Door* (`zephyr → ceron`) retains its existing narrative fields;
  jump-mechanics fields added if/when reached.

### Story S2 — Server: jump adjudication on edges via the SWN ruleset seam
**Lane:** Dev · **Repo:** server · **Files:** `agents/subsystems/movement.py`,
ruleset module (ADR-117, space_opera→SWN), `cartography`/region loader
**Depends on:** S1 (region-scoped spatial state)

- AC1: Inter-system jump cost/time/hazard adjudicated through the **bound
  ruleset** (ADR-117 SWN drive/fuel/transit), reading `routes` edge fields when
  present.
- AC2: Edge with **no** `routes` entry → ruleset computes a **default** jump
  cost from the SWN drive model; this default is explicit and **OTEL-logged**
  (No Silent Fallbacks).
- AC3: Finalizes the additive `routes` field names (`jump_fuel`, `transit_days`,
  `drive_rating_min`, …) and documents them for C2.
- AC4: Intra-system movement (ADR-130 course model) is **untouched** — the two
  movement scales stay separate (mirror of the two view scales).
- AC5: OTEL span per jump: from/to region, fuel spent, transit days, hazard roll.

## 5. Dependency / sequencing

```
C1 ──► S1 ──► U1        (critical path: orrery becomes legible per-system)
        │
        └──► S2 ──► C2  (jump mechanics layer; follows once region-scoped)
```

- **C1 + S1 + U1** deliver the core ADR value (legible campaign map + readable
  per-system orrery for `yula`). Ship this slice first.
- **S2 + C2** layer the campaign-scale jump crunch (Sebastien/Jade crunch
  payoff). Can be a second epic increment if scope pressure demands.

## 6. Out of scope / explicit non-goals

- Authoring all 34 system files (on demand — Diamonds-and-Coal).
- Promoting `perseus_cloud.sector.json` to a runtime source (stays dormant
  authoring reference — ADR §Source of truth, No Silent Fallbacks).
- Touching `coyote_star`'s content (genuine single system; only regression-tested).
- New world-level "cluster vs single" flag — derivable from node count; add only
  if implementation finds it materially clearer (ADR §Single-system worlds).

## 7. Verification spine (per OTEL principle)

Every subsystem decision emits a watcher event so the GM panel is the lie
detector, not Claude's prose:

- System-file resolution (S1 AC4): region → file → hit/miss.
- Jump adjudication (S2 AC5): from/to, fuel, transit days, hazard.
- Default-jump-cost computation (S2 AC2): explicit ruleset default, logged.

Each story's test suite includes a **wiring test** (CLAUDE.md mandate): S1 asserts
the loader is hit from a production path for `yula`; U1 asserts the cartography
graph mounts as default Map for a cluster world; S2 asserts jump adjudication is
reached from `movement.py`, not just unit-testable in isolation.
```
