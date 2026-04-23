---
story_id: "29-7"
jira_key: null
epic: "29"
workflow: "tdd"
---
# Story 29-7: Jaquayed layout — cycle detection, ring placement, loop closure validation, overlap detection

## Story Details
- **ID:** 29-7
- **Jira Key:** not required (internal story tracking)
- **Branch:** feat/29-7-jaquayed-layout
- **Epic:** 29 (Tactical ASCII Grid Maps)
- **Workflow:** tdd
- **Points:** 5
- **Priority:** p1
- **Repos:** sidequest-api
- **Stack Parent:** 29-6 (Shared-wall layout engine — tree topology placement)

## Context

### Preceding Work Complete

**29-1 through 29-6 are shipping (completed by 2026-04-13):**
- **29-1** (3 pts): ASCII grid parser — glyph vocabulary, legend, exit extraction from wall gaps
- **29-2** (2 pts): Tactical grid validation — perimeter closure, flood fill, exit matching
- **29-3** (5 pts): Author ASCII grids for Mawdeep 18 rooms
- **29-4** (5 pts): Single-room SVG tactical renderer
- **29-5** (3 pts): TACTICAL_STATE protocol message
- **29-6** (5 pts): Shared-wall layout engine — tree topology placement with actual room dimensions

Story 29-6 implements `DungeonLayout` and the room placement algorithm for **tree-structured dungeon graphs only** (parent-child room relationships, no loops). The algorithm places rooms using BFS traversal, aligning shared walls via exit position matching. This works perfectly for linear dungeons and forests of branches, but cannot handle cyclic room graphs (e.g., "Entrance → Corridor A → Chamber → Corridor B → Entrance").

### What This Story Does

**29-7 extends 29-6 to support jaquayed (cyclic) dungeon topologies.** It implements the constraint solver that:

1. **Detects cycles** in the room graph via DFS back-edge detection
2. **Lays out cycles first** — places rooms on each fundamental cycle as a ring with aligned shared walls
3. **Lays out tree branches** — places rooms hanging off cycle nodes via BFS (reuses 29-6 tree logic)
4. **Validates cycle closure** — verifies the last connection in each cycle can close (exit positions are compatible)
5. **Resolves overlaps** — nudges rooms if irregular shapes cause floor-on-floor collisions in the global grid
6. **Fails loudly** if the dungeon cannot be laid out — content authoring error, not a runtime fallback

### Key Architecture

1. **Data flow:**
   - Input: `room_graph` (RoomDef references + edge list) + `rooms_by_id` map
   - Output: `DungeonLayout` (all rooms positioned in global coordinates)
   - Algorithm phases: cycle detection → ring placement → tree expansion → overlap resolution

2. **Cycle detection:**
   - DFS traversal from an unvisited root
   - Track `visited`, `rec_stack` (recursion stack for back-edge detection)
   - Extract fundamental cycles (independent loops) using union-find or back-edge grouping
   - Reference: Dragon Book, section 8.4.1, or Tarjan's algorithm for strongly connected components

3. **Ring placement (cycle layout):**
   - For each fundamental cycle, place rooms as a ring
   - Start at cycle node 0, place at (0, 0)
   - For each subsequent node in the cycle, use the shared-wall alignment from 29-6
   - Calculate cumulative position as `prev_position + exit_offset`
   - Track rotation/reflection to ensure the ring closes (last room's exit aligns with first room's entry)

4. **Cycle closure validation:**
   - After placing all rooms in a cycle, verify: the last room's exit to the first room has compatible gap widths and positions
   - If closure fails, return an error with the problematic room pair and why (gap width mismatch, position mismatch, overlap)

5. **Tree expansion:**
   - After all cycles are placed, place tree branches using BFS (identical to 29-6 logic)
   - Branches start from any cycle node as the root
   - Ensures no cycle nodes are revisited

6. **Overlap detection and resolution:**
   - After all rooms are placed, scan the global grid for floor-on-floor or feature-on-feature collisions
   - If irregular room shapes cause overlaps, attempt local nudging (small position adjustments)
   - If nudging cannot resolve overlaps, fail with specific room pair and collision report

### Integration Boundary

The output of 29-7 is identical to 29-6: a `DungeonLayout` struct with all rooms positioned in global coordinates. Downstream consumers (29-8 SVG dungeon map, room graph pathfinding) use the same interface — they don't need to know whether the layout is tree or cyclic.

**File locations:**
- `sidequest-api/crates/sidequest-game/src/layout/` — existing module from 29-6, add jaquayed logic here
- Input: `RoomGraph`, `rooms_by_id`, `DungeonLayout` from 29-6
- Output: same `DungeonLayout` structure

