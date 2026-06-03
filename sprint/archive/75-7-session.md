---
story_id: "75-7"
jira_key: null
epic: "75"
workflow: "tdd"
---
# Story 75-7: Universal retrieval: OTEL retrieval.universal instrumentation + GM-panel surface (ADR-118)

## Story Details
- **ID:** 75-7
- **Jira Key:** None
- **Workflow:** tdd
- **Stack Parent:** 75-5 (depends_on, archived)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T02:08:04Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T01:29:12Z | 2026-06-03T01:37:57Z | 8m 45s |
| red | 2026-06-03T01:37:57Z | 2026-06-03T01:48:09Z | 10m 12s |
| green | 2026-06-03T01:48:09Z | 2026-06-03T01:57:06Z | 8m 57s |
| spec-check | 2026-06-03T01:57:06Z | 2026-06-03T01:58:29Z | 1m 23s |
| verify | 2026-06-03T01:58:29Z | 2026-06-03T02:01:55Z | 3m 26s |
| review | 2026-06-03T02:01:55Z | 2026-06-03T02:07:00Z | 5m 5s |
| spec-reconcile | 2026-06-03T02:07:00Z | 2026-06-03T02:08:04Z | 1m 4s |
| finish | 2026-06-03T02:08:04Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

- **[Gap, non-blocking] (setup/architect scout, 2026-06-02):** The `retrieval.universal` OTEL span is ALREADY built and ships live in 75-5 — `retrieve_turn_context` (`game/retrieval_orchestration.py:178`, attrs `:209-220`), wired per-turn at `websocket_session_handler.py:2500`. Despite the title's "instrumentation," 75-7 is NOT building the span emitter. The real gap is the **GM-panel surface**: the span flows only to OTLP/Jaeger, but the GM dashboard reads **WatcherHub `publish_event`** (`telemetry/watcher_hub.py:534`), and `retrieve_turn_context` emits NO `publish_event`. The span→watcher bridge is one-way (watcher→span only). Fix = add the watcher-emission half, mirroring the dual-emission siblings `entity_sync.sync_for_turn` (`server/dispatch/entity_sync.py:68,78`, `component="retrieval"`) and `lore_embed.retrieve_for_turn`. Scope + ACs in `sprint/context/context-story-75-7.md` reflect this.
- **[Conflict, non-blocking] (architect scout):** 75-5's context filed "per-turn total budget unification" as a "75-7 follow-up." That is a budget-seam change, not instrumentation — scoped OUT of 75-7 (deferred). Candidate Delivery Finding, not a test demand.

### TEA (test design)
- **Improvement** (non-blocking): The current `_retrieve_entities_for_turn` (`sidequest/server/websocket_session_handler.py:2986`) calls `retrieve_turn_context` directly with NO `client=` arg, so the orchestrator constructs `DaemonClient()` from `game/retrieval_orchestration.py`'s own import — which the autouse `_mock_daemon_client` fixture does NOT patch (it patches the `websocket_session_handler` and `lore_embedding` namespaces only). Dev's new `universal_retrieval.retrieve_for_turn` should preserve this call shape; the wiring test patches `retrieval_orchestration.DaemonClient` itself to force a deterministic `query_failed`. *Found by TEA during test design.*
- **Question** (non-blocking): `retrieve_turn_context` is contractually "NEVER raises," so the only realistic emit-path failure is inside `publish_event`. The failure-isolation tests therefore target the emit step (publish raises → swallowed, result still returned), NOT a forced `retrieve_turn_context` raise — forcing the orchestrator to raise and still demanding a `RetrievedEntities` back would be an unreasonable contract. If Dev believes the wrapper should also guard a retrieve raise, surface it; current tests do not demand it. *Found by TEA during test design.*

