# ADR-062: Server lib.rs Extraction — Route Groups, State, and Watcher Events

**Status:** Accepted (realized during ADR-082 Python port, 2026-04)
**Date:** 2026-04-04
**Deciders:** Keith
**Relates to:** ADR-058 (Claude Subprocess OTEL Passthrough)

> **Status amendment (2026-04-23):** Executed during the Python port (ADR-082).
> There is no `lib.rs` equivalent in Python; the six concerns live as separate
> modules under `sidequest-server/sidequest/server/` (app.py, websocket.py,
> watcher.py, rest.py, session_handler.py, session_room.py). See the Post-port
> mapping section at the end.

## Context

`sidequest-server/src/lib.rs` has grown to 1,924 lines with 49 public functions,
10 impl blocks, and at least six distinct concerns in a single file:

1. **Watcher/OTEL types** (~180 lines) — `WatcherEvent`, `WatcherEventType`, `Severity`,
   `WatcherEventBuilder` with builder pattern
2. **CLI args** (~70 lines) — `Args` struct with clap derives and validation
3. **App state** (~400 lines) — `AppState`, `AppStateInner`, `PlayerId`, `ServerError`,
   `ProcessingGuard` with session management, genre loading, TTS integration
4. **Router construction** (~100 lines) — `build_router()` with route table
5. **HTTP/WS handlers** (~800 lines) — `list_genres()`, `ws_handler()`,
   `handle_ws_connection()`, `dispatch_message()` with full WebSocket lifecycle
6. **Server bootstrap** (~50 lines) — `create_server()`, `serve_with_listener()`
7. **Test utilities** (~50 lines) — `test_app_state()`

This is the classic "lib.rs as junk drawer" pattern. The WebSocket handler alone
(`handle_ws_connection` through `dispatch_message`) is ~500 lines of connection
lifecycle management interleaved with message routing.

## Decision

**Extract concerns into focused submodules within `sidequest-server/src/`.**

### Module Structure

```
sidequest-server/src/
├── lib.rs              # Re-exports, create_server(), serve_with_listener()
├── args.rs             # Args (clap CLI definition)
├── state.rs            # AppState, AppStateInner, PlayerId, ServerError,
│                       #   ProcessingGuard — session and genre pack management
├── watcher.rs          # WatcherEvent, WatcherEventType, Severity,
│                       #   WatcherEventBuilder — OTEL event construction
├── routes.rs           # build_router(), list_genres(), REST handlers
├── websocket.rs        # ws_handler(), handle_ws_connection(), dispatch_message()
│                       #   — full WS lifecycle
├── helpers.rs          # error_response(), reconnect_required_response()
├── dispatch/           # (already exists) — narration dispatch pipeline
│   ├── mod.rs
│   └── connect.rs
├── render_integration.rs  # (already exists)
├── shared_session.rs      # (already exists)
└── tracing_setup.rs       # (already exists)
```

### Key Design Choices

**`websocket.rs` gets `dispatch_message()`:** The dispatch function is the bridge
between the WS connection handler and the `dispatch/` pipeline. It belongs with
the connection lifecycle, not in a generic `lib.rs`. The `dispatch/` directory
handles narration-specific dispatch; `dispatch_message()` is the top-level router
that decides *which* dispatch pipeline to invoke.

**`state.rs` gets `AppState` impl blocks:** The ~400 lines of `impl AppState`
(session creation, genre loading, TTS wiring) are state management, not routing.
They belong with the type definition.

**`lib.rs` stays thin:** Only `create_server()`, `serve_with_listener()`, module
declarations, and re-exports. Under 100 lines.

## Alternatives Considered

### Extract only the largest concern (WS handlers)
Would help but leaves `lib.rs` at ~1,100 lines with 5 remaining concerns. Half
measures invite the same problem in 3 months. Rejected.

### Merge dispatch_message into dispatch/mod.rs
Logical but `dispatch/mod.rs` is already 2,132 lines (see ADR-063). Adding more
would worsen that problem. Rejected.

## Consequences

- **Positive:** `lib.rs` drops from 1,924 to ~100 lines. Each new concern has a
  clear file home.
- **Positive:** `watcher.rs` extraction makes the OTEL event API discoverable —
  important given the OTEL observability mandate in CLAUDE.md.
- **Negative:** More `use` imports in each submodule. Acceptable trade-off.
- **Negative:** `websocket.rs` will be ~800 lines. Still large, but it's a single
  cohesive concern (WS lifecycle) rather than six unrelated ones.

## Post-port mapping (ADR-082)

The `lib.rs` extraction decision was realized directly in the Python port.
`sidequest-server/src/lib.rs` has no Python counterpart by name; the six concerns
live as separate modules in `sidequest-server/sidequest/server/`:

- **Watcher / OTEL types** → `watcher.py`
- **App state / session mgmt** → `session_handler.py`, `session_room.py`
- **Router construction / HTTP handlers** → `app.py`, `rest.py`
- **WebSocket lifecycle** → `websocket.py`
- **Dispatch pipeline** → `dispatch/` package (see ADR-063)

CLI args live in `app.py`'s entry point (`main()`) rather than a dedicated struct;
uvicorn + FastAPI handles server bootstrap. The "lib.rs as junk drawer" failure
mode cannot recur — there is no lib.rs.
