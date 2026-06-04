---
story_id: "71-30"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 71-30: action_reveal.dropped_rate_limit also ephemeral — add to _EPHEMERAL_EVENT_TYPES (sibling of composing-storm fix)

## Story Details
- **ID:** 71-30
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
| setup | 2026-06-04T00:00:00Z | - | - |
| implement | 2026-06-04T00:00:00Z | - | - |

## Technical Approach

Find the `_EPHEMERAL_EVENT_TYPES` definition in sidequest-server (per ADR-132 ephemeral-event taxonomy). Add the event type `action_reveal.dropped_rate_limit` to that set, following the same pattern as the prior `composing-storm` fix. Write a membership test to verify the event is in the set.

## Acceptance Criteria

- Event type `action_reveal.dropped_rate_limit` is added to `_EPHEMERAL_EVENT_TYPES`
- Membership test passes and asserts the event is in the ephemeral set
- All existing tests pass
- Ruff lint check is clean (no new violations introduced)
- Branch created off develop: `feat/71-30-dropped-rate-limit-ephemeral`

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/telemetry/watcher_hub.py` - added `"action_reveal.dropped_rate_limit"` to `_EPHEMERAL_EVENT_TYPES` (line ~335)
- `sidequest-server/tests/telemetry/test_action_reveal_ephemeral_not_persisted.py` - added 2 tests (membership + seam: pushed-live-not-persisted), matching the composing sibling pattern

**Emit-site verification:** `sidequest/handlers/action_reveal.py:90` emits the literal `"action_reveal.dropped_rate_limit"` via `_watcher_publish(...)` — exact match, no discrepancy.

**Tests:** 12/12 passing (GREEN) — `test_action_reveal_ephemeral_not_persisted.py` + `test_action_reveal_otel.py`
**Ruff:** clean (All checks passed!)
**Branch:** feat/71-30-dropped-rate-limit-ephemeral (NOT committed — SM handles git)

**Handoff:** To review

## Design Deviations

No deviations recorded.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
