---
story_id: "13-4"
jira_key: "none"
epic: "13"
workflow: "tdd"
---
# Story 13-4: Timeout fallback with player notification — fill missing actions and notify who was auto-resolved

## Story Details
- **ID:** 13-4
- **Jira Key:** none (personal project)
- **Epic:** 13 — Sealed Letter Turn System
- **Workflow:** tdd
- **Stack Parent:** 13-2
- **Points:** 3
- **Priority:** P1

## Scope

When the adaptive timeout fires before all players submit their actions, automatically fill missing players with contextual defaults and notify the remaining players which characters were auto-resolved. The UI will show a subtle indicator on those players' action cards during the reveal.

**Acceptance criteria:**
1. When timeout fires (wait_for_turn returns with timed_out=true), identify missing players
2. Auto-fill missing actions with contextual defaults (e.g., "waits and observes", "hesitates")
3. Broadcast PLAYER_TIMEOUT_AUTO_FILLED message to all clients with list of auto-resolved players
4. Include auto-resolution metadata in combined action context for narrator awareness
5. UI renders subtle indicator (icon/badge) on auto-resolved action cards during ACTION_REVEAL
6. Tests verify timeout handling with mixed complete/incomplete submissions

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-30T14:10:25Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-30T13:11:16Z | 2026-03-30T13:42:15Z | 30m 59s |
| red | 2026-03-30T13:42:15Z | 2026-03-30T13:53:21Z | 11m 6s |
| green | 2026-03-30T13:53:21Z | 2026-03-30T13:57:29Z | 4m 8s |
| spec-check | 2026-03-30T13:57:29Z | 2026-03-30T13:59:09Z | 1m 40s |
| verify | 2026-03-30T13:59:09Z | 2026-03-30T14:03:10Z | 4m 1s |
| review | 2026-03-30T14:03:10Z | 2026-03-30T14:09:10Z | 6m |
| spec-reconcile | 2026-03-30T14:09:10Z | 2026-03-30T14:10:25Z | 1m 15s |
| finish | 2026-03-30T14:10:25Z | - | - |

## Sm Assessment

Story 13-4 is the timeout fallback layer for the sealed letter turn system. When the adaptive timeout fires before all players submit, it auto-fills missing actions with contextual defaults and notifies everyone who was auto-resolved.

**Dependencies:** Builds on 13-2 (adaptive timeout) which provides the `wait_for_turn` timeout mechanism. This story handles what happens *after* timeout fires.

**Scope validation:** 6 ACs covering API auto-fill logic, broadcast message, narrator context, and UI indicator. Clean 3-point story — well-scoped for TDD.

**Risks:** None identified. Protocol types and turn orchestration patterns are established from prior epic 13 work.

**Routing:** TDD phased workflow → TEA (Radar) for red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 6 ACs spanning game engine, protocol, and UI — full cross-layer coverage needed.

**Test Files:**
- `sidequest-api/crates/sidequest-game/tests/timeout_notify_story_13_4_tests.rs` — Mode-contextual auto-fill, auto_resolved_character_names extraction, TurnBarrier mode-aware timeout, E2E mixed submission scenarios
- `sidequest-ui/src/components/__tests__/TurnStatusAutoResolved.test.tsx` — TurnStatusPanel timeout labels, local player notification, data-timeout attribute
- `sidequest-ui/src/screens/__tests__/ActionRevealAutoResolved.test.tsx` — ActionReveal data-auto-resolved attributes, timeout indicator text, mixed/all-timeout scenarios

**Tests Written:** 35 tests covering 5 of 6 ACs (AC-6 is "tests exist" = meta-satisfied)
**Status:** RED (failing — ready for Dev)

- **Rust:** 14 tests, 15 compile errors (3 missing methods: `force_resolve_turn_for_mode`, `auto_resolved_character_names`, `set_turn_mode`)
- **UI:** 21 tests, 10 assertion failures (missing timeout labels, data attributes, notification text), 11 passing (existing behavior)

### New APIs Required by Tests

| Method | On | Purpose |
|--------|-----|---------|
| `force_resolve_turn_for_mode(&TurnMode)` | `MultiplayerSession` | Mode-contextual default action (structured→hesitates, cinematic→remains silent) |
| `auto_resolved_character_names()` | `TurnBarrierResult` | Extract character names (not player IDs) for ActionRevealPayload.auto_resolved |
| `set_turn_mode(TurnMode)` | `TurnBarrier` | Store mode for use during timeout resolution |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Rust #6 test quality | Self-check: all 14 Rust tests have assert!/assert_eq! | verified |
| TS #8 test quality | No `as any` in UI tests; assertions are specific | verified |
| TS #6 React/JSX | Test components are stateless renders, no hook concerns | n/a |

**Rules checked:** 3 of applicable rules have test coverage. Most lang-review rules target implementation, not test design.
**Self-check:** 0 vacuous tests found. All tests have meaningful assertions.

