---
parent: context-epic-72.md
workflow: tdd
---

# Story 72-3: MM NPC provenance through the injection seam

**ID:** 72-3 | **Epic:** 72 (NPC Identity Hardening) | **Points:** 3 | **Type:** bug | **Repo:** sidequest-server

Adds a `manual_origin`/provenance marker to `NpcPatch` so Monster-Manual-authored NPCs
(ADR-059 pre-generated, game-state-injected creatures and humans) are distinguishable from
narrator-invented NPCs, and threads that marker through materialization (`_npc_from_patch`)
and re-merge (`_merge_npc_patch`) onto the canonical `Npc` in `snapshot.npcs`, with an OTEL
attribute carrying the provenance so the GM panel can attribute MM-seeded NPCs.

---

## Business Context

Epic 72 (NPC Identity Hardening) closes a split-brain identity model where the same logical
NPC can exist twice — as an identity scaffold in `snapshot.npc_pool` and as mechanical state
in `snapshot.npcs` — with no invariant binding them and no provenance on where an NPC *came
from*. ADR-059's Monster Manual is one of the upstream authors: it pre-generates creatures
and humans server-side and injects them into game state as `Npc` records (not tool calls,
not "available list" prose — see `monster_manual_inject.py` doctrine note, lines 1-9). The
narrator is *also* an author of `Npc` records, minting invented NPCs off its own prose.

Today, once an MM-seeded NPC lands in `snapshot.npcs`, nothing distinguishes it from a
narrator-invented one. `Npc.pool_origin` only records the `NpcPoolMember.name` an NPC was
*promoted from* — it does not say "this came from the Monster Manual." That gap matters for
two consumers:

- **The GM panel (Keith / dev observability).** Per the OTEL Observability Principle, every
  subsystem decision must be inspectable so Keith can tell whether the MM actually seeded an
  NPC or whether the narrator improvised one with the same name. Without a provenance marker
  on the materialization span, the lie-detector can't attribute an NPC to the MM seam. (This
  is dev-side observability — *not* a Sebastien/Jade player-facing surface. Do not frame
  `manual_origin` as a "Sebastien's lie-detector" feature; it is a Keith/dev tool.)
- **Downstream identity reconcile (72-1/72-2).** A developed, tier-escalated NPC's behavior
  should differ depending on whether it has an authored MM stat block behind it or is pure
  narrator improv. Provenance is the precondition for that distinction; this story only
  *records* it, it does not branch on it.

This is a **bug** story: the MM injection seam silently erases authorship. The fix is to
carry one provenance flag, end to end, and emit it on OTEL.

---

## Technical Guardrails

### The real seam (verified)

- **`NpcPatch`** — `sidequest/game/session.py:282`. The injection patch, used by two emitters
  (narrator-declared NPCs and the MM seeder, per its docstring at lines 285-296). `model_config
  = {"extra": "forbid"}`, so the new field must be a declared model field, not an ad-hoc dict
  key. All creature-shape fields are `| None = None` optional; follow that convention.
- **`_npc_from_patch`** — `sidequest/game/session.py:1501`. Builds a fresh `Npc` from a patch
  when no NPC of that name exists yet. The new provenance must be set on the returned `Npc`
  here. Note the existing `is_creature` signal (lines 1505-1507) and the born-hostile default
  at line 1533 (`disposition=-20 if is_creature else 0`) — **72-5 owns that default; do not
  touch it here.**
- **`_merge_npc_patch`** — `sidequest/game/session.py:1466`. The *collision* path: when an
  `Npc` of the same `core.name` already exists, `apply_world_patch` (lines 1429-1435) calls
  this merge instead of materializing fresh. This method currently copies flavor + creature
  fields but has **no provenance handling** — it must also carry `manual_origin` so an MM
  patch re-encountered (or colliding with a prior narrator-invented `Npc` of the same name)
  records its authorship.
- **`Npc`** — `sidequest/game/session.py:120`. The canonical record. It already carries
  `pool_origin: str | None = None` (line 151) as a provenance field; the new marker lives
  alongside it. Decide a representation (e.g. a `manual_origin: bool = False` flag, or a
  provenance enum) and keep it consistent across `NpcPatch` → `Npc`. `extra="forbid"` here
  too — declare the field.

