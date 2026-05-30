---
parent: context-epic-72.md
workflow: tdd
---

# Story 72-2: Preserve disposition on promotion + reconcile stores on load

**Epic:** 72 (NPC Identity Hardening) · **Points:** 5 · **Type:** bug · **Repo:** sidequest-server · **Workflow:** tdd

## Business Context

An NPC in SideQuest is modeled twice with no consistency invariant binding the
two representations: `snapshot.npc_pool` (`list[NpcPoolMember]`, identity
scaffold — name/role/pronouns/appearance/`drawn_from`/`observation_pending`,
**no mechanical state**) and `snapshot.npcs` (`list[Npc]`, mechanical state —
`CreatureCore`, HP, **`disposition: Disposition`**, `BeliefState`, `ocean`,
`pool_origin`). The only key joining them is a case-folded name string matched
ad hoc at each call site. Disposition — the numeric relationship score that
ADR-020 maps to a friendly/neutral/hostile attitude — lives **only** on `Npc`,
never on `NpcPoolMember`.

Two defects ride on this seam, and this story closes both:

1. **Disposition is reset on pool→Npc promotion.**
   `_promote_pool_member_to_npc` (`sidequest/server/narration_apply.py:916`)
   builds a fresh `Npc(...)` with **no `disposition=` argument**, so the field
   falls back to `default_factory=Disposition` → value `0` (neutral). If the
   same logical person already had a non-neutral disposition recorded (e.g. an
   `Npc` the playgroup made friendly that was re-minted, or any future path that
   stamps disposition onto the scaffold), promotion silently flattens the
   relationship back to neutral. A bartender the party spent ten turns
   befriending re-promotes as a stranger.

2. **The two stores are never reconciled on load.** `migrate_legacy_snapshot`
   (`sidequest/game/migrations.py:290`) runs S1–S4 sub-migrations but has **no
   pass that reconciles `npcs` against `npc_pool`** for the same logical name.
   A save can carry an `Npc` with `pool_origin="Mara"` (disposition +18,
   friendly) *and* a separate `NpcPoolMember(name="Mara")` whose role/pronouns
   have since drifted, with nothing enforcing single-source-of-truth. On load
   the divergent state survives, and the next call site that case-folds names
   gets whichever record it happens to hit first.

**Why this matters to the playgroup:** Sebastien and Jade are mechanics-first
players who want disposition/attitude legible in the player UI; a relationship
that silently resets to neutral on an internal promotion is exactly the kind of
"Claude is winging it" failure the OTEL lie-detector exists to catch. Keith (as
player) must be able to trust that an NPC the table invested in stays invested
in — disposition is the spine of NPC continuity. This story makes promotion and
load **disposition-preserving and reconciled**, with OTEL on both legs so the GM
panel can verify the fix fired.

## Technical Guardrails

**Primary seams (verified at authoring time):**

- **Promotion:** `_promote_pool_member_to_npc(member: NpcPoolMember) -> Npc`
  at `sidequest/server/narration_apply.py:916`. Today it constructs
  `CreatureCore` + `Npc(core=..., pronouns=..., appearance=...,
  pool_origin=member.name)` with **no disposition carried**. Called from
  `resolve_status_target` (same file, ~line 990), which appends the promoted
  `Npc` to `snapshot.npcs` and publishes the `state_transition`
  `field="npcs", op="promoted_from_pool"` watcher event (~line 992).
- **Load-time reconcile:** `migrate_legacy_snapshot`
  (`sidequest/game/migrations.py:290`) iterates a tuple of sub-functions
  (`_migrate_s1…s4`), each returning either `None` (no-op) or a dict of OTEL
  attributes merged into a single `SPAN_SNAPSHOT_CANONICALIZE` span emitted only
  when something was rewritten. `_migrate_s2_npc_registry_split` (line 73) is the
  existing NPC-store seam and the model to mirror: it case-folds names, merges
  fields onto a matched `Npc` dict, counts outcomes into OTEL attributes, and
  is **non-mutating of its input** (operates on the deep-copied `out`). Add the
  reconcile pass as a new sub-function in this same tuple so it shares the
  canonicalize span and the dict-in/dict-out contract (it runs **before**
  pydantic re-hydrates the snapshot, so it operates on raw dicts, not model
  instances).
