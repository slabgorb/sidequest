---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-29: intent_router degrade path doesn't persist decompose spans to turn_telemetry (GM-panel blind on degraded turns)

## Business Context

ADR-113's whole point is that the GM panel is the lie detector: every router decision
emits an OTEL span so Keith-the-dev can verify the mechanical spine engaged instead of
the narrator improvising. The router has an opt-in degrade path — when
`SIDEQUEST_INTENT_ROUTER_DEGRADE_ON_FAIL` is set and the router raises
`IntentRouterFailure` after its bounded retry, the turn continues with
`dispatch_package=None` (the pre-ADR-113 narrator-only behavior). The 2026-05-27
playtest found that **on this degraded path the router's decompose spans are not
persisted to `turn_telemetry`**, so when an operator later inspects a degraded turn
the GM panel is blind: it can't show that the router was attempted, why it failed, or
that the turn ran without mechanical backing. That is the precise scenario the
OTEL-observability principle exists to make visible — and it's exactly the turn an
operator most needs to inspect (the one where the lie detector itself fell back).

This is a direct fix to the observability contract: degraded-turn router telemetry
must land in `turn_telemetry`, with a test asserting persistence on the degrade path.

## Technical Guardrails

**The degrade path:**
- `sidequest/server/websocket_session_handler.py` — the `try/except
  IntentRouterFailure` around `execute_intent_router_pre_narrator_pass`
  (lines ~746-789). On failure, if `SIDEQUEST_INTENT_ROUTER_DEGRADE_ON_FAIL` is set,
  it logs `intent_router.degraded_continue` (line ~773) and sets
  `_dispatch_package = None` / `_bank_result = None` (lines ~786-787), then continues
  to `run_narration_turn`. Otherwise it re-raises (fail-loud default).

**Why the spans don't persist (root cause to confirm):**
- `sidequest/agents/intent_router.py` — `IntentRouter.decompose`. The SUCCESS span
  `intent_router.decompose` is only emitted on the success branch (lines ~297-305),
  *after* validation; on failure each attempt emits an ERROR-level
  `intent_router.failed` span via `_emit_failed_span` (lines ~312-324). So on a
  fully-failed (degraded) turn there is **no `decompose` span at all** — only
  `failed` spans. The decompose telemetry the panel expects on a normal turn is
  simply absent on a degraded one.
- These spans fire *before* the narration turn opens its DB transaction. They route
  through `publish_event` (`sidequest/telemetry/watcher_hub.py:534`) with the default
  `tx=None` / `event_seq=None`, which means `_persist_turn_telemetry` (line ~398)
  takes the out-of-frame branch: `tx is None -> _telemetry_sink.record(...)` opening
  its own session_tx with NULL `event_seq` (lines ~412-418, ~436-449). **If no
  telemetry sink is bound for the session, that branch is a no-op** (legacy/in-memory
  guard) — and a degraded turn may be tearing down or never establishing the frame
  that binds the sink, so the failed/decompose spans evaporate. Confirm whether the
  sink is bound at the point the router runs on the degrade path; the fix is to
  ensure the degraded turn's router spans (the `intent_router.failed` ERROR spans,
  and ideally a degrade-marker for the absent decompose) reach `turn_telemetry`.

**Persistence machinery (do not duplicate):**
- `sidequest/telemetry/watcher_hub.py` — `publish_event(..., tx=, event_seq=)`
  (line ~534), `_persist_turn_telemetry` (line ~398). The in-frame vs out-of-frame
  split is decided by the EXPLICIT `tx` parameter (no connection-state sniffing).
  `_EPHEMERAL_EVENT_TYPES` (line ~335) is the explicit non-persist set — router
  spans are NOT ephemeral and MUST persist.
- The Postgres telemetry sink lives at `sidequest/game/pg/telemetry.py`
  (`PgTelemetrySink`); `turn_telemetry` is read by `sidequest/game/pg/forensic.py` /
  `forensic_query.py` for the GM panel.

**OTEL/No-Silent-Fallbacks:** the failed spans are ERROR-level and the degrade is an
operator opt-in, NOT a silent fallback — so the telemetry MUST record that the router
was attempted-and-failed-and-degraded. Losing it silently is the bug.

**Do NOT touch:** the fail-loud default (re-raise when the env var is unset), the
ephemeral-event-type set, or the success-path decompose span.

## Scope Boundaries

**In scope:**
- Ensure that on the degrade path (`IntentRouterFailure` caught, env var set), the
  router's decompose-attempt telemetry — the `intent_router.failed` spans and a
  durable marker that the turn degraded — is persisted to `turn_telemetry`.
- A test asserting persistence (a `turn_telemetry` row, or the bound sink's
  `record(...)`, is written) on the degrade path.

**Out of scope:**
- Changing the router's success-path span emission or the bounded-retry contract.
- The fail-loud (non-degrade) default behavior.
- p50/p95 latency diagnosis (71-22/71-26) — this is purely about persistence on
  degrade.

## AC Context

**AC1 — degraded-turn router telemetry persists.** Drive a turn where the injected
router raises `IntentRouterFailure` with `SIDEQUEST_INTENT_ROUTER_DEGRADE_ON_FAIL`
set, with a real (or fake-but-record-capturing) telemetry sink bound. Assert at
least one router telemetry row reaches `turn_telemetry` (or the sink's `record` is
called) for that turn — i.e. the `intent_router.failed` span(s) and/or a degrade
marker are persisted, not dropped. This is the failing test today (the panel is
blind).

**AC2 — fail-loud default unchanged.** With the env var UNSET, `IntentRouterFailure`
still propagates (the turn surfaces an explicit failure); assert no silent
continuation. This guards against the fix accidentally swallowing the failure.

**Edge cases:**
- No sink bound (legacy/in-memory): persistence is a no-op by design (not an error) —
  the test for AC1 must bind a sink so the persistence path is actually exercised.
- The decompose *success* span is absent on a fully-failed turn (by construction);
  the durable signal the panel needs is the `failed` span(s) plus the degrade
  marker, not a fabricated decompose span.

**Wiring (required):** the test must drive the *real* degrade path in
`websocket_session_handler` (or `intent_router_pass` + the handler's except block),
through the real `publish_event` → `_persist_turn_telemetry` machinery with a bound
sink — not a unit test that calls the sink directly.

## Assumptions

- The root cause is that the degrade path's router spans fire outside a turn frame /
  without a bound sink (or the failed spans were never expected to persist), leaving
  `turn_telemetry` empty for the turn. If investigation shows the spans DO persist but
  the GM panel query filters them out, the fix shifts to the query side
  (`forensic_query.py`) — log a Design Deviation and notify SM.
- `intent_router.failed` is the correct durable record of the attempt; if the team
  wants an explicit `intent_router.degraded` marker event in addition, that is a
  small additive span and within scope.
- A test sink that captures `record(...)` calls is available via the integration
  conftest (`tests/integration/conftest.py` re-exports `store_bound_to_hub` /
  `otel_capture`); reuse it rather than mocking the whole hub.

If the degrade path's spans turn out to already persist in some configurations, the
test must pin the *playtest configuration* that loses them, not a configuration that
already works.
