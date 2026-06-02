---
story_id: "76-1"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 76-1: dispatch_worker entity_pending gate regression test — assert sd.embed_task spawns on an entity-only turn (seed pool member, no lore, call lore_embed.dispatch_worker). Guards the 75-6 silent-revert risk.

## Story Details
- **ID:** 76-1
- **Jira Key:** (none — Jira not configured for this project)
- **Workflow:** trivial
- **Stack Parent:** none
- **Epic:** 76 — Universal Retrieval Follow-Ups — 75-6 Hardening + Source Coverage

## Context
This is a regression test for the dispatch_worker entity_pending gate in the embedding system. The story guards against a silent revert in story 75-6 (ADR-118 entity card sync/reproject review). The test should verify that `sd.embed_task` spawns correctly when called on an entity-only turn with a seed pool member that has no lore, via `lore_embed.dispatch_worker`.

**Key Details:**
- Type: chore
- Points: 1
- Priority: p2
- Repos: sidequest-server
- Depends on: (none — independent 1-pointer)

## Sm Assessment

**Scope:** 1-point trivial test-only story. Add a regression test in `sidequest-server` that asserts `sd.embed_task` is spawned on an entity-only turn — a seed pool member with no lore — when `lore_embed.dispatch_worker` runs. The test guards the 75-6 hardening (ADR-118 §D2 entity card sync/reproject) against a silent revert: if the entity_pending gate ever stops dispatching the embed worker for entity-only turns, this test must fail.

**Approach for Dev:**
- This is a test-addition story. No production behavior should change — the test pins existing 75-6 behavior.
- Locate the `dispatch_worker` entity_pending path (likely `lore_embed`/embedding subsystem in `sidequest-server`) and the existing 75-6 tests; co-locate the new regression test there.
- Construct an entity-only turn fixture: a seed pool member entity present, no lore content. Assert `sd.embed_task` (the embed task spawn) fires via `dispatch_worker`.
- Per project doctrine: include a wiring assertion — verify the dispatch is reachable from the production code path, not just that a helper returns the right value.
- Run `just server-test` (pytest) to confirm green.

**Workflow:** trivial → next phase is `implement`, owned by Dev. No design/architecture phase needed for a single test.

**Jira:** not configured for this project — skipped intentionally.

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-02T10:50:07Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-02T10:27:30.925784Z | 2026-06-02T10:29:23Z | 1m 52s |
| implement | 2026-06-02T10:29:23Z | 2026-06-02T10:35:49Z | 6m 26s |
| review | 2026-06-02T10:35:49Z | 2026-06-02T10:45:12Z | 9m 23s |
| implement | 2026-06-02T10:45:12Z | 2026-06-02T10:47:34Z | 2m 22s |
| review | 2026-06-02T10:47:34Z | 2026-06-02T10:50:07Z | 2m 33s |
| finish | 2026-06-02T10:50:07Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings. The 75-6 dispatch gate (`entity_pending` arm) was already correct in production; this story only adds a missing regression guard. No production behavior changed.

### Reviewer (code review)
- **Improvement** (non-blocking): The gate is pinned on one side only (entity-only → task spawned). A complementary `test_dispatch_worker_skips_when_both_stores_empty` (both stores empty → `embed_task is None`) would make it a mutation-resistant pair and catch an always-fire regression. Affects `sidequest-server/tests/server/dispatch/test_lore_embed.py` (add one test). Out of strict scope for 76-1; the both-empty skip is already exercised indirectly by existing lore tests. Suggested follow-up for epic 76. *Found by Reviewer during code review.*
- **Gap** (non-blocking): The autouse daemon guard in `tests/server/conftest.py` patches `sidequest.game.lore_embedding.DaemonClient` and `...websocket_session_handler.DaemonClient` but not `sidequest.game.entity_embedding.DaemonClient`. Not exploitable by this test (see audit — the worker body never runs), but worth closing for any future test that *does* let `run_worker` execute against the entity store. Affects `sidequest-server/tests/server/conftest.py`. *Found by Reviewer during code review.*


## Impact Summary

**Story type:** Test/regression guard (trivial, test-only)
**Blocking issues:** 0
**Non-blocking findings:** 2 (both deferred to epic 76)

### Delivery Findings Analysis

