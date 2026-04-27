---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-31: Daemon worker heartbeat + render-unavailable degradation

## Business Context

**Playtest 3 evidence (2026-04-19, Felix solo).** The last successful
render landed at 14:43 EDT. The session continued playing until 14:56
EDT — thirteen minutes that produced *zero* renders for turns that, under
the policy contract being introduced in story 45-30, should have fired on
beat changes, named-NPC reveals, and at least one resolved encounter.

The post-mortem failure was not the missing renders themselves — those
will recur for genuine reasons (GPU under load, model swap, MPS OOM,
unrelated daemon crash). The post-mortem failure was that **we cannot
tell from the save file or from the OTEL stream** whether each missing
render was:

- never requested (server policy rejected it — covered by 45-30),
- requested but enqueue path silently dropped it (no instrumentation
  exists today for queue depth or backpressure),
- requested, accepted, but the daemon hung mid-render (no heartbeat — the
  server's only signal is the per-call socket timeout in
  `daemon_client/client.py:204–217`, which fires *after* the entire 180-second
  ceiling),
- or completed but failed to deliver (these *do* emit
  `field=render, op=failed` watcher events at
  `session_handler.py:4665–4715`).

Without a continuous daemon liveness signal, the four cases collapse into
"silence," which is the exact bug CLAUDE.md "No Silent Fallbacks" exists to
prevent. ADR-006 (Graceful Degradation) is the design principle this story
implements: when an optional sidecar is unhealthy, the system MUST surface
that degradation to the player (and the GM panel), not silently absorb it.

**Audience:**
- Sebastien (mechanical-first) needs the heartbeat in the OTEL stream so
  the GM panel reports `daemon=ready/busy/paused` continuously, not only on
  request edges.
- Operations / dev (Keith, post-session) needs a worker-state log written at
  session end so a 13-minute silence in the next playtest can be diagnosed
  without reproducing the crash.
- Players (Felix in the playtest evidence, James in narrative continuity)
  need a *visible* "render unavailable" marker in the scrapbook row when
  the policy fired but the daemon couldn't service the request — not a
  silent gap that looks like a banter turn.

**Load-bearing references:**

- ADR-006 (Graceful Degradation) — the design contract this story
  implements; load-bearing.
- ADR-035 (Unix Socket IPC for Python Sidecar) — defines the JSON-RPC
  framing the heartbeat extends. The heartbeat is a daemon-initiated
  status event, not a new method, so the protocol surface stays
  per-connection request/response with the new `event` line a documented
  addition to ADR-035.
- ADR-046 (GPU Memory Budget Coordinator) — informs the `paused` state
  semantics: the daemon may pause its render queue under MPS pressure and
  must announce the pause.
- ADR-031 (Game Watcher) — heartbeat events flow into the watcher stream
  the GM panel already consumes.
- ADR-050 (Image Pacing Throttle) — orthogonal; throttle is server-side
  cooldown, heartbeat is daemon-side liveness. Both feed the same
  decision but neither replaces the other.
- CLAUDE.md "No Silent Fallbacks" — load-bearing; the 13-minute silence is
  the precise scenario this principle exists to forbid.
- CLAUDE.md OTEL Observability Principle — gate-blocking.

The story is 5 points because it crosses both repos
(`sidequest-server` and `sidequest-daemon`) and threads four sub-fixes (a/b/c/d)
through one IPC seam.

## Technical Guardrails

### Cross-repo IPC seam (load-bearing)

The heartbeat is a *daemon → server* event over the existing Unix socket.
Today every connection is request/response (server opens a socket per call
in `DaemonClient._call`, `daemon_client/client.py:188–260`). Heartbeats
need a different shape: the daemon must be able to publish its state
continuously without a live request. Two options the implementation may
choose between (architect leaves this to the test engineer to confirm
matches the existing socket framing):

1. **Per-connection event line** — when the server opens a daemon connection
   for any method (`render`, `embed`, future), the daemon writes a status
   event line *before* the response line. The server reader parses any
   pre-result events, threads them through the watcher, and continues to
   the result line. This stays within ADR-035 (line-framed JSON, single
   socket).
2. **Dedicated long-lived heartbeat socket** — server opens a side
   connection at startup that only receives heartbeat events. Heavier;
   prefer option 1 unless the framing forces it.

Either way: heartbeat events are tagged JSON lines distinguishable by an
`event` key (vs. `result`/`error`). The server's `daemon_client.client._call`
loop at `client.py:219–254` is the seam the heartbeat reader extends.

