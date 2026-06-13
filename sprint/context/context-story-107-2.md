---
parent: 107
---

# Story 107-2 Context

## Title
Monster Manual for beneath_sunden — combat opponents are narrator-improvised
(the creature of animal musk) with no stable name or portrait; author the dungeon
bestiary as content entities (stable names + portrait assets: the four-toed pale
scuttler, the eyeless bristle-faced den creature) and inject per ADR-059 into
game_state as creatures nearby (not yet met), bound per-room, so the narrator draws
from them instead of inventing.

## Metadata
- **Story ID:** 107-2
- **Type:** feature
- **Points:** 5
- **Priority:** p1
- **Workflow:** tdd
- **Repos:** content, server
- **Epic:** 107 — beneath_sunden dungeon scene advance and Monster Manual binding
- **depends_on:** 107-1

## Source finding (sq-playtest-pingpong)

`/Users/slabgorb/Projects/sq-playtest-pingpong.md:245-254`
[GAP] Combat opponent is narrator-improvised, not a pre-rendered content item
(Monster Manual) — no portrait, ad-hoc name. Priority **high**, status **open**,
found by Operator (Keith) + DRIVER 2026-06-13.

- World: `caverns_and_claudes/beneath_sunden`, session
  `2026-06-13-beneath_sunden-bf7e8a76`.
- **Repro:** the Dungeon Combat opponent is named **"The creature of animal musk"** —
  an on-the-fly narrator label, not a defined bestiary entity. It has no portrait,
  so the confrontation panel can only show a "T" letter chip (pingpong:251).
- **Operator direction (pingpong:252):** the monster **should be pre-rendered as a
  content item** (Monster Manual / ADR-059 pre-gen pattern) **and have an icon in the
  confrontation panel.**
- **Two prongs (pingpong:253-254):**
  1. **CONTENT (this story):** beneath_sunden needs an authored bestiary — the dungeon
     creatures (the four-toed pale scuttler from the chase, the eyeless bristle-faced
     dog-sized den creature) as real content entities with stable names + portrait
     assets, injected per ADR-059 into `<game_state>` as "NPCs/creatures nearby (not
     yet met)" so the narrator draws from them instead of inventing.
  2. **CODE — confrontation panel renders the creature's portrait icon** — UI-polish,
     **OUT OF SCOPE** for this story (stays in the ping-pong loop; see also the related
     [UX] item at pingpong:233-243, "monster needs an icon").

The gap ties into the location/scene bug: generated-dungeon encounters spawn improvised
opponents because there is no per-room content binding — which is exactly why this story
**depends_on 107-1**.

### Dependency on 107-1 (pingpong source for the epic; epic-107.yaml:9-16)

107-1 is the **server bug** that generated-dungeon traversal never advances the structured
location/scene: descending the procedural ADR-106 dungeon leaves `discovered_rooms` empty,
`scene_id` null, and `region_transitions` frozen after the scripted opening — so the engine
treats the whole descent as ONE scene. 107-2's per-room creature binding **requires a stable
per-room location key to bind against**, which 107-1 produces. Until 107-1 lands, every turn's
`current_location` collapses to one frozen value and the injection seam cannot distinguish
"in the entrance (bind gnaw_swarm)" from "in the sump (bind otyugh)". Build the binding hook so
it consumes 107-1's advanced room/scene key; do not re-implement scene advance here.

## Background — what already exists (do not reinvent)

The Monster Manual injection mechanism is **fully live and wired** on the server — this is
NOT a build-from-scratch. The gap is **content authoring + per-room binding**, not engine
infrastructure. Verified against the live code:

**Server (ADR-059 injection — LIVE):**
- `sidequest-server/sidequest/game/monster_manual.py` — `MonsterManual` (pydantic),
  `EntryState{AVAILABLE,ACTIVE,DORMANT}`, `ManualNpc`, `ManualEncounter`. Formatting at
  `monster_manual.py:253` (`format_nearby_npcs`) and `:301` (`format_area_creatures`).
- `sidequest-server/sidequest/server/dispatch/monster_manual_inject.py` — the Python
  injection seam. Per the gaslighting doctrine it **materializes Manual entries into
  `snapshot.npcs`** as runtime `Npc` records via `NpcPatch`/`WorldStatePatch` (NOT
  appended "available list" prose). `inject()` at `:323`; encounter→patch at
  `_npc_patches_for_encounters` (stamps `location=current_location`); emits
  `monster_manual.injected` OTEL span (`SPAN_MONSTER_MANUAL_INJECTED`).
