# SideQuest API — Tech Stack

> Aligned with [axiathon](https://github.com/1898andCo/axiathon) for shared learning.
> Axiathon is an enterprise security product — overlap is in the foundational Rust
> crates and patterns, not domain-specific libraries (Arrow, DataFusion, protobuf, etc.).

## Shared Foundation (from Axiathon)

| Concern | Crate | Version | Notes |
|---------|-------|---------|-------|
| Async runtime | `tokio` | 1 (full) | Same async model, same executor |
| HTTP framework | `axum` | 0.8 (macros) | Same router, extractors, middleware patterns |
| Serialization | `serde` | 1 (derive) | Same derive macros, same mental model |
| JSON | `serde_json` | 1 | |
| Error handling | `thiserror` | 2 | Same `#[error]` derive pattern |
| Tracing | `tracing` | 0.1 | Structured logging, same subscriber setup |
| Tracing subscriber | `tracing-subscriber` | 0.3 (env-filter, json) | Same filtering, same JSON output |
| CLI args | `clap` | 4 (derive) | Same derive-based CLI parsing |
| UUIDs | `uuid` | 1 (v4, serde) | Player/session IDs |
| Time | `chrono` | 0.4 (serde) | Timestamps on game events |
| Edition | **2024** | rust-version 1.85 | Same edition, same language features |

## SideQuest-Specific Additions

| Concern | Crate | Version | Why |
|---------|-------|---------|-----|
| WebSocket | `axum` (built-in) | 0.8 | `axum::extract::ws` — no extra crate needed |
| YAML loading | `serde_yaml` | 0.9 | Genre pack files are YAML |
| SQLite | `rusqlite` | 0.32 (bundled) | Game save/load — lightweight, no server needed |
| Futures | `futures` | 0.3 | Stream combinators for WebSocket message routing |
| Tower HTTP | `tower-http` | 0.6 (cors, fs) | Static file serving, CORS for dev |

## Not Needed (Axiathon-only)

These are axiathon domain crates with no SideQuest equivalent:

- `arrow` / `parquet` / `datafusion` — columnar analytics
- `chumsky` / `miette` — query language parser
- `prost` / `prost-build` — protobuf (OCSF schemas)
- `sqlx` / PostgreSQL — enterprise DB (we use SQLite)
- `proptest` / `insta` — adopt later if useful, not day-one

## Project Structure

Axiathon uses a workspace with 8 crates. SideQuest uses a similar workspace
pattern with 5 domain crates:

```
sidequest-api/
├── Cargo.toml                    # [workspace] root
├── crates/
│   ├── sidequest-protocol/       # GameMessage enum, typed payloads (serde)
│   │   └── src/lib.rs
│   ├── sidequest-genre/          # YAML genre pack loader
│   │   └── src/lib.rs
│   ├── sidequest-game/           # Game state, characters, combat, chase, tropes
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── state.rs          # GameState + state deltas
│   │       ├── character.rs      # Character model + builder
│   │       ├── combat.rs         # Combat state
│   │       ├── chase.rs          # Chase engine
│   │       ├── tropes.rs         # Trope engine
│   │       ├── npc.rs            # NPC registry + disposition
│   │       ├── progression.rs    # Milestones, affinities, item evolution
│   │       ├── cartography.rs    # World topology + discovery
│   │       └── persistence.rs    # rusqlite save/load
│   ├── sidequest-agents/         # Claude CLI subprocess orchestration
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── claude.rs         # Subprocess wrapper + session mgmt
│   │       ├── router.rs         # Intent-based agent routing
│   │       └── json_extract.rs   # Lazy JSON extraction fallback
│   └── sidequest-server/         # axum HTTP/WebSocket server
│       └── src/
│           ├── main.rs           # tokio::main, CLI args, server startup
│           ├── router.rs         # axum Router assembly
│           ├── ws.rs             # WebSocket upgrade + message dispatch
│           ├── session.rs        # Per-connection state machine
│           └── genres.rs         # GET /api/genres
└── tests/                        # Integration tests
```

## Tooling Alignment

| Tool | Config | Matches Axiathon |
|------|--------|------------------|
| `rustfmt` | edition 2024, `group_imports = "StdExternalCrate"`, `trailing_comma = "Vertical"` | Yes |
| `clippy` | `-D warnings`, `unsafe_code = forbid` | Yes |
| `rust-toolchain.toml` | stable channel | Yes |

## Claude CLI Integration

LLM calls use `claude -p` as a subprocess (not an SDK). This is the same
pattern as sq-2's Python implementation but via `tokio::process::Command`:

```rust
let output = Command::new("claude")
    .arg("-p")
    .arg(&prompt)
    .output()
    .await?;
```

The media daemon (image gen, TTS, audio) stays in Python (sq-2) as a sidecar.
