---
story_id: "16-9"
jira_key: "none"
epic: "16"
workflow: "tdd"
---
# Story 16-9: Confrontation UI — generic encounter display with genre theming

## Story Details
- **ID:** 16-9
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Epic:** 16 — Genre Mechanics Engine — Confrontations & Resource Pools
- **Repository:** sidequest-ui
- **Branch:** feat/16-9-confrontation-ui
- **Points:** 5
- **Priority:** p1
- **Status:** in-progress

## Context

The server sends StructuredEncounter data (from Epic 16 stories 16-2 through 16-7). The UI needs a single ConfrontationOverlay component that renders any confrontation type with genre-appropriate visual treatment.

## Acceptance Criteria

1. ConfrontationOverlay component renders for any confrontation type
2. Metric bar displays with genre-themed colors/styling
3. Available beats render as action buttons
4. Actor portraits display
5. Secondary stats render when present
6. Standoff type gets letterbox framing + extreme close-up portraits
7. Chase type delegates to existing chase visualization
8. Combat type keeps current CombatOverlay layout
9. Component reads confrontation type and genre theme for visual treatment

## Workflow Phases

| Phase | Owner | Status |
|-------|-------|--------|
| setup | sm | complete |
| red | tea | in-progress |
| green | dev | pending |
| review | reviewer | pending |
| finish | sm | pending |

## Workflow Tracking

**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-04-05T09:45Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05T09:45Z | 2026-04-05T09:45Z | 0m |
| red | 2026-04-05T09:45Z | — | — |

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings yet.

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations yet.
