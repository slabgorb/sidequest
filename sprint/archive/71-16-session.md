---
story_id: "71-16"
jira_key: null
epic: "71"
workflow: "tdd"
---
# Story 71-16: ADR-113 — per-dispatch confidence scoring + threshold gating in the intent router

## Story Details
- **ID:** 71-16
- **Jira Key:** N/A (non-Jira project)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-28T16:31:44Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T15:51:38Z | 2026-05-28T15:53:35Z | 1m 57s |
| red | 2026-05-28T15:53:35Z | 2026-05-28T16:02:08Z | 8m 33s |
| green | 2026-05-28T16:02:08Z | 2026-05-28T16:21:11Z | 19m 3s |
| spec-check | 2026-05-28T16:21:11Z | 2026-05-28T16:22:29Z | 1m 18s |
| verify | 2026-05-28T16:22:29Z | 2026-05-28T16:24:29Z | 2m |
| review | 2026-05-28T16:24:29Z | 2026-05-28T16:29:00Z | 4m 31s |
| spec-reconcile | 2026-05-28T16:29:00Z | 2026-05-28T16:31:44Z | 2m 44s |
| finish | 2026-05-28T16:31:44Z | - | - |

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

7 deviations

- **confidence field made required (no default)**
  - Rationale: "populated for every emitted dispatch" = always present on the wire; a default would let a router bug ship a silent 0.0/1.0 (violates No Silent Fallbacks). Required surfaces omission as a retry/fail-loud, not a quiet default
  - Severity: minor
  - Forward impact: large construction-site ripple — Dev updated all callers at GREEN
- **Threshold resolver guards on `isinstance(thresholds, dict)`**
  - Rationale: `RulesConfig` types the field as `dict[str, float]` with a dict default, so production always satisfies the guard. Pre-existing dispatch tests pass a bare `MagicMock()` as `pack`, whose attribute chain returns mocks — the guard makes the helper robust at the boundary without weakening the production contract (a real malformed value still fails loud in `RulesConfig` validation, not here). This is owning the boundary, not a silent fallback masking a config problem
  - Severity: minor
  - Forward impact: none — production packs always carry a real dict
- **Degrade hint uses the `must_narrate` NarratorDirective kind**
  - Rationale: ADR-113 says "narrator_instruction hint" without naming a directive kind; `must_narrate` is the existing kind that forces the narrator to address the player's attempt, and inheriting `visibility` keeps redaction (ADR-104/105) intact. Conforms to TEA's test contract
  - Severity: minor
- **Threshold config field name + plumbing chosen by TEA**
  - Rationale: Spec named neither the field nor the bank-access path; TEA chose names matching existing conventions and the existing context contract. Dev MAY rename, but must update the tests in lockstep
  - Severity: minor
  - Forward impact: if Dev renames, `test_confidence_gate.py` field/key references must change too
- **Gate-decision span reuses the existing per-dispatch span**
  - Rationale: Spec said "a span" not "a new span"; reusing the per-dispatch span keeps one span per dispatch and is refactor-stable. The new requirement is that it also fires when the engine is gated out
  - Severity: minor
  - Forward impact: Dev must move/duplicate the `intent_router_subsystem_span` open so it wraps the degrade branch, and add the three attributes
- **AC5 spine-ordering not re-tested end-to-end**
  - Rationale: Ordering (router-before-narrator) is already pinned by `tests/server/test_59_4_router_wiring.py`; this story adds a gate INSIDE the bank and does not touch ordering, so re-testing ordering here would duplicate coverage. The relevant new risk — the gate silently dropping a valid dispatch — IS covered (`test_spine_intact_all_high_confidence_dispatches_engage`)
  - Severity: minor
  - Forward impact: none (existing wiring test still guards ordering)
