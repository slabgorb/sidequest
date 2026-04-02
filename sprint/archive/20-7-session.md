---
story_id: "20-7"
jira_key: null
epic: 20
workflow: tdd
---

# Story 20-7: personality_event, resource_change, play_sfx tools

## Story Details

- **ID:** 20-7
- **Epic:** 20 (Narrator Crunch Separation)
- **Points:** 3
- **Workflow:** tdd
- **Repos:** sidequest-api
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-02T16:54:20Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T12:00:00Z | 2026-04-02T16:13:07Z | 4h 13m |
| red | 2026-04-02T16:13:07Z | 2026-04-02T16:23:11Z | 10m 4s |
| green | 2026-04-02T16:23:11Z | 2026-04-02T16:34:25Z | 11m 14s |
| spec-check | 2026-04-02T16:34:25Z | 2026-04-02T16:35:57Z | 1m 32s |
| verify | 2026-04-02T16:35:57Z | 2026-04-02T16:40:24Z | 4m 27s |
| review | 2026-04-02T16:40:24Z | 2026-04-02T16:53:35Z | 13m 11s |
| spec-reconcile | 2026-04-02T16:53:35Z | 2026-04-02T16:54:20Z | 45s |
| finish | 2026-04-02T16:54:20Z | - | - |

## Delivery Findings

- No upstream findings during test design.
- **Improvement** (non-blocking): Story 20-5 test file used explicit struct literal syntax for `ToolCallResults` instead of `..Default::default()`, breaking when new fields were added. Updated to struct update syntax. Affects `tests/scene_render_story_20_5_tests.rs`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `.unwrap()` on `serde_json::from_value` at tool_call_parser.rs:175 should be replaced with `map_err` + warn + skip for consistency with all other error handling in the parser. Coupling between VALID_EVENT_TYPES and game enum is implicit. Affects `crates/sidequest-agents/src/tools/tool_call_parser.rs` (line 175). *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Reviewer (audit)
- **Updated sibling test files for Phase 7 migration** → ✓ ACCEPTED by Reviewer: Necessary cascade from removing narrator prompt fields. All three sibling test updates are correct and minimal.

### Architect (reconcile)
- No additional deviations found. Dev's single logged deviation (sibling test updates) is accurate, properly sourced, and correctly stamped by Reviewer. All 6 ACs implemented without drift. The Reviewer's `.unwrap()` finding is a quality improvement (Delivery Finding), not a spec deviation — the code fulfills AC-1 (validate event_type enum) as specified; the implementation detail of how the validated string is converted to the game enum is not prescribed by the AC.

### Dev (implementation)
- **Updated sibling test files for Phase 7 migration**
  - Spec source: context-story-20-7.md, AC-4
  - Spec text: "All three removed from narrator JSON schema documentation"
  - Implementation: Updated stale "not yet migrated" assertions in 20-1 and 20-6 test files; fixed struct literal syntax in 20-5 tests
  - Rationale: Removing schema fields from narrator prompt necessarily invalidates prior-phase assertions that those fields still exist
  - Severity: minor
  - Forward impact: none — tests now correctly reflect cumulative migration state

## TEA Assessment

**Tests Required:** Yes
**Reason:** Three new tool modules with validation, parser integration, assemble_turn wiring, and narrator prompt changes.

**Test Files:**
- `crates/sidequest-agents/tests/personality_resource_sfx_story_20_7_tests.rs` — all ACs for personality_event, resource_change, play_sfx tools

**Tests Written:** 70+ tests covering 6 ACs
**Status:** RED (failing — compilation errors, ready for Dev)

### AC Coverage

| AC | Tests | Category |
|----|-------|----------|
| AC-1: personality_event validation | 13 tests | enum validation, case-insensitive, rejects invalid, trims, serializes |
| AC-2: resource_change validation | 12 tests | genre declaration match, case-insensitive, rejects NaN/Infinity, trims |
| AC-3: play_sfx validation | 7 tests | library match, case-insensitive, rejects unknown, trims |
| AC-4: narrator prompt schema removal | 4 tests | personality_events/resource_deltas/sfx_triggers removed, non-migrated retained |
| AC-5: assemble_turn integration | 18 tests | override semantics, fallback, empty-overrides-narrator, cross-field preservation |
| AC-6: OTEL spans | 4 tests | tracing subscriber tests for each tool |

