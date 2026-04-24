# SideQuest Server — Tech Stack

> Package and dependency choices for the Python game engine.
> FastAPI + uvicorn, pydantic v2, pytest, OTEL.
>
> **Last updated:** 2026-04-23 (post-ADR-082 cutover)

## Runtime & Tooling

| Concern | Choice | Notes |
|---------|--------|-------|
| Python | 3.12+ | Required by pydantic v2 typing, `Annotated` discriminators |
| Build backend | `hatchling` | declared in `pyproject.toml`; no compile step |
| Environment manager | `uv` | Fast lockfile resolution; `uv run` for entry points |
| Test runner | `pytest` + `pytest-asyncio` | `asyncio_mode = "auto"` for async fixtures |
| Lint / format | `ruff` | `ruff check` and `ruff format` — one tool |
| Type checker | `pyright` | Strict on protocol + game modules |

## Core Dependencies

Declared in `sidequest-server/pyproject.toml`:

| Concern | Package | Minimum | Notes |
|---------|---------|---------|-------|
| HTTP / WS framework | `fastapi` | 0.110 | Router, dependency injection, pydantic integration |
| ASGI server | `uvicorn[standard]` | 0.29 | `uvicorn sidequest.server.app:app --reload` in dev |
| Models / validation | `pydantic` | 2.6 | Discriminated unions, protocol payload validation |
| YAML | `pyyaml` | 6.0 | Genre pack loading |
| WebSockets | `websockets` | 12.0 | Underlies FastAPI WS handler; direct usage for tests |
| Observability | `opentelemetry-api` + `opentelemetry-sdk` | 1.24 | Span catalog ported from the Rust tree verbatim |
| HTTP client (tests) | `httpx` | 0.27 | FastAPI's recommended test transport |

The standard library covers persistence (`sqlite3`), subprocess (`asyncio.create_subprocess_exec`), filesystem, regex, time, random, and UUID. No ORM, no migration framework — game state is document-shaped, not relational.

## Package Structure

```
sidequest-server/
├── pyproject.toml                     # [project], deps, entry points, ruff config
├── sidequest/
│   ├── protocol/                      # GameMessage discriminated union, 33+ message types, sanitization
│   ├── genre/                         # YAML genre pack loader, pydantic models, 6 packs
│   ├── game/                          # ~30+ modules — state, combat, NPCs, lore, audio direction
│   ├── agents/                        # Claude CLI subprocess, narrator + auxiliary agents
│   ├── server/                        # FastAPI app, session management, dispatch, watcher
│   ├── daemon_client/                 # Unix socket client for Python media daemon
│   ├── telemetry/                     # OTEL span helpers + watcher event infrastructure
│   └── cli/                           # CLI entry points (pyproject.toml [project.scripts])
└── tests/                             # pytest test suite
```

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

The composition mirrors the prior Rust crate layout 1:1 (per ADR-082) — any feature, span, or test can be compared across historical trees by path.

## Claude CLI Integration

All LLM calls use `claude -p` as a subprocess via `asyncio.create_subprocess_exec`. No Anthropic SDK. Claude Max subscription handles billing. The agent layer wraps this with timeout, stdout parsing, and error recovery.

Active agent types, each a Python class wrapping the same subprocess pattern with agent-specific system prompts:

- **Narrator** — unified prose generation (exploration, dialogue, combat, chase). Persistent Opus session per ADR-066/067.
- **WorldBuilder** — world state patches, NPC creation, faction updates
- **IntentRouter** — state-override classification (in_combat → Combat, in_chase → Chase, default → Exploration)
- **Troper** — trope beat injection and narrative pacing

Historical agents (CreatureSmith, Ensemble, Dialectician) are superseded by ADR-067's unified narrator; their routing references remain in the `AgentKind` enum but do not dispatch.

```python
proc = await asyncio.create_subprocess_exec(
    "claude", "-p", prompt,
    "--system", system_prompt,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
```

The narrator outputs prose only — no JSON blocks or structured data. Mechanical state changes are handled by sidecar tools that run alongside narration (mood, intent, items, quests, SFX, resource changes, personality events, scene renders). Tool results are validated and merged in `assemble_turn` with tool values taking precedence over extraction. NPC and encounter data is pre-generated server-side and injected into `<game_state>` as world facts (ADR-059: Monster Manual).

Player input is sanitized at the protocol layer before reaching any agent prompt (ADR-047).

## Python Sidecar (sidequest-daemon)

The ML inference stack is a separate Python service. `sidequest.daemon_client` communicates over Unix socket with newline-delimited JSON-RPC (ADR-035).

| Subsystem | Stack | Notes |
|-----------|-------|-------|
| Image generation | Flux.1 / Z-Image Turbo, MLX | Apple Silicon target (ADR-070). Z-Image Turbo is the active renderer; prompting guide at `sidequest-content/PROMPTING_Z_IMAGE.md` |
| Music library | Pre-rendered ACE-Step tracks | Build-time generation, runtime library playback |
| Audio mixing | pygame mixer | Music + SFX (no voice/TTS channel after 2026-04 removal) |
| Scene interpretation | Pattern matching | Narrative text → stage cues |
| Subject extraction | Claude CLI | Prose → visual descriptions |

See ADR-035 for the Unix socket IPC architecture and ADR-046 for GPU memory budget coordination.

## React Client (sidequest-ui)

| Concern | Choice | Notes |
|---------|--------|-------|
| Framework | React 19 | Concurrent features for streaming narration |
| Bundler | Vite | HMR for dev, optimized build |
| Language | TypeScript | Strict mode |
| Styling | Tailwind CSS + shadcn/ui | Genre theming via CSS variables (ADR-079) |
| Testing | Vitest | Unit + component tests |
| Audio | Web Audio API | Two-channel playback (music + SFX) per current ADR-045 state |
| State management | `useStateMirror` (custom) | Delta replay from server (ADR-026) |
| 3D dice | Three.js + Rapier | Overlay with genre-themed skins (ADR-075) |

## Deliberate Omissions

Not used and not planned:

- **Anthropic SDK** — `claude -p` subprocess is the integration pattern (ADR-001)
- **PostgreSQL / asyncpg** — SQLite is sufficient for single-server game saves
- **SQLAlchemy / ORM** — game state is document-shaped; raw `sqlite3` with typed row factories
- **Alembic / migrations** — saves are versioned by genre/world slug, not schema evolution
- **protobuf / msgpack** — JSON over WebSocket is the protocol; no binary serialization needed
- **gRPC** — Unix-socket JSON-RPC is the daemon contract (ADR-035)
- **Redis / external cache** — in-process caches are adequate at target scale
- **Celery / task queue** — asyncio tasks and background subprocesses cover all async work
- **mypy** — pyright chosen for speed and strict-mode ergonomics

## History

The backend was originally Python (archived as `sq-2`), briefly Rust (`sidequest-api`, ~2026-03-30 to 2026-04-19, 12-crate cargo workspace on `tokio` + `axum` + `serde` + `rusqlite`), and is now Python again per **ADR-082**. The Rust tree no longer exists on disk. Design carried forward: crate boundaries → package boundaries, serde structs → pydantic models, tracing spans → OTEL spans (verbatim catalog), `cargo test` → `pytest`. The typed-protocol discipline survives intact; the language does not.
