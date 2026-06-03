---
story_id: "76-5"
jira_key: ""
epic: "76"
workflow: "trivial"
---
# Story 76-5: Entity-only-turn embed telemetry precision

## Story Details
- **ID:** 76-5
- **Jira Key:** (none — project does not use Jira)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Repos:** sidequest-server
**Phase:** implement
**Phase Started:** 2026-06-03T12:12:50Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T12:12:50Z | 2026-06-03T12:12:50Z | 0m |

## Delivery Findings

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings.

## Design Deviations

No deviations yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/dispatch/lore_embed.py` — added `entity_pending` to both the `lore_embedding.completed` watcher event (sourced from a new `entity_pending_count` param threaded from `dispatch_worker`) and the `lore_embedding.dispatch_skipped` span + `skipped` watcher event (computed inline from `sd.entity_store.pending_embedding_ids`).
- `tests/server/dispatch/test_lore_embed.py` — added `test_run_worker_completed_event_surfaces_entity_pending` and `test_dispatch_skipped_event_surfaces_entity_pending`.

**Tests:** 8/8 passing (GREEN) — both new entity-only-turn telemetry tests RAN and passed.
**Branch:** feat/76-5-entity-pending-telemetry (pushed)

**Handoff:** To finish (SM).