### MM emitters that set the marker (verified)

The MM injection builders in `sidequest/server/dispatch/monster_manual_inject.py` are where
`manual_origin` should be set *true* on the patch:

- `_human_patch` (line 157) — Available/Active human Manual NPCs.
- `_creature_patch_from_enemy` (line 229) — encounter creatures.

Both already construct `NpcPatch(...)`. The narrator path (`commands.py:374`, and the
narrator's `npcs_present` tool emissions) must **not** set the marker — that's the negative
edge case below.

### Materialization → merge flow (verified)

`apply_world_patch` (`session.py:1429-1435`) is the single junction: for each `npc_patch` in
`patch.npcs_present`, it either merges into an existing `Npc` (`_merge_npc_patch`) or
materializes a new one (`_npc_from_patch`). Both legs must preserve provenance. The
`monster_manual_inject.inject()` function (line 279) bundles MM patches into a
`WorldStatePatch(npcs_present=...)` and calls `apply_world_patch` (line 334) — that is the
production call path your wiring test should drive.

### OTEL (mandatory — this is the lie-detector leg)

NPC spans live in `sidequest/telemetry/spans/npc.py`. The materialization/merge of an MM NPC
must emit `manual_origin` as a span attribute so the GM panel can attribute the NPC. The
existing `SPAN_MONSTER_MANUAL_INJECTED` span (`monster_manual_inject.py:314`, defined in
`telemetry/spans/monster_manual.py`) already fires on the inject pass — extending it (or the
per-NPC registration/referenced span in `npc.py`) with a provenance attribute is the natural
home. Match the existing attribute-dict shape; do not invent a parallel span if an existing
one already covers the materialization decision point.

### Server test rule

Per `sidequest-server/CLAUDE.md` "No Source-Text Wiring Tests": assert **behavior and spans**,
not source text. Drive a real `WorldStatePatch` through `apply_world_patch` (or
`monster_manual_inject.inject`) and assert (a) the materialized `Npc.manual_origin` is set,
and (b) the OTEL span carries the provenance attribute. Use OTEL span assertions or
fixture-driven behavior tests (the `tests/server/test_location_description_emit.py` shape).
Do **not** grep `session.py`/`monster_manual_inject.py` source as a wiring assertion.

---

## Scope Boundaries

**In scope:**
- New `manual_origin`/provenance field on `NpcPatch` (`session.py:282`).
- Carrying it through `_npc_from_patch` (1501) onto a fresh `Npc`.
- Carrying it through `_merge_npc_patch` (1466) onto an existing colliding `Npc`.
- Setting it `true` in the MM emitters `_human_patch` / `_creature_patch_from_enemy`
  (`monster_manual_inject.py`).
- A provenance attribute on the relevant OTEL span (materialization / inject).
- One wiring test proving the marker reaches `snapshot.npcs` via the production inject path.

**Out of scope (do NOT touch):**
- **72-4 (namegen routing):** routing narrator-invented bare names through ADR-091
  culture-bound namegen. The invented-name mint path is 72-4's; this story only *abstains*
  from marking it `manual_origin`.
- **72-9 (OCEAN/belief_state wiring):** seeding OCEAN/`belief_state` on invented NPCs.
- **72-5 (born-hostile default):** the `disposition=-20 if is_creature else 0` line at
  `_npc_from_patch:1533` is 72-5's. Leave disposition seeding alone.
- **72-1/72-2 (development pipeline + reconcile):** provenance is a *precondition* for these
  but this story does not branch behavior on `manual_origin` — it only records it.
- The two-store reconcile / `npc_pool` join (72-2) — not this seam.

---

## AC Context

No explicit ACs existed; these are derived and testable. All assertions are behavioral/span
(server rule), not source-text.

**AC1 — `NpcPatch` carries a provenance marker.**
`NpcPatch` (`session.py:282`) gains a declared `manual_origin` (or equivalent provenance)
field, optional/defaulted so existing narrator-emitted patches and fixtures round-trip
unchanged. Test: construct an `NpcPatch` with and without the marker; both validate under
`extra="forbid"`; the default for an unmarked patch is the non-MM value.

**AC2 — The marker survives merge into the canonical `Npc`.**
An MM-marked patch driven through `apply_world_patch` materializes (`_npc_from_patch`) an
`Npc` whose provenance reads as manual-origin. The same marked patch applied when an `Npc`
of that name already exists (`_merge_npc_patch`) also records manual-origin on the existing
record. Test: fixture snapshot + `WorldStatePatch(npcs_present=[marked_patch])` →
`apply_world_patch` → assert `snapshot.npcs[...].manual_origin` is set, in both the
fresh-materialize and the name-collision branches.

**AC3 — An MM-injected NPC is queryable as manual-origin downstream.**
After `monster_manual_inject.inject()` runs against a Manual fixture, the NPCs it materialized
into `snapshot.npcs` are distinguishable as manual-origin by reading the `Npc` field — no
heuristic on `creature_id`/name needed. Test (wiring): drive the real `inject()` path with a
seeded `MonsterManual` fixture; assert the resulting `snapshot.npcs` entries carry the marker.
This is the integration/wiring test the suite requires.

**AC4 — OTEL span carries provenance.**
The materialization/inject decision emits an OTEL span attribute recording the provenance, so
the GM panel can attribute MM-seeded NPCs. Test: drive the inject path under a span-capture
fixture; assert the emitted span exposes the `manual_origin` attribute with the expected value.

**Edge cases (must be covered):**
- **E1 — Narrator-invented NPC must NOT get `manual_origin`.** An `NpcPatch` emitted by the
  narrator path (no MM marker set) materializes an `Npc` whose provenance reads as
  *not* manual-origin. Negative assertion guarding against accidental default-true.
- **E2 — Merge collision: MM NPC vs invented NPC of same name.** When an MM-marked patch
  collides with an already-present narrator-invented `Npc` of the same `core.name`
  (`_merge_npc_patch` path), the MM provenance is recorded on the surviving record. Define and
  test the deterministic resolution: MM authorship is authoritative on the marker (the engine
  should not silently keep "invented" when an authored MM patch arrives). Document the chosen
  direction in the test name so the behavior is pinned. (Symmetric reverse — narrator patch
  arriving for an NPC already marked manual-origin — should not *clear* the MM marker.)

---

## Assumptions

1. **Representation.** `manual_origin` is modeled as a simple provenance marker on both
   `NpcPatch` and `Npc` (mirroring the existing `pool_origin: str | None` convention at
   `session.py:151`). A boolean flag is the minimal shape; an enum is acceptable if it stays
   consistent across patch → npc → span. The story does not require reconciling `pool_origin`
   and `manual_origin` into one provenance object — that's 72-2's concern.
2. **MM emitters are the only `true` source.** Only `_human_patch` and
   `_creature_patch_from_enemy` in `monster_manual_inject.py` set the marker `true`. The
   `commands.py:374` debug-command path and the narrator's `npcs_present` tool emissions leave
   it at the non-MM default. (If any other production builder constructs MM patches, it must
   set the marker — verify no third emitter exists before finalizing.)
3. **Collision authority.** On a name collision between an MM patch and an existing invented
   `Npc`, MM authorship wins the marker (an authored stat block is "more real" than narrator
   improv). This is the documented default; confirm with epic owner if a different policy is
   desired, but do not leave it silently undefined (No Silent Fallbacks).
4. **Span home.** The provenance attribute attaches to an existing materialization/inject span
   (`SPAN_MONSTER_MANUAL_INJECTED` or the per-NPC `npc.py` registration/referenced span) rather
   than a brand-new span, to avoid GM-panel dashboard churn. If no existing span covers the
   per-NPC materialization decision cleanly, a new span in `telemetry/spans/npc.py` is
   acceptable — but prefer extension.
5. **No behavior branches on provenance yet.** This story records and surfaces `manual_origin`;
   it does not change disposition, development, reconcile, or narrator behavior based on it.
   Those are 72-1/72-2/72-5/72-9.
