---
story_id: 63-5
jira_key: null
epic: 63
workflow: tdd
---
# Story 63-5: Cleanup: live-pack validator, tropes exclusion, R2 screenshots, final gate

## Story Details
- **ID:** 63-5
- **Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
- **Jira Key:** none (project does not use Jira)
- **Workflow:** tdd (phased: red → green → spec-check → verify → review → spec-reconcile → finish)
- **Stack Parent:** 63-4 (depends_on)

## Story Context

This story handles Tasks 23–25 from the v3 plan (`docs/superpowers/plans/2026-05-23-reference-pages-v3.md`), the final cleanup and validation gates before the epic merges:

- **Task 23:** Live-pack validator (`python -m sidequest.cli.validate reference-chrome`) — walks `theme.yaml` in each pack for required chrome fields (archetype, palette, web_font_family, display_font_family, dinkus glyphs), reports loudly on missing fields
- **Task 24:** Explicit exclusion of `tropes.yaml` + `seed_tropes.yaml` from rendered reference pages (they are GM-side only per the design bundle)
- **Task 25:** Stage design-bundle screenshots (1.3 MB of PNGs) from `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/` to R2 at `cdn.slabgorb.com/design-bundles/2026-05-23-lore-and-rules/screenshots/`; replace local dir with pointer README

Context: 63-4 shipped chrome rendering with per-pack theme injection, static CSS, hero, and contents rail. 63-7 (done 2026-05-24) fixed markup vocabulary drift in 63-4. This story wraps up final validation and asset staging.

## Acceptance Criteria (from Plan Tasks 23–25)

**Task 23 (Validator):**
1. `sidequest-server/sidequest/cli/validate/reference_chrome.py` exists and implements a click command
2. Subcommand registered in `sidequest-server/sidequest/cli/validate/__main__.py`
3. Validator walks `theme.yaml`, asserts presence of: archetype, web_font_family, display_font_family, primary, accent, background, dinkus.glyph.{light,medium,heavy}
4. Missing field → non-zero exit + [FAIL] line on stderr + field name in message (loud, no silent fallback)
5. Tests: `sidequest-server/tests/cli/test_validate_reference_chrome.py` — fixture-driven only (never reads live `genre_packs/*`)
6. `just content-validate` recipe added to orchestrator justfile (walks all live packs via the validator)

**Task 24 (Tropes Exclusion):**
1. `sidequest-server/sidequest/server/reference_renderer.py` — modify exclusion list to include `tropes.yaml` and `seed_tropes.yaml` alongside `npcs.yaml`
2. Test: `sidequest-server/tests/server/test_reference_renderer.py` — add regression case that fixture pack with `tropes.yaml` does NOT render trope content
3. No tropes section heading or content in rendered pages

**Task 25 (R2 Screenshots):**
1. All PNG files from `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/` uploaded to R2 at `cdn.slabgorb.com/design-bundles/2026-05-23-lore-and-rules/screenshots/`
2. Local PNG files deleted
3. `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/README.md` created with pointer to R2 URL
4. Per project rule: images go to R2, not LFS

## Plan Reference

Plan location: `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` (lines 2857–3055)

Tasks breakdown:
- Task 23 (lines 2857–2965): live-pack validator
- Task 24 (lines 2968–3006): tropes exclusion
- Task 25 (lines 3009–3055): screenshot staging to R2

## Repos & Branch

- **Repos:** server (sidequest-server), content (sidequest-content)
- **Branch:** feat/63-5-cleanup-validator-tropes-r2-final-gate

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-25T11:41:21Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-25 | 2026-05-25T10:03:34Z | 10h 3m |
| red | 2026-05-25T10:03:34Z | 2026-05-25T10:14:58Z | 11m 24s |
| green | 2026-05-25T10:14:58Z | 2026-05-25T10:19:51Z | 4m 53s |
| spec-check | 2026-05-25T10:19:51Z | 2026-05-25T10:21:23Z | 1m 32s |
| verify | 2026-05-25T10:21:23Z | 2026-05-25T10:24:24Z | 3m 1s |
| review | 2026-05-25T10:24:24Z | 2026-05-25T11:05:06Z | 40m 42s |
| green | 2026-05-25T11:05:06Z | 2026-05-25T11:18:10Z | 13m 4s |
| spec-check | 2026-05-25T11:18:10Z | 2026-05-25T11:24:08Z | 5m 58s |
| verify | 2026-05-25T11:24:08Z | 2026-05-25T11:25:10Z | 1m 2s |
| review | 2026-05-25T11:25:10Z | 2026-05-25T11:37:48Z | 12m 38s |
| spec-reconcile | 2026-05-25T11:37:48Z | 2026-05-25T11:41:21Z | 3m 33s |
| finish | 2026-05-25T11:41:21Z | - | - |

