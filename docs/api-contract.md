# SideQuest API Contract

> WebSocket + REST protocol between sidequest-server (Python) and sidequest-ui (React).
> Source of truth: `sidequest-server/sidequest/protocol/messages.py` (pydantic v2 discriminated union),
> `sidequest-server/sidequest/protocol/enums.py` (MessageType), and the supporting modules
> `sidequest-server/sidequest/protocol/{models,dice,course_intent,orbital_intent,dispatch}.py`.
>
> **Last updated:** 2026-05-11
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
  ACTION_REVEAL         Peer action-text reveal (multiplayer; collaborative visibility per ADR-036 amendment 2026-05-03)
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
- `aside: true` on `PLAYER_ACTION` = an out-of-band OOC question to the GM
  (ADR-107). It is a non-turn input: it spends no turn, advances the world
  not at all, and does not count toward the multiplayer submit-and-wait
  barrier (ADR-036). The server answers with an `ASIDE_ANSWER` message
  broadcast to the whole room (table-visible). The asker still owes their
  normal action for the turn to resolve — an aside costs no turn.
- `ASIDE_ANSWER` payload: `{ asker_id, question, answer, grounded_on[],
  round }`. `round` is for client ordering only — it is never a turn record.
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

### ACTION_REVEAL (outbound — live teammate typing)
Broadcasts in-progress action text to peers in real time. ADR-036 amendment 2026-05-03 (Action Visibility Model). Clients send `composing` (debounced ~250ms) and `submitted`; the server emits `cleared` and clients sending `cleared` are silently dropped.

```json
{
  "type": "ACTION_REVEAL",
  "payload": {
    "player_id": "",
    "character_name": "Rux",
    "status": "composing",
    "action": "I creep along the rafters",
    "aside": false,
    "seq": 3,
    "round": 0
  },
  "player_id": ""
}
```

- `player_id` and `round` are server-stamped on fan-out — client-supplied values are overwritten (`handlers/action_reveal.py:107-112`).
- `seq` is monotonic per `(player_id, round)`; receivers drop non-monotonic seq within a round. Round transitions hard-flush state.
- `status` ∈ `composing` | `submitted` | `cleared` (`cleared` is server-only).
- `action` is the current text; empty string when `status="cleared"`.
- `aside: true` marks the in-progress text as an out-of-band OOC question
  (ADR-107), not an in-fiction action. It is mirrored to peers as OOC
  table-talk and resolved via `ASIDE_ANSWER` — it does not become narration
  and does not count toward the ADR-036 barrier.
- Server rate-limit floor: 100ms per socket for `composing` (excess silently dropped, OTEL counter increments). `submitted` bypasses the floor.

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
{ "type": "NARRATION_END", "payload": { "state_delta": { ... }, "round": 5 } }
```

`NARRATION_END` clears the "thinking" indicator and commits any final
`state_delta` in the same render cycle as the preceding `NARRATION` text.
Always sent, even when the turn produced no state delta.

`round` (added 2026-06-07, server #741) is the round the turn **resolved** —
captured before `record_interaction()` bumps the counter, so it matches the
`round` on the turn's `ACTION_REVEAL` entries. The UI anchors persisted
peer-action quotes into the transcript by this round (ui #351); the own
`PLAYER_ACTION` round remains a legacy fallback. Dice-driven turns (beat
commits ride `DICE_THROW`, never `PLAYER_ACTION`) have no other round
carrier. `null`/absent on legacy frames.

> **Removed (2026-04, per ADR-076):** `NARRATION_CHUNK` was a streaming
> partial-text variant paired with binary TTS voice frames. With TTS gone,
> the chunked streaming path has zero production senders. The variant still
> exists in `sidequest-protocol/src/message.rs` but will be removed when
> ADR-076 moves from Proposed to Accepted.

> **Removed (2026-06-07, operator-directed):** `narration.delta` (the
> Story 71-23 ephemeral streaming message — `kind` not `type`, outside the
> `GameMessage` union, never event-sourced) was deleted along with the entire
> narrator-text streaming feature (server #732, ui #349). Narration is
> delivered complete-only: the canonical `NARRATION` message is the first and
> only prose the client renders for a turn. The ADR-133 client
> streaming-narration accumulator was removed with it.

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

> **Per-beat `difficulty` — server-authored pre-roll DC (story 97-3, server `build_confrontation_payload`):** every beat object in `ConfrontationPayload.beats` carries a `difficulty: int` — the exact target number the server will resolve that beat against. The value is resolver-dependent: native dial packs send the beat DC (`clamp(10 + 2·|base|, 10..30)`); SWN-family `hp_depletion` attacks send the target's armor class; `opposed_check` confrontations send the per-side formula DC (`_opposed_dc`); cwn `hacking` (net_run) sends the security-tier DC + alert escalation. **The server is the only DC author** — the client renders this number on the beat tile and the TARGET banner and computes nothing; the old client-side `rawDc` formula is deleted. A beat offer *without* `difficulty` is treated as malformed: the UI refuses the commit loudly (console error + transient strip) rather than inventing a number (No Silent Fallbacks). Offers built by legacy/bootstrap reconstruction paths (`rules=None`) omit the key by design and are uncommittable. The GM-panel lie-detector for the authorship decision is the `confrontation.beat_dc_authored` OTEL span (carries `ruleset` + `beat_difficulties`); it must agree with the resolution-time `dice.request_sent` difficulty.

> **Survivability fields — `hp` / `max_hp` / `current_hp` (ADR-114, ADR-078):** these wire fields carry **real hit points**. ADR-114 (Ablative HP Substrate, *partial — Part 1 live*) reintroduced HP as a first-class `HpPool` (`current` / `max` / `base_max`) on `CreatureCore`, shared by `Character` and `Npc` (`game/creature_core.py`), reversing ADR-078's earlier HP→composure deletion. There is **no longer an `EdgePool` (personal-composure) field on `CreatureCore`** — the only composure pool that survives is the vessel/`rig_pool`, surfaced separately as `rig_composure_current` / `rig_composure_max`.
>
> **What the fields carry, and the per-ruleset story.** `PartyMember.current_hp` / `max_hp` (PARTY_STATUS) are populated **unconditionally** from `character.core.hp.current` / `.max` (`server/views.py:506-511`) — there is no per-ruleset branch on this publish path, so they carry the HpPool for *every* pack regardless of which ruleset is bound. Genre packs select a pluggable ruleset module via `ruleset:` in `rules.yaml` (`game/ruleset/`; `native` = dial/confrontation engine per ADR-033/-078 is the default; the three Without-Number modules are all HP-based — `swn` = Stars Without Number (`space_opera`), `wwn` = Worlds Without Number (`elemental_harmony`), `cwn` = Cities Without Number (`neon_dystopia`); unknown names fail loud). The ruleset governs **combat resolution and win conditions**, not whether the HpPool exists — every ruleset carries an `HpPool` on `CreatureCore`. Where the ruleset *is* visible on the wire is the confrontation surface: `ConfrontationPayload` (`protocol/messages.py:759-792`) emits `win_condition` plus `player_hp` / `opponent_hp` (`{"current", "max"}`) under `hp_depletion` (the Without-Number HP path), and emits `win_condition="dial_threshold"` while omitting the hp fields for native dial packs.
>
> Near-term focus is HP. Three HP-based Without-Number rulesets are live: `swn` for `space_opera`, `wwn` for `elemental_harmony`, and `cwn` for `neon_dystopia`; a B/X or 3.5-SRD ruleset is planned for `caverns_and_claudes`. Personal Edge/Composure as a survivability substrate is slated to return with the planned Fate-SRD ruleset.
>
> `CharacterState` (`protocol/models.py:174-195`, `hp` / `max_hp` documented as current/maximum hit points) is the typed shape for `StateDelta.characters`, but is **not instantiated anywhere in the live server** — UI-facing party survivability travels via `PartyMember` in PARTY_STATUS, not via `StateDelta.characters`.
>
> **Frontend (transitional naming).** `CharacterPanel.tsx` and `CharacterSheet.tsx` render these values as HP/vitality — the panel guards the badge/tick bar on the values being present (renders nothing rather than a fake `0/0`), and the sheet shows an `HP {current}/{max}` bar conditional on `hp` / `hp_max` being set. The values are HP per ADR-114, but the UI rename is **not fully complete**: some surfaces still use the legacy `Edge` vocabulary in variable/component names (e.g. `hasEdge`, `EdgeBadge`, `FolioEdgeTicks`) and a couple of TS doc comments still describe the field as composure. Renaming the wire fields and the residual UI `Edge` identifiers remains an open cleanup; the runtime values are already HP.

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

### ACTION_REVEAL (inbound — peer fan-out)
Broadcast to all party members except the sender so peers can coordinate during cinematic-mode rounds. ADR-036 amendment 2026-05-03 (Action Visibility Model) — collaborative visibility is the default; the submit-and-wait barrier and CAS dispatcher are unaffected.

```json
{
  "type": "ACTION_REVEAL",
  "payload": {
    "player_id": "alex-123",
    "character_name": "Rux",
    "status": "submitted",
    "action": "I draw my pistol and watch the door.",
    "aside": false,
    "seq": 7,
    "round": 2
  },
  "player_id": "alex-123"
}
```

Lifecycle for one peer across a single round:

1. Peer types first char → `composing` with `seq=0`.
2. Peer keeps typing (250ms client debounce) → `composing` updates with monotonic `seq`.
3. Peer hits send → `submitted` with the final `action`.
4. Server-elected dispatcher fires barrier → server emits `cleared` for every peer (one per player, sequenced after the prior payload).
5. Round `N+1` opens; per-peer `seq` resets to 0; receivers hard-flush state on round transition.

**`cleared` is server-only.** It fires at three sites:
- *Dispatch* — `session_room._emit_action_reveal_cleared` runs at barrier-fire, before the narrator dispatches.
- *Disconnect* — last-socket disconnect emits `cleared` (`reason="disconnect"`) so peers don't see frozen ghost typing.
- *Timeout* — cinematic-mode timeout cleanup (not yet wired; placeholder).

**Privacy.** OTEL watcher events carry `text_length` only, never `action` content. Player input is sensitive; length + cadence + count are sufficient for the GM-panel lie-detector.

| OTEL event | Fields |
|---|---|
| `action_reveal.composing` | `slug`, `player_id`, `round`, `seq`, `text_length` |
| `action_reveal.submitted` | `slug`, `player_id`, `round`, `text_length`, `aside` |
| `action_reveal.cleared` | `slug`, `player_id`, `round`, `reason` ∈ {`dispatch`, `disconnect`, `timeout`} |
| `action_reveal.dropped_rate_limit` | `slug`, `player_id`, `round` (counter) |

See ADR-036 amendments (2026-05-03 + 2026-05-09) for the doctrine and the three-meaning disambiguation of "sealed-letter".

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
6. Multiplayer turn flow (Cinematic mode — the live default):
   - All players submit PLAYER_ACTION independently
   - Server holds actions until SessionRoom.TurnBarrier resolves (all
     submitted; timeout default deferred — story 45-2 closed the active-
     turn-takers vs lobby-count gap)
   - During the wait window, ACTION_REVEAL fans out continuously so peers
     see each other's in-progress and post-submit text (ADR-036 amendment
     2026-05-03; collaborative visibility is the default). Server stamps
     player_id + round; clients debounce composing updates at ~250ms.
   - One handler wins the CAS guard and calls narrator with the merged
     party action; others receive the broadcast.
   - At barrier-fire, server emits ACTION_REVEAL with status=cleared for
     every player before dispatching the narrator.
   - Server sends TURN_STATUS per player as they submit.
   - Shared-world delta (location, encounter id, party adjacency) flows
     between turns via the shared-world handshake (story 45-1).
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
