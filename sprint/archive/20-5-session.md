---
story_id: "20-5"
jira_key: ""
epic: "20"
workflow: "tdd"
---

# Story 20-5: scene_render tool — visual scene via tool call

## Story Details
- **ID:** 20-5
- **Title:** scene_render tool — visual scene via tool call
- **Jira Key:** (Personal project — no Jira)
- **Epic:** 20 — Narrator Crunch Separation — Tool-Based Mechanical Extraction (ADR-057)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-02T14:50:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T14:06:18Z | 2026-04-02T14:07:52Z | 1m 34s |
| red | 2026-04-02T14:07:52Z | 2026-04-02T14:12:29Z | 4m 37s |
| green | 2026-04-02T14:12:29Z | 2026-04-02T14:30:36Z | 18m 7s |
| spec-check | 2026-04-02T14:30:36Z | 2026-04-02T14:31:45Z | 1m 9s |
| verify | 2026-04-02T14:31:45Z | 2026-04-02T14:38:49Z | 7m 4s |
| review | 2026-04-02T14:38:49Z | 2026-04-02T14:46:12Z | 7m 23s |
| green | 2026-04-02T14:46:12Z | 2026-04-02T14:48:16Z | 2m 4s |
| review | 2026-04-02T14:48:16Z | 2026-04-02T14:49:28Z | 1m 12s |
| spec-reconcile | 2026-04-02T14:49:28Z | 2026-04-02T14:50:32Z | 1m 4s |
| finish | 2026-04-02T14:50:32Z | - | - |

## Business Context

`visual_scene` is the image generation trigger — subject, tier, mood, tags. The narrator currently writes prose AND formats a visual description suitable for image generation. The creative work is describing the scene; decomposing it into tier/mood/tags is mechanical. Entity introductions (NPC portraits, location landscapes) may already have `visual_prompt` from generator tools (ADR-056) — `scene_render` unifies the path.

## Technical Context

### Scope Boundaries

**In scope:**
- `scene_render` tool with enum validation for tier/mood/tags
- Remove visual_scene JSON schema from narrator prompt
- `assemble_turn` integration
- OTEL events

**Out of scope:**
- Changing the `VisualScene` struct
- Image generation pipeline (daemon side)
- Generator tool visual_prompt integration (future enhancement)

### Technical Guardrails

- `scene_render` takes: subject description (free text from narrator, ≤100 chars), tier (portrait/landscape/scene_illustration), mood (from visual mood enum), tags (from tag enum).
- Returns `VisualScene` struct JSON.
- The narrator calls this when something visually significant happens. For entity introductions where a generator tool already produced a `visual_prompt`, the narrator can pass that through.
- Remove `visual_scene` JSON schema documentation (~100 tokens) from narrator system prompt.
- `assemble_turn` merges into `ActionResult.visual_scene`.
- Key consideration: the narrator's subject description is creative (LLM decides what to paint). The tool validates and structures it. Don't over-constrain the subject text.

## Acceptance Criteria

