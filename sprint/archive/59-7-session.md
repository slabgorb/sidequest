---
story_id: "59-7"
jira_key: "NO_JIRA"
epic: "59"
workflow: "tdd"
---

# Story 59-7: Wire three LocalDM subsystems (npc_agency, distinctive_detail_hint, reflect_absence)

## Story Details

- **ID:** 59-7
- **Jira Key:** NO_JIRA (SideQuest does not use Jira per project memory)
- **Epic:** 59 (Intent Router — Mechanical-Engagement Spine)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p2
- **Stack Parent:** none

## Context

Three subsystem modules already exist in `sidequest/agents/subsystems/` from the 2026-04 LocalDM build but have no live dispatch path. Now that the router is live (post 59-4), wire them through `run_dispatch_bank`. Pure additive — no engine retirement, no field zeroing changes. Subsystems wake for the first time since 2026-04-28 dormancy.

### Acceptance Criteria

1. npc_agency dispatch engages its handler when the router emits it (fixture test mirroring 59-4 confrontation shape)
2. distinctive_detail_hint dispatch engages its handler when the router emits it
3. reflect_absence dispatch engages its handler when the router emits it
4. redact_dispatch_package honored: visibility-tagged dispatches filtered before narrator sees them in narrator_instructions (existing prompt_redaction module)
5. Lie-detector watches these three subsystems (extends 59-3 watcher vocabulary)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-25T06:36:29Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-25T00:00:00Z | 2026-05-25T06:06:41Z | 6h 6m |
| red | 2026-05-25T06:06:41Z | 2026-05-25T06:16:45Z | 10m 4s |
| green | 2026-05-25T06:16:45Z | 2026-05-25T06:22:43Z | 5m 58s |
| spec-check | 2026-05-25T06:22:43Z | 2026-05-25T06:24:46Z | 2m 3s |
| verify | 2026-05-25T06:24:46Z | 2026-05-25T06:29:14Z | 4m 28s |
| review | 2026-05-25T06:29:14Z | 2026-05-25T06:35:30Z | 6m 16s |
| spec-reconcile | 2026-05-25T06:35:30Z | 2026-05-25T06:36:29Z | 59s |
| finish | 2026-05-25T06:36:29Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): `prompt_redaction.py` module docstring says "DORMANT" but `redact_dispatch_package` is actively called from `orchestrator.py:1600` on the live narrator prompt path. The DORMANT label predates the ADR-113 router revival and is misleading. Affects `sidequest/agents/prompt_redaction.py` (remove DORMANT marker from docstring). *Found by TEA during test design.*
- **Improvement** (non-blocking): The `__init__.py` docstring note (lines 28-36) says the three subsystems are "registered for symmetry" and "not yet emitted by the live router's prompt." After 59-7 ships this note should be updated to reflect live status. Affects `sidequest/agents/subsystems/__init__.py` (update docstring). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. TEA's non-blocking improvement findings (DORMANT markers, `__init__.py` docstring) were addressed as part of the implementation.

### TEA (test verification)
- No upstream findings during test verification.

### Reviewer (code review)
- **Gap** (non-blocking): `redact_dispatch_package()` iterates only `pkg.per_player` and does not inspect `pkg.cross_player` for `redact_from_narrator_canonical=True` dispatches. Pre-existing gap not introduced by 59-7, but now more relevant with three additional live-path subsystems. Affects `sidequest/agents/prompt_redaction.py` (add cross_player redaction loop). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### TEA (test verification)
- No deviations from spec.

### Reviewer (audit)
- TEA and Dev deviations reviewed. No deviations logged, and none undocumented found. The Architect's spec-check noted one trivial spec ambiguity (AC5 "verification of existing coverage" vs. needed new witness functions) — correctly resolved as category C (clarify spec).

### Architect (reconcile)
- No additional deviations found. TEA, Dev, and Reviewer all reported zero deviations. The spec-check phase's single trivial finding (AC5 ambiguity about "verification of existing coverage") was correctly categorized as spec clarification (C) — the implementation added witnesses that the spec implied but did not explicitly call for, and the watcher code itself documented that 59-7 would add them. No AC deferrals to verify. Deviation manifest is clean.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 4 | confirmed 0, dismissed 3 (pre-existing), deferred 1 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 returned, 7 disabled via settings)
**Total findings:** 0 confirmed, 3 dismissed (with rationale), 1 deferred

### Security Finding Triage

1. **[SEC] npc_agency.py:63 — dispatch.params['situation'] in directive payload** (medium) — Dismissed: pre-existing handler code unchanged by 59-7. The handler logic including f-string payload construction existed since 2026-04 Wave 2A. The injection path is LLM-mediated (router LLM output, not raw player text). ADR-047 sanitization applies at the player→router boundary, not subsystem→narrator. Not introduced by this story.

