---
id: 70
title: "MLX Image Renderer — Replace PyTorch/diffusers with Apple MLX"
status: accepted
date: 2026-04-07
deciders: [Keith Avery]
supersedes: [32, 84]
superseded-by: null
related: []
tags: [media-audio]
implementation-status: live
implementation-pointer: null
---

# ADR-070: MLX Image Renderer — Replace PyTorch/diffusers with Apple MLX

## Context

The `sidequest-daemon` Python sidecar currently runs three ML workers:

1. **FluxWorker** — Flux.1-dev/schnell image generation via `torch` + `diffusers`
2. **TTSWorker** — Kokoro TTS via `onnxruntime`
3. **ACEStepWorker** — ACE-Step music generation via `torch`

Analysis reveals:
- **TTS is being removed** — no user demand for voice synthesis during play
- **ACE-Step is content-creation-only** — generates tracks committed to `sidequest-content`,
  never runs during game sessions. Already isolated in its own venv at `~/Projects/ACE-Step`
- **Flux is the only runtime ML model** — renders portraits, scenes, landscapes during active play

The daemon currently requires PyTorch (~2GB) and diffusers as runtime dependencies for a single
model family. Apple's MLX framework offers 3-5x faster inference on Apple Silicon via unified
memory zero-copy operations.

## Decision

1. **Drop TTSWorker** from the daemon entirely
2. **Remove ACEStepWorker** from the daemon — it stays as a standalone content-creation script
3. **Replace FluxWorker's PyTorch/diffusers backend with MLX** using a community Flux-on-MLX
   implementation (e.g., `mflux` or equivalent)
4. **Remove `torch`, `diffusers`, `accelerate`, `onnxruntime`, `piper-tts`** from daemon dependencies
5. **Add `mlx`, `mlx-nn`** (and whichever Flux-on-MLX package proves stable)

## Consequences

### Positive

- **Faster image generation** — 3-5x improvement on M3 Max via unified memory, no CPU↔GPU copies
- **Simpler daemon** — single ML framework, single model, single purpose
- **Smaller dependency footprint** — MLX (~200MB) replaces PyTorch (~2GB) + diffusers + accelerate
- **Better memory utilization** — MLX's lazy evaluation and unified memory model is purpose-built
  for the 128GB Apple Silicon config
- **Cleaner architecture** — daemon becomes "image generation sidecar," not "media services sidecar"

### Negative

- **Apple Silicon only** — MLX does not run on CUDA/x86. This is acceptable because SideQuest
  is a personal project running on a single M3 Max
- **Community Flux port maturity** — MLX Flux implementations are community-maintained, not
  official. Need to evaluate stability before committing
- **No Rust bindings** — MLX offers Python, C++, Swift, C. No future path to move image gen
  into the Rust API. The Unix socket interface between API and daemon remains necessary
- **IP-Adapter/LoRA compatibility** — ADR-034 (portrait identity consistency) requires
  IP-Adapter support. Must verify the chosen MLX Flux implementation supports this before
  migration

### Unchanged

- **Unix socket protocol** — the JSON-RPC interface between `sidequest-api` and the daemon
  is unaffected. The API sends render requests; the daemon returns image paths
- **Tier system** — portrait/scene/landscape/text_overlay tiers remain; only the backend changes
- **Prompt composition** — T5/CLIP token budgeting logic stays the same
- **ACE-Step workflow** — music generation continues via standalone script, unaffected

## Migration Plan

### Phase 1: Evaluate (spike)
- Test `mflux` or equivalent with the same tier configs (dev 12-step, schnell 4-step)
- Verify IP-Adapter compatibility for portrait identity (ADR-034 dependency)
- Benchmark against current PyTorch/MPS baseline on M3 Max
- Confirm Flux.1-dev and Flux.1-schnell model loading from safetensors

### Phase 2: Implement
- New `FluxMLXWorker` replacing `FluxWorker`
- Same interface: `load_model()`, `warm_up()`, `render()`, `cleanup()`
- Remove torch/diffusers/accelerate/onnxruntime from `pyproject.toml`
- Remove `TTSWorker` and `ACEStepWorker` from daemon
- Update `renderer_factory.py` to use MLX worker

### Phase 3: Verify
- Run full playtest with MLX renderer
- Compare image quality (should be identical — same model weights)
- Measure latency improvement
- Verify OTEL spans still fire for render operations

## Supersedes

- Partially supersedes ADR-032 (genre LoRA style training) — LoRA loading path changes
  from diffusers to MLX format
- TTSWorker removal is independent of this ADR but happens in the same cleanup

## Related

- ADR-034: Portrait identity consistency (IP-Adapter dependency — must verify MLX support)
- ADR-001: Claude CLI only (unchanged — Claude calls remain Rust CLI subprocesses)
