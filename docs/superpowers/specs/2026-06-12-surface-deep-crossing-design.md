# Surface→Deep Crossing — Story 105-2 Seam-Design Note

**Date:** 2026-06-12
**Author:** Architect (Emmanuel Goldstein)
**Story:** 105-2 — Deterministic surface→deep seam crossing (epic 105, Beneath Sünden)
**Status:** Approved design, pre-implementation
**Repos:** server, content *(scope amendment — see §6)*

## 1. Problem (from the 2026-06-12 live dive)

The ADR-106 procedural Deep is fully materialized (6 regions, 12 edges, the_siphon
setpiece) but unreachable in live play. The surface→deep crossing — the Story-59-12
handoff in `movement.py:201-269` that binds a PC to `graph.entrance_id` on descent —
is gated entirely behind the Haiku intent router emitting `movement{direction:deeper}`.
On turn 3 of the dive, the most explicit descent possible ("down the rope into the dark
tunnels … until my boots find rock") produced **no movement dispatch at all**; the
narrator papered the gap with a `location` patch inventing "The Dropmouth — The Deep"
as a surface sub-location — a confabulated dungeon with zero mechanical backing.

## 2. Root-cause analysis (three compounding defects, not one)

1. **The router is blind to the seam.** The movement classification prompt
   (`intent_router.py:162-169`) defines movement as relocation "between dungeon
   regions" and the router's state context never mentions that the PC's current
   region (`the_dropmouth`) has exactly one onward exit — a descent named
   "Down the Rope" (`cartography.yaml routes[], to_id: deep_descent`). The router
   was asked to recognize a descent it was never told existed.

2. **There is no deterministic backstop.** When the router misses, nothing
   downstream knows a crossing was expressed. `narration_apply.location_update`
   accepts the narrator's scene re-title; the 90-6 guard
   (`region.entry_skipped_sub_location`) prevents graph pollution but still
   applies the patch as a cosmetic re-title — so the confabulated deep is
   *narrated* even though it is mechanically nothing.

3. **The far side of the crossing is empty.** The materializer reserves
   expansion 0 for the entrance and refuses to compose content for it
   (`materializer.py:588`, `_stage_emit_room_yamls` runs only for
   `expansion_id >= 1`). Every expansion region gets a cookbook-composed
   `rooms/expNNN.rN.yaml` (prose + entity manifest); the entrance — the first
   procedural region every player lands in — is a bare
   `RegionNode(id="entrance", theme=…)` with no name, no prose, no entities,
   no encounter. There is nothing concrete to land in, which is why the
   narrator invented something.

## 3. Design decision

**The crossing is ordinary exit movement, and the first procedural region is a
real, authored room.** No seam registry, no second classifier, no new intent
router. Determinism comes from state — the seam region has exactly one onward
exit — not from re-reading the player's text.

Rejected alternatives:

- **Lexical descent floor** (keyword sniffer beside the Haiku router) — a second
  intent router by another name; brittle, violates the Zork doctrine's spirit,
  and re-introduces text classification as the gate.
- **Seam-kind registry** (generic `sentinel → resolver` abstraction for future
  static→procedural boundaries: orbital jumps, frontier expansion) — premature.
  One concrete intersection exists today; the pattern can be extracted when a
  second one is built. YAGNI.
- **Reject-and-reprompt only** (guard refuses the confabulated patch but never
  crosses) — strands a player who expressed descent perfectly well; the
  narrator's location patch *is* a relocation signal and should be honored
  mechanically, not bounced.

## 4. The three pieces

### Piece 1 — "Under the Rope": author the entrance room (content repo)

Author `genre_packs/caverns_and_claudes/worlds/beneath_sunden/rooms/entrance.yaml`
in the same on-disk shape the materializer emits for expansion rooms
(`room_yaml_emit.write_room_yaml` contract: `room_type`, `name`, `description`,
`entities`), which `room_file_loader.load_room_payload` already consumes.

- **Name:** "Under the Rope" (or in-world variant). The rope's end: frayed
  cord, the lit collar a long way up, bones and old gear of the unlucky,
  guano, dripping dark.
- **Content:** an easy-paced first encounter — rat-tier vermin from the
  shallow band of `bestiary.yaml`. Easy-peasy rat killing: the player's first
  mechanically real act in the deep, on purpose.
- **Freeze invariant holds:** `write_room_yaml` raises `FileExistsError` when
  the target exists and production passes `overwrite=False` — the engine will
  never clobber an authored entrance. This is pure content (the Jade path);
  zero engine code.
- **Doctrine:** every world that roots an ADR-106 dungeon SHOULD author its
  entrance room. The entrance is the threshold scene — it deserves authored
  weight (Diamonds and Coal: the first room of the deep is a diamond).

**Guardrail check:** no materializer changes. The materializer already skips
expansion 0; the authored file fills the hole it leaves by design.

### Piece 2 — Tell the router what the exits are (server)

- **Context, not prompt surgery:** include the PC's current region's actual
  onward exits in the router's per-turn game-state context — for
  `the_dropmouth`: `exits: [{name: "Down the Rope", kind: descent}]` (from
  cartography routes + adjacency). "Down the rope into the dark tunnels"
  becomes a trivial classification when the context literally names that exit.
- **Sole-exit relaxation in `movement.py`:** from a surface region whose only
  onward route is the seam route, any movement dispatch that is not `back`
  resolves as the descent. Today `direction != "deeper"` from the surface
  fails with `surface_no_route` ("the only way on from here is down") — keep
  that fail-loud for `back`/ambiguous-retreat, but let `deeper`,
  `toward_exit`, and exit-descriptor matches all cross. There is nowhere else
  to go; the state answers the question.
- The existing 59-12 handoff (bind to `entrance`, `movement_resolved_span`
  with `resolved_via="surface_descent"`, frontier transition) is **unchanged**
  and remains the single crossing implementation.

### Piece 3 — The guard crosses, it doesn't just reject (server)

In `narration_apply.location_update`, adjacent to the 90-6
`entry_skipped_sub_location` path:

**Invariant: a PC cannot be narrated across the seam.** While THIS PC's region
is a surface cartography region that owns a `deep_descent` route, a `location`
patch that mints a new scene heading (one that does not resolve to a known
cartography region) is treated as the relocation signal the router missed:

1. **Recover the crossing:** perform the real crossing — the same
   bind-to-`entrance` path movement.py uses (per-PC `pc_region` patch,
   frontier transition, spans). Re-anchor the scene to the *actual* entrance
   room's authored name and prose ("Under the Rope"), discarding the
   confabulated heading. The player ends up where the fiction said they went,
   but in the real room, mechanically bound.
2. **Or fail loud:** if the dungeon graph or entrance node is absent
   (`no_dungeon_entrance` condition), reject the patch with
   `region_entry_rejected_span` and an honest surface — never accept a
   procedural-deep scene title while `pc_region` is a surface lane.

**90-6 non-regression:** the existing `entry_skipped_sub_location` /
`_same_region_drift` behavior is untouched for non-seam regions and for
headings that are genuine POIs within the current region. The seam recovery
fires only when the region owns a `deep_descent` route AND the heading does
not resolve to known cartography. Real region changes still abandon anchored
confrontations; same-region drift still does not.

## 5. OTEL (the acceptance gate)

| Signal | Source | New/existing |
|---|---|---|
| `movement.resolved` `resolved_via="surface_descent"` | movement.py 59-12 handoff | existing |
| `movement.resolved` `resolved_via="narration_seam_recovery"` | Piece 3 recovery path | **new attribute value**, same span family |
| `frontier.region_transition` surface→`entrance` | per-PC patch path | existing (fires once bind is real) |
| `region_projection` engages (no "surface lane — no projection") | projection, post-bind | existing (falls out) |
| `region_entry_rejected` `reason="seam_crossing_unresolvable"` | Piece 3 fail-loud | **new reason value** |
| `dungeon.map_emitted` `discovered_regions > 0` | map emit, post-bind | existing (falls out) |

GM panel distinguishes router-driven crossings from guard-recovered ones; a
nonzero rate of `narration_seam_recovery` is the live signal that Piece 2's
router context needs tuning.

## 6. Scope amendments & dependencies

- **Repos:** `server` → `server,content` (Piece 1 is a content file).
- **AC coverage:** AC1 ← Pieces 2+3 (deterministic via state; router not the
  sole gate). AC2 ← Piece 3 fail-loud branch. AC3 ← §5 spans. AC4 ← 59-15
  scenario after 105-1 lands. AC5 ← Piece 3 non-regression constraint +
  existing surface-to-surface movement untouched (ropefoot ↔ the_dropmouth
  flows through cartography adjacency, not the seam path).
- **Materializer:** untouched (epic guardrail holds).
- **Dependency:** 105-1 (span-proof harness) must land before AC4
  verification; Pieces 1–3 are implementable and unit/behavior-testable
  before it.
- **MP note (out of scope, recorded):** Piece 3 binds THIS PC (per-PC
  `pc_region`), consistent with split-party semantics; full MP crossing
  choreography is a follow-up if live MP play surfaces it.

## 7. Test strategy (for TEA)

- **Behavior test (AC1):** beneath_sunden repro fixture — PC at
  `the_dropmouth`, movement dispatch with each of `deeper` / `toward_exit` /
  exit-descriptor "down the rope" → `pc_region == "entrance"`, span asserted.
- **Recovery test (AC1/AC2):** no movement dispatch; apply a narration result
  with `location: "The Dropmouth — The Deep"` while PC on seam region →
  PC bound to `entrance`, scene anchored to authored room name, recovery span
  fired; confabulated heading NOT in `discovered_regions`.
- **Fail-loud test (AC2):** same, with empty dungeon store → patch rejected,
  `seam_crossing_unresolvable` span, `pc_region` unchanged, no deep-titled
  scene applied.
- **Non-regression (AC5):** 90-6's existing tests stay green; ropefoot ↔
  the_dropmouth surface adjacency moves still resolve; non-seam region-mode
  worlds (oz/wonderland/the_circuit fixtures) hit `entry_skipped_sub_location`
  exactly as before.
- **Wiring test:** drive a full turn through
  `execute_intent_router_pre_narrator_pass` + `narration_apply` with the
  synthetic seam fixture and assert the span family — proving the guard is
  reachable from the production path, not just unit-importable.
- **Content validator:** entrance-room presence for dungeon-rooting worlds
  belongs in the pack validator (not pytest) per the no-content-in-unit-tests
  rule.
