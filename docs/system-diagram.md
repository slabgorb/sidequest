# SideQuest System Architecture

How the four repositories coordinate to run the SideQuest AI Narrator.

## Repository Ecosystem

```mermaid
graph TB
    subgraph "Orchestrator (oq-1)"
        ORC[oq-1<br/>Sprint tracking, scripts,<br/>cross-repo justfile]
    end

    subgraph "Game Engine (sidequest-api)"
        SERVER[sidequest-server<br/>axum HTTP/WebSocket]
        AGENTS[sidequest-agents<br/>Claude CLI orchestration]
        GAME[sidequest-game<br/>State, combat, chase, tropes]
        GENRE[sidequest-genre<br/>YAML pack loader]
        PROTO[sidequest-protocol<br/>Message types]
        DCLIENT[sidequest-daemon-client<br/>Unix socket client]
    end

    subgraph "React Client (sidequest-ui)"
        UI[React 19 + TypeScript<br/>Game client, audio engine,<br/>3D dice overlay, GM mode]
    end

    subgraph "Media Services (sidequest-daemon)"
        FLUX[Flux Worker<br/>Image generation MLX]
        MIXER[Audio Library<br/>+ pygame mixer]
    end

    subgraph "Asset Library (sidequest-content)"
        PACKS[Genre Packs<br/>YAML configs, audio,<br/>images, worlds]
    end

    UI -->|WebSocket /ws| SERVER
    UI -->|REST /api/*| SERVER
    SERVER --> AGENTS
    SERVER --> GAME
    AGENTS --> GAME
    GAME --> GENRE
    SERVER --> PROTO
    UI --> PROTO
    SERVER -->|Unix socket| DCLIENT
    DCLIENT -->|JSON-RPC| FLUX

    PACKS -.->|--genre-packs-path| GENRE
    PACKS -.->|SIDEQUEST_GENRE_PACKS| FLUX
    PACKS -.->|pre-rendered tracks| MIXER
    ORC -.->|just commands| SERVER
    ORC -.->|just commands| UI
    ORC -.->|just commands| FLUX

    classDef rust fill:#dea584,stroke:#333
    classDef ts fill:#3178c6,stroke:#333,color:#fff
    classDef py fill:#306998,stroke:#333,color:#fff
    classDef yaml fill:#cb171e,stroke:#333,color:#fff
    classDef orch fill:#6c757d,stroke:#333,color:#fff

    class SERVER,AGENTS,GAME,GENRE,PROTO,DCLIENT rust
    class UI ts
    class FLUX,KOKORO,ACE,MIXER py
    class PACKS yaml
    class ORC orch
```

## Communication Protocols

| Path | Protocol | Format |
|------|----------|--------|
| UI ↔ API | WebSocket (`/ws`) | JSON `GameMessage` enum |
| UI → API | REST (`/api/*`) | JSON (genres, save/load) |
| API → Daemon | Unix socket (`/tmp/sidequest-renderer.sock`) | Newline-delimited JSON-RPC (ADR-035) |
| API → Claude | Subprocess (`claude -p`) | Stdin prompt, stdout response |
| Content → All | Filesystem path | YAML + binary assets (Git LFS) |

## Data Flow: Game Turn

```mermaid
sequenceDiagram
    participant P as Player (UI)
    participant S as Server (axum)
    participant O as Orchestrator
    participant I as Intent Router
    participant A as Agent (Claude)
    participant G as Game State
    participant D as Daemon
    participant M as Media

    P->>S: PLAYER_ACTION (WebSocket)
    S->>O: dispatch(action)

    O->>I: classify(action)
    I->>A: claude -p (Haiku classifier)
    A-->>I: intent + confidence
    Note over I: Two-tier: Haiku first,<br/>Narrator resolves ambiguity

    O->>A: claude -p (Narrator/WorldBuilder/etc.)
    A-->>O: narration + JSON patch

    O->>G: apply_patch(delta)
    G-->>O: updated GameSnapshot

    par Media Pipeline
        O->>D: render(subject, tier)
        D->>M: Flux image gen (MLX)
        M-->>D: PNG bytes
        D-->>O: render result
    end

    O->>S: broadcast(NARRATION + patches)
    S->>P: NARRATION → NARRATION_END (atomic state commit)
    S->>P: IMAGE / AUDIO_CUE
    S->>P: PARTY_STATUS / MAP_UPDATE
```

## Data Flow: Character Creation

```mermaid
sequenceDiagram
    participant P as Player (UI)
    participant S as Server
    participant B as CharacterBuilder
    participant CS as CreatureSmith (Claude)
    participant G as Genre Pack

    P->>S: Connect (genre, world, name)
    S->>G: load genre pack
    G-->>S: pack config + creation scenes

    loop Creation Scenes
        S->>P: CHARACTER_CREATION (scene + choices)
        P->>S: choice selection or freeform text
        S->>B: advance(choice)
    end

    B->>CS: claude -p (generate character)
    CS-->>B: Character JSON
    B-->>S: Character confirmed
    S->>P: SESSION_EVENT (game begins)
```

## Data Flow: Media Pipeline

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant SE as Subject Extractor
    participant BF as Beat Filter
    participant RQ as Render Queue
    participant DC as Daemon Client
    participant FX as Flux Worker (MLX)
    participant MX as Audio Library

    O->>SE: extract(narration)
    SE-->>O: subjects + tiers

    O->>BF: should_render?(drama_weight)
    alt drama_weight > threshold
        BF-->>O: render
        O->>RQ: enqueue(subject, tier)
        RQ->>DC: render request (JSON-RPC)
        DC->>FX: generate image
        FX-->>DC: PNG bytes
        DC-->>RQ: RenderResult
    else low drama
        BF-->>O: suppress
    end

    O->>DC: audio_cue(mood, genre)
    DC->>MX: play(pre-rendered track, channel)
    Note over MX: Channels: music, SFX<br/>(TTS voice pipeline removed 2026-04)
```

## Repository Responsibilities

### orc-quest (Orchestrator)
- Cross-repo coordination via `justfile`
- Sprint tracking and story management
- Architecture docs, Architecture Decision Records, design artifacts
- Asset generation scripts (POI images, music, portraits)
- System-level documentation (this file)

### sidequest-api (Rust)
- Game engine: state, combat, chase, tropes, progression
- Agent orchestration: unified Opus narrator (ADR-067) with auxiliary agents
- WebSocket server: real-time game communication
- Session management: connect → create → play lifecycle
- SQLite persistence: save/load game state
- Pacing engine: tension model, drama-aware delivery
- Multiplayer: turn barriers, perception rewriting
- Input sanitization: protocol-layer prompt injection defense (ADR-047)

### sidequest-ui (TypeScript/React)
- Game client: narrative display, character sheets, inventory, map
- Audio engine: two-channel mixer (music + SFX), crossfader
- 3D dice overlay: Three.js + Rapier (ADR-075, proposed)
- GM Mode: real-time telemetry dashboard
- Genre theming: CSS variable injection from pack config

### sidequest-daemon (Python)
- Image generation: Flux.1 (schnell + dev) via MLX (ADR-070)
- Audio library playback: pre-rendered ACE-Step tracks, mood-indexed rotation
- Audio mixing: pygame-ce
- GPU memory coordination: LRU model eviction across budget (ADR-046)

### sidequest-content
- Genre pack YAML configs (11 packs)
- Audio assets (pre-rendered music, SFX)
- Image assets (portraits, POI landscapes, maps)
- World data (history, factions, cultures)
- Fonts and visual style assets
