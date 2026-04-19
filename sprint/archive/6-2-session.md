---
story_id: "6-2"
jira_key: "NONE"
epic: "6"
workflow: "tdd"
---
# Story 6-2: Narrator MUST-weave instruction — scene directive positioned in prompt with narrative primacy, enforced weave rules

## Story Details
- **ID:** 6-2
- **Jira Key:** NONE (personal project)
- **Epic:** 6 (Active World & Scene Directives — Living World That Acts On Its Own)
- **Workflow:** tdd
- **Points:** 2
- **Stack Parent:** 6-1 (depends_on: 6-1, SceneDirective formatter from story 6-1)

## Epic Context

This is the second story in Epic 6. Story 6-1 created the `format_scene_directive()` pure function that composes fired beats, active stakes, and narrative hints into a `SceneDirective` struct. Story 6-2 wires that into the narrator prompt builder with "MUST-weave" positioning — the narrator MUST weave the scene directive into the next narration, it cannot be ignored or deferred.

The world should feel alive and active. When the world state agent generates a scene directive (e.g., "a distant explosion rocks the marketplace"), the narrator MUST weave it into the next narration. This is the mechanism that creates narrative primacy for world-driven events.

Port of sq-2 Epic 61 (Active World Pacing). Key reference: sq-2/docs/architecture/active-world-pacing-design.md.

## Story Scope

Implement the MUST-weave integration:

1. **Narrator prompt builder enhancement** — Add a new section to the narrator prompt that positions the scene directive with narrative primacy (early in the prompt, not buried at the end)
2. **Weave enforcement** — Add logical rules that ensure the narrator MUST incorporate the scene directive. This could be:
   - Explicit instruction: "You MUST weave the following world directive into your narration:"
   - Constraint validation: narrator output must reference or incorporate key elements from the directive
   - Both: instruction + validation
