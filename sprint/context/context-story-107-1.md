---
parent: 107
---

# Story 107-1 Context

## Title
Generated-dungeon scene/location advance — traversing ADR-106 procedural rooms never
updates discovered_rooms, scene_id, or region_transitions (all frozen after the scripted
opening), so the whole descent reads as one scene and the ADR-109/ADR-050 render pipeline
under-fires; advance the structured scene per room entry (populate discovered_rooms,
advance scene_id, log region_transitions) so a fresh POI/illustration fires on room entry
and per-room content binding becomes possible

## Metadata
- **Story ID:** 107-1
- **Type:** bug
- **Points:** 5
- **Priority:** p1
- **Workflow:** tdd
- **Repo:** server
- **Epic:** 107 — beneath_sunden dungeon scene advance and Monster Manual binding

## Business Context

Keith is the forever-GM who finally wants to *play* — and the single most load-bearing fact
about SideQuest is that the narrator must be good enough to fool a career GM. A dungeon
descent that reads as **one frozen scene** is exactly the kind of tell that breaks that
illusion: the narration sub-titles say you walked rope → "The Dropmouth — First Floor" →
"Wider Chamber" → combat, but the engine never advanced the structured location. To a
career GM, the give-away is the visuals: you move three "rooms" and the table sees one
illustration. The descent should *feel* like descending — each room a fresh place, with a
fresh image, with the room actually existing as an addressable thing the engine knows about.

This is also the **enabling story for the Monster Manual (107-2)**. Sebastien and Jade are
the mechanics-first players who carried a 140-turn game on narrative while the crunch was
broken — they want the dungeon to be a *real place* with *real inhabitants*, not the
narrator improvising "the creature of animal musk." But you cannot bind a pre-rendered
monster to a room (ADR-059 game-state injection) if the engine never registers that the PC
entered a new room. **Scene advance is the substrate; the bestiary content sits on top of
it.** 107-1 lays the substrate; 107-2 depends on it (`depends_on: 107-1` in the epic).

Source forensics: `/Users/slabgorb/Projects/sq-playtest-pingpong.md`, the
*"[BUG] Generated-dungeon traversal does not update location/scene entry"* finding (world
`caverns_and_claudes/beneath_sunden`, the 2026-06-13 dive). Smoking gun from
`/api/debug/save/<slug>/snapshot`:
- `discovered_rooms: []` — empty despite traversing.
- `current_region: "the_dropmouth"` BUT `pc_regions: {"Groucho":"entrance"}` — inconsistent
  pointers (party-level vs per-PC disagree).
- `character_locations: {"Groucho":"The Dropmouth"}` — coarse, stuck on the rim name.
- `region_transitions`: only two, both ≤ turn 4 (ropefoot→the_dropmouth turn 2,
  the_dropmouth→entrance turn 4). **ZERO after turn 4** across the entire descent / chase /
  chamber / combat.
- top-level `location` and `scene_id` null/None.

Impact: the render pipeline keys off scene/room change (ADR-109 persistent location
descriptions, ADR-050 image pacing throttle), so it **under-fires** — fewer illustrations
than rooms traversed. Renders are NOT dead (the daemon confirmed at least one scene render
fired for the wider chamber); the symptom is under-rendering, not zero rendering.

## Technical Guardrails

