---
id: 58
title: "Claude Subprocess OTEL Passthrough"
status: proposed
date: 2026-04-02
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [observability]
implementation-status: deferred
implementation-pointer: null
---

# ADR-058: Claude Subprocess OTEL Passthrough

> Extends ADR-031 (Game Watcher Semantic Telemetry). Bridges the gap between
> the Rust backend's internal telemetry and the Claude CLI's internal operations.

## Context

SideQuest invokes Claude via `claude -p` as a subprocess (ADR-001). The Rust
backend wraps each call in an `agent.call` tracing span that records token
counts and duration from the JSON envelope. But Claude Code has its own rich
OTEL telemetry — tool invocations, thinking duration, per-step token breakdowns,
success/failure per tool — and none of it reaches the Game Watcher.

The result: the `agent.call` span is a black box. We know *that* Claude
responded in 8.2 seconds with 1200 input / 800 output tokens, but not *how*
it got there. Did it call three tools? Did one tool fail and retry? Did
thinking take 6 seconds and tool execution take 2? We can't tell.

### Prior Art

Pennyfarthing's BikeRack Frame (`pf/frame/otlp.py`) already receives and
renders Claude Code OTEL data — tool call timelines, token breakdowns, cost
accumulation. It proves the data is structured, parseable, and actionable.
The playtest dashboard (`scripts/playtest.py`) is the SideQuest equivalent
but currently only receives game-engine telemetry via `/ws/watcher`.

### What Claude Code Exports

Claude Code supports native OTEL export via environment variables:

| Env Var | Purpose |
|---------|---------|
| `CLAUDE_CODE_ENABLE_TELEMETRY=1` | Enable collection |
| `OTEL_LOGS_EXPORTER=otlp` | Export tool events as OTLP logs |
| `OTEL_METRICS_EXPORTER=otlp` | Export token usage as OTLP metrics |
| `OTEL_EXPORTER_OTLP_PROTOCOL=http/json` | HTTP/JSON transport |
| `OTEL_EXPORTER_OTLP_ENDPOINT=<url>` | Receiver endpoint |
| `OTEL_LOG_TOOL_CONTENT=1` | Include tool I/O in events |
| `OTEL_LOG_TOOL_DETAILS=1` | Include tool names |

Key event types:
- `claude_code.tool_result` — tool name, duration, success, input, parameters
- `claude_code.token.usage` — input, output, cache read, cache creation counts

## Decision

### 1. Embed a Lightweight OTLP Receiver in the Playtest Dashboard

The playtest dashboard (`scripts/playtest.py`) gains an HTTP server that
accepts OTLP POST requests at `/v1/logs`, `/v1/metrics`, `/v1/traces`.
Parsing logic is modeled on Frame's `otlp.py` (same OTLP JSON format,
same bounded span buffer pattern).

Received events are broadcast to connected browser clients through the
existing dashboard WebSocket, wrapped in an envelope that distinguishes
them from game-engine watcher events:

```json
{"source": "claude_otel", "type": "tool_span", "data": {...}}
{"source": "claude_otel", "type": "token_stats", "data": {...}}
```

**Not** coupled to BikeRack Frame. The playtest dashboard remains a
self-contained one-pager. Frame's code is a template, not a dependency.

### 2. Inject OTEL Env Vars into Claude Subprocess

`ClaudeClient` gains an optional `otel_endpoint: Option<String>`. When
set, `send_impl()` adds the OTEL environment variables to the `Command`
before spawn. When unset, no env vars are added and behavior is unchanged.

```rust
if let Some(endpoint) = &self.otel_endpoint {
    cmd.env("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
       .env("OTEL_LOGS_EXPORTER", "otlp")
       .env("OTEL_METRICS_EXPORTER", "otlp")
       .env("OTEL_EXPORTER_OTLP_PROTOCOL", "http/json")
       .env("OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)
       .env("OTEL_LOG_TOOL_CONTENT", "1")
       .env("OTEL_LOG_TOOL_DETAILS", "1");
}
```

The endpoint is configured via server config or CLI flag, threaded
through to the orchestrator's `ClaudeClient` instances.

### 3. Split playtest.py

The current `playtest.py` (27K+ tokens) is split into focused modules:

| Module | Responsibility |
|--------|---------------|
| `playtest.py` | CLI, main(), mode dispatch |
| `playtest_dashboard.py` | HTML/JS dashboard, WebSocket server, HTTP serving |
| `playtest_otlp.py` | OTLP receiver, parsing, broadcast integration |
| `playtest_messages.py` | Message styles, rendering, construction helpers |

### 4. Dashboard Claude Tab

New tab (⑧ Claude) in the browser dashboard showing:
- Tool call timeline with duration bars per turn
- Token breakdown (input/output/cache) per turn
- Running cost accumulator
- Tool success/failure indicators

## Consequences

### Positive
- **X-ray into the black box.** Every Claude invocation shows what tools it
  called, how long each took, and whether they succeeded.
- **Zero new infrastructure.** No OTEL collector, no new services. The
  dashboard process is already running during playtests.
- **Config-driven.** When no `otel_endpoint` is configured, zero overhead —
  no env vars set, no listener started, no behavior change.
- **Proven data format.** Frame's `otlp.py` has tested parsing for the
  exact OTLP payloads Claude Code emits.

### Negative
- **Short-lived subprocesses.** Each `claude -p` invocation is a fresh
  process. OTEL startup/shutdown happens per call. Claude Code handles
  this gracefully (flush timeout is configurable via
  `CLAUDE_CODE_OTEL_FLUSH_TIMEOUT_MS`), but some spans may be lost if
  the process exits before the flush completes. Mitigated by setting a
  reasonable flush timeout.
- **Dashboard must be running.** If the OTLP endpoint is configured but
  the dashboard isn't up, Claude Code's export will fail silently per
  call. This is acceptable — it's an observability tool, not a data path.

### Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| Console exporter → parse stderr | Extra parsing layer in Rust. Dashboard has to be the one rendering anyway. |
| Couple to BikeRack Frame | Wrong dependency direction. Playtest dashboard must be self-contained. |
| Full OTEL collector (Jaeger, etc.) | Overkill for a personal project. Adds operational complexity. |
| Embed OTLP receiver in Rust backend | Mixes observability infrastructure into the game engine. Playtest dashboard is the right home. |
