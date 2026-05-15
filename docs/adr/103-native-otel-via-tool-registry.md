---
id: 103
title: "Native OTEL via Tool Registry"
status: proposed
date: 2026-05-15
deciders: [Keith Avery]
supersedes: [58]
superseded-by: null
related: [31, 58, 90, 101, 102]
depends_on: [101, 102]
tags: [observability, agent-system]
implementation-status: partial
implementation-pointer: 101
load_bearing: true
---

# ADR-103: Native OTEL via Tool Registry

## Status

**Proposed.** Promotes to `accepted` on the Phase E merge alongside
ADR-101 and ADR-102.

## Context

ADR-058 routed the Claude CLI subprocess's own OpenTelemetry exporter
to the SideQuest OTLP collector via environment variables
(`CLAUDE_CODE_ENABLE_TELEMETRY=1`,
`OTEL_EXPORTER_OTLP_ENDPOINT=<sidequest-otlp>`). The subprocess emitted
its own spans (`claude.cli.*`) into our trace tree, and SideQuest
correlated them with the `agent_call_span` parent on the Python side.

This worked but had three structural weaknesses:

1. **Forensic, not direct.** The narrator's mechanical decisions
   (resolve roll, apply damage, advance scene, etc.) lived inside the
   model's prose output; the subprocess OTEL only saw "model produced
   text." No span existed for the *mechanical effect itself* — we
   reconstructed it after the fact from the sidecar parser.
2. **Per-process span IDs.** The subprocess emitted its own trace_id;
   stitching parent/child relationships across the subprocess boundary
   required careful collector configuration.
3. **No structural lie-detection.** A narration that claimed a damage
   effect without a corresponding sidecar field showed up as a missing
   sidecar — but that's an absence, not a span. There was no
   first-class way to say "the model just claimed X happened without
   the X span being present."

## Decision

**OTEL emission moves into the Python tool registry on the narrator
path.** Every model HTTP call and every tool dispatch is wrapped in a
typed span on the Python side, native to the same tracer the rest of
the server uses.

### Span taxonomy

| Span | Emitter | When |
|---|---|---|
| `narration.turn` | `sidequest/telemetry/spans/cost.py` | Once per turn — rollup parent |
| `llm.request` | `sidequest/telemetry/spans/llm_request.py` (Phase A) | Each `messages.create` call inside the tool-use loop |
| `tool.{category}.{name}` | `Registry.dispatch` (Phase B) | Each tool invocation; attributes: input keys, output status, perception-filter applied |
| `tool.write.*` | as above, write-category subset | Mutation-class tools — appear iff the narrator actually mutated state |

Three new structural-lie-detection classes become possible:

1. **Mechanical assertion without span** — the narrative says "Carl
   takes 4 damage" but no `tool.write.apply_damage` span fires →
   flagged in the GM panel.
2. **State described without query span** — the narrative says
   "Donut's mood lifts" but no `tool.read.query_npc` span fires for
   Donut → flagged.
3. **Perception-filter violation** — a tool result's
   `perception_filtered` attribute disagrees with the `perspective_pc`
   on the parent `narration.turn` span → flagged.

### Cost-USD rollup

`narration.turn.total_cost_usd` is computed from per-iteration
`llm.cost_usd` (`AnthropicSdkClient` already computes via
`sidequest/agents/anthropic_cost.py`). The GM panel displays
per-turn-cost — visible budget for runaway tool loops.

## Consequences

### Positive

- Native Python OTEL — no subprocess passthrough plumbing for the
  narrator path.
- Single tracer, single trace_id per turn, native parent/child
  relationships.
- Structural lie-detection classes 1, 2, 3 above are first-class.
- ADR-031 (Game Watcher — Semantic Telemetry) principle preserved;
  only the mechanism changes.

### What survives ADR-058

The Claude CLI OTEL passthrough environment-variable setup remains
**live** for the auxiliary `ClaudeClient` paths (mood classifier, name
gen, scratch). These paths still subprocess to `claude -p` and still
emit `agent_call_span` parents; their subprocess OTEL is still useful.

The Phase D plan called for deleting "narrator-specific subprocess
stderr scraping" — no such scraping exists. The mechanism was always
the env-var passthrough at `claude_client.py:429-442`. That code stays
because:

- It's gated on `self._otel_endpoint` being set (already optional).
- It's used by the same `ClaudeClient.__init__` that auxiliary callers
  reach today.
- The Phase D narrator SDK path doesn't touch `ClaudeClient`, so no
  narrator-side OTEL ambiguity arises.

In short: ADR-058's mechanism is no longer load-bearing for the
narrator (Phase E formalizes), but it stays live for auxiliaries.
Both ADRs coexist during the migration window; ADR-058's status flips
to `superseded` at Phase E merge, but the underlying env-var
passthrough code stays in the codebase until the auxiliary paths
themselves move to native instrumentation (no immediate plan).

### Negative

- Trace volume rises during a multi-tool turn — each tool call is a
  span. Most tools complete in <5ms; the span budget per turn is
  bounded by the model's tool-use loop iteration count (max 8 in
  `complete_with_tools`).

## References

- ADR-101 — Anthropic SDK as Narrator Backend (parent)
- ADR-058 — Claude Subprocess OTEL Passthrough (superseded for the
  narrator path; retained for auxiliaries)
- ADR-031 — Game Watcher — Semantic Telemetry for AI Agent
  Observability (principle preserved)
- ADR-090 — OTEL Dashboard Restoration after Python Port (consumer)
- Design spec: `docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md` §OTEL / observability
