---
story_id: "59-5"
jira_key: "none"
epic: "59"
workflow: "tdd"
---
# Story 59-5: Magic_working dispatch handler + sidecar engagement retirement

## Story Details
- **ID:** 59-5
- **Jira Key:** none
- **Epic:** 59 — Intent Router — Mechanical-Engagement Spine
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Stack Parent:** 59-4 (feat/59-4-confrontation-cutover-router-wiring)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-24T22:41:52Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24T22:03:41Z | 2026-05-24T22:06:44Z | 3m 3s |
| red | 2026-05-24T22:06:44Z | 2026-05-24T22:16:31Z | 9m 47s |
| green | 2026-05-24T22:16:31Z | 2026-05-24T22:27:04Z | 10m 33s |
| spec-check | 2026-05-24T22:27:04Z | 2026-05-24T22:30:00Z | 2m 56s |
| verify | 2026-05-24T22:30:00Z | 2026-05-24T22:33:09Z | 3m 9s |
| review | 2026-05-24T22:33:09Z | 2026-05-24T22:38:47Z | 5m 38s |
| spec-reconcile | 2026-05-24T22:38:47Z | 2026-05-24T22:41:52Z | 3m 5s |
| finish | 2026-05-24T22:41:52Z | - | - |

## Sm Assessment

Story 59-5 follows the established IntentRouter dispatch pattern from 59-4 (confrontation cutover). The shape is well-proven: new handler in subsystems/, vocabulary addition to the router, sidecar retirement in narration_apply.py. All four prior stories (59-1 through 59-4) are done and merged.

**Routing to TEA (red phase):** TDD workflow, 5 points. TEA writes failing tests covering the 5 ACs: fixture dispatch, retirement guard, lie-detector coverage verification, pipeline wiring, and ADR-013 drift note. The epic context (context-epic-59.md) and story context (context-story-59-5.md) provide full architectural detail.

**Dependencies verified:** 59-4 is done (merged to develop). Feature branch `feat/59-5-magic-working-dispatch` created from current develop in sidequest-server.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- **Gap** (non-blocking): AC2 test used wrong function name `apply_narration` (does not exist). Fixed to use `_apply_narration_result_to_snapshot` with `room_for` helper. Affects `tests/agents/subsystems/test_magic_working_dispatch.py` (test fixture correction). *Found by Dev during implementation.*
- **Improvement** (non-blocking): 47 pre-existing test failures on develop in encounter/NPC/dice areas unrelated to magic changes. Affects `tests/server/test_encounter_*`, `tests/server/test_npc_*`, `tests/server/dispatch/test_sealed_letter_*` (pre-existing, not introduced by 59-5). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Stale comment at `narration_apply.py:1676-1683` references the removed sidecar consumer ("swallowed below", "wired below in the else branch"). Affects `sidequest/server/narration_apply.py` (clean up orphaned comment block). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No deviations recorded yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- **Handler includes threshold status promotions** → ✓ ACCEPTED by Reviewer: Correct — the promotion chain is load-bearing (test_threshold_promotion.py pins it) and the relocation preserves identical behavior. Not adding it would have been a regression.

### Reviewer (audit)
- No additional undocumented deviations found.

### Architect (reconcile)
- **Narrator prompt update not performed but may be a no-op**
  - Spec source: context-story-59-5.md, Scope Boundaries, "In scope"
  - Spec text: "Narrator prompt updated: magic engagement is no longer narrator's signal"
  - Implementation: No changes to `sidequest/agents/narrator_prompts/output_only.md`. The prompt at line 45 references `apply_spell_effect` tool (a tool-use mechanism), not the retired `result.magic_working` sidecar field. The prompt never mentioned the sidecar field, so there is nothing to remove.
  - Rationale: The `apply_spell_effect` tool is a separate, still-live mechanism (ADR-102 tool-use protocol) distinct from the retired `result.magic_working` structured output sidecar. The prompt instruction for magic routing refers to the tool, not the sidecar. Updating it would be incorrect — the tool still exists and works.
  - Severity: trivial
  - Forward impact: none — the sidecar field was never referenced in the prompt; the tool-use path remains active and correct

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD workflow, 5-point handler story with 5 ACs

**Test Files:**
- `tests/agents/subsystems/test_magic_working_dispatch.py` — 10 tests covering all 5 ACs

