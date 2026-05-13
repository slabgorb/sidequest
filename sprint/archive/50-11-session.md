---
story_id: "50-11"
jira_key: "none"
epic: "50"
workflow: "tdd"
---

# Story 50-11: Disposition: SPAN_DISPOSITION_SHIFT threshold-crossing fields (before_attitude, after_attitude, crossed)

## Story Details

- **ID:** 50-11
- **Jira Key:** none (SideQuest uses no Jira)
- **Epic:** 50 (Pingpong-archive triage and dropped-work cleanup)
- **Workflow:** tdd
- **Points:** 2
- **Priority:** p2
- **Repos:** server
- **Type:** feature
- **Stack Parent:** 50-10 (Disposition: central Attitude enum + Disposition.attitude() derivation)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T08:55:43Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13 | 2026-05-13T08:14:35Z | 8h 14m |
| red | 2026-05-13T08:14:35Z | 2026-05-13T08:21:20Z | 6m 45s |
| green | 2026-05-13T08:21:20Z | 2026-05-13T08:32:42Z | 11m 22s |
| spec-check | 2026-05-13T08:32:42Z | 2026-05-13T08:34:59Z | 2m 17s |
| verify | 2026-05-13T08:34:59Z | 2026-05-13T08:44:51Z | 9m 52s |
| review | 2026-05-13T08:44:51Z | 2026-05-13T08:54:15Z | 9m 24s |
| spec-reconcile | 2026-05-13T08:54:15Z | 2026-05-13T08:55:43Z | 1m 28s |
| finish | 2026-05-13T08:55:43Z | - | - |

## Story Context

This story is part of the disposition system refactor series. Story 50-10 introduces a central `Attitude` enum and derives `Disposition.attitude()`. Story 50-11 extends that foundation to emit threshold-crossing telemetry.

**Acceptance Criteria:**

1. `SPAN_DISPOSITION_SHIFT` OTEL span includes three new fields: `before_attitude`, `after_attitude`, and `crossed` (boolean)
2. When a disposition shift would cross a configureable threshold (currently ±10 default per ADR-090 or interim spec), `crossed=true`
3. `before_attitude` and `after_attitude` are the string representations of the Attitude enum values before and after the shift
4. Integration test covers threshold-crossing and non-crossing shifts; each emits the correct OTEL span with all three fields populated
5. OTEL span is emitted during disposition application (same callsite as the current shift detector)
6. `crossed` field is populated correctly even when the threshold changes (no hardcoded assumptions)

## Delivery Findings

<!-- AGENT-FINDINGS-MARKER -->

### TEA (test design)

- **Gap** (non-blocking): Story 50-10 (central `Attitude` enum + `Disposition.attitude()`) has status `backlog` and has not landed.
  Affects `sidequest-server/sidequest/server/dispatch/opening.py` (the existing `_disposition_attitude` helper is the *de facto* source of truth for band strings).
  Tests use the strings `"friendly"`, `"neutral"`, `"hostile"` per ADR-020. Dev should either reuse `_disposition_attitude` (its stable contract) or land 50-10 first; do not invent a parallel band vocabulary.
  *Found by TEA during test design.*

- **Improvement** (non-blocking): The route lambda at `sidequest-server/sidequest/telemetry/spans/disposition.py:12` currently extracts only `npc_name`/`delta`/`before`/`after`. Adding the three new fields to the emission site without also updating this lambda would silently drop them at the watcher boundary — the GM panel would never see them.
  Affects `sidequest-server/sidequest/telemetry/spans/disposition.py` (extract lambda must be updated alongside the emitter in `sidequest/game/session.py:1168`).
  *Found by TEA during test design.*

- **Question** (non-blocking): AC6 says "no hardcoded assumptions" about the threshold. Story 50-13 will introduce genre-configurable thresholds. For 50-11, the RED tests pin only *band-identity* semantics (canary tests prove `crossed` is not `abs(delta) > 10`). The threshold *value* remains the existing ±10 (ADR-020, strict boundaries). Dev should ensure the implementation routes `crossed` through whatever helper computes the band — not through a duplicated literal — so 50-13 can swap thresholds without revisiting 50-11.
  Affects `sidequest-server/sidequest/game/session.py` (the disposition shift emission site).
  *Found by TEA during test design.*

### Dev (implementation)

- **Improvement** (non-blocking): The docstring `"""Mirrors Npc.attitude() — three-tier ADR-020 mapping."""` on the pre-existing private helper referenced a non-existent `Npc.attitude()` method (grepped: no such method exists in `sidequest/game/`). The helper move deleted that stale comment as a side-effect.
  Affects `sidequest-server/sidequest/game/disposition.py` (the new home; docstring there is current and accurate).
  *Found by Dev during implementation.*

- **Gap** (non-blocking): Pre-existing pyright error at `sidequest-server/sidequest/game/session.py:817` — `float(raw_current)` where `raw_current: object` is not narrowed to `ConvertibleToFloat`. Predates this story; not in the disposition shift code path; needs a separate story to add a `try/except` around a type narrowing or a `cast(float | int | str, raw_current)` annotation.
  Affects `sidequest-server/sidequest/game/session.py` (legacy resource pool coercion in `_coerce_current`).
  *Found by Dev during implementation.*

- **Gap** (non-blocking): Pre-existing test failure for `test_mp_joiner_suppresses_opening_seed` (2 variants) on `develop`. Unrelated to disposition; affects multiplayer joiner / opening-seed wiring. Visible in any full-suite run.
  Affects `sidequest-server/tests/...` (MP joiner suite — exact path not investigated; out of scope for 50-11).
  *Found by Dev during implementation.*

### TEA (test verification)

- No upstream findings during test verification. The MP-joiner failures Dev recorded did not reproduce on the verify-phase full run (0 failed). All three simplify teammates returned `status: clean`.

  *Found by TEA during test verification.*

### Reviewer (code review)

- **Improvement** (non-blocking): Test file attributes the sprint-3 cold-subsystem disposition wiring to "story 50-9," but 50-9 in `epic-50.yaml` is the music mood-alias story. Fix in a follow-on chore — strike the two `50-9` references and replace with "sprint-3 cold-subsystem audit." Affects `sidequest-server/tests/integration/test_disposition_threshold_crossing.py` (lines 3 and 394, both docstrings only — no test logic). *Found by Reviewer during code review.*

- **Improvement** (non-blocking): New public module `sidequest/game/disposition.py` lacks `__all__`. Project convention adds explicit public-API declaration for public modules. Single-line fix: `__all__ = ["disposition_attitude"]`. Affects `sidequest-server/sidequest/game/disposition.py` (add `__all__` after the docstring). *Found by Reviewer during code review.*

- **Improvement** (non-blocking): `asyncio.get_event_loop().time()` at lines 96-97 of the new test file is deprecated in Python 3.10+; `asyncio.get_running_loop().time()` is the modern idiom (same file uses it correctly at line 73). The same drift exists in `tests/integration/test_disposition_otel_wiring.py` — a single follow-on chore can fix both. Affects `sidequest-server/tests/integration/test_disposition_threshold_crossing.py` and `sidequest-server/tests/integration/test_disposition_otel_wiring.py`. *Found by Reviewer during code review.*

