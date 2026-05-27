---
parent: context-epic-61.md
workflow: tdd
---

# Story 61-followup-B: Promote narrator.sdk.usage log line to a watcher INFO event for continuous cost-trend on GM panel

## Business Context

The GM panel is SideQuest's lie detector for the narrator (CLAUDE.md OTEL Observability
Principle). Cost is one of the things it should be able to watch continuously: every
narrator SDK call already computes `input_tokens`, `output_tokens`, `cost_usd`, `model`,
and the cache read/write split, but today those values only escape as a `logger.info`
line (`narrator.sdk.usage …`) in `anthropic_sdk_client.py`. A log line is invisible to
the GM-panel watcher transport — it cannot be plotted, grouped, or trended.

Epic 61's cost-telemetry track has already built the *alarm* half of the picture:
- **61-4** fires `cost_runaway_suspected` at `severity=warn` when a call trips a
  rolling-baseline fingerprint.
- **61-followup-D** fires per-turn session-cumulative pulses and a cost-ceiling event.

What's missing is the **continuous baseline signal** those alarms implicitly compare
against — a steady, every-call `info`-severity heartbeat of raw usage. This story
promotes the existing log line to a proper watcher event so the GM panel gets a
per-call cost trend and the warn/error alarms have a visible baseline beneath them.

This is a **Keith/dev observability** concern (OTEL-side), **not** a player-facing
feature. Per CLAUDE.md, do not frame it as a Sebastien player-UI feature — Sebastien
never sees the watcher transport.

## Technical Guardrails

**Repo:** `sidequest-server` (Python/FastAPI, uv-managed). Branch off `develop`.

**Key file to modify:**
- `sidequest/agents/anthropic_sdk_client.py` — the emit site. The `narrator.sdk.usage`
  `logger.info(...)` call lives at ~line 396–407, inside the tool-use loop in the
  streaming/tooling call path, immediately after `cost = compute_cost_usd(...)` and the
  `span.set_attributes({...})` block.

**Pattern to follow — wire up what exists, do not reinvent:**
- The watcher transport is already imported in this file:
  `from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish_event`
  (line 24).
- The **canonical sibling** is the 60-7 `narrator.cache.both_writes_fired` emit
  (~line 434): it logs *and* calls `_watcher_publish_event(event_type, fields,
  component="narrator.sdk", severity=...)`. Mirror that shape exactly — keep the
  existing `logger.info` line AND add the watcher event next to it.
- `publish_event` signature (`sidequest/telemetry/watcher_hub.py:477`):
  `publish_event(event_type: str, fields: dict, *, component="sidequest-server",
  severity="info")`. Severity vocabulary per docstring is `info | warning | error`.
  This story uses `severity="info"`.
- Use `component="narrator.sdk"` to match the sibling cache event's grouping in the
  Subsystems tab.

**OTEL span (already present, extend if needed):** the `span.set_attributes({...})`
block at ~line 384 already carries `llm.input_tokens`, `llm.output_tokens`,
`llm.cached_input_read_tokens`, `llm.cached_input_write_tokens`, `llm.cost_usd`. AC6
asks the cost fields to be span attributes for dashboard filtering — verify the model
is also represented (the call already sets `llm.*` token/cost attrs; confirm `model`
is filterable, add `llm.model` if absent). Do not regress existing attributes.

