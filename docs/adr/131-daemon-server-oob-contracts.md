---
id: 131
title: "Daemon↔Server Out-of-Band Contracts — Liveness Heartbeat, OTEL HTTP Bridge, Output-Dir Handshake, R2 Artifact Layout"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [35, 95, 103]
tags: [transport-infrastructure, observability]
implementation-status: live
implementation-pointer: null
---

# ADR-131: Daemon↔Server Out-of-Band Contracts

> **Documents a family of cross-process contracts already live in code.** The
> liveness heartbeat stream, the daemon→server OTEL HTTP bridge, the output-dir
> handshake file, and the R2 artifact-key layout all shipped incrementally
> across the 2026-04 / 2026-05 work (stories 45-31, 37-23, the music tier of
> ADR-095, and a string of playtest P1 fixes) **without a governing ADR**. ADR-035
> defines the Unix-socket JSON-RPC transport and is silent on every one of these.
> This record closes that architecture-of-record gap and states what each
> decision *was* and *why*.

## Context

ADR-035 established a single channel between `sidequest-server` and
`sidequest-daemon`: newline-delimited JSON-RPC over a Unix domain socket at
`/tmp/sidequest-renderer.sock`, one connection per request, daemon as an
*optional* sidecar. That channel is purely request/response: the server asks for
a render or an embed, the daemon answers or the call fails with a structured
`DaemonUnavailableError` (`sidequest-server/sidequest/daemon_client/client.py`).

That single channel turned out to be insufficient for four distinct problems,
each solved out-of-band — *on top of*, not *through*, the JSON-RPC request path:

1. **Liveness.** The original liveness signal was the binary "does the socket
   file exist on disk?" check (`client.py` `is_available`). That check passed
   the entire time the daemon hung mid-render during the **2026-04-19 playtest:
   the daemon went silent for ~13 minutes**, the server kept dispatching into a
   dead socket, and players saw neither images nor an error. A socket that exists
   but never answers is indistinguishable from a healthy one under an
   exists-on-disk probe. We needed a *continuous* liveness signal, not a presence
   bit. (This is the "Felix anti-13-minute-silence" contract referenced
   throughout `state_mirror.py`.)
2. **Telemetry.** The watcher hub (the GM-panel lie detector, ADR-031 / ADR-090)
   lives in the *server* process. The daemon physically cannot import it across
   the process boundary, yet daemon-side subsystems (prompt composition, music
   pipeline, render dispatch) make decisions that the OTEL principle says **must**
   be observable. The daemon needed a way to emit watcher events into the
   server's hub without coupling the two processes' memory.
3. **Output-dir discovery.** When run with no `SIDEQUEST_OUTPUT_DIR`, the daemon
   picks a random `tempfile.mkdtemp(prefix="sq-daemon-")` directory
   (`daemon.py`). The server has no way to know that path, so its
   `/renders/*` static mount never gets created and every image 404s even though
   the PNG was written correctly. This was the **2026-04-25 P1 regression**.
4. **Durable artifact storage.** Renders and music land in R2, and the key layout
   matters: session-scoped ephemeral art has different lifecycle and addressing
   needs than durable, hand-authored pack assets. An ad-hoc key scheme would have
   crossed those two lifecycles and made cleanup unsafe.

These were built piecemeal as the failures surfaced. None is governed by an ADR.
ADR-095 *names* `watcher_bridge.py` and `r2_writer.py` as files the music tier
uses, but does not govern their contracts. ADR-103 governs *server-side* native
OTEL via the tool registry — not the daemon bridge. This ADR is the missing
record.

## Decision

**Four cross-process contracts are layered on top of the ADR-035 socket
transport, plus one related concurrency decision about the daemon's internal
locks. Each is stated below as a named, durable contract.**

### Contract 1 — Liveness heartbeat stream

The daemon emits a heartbeat event on every connection-state transition; the
server maintains a per-queue mirror keyed on its *own* receive clock.

- **Daemon side** (`sidequest-daemon/sidequest_daemon/media/daemon.py`): a
  `WorkerState` enum (`daemon.py` — `READY`/`BUSY`/`PAUSED`/`COLD`) and a
  heartbeat payload `{"event":"heartbeat","queue","state","queue_depth",
  "ts_monotonic"}` built by `_make_heartbeat` (`daemon.py`) and written
  inline by `_write_heartbeat` (`daemon.py`). Heartbeats fire at six
  per-connection sites: accept (×2 queues, `daemon.py`), render-lock
  acquire/release (`daemon.py`, `:932`), and embed-lock acquire/release
  (`daemon.py`, `:1029`). The `queue_depth` field is fed from
  `_IN_FLIGHT_COUNTS` (`daemon.py`), a per-queue (`image`/`embed`)
  backpressure counter the daemon owns, so the server sees concurrent load even
  on a connection that has no work of its own in flight. A daemon-driven *periodic*
  idle emitter was deferred and the unwired `start_periodic_heartbeat` scaffold was
  **cut in story 78-3 (2026-06-03)** — see Consequences; fresh heartbeats come
  only from per-request connections and the server's reconnecting listener.
