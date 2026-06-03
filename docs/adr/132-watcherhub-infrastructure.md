---
id: 132
title: "WatcherHub Infrastructure — builtins-Pinned Singleton, ContextVar Per-Session Isolation, and Ephemeral-Event Taxonomy"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [31, 90, 103]
tags: [observability]
implementation-status: live
implementation-pointer: null
---

# ADR-132: WatcherHub Infrastructure

> **Documents a system already live in code.** The process-level telemetry hub
> plumbing in `sidequest/telemetry/watcher_hub.py` — the `builtins`-pinned
> singleton, the dual process-global/`ContextVar` `TelemetrySink` binding, the
> explicit-`tx` in-frame/out-of-frame split, and the `_EPHEMERAL_EVENT_TYPES`
> load-shedding taxonomy — shipped incrementally across the 2026-04/05 OTEL
> restoration and persistence-substrate work (playtests 2026-04-23, 2026-04-29,
> perseus_cloud session 894, and the 2026-05-29 cross-session contamination fix)
> without a governing ADR. ADR-031 states the semantic *model*; this record
> closes the architecture-of-record gap for the *infrastructure* beneath it and
> states what the decision *was*.

## Context

ADR-031 (Game Watcher) defines the **three-layer semantic telemetry model** —
what events mean, the `TurnRecord` audit structure, the Layer-3 validator, and
the `/ws/watcher` endpoint contract. It is the canonical statement of *what is
observed and why*. It does not, however, specify the process-level pub/sub
*plumbing* that carries those events from arbitrary subsystem call sites to the
GM dashboard and into durable storage.

That plumbing is `WatcherHub` and the module-level `publish_event` entry point
(`sidequest/telemetry/watcher_hub.py`). It lives in `sidequest.telemetry`
rather than `sidequest.server` deliberately: subsystem code (orchestrator, game,
genre) must be able to publish semantic events without pulling FastAPI/uvicorn
into the import graph — importing `sidequest.server.watcher` would trigger
`sidequest.server.__init__` → `app.py` → `uvicorn`, and uvicorn reconfigures
logging handlers at import, breaking pytest's `caplog` fixture
(`watcher_hub.py`). The FastAPI-facing pieces (the `/ws/watcher` WebSocket
endpoint and the OTEL `WatcherSpanProcessor`) live in `sidequest.server.watcher`
and import *from* here.

Four hard infrastructure problems surfaced during operation that the semantic
model never addressed, each fixed in code and each now stated here as a
decision:

1. **Singleton survival across `uvicorn --reload`.** A naïve module-level
   `watcher_hub = WatcherHub()` creates a fresh instance on every reload,
   orphaning the OTEL span processors registered against the previous instance
   and turning the dashboard deaf once the first source-file save fires
   (`watcher_hub.py`, playtest 2026-04-23).
2. **Concurrent-session cross-attribution.** A single mutable process-global
   `TelemetrySink` meant that when two `/ws` sessions ran in one process, a
   trailing out-of-frame span from session A landed under session B's
   `session_id` because B was the last to bind the global
   (`watcher_hub.py`, 2026-05-29 contamination bug).
3. **In-frame vs out-of-frame persistence routing.** Whether a telemetry row
   should ride the open turn transaction (same connection) or open its own short
   transaction was originally *sniffed* from connection state — a now-deleted
   `conn.in_transaction` / `MAX(seq)` heuristic. Borrowing a second pooled
   connection (each `sink.record` / `append_encounter_event` takes the
   per-session `FOR UPDATE` row lock) while the turn transaction holds that lock
   on the same session self-deadlocks (`watcher_hub.py`).
4. **Write-amplification from ephemeral UI state.** Keystroke-level events
   (debounced composing state) were being event-sourced one Postgres INSERT per
   debounced keystroke — 30% of all telemetry rows in perseus_cloud session 894,
   with zero audience in solo play (`watcher_hub.py`).

## Decision

### 1 — `builtins`-pinned singleton (reload-survivable)

The hub is a single process-wide instance pinned to a `builtins` attribute
(`_BUILTINS_HUB_ATTR = "_sidequest_watcher_hub_singleton"`,
`watcher_hub.py`), not merely a module global. At import, the module checks
`builtins` for an existing hub and reuses it; only if absent does it construct a
new one and pin it (`watcher_hub.py`). FastAPI runs one app per process,
so one hub is correct by construction; pinning to `builtins` makes the *same*
instance survive `uvicorn --reload` re-imports of the module within the same
interpreter, so span processors registered against it stay live.

The identity check is **by-name, not `isinstance`**:
`type(_existing).__name__ == "WatcherHub"` (`watcher_hub.py`). After
`importlib.reload`, the post-reload `WatcherHub` class is a fresh object, so a
pre-reload instance fails `isinstance` against the new class even though its
interface is identical; `type(x).__name__` is stable across reloads
(`watcher_hub.py`).

### 2 — Dual `TelemetrySink` binding: process-global fallback + `ContextVar` (authoritative)

The out-of-frame `TelemetrySink` is bound in **two places at once**
(`watcher_hub.py`):

