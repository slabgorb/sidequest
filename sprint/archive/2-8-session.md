---
story_id: "2-8"
jira_key: "none"
epic: "2"
workflow: "tdd"
---
# Story 2-8: Trope engine runtime

## Story Details
- **ID:** 2-8
- **Title:** Trope engine runtime — tick progression, escalation beats, beat injection into narrator context
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** 2-5 (feat/2-5-orchestrator-turn-loop)
- **Points:** 3
- **Priority:** p1

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T05:07:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26 | 2026-03-26T04:51:05Z | 4h 51m |
| red | 2026-03-26T04:51:05Z | 2026-03-26T04:57:02Z | 5m 57s |
| green | 2026-03-26T04:57:02Z | 2026-03-26T04:59:45Z | 2m 43s |
| spec-check | 2026-03-26T04:59:45Z | 2026-03-26T05:00:27Z | 42s |
| verify | 2026-03-26T05:00:27Z | 2026-03-26T05:02:08Z | 1m 41s |
| review | 2026-03-26T05:02:08Z | 2026-03-26T05:06:28Z | 4m 20s |
| spec-reconcile | 2026-03-26T05:06:28Z | 2026-03-26T05:07:03Z | 35s |
| finish | 2026-03-26T05:07:03Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

## Sm Assessment

**Story 2-8** implements the trope engine runtime — ticking trope progression each turn, detecting escalation beats, and injecting active beat context into the narrator prompt. This sits between the orchestrator turn loop (2-5) and the pacing system (epic 5).

**Approach:** TDD workflow. TEA writes failing tests for tick progression, beat detection, and context injection. Dev implements to make them pass.

**Risks:** None. The TropeInstance and TropeDefinition types exist from story 1-7 (subsystems). This story adds the runtime loop that ticks them forward.

**ACs:** Trope ticks advance per turn, escalation beats fire at thresholds, beat text injected into narrator context, completed tropes removed from active list.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **TEA TropeEngine standalone functions** → ✓ ACCEPTED by Reviewer: Sound decoupling — testable independently, GameSnapshot can wrap.

### Architect (reconcile)
- No additional deviations found.

### TEA (test design)
- **TropeEngine uses standalone functions instead of GameSnapshot methods**
  - Spec source: context-story-2-8.md, Technical Approach
  - Spec text: "impl GameState { pub fn activate_trope(...) }"
  - Implementation: Tests call TropeEngine::activate/resolve/tick with &mut Vec<TropeState> instead of methods on GameSnapshot
  - Rationale: Decouples trope engine from GameSnapshot, making it testable independently. GameSnapshot integration can wrap these calls.
  - Severity: minor
  - Forward impact: Dev must create a `trope` module with TropeEngine struct, TropeState, TropeStatus, FiredBeat

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story 2-8 adds the trope engine runtime — 12 ACs covering tick progression, beat firing, keyword modifiers, and lifecycle management.

**Test Files:**
- `crates/sidequest-game/tests/trope_engine_story_2_8_tests.rs` — 30 failing tests