## Sm Assessment

**Story 63-5** wraps up epic 63 (Reference pages v3) with three discrete tasks: a live-pack theme validator CLI, tropes exclusion from rendered reference pages, and R2 staging of design-bundle screenshots. All three are well-scoped from the v3 plan (Tasks 23–25). No blockers identified — 63-4 and 63-7 both shipped, so the foundation code is in place. Branch created in server and content repos on develop base.

**Routing:** TDD workflow → TEA (RED phase) writes failing tests for the validator, tropes exclusion, and screenshot presence assertions.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story has two implementation tasks (validator CLI + tropes exclusion) requiring TDD coverage

**Test Files:**
- `sidequest-server/tests/cli/test_validate_reference_chrome.py` — validator CLI tests (14 tests)
- `sidequest-server/tests/server/test_reference_renderer.py` — tropes exclusion tests (2 new + 1 updated)

**Tests Written:** 17 tests covering 9 ACs (AC-1 through AC-9; AC-10 is no-op)
**Status:** RED (failing — ready for Dev)

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| AC-1 (click command exists) | `TestPassingValidation::test_all_fields_present_exits_zero` | failing (import error) |
| AC-2 (registered in __main__) | `TestWiring::test_subcommand_registered_in_validate_group` | failing (import error) |
| AC-3 (validates all fields) | `TestMissingTopLevelFields::test_missing_field_exits_nonzero[*]` (6 params) + `TestMissingNestedDinkusFields::test_missing_dinkus_glyph_exits_nonzero[*]` (3 params) | failing (import error) |
| AC-4 ([FAIL] + field name) | All failing tests check `[FAIL]` and field name in output | failing (import error) |
| AC-5 (fixture-driven only) | All tests use `tmp_path` fixtures, zero live pack references | failing (import error) |
| AC-6 (just content-validate) | Not testable in pytest — manual verification of justfile recipe | n/a |
| AC-7 (tropes.yaml in EXCLUDED_FILES) | `test_tropes_yaml_excluded_from_rules_files` + `test_rules_files_in_documented_order` | failing |
| AC-8 (regression test) | `test_tropes_content_never_rendered_on_rules_page` | passing |
| AC-9 (no tropes in output) | Same as AC-8 | passing |
| AC-10 (R2 screenshots) | No-op — screenshots dir does not exist | skipped |

