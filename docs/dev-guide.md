# SideQuest Development Guide

Debugging, logging, tracing, and local development reference for agents working across the SideQuest repos.

---

## Quick Reference

| What | Command | Notes |
|------|---------|-------|
| Run API server | `just server` or `just api-run` | Alias adds `--trace` |
| Run API with tracing | `just api-run --trace` | Chrome trace → `trace-{pid}.json` |
| Run API headless | `just playtest-server` | No daemon, no rendering |
| Run UI dev server | `just ui-dev` | Vite on `localhost:5173` |
| Run daemon | `just daemon-run` | Renderer warmup |
| Run watcher (CLI) | `just watch` | Rich terminal telemetry stream |
| Run OTEL dashboard | `python3 scripts/playtest.py --dashboard-only` | Web UI on `localhost:9765` |
| Run headless playtest | `just playtest` | Interactive Python driver + OTEL dashboard |
| Run scripted playtest | `just playtest-scenario {name}` | YAML-driven scenario |
| Run all tests | `just check-all` | API lint+test, UI lint+test |

---

## Tracing & Telemetry

### Three-Layer Model (ADR-031)

SideQuest uses structured telemetry with three layers:

1. **Transport Telemetry** — tower-http middleware traces HTTP/WebSocket requests automatically
2. **Agent Telemetry** — `#[instrument]` spans on every decision point (intent routing, LLM invocation, state patches, trope engine ticks, context composition)
3. **Narrative Telemetry** — async post-turn validation checks comparing agent output against game state (runs on cold path, never blocks gameplay)

### RUST_LOG

The API server initializes tracing in `sidequest-server/src/tracing_setup.rs`. Default filter:

```
RUST_LOG="sidequest=debug,tower_http=info"
```

Override via environment variable:

```bash
RUST_LOG="sidequest_server=trace,sidequest_game=debug" just api-run
```

### Tracing Subscriber Stack

The server composes multiple layers on a `tracing_subscriber::Registry`:

| Layer | When | Output |
|-------|------|--------|
| **EnvFilter** | Always | Respects `RUST_LOG` |
| **JSON layer** | Always | Structured JSON to stdout |
| **Pretty layer** | Debug builds only | Human-readable colored output |
| **Chrome trace** | `--trace` flag | `trace-{pid}.json` for Perfetto/chrome://tracing |

### Chrome Trace (Flame Charts)

```bash
just api-run --trace
# Play the game, then stop the server
# Open trace file in browser:
open trace-*.json  # or load in chrome://tracing or https://ui.perfetto.dev
```

The trace file shows flame charts of every `#[instrument]`-annotated span — agent invocations, JSON extraction tiers, state patches, context composition. This is the primary tool for answering "where did the time go?"

---

## OTEL Dashboard (Web)

The Python playtest driver includes a built-in OTEL dashboard — a browser-based telemetry viewer that connects to the API's `/ws/watcher` endpoint.

### Dashboard-only mode

Connect to an already-running API server:

```bash
python3 scripts/playtest.py --dashboard-only
```

- **HTTP dashboard:** `http://localhost:9765/`
- **WebSocket feed:** `ws://localhost:9766/`

Custom ports:

```bash
python3 scripts/playtest.py --dashboard-only --port 8080 --dashboard-port 9000
```

### Dashboard with playtest

The dashboard runs automatically alongside any playtest mode:

```bash
just playtest                                    # interactive + dashboard
just playtest-scenario smoke_test                # scripted + dashboard
python3 scripts/playtest.py --players 2          # multiplayer + dashboard
python3 scripts/playtest.py --no-watch           # disable dashboard
```

### What the dashboard shows

The dashboard receives the same `WatcherEvent` stream as `just watch`, rendered as a tabbed web UI:

- **Timeline** — turn-by-turn flame chart (agent spans, durations)
- **State** — current game state inspector
- **Subsystems** — trope engine, combat, chase, render pipeline activity
- **Timing** — p95 agent duration, LLM call latency

Late-joining browsers receive up to 200 events of history.

---

## CLI Watcher (Terminal)

For terminal-based telemetry without a browser:

```bash
just watch              # default port 8765
just watch 9000         # custom port
```

This runs `scripts/watch.py` — a Rich-formatted stream of agent decisions, validation results, and subsystem activity per turn. Color-coded by severity (info/pass/warn/error).

---