- **Gap** (non-blocking, deferred): Three test-coverage gaps worth a future hardening pass — (1) no `delta=0` test (documents whether degenerate patches emit a span), (2) no lower-bound clamp mirror test (`before=-95, delta=-50→-100`), (3) the `test_disposition_shift_route_extracts_threshold_fields` unit test passes `crossed=True` to the route lambda's `bool(...)` cast, so the cast itself is not exercised — a `crossed=1` (int) variant would. None of these block the merge; all are coverage strengthening. Affects `sidequest-server/tests/integration/test_disposition_threshold_crossing.py` and `sidequest-server/tests/telemetry/test_spans.py`. *Found by Reviewer during code review.*

- **Question** (non-blocking, deferred): Pre-existing silent-skip behavior in `apply_world_patch` — `WorldStatePatch(npc_attitudes={"Unknown": 5})` where the name isn't in `self.npcs` is silently no-op'd, no warning span emitted. Predates 50-11; not introduced by this branch. Worth a separate story to add a warning span for the GM panel (consistent with CLAUDE.md "No Silent Fallbacks"). Affects `sidequest-server/sidequest/game/session.py:1160-1188`. *Found by Reviewer during code review.*

## Design Deviations

<!-- AGENT-DEVIATIONS-MARKER -->

### TEA (test design)

- **Tests assert on `_disposition_attitude` string vocabulary rather than a central `Attitude` enum**
  - Spec source: session SM Assessment — "string representations of the Attitude enum values"
  - Spec text: "`before_attitude` and `after_attitude` are the string representations of the Attitude enum values before and after the shift" (AC3)
  - Implementation: Tests assert literal strings `"friendly"`, `"neutral"`, `"hostile"` matching the existing `_disposition_attitude` helper at `sidequest/server/dispatch/opening.py:49`. One test (`test_attitude_strings_match_existing_helper_vocabulary`) directly cross-checks against that helper.
  - Rationale: Story 50-10 (introduces the `Attitude` enum) is still `backlog`. The existing ADR-020 helper produces the same strings the future enum will use as its `.value`. Testing the string contract keeps the AC stable across the 50-10 refactor without blocking 50-11 on a story that hasn't started.
  - Severity: minor
  - Forward impact: When 50-10 lands, `Attitude` enum's string values must be exactly `"friendly"`/`"neutral"`/`"hostile"` (the existing vocabulary). 50-10 author should preserve that.

- **AC6 ("no hardcoded assumptions") tested via band-identity canaries, not via configurable threshold injection**
  - Spec source: session AC6 — `crossed` correct even when the threshold changes
  - Spec text: "`crossed` field is populated correctly even when the threshold changes (no hardcoded assumptions)"
  - Implementation: Two canary tests (`test_large_delta_within_same_band_does_not_set_crossed`, `test_tiny_delta_across_boundary_sets_crossed_true`) prove `crossed` cannot be `abs(delta) > 10`. No test injects a different threshold value because no configurable threshold mechanism exists yet — 50-13 owns that work.
  - Rationale: The current threshold is hardcoded at ±10 in `_disposition_attitude`. Testing "what if the threshold changes" before 50-13 lands would require a fixture that doesn't exist. The canaries enforce the *shape* of the predicate (band identity, not delta magnitude), which is the part 50-11 can lock in. When 50-13 makes thresholds configurable, those tests still pass — the band helper continues to be the source of truth.
  - Severity: minor
  - Forward impact: 50-13 should add the parametric-threshold tests (different genre packs → different boundaries → `crossed` reflects band identity per pack). Not 50-11's job.

- **No test of OTEL span name / route registration beyond the existing `test_disposition_span_names`**
  - Spec source: session AC1 — fields on `SPAN_DISPOSITION_SHIFT`
  - Spec text: "`SPAN_DISPOSITION_SHIFT` OTEL span includes three new fields"
  - Implementation: The span name and route registration were already covered by `tests/telemetry/test_spans.py::test_disposition_span_names` and `tests/integration/test_disposition_otel_wiring.py`. New tests only cover the *new field* contract.
  - Rationale: AC1 is about field presence, not span/route existence. Existing tests already pin span name + routing. Adding redundant coverage would dilute, not strengthen.
  - Severity: trivial
  - Forward impact: None.

### TEA (test verification)

- No deviations from spec during verify. Simplify fan-out returned clean from all three teammates; no changes applied; no regressions detected. The story's RED-phase deviations remain the only test-design deviations.

### Reviewer (audit)

- TEA #1 ("Tests assert on `_disposition_attitude` string vocabulary rather than a central `Attitude` enum") → ✓ ACCEPTED by Reviewer: 50-10 is `backlog`; using the existing helper's string contract is the correct forward-compat move. `test_attitude_strings_match_existing_helper_vocabulary` makes the contract testable so 50-10 can't break it silently.
- TEA #2 ("AC6 tested via band-identity canaries, not via configurable threshold injection") → ✓ ACCEPTED by Reviewer: the two canary tests (`test_large_delta_within_same_band_does_not_set_crossed`, `test_tiny_delta_across_boundary_sets_crossed_true`) genuinely rule out `crossed = abs(delta) > 10` implementations. Threshold *value* configurability is 50-13's scope. Implementation routes `crossed` through the band helper, so 50-13 can swap the literal at one site.
- TEA #3 ("No test of OTEL span name / route registration beyond `test_disposition_span_names`") → ✓ ACCEPTED by Reviewer: pre-existing tests cover span name + routing; new tests focus on the new-field contract. Non-duplication is correct.
- Architect Mismatch #1 ("Wrong ADR cited in AC2 — ADR-090 instead of ADR-020") → ✓ ACCEPTED by Reviewer: AC text drift. Code correctly cites ADR-020. The "or interim spec" hedge in AC2 covers the ambiguity. Cosmetic — no code change needed.
- Architect Mismatch #2 ("Threshold value still hardcoded — deferred to 50-13") → ✓ ACCEPTED by Reviewer: predicate is threshold-agnostic by structure (band-identity comparison); literal `10` lives in one place. 50-13's job to make configurable. Defer is correct.
- Architect Mismatch #3 ("Spec did not anticipate the helper extraction — positive drift") → ✓ ACCEPTED by Reviewer: bounded boy-scouting; new module is 22 lines and is the natural landing zone for 50-10's enum. The module docstring directs 50-10 there explicitly. The cross-check test enforces the forward contract.
- Dev #1 ("Stale docstring claim `Mirrors Npc.attitude()` referenced a non-existent method") → ✓ ACCEPTED by Reviewer: the lie is deleted by this PR. New module's docstring is accurate. No live issue.
- Dev #2 ("Pre-existing pyright error at session.py:817") → ✓ ACCEPTED by Reviewer: confirmed pre-existing on `develop`; not introduced by this branch.
- Dev #3 ("Pre-existing `test_mp_joiner_suppresses_opening_seed` failure") → ✓ ACCEPTED by Reviewer: did not reproduce on TEA's verify-phase full run (`5,104 passed, 0 failed`). Flaky or fixed by sibling merge. Not 50-11's concern.

**Undocumented deviations:** Reviewer identified the following deviations that TEA/Dev/Architect did not log:

- **Test file references the wrong sprint-3 promotion story (`50-9`)**
  - Spec source: `epic-50.yaml` (sprint backlog reference)
  - Spec text: 50-9 in the epic YAML is "Mood: implement mood_aliases alias-chain fallback in music director track selection" — owns no disposition span work.
  - Implementation: `tests/integration/test_disposition_threshold_crossing.py:3` and `:394` both attribute the numeric `before`/`after`/`delta` fields to "story 50-9's cold-subsystem promotion." The actual source is the sprint-3 audit (no story ID), as the existing `disposition.py` telemetry-route comment correctly states.
  - Rationale: TEA wrote the comments off-by-one when looking up the sprint-3 attribution. Not a behavioral bug; cosmetic doc-rot.
  - Severity: low
  - Forward impact: Annoying to grep for the wrong story ID; misleading to anyone tracing the GM-panel disposition wiring's history. Fix in a follow-on chore (single sed).

- **New public module `sidequest/game/disposition.py` lacks `__all__`**
  - Spec source: `gates/lang-review/python.md` rule #10 (import-hygiene)
  - Spec text: "Missing `__all__` on public modules — unclear public API."
  - Implementation: Module exports `disposition_attitude` but does not declare `__all__`. Project convention (e.g., `sidequest/game/__init__.py`) uses `__all__` on public modules.
  - Rationale: Single-symbol module; the omission was overlooked, not deliberate.
  - Severity: low
  - Forward impact: A `from sidequest.game.disposition import *` would currently pull `disposition_attitude` plus the `__future__.annotations` import — not harmful, but ambiguous public API.

- **Deprecated `asyncio.get_event_loop()` in new test file**
  - Spec source: `gates/lang-review/python.md` rule #9 (async-pitfalls)
  - Spec text: "Blocking calls (`time.sleep`, `requests.get`, file I/O) inside async functions — use `aiohttp`, `aiofiles`, or `asyncio.to_thread()`." (Adjacent: deprecated event-loop API.)
  - Implementation: `tests/integration/test_disposition_threshold_crossing.py:96-97` calls `asyncio.get_event_loop().time()` inside a running coroutine. Deprecated in Python 3.10+; should be `asyncio.get_running_loop().time()`. The same file's `_setup()` at line 73 uses `get_running_loop()` correctly.
  - Rationale: Pattern copied wholesale from `tests/integration/test_disposition_otel_wiring.py`. Project-wide drift, not a new-pattern introduction.
  - Severity: low
  - Forward impact: Will produce a `DeprecationWarning` under Python 3.10+; could become a `RuntimeError` in Python 3.13+/3.14+. A single-line fix here AND in the sibling test would resolve both files.

### Architect (reconcile)

**Existing entries reviewed:**

- TEA (test design) #1, #2, #3 — all 6 fields present, substantive, spec sources verified (`session SM Assessment`, AC text, sprint YAML). No corrections needed.
- Dev (implementation) entries live under `## Delivery Findings`, not under `## Design Deviations` — that is the correct routing per Dev's agent definition (Dev observations are findings, not deviations, when no spec was violated). No entries to verify here.
- Reviewer (audit) — stamps every prior deviation ACCEPTED with rationale, and adds 3 undocumented deviations (50-9 attribution, missing `__all__`, deprecated `get_event_loop`) with full 6-field structure. Spec sources verified: `epic-50.yaml` exists and 50-9 is indeed the music mood-alias story; `gates/lang-review/python.md` rules #9 and #10 exist as cited. Spec-text quotation for the deprecated-API entry is approximate (labeled "Adjacent" by the author, which is intellectually honest — Python's deprecation of `get_event_loop()` from coroutines is not literally enumerated in rule #9's bullet list, but is in the spirit of async-pitfalls). No correction needed; the "Adjacent" hedge accurately characterizes the inference.

**Missed deviations formalized below:**

- **AC2 cites the wrong ADR (ADR-090 instead of ADR-020)**
  - Spec source: session file's `## Story Context` — Acceptance Criterion #2
  - Spec text (verbatim): "When a disposition shift would cross a configureable threshold (currently ±10 default per ADR-090 or interim spec), `crossed=true`"
  - Implementation: All code citations correctly reference ADR-020 (NPC Disposition System): `sidequest/game/disposition.py` module docstring ("This matches `ADR-020`'s NPC disposition system"), the test module docstring ("Bands follow ADR-020's three-tier mapping"), and the SM Assessment in this session. ADR-090 is "OTEL Dashboard Restoration after Python Port" — unrelated to disposition bands.
  - Rationale: AC text drift introduced when the story was authored. The "or interim spec" hedge in AC2 covers the ambiguity and the implementation correctly follows ADR-020, so the AC's intent is honored. The deviation is purely textual.
  - Severity: trivial
  - Forward impact: None on this story (code is correct). Could mislead a future reader trying to look up the threshold rationale; an `epic-50.yaml` edit fixing the ADR reference would resolve it for the historical record. Not worth blocking on; flag in a tracker-hygiene chore.

**AC accountability:** No ACs were deferred during this story. All 6 ACs map to confirmed test coverage in the TEA Assessment's test inventory table. No status changes during review (the Reviewer's findings were all LOW improvements; none invalidated or addressed any AC). No-op for the AC-deferral cross-reference step.

**Spec-reconcile verdict:** Deviation manifest complete. Every deviation that affected this story is now either:
- Logged in `### TEA (test design)` with full 6 fields (3 entries), OR
- Logged in `### Reviewer (audit)`'s "Undocumented deviations" with full 6 fields (3 entries), OR
- Logged in `### Architect (reconcile)` with full 6 fields (1 entry — this one), OR
- Stamped as ACCEPTED in `### Reviewer (audit)` against an earlier entry.

The story can proceed to SM finish.

## Sm Assessment

**Story scope:** Extend the existing `SPAN_DISPOSITION_SHIFT` OTEL span with three threshold-crossing fields — `before_attitude`, `after_attitude`, `crossed`. This is observability work, not behavior change. The disposition shift logic itself is unchanged; we are adding telemetry so the GM panel (and Sebastien) can see *when* attitude bands flip versus when only the numeric delta moved.

**Dependency on 50-10:** Story 50-10 introduces a central `Attitude` enum and a `Disposition.attitude()` derivation. 50-11 builds directly on that — the `before_attitude` and `after_attitude` fields are the string forms of that enum. If 50-10 has not landed when 50-11's RED phase begins, TEA should flag it; do not stub a parallel enum.

**Workflow:** TDD phased (setup → red → green → review → finish). Single repo: sidequest-server. Branch `feat/50-11-disposition-shift-threshold-fields` cut from `develop`. No UI, daemon, or content changes expected.

**OTEL alignment:** Per project doctrine, every subsystem fix must add OTEL watcher events. This story *is* an OTEL enrichment — the AC is the watcher signal. TEA should write tests against the emitted span fields (via the OTEL test harness), not against any narration-level effect.

**Risks for TEA to consider:**
- Threshold may be configurable (AC6); test should not hardcode ±10. Read it from the same source the production code reads.
- `crossed` must be computed from the *band* transition (Attitude enum change), not the numeric delta crossing ±10. A shift from +9 to +11 is a crossing only if those numbers map to different attitude bands.
- The current callsite emitting `SPAN_DISPOSITION_SHIFT` is the integration point — do not add a second emission site.