- `_telemetry_sink: TelemetrySink | None` — the process-global **fallback**, for
  contexts that never bound a per-task sink (process startup, REST tasks, tests
  that read without an asyncio task scope).
- `_session_telemetry_sink: ContextVar[TelemetrySink | None]` — the
  **authoritative** binding, scoped per asyncio task.

`bind_event_store` writes **both in lockstep** (`watcher_hub.py`): it
sets the global and calls `_session_telemetry_sink.set(...)`. Synchronous callers
and existing tests therefore see identical values; only interleaved asyncio
tasks diverge — which is exactly the isolation wanted. Each `/ws` connection runs
as its own asyncio Task with an isolated copied context, so a `bind_event_store`
call inside one connection's task sets *that* task's `ContextVar` without
disturbing a concurrently running session (`watcher_hub.py`).

Resolution for an out-of-frame write reads context-first, falling back to the
global: `_resolve_out_of_frame_sink()` returns the `ContextVar` value when present
(its default is `None`), else the process-global (`watcher_hub.py`). A
task that bound its own sink resolves it even after another task rebound the
global. This is the fix for the 2026-05-29 cross-session contamination
(`watcher_hub.py`).

### 3 — Explicit-`tx` in-frame/out-of-frame split (no connection-state sniffing)

`publish_event` takes an explicit `tx: SaveTransaction | None` (and
`event_seq: int | None`) parameter (`watcher_hub.py, 564-568`). The
persistence routing in `_persist_turn_telemetry` is decided **solely by that
parameter** (`watcher_hub.py`):

- `tx is not None` → `tx.write_telemetry(event_seq=event_seq, ...)` — the row
  rides the open turn transaction on the **same connection**, committing or
  rolling back atomically with the event (`watcher_hub.py`).
- `tx is None` → the resolved out-of-frame sink's `record(...)` opens its own
  short session transaction with a NULL `event_seq` (`watcher_hub.py`).
  If no sink is bound (legacy/in-memory session) this is a no-op — not an error,
  mirroring the historical `store is None` guard.

When `tx` is set the write goes **through** `tx`, never through the sink, so the
deadlock constraint (the sink's `record` would take the `FOR UPDATE` lock the
open turn already holds) cannot be violated (`watcher_hub.py`). This
**replaces a deleted heuristic**: the prior code sniffed `conn.in_transaction` /
`MAX(seq)` from connection state to guess in-frame vs out-of-frame
(`watcher_hub.py, 408-410`). That anti-pattern is gone — the caller
states intent explicitly.

The encounter-row path (`_maybe_persist_encounter_row`) is always out-of-frame:
encounter ops fire during resolution, *outside* the turn-tx block, so the sink's
own `session_tx` is correct and `tx` is deliberately **not** threaded into it
(`watcher_hub.py`).

### 4 — Ephemeral-event taxonomy (live-push only, never persisted)

`_EPHEMERAL_EVENT_TYPES: frozenset[str]` (`watcher_hub.py`, currently
`{"action_reveal.composing"}`) names event types that are **broadcast to the GM
panel but never written to `turn_telemetry`**. `_persist_turn_telemetry`
short-circuits on these before any DB work (`watcher_hub.py`). They carry
ephemeral UI/keystroke state with no forensic or mechanical value;
event-sourcing them is pure write-amplification.