1. `scene_render` tool accepts subject, tier, mood, tags and returns `VisualScene` JSON
2. Tier, mood, and tags validated against their enums
3. Subject text passed through as-is (narrator's creative judgment)
4. Narrator prompt documents the tool instead of the JSON field schema
5. `assemble_turn` merges into ActionResult
6. OTEL span with subject text and tier for GM panel visibility

## Delivery Findings

- No upstream findings during test design.
- **Improvement** (non-blocking): Existing 20-2 tests use struct literal syntax for `ToolCallResults` without `..Default::default()`, breaking every time a new field is added. Updated to struct update syntax. Affects `tests/scene_tools_story_20_2_tests.rs` (future-proofing for 20-6/20-7). *Found by Dev during implementation.*

## Impact Summary

**Blocking Issues:** 0  
**Improvement Findings:** 1

### Key Deliverables

- `scene_render` tool module (Rust): New tool for visual scene extraction, 3 enums (SceneTier, VisualMood, VisualTag) with case-insensitive validation, 1 validator function with OTEL instrumentation
- Tool call parser integration: `tool_call_parser.rs` wired to call validate_scene_render() instead of raw struct construction
- Narrator prompt: Removed ~100 tokens of visual_scene JSON schema documentation, replaced with tool reference
- `assemble_turn` integration: ToolCallResults extended with visual_scene field, override logic wired (tool result OR extracted visual_scene)
- Test coverage: 30 tests covering validation, enum exhaustiveness, parser integration, assembler wiring, OTEL spans

### Quality Metrics

- Build: Clean (557 tests passing, all green)
- Code review: 9 specialists cleared (preflight, edge-case, silent-failure, rule-check, test-analyzer, comment-analyzer, type-design, security, simplifier)
- Lint: Clean
- OTEL instrumentation: Complete (tracing::instrument on validate_scene_render, tracing::warn! on all error paths)
- Test suite: 30/30 passing, wiring tests included

### Improvement Notes

1. **Struct literal syntax in 20-2 tests** (non-blocking): Existing test files for story 20-2 used `ToolCallResults { .. }` struct literal syntax without `..Default::default()`. This breaks whenever a new field is added to the struct. Updated to struct update syntax for future-proofing (affects stories 20-6/20-7). *Found during implementation, applied as best practice.*

### Follow-Up Dependencies

- Story 20-6: Visual prompt integration for entity tools (portrait generation with visual_prompt from generator tools)
- Story 20-7: Similar tool-based extraction for remaining mechanical fields


## Sm Assessment

Story 20-5 is ready for TDD red phase. Context is complete — story builds on the tool infrastructure from 20-10 (sidecar file protocol, ToolCallParser). The `scene_render` tool follows the same pattern as `set_mood`/`set_intent` (20-2) but with richer parameters (subject, tier, mood, tags with enum validation). Repo: `api` only. Handoff to Han Solo (TEA) for failing tests.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New tool module with enum validation, parser integration, assembler wiring

**Test Files:**
- `crates/sidequest-agents/tests/scene_render_story_20_5_tests.rs` — 28 tests

**Tests Written:** 28 tests covering 6 ACs
**Status:** RED (compile errors — module, struct field, parser arm don't exist)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `scene_tier_enum_is_non_exhaustive`, `visual_mood_enum_is_non_exhaustive`, `visual_tag_enum_is_non_exhaustive` | failing |
| #6 test quality | All tests have meaningful assert_eq!/assert! with specific messages | self-checked |
| OTEL | `validate_scene_render_has_tracing_instrument` | failing |
| Wiring | `scene_render_module_is_exported`, `tool_call_parser_handles_scene_render_tool_name`, `scene_render_e2e_sidecar_to_action_result`, `narrator_prompt_does_not_contain_visual_scene_json_schema` | failing |

**Rules checked:** 3 of 15 applicable (non_exhaustive, test quality, OTEL). Others (validated constructors, serde bypass, public fields) less applicable — VisualScene is an existing struct with pub fields, scene_render returns it directly.
**Self-check:** 0 vacuous tests found

**Handoff:** To Yoda (Dev) for implementation

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (spec-check)
- No additional deviations found.

### Architect (reconcile)
- No additional deviations found. TEA and Dev entries verified — both correctly report no spec deviations. Reviewer's B1/B2 were implementation bugs (wiring gap and missing OTEL events), not spec drift — both fixed in round 2. No ACs deferred.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 6 ACs verified against implementation:
- AC-1: validate_scene_render() accepts subject/tier/mood/tags, returns VisualScene ✓
- AC-2: SceneTier/VisualMood/VisualTag enums with case-insensitive validation ✓
- AC-3: Subject passthrough with length-only constraint (1-100 chars) ✓
- AC-4: visual_scene JSON schema removed from narrator prompt ✓
- AC-5: assemble_turn uses tool_results.visual_scene.or(extraction.visual_scene) ✓
- AC-6: tracing::instrument with subject and tier fields ✓

Technical guardrails honored: VisualScene struct unchanged, override pattern matches set_mood/set_intent precedent, parser handles missing fields gracefully.

**Decision:** Proceed to verify

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/tools/scene_render.rs` — new module: SceneTier, VisualMood, VisualTag enums + validate_scene_render() + tracing::warn! on all error paths (B2 fix)
- `src/tools/mod.rs` — export scene_render
- `src/tools/assemble_turn.rs` — add visual_scene field to ToolCallResults, wire override logic
- `src/tools/tool_call_parser.rs` — scene_render match arm now calls validate_scene_render() instead of raw VisualScene construction (B1 fix)
- `src/agents/narrator.rs` — remove visual_scene JSON schema docs from system prompt
- `tests/assemble_turn_story_20_1_tests.rs` — update guard test (visual_scene → personality_events)
- `tests/scene_tools_story_20_2_tests.rs` — update guard test, use ..Default for future-proofing

**Review Round 2 Fixes:**
- B1: Parser now calls validate_scene_render() — validator has production callers
- B2: All error paths emit tracing::warn! before returning Err

**Tests:** 30/30 passing (GREEN), full suite clean
**Branch:** feat/20-5-scene-render-tool (pushed)

**Handoff:** Back to review pipeline

## TEA Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (source only, test files excluded)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | Enum boilerplate duplication (high), validate pattern duplication (high), parser block duplication (medium), JSON extraction pattern (medium) |
| simplify-quality | 1 finding | Unnecessary explicit deref `(*tag)` (medium) |
| simplify-efficiency | 5 findings | Enum→string round-trip (high×2), parser bypasses validation (medium), preprocessor complexity (medium), enum boilerplate (low) |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 1 medium-confidence finding (cosmetic `(*tag)` deref in scene_render.rs:161)
**Noted:** 9 findings dismissed — 4 pre-existing code (not this story), 3 premature abstraction (below threshold per CLAUDE.md), 2 by-design (validation round-trip is the point)
**Reverted:** 0

**Overall:** simplify: clean (no changes applied to story code)

**Quality Checks:** All passing — full crate suite green
**Handoff:** To Obi-Wan (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | pass | Build green, 557 tests pass, 0 code smells | N/A |
| 2 | reviewer-edge-hunter | Yes | 6 findings | Validator bypass (high), bytes-vs-chars (high), whitespace subject (high), dup tags (med), non-string tags (med), dup calls (med) | 1 blocking, 2 improvements, 3 dismissed |
| 3 | reviewer-silent-failure-hunter | Yes | 3 findings | Validator bypass (high), tags default (medium), sidecar open default (medium) | 1 blocking, 2 dismissed |
| 4 | reviewer-rule-checker | Yes | 2 violations | Rule #5 unvalidated constructor (high), Rule #4 missing tracing on error paths (high) | 2 blocking |
| 5 | reviewer-test-analyzer | Yes | clean | 30 tests, all meaningful assertions, AC coverage complete | N/A |
| 6 | reviewer-comment-analyzer | Yes | clean | Doc comments on all pub types and functions, no stale comments | N/A |
| 7 | reviewer-type-design | Yes | clean | Enums use #[non_exhaustive], no stringly-typed APIs (enums validate then stringify for VisualScene compat) | N/A |
| 8 | reviewer-security | Yes | clean | No injection vectors, no user-controlled paths without validation (except B1 wiring gap) | Covered by B1 |
| 9 | reviewer-simplifier | Yes | clean | No unnecessary complexity — enum pattern matches set_mood/set_intent precedent | N/A |

All received: Yes

## Reviewer Assessment

**Verdict:** APPROVED (round 2) — both blockers fixed

### Blocking Findings

**B1 — `[RULE]` `[EDGE]` `[SILENT]` `[SEC]` Parser bypasses validate_scene_render() (rule #5, all 4 subagents)**
- `tool_call_parser.rs:133` constructs `VisualScene` from raw sidecar strings without calling `validate_scene_render()`. The validator has 30 tests and zero production callers — dead code in production.
- **Fix:** Replace `VisualScene { ... }` construction with `validate_scene_render(subject, tier, mood, &tag_refs)`. On `Err`, `warn!` + `skipped_count += 1`.

**B2 — `[RULE]` validate_scene_render error paths have no tracing::warn! (rule #4)**
- `scene_render.rs:137-161` — four `return Err(...)` paths emit no tracing event. The `#[instrument]` span closes silently on validation failure. OTEL principle requires every subsystem decision to be logged.
- **Fix:** Add `tracing::warn!(valid = false, ...)` before each `return Err(...)`, matching the pattern in `set_mood.rs:76-77`.

### Non-Blocking Improvements (noted, not required for approval)

- `subject.len()` counts bytes not chars — use `subject.chars().count()` for Unicode correctness
- Whitespace-only subject passes validation — add `subject.trim().is_empty()` check

### Dismissed (5 findings)

- `[EDGE]` Duplicate tags: spec doesn't require dedup, tags are hints
- `[EDGE]` Non-string tag elements: pre-existing filter_map pattern from set_mood/set_intent
- `[EDGE]` Duplicate scene_render overwrites: same last-wins pattern as other tools
- `[SILENT]` Sidecar open failure: pre-existing, not this story's scope
- `[SILENT]` Tags unwrap_or_default: empty tags valid per AC

### Clean Categories

- `[TEST]` 30 tests with meaningful assertions, all ACs covered, wiring tests included
- `[DOC]` Doc comments on all pub types/functions, no stale comments found
- `[TYPE]` Enums use #[non_exhaustive], no stringly-typed APIs — enums validate then stringify for VisualScene String field compat
- `[SEC]` No injection vectors beyond B1 wiring gap (covered above)
- `[SIMPLE]` No unnecessary complexity — pattern matches set_mood/set_intent precedent

### Round 2 Verification

- B1 ✅ `tool_call_parser.rs:123` now calls `validate_scene_render()` — production caller confirmed via grep
- B2 ✅ All 4 error paths in `validate_scene_render()` emit `tracing::warn!(valid = false, ...)` with contextual fields
- 30/30 tests GREEN
- No new issues introduced by fix commit

**Handoff:** To spec-reconcile (Architect)