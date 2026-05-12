---
story_id: "49-5"
jira_key: null
epic: "49"
workflow: "trivial"
---
# Story 49-5: Delete or rewire dead module-level run_narration_turn (orchestrator.py:2587)

## Story Details
- **ID:** 49-5
- **Jira Key:** N/A (no Jira in SideQuest)
- **Workflow:** trivial
- **Epic:** Playtest 4 Closeout — Glenross / ADR-098 Continuity Recovery
- **Points:** 2
- **Stack Parent:** none

## Story Context

This is a refactor follow-up filed during review of story 49-1 (Recency-zone recent-narrative window). The story targets a dead or dormant function at `sidequest-server/sidequest/agents/orchestrator.py:2587` named `run_narration_turn`. 

**Work:** Investigate whether this module-level function has any live callers in the codebase. If it is truly dead (no callers), delete it. If it has callers but should not, either rewire the call sites or document the intended use.

Trivial workflow: discovery and cleanup, no test suite required. If the function is deleted, a simple verification that tests still pass is sufficient.

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-12T11:54:29Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-12T06:55:00Z | 2026-05-12T10:52:17Z | 3h 57m |
| implement | 2026-05-12T10:52:17Z | 2026-05-12T11:32:53Z | 40m 36s |
| review | 2026-05-12T11:32:53Z | 2026-05-12T11:41:04Z | 8m 11s |
| implement | 2026-05-12T11:41:04Z | 2026-05-12T11:48:00Z | 6m 56s |
| review | 2026-05-12T11:48:00Z | 2026-05-12T11:54:29Z | 6m 29s |
| finish | 2026-05-12T11:54:29Z | - | - |

## SM Assessment

**Scope:** Investigate `sidequest-server/sidequest/agents/orchestrator.py:2587` — module-level `run_narration_turn`. Determine whether it has any live callers (production code, not just tests, since per CLAUDE.md "every set of tests must include at least one integration test"). If dead, delete it. If callers exist, decide deletion vs. rewire based on whether they should still be there post-ADR-098 (stateless narrator turns).

**Context for the dev:**
- This was filed during 49-1 review as cleanup follow-up — it's specifically tagged "dead module-level" by the reviewer, meaning the suspicion is that this is leftover from the pre-ADR-098 narrator architecture or from the Rust→Python port (ADR-082).
- The corresponding live entry point is on the orchestrator class instance (not the module-level shim). Verify by reading orchestrator.py around 2587 for the function shape and grepping for non-test imports.
- Per memory, `delta-tier prompt unwired` (orchestrator.py:2497) keys on is_first_turn — adjacent code that should not be confused with this work.

**Repo + branch:** `sidequest-server` on `feat/49-5-delete-dead-run-narration-turn` (already created off origin/develop).

**Workflow:** trivial — SM → Dev → Reviewer → SM. No TEA phase. Verification is "tests still pass" via testing-runner subagent after the change.

**Risks / things to flag back:**
- If the function has callers that look intentional (e.g., a CLI entry point, a scenario harness), do NOT delete blindly — surface in Delivery Findings and ask before destruction.
- If the function has a test-only caller, the test is part of the dead code — delete both, but call it out in findings.
- This is sidequest-server only. Default base branch is `develop`, not `main`.

**Verdict:** ready for dev.

## Delivery Findings

No upstream findings at setup.

