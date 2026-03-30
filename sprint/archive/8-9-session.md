---
story_id: "8-9"
jira_key: "none"
epic: "8"
workflow: "tdd"
---
# Story 8-9: Turn reminders — notify idle players

## Story Details
- **ID:** 8-9
- **Jira Key:** none (personal project, no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** 8-2 (Turn barrier — wait for all players before resolving turn)
- **Points:** 2
- **Priority:** p2

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-27T19:38:05Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T19:19:04Z | 2026-03-27T19:19:58Z | 54s |
| red | 2026-03-27T19:19:58Z | 2026-03-27T19:26:38Z | 6m 40s |
| green | 2026-03-27T19:26:38Z | 2026-03-27T19:29:01Z | 2m 23s |
| spec-check | 2026-03-27T19:29:01Z | 2026-03-27T19:29:58Z | 57s |
| verify | 2026-03-27T19:29:58Z | 2026-03-27T19:32:20Z | 2m 22s |
| review | 2026-03-27T19:32:20Z | 2026-03-27T19:37:17Z | 4m 57s |
| spec-reconcile | 2026-03-27T19:37:17Z | 2026-03-27T19:38:05Z | 48s |
| finish | 2026-03-27T19:38:05Z | - | - |

## Story Context

This story adds idle player detection and notifications to the turn barrier system. When players don't submit actions within a configurable timeout, the server sends reminder messages and optionally auto-submits a default action (pass).

**Acceptance Criteria:**
1. Idle timeout is configurable per game session
2. Reminder messages are sent to idle players via WebSocket
3. Configurable auto-pass behavior (skip turn, use default action, or wait indefinitely)
4. Idle state tracking per player during turn barrier wait
5. Reminders include time remaining until auto-pass (if enabled)

**Technical Context:**
- Builds on 8-2 (Turn barrier) which provides the turn synchronization primitive
- MultiplayerSession coordinates the barrier and player state
- Idle detection happens in the turn barrier loop
- Notifications sent via the session's broadcast mechanism

**Key References:**
- sq-2/sidequest/game/turn_manager.py (reference implementation)
- OQ-2 docs/adr/029-guest-npc-players.md (NPC behavior patterns)

## Sm Assessment

Story 8-9 closes out Epic 8 (Multiplayer). This is a 2-point TDD story building on the turn barrier (8-2). Scope is well-defined: idle detection, configurable timeouts, WebSocket reminders, and optional auto-pass. No blockers. Routing to TEA for red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 2-point TDD story with new API surface (validated constructor, mode-aware checks, async execution)

**Test Files:**
- `crates/sidequest-game/tests/turn_reminders_8_9_gaps_tests.rs` — 28 new tests covering validation, FreePlay skip, async reminder, genre voice

**Tests Written:** 28 tests covering 6 ACs (from story context)
**Status:** RED (compilation errors — APIs don't exist yet)

**Existing Tests:** 24/24 passing in `turn_reminders_story_8_9_tests.rs` (unchanged)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #5 validated constructors | `try_new_rejects_negative_threshold`, `try_new_rejects_nan`, `try_new_rejects_empty_message` + 7 more | failing (compile) |
| #6 test quality | Self-checked all 28 tests — every test has meaningful assertions | passing |
| #9 public fields | Existing tests verify private fields with getters | passing (existing) |

**Rules checked:** 3 of 15 applicable (most rules apply to implementation, not test-only changes)
**Self-check:** 0 vacuous tests found

### Dev Implementation Required

1. **`ReminderError`** enum — validation error type (threshold out of range, empty message)
2. **`ReminderConfig::try_new()`** — validated constructor returning `Result<Self, ReminderError>`
3. **`ReminderResult::check_with_mode()`** — takes `&TurnMode`, returns empty for FreePlay
4. **`ReminderResult::run_reminder()`** — async fn: sleeps for delay, checks idle players, cancellation-safe

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/turn_reminder.rs` — added `ReminderError` enum, `try_new()`, `check_with_mode()`, `run_reminder()` async

**Tests:** 47/47 passing (GREEN) — 23 new gap tests + 24 existing
**Branch:** feat/8-9-turn-reminders (pushed)

**Handoff:** To Tyr One-Handed (TEA) for verify phase

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 6 story context ACs are covered by the implementation. Three structural differences from the reference code are improvements: private fields (Rule #9), result-returning `run_reminder` (separation of concerns), and encapsulated session parameter. TEA's deviation log for session AC3/AC5 is accurate — auto-pass behavior belongs to story 8-2's `force_resolve_turn()`, not to the reminder system.

**Decision:** Proceed to review

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 1

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | FreePlay empty result duplicated (high), trim pattern repeated across crate (medium) |
| simplify-quality | 3 findings | lib.rs re-export missing (high), check() "dead code" FALSE POSITIVE (medium), redundant FreePlay check (medium) |
| simplify-efficiency | 1 finding | FreePlay mode check duplicated (high) |

**Applied:** 1 high-confidence fix — extracted `ReminderResult::empty()` helper to DRY FreePlay check in `check_with_mode()` and `run_reminder()`
**Flagged for Review:** 1 medium-confidence finding — `pub use` re-export for turn_reminder types not in lib.rs (convention, not a bug)
**Noted:** 1 medium-confidence observation — trim/is_empty pattern exists elsewhere in crate (future extraction candidate)
**Reverted:** 0
**Dismissed:** 1 — `check()` flagged as dead code is a false positive (24 existing tests + internal delegation)

**Overall:** simplify: applied 1 fix

**Quality Checks:** All 47 tests passing
**Handoff:** To Heimdall (Reviewer) for code review

## Delivery Findings

### TEA (test verification)
- No upstream findings during test verification.

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test design)
- **Conflict** (non-blocking): Session file AC3 ("Configurable auto-pass behavior") and AC5 ("time remaining until auto-pass") conflict with story context scope boundaries which exclude auto-kick/escalating behavior. Auto-pass is handled by `force_resolve_turn()` in story 8-2's TurnBarrier. Tests follow story context ACs (higher detail, in-scope). Affects `.session/8-9-session.md` (ACs need reconciliation). *Found by TEA during test design.*

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | fmt fail, 17 pre-existing clippy warns | confirmed 1 (fmt), dismissed 1 (pre-existing) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 1 (new bypass), dismissed 2 (out of scope) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 (3 rules) | confirmed 3 (tracing, new bypass, vacuous test), 2 duplicate of silent-failure |

**All received:** Yes (3 returned with findings, 6 disabled via settings)
**Total findings:** 4 confirmed (1 duplicate merged), 3 dismissed (with rationale)

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] `ReminderError` has `#[non_exhaustive]` and uses `thiserror` — turn_reminder.rs:17-26. Complies with Rules #2 and error type conventions.
2. [VERIFIED] `ReminderConfig` fields (`threshold`, `message`) are private with getters — turn_reminder.rs:31-32, getters at lines 43-48. Complies with Rule #9.
3. [VERIFIED] `ReminderResult` fields (`idle_players`, `message`) are private with getters — turn_reminder.rs:81-82, getters at lines 101-108. Complies with Rule #9.
4. [VERIFIED] `try_new()` validates threshold ∈ [0.0, 1.0], rejects NaN/Inf, rejects empty/whitespace message — turn_reminder.rs:53-61. Complies with Rule #5 for the validated path.
5. [VERIFIED] `run_reminder()` is cancellation-safe — only await points are `tokio::time::sleep` (cancel-safe) and `session.read().await` (cancel-safe RwLock read). No state mutation between awaits. Doc comment at line 130-134 is accurate.
6. [VERIFIED] FreePlay suppression works correctly — `check_with_mode()` at line 126 pattern-matches `TurnMode::FreePlay` and returns empty. `run_reminder()` at line 146 has same guard before sleeping. Both delegate to `empty()` helper at line 116.
7. [VERIFIED] No `#[derive(Deserialize)]` on any type — Rules #8 and #13 are not applicable. If Deserialize is added later, it must use `serde(try_from)`.
8. [MEDIUM] [RULE] No tracing instrumentation — turn_reminder.rs has zero `tracing::*` calls. Rule #4 requires tracing on error paths. `try_new()` validation failures at lines 55/58 return `Err` silently. `run_reminder()` has no `#[instrument]`. Valid Rule #4 concern but not in story ACs, and no other code in this file had tracing before this PR. Recommend adding tracing as tech debt.
9. [MEDIUM] [SILENT] `ReminderConfig::new()` remains public alongside `try_new()` — turn_reminder.rs:37. Callers can bypass validation. Pre-existing API (not introduced by this PR). Changing it would break 24 existing tests. Recommend deprecation or `pub(crate)` in a follow-up.
10. [LOW] [RULE] `config_fields_are_private` test has zero assertions — story_8_9_tests.rs:85. Uses `let _` to discard values. Pre-existing test, not introduced by this PR. Recommend removal in a follow-up.
11. [LOW] `cargo fmt --check` fails on story files — formatting issues in turn_reminder.rs:85 (chain formatting) and both test files (assert! macro formatting). Mechanical fix: `cargo fmt -p sidequest-game`.

### Rule Compliance

| Rule | Instances | Status |
|------|-----------|--------|
| #1 silent errors | 4 checked | PASS — no .ok()/.unwrap_or_default() on user input |
| #2 non_exhaustive | 1 enum (ReminderError) | PASS — has #[non_exhaustive] |
| #3 placeholders | 2 checked | PASS — no magic numbers |
| #4 tracing | 3 paths checked | MEDIUM — no tracing on error/async paths |
| #5 constructors | 2 constructors | MEDIUM — new() unvalidated alongside try_new() |
| #6 test quality | 25 tests checked | LOW — 1 vacuous test (pre-existing) |
| #7 unsafe casts | 0 in diff | PASS — N/A |
| #8 serde bypass | 2 types | PASS — no Deserialize |
| #9 public fields | 4 fields | PASS — all private with getters |
| #10 tenant context | 0 traits | PASS — N/A |
| #11 workspace deps | 3 checked | PASS |
| #12 dev deps | 4 checked | PASS |
| #13 constructor/deser | 1 type | PASS — no Deserialize |
| #14 fix regressions | 3 checked | PASS |
| #15 unbounded input | 2 checked | PASS |

### Devil's Advocate

What if this code is broken? Let me try to break it.

**Race condition in `run_reminder`:** The function sleeps, then acquires a read lock to check idle players. Between the sleep completing and the lock acquisition, players could submit actions. This means the reminder could fire for a player who submitted 1ms before the check. Is this a bug? No — this is the expected eventual-consistency behavior for a reminder system. The alternative (holding a lock across the sleep) would block all action submissions during the reminder delay, which is far worse. The reminder is a nudge, not a real-time guarantee.

**What if `barrier_timeout` is zero?** `reminder_delay()` would compute `Duration::from_secs(0) * 0.6 = 0`. The sleep would return immediately, and the check would run. This is correct — if the barrier has no timeout, the reminder fires instantly, which degenerates to a one-time check. Not harmful.

**What if `pending_players()` panics or the session is poisoned?** `pending_players()` is a pure computation over a HashMap — no panics possible unless the allocator fails. The `RwLock` in `run_reminder` uses tokio's async RwLock (not std), which cannot be poisoned. Safe.

**What if a malicious genre pack sets threshold to exactly 0.0?** The `try_new()` constructor accepts 0.0 as valid. An instant reminder is arguably surprising but not dangerous — it fires once and the system moves on. The barrier still resolves normally.

**What about the `message` field allowing arbitrary strings?** A genre pack could inject control characters, ANSI escapes, or very long strings. The `try_new()` only rejects empty/whitespace. This is a display string sent via WebSocket — the UI should sanitize. Not a server-side vulnerability, but worth noting for the client team.

**What if someone adds `#[derive(Deserialize)]` to `ReminderConfig` later?** They'd bypass `try_new()` validation entirely. Rule #8 would be violated. The code has no compile-time guard against this. This is documented as a future concern — acceptable for now, but a code review trap for the next person who touches this file.

The devil's advocate found no critical issues. The race condition is benign by design. The zero-timeout edge case is handled. The arbitrary string concern is a client-side responsibility. The Deserialize bypass is a future risk, not a current one.

**Data flow traced:** Genre config (YAML) → `ReminderConfig::try_new()` (validated) → `run_reminder()` (async sleep + check) → `ReminderResult` (returned to caller) → caller sends via WebSocket. Safe — validation at entry, no mutation in the async path.

**Pattern observed:** Clean separation between "who is idle" (`check`/`check_with_mode`) and "when to check" (`run_reminder`). Good testability — sync logic tested synchronously, async orchestration tested with tokio.

**Error handling:** `try_new()` returns `Result<Self, ReminderError>` with descriptive error messages. `run_reminder()` is infallible (returns empty on FreePlay, populated otherwise). No panic paths.

[EDGE] N/A — edge-hunter disabled.
[SILENT] `new()` bypass confirmed as MEDIUM — pre-existing, recommend deprecation.
[TEST] N/A — test-analyzer disabled.
[DOC] N/A — comment-analyzer disabled.
[TYPE] N/A — type-design disabled.
[SEC] N/A — security disabled.
[SIMPLE] N/A — simplifier disabled.
[RULE] Rule #4 tracing and Rule #5 constructor confirmed as MEDIUM — recommend follow-up.

**Handoff:** To Baldur the Bright (SM) for finish-story. Formatting fix (`cargo fmt`) needed before merge.

## Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): `ReminderConfig::new()` should be deprecated or made `pub(crate)` now that `try_new()` exists. Affects `crates/sidequest-game/src/turn_reminder.rs` (change `new` visibility). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Add `tracing::warn!` to `try_new()` rejection paths and `#[instrument]` to `run_reminder()`. Affects `crates/sidequest-game/src/turn_reminder.rs` (add tracing calls). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Remove vacuous `config_fields_are_private` test. Affects `crates/sidequest-game/tests/turn_reminders_story_8_9_tests.rs` (delete test). *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **Session AC3 and AC5 excluded from tests**
  - Spec source: .session/8-9-session.md, AC-3 and AC-5
  - Spec text: "Configurable auto-pass behavior (skip turn, use default action, or wait indefinitely)" and "Reminders include time remaining until auto-pass (if enabled)"
  - Implementation: Tests cover story context ACs only — reminders, not auto-pass
  - Rationale: Story context explicitly scopes out auto-kick/escalation. Auto-pass is already implemented in TurnBarrier::force_resolve_turn() (story 8-2). Session ACs appear to conflate reminder and barrier timeout behavior.
  - Severity: minor
  - Forward impact: If auto-pass reminder integration is desired, it would be a separate story

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **Session AC3 and AC5 excluded from tests** → ✓ ACCEPTED by Reviewer: Agrees with TEA reasoning — auto-pass is story 8-2's TurnBarrier concern, not the reminder system. Story context explicitly scopes it out.
- **Dev: No deviations from spec** → ✓ ACCEPTED by Reviewer: Implementation matches all 6 story context ACs. No undocumented deviations found.

### Architect (reconcile)
- No additional deviations found. TEA's deviation entry for session AC3/AC5 is accurate, properly formatted, and correctly accepted by Reviewer. The implementation's structural differences from the story context reference code (returning `ReminderResult` instead of directly sending messages, taking `Arc<RwLock<MultiplayerSession>>` instead of separate sets) are documented improvements in the Architect spec-check assessment, not specification drift.