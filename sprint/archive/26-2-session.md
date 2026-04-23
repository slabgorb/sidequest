---
story_id: "26-2"
jira_key: "none"
epic: "26"
workflow: "trivial"
---

# Story 26-2: Wire exercise_tracker into orchestrator dispatch

## Story Details

- **ID:** 26-2
- **Jira Key:** none (personal project)
- **Epic:** 26 — Wiring Audit Remediation
- **Workflow:** trivial (phased: setup → implement → review → finish)
- **Points:** 3
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-04-06T07:00:00Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-06T07:00:00Z | - | - |

## Delivery Findings

No upstream findings.

## Design Deviations

None yet.

## Implementation Notes

### Module Status

The `exercise_tracker` module exists fully implemented in `sidequest-agents/src/exercise_tracker.rs`:
- 843 LOC total across unwired modules (exercise_tracker, entity_reference, session_restore, turn_reminder, guest_npc, scenario_archiver)
- Tracks agent invocation histogram: 8 expected agents (narrator, creature_smith, ensemble, troper, world_builder, dialectician, resonator, intent_router)
- Emits `tracing::info!()` summaries and coverage gap warnings
- Lives in watcher validator task (cold path)

### Wiring Points

1. **Orchestrator struct** — add `SubsystemTracker` field
2. **Orchestrator::new()** — instantiate tracker with default thresholds
3. **process_action()** — call `tracker.record(&agent_name)` after agent is determined
4. **turn_record_bridge()** — optional: emit tracker summaries as WatcherEvents

### Current Code Path

- Orchestrator receives TurnRecord with `agent_name` field (line 50 in turn_record.rs)
- turn_record_bridge (main.rs:113) receives the record and broadcasts as WatcherEvent
- Exercise tracker should hook into this cold path to accumulate invocation counts
