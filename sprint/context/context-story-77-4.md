---
parent: context-epic-77.md
workflow: tdd
---

# Story 77-4: One-mechanism cleanup — retire quest_updates lane + strip apply_world_patch quest/stakes paths

## Business Context

This is the **"one mechanism" payoff** of epic 77 (Quest & Stakes Substrate). The
epic exists because the wry_whimsy/oz playtest (2026-06-02) ran 13 turns against a
world whose *entire premise is a campaign spine* yet finished with `quest_log: {}`,
`quest_anchors: []`, `active_stakes: ""` — convincing narration with zero
mechanical backing. ADR-137's root-cause audit found the spine had **three
competing, mostly-broken write mechanisms** and no single create/evolve lane:

- the `quest_updates` extraction lane (status-only — can update an existing quest,
  can't mint one),
- the **deprecated** `apply_world_patch` escape hatch (the narrator is explicitly
  *told not to use it* for stakes),
- the trope handshake (needs a *resolved* trope, never fires in a prose-only pack).

Story **77-2** introduces the single replacement: typed `record_quest` /
`set_stakes` tools (ADR-102), plus the creation seed (77-1). Once that one
mechanism exists, the other two lanes are **redundant duplicate writers** to the
same fields. This story **retires them**: it removes the `quest_updates`
extraction/merge lane and strips the quest/stakes path from the escape hatch, so
quest and stakes mutations flow through exactly **one** create/evolve mechanism.

Why it matters beyond tidiness:

- **Saves stop carrying quests written by a retired lane.** If the old
  `quest_updates` merge keeps writing `snapshot.quest_log` after `record_quest`
  ships, two writers race the same field and a save can persist a quest the typed
  tool never minted — exactly the inconsistency the consolidation exists to kill.
- **The deprecated escape hatch is closed for good.** Leaving `/active_stakes` on
  `apply_world_patch` keeps alive a path the narrator was instructed to avoid;
  removing it makes the typed `set_stakes` tool the *only* way to set stakes, so
  "the narrator wrote stakes through a back door" becomes impossible rather than
  merely discouraged.
- **Dead code goes in the same PR** (CLAUDE.md "Delete dead code in the same PR").
  This story is the deletion half of the epic; it is not a follow-up cleanup to be
  deferred.

End state (ADR-137 §One-mechanism consolidation): one create/evolve lane
(`record_quest`/`set_stakes` + the creation seed), zero discouraged duplicate
writers.

> **Numbering caveat (from epic context + ADR-137).** ADR-137 §Implementation
> Stories was written when the design story was 77-1, so its internal table
> numbers this cleanup story **77-5**. After the design story archived, the
> implementation stories were re-promoted: ADR 77-5 → sprint **77-4** (this
> story), ADR 77-3 → sprint **77-2** (typed tools, the lockstep dependency). Read
> the ADR's "77-5 — One-mechanism cleanup" row and its "gate 77-5 on 77-3" line as
> **this** story gating on **sprint 77-2**.

## Technical Guardrails

- **LOCKSTEP WITH 77-2 — the load-bearing ordering hazard.** ADR-137 is explicit:
  *"Migration (77-5/sprint-77-4) must land in lockstep with 77-3/sprint-77-2 or
  saves could carry quests written by a retired lane; gate 77-5 on 77-3."* This
  story may only land **after** the typed `record_quest`/`set_stakes` tools exist
  and are wired. **Measured fact (2026-06-02): they do not exist yet** — a repo
  grep for `record_quest`/`set_stakes` across `sidequest-server/sidequest/` finds
  no tool (the only hit, `record_questioned_npc` in `game/scenario_state.py`, is
  unrelated). Do **not** retire the old lanes before the replacement is in place;
  doing so leaves quest/stakes with zero writers. If 77-2 is not yet merged, this
  story is **blocked**, not "start the deletions early".

- **Retire the `quest_updates` extraction lane (orchestrator.py).** The
  `quest_updates` field and its extraction live at four confirmed seams in
  `sidequest-server/sidequest/agents/orchestrator.py`:
  - `:472` — `quest_updates: dict[str, str] = field(default_factory=dict)` (the
    dataclass field on the extraction result),
  - `:1258` — `"quest_updates": patch.get("quest_updates", {})` (patch-dict
    assembly; see also the surrounding logging at `:1188`, `:1203`, `:1214`),
  - `:3219` — `quest_updates=extraction["quest_updates"] if isinstance(...)` (the
    no-successor-tool state-lane population, see context at `:3484`),
  - `:3549` — the second `"quest_updates": extraction["quest_updates"] if
    isinstance(...)` assembly (context at `:3604`).
  Remove the `quest_updates` plumbing at these seams once the typed tool supersedes
  it (ADR-137 §One-mechanism consolidation). Status-only updates become an
  update-mode of `record_quest` (built in 77-2), not a separate extraction lane.

- **Migrate the `narration_apply` quest_log write onto the typed tool, then remove
  the `quest_updates` merge.** The live write is at
  `sidequest-server/sidequest/server/narration_apply.py:2863-2878`
  (note: the file lives under `sidequest/server/`, *not* `sidequest/agents/`):
  ```
  if result.quest_updates:
      with quest_update_span(updates=result.quest_updates, ...):
          for quest_id, status in result.quest_updates.items():
              snapshot.quest_log[quest_id] = status
  ```
  After 77-2's `record_quest` owns quest writes, this `result.quest_updates` →
  `snapshot.quest_log` merge is the redundant duplicate writer. Remove it so
  `quest_log` is written **only** through `record_quest`. The
  `quest_update_span`/`SPAN_QUEST_UPDATE` it wraps
  (`sidequest-server/sidequest/telemetry/spans/state_patch.py:29-30`, the
  `SpanRoute` registration, and `quest_update_span` at `:104-120`) is **replaced by
  77-2's `quest.updated` span**, per the ADR-137 OTEL table ("`quest.updated` …
  replaces `SPAN_QUEST_UPDATE`"). Confirm 77-2 actually emits `quest.updated`
  before deleting `SPAN_QUEST_UPDATE`; do not leave the GM panel without a quest
  span for an update.

- **Strip the quest/stakes path from `apply_world_patch.py` — but the surface is
  narrower than the ADR prose suggests; measure it.** ADR-137 names `/quest_log`,
  `/quest_updates`, and `/active_stakes`. **Measured fact:** the allowlist
  `_SUPPORTED_PATHS` in
  `sidequest-server/sidequest/agents/tools/apply_world_patch.py:111-116` contains
  only `/location`, `/time_of_day`, `/atmosphere`, `/current_region`, and
  `/active_stakes` — **`/quest_log` and `/quest_updates` were never exposed** (the
  module docstring at `:46-49` explicitly lists them as intentionally *not* routed
  through the escape hatch). So the concrete strip here is **`/active_stakes`
  only**: remove its `_SUPPORTED_PATHS` entry (`:116`), its dispatch branch
  (`:195-196` `elif field_name == "active_stakes": patch =
  WorldStatePatch(active_stakes=args.value)`), the docstring line that advertises
  it (`:37`/`:87` "v1 supports … '/active_stakes'"), and the args `description`
  reference (`:84-89`). Update the docstring to reflect that stakes now have a
  typed home (`set_stakes`, 77-2). After the strip, `/active_stakes` must return
  the existing **recoverable** "unsupported path" error (`:159-172`), pointing the
  narrator at the typed tool.

- **KEEP `/location` and `/current_region` (and `/time_of_day`, `/atmosphere`).**
  These are explicitly out of scope per ADR-137 §One-mechanism consolidation
  ("Other paths (location, current_region) … remain"). Do **not** touch
  `_SUPPORTED_PATHS["/location"]` / `["/current_region"]` or their dispatch
  branches (`:187-194`). `/location` also carries the migrated
  `LOCATION_PATCH_CONSTRAINT` guardrail (`:142-145`, ADR-111/story 57-4) — leaving
  it intact is load-bearing.

- **OTEL discipline (CLAUDE.md Observability Principle).** This story *removes* a
  span (`SPAN_QUEST_UPDATE`/`quest_update_span`) rather than adding one — but only
  because 77-2 replaces it with `quest.updated`. The net invariant the GM panel
  must keep: a quest-status change still emits a span (now `quest.updated`), and a
  stakes write still emits a span (now `stakes.set`, 77-2). Verify both fire via
  the typed tools before deleting the old span; never end up with a quest/stakes
  mutation that emits no span (that recreates the original "improvisation
  invisible to the lie detector" failure).

- **No Source-Text Wiring Tests (server CLAUDE.md).** Prove the old lane is gone by
  **behavior**, not by grepping source. Drive a turn whose extraction would
  previously have carried `quest_updates` and assert `snapshot.quest_log` is *not*
  written by that lane (and is written only by `record_quest`); drive an
  `apply_world_patch` call with `path: "/active_stakes"` through the real tool and
  assert it returns the recoverable unsupported-path error. Prefer OTEL-span and
  fixture-driven behavior assertions.

## Scope Boundaries

**In scope:**
- Retire the `quest_updates` extraction lane in
  `sidequest-server/sidequest/agents/orchestrator.py` (seams `:472`, `:1258`,
  `:3219`, `:3549`).
- Remove the redundant `result.quest_updates` → `snapshot.quest_log` merge in
  `sidequest-server/sidequest/server/narration_apply.py:2863-2878`, so `quest_log`
  is written only through the typed `record_quest` tool.
- Strip the quest/stakes path from
  `sidequest-server/sidequest/agents/tools/apply_world_patch.py` — concretely
  `/active_stakes` (allowlist `:116`, dispatch `:195-196`, docstring/arg
  descriptions). (`/quest_log` and `/quest_updates` are already not in the
  allowlist; ensure no stray references remain.)
- Replace/remove `SPAN_QUEST_UPDATE` / `quest_update_span`
  (`telemetry/spans/state_patch.py:29-30,104-120`) once 77-2's `quest.updated`
  span owns the update telemetry.
- Behavior/OTEL tests proving the old lanes no longer fire and the kept paths still
  work.

**Out of scope:**
- Building the typed `record_quest` / `set_stakes` tools and their
  `quest.created` / `quest.updated` / `stakes.set` spans — **story 77-2** (the
  hard lockstep dependency this story sits *after*).
- The creation seed of `quest_log` / `quest_anchors` / `active_stakes` —
  **story 77-1**.
- Promoting `quest_anchors` to a `WorldStatePatch` field + apply path + feeding
  `orbital/course.py` — **story 77-3** (`+quest.anchor.added`).
- The player-facing quest/objective UI panel — **story 77-5** (ui).
- Authoring wry_whimsy `seed_tropes` (the `active_seeds` content carve-out,
  ADR-128) — **story 77-6** (content).
- **Do NOT strip `/location`, `/current_region`, `/time_of_day`, or `/atmosphere`
  from `apply_world_patch`.** Only the quest/stakes path goes; the other escape-hatch
  paths (and the `/location` `LOCATION_PATCH_CONSTRAINT` guardrail) remain.

## AC Context

> Story acceptance_criteria and description are **null** in sprint YAML at
> authoring time (verified via `pf sprint story field 77-4 …`). The ACs below are
> derived from ADR-137 §One-mechanism consolidation (AC-3), the epic write-path
> consolidation diagram, and the confirmed code seams. TEA/Dev should treat them
> as the test contract; flag any divergence from a populated story field if one
> lands later.

**AC-1 — The `quest_updates` extraction lane no longer fires.** After the
migration, a narrator turn whose extraction would previously have produced
`quest_updates` must not reach the old `result.quest_updates` → `snapshot.quest_log`
merge.
*How a test verifies:* drive a turn through the real apply path with extraction that
historically carried `quest_updates`; assert `snapshot.quest_log` is not mutated by
that lane (the field/merge is gone) and that any quest write present came through
`record_quest`. Assert no `SPAN_QUEST_UPDATE` is emitted (it has been replaced by
77-2's `quest.updated`).

**AC-2 — `apply_world_patch` rejects the removed quest/stakes path.** A call with
`path: "/active_stakes"` (and, defensively, `/quest_log` / `/quest_updates`) must
return the existing **recoverable** unsupported-path `ToolResult`, not write the
field.
*How a test verifies:* invoke the real `apply_world_patch` tool with
`path="/active_stakes"`; assert the result is the recoverable "unsupported path"
error referencing the typed tool, and that no `WorldStatePatch(active_stakes=…)` was
constructed/applied.

**AC-3 — `/location` and `/current_region` still work (kept-path regression
guard).** The non-quest escape-hatch paths must be unaffected by the strip.
*How a test verifies:* invoke `apply_world_patch` with `path="/location"` and
`path="/current_region"` and assert each builds the correct `WorldStatePatch` field
and succeeds, with the `/location` `LOCATION_PATCH_CONSTRAINT` guardrail still
applied. (`/time_of_day` / `/atmosphere` may be asserted too.)

**AC-4 — Quest writes now flow only through `record_quest` (single-mechanism
invariant).** With the old lanes retired, the only path that mutates
`snapshot.quest_log` in normal play is the typed `record_quest` tool; the only path
that sets `active_stakes` is `set_stakes`.
*How a test verifies:* exercise `record_quest`/`set_stakes` (from 77-2) and confirm
`quest_log`/`active_stakes` are written and emit `quest.created`/`quest.updated`/
`stakes.set`; then confirm the retired lanes (extraction merge, escape-hatch
`/active_stakes`) cannot write those fields. This AC is **only assertable once 77-2
has landed** — it is the concrete expression of the lockstep gate.

## Assumptions

- **Load-bearing — strict lockstep ordering.** This story is gated on **sprint
  77-2** (typed `record_quest`/`set_stakes` tools). The tools **do not exist yet**
  (measured 2026-06-02). Retiring the `quest_updates` lane and stripping
  `/active_stakes` *before* 77-2 lands would leave quest/stakes fields with no
  writer at all — the opposite of the epic goal. If 77-2 is not merged when this
  story is picked up, it is **blocked**; do not begin deletions. Confirm 77-2's
  tools and their `quest.created`/`quest.updated`/`stakes.set` spans are live first.
- **The `apply_world_patch` strip is `/active_stakes`-only in practice.** Despite
  ADR-137 naming three paths, only `/active_stakes` is in the current allowlist;
  `/quest_log` and `/quest_updates` were never exposed (docstring `:46-49`). Treat
  the ADR's three-path list as the *intent*; implement against the *measured*
  allowlist. Defensive tests for the never-exposed paths are fine but require no
  removal work.
- **`SPAN_QUEST_UPDATE` deletion depends on 77-2 emitting `quest.updated`.** Do not
  delete the old span until the replacement is confirmed live, or the GM panel
  loses quest-update telemetry — a regression against the OTEL Observability
  Principle. If 77-2 shipped `quest.updated`, removing `SPAN_QUEST_UPDATE` here is
  correct and in-scope (ADR-137 OTEL table).
- **`orbital/course.py` is untouched.** The anchor consumer (ADR-130,
  `course.py:125,157`) belongs to 77-3; nothing in this cleanup story reads or
  writes anchors.
- The three target fields already exist on `GameSnapshot`; this story only removes
  *writers*, it adds no schema and removes no field declarations from the snapshot
  model.