2. **[SEC] prompt_redaction.py:37 — cross_player not redacted** (high) — Deferred: legitimate gap but pre-existing. `redact_dispatch_package()` was not modified by 59-7. AC4 says "existing prompt_redaction module" and the mechanism works correctly for per_player dispatches, which is all that was in scope. Logged as delivery finding for a future story.

3. **[SEC] dispatch_engagement_watcher.py:122 — NPC name in mismatch evidence** (low) — Dismissed: OTEL spans go to the GM panel (a dev/operator tool, not player-facing). All existing witnesses emit similarly detailed evidence strings. The mismatch scenario requires both the router to dispatch AND the NPC to be absent from the pool — informational, not exploitable.

4. **[SEC] npc_agency.py:38 — silent no-op on missing npc_name** (low) — Dismissed: pre-existing, documented, intentional design (playtest 2026-04-25 P3-MED regression fix). The bank surfaces `data["error"]` as a span attribute for OTEL observability. The "No Silent Fallbacks" rule is satisfied by the structured error data channel, not by raising.

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Watcher witnesses follow established pattern — `_check_npc_agency_engaged` at `dispatch_engagement_watcher.py:118` uses bare `[]` for param access (fail-loud per project rule), case-insensitive `.lower()` matching mirrors the handler's own lookup. `_check_distinctive_detail_engaged` and `_check_reflect_absence_engaged` are always-pass (directive-only subsystems with no snapshot state to verify). Correct per Architect spec-check.

2. [VERIFIED] OTEL span plumbing at `dispatch_engagement.py:34-36,54-56,69-71,119-121` — constants, SPAN_ROUTES registration, `_SUBSYSTEM_TO_SPAN_NAME` mapping, and `__all__` export all follow exact pattern of existing entries at lines 31-33, 51-53, 66-68, 116-118. Every new subsystem has a span.

3. [VERIFIED] Router vocabulary at `intent_router.py:85-91` — adds all six subsystem names (three pre-existing + three new) so the prompt is complete. The subsystem descriptions are terse and accurate.

4. [VERIFIED] No handler logic changes — `npc_agency.py`, `distinctive_detail.py`, `reflect_absence.py` only had docstring updates (DORMANT → live-path). Zero code changes to handler functions. Confirmed via `git diff develop -- sidequest/agents/subsystems/npc_agency.py` showing only lines 1-15 changed (docstring).

5. [VERIFIED] Docstrings are accurate — each module now references ADR-113 and story 59-7. `prompt_redaction.py` correctly states it's live since story 59-4. `__init__.py` correctly states all six subsystems are live.

6. [MEDIUM] [SEC] `redact_dispatch_package()` does not iterate `cross_player` — deferred as pre-existing gap, not introduced by this story. Logged as delivery finding.

7. [EDGE] No edge case concerns in new code — the three witness functions are minimal (one pool lookup, two always-pass). The pool lookup uses the same case-insensitive pattern as the handler itself.

8. [SILENT] No silent failures introduced — all new code follows existing fail-loud patterns. The watcher raises `KeyError` on missing params (line 119), consistent with confrontation/magic/scenario witnesses.

9. [TEST] 22 tests cover all 5 ACs with OTEL span verification, redaction filtering, watcher witness registration, router vocabulary, and DORMANT marker removal. Tests use behavioral assertions (dict membership, OTEL spans), not source-text grep.

10. [DOC] Docstring updates are accurate and complete. No stale references remain.

11. [TYPE] No type design concerns — all functions have complete type annotations matching existing patterns.

12. [SIMPLE] Pure additive changes — no unnecessary abstractions, no scope creep. 81 lines added, 62 removed (net +19 production lines).

13. [RULE] No project rule violations in changed code. Fail-loud param access, OTEL spans on every subsystem decision, no silent fallbacks, no source-text wiring tests.

### Devil's Advocate

This code looks clean — suspiciously clean. What could go wrong?

The npc_agency witness checks `snapshot.npc_pool` but the handler receives `npc_pool` via the bank's context dict. What if the pool passed to the bank differs from the snapshot's pool? The watcher runs post-turn on the snapshot; the handler runs pre-narrator on context injected by the orchestrator. If the orchestrator passes a stale pool to the bank but the snapshot has been updated by another subsystem, the watcher could fire false mismatch spans — the handler found the NPC (old pool) but the watcher doesn't (new pool), or vice versa. However, this is an orchestrator-level timing concern that applies equally to ALL witnesses (confrontation checks `snapshot.encounter` which is also set by the bank), not unique to 59-7.

