# SideQuest API Contract

> Extracted from `sidequest-ui` — defines the interface the Rust backend must implement.

## Transport

### WebSocket

- **URL:** `ws://{host}/ws` (or `wss://` over TLS)
- **Protocol:** JSON text frames for game messages, binary frames for voice audio
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

## Message Types (enum)

```
PLAYER_ACTION       client → server
SESSION_EVENT       bidirectional
CHARACTER_CREATION  bidirectional
VOICE_SIGNAL        bidirectional (WebRTC signaling)

NARRATION           server → client
NARRATION_CHUNK     server → client (streaming)
NARRATION_END       server → client (stream complete)
THINKING            server → client
TURN_STATUS         server → client
PARTY_STATUS        server → client
CHARACTER_SHEET     server → client
INVENTORY           server → client
MAP_UPDATE          server → client
COMBAT_EVENT        server → client
IMAGE               server → client
AUDIO_CUE           server → client
VOICE_TEXT          server → client
ACTION_QUEUE        server → client
CHAPTER_MARKER      server → client
ERROR               server → client
```

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
  "payload": { "phase": "string", "choice": "string", ... },
  "player_id": ""
}
```

### VOICE_SIGNAL (outbound)
WebRTC signaling relay.
```json
{
  "type": "VOICE_SIGNAL",
  "payload": { "target": "peer_id", "signal": { ... } },
  "player_id": ""
}
```

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
  "payload": { "event": "ready" }
}
```
→ Client enters game phase.

**Initial state (on ready):**
```json
{
  "type": "SESSION_EVENT",
  "payload": {
    "event": "ready",
    "initial_state": {
      "characters": [{ "name": "", "hp": 0, "max_hp": 0, "statuses": [], "inventory": [] }],
      "location": "string",
      "quests": { "quest_name": "status_string" }
    }
  }
}
```