The property is **intrinsic to the event TYPE** — it holds regardless of which
call site publishes it or whether a turn `tx` is open (Keith, 2026-05-29: "must
NOT be persisted in ANY mode") (`watcher_hub.py`). Discrete events with
diagnostic value (`action_reveal.submitted`) are deliberately *not* in the set
and keep persisting (`watcher_hub.py`). This is load-shedding by
taxonomy, not by sampling or backpressure.

## Invariants / Contracts

- **No cross-session attribution.** Out-of-frame telemetry resolves the
  `ContextVar`-bound sink for the publishing asyncio task; a concurrent session's
  rebind of the process-global never reattributes another task's rows
  (`watcher_hub.py`).
- **Never connection-state sniffing.** In-frame vs out-of-frame is decided only
  by the explicit `tx` parameter. The `conn.in_transaction` / `MAX(seq)`
  heuristic is deleted and must not return (`watcher_hub.py, 408-410`).
- **`tx` set ⇒ write through `tx`.** When a turn transaction is open the
  telemetry row rides it on the same connection; the hub never borrows a second
  pooled connection while `tx` is open (`watcher_hub.py, 444-452`).
- **Ephemeral = never persisted, in any mode.** Membership in
  `_EPHEMERAL_EVENT_TYPES` forbids a `turn_telemetry` row whether in-frame or
  out, while still allowing the live GM-panel push (`watcher_hub.py`).
- **One hub per interpreter, surviving reload.** The `builtins`-pinned instance
  is reused across module re-imports; span processors registered against it are
  never orphaned (`watcher_hub.py`).
- **Telemetry never crashes a turn.** Both persistence paths are fully wrapped:
  any failure loud-logs (`turn_telemetry.sink_failed` /
  `watcher_hub.encounter_row_failed`) and returns; it never raises, never stalls
  the turn, and never writes to a different store — a loud-logged drop, not a
  silent fallback (`watcher_hub.py, 464-471`). The live-push path is
  lossy by design: `publish` drops if no loop is bound or no subscribers, and
  `_broadcast` drops (loud-logged) a single unserializable event rather than
  evicting live subscribers (`watcher_hub.py, 144-189`).

## Consequences

**Positive**

- The dashboard stays live across `--reload` development cycles; no "the bridge
  silently went deaf after my last edit" failures.
- Two interleaved sessions in one process attribute their out-of-frame telemetry
  correctly — the 2026-05-29 contamination class is closed structurally.
- The in-frame/out-of-frame decision is explicit and greppable at the call site,
  not an opaque connection-state guess; the self-deadlock risk is eliminated by
  contract.
- Ephemeral keystroke state still reaches the live GM panel but stops dominating
  `turn_telemetry` (was 30% of rows in session 894), shedding write load without
  losing operator visibility.

**Negative / cost**

- Every persisting call site must thread `tx`/`event_seq` correctly — an
  in-frame event published with `tx=None` writes out-of-frame with a NULL
  `event_seq` (still correct, but loses the atomic tie to the turn event). The
  discipline is on the caller, not enforced by the hub.
- The dual binding means two pieces of state to keep in lockstep;
  `bind_event_store` must always write both, and a future direct write to either
  alone would reintroduce divergence.
- `_EPHEMERAL_EVENT_TYPES` is a hand-maintained taxonomy. Adding a new
  high-frequency event type without classifying it re-opens the
  write-amplification hole.
- Pinning to `builtins` is a deliberate global-namespace use; the by-name
  identity check is a subtlety any future maintainer touching the singleton must
  preserve.

## Alternatives considered

- **Plain module-global singleton (no `builtins` pin).** Rejected: a fresh
  instance on every `uvicorn --reload` orphans registered span processors and
  silences the dashboard (`watcher_hub.py, 248-253`). The `builtins`
  attribute is the only place that survives module re-import within one
  interpreter.
- **Explicit session threading of the sink through every publisher.** Rejected
  in favor of the `ContextVar`: threading a session-scoped sink argument through
  every subsystem call site that may publish a watcher event would touch the
  entire orchestrator/game/genre surface. The `ContextVar` achieves per-task
  isolation transparently — each `/ws` Task's copied context carries its own
  binding — while a process-global fallback still serves startup/REST/test
  contexts that have no task scope (`watcher_hub.py, 315-322`).
- **Connection-state sniffing for in-frame detection** (`conn.in_transaction` /
  `MAX(seq)`). Rejected and deleted: it was implicit, fragile, and risked
  self-deadlock by borrowing a second connection against an open turn lock. An
  explicit `tx` parameter is unambiguous and honors No Silent Fallbacks
  (`watcher_hub.py, 408-423`).
- **Sampling / backpressure to shed ephemeral load.** Rejected in favor of a
  type-keyed allowlist: the offending events have *no* forensic value at all, so
  dropping them entirely from persistence (while keeping the live push) is
  correct, rather than statistically thinning events that might have mattered
  (`watcher_hub.py`).

## Reconciliation with ADR-031 / ADR-090 / ADR-103

- **ADR-031 (Game Watcher — Semantic Telemetry):** governs the **model** — the
  three-layer taxonomy, the `intent_router.classify` / `agent.invoke` /
  `state.apply_patch` span vocabulary, the `TurnRecord` audit structure, the
  Layer-3 validator, and the `/ws/watcher` endpoint contract. It says nothing
  about how the hub survives reloads, isolates concurrent sessions, routes
  in-frame vs out-of-frame persistence, or sheds ephemeral load. This ADR adds
  exactly those four infrastructure decisions beneath ADR-031's model. The
  `publish_event(event_type, fields, ...)` signature here is the concrete
  emission path for ADR-031's semantic events (`watcher_hub.py`).
- **ADR-090 (OTEL Dashboard Restoration):** governs the post-port restoration of
  the dashboard and the "lossy by design" stance the hub's ring buffer and
  drop-on-no-loop behavior implement (`watcher_hub.py, 114-126`). This ADR
  documents the hub plumbing the restored dashboard subscribes to; it does not
  change the dashboard contract.
- **ADR-103 (Native OTEL via Tool Registry):** governs the OTEL tool-registry
  span layer. The hub's *optional* synthetic-span bridge
  (`SIDEQUEST_WATCHER_AS_SPANS=1` → `_emit_watcher_span`,
  `watcher_hub.py, 581-582`) mints a zero-duration OTEL span per
  semantic event so OTLP exporters (Jaeger) see the semantic stream alongside
  real spans; `WatcherSpanProcessor` recognizes the synthetic marker attribute
  and skips re-publishing them (`watcher_hub.py`). That bridge is the seam
  to ADR-103's layer — it is opt-in and additive, not the hub infrastructure
  this ADR governs.
