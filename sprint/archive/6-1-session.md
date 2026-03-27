---
story_id: "6-1"
jira_key: "NONE"
epic: "6"
workflow: "tdd"
---
# Story 6-1: Scene directive formatter — format_scene_directive() composing fired beats + narrative hints + active stakes into MUST-weave narrator block

## Story Details
- **ID:** 6-1
- **Jira Key:** NONE (personal project)
- **Epic:** 6 (Active World & Scene Directives — Living World That Acts On Its Own)
- **Workflow:** tdd
- **Points:** 3
- **Stack Parent:** none (root story for epic 6)

## Epic Context

This is the first story in Epic 6, which makes the world an active participant in the story. Currently the trope engine and world state agent are purely reactive — they process what happened but never initiate anything. Scene directives are mandatory narrator instructions composed from fired escalation beats, narrative hints, active stakes, and faction agendas.

Port of sq-2 Epic 61 (Active World Pacing). Key reference: sq-2/docs/architecture/active-world-pacing-design.md.

## Story Scope

Implement `format_scene_directive()` as a pure function that composes:
- Fired beats from the trope engine → `DirectiveElement` with `TropeBeat` source
- Active stakes → `DirectiveElement` with `ActiveStake` source
- Narrative hints → passed through as-is

Output is a `SceneDirective` struct with mandatory elements sorted by priority and capped at a configurable limit (default 3).

**Types to create:** `SceneDirective`, `DirectiveElement`, `DirectiveSource`, `DirectivePriority`

## Technical Dependencies

Prerequisite: Story 2-8 (trope engine runtime — provides fired beats). The `FiredBeat` type should already exist in `sidequest-game`.

## Downstream

- Story 6-2: Narrator MUST-weave instruction (consumes SceneDirective)
- Story 6-3: Engagement multiplier (scales trope progression)
- Story 6-5: Wire faction agendas into scene directive
- Story 6-9: Wire scene directive into orchestrator

## Repos
- **api:** sidequest-api (Rust backend — where the code lives)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-27T11:49:05Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|

## Sm Assessment

3-point TDD story — pure function, no I/O, no LLM calls. `format_scene_directive()` collects fired beats and active stakes, converts them to `DirectiveElement`s, sorts by priority, caps at max, and returns a `SceneDirective`. Typed inputs and outputs with clear acceptance criteria. Straightforward TDD.

**Decision:** Proceed to RED. No blockers.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Pure function with typed inputs/outputs, 7 ACs, priority sorting, element cap — all testable

**Test Files:**
- `crates/sidequest-game/tests/scene_directive_story_6_1_tests.rs` — 22 tests covering 7 ACs + edge cases

**Tests Written:** 22 tests covering 7 ACs
**Status:** RED (fails to compile — `scene_directive` module does not exist in `sidequest_game`)

**Test Strategy:**
- Pure function: verify takes refs, returns owned SceneDirective
- Beat conversion: FiredBeat → DirectiveElement with TropeBeat source, content from beat.event
- Stake conversion: ActiveStake → DirectiveElement with ActiveStake source
- Priority ordering: descending sort, mixed sources
- Element cap: default 3, keeps highest priority, exact-3 passthrough
- Empty inputs: all empty vecs → empty directive
- Narrative hints: pass-through, independent of element cap
- Priority enum: Ord comparison (High > Medium > Low)
- from_beat_urgency: high (0.9) → High, medium (0.5) → Medium, low (0.15) → Low
- Faction events: empty vec (wired in 6-5)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Non-exhaustive enums | Deferred — reviewer will verify on DirectiveSource, DirectivePriority | deferred to review |
| Test quality | Self-checked all 22 tests | no vacuous assertions |

**Rules checked:** No lang-review gate file found for Rust. Self-check on vacuous assertions: 0 found.
**Self-check:** 0 vacuous tests found

