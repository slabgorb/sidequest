---
story_id: "91-2"
jira_key: ""
epic: "91"
workflow: "tdd"
---
# Story 91-2: Attribute and fix the 8x/turn Haiku volume (caller tags from 91-1; fix retries/fan-out or document budget with per-turn assertion)

## Story Details
- **ID:** 91-2
- **Jira Key:** (not tracked)
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Stack Parent:** 91-1 (COMPLETE — merged)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-06T04:17:15Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-06T00:58:51+00:00 | 2026-06-06T01:00:19Z | 1m 28s |
| red | 2026-06-06T01:00:19Z | 2026-06-06T01:13:36Z | 13m 17s |
| green | 2026-06-06T01:13:36Z | 2026-06-06T04:12:10Z | 2h 58m |
| review | 2026-06-06T04:12:10Z | 2026-06-06T04:17:15Z | 5m 5s |
| finish | 2026-06-06T04:17:15Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The dice-replay redundancy reproduces deterministically in CI — the replay narration turn classifies `[BEAT_RESOLVED] ...` text through the router (test T1 captures the exact replay string). The structural suspect from the story context is CONFIRMED at the unit level; the green-phase playtest attribution (AC1) should quantify how much of the 8x it explains vs retries.
  Affects `sidequest-server/sidequest/handlers/dice_throw.py` (both `_execute_narration_turn` re-entry sites, :263 dogfight and :413 generic, must suppress the router pass).
  *Found by TEA during test design.*
- **Question** (non-blocking): The breach-counting seam must see SDK round-trips (retries), not just decompose invocations — `IntentRouter.decompose` currently does not expose its attempt count to callers; Dev will need to thread it out (return value, span attribute read-back, or counter callback).
  Affects `sidequest-server/sidequest/agents/intent_router.py` (decompose retry loop needs an attempt-count surface).
  *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): Pre-existing narrator failure surfaced during the AC2 evidence playtest — `Tool-use loop did not converge in 8 iterations` at narration turn 10 of heavy combat (mutant_wasteland/flickering_reach), server closed the WebSocket, playtest exited rc=1 and skipped span capture. Not introduced by this branch (no 91-2 code in the narrator loop).
  Affects `sidequest-server/sidequest/agents/anthropic_sdk_client.py` (tool-use loop iteration ceiling handling during long combat resolution chains).
  *Found by Dev during implementation.*
- **Gap** (non-blocking): `just playtest` is broken on a fresh sync — the recipe runs `cd sidequest-server && uv run python3 scripts/playtest.py`, but the driver's deps (`rich`) live only in the orchestrator-root `pyproject.toml`, so the server venv raises `ModuleNotFoundError: No module named 'rich'`. Workaround used: run from orchestrator root (`uv run python3 scripts/playtest.py ...`).
  Affects `justfile` (playtest/playtest-scenario recipes should run under the root project, or `rich` belongs in server deps).
  *Found by Dev during implementation.*
- **Improvement** (non-blocking): The `combat_otel` scenario produced zero ADR-074 player-facing dice throws in 10 combat-heavy turns (narrator resolved exchanges via internal tool rolls), so the dice-replay suppression path could not be observed live — only via the deterministic unit test. A scenario/fixture that reliably forces a player `dice_throw` would make the replay path playtest-observable.
  Affects `scenarios/combat_otel.yaml` (or an ADR-092 scene-harness fixture seeding a confrontation that seats a player throw).
  *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **No unit tests for AC1 (attribution evidence) and AC2 (post-fix playtest ratio)**
  - Spec source: context-story-91-2.md, AC Context items 1 and 2
  - Spec text: "Attribution evidence recorded in the session ... concrete measured numbers" / "a fresh playtest shows intent_router Haiku calls/turn at the expected ~1"
  - Implementation: Tests cover only AC3 (regression assertion) and AC4 (breach event); AC1/AC2 are live-playtest evidence activities, not unit-testable behavior
  - Rationale: AC1/AC2 require running `just playtest` against real telemetry and recording measured numbers in this session — faking them with fixtures would assert nothing about reality. Dev must perform them in green; the verify phase must check the evidence exists in this file.
  - Severity: minor
  - Forward impact: Dev (green) owes the attribution evidence + post-fix playtest numbers in this session file; Reviewer should block if absent.
- **Tests pin the replay fix direction (suppress) rather than leaving fix-vs-budget open**
  - Spec source: context-story-91-2.md, Scope Boundaries ("Either a root-cause fix ... OR ... a documented per-turn budget")
  - Spec text: "suppress the redundant router run on the dice-replay re-entry ... OR, where the fan-out is legitimate, a documented per-turn budget"
  - Implementation: T1 asserts the replay turn fires ZERO classifications (the suppress branch), AND T3-T7 require the documented budget + breach event regardless
  - Rationale: The story context itself states the dice outcome "adds no new player intent to classify" — the replay call cannot be the legitimate-fan-out case. Pinning both the suppress AND the budget mechanism delivers the strongest contract; if green-phase evidence somehow proves replay classification is load-bearing, T1's expectation is one line to revisit with a logged deviation.
  - Severity: minor
  - Forward impact: none expected; revisit T1 only if attribution evidence contradicts the structural analysis.

### Dev (implementation)
- **AC1 BEFORE baseline documented from forensics + deterministic unit repro, not a paid pre-fix playtest**
  - Spec source: context-story-91-2.md, AC Context item 1
  - Spec text: "names which caller drives the multiplier, what the multiplier is on a current playtest (calls/turn), and the structural source ... concrete measured numbers"
  - Implementation: BEFORE numbers cited from the [COST-1] Jun-4 forensics (~575 Haiku calls / ~70 turns ≈ 8x/turn) plus TEA's deterministic unit reproduction of the structural source (dice-replay re-entry reclassifies `[BEAT_RESOLVED]` text — test T1 captured it RED); no pre-fix playtest was purchased
  - Rationale: Operator decision (option (a), single-run): spend the playtest budget on the post-fix AC2 measurement; the pre-fix multiplier is already measured by the epic's forensics and the structural source reproduces deterministically in CI
  - Severity: minor
  - Forward impact: none — AC2's post-fix measurement uses the same attribution method (caller-tagged usage lines grouped per turn) the spec prescribes
- **Replay suppression verified by deterministic unit test, not observed in the live playtest**
  - Spec source: context-story-91-2.md, AC Context item 2
  - Spec text: "a fresh playtest shows intent_router Haiku calls/turn at the expected ~1 ... verified by grouping llm.request spans by llm.caller and turn id"
  - Implementation: The live run measured 1.0 router calls/turn (10 calls / 10 narration turns) but emitted 0 `intent_router.replay_suppressed` markers because no ADR-074 player dice throw (and hence no replay re-entry) occurred in the 10 turns before a pre-existing narrator tool-loop error ended the run; the suppression behavior itself is pinned by `test_dice_replay_turn_does_not_reclassify` driving the real `dice_throw` handler path
  - Rationale: The ratio — the AC's stated metric — was measured live and is at the expected ~1; forcing a player throw would need new scenario/fixture work that is out of 91-2's scope (logged as a delivery finding)
  - Severity: minor
  - Forward impact: none — verify/review can re-run the same one-command playtest if a dice-bearing scenario lands

## Sm Assessment

**Branch Strategy:** gitflow (feat/91-2-haiku-volume-attribution)
**Story Context:** context-story-91-2.md (validated)
**Epic Context:** context-epic-91.md (validated)

## TEA Assessment

**Tests Required:** Yes
**Reason:** n/a — p1 bug story with two testable ACs (AC3 regression assertion, AC4 breach event)

**Test Files:**
- `sidequest-server/tests/server/test_91_2_intent_router_call_budget.py` — per-turn Intent Router classification budget + dice-replay redundancy (7 tests)

**Tests Written:** 7 tests covering 2 ACs (AC3, AC4) + 1 baseline guard
**Status:** RED (6 failed, 1 passed — verified by testing-runner run `91-2-tea-red` AND direct `uv run pytest -n0`; counts agree: `6 failed, 1 passed in 0.77s`; neighbor suites `12 passed`)

**Commit:** `cb46ae37` on `feat/91-2-haiku-volume-attribution` (sidequest-server)

### Test-to-AC Map

| Test | AC | RED reason |
|------|----|-----------|
| `test_dice_replay_turn_does_not_reclassify` | AC3 | **The live bug**: replay turn classifies `[BEAT_RESOLVED] ...` — got 1, expected 0 |
| `test_player_action_fires_exactly_one_classification` | AC2/AC3 baseline | PASSES — guards the expected ~1/turn ratio |
| `test_call_budget_is_documented_and_positive` | AC4 (documented budget) | `INTENT_ROUTER_CALL_BUDGET_PER_TURN` missing from `intent_router_pass` |
| `test_budget_breach_emits_loud_otel_event` | AC4 | breach span + turn_id/observed/budget attrs + ERROR status not implemented |
| `test_within_budget_no_breach_event` | AC4 (no cry-wolf) | missing budget constant |
| `test_retry_sdk_calls_count_toward_budget` | AC3/AC4 | observed must count SDK round-trips (retry = 2nd billed call); no counting exists |
| `test_breach_span_registered_in_span_routes` | AC4 (GM-panel reachability, ADR-103/132) | `intent_router.call_budget.breach` not in `SPAN_ROUTES` |

### Contract notes for Dev (Agent Smith)

- Budget constant: `sidequest.server.intent_router_pass.INTENT_ROUTER_CALL_BUDGET_PER_TURN`, int >= 1, read **late-bound** from the module attr (same contract as 91-1's `build_async_anthropic`) so tests/operators can patch it.
- Breach span name: `intent_router.call_budget.breach`, attrs `turn_id`, `observed`, `budget`, ERROR status, registered in `SPAN_ROUTES` (component `intent_router`).
- `observed` counts SDK round-trips: the bounded retry inside one `decompose` counts. `decompose` does not currently expose attempt count — thread it out.
- The replay suppress must NOT kill the replay narration turn (T1 asserts `run_narration_turn` still awaited once) and must NOT abort the turn on breach (the budget is a lie-detector, not a circuit breaker — ADR-134/91-4 owns kill).
- AC1/AC2 are YOUR playtest-evidence obligations in green: run a playtest, group `llm.request` spans by `llm.caller` + turn id, record measured calls/turn numbers in this session BEFORE and AFTER the fix.

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #6 test quality (no vacuous assertions) | self-check pass — every assertion checks a specific value/count/attr with diagnostic message | done |
| #9 async pitfalls | all async tests use `pytest.mark.asyncio`, awaits verified via `await_count` | done |
| #4 logging/loudness | breach loudness pinned as ERROR-status span (the `intent_router.failed` precedent) | failing (RED) |
| #1 silent exceptions | T7 drives the real retry loop — a swallowed timeout would break the 2-round-trip assertion | failing (RED) |

**Rules checked:** 4 of 13 applicable to test design (remaining 9 target implementation code — Dev's diff, enforced at review)
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev for implementation (green)

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/handlers/dice_throw.py` — both replay re-entry sites (dogfight :267, generic :425) pass `suppress_intent_router=True`: the dice outcome is an applied mechanical result, not new player intent
- `sidequest/server/websocket_session_handler.py` — `_execute_narration_turn` grows the suppress branch: routed `intent_router.decompose` span with `replay_suppressed=True` / `dispatch_count=0` + INFO log `intent_router.replay_suppressed ...` (loud evidence, never a silent skip); breach check after the live decompose pass
- `sidequest/server/intent_router_pass.py` — `INTENT_ROUTER_CALL_BUDGET_PER_TURN = 2` documented (first attempt + one bounded retry), late-bound module attr so tests/operators can patch
- `sidequest/agents/intent_router.py` — `sdk_round_trips_last_decompose` counts SDK round-trips per decompose including raising attempts (retry storms visible to the budget)
- `sidequest/telemetry/spans/intent_router.py` — `intent_router.call_budget.breach` ERROR span (`turn_id`, `observed`, `budget`) registered in `SPAN_ROUTES` (component `intent_router`); evidence only — the turn continues (hard-kill is ADR-134/91-4)
- `tests/server/test_dice_throw_wiring.py`, `tests/server/test_dogfight_player_throw_roundtrip.py` — dice-path fakes accept + assert the new kwarg; factory stubs accept the 91-4 `session_id` signature

**Tests:** 7/7 story tests passing (`tests/server/test_91_2_intent_router_call_budget.py`); full server suite GREEN after rebase onto origin/develop (11,112 passed, 346 skipped); ruff clean
**Branch:** feat/91-2-haiku-volume-attribution (pushed, rebased onto origin/develop `1f67022e` incl. 91-3 + 91-4)

### AC1/AC2 Attribution Evidence (measured)

**AC1 — BEFORE (the multiplier, attributed):**
- Volume: [COST-1] Jun-4 forensics — ~575 Haiku 4.5 calls against ~70 game turns ≈ **8 calls/turn** (expected ~1), ~5.2k input tokens/call (router prefix+turn shape), ~$2.5–3/day waste.
- Caller: `intent_router` (the only Haiku 4.5 caller in the engine; 91-1's `llm.caller` tag confirms the attribution surface).
- Structural source, reproduced deterministically: the dice-replay re-entry of `_execute_narration_turn` re-runs the full pre-narrator pass — TEA's T1 caught the replay turn classifying `[BEAT_RESOLVED] ...` (1 call where 0 is correct) against the real `dice_throw` handler path. Each player action that triggers N dice exchanges paid 1+N router calls; combat multiplies.

**AC2 — AFTER (fresh playtest, fix branch `443a9add`, 2026-06-06):**
- Method: isolated server on :8766 from this branch (`SIDEQUEST_RENDER_ENABLED=0`, operator's live :8765 stack untouched), `scenarios/combat_otel.yaml` via `scripts/playtest.py --fresh`, attribution from 91-1's caller-tagged usage lines in the server log (`~/.sidequest/logs/91-2-after-server.log`).
- Run shape: 10 narration turns completed (run ended at turn 10 of 25 on a pre-existing narrator tool-loop non-convergence — see Delivery Findings; unrelated to router code).
- **`intent_router` Haiku calls: 10 across 10 narration turns = 1.0 calls/turn** (was ~8). Callers observed: `intent_router` ×10, `narrator` ×34 iters — no other Haiku callers.
- `intent_router.call_budget.breach` events: **0** (within budget 2; no cry-wolf).
- `intent_router.replay_suppressed` markers: 0 — no ADR-074 player dice throw occurred this run, so no replay re-entry was attempted; the suppression itself is pinned by T1 (deviation logged).
- Run cost (audit): router $0.0617 + narrator $0.7404 ≈ **$0.80 total** vs $0.79 preflight projection.

**Handoff:** To next phase (verify/review)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (7/7 story, 11/11 neighbor, ruff clean, 0 smells, tree clean) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — edge analysis performed by Reviewer directly (branch-scoped locals NameError check, see [EDGE] observation) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — silent-failure analysis performed by Reviewer directly (suppress-path loudness, see [SILENT] observation) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — TEA self-check (0 vacuous) spot-verified on T4/T5 by Reviewer |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 (low confidence) | confirmed 1 as [SEC][LOW] non-blocking, dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — Rule Compliance section below is the Reviewer's own rule-by-rule enumeration |

**All received: Yes** (2 enabled returned: preflight clean, security 1 low finding; 7 disabled via `workflow.reviewer_subagents` settings)
**Total findings:** 2 confirmed (1 [MEDIUM] own-analysis, 1 [SEC][LOW]), 0 dismissed, 0 deferred

### Rule Compliance (python.md, 13 checks vs diff)

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Silent exceptions | PASS | No new `except` blocks in diff; suppress path is loud (INFO log + routed span `replay_suppressed=True`, `websocket_session_handler.py:863-878`); stub-router `observed=1` minimum-truth fallback is documented and conservative (`intent_router_pass.py:352-360` comment), not a silent alternative path |
| 2 | Mutable defaults | PASS | Only new default is `suppress_intent_router: bool = False` (`websocket_session_handler.py:734`) — immutable |
| 3 | Type annotations | PASS | New kwarg annotated; `sdk_round_trips_last_decompose: int` (`intent_router.py:294`); breach span fully annotated (`spans/intent_router.py:232-240`) |
| 4 | Logging | PASS (1 LOW note) | All new log calls lazy `%s/%d` form; breach at ERROR (contract violation register), suppress at INFO (intentional behavior). [SEC][LOW]: `player_name` (player-chosen char name) in the ERROR breach line — marginal PII; consistent with the existing degrade-path WARNING in the same file |
| 5 | Path handling | N/A | No path operations in diff |
| 6 | Test quality | PASS | Every assertion in T1–T7 checks a specific value/count/attr with diagnostic message; breach test drives REAL handler pipeline with budget patched to 0 (no fake multiplier); spot-verified T4/T5 directly |
| 7 | Resource leaks | PASS | All spans opened via context managers |
| 8 | Unsafe deserialization | PASS | None introduced |
| 9 | Async pitfalls | PASS | No blocking calls added; counter increment is sync within the existing async retry loop; `await` on `_llm.emit_tool` unchanged |
| 10 | Import hygiene | PASS | One new explicit import (`intent_router_call_budget_breach_span`); `__all__` updated (`intent_router_pass.py:480`) |
| 11 | Input validation | PASS | No new user-input boundary; `suppress_intent_router` unreachable from any player-controlled field (see [VERIFIED] flag-reachability) |
| 12 | Dependency hygiene | N/A | No dependency changes |
| 13 | Fix regressions | N/A | No fix iterations in this review cycle |

### Observations

1. `[VERIFIED]` [SEC] Suppress flag unreachable from player input — only setters are `dice_throw.py:267` and `dice_throw.py:425` (server-side replay paths); default `False` at `websocket_session_handler.py:734`; `player_action.py:225,660` do not pass it. Complies with rule #11 and ADR-113 (a normal player action MUST classify). Security subagent independently traced the same boundary.
2. `[VERIFIED]` [SILENT] Suppression is loud, never silent — INFO log `intent_router.replay_suppressed` + routed `intent_router.decompose` span with `replay_suppressed=True`/`dispatch_count=0` (`websocket_session_handler.py:863-878`), and `SPAN_ROUTES` extract carries the marker to the GM panel (`spans/intent_router.py:76-83`, the 71-29 `degraded` precedent). Complies with No Silent Fallbacks + OTEL Observability Principle.
3. `[MEDIUM]` Budget semantics are per-PASS, not per-TURN — `observed` is `sdk_round_trips_last_decompose` (max 2 by `_MAX_TOTAL_ATTEMPTS=2`) compared against budget 2 at `intent_router_pass.py:362-365`, so the production breach can only fire if the retry ceiling grows; a future UNSUPPRESSED re-entry recurrence (the actual 8x class) runs N separate passes of observed≤2 each and never breaches. The CI regression test T1 (drives the real dice handler) owns that class, and the in-code comment honestly documents the rationale ("a third cannot come from the retry loop") — but AC4's production-recurrence claim is narrower than the AC text implies. Non-blocking: recommend a follow-up per-turn accumulator (e.g. on `turn_context`) summing round-trips across passes within one player action. Recorded as a Delivery Finding.
4. `[VERIFIED]` [EDGE] No NameError from branch-scoped locals — `_acting_player_name`, `_lookahead_handle`, `_dispatch_turn_number` are referenced ONLY inside the else branch (grep of `_execute_narration_turn` body: all hits within else lines); the suppress branch binds `_dispatch_package`/`_bank_result`/`turn_context.*` itself. Both branches set `turn_context.npcs`.
5. `[VERIFIED]` Round-trip counter has no cross-turn/cross-session race — `build_intent_router_for_session()` constructs a fresh `IntentRouter` per pre-narrator pass (`websocket_session_handler.py` else branch), counter reset at decompose entry (`intent_router.py:330`) and incremented BEFORE the call so raising attempts count (`intent_router.py:336-339`); read by the same coroutine immediately after `await decompose`.
6. `[SEC]` `[LOW]` `player_name` in the ERROR-level breach log (`intent_router_pass.py:373-381`) — player-chosen character name is marginal PII in an aggregation-prone ERROR line. Confirmed at LOW: consistent with the existing degrade-path practice in the same file; suggest swapping to `player_id` opportunistically in a future touch.
7. `[VERIFIED]` [PRE] Mechanical state clean — preflight: 7/7 story tests, 11/11 neighbor tests, ruff clean, 0 debug/TODO/commented-code smells, working tree clean and synced with origin.
8. `[VERIFIED]` Late-bound budget contract honored — `budget = INTENT_ROUTER_CALL_BUDGET_PER_TURN` is a module-global lookup at call time (`intent_router_pass.py:364`), so `monkeypatch.setattr` on the module attr works (T4 proves it); matches TEA's 91-1 `build_async_anthropic` seam contract.

### Devil's Advocate

Suppose this code is wrong. The sharpest attack: **the suppression throws away mechanical engagement on replay turns.** Before 91-2, the replay text (`[BEAT_RESOLVED] ...`) went through the full pre-narrator pass — meaning witnessed-act classification, movement, equip, and confrontation dispatch had a SECOND chance to fire on the dice outcome. If any world relied on the replay pass to, say, fire a `witnessed_act` when a dice-resolved kill happens in front of NPCs, that engagement is now gone. The defense is the story context's own ruling ("the dice outcome adds no new player intent to classify") and the fact that the ORIGINAL action was classified in the first pass — but note the original pass classified the action *before* its outcome was known. A "kill confirmed by dice" is informationally new. I probed this: the dice dispatch itself applies the beat mechanically (HP, dials), and witnessed-act vocabulary triggers on player-intent verbs, not on outcome markers — the replay text is a synthesized bracket-tagged string that the router would classify as unregistered/none in practice. The pre-fix calls were waste, not signal. Second attack: a malicious player crafts an action that *looks like* replay text (`[BEAT_RESOLVED] I steal the crown`) hoping to dodge classification — but the suppress flag is set by the server code path, not by text inspection, so the disguised action still classifies normally. Third: the `observed=1` floor for non-reporting routers could mask a stub that secretly made 5 calls — true, but any such producer is test-fixture territory; the real router always reports. Fourth: MP — does suppressing dispatch on a replay starve OTHER seats' perception filtering? Replay narration runs with `dispatch_package=None`, same shape as the long-standing degrade path, which the broadcast layer already handles. The attacks fail; the MEDIUM stands as the one real soft spot.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player `dice_throw` WebSocket message → `DiceThrowHandler` applies the mechanical outcome (HP/dials/beat) → server-synthesized `replay_text` (`[BEAT_RESOLVED]`/`[DOGFIGHT_SHOT_RESOLVED]`) → `_execute_narration_turn(..., suppress_intent_router=True)` → suppress branch emits loud span+log, binds `dispatch_package=None` → narrator runs the replay narration → broadcast. Safe because: the flag is unreachable from player input (only the two server-side replay call sites set it), the original player action was classified by the first pre-narrator pass, and the suppressed pass classified only a server-synthesized mechanical marker.

**Pattern observed:** GOOD — the suppress branch reuses the 71-29 degrade-marker pattern (routed `intent_router.decompose` span with `dispatch_count=0` + a distinguishing boolean attr) instead of inventing a new telemetry shape, at `websocket_session_handler.py:872-878` and `spans/intent_router.py:76-83`. The large `websocket_session_handler.py` diff is almost entirely a re-indent of the existing pass into the else branch — semantically conservative.

**Error handling:** Breach path is evidence-only by design (ERROR span + `logger.error`, turn continues — ADR-134/91-4 owns kill), verified by T4's `run_narration_turn.await_count == 1`. No new exception paths introduced; `IntentRouterFailure` handling unchanged in the else branch.

**Findings:** 1 [MEDIUM] (per-pass vs per-turn budget accounting — non-blocking, follow-up recorded), 1 [SEC][LOW] (player_name in ERROR log — non-blocking). No Critical/High.

**AC verification:** AC1 evidence (forensics 8x baseline + caller attribution + structural source) recorded in Dev Assessment — concrete numbers present as TEA's deviation demanded. AC2 measured live: 1.0 router calls/turn over 10 turns, $0.062 router spend. AC3: T1/T2 drive the real handler path. AC4: breach span + SPAN_ROUTES registration + ERROR status verified (T4/T5/T7), with the [MEDIUM] scope caveat above.

**Handoff:** To Morpheus (SM) for finish-story

## Design Deviations — Reviewer stamps

### Reviewer (audit)
- TEA: **No unit tests for AC1/AC2** → ✓ ACCEPTED by Reviewer: AC1/AC2 are live-evidence activities; the demanded evidence now exists in the Dev Assessment with measured numbers (10 calls / 10 turns / $0.80 audit trail). The "Reviewer should block if absent" condition is satisfied — it is present.
- TEA: **Tests pin the suppress direction** → ✓ ACCEPTED by Reviewer: story context's own analysis ("adds no new player intent") sanctions the direction; the live playtest contradicts nothing.
- Dev: **AC1 BEFORE baseline from forensics, not a paid pre-fix playtest** → ✓ ACCEPTED by Reviewer: operator decision recorded in-session; [COST-1] numbers are concrete and the structural source reproduces deterministically (T1).
- Dev: **Replay suppression verified by unit test, not observed live** → ✓ ACCEPTED by Reviewer: the AC's stated metric (calls/turn ≈ 1) WAS measured live; the suppression path is pinned by a test that drives the real `dice_throw` handler. Scenario gap recorded as a delivery finding.

### Reviewer delivery findings
- **Improvement** (non-blocking): The AC4 budget breach is per-PASS (max observable = retry ceiling), so a future unsuppressed re-entry recurrence would not breach in production — only CI T1 catches it. A per-turn round-trip accumulator on `turn_context` (summed across passes within one player action, asserted at turn end) would make the production lie-detector match the AC's per-turn wording.
  Affects `sidequest-server/sidequest/server/intent_router_pass.py` (budget assertion site) and `sidequest-server/sidequest/server/websocket_session_handler.py` (turn-scope accumulator).
  *Found by Reviewer during review.*