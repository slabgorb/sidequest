---
story_id: "11-9"
jira_key: "none"
epic: "epic-11"
workflow: "tdd"
---
# Story 11-9: Narrator name injection

## Story Details
- **ID:** 11-9
- **Epic:** Epic 11 (Conlang System)
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** 11-7 (Morpheme glossary) and 11-8 (Name bank generation) — both merged
- **Points:** 2
- **Priority:** P1

## Story Description

Load a NameBank for the current genre pack's language and format name bank entries for inclusion in narrator prompts so NPC and location names feel linguistically consistent.

The narrator name injection system should:
- Load a NameBank for the current genre pack's language
- Format name bank entries for inclusion in narrator prompts
- Provide a function like `format_name_bank_for_prompt(bank: &NameBank, max_names: usize) -> String`
- Output should list available names with their glosses so the narrator can use linguistically consistent names
- Include a section header and formatted entries suitable for prompt injection
- Respect a max_names limit to control prompt size

Target: extend the conlang module in `crates/sidequest-game/src/conlang.rs`

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-27T20:30:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T20:30:00Z | - | - |

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
