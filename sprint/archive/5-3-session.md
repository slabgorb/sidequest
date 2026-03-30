---
story_id: "5-3"
jira_key: "none"
epic: "5"
workflow: "tdd"
---
# Story 5-3: Drama Weight Computation — max(action_tension, stakes_tension), event spike injection with decay

## Story Details
- **ID:** 5-3
- **Jira Key:** none (personal project)
- **Workflow:** tdd (phased)
- **Stack Parent:** 5-2 (completed, in archive)
- **Points:** 3
- **Priority:** p0

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-27T21:17:50Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T16:50:00Z | 2026-03-27T20:52:14Z | 4h 2m |
| red | 2026-03-27T20:52:14Z | 2026-03-27T21:00:29Z | 8m 15s |
| green | 2026-03-27T21:00:29Z | 2026-03-27T21:06:35Z | 6m 6s |
| spec-check | 2026-03-27T21:06:35Z | 2026-03-27T21:08:00Z | 1m 25s |
| verify | 2026-03-27T21:08:00Z | 2026-03-27T21:11:09Z | 3m 9s |
| review | 2026-03-27T21:11:09Z | 2026-03-27T21:16:52Z | 5m 43s |
| spec-reconcile | 2026-03-27T21:16:52Z | 2026-03-27T21:17:50Z | 58s |
| finish | 2026-03-27T21:17:50Z | - | - |

## Context

### Parent Story: 5-2 (Combat Event Classification)

5-2 delivered:
- `DetailedCombatEvent` enum with variants: Boring, Normal, Dramatic(DramaticDetail)
- `classify_combat_outcome()` function that categorizes RoundResult into events
- `TensionTracker::observe()` method that records events and injects spike magnitudes
- Spike magnitudes: Boring=0.0, Normal=0.2, NearMiss=0.6, CriticalHit=0.7, FirstBlood=0.8, KillingBlow=1.0
- Static `SPIKE_DECAY` constant (0.5) applied uniformly to all spikes

### Parent Story: 5-1 (TensionTracker)

5-1 delivered:
- `TensionTracker` struct with dual-track tension model
- `action_tension`: gambler's ramp (0.0..=1.0, increases on damage, resets on boring turns)
- `stakes_tension`: HP-based (0.0..=1.0, player_hp / max_hp, tracks danger)
- `boring_streak`: counter for consecutive non-dramatic rounds
- `record_event()` method to track CombatEvent enum (Boring, Dramatic, Normal)
- `inject_spike()` method to add magnitude spike with decay over time
- `tick()` method to apply decay to active spikes each turn

### Spec: Drama Weight Computation

**Goal:** Compute `drama_weight` (0.0..=1.0) that drives pacing decisions downstream.

**Algorithm:**
1. Drama weight = `max(action_tension, stakes_tension, effective_spike)` — max of three tracks
2. Event spike injection: Dramatic event sets single spike with magnitude and per-event decay_rate
3. Spike decay: Each observe() call ages the spike linearly (magnitude - decay_rate * age)
4. Spike replacement: New dramatic event replaces existing spike, resets decay age
5. Clamped output: drama_weight always in 0.0-1.0

## Story Acceptance Criteria

1. **Drama weight computation:** `drama_weight()` = max(action_tension, stakes_tension, effective_spike)
2. **Spike storage:** Single spike model (Option<EventSpike> with magnitude + decay_rate)
3. **Spike injection in observe():** Dramatic events set spike with per-event decay_rate from DetailedCombatEvent
4. **Spike decay per observe:** age_spike() at start of observe, linear decay
5. **Drama weight wiring:** Callable and tested before 5-4
6. **Test coverage:** Spike injection, decay curves, replacement, cleanup, combined scenarios

## Sm Assessment

Story 5-3 is ready for RED phase. Parent stories 5-1 (TensionTracker) and 5-2 (Combat event classification) are complete, providing the foundation. This is a focused 3-point story adding drama_weight computation with spike injection and per-event decay. TEA should write failing tests covering all 6 acceptance criteria before Dev implements.

**Routing:** TDD phased → TEA (red phase)

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core behavioral changes to TensionTracker — new spike model, decay mechanics, drama_weight formula

