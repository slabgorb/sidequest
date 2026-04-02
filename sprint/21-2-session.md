---
story_id: "21-2"
jira_key: "none"
epic: "Epic 21"
workflow: "tdd"
---
# Story 21-2: OTLP receiver in playtest dashboard — parse and broadcast Claude Code telemetry

## Story Details
- **ID:** 21-2
- **Title:** OTLP receiver in playtest dashboard — parse and broadcast Claude Code telemetry
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** 21-1 (split playtest.py into modules)
- **Epic:** 21 — Claude Subprocess OTEL Passthrough — See Inside the Black Box (ADR-058)
- **Repos:** orchestrator (scripts/)
- **Points:** 5
- **Priority:** p1

## Acceptance Criteria
1. POST /v1/logs parses claude_code.tool_result events into tool spans
2. POST /v1/metrics parses claude_code.token.usage into token stats
3. POST /v1/traces parses tool spans from trace payloads
4. Parsed events broadcast to dashboard browsers via WebSocket
5. Envelope format distinguishes OTEL events from watcher events
6. Span buffer bounded at 500 with FIFO eviction
7. Late-joining browsers receive span history
8. --otlp-port CLI flag configures receiver port
9. Unit tests for all three parse functions (modeled on Frame's test_148_5)

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T15:53:55Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T15:53:55Z | - | - |

## Story Context

### Architecture
The playtest dashboard runs as an HTTP server with WebSocket broadcast. Story 21-1 split playtest.py into:
- **playtest.py** — CLI/main dispatch
- **playtest_dashboard.py** — HTTP server, WebSocket broadcast (53K lines)
- **playtest_messages.py** — Message rendering helpers
- **playtest_otlp.py** — Empty skeleton for OTLP receiver (to be populated)

This story populates playtest_otlp.py with an OTLP HTTP receiver that:
- Listens on a separate port (--otlp-port, defaults to dashboard_port + 2)
- Accepts POST to /v1/logs, /v1/metrics, /v1/traces
- Parses Claude Code OTEL JSON format (same format as Frame's otlp.py)
- Buffers spans (500 max, FIFO eviction)
- Broadcasts parsed events to dashboard WebSocket clients as {"source": "claude_otel", ...}

### Reference Implementation
Frame (internal work project) has otlp.py with reference parsing logic. Model the parse functions on Frame's implementation.

### Dependencies
- Story 21-1 (split playtest.py) — COMPLETED 2026-04-02
- Story 21-3 (dashboard Claude tab) — Depends on this; receives OTEL broadcast events
- Story 21-4 (ClaudeClient env var injection) — Parallel; configures subprocess OTEL endpoint

## Delivery Findings

No upstream findings.

## Design Deviations

No design deviations at setup.
