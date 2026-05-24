---
story_id: "61-9"
jira_key: ""
epic: "61"
workflow: "tdd"
---

# Story 61-9: Commit to SDK narrator: remove legacy output_only prose and claude -p/Ollama narrator paths

## Story Details

- **ID:** 61-9
- **Title:** Commit to SDK narrator: remove legacy output_only prose and claude -p/Ollama narrator paths
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Stack Parent:** none

## Technical Approach

Commit to Anthropic SDK (ADR-101/102) as the sole narrator backend. The legacy `output_only.md` (24,698 B / ~3,610 tok) produces byte-identical output to pre-E1.5-A behavior by instructing the model to emit a full sidecar covering 8 tool-owned categories that the SDK path zeroes. This is a divergence-by-construction the moment you flip backends.

**Current state:** `anthropic_sdk` is the production default (`SIDEQUEST_LLM_BACKEND`). The legacy prose has zero live consumer, doubles the maintenance surface of every narrator-prompt change, and forces every tool-routing test to gate twice.

**Constraints:** Keeping `claude -p` / `Ollama` as narrator backends with the SDK prose would silently break them (told to call tools they do not have) — a NO-FALLBACK violation per project memory. This story removes them. `claude -p` stays available for non-narrator callers (e.g., dungeon 'curate').

## Files to Modify

**Delete:**
- `sidequest/agents/narrator_prompts/output_only.md`

**Rename/Edit:**
- `sidequest/agents/narrator_prompts/output_only_sdk.md` → rename to `output_only.md` (keep file name that tests already know)
- `sidequest/agents/narrator_prompts/__init__.py` — drop `NARRATOR_OUTPUT_ONLY`, rename `NARRATOR_OUTPUT_ONLY_SDK` → `NARRATOR_OUTPUT_ONLY`
- `sidequest/agents/narrator.py:252-301` — drop `tool_backend` kwarg, remove gating branch (always SDK prose)
- `sidequest/agents/orchestrator.py:1465` — drop `tool_backend` kwarg at call site
- `sidequest/agents/orchestrator.py:2225-2233` — collapse telemetry `tool_backend` conditional (now always `True`)

**Test files (rewrite to assert SDK prose only, drop dual-backend parameterization):**
- `test_narrator_output_format_backend_gate.py` — entire file pivots; keep wrapper-shape assertion, drop legacy-vs-SDK divergence assertions
- `test_50_24_player_check_seam.py` — drop `tool_backend=False` branch
- `test_57_4_recency_guardrails_migration.py` — drop `tool_backend=False` assertions and legacy-path span shape
- `test_47_9_innate_proactive.py`, `test_narrator_pre_prompt.py`, `test_narrator_prompt.py`, `test_50_2_confrontation_trigger_prompt.py`, `test_50_24_dice_contract_parity.py`, `test_narrator.py` — all assert content of `NARRATOR_OUTPUT_ONLY`; after rename, these assert SDK prose with no logic change

## Test Plan

1. **Unit tests:** All narrator and orchestrator tests pass, asserting SDK prose only
2. **Integration:** Playtest runs with `SIDEQUEST_LLM_BACKEND=anthropic_sdk` (default); narrator calls SDK tool-use contract
3. **Error handling:** Setting `SIDEQUEST_LLM_BACKEND=claude_cli` or `=ollama` for narrator errors loudly with clear message
4. **Non-narrator:** `claude -p` remains available for dungeon 'curate' and other non-narrator callers

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-24T10:53:09Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | 2026-05-24T08:18:18Z | 8h 18m |
| red | 2026-05-24T08:18:18Z | 2026-05-24T09:07:48Z | 49m 30s |
| green | 2026-05-24T09:07:48Z | 2026-05-24T10:25:07Z | 1h 17m |
| spec-check | 2026-05-24T10:25:07Z | 2026-05-24T10:28:44Z | 3m 37s |
| verify | 2026-05-24T10:28:44Z | 2026-05-24T10:36:14Z | 7m 30s |
| review | 2026-05-24T10:36:14Z | 2026-05-24T10:45:01Z | 8m 47s |
| spec-reconcile | 2026-05-24T10:45:01Z | 2026-05-24T10:53:09Z | 8m 8s |
| finish | 2026-05-24T10:53:09Z | - | - |

## Delivery Findings

### TEA (test design)

- **Gap** (blocking — for RED-completion only, NOT the story): `sidequest-server/develop` is missing the `GenreTheme.display_font_family` pydantic field that `sidequest-content` already references in every `theme.yaml`. Affects `sidequest/genre/models/theme.py` (need the field added); fix lives on `feat/63-3-theme-display-font-family` (`4a63ce5`) and must merge to develop before the worktree can complete its dungeon wiring test. Without it, every `GenreLoader.load("caverns_and_claudes")` call raises `GenreLoadError: display_font_family Extra inputs are not permitted`, blocking `tests/dungeon/test_61_9_dungeon_purpose_wiring.py` and all dungeon-attach tests on origin/develop today. *Found by TEA during test design.*

- **Improvement** (non-blocking): the `claude_client` parameter name across `sidequest/dungeon/materializer.py` and `sidequest/dungeon/lookahead_worker.py` is misleading post-61-9 — the dungeon "curate" path is structurally SDK-only because it calls `complete_with_tools` (a `ToolingLlmClient`-only method). Architect §A flagged renaming to `tool_client` or `sdk_client` as a low-cost boy-scout op. Affects 8 sites in materializer + 5 in lookahead_worker. *Found by TEA during test design.*

- **Improvement** (non-blocking): `sidequest/server/websocket_session_handler.py:1205` has a bare `ClaudeClient` as the local default for `claude_client_factory`. Per architect §B, that local default is the exact silent-degradation path AC-3 is closing — should be dropped or replaced with `lambda: build_llm_client(purpose="narrator")`. Won't affect production wiring (which uses `app.state.claude_client_factory`), but the local default is misleading dead code. *Found by TEA during test design.*

### Dev (green implementation)

- **Improvement** (non-blocking): Dungeon `claude_client` parameter rename (architect §A / TEA-flagged boy-scout op) deferred per the story's explicit Out-of-Scope clause. Affects ~13 sites across `sidequest/dungeon/materializer.py` and `sidequest/dungeon/lookahead_worker.py`. Mechanical and low-risk if folded into a follow-up cleanup story. *Found by Dev during green-phase verification.*

- **Improvement** (non-blocking): `sidequest/agents/orchestrator.py:1296` still has a bare `ClaudeClient()` default inside `Orchestrator.__init__` (`client if client is not None else ClaudeClient()`). This is the same silent-fallback pattern AC-3 closed at the handler layer (line 1205), but applied to a different constructor. Out-of-scope for 61-9 (the story enumerates only `websocket_session_handler.py:1205` under Files in Scope) and currently masked by the autouse `_mock_claude_client` conftest fixture, but worth a follow-up story to route through `build_llm_client(purpose="narrator")`. *Found by Dev during green-phase verification.*

