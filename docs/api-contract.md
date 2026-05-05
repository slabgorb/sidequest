# SideQuest API Contract

> WebSocket + REST protocol between sidequest-server (Python) and sidequest-ui (React).
> Source of truth: `sidequest-server/sidequest/protocol/messages.py` (pydantic v2 discriminated union),
> `sidequest-server/sidequest/protocol/enums.py` (MessageType), and the supporting modules
> `sidequest-server/sidequest/protocol/{models,dice,course_intent,orbital_intent,dispatch}.py`.
>
> **Last updated:** 2026-05-05
>
> *Historical note:* between 2026-03-30 and 2026-04-19 the source of truth was
> `sidequest-api/crates/sidequest-protocol/src/message.rs` (Rust). ADR-082 ported
> the protocol to pydantic with byte-identical JSON on the wire; the type set has
> since expanded with magic, dogfight, dice, orbital chart, sealed-letter, lobby
> seat, and going-forward-corpus message kinds. This document describes the
> live wire today.

## Transport

### WebSocket

- **URL:** `ws://{host}/ws` (or `wss://` over TLS)
- **Protocol:** JSON text frames for game messages *(binary frames were used for TTS PCM audio; removed 2026-04 along with TTS)*
- **Reconnect:** Client auto-reconnects on abnormal close (code != 1000) with 1s backoff

All JSON messages conform to:

```typescript
interface GameMessage {
  type: MessageType;       // enum string — see below
  payload: object;         // type-specific
  player_id: string;       // "" for client-originated
}
```

### REST

| Method | Path | Response | Purpose |
|--------|------|----------|---------|
| GET | `/api/genres` | `Record<string, { worlds: string[] }>` | Genre list with worlds per genre |

That's the only REST endpoint. Everything else flows through WebSocket.

---

## Message Types (44 total)

The authoritative list lives in `sidequest-server/sidequest/protocol/enums.py::MessageType`. Grouped here by purpose:

```
Client → Server:
  PLAYER_ACTION         Player game input
  SESSION_EVENT         Session lifecycle (connect)
  CHARACTER_CREATION    Creation scene response
  PLAYER_SEAT           Lobby seat claim
  YIELD                 Voluntary turn yield
  DICE_THROW            Player rolls inline 3D dice (ADR-074)
  BEAT_SELECTION        Player selects a beat in a confrontation
  TACTICAL_ACTION       Tactical-grid action (Epic 29 work; engine deferred per ADR-071)
  COURSE_INTENT         Orbital chart course intent (ADR-094)
  ORBITAL_INTENT        Orbital chart UI request → server returns ORBITAL_CHART
  JOURNAL_REQUEST       Request journal contents

Server → Client (turn flow):
  NARRATION             Complete narration with state delta + footnotes
  NARRATION_END         Turn-completion marker, carries final state delta
  THINKING              Processing indicator (spinner)
  SESSION_EVENT         Session lifecycle (connected, ready, theme_css)
  CHARACTER_CREATION    Creation scene prompt / confirmation / complete
  TURN_STATUS           Turn/round tracking with player status
  PARTY_STATUS          Full party snapshot
  ACTION_QUEUE          Queued actions
  ACTION_REVEAL         Sealed-letter action reveal (multiplayer)
  CHAPTER_MARKER        Chapter/scene transition

Server → Client (mechanics + UI):
  CONFRONTATION         Confrontation engine state (resource pools, beats — ADR-033)
  CONFRONTATION_OUTCOME Magic / dogfight resolution (Phase 5 — story 47-3)
  TACTICAL_STATE        Tactical grid state (Epic 29)
  DICE_REQUEST          Server prompts player to roll
  DICE_RESULT           Resolved dice roll
  ORBITAL_CHART         Orbital chart SVG payload
  SCRAPBOOK_ENTRY       Persistent illustration record (per scene)
  RENDER_QUEUED         Image render queued notification
  IMAGE                 Image delivery (scene, portrait, handout)
  AUDIO_CUE             Music and SFX control (2-channel — ADR-076)
  SCENARIO_EVENT        Scenario lifecycle events
  ACHIEVEMENT_EARNED    Achievement/milestone notification
  JOURNAL_RESPONSE      Journal contents response
  ITEM_DEPLETED         Item consumed/destroyed notification
  RESOURCE_MIN_REACHED  Resource threshold warning

Server → Client (lobby / pause / per-player):
  PLAYER_PRESENCE       Lobby presence updates
  SEAT_CONFIRMED        Seat-claim confirmation
  GAME_PAUSED           Server-driven session pause
  GAME_RESUMED          Pause lifted
  SECRET_NOTE           Per-player secret note (asymmetric reveal)

Reserved (going-forward corpus capture; not yet emitter-reachable on all paths):
  DISPATCH_PACKAGE          LocalDM dispatch package payload
  NARRATOR_DIRECTIVE_USED   Narrator directive consumption record
  VERDICT_OVERRIDE          Lethality / verdict override record

Errors:
  ERROR                 Error with optional reconnect_required flag

Retired (kept in MessageType enum for backwards compatibility; no production sender):
  VOICE_SIGNAL          (was WebRTC voice chat — ADR-054 / ADR-076)
  VOICE_TEXT            (was TTS narration text payload — ADR-076)
```