The always-pass witnesses for distinctive_detail and reflect_absence mean the lie detector is blind to these subsystems. If either starts silently failing in the future (e.g., a bug causes empty directives), the watcher won't catch it. But there's nothing on the snapshot to verify against for directive-only subsystems — the watcher's `(package, snapshot)` signature can't observe directive production. A future enhancement could add a `bank_result` parameter to the watcher, but that's a different story.

The router vocabulary adds subsystem names to the system prompt, which is stable (cached). If Haiku starts aggressively emitting dispatches for these subsystems on every turn, the per-turn subsystem execution cost increases. But the handlers are cheap (no LLM calls, no I/O) — npc_agency does a list scan, distinctive_detail builds a string, reflect_absence returns hardcoded directives. No performance concern.

Could a malicious player craft input that makes the router emit a dispatch with adversarial params? The router's output is constrained by Pydantic's `DispatchPackage.model_validate()` — unknown fields are rejected. But within the schema, `params` is a `dict[str, Any]`, so the router LLM could echo player-controlled text into param values. This is the pre-existing injection concern from finding #1 — mediated by the router LLM, not a direct path.

None of these uncover a blocker. The code is genuinely clean additive wiring.

**Data flow traced:** Player action → `_build_user_prompt()` → Haiku LLM → JSON → `DispatchPackage.model_validate()` → `run_dispatch_bank()` → `_check_npc_agency_engaged(dispatch, snapshot)` → mismatch span if NPC not in pool. Safe because Pydantic validates schema, witnesses use fail-loud `[]` access, and OTEL spans surface every decision.

**Pattern observed:** All three witnesses follow the established pattern at `dispatch_engagement_watcher.py:85-115` — extract param, check snapshot, return evidence or None. Clean extension.

**Error handling:** `KeyError` on missing params propagates through the bank's try/except at `__init__.py:261` which catches and logs the exception without crashing the turn. Consistent with existing witnesses.

**Handoff:** To Captain Carrot (SM) for finish-story

## Tea Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 6 findings | All pre-existing patterns (retry loop duplication, param validation boilerplate, parallel dicts) — none introduced by 59-7 |
| simplify-quality | clean | No issues |
| simplify-efficiency | 6 findings | Pre-existing patterns (topo_sort, retry loop, string branch). One 59-7 item (no-op witnesses) is intentional per Architect spec-check |

**Applied:** 1 format fix (ruff import sorting + formatting in test file)
**Flagged for Review:** 0 medium-confidence findings (all pre-existing, not in scope)
**Noted:** 12 low/medium observations about pre-existing codebase patterns
**Reverted:** 0

**Overall:** simplify: applied 1 fix (formatting only)

**Quality Checks:** ruff lint passing on changed files, 22/22 tests GREEN
**Handoff:** To Granny Weatherwax (Reviewer) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 1 (trivial — spec ambiguity, correct implementation)

- **AC5 spec says "verification of existing coverage" but new witnesses were needed** (Ambiguous spec — Behavioral, Trivial)
  - Spec: "This is a verification of existing coverage, not new watcher logic."
  - Code: Added three new witness functions (`_check_npc_agency_engaged`, `_check_distinctive_detail_engaged`, `_check_reflect_absence_engaged`) and entries in `_WITNESSES`, `_DISPATCHED_TYPE_KEY`, and `dispatch_engagement.py` span plumbing.
  - Recommendation: C — The spec's "verification of existing coverage" language was written before the watcher code was examined; the watcher explicitly documented that 59-7 would add witnesses. The implementation is correct. Spec ambiguity noted for traceability.

**Architectural observations (non-blocking):**
- The always-pass witnesses for `distinctive_detail_hint` and `reflect_absence` are architecturally correct — these are directive-only subsystems with no snapshot state to verify against. If they later grow snapshot dependencies, the witnesses should be updated.
- The `npc_agency` witness correctly mirrors the handler's own case-insensitive lookup pattern (both use `.lower()`), so the watcher and handler agree on what "NPC present" means.
- OTEL plumbing (`dispatch_engagement.py`) follows the existing pattern exactly — constants, SPAN_ROUTES registration, `_SUBSYSTEM_TO_SPAN_NAME` mapping, `__all__` export. Clean extension.

