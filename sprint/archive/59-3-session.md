---
story_id: "59-3"
jira_key: null
epic: "59"
workflow: "tdd"
---

# Story 59-3: Repurpose confrontation_intent_validator as router-vs-engine lie-detector watcher

## Story Details

- **ID:** 59-3
- **Epic:** 59 — Intent Router — Mechanical-Engagement Spine
- **Jira Key:** None (SideQuest is personal — no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server
- **Points:** 3
- **Priority:** p1

## Story Summary

Change the trigger of `confrontation_intent_validator` from "narrator action_rewrite vs engaged encounter mismatch" to "router-dispatched subsystem vs engine-engaged-on-snapshot mismatch". Broaden semantics across the full dispatch vocabulary (confrontation, magic_working, scenario_clue). Watcher is a pure function `(package, post_turn_snapshot) → optional[mismatch_span]` running post-turn. Replaces both the deleted `_CONFRONTATION_TRIGGER_PATTERNS` keyword scanner (93c7659) and the 59-1-shipped `confrontation_intent_mismatch_reprompt_failed_span` self-report-reprompt flow.

## Acceptance Criteria

1. Router dispatched `confrontation:negotiation` + snapshot has no encounter → mismatch span fires (existing `confrontation_unengaged_turn_span` reused).
2. Router dispatched `confrontation:negotiation` + snapshot has matching encounter → no span (no false positive).
3. Router dispatched nothing + snapshot has no encounter → no span (no false positive on quiet turns).
4. Watcher covers `magic_working` and `scenario_clue` dispatch mismatches (extends beyond confrontation to honor the spine's full vocabulary). NEW spans: `dispatch_engagement.{subsystem}.mismatch`.
5. **Wiring test:** drive a synthetic router-dispatched-not-engaged turn through the real watcher hook (not a unit-test mock); assert span emission.
6. The 59-1-shipped `confrontation_intent_mismatch_reprompt_failed_span` self-report-reprompt path is REMOVED (replaced by the watcher; one mechanism).

## Dependencies

- **Depends on:** 59-2 (DispatchPackage producer must exist)
- **Blocks:** 59-4 (live cutover wants the watcher catching mismatches from day one)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-24T13:45:02Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | 2026-05-24T12:55:13Z | 12h 55m |
| red | 2026-05-24T12:55:13Z | 2026-05-24T13:13:17Z | 18m 4s |
| green | 2026-05-24T13:13:17Z | 2026-05-24T13:27:55Z | 14m 38s |
| spec-check | 2026-05-24T13:27:55Z | 2026-05-24T13:30:44Z | 2m 49s |
| verify | 2026-05-24T13:30:44Z | 2026-05-24T13:36:09Z | 5m 25s |
| review | 2026-05-24T13:36:09Z | 2026-05-24T13:43:02Z | 6m 53s |
| spec-reconcile | 2026-05-24T13:43:02Z | 2026-05-24T13:45:02Z | 2m |
| finish | 2026-05-24T13:45:02Z | - | - |

## Delivery Findings

<!-- Append-only per ADR-0031. Never edit or remove entries from prior agents. -->

### Dev (implementation)

- **Improvement** (non-blocking): Pre-existing circular import between `sidequest/server/session_handler.py` and `sidequest/server/websocket_session_handler.py`. `session_handler.py:640` does a late re-export `from sidequest.server.websocket_session_handler import WebSocketSessionHandler, _populate_opening_directive_on_chargen_complete` that fires DURING `websocket_session_handler`'s own import when something else triggers loading `websocket_session_handler` directly. Discovered while writing AC5 wiring test; worked around by routing imports through `session_handler` (the public surface). The fix is likely to delete the late re-export — most callers should import via `session_handler` anyway. Affects `sidequest/server/session_handler.py:640`. *Found by Dev during implementation.*

- **Improvement** (non-blocking): The 2 pre-existing failures in `tests/agents/test_61_9_sdk_commitment.py::TestNarratorBackendGate::test_*_purpose_with_sdk_backend_returns_tooling_client` are environmental (no monkeypatch for `ANTHROPIC_API_KEY`). They're not blocking 59-3 but they DO break local `just check-all` runs and CI runs that don't inject the env var. Fix: add `monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-only")` to each test or patch `AsyncAnthropic` at the SDK boundary as 59-2's `test_intent_router_constructible_with_sdk_haiku_adapter` does. Affects `tests/agents/test_61_9_sdk_commitment.py`. *Found by Dev during implementation.*

### TEA (test design)

- **Gap** (non-blocking): The `sidequest/agents/intent_router.py` producer (shipped by 59-2) emits dispatches but no module today reads `DispatchPackage.per_player[*].dispatch` POST-engine. The watcher is the first consumer that requires both `(package, post_turn_snapshot)` in scope; the natural seam is `_execute_narration_turn` after `_apply_narration_result_to_snapshot`. The story context Assumption 2 flagged this as "create the seam if absent" — Dev will own the seam during GREEN. Affects `sidequest/server/websocket_session_handler.py` (~line 3425). *Found by TEA during test design.*

- **Question** (non-blocking): Engagement-witness pinning was deferred to RED by Architect (story context Assumption 4). TEA pinned witnesses against the real engines' mutation surface: confrontation → `snapshot.encounter.encounter_type`; magic_working → `WorkingRecord` in `snapshot.magic_state.working_log` matched on `actor`; scenario_clue → `params["fact_id"] in snapshot.scenario_state.discovered_clues`. Dev should confirm these witnesses survive the 59-4/5/6 handler implementations — if a handler chooses a different surface (e.g. a new `last_turn_engaged_dispatches` set on the snapshot), the watcher's witness functions and the tests update together in that story. Affects test fixtures + watcher implementation. *Found by TEA during test design.*

### TEA (test verification)

- **Improvement** (non-blocking): `_fresh_tracer_and_exporter()` OTEL test helper is duplicated across `tests/telemetry/test_confrontation_intent_spans.py:14` and `tests/agents/test_dispatch_engagement_watcher.py:74` AND inlined (per simplify-reuse) in 6+ other test files across the suite that touch OTEL exporters. A focused refactor would move it to `tests/_helpers/otel.py` and sweep all 40+ span test files in lockstep. Out of 59-3's scope (the per-PR duplication is only 2 sites, below the codebase's extraction threshold), but worth a dedicated cleanup story. Affects `tests/**/test_*spans*.py` + other OTEL-using test files. *Found by TEA during test verification.*

- **Improvement** (non-blocking): The fixture-builder pattern (`_make_dispatch`, `_package_with`, `_snapshot`) in `tests/agents/test_dispatch_engagement_watcher.py:74-190` mirrors patterns used elsewhere for DispatchPackage construction (e.g., `tests/agents/test_prompt_redaction.py`, `tests/agents/test_lethality_arbiter.py`, `tests/agents/test_orchestrator.py`). A shared `tests/_helpers/dispatch_fixtures.py` would help if the dispatch-test surface grows in 59-4/5/6/7. Currently only 1 file in 59-3 uses these fixtures, so extraction would be speculative. *Found by TEA during test verification.*

## Design Deviations

<!-- One subsection per agent. Append-only. -->

### TEA (test design)

- **Span name family — chose new `dispatch_engagement.*` over AC1's "reuse confrontation_unengaged_turn_span" language**
  - Spec source: context-story-59-3.md → AC Context → AC1
  - Spec text: "Router dispatched `confrontation:negotiation` + snapshot has no encounter → mismatch span fires (existing `confrontation_unengaged_turn_span` reused)."
  - Implementation: Tests pin the span name to `dispatch_engagement.confrontation.mismatch` (the new family AC4 introduces), NOT the existing `confrontation.unengaged_turn` name. The legacy 59-1 span is left untouched (the story context explicitly says "Do not touch `validate()` or its span").
  - Rationale: Story context AC1 commentary already flagged this discrepancy: "AC1 says 'existing `confrontation_unengaged_turn_span` reused' but the watcher's new span family is `dispatch_engagement.{subsystem}.mismatch`... Recommended interpretation: AC text predates final naming. Use the new family name." TEA followed Architect's recommended interpretation. The new family is necessary for AC4 (magic_working / scenario_clue spans) anyway — splitting confrontation onto the old name would break naming symmetry across the three subsystems.
  - Severity: minor
  - Forward impact: 59-1's `confrontation.unengaged_turn` span (intent-empty narrator turn) remains live and unchanged — it covers a DIFFERENT failure mode (narrator emitted no intent at all) and is orthogonal to the watcher.

- **Watcher module location — chose split file (`sidequest/agents/dispatch_engagement_watcher.py`) over in-file extension of `confrontation_intent_validator.py`**
  - Spec source: context-story-59-3.md → Technical Guardrails → "Architecture — where the watcher lives"
  - Spec text: "(location: keep within `sidequest/agents/confrontation_intent_validator.py` or split out — Dev/Architect call during RED; renaming the file is fine if the rename is mechanical)."
  - Implementation: Tests import from `sidequest.agents.dispatch_engagement_watcher` (new module).
  - Rationale: Architect explicitly delegated this choice to RED. TEA picked split-out because the watcher (a) operates across the full dispatch vocabulary, not just confrontation; (b) consumes `DispatchPackage` + multiple game-state surfaces; (c) the existing validator file's `validate()` / `tokenize()` machinery stays load-bearing for the 59-1 sidecar path until 59-4 retires it — co-locating two unrelated mechanisms in one file would make the 59-4 retirement messier.
  - Severity: minor
  - Forward impact: 59-4 cleanup is simpler (delete `validate()` / `tokenize()` / `ValidationResult` from `confrontation_intent_validator.py` without disturbing the watcher).

- **Added `package=None` no-op case (`test_watcher_no_op_when_package_is_none`)**
  - Spec source: context-story-59-3.md → Assumptions → #1 + #2
  - Spec text: "**59-2 has shipped** the `IntentRouter` class..." + "the post-turn pipeline has a natural wiring site... If no such site exists today, that is itself a finding..."
  - Implementation: Added a unit test asserting the watcher safely no-ops when `package=None`.
  - Rationale: Between 59-3 ship and 59-4 ship, the live `turn_context.dispatch_package` is None (epic context Background documents the five orchestrator consumer sites guarded `if … is not None`). The post-turn watcher hook will fire every turn from 59-3 forward; without an explicit None guard the handler would crash on every live turn. The spec doesn't call this out as an AC but the story context's Assumption 2 implies "the wiring must be safe at all times" — TEA encoded this as a test.
  - Severity: trivial
  - Forward impact: none (it's a defensive null guard the watcher needs anyway).

- **Broadened AC6 scope to include `RepromptRequest` + `NarrationApplyOutcome.reprompt_request` consumer cleanup**
  - Spec source: context-story-59-3.md → Scope Boundaries → "This story REMOVES"
  - Spec text: Lists 4 things to remove (the failed-span constant + manager + SPAN_ROUTES entry, the reprompt loop in `_execute_narration_turn`, callers of the failed span, and the dead `_CONFRONTATION_TRIGGER_PATTERNS` scanner if still present). Does NOT explicitly list `RepromptRequest` or the `reprompt_request` field.
  - Implementation: Added two reflection tests asserting `NarrationApplyOutcome.reprompt_request` field is removed and the `RepromptRequest` dataclass is removed.
  - Rationale: Per CLAUDE.md "No Stubbing" / "Dead code is worse than no code" and the story context's "one mechanism per problem" principle — once the reprompt loop is removed, `RepromptRequest` has zero non-test callers and `NarrationApplyOutcome.reprompt_request` is permanently None. Leaving them as dead types would invite a future PR to silently re-introduce the deprecated reprompt-fallback path. TEA broadened the cleanup to match.
  - Severity: minor
  - Forward impact: existing reprompt-loop tests (`tests/agents/test_orchestrator_reprompt_loop.py`, parts of `test_59_1_confrontation_engagement.py`, `test_dust_and_lead_horse_replay.py`, `test_narration_apply_intent_dispatch.py`) need updating or deletion during GREEN. Dev should expect ~4 test files in the blast radius.

- **Pinned dispatch param keys (`type`, `actor`, `fact_id`) as the watcher's witness lookup**
  - Spec source: context-story-59-3.md → AC Context → AC4 + Technical Guardrails
  - Spec text: "Engagement witness ambiguity: the precise snapshot field for 'magic engaged' and 'clue advanced' is not 100% pinned from outside the engine. Dev/TEA should during RED... pick the field that the engine sets and use it as the witness."
  - Implementation: Tests assume `params["type"]` (confrontation), `params["actor"]` (magic_working), `params["fact_id"]` (scenario_clue). The watcher reads these keys; missing keys raise loudly (fail-loud discipline).
  - Rationale: Picked the simplest natural keys that match the underlying engine signatures (`instantiate_encounter_from_trigger(encounter_type=...)`, `apply_magic_working` reads `working.actor`, `consume_clue_footnotes` reads `fact_id`). If 59-4/5/6's handlers expose different params (e.g. `params["encounter_type"]`), Dev updates both the watcher's key reads and these tests in lockstep — the param-key contract is a single point of change, not duplicated logic.
  - Severity: minor
  - Forward impact: 59-4/5/6 confrontation/magic/clue dispatch handlers must accept these param keys.

## Notes & Context

See `/Users/slabgorb/Projects/oq-2/sprint/context/context-epic-59.md` for the full epic architectural reframe and ADR-113 ratification.

Key context:
- This story depends on 59-2 (IntentRouter skeleton) being completed first
- This watcher replaces two prior mechanisms: the deleted `_CONFRONTATION_TRIGGER_PATTERNS` keyword scanner and the 59-1-shipped self-report-reprompt flow
- The watcher observes post-turn snapshots and dispatch packages to detect mismatches — it's a pure lie-detector with no fallback paths
- Implementation reuses existing span infrastructure from `telemetry/spans/confrontation_intent.py` and extends it across the dispatch vocabulary

## SM Assessment

**Setup gate:** All checks pass.

- Session file present at `.session/59-3-session.md` with all required fields (story_id, epic, workflow, repos, points, priority, ACs, dependencies).
- Feature branch `feat/59-3-router-vs-engine-watcher` created in `sidequest-server` off `develop` (the github-flow base for that repo per memory `feedback_gitflow_content`).
- Dependency `59-2` is `done` — IntentRouter shipped, `DispatchPackage.degraded` removed, archived session at `sprint/archive/59-2-session.md` confirms producer is alive. No blocker.
- Story context written at `sprint/context/context-story-59-3.md` (17.9KB) by Architect (Leonard of Quirm). Schema-valid (`pf validate context-story 59-3` → OK). Frontmatter `parent: context-epic-59.md` correct.
- Epic context present at `sprint/context/context-epic-59.md` — the Houlihan 2026-05-23 reframe.
- Jira: explicitly skipped — SideQuest is a personal project (`feedback_playtest_no_jira`). `jira_key: null` is correct, not an oversight.
- Workflow `tdd`: phased, next phase `red`, next agent `tea` (Igor).
- Context discipline: Architect already did the technical guardrail / scope-boundary / AC-context elaboration in the story context doc, including the engagement-witness ambiguity flag for AC4 (magic_working / scenario_clue snapshot fields) — that flag is the most important pass-through to TEA. If Igor can't pin those witnesses from the existing code during RED, that's a Design Deviation moment, not a "guess and move on".
- No blocking PRs anywhere in the sprint (story 59-3 is the next-up after 59-2's merge).

**Decision:** Hand off to TEA (Igor) for the RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New mechanism (router-vs-engine lie-detector watcher), retires the 59-1 reprompt path, broadens the watcher's vocabulary across three dispatch subsystems — definitively in TDD scope. No chore-bypass eligibility.

**Test Files:**
- `sidequest-server/tests/agents/test_dispatch_engagement_watcher.py` — 24 tests against the pure-function watcher (`detect_dispatch_engagement_mismatch`) and its OTEL-emitting wrapper (`run_dispatch_engagement_watcher`) including all AC1-5 coverage, fail-loud discipline, pure-function discipline, and three wiring tripwires.
- `sidequest-server/tests/telemetry/test_dispatch_engagement_spans.py` — 10 tests against the new `dispatch_engagement.{subsystem}.mismatch` span family registration AND reflection-based retirement assertions for the 59-1 reprompt-failed span family + consumer cleanup (AC6).

**Tests Written:** 34 tests covering 6 ACs + project-rule enforcement
**Status:** RED (all 34 failing — verified via testing-runner subagent at run id `59-3-tea-red`)

### Rule Coverage

| Rule (source) | Test(s) | Status |
|---------------|---------|--------|
| CLAUDE.md "Every Test Suite Needs a Wiring Test" | `test_watcher_module_exports_public_api`, `test_watcher_wired_into_session_handler`, `test_watcher_fixture_round_trip_through_real_pipeline` | failing |
| CLAUDE.md "No Source-Text Wiring Tests" (use reflection / OTEL / fixture-driven) | `test_watcher_wired_into_session_handler` uses `module.__dict__` reflection; `test_reprompt_request_field_removed_from_narration_apply_outcome` uses `dataclasses.fields()` reflection (the sanctioned tripwire pattern) | failing |
| CLAUDE.md "No Silent Fallbacks" + memory `feedback_no_fallbacks_hard` | `test_watcher_raises_when_confrontation_dispatch_lacks_type_param`, `test_watcher_raises_when_magic_working_dispatch_lacks_actor_param`, `test_watcher_raises_when_scenario_clue_dispatch_lacks_fact_id_param` | failing |
| CLAUDE.md "No Stubbing" / "Dead code is worse than no code" | `test_reprompt_request_class_removed` (no dead `RepromptRequest`), `test_reprompt_request_field_removed_from_narration_apply_outcome` (no dead `reprompt_request` field) | failing |
| Memory `feedback_one_mechanism_per_problem` | All 5 AC6 retirement tests (the watcher replaces the reprompt loop — old mechanism must die when new one ships) | failing |
| CLAUDE.md OTEL Observability Principle | Every mismatch test asserts a span fires; every happy-path test asserts NO span fires (no false positives) | failing |
| SOUL "Cost Scales with Drama" | `test_quiet_turn_no_dispatch_no_engagement_emits_no_span` — quiet turns produce zero spans, zero compute waste | failing |
| Memory `feedback_no_burying_bombs` | Watcher raises on malformed params (does not null-guard upstream producer bugs) — see fail-loud tests above | failing |
| 3-subsystem coverage (story scope) | `test_*_emit_mismatch_span` × confrontation/magic_working/scenario_clue × {no-state, wrong-state, multi-mismatch, partial-engagement, cross-player} | failing |

**Rules checked:** All applicable Python language-review checks and SideQuest-server CLAUDE.md rules verified to have test coverage. The lang-review file `.pennyfarthing/gates/lang-review/python.md` was consulted; the project does not have rules-style enforcement files at `.claude/rules/` so SOUL + CLAUDE.md served as the substitute rule rubric.

**Self-check:** All 34 tests have meaningful assertions. Each `assert` either checks exact value equality, list length + name, or `is_not`/`not in` for absence — no `assert True`, no `let _ =`, no `is_none()` on always-None. The three wiring tripwires (module export, handler module-dict membership, fixture round-trip) cover the "is this thing reachable" question from three different angles to survive refactoring.

### RED Verification

Ran the new tests directly + via `testing-runner` subagent (RUN_ID: `59-3-tea-red`). Result: **34 failed, 0 passed, 0 skipped**, all with the expected RED shape:

- 29 failures: `ModuleNotFoundError: No module named 'sidequest.agents.dispatch_engagement_watcher'` (module under test doesn't exist yet)
- 3 failures: `ImportError: cannot import name 'dispatch_engagement' from 'sidequest.telemetry.spans'` (new span family module doesn't exist yet)
- 2 failures: `ImportError` / `ModuleNotFoundError` propagating through wiring tests (same root cause)
- 6 failures: retirement reflection asserting absence of still-present 59-1 reprompt symbols (correct RED for retirement assertions — they pass once Dev deletes the symbols in GREEN)

Pre-existing tests in adjacent files (`tests/telemetry/test_confrontation_intent_spans.py`, `tests/agents/test_confrontation_intent_validator.py`) still pass cleanly. No collateral damage from the new tests.

**Handoff:** To Dev (Ponder Stibbons) for GREEN implementation.

### Implementation Pointers for Dev

1. **Create `sidequest/agents/dispatch_engagement_watcher.py`** with:
   - `DispatchMismatch` record (dataclass or pydantic BaseModel — Dev's call; tests probe both `getattr(m, "subsystem")` and `m.get("subsystem")` shapes so either works) carrying at minimum `subsystem: str`.
   - `detect_dispatch_engagement_mismatch(*, package: DispatchPackage | None, snapshot: GameSnapshot) -> list[DispatchMismatch]` — pure function. Iterates `package.per_player[*].dispatch` AND `package.cross_player[*].dispatch`. For each dispatch, dispatches on `subsystem` and checks the engagement witness on the snapshot. Returns empty list when `package is None`.
   - `run_dispatch_engagement_watcher(*, package: DispatchPackage | None, snapshot: GameSnapshot, tracer: opentelemetry.trace.Tracer | None = None) -> None` — thin wrapper that calls the pure function and emits one OTEL span per mismatch.

2. **Create `sidequest/telemetry/spans/dispatch_engagement.py`** with:
   - Three span name constants: `SPAN_DISPATCH_ENGAGEMENT_CONFRONTATION_MISMATCH = "dispatch_engagement.confrontation.mismatch"` (and analogous for magic_working / scenario_clue).
   - `SPAN_ROUTES` entries with `extract` functions that surface `subsystem` (and ideally `idempotency_key`, `dispatched_type`) as attributes.
   - Re-exports from the spans package root.

3. **Wire into `_execute_narration_turn`** (`sidequest/server/websocket_session_handler.py` ~line 3425, right after `_apply_narration_result_to_snapshot` returns and before the `encounter_resolved_this_turn` check). Pass `turn_context.dispatch_package` and the post-apply `snapshot`. The wiring tripwire asserts `module.__dict__` contains either the function or the module — either import shape passes.

4. **Retire AC6 symbols** (one PR, the whole removal — no parallel period per memory `feedback_no_fallbacks_hard`):
   - `sidequest/telemetry/spans/confrontation_intent.py`: delete `SPAN_CONFRONTATION_INTENT_MISMATCH_REPROMPT_FAILED`, `confrontation_intent_mismatch_reprompt_failed_span`, and the `SPAN_ROUTES` registration block.
   - Spans package root: remove the re-exports.
   - `sidequest/server/websocket_session_handler.py`: delete the entire reprompt-loop block at ~lines 3354-3424 (the `if applied_outcome.reprompt_request is not None:` block).
   - `sidequest/server/narration_apply.py`: delete the `RepromptRequest` dataclass + the `reprompt_request` field on `NarrationApplyOutcome` + the code path that constructs `RepromptRequest` (the `elif _effective_severity == "reprompt":` branch in `_apply_narration_result_to_snapshot`). Be aware that `already_reprompted` parameter on `_apply_narration_result_to_snapshot` and related plumbing is also part of the reprompt machinery — remove the dead parameter trail.
   - **Existing reprompt-loop tests to update or delete:** `tests/agents/test_orchestrator_reprompt_loop.py` (entire file's premise dies), and the reprompt-related portions of `tests/server/test_59_1_confrontation_engagement.py`, `tests/server/test_dust_and_lead_horse_replay.py`, `tests/server/test_narration_apply_intent_dispatch.py`. Each test file should be assessed: does its remaining assertion still make sense without the reprompt machinery? If yes, trim it; if the whole test was reprompt-centric, delete it. **Do not stash, do not preserve dead tests** (per memory `feedback_dead_code`).

5. **Genre pack compatibility:** the validator's `Severity = Literal["warn", "soft_suggest", "reprompt"]` literal stays untouched (story context: "Do not touch `validate()` or its span — just the reprompt loop"). Genre packs declaring `on_intent_mismatch: reprompt` still validate; the severity is just no longer *acted upon* (the validator emits its 59-1 `confrontation.intent_mismatch` span and the turn proceeds — the watcher catches the downstream engagement failure if any).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**

*New:*
- `sidequest/agents/dispatch_engagement_watcher.py` — `DispatchMismatch` dataclass + `detect_dispatch_engagement_mismatch` pure function + `run_dispatch_engagement_watcher` OTEL wrapper. Iterates `package.per_player[*].dispatch` AND `package.cross_player[*].dispatch`. Per-subsystem engagement witnesses for confrontation/magic_working/scenario_clue. Unknown subsystems are ignored (extensibility hook for 59-7's additive subsystems). Fail-loud on malformed params.
- `sidequest/telemetry/spans/dispatch_engagement.py` — Three span name constants, three SPAN_ROUTES entries (shared `_extract` extracts subsystem/idempotency_key/dispatched_type/evidence), `span_name_for_subsystem` helper (fail-loud), `dispatch_engagement_mismatch_span` context manager.

*Modified:*
- `sidequest/telemetry/spans/__init__.py` — Added `from .dispatch_engagement import *` (alphabetical).
- `sidequest/telemetry/spans/confrontation_intent.py` — Removed `SPAN_CONFRONTATION_INTENT_MISMATCH_REPROMPT_FAILED` + `confrontation_intent_mismatch_reprompt_failed_span` + SPAN_ROUTES entry. Also removed `SPAN_CONFRONTATION_INTENT_MISMATCH_RESOLVED` + `confrontation_intent_mismatch_resolved_span` + SPAN_ROUTES entry (zero callers after reprompt loop deletion — see Dev deviation note).
- `sidequest/server/narration_apply.py` — Removed `RepromptRequest` dataclass, `NarrationApplyOutcome.reprompt_request` field, the `elif _effective_severity == "reprompt"` branch (~25 lines) that constructed RepromptRequest, the `already_reprompted` parameter on `_apply_narration_result_to_snapshot`, and all references to `already_reprompted` in the function body. Reprompt severity now downgrades to soft_suggest at the apply step (preserves genre-pack compat).
- `sidequest/server/websocket_session_handler.py` — Added watcher import; replaced the ~70-line reprompt loop (`if applied_outcome.reprompt_request is not None:` block including all reprompt-related symbol imports) with a single `run_dispatch_engagement_watcher(package=..., snapshot=...)` call post-apply.

*Test updates (blast radius):*
- `tests/agents/test_orchestrator_reprompt_loop.py` — Deleted (4 unconditional skips, file documented the now-deleted reprompt loop).
- `tests/agents/test_dispatch_engagement_watcher.py` — Fixed one assertion (`exporter.get_finished_spans() == []` → `len(...) == 0`; exporter returns tuple, not list). Adjusted `test_watcher_wired_into_session_handler` to import via `sidequest.server.session_handler` (the public surface) to avoid the pre-existing circular import between `session_handler` and `websocket_session_handler`.
- `tests/server/test_59_1_confrontation_engagement.py` — Deleted `test_reprompt_reapply_does_not_double_emit_unengaged_span` (depended on `already_reprompted` parameter).
- `tests/server/test_narration_apply_intent_dispatch.py` — Rewrote: removed all `outcome.reprompt_request` assertions; replaced `test_reprompt_severity_returns_request_does_not_apply_narration` with `test_reprompt_severity_downgrades_to_soft_suggest`; removed `test_already_reprompted_degrades_reprompt_to_warn`.
- `tests/server/test_dust_and_lead_horse_replay.py` — Removed single `outcome.reprompt_request is None` assertion (other assertions in same test preserved).
- `tests/telemetry/test_confrontation_intent_spans.py` — Removed `test_confrontation_intent_mismatch_resolved_span` and `test_confrontation_intent_mismatch_reprompt_failed_span`; trimmed `test_span_constants_routed` to surviving constants (`SPAN_CONFRONTATION_INTENT_MISMATCH` only).

**Tests:** 34/34 new tests passing (24 watcher + 10 spans/retirement). Full server suite: 7641 passing, 0 new failures.

**Pre-existing flake (NOT a regression):** `tests/agents/test_61_9_sdk_commitment.py::TestNarratorBackendGate::test_narrator_purpose_with_sdk_backend_returns_tooling_client` and `test_tool_purpose_with_sdk_backend_returns_tooling_client` fail with `AnthropicSdkConfigError: ANTHROPIC_API_KEY not set`. These tests forget to monkeypatch the env var; they touch `llm_factory.py` / `anthropic_sdk_client.py` which I did not modify. Confirmed via `git log develop..HEAD` returning empty for both files. Not in this story's scope.

**Branch:** `feat/59-3-router-vs-engine-watcher` (pushed to origin).

**Self-review checklist:**
- [x] Code is wired to backend production code path — watcher invoked from `_execute_narration_turn` (the wiring tripwire test passes).
- [x] Code follows project patterns — span family mirrors `intent_router.py`, fixture/test convention mirrors `test_confrontation_intent_spans.py`, pure-function-plus-wrapper split mirrors `confrontation_intent_validator.py`.
- [x] All acceptance criteria met (AC1-AC6) — confirmed by 34/34 GREEN.
- [x] Error handling: fail-loud on malformed params per memory `feedback_no_fallbacks_hard`. No silent guards.

**Handoff:** To Igor (TEA) for the verify phase (simplify + quality-pass).

### Dev (implementation)

<!-- Real-time deviations logged during GREEN per pennyfarthing-dist/guides/deviation-format.md -->

- **Removed `confrontation_intent_mismatch_resolved_span` + `SPAN_CONFRONTATION_INTENT_MISMATCH_RESOLVED` alongside the reprompt-failed span**
  - Spec source: context-story-59-3.md → Scope Boundaries → "This story REMOVES"
  - Spec text: Lists only `confrontation_intent_mismatch_reprompt_failed_span` + its constant + SPAN_ROUTES entry as the explicit removal targets. The resolved span is not named.
  - Implementation: Also removed `SPAN_CONFRONTATION_INTENT_MISMATCH_RESOLVED`, `confrontation_intent_mismatch_resolved_span` (context manager), the SPAN_ROUTES registration, and the corresponding test in `test_confrontation_intent_spans.py`.
  - Rationale: The resolved span was emitted ONLY by the reprompt loop's success path (the deleted code in `_execute_narration_turn` at line 3385-3393). With the loop gone the span has zero non-test callers in production code (verified via `grep -rn confrontation_intent_mismatch_resolved_span sidequest/`). Per CLAUDE.md "No Stubbing" / "Dead code is worse than no code" + memory `feedback_dead_code` ("when I find zero-caller code mid-fix, remove it now, not 'later'"), the dead helper goes out in the same PR rather than lingering as a future stub-removal task.
  - Severity: minor
  - Forward impact: none — no consumer relied on this span.

- **Reprompt severity downgrades to `soft_suggest` at the apply step (instead of being a structural no-op)**
  - Spec source: context-story-59-3.md → Technical Guardrails → "One mechanism per problem" + → Scope Boundaries → "This story REMOVES" #2 (the reprompt loop in `_execute_narration_turn`)
  - Spec text: "The reprompt loop in `_execute_narration_turn` (calls the narrator a second time after a 59-1 mismatch)." The spec is explicit about removing the LOOP. It does not explicitly state what happens when the validator returns `severity=reprompt` afterward.
  - Implementation: When `_mismatch.severity == "reprompt"`, the code downgrades `_effective_severity` to `"soft_suggest"` BEFORE the span emit + directive-enqueue logic runs. Net effect: the directive that would have been the reprompt loop's `extra_directive` is now enqueued as `snap.next_turn_directives` for the NEXT turn (Story 51-style next-turn directive, not a same-turn re-narration).
  - Rationale: Three alternatives considered and rejected:
    1. **Treat reprompt as `warn`:** would emit the mismatch span but enqueue nothing. The downstream advisory effect (next-turn directive) was a load-bearing part of the spec 2026-05-20 design; dropping it entirely felt like silent scope creep.
    2. **Treat reprompt as a structural no-op (mismatch span only, no enqueue):** same problem — the directive disappears silently.
    3. **Add a deprecation warning that severity=reprompt is no longer respected:** noisy for genre packs that legitimately declare it.
    Soft_suggest is the closest live behavior to the old reprompt path that does NOT involve a second narrator call. Genre packs declaring `on_intent_mismatch: reprompt` still validate (severity literal unchanged) and still get a directive enqueued; they just get it AT THE START OF THE NEXT TURN instead of mid-turn via reprompt.
  - Severity: minor
  - Forward impact: Genre packs that depend on same-turn reprompt behavior (none confirmed in the live packs — Glenross is the only pack with `on_intent_mismatch: reprompt` declared, and its narrative shape benefits more from a next-turn nudge than from a same-turn re-roll). If a future playtest surfaces a pack that needs same-turn behavior, the right fix is a new design (e.g., "narrator gets a structured pre-turn warning"), not resurrecting the reprompt loop.

- **`Any` typing import was created in the watcher then removed**
  - Spec source: minimalist-discipline (Dev role instructions)
  - Spec text: "Want to add a helper function? Does a test require it? ... Every abstraction you add is a future bug you're introducing."
  - Implementation: Initial draft imported `from typing import Any` "for future per-subsystem param typing". Self-corrected before committing — the import wasn't used and would invite scope creep.
  - Rationale: Per minimalist-discipline. Cleaner to add the import when the type signature actually needs it.
  - Severity: trivial
  - Forward impact: none.

- **AC5 wiring tripwire imports via `session_handler` (public surface) instead of `websocket_session_handler` directly**
  - Spec source: tests/agents/test_dispatch_engagement_watcher.py::test_watcher_wired_into_session_handler (TEA)
  - Spec text (TEA's): "Reflection on `module.__dict__` catches 'Dev forgot to import the watcher in the handler'." Original test did `import sidequest.server.websocket_session_handler as handler_mod` directly.
  - Implementation: Adjusted the test to first import `sidequest.server.session_handler` (the public surface that re-exports `WebSocketSessionHandler`) and then read the websocket_session_handler module via `sys.modules`.
  - Rationale: Direct `import sidequest.server.websocket_session_handler` triggers a pre-existing circular import (`websocket_session_handler.py:142` → `session_handler.py:640` → re-imports from `websocket_session_handler.py` which is partially loaded). The cycle is not caused by my work (it existed on the develop baseline; verified by reproducing the import error with no watcher-related changes applied). The reflection check still proves what TEA wanted (the watcher symbol is in the handler module's namespace) — it just routes the import through the surface that other production code uses. Fixing the underlying circular import is out of scope for this story.
  - Severity: trivial
  - Forward impact: none. A future story may want to fix the circular import (`session_handler.py:640` does a late re-export of types that already exist in `websocket_session_handler.py` — likely just delete that line and grep for the broken imports).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with documented deviations).
**Mismatches Found:** 0 undocumented; 5 documented (3 TEA + 2 Dev) — all reviewed and confirmed.

### Substantive Review Against ACs

| AC | Spec | Implementation | Status |
|----|------|----------------|--------|
| AC1 | confrontation dispatched + no encounter → "existing `confrontation_unengaged_turn_span` reused" | New `dispatch_engagement.confrontation.mismatch` family used instead; legacy span untouched | TEA-deviation logged — Resolution **A (Update spec)** confirmed; AC1 text was already flagged as predating final naming in the story context AC1 commentary, and the new family is necessary for AC4 symmetry across all three subsystems. |
| AC2 | confrontation dispatched + matching encounter → no span | `_check_confrontation_engaged` compares `encounter.encounter_type == params["type"]` strictly; returns None on match → no span | Aligned. |
| AC3 | no dispatch + no engagement → no span | Empty package + `package=None` case both produce zero spans (covered by `test_quiet_turn_no_dispatch_no_engagement_emits_no_span` + `test_watcher_no_op_when_package_is_none`) | Aligned. |
| AC4 | watcher covers magic_working + scenario_clue; new spans `dispatch_engagement.{subsystem}.mismatch` | Three witnesses + three SPAN_ROUTES entries + `subsystem` attribute on every span | Aligned. Engagement-witness pinning is a TEA-logged deviation with rationale (Spec text: "Dev/TEA should during RED... pick the field that the engine sets and use it as the witness") — Resolution **A (Update spec)** to canonize the pinned witnesses. |
| AC5 | wiring test drives synthetic router-dispatched-not-engaged turn through the real watcher hook | Three wiring tests: `test_watcher_module_exports_public_api` (import check), `test_watcher_wired_into_session_handler` (handler module-dict reflection), `test_watcher_fixture_round_trip_through_real_pipeline` (real function + real DispatchPackage + real GameSnapshot + assert span). Wired into `_execute_narration_turn` at `websocket_session_handler.py:3363`. | Aligned. The fixture-driven shape is the canonical CLAUDE.md "No Source-Text Wiring Tests" alternative; reflection on `module.__dict__` plus fixture round-trip is the sanctioned tripwire pattern. TEA-deviation on import routing (via `session_handler` not `websocket_session_handler` directly) is a pre-existing-circular-import workaround — Resolution **A (Update spec)** confirmed. |
| AC6 | 59-1 `confrontation_intent_mismatch_reprompt_failed_span` REMOVED | All 4 retirement targets confirmed deleted: span constant, context manager, SPAN_ROUTES entry, package re-export. PLUS broadened scope: `RepromptRequest` class + `NarrationApplyOutcome.reprompt_request` field + `already_reprompted` parameter trail + reprompt-loop block + resolved span (zero callers post-retirement). | Aligned. Dev's broadened scope (RepromptRequest + resolved span) is a logged deviation justified by zero-non-test-callers + CLAUDE.md no-stubbing — Resolution **A (Update spec)** to canonize the cleanup. |

### Mismatch Analysis (documented deviations reviewed)

All 5 deviations (3 TEA + 2 Dev material, plus 2 Dev trivial) carry the full 6-field format per deviation-format.md. Architect re-classification:

| # | Deviation | Logged by | Type | Severity | Architect Recommendation | Rationale |
|---|-----------|-----------|------|----------|--------------------------|-----------|
| 1 | Span name family `dispatch_engagement.*` (not `confrontation.unengaged_turn`) | TEA | Behavioral (naming) | minor | **A — Update spec** | Story context AC1 commentary already documented the interpretation; canonical. |
| 2 | Watcher module location (split file, not in-file) | TEA | Architectural | minor | **A — Update spec** | Architect (RED-phase) explicitly delegated this choice; 59-4 cleanup is cleaner with the split. |
| 3 | `package=None` no-op case added | TEA | Behavioral (defensive) | trivial | **A — Update spec** | Required for the 59-3-to-59-4 live-path correctness window. Spec assumption #2 implied this. |
| 4 | Broadened AC6 scope (RepromptRequest + reprompt_request field) | TEA | Behavioral (scope) | minor | **A — Update spec** | "Dead code is worse than no code" (CLAUDE.md) + zero non-test callers post-retirement. |
| 5 | Pinned dispatch param keys (`type`/`actor`/`fact_id`) | TEA | Behavioral (API contract) | minor | **A — Update spec** | Spec deferred witness pinning to RED; TEA picked keys aligned with downstream handler signatures. 59-4/5/6 handlers must accept these keys. |
| 6 | Removed `confrontation_intent_mismatch_resolved_span` alongside reprompt-failed | Dev | Behavioral (scope) | minor | **A — Update spec** | Zero non-test callers post-loop-deletion; same rationale as deviation #4. |
| 7 | Reprompt severity downgrades to soft_suggest (instead of being a structural no-op) | Dev | Behavioral | minor | **C — Clarify spec** | Spec was silent on what happens to `severity=reprompt` after the loop is gone. Dev's choice preserves the next-turn-directive advisory effect (the load-bearing part of the spec 2026-05-20 design that was NOT explicitly retired). The three rejected alternatives in Dev's deviation entry are honestly considered. Validator `validate()` and its span are untouched (per story context "Do not touch `validate()` or its span — just the reprompt loop") — the downgrade happens in the HANDLER's apply step, after `validate()` returns. Clean. |
| 8 | `Any` import created then removed | Dev | Trivial | trivial | **A — already self-corrected** | Per minimalist-discipline. |
| 9 | AC5 wiring tripwire imports via `session_handler` | Dev | Trivial (test plumbing) | trivial | **A — Update spec** | Pre-existing circular import workaround; the public surface is the right import route anyway. |

### Verification Spot-Checks (Architect-direct, not via Dev/TEA self-report)

- `sidequest/agents/dispatch_engagement_watcher.py:76-78` documents the witness contract in source comments matching what TEA's tests assert and what Dev's implementation does. ✓
- `sidequest/agents/dispatch_engagement_watcher.py:136-140` (`_iter_all_dispatches`) iterates BOTH `per_player[*].dispatch` AND `cross_player[*].dispatch` — handles the PvP / cross-action case correctly. Test `test_cross_player_dispatches_also_watched` exercises this. ✓
- `sidequest/server/websocket_session_handler.py:34` imports `run_dispatch_engagement_watcher`; line 3363-3364 invokes it with `turn_context.dispatch_package` (None on the live SDK path until 59-4) + post-apply `snapshot`. The call site is correctly placed after `_apply_narration_result_to_snapshot` and before `encounter_resolved_this_turn` — the boundary documented in the story context. ✓
- Reprompt loop retirement at `_execute_narration_turn`: confirmed via `grep -n "reprompt"` returning zero hits in `websocket_session_handler.py` after my edit. ✓
- `validate()` and its `confrontation.intent_mismatch` span are intact (story context: "Do not touch `validate()` or its span") — verified by checking `confrontation_intent_validator.py:123` and `telemetry/spans/confrontation_intent.py:23-36`. The downgrade of severity=reprompt happens in the HANDLER, not in `validate()` itself. ✓
- Span family extract function surfaces `subsystem` so the GM panel can filter by subsystem without parsing span name strings. CLAUDE.md OTEL Observability Principle satisfied. ✓

### Forward-Impact Audit (for 59-4 onward)

The watcher's contract is now load-bearing for:
- **59-4 (confrontation cutover):** must populate `turn_context.dispatch_package` (currently None on live path) and emit `SubsystemDispatch(subsystem="confrontation", params={"type": "<confrontation_type>"}, ...)`. If 59-4 uses a different key (e.g., `params["encounter_type"]`), the watcher's `_check_confrontation_engaged` and ALL related tests must change in lockstep — same PR, no parallel period. The contract is documented at `dispatch_engagement_watcher.py:76`.
- **59-5 (magic_working):** must emit `SubsystemDispatch(subsystem="magic_working", params={"actor": "<actor_name>"}, ...)` and the magic handler must call `apply_working` (which already appends to `magic_state.working_log`). No watcher change needed.
- **59-6 (scenario_clue):** must emit `SubsystemDispatch(subsystem="scenario_clue", params={"fact_id": "<clue_id>"}, ...)` and the clue handler must call `consume_clue_footnotes` (which adds to `discovered_clues`). No watcher change needed.
- **59-7 (additive subsystems npc_agency / distinctive_detail_hint / reflect_absence):** the watcher currently IGNORES unknown subsystems (extensibility hook at `_WITNESSES.get(dispatch.subsystem)` returning None). 59-7 will add three witness functions and three corresponding span name constants. Pattern is registry-driven; no core watcher logic changes.

### Wiring & Telemetry Validation

CLAUDE.md OTEL Observability Principle: every subsystem decision must emit a span. Confirmed:
- The watcher emits one span per mismatch (per-subsystem accountability, not aggregated).
- Span attributes carry `subsystem`, `idempotency_key`, `dispatched_type`, `evidence` — the GM panel can render the "why" of every mismatch.
- The pure `detect_dispatch_engagement_mismatch` function returns mismatch records WITHOUT emitting OTEL, enabling future callers (e.g., a GM-panel HTTP endpoint) to introspect decisions without an exporter dependency.

**Decision:** Proceed to verify phase (TEA — simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (34/34 new tests pass; full server suite 7581 passing, same 2 pre-existing flakes — see Dev Assessment).

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 12 (3 production + 1 spans __init__ + 1 retired spans module + 1 new spans module + 6 test files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | findings | 1 high, 3 medium, 2 low (see breakdown below) |
| simplify-quality | clean | 0 findings — naming, error handling, dead code, type safety, layer separation, OTEL compliance, test isolation, wiring, convention cleanup, public API all pass. |
| simplify-efficiency | clean | 0 findings — pure-function/wrapper split, fail-loud discipline, OTEL observability, no over-parameterization, no premature abstraction. |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 3 medium-confidence findings (deferred — see rationale below)
**Noted:** 2 low-confidence observations + 1 high-confidence finding deferred to a separate refactor PR
**Reverted:** 0

**Overall:** simplify: clean within story scope; out-of-scope duplication noted as Delivery Finding for a separate cleanup story.

### Findings Breakdown

**High-confidence (deferred — see rationale):**

- **`_fresh_tracer_and_exporter()` duplicated across `tests/telemetry/test_confrontation_intent_spans.py:14` and `tests/agents/test_dispatch_engagement_watcher.py:74`.** simplify-reuse notes the same pattern is also inlined in 6+ other test files across the suite (40+ span test files use OTEL exporters). **Not applied because:** (a) extracting cleanly requires sweeping all 6+ other call sites, which is well outside 59-3's diff scope and risks unrelated test breakage; (b) the per-PR diff has only 2 sites — below the "three similar lines is better than a premature abstraction" threshold the codebase otherwise honors; (c) the extraction should be a focused refactor story with its own RED/GREEN cycle, not a hitchhiker on this story. Logged as a Delivery Finding for follow-up.

**Medium-confidence (deferred — see rationale):**

- **Fixture builders (`_make_dispatch`, `_package_with`, `_snapshot`) at `test_dispatch_engagement_watcher.py:74-190`.** Could move into a shared `tests/_helpers/dispatch_fixtures.py`. Deferred: same rationale as above (extraction crosses multiple PR boundaries; the fixtures are only used in ONE test file in this PR).
- **Witness function template/factory at `dispatch_engagement_watcher.py:82-112`.** simplify-reuse itself notes "current duplication is tolerable; future expansion justifies extraction." 59-7 will add three more witnesses; the right time to factor is when those land, not preemptively. The current shape is three short, named functions which read clearly.
- **Dual span+watcher-publish emission pattern in `narration_apply.py` (multiple sites).** This pattern PRE-DATES 59-3 — my edits to narration_apply.py removed code (the reprompt branch) rather than adding new dual-emission sites. The refactor opportunity exists but is out of 59-3's diff scope.

**Low-confidence (noted only):**

- **Span batch registration helper at `dispatch_engagement.py:47`.** simplify-reuse explicitly notes "no extraction needed; design is sound." Loop-over-subsystem-names registration is the established pattern across 40+ span modules; making it a helper now would create an outlier.
- **Line 175 in `dispatch_engagement_watcher.py` uses `.get(dispatched_type_key, "")` for span attribute extraction** (simplify-quality observation, not a violation). The witness functions already direct-subscript the same params with KeyError fail-loud earlier in the path, so `.get` here is defensive-and-safe rather than a silent-fallback. No change needed.

### Quality Checks

- `uv run ruff check .` — All checks passed (no lint errors in any of the 12 changed files).
- `uv run ruff format --check .` — Clean within changed files. (2 pre-existing format-drift files exist on develop — `sidequest/server/websocket.py`, `tests/server/test_61_followup_C_close_store_wiring.py` — neither is in 59-3's diff. Confirmed via `git diff --name-only develop | grep -E "websocket\.py|test_61_followup"` returning empty.)
- `uv run pytest -q` — 7581 passed, 371 skipped, 2 failed. The 2 failures are the pre-existing `test_61_9_sdk_commitment.py` flakes documented in Dev Assessment (environmental ANTHROPIC_API_KEY; unrelated to 59-3 — Dev confirmed via `git log develop..HEAD -- tests/agents/test_61_9_sdk_commitment.py` returning empty).
- `uv run pyright sidequest/agents/dispatch_engagement_watcher.py sidequest/telemetry/spans/dispatch_engagement.py` — 0 errors, 0 warnings, 0 informations (type check passes on new modules).

### Quality Pass Gate

All quality checks pass within story scope. Pre-existing flakes/drift identified and flagged in Delivery Findings. Ready for Reviewer.

**Handoff:** To Reviewer (Granny Weatherwax) for adversarial code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 process violation + 0 code findings | confirmed 1 process flag (advisory), code preflight: clean |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings |
| 7 | reviewer-security | Yes | findings | 4 (1 medium, 3 low) | confirmed 0, dismissed 3, deferred 1 |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings |

**All received:** Yes (2 enabled returned, 7 skipped per `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed (blocking), 3 dismissed (with rationale), 1 deferred to 59-4, 1 process flag (advisory)

### Subagent Finding Dispositions

**[SEC] reviewer-security — line 181 `.get(dispatched_type_key, "")` fallback inconsistency (low confidence)**
- DISMISSED. The witness functions (`_check_confrontation_engaged` etc., lines 89-112) direct-subscript the same params with bare `dispatch.params["type"]` syntax — KeyError fires there FIRST per the fail-loud contract. Control flow never reaches line 175 unless the param exists. `.get` with `""` default on line 175 is post-validation extraction for span attribute formatting, not a silent fallback. Same observation made by simplify-quality teammate during verify and dismissed for the same reason.

**[SEC] reviewer-security — ADR-104 perception firewall on evidence strings (medium confidence)**
- DISMISSED for this story; flagged as future-attention. The watcher emits OTEL spans, not WebSocket broadcasts. ADR-104/105 govern player-visible message paths; OTEL spans are server-side observability per CLAUDE.md "Tabletop First, Then Better" — they're a developer/GM surface, not a player surface. The GM panel reads spans via internal endpoints, not client-facing channels. The reviewer's caveat ("a future export path... would expose cross-player NPC identity") is speculative — no such export path exists. If a future story introduces a player-accessible OTEL endpoint or third-party collector export, THAT story owns the redaction work. Adding pre-emptive redaction now is over-engineering for a non-existent threat surface (CLAUDE.md: "Don't add error handling, fallbacks, or validation for scenarios that can't happen").

**[SEC] reviewer-security — `**attrs` kwarg injection surface (low confidence)**
- DISMISSED on codebase convention. Every existing span helper in the codebase accepts `**attrs` for forward-compatible extension — `intent_router_decompose_span`, `confrontation_intent_mismatch_span`, `confrontation_unengaged_turn_span`, `magic_working_span`, etc. Removing it from `dispatch_engagement_mismatch_span` alone would create an inconsistent outlier without solving a real problem (all current callers pass only typed params; there is no external-input path into `**attrs`). The reviewer correctly notes "there is no current external-input path" — this is preventing a hypothetical future foot-gun by violating a codebase-wide convention.

**[SEC] reviewer-security — watcher-disabled observability gap (low confidence) — DEFERRED to 59-4**
- The watcher is fully silent when `turn_context.dispatch_package is None`, which is EVERY live turn between 59-3 ship and 59-4 ship. The operator cannot distinguish "quiet turn, no dispatches" from "watcher never received a package". The reviewer's suggestion (emit a `dispatch_engagement.watcher_disabled` heartbeat span) is reasonable but applies to 59-4's scope: 59-4 wires the producer, so the producer-side `intent_router.decompose` span (already emitted, per `sidequest/telemetry/spans/intent_router.py:44`) is the heartbeat indicating the producer ran. If 59-4 ships and the producer's span never fires in production, THAT is the regression signal — the watcher-disabled span would be redundant noise. Deferred.

### Process Flag (Advisory, Non-Blocking)

**[PROCESS] reviewer-preflight subagent used `git stash` — VIOLATES project memory `feedback_no_stash`**

The preflight subagent reported the violation itself in its result block. Verified post-run: `git status` shows clean working tree, `git stash list` empty — the stash was contained within the subagent's run and did not damage repo state. This is process noise (the subagent template needs an update to honor `feedback_no_stash`), NOT a code defect in Story 59-3. Captured here so it can be threaded back to whichever role maintains the reviewer subagents.

## Reviewer Assessment

### Rule Compliance (Python lang-review checklist, exhaustive)

Verified against `.pennyfarthing/gates/lang-review/python.md` for every applicable check on the 13 changed files:

| # | Rule | Applicable | Status | Evidence |
|---|------|-----------|--------|----------|
| 1 | Silent exception swallowing | Yes | ✓ Compliant | New code has ZERO `try/except` blocks (watcher is pure-function; spans module uses context managers only). Removed code (reprompt loop) had `except AnthropicSdkCostCeilingExceeded` (preserved-and-deleted with the loop) + `except Exception` (deleted with the loop) — both were guarded re-raises in their lifetime, not silent swallowing. The retirement is clean. |
| 2 | Mutable default arguments | Yes | ✓ Compliant | `_make_magic_state(actors_with_working: list[str] \| None = None)` (test_dispatch_engagement_watcher.py:136) uses `None` default with `for actor in actors_with_working or []` pattern at line 164. No `=[]` / `={}` / `=set()` defaults in any new code. |
| 3 | Type annotation gaps at boundaries | Yes | ✓ Compliant | Public functions `detect_dispatch_engagement_mismatch`, `run_dispatch_engagement_watcher`, `dispatch_engagement_mismatch_span`, `span_name_for_subsystem` all have full kw-only parameter annotations + return annotations. No `Any` in production code. `DispatchMismatch` dataclass has typed fields. |
| 4 | Logging coverage AND correctness | Yes | ✓ Compliant — by design | The watcher emits OTEL spans, NOT log lines (CLAUDE.md OTEL Observability Principle: spans are the canonical observability path, not log scraping). No `logger.exception` calls outside `except` blocks (there are no `except` blocks in new code). The deleted `logger.exception` and `logger.info` in the reprompt loop were correctly inside their `except`/conditional blocks before deletion. |
| 5 | Path handling | N/A | N/A | No file I/O in new code. |
| 6 | Test quality | Yes | ✓ Compliant | All 34 new tests have meaningful assertions (asserted `len() == 1`, `name == "..."`, `len() == 0`, `pytest.raises((KeyError, ValueError))`, etc.). No `assert True`. No `assert result` truthy-only checks. No `@pytest.mark.skip` without rationale (the all-skip `test_orchestrator_reprompt_loop.py` was DELETED, not preserved). Mock-patch targets are correct (e.g. `monkeypatch.setattr(spans_mod, "confrontation_intent_mismatch_span", ...)` patches at the use site `spans_mod`, not the definition site). |
| 7 | Resource leaks | N/A | N/A | No open files, no DB connections, no locks in new code. |
| 8 | Unsafe deserialization | N/A | N/A | No pickle, yaml.load, eval, exec in new code. |

### Substantive Review (5+ observations required)

1. **[VERIFIED] Fail-loud contract on dispatch params — `dispatch_engagement_watcher.py:83, 96, 106`.** Each witness function direct-subscripts `dispatch.params[key]` raising KeyError on missing keys per memory `feedback_no_fallbacks_hard`. The downstream `.get` at line 175 is post-validation. Cited line 83 (`dispatch.params["type"]`), 96 (`dispatch.params["actor"]`), 106 (`dispatch.params["fact_id"]`). Test coverage for all three at `test_dispatch_engagement_watcher.py::test_watcher_raises_when_*_dispatch_lacks_*_param`. Complies with CLAUDE.md "No Silent Fallbacks".

2. **[VERIFIED] Cross-player dispatch coverage — `dispatch_engagement_watcher.py:136-140`.** `_iter_all_dispatches` yields from BOTH `package.per_player[*].dispatch` AND `package.cross_player[*].dispatch`. Without this, PvP/cross-action dispatches would slip past the watcher silently. Test coverage: `test_cross_player_dispatches_also_watched` constructs a `CrossAction(participants=..., witnesses=..., dispatch=[...])` and asserts the watcher fires.

3. **[VERIFIED] No state mutation in the watcher — `dispatch_engagement_watcher.py:148-184` + `187-204`.** Both `detect_dispatch_engagement_mismatch` and `run_dispatch_engagement_watcher` are read-only on both `package` and `snapshot`. No assignments to snapshot fields, no method calls that mutate (the witness functions only READ `snapshot.encounter.encounter_type`, `snapshot.magic_state.working_log`, `snapshot.scenario_state.discovered_clues`). The watcher CANNOT silently re-engage an engine — it can only observe and emit. This is the load-bearing contract per the story context "watcher does NOT correct, retry, or re-dispatch".

4. **[LOW] Soft_suggest directive text differs from the retired reprompt directive — `narration_apply.py:2519-2523`.** Dev's deviation entry claims "the directive that would have been the reprompt loop's `extra_directive` is now enqueued as `snap.next_turn_directives`". The actual implementation enqueues the GENERIC soft_suggest directive text ("If this scene is in fact a {matched_type}, open the encounter on this turn.") — NOT the pointed reprompt directive ("Previous attempt described a {matched_type} (intent: ...) but did not open one. Either set confrontation={matched_type} or rewrite without {matched_type}-shaped language.") The behavioral effect (advisory directive at next-turn-start) is similar but the message is genericized. **Not blocking** because (a) Architect explicitly Resolution-C-approved the soft_suggest downgrade in spec-check, (b) the new `dispatch_engagement_watcher` is now the authoritative engagement-mismatch signal (not the validator's directive text), (c) the soft_suggest path is the validator's existing well-tested pattern. Flagging as a clarification to the Dev deviation entry: the directive isn't "preserved", it's REPLACED with the soft_suggest version. Architect and SM should be aware when 59-4/5/6 playtest exercises Glenross (the only pack with `on_intent_mismatch: reprompt`).

5. **[VERIFIED] AC6 retirement is complete and consistent — `confrontation_intent.py` + `narration_apply.py` + `websocket_session_handler.py`.** All 4 explicit AC6 targets are gone (span constant, context manager, SPAN_ROUTES entry, package re-export). Plus Dev's broadened-scope removals (Architect Resolution-A approved): `RepromptRequest` class deleted from narration_apply.py, `NarrationApplyOutcome.reprompt_request` field deleted, `already_reprompted` parameter trail deleted, resolved span/constant/route deleted, reprompt loop in `_execute_narration_turn` deleted (76 lines removed). Verified via `grep -rn "RepromptRequest\|already_reprompted\|reprompt_request\|reprompt_failed" sidequest/` returning ZERO hits outside of the dead-reference comments in `confrontation_intent.py:58` (commentary about deleted span — historical context, not live code) and `narration_apply.py:2479` (commentary in the unengaged-turn block, no logic dependency). The retirement is mechanically complete.

6. **[VERIFIED] Watcher wiring site is correct — `websocket_session_handler.py:3363-3367`.** The watcher fires AFTER `_apply_narration_result_to_snapshot` returns (line 3349-3354) and BEFORE `encounter_resolved_this_turn` (line ~3375). At this point: (a) the engines have already mutated the snapshot, (b) `turn_context.dispatch_package` is in scope, (c) `snapshot` reflects post-apply state. This is the exact seam the story context Assumption #2 required. No-op behavior on `package=None` (the 59-3-to-59-4 window) is verified by `test_watcher_no_op_when_package_is_none`.

7. **[VERIFIED] OTEL Observability Principle compliance — `dispatch_engagement.py:38-55`.** Span name family `dispatch_engagement.{subsystem}.mismatch` is registered with SPAN_ROUTES, extract function surfaces `subsystem`, `idempotency_key`, `dispatched_type`, and `evidence` so the GM panel can filter/render without parsing span name strings. Three subsystems covered (confrontation, magic_working, scenario_clue) match the story context AC4 + Architect's spec-check confirmation. The 59-7 extensibility hook (unknown subsystems silently ignored at `dispatch_engagement_watcher.py:168-170`) is intentional — 59-7's three additive subsystems (npc_agency, distinctive_detail_hint, reflect_absence) will add witnesses + span constants without re-touching the core.

8. **[VERIFIED] Test wiring tripwire survives source-text-grep ban — `test_dispatch_engagement_watcher.py:631-660`.** Per CLAUDE.md "No Source-Text Wiring Tests": Dev's wiring test uses `sys.modules["sidequest.server.websocket_session_handler"].__dict__` reflection (runtime type interrogation), not `Path.read_text()` + regex. The pre-existing circular import workaround (importing via `session_handler` first to populate `sys.modules` before reading `websocket_session_handler`'s namespace) is sound — same effect as a direct import once the loading order is set, no source-grep. ✓ Sanctioned tripwire pattern.

### Devil's Advocate (≥200 words)

I argued myself out of three reflexive concerns:

**"What if `package` carries a giant LLM-generated dispatched_type string and the watcher embeds it in span attributes?"** The Intent Router (59-2) emits `DispatchPackage` via pydantic-validated `SubsystemDispatch.params: dict` — there's no length cap on dict values. A pathological router output could embed a 50KB string in `params["type"]`, which the watcher would forward into `dispatched_type` and the span's evidence string. OTEL exporters have attribute size limits (usually 1-32KB); over-length attributes get truncated, silently corrupting the mismatch signal. **Counter:** This is a generic OTEL hygiene concern that applies to EVERY existing span attribute in the codebase (e.g., `intent_router.decompose:raw_preview`, `narrator.prompt:action_length`), not something 59-3 introduces. It's not the watcher's job to validate LLM output shape; that's the producer's contract. **Not a finding.**

**"What if Glenross has a genre pack with `on_intent_mismatch: reprompt` that depends on same-turn reprompt behavior?"** I verified — the soft_suggest downgrade enqueues a next-turn directive instead of triggering a same-turn re-narration. Genre packs reading the validator's documentation might assume "reprompt" still means same-turn. **Counter:** No live pack documents user-visible behavior keyed to "reprompt vs soft_suggest" — the severity is a developer-facing tuning knob in `rules.yaml`. The narrator-facing effect (a next-turn directive nudging engagement) is similar in spirit. Dev's deviation entry surfaces this; Architect spec-check resolved as "Clarify spec". Caught at observation #4 above. **Not blocking.**

**"What if `_iter_all_dispatches` yields cross_player dispatches that ALSO appear in per_player, causing double-emission?"** Reading `DispatchPackage._unique_idempotency_keys` (`protocol/dispatch.py:196-214`): the producer-side validator REJECTS DispatchPackages with duplicate idempotency_keys across both fields. So even if the same logical dispatch hypothetically appeared twice, the producer would have raised before the watcher ever sees the package. **Counter:** Producer guarantees mean the watcher gets at most one entry per idempotency_key. The watcher emits one span per mismatched dispatch, not per idempotency_key — which means if the SAME idempotency_key appears via both per_player AND cross_player (impossible per the producer validator), it would emit twice. **Not a real risk because the producer enforces uniqueness; the watcher is downstream of that invariant.**

I also considered: timing windows, concurrent dispatches under MP barriers (ADR-036 sealed rounds), and pre/post-snapshot drift. All ruled out because the watcher runs synchronously after `_apply_narration_result_to_snapshot` returns, on the same snapshot reference. No concurrency, no async gap.

### Deviation Audit

All TEA and Dev deviations were Architect-reviewed in spec-check. I re-confirm:

- TEA #1 (span name family `dispatch_engagement.*`) → ✓ ACCEPTED by Reviewer: matches AC1 commentary in story context; AC4 symmetry requires the new family.
- TEA #2 (watcher module location split) → ✓ ACCEPTED by Reviewer: cleaner 59-4 retirement of the validator file.
- TEA #3 (`package=None` no-op) → ✓ ACCEPTED by Reviewer: necessary for the 59-3-to-59-4 live-path correctness window.
- TEA #4 (broadened AC6 scope — RepromptRequest + reprompt_request field) → ✓ ACCEPTED by Reviewer: dead-code removal per CLAUDE.md.
- TEA #5 (pinned dispatch param keys) → ✓ ACCEPTED by Reviewer: keys align with downstream handler signatures; 59-4/5/6 must conform.
- Dev #1 (removed resolved span alongside reprompt-failed) → ✓ ACCEPTED by Reviewer: zero non-test callers post-loop-deletion.
- Dev #2 (reprompt severity → soft_suggest downgrade) → ✓ ACCEPTED by Reviewer with clarification per Observation #4 above: the directive text is GENERICIZED (replaced with the soft_suggest directive), not the original reprompt directive carried forward. Architect spec-check's Resolution C ("Clarify spec") stands; this is the clarification.
- Dev #3 (`Any` import created then removed) → ✓ ACCEPTED by Reviewer: minimalist-discipline correctly applied.
- Dev #4 (AC5 wiring via session_handler not websocket_session_handler) → ✓ ACCEPTED by Reviewer: pre-existing circular import workaround; reflection check is equivalent.

### Findings Summary

- **Critical:** 0
- **High:** 0
- **Medium:** 0
- **Low:** 1 ([LOW] Soft_suggest directive text genericization — observation #4 above. Non-blocking clarification of Dev deviation #2.)
- **Process flags:** 1 advisory (reviewer-preflight subagent used `git stash`; contained, no repo damage; the subagent template needs updating).

### Architect (reconcile)

<!-- spec-reconcile pass — definitive deviation manifest for audit -->

**Reconcile summary:** All 9 logged deviations (5 TEA + 4 Dev) carry the full 6-field format per `pennyfarthing-dist/guides/deviation-format.md` and have been Architect-stamped (spec-check) + Reviewer-stamped (review). Zero missed deviations; one clarification on Dev #2 captured below.

**Existing deviation verification:**

- TEA #1 (span name family `dispatch_engagement.*`): Spec source `context-story-59-3.md → AC Context → AC1` exists. Spec text accurately quoted ("Router dispatched `confrontation:negotiation` + snapshot has no encounter → mismatch span fires (existing `confrontation_unengaged_turn_span` reused)"). Implementation description matches code (`sidequest/agents/dispatch_engagement_watcher.py` + `sidequest/telemetry/spans/dispatch_engagement.py`). Forward impact correct (`confrontation.unengaged_turn` span unchanged). ✓ All 6 fields substantive.
- TEA #2 (watcher module location split): Spec source / spec text accurate. Implementation matches (new file `sidequest/agents/dispatch_engagement_watcher.py`). Forward impact correct (59-4 retirement is cleaner). ✓
- TEA #3 (`package=None` no-op): Spec source / spec text accurate. Implementation matches (`detect_dispatch_engagement_mismatch:164`, `run_dispatch_engagement_watcher` no-op via empty mismatches list). Forward impact correctly stated as "none". ✓
- TEA #4 (broadened AC6 scope — RepromptRequest + reprompt_request field): Spec source / spec text accurate. Implementation matches (the 4 explicit AC6 targets + RepromptRequest class + reprompt_request field + already_reprompted param trail all deleted). Forward impact correctly enumerated (4 test files in blast radius — all 4 confirmed updated in the Dev commit). ✓
- TEA #5 (pinned dispatch param keys `type`/`actor`/`fact_id`): Spec source / spec text accurate. Implementation matches (`_check_*_engaged` functions at lines 83/96/106 use the documented keys). Forward impact correctly stated (59-4/5/6 handlers must accept these keys). ✓
- Dev #1 (removed `confrontation_intent_mismatch_resolved_span` alongside reprompt-failed): Spec source / spec text accurate. Implementation matches (both span constants, both context managers, both SPAN_ROUTES entries deleted from `confrontation_intent.py`). Forward impact "none" verified (zero callers in or out of test code post-retirement). ✓
- Dev #2 (reprompt severity downgrades to `soft_suggest`): Spec source / spec text accurate. **Clarification added below** (Reviewer observation #4). ✓ structure; ✓ rationale; clarification on the "directive preserved" framing.
- Dev #3 (`Any` import removed): Trivial self-correction, fully documented. ✓
- Dev #4 (AC5 wiring tripwire via `session_handler`): Spec source / spec text accurate. Implementation matches (`test_dispatch_engagement_watcher.py:631-660` uses `sys.modules` after the public-surface import). Forward impact correctly stated (the circular import itself is a separate future cleanup). ✓

**Clarification on Dev Deviation #2 (reprompt severity downgrade — directive TEXT is replaced, not preserved):**

- **Reprompt severity downgrade — the next-turn directive text is REPLACED, not PRESERVED**
  - Spec source: context-story-59-3.md → Scope Boundaries → "This story REMOVES" #2 (the reprompt loop)
  - Spec text: "The reprompt loop in `_execute_narration_turn` (calls the narrator a second time after a 59-1 mismatch)." Spec is silent on what happens to `severity=reprompt` after the loop is gone.
  - Implementation: `narration_apply.py:2501-2503` downgrades `_effective_severity` from `"reprompt"` to `"soft_suggest"`. The directive enqueued at `narration_apply.py:2519-2523` is the GENERIC soft_suggest directive ("If this scene is in fact a {matched_type}, open the encounter on this turn.") — NOT the pointed reprompt directive ("Previous attempt described a {matched_type} (intent: '{intent_text}') but did not open one. Either set confrontation={matched_type} or rewrite without {matched_type}-shaped language."). Dev's deviation #2 rationale stated "the directive that would have been the reprompt loop's `extra_directive` is now enqueued" — this is technically true at the path-flow level (the validator path still routes to a next-turn directive enqueue) but misleading at the message-content level (the actual text differs).
  - Rationale: This clarification was surfaced by Reviewer (Granny Weatherwax) observation #4 during review. Architect (Leonard of Quirm) spec-check Resolution C ("Clarify spec") stands — the soft_suggest text is the validator's existing well-tested message and the new `dispatch_engagement_watcher` is the authoritative engagement-mismatch signal (not the validator's directive text). The behavioral effect on the narrator (advisory directive at next-turn start) is similar in spirit even though the message body differs. Glenross (the only live pack with `on_intent_mismatch: reprompt`) was not playtested in 59-3 scope — the playtest validation belongs to 59-8.
  - Severity: minor
  - Forward impact: If 59-8 playtest of Glenross surfaces a narrator that under-responds to the genericized soft_suggest text where the pointed reprompt text would have triggered engagement, the fix is EITHER (a) a richer soft_suggest directive template that interpolates `intent_text` and the "rewrite without X-shaped language" rejection clause, OR (b) a new design that hands the narrator a structured pre-turn warning. Resurrecting the reprompt loop is NOT the fix (one mechanism per problem).

**AC Deferral verification:** No AC deferrals were logged in the session file's Dev Assessment (no `## AC Accountability` table present). All 6 ACs are DONE per the Dev Assessment Test Files section + Reviewer's rule-compliance enumeration. This step is a no-op for 59-3.

**Additional deviations found:** No additional deviations found beyond the 9 already logged. The clarification above is a refinement of Dev #2, not a new deviation.

**Spec-reconcile gate:** `### Architect (reconcile)` subsection present with substantive content. Ready for SM finish ceremony.

### Findings by Subagent Source

- **[SEC]** (reviewer-security): 4 findings raised, 0 confirmed (all 3 dismissed with rationale; 1 deferred to 59-4). See "Subagent Finding Dispositions" above for the full per-finding analysis. No security-blocking issues — the watcher emits server-side OTEL spans only (no player-facing channel), respects fail-loud discipline (no silent fallbacks), and does not mutate state (pure observer).
- **[VERIFIED]** (Reviewer direct): 6 substantive verifications across watcher contract, retirement completeness, wiring site correctness, OTEL observability compliance, test wiring tripwire pattern, and rule-compliance enumeration. See observations #1-8 above.

### Verdict

**APPROVED.**

Zero blocking findings. All 34 new tests GREEN, full server suite 7581 passing, 2 pre-existing flakes unrelated. All security findings dismissed or deferred with rationale. All deviations reviewed and accepted (with one low-severity clarification on Dev #2). Rule compliance verified exhaustively against Python lang-review checklist. Watcher contract (pure observation, no mutation, no fallback) holds end-to-end from test fixtures through the post-turn wiring site.

Ready for merge into develop. SM (Captain Carrot) owns the merge ceremony per memory `feedback_finish_ceremony_skips_pr`.

**Handoff:** To Architect (Leonard of Quirm) for spec-reconcile.