### Outermost reachable layers (wire-first seams)

1. **Daemon emit seam** — `_handle_client()` and the `WorkerPool` in
   `sidequest-daemon/sidequest_daemon/media/daemon.py:259–605`. Heartbeats
   must emit:
   - on the connection-accept path (`client.py:259–268`, status: `ready`),
   - on render-lock acquisition (`daemon.py:489`, status: `busy`),
   - on render-lock release (after `daemon.py:491–510`, status: `ready`),
   - on a paused-state transition driven by the future GPU coordinator
     (ADR-046 — out of scope to *implement* the pause, in scope to *emit*
     `paused` if the coordinator flips a flag the daemon already exposes;
     today there is no such flag, so the `paused` emit site is the
     placeholder hook tied to a daemon-internal queue gate that the GPU
     coordinator will set in a follow-up).
   - **Periodic** ready emit at a configured interval (default 30s) when
     no work is in flight, so a silent socket distinguishes from a wedged
     daemon. Implement on the same asyncio loop that runs the server in
     `_run_daemon` (`daemon.py:715–746`).

2. **Server enqueue seam (backpressure + threshold)** —
   `_maybe_dispatch_render()` in
   `sidequest-server/sidequest/server/session_handler.py:4170–4290`. Today
   the gate at line 4218 is binary (`client.is_available()` checks socket
   existence on disk). Add:
   - a server-held `daemon_state: DaemonState` enum
     (`READY`/`BUSY`/`PAUSED`/`UNRESPONSIVE`) updated by the heartbeat
     reader,
   - a queue-depth counter incremented at enqueue, decremented on reply
     (success or error), held on `_SessionData` alongside the existing
     `image_pacing_throttle`,
   - a configurable threshold (default 3 in-flight) above which enqueue
     emits a loud warn + a `render.enqueue.backpressure` watcher event.
     The trigger policy (45-30) still chose to render; backpressure is
     the orthogonal "the daemon can't service this right now" path.
3. **Server graceful-degradation seam** — same `_maybe_dispatch_render()`.
   When `daemon_state == UNRESPONSIVE` (no heartbeat seen for >2x the
   configured interval), the server MUST:
   - skip the daemon round-trip,
   - emit `render.unavailable` watcher event,
   - hand off to the scrapbook emitter with `render_status="unavailable"`
     (a fourth value on the discriminator that 45-30 introduces; if 45-30
     has not yet landed, this story owns the discriminator). The
     scrapbook row is the user-facing "render unavailable" marker.
4. **Post-session diagnostic log** — at session end (the same teardown
   point referenced at `session_handler.py:1105`), write a
   worker-state JSON snapshot to a known location
   (`~/.sidequest/diagnostics/render-{room_slug}-{session_end_iso}.json`).
   The snapshot includes: heartbeat history (last N states with
   timestamps), enqueue/backpressure counts, last seen daemon socket
   path, last successful render id and timestamp, and any
   `UNRESPONSIVE` windows observed. Format is JSON so the file is
   greppable in post-mortem.

### Daemon state machine (NEW)

In `sidequest-daemon/sidequest_daemon/media/daemon.py`, model the worker
state explicitly. Reuse: `WorkerPool.status()` at line 235 already returns
`{"image": "warm"|"cold", ...}`. Extend with a `state: str` field driven
by the render lock (`render_lock.locked()` at line 489) and the embed lock.
Per-queue (image, embed) emission lets the heartbeat distinguish a busy
render from a busy embed.

```python
class WorkerState(StrEnum):
    READY    = "ready"     # warm, no work in flight
    BUSY     = "busy"      # render_lock acquired (or embed_lock for embed queue)
    PAUSED   = "paused"    # GPU coordinator gated the queue (ADR-046 hook)
    COLD     = "cold"      # not warmed yet — not the same as paused
```

Heartbeat payload:
```json
{"event": "heartbeat", "queue": "image", "state": "ready",
 "queue_depth": 0, "ts_monotonic": 1234.5}
```

### Server-side daemon state mirror (NEW)

In `sidequest/daemon_client/client.py`, add a `DaemonStateMirror`
singleton (or per-`DaemonClient` instance) that the heartbeat reader
populates. The mirror is what `_maybe_dispatch_render()` consults instead
of (or in addition to) `client.is_available()` at
`session_handler.py:4218`. Threading: the heartbeat must be parsed on the
same asyncio loop that owns the WebSocket session, so a single shared
client + reader task at server startup is the safe shape.