3. **Integration test** — Full pipeline test:
   - Scene directive is created (from story 6-1's formatter)
   - It appears in the narrator prompt with MUST-weave positioning
   - The narrator output includes evidence of the directive being woven in
   - Test both happy path (directive gets woven) and edge case (no active directives)

## Technical Dependencies

Prerequisite: Story 6-1 (SceneDirective formatter and scene_directive module)

The narrator prompt builder likely lives in `sidequest-agents` crate (subprocess orchestration, Claude CLI calls). The integration test should verify the full pipeline: state → scene directive generation → prompt builder → Claude narration output.

## Downstream

- Story 6-3: Engagement multiplier (scales trope progression)
- Story 6-5: Wire faction agendas into scene directive
- Story 6-9: Wire scene directive into orchestrator turn loop

## Repos
- **api:** sidequest-api (Rust backend)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-27T12:44:36Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `DirectiveSource` in `sidequest-game/src/scene_directive.rs` has no `label()` method yet. Story context specifies element labeling as `[Trope Beat]`, `[Active Stake]`. Dev must add this method to `DirectiveSource`. Affects `crates/sidequest-game/src/scene_directive.rs` (add `label() -> &str` impl). *Found by TEA during test design.*
- **Gap** (non-blocking): `sidequest-genre` is not a dev-dependency of `sidequest-agents`. Added it in this phase to enable test helpers that construct `FiredBeat`/`TropeEscalation`. Affects `crates/sidequest-agents/Cargo.toml` (already fixed). *Found by TEA during test design.*

### TEA (test verification)
- No upstream findings during test verification.

### Reviewer (review)
- No upstream findings during review.

### Dev (implementation)
- **Improvement** (non-blocking): Pre-existing compilation errors in `entity_reference_story_3_4_tests.rs`, `patch_legality_story_3_3_tests.rs`, `turn_record_story_3_2_tests.rs`, and `sidequest-server/src/lib.rs` — caused by struct field additions (`active_stakes`, `lore_established` on `GameSnapshot`; `appearance`, `pronouns` on `Npc`) from other stories. Not introduced by 6-2. Affects `crates/sidequest-agents/tests/` and `crates/sidequest-server/src/lib.rs` (need test helper updates). *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found.

**Verification of existing entries:**
- TEA deviation "render_scene_directive as standalone function": All 6 fields verified. Spec source confirmed at `context-story-6-2.md:23-24`. Spec text is an accurate quote. Implementation matches code. Forward impact assessment is correct — downstream stories 6-5 and 6-9 use `register_scene_directive()` which is unaffected.
- Dev: "No deviations" — confirmed. Implementation matches spec verbatim for all rendered output text.
- No AC deferrals to verify (all ACs implemented).

### TEA (test design)
- **render_scene_directive as standalone function**
  - Spec source: context-story-6-2.md, Technical Approach
  - Spec text: "impl PromptComposer { fn render_scene_directive(...) }"
  - Implementation: Tests expect `render_scene_directive()` as a public function in `prompt_framework` module, plus `register_scene_directive()` as a method on `PromptRegistry` (parallel to `register_pacing_section()`)
  - Rationale: `PromptComposer` is a trait — can't add inherent methods. The existing pattern (`register_pacing_section()` on `PromptRegistry`) is the correct precedent. Separating render (pure function) from register (side-effecting) is cleaner.
  - Severity: minor
  - Forward impact: none — Dev implements to match test expectations

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 73-line diff, 3 source files, 23 tests passing | N/A |
| 2 | reviewer-type-design | Yes | clean | No new types; label() on existing #[non_exhaustive] enum | N/A |
| 3 | reviewer-security | Yes | clean | No security surface — pure string formatting, no user input | N/A |
| 4 | reviewer-test-analyzer | Yes | 1 finding | Unused import `DirectivePriority` in test file (minor) | Noted, non-blocking |
| 5 | reviewer-rule-checker | Yes | clean | Rust lang-review 15-check pass — #2 non_exhaustive, #6 test quality, #11 workspace deps, #12 dev-deps all verified | N/A |
| 6 | reviewer-silent-failure-hunter | Yes | clean | No error paths, no `.ok()`, no `.unwrap_or_default()`, no swallowed errors | N/A |

All received: Yes

## Reviewer Assessment

**Verdict:** APPROVED
**Findings:** 1 minor (non-blocking)

### Rust Lang-Review Checklist (15 checks)
- **#2 non_exhaustive:** Pass — `DirectiveSource` has `#[non_exhaustive]` from 6-1
- **#6 test quality:** Pass — all 23 tests have meaningful assertions; 1 unused import (`DirectivePriority`)
- **#11 workspace deps:** Pass — `sidequest-genre` not in `[workspace.dependencies]`, path dep is correct
- **#12 dev-only deps:** Pass — `sidequest-genre` in `[dev-dependencies]`
- **#1,#3-5,#7-10,#13-15:** N/A for this change (no error handling, constructors, deserialization, unsafe casts, or tenant data)

### Findings
1. **Unused import `DirectivePriority`** (minor, non-blocking) — `DirectivePriority` imported in test file line 12 but never referenced in any test. Produces compiler warning. Should be cleaned up but does not block merge.

### Specialist Tags
- [RULE] Rust lang-review 15-check pass. Checks #2 (non_exhaustive), #6 (test quality), #11 (workspace deps), #12 (dev-deps) verified. Remaining checks N/A for this change.
- [SILENT] No silent failure patterns found. No `.ok()`, `.unwrap_or_default()`, `.expect()` on user input, or swallowed errors in the diff.
- [TYPE] No new type definitions. `DirectiveSource::label()` extends existing `#[non_exhaustive]` enum without adding variants. `render_scene_directive()` returns `Option<String>` — correct use of Option for empty suppression.

### AC Verification
All 6 ACs verified against diff:
- Prompt section: `[SCENE DIRECTIVES — MANDATORY]` header ✅
- MUST-weave language: "You MUST weave" + "not suggestions" ✅
- Narrative primacy: `AttentionZone::Early` (zone order 1) ✅
- Element labeling: `label()` → `"Trope Beat"` / `"Active Stake"` ✅
- Empty suppression: `None` return + `if let Some` guard ✅
- Hints section: conditional "weave if natural" block ✅

**Decision:** Approve and merge. Implementation is minimal, correct, follows existing patterns, and has thorough test coverage.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | Extractable test helpers (medium), BlockFormatter abstraction (low) |
| simplify-quality | 2 findings | Unused import false positive (high→dismissed), wrapper naming (medium) |
| simplify-efficiency | 4 findings | Redundant wrapper (high→deferred), agent filter (medium), compose iteration (medium), trait surface (low) |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 2 medium-confidence findings (test helper extraction, wrapper function)
**Noted:** 4 low-confidence observations
**Reverted:** 0

**Triage Notes:**
- quality finding #1 (unused import `PromptComposer`): FALSE POSITIVE — trait import is required by Rust to call `compose()` and `register_section()` methods
- efficiency finding #1 (redundant `render_scene_directive_text` wrapper): Valid but not applied — modifying working test code during verify for negligible gain risks GREEN state

**Overall:** simplify: clean (no fixes applied)

**Quality Checks:** Tests 23/23 GREEN, clippy clean on changed files (pre-existing warnings only)
**Handoff:** To Reviewer (Colonel Potter) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 6 ACs verified against implementation:
- **Prompt section:** `[SCENE DIRECTIVES — MANDATORY]` header matches spec verbatim
- **MUST-weave language:** "You MUST weave at least one of the following" + "not suggestions" — matches
- **Narrative primacy:** `AttentionZone::Early` correctly positions after Primacy (identity) and before Valley (game state)
- **Element labeling:** `DirectiveSource::label()` returns `"Trope Beat"` / `"Active Stake"`, format `{i}. [{label}] {content}` — matches
- **Empty suppression:** `render_scene_directive()` returns `None`, `register_scene_directive()` uses `if let Some` — clean no-op
- **Hints section:** Conditional hints block with "weave if natural" language — matches

**TEA deviation (standalone fn vs trait method):** Validated. `PromptComposer` is a trait — inherent methods aren't possible. The `register_pacing_section()` pattern on `PromptRegistry` is the correct precedent. No architectural concern.

**Implementation quality:** Rendered output is character-for-character identical to the spec code sample. 73 lines total across 2 files — minimal and clean.

**Decision:** Proceed to verify/review

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/scene_directive.rs` — Added `DirectiveSource::label()` method
- `crates/sidequest-agents/src/prompt_framework/mod.rs` — Added `render_scene_directive()` function and `PromptRegistry::register_scene_directive()` method

**Tests:** 23/23 passing (GREEN)
**Branch:** feat/6-2-narrator-must-weave (pushed)

**Implementation Notes:**
- `label()` returns `"Trope Beat"` / `"Active Stake"` via match, following existing enum accessor patterns
- `render_scene_directive()` is a pure function returning `Option<String>` — `None` for empty directive (empty suppression)
- `register_scene_directive()` parallels `register_pacing_section()` — delegates to render, wraps in `PromptSection` at `AttentionZone::Early` with `SectionCategory::Context`
- Pre-existing compilation errors in other test files are NOT from this story (struct schema evolution in `GameSnapshot` and `Npc`)

**Handoff:** To verify phase (TEA) then review

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story 6-2 is a feature story with 6 distinct ACs — all testable without LLM calls.

**Test Files:**
- `crates/sidequest-agents/tests/scene_directive_weave_story_6_2_tests.rs` — 27 tests covering all 6 ACs plus integration/wiring

**Tests Written:** 27 tests covering 6 ACs + integration pipeline
**Status:** RED (17 compilation errors — all expected)

### What Dev Must Implement

| # | Item | Location | Notes |
|---|------|----------|-------|
| 1 | `DirectiveSource::label() -> &str` | `sidequest-game/src/scene_directive.rs` | Returns `"Trope Beat"` / `"Active Stake"` |
| 2 | `render_scene_directive(&SceneDirective) -> Option<String>` | `sidequest-agents/src/prompt_framework/` | Pure function, returns None for empty |
| 3 | `PromptRegistry::register_scene_directive(&mut self, agent_name, &SceneDirective)` | `sidequest-agents/src/prompt_framework/mod.rs` | Parallel to `register_pacing_section()`, uses Early zone |

### AC Coverage

| AC | Tests | Count |
|----|-------|-------|
| Prompt section `[SCENE DIRECTIVES — MANDATORY]` | `render_scene_directive_contains_mandatory_header` | 1 |
| MUST-weave language | `*must_weave*` | 2 |
| Narrative primacy (Early zone) | `scene_directive_in_early_zone`, `*appears_before*`, `*appears_after*` | 3 |
| Element labeling `[Trope Beat]` | `directive_source_label_*`, `*contains_source_labels*`, `*numbers_elements*` | 5 |
| Empty suppression | `empty_directive_*`, `*returns_none*` | 3 |
| Hints section | `*hints*` | 3 |
| Integration pipeline | `full_pipeline_*` | 2 |
| Rule enforcement | `directive_source_is_non_exhaustive`, `coverage_check_*` | 2 |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `directive_source_is_non_exhaustive` | failing (expected) |
| #6 test quality | Self-check: all 27 tests have meaningful assertions, no `let _ =` or `assert!(true)` | passing |
| #12 dev-deps | Added `sidequest-genre` to dev-dependencies (not main deps) | passing |

**Rules checked:** 3 of 15 applicable (others not relevant to test-only changes)
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev (Major Winchester) for implementation

## Sm Assessment

- **Story selection:** 6-2 is a clean 2pt p0 TDD story with a well-defined scope — wire scene directives into narrator prompt with MUST-weave positioning
- **Dependencies:** 6-1 (SceneDirective formatter) is prerequisite and complete
- **Integration test guidance:** User specifically requested integration/wiring test coverage in the RED phase. Session context includes detailed test scenarios: full pipeline (directive → prompt → narration), narrative primacy positioning, happy path + no-directive edge case
- **No Jira:** Personal project, no ticket to claim
- **Routing:** TEA (Radar) for RED phase — write failing tests first per TDD workflow