---
parent: context-epic-29.md
---

# Story 29-5: TACTICAL_STATE Protocol Message

## Business Context

The tactical grid data needs to travel from server to client. This story adds the
TACTICAL_STATE and TACTICAL_ACTION protocol messages, wires TACTICAL_STATE emission
into the dispatch pipeline on room entry, and defines the payload structures that
carry grid, entity, and zone data.

## Technical Approach

### Step 1: Define payload types in sidequest-protocol

In `sidequest-protocol/src/message.rs`, add new payload structs:

```rust
pub struct TacticalStatePayload {
    pub room_id: String,
    pub grid: TacticalGridPayload,
    pub entities: Vec<TacticalEntityPayload>,
    pub zones: Vec<EffectZonePayload>,
}

pub struct TacticalGridPayload {
    pub width: u32,
    pub height: u32,
    pub cells: Vec<Vec<String>>,  // cell type strings for JSON simplicity
    pub features: Vec<TacticalFeaturePayload>,
}

pub struct TacticalFeaturePayload {
    pub glyph: char,
    pub feature_type: String,
    pub label: String,
    pub positions: Vec<[u32; 2]>,
}

pub struct TacticalEntityPayload {
    pub id: String,
    pub name: String,
    pub x: u32,
    pub y: u32,
    pub size: u32,       // cells occupied (1 for medium, 2 for large, etc.)
    pub faction: String, // "player", "hostile", "neutral", "ally"
}

pub struct EffectZonePayload {
    pub id: String,
    pub zone_type: String,  // "circle", "cone", "line", "rect"
    pub params: serde_json::Value,  // shape-specific parameters
    pub label: String,
    pub color: Option<String>,
}

pub struct TacticalActionPayload {
    pub action_type: String,  // "move", "target", "inspect"
    pub entity_id: Option<String>,
    pub target: Option<[u32; 2]>,
    pub ability: Option<String>,
}
```

### Step 2: Add GameMessage variants

In `GameMessage` enum (message.rs line 98), add:
```rust
#[serde(rename = "TACTICAL_STATE")]
TacticalState {
    payload: TacticalStatePayload,
    player_id: String,
},

#[serde(rename = "TACTICAL_ACTION")]
TacticalAction {
    payload: TacticalActionPayload,
    player_id: String,
},
```

### Step 3: Wire TACTICAL_STATE emission on room entry

In `sidequest-server/src/dispatch/mod.rs`, after a room transition is detected
(location change in state_mutations), build and send a TACTICAL_STATE message
if the new room has a grid. The grid is already parsed and available on
DispatchContext.rooms.

Create `sidequest-server/src/dispatch/tactical.rs` for the tactical dispatch logic:
- `fn build_tactical_state(room: &RoomDef, grid: &TacticalGrid) -> TacticalStatePayload`
- `fn send_tactical_state(ctx: &DispatchContext, room_id: &str, tx: &Sender<GameMessage>)`

### Step 4: Add TACTICAL_STATE handler in UI

In `sidequest-ui/src/hooks/useGameState.ts` or the WebSocket message handler,
add a case for `TACTICAL_STATE` that stores the payload in game state, making
it available to the Automapper/TacticalGridRenderer.

## Acceptance Criteria

- AC-1: `TacticalStatePayload` serializes/deserializes correctly (round-trip test)
- AC-2: `TacticalActionPayload` serializes/deserializes correctly (round-trip test)
- AC-3: `TACTICAL_STATE` variant added to GameMessage enum
- AC-4: `TACTICAL_ACTION` variant added to GameMessage enum
- AC-5: Server emits TACTICAL_STATE on room entry when room has grid data
- AC-6: Server does NOT emit TACTICAL_STATE for rooms without grid data
- AC-7: UI receives and stores TACTICAL_STATE payload in game state
- AC-8: Wiring test: room transition to a tactical room triggers TACTICAL_STATE emission (non-test consumer in dispatch)
- AC-9: OTEL event emitted when TACTICAL_STATE is sent: `tactical.state_sent` with room_id, entity_count, zone_count

## Key Files

| File | Action |
|------|--------|
| `sidequest-protocol/src/message.rs` | ADD: TacticalState/TacticalAction variants + payload structs |
| `sidequest-server/src/dispatch/tactical.rs` | NEW: tactical state building and emission |
| `sidequest-server/src/dispatch/mod.rs` | ADD: pub(crate) mod tactical, wire into room transition |
| `sidequest-ui/src/hooks/useGameState.ts` | ADD: TACTICAL_STATE message handler |
| `sidequest-ui/src/types/tactical.ts` | ADD: matching TypeScript payload types |
