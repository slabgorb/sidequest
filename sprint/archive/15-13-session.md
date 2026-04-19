---
story_id: "15-13"
jira_key: "none"
epic: "epic-15"
workflow: "tdd"
---
# Story 15-13: Wire AchievementTracker — check_transition never called, achievements never fire

## Story Details
- **ID:** 15-13
- **Title:** Wire AchievementTracker — check_transition never called, achievements never fire
- **Points:** 3
- **Workflow:** tdd
- **Stack Parent:** none
- **Priority:** p1

## Summary
GameSnapshot holds an achievement_tracker field. AchievementTracker::check_transition() evaluates trope status transitions against achievement definitions and returns newly earned achievements. It's never called from dispatch_player_action().

**Fix:** In the trope tick loop, after calling trope.tick(), if the status changed, call achievement_tracker.check_transition(&trope, old_status). Broadcast any earned achievements as GameMessage events to all session players. Add OTEL event: achievement.earned (achievement_id, trope_id, trigger_type).

## Workflow Tracking
**Workflow:** tdd
**Phase:** green
**Phase Started:** 2026-04-01T10:13:39Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-01T09:30:13Z | 2026-04-01T09:30:57Z | 44s |
| red | 2026-04-01T09:30:57Z | 2026-04-01T09:40:22Z | 9m 25s |
| green | 2026-04-01T09:40:22Z | 2026-04-01T09:46:38Z | 6m 16s |
| spec-check | 2026-04-01T09:46:38Z | 2026-04-01T09:48:41Z | 2m 3s |
| green | 2026-04-01T09:48:41Z | 2026-04-01T10:00:13Z | 11m 32s |
| spec-check | 2026-04-01T10:00:13Z | 2026-04-01T10:01:23Z | 1m 10s |
| verify | 2026-04-01T10:01:23Z | 2026-04-01T10:03:21Z | 1m 58s |
| green | 2026-04-01T10:03:21Z | 2026-04-01T10:06:39Z | 3m 18s |
| spec-check | 2026-04-01T10:06:39Z | 2026-04-01T10:07:39Z | 1m |
| verify | 2026-04-01T10:07:39Z | 2026-04-01T10:10:47Z | 3m 8s |
| review | 2026-04-01T10:10:47Z | 2026-04-01T10:13:39Z | 2m 52s |
| green | 2026-04-01T10:13:39Z | - | - |

## Delivery Findings

No upstream findings.

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

## Design Deviations

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- **New methods on TropeEngine instead of modifying existing tick()**
  - Spec source: session summary, AC-1
  - Spec text: "In the trope tick loop, after calling trope.tick(), if the status changed, call achievement_tracker.check_transition"
  - Implementation: Tests expect new composite methods (tick_and_check_achievements, resolve_and_check_achievements) rather than modifying existing tick() signature
  - Rationale: Adding &mut AchievementTracker to tick()'s signature would break all existing callers (tests and production code). Composite methods preserve backward compatibility while adding the wiring.
  - Severity: minor
  - Forward impact: Dev may choose a different integration pattern (e.g., calling check_transition after tick at the call site instead of composite methods). Tests document the expected behavior, not the exact API shape.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core wiring story — achievements never fire because check_transition is never called

**Test Files:**
- `crates/sidequest-game/tests/achievement_wiring_story_15_13_tests.rs` — 8 tests covering tick+achievement integration

**Tests Written:** 8 tests covering 3 ACs
**Status:** RED (compile failure — 17 errors on 3 missing TropeEngine methods)

### Test Coverage

| Test | AC | What it proves |
|------|-----|---------------|
| `tick_and_check_achievements_fires_on_active_to_progressing` | AC-1 | Active→Progressing transition earns achievement |
| `tick_and_check_achievements_multiple_tropes` | AC-1 | Multiple tropes independently check achievements |
| `tick_and_check_achievements_no_transition_no_achievement` | AC-1 | No status change = no achievement |
| `tick_and_check_achievements_skips_resolved_and_dormant` | AC-1 | Resolved/Dormant tropes excluded |
| `tick_and_check_achievements_dedup_across_ticks` | AC-1 | Dedup guard works through integrated path |
| `tick_and_check_achievements_with_multiplier` | AC-1 | Engagement multiplier path also checks achievements |
| `resolve_and_check_achievements_fires_resolved` | AC-1 | Resolve path fires resolved achievement |
| `resolve_and_check_achievements_fires_subverted` | AC-1 | Subversion fires both resolved + subverted |

### Rule Coverage

| Rule | Applicable? | Notes |
|------|-------------|-------|
| #1 silent errors | No | No error paths in this change |
| #2 non_exhaustive | No | No new public enums |
| #4 tracing | Yes | Deferred to Dev — OTEL spans for achievement.earned (AC-3) |
| #6 test quality | Yes | All tests have meaningful assert_eq!/assert! on specific values |

**Rules checked:** 4 of 15 applicable; remainder not applicable to this additive wiring change
**Self-check:** 0 vacuous tests found

**Handoff:** To Major Winchester (Dev) for implementation

## TEA Assessment (verify)

**Phase:** green
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | Duplicated tracing::info! (high), WatcherEvent boilerplate (high, pre-existing), achievement logging duplication (medium) |
| simplify-quality | 3 findings | _earned_achievements underscore (high, correct as-is), clone convention (medium), trigger vs trigger_status naming (medium) |
| simplify-efficiency | 2 findings | def_map duplication (high, pre-existing), WatcherEvent verbosity (medium, pre-existing) |

