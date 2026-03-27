---
story_id: "5-2"
jira_key: "none"
epic: "5"
workflow: "tdd"
---
# Story 5-2: Combat Event Classification — Categorize Combat Outcomes as Boring/Dramatic, Track boring_streak

## Story Details
- **ID:** 5-2
- **Jira Key:** none (personal project)
- **Workflow:** tdd (phased)
- **Stack Parent:** 5-1 (completed, in archive)
- **Points:** 3
- **Priority:** p0

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-27T14:20:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T13:29:21Z | 2026-03-27T13:30:35Z | 1m 14s |
| red | 2026-03-27T13:30:35Z | 2026-03-27T13:53:27Z | 22m 52s |
| green | 2026-03-27T13:53:27Z | 2026-03-27T14:06:38Z | 13m 11s |
| review | 2026-03-27T14:06:38Z | 2026-03-27T14:20:32Z | 13m 54s |
| finish | 2026-03-27T14:20:32Z | - | - |

## Tea Assessment

**Tests Required:** Yes
**Reason:** Core pacing engine — combat event classification drives the gambler's ramp

**Test Files:**
- `crates/sidequest-game/tests/combat_event_story_5_2_tests.rs` — 33 tests

**Tests Written:** 33 tests covering event types, spike data, classification, observe, edge cases

**Status:** RED (failing — compilation errors for missing types/methods)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | DetailedCombatEvent Copy+Eq check | failing |
| #6 test quality | Self-check: all 33 tests have meaningful assertions | pass |
| #9 public fields | spike_magnitude()/decay_rate() via methods, not fields | failing |

**Rules checked:** 3 of 15 applicable
**Self-check:** 0 vacuous tests found

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | clippy pre-existing, fmt drift | dismissed (not this story) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 high, 1 medium | deferred 2 (decay_rate 5-3, NearMiss doc), confirmed 1 as LOW (FirstBlood misuse) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 findings | confirmed 1 LOW (weak test), dismissed 2 (magic numbers from epic spec, non_exhaustive on 3-variant enum) |

**All received:** Yes (3 returned, 6 disabled)
**Total findings:** 2 confirmed (LOW), 2 deferred, 3 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** RoundResult (damage_events + effects_applied) → classify_combat_outcome() → TurnClassification → TensionTracker::observe() → record_event(CombatEvent) + inject_spike(magnitude). Pure in-memory game logic, no I/O, no error paths.

**[EDGE] Observations:**
1. [VERIFIED] DetailedCombatEvent has #[non_exhaustive] at tension_tracker.rs:184 — rule #2 compliant.
2. [VERIFIED] All 6 spike magnitudes match epic context spec exactly — tests pin each value with f64::EPSILON.
3. [VERIFIED] observe() bridges detailed→coarse classification correctly: Boring→record_event(Boring), Dramatic→record_event(Dramatic)+inject_spike, Normal→record_event(Normal).
4. [VERIFIED] Priority ordering in classify_combat_outcome: kill(KillingBlow) → low_hp(NearMiss) → high_damage(CriticalHit) → effects(FirstBlood) → normal → boring. Tests verify kill beats damage and kill beats effects.
5. [VERIFIED] Negative damage clamped via .max(0) at tension_tracker.rs:261 — healing doesn't count as damage.

**[SILENT] decay_rate() defined but not wired into tick().** The current SPIKE_DECAY constant (0.5) applies uniformly regardless of event type. Per-event decay is infrastructure for story 5-3. Not a bug — it's planned scope.
**[TEST] 38/38 GREEN. One weak assertion: `classify_new_effects_as_dramatic` uses `matches!` instead of `assert_eq!` — LOW.
**[DOC] Code is well-documented with priority ordering in doc comment.
**[TYPE] DetailedCombatEvent: Copy+Eq+non_exhaustive. TurnClassification: Copy+Eq (missing non_exhaustive — LOW, 3-variant enum with Dramatic carrying data).
**[SEC] Pure game logic, no user input, no I/O. N/A.
**[SIMPLE] Minimal implementation — one function, one method, two enums. No over-engineering.
**[RULE] #2 ✓ (DetailedCombatEvent), #3 values from epic spec, #6 one weak test, #9 N/A (no new structs).

### Devil's Advocate

This is a small, focused story that delivers exactly what it promises: combat event classification with spike data. What could go wrong? The DeathSave and LastStanding variants exist but are currently unreachable from classify_combat_outcome — the function lacks encounter-level context to detect them. A player character who drops to 1 HP and survives gets classified as NearMiss (if HP ratio is provided) or Normal (if not), never DeathSave. The "last standing" condition requires knowing how many combatants remain, which isn't in the function signature. These are valid future events that need richer context from the orchestrator — but right now they're dead enum variants. The FirstBlood variant is also misused — any status effect triggers it, not just the first damage. These are design gaps that story 5-3 or a follow-up should address when wiring the classification into the orchestrator. They don't break anything now because the spike magnitudes are close enough that the pacing effect is similar whether you get a 0.6 (FirstBlood) or a 0.7 (DeathSave) spike. The gambler's ramp and boring_streak work correctly regardless.

### Rule Compliance

| Rule | Instances | Status |
|------|-----------|--------|
| #2 non_exhaustive | DetailedCombatEvent | PASS |
| #2 non_exhaustive | TurnClassification | NOTE — missing, LOW |
| #3 magic numbers | spike/decay values | NOTE — from epic spec, pinned by tests |
| #6 test quality | classify_new_effects_as_dramatic | NOTE — matches! instead of assert_eq!, LOW |

**Handoff:** To Baldur the Bright (SM) for finish-story

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/tension_tracker.rs` — DetailedCombatEvent enum, TurnClassification enum, classify_combat_outcome(), TensionTracker::observe()

**Tests:** 38/38 passing (GREEN), all existing sidequest-game tests pass
**Branch:** feat/5-2-combat-event-classification (pushed)

**Handoff:** To review

## Sm Assessment

Story 5-2 ready for TDD red phase. Prerequisite 5-1 (TensionTracker) is done. Work lives in sidequest-game crate (tension_tracker module). Branch `feat/5-2-combat-event-classification` created in sidequest-api. No Jira (personal project). No blockers.

**Routing:** TEA (Tyr One-Handed) for red phase — write failing tests for CombatEvent classification, boring_streak tracking, and TurnClassification.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): classify_combat_outcome uses FirstBlood for any effects-applied round, not just the first damage in an encounter. Needs encounter context (is_first_blood flag) to distinguish. Affects `crates/sidequest-game/src/tension_tracker.rs` (classify_combat_outcome). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): decay_rate() on DetailedCombatEvent is defined but never called — current spike decay uses flat SPIKE_DECAY constant. Story 5-3 should wire per-event decay rates. Affects `crates/sidequest-game/src/tension_tracker.rs` (tick method). *Found by Reviewer during code review.*

### TEA (test design)
- No upstream findings during test design.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No deviations were logged by TEA or Dev. No undocumented deviations found in code review.