### Reviewer (code review)
- **Gap** (non-blocking): Three TurnContext fields sibling to `pending_resolution_signal` follow the same pattern dev flagged — `statuses_by_actor`, `pc_classes_by_name`, and `pc_positions` (declared in `sidequest-server/sidequest/agents/orchestrator.py:539, 547, 462` respectively) are consumed by `Orchestrator._run_narration_turn_synchronous` (e.g., orchestrator.py:1235, 1237, 1352-1353) and by `narrator.py:283, 310-321`, but the live `_build_turn_context` in `sidequest-server/sidequest/server/session_helpers.py:429-470` does not populate any of them. Only the deleted module-level wrapper did. Net effect: per-actor status rendering, class-distinct beat menus (Task 7 / C&C B/X), and chassis-position section (ship-tab positions) are silently dormant in production. Same fix as the dev's `pending_resolution_signal` finding: thread these four fields through `_build_turn_context` (or remove them from TurnContext if they're truly retired). Out of scope for 49-5 — file as a separate cleanup story. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The fix for the wiring gap (this PR's Delivery Findings, mine + Dev's) should be filed as a single follow-up story named something like "Thread snapshot fields through `_build_turn_context`," covering `pending_resolution_signal`, `statuses_by_actor`, `pc_classes_by_name`, `pc_positions`. Test scope: add a wiring test that calls `_build_turn_context` with a snapshot whose `pending_resolution_signal` is non-None and asserts `ctx.pending_resolution_signal is not None`. Affects `sidequest-server/sidequest/server/session_helpers.py:429-470` and `sidequest-server/sidequest/server/websocket_session_handler.py:2536` (signal-clearing call site). *Found by Reviewer during code review.*

### Dev (implementation)
- **Gap** (non-blocking): `snapshot.pending_resolution_signal` is set by three production sites (`server/narration_apply.py:2551`, `server/narration_apply.py:2833`, `server/dispatch/yield_action.py:183`) but never read by any live code path. The deleted module-level wrapper was the only consumer that copied it into `TurnContext.pending_resolution_signal`; the live `session_helpers._build_turn_context` (the production builder) does not. Affects `sidequest-server/sidequest/game/session.py:750` (the field) and `sidequest-server/sidequest/server/session_helpers.py:429` (the live TurnContext constructor — missing `pending_resolution_signal=` kwarg). Either thread the signal through `_build_turn_context` so the `[ENCOUNTER RESOLVED]` narrator zone fires on the next turn, or remove the snapshot field entirely. Out of scope for this trivial-workflow cleanup. *Found by Dev during implementation.*

## Design Deviations

No deviations at setup.

### Dev (implementation)
- No deviations from spec. → ✓ ACCEPTED by Reviewer: confirmed — diff is pure deletion, no spec interpretation required.

### Reviewer (audit)
- **Undocumented:** Dev's investigation surfaced four TurnContext fields (`pending_resolution_signal`, `statuses_by_actor`, `pc_classes_by_name`, `pc_positions`) populated only by the deleted wrapper, but logged only the first as a Delivery Finding. Severity: low — this is investigation completeness, not a deviation from implementation spec. Captured by Reviewer in Delivery Findings below.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/agents/orchestrator.py` — deleted module-level `run_narration_turn` wrapper + its two private helpers `_resolve_spell_slots_for_pc` and `_resolve_world_items` (193 lines).
- `sidequest-server/sidequest/agents/__init__.py` — removed `run_narration_turn` from imports, `__all__`, and the Phase 1 docstring listing.
- `sidequest-server/tests/agents/test_orchestrator.py` — deleted `test_run_narration_turn_clears_pending_resolution_signal_on_error` (62 lines) — exercised the wrapper's finally-clause signal-clearing.
- `sidequest-server/tests/server/test_npc_identity_drift.py` — deleted `test_run_narration_turn_passes_npc_registry_to_turn_context` and its Story 37-48 section header — wrapper-locked the wrapper's npc_pool forwarding. Production-path wiring is covered by `test_wiring_turn_n_registry_lands_in_turn_n_plus_1_prompt`.
- `sidequest-server/tests/server/test_party_peer_identity.py` — deleted `test_module_level_run_narration_turn_forwards_party_peers` — wrapper-locked party_peers forwarding. Production-path wiring is covered by `test_build_turn_context_populates_party_peers_in_multiplayer`, `test_build_turn_context_excludes_acting_player_from_peers`, `test_build_turn_context_solo_session_has_no_peers`, and `test_wiring_sd_to_prompt_delivers_peer_identity` in the same file.

