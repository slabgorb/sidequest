---
story_id: "20-6"
jira_key: "none"
epic: "20"
workflow: "tdd"
---
# Story 20-6: quest_update tool — quest state transitions

## Story Details
- **ID:** 20-6
- **Epic:** 20 (Narrator Crunch Separation — Tool-Based Mechanical Extraction / ADR-057)
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p2

## Story Description

Add the `quest_update` tool for quest state transitions. This is part of ADR-057's narrator decoupling architecture — replacing the narrator's monolithic JSON output block with discrete tool calls.

The quest_update tool validates quest state transitions and extracts them via structured tool calls, rather than relying on regex extraction from the narrator's JSON block.

This story follows the established pattern in 20-2 (scene_mood/scene_intent tools) and 20-4 (lore_mark tool).

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-02T15:54:27Z 11:05 UTC
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02 | 2026-04-02T15:08:48Z | 15h 8m |
| red | 2026-04-02T15:08:48Z | 2026-04-02T15:13:11Z | 4m 23s |
| green | 2026-04-02T15:13:11Z | 2026-04-02T15:24:34Z | 11m 23s |
| spec-check | 2026-04-02T15:24:34Z | 2026-04-02T15:29:02Z | 4m 28s |
| verify | 2026-04-02T15:29:02Z | 2026-04-02T15:32:38Z | 3m 36s |
| review | 2026-04-02T15:32:38Z | 2026-04-02T15:41:16Z | 8m 38s |
| red | 2026-04-02T15:41:16Z | 2026-04-02T15:43:22Z | 2m 6s |
| green | 2026-04-02T15:43:22Z | 2026-04-02T15:49:16Z | 5m 54s |
| review | 2026-04-02T15:49:16Z | 2026-04-02T15:54:27Z | 5m 11s |
| finish | 2026-04-02T15:54:27Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Architect (spec-check)
- **Gap** (non-blocking): prompt.rs:232 still tells narrator to use quest_updates JSON block, contradicting the migration. Affects `crates/sidequest-server/src/dispatch/prompt.rs` (remove or reword quest_updates reference). *Found by Architect during spec-check.*

### TEA (test verification)
- No upstream findings during test verification.

### Reviewer (code review)
- **Gap** (blocking): tool_call_parser.rs:140 bypasses validate_quest_update — LLM strings inserted raw into quest_updates HashMap. Affects `crates/sidequest-agents/src/tools/tool_call_parser.rs` (call validate_quest_update in quest_update branch). *Found by Reviewer during code review.*

### Dev (rework implementation)
- No upstream findings during rework implementation.

### Reviewer (re-review)
- No upstream findings during re-review.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- TEA "No deviations" → ✓ ACCEPTED by Reviewer: test design matches ACs correctly.
- Dev "No deviations" → ✗ FLAGGED by Reviewer: tool_call_parser bypasses validate_quest_update — this is an undocumented deviation from the pattern established by scene_render (which calls validate_scene_render). Should have been logged as a deviation from the sibling story pattern.

### TEA (rework test design)
- No deviations from spec.

### Dev (rework implementation)
- No deviations from spec.

### Reviewer (re-review audit)
- TEA rework "No deviations" → ✓ ACCEPTED by Reviewer: rework tests match reviewer findings.
- Dev rework "No deviations" → ✓ ACCEPTED by Reviewer: fixes match exactly what was requested.

## Sm Assessment

Story 20-6 is set up and ready for TDD red phase. Follows the established tool-based extraction pattern from 20-2, 20-4, 20-5. API repo branch `feat/20-6-quest-update-tool` created from `develop`. No Jira (personal project). No blockers identified.

**Routing:** → Fezzik (TEA) for red phase — write failing tests for quest_update tool.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New tool module with 5 ACs requiring unit, integration, and wiring tests

**Test Files:**
- `crates/sidequest-agents/tests/quest_update_story_20_6_tests.rs` — 30 tests covering all ACs

**Tests Written:** 30 tests covering 5 ACs
**Status:** RED (failing — ready for Dev)