- **Disposition type:** `Disposition` (`sidequest/game/disposition.py`) — a
  clamped `-100..+100` integer wrapper with `.attitude()` → `Attitude`
  (`friendly`/`neutral`/`hostile`, ADR-020). Pydantic coerces a bare int to
  `Disposition` and serializes back to a bare int, so in raw-dict (migration)
  space disposition is an **integer**, and in model space it is a `Disposition`.
  Reconcile logic must compare numeric values, not wrapper identity.
- **Models:** `Npc` (`sidequest/game/session.py:120`) has
  `disposition: Disposition = Field(default_factory=Disposition)` and
  `pool_origin: str | None`. `NpcPoolMember` (`sidequest/game/npc_pool.py:17`)
  has **no disposition field** (`model_config = {"extra": "forbid"}`). The join
  key everywhere is the **case-folded name** (`name.casefold()`), matching the
  pattern already in `_migrate_s2_npc_registry_split`.

**OTEL (required — both legs):** All NPC spans live in
`sidequest/telemetry/spans/npc.py`; the disposition-shift span route is at
`session.py:1410` (`SPAN_DISPOSITION_SHIFT` → `state_transition`). Per the epic
span plan:
- A **reconcile span on load** recording members merged / conflicts resolved
  (mirror the `_migrate_s2_*` attribute-dict style so it folds into
  `SPAN_SNAPSHOT_CANONICALIZE`, or emit a dedicated NPC reconcile span — author's
  choice, but it MUST fire and carry counts).
- A **disposition-preserved attribute** on the existing `promoted_from_pool`
  watcher event (e.g. `disposition`, `attitude`) so the GM panel can see the
  value carried through promotion rather than reset.

**Server testing rule (CLAUDE.md "No Source-Text Wiring Tests"):** Assert
**behavior and spans**, never grep production source. The wiring test for this
story is an **OTEL span assertion** (drive a promotion / drive a load with a
divergent fixture, assert the reconcile span fired and the
`promoted_from_pool` event carries the preserved disposition) and/or a
**fixture-driven behavior test** (synthetic snapshot → real
`_promote_pool_member_to_npc` / `migrate_legacy_snapshot` invocation → assert the
resulting disposition value). Reflection-based field checks
(`inspect`/`model_fields`) are acceptable if a field needs to be added.

**Project principles:** No Silent Fallbacks — a reconcile conflict must be
resolved by an explicit, recorded rule (and counted in OTEL), never by silently
picking whichever record loads first. No Stubbing — wire the reconcile pass into
the live `migrate_legacy_snapshot` tuple; an unwired helper is dead code.

## Scope Boundaries

**In scope:**
- Make `_promote_pool_member_to_npc` (and its `resolve_status_target` call site)
  **preserve disposition** through pool→Npc promotion — i.e. promotion must not
  reset a known disposition to neutral-0. Where the disposition is carried from
  (an existing same-name `Npc`, a scaffold-side value, or a passed-in argument)
  is a design decision for the implementer, but the round-trip
  (known-disposition in → same disposition out) must hold.
- Add a **load-time reconcile pass** alongside `migrate_legacy_snapshot` that
  brings `npcs` and `npc_pool` to a consistent, single-source-of-truth state for
  each logical (case-folded) name, with no orphaned or divergent disposition.
- **OTEL on both legs:** reconcile span (with merge/conflict counts) on load; a
  disposition-preserved attribute on the `promoted_from_pool` event.
- Handle the three state edge cases enumerated under AC Context below.

**Out of scope (do NOT touch):**
- **72-1** — reviving the dormant *development* pipeline (interest increment,
  `resolution_tier` escalation, emergent disposition **drift**). This story
  preserves and reconciles an *existing* disposition; it does not make
  disposition *evolve*.