The `CHARACTER_SHEET`, `INVENTORY`, `COMBAT_EVENT`, and `MAP_UPDATE` message types listed in earlier revisions of this document **never existed in the live wire protocol**. Character details flow through `CHARACTER_CREATION` (during chargen) and `PARTY_STATUS` (during play). Inventory is delivered via `state_delta.inventory` inside `NARRATION` / `NARRATION_END` / `PARTY_STATUS`. Combat is `CONFRONTATION` + `CONFRONTATION_OUTCOME` (and `TACTICAL_STATE` where Epic 29 grid is used). The world-map view (`MAP_UPDATE`) was retired with cartography 2026-04-28 (ADR-019 superseded; ADR-055 room-graph nav successor).

---

## Client → Server Messages

### PLAYER_ACTION
Player types something in the game.
```json
{
  "type": "PLAYER_ACTION",
  "payload": { "action": "string", "aside": false },
  "player_id": ""
}
```
- `aside: true` = out-of-character message (not narrated)
- Slash commands (`/status`, `/inventory`, etc.) are intercepted server-side before intent classification
- Player text is sanitized at the protocol layer (ADR-047) before reaching intent classification or any agent prompt.

### SESSION_EVENT (connect)
Sent immediately after WebSocket opens.
```json
{
  "type": "SESSION_EVENT",
  "payload": { "event": "connect", "player_name": "string", "genre": "string", "world": "string" },
  "player_id": ""
}
```

### CHARACTER_CREATION (response)
Player responds to a creation scene.
```json
{
  "type": "CHARACTER_CREATION",
  "payload": { "phase": "string", "choice": "string" },
  "player_id": ""
}
```

### YIELD (outbound)
Voluntary turn yield — debits Edge per ADR-078.
```json
{
  "type": "YIELD",
  "payload": { "reason": "string|null" },
  "player_id": ""
}
```

### PLAYER_SEAT (outbound)
Lobby seat claim. Server replies with `SEAT_CONFIRMED` or `ERROR`.

### DICE_THROW / BEAT_SELECTION / TACTICAL_ACTION / COURSE_INTENT / ORBITAL_INTENT
Mechanic payloads. Schemas live in:
- `sidequest-server/sidequest/protocol/dice.py` (dice)
- `sidequest-server/sidequest/protocol/course_intent.py` (course)
- `sidequest-server/sidequest/protocol/orbital_intent.py` (orbital chart)
- `sidequest-server/sidequest/protocol/messages.py` (beat selection, tactical action)

Inbound dispatch handlers live under `sidequest-server/sidequest/handlers/`.

---

## Server → Client Messages

### SESSION_EVENT
Controls session phase transitions.

**Connected (no character yet):**
```json
{
  "type": "SESSION_EVENT",
  "payload": { "event": "connected", "has_character": false }
}
```
→ Client enters character creation phase.

**Ready (character exists):**
```json
{
  "type": "SESSION_EVENT",
  "payload": {
    "event": "ready",
    "initial_state": {
      "characters": [{ "name": "", "hp": 0, "max_hp": 0, "level": 1, "class": "", "statuses": [], "inventory": [] }],
      "location": "string",
      "quests": { "quest_name": "status_string" },
      "turn_count": 0
    }
  }
}
```

