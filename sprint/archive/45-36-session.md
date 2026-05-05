---
story_id: "45-36"
jira_key: ""
epic: "45"
workflow: "trivial"
---
# Story 45-36: 45-10 follow-up — reviewer cleanup (logger, vacuous test, doc fixes)

## Story Details
- **ID:** 45-36
- **Title:** 45-10 follow-up — reviewer cleanup (logger, vacuous test, doc fixes)
- **Jira Key:** (none — SideQuest uses sprint YAML tracking, no Jira)
- **Epic:** 45
- **Workflow:** trivial (chore, 1pt, p3)
- **Points:** 1
- **Priority:** p3
- **Type:** chore
- **Repos:** sidequest-server
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-05T08:57:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-05T08:25:25Z | 2026-05-05T08:25:25Z | 0s |
| implement | 2026-05-05T08:25:25Z | 2026-05-05T08:47:20Z | 21m 55s |
| review | 2026-05-05T08:47:20Z | 2026-05-05T08:57:03Z | 9m 43s |
| finish | 2026-05-05T08:57:03Z | - | - |

## Story Context

Story 45-36 bundles 14 non-blocking findings from the Reviewer's audit of story 45-10 (PR #106, sidequest-server). All findings are Medium/Low priority — **no behavioral defects**.

**Source:** `sprint/archive/45-10-session.md` → "Reviewer (code review)" delivery findings section.

### Substantive Items

1. **scrapbook_coverage.py missing logger** — Module emits OTEL on gap branch but has no `logger.warning()`. When GM panel is disconnected, stdout/journald is blind to the gap signal.
   - File: `sidequest/game/scrapbook_coverage.py:120`
   - Fix: Add module-level logger + `logger.warning('scrapbook.coverage_gap_detected genre=%s world=%s slug=%s gap_count=%d gap_rounds=%s', ...)`

2. **test_module_imports_cleanly is vacuous** — Test at `tests/server/test_scrapbook_coverage.py:177` has no assertions.
   - Fix: Either merge into the immediately-following `test_helper_function_exported` or add `assert hasattr(mod, "detect_scrapbook_coverage_gaps")`

3. **empty-store path missing silence assertion** — Test `test_empty_store_emits_evaluated_span_with_max_round_zero` at line 456 verifies the evaluated span but doesn't assert the gap span and watcher event are silent.
   - Fix: Add `assert _spans_named(otel_capture, 'scrapbook.coverage_gap_detected') == [] AND assert watcher_capture == []`

4. **_row_count f-string SQL** — Helper function at line 606 uses f-string interpolation (`f"SELECT COUNT(*) FROM {table}"`).
   - Fix: Either whitelist with `assert table in {"narrative_log", "scrapbook_entries"}` before the query, or inline the two queries directly at callers