**Field contract (the six required fields):** `input_tokens`, `output_tokens`,
`cost_usd`, `model`, `cache_read_tokens`, `cache_write_tokens`. The local variables at
the emit site are `input_tokens`, `output_tokens`, `cost`, `response.model` /
`last_model`, `cache_read`, `cache_write`. Map carefully — note the watcher field is
named `cost_usd` but the local is `cost`; and `cache_write` is the *aggregate* (the
5m/1h split lives in `cache_write_5m`/`cache_write_1h`, which the both_writes detector
uses but which this story's contract does not require).

**Wiring discipline (CLAUDE.md):**
- **No source-text wiring tests.** Do NOT assert `_watcher_publish_event(` appears in
  the source. Drive a synthetic SDK response through the real tooling call path and
  capture published events via the watcher hub (the 61-4 test harness does exactly
  this — see `tests/agents/test_61_4_cost_runaway_alarm.py`, which monkeypatches a fake
  raw-responses client and captures `publish_event` calls).
- **Every test suite needs a wiring test:** at least one test must prove the event
  actually reaches the watcher transport from the production call path, not just that a
  helper can be called in isolation.

**What NOT to touch:**
- Do not modify `compute_cost_usd` / `anthropic_cost.py` pricing logic (60-4 territory).
- Do not modify the 61-4 `_maybe_emit_cost_runaway` detector or the followup-D
  `_emit_cost_running_total` / `_update_session_cumulative` ceiling logic. This story is
  additive — a new always-fire `info` event, not a change to the existing warn/error
  detectors.
- Do not change the existing `narrator.sdk.usage` log line text (other tooling/operators
  may grep it). Add alongside it.

## Scope Boundaries

**In scope:**
- Add an `info`-severity watcher event at the existing `narrator.sdk.usage` emit site
  carrying the six required fields (`input_tokens`, `output_tokens`, `cost_usd`,
  `model`, `cache_read_tokens`, `cache_write_tokens`).
- Ensure the OTEL span at that site carries the cost/token fields as attributes for
  dashboard filtering (extend with `model` if not already filterable).
- Failing-then-passing tests proving the event fires with the correct payload and is
  wired into the real call path.

**Out of scope:**
- Any GM-panel / `sidequest-ui` frontend work to *render* the trend (this story makes
  the signal available; consuming it is a separate UI concern).
- Changes to the 61-4 alarm thresholds or followup-D session-ceiling behavior.
- Per-TTL (5m/1h) cache-write breakdown in the event payload — not part of the six-field
  contract.
- Aggregating per-call events into a per-turn rollup beyond what followup-D already
  emits (see AC-3 ambiguity below).

## AC Context

**AC-1 — Log line promoted to a watcher event with `severity=info`.**
The existing `logger.info("narrator.sdk.usage …")` stays; a new
`_watcher_publish_event("narrator.sdk.usage", {...}, component="narrator.sdk",
severity="info")` fires at the same site. *Test:* drive a synthetic SDK response
through the tooling call path, capture published events, assert exactly one
`narrator.sdk.usage` event with `severity == "info"`.

**AC-2 — Event payload includes all six fields.**
`input_tokens`, `output_tokens`, `cost_usd`, `model`, `cache_read_tokens`,
`cache_write_tokens`. *Test:* assert every key is present in `event["fields"]` and the
values match the synthesized usage (e.g. input=12000, output=500, cost matching
`compute_cost_usd`, model="claude-…", cache_read/cache_write as fed). Edge cases:
zero-token fields must still be present (not omitted); `cost_usd` is a float, not a
preformatted string. **Paranoia check:** assert the field is named `cost_usd` (not
`cost`), since the local variable is `cost` — easy to mis-map.

**AC-3 — Fires once per narrator turn after the SDK call completes. ⚠ AMBIGUITY.**
The existing log line fires **per tool-use iteration** (`iter=N`), and a narrator turn
may make multiple SDK calls (tool loop). "Once per turn" therefore conflicts with the
natural emit cadence of the line being promoted. **Resolution for this story:** the
event is a *continuous per-call baseline* (the 61-4 alarm it feeds also evaluates
per-call inside the same loop), so it fires **once per SDK call / per tool-use
iteration** — a 3-iteration turn emits 3 `narrator.sdk.usage` events. A single-call turn
emits exactly one, satisfying the literal AC-3 for the common case. The per-*turn*
cumulative pulse already exists separately (followup-D `_emit_cost_running_total`); this
story does not duplicate it. *Test:* a single-iteration turn emits exactly one event; a
multi-iteration (tool-use) turn emits one event per iteration with that iteration's own
field values. **If Dev/Reviewer disagree with per-call cadence, log a Design Deviation
before changing the emit point.**

**AC-4 — Event wired into telemetry so the GM panel can consume it.**
The event must travel the real `watcher_hub` transport, matching the TypeScript
`WatcherEvent` shape (`component`, `event_type`, `severity`, `fields`, `timestamp`).
*Test (wiring):* capture at the hub boundary (as the 61-4 test does), not at the helper
call. This is the mandatory wiring test.

**AC-5 — Regression test: simple narration turn asserts the event with correct payload.**
A focused happy-path test that constructs a minimal turn through the production tooling
path and asserts the emitted event's payload. Distinct from AC-4's wiring assertion in
intent (payload correctness vs. transport reachability) though they may share a harness.

**AC-6 — OTEL span carries the cost fields as attributes for dashboard filtering.**
The `span.set_attributes({...})` block already sets `llm.input_tokens`,
`llm.output_tokens`, `llm.cached_input_read_tokens`, `llm.cached_input_write_tokens`,
`llm.cost_usd`. Confirm `model` is filterable (add `llm.model` if absent). *Test:* use
the OTEL span capture pattern already present in
`tests/agents/test_cache_ttl_prefix_and_otel.py`; assert the cost/token attributes are
set. Do not regress existing `llm.*` attributes.

## Assumptions

- **`_watcher_publish_event` is the correct transport** — confirmed: already imported
  and used by the sibling cache event in the same file. If the GM panel expects a
  different `event_type` registration on the TS side, that surfaces as a non-blocking
  Delivery Finding, not a blocker for the backend emit.
- **Per-call (per-iteration) cadence is the intended reading of AC-3** — see AC-3 above.
  This is the load-bearing assumption; if wrong, it changes where the emit sits and the
  test count. Log a deviation if Dev/Reviewer overrides it.
- **The six-field contract is exhaustive** — the per-TTL 5m/1h split is intentionally
  excluded (the story names six fields; `cache_write_tokens` is the aggregate).
- **Test harness reuse** — the 61-4 / followup-D tests already build a fake
  raw-responses SDK client and a `publish_event` capture; RED tests should reuse that
  harness rather than inventing a new one (`tests/agents/test_61_4_cost_runaway_alarm.py`,
  `tests/agents/test_61_followup_D_session_cost_ceiling.py`).