**Theme CSS:**
```json
{
  "type": "SESSION_EVENT",
  "payload": { "event": "theme_css", "css": "..." }
}
```

### CHARACTER_CREATION

**Scene (interactive step):**
```json
{
  "type": "CHARACTER_CREATION",
  "payload": {
    "phase": "scene",
    "scene_index": 1,
    "total_scenes": 3,
    "prompt": "Describe your character...",
    "summary": "optional recap",
    "message": "optional flavor text",
    "choices": [{ "label": "Warrior", "description": "Strong fighter" }],
    "allows_freeform": true,
    "input_type": "text",
    "character_preview": { ... }
  }
}
```

**Confirmation:**
```json
{
  "type": "CHARACTER_CREATION",
  "payload": {
    "phase": "confirmation",
    "prompt": "Is this your character?",
    "character_preview": { ... },
    "choices": [{ "label": "Yes", "description": "" }, { "label": "No", "description": "" }]
  }
}
```

**Complete:**
```json
{
  "type": "CHARACTER_CREATION",
  "payload": {
    "phase": "complete",
    "character": { ... }
  }
}
```

### NARRATION / NARRATION_END

Narrative text from the AI with optional state deltas and structured footnotes.

**NARRATION (complete):**
```json
{
  "type": "NARRATION",
  "payload": {
    "text": "The orc lunges...",
    "state_delta": {
      "location": "Dark Cave",
      "characters": [{ "name": "Grok", "hp": 15, "max_hp": 20, "level": 3, "class": "Warrior", "statuses": ["poisoned"], "inventory": ["sword"] }],
      "quests": { "Find the Gem": "in_progress" },
      "items_gained": [{ "name": "sealed matte-black case", "description": "A mysterious container", "category": "quest" }]
    },
    "footnotes": [
      { "marker": 1, "summary": "The Flickering Reach was once a unified city-state", "category": "Lore", "is_new": true },
      { "marker": 2, "fact_id": "fact-abc123", "summary": "Remnant of the old trade route", "category": "Place", "is_new": false }
    ]
  }
}
```

**NARRATION_END (turn-completion marker):**
```json
{ "type": "NARRATION_END", "payload": { "state_delta": { ... } } }
```

`NARRATION_END` clears the "thinking" indicator and commits any final
`state_delta` in the same render cycle as the preceding `NARRATION` text.
Always sent, even when the turn produced no state delta.

> **Removed (2026-04, per ADR-076):** `NARRATION_CHUNK` was a streaming
> partial-text variant paired with binary TTS voice frames. With TTS gone,
> the chunked streaming path has zero production senders. The variant still
> exists in `sidequest-protocol/src/message.rs` but will be removed when
> ADR-076 moves from Proposed to Accepted.

#### Footnotes

Footnotes are structured knowledge extracted from narrator output. New discoveries (`is_new: true`) become KnownFact entries. Callbacks (`is_new: false`) link to existing facts via `fact_id`.

```typescript
interface Footnote {
  marker?: number;         // matches [N] superscript in prose
  fact_id?: string;        // links to existing KnownFact (callbacks only)
  summary: string;         // one-sentence description
  category: FactCategory;  // "Lore" | "Place" | "Person" | "Quest" | "Ability"
  is_new: boolean;         // true = discovery, false = callback
}
```

### THINKING
Server is processing (shows spinner).
```json
{ "type": "THINKING", "payload": {} }
```

