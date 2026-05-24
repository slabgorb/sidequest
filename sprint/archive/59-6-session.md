---
story_id: "59-6"
jira_key: "none"
epic: "none"
workflow: "tdd"
---
# Story 59-6: Scenario_clue dispatch handler — supplements footnotes (no retirement)

## Story Details
- **ID:** 59-6
- **Jira Key:** none (oq-2 is not Jira-tracked)
- **Workflow:** tdd
- **Stack Parent:** 59-4 (feat/59-4-confrontation-cutover-router-wiring)
- **Points:** 3

## Context

This story implements a `scenario_clue` dispatch handler within the Intent Router (ADR-113) epic. The handler supplements narration footnotes but does NOT retire the sidecar — it coexists with the current tool-use and JSON extraction path.

**Prior context:** Stories 59-1 through 59-5 established the dispatch handler pattern:
- 59-1: dispatch router foundation
- 59-2: event_cue handler (creates encounter beats)
- 59-3: npc_disposition handler (tracks NPC state)
- 59-4: confrontation_cutover handler (routes confrontations)
- 59-5: magic_working handler (magic system integration)

This story (59-6) adds scenario_clue dispatch to surface scenario footnotes as mechanical signals.

**Related ADRs:**
- ADR-113: Intent Router — Mechanical-Engagement Spine
- ADR-100: Journal Pipeline Coherence — Footnotes, KnownFacts, JOURNAL_RESPONSE, and the Scenario Clue Hook
- ADR-053: Scenario System (Clue Graph, Belief State, Gossip Propagation)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-24T23:52:30Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24T00:00:00Z | 2026-05-24T22:50:40Z | 22h 50m |
| red | 2026-05-24T22:50:40Z | 2026-05-24T23:03:37Z | 12m 57s |
| green | 2026-05-24T23:03:37Z | 2026-05-24T23:12:40Z | 9m 3s |
| spec-check | 2026-05-24T23:12:40Z | 2026-05-24T23:18:43Z | 6m 3s |
| verify | 2026-05-24T23:18:43Z | 2026-05-24T23:41:56Z | 23m 13s |
| review | 2026-05-24T23:41:56Z | 2026-05-24T23:48:38Z | 6m 42s |
| spec-reconcile | 2026-05-24T23:48:38Z | 2026-05-24T23:52:30Z | 3m 52s |
| finish | 2026-05-24T23:52:30Z | - | - |

## Sm Assessment

Story 59-6 adds a `scenario_clue` dispatch handler to the Intent Router (ADR-113). This follows the established pattern from 59-1 through 59-5 — each story adds a handler that supplements narrator footnotes with mechanical signals. This handler focuses on scenario clues (ADR-100, ADR-053) and coexists with the existing sidecar; no retirement.

- **Repos:** sidequest-server only
- **Branch:** feat/59-6-scenario-clue-dispatch (off develop)
- **Workflow:** TDD (phased) — next phase: red (TEA writes failing tests)
- **Risk:** Low — follows established dispatch handler pattern from prior stories in the epic
- **Stack note:** depends_on 59-4; branched off develop since 59-4 isn't merged yet

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story adds a new dispatch handler — requires unit, idempotency, wiring, and regression tests

**Test Files:**
- `tests/agents/subsystems/test_scenario_clue_dispatch.py` — 12 tests covering all 4 ACs

**Tests Written:** 12 tests covering 4 ACs
**Status:** RED (8 failing, 4 passing — ready for Dev)

