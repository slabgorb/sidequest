---
story_id: "61-17"
jira_key: "61-17"
epic: "61"
workflow: "trivial"
---
# Story 61-17: Fix stale test_zones_carry_cache_boundary_flag — 61-10 promoted narrator_constraints to System/cached bucket (#434) but test still asserts User-bucket cached=False

## Story Details
- **ID:** 61-17
- **Jira Key:** 61-17
- **Workflow:** trivial
- **Stack Parent:** none
- **Priority:** p2
- **Points:** 3

## Acceptance Criteria

**AC1:** The stale assertion in test_zones_carry_cache_boundary (narrator_constraints expected cached=False) is updated to cached=True, matching the 61-10/#434 behavior where narrator_constraints lives in the System/cached bucket.

**AC2:** The full server test suite passes (uv run pytest), confirming no other tests depend on the old expectation.

**AC3:** Wiring sanity — verify the test still meaningfully asserts the cache-boundary contract (it should now confirm narrator_constraints IS cached, not merely flip to a vacuous pass).

## Story Context

Story 61-10 (merged PR #434) promoted `narrator_constraints` from the User bucket into the System/cached bucket. A test still asserts the old expectation — `narrator_constraints` cached=False — and is now stale. The fix is to flip that assertion to cached=True to match current behavior.

**Root cause (from git-history audit):** story 61-10 promoted `narrator_constraints` from User bucket into System/cached bucket. Test location: sidequest-server/tests/agents/ — the test named `test_zones_carry_cache_boundary` (audit also referenced `test_prompt_cache_attribution_otel.py`). Dev should grep for `test_zones_carry_cache_boundary` and `narrator_constraints` cached assertions to locate the exact stale assert before changing it.

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-28T16:31:09Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28 | 2026-05-28T16:25:02Z | 16h 25m |
| implement | 2026-05-28T16:25:02Z | 2026-05-28T16:28:31Z | 3m 29s |
| review | 2026-05-28T16:28:31Z | 2026-05-28T16:31:09Z | 2m 38s |
| finish | 2026-05-28T16:31:09Z | - | - |

## Delivery Findings

No upstream findings.

### Dev (implementation)
- No upstream findings.

### Reviewer (code review)
- No upstream findings.

## Design Deviations

None.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **"No deviations from spec." (Dev)** → ✓ ACCEPTED by Reviewer: confirmed against the diff — the change is exactly the AC1 assertion flip plus an AC3-supporting comment correction. No undocumented deviations found; correcting the now-false "User-bucket guardrail" comment is within AC3's intent (the test must read true, not vacuous).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/tests/agents/test_prompt_cache_attribution_otel.py` — flipped stale `narrator_constraints` per-section assertion from `cached is False` to `cached is True`; corrected the explanatory comment that falsely described it as a "User-bucket guardrail" (it is now System-bucket per Story 61-10).

**Root cause verified:** `sidequest/agents/prompt_framework/bucket.py:68-71` adds `narrator_constraints` to `STABLE_SECTION_NAMES` (Story 61-10), routing it to `SectionBucket.System` → cached. The test asserted the pre-61-10 expectation and failed with `assert True is False`.

**AC coverage:**
- AC1 — stale assertion flipped to `cached=True`. ✓
- AC2 — `tests/agents/test_prompt_cache_attribution_otel.py` 9/9 pass; full server suite 7543 passed. The 6 failures are pre-existing content/corpus validation suites (`tests/cli/validate/`, `tests/scripts/test_audit_namegen_corpora.py`) untouched by this change. ✓
- AC3 — not vacuous: the assertion still verifies `narrator_constraints` IS cached (rides `system_blocks[0]`); the zone-level loop continues to assert the CACHED/UNCACHED split. Misleading comment corrected so the contract reads true. ✓

**Tests:** 9/9 passing in target file (GREEN); full suite GREEN modulo 6 unrelated pre-existing content failures.
**Branch:** feat/61-17-fix-stale-cache-boundary-test (pushed, commit dffcf5b)

**Handoff:** To review (Colonel Potter).

## Sm Assessment

Trivial single-repo (sidequest-server) test-fix story. Setup complete: session created, branch `feat/61-17-fix-stale-cache-boundary-test` cut, ACs and root-cause context written.

**Scope:** Story 61-10 (PR #434) promoted `narrator_constraints` from the User bucket into the System/cached bucket. The test `test_zones_carry_cache_boundary` still asserts the old expectation (`narrator_constraints` cached=False) and is now stale. Flip that assertion to cached=True to match current behavior.

**Handoff to Dev (Winchester):** Grep `tests/agents/` for `test_zones_carry_cache_boundary` and `narrator_constraints` cached asserts to locate the exact stale line before editing. AC3 is the trap to watch — confirm the test still meaningfully asserts the cache-boundary contract (narrator_constraints IS cached) rather than flipping to a vacuous pass. Run full `uv run pytest` per AC2 to confirm no other test depends on the old expectation.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (9/9 GREEN, lint clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled returned clean; 7 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

Test-only diff (8 lines, 1 file): `tests/agents/test_prompt_cache_attribution_otel.py`. Flips the stale `narrator_constraints` per-section assertion in `test_zones_carry_cache_boundary_flag` from `cached is False` to `cached is True`, and corrects the explanatory comment.

**Data flow traced:** Test builds a real prompt via `_run_turn` → reads enriched watcher event `fields.zones` → asserts per-section `cached` flags. The `cached` verdict for `narrator_constraints` derives from `default_bucket_for_section` (`bucket.py:81-90`), which returns `SectionBucket.System` for any name in `STABLE_SECTION_NAMES`. `narrator_constraints` is on that list at `bucket.py:71` (added by Story 61-10), so System → cached=True. The new assertion matches actual engine behavior.

**Independently verified (root cause):** `[VERIFIED] narrator_constraints ∈ STABLE_SECTION_NAMES — sidequest/agents/prompt_framework/bucket.py:71; default_bucket_for_section (bucket.py:88-90) maps STABLE names to SectionBucket.System.` The old `cached is False` expectation was genuinely stale (test failed `assert True is False` before the fix).

**AC3 anti-vacuous check (the trap SM flagged):** `[VERIFIED] assertion is non-vacuous — test_prompt_cache_attribution_otel.py:203 asserts a specific named section (narrator_constraints) IS cached.` A bucketing regression (removing narrator_constraints from STABLE_SECTION_NAMES) would re-break this `is True` assertion. The zone-level loop (lines 177-193) independently asserts the CACHED_ZONES/UNCACHED_ZONES split, so the cache-boundary contract remains strongly tested. Not a vacuous pass.

**Findings by source:**
- `[EDGE]` — skipped (disabled); no boundary logic in a test assertion flip. None.
- `[SILENT]` — skipped (disabled); no error handling in diff. None.
- `[TEST]` — skipped (disabled); reviewer assessed manually — assertion is meaningful, not coupled to implementation internals (reads the public watcher event shape). None.
- `[DOC]` — skipped (disabled); reviewer assessed manually — the corrected comment now accurately describes narrator_constraints as System-bucket per Story 61-10. No stale/misleading docs remain. None.
- `[TYPE]` — skipped (disabled); no type surface changed. None.
- `[SEC]` — reviewer-security clean: cached System-bucket content is operator-static .md prose (no per-turn user interpolation), satisfying ADR-047; no guardrail-bypass risk introduced by this diff. None.
- `[SIMPLE]` — skipped (disabled); diff is already minimal (1 assertion + comment). None.
- `[RULE]` — skipped (disabled); reviewer assessed manually — no source-text wiring test, no silent fallback. Complies with sidequest-server CLAUDE.md test rules. None.

**Error handling:** N/A — test-only change, no production code paths touched.

**Pattern observed:** Correct test maintenance — assertion follows the engine's actual bucketing source of truth (`bucket.py`) rather than a hardcoded stale expectation, at `tests/agents/test_prompt_cache_attribution_otel.py:200-206`.

**Devil's Advocate:** Could this flip be hiding a real regression — i.e., should `narrator_constraints` actually be User-bucket (uncached) and the *production* code be wrong, not the test? Investigated: Story 61-10's bucket.py comment (lines 68-71) documents the deliberate promotion — `narrator_constraints` is byte-static `.md` prose with no runtime interpolation, exactly the profile that belongs in the cached System block. Caching it is correct, not a bug; the test was simply not updated at 61-10's cutover. Could a confused reader think Primacy no longer contains any User-bucket section (losing the original "must NOT share a verdict" contrast)? The zone-level loop still exercises both CACHED and UNCACHED zones, so the System/User cached distinction is still tested elsewhere in the same test — the per-section block now legitimately confirms two System-Primacy sections are both cached. Could the broader suite hide a dependency on the old value? Preflight + Dev's full run show only 6 pre-existing content/corpus failures, none referencing this assertion. No malicious-input or filesystem surface exists in a pure test-assertion change. Nothing uncovered that changes the verdict.

**Handoff:** To SM (Hawkeye) for finish-story.