---
story_id: "20-6"
jira_key: ""
epic: "20"
epic_title: "Narrator Crunch Separation — Tool-Based Mechanical Extraction"
workflow: "tdd"
---

# Story 20-6: quest_update tool — quest state transitions

## Story Details

- **ID:** 20-6
- **Epic:** 20 (Narrator Crunch Separation — ADR-057)
- **Jira Key:** N/A (personal project)
- **Workflow:** tdd
- **Story Points:** 3
- **Priority:** p2
- **Stack Parent:** none (Phase 5 of 8-phase migration)
- **Repos:** sidequest-api
- **Branch:** feat/20-6-quest-update-tool

## Overview

**Phase 5 of ADR-057:** Replace the narrator's `quest_updates` JSON field with a typed `quest_update` tool call.

Currently, the narrator emits quest state transitions as a JSON object block:
```json
{
  "quest_updates": {
    "The Corrupted Grove": "completed: the source was purified",
    "Find the Artifact": "active: searching in the Shadow Caves (from: Mage Council)"
  }
}
```

This mashes two concerns: intent interpretation (the LLM decides THAT a quest changed) and structured formatting (the crunch of formatting status strings). ADR-057 separates them:

1. **Narrator continues deciding what quests changed** — that's intent judgment.
2. **Narrator calls `quest_update` tool** with quest name and new status string.
3. **Tool returns a structured `QuestUpdate`** with validated data.
4. **`assemble_turn` collects quest updates** from tool calls into `ActionResult.quest_updates` HashMap.

The narrator's behavioral rule (never send player back to quest giver) remains in the prompt — it's intent, not crunch.

This follows the pattern established by Phases 2-4 (scene_mood, scene_intent, item_acquire, merchant_transact, lore_mark).

## Acceptance Criteria

1. **Tool implementation:** Create `crate::tools::quest_update` module (quest_update.rs).
   - Input struct: `QuestUpdateInput` with quest_name (String) and status (String).
   - Validation: quest_name must be non-empty, status must be non-empty.
   - Format validation: status follows the expected format: `"active: description (from: NPC)"`, `"completed: outcome"`, `"failed: reason"` — or free-form if the narrator prefers. **No format enforcement** — just non-empty.
   - Output: `sidequest_protocol::QuestUpdate` struct with quest_name and status.
   - OTEL: tracing instrumentation on success/failure.

2. **Integration into `ToolCallResults`:**
   - Add `quest_updates: Option<HashMap<String, String>>` field to `ToolCallResults`.
   - Update `assemble_turn` to collect quest_updates from tool calls into the result HashMap.
   - **RULE:** No silent fallback. Same semantics as items/merchants (20-3):
     - If tool fires (Some), tool updates WIN — even if empty HashMap.
     - If tool doesn't fire (None), result is empty — narrator extraction discarded.

3. **Narrator prompt update (deferred, Phase 8):**
   - For Phase 5, the narrator still uses the old JSON-block protocol.
   - In Phase 8 (story 20-8), the quest update JSON schema will be removed from the narrator prompt.
   - The referral rule ("never send player back to quest giver") remains in Phase 5 — it's behavioral, not crunch.
   - For now, narrator emits both tool calls AND JSON block updates. `assemble_turn` uses tool results.

4. **Tests:**
   - Unit tests for quest_update validation covering non-empty name/status.
   - Test invalid inputs: empty quest_name, empty status.
   - Integration test: verify tool results flow through `assemble_turn` and override narrator extraction.
   - Wiring test: verify `quest_update` module is imported and used in production code path.

5. **OTEL coverage:**
   - Every tool call emits a span with `tool.quest_update` name.
   - On success: fields `quest_name`, `status_len`.
   - On failure: `valid = false`, error message.

6. **No silent fallbacks:**
   - If quest_name is empty, return `Err`, not a default.
   - If status is empty, return `Err`, not a default.

## Scope

### In
- Tool function `quest_update::update_quest()`.
- Input validation logic (non-empty checks).
- OTEL instrumentation.
- Unit tests for validation logic.
- Integration test verifying tool output flows to `ActionResult.quest_updates`.
- Wiring verification.

### Out (Phase 8)
- Narrator prompt updates (story 20-8).
- Removal of old JSON quest block from extraction.
- Deletion of `extractor.rs` (story 20-8).

## Technical Context

### Related Files

**Tools (Phase 2-4 patterns):**
- `/Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-agents/src/tools/set_mood.rs` — Simple enum validation pattern.
- `/Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-agents/src/tools/item_acquire.rs` — Richer struct input, validation, OTEL.
- `/Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-agents/src/tools/lore_mark.rs` — String validation with enum mapping, OTEL.
- `/Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-agents/src/tools/assemble_turn.rs` — `ToolCallResults` merging logic.

**Quest infrastructure:**
- `/Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-protocol/src/message.rs` — `QuestUpdate` struct (if exists) or needs definition.
- `/Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-game/src/state/quest.rs` — Quest state management (reference).
- `/Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-agents/src/agents/narrator.rs` — Current quest_updates protocol.

### QuestUpdate Type

The tool accepts quest_name and status strings and returns a `QuestUpdate` struct. This may need to be added to `sidequest-protocol/src/message.rs` if it doesn't exist:

```rust
pub struct QuestUpdate {
    pub quest_name: String,
    pub status: String,  // "active: ...", "completed: ...", "failed: ...", or freeform
}
```

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T15:05:18Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T15:05:18Z | - | - |

## Sm Assessment

Story 20-6 follows the established tool-call pattern from Phases 2-4. Session has clear ACs, scope boundaries (Phase 8 handles prompt removal), and technical references to all four prior tool implementations. Branch created on API develop. No blockers — well-grooved pattern.

**Routing:** TDD → TEA (red phase) writes failing tests first.

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->