- **Improvement** (non-blocking, doc-only): AC-6 deliverable — ADR-101 amendment needs authoring to document that `claude_cli` and `ollama` are retired for narration as of this story (non-narrator `claude -p` usage continues, e.g. the offline A/B eval CLI). Tech Writer surface, flagged per the story's AC-6 scope-out. *Found by Dev during green-phase verification.*

- **Gap** (non-blocking, environmental): 34 tests in the worktree fail with path-resolution errors because `Path(__file__).resolve().parents[3]` lands inside `.worktrees/` rather than at the repo root. Affects `tests/scripts/test_audit_namegen_corpora.py`, `tests/server/test_scene_harness.py`, `tests/server/test_scene_harness_hydrator.py`, `tests/protocol/test_api_contract_aside.py`, and `tests/infrastructure/test_pytest_xdist_setup.py`. Verified zero-failure on the main develop checkout — these are worktree-environment-only artifacts that will not appear in CI or post-merge. Fix would be a `parents[N]` traversal that finds the repo root via a marker file (`.pennyfarthing/repos.yaml`, `pyproject.toml`, etc.) rather than a hardcoded depth. *Found by Dev during green-phase verification.*

### Architect (spec-check)

- No upstream findings during spec-check.

### TEA (test verification)

- **Improvement** (non-blocking): `sidequest/agents/llm_factory.py` `_AsideLlm` (line 81) and `_IntentRouterLlm` (line 122) are ~85% duplicated single-shot Haiku adapters (identical API-key validation, identical `complete()` shape, differ only in model id + max_tokens). Pre-existing code — not introduced by 61-9 — but a candidate cleanup story could extract a shared `_SingleShotHaikuLlm(model_id, max_tokens, context_name)` base + helper. Affects 2 classes / ~50 lines. *Found by TEA during test verification.*

- **Improvement** (non-blocking): The "dead-code" claim by simplify-quality that `Orchestrator._run_narration_turn_streaming` / `_run_narration_turn_synchronous` / `narrator.is_streaming_enabled()` are unreachable post-61-9 is technically PARTIALLY correct (every live narrator path now goes through `build_llm_client` → `AnthropicSdkClient` which IS a `ToolingLlmClient`), but the methods remain structurally reachable through (a) `Orchestrator.__init__:1296`'s bare `ClaudeClient()` default (Dev's separate Delivery Finding) and (b) `scripts/ab_eval_harness_cli.py`'s direct `ClaudeClient` construction (architect §A, spec scope-out). Removing the methods is out of 61-9 scope and would break the offline A/B harness. Worth tracking as a follow-up after both ad-hoc consumers move through the gated factory. *Found by TEA during test verification.*

### Reviewer (code review)