### Reviewer (code review)
- **Improvement** (non-blocking): `tests/server/dispatch/test_universal_retrieval_dispatch.py:162` uses `asyncio.iscoroutinefunction()`, deprecated and slated for removal in Python 3.16. Affects that test file (swap to `inspect.iscoroutinefunction()`). Trivial future-proofing; not blocking. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `universal_retrieval.py:92` logs `error=%s` on the emit-failure path; `error=%r` would bound exception repr. Affects `sidequest/server/dispatch/universal_retrieval.py` (optional; note the codebase pattern at `retrieval_orchestration.py:253` also uses `%s`, so leave-as-is is defensible). *Found by Reviewer during code review (via reviewer-security).* 
- **Improvement** (non-blocking): If GM-panel scan-consistency is later desired, `query_failed` severity could be promoted `warning`→`error` to match sibling failure events. Affects `sidequest/server/dispatch/universal_retrieval.py:69`. Deliberately NOT changed in 75-7 (warning is semantically correct + spec-compliant). *Found by Reviewer during code review.*

### Dev (implementation)
- **Gap** (non-blocking): PRE-EXISTING failure on `develop`, surfaced by 75-7's full-suite run and FIXED here. `tests/handlers/_harness.py::_StubSession` defined `_retrieve_lore_for_turn` but not `_retrieve_entities_for_turn`, which 75-5 added to the real handler and `player_action.py:496` calls — so `tests/handlers/test_aside_channel_wiring.py::test_aside_is_out_of_band_in_mp` failed with `AttributeError` independent of my change (proven by stashing my impl: the test still failed). Affects `tests/handlers/_harness.py` (added the missing stub, returning `None`, mirroring the lore stub; `_build_turn_context` no-ops on `None`). No production behavior changed. The deeper lesson is a process gap: 75-5 added a handler method consumed by `player_action` without updating the shared `_StubSession` — future handler-method additions should update the stub in lockstep. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

### TEA (test design)
- No deviations from spec. All 7 derived ACs (ADR-118 §D5 + context-story-75-7) have failing-test coverage; out-of-scope items (the span itself, floor+fill logic, budget unification, UI components) are explicitly NOT tested per Scope Boundaries.

### Dev (implementation)
- No deviations from spec. The implementation matches the TEA contract exactly: a `universal_retrieval.retrieve_for_turn` wrapper that calls `retrieve_turn_context`, returns its result unchanged, and publishes the §D5 watcher event; `_retrieve_entities_for_turn` delegates to it. The one out-of-scope edit (a `_StubSession` test-harness fix) is recorded as a Delivery Finding, not a spec deviation — it fixed pre-existing debt that blocked the full suite, with zero production-behavior change.

### Reviewer (audit)
- **TEA "No deviations from spec"** → ✓ ACCEPTED by Reviewer: confirmed — all 7 derived ACs have coverage; out-of-scope items correctly untested. Agrees with author reasoning.
- **Dev "No deviations from spec"** → ✓ ACCEPTED by Reviewer: confirmed — implementation matches the pinned test contract; no spec divergence found in the diff.
- **Dev's out-of-scope `_StubSession` harness fix** (logged as a Delivery Finding) → ✓ ACCEPTED by Reviewer: a legitimate pre-existing-debt fix (proven independent of 75-7 by the stash test), test-only, zero production-behavior change. Correctly logged as a finding rather than a deviation. Reviewer adds a note: ideal practice would be a separate chore commit, but folding a one-line harness fix that unblocks the full suite into this PR is reasonable and is transparently documented.
- **No undocumented deviations found.** The `severity="warning"` choice was surfaced by the verify-phase simplify pass and explicitly ruled ACCEPT in the Reviewer Assessment (it is spec-compliant per AC-4, not a deviation).

### Architect (reconcile)

Reviewed all in-flight deviation entries (TEA, Dev) and the Reviewer audit against the authoritative specs (`sprint/context/context-story-75-7.md`, `sprint/context/context-epic-75.md`, `docs/adr/118-universal-retrieval-layer.md` §D5, and sibling ACs 75-5/75-6/75-8 in `sprint/epic-75.yaml`). Verification:

- **TEA "No deviations from spec"** — accurate. All 7 derived ACs (ADR-118 §D5 + story context) carry failing→passing test coverage; out-of-scope items (the span emitter itself = 75-5, floor+fill logic = 75-5, budget unification = deferred, UI = 75-8/out) are correctly excluded per the context's Scope Boundaries.
- **Dev "No deviations from spec"** — accurate. The shipped `universal_retrieval.retrieve_for_turn` matches the pinned contract: calls `retrieve_turn_context`, returns `RetrievedEntities` unchanged, publishes the §D5 `state_transition` event (`component="retrieval"`, `field="universal_retrieval"`, `op=<outcome>`, full count set, `turn_number`); the handler delegates on the live `:2500` seam. Spec source paths and behavior descriptions in the Dev entry are correct.
- **Reviewer audit** — concur with all three ACCEPTED stamps and the "no undocumented deviations" finding.

**Severity `warning` vs sibling `error` (the only contested point):** NOT a deviation. ADR-118 §D5 mandates a distinct non-silent `outcome` per failure path but does not pin the watcher-event severity band; the story context AC-4 explicitly permitted non-`info` (warning OR error). `query_failed` is an *expected, recorded* degradation, not a caught exception (the band the siblings reserve `error` for), so `warning` is within spec. Reviewer ruled ACCEPT; I confirm.

**AC deferrals:** None. All 7 ACs DONE (none DEFERRED/DESCOPED) — the AC-deferral cross-check is a no-op.

**Out-of-scope `_StubSession` harness fix:** correctly classified as a pre-existing-debt Delivery Finding (proven independent of 75-7), not a spec deviation. No reclassification needed.

- **No additional deviations found.**

## Sm Assessment

**Setup complete — handing off to TEA (RED phase).**