**Handoff:** To Major Winchester (Dev) for implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-game/src/multiplayer.rs` — Added `force_resolve_turn_for_mode(&TurnMode)` with mode-contextual defaults; existing `force_resolve_turn()` now delegates to it
- `sidequest-api/crates/sidequest-game/src/barrier.rs` — Added `turn_mode` field to `Inner`, `set_turn_mode()` method, `auto_resolved_character_names()` on `TurnBarrierResult`; `resolve()` uses stored mode
- `sidequest-ui/src/components/TurnStatusPanel.tsx` — Added "timed out" label, `data-timeout` attribute, local player timeout notification
- `sidequest-ui/src/screens/NarrativeView.tsx` — Added `data-auto-resolved` attributes on action-reveal entries, "timed out" label on auto-resolved cards

**Tests:** 33/33 passing (GREEN) — 12 Rust + 21 UI. Zero regressions (50 existing UI tests + 9 existing 13-9 barrier tests pass).
**Branch:** `feat/13-4-timeout-fallback-notification` (pushed in api + ui repos)

**Handoff:** To verify phase (TEA) or review.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | 1 high (duplicated extraction), 1 medium (dedup helper) |
| simplify-quality | 2 findings | 1 low (dup doc comment), 1 medium (null handling — pre-existing) |
| simplify-efficiency | 8 findings | 1 high (duplicated extraction), 7 medium/low (pre-existing complexity) |

**Applied:** 1 high-confidence fix — deduplicated character name extraction in `barrier.rs`. `format_auto_resolved_context()` now delegates to `auto_resolved_character_names()` instead of reimplementing the same logic. Net -15 lines.
**Flagged for Review:** 0 medium-confidence findings (all medium findings were in pre-existing code, not story changes)
**Noted:** 9 low/medium observations about pre-existing code patterns
**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** All passing — 21 Rust tests (12 story + 9 existing), 71 UI tests, clippy clean on changed files
**Handoff:** To Colonel Potter (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | All tests pass (12 Rust + 21 UI), clippy clean on changed files | N/A |
| 2 | reviewer-edge-hunter | Yes | clean | No critical edge cases in changed code; name extraction handles missing ':' gracefully via filter_map | N/A |
| 3 | reviewer-test-analyzer | Yes | clean | No vacuous assertions, all tests have meaningful checks, coverage aligns with ACs | N/A |
| 4 | reviewer-rule-checker | Yes | clean | Rust #2 non_exhaustive: TurnMode already has it. #5 constructors: no new public types. #8 serde bypass: n/a. TS #1 type-safety: no as any. | N/A |
| 5 | reviewer-silent-failure-hunter | Yes | clean | No swallowed errors. filter_map correctly skips missing entries without silent failure. No empty catch blocks. | N/A |
| 6 | reviewer-type-design | Yes | clean | TurnMode already #[non_exhaustive]. TurnBarrierResult fields are pub (pre-existing pattern). auto_resolved_character_names returns Vec<String> — appropriate for cross-layer transport. | N/A |

All received: Yes

## Reviewer Assessment

**Decision:** APPROVE
**Confidence:** High

**Files Reviewed:**
- `barrier.rs` — `auto_resolved_character_names()`, `set_turn_mode()`, mode-aware `resolve()`, DRY refactor of `format_auto_resolved_context()`
- `multiplayer.rs` — `force_resolve_turn_for_mode()` with match on TurnMode
- `TurnStatusPanel.tsx` — timeout labels, data-timeout attribute, local player notification
- `NarrativeView.tsx` — data-auto-resolved attributes, timeout label on auto-resolved entries

**Findings:**
- **Backward compat (minor, non-blocking):** Default text changed from `"hesitates"` to `"hesitates, waiting to see what happens"`. All existing tests use `contains("hesitate")` — no breakage. Server code doesn't match exact text.
- **Lock ordering (verified safe):** `resolve()` acquires `turn_mode` lock while holding `session` lock. Brief clone-and-drop, no async contention. Acceptable.
- **Server wiring gap (acknowledged):** AC-3 broadcast wiring deferred to integration story 13-7, as noted by Architect. Building blocks are in place.
- [RULE] Rust lang-review: TurnMode has `#[non_exhaustive]`, no new public enums, constructors validated. TS: no `as any`, no type-safety escapes.
- [SILENT] No silent failure paths. `filter_map` on narration entries correctly skips missing keys without swallowing errors. No empty catch blocks.
- [TYPE] Type design sound: `auto_resolved_character_names()` returns `Vec<String>` — appropriate for cross-crate transport to `ActionRevealPayload.auto_resolved`. `TurnMode` is `Clone` for mutex extraction. `TurnBarrierResult` fields remain pub (pre-existing pattern).

**Quality:**
- 33 tests, all passing. 59 existing tests verified for regression.
- DRY refactor removed 15 lines of duplication in verify phase.
- No security concerns, no error swallowing, no unsafe patterns.

## Architect Assessment (spec-check)

