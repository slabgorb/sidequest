---
parent: context-epic-29.md
---

# Story 29-18: OTEL for Tactical System

## Business Context

Per project rules, every subsystem decision must emit OTEL watcher events so the GM
panel can verify the system is working. The tactical system spans multiple crates
(game, server, agents) and has multiple decision points (parsing, layout, pathfinding,
entity placement, zone creation). This story instruments all of them. Without this,
there is no way to tell whether the tactical system is engaged or whether Claude is
just describing rooms from memory.

## Technical Approach

### Step 1: Grid parsing OTEL

In `sidequest-game/src/tactical/parser.rs`, emit after successful parse:
```
tactical.grid_parsed:
  room_id, width, height, floor_cells, wall_cells, void_cells,
  feature_count, exit_count, legend_entries
```

### Step 2: Layout engine OTEL

In `sidequest-game/src/tactical/layout.rs`, emit:
```
tactical.layout_started:
  room_count, cycle_count, tree_node_count

tactical.room_placed:
  room_id, offset_x, offset_y, shared_walls_count

tactical.cycle_closed:
  cycle_rooms, closure_room_a, closure_room_b, gap_aligned

tactical.layout_complete:
  total_rooms, global_width, global_height, elapsed_ms
```

### Step 3: Pathfinding OTEL

In `sidequest-game/src/tactical/pathfinding.rs`:
```
tactical.pathfind:
  entity_id, from, to, path_length, cells_explored,
  difficult_terrain_cells, blocked (bool), elapsed_ms
```

### Step 4: Entity/zone OTEL

Already partially covered in 29-11 and 29-13. Verify and fill gaps:
```
tactical.entity_placed: entity_id, name, position, faction, source (narrator/system)
tactical.entity_moved: entity_id, from, to, path_length
tactical.entity_removed: entity_id, reason (death/flee/despawn)
tactical.zone_created: zone_id, label, shape, is_hazard
tactical.zone_removed: zone_id, reason (expiry/dispel)
```

### Step 5: Protocol OTEL

In `sidequest-server/src/dispatch/tactical.rs`:
```
tactical.state_sent:
  room_id, entity_count, zone_count, grid_cells, message_size_bytes

tactical.action_received:
  action_type, entity_id, target, player_id
```

### Step 6: GM Dashboard tactical tab

Verify the existing OTEL dashboard (`sidequest-ui/src/components/Dashboard/`) can
display tactical events. The Timeline tab should show tactical spans. If the Subsystems
tab groups by subsystem prefix, "tactical.*" events should appear as a group.

## Acceptance Criteria

- AC-1: Grid parsing emits `tactical.grid_parsed` with cell counts and dimensions
- AC-2: Layout engine emits `tactical.layout_started`, `tactical.room_placed`, `tactical.layout_complete`
- AC-3: Cycle closure emits `tactical.cycle_closed` with alignment result
- AC-4: Pathfinding emits `tactical.pathfind` with path stats and timing
- AC-5: Entity placement/movement/removal all emit OTEL events
- AC-6: Zone creation/removal emits OTEL events
- AC-7: Protocol messages emit `tactical.state_sent` and `tactical.action_received`
- AC-8: All tactical OTEL events visible in GM Dashboard Timeline tab
- AC-9: Every OTEL event has a non-test emitter in production code
- AC-10: `grep -r "tactical\\." crates/ --include="*.rs" | grep WatcherEvent | grep -v test` returns results for all 5 subsystems (parser, layout, pathfinding, entity, protocol)

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/tactical/parser.rs` | ADD: WatcherEvent emissions |
| `sidequest-game/src/tactical/layout.rs` | ADD: WatcherEvent emissions |
| `sidequest-game/src/tactical/pathfinding.rs` | ADD: WatcherEvent emissions |
| `sidequest-game/src/tactical/entity.rs` | VERIFY: WatcherEvent emissions from 29-10/29-11 |
| `sidequest-game/src/tactical/zone.rs` | VERIFY: WatcherEvent emissions from 29-13 |
| `sidequest-server/src/dispatch/tactical.rs` | ADD/VERIFY: protocol-level WatcherEvent emissions |
