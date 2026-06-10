# Story 98-4: C2 Content — jump mechanics on reached cartography routes (yula neighbors first)

**Story ID:** 98-4  
**Epic:** 98 — ADR-141 Two-Scale Spatial Model — Galactic Graph + Per-System Orrery  
**Points:** 2  
**Workflow:** trivial  
**Type:** content authoring  
**Repos:** sidequest-content  

## Summary

Author jump mechanics (fuel, transit time, drive rating requirements) on the cartography routes between reached systems in the `perseus_cloud` world. Start with `yula` and its neighbors. These mechanics override default ruleset-derived jump costs when explicitly authored on route edges.

## Context

**ADR-141** mandates a two-scale spatial model: galactic campaign view (cartography graph of systems) and local view (per-system orrery). Jump mechanics live on the graph **edges** (`cartography.yaml` `routes:`), overriding ruleset-default costs (ADR-117 SWN drive/fuel subsystem, landed in 98-5).

**Related Stories:**
- 98-1 (DONE): Split `orbits.yaml` into per-system files, authored `yula`
- 98-2 (DONE): Server loader resolution (per-region system files)
- 98-3 (DONE): UI two-scale MapWidget (cartography graph ↔ orrery drill-down)
- 98-5 (DONE): Server jump adjudication via SWN seam (default cost OTEL-logged)

**This story (98-4) depends on:** 98-5 (S2 finalizes the `routes` edge field names — `jump_fuel`, `transit_days`, `drive_rating_min`, `hazard`, etc.)

## Acceptance Criteria

1. For each `adjacent` edge from `yula` that play reaches, a `routes` entry in `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` carries authored jump mechanics in the field names finalized by S2 (98-5).
2. Unreached edges carry **no** routes entry and rely on the SWN ruleset default (valid, not an error).
3. *The Black Door* (`zephyr → ceron`) retains its existing narrative fields (`distance`, `danger`, `terrain`, `from_id`, `to_id`); jump-mechanics fields are added if/when reached.

## Implementation Notes

- **Data model:** `cartography.yaml` `routes:` is a list of objects with `from_id`, `to_id`, and optional mechanics fields.
- **Connectivity:** Graph connectivity stays on each system's `adjacent:` list (not on `routes:`); `routes:` entries are mechanics overlays on existing adjacencies.
- **Defaults:** An adjacency with no matching `routes` entry uses the ruleset default; the default cost is explicit and OTEL-logged (No Silent Fallbacks).
- **Spec location:** `docs/superpowers/specs/2026-06-08-two-scale-spatial-model-epic-design.md` § Story C2.

## Files

- `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` (modify `routes:`)
- Spec: `/docs/superpowers/specs/2026-06-08-two-scale-spatial-model-epic-design.md`

## Key References

- ADR-141: Two-Scale Spatial Model (galactic graph + per-system orrery)
- ADR-117: SWN ruleset seam for jump mechanics (drive/fuel/transit)
- Story 98-5: Finalizes the `routes` field names
