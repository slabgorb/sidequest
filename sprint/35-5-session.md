---
story_id: "35-5"
jira_key: ""
epic: "MSSCI-16932"
workflow: "tdd"
---
# Story 35-5: Wire turn_reminder into barrier creation — spawn async reminder task

## Story Details
- **ID:** 35-5
- **Epic:** MSSCI-16932 (Wiring Remediation II — Unwired Modules, OTEL Blind Spots, Dead Code)
- **Jira Key:** TBD
- **Workflow:** tdd
- **Points:** 5
- **Stack Parent:** none
- **Repos:** api

## Story Context

The `turn_reminder` module is fully implemented in the API codebase but has zero production consumers. This story wires it into barrier creation so it becomes operational.

**Context:**
- `turn_reminder.rs` (161 LOC) in sidequest-game crate — fully tested with story 8-9 tests
- `TurnBarrier` created in two locations: `sidequest-server/src/dispatch/connect.rs` and `sidequest-server/src/lib.rs`
- `ReminderConfig` + `ReminderResult` types exist and are production-ready
- `run_reminder()` is an async function that sleeps for threshold duration, then checks idle players

**Acceptance Criteria:**
1. After `TurnBarrier::new()` in both production locations, spawn async reminder task via `tokio::spawn`
2. Reminder task calls `ReminderResult::run_reminder()` with barrier timeout, config (load from genre pack or default), session Arc, and turn mode
3. OTEL watcher events emitted: "reminder_spawned", "reminder_fired" (with idle_player_count)
4. Integration test verifies turn_reminder has a non-test consumer in production code paths (sidequest-server dispatch or session setup)
5. No silent fallbacks; fail loudly if turn_reminder config is missing from genre pack

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-09

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-09 | - | - |

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
