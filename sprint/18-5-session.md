---
story_id: "18-5"
jira_key: ""
epic: "18"
workflow: "tdd"
---
# Story 18-5: Structured NPC Registry and Inventory Panels in State Tab

## Story Details
- **ID:** 18-5
- **Jira Key:** (personal project, not tracked)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p1

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-01T03:45:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-01T03:45:00Z | - | - |

## Story Context

The State tab currently dumps `GameState` as raw JSON, which is unreadable for NPCs and inventory. The game's entity model is fully implemented:

- **NPCs:** NpcInstance structs in game state, tracked by NPC ID with attributes (name, location, state)
- **Inventory:** Character inventory, equipment slots, item conditions — all modeled in GameState

The UI receives `GameStateSnapshot` events via OTEL (wired in 18-2). This story converts those snapshots into structured tables:

1. **NPC Registry Panel** — table showing all NPCs: ID, Name, Location, State, Attributes
2. **Inventory Panel** — table showing equipment/items: Slot, Item Name, Condition, Properties

This is a visualization-only story — the data model is ready, just needs UI representation.

### Acceptance Criteria
1. State tab has "NPC Registry" and "Inventory" subtabs
2. NPC Registry shows table with: ID | Name | Location | State | (expandable attributes)
3. Inventory shows table with: Slot | Item | Condition | Weight | (expandable properties)
4. Search/filter works on both tables (by NPC name, item name)
5. Tables handle empty state gracefully (no NPCs, empty inventory)
6. OTEL events flow correctly to dashboard (events already emitted from backend, just need UI to render)

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