**Tests Written:** 10 tests covering 5 ACs
**Status:** RED (8 failing, 2 passing — ready for Dev)

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| AC1 — handler applies working pre-narrator | `test_magic_working_handler_applies_working_on_snapshot`, `test_magic_working_handler_debits_costs`, `test_magic_working_handler_emits_otel_span` | failing (ModuleNotFoundError) |
| AC1 — fail-loud behavior | `test_magic_working_handler_raises_when_no_magic_state`, `test_magic_working_handler_raises_on_unknown_actor` | failing (ModuleNotFoundError) |
| AC2 — retirement guard | `test_narration_apply_ignores_result_magic_working_sidecar` | failing (sidecar consumer still exists) |
| AC3 — lie-detector coverage | `test_lie_detector_emits_mismatch_when_magic_dispatched_not_engaged`, `test_lie_detector_no_false_positive_when_magic_engaged` | **passing** (watcher shipped in 59-3) |
| AC4 — wiring | `test_magic_working_handler_registered_with_dispatch_bank`, `test_run_dispatch_bank_invokes_magic_working_handler` | failing (handler not registered) |
| AC5 — ADR-013 drift note | No test (docs-only AC) | n/a |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Every Test Suite Needs a Wiring Test | `test_magic_working_handler_registered_with_dispatch_bank`, `test_run_dispatch_bank_invokes_magic_working_handler` | failing |
| No Source-Text Wiring Tests | All wiring tests use `get_registered()` reflection | compliant |
| No Silent Fallbacks | `test_magic_working_handler_raises_when_no_magic_state`, `test_magic_working_handler_raises_on_unknown_actor` | failing |
| OTEL Observability Principle | `test_magic_working_handler_emits_otel_span` | failing |