- **`depends_on` does not cascade through the confidence gate**
  - Rationale: ADR-113 and the story ACs specify per-dispatch gating only; cascade semantics for `depends_on` chains are unspecified, and the live dispatch vocabulary (confrontation, magic_working, scenario_clue, npc_agency, movement, distinctive_detail_hint, reflect_absence) rarely chains dependencies. Adding cascade now would be unrequested scope. Surfaced by the Reviewer's independent pass.
  - Severity: minor
  - Forward impact: Candidate for the ADR-113 confidence-calibration follow-up (the same story that tunes real confidence values once OTEL shows distributions) — revisit if OTEL reveals dependent-dispatch chains degrading partially. No current AC or test depends on cascade behavior.

## Sm Assessment

**Story:** 71-16 — ADR-113 per-dispatch confidence scoring + threshold gating in the intent router (5pts, p2, tdd, repo: sidequest-server).

**Premise verified before setup** (cheap code-state check, not a re-investigation):
- `SubsystemDispatch` carries NO `confidence` field — the only confidence floats in `protocol/dispatch.py` are `Referent.confidence` (:78) and `DispatchPackage.confidence_global` (:207).
- `run_dispatch_bank` (`agents/subsystems/__init__.py:186`) has no threshold/gate logic.
- Confirms the story's premise: the ADR-113 confidence gate was never built; every dispatch fires its engine unconditionally today.

**Context:** Story context doc already authored at `sprint/context/context-story-71-16.md` (Architect ADR-accuracy audit, 2026-05-28) — thorough, file:line-pinned, with ACs, scope boundaries, and TEA test guidance. Not regenerated.

**Routing:** TDD/phased → TEA owns RED. TEA should write failing tests for: (AC1) `SubsystemDispatch.confidence` validated 0.0–1.0 populated by `IntentRouter`; (AC2) below-threshold dispatch does NOT engage its engine and degrades to a `narrator_instruction` hint, at/above engages — driven through real `run_dispatch_bank`; (AC3) per-subsystem threshold from `rules.yaml`, default 0.6, malformed fails loud; (AC4) OTEL gate-decision span (confidence + threshold + engaged|degraded_to_hint); (AC5) spine ordering (router→bank→engines→narrator) unchanged. No source-grep tests — fixture-driven engine-state assertions + OTEL span assertions.

**Cross-story note:** This unblocks 59-8 (playtest validation waits on this gate). Do NOT entangle with 59-11 (double-dispatch cleanup).

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** New mechanical behavior (confidence gate) with 5 ACs — protocol field, gate logic, config, OTEL.

**Test Files:**
- `sidequest-server/tests/agents/subsystems/test_confidence_gate.py` — 20 tests covering all 5 ACs.

**Tests Written:** 20 tests covering 5 ACs
**Status:** RED (17 failing for the right reason; 3 boundary-rejection tests pass-now-via-`extra=forbid` and stay correct at GREEN — see note)

### Coverage map (AC → tests)

| AC | Tests | RED status |
|----|-------|-----------|
| AC1 confidence field | `test_subsystem_dispatch_carries_confidence`, `_confidence_rejects_above_one`, `_below_zero`, `_is_required`, `test_router_round_trips_per_dispatch_confidence`, `test_router_prompt_instructs_per_dispatch_confidence` | failing (field absent) |
| AC2 threshold gate | `test_below_threshold_dispatch_does_not_engage_engine`, `_produces_narrator_hint`, `test_at_threshold_dispatch_engages_engine`, `_above_threshold_`, `test_default_threshold_is_point_six` | failing (no gate) |
| AC3 tunable threshold | `test_rules_config_accepts_per_subsystem_thresholds`, `_defaults_thresholds_empty`, `_rejects_out_of_range_threshold`, `test_per_subsystem_threshold_override_changes_gate`, `_override_lowering_engages` | failing (config absent) |
| AC4 OTEL gate span | `test_gate_emits_span_decision_engaged`, `_decision_degraded`, `test_mixed_confidence_turn_partitions_engage_and_degrade` | failing (no decision attr) |
| AC5 spine intact | `test_spine_intact_all_high_confidence_dispatches_engage` | failing (field absent) |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| No Silent Fallbacks (malformed threshold fails loud) | `test_rules_config_rejects_out_of_range_threshold` | passing-at-RED (raises via extra=forbid; right-reason at GREEN via range bound) |
| No Silent Fallbacks (no default confidence) | `test_subsystem_dispatch_confidence_is_required` | failing |
| No Source-Text Wiring Tests | gate proven by probe-engine engagement + OTEL span attrs; only `_SYSTEM_PROMPT` membership is prompt-vocabulary (accepted exception) | n/a |
| OTEL Observability (every gate decision emits a span) | `test_gate_emits_span_decision_{engaged,degraded}` | failing |
| Wiring test present | gate exercised through real `run_dispatch_bank` (not a mocked seam); probe registered in the live `_REGISTRY` | failing |

