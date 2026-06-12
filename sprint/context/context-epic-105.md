# Epic 105 Context

## Title
Beneath Sünden — make the procedural Deep reachable in live play (ADR-106 surface→deep crossing)

## Overview
Live-play dive 2026-06-12 (UI drive of caverns_and_claudes/beneath_sunden, OTEL + forensics confirmed). The ADR-106 megadungeon is FULLY BUILT but UNREACHABLE in real play. dungeon spans show materialize.commit seeded_entrance=true regions_committed=5 edges_committed=12 + setpiece_attach the_siphon at exp001.r3/r4 + dungeon_attach bootstrapped regions=6 — a complete Jaquaysed deep sits committed in the dungeon store. But the player never enters it: current_region walks ropefoot→the_dropmouth and STOPS (both static surface cartography regions); repeated region_projection 'current_region is a static cartography region (surface lane), not a node of the procedural dungeon graph — no projection' and dungeon.map_emitted discovered_regions=0/6 every turn. ROOT CAUSE: the surface→deep crossing (movement.py 59-12 handoff that binds PC to graph.entrance_id) is gated ENTIRELY behind the Haiku intent router classifying the action as movement{direction:deeper}, with NO deterministic backstop. Activity grid: movement fired turns 1-2 (ropefoot→the_dropmouth, surface-to-surface) but NOT on turn 3 — the most explicit descent ('down the rope into the dark tunnels until my boots find rock') was misclassified, no movement dispatch, and the narrator silently papered the gap with a location patch inventing 'The Dropmouth — The Deep' as a sub-location POI of the surface region (confabulated passages + a lurking threat). Violates No Silent Fallbacks + the OTEL principle: convincing narration, zero mechanical backing; the real megadungeon (the_siphon setpiece, 6 regions) unreachable behind the seam. NOT broken: chargen→game (works in UI; the headless WrongPhaseError is a driver-only pick_portrait gap), the authored Ropefoot opening (fires correctly), and the ADR-106 materializer (builds the deep faithfully). The defect is purely the binding/crossing. Sibling context: 90-6 fixed a related region-mode narration-drift confrontation-abandon in the same narration_apply neighborhood; 90-9 (backlog) also touches scripts/playtest.py chargen — coordinate the driver fix. Refs: ADR-106, ADR-055, ADR-113; movement.py:201-267 (59-12 handoff); narration_apply location_update; scenario scenarios/beneath_sunden_engagement.yaml (Story 59-15).

## Metadata
- **Epic ID:** 105
- **Repo:** server,orchestrator

## Evidence (live dive 2026-06-12)

Drive: real UI session `2026-06-12-beneath_sunden-2`, Groucho (Mage, INT 18), solo,
caverns_and_claudes / beneath_sunden. Surfaces read: OTEL dashboard (`:8765/dashboard`)
+ Save Forensics (`:8765/forensics`) + `/api/debug/save/<slug>/snapshot`.

**The Deep is built.** `dungeon` subsystem (65 events) emitted:
- `materialize.commit expansion_id=1 seeded_entrance=true regions_committed=5 edges_committed=12 frontier_edges_added=5`
- `commit_expansion expansion_id=0 regions=1` (entrance) + `expansion_id=1 regions=5 edges=12`
- `setpiece_attach setpiece_id=the_siphon region_id=exp001.r3` and `…r4`
- `dungeon_attach bootstrapped … regions=6` (entrance + `exp001.r0..r4`)

**The player never enters it.** Same subsystem, every turn:
- `region_projection … reason=current_region='ropefoot' is a static cartography region (surface lane), not a node of the procedural dungeon graph — no projection`
- `region_projection … current_region='the_dropmouth' … surface lane … no projection`
- `dungeon.map_emitted … pc_region=the_dropmouth, discovered_regions=0, total_regions=6` (×2)

Snapshot after two explicit descents: `current_region=the_dropmouth`,
`discovered_regions=['ropefoot','the_dropmouth']`, `pc_regions={Groucho: the_dropmouth}`,
`total_beats_fired=0`, `encounter=None`, `npc_pool=0`.

**Activity grid (movement subsystem):** fired turns 1–2, last-seen **T#2**. Turn 3 — the
most explicit descent ("down the rope into the dark tunnels … until my boots find rock") —
**no movement dispatch at all**. Turn-2 detail: `Patches: location(location)`, `Beats: none`.
The region change to "The Dropmouth — The Deep" came from a narrator `location` patch
(sub-location POI of the surface region), not a movement/region dispatch.

## Background — cross-story constraints & guardrails

- **No silent fallback at the seam.** The fix must make the surface→deep crossing
  deterministic OR fail loud. Never let `location_update` / narrator improvisation paper
  over a missed crossing by inventing a procedural-deep scene on the surface lane. This is
  the core SOUL/CLAUDE.md violation the epic exists to close.
- **Do NOT touch the ADR-106 materializer.** It builds the deep faithfully (6 regions, 12
  edges, the_siphon setpiece). The defect is purely *binding/crossing*. No generation
  changes, no re-roll/affinity changes. Scope discipline: binding only.
- **OTEL is the acceptance gate.** Per CLAUDE.md, every subsystem fix proves itself with
  spans. The crossing must emit a span showing the PC bound to a procedural node, and the
  region projection must engage (no more "surface lane — no projection" once descended).
- **Sequencing:** 105-1 (instrument) MUST land before 105-2 is verified — the headless
  `beneath_sunden_engagement.yaml` (59-15) is the span-proof harness and it currently dies
  in chargen. Fix the lie detector before trusting it.
- **Shared-file coordination:** 105-1 edits `scripts/playtest.py` chargen; backlog story
  **90-9** also edits `scripts/playtest.py` chargen (honor `scenario class:`). Land the two
  driver fixes without clobbering each other (ideally fold both chargen-driver gaps together).
- **Region-mode sibling:** 90-6 (done) fixed a related region-mode narration-drift bug
  (cosmetic scene re-title abandoning a confrontation) in `narration_apply.py`. 105-2's
  `location_update` guard lives in the same neighborhood — reuse the same
  `region.entry_skipped_sub_location` signal that 90-6 referenced; do not regress it.
- **What is NOT broken (don't chase):** chargen→game (works in UI; the headless
  WrongPhaseError is the 105-1 driver gap, not a player bug), the authored Ropefoot opening
  (fires correctly at session start), the materializer.

## Key references
- ADR-106 (procedural Jaquaysed megadungeon), ADR-055 (room/region graph navigation),
  ADR-113 (intent router — the probabilistic classifier being over-trusted).
- `sidequest-server/sidequest/agents/subsystems/movement.py:201-267` — Story 59-12
  surface→deep handoff (binds PC to `graph.entrance_id` on `direction=deeper`).
- `sidequest-server/sidequest/server/narration_apply.py` — `location_update` (the path that
  silently invented "The Deep" on the surface lane).
- `sidequest-server/sidequest/agents/intent_router.py:162-169` — movement classification
  prompt (the single point of failure today).
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml`
  — `the_dropmouth` owns the `Down the Rope → to_id: deep_descent` seam route.
- `scenarios/beneath_sunden_engagement.yaml` (Story 59-15) — the span-proof scenario.

---
_Generated by `pf context create epic 105` from the sprint YAML; enriched by PM 2026-06-12._