- Story 75-7 (3pt, tdd, p2) set up in `sidequest-server` (base branch `develop`; gitflow — PR targets server's `develop`, not the orchestrator). Session-tracking branch `feat/75-7-universal-retrieval-otel` on the orchestrator.
- Dependency 75-5 is DONE (archived); sibling 75-6 (entity sync) merged. No Jira key (X-Y id only) → Jira step skipped.
- Story context written and validated: `sprint/context/context-story-75-7.md` (`pf validate context-story 75-7` → OK). Authored scout-grounded by Architect, matching the 75-6 gold-standard format.
- **Scope-shaping finding (see Delivery Findings):** the `retrieval.universal` span already exists from 75-5; the genuine deliverable is the **GM-panel surface** — adding the WatcherHub `publish_event` (watcher-emission) half so the retrieval decision reaches the GM lie-detector dashboard. Mirror dual-emission siblings `entity_sync.sync_for_turn` / `lore_embed.retrieve_for_turn`. TEA should write RED tests against the **watcher-emission + GM-panel wiring**, not re-test the existing OTLP span. A wiring test (span/event reaches the GM panel) is a required AC.
- Budget-seam unification is explicitly OUT of scope (deferred).

**TEA focus:** Failing tests for the `retrieval.universal` WatcherHub emission + GM-panel surface, including the mandatory wiring test, failure-isolation (retrieval failure must not kill the turn's narration), and zero-byte-leak skip semantics. Meaningful assertions only — assert event attribute values, not `is not None`.

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** Net-new backend behavior (a WatcherHub emission + handler delegate) with a doctrine-mandated wiring requirement (OTEL/GM-panel observability). Not a chore-bypass candidate.

**Test Files:**
- `sidequest-server/tests/server/dispatch/test_universal_retrieval_dispatch.py` — 17 failing tests for the universal-retrieval GM-panel watcher emission + handler delegate.

**Tests Written:** 17 tests covering all 7 derived ACs (+ paranoia cases).
**Status:** RED (failing — ready for Dev). Verified via `testing-runner` (RUN_ID `75-7-tea-red`): 17 failed, 0 passed, file collected cleanly, every failure a clean `ImportError` on the not-yet-existing `sidequest.server.dispatch.universal_retrieval` (GOOD red — zero test-code bugs). Test file passes `ruff check` + `ruff format`.

**Contract the suite pins (the test IS the spec):**
- New module `sidequest.server.dispatch.universal_retrieval` exposing `async def retrieve_for_turn(handler, sd, action) -> RetrievedEntities`.
- It calls the 75-5 `retrieve_turn_context` (imported into the module namespace; passes `current_turn=snapshot.turn_manager.interaction`) and **returns the result unchanged**.
- It publishes ONE `publish_event("state_transition", {field:"universal_retrieval", op:<outcome>, budget_total, floor_count, floor_token_cost, fill_candidate_count, fill_selected_count, fill_token_cost, npc_count, location_count, faction_count, rejected_below_similarity, dimension_mismatch_count, turn_number}, component="retrieval", severity=...)` via the module-level `_watcher_publish` alias (so it's monkeypatchable, mirroring siblings).
- `severity="info"` for success; non-`info` for `query_failed`.
- Emission is wrapped: a `publish_event` raise is logged + swallowed; the result is still returned.
- `WebSocketSessionHandler._retrieve_entities_for_turn` delegates to `universal_retrieval.retrieve_for_turn` (the live seam at `websocket_session_handler.py:2500`), replacing today's direct `retrieve_turn_context` call.

### AC / Rule Coverage

| AC / Rule | Test(s) | Status |
|-----------|---------|--------|
| Module surface + async (lang-review: await-on-coroutine) | `test_dispatch_module_exposes_retrieve_for_turn` | failing |
| Delegate wiring (CLAUDE.md wiring) | `test_handler_delegate_calls_retrieve_for_turn`, `test_retrieve_for_turn_returns_orchestrator_result_unchanged`, `test_retrieve_for_turn_passes_current_turn_to_orchestrator` | failing |
| AC-2 core emission | `test_emits_state_transition_for_retrieval_component` | failing |
| AC-3 lossless §D5 counts + per-type sum invariant | `test_event_carries_all_d5_counts_losslessly`, `test_per_type_counts_are_zero_when_type_absent` | failing |
| AC-4 distinct outcomes (No Silent Fallbacks) + severity | `test_outcome_string_reaches_event_uncoerced[4 params]`, `test_query_failed_event_severity_is_not_info` | failing |
| AC-5 zeroed clean-skip event | `test_no_candidates_publishes_zeroed_event_not_suppressed` | failing |
| AC-6 failure isolation (lang-review: error paths logged) | `test_publish_failure_is_swallowed_and_result_returned`, `test_narration_turn_survives_emit_failure` | failing |
| AC-7 production-path wiring (real `watcher_hub` subscriber; no source-grep) | `test_event_reaches_watcher_hub_subscriber_via_handler` | failing |
| AC-1 span regression (no double-emit) | `test_wrapper_does_not_double_emit_the_universal_span` | failing |

**Rules checked:** Python lang-review applicable rules covered — type annotations (all test sigs), error-paths-logged (failure-isolation tests), await-on-coroutine (module-surface test asserts `iscoroutinefunction`), meaningful-assertions (self-checked below). No `.claude/rules/` dir in repo.
**Self-check:** 0 vacuous tests. Every test asserts concrete field VALUES / outcome strings / span counts — no `assert x is not None` where a value is the contract, no `assert True`, no source-text grep (wiring test drives the real handler + a real hub subscriber per server CLAUDE.md "No Source-Text Wiring Tests").

**Handoff:** To Dev (Agent Smith) for GREEN — implement `sidequest.server.dispatch.universal_retrieval.retrieve_for_turn` + wire `_retrieve_entities_for_turn` to delegate to it.

---
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/server/dispatch/universal_retrieval.py` (NEW) — `async def retrieve_for_turn(handler, sd, action) -> RetrievedEntities`: wraps the 75-5 `retrieve_turn_context` (returns its result unchanged), then publishes the ADR-118 §D5 `state_transition` watcher event (`component="retrieval"`, `field="universal_retrieval"`, `op=<outcome>`, full count set, `turn_number`). Emission wrapped in try/except → logged + swallowed (turn never crashes). `severity="warning"` for `query_failed`, else `"info"`.
- `sidequest-server/sidequest/server/websocket_session_handler.py` — `_retrieve_entities_for_turn` now delegates to `universal_retrieval.retrieve_for_turn` (the live per-turn seam at `:2500`), mirroring the lore sibling's decomposition. Behavior preserved: same args, same `current_turn`, same return.
- `sidequest-server/tests/handlers/_harness.py` — added the missing `_retrieve_entities_for_turn` stub to `_StubSession` (pre-existing harness gap; see Delivery Findings).

**Tests:** GREEN.
- Story file `tests/server/dispatch/test_universal_retrieval_dispatch.py`: 17/17 passing (RUN_ID `75-7-dev-green`).
- Adjacent suites (entity_sync dispatch, lore_embed, retrieval_orchestration): 33 passing, no regressions.
- **Full server suite: 9741 passed, 0 failed, 361 skipped** (RUN_ID `75-7-dev-green-full2`). The pre-existing `test_aside_is_out_of_band_in_mp` failure is now fixed.
- `ruff check` + `ruff format` clean on all changed files.

**Branch:** `feat/75-7-universal-retrieval-otel` (pushed to origin/sidequest-server; PR target `develop`).

**Self-review:**
- ✅ Wired to production: `universal_retrieval.retrieve_for_turn` is called by `_retrieve_entities_for_turn`, which fires on the live per-turn path (`websocket_session_handler.py:2500`) — real non-test consumer (satisfies wiring-check + the wiring test).
- ✅ Follows project patterns: dual-emission (span in game tier + watcher event in server dispatch tier), `_watcher_publish` alias, `component="retrieval"` — identical shape to `entity_sync.sync_for_turn` and `lore_embed.retrieve_for_turn`.
- ✅ All ACs met (17 tests). ✅ Error handling: emission isolated + logged (No Silent Fallbacks: real outcome string always carried).
- Minimalist: no abstractions beyond the test contract; the wrapper observes and returns, nothing more.

**Handoff:** To Reviewer (The Merovingian) for code review.

---
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None substantive (2 trivial observations below)

Structural gate (`gates/spec-check`) passes: AC coverage present in Dev Assessment, implementation marked complete, TEA + Dev deviation subsections well-formed. Substantive review of the production diff (`universal_retrieval.py` + the `_retrieve_entities_for_turn` delegate) against all 7 derived ACs (ADR-118 §D5 + `context-story-75-7.md`) — which I authored at setup — confirms alignment:

- AC-1 (span intact / no double-emit): the wrapper only *calls* `retrieve_turn_context`; it opens no span. ✓
- AC-2/3 (event + lossless §D5 counts): `state_transition` / `component="retrieval"` / `field="universal_retrieval"` / `op=<outcome>` with all 12 §D5 attributes; per-type counts via `len(retrieved_* or [])`. ✓
- AC-4 (uncoerced outcome + severity): `op=result.outcome` verbatim; `severity="warning"` for `query_failed`, else `"info"`. ✓ (No Silent Fallbacks honored.)
- AC-5 (zeroed clean-skip, not suppressed): emission is unconditional; empty fill → per-type 0. ✓
- AC-6 (failure isolation): `publish` wrapped in try/except → `logger.warning` + swallow; result returned regardless. ✓ (ADR-006.)
- AC-7 (wiring): `_retrieve_entities_for_turn` delegates on the live per-turn seam (`websocket_session_handler.py:2500`); real non-test consumer. ✓

**Trivial observations (recommend A — accept as-is; no action):**
- **Single outcome key** (Cosmetic — Trivial): the sibling `entity_sync` event carries both `op` and a separate `outcome` key; this event carries the outcome only under `op`. This matches the authored contract (context line 119 specified `op=<outcome>`) and the pinned tests — aligned, not drift.
- **Severity scope** (Behavioral — Trivial): only `query_failed` is non-`info`; `budget_exhausted`/`no_candidates` stay `info`. The spec (AC-4) mandated non-`info` only for `query_failed`; these are legitimate decisions, not errors. Reasonable, spec-aligned. If the GM later wants `budget_exhausted` flagged, that's a tuning follow-up, not a 75-7 defect.

The out-of-scope `_StubSession` harness fix is correctly an **Extra in code** (Cosmetic/test-infra, Trivial) — fixes pre-existing debt, zero production-behavior change, already logged as a Dev Delivery Finding. Accept (A).

**Decision:** Proceed to verify (TEA).

---
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (no changes applied → Dev's full-suite GREEN of 9741 passed stands; lint clean on all 4 changed files; working tree clean)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (`universal_retrieval.py`, `websocket_session_handler.py`, `tests/handlers/_harness.py`, `tests/server/dispatch/test_universal_retrieval_dispatch.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | Sibling structural similarity (`entity_sync`/`lore_embed`) is the intended, doctrine-mandated pattern — not extractable dup. |
| simplify-quality | 2 findings | (1) medium: `severity` divergence; (2) low: harness import path. |
| simplify-efficiency | clean | Thin wrapper; per-field dict + failure-isolation try/except are spec-required (ADR-118 §D5), not over-engineering. |

**Applied:** 0 high-confidence fixes (none were high-confidence).
**Flagged for Review:** 2 findings (1 medium, 1 low) — see below.
**Reverted:** 0.

**Overall:** simplify: clean (no fixes applied; 2 findings flagged for Reviewer judgment)

#### Flagged for Reviewer (The Merovingian)

1. **[medium] Severity divergence — `query_failed` is `"warning"`, siblings use `"error"`** (`universal_retrieval.py:69`). simplify-quality recommends `"error"` for cross-subsystem GM-panel consistency. **TEA analysis (do not auto-apply — genuine judgment call):** the siblings (`entity_sync.py`, `lore_embed.py`) reserve `severity="error"` for their `except Exception` paths (caught crashes → `op="failed"`). `query_failed` here is NOT an exception — it is an *expected, recorded* degradation outcome returned by `retrieve_turn_context` (daemon unavailable / blank query / embed failed), semantically closer to a warning. The context AC-4 explicitly permitted non-`info` (warning OR error); `"warning"` is spec-compliant and arguably more semantically correct. Switching to `"error"` would keep all 17 tests green (they assert `!= "info"`). Reviewer/Keith to decide whether GM-panel scan-consistency outweighs the semantic distinction. Not blocking.
2. **[low] Harness import path** (`tests/handlers/_harness.py:46`) — imports `_SessionData`/`_State` from `websocket_session_handler` (works via documented re-export) rather than the canonical `session_state`. Cosmetic, test-only, no behavior impact. The line I touched (the new stub) doesn't introduce this; it's the file's existing convention. Defer/accept.

**Quality Checks:** `ruff check` passing (4 changed files); full suite GREEN (9741 passed, 0 failed — Dev RUN_ID `75-7-dev-green-full2`, unchanged since).
**Handoff:** To Reviewer (The Merovingian) for code review.

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; 17/17 story tests + 227 broader pass; lint/format PASS; 1 low note (deprecated `asyncio.iscoroutinefunction` in test) | confirmed 1 (LOW), dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — assessed by Reviewer directly ([EDGE]) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — assessed by Reviewer directly ([SILENT]) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer directly ([TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer directly ([DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed by Reviewer directly ([TYPE]) |
| 7 | reviewer-security | Yes | findings | 1 LOW info-leak nit (`error=%s` vs `%r`, line 92); 0 rule violations across 4 rules | confirmed 1 (LOW), dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — covered by verify-phase simplify fan-out (reuse/quality/efficiency) + Reviewer ([SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — Reviewer did the rule-by-rule enumeration directly ([RULE], see Rule Compliance) |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents` and assessed directly)
**Total findings:** 2 confirmed (both LOW, non-blocking), 0 dismissed, 0 deferred

---
## Reviewer Assessment

**Verdict:** APPROVED

**Summary:** A tight, doctrine-correct change. The new `universal_retrieval.retrieve_for_turn` adds the watcher-emission half of the `retrieval.universal` observability path (ADR-118 §D5), mirroring the established `entity_sync` / `lore_embed` sibling pattern exactly. No Critical/High findings. Two LOW non-blocking nits noted. Full suite GREEN (9741 passed).

**Data flow traced:** player `action` → `PlayerActionHandler.handle` (sanitized at `player_action.py:287`) → `_retrieve_entities_for_turn` → `universal_retrieval.retrieve_for_turn` → `retrieve_turn_context` (embeds `action` as a daemon query; sanitizes retrieved card content at `retrieval_orchestration.py:144`). The wrapper returns the result unchanged and publishes only integer counts + the controlled `outcome` enum + `turn_number` to the WatcherHub. **No player text, card content, embeddings, secrets, or PII reach the dashboard stream** (confirmed by [SEC]).

**Pattern observed:** Dual-emission dispatch sibling (`universal_retrieval.py:46-103`) — game-tier span stays in `retrieve_turn_context`, server-tier watcher event lives in the dispatch module; handler delegates lazily (`websocket_session_handler.py:2994`) to avoid the server↔dispatch import cycle. Identical shape to `lore_embed.retrieve_for_turn` / `entity_sync.sync_for_turn`. Correct reuse, not reinvention.

**Error handling:** The emit is wrapped in try/except → `logger.warning` + swallow (`universal_retrieval.py:90-96`) — ADR-006 carve-out scoped to the *observability* emit only. `retrieve_turn_context` is OUTSIDE the try, so real orchestrator failures propagate exactly as before (no regression vs the old inline call). The real `outcome` string is always carried uncoerced — No Silent Fallbacks honored.

### Observations (subagent findings tagged by source)

- `[VERIFIED]` Watcher payload carries no sensitive data — `universal_retrieval.py:78-92` publishes one hardcoded `field`, the controlled `outcome` enum under `op`, nine integer counts, and `turn_number`. Complies with the GM-panel-is-dev-observability rule (no player text / PII). Evidence + 4-rule clearance from [SEC].
- `[VERIFIED]` Failure isolation correct — `retrieve_turn_context` call at `:59-64` is outside the try; only `_watcher_publish` is wrapped (`:68-96`). Orchestrator failures cannot be masked. Complies with ADR-006.
- `[VERIFIED]` No Silent Fallbacks — `op=result.outcome` (`:74`) verbatim; emit failure logged loud. All four outcome strings surface distinctly (tests pin this).
- `[SEC][LOW]` `logger.warning("...error=%s", ..., exc)` at `universal_retrieval.py:92` uses `%s` not `%r`. Low risk for the actual exception types (publish serialize / asyncio). **Decision: ACCEPT (non-blocking)** — `%s` is consistent with the established codebase pattern (`retrieval_orchestration.py:253` uses `error=%s exc`); normalizing to `%r` across both is an optional future nit, not a defect in this diff.
- `[LOW]` (preflight) Deprecated `asyncio.iscoroutinefunction()` at `test_universal_retrieval_dispatch.py:162` (removed in Python 3.16). **Decision: ACCEPT (non-blocking)** — test-only, future-cleanup; recorded as a Delivery Finding.
- `[SIMPLE]` Verify-phase fan-out (reuse/quality/efficiency) returned clean except the severity nit below — confirmed: thin wrapper, no over-engineering, sibling similarity is the intended pattern.
- `[EDGE]` `None` fill lists handled via `len(result.retrieved_* or [])` → count 0 (`:85-87`); empty/`no_candidates`/`budget_exhausted`/`query_failed` all covered by tests. No unhandled boundary.
- `[TEST]` 17 tests assert concrete field VALUES + a real production-path wiring test (subscribes a fake `_Sendable` to the live `watcher_hub`, asserts delivery) — not source-grep. High quality; one LOW deprecation (above).
- `[DOC]` Module + function docstrings accurate and ADR-cited; inline comments correct (the `_FAILURE_OUTCOME` rationale, the ADR-006 swallow comment). No stale/misleading docs.
- `[TYPE]` Returns `RetrievedEntities` (typed); all params/return annotated; `_SessionData`/handler under TYPE_CHECKING. `outcome` remains a `str` — established 75-5 contract, out of scope to newtype here.

### Severity table

| Severity | Issue | Location | Disposition |
|----------|-------|----------|-------------|
| [LOW] | `error=%s` could be `%r` | `universal_retrieval.py:92` | Accept (consistent with codebase pattern) |
| [LOW] | Deprecated `asyncio.iscoroutinefunction` | `test_universal_retrieval_dispatch.py:162` | Accept (future cleanup; Delivery Finding) |
| [LOW] | `severity="warning"` vs siblings' `"error"` for failure | `universal_retrieval.py:69` | Accept (see ruling below) |

**Ruling on the verify-phase MEDIUM (severity warning vs error):** ACCEPT `"warning"`. The siblings reserve `severity="error"` for their `except Exception` paths (caught *crashes* → `op="failed"`). `query_failed` here is an *expected, recorded* degradation outcome returned by `retrieve_turn_context` (daemon unavailable / blank query / embed error), not a caught exception — `"warning"` is the semantically correct band and is explicitly spec-compliant (context AC-4 permitted non-`info`). Downgraded MEDIUM→LOW; no change required. If Keith later wants all retrieval-subsystem signals at one severity for GM-panel scan-consistency, that's a trivial tuning follow-up, not a 75-7 defect.

### Rule Compliance (Python lang-review — enumerated, rule-checker disabled so done directly)

- **Type annotations on all params + returns:** `retrieve_for_turn(handler, sd, action) -> RetrievedEntities` — all annotated ✓. Stub `_retrieve_entities_for_turn(self, sd, action) -> None` ✓.
- **Error paths logged (`logger.error`/`warning`):** the one error path (`except` at `:90`) logs `logger.warning` ✓.
- **`await` on coroutines:** `await retrieve_turn_context(...)` (`:59`) ✓; handler `return await universal_retrieval.retrieve_for_turn(...)` ✓.
- **No bare `except` / justified broad catch:** `except Exception` with `# noqa: BLE001` + rationale comment, matching siblings ✓.
- **Meaningful test assertions (no vacuous):** verified — every test asserts field values / outcome strings / span counts; the production-path wiring test asserts real delivery, no source-grep ✓.
- **No Silent Fallbacks:** outcome carried verbatim; emit failure logged ✓.
- **Input validation / sanitization:** `action` sanitized upstream (`player_action.py:287`); card content sanitized in orchestrator; wrapper adds no new unsanitized path ✓.

### Devil's Advocate

Let me argue this code is broken. **The watcher event fires unconditionally on every turn** — could that flood the GM panel or the 2000-event replay buffer (`watcher_hub.py:97`)? At one universal-retrieval event per turn plus the sibling lore/entity-sync events, the buffer holds ~130 turns; that's an accepted, documented "lossy by design" bound, and 75-7 adds exactly one event per turn, the same cadence as its siblings — no new flood vector. **What if `result.outcome` were attacker-controlled?** It can't be — it's one of four module-level constants in the frozen `RetrievedEntities`, never derived from player input (confirmed [SEC]). **What if `publish_event` blocks or deadlocks?** `watcher_hub.publish` is non-blocking — it schedules `run_coroutine_threadsafe` and returns, or drops if no loop is bound; it cannot stall the turn. **What if the daemon is down for an entire session?** Every turn emits `query_failed` at `severity="warning"` — visible, distinct, non-crashing; the player still gets narration (the retrieval failure is isolated upstream in 75-5). **Could the wrapper double-count or desync from the span?** No — it reads the same `RetrievedEntities` the span was built from, in the same call; AC-1's regression test asserts exactly one span and the wrapper opens none. **What about a confused operator misreading the panel?** The `field="universal_retrieval"` + `component="retrieval"` grouping matches entity-sync, so the subsystem reads coherently. **The one real residual:** if a future `publish_event` exception carried a sensitive string, `%s` would log it verbatim ([SEC] LOW) — but current exception types don't, and it'd land in server logs (operator-only), not the player surface. Nothing here rises to blocking. The change is small, isolated, well-tested, and observability-only — the blast radius is a dashboard event, not game state.

### Deviation audit — see `### Reviewer (audit)` under Design Deviations.

**Handoff:** To SM (Morpheus) for finish-story.