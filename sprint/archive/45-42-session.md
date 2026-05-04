---
story_id: "45-42"
jira_key: null
epic: "45"
workflow: "tdd"
note: "Carried out in subrepo branches/PRs as 45-41 before tracker collision detected — ID renumbered to 45-42 at finish-time. Subrepo artifacts (branch feat/45-41-confrontation-calibration-v1, PRs slabgorb/sidequest-server#190, slabgorb/sidequest-content#177) remain labeled 45-41."
---
# Story 45-42: Confrontation Difficulty Calibration v1

## Story Details
- **ID:** 45-42 (originally branched and PR'd as 45-41; renumbered after merge — see frontmatter note)
- **Jira Key:** (not yet created)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-04T10:58:33Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04 | 2026-05-04T09:57:58Z | 9h 57m |
| red | 2026-05-04T09:57:58Z | 2026-05-04T10:10:17Z | 12m 19s |
| green | 2026-05-04T10:10:17Z | 2026-05-04T10:24:04Z | 13m 47s |
| spec-check | 2026-05-04T10:24:04Z | 2026-05-04T10:29:23Z | 5m 19s |
| verify | 2026-05-04T10:29:23Z | 2026-05-04T10:37:42Z | 8m 19s |
| review | 2026-05-04T10:37:42Z | 2026-05-04T10:48:49Z | 11m 7s |
| spec-reconcile | 2026-05-04T10:48:49Z | 2026-05-04T10:58:33Z | 9m 44s |
| finish | 2026-05-04T10:58:33Z | - | - |

## Sm Assessment

**Setup Complete:** Yes
**Story:** 45-41 — Confrontation difficulty calibration v1 (ADR-093)
**Workflow:** tdd (phased)
**Repos:** server, content
**Branch:** feat/45-41-confrontation-calibration-v1 (created in both repos)
**Context:** sprint/context/context-story-45-41.md (written, references ADR-093 implementation pointer)
**Acceptance Criteria:** 7 ACs declared in epic-45.yaml
**Source ADR:** docs/adr/093-confrontation-difficulty-calibration.md (status: accepted, implementation: deferred)

**Routing:** TEA (Fezzik) for the RED phase. Distribution-assertion test is the load-bearing AC — TEA needs to write a Monte-Carlo test that simulates 10k opposed_check rolls at calibrated parameters (player +1, opponent +0, tie band ±1) and asserts the resulting tier distribution lands within ±5pp of the ADR-093 expected: ~45% Success-or-better, ~33% Tie, ~22% Fail-or-worse. Plus failing tests for the band-narrowing constants and the YAML calibration sweeps.

**Handoff:** To TEA (red phase).

## Tea Assessment

**Tests Written:** Yes — 3 test files committed, RED state confirmed.
**Branch:** feat/45-41-confrontation-calibration-v1 (pushed to origin)
**Repos modified:** sidequest-server only (test files; no content changes)

### Files

- **`tests/game/test_opposed_check.py`** (modified): flipped the existing ±2 boundary tests to assert the calibrated ±1 tie band. Two existing tests at the ±2 boundary became `test_shift_at_plus_2_is_success_not_tie` and `test_shift_at_minus_2_is_fail_not_tie`. Added new explicit boundary tests at ±1 (`test_shift_at_plus_1_is_tie_top_of_band`, `test_shift_at_minus_1_is_tie_bottom_of_band`) so the new band geometry is locked in both directions. Updated module docstring.

- **`tests/game/test_opposed_check_distribution.py`** (new): three tests covering the load-bearing AC.
  - `test_calibrated_distribution_meets_adr_093_targets` — 10k Monte-Carlo, deterministic seed (45041), asserts distribution within ±5pp of analytical expected values.
  - `test_calibrated_distribution_player_edge_is_real` — sanity guard that Success+ exceeds Fail+ by ≥ 5pp under calibrated stats. Catches any regression where the band shrinks but the opponent modifier doesn't drop.
  - `test_calibrated_band_geometry` — parametrized boundary geometry assertions through the full resolver (not just `_tier_from_shift`), pinning shifts +2/+1/0/-1/-2/+10 to their expected tiers.

- **`tests/genre/test_confrontation_calibration.py`** (new): five tests covering YAML data calibration.
  - `test_opponent_default_stats_no_parity_12_remains` (parametrized over 5 packs) — no `opponent_default_stats` value may equal 12 or exceed 10.
  - `test_opposed_check_thresholds_calibrated_to_7` (parametrized over 5 packs) — every confrontation with `resolution_mode: opposed_check` must have both metric thresholds at 7.
  - `test_sealed_letter_thresholds_unchanged` (parametrized) — sealed-letter confrontations stay at 30.
  - `test_negotiation_thresholds_not_collapsed_below_5` (parametrized) — guard against accidental over-shortening of social scenes.
  - `test_at_least_one_pack_exposes_an_opposed_check_confrontation` — wiring guard that the parametrized tests aren't vacuous.

### Test Run Result (RED)

```
13 failed, 56 passed in 0.40s
```

All 13 failures are AC-driven assertion failures, not infrastructure errors:

- **Band geometry (3 failures):** `test_shift_at_plus_2_is_success_not_tie`, `test_shift_at_minus_2_is_fail_not_tie`, plus 2 of the 6 parametrized rows in `test_calibrated_band_geometry` that sit on the ±2 boundary.
- **Distribution (1 failure):** `test_calibrated_distribution_meets_adr_093_targets` — current Tie rate ~23% vs expected 14.25% (band hasn't been narrowed).
- **YAML (9 failures):** 4 `opponent_default_stats` failures (one per pack with the field), 4 `opposed_check_thresholds_calibrated_to_7` failures (caverns/elem/mutant/space). space_opera's failure includes both `combat` AND `ship_combat` confrontations, validating the resolution-mode-based filter.

### Rule Coverage

- **CLAUDE.md no-silent-fallback** — `test_modifier_hard_fails_when_neither_source_has_stat` already covers this in the existing test suite; left intact.
- **OTEL spans unchanged** — AC-7 says no telemetry schema change. Existing wiring tests (`test_opposed_check_wiring.py`) validate span attributes; those pass and aren't touched.
- **Wiring tests** — `test_at_least_one_pack_exposes_an_opposed_check_confrontation` catches the case where the parametrized YAML tests would silently become vacuous if all opposed_check entries were removed.

### Chore Bypass

Not applicable — this is a calibration story with a load-bearing math test. Tests written.

**Handoff:** To Dev (Inigo Montoya, green phase).

## Dev Assessment

**Implementation Complete:** Yes — 82 calibration-surface tests pass.
**Branches:** feat/45-41-confrontation-calibration-v1 pushed to both server and content origin.

**Files Changed:**

*sidequest-server*:
- `sidequest/game/opposed_check.py` — `_SUCCESS_SHIFT` 3→2, `_FAIL_SHIFT` -3→-2; module + function docstrings updated for the calibrated bands. CritSuccess/CritFail thresholds unchanged at ±10.
- `tests/server/test_encounter_lifecycle.py` — fixture-loaded threshold assertion updated 10→7 to match calibrated cac pack data.
- `tests/game/test_opposed_check_distribution.py`, `tests/genre/test_confrontation_calibration.py` — minor lint fixes from ruff `--fix` (import sort, branch combine).

*sidequest-content* (genre packs):
- `caverns_and_claudes/rules.yaml` — combat: opponent stats 12→10, thresholds 10→7
- `elemental_harmony/rules.yaml` — combat: opponent stats 12→10, thresholds 10→7
- `mutant_wasteland/rules.yaml` — combat: opponent stats 12→10, thresholds 10→7
- `space_opera/rules.yaml` — ship_combat AND combat (firefight): opponent stats 12→10, thresholds 10→7. dogfight (sealed_letter_lookup, threshold 30) untouched.

**Tests:**

Calibration surface — `tests/game/test_opposed_check.py`, `tests/game/test_opposed_check_distribution.py`, `tests/genre/test_confrontation_calibration.py`, `tests/server/test_encounter_lifecycle.py`: **82 passed, 0 failed.**

Full server suite: 3856 passed, 36 failed, 57 skipped. The 36 failures are **pre-existing on main** (verified by stashing my changes, checking out `origin/main`'s `opposed_check.py`, and reproducing the same failure set across `test_dice_throw_*`, `test_chargen_dispatch`, `test_culture_context`, `test_pack_load`, `test_resolution_mode`, etc.). None are calibration-driven.

Lint: `uv run ruff check` on all my changed files passes clean. The 17 ruff errors elsewhere in the tree (orbital, course, narration_apply, session) pre-exist on main.

**Acceptance Criteria status:**

1. ✅ All `opponent_default_stats` 12→10 across the 4 packs (caverns, elem, mutant, space).
2. ✅ Tie band ±2→±1 in `opposed_check.py`. Boundary tests at ±1 pass.
3. ✅ All opposed_check confrontations at threshold 7. Includes space_opera's `ship_combat` (deviation logged).
4. ✅ Monte-Carlo distribution test passes within ±5pp of analytical expected values (asserted against the corrected math 47.5/14.25/38.25, not the ADR's quoted 45/33/22 — deviation logged).
5. ✅ Existing opposed_check unit tests pass; updated `test_instantiate_combat_creates_encounter` threshold assertion documented in deviation log.
6. ⚠️ `just check-all` partial — 36 pre-existing test failures and 17 pre-existing lint errors on `main`. Calibration surface itself is clean. Treating this AC as not-blocked-by-this-story since the failures are inherited from `main`. Recorded as Question in Delivery Findings.
7. ✅ OTEL span surface unchanged. `tests/server/test_opposed_check_wiring.py` (8 passed) confirms the existing spans still emit per the same attribute schema.

**Handoff:** To Reviewer (Westley, review phase).

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — both deviations resolved by amending the spec (ADR-093). Implementation aligns with the amended ADR.
**Mismatches Found:** 3 (all caught and logged in flight by TEA + Dev — no surprises)

**Mismatch 1 — Distribution percentages** (Different behavior — Behavioral, Minor)
- Spec said: "~45% Success-or-better, ~33% Tie, ~22% Fail-or-worse"
- Code does: 47.50% / 14.25% / 38.25% (analytical, exact, computed by enumerating 400 d20×d20 pairs); test asserts within ±5pp of those values
- Recommendation: **A — Update spec.** Rationale: TEA's analytical math is correct; my back-of-envelope estimate was wrong. The calibration's qualitative intent (player edge real, ties drop, decisive scenes) is unchanged; only the specific percentages move. ADR-093 amended (Expected behavior shift table replaced with the analytical numbers + a 2026-05-04 amendment note).

**Mismatch 2 — `ship_combat` classification** (Different behavior — Behavioral, Major)
- Spec said: "`dogfight` / `ship_combat` (sealed_letter mode) at 30, no change"
- Code does: `ship_combat` calibrated to threshold 7 (mode is `opposed_check`); only `dogfight` (mode is `sealed_letter_lookup`) stays at 30
- Recommendation: **A — Update spec.** Rationale: The implementation's data model is correct — `ship_combat` IS `opposed_check` and shares the calibrated tie-band geometry. Treating it as a sealed-letter exception would either leave it grindy at threshold 10 or raise it to 30 (the opposite of "untouched"). Filtering by `resolution_mode` is the consistent invariant. ADR-093 amended (calibration set table now keys off resolution mode; Implementation Pointer updated to match).

**Mismatch 3 — AC-6 (`just check-all`)** (Missing in code — Behavioral, Minor)
- Spec said: "`just check-all` passes"
- Code does: 36 server tests fail and 17 ruff lint errors remain in unrelated modules (orbital, course, narration, session, dice_throw, chargen, culture, pack_load) — pre-existing on `origin/main`
- Recommendation: **D — Defer.** Rationale: Verified by branch-stash + revert cycle — the failures and lint debt exist on `main` independently of 45-41. AC-6 is unsatisfiable in this story without an exponential cleanup pass. Calibration-surface tests (82) and lint are clean. Recommend filing a separate cleanup story; do not block 45-41 review.

**Decision:** Proceed to review. ADR-093 amended (status flipped from `deferred` to `live`, indexes regenerated). Implementation aligns with the amended spec. Reviewer should accept on calibration-surface evidence; do not gate on full-suite green.

## Tea Assessment (verify)

**Verify Phase Complete:** Yes — calibration surface tests still GREEN (82 passed) after the spec-check amendments and across simplify dispatch.
**Branch:** feat/45-41-confrontation-calibration-v1 (no further pushes from verify).
**Files re-tested:** `tests/game/test_opposed_check.py`, `tests/game/test_opposed_check_distribution.py`, `tests/genre/test_confrontation_calibration.py`, `tests/server/test_encounter_lifecycle.py`.

### Simplify Fan-out Results

Three simplify subagents dispatched in parallel against the 5 changed code files (`sidequest/game/opposed_check.py` plus 4 test files). Results:

| Agent | Status | Findings |
|-------|--------|----------|
| simplify-reuse | findings | 3 HIGH (cross-file fixture duplication) + 1 HIGH (unify `_make_cdef`/`_calibrated_cdef`) |
| simplify-quality | clean | 0 findings — naming, error handling, type safety, dead code, conventions all check out |
| simplify-efficiency | findings | 1 HIGH (case-insensitive stat lookup dup), 1 MEDIUM (unused `encounter` param), 1 LOW (test pattern repetition) |

### Triage and Decisions

**Applied (none).** No mechanical changes made during verify — all actionable findings either touch pre-existing code outside this story's scope, or the agents themselves flagged the change as low-confidence / "could go either way."

**Deferred — logged as Improvement findings for a follow-up cleanup story:**

1. **Cross-file fixture duplication** (simplify-reuse, 3 HIGH). `_make_cdef`/`_attack_beat`/`_make_resolver_actors` exist in both `test_opposed_check.py` (pre-existing, prior story) and `test_opposed_check_distribution.py` (added by 45-41). Cleanest fix is a shared `tests/game/conftest.py` or helper module, which would touch the pre-existing test file. Out of scope per boy-scout-bounded principle; the duplication is mild (~30 lines total) and the test files remain self-readable.

2. **Case-insensitive stat lookup duplication in `opposed_check.py`** (simplify-efficiency, HIGH). `_stat_score_from_actor` and `_stat_score_from_cdef_default` both inline the same fallback loop. This code was NOT touched by 45-41; calibration only flipped two constants and edited docstrings. Logging for cleanup but deferring.

3. **Unused `encounter` parameter on `resolve_opposed_check`** (simplify-efficiency, MEDIUM). Pre-existing future-proofing stub flagged by the agent against the CLAUDE.md no-stubbing rule. Out of scope for calibration; if it lands in a cleanup story, the architect should weigh "future contextual logic" intent against the no-stubbing rule.

4. **Test pattern repetition in `test_confrontation_calibration.py`** (simplify-efficiency, LOW). Four tests share a parse → loop → collect → assert structure. Agent self-rated as "could go either way"; the explicit form is more readable than a parametrized helper would be. Not deferring — declining as a non-finding.

### Rule Coverage Check

- **CLAUDE.md "Every test suite needs a wiring test":** ✓ `test_at_least_one_pack_exposes_an_opposed_check_confrontation` wires the parametrized YAML tests to actual data.
- **CLAUDE.md "OTEL observability":** ✓ AC-7 explicitly preserves the existing span surface; no telemetry changes. Existing `test_opposed_check_wiring.py` (8 passed) confirms wiring intact.
- **CLAUDE.md "No silent fallbacks":** ✓ `resolve_opponent_modifier` raises `ValueError` (existing behavior, untouched).
- **TEA test-paranoia (vacuous assertions):** ✓ Self-checked all new tests. Distribution test asserts on actual counted percentages with named bounds; band-geometry tests assert specific tier outcomes; YAML tests assert on parsed values with offending-list output for diagnosability. No `let _ =`, no `assert!(true)`, no `is_none()` on always-None.

### Conclusion

**Verify gate passes.** Calibration surface is GREEN, simplify findings triaged and either applied (none required), deferred (3 cleanup-story candidates), or declined (1 non-finding). Code is ready for Reviewer.

**Handoff:** To Reviewer (Westley, review phase).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (1 informational note re: ship_combat reconciliation, already resolved in spec-check) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.edge_hunter: false`) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.silent_failure_hunter: false`) |
| 4 | reviewer-test-analyzer | Yes | findings | 4 (1 HIGH, 2 MEDIUM, 1 LOW) | confirmed 3, dismissed 1, deferred 0 |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 (2 HIGH, 1 MEDIUM, 1 LOW) | confirmed 3, dismissed 1, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.type_design: false`) |
| 7 | reviewer-security | No | Skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.security: false`) |
| 8 | reviewer-simplifier | No | Skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.simplifier: false`) |
| 9 | reviewer-rule-checker | Yes | findings | 2 (both LOW) | confirmed 0, dismissed 2, deferred 0 |

**All received:** Yes (4 enabled subagents returned, 5 disabled via settings)
**Total findings:** 6 confirmed and fixed, 4 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Branch state:** feat/45-41-confrontation-calibration-v1 pushed on both server and content repos. Server HEAD `5cfac4d`, content HEAD `157c45b`. ADR-093 amendment committed to orchestrator main (`a37574a`).
**Test surface:** 87 calibration-surface tests pass (up from 82 after applying review fixes).
**Verdict:** **Approve.** All HIGH-severity findings resolved in-branch. Calibration surface is clean.

### Confirmed Findings — Fixed In-Branch

**[TEST] HIGH — Monte-Carlo distribution test could pass with one calibration lever broken** (`tests/game/test_opposed_check_distribution.py:119`). The agent verified analytically that the ±5pp tolerance on Success-or-better cannot distinguish "narrow band + calibrated stats" (47.50%) from "narrow band + parity stats at 12" (42.75%). The `_player_edge_is_real` test catches the parity case via its 5pp edge floor, but the load-bearing AC's docstring claimed it alone proves the calibration; that claim was false. **Fix applied:** added a pre-loop sentinel `resolve_opposed_check` call asserting `player_mod == 1` and `opponent_mod == 0`. Zero-cost wiring guard; the load-bearing AC now refuses to pass when either lever has not fired.

**[TEST] MEDIUM — Wiring guard exited on first match, masking accidental loss of combat confrontations** (`tests/genre/test_confrontation_calibration.py:191`). The original `test_at_least_one_pack_exposes_an_opposed_check_confrontation` broke the loop after finding the first opposed_check entry, so a pack that lost its opposed_check confrontation would still be guarded by another pack. **Fix applied:** replaced with a parametrized `test_combat_pack_exposes_at_least_one_opposed_check_confrontation` over a new `COMBAT_PACKS` list (4 packs, excludes victoria which is social-only by design). Per-pack assertion catches the regression.

**[TEST] MEDIUM — Asymmetric band coverage in the parametrized geometry test** (`tests/game/test_opposed_check_distribution.py:282`). The original 6-row parametrize covered Tie / Success / Fail / CritSuccess but not CritFail; a regression that widened the CritFail boundary would not be caught by this fixture. **Fix applied:** added two rows covering shift -9 → Fail and shift -10 → CritFail through the full resolver stack.

**[DOC] HIGH — `space_opera/rules.yaml` ship_combat comment fabricated an ADR/reality disagreement** (`genre_packs/space_opera/rules.yaml:206`). The inline comment described an ADR misclassification that was already resolved by the spec-check phase amendment; a fresh reader of ADR-093 today finds no such discrepancy. **Fix applied:** rewrote as a concise factual note.

**[DOC] HIGH — `test_confrontation_calibration.py` module docstring overstated victoria's role** (file head). ADR-093 names four packs as calibration targets, not five; victoria is referenced only as a baseline. **Fix applied:** rewrote the docstring to explain victoria's inclusion as a forward-compatibility guard (it has no opposed_check confrontations today, but the parametrize ensures any future addition gets caught) and contrasted it against the stricter `COMBAT_PACKS` list.

**[DOC] MEDIUM — `test_opposed_check.py` Spec citation pointed at a pre-calibration archive doc** (file head). The "Spec: .archive/handoffs/opposed-checks-design.md" reference would lead a fresh reader to a doc with superseded ±2/±3 band values. **Fix applied:** updated the citation to ADR-093 with an explicit "superseded" note for the archive doc.

### Dismissed Findings

**[TEST] LOW — `_make_cdef` in `test_opposed_check.py:122` uses pre-calibration threshold=10**. The helper is in code that pre-existed this story and was not touched by 45-41; the tests using it do not assert on threshold so the value has no observable effect. Logged as Improvement finding for the cleanup story alongside the simplify-reuse fixture-duplication finding.

**[DOC] LOW — `# Shift band boundaries (spec table — locked thresholds)` shorthand**. Cosmetic; the body of the section correctly cites ADR-093 via the updated module docstring above it.

**[RULE] LOW — `test_calibrated_band_geometry` parametrize rows 1/3/4 hit the same return branch in `_tier_from_shift`**. The rows probe distinct boundary positions for documentation, not for branch coverage. The agent itself flagged it as a judgment call.

**[RULE] LOW — No production-wiring test in `test_opposed_check_distribution.py`**. Covered by the pre-existing `test_opposed_check_wiring.py` (8 passed in green phase). Duplicating in the new file would add no signal.

### Rule Compliance Summary

The rule-checker evaluated 21 rules across 47 instances; 0 violations on rules 1, 2, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 21. Two LOW-severity issues on rules 6 and 18 (both dismissed above with rationale). Rule 3 (type annotations) had two private-helper exemptions correctly recognized. Calibration surface complies with every rule in `.pennyfarthing/gates/lang-review/python.md` plus every CLAUDE.md/SOUL.md rule extracted as ADDITIONAL_RULES.

### Note on Preflight Commit Listing

`reviewer-preflight` listed extra commits (`feat(45-41): loud-fail when OTLP exporter is dormant`, `Merge pull request #189`) in `commits_on_branch`. These do not appear in the diff against `origin/main` and are likely a preflight artifact from comparing against `origin/develop` (server repo's base is `main` per `repos.yaml`, not `develop`). Actual branch delta against `origin/main` is the 45-41 calibration commits plus the three review-fix commits added in this phase. Calibration scope is unaffected.

### Decision

**Verdict: APPROVED.** Branches ready for merge. SM should open PRs, merge, and finish.

**Summary of what was reviewed:**
- ADR-093 confrontation calibration v1 across two repos: sidequest-server (band constants + 3 test files + 1 integration-test fix) and sidequest-content (4 genre-pack rules.yaml files).
- Diff scope: 5 server files, 4 content files; ~580 net lines added (mostly test code).
- 4 specialist subagents dispatched (5 disabled via project settings): preflight, test-analyzer, comment-analyzer, rule-checker. All received and assessed.
- 6 confirmed findings fixed in-branch (87 calibration-surface tests pass, up from 82).
- 4 dismissed findings (all LOW), 0 deferred (all confirmed findings actioned, not pushed to follow-up).
- 21 project rules evaluated by rule-checker across 47 instances; 0 violations on 18 rules, 2 LOW issues on rules 6 & 18 (dismissed with rationale tied to existing coverage).

### Rule Compliance

| Rule | Source | Status | Notes |
|---|---|---|---|
| 1 — Silent exception swallowing | python.md #1 | ✓ Compliant | All error paths raise loud ValueError; no swallowing |
| 2 — Mutable default arguments | python.md #2 | ✓ Compliant | All defaults are immutable (None, str) |
| 3 — Type annotation gaps at boundaries | python.md #3 | ✓ Compliant | Public boundaries fully annotated; private helper exemptions valid |
| 4 — Logging coverage | python.md #4 | ✓ Compliant | Pure-computation modules; ValueError raises serve the diagnostic role |
| 5 — Path handling | python.md #5 | ✓ Compliant | pathlib.Path with `/` operator; encoding='utf-8' on all opens |
| 6 — Test quality | python.md #6 | ⚠ LOW (dismissed) | Tie-band parametrize rows probe distinct boundaries; intentional documentation |
| 7 — Resource leaks | python.md #7 | ✓ Compliant | All file opens use `with` context managers |
| 8 — Unsafe deserialization | python.md #8 | ✓ Compliant | yaml.safe_load throughout |
| 9 — Async/await pitfalls | python.md #9 | N/A | No async code in diff |
| 10 — Import hygiene | python.md #10 | ✓ Compliant | Explicit imports, no star imports, no cycles |
| 11 — Input validation at boundaries | python.md #11 | ✓ Compliant | resolve_opposed_check validates roll range; raises ValueError on out-of-range |
| 12 — Dependency hygiene | python.md #12 | N/A | No dependency manifest changes |
| 13 — Fix-introduced regressions | python.md #13 | ✓ Compliant | Constant changes only; no new exception handling or validation introduced |
| 14 — No silent fallbacks | CLAUDE.md | ✓ Compliant | Already-loud failure paths preserved |
| 15 — No stubbing | CLAUDE.md | ✓ Compliant | All new functions fully implemented |
| 16 — Reuse over reimplementation | CLAUDE.md | ✓ Compliant | New tests use existing model classes and resolver |
| 17 — Verify wiring, not existence | CLAUDE.md | ✓ Compliant | New tests exercise production model_validate paths and real GenreLoader |
| 18 — Every test suite needs a wiring test | CLAUDE.md | ⚠ LOW (dismissed) | New per-pack wiring assertion added; production-dispatch wiring covered by sibling test_opposed_check_wiring.py |
| 19 — OTEL span surface unchanged | AC-7 | ✓ Compliant | No telemetry files in diff; existing wiring test (8 passed) confirms |
| 20 — Test-paranoia: no vacuous assertions | TEA stance | ✓ Compliant | Every test asserts a specific value or invariant; sentinel guard added during review |
| 21 — Spec authority: deviations logged | CLAUDE.md | ✓ Compliant | 2 deviations logged in flight; ADR-093 amended via Option A in spec-check |

**Handoff:** To SM (Vizzini, finish phase).

**ADR Changes:**
- `docs/adr/093-confrontation-difficulty-calibration.md`:
  - Frontmatter: `implementation-status: deferred` → `live`
  - Calibration set table: `ship_combat` row corrected; tie-band rationale updated (24%→14%, not 50%→33%)
  - "Expected behavior shift" section: replaced rough estimates with analytical distribution table
  - Implementation Pointer: Step 1 now keys off `resolution_mode: opposed_check` rather than type names; ±5% changed to ±5pp; "Implementation status" closing note added
- Regenerated `docs/adr/README.md`, `DRIFT.md`, `CLAUDE.md` ADR index block

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Conflict** (non-blocking): ADR-093's claimed expected distribution (45% Success-or-better, 33% Tie, 22% Fail-or-worse) does not match the analytical expected distribution under the calibrated parameters. Enumerating all 400 d20×d20 pairs with player +1 / opponent +0 / tie band ±1 yields 47.50% / 14.25% / 38.25%. Affects `docs/adr/093-confrontation-difficulty-calibration.md` lines 85–97 (the "Expected behavior shift" table). The calibration intent (player edge becomes real, ties drop sharply) is preserved — only the specific percentages need updating. *Found by TEA during distribution test design.*

- **Conflict** (non-blocking): ADR-093's Implementation Pointer treats space_opera's `ship_combat` as a sealed-letter mode confrontation that should stay at threshold 30. In reality `ship_combat` uses `resolution_mode: opposed_check` (only `dogfight` is sealed_letter_lookup). Because ship_combat shares the calibrated tie-band geometry, it must be calibrated to threshold 7 alongside the other opposed_check confrontations. Affects `docs/adr/093-confrontation-difficulty-calibration.md` Implementation Pointer (calibration set table) and `sidequest-content/genre_packs/space_opera/rules.yaml`. *Found by TEA during YAML survey.*

- **Question** (non-blocking): Three packs (elemental_harmony, mutant_wasteland, space_opera) have `negotiation` confrontations at threshold 10 instead of 7. ADR-093 explicitly says "negotiation: 7 (already correct)" but only victoria and caverns_and_claudes match that statement. v1 leaves these alone per ADR scope. Affects negotiation pacing across those three packs — flagged for v2 consideration. *Found by TEA during YAML survey.*

### Dev (implementation)

- **Question** (non-blocking): `main` has 36 pre-existing server test failures and 17 pre-existing ruff lint errors that are unrelated to this story — `test_dice_throw_*`, `test_chargen_dispatch`, `test_culture_context`, `test_pack_load`, `test_resolution_mode`, `test_visual_style_lora_removal_wiring`, `test_audit_namegen_corpora`, plus orbital/course lint debt. Verified by stashing branch changes and reproducing on `origin/main`. AC-6 (`just check-all` passes) cannot be satisfied without addressing these unrelated regressions. Recommend separate cleanup story; do not block 45-41 review. Affects `sidequest/orbital/course.py`, `sidequest/server/narration_apply.py`, `sidequest/server/session.py`, `tests/agents/test_narrator_courses_block.py`, `tests/handlers/test_course_intent_wired.py`, `tests/orbital/test_course_compute.py`, and the failing test files listed above. *Found by Dev during just check-all run.*

- **No upstream findings** beyond the question above — calibration surface is clean.

### TEA (verify)

- **Improvement** (non-blocking): Cross-file fixture duplication. `_make_cdef`, `_attack_beat`, and `_make_resolver_actors` exist with near-identical bodies in both `tests/game/test_opposed_check.py` (pre-existing, prior story) and `tests/game/test_opposed_check_distribution.py` (added by 45-41). Cleanest fix is to extract to a shared helper module (e.g. `tests/game/_fixtures.py`) or `tests/game/conftest.py` and have both test files import from it. Affects 2 test files plus a new shared module (~30 lines net touch). Out of scope for calibration; deferring to a follow-up cleanup story. *Found by TEA simplify-reuse during verify.*

- **Improvement** (non-blocking): Case-insensitive stat lookup duplication in `sidequest/game/opposed_check.py`. `_stat_score_from_actor` (lines 123-128) and `_stat_score_from_cdef_default` (lines 143-146) both inline the same case-insensitive dict-walk. Pre-existing code, not touched by 45-41. Extract to a shared `_find_stat_case_insensitive(stats_dict, stat_name)` helper. Affects `sidequest/game/opposed_check.py` only. *Found by TEA simplify-efficiency during verify.*

- **Question** (non-blocking): Unused `encounter` parameter on `resolve_opposed_check` in `sidequest/game/opposed_check.py:201`. Documented as "currently unused; carried in the signature so the resolver can grow contextual logic." Per the CLAUDE.md "no stubbing" rule, future-proofing parameters that are not yet wired should be removed. However, the comment signals deliberate intent. Architect should decide whether to keep or remove during a cleanup story. Affects `sidequest/game/opposed_check.py` plus all call sites in dispatch + tests. *Found by TEA simplify-efficiency during verify.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Distribution-test bounds use analytical expected, not ADR-093 quoted percentages**
  - Spec source: `docs/adr/093-confrontation-difficulty-calibration.md` lines 85–97 (Expected behavior shift) AND `sprint/context/context-story-45-41.md` AC-4
  - Spec text: "asserts tier distribution within ±5pp of: 45% Success-or-better, 33% Tie, 22% Fail-or-worse"
  - Implementation: `test_calibrated_distribution_meets_adr_093_targets` asserts within ±5pp of 47.50% Success-or-better, 14.25% Tie, 38.25% Fail-or-worse — the values produced by enumerating all 400 d20×d20 outcomes under the calibrated parameters.
  - Rationale: The ADR's quoted percentages are mathematically inconsistent with the prescribed parameters. Under player +1 / opponent +0 / tie band ±1, p(Tie) = 57/400 = 14.25%, not 33%. Asserting against the wrong number would either (a) flake on noise (if tolerance widened) or (b) be unreachable (if tolerance kept tight). Asserting against the actual analytical expected value preserves the AC's intent (verify the calibration delivers the documented distribution shape) without baking the math error into the test suite.
  - Severity: minor
  - Forward impact: minor — Architect (The Man in Black) should amend ADR-093's Expected behavior shift table to the corrected percentages. Recorded as Conflict in Delivery Findings.

- **Threshold-calibration test filters by resolution_mode, not by type name**
  - Spec source: `sprint/context/context-story-45-41.md` AC-3 AND `docs/adr/093-confrontation-difficulty-calibration.md` Implementation Pointer (calibration set table)
  - Spec text: "Combat and chase confrontations across all genre packs have player_metric.threshold and opponent_metric.threshold lowered from 10 to 7. Negotiation remains at 7; dogfight/ship_combat at 30."
  - Implementation: `test_opposed_check_thresholds_calibrated_to_7` filters confrontations by `resolution_mode == "opposed_check"`, not by `type in {"combat", "chase"}`. This is broader on one axis (catches space_opera's `ship_combat` whose mode is `opposed_check`) and narrower on another (chase confrontations use the default `beat_selection` mode and are skipped — they are already at threshold 7 across all packs and are exercised by the redundant negotiation/sealed-letter guards).
  - Rationale: ADR-093 states "ship_combat at 30" but the actual data has ship_combat at threshold 10 with `resolution_mode: opposed_check`. Treating ship_combat as a sealed-letter exception would either leave it grindy at threshold 10 or RAISE it to 30 (the opposite of "untouched"). The consistent interpretation is that `resolution_mode == "opposed_check"` is the calibration filter — it captures every confrontation that shares the calibrated tie-band geometry. Per Spec Authority Hierarchy, the AC text outranks the ADR; this deviation reconciles the AC's intent ("calibrate combat-style confrontations") with the actual YAML data shape.
  - Severity: minor
  - Forward impact: minor — Dev must include space_opera's ship_combat in the threshold-7 sweep. Recorded as Conflict in Delivery Findings; ADR-093 needs a one-line amendment to the calibration set table.

### Dev (implementation)

- **Updated `test_instantiate_combat_creates_encounter` threshold assertion 10 → 7**
  - Spec source: `sprint/context/context-story-45-41.md` AC-5 (existing tests pass; any test hardcoding the old values updated and logged)
  - Spec text: "Existing opposed_check unit tests pass; any test that hardcoded shift = ±2 → Tie updated with change documented in deviation log."
  - Implementation: `tests/server/test_encounter_lifecycle.py:39` changed `assert enc.player_metric.threshold == 10` to `assert enc.player_metric.threshold == 7`. The test loads `cac_pack` from disk; threshold value flows from the calibrated YAML, so the assertion must track the calibration.
  - Rationale: The test was reading the live pack data, not constructing a synthetic fixture. Calibrating the YAML without updating this assertion would have broken an otherwise-correct integration test. AC-5 explicitly anticipates this kind of update.
  - Severity: trivial
  - Forward impact: none — this test was the only assertion in the suite that pinned the cac_pack threshold to a specific value.

- **AC-6 (`just check-all` passes) treated as non-blocked-by-this-story**
  - Spec source: `sprint/context/context-story-45-41.md` AC-6
  - Spec text: "`just check-all` passes (server-check + client-lint + client-test + daemon-lint)."
  - Implementation: `just check-all` does not pass on the calibrated branch — but it also does not pass on `origin/main`. 36 server test failures and 17 ruff lint errors pre-exist; verified by stashing branch changes and reproducing the failure set on `origin/main`. Calibration-surface tests pass; calibration-surface lint is clean.
  - Rationale: Satisfying AC-6 in this story would require fixing 36 unrelated server tests and 17 unrelated lint errors. That is exponential boy-scouting (per memory `feedback_boy_scout_bounded`). Recommended path: hand off to review with the calibration delta clean, file the cleanup as a separate story.
  - Severity: minor
  - Forward impact: minor — Reviewer should accept this story on calibration-surface evidence; do not gate on full-suite green. Recorded as Question in Delivery Findings.

### Architect (reconcile)

**Verification of in-flight deviation entries:**

All four in-flight entries (TEA: 2, Dev: 2) verified accurate.

- TEA-1 (distribution percentages): spec source `docs/adr/093-confrontation-difficulty-calibration.md` lines 85–97 and `context-story-45-41.md` AC-4 (line 38) confirmed; quoted text matches AC-4 verbatim. Implementation values 47.50 / 14.25 / 38.25 confirmed in `tests/game/test_opposed_check_distribution.py:101–102` (constants `EXPECTED_TIE_PCT = 14.25`, `EXPECTED_FAIL_OR_WORSE_PCT = 38.25`) and in the module docstring. ADR-093 amended via Option A in spec-check (orchestrator commit `a37574a`) with a 2026-05-04 amendment note explicitly flagging the percentage correction.
- TEA-2 (resolution_mode filter): spec source AC-3 (context-story-45-41.md line 37) confirmed; quoted text matches. Implementation filters by `resolution_mode == "opposed_check"` confirmed in `tests/genre/test_confrontation_calibration.py:130` and module docstring lines 4–8. `space_opera/rules.yaml:218,222` shows `ship_combat` thresholds at 7 with `resolution_mode: opposed_check` declared at line 209. ADR-093 calibration set table amended (commit `a37574a`) so the filter is now spec-aligned.
- Dev-1 (encounter_lifecycle threshold): spec source AC-5 confirmed; quoted text matches. `tests/server/test_encounter_lifecycle.py:40` asserts `enc.player_metric.threshold == 7` with an inline ADR-093 citation comment. Trivial deviation justified by AC-5's anticipatory clause.
- Dev-2 (AC-6 treated as non-blocked): spec source AC-6 confirmed; quoted text matches. The pre-existing-failure scoping is corroborated by Dev's branch-stash verification recorded under "Delivery Findings → Dev (implementation)" and was accepted by Reviewer in the merge-ready disposition.

**Missed deviations:**

- **Story-context Implementation Pointer enumerated 5 content files; implementation edited 4**
  - Spec source: `sprint/context/context-story-45-41.md` Implementation Pointer / "Files to Edit" (line 24)
  - Spec text: "`genre_packs/victoria/rules.yaml` — same pattern (victoria negotiation already at 7; dogfight/ship_combat at 30 unchanged)"
  - Implementation: `victoria/rules.yaml` was not modified. The pack has no `opponent_default_stats` entries (vacuously satisfies AC-1) and no `resolution_mode: opposed_check` confrontations (vacuously satisfies AC-3). It is included in the parametrized YAML calibration tests as a forward-compatibility guard and explicitly excluded from the per-pack opposed_check wiring guard (`COMBAT_PACKS` in `tests/genre/test_confrontation_calibration.py:51–57`) because victoria is social-only by design.
  - Rationale: The Implementation Pointer's "5 files" prediction overstated the actual edit set. Editing victoria would have been a no-op (no fields to change). The implementation correctly recognized this and documented the exclusion in the test docstring rather than silently dropping victoria from the test sweep. Per Spec Authority Hierarchy, AC-1/AC-3 (story scope) outrank the Implementation Pointer's file enumeration; the AC text is satisfied vacuously for victoria.
  - Severity: minor
  - Forward impact: none — victoria's continued participation in the test parametrize ensures any future addition of opposed_check confrontations to the pack will be caught by the calibration guard. No downstream story makes a load-bearing assumption about victoria having been edited in 45-41.

**AC accountability cross-check:**

The session does not contain a separate ac-completion accountability table; AC status is inlined in the Dev Assessment (lines 110–117). Cross-referenced against Reviewer findings:

- AC-1, AC-2, AC-3, AC-4, AC-5, AC-7 — all marked DONE by Dev; Reviewer's Rule Compliance table (rules 14–21) and 87 calibration-surface tests passing corroborate full satisfaction. No status changes during review.
- AC-6 — soft-deferred by Dev with rationale; Reviewer accepted on calibration-surface evidence. Status unchanged through review. The deferral is captured in Dev's deviation entry (severity minor, forward impact minor).

No deferred AC was inadvertently addressed or invalidated during review.

**Spec authority outcomes:**

- ADR-093 (architecture-doc tier) was amended via Option A to reconcile with TEA-1 and TEA-2 deviations — spec moved to match the implementation rather than vice versa, because the implementation was mathematically correct (TEA-1) or schema-correct (TEA-2). ADR frontmatter `implementation-status` flipped `deferred` → `live`. Indexes regenerated.
- Story context (story-tier) was not amended; the deviations are minor and self-contained.

**Spec Alignment:** Aligned. All deviations resolved or documented. Implementation matches the amended ADR-093 and the story context's ACs.