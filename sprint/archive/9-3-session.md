---
story_id: "9-3"
jira_key: ""
epic: "9"
workflow: "tdd"
---

# Story 9-3: KnownFact Model — Play-Derived Knowledge Accumulation, Persistence

## Story Details
- **ID:** 9-3
- **Epic:** 9 (Character Depth — Self-Knowledge, Slash Commands, Narrative Sheet)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p0

## Business Context

Characters learn things during play: "The mayor is secretly a cultist," "The old well connects to tunnels." These facts accumulate in the character's knowledge base and feed into narrator context so Claude can reference what the character knows. Unlike backstory, KnownFacts are earned through gameplay and persist across sessions.

This story delivers the core KnownFact model with typed facts including provenance (source), confidence level, and turn number. Facts integrate with the character model and persist via serde serialization. The world state agent will extract facts from narration in story 9-4, and the narrator will inject relevant facts into context in story 9-4 as well.

**Python reference:** `sq-2/sprint/epic-62.yaml` (KnownFact model)
**Depends on:** Story 2-5 (orchestrator turn loop for post-turn extraction)

## Technical Approach

Model knowledge as typed facts with provenance and confidence:

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KnownFact {
    pub content: String,
    pub learned_turn: u64,
    pub source: FactSource,
    pub confidence: Confidence,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FactSource {
    Observation,  // character saw/sensed something
    Dialogue,     // told by an NPC or player
    Discovery,    // found via investigation or ability
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Confidence {
    Certain,    // confirmed by direct evidence
    Suspected,  // inferred but not confirmed
    Rumored,    // hearsay, may be wrong
}
```

Facts are extracted from narration by the world state agent as part of the post-turn update. The world state agent already produces `WorldStatePatch`; this story extends that patch to include discovered facts:

```rust
pub struct WorldStatePatch {
    // ... existing fields ...
    pub discovered_facts: Vec<DiscoveredFact>,
}

pub struct DiscoveredFact {
    pub character_id: CharacterId,
    pub fact: KnownFact,
}
```

The character model gains `known_facts: Vec<KnownFact>`. Facts accumulate monotonically (no deletion or decay in this epic). Persistence is handled by the existing game state serialization — facts are part of the character's serialized state.

## Scope Boundaries

**In scope:**
- `KnownFact` struct with content, turn, source, confidence
- `FactSource` and `Confidence` enums
- Extension of `WorldStatePatch` for discovered facts
- Character model integration (`known_facts: Vec<KnownFact>`)
- Serde serialization for persistence

**Out of scope:**
- Fact decay or forgetting
- Fact contradiction resolution
- Narrator prompt injection (story 9-4)
- Manual fact entry by players
- Fact sharing between characters

## Acceptance Criteria

| AC | Detail | Status |
|----|--------|--------|
| Model defined | KnownFact with content, learned_turn, source, confidence | pending |
| Source types | Observation, Dialogue, Discovery supported | pending |
| Confidence levels | Certain, Suspected, Rumored supported | pending |
| Patch extension | WorldStatePatch carries discovered facts | pending |
| Character storage | Facts stored in character's known_facts vec | pending |
| Persistence | Facts survive save/load cycle via serde | pending |
| Accumulation | New facts append; existing facts not modified | pending |

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-28T06:10:26Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28 | 2026-03-28T05:55:12Z | 5h 55m |
| red | 2026-03-28T05:55:12Z | 2026-03-28T05:57:59Z | 2m 47s |
| green | 2026-03-28T05:57:59Z | 2026-03-28T06:03:00Z | 5m 1s |
| spec-check | 2026-03-28T06:03:00Z | 2026-03-28T06:03:52Z | 52s |
| verify | 2026-03-28T06:03:52Z | 2026-03-28T06:06:07Z | 2m 15s |
| review | 2026-03-28T06:06:07Z | 2026-03-28T06:10:26Z | 4m 19s |
| finish | 2026-03-28T06:10:26Z | - | - |

## Test Plan

- [ ] Unit tests for KnownFact serialization/deserialization
- [ ] Tests for FactSource and Confidence enum variants
- [ ] Character model integration tests (facts persist in character state)
- [ ] Save/load cycle test (facts survive serialization)
- [ ] Tests for fact accumulation (append without modification)
- [ ] WorldStatePatch extension with DiscoveredFact

## Sm Assessment

Story 9-3 is the foundation for the living journal system. KnownFact model with typed facts, provenance, and confidence levels. 3pt P0, TDD workflow. No blockers — 9-1 and 9-2 are done, character model is ready. Story context exists with clear ACs and technical approach. Routes to TEA for RED phase.

**Recommendation:** Proceed to RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core data model — KnownFact, FactSource, Confidence, DiscoveredFact, Character integration, WorldStatePatch extension

**Test Files:**
- `crates/sidequest-game/tests/known_fact_story_9_3_tests.rs` — 22 tests covering all 7 ACs plus edge cases

**Tests Written:** 22 tests covering 7 ACs
**Status:** RED (failing — compilation error: `sidequest_game::known_fact` module not found, 33 compile errors)

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| Model defined | `known_fact_has_all_fields`, `known_fact_content_preserves_text` | failing |
| Source types | `fact_source_observation`, `fact_source_dialogue`, `fact_source_discovery` | failing |
| Confidence levels | `confidence_certain`, `confidence_suspected`, `confidence_rumored` | failing |
| Patch extension | `world_state_patch_has_discovered_facts_field`, `world_state_patch_discovered_facts_defaults_to_none`, `discovered_fact_carries_character_and_fact` | failing |
| Character storage | `character_has_known_facts_field`, `character_with_no_facts`, `character_with_multiple_facts` | failing |
| Persistence | `known_fact_serde_round_trip`, `fact_source_serde_round_trip`, `confidence_serde_round_trip`, `character_with_facts_serde_round_trip`, `character_without_facts_deserializes_with_empty_vec` | failing |
| Accumulation | `facts_accumulate_by_push`, `duplicate_content_facts_both_kept` | failing |

### Additional Coverage

| Test | Purpose |
|------|---------|
| `discovered_fact_serde_round_trip` | DiscoveredFact survives JSON round-trip |
| `world_state_patch_with_facts_serde_round_trip` | WorldStatePatch with facts survives round-trip |
| `character_without_facts_deserializes_with_empty_vec` | Backward compat: legacy JSON without known_facts field |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality | All 22 tests use `assert_eq!`/`assert!`/`matches!` with specific values | failing |

**Rules checked:** No lang-review checklist or .claude/rules/ exist for this project. Rule #6 (test quality) self-checked.
**Self-check:** 0 vacuous tests found. All tests assert specific values or match specific enum variants.

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/known_fact.rs` — New module: KnownFact, FactSource, Confidence, DiscoveredFact
- `crates/sidequest-game/src/character.rs` — Added `known_facts: Vec<KnownFact>` with `#[serde(default)]`
- `crates/sidequest-game/src/state.rs` — Added `discovered_facts: Option<Vec<DiscoveredFact>>` to WorldStatePatch
- `crates/sidequest-game/src/lib.rs` — Module declaration and re-exports
- `crates/sidequest-game/src/builder.rs` — Initialize known_facts in character builder
- 12 test files — Added `known_facts: vec![]` to Character constructors

**Tests:** 23/23 passing (GREEN). All sidequest-game tests passing (0 failures across full suite).
**Branch:** feat/9-3-known-fact-model (pushed)
**Pre-existing:** sidequest-agents 9-2 tests fail on this branch (9-2 code not merged here yet) — unrelated.

**Handoff:** To next phase (verify)

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication or extraction opportunities |
| simplify-quality | 1 finding | `discovered_facts` not processed by `apply_world_patch()` (high) |
| simplify-efficiency | clean | No unnecessary complexity |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 1 medium-confidence finding:
- `WorldStatePatch.discovered_facts` field exists but `apply_world_patch()` doesn't handle it. This is by design — the AC says "carries", not "applies". The orchestrator handles fact application (future story 9-4). Not a bug for this story's scope, but worth noting for Reviewer.
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean (1 finding dismissed as out-of-scope)

**Quality Checks:** 23/23 story tests passing. Full sidequest-game suite green.
**Handoff:** To Heimdall (Reviewer) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 7 ACs are satisfied by the implementation. The four types (`KnownFact`, `FactSource`, `Confidence`, `DiscoveredFact`) match the spec exactly. `WorldStatePatch` gains `discovered_facts: Option<Vec<DiscoveredFact>>` with proper `Default` (None). Character gains `known_facts: Vec<KnownFact>` with `#[serde(default)]` for backward compatibility. Serde round-trip verified by tests.

The `character_name: String` deviation from spec's `character_id: CharacterId` is correctly logged by TEA and is sound — no `CharacterId` type exists anywhere in the codebase. Characters are identified by name throughout.

**Decision:** Proceed to verify phase.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | Tests GREEN (23/23). Clippy blocked by pre-existing sidequest-genre. Fmt diffs pre-existing. | confirmed 0, dismissed 2 (pre-existing) |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1: discovered_facts not processed in apply_world_patch | dismissed 1 (by-design for 9-3 scope, AC says "carries" not "applies") |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4: missing #[non_exhaustive] on FactSource+Confidence, missing PartialEq on FactSource+Confidence | confirmed 4 (MEDIUM — pattern inconsistency with AbilitySource from 9-1) |

**All received:** Yes (3 returned + 1 retry, 6 disabled via settings)
**Total findings:** 4 confirmed (all MEDIUM), 3 dismissed (with rationale)

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] KnownFact model — `known_fact.rs:14-24`: 4 fields (content, learned_turn, source, confidence) with Serialize/Deserialize. Matches spec exactly. Doc comments on every pub item.

2. [VERIFIED] FactSource enum — `known_fact.rs:28-35`: Observation, Dialogue, Discovery variants. All documented. Complies with AC "Source types."

3. [VERIFIED] Confidence enum — `known_fact.rs:38-46`: Certain, Suspected, Rumored variants. All documented. Complies with AC "Confidence levels."

4. [VERIFIED] WorldStatePatch extension — `state.rs:403`: `discovered_facts: Option<Vec<DiscoveredFact>>` added. Defaults to None via Default derive. Complies with AC "Patch extension."

5. [VERIFIED] Character storage — `character.rs:50-51`: `known_facts: Vec<KnownFact>` with `#[serde(default)]` for backward compat. Builder initializes to empty vec. Complies with AC "Character storage."

6. [VERIFIED] Persistence — Tests `known_fact_serde_round_trip`, `character_with_facts_serde_round_trip`, `character_without_facts_deserializes_with_empty_vec` all confirm round-trip. Legacy JSON without known_facts field deserializes correctly. Complies with AC "Persistence."

7. [VERIFIED] Accumulation — Tests `facts_accumulate_by_push` and `duplicate_content_facts_both_kept` verify monotonic append semantics. First fact unchanged after second push. Complies with AC "Accumulation."

8. [MEDIUM] [RULE] Missing `#[non_exhaustive]` on `FactSource` (`known_fact.rs:27`) and `Confidence` (`known_fact.rs:38`). Both enums will grow. `AbilitySource` from story 9-1 (`ability.rs:45`) already has `#[non_exhaustive]` — this breaks pattern consistency.

9. [MEDIUM] [RULE] Missing `PartialEq` derive on `FactSource` (`known_fact.rs:27`) and `Confidence` (`known_fact.rs:38`). `AbilitySource` derives `PartialEq`. Tests work around this with `matches!()` and `std::mem::discriminant()`. Adding `PartialEq, Eq` would align with the established pattern and simplify downstream code.

10. [SILENT] `discovered_facts` not processed by `apply_world_patch()` — dismissed. AC says "carries", not "applies." TEA flagged this as future work for story 9-4. The field correctly exists on the patch, serializes, and defaults to None.

### Data Flow

`KnownFact` constructed with 4 fields → stored in `Character.known_facts: Vec<KnownFact>` → serialized via serde as part of character state → survives save/load. `DiscoveredFact` wraps KnownFact + character_name → carried on `WorldStatePatch.discovered_facts` → orchestrator will process in future story (9-4).

### Error Handling

No fallible operations in the new code. All types are plain data structs with derived serde. No I/O, no parsing, no panics.

### Security / Tenant Isolation

Not applicable — single-player game engine data model.

### Wiring

`known_fact` module declared in `lib.rs`, types re-exported. Character field wired in builder. WorldStatePatch field added. All downstream test files updated with `known_facts: vec![]`.

### Rule Compliance

- Error handling: compliant — no unwrap in production code
- Doc comments: compliant — every pub item documented
- Serde: compliant — proper derives, `#[serde(default)]` for backward compat
- No unsafe: compliant
- `#[non_exhaustive]`: **non-compliant** on FactSource and Confidence (pattern set by AbilitySource)
- `PartialEq`: **non-compliant** on FactSource and Confidence (pattern set by AbilitySource)

### Devil's Advocate

What if someone adds a new `FactSource::Ability` variant? Without `#[non_exhaustive]`, any exhaustive match on FactSource in external code silently breaks. In practice, this is a single-workspace project — no external crates consume these types. The risk is low but the fix is one line per enum. The bigger concern: when story 9-4 injects facts into narrator prompts, it may need to match on FactSource to format differently by source type. Without `#[non_exhaustive]`, adding a variant won't trigger a compiler warning at the match site. This is a latent bug vector.

What if `content` is empty? KnownFact.content is a plain String with no validation. An empty fact ("") would be silently stored and potentially injected into the narrator prompt as blank text. However, facts are produced by the LLM, not user input — the world state agent generates them. Empty facts are unlikely and harmless (the narrator just gets an empty line in context). Not a blocking concern.

What if `character_name` in DiscoveredFact doesn't match any character? The `apply_world_patch` doesn't process this field yet (future story), but when it does, a mismatched name would silently drop the fact. TEA's delivery finding already flags this — the handler should log a warning on mismatch.

None of these are blocking. The `#[non_exhaustive]` and `PartialEq` gaps are pattern violations but MEDIUM severity — non-blocking for approval.

**Pattern:** Clean data model following the established `ability.rs` pattern from 9-1, with two derive gaps that should be addressed.

[EDGE] N/A — disabled via settings
[SILENT] 1 finding dismissed — discovered_facts not processed is by-design for 9-3 scope
[TEST] N/A — disabled via settings
[DOC] N/A — disabled via settings
[TYPE] N/A — disabled via settings
[SEC] N/A — disabled via settings
[SIMPLE] N/A — disabled via settings
[RULE] 4 MEDIUM findings — missing #[non_exhaustive] and PartialEq on two enums

**Handoff:** To Baldur the Bright (SM) for finish-story
## Impact Summary

**Status:** All 7 acceptance criteria met. No blocking issues. Ready to finish.

### Scope Delivered

- **KnownFact model** with 4 fields (content, learned_turn, source, confidence)
- **FactSource enum** with 3 variants (Observation, Dialogue, Discovery)
- **Confidence enum** with 3 levels (Certain, Suspected, Rumored)
- **WorldStatePatch extension** carrying discovered facts for orchestrator processing
- **Character integration** with known_facts vector and serde backward compatibility
- **Full serde support** for persistence — facts survive save/load cycles
- **Monotonic accumulation** semantics — new facts append without modifying existing ones

### Test Coverage

23/23 tests passing (100% AC coverage). All story tests green. No pre-existing regressions.

### Non-Blocking Improvements Logged

| Finding | Severity | Status | Notes |
|---------|----------|--------|-------|
| Missing `#[non_exhaustive]` on FactSource, Confidence | MEDIUM | logged | Pattern violation vs AbilitySource (9-1). Recommended for consistency but non-blocking. |
| Missing `PartialEq` derive on FactSource, Confidence | MEDIUM | logged | Tests work around with `matches!()`. Recommended for downstream simplicity but non-blocking. |
| `apply_world_patch()` doesn't process discovered_facts | non-blocking | by-design | AC says "carries", not "applies". Future story 9-4 will handle application. |
| DiscoveredFact uses character_name not CharacterId | MINOR | accepted | No CharacterId type exists. String consistent with codebase. Spec deviation accepted by Reviewer. |

### Forward Impact

- Story 9-4 will extract facts from narration and inject them into narrator context (story 9-4 scope)
- Orchestrator turn loop will apply discovered facts to character knowledge base (story 9-4 scope)
- If CharacterId type is introduced later, DiscoveredFact.character_name may need migration

### Ready to Finish

All ACs verified. Reviewer verdict: **APPROVED**. No blocking issues. Proceed to story merge and transition.


## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The spec uses `character_id: CharacterId` in DiscoveredFact but no `CharacterId` type exists in the codebase. Tests use `character_name: String` instead, matching how characters are identified elsewhere. Affects `crates/sidequest-game/src/known_fact.rs` (Dev should use String name, not a CharacterId type). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test verification)
- **Improvement** (non-blocking): `apply_world_patch()` does not process the new `discovered_facts` field — facts on the patch are carried but not applied to characters. This is by design for story 9-3 (AC says "carries"), but story 9-4 or the orchestrator will need to handle application. Affects `crates/sidequest-game/src/state.rs` (add discovered_facts handling when fact application is in scope). *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): `FactSource` and `Confidence` enums are missing `#[non_exhaustive]` and `PartialEq` derives, breaking pattern consistency with `AbilitySource` from story 9-1. Affects `crates/sidequest-game/src/known_fact.rs` (add `#[non_exhaustive]` and `PartialEq, Eq` to both enum derives). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **DiscoveredFact uses character_name: String instead of character_id: CharacterId**
  - Spec source: context-story-9-3.md, Technical Approach
  - Spec text: "pub character_id: CharacterId"
  - Implementation: Tests use `character_name: String` for character identification
  - Rationale: No CharacterId type exists in the codebase. Characters are identified by name (NonBlankString) throughout. Using String avoids introducing a new type not in scope.
  - Severity: minor
  - Forward impact: If CharacterId is introduced later, DiscoveredFact will need updating

### Dev (implementation)
- No deviations from spec.

### TEA (test verification)
- No deviations from spec.

### Reviewer (audit)
- TEA: "DiscoveredFact uses character_name: String instead of character_id: CharacterId" → ✓ ACCEPTED by Reviewer: No CharacterId type exists. character_name: String is consistent with how characters are identified throughout the codebase.
- Dev: "No deviations from spec." → ✓ ACCEPTED by Reviewer: implementation matches spec for all 7 ACs.