**Applied:** 1 high-confidence fix — extracted `log_earned_achievements()` helper in trope.rs to deduplicate tracing::info! across tick and resolve paths
**Flagged for Review:** 1 — `trigger` vs `trigger_status` naming inconsistency in AchievementEarnedPayload (medium, cosmetic)
**Noted:** 3 pre-existing patterns (WatcherEvent boilerplate, def_map construction) not introduced by this story
**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** All passing (9/9 tests, server compiles clean)
**Handoff:** To Colonel Potter (Reviewer) for code review

## Architect Assessment (spec-check)

### Round 1 (returned to Dev)
Detected `process_tropes()` still calling unwired `TropeEngine::tick()`. Returned to Dev for fix.

### Round 2
**Spec Alignment:** Aligned (with one known deferral)
**Mismatches Found:** 1 (deferred, non-blocking)

- **No GameMessage::AchievementEarned variant for player broadcast** (Missing in code — Behavioral, Minor)
  - Spec: "Broadcast any earned achievements as GameMessage events to all session players"
  - Code: WatcherEvents emitted for GM panel. No WebSocket message to players. Requires new protocol variant + UI handling.
  - Recommendation: **D — Defer** — Adding a protocol variant crosses into sidequest-protocol (which is marked "Zero TODO/FIXME — this crate is done") and requires UI changes. Dev logged as delivery finding. Recommend follow-up story.

**Resolved from round 1:**
- `process_tropes()` now calls `tick_and_check_achievements()` via `ctx.achievement_tracker` ✓
- `achievement_tracker` threaded through full dispatch chain (DispatchContext, dispatch_message, dispatch_connect, dispatch_character_creation) ✓
- Tracker persisted in snapshot save and restored on reconnect ✓
- WatcherEvent emission for GM panel visibility ✓

**Decision:** Proceed to verify

### Round 3
**Spec Alignment:** Aligned
**Mismatches Found:** None

All three ACs now have production code:
- AC-1: `tick_and_check_achievements()` called from `process_tropes()` ✓
- AC-2: `GameMessage::AchievementEarned` broadcast to all session players ✓
- AC-3: `tracing::info!` + `WatcherEvent` emission with achievement_id, trope_id, trigger_type ✓

Round 2 deferral of AC-2 was incorrect — corrected by Dev in this round.

**Decision:** Proceed to verify

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/trope.rs` — Added 3 methods to TropeEngine: `tick_and_check_achievements`, `tick_and_check_achievements_with_multiplier`, `resolve_and_check_achievements`. Each snapshots old status, delegates to existing tick/resolve, then calls `AchievementTracker::check_transition` for any status change. OTEL `tracing::info!` events emitted per earned achievement.
- `crates/sidequest-server/src/dispatch/mod.rs` — Added `achievement_tracker` field to `DispatchContext`. Persist tracker in snapshot save path.
- `crates/sidequest-server/src/dispatch/tropes.rs` — Replaced `TropeEngine::tick()` with `tick_and_check_achievements()`. Added WatcherEvent emission for earned achievements (GM panel visibility). Broadcast `GameMessage::AchievementEarned` to all session players. Return type now includes earned achievements.
- `crates/sidequest-server/src/lib.rs` — Thread `achievement_tracker` through `dispatch_message`, `dispatch_connect`, `dispatch_character_creation`. Declare, initialize, restore from snapshot, and pass through all dispatch paths.
- `crates/sidequest-protocol/src/message.rs` — Added `GameMessage::AchievementEarned` variant with `AchievementEarnedPayload` (achievement_id, name, description, trope_id, trigger, emoji). Broadcast to all session players on earned.

**Tests:** 9/9 passing (GREEN)
**Branch:** feat/15-13-wire-achievement-tracker (pushed)
**Pre-existing failures:** `validates_against_location_context` (14-7), E2E WebSocket tests (2-9) — both unrelated

**Handoff:** To next phase

## Reviewer Assessment

**Decision:** REJECT — hand back to Dev for 3 required fixes

### Required Fixes (blocking)

1. **`player_id: String::new()` → `"server".to_string()`** in `dispatch/tropes.rs:152`
   Every other server-originated message uses `"server"`. Empty string violates convention.

2. **`activate_and_check_achievements()` missing** — `TropeEngine::activate()` has no achievement-checking wrapper. `TropeState::new()` starts at `Active`, so the only way to fire `trigger_status: "activated"` achievements is via a `Dormant → Active` transition in `activate()`. Without a wrapper, achievements with `trigger_status = "activated"` are silently unearnable. Wire it in `dispatch/tropes.rs` where `TropeEngine::activate()` is called.

3. **`advance_between_sessions` not wired** — `lib.rs` calls `advance_between_sessions()` on reconnect AFTER restoring `achievement_tracker`, but uses the bare method that doesn't call `check_transition`. Tropes that cross status boundaries during offline gap earn nothing. Add `advance_between_sessions_and_check_achievements()` or snapshot+check after the call.

### Flagged (non-blocking, Reviewer discretion)

- `trigger_status: String` should be an `AchievementTrigger` enum — typos in genre pack YAML create silently dead achievements. Valid but scope-expanding; flag for follow-up.
- `_earned_achievements` in dispatch/mod.rs — rename to `earned_achievements` and record in `system_tick_span` for OTEL completeness.

## Sm Assessment

**Story is clear and unblocked.** AchievementTracker exists but check_transition() is never called — pure wiring story. The fix touches the trope tick loop in sidequest-game, broadcasts earned achievements as GameMessage events, and adds OTEL spans. TDD workflow is appropriate: write tests that assert check_transition is called on status change and that achievements are broadcast, then wire it up.

- **Repos:** api (sidequest-game crate, likely sidequest-server for broadcast)
- **Risk:** Low — additive wiring, no breaking changes
- **Routing:** TEA (Radar) for RED phase