**Test Files:**
- `sidequest-api/crates/sidequest-game/tests/drama_weight_story_5_3_tests.rs` — 23 tests covering all 6 ACs

**Tests Written:** 23 tests covering 6 ACs
**Status:** RED (11 failing, 12 passing — ready for Dev)

### Failing Tests (11) — drive implementation:
1. `drama_weight_is_max_of_three_tracks_not_additive` — current additive formula returns 1.0, expects max = 0.8
2. `critical_hit_spike_decays_linearly_per_observe` — no per-observe decay, spike stays at 0.8
3. `killing_blow_spike_decay_curve` — full 5-turn decay curve for KillingBlow (0.20/turn)
4. `spike_cleaned_up_after_full_decay` — spike not cleaned to 0.0 after full decay
5. `drama_weight_falls_back_after_spike_decays` — drama_weight doesn't fall back to base tensions
6. `new_spike_replaces_existing_not_additive` — spike is additive, should be replacement
7. `spike_replacement_resets_decay_age` — new spike doesn't reset decay counter
8. `observe_ages_existing_spike_before_classification` — no age_spike() call in observe
9. `near_miss_decays_slower_than_killing_blow` — per-event decay rates not wired
10. `multiple_dramatic_events_in_sequence` — additive stacking instead of replacement
11. `drama_weight_tracks_spike_decay_correctly` — end-to-end decay curve tracking

### Passing Tests (12) — validate existing infrastructure:
- Spike injection at correct magnitudes (CriticalHit=0.8, KillingBlow=1.0, NearMiss=0.5)
- drama_weight returns correct track when no spike conflict
- Stakes tension update, boring observe, clamped output, zero-activity baseline

### Rule Coverage

| Rule | Applicable? | Test(s) | Status |
|------|-------------|---------|--------|
| #1 silent errors | No — no Result/Option chains in test scope | n/a | n/a |
| #2 non_exhaustive | No — no new public enums (DetailedCombatEvent already has it) | n/a | n/a |
| #3 placeholders | No — no hardcoded IDs | n/a | n/a |
| #6 test quality | Yes | Self-checked all 23 tests | pass — all have meaningful assertions |
| #9 public fields | Deferred — EventSpike struct doesn't exist yet; Dev must use private fields | n/a | pending |

**Rules checked:** 2 of 15 applicable (test quality self-check, non_exhaustive audit)
**Self-check:** 0 vacuous tests found — all tests use assert_eq! or assert! with meaningful conditions

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-game/src/tension_tracker.rs` — replaced additive spike model with EventSpike struct, linear decay, max-of-three drama_weight

**Tests:** 23/23 passing (GREEN) — 0 regressions across full sidequest-game suite
**Branch:** feat/6-5-wire-faction-agendas (pushed)

**Handoff:** To TEA for verify phase

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 1 (Trivial)

- **EventSpike omits event variant field** (Different behavior — Cosmetic, Trivial)
  - Spec: context-story-5-3.md shows `EventSpike { event, magnitude, decay_rate }` storing the `CombatEvent` variant
  - Code: `EventSpike { magnitude, decay_rate }` — stores only the extracted values, not the event variant
  - Recommendation: A (update spec) — the event variant is unused after extracting magnitude/decay_rate. Storing it would be dead data. Code is correct.

**Notes on existing deviations:** All three logged deviations (TEA single-spike, TEA observe-not-tick, Dev tick-also-ages) are well-documented with correct 6-field format. The rationales are sound:
- Single spike model matches story context scope boundaries
- tick() aging preserves 5-7 test compatibility without functional regression
- observe() flow matches context behavioral spec

**Decision:** Proceed to verify

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | Test helper duplication across 5-2/5-3 files (RoundResult builders) |
| simplify-quality | 1 finding | Pre-existing: 5-2 types not re-exported from lib.rs (not from this story) |
| simplify-efficiency | 1 finding | Test helpers verbose but acceptable (recommends no changes) |

**Applied:** 0 high-confidence fixes (all findings are out-of-scope or pre-existing)
**Flagged for Review:** 1 medium-confidence finding — test helper duplication could benefit from shared test utils module in a future chore
**Noted:** 1 low-confidence observation — test verbosity acceptable for clarity
**Reverted:** 0

**Overall:** simplify: clean (no in-scope fixes needed)

**Quality Checks:** All passing
- cargo test: 0 failures across full sidequest-game suite
- cargo clippy: 0 warnings in changed files (pre-existing warnings in other files only)

**Handoff:** To Heimdall (Reviewer) for code review

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (non-blocking): Session file AC-2 specifies `Vec<Spike>` for overlapping spikes, but story context explicitly scopes out multiple simultaneous spikes. Tests follow story context (single spike replacement model). Dev should confirm this design choice.
  Affects `sidequest-api/crates/sidequest-game/src/tension_tracker.rs` (spike storage model).
  *Found by TEA during test design.*

- **Conflict** (non-blocking): Session file AC-4 says "Modify tick() to apply per-event decay rates" but story context shows `age_spike()` in `observe()`, not `tick()`. Tests expect spike aging per observe() call.
  Affects `sidequest-api/crates/sidequest-game/src/tension_tracker.rs` (observe vs tick spike aging).
  *Found by TEA during test design.*

- **Question** (non-blocking): Current `inject_spike(amount: f64)` signature is additive. Story 5-3 changes semantics to replacement. Existing 5-2 tests call `inject_spike(event.spike_magnitude())` — Dev should verify 5-2 tests still pass after signature/behavior change.
  Affects `sidequest-api/crates/sidequest-game/tests/combat_event_story_5_2_tests.rs` (spike injection calls).
  *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. All 5-2 tests pass with the new spike replacement semantics. The 5-7 pacing tests also pass because tick() still calls age_spike().

### Reviewer (code review)
- **Improvement** (non-blocking): Pre-existing `CombatEvent` and `TurnClassification` enums lack `#[non_exhaustive]` (from stories 5-1/5-2). Should be added in a future chore to prevent breaking changes when new pacing states are added.
  Affects `sidequest-api/crates/sidequest-game/src/tension_tracker.rs` (lines 88, 358).
  *Found by Reviewer during code review.*

