---
story_id: "27-4"
jira_key: null
epic: "27"
workflow: "trivial"
---
# Story 27-4: Daemon dependency swap — remove torch/diffusers, add mlx/mflux

## Story Details
- **ID:** 27-4
- **Jira Key:** None (personal project, no tracking)
- **Workflow:** trivial
- **Stack Parent:** 27-3 (FluxMLXWorker - completed)
- **Repos:** sidequest-daemon

## Story Context

Epic 27 is migrating the image renderer from PyTorch/diffusers to Apple MLX via mflux. Prior stories have:
- Stripped TTSWorker and Kokoro (27-1)
- Stripped ACEStepWorker (27-2)
- Implemented FluxMLXWorker with mflux backend (27-3)

This story completes the migration by updating dependencies and cleaning up legacy code.

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-07T07:25:47Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-07T03:14Z | 2026-04-07T07:17:04Z | 4h 3m |
| implement | 2026-04-07T07:17:04Z | 2026-04-07T07:20:51Z | 3m 47s |
| review | 2026-04-07T07:20:51Z | 2026-04-07T07:25:47Z | 4m 56s |
| finish | 2026-04-07T07:25:47Z | - | - |

## Work Scope

### Changes Required

**pyproject.toml:**
- Remove: `torch>=2.0`, `diffusers>=0.30`, `accelerate>=0.30`, `piper-tts>=1.2`
- Add: `mlx`, `mflux`
- Keep: pydantic, transformers, safetensors, numpy, pyyaml, aiohttp, sentence-transformers, pygame-ce, pedalboard, scipy, sounddevice

**gpu_detect.py:**
- Update to detect MLX instead of torch CUDA/MPS
- Verify it reports MLX availability correctly

**Clean up legacy:**
- Delete `flux_worker.py` (replaced by FluxMLXWorker from 27-3)

### Branch
**feat/27-4-daemon-dep-swap** (created, on develop base)

## Delivery Findings

No upstream findings yet.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): renderer_factory.py had wrong package name in subprocess command (`sidequest.media` instead of `sidequest_daemon.media`) — corrected during this story.
  Affects `sidequest_daemon/media/renderer_factory.py` (line 67, was broken before this fix).
  *Found by Dev during implementation.*

### Reviewer (code review)
- No upstream findings during code review.

## Sm Assessment

Story 27-4 is a 2-point trivial workflow — dependency swap in pyproject.toml, gpu_detect.py update, and flux_worker.py deletion. All prerequisites complete (27-1 stripped TTS, 27-2 stripped ACE-Step, 27-3 created FluxMLXWorker and wired it into daemon.py).

**Scope:** Pure infrastructure — swap deps, delete dead code, update GPU detection. No new features, no behavior changes.

**Routing:** Inigo Montoya (Dev) implements directly, then Westley (Reviewer) reviews.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `pyproject.toml` — Removed torch>=2.0, diffusers>=0.30, accelerate>=0.30; added mlx>=0.18, mflux>=0.4
- `sidequest_daemon/media/gpu_detect.py` — Replaced torch CUDA/MPS detection with MLX detection via `mlx.core.default_device()`
- `sidequest_daemon/media/renderer_factory.py` — Updated subprocess module path from `flux_worker` to `flux_mlx_worker`
- `sidequest_daemon/media/workers/flux_worker.py` — Deleted (294 lines, replaced by FluxMLXWorker from 27-3)

**Tests:** 53/53 passing (GREEN)
**Branch:** feat/27-4-daemon-dep-swap (pushed)

**Implementation notes:**
- GpuBackend Literal narrowed from `"cuda" | "mps" | "none"` to `"mlx" | "none"` — Apple Silicon only now
- renderer_factory.py had a stale module path `sidequest.media.workers.flux_worker` (wrong package name too) — corrected to `sidequest_daemon.media.workers.flux_mlx_worker`
- piper-tts was already removed in pyproject.toml (by 27-1), confirmed not present

**Handoff:** To Westley (Reviewer) for code review

## Design Deviations

No design deviations yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No undocumented deviations found.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | dismissed 2 (pre-existing code), confirmed 1 LOW (gpu_detect catch pattern) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 3 | dismissed 3 (all in flux_mlx_worker.py, not changed by this diff) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 9 | confirmed 3 LOW, dismissed 6 (pre-existing, 27-3 code, or 27-7 scope) |

**All received:** Yes (4 returned, 5 disabled via settings)
**Total findings:** 4 confirmed (all LOW), 11 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Dependency swap correct — `pyproject.toml` removes torch>=2.0, diffusers>=0.30, accelerate>=0.30; adds mlx>=0.18, mflux>=0.4. Keeps transformers/safetensors (transitive deps for sentence-transformers and mflux). Evidence: `pyproject.toml:7-10`.

2. [VERIFIED] gpu_detect.py rewritten for MLX — uses `mlx.core.default_device()` instead of torch CUDA/MPS chain. GpuBackend narrowed to `Literal["mlx", "none"]`. Only consumer (renderer_factory.py) checks `gpu.available` bool, never branches on backend string. Evidence: `gpu_detect.py:23-40`, `renderer_factory.py:57-58`.

3. [VERIFIED] Old FluxWorker deleted — 293 lines removed. No remaining imports anywhere in codebase. Confirmed via grep: only references in test file are negative assertions (verify old import NOT present). Evidence: `flux_worker.py` deleted, `grep flux_worker` returns only test assertions.