### Testing Strategy

1. **Unit tests — cycle detection:**
   - Test graphs with 0, 1, 2, 3 cycles (simple loop, figure-8, complex)
   - Verify each back-edge is identified
   - Verify cycles are decomposed correctly

2. **Unit tests — ring placement:**
   - Test simple 3-room cycle (triangle)
   - Test 4-room cycle with different exit positions
   - Test overlapping exit positions (exit offset vectors sum to zero)
   - Verify cumulative positions and rotation tracking

3. **Unit tests — cycle closure validation:**
   - Test valid closure (exit positions align)
   - Test closure failure (gap width mismatch, position offset)
   - Verify error message identifies the problematic edge

4. **Unit tests — overlap detection:**
   - Create two rooms that would overlap (large irregular shapes)
   - Verify overlap is detected (specify which cells collide)
   - Test nudging resolution (adjust position, retry)

5. **Integration test — full cyclic dungeon:**
   - Load a cyclic test fixture (mock dungeon with 5-6 rooms, 1-2 loops)
   - Call layout solver, verify output `DungeonLayout`
   - Verify all rooms placed without overlap, all cycles closed
   - Verify downstream consumers (29-8 SVG) can render without errors

6. **Wiring test:**
   - Verify `layout_dungeon()` is called from the room graph loader
   - Verify `DungeonLayout` is persisted to game state and retrievable on room entry
   - Verify no test-only paths (all layout code has non-test consumers)

### OTEL Observations

**29-18 owns tactical OTEL, but this story should document what is observable:**
- Cycle detection phase: `layout.cycles_detected` span with cycle count
- Ring placement per cycle: `layout.cycle_placed` span with room count, rotation/reflection tracking
- Overlap detection: `layout.overlap_detected` span (if any) or `layout.no_overlaps` (success)
- Closure validation: `layout.cycle_closed` span per cycle (success) or `layout.cycle_closure_failed` (with room IDs)

Do NOT add OTEL to this story's scope — that lives in 29-18. Just ensure the layout solver is observable (add debug-level structured logging at each phase).

### Acceptance Criteria

1. **Cycle detection works**
   - Dungeon graph with loops is correctly identified (0+ cycles)
   - DFS back-edges extracted
   - Fundamental cycles decomposed (independent loops)

2. **Ring placement works**
   - Rooms on a cycle placed as a ring with shared walls aligned
   - Positions calculated via cumulative exit offsets
   - Rotation/reflection tracked to close the ring

3. **Cycle closure validates**
   - Last room's exit to first room checked for gap compatibility
   - Error if closure fails (identifies problematic room pair)
   - Success if closure succeeds

4. **Overlap detection works**
   - Global grid scanned for floor-on-floor collisions after placement
   - Overlaps identified with specific cell ranges and room IDs
   - Nudging attempted (small position adjustments)
   - Fails with specific collision report if nudging cannot resolve

5. **Tree expansion still works**
   - Branches placed correctly after cycles are fixed
   - BFS traversal from cycle nodes (no cycle node revisits)
   - Identical to 29-6 tree logic

6. **Interface unchanged**
   - `DungeonLayout` output identical to 29-6 (consumers don't change)
   - Input is same `RoomGraph`, `rooms_by_id`
   - Backward compatible with tree-only dungeons

7. **Tests green**
   - Cycle detection unit tests pass
   - Ring placement unit tests pass
   - Overlap detection unit tests pass
   - Integration test with cyclic fixture passes
   - Wiring test verifies layout is called from room loader

### Risks & Mitigations

**Risk:** Ring placement fails for certain room sizes/shapes
- **Mitigation:** Validate at authoring time (sidequest-validate, 29-2). Layout solver never fails silently.

**Risk:** Nudging causes cascading overlaps
- **Mitigation:** Limit nudge iterations, fail with specific collision report after N attempts

**Risk:** Complex jaquayed topologies (3+ nested cycles)
- **Mitigation:** Decompose into fundamental cycles, place independently, validate closure per cycle

### Reference

- **ADR-071:** `docs/adr/071-tactical-ascii-grid-maps.md` — sections 5 (Jaquayed Layout Algorithm)
- **29-6 Layout Engine:** `sidequest-api/crates/sidequest-game/src/layout/` — tree topology placement
- **Cycle detection:** Dragon Book (Aho/Sethi/Ullman), section 8.4.1 or Tarjan SCC algorithm
- **Enter the Gungeon:** Hierarchical decomposition reference in game design literature
- **Test fixtures:** `sidequest-api/tests/fixtures/dungeon_cyclic_*.yaml` (to be created by this story)

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-13T12:45:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-13T12:45:00Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings.

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No deviations yet.