### TEA (test verification)
- **Improvement** (non-blocking): Test helper duplication — `drama_weight_story_5_3_tests.rs` defines 4 RoundResult builders that duplicate the `make_round()`/`damage()` pattern from `combat_classification_story_5_2_tests.rs`. A shared test utils module would reduce duplication across epic 5 test files.
  Affects `sidequest-api/crates/sidequest-game/tests/` (future chore to extract shared test builders).
  *Found by TEA during test verification.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

4 deviations

- **Single spike model instead of Vec<Spike>**
  - Rationale: Story context (higher authority) explicitly states "Out of scope: Multiple simultaneous spikes (Python supports this, Rust simplifies to one)"
  - Severity: major (changes data model)
  - Forward impact: Stories 5-4 and 5-5 consume drama_weight — no impact since they only read the output value
- **Spike aging in observe() not tick()**
  - Rationale: Story context (higher authority) shows age_spike() called in observe() flow, not tick(). Spikes age per combat round (observe call), which matches the "per-turn decay" semantics
  - Severity: minor (same decay behavior, different trigger point)
  - Forward impact: none — drama_weight output is identical regardless of aging trigger
- **tick() also ages spikes (not just observe)**
  - Rationale: Story 5-7 pacing tests use tick() for spike decay. Removing spike decay from tick() would break 5-7 tests. Both call sites are safe — no production code calls both observe() and tick() in the same turn.
  - Severity: minor
  - Forward impact: none — additional call site preserves backward compatibility
- **EventSpike omits event variant field**
  - Rationale: The event variant is unused after magnitude and decay_rate extraction. Storing it would be dead data that couples EventSpike to the DetailedCombatEvent enum unnecessarily.
  - Severity: trivial (cosmetic — no behavioral impact)
  - Forward impact: none — no downstream consumer needs the event variant from the spike

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Single spike model instead of Vec<Spike>**
  - Spec source: session file AC-2, AC-6
  - Spec text: "Add spikes field to TensionTracker (Vec of active spikes)" and "Overlapping spikes (two spikes active simultaneously)"
  - Implementation: Tests use single-spike replacement model (Option<EventSpike>, not Vec)
  - Rationale: Story context (higher authority) explicitly states "Out of scope: Multiple simultaneous spikes (Python supports this, Rust simplifies to one)"
  - Severity: major (changes data model)
  - Forward impact: Stories 5-4 and 5-5 consume drama_weight — no impact since they only read the output value