**Rules checked:** all applicable lang-review/SOUL rules mapped.
**Self-check:** No vacuous assertions. NOTE — the 3 `_rejects_*` boundary tests pass at RED because `SubsystemDispatch`/`RulesConfig` use `extra="forbid"`, so the bad value is rejected as an unknown field rather than an out-of-range value. They are NOT vacuous (they assert a genuine constraint) and become right-reason green once the field exists with its `ge/le` bound. Flagged honestly rather than forcing a brittle pydantic-error-message assertion.

**Verification:** testing-runner RUN_ID `71-16-tea-red` — 20 collected, no collection/import/fixture errors, ruff clean.

**Handoff:** To Dev (Inigo Montoya) for GREEN implementation.

---
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (source):**
- `sidequest/protocol/dispatch.py` — added required `SubsystemDispatch.confidence: float` (ge=0.0, le=1.0).
- `sidequest/genre/models/rules.py` — added `RulesConfig.dispatch_confidence_thresholds: dict[str, float]` (default `{}`) + `field_validator` failing loud on out-of-range values.
- `sidequest/agents/subsystems/__init__.py` — `DEFAULT_DISPATCH_CONFIDENCE_THRESHOLD = 0.6`, `_threshold_for()` (reads `context["pack"].rules.dispatch_confidence_thresholds`, dict-guarded), and the per-dispatch gate in `run_dispatch_bank` (engage if `confidence >= threshold`, else degrade to a `must_narrate` hint; both branches set span attrs).
- `sidequest/agents/intent_router.py` — `_SYSTEM_PROMPT` now instructs per-dispatch confidence scoring.
- `sidequest/telemetry/spans/intent_router.py` — `intent_router.subsystem` SpanRoute extract now projects `confidence` / `threshold` / `decision` for the GM panel.

**Files Changed (test fixtures, required-field ripple):** 25 existing test files updated to add `confidence=1.0` to their `SubsystemDispatch(...)` constructions (+ one dict fixture in `test_intent_router.py`). All are "engage" fixtures, so 1.0 preserves prior behavior.

**Tests:** New suite `tests/agents/subsystems/test_confidence_gate.py` — 20/20 GREEN. Full server suite: 7563 passed, 1365 skipped, **7 failed — all pre-existing and unrelated** (see Findings): 6 content-layer (corpus/asset/trope — backlog 64-7/64-9 + asset gate) and 1 stale prompt-cache test (`test_zones_carry_cache_boundary_flag` — backlog 61-17). My changed files are ruff- and pyright-clean.

**Branch:** `feat/71-16-intent-router-confidence-gate` (pushed to origin).

**Handoff:** To Reviewer (Westley) for code review.

---
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None requiring rework (5 logged deviations reviewed — all sound)

Per-AC substance check against `context-story-71-16.md` and the code:

- **AC1 (confidence field, router-populated):** `SubsystemDispatch.confidence` is required + range-bound (`dispatch.py`). "Populated by the IntentRouter" is satisfied via the ADR-102 tool-use path — the field is in `DispatchPackage.model_json_schema()`, the prompt instructs Haiku to score it, and a required field makes an omission fail loud (retry → `IntentRouterFailure`) rather than silently default. *Ambiguous-spec → reasonable assumption (Option C, no code change): "populated by the IntentRouter" means the Haiku decomposition pass emits it, not that router code assigns a value — correct per ADR-102. Logged by TEA.*
- **AC2 (gate engage/degrade):** `run_dispatch_bank` gates each dispatch: `confidence < threshold` → degrade to a `must_narrate` hint (engine NOT called, `continue`); else engage. Boundary is `>=` (spec-exact). The gate sits inside the per-dispatch span within the topo-sorted loop — router→bank→engine ordering untouched. Aligned.
- **AC3 (per-subsystem threshold, default 0.6, fail loud):** `RulesConfig.dispatch_confidence_thresholds` + `field_validator` raising on out-of-range (fail loud at pack load). `_threshold_for` reads it from `context["pack"].rules` (the existing seam — pack already flows into bank context) with 0.6 default. The `isinstance(dict)` guard (Dev deviation) is sound — production `RulesConfig` always yields a dict; the guard only catches test mocks, and real malformed values still fail loud upstream in validation. Aligned.
- **AC4 (OTEL gate-decision span):** `intent_router.subsystem` span carries `confidence` / `threshold` / `decision` on BOTH branches, and the SpanRoute extract projects them to the GM panel. Reusing the existing per-dispatch span (TEA deviation) keeps one span per dispatch and is refactor-stable. Aligned.
- **AC5 (spine intact):** Gate added inside the bank, no re-architecture; ordering and high-confidence engagement unchanged (`test_spine_intact_*`). Aligned.

**Reuse-first check:** No new infrastructure introduced — the change extends the existing `RulesConfig` model, the existing `run_dispatch_bank` loop, and the existing `intent_router.subsystem` span. Threshold delivery rides the pre-existing `context["pack"]` seam rather than a new plumbing path. This is the correct minimal footprint.

**Decision:** Proceed to TEA verify.