- **Server side** (`sidequest-server/sidequest/daemon_client/state_mirror.py`):
  `DaemonStateMirror` holds per-queue `DaemonState` and `queue_depth`. The mirror
  is consumed via the process-wide singleton `get_mirror()` (`state_mirror.py`),
  pinned to a `builtins` attribute (`state_mirror.py`, `:221-225`) so it
  survives `uvicorn --reload` re-imports — the same pattern `watcher_hub` uses.
  `DaemonClient.heartbeat_listener` (`client.py`) is wired into the FastAPI
  startup hook, opens a connection, sends a throwaway `status` request to keep it
  open, and drains heartbeat lines into the mirror; it reconnects on a ~15s idle
  window — 4× faster than the 60s unresponsive threshold. Per-request `_call`
  also drains heartbeats off the wire (`client.py`).

### Contract 2 — OTEL HTTP bridge (daemon → server hub)

`sidequest-daemon/sidequest_daemon/telemetry/watcher_bridge.py` —
`emit_watcher_event(event_type, fields, *, component="daemon")` POSTs a JSON body
to the server's `/internal/watcher/emit` endpoint
(`watcher_bridge.py`). The endpoint (`sidequest-server/sidequest/server/
app.py`) forwards the payload to `publish_event` on the in-process hub. The
transport is stdlib `urllib.request` (`watcher_bridge.py`), **not**
`requests` — neither process carries `requests` as a runtime dep, and a
fire-and-forget telemetry POST does not justify adding one. The call has a **2s
timeout** (`_TIMEOUT_SECONDS = 2.0`, `watcher_bridge.py`) and is **fire-and-
forget**: any `URLError`/`ConnectionError`/`OSError`/`TimeoutError` is logged at
`WARNING` and swallowed (`watcher_bridge.py`) — telemetry must never break a
render. The server base URL is `http://127.0.0.1:8765`, overridable via
`SIDEQUEST_SERVER_URL` (`watcher_bridge.py`, `:33-34`). Live consumers:
`prompt_composer.py`, `pipeline_factory.py`, `daemon.py`.

### Contract 3 — Output-dir handshake file

`_run_daemon` resolves its output directory (env `SIDEQUEST_OUTPUT_DIR` or a
random tmpdir) and **publishes the resolved absolute path** to a known location:
`~/.sidequest/daemon-output-dir` (`daemon.py`). The write is **one-way
publish** and **non-fatal** — an `OSError` is logged and the daemon continues
(`daemon.py`). The server reads this file when constructing its
`/renders/*` static mount, with explicit precedence: (1) `SIDEQUEST_OUTPUT_DIR`
env, (2) the handshake file, (3) no mount + loud log
(`app.py`). On a successful handshake read the server propagates the value
back into its own env so the per-render `_render_url_from_path` sees the same
root. This is the fix for the 2026-04-25 P1 404 regression.

### Contract 4 — R2 artifact-key layout

`sidequest-daemon/sidequest_daemon/media/r2_writer.py` defines two distinct,
non-overlapping namespaces in the `sidequest` bucket (`BUCKET`, `r2_writer.py`):

- **`upload_artifact`** (`r2_writer.py`) — **session-scoped, content-addressed**
  ephemeral output. Key shape:
  `artifacts/<world_slug>/<session_id>/<kind>/<sha256>.<ext>` (`r2_writer.py`),
  where the SHA-256 is over the content bytes (`r2_writer.py`) — identical
  content dedupes to the same key. `kind` is constrained to the `ArtifactKind`
  taxonomy `{portraits, poi, scenes, music, sfx}` (`r2_writer.py`); an
  unknown kind or unknown content-type **raises `ValueError`** (`r2_writer.py`).
  Live consumer: `zimage_mlx_worker.py`.
- **`upload_pack_asset`** (`r2_writer.py`) — **durable, caller-keyed** pack
  assets. Uses the raw key the caller provides; the JSON-params file's location
  *is* the identity (cf. `music_pipeline.derive_r2_key`). Both `upload_pack_asset`
  and its mirror `download_pack_asset` (`r2_writer.py`) enforce a
  **namespace-prefix guard**: the key must start with `genre_packs/`, else
  `ValueError` (`r2_writer.py`, `:180-181`). Live consumer:
  `pipeline_factory.py`.

Both paths set `CacheControl = "public, max-age=86400"` (`r2_writer.py`) and
propagate any boto3 error verbatim — **no fake URL is ever returned** (no silent
fallback; the caller surfaces failure and emits `image_unavailable`).

