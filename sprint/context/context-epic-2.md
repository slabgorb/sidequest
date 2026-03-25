# Epic 2: Core Game Loop Integration

## Overview

Wire the five Rust crates from Epic 1 into a playable game loop. At the end of this
epic, a player can: connect via WebSocket, create a character through genre-defined
scenes, take actions in a turn loop, receive narrated responses from Claude agents,
and have their game state persisted to SQLite.

This is an integration epic — Epic 1 built the parts, Epic 2 connects them. Agent
behavior is already defined in the Python codebase (sq-2); the work here is faithful
Rust implementation with type-system enforcement, not behavior design.

## Background

### What Epic 1 Delivered (437 tests, all green)

| Crate | What's Done |
|-------|-------------|
| **sidequest-protocol** | 16 typed `GameMessage` variants, input sanitization, `NonBlankString` newtype |
| **sidequest-genre** | Unified YAML loader, 50+ models, `GenreCache`, trope resolution, validation |
| **sidequest-game** | `Character`, `NPC`, `CreatureCore`, `CombatState`, `ChaseState`, `Inventory`, `TurnManager`, `NarrativeEntry`, progression functions, `Disposition` newtype |
| **sidequest-agents** | 8 concrete agents (Narrator, CreatureSmith, Ensemble, Troper, WorldBuilder, Dialectician, Resonator, IntentRouter), `ClaudeClient`, `ContextBuilder`, prompt framework with attention zones |
| **sidequest-server** | Empty shell — dependencies configured, no routes |

### Remaining Epic 1 Stories (must complete first)

- **1-8**: `GameSnapshot`, typed patches, state delta, `TurnManager` integration, session persistence structs
- **1-11**: Agent implementations wired to orchestrator, `GameService` trait (branch exists, in review)
- **1-12**: axum router, WebSocket handler, `/api/genres` endpoint, service facade

### What the React UI Already Has

The UI (`sidequest-ui`) is a **complete game client** copied from sq-2:
- WebSocket connection with auto-reconnect
- Character creation flow (multi-scene with choices/freeform)
- Narrative display with markdown, images, chapters, thinking indicator
- Combat overlay, party panel, inventory, map, journal
- Audio engine, push-to-talk with local Whisper transcription
- 19 message types matching the Rust protocol

**The UI is waiting for a Rust server to talk to.** No UI changes needed for core loop.

### Python Reference (sq-2)

The Python orchestrator (`sq-2/sidequest/orchestrator.py`) implements the proven game loop:
1. Player input → sanitize → slash command check → intent routing
2. Intent → agent selection → system prompt refresh → context building
3. Agent dispatch (Claude CLI subprocess) → response streaming
4. Post-response: JSON patch extraction → state update → broadcast
5. Background pipelines: state save, trope tick, achievements

Key Python files to reference during implementation:
- `orchestrator.py` — turn loop hub, agent coordination (~2500 lines)
- `game/session.py` — SessionManager, save/load
- `game/character_builder.py` — character creation state machine
- `game/state.py` — GameState model (what becomes GameSnapshot)
- `state_processor.py` — background turn processing
- `server/app.py` — aiohttp WebSocket server
- `agents/intent_router.py` — LLM-based intent classification

## Technical Architecture

### Session Lifecycle (ADR-003, ADR-012)

```
WebSocket Connect
       │
       ▼
   ┌─────────┐     SESSION_EVENT{connect}
   │ Connect  │◄─── player_name, genre, world
   └────┬─────┘
        │  bind genre pack, check for save
        ▼
   ┌─────────┐     CHARACTER_CREATION messages
   │ Create   │◄──► builder state machine
   └────┬─────┘
        │  character complete
        ▼
   ┌─────────┐     PLAYER_ACTION / NARRATION / state messages
   │  Play    │◄──► orchestrator turn loop
   └─────────┘
```

Each WebSocket connection spawns a dedicated tokio task owning a `Session`.
Sessions hold: genre pack ref (`Arc<GenrePack>`), game state, agent handles.

### Turn Loop (ADR-006, ADR-010)

```
PLAYER_ACTION received
       │
       ▼
  Intent Router (LLM classify → Combat/Dialogue/Exploration/Examine/Meta)
       │
       ▼
  Agent Dispatch (compose prompt with genre + state context → claude -p)
       │
       ▼
  Response Stream (THINKING → NARRATION_CHUNK* → NARRATION_END)
       │
       ▼
  State Patch (extract JSON → apply combat/chase/world patches)
       │
       ▼
  Broadcast (PARTY_STATUS, MAP_UPDATE, TURN_STATUS, state_delta)
       │
       ▼
  Background (save state, tick tropes, check achievements)
```

### Persistence (ADR-006, ADR-023)

SQLite replaces Python's JSON file I/O:
- `game_state` table: serialized GameSnapshot (atomic writes)
- `narrative_log` table: append-only entries (round, author, content, timestamp)
- `session_meta` table: genre, world, created_at, last_played
- "Previously On..." recap generated from recent narrative entries on load

### Key ADRs for This Epic

| ADR | Relevance |
|-----|-----------|
| ADR-003 | Session as actor (tokio task per connection) |
| ADR-005 | Claude CLI subprocess (`claude -p`), not SDK |
| ADR-006 | SQLite persistence, not JSON files |
| ADR-010 | Intent-based agent routing |
| ADR-011 | World state JSON patches |
| ADR-012 | Agent session management |
| ADR-013 | Lazy JSON extraction (3-tier fallback) |
| ADR-015 | Character builder state machine |
| ADR-018 | Trope engine lifecycle |
| ADR-023 | Session persistence with "Previously On..." |
| ADR-026 | Client state mirror (server sends deltas) |
| ADR-027 | Reactive state messaging (broadcast patterns) |

## Deferred (Not in This Epic)

- **Image rendering** — sidequest-daemon stays Python, wired later
- **TTS / voice synthesis** — same, stays in daemon
- **Audio/music pipeline** — UI has the engine, server just needs AUDIO_CUE messages later
- **WebRTC voice chat** — P2P, doesn't need server changes
- **Multiplayer turn barrier** — single-player first, barrier comes in a future epic
- **Speculative pre-generation** — optimization, not core loop
- **Scenario-specific logic** — whodunit/rat-hunt bottle episodes deferred
- **Perception rewriter** — per-character narration variants (ADR-028), multiplayer feature
- **Slash commands** — local in UI already, server-side can come later

## Dependencies

### From Epic 1 (must complete)
- Story 1-8: GameSnapshot + state delta (2-4 and 2-5 depend on this)
- Story 1-11: Agent implementations + orchestrator scaffold (2-5 depends on this)
- Story 1-12: Server axum skeleton (2-1 extends this)

### External
- Claude CLI installed and accessible as `claude` command
- Genre pack YAML at configured `--genre-packs-path`
- `mutant_wasteland/flickering_reach` for testing (fully spoilable)

## Success Criteria

A human can:
1. Start the Rust API server
2. Open the React UI in a browser
3. Connect with a player name and select a genre/world
4. Go through character creation scenes
5. Take an action ("I look around the tavern")
6. See a narrated response stream into the UI
7. See party status update with character state
8. Close and reopen — game state persists

## Cross-Epic Dependencies

This epic enables:
- **Epic 3** (future): Media integration — wire sidequest-daemon for images/audio/TTS
- **Epic 4** (future): Multiplayer — turn barrier, perception rewriter, party management
- **Epic 5** (future): Scenario packs — whodunit, rat-hunt, bottle episodes
