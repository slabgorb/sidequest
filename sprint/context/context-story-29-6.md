---
parent: context-epic-29.md
---

# Story 29-6: Shared-Wall Layout Engine (Tree Topology)

## Business Context

Individual room grids need to be composed into a dungeon map. Adjacent rooms share wall
segments at exit gaps -- one wall, not two. This story implements the tree-topology
layout algorithm that places rooms in global coordinates with shared walls. Cycle handling
(jaquayed layouts) is deferred to 29-7; this story handles tree-structured room graphs.

## Technical Approach

### Step 1: Create layout module in sidequest-game

New module: `sidequest-game/src/tactical/layout.rs`

Core type:
```rust
pub struct DungeonLayout {
    pub rooms: Vec<PlacedRoom>,
    pub width: u32,
    pub height: u32,
}

pub struct PlacedRoom {
    pub room_id: String,
    pub offset_x: i32,
    pub offset_y: i32,
    pub grid: TacticalGrid,
}
```

### Step 2: Exit alignment algorithm

For two connected rooms A and B:
1. Identify A's exit gap facing B (wall side + cell range)
2. Identify B's corresponding exit gap facing A (opposite wall)
3. Position B such that the exit gaps align in global coordinates
4. Shared wall: A's wall cells and B's wall cells at the boundary are the SAME cells
   in the global grid (merge, don't duplicate)

Function: `fn align_rooms(a: &PlacedRoom, a_exit: &ExitGap, b_grid: &TacticalGrid, b_exit: &ExitGap) -> (i32, i32)`

### Step 3: BFS tree placement

Starting from the entrance room (room_type == "entrance"), BFS through the room graph.
For each unplaced neighbor:
1. Find the exit connecting current room to neighbor
2. Find the corresponding exit on the neighbor (reverse direction)
3. Compute placement offset using align_rooms()
4. Check for overlap with all previously placed rooms
5. If overlap, try shifting perpendicular to the shared wall

Function: `fn layout_tree(rooms: &[RoomDef], grids: &HashMap<String, TacticalGrid>) -> Result<DungeonLayout, LayoutError>`

### Step 4: Overlap detection

Two placed rooms overlap if any of their non-void cells occupy the same global coordinate.
Check by iterating cells of the new room against a global occupancy grid (HashSet<GridPos>).

Function: `fn check_overlap(placed: &[PlacedRoom], candidate: &PlacedRoom) -> Vec<GridPos>`

### Step 5: Error reporting

If a room cannot be placed without overlap, this is a content authoring error. Return
`LayoutError` with both room IDs, the overlap cells, and a suggestion ("try reducing
room size or adjusting exit positions"). Never silently degrade.

## Acceptance Criteria

- AC-1: Entrance room placed at origin (0, 0)
- AC-2: Adjacent rooms share exactly one wall segment at exit gaps
- AC-3: Exit gaps align in global coordinates (gap cells overlap perfectly)
- AC-4: Overlap detection catches floor-on-floor collisions
- AC-5: Layout fails loudly on unresolvable overlap (LayoutError with context)
- AC-6: BFS visits all reachable rooms from entrance
- AC-7: Non-void cells of different rooms never occupy same global position
- AC-8: Unit test: linear chain of 3 rooms places correctly
- AC-9: Unit test: T-junction (3 rooms sharing a hub) places correctly
- AC-10: Wiring test: layout engine callable from non-test code (server dispatch or validate)

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/tactical/layout.rs` | NEW: DungeonLayout, PlacedRoom, BFS placement, overlap detection |
| `sidequest-game/src/tactical/mod.rs` | ADD: pub mod layout |