**Investigation summary:**
- Grepped every Python file under `sidequest-server/sidequest/` (production) for `run_narration_turn` references at the module-level. The only production caller of `*.run_narration_turn(...)` is `server/websocket_session_handler.py:2536`, which calls the **instance method** on `sd.orchestrator` — not the module-level shim. No CLI entry point, scenario harness, or script imported the wrapper.
- The two helpers `_resolve_spell_slots_for_pc` and `_resolve_world_items` had zero references after wrapper removal.
- Live TurnContext construction happens in `server/session_helpers.py:_build_turn_context` (the WS handler calls this on every turn). The deleted wrapper was a second, redundant TurnContext builder used only by tests.

**Tests:** 5004/5004 passing (GREEN), 58 skipped, 0 failed.
**Branch:** `feat/49-5-delete-dead-run-narration-turn` (will push after commit).

**Handoff:** To review phase (Reviewer).

## Dev Assessment — Rework Round 1 (post-reviewer rejection)

**Implementation Complete:** Yes
**Scope of rework:** Stale comments on TurnContext field declarations, per Reviewer's REJECTED verdict.

**Files Changed:**
- `sidequest-server/sidequest/agents/orchestrator.py` — rewrote the docstring comments on `statuses_by_actor` (lines 533-543) and `pending_resolution_signal` (lines 548-568). Both comments previously claimed the field was "Populated by run_narration_turn" — referring to the now-deleted module-level wrapper. New comments name the live builder (`_build_turn_context` in session_helpers.py), explicitly state that the field is NOT currently populated in production, and point readers to the 49-5 Delivery Findings for the follow-up that should close the wiring gap.

**What I did not change (per minimalist discipline):**
- Lines 521 and 526 — Reviewer verified these are accurate post-deletion ("session handler populates before calling run_narration_turn" — the class method). No edit.
- Lines 915 and 989 — Reviewer flagged as medium-confidence ambiguity (deferred to follow-up). No edit.
- `pc_classes_by_name` comment (lines 540-545) — does not mention `run_narration_turn`. Has the same wiring-gap pattern (only the deleted wrapper populated it) but is not in the Reviewer's required-fix list. Captured by Reviewer's Delivery Finding as part of the follow-up scope; comment unchanged.

