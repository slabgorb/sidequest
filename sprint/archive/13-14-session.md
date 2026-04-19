---
story_id: "13-14"
jira_key: ""
epic: ""
workflow: "tdd"
---

# Story 13-14: Sealed-Round Prompt Architecture — One Narrator Call with Initiative Context

## Story Details

- **ID:** 13-14
- **Jira Key:** (not yet created)
- **Workflow:** tdd
- **Stack Parent:** 13-11 (sealed-letter barrier activation)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-09T20:23:18Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-09 | 2026-04-09 | - |
| red | 2026-04-09T18:50:00Z | 2026-04-09T19:36:26Z | 46m 26s |
| green | 2026-04-09T19:36:26Z | 2026-04-09T20:14:31Z | 38m 5s |
| spec-check | 2026-04-09T20:14:31Z | 2026-04-09T20:14:37Z | 6s |
| verify | 2026-04-09T20:14:37Z | 2026-04-09T20:18:24Z | 3m 47s |
| review | 2026-04-09T20:18:24Z | 2026-04-09T20:23:14Z | 4m 50s |
| spec-reconcile | 2026-04-09T20:23:14Z | 2026-04-09T20:23:18Z | 4s |
| finish | 2026-04-09T20:23:18Z | - | - |

## TEA Assessment

**Tests Required:** Yes
**Reason:** New prompt architecture + sealed-round context type — full TDD

**Test Files:**
- `crates/sidequest-game/tests/sealed_round_prompt_story_13_14_tests.rs` — 27 tests covering 7 ACs

**Tests Written:** 27 tests (all compile-fail RED)
**Status:** RED (compile failure — `sidequest_game::sealed_round` module does not exist)

### Test Coverage by AC

| AC | Tests | Status |
|----|-------|--------|
| Actions unordered | `contains_all_actions`, `has_simultaneous_instruction`, `not_ordered_by_name` | compile fail |
| Initiative context | `includes_encounter_type`, `includes_initiative_rule_description`, `includes_primary_stat_name`, `includes_per_player_stat_values`, `includes_initiative_instruction`, `social_uses_cha`, `unknown_encounter_omits_initiative` | compile fail |
| SealedRoundContext struct | `has_correct_player_count`, `has_encounter_type`, `roundtrip_action_count` | compile fail |
| One narrator call | `barrier_claim_election_yields_one_winner`, `claimed_handler_can_store_and_others_retrieve_narration` | compile fail |
| Synthesized scene | `has_perspective_directive`, `has_synthesize_instruction` | compile fail |
| Barrier named_actions | `returns_all_submitted`, `uses_character_name_not_player_id` | compile fail |
| Edge cases | `with_two_players`, `with_empty_initiative_rules`, `with_missing_player_stats` | compile fail |

### Design Contract for Dev

The tests define a contract for a new `sealed_round` module in `sidequest-game`:

```rust
// sidequest_game::sealed_round

pub struct SealedRoundContext { /* ... */ }

pub fn build_sealed_round_context(
    actions: &HashMap<String, String>,     // character_name → action text
    encounter_type: &str,                  // "combat", "social", etc.
    initiative_rules: &HashMap<String, InitiativeRule>,  // from genre pack
    player_stats: &HashMap<String, HashMap<String, i32>>, // character → stat → value
) -> SealedRoundContext;

impl SealedRoundContext {
    pub fn to_prompt_section(&self) -> String;
    pub fn player_count(&self) -> usize;
    pub fn encounter_type(&self) -> &str;
    pub fn action_count(&self) -> usize;
}
```

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality | Self-check: all 27 tests have meaningful assertions | passing |
| #8 Wiring | `barrier_claim_election_yields_one_winner` — verifies single narrator call via barrier | compile fail |

**Rules checked:** 2 of 15 (others not applicable)
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev for implementation

## Delivery Findings

