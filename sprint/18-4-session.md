---
story_id: "18-4"
jira_key: ""
epic: "18"
workflow: "tdd"
---
# Story 18-4: LoreStore Browser Tab with Per-Turn Budget Visualization

## Story Details
- **ID:** 18-4
- **Jira Key:** (personal project, not tracked)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 5
- **Priority:** p1

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-01T00:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-01T00:00:00Z | - | - |

## Story Context
The LoreStore (lore.rs, 2,746 LOC) is the game's knowledge base — every place, NPC, event, faction, and item the narrator knows about. Each turn, `select_lore_for_prompt()` selects fragments within a token budget for the Claude prompt. Currently there's zero visibility into what's in the store, what gets selected, and what gets cut. This is the primary tool for catching "Claude is winging it" — if a relevant fact exists in the store but wasn't selected, the narrator literally can't reference it.

### Acceptance Criteria
1. Lore tab appears in dashboard tab bar
2. Browser view shows all LoreFragments with search and category filter
3. Budget view shows selected vs rejected fragments per turn with token counts
4. Budget bar visually shows tokens_used / budget_tokens ratio
5. Events flow — `lore_selection` events visible in Console tab
6. No performance regression — lore event emission doesn't slow turn processing

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
