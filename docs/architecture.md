# SideQuest API — Architecture

> System design for the Rust port of the SideQuest AI Narrator engine.
> 12-crate workspace, ~70 game modules, narrator-primary agent model, 3 turn modes.
>
> **Last updated:** 2026-04-11

## Architectural Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React Client (sidequest-ui)                  │
│  ThemeProvider, GameLayout, NarrativeView, PartyPanel, CombatOverlay│
│  useGameSocket, useStateMirror, useMusicPlayer, 3D dice overlay     │
└────────┬──────────────────────────────────────┬─────────────────────┘
         │ WebSocket /ws (JSON + binary PCM)     │ REST /api/genres
         ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Transport Layer (sidequest-server)              │
│  axum Router, WebSocket upgrade, CORS, static files                 │
│  router.rs, ws.rs, telemetry.rs, render_integration.rs              │
└────────┬────────────────────────────────────────────────────────────┘
         │ GameMessage (sidequest-protocol)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Session Layer (sidequest-server)                │
│  Per-connection state machine: Connect → Create → Play              │
│  SharedGameSession for multiplayer (Arc<RwLock<>>)                  │
│  session.rs, shared_session.rs, lifecycle.rs, dispatch.rs           │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer (sidequest-server/lib.rs)      │
│  Intent routing → Agent dispatch → State patching → Broadcast       │
│  Slash command interception, TurnBarrier, perception rewriting      │
│  Pacing engine (TensionTracker → drama_weight → delivery mode)      │
└────────┬──────────────────────┬─────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────────┐ ┌────────────────────────────────────────────┐
│    Agent Layer       │ │              Game Layer (sidequest-game)    │
│  (sidequest-agents)  │ │  ~70 modules: state, combat, chase, tropes,│
│  Claude CLI subproc  │ │  inventory, NPCs, OCEAN, lore, conlang,    │
│  Unified narrator    │ │  faction agendas, world materialization,   │
│  + auxiliary agents  │ │  music direction, barriers, dice resolve   │
└──────────────────────┘ └──────────────┬─────────────────────────────┘
                                        │
         ┌──────────────────────────────┤
         ▼                              ▼
┌──────────────────────┐ ┌────────────────────────────────────────────┐
│  Genre Layer         │ │           Persistence Layer                 │
│  (sidequest-genre)   │ │  rusqlite (saves), serde_yaml (genre packs)│
│  YAML pack loader    │ │  Narrative log, KnownFact accumulation     │
│  11 genre packs       │ │  persistence.rs                            │
└──────────────────────┘ └────────────────────────────────────────────┘

         ┌────────────────────────────────────────────────────────────┐
         │              Daemon Client (sidequest-daemon-client)        │
         │  Unix socket → sidequest-daemon (Python sidecar)           │
         │  Image gen (Flux), music (ACE-Step), SFX mixing (pygame)   │
         └────────────────────────────────────────────────────────────┘
```

## Workspace Structure

```
sidequest-api/
├── Cargo.toml                        # [workspace] root
├── crates/
│   ├── sidequest-protocol/           # GameMessage enum, typed payloads, serde
│   ├── sidequest-genre/              # YAML loader, genre pack structs, 11 packs
│   ├── sidequest-game/               # ~70 modules — state, combat, NPCs, lore, pacing, etc.
│   ├── sidequest-agents/             # Claude CLI subprocess, narrator + auxiliary agents
│   ├── sidequest-server/             # axum HTTP/WS, session management, orchestrator
│   ├── sidequest-daemon-client/      # Unix socket client for Python media daemon
│   ├── sidequest-telemetry/          # OTEL tracing and watcher event infrastructure
│   ├── sidequest-validate/           # Genre pack validation utilities
│   ├── sidequest-encountergen/       # CLI: enemy stat block generator
│   ├── sidequest-loadoutgen/         # CLI: starting equipment generator
│   ├── sidequest-namegen/            # CLI: NPC identity block generator
│   └── sidequest-promptpreview/      # CLI: prompt template preview tool
└── tests/                            # Integration tests
```

**Dependency graph:**
```
sidequest-server
  ├── sidequest-agents
  │     └── sidequest-protocol
  ├── sidequest-game
  │     ├── sidequest-protocol
  │     └── sidequest-genre
  ├── sidequest-daemon-client
  └── sidequest-protocol
