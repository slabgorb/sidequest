# Tactical Map Data Flow

Shows the intended pipeline for tactical grid rendering and where wiring currently breaks.

## Pipeline Diagram

```mermaid
sequenceDiagram
    title Tactical Map Pipeline — Intended Flow vs Current Breaks

    participant Save as SaveDB<br/>(SQLite)
    participant Connect as ConnectHandler<br/>(dispatch/connect.rs)
    participant Genre as GenreLoader<br/>(sidequest-genre)
    participant Room as RoomMovement<br/>(sidequest-game)
    participant Parser as TacticalParser<br/>(tactical/parser.rs)
    participant Narrator as Narrator<br/>(Claude subprocess)
    participant Dispatch as DispatchLoop<br/>(dispatch/mod.rs)
    participant Proto as Protocol<br/>(sidequest-protocol)
    participant WS as WebSocket
    participant Map as MapWidget<br/>(UI)
    participant Auto as Automapper<br/>(UI)
    participant Grid as TacticalGridRenderer<br/>(UI)

    note over Save,Grid: ═══ PHASE 1: Connection & Initial Load ═══

    Save->>Connect: Load snapshot (location: "mouth",<br/>discovered_rooms: ["mouth"])
    Connect->>Genre: Load genre pack rooms
    Genre-->>Connect: rooms.yaml → RoomDef[] (19 defined, 17 loaded)

    note right of Genre: ⚠ 2 rooms fail to parse<br/>(legend/grid deserialization)

    Connect->>Room: build_room_graph_explored(<br/>rooms, discovered=["mouth"], loc="mouth")
    Room->>Room: Filter rooms by discovered_rooms
    Room->>Parser: parse_room_grid(room) for each discovered room
    Parser-->>Room: TacticalGridPayload (cells, legend, dimensions)
    Room-->>Connect: ExploredLocation[]<br/>with tactical_grid: Some(...)
    Connect->>Proto: MAP_UPDATE message
    Proto->>WS: Send to client
    WS->>Map: MAP_UPDATE payload
    Map->>Auto: Render explored locations
    Auto->>Grid: Delegate grid → SVG

    note over Save,Grid: ═══ PHASE 2: Narrator Turn — WHERE IT BREAKS ═══

    Narrator->>Dispatch: Turn response with<br/>[LOCATION: The Threshold]

    note right of Narrator: Narrator invents creative name.<br/>Does NOT know room graph IDs.

    Dispatch->>Dispatch: extract_location_header()<br/>"The Threshold" → normalize → "threshold"
    Dispatch->>Save: snapshot.location = "threshold"<br/>discovered_rooms += "threshold"

    rect rgb(255, 220, 220)
        note over Dispatch,Room: 🔴 BREAK 1: ID Mismatch<br/>"threshold" is NOT a room ID in rooms.yaml.<br/>It's a creative landmark name from the narrator.<br/>Room graph uses IDs like "mouth", "gullet", "stomach".
    end

    Dispatch->>Connect: Rebuild room graph with<br/>discovered=["mouth","threshold"]
    Connect->>Room: build_room_graph_explored(...)
    Room->>Room: Filter rooms where id ∈ discovered_rooms

    rect rgb(255, 220, 220)
        note over Room,Parser: 🔴 BREAK 2: Zero Grid Data<br/>"threshold" matches no RoomDef.id → filtered out.<br/>"mouth" still matches but new location shows nothing.<br/>ExploredLocation[] has tactical_grid: None for current.
    end

    Room-->>Connect: ExploredLocation[] (no grids populated)

    rect rgb(255, 220, 220)
        note over Connect,Proto: 🔴 BREAK 3: Silent OTEL Gap<br/>No tactical_grid.map_update span fires<br/>(grids_populated == 0). No telemetry = no visibility.
    end

    Connect->>Proto: MAP_UPDATE (empty grid data)
    Proto->>WS: Send to client
    WS->>Map: MAP_UPDATE (no grids)
    Map->>Auto: No tactical grid available

    note right of Auto: Falls back to schematic boxes.<br/>User sees abstract map, not tactical grid.

    note over Save,Grid: ═══ DEAD CODE: Never Reached ═══

    note over Proto: TACTICAL_STATE message type<br/>is defined in protocol but<br/>never sent by any handler.

    note over Grid: TacticalGridRenderer exists<br/>but never receives grid data<br/>after first narrator turn.
```

## Root Cause

The narrator generates creative location names (`"The Threshold"`, `"The Gullet's Edge"`) that are normalized and stored as the player's current location. These names never match the mechanical room IDs defined in `rooms.yaml` (`"mouth"`, `"gullet"`, `"stomach"`).

Once the first narrator turn fires, every subsequent `build_room_graph_explored` call filters against `discovered_rooms` containing narrator-invented names that match zero `RoomDef` entries.

## Additional Issues

| Issue | Detail |
|---|---|
| **17/19 rooms loaded** | 2 rooms fail during parse — likely legend or grid deserialization errors in `rooms.yaml` |
| **TACTICAL_STATE unused** | Protocol message defined but no handler sends it |
| **Daemon tactical_sketch** | Tier config exists in daemon but is never called (Phase 1 is client-side SVG) |
| **No narrator constraint** | Narrator prompt does not include room graph IDs or instructions to use them |

## Fix Direction

The narrator must either:
1. Be constrained to emit room graph IDs (add room ID list to narrator system prompt), or
2. A mapping layer must resolve creative names to room IDs (fuzzy match / alias table in `cartography.yaml`)

Option 1 is simpler but constrains narrator creativity. Option 2 preserves narrator freedom but adds a resolution step that can fail.
