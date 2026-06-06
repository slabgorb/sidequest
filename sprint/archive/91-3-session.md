---
story_id: "91-3"
jira_key: null
epic: "91"
workflow: "tdd"
---
# Story 91-3: Intent Router cache repair + fail-loud floor guard (combined prefix >=4096 or raise at build; live-gated test: cache_creation>0 turn 1, cache_read>0 turn 2; DESCOPE if local routing epic lands first)

## Story Details
- **ID:** 91-3
- **Jira Key:** None (Jira not configured for this project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Type:** bug
- **Points:** 3
- **Priority:** p1
- **Epic:** 91 (Dark Spend — LLM Cost Observability & Cache Integrity)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-06T01:45:58Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T00:00:00Z | 2026-06-06T01:14:40Z | 25h 14m |
| red | 2026-06-06T01:14:40Z | 2026-06-06T01:22:42Z | 8m 2s |
| green | 2026-06-06T01:22:42Z | 2026-06-06T01:36:49Z | 14m 7s |
| review | 2026-06-06T01:36:49Z | 2026-06-06T01:45:58Z | 9m 9s |
| finish | 2026-06-06T01:45:58Z | - | - |

## Story Context

### Title
Intent Router cache repair + fail-loud floor guard

### Description
The intent router fails to pass the combined prefix through to prompt cache in Haiku calls. Requirement: verify combined prefix is >= 4096 bytes at build time; fail loud if not (prevent silent no-cache trap). Live-gated test: cache_creation > 0 on turn 1, cache_read > 0 on turn 2.

**DESCOPE:** If the local classification routing epic (wiring epic-48 Ollama deliverables) lands first, this story is descoped — the Haiku bill will be removed entirely.

### Acceptance Criteria
1. Combined intent-router prefix size is validated at build time to be >= 4096 bytes
2. Build fails with clear error message if prefix is below threshold
3. Integration test verifies cache_creation > 0 on first turn
4. Integration test verifies cache_read > 0 on second turn
5. OTEL spans log cache metrics (creation, reads) for observability

### Epic Context
Dark Spend — LLM Cost Observability & Cache Integrity (Epic 91)
- Cost-forensics found ~half the daily Anthropic bill invisible to internal accounting
- Haiku 4.5 burns $3.3-3.5/day with ZERO prompt caching (silent-no-cache trap)
- ~8 Haiku calls/turn vs expected ~1 (575 calls / 70 turns on Jun 4)
- ~97% of that spend emits no llm.request span and no usage log line
- Sibling epic (local classification routing) removes the Haiku bill entirely
- Story 91-3 is descoped if local routing lands first

## Sm Assessment

**Setup complete; story is ready for the RED phase.**

- **Session + context:** Session file created; story context auto-generated and validated at `sprint/context/context-story-91-3.md`. ACs are concrete and testable (build-time floor guard >= 4096, fail-loud below threshold, live-gated cache_creation/cache_read assertions, OTEL cache metrics).
- **Branch:** `feat/91-3-intent-router-cache-repair` created off develop in sidequest-server (gitflow per repos.yaml). Single-repo story.
- **Jira:** Not configured (jira_key null) — claim explicitly skipped.
- **Workflow:** tdd (phased). Next agent: tea (RED — write failing tests for the floor guard and the live-gated cache assertions).
- **Risk noted at selection:** This story carries a conditional descope against 92-2 (local classification routing). User selected 91-3 with that flag in full view. If 92-2 lands mid-flight, the descope must be recorded explicitly per ADR-092 doctrine, not silently dropped — flagging for the review/finish phases.
- **Technical pointers for TEA:** Intent Router lives in sidequest-server (ADR-113); SDK backend + caching per ADR-101 (`sidequest/agents/`). The live-gated test pattern (cache_creation>0 turn 1, cache_read>0 turn 2) mirrors the 91-6 gate (both_writes_fired WARN gated on cache_read>0). Honor No Silent Fallbacks: below-floor prefix must raise at build, never silently skip caching.

## Delivery Findings

### TEA (test design)
- **Question** (non-blocking): The org-wide 0/0 cache incident occurred *despite* the marker+header being in code — one plausible root cause is that the real combined prefix is actually below the 4,096-token floor live (the ~4,730-token figure is a char-ratio estimate; the authoritative opt-in `test_intent_router_prefix_token_floor_live` may never have been run). Affects `sidequest/agents/llm_factory.py` (Dev should run BOTH env-gated live tests — `SIDEQUEST_VERIFY_HAIKU_CACHE_FLOOR` and the new `SIDEQUEST_VERIFY_HAIKU_CACHE_LIVE` — early in GREEN to learn whether the repair is "grow/restructure the prefix" or "config/transport"). *Found by TEA during test design.*
- **Improvement** (non-blocking): The guard estimator must be offline (no `count_tokens` network call) because `build_intent_router_for_session` constructs the adapter once per turn. Affects `sidequest/agents/llm_factory.py` (calibrate chars→tokens against the measured ~3.2 chars/tok; both calibration ends are pinned by tests). *Found by TEA during test design.*

### Dev (implementation)
- **Question** (non-blocking): TEA's root-cause question is ANSWERED by live measurement — the prefix is 4,730 tokens (above floor) and the two-turn cache proof PASSES live, so the marker fix pinned in `test_haiku_cache_control.py` already repaired the cache; the org-wide 0/0 Admin-API data predated it. Affects `sprint/context/context-epic-91.md` (epic stories 91-2/91-5 should expect the Haiku cache line to be warm going forward — the ~75% Haiku-spend reduction may already be in flight; 91-5's reconciliation should confirm against Admin API ground truth, which lags). *Found by Dev during implementation.*
- **Improvement** (non-blocking): The story's "DESCOPE if local routing lands first" condition did NOT trigger — 92-2 has not landed; this story shipped as scoped. If 92-2 later routes classification to Ollama, the guard simply stops being exercised on the Anthropic path; no removal needed. Affects `sprint/epic-91.yaml` (note for the 91-3 close-out: descope clause resolved as not-triggered). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): The build-time guard validates module constants, not the `system` argument `emit_tool` actually receives — a future second caller of `_IntentRouterLlm` (or a prompt-parameterizing refactor) could pass a sub-floor system through a passing build and silently no-cache. Affects `sidequest-server/sidequest/agents/llm_factory.py` (consider a call-time assertion in `emit_tool` or a docstring contract note if a second caller ever appears). *Found by Reviewer during code review.*
- **Gap** (non-blocking): The refusal span's `StatusCode.ERROR` is untested — `set_status` could be removed and the suite stays green; the GM panel's at-a-glance error signal is unpinned. Affects `sidequest-server/tests/agents/test_91_3_cache_floor_guard.py` (add a one-line status assertion in `test_failing_build_emits_cache_floor_span_before_raising`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing bare `except Exception` in `_IntentRouterLlm.emit_tool`'s usage_repr fallback violates lang-review #1/#4 (no logger call, no safety-justification comment) — untouched by this diff. Affects `sidequest-server/sidequest/agents/llm_factory.py` (add justifying comment + logger.warning, any future story touching this file). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): TEA's RED-phase "Today..." narrative in two test docstrings reads as false post-merge, and the 15,425-vs-15,289 char figures in llm_factory.py vs test_haiku_cache_control.py differ without an explanatory cross-note (estimator includes tool name+description; tripwire does not). Affects `sidequest-server/tests/agents/test_91_3_cache_floor_guard.py` and `sidequest-server/sidequest/agents/llm_factory.py` (doc-polish pass: recast to past tense, add one-line scope note to the calibration comments). *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **AC1 floor unit corrected from bytes to tokens**
  - Spec source: .session/91-3-session.md, AC-1
  - Spec text: "Combined intent-router prefix size is validated at build time to be >= 4096 bytes"
  - Implementation: Tests validate a 4,096-**token** floor (`floor_tokens == 4096`, estimate compared in tokens)
  - Rationale: The API's cacheable-prefix floor is measured in tokens, not bytes — per epic context ("Haiku's 4,096-token cacheable floor"), the story title, and the in-code docs; 4,096 *bytes* (~1,280 tok) would pass prefixes that silently never cache
  - Severity: minor
  - Forward impact: Dev implements a token-denominated guard; spec-authority hierarchy honored (story title + epic context over the session AC transcription)
- **AC3/AC4 strengthened from >0 to >=4096, with nonce-salted prefix**
  - Spec source: .session/91-3-session.md, AC-3/AC-4
  - Spec text: "cache_creation > 0 on first turn ... cache_read > 0 on second turn"
  - Implementation: Live test asserts `cache_creation_input_tokens >= 4096` (turn 1) and `cache_read_input_tokens >= 4096` (turn 2), with the production system prompt salted by a per-run uuid nonce
  - Rationale: `>= floor` proves the *whole* tools+system prefix cached, not a fragment; the nonce guarantees a cold turn-1 write even when a prior run within the 1h TTL left the unsalted prefix warm (without it, a warm turn 1 reports creation=0 and the test flakes)
  - Severity: minor
  - Forward impact: none — strictly stronger than the AC; salt adds ~10 tokens and does not change the mechanics under test
- **AC5 covered via guard-decision span, not duplicated per-call metrics**
  - Spec source: .session/91-3-session.md, AC-5
  - Spec text: "OTEL spans log cache metrics (creation, reads) for observability"
  - Implementation: New tests pin the `intent_router.cache_floor` span (pass+fail paths); per-call `llm.cached_input_{read,write}_tokens` on `llm.request` spans are asserted through the live test end-to-end rather than re-pinned in new unit tests
  - Rationale: Per-call cache metrics are already pinned by 91-1 (`test_91_1_sdk_choke_point_instrumentation.py:464`) and `test_haiku_cache_control.py`; duplicating them adds maintenance surface without coverage
  - Severity: minor
  - Forward impact: none

### Dev (implementation)
- **Guard estimator includes tool name+description beyond TEA's tripwire formula**
  - Spec source: tests/agents/test_91_3_cache_floor_guard.py (TEA contract) + test_haiku_cache_control.py tripwire
  - Spec text: "the combined tools+system prefix (production `_SYSTEM_PROMPT` + `_dispatch_tool_schema()`, read late-bound through the `intent_router` module)"
  - Implementation: Estimator sums system prompt + schema JSON + `_TOOL_NAME` + `_TOOL_DESCRIPTION` chars (the cache marker covers the full tools block, name and description included)
  - Rationale: More accurate to what the API actually caches; adds ~250 chars (~78 tok) and changes no test outcome
  - Severity: minor
  - Forward impact: none — both TEA calibration ends still hold
- **Ratio 3.2 chosen to sit beneath the existing CI tripwire**
  - Spec source: context-epic-91.md, Design constraints
  - Spec text: "raises at client-build time if the combined cacheable prefix is below 4,096 tokens"
  - Implementation: Offline estimate `chars / 3.2` (measured live ratio 3.261), so the runtime guard threshold (~13.1k chars) is slightly looser than the 13.5k-char CI tripwire in test_haiku_cache_control.py
  - Rationale: Ordering matters — a shrinking prefix should fail in CI (tripwire) before the runtime guard starts killing live sessions; the guard is the last-resort backstop, count_tokens the authoritative check
  - Severity: minor
  - Forward impact: none — documented in the constant's comment for whoever picks up 82-10 (state_summary slimming does not touch this prefix, but prompt slimming would)

### Reviewer (audit)
- **TEA: AC1 floor unit corrected from bytes to tokens** → ✓ ACCEPTED by Reviewer: the API floor is token-denominated; 4,096 *bytes* (~1,280 tok) would wave through silently-uncacheable prefixes — the session AC was a transcription error, epic context is authoritative.
- **TEA: AC3/AC4 strengthened from >0 to >=4096, with nonce-salted prefix** → ✓ ACCEPTED by Reviewer: strictly stronger assertions; the salt is required for determinism against the 1h TTL (an unsalted re-run within the hour would report creation=0 and flake).
- **TEA: AC5 covered via guard-decision span, not duplicated per-call metrics** → ✓ ACCEPTED by Reviewer: per-call cache fields verified pinned at test_91_1_sdk_choke_point_instrumentation.py:464 and test_haiku_cache_control.py:142-170; the live test additionally proves them end-to-end.
- **Dev: Guard estimator includes tool name+description beyond TEA's tripwire formula** → ✓ ACCEPTED by Reviewer: verified `model_json_schema()` excludes name/description (intent_router.py:100), so the addends are disjoint and the wider sum is more faithful to what the API caches; explains the 15,425-vs-15,289 char delta between the two comments (a [DOC] low to clarify, not a contradiction).
- **Dev: Ratio 3.2 chosen to sit beneath the existing CI tripwire** → ✓ ACCEPTED by Reviewer: the layered ordering (CI tripwire 13,500 chars fires before the runtime guard's ~13,107) is deliberate and documented; note the inherent estimator false-pass window (13,107–13,353 chars) is covered ONLY by the tripwire + live test — recorded in Devil's Advocate and as a delivery finding.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/agents/llm_factory.py` — `IntentRouterCacheFloorError(LlmClientError)`, `HAIKU_CACHEABLE_PREFIX_FLOOR_TOKENS = 4096`, offline prefix estimator (`_estimate_intent_router_prefix_tokens`, late-bound reads of `intent_router._SYSTEM_PROMPT`/`_dispatch_tool_schema`/tool name+description, ratio 3.2 chars/tok calibrated against live count_tokens 2026-06-05: 15,425 chars = 4,730 tok = 3.261), guard wired into `build_intent_router_llm()` ahead of adapter construction, `logger.error` + clear raise message naming the floor and the silent-no-cache trap
- `sidequest-server/sidequest/telemetry/spans/intent_router.py` — `intent_router.cache_floor` span (SpanRoute → GM dashboard via state_transition/intent_router; ERROR status on refusal) + module docstring entry
- `sidequest-server/tests/agents/test_91_3_cache_floor_guard.py` — ruff format only (no logic changes to TEA's tests)

**Tests:** 9/9 unit passing + 1 env-gated live test (run manually: PASSED); full server suite 11,087 passed / 0 failed / 346 skipped (testing-runner run `91-3-dev-green`); ruff + pyright clean
**Branch:** feat/91-3-intent-router-cache-repair (pushed, head d1e2c882)

**Live verification performed during GREEN (operator-gated tests, key present locally):**
- `SIDEQUEST_VERIFY_HAIKU_CACHE_FLOOR=1` → count_tokens says the combined prefix is **4,730 tokens — genuinely above the floor**
- `SIDEQUEST_VERIFY_HAIKU_CACHE_LIVE=1` → the two-turn proof **PASSES through the guarded build**: cache_creation ≥ 4,096 turn 1, cache_read ≥ 4,096 turn 2

**Calibration note:** ratio 3.2 puts the runtime guard's threshold (~13.1k chars) just below the CI tripwire in `test_haiku_cache_control.py` (13.5k chars), so a shrinking prefix fails in CI before the runtime guard would start refusing live sessions.

**Handoff:** To Mr. Praline (TEA) for verify phase

## TEA Assessment

**Tests Required:** Yes
**Reason:** P1 bug fix with concrete, testable contract (build-time fail-loud guard + live cache proof)

**Test Files:**
- `sidequest-server/tests/agents/test_91_3_cache_floor_guard.py` — 10 tests: build-time floor guard (AC1/AC2), combined-prefix semantics, production wiring, `intent_router.cache_floor` OTEL span (AC5), env-gated live two-turn cache proof (AC3/AC4)

**Tests Written:** 10 tests covering 5 ACs
**Status:** RED (6 failing, 3 passing non-regression pins, 1 env-gated skip — verified by testing-runner, run `91-3-tea-red`; no collection errors; sibling `test_haiku_cache_control.py` intact at 5 pass / 1 gated skip)

**Contract for Dev (GREEN):**
1. `IntentRouterCacheFloorError(LlmClientError)` in `sidequest/agents/llm_factory.py`
2. `build_intent_router_llm()` validates the combined tools+system prefix (production `_SYSTEM_PROMPT` + `_dispatch_tool_schema()`, read late-bound through the `intent_router` module) against the 4,096-token floor using an **offline** estimator (per-turn build — no `count_tokens` network call); raises with a message naming the floor and the silent-no-cache trap
3. Calibration is pinned at both ends: the real production prefix (~15.3k chars) must PASS; a tiny prefix must RAISE; system-alone-sub-floor + big schema must PASS (combined semantics — the original defect class)
4. `intent_router.cache_floor` span on every build (pass and fail): `passed`, `floor_tokens=4096`, `estimated_tokens`, `prefix_chars`
5. Aside adapter (`build_aside_llm`) stays unguarded (intentionally uncached)
6. The live repair proof: `SIDEQUEST_VERIFY_HAIKU_CACHE_LIVE=1` + key → two-turn test must show creation>=4096 then read>=4096. **If turn 1 shows creation=0, the prefix is genuinely sub-floor live — repair means growing/restructuring the prefix, not just adding the guard.**

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing — fail-loud contract | `test_build_raises_cache_floor_error_below_floor`, `test_cache_floor_error_message_names_floor_and_trap` | failing (RED) |
| #4 logging/observability on error paths | `test_failing_build_emits_cache_floor_span_before_raising` | failing (RED) |
| #6 test quality — no vacuous assertions | self-check pass: every test asserts specific values/exception types; skip carries reason | n/a |
| #9 async pitfalls — proper awaits, `asyncio.sleep` not `time.sleep` | `test_intent_router_live_cache_write_then_read` | gated skip |
| #10 import hygiene — function-level imports for granular RED (no collection-killing module import) | whole file — verified 0 collection errors | pass |
| Wiring test (CLAUDE.md mandatory) | `test_production_session_build_path_is_floor_guarded` | failing (RED) |

**Rules checked:** 5 of 13 lang-review rules applicable to this test surface have coverage; remainder (paths, deserialization, deps, SQL) not applicable to this change
**Self-check:** 0 vacuous tests found

**Handoff:** To Bicycle Repair Man (Dev) for implementation

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player action → `websocket_session_handler._execute_narration_turn` → `build_intent_router_for_session()` (intent_router_pass.py:79) → `build_intent_router_llm()` → guard reads `intent_router._SYSTEM_PROMPT`/`_dispatch_tool_schema()`/`_TOOL_NAME`/`_TOOL_DESCRIPTION` late-bound → offline estimate vs 4,096-token floor → `intent_router.cache_floor` span → refuse (`IntentRouterCacheFloorError`) or construct adapter → `IntentRouter.decompose` passes the *same* `_SYSTEM_PROMPT` the guard validated into `emit_tool`'s 1h cache marker. Safe because: the guard fires on the per-turn production construction path (cannot be bypassed by production code), the estimate inputs are exactly the constants the call site sends, and failure is a typed loud raise — never a degraded adapter.

**Observations (≥5, tagged):**
1. `[VERIFIED]` Wiring — `test_production_session_build_path_is_floor_guarded` drives the real `build_intent_router_for_session` (intent_router_pass.py:77-79) into the guard raise. Complies with "Verify Wiring, Not Just Existence" + "Every Test Suite Needs a Wiring Test"; no source-text greps anywhere in the new tests.
2. `[VERIFIED]` Fail-loud — sub-floor build raises `IntentRouterCacheFloorError(LlmClientError)` with floor + measurement + remediation in the message, `logger.error` (%-style) before raise. Complies with No Silent Fallbacks and lang-review #1/#4 on the new code.
3. `[VERIFIED]` OTEL — `intent_router.cache_floor` emitted on BOTH paths, registered as a SpanRoute (state_transition/intent_router) so it reaches the live GM dashboard, ERROR status on refusal. Complies with the OTEL Observability Principle; follows the module's established Span.open/SpanRoute pattern (Don't Reinvent).
4. `[VERIFIED]` Import hygiene — `telemetry.spans.intent_router` imports nothing from `agents/`; the estimator's function-level `import sidequest.agents.intent_router` correctly breaks the pre-existing reverse module edge (lang-review #10). The new module-level span import is acyclic.
5. `[TEST]` [MEDIUM] Refusal-span `StatusCode.ERROR` untested — the `set_status` call is invisible to the suite at tests/agents/test_91_3_cache_floor_guard.py (`test_failing_build_emits_cache_floor_span_before_raising`). Non-blocking; delivery finding filed.
6. `[TEST]` [LOW] Exact-boundary (est == 4096) semantics untested; both far ends pinned. `[TEST]` [LOW] live test's `spans[-2]/[-1]` slicing — downgraded from medium: `emit_tool` has no internal retry and the exporter is fixture-scoped, so exactly two `llm.request` spans exist; defensive baseline-slice suggested, not required. `[TEST]` [LOW] local `otel_capture` duplicates tests/agents/conftest.py:64 (existing pattern in both sibling files; consolidation is a cleanup, not a defect).
7. `[DOC]` [LOW] Two RED-phase "Today..." docstrings read false post-merge; calibration char figures (15,425 vs 15,289) lack a one-line scope note (estimator includes tool name+description; tripwire doesn't). Delivery finding filed for a doc-polish pass.
8. `[RULE]` Pre-existing (untouched by diff): bare `except Exception` in `emit_tool`'s usage_repr fallback (lang-review #1/#4) — delivery finding filed; not a story-91-3 regression. `[RULE]` The headline "async test never executes" claim was REFUTED with evidence (pyproject.toml:45 `asyncio_mode="auto"`, pytest banner `Mode.AUTO`, test executed live twice during GREEN).
9. `[EDGE]` `[SILENT]` `[TYPE]` `[SEC]` `[SIMPLE]` — specialists disabled via settings; I covered their domains directly: boundary analysis in Devil's Advocate (estimator false-pass window 13,107–13,353 chars, covered by the stricter CI tripwire + authoritative live test — deliberate, documented layering); no new swallowed errors (guard raises, span context cannot suppress — `with ...: pass` closes before the raise); types are exact (`tuple[int,int]`, typed exception subclass); no security surface (no user input — module constants only); no over-engineering (estimator is four `len()` calls and one division; simplest thing that satisfies the pinned contract).

**Pattern observed:** Good — the guard reuses the established telemetry SpanRoute registration + contextmanager-helper pattern verbatim (sidequest/telemetry/spans/intent_router.py), and the layered-defense ordering (CI tripwire trips at 13,500 chars BEFORE the runtime guard's ~13,107) is explicitly documented in the `_PREFIX_CHARS_PER_TOKEN` comment — calibrated against a live count_tokens measurement with date and figures.

**Error handling:** Sub-floor → ERROR span → logger.error → typed raise; missing API key → `LlmClientError` from `build_async_anthropic` (pre-existing, still reachable after the guard passes); estimator inputs are trusted module constants (no null/user-input surface); an import failure of `intent_router` would propagate loudly (correct — that module is load-bearing for the turn anyway).

**Tenant isolation:** N/A — no tenant-scoped data in this diff (single-operator personal project; no trait methods handling per-tenant data introduced).

**AC verdicts:** AC1/AC2 met (build-time guard, clear message — token-denominated per accepted deviation); AC3/AC4 met and **executed live during GREEN** (creation ≥ 4,096 turn 1, read ≥ 4,096 turn 2 — the cache provably engages; gated out of default CI per epic constraint); AC5 met (guard-decision span both paths + per-call cache fields already pinned by 91-1, proven end-to-end by the live test).

**Handoff:** To The Announcer (SM) for finish-story

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (tests GREEN 33/0/2, ruff pass, 0 new pyright errors, 0 smells, tree clean) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 4 (1 medium, 3 low), dismissed 1 (estimator-arithmetic unit test — covered by both-ends calibration pins; formula is 4 `len()` calls) |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 | confirmed 3 (low), dismissed 2 (see below) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 2 (pre-existing, non-blocking) + 1 low, dismissed 2 |

**All received:** Yes (4 enabled returned, 5 disabled via settings)
**Total findings:** 10 confirmed (0 blocking), 5 dismissed (with rationale), 0 deferred

**Key dismissals (evidence):**
- [RULE] "HIGH: async test missing @pytest.mark.asyncio — body never executes" — **REFUTED**: `pyproject.toml:45` sets `asyncio_mode = "auto"` (pytest header confirms `asyncio: mode=Mode.AUTO`); the live test executed and PASSED twice during GREEN (Dev Assessment) and SKIPS (not errors) in default runs. Finding is factually wrong, not rule-overridden.
- [DOC] "estimator may double-count tool name/description inside schema JSON" — **REFUTED**: `_dispatch_tool_schema()` returns `DispatchPackage.model_json_schema()` (intent_router.py:100), which contains neither the tool name `emit_dispatch_package` nor `_TOOL_DESCRIPTION`; the four addends are disjoint, matching the docstring's component list.
- [TEST] estimator-arithmetic unit test (low) — dismissed: the formula is four `len()` calls; both calibration ends are pinned behaviorally (production passes, tiny raises, combined semantics), per TEA's deliberate contract.
- [RULE] bare `Iterator` fixture annotation (#3) — dismissed as exempt: rule text exempts internal/private helpers; the fixture is module-local test plumbing (and mirrors the conftest original).
- [RULE] check #10 circular import — the rule-checker itself concluded CLEAN after analysis: `telemetry.spans.intent_router` imports nothing from `agents/`; the function-level import in the estimator correctly breaks the `agents/intent_router → llm_factory` cycle.

### Rule Compliance

Per `.pennyfarthing/gates/lang-review/python.md`, enumerated against every changed symbol (`IntentRouterCacheFloorError`, `HAIKU_CACHEABLE_PREFIX_FLOOR_TOKENS`, `_PREFIX_CHARS_PER_TOKEN`, `_estimate_intent_router_prefix_tokens`, `build_intent_router_llm` guard block, `intent_router_cache_floor_span` + SpanRoute, 10 tests):

| Check | Verdict | Evidence |
|-------|---------|----------|
| #1 silent exceptions | PASS (new code) | Guard raises `IntentRouterCacheFloorError`; no suppression. Pre-existing violation at `llm_factory.py` `emit_tool` usage_repr bare-except (untouched by diff) — logged as delivery finding |
| #2 mutable defaults | PASS | 6/6 signatures checked — none |
| #3 annotations | PASS | All new public functions annotated (`tuple[int, int]`, `_IntentRouterLlm`, `Iterator[trace.Span]`); fixture bare-`Iterator` exempt (private test helper) |
| #4 logging | PASS (new code) | `logger.error` (%-style) before raise at guard fail path; pre-existing emit_tool gap logged as delivery finding |
| #5 paths | N/A | No path handling in diff |
| #6 test quality | PASS | 10/10 tests assert specific values/exceptions; skip carries reason; no vacuous assertions |
| #7 resource leaks | PASS | All spans via `with`; fixture try/finally shutdown |
| #8 deserialization | N/A | `json.dumps` is outbound serialization only |
| #9 async pitfalls | PASS | `asyncio_mode="auto"` (pyproject.toml:45); `asyncio.sleep(2)` carries justifying comment; all coroutines awaited |
| #10 import hygiene | PASS | New module-level import `llm_factory → telemetry.spans.intent_router` is acyclic; estimator's function-level `import sidequest.agents.intent_router` correctly breaks the pre-existing reverse edge |
| #11 input validation | N/A | No user-input boundary in diff |
| #12 dependency hygiene | N/A | No dependency changes |
| #13 fix regressions | PASS | New error handling raises specifically; no new broad catches |

Project-rule sweep (CLAUDE.md/SOUL): **No Silent Fallbacks** — guard turns the silent-no-cache API trap into a build-time raise (compliant, the point of the story); **Don't Reinvent** — reuses `Span.open`/`SpanRoute` pattern and existing exception hierarchy (compliant); **Verify Wiring** — guard has a non-test consumer (`build_intent_router_for_session` → `build_intent_router_llm`, intent_router_pass.py:77-79) (compliant); **Wiring test mandatory** — `test_production_session_build_path_is_floor_guarded` exercises the production path (compliant); **No Source-Text Wiring Tests** — all assertions behavioral on exceptions/spans (compliant); **OTEL Observability Principle** — decision span on both paths, routed to GM dashboard via SpanRoute state_transition (compliant).

### Devil's Advocate

Let me argue this code is broken. **First, the guard validates the wrong thing at the wrong time.** It reads module constants at build, but `emit_tool` caches whatever `system` argument it actually receives at call time. A future second caller — or a refactor that parameterizes the prompt — could pass a sub-floor system string through a build that passed the guard, and the marker would silently no-op exactly as before. The guard protects today's single-caller topology, not the adapter's contract. The story title ordained "raise at build," so this is spec-compliant — but it is a real seam a future change can slip through, and nothing in the adapter itself would catch it. **Second, the offline estimator has a false-pass window.** Threshold is 13,107 chars (est 4,096 tok at ratio 3.2), but at the measured true ratio 3.261 the *actual* token count at 13,107 chars is ~4,020 — below the real floor. A prefix shrunk into the 13,107–13,353-char band passes the runtime guard while genuinely sub-floor. The mitigation is deliberate and documented — the CI tripwire at 13,500 chars fires first, and the live count_tokens test is authoritative — but the runtime guard *alone* is not sufficient, and an operator who trusts the `passed=True` span over the tripwire could be misled. **Third, the ERROR status on the refusal span is untested** — `set_status(StatusCode.ERROR, ...)` could be deleted and the suite stays green; the GM panel's at-a-glance error signal is unpinned. **Fourth**, the salted live test writes a fresh 1h cache entry per run — negligible cost, but a sloppy loop running it hourly would silently accumulate cache writes. None of these rise to blocking: the first two are documented, defense-in-depth design choices pinned to the spec, the third is a Medium test gap, the fourth is operational trivia. But the first one deserves a recorded trail — added as delivery finding for the epic.

## Development Notes

### Branch
**Branch Strategy:** gitflow (feat/91-3-intent-router-cache-repair)

### Repository
**Repository:** sidequest-server
**Path:** /Users/slabgorb/Projects/oq-1/sidequest-server

### Workflow Type
This is a **phased workflow** (TDD: setup → red → green → review → finish).
Next agent after setup: **tea** (write failing tests in RED phase)

### Key References
- Epic 91 description: Dark Spend cost observability & cache integrity
- Related: ADR-134 (runaway detector), ADR-101 (Anthropic SDK as narrator backend)
- Local routing epic: parallel story descoping condition