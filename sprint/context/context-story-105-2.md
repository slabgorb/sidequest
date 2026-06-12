# Story 105-2 Context

## Title
Deterministic surface→deep seam crossing — when a PC in a cartography region that owns a deep_descent route expresses descent, bind to the dungeon entrance (or fail loud), NOT gated on the Haiku intent router alone; forbid location_update from inventing procedural-deep sub-locations on the surface lane; emit OTEL proving pc_region reaches a procedural node + discovered_regions>0 + projection engages. 59-15 goes green on span-proof

## Metadata
- **Story ID:** 105-2
- **Type:** bug
- **Points:** 5
- **Priority:** p1
- **Workflow:** tdd
- **Repo:** server
- **Epic:** Beneath Sünden — make the procedural Deep reachable in live play (ADR-106 surface→deep crossing)

## Problem

In live beneath_sunden play the ADR-106 procedural Deep is fully materialized (6 regions,
12 edges, the_siphon setpiece — see epic Evidence) but **unreachable**. The surface→deep
crossing — the `movement.py` Story-59-12 handoff that binds the PC to `graph.entrance_id`
when descending from the surface lane — is gated **entirely** behind the Haiku intent router
classifying the action as `movement{direction:deeper}`. There is no deterministic backstop.

Measured on the 2026-06-12 dive:
- Turn 2 ("climb down the shaft into the Deep"): `movement` fired but from `ropefoot`
  resolved to the **adjacent surface region** `the_dropmouth` (the rim), not the deep.
- Turn 3 ("down the rope into the dark tunnels … until my boots find rock"): `movement`
  **did not fire** (activity grid last-seen T#2). The intent router misclassified the most
  explicit descent possible; the narrator then silently changed the scene to
  "The Dropmouth — The Deep" via a `location` patch — a sub-location POI of the **surface**
  region — inventing passages and a lurking threat with zero mechanical backing.
- Result: `current_region` stuck at `the_dropmouth`; `discovered_regions` never grows past
  the two surface regions; region projection refuses ("surface lane — no projection") every
  turn; `total_beats_fired=0`, `encounter=None`. The player experiences a confabulated
  dungeon while the real one sits behind the seam.

`the_dropmouth` is the seam region — its cartography owns `Down the Rope → to_id:
deep_descent`. A descent expressed from it should deterministically cross into the procedural
`entrance`, or fail loud. It does neither.

## Technical Approach

**DESIGN-BEARING — requires an Architect seam-design note before Dev** (the Man in Black
already holds the diagnosis). The note must decide between, at minimum:
- a deterministic crossing trigger keyed on "PC is in a cartography region that owns a
  `deep_descent`-class route AND the action expresses descent" (independent of, or as a
  fallback to, the intent-router `movement{deeper}` path), vs.
- hardening the intent-router path with a loud-fail backstop.

Candidate seams (for the design note to confirm, not prescriptive):
- `sidequest-server/sidequest/agents/subsystems/movement.py:201-267` — the existing 59-12
  surface→deep handoff; today only reached when the router emits `movement{deeper}`.
- `sidequest-server/sidequest/server/narration_apply.py` `location_update` — must be
  *prevented* from minting a procedural-deep scene on the surface lane (reuse the
  `region.entry_skipped_sub_location` signal that 90-6 already keys on; do not regress 90-6).
- `intent_router.py:162-169` — movement classification prompt (the single point of failure).

**Guardrail:** No ADR-106 materializer changes. Binding/crossing only.

## Scope

- **In scope:** the deterministic surface→deep crossing (or loud-fail) from a seam-route
  cartography region; preventing `location_update` from inventing procedural-deep
  sub-locations on the surface lane; the OTEL spans that prove the crossing.
- **Out of scope:** dungeon generation / materializer; the headless driver fix (105-1);
  multiplayer split-party crossing semantics beyond what the solo repro needs (note any
  MP follow-up, don't expand scope here).

## Acceptance Criteria

1. **Deterministic crossing:** when a PC whose `current_region` is a cartography region that
   owns a `deep_descent`-class route expresses descent, the engine binds the PC's `pc_region`
   to the dungeon `entrance` node — it does NOT depend solely on the intent router emitting
   `movement{deeper}`. (Behavior test on the beneath_sunden repro: ropefoot → the_dropmouth →
   `entrance`.)
2. **No silent fallback:** if the crossing cannot resolve (no graph / no entrance), it fails
   loud (error directive / honest-surface), and `location_update` does NOT mint a
   procedural-deep scene (e.g. "The Deep") while `current_region` is still a surface lane.
   (Regression guard reusing the 90-6 `region.entry_skipped_sub_location` path.)
3. **OTEL proof (the gate):** the crossing emits a span showing the PC bound to a procedural
   node; after descent `discovered_regions` includes a procedural region (`entrance`/
   `exp00N.rN`) and `region_projection` engages (no "surface lane — no projection" once in
   the deep). `frontier.region_transition` fires on the surface→deep hop.
4. **Live span-proof via 59-15:** with 105-1 landed, `scenarios/beneath_sunden_engagement.yaml`
   reaches the deep — `movement.resolved` (surface_descent) + region transition into a
   procedural node, and the lie-detector (`dispatch_engagement.*.mismatch`) stays at 0.
5. **No regression** to 90-6 (real region change still abandons an anchored confrontation;
   same-region drift still does not) or to surface-to-surface movement (ropefoot ↔
   the_dropmouth still works).

## Dependencies
- **Depends on 105-1** (span-proof harness) for AC4 live verification.
- **Architect seam-design note** is a prerequisite to Dev (design-bearing change).
