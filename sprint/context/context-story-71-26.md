---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-26: Solo turn-latency p95 — diagnose/cap tool-loop iterations

## Business Context

Sibling to 71-22 (which diagnoses the *router* pass). This story owns the **narrator
SDK tool-loop** — the second LLM pass per turn. On the ADR-101 default backend, each
narration turn runs `AnthropicSdkClient.complete_with_tools`, a loop that calls the
model, dispatches any requested tools, appends the results, and calls again — up to
`max_iterations` times. A turn that keeps requesting tools (or a model that won't
converge on a final text block) burns one full SDK round-trip per iteration, and
solo-turn p95 latency balloons. The 2026-05-27 playtest flagged solo turns running
long; the suspect is runaway tool-loop iterations.

The loop already has a ceiling (`max_iterations: int = 8`) and already raises
`AnthropicSdkLoopExceeded` when it doesn't converge — so the failure mode is "loud"
at the absolute ceiling, but there is **no per-turn observability on how many
iterations a turn actually consumed**, and no cheaper-than-8 cap with a recorded
cap-hit signal. This story: measure solo-turn p95, identify whether tool-loops are
the cause, and add an iteration cap with an **OTEL span on cap-hit** so the GM panel
(the lie detector) shows when a turn is being throttled rather than silently eating
latency. This serves Keith-the-dev directly — when a turn is slow he must see *why*.

## Technical Guardrails

**Primary surface — the tool loop:**
- `sidequest/agents/anthropic_sdk_client.py` — `complete_with_tools` (line ~281).
  - The loop: `for iteration in range(1, max_iterations + 1):` (line ~330).
  - `max_iterations: int = 8` (line ~290) — the existing ceiling.
  - Per-iteration span ALREADY exists: `with llm_request_span(model=model,
    iteration=iteration) as span:` (line ~356) wraps each SDK call. Iteration count
    is therefore already observable per call, but there is no *turn-level* "loop
    consumed K iterations" or "cap hit" summary span.
  - Non-convergence ALREADY raises loud: `raise AnthropicSdkLoopExceeded("Tool-use
    loop did not converge in {max_iterations} iterations")` (line ~610-612). The
    exception class docstring is at line ~104. **Do not weaken this fail-loud
    behavior** — the cap this story adds is about observability + an earlier,
    recorded throttle, not silencing the ceiling.

**Reuse-first for p95:**
- `sidequest/telemetry/validator.py:_percentile(values, pct)` (line ~572), already
  used for p50/p99 (lines ~555-556). Reuse it for solo-turn p95.

**Turn duration is already recorded:**
- `sidequest/server/websocket_session_handler.py` logs
  `session.narration_complete ... duration_ms=%s` (line ~801-807) with
  `result.agent_duration_ms`. That is the solo-turn wall-clock to feed the p95
  measurement.
- The cost-summary span at the end of `complete_with_tools` (around line ~979,
  "fires once per successful complete_with_tools return") is the natural home for a
  turn-level `iterations_used` attribute.

**OTEL discipline (CLAUDE.md):** the cap-hit decision is a subsystem decision and
MUST emit a span. Add a span (or an attribute on the existing per-turn cost/summary
span) recording `iterations_used`, the cap value, and a boolean/`decision` for
cap-hit, routed through the telemetry span registry (`sidequest/telemetry/spans/`,
following the `intent_router.py` span-route pattern). Source-text wiring tests are
banned (CLAUDE.md "No Source-Text Wiring Tests") — assert via span emission or
fixture-driven behavior.

**Do NOT touch:** the router decompose pass (71-22's surface), streaming deltas
(71-23), the cost-ceiling / runaway-fingerprint alarm (Story 61-4 — a separate
guard), or the `claude -p` non-tooling path.

## Scope Boundaries

**In scope:**
- Measure solo-turn p95 latency over a representative run; correlate with tool-loop
  iteration counts to confirm/deny tool-loops as the cause.
- Add a tool-loop iteration cap (a configurable max, defaulting to the current 8 or
  lower as diagnosis warrants) with an OTEL span/attribute recording `iterations_used`
  and a cap-hit signal.
- Emit a span when the cap is hit so the GM panel surfaces throttled turns.

**Out of scope:**
- Router pass latency / env-vs-code attribution — owned by 71-22.
- Streaming narration — owned by 71-23.
- Reducing the *cause* of extra iterations (prompt tuning, tool-description fixes
  that make the model converge faster) — a downstream fix this diagnosis scopes.
- Changing the cost-ceiling terminal-refusal contract.

## AC Context

**AC1 — solo-turn p95 measured.** Drive a representative solo run and collect
per-turn `agent_duration_ms` (or the `complete_with_tools` summary duration); compute
p95 via `_percentile`. Test: feed the harness a list of recorded turn durations,
assert it yields a p95 number. Edge case: include a turn that hit `max_iterations`
(loop-exceeded) so the tail is represented.

**AC2 — runaway tool-loops identified.** The per-turn summary must expose
`iterations_used` so a turn that consumed many iterations is distinguishable from a
one-shot turn. Test: drive `complete_with_tools` with a mocked SDK that requests a
tool on the first K iterations then returns final text; assert the emitted summary
records `iterations_used == K+1` (or equivalent).

**AC3 — iteration cap with OTEL cap-hit span.** When the loop reaches the cap, a span
fires recording the cap value and `iterations_used`, AND the existing
`AnthropicSdkLoopExceeded` fail-loud behavior is preserved at the true ceiling.
Test: mock the SDK to request a tool every iteration; assert (a) the cap-hit span
emits with the cap value, and (b) `AnthropicSdkLoopExceeded` still raises (no silent
swallow). If the cap is set below 8 and below the loop-exceeded ceiling, assert the
cap-hit span fires at the cap before the ceiling raise.

**Wiring (required):** a test must drive the *real* `complete_with_tools` (mocked
SDK transport) and assert the iteration/cap span actually emits through the watcher
hub — not a unit test of a counter in isolation.

## Assumptions

- Tool-loop iteration count is a leading cause of solo-turn p95 (the playtest
  finding's hypothesis); diagnosis may confirm a different dominant cause (e.g. a
  single slow large-output iteration), in which case the cap is still valuable but
  the diagnosis narrative changes — log a Design Deviation if so.
- The existing `max_iterations=8` ceiling and `AnthropicSdkLoopExceeded` raise are
  the right fail-loud anchor; the new cap layers observability/throttle on top, it
  does not replace the loud ceiling.
- `result.agent_duration_ms` is the canonical solo-turn wall-clock and is already
  populated on the success path (confirmed at the `narration_complete` log site).
- Tests mock the SDK; no live `ANTHROPIC_API_KEY` required.

If diagnosis shows tool-loops are NOT the cause, the cap remains a defensive guard
but the story's emphasis shifts to the actual cause — notify SM.