### No Silent Fallbacks — narration must not paper over a static scene
The whole bug class is a *narration-only scene change*: the narrator emits a sub-title
("Wider Chamber") via the `location_update` path while the structured region/room state
never moves. Today, when a narrator-supplied heading does not canonicalize to a **known**
region id, `narration_apply.py` deliberately treats it as a POI within the current region
and **skips** any transition — see the `region.entry_skipped_sub_location` span at
`sidequest-server/sidequest/server/narration_apply.py:4076-4101` (the
`sub_location_in_region_mode_world` reject path). That skip is *correct* for a genuine
in-region POI (90-6's "Dunkelkurve — Inside the Tunnel"), but in the procedural deep it is
swallowing a real room entry. **The fix must make in-dungeon room entry a real, structured,
dispatched event — not let the narration sub-title stand in for it.** If a descent expresses
movement but cannot resolve to a real room, fail loud (the existing `movement.unresolved`
ERROR span at `movement.py:18-25`), never narrate a phantom room with no backing state.

### The render fires on a REAL room change, not on a narration title
The render trigger keys off `result.location` truthiness in the `location_update` block
(`narration_apply.py:4140-4153`, the `state.location_update` watcher emit with
`discovered_count`), and ADR-050/ADR-109 throttle/persist off scene change. The fix must
ensure that **a real in-dungeon room entry produces the location/region advance the render
pipeline already keys on** — so a fresh POI/illustration fires per room. Do not add a second
render path; wire the real room-entry signal into the existing one. Per the OTEL principle,
every room-entry decision must emit a watcher event (the GM panel is the lie detector for
"did the engine actually advance, or did Claude just retitle the scene?").

### Coordinate, do not collide, with Epic 105's crossing fix
105-2 fixed the **surface→deep CROSSING** — the single hop from a cartography seam region
(`the_dropmouth`, which owns `Down the Rope → to_id: deep_descent`) into the procedural
`entrance` node, via `movement.py`'s `resolve_deep_descent` / `surface_descent` path
(`movement.py:300-315`, returns `resolved_via="surface_descent"`). That is the `turn 4`
the_dropmouth→entrance transition you DO see in the ledger. **107-1 is everything AFTER
that hop:** per-room scene/location advance during *in-dungeon* traversal (entrance →
exp00N.rN → …) and the render fire on each step. The in-dungeon resolution path already
exists in the same file (`movement.py:317-415`: `project_region` → candidate edges →
`_resolve` → sync-materialize → `apply_world_patch(pc_region=...)`); the bug is that this
path is **not firing** for in-dungeon descent (the narrator retitled the scene instead).
Do not touch the surface→deep crossing (done in 105-2) or the ADR-106 materializer.

### The substrate, not a parallel nav path
There is exactly one per-PC region-transition applier:
`GameSnapshot._apply_world_patch_inner`'s `pc_region` block
(`sidequest-server/sidequest/game/session.py:1497-1531`) — it stamps the
`region_transitions` ledger AND calls `notify_region_transition`
(`sidequest/dungeon/frontier_hook.py:109-160`), which dedup-appends into
`discovered_regions`. The in-dungeon fix must flow through THIS applier (the one-mechanism
rule), not invent a parallel writer. The `region_transitions` ledger is also what the
movement-engagement witness reads (`dispatch_engagement_watcher.py:257-283`) — keep it
fed so that witness does not false-negative.

### `scene_id` / `discovered_rooms` — name the substrate precisely
Two traps the FIXER/Dev must not conflate:
- **`scene_id` is NOT a `GameSnapshot` field.** `GameSnapshot` has no `current_scene` /
  formal `scene_id` — confirmed at `agents/tools/list_npcs_in_scene.py:11-17` and
  `agents/tools/query_scene_state.py:27-34`, where the tools *derive* an effective scene
  from the perspective PC's `current_room`. The pingpong's "scene_id null/None" means the
  top-level scene/location signal is absent; "advance scene_id" here means **advance the
  structured location/region signal the scene-derivation and render keys off** (per-PC
  region + location), not minting a brand-new top-level field unless the design note says so.
- **`discovered_rooms: []` is EXPECTED for this world — beneath_sunden is
  `navigation_mode: region`, not `room_graph`** (see
  `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml:8-17`
  — "navigation_mode is REGION (not room_graph) by deliberate design"). The ONLY writer of
  `discovered_rooms` today is the chargen-time init (`game/room_movement.py:55`); the
  runtime room surface (`validate_room_transition` / `apply_validated_move` /
  `build_room_graph_explored`) is explicitly documented as *not yet landed*
  (`room_movement.py:1-10`). So for THIS world the structured per-room advance lives on the
  **region/frontier substrate** (`discovered_regions` + `region_transitions`), and each
  procedural deep room IS a frontier region node (`entrance`, `exp00N.rN`). The Dev/Architect
  must decide with eyes open whether "populate discovered_rooms" means feeding the
  region/frontier substrate (most likely for a region-mode world) and/or whether the
  procedural deep should expose a room-graph surface — but must NOT silently leave the
  region substrate frozen while chasing an unused room_graph field.

## Scope Boundaries

### In scope
- **Structured scene/location advance per in-dungeon room entry** within the procedural
  ADR-106 deep: each descent/traversal step from one procedural region/room to the next must
  fire the real movement resolution (`movement.py` in-dungeon path,
  `apply_world_patch(pc_region=...)`), so:
  - `discovered_regions` (the region-mode substrate for this world; the field the pingpong
    calls "discovered_rooms") grows on each new room entry,
  - the per-PC region advances and stays consistent with `current_region` (fix the
    `current_region=the_dropmouth` vs `pc_regions.Groucho=entrance` inconsistency),
  - the structured location/scene signal advances per room (the `scene_id`/location signal
    the render + scene-derivation keys off),
  - `region_transitions` logs each in-dungeon move (not just the two scripted-opening hops).
- **Render fires per room:** the existing ADR-050/ADR-109 render trigger (keyed on the
  location/scene change) fires a fresh POI/illustration on each real room entry.
- **OTEL on every room-entry decision** (resolved / unresolved / skipped-as-POI) so the GM
  panel can confirm the engine advanced rather than the narrator retitling.

### Out of scope
- **The surface→deep CROSSING itself** — that is 105-2, already fixed (the rope hop from
  `the_dropmouth` to the procedural `entrance`; `resolve_deep_descent` /
  `surface_descent`). Do not re-open it. The two scripted-opening transitions in the ledger
  (ropefoot→the_dropmouth, the_dropmouth→entrance) are 105 territory.
- **The ADR-106 materializer / edge-expansion** — no generation changes (same guardrail as
  105-2). 107-1 advances state across already-materialized rooms and triggers
  sync-materialize through the existing path only.
- **The Monster Manual content + ADR-059 injection (107-2)** — authored bestiary, stable
  monster names, portraits, per-room creature binding. 107-2 `depends_on` this story; 107-1
  only makes per-room content binding *possible* by advancing the scene, it does not bind
  any content.
- **The confrontation-panel portrait/icon RENDERING** (UI polish) — stays in the ping-pong
  loop per the epic; not this server story.
- **Intent-router classification rework** — 105-2 already hardened the surface→deep router
  path; if in-dungeon descent is failing to classify as movement, note it for the Architect
  seam note but keep the fix on the deterministic in-dungeon resolution + render fire, not a
  router rewrite.

## AC Context

The acceptance criteria should prove the descent advances the structured scene per room and
the render fires per room — on the real beneath_sunden repro.

1. **Per-room region advance.** Descending into the generated dungeon and moving room-to-room
   (entrance → exp00N.rN → …) advances the per-PC region on EACH move via the in-dungeon
   `movement.py` resolution path (`apply_world_patch(pc_region=...)`), with
   `current_region` and `pc_regions[pc]` staying consistent (no repeat of the
   `the_dropmouth` vs `entrance` split). Behavior test on the repro topology.
2. **`discovered_regions` / discovered-rooms substrate populates.** The visited-room set
   grows on each new room entry (not frozen after the scripted opening) — i.e. the field the
   pingpong observed as `discovered_rooms: []` is no longer empty after an in-dungeon
   descent. (For this region-mode world that substrate is `discovered_regions`; the AC is
   "the visited-room set grows," substrate-agnostic.)
3. **`region_transitions` logs each in-dungeon move.** After descent through N rooms, the
   ledger carries a transition per real room entry (turn-stamped, per-PC), not just the two
   ≤turn-4 scripted hops. The movement-engagement witness
   (`dispatch_engagement_watcher`) sees a transition for the moving PC on each move turn.
4. **scene/location signal advances per room.** The structured location/scene signal the
   render + scene-derivation keys off advances per room entry (no longer null/frozen for the
   whole descent).
5. **Render fires per room (the load-bearing AC).** The ADR-050/ADR-109 render pipeline
   fires a fresh POI/illustration on each real room entry — **render-count tracks
   rooms-entered**. FIXER/DRIVER MUST confirm render-count vs rooms-entered (the original
   symptom was fewer illustrations than rooms traversed); the pass condition is
   approximately one fresh render per room entered (within the ADR-050 throttle), not one
   render for the whole descent.
6. **OTEL proof (the gate).** Each in-dungeon room entry emits a watcher/OTEL event
   (movement resolved span + frontier.region_transition with observers>0, and the
   location_update / render trigger), so the GM panel can distinguish "engine advanced the
   room" from "narrator retitled the scene." A descent step that cannot resolve a real room
   fails loud (`movement.unresolved`) — no phantom room narrated.
7. **No regression** to 105-2's surface→deep crossing (rope hop still binds to `entrance`),
   to 90-6's in-region POI skip (a genuine sub-location title in a region still does NOT
   fork a transition / sweep an anchored confrontation), or to surface-to-surface movement
   (ropefoot ↔ the_dropmouth).

