---
story_id: "11-4"
jira_key: "none"
epic: "11"
workflow: "tdd"
---

# Story 11-4: Lore injection into agent prompts

## Story Details

- **ID:** 11-4
- **Title:** Lore injection into agent prompts — relevant lore fragments included in narrator/world state context
- **Points:** 3
- **Priority:** P1
- **Workflow:** tdd
- **Stack Parent:** none (depends on 11-2, 11-3 — both merged)
- **Target Repo:** sidequest-api (Rust)
- **Target File:** crates/sidequest-game/src/lore.rs

## Story Requirements

Implement lore injection to include relevant lore fragments in agent prompts for:
- Narrator agent (world narration)
- World state agent (dynamic event generation)

### Selection Logic

- Select relevant lore fragments for inclusion in agent prompts
- Respect a token budget — only include fragments that fit within the budget
- Prioritize fragments by relevance:
  - Category matching (context_hint points to a category)
  - Recency (turn_created — newer fragments weighted higher)
  - Keyword relevance (content matching context keywords)
- Format selected fragments as a context block for prompt injection

### Function Signatures (TDD target)

```rust
/// Select relevant lore fragments for prompt injection within a token budget.
///
/// Prioritizes fragments by:
/// 1. Category match (if context_hint matches a category)
/// 2. Recency (newer turn_created values first)
/// 3. Keyword relevance (content matching context_hint keywords)
///
/// Only includes fragments whose token estimates fit within the remaining budget.
pub fn select_lore_for_prompt(
    store: &LoreStore,
    budget: usize,
    context_hint: Option<&str>,
) -> Vec<&LoreFragment>

/// Format selected lore fragments as a context block for prompt injection.
///
/// Returns a formatted string like:
/// ```
/// === RELEVANT LORE ===
/// [Category: History]
/// {fragment content}
///
/// [Category: Geography]
/// {fragment content}
/// ...
/// ```
pub fn format_lore_context(fragments: &[&LoreFragment]) -> String
```

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-27 21:10 UTC

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27 21:10 | - | - |

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Context Files

See `.session/11-4-context.md` for implementation notes.

## Related Stories

- **11-1** (LoreFragment model) — merged ✓
- **11-2** (LoreStore) — merged ✓
- **11-3** (Lore seed) — merged ✓
- **11-5** (Lore accumulation) — depends on this story
- **11-6** (Semantic retrieval) — depends on 11-2, complements this story