### Failing (8 — handler does not exist yet):
| Test | AC | Error |
|------|-----|-------|
| `test_scenario_clue_handler_discovers_clue_on_snapshot` | AC1 | ModuleNotFoundError |
| `test_scenario_clue_handler_mints_known_fact_on_first_discovery` | AC1 | ModuleNotFoundError |
| `test_scenario_clue_handler_noop_when_no_scenario_state` | AC1 | ModuleNotFoundError |
| `test_scenario_clue_handler_prerequisite_not_satisfied_does_not_raise` | AC1 | ModuleNotFoundError |
| `test_handler_then_footnote_does_not_double_mint_known_fact` | AC3 | ModuleNotFoundError |
| `test_footnote_then_handler_does_not_double_mint_known_fact` | AC3 | ModuleNotFoundError |
| `test_scenario_clue_handler_registered_with_dispatch_bank` | Wiring | AssertionError (not in registry) |
| `test_run_dispatch_bank_invokes_scenario_clue_handler` | Wiring | AssertionError (clue not discovered) |

### Passing (4 — existing coverage verification):
| Test | AC | Verification |
|------|-----|-------------|
| `test_footnote_path_still_discovers_clues` | AC2 | Footnote path unchanged |
| `test_lie_detector_emits_mismatch_when_scenario_clue_dispatched_not_engaged` | AC4 | 59-3 watcher coverage |
| `test_lie_detector_no_false_positive_when_scenario_clue_engaged` | AC4 | No false positive |
| `test_lie_detector_mismatch_when_no_scenario_state` | AC4 | Edge: None scenario_state |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 type annotations | handler signature coverage via AC1 tests | failing (handler DNE) |
| #6 test quality | self-check: all tests have meaningful assertions | clean |
| #9 async/await | handler is async, tested with pytest-asyncio | failing (handler DNE) |
| #10 import/__all__ | `test_scenario_clue_handler_registered_with_dispatch_bank` | failing |
| #14 state cleanup | AC3 idempotency tests verify no double-mint | failing (handler DNE) |
| CLAUDE.md wiring | `test_run_dispatch_bank_invokes_scenario_clue_handler` | failing |
| No silent fallbacks | `test_scenario_clue_handler_noop_when_no_scenario_state` | failing (handler DNE) |
| OTEL observability | handler delegates to consume_clue_footnotes → SPAN_SCENARIO_ADVANCE | failing (handler DNE) |

**Rules checked:** 8 applicable rules have test coverage
**Self-check:** 0 vacuous tests found

**Implementation guidance for Dev:**
1. Create `sidequest/agents/subsystems/scenario_clue.py` with `run_scenario_clue_dispatch`
2. Handler signature: `async def run_scenario_clue_dispatch(dispatch, *, snapshot, player_name="")`
3. Handler builds a `Footnote` from `dispatch.params` and calls `consume_clue_footnotes`
4. Register handler in `subsystems/__init__.py:_register_defaults()` under `"scenario_clue"`
5. Update module docstring in `__init__.py` to list scenario_clue