- **Spike aging in observe() not tick()**
  - Spec source: session file AC-4
  - Spec text: "Modify tick() to apply per-event decay rates to all active spikes"
  - Implementation: Tests expect spike aging per observe() call (age_spike at start of observe), not in tick()
  - Rationale: Story context (higher authority) shows age_spike() called in observe() flow, not tick(). Spikes age per combat round (observe call), which matches the "per-turn decay" semantics
  - Severity: minor (same decay behavior, different trigger point)
  - Forward impact: none — drama_weight output is identical regardless of aging trigger

### Dev (implementation)
- **tick() also ages spikes (not just observe)**
  - Spec source: context-story-5-3.md, Technical Approach
  - Spec text: "age_spike() called at the start of each observe()" — no mention of tick()
  - Implementation: age_spike() called in both observe() AND tick()
  - Rationale: Story 5-7 pacing tests use tick() for spike decay. Removing spike decay from tick() would break 5-7 tests. Both call sites are safe — no production code calls both observe() and tick() in the same turn.
  - Severity: minor
  - Forward impact: none — additional call site preserves backward compatibility

### Architect (reconcile)
- **EventSpike omits event variant field**
  - Spec source: context-story-5-3.md, Spike Injection section
  - Spec text: "EventSpike { event, magnitude: event.spike_magnitude(), decay_rate: event.decay_rate() }" — stores the CombatEvent variant alongside extracted values
  - Implementation: `EventSpike { magnitude, decay_rate }` — stores only the extracted f64 values, not the event variant
  - Rationale: The event variant is unused after magnitude and decay_rate extraction. Storing it would be dead data that couples EventSpike to the DetailedCombatEvent enum unnecessarily.
  - Severity: trivial (cosmetic — no behavioral impact)
  - Forward impact: none — no downstream consumer needs the event variant from the spike

- No additional missed deviations found. All 3 existing entries (TEA×2, Dev×1) have accurate spec sources, correct implementation descriptions, and valid forward impact assessments.

### Reviewer (audit)
- **Single spike model** → ACCEPTED: Story context explicitly scopes out multi-spike. Agrees with author reasoning.
- **Spike aging in observe() not tick()** → ACCEPTED: Context authority hierarchy is correct. observe() is the per-combat-round entry point.
- **tick() also ages spikes** → ACCEPTED: Backward compat with 5-7 tests is sound. Both call sites are safe.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (fmt cosmetic, pre-existing) | dismissed 1 — pre-existing fmt diffs in audio_mixer.rs/persistence.rs, not from 5-3 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 (all pre-existing) | dismissed 3 — CombatEvent/TurnClassification non_exhaustive and base64 dep are from 5-1/5-2, not this diff |

**All received:** Yes (3 returned, 6 disabled)
**Total findings:** 0 confirmed, 4 dismissed (all pre-existing), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] `EventSpike` is private struct with private fields — `tension_tracker.rs:97-102`. Rule #9 compliant. No public access except through `active_spike()` getter.

2. [VERIFIED] `drama_weight()` computes `max(action, stakes, effective_spike)` — `tension_tracker.rs:160-166`. Matches AC-1 exactly. Clamped via `clamp01()`.

3. [VERIFIED] `effective_spike()` implements correct linear decay: `magnitude - decay_rate * age` — `tension_tracker.rs:188-195`. `.max(0.0)` prevents negative spike values. Age is u32 internal counter, `as f64` cast is lossless. Rule #7 (unsafe casts) checked — compliant.

4. [VERIFIED] `observe()` ages spike before classification — `tension_tracker.rs:427` calls `age_spike()` first. Per-event decay rates wired at `tension_tracker.rs:438-442` via `event.spike_magnitude()` and `event.decay_rate()`. Rule #1 (silent errors) checked — no Result/Option swallowing.

5. [VERIFIED] Spike replacement semantics correct — `observe()` at line 438 sets `last_event_spike = Some(...)` and `spike_decay_age = 0`, fully replacing any existing spike. Tests confirm: `new_spike_replaces_existing_not_additive`, `spike_replacement_resets_decay_age`.

