---
story_id: "92-2"
jira_key: ""
epic: "92"
workflow: "tdd"
---
# Story 92-2: Local rung in the model ladder — CallType.CLASSIFICATION/SCRATCH route to Ollama behind explicit config; fail loud if unreachable (NO silent Haiku fallback)

## Story Details
- **ID:** 92-2
- **Jira Key:** (none — Jira not enabled for this project)
- **Workflow:** tdd
- **Stack Parent:** 92-1 (router A/B eval instrument)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-06T04:45:23Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-06T03:59:56Z | 2026-06-06T04:01:08Z | 1m 12s |
| red | 2026-06-06T04:01:08Z | 2026-06-06T04:10:45Z | 9m 37s |
| green | 2026-06-06T04:10:45Z | 2026-06-06T04:23:47Z | 13m 2s |
| review | 2026-06-06T04:23:47Z | 2026-06-06T04:33:07Z | 9m 20s |
| red | 2026-06-06T04:33:07Z | 2026-06-06T04:37:10Z | 4m 3s |
| green | 2026-06-06T04:37:10Z | 2026-06-06T04:40:58Z | 3m 48s |
| review | 2026-06-06T04:40:58Z | 2026-06-06T04:45:23Z | 4m 25s |
| finish | 2026-06-06T04:45:23Z | - | - |

## Sm Assessment

**Repos:** sidequest-server
**Branch:** feat/92-2-local-model-rung (base: develop)
**Workflow:** tdd (phased) → next agent: tea (red phase)

