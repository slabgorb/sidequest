---
story_id: "30-3"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 30-3: GM panel StateTab crashes on undefined in_combat — PlayerCard reads uninitialized game state

## Story Details
- **ID:** 30-3
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p1
- **Type:** bug

## Problem

The GM panel's StateTab component crashes when rendering the PlayerCard because it references `player.combat_state.in_combat`, which no longer exists in the game state. 

Epic 28 replaced the old `CombatState` with `StructuredEncounter`. The `PlayerStateView` type in the watcher API does not include a `combat_state` field at all. The code at line 276 of StateTab.tsx tries to access this undefined field:

```typescript
{player.combat_state.in_combat && (
  <div style={{ fontSize: 11, color: THEME.red, fontWeight: "bold" }}>
    IN COMBAT — Round {player.combat_state.round}
  </div>
)}
```

## Fix

Remove the dead combat state reference from PlayerCard. Do NOT revert to add `in_combat` back — the old field is gone. The fix is deletion, not restoration.

If we need to show combat status in the GM panel later, that's a separate feature that requires wiring StructuredEncounter into the debug state endpoint. For now, just remove the crash.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-08T20:30:41Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-08T16:00Z | 2026-04-08T20:14:08Z | 4h 14m |
| red | 2026-04-08T20:14:08Z | 2026-04-08T20:19:13Z | 5m 5s |
| green | 2026-04-08T20:19:13Z | 2026-04-08T20:22:17Z | 3m 4s |
| spec-check | 2026-04-08T20:22:17Z | 2026-04-08T20:23:12Z | 55s |
| verify | 2026-04-08T20:23:12Z | 2026-04-08T20:25:43Z | 2m 31s |
| review | 2026-04-08T20:25:43Z | 2026-04-08T20:29:49Z | 4m 6s |
| spec-reconcile | 2026-04-08T20:29:49Z | 2026-04-08T20:30:41Z | 52s |
| finish | 2026-04-08T20:30:41Z | - | - |

## Sm Assessment

**Routing:** 2pt bug fix — PlayerCard references dead `combat_state.in_combat` field from pre-Epic 28. Fix is pure deletion of the dead reference. TDD workflow: TEA writes a test that the PlayerCard renders without crashing when no `combat_state` exists, then Dev removes the dead code.

**Direction from user:** Do NOT revert — don't add `in_combat` back. Forward-fix only.

## Delivery Findings

No upstream findings.

### TEA (verify)
- **Improvement** (non-blocking): Dashboard tabs duplicate Card component, thStyle, tdStyle, btnStyle, inputStyle across 6 files. Affects `src/components/Dashboard/tabs/*.tsx` (extract to shared/). *Found by TEA during test verification.*

## Impact Summary

**Upstream Effects:** 1 findings (0 Gap, 0 Conflict, 0 Question, 1 Improvement)
**Blocking:** None

- **Improvement:** Dashboard tabs duplicate Card component, thStyle, tdStyle, btnStyle, inputStyle across 6 files. Affects `src/components/Dashboard/tabs/*.tsx`.

### Downstream Effects

- **`src/components/Dashboard/tabs`** — 1 finding

## TEA Assessment

**Tests Required:** Yes
**Reason:** Bug fix — must prove crash exists before fixing

**Test Files:**
- `src/components/Dashboard/__tests__/StateTab.test.tsx` — 4 tests covering PlayerCard rendering

**Tests Written:** 4 tests covering 1 AC (PlayerCard renders without crashing)
**Status:** RED (failing — ready for Dev)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| No silent fallbacks | `renders without crashing when no combat_state` | failing |
| Wiring test | `renders multiple players without crashing` | failing |

**Rules checked:** 2 applicable rules have test coverage
**Self-check:** 0 vacuous tests found — all assertions use `toBeInTheDocument()` on specific content

**Fix direction:** Delete lines 275-280 of StateTab.tsx (the dead `combat_state` block). Do NOT add optional chaining — the field is gone from `PlayerStateView`, there's nothing to chain.

**Handoff:** To Inigo Montoya (Dev) for implementation

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | Pre-existing Card/style duplication across 6 dashboard tabs — not story-scoped |
| simplify-quality | 1 finding | Missing wiring test for StateTab in DashboardApp (medium confidence, pre-existing) |
| simplify-efficiency | clean | No issues |

**Applied:** 0 high-confidence fixes (all findings are pre-existing, out of story scope)
**Flagged for Review:** 1 medium-confidence finding (wiring test)
**Noted:** 4 low-priority pre-existing reuse opportunities
**Reverted:** 0

**Overall:** simplify: clean (no story-scoped issues)

**Quality Checks:** All passing (4/4 tests GREEN)
**Handoff:** To Westley (Reviewer) for code review

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/components/Dashboard/tabs/StateTab.tsx` — removed dead `combat_state` block (lines 275-280 deleted)
- `src/components/Dashboard/__tests__/StateTab.test.tsx` — fixed ambiguous `getByText` assertion for location (appears in multiple cards)

**Tests:** 4/4 passing (GREEN)
**Branch:** feat/30-3-gm-panel-statetab-crash-fix (pushed)

**Handoff:** To next phase (verify)

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Session spec: "Remove the dead combat state reference from PlayerCard. Do NOT revert to add `in_combat` back."
Implementation: Deleted lines 275-280 (the `combat_state` block). No new code added. Forward-fix only.

**Decision:** Proceed to verify

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (49 test failures + 101 lint errors all pre-existing on develop) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 5 | dismissed 5 — all pre-existing type gaps in watcher.ts (stringly-typed fields, Record<string,unknown>), not introduced by this diff |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 | dismissed 1 — missing wiring test is pre-existing debt (StateTab was already wired into DashboardApp before this story; this story only deleted dead code inside the component) |

**All received:** Yes (4 returned, 5 disabled)
**Total findings:** 0 confirmed, 6 dismissed (all pre-existing), 0 deferred

## Reviewer Assessment

**Verdict: APPROVE**

### Summary
Pure deletion fix — 7 lines of dead code removed from `PlayerCard` in `StateTab.tsx`. The `combat_state` field was removed from `PlayerStateView` when Epic 28 replaced `CombatState` with `StructuredEncounter`, but the JSX referencing it was left behind. Accessing `.in_combat` on `undefined` caused a `TypeError` crash in the GM panel.

### What Changed
- **StateTab.tsx**: Deleted lines 275-280 (the `{/* Combat */}` conditional block)
- **StateTab.test.tsx**: New test file with 4 tests verifying PlayerCard renders correctly without `combat_state`

### Correctness
- The deleted code referenced `player.combat_state.in_combat` — a field that does not exist on `PlayerStateView` (confirmed at `watcher.ts:57-68`)
- No optional chaining or fallback added — correct approach since the field is permanently gone
- Tests use the real `PlayerStateView` shape, confirming the fix matches the type contract

### Risk Assessment
- **Risk: Minimal** — pure deletion of dead code, no behavioral changes to working code paths
- **Regression potential: None** — removed code was always crashing, never rendering successfully

### Subagent Findings
- **[SILENT] No silent failures found** — clean. Deletion fully removes all `combat_state` accesses, no residual undefined property reads.
- **[TYPE] watcher.ts type gaps** (5 findings, dismissed): Pre-existing stringly-typed fields (`turn_mode`, `status`, `npcSort.col`) and `Record<string, unknown>` on `WatcherEvent.fields`. Real debt but not introduced by this story.
- **[RULE] Missing wiring test** (1 finding, dismissed): StateTab test suite has no integration test verifying DashboardApp renders it. Pre-existing — StateTab was already wired before this story.

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found.