- **Improvement** (non-blocking): `sidequest/server/websocket_session_handler.py:1208` `cast("Callable[[], LlmClient]", lambda: build_llm_client(purpose="narrator"))` is a tactical type-system lie — `build_llm_client(purpose="narrator")` returns an `AnthropicSdkClient` that implements `complete_with_tools` (`ToolingLlmClient` protocol) but NOT the `LlmClient` `send_with_model` / `send_with_session` / `send_stateless` / `capabilities` methods. The two protocols are structurally disjoint (architect §A note: "the two protocols serve different call sites"). In practice this is unreachable in production (every live caller injects `claude_client_factory` via `app.state.claude_client_factory`) and in tests (the autouse `_mock_claude_client` conftest fixture redirects `build_llm_client` to `_FakeClaudeClient` which DOES implement `send_*`). But the annotation lie is a latent footgun for a future caller that constructs `WebSocketSessionHandler` without injecting and then invokes a `LlmClient`-only method — `AttributeError` at runtime, not a clean error message. Cleanest fix is to widen `_client_factory` type to `Callable[[], LlmClient | ToolingLlmClient]` and add `isinstance` guards at downstream call sites; same converging-protocols cleanup needed at `Orchestrator.__init__:1296` (Dev's separate Delivery Finding). Affects 1 site + downstream call-site analysis. *Found by Reviewer during code review (confirms [SEC] subagent finding, low-confidence).*

- **Improvement** (non-blocking): `tests/server/conftest.py:458-460` autouse fixture lambda `lambda *, purpose="narrator": _FakeClaudeClient()` accepts `purpose` but ignores it — a future server-test that exercises a `purpose="tool"` path through `WebSocketSessionHandler` would silently receive a non-`ToolingLlmClient` fake instead of the structurally-correct shape. No production hole; current test surface doesn't exercise this path through the handler (dungeon tests have their own per-test monkeypatch of `session_integration.build_llm_client`). Worth fixing alongside the `cast` cleanup above: make the lambda purpose-aware (return a fake that implements `complete_with_tools` when `purpose="tool"`). *Found by Reviewer during code review (confirms [SEC] subagent finding, low-confidence).*

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (one Minor mismatch resolved as Option A)
**Mismatches Found:** 1

- **Extra deletion: `tests/agents/test_ollama_backend_e2e_48_2.py`** (Extra in code — Cosmetic/Behavioral, Minor)
  - Spec: AC-4's test-file list (context-story-61-9.md §AC-4 table) does not include this file. Out-of-scope clause says "Removing the OllamaClient class itself" remains out of scope but is silent on Ollama narrator-path e2e tests.
  - Code: Dev deleted the file. Inspection confirms the file's stated purpose was "Validate `SIDEQUEST_LLM_BACKEND=ollama` end-to-end" (narrator backend contract) — exactly the contract AC-3 retires. Keeping the file would have surfaced as either an `ImportError` (if it touched a removed symbol) or assertions against a now-raising `NarratorBackendRetired` code path.
  - Recommendation: **A — Update spec implicitly.** The deletion is the structurally-correct consequence of AC-3 retiring the Ollama narrator backend; the spec's silence on this file is an oversight rather than a directive. The non-narrator OllamaClient surface remains covered via `scripts/ab_eval_harness_cli.py` and `tests/agents/test_ab_eval_harness.py` (direct construction, not factory routing) per architect §A enumeration. No code change; no further action.

**Substantive AC-by-AC alignment:**

| AC | Spec | Implementation | Verdict |
|----|------|----------------|---------|
| AC-1 | Delete legacy `output_only.md`; rename `_sdk.md` → `output_only.md`; drop `NARRATOR_OUTPUT_ONLY_SDK` const + `__all__` entry | `git status` confirms file rename + delete; `narrator_prompts/__init__.py` exports only the single constant | Aligned |
| AC-2 | `build_output_format` drops `tool_backend`; orchestrator call site bare; OTEL Option (a) — attr removed, `guardrails_skipped`/`bytes_saved` hard-wired constants | `narrator.py:250` signature clean; `orchestrator.py:1461` call site bare; `orchestrator.py:2223` span emits the two constants only | Aligned |
| AC-3 | `purpose: Literal["narrator","tool"]` kwarg (default `"narrator"`); raise typed `NarratorBackendRetired(LlmClientError)` for `claude`/`ollama` regardless of `purpose` at config boundary; dungeon caller opts in with `purpose="tool"`; `websocket_session_handler.py:1205` bare default closed | `llm_factory.py:34` keyword-only kwarg per architect §B chokepoint; `_RETIRED_BACKENDS = {"claude", "ollama"}` raises for either purpose; `session_integration.py:155` passes `purpose="tool"`; `websocket_session_handler.py:1208` routes through `cast`-wrapped `build_llm_client(purpose="narrator")` lambda (cast pragmatically narrows the factory's `LlmClient \| ToolingLlmClient` return to satisfy pyright without rippling the annotation through 20+ test fixtures — minimal-touch choice) | Aligned |
| AC-4 | Delete `test_narrator_output_format_backend_gate.py`; rewrite `test_50_24_player_check_seam.py` + `test_57_4_recency_guardrails_migration.py`; mechanical const rename in `test_50_24_dice_contract_parity.py`; mechanical verify the four NARRATOR_OUTPUT_ONLY importers | All specified rewrites completed; `test_ollama_backend_e2e_48_2.py` additionally deleted (see Mismatch 1 above); conftest autouse `_mock_claude_client` fixture redirected from removed `ClaudeClient` import to `build_llm_client` patch (necessary downstream consequence) | Aligned |
| AC-5 | `git grep NARRATOR_OUTPUT_ONLY_SDK` empty in production code | Verified during green phase; remaining references are doc-string history notes in `AUDIT.md` + the AC-5 test that asserts the constant is gone | Aligned |
| AC-6 | ADR-101 amendment is a Tech Writer doc deliverable, NOT a green-phase code AC; flag as review-phase Delivery Finding | Flagged under `### Dev (green implementation)` as `Improvement (non-blocking, doc-only)` per spec instruction | Aligned (per spec scope-out) |

**Tandem-notes coverage check:**

- **§A non-narrator caller enumeration:** All callers preserved per spec — `scripts/ab_eval_harness_cli.py` constructs `ClaudeClient`/`OllamaClient` directly (bypassing factory) per the in-scope `ab_eval_harness_cli.py` edit Dev made.
- **§B chokepoint mechanism:** Single `purpose` kwarg on `build_llm_client` is the only narrator-vs-tool detection — no parallel `isinstance` gate at narrator-build time. Confirmed by inspecting `llm_factory.py` (single gate) and `orchestrator.py` (no new `isinstance(self._client, ...)` branch).
- **§C `tool_backend` blast radius:** Production sites (3) and test sites (3) all handled per the enumeration. Zero new sites detected via `git grep tool_backend` in `sidequest/` (only the residual comment at `orchestrator.py:2217` documenting the removal).
- **§D silent-flip risk for `NARRATOR_OUTPUT_ONLY`:** Dev's full test run included `test_47_9_innate_proactive.py`, `test_narrator_pre_prompt.py`, `test_narrator_prompt.py`, `test_50_2_confrontation_trigger_prompt.py`, and `test_narrator.py` — all green (test_47_9 skipped via pre-existing conftest mechanism unrelated to 61-9, per Dev verification). Risk did not materialize.
- **§E test-classification:** Each listed file handled per the classification table (DELETE / REWRITE / MECHANICAL RENAME / MECHANICAL VERIFY).

**Dev Delivery Findings carried forward to TEA verify / Reviewer / SM:**

- **Non-blocking:** Dungeon `claude_client` param rename deferred (architect §A boy-scout op).
- **Non-blocking:** `orchestrator.py:1296` bare `ClaudeClient()` default flagged for follow-up — same silent-fallback pattern AC-3 closed at handler layer, but at a different constructor.
- **Non-blocking, doc-only:** ADR-101 amendment for Tech Writer (AC-6).
- **Non-blocking, environmental:** 34 worktree-path-resolution test failures unrelated to 61-9 (verified clean on main develop checkout).

**Decision:** Proceed to TEA verify.

**Handoff:** To Radar O'Reilly for verify phase.

## TEA Assessment (verify phase)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8 (production focus — `scripts/ab_eval_harness_cli.py`, `sidequest/agents/llm_factory.py`, `sidequest/agents/narrator.py`, `sidequest/agents/narrator_prompts/__init__.py`, `sidequest/agents/orchestrator.py`, `sidequest/dungeon/session_integration.py`, `sidequest/server/websocket_session_handler.py`, `tests/server/conftest.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | All pre-existing `_AsideLlm` / `_IntentRouterLlm` duplication in `llm_factory.py` — not introduced by 61-9; flagged for follow-up |
| simplify-quality | 3 findings | 1 in-scope stale-comment fix (applied); 2 dead-code claims rejected (orchestrator legacy branches remain reachable through scope-out paths) |
| simplify-efficiency | 4 findings | 1 pre-existing duplication, 1 incorrect (would lose retired-backend diagnostic), 1 incorrect (cast is required for `LlmClient \| ToolingLlmClient` widening), 1 low-confidence cascade |

**Applied:** 1 high-confidence fix (`05c3d13` — narrator.py:221-226 stale dual-path comment updated to reflect 61-9 retirement; Dev fixed the `build_output_format` docstring during green but missed this earlier comment block).
**Flagged for Review:** 0 (medium-confidence findings all rejected with rationale).
**Noted:** 2 follow-up observations carried to Delivery Findings (`_AsideLlm` duplication, latent dead-code reachable via scope-out paths).
**Reverted:** 0.

**Overall:** simplify: applied 1 fix.

**Rejection rationale for the dead-code findings:**
- `Orchestrator._run_narration_turn_streaming` / `_run_narration_turn_synchronous` remain reachable because `Orchestrator.__init__:1296` retains a bare `ClaudeClient()` default (Dev's explicit Delivery Finding — same silent-fallback pattern AC-3 closed at the handler layer but at a different constructor; out-of-scope for 61-9) AND `scripts/ab_eval_harness_cli.py` constructs `ClaudeClient` directly per architect §A enumeration (explicit Out-of-Scope).
- `narrator.is_streaming_enabled()` remains a live feature flag for the same reachability reasons.
- `llm_factory._VALID_BACKENDS` / `_RETIRED_BACKENDS` two-set design is intentional: collapsing to a single set would lose the targeted "you set `claude` — that backend is retired, use `anthropic_sdk`" diagnostic that AC-3's loud-fail spec requires, replacing it with a generic "unknown backend" error.
- `cast(...)` wrapper at `websocket_session_handler.py:1208` is structurally required because `build_llm_client` returns `LlmClient | ToolingLlmClient` and `_client_factory` is typed `Callable[[], LlmClient]`; pyright fails without the cast (verified during green). The cleaner alternative — widening the annotation through 20+ test fixtures — was correctly rejected by Dev as scope creep.

### Quality Checks

| Check | Result |
|-------|--------|
| ruff check | All checks passed |
| ruff format --check | 1318 files already formatted |
| pyright (touched files) | Net 0 new errors (cast added in green phase to satisfy `LlmClient \| ToolingLlmClient` widening) |
| Full server pytest | 7459 passed, 375 skipped — 34 failures all pre-existing worktree-path artifacts (`Path(__file__).resolve().parents[3]` lands in `.worktrees/`, not repo root; verified zero-failure on the main develop checkout where the same 35 tests pass). Identical failure set before and after the simplify commit — zero regression introduced. |

### Test surface verification

- All 17 RED tests from `tests/agents/test_61_9_sdk_commitment.py` flipped to GREEN.
- The `tests/dungeon/test_61_9_dungeon_purpose_wiring.py` AC-3 wiring assertion passes — `attach_dungeon_to_session` calls `build_llm_client(purpose="tool")`.
- The 5 sanity-check baseline tests (asserting today's-state invariants Dev must not regress, per TEA's RED-phase contract) all remain green.
- AC-5 invariant verified: `git grep NARRATOR_OUTPUT_ONLY_SDK -- sidequest/` returns empty in production code; remaining references are doc-string history notes in `AUDIT.md` + the AC-5 test that asserts the constant is gone.
- High-risk silent-flip files per architect §D (`test_47_9_innate_proactive.py`, `test_narrator_pre_prompt.py`, `test_narrator_prompt.py`, `test_50_2_confrontation_trigger_prompt.py`, `test_narrator.py`) all green or pre-existing-skip per the conftest `_CAVERNS_SUNDEN_DEPRECATED_TESTS` mechanism (unrelated to 61-9, verified by Dev).

**Handoff:** To Colonel Potter for code review.

## SM Assessment

**Setup phase complete.** Story 61-9 is well-scoped — the description enumerates exact files, line numbers, and tests to touch. Risk profile is moderate-low for a 3-point story:

- Removing the legacy `output_only.md` prose path is mechanical (rename + delete) once the dual-backend tests pivot to SDK-only assertions.
- Real risk is in `llm_factory.py`: gating `claude_cli` / `ollama` to ERROR on narrator selection while keeping `claude -p` alive for non-narrator callers (dungeon `curate`). TEA must design a test that proves a narrator-routed `claude_cli` selection fails loud (NO-FALLBACK) and a non-narrator caller still resolves.
- ADR-101 amendment is a doc deliverable, not a code AC — flag in review phase.
- Watch for: any caller still passing `tool_backend` kwarg after the gating branch is removed (orchestrator.py:1465, telemetry 2225-2233). Grep the repo broadly in green phase, not just the listed sites.

No design deviations. No blockers. Handoff to Radar for red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** N/A — full TDD red phase for a 3-point refactor with mechanical + behavioral surfaces.

**Test Files:**

- `tests/agents/test_61_9_sdk_commitment.py` (NEW, 17 tests) — consolidated 61-9 RED contract covering AC-1/2/3/4/5 + OTEL span shape (Option a per DECISION LOCKED in story context).
- `tests/dungeon/test_61_9_dungeon_purpose_wiring.py` (NEW, 1 test) — fixture-driven wiring assertion that `attach_dungeon_to_session` calls `build_llm_client(purpose="tool")`. Uses the existing `_real_pack()` / `_beneath_sunden_world_dir()` fixtures from `tests/dungeon/test_session_integration.py` (reuse, not duplicate).

**Tests Written:** 18 tests covering 6 ACs + OTEL span shape decision
**Status:** RED (17 failing as designed, 5 sanity-check passes — Dev's green-phase work should flip all 17 to green without breaking the 5 passes)

### Rule Coverage

| Rule (lang-review/python.md) | Test(s) | Status |
|------------------------------|---------|--------|
| #1 silent-exceptions | `test_narrator_purpose_with_claude_backend_raises` + ollama + tool variants (NO-FALLBACK at config boundary) | failing |
| #6 test-quality (no vacuous assertions) | Self-check: caught + rewrote `test_build_output_format_no_kwarg_registers_sdk_prose` (was checking `NARRATOR_OUTPUT_ONLY in body` which is tautological; now asserts SDK-specific sentinel `begin_confrontation`) | rewritten |
| #6 test-quality (mock target correctness) | Dungeon wiring patches `session_integration.build_llm_client` (use site), not `llm_factory.build_llm_client` (define site) — same pattern as existing `test_attach_seeds_and_registers...` | applied |
| CLAUDE.md "No Source-Text Wiring Tests" | All wiring assertions are reflection (`inspect.signature`, `hasattr`, `Path.exists`) or fixture-driven spy. Zero `Path.read_text() + grep` in 61-9 tests | applied |
| CLAUDE.md "Every Test Suite Needs a Wiring Test" | `test_attach_dungeon_calls_build_llm_client_with_purpose_tool` + `test_orchestrator_call_site_passes_no_tool_backend` are the wiring assertions for AC-2 and AC-3 | applied |
| Memory `feedback_no_fallbacks_hard` | Strict interpretation: AC-3 raises for ALL non-SDK backends regardless of purpose. Tests assert this stricter shape (architect §B recommended gentler option; strict wins per Doctor's standing preference) | applied |
| Memory `feedback_no_content_coupled_tests` | RED tests use only in-repo fixtures and reflection — no live `genre_packs/*` loads in unit tests | applied |
| Memory `feedback_one_mechanism_per_problem` | Single `purpose` kwarg on `build_llm_client` is the only narrator-vs-tool detection mechanism — no parallel `isinstance` gate at narrator-build time (architect §B rejected alternative) | applied |
| Memory `feedback_log_absence_not_deadness` | Sanity-check passes (5 tests) verify today's-state baseline — confirms what Dev must NOT regress (e.g. the OTEL span still emits post-AC-2) | applied |

**Rules checked:** 9 of 14 applicable lang-review + project-memory rules have test coverage.
**Self-check:** 1 vacuous test found and rewritten during RED verification.

### Test inventory (RED outcomes for Dev)

| # | Test | Today (RED) | Post-AC | AC |
|---|------|-------------|---------|------|
| 1-8 | `TestNarratorBackendGate` (8 tests) | TypeError or no-raise | LlmClientError-subclass raised at construction | AC-3 |
| 9 | `test_narrator_output_only_sdk_constant_is_removed` | `hasattr` returns True | const + `__all__` entry gone | AC-5 |
| 10 | `test_narrator_output_only_constant_remains_present` | **passes today** | still passes | AC-1 baseline |
| 11 | `test_narrator_output_only_contains_sdk_tool_use_directive` | sentinel absent | sentinel present (post-rename) | AC-1 |
| 12 | `test_legacy_output_only_sdk_file_no_longer_exists` | file exists | file deleted | AC-1 |
| 13 | `test_output_only_md_file_exists_post_rename` | **passes today** | still passes | AC-1 baseline |
| 14 | `test_build_output_format_signature_drops_tool_backend` | param present | param absent | AC-2 |
| 15 | `test_build_output_format_no_kwarg_registers_sdk_prose` | legacy prose by default | SDK prose by default | AC-2 |
| 16 | `test_orchestrator_call_site_passes_no_tool_backend` | passes `tool_backend=True` | no kwargs | AC-2 |
| 17 | `test_span_still_emits_on_sdk_path` | **passes today** | still passes | OTEL (Option a) |
| 18 | `test_span_no_longer_carries_tool_backend_attr` | attr present | attr absent | OTEL (Option a) |
| 19 | `test_span_emits_hardwired_guardrails_skipped_constant` | **passes today** | still passes (now unconditional) | OTEL (Option a) |
| 20 | `test_span_emits_hardwired_bytes_saved_constant` | **passes today** | still passes (now unconditional) | OTEL (Option a) |
| 21 | `test_backend_gate_test_module_no_longer_exists` | file exists | file deleted | AC-4 |
| 22 | `test_attach_dungeon_calls_build_llm_client_with_purpose_tool` | call site is bare | call site passes `purpose="tool"` | AC-3 (wiring) |

### Notes for Dev (Major Winchester)

1. **Read `sprint/context/context-story-61-9.md` first.** The DECISION LOCKED for the OTEL span (Option a) and the architect §A enumeration of non-narrator callers are load-bearing.
2. **AC-4 is partly verified by other tests.** Delete `test_narrator_output_format_backend_gate.py` AND rewrite the `tool_backend=True/False` assertions in `test_57_4_recency_guardrails_migration.py`. The latter is not asserted by a separate RED test because those rewrites are within the SDK-prose tests Dev must already touch.
3. **AC-5 zero-references invariant.** `test_narrator_output_only_sdk_constant_is_removed` covers the production side; the test files in `tests/agents/` and `tests/magic/` that import `NARRATOR_OUTPUT_ONLY_SDK` will Python-ImportError when Dev removes it — those failures are the test-side AC-5 verification surface. Dev should grep `git grep NARRATOR_OUTPUT_ONLY_SDK` after the rename and replace each reference with `NARRATOR_OUTPUT_ONLY`.
4. **Watch the silent flip risk (architect §D).** Post-rename, `NARRATOR_OUTPUT_ONLY` points to SDK prose. The 4 magic-suite tests + `test_narrator.py` that import the legacy name will silently start asserting SDK prose. `test_47_9_innate_proactive.py` (11 references, CRITICAL MAGIC RULE assertions) is the highest-risk file — RUN it, do not just inspect.
5. **AC-6 (ADR-101 amendment) is doc-only.** Tech Writer surface; flag in review-phase Delivery Findings. Not a green-phase code AC.
6. **Boy-scout opportunity (deferred).** Dungeon `claude_client` param rename to `tool_client` / `sdk_client` (architect §A). Defer or fold in only if green is otherwise clean — not a blocker.

**Handoff:** To Dev for green-phase implementation.

## Design Deviations

### TEA (test design)

- **Dungeon wiring RED test temporarily blocked on cross-repo drift — RESOLVED 2026-05-24**
  - Spec source: context-story-61-9.md, AC-3 ("non-narrator callers of claude_client.py continue to work")
  - Spec text: AC-3 requires a wiring test proving `attach_dungeon_to_session` calls `build_llm_client(purpose="tool")`.
  - Implementation: `tests/dungeon/test_61_9_dungeon_purpose_wiring.py` initially errored at `GenreLoader.load("caverns_and_claudes")` because `sidequest-content`'s `theme.yaml` files referenced `display_font_family` that origin/develop's `GenreTheme` pydantic model did not yet accept.
  - Rationale: Doctor merged story 63-3 (now `c2d1238` on origin/develop) 2026-05-24; worktree rebased onto the new develop and the wiring test now fails for the correct AC-3 reason (`captured_kwargs=[{}]` proves `session_integration.py:155` still has bare `build_llm_client()`).
  - Severity: minor (resolved)
  - Forward impact: none — red phase verified complete with 17/17 designed failures and 5 sanity-check passes.
  - ✓ ACCEPTED by Reviewer: cross-repo drift was a real RED-phase blocker, resolved by an unrelated already-merged story (63-3); spec authority preserved.

### Reviewer (audit)

- No additional undocumented deviations found. All Architect spec-check findings (the `test_ollama_backend_e2e_48_2.py` extra-deletion, resolved as Option A) are reasonable and well-rationalized — the deleted file's stated purpose was Ollama-narrator-backend e2e validation, exactly the contract AC-3 retires.

### Architect (reconcile)

- **Extra deletion: `tests/agents/test_ollama_backend_e2e_48_2.py`**
  - Spec source: context-story-61-9.md, AC-4 (test-file classification table) and Scope Boundaries → Out of scope
  - Spec text: "Removing the OllamaClient class itself — the gate is on `purpose=\"narrator\"`; the class can stay as dead code for future re-introduction if anyone wants Ollama as a tool backend." AC-4's test classification table enumerates 7 test files; this Ollama e2e file is not among them.
  - Implementation: Dev deleted `tests/agents/test_ollama_backend_e2e_48_2.py` (744 lines) in addition to the AC-4-enumerated rewrites.
  - Rationale: The file's stated purpose was validating `SIDEQUEST_LLM_BACKEND=ollama` end-to-end through the narrator path — exactly the contract AC-3 retires. Keeping it would have either ImportError'd against removed symbols or asserted against a now-raising `NarratorBackendRetired` code path. Non-narrator OllamaClient surface remains covered via `tests/agents/test_ab_eval_harness.py` direct-construction tests per spec scope-out.
  - Severity: minor
  - Forward impact: none — Ollama-as-tool-backend reintroduction (deferred, no story) would author a new test file rather than restore this one; the deleted file's structure was narrator-path-shaped.

- **`cast(...)` wrapper added at `sidequest/server/websocket_session_handler.py:1208`**
  - Spec source: context-story-61-9.md, Technical Guardrails → Files in scope (`websocket_session_handler.py:1205`)
  - Spec text: "Drop bare `ClaudeClient` default or replace with `lambda: build_llm_client(purpose=\"narrator\")`. The `claude_client_factory` parameter still flows through but its local default is a fallback that AC-3 forbids."
  - Implementation: Dev replaced the bare default with `cast("Callable[[], LlmClient]", lambda: build_llm_client(purpose="narrator"))` — adding a `typing.cast` to narrow the factory's `LlmClient | ToolingLlmClient` return down to `LlmClient` to satisfy pyright without rippling the wider annotation through the handler's 20+ test fixtures.
  - Rationale: `build_llm_client` returns the union of both client protocols (since story 61-9 broadened it); the handler's `_client_factory` was already typed `Callable[[], LlmClient]`. Without the cast, pyright errors at the assignment. Widening the annotation through every fixture would have ballooned the diff for a structurally-unreachable path (production injects `app.state.claude_client_factory`; tests inject via autouse `_mock_claude_client`). The cast is a localized type-system narrowing, not a runtime behavior change.
  - Severity: minor
  - Forward impact: minor — Reviewer logged this as non-blocking Delivery Finding (latent footgun: if a future caller constructs `WebSocketSessionHandler` without injecting and then invokes a `LlmClient`-only method, the SDK client's `AttributeError` would surface as a confusing runtime error rather than a type-time mismatch). Follow-up cleanup: widen `_client_factory: Callable[[], LlmClient | ToolingLlmClient]` and add `isinstance` guards at downstream call sites. Same pattern applies at `Orchestrator.__init__:1296` (Dev's separate Delivery Finding). No story currently filed.

- **`scripts/ab_eval_harness_cli.py` materially modified — spec assertion "survives untouched" was wrong**
  - Spec source: context-story-61-9.md, AC Context → AC-3 (Non-narrator callers enumeration)
  - Spec text: "`sidequest/agents/ab_eval_harness.py` — offline A/B eval CLI. Constructs `ClaudeClient` directly, bypasses `build_llm_client()`. Unaffected by the factory gate; survives untouched."
  - Implementation: The CLI's Ollama branch was NOT bypassing `build_llm_client()` — it was calling `build_llm_client()` with `SIDEQUEST_LLM_BACKEND` temporarily forced to `"ollama"`. AC-3's gate raises on that env value for both `purpose="narrator"` and `purpose="tool"` (Architect §A: those backends don't implement `complete_with_tools` either). Dev had to rewrite `_build_clients()` (~40 lines) to construct `OllamaClient` directly (mirroring the existing `ClaudeClient()` direct construction) and dropped the now-dead `build_llm_client` / `ENV_BACKEND` / `UnknownBackend` imports. The CLI's two AC5 tests (`test_ab_eval_harness.py:553-587`) were correspondingly updated from asserting `build_llm_client` import to asserting `ClaudeClient` + `OllamaClient` direct imports.
  - Rationale: The spec's "survives untouched" assertion conflated `ClaudeClient` direct construction (true) with Ollama's factory routing (false). Catching this earlier would have widened the AC-3 enumeration to flag the ab_eval CLI as an in-scope migration site. The post-fact answer is correct (direct construction, isinstance-guarded, no factory routing), and the offline benchmarking capability the CLI exists for is preserved.
  - Severity: minor
  - Forward impact: none — CLI behavior preserved; operator-facing UX unchanged (`SIDEQUEST_OLLAMA_URL` env-var still honored via `DEFAULT_OLLAMA_URL` fallback). The `test_ab_eval_harness.py` test docstrings now explicitly cite the post-61-9 contract, so the next refactor will have correct context.

- **Incidental ruff-format cleanup of `sidequest/agents/anthropic_sdk_client.py` (33 lines) and several `tests/agents/test_61_followup_D_*.py` files**
  - Spec source: context-story-61-9.md, Technical Guardrails → Files in scope (enumerated list — none of the above appear)
  - Spec text: Implicit — files not in the in-scope table should not be modified absent a downstream-consequence justification.
  - Implementation: `anthropic_sdk_client.py` received pure ruff-format line-wrapping reflows (no semantic change verified by spot diff: `cost_window is None or input_window is None or len(cost_window) < _BASELINE_WINDOW_K` collapsed onto a single line, similar reflows in `_update_cost_baseline` and `_check_session_cumulative`). Several `test_61_followup_D_*.py` test files received the same kind of f-string concatenation reflows.
  - Rationale: ruff-format pre-commit hook ran across touched-directory neighbors during one of the green/verify-phase commits. Pre-existing formatting drift was incidentally cleaned up; no behavioral change. Out-of-scope but defensible as boy-scouting (project memory `feedback_boy_scout_bounded` — small adjacent fixes welcome during a story). Consistent with the broader "73 pre-existing repo-wide ruff-format-debt files" surface that earlier work has been clearing opportunistically.
  - Severity: minor
  - Forward impact: none — cosmetic only; downstream stories see cleaner baselines.

---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.test_analyzer=false` |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.comment_analyzer=false` |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Yes | findings | 2 (both low-confidence) | confirmed 2, dismissed 0, deferred 0 (both confirmed as non-blocking Delivery Findings for follow-up; logged under `### Reviewer (code review)`) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.rule_checker=false` |

**All received:** Yes (2 enabled + 7 pre-filled disabled per settings; gate per agent-spec accepts disabled subagents as non-blocking)
**Total findings:** 2 confirmed (both low-confidence, both non-blocking, both logged as Delivery Findings), 0 dismissed, 0 deferred

---

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** `SIDEQUEST_LLM_BACKEND` env var → `llm_factory.build_llm_client(purpose=...)` → either `AnthropicSdkClient()` (safe, sole live path) or `NarratorBackendRetired` raise (loud, names the retired backend, points at the ADR-101 amendment). The legacy `ClaudeClient` / `OllamaClient` construction sites that used to live inside `build_llm_client` are gone; the only remaining direct constructors of those classes are `scripts/ab_eval_harness_cli.py` (offline operator CLI, explicit spec scope-out per architect §A) and the `Orchestrator.__init__:1296` bare default (Dev's flagged non-blocking follow-up — not introduced by 61-9, but adjacent and worth tracking). The `WebSocketSessionHandler.__init__:1205` local default previously bare-`ClaudeClient`'d a `claude -p` subprocess when no factory was injected — this story closes that silent-fallback at the same time as the factory gate lands, so the AC-3 "fail at config boundary" invariant holds end-to-end through both production wiring (`app.py:105` factory injection) and the hardened local default. Unsafe alternative would have been an `isinstance(...)` check at narrator-build time, which the architect tandem explicitly rejected (§B) because it shifts the error from a config boundary to a deep call site.

**Pattern observed:** **NO-FALLBACK at the config boundary** — `llm_factory.py:34-67` raises `NarratorBackendRetired(LlmClientError)` immediately on retired-backend env value, regardless of `purpose`, with a diagnostic message that names the retired backend, cites the ADR-101 amendment, and tells the operator how to fix it. This matches the project memory rule `feedback_no_fallbacks_hard` (verbatim: "retired mechanisms get ZERO backstop; fail LOUD with surfaced error message") and the `feedback_one_mechanism_per_problem` rule (single `purpose` kwarg is the only narrator-vs-tool detection mechanism — no parallel `isinstance` gate at narrator-build time).

**Error handling:** Verified at `llm_factory.py:55-67` — three failure modes covered loudly:
1. Unknown backend value → `UnknownBackend(LlmClientError)` with `pick one of [anthropic_sdk, claude, ollama]` diagnostic (preserves the diagnostic ability to tell a user with a typo that they should pick a valid value, even though two of the three are retired).
2. Retired backend (`claude`/`ollama`) → `NarratorBackendRetired(LlmClientError)` with backend name + purpose + ADR pointer + fix action.
3. Valid live backend (`anthropic_sdk`) → returns `AnthropicSdkClient()`.

The two-set design (`_VALID_BACKENDS` + `_RETIRED_BACKENDS`) is intentional: it preserves the targeted "you set claude — that backend is retired" diagnostic that the loud-fail spec requires. A simplifier subagent flagged collapsing the sets but the collapse would replace the named-retirement diagnostic with a generic "unknown backend" error (rejected by TEA in verify phase).

### Rule Compliance (.pennyfarthing/gates/lang-review/python.md)

Enumerated against each rule that touches changed code:

| # | Rule | Files in diff | Verdict | Evidence |
|---|------|---------------|---------|----------|
| 1 | Silent exception swallowing | All 30 diff files | Compliant | No new `except` clauses introduced; existing `try/except` blocks unchanged; `NarratorBackendRetired` raises rather than catches |
| 2 | Mutable default arguments | All diff files | Compliant | No new function signatures with `=[]`/`={}`/`=set()`; `purpose: Literal["narrator","tool"] = "narrator"` uses an immutable string literal default |
| 3 | Type annotation gaps at boundaries | `llm_factory.py`, `narrator.py`, `websocket_session_handler.py`, `session_integration.py` | Compliant | `build_llm_client` signature fully annotated (kwarg + return type); `build_output_format(self, registry: object) -> None`; `_client_factory: Callable[[], LlmClient]` annotated (see `[SEC]` finding about the cast widening this annotation — type-system lie, not a missing annotation) |
| 4 | Logging coverage AND correctness | Diff doesn't touch `logging` calls | N/A | Story refactor is structural; no new error paths needed logging |
| 5 | Path handling | `narrator_prompts/__init__.py` | Compliant | Pre-existing `Path / file` pattern preserved; `encoding="utf-8"` present on `read_text()` |
| 6 | Test quality | `test_61_9_sdk_commitment.py`, `test_61_9_dungeon_purpose_wiring.py`, `test_50_24_player_check_seam.py`, `test_57_4_recency_guardrails_migration.py`, `conftest.py` | Compliant | TEA self-caught one vacuous assertion during RED phase and rewrote it (see TEA Assessment §Rule Coverage); mock targets verified correct (conftest patches `websocket_session_handler.build_llm_client` at use site, not define site); no `assert True` / `assert result` patterns; no parametrized tests testing the same path |
| 7 | Resource leaks | Diff doesn't touch resource handling | N/A | |
| 8 | Unsafe deserialization | Diff doesn't touch deserialization | N/A | |
| 9 | Async/await pitfalls | `session_integration.py:155` is in an `async def` | Compliant | `build_llm_client(purpose="tool")` is sync — proper to call directly without await |
| 10 | Import hygiene | `narrator.py`, `narrator_prompts/__init__.py`, `websocket_session_handler.py` | Compliant | No star imports; `NARRATOR_OUTPUT_ONLY_SDK` removed from `__all__` cleanly; `cast` added to TYPE_CHECKING-adjacent typing import (line 23); no circular import risk introduced |
| 11 | Input validation at boundaries | `llm_factory.py` | Compliant | Env-var input validated against `_VALID_BACKENDS` frozenset (line 55-58), then retired-set (59-67), then SDK construction. No SQL, no HTML output, no `re.compile` on user input |
| 12 | Dependency hygiene | `pyproject.toml` unchanged | N/A | |
| 13 | Fix-introduced regressions | Verify-phase simplify commit (`05c3d13`) | Compliant | Re-scan: docstring-only change, no new error handling, no new types, no new validation surface |
| 14 | State cleanup ordering with fallible side effects | `narrator.py:269-277` (`build_output_format` registers a section) | Compliant | Single `register_section` call, no upstream queue/buffer that needs clearing first |

### Observations

1. **[VERIFIED]** AC-1 file rename + constant removal complete — `__init__.py:27` loads `output_only.md` (which now holds the SDK prose post-rename); `git status` shows `D output_only_sdk.md`; `__all__` no longer exports `NARRATOR_OUTPUT_ONLY_SDK`. Complies with the spec's AC-1 sequence verbatim.

2. **[VERIFIED]** AC-2 `build_output_format` signature scrubbed — `narrator.py:250` reads `def build_output_format(self, registry: object) -> None:` (no `tool_backend` kwarg); orchestrator call site at `orchestrator.py:1461` is bare (no kwarg passed); OTEL span at `orchestrator.py:2223-2229` emits `guardrails_skipped` + `bytes_saved` as hard-wired constants with the `tool_backend` attribute removed. Matches DECISION LOCKED Option (a) in the story context verbatim.

3. **[VERIFIED]** AC-3 loud-fail at config boundary — `llm_factory.py:34-67` is the single chokepoint per architect §B; the `NarratorBackendRetired` exception has a typed inheritance hierarchy (`LlmClientError → NarratorBackendRetired`) so callers can either catch the specific retirement case or the general LLM error.

4. **[SEC]** `cast` at `websocket_session_handler.py:1208` masks a `LlmClient` vs `ToolingLlmClient` protocol-shape mismatch (`AnthropicSdkClient` implements only `complete_with_tools`, not `send_with_model` / `send_with_session` / `send_stateless` / `capabilities`). Production path always injects via `app.state.claude_client_factory` and the autouse test fixture redirects, so the latent footgun is structurally unreachable today. Logged as non-blocking Delivery Finding for follow-up.

5. **[SEC]** `tests/server/conftest.py:458-460` autouse-fixture lambda accepts but ignores `purpose=` kwarg, returning a non-`ToolingLlmClient` fake regardless of caller intent. Test-only concern; dungeon tests have their own per-test monkeypatch for the `purpose="tool"` path. Logged as non-blocking Delivery Finding for follow-up.

6. **[SIMPLE]** simplify-quality flagged a stale dual-path comment at `narrator.py:221-226` during verify phase. TEA applied the fix as commit `05c3d13` ("refactor: simplify code per verify review"). Verified compliant on re-read.

7. **[RULE]** All 14 applicable python.md checks pass on the diff (see Rule Compliance table above). The retiring backend's prose-coupled tests (`test_narrator_output_format_backend_gate.py`, `test_ollama_backend_e2e_48_2.py`) deletions are correctly bounded — non-narrator OllamaClient surface preserved via direct construction in `scripts/ab_eval_harness_cli.py` per spec scope-out.

8. **[VERIFIED]** Commit hygiene — `od -c` byte-dump of all three commits (`3903a06`, `265c864`, `05c3d13`) confirms zero `<system-reminder>` leakage in commit bodies. Per project memory `feedback_implementer_commit_leakage` rule, this is the authoritative check (harness adds the markers to tool output, but the messages on-disk are clean).

9. **[EDGE]** [SUBAGENT DISABLED — `workflow.reviewer_subagents.edge_hunter=false`] Manual edge analysis: `build_llm_client` env-var handling tolerates leading/trailing whitespace via `.strip().lower()` (line 54). `SIDEQUEST_LLM_BACKEND=""` becomes `""` after strip/lower, which is not in `_VALID_BACKENDS` → raises `UnknownBackend` loudly. `SIDEQUEST_LLM_BACKEND` unset → `os.environ.get(..., "anthropic_sdk")` defaults to the SDK path. Boundary inputs handled cleanly.

10. **[SILENT]** [SUBAGENT DISABLED — `workflow.reviewer_subagents.silent_failure_hunter=false`] Manual silent-failure scan of diff: zero new `except` blocks; the only failure mode introduction is the `NarratorBackendRetired` raise (loud-by-design). The `cast` at `websocket_session_handler.py:1208` is a type-system silence, not a runtime silence — already captured as `[SEC]` Observation 4.

11. **[TEST]** [SUBAGENT DISABLED — `workflow.reviewer_subagents.test_analyzer=false`] Manual test-quality scan: TEA's RED-phase 18 tests (17 RED → green, 1 wiring test + 5 sanity passes) all live behind narrow assertions; reflection-based wiring assertions (`inspect.signature`, `hasattr`, `Path.exists`) per project memory `feedback_no_content_coupled_tests`. The test for the gate uses `pytest.raises(NarratorBackendRetired)` rather than catching the broader `LlmClientError`, which preserves the typed-error contract.

12. **[DOC]** [SUBAGENT DISABLED — `workflow.reviewer_subagents.comment_analyzer=false`] Manual doc scan: Dev's green-phase docstring updates at `build_output_format` (narrator.py:250) and `build_llm_client` (llm_factory.py:37) accurately describe the post-61-9 contract. The verify-phase simplify commit fixed the only stale comment (`narrator.py:221-226`). `AUDIT.md` has a new 2026-05-24 entry recording the rename. No misleading/stale docs remain post-`05c3d13`.

13. **[TYPE]** [SUBAGENT DISABLED — `workflow.reviewer_subagents.type_design=false`] Manual type-design scan: `purpose: Literal["narrator", "tool"] = "narrator"` is properly bounded (Literal not str); `NarratorBackendRetired(LlmClientError)` extends the existing typed exception hierarchy; one outstanding issue is the `cast` widening at `websocket_session_handler.py:1208` (already captured as `[SEC]` Observation 4 — same root cause).

### Devil's Advocate

This refactor looks clean — too clean, perhaps. Let me argue it is broken in subtle ways and see what survives.

**Argument 1: "The conftest redirect breaks reachability of the real loud-fail."** The autouse `_mock_claude_client` fixture monkeypatches `websocket_session_handler.build_llm_client` to `lambda *, purpose="narrator": _FakeClaudeClient()`. This means every server test now uses a fake that NEVER raises `NarratorBackendRetired` — so if someone introduces a regression where `purpose="narrator"` accidentally constructs a `ClaudeClient` somewhere downstream, the test suite would not catch it. **Counter:** The factory-level loud-fail is exercised by `test_61_9_sdk_commitment.py::TestNarratorBackendGate` (8 tests) which monkeypatch the env var directly and assert the typed raise — those tests bypass the conftest fixture because they call `build_llm_client()` from the factory module, not through the handler. Verified: the AC-3 contract is locked at the right layer.

**Argument 2: "The cast hides a real type mismatch that will bite in production."** The cast at `websocket_session_handler.py:1208` declares `_client_factory: Callable[[], LlmClient]` but the lambda actually returns an `AnthropicSdkClient` (a `ToolingLlmClient`, not an `LlmClient`). If any code path on the handler calls `self._client_factory().send_with_model(...)`, it will `AttributeError` because `AnthropicSdkClient` doesn't implement that method. **Counter:** The handler's `_client_factory` is invoked only in code paths that already isinstance-guard on `ToolingLlmClient` before calling the SDK tool-use surface; production injection via `app.state.claude_client_factory` provides a properly-shaped factory; tests use the autouse `_FakeClaudeClient` which DOES implement `send_*`. The latent footgun is real but unreachable today. **Conceded:** This is exactly the Delivery Finding I logged — non-blocking, worth a follow-up cleanup.

**Argument 3: "The `_VALID_BACKENDS` set has a `claude` typo."** Wait, no, `claude` is the legitimate name of the retired claude-CLI backend. The first check (`_VALID_BACKENDS`) intentionally accepts the names of retired backends so the second check (`_RETIRED_BACKENDS`) can give the targeted retirement diagnostic. If `claude` were not in `_VALID_BACKENDS`, the user would get "pick one of [anthropic_sdk]" without learning their previously-working setting is now retired. Verified intentional and correct.

**Argument 4: "The OTEL span lost information."** The `narrator.recency_guardrails_skipped` span used to carry a `tool_backend` attribute that distinguished SDK from legacy emission; now it only carries the two hard-wired constants. A future operator looking at the GM panel will not be able to tell which backend was used. **Counter:** Post-61-9 there is no "which backend" — only the SDK can be live. The span's only remaining job is to fire as an "ADR-111 migration engaged" cheap dashboard signal. DECISION LOCKED Option (a) anticipated this exact tradeoff and chose it deliberately.

**Argument 5: "A future operator running the A/B eval CLI will get confused — `claude` works there but raises in the server."** The CLI constructs `ClaudeClient()` directly, bypassing the factory gate. If an operator sets `SIDEQUEST_LLM_BACKEND=claude` in their shell and then `just up`'s the server, they get a loud `NarratorBackendRetired` — but if they then run `python scripts/ab_eval_harness_cli.py`, the CLI happily uses `claude -p`. **Counter:** This is the explicit spec scope-out per architect §A. Adding a similar gate to the harness would prevent the very offline benchmarking work the harness exists to do. Documented behavior, not a bug.

**What survives:** Only Argument 2 (the type-cast widening) — and that is already a confirmed non-blocking Delivery Finding. Nothing else from the devil's-advocate pass uncovers a new severity-blocking issue.

**Handoff:** To SM (Hawkeye Pierce) for finish-story / PR creation and merge.