Today `DaemonClient` opens a fresh connection per request. Adding a
long-lived heartbeat reader is the structural change; the per-request
connections continue to coexist for `render`/`embed` so the existing
fault-isolation property (`client.py:1–14` docstring) survives.

### OTEL spans (LOAD-BEARING)

Define in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES` entries.
On the daemon side, define in
`sidequest-daemon/sidequest_daemon/media/daemon.py` (the daemon already
holds its own tracer at line 76).

| Span / event | Attributes | Site (file:line) |
|------|------------|------|
| `daemon.heartbeat` | `queue` (`image`/`embed`), `state` (`ready`/`busy`/`paused`/`cold`), `queue_depth` (int), `ts_monotonic` (float) | daemon emit at `daemon.py:_handle_client` accept (line 268), pre-/post- `render_lock` (lines 489, 510), pre-/post- `embed_lock` (lines 543, 588), and on the periodic timer in `_run_daemon` (lines 730–746). Server-side mirror re-publishes through the watcher with `component="daemon"`. |
| `render.enqueue.backpressure` | `queue_depth`, `threshold`, `turn_number`, `player_id`, `decision` (`warn`/`reject`) | server enqueue at `session_handler.py:4218` (new branch above the daemon-availability check). `warn` lets the request through and logs loud; `reject` short-circuits and triggers the unavailable fallback. |
| `render.unavailable` | `reason` (`heartbeat_lost`/`backpressure_reject`/`socket_missing`), `last_heartbeat_ts`, `turn_number`, `player_id` | server fallback site, replaces the silent miss path. Fired alongside the scrapbook emit so the GM panel sees the substitution. |
| `daemon.session_diagnostic_written` | `path`, `heartbeat_count`, `unresponsive_window_count`, `room_slug` | post-session log writer at the session-end teardown. Fires once. |

The existing `field=render, op=failed` / `op=throttle_decision` /
`op=dispatched` watcher events remain unchanged — heartbeat is additive.

### Reuse, don't reinvent

- `DaemonClient` (`daemon_client/client.py:75`) is the single client class;
  do not create a parallel heartbeat client. Add a `heartbeat_listener()`
  coroutine to it.
- `DaemonUnavailableError` (`client.py:61`) is the existing terminal
  failure type; the unresponsive path raises this so callers downstream of
  `client.render()` keep working.
- `WorkerPool.status()` (`daemon.py:235`) already projects pool health;
  extend the dict, do not parallel it.
- `_watcher_publish` (`session_handler.py`) is the single watcher path; emit
  through it.
- The scrapbook `render_status` field is shared with story 45-30. If
  45-30 lands first, this story extends the enum with `"unavailable"`; if
  this story lands first, it owns the field.
- Diagnostics directory: `~/.sidequest/diagnostics/` is a new sibling to
  the existing save directory at `~/.sidequest/saves/` (referenced in
  CLAUDE.md). Use `pathlib.Path.home() / ".sidequest" / "diagnostics"`;
  `mkdir(parents=True, exist_ok=True)` at write time.

### Test files (where new tests should land)

Server side:
- New: `tests/server/test_daemon_state_mirror.py` — unit tests for
  `DaemonStateMirror` state transitions on heartbeat events.
- New: `tests/server/test_render_backpressure.py` — wire-first boundary
  test: drive a sequence of enqueue calls past the threshold; assert
  `render.enqueue.backpressure` watcher event with `decision="warn"`.
- New: `tests/server/test_render_unavailable_fallback.py` — wire-first:
  a fixture stops the daemon (or never starts the heartbeat reader);
  drive `_maybe_dispatch_render()`; assert `render.unavailable` event,
  scrapbook row with `render_status="unavailable"`, and no daemon
  round-trip attempted.
- New: `tests/server/test_post_session_diagnostic.py` — end-to-end:
  run a short session, trigger a heartbeat-lost window, end the
  session, assert the diagnostic JSON is written with the expected
  fields.

Daemon side:
- New: `sidequest-daemon/tests/test_heartbeat_emit.py` — drive a render,
  capture emitted events on a fake stream writer, assert
  `ready → busy → ready` sequence and the periodic emit.
- Extend: `sidequest-daemon/tests/test_daemon_protocol.py` (or whichever
  IPC test exists) — assert heartbeat lines coexist with the per-request
  result line and don't break existing clients.

## Scope Boundaries

**In scope:**

- Daemon-side `WorkerState` enum, per-queue heartbeat emit, periodic
  emit at configurable interval (default 30s).
- Server-side `DaemonStateMirror`, heartbeat reader threaded into
  `DaemonClient`.
- Backpressure threshold + `render.enqueue.backpressure` event at the
  enqueue path.
- Graceful degradation: `UNRESPONSIVE` daemon → skip dispatch, emit
  `render.unavailable`, scrapbook row with `render_status="unavailable"`.
- Post-session diagnostic JSON written to
  `~/.sidequest/diagnostics/render-{room_slug}-{session_end_iso}.json`.
- OTEL spans `daemon.heartbeat`, `render.enqueue.backpressure`,
  `render.unavailable`, `daemon.session_diagnostic_written`. Register
  all in `SPAN_ROUTES`.
- Wire-first boundary tests on both repos exercising the IPC seam.

**Out of scope:**

- Daemon restart automation. If the heartbeat is lost the system
  surfaces the degradation; recovery is manual (`just daemon` /
  `just daemon-stop`).
- Queue resizing, render-lock priority, or fairness between embed and
  render workers.
- GPU recovery / MPS cache release on `paused`. ADR-046 owns the GPU
  coordinator; this story emits `paused` if a flag exists, no more.
- Backpressure-driven dropping of low-priority renders (the threshold
  emits a warn; rejection-mode is implemented but the threshold for
  `decision="reject"` is conservative and tunable, not a feature this
  story exercises in playtest).
- Retroactive scrapbook updates from late-arriving daemon failures
  (today's fire-and-forget pattern is preserved).
- Migrating diagnostics files into the save DB. JSON-on-disk is the
  v1 surface; a follow-up may absorb it into the events journal.

## AC Context

1. **Daemon emits heartbeat on render-lock acquisition and release.**
   - Test (daemon side, isolated): drive a render call against a fake
     pipeline that blocks; capture the per-connection event lines.
     Assert sequence `heartbeat(state="ready") → heartbeat(state="busy")
     → heartbeat(state="ready")` with `queue="image"` on each, and the
     `queue_depth` reflects the in-flight count.
   - Negative: an embed call MUST NOT emit a `queue="image"` busy
     heartbeat (the locks are independent per ADR-035 + 37-23).

2. **Daemon emits periodic ready heartbeat when idle.**
   - Test: with the daemon idle, advance the asyncio clock by the
     configured interval (default 30s) twice; assert two `state="ready"`
     heartbeats published, each with `queue_depth=0`.

3. **Server enqueue emits backpressure event past threshold.**
   - Wire-first test: simulate three concurrent in-flight renders
     (depth=3, default threshold). Drive a fourth enqueue. Assert:
     - the fourth call still proceeds (warn mode, not reject),
     - `render.enqueue.backpressure` watcher event fires with
       `decision="warn"`, `queue_depth=4`, `threshold=3`,
     - the warning is logged via the standard logger.

4. **Unresponsive daemon → scrapbook row carries `render_status="unavailable"`.**
   - Wire-first test (the Felix scenario): start a session, take one
     successful render, then kill the daemon (or let the heartbeat
     fixture stop emitting). After the lost-heartbeat window
     (`> 2 × interval`), drive a turn that the trigger policy from
     45-30 marks as eligible (e.g., a beat fire). Assert:
     - no daemon socket round-trip is attempted,
     - `render.unavailable` event fires with
       `reason="heartbeat_lost"` and a non-null `last_heartbeat_ts`,
     - the scrapbook row is persisted with
       `render_status="unavailable"`,
     - `_watcher_publish(field=render, op=...)` carries the
       degradation, not silence.
   - This is the explicit anti-Felix-13-minutes-of-silence test. It
     MUST drive the WS-narration → policy → enqueue path end to end,
     not unit-test the mirror.

5. **Post-session diagnostic file written to known location.**
   - Test: complete a short session that includes one normal render,
     one backpressure-warn enqueue, and one unresponsive window.
     Trigger session-end teardown. Assert a file at
     `~/.sidequest/diagnostics/render-{room_slug}-{iso}.json` exists
     with: `heartbeat_history` (non-empty list), `enqueue_count`,
     `backpressure_warn_count` (>=1), `unresponsive_windows`
     (one entry with start/end timestamps), `last_successful_render_id`,
     `last_successful_render_ts`. Assert
     `daemon.session_diagnostic_written` watcher event fires once.

6. **Heartbeat reader does not break existing per-request flows.**
   - Regression test: with the heartbeat reader running, drive ten
     normal `render()` calls. Assert all ten complete normally, the
     `daemon_client.request` span at `client.py:190` continues to
     fire per call, and no per-request line is mis-parsed as a
     heartbeat.
