---
story_id: "34-11"
jira_key: ""
epic: "34"
workflow: "tdd"
---

# Story 34-11: OTEL dice spans — request_sent, throw_received, result_broadcast

## Story Details

- **ID:** 34-11
- **Jira Key:** (pending)
- **Epic:** 34 — 3D Dice Rolling System — MVP
- **Workflow:** tdd (phased: setup → red → green → spec-check → verify → review → spec-reconcile → finish)
- **Points:** 2
- **Stack Parent:** none
- **Repos:** api (sidequest-api)

## Summary

Add OTEL watcher events to the three critical dice dispatch points so the GM panel can verify dice are engaging:

1. **`dice.request_sent`** — when `DiceRequest` is broadcast to clients
2. **`dice.throw_received`** — when `DiceThrow` arrives from the rolling player  
3. **`dice.result_broadcast`** — when `DiceResult` is broadcast after resolution

These are `WatcherEvent` emissions using the existing `WatcherEventBuilder` pattern in `sidequest-server`. The dispatch code already has `tracing::info!` calls at these points (added in 34-4/34-8) — this story upgrades them to structured `WatcherEvent`s visible on the GM panel.

## Acceptance Criteria

1. **`dice.request_sent` emitted on broadcast** — When `dispatch/beat.rs` broadcasts `DiceRequest` to all connected clients, emit a `WatcherEvent` with:
   - Event name: `dice.request_sent`
   - Span attributes: `request_id`, `rolling_player_id`, `character_name`, `dc`, `die_pool_description` (e.g., "1d20+3")
   
2. **`dice.throw_received` emitted on arrival** — When the server receives `ClientMessage::DiceThrow`, emit a `WatcherEvent` with:
   - Event name: `dice.throw_received`
   - Span attributes: `request_id`, `rolling_player_id`, `throw_velocity`, `throw_angular_momentum`, `throw_position`
   
3. **`dice.result_broadcast` emitted after resolution** — When `dispatch/beat.rs` broadcasts `DiceResult` to all clients, emit a `WatcherEvent` with:
   - Event name: `dice.result_broadcast`
   - Span attributes: `request_id`, `rolling_player_id`, `outcome` (e.g., "CritSuccess", "Success", "Fail"), `total`, `seed`

4. **Tests verify span emissions** — Unit tests confirm each span is emitted at the correct point with correct attributes

5. **No silent fallbacks** — If a span attribute is unavailable, log loudly (fail the emission or use a sentinel value, never silently omit)

6. **Wiring verified end-to-end** — Grep for non-test consumers of the telemetry exports; verify they're imported and called in production dispatch code

## Key References

- **Epic context:** `/Users/keithavery/Projects/oq-1/sprint/context/context-epic-34.md` (guardrail #5: "OTEL on every dispatch decision")
- **Telemetry crate:** `sidequest-api/crates/sidequest-telemetry/src/`
- **WatcherEvent pattern:** `sidequest-api/crates/sidequest-server/src/watcher.rs`
- **DiceThrow handler:** `sidequest-api/crates/sidequest-server/src/lib.rs` (line ~2229)
- **Existing dice tracing:** grep for `"dice."` in `lib.rs` to find existing `tracing::info!` calls

## Workflow Tracking

**Workflow:** tdd (phased)  
**Phase:** setup  
**Phase Started:** 2026-04-12  

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-12 | — | — |

## Delivery Findings

No upstream findings.

## Design Deviations

No design deviations at this stage.

---

**Branch:** `feat/34-11-otel-dice-spans`  
**Session Created:** 2026-04-12  
**Next Agent:** tea (RED phase)