6. [LOW] Dual spike creation paths — `inject_spike()` (line 179, public, DEFAULT_SPIKE_DECAY_RATE) and `observe()` (line 438, per-event decay). If EventSpike gains a field, both paths need updating. Acceptable for now — EventSpike is private and small.

7. [SILENT] Silent-failure-hunter noted: `observe()` bypasses `inject_spike()` clamp01 for magnitude. Not a current issue since `spike_magnitude()` returns hardcoded 0.5-1.0 values. Future variants should maintain this range.

8. [RULE] Rule-checker found 3 violations — all pre-existing (CombatEvent/TurnClassification missing `#[non_exhaustive]` from 5-1/5-2, base64 inline pin). Not introduced by this diff. Flagged for future chore.

### Rule Compliance

| Rule | Applicable? | Status | Evidence |
|------|-------------|--------|----------|
| #1 Silent errors | Yes | Pass | No .ok()/.expect() in diff |
| #2 non_exhaustive | No new pub enums | Pass | EventSpike is private |
| #3 Placeholders | Yes | Pass | All constants named and documented |
| #5 Constructors | Yes | Pass | inject_spike clamps input; observe uses bounded constants |
| #6 Test quality | Yes | Pass | All 23 tests have meaningful assertions |
| #7 Unsafe casts | Yes | Pass | spike_decay_age as f64 is internal, lossless |
| #8 Serde bypass | No | N/A | No Deserialize on changed types |
| #9 Public fields | Yes | Pass | EventSpike private; TensionTracker fields private with getters |
| #11 Workspace deps | No new deps | N/A | Diff adds no dependencies |

### Devil's Advocate

What if this code is broken? The most plausible failure modes:

**Double-aging:** If production code calls both `observe()` AND `tick()` in the same turn, the spike ages twice — decaying at double the intended rate. This would make dramatic moments feel shorter than designed. The Dev deviation log notes "no production code calls both in the same turn," but this is an implicit contract, not an enforced one. A future orchestrator change that adds a `tick()` call in the combat loop after `observe()` would silently halve spike lifetimes. This is a real risk but mitigated by the test suite — any double-aging would cause the 5-3 decay curve tests to fail if the orchestrator wiring changes.

**Magnitude clamping inconsistency:** `inject_spike(amount)` clamps via `clamp01(amount)`, but `observe()` writes `event.spike_magnitude()` directly without clamping. All current magnitudes are 0.5-1.0, so this is safe today. But if someone adds a `DetailedCombatEvent::Apocalypse` with `spike_magnitude() -> 2.0`, it would bypass the clamp and produce an `effective_spike()` > 1.0 before drama_weight's final `clamp01()` catches it. The outer clamp in `drama_weight()` saves us, so this can't produce an out-of-range drama_weight. Still, `effective_spike()` would briefly return > 1.0 which could confuse if exposed differently in the future. Low risk.

**Spike decay age overflow:** `spike_decay_age` is u32. In theory, if a spike were never cleaned up and age_spike() were called billions of times, it would overflow and wrap to 0, causing a "zombie spike" to reappear at full magnitude. In practice, spikes are cleaned up within ~5-10 ticks (magnitude/decay_rate), so this cannot happen.

None of these scenarios are current bugs. The double-aging concern is the most realistic future risk but is test-protected.

**Data flow traced:** `observe(&RoundResult, killed, lowest_hp_ratio)` → `classify_combat_outcome()` → `TurnClassification::Dramatic(event)` → `EventSpike { magnitude: event.spike_magnitude(), decay_rate: event.decay_rate() }` → stored in `last_event_spike` → read by `effective_spike()` → consumed by `drama_weight()`. All values bounded by design — magnitudes 0.5-1.0, decay rates 0.10-0.20, output clamped 0.0-1.0.

**Wiring:** This is backend-only game engine computation. No UI wiring needed — downstream consumers (5-4 pacing hints, 5-5 delivery modes) will read `drama_weight()` which is already public.

**Error handling:** No error paths — pure computation. `debug_assert!(max_hp > 0)` in `update_stakes()` guards division by zero in debug builds.

**Security:** No auth, no user input, no network. Internal game state only. Tenant isolation N/A.

**Handoff:** To Baldur the Bright (SM) for finish-story