### Related decision — independent render/embed locks + MPS-vs-CPU device split

`_run_daemon` constructs **two independent `asyncio.Lock`s** — `render_lock` and
`embed_lock` (`daemon.py`). Z-Image runs on **MPS** under `render_lock`;
the embed model (`SentenceTransformer` all-MiniLM-L6-v2) is pinned to **CPU**
(`daemon.py`) under `embed_lock`. Independent devices → independent locks, so
a long render no longer blocks a ~30ms embed. This is the fix for the **2026-04-10
concurrent-MPS-session deadlock**: a per-request `SentenceTransformer`
construction was racing Flux on the same MPS device (`daemon.py`). The
embed worker is now a pool-owned singleton constructed eagerly at warmup, never
per-request.

## Invariants / Contracts

- **Server-clock liveness.** Staleness is computed against the server's own
  `time.monotonic()` at heartbeat *receipt*, **never** the daemon's
  `ts_monotonic`. The two processes have independent monotonic clock references;
  subtracting one from the other is garbage (state_mirror.py, `is_unresponsive`
  at `:169-191`, review H3). The daemon's `ts_monotonic` is retained for
  diagnostic logging only (`last_heartbeat_ts`, `state_mirror.py`).
- **Failure-closed cold start.** A fresh mirror, or any queue that has never
  published a heartbeat, reports `UNRESPONSIVE` (`state_mirror.py`,
  `:187-188`). The safe default is "fail closed" until a heartbeat lands — the
  dispatcher skips the daemon round-trip and emits the `render.unavailable`
  fallback rather than dispatching into the unknown.
- **2× interval threshold.** `is_unresponsive` fires when the gap since the last
  *received* heartbeat exceeds `2 × heartbeat_interval` (default 30s → 60s window,
  `state_mirror.py`).
- **Unknown state raises.** `record_heartbeat` rejects any state outside
  `{ready, busy, paused, cold}` with `ValueError` (`state_mirror.py`) — a
  typo'd daemon state must not masquerade as health (No Silent Fallbacks). `cold`
  maps to mirror `READY` (a cold-but-alive daemon is still reachable;
  `state_mirror.py`).
- **Fire-and-forget, non-blocking telemetry.** The OTEL bridge never raises into
  the calling path and never blocks it longer than 2s; failures are visible at
  `WARNING` but do not propagate (Contract 2).
- **One-way handshake.** The output-dir handshake is publish-only from the daemon
  and read-only from the server; the write is non-fatal, and the server has an
  explicit env→handshake→none precedence with a loud log on the none branch.
- **SHA-256 content-addressing + namespace guard.** Session artifacts are
  content-addressed under `artifacts/...`; durable pack assets live under
  `genre_packs/...` and are guarded by a prefix check on every read and write.
  The two namespaces never overlap, so artifact cleanup can never touch a pack
  asset.

## Observability

These contracts are themselves part of the observability fabric, and most emit
their own spans:

- **R2 uploads/downloads** emit `daemon.r2.upload.{start,success,failure}` and
  `daemon.r2.download.pack_asset` spans with `kind`/`world`/`session`/`bytes`/
  `ms`/`key` and, on failure, `error_class`/`error_message`/`retry_attempt`
  (`r2_writer.py`, `:148-159`, `:192-208`).
- **The OTEL bridge** is the daemon's *only* path into the GM-panel watcher hub;
  daemon subsystems (prompt composition, music pipeline, render dispatch) emit
  through it (Contract 2 consumers). A bridge POST failure is itself logged at
  `WARNING`, so a telemetry outage is visible rather than silent.
- **Socket-client outcomes** are spanned as `daemon_client.request` with
  `daemon.outcome` values (`socket_missing`, `connection_failed`,
  `reply_timeout`, `eof_before_reply`, `invalid_json`, `error`, `ok`) at
  `client.py`.
- **Liveness** surfaces on the `render.unavailable` watcher event: the mirror
  exposes both the server receive timestamp (`last_received_at`) and the daemon's
  self-reported `ts_monotonic` (`last_heartbeat_ts`) for GM-panel display
  (`state_mirror.py`).
- **Deferred (not a gap):** the daemon-driven periodic idle-heartbeat emitter was
  **cut in story 78-3 (2026-06-03)** rather than left as an unwired scaffold (see
  Consequences). During a fully idle stretch liveness rides on the server listener's
  reconnect cadence (~15s, 4× margin under the 60s unresponsive threshold), which is
  sufficient — wiring a daemon-driven push would have required a net-new active-writer
  broadcast registry. Revive with that registry + a live-path span test if the
  reconnect dependency ever proves insufficient.

## Consequences

**Positive**