## Key Code Sites (cite in the design note / tests)

- `sidequest-server/sidequest/agents/subsystems/movement.py:300-415` — in-dungeon movement
  resolution: `project_region` → candidate edges → `_resolve` → sync-materialize →
  `apply_world_patch(pc_region=...)`. This path EXISTS; the bug is it is not firing for
  in-dungeon descent. (Lines 300-315 are the 105-2 surface→deep crossing — out of scope.)
- `sidequest-server/sidequest/game/session.py:1497-1531` — the single per-PC
  region-transition applier (`pc_region` block): stamps `region_transitions` + calls
  `notify_region_transition`. The one-mechanism point; all advance must flow through here.
- `sidequest-server/sidequest/dungeon/frontier_hook.py:109-160` —
  `notify_region_transition`: dedup-appends `discovered_regions`, fires
  `frontier.region_transition` span, dispatches the look-ahead worker.
- `sidequest-server/sidequest/server/narration_apply.py:4076-4101` — the
  `region.entry_skipped_sub_location` reject (`sub_location_in_region_mode_world`): where a
  narrator sub-title is treated as an in-region POI and NO transition fires. The locus of
  the "narration papered over a real room entry" bug.
- `sidequest-server/sidequest/server/narration_apply.py:3895-3920` — Site B: the
  region-mode `current_region_advanced` path that stamps `region_transitions`
  (`via="narration_apply"`) ONLY when the heading canonicalizes to a KNOWN region id —
  procedural deep rooms the narrator titles ad-hoc won't match.