5. **import json in loop bodies** — Two test files have `import json as _json` inside fixture bodies (rule #10 violation).
   - Files: `tests/server/test_scrapbook_coverage.py:119` and `tests/server/test_scrapbook_coverage_resume_wire.py:294`
   - Fix: Move to module/fixture top

### Documentation & Comment Cleanups

6. **Fixture comment at line 436** — Says "production join goes through narrative_log.round_number" but production doesn't join; it uses `max_narrative_round()` and queries `scrapbook_entries.turn_id` directly.
   - Fix: Replace with "production uses max_narrative_round() to bound the range and queries scrapbook_entries.turn_id directly"

7. **"Stub snapshot" comment at line 184** — Misleading; fixture creates a real `GameSnapshot`, not a test double.
   - Fix: Rename to "Minimal snapshot fixture"

8. **Legacy persona reference at connect.py:907-908** — Comment mentions "Felix's solo sessions" (Playtest 3 character not in current roster).
   - Fix: Replace with technical phrasing: "genre+world+player triple saves without a slug"

9. **Module docstring expansion** — `sidequest/game/scrapbook_coverage.py:16-19` should explain lockstep invariant.
   - Fix: Add that `narrative_log.round_number` is written from `turn_manager.interaction` at the narration site (`websocket_session_handler._execute_narration_turn`)

### Cross-Cutting Issue

10. **otel_capture fixture flakiness** — `SimpleSpanProcessor.shutdown()` does not deregister processors from the global `TracerProvider`, so processors accumulate across test sessions.
    - Files: `tests/server/conftest.py:917` and `tests/server/test_dice_throw_momentum_span.py:60`
    - Fix: Reset the global provider on each fixture setup for consistency

## Acceptance Criteria

All items from `sprint/epic-45.yaml` acceptance_criteria for 45-36:

- [ ] Add module logger + logger.warning() on the gap branch in `sidequest/game/scrapbook_coverage.py:120` with format `'scrapbook.coverage_gap_detected genre=%s world=%s slug=%s gap_count=%d gap_rounds=%s'`
- [ ] Fix vacuous `test_module_imports_cleanly` at `tests/server/test_scrapbook_coverage.py:177` — either merge into the immediately-following test_helper_function_exported, or add `assert hasattr(mod, "detect_scrapbook_coverage_gaps")`
- [ ] Add silence assertion at `tests/server/test_scrapbook_coverage.py:456` — assert `_spans_named(otel_capture, 'scrapbook.coverage_gap_detected') == []` AND `watcher_capture == []` on the empty-store path
- [ ] Strengthen substring check at `tests/server/test_scrapbook_coverage.py:363` — replace `assert "11" in gap_str and "29" in gap_str` with `tuple(gap_rounds_attr) == tuple(range(11, 30))` when sequence-typed, with string-parse fallback for SDK-serialised case
- [ ] Add SpanRoute.extract invocation tests in TestSpanRouting — construct fake span with known attributes and assert each route.extract returns the expected dict shape (currently only route.component is asserted)
- [ ] Add edge-case test: non-contiguous gap pattern (rounds 1-5 + 8-10 covered, expecting gap_rounds == [6, 7])
- [ ] Add edge-case test: out-of-range scrapbook rows (turn_id=0 and turn_id=max_round+5) — assert WHERE filter excludes them
- [ ] Whitelist or inline `_row_count` f-string SQL at `tests/server/test_scrapbook_coverage.py:606` — either `assert table in {"narrative_log", "scrapbook_entries"}` before the query, or inline the two queries directly at their callers
- [ ] Move `import json as _json` to fixture/module top in `tests/server/test_scrapbook_coverage.py:119` and `tests/server/test_scrapbook_coverage_resume_wire.py:294`
- [ ] Fix stale fixture comment at `tests/server/test_scrapbook_coverage.py:436` — replace 'production join goes through narrative_log.round_number' with 'production uses max_narrative_round() to bound the range and queries scrapbook_entries.turn_id directly'
- [ ] Rename 'Stub snapshot' comment at `tests/server/test_scrapbook_coverage.py:184` to 'Minimal snapshot fixture'
- [ ] Replace 'Felix's solo sessions' persona reference at `sidequest/handlers/connect.py:907-908` with technical phrasing ('genre+world+player triple saves without a slug')
- [ ] Expand module docstring at `sidequest/game/scrapbook_coverage.py:16-19` to explain that narrative_log.round_number is written from turn_manager.interaction at the narration site (websocket_session_handler._execute_narration_turn) — the lockstep invariant is non-obvious otherwise
- [ ] Address otel_capture fixture flakiness in `tests/server/conftest.py:917` — SimpleSpanProcessor.shutdown() does not deregister from the global TracerProvider; processors accumulate across the session. Reset the global provider on each fixture setup. Same defect in `tests/server/test_dice_throw_momentum_span.py:60` (45-3 work) — fix both for consistency

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **Improvement** (non-blocking): The full server test suite has 18 pre-existing failures unrelated to 45-36 — all in `tests/genre/test_loader_hub_world.py`, `tests/genre/test_models/test_pack_integration.py` (hub/grimvault world fixtures), `tests/integration/test_npc_wiring.py` (2 span-route tests), and `tests/server/test_rest.py::test_debug_state_projects_saved_game`. Verified by stash-and-rerun against baseline: identical 18 failures with and without my changes. Affects sprint health metrics only — file separately.
  *Found by Dev during implementation.*

- **Improvement** (non-blocking): The 45-36 otel_capture fix (clear `_span_processors` instead of swap provider) also incidentally fixed a pre-existing cross-test contamination affecting `tests/server/test_chargen_loadout.py::TestStartingKitDedupSpans` (6 tests) and `tests/server/test_chargen_persist_and_play.py::TestChargenPersistAndPlay` (2 tests + 1 sibling). Total bonus fixes: 9 tests that were silently failing in CI. Root cause: the old fixture's `init_tracer() → get_tracer_provider()` path returned the same singleton across fixture invocations, accumulating processors on `provider._active_span_processor._span_processors`; production modules cache `otel_trace.get_tracer(__name__)` at import (e.g. `sidequest/server/dispatch/chargen_loadout.py:31`) and span emission via the cached tracer hit only the FIRST processor, which had been shut down between tests.
  *Found by Dev during implementation.*

- **Question** (non-blocking): AC pointer for AC12 names `sidequest/handlers/connect.py:907-908` for the "Felix's solo sessions" persona reference, but the actual reference is in `tests/server/test_scrapbook_coverage_resume_wire.py:18`. Fixed the real location. The connect.py path may have been stale at audit time or a lookup error in the AC. Affects AC pointer accuracy in future similar cleanup stories — recommend verifying file paths before filing.
  *Found by Dev during implementation.*

- **Question** (non-blocking): AC10 names "fixture comment at line 436" but the only `production join goes through narrative_log.round_number` comment in `tests/server/test_scrapbook_coverage.py` is at line 105 (in the `populated_store` fixture). The line 436 location is inside a test docstring assertion message about gap-span emission, not a fixture comment. Replaced the actual stale comment per the spirit of the AC.
  *Found by Dev during implementation.*

### Reviewer (code review)

- **Improvement** (non-blocking): The `(45-36 fix)` story-ID label appears in 3 places — `tests/server/conftest.py:1105` (docstring heading) + `:1140` (inline back-reference) and `tests/server/test_dice_throw_momentum_span.py:69`. CLAUDE.md explicitly prohibits this pattern. Affects those 3 lines (rename to `Provider reset rationale:` and update the inline back-reference accordingly).
  *Found by Reviewer during code review.*

- **Improvement** (non-blocking): `_row_count` whitelist guard at `tests/server/test_scrapbook_coverage.py:879` uses `assert table in _ROW_COUNT_TABLE_WHITELIST` — the docstring claims python.md rule #11 protection, but `assert` is stripped under `python -O`. Affects the docstring's documented contract. Replace with `if table not in _ROW_COUNT_TABLE_WHITELIST: raise ValueError(...)` to make the protection survive optimization. Also clarify the docstring causality — "the whitelist makes the f-string safe" rather than "non-exploitable from test inputs but the whitelist pins the surface."
  *Found by Reviewer during code review.*

- **Improvement** (non-blocking): `TestGapPatternEdgeCases::test_non_contiguous_gap_pattern` (test_scrapbook_coverage.py:736) and `::test_out_of_range_scrapbook_rows_excluded` (line 803) request `otel_capture` and `watcher_capture` fixtures but never assert on them. Per CLAUDE.md OTEL discipline, tests should verify both fire-when-expected (the gap test should assert the gap span fires with `gap_rounds == (6, 7)` and the watcher event publishes) and silent-when-not-expected (the out-of-range test should assert the gap span and watcher event stay silent despite the noise rows). Affects test value: a half-fix that gets `gap_count` correct but mis-fires the OTEL surface would pass these tests today.
  *Found by Reviewer during code review.*

- **Improvement** (non-blocking): `sidequest/telemetry/spans/scrapbook.py:59` — `gap_rounds` extractor default is `""` (empty string), inconsistent with all other numeric defaults (`0`) and with the populated value type (tuple). Pre-existing in 45-10's work, not in 45-36's diff. Affects the contract of `SPAN_SCRAPBOOK_COVERAGE_GAP_DETECTED` route extractor — an unreachable branch in production today, but a type-shape regression hazard. Pair with adding a missing-attributes test for the gap_detected route in a follow-up.
  *Found by Reviewer during code review.*

- **Improvement** (non-blocking): `sidequest/game/scrapbook_coverage.py` is missing `__all__` declaration. Sibling modules in `sidequest/game/` (ability.py, builder.py, lore_embedding.py, belief_state.py, lore_seeding.py, region_init.py, region_validation.py, room_movement.py) all declare one. Pre-existing from 45-10's work. Affects public-API clarity. Could be addressed alongside a broader `__all__` audit of `sidequest/game/`.
  *Found by Reviewer during code review.*

- **Improvement** (non-blocking): `provider._active_span_processor._span_processors = ()` at `tests/server/conftest.py:1141` and `tests/server/test_dice_throw_momentum_span.py:90` bypasses the `threading.Lock` (`_lock`) that `SynchronousMultiSpanProcessor.add_span_processor` holds when mutating `_span_processors`. The OTel SDK has no public clear/remove API in this version, so the private-attribute write is pragmatically forced — but the lock bypass is undocumented. If pytest-xdist is ever introduced, this becomes a real race. Affects test infrastructure resilience — wrap the assignment in `with provider._active_span_processor._lock:` for forward-compatibility.
  *Found by Reviewer during code review.*

- **Question** (non-blocking): `tests/server/test_scrapbook_coverage.py:752` constructs a database path via f-string: `db_path = f"{td}/non-contig.db"`. Python rule #5 prefers `pathlib`. Affects test code only (not user-facing path handling). Could be `str(Path(td) / "non-contig.db")` for consistency with the `populated_store` fixture's `tmp_path / f"cov-{n}-{m}.db"` style.
  *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **AC14 fix uses processor-list reset, not provider swap**
  - Spec source: `sprint/epic-45.yaml` story 45-36 AC #14
  - Spec text: "SimpleSpanProcessor.shutdown() does not deregister from the global TracerProvider; processors accumulate across the session. Reset the global provider on each fixture setup."
  - Implementation: Cleared `provider._active_span_processor._span_processors` to `()` on each fixture setup, rather than constructing a new `TracerProvider()` and swapping the global. Matches the AC's stated goal (no stale processors) but preserves the existing provider singleton.
  - Rationale: A first attempt at literal "reset the global provider" (provider swap via `otel_trace._TRACER_PROVIDER = TracerProvider()`) broke 6+ chargen tests because `sidequest/server/dispatch/chargen_loadout.py:31` and similar production modules cache `otel_trace.get_tracer(__name__)` at module import, binding the cached tracer to the old (now-orphaned) provider. The processor-list reset achieves the same goal (no accumulated processors) without the side effect.
  - Severity: minor
  - Forward impact: none — the AC is satisfied, and the fix is more conservative than the literal spec

- **AC10 fix targets a different line than the AC pointer**
  - Spec source: `sprint/epic-45.yaml` story 45-36 AC #10
  - Spec text: "Fix stale fixture comment at `tests/server/test_scrapbook_coverage.py:436` — replace 'production join goes through narrative_log.round_number' with 'production uses max_narrative_round() to bound the range and queries scrapbook_entries.turn_id directly'"
  - Implementation: Fixed the stale comment at line 105 (the actual location in the `populated_store` fixture). Line 436 is inside a test assertion message, not a fixture comment.
  - Rationale: The intent of the AC is unambiguous (kill the stale "production join" claim) and only one such comment exists in the file. Fixing line 105 satisfies the spirit of the AC; literally editing line 436 would be wrong.
  - Severity: trivial
  - Forward impact: none

- **AC12 fix targets a different file than the AC pointer**
  - Spec source: `sprint/epic-45.yaml` story 45-36 AC #12
  - Spec text: "Replace 'Felix's solo sessions' persona reference at `sidequest/handlers/connect.py:907-908`"
  - Implementation: Fixed the actual reference in `tests/server/test_scrapbook_coverage_resume_wire.py:18`. `connect.py` does not contain the string "Felix" anywhere.
  - Rationale: A grep across `sidequest/handlers/connect.py` returns no match for "Felix" or "solo session" — the AC pointer is stale or wrong. The intended target is the test docstring describing the legacy resume path, which I corrected.
  - Severity: trivial
  - Forward impact: none

### Reviewer (audit)

- **AC14 fix uses processor-list reset, not provider swap** → ✓ ACCEPTED by Reviewer: more conservative than literal spec, with concrete evidence (chargen tests would break under provider swap). Diagnose-before-fix is exactly the right move.
- **AC10 fix targets a different line than the AC pointer** → ✓ ACCEPTED by Reviewer: AC line numbers were stale (line 436 is in an assertion message, not a fixture comment). Only one stale comment of that shape exists; correct location was fixed.
- **AC12 fix targets a different file than the AC pointer** → ✓ ACCEPTED by Reviewer: verified via grep — `sidequest/handlers/connect.py` contains no "Felix" string. Real reference was in test docstring; correctly fixed.

**Undocumented deviation observed:**
- **Comment-style deviation:** New `(45-36 fix)` story-ID labels were added in 3 places (conftest.py x2, test_dice_throw_momentum_span.py x1) despite CLAUDE.md explicitly prohibiting "reference the current task, fix, or callers" in code comments. Severity: LOW. Not flagged in dev's deviation log because dev judged the technical content (not the label) was load-bearing. The label IS the violation, not the explanation it sits in.


## Impact Summary

### Key Metrics
- **Acceptance Criteria:** 14 total, 14 completed (100%)
- **Targeted Test Suite:** 62/62 passing (100%)
- **Bonus Fixes:** 9 pre-existing chargen test failures resolved by AC14 fix
- **Code Quality Findings:** 10 confirmed (2 Medium, 4 Low, 4 pre-existing/deferred)

### Substantive Fixes Delivered
1. **Module Logger Coverage** — `scrapbook_coverage.py` now emits `logger.warning()` on gap detection with proper lazy formatting, enabling blind-spot visibility when GM panel is disconnected (AC1)
2. **Test Assertion Strengthening** — Vacuous `test_module_imports_cleanly` fixed (AC2); substring checks → exact tuple comparisons (AC4); silence assertions added to empty-store path (AC3)
3. **OTEL Discipline Enforcement** — New `SpanRoute.extract` invocation tests validate span-routing integration (AC5); edge-case tests for non-contiguous gaps (AC6) and out-of-range rows (AC7) now properly exercised
4. **Cross-Test Contamination Eliminated** — `otel_capture` fixture now clears `_span_processors` on setup, fixing chargen test suite cross-contamination that was silently failing in CI (AC14)

### Findings Status
**Blocking Issues:** None
**Ready to Merge:** Yes

### Follow-Up Work Required (filed as issue, not blocking)
- **[MEDIUM]** Reviewer-confirmed issues for cleanup story 45-N:
  - `_row_count` whitelist uses `assert` (stripped under `python -O`); replace with explicit `if...raise ValueError`
  - New edge-case tests don't assert on OTEL fixtures they request (CLAUDE.md OTEL discipline)
  - `(45-36 fix)` story-ID labels in 3 places (CLAUDE.md "no current-task references")
  - Path construction at line 752 uses f-string instead of pathlib (rule #5)
  - `_span_processors` mutation lacks lock wrapper (pytest-xdist forward-compatibility)
  - Pre-existing: `sidequest/game/scrapbook_coverage.py` missing `__all__` declaration
  - Pre-existing: `gap_rounds` extractor default asymmetry (string vs. tuple)

### Health Assessment
- **Code Health:** Lint clean on changed files; all AC's substantively satisfied
- **Test Health:** 62/62 targeted suite passes; 18 pre-existing failures verified unrelated
- **Integration:** Production module uses parameterized SQL (safe); logger uses lazy %s interpolation (rule #4 compliant); no regressions to existing behavior

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/scrapbook_coverage.py` — added module logger + `logger.warning()` on the gap branch (AC1); expanded module docstring to explain where `narrative_log.round_number` is written (AC13).
- `tests/server/test_scrapbook_coverage.py` — moved `import json as _json` to module top (AC9 part 1); fixed vacuous `test_module_imports_cleanly` with `hasattr` assertion (AC2); added silence assertions to empty-store path (AC3); strengthened gap_rounds substring check to exact tuple-or-parsed-equality (AC4); added 3 `SpanRoute.extract` invocation tests (AC5); added `TestGapPatternEdgeCases` class with non-contiguous gap test (AC6) and out-of-range scrapbook rows test (AC7); whitelisted `_row_count` table parameter (AC8); fixed stale fixture comment (AC10, line 105); renamed "Stub snapshot" to "Minimal snapshot fixture" (AC11).
- `tests/server/test_scrapbook_coverage_resume_wire.py` — moved `import json as _json` to module top (AC9 part 2); replaced "Felix's solo sessions" with technical phrasing (AC12 — actual location, not the file/line in the AC).
- `tests/server/conftest.py` — `otel_capture` fixture now clears `provider._active_span_processor._span_processors` on setup, eliminating cross-test processor accumulation (AC14 part 1).
- `tests/server/test_dice_throw_momentum_span.py` — same `_span_processors` reset for the local `otel_capture` fixture (AC14 part 2).

**Tests:** 62/62 targeted tests passing (test_scrapbook_coverage + test_scrapbook_coverage_resume_wire + test_dice_throw_momentum_span + test_chargen_loadout). Full server suite has 18 pre-existing failures unrelated to this story (verified via stash-and-rerun); these are the same failures present before any 45-36 work.

**Branch:** `feat/45-36-45-10-followup-reviewer-cleanup` (sidequest-server, based on develop)

**Lint:** `ruff check` clean, `ruff format` applied.

**Handoff:** To review phase (Westley / Reviewer).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 3, dismissed 0, deferred 2 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 4, dismissed 0, deferred 1 |

**All received:** Yes (4 enabled, 4 returned; 5 disabled per settings)
**Total findings:** 10 confirmed, 0 dismissed, 3 deferred

### Confirmed findings (cross-referenced)

1. **[MEDIUM] [RULE 11]** `_row_count` whitelist guard uses `assert` (test_scrapbook_coverage.py:879).
   The fixed-up docstring claims it "protects against attacker-controlled name (python.md rule #11)" but `assert` statements are stripped under `python -O`. The whitelist is then a no-op in optimized builds. The test code never runs under `-O` in this project, so practical impact is nil — but the docstring overstates the protection. Fix is one-liner: `if table not in _ROW_COUNT_TABLE_WHITELIST: raise ValueError(...)`. Caught by both rule-checker and comment-analyzer (the latter via the "non-exploitable from test inputs" causality-inversion finding).

2. **[MEDIUM] [TEST]** New edge-case tests in `TestGapPatternEdgeCases` request `otel_capture` and `watcher_capture` fixtures but never assert on them (test_scrapbook_coverage.py:736 and :803).
   - `test_non_contiguous_gap_pattern` exercises `gap_count > 0` (gap = [6, 7]) — per the OTEL discipline rule from CLAUDE.md, the gap span and watcher event MUST fire for this case. The test should assert that.
   - `test_out_of_range_scrapbook_rows_excluded` exercises `gap_count == 0` with noise rows — the gap span must NOT fire. The test should assert silence.
   - The story itself just added these silence/fire assertions to the empty-store path (AC3); the new tests should follow the same pattern. The fixtures are required for monkeypatching `_watcher_publish` but the captured data goes unchecked.

3. **[LOW] [DOC]** `(45-36 fix)` story-ID labels embedded in 3 places (conftest.py:1105 docstring + :1140 inline; test_dice_throw_momentum_span.py:69 docstring).
   CLAUDE.md explicitly says: "Don't reference the current task, fix, or callers — those belong in PR description, rot in the codebase." This is a project-rule-explicit violation that cannot be dismissed (per Reviewer's PROJECT RULES are not suggestions). Severity is LOW (style only); fix is rename to `**Provider reset rationale:**` and `# see "Provider reset rationale:" above`.

4. **[LOW] [RULE 5]** Path construction with f-string at test_scrapbook_coverage.py:752: `f"{td}/non-contig.db"`. CLAUDE.md python rule #5 prefers pathlib: `str(Path(td) / "non-contig.db")`. Test code, not user-facing — minor.

5. **[LOW] [RULE 13]** otel_capture lock bypass on `_span_processors` (conftest.py:1141 + test_dice_throw_momentum_span.py:90). The mutation `provider._active_span_processor._span_processors = ()` does not acquire `_lock` that `add_span_processor` holds. Acceptable for synchronous test runs (current state) but a latent race under pytest-xdist. Docstring acknowledges the private-API access via `# type: ignore[attr-defined]` but doesn't note the lock bypass. The OTel SDK has no public clear/remove API — the approach is pragmatically forced.

### Deferred findings

- **[DEFERRED] [RULE 10]** `sidequest/game/scrapbook_coverage.py` missing `__all__` declaration (rule-checker). This is **pre-existing** in develop — the module was authored in 45-10 without `__all__`. Not introduced by this PR. File a separate cleanup story for sidequest/game/ `__all__` audit.

- **[DEFERRED] [TEST]** Asymmetric default in `SPAN_SCRAPBOOK_COVERAGE_GAP_DETECTED` extractor: `gap_rounds` defaults to `""` (string) rather than `()` (tuple). The asymmetry is in `sidequest/telemetry/spans/scrapbook.py:59` — also **pre-existing**, not in this PR's diff. The new `test_evaluated_route_extract_handles_missing_attributes` doesn't have a parallel for gap_detected route. Worth a follow-up to (a) symmetrize the extractor defaults and (b) add the missing test. File separately.

- **[DEFERRED] [TEST]** Dead string-repr branch in gap_rounds parsing — the `else` branch with `re.findall(r"-?\d+", ...)` is never exercised by tests because OTel SDK always returns sequence types in the in-memory exporter path. Not a regression; out of scope for this story.

### Rule Compliance

Mapped to `.pennyfarthing/gates/lang-review/python.md` (13 rules):

| # | Rule | Compliance |
|---|------|------------|
| 1 | Silent exception swallowing | COMPLIANT — `contextlib.suppress(Exception)` in fixture cleanup has the required explanatory comment (test_scrapbook_coverage.py:152-154) |
| 2 | Mutable default arguments | COMPLIANT — no mutable defaults across 5 changed files |
| 3 | Type annotation gaps | COMPLIANT — all public boundaries (detect_scrapbook_coverage_gaps, _make) annotated; test helpers (_FakeSpan, _spans_named, _row_count) exempt as private |
| 4 | Logging coverage AND correctness | COMPLIANT — logger added at module level, warning() inside gap branch, %s lazy interpolation, no f-strings, no sensitive data |
| 5 | Path handling | 1 VIOLATION — test_scrapbook_coverage.py:752 uses f-string path construction (LOW) |
| 6 | Test quality | COMPLIANT — fixed vacuous test_module_imports_cleanly with hasattr; strengthened gap_rounds substring → exact tuple/parsed equality; whitelist on _row_count; 28 test functions checked, all have meaningful assertions |
| 7 | Resource leaks | COMPLIANT — store.close() in try/finally, tempfile.TemporaryDirectory as context manager, processor.shutdown() in finally |
| 8 | Unsafe deserialization | COMPLIANT — only json.dumps() (serialize), no pickle/yaml.load/eval/exec/shell=True |
| 9 | Async/await pitfalls | COMPLIANT — no async code in changed lines |
| 10 | Import hygiene | 1 PRE-EXISTING (deferred) — scrapbook_coverage.py missing __all__ (not in diff scope) |
| 11 | Security: input validation | 1 VIOLATION — _row_count uses `assert` for whitelist; stripped under `python -O` (MEDIUM) |
| 12 | Dependency hygiene | COMPLIANT — pyproject.toml unchanged |
| 13 | Fix-introduced regressions | 2 VIOLATIONS — _span_processors lock bypass in conftest.py + test_dice_throw_momentum_span.py (LOW, pragmatically forced by OTel API gap) |

### Devil's Advocate

Suppose I am a future maintainer 6 months from now. The `(45-36 fix)` labels in two fixture docstrings are confusing — what's 45-36? I have to dig through git history to find a sprint story that was archived 6 sprints ago. The actual rationale in the docstring is sound, but the label is dead weight. CLAUDE.md was explicit about this exact failure mode for exactly this reason.

Suppose I am running tests under `python -O` for performance. The `_row_count` whitelist disappears. The docstring tells me it protects against attacker names. I trust the docstring. A future caller passes a user-provided table name (perhaps in a refactor that exposes `_row_count` to a CLI) and we have a SQL injection — even though the docstring claimed otherwise. The `assert` form fails CLAUDE.md "no silent fallbacks" because the validation silently disappears under -O.

Suppose I am writing the next gap-pattern edge case in 45-XX. I look at `test_non_contiguous_gap_pattern` for the pattern. It requests `otel_capture` and `watcher_capture` but never asserts on them. I conclude the convention is "ignore the captures, just check the report." I write 5 more tests this way. The OTEL discipline corrodes one test at a time. The CLAUDE.md OTEL principle is exactly the rule that this story was written to enforce — and yet the new tests don't enforce it themselves.

Suppose pytest-xdist gets enabled in CI tomorrow. The lock bypass on `_span_processors` becomes a real race. The fix would have been a one-line `with provider._active_span_processor._lock:` wrapper.

Suppose someone reads `_row_count`'s docstring "non-exploitable from test inputs" and concludes "test inputs are inherently safe, I can drop the whitelist." The docstring inverts the causality — the safety comes FROM the whitelist, not IN SPITE OF it. This is the same class of bug as the dev's own deviation #1 (literal "reset the global provider" would have broken cached tracers): the documented intent and the actual code mechanism diverge.

Of these worries, only the docstring-vs-mechanism mismatch in `_row_count` and the OTEL-discipline corrosion in the new tests are *materially* concerning. The story-ID labels and lock bypass are real but contained.

### Verified-with-evidence

- **[VERIFIED]** logger uses %s lazy interpolation per python.md rule #4 — sidequest/game/scrapbook_coverage.py:127-134 calls `logger.warning("...%s...", arg, ...)` with positional args; no f-strings. Complies with rule #4.
- **[VERIFIED]** Empty-store silence assertions added — test_scrapbook_coverage.py:498-507 asserts `_spans_named(otel_capture, "scrapbook.coverage_gap_detected") == []` AND `gap_publishes == []` on max_round==0 path. AC3 satisfied.
- **[VERIFIED]** gap_rounds substring check strengthened — test_scrapbook_coverage.py:381-401 replaces fuzzy substring with exact `tuple(gap_rounds_attr) == tuple(range(11, 30))` for sequence types and `re.findall(r"-?\d+", ...)` parse-then-compare for stringified types. The off-by-one regressions ("111", "291", "229") that the old check would have masked are now caught.
- **[VERIFIED]** SQL parameterized in production module — sidequest/game/scrapbook_coverage.py:90-92 uses `WHERE turn_id >= 1 AND turn_id <= ?` with `(max_round,)` tuple. No f-string interpolation in the production query path. Complies with rule #11 at the boundary that actually matters.
- **[VERIFIED]** Daemon guard intact — tests/server/conftest.py changes are limited to the `otel_capture` fixture; `_mock_daemon_client` autouse guard at line 154 unchanged. No risk of daemon socket round-trip leaking into the suite.

## Reviewer Assessment

**Verdict:** APPROVED

**Severity check:** 0 Critical, 0 High, 2 Medium, 3 Low → meets the APPROVE threshold per the severity rubric (Medium and below do not block).

**Data flow traced:** `detect_scrapbook_coverage_gaps(store, snapshot, slug)` → `store.max_narrative_round()` + parameterized `SELECT DISTINCT turn_id ... WHERE turn_id >= 1 AND turn_id <= ?` → set-difference math → `Span.open(SPAN_SCRAPBOOK_COVERAGE_EVALUATED)` always + `logger.warning() + Span.open(SPAN_SCRAPBOOK_COVERAGE_GAP_DETECTED) + _watcher_publish("scrapbook_coverage_gap", severity="warning")` when `gap_count > 0`. Safe because the only user-controlled inputs (genre/world/slug) are span attributes (string-only), not SQL interpolated; the SQL is parameterized.

**Pattern observed:** Test-strengthening pattern consistently applied — vacuous-assertion fix at test_scrapbook_coverage.py:181 with hasattr(); fuzzy-substring → exact-or-parsed equality at line 363; silence assertions added to empty-store path at line 498. The same pattern was NOT applied to the new `TestGapPatternEdgeCases` tests (Finding 2) — that is the one substantive test-quality finding.

**Error handling:** `if gap_count > 0:` branch now logs warning AND fires gap span AND publishes watcher event — three independent observability surfaces, none silent. Empty-store path correctly emits `coverage_evaluated` only (negative confirmation) without falsely firing the gap branch.

**Bonus observation:** Dev's AC14 fix (clear `_span_processors` instead of swap provider) incidentally resolved 9 pre-existing chargen test failures from cross-test contamination. Verified via stash-and-rerun (Dev's delivery finding). This is a real quality win and a good example of "diagnose before fix" — the literal spec ("reset the provider") would have been a regression.

**Confirmed findings tagged by specialist source:**
- `[RULE]` `_row_count` `assert` whitelist stripped under `python -O` (rule #11) — test_scrapbook_coverage.py:879 — MEDIUM
- `[TEST]` New edge-case tests don't assert on `otel_capture`/`watcher_capture` fixtures they request (CLAUDE.md OTEL discipline) — test_scrapbook_coverage.py:736 + :803 — MEDIUM
- `[DOC]` `(45-36 fix)` story-ID labels in 3 places (CLAUDE.md "don't reference the current task") — conftest.py:1105 + :1140 + test_dice_throw_momentum_span.py:69 — LOW
- `[RULE]` Path f-string construction (rule #5) — test_scrapbook_coverage.py:752 — LOW
- `[RULE]` `_span_processors` lock bypass (rule #13 fix-introduced regression) — conftest.py:1141 + test_dice_throw_momentum_span.py:90 — LOW
- `[DOC]` `_row_count` docstring causality inversion ("non-exploitable from test inputs") — test_scrapbook_coverage.py:506 — LOW

**Recommendation:** APPROVED to merge. The 2 Medium and 4 Low findings should be filed as a follow-up cleanup story (call it 45-N in a future sprint) on the same pattern that 45-36 itself follows for 45-10. Total cleanup scope: ~30 lines across 4 files. Could be combined with the deferred `__all__` audit and the `gap_rounds` extractor default symmetrization for a single 1-2pt chore.

**Handoff:** To SM for finish-story.