**Implementation Notes for Dev:**
- `FiredBeat` (trope.rs:84) has `beat: TropeEscalation` — use `beat.event` as content and `beat.at` as urgency for `DirectivePriority::from_beat_urgency()`
- `ActiveStake` is a NEW type — does not exist yet. Tests assume `pub description: String`
- `active_stakes` on GameState is currently a plain `String` — this story creates the typed `ActiveStake` struct but does NOT migrate GameState (that's wiring work for 6-9)

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/scene_directive.rs` — new module: `ActiveStake`, `DirectiveSource`, `DirectivePriority`, `DirectiveElement`, `SceneDirective`, `format_scene_directive()`
- `crates/sidequest-game/src/lib.rs` — registered `pub mod scene_directive`

**Tests:** 23/23 passing (GREEN) + all existing crate tests passing (873 across all test suites)
**Branch:** `feat/6-1-scene-directive-formatter` (pushed)

**Implementation Notes:**
- `DirectivePriority` derives `Ord` with variant order Low < Medium < High
- `from_beat_urgency()`: >= 0.7 → High, >= 0.3 → Medium, < 0.3 → Low
- `DirectiveSource` and `DirectivePriority` both `#[non_exhaustive]` per crate pattern
- `faction_events` typed as `Vec<String>` placeholder — story 6-5 will introduce proper `FactionEvent` type
- Active stakes always get `Medium` priority per spec

**Handoff:** To verify phase (TEA for simplify + quality-pass)

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 0

All 7 ACs covered. The implementation matches the story context exactly: `format_scene_directive()` pure function taking refs and returning owned `SceneDirective`, beat conversion via `DirectiveSource::TropeBeat`, stake conversion via `DirectiveSource::ActiveStake`, priority-descending sort, element cap at const 3, empty input handling, narrative hints pass-through. Both enums have `#[non_exhaustive]`. `faction_events: Vec<String>` is a reasonable placeholder for story 6-5's `FactionEvent` type. TEA's deviation on `FiredBeat` field mapping (pseudocode vs actual struct) is correctly logged and the implementation follows the actual struct.

**Decision:** Proceed to verify

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | no duplication, well-structured ETL pattern |
| simplify-quality | 1 finding | SceneDirective missing Serialize/Deserialize derives (consistency) |
| simplify-efficiency | clean | faction_events field is spec-required for 6-5 |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 1 medium-confidence finding (SceneDirective serde derives — consistency improvement but beyond story scope; struct is transient in-memory value, not serialized)
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** All tests passing (873+ across crate), clippy errors pre-existing in sidequest-genre (not story code)
**Handoff:** To Heimdall (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 23/23 GREEN, 0 clippy in story files | N/A |
| 2 | reviewer-type-design | Yes | findings | 2: missing derives on SceneDirective (high), Vec<String> placeholder (medium) | dismissed 1, noted 1 |
| 3 | reviewer-rule-checker | Yes | findings | 5: missing derives (1), pub fields (3), missing Debug (1) | dismissed 4, noted 1 — see below |
| 4 | reviewer-silent-failure-hunter | Yes | findings | 3: silent truncation (high), empty event string (medium), empty stake string (medium) | dismissed 3 — see below |

**All received:** Yes (4 returned)
**Total findings:** 0 confirmed blocking, 10 dismissed/noted (with rationale)

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] `DirectivePriority` has `#[non_exhaustive]` — `scene_directive.rs:15`. Derives `Ord` with variant order Low < Medium < High. Sort at line 102 uses `b.cmp(a)` for descending. Correct.

2. [VERIFIED] `DirectiveSource` has `#[non_exhaustive]` — `scene_directive.rs:40`. Two variants: `TropeBeat`, `ActiveStake`. Will grow when 6-5 adds `FactionAgenda`.

3. [VERIFIED] `from_beat_urgency()` maps `beat.beat.at` (0.0–1.0 threshold) to priority levels. Thresholds: >= 0.7 → High, >= 0.3 → Medium, < 0.3 → Low. Boundary at exactly 0.7 → High, at exactly 0.3 → Medium. Tests cover interior values (0.9, 0.5, 0.15) but not exact boundaries — minor gap, not blocking.

4. [VERIFIED] Element cap at `DEFAULT_MAX_ELEMENTS = 3`. Sort then truncate preserves highest-priority elements. Correct algorithm.

5. [TYPE-DESIGN] `SceneDirective` missing `Debug, Clone, Serialize, Deserialize` — NOTED as delivery finding. The struct is a transient in-memory value consumed by the prompt composer. Not serialized, not persisted. Adding derives is a consistency improvement for debugging/testing ergonomics but not a functional requirement. Non-blocking.

6. [TYPE-DESIGN] `faction_events: Vec<String>` placeholder — DISMISSED. Story context explicitly marks faction events as out of scope (story 6-5). The type will change when 6-5 is implemented. Introducing a `FactionEvent` newtype now would be premature — story 6-5's context will define the proper type. The `Vec<String>` is always `vec![]` and never populated by this story's code.

7. [VERIFIED] `ActiveStake` gets `Medium` priority per spec. `DirectiveElement` and `ActiveStake` both have full serde derives. Test coverage: 23 tests covering all 7 ACs.

### Rule Compliance

| Rule | Instances | Verdict | Evidence |
|------|-----------|---------|----------|
| #non_exhaustive | DirectivePriority, DirectiveSource | Pass | Lines 15, 40 |
| Test quality | 23 tests | Pass | All assertions meaningful, no vacuous tests |
| Serde derives | DirectiveElement, ActiveStake, DirectivePriority, DirectiveSource | Pass | Full derive sets |
| Serde derives | SceneDirective | Noted | Missing — non-blocking improvement |

### Devil's Advocate

What if this code is wrong?

**The sort-then-truncate could discard important stakes.** If 3 high-urgency beats fire simultaneously, all active stakes get dropped (they're always Medium). In a scenario where the world state has critical stakes ("the village is burning"), those stakes would be invisible to the narrator. The cap is a blunt instrument. However: this is by design — the spec says "caps mandatory elements at a configurable limit (default 3)" and the priority ordering ensures the most urgent items survive. Future stories (6-3 engagement multiplier, 6-5 faction agendas) will refine this. Not a bug — a known simplification for story 6-1 scope.

**The `Vec<String>` for `faction_events` creates a false affordance.** External code could push strings into it before story 6-5 changes the type. In practice, `SceneDirective` is only constructed by `format_scene_directive()` which always returns `vec![]`. No other constructor exists. The risk is theoretical.

No critical or high-severity issues found. Clean implementation of a pure function with typed inputs/outputs.

8. [RULE] Rule-checker flagged pub fields on DirectiveElement, ActiveStake, SceneDirective — DISMISSED. The spec (context-story-6-1.md Technical Approach, lines 26-55) explicitly shows pub fields with direct construction. `SceneDirective` is assembled solely by `format_scene_directive()` — no external callers mutate it post-construction. `DirectiveElement` and `ActiveStake` match the crate's data model pattern (pub fields + convenience methods) as established by `AbilityDefinition` in story 9-1. Adding private fields + constructors would break all 23 integration tests.

9. [SILENT] Silent-failure-hunter flagged truncation dropping elements silently — DISMISSED. The truncation is the AC: "No more than configurable max mandatory elements (default 3)". The cap is the feature, not a bug. The caller knows the cap exists. Tracing/metrics for discarded elements is a valid future improvement but not in scope for a pure formatter story. Logging would also make this function impure.

10. [SILENT] Silent-failure-hunter flagged empty `beat.beat.event` and `stake.description` — DISMISSED. The formatter is a pure pass-through. Input validation belongs at the genre pack loading boundary (sidequest-genre crate) or at the caller site. Empty strings are cosmetic failures, not data corruption. Same reasoning as story 9-1's treatment of empty `mechanical_effect`.

**Handoff:** To Baldur the Bright (SM) for finish

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Improvement** (non-blocking): Consider adding `#[derive(Debug, Clone, Serialize, Deserialize)]` to `SceneDirective` for consistency with all other public structs in the crate. Currently not needed (transient in-memory value) but would improve debugging and testing ergonomics. Affects `crates/sidequest-game/src/scene_directive.rs` (line 67). *Found by Reviewer during code review.*

### TEA (test verification)
- **Improvement** (non-blocking): `SceneDirective` struct lacks `Debug, Clone, Serialize, Deserialize` derives that all other public structs in the crate have. Currently not needed (transient in-memory value) but would improve consistency. Affects `crates/sidequest-game/src/scene_directive.rs` (line 67). *Found by TEA during test verification.*

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test design)
- **Gap** (non-blocking): Story context spec shows `beat.narrator_instruction` and `beat.urgency` fields on `FiredBeat`, but actual `FiredBeat` (trope.rs:84-92) has `beat: TropeEscalation` where `event` maps to narrator instruction and `at` maps to urgency. Dev should use `beat.beat.event` and `beat.beat.at` respectively. Tests are written to match the actual `FiredBeat` struct, not the spec pseudocode. Affects `crates/sidequest-game/src/scene_directive.rs` (implementation mapping). *Found by TEA during test design.*
- **Gap** (non-blocking): `ActiveStake` struct does not exist in the current codebase. `active_stakes` on `GameState` (state.rs:74) is a plain `String`. This story creates the typed `ActiveStake` struct but migration of `GameState.active_stakes` from `String` to `Vec<ActiveStake>` is out of scope (story 6-9 wiring). Affects `crates/sidequest-game/src/scene_directive.rs` (new type definition). *Found by TEA during test design.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- **Tests use actual FiredBeat struct fields instead of spec pseudocode fields**
  - Spec source: context-story-6-1.md, Technical Approach
  - Spec text: "`beat.narrator_instruction.clone()` ... `DirectivePriority::from_beat_urgency(beat.urgency)`"
  - Implementation: Tests construct `FiredBeat` with `beat: TropeEscalation { event, at, ... }` matching the actual struct
  - Rationale: The spec pseudocode assumed fields that don't exist on the real `FiredBeat`. Using actual struct fields ensures tests compile and test real behavior.
  - Severity: minor
  - Forward impact: Dev must map `beat.beat.event` → content and `beat.beat.at` → urgency in `from_beat_urgency()`

### Architect (reconcile)
- No additional deviations found. Implementation matches the story context's Technical Approach section: `format_scene_directive()` pure function with typed inputs (`&[FiredBeat]`, `&[ActiveStake]`, `&[String]`), typed output (`SceneDirective`), priority-descending sort, element cap at 3, narrative hints pass-through. TEA's deviation on FiredBeat field mapping is the only spec drift and is accurately documented with correct forward impact. The Reviewer's `SceneDirective` serde derives observation is a consistency improvement, not a spec deviation — the story context does not specify serialization for SceneDirective.