---
parent: context-epic-78.md
workflow: tdd
---

# Story 78-3: Daemon deferred observability — start_periodic_heartbeat (ADR-131) + detect_gpu/GpuInfo span (ADR-046) unwired: wire or cut

## Business Context

This is the **deferred-feature** lane of the 2026-06-02 `sq-wire-it` daemon
wiring audit (epic 78). Unlike 78-2's pure dead-export sweep, both exports here
carry **ADR lineage**, so each is a deliberate **finish-or-cut** decision, not an
automatic delete. The doctrine the epic applies: *prefer wiring if the ADR still
wants the capability* — and "Wired = visible in the GM panel" (OTEL Observability
Principle). The cost of leaving them as-is is the project's most expensive defect
class: a self-documented `NOT YET WIRED` stub is a trap that makes the daemon
*look* more observable than it is.

The two exports diverge sharply once you read their ADRs, and the Dev should not
treat them as a single symmetric decision:

- **`start_periodic_heartbeat` (`media/daemon.py:155`) — ADR-131, status `live`.**
  ADR-131 Contract 1 (Liveness heartbeat stream) is the "Felix anti-13-minute-
  silence" contract: a hung-but-present daemon must surface as `UNRESPONSIVE`
  rather than passing an exists-on-disk probe (the 2026-04-19 playtest failure
  where the daemon went silent ~13 min and the server kept dispatching into a
  dead socket). The periodic idle emitter is explicitly called out as a **known,
  documented follow-up** in ADR-131 Consequences and Observability ("Gap: the
  periodic idle-heartbeat emitter is not yet wired ... during a fully idle
  stretch liveness rides solely on the listener's reconnect cadence rather than a
  daemon-driven push"). The ADR still wants this capability. **Leans WIRE.** Today
  idle liveness rides on the server's `DaemonClient.heartbeat_listener`
  reconnecting every ~15s (4× margin under the 60s unresponsive threshold), so
  liveness is *not currently broken* — wiring the daemon-driven push completes the
  contract and removes the reconnect-cadence dependency.

- **`detect_gpu`/`GpuInfo` (`media/gpu_detect.py:25`) — ADR-046, status `retired`.**
  Read ADR-046's banner carefully: the GPU Memory Budget Coordinator
  (`ModelMemoryManager`, `sidequest_daemon/ml/memory_manager.py`) was **deleted in
  commit `5118d6c` on 2026-05-10** because it had zero non-test callers, and the
  ADR explicitly states "the implementation in this ADR is not what should be
  revived." The `memory_manager` module is gone (grep confirms zero remnants in
  the daemon). So the epic's framing — "GPU detection feeds the ADR-046 budget
  coordinator's observability" — describes a coordinator that **no longer exists**.
  `detect_gpu` is a standalone diagnostic that emits a `gpu.detect` span; nothing
  consumes its `GpuInfo` result in production. There is no live coordinator for it
  to feed. **This one does NOT clearly lean wire** — its parent ADR is retired.
  The honest options are: (a) **CUT** it with an ADR-046-deferral note (the
  coordinator it was meant to feed is dead), or (b) a **minimal WIRE** as a
  one-shot warmup diagnostic span — useful only if Keith wants "what GPU did the
  daemon see at boot?" visibility in the GM panel for its own sake, independent of
  the dead coordinator. The Dev should surface this distinction in the story and
  let the wire-vs-cut call be made on whether boot-time GPU visibility has
  standalone value, NOT on a still-wanted ADR-046 (it isn't).

The audit ran with the daemon at `origin/develop`, so these are current findings,
not stale-tree artifacts (cf. the "Playtest verify: pull, don't just restart"
discipline). Re-confirm zero-consumer status at story start in case develop moved.

## Technical Guardrails

**Confirmed seams (read 2026-06-02):**

- `start_periodic_heartbeat` is at `media/daemon.py:155`, an `async def`
  long-running coroutine. Its docstring (lines 160–177) literally says **"NOT YET
  WIRED INTO `_run_daemon` (review H2 follow-up)"**. It takes
  `interval_seconds` (default `DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30.0`,
  `daemon.py:118`) and an `emit: Callable[[dict], None | Awaitable[None]] | None`
  that defaults to `None` (→ no-op loop). It builds payloads via `_make_heartbeat`
  (`daemon.py:127`) for both `("image", "embed")` queues with state
  `WorkerState.READY`. **Sole non-test reference is its own definition;** the only
  caller is `tests/test_heartbeat_emit.py` (AC2 isolation test).
- `_run_daemon` is at `daemon.py:1070`. The wire seam: after warmup
  (`daemon.py:1137-1145`) and after `asyncio.start_unix_server`
  (`daemon.py:1162`), but the daemon then blocks on `await stop_event.wait()`
  (`daemon.py:1189`). A periodic emitter must be scheduled as a **background
  task** (`asyncio.create_task(...)`) before that wait, and **cancelled in the
  `finally` shutdown block** (`daemon.py:1190-1200`) alongside `server.close()` /
  `pool.cleanup()` — do not leak a dangling task.
- **The real heartbeat design subtlety (do not skip):** ADR-131 says the wired
  `emit` must be **"a broadcast helper that fans out to every active client
  writer"** (docstring lines 174–175; ADR-131 Consequences: "Until a broadcast
  emit fans out to active client writers..."). Per-connection writers in
  `_handle_client` are **not currently tracked in a global registry** — there is
  no set of active writers to broadcast to. Wiring this honestly means either (a)
  adding an active-writer registry that connections register/deregister into and
  the periodic task fans out across, or (b) a narrower interpretation the Dev must
  justify. A `start_periodic_heartbeat(emit=None)` scheduled with a no-op `emit`
  would satisfy the letter of "scheduled in `_run_daemon`" while emitting nothing
  — that is a **stub-in-disguise** and violates AC1's "idle-heartbeat emission
  verified". The span-assertion test (below) is what prevents that no-op outcome.
- `detect_gpu` is at `media/gpu_detect.py:25`. It opens a `gpu.detect` span via
  `trace.get_tracer("sidequest_daemon.media.gpu_detect")` and sets
  `gpu.backend` / `gpu.available` / `gpu.device_name` attributes (mlx import probe
  → `GpuInfo`). **No production caller;** only `tests/test_otel_spans.py`
  (`TestDetectGpuSpan`) imports it. If wired, the natural seam is **once at warmup
  in `_run_daemon`** (near `daemon.py:1137-1145`, before/after `warm_up_image`),
  logging the `GpuInfo` so the `gpu.detect` span fires on the live boot path.

**If WIRING (either export):**
- Schedule `start_periodic_heartbeat` as a background `asyncio.create_task` in
  `_run_daemon` (ADR-131 Contract 1), with a real broadcast `emit` (active-writer
  fan-out), and cancel it in the shutdown `finally`. Call `detect_gpu()` once at
  warmup so the `gpu.detect` span fires in production.
- **EITHER wired path REQUIRES an OTEL span-assertion test proving the span fires
  on the LIVE path** (AC3). An isolated unit test that calls the function directly
  (the existing `test_heartbeat_emit.py` / `test_otel_spans.py` shape) does **not**
  satisfy this — those already exist and prove the function works in isolation.
  The new test must exercise the `_run_daemon` wiring (or the warmup call) and
  assert the heartbeat emit actually fanned out / the `gpu.detect` span was
  recorded on the production code path. This is the project's
  "Every Test Suite Needs a Wiring Test" rule applied literally.
- OTEL spans are the lie detector here — daemon→server telemetry rides the
  ADR-131 Contract 2 OTEL HTTP bridge (`telemetry/watcher_bridge.py`,
  `emit_watcher_event`) into the server's watcher hub / GM panel. If a wired
  heartbeat or GPU span isn't visible in the GM panel, it isn't wired.

**If CUTTING (either export):**
- Delete the export (`start_periodic_heartbeat` + `DEFAULT_HEARTBEAT_INTERVAL_SECONDS`
  if it becomes orphaned, or `detect_gpu` + `GpuInfo` + the `gpu_detect.py`
  module) **and its now-orphaned isolation test** in the same PR
  ("Delete Dead Code in the Same PR"). Do NOT preserve a test pointed at deleted
  code.
- Record an **explicit ADR-deferral note** in the relevant ADR rather than leaving
  the self-documented `NOT YET WIRED` stub. For heartbeat: amend ADR-131's
  Consequences to state the periodic emitter is *cut/deferred* with rationale (the
  server listener's reconnect cadence covers idle liveness). For GPU: ADR-046 is
  already `retired` and already documents the coordinator's removal — a cut here
  just removes the orphaned diagnostic and notes it followed the coordinator out.
  The point of the note is that the *next* contributor reads "deferred, here's
  why" instead of "wired (it lies) / NOT YET WIRED (a trap)".

**Repo / process:** daemon repo only (`sidequest-daemon`), gitflow, branch off
`develop`, PR → `develop`, squash-merge. Gate with `just daemon-test` +
`just daemon-lint` green. The daemon must reload cached state on bounce; if you
manually verify, restart the daemon, don't just reload.

## Scope Boundaries

**In scope:**
- The wire-or-cut decision and implementation for `start_periodic_heartbeat`
  (the 30s idle heartbeat, ADR-131 Contract 1).
- The wire-or-cut decision and implementation for `detect_gpu`/`GpuInfo` (the
  `gpu.detect` OTEL span, ADR-046 lineage).
- If either is wired: the OTEL **span-assertion test on the live path** proving
  the span fires (AC3), plus the broadcast-writer fan-out needed for a real
  heartbeat emit.
- If either is cut: deletion of the export + its orphaned isolation test + an
  explicit ADR-deferral note in the owning ADR.

**Out of scope:**
- Camera post-processing / `apply_post` / `required_render_size` / `CameraSpec.post`
  — that is **78-1** (the only output-affecting daemon item).
- The pure dead-export sweep — `NullRenderer`, `renderer.base.Renderer` ABC, the
  `genre/models.py` stubs, and the `dispatch_request` image-tier
  `NotImplementedError` trap branch — that is **78-2**.
- Reviving the ADR-046 `ModelMemoryManager` budget coordinator. It is retired
  (deleted `5118d6c`, 2026-05-10) and the ADR says its implementation is "not what
  should be revived." This story does not bring it back; at most it wires a
  standalone boot-time GPU diagnostic span.
- Reworking ADR-131 Contracts 2–4 (OTEL bridge, output-dir handshake, R2 layout) —
  those are live and out of scope; only Contract 1's periodic emitter is in play.
- Changing the server-side `DaemonStateMirror` / `heartbeat_listener` — the wiring
  is daemon-side; the server consumes whatever the daemon emits.

## AC Context

**AC1 — `start_periodic_heartbeat`: scheduled in `_run_daemon` as a background
task AND idle-heartbeat emission verified, OR removed with an ADR-131 deferral
note.**
This is the heartbeat finish-or-cut. *Leans WIRE* (ADR-131 is `live` and names
this an explicit wanted follow-up). "Scheduled as a background task" means an
`asyncio.create_task` in `_run_daemon` before the `stop_event.wait()`, cancelled
in the shutdown `finally`. **"idle-heartbeat emission verified" is the load-bearing
clause** — a `create_task` with a no-op `emit=None` would satisfy "scheduled" but
emit nothing; that is the stub-in-disguise failure. Real wiring needs a broadcast
emit that fans out to active client writers (which requires an active-writer
registry that doesn't exist today — see Technical Guardrails). If cut instead,
delete the coroutine + its `test_heartbeat_emit.py` AC2 test and amend ADR-131
Consequences to mark the periodic emitter deferred with rationale.

**AC2 — `detect_gpu`/`GpuInfo`: called at daemon warmup so the GPU-detection span
fires in production, OR removed with an ADR-046 deferral note.**
This is the GPU finish-or-cut. **Ambiguity to resolve at story start:** the AC
phrasing ("so the span fires in production") presumes wiring is desirable, but
ADR-046 is **retired** and the coordinator the span was designed to feed is
**deleted**. The Dev must decide on the *standalone* merit of a boot-time GPU
diagnostic span — there is no live ADR-046 consumer pulling for it. If wired:
call `detect_gpu()` once in `_run_daemon`'s warmup block (`daemon.py:1137-1145`),
log the result, span fires on boot. If cut: delete `gpu_detect.py` + its
`test_otel_spans.py` `TestDetectGpuSpan` and add a one-line ADR-046 note that the
orphaned diagnostic followed the coordinator out (2026-05-10). Either is
defensible; do not pretend ADR-046 mandates wiring — it does not.

**AC3 — If wired: OTEL span assertion test proves the heartbeat/GPU span fires on
the live path.**
Conditional, fires only for whichever export(s) get wired. The bar is **live
path**, not isolated unit. The existing `test_heartbeat_emit.py` and
`test_otel_spans.py::TestDetectGpuSpan` already call the functions directly and
prove isolated behavior — they do NOT satisfy AC3. The new test must drive the
`_run_daemon` wiring (heartbeat: assert the scheduled task fanned a heartbeat out
to a registered writer; GPU: assert the warmup call recorded the `gpu.detect`
span) so the GM panel would actually see it. If *both* exports are cut, AC3 is
vacuously satisfied (no wiring to test) — but then AC1 and AC2 each carry their
deletion + ADR-note obligations.

## Assumptions

- ADR-046's `retired` status and the 2026-05-10 `5118d6c` coordinator deletion are
  authoritative; grep confirms no `memory_manager` / `ModelMemoryManager` remnant
  in the daemon today. The GPU export is genuinely orphaned, not feeding a live
  system.
- ADR-131's `live` status and its explicit "periodic emitter is a documented
  follow-up" language mean the heartbeat capability is still wanted by
  architecture-of-record; this is the basis for its WIRE lean.
- Wiring a *real* idle heartbeat requires touching `_handle_client` to register
  active writers (no such registry exists). If the Dev finds the broadcast fan-out
  is larger than the 2-point budget allows, the honest fallback is to CUT the
  heartbeat with an ADR-131 deferral note rather than ship a no-op `emit=None`
  scheduled task — re-scope to SM rather than fake the wire.