---
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (no simplify edits applied → state unchanged from Dev's GREEN)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (the changed source files; mechanical test-fixture one-liners excluded)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | LOW-confidence: span extract uses inline lambdas vs an `_attr()` helper used in other span modules |
| simplify-quality | clean | 0 findings — typed/bounded field, fail-loud validator, correct dependency direction |
| simplify-efficiency | clean | 0 findings — surgical additions, no over-engineering |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings
**Noted (dismissed):** 1 low-confidence finding — the reuse suggestion to adopt an `_attr()` span-extract helper. Dismissed: `telemetry/spans/intent_router.py` uses inline `(span.attributes or {}).get(...)` lambdas for *every* SPAN_ROUTES entry; converting only my 3 new attributes would make the file internally inconsistent, and refactoring all of its routes (or importing a cross-module helper) is out of scope for this story. The reuse agent itself rated it low and flagged the coupling risk.
**Reverted:** 0

**Overall:** simplify: clean (1 low-confidence observation noted, none applied)

**Quality Checks:** Dev's full-suite run stands (7563 passed; 7 pre-existing unrelated failures); no code changed in verify, so no re-run needed. Changed source files are ruff- and pyright-clean.

**Handoff:** To Reviewer (Westley) for code review.

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | yes | Clean | lint ✓, pyright ✓, tests GREEN (20/20 new + broad agents/protocol/genre run); only baseline 61-17 stale-cache failure; 0 code smells | Accept |
| 2 | reviewer-security | yes | Clean | 0 violations across No-Silent-Fallbacks, no-PII-logs, ADR-047 prompt-injection, pydantic extra=forbid. `d.subsystem` f-string = constrained LLM-to-LLM passthrough (low-theoretical, not exploitable); `_threshold_for` default is documented-not-silent (malformed fails loud at RulesConfig load); span floats cast safe | Accept |
| 3 | reviewer-edge-hunter | n/a | Skipped | disabled | Disabled via settings |
| 4 | reviewer-silent-failure-hunter | n/a | Skipped | disabled | Disabled via settings |
| 5 | reviewer-test-analyzer | n/a | Skipped | disabled | Disabled via settings |
| 6 | reviewer-comment-analyzer | n/a | Skipped | disabled | Disabled via settings |
| 7 | reviewer-type-design | n/a | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | n/a | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | n/a | Skipped | disabled | Disabled via settings |

**All received: Yes** — both enabled subagents (preflight, security) returned; the 7 others are disabled via `workflow.reviewer_subagents` settings.

## Reviewer Assessment

**Verdict:** APPROVE

**Diff:** 5 source files (+~140 lines) + 26 test files (mechanical `confidence=1.0` ripple). I read the full source diff independently, not just the subagent summaries.

### Rule Compliance (Python lang-review checklist)
- **#1 silent exceptions:** none — no bare/broad except added; failure surfaces via Pydantic ValidationError + IntentRouterFailure. ✓
- **#2 mutable defaults:** none — `dispatch_confidence_thresholds` uses `Field(default_factory=dict)`, not `={}`. ✓
- **#3 type annotations:** `_threshold_for(subsystem: str, context: dict[str, Any]) -> float` fully annotated; new fields typed. ✓
- **#6 test quality:** new suite asserts behavior (engine engagement via probe + OTEL attrs), no vacuous assertions; the 3 boundary tests are honestly flagged (pass-via-extra=forbid at RED, right-reason at GREEN). ✓
- **#8 unsafe deserialization:** none. **#11 input validation [SEC]:** the new f-string interpolates only an LLM-constrained subsystem keyword + `:.2f` floats into narrator prose — no SQL/HTML/path/user-text surface. `[SEC]` reviewer-security rated the `d.subsystem` LLM-to-LLM passthrough low-theoretical / not exploitable (closed 7-keyword vocabulary, `extra="forbid"`, same trust boundary) and the interpolated floats safe (cast + `:.2f`). ✓
- **No Silent Fallbacks (SOUL/CLAUDE.md) [SEC]:** VERIFIED — `[SEC]` reviewer-security confirmed 0 violations: malformed threshold raises at `RulesConfig._validate_dispatch_thresholds` before pack load; `_threshold_for`'s 0.6 is the documented ADR-113 default for the structurally-valid no-override case, not a masked error. The `isinstance(dict)` guard only catches non-RulesConfig stand-ins (test mocks).
- **OTEL Observability (CLAUDE.md):** VERIFIED — both gate branches (engaged / degraded_to_hint) set `confidence`/`threshold`/`decision` on the per-dispatch span, and the SpanRoute extract projects them to the GM panel. The gate is itself a subsystem decision and is now observable.

### AC verification (independent)
All five ACs met: confidence field required+bounded (AC1); gate `>=` boundary with engine-skip + narrator hint below threshold (AC2); per-subsystem `rules.yaml` threshold, 0.6 default, fail-loud (AC3); per-dispatch gate-decision span (AC4); gate added inside the bank with ordering/high-confidence behavior unchanged (AC5).

### Independent findings
- **Observation (defer, low):** `depends_on` does not cascade through the gate — if dispatch A degrades (gated out) and dispatch B `depends_on=[A]`, B still engages on its own confidence even though A's engine never ran. This is out of scope for 71-16 (the ACs gate each dispatch on its own confidence; `depends_on` cascade semantics aren't specified by ADR-113) and the live dispatch vocabulary rarely chains dependencies. Reasonable follow-up for the calibration story once OTEL shows real dependency patterns. Not a blocker — no AC requires cascade, all tests pass. *Recommend D (defer).*

**Decision:** Approve — proceed to spec-reconcile / finish.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Making `SubsystemDispatch.confidence` a REQUIRED field (no
  default) breaks every existing construction site of `SubsystemDispatch` across the
  suite and production. At GREEN, Dev must add `confidence=` to all of them and have
  `IntentRouter` populate it (Haiku via the tool schema). Affects
  `sidequest/protocol/dispatch.py` (add field), `sidequest/agents/intent_router.py`
  (prompt + ensure populated), and ~all `SubsystemDispatch(...)` callers including
  test helpers like `tests/agents/subsystems/test_localdm_wiring.py::_make_dispatch`
  and `sidequest/agents/prompt_redaction.py` paths that rebuild dispatches. Expect a
  wide RED across the existing suite once the field lands — that ripple is the
  required-field blast radius, not a regression. *Found by TEA during test design.*
