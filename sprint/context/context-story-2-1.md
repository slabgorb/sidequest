---
parent: context-epic-2.md
---

# Story 2-1: Server Bootstrap — Axum Router, WebSocket Upgrade, /api/genres REST, CORS, Graceful Shutdown

## Business Context

Story 1-12 scaffolded the server crate with module structure and the `GameService` facade
trait. This story makes it actually run: bind a port, accept WebSocket connections, serve
genre metadata over REST, and shut down cleanly. This is the first time all five crates
compile together into a runnable binary.

The Python server (`server/app.py`) is 1178 lines because it mixes routing, game logic,
character creation, voice synthesis, and render queue management into a single class. The
Rust server separates these concerns — this story handles only the transport layer.

**Python source:** `sq-2/sidequest/server/app.py` (GameServer class, `create_app()`, `handle_ws()`)
**Python source:** `sq-2/sidequest/server/cli.py` (argument parsing, startup)
**Depends on:** Story 1-12 (server module structure, `GameService` trait)

## Technical Approach

### What Python Does

```python
class GameServer:
    def create_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/ws", self.handle_ws)
        app.router.add_get("/api/genres", self.handle_genres)
        # static routes for renders, genre assets, SPA fallback
        return app

    async def handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        player_id = str(uuid.uuid4())
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                parsed = GameMessage.from_dict(json.loads(msg.data))
                await self._dispatch(player_id, parsed, ws)
        # cleanup on disconnect
```

### What Rust Does Differently

**The `GameServer` god object becomes separated concerns:**

| Python (all in GameServer) | Rust (separated) |
|---|---|
| `self.clients: dict` | `AppState.connections: DashMap<PlayerId, mpsc::Sender>` |
| `self.orchestrator` | Injected via `AppState` as `Arc<dyn GameService>` |
| `self._processing: set` | `ProcessingGuard` — RAII drop removes from set |
| `self.broadcast()` | `tokio::sync::broadcast::Sender<GameMessage>` |
| `create_app()` returns mutable app | `Router::new()` returns immutable router |
| Lazy orchestrator init | Constructed at startup, passed as state |

**Type-system improvements:**
- Python's `_dispatch` does string matching on `msg.type.value`. Rust matches on `GameMessage` enum variants — exhaustive, compiler-checked.
- Python's `_processing` set uses manual try/finally for cleanup. Rust uses a RAII guard: when the guard drops (even on panic), the player_id is removed.
- Python's `broadcast()` silently catches send errors and marks stale clients. Rust uses `broadcast::Sender` which doesn't track individual subscribers — stale cleanup happens at the receiver end.
- Python accepts any dict as payload. Rust deserializes directly into the typed `GameMessage` enum — malformed messages fail at deserialization, not deep in handler logic.

### Module Structure

```
sidequest-server/src/
├── main.rs       — tokio::main, clap args, tracing setup, build router, serve
├── router.rs     — axum Router assembly: /ws, /api/genres, fallback
├── ws.rs         — WebSocket upgrade handler, message read loop, dispatch
├── genres.rs     — GET /api/genres → scan genre_packs dir, return metadata
├── state.rs      — AppState: shared config, connections map, broadcast channel
└── error.rs      — Server error types (connection, deserialization, service)
```

### CLI (clap derive)

```rust
#[derive(Parser)]
struct Args {
    #[arg(long, default_value = "8765")]
    port: u16,
    #[arg(long)]
    genre_packs_path: PathBuf,
    #[arg(long)]
    save_dir: Option<PathBuf>,  // default: ~/.sidequest/saves
}
```

Python's `--genre`, `--world`, `--scenario` args are removed — the client selects these
at connect time via SESSION_EVENT. The server doesn't need to know genre upfront.

### WebSocket Handler

```rust
async fn ws_handler(
    ws: WebSocketUpgrade,
    State(app): State<Arc<AppState>>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_connection(socket, app))
}

async fn handle_connection(stream: WebSocket, app: Arc<AppState>) {
    let player_id = PlayerId::new();  // UUID newtype
    let (sink, mut stream) = stream.split();
    // spawn sender task reading from mpsc channel → sink
    // main loop: read from stream, deserialize GameMessage, dispatch
}
```

**Key difference from Python:** Python's `handle_ws` is one big async loop that does
everything inline. Rust splits into a reader task (deserialize + dispatch) and a writer
task (receive from mpsc channel + send to WebSocket). This prevents head-of-line blocking
where a slow send delays reading the next message.

### /api/genres Endpoint

```rust
async fn list_genres(
    State(app): State<Arc<AppState>>,
) -> Json<HashMap<String, GenreInfo>> {
    // scan genre_packs_path for directories containing pack.yaml
    // for each, load pack.yaml to get name, scan worlds/ subdirectory
    // return { "genre_slug": { "worlds": ["world1", "world2"] } }
}
```

Python loads full GenrePack objects for this endpoint. Rust should only read `pack.yaml`
metadata and scan `worlds/` directory names — no need to load the entire pack.

### CORS

```rust
let cors = CorsLayer::new()
    .allow_origin("http://localhost:5173".parse::<HeaderValue>().unwrap())
    .allow_methods([Method::GET])
    .allow_headers(Any);
```

Dev-only: allow the React dev server at localhost:5173. Production will use same-origin.

### Graceful Shutdown

```rust
let shutdown = tokio::signal::ctrl_c();
axum::serve(listener, app)
    .with_graceful_shutdown(async { shutdown.await.ok(); })
    .await?;
```

On SIGTERM/SIGINT: stop accepting new connections, let in-flight requests complete,
then exit. Python's aiohttp does this automatically; axum needs explicit wiring.

## Scope Boundaries

**In scope:**
- axum Router with `/ws` (WebSocket upgrade) and `/api/genres` (REST)
- WebSocket read/write split with mpsc channel per connection
- `AppState` struct with genre_packs_path, connections map, broadcast channel
- `ProcessingGuard` RAII pattern for action gating
- CORS middleware for dev
- CLI args via clap
- Graceful shutdown on SIGTERM
- Structured tracing spans on every connection (player_id, component)

**Out of scope:**
- Session state machine (story 2-2)
- Character creation (story 2-3)
- Game logic dispatch (story 2-5)
- SQLite persistence (story 2-4)
- TTS/audio binary frames (deferred)
- Static file serving for SPA (nice-to-have, not core loop)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Server starts | `cargo run` binds to configured port, logs startup message with tracing |
| REST endpoint | `GET /api/genres` returns `{ "genre_slug": { "worlds": [...] } }` |
| WebSocket connects | Client opens `/ws`, server assigns PlayerId, logs connection |
| Message deserialization | Valid GameMessage JSON deserializes to typed enum variant |
| Invalid message rejected | Malformed JSON returns ERROR message, doesn't crash connection |
| Processing guard | Two PLAYER_ACTIONs from same player — second gets ERROR while first runs |
| CORS | React dev server at localhost:5173 can reach /api/genres and /ws |
| Graceful shutdown | SIGTERM closes connections, logs shutdown, exits cleanly |
| Broadcast channel | Messages sent on broadcast reach all connected WebSocket clients |

## Assumptions

- axum 0.8 WebSocket support handles ping/pong and close frames automatically
- Single-player first — broadcast is still wired because the UI expects it, but only one client connects
- The `GameService` trait from 1-11/1-12 may need extension as we discover what handlers need — that's expected and fine
