# SideQuest API — Architecture

> System design for the Rust port. Derived from the Python codebase (sq-2)
> and the UI contract. This is a learning project — the goal is deep Rust
> fluency, not feature parity on day one.

## Architectural Layers

```
┌─────────────────────────────────────────────────┐
│                  React Client                    │
│            (sidequest-ui, unchanged)             │
└────────┬──────────────────────────────┬──────────┘
         │ WebSocket /ws                │ REST /api/*
         ▼                              ▼
┌─────────────────────────────────────────────────┐
│                 Transport Layer                   │
│         axum Router + WebSocket upgrade           │
│         (api/mod.rs, api/ws.rs, api/genres.rs)   │
└────────┬──────────────────────────────────────────┘
         │ GameMessage (protocol/)
         ▼
┌─────────────────────────────────────────────────┐
│                 Session Layer                     │
│         Per-connection state machine              │
│         Connect → Create → Play                   │
│         (game/session.rs)                         │
└────────┬──────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│               Orchestrator Layer                  │
│         Routes player actions to agents           │
│         Manages game state + deltas               │
│         (game/orchestrator.rs, game/state.rs)     │
└────────┬──────────────────────────────────────────┘
         │ tokio::process::Command
         ▼
┌─────────────────────────────────────────────────┐
│                 Agent Layer                        │
│         Claude CLI subprocess calls               │
│         Narrator, Combat, NPC, Creator            │
│         (agents/)                                  │
└───────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              Persistence Layer                     │
│         rusqlite for saves, serde_yaml for        │
│         genre packs, filesystem for narrative log  │
│         (game/persistence.rs, genre/)              │
└───────────────────────────────────────────────────┘
```

## Key Design Decisions

### ADR-001: Workspace with Domain Crates

**Context:** Axiathon uses a workspace with 8 crates. SideQuest has 14+ game
system ADRs, an agent layer, a protocol layer, genre loading, and persistence.
A single crate would grow unwieldy quickly.

**Decision:** Cargo workspace with domain-separated crates:

```
sidequest-api/
├── Cargo.toml                 # [workspace] root
├── crates/
│   ├── sidequest-protocol/    # GameMessage enum, typed payloads, serde
│   ├── sidequest-game/        # State, characters, progression, combat, chase, tropes
│   ├── sidequest-genre/       # YAML loader, genre pack structs
│   ├── sidequest-agents/      # Claude CLI subprocess wrapper, agent types
│   └── sidequest-server/      # axum HTTP/WebSocket, session management
└── tests/                     # Integration tests
```

**Rationale:** The game systems alone (characters, combat, chases, tropes,
progression, cartography, NPCs) are complex enough to warrant a dedicated crate.
Protocol types are shared between server and tests. Genre loading is independent
of game logic. This mirrors axiathon's workspace pattern for shared learning.

**Dependency graph:**
```
sidequest-server
  ├── sidequest-agents
  │     └── sidequest-protocol
  ├── sidequest-game
  │     ├── sidequest-protocol
  │     └── sidequest-genre
  └── sidequest-protocol
```

### ADR-002: Typed Protocol over Untyped Payloads

**Context:** Python uses `dict[str, Any]` payloads with string-typed message
enums. The UI's TypeScript also uses `Record<string, unknown>`.

**Decision:** Define strongly-typed Rust structs for each message payload, using
serde's `#[serde(tag = "type")]` for the outer `GameMessage` enum. Keep a
`serde_json::Value` escape hatch for truly dynamic payloads.

**Rationale:** This is where Rust gives us the most learning value. The type
system catches payload mismatches at compile time. The Python codebase has
runtime `KeyError` bugs that typed payloads eliminate.

```rust
#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum GameMessage {
    #[serde(rename = "PLAYER_ACTION")]
    PlayerAction { payload: PlayerActionPayload, player_id: String },

    #[serde(rename = "NARRATION")]
    Narration { payload: NarrationPayload, player_id: String },

    // ... etc
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PlayerActionPayload {
    pub action: String,
    #[serde(default)]
    pub aside: bool,
}
```

### ADR-003: Session as Actor (tokio task per connection)

**Context:** Python uses a `GameServer` class with a `clients` dict and
per-player state scattered across the server object.

**Decision:** Each WebSocket connection spawns a dedicated tokio task that owns
a `Session` struct. Communication between sessions (for multiplayer) uses
`tokio::sync::mpsc` channels.

**Rationale:** This maps naturally to Rust ownership — one task owns one
session's mutable state, no `Arc<Mutex<>>` needed for the common case.
Multiplayer message passing uses channels rather than shared mutable state.

```
WebSocket connection
    └─► tokio::spawn(session_task)
            ├── owns: Session { state, genre_pack, orchestrator }
            ├── reads from: ws_receiver (client messages)
            ├── writes to: ws_sender (server messages)
            └── orchestrator calls: claude -p subprocesses
```

### ADR-004: Genre Packs Stay as YAML