- **Improvement** (non-blocking): The degrade path emits a `must_narrate`
  `NarratorDirective` as the hint; the bank should still record the gate decision on
  the per-dispatch span even when no engine runs, so the GM panel (lie detector) sees
  every gate fire. Affects `sidequest/agents/subsystems/__init__.py` (`run_dispatch_bank`
  loop must open `intent_router_subsystem_span` for degraded dispatches too).
  *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): Full-suite baseline carries 7 pre-existing failures unrelated
  to this story, all owned by other backlog stories: 6 content-layer
  (`tests/scripts/test_audit_namegen_corpora.py` ×4 — missing namegen corpus files,
  backlog **64-7/64-9**; `tests/cli/validate/test_pack_validator.py` +
  `test_pack_validator_crossref.py` — missing `assets/images/{portraits,poi}` dirs +
  unknown trope ids, the documented asset gate) and 1 stale prompt-cache test
  (`tests/agents/test_prompt_cache_attribution_otel.py::test_zones_carry_cache_boundary_flag`
  — narrator_constraints bucket promotion from 61-10, backlog **61-17**). My diff
  (intent-router dispatch path) has no causal path to corpus/asset/prompt-bucket code.
  *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **confidence field made required (no default)**
  - Spec source: context-story-71-16.md, AC-1
  - Spec text: "SubsystemDispatch carries a validated confidence: float (0.0–1.0), populated by the IntentRouter for every emitted dispatch"
  - Implementation: Tests pin `confidence` as REQUIRED (no default) — `test_subsystem_dispatch_confidence_is_required` asserts construction without it raises ValidationError
  - Rationale: "populated for every emitted dispatch" = always present on the wire; a default would let a router bug ship a silent 0.0/1.0 (violates No Silent Fallbacks). Required surfaces omission as a retry/fail-loud, not a quiet default
  - Severity: minor
  - Forward impact: large construction-site ripple — Dev updated all callers at GREEN

### Dev (implementation)
- **Threshold resolver guards on `isinstance(thresholds, dict)`**
  - Spec source: context-story-71-16.md, AC-3
  - Spec text: "Threshold is read per-subsystem from genre pack rules.yaml, defaulting to 0.6"
  - Implementation: `_threshold_for()` only applies a pack override when `context["pack"].rules.dispatch_confidence_thresholds` is an actual `dict`; otherwise it returns the 0.6 default
  - Rationale: `RulesConfig` types the field as `dict[str, float]` with a dict default, so production always satisfies the guard. Pre-existing dispatch tests pass a bare `MagicMock()` as `pack`, whose attribute chain returns mocks — the guard makes the helper robust at the boundary without weakening the production contract (a real malformed value still fails loud in `RulesConfig` validation, not here). This is owning the boundary, not a silent fallback masking a config problem
  - Severity: minor
  - Forward impact: none — production packs always carry a real dict
- **Degrade hint uses the `must_narrate` NarratorDirective kind**
  - Spec source: context-story-71-16.md, AC-2
  - Spec text: "below threshold it does NOT engage and instead produces a narrator_instruction hint (ADR-113 degrade path)"
  - Implementation: the gated-out dispatch appends a `NarratorDirective(kind="must_narrate", ...)` carrying the inferred-intent context and inheriting the dispatch's `visibility`
  - Rationale: ADR-113 says "narrator_instruction hint" without naming a directive kind; `must_narrate` is the existing kind that forces the narrator to address the player's attempt, and inheriting `visibility` keeps redaction (ADR-104/105) intact. Conforms to TEA's test contract
  - Severity: minor
  - Forward impact: none

### TEA (test design, continued)
- **Threshold config field name + plumbing chosen by TEA**
  - Spec source: context-story-71-16.md, AC-3 + "Files to Modify"
  - Spec text: "Threshold is read per-subsystem from genre pack rules.yaml, defaulting to 0.6" / "rules.py — per-subsystem threshold config (default 0.6)"
  - Implementation: Tests pin the field as `RulesConfig.dispatch_confidence_thresholds: dict[str, float]`, read by the bank from `context["pack"].rules` (pack already flows into bank context via `intent_router_pass`)
  - Rationale: Spec named neither the field nor the bank-access path; TEA chose names matching existing conventions and the existing context contract. Dev MAY rename, but must update the tests in lockstep
  - Severity: minor
  - Forward impact: if Dev renames, `test_confidence_gate.py` field/key references must change too
