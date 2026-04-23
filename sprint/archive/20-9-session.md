---
story_id: "20-9"
jira_key: ""
epic: "20"
workflow: "tdd"
---

# Story 20-9: Wire assemble_turn into dispatch pipeline

## Story Details
- **ID:** 20-9
- **Title:** Wire assemble_turn into dispatch pipeline
- **Jira Key:** (Personal project — no Jira)
- **Epic:** 20 — Narrator Crunch Separation — Tool-Based Mechanical Extraction (ADR-057)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Type:** refactor
- **Stack Parent:** none
- **Split From:** 20-8 (story 20-8 was split to prioritize tool wiring)

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T19:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T19:00Z | - | - |

## Business Context

This is a connectivity/integration story, not a feature story. The `assemble_turn` function was built in story 20-1 to collect tool call results and merge them with narrator extraction. Currently it exists in the code but is **never called** — the orchestrator still builds ActionResult directly from the narrator extraction without using assemble_turn as an intermediary.

**Why now?** Story 20-10 (tool call parsing) will produce ToolCallResults and feed them into assemble_turn. Before that lands, we need to ensure the dispatch pipeline calls assemble_turn so tool results actually reach the game.

This is a "no op" refactoring: with ToolCallResults::default() (no tools fired), assemble_turn produces an identical ActionResult to what the orchestrator currently builds directly. After this wiring lands, 20-10 can add tool result population without worrying about whether dispatch calls it.

## Technical Context

### Current Wiring (20-1 Baseline)

From `/sidequest-api/crates/sidequest-agents/src/orchestrator.rs`:

- **Line 630:** Extraction happens: `let extraction = extract_structured_from_response(raw_response);`
- **Lines 704-730:** ActionResult is built **directly from extraction**, filling fields line-by-line.
- **assemble_turn module exists** (`src/tools/assemble_turn.rs`) but is never imported or called in orchestrator.
- **action_rewrite and action_flags** currently come from narrator JSON block (extraction fields), not from a preprocessor.

### What Needs to Change

1. **Import assemble_turn module** into orchestrator.rs (currently exists but not public-facing).
2. **Call assemble_turn()** to build ActionResult, replacing the direct field-by-field construction (lines 704-730).
3. **No changes needed to:**
   - The ActionResult struct itself
   - How action_rewrite/action_flags are currently extracted (still from JSON in 20-9)
   - Any dispatch/server code (assemble_turn is transparent to consumers)

### ToolCallResults Placeholder

For 20-9, ToolCallResults::default() passes through. All fields are None, so assemble_turn falls back to narrator extraction for scene_mood/scene_intent. Footnotes return empty (no tool fired), per the no-fallback rule documented in assemble_turn.rs.

This is **safe for 20-9** because:
- No tools are wired yet (story 20-2 adds mood/intent tools, but those stories are still in backlog).
- assemble_turn with default ToolCallResults produces identical output to current orchestrator behavior.
- Tests will verify the no-op is correct.

### Story 20-1 Success Criteria (Reference)

From context-story-20-1.md, AC-6 (footnotes handling):

> "footnotes: Tool call wins, NO fallback to narrator extraction. Same no-fallback semantics as items/merchants. If tool fired (Some), use its value (even if empty vec). If tool didn't fire (None), result is empty — narrator footnotes are discarded."

For 20-9, since no tools fire yet, narration footnotes will be discarded (assemble_turn.rs warns about this). This is correct per spec — story 20-4 will wire the lore_mark tool that populates footnotes via ToolCallResults.

## Acceptance Criteria

1. **assemble_turn is imported** and callable from orchestrator.rs (no longer dead code).
2. **ActionResult is built via assemble_turn()**, not via direct field construction.
3. **Current behavior unchanged** — ActionResult fields have identical values to pre-20-9 (assemble_turn with default ToolCallResults is a no-op).
4. **Tests pass** — existing unit and integration tests all pass without modification.
5. **OTEL events preserved** — no regression in observability (ToolCallResults has no side effects for OTEL).
6. **Wiring verified** — non-test consumers (dispatch pipeline) call process_action(), which calls orchestrator.process_action(), which calls assemble_turn().

## Risk & Mitigations

**Risk:** Footnotes will be discarded in 20-9 (no lore_mark tool yet). Narrator's JSON footnotes field ignored.
- **Mitigation:** Document in story 20-4 context that footnotes were deferred to tool call wiring. Add warning in assemble_turn (already present).
- **Severity:** Non-blocking — footnotes aren't used in gameplay until story 9-11 integration is verified.

**Risk:** Preprocessor fields (action_rewrite/action_flags) are still coming from narrator JSON, not from a preprocessor.
- **Mitigation:** That's story 20-1 work (split into 20-1 infrastructure + 20-9 wiring). Preprocessor population is future work.
- **Severity:** Non-blocking — 20-1 built the infrastructure, 20-9 wires dispatch, preprocessor wiring is a later story.

## Delivery Findings

No upstream findings.

## Design Deviations

None (implementation matches ADR-057 design).