**Context:** Genre packs are YAML files with world definitions, NPC templates,
item catalogs, etc. Shared between Python and Rust via the orchestrator's
`genre_packs/` directory.

**Decision:** Load with `serde_yaml`, deserialize into typed Rust structs.
Genre packs are read-only at runtime — loaded once per session.

**Rationale:** YAML is the format, serde_yaml handles it, and typed structs
give us compile-time validation of genre data shapes. The genre packs are
shared with sq-2, so the format can't change unilaterally.

### ADR-005: Claude CLI Subprocess (not SDK)

**Context:** sq-2 uses `claude -p` subprocesses. No API key needed — Claude
Max subscription handles billing.

**Decision:** Port the same pattern using `tokio::process::Command`. Wrap in
an `Agent` struct that handles timeout, stdout parsing, and error recovery.

**Rationale:** This is the existing working pattern. The Claude CLI handles
auth, rate limiting, and tool use. Switching to the API SDK would be a
different project. The learning goal is Rust async subprocess management, not
API client design.

```rust
pub struct Agent {
    pub name: String,
    pub system_prompt: String,
    pub timeout: Duration,
}

impl Agent {
    pub async fn prompt(&self, input: &str) -> Result<String, AgentError> {
        let output = Command::new("claude")
            .args(["-p", input, "--system", &self.system_prompt])
            .output()
            .await?;
        // ... parse, validate, return
    }
}
```

### ADR-006: Persistence — SQLite via rusqlite

**Context:** Python uses JSON files on disk (state.json, narrative_log.jsonl).
This works but has atomicity issues and no query capability.

**Decision:** Use rusqlite for structured persistence (game state, character
data, saves). Keep narrative log as append-only for simplicity.

**Rationale:** SQLite gives us atomic saves, queryable history, and a single
file per save. rusqlite is synchronous but can be wrapped in
`tokio::task::spawn_blocking` for the async boundary. This is a deliberate
improvement over the Python file-based approach.

## Implementation Priority

Build bottom-up, each layer testable independently:

| Phase | Layer | Deliverable |
|-------|-------|-------------|
| 1 | **Protocol** | `GameMessage` enum with serde, unit tests for round-trip |
| 2 | **Genre** | YAML loader, typed genre pack structs |
| 3 | **Transport** | axum server, WebSocket upgrade, `/api/genres` endpoint |
| 4 | **Session** | Connect → Create → Play state machine |
| 5 | **Agent** | Claude CLI subprocess wrapper with timeout |
| 6 | **Orchestrator** | Route actions to agents, manage state deltas |
| 7 | **Persistence** | rusqlite save/load |
| 8 | **Integration** | Wire UI to Rust backend end-to-end |

Phase 1-3 gets the server compiling and serving the UI. Phase 4-5 gets a
minimal game loop running. Phase 6-8 approaches feature parity with sq-2.

## What Stays in Python (sidequest-daemon)

The media pipeline stays in Python as a dedicated repo (`sidequest-daemon`),
extracted from sq-2. This is a separate service, not a library dependency.

### sidequest-daemon responsibilities
- **Image generation:** Flux (schnell + dev), scene cache, stale render policy
- **TTS voice synthesis:** Kokoro (primary) + Piper (fallback), voice routing
- **Audio:** Pre-generated library playback, theme rotation, mood selection
- **Scene interpretation:** Narrative text → stage cues via pattern matching
- **Subject extraction:** Prose → visual descriptions via Claude CLI

### Communication boundary
```
sidequest-api (Rust)  ◄──── Unix socket / HTTP ────►  sidequest-daemon (Python)
     │                                                        │
     ├── Sends: narrative text, scene context                 ├── Returns: image URLs, audio paths
     ├── Sends: voice synthesis requests                      ├── Returns: binary PCM frames
     └── Shares: genre_packs/ (read-only assets)              └── Reads: genre_packs/ visual/audio config
```

The binary WebSocket frame protocol (voice audio to client) is relayed
through the Rust API — daemon produces PCM, API forwards to client.

### ADRs governing the daemon
See `docs/adr/README.md` → "Media Pipeline (stays in sidequest-daemon)" for
the 12 ADRs that define daemon architecture. These remain authoritative for
the Python service.

## Multiplayer Architecture

Python sq-2 supports multiplayer via a single `GameServer` with multiple
WebSocket clients sharing one `Orchestrator`. The Rust port preserves this:

```
Client A ──ws──► Session A ─┐
                             ├──► Shared Orchestrator (Arc<Mutex<>>)
Client B ──ws──► Session B ─┘        │
                                     ├── Game State
                                     ├── Agent calls
                                     └── State deltas broadcast to all sessions
```

For multiplayer, the `Orchestrator` is shared behind `Arc<Mutex<Orchestrator>>`
(or better, `Arc<RwLock<>>` since reads dominate). Individual sessions send
actions through a channel; the orchestrator processes them and broadcasts
deltas back. This is the one place where shared state is justified.

Single-player is the degenerate case: one session, one orchestrator, no
contention.