- `sidequest-server/sidequest/server/narration_apply.py:4140-4153` — `state.location_update`
  watcher emit; the location/scene-change signal the render trigger keys on.
- `sidequest-server/sidequest/game/room_movement.py:1-55` — room_graph init (the ONLY
  `discovered_rooms` writer; runtime room surface NOT yet landed). Read to understand why
  `discovered_rooms` is empty for this region-mode world.
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml:8-17,184-199`
  — `navigation_mode: region` (deliberate) + the `deep_descent` seam sentinel.
- `sidequest-server/sidequest/agents/dispatch_engagement_watcher.py:257-283` — the
  movement-engagement witness that reads `region_transitions` (keep it fed).

## Dependencies / Coordination
- **Sibling Epic 105** (same dungeon seam neighborhood): 105-2 fixed the surface→deep
  *crossing* (done); 105-3 covers reverse-seam / in-dungeon graph traversal — coordinate so
  107-1's per-room scene/render advance and 105-3's graph traversal don't double-implement
  the in-dungeon move. Boundary: 105 owns *crossing + graph reachability/traversal mechanics*;
  107-1 owns *scene/location advance + render fire on in-dungeon room entry*.
- **107-2 (Monster Manual)** `depends_on` this story — it binds content per room only after
  the scene advances. Do not pull any bestiary/ADR-059 work into 107-1.
- **Likely DESIGN-BEARING** (like 105-2): an Architect seam note should decide whether the
  fix is (a) ensuring the in-dungeon `movement.py` path dispatches on descent vs (b) wiring
  a deterministic in-dungeon room-entry advance, and precisely what "scene_id /
  discovered_rooms advance" means for a region-mode world. Confirm with SM whether a note
  gates Dev.
