---
parent: context-epic-29.md
---

# Story 29-11: Narrator tactical_place Tool

## Business Context

The narrator needs to place and move entities on the tactical grid via structured tool
calls, not prose. "A goblin scout crouches behind the pillar" must become a tool call
that positions the goblin at a specific grid coordinate near a cover feature. This
prevents spatial inconsistency between narration and map state.

## Technical Approach

### Step 1: Define tactical_place tool schema

In `sidequest-agents/src/tools/`, create `tactical_place.rs`:

Tool call JSON schema for the narrator:
```json
{
  "tool": "tactical_place",
  "entity_id": "goblin_scout_1",
  "name": "Goblin Scout",
  "x": 9,
  "y": 3,
  "size": "medium",
  "faction": "hostile"
}
```

For moving existing entities:
```json
{
  "tool": "tactical_place",
  "entity_id": "goblin_scout_1",
  "x": 7,
  "y": 5
}
```

### Step 2: Tool execution handler

Process the tool call server-side in the dispatch pipeline (same pattern as
`item_acquire`, `quest_update`, etc. in `sidequest-agents/src/tools/`):

1. Validate position is walkable (not wall, void, or occupied by non-traversable feature)
2. If entity_id already exists, update position (move). If new, create TacticalEntity
3. Add/update entity in the room's tactical entity list
4. Emit OTEL event: `tactical.entity_placed` with entity_id, position, faction

### Step 3: Add to narrator output schema

In `sidequest-agents/src/agents/narrator.rs`, add `tactical_place` to the game_patch
JSON schema that defines what the narrator can emit. Add it alongside existing tools
like `items_gained`, `quest_updates`, etc.

### Step 4: Inject grid context into narrator prompt

When a room has a tactical grid, inject a compact summary into the narrator prompt
(Valley zone -- state context). Format from ADR-071:
```
TACTICAL: The Mouth (12x12). PC "Grimjaw" at (2,5).
Hostile: "Goblin Scout" at (9,3), "Tunnel Spider" at (1,6).
Cover: Worn tooth stumps at (4,4)(4,8).
Hazard: Slippery moss circle r=2 at (6,6).
```

Build this in `sidequest-server/src/dispatch/prompt.rs` alongside existing context sections.

### Step 5: Wire tool result into dispatch

In `sidequest-agents/src/tools/assemble_turn.rs`, extract `tactical_place` entries
from the narrator's game_patch JSON and apply them to the tactical entity registry.
After applying, send updated TACTICAL_STATE to the client.

## Acceptance Criteria

- AC-1: `tactical_place` tool schema defined in narrator output format
- AC-2: New entity placement creates TacticalEntity with all fields
- AC-3: Existing entity placement updates position only (preserves other fields)
- AC-4: Position validation rejects wall, void, and blocking cells
- AC-5: Narrator prompt includes compact grid summary when room has tactical grid
- AC-6: Tool results extracted from game_patch and applied in dispatch
- AC-7: Updated TACTICAL_STATE sent to client after placement
- AC-8: OTEL event: `tactical.entity_placed` with entity_id, position, faction
- AC-9: Unit test: place new entity, move existing entity, reject invalid position
- AC-10: Wiring test: narrator game_patch with tactical_place flows through assemble_turn to tactical state

## Key Files

| File | Action |
|------|--------|
| `sidequest-agents/src/tools/tactical_place.rs` | NEW: tool execution handler |
| `sidequest-agents/src/tools/mod.rs` | ADD: pub mod tactical_place |
| `sidequest-agents/src/agents/narrator.rs` | MODIFY: add tactical_place to game_patch schema |
| `sidequest-agents/src/tools/assemble_turn.rs` | MODIFY: extract and apply tactical_place |
| `sidequest-server/src/dispatch/prompt.rs` | ADD: tactical grid summary in narrator prompt context |
| `sidequest-server/src/dispatch/tactical.rs` | MODIFY: send updated TACTICAL_STATE after placement |