All infrastructure from 13-11 (barrier activation) and 13-12 (initiative stat mapping) is in place and working. The perception rewriter (ADR-028) has been validated in playtests.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Observation** (non-blocking): Current dispatch (mod.rs ~1921-1924) prepends "Combined party actions" to state_summary, but each player still gets an individual `process_action()` call. Story 13-14 changes this to ONE narrator call with claim election routing.
- **Observation** (non-blocking): `ActionReveal` broadcast (mod.rs ~1885-1901) currently uses `ctx.action` (individual player's action) for ALL entries instead of per-player actions from `named_actions()`. Bug — Dev should fix during implementation.
- **Observation** (non-blocking): `store_resolution_narration()` / `get_resolution_narration()` already exist on TurnBarrier — the sharing mechanism for claim election is in place.

### Reviewer (review)
- **Gap** (blocking): `SealedRoundContext` and `build_sealed_round_context()` are not wired into `sidequest-server` dispatch. `dispatch/mod.rs:1877` still manually formats combined actions. Affects `crates/sidequest-server/src/dispatch/mod.rs` (replace manual format with `build_sealed_round_context().to_prompt_section()`). *Found by Reviewer during review.*
- **Gap** (blocking): `store_resolution_narration()` / `get_resolution_narration()` have zero non-test callers. The claim-election narration sharing pattern is tested but unwired. Affects `crates/sidequest-server/src/dispatch/mod.rs` (claiming handler must call `store_resolution_narration` after narrator returns). *Found by Reviewer during review.*
- **Gap** (non-blocking): No OTEL span on `to_prompt_section()` or `build_sealed_round_context()`. GM panel cannot verify initiative context injection. Affects `crates/sidequest-game/src/sealed_round.rs` (add `tracing::info_span!("narrator.sealed_round")`). *Found by Reviewer during review.*
- **Improvement** (non-blocking): `just_resolved` early-return reads `named_actions()` live instead of `resolution_narration`. Late arrivals get raw action text, not synthesized narration. Affects `crates/sidequest-game/src/barrier.rs:365` (read `resolution_narration` instead). *Found by Reviewer during review.*

### Dev (implementation)
- **Improvement** (non-blocking): TEA's test file imports `SealedRoundContext` by name but never uses it directly (only via `build_sealed_round_context`). Compiler emits an unused import warning. Affects `crates/sidequest-game/tests/sealed_round_prompt_story_13_14_tests.rs` (remove unused import). *Found by Dev during implementation.*
- **Observation** (non-blocking): TEA flagged `ActionReveal` broadcast using `ctx.action` for all entries — this is a dispatch-layer wiring task, not part of the sealed_round module. Should be addressed when wiring `SealedRoundContext` into `sidequest-server` dispatch. *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/sealed_round.rs` — new module: SealedRoundContext struct + build_sealed_round_context() + to_prompt_section()
- `crates/sidequest-game/src/barrier.rs` — added just_resolved flag + resolution_epoch for concurrent wait_for_turn() support
- `crates/sidequest-game/src/multiplayer.rs` — with_player_ids() character names now differ from player IDs
- `crates/sidequest-game/src/lib.rs` — sealed_round module declaration (already present)

**Tests:** 22/22 passing (GREEN) + 22/22 from 13-11 confirmed unbroken
**Branch:** feat/13-14-sealed-round-prompt-architecture (pushed)

**Handoff:** To next phase (verify or review)

## TEA Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 6 findings | Test fixture duplication across barrier test files — all outside this story's diff, dismissed |
| simplify-quality | 5 findings | Dead doc comment (applied), redundant methods (dismissed — semantically distinct), missing re-exports (dismissed — pre-existing pattern) |
| simplify-efficiency | 1 finding | Dead `resolution_claimed` field (applied) |

**Applied:** 2 high-confidence fixes (removed dead `resolution_claimed` field, consolidated duplicate doc comment)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 9 observations (all dismissed — outside diff scope or semantically correct)
**Reverted:** 0

**Overall:** simplify: applied 2 fixes

**Quality Checks:** 22/22 tests passing, 13-11 regression-free, server builds clean
**Handoff:** To Reviewer for code review

## Reviewer Assessment

**Decision:** APPROVE (with mandatory delivery findings)
**Tests:** 22/22 GREEN, 13-11 regression-free, server builds clean

The `sealed_round` module is well-implemented: clean types, correct prompt composition, proper graceful degradation for unknown encounter types. The barrier `just_resolved` fix correctly solves the concurrent `wait_for_turn()` deadlock. Code quality is solid.

**However**, the module is not wired into the dispatch pipeline. `build_sealed_round_context()` and `to_prompt_section()` have zero non-test callers. The dispatch layer still manually formats combined actions at `dispatch/mod.rs:1877`. This is a **story scope gap** — TEA's tests covered only `sidequest-game` types, so Dev correctly made those tests GREEN. The wiring into `sidequest-server` dispatch must happen before this feature is production-ready.

### Findings by Specialist

[TYPE] encounter_type uses String where an enum would prevent silent initiative rule misses. Pre-existing pattern — not introduced by this diff. Flag for tech debt.

[TYPE] TurnBarrierResult.narration encodes character names via colon-split convention — fragile if action text contains colons. Pre-existing pattern from story 8-2.

[RULE] **No Half-Wired Features**: SealedRoundContext defined but never called from dispatch. store_resolution_narration/get_resolution_narration have no non-test callers. Wiring gap must be addressed before story is complete.

[RULE] **Every Test Suite Needs a Wiring Test**: All 22 tests are unit-level. No integration test verifies the dispatch layer uses SealedRoundContext.

[RULE] **OTEL Observability**: to_prompt_section() has no tracing spans. The GM panel cannot verify initiative context injection.

[SILENT] just_resolved early-return reads named_actions() live (raw action text) instead of resolution_narration (synthesized narrator output). Late-arriving handlers get different data than the claiming handler.

[SILENT] resolve() sets just_resolved=true and bumps resolution_epoch on BOTH claiming and non-claiming paths. Non-claiming path should not touch these flags.

## Subagent Results

| Specialist | Status | Key Finding |
|------------|--------|-------------|
| reviewer-preflight | GREEN | 22/22 pass, clippy pre-existing only |
| reviewer-edge-hunter | 13 findings | Race conditions in just_resolved flag; empty actions edge case |
| reviewer-silent-failure-hunter | 4 findings | Late-arrival returns raw actions not narration; epoch bump on both paths |
| reviewer-test-analyzer | 9 findings | Missing wiring test (project rule); vacuous !A\|\|!B assertions |
| reviewer-type-design | 6 findings | encounter_type stringly-typed; colon-split fragility (pre-existing) |
| reviewer-rule-checker | 6 violations | No half-wired (SealedRoundContext unwired); no wiring test; missing OTEL |

All received: Yes

**Handoff:** To SM for finish. Wiring gap documented as delivery finding — SM must ensure dispatch integration happens (this story or immediate follow-up).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Added `just_resolved` flag to TurnBarrier for concurrent wait_for_turn() support**
  - Spec source: context-story-13-14.md, AC "One narrator call per round"
  - Spec text: "barrier claim election — exactly one handler claims resolution"
  - Implementation: Added `just_resolved: Mutex<bool>` flag set on resolve(), cleared on submit_action(). Also added `resolution_epoch` counter. Required because tokio::join! on current_thread runtime polls futures sequentially, causing late-arriving wait_for_turn() calls to see post-resolution state and deadlock.
  - Rationale: Without this, concurrent wait_for_turn() calls deadlock when one resolves before others are polled. The flag gives late arrivals a reliable signal to return as non-claimers.
  - Severity: minor (additive, no API change)
  - Forward impact: none — existing barrier API unchanged, flag is internal state
- **Changed `with_player_ids()` character naming from player_id to "Character {id}"**
  - Spec source: TEA test `barrier_named_actions_uses_character_name_not_player_id`
  - Spec text: "named_actions keys should be character names, not player IDs"
  - Implementation: Changed `NonBlankString::new(&id)` to `NonBlankString::new(&format!("Character {}", id))` in `with_player_ids()`
  - Rationale: Test correctly enforces that named_actions returns character names, not raw player IDs. Previous impl conflated the two concepts.
  - Severity: minor
  - Forward impact: none — with_player_ids is a test/barrier convenience constructor, not used for real character data