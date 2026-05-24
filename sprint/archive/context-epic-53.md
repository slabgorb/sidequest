# Epic 53: Road Warrior — Rig two-pool wiring + content alignment

## Overview

Content-side rig overhaul has landed in `sidequest-content/genre_packs/road_warrior/` (rules.yaml `edge_config`, inventory.yaml vessel templates, classes.yaml signatures, npcs.yaml). The backend now needs to be wired to match: the `EdgePool` model extended for vessel-attached `RigComposurePool` (53-1 ✓), the materializer hooking the vessel inventory item into a bound pool (53-2), a crash-event handler at Composure→0 (53-3), OTEL spans per ADR-031 (53-4), and a UI surface for the new pool + injury tags (53-5). One small content-tooling fix (53-6, render_common.slugify precedence) rides along.

**Priority:** P1
**Repos:** sidequest-server, sidequest-content, sidequest-ui
**Stories:** 6 (1 done, 5 remaining — 14 of 17 points outstanding)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Story 53-1 context** (`sprint/context/53-1.md`) | Foundation contract for `RigComposurePool` (delta API, binding model, OTEL stubs) — 53-2 builds directly on it |
| **ADR-014** (`docs/adr/014-diamonds-and-coal.md`) | Narrative-weight principle; rigs are diamond-class vessels |
| **ADR-024** (`docs/adr/024-dual-track-tension-model.md`) | Composure as the structural pool counterpart to Edge |
| **ADR-031** (`docs/adr/031-game-watcher.md`) | OTEL emission requirement; rig pool deltas + crash events must be observable |
| **ADR-078** (`docs/adr/078-edge-composure-combat.md`) | Edge / Composure semantics — RigComposurePool follows this contract |
| **road_warrior inventory** (`sidequest-content/genre_packs/road_warrior/inventory.yaml`) | Vessel templates (Tier 1–4 rigs) with composure encoded in tags (`composure:N`, `composure_max:N`) |
| **road_warrior rules** (`sidequest-content/genre_packs/road_warrior/rules.yaml`) | `edge_config` + `custom_rules.rig_progression_arc` + `rig_composure_spec` |

## Background

### Why this epic exists

Road Warrior is the SideQuest genre pack whose core fantasy is *the rig and the rider*. ADR-078 specified a two-pool combat model — Edge (personal Composure) and a *separate* vessel-attached pool — but the backend has only ever supported a single per-character `EdgePool`. The content team has shipped the data (vessel items as inventory, composure encoded in tags, progression arc + composure spec in rules.yaml) and is currently blocked on backend wiring: characters who select a rig at chargen have no `RigComposurePool` instantiated, the crash event never fires, and the GM panel has no observability into vessel state. Without this epic, the rig is purely narrative — the narrator can be gaslit by stat-bearing tags but nothing mechanically *guards* the rig at runtime. Per the CLAUDE.md "Gaslight the narrator with game state" principle, the materialized pool is the lie detector.

### Current state

- **Done (53-1):** `RigComposurePool` class lives at `sidequest-server/sidequest/game/rig_composure_pool.py` — Pydantic v2 model with `character_id` + `chassis_id` binding, bounded composure (0..max), `apply_delta()` returning a `RigComposurePoolDelta`, zero-crossing detection, and serialization. Telemetry helpers stubbed at `sidequest/telemetry/spans/rig.py`.
- **Not yet wired:** No materializer code reads vessel inventory items, no `RigComposurePool` is attached to `CreatureCore`, no crash event handler subscribes to `is_destroyed()`, OTEL spans are stub-level (53-4 finishes), UI shows nothing.
- **Content:** Vessel templates exist for tiers 1–4 with `composure:N`/`composure_max:N` encoded as tags. The materializer must parse these tags at instantiation time.

## Technical Architecture

### Component flow

```
Character Creation ─► Inventory (rig vessel item) ─► Materializer
                                                          │
                                                          ▼
                                    parse tags(composure:N, composure_max:N)
                                                          │
                                                          ▼
                                          RigComposurePool(character_id, chassis_id, …)
                                                          │
                                                          ▼
                                       Bound to CreatureCore alongside EdgePool
                                                          │
                                              ┌───────────┼───────────┐
                                              ▼           ▼           ▼
                                       OTEL span    Snapshot     Crash handler
                                       (53-4)       (persist)    (53-3, on Composure→0)
                                                                       │
                                                                       ▼
                                                   injury tag + Edge hit + dismount
```

### Key files

| File | Purpose | Status |
|------|---------|--------|
| `sidequest-server/sidequest/game/rig_composure_pool.py` | Pool model + delta/zero-crossing | ✓ (53-1) |
| `sidequest-server/sidequest/game/creature_core.py` | Carries the bound pool alongside EdgePool | wire (53-2) |
| `sidequest-server/sidequest/game/world_materialization.py` | Detect vessel item → instantiate pool | wire (53-2) |
| `sidequest-server/sidequest/telemetry/spans/rig.py` | Span definitions for rig_pool deltas + crash | extend (53-4) |
| `sidequest-server/sidequest/game/` (TBD crash handler module) | Composure→0 → injury + Edge + dismount | new (53-3) |
| `sidequest-ui/src/components/CharacterSheet*` | Surface RigComposure + Edge + injury tags | new (53-5) |
| `scripts/render_common.py` | slugify precedence fix for vessel item slugs | small (53-6) |

### Data flow / contracts

- **Tag parsing:** Materializer must read `composure:N`/`composure_max:N` from vessel item tags. No silent defaults — if a vessel lacks composure tags, the materializer fails loudly (per CLAUDE.md "No Silent Fallbacks").
- **Binding:** `RigComposurePool(character_id=<owner>, chassis_id=<vessel item id>)`. One rig per character per session; swapping vessels means replacing the pool.
- **Serialization:** Pool participates in session save (SQLite) via the snapshot path. Legacy saves without rig pools are throwaway per memory `[[legacy_saves]]`.
- **HP→Edge translation:** Per memory `[[hp_removed]]`, content YAML may carry B/X HP fields; translate at the materializer seam — never propagate HP into runtime entities.

## Cross-Epic Dependencies

**Depends on:**
- 53-1 (RigComposurePool model) — provides the class and APIs that 53-2 instantiates
- Content-side rig overhaul in `sidequest-content/genre_packs/road_warrior/` — already shipped

**Depended on by:**
- 53-3 (Crash handler) — needs 53-2's materialized pool to subscribe to zero-crossing
- 53-4 (OTEL spans) — needs 53-2's instantiation site to emit `rig_pool.created`
- 53-5 (UI surface) — needs 53-2's pool to be present in the snapshot before the client can render it