**Decision:** Proceed to verify phase.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/agents/dispatch_engagement_watcher.py` — added engagement witnesses for npc_agency (checks snapshot.npc_pool), distinctive_detail_hint (always-pass), reflect_absence (always-pass); added _DISPATCHED_TYPE_KEY entries; updated docstring
- `sidequest/agents/intent_router.py` — added subsystem dispatch vocabulary (npc_agency, distinctive_detail_hint, reflect_absence) to _SYSTEM_PROMPT
- `sidequest/agents/prompt_redaction.py` — replaced DORMANT docstring with live-path description
- `sidequest/agents/subsystems/__init__.py` — updated docstring to reflect all six subsystems live
- `sidequest/agents/subsystems/npc_agency.py` — replaced DORMANT docstring with live-path description
- `sidequest/agents/subsystems/distinctive_detail.py` — replaced DORMANT docstring with live-path description
- `sidequest/agents/subsystems/reflect_absence.py` — replaced DORMANT docstring with live-path description
- `sidequest/telemetry/spans/dispatch_engagement.py` — added span name constants, SPAN_ROUTES entries, and _SUBSYSTEM_TO_SPAN_NAME mappings for three new mismatch span types

**Tests:** 22/22 passing (GREEN) + 125 related tests pass (zero regressions)
**Branch:** feat/59-7-wire-localdm-subsystems (pushed)

**Handoff:** To Igor (TEA) for verify phase

## Tea Assessment

**Tests Required:** Yes
**Reason:** 5 ACs require mechanical verification — bank pipeline integration, redaction coverage, watcher engagement witnesses, router vocabulary, DORMANT marker removal.

**Test Files:**
- `tests/agents/subsystems/test_localdm_wiring.py` — 22 tests covering all 5 ACs + project rules

**Tests Written:** 22 tests covering 5 ACs
**Status:** RED (13 failing — ready for Dev)

### Breakdown

| AC | Tests | Status | What Fails |
|----|-------|--------|------------|
| AC1 (npc_agency bank + OTEL) | 1 | PASS | Already wired in bank registry |
| AC2 (distinctive_detail bank + OTEL) | 1 | PASS | Already wired in bank registry |
| AC3 (reflect_absence bank + OTEL) | 1 | PASS | Already wired in bank registry |
| AC4 (redaction) | 3 | PASS | Generic redaction already works |
| AC5 (watcher witnesses) | 8 | 3 PASS / 5 FAIL | `_WITNESSES` dict missing all three; `_DISPATCHED_TYPE_KEY` missing all three; npc_agency mismatch detection and multi-subsystem turn test fail |
| Router vocabulary | 3 | FAIL | `_SYSTEM_PROMPT` doesn't mention any of the three subsystem names |
| DORMANT markers | 4 | FAIL | 4 module docstrings still say DORMANT |

### What Dev Must Implement

1. **Watcher engagement witnesses** — add entries to `_WITNESSES` and `_DISPATCHED_TYPE_KEY` in `dispatch_engagement_watcher.py` for npc_agency (check snapshot.npc_pool for referenced NPC), distinctive_detail_hint (always-pass: directive-only), reflect_absence (always-pass: directive-only)
2. **Router vocabulary** — update `_SYSTEM_PROMPT` in `intent_router.py` to explicitly name npc_agency, distinctive_detail_hint, reflect_absence as valid dispatch subsystem types
3. **DORMANT markers** — remove "DORMANT" from module docstrings of npc_agency.py, distinctive_detail.py, reflect_absence.py, and prompt_redaction.py
4. **`__init__.py` docstring** — update the note about these three being "registered for symmetry" to reflect live status

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| "Every Test Suite Needs a Wiring Test" | `test_ac5_watcher_witnesses_include_*`, `test_intent_router_prompt_includes_*` | failing |
| "No Source-Text Wiring Tests" | All tests use runtime imports, dict membership, behavioral assertions | n/a (design rule) |
| "No Silent Fallbacks" | `test_ac5_npc_agency_dispatched_with_npc_not_in_pool_emits_mismatch` | failing |
| "OTEL Observability Principle" | `test_ac1_*`, `test_ac2_*`, `test_ac3_*` (span verification) | passing |

**Rules checked:** 4 of 14 applicable Python lang-review rules have test coverage (remainder are Dev-phase implementation rules, not test-design rules)
**Self-check:** 0 vacuous tests found — all 22 tests have meaningful assertions on specific values

**Handoff:** To Ponder Stibbons (Dev) for implementation

## Sm Assessment

Story 59-7 is ready for RED phase. Three dormant subsystem modules (npc_agency, distinctive_detail_hint, reflect_absence) in sidequest/agents/subsystems/ need wiring through the Intent Router's run_dispatch_bank, which is live post-59-4. Pure additive work — no retirement, no field changes. Five clear ACs covering handler engagement, visibility filtering, and OTEL lie-detector vocabulary. Server-only (sidequest-server), TDD workflow. Branch feat/59-7-wire-localdm-subsystems created off develop. No Jira. Handing off to Igor (TEA) for failing tests.