**Handoff:** To Ponder Stibbons (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/agents/subsystems/scenario_clue.py` — new handler module: `run_scenario_clue_dispatch` builds a synthetic `Footnote` from `dispatch.params` and delegates to `consume_clue_footnotes`
- `sidequest/agents/subsystems/__init__.py` — registered `scenario_clue` handler in `_register_defaults()`, updated module docstring

**Tests:** 12/12 passing (GREEN)
**Branch:** feat/59-6-scenario-clue-dispatch (pushed)

**Handoff:** To Igor (TEA) for verify phase

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All four ACs verified against the implementation:
- **AC1** — Handler builds `Footnote` from `dispatch.params` and delegates to `consume_clue_footnotes`. Discovery lands in `discovered_clues`, `KnownFact` minted on active character. Matches spec.
- **AC2** — No changes to `scenario_clue_intake.py` or the narration_apply consumer. Footnote path stays alive. Matches spec ("supplements without retiring").
- **AC3** — Both paths converge on `ScenarioState.discover_clue` which is idempotent. The `is_new` guard in `consume_clue_footnotes` prevents double-mint. Tests verify both orderings. Matches spec.
- **AC4** — Watcher coverage for `scenario_clue` confirmed passing (shipped in 59-3). No new watcher code needed.

Implementation reuses existing infrastructure (`consume_clue_footnotes`, `Footnote`, `SubsystemOutput`) with zero new abstractions. Follows the sibling handler pattern (59-5 `magic_working`) exactly. The module-level docstring correctly documents the supplementing (non-retirement) nature.

**Decision:** Proceed to verify

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | test fixture duplication from intake tests (high), _package_with extractable (medium), params unpacking (low) |
| simplify-quality | 2 findings | undocumented exception contract (medium), is_new=True redundancy (low — incorrect, field is required) |
| simplify-efficiency | 2 findings | _open_viz() as constant (high — dismissed, matches 59-5 convention), snapshot factory consolidation (medium) |

**Applied:** 0 high-confidence fixes (all dismissed — either match established sibling patterns or are incorrect)
**Flagged for Review:** 3 medium-confidence findings (fixture extraction, exception docs, factory consolidation)
**Noted:** 3 low-confidence observations
**Reverted:** 1 (testing-runner made unauthorized changes to output_only.md and advance_confrontation.py — reverted immediately)

**Overall:** simplify: clean

**Quality Checks:** All passing (ruff clean, 12/12 tests GREEN)
**Handoff:** To Granny Weatherwax (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 3 | dismissed 3 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 returned, 7 disabled)
**Total findings:** 0 confirmed, 3 dismissed (with rationale), 0 deferred

### Security Findings Dismissed

1. **fact_id injection (medium)** — Dismissed: `consume_clue_footnotes:62` gates all downstream effects with `if fn.fact_id not in clue_ids: continue`. Unknown fact_ids never reach `discover_clue` or `KnownFact` minting. Transient Footnote is discarded.
2. **category ValidationError (medium)** — Dismissed: Pydantic's `FactCategory(StrEnum)` rejects invalid values; `ValidationError` propagates to bank executor at `__init__.py:255-265` which catches per-dispatch exceptions and records error spans. Same pattern as `MagicWorkingParseError` in sibling handler.
3. **player_name="" default (medium)** — Dismissed: Identical to `magic_working.py:40`. Bank call site at `intent_router_pass.py:132` always supplies `player_name` from session handler. Empty default is test convenience, not production path.

## Reviewer Assessment

**Verdict: APPROVE**

### Observations

1. [VERIFIED] Handler delegates to `consume_clue_footnotes` correctly — `scenario_clue.py:56` call matches function signature at `scenario_clue_intake.py:34`. Wiring is correct.
2. [VERIFIED] `dispatch.params["fact_id"]` bare access at line 51 raises `KeyError` on missing key — correct fail-loud per "No Silent Fallbacks." Matches watcher pattern at `dispatch_engagement_watcher.py:106`.
3. [VERIFIED] Registration at `__init__.py:144` — `run_scenario_clue_dispatch` imported and registered under `"scenario_clue"` in `_register_defaults()`. Follows pop-then-insert pattern used by all handlers.
4. [VERIFIED] `__all__ = ["run_scenario_clue_dispatch"]` at line 60 — complies with Python lang-review #10 (import hygiene).
5. [VERIFIED] Async handler calling sync `consume_clue_footnotes` — safe, no blocking I/O inside (only in-memory state mutation). Complies with Python #9 (async/await pitfalls).
6. [VERIFIED] No mutable default arguments — `player_name: str = ""` is immutable. Complies with Python #2.
7. [VERIFIED] OTEL coverage — bank emits `intent_router_subsystem_span` per dispatch (line 232-235), `discover_clue` emits `SPAN_SCENARIO_ADVANCE`. Two-layer OTEL matches sibling handlers.
8. [SEC] fact_id injection path — dismissed: `consume_clue_footnotes:62` gates all downstream effects with clue_ids membership check. Unknown fact_ids never persist.
9. [SEC] category ValidationError propagation — dismissed: bank executor catches per-dispatch exceptions at `__init__.py:255`. Same error path as sibling handlers.
10. [SEC] player_name="" silent data loss — dismissed: identical default to `magic_working.py:40`; bank always supplies value from session handler at `intent_router_pass.py:132`.

### Rule Compliance

| Rule | Scope | Verdict |
|------|-------|---------|
| No Silent Fallbacks | `dispatch.params["fact_id"]` KeyError propagation | Compliant |
| No Stubbing | Handler is real implementation | Compliant |
| OTEL Observability | Bank span + discover_clue span | Compliant |
| Every Test Suite Needs a Wiring Test | 2 wiring tests (registration + bank) | Compliant |
| No Source-Text Wiring Tests | `get_registered()` reflection | Compliant |
| Python #1 Silent exceptions | No try/except in handler | N/A |
| Python #2 Mutable defaults | `player_name: str = ""` | Compliant |
| Python #3 Type annotations | Full annotations on public function | Compliant |
| Python #9 Async/await | Sync callee, no blocking I/O | Compliant |
| Python #10 Import/__all__ | `__all__` exported | Compliant |

### Devil's Advocate

What if this code is broken? Let me argue the case.

**Missing fact_id**: If the router emits a dispatch without `fact_id` in params, `dispatch.params["fact_id"]` raises `KeyError`. This propagates to the bank, which catches it at `__init__.py:255` and records an error span. One bad dispatch doesn't kill siblings — the bank iterates and continues. The watcher then sees no discovery and emits a mismatch span. The failure surface is correct.

**LLM hallucinates a valid fact_id**: If the router coincidentally emits a `fact_id` that exists in the clue graph, the handler would discover a clue the player didn't actually investigate. But this is a router classification problem (confidence threshold = 0.6 per epic), not a handler problem. The handler correctly trusts the router's output — that's the architecture (ADR-113). A handler that second-guesses the router would break the single-source-of-truth principle.

**player_name doesn't match any character**: `consume_clue_footnotes` sets `active = None`, Seam A (discovery) fires but Seam B (KnownFact mint) is skipped. The clue appears discovered but no character "knows" it. The watcher won't flag this — it checks `fact_id in discovered_clues`, which IS true. However, this path is unreachable in production: the bank always supplies `player_name` from `intent_router_pass.py:132` which maps from `player_seats`. A mismatched name would require a bug in the session handler, not in this handler.

**Multiplayer race**: Two players submit investigation actions on the same turn, both dispatches carry the same `fact_id`. The bank runs sequentially (not concurrently). The first dispatch discovers the clue. The second dispatch calls `consume_clue_footnotes` which finds `is_new = False` and skips the KnownFact mint. Idempotency is sound — protected by `ScenarioState.discovered_clues` set membership.

**consume_clue_footnotes becomes async**: If refactored to async, the synchronous call at `scenario_clue.py:56` would return a coroutine object without executing. This is a hypothetical future concern. The function is currently synchronous with no I/O, and the test suite pins the current contract.

None of these scenarios uncover a real bug. The handler is minimal, correct, and follows established patterns exactly.

**Decision:** APPROVE — no Critical or High issues. Clean implementation following the sibling handler pattern with comprehensive test coverage (12 tests, 4 ACs).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test verification)
- **Improvement** (non-blocking): Test fixture builders (_clue_node, _character, _footnote) are copy-pasted across test_scenario_clue_dispatch.py and test_scenario_clue_intake.py. Consider extracting to shared conftest in a future chore. Affects `tests/agents/subsystems/` and `tests/server/` (fixture consolidation). *Found by TEA during test verification.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found. TEA and Dev entries verified accurate — implementation follows the epic 59 spec (§59-6 ACs 1-4) exactly. Handler delegates to existing `consume_clue_footnotes` seam, registered in dispatch bank, footnote path unchanged, idempotency via `ScenarioState.discover_clue`. Zero new abstractions introduced.