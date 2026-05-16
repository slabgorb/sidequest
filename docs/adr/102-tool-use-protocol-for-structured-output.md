---
id: 102
title: "Tool-Use Protocol for Structured Output"
status: accepted
date: 2026-05-15
deciders: [Keith Avery]
supersedes: [39]
superseded-by: null
related: [13, 39, 101]
depends_on: [101]
tags: [agent-system, prompt-engineering]
implementation-status: partial
implementation-pointer: 101
load_bearing: true
---

# ADR-102: Tool-Use Protocol for Structured Output

## Status

**Proposed.** Lands `accepted` on the same Phase E merge that promotes
ADR-101 — they ship together because the SDK backend and the tool-use
protocol are two views of the same change.

## Context

ADR-039 introduced a JSON sidecar block embedded inside the narrator's
prose output (a fenced ` ```game_patch ` block). A three-tier
`extract_structured_from_response` parser (ADR-013) recovers the JSON
even when the model wraps it in extra fences, adds preamble, or skips
the close fence. ~10% of `claude -p` responses required the fallback
tiers; the fence parser is ~200 LOC; the extraction surface is fragile
in three ways:

1. **Forgeable.** The narrator can describe a mechanical effect in prose
   without emitting the corresponding sidecar field. The OTEL dashboard
   sees a story event with no mechanical write — a structural lie.
2. **Format-coupled.** Each new structured output (e.g. `magic_working`,
   `companions_added`, `items_consumed`) requires teaching the model a
   new sidecar schema AND adding a new extractor branch AND wiring the
   downstream `narration_apply` field.
3. **Drift-prone.** When the model occasionally produces a near-miss
   JSON (trailing commas, smart quotes), the parser silently falls
   back; the OTEL surface logs the recovery but the downstream effects
   can land subtly wrong.

ADR-001's `claude -p` constraint forced the sidecar approach: there was
no in-protocol way to call back from the LLM mid-generation. ADR-101
removes that constraint by switching the narrator backend to the
Anthropic SDK, which supports the standard tool_use → tool_result
round-trip natively.

## Decision

**Structured output moves from prose-embedded sidecars to typed
tool_use calls.** The narrator orchestrator hands the model a
JSON-Schema-described catalog of tools and dispatches each
`tool_use` block through a typed Pydantic-validated adapter in the
tool registry (ADR-101 §Tool Registry). Each tool call:

1. Validates its `input` against a Pydantic model (`args_model` on
   `@tool` registration).
2. Executes a typed handler that mutates state or returns a typed
   result.
3. Emits an OTEL `tool.{category}.{name}` span carrying input + output
   + perception-filter decisions.
4. Returns a `ToolResultBlock` that the SDK feeds back into the model
   on the next iteration.

The narrator can no longer describe a mechanical effect without
invoking the corresponding tool — the model emits an explicit
`tool_use` block or the effect didn't happen. This is the structural
lie-detection mechanism ADR-101 promised.

### Coverage

Phase C's `tests/agents/test_sidecar_coverage_map.py` is a hard gate:
every sidecar field from `NarrationTurnResult` has a designated
successor tool, and the test fails if any cell is `None`. The 26-tool
v1 catalog covers the full surface; the test is the entry gate for
this ADR's acceptance.

### `apply_world_patch` escape hatch

A typed `apply_world_patch` tool accepts an arbitrary
patch-dict for not-yet-typed mutations (current scope: 5 top-level
fields — `location`, `time_of_day`, `atmosphere`, `current_region`,
`active_stakes`). It logs heavy OTEL for any out-of-scope field so the
deprecation criterion ("zero spans across 10 consecutive playtests")
is measurable from day one.

## Consequences

### Positive

- Structural lie-detection (the GM panel sees a tool span or the
  effect didn't happen).
- 26 tools cover every former sidecar field — schema discoverable,
  validated, typed.
- Adding a new structured output is a `@tool`-decorated adapter, not a
  prose-prompt change + extractor branch.
- Perception filtering becomes natural at the tool result boundary
  (ADR-104).

### Migration cost / partial-implementation reality

The Phase D plan envisioned outright deletion of
`sidequest/agents/claude_stream_parser.py` and removal of the
sidecar parser. The actual Phase D scope was narrower because:

- `claude_stream_parser.py` is the **Claude CLI NDJSON stream parser**,
  not the ADR-039 sidecar parser. It is load-bearing for `ClaudeClient`
  streaming and stays.
- The ADR-039 sidecar parser is `extract_structured_from_response` in
  `sidequest/agents/orchestrator.py` (plus `stream_fence.py` for the
  streaming variant). Both remain live because Phase C did **not**
  retire the `narrator_output_only` injection in
  `NarratorAgent.build_output_format` — the narrator prompt still
  instructs the model to emit a `game_patch` sidecar.
- Phase D's SDK narrator path wraps `ToolingResult.text` back into a
  `ClaudeResponse` shim and still invokes the sidecar parser. Both
  surfaces — tool calls AND sidecar — are populated by the model
  during the migration; downstream consumers see whichever shows up.
  This is intentional belt-and-suspenders during the in-flight period.

ADR-013 is marked `drift` with `superseded-by: 102` — the three-tier
extraction stays live but is on a retirement path. The post-Phase-D
follow-up is:

1. Drop the `narrator_output_only` instruction from the SDK code path
   (keep it on the legacy ClaudeClient path until Phase E retires the
   backend altogether).
2. Update `_assemble_turn_result` on the SDK path to skip
   `extract_structured_from_response` and populate
   `NarrationTurnResult` from the tool-call ledger only.
3. Delete the sidecar parser, `extract_structured_from_response`, and
   `stream_fence.py` once the legacy ClaudeClient backend is retired
   in Phase E.

### Negative

- Model occasionally hallucinates a tool that doesn't exist — the SDK
  surfaces this as a `tool_use` for an unknown tool; the dispatcher
  must return a structured `is_error=True` ToolResult so the model
  recovers on the next iteration.
- Tool-use round-trips cost extra HTTP round-trips per turn vs a
  single fenced-JSON parse. Cache-zone discipline (ADR-101 §Cache
  zones) mitigates the per-trip cost; tool latency is the new lever.

## References

- ADR-101 — Anthropic SDK as Narrator Backend (parent)
- ADR-039 — Narrator Structured Output (superseded)
- ADR-013 — Lazy JSON Extraction (drift, this is its successor)
- Design spec: `docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md`
- Phase C plan (tool catalog): `docs/superpowers/plans/2026-05-15-anthropic-sdk-migration-phase-c-tool-conversions.md`
