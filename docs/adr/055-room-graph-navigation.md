---
id: 55
title: "Room Graph Navigation"
status: accepted
date: 2026-04-01
deciders: [Keith]
supersedes: []
superseded-by: null
related: [18, 19, 33]
tags: [room-graph]
implementation-status: partial
implementation-pointer: 87
---

# ADR-055: Room Graph Navigation

**Epic:** 19

## Context

The Caverns & Claudes genre pack introduces dungeon crawling where navigation happens
at room-level granularity — discrete named rooms with typed exits (door, corridor,
stairs, chute). The existing CartographyConfig supports region-based navigation
(ADR-019) where locations are freeform strings the narrator sets freely.

Freeform location breaks dungeon crawling in two ways:

1. **Narrator fabrication** — the LLM can invent rooms, exits, and connections that
   don't exist in the authored dungeon topology. There is no validation.
2. **No transition events** — resource depletion (torch burn, ration consumption) and
   trope escalation (Keeper awareness) must fire per room transition, not per turn.
   The engine has no concept of "player moved to a new room."

Region-based cartography can't solve this. Regions are neighborhoods with freeform
internal navigation. A room graph is a finite directed graph where every node and
edge is authored content.

## Decision

Extend CartographyConfig with a `navigation_mode` discriminant. When a genre pack
(or world override) sets `navigation_mode: room_graph`, the engine switches to
validated room-by-room navigation.

### Data Model

```rust
enum NavigationMode {
    Region,     // Default. Freeform location string, regions for context.
    RoomGraph,  // Validated. Location must be a room_id with exit from current room.
}

struct RoomDef {
    id: String,
    name: String,
    description: String,
    level: Option<String>,      // Dungeon level ID (for depth mechanics)
    room_type: String,          // chamber, corridor, hub, entrance, epitome, passage, maze
    size: String,               // small, medium, large
    exits: Vec<RoomExit>,
    contents: RoomContents,     // treasure, hazards, creatures (content-level, not engine structs)
    keeper_awareness_modifier: f64,  // Trope multiplier for this room
    notes: Option<String>,
}

struct RoomExit {
    to: String,                 // Target room_id
    exit_type: String,          // door, corridor, stairs_up, stairs_down, chute_down, archway
    direction: String,          // north, south, east, west, up, down
    description: String,
}
```

### Navigation Behavior

**Region mode (default):** No change. Location is a freeform string. Narrator sets
it via WorldStatePatch. No validation.

**Room graph mode:**
- `GameSnapshot.location` is constrained to valid room_ids from the loaded room graph.
- `WorldStatePatch.location` is validated: the target room must be reachable via an
  exit from the current room. Invalid moves are rejected.
- One-way exits (chute_down) are respected — the reverse path must exist as a separate
  exit or the room is one-way.
- On valid room transition: fire `TropeEngine::tick_on_room_transition()` which
  advances all active tropes by their `rate_per_turn` (room transitions ARE turns in
  dungeon mode).
- `discovered_rooms: HashSet<String>` tracks fog of war. Rooms are discovered on entry.
- MAP_UPDATE messages include the full discovered room graph with exits and types for
  the automapper UI.

### Trope Integration

The trope engine's `rate_per_turn` field gets a dual meaning based on navigation mode:
- **Region mode:** rate_per_turn fires once per player action (existing behavior).
- **Room graph mode:** rate_per_turn fires once per room transition.

Room-level `keeper_awareness_modifier` scales the multiplier for that specific room.
High-value rooms (Vault of Teeth: +2) escalate tropes faster than empty corridors (+0).

### Resource Depletion

Consumable items gain a `uses_remaining: Option<u32>` field. On room transition in
room_graph mode, the engine decrements uses_remaining for active light sources (tag:
`light`) and optionally for rations (configurable per genre pack).

Items at `uses_remaining == 0` are removed from inventory. This fires a protocol
message so the UI can update and the narrator is informed.

### What This Does NOT Change

- Region-based cartography continues to work identically for all other genre packs.
- The freeform narrator location setting is not removed — it's gated behind navigation_mode.
- No new subsystems are created. This extends CartographyConfig and adds validation to
  existing movement paths.
- ConfrontationDef is unchanged. Boss encounters are content-level (room_type: epitome).

## Consequences

**Positive:**
- Dungeon topology is enforced by the engine, not by LLM prompt compliance.
- Resource depletion tied to movement creates the extraction pressure loop.
- Trope escalation per-room creates the Keeper awareness mechanic without a custom subsystem.
- Automapper UI has structured data to render (room graph, exits, fog of war).

**Negative:**
- Dual navigation modes add complexity to state validation.
- Room graph YAML must be hand-authored per dungeon (no procedural generation).
- Test matrix grows: every state mutation path must handle both navigation modes.

## Alternatives Considered

1. **Custom Keeper awareness subsystem** — Rejected. The trope engine already handles
   escalation with passive progression and accelerators. A custom system would duplicate
   this infrastructure.

