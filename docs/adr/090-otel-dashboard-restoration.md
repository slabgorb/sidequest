---
id: 90
title: "OTEL Dashboard Restoration after Python Port"
status: accepted
date: 2026-04-25
deciders: ["Keith Avery"]
supersedes: []
superseded-by: null
related: [31, 58, 82]
tags: [observability, project-lifecycle]
implementation-status: live
implementation-pointer: null
---

# ADR-090: OTEL Dashboard Restoration after Python Port

## Status

**Accepted** — 2026-04-25.

## Context

After the Rust → Python port (ADR-082), the OTEL dashboard at `/ws/watcher`
and the React `Dashboard/` panes degraded materially. The CLAUDE.md
"OTEL Observability Principle" was no longer enforced: the GM panel — the
"lie detector" Sebastien-the-mechanics-first-player and Keith-the-builder
both depend on — surfaced almost no live signal.

A forensic audit found four failures:

1. The `just otel` recipe pointed at a deleted `playtest.py`.
2. Most `WatcherEventType` values declared in `watcher.ts` had zero or one
   emission sites in production code.
3. ~80% of `SPAN_*` constants in `telemetry/spans.py` were transcribed from
   Rust but never re-implanted into Python dispatch — the catalog was
   aspirational.
4. The translator (`WatcherSpanProcessor.on_end`) flattened every span to
   `agent_span_close` with no semantic typed-event routing.

The Python port copied the **vocabulary** and **transport** but not the
**emission discipline** or the **Layer-3 narrative validator**.

## Decision

Restore the dashboard to ADR-031's three-layer semantic-telemetry contract,
faithfully ported to Python, with three deliberate departures:

1. **`TurnRecord` shape.** Store `snapshot_before_hash + snapshot_after +
   StateDelta` rather than two full `GameSnapshot` clones. Same validation
   power, no double-clone cost.
