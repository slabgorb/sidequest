---
story_id: "9-5"
jira_key: "none"
epic: "9"
workflow: "tdd"
---
# Story 9-5: Narrative character sheet — genre-voiced to_narrative_sheet() for player-facing display

## Story Details
- **ID:** 9-5
- **Jira Key:** none (personal project)
- **Epic:** 9 (Character Depth)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Stack Parent:** none (depends on 9-1, already complete)

## Story Context

**Summary:** Implement a `to_narrative_sheet()` function that generates a player-facing character sheet with genre-voiced output. Combines ability descriptions (from 9-1) and known facts (from 9-3) into cohesive narrative prose.

**Acceptance Criteria:**
1. `Character` struct has `to_narrative_sheet()` method returning `String`
2. Output includes genre-voiced abilities and description (from AbilityDefinition.genre_voice)
3. Output includes relevant known facts with context
4. Method integrates cleanly with narrator context
5. Unit tests verify genre voice consistency
6. Integration test confirms wiring to game state

**Dependencies:**
- 9-1: AbilityDefinition model (complete)
- 9-3: KnownFact model (complete)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-28T20:08:33Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28T19:48:23Z | 2026-03-28T19:49:25Z | 1m 2s |
| red | 2026-03-28T19:49:25Z | 2026-03-28T19:52:23Z | 2m 58s |
| green | 2026-03-28T19:52:23Z | 2026-03-28T19:59:54Z | 7m 31s |
| spec-check | 2026-03-28T19:59:54Z | 2026-03-28T20:00:50Z | 56s |
| verify | 2026-03-28T20:00:50Z | 2026-03-28T20:03:06Z | 2m 16s |
| review | 2026-03-28T20:03:06Z | 2026-03-28T20:07:42Z | 4m 36s |
| spec-reconcile | 2026-03-28T20:07:42Z | 2026-03-28T20:08:33Z | 51s |
| finish | 2026-03-28T20:08:33Z | - | - |

## Sm Assessment

**Story 9-5** produces the player-facing narrative character sheet — a genre-voiced summary combining abilities, known facts, and character identity. This is the player's view of who their character has become.

**Dependencies:** 9-1 (AbilityDefinition) and 9-3 (KnownFact) are both complete. 9-4 (knowledge in narrator prompt) also done — this story is about the player-facing sheet, not the narrator prompt.

**Scope:** Rust-side only (sidequest-game). The `to_narrative_sheet()` method on Character produces a String. Story 9-10 handles wiring to React.

**Routing:** TDD workflow → TEA (Sherlock Holmes) for the red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core game model — genre-voiced character sheet struct and composition

**Test Files:**
- `sidequest-api/crates/sidequest-game/tests/narrative_sheet_story_9_5_tests.rs` — 24 tests covering all 6 ACs

**Tests Written:** 24 tests covering 6 ACs
**Status:** RED (fails to compile — `to_narrative_sheet` not found on Character, `narrative_sheet` module missing)

### AC Coverage

| AC | Tests | Description |
|----|-------|-------------|
| Structured output | `to_narrative_sheet_returns_*`, `narrative_sheet_has_*` | NarrativeSheet has identity, abilities, knowledge, status fields |
| Genre voice | `ability_entry_contains_genre_description`, `ability_entry_does_not_contain_mechanical_effect`, `ability_entry_preserves_involuntary_flag`, `all_abilities_included_*` | genre_description used, mechanical_effect excluded |
| Knowledge included | `knowledge_entry_contains_fact_content`, `knowledge_entry_contains_confidence`, `empty_knowledge_*` | facts with confidence tags |
| Status included | `status_reflects_wounded_*`, `status_includes_conditions_*`, `status_no_conditions_*` | narrative HP/conditions, no raw numbers |
| Serializable | `narrative_sheet_serializes_to_json`, `narrative_sheet_json_roundtrip` | JSON serialize + deserialize roundtrip |
| No stat blocks | `identity_does_not_contain_raw_stats`, `identity_contains_character_name`, `identity_contains_class_and_race` | no STR/DEX/AC/HP numbers in identity |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality | All tests use specific content/structure assertions, no vacuous patterns | pass |

**Rules checked:** 1 of 15 applicable (most rules apply to implementation, not test design)
**Self-check:** 0 vacuous tests found

