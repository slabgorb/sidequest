# Epic 27: MLX Image Renderer — Replace PyTorch with Apple MLX

## Overview

Migrate the `sidequest-daemon` image generation backend from PyTorch/diffusers to
Apple MLX via `mflux`. Simultaneously strip dead workers (TTSWorker, ACEStepWorker)
that no longer run during game sessions. The daemon becomes a single-purpose Flux
image renderer with dramatically reduced dependency footprint (~200MB MLX vs ~2GB
PyTorch).

**Core change:** Replace `FluxWorker` (PyTorch/diffusers/MPS) with `FluxMLXWorker`
(MLX unified memory, zero-copy). Same interface: `load_model()`, `warm_up()`,
`render()`, `cleanup()`. Same tiers, same prompt composition, same JSON-RPC protocol.

**ADR:** 070-mlx-image-renderer.md

## Background

### Why MLX

The daemon currently drags in PyTorch (~2GB), diffusers, and accelerate to run a
single model family (Flux.1-dev/schnell). Apple's MLX framework provides:
- 3-5x faster inference on M3 Max via unified memory (no CPU↔GPU copies)
- Lazy evaluation and memory-efficient computation
- Purpose-built for the 128GB Apple Silicon config

The other two workers are already vestigial:
- **TTSWorker (Kokoro)** — no user demand for voice synthesis during play
- **ACEStepWorker** — content-creation-only, runs in its own venv at `~/Projects/ACE-Step`

### Current Architecture

```
sidequest-daemon/sidequest_daemon/
├── media/
│   ├── daemon.py          # WorkerPool routes by tier → FluxWorker/ACEStep/TTS
│   ├── workers/
│   │   ├── flux_worker.py    # PyTorch/diffusers, MPS device, torch.float16
│   │   ├── acestep_worker.py # ACE-Step music gen (remove)
│   │   └── tts_worker.py     # Kokoro TTS (remove)
│   ├── prompt_composer.py    # T5/CLIP token budgeting (unchanged)
│   ├── subject_extractor.py  # LLM-based subject extraction (unchanged)
│   ├── gpu_detect.py         # torch.cuda/mps detection (update for MLX)
│   └── protocol.py           # WorkerRequest/Response models (unchanged)
├── renderer/
│   ├── base.py            # Renderer ABC (unchanged)
│   ├── models.py          # RenderTier, StageCue, RenderResult (unchanged)
│   ├── beat_filter.py     # Skip non-visual beats (unchanged)
│   ├── null.py            # NullRenderer for testing (unchanged)
│   └── stale.py           # Stale image detection (unchanged)
├── scene_interpreter.py   # Narration → StageCue extraction (unchanged)
├── voice/                 # 17 modules — Kokoro/Piper TTS (remove)
└── audio/                 # Audio mixer/rotator (may stay for music playback)
```

### What Changes vs What Stays

| Component | Action | Reason |
|-----------|--------|--------|
| `workers/flux_worker.py` | Replace with `FluxMLXWorker` | Core migration |
| `workers/tts_worker.py` | Delete | No user demand for TTS |
| `workers/acestep_worker.py` | Delete | Standalone script, not runtime |
| `voice/` (17 files) | Delete | All Kokoro/Piper infrastructure |
| `daemon.py` WorkerPool | Simplify | Remove ACE-Step/TTS routing |
| `gpu_detect.py` | Update | Replace torch detection with MLX |
| `pyproject.toml` | Swap deps | torch/diffusers/accelerate/piper → mlx/mflux |
| `renderer/` | Unchanged | Abstract interface, models, beat filter |
| `scene_interpreter.py` | Unchanged | Rules-based cue extraction |
| `prompt_composer.py` | Unchanged | T5/CLIP budgeting |
| `media/protocol.py` | Unchanged | WorkerRequest/Response |
| Unix socket protocol | Unchanged | JSON-RPC, tier routing |

## Technical Architecture

### Worker Interface Contract

The `FluxMLXWorker` must implement the same interface as `FluxWorker`:

```python
class FluxMLXWorker:
    def __init__(self, output_dir: Path): ...
    def load_model(self, variant: str = "dev"): ...  # "dev" (12-step) or "schnell" (4-step)
    def warm_up(self) -> dict: ...
    def render(self, params: dict) -> dict: ...       # Returns {"path": str, "seed": int, ...}
    def cleanup(self): ...
```

### Tier Routing (post-migration)

Only Flux tiers remain active:
```python
FLUX_TIERS = {"scene_illustration", "portrait", "landscape", "cartography", "text_overlay", "tactical_sketch"}
EMBED_TIERS = {"embed"}  # sentence-transformers, stays
```

`MUSIC_TIERS` and `TTS_TIERS` are removed entirely. Requests for those tiers
should raise `ValueError` (no silent fallbacks).

### Dependency Swap

**Remove:**
- `torch>=2.0`
- `diffusers>=0.30`
- `accelerate>=0.30`
- `piper-tts>=1.2`

**Add:**
- `mlx` (Apple MLX framework)
- `mflux` (or equivalent Flux-on-MLX implementation)