2. **Validator transport.** `asyncio.Queue(maxsize=32)` with oldest-record
   drop on backpressure (faithful to ADR-031's "lossy by design" intent).
3. **Console exporter gating.** `ConsoleSpanExporter` defaults off; gated
   behind `SIDEQUEST_OTEL_CONSOLE=1` for debug.

The translator gains a routing table (`SPAN_ROUTES`) colocated with span
constants in `spans.py` so renaming a constant breaks the route at import
and a new constant without a routing decision trips the
`test_routing_completeness.py` lint.

A new `Validator` task consumes `TurnRecord`s and runs five deterministic
checks: entity, inventory, patch-legality, trope-alignment,
subsystem-exercise. The validator owns `turn_complete`, `coverage_gap`,
and `validation_warning`.

## Consequences

### Positive

- Every `WatcherEventType` declared in `watcher.ts` has a clear owner;
  no orphans, no double-emission.
- Adding a new span constant requires an explicit routing decision —
  catches the regression that caused this work.
- The "lie detector" property is restored: subsystem activity surfaces
  on the dashboard whether or not the LLM mentions it.
- `just otel` is CI-protected against future script renames.

### Negative

- ~24 emission families still need re-implanting (Phase 2 follow-up
  plans, one per family). The infrastructure now in place makes each
  rollout a small, repeatable change.
- Validator runs on the same event loop as dispatch. Bounded queue +
  lossy drop policy keeps it from impacting hot-path latency, but heavy
  check overhead would still serialize behind dispatch. Acceptable for
  current playtest scale (≤5 watchers, ≤1 turn/sec).

### Out of scope

- No `TurnRecord` persistence / replay.
- No second-LLM validation (ADR-031's "God lifting rocks" prohibition).
- No HTTP OTLP receiver. In-process span processor remains.

## Implementation

See `docs/superpowers/specs/2026-04-25-otel-dashboard-restoration-design.md`
for the design and `docs/superpowers/plans/2026-04-25-otel-dashboard-restoration.md`
for the task plan.

## Amendment (2026-05-31): Validator Concurrency Model + PhaseTimings Accumulator

The original ADR **named** the `Validator`, its five checks, and the
`asyncio.Queue(maxsize=32)` / drop-oldest transport, but deferred the
architectural rationale ("Acceptable for current playtest scale (≤5
watchers, ≤1 turn/sec)" — Consequences › Negative). This amendment makes
the **concurrency model**, the **check-registration pattern**, and the
**`PhaseTimings` passive-accumulator + NULL-sentinel** design load-bearing
decisions rather than incidental implementation. No behavior changes — this
records what shipped.

### Validator concurrency model

`Validator` (`sidequest/telemetry/validator.py`) is a **single-consumer**
pipeline. A lone `asyncio.Task` (`sidequest.validator`, created in
`start()` at `validator.py`) pulls one `TurnRecord` at a time off a
bounded `asyncio.Queue(maxsize=32)` (`validator.py`) and runs the
registered checks serially in `_validate` (`validator.py`,
check loop at `validator.py`).

Load-bearing assumptions, now governed:

- **Same event loop as dispatch.** The queue and task live on the dispatch
  event loop — there is no thread or process boundary. The consequence is
  explicit: a **slow check serializes behind dispatch**. The checks are
  therefore kept cheap (regex scans, set membership, dict lookups — see
  `entity_check` at `validator.py`, `inventory_check` at `:107`,
  `patch_legality_check` at `:169`, `trope_alignment_check` at `:263`,
  `subsystem_exercise_check` at `:308`). This is acceptable **only** at the
  stated scale (≤5 watchers, ≤1 turn/sec). Crossing that scale is the
  trigger to revisit (move the consumer off-loop, e.g. a thread/queue
  handoff), not to silently absorb latency.
- **Bounded at 32 / drop-oldest.** `maxsize=32` is a deliberate small bound:
  at ≤1 turn/sec the consumer never falls 32 turns behind in healthy
  operation, so a full queue is itself a signal of pathology, not normal
  load. On `QueueFull`, `submit()` (`validator.py`) **drops the
  oldest record** (`get_nowait()` + `task_done()`), increments
  `dropped_records`, fires a `validation_warning` (`check=validator.queue`,
  `reason=queue_full`), then enqueues the new record. Drop-**oldest** (not
  drop-newest) is faithful to ADR-031's "lossy by design": validation is a
  *liveness* signal, so the freshest turn is the most diagnostically
  valuable — stale turns are the ones worth shedding.
- **Never raises into the dispatch hot path.** Each check runs inside
  try/except in `_validate` (`validator.py`); a check exception
  fires a `validation_warning` with `severity=error` and is logged, but the
  validator task keeps running and dispatch is never disturbed. The module
  docstring states this contract (`validator.py`).
- **Imperative `register_check` registration.** Checks are registered by
  appending to `self._checks` via `register_check` (`validator.py`),
  called five times in `__init__` (`validator.py`). This is a
  deliberate imperative list rather than a decorator registry — order is
  the construction order, the set is closed at construction, and tests can
  register additional checks on an instance. `turn_complete` is emitted
  unconditionally ahead of the checks (`validator.py`), so it is
  not itself a registered check.
- **Heartbeat liveness.** A second task (`sidequest.validator.heartbeat`,
  `validator.py`) emits a `state_transition` event
  (`field=validator.heartbeat`) every 30s (`validator.py`) carrying
  `queue_depth`, `queue_max`, `dropped_records`, and p50/p99 check
  durations. This is how the GM panel distinguishes "validator idle" from
  "validator dead/wedged" — without it, a silent queue and a hung consumer
  look identical.

### PhaseTimings passive accumulator + NULL sentinel

`PhaseTimings` (`sidequest/telemetry/phase_timing.py`) is the per-turn
**additive wall-clock accumulator** that rides on `TurnContext`. Its design
is now governed:

- **Passive accumulator — never interprets.** Per the module docstring
  (`phase_timing.py`), the class "does not interpret, threshold, log, or
  alert. All semantic decisions live downstream (validator, panel)." It
  records elapsed-ms per named phase (`phase()` context manager,
  `phase_timing.py`; out-of-band `record_phase`, `:46-60`), accumulates
  **repeated phase names additively** (`:43`, `:59`), and counts calls.
  `mark_done()` (`:62`) finalizes; reads before finalize raise (`:70-74`).
  This is what lets it ride `turn_complete` as a **flame-chart input** — the
  `phase_durations_ms` dict becomes the one-bar-per-phase `spans` array in
  `_validate` (`validator.py`, emitted at `:502`), laid out
  monotonically in observed insertion order so the bars match pipeline
  sequence. Keeping the accumulator dumb means the timeline reflects *what
  happened*, with all thresholding deferred to the consumer.
- **`_NullPhaseTimings` NULL sentinel — not None-checks.** `PhaseTimings.NULL`
  (`phase_timing.py`) is a no-op singleton (`_NullPhaseTimings`,
  `:90-125`) used by fixtures and partial mocks. It is a true Null-Object:
  call sites use `PhaseTimings.NULL` and call `.phase(...)` / `.record_phase(...)`
  / `.mark_done()` unconditionally rather than guarding with `if timings is
  not None`. Its `__init__` deliberately **does not** call
  `super().__init__` (`:99-104`) — this avoids the unused `time.monotonic()`
  syscall at import and decouples the sentinel from parent internals so a
  future `PhaseTimings.__init__` refactor cannot silently leak live
  monotonic time into the singleton's reads. `total_ms`/`unaccounted_ms`
  return `0` and `to_dict()` returns `{}` (`:116-125`), so a NULL-timed turn
  degrades to a single fallback `agent_llm` bar in the timeline
  (`validator.py`) rather than an empty/erroring flame chart.

### Summary of what this amendment governs

ADR-090 named the `Validator` and stated its purpose; this amendment governs
(1) the **concurrency model** — single bounded `asyncio.Queue(maxsize=32)`,
same event loop as dispatch, drop-oldest on backpressure, never-raise into
the hot path, with heartbeat liveness; (2) the imperative **`register_check`
registration pattern** (closed-at-construction ordered list, not a
decorator registry); and (3) the **`PhaseTimings` passive-accumulator +
`_NullPhaseTimings` NULL-sentinel** design (additive, never-interpreting,
flame-chart input via `turn_complete`).

## Related

- ADR-031: Game Watcher — Semantic Telemetry (this ADR ports it to Python)
- ADR-058: Claude subprocess OTEL passthrough (unchanged)
- ADR-082: Port `sidequest-api` from Rust back to Python (this ADR closes one of its drift items)