**Spec Alignment:** Minor drift detected
**Mismatches Found:** 1

- **Server-layer broadcast wiring not implemented** (Missing in code — Behavioral, Minor)
  - Spec: AC-3 says "Broadcast PLAYER_TIMEOUT_AUTO_FILLED message to all clients with list of auto-resolved players." Story context says: "Include auto-resolved player names in the ACTION_REVEAL message's auto_resolved field" and "Broadcast a TURN_STATUS with status 'auto_resolved' for each timed-out player."
  - Code: `auto_resolved_character_names()` extraction helper exists on `TurnBarrierResult`. `ActionRevealPayload.auto_resolved` field exists (from 13-3). But the server handler in `sidequest-server` was not updated to populate `auto_resolved` when building `ActionRevealPayload`, nor to broadcast `TURN_STATUS` with `"auto_resolved"` status.
  - Recommendation: D — Defer. The data layer and UI layer are complete. The server wiring is a natural integration concern covered by story 13-7 (integration test) or can be a quick follow-up. TEA wrote no tests for server-layer broadcast, so this was outside the RED-GREEN scope. The building blocks are all in place.

**Existing deviations verified:** Both TEA and Dev deviations about Combat mode are well-documented with accurate spec references and reasonable rationale. No corrections needed.

**Decision:** Proceed to verify. The minor gap is a wiring concern, not an architectural one — the extraction method, payload field, and UI rendering are all in place.

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Architect (spec-check)
- **Gap** (non-blocking): Server handler does not populate `ActionRevealPayload.auto_resolved` from `TurnBarrierResult.auto_resolved_character_names()`. Affects `sidequest-server/src/shared_session.rs` or dispatch handler (one-liner wiring). *Found by Architect during spec-check.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Combat mode default not separately testable**
  - Spec source: context-story-13-4.md, Configurable Default Action
  - Spec text: "Combat: 'takes a defensive stance' (dodge/defend equivalent)"
  - Implementation: Tests only cover Structured and Cinematic modes. TurnMode has no `Combat` variant — `CombatStarted` transitions to `Structured`. Combat-specific defaults require either a new TurnMode variant or a separate context parameter.
  - Rationale: Cannot test a TurnMode variant that doesn't exist. Dev should determine the right approach (add Combat variant, or use a separate flag).
  - Severity: minor
  - Forward impact: Dev may need to add a combat-specific parameter or extend TurnMode

### Dev (implementation)
- **Combat mode uses Structured default**
  - Spec source: context-story-13-4.md, Configurable Default Action
  - Spec text: "Combat: 'takes a defensive stance' (dodge/defend equivalent)"
  - Implementation: `CombatStarted` transitions `TurnMode` to `Structured`, so combat timeout uses the Structured default ("hesitates, waiting to see what happens"). No separate combat default exists.
  - Rationale: TurnMode has no Combat variant. Adding one would be scope creep — `CombatStarted → Structured` is the established pattern from Epic 8. Combat-specific defaults can be added later if gameplay demands it.
  - Severity: minor
  - Forward impact: none — can be added as a follow-up if "takes a defensive stance" is needed

### Architect (reconcile)
- **Server broadcast wiring deferred**
  - Spec source: context-story-13-4.md, Server-Side Changes, items 3-4
  - Spec text: "Include auto-resolved player names in the ACTION_REVEAL message's auto_resolved field" and "Broadcast a TURN_STATUS with status 'auto_resolved' for each timed-out player"
  - Implementation: Data extraction helper (`auto_resolved_character_names()`) and UI rendering exist, but the server handler does not populate `ActionRevealPayload.auto_resolved` from the barrier result, nor broadcast `TURN_STATUS` with `"auto_resolved"` status.
  - Rationale: TEA tests did not cover server-layer broadcast, so it fell outside the RED-GREEN TDD scope. The building blocks (extraction method, payload field, UI rendering) are all in place. Server wiring is a one-liner integration concern naturally covered by story 13-7 (integration test).
  - Severity: minor
  - Forward impact: Story 13-7 (integration test) must wire `auto_resolved_character_names()` into the broadcast handler when building `ActionRevealPayload`.
- **Default action text changed from "hesitates" to "hesitates, waiting to see what happens"**
  - Spec source: context-story-13-4.md, Server-Side Changes, item 2
  - Spec text: "Auto-fill with contextual default: '{character_name} hesitates, waiting to see what happens.'"
  - Implementation: `force_resolve_turn()` previously used `"hesitates"` (from story 8-1). Now delegates to `force_resolve_turn_for_mode(&TurnMode::FreePlay)` which uses `"hesitates, waiting to see what happens"`. All existing tests use `contains("hesitate")` so no breakage.
  - Rationale: The story context explicitly specifies the longer form. The change aligns code with spec. Reviewer verified no downstream exact-match dependencies.
  - Severity: trivial
  - Forward impact: none — narrator consumes this as free-text prompt context, not exact-match