2. **Procedural dungeon generation** — Deferred. Hand-authored room graphs are sufficient
   for initial content. Procedural generation can be added later as a room graph factory.

3. **LLM-constrained navigation via prompt** — Rejected. Prompt compliance is unreliable.
   The narrator will invent rooms regardless of instructions. Mechanical validation is
   the only reliable approach (consistent with OTEL observability principle).

## Implementation status (2026-05-02)

Audited during the deferred/proposed bucket sweep. The data layer, init
runtime, and content footprint are live; per-transition mechanics
(trope tick, resource depletion) and a replacement map-update wire
message are owed. The shipped data shape diverges from this ADR's
prose on several fields — defer to the running models, not the body
above.

### Live

- **`NavigationMode` enum** — `sidequest-server/sidequest/genre/models/world.py`.
  Three variants: `region`, `room_graph`, `hierarchical`. (See **Spec drift**
  below — this ADR specified two; `hierarchical` is an unspecified addition.)
- **`RoomDef` model** — same file, with `keeper_awareness_modifier: float = 1.0`
  on every room (line 87). Field is populated from YAML but not currently
  consumed by trope-tick logic (gap, see below).
- **`RoomExit*` tagged union** — discriminated by `type: Literal["door" | …]`.
  Different shape from this ADR's flat `RoomExit { exit_type: String }` spec
  but architecturally equivalent.
- **`init_room_graph_location()`** — `sidequest-server/sidequest/game/room_movement.py:24`.
  Places the player at the entrance room and seeds `discovered_rooms`.
- **Production switch** — `sidequest-server/sidequest/server/websocket_session_handler.py:1207–1230`
  branches on `world.cartography.navigation_mode == NavigationMode.room_graph`
  and invokes the room-graph init path. Logs `room_graph.init genre=… world=…
  entrance=… discovered_rooms=…`.
- **`discovered_rooms`** — field on `GameSnapshot`, populated and tracked.
- **Content shipping** — four worlds in `sidequest-content/genre_packs/caverns_and_claudes/worlds/`
  ship `rooms.yaml`: `dungeon_survivor`, `grimvault`, `horden`, `mawdeep`.
  Each is a hand-authored room graph with id/name/room_type/size/
  keeper_awareness_modifier/description/exits.

### Spec drift (running data shape differs from this ADR)

- **`size`:** ADR specified `String` (`"small"`/`"medium"`/`"large"`).
  Running shape is `[width, height]` tile coordinates — see e.g.
  `caverns_and_claudes/worlds/dungeon_survivor/rooms.yaml` (`size: [3, 3]`).
  The tile-grid form is more useful and is what production consumes; the
  string-label form is dead spec.
- **`RoomExit`:** ADR specified flat struct with `exit_type: String`.
  Running shape is a Pydantic tagged union with `type` discriminator
  (`RoomExitDoor`, etc.). Same intent, more typesafe shape.
- **`NavigationMode`:** ADR specified two variants. Running enum has three;
  `hierarchical` is unspecified here. If/when hierarchical mode acquires
  documentation owe, this ADR is *not* the place — write a fresh ADR.

### Dark / restoration owed (tracked in [ADR-087](087-post-port-subsystem-restoration-plan.md))

- **Per-transition trope tick.** §Trope Integration specified that
  `rate_per_turn` fires once per room transition in room_graph mode (vs.
  once per player action in region mode). No `tick_on_room_transition`
  function exists in the Python tree — `grep` returns zero hits. The
  Keeper-awareness escalation mechanic the ADR is shaped around is not
  currently driven by movement.
- **Per-transition resource depletion.** §Resource Depletion specified
  `uses_remaining` decrement on room transition for active light sources
  (and optionally rations). The `uses_remaining` field is populated on
  items at loadout time (`server/dispatch/chargen_loadout.py:65`,
  `game/builder.py:1364, 1405`) but never decremented on transition.
  The torch-burn / extraction-pressure loop is not wired.
- **Map-update wire message.** §Navigation Behavior specified that
  `MAP_UPDATE` messages carry the discovered room graph to the
  automapper UI. **The MAP_UPDATE pipeline was deleted server-side
  on 2026-04-28** when ADR-019 cartography was retired. The UI still
  carries dead consumer code (`sidequest-ui/src/App.tsx:781`,
  `types/payloads.ts:409`, `types/protocol.ts:17`); the server never
  emits MAP_UPDATE. A *new* wire message — distinct from MAP_UPDATE —
  is owed for room-graph delivery; the dead UI code should be cleaned
  up in the same pass.

### Source of truth

For the current room-graph contract, defer to:

- **Models:** `sidequest-server/sidequest/genre/models/world.py`
- **Runtime:** `sidequest-server/sidequest/game/room_movement.py`
- **Content:** `sidequest-content/genre_packs/caverns_and_claudes/worlds/*/rooms.yaml`
- **Dispatch wiring:** `sidequest-server/sidequest/server/websocket_session_handler.py:1207`

Not the prose body above. ADR text is the original 2026-04-01 intent;
the running design has evolved.
