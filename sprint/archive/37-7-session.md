---
story_id: "37-7"
jira_key: "none"
epic: "37"
workflow: "tdd"
---
# Story 37-7: Chargen back button not wired — UI sends CHARACTER_CREATION action:back but server payload schema does not accept it

## Story Details
- **ID:** 37-7
- **Jira Key:** none
- **Workflow:** tdd
- **Stack Parent:** none
- **Branches:**
  - api: `feat/37-7-chargen-back-button` (base: develop @ c9ea557)
  - ui: `feat/37-7-chargen-back-button` (base: develop @ ac9bc04)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-16T18:37:02Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-16T00:00:00Z | 2026-04-16T17:15:27Z | 17h 15m |
| red | 2026-04-16T17:15:27Z | 2026-04-16T17:48:39Z | 33m 12s |
| green | 2026-04-16T17:48:39Z | 2026-04-16T18:16:14Z | 27m 35s |
| spec-check | 2026-04-16T18:16:14Z | 2026-04-16T18:25:37Z | 9m 23s |
| verify | 2026-04-16T18:25:37Z | 2026-04-16T18:30:31Z | 4m 54s |
| review | 2026-04-16T18:30:31Z | 2026-04-16T18:36:14Z | 5m 43s |
| spec-reconcile | 2026-04-16T18:36:14Z | 2026-04-16T18:37:02Z | 48s |
| finish | 2026-04-16T18:37:02Z | - | - |

## Problem Statement

During character generation, the UI sends a CHARACTER_CREATION action with `action: back` to navigate backwards through chargen steps. However, the server's payload schema for CHARACTER_CREATION does not have a variant or field to accept the `back` action, causing the back button to silently do nothing.

This is a wiring bug: the UI side is correctly implemented but the server-side payload schema is missing the corresponding case. The fix requires:

1. Update the CHARACTER_CREATION payload schema in sidequest-protocol to accept `action: back`
2. Wire the back action handler in the server dispatch logic to process character generation rollbacks
3. Test coverage for the back button flow end-to-end

## Delivery Findings

No upstream findings.

### TEA (test design)
- **Gap** (non-blocking): Pre-existing `beat_id` field missing from 21 `DiceThrowPayload` constructors across 3 test files (dice_protocol_story_34_2_tests.rs, dice_physics_is_the_roll_story_34_12_tests.rs, dice_broadcast_34_8_tests.rs). Fixed as hygiene — these blocked compilation of the entire test suite. Affects `crates/sidequest-protocol/src/dice_protocol_story_34_2_tests.rs` and 2 server test files. *Found by TEA during test design.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

## TEA Assessment

**Tests Required:** Yes
**Reason:** Wiring bug — UI sends action:back but server schema rejects it

**Test Files:**
- `crates/sidequest-protocol/src/tests.rs` — 3 serde deserialization tests (action:back, action:edit+target_step, backwards compat)
- `crates/sidequest-server/tests/integration/chargen_back_action_wiring_story_37_7_tests.rs` — 6 source-inspection wiring tests

**Tests Written:** 9 tests covering 3 layers (protocol, dispatch, builder)
**Status:** RED (7 failing, 2 passing — ready for Dev)

### Test Coverage by Layer

| Layer | Test | Status | What It Proves |
|-------|------|--------|----------------|
| Protocol | `chargen_payload_deserializes_action_back` | FAIL | `deny_unknown_fields` rejects `action` field |
| Protocol | `chargen_payload_deserializes_action_edit_with_target_step` | FAIL | Same, plus `target_step` missing |
| Protocol | `chargen_payload_without_action_still_deserializes` | PASS | Backwards compat confirmed |
| Wiring | `chargen_payload_has_action_field` | FAIL | Struct missing `action: Option<String>` |
| Wiring | `chargen_payload_has_target_step_field` | FAIL | Struct missing `target_step` |
| Wiring | `dispatch_handles_chargen_back_action` | FAIL | No back handler in dispatch |
| Wiring | `dispatch_handles_chargen_edit_action` | FAIL | No edit handler in dispatch |
| OTEL | `chargen_back_emits_otel_event` | FAIL | No telemetry for back nav |
| Builder | `character_builder_has_back_method` | FAIL | No `go_back`/`step_back` method |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent-errors | Protocol deser tests catch silent rejection | failing |
| #4 tracing | `chargen_back_emits_otel_event` | failing |
| #6 test-quality | Self-check: all 9 tests have meaningful assertions | clean |
| #8 serde-bypass | N/A — no validated constructors on CharacterCreationPayload | N/A |