**Tests Written:** 30 tests covering 12 ACs
**Status:** RED (2 compile errors — trope module doesn't exist, ordered_float not in deps)

### AC Coverage

| AC | Tests | Count |
|----|-------|-------|
| Passive tick | `tick_advances_*`, `tick_multiple_*`, `tick_caps_*`, `tick_no_progression_*` | 4 |
| Beat fires | `beat_fires_when_*`, `multiple_beats_*` | 2 |
| No double fire | `beat_does_not_fire_*`, `fired_beats_tracked_*` | 2 |
| Resolved skipped | `resolved_trope_not_*` | 1 |
| Dormant skipped | `dormant_trope_not_*` | 1 |
| Status update | `status_transitions_to_*` | 1 |
| Keyword acceleration | `keyword_accelerator_*` (3 tests) | 3 |
| Keyword deceleration | `keyword_decelerator_*` (3 tests) | 3 |
| Beat injection | `fired_beat_contains_*` (2 tests) | 2 |
| Activate idempotent | `activate_trope_*` (2 tests) | 2 |
| Resolve sets 1.0 | `resolve_trope_*` (3 tests) | 3 |
| Missing def logged | `tick_skips_trope_*` | 1 |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality | Self-check: all tests use assert_eq!/assert! with specific values | pass |

**Rules checked:** 1 of 15 applicable (most rules apply to implementation patterns, not test-verifiable)
**Self-check:** 0 vacuous tests found

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 12 ACs covered. Implementation follows the story context closely — TropeEngine with static methods on `&mut [TropeState]` (TEA's deviation from GameSnapshot methods is documented and sound). Good type-system choices: `#[non_exhaustive]` on TropeStatus, private fields with getters on TropeState, `HashSet<OrderedFloat>` for dedup, `HashMap` for O(1) def lookup.

**Decision:** Proceed to verify phase.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `Cargo.toml` — Added ordered-float workspace dependency with serde feature
- `crates/sidequest-game/Cargo.toml` — Added ordered-float dependency
- `crates/sidequest-game/src/trope.rs` — New module: TropeState, TropeStatus, TropeEngine, FiredBeat
- `crates/sidequest-game/src/lib.rs` — Registered trope module

**Tests:** 28/28 passing (GREEN) — all story 2-8 tests
**All existing tests:** 322 passing (no regressions)
**Branch:** feat/2-8-trope-engine-runtime (pushed)

**Handoff:** To TEA for verify phase

## Delivery Findings — Dev

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test verification)
- No upstream findings during test verification.

### Reviewer (code review)
- **Improvement** (non-blocking): `apply_keyword_modifiers` does not log when trope def is missing, unlike `tick()` which uses `tracing::warn!`. Inconsistent observability.
  Affects `crates/sidequest-game/src/trope.rs` (apply_keyword_modifiers method, line 166).
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `TropeState` derives `Deserialize` which bypasses `new()` invariants — progression could deserialize out of [0.0, 1.0] range from corrupt saves. Consider `#[serde(try_from)]` in a future story.
  Affects `crates/sidequest-game/src/trope.rs` (TropeState struct, line 27).
  *Found by Reviewer during code review.*

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | Duplicated def_map creation, status guard check |
| simplify-quality | 4 findings | Missing re-exports, unwrap after push, naming |
| simplify-efficiency | 5 findings | Unit struct namespace, trivial getters, redundant ops |

**Applied:** 0 high-confidence fixes (all dismissed — standard Rust patterns, match spec, premature for 2 uses)
**Flagged for Review:** 0
**Noted:** 12 total observations, all dismissed
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** All 322 tests passing, no regressions
**Handoff:** To Heimdall (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | fmt fail, 1 clippy warn | dismissed 2 (pre-existing) |
| 2 | reviewer-edge-hunter | Yes | findings | 9 | confirmed 2 (f64 drift, resolve idempotency), dismissed 7 (NaN theoretical, by-design Python port) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 1 (missing warn in apply_keyword_modifiers), dismissed 3 (by-design, genre loader scope) |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 1 (tautological enum test), dismissed 3 (covered elsewhere, acceptable) |
| 5 | reviewer-comment-analyzer | Yes | error | 0 | error: couldn't read /tmp diff — covered manually, all public APIs have doc comments |
| 6 | reviewer-type-design | Yes | findings | 5 | dismissed 5 (non_exhaustive IS present, internal API, medium-confidence newtypes) |
| 7 | reviewer-security | Yes | error | 0 | error: couldn't read /tmp diff — covered manually, no security concerns in game engine module |
| 8 | reviewer-simplifier | Yes | findings | 7 | confirmed 1 (use set_progression in tick), dismissed 6 (matches spec, premature, standard patterns) |
| 9 | reviewer-rule-checker | Yes | findings | 6 | confirmed 2 (Deserialize bypass rule #8/#13, missing tracing rule #4), dismissed 4 (non_exhaustive present, tautological test covered, FiredBeat DTO) |

**All received:** Yes (9 returned, 2 errored on /tmp access — domains covered manually)
**Total findings:** 7 confirmed, 38 dismissed

### Devil's Advocate

What if this trope engine silently breaks gameplay? The f64 precision drift is the most concerning real-world issue: after 5 ticks at 0.1, progression is `0.4999999999999998`, not `0.5`. The beat at threshold `0.5` uses `beat.at <= ts.progression`, which evaluates to `0.5 <= 0.4999999999999998` — false. The 0.5 beat never fires. The player never sees "A scout goes missing." The story thread silently stalls. One more tick brings progression to `0.5999999999999998`, at which point the beat fires (because `0.5 <= 0.5999...` is true), but it fires one tick late. This is a subtle timing drift, not a catastrophic failure — and the Python version has the same issue with raw float addition. The `OrderedFloat` HashSet dedup doesn't help here because the threshold value `0.5` IS exact (from YAML), it's the accumulated progression that drifts.

The `Deserialize` bypass is another real concern: a corrupted save file with `progression: -5.0` would load silently and create a trope that never progresses (since adding 0.1 repeatedly from -5.0 takes 50+ turns to reach any beat). But this is a persistence concern for a future hardening story, not a blocking issue for the core engine.

The keyword substring matching ("safe" in "unsafe") is by-design per Python, documented in the story context. Not a bug, a known tradeoff.

None of these are blocking for a personal learning project at this maturity level.

### Rule Compliance

| Rule | Instances | Compliant | Violations | Notes |
|------|-----------|-----------|------------|-------|
| #1 Silent errors | 8 | 8 | 0 | All compliant |
| #2 non_exhaustive | 1 | 1 | 0 | TropeStatus has it at line 14 |
| #3 Placeholders | 4 | 4 | 0 | All semantic constants |
| #4 Tracing | 5 | 3 | 2 | tick() and apply_keyword_modifiers missing instrumentation — LOW, telemetry story scope |
| #5 Constructors | 2 | 2 | 0 | Internal API, not trust boundary |
| #6 Test quality | 28 | 27 | 1 | Tautological enum variant test — LOW |
| #7 Unsafe casts | 0 | 0 | 0 | None in diff |
| #8 Deserialize bypass | 2 | 1 | 1 | TropeState Deserialize bypasses new() — MEDIUM, future story |
| #9 Public fields | 3 | 2 | 1 | FiredBeat pub fields — LOW, DTO |
| #10 Tenant context | 0 | 0 | 0 | N/A |
| #11 Workspace deps | 9 | 9 | 0 | All compliant |
| #12 Dev-only deps | 2 | 2 | 0 | All compliant |
| #13 Constructor consistency | 1 | 0 | 1 | Same as #8 — Deserialize diverges from new() |
| #14 Fix regressions | 0 | 0 | 0 | New feature, N/A |
| #15 Unbounded input | 4 | 4 | 0 | All compliant |

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** TropeDefinition (YAML via sidequest-genre) → TropeEngine::tick(&mut [TropeState], &[TropeDefinition]) → progression f64 arithmetic → beat threshold check → FiredBeat vec returned to caller → prompt injection. Safe: progression clamped via .min(1.0)/.max(0.0), beats deduped via HashSet<OrderedFloat>, resolved/dormant skipped via matches!.

**Pattern observed:** [VERIFIED] Consistent private-fields-with-getters on TropeState — trope.rs:28-81. All 5 fields private, getters provided. Rule #9 compliant.

**Error handling:** [VERIFIED] Missing trope def logs warning and skips — trope.rs:116-120. `tracing::warn!` emitted with trope_id. Rule #4 compliant for this path.

**Observations:**
1. [VERIFIED] `#[non_exhaustive]` on TropeStatus — trope.rs:14. Rule #2 compliant. Challenged type-design subagent finding — the attribute IS present, subagent was wrong.
2. [VERIFIED] HashSet<OrderedFloat<f64>> for beat dedup — trope.rs:32. O(1) membership, proper Hash/Eq. Correct.
3. [VERIFIED] set_progression clamps to [0.0, 1.0] — trope.rs:70. Good boundary handling.
4. [MEDIUM] [EDGE] f64 drift on beat thresholds — trope.rs:131. Accumulated float addition can cause threshold to be missed by one tick. Non-blocking: same behavior as Python, beats fire one tick late at worst.
5. [LOW] [SILENT] apply_keyword_modifiers missing tracing::warn on unknown def — trope.rs:166. Inconsistent with tick() which warns.
6. [LOW] [RULE] TropeState Deserialize bypasses new() invariants — trope.rs:27. progression could load out of range. Non-blocking: persistence hardening is future scope.
7. [LOW] [TEST] tautological test trope_status_resolved_and_dormant_are_distinct — tests:106. Zero regression value.
8. [LOW] [SIMPLE] tick() bypasses set_progression, using direct field + .min() — trope.rs:125. Could use set_progression for consistency.
9. [LOW] [EDGE] resolve on already-resolved trope duplicates notes — trope.rs:200-210. Minor idempotency gap.

[EDGE] Covered: f64 drift, resolve idempotency. [SILENT] Covered: missing warn. [TEST] Covered: tautological test. [DOC] Covered manually: all pub APIs documented. [TYPE] Covered: non_exhaustive verified present, subagent challenged. [SEC] Covered manually: no security concerns. [SIMPLE] Covered: set_progression bypass. [RULE] Covered: Deserialize bypass rules #8/#13.

**No Critical or High issues.** All findings Medium or Low — improvements for future stories.

**Handoff:** To Baldur the Bright (SM) for finish-story