- **Wired per-turn:** `sidequest-server/sidequest/server/websocket_session_handler.py:796-815`
  calls `ensure_loaded(sd)` then `inject(sd, snapshot, current_location=mm_location,
  in_combat=...)` BEFORE the narrator runs. `:1139-1140` calls `mark_all_dormant` on
  location change + `mark_active_from_narration`.
- **Seeding:** `sidequest-server/sidequest/server/dispatch/pregen.py:196` `seed_manual` —
  for a `ruleset: wwn` pack it samples the resolved **`bestiary.yaml`** via
  `encountergen` (`GenrePack.effective_bestiary`) and **fails LOUD** (`EncounterSeedError`)
  if seeding produces nothing (story 90-1; No Silent Fallbacks).
- **Encountergen source path:** `sidequest-server/sidequest/cli/encountergen/encountergen.py`
  — ruleset-module packs (`ruleset != native`) seed from `bestiary.yaml`
  (`encountergen.py:811-817` fails loud if a ruleset pack resolves no bestiary). The
  **native** path reads `worlds/{world}/creatures.yaml` — but that path is NOT used here
  because caverns_and_claudes is `ruleset: wwn`
  (`genre_packs/caverns_and_claudes/rules.yaml:44`).

**Content (beneath_sunden — already authored):**
- `genre_packs/caverns_and_claudes/worlds/beneath_sunden/bestiary.yaml` — **14 SRD-stat
  combat entries** (the encountergen/Manual roster). Low band: `gnaw_swarm`, `rope_spider`,
  `hold_skeleton`, `shaft_goblin`, `grave_ghoul`, `harrier_pack_leader`. Mid:
  `wight`, `the_seep`, `otyugh`, `black_pudding`. Deep: `aboleth`, `vampire`,
  `mummy_lord`, `lich`. WWN-aligned stat lines (level==HD, ascending AC, attack_bonus≈level,
  morale on 2d12, save==15−floor(level/2)).
- `genre_packs/caverns_and_claudes/worlds/beneath_sunden/creatures.yaml` — the **image
  manifest** (Z-Image render spec), flat `creatures:` list consumed by
  `scripts/generate_creature_images.py`. **Only the 7 deep/mid capstones** have image specs
  (aboleth, lich, mummy_lord, vampire, otyugh, black_pudding, wight). **No image specs for the
  6 low-band shaft creatures** — and those are the actual early-combat opponents (see the
  diagnosis below).
- `genre_packs/caverns_and_claudes/worlds/beneath_sunden/portrait_manifest.yaml` — named-NPC
  portrait manifest; `characters:` carries chargen player-picker faces only (no townsfolk by
  `world_register.humanoid_constraint`). NOT the creature image surface.
- `genre_packs/caverns_and_claudes/worlds/beneath_sunden/rooms/` — 13 room files
  (`entrance.yaml`, `exp001.r0-r5`, `exp002.r0-r5`). `entrance.yaml:30` is the ONLY room that
  references a creature: `"Disturbing the drifts wakes the Gnaw-Swarm — an easy first fight,
  on purpose."` (prose affordance, **not a structured creature binding**).

## The diagnosis — why "creature of animal musk" appeared

The injection seam is live and the combat roster exists, yet the narrator still invented
"the creature of animal musk" with no portrait. Three interlocking causes:

1. **No per-room creature binding.** `_npc_patches_for_encounters` stamps a flat
   `location=current_location` zone label but there is **no mechanism tying a specific
   bestiary entry to a specific room** (entrance→gnaw_swarm, the sump→otyugh). The narrator
   received an unfiltered Available pool (or none salient to the room) and improvised a label.
   Per-room binding is the missing content+wiring layer this story adds — and it needs 107-1's
   per-room scene/location key to bind against.
2. **No portrait asset for the actual opponent.** Even when the narrator names a real
   bestiary creature, the 6 low-band shaft creatures (`gnaw_swarm` etc.) have **no entry in
   `creatures.yaml`**, so there is no rendered image asset — hence the "T" chip. The deep-band
   capstones have images; the early-game fights do not.
3. **The named playtest creatures do not exist as content.** Grep across the world dir for
   "scuttler", "bristle", "animal musk", "four-toed", "eyeless" returns **zero hits** —
   confirming "the four-toed pale scuttler" and "the eyeless bristle-faced den creature" are
   pure narrator inventions. They must either be authored as real bestiary entries with stable
   names + image specs, OR (preferred, less roster bloat) the existing `bestiary.yaml`
   low-band creatures must be bound per-room and given image specs so the narrator draws those
   instead. **Raise this authoring call with Keith** (Diamonds-and-Coal / Monster Manual
   doctrine): reskin the invented chase/den creatures onto existing roster entries
   (e.g. four-toed pale scuttler ↔ `rope_spider`/`gnaw_swarm`; eyeless bristle-faced den
   creature ↔ `grave_ghoul`/a den `shaft_goblin`) vs. adding net-new entries.

