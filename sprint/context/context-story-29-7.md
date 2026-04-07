---
parent: context-epic-29.md
---

# Story 29-7: Jaquayed Layout (Cycle Detection + Ring Placement)

## Business Context

Mawdeep has loops in its room graph (e.g., mouth -> throat -> junction -> antechamber -> mouth).
Tree-only placement (29-6) cannot close these cycles. This story adds the hierarchical
decomposition algorithm from ADR-071: detect cycles first, lay them out as rings, then
attach tree branches. This is the Enter the Gungeon pattern.

## Technical Approach

### Step 1: Cycle detection

Use DFS back-edge detection on the room graph to find all cycles. Each cycle is an
ordered list of room IDs forming a loop.

Function: `fn detect_cycles(rooms: &[RoomDef]) -> Vec<Vec<String>>`

Build adjacency list from room exits. Run DFS, track parent edges. When a back edge
is found, extract the cycle by walking the DFS stack from the back-edge target to
the current node.

### Step 2: Ring placement for cycles

For each cycle, place rooms in a ring:
1. Start with any room in the cycle
2. Place next room by aligning shared exit
3. Continue around the ring
4. At the last connection (loop closure), verify the exit gap alignment works
5. If it doesn't close, this is an authoring error -- fail loudly

Function: `fn layout_cycle(cycle: &[String], rooms: &[RoomDef], grids: &HashMap<String, TacticalGrid>) -> Result<Vec<PlacedRoom>, LayoutError>`

### Step 3: Hierarchical composition

Modify the main layout function from 29-6:
1. Detect all cycles
2. Lay out each cycle as a ring
3. Mark all cycle rooms as placed
4. BFS from cycle nodes to place remaining tree branches (reuse 29-6 logic)
5. If multiple disconnected cycles exist, place them with spacing between

### Step 4: Loop closure validation

The critical constraint: when closing a cycle, the last room's exit gap must align
with the first room's exit gap at a shared wall. If room sizes/shapes make this
impossible, emit `LayoutError::CycleClosureFailed` with the cycle, the gap mismatch
details, and which rooms need adjustment.

### Step 5: Overlap resolution

After ring placement, check for overlaps between cycle rooms and between cycle rooms
and tree branches. If irregular shapes cause overlap, try perpendicular nudging. If
nudging fails, fail with LayoutError (authoring error).

## Acceptance Criteria

- AC-1: DFS cycle detection finds all cycles in Mawdeep room graph
- AC-2: Ring placement produces valid shared walls for all cycle edges
- AC-3: Loop closure validates exit gap alignment at the closing edge
- AC-4: CycleClosureFailed error includes actionable context (which rooms, which gaps)
- AC-5: Tree branches BFS-attach to cycle nodes after ring placement
- AC-6: Overlap detection runs between cycle rooms and tree branches
- AC-7: Multiple disconnected cycles placed with spacing (no overlap)
- AC-8: Unit test: 4-room square cycle places and closes correctly
- AC-9: Unit test: cycle with tree branch hanging off one node
- AC-10: Integration test: full Mawdeep layout (18 rooms with loops) succeeds

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/src/tactical/layout.rs` | ADD: detect_cycles(), layout_cycle(), hierarchical composition |
| `sidequest-game/src/tactical/layout.rs` | MODIFY: layout_tree() becomes layout_dungeon() with cycle-first logic |
