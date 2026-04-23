---
story_id: "21-3"
epic: "21"
workflow: "tdd"
---

# Story 21-3: Dashboard Claude tab — tool timeline, token breakdown, cost accumulator

## Story Details

- **ID:** 21-3
- **Epic:** 21 — Claude Subprocess OTEL Passthrough — See Inside the Black Box (ADR-058)
- **Workflow:** tdd
- **Repos:** orchestrator (React dashboard), sidequest-api (optional for later turns)
- **Points:** 5
- **Priority:** p1

## Acceptance Criteria

- Tab 8 (Claude) appears in dashboard tab bar
- Tool call timeline renders with duration bars per tool invocation
- Token breakdown shows input/output/cache read/cache creation per turn
- Running cost accumulator displays total spend
- Tool failures highlighted with error indicator
- Events correlate to game turns via timestamp
- Tab badge shows count of tool invocations

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T17:32:00Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T17:32:00Z | - | - |

## Context & Dependencies

### Upstream Work

- **21-1** (DONE): Split playtest.py into focused modules
- **21-2** (DONE): OTLP receiver in playtest dashboard — parse and broadcast Claude Code telemetry

The playtest dashboard receives claude_otel WebSocket events with:
- Tool invocation spans (tool name, duration, success/failure)
- Token stats (input, output, cache read, cache creation tokens)
- Timestamp data for correlation to game turns

### Feature Description

Add a new "Claude" tab (tab 8) to the playtest dashboard HTML/JS. This tab consumes the OTEL telemetry data already being broadcast from the OTLP receiver (story 21-2) and presents:

1. **Tool Timeline** — Flame chart pattern (reuse from tab 1) showing tool invocations with duration bars
2. **Token Breakdown** — Table showing input/output/cache read/cache creation tokens per turn
3. **Cost Accumulator** — Running total of Claude API spend (using OpenAI pricing model)
4. **Tool Status** — Success/failure indicators on tool invocations
5. **Turn Correlation** — Events linked to game turns via timestamp proximity to watcher turn events
6. **Tab Badge** — Shows count of tool invocations

### Data Flow

```
OTLP Receiver (playtest_otlp.py)
  ↓ (POST /v1/logs, /v1/metrics, /v1/traces)
Playtest Dashboard (playtest_dashboard.py)
  ↓ WebSocket broadcast {source: "claude_otel", ...}
Dashboard Browser (orchestrator/playtest.html)
  ↓ Claude tab JS handler
Claude Tab (new)
  ├─ Tool Timeline
  ├─ Token Breakdown
  ├─ Cost Accumulator
  └─ Turn Correlation
```

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
