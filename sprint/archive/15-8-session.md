---
story_id: "15-8"
jira_key: ""
epic: "15"
workflow: "tdd"
---
# Story 15-8: Canonical GameSnapshot in dispatch — eliminate load-before-save round-trip on every turn

## Story Details
- **ID:** 15-8
- **Epic:** 15 (Playtest Debt Cleanup — Stubs, Dead Code, Disabled Features)
- **Workflow:** tdd
- **Priority:** p1
- **Points:** 5
- **Stack Parent:** none

## Problem Statement

`persist_game_state()` in `dispatch/mod.rs:1254` performs a full SQLite load every turn just to merge 15 loose local variables back into a snapshot, then saves the merged result. This creates two actor-channel round-trips per player action:

1. Load round-trip: load() → request queued in persistence actor → response awaited
2. Save round-trip: save() → request queued in persistence actor → response awaited

**Root cause:** The dispatch loop scatters game state across individual locals in DispatchContext:
- `ctx.hp`, `ctx.max_hp`, `ctx.level`, `ctx.xp`
- `ctx.current_location`
- `ctx.inventory`
- `ctx.combat_state`, `ctx.chase_state`
- `ctx.npc_registry`, `ctx.turn_manager`, `ctx.quest_log`, `ctx.trope_states`
- `ctx.character_json`
- And more...

These are then re-assembled into a snapshot by:
1. Loading the previous snapshot from SQLite (line 1267)
2. Patching 15+ fields into it (lines 1272-1338)
3. Saving it back (lines 1339-1348)

**Impact:** Every player action incurs minimum 2 actor round-trips. With 6-player multiplayer, per-player latency adds up quickly.

## Solution

Carry a **mutable GameSnapshot as a canonical source** in DispatchContext. Patch it in-place as the turn progresses. Save it directly to SQLite without a load.

### Key Changes

1. **Add `snapshot: GameSnapshot` field to DispatchContext** — this becomes the canonical game state during dispatch
2. **Patch the snapshot in-place** during turn processing instead of patching loose locals
3. **Modify persist_game_state()** to call `state.persistence().save()` directly **without the load** (lines 1264-1268)
4. **Keep the load path for session restore** — `dispatch_connect()` will still load from SQLite to populate the initial snapshot
5. **Add OTEL span** `persistence.save_latency_ms` with before/after comparison to demonstrate latency reduction

### Backwards Compatibility

- Session load on reconnect (`dispatch_connect`) still calls `persistence().load()` — this is infrequent (reconnect only) and necessary for restoration
- Hot path (every turn) becomes **save-only**, cutting round-trips in half

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-01T10:40:17Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-01T10:40:17Z | - | - |

## Delivery Findings

No upstream findings at this time.

## Design Deviations

None at this time.

## Implementation Notes

### Files to Modify

- **crates/sidequest-server/src/dispatch/mod.rs**
  - Modify `DispatchContext` struct (add `snapshot: GameSnapshot` field)
  - Update `dispatch_player_action()` to work with canonical snapshot
  - Rewrite `persist_game_state()` to save-only path
  - Add OTEL `persistence.save_latency_ms` span

- **crates/sidequest-server/src/lib.rs**
  - Update `dispatch_player_action` call site(s) to pass/initialize canonical snapshot
  - May need to adjust how snapshot is initially loaded at session start

### Testing Strategy

1. **Unit test** — verify persist_game_state() saves snapshot without load
2. **Integration test** — multi-turn session with latency measurement
3. **Multiplayer test** — 6-player session latency baseline before/after

### Wiring Verification

- Non-test callers of `persist_game_state()`: currently called from line 686 in dispatch_player_action
- Snapshot initialization: occurs in `dispatch_connect()` and possibly during session init
- OTEL emission: must trace save latency in `persist_game_state()` before/after `state.persistence().save()` call
