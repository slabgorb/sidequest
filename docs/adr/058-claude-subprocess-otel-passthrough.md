---
id: 58
title: "Claude Subprocess OTEL Passthrough"
status: accepted
date: 2026-04-02
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [31, 90]
tags: [observability]
implementation-status: live
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

## Implementation status (2026-05-02)

All four design pillars of this ADR are live in Python. The Rust code
sample in §Decision step 2 (lines 86–96) is preserved as historical
illustration; the 2026-04 port to Python ([ADR-082](082-port-sidequest-api-back-to-python.md))
adopted the same design unchanged.

### §1 OTLP receiver — live

`scripts/playtest_otlp.py` runs the lightweight HTTP receiver. Routes
registered at lines 154–156:

- `POST /v1/logs` → `parse_log_records` (parses `claude_code.tool_result` events)
- `POST /v1/metrics` → `parse_metric_records` (parses `claude_code.token.usage` metrics)
- `POST /v1/traces` → `parse_trace_spans`

Entry point: `run_otlp_receiver` (called from `playtest_dashboard.py:983`).

### §2 OTEL env injection — live

`sidequest-server/sidequest/agents/claude_client.py`:

- `otel_endpoint: str | None = None` constructor parameter at line 173,
  stored at line 178; property accessor at line 194.
- Env-var injection block at line 337 — when `_otel_endpoint` is truthy,
  the spawn command receives `CLAUDE_CODE_ENABLE_TELEMETRY=1`,
  `OTEL_LOGS_EXPORTER=otlp`, `OTEL_METRICS_EXPORTER=otlp`,
  `OTEL_EXPORTER_OTLP_PROTOCOL=http/json`,
  `OTEL_EXPORTER_OTLP_ENDPOINT=<self._otel_endpoint>`,
  `OTEL_LOG_TOOL_CONTENT=1`, `OTEL_LOG_TOOL_DETAILS=1`. When unset, no
  env vars are added — the zero-overhead "no telemetry configured" path
  this ADR §Consequences §Positive specified.
- `ClaudeClientBuilder.otel_endpoint(endpoint)` builder at lines 481–486.

### §3 playtest.py split — live

All four modules from the design table exist in `scripts/`:

- `playtest.py` — CLI, `main()`, mode dispatch
- `playtest_dashboard.py` — HTML/JS dashboard, WebSocket server, HTTP serving
- `playtest_otlp.py` — OTLP receiver, parsing, broadcast integration
- `playtest_messages.py` — message styles, rendering, construction helpers

### §4 Dashboard Claude tab — live

The browser dashboard's Claude tab consumes `claude_otel`-source events
(tool_result, token_usage, span) — see `scripts/tests/test_claude_tab.py:4, 295–301`
which assert `dispatch()` routes events with `source === "claude_otel"`
to the Claude tab and updates the `tab7-badge` element.

### Cross-reference

[ADR-090 (OTEL Dashboard Restoration after Python Port)](090-otel-dashboard-restoration.md) —
`accepted`/`live`, dated 2026-04-25 — explicitly cites this ADR via
`related: [31, 58, 82]` and is the load-bearing record that the
passthrough design survived the port intact. ADR-058 is the original
design; ADR-090 is its post-port confirmation.