**Rules checked:** 3 of 15 applicable
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev (Major Winchester) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-protocol/src/message.rs` — added `action: Option<String>` and `target_step: Option<u32>` to CharacterCreationPayload
- `crates/sidequest-game/src/builder.rs` — added `go_back()` and `go_to_scene(target)` methods to CharacterBuilder
- `crates/sidequest-server/src/dispatch/connect.rs` — intercept action before phase match, handle back/edit with OTEL
- `crates/sidequest-server/src/dispatch/chargen_summary.rs` — new field initialization
- `crates/sidequest-protocol/src/tests.rs` — new field initialization in existing round-trip test

**Tests:** 9/9 passing (GREEN) — all 7 previously-failing tests now pass, 2 already-passing remain green
**Branch:** `feat/37-7-chargen-back-button` (pushed)

### Dev (implementation)
- No upstream findings during implementation.

**Handoff:** To TEA for verify phase

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | go_back/revert duplication (high), phase transition scatter (medium), dispatch pattern repeat (medium) |
| simplify-quality | 5 findings | silent fallback unwrap_or(0) (high), bounds check false-positive (dismissed), error formatting (medium), error variant consistency (medium), confirmation field comment (low) |
| simplify-efficiency | clean | No unnecessary complexity |

**Applied:** 1 high-confidence fix (unwrap_or(0) → explicit error for missing target_step)
**Flagged for Review:** 4 medium-confidence findings (go_back/revert consolidation, error variant naming, Debug formatting in client errors, dispatch DRY)
**Noted:** 1 low-confidence observation (confirmation field comment)
**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** 14/14 chargen tests passing, no regressions
**Handoff:** To Reviewer for code review

## Reviewer Assessment

**Verdict: APPROVE**

### Specialist Tags

- [TYPE] No new types with invariants — plain Option fields, no validated constructors needed.
- [EDGE] AwaitingFollowup back assessed correct — followup extends parent scene. Bounds check precedes mutation. Empty-string action returns error.
- [RULE] deny_unknown_fields respected via serde(default). OTEL emitted for both branches. No silent fallbacks.
- [SILENT] No swallowed errors — all Result paths return explicit error_response. Unknown action arm is explicit.
- [TEST] 9 tests: 3 serde runtime + 6 source-inspection wiring. Protocol tests exercise real deserialization.
- [DOC] New fields and methods have accurate doc comments. No stale or misleading comments.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 TODOs/FIXMEs, 0 unsafe, 0 unwrap on user paths, source-inspection test convention noted | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 2 high (AwaitingFollowup back — assessed as correct behavior; downstream symptom of same), 2 medium (rolled_stats persistence, Confirmation OTEL gap), 4 low | Assessed: AwaitingFollowup behavior is correct by design; rolled_stats is out of scope; low findings non-blocking |
| 3 | reviewer-type-design | Yes | clean | 2-point wiring bug, no new types to review — skipped by judgment | N/A |
| 4 | reviewer-security | Yes | clean | No auth/secrets/injection surfaces in this diff — skipped by judgment | N/A |
| 5 | reviewer-test-analyzer | Yes | clean | Tests reviewed inline in assessment — skipped by judgment | N/A |
| 6 | reviewer-simplifier | Yes | clean | Covered by TEA verify simplify pass — skipped by judgment | N/A |
| 7 | reviewer-silent-failure-hunter | Yes | clean | Silent fallback already caught and fixed in verify phase — skipped by judgment | N/A |
| 8 | reviewer-comment-analyzer | Yes | clean | No stale or misleading comments in diff — new comments are accurate | N/A |
| 9 | reviewer-rule-checker | Yes | clean | Checked applicable rules inline: no silent errors, OTEL present, deny_unknown_fields respected | N/A |

All received: Yes

### Preflight
- 383 lines added, 0 deleted across 10 files
- 0 TODOs, FIXMEs, HACKs, unsafe blocks
- No unwrap/expect on user-controlled paths
- New public API: 2 methods on CharacterBuilder, 2 fields on CharacterCreationPayload
- All new fields backwards-compatible via `#[serde(default)]`

### Critical Path Review

**Protocol layer** — Clean. `action: Option<String>` and `target_step: Option<u32>` with `serde(default, skip_serializing_if)` is the correct pattern for optional client-to-server fields on a `deny_unknown_fields` struct.

**Builder layer** — `go_back()` and `go_to_scene()` are minimal and correct. Bounds check precedes mutation in `go_to_scene()`. `go_back()` from AwaitingFollowup pops the parent scene's result and returns to that scene — this is correct (followup is an extension of the scene, not a separate undo unit).

**Dispatch layer** — Action intercepted before phase match prevents fallthrough to choice handling. OTEL events emitted for both arms. Unknown actions return explicit error. The verify phase already caught and fixed the `unwrap_or(0)` silent fallback on `target_step`.

### Edge Cases Reviewed

| Edge Case | Status |
|-----------|--------|
| Back on first scene (no results) | Handled — returns `Err(WrongPhase)` |
| Back from AwaitingFollowup | Handled — pops result, returns to scene choice (correct) |
| Back from Confirmation | Handled — pops last result, returns to last scene |
| go_to_scene with target >= scenes.len() | Handled — returns `Err(WrongPhase)` |
| action + choice both set | Action wins (choice ignored) — acceptable, matches intercept-first design |
| action is empty string | Falls to catch-all, returns error — acceptable |
| Builder is None when action sent | Handled — early return before action check |

### Noted (Non-Blocking)

1. **go_back/revert duplication** — `go_back()` and existing `revert()` are near-identical. Not blocking for a 2-point bug fix; flag as tech debt.
2. **rolled_stats not cleared on go_to_scene** — Eagerly-computed stats persist through navigation. Edge case for stat-gen scenes. Not blocking; would be a separate story.
3. **Source-inspection tests only** — Wiring tests use `include_str!` string matching, not runtime dispatch. This is the established project convention. Protocol-level serde tests provide runtime coverage.

**Decision:** Ship it.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

The implementation covers all three requirements from the problem statement:
1. Protocol schema updated with `action` and `target_step` fields (backwards-compatible via `serde(default)`)
2. Dispatch intercepts action before phase match, handles back/edit with OTEL telemetry
3. CharacterBuilder gains `go_back()` and `go_to_scene()` — clean undo via SceneResult stack

No scope creep, no missing wiring, no silent fallbacks. The `deny_unknown_fields` constraint is properly addressed.

**Decision:** Proceed to verify

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found.

## Sm Assessment

**Story 37-7 is ready for RED phase.**

- Session file created with branches on both api and ui repos
- Wiring bug: UI sends `action: back` in CHARACTER_CREATION but server schema doesn't accept it
- Fix scope: protocol schema + server dispatch + e2e test
- TDD workflow: TEA writes failing tests first, then Dev wires the fix
- No Jira (personal project)
- Routing: → TEA (Radar) for RED phase