# SideQuest Server — Architecture

> System design for the SideQuest AI Narrator engine.
> Python package composition, narrator-primary agent model, three turn modes.
>
> **Last updated:** 2026-04-23 (post-ADR-082 cutover)

## Architectural Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React Client (sidequest-ui)                  │
│  ThemeProvider, GameLayout, NarrativeView, PartyPanel, CombatOverlay│
│  useGameSocket, useStateMirror, useMusicPlayer, 3D dice overlay     │
└────────┬──────────────────────────────────────┬─────────────────────┘
         │ WebSocket /ws (JSON)                  │ REST /api/genres
         ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Transport Layer (sidequest.server)                 │
│  FastAPI app, WebSocket upgrade, CORS, static files                 │
│  app.py, websocket.py, watcher.py, rest.py                          │
└────────┬────────────────────────────────────────────────────────────┘
         │ GameMessage (pydantic discriminated union)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Session Layer (sidequest.server)                  │
│  Per-connection state machine: Connect → Create → Play              │
│  SessionRoom for multiplayer (asyncio locks + broadcast channels)   │
│  session_handler.py, session_room.py, dispatch/                     │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Orchestrator Layer (sidequest.agents.orchestrator)    │
│  Intent routing → Agent dispatch → State patching → Broadcast       │
│  Slash command interception, TurnBarrier, perception rewriting      │
│  Pacing engine (TensionTracker → drama_weight → delivery mode)      │
└────────┬──────────────────────┬─────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────────┐ ┌────────────────────────────────────────────┐
│    Agent Layer       │ │              Game Layer                     │
│  (sidequest.agents)  │ │  (sidequest.game)                           │
│  Claude CLI subproc  │ │  ~70 modules: state, combat, chase, tropes,│
│  Unified narrator    │ │  inventory, NPCs, OCEAN, lore, conlang,    │
│  + auxiliary agents  │ │  faction agendas, world materialization,   │
│  + prompt_framework  │ │  music direction, barriers, dice resolve   │
└──────────────────────┘ └──────────────┬─────────────────────────────┘
                                        │
         ┌──────────────────────────────┤
         ▼                              ▼
┌──────────────────────┐ ┌────────────────────────────────────────────┐
│  Genre Layer         │ │           Persistence Layer                 │
│  (sidequest.genre)   │ │  sqlite3 (saves), PyYAML (genre packs)     │
│  YAML pack loader    │ │  Narrative log, KnownFact accumulation     │
│  6 genre packs       │ │  sidequest.game.persistence                │
└──────────────────────┘ └────────────────────────────────────────────┘

         ┌────────────────────────────────────────────────────────────┐
         │              Daemon Client (sidequest.daemon_client)        │
         │  Unix socket → sidequest-daemon (Python sidecar)           │
         │  Image gen (Flux / Z-Image), music (ACE-Step), SFX mixing  │
         └────────────────────────────────────────────────────────────┘
```

## Package Structure

```
sidequest-server/
├── pyproject.toml                     # hatchling build, uv-managed
├── sidequest/
│   ├── protocol/                      # GameMessage discriminated union, typed payloads
│   ├── genre/                         # YAML loader, genre pack models, 6 packs
│   ├── game/                          # ~30+ modules — state, combat, NPCs, lore, pacing, etc.
│   ├── agents/                        # Claude CLI subprocess, narrator + auxiliary agents
│   ├── server/                        # FastAPI HTTP/WS, session management, dispatch
│   ├── daemon_client/                 # Unix socket client for Python media daemon
│   ├── telemetry/                     # OTEL tracing and watcher event infrastructure
│   └── cli/                           # Entry points (encountergen, loadoutgen, namegen,
│                                      #   promptpreview, validate)
└── tests/                             # pytest + pytest-asyncio
```

The package composition mirrors the prior Rust crate layout 1:1 (per ADR-082). This was load-bearing during the port — any feature, span, or test can be compared across historical trees by path. Post-port refactoring is a separate decision; for now, structural fidelity wins ties.

**Dependency graph:**
```
sidequest.server
  ├── sidequest.agents
  │     └── sidequest.protocol
  ├── sidequest.game
  │     ├── sidequest.protocol
  │     └── sidequest.genre
  ├── sidequest.daemon_client
  └── sidequest.protocol
```

## Key Design Decisions

### ADR-001 / ADR-067: Claude CLI Only, Unified Narrator

All LLM calls use `claude -p` subprocess via `asyncio.create_subprocess_exec`. No Anthropic SDK. Claude Max subscription handles billing. The agent layer wraps this with timeout, stdout parsing, and error recovery. Per **ADR-067** (Unified Narrator Agent), the narrator is the primary agent — it handles exploration, dialogue, combat narration, and chase narration through a persistent Opus session. Auxiliary agents (`world_builder`, `troper`, `resonator`) run for specialist tasks outside the per-turn critical path. The original multi-agent dispatch (ADR-010: creature_smith, dialectician, ensemble) is superseded. `intent_router` remains as state-override classification (`in_combat` → Combat, `in_chase` → Chase, default → Exploration).

### ADR-002: Typed Protocol

Strongly-typed pydantic v2 models for every message payload. `GameMessage` is a discriminated union keyed on `type` (`Annotated[Union[...], Field(discriminator='type')]`). The type system catches payload mismatches at validation time — eliminates the `KeyError` class of bugs from legacy `dict[str, Any]` handlers. This is a strict upgrade over the pre-port Python ancestor; pydantic validation is enforced at the WebSocket boundary.

### ADR-003: Session as Actor

Each WebSocket connection runs as an asyncio task owning a `Session`. Single-player: one session, one orchestrator, no contention. Multiplayer: sessions share a `SessionRoom` behind `asyncio.Lock` with `TurnBarrier` for coordinated turn resolution.

### ADR-004: Genre Packs as YAML

6 genre packs loaded via PyYAML into pydantic models. Read-only at runtime. Shared with the `sidequest-content` repo as single source of truth. Each pack defines: world topology, NPC archetypes (with OCEAN profiles), item catalogs, trope definitions, audio themes, visual style, conlang morphemes, and faction agendas. Layered inheritance between genre and world tiers is handled via a base-class pattern in `sidequest.genre.models`.

### ADR-005: Background-First Pipeline

Only the text narration response is on the critical path. Everything else runs as asyncio tasks: image generation, music cue selection, state delta computation, trope tick, lore accumulation. The player sees narration immediately; media arrives asynchronously.

### ADR-006: Persistence via SQLite

Standard-library `sqlite3` for structured persistence (game state, character data, saves). DB calls run on a worker thread via `asyncio.to_thread` at the async boundary. Narrative log is append-only. KnownFacts persist and accumulate across turns with provenance tracking.

### ADR-035: Unix Socket IPC
Python ML sidecar communicates via Unix domain socket (`/tmp/sidequest-renderer.sock`) with newline-delimited JSON-RPC. Separate failure domain from the game engine. Models stay warm across sessions.

### ADR-036/037: Multiplayer State Architecture
`SessionRoom` keyed by `genre:world` holds world state; `PlayerState` holds per-player data. Sync-to-locals pattern checks out state for dispatch, preserving the single-player code path unchanged. `TurnBarrier` with adaptive timeout and claim-election prevents duplicate narrator calls.

### ADR-038: WebSocket Transport
Reader/writer task split per connection. Broadcast channels: JSON `GameMessage` for global state and session-scoped `TargetedMessage` for per-player narration. `ProcessingGuard` prevents concurrent dispatch per player. *(ADR-038 marks TTS binary channel as historical; see ADR-076.)*

### ADR-039/057: Narrator Output & Sidecar Tools
The narrator outputs prose only — no JSON blocks. Mechanical state changes (mood, intent, items acquired, quests, SFX, resource deltas, personality events, scene renders) are handled by sidecar tools that write JSONL results during narration. `assemble_turn` merges tool results with narration, with tool values always taking precedence. The old three-tier JSON extraction fallback (ADR-039/013) is superseded by this tool-based approach.

### ADR-059: Monster Manual — Server-Side Pre-Generation
NPC and encounter data is pre-generated server-side using Python CLI entry points (`namegen`, `encountergen`, `loadoutgen`) and stored in a persistent Monster Manual at `~/.sidequest/manuals/{genre}_{world}.json`. The narrator sees pre-generated NPCs and enemies embedded in `<game_state>` as world facts ("NPCs nearby", "Hostile creatures"). Claude treats game_state as ground truth and uses exact names, dialogue quirks, and abilities. Post-narration gate matches mentioned names against the Manual via compound key `(name, faction, world)` for stat block enrichment. This replaced narrator-side tool calling (ADR-056), which failed empirically — Claude in `claude -p` mode consistently ignores `--allowedTools` instructions.

### ADR-047: Input Sanitization
All player text passes through `sanitize_player_text()` at the protocol layer — strips injection attempts before routing.

## Game Systems (sidequest.game, ~30+ modules)

### Core State
- **GameState:** Central state composition — characters, NPCs, world, combat, chase
- **State deltas:** JSON patches for incremental updates, broadcast to all clients
- **Session persistence:** Save/load GameSnapshot via SQLite

### Combat & Chase
- **Combat:** Turn-based with combatant tracking, HP management, ability resolution
- **Chase:** Beat-based cinematic chases with Lead variable and rig mechanics (ADR-017)
- **Consequences:** Action outcome tracking
- **Consequence engine:** Genie Wish detection with rotating consequence types (ADR-041)

### Characters & NPCs
- **Character:** Unified model — narrative identity + mechanical stats (ADR-007)
- **NPC:** OCEAN personality profiles (0.0-10.0), disposition system, behavioral summaries
- **OCEAN evolution:** Live personality shifts via narrator-extracted events (ADR-042)
- **Guest NPCs:** Human-controlled NPCs in multiplayer (ADR-029)
- **Character builder:** Genre-driven scene-based creation state machine (ADR-015/016)

### Narrative Systems
- **KnownFact:** Play-derived knowledge with tiered injection by relevance
- **Lore:** LoreFragment/LoreStore, genre pack seeding, semantic retrieval (ADR-048: cross-process embedding via daemon)
- **Conlang:** Morpheme glossary, name bank generation, transliteration growth (ADR-043)
- **Scene directives:** Mandatory narrator instructions with engagement multiplier
- **Footnotes:** Structured output with discovery/callback typing

### World Systems
- **Faction agendas:** Goals + urgency, injected into scenes per turn
- **World materialization:** Campaign maturity levels (fresh/early/mid/veteran)
- **Trope engine:** Genre-defined narrative pacing via lifecycle management (ADR-018)
- **Cartography:** Graph-based topology with fog of war (ADR-019)

### Pacing & Drama
- **TensionTracker:** Dual-track model — gambler's ramp + HP stakes + event spikes
- **Drama-aware delivery:** INSTANT (<0.30) / SENTENCE (0.30-0.70) / STREAMING (>0.70)
- **Quiet turn detection:** Escalation beat injection after sustained low drama
- **Beat filter:** Suppress media renders for low-weight beats

### Multiplayer
- **TurnBarrier:** Wait for all players, adaptive timeout (3s for 2-3, 5s for 4+)
- **Turn modes:** FREE_PLAY, STRUCTURED, CINEMATIC
- **Party action composition:** Multi-character PARTY ACTIONS block
- **Perception rewriter:** Per-player narration variants based on status effects
- **Two-tier turn counter:** Interaction (monotonic) vs Round (narrative beats) — ADR-051
- **Catch-up narration:** Snapshot + "Previously On..." for mid-session joins

### Media Integration
- **Music director:** Mood extraction from narration → audio cue selection
- **Image pacing throttle:** Configurable cooldown (30s solo, 60s multiplayer) with DM override (ADR-050)
- **Render queue:** Speculative prerendering with hash-based cache dedup (ADR-044)
- **Subject extractor:** Prose → visual description via Claude CLI
- **Client audio:** Music + SFX channels only. Voice/TTS pipeline removed — ADR-045 and ADR-054 describe the historical architecture and are marked for retirement.

### Player Interface
- **Slash router:** Server-side /command interception before intent classification
- **Commands:** /status, /inventory, /map, /save, /help, /tone, /gm suite
- **Inventory:** Items by type, equipped state, merchant transactions
- **Progression:** Milestones, affinities, item evolution, wealth (ADR-021)

## Multiplayer Architecture

```
Client A ──ws──► Session A ─┐
                             ├──► SessionRoom (asyncio.Lock)
Client B ──ws──► Session B ─┘        │
                                     ├── TurnBarrier (adaptive timeout)
Client C ──ws──► Session C ──────────┤   └── Resolution lock (one narrator call)
                                     ├── Game State (single source of truth)
                                     ├── Orchestrator (agent dispatch)
                                     ├── Perception rewriter (per-player variants)
                                     └── State deltas broadcast to all sessions
```

Three turn modes govern coordination:
- **FREE_PLAY:** Actions process immediately, no barrier
- **STRUCTURED:** Sealed letter pattern — all submit, then barrier resolves, one narrator call
- **CINEMATIC:** DM-driven, players observe

## What Stays in sidequest-daemon (Python sidecar)

The ML inference pipeline is its own service. `sidequest.daemon_client` communicates over Unix socket (ADR-035). The daemon is out of scope for the server and has uses beyond SideQuest.

| Subsystem | Stack | Notes |
|-----------|-------|-------|
| Image generation | Flux.1 / Z-Image Turbo, MLX | Multiple render tiers, scene cache, beat filter |
| Music library | ACE-Step pre-render | Mood-indexed theme tracks, cross-fade on scene change |
| Audio mixing | pygame mixer | Music + SFX channels only (no voice/TTS) |
| Scene interpretation | Pattern matching | Narrative text → structured stage cues |
| Subject extraction | Claude CLI | Prose → visual descriptions |

```
sidequest-server (Python)  ◄──── Unix socket ────►  sidequest-daemon (Python)
     │                                                     │
     ├── Sends: narrative text, scene context              ├── Returns: image URLs, audio paths
     ├── Sends: music cue requests (mood / intensity)      ├── Returns: track identifiers
     └── Shares: genre_packs/ (read-only assets)           └── Reads: genre_packs/ visual/audio config
```

## ADR Index

Architecture Decision Records govern the system. See [docs/adr/README.md](adr/README.md) for the current index. Post-ADR-082 cutover, decomposition-era ADRs that describe Rust crate layouts (060-065, 072) carry post-port mapping notes to the Python package tree; narrative and game-design ADRs remain untouched as language-agnostic historical records.

## Wiring Diagrams

For end-to-end signal traces showing every feature's path from UI input through server layers to storage, see [docs/wiring-diagrams.md](wiring-diagrams.md). Covers all 15 feature areas with Mermaid flowcharts, file paths, and function names.

## History

The backend was originally written in Python (archived as `sq-2`), briefly ported to Rust as `sidequest-api` (~2026-03-30) as a learning exercise and for type-safety benefits, and then ported back to Python as `sidequest-server` per **ADR-082** (2026-04-19). **ADR-085** governed sprint-tracker hygiene through the cutover window. The Rust tree no longer exists on disk as of 2026-04-23. Design artifacts from the Rust era — crate boundaries, OTEL span catalog, the typed-protocol discipline — carried forward as the Python package composition; the code itself did not.