- **72-6** — `npc_pool` growth cap / LRU / stale-`observation_pending` prune.
- **72-3/72-4/72-5/72-7/72-8/72-9/72-10** — provenance threading, namegen
  routing, born-hostile default fix, authoritative drift overwrite, last-seen
  stamping, OCEAN/belief enrichment, gate-ordering assert. Where reconcile
  *reads* fields those stories own (e.g. `drawn_from`, `pronouns`), preserve them
  unchanged — do not start owning them here.
- Schema migrations / Alembic, UI, daemon. Reconcile operates on the in-memory
  snapshot dict during load canonicalization, not on Postgres DDL.

## AC Context

No explicit ACs exist in the story; the following are **derived** and testable.
TEA/Dev should refine wording during red-phase test authoring.

- **AC1 — Disposition survives promotion (round-trip).** Given a logical NPC with
  a known non-neutral disposition (e.g. +18 → friendly) that is promoted from the
  pool to an `Npc` via `_promote_pool_member_to_npc` /
  `resolve_status_target`, the resulting `Npc.disposition` equals the
  pre-promotion value (attitude unchanged). A neutral/unknown source still
  promotes to a valid neutral default — preservation must not regress the
  no-prior-disposition case.

- **AC2 — Stores reconciled to a consistent state on load.** After
  `migrate_legacy_snapshot` runs on a snapshot where the same case-folded name
  appears in both `npcs` and `npc_pool`, the two stores are left in a single
  source-of-truth state: no record carries a disposition that diverges from the
  authoritative one, and no logical NPC is left orphaned across the boundary.

- **AC3 — Edge case: pool-only.** A name present in `npc_pool` but **not** in
  `npcs` reconciles without error and without fabricating a spurious `Npc`
  (the scaffold has no mechanical state to reconcile; it remains a valid,
  re-citable pool member). No silent drop.

- **AC4 — Edge case: npcs-only + divergent disposition.** A name present in
  `npcs` but **not** in `npc_pool` (or present in both with divergent
  disposition between the two representations) resolves to the authoritative
  disposition by an explicit, recorded rule — the `Npc` mechanical record is
  authoritative for disposition — and the divergence is counted in the reconcile
  OTEL span (no silent first-wins pick).

- **AC5 — OTEL fires on both legs (wiring test).** Driving a real promotion emits
  the `promoted_from_pool` event carrying the preserved disposition attribute;
  driving a real load of a divergent fixture emits a reconcile span carrying
  merge/conflict counts. These span assertions are the refactor-stable wiring
  proof for this story (no source-text grep).

## Assumptions

- **The case-folded name remains the join key.** This story does not introduce a
  stable NPC id (that is the epic's broader thesis but not this story's deliverable).
  Reconcile and promotion match on `name.casefold()`, consistent with
  `_migrate_s2_npc_registry_split` and the existing call sites.
- **`Npc` is authoritative for disposition** in a conflict, because
  `NpcPoolMember` has no disposition field today and the mechanical record is the
  one ADR-020 deltas land on (`session.py:1398-1410`). If review prefers a
  different conflict rule, it must still be explicit and OTEL-recorded (No Silent
  Fallbacks) — the AC requires *a* recorded rule, not specifically Npc-wins.
- **Reconcile runs in raw-dict space** (before pydantic re-hydration), so it
  reads/writes integer disposition values, mirroring how `_migrate_s2_*`
  manipulates `out["npcs"]`/`out["npc_pool"]` dicts. The new sub-function follows
  the same `dict -> dict | None` (None = no-op) contract and shares the
  `SPAN_SNAPSHOT_CANONICALIZE` span unless the implementer adds a dedicated NPC
  reconcile span.
- **No saves to migrate in anger** (per project memory): correctness of the
  reconcile rule on constructed fixtures is the bar, not backward-compat with a
  large corpus of legacy saves. Prefer a clean, explicit reconcile over
  defensive preservation of malformed legacy shapes — but still fail loud on
  genuinely corrupt input rather than silently dropping it (mirror the
  `s2_malformed_npcs_skipped` / `s2_nameless_entries_dropped` counted-skip
  pattern).
- **This story does not make disposition *change*** — it preserves and reconciles
  an existing value. Any emergent drift is 72-1's deliverable. A test that
  expects disposition to *move* as a function of engagement is out of scope here.