**Compilation Errors:**
- 1 unresolved import (`sidequest_agents::tools::quest_update` — module doesn't exist)
- 8 missing field errors (`ToolCallResults` has no `quest_updates` field)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent errors | validate rejects empty/whitespace (no `.ok()` in tool) | failing |
| #5 validated constructors | `validate_quest_update_rejects_empty_name`, `_rejects_empty_status`, `_rejects_whitespace_*` | failing |
| #6 test quality | Self-check: all 30 tests have meaningful `assert_eq!`/`assert!` with value checks | pass |
| #8 Deserialize bypass | `quest_update_serializes_to_json` — Serialize tested, Deserialize not needed (tool produces, never consumes) | n/a |
| #9 public fields | `quest_update_struct_is_exported` — QuestUpdate fields accessed directly (simple DTO, no invariants) | failing |

**Rules checked:** 5 of 15 applicable lang-review rules have test coverage (remaining are implementation-phase concerns: tracing, workspace deps, etc.)
**Self-check:** 0 vacuous tests found

**Handoff:** To Inigo Montoya (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-agents/src/tools/quest_update.rs` — new module: validate_quest_update(), QuestUpdate struct, OTEL spans
- `crates/sidequest-agents/src/tools/mod.rs` — register quest_update module
- `crates/sidequest-agents/src/tools/assemble_turn.rs` — add quest_updates to ToolCallResults, wire override logic
- `crates/sidequest-agents/src/tools/tool_call_parser.rs` — add quest_update branch (accumulates into HashMap)
- `crates/sidequest-agents/src/agents/narrator.rs` — remove QUEST PROTOCOL, keep REFERRAL RULE, remove quest_updates from JSON block
- `crates/sidequest-agents/tests/scene_render_story_20_5_tests.rs` — fix for new ToolCallResults field

**Tests:** 31/31 passing (GREEN), full sidequest-agents suite 0 failures
**Branch:** feat/20-6-quest-update-tool (pushed)

**Handoff:** To next phase (verify or review)

## Dev Assessment (rework)

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-agents/src/tools/quest_update.rs` — fields made private, added getters
- `crates/sidequest-agents/src/tools/tool_call_parser.rs` — replaced raw insert with validate_quest_update() call
- `crates/sidequest-agents/tests/quest_update_story_20_6_tests.rs` — struct literal → validator, field access → getters

**Tests:** 37/37 passing (GREEN), full sidequest-agents suite 0 failures
**Branch:** feat/20-6-quest-update-tool (pushed)

**Handoff:** To next phase

## Architect Assessment (spec-check)

**Spec Alignment:** Minor drift detected
**Mismatches Found:** 1

- **prompt.rs still references quest_updates JSON block** (Missing in code — Behavioral, Minor)
  - Spec: context-story-20-6.md AC-3 says "Narrator prompt keeps referral rule but removes quest JSON schema"
  - Code: `narrator.rs` correctly removes QUEST PROTOCOL, but `sidequest-server/src/dispatch/prompt.rs:232` still injects "Update quest status in quest_updates when objectives change" into the state summary. This contradicts the migration by telling the narrator to use the old JSON block approach.
  - Recommendation: **B — Fix code.** Remove or reword the quest_updates reference in prompt.rs. The narrator should no longer emit quest_updates in JSON. Suggest: "Quest state changes are handled via the quest_update tool." or remove the line entirely since the referral rule in the system prompt covers intent.

**Decision:** Fixed directly — updated prompt.rs:232 to reference quest_update tool instead of JSON block. Committed as `8f017e1`. Proceed to review.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 6 findings | 2 high (false positive + out-of-scope test fixture dup), 2 medium (flagged), 2 low (dismissed) |
| simplify-quality | 1 finding | 1 high (false positive — scene_render.rs exists, agent couldn't find it) |
| simplify-efficiency | clean | No unnecessary complexity detected |

**Applied:** 0 high-confidence fixes (all high-confidence findings were false positives or out-of-scope)
**Flagged for Review:** 2 medium-confidence findings (NarratorExtraction builder pattern, tool_call_parser field extraction DRY)
**Noted:** 3 low-confidence observations (dismissed)
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** Tests 31/31 passing. Clippy clean on changed crates (pre-existing warnings in sidequest-genre only).
**Handoff:** To Westley (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (clippy issues pre-existing in sidequest-genre) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 | confirmed 1 |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 4 | confirmed 2, dismissed 2 |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 3, dismissed 1 |

**All received:** Yes (4 returned, 5 disabled via settings)
**Total findings:** 4 confirmed (3 unique — parser bypass is root cause of 3), 2 dismissed (with rationale)

### Finding Triage

**Confirmed:**
1. [SILENT][TYPE][RULE] **tool_call_parser bypasses validate_quest_update** — `tool_call_parser.rs:140`. Raw LLM strings inserted without validation. Fixes OTEL gap too (AC-5). Three subagents converged independently.
2. [RULE] **Missing wiring test for parse_tool_results quest_update branch** — `quest_update_story_20_6_tests.rs:517`. Test only serializes a ToolCallRecord; never calls parse_tool_results() with a sidecar file.
3. [TYPE][RULE] **QuestUpdate pub fields bypass validation invariants** — `quest_update.rs:13`. Post-construction mutation defeats trim/non-empty enforcement.

**Dismissed:**
- InvalidQuestUpdate inner field visibility (type-design, low confidence) — tuple struct field is private by default in Rust; the `pub struct` makes the type public, not the field. The `(String)` field is already module-private. No bypass possible from outside the module.
- Primitive obsession on HashMap<String, String> (type-design, low) — matches existing ActionResult.quest_updates type used across 5+ files; changing it is a cross-cutting refactor beyond this story's scope.
- Workspace dep compliance for tempfile (rule-checker, #11) — pre-existing, not introduced by this diff.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | [SILENT][TYPE][RULE] Parser bypasses validate_quest_update — LLM strings inserted raw, OTEL spans never fire | `tool_call_parser.rs:140` | Replace raw insert with `match validate_quest_update(quest_name, status)` mirroring scene_render pattern |
| [MEDIUM] | [RULE] Missing wiring test — tool_call_parser_recognizes_quest_update never exercises parse_tool_results() | `quest_update_story_20_6_tests.rs:517` | Write sidecar JSONL file, call parse_tool_results(), assert quest_updates HashMap populated |
| [MEDIUM] | [TYPE][RULE] QuestUpdate pub fields allow post-construction mutation bypassing validated invariants | `quest_update.rs:13` | Make quest_name/status private, add getters; update test that constructs directly |

### Rule Compliance

| Rule | Instances | Compliant | Violation |
|------|-----------|-----------|-----------|
| #1 silent errors | 5 | 5 | 0 |
| #2 non_exhaustive | 0 enums | N/A | 0 |
| #3 placeholders | 3 | 3 | 0 |
| #4 tracing | 4 | 4 | 0 |
| #5 constructors at trust boundary | 2 | 1 | 1 (parser bypass) |
| #6 test quality | 23 | 22 | 1 (wiring test gap) |
| #7 unsafe casts | 0 in diff | N/A | 0 |
| #8 Deserialize bypass | 1 | 1 | 0 |
| #9 public fields | 2 | 1 | 1 (QuestUpdate) |
| #10 tenant context | 0 traits | N/A | 0 |
| #11 workspace deps | 1 | 0 | 1 (pre-existing) |
| #12 dev-deps | 5 | 5 | 0 |
| #13 constructor consistency | 1 | 1 | 0 |
| #14 fix regressions | 3 | 3 | 0 |
| #15 unbounded input | 2 | 2 | 0 |

### Data Flow Traced
Quest name string: LLM tool call → sidecar JSONL → tool_call_parser → ToolCallResults.quest_updates → assemble_turn → ActionResult.quest_updates → state_mutations.rs → GameState. **Gap at parser**: no validation between sidecar read and HashMap insert.

### Devil's Advocate

What if the LLM emits a quest_update tool call with `quest_name: ""` or `quest_name: "   "`? The sidecar JSONL will have a non-null string, so `record.result.get("quest_name").and_then(|v| v.as_str())` returns `Some("")` — the `if let (Some, Some)` guard passes. An empty-string key gets inserted into the HashMap. Downstream in `state_mutations.rs:347`, the loop iterates over quest_updates and applies them to GameState. An empty quest name becomes a phantom entry in the quest log — visible to the player, impossible to reference by name, and never completable. Worse: `audio.rs:31` checks `quest_updates.values().any(|v| v.starts_with("completed"))` — a phantom quest with status "completed: " triggers the quest-completion audio cue for a quest the player never had. The validator exists precisely to prevent this. It trims whitespace, rejects empty strings, and emits OTEL spans so the GM panel can see what happened. But it's never called on the production path.

What if two quest_update tool calls arrive for the same quest name with different statuses? The HashMap `insert` overwrites — last write wins. This is actually correct behavior (the latest status should win), but without the validator's OTEL spans, the GM panel has no visibility into which update won.

What about the pub fields on QuestUpdate? A caller does `let mut u = validate_quest_update("Valid", "active: thing").unwrap(); u.quest_name = String::new();` — the invariant is silently defeated. Today this only matters if someone constructs QuestUpdate directly in tests and that pattern spreads to production. The test at line 202 already demonstrates the bypass. Medium severity because the current production path (tool_call_parser) doesn't construct QuestUpdate at all (it bypasses the validator entirely — which is the worse bug).

**Handoff:** Back to Fezzik (TEA) for failing tests on the parser validation gap, then Inigo Montoya (Dev) for fixes.

## Subagent Results (re-review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (37/37 tests, full suite green) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean | 0 (original finding verified fixed) | N/A |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | error | 0 (permission error reading /tmp diff) | Covered by own analysis + rule-checker |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 (all 15 rules pass, 4 prior violations confirmed fixed) | N/A |

**All received:** Yes (4 returned, 5 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed

## Reviewer Assessment (re-review)

**Verdict:** APPROVED

**Previous findings resolution:**
- [SILENT][TYPE][RULE] Parser bypass → **FIXED** at `tool_call_parser.rs:145`: `validate_quest_update()` now called, Err branch warns+skips. [VERIFIED] — `tool_call_parser.rs:145-156` mirrors `scene_render` pattern exactly. Rule #5 compliant.
- [RULE] Missing wiring test → **FIXED**: 6 sidecar tests added (`parser_extracts_quest_update_from_sidecar` + 4 edge cases + e2e). [VERIFIED] — `quest_update_story_20_6_tests.rs:625-745` exercises `parse_tool_results()` with real JSONL files. Rule #6 compliant.
- [TYPE][RULE] QuestUpdate pub fields → **FIXED** at `quest_update.rs:13-17`: fields private, getters at lines 20-29. [VERIFIED] — `quest_update.rs:13` `quest_name: String` (no `pub`), getter at line 22. Rule #9 compliant.

**Data flow traced:** Quest name: LLM tool call → sidecar JSONL → `parse_tool_results` → `validate_quest_update` (trim + reject empty) → `ToolCallResults.quest_updates` → `assemble_turn` (unwrap_or narrator fallback) → `ActionResult.quest_updates` → `state_mutations.rs` → GameState. Validated at every trust boundary.
**Pattern observed:** Parser validation now mirrors scene_render pattern at `tool_call_parser.rs:145` — `match validate_fn(args) { Ok => insert, Err => warn+skip }`.
**Error handling:** Empty/whitespace quest names rejected with `warn!` + `skipped_count` increment. Missing JSON fields rejected with separate `warn!`. OTEL `#[instrument]` span fires on every call via the validator.
**[EDGE]** No findings (disabled). **[SILENT]** Clean — original finding fixed. **[TEST]** No findings (disabled). **[DOC]** No findings (disabled). **[TYPE]** Verified fixes manually — fields private, getters added. **[SEC]** No findings (disabled). **[SIMPLE]** No findings (disabled). **[RULE]** All 15 rules pass, 4 prior violations confirmed resolved.

**Handoff:** To Vizzini (SM) for finish-story