- A hung-but-present daemon is now detectable; the 13-minute-silence class of
  failure surfaces as `UNRESPONSIVE` and the dispatcher degrades gracefully.
- Daemon subsystems are observable in the GM panel despite the process boundary,
  satisfying the OTEL Observability Principle without coupling the two processes'
  memory.
- The dev-default (no env) flow renders correctly end-to-end; the 404 regression
  cannot recur silently.
- Session artifacts and durable pack assets have clean, non-overlapping
  lifecycles; content-addressing dedupes identical renders for free.
- Render and embed no longer contend; the MPS/CPU split removes the deadlock
  class entirely.

**Negative / cost**

- **Four out-of-band channels** now ride alongside the ADR-035 socket (heartbeat
  lines on the socket, an HTTP telemetry POST, a filesystem handshake, an R2 key
  convention). Each is a contract a contributor must know about; none is
  discoverable from the JSON-RPC method signatures alone — which is precisely why
  this ADR exists.
- **The periodic idle-heartbeat emitter is deferred (cut, not wired).** The unwired
  `start_periodic_heartbeat` scaffold + its `DEFAULT_HEARTBEAT_INTERVAL_SECONDS`
  constant and isolation test were **removed in story 78-3 (2026-06-03)** rather than
  shipped as a `NOT YET WIRED` stub (a self-documented stub is a trap that makes the
  daemon look more observable than it is). Idle liveness depends on the server
  listener's reconnect loop (~15s); a daemon-driven push would need an active-writer
  broadcast registry that does not exist. Deferred with rationale, not a silent gap.
- The handshake file is a single well-known path (`~/.sidequest/daemon-output-dir`);
  it assumes daemon and server share a home directory (true for the current
  single-host deployment). A multi-host split would need a different discovery
  mechanism.
- The OTEL bridge is synchronous `urllib` on the daemon; a server that hangs
  (rather than refusing) could cost up to 2s per emit on the calling path. Judged
  acceptable for a fire-and-forget error-path call.

## Alternatives considered

- **Socket-message liveness instead of a heartbeat stream.** Rejected: the
  exists-on-disk probe (`is_available`) already *was* the socket-message-presence
  signal, and it is exactly what swallowed the 13-minute silence. A liveness
  signal that depends on the same channel that hangs cannot detect the hang. A
  separate, server-clock-anchored heartbeat with a staleness threshold is the
  minimal thing that actually detects a wedged daemon.
- **`requests` for the OTEL bridge.** Rejected: neither process carries
  `requests` as a runtime dependency, and a fire-and-forget 2s telemetry POST
  from an error path does not justify adding one. Stdlib `urllib.request` is
  crude and synchronous, but adequate at this call volume and timeout
  (`watcher_bridge.py`).
- **Env-var output-dir instead of a handshake file.** Rejected as the *sole*
  mechanism: it requires the operator to set `SIDEQUEST_OUTPUT_DIR` in the
  server's environment too, which the dev-default flow does not do — and its
  absence is exactly what caused the P1 404. The handshake file makes the
  daemon's actual choice discoverable with no shared env. The env var is kept as
  the higher-precedence explicit override (prod / shared dev).
- **One shared lock / shared device for render and embed.** Rejected: that *was*
  the original 37-5 fix and it serialized a ~30ms embed behind a ~120s render.
  Splitting onto independent devices (MPS render, CPU embed) lets them run
  concurrently with independent locks and removes the deadlock at its root rather
  than papering over it.
- **A single flat R2 namespace.** Rejected: session artifacts and durable pack
  assets have different lifecycles; a flat namespace would make artifact cleanup
  unable to distinguish ephemeral from durable, risking deletion of authored
  assets. The two-namespace + prefix-guard split keeps cleanup safe.

## Reconciliation with ADR-035 / ADR-095 / ADR-103

- **ADR-035 (Unix Socket IPC for Python Sidecar):** unchanged and unsuperseded.
  ADR-035 governs the request/response JSON-RPC transport; all four contracts
  here are *additive* layers on top of it (heartbeat lines share the socket but
  are a distinct event shape; the OTEL bridge and handshake use entirely separate
  channels; the R2 layout governs what the render *result* points at). Nothing in
  ADR-035 is contradicted — only extended.
- **ADR-095 (Daemon Music Tier via ACE-Step):** *names* `watcher_bridge.py` and
  `r2_writer.py` as files the music pipeline depends on, but does not state their
  contracts. This ADR governs those contracts (Contracts 2 and 4); the music
  pipeline (`pipeline_factory.py`) is one of their consumers, not their owner.
- **ADR-103 (Native OTEL via Tool Registry):** governs *server-side* native OTEL
  emission via the tool registry. The daemon→server **bridge** (Contract 2) is
  the complementary cross-process feed *into* the same hub from the other
  process; it is not covered by ADR-103 and is governed here.