Setup complete. Story 92-2 selected as the highest-leverage p1 in the backlog: routes CallType.CLASSIFICATION/SCRATCH to a local Ollama rung behind explicit config, failing loud if unreachable (No Silent Fallbacks — no silent Haiku fallback). Dependency 92-1 (router A/B eval instrument, server #711) is merged, so there is no false-start risk. Completing this unblocks 92-4 (playtest cost proof) and descopes part of epic-91.

- Jira: skipped — not enabled for this project (JIRA_KEY empty in sprint YAML).
- Story context written and validated: `sprint/context/context-story-92-2.md` (passes `pf validate context-story 92-2`).
- Session file created, branch created in sidequest-server off develop per repos.yaml.

Routing to Amos Burton (TEA) for the RED phase: failing tests covering explicit-config routing, fail-loud unreachable behavior, and the no-fallback invariant per the story ACs.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (blocking): The SCRATCH consumer (dungeon curate, `sidequest/dungeon/materializer.py:1213`) feeds `resolve_model(CallType.SCRATCH)` into `claude_client.complete_with_tools(...)` — an Anthropic-SDK tooling interface. With the rung on, the ladder returns `qwen2.5:7b-instruct`, which the SDK client cannot serve (the API will 404 — loud, $0, but the curate stage degrades every time). Dev must decide the SCRATCH consumer wiring: route the curate call through an Ollama-capable client when the rung is on, or explicitly scope curate out of the rung (and log a deviation). The ladder test (`test_local_rung_resolves_scratch_to_local`) intentionally forces this decision.
  Affects `sidequest/dungeon/materializer.py` (client routing for the SCRATCH call when SIDEQUEST_CLASSIFICATION_BACKEND=ollama).
  *Found by TEA during test design.*
- **Improvement** (non-blocking): `ab_eval_harness.OLLAMA_MODEL` becomes load-bearing for production routing (the A/B-validated model id). Consider moving the constant to `model_routing.py` or `llm_factory.py` with the harness importing it, so production doesn't import from a measurement module. Tests pin equality, not ownership location.
  Affects `sidequest/agents/ab_eval_harness.py` (constant ownership).
  *Found by TEA during test design.*
- **Question** (non-blocking): cost_safety ledger (ADR-134) semantics for the local path are unpinned — local calls are $0 so ceiling/detector participation is arguably moot, but if the team wants local-call volume in the per-session books, Dev should wire `record_call` with cost 0 and a test. Deferred to Dev/Reviewer judgment.
  Affects `sidequest/agents/llm_factory.py` (local adapter ledger participation).
  *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Story 92-3 (asides to local) can reuse this story's seam directly — `classification_backend()` + `build_local_classifier_client()` are both public; the aside adapter only needs the same branch `build_aside_llm` that `build_intent_router_llm` got, plus the prompt-coercion is unnecessary for asides (plain completion, no tool schema). Likely small enough to confirm the epic's "fold into 92-2 if trivial" note was right to keep separate — the config seam exists now, so 92-3 is ~1 point of work.
  Affects `sidequest/agents/llm_factory.py` (`build_aside_llm` branch).
  *Found by Dev during implementation.*
- **Question** (non-blocking): The local intent-router path has no equivalent of the Haiku adapter's cost-ledger `record_call`, so the ADR-134 per-session books see zero router activity when the rung is on. If 91-5's dark-spend reconciliation cross-checks call *counts* (not just dollars), the local rung will look like missing calls rather than $0 calls. Worth a look during 91-5/92-4.
  Affects `sidequest/agents/cost_safety.py` (whether local calls should be booked at cost 0).
  *Found by Dev during implementation.*

### TEA (test design — review rework)
- No new upstream findings during rework test design. The role-boundary fix is local to the two named call sites; `send_with_session` already exists and builds the role-separated `/api/chat` body, so the fix needs no new transport infrastructure.

### Reviewer (code review)
- **Gap** (blocking): The local Ollama path erases the system/user role boundary (`send_stateless` flattens both into one prompt string), raising the prompt-injection surface and the misclassification rate for player actions containing JSON. Must be fixed before the 92-4 live flip so flip-evidence measures the shipped shape.
  Affects `sidequest/agents/llm_factory.py` (`_OllamaIntentRouterLlm.emit_tool`) and `sidequest/dungeon/materializer.py` (curate branch) — switch to `send_with_session` role-separated messages; mirror in `ab_eval_harness.QwenRouterLlm`.
  *Found by Reviewer during code review.*
- **Gap** (non-blocking): Local classification calls emit no `llm.sdk.usage` accounting line — the 91-1 "every call flows through uniform usage accounting" invariant has no local-path equivalent, so 91-5 count-based reconciliation will see a silent zero rather than $0 calls.
  Affects `sidequest/agents/ollama_client.py` / `sidequest/agents/llm_factory.py` (emit a usage line for local calls at $0). Deferred to 91-5/92-4.
  *Found by Reviewer during code review.*

### Reviewer (code review — round 2 / re-review)
- **Gap** (non-blocking): 92-4 must include a curate-on-ollama SUCCESS observation (a `curated=true` region produced by the local model) — the unit suite covers routing + loud-degrade but the success path was deferred from 92-2 with an accepted deviation.
  Affects 92-4 playtest scope (add a local-curate success assertion).
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing `ollama_client` hygiene surfaced (not introduced by this story): `send_with_session(session_id=None)` allocates a never-evicted `_histories` entry (bounded today by per-turn clients), and `_post_chat`'s `envelope.get("message") or {}` mislabels a malformed envelope as a parse failure rather than a transport error. Candidate for a small standalone `ollama_client` story.
  Affects `sidequest/agents/ollama_client.py` (stateless-turn history eviction + envelope-shape guard).
  *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **ACs defined by TEA, not sprint YAML**
  - Spec source: context-story-92-2.md, "Acceptance Criteria" section
  - Spec text: "No acceptance criteria recorded in the sprint YAML — TEA to define during the RED phase."
  - Implementation: TEA derived 9 ACs from the story title + epic-92 doctrine (explicit config, fail-loud, no silent Haiku fallback, A/B-validated model, OTEL observability for 92-4) and pinned them in `tests/agents/test_92_2_local_classification_rung.py`'s module docstring.
  - Rationale: The context file explicitly delegates AC definition to TEA; the epic description and the 92-1 harness docstring ("Building the production adapter is 92-2's job") supply the contract.
  - Severity: minor
  - Forward impact: Dev implements to the test-pinned contract; Reviewer should validate the ACs against the epic doctrine, not the (empty) YAML.
- **Env var name chosen by TEA: SIDEQUEST_CLASSIFICATION_BACKEND**
  - Spec source: epic-92.yaml description
  - Spec text: "the local rung is explicit config, fail-loud if Ollama is unreachable" (no var name given)
  - Implementation: Tests pin `SIDEQUEST_CLASSIFICATION_BACKEND` ∈ {anthropic (default), ollama}, normalized strip+lower, exported as `ENV_CLASSIFICATION_BACKEND` from llm_factory — mirroring the existing `SIDEQUEST_LLM_BACKEND`/`ENV_BACKEND` doctrine.
  - Rationale: Consistency with the existing backend-seam naming; a scoped var (not reusing SIDEQUEST_LLM_BACKEND) keeps the narrator backend and the classification rung independently switchable.
  - Severity: minor
  - Forward impact: If Dev/Reviewer prefer a different name, change tests + impl together in GREEN; 92-3/92-4 will reuse this seam.
- **Unreachable-Ollama failure pinned at call time, not build time**
  - Spec source: epic-92.yaml description
  - Spec text: "fail-loud if Ollama is unreachable"
  - Implementation: Tests assert the typed `OllamaClientError` surfaces from `emit_tool` (first call), not from a build-time reachability probe.
  - Rationale: The adapter is rebuilt every turn (`build_intent_router_for_session`); a build-time HTTP probe would add a per-turn round-trip for no benefit (same reasoning as the 91-3 offline floor estimate). Call-time failure is equally loud and turn-scoped.
  - Severity: minor
  - Forward impact: none — if Dev adds a probe anyway, the call-time tests still hold.

### TEA (test design — review rework round-trip 1)
- **Role-boundary RED tests pin the fix transport, not a probe**
  - Spec source: Reviewer Assessment [SEC][HIGH], session file
  - Spec text: "Use `send_with_session(prompt=user, system_prompt=system+coercion, session_id=None)` to build a role-separated `/api/chat` messages array"
  - Implementation: The two new tests capture the actual HTTP request body (`req.data`) and assert role separation in the `messages` array — they do NOT assert "send_with_session was called" (that would be a source-shape test). Any transport that yields a role-separated body passes.
  - Rationale: No Source-Text Wiring Tests — assert the observable wire behavior, not the call site. Survives a refactor that achieves role separation a different way.
  - Severity: minor
  - Forward impact: none — Dev is free to fix via send_with_session or any role-preserving path.
- **Curate success-path test deferred to 92-4 (explicit deviation per Reviewer)**
  - Spec source: Reviewer Assessment "Recommended in the same rework", session file
  - Spec text: "Add a curate success-path test (valid local verdict → curated=True), or log an explicit deviation deferring it to 92-4."
  - Implementation: NOT added. The curate rework test asserts role separation on the request; the loud-degrade path is already covered. A success-path test requires a hand-built valid curation verdict keyed to the real beneath_sunden manifest (creature CR/Edge-translatable rows) — disproportionate fixture work for a path 92-4 exercises against a live model.
  - Rationale: Reviewer explicitly permitted deferral-with-deviation; the blocking finding (role boundary) is fully covered; 92-4's playtest is the natural success-path proof.
  - Severity: minor
  - Forward impact: 92-4 must include a curate-on-ollama success observation (a curated=true region from the local model). Captured as a forward note for 92-4.

### Dev (implementation — review rework round-trip 1)
- **Role boundary restored via send_with_session at both local call sites + harness mirror**
  - Spec source: Reviewer Assessment [SEC][HIGH], session file
  - Spec text: "Use `send_with_session(prompt=user, system_prompt=system+coercion, session_id=None, model=...)` ... Mirror the change (or drive the production adapter) in `QwenRouterLlm`."
  - Implementation: Replaced `send_stateless` with `send_with_session(... session_id=None)` in `_OllamaIntentRouterLlm.emit_tool` (`llm_factory.py`), the curate branch (`materializer.py`), and `QwenRouterLlm.emit_tool` (`ab_eval_harness.py`). `send_with_session` is on the `LlmClient` protocol (`claude_client.py:829`), so the harness's generic-client contract is unbroken.
  - Rationale: Exactly the reviewer-prescribed fix; the role-separated `/api/chat` messages array keeps player text in `role: user`, never adjacent to the JSON-coercion instructions.
  - Severity: minor (resolves a HIGH finding)
  - Forward impact: 92-4 flip-evidence now measures the shipped role-separated shape. The pre-existing `send_stateless` history-leak the reviewer noted no longer applies to these call sites (they were the new exercisers); `send_with_session(session_id=None)` still allocates an ephemeral history entry — that pre-existing `ollama_client` hygiene item is unchanged and remains a candidate for a separate small story.

### Dev (implementation)
- **Tightened the prose-only emit_tool test from blind Exception to LlmClientError**
  - Spec source: tests/agents/test_92_2_local_classification_rung.py, AC4 (`test_emit_tool_raises_on_prose_only_response`)
  - Spec text: "with pytest.raises(Exception)" (TEA's RED version)
  - Implementation: Changed to `pytest.raises(LlmClientError)` — the adapter raises `IntentRouterEmptyResponse` (an `LlmClientError`), reusing the existing no-usable-output error family.
  - Rationale: ruff B017 forbids blind `Exception` asserts; pinning the typed family is strictly stronger than TEA's pin, not weaker.
  - Severity: minor
  - Forward impact: none.
- **SCRATCH consumer wired to the local rung inside the curate one-shot (Dev-added tests)**
  - Spec source: session file story title + TEA blocking Delivery Finding
  - Spec text: "CallType.CLASSIFICATION/SCRATCH route to Ollama behind explicit config" / "Dev must decide the SCRATCH consumer wiring"
  - Implementation: `_one_attempt` in `materializer.py` consults `classification_backend()` per attempt; ollama → `build_local_classifier_client().send_stateless(...)` (curate is a plain completion, tools=[]), failures flow the existing ADR-106 Amendment A retry→degrade ladder; default path unchanged. Dev added the wiring tests TEA's finding asked for (`tests/dungeon/test_92_2_scratch_curate_local.py`, 2 tests) rather than leaving the flag-on curate path to 404 against Anthropic (half-wired feature).
  - Rationale: The epic counts SCRATCH callers in the workload moving off Anthropic billing; "No half-wired features" forbids shipping the rung with curate permanently degrading. An unknown env value raises `ValueError` outside the ladder's catch — config typos abort loudly, they do not degrade.
  - Severity: minor
  - Forward impact: 92-4's playtest will see `agent.backend=ollama` spans from curate as well as the intent router.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-point p1 feature story; new config seam + routing behavior + fail-loud invariants.

**Test Files:**
- `sidequest-server/tests/agents/test_92_2_local_classification_rung.py` — 22 tests pinning the 92-2 contract (9 TEA-defined ACs, documented in the module docstring)

**Tests Written:** 22 tests covering 9 ACs (commit `e51f32c` on `feat/92-2-local-model-rung`)
**Status:** RED (15 failing — ready for Dev). 7 tests pass BY DESIGN: they are default-off regression pins of *current* behavior (Haiku default, narration tiers untouched, session_id keyword contract, production wiring default) — they exist so Dev's change cannot move the default, honoring the epic's "no routing flip by default" hard gate.

**AC map (test groups):**
1. AC1 explicit config, default OFF — env constant + default/`anthropic` keep Haiku exactly
2. AC2 ladder local rung — CLASSIFICATION/SCRATCH → `ab_eval_harness.OLLAMA_MODEL` (the A/B-validated model); narration untouched; pack overrides still win
3. AC3 factory routes local — no ANTHROPIC_API_KEY needed; Anthropic construction site (91-1 sentinel) untouched; value normalization; session_id stays required keyword-only
4. AC4 emit_tool — prompt-coerced JSON through `ollama_client` transport (urlopen seam); prose-only response raises, never returns `{}`
5. AC5 fail loud unreachable — typed `OllamaClientError`; sentinel proves NO Haiku fallback through build + failing call
6. AC6 unknown config value fails loud at ladder AND factory, naming the env var
7. AC7 91-3 cache-floor guard is Haiku-only (sub-floor prefix must not refuse a local build — frees 82-10)
8. AC8 wiring — `build_intent_router_for_session` honors the seam both ways
9. AC9 OTEL — successful local call emits `agent.backend=ollama` span (92-4's verification consumes these)

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions / fallbacks | `test_unreachable_ollama_never_falls_back_to_haiku`, `test_unknown_classification_backend_fails_loud_at_{ladder,factory}`, `test_emit_tool_raises_on_prose_only_response` | failing (RED) |
| #3 boundary type contracts | `test_session_id_remains_required_keyword_only_on_local_path`, `test_env_classification_backend_constant_exported` | 1 passing (pin), 1 failing |
| #4 logging/observability | `test_emit_tool_emits_backend_ollama_span` (OTEL principle) | failing (RED) |
| #6 test quality | Self-check below | done |
| #9 async pitfalls | All `emit_tool` tests await the coroutine end-to-end through the transport seam | failing (RED) |
| #11 input validation at boundaries | env-value normalize-then-gate tests (`test_factory_ollama_value_is_normalized`, unknown-value tests) | failing (RED) |

**Rules checked:** 6 of 13 lang-review rules applicable to this surface have test coverage; the rest (paths, deserialization, deps, resources) don't apply to this diff.
**Self-check:** 0 vacuous tests — every test asserts a specific value, type, raise, or recorded-calls list; the span test asserts the attribute value, not just span existence.

**Wiring tests:** `test_wiring_session_factory_builds_local_router` / `..._default_remains_haiku` verify the production per-turn entry point (`build_intent_router_for_session`, called from `websocket_session_handler`) honors the seam — not just the factory unit.

**Handoff:** To Naomi Nagata (Dev) for GREEN. Key Dev notes: (1) the production adapter should reuse `ollama_client` transport per Don't-Reinvent (the 92-1 `QwenRouterLlm` is the measurement-only template; its docstring names 92-2 for the production version); (2) see blocking Delivery Finding on the SCRATCH consumer (dungeon curate) client routing; (3) `_install_anthropic_sentinel` relies on the 91-1 late-bound lookup doctrine — keep `build_async_anthropic` lookups late-bound.

### TEA Assessment — Review Rework (round-trip 1)

**Tests Required:** Yes (Reviewer REJECT — [SEC][HIGH] role boundary + [TEST] vacuous assertions)
**Status:** RED (2 new failing tests, 25 passing) — commit `186e5f8`.

**New RED tests (must drive the fix):**
- `tests/agents/test_92_2_local_classification_rung.py::test_emit_tool_preserves_system_user_role_boundary` — router path. Captures the `/api/chat` request body; asserts player text (incl. an embedded JSON injection payload) lands ONLY in a `role: user` message and `system`+coercion ONLY in `role: system`. Fails now (`roles=['user']` — flattened).
- `tests/dungeon/test_92_2_scratch_curate_local.py::test_curate_local_preserves_system_user_role_boundary` — curate path. Same wire-body assertion; the curate instruction must be `role: system`, not folded into the manifest user turn. Fails now (`roles=['user']`).

**Assertion tightening (now passing — pin the fix, no production change):**
- `test_cache_floor_guard_not_applied_to_local_path`, `test_factory_ollama_builds_local_adapter_without_api_key`, `test_factory_ollama_value_is_normalized` → all now assert `isinstance(adapter, _OllamaIntentRouterLlm)` (was vacuous `is not None` / negative-isinstance).

**New coverage (reviewer-recommended):**
- `test_local_classifier_client_honors_ollama_url_env` — proves `SIDEQUEST_OLLAMA_URL` reaches `OllamaClient._base_url`.

**Deferred (with deviation):** curate success-path test → 92-4 live proof (see Design Deviations).

**Fix for Dev:** In `_OllamaIntentRouterLlm.emit_tool` (`llm_factory.py`) and the curate branch (`materializer.py`), replace `send_stateless(system_prompt=…, user_message=…)` with `send_with_session(prompt=<user/manifest>, system_prompt=<system+coercion / curate instruction>, session_id=None, model=…)`. Mirror the change in `ab_eval_harness.QwenRouterLlm` so 92-4 flip-evidence measures the shipped role-separated shape. The role-boundary tests pin the wire behavior, not the call site — any role-preserving transport satisfies them.

**Handoff:** To Naomi Nagata (Dev) for GREEN rework.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/agents/model_routing.py` — `SIDEQUEST_CLASSIFICATION_BACKEND` seam (`ENV_CLASSIFICATION_BACKEND`, `classification_backend()`, `UnknownClassificationBackend`), `LOCAL_CLASSIFIER_MODEL` constant (A/B-validated id, single source), local rung in `resolve_model` for CLASSIFICATION/SCRATCH (after pack overrides; narration never consults the seam)
- `sidequest/agents/ab_eval_harness.py` — `OLLAMA_MODEL` now imports `LOCAL_CLASSIFIER_MODEL` (instrument and rung cannot drift; resolves TEA's non-blocking Improvement finding)
- `sidequest/agents/llm_factory.py` — re-exports `ENV_CLASSIFICATION_BACKEND`; `build_local_classifier_client()` (shared OllamaClient builder); `_OllamaIntentRouterLlm` production adapter (prompt-coerced JSON, `_extract_json_object` raising `IntentRouterEmptyResponse`); `build_intent_router_llm` gates on the seam (unknown → `UnknownBackend`), Ollama branch returns before the Haiku-only 91-3 cache-floor guard
- `sidequest/dungeon/materializer.py` — curate `_one_attempt` consults the seam: ollama → local `send_stateless`, failures flow the existing loud retry→degrade ladder; injected Anthropic client untouched on the local path (resolves TEA's blocking SCRATCH finding)
- `tests/agents/test_92_2_local_classification_rung.py` — prose-only test tightened to `LlmClientError` (ruff B017; logged as deviation)
- `tests/dungeon/test_92_2_scratch_curate_local.py` — NEW: 2 fixture-driven wiring tests for the SCRATCH consumer (rung-on routes Ollama + degrades loud; default still targets the injected client)

**Tests:** 22/22 story tests passing; 2,359 passed across `tests/agents` + `tests/dungeon` serial sweep (`-n0`, OTEL-deadlock-safe), 0 failed, 2 pre-existing skips. Lint clean (`ruff check`/`format`); pyright errors at `llm_factory.py:482-483` and `ab_eval_harness` are pre-existing SDK-union noise, none introduced by this diff.
**Branch:** feat/92-2-local-model-rung (pushed; commits `e51f32c` RED, `16bcde1` GREEN)

**Handoff:** To Amos Burton (TEA) for verify (simplify + quality-pass).

## Dev Assessment — Review Rework (round-trip 1)

**Implementation Complete:** Yes
**Reviewer findings addressed:**
- [SEC][HIGH] role boundary erased → FIXED. `send_stateless` → `send_with_session(prompt=user, system_prompt=system+coercion, session_id=None)` at both production call sites (`_OllamaIntentRouterLlm.emit_tool` in `llm_factory.py`; curate branch in `materializer.py`) and the measurement adapter (`QwenRouterLlm.emit_tool` in `ab_eval_harness.py`). The two TEA RED role-boundary tests now PASS (player text isolated in `role: user`; system+coercion in `role: system`).
- [TEST] vacuous/negative-isinstance assertions → FIXED in the RED-rework phase by TEA (positive `isinstance(_OllamaIntentRouterLlm)`); confirmed green.
- [TEST][MEDIUM] `SIDEQUEST_OLLAMA_URL` coverage → added (`test_local_classifier_client_honors_ollama_url_env`), green.
- [TEST][MEDIUM] curate success-path → deferred to 92-4 with an explicit TEA deviation (reviewer-permitted).
- [SILENT][MEDIUM] local usage-accounting gap → deferred to 91-5/92-4 (Delivery Finding on file); out of scope for the HIGH fix.

**Files Changed (this round):**
- `sidequest/agents/llm_factory.py` — `_OllamaIntentRouterLlm.emit_tool` role-separated transport
- `sidequest/dungeon/materializer.py` — curate branch role-separated transport
- `sidequest/agents/ab_eval_harness.py` — `QwenRouterLlm.emit_tool` mirror (measurement = production shape)

**Tests:** 2 role-boundary tests now GREEN; 2,362 passed across `tests/agents` + `tests/dungeon` (`-n0`), 0 failed, 2 pre-existing skips. Lint/format clean. No regression from the harness mirror (`send_with_session` is on the `LlmClient` protocol).
**Branch:** feat/92-2-local-model-rung (pushed; rework commits `186e5f8` RED, `4b756d6` GREEN fix)

**Handoff:** To Chrisjen Avasarala (Reviewer) for re-review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 8 (1 self-confirmed-handled) | confirmed 3 as LOW notes, dismissed 4, N/A 1 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 1 (deferred to 91-5/92-4), dismissed 1, noted 2 pre-existing |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 4, dismissed 1, deferred 2 |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 3 | confirmed 1 HIGH + 1 LOW note, dismissed 1 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled via settings)
**Total findings:** 9 confirmed (1 HIGH, 3 MEDIUM, 5 LOW notes), 7 dismissed (with rationale), 3 deferred

### Dismissals (with evidence)
- [EDGE] `_extract_json_object` returns `{}` / array-fragment dicts → DISMISSED: `DispatchPackage.model_validate` at `intent_router.py:383` requires `turn_id` + `confidence_global` (no defaults, `protocol/dispatch.py:219-222`) — empty/fragment objects fail validation and flow the retry/failure taxonomy.
- [EDGE] `system_blocks[0]` IndexError → DISMISSED: `system_blocks` is a one-element literal constructed 10 lines above (`materializer.py:1194-1203`); it cannot be empty.
- [EDGE] `json.dumps(tool_schema)` TypeError → DISMISSED: schema comes from `DispatchPackage.model_json_schema()` (`intent_router.py:_dispatch_tool_schema`), always JSON-serializable.
- [EDGE] mid-retry env mutation TOCTOU → DISMISSED: `os.environ` is process-static in production; per-call env reads are the established pattern (`build_llm_client` reads `ENV_BACKEND` per call, `llm_factory.py:185`), and the failure mode if it ever happened is loud (`UnknownModel`).
- [SILENT] mid-attempt double env read → DISMISSED as failure mode (same rationale), retained as LOW simplification note below.
- [TEST] narration test uses `startswith("claude-")` not exact ids → DISMISSED: the contract under test is "narration stays on the Anthropic family"; exact-id pins would false-fail on routine model upgrades that don't concern this seam.
- [SEC] tool schema embedded verbatim in prompt → DISMISSED as design-inherent: prompt-coercion with embedded schema is exactly the shape the 92-1 A/B gate measures (`QwenRouterLlm`), and the dispatch bank's precondition/unregistered gates (ADR-123) bound what a crafted package can do. Retained as context for the HIGH finding.

### Rule Compliance (python.md lang-review, applied to this diff)
- **#1 silent exceptions:** COMPLIANT — every new error path raises typed errors (`UnknownClassificationBackend`, `UnknownBackend`, `IntentRouterEmptyResponse`, `OllamaClientError`); curate failures flow the loud degrade ladder (ERROR log + routed span, pre-existing `materializer.py` Layer 2).
- **#2 mutable defaults:** COMPLIANT — no mutable defaults in any new signature (`classification_backend()`, `resolve_model`, `build_local_classifier_client()`, `_OllamaIntentRouterLlm.__init__`, `emit_tool`).
- **#3 type annotations:** COMPLIANT — all new public functions fully annotated (`classification_backend() -> str`, `build_local_classifier_client() -> OllamaClient`, `emit_tool(...) -> dict[str, Any]`, `build_intent_router_llm(...) -> _IntentRouterLlm | _OllamaIntentRouterLlm`).
- **#4 logging:** PARTIAL — config errors raise (callers log); the local path's usage accounting gap is the deferred [SILENT] finding (no `llm.sdk.usage` line for Ollama calls — deferred to 91-5/92-4 with Delivery Finding already on file).
- **#6 test quality:** VIOLATION (LOW) — `test_cache_floor_guard_not_applied_to_local_path` asserts `adapter is not None` (vacuous; the function cannot return None); two tests use negative-isinstance instead of positive `_OllamaIntentRouterLlm` checks. Rule-matching — must fix, cannot dismiss.
- **#9 async pitfalls:** COMPLIANT — `emit_tool`/`send_stateless` awaited end-to-end; blocking urllib runs in `asyncio.to_thread` (pre-existing `ollama_client.py:105`).
- **#10 import hygiene:** COMPLIANT — explicit `as` re-export for `ENV_CLASSIFICATION_BACKEND`; function-level imports in `_one_attempt` documented (lazy, avoids module-load weight); no cycles (`model_routing` is dependency-free; verified `ab_eval_harness` → `model_routing` is acyclic).
- **#11 input validation at boundaries:** VIOLATION (HIGH) — see [SEC] finding: player text crosses into the local model with the system/user role boundary erased.
- **#5/#7/#8/#12:** N/A to this diff (no path handling, resources are context-managed in pre-existing transport, no deserialization of untrusted input beyond json.loads-with-pydantic-gate, no dependency changes).

### Observations (own review + confirmed subagent findings)
1. [VERIFIED] Default-off hard gate holds — `model_routing.py:96-99`: the rung consults the seam only for CLASSIFICATION/SCRATCH and only after pack overrides; env unset → `_DEFAULT` Haiku ids; pinned by `test_default_classification_resolves_to_haiku` with exact-id asserts. Complies with epic "no flip by default" + No Silent Fallbacks.
2. [VERIFIED] No-Haiku-fallback invariant is structurally proven — `_install_anthropic_sentinel` patches the single 91-1 construction site (`build_async_anthropic`), and `test_unreachable_ollama_never_falls_back_to_haiku` asserts the sentinel list stays empty through build + failing call. Complies with `feedback_no_fallbacks_hard`.
3. [VERIFIED] Single-source model id — `LOCAL_CLASSIFIER_MODEL` owned by `model_routing.py:30`, imported by `ab_eval_harness.py:43` (`OLLAMA_MODEL = LOCAL_CLASSIFIER_MODEL`); instrument and rung cannot drift. Complies with the 92-1-evidence-binding doctrine in the epic.
4. [VERIFIED] Cache-floor guard scoping — `llm_factory.py:618-625`: the ollama branch returns before `_estimate_intent_router_prefix_tokens()`; the 91-3 guard remains on the Haiku path only (sub-floor + ollama builds fine; sub-floor + default still refuses; both pinned).
5. [SEC][HIGH] Role boundary erased on the local path — `emit_tool` (`llm_factory.py:585`) and the curate branch (`materializer.py:1222`) call `send_stateless`, which flattens system+user into ONE prompt string (`ollama_client.py:197: combined = f"{system_prompt}\n\n{user_message}"`). The Haiku/SDK path keeps system and user structurally separate roles; the local path hands the model an undivided string where player-authored text sits adjacent to the JSON-coercion instructions. ADR-047's sanitizer (applied upstream) does not strip JSON-shaped player text, so a player action containing a well-formed JSON object materially raises both the injection surface AND the misclassification rate — and a misclassified dispatch is a SOUL/agency problem per the epic's own hard gate. **The fix is one line per call site:** `send_with_session(prompt=user, system_prompt=system+coercion, session_id=None, model=...)` builds a proper role-separated `/api/chat` messages array (`ollama_client.py:145-150`) — same transport, same endpoint, structural boundary restored. The A/B harness (`QwenRouterLlm`) should make the same change (or better, drive the production adapter) so measurement shape = production shape before the 92-4 flip evidence is collected.
6. [TEST][LOW] Vacuous assert — `test_cache_floor_guard_not_applied_to_local_path` ends `assert adapter is not None`; must assert `isinstance(adapter, _OllamaIntentRouterLlm)`. Same positive-isinstance fix for `test_factory_ollama_builds_local_adapter_without_api_key` and `test_factory_ollama_value_is_normalized` (negative-isinstance passes for any stub). Rule-matching (#6), not dismissible.
7. [TEST][MEDIUM] `SIDEQUEST_OLLAMA_URL` wiring untested — `build_local_classifier_client()` reads the env var but no test proves a custom URL reaches `OllamaClient._base_url`/the request URL. An operator pointing at a non-default port has zero coverage.
8. [TEST][MEDIUM] Curate success path untested — the SCRATCH wiring tests prove routing + loud degrade, but no test shows a VALID local verdict producing `curated=True` through `_parse_curation_verdict`. Recommend adding (reflecting-fake pattern exists); acceptable to defer to 92-4's live proof only with an explicit deviation.
9. [SILENT][MEDIUM→deferred] Local calls invisible to the usage books — no `llm.sdk.usage` line, no ledger feed for Ollama calls (token counts ride span attributes only). Documented-by-intent in the adapter docstring and already captured as a Dev Delivery Finding pointing at 91-5/92-4. Deferred, not blocking this story.
10. [EDGE][LOW] notes (non-blocking): whitespace-only env value raises with an opaque `'   ' not supported` message (correct but unhelpful); garbage `SIDEQUEST_OLLAMA_URL` fails loud but the transport error doesn't name the env var; `resolve_model(CallType.SCRATCH)` inside the ollama guard is a constant — fold to `LOCAL_CLASSIFIER_MODEL` or snapshot the backend once per attempt. [SILENT][LOW] pre-existing: `send_stateless` leaks one `_histories` entry per call (bounded — clients are per-turn, `intent_router_pass.py:57` docstring) and `_post_chat` maps a missing `message.content` to `text=""` (loud one layer up, mislabeled). Both predate this diff; candidates for a small ollama_client hygiene story.
11. [DOC]/[TYPE]/[SIMPLE]/[RULE]: specialists disabled via settings; covered by my own pass — docstrings are accurate and story-stamped (checked all new ones against behavior), the union return type on `build_intent_router_llm` is honest, no dead code introduced, rule sweep done by hand in Rule Compliance above.

**Data flow traced:** player action text → `sanitize_player_text` (`player_action.py`) → `execute_intent_router_pre_narrator_pass` → `build_intent_router_for_session` → seam (`classification_backend()`) → `_OllamaIntentRouterLlm.emit_tool` → `send_stateless` (**flattens roles — the HIGH**) → local qwen → `_extract_json_object` → `DispatchPackage.model_validate` (`intent_router.py:383`, the semantic gate) → dispatch bank precondition gates (ADR-123). Loud at every failure point; the weakness is the flattened boundary, not a silent path.

### Devil's Advocate
Suppose this code is broken and I approved it anyway — where does it bite? First: James types an action that happens to contain a JSON-looking flourish — or deliberately pastes `{"turn_id":"x","confidence_global":1.0,"per_player":[...]}` to see what happens, because players poke systems. On the Haiku path the SDK's role separation keeps that string firmly inside the user message; qwen-7B on a flattened single-string prompt, instructed to "respond with ONLY a single JSON object," is far more suggestible — it may echo the player's object, and `_extract_json_object`'s first-`{`-to-last-`}` grab will happily lift it. The pydantic gate (`DispatchPackage.model_validate`) and the ADR-123 precondition gates stop the *worst* outcomes (a malformed package fails loud; a dispatch with no registered handler is dropped), so this is not arbitrary code execution — but a *well-formed* crafted package can still bias which subsystems fire and at what confidence, and that is precisely the "misclassified dispatch is a SOUL/agency problem" the epic names as its hard gate. Second failure mode: a stressed operator points `SIDEQUEST_OLLAMA_URL` at a dead port; that path fails loud (`OllamaClientError`), good, but the error never names the env var, so the 2am debugging session is longer than it should be — annoyance, not breakage. Third: the curate path on the rung degrades loudly to uncurated on a bad verdict, which is correct, but I have NO test proving a *good* local verdict produces curated content — so "it works when qwen behaves" is asserted by nobody. Fourth, the quiet one: every local classification call is invisible to the usage books. Epic 91's entire thesis is "a call we cannot account for is dark spend"; we are about to route the single highest-frequency caller to a path that emits no `llm.sdk.usage` line at all. It bills $0, yes — but 91-5's reconciliation cross-checks call *counts*, and a silent zero looks identical to a caller that vanished. None of these are catastrophic, but two of them are rule-matching (the role boundary against #11, the vacuous assertion against #6) and the guidance is explicit that rule-matching findings may not be dismissed. The cheap fix exists today — `send_with_session` already builds a role-separated `/api/chat` messages array; using it instead of `send_stateless` is one line per call site and it makes the 92-4 flip-evidence valid by measuring the shape we actually ship. Fix it now while it costs nothing.

### Reviewer (audit) — Design Deviation stamps
- **ACs defined by TEA, not sprint YAML** → ✓ ACCEPTED: context file explicitly delegates AC definition to TEA; the 9 derived ACs faithfully track the epic doctrine.
- **Env var name `SIDEQUEST_CLASSIFICATION_BACKEND`** → ✓ ACCEPTED: mirrors the existing `SIDEQUEST_LLM_BACKEND`/`ENV_BACKEND` seam doctrine; a scoped var keeps narrator and classifier independently switchable.
- **Unreachable-Ollama failure pinned at call time, not build time** → ✓ ACCEPTED: per-turn adapter rebuild makes a build-time probe a wasted round-trip; call-time `OllamaClientError` is equally loud.
- **Prose-only emit_tool test tightened to `LlmClientError`** → ✓ ACCEPTED: strictly stronger than the blind-`Exception` RED pin; satisfies ruff B017.
- **SCRATCH consumer wired into the curate one-shot (Dev-added tests)** → ✓ ACCEPTED in intent (resolving the half-wired curate path was correct), but the *implementation* carries the HIGH role-boundary finding below — the wiring should use the role-separated transport. Re-stamp on rework.
- **UNDOCUMENTED (Reviewer):** The local path emits no `llm.sdk.usage` accounting line — the 91-1 choke-point invariant ("every Anthropic call flows through uniform usage accounting") has no local-path equivalent. TEA/Dev captured the ledger/ceiling gap but not the *log-line* gap. Severity: MEDIUM, deferred to 91-5/92-4. Logged as a blocking Delivery Finding below.

## Prior Review — Round 1 (REJECTED, superseded by the Reviewer Assessment below)

**Verdict (round 1, superseded):** REJECTED

The story's spine is correct and genuinely well-built: the seam is off by default with an exact-id regression pin, the no-Haiku-fallback invariant is *structurally* proven via the 91-1 construction-site sentinel, the unknown-config and unreachable paths fail loud, and the single-source model id binds the rung to the 92-1 evidence. I traced player input end-to-end and every failure point is loud. But two rule-matching findings block approval — and the guidance is explicit that rule-matching findings may not be dismissed.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [SEC][HIGH] | Role boundary erased on the local path: `send_stateless` flattens system+coercion and player text into one undivided prompt string (`ollama_client.py:197`). qwen is instructed to emit ONLY a JSON object; a player action containing well-formed JSON raises both the prompt-injection surface and the misclassification rate (a SOUL/agency problem per the epic). Rule #11 (input validation at boundaries). | `llm_factory.py:585` (`_OllamaIntentRouterLlm.emit_tool`), `materializer.py:1222` (curate branch) | Use `send_with_session(prompt=user, system_prompt=system+coercion, session_id=None, model=...)` to build a role-separated `/api/chat` messages array — same transport/endpoint, structural boundary restored. Add a RED test asserting player-supplied JSON does not become the returned dispatch (role separation holds). Mirror the change (or drive the production adapter) in `QwenRouterLlm` so 92-4 flip-evidence measures the shipped shape. |
| [TEST][LOW→must-fix] | Vacuous assertion `adapter is not None` (function cannot return None); two sibling tests use negative-isinstance. Rule #6 (test quality). | `test_92_2_local_classification_rung.py` (`test_cache_floor_guard_not_applied_to_local_path`, `test_factory_ollama_builds_local_adapter_without_api_key`, `test_factory_ollama_value_is_normalized`) | Assert `isinstance(adapter, _OllamaIntentRouterLlm)` (positive type confirmation). |

**Recommended in the same rework (non-blocking but cheap):**
- [TEST][MEDIUM] Add a `SIDEQUEST_OLLAMA_URL`-honored test (custom URL reaches `OllamaClient._base_url`).
- [TEST][MEDIUM] Add a curate *success*-path test (valid local verdict → `curated=True`), or log an explicit deviation deferring it to 92-4.
- [EDGE][LOW] Fold `resolve_model(CallType.SCRATCH)` inside the ollama guard to `LOCAL_CLASSIFIER_MODEL` (it's a constant there) or snapshot `classification_backend()` once per attempt.

**Dispatch tags:** [EDGE] empty-env/garbage-URL/TOCTOU notes (LOW, mostly dismissed — backstopped by loud failure); [SILENT] usage-accounting gap (MEDIUM, deferred to 91-5/92-4) + pre-existing `send_stateless` history leak (LOW, predates diff); [TEST] vacuous + missing-coverage findings (one must-fix, rest recommended); [DOC] N/A (specialist disabled; my pass found docstrings accurate and story-stamped); [TYPE] N/A (disabled; union return type is honest, hand-checked); [SEC] role-boundary HIGH (blocking) + embedded-schema LOW (dismissed, design-inherent, ADR-123-bounded); [SIMPLE] N/A (disabled; no dead code, the double env-read is the only [EDGE][LOW] simplification note); [RULE] N/A (disabled; full hand sweep in Rule Compliance above — #6 and #11 are the violations driving this verdict).

**Data flow traced:** player text → `sanitize_player_text` → router pass → seam → `emit_tool` → `send_stateless` (**flattens roles — the HIGH**) → qwen → `_extract_json_object` → `DispatchPackage.model_validate` (semantic gate) → ADR-123 dispatch gates. Loud at every failure; the weakness is the flattened boundary, not a silent path.

**Handoff:** Back to Amos Burton (TEA) for red rework — the role-separation fix needs a failing test first, and the test-quality fixes are TEA's lane.

## Subagent Results

(Round 2 re-review — focused on the rework delta `git diff 16bcde1...HEAD`: three production lines, `send_stateless` → `send_with_session` at the two local call sites + the `QwenRouterLlm` mirror, plus the rework tests. Specialists whose domain the delta does not touch are carried from the round-1 fan-out with rationale.)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes (round 2) | clean | 0 | N/A — lint clean, 27/27 story tests green incl. both role-boundary tests |
| 2 | reviewer-edge-hunter | Yes (round 2) | findings | 2 | confirmed param-mapping CORRECT; 2 findings both pre-existing `ollama_client` LOW (history leak, empty-system guard) — dismissed as not-introduced + bounded |
| 3 | reviewer-silent-failure-hunter | Yes (round 2) | findings | 2 | Q1–Q3 invariants CONFIRMED (unreachable still loud; no new swallow; tests honest); 2 findings pre-existing LOW — dismissed as not-introduced |
| 4 | reviewer-test-analyzer | Carried (round 1) | findings | — | The must-fix [TEST] finding (vacuous/negative-isinstance) is RESOLVED this round (positive `isinstance(_OllamaIntentRouterLlm)`, confirmed green by round-2 preflight); recommended OLLAMA_URL coverage ADDED; curate success-path deferred with deviation. No new test surface in the delta beyond the role-boundary tests, which I verified honest myself. |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Carried (round 1) | findings | — | The round-1 [SEC][HIGH] role-boundary finding is the EXACT thing this delta fixes; I verified the fix restores role separation (silent-failure Q3 + my own read of the captured-body tests). No new security surface introduced. |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (3 ran fresh on the delta, 2 carried from round 1 with rationale, 4 disabled via settings)
**Total findings:** 0 new blocking; 2 pre-existing LOW dismissed (not introduced); prior HIGH + must-fix TEST both resolved.

### Round-2 dismissals (with evidence)
- [EDGE]/[SILENT] `_histories` leak on `send_with_session(session_id=None)` → DISMISSED (not introduced): `send_stateless` already delegated to `send_with_session(session_id=None)` (`ollama_client.py:197-205`), so the diff changes no allocation behavior; in current wiring the client is per-turn (`build_intent_router_for_session` rebuilds per turn; curate builds fresh per `_one_attempt`) and GC'd, so it is bounded. Pre-existing `ollama_client` hygiene — candidate for a separate story, already noted round 1.
- [EDGE] empty-`system_prompt` guard omits the system role → DISMISSED: at both call sites `system_prompt = system + coercion` where `coercion` is a multi-line non-empty literal constant — the degenerate empty case is unreachable from production.
- [SILENT] `envelope.get("message") or {}` mis-attributes a malformed Ollama envelope as a parse failure → DISMISSED (not introduced + loud): pre-existing in `_post_chat`; both transports funnel through it; the failure is still surfaced loudly one frame later (`IntentRouterEmptyResponse`/`CurationError`), only the OTEL `failure_kind` label is imprecise. Candidate for the same hygiene story.

### Reviewer (audit) — Round-2 Design Deviation stamps
- **TEA: Role-boundary RED tests pin the fix transport, not a probe** → ✓ ACCEPTED: asserts the observable `/api/chat` wire body (No Source-Text Wiring Tests); I confirmed the tests hard-fail on revert.
- **TEA: Curate success-path test deferred to 92-4 (explicit deviation)** → ✓ ACCEPTED: I explicitly permitted this deferral in round 1; the blocking finding is the role boundary, which is fully covered. Forward obligation recorded as a Delivery Finding for 92-4.
- **Dev: Role boundary restored via send_with_session at both call sites + harness mirror** → ✓ ACCEPTED: exactly the prescribed fix; param mapping verified correct (edge-hunter + my own read); `send_with_session` is on the `LlmClient` protocol so the harness contract holds.

## Reviewer Assessment

**Verdict:** APPROVED

Round-trip 1 resolved cleanly. The [SEC][HIGH] role-boundary finding is fixed at all three call sites by swapping the flattening `send_stateless` for the role-separated `send_with_session(prompt=user, system_prompt=system+coercion, session_id=None)` — the exact prescribed fix, with the `QwenRouterLlm` measurement adapter mirrored so 92-4's flip-evidence measures the shipped shape. I verified the parameter mapping is not transposed (`prompt`=user/manifest, `system_prompt`=system+coercion), that `send_with_session(session_id=None)` builds `[{role:system},{role:user}]`, and that the two new tests assert on the captured `/api/chat` request body — they hard-fail on revert (silent-failure Q3 + my own read), so they are load-bearing, not tautological. The must-fix [TEST] vacuous assertions are now positive `isinstance(_OllamaIntentRouterLlm)` checks, and the recommended `SIDEQUEST_OLLAMA_URL` coverage was added. 2,362 agents+dungeon tests pass (`-n0`), 0 fail, 2 pre-existing skips.

**Data flow re-traced:** player text → `sanitize_player_text` → router pass → seam → `emit_tool` → **`send_with_session` (role-separated — the HIGH is resolved)** → qwen as `{role:system}`+`{role:user}` → `_extract_json_object` → `DispatchPackage.model_validate` (semantic gate) → ADR-123 dispatch gates. Loud at every failure point; the boundary now holds.

**Pattern observed:** the fix reuses the existing `ollama_client` transport seam (Don't Reinvent) and the change is one method swap per site — minimal, correct, well-commented at each site with the `[SEC HIGH]` rationale.

**Error handling:** unreachable Ollama still raises `OllamaClientError` (an `LlmClientError`) through `_post_chat`'s `except Exception` wrap; the curate retry→degrade ladder (`materializer.py`) and the router failure taxonomy catch it unchanged — fail-loud invariant preserved (silent-failure Q1/Q2 confirmed).

**Dispatch tags:** [EDGE] param-mapping verified correct, 2 pre-existing LOW dismissed (not introduced); [SILENT] Q1–Q3 loud-failure invariants confirmed, 2 pre-existing LOW dismissed; [TEST] must-fix vacuous assertions RESOLVED, OLLAMA_URL coverage added, role-boundary tests verified honest, curate success-path deferred to 92-4 with deviation; [DOC] specialist disabled — my pass found every new comment accurate and story-stamped; [TYPE] disabled — `send_with_session` is on the `LlmClient` protocol, return contract (`resp.text`) unchanged; [SEC] the round-1 HIGH is the finding this delta fixes — role separation restored, verified; [SIMPLE] disabled — minimal one-line-per-site change, no dead code, no over-engineering; [RULE] disabled — hand sweep: #11 (input validation at boundary) now COMPLIANT (boundary restored), #6 (test quality) now COMPLIANT (positive isinstance).

**Residual non-blocking (for the epic, not this story):** local usage-accounting line for $0 Ollama calls (Delivery Finding → 91-5/92-4); curate success-path live proof (→ 92-4); the pre-existing `ollama_client` `_histories`/`message`-shape hygiene items (candidate for a small standalone story). None block this opt-in, off-by-default seam.

**Handoff:** To Camina Drummer (SM) for finish-story.