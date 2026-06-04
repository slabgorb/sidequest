---
story_id: "71-29"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 71-29: intent_router degrade path doesn't persist decompose spans to turn_telemetry (GM-panel blind on degraded turns)

## Story Details
- **ID:** 71-29
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** implement
**Phase Started:** 2026-06-04T00:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T00:00:00Z | 2026-06-04T00:00:00Z | - |
| implement | 2026-06-04T00:00:00Z | - | - |

## Story Context

### Problem Statement
The intent_router (ADR-113 intent router / ADR-123 mechanical-engagement pipeline) has a "degrade" path — when the router degrades (falls back), it apparently does NOT persist its decompose spans to turn_telemetry, so the GM panel is blind to what happened on degraded turns.

### Technical Task
1. Locate the intent_router degrade path
2. Compare to the happy path's decompose-span persistence
3. Identify why spans aren't persisted on degrade
4. Persist decompose spans to turn_telemetry on the degrade path (mirroring the happy path)

### Acceptance Criteria
- Degrade path persists decompose spans to turn_telemetry
- A test asserts the spans are present after a degraded turn
- OTEL watcher event coverage confirmed
- ruff clean
- Existing tests pass

### Branch Strategy
gitflow (feat/71-29-degrade-decompose-spans-telemetry)

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
