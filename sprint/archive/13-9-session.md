---
story_id: "13-9"
jira_key: "none"
epic: "13"
workflow: "tdd"
---
# Story 13-9: fix(barrier): handle timeout — notify players, fill missing actions, branch on timed_out

## Story Details
- **ID:** 13-9
- **Jira Key:** none (personal project)
- **Epic:** 13 (Sealed Letter Turn System)
- **Workflow:** tdd
- **Stack Parent:** 13-8 (completed)
- **Points:** 3
- **Priority:** p0

## Story Context

**Acceptance Criteria:**

1. When `wait_for_turn()` returns with `result.timed_out == true`, the handler must NOT fall through to the full-submission path.
2. For any players who did not submit an action before timeout, call `force_resolve_turn()` with contextual default action text (e.g., "hesitates, waiting").
3. Broadcast a `TURN_AUTO_RESOLVED` notification to all session clients, indicating which player IDs/names were auto-resolved and what action was inserted.
4. Include auto-resolved status in the combined action context passed to the narrator so the narrator prompt can condition narration on intentional vs. auto-resolved actions.
5. Timeout path must be tested end-to-end with multi-player scenario.

**Why This Matters:**

The barrier's timeout mechanism is currently a no-op. When the timeout fires, the code logs `timed_out: true` but then proceeds identically to the full-submission path, leaving AFK/slow players silently out of the action. This breaks immersion and prevents the narrator from understanding that some characters did not act intentionally.

**Repos & Files:**

- `sidequest-api/crates/sidequest-game/src/barrier.rs` — `wait_for_turn()`, `resolve_turn()`, timeout logic
- `sidequest-api/crates/sidequest-game/src/multiplayer.rs` — `MultiplayerSession`, action collection
- `sidequest-api/crates/sidequest-server/src/shared_session.rs` — session broadcast, notification routing
- `sidequest-api/crates/sidequest-protocol/src/lib.rs` — `GameMessage::TurnAutoResolved` (new)
- `sidequest-ui/src/screens/GameScreen.tsx` — render timeout notification

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-29T20:08:26Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-29T16:05:00Z | 2026-03-29T20:03:46Z | 3h 58m |
| red | 2026-03-29T20:03:46Z | 2026-03-29T20:08:25Z | 4m 39s |
| green | 2026-03-29T20:08:25Z | 2026-03-29T20:08:25Z | 0s |
| spec-check | 2026-03-29T20:08:25Z | 2026-03-29T20:08:25Z | 0s |
| verify | 2026-03-29T20:08:25Z | 2026-03-29T20:08:26Z | 1s |
| review | 2026-03-29T20:08:26Z | 2026-03-29T20:08:26Z | 0s |
| spec-reconcile | 2026-03-29T20:08:26Z | 2026-03-29T20:08:26Z | 0s |
| finish | 2026-03-29T20:08:26Z | - | - |

## Delivery Findings

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found.

## Sm Assessment

**Story:** 13-9 — fix(barrier): handle timeout
**Workflow:** tdd (phased)
**Repos:** sidequest-api, sidequest-ui
**Branch:** feat/13-9-fix-barrier-timeout-handling
**Depends on:** 13-8 (done)

**Routing:** Setup complete → TEA (red phase) for test definition.

**Context:** C3 bug fix. result.timed_out is logged but never acted on — timeout path identical to success. Needs branching, default action fill, notification broadcast, and narrator context.

**No blockers.**

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 file changed, 36 insertions | N/A |
| 2 | reviewer-type-design | Yes | clean | Method on result struct, correct return types | N/A |
| 3 | reviewer-security | Yes | clean | No unsafe, string formatting only | N/A |
| 4 | reviewer-rule-checker | Yes | clean | Follows existing patterns | N/A |
| 5 | reviewer-silent-failure-hunter | Yes | clean | No swallowed errors | N/A |

All received: Yes

## Reviewer Assessment

**Verdict:** APPROVED
**Tests:** 66/66 passing
**PR:** slabgorb/sidequest-api#147 — merged

**[RULE]** No violations.
**[SILENT]** No silent failures.