## Business Context

Per CLAUDE.md, SideQuest's load-bearing requirement is that the narrator be **good enough to
fool a 40-year career GM** — genuinely responsive, genre-true, never "winging it" with zero
mechanical backing. Combat is the most consequential moment, and an opponent named "the
creature of animal musk" with a placeholder "T" chip is the narrator improvising where it
should be drawing from authored world truth. ADR-059's Monster Manual pattern exists
precisely to stop this: pre-generated content in `<game_state>` is treated by Claude as
ground truth, so enemies are referenced with **exact names, abilities, and attack patterns**
instead of invented labels.

This also serves the **content-authorability** pillar (Jade, Keith): the dungeon bestiary
is *content* (world-tier YAML + image specs), authorable without engine changes (ADR-140:
genre is rules-only, the world owns the cast). Stable named opponents with portrait assets
beat narrator improvisation on every axis — and they make the later confrontation-panel
portrait-icon UX item (the OUT-OF-SCOPE prong) actually possible, because the opponent will
finally be a real entity with a stable name + rendered asset to wire to.

## Technical Guardrails

- **Follow the ADR-059 injection contract exactly.** Creatures enter as "nearby / not yet
  met" — materialized into `snapshot.npcs` as `NpcPatch`/`WorldStatePatch` records via the
  existing `monster_manual_inject.inject()` seam, NOT as appended "available list" prose
  (the Python gaslighting-doctrine divergence is deliberate — keep it). Do not bypass the
  seam or hand-roll a second injection path.
- **No new injection infrastructure.** `monster_manual.py`, `monster_manual_inject.py`,
  `pregen.py`, and the per-turn call at `websocket_session_handler.py:796-815` are LIVE and
  correct. This story adds (a) **per-room binding** that filters/selects which authored
  creature(s) are surfaced for the current room, consuming 107-1's room/scene key, and
  (b) **content** (image specs + any reskin/roster edits). Wire up what exists.
- **Content lives in the world dir, not the genre.** ADR-140: genre is the rulebook only;
  the world owns the cast and catalog. Bestiary stat blocks
  (`worlds/beneath_sunden/bestiary.yaml`), image specs
  (`worlds/beneath_sunden/creatures.yaml`), and per-room bindings
  (`worlds/beneath_sunden/rooms/*.yaml`) are all world-tier. The pack ships NO genre-level
  bestiary (see bestiary.yaml header).
- **Style lives ONLY in the visual_style suffix** (project rule, Keith emphatic). When
  authoring `creatures.yaml` image specs for the low-band creatures, the `description` is
  camera-style concrete subject prose ONLY (anatomy, posture, scale cue, what the dark does
  around it). Do NOT put medium/style ("pen-and-ink", "engraving", "crosshatch", "B&W")
  in creature `description` — that auto-layers from `visual_style.yaml` `positive_suffix`
  via the daemon StyleCatalog WORLD slot. Putting it in the description fights the suffix and
  flattens the render. Follow the existing `creatures.yaml` capstone entries as the template
  (note their header WIRING block and the no-text/no-caption cleanup clause).
- **No proper nouns in image specs.** Per the world's conceit (nothing is named) and the
  Z-Image rule in `creatures.yaml`, each `name` is a non-proper-noun descriptive phrase
  (it slugifies to the PNG filename); the SRD linkage stays in `id` for audit only and never
  reaches the renderer prompt.
