---
parent: context-epic-77.md
workflow: tdd
---

# Story 77-3: Promote quest_anchors to first-class WorldStatePatch field + wire to orbital course

## Business Context

`quest_anchors` is the rarest kind of broken field: it has a **live reader and a
live consumer but no writer**. It is declared on the snapshot
(`game/session.py:736`), read into narrator context (`orchestrator.py:2413`),
shipped to the client (`server/session_helpers.py:1238`), and — critically —
**consumed by the orbital course planner** (`orbital/course.py:125,157`, ADR-130,
`implementation-status: live`), where each anchor body id is promoted to
`CourseSource.QUEST_OBJECTIVE` priority in the `<courses>` block the narrator
sees. But it is **not** a `WorldStatePatch` field (absent from the patch model
at `session.py:421`) and a grep for any assignment/append/`setattr` returns
nothing. The seed-at-creation hook (77-1) and the typed `record_quest` tool
(77-2) have nowhere to write an anchor.

For the wry_whimsy/oz playtest (the epic's founding failure), the world's entire
premise *is* an anchor — "the traveler wants only to go home" — and turn 13
showed `quest_anchors: []`. The objective the player most cares about could never
reach the one subsystem (ADR-130) that turns "go home" into a plotted Hohmann
course with an ETA and Δv that mechanics-first players (Sebastien, Jade) can
reason about.

This story does **exactly one thing**: promote `quest_anchors` to a first-class
writable `WorldStatePatch` field with a real apply path, and prove end-to-end
that a written anchor flows through the unchanged `compute_courses` consumer and
produces a course. **Promote, do not retire** (ADR-137 §Decision point 3,
§Alternatives "Retire `quest_anchors` entirely" — *rejected*): retiring the field
would delete a working course-planning input. `orbital/course.py` is the
downstream validator here, not a thing this story edits — it is how we know the
promotion actually fed something real rather than landing a dead patch field.

## Technical Guardrails

**Repo:** server only. **Workflow:** TDD — write the failing test first.

**The two production changes (both in `game/session.py`):**

1. **Add `quest_anchors` to `WorldStatePatch`** (the patch model at
   `session.py:421`, fields run l.430–452). Follow the established `None`-means-
   "no change" convention used by every sibling field, e.g.
   `quest_anchors: list[str] | None = None`. The model is
   `model_config = {"extra": "forbid"}` — the new field is the only way the patch
   will accept anchor data.

2. **Add a real apply path** in `apply_world_patch` (`session.py:1248`). Place the
   new branch alongside the existing quest/stakes branches —
   `quest_log` replace (`:1283`), `quest_updates` merge (`:1285`),
   `active_stakes` (`:1448`). Decide append-vs-replace deliberately and document
   it: anchors are a small id list the course planner unions, and the seed (77-1)
   plus `record_quest` (77-2) may each contribute one, so an **idempotent append**
   (skip ids already present — mirror the `discovered_routes` dedup-append at
   `:1444-1447`) is the natural shape. Whatever you choose, the test must pin it.

**OTEL span — `quest.anchor.added` (ADR-137 §AC-4, the GM-panel lie-detector for
this substrate).** Attributes per the ADR table: `anchor_id`, `quest_id`,
`resolved_to_beat` (bool). There is **no `quest.py` spans module today** — the
existing quest span (`SPAN_QUEST_UPDATE = "quest_update"`) lives in
`telemetry/spans/state_patch.py:29`, and dungeon quest seeding uses
`SPAN_QUEST_SEED = "quest.seed"` in `telemetry/spans/dungeon_setpiece.py`. Add the
new span following the **flat-span pattern** in `telemetry/spans/course.py`
(`Span.open(NAME, attrs={...})` + register the name in `FLAT_ONLY_SPANS`) — that
module is the closest sibling because it is the same subsystem family. Emit the
span from the apply branch, once per anchor actually added (do not emit for an id
that was deduped away — that would lie to the panel about a write that did not
happen). `resolved_to_beat` reflects whether the anchor id corresponds to a known
orbital body / beat at write time; if you cannot resolve that at the apply seam
without reaching into orbits config, set it from whatever resolution signal is
available and note the limitation in the AC test.

**The shape contract — `quest_anchors` is the beat/location-id bridge.** It is a
`list[str]` of body/location ids (see the field docstring at `session.py:732-735`
and `course.py:131` "a body is included if it appears in … `quest_anchors`").
`compute_courses` does `for bid in quest_anchors: if bid in orbits.bodies` — so an
anchor must remain a **plain id string the course planner can match against
`orbits.bodies`**. Do not change it to a structured object, a dict, or anything
the course planner cannot iterate as ids. Preserving this shape *is* the
wiring contract.

**`orbital/course.py` MUST NOT be touched.** It already accepts
`quest_anchors: list[str]` (`:125`) and assigns `CourseSource.QUEST_OBJECTIVE`
(`:157`). The two call sites already pass `quest_anchors=list(snapshot.quest_anchors)`
(`orchestrator.py:2413`, `narration_apply.py:1975`). The whole point of this story
is that the consumer needs **zero** changes — promoting the writer is sufficient.
If you find yourself editing `course.py`, stop: that is out of scope and signals a
wrong turn.

**Test discipline (per server CLAUDE.md "No Source-Text Wiring Tests").** Do not
grep production source as a wiring assertion. Use:
- a round-trip behavior test on the patch field (construct a `WorldStatePatch`
  with `quest_anchors`, call `apply_world_patch`, assert `snapshot.quest_anchors`);
- an **OTEL span assertion** (drive the apply, assert `quest.anchor.added` fired
  with the right attrs) — the refactor-stable wiring proof;
- the **end-to-end** proof: write an anchor via the patch, then call the *real,
  unchanged* `compute_courses(party_at=…, quest_anchors=list(snapshot.quest_anchors), …)`
  against a synthetic `orbits` fixture and assert the anchor body appears as a
  `CourseRow` with `source == CourseSource.QUEST_OBJECTIVE`. This is the wiring
  test the suite requires — it proves the promoted field reaches the live
  consumer and produces a course, not just that it round-trips in isolation.

Saves must still load: the field is `list[str]` with a `default_factory` on the
snapshot, so old saves lacking it stay loadable (legacy-save tolerance per project
doctrine). The new `WorldStatePatch` field defaulting to `None` is non-breaking.

## Scope Boundaries

**In scope:**
- Add `quest_anchors: list[str] | None` to `WorldStatePatch` (`session.py:421`).
- Add the apply branch in `apply_world_patch` (`session.py:1248`) with a pinned,
  documented append-vs-replace semantics.
- Add and emit the `quest.anchor.added` OTEL span (new flat span, `course.py`
  pattern) with attrs `anchor_id`, `quest_id`, `resolved_to_beat`.
- Tests: patch round-trip, span-fired assertion, and the end-to-end course-
  planner validation through the unchanged `orbital/course.py`.

**Out of scope:**
- **Seed-at-creation** (77-1) — deriving the first anchor from PC drive/calling at
  session init + `quest.seeded_at_creation`. This story provides the writable
  field that 77-1 writes *into*; it does not add the creation hook.
- **Typed `record_quest`/`set_stakes` tools** (77-2) — the narrator-facing
  create/evolve lane (ADR-102) + `quest.created`/`quest.updated`/`stakes.set`.
  This story does not add tools or touch `agents/tools/`.
- **One-mechanism cleanup** (77-4) — retiring the `quest_updates` extraction lane
  and stripping `/quest_log`+`/active_stakes` from `apply_world_patch`. Do **not**
  remove `quest_updates` or other existing patch branches in this story; only
  *add* `quest_anchors`.
- **Quest/objective UI panel** (77-5) — rendering the `quests` payload field.
- **wry_whimsy `seed_tropes` deck** (77-6, content) — the `active_seeds` carve-out.
- **Editing `orbital/course.py`** — it is the unchanged downstream validator.
  Touching it is a scope violation.
- **`active_stakes` / `quest_log` create affordances** — those belong to 77-1/77-2.

## AC Context

> No `acceptance_criteria` or `description` is set on story 77-3 in the sprint YAML
> (both return `null`). The criteria below are derived from ADR-137 §Decision
> point 3, §AC-4, and the epic's §Technical Architecture table; the implementing
> TEA/Dev should confirm against the epic and ADR. Flag for the next agent: the AC
> field is empty — these are reconstructed, not authored.

**AC-1 — `quest_anchors` is a first-class writable `WorldStatePatch` field.**
A `WorldStatePatch(quest_anchors=["the_gate"])` passed to `apply_world_patch`
mutates `snapshot.quest_anchors`. Test: construct the patch, apply it to a
snapshot fixture, assert the anchor id is present afterward. Verify the
`None`-means-no-change convention holds (a patch with `quest_anchors=None` leaves
existing anchors untouched). Pin the append-vs-replace semantics you implement —
ADR-137 frames the field as fed by *both* the creation seed and `record_quest`,
which argues for idempotent append (no duplicate ids), mirroring the
`discovered_routes` dedup-append at `session.py:1444-1447`.

**AC-2 — the `quest.anchor.added` OTEL span fires on every real anchor write.**
Driving an anchor write through `apply_world_patch` emits `quest.anchor.added`
with attributes `anchor_id`, `quest_id`, `resolved_to_beat` (bool), per ADR-137
§AC-4. Test via an in-memory span exporter (the `Span.open` / `tracer` pattern the
existing span tests use). The span must *not* fire for an id that was deduped away
(an append that added nothing is not an "anchor added"). This is the GM-panel
lie-detector that proves the substrate is engaged, not improvised. Ambiguity to
resolve: how `quest_id` is sourced at the patch seam — `WorldStatePatch` carries
`quest_log`/`quest_updates` (dicts keyed by quest id) but no explicit
anchor→quest link today; the implementer must decide whether `quest_id` comes
from a co-submitted quest entry, a new patch field, or is left empty when the
writer (77-1/77-2) does not supply one. Choose the simplest shape that lets 77-1
and 77-2 populate it, and document the choice.

**AC-3 — the promoted anchor reaches `orbital/course.py` and produces a course
(end-to-end).** After writing an anchor via the patch, calling the **unchanged**
`compute_courses(party_at=<body>, in_scope_body_ids=…, recent_body_mentions=…,
quest_anchors=list(snapshot.quest_anchors), orbits=<fixture>)` returns a
`CourseRow` for the anchor body with `source == CourseSource.QUEST_OBJECTIVE`.
This is the load-bearing wiring test: it proves the writer→reader→consumer chain
is whole (`session.apply_world_patch` → `snapshot.quest_anchors` → `compute_courses`
→ `QUEST_OBJECTIVE` course) without modifying the consumer. The orbits fixture
must include the anchor body in `orbits.bodies` (else `compute_courses` skips it —
that is the planner's own contract at `course.py:157-159`, not a bug to fix here).

## Assumptions

- `quest_anchors` remains a `list[str]` of orbital-body/location ids end-to-end;
  the course planner's `if bid in orbits.bodies` match (`course.py:158`) is the
  reason the shape cannot change to a structured object.
- Old saves without the field stay loadable via the snapshot's
  `Field(default_factory=list)` (`session.py:736`); the new patch field defaults
  to `None` and is non-breaking.
- 77-1 (seed) and 77-2 (`record_quest`) are the writers that will *call* this
  apply path; this story delivers the field + path + span they target, and does
  not itself populate anchors at creation or via a tool.
