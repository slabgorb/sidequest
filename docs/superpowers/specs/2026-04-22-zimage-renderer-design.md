# Z-Image Base 1.0 as Sole Image Renderer

**Date:** 2026-04-22
**Author:** Architect (Neo)
**Status:** Approved — ready for implementation plan

## Summary

Swap Flux for Z-Image Base 1.0 in `sidequest-daemon`. Drop all LoRA support. That's it.

## Motivation

Z-Image Base with good prompts produces better style adherence than Flux with custom LoRAs. mflux (already a daemon dep) ships Z-Image as a first-class backend, so no new library.

## What changes

| Path | Action |
|---|---|
| `pyproject.toml` | Bump `mflux` pin to a version that includes the `z_image` module. Remove the Task-4.2b pin comment. |
| `media/workers/flux_mlx_worker.py` | Delete. |
| `media/workers/zimage_mlx_worker.py` | New. Same JSON-line stdin/stdout protocol and `MediaWorker` contract as the old Flux worker, but calls mflux's Z-Image pipeline. No LoRA loading, no LoRA mapping, no safetensors validation. |
| `media/flux_config.py` | Delete. |
| `media/zimage_config.py` | New. Same `TierConfig` shape; Z-Image defaults (steps/guidance/width/height) for every `RenderTier`. |
| `media/renderer_factory.py` | Subprocess command → `zimage_mlx_worker`. `renderer_name="flux"` → `"zimage"`. Import `ZIMAGE_SUPPORTED_TIERS`. |
| `media/daemon.py` | `FLUX_TIERS` → `IMAGE_TIERS`. Update module docstring. |
| `media/prompt_composer.py` | Remove `_FLUX_FORCED_TIERS` branch. Positive/negative prompt assembly stays as-is — the `negative_prompt` end-to-end pathway (genre → composer → worker params) is already wired and untouched. |
| Flux LoRA tests | Delete. |
| Rust API, UI, content packs | No change. |

## What does not change

- `RenderTier` enum stays intact. Every existing tier is served by Z-Image.
- Unix-socket protocol unchanged.
- `scene_interpreter`, `prompt_composer` core logic, `renderer.py` (`SubprocessRenderer`), `MediaWorker` — unchanged.
- Rust API speaks tier, not model. No change needed.
- No CLI flag for renderer selection. Z-Image is hardcoded.
- Genre pack YAMLs untouched. `/sq-lora` skill untouched. ADRs untouched.

## Tests

- Unit: `zimage_mlx_worker.load_model()` and `render()` return a PIL-compatible image for `SCENE_ILLUSTRATION`. Skipped if Z-Image weights aren't cached locally.
- Unit: `ZIMAGE_TIER_CONFIGS` has an entry for every `RenderTier`.
- Integration (CLAUDE.md wiring requirement): `renderer_factory.create_renderer()` returns a `SubprocessRenderer` with `renderer_name == "zimage"` when a GPU is available; daemon round-trips a `SCENE_ILLUSTRATION` render over the Unix socket.
- Delete: Flux LoRA mapping tests, Flux worker unit tests.

## OTEL

Per CLAUDE.md OTEL obligation, the new worker emits the same span shape the GM panel already consumes for renders, with `renderer=zimage` in attributes. Span names and attribute keys mirror whatever the Flux worker emitted today — verify during implementation.

## Rollout

Single PR on `sidequest-daemon` → `develop` (per `repos.yaml`). Revert = `git revert`. No migration state.

## Acceptance Criteria

1. Daemon runs on Z-Image Base 1.0 for all tiers with no Flux worker present.
2. `flux_mlx_worker.py`, `flux_config.py`, and all Flux LoRA code/tests removed.
3. `mflux` pin bumped to a Z-Image-capable version.
4. `renderer_factory` returns a `SubprocessRenderer` named `"zimage"` when a GPU is available.
5. Integration test covers end-to-end `SCENE_ILLUSTRATION` render through the daemon.
6. OTEL spans are emitted for Z-Image renders.
