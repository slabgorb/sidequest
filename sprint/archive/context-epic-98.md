# Epic 98: ADR-141 Two-Scale Spatial Model — Galactic Graph + Per-System Orrery

**Epic ID:** 98  
**ADR:** ADR-141 (accepted 2026-06-08)  
**Status:** Backlog  
**Priority:** P3  
**Repos:** content, server, ui  

## Summary

Implement ADR-141: a two-scale spatial model for campaign exploration. The galactic view shows a cartography graph (systems as nodes, jumps as edges); drilling into a node reveals that system's orrery (orbital mechanics, per ADR-130). Reuses existing renderers and clock; minimal new code.

## Design Overview

**ADR-141 mandates:**
- **Galactic scale:** `cartography.yaml` SVG graph with systems=nodes, adjacencies=edges
- **Local scale:** Per-system orrery, one file per system (`worlds/<world>/systems/<id>.yaml`)
- **Jump mechanics:** Authored on routes edges, overriding SWN ruleset defaults
- **Reuse:** Both renderers (orrery + graph) already exist; the split is organizational

**Two authoring choices:**
1. **Connectivity stays on `adjacent:`** (feeds movement logic; do not fork)
2. **Jump mechanics are `routes:` entries**, one per *reached* adjacency (Diamonds-and-Coal)

## Stories

| ID | Title | Points | Type | Status | Deps |
|---|---|---|---|---|---|
| 98-1 | C1: split orbits.yaml → systems/yula.yaml | 3 | refactor | DONE | — |
| 98-2 | S1: per-region system-file resolution | 5 | tdd | DONE | 98-1 |
| 98-3 | U1: two-scale MapWidget (graph+orrery drill) | 5 | tdd | DONE | 98-2, 100-10 |
| 98-4 | C2: jump mechanics on reached routes | 2 | trivial | BACKLOG | 98-5 |
| 98-5 | S2: jump adjudication via SWN seam | 5 | tdd | DONE | 98-2 |

## Spec

**Full spec:** `docs/superpowers/specs/2026-06-08-two-scale-spatial-model-epic-design.md`

**Key sections:**
- § 2: Seam corrections (loader.py, render.py, models.py)
- § 3: Edge wrinkle (connectivity vs. mechanics authoring)
- § 4: Story breakdown with acceptance criteria
- § 5: Dependency graph (C1 → S1 → U1; S1 → S2 → C2)
- § 7: OTEL verification spine (every subsystem emits watcher events)

## Verification

Every story includes wiring tests (CLAUDE.md mandate) per § 7:
- **S1:** System-file resolution (region → file → hit/miss) — OTEL span
- **U1:** Cartography graph mounts as default Map for cluster world
- **S2:** Jump adjudication reached from movement.py, not isolated unit test
- **S2 AC2:** Default jump cost is explicit and OTEL-logged (No Silent Fallbacks)

## Cross-Epic Dependencies

**Epic 100 (Phase 3):** Story 98-3 depends on epic 100 story 100-10 (shared d3-dag Map component). Land 100-10 before 98-3. Ownership: 100-10 owns the layout engine; 98-3 owns the view-model (scale/drill UX).

## Out of Scope

- Authoring all 34 system files (on demand, Diamonds-and-Coal)
- Promoting `perseus_cloud.sector.json` to runtime (stays authoring reference)
- Touching `coyote_star` (single-system regression test only)
- New "cluster vs single" flag (derivable from node count)

## References

- ADR-141: Two-Scale Spatial Model (accepted 2026-06-08)
- ADR-117: SWN ruleset seam for drive/fuel mechanics
- ADR-130: Orbital Story-Time Clock (calendar + per-body periods)
- ADR-014: Diamonds and Coal (author on demand)