- **WWN/SRD fidelity.** caverns_and_claudes is `ruleset: wwn` (`rules.yaml:44`,
  `win_condition: hp_depletion`). Any new/edited bestiary stat lines follow the existing
  SRD-aligned bands in `bestiary.yaml` (defer to SRD; don't hand-balance). Seeding fails
  LOUD if the roster resolves empty — keep it that way.
- **OTEL is the lie detector.** The injection seam already emits `monster_manual.injected`
  with `creatures_injected`, `patches_with_location`, `available_encounters`, `location`.
  The per-room binding MUST emit a span (or extend the existing one) proving the *bound*
  creature for the current room reached game_state — so the GM panel can confirm the narrator
  drew the authored creature rather than inventing one. Tie a wiring test to a production
  call path (CLAUDE.md: every test suite needs a wiring test).

## Scope Boundaries

**IN scope:**
- Authored bestiary **image specs** for the low-band shaft creatures that are the actual
  early-combat opponents (the 6 entries in `bestiary.yaml` with no `creatures.yaml` image
  spec): add render-ready entries to `worlds/beneath_sunden/creatures.yaml` (non-proper-noun
  descriptive name, camera-style `description`, `threat_level`, `tags`) — including the
  reskin decision for the playtest-named creatures (four-toed pale scuttler, eyeless
  bristle-faced den creature) onto roster entries OR as net-new authored entities
  (**confirm the reskin-vs-new call with Keith**).
- Any stat-block edits/additions to `bestiary.yaml` needed for the bound creatures (WWN/SRD
  bands; fail-loud preserved).
- **Per-room creature binding** — the hook that ties the right bestiary creature(s) to the
  right room and surfaces it through the existing ADR-059 `inject()` seam as "nearby / not
  yet met", consuming **107-1's** per-room scene/location key. The structured binding
  (room→creature) is the content+wiring deliverable.
- The OTEL span proving the bound creature for the current room reached `snapshot.npcs`.
- Portrait/creature image **prompts/specs** (WHAT entities + WHAT prompt text). Note which
  PNGs need rendering (see closing summary) — actual render is the asset-gen task below.

**OUT of scope:**
- **The confrontation-panel portrait/icon RENDERING** — wiring the UI panel to display the
  creature's image instead of the "T" chip. This is UI polish and stays in the ping-pong loop
  (pingpong:253-254 prong 2; related [UX] pingpong:233-243). This story makes the opponent a
  **real entity with a stable name + image spec**; showing it in the panel is separate.
- **107-1's scene/location advance** — depended on, not re-implemented here.
- ADR-106 dungeon materializer / generation changes (sibling to Epic 105; out per epic SCOPE).
- The actual GPU render of the new creature PNGs (asset-gen task — see closing note); the
  story delivers the specs and references the established render→R2 pipeline.

## AC Context

1. **Authored opponent, not improvised.** In beneath_sunden dungeon combat (the repro
   session's fight), the seated opponent resolves to an **authored bestiary entity with a
   stable name** (e.g. a low-band shaft creature from `bestiary.yaml`/`creatures.yaml`), NOT
   "the creature of animal musk." A behavior/integration test on the beneath_sunden combat
   path asserts the injected creature name matches an authored entry.
2. **ADR-059 nearby/not-yet-met injection.** The bound creature(s) appear in `game_state`
   (materialized into `snapshot.npcs` via the existing `monster_manual_inject.inject()` seam)
   as Available/not-yet-met BEFORE the narrator runs, so the narrator names them from content.
   The `monster_manual.injected` span shows `creatures_injected > 0` and
   `patches_with_location > 0` for the room.
3. **Per-room binding.** The right creature is bound to the right room: entering a given room
   surfaces that room's authored creature(s) (entrance→gnaw_swarm-class first fight per
   `entrance.yaml:30`; deeper rooms→their band), driven by 107-1's per-room location/scene
   key. A test proves room A surfaces creature A and room B surfaces creature B (not the same
   flat pool everywhere).
4. **Image spec exists for the bound opponent.** Each low-band combat opponent has a
   `creatures.yaml` image spec (non-proper-noun name, style-free camera-prose `description`,
   `threat_level`, `tags`) so a portrait asset can be rendered — closing the "no portrait /
   T-chip" half on the content side (the panel-wiring half stays OUT of scope).
5. **OTEL proof + wiring test.** A wiring test exercises the production injection path and the
   per-room binding span fires, proving the bound creature reached game_state from content
   (CLAUDE.md OTEL principle + every-suite-needs-a-wiring-test). No silent fallback: an
   unresolved room→creature binding fails loud, not silently emits an empty pool.

## Assumptions
- 107-1 lands first and exposes a stable per-room scene/location key usable as the binding
  filter (epic SCOPE confirms 107-1 populates `discovered_rooms`/advances `scene_id`/logs
  `region_transitions`). If 107-1's key shape differs from what binding needs, surface it as a
  cross-story dependency note rather than reinventing scene advance here.
- The reskin-vs-net-new authoring call (playtest-named creatures onto existing roster vs. new
  entries) is Keith's content decision; default to reskinning onto the existing low-band
  roster to avoid roster bloat, but confirm before authoring.
- The render→R2 asset pipeline (`generate_creature_images.py` → `r2_sync_packs.py` →
  `r2_manifest_from_bucket.py`) is the established path for the new creature PNGs; assets are
  canonical in R2, the YAML spec is what lives in git.