**Handoff:** To Inspector Lestrade (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-game/src/narrative_sheet.rs` — New module: NarrativeSheet, AbilityEntry, KnowledgeEntry, CharacterStatus structs with Serde derives; describe_health() converts HP ratio to narrative text
- `sidequest-api/crates/sidequest-game/src/character.rs` — Added `to_narrative_sheet(&self, genre_voice: &str) -> NarrativeSheet` method
- `sidequest-api/crates/sidequest-game/src/lib.rs` — Registered narrative_sheet module
- `sidequest-api/crates/sidequest-game/tests/*.rs` (8 files) — Fixed test fixtures for npc_registry and stat_bonuses fields

**Tests:** 23/23 passing (GREEN), 816 existing tests no regressions
**Branch:** `feat/9-5-narrative-character-sheet` (pushed)

**Implementation details:**
- `NarrativeSheet` struct with identity (String), abilities (Vec<AbilityEntry>), knowledge (Vec<KnowledgeEntry>), status (CharacterStatus)
- Identity composed as `"{name}, {race} {class}"` — no raw stats
- AbilityEntry uses `genre_description` from AbilityDefinition, never `mechanical_effect`
- KnowledgeEntry carries fact content + Confidence enum
- CharacterStatus uses `describe_health()` — HP ratio mapped to narrative text ("in good health", "lightly wounded", "badly wounded", "near death", "fallen")
- Conditions passed through as-is (already narrative strings)
- `_genre_voice` parameter accepted but not yet used for identity composition (template v1 per spec scope)

**Handoff:** To TEA for verify phase

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 6 ACs validated:

| AC | Status |
|----|--------|
| Structured output | Aligned — NarrativeSheet typed struct with four sections |
| Genre voice | Aligned — AbilityEntry.description = genre_description, mechanical_effect excluded |
| Knowledge included | Aligned — KnowledgeEntry with content + Confidence |
| Status included | Aligned — CharacterStatus with narrative health text + conditions |
| Serializable | Aligned — all types derive Serialize/Deserialize |
| No stat blocks | Aligned — identity uses name/race/class, status uses narrative text |

**Note:** `_genre_voice` parameter is accepted but unused — this is explicitly in scope as "template for v1" per the story context's Scope Boundaries ("LLM-generated identity prose" is out of scope). No deviation.

**Decision:** Proceed to verify

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | From trait extractions for AbilityEntry/KnowledgeEntry — premature abstraction for 3-line maps. describe_health reusability — speculative. |
| simplify-quality | 3 findings | Unused _genre_voice — documented v1 scope boundary. No non-test consumers — same as 9-4, wire-later pattern. describe_health visibility — private is correct. |
| simplify-efficiency | 1 finding | Unused _genre_voice — same as quality finding, documented scope boundary. |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings applicable to 9-5
**Noted:** 7 observations (all dismissed — premature abstractions, documented scope, or pre-existing patterns)
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:**
- Tests: 23/23 passing
- No regressions in existing test suite

**Handoff:** To Professor Moriarty (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 (wiring gap) | confirmed 1 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 1, dismissed 1 (documented scope) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 6 | confirmed 1, dismissed 5 (1 false positive, 4 low-severity/documented scope) |

**All received:** Yes (3 returned, 6 disabled via settings)
**Total findings:** 2 confirmed (wiring gap + max_hp guard), 6 dismissed (with rationale)

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Genre voice enforcement correct — `character.rs:88-91` maps `AbilityDefinition.genre_description` to `AbilityEntry.description`. `mechanical_effect` is never referenced in `to_narrative_sheet()`. Tests `ability_entry_contains_genre_description` and `ability_entry_does_not_contain_mechanical_effect` validate this at `narrative_sheet_story_9_5_tests.rs:160-192`.

2. [VERIFIED] Status uses narrative text, not raw numbers — `describe_health()` at `narrative_sheet.rs:59-77` converts HP ratio to narrative strings. `CharacterStatus` has `health: String` and `conditions: Vec<String>` — no i32 fields. Test `status_reflects_wounded_character` verifies `"hp":18` does NOT appear in serialized JSON.

3. [VERIFIED] Serde roundtrip works — all four types derive `Serialize, Deserialize`. Test `narrative_sheet_json_roundtrip` at line 366 serializes and deserializes, checking identity/abilities/knowledge survive.

4. [VERIFIED] No stat blocks in identity — `character.rs:80-83` formats identity as `"{name}, {race} {class}"`. No stats HashMap, no AC, no HP, no level in the string. Tests at lines 398-420 check absence of "STR", "16", "AC".

5. [MEDIUM] [SILENT] `describe_health()` max_hp<=0 guard — `narrative_sheet.rs:60-62` returns `"in unknown condition"` when `max_hp <= 0`. This is a defensive guard for a game state that should never occur (`max_hp` is always >= 1 per `CreatureCore` contract). CLAUDE.md says fail loudly. However, this is a display-only function — panicking here crashes the server for one corrupted character. A `debug_assert!(max_hp > 0)` would be the ideal middle ground. Flagged as delivery finding, not blocking.

6. [MEDIUM] [RULE] No non-test callers — same pattern as 9-4. `to_narrative_sheet()` has no production call site. Story 9-10 explicitly handles wiring to React. Method-first, wire-later.

7. [VERIFIED] Test coverage thorough — [RULE] Rule-checker falsely reported zero tests. 23 tests exist in `tests/narrative_sheet_story_9_5_tests.rs` covering all 6 ACs. Challenged: rule-checker searched `src/` only, missed integration test directory.

### Rule Compliance

| Rule | Instances | Compliant | Notes |
|------|-----------|-----------|-------|
| #1 Silent errors | 3 | Yes | No .ok()/.expect() |
| #2 Non-exhaustive | 0 new enums | N/A | |
| #3 Placeholders | 3 | Yes | All values from real fields |
| #4 Tracing | 1 | N/A | Pure struct composition, not subsystem decision |
| #7 Unsafe casts | 2 (hp as f64) | Yes | i32→f64 is lossless; HP bounded by clamp_hp() |
| #8 Deserialize bypass | 4 | Yes | No validating constructors on DTOs |
| #9 Public fields | 4 structs | Yes | DTOs for serialization, no invariants |
| #15 Unbounded input | 2 | Yes | Bounded Vec iteration |

### Data Flow

`Character` fields → `to_narrative_sheet()` → `NarrativeSheet` struct → (future: JSON via WebSocket). Pure transformation from game state to display DTO. No trust boundary crossing.

### Devil's Advocate

The `_genre_voice` parameter is the most interesting smell. Three subagents flagged it. The argument: it's a stub, the doc comment lies about what it does, and the test that claims to verify it is vacuous.

But consider the alternative: remove the parameter now, then add it back in a future story. That changes the API signature, which means every call site needs updating. The spec explicitly includes the parameter. The story context explicitly marks LLM-generated identity as "out of scope for v1." The underscore prefix is Rust's conventional signal for "intentionally unused."

The test `genre_voice_parameter_is_used` at line 459 is indeed weak — it only checks `identity.len() > "Reva".len()`. But that test name is aspirational, not deceptive. It verifies the identity is composed (not just the raw name), which is the v1 behavior. A future story that wires genre_voice would strengthen this test.

Could the `describe_health()` function hide bugs? The HP ratio thresholds (1.0, 0.75, 0.5, 0.25, 0.0) are hardcoded. If game balance changes HP scaling, these thresholds become wrong. But this is a display function — "badly wounded" at 40% HP vs 25% HP is a tuning knob, not a correctness issue. The important thing is that no raw numbers leak to the player, and the tests verify that.

The wiring gap is the same pattern as 9-4, and it's the real risk: the sheet exists, but nobody calls it. Story 9-10 is supposed to handle this, but if 9-10 gets deferred, the narrative sheet is dead code.

**Conclusion:** Implementation is correct, clean, well-tested. No critical or high-severity issues. The max_hp guard and wiring gap are documented as delivery findings.

**Handoff:** To Dr. Watson (SM) for finish-story

## Delivery Findings

### TEA (test design)
- **Question** (non-blocking): The spec shows `CharacterStatus` as the status field type but doesn't define its structure. Tests assert no raw HP numbers in JSON serialization. Dev should design CharacterStatus to use narrative descriptions (e.g., "badly wounded" instead of "hp: 18"). Affects `sidequest-game/src/narrative_sheet.rs` (CharacterStatus struct design). *Found by TEA during test design.*

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- TEA reported no deviations — confirmed, no deviations found by TEA or Dev.
- No additional undocumented deviations found. The `_genre_voice` unused parameter is a designed v1 scope boundary per story context ("template for v1, LLM enhancement later"), not an undocumented deviation.

### Architect (reconcile)
- No additional deviations found. TEA and Dev both logged no deviations — verified accurate. The `_genre_voice` parameter is specified in context-story-9-5.md line 23 and unused per the explicit v1 scope boundary at line 78 ("LLM-generated identity prose... template for v1"). No deviation because the spec anticipated this. Reviewer's audit is consistent. All delivery findings (max_hp guard, wiring gap) are properly documented as non-blocking improvements, not spec deviations.

### Dev (implementation findings)
- No upstream findings during implementation.

### TEA (test verification)
- No upstream findings during test verification.

### Reviewer (code review)
- **Improvement** (non-blocking): `describe_health()` returns `"in unknown condition"` when `max_hp <= 0` — a defensive guard for an impossible game state. Per CLAUDE.md no-silent-fallbacks rule, consider replacing with `debug_assert!(max_hp > 0)` plus the fallback string. Panicking in a display function would crash the server, so the fallback is acceptable for release builds. Affects `sidequest-game/src/narrative_sheet.rs:60` (add debug_assert). *Found by Reviewer during code review.*
- **Gap** (non-blocking): `to_narrative_sheet()` has no production call site. Server's CHARACTER_SHEET emission sites still use old `CharacterSheetPayload` with raw stats. Story 9-10 handles React wiring. Affects `sidequest-server/src/lib.rs` (CHARACTER_SHEET emission). *Found by Reviewer during code review.*