**Keep:**
- `pydantic`, `transformers`, `safetensors`, `numpy`, `pyyaml`, `aiohttp`
- `sentence-transformers` (EmbedWorker)
- `pygame-ce`, `pedalboard`, `scipy`, `sounddevice` (audio playback)

### LoRA Compatibility

Genre style LoRAs (loaded from `sidequest-content/genre_packs/*/lora/`) must work
with the MLX backend. ADR-032 defines the LoRA training pipeline. The MLX worker
must load `.safetensors` LoRA weights — verify `mflux` supports this path.

### IP-Adapter / img2img Dependency

ADR-034 (portrait identity consistency) requires either IP-Adapter or img2img for
character recognition across re-renders. This is a potential blocker — if `mflux`
doesn't support IP-Adapter, the portrait identity epic (17) needs a different
approach. Story 27-6 evaluates Redux/img2img as an alternative.

## Dependency Chain

```
27-1 (Strip TTS) ──────────────┐
27-2 (Strip ACE-Step) ─────────┤
                                ├→ 27-4 (Dependency swap) → 27-8 (Playtest)
27-3 (FluxMLXWorker) ──────────┤
                                ├→ 27-5 (LoRA verification)
                                └→ 27-7 (OTEL spans)
27-6 (Redux/img2img eval) ─── independent spike
```

**Phase 1 (27-1, 27-2):** Strip dead workers. Pure deletion, no new code.
**Phase 2 (27-3):** Core migration — FluxMLXWorker implementation.
**Phase 3 (27-4):** Dependency swap in pyproject.toml. Blocks playtest.
**Phase 4 (27-5, 27-7):** LoRA verification and OTEL instrumentation.
**Phase 5 (27-8):** End-to-end playtest validation.
**Independent (27-6):** Redux/img2img spike — can run anytime.

## Story Points

| Story | Title | Points | Priority | Workflow | Depends On |
|-------|-------|--------|----------|----------|------------|
| 27-1 | Strip TTSWorker and Kokoro from daemon | 2 | p1 | trivial | — |
| 27-2 | Strip ACEStepWorker from daemon runtime | 2 | p1 | trivial | — |
| 27-3 | FluxMLXWorker — replace FluxWorker with mflux backend | 5 | p1 | tdd | — |
| 27-4 | Daemon dependency swap — remove torch/diffusers, add mlx/mflux | 2 | p1 | trivial | 27-1, 27-2, 27-3 |
| 27-5 | LoRA loading verification — genre style LoRAs via mflux | 3 | p1 | tdd | 27-3 |
| 27-6 | Redux/img2img evaluation — portrait identity without IP-Adapter | 3 | p2 | tdd | — |
| 27-7 | OTEL spans for MLX render pipeline | 2 | p2 | tdd | 27-3 |
| 27-8 | Playtest validation — MLX renderer end-to-end | 2 | p1 | trivial | 27-4 |
| **Total** | | **21** | | | |

## Scope Boundaries

**IN scope:**
- Replace FluxWorker with MLX-based equivalent
- Remove TTSWorker, ACEStepWorker, and all voice/ modules
- Remove torch/diffusers/accelerate/piper-tts from dependencies
- Add mlx/mflux dependencies
- Verify LoRA loading path works with MLX
- Evaluate img2img/Redux as IP-Adapter alternative
- OTEL spans for MLX render operations
- End-to-end playtest verification

**OUT of scope:**
- Portrait identity system (Epic 17 — depends on 27-6 evaluation)
- Audio playback changes (pygame-ce stays for music file playback)
- Scene interpreter changes (rules-based, no ML dependency)
- Prompt composition changes (T5/CLIP budgeting is model-agnostic)
- Unix socket protocol changes (JSON-RPC interface unchanged)
- ACE-Step standalone script changes (stays in its own venv)

## Key Files

### Daemon core
- `sidequest_daemon/media/daemon.py` — WorkerPool, tier routing, JSON-RPC handler
- `sidequest_daemon/media/workers/flux_worker.py` — Current PyTorch FluxWorker (replace)
- `sidequest_daemon/media/workers/tts_worker.py` — TTSWorker (delete)
- `sidequest_daemon/media/workers/acestep_worker.py` — ACEStepWorker (delete)
- `sidequest_daemon/media/gpu_detect.py` — GPU detection (update for MLX)

### Voice infrastructure (delete all)
- `sidequest_daemon/voice/` — 17 files: kokoro.py, piper.py, router.py, selector.py, etc.

### Unchanged but relevant
- `sidequest_daemon/renderer/base.py` — Renderer ABC
- `sidequest_daemon/renderer/models.py` — RenderTier, StageCue, RenderResult
- `sidequest_daemon/media/prompt_composer.py` — T5/CLIP token budgeting
- `sidequest_daemon/scene_interpreter.py` — Narration → StageCue
- `pyproject.toml` — Dependencies to swap

### Cross-repo
- `docs/adr/070-mlx-image-renderer.md` — This epic's ADR
- `docs/adr/034-portrait-identity.md` — IP-Adapter dependency (27-6 evaluates alternatives)
- `docs/adr/032-genre-lora-training.md` — LoRA path changes