**Theme CSS:**
```json
{
  "type": "SESSION_EVENT",
  "payload": { "event": "theme_css", ... }
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

### NARRATION / NARRATION_CHUNK / NARRATION_END
Narrative text from the AI. Can include state deltas.

```json
{
  "type": "NARRATION",
  "payload": {
    "text": "The orc lunges...",
    "state_delta": {
      "location": "Dark Cave",
      "characters": [{ "name": "Grok", "hp": 15, "max_hp": 20, "statuses": ["poisoned"], "inventory": ["sword"] }],
      "quests": { "Find the Gem": "in_progress" }
    }
  }
}
```

`NARRATION_CHUNK` streams partial text. `NARRATION_END` signals end of stream. Both clear the "thinking" indicator.

### THINKING
Server is processing (shows spinner).
```json
{ "type": "THINKING", "payload": {} }
```

### TURN_STATUS
Turn/round tracking. Can include state deltas.
```json
{
  "type": "TURN_STATUS",
  "payload": {
    "state_delta": { ... }
  }
}
```

### PARTY_STATUS
Full party snapshot (richer than state_delta characters).
```json
{
  "type": "PARTY_STATUS",
  "payload": {
    "members": [
      {
        "player_id": "string",
        "name": "string",
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

### CHARACTER_SHEET
Full character details for the sheet overlay.
```json
{
  "type": "CHARACTER_SHEET",
  "payload": {
    "name": "string",
    "class": "string",
    "level": 1,
    "stats": { "strength": 16, "dexterity": 12 },
    "abilities": ["Power Strike", "Shield Bash"],
    "backstory": "string",
    "portrait_url": "https://..."
  }
}
```

### INVENTORY
Full inventory snapshot.
```json
{
  "type": "INVENTORY",
  "payload": {
    "items": [
      { "name": "Iron Sword", "type": "weapon", "equipped": true, "quantity": 1, "description": "A sturdy blade" }
    ],
    "gold": 150
  }
}
```

### MAP_UPDATE
World map state for the map overlay.
```json
{
  "type": "MAP_UPDATE",
  "payload": {
    "current_location": "Dark Cave",
    "region": "Shadowlands",
    "explored": [
      { "name": "Dark Cave", "x": 100, "y": 200, "type": "dungeon", "connections": ["Forest Path"] }
    ],
    "fog_bounds": { "width": 500, "height": 400 }
  }
}
```

### COMBAT_EVENT
Combat state for the combat overlay. Send `in_combat: false` to dismiss.
```json
{
  "type": "COMBAT_EVENT",
  "payload": {
    "in_combat": true,
    "enemies": [
      { "name": "Goblin", "hp": 8, "max_hp": 12, "ac": 13 }
    ],
    "turn_order": ["Player", "Goblin", "Orc"],
    "current_turn": "Player"
  }
}
```

### IMAGE
Image delivery (portraits, handouts, scene art).
```json
{
  "type": "IMAGE",
  "payload": {
    "url": "https://...",
    "description": "A crumbling tower",
    "handout": true,
    "render_id": "unique-id"
  }
}
```
- `handout: true` → added to journal

### AUDIO_CUE
Background music and sound effects.
```json
{
  "type": "AUDIO_CUE",
  "payload": {
    "mood": "combat",
    "music_track": "battle_theme_01",
    "sfx_triggers": ["sword_clash", "explosion"]
  }
}
```

### VOICE_SIGNAL (inbound)
WebRTC signaling relay from another peer.
```json
{
  "type": "VOICE_SIGNAL",
  "payload": { "from": "peer_id", "signal": { ... } }
}
```

### VOICE_TEXT
TTS text companion (displayed alongside audio).
```json
{ "type": "VOICE_TEXT", "payload": { ... } }
```

### ACTION_QUEUE / CHAPTER_MARKER / ERROR
```json
{ "type": "ACTION_QUEUE", "payload": { ... } }
{ "type": "CHAPTER_MARKER", "payload": { ... } }
{ "type": "ERROR", "payload": { "message": "string" } }
```

---

## Binary Frames: Voice Audio

Binary WebSocket frames carry TTS audio (server → client).

**Frame format:**
```
[4 bytes: header length (uint32 big-endian)]
[N bytes: JSON header]
[remaining: raw audio data]
```

**Header:**
```json
{
  "type": "VOICE_AUDIO",
  "segment_id": "unique-id",
  "format": "pcm_s16le",
  "sample_rate": 24000
}
```

Audio data is raw PCM signed 16-bit little-endian, routed through the client's AudioEngine voice channel with music ducking.

---

## Session Lifecycle

```
1. Client opens WebSocket to /ws
2. Client sends SESSION_EVENT { event: "connect", player_name, genre, world }
3. Server responds with SESSION_EVENT:
   a. { event: "connected", has_character: false } → creation flow
   b. { event: "ready", initial_state: {...} } → game flow
4. If creation:
   - Server sends CHARACTER_CREATION { phase: "scene", ... } (repeat)
   - Client responds with CHARACTER_CREATION { choice: ... }
   - Server sends CHARACTER_CREATION { phase: "complete", character: {...} }
   → Client transitions to game phase
5. Game loop:
   - Client sends PLAYER_ACTION { action: "...", aside: bool }
   - Server sends THINKING → NARRATION_CHUNK* → NARRATION_END
   - Server may send state updates via PARTY_STATUS, MAP_UPDATE, COMBAT_EVENT, etc.
```

---

## State Delta Model

Carried in `NARRATION` and `TURN_STATUS` payloads under `state_delta`:

```typescript
interface StateDelta {
  location?: string;
  characters?: CharacterState[];   // merged by name
  quests?: Record<string, string>; // merged by key
}

interface CharacterState {
  name: string;
  hp: number;
  max_hp: number;
  statuses: string[];
  inventory: string[];
}
```

Client maintains a `ClientGameState` by replaying all deltas. Characters are merged by `name` (upsert). Quests are merged by key.