4. [VERIFIED] renderer_factory.py module path fixed — old path `sidequest.media.workers.flux_worker` (wrong package name!) corrected to `sidequest_daemon.media.workers.flux_mlx_worker`. Dev caught a pre-existing bug. Evidence: `renderer_factory.py:67`.

5. [VERIFIED] No silent fallbacks in new code — gpu_detect.py fails loudly on ImportError (returns `available=False` with log), and catches Exception on `mx.default_device()` with `logger.warning`. Matches pre-existing pattern. Evidence: `gpu_detect.py:27-29, 36-37`.

6. [LOW] [RULE] `mlx>=0.18` and `mflux>=0.4` lack upper bounds — 0.x libraries may have breaking changes. Non-blocking for personal project. `pyproject.toml:8-9`.

7. [LOW] [RULE] `logger.warning` in gpu_detect.py:37 should be `logger.error` per checklist (server-side failure = error level). Matches old pattern but technically violates rule #4.

8. [LOW] [SILENT] gpu_detect.py:36 bare `except Exception` could swallow unexpected MLX failures. Same pattern as old torch version. Non-blocking.

9. [LOW] [RULE] transformers/safetensors retained as explicit deps — not directly imported but likely transitive. Could be removed if sentence-transformers and mflux handle their own transitive deps, but keeping them pinned is safer.

### Rule Compliance

| Rule | Instances | Compliant | Notes |
|------|-----------|-----------|-------|
| #1 Silent exceptions | 5 | 4/5 | gpu_detect catch; matches old pattern |
| #2 Mutable defaults | 6 | 6/6 | Clean |
| #3 Type annotations | 8 | 7/8 | render() bare dict (27-3 code, not this diff) |
| #4 Logging | 8 | 7/8 | warning→error in gpu_detect; LOW |
| #5 Path handling | 4 | 4/4 | Clean |
| #6 Test quality | 13 | 11/13 | Minor (27-3 tests, not this diff) |
| #7 Resource leaks | 2 | 2/2 | Clean |
| #8 Unsafe deser | 3 | 3/3 | Clean |
| #9 Async pitfalls | 3 | 3/3 | Clean |
| #10 Import hygiene | 6 | 5/6 | mflux deep path (27-3 code) |
| #11 Security | 2 | 2/2 | Clean |
| #12 Dependency | 5 | 3/5 | No upper bounds; LOW |
| #13 Meta-check | 3 | 3/3 | Clean |
| No silent fallbacks | 3 | 2/3 | gpu_detect catch chain; LOW |
| OTEL | 2 | 0/2 | Story 27-7 scope |

[EDGE] No edge-hunter findings — disabled via settings.
[SILENT] 1 confirmed LOW (gpu_detect catch pattern). 2 dismissed (pre-existing renderer_factory code).
[TEST] No test-analyzer findings — disabled via settings.
[DOC] No comment-analyzer findings — disabled via settings.
[TYPE] 0 confirmed in this diff. 3 dismissed (all in 27-3 code, not changed here).
[SEC] No security findings — disabled via settings.
[SIMPLE] No simplifier findings — disabled via settings.
[RULE] 3 confirmed LOW (dep upper bounds, logger level, gpu_detect catch). 6 dismissed (pre-existing, 27-3, or 27-7 scope).

### Devil's Advocate

What if this dependency swap breaks production? The daemon was running on torch/diffusers before this change. Now it depends on mlx/mflux, which are Apple-Silicon-only libraries. What happens on a Linux CI server? `uv sync` will try to install mlx and fail — mlx only builds on macOS with Apple Silicon. This means the daemon can no longer be installed or tested on non-Apple hardware.

However — this is a personal project running exclusively on Keith's M3 Max MacBook Pro (128GB). There is no Linux CI. There is no cross-platform deployment. The entire premise of epic 27 is "optimize for Apple Silicon." The torch dependency was already Apple-only in practice (MPS backend). This change makes that explicit rather than implicit.

What about the phantom deps (transformers, safetensors)? If we remove them and sentence-transformers or mflux pins incompatible versions transitively, the venv breaks silently. Keeping them pinned is conservative and correct.

What about the `mx.default_device()` catch swallowing failures? On Keith's M3 Max, MLX will always succeed. The catch exists for defensive completeness. If MLX is installed but somehow broken, the daemon logs a warning and falls through to NullRenderer — which is what the old torch version did too. Not a regression.

**Conclusion:** This is a clean, minimal dependency swap. The only real work is the pyproject.toml change and flux_worker deletion. The gpu_detect rewrite is straightforward. The renderer_factory fix caught a pre-existing bug. APPROVED.

**Data flow traced:** `detect_gpu()` → `import mlx.core` → `mx.default_device()` → `GpuInfo(available=True, backend="mlx")` → `create_renderer()` checks `gpu.available` → proceeds to subprocess worker. Safe: MLX import is guarded, device check is guarded.
**Pattern observed:** Lazy import for optional ML dependency at `gpu_detect.py:30` — same pattern as FluxMLXWorker's mflux import.
**Error handling:** ImportError → clean fallback to none. Exception → warning + fallback. Both match existing patterns.
**Handoff:** To Vizzini (SM) for finish-story