**Tests:** 5004/5004 passing (GREEN), 58 skipped, 0 failed.
**Branch:** `feat/49-5-delete-dead-run-narration-turn` (pushing this round's commit).

**Handoff:** Back to review phase (Reviewer).

## Subagent Results — Round 2 (post-rework)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells, 5004/0/58 GREEN, branch-touched files pass format check | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | not re-spawned | N/A | Round-1 result still valid — rework is comment-only, no test changes |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (1 low-confidence wording suggestion on `statuses_by_actor`, 1 medium-confidence missing-context note on `pending_resolution_signal` — "stale signal persistence" consequence unstated) | confirmed 0, dismissed 2 (both are stylistic polish below the bar for blocking; the required fixes from round-1 are present and accurate), deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | not re-spawned | N/A | Round-1 result still valid — rework is comment-only, no rule-bearing code changes |

**All received:** Yes (2 round-2 subagents returned; 7 either disabled or round-1-valid)
**Total findings:** 0 confirmed, 2 dismissed (with rationale), 0 deferred

## Reviewer Assessment — Round 2

**Verdict:** APPROVED

The dev rework (commit bdc7e3e, comment-only) addresses both round-1 blocking findings:
- `TurnContext.statuses_by_actor` (orchestrator.py:533-543) — rewrite names `_build_turn_context` as the live builder, explicitly states the field is NOT currently populated, points at 49-5 Delivery Findings for the follow-up. No reference to the deleted wrapper as a current populator. **Required fix delivered.**
- `TurnContext.pending_resolution_signal` (orchestrator.py:553-568) — rewrite removes the "Cleared on the snapshot in the module-level wrapper after the orchestrator returns" line, replaces with an honest account: snapshot field is still set by `narration_apply.py` / `dispatch/yield_action.py` but never threaded into the field, [ENCOUNTER RESOLVED] zone is dormant, follow-up must (a) thread through `_build_turn_context` and (b) clear at the call site. **Required fix delivered.**

Comment-analyzer round-2 raised two wordsmithing nits (low + medium confidence). Both are dismissed:
- The "NOT currently populated by `_build_turn_context`" phrasing is precise enough — the comment-analyzer's concern that a reader might think `_build_turn_context` "had a code path that was removed" is a stretch; the comment immediately follows with "the only code that ever populated this... was the module-level wrapper deleted in story 49-5," which forecloses that misreading.
- The "stale signal persistence" consequence (signal sits indefinitely on the snapshot post-resolution) is implied by the comment's framing but not spelled out. Below the bar for a second rejection — captured in the Delivery Findings and the follow-up story scope, where the consequence belongs.

**Data flow re-traced:** No code-flow changes since round-1. The deletion is still sound; the rework is documentation hygiene only.

**Subagent tag carry-forward from round-1 (still applicable):**
- [DOC] [RULE] — Stale-comment findings at orchestrator.py:534-538 and 549-554 — **now resolved** by commit bdc7e3e.
- [TEST] — Deleted `test_run_narration_turn_clears_pending_resolution_signal_on_error` was non-vacuous but exercised dead code; coverage of the live `_build_turn_context` path is unchanged. Captured as wiring-gap follow-up in Delivery Findings.
- [RULE] — CLAUDE.md "No Silent Fallbacks" / "Verify Wiring, Not Just Existence" violations are pre-existing (not caused by this PR); now made explicit in the rewritten comments and tracked in Delivery Findings. Compliant for this story's scope.

**Pattern observed:** Dev correctly applied minimalist discipline — touched only what the Queen required, left lines 521, 526, 540-545, 915, 989 untouched per round-1 verifications.

**Error handling:** N/A (comment-only).

### Rule Compliance — Round 2 Delta

- **CLAUDE.md No Silent Fallbacks:** the rewritten comments now make the wiring gap loud (the field is NOT populated, the zone is dormant, here's the follow-up). The PR no longer silently masks the gap behind misleading documentation. Compliant.
- **Python #6 (test quality):** no test changes in round-2. Round-1 result stands.
- **Python #10 (import hygiene):** no import changes in round-2. Round-1 result stands.

### Devil's Advocate — Round 2

Sebastien on a future mechanics pass opens orchestrator.py at the TurnContext dataclass. He reads the new comment on `pending_resolution_signal` and learns: (a) the field exists but is currently dormant in production, (b) why (the deleted wrapper was the only populator), (c) where the gap is on both sides (population AND clearing), (d) where to look for the follow-up (49-5 Delivery Findings). That's the documentation contract a 40-year tabletop veteran expects — honest about what works, honest about what doesn't, with a forwarding address.

What could still go wrong? A maintainer might miss that `pc_classes_by_name` has the same wiring gap because its comment wasn't rewritten. Mitigated: the Reviewer Delivery Finding lists all four fields and the follow-up story scope captures them together. Acceptable.

**Handoff:** To SM for finish-story.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (auto-fixed 3 unused imports + trailing whitespace as separate commit 1b6981b) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 1 high-confidence (signal-clear test was non-vacuous; deleted alongside its only implementation) | confirmed 1, dismissed 0, deferred 0 |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 (3 high-confidence stale, 2 medium-confidence ambiguity, 1 low/clean) | confirmed 4, dismissed 1 (low-confidence accurate-as-is), deferred 1 (medium-confidence wording polish — defer to follow-up) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 violations (rule #6 test-quality, CLAUDE.md No-Silent-Fallbacks) | confirmed 1 (stale-comment regression caused by this PR), dismissed 1 (wiring gap is pre-existing — out of scope per story SM assessment, dev correctly logged in Delivery Findings) |

**All received:** Yes
**Total findings:** 3 confirmed, 2 dismissed (with rationale), 1 deferred

## Reviewer Assessment

**Verdict:** REJECTED

The deletion itself is correctly scoped and verified — the module-level `run_narration_turn` wrapper had zero live callers, the deleted tests exercised only the wrapper (the replacement wiring tests for `npc_pool` and `party_peers` in the same files do cover the live `_build_turn_context` path), and the test suite is GREEN (5004/0/58). The lint cleanup auto-applied by preflight (commit 1b6981b) is appropriate.

However, this PR introduced a documentation regression: several comments on the surviving `TurnContext` dataclass still describe a wrapper that no longer exists. These comments are not nitpicks — they actively misdirect maintainers about where `pending_resolution_signal` is cleared (claiming "the module-level wrapper after the orchestrator returns" — a function this PR just deleted). The boy-scout fix is bounded and belongs in this PR, not a follow-up.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM] [DOC] [RULE] | Stale comment naming deleted wrapper as the cleanup site — "Cleared on the snapshot in the module-level wrapper after the orchestrator returns." Now factually false; the wrapper is gone. Comment-analyzer high-confidence. | `sidequest-server/sidequest/agents/orchestrator.py:552-554` | Rewrite to reflect the actual (post-deletion) state: `pending_resolution_signal` is no longer threaded through `_build_turn_context`, so the field is effectively dormant in production. Phrase the comment to make the gap explicit rather than implying a non-existent cleanup. |
| [MEDIUM] [DOC] | `TurnContext.statuses_by_actor` claims "Populated by run_narration_turn from session.characters" — only the deleted wrapper did this. `_build_turn_context` never has. Comment-analyzer high-confidence. | `sidequest-server/sidequest/agents/orchestrator.py:534-538` | Rewrite to: "Populated by `_build_turn_context` in `session_helpers.py` from `session.characters`." If `_build_turn_context` does not populate it (verify), say so and mark the field dormant. |
| [MEDIUM] [DOC] | `TurnContext.pending_resolution_signal` claims "Populated by run_narration_turn from session.pending_resolution_signal" — only the deleted wrapper did this. | `sidequest-server/sidequest/agents/orchestrator.py:549-550` | Same as above: rewrite to name the actual (post-deletion) populator, or mark the field dormant if no live code populates it. |
| [LOW] [DOC] | `TurnContext.dispatch_package` and `lethality_policy` comments say "session handler populates before calling run_narration_turn." Post-deletion this is *correct* — refers to the class method. **Keep, no change**. Listed here only to record the verification. | `sidequest-server/sidequest/agents/orchestrator.py:521, 526` | None. Verified accurate. |

**Data flow traced:** A snapshot's `pending_resolution_signal` field → set by `narration_apply.py` after encounter resolution → never threaded into TurnContext by the live `_build_turn_context` (session_helpers.py:429-470) → orchestrator reads `context.pending_resolution_signal` (orchestrator.py:1194, 1228, 1236, 1239, 1245), but the value is always `None` because the live builder never populates it. The deleted wrapper was the only code that bridged snapshot→context for this field. This gap is pre-existing — not caused by 49-5 — but the deletion makes it more obvious. Correctly flagged in Dev Delivery Findings; reviewer adds three sibling fields (statuses_by_actor, pc_classes_by_name, pc_positions) with the same pattern.

**Pattern observed:** `_build_turn_context` (session_helpers.py:429) is the live TurnContext builder; the deleted module-level `run_narration_turn` was a redundant second builder. Good cleanup. The remaining concern is that `TurnContext` field docstrings still attribute population to the deleted wrapper — those need to come into alignment with the live builder.

**Error handling:** N/A (pure deletion).

**Verified items challenged against subagent findings:**
- `[VERIFIED] Deletion has no live callers` — websocket_session_handler.py:2536 uses `sd.orchestrator.run_narration_turn` (instance method on the Orchestrator object), which survives. Rule-checker confirmed. No subagent contradicts.
- `[VERIFIED] Replacement tests cover the live path` — test-analyzer confirmed `test_wiring_turn_n_registry_lands_in_turn_n_plus_1_prompt` and `test_wiring_sd_to_prompt_delivers_peer_identity` independently exercise `_build_turn_context` with non-empty inputs.
- `[VERIFIED] No security/type/edge-case regressions introduced by deletion` — subagents that would have caught these (edge-hunter, silent-failure-hunter, type-design, security, simplifier) are disabled via settings; mechanical preflight (lint+tests) is clean. Acceptable given the deletion is pure (no new logic introduced) and the rule-checker exhaustively walked the 13-rule Python checklist.

### Rule Compliance

- **Python #6 (test quality):** `test_run_narration_turn_clears_pending_resolution_signal_on_error` was NOT vacuous; it was a real exception-safety contract. However, the contract it enforced was for the wrapper itself, not for production. The wrapper had zero production callers; deleting it removes a test of dead code. Compliant in spirit even though rule-checker flagged.
- **Python #10 (import hygiene):** `__init__.py` `__all__`, import block, and docstring header all consistent post-deletion. Compliant.
- **CLAUDE.md No Silent Fallbacks:** Wiring gap in `_build_turn_context` (for `pending_resolution_signal` and three sibling fields) is pre-existing. Dev correctly flagged in Delivery Findings. Not a violation of THIS PR — but should be tracked as a separate story.
- **CLAUDE.md No Stubbing:** Deletion is the cure, not a violation. Compliant.
- **CLAUDE.md Verify Wiring, Not Just Existence:** Replacement wiring tests for `npc_pool` and `party_peers` independently exist and cover the live `_build_turn_context` path. Compliant.
- **CLAUDE.md Every Test Suite Needs a Wiring Test:** Both modified test files retain wiring tests for the live production path. Compliant.
- **CLAUDE.md OTEL Observability Principle:** Pure dead-code deletion that doesn't alter live subsystem logic; exempt. Compliant.

### Devil's Advocate

Argue this code is broken. A maintainer in three months — let's say Sebastien on a mechanics tuning pass — opens orchestrator.py looking for where `pending_resolution_signal` is cleared from snapshot, because he's seen the encounter-resolution zone fire twice in a row during a playtest. He grep-finds `TurnContext.pending_resolution_signal`, reads the comment at line 552-554, and is told "Cleared on the snapshot in the module-level wrapper after the orchestrator returns." He greps for the wrapper. Nothing. He greps for any `pending_resolution_signal = None` assignment. Nothing in production code. He has now wasted twenty minutes following a comment that points at code that was deleted. The comment is a Chekhov's gun pointing at an empty corner.

What's worse: the comment is *near* the field declaration, which a competent reader would treat as the canonical documentation of the field's lifecycle. If the lifecycle documentation is wrong, the entire mental model of how resolution signals propagate is wrong. This is exactly the failure mode CLAUDE.md's "No Silent Fallbacks" rule exists to prevent — the system gives the appearance of a clean cleanup ("the wrapper handles it") that does not exist in code.

Three sibling fields (`statuses_by_actor`, `pc_classes_by_name`, `pc_positions`) carry the same "Populated by run_narration_turn" comment that the deleted wrapper made true. Post-deletion these three production-narrator features (per-actor status rendering, class-distinct beat menus, chassis-position section) silently never engage because the live `_build_turn_context` never populates the fields. A reviewer of a future PR touching the encounter zone would see those comments and assume the features are wired — and waste cycles debugging "why isn't the class-distinct beat menu showing up?"

What would a stressed filesystem do? N/A — pure deletion.

What would a confused user misunderstand? A maintainer would believe `pending_resolution_signal` is properly cleaned up.

What happens with unexpected config? N/A.

The Devil's Advocate finds: this PR has stale-comment regressions that mask a production gap. The dev correctly flagged the underlying wiring gap, but the comments themselves are a separate, this-PR-caused issue and need cleanup.

**Handoff:** Back to Dev for stale-comment cleanup (no logic changes; this is documentation hygiene). Workflow: `review → green → dev` rework path (green-state rework, not red — no failing tests).