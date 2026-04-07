---
parent: context-epic-29.md
---

# Story 29-12: Click-to-Move + Server-Side A* Pathfinding

## Business Context

Players need to move their token by clicking a destination cell. The server validates
the path (A* on the walkability grid) and moves the token, preventing illegal moves
through walls or over obstacles. Server-side pathfinding is authoritative -- the client
never computes paths.

## Technical Approach

### Step 1: Implement A* in sidequest-game

In `sidequest-game/src/tactical/pathfinding.rs`:

```rust
pub fn find_path(
    grid: &TacticalGrid,
    from: GridPos,
    to: GridPos,
    entities: &[TacticalEntity],
) -> Option<Vec<GridPos>>
```

Grid-based A* with:
- 4-directional movement (no diagonals -- matches D&D 5e grid rules)
- Walkability from TacticalCell properties (walls, void blocked)
- Entity collision (occupied cells blocked, except destination if targeting)
- Difficult terrain costs 2 movement instead of 1
- Water is conditional (walkable but may have effects)
- Doors: closed doors block unless the entity can open them

Heuristic: Manhattan distance (consistent with 4-directional movement).

### Step 2: Handle TACTICAL_ACTION Move on server

In `sidequest-server/src/dispatch/tactical.rs`, handle incoming TACTICAL_ACTION
messages with `action_type: "move"`:

1. Look up the entity by entity_id (must be the player's PC)
2. Compute A* path from current position to target
3. If path exists and within movement budget: move the entity
4. If no path: return error message to client ("No valid path")
5. Send updated TACTICAL_STATE with new position
6. Emit OTEL: `tactical.move` with entity_id, from, to, path_length

### Step 3: Movement budget

Movement points per turn (from CreatureCore stats or a default). A* path length
must not exceed the budget. Difficult terrain cells cost double. If the destination
is reachable but over budget, truncate the path to the farthest reachable cell.

### Step 4: Client-side click handling

In `TacticalGridRenderer.tsx`, when a floor cell is clicked:
1. Send TACTICAL_ACTION with `action_type: "move"`, `entity_id: pcId`, `target: [x, y]`
2. Show a "pending move" indicator on the clicked cell
3. On TACTICAL_STATE response, update entity positions (server is authoritative)

### Step 5: Path preview (optional visual aid)

On hover over a walkable cell, compute a visual path preview client-side (simple BFS,
not authoritative). Render as dotted line overlay. The actual move still goes through
the server.

## Acceptance Criteria

- AC-1: A* finds shortest path on walkable cells with 4-directional movement
- AC-2: A* respects wall and void cells as impassable
- AC-3: Difficult terrain cells cost double movement
- AC-4: Entity-occupied cells are blocked (except destination for targeting)
- AC-5: Server rejects moves with no valid path (error message to client)
- AC-6: Server rejects moves exceeding movement budget
- AC-7: Successful move updates entity position and sends TACTICAL_STATE
- AC-8: Client click on floor cell sends TACTICAL_ACTION to server
- AC-9: OTEL event: `tactical.move` with from, to, path_length, budget_remaining
- AC-10: Unit tests: open path, blocked path, difficult terrain cost, budget exceeded

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/tactical/pathfinding.rs` | NEW: A* pathfinding on TacticalGrid |
| `sidequest-game/src/tactical/mod.rs` | ADD: pub mod pathfinding |
| `sidequest-server/src/dispatch/tactical.rs` | ADD: TACTICAL_ACTION Move handler |
| `sidequest-ui/src/components/TacticalGridRenderer.tsx` | ADD: click-to-move, pending indicator |