The delivery phase identified 2 non-blocking findings, both recorded as epic-76 follow-ups and not required for 76-1 closure:

1. **Mutation resistance gap** (Improvement, non-blocking): The regression guard currently asserts entity-only dispatch fires (`embed_task spawned`) but does not pin the inverse side (both stores empty → no spawn). Adding `test_dispatch_worker_skips_when_both_stores_empty` would create a mutation-resistant pair and guard against an always-fire regression. Scope: `sidequest-server/tests/server/dispatch/test_lore_embed.py` (single test addition). **Status:** Deferred to epic 76; both-empty skip already covered indirectly by existing lore tests.

2. **Conftest daemon guard gap** (Gap, non-blocking): The autouse `DaemonClient` patch in `tests/server/conftest.py` covers `lore_embedding.DaemonClient` and `websocket_session_handler.DaemonClient` but not `entity_embedding.DaemonClient`. This test's design (cancel before first await) prevents execution of `run_worker`, so the gap is not exploitable here. However, closing it guards against future tests that may permit worker execution. Scope: `sidequest-server/tests/server/conftest.py` (patch addition). **Status:** Deferred to epic 76 as hygiene follow-up.

### Production Impact

**None.** This is a test-only story. The regression guard pins existing 75-6 behavior (dispatch_worker entity_pending gate) exactly as implemented; no production code was changed. All three round-1 reviewer fixes (docstring accuracy, precondition tightening, comment rationale) are test-internal refinements.

### Ready to Finish

✓ All tests passing (6/6 GREEN)
✓ Code review approved (round 2)
✓ No production behavior changed
✓ Both non-blocking findings logged as epic-76 follow-ups

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.
- Rework round-trip 1 (reviewer fixes): no new deviations — all three changes are test-internal refinements (docstring accuracy, precondition precision, comment completeness). No production code touched, primary mutation guard unchanged.

### Reviewer (audit)
- Dev's "No deviations from spec" — **ACCEPTED**. Diff is test-only (+62 lines, one file), no production behavior changed; the test pins existing 75-6 behavior exactly as the story scoped.
- Dev's rework round-trip 1 entry ("no new deviations — test-internal refinements only") — **ACCEPTED**. Verified the round-1→round-2 delta is confined to docstring/precondition/comment; no production code and no spec departure.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/tests/server/dispatch/test_lore_embed.py` — added `test_dispatch_worker_spawns_on_entity_only_turn` (+62 lines). Builds an entity-only turn (seed pool member `Borin` synced into `entity_store` via `entity_sync.sync_for_turn`, `lore_store` empty), calls `lore_embed.dispatch_worker`, asserts `sd.embed_task` is spawned as an `asyncio.Task`. Drains the fire-and-forget worker via cancel+suppress to avoid daemon coupling.

**Approach notes:**
- Test-only story — no production code changed (`git diff --stat` shows the one test file).
- Co-located in the existing `lore_embed` dispatch test module, mirroring the `NpcPoolMember` fixture pattern from the sibling `test_entity_sync_dispatch.py`.
- **Behavior-test, not source-text** (CLAUDE.md "No Source-Text Wiring Tests"): drives the real `dispatch_worker` through the real `entity_sync` and asserts on the spawned task, not on source strings.
- **Mutation-verified**: temporarily reverted the dispatch gate to lore-only (`if not pending:`) and confirmed the new test FAILS; restored the gate and confirmed GREEN. The guard genuinely bites on the 75-6 silent-revert it exists to catch (ADR-118 §D2).

**Tests:** 6/6 passing (GREEN) — `tests/server/dispatch/test_lore_embed.py`. Ruff lint + format clean.

**Branch:** `feat/76-1-dispatch-worker-entity-pending-gate-regression` (pushed)

### Dev Rework (round-trip 1 — reviewer fixes)

