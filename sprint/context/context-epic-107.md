# Epic 107 Context — beneath_sunden dungeon scene advance & Monster Manual binding

## Overview

Make in-dungeon traversal of `caverns_and_claudes/beneath_sunden` (WWN port, ADR-106
runtime procedural dungeon) advance the **structured** scene/location per room so the render
pipeline fires per room, and give combat **authored, named, portrait-bearing opponents**
(Monster Manual, ADR-059) instead of narrator improvisation. This is dungeon-traversal
*infrastructure + content*, distinct from Epic 106 (combat mechanics) and sibling to Epic
105 (procedural-deep reachability).

Source of record: the 2026-06-13 combat playtest (`~/Projects/sq-playtest-pingpong.md`),
OTEL + save-forensics.

## Background

Two interlocked findings from the run:

1. **Generated-dungeon scene/location does not advance (107-1).** Descending the procedural
   dungeon (rope → The Dropmouth → Wider Chamber → combat) advances the narration
   sub-titles but NOT the structured location/scene. Forensics: `discovered_rooms: []`,
   top-level `location`/`scene_id` null, `region_transitions` frozen after turn 4 (zero
   across the entire descent/chase/chamber/combat), inconsistent region pointers
   (`current_region: the_dropmouth` vs `pc_regions: {Groucho: entrance}`). The engine treats
   the whole descent as one scene, so the render pipeline (keys off scene/room change per
   ADR-109/ADR-050) **under-fires** (renders are not dead — at least one fired — but fewer
   illustrations than rooms traversed). It also **blocks per-room content binding** (107-2
   depends on this).

2. **Combat opponents are narrator-improvised (107-2).** The Dungeon Combat opponent was
   "the creature of animal musk" — an on-the-fly label with no stable identity or portrait,
   so the confrontation panel could only show a "T" letter chip. Per Operator direction the
   monsters should be **pre-rendered content entities** (ADR-059 pre-gen) injected into
   game_state as "creatures nearby (not yet met)" so the narrator draws from them.

## Technical Architecture

**107-1 (server).** The in-dungeon movement-resolution path exists (`movement.py` →
per-PC region applier → frontier hook) but isn't firing on descent — the narrator retitles
the scene via `narration_apply.py` `location_update`, hitting the
`sub_location_in_region_mode_world` skip so no transition/render fires. Two disambiguations
from the Architect pass: (a) `scene_id` is NOT a `GameSnapshot` field — tools derive it from
`current_room`; (b) `discovered_rooms: []` is *expected* because beneath_sunden is
`navigation_mode: region` — the real substrate is **`discovered_regions` + `region_transitions`**.
Render scheduling lives in `sidequest/renderer/` (ADR-050/ADR-109). Guardrail: No Silent
Fallbacks (don't let narration paper a static scene); no ADR-106 materializer changes.

**107-2 (content + server, depends_on 107-1).** The ADR-059 Monster Manual injection seam
is **already live and wired per-turn** (`monster_manual_inject.inject()` in
`websocket_session_handler.py`), and beneath_sunden **already has a 14-entry SRD
`bestiary.yaml`**. The real gaps: (1) **no per-room creature binding** (encounters surface
as a flat unfiltered pool, so the narrator invented an opponent), and (2) **no image specs
for the 6 low-band shaft creatures** (only the 7 deep-band capstones are in `creatures.yaml`).
The story binds the right authored creature per room (consuming 107-1's room key) and authors
the missing low-band image specs. Content authored in the **world** dir (ADR-140: genre is
rules-only, world owns the cast); **style lives only in the `visual_style.yaml`
`positive_suffix`**, never in creature description text.

**Out of scope (both stories):** the confrontation-panel portrait/icon *rendering* (UI
polish — stays in the ping-pong loop). This epic makes the opponent a real entity with an
asset and binds it per room; wiring the panel to display it is separate.

**Assets to render (asset-gen task specified by 107-2, not its code/test scope):** PNGs for
the six low-band beneath_sunden bestiary entries missing image specs — `gnaw_swarm`,
`rope_spider`, `hold_skeleton`, `shaft_goblin`, `grave_ghoul`, `harrier_pack_leader` (plus
whatever reskin Keith picks for the playtest-named "four-toed pale scuttler" and
"eyeless bristle-faced den creature"). Pipeline: `scripts/generate_creature_images.py` →
`r2_sync_packs.py` → `r2_manifest_from_bucket.py`. **Open authoring decision (Keith):**
reskin the invented chase/den creatures onto existing roster entries vs author net-new
(Architect recommends reskin to avoid roster bloat).

## Cross-Epic Dependencies

- **Epic 105** owns the surface→deep **crossing** and graph reachability/traversal mechanics
  (105-2 done: the single rope hop; 105-3: reverse seam / in-dungeon graph traversal).
  **107-1 owns everything AFTER the crossing**: per-room structured scene/location advance
  and the render fire per room entry. Explicit boundary to avoid collision.
- **Epic 106** (combat mechanics) is the companion epic from the same run.

## Planning Documents

- Source findings: `~/Projects/sq-playtest-pingpong.md` (2026-06-13 combat run).
- Per-story context: `sprint/context/context-story-107-{1,2}.md`.
- Key ADRs: 106 (procedural dungeon edge-expansion), 059 (Monster Manual game-state
  injection), 109 (persistent location descriptions + mechanical manifest), 050 (image
  pacing throttle), 140 (genre is rules; world owns the cast).