**Handoff target:** TEA (RED phase) writes the failing integration tests for the three new span fields and the crossing logic.

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish
**Status:** RED (15 new tests; 14 failing on missing attributes, 1 passing as a regression guard)

**Test Files:**
- `sidequest-server/tests/integration/test_disposition_threshold_crossing.py` (new) — 13 integration tests through the watcher harness, asserting on `state_transition` payload fields
- `sidequest-server/tests/telemetry/test_spans.py` (modified) — 2 new unit tests for `SPAN_ROUTES[disposition.shift].extract` contract

### Test Inventory (AC mapping)

| Test | AC | Why |
|------|----|-----|
| `test_disposition_shift_emits_attitude_strings_and_crossed_field` | AC1, AC3 | All three fields present and correctly typed (strings + bool) |
| `test_neutral_to_friendly_marks_crossed_true` | AC2, AC3 | Upper-boundary crossing (10 → 15) |
| `test_neutral_to_hostile_marks_crossed_true` | AC2, AC3 | Lower-boundary crossing (-10 → -15) |
| `test_friendly_to_hostile_two_band_jump_still_crossed` | AC2 | Two-band leap (15 → -25) still crossed=True |
| `test_shift_within_friendly_band_marks_crossed_false` | AC2 (negative) | 15 → 25, no crossing |
| `test_shift_within_neutral_band_marks_crossed_false` | AC2 (negative) | 5 → 8, no crossing |
| `test_back_crossing_friendly_to_neutral_marks_crossed_true` | AC2 | Tiny back-crossing (11 → 10) |
| `test_clamped_at_bound_uses_clamped_attitude` | AC2, AC3 | Clamp at ±100 still picks the clamped band (95+50 → 100, friendly) |
| `test_large_delta_within_same_band_does_not_set_crossed` | AC6 | **Canary:** `abs(delta)=15 > 10` but both ends friendly → crossed=False |
| `test_tiny_delta_across_boundary_sets_crossed_true` | AC6 | **Canary:** `abs(delta)=1` but bands flip → crossed=True |
| `test_attitude_strings_match_existing_helper_vocabulary` | AC3 | Strings match `_disposition_attitude` output |
| `test_single_shift_emits_exactly_one_state_transition` | AC5 | Regression guard: one patch entry → one event (passes today, fails if Dev double-emits) |
| `test_numeric_fields_preserved_alongside_new_fields` | AC1 | No regression on existing `before`/`after`/`delta`/`npc_name` |
| `test_disposition_shift_route_extracts_threshold_fields` | AC1 | Unit-level: extract lambda propagates new fields from attributes |
| `test_disposition_shift_route_defaults_threshold_fields_when_missing` | AC1 | Unit-level: extract lambda has stable defaults during partial rollout |

### Rule Coverage

| Rule (CLAUDE.md / SOUL) | Test(s) | Status |
|---|---|---|
| No silent fallbacks — extract lambda must produce typed defaults, not raise | `test_disposition_shift_route_defaults_threshold_fields_when_missing` | failing |
| Verify wiring, not just existence — span fields must reach the watcher payload | `test_disposition_shift_emits_attitude_strings_and_crossed_field` + the integration suite | failing |
| OTEL observability — every subsystem decision emits a span | (story *is* this rule; all integration tests enforce it) | failing |
| No half-wired features — emission *and* route must be updated together | 13 integration tests fail until the route is updated; 2 unit tests fail until both emission and route are updated | failing |
| Every test suite needs a wiring test | The whole integration file is a wiring suite (real `apply_world_patch` → real `Span.open` → real `WatcherSpanProcessor` → real subscriber) | failing |

**Rules checked:** 5 of 5 applicable rules from `sidequest-server/CLAUDE.md` and SOUL.md have test coverage
**Self-check:** No vacuous assertions. Every test has at least one explicit field assertion. The single `_apply_shift` helper returns a tuple but the call sites only use it for setup — return value is consumed via `snapshot` (no `let _ =` pattern).

### Test Strategy Notes

- **Why integration over pure unit:** The AC is *user-visible OTEL fields* via the watcher. Asserting on `Span.attributes` directly would test what the emitter sets; asserting on `evt["fields"]` tests what the GM panel actually receives. The route lambda is the choke point — a unit test on it can't catch the case where the emitter sets the wrong key. I added focused unit tests for the route contract too, but the integration tests are the load-bearing ones.

- **Magic-number canaries (AC6):** Two tests are specifically designed to fail under a naive `crossed = abs(delta) > threshold` implementation. The 20→35 case (delta=15, both friendly) and 10→11 case (delta=1, band flip) cross-cancel any threshold-based predicate. The correct predicate is `before_band != after_band`.

- **Strings vs enum:** Tests assert string literals `"friendly"`/`"neutral"`/`"hostile"`. When 50-10 lands, those strings remain the contract; the enum just gives them a typed home. See Design Deviations.

- **Single-emission regression guard:** `test_single_shift_emits_exactly_one_state_transition` passes today and is expected to keep passing. It's a Chekhov's gun for Dev: if implementing the threshold fields tempts anyone to `with Span.open(SPAN_DISPOSITION_SHIFT, ...)` twice (once for numbers, once for bands), this test fires.

### Implementation Pointers for Dev

1. **Emit at `sidequest-server/sidequest/game/session.py:1168`** — extend the existing `Span.open(SPAN_DISPOSITION_SHIFT, {...})` attribute dict with `before_attitude`, `after_attitude`, `crossed`. **Do not add a second `Span.open` block.**
2. **Update the route at `sidequest-server/sidequest/telemetry/spans/disposition.py:12`** — add the three keys to the `extract` lambda, with `""`/`""`/`False` defaults if attributes are missing (matches the existing pattern of `(span.attributes or {}).get("npc_name", "")`).
3. **Use the existing `_disposition_attitude` helper** at `sidequest-server/sidequest/server/dispatch/opening.py:49` — it's the source of truth until 50-10 lands a central `Attitude` enum. Either import it or move it to a shared module; do not duplicate the literal `10`.
4. **`crossed` must be `before_attitude != after_attitude`** — band identity, not numeric delta. Computing it from the strings keeps the predicate threshold-agnostic and unblocks 50-13.

**Handoff:** To Dev (White Rabbit) for GREEN implementation.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — 15 new tests pass, 5,104 tests pass overall (2 pre-existing MP-joiner failures unrelated to this change), lint clean.

**PR:** https://github.com/slabgorb/sidequest-server/pull/273 (targets `develop`)

### Files Changed

- `sidequest-server/sidequest/game/disposition.py` (new, 22 lines) — public `disposition_attitude(int) -> str`, ADR-020 three-tier mapping. Strict boundaries: `>10` → friendly, `<-10` → hostile, else neutral. Module docstring flags the contract that 50-10's `Attitude` enum must preserve (`"friendly"`/`"neutral"`/`"hostile"` string values).
- `sidequest-server/sidequest/game/session.py` — emission site at `apply_world_patch` extended. Computes `before_attitude` and `after_attitude` via the new helper, sets `crossed = before_attitude != after_attitude` (band identity, not delta magnitude). The numeric `after` is computed from the *clamped* disposition so `after_attitude` matches state, not raw delta.
- `sidequest-server/sidequest/telemetry/spans/disposition.py` — route's `extract` lambda propagates the three new fields. Defaults are `""`/`""`/`False` for partial-rollout safety. Comment updated to explain the GM-panel rationale.
- `sidequest-server/sidequest/server/dispatch/opening.py` — `_disposition_attitude` private inline deleted; two callsites (lines 132, 333) now use the public import. No behavioural change at these callsites.
- `sidequest-server/tests/integration/test_disposition_threshold_crossing.py` — TEA's test file updated in one place: the `test_attitude_strings_match_existing_helper_vocabulary` test now imports from the new public location (`sidequest.game.disposition.disposition_attitude`). The contract being asserted is unchanged.

