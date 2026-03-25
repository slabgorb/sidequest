---
parent: context-epic-1.md
---

# Story 1-6: Server — Axum Router, WebSocket, Genres Endpoint, Service Facade, Structured Logging

## Business Context

Port `server/app.py`, `server/session_handler.py`, and `server/cli.py`. The Python
server is 1,177 lines of aiohttp with the #1 finding from the debt audit: 35+ direct
accesses into orchestrator internals. The Rust version enforces the facade boundary
from the start — the server talks to a `GameService` trait, never to game state directly.

**Python sources:**
- `sq-2/sidequest/server/app.py` — GameServer (aiohttp WebSocket, 1177 lines)
- `sq-2/sidequest/server/session_handler.py` — character selection, recap delivery
- `sq-2/sidequest/server/action_queue.py` — player action queuing
- `sq-2/sidequest/server/turn_mode.py` — turn mode management
- `sq-2/sidequest/server/collect_window.py` — action collection window
- `sq-2/sidequest/server/idle_timer.py` — idle detection
- `sq-2/sidequest/server/cli.py` — server startup

## Technical Guardrails

- **Port lesson #1 (CRITICAL — server/orchestrator coupling):** The server MUST NOT access
  game state directly. It calls `GameService` trait methods. The trait is defined in
  story 1-5. Server depends on the trait, not the implementation
- **Port lesson #12 (structured logging):** Configure `tracing-subscriber` with structured
  JSON output. Every request gets a span with `component`, `operation`, `player_id`
- **ADR-003 (Session as Actor):** One tokio task per WebSocket connection. Task owns a
  `Session` struct. Communication via `tokio::sync::mpsc`
- **Message dispatch:** Incoming `GameMessage` (from story 1-2) is deserialized and
  dispatched to the `GameService`. Outgoing messages are broadcast via
  `tokio::sync::broadcast` channel
- **CORS:** `tower-http::cors` — React UI runs on different port
- **CLI:** `clap` for server startup (host, port, genre_packs_path, soul_path)

### Python → Rust Translation

| Python (aiohttp) | Rust (axum) |
|---|---|
| `GameServer` class with mutable state | `AppState` in `Arc`, routes as functions |
| `handle_ws(request)` | `async fn ws_handler(ws: WebSocketUpgrade)` |
| `self.clients: dict[str, WebSocket]` | `DashMap<PlayerId, mpsc::Sender>` |
| `broadcast_to_clients()` | `broadcast::Sender<GameMessage>` |
| `_processing` set (action gate) | Scoped guard pattern |
| `_init_orchestrator()` (lazy) | Initialized at startup, shared via `Arc` |
| Silent broadcast failures (app.py:1049) | Log every failure before evicting |

### Session lifecycle

1. Client opens WS → server spawns tokio task, assigns PlayerId
2. Client sends `SESSION_EVENT { event: "connect" }` → server loads/creates session
3. If no character → character creation flow
4. Game loop: `PLAYER_ACTION` → `GameService::handle_action()` → response messages
5. Client disconnects → task cleans up, session persisted

## Scope Boundaries

**In scope:**
- axum Router with routes: `GET /api/genres`, WebSocket upgrade
- WebSocket handler dispatching GameMessage to GameService
- Session lifecycle (connect, character selection, game loop, disconnect)
- Broadcast via tokio channels
- CORS middleware
- Structured tracing with request spans
- CLI args via clap
- Action queue and turn mode
- Idle timer and collection window
- Reconnection handling (evict stale connections)

**Out of scope:**
- Game logic (story 1-4, behind GameService facade)
- Agent orchestration (story 1-5, behind GameService facade)
- TTS/audio streaming (daemon territory)
- Static file serving (React UI serves itself)

## AC Context

| AC | Detail |
|----|--------|
| Server starts | `cargo run` binds to configured host:port |
| REST endpoint | `GET /api/genres` returns genre pack summaries |
| WebSocket works | Client connects, sends GameMessage, receives response |
| Service facade | Server calls GameService trait, never accesses game state directly |
| Session lifecycle | Connect → character select → game loop → disconnect |
| Structured logging | Requests produce tracing spans with component/operation/player_id |
| CORS | Cross-origin requests from React dev server allowed |
| Reconnection | Stale connections evicted with logged reason |
| Broadcast | Messages delivered to all connected clients via channel |