## Headless Playtest

Test game logic without UI, daemon, or media rendering. The API runs with `--headless` which stubs out the render pipeline.

### Start headless server

```bash
just playtest-server
```

This compiles and runs the server with `--headless` flag. Render hooks fire and emit tracing spans (`render_pipeline_headless_skip`) but produce no images.

### Python driver modes

```bash
# Interactive — you type actions
python3 scripts/playtest.py

# Scripted — YAML scenario drives gameplay
python3 scripts/playtest.py --scenario scenarios/smoke_test.yaml

# Multiplayer — N concurrent simulated players
python3 scripts/playtest.py --players 4

# Custom genre/world
python3 scripts/playtest.py --genre victoria --world blackthorn_manor
```

### Full-stack playtest (with UI)

Use the `/sq-playtest` skill which coordinates:
- API server + UI dev server + daemon in tmux panes
- Playwright browser for visual interaction
- UX Designer agent evaluating screenshots
- Cross-workspace bug coordination via ping-pong file

Headless variant: `/sq-playtest headless`

---

## Key Tracing Spans

These are the `#[instrument]` spans you'll see in logs and traces:

| Span | Crate | What It Captures |
|------|-------|-----------------|
| `intent_router.classify` | sidequest-game | Player input → classified intent → routed agent |
| `agent.invoke` | sidequest-agents | Token counts, duration, raw response length |
| `json_extractor.extract` | sidequest-agents | Extraction tier (1/2/3), target type, success (ADR-039) |
| `state.apply_patch` | sidequest-game | Patch type (world/combat/chase), fields changed |
| `trope_engine.tick` | sidequest-game | Tropes advanced, beats fired, thresholds crossed |
| `context_builder.compose` | sidequest-agents | Section count, total tokens, zone distribution |
| `state.compute_delta` | sidequest-game | Fields changed from client perspective |
| `render_pipeline_headless_skip` | sidequest-server | Render hook fired in headless mode (tier, prompt) |
| `orchestrator.process_action` | sidequest-server | Full narration pipeline for a player action |

---

## Server Endpoints

| Endpoint | Type | Purpose |
|----------|------|---------|
| `GET /ws` | WebSocket | Game client connection |
| `GET /ws/watcher` | WebSocket | Read-only telemetry stream (watcher/dashboard) |
| `GET /api/genres` | REST | Genre pack metadata |

The watcher endpoint streams `WatcherEvent` JSON objects: `AgentSpanOpen`, `AgentSpanClose`, `StateTransition`, `ValidationWarning`, `SubsystemExerciseSummary`, `CoverageGap`.

---

## Test Commands

```bash
just api-test           # cargo test (all crates)
just api-check          # fmt + clippy + test
just ui-test            # vitest run
just ui-lint            # eslint
just daemon-test        # pytest
just check-all          # api-check + ui-lint + ui-test
```

### Test-specific tracing

For capturing tracing output in tests, use the test subscriber helper in `tracing_setup.rs`:

```rust
use sidequest_server::tracing_setup::tracing_subscriber_for_test;

let buffer = Arc::new(Mutex::new(Vec::new()));
let subscriber = tracing_subscriber_for_test(buffer.clone());
// Use tracing::subscriber::with_default(subscriber, || { ... })
```

---

## Scenarios

YAML scenario files in `scenarios/` drive scripted playtests:

```bash
just playtest-scenario smoke_test       # Basic game loop
just playtest-scenario combat_stress    # Combat subsystem stress test
just playtest-scenario otel_extended    # Long-running for dashboard observation
```

---

## Environment Setup

First-time setup for all repos:

```bash
just setup
```

This installs Rust toolchain components, npm dependencies, and Python dev dependencies across all three subrepos.

---

## Architecture Decision Records

54 ADRs document the key architectural decisions. See [docs/adr/README.md](adr/README.md).

Key ADRs for debugging and development:
- **ADR-031:** Semantic telemetry — the three-layer observability model
- **ADR-035:** Unix socket IPC — how API talks to daemon
- **ADR-038:** WebSocket transport — broadcast architecture (now two-channel post-TTS, see ADR-076)
- **ADR-039:** Narrator structured output — JSON sidecar extraction
- **ADR-047:** Prompt injection sanitization — protocol-layer input defense
- **ADR-044:** Speculative prerendering — latency hiding during the gap between narration turns