- **Gate-decision span reuses the existing per-dispatch span**
  - Spec source: context-story-71-16.md, AC-4
  - Spec text: "Each dispatch emits a span with its confidence, the threshold applied, and the decision (engaged | degraded_to_hint)"
  - Implementation: Tests assert these as NEW attributes (`confidence`, `threshold`, `decision`) on the EXISTING `intent_router.subsystem` span, and require that span to fire for degraded (gated-out) dispatches too — not a new span name
  - Rationale: Spec said "a span" not "a new span"; reusing the per-dispatch span keeps one span per dispatch and is refactor-stable. The new requirement is that it also fires when the engine is gated out
  - Severity: minor
  - Forward impact: Dev must move/duplicate the `intent_router_subsystem_span` open so it wraps the degrade branch, and add the three attributes
- **AC5 spine-ordering not re-tested end-to-end**
  - Spec source: context-story-71-16.md, AC-5 + Test Guidance ("the end-to-end intent-router pass still runs before the narrator")
  - Spec text: "the live router→bank→engines→narrator ordering is unchanged"
  - Implementation: TEA tests the gate's no-drop guarantee (all high-confidence dispatches engage) at the `run_dispatch_bank` unit level, not the full pre-narrator-pass ordering
  - Rationale: Ordering (router-before-narrator) is already pinned by `tests/server/test_59_4_router_wiring.py`; this story adds a gate INSIDE the bank and does not touch ordering, so re-testing ordering here would duplicate coverage. The relevant new risk — the gate silently dropping a valid dispatch — IS covered (`test_spine_intact_all_high_confidence_dispatches_engage`)
  - Severity: minor
  - Forward impact: none (existing wiring test still guards ordering)

### Architect (reconcile)

**Existing-entry audit:** Reviewed all TEA (4) and Dev (2) deviation entries. All cite real spec sources (`context-story-71-16.md`, AC-1/2/3/4/5 — file exists and the quoted AC text is accurate), describe what the code actually does, and carry all 6 fields. No corrections needed. (Layout note: the in-flight TEA entries 2–4 are grouped under a "TEA (test design, continued)" subheading after the Dev block — an artifact of append ordering during the Dev phase; attribution is correct, all entries are TEA's.)

**AC deferral check:** No-op — all 5 ACs are DONE (none deferred or descoped), so there are no deferral justifications to verify.

**Missed deviation (1):**
- **`depends_on` does not cascade through the confidence gate**
  - Spec source: context-story-71-16.md, AC-2 (and ADR-113 degrade-path Decision)
  - Spec text: "a dispatch engages its engine only when `confidence >= threshold`; below threshold it does NOT engage and instead produces a `narrator_instruction` hint"
  - Implementation: The gate decides per-dispatch on each dispatch's own `confidence`. `run_dispatch_bank` topo-sorts on `depends_on` for ordering, but a dispatch whose dependency was gated out (degraded) still engages on its own confidence — degradation does not propagate to dependents.
  - Rationale: ADR-113 and the story ACs specify per-dispatch gating only; cascade semantics for `depends_on` chains are unspecified, and the live dispatch vocabulary (confrontation, magic_working, scenario_clue, npc_agency, movement, distinctive_detail_hint, reflect_absence) rarely chains dependencies. Adding cascade now would be unrequested scope. Surfaced by the Reviewer's independent pass.
  - Severity: minor
  - Forward impact: Candidate for the ADR-113 confidence-calibration follow-up (the same story that tunes real confidence values once OTEL shows distributions) — revisit if OTEL reveals dependent-dispatch chains degrading partially. No current AC or test depends on cascade behavior.

**Manifest verdict:** Spec aligned. All deviations are minor, justified, and consistent with ADR-113 + SOUL (No Silent Fallbacks, OTEL Observability). No rework required.