All three required reviewer findings addressed in commit `2314d718`:
1. **[DOC]** Docstring now names the actual gate locals (`pending` / `entity_pending`) and points to `lore_embed.dispatch_worker`; the nonexistent `lore_pending` is gone.
2. **[TEST/RULE #6]** Precondition tightened from bare truthy to `assert "npc:borin" in sd.entity_store.pending_embedding_ids(max_retries=3)` — a wrong/zero-card fixture can no longer masquerade as the entity-only state.
3. **[TEST/RULE #1]** `contextlib.suppress` comment now states *why* suppression is safe (we cancelled the task ourselves, after the load-bearing assertion already passed; the awaited drain only settles the loop).

Non-blocking findings (both-empty negative test; conftest `entity_embedding.DaemonClient` guard gap) left as logged epic-76 follow-ups per reviewer's non-blocking classification — out of scope for this 1-pointer.

**Tests:** 6/6 GREEN, ruff check + format clean. Primary mutation guard (`isinstance(sd.embed_task, asyncio.Task)`) untouched.

**Handoff:** Back to review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 6/6 GREEN, ruff check + format clean, 0 smells |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 2 (suppress comment, truthy precondition), dismissed 1 (daemon guard — empirically refuted), deferred 1 (both-empty negative test) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 2 (docstring var names, suppress comment), dismissed 1 (ADR-118 §D2 — established convention) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 1 (truthy precondition, rule 6), dismissed 1 (redundant asyncio marker — matches sibling tests) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 3 confirmed (minor), 4 dismissed (with rationale), 2 deferred/non-blocking

## Reviewer Assessment

**Verdict:** APPROVED (round 2 — all round-1 findings resolved)

**Round 2 re-review (current verdict).** Dev's rework (commit `2314d718`) is *exactly* the three fixes I requested — no scope creep, no new code, no production change. I independently re-verified:
- **Diff scope:** `git diff beb66979 2314d718` touches only the docstring, one precondition operator, and one comment block. Nothing else moved.
- **Finding 1 [DOC] — RESOLVED:** docstring now reads `if not pending` / `if not pending and not entity_pending` and names the `lore_embed.dispatch_worker` locals; the nonexistent `lore_pending` is gone.
- **Finding 2 [TEST][RULE #1] — RESOLVED:** the `contextlib.suppress` comment now states *why* suppression is safe (we cancelled it ourselves, after the load-bearing assertion already passed; the awaited drain only settles the loop). Satisfies `python.md` rule #1.
- **Finding 3 [TEST][RULE #6] — RESOLVED:** precondition is now `assert "npc:borin" in sd.entity_store.pending_embedding_ids(max_retries=3)` — pins the specific seeded card. `"npc:borin"` is the correct id (verified against `test_entity_sync_dispatch.py`). Satisfies `python.md` rule #6.
- **No fix-introduced regression (rule #13):** the membership check cannot false-pass; comment/docstring edits carry no behavior. Independent run: **6/6 GREEN**, `ruff check` + `ruff format --check` clean, working tree clean. The primary mutation guard (`isinstance(sd.embed_task, asyncio.Task)`) is untouched and still bites.

**Data flow traced:** seed `NpcPoolMember("Borin")` → `entity_sync.sync_for_turn` projects `npc:borin` into `entity_store` with `embedding_pending=True` → `lore_embed.dispatch_worker` reads `entity_store.pending_embedding_ids()` (non-empty) with `lore_store` empty → spawns `sd.embed_task`. Safe: the test asserts the spawn before cancelling, and the cancel-before-first-await guarantees `run_worker` never touches the daemon.
**Pattern observed:** fixture-driven behavior test mirroring `test_entity_sync_dispatch.py`'s `NpcPoolMember` setup — `tests/server/dispatch/test_lore_embed.py:140`.
**Error handling:** the lone swallow (`contextlib.suppress(asyncio.CancelledError)`, L196–203) is now rule-compliant with a stated safety rationale.

**Dispatch-tag coverage (round 2):** [EDGE] disabled — no new branches in the delta. [SILENT] the single `suppress` now carries its safety rationale (rule #1 satisfied). [TEST] all three test/precondition findings resolved. [DOC] docstring accuracy corrected. [TYPE] disabled — N/A for a test-only diff. [SEC] disabled — N/A, no input/secret/injection surface. [SIMPLE] no dead code or over-engineering; +70 lines, structure mirrors siblings. [RULE] both confirmed `python.md` violations (rules #1, #6) now corrected.

**Handoff:** To SM for finish-story.

---

### Round 1 (superseded — was REJECTED, changes requested)

**Round-1 verdict:** changes requested — minor polish; routed to Dev (green rework). All three findings below were resolved in round 2 (see above).

**Why not approved (round 1):** The test was *correct* and I independently mutation-verified it bites (reverted the gate to `if not pending:` → the new test FAILED; restored → GREEN). There were **no Critical/High severity, correctness, or security issues.** However, three confirmed minor findings remained, two matching stated `python.md` rules — and per reviewer doctrine I may downgrade severity but may **not** dismiss rule-matching findings. Two independent subagents flagged the `suppress` comment as a rule-1 violation (rule-checker disagreed); a 2-of-3 majority on a rule-flagged line is not something I will wave through on a test whose entire job is rigor.

**Required fixes (Dev — green rework):**

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MINOR] [DOC] | Docstring describes the gate as `if not lore_pending` → `if not lore_pending and not entity_pending`, but the production variable is named `pending` (not `lore_pending`); `lore_pending` exists nowhere in the codebase. | `tests/server/dispatch/test_lore_embed.py` docstring (~L141, L148) | Replace `lore_pending` → `pending` in both docstring occurrences to match `lore_embed.py:184`. |
| [MINOR] [TEST] [RULE] | `contextlib.suppress(asyncio.CancelledError)` comment explains the *purpose* (deterministic drain) but not *why suppression is safe* — `python.md` rule #1 requires the safety rationale at the call site. (rule-checker judged it borderline-compliant; test-analyzer + comment-analyzer flagged it.) | `tests/server/dispatch/test_lore_embed.py` (~L194–198) | Add a clause: CancelledError is the expected outcome because we cancelled the task ourselves *after* the load-bearing assertion already passed, so the task's result is irrelevant. |
| [MINOR] [TEST] [RULE] | Bare truthy precondition `assert sd.entity_store.pending_embedding_ids(max_retries=3)` — `python.md` rule #6 (truthy assert misses wrong values). | `tests/server/dispatch/test_lore_embed.py` (~L176) | Tighten to membership: `assert "npc:borin" in sd.entity_store.pending_embedding_ids(max_retries=3)` — confirms the seeded card specifically is pending, not merely *some* list. |

**Confirmed-but-deferred / non-blocking (do NOT require for 76-1):**
- [TEST] Add a both-stores-empty → `embed_task is None` negative test to pin the other side of the gate (test-analyzer finding C). Recorded as a non-blocking delivery finding / epic-76 follow-up.

**Dismissed with rationale (dispatch tags):**
- [TEST] Daemon-guard gap on `entity_embedding.DaemonClient` (test-analyzer): **dismissed — empirically refuted.** I ran a probe: with no `await` between `create_task` and `cancel()`, the task is cancelled before its first suspension point and `run_worker`'s body never executes (`ran_body=False`, `cancelled=True`). The daemon client is never constructed; isolation does not depend on event-loop timing. Logged as a non-blocking conftest hygiene finding for future tests that *do* run the worker.
- [DOC] "ADR-118 §D2 is deferred, so citing it is misleading" (comment-analyzer): **dismissed — established convention.** `§D2` is cited identically across production (`entity_sync.py:1`, `entity_store.py:54`, `websocket_session_handler.py:1264`) and sibling tests (`test_entity_sync_dispatch.py:179`, `test_entity_sync.py`). The 75-x epics *are* the ADR-118 implementation; the citation is consistent and grounded.
- [RULE] Redundant `@pytest.mark.asyncio` under `asyncio_mode="auto"` (rule-checker): **dismissed — consistency wins.** All four existing async tests in this same file carry the marker; removing it from only the new test would create the real inconsistency. rule-checker itself noted this is a file-wide pre-existing pattern, not introduced by this diff.

**Dispatch-tag coverage:** [EDGE] disabled — manually considered: test adds no production branches, no new paths to enumerate. [SILENT] disabled — manually considered: the one `suppress` is the only swallow and is addressed above (rule fix). [TEST] covered (3 findings). [DOC] covered (2 findings). [TYPE] disabled — N/A, no type/signature surface in a test-only diff. [SEC] disabled — N/A, no input boundary/secret/injection surface in a test. [SIMPLE] disabled — manually considered: 62 lines, no dead code or over-engineering; structure mirrors sibling tests. [RULE] covered (rule-checker, 14 rules / 22 instances, 2 confirmed violations folded into required fixes above).

**Handoff:** Back to Dev for fixes.

**Handoff:** To review phase (Reviewer).