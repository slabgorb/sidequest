# SideQuest API — Tech Stack

> Crate and dependency choices for the Rust game engine.
> 6-crate workspace, edition 2021, stable toolchain.
>
> **Last updated:** 2026-04-04

## Workspace Dependencies

Centralized in `Cargo.toml` `[workspace.dependencies]`:

| Concern | Crate | Version | Notes |
|---------|-------|---------|-------|
| Async runtime | `tokio` | 1.38 (full) | Task spawning, process management, channels, timers |
| HTTP framework | `axum` | 0.7 (macros, ws) | Router, extractors, middleware, WebSocket upgrade |
| Middleware | `tower` | 0.4 (util) | Service composition |
| HTTP middleware | `tower-http` | 0.5 (cors, fs, trace) | CORS, static files, request tracing |
| Serialization | `serde` | 1.0 (derive) | Derive macros on all protocol and game types |
| JSON | `serde_json` | 1.0 | WebSocket message encoding, state deltas |
| YAML | `serde_yaml` | 0.9 | Genre pack loading |
| Error handling | `thiserror` | 1.0 | `#[error]` derive on domain error types |
| Tracing | `tracing` | 0.1 | `#[instrument]` spans, structured logging |
| Tracing subscriber | `tracing-subscriber` | 0.3 (env-filter, json) | JSON output for GM watcher telemetry |
| CLI args | `clap` | 4.5 (derive) | Server startup flags (port, genre-packs-path) |
| UUIDs | `uuid` | 1.0 (v4, serde) | Player IDs, session IDs, render IDs |
| Time | `chrono` | 0.4 (serde) | Timestamps on game events, turn records |
| Random | `rand` | 0.9 | OCEAN profile generation, combat dice, NPC behavior |
| SQLite | `rusqlite` | 0.31 (bundled, chrono, uuid) | Game save/load, session persistence |
| Futures | `futures` | 0.3 | Stream combinators for WebSocket message routing |
| Regex | `regex` | 1.10 | Input sanitization, prompt injection defense (ADR-047) |
| Ordered floats | `ordered-float` | 4 (serde) | Hashable floats for OCEAN profiles, drama weights |

### Crate-Specific Dependencies

| Crate | Additional Deps | Purpose |
|-------|----------------|---------|
| sidequest-game | `base64` 0.22 | TTS audio chunk encoding |
| sidequest-server | `dirs` 5 | User directory resolution for config |
| sidequest-server | `tokio-tungstenite` 0.24 (dev) | WebSocket integration tests |
| sidequest-game | `tempfile` 3 (dev) | SQLite test fixtures |

## Workspace Structure

```
sidequest-api/
├── Cargo.toml                        # [workspace] root, centralized deps
├── crates/
│   ├── sidequest-protocol/           # GameMessage enum, 23 message types, sanitization
│   ├── sidequest-genre/              # YAML genre pack loader, typed structs
│   ├── sidequest-game/               # 52 game modules — state, combat, NPCs, lore, audio
│   ├── sidequest-agents/             # Claude CLI subprocess, 7 agent types, JSON extraction
│   ├── sidequest-server/             # axum server, session management, orchestrator
│   └── sidequest-daemon-client/      # Unix socket client for Python media daemon
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

## Tooling

| Tool | Config | Notes |
|------|--------|-------|
| `rustfmt` | edition 2021, `max_width = 100` | `.rustfmt.toml` in workspace root |
| `clippy` | `-D warnings` | All warnings are errors |
| `rust-toolchain.toml` | stable channel | No nightly features required |
| Edition | **2021** | rust-version 1.80 minimum |

## Claude CLI Integration

All LLM calls use `claude -p` as a subprocess via `tokio::process::Command`. No Anthropic SDK. Claude Max subscription handles billing.

7 agent types, each wrapping the same subprocess pattern with agent-specific system prompts, timeout, and JSON extraction:

- **Narrator** — prose generation with state deltas and footnotes
- **WorldBuilder** — world state patches, NPC creation, faction updates
- **CreatureSmith** — NPC/monster generation from genre archetypes
- **Ensemble** — multi-NPC dialogue composition
- **Dialectician** — genre-voiced text transformation
- **IntentRouter** — two-tier action classification (Haiku + Narrator)
- **Troper** — trope beat injection and narrative pacing

```rust
let output = Command::new("claude")
    .arg("-p")
    .arg(&prompt)
    .arg("--system")
    .arg(&system_prompt)
    .output()
    .await?;
```

The narrator outputs prose only — no JSON blocks or structured data. Mechanical state
changes are handled by sidecar tools that run alongside narration (mood, intent, items,
quests, SFX, resource changes, personality events, scene renders). Tool results are
validated and merged in `assemble_turn` with tool values taking precedence over
extraction. NPC and encounter data is pre-generated server-side and injected into
`<game_state>` as world facts (ADR-059: Monster Manual). Claude treats game_state
as ground truth and uses pre-generated names, abilities, and dialogue quirks naturally.

Player input is sanitized at the protocol layer before reaching any agent prompt (ADR-047).

## Python Sidecar (sidequest-daemon)

The ML inference stack stays in Python. The Rust server communicates via `sidequest-daemon-client` over Unix socket.

| Subsystem | Python Stack | Notes |
|-----------|-------------|-------|
| Image generation | Flux.1 (schnell + dev), diffusers | 6 render tiers, GPU-accelerated |
| TTS synthesis | Kokoro (54 voices) | Streaming, per-character voice routing |
| Music generation | ACE-Step | Build-time generation, runtime library playback |
| Audio mixing | pygame mixer | 3-channel (music/SFX/ambience), speech ducking |
| Scene interpretation | Pattern matching | Narrative text → stage cues |
| Subject extraction | Claude CLI | Prose → visual descriptions |

See ADR-035 for the Unix socket IPC architecture and ADR-046 for GPU memory budget coordination.

## React Client (sidequest-ui)

| Concern | Choice | Notes |
|---------|--------|-------|
| Framework | React 19 | Concurrent features for streaming narration |
| Bundler | Vite | HMR for dev, optimized build |
| Language | TypeScript | Strict mode |
| Styling | Tailwind CSS + shadcn/ui | Genre theming via CSS variables |
| Testing | Vitest | Unit + component tests |
| Audio | Web Audio API | 3-channel playback, voice ducking (ADR-045) |
| Voice chat | WebRTC (PeerMesh) | Disabled — echo feedback loop (ADR-054) |
| State management | useStateMirror (custom) | Delta replay from server (ADR-026) |

## Deliberate Omissions

Not used and not planned:

- **Anthropic SDK** — `claude -p` subprocess is the integration pattern (ADR-001)
- **PostgreSQL / sqlx** — SQLite is sufficient for single-server game saves
- **protobuf** — JSON over WebSocket is the protocol; no binary serialization needed
- **ORM** — rusqlite with manual queries; game state is document-shaped, not relational
- **proptest / insta** — standard `#[test]` with assertions; snapshot testing adds complexity without value for game logic
- **nightly features** — stable channel only