### Parser & E2E Coverage

| Category | Tests |
|----------|-------|
| Sidecar parser recognition | 9 tests (individual + multi + mixed records) |
| End-to-end sidecar→parse→assemble | 3 tests (one per tool type) |
| Wiring (module accessibility) | 3 tests |
| ToolCallResults new fields | 4 tests |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #5 validated constructors | rejects_empty, rejects_invalid, rejects_whitespace (all 3 tools) | failing |
| #6 test quality | Self-check: all tests have meaningful assert_eq!/assert! with specific values | verified |
| #9 public fields | Getter methods used throughout (.npc(), .resource(), .sfx_id()) | failing |
| #2 non_exhaustive | N/A — tool result types are not public enums | — |
| #8 Deserialize bypass | N/A — types produced by validate_*, not deserialized | — |
| #13 constructor consistency | N/A — no Deserialize impls on these types | — |

**Rules checked:** 3 of 15 applicable, 12 N/A for this story
**Self-check:** 0 vacuous tests found

**Handoff:** To Inigo Montoya (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-agents/src/tools/personality_event.rs` — new: validates event_type enum, NPC name, returns PersonalityEventResult
- `crates/sidequest-agents/src/tools/resource_change.rs` — new: validates resource name against genre declarations, finite delta
- `crates/sidequest-agents/src/tools/play_sfx.rs` — new: validates SFX ID against loaded library
- `crates/sidequest-agents/src/tools/mod.rs` — registered three new modules
- `crates/sidequest-agents/src/tools/assemble_turn.rs` — three new Option fields on ToolCallResults, override semantics in assemble_turn
- `crates/sidequest-agents/src/tools/tool_call_parser.rs` — three new match arms for sidecar JSONL parsing
- `crates/sidequest-agents/src/agents/narrator.rs` — removed ~280 tokens of JSON schema docs for personality_events, resource_deltas, sfx_triggers
- `crates/sidequest-agents/tests/assemble_turn_story_20_1_tests.rs` — updated stale prompt assertion
- `crates/sidequest-agents/tests/quest_update_story_20_6_tests.rs` — updated stale prompt assertion
- `crates/sidequest-agents/tests/scene_render_story_20_5_tests.rs` — fixed struct literal syntax

**Tests:** 70/70 passing (GREEN). Full suite: 0 new regressions.
**Branch:** feat/20-7-personality-resource-sfx-tools (pushed)

**Handoff:** To Westley (Reviewer) via verify phase

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 7 findings | Shared validation patterns, extractable helpers, repeated tracing |
| simplify-quality | 7 findings | Parser validation inconsistency, naming, unwrap safety |
| simplify-efficiency | clean | No unnecessary complexity |

**Applied:** 0 high-confidence fixes (all dismissed with rationale)
**Flagged for Review:** 1 medium-confidence finding (unwrap on serde_json::from_value in parser line 175 — fragile if game enum diverges from const array)
**Noted:** 6 low-confidence observations (validation helper extraction, naming)
**Reverted:** 0

**Dismissal rationale for high-confidence findings:**
- Reuse findings (shared validation helpers): Project rules say "three similar lines > premature abstraction." Each tool has different validation needs. Coupling them via shared helpers adds fragility.
- Quality "dead code" findings (validate_resource_change, validate_play_sfx not called in parser): Architecturally intentional — parser does raw extraction because genre data is unavailable at parse time. Validation functions are for tool-script invocation path where genre context IS available. Confirmed by Architect in spec-check.

**Overall:** simplify: clean (no changes applied)

**Quality Checks:** All passing (0 new regressions in full suite)
**Handoff:** To Westley (Reviewer) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 6 ACs verified against implementation:

| AC | Spec | Code | Status |
|----|------|------|--------|
| AC-1 | personality_event validates enum, returns JSON | `validate_personality_event` with 5-variant const array, `PersonalityEventResult` serializable | Aligned |
| AC-2 | resource_change validates against genre declarations | `validate_resource_change` takes `&[String]`, case-insensitive, rejects NaN/Infinity | Aligned |
| AC-3 | play_sfx validates against SFX library | `validate_play_sfx` takes `&[String]`, case-insensitive | Aligned |
| AC-4 | Remove all three from narrator JSON schema | personality_events (8 lines), sfx_triggers (5 lines), resource_deltas (5 lines) removed | Aligned |
| AC-5 | assemble_turn collects into ActionResult fields | Three new Option fields on ToolCallResults, unwrap_or() override semantics | Aligned |
| AC-6 | OTEL spans per invocation | `#[tracing::instrument]` on all three, info/warn in parser | Aligned |

**Architectural note:** Parser does raw extraction for resource_change and play_sfx (no genre validation at parse time). This is correct — genre data isn't available at the parser level; validation occurs at tool invocation time. personality_event validation IS done in the parser because the enum is compile-time static.

**Decision:** Proceed to verify/review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — tests pass, clippy clean on story files, no smells |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 1 (unwrap), dismissed 2 (resource/sfx validation bypass — architectural) |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 4 | confirmed 1 (unwrap), dismissed 2 (ToolCallResults pub fields — pattern-consistent, validation bypass — architectural), noted 1 (VALID_EVENT_TYPES sync) |
| 7 | reviewer-security | Yes | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | error | 0 | Subagent couldn't read diff file; domain covered manually by Reviewer (15-rule check above) — 1 finding (Rule #1 unwrap) |

**All received:** Yes (4 returned with results, 5 disabled via settings, rule-checker errored but domain covered manually)
**Total findings:** 1 confirmed, 4 dismissed (with rationale), 1 noted

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Private fields with getters on all three result types — `PersonalityEventResult` (personality_event.rs:13-17 fields private, getters at 21-33), `ResourceChangeResult` (resource_change.rs:12-15 private, getters at 18-27), `PlaySfxResult` (play_sfx.rs:11-12 private, getter at 16-19). Complies with lang-review rule #9.

2. [VERIFIED] Error types use thiserror — `InvalidPersonalityEvent` (personality_event.rs:38), `InvalidResourceChange` (resource_change.rs:31), `InvalidSfxId` (play_sfx.rs:24). All use `#[derive(thiserror::Error)]`.

3. [VERIFIED] OTEL tracing on all validation functions — `#[tracing::instrument]` on personality_event.rs:55, resource_change.rs:39, play_sfx.rs:31. Info on success, warn on failure. Parser arms also emit info/warn. Complies with OTEL observability principle.

4. [VERIFIED] assemble_turn override semantics correct — `unwrap_or()` for Vec/HashMap fields (personality_events, resource_deltas, sfx_triggers) at assemble_turn.rs:69-73. Matches existing `quest_updates` pattern at line 67. `Some(empty)` correctly overrides narrator extraction.

5. [MEDIUM] [SILENT] [TYPE] [RULE] `.unwrap()` on `serde_json::from_value` at tool_call_parser.rs:175 — panics if `VALID_EVENT_TYPES` (personality_event.rs:42-48) diverges from `sidequest_game::PersonalityEvent` serde mapping. Should be `map_err` + warn + skip, consistent with all other error handling in this match block. Flagged by silent-failure-hunter, type-design, and manual rule check (Rule #1). **Non-blocking** because: (a) coupling is within same codebase, (b) test suite covers all 5 variants, (c) divergence requires inconsistent developer action.

6. [VERIFIED] Narrator prompt removal correct — personality_events (8 lines), sfx_triggers (5 lines), resource_deltas (5 lines) removed from narrator.rs. Remaining fields (footnotes, items_gained, npcs_present, merchant_transactions) preserved. Verified against narrator.rs:94-108.

7. [VERIFIED] No `#[derive(Deserialize)]` on result types — only `Serialize`. Complies with lang-review rule #8.

8. [VERIFIED] Sibling test updates correct — 20-1 (assemble_turn_story_20_1_tests.rs:354), 20-5 (scene_render_story_20_5_tests.rs:296-338), 20-6 (quest_update_story_20_6_tests.rs:287) all updated for Phase 7 migration. No stale assertions remain.

### Rule Compliance

| Rule | Items Checked | Compliant |
|------|--------------|-----------|
| #1 Silent errors | `.unwrap()` at parser:175 | **VIOLATION** (Medium — should be graceful skip) |
| #2 non_exhaustive | No new public enums | N/A |
| #4 Tracing | 3 validate fns + 3 parser arms | Pass |
| #5 Validated constructors | 3 validate fns return Result | Pass |
| #8 Deserialize bypass | 3 result types: Serialize only | Pass |
| #9 Public fields | Result types: private+getters. ToolCallResults: pub but no invariants (pattern-consistent) | Pass |
| #13 Constructor consistency | No Deserialize on result types | N/A |

### Devil's Advocate

What if this code is broken? Let me argue the case.

The most dangerous path is `personality_event` in the parser. The validation function uses a const string array (`VALID_EVENT_TYPES`) as its source of truth, but the actual type system uses `sidequest_game::PersonalityEvent` — a separate enum with `#[serde(rename_all = "snake_case")]`. These are two independent truth sources. Today they match. Tomorrow, someone adds `Humiliation` to the game enum. If they add `"humiliation"` to the const array too, everything works. But if they forget — or if a serde rename changes the mapping — `validate_personality_event` accepts the string, then `serde_json::from_value` panics on line 175. The narrator's entire turn dies. For a low-frequency field (personality events don't fire every turn), this could lurk for days before hitting.

For resource_change and play_sfx, the parser does zero validation — any string the LLM hallucinates goes through. A made-up resource like "mana" in a genre that only has "luck" would silently enter `resource_deltas` and propagate to `ActionResult`. The downstream consumer (dispatch pipeline) might silently ignore unknown resources, or it might try to apply a delta to a resource that doesn't exist. The Architect says "genre data unavailable at parse time" — but is that a constraint or a choice? Could `parse_tool_results` accept a genre context parameter? That's a design question for story 20-8 or beyond, not a blocker here.

What about a malicious or confused LLM? If the LLM calls `play_sfx` with `sfx_id: "../../../etc/passwd"` — the parser accepts it verbatim. The SFX ID eventually reaches the client UI, which presumably looks up a file path. Path traversal through SFX IDs? Unlikely to be exploitable (client-side lookup, not server-side file access), but it's an unvalidated trust boundary.

**Conclusion from devil's advocate:** The `.unwrap()` is the only finding that could cause real runtime damage. It's Medium severity because the test suite would catch most divergence scenarios, but it should be fixed. The unvalidated resource/SFX paths are by design and documented by the Architect. No new findings from this exercise beyond what was already identified.

### Tags Coverage
[EDGE] No edge-hunter findings (disabled). [SILENT] `.unwrap()` at parser:175 confirmed. [TEST] No test-analyzer findings (disabled). [DOC] No comment-analyzer findings (disabled). [TYPE] ToolCallResults pub fields dismissed (pattern-consistent); VALID_EVENT_TYPES sync noted. [SEC] No security findings (disabled). [SIMPLE] No simplifier findings (disabled). [RULE] Rule #1 violation confirmed (unwrap on LLM-adjacent path).

**Data flow traced:** LLM prose + tool calls → sidecar JSONL → `parse_tool_results` → `ToolCallResults` → `assemble_turn` → `ActionResult` → dispatch pipeline. Safe because: validation at tool call time (personality_event) or tool script time (resource_change, play_sfx), OTEL spans on all paths, override semantics prevent stale narrator fallback.

**Pattern observed:** Consistent with stories 20-2 through 20-6 — same Option/unwrap_or override semantics, same private-fields-with-getters on result types, same tracing instrumentation pattern.

**Error handling:** Validation errors return Result::Err, parser arms log warnings and increment skipped_count. One exception: the `.unwrap()` at parser:175 (finding above).

**Review findings:** parser bypasses validation for resource_change/play_sfx (architectural — documented by Architect), `.unwrap()` on serde round-trip (Medium, non-blocking)

**Handoff:** To Vizzini (SM) for finish-story

## Sm Assessment

Final reactive tool batch in Epic 20's crunch separation arc. Three low-frequency tools (personality_event, resource_change, play_sfx) follow the identical pattern established in 20-2 through 20-6: narrator calls tool → tool validates → assemble_turn collects result into ActionResult. Context file is thorough, ACs are clear. No blockers. Straight to Fezzik for RED phase.