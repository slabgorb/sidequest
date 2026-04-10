---
story_id: "35-11"
jira_key: "MSSCI-35-11"
epic: "MSSCI-35"
workflow: "trivial"
---
# Story 35-11: Delete dead UI components — LayoutModeSelector, TurnModeIndicator

## Story Details
- **ID:** 35-11
- **Jira Key:** MSSCI-35-11
- **Epic:** MSSCI-35 — Wiring Remediation II
- **Workflow:** trivial
- **Type:** chore
- **Points:** 1
- **Repos:** sidequest-ui
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-04-10T13:34:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-10T13:34:00Z | - | - |

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

No design deviations.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Scope & Context

### Components to Delete
1. **LayoutModeSelector** (`src/components/LayoutModeSelector.tsx`) — No production consumers
2. **TurnModeIndicator** (`src/components/TurnModeIndicator.tsx`) — No production consumers

### Test File
- **`src/__tests__/layout-modes.test.tsx`** — References both components; will need updating or deletion after component removal

### Verification
- Grep confirms zero imports of these components in production code
- Only appear in their own definitions and test file
- Safe to remove without breaking any wiring
