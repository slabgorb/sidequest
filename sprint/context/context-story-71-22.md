---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-22: Glenross router latency AC5 — measure + diagnose 4-12s vs <1.2s budget (env vs code)

## Business Context

Epic 59 (Intent Router — Mechanical-Engagement Spine) added a pre-narrator Haiku
pass that decomposes every player action into a `DispatchPackage` *before* the
narrator runs. ADR-113's latency budget (59-8 AC5) was an explicit **< 1.2s** for
that router add — Haiku 4.5 was expected at ~0.3-0.5s, with the rest of the budget
absorbing pipeline overhead. The 2026-05-27 `coyote_star` MP playtest (and the
Glenross / `tea_and_murder` follow-up) measured **4-12s** for the router decompose
pass — 3-10x over budget. That is a player-facing stall on every turn: the table
waits on the lie-detector spine before the narrator even begins.

This story does **not** fix the latency. It is a diagnosis story: instrument the
router decompose pass, capture p50/p95 over a representative Glenross run, and
**attribute the cost** — is it environmental (Haiku SDK call round-trip, network,
cold connection) or code (oversized state-summary prompt, retry firing, tool-schema
bloat)? The output is an evidence-backed diagnosis that tells the next story (a fix)
where to cut. It serves Keith-the-dev: the GM panel must show *why* a turn is slow,
not just that it is. It is the sibling of 71-26 (solo turn-latency p95 / narrator
tool-loop) — together they bracket the two LLM passes per turn.

## Technical Guardrails

**Primary instrumentation site — already emits latency:**
- `sidequest/agents/intent_router.py` — `IntentRouter.decompose` wraps the
  successful path in `intent_router_decompose_span(...)` and already sets
  `latency_ms` (measured via `time.perf_counter_ns()` around the whole attempt
  loop, lines ~222 and ~296-304), plus `retry_count` and `dispatch_count`. The
  span is `intent_router.decompose` (`SPAN_INTENT_ROUTER_DECOMPOSE` in
  `sidequest/telemetry/spans/intent_router.py`). **The latency signal already
  exists** — the work is capturing it across a run and decomposing it, not adding
  the first measurement.
- The per-attempt failure span `intent_router.failed`
  (`intent_router_failed_span`) carries `retry_count` — a high retry rate inflates
  total latency (each retry is a fresh SDK round-trip). Whether retries are firing
  is a first-order env-vs-code signal.

**Env-attribution anchors (the SDK call itself):**
- `sidequest/agents/llm_factory.py` — `_INTENT_ROUTER_MODEL = "claude-haiku-4-5-20251001"`
  (line ~119); `build_intent_router_llm()` (line ~199) builds the SDK-Haiku adapter
  the router injects. The raw SDK round-trip is the env cost; isolate it by timing
  *inside* `emit_tool` separately from the surrounding `decompose` bookkeeping.
- `sidequest/agents/model_routing.py` — `CallType.CLASSIFICATION → claude-haiku-4-5-20251001`
  (line ~28). Confirms the router is on Haiku, not accidentally routed to a slower
  model.

**Code-attribution anchors (prompt size / loop / schema):**
- `sidequest/server/intent_router_pass.py` — `_build_state_summary` (line ~75)
  builds the JSON state-summary the router sends. It uses
  `snapshot.model_dump(exclude_defaults=True, exclude_none=True)` and appends a
  `confrontation_types` projection. **Prompt-size is the prime code suspect**:
  measure the serialized `state_summary` byte/token length per turn and correlate
  with `latency_ms`. `action_length` is already a decompose-span attribute — add
  state-summary size alongside it.
- `_dispatch_tool_schema()` in `intent_router.py` (line ~94) =
  `DispatchPackage.model_json_schema()`. A large forced tool schema adds input
  tokens every call.

**Reuse-first for p50/p95:**
- `sidequest/telemetry/validator.py` already has `_percentile(values, pct)`
  (line ~572) and uses it for p50/p99 (lines ~555-556). **Reuse it** — do not write
  a second percentile helper.

**Do NOT touch:** the narrator tool-loop (that is 71-26's surface,
`anthropic_sdk_client.py:complete_with_tools`), the confidence-gate logic, or the
fail-loud retry contract. This story measures; it does not change router behavior.

## Scope Boundaries

**In scope:**
- Capture p50/p95 of `intent_router.decompose` `latency_ms` over a representative
  Glenross (`tea_and_murder`) run (live or replayed scenario).
- Add the missing decomposition signals needed to attribute env vs code: the raw
  SDK-call duration (inside `emit_tool`) separated from the surrounding decompose
  bookkeeping, the serialized `state_summary` size, and the observed `retry_count`
  distribution. Emit these as OTEL attributes on the existing spans (no new span
  family required).
- A written diagnosis with evidence: a numeric env-vs-code attribution (e.g. "SDK
  round-trip = N s p95, state-summary = M tokens, retries fired on K% of turns").

**Out of scope:**
- Any latency *fix* (prompt slimming, caching the router system prompt, connection
  reuse, retry tuning) — that is a downstream fix story this diagnosis scopes.
- Solo narrator-turn p95 and the tool-loop iteration cap — owned by 71-26.
- Changing the 1.2s budget or the ADR-113 fail-loud contract.

## AC Context

**AC1 — p50/p95 captured.** Drive a representative Glenross turn set and collect the
`intent_router.decompose` `latency_ms` values. A test can assert the measurement
harness produces p50 and p95 numbers from a list of captured decompose spans, reusing
`telemetry/validator.py:_percentile`. Edge case: a run where retries fired must
include the retry-inflated turns (do not silently drop `intent_router.failed`
attempts — they are part of the wall-clock cost the player feels).

**AC2 — env-vs-code attribution with evidence.** The decompose span (or a sibling
span) must carry enough attributes to split total `latency_ms` into (a) raw SDK
round-trip and (b) in-process bookkeeping/prompt-assembly. A test asserts the new
attribute(s) are present and that raw-SDK ≤ total. Concretely: time `emit_tool`
independently and record both, plus the serialized `state_summary` size.

**AC3 — diagnosis artifact.** A diagnosis (committed as a session/report artifact,
not engine code) stating which cause dominates, with the captured numbers. Testable
precondition: the instrumentation AC1/AC2 add is present and emits on the real
`decompose` path (drive a fixture/mock router through `decompose`, assert the new
attributes fire on the success span and, where relevant, on the failed span).

**Wiring:** at least one test must drive the *real* `IntentRouter.decompose` (with a
mocked `IntentRouterLLM` returning a valid `DispatchPackage`) and assert the new
attribution attributes land on the emitted `intent_router.decompose` span — not a
unit test of a standalone timing helper.

## Assumptions

- The `intent_router.decompose` span's `latency_ms` is the canonical router-pass
  cost and is already wired through `publish_event` to the GM panel (confirmed: the
  span route exists in `telemetry/spans/intent_router.py`).
- A Glenross / `tea_and_murder` scenario can be driven headlessly (via the playtest
  driver or a scenario fixture) without a live human table; if not, the run may be
  captured from a recorded session's telemetry rows.
- Mocked-LLM tests cannot measure real network/env latency; the env-vs-code split's
  *real numbers* come from a live or recorded run, while tests only assert the
  attribution *instrumentation* is present and correct.
- The retry path (`_MAX_TOTAL_ATTEMPTS = 2`) is unchanged; if diagnosis finds retries
  are a dominant cost, that informs a downstream fix, not this story.

If any assumption proves wrong (e.g. the decompose span is not reaching the panel on
degraded turns — see 71-29), log a Design Deviation and notify SM.