### How the implementation maps to TEA's pointers

| TEA pointer | What Dev did |
|---|---|
| Extend the existing `Span.open` at `session.py:1168`; **do not** add a second emission | Single `Span.open` block now has 7 keys instead of 4. Single-emission regression guard still passes. |
| Update the route extract lambda | Three new keys added with `(span.attributes or {}).get(..., default)` pattern matching the existing style. `bool(...)` cast around `crossed` to keep the type pinned even if a malformed attribute slips in. |
| Use existing `_disposition_attitude`; do not duplicate the literal `10` | Moved the helper to a shared game-layer module and renamed to public `disposition_attitude`. Both consumers (`session.py`, `opening.py`) import it. The literal `10`/`-10` exists in exactly one place: `sidequest/game/disposition.py:25-29`. |
| `crossed` must be band identity, not numeric delta | `crossed = before_attitude != after_attitude` — derived purely from band strings. Tests confirm canary cases pass. |

### Boy-scouting (bounded)

The helper move from `server/dispatch/opening.py` to `sidequest/game/disposition.py` is the only refactor in this PR. It was strictly required to satisfy AC6's "no hardcoded assumptions" rule — leaving the helper inline in a `server/dispatch` module would have meant either (a) game-layer code importing from server-layer (backward dep), or (b) duplicating the `±10` literal in `session.py`. Both are worse than the move. New module is 22 lines and prepped for 50-10 to drop the `Attitude` enum into.

### What I did *not* do

- I did not modify the deeper pyright error at `session.py:817` (a pre-existing `float(raw_current)` typing issue unrelated to this story). Out of scope.
- I did not investigate the 2 pre-existing MP-joiner test failures (`test_mp_joiner_suppresses_opening_seed`). They fail on `develop` without my changes — confirmed by testing-runner.
- I did not modify the `Npc.attitude()` comment-reference at the now-deleted helper site (the docstring claim "Mirrors `Npc.attitude()`" pointed at a method that does not exist). Deleting the helper deletes the stale reference; no further action needed.

### Delivery Findings

See `## Delivery Findings → Dev (implementation)` below.

