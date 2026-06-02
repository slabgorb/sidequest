# Epic 78: Daemon Media-Pipeline Wiring Debt

## Overview

Resolve a cluster of **daemon exports that exist but are not connected** to the
live Unix-socket / render path — surfaced by the 2026-06-02 `sq-wire-it` wiring
audit. Each story is a deliberate **wire-or-delete decision**: either connect the
mechanism into the real path (and prove it with a test/OTEL span) or remove the
dead surface in the same PR. The cluster spans camera post-processing never
invoked at render, several pure dead exports, and two deferred-feature
observability hooks (heartbeat, GPU detection) with ADR lineage.

**Priority:** P3
**Repo:** daemon
**Stories:** 3 (7 points) — all backlog

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **sq-wire-it audit (2026-06-02)** | The wiring audit that surfaced every finding in this epic; daemon was at `origin/develop` during the scan, so findings are current, not stale-tree artifacts |
| **ADR-131 — Daemon↔Server Out-of-Band Contracts** (`docs/adr/131-*.md`) | Liveness heartbeat — the contract `start_periodic_heartbeat` (78-3) is meant to satisfy |
| **ADR-046 — GPU Memory Budget Coordinator** (`docs/adr/046-*.md`) | The budget/observability context for `detect_gpu`/`GpuInfo` (78-3) |
| **ADR-127 — Image Prompt-Composition Pipeline** (`docs/adr/127-*.md`) | The render/compose path 78-1's camera post-processing would hook into |
| **ADR-070 — MLX Image Renderer** (`docs/adr/070-*.md`) | `ZImageMLXWorker.render` is the sole runtime image worker — the render seam for 78-1 |
| **CLAUDE.md — Wiring principles** | "No Stubbing", "Wire Up What Exists", "Verify Wiring, Not Just Existence", "Delete dead code in the same PR" — the doctrine each story applies |

## Background

The `sq-wire-it` audit on 2026-06-02 scanned all four repos for code that exists
but has no production consumer — the project's most expensive defect class,
because the system can *look* like it works while a subsystem is silently inert.
The daemon (which was already at `origin/develop`) yielded a coherent cluster of
unwired exports, grouped here into three stories by the *kind* of decision each
requires:

- **Output-affecting (78-1).** `apply_post`/`required_render_size`
  (`media/post_processor.py`) have no non-test callers. `CameraLoader` loads
  `CameraSpec.post` (a `PostDirective`), but `ZImageMLXWorker.render` never
  invokes post-processing — so any camera spec relying on crop/rotate is
  **silently dropped at render**. This is LLM-compensation in image form: the
  output looks plausible while the directive is ignored. The only daemon item
  that changes real output.
- **Pure dead code (78-2).** Exports with zero (often zero total) consumers:
  `NullRenderer` + the `renderer.base.Renderer` ABC (no importer anywhere, even
  tests; no factory, no daemon path); dead `genre/models.py` stubs
  (`VisualStyle`, `AudioConfig`, `MixerSettings`, `AIGenerationConfig`,
  `ThemeFamily`, `MoodTrack`, `Variation`, `PackMeta` — the daemon uses
  `StyleCatalog`/YAML directly; only `GenrePack` is referenced, and only under
  `TYPE_CHECKING`); and the half-extracted `dispatch_request` image-tier branch
  (`daemon.py:246`) that raises `NotImplementedError` — a trap for any future
  caller that routes an image tier through it.
- **Deferred-feature observability (78-3).** Two exports with ADR lineage, so a
  *finish-or-cut* decision rather than an automatic delete:
  `start_periodic_heartbeat` (`media/daemon.py:155`) whose own docstring says
  *"NOT YET WIRED INTO `_run_daemon`"* — the 30s idle heartbeat (ADR-131
  liveness) never fires, only per-connection writes keep liveness; and
  `detect_gpu`/`GpuInfo` (`media/gpu_detect.py:25`) with no prod caller, so its
  GPU-detection OTEL span (ADR-046) never fires in production.

## Technical Architecture

All work is in the daemon's socket/render path. The audit traced each export to
its (absent) call site; each story either adds the missing call site or removes
the export.

```
daemon socket loop (_handle_client / _run_daemon)
  ├─ render path ─► ZImageMLXWorker.render (ADR-070, sole image worker)
  │       └─ [78-1] required_render_size + apply_post  ← currently NOT called;
  │                 CameraSpec.post loaded but ignored. WIRE here or DELETE field+loader.
  ├─ liveness ────► per-connection _write_heartbeat (live)
  │       └─ [78-3] start_periodic_heartbeat (30s idle) ← "NOT YET WIRED"; schedule as
  │                 background task in _run_daemon (ADR-131) or CUT with a deferral note.
  ├─ warmup ──────► WorkerPool / ZImageMLXWorker warmup
  │       └─ [78-3] detect_gpu/GpuInfo ← never called; call at warmup so the ADR-046
  │                 GPU span fires, or CUT with a deferral note.
  └─ dispatch_request: music tier WIRED; image tier raises NotImplementedError
          └─ [78-2] finish the image-tier extraction OR remove the trap branch.

dead, no path: NullRenderer + Renderer ABC, genre/models.py stubs  ← [78-2] DELETE
```

**Key files:**

| File | Story |
|------|-------|
| `sidequest-daemon/sidequest_daemon/media/post_processor.py` (`apply_post`, `required_render_size`) + `CameraLoader` (`CameraSpec.post`) + `media/workers/zimage_mlx_worker.py` (`render`) | 78-1 |
| `sidequest_daemon/renderer/null.py` (`NullRenderer`), `renderer/base.py` (`Renderer` ABC), `genre/models.py` (stubs), `media/daemon.py:246` (`dispatch_request` image branch) | 78-2 |
| `media/daemon.py:155` (`start_periodic_heartbeat`, `_run_daemon`), `media/gpu_detect.py:25` (`detect_gpu`, `GpuInfo`) | 78-3 |

**Decision guardrails (per story):**
- **78-1** — first determine whether any in-use `CameraSpec` actually sets a
  `post:` directive (grep content camera specs). If yes → wire and add an
  integration test asserting the transform applied. If no → delete `apply_post`,
  `required_render_size`, the `CameraSpec.post` field, and its `CameraLoader`
  parsing in one PR (Delete Dead Code in the Same PR).
- **78-2** — confirm zero consumers immediately before deleting each export.
  Default action is delete; for `dispatch_request`'s image branch, either finish
  the extraction or remove the `NotImplementedError` trap so it can't ambush a
  future caller. `daemon-test` + `daemon-lint` green after removals.
- **78-3** — prefer **wiring** if the ADR still wants the capability (heartbeat is
  an ADR-131 contract; GPU detection feeds ADR-046). If wired, an **OTEL span
  assertion test** must prove the heartbeat/GPU span fires on the live path —
  "Wired = visible in the GM panel." If cut, remove with an explicit ADR-deferral
  note rather than leaving a self-documented "NOT YET WIRED" stub.

## Cross-Epic Dependencies

**Depends on:**
- **sq-wire-it audit (2026-06-02)** — the source of every finding; re-confirm
  zero-consumer status at story start in case develop moved.
- **ADR-131 (liveness heartbeat)** and **ADR-046 (GPU budget)** — determine
  whether 78-3's exports get wired or cut.

**Depended on by:**
- Nothing blocks on this epic — it is pure debt reduction. Value is a smaller,
  honest daemon surface (no "looks-wired" traps) and, for 78-1/78-3 if wired,
  correct image output and real liveness/GPU observability.