### TURN_STATUS
Turn/round tracking with per-player status.
```json
{
  "type": "TURN_STATUS",
  "payload": {
    "player_name": "string",
    "status": "active",
    "state_delta": { ... }
  }
}
```
- `status`: `"active"` (this player's turn) or `"resolved"` (turn complete)

### PARTY_STATUS
Full party snapshot.
```json
{
  "type": "PARTY_STATUS",
  "payload": {
    "members": [
      {
        "player_id": "string",
        "name": "string",
        "character_name": "Grok the Mighty",
        "current_hp": 20,
        "max_hp": 20,
        "statuses": ["blessed"],
        "class": "Warrior",
        "level": 3,
        "portrait_url": "https://..."
      }
    ]
  }
}
```
- `name`: player lobby name (what user typed at connect)
- `character_name`: in-game character name (for party panel display)

### Character details, inventory, and combat state

Character details, inventory, and combat state do **not** travel in dedicated message types. They flow through the turn-stream messages already documented:

- **Character details** — `CHARACTER_CREATION` payloads during chargen (`CharacterSheetDetails` in `protocol/models.py`); the live character sheet view reads from `PARTY_STATUS` + `state_delta.characters`. Per ADR-040 the sheet uses narrative voice rather than raw stat dumps.
- **Inventory** — `state_delta.characters[].inventory` and `state_delta.items_gained` inside `NARRATION` / `NARRATION_END` / `PARTY_STATUS`. `InventoryPayload` (`protocol/models.py`) shapes the journal-style listing.
- **Combat / confrontation** — `CONFRONTATION` (live state) and `CONFRONTATION_OUTCOME` (resolution; magic Phase 5 / dogfight sealed-letter). `TACTICAL_STATE` carries grid state where Epic 29 work is used. There is no `COMBAT_EVENT` message type.

> **Edge / Composure (ADR-078):** internally `CreatureCore` tracks Edge, not HP — story 45-35 removed HP from chargen and CreatureCore. The wire still ships `hp` / `max_hp` / `current_hp` on `CharacterState` and `PartyMember` for backward compatibility; these are Edge values reusing the legacy field names. Frontend renders them as Edge bars (`GenericResourceBar`, `LedgerPanel`). A protocol cleanup story to rename the wire fields is on the post-port follow-up list.

### IMAGE
Image delivery (portraits, handouts, scene art).
```json
{
  "type": "IMAGE",
  "payload": {
    "url": "https://...",
    "description": "A crumbling tower",
    "handout": true,
    "render_id": "unique-id",
    "tier": "scene",
    "scene_type": "exploration",
    "generation_ms": 3200
  }
}
```
- `handout: true` → added to journal
- `tier`: "scene_illustration", "portrait", "portrait_square", "landscape", "text_overlay", "fog_of_war"
- `scene_type`: "combat", "dialogue", "exploration", etc.

### AUDIO_CUE
Background music, sound effects, and ambience control.
```json
{
  "type": "AUDIO_CUE",
  "payload": {
    "mood": "combat",
    "music_track": "battle_theme_01",
    "sfx_triggers": ["sword_clash", "explosion"],
    "channel": "music",
    "action": "play",
    "volume": 0.8
  }
}
```
- `channel`: `"music"`, `"sfx"` *(the daemon mixer additionally tracks an `"ambience"` channel internally, but the protocol only routes music and SFX through the client)*
- `action`: `"play"`, `"fade_in"`, `"fade_out"`, `"stop"`, plus `"configure"` for initial genre-pack mixer setup
- `volume`: 0.0-1.0

> **Removed (2026-04):** `TTS_START`, `TTS_CHUNK`, `TTS_END`, `VOICE_TEXT`,
> and `VOICE_SIGNAL` have all been removed from the protocol. Kokoro TTS and
> WebRTC voice chat no longer exist in the system. See
> `docs/adr/076-narration-protocol-collapse-post-tts.md` for the cleanup
> decision and ADR-054 for the WebRTC history. The `"duck"` and `"restore"`
> audio-cue actions were also retired — they only ever ducked music under
> TTS voice playback.

### ACTION_QUEUE / CHAPTER_MARKER / ERROR
```json
{ "type": "ACTION_QUEUE", "payload": { "actions": [ ... ] } }
{ "type": "CHAPTER_MARKER", "payload": { "title": "Chapter 3", "location": "Dark Cave" } }
{ "type": "ERROR", "payload": { "message": "string", "reconnect_required": true } }
```
- `reconnect_required: true` → client must re-send SESSION_EVENT{connect} before retrying

---

## Binary Frames (historical)

> **Removed (2026-04):** Binary WebSocket frames used to carry raw TTS PCM
> audio (server → client) alongside JSON `TTS_CHUNK` messages. After TTS
> removal, **no production code path sends `Message::Binary`** through the
> WebSocket. See ADR-076 for the protocol cleanup and ADR-045 for the
> historical two-channel Web Audio engine description. ADR-038 still
> references a three-channel broadcast topology from the TTS era and is
> flagged for a status update.

---

## Session Lifecycle

```
1. Client opens WebSocket to /ws
2. Client sends SESSION_EVENT { event: "connect", player_name, genre, world }
3. Server responds with SESSION_EVENT:
   a. { event: "connected", has_character: false } → creation flow
   b. { event: "ready", initial_state: {...} } → game flow
4. If creation:
   - Server sends CHARACTER_CREATION { phase: "scene", ... } (repeat per scene)
   - Client responds with CHARACTER_CREATION { choice: ... }
   - Server sends CHARACTER_CREATION { phase: "confirmation", ... }
   - Server sends CHARACTER_CREATION { phase: "complete", character: {...} }
   → Client transitions to game phase
5. Game loop:
   - Client sends PLAYER_ACTION { action: "...", aside: bool }
   - Server sends THINKING
   - Server sends NARRATION (complete text) followed by NARRATION_END
     (turn completion marker carrying the final StateDelta)
   - Server may send: PARTY_STATUS, CONFRONTATION, CONFRONTATION_OUTCOME,
     IMAGE, AUDIO_CUE, CHAPTER_MARKER, SCRAPBOOK_ENTRY, SECRET_NOTE
   - In confrontations, dice exchanges go DICE_REQUEST → DICE_THROW → DICE_RESULT
   - On orbital chart open, ORBITAL_INTENT → ORBITAL_CHART; course intent
     uses COURSE_INTENT
6. Multiplayer turn flow (STRUCTURED mode):
   - All players submit PLAYER_ACTION independently
   - Server holds actions until SessionRoom.TurnBarrier resolves (all
     submitted or timeout — adaptive per active turn-takers, story 45-2)
   - One handler claims and calls narrator with combined action; others
     receive broadcast
   - Server sends TURN_STATUS per player as they submit; ACTION_REVEAL when
     the seal opens
   - Shared-world delta (location, encounter id, party adjacency) flows
     between turns via the shared-world handshake (story 45-1)
7. Pause / resume:
   - Server may emit GAME_PAUSED / GAME_RESUMED at any time
```

See ADR-036 for the three-mode turn coordination FSM and ADR-037 for the shared-world / per-player state architecture.

---

## State Delta Model

Carried in `NARRATION`, `NARRATION_END`, and `TURN_STATUS` payloads under `state_delta`:

```typescript
interface StateDelta {
  location?: string;
  characters?: CharacterState[];     // merged by name (upsert)
  quests?: Record<string, string>;   // merged by key
  items_gained?: ItemGained[];       // new items acquired this turn
}

interface CharacterState {
  name: string;          // merge key
  hp: number;
  max_hp: number;
  level: number;
  class: string;
  statuses: string[];
  inventory: string[];
}

interface ItemGained {
  name: string;          // short item name
  description: string;   // one-sentence description
  category: string;      // weapon, armor, tool, consumable, quest, misc
}
```

Client maintains a `ClientGameState` by replaying all deltas. Characters are merged by `name` (upsert). Quests are merged by key. Items gained trigger inventory notifications.

---

## Server-Side Slash Commands

Commands starting with `/` are intercepted before intent classification by `sidequest-server/sidequest/game/commands.py`. Responses route through the existing turn-flow types (NARRATION, PARTY_STATUS, CONFRONTATION, ERROR).

| Command | Response Type | Description |
|---------|--------------|-------------|
| `/status` | NARRATION | Character status (narrative voice — ADR-040) |
| `/inventory` | NARRATION + PARTY_STATUS | Inventory readout |
| `/map` | NARRATION | Region / room readout (live map view retired 2026-04-28) |
| `/save` | NARRATION | Save confirmation |
| `/help` | NARRATION | Available commands |
| `/tone <axis> <value>` | NARRATION | Adjust genre alignment axes (ADR-052) |
| `/gm set <prop> <val>` | NARRATION + state delta | GM: modify game state |
| `/gm teleport <loc>` | NARRATION + CHAPTER_MARKER | GM: move party |
| `/gm spawn <npc>` | NARRATION + PARTY_STATUS | GM: create NPC |
| `/gm dmg <target> <amt>` | NARRATION + CONFRONTATION | GM: deal Edge damage |
