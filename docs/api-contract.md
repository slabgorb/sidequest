# SideQuest API Contract

> WebSocket + REST protocol between sidequest-server (Python) and sidequest-ui (React).
> Source of truth: `sidequest-server/sidequest/protocol/messages.py` (pydantic v2 discriminated union).
>
> **Last updated:** 2026-04-23 (post-ADR-082 cutover)
>
> *Historical note:* between 2026-03-30 and 2026-04-19 the source of truth was
> `sidequest-api/crates/sidequest-protocol/src/message.rs` (Rust). ADR-082 ported
> the protocol to pydantic with byte-identical JSON on the wire; the message
> type set and payload shapes documented below are unchanged by the port.

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

## Message Types (33 total)

```
Client → Server:
  PLAYER_ACTION       Player game input
  SESSION_EVENT       Session lifecycle (connect)
  CHARACTER_CREATION  Creation scene response
  VOICE_SIGNAL        WebRTC signaling (outbound)
  JOURNAL_REQUEST     Request journal contents

Server → Client:
  NARRATION           Complete narration with state delta + footnotes
  NARRATION_END       Turn-completion marker, carries final state delta
  THINKING            Processing indicator (spinner)
  SESSION_EVENT       Session lifecycle (connected, ready, theme_css)
  CHARACTER_CREATION  Creation scene prompt / confirmation / complete
  TURN_STATUS         Turn/round tracking with player status
  PARTY_STATUS        Full party snapshot
  CHARACTER_SHEET     Full character details for sheet overlay
  INVENTORY           Full inventory snapshot
  MAP_UPDATE          World map state for map overlay
  COMBAT_EVENT        Combat state for combat overlay
  CONFRONTATION       Confrontation engine state (resource pools)
  RENDER_QUEUED       Image render queued notification
  IMAGE               Image delivery (scene, portrait, handout)
  AUDIO_CUE           Music and SFX control
  ACTION_QUEUE        Queued actions
  ACTION_REVEAL       Sealed letter action reveal (multiplayer)
  CHAPTER_MARKER      Chapter/scene transition
  SCENARIO_EVENT      Scenario lifecycle events
  ACHIEVEMENT_EARNED  Achievement/milestone notification
  JOURNAL_RESPONSE    Journal contents response
  ITEM_DEPLETED       Item consumed/destroyed notification
  RESOURCE_MIN_REACHED Resource threshold warning
  ERROR               Error with optional reconnect_required flag
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

### CHARACTER_SHEET
Full character details for the sheet overlay.
```json
{
  "type": "CHARACTER_SHEET",
  "payload": {
    "name": "string",
    "class": "string",
    "race": "string",
    "level": 1,
    "stats": { "strength": 16, "dexterity": 12 },
    "abilities": ["Power Strike", "Shield Bash"],
    "backstory": "string",
    "personality": "string",
    "pronouns": "string",
    "equipment": ["Iron Sword", "Leather Armor"],
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
    "render_id": "unique-id",
    "tier": "scene",
    "scene_type": "exploration",
    "generation_ms": 3200
  }
}
```
- `handout: true` → added to journal
- `tier`: "portrait", "scene", "landscape", "abstract", "text", "cartography", "tactical"
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
   - Server may send: PARTY_STATUS, MAP_UPDATE, COMBAT_EVENT, IMAGE,
     AUDIO_CUE, CHAPTER_MARKER
6. Multiplayer turn flow (STRUCTURED mode):
   - All players submit PLAYER_ACTION independently
   - Server holds actions until TurnBarrier resolves (all submitted or timeout)
   - One handler calls narrator with combined action; others receive broadcast
   - Server sends TURN_STATUS per player as they submit
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

Commands starting with `/` are intercepted before intent classification. Responses use existing message types (NARRATION, CHARACTER_SHEET, INVENTORY, MAP_UPDATE, ERROR).

| Command | Response Type | Description |
|---------|--------------|-------------|
| `/status` | CHARACTER_SHEET | Full character sheet |
| `/inventory` | INVENTORY | Full inventory snapshot |
| `/map` | MAP_UPDATE | Current map state |
| `/save` | NARRATION | Save confirmation |
| `/help` | NARRATION | Available commands |
| `/tone <axis> <value>` | NARRATION | Adjust genre alignment axes |
| `/gm set <prop> <val>` | NARRATION | GM: modify game state |
| `/gm teleport <loc>` | NARRATION + MAP_UPDATE | GM: move party |
| `/gm spawn <npc>` | NARRATION | GM: create NPC |
| `/gm dmg <target> <amt>` | NARRATION + COMBAT_EVENT | GM: deal damage |