```

## Key Design Decisions

### ADR-001 / ADR-067: Claude CLI Only, Unified Narrator

All LLM calls use `claude -p` subprocess via `tokio::process::Command`. No Anthropic SDK. Claude Max subscription handles billing. The agent layer wraps this with timeout, stdout parsing, and error recovery. Per **ADR-067** (Unified Narrator Agent), the narrator is the primary agent — it handles exploration, dialogue, combat narration, and chase narration through a persistent Opus session. Auxiliary agents (`world_builder`, `troper`, `resonator`) run for specialist tasks outside the per-turn critical path. The original multi-agent dispatch (ADR-010: creature_smith, dialectician, ensemble) is superseded; those agent files have been removed. `intent_router` remains in-crate as a lightweight fallback during the ADR-067 migration.

### ADR-002: Typed Protocol

Strongly-typed Rust structs for every message payload using `serde(tag = "type")` on the `GameMessage` enum. The type system catches payload mismatches at compile time — eliminates the `KeyError` class of bugs from the Python codebase. Current `GameMessage` variant count grows with each story; count is intentionally not tracked here to avoid stale documentation.

### ADR-003: Session as Actor

Each WebSocket connection spawns a tokio task owning a `Session`. Single-player: one session, one orchestrator, no contention. Multiplayer: sessions share a `SharedGameSession` behind `Arc<RwLock<>>` with `TurnBarrier` for coordinated turn resolution.

### ADR-004: Genre Packs as YAML

11 genre packs loaded via `serde_yaml` into typed structs. Read-only at runtime. Shared with sq-2 and sidequest-content repo. Each pack defines: world topology, NPC archetypes (with OCEAN profiles), item catalogs, trope definitions, audio themes, visual style, conlang morphemes, and faction agendas.

### ADR-005: Background-First Pipeline

Only the text narration response is on the critical path. Everything else spawns as background tasks: image generation, music cue selection, state delta computation, trope tick, lore accumulation. The player sees narration immediately; media arrives asynchronously.

### ADR-006: Persistence via SQLite

`rusqlite` for structured persistence (game state, character data, saves). Wrapped in `spawn_blocking` at the async boundary. Narrative log is append-only. KnownFacts persist and accumulate across turns with provenance tracking.

### ADR-035: Unix Socket IPC
Python ML sidecar communicates via Unix domain socket (`/tmp/sidequest-renderer.sock`) with newline-delimited JSON-RPC. Separate failure domain from the game engine. Models stay warm across sessions.

### ADR-036/037: Multiplayer State Architecture
SharedGameSession keyed by `genre:world` holds world state; PlayerState holds per-player data. Sync-to-locals pattern checks out state for dispatch, preserving the single-player code path unchanged. TurnBarrier with adaptive timeout and claim-election prevents duplicate narrator calls.

### ADR-038: WebSocket Transport
Reader/writer task split per connection. Broadcast channels: JSON `GameMessage` for global state and session-scoped `TargetedMessage` for per-player narration. ProcessingGuard prevents concurrent dispatch per player. *(Note: ADR-038 still references a binary-PCM audio channel from the TTS era — pending ADR update to match post-TTS reality.)*

### ADR-039/057: Narrator Output & Sidecar Tools
The narrator outputs prose only — no JSON blocks. Mechanical state changes (mood, intent,
items acquired, quests, SFX, resource deltas, personality events, scene renders) are handled
by sidecar tools that write JSONL results during narration. `assemble_turn` merges tool
results with narration, with tool values always taking precedence. The old three-tier JSON
extraction fallback (ADR-039/013) is superseded by this tool-based approach.

### ADR-059: Monster Manual — Server-Side Pre-Generation
NPC and encounter data is pre-generated server-side using Rust tool binaries (namegen,
encountergen, loadoutgen) and stored in a persistent Monster Manual at
`~/.sidequest/manuals/{genre}_{world}.json`. The narrator sees pre-generated NPCs and
enemies embedded in `<game_state>` as world facts ("NPCs nearby", "Hostile creatures").
Claude treats game_state as ground truth and uses exact names, dialogue quirks, and
abilities. Post-narration gate matches mentioned names against the Manual via compound
key `(name, faction, world)` for stat block enrichment. This replaced narrator-side
tool calling (ADR-056), which failed empirically — Claude in `claude -p` mode
consistently ignores `--allowedTools` instructions.

### ADR-047: Input Sanitization
All player text passes through `sanitize_player_text()` at the protocol layer — strips injection attempts before routing.

## Game Systems (sidequest-game, 71 modules)

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
                             ├──► SharedGameSession (Arc<RwLock<>>)
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

## What Stays in Python (sidequest-daemon)

The ML inference pipeline stays in Python as a sidecar service. Rust communicates via `sidequest-daemon-client` crate over Unix socket (ADR-035).

| Subsystem | Stack | Notes |
|-----------|-------|-------|
| Image generation | Flux.1 (schnell + dev) | Multiple render tiers, scene cache, beat filter |
| Music library | ACE-Step pre-render | Mood-indexed theme tracks, cross-fade on scene change |
| Audio mixing | pygame mixer | Music + SFX channels only (no voice/TTS) |
| Scene interpretation | Pattern matching | Narrative text → structured stage cues |
| Subject extraction | Claude CLI | Prose → visual descriptions |

```
sidequest-api (Rust)  ◄──── HTTP / Unix socket ────►  sidequest-daemon (Python)
     │                                                        │
     ├── Sends: narrative text, scene context                 ├── Returns: image URLs, audio paths
     ├── Sends: music cue requests (mood / intensity)         ├── Returns: track identifiers
     └── Shares: genre_packs/ (read-only assets)              └── Reads: genre_packs/ visual/audio config
```

## ADR Index

Architecture Decision Records govern the system. See [docs/adr/README.md](adr/README.md) for the current index. **Note:** several ADRs in the TTS / voice chat / WebRTC family describe historical architecture that has since been removed — pass 2 of the 2026-04-11 doc sweep will mark the affected ADRs (notably ADR-045, ADR-054, and media-channel references in ADR-038) with status updates.

## Wiring Diagrams

For end-to-end signal traces showing every feature's path from UI input through server layers to storage, see [docs/wiring-diagrams.md](wiring-diagrams.md). Covers all 15 feature areas with Mermaid flowcharts, file paths, and function names.