**Rules checked:** 4 of 4 applicable rules have test coverage
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev (Ponder Stibbons) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/agents/subsystems/magic_working.py` — NEW handler: calls apply_magic_working + status promotions
- `sidequest/agents/subsystems/__init__.py` — Register magic_working handler in _register_defaults()
- `sidequest/server/narration_apply.py` — Retire result.magic_working sidecar consumer (lines 1684-1709 removed)
- `tests/agents/subsystems/test_magic_working_dispatch.py` — Fix AC2 test import (apply_narration → _apply_narration_result_to_snapshot)
- `tests/magic/test_narration_apply_magic.py` — Update wiring test from sidecar path to dispatch handler
- `tests/magic/test_threshold_promotion.py` — Update wiring test from sidecar path to dispatch handler

**Tests:** 10/10 passing (GREEN) + 240/240 across magic/subsystem suites
**Branch:** feat/59-5-magic-working-dispatch (pushed)

**Handoff:** To TEA (Igor) for verify phase

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with one minor gap and one trivial finding)
**Mismatches Found:** 2

- **AC5 ADR-013 drift note not updated** (Missing in code — Cosmetic, Minor)
  - Spec: "ADR-013's drift note gains a reference to magic_working engagement also being superseded by ADR-113 on the SDK path"
  - Code: ADR-013 is in the orchestrator repo; story repos is sidequest-server only. No change made.
  - Recommendation: D (Defer) — ADR-013 lives in the orchestrator repo. SM can append the drift note during finish when committing orchestrator sprint changes. No code impact.

- **Stale comment in narration_apply.py:1676-1683** (Extra in code — Cosmetic, Trivial)
  - Spec: n/a (not specified)
  - Code: Comment references "swallowed below" and "wired below in the else branch" — the sidecar code those lines describe was removed by this PR.
  - Recommendation: A (Update spec/code) — Reviewer can flag for cleanup or it can be cleaned in a subsequent touch. No functional impact.

**Decision:** Proceed to verify

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | 3 high (test helper duplication across files — out of story scope), 2 low (intentional patterns) |
| simplify-quality | 5 findings | 2 medium (handler param types), 1 medium (incomplete mock — dismissed, intentional), 2 low (misapplied rules — dismissed) |
| simplify-efficiency | clean | No unnecessary complexity |

**Applied:** 0 high-confidence fixes (reuse findings touch out-of-scope test file)
**Flagged for Review:** 5 findings (3 reuse, 2 quality — reviewer discretion)
**Noted:** 4 low-confidence observations (dismissed with rationale)
**Reverted:** 0

**Overall:** simplify: clean (no auto-applied changes)

**Quality Checks:** Lint clean, 224/224 tests passing (0 failed, 50 skipped)
**Handoff:** To Granny Weatherwax for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 cosmetic (stale "FAILS TODAY" in test docstrings) | dismissed 1 — cosmetic, pre-implementation docstrings from red-phase commit |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 3 findings | dismissed 3 — all pre-existing bank behavior, not introduced by this PR |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 returned, 7 disabled)
**Total findings:** 0 confirmed, 4 dismissed (with rationale), 0 deferred

### Security Findings Dismissal Rationale

- **Bank broad `except Exception` (medium):** Pre-existing `run_dispatch_bank` design from 59-2. The handler correctly raises `MagicWorkingParseError`; the bank catches per-dispatch exceptions and records them as error spans + `BankResult.errors`. This is the same pattern confrontation uses. The OTEL `intent_router.subsystem` span carries the error class name. Not introduced by this PR.
- **`dict(dispatch.params)` without isinstance guard (low):** `SubsystemDispatch.params` is pydantic-validated with `default_factory=dict`, always a dict under normal construction. Theoretical `model_construct` bypass is not a realistic attack vector for an internal dispatch type.
- **`repr(exc)` in BankResult.errors (low):** Pre-existing bank logging pattern. Errors are server-side only, never forwarded to WebSocket clients. For a personal game server, log-level echo of dispatch params is not a security concern.

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Handler delegates to existing `apply_magic_working` entrypoint — `magic_working.py:58` calls `apply_magic_working(snapshot=snapshot, patch_field=dict(dispatch.params))`. Reuse-first: no new parse/validate logic, no new OTEL span definitions. Mirrors confrontation handler pattern at `confrontation.py:124-133`. Complies with CLAUDE.md "Don't Reinvent — Wire Up What Exists."

2. [VERIFIED] Sidecar consumer fully removed — `narration_apply.py` diff shows 27-line block cleanly excised at former lines 1684-1709. No dangling references to `result.magic_working` remain in `_apply_narration_result_to_snapshot`. `apply_magic_working` function itself is preserved (still called by the handler). Complies with AC2.

3. [VERIFIED] Handler registration follows idempotent pattern — `__init__.py:137-145` adds `("magic_working", run_magic_working_dispatch)` to the `_register_defaults` tuple using the existing pop-then-assign pattern. Import is alphabetically sorted. Wiring test at `test_magic_working_dispatch.py:487-499` verifies via `get_registered()` reflection. Complies with CLAUDE.md "Every Test Suite Needs a Wiring Test" and "No Source-Text Wiring Tests."

4. [VERIFIED] Fail-loud behavior — handler propagates `MagicWorkingParseError` for: missing `magic_state` (via `apply_magic_working`'s guard at `narration_apply.py:644-645`), invalid pydantic schema (via `MagicWorking.model_validate` at line 647-649), unknown actor (via `apply_working` KeyError at line 655-656). Tests pin all three at `test_magic_working_dispatch.py:316-360`. Complies with CLAUDE.md "No Silent Fallbacks."

5. [VERIFIED] OTEL span emission — `apply_magic_working` calls `magic_working_span()` context manager at `narration_apply.py:682-696`, which uses `tracer()` from `sidequest.telemetry.spans`. The test at `test_magic_working_dispatch.py:268-307` monkeypatches `spans_module.tracer` and asserts a span with "magic" and "working" in the name fires. Complies with CLAUDE.md "OTEL Observability Principle."

6. [LOW] Stale comment at `narration_apply.py:1676-1683` references "swallowed below" and "wired below in the else branch" — both refer to the removed sidecar consumer. Non-functional, cosmetic. Already noted by Architect in spec-check.

7. [LOW] Test docstrings in `test_magic_working_dispatch.py` still say "FAILS TODAY: module does not exist" (lines 198, 241, 279, 322, 345). These are from the red-phase commit and weren't cleaned after implementation. Cosmetic only.

8. [SEC] Security subagent findings (3) all relate to pre-existing dispatch bank behavior, not code introduced by this PR. Dismissed with rationale above.

### Data Flow Trace

`dispatch.params` (dict from `SubsystemDispatch`, pydantic-validated) → `dict(dispatch.params)` (shallow copy) → `apply_magic_working(patch_field=...)` → `MagicWorking.model_validate(patch_field)` (pydantic strict validation, `extra="forbid"`) → `snapshot.magic_state.apply_working(working)` (mutates ledger bars, appends to working_log) → `_apply_magic_status_promotions()` (promotes threshold crossings to character statuses). Safe: pydantic validates at the boundary, fail-loud on schema mismatch, no user-facing error surfaces.

### Rule Compliance

| Rule | Instances Checked | Compliant |
|------|-------------------|-----------|
| No Silent Fallbacks | `run_magic_working_dispatch` raises on invalid input | Yes |
| Don't Reinvent — Wire Up What Exists | Handler reuses `apply_magic_working`, doesn't reimplement | Yes |
| Every Test Suite Needs a Wiring Test | `test_magic_working_handler_registered_with_dispatch_bank` | Yes |
| No Source-Text Wiring Tests | Uses `get_registered()` reflection | Yes |
| OTEL Observability Principle | `magic_working_span()` fires via `apply_magic_working` | Yes |
| Verify Wiring, Not Just Existence | Bank end-to-end test at line 502-532 | Yes |
| No Stubbing | Handler is complete, not a placeholder | Yes |

### Devil's Advocate

What if this code is broken? The handler passes `dict(dispatch.params)` directly to `apply_magic_working` as `patch_field`. If the IntentRouter (Haiku) emits a `params` dict that doesn't match the `MagicWorking` pydantic schema — wrong field names, missing required fields, extra fields — `MagicWorking.model_validate` raises `ValidationError`, which `apply_magic_working` wraps as `MagicWorkingParseError`. The dispatch bank catches this, logs it, and continues. The narrator proceeds without pre-applied magic state. From the player's perspective, they said "I cast a spell" and nothing mechanical happened — the narrator improvises, which is exactly the SOUL Illusionism failure mode the entire Intent Router epic exists to prevent. This is the known architectural tension: the bank's catch-all design means router classification errors (Haiku misclassifies or emits malformed params) silently degrade to narrator-only mode. However, the dispatch engagement watcher (59-3) catches this: it detects a `magic_working` dispatch with no matching `working_log` entry and emits a `dispatch_engagement.magic_working.mismatch` OTEL span. The GM panel would show the engagement gap. So the failure IS observable, just not user-surfacing. This is pre-existing architectural behavior (same for confrontation), not a regression.

What about a confused user? The handler signature accepts `pack: Any = None` but never uses it. A future developer might wonder why it's there. Answer: `_filter_context_for_callable` in the bank passes kwargs matching the handler's signature. The bank's context always includes `pack`, and if the handler didn't declare it, `_filter_context_for_callable` would strip it — which is correct behavior. The `pack` param exists only for signature compatibility, not for use. The confrontation handler uses `pack` (it needs the ConfrontationDef registry), but the magic handler doesn't — `apply_magic_working` reads config from `snapshot.magic_state.config` instead.

What about a stressed filesystem or race condition? None relevant — the handler is synchronous state mutation on an in-memory snapshot. No file I/O, no database writes, no network calls. The snapshot is the authoritative state.

**Conclusion from devil's advocate:** No new issues uncovered. The handler is minimal, correctly delegates, and the known architectural tension (bank catch-all vs fail-loud) is pre-existing and mitigated by the dispatch engagement watcher.

**Handoff:** To Captain Carrot Ironfoundersson for finish-story
## Impact Summary

**Compilation Status:** Success (3 findings, 0 blocking)

### Delivery Findings Summary

| Finding Type | Urgency | Count | Details |
|--------------|---------|-------|---------|
| Gap | non-blocking | 1 | AC2 test fixture correction (wrong function name) — fixed during implementation |
| Improvement | non-blocking | 2 | Pre-existing test failures (47 tests, unrelated); stale comment in narration_apply.py |
| **Blocking** | — | **0** | — |

### Test Coverage Summary

| Category | Result | Details |
|----------|--------|---------|
| Target Tests | 10/10 PASS | All AC-specific tests passing (magic_working_dispatch suite) |
| AC1 Coverage | 3/3 tests | Handler dispatch, cost debit, OTEL emission — all GREEN |
| AC2 Coverage | 1/1 tests | Sidecar retirement guard — GREEN |
| AC3 Coverage | 2/2 tests | Lie-detector watcher (pre-shipped in 59-3) — GREEN |
| AC4 Coverage | 2/2 tests | Dispatch bank wiring — GREEN |
| AC5 Coverage | n/a | ADR-013 drift note (deferred to orchestrator, non-code) |
| Wiring Tests | 2/2 PASS | `get_registered()` reflection + end-to-end bank invocation — compliant |

### Blocking Issues

None. All findings are cosmetic/non-functional (stale comment, pre-existing test noise).

### Ready-to-Finish Assessment

- **Tests:** GREEN (10/10, all target ACs covered)
- **Findings:** 3 non-blocking (0 blocking)
- **Reviewer Verdict:** APPROVED
- **Code Quality:** All CLAUDE.md rules compliant (no silent fallbacks, reuse-first, wiring verified, OTEL instrumented)
- **Branch Status:** Clean, up to date with origin
- **Session:** Complete (all phases passed, Reviewer approved)

**Recommendation:** Ready to finish.