**Handoff:** To Reviewer (Queen of Hearts) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (lint+pytest pass; 1 pre-existing pyright at session.py:817 not introduced by this branch) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.edge_hunter |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.silent_failure_hunter |
| 4 | reviewer-test-analyzer | Yes | findings | 9 | confirmed 3, dismissed 4, deferred 2 |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 | confirmed 2, dismissed 3, deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.type_design |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.security |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.simplifier |
| 9 | reviewer-rule-checker | Yes | findings | 3 (2 unique — one instance double-counted under rules #6 and #9) | confirmed 2, dismissed 0 |

**All received:** Yes (4 enabled returned; 5 skipped per settings)
**Total findings:** 7 confirmed (all LOW), 7 dismissed (with rationale), 2 deferred (low-priority gaps for a follow-up)

## Rule Compliance

Exhaustive enumeration against `gates/lang-review/python.md` (13 checks) + CLAUDE.md project rules (5 checks) — 18 rules total.

| Rule | Domain | Instances Checked | Verdict |
|------|--------|------|---------|
| #1 silent-exceptions | Bare `except:`, swallowed exceptions | 5 (3 prod, 2 test) | ✓ All compliant — no exception handling added; existing try/except at session.py:816 re-raises with context (pre-existing) |
| #2 mutable-defaults | `def f(items=[])` etc. | 8 (1 prod fn, 7 test fns/lambdas) | ✓ All compliant — `disposition_attitude(disposition: int)`, all test helpers, route lambda all use immutable/required params |
| #3 type-annotations | Public fn signatures + returns | 4 (1 new public fn, 1 import, 1 mod-method-call, 1 test helper) | ✓ All compliant — `disposition_attitude(int) -> str` typed; private callers (`_render_directive_*`) exempt |
| #4 logging | Error paths logged at right level | 5 files | ✓ All compliant — no new error paths; OTEL span IS the observability path |
| #5 path-handling | `Path()` vs string concat, encoding | 0 | ✓ N/A — no path operations |
| #6 test-quality | Vacuous assertions, missing assertions | 18 (15 new tests + 3 helpers) | ⚠ 1 violation — `asyncio.get_event_loop().time()` at lines 96-97 of the new test (deprecated in Py 3.10+; should be `get_running_loop()`). Pattern inherited from sibling `test_disposition_otel_wiring.py`. **LOW.** |
| #7 resource-leaks | `open()`/`Session()` without `with` | 2 | ✓ `Span.open(...)` used as context manager at session.py:1177; no other resources |
| #8 unsafe-deserialization | pickle/eval/yaml.load | 0 | ✓ N/A — no deserialization |
| #9 async-pitfalls | Missing awaits, blocking calls | 14 (1 deprecated-API instance + 13 `asyncio.sleep(0)` yields) | ⚠ Same instance as #6 — `get_event_loop()` deprecated. `asyncio.sleep(0)` is the documented yield-the-loop pattern used across the project's WatcherSpanProcessor tests; not a new violation. **LOW.** |
| #10 import-hygiene | Star imports, missing `__all__` | 7 (1 new module, 7 import sites) | ⚠ 1 violation — new public module `sidequest/game/disposition.py` lacks `__all__`. Project uses `__all__` on public modules (`sidequest/game/__init__.py` has one). **LOW.** Inline imports at session.py:1156-1157 match 7 existing inline patterns in the same file; compliant. |
| #11 input-validation | User input sanitization at boundaries | 2 | ✓ `disposition_attitude` takes engine-computed int; clamp at session.py:1163 preserved |
| #12 dependency-hygiene | Unpinned deps, test deps in main | 1 | ✓ `pyproject.toml` unchanged |
| #13 fix-regressions | New fix introduces same bug class | 5 | ✓ Helper extraction preserves three-tier logic verbatim; ordering correct (`before` captured pre-mutation, `after` captured post-mutation); numeric fields preserved |
| CLAUDE.md No Silent Fallbacks | Default values that mask config errors | 3 (route extract lambda) | ✓ Compliant — `False`/`""` defaults are typed sentinels for partial-rollout safety, explicitly tested by `test_disposition_shift_route_defaults_threshold_fields_when_missing`; matches existing numeric `0` defaults in same lambda |
| CLAUDE.md No Stubbing | Placeholder/skeleton modules | 1 (new disposition.py) | ✓ Compliant — 22 LOC, fully implemented, immediately consumed by 3 callers |
| CLAUDE.md Don't Reinvent | Wire up existing infrastructure | 1 (helper move) | ✓ Compliant — consolidation, not reinvention |
| CLAUDE.md Verify Wiring | Non-test production consumers | 1 (new module) | ✓ Compliant — 3 production callers: `session.py:1166` (×2 lines), `opening.py:132`, `opening.py:333` |
| CLAUDE.md Every Test Suite Needs a Wiring Test | At least one integration test | 1 (new test file) | ✓ Compliant — 13 of 13 integration tests exercise the full pipeline (`apply_world_patch` → `Span.open` → `WatcherSpanProcessor` → real `watcher_hub` subscriber). The `opening.py` callsite is exercised by pre-existing tests (5,089 non-50-11 tests would fail if `from sidequest.game.disposition import disposition_attitude` were broken). |
| CLAUDE.md OTEL Observability | Subsystem decisions emit spans | 1 (this story) | ✓ Compliant — the story IS the principle. Three new fields enrich the GM panel's `state_transition` payload; route lambda updated; tests assert the watcher-visible surface, not the span attrs directly. |

### Rule Compliance Summary

- **Pass:** 15 of 18 rules
- **Violations:** 3 LOW (1 deprecated-API instance counted under rules #6 & #9, 1 missing-`__all__` under rule #10)
- **Blocking:** None

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:**
`WorldStatePatch.npc_attitudes={"NPC": delta}` from narrator structured output
  → `GameSnapshot.apply_world_patch(patch)` at session.py:1118
  → name-match loop at session.py:1160
  → numeric clamp `max(-100, min(100, ...))` at session.py:1162 (preserves existing invariant; no widening)
  → band derivation via `disposition_attitude(before)` and `disposition_attitude(after)` at session.py:1165-1166
  → `Span.open(SPAN_DISPOSITION_SHIFT, {...7 keys...})` at session.py:1177
  → OTel `WatcherSpanProcessor.on_end()` (pre-existing pipeline)
  → `SPAN_ROUTES[disposition.shift].extract(span)` at telemetry/spans/disposition.py:17
  → typed `state_transition` event via `watcher_hub.publish()`
  → GM panel JSON subscriber

**Safe because:**
1. Numeric clamp at the boundary keeps `before`/`after` in `[-100, 100]`; band derivation is exhaustive over that range.
2. `crossed` is `before_attitude != after_attitude` — pure string comparison, no magic-number trap.
3. The route lambda's `bool(...)` cast on `crossed` normalizes any future emitter drift (int/string → bool).
4. No untrusted user input touches the disposition shift path; the patch originates from the narrator's typed Pydantic schema.
5. No SQL/shell/eval/deserialization in the data flow.

**Pattern observed:**
Inline imports inside `if patch.npc_attitudes is not None:` at session.py:1156-1157 — matches the 7 other inline-import-inside-method-branch sites in `session.py` (lines 886, 991, 1013, 1060, 1064, 1098, 1145). Defensive against circular-import risk at module load time; consistent project style. Compliant.

**Error handling:**
- `disposition_attitude(int) -> str` has no error paths — exhaustive three-tier mapping with a final `return "neutral"` catch-all. No exception raised on extreme inputs (e.g., `disposition_attitude(10_000)` returns `"friendly"`, which is correct given the clamp upstream).
- `Span.open` is used as a context manager at session.py:1177; OTel handles its own teardown.
- Route lambda at telemetry/spans/disposition.py:17 uses `(span.attributes or {}).get(key, default)` for all 7 keys; never raises on malformed spans. Default values are typed sentinels (`""` for strings, `False` for bool, `0` for numbers) — tested by `test_disposition_shift_route_defaults_threshold_fields_when_missing`.

**Confirmed findings:**

| Severity | Issue | Location | Source | Recommended action |
|----------|-------|----------|--------|--------------------|
| [LOW] [DOC] | Wrong story attribution: comments reference "50-9" as the source of the cold-subsystem numeric promotion; 50-9 is the music mood-alias story per `epic-50.yaml`. The promotion was the sprint-3 audit (no story ID). | `tests/integration/test_disposition_threshold_crossing.py:3` and `:394` | `[DOC]` comment-analyzer | Strike "50-9" references; replace with "sprint-3 cold-subsystem audit". Follow-on chore. |
| [LOW] [RULE] | `asyncio.get_event_loop().time()` deprecated in Python 3.10+ when called from inside a running coroutine; should be `asyncio.get_running_loop().time()`. The same file uses `get_running_loop()` correctly at line 73 — inconsistency is visible. | `tests/integration/test_disposition_threshold_crossing.py:96-97` | `[RULE]` rule-checker + `[TEST]` test-analyzer (cross-confirmed) | One-line fix. Project-wide drift (sibling `test_disposition_otel_wiring.py` has same bug); could be a chore that fixes both. |
| [LOW] [RULE] | New public module `sidequest/game/disposition.py` has no `__all__`. Project convention (e.g., `sidequest/game/__init__.py`) uses `__all__` on public modules. | `sidequest/game/disposition.py:1` | `[RULE]` rule-checker | Add `__all__ = ["disposition_attitude"]` after the docstring. |
| [LOW] [TEST] | `delta=0` not tested. Production code currently emits a `disposition.shift` span with `before==after` and `crossed=False` on a zero-delta patch entry. No test documents the intended policy. | `tests/integration/test_disposition_threshold_crossing.py` (gap) | `[TEST]` test-analyzer | Defer — gap, not regression. Could add as part of the follow-on chore or as a future hardening story. |
| [LOW] [TEST] | Lower-bound clamp untested. Upper bound `before=95, delta=+50→100` is covered; mirror case `before=-95, delta=-50→-100` is not. Production paths are symmetric so no behavioral concern, but coverage is asymmetric. | `tests/integration/test_disposition_threshold_crossing.py` (gap) | `[TEST]` test-analyzer | Defer — gap, not regression. |
| [LOW] [TEST] | 50ms `await asyncio.sleep(0.05)` in `test_single_shift_emits_exactly_one_state_transition` introduces a wall-clock dependency for double-emit detection. `provider.force_flush()` would be deterministic. | `tests/integration/test_disposition_threshold_crossing.py:367` | `[TEST]` test-analyzer | Defer — common project pattern; CI tolerance for 50ms is generous. |
| [LOW] [TEST] | `test_disposition_shift_route_extracts_threshold_fields` passes `crossed=True` (already bool) to the route lambda's `bool(...)` cast — the cast is not actually exercised. Stronger test would pass `crossed=1` or `crossed="True"`. | `tests/telemetry/test_spans.py:248-263` | `[TEST]` test-analyzer | Defer — the defaults-test does cover the cast on the missing-key path. Strengthening is incremental. |

**Dispatched and dismissed:**

| Source | Subagent finding | Why dismissed |
|--------|-------------------|---------------|
| `[TEST]` test-analyzer | Single-emission guard scope: a second `Span.open` via the *global* tracer (not the monkeypatched local one) would escape the captured list. | Theoretical — there is exactly one `Span.open(SPAN_DISPOSITION_SHIFT, ...)` callsite in the codebase, and the only emission path uses `spans.tracer()` (the monkeypatched indirection). A second tracer path would be a new code structure, not a regression of this PR. |
| `[TEST]` test-analyzer | No wiring test for `opening.py` rendering path. | Pre-existing `opening.py` tests cover the rendering wiring. If the new `from sidequest.game.disposition import disposition_attitude` were broken at module load, all `opening.py`-importing tests (~hundreds of tests) would fail. The 5,089 non-50-11 tests passing IS the wiring proof. |
| `[TEST]` test-analyzer | Unknown-NPC patch entry silently skipped. | Pre-existing behavior in `apply_world_patch`; not introduced by 50-11. Worth a separate story to add a warning span for unknown NPCs, but out of scope here. |
| `[TEST]` test-analyzer | Global `watcher_hub` mutation in `_setup()`. | Pre-existing test-infra pattern shared with `test_disposition_otel_wiring.py`. Refactor to test-scoped hub is a test-infra story, not 50-11's concern. |
| `[DOC]` comment-analyzer | `disposition_attitude` lacks a function-level docstring. | CLAUDE.md: "Default to writing no comments. Only add one when the WHY is non-obvious." The 4-line body is self-evident from the function name + signature. The module docstring already carries the WHY (the forward-contract for 50-10). Adding a function docstring would describe WHAT the code does — which CLAUDE.md explicitly proscribes. |
| `[DOC]` comment-analyzer | session.py:1167 comment about "50-13 can land without revisiting this callsite" is technically misleading because 50-10 (which 50-13 depends on) WILL revisit the import line. | The spirit of the comment is about threshold-configuration changes (50-13's domain) not requiring an emission-site revisit. 50-10 is an unrelated refactor that happens to update the import line. The comment is accurate about what it claims. |
| `[DOC]` comment-analyzer | Deleted `_disposition_attitude` docstring claimed it mirrors `Npc.attitude()`, which doesn't exist. | The lying docstring is *deleted* by this PR. No live issue. The Dev assessment already records this as a finding for the 50-10 author's awareness. |

### Devil's Advocate

I argued the case for rejection. Here is what I considered and why each path returned to approval:

**Could a malicious narrator weaponize this?** The narrator emits typed Pydantic `WorldStatePatch.npc_attitudes` — values are clamped to `[-100, 100]` at session.py:1162. A huge int does nothing surprising; a negative becomes hostile; an absent key is ignored. No injection vector. The attitude strings flow only to OTel span attributes and to JSON in the watcher event — no SQL, no template eval, no shell. **Cleared.**

**Could a future Dev double-emit without anyone noticing?** The single-emission regression test catches the case where someone naively adds a second `Span.open(SPAN_DISPOSITION_SHIFT, ...)` in the same code path. It does *not* catch the case where someone adds a third tracer that bypasses `spans.tracer()` entirely. That's a theoretical structural risk, not a 50-11 regression. **Marked, but not blocking.**

**Could 50-10 break the contract this PR sets up?** The module docstring claims `Attitude` enum values must remain `"friendly"`/`"neutral"`/`"hostile"`. That's enforced by `test_attitude_strings_match_existing_helper_vocabulary` cross-checking the literal strings. If 50-10 renames an enum value, this test breaks loudly. **The forward contract is testable, not just aspirational.**

**Could the clamp interact badly with the band derivation?** Examined: `before=95, delta=+50 → clamped to 100 → still friendly`. `before=-95, delta=-50 → clamped to -100 → still hostile`. Both endpoints of the clamp align with the band the helper would assign; no off-by-one possible because the band check is `> 10` / `< -10` strict and the clamp bound `100` is squarely friendly. **Cleared.**

**Could a stressed filesystem produce surprising state?** Disposition shift writes nothing to disk. The save path (`SQLite at ~/.sidequest/saves/...`) serializes the NPC's final disposition, but the OTel span is in-memory and flushed via the watcher hub. Filesystem stress would affect the save layer, not this code path. **Cleared.**

**Could a stress test (10,000 shifts in one patch) blow up?** Each shift loops one `Span.open(...)` (microseconds). 10K = ~10ms. No memory accumulation — the span is immediately closed by the `with` context. The `watcher_hub` subscribers buffer events but the test harness clears between tests. **Cleared at typical playtest scale.**

**Could prompt injection through NPC names break anything?** NPC names come from the narrator's structured output. A name like `"; DROP TABLE npcs;--"` would just not match any NPC (silent skip — pre-existing behavior) or, if it happened to match by collision, would flow as a span attribute and into JSON. JSON serialization is safe; OTel attribute storage is safe. **Cleared, but the silent-skip is a pre-existing observability gap.**

**Could the deprecated `asyncio.get_event_loop()` break in Python 3.13+?** Python 3.13 made the deprecation more aggressive; future 3.14/3.15 may convert to `RuntimeError`. This test would break. **Real future-proofing risk — but this is the LOW finding I already confirmed under rule #9. Fix in follow-up.**

**Could the missing `__all__` allow accidental star-import of `__future__` machinery?** `from sidequest.game.disposition import *` would currently pull `disposition_attitude` plus `__future__.annotations` (which is a no-op). Not a security issue. **Cleared, but worth fixing for API hygiene.**

**Conclusion:** No critical or high-severity issues. Three confirmed LOW findings (1 doc-rot, 1 deprecated-API, 1 missing-`__all__`) plus four LOW test-coverage gaps. None block the merge. APPROVE.

**Verified pattern observations:**

- `[VERIFIED]` Three new span attributes set at session.py:1184-1186 AND extracted at telemetry/spans/disposition.py:23-25 — both sites updated in lock-step. Evidence: diff shows both files modified in commit `57f6cc6`. Complies with CLAUDE.md "Verify Wiring" rule (route + emission updated together).
- `[VERIFIED]` `crossed` is `before_attitude != after_attitude` — band identity, not magic-number predicate. Evidence: session.py:1186 reads `"crossed": before_attitude != after_attitude`. Canary tests at lines 280 and 304 of the new test file enforce this against naive impls. Complies with story AC6.
- `[VERIFIED]` `after_attitude` is computed from clamped post-mutation disposition. Evidence: `after = int(npc.disposition)` at session.py:1164 (after the clamp at line 1162), then `after_attitude = disposition_attitude(after)` at line 1166. The clamp test at line 255 of the test file confirms the clamped value drives the attitude string.
- `[VERIFIED]` Single emission per shift preserved. Evidence: only one `Span.open(SPAN_DISPOSITION_SHIFT, ...)` block in `apply_world_patch`. `test_single_shift_emits_exactly_one_state_transition` enforces this as a future invariant.
- `[VERIFIED]` Helper extraction preserves three-tier logic verbatim. Evidence: deleted lines at `opening.py:49-55` match new lines at `disposition.py:25-29` exactly (`> 10` / `< -10` strict boundaries, same return strings). Rule-checker confirmed under rule #13 (fix-regressions). Complies with ADR-020.

**Handoff:** To SM for finish-story.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with three pre-logged deviations the gate already accepts)
**Mismatches Found:** 2 substantive + 1 cosmetic; all already logged in TEA/Dev deviation subsections — no new drift introduced by Dev beyond what TEA anticipated.

### AC-by-AC Audit

| AC | Code surface | Verdict |
|---|---|---|
| AC1 — span includes `before_attitude`, `after_attitude`, `crossed` (bool) | `session.py:1180-1183` sets attrs; `telemetry/spans/disposition.py:22-24` extracts them | Aligned. Names exact. `crossed` typed as `bool` both at set site (`!=` comparison) and at route (`bool(...)` cast). |
| AC2 — `crossed=true` when band changes | `session.py:1183` `crossed = before_attitude != after_attitude` | Aligned. Behaviour matches spec; spec-text ADR reference is wrong (see Mismatch #1). |
| AC3 — attitude fields are string reps of `Attitude` enum | `game/disposition.py:25-29` returns literal strings | Forward-aligned via deviation. The enum doesn't exist yet (50-10 backlog); literal strings will become the enum's `.value` per the module docstring's contract claim. TEA Deviation #1 documents this. |
| AC4 — integration tests cover crossing + non-crossing | 13 tests in `tests/integration/test_disposition_threshold_crossing.py` | Aligned. Coverage: positive crossings (neutral→friendly, neutral→hostile, friendly→hostile two-band-jump), negatives (intra-band drift in friendly + neutral), back-crossing (11→10), clamp at +100, plus AC6 canaries. |
| AC5 — same callsite as current shift detector | Single `Span.open(SPAN_DISPOSITION_SHIFT, ...)` block at `session.py:1177-1188`; regression guard test passes | Aligned. No second emission site; the test `test_single_shift_emits_exactly_one_state_transition` enforces it as a future invariant. |
| AC6 — `crossed` correct even when threshold changes | `crossed` is computed from band strings, not from `delta` magnitude. Threshold literal `10`/`-10` lives in exactly one place (`game/disposition.py`) | Partially aligned via deferred deviation. The *predicate* is threshold-agnostic; the *threshold value* is still hardcoded. TEA Deviation #2 (50-13 owns making threshold configurable) and the implementation's single-source-of-truth structure together cover the spirit of AC6. See Mismatch #2. |

### Mismatch Analysis

**Mismatch #1 — Wrong ADR cited in AC2** (Cosmetic, Trivial)
- Spec: AC2 says "configureable threshold (currently ±10 default per ADR-090 or interim spec)".
- Code: Implementation correctly cites ADR-020 (NPC Disposition System) in module docstrings and span comments. ADR-090 is "OTEL Dashboard Restoration after Python Port" — unrelated.
- Recommendation: **C — Clarify spec.** The AC's "ADR-090" is a typo/transposition; should read "ADR-020". The "or interim spec" hedge in the AC text already covers the ambiguity, so behaviour is unaffected. Code is correct. **Logging this in Architect (reconcile) for the spec-reconcile phase to capture in the canonical deviation manifest.**
- Severity: trivial. Forward impact: none.

**Mismatch #2 — Threshold value still hardcoded** (Behavioral, Minor — deferred)
- Spec: AC6 says "no hardcoded assumptions" about the threshold.
- Code: The literal `10`/`-10` exists in `sidequest/game/disposition.py:25-29`. AC6 implies the threshold should be data-driven.
- Recommendation: **D — Defer.** Story 50-13 (genre-configurable thresholds; `depends_on: 50-10`) explicitly owns making thresholds configurable. 50-11's contribution is the *predicate structure* — `crossed` is derived from the band helper's output, so 50-13 can swap the threshold value at one point without touching the emission site or the route. This is the "no hardcoded assumptions" *in the cross-cutting flow*, even though one literal remains.
- TEA's Deviation #2 already records this trade-off; this analysis confirms it as the right call. No code change required.
- Severity: minor. Forward impact: 50-13 makes thresholds configurable; 50-11's `disposition_attitude` helper is the swap point. The canary tests (`test_large_delta_within_same_band_does_not_set_crossed`, `test_tiny_delta_across_boundary_sets_crossed_true`) continue to pass under 50-13 because they assert band-identity, not threshold value.

**Mismatch #3 — Spec did not anticipate the helper extraction** (Architectural, Trivial — positive drift)
- Spec: AC list focused on the OTEL span fields. The spec did not direct moving `_disposition_attitude` from `server/dispatch/opening.py` to `game/disposition.py`.
- Code: Dev created a new module `sidequest/game/disposition.py` and made the helper public. Two existing callsites in `opening.py` updated to the new import.
- Recommendation: **A — Update spec (implicitly accepted).** This was bounded boy-scouting required to satisfy AC6 without back-layering (game → server) or duplicating the `±10` literal. The new module is 22 lines and is the natural landing zone for 50-10's `Attitude` enum (the module docstring directs 50-10 there).
- Severity: trivial. Forward impact: positive — 50-10 lands the enum into an existing module rather than creating one. The forward-compat contract claim is asserted by `test_attitude_strings_match_existing_helper_vocabulary`.

### Architectural Notes (for Reviewer)

- **Inline imports preserved.** The `disposition_attitude` import is inline inside the `if patch.npc_attitudes` branch of `apply_world_patch`, matching the pre-existing inline imports of `SPAN_DISPOSITION_SHIFT, Span` immediately above it. Reviewer may want to ask whether the original inlining was defensive against circular imports — if not, hoisting all three to module-level imports is a follow-on cleanup. Not in scope for 50-11.
- **Forward-compat contract is real and tested.** `test_attitude_strings_match_existing_helper_vocabulary` cross-asserts that the emitted strings equal `disposition_attitude(...)` output. When 50-10 lands the `Attitude` enum, the enum's `.value` strings must remain `"friendly"`/`"neutral"`/`"hostile"` or this test fails — which is exactly the guardrail we want.
- **OTEL contract enriched, not broken.** All four pre-existing fields (`npc_name`/`delta`/`before`/`after`) remain. The route lambda now returns 8 keys (including `field`) instead of 5. GM panel consumers reading the new fields can pick them up; old consumers continue working unchanged.

**Decision:** Proceed to TEA verify (next phase) and then Reviewer. No hand-back required.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — 5,104 passed, 0 failed, 64 skipped in 106s. All 15 story-50-11 tests green.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (3 production, 3 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 findings — the `disposition_attitude` extraction is at exactly the right level (3 callers); span route lambda follows the existing pattern; tests use the standard async watcher harness; no consolidation opportunities. |
| simplify-quality | clean | 0 findings — types are explicit and correct, no dead code, defensive defaults in extract lambda, naming/imports consistent, comprehensive wiring + canary tests. |
| simplify-efficiency | clean | 0 findings — no premature abstraction, no gold-plating, single-emission preserved, Span.open argument dict is minimal. |

**Applied:** 0 high-confidence fixes (none needed)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean

### Quality Checks

- `uv run ruff check .` — All checks passed
- `uv run pytest` — **5,104 passed, 0 failed, 64 skipped in 106s**
- 15 new 50-11 tests all PASS:
  - `tests/integration/test_disposition_threshold_crossing.py` — 13/13 ✓
  - `tests/telemetry/test_spans.py::test_disposition_shift_route_extracts_threshold_fields` ✓
  - `tests/telemetry/test_spans.py::test_disposition_shift_route_defaults_threshold_fields_when_missing` ✓

### Note on pre-existing MP-joiner failures

Dev's earlier assessment recorded 2 pre-existing failures of `test_mp_joiner_suppresses_opening_seed`. On the verify-phase full run, those failures did not reproduce — current `develop`-merge state is fully green. Possibly flaky, possibly fixed by a sibling merge between Dev's run and Verify's run. **Not a 50-11 concern; no action.** Removing the entry from the deviation log would be revisionist; leaving it as Dev observed it.

### Delivery Findings

See `## Delivery Findings → TEA (test verification)` below.

**Handoff:** To Reviewer (Queen of Hearts) for code review.