**Handoff:** To Major Winchester (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/cli/validate/reference_chrome.py` — new click command wrapping `load_reference_theme()`
- `sidequest-server/sidequest/cli/validate/__main__.py` — registered `reference-chrome` subcommand
- `sidequest-server/sidequest/server/reference_renderer.py` — moved `tropes.yaml` from `RULES_FILES` to `EXCLUDED_FILES`, removed dead `_KIND_OVERRIDES["tropes"]`
- `justfile` — added `reference-chrome-validate` recipe, wired into `content-validate`

**Tests:** 54/54 passing (GREEN)
**Branch:** feat/63-5-cleanup-validator-tropes-r2-final-gate (pushed)

**AC Status:**
- AC-1 through AC-6: DONE (validator CLI created, registered, tested, justfile recipe added)
- AC-7 through AC-9: DONE (tropes.yaml excluded from RULES_FILES, added to EXCLUDED_FILES)
- AC-10: DESCOPED — screenshots directory does not exist on this branch (no git history, no files)

**Handoff:** To spec-check phase

### Dev Assessment (rework — round 1)

**Reviewer finding addressed:** `[HIGH]` stale `test_kind_for_stem[tropes-trope]` in `tests/server/test_reference_renderer_namespacing.py:43`.

**Fix:** Removed the `("tropes", "trope")` entry from the `@pytest.mark.parametrize` list. The `_KIND_OVERRIDES["tropes"]` mapping was intentionally removed (dead code — tropes.yaml is now excluded from rendering), so `_kind_for_stem("tropes")` now correctly returns the identity `"tropes"`. The assertion was the only orphaned reference; verified by grepping the test tree (other `trope` matches are in the unrelated dungeon trope-engine tests).

**Full-suite verification:** 7944 passed, 17 failed, 375 skipped. All 17 failures are pre-existing on develop (Reviewer cross-branch-verified). `test_kind_for_stem[tropes-trope]` confirmed GONE. Zero branch-introduced failures.

**Branch:** feat/63-5-cleanup-validator-tropes-r2-final-gate (commit 242f78b, pushed)

**Handoff:** To spec-check phase (re-review)

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 9 active ACs (AC-1 through AC-9) align cleanly with the story context and plan Tasks 23–24. AC-10 (R2 screenshots) correctly descoped — the screenshots directory has no git history and does not exist on this branch or develop.

Implementation highlights:
- Validator CLI is a proper thin wrapper around the existing `load_reference_theme()` loader — single definition of "required fields" shared between validation and rendering (reuse-first, as it should be)
- Tropes exclusion is a 3-line diff moving `tropes.yaml` between tuples — minimal, precise
- Dead `_KIND_OVERRIDES["tropes"]` removed as bounded boy-scout (story context explicitly authorized this)
- Justfile recipe follows the existing `reference-validate-all` pattern exactly

**Decision:** Proceed to verify

### Architect Assessment (spec-check — round 2, post-rework)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Rework round 1 added a single deletion: the stale `("tropes", "trope")` parametrize entry in `test_reference_renderer_namespacing.py:43`. This is a test correction consequent to the authorized `_KIND_OVERRIDES["tropes"]` removal — no production behavior change. My round-1 alignment assessment stands: all 9 active ACs aligned, AC-10 descoped. The fix correctly brings the namespacing test in line with the (correct) production identity behavior for `tropes`.

**Decision:** Proceed to verify

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication — reference_chrome.py is a proper thin wrapper |
| simplify-quality | 1 finding | `raise SystemExit(1)` without `from None` (ruff B904) |
| simplify-efficiency | clean | No over-engineering detected |

**Applied:** 1 high-confidence fix (ruff B904: `raise SystemExit(1) from None`)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Quality-pass note:** simplify-quality also flagged `SystemExit` vs `ctx.exit()` inconsistency with sibling validators — dismissed because the plan explicitly specifies `raise SystemExit(1)` (plan line 2933) and adding `@click.pass_context` would increase complexity for zero behavioral difference.

**Quality Checks:** Lint clean (ruff), 54/54 tests passing
**Overall:** simplify: applied 1 fix

### TEA Assessment (verify — round 2, post-rework)

**Status:** GREEN confirmed
The only delta since round-1 verify is the one-line stale-test deletion in `test_reference_renderer_namespacing.py` (Reviewer finding). No production code changed — nothing new to simplify. Re-ran quality-pass: ruff clean on all 6 changed files, 68/68 tests passing across the three affected suites. Full-suite branch-introduced failure count is 0 (confirmed by Dev's rework full-suite run).
**Overall:** simplify: clean (no new code to analyze)
**Handoff:** To Colonel Potter (Reviewer) for re-review

**Handoff:** To Colonel Potter (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (round 2) | round-1 blocker resolved | confirmed 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes (round 1, carried) | findings | 3 | confirmed 0, dismissed 1, deferred 2 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (preflight re-run round 2 + security carried from round 1; 7 disabled via settings)
**Total findings:** round 1 — 1 blocking (now RESOLVED), 1 dismissed, 2 deferred; round 2 — 0 new

**Round-2 note:** reviewer-security was not re-dispatched because the rework diff (commit 242f78b) is a single-line deletion in a test file (`test_reference_renderer_namespacing.py`) — zero production/CLI code changed, so the round-1 security assessment is unchanged. reviewer-preflight WAS re-run on the full suite and confirms the round-1 blocker (`test_kind_for_stem[tropes-trope]`) is gone with no new regressions.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | `[PREFLIGHT]` Branch-introduced test failure: `test_kind_for_stem[tropes-trope]` asserts `_kind_for_stem("tropes") == "trope"`, but Dev removed `_KIND_OVERRIDES["tropes"]` (correctly — dead code). The sibling test was not updated. | `tests/server/test_reference_renderer_namespacing.py:43` | Remove the `("tropes", "trope")` entry from the `@pytest.mark.parametrize` list. The mapping no longer exists; `_kind_for_stem("tropes")` now correctly returns the identity `"tropes"`. |

### Root cause

Winchester's dead-code removal of `_KIND_OVERRIDES["tropes"]` was correct and authorized by story context. But the verify/green phases only ran the two *changed* test files (`test_validate_reference_chrome.py` + `test_reference_renderer.py`), not the full suite. The orphaned assertion lives in a *third* file (`test_reference_renderer_namespacing.py`) that nobody re-ran until preflight executed the full suite. This is exactly the failure mode the Reviewer's full-suite preflight exists to catch.

### Observations (independent review)

- `[VERIFIED]` No injection/path-traversal in validator — `pack_dir` gated by `click.Path(exists=True, file_okay=False)`, `pack_name` only flows to `click.echo`, no shell/eval — reference_chrome.py:18,22,26,28
- `[VERIFIED]` No silent fallback — `MissingThemeFieldError` caught specifically (not bare except), `[FAIL]` to stderr + exit 1 — reference_chrome.py:25-27
- `[VERIFIED]` Tropes exclusion + TOC interaction graceful — `confrontations` TOC id maps to `["tropes"]`; excluded stem yields empty `<section id="confrontations"></section>` at reference_renderer.py:839, anchor resolves, no other content dropped — reference_renderer.py:830-839
- `[VERIFIED]` Validator reuses `load_reference_theme` — single source of truth shared with renderer — reference_chrome.py:24
- `[VERIFIED]` Registration matches sibling pattern (`locations`, `audio`) — __main__.py:33
- `[SEC]` CSS injection via unescaped theme values in `_theme_style_block` — DEFERRED (pre-existing, shipped in 63-4, not in this diff; theme.yaml is dev-authored content) — reference_renderer.py:577
- `[SEC]` ANSI escape injection in `click.echo` of YAML-sourced theme fields — DEFERRED (low confidence; single-operator dev tool, dev-authored content) — reference_chrome.py:28
- `[SEC]` `from None` "exception swallowing" — DISMISSED: error surfaced loudly via `[FAIL]` echo immediately before exit; `from None` is the ruff-B904-sanctioned form for translating an exception to a clean CLI exit (no traceback dump) — reference_chrome.py:27

### Rule Compliance

- **No silent fallbacks:** Validator fails loud (`[FAIL]` + exit 1). Tropes exclusion is a named-set membership, not a silent skip. COMPLIANT.
- **No silent exception swallowing:** `MissingThemeFieldError` caught specifically, surfaced via stderr echo. COMPLIANT (security agent's finding 3 dismissed — see above).
- **No stubbing:** No stubs. COMPLIANT.
- **Path handling (pathlib):** `Path(pack_dir)` used. COMPLIANT.
- **open() with encoding:** Validator delegates file IO to `load_reference_theme` which uses `encoding="utf-8"`. COMPLIANT.
- **No content-coupled tests:** All 14 validator tests use `tmp_path` fixtures, zero live `genre_packs/*` reads. COMPLIANT.
- **Every test suite needs a wiring test:** `TestWiring::test_subcommand_registered_in_validate_group` proves the subcommand is reachable from the production click group. COMPLIANT.

### Devil's Advocate

Could this code be broken in ways the tests don't show? Let me argue the worst case. The validator takes a filesystem path from the operator — a confused dev could point it at a non-pack directory; click's `exists=True, file_okay=False` gate stops files but not arbitrary dirs, so `load_reference_theme` would raise `MissingThemeFieldError` ("theme.yaml not found") — that's the loud-fail path, acceptable. What if `theme.yaml` exists but is an empty file? `yaml.safe_load` returns `None`, `load_reference_theme` coerces to `{}`, and every `_require_str` raises on the first missing field — loud fail, correct. What if a malicious theme.yaml carries CSS-breaking values or ANSI escapes? Those are the two deferred security findings — real but out of this story's diff (CSS) or negligible for a single-operator dev tool (ANSI). What about the tropes exclusion — could removing `tropes.yaml` from `RULES_FILES` silently drop content a pack relies on? I traced this: the `confrontations` TOC section renders empty but its anchor still resolves, and unmapped stems append at page end, so no *other* content is lost. The one thing that genuinely broke: a stale parametrized test assertion in a third file — caught by preflight's full-suite run. That is the blocking finding. A stressed reviewer who only re-ran the changed files (as verify did) would have missed it and shipped a red suite to develop. The lesson reinforces the project's own rule: changed-file-only test runs are insufficient when production changes remove symbols that sibling tests reference. The fix is a one-line parametrize deletion — trivial, but the suite must be green before merge.

**Handoff:** Back to Dev (green rework) — the fix is a stale-test deletion adjacent to the dead-code removal Dev performed.

## Reviewer Assessment (round 2 — post-rework)

**Verdict:** APPROVED

The sole round-1 blocking finding is resolved. Dev's rework (commit 242f78b) removed the stale `("tropes", "trope")` parametrize entry from `test_reference_renderer_namespacing.py`. Full-suite preflight re-run confirms:
- `test_kind_for_stem[tropes-trope]` is ABSENT from failures (blocker resolved)
- 17 failures remain, all pre-existing on develop (matches round-1 baseline) — none branch-introduced
- +1 net passing test (7943 → 7944), lint errors all pre-existing and outside changed files

**Data flow traced:** operator-supplied `pack_dir` → `click.Path(exists=True, file_okay=False)` gate → `load_reference_theme(pack_path)` → `[OK]`/`[FAIL]` echo. Safe: no shell, no eval, `pack_name` only flows to terminal output.

**Pattern observed:** validator is a thin reuse-first wrapper around the renderer's own `load_reference_theme` — single source of truth for required fields. reference_chrome.py:24.

**Error handling:** `MissingThemeFieldError` caught specifically, surfaced loudly via `[FAIL]` + exit 1. No silent swallow. reference_chrome.py:25-27.

**Tag carryforward (round 1):** `[PREFLIGHT]` blocker → RESOLVED. `[SEC]` ×3 → 1 dismissed (`from None` is ruff-B904-sanctioned, error surfaced), 2 deferred (CSS injection pre-existing from 63-4, out of diff; ANSI escape negligible for single-operator dev tool). `[VERIFIED]` ×5 stand unchanged.

**Two deferred security findings** logged as non-blocking delivery findings for follow-up — neither is introduced by this story.

**Handoff:** To Architect for spec-reconcile, then SM for finish-story.

## Delivery Findings

No upstream findings at setup stage.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Task 25 (R2 screenshots, AC-10) is a no-op — the `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/` directory does not exist on this branch and has no git history. No test written. Dev should confirm and document as descoped. *Found by TEA during test design.*
- **Improvement** (non-blocking): `test_tropes_content_never_rendered_on_rules_page` currently passes because it checks for "Keeper Only Trope" which doesn't appear even when tropes.yaml renders (the content goes through the walker which may transform it). After Dev removes tropes.yaml from RULES_FILES, the test will continue to pass — but that's correct behavior (content absent = assertion holds). The real RED signal is `test_tropes_yaml_excluded_from_rules_files` which directly asserts the tuple membership. *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): CSS injection vector in `_theme_style_block` — unescaped theme palette/font values interpolated into inline `<style>`. Affects `sidequest-server/sidequest/server/reference_renderer.py:577` (validate color values against hex/named-color allowlist, font families against safe-identifier pattern before interpolation). Pre-existing from 63-4, not in this diff; surface as follow-up. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): ANSI/control-char escape injection in validator terminal output — YAML-sourced `theme.archetype`/`display_font_family` echoed verbatim. Affects `sidequest-server/sidequest/cli/validate/reference_chrome.py:28` (strip control chars < 0x20 before echo). Low risk for single-operator dev tool. *Found by Reviewer during code review.*

## Design Deviations

No deviations at setup stage.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.
- **Stale sibling-test assertion from dead-code removal (rework round 1)**
  - Spec source: context-story-63-5.md, "Constraints / Project Memory" — "removing dead `_KIND_OVERRIDES["tropes"]` entry is acceptable since it's directly related to the tropes exclusion change"
  - Spec text: "Boy-scout bounded — removing dead `_KIND_OVERRIDES["tropes"]` entry is acceptable"
  - Implementation: Removed the override but initially missed the sibling parametrize assertion in test_reference_renderer_namespacing.py:43 that referenced it; corrected in rework round 1 (commit 242f78b)
  - Rationale: The dead-code removal was authorized; the stale test was a consequence not caught by changed-file-only test runs in green/verify
  - Severity: minor
  - Forward impact: none — fully resolved within this story

### Reviewer (audit)
- TEA entry (no deviations) → ✓ ACCEPTED by Reviewer: test design followed spec; the stale `test_kind_for_stem` parametrize entry is a sibling-file test not authored by this story, orphaned by Dev's dead-code removal — not a spec deviation, a missed full-suite run.
- Dev entry (no deviations) → ✓ ACCEPTED by Reviewer: implementation matches spec exactly. The `_KIND_OVERRIDES["tropes"]` removal was authorized by story context as bounded boy-scout; its only flaw was not updating the orphaned sibling assertion (the blocking finding, routed back as green rework).

### Architect (reconcile)

Verified the TEA and Dev deviation entries against the actual code and spec sources: all fields are accurate, spec text quotes are correct excerpts from `context-story-63-5.md`, and the Dev stale-test entry's commit reference (242f78b) matches the rework. Two deviations were not formally logged in-flight but should appear in the audit manifest:

- **Task 25 (R2 screenshots) descoped to no-op**
  - Spec source: `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` Task 25 (lines 3009–3055), surfaced as story AC-10
  - Spec text: "All PNG files from `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/` uploaded to R2 ... Local PNG files deleted ... README.md created with pointer to R2 URL"
  - Implementation: No action taken. The `screenshots/` directory does not exist on this branch or develop and has no git history — there are no PNGs to stage. Confirmed by `find docs/design-bundles/ -name "*.png"` (empty) and `git log --all -- <screenshots path>` (empty).
  - Rationale: The plan was authored assuming a screenshots directory that was either never committed or removed before this branch. Staging nonexistent files is impossible; the task is vacuous, not skipped.
  - Severity: minor
  - Forward impact: none — if screenshots are later produced, a fresh story should stage them per the plan's R2 convention. No sibling story in epic 63 depends on this asset staging.

- **AC-6 implemented by extending an existing recipe rather than adding a new `content-validate`**
  - Spec source: `context-story-63-5.md`, AC-6
  - Spec text: "`just content-validate` recipe added to orchestrator justfile (walks all live packs via the validator)"
  - Implementation: A `content-validate` recipe already existed (aliasing `reference-validate-all`). Dev added a new `reference-chrome-validate` recipe and wired it as a prerequisite of `content-validate` (`content-validate: reference-chrome-validate reference-validate-all`). The AC intent — `content-validate` walks all live packs through the new chrome validator — is satisfied.
  - Rationale: Adding a second recipe named `content-validate` would collide; extending the existing aggregate is the correct just idiom and matches the sibling `reference-validate-all` pattern.
  - Severity: trivial
  - Forward impact: none.

AC deferral check: AC-10 is the only non-DONE AC. It is DESCOPED (not deferred to a future story) — there is no work item to carry forward because the source files do not exist. Reviewer's round-2 APPROVED verdict did not invalidate this descope. No status change.