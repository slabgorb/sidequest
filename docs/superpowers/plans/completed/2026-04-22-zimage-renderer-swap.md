# Z-Image Renderer Swap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Swap Flux for Z-Image Base 1.0 in `sidequest-daemon` and delete all LoRA support.

**Architecture:** Replace the `FluxMLXWorker` subprocess with a new `ZImageMLXWorker` that calls mflux's `ZImage` pipeline. Keep the JSON-line protocol, `MediaWorker` contract, `SubprocessRenderer`, daemon Unix socket, and `RenderTier` enum unchanged. Rust API, UI, and genre pack YAMLs are untouched.

**Tech Stack:** Python 3.11+, mflux (bumped to a Z-Image-capable version), `mflux.models.z_image.variants.ZImage`, pytest + pytest-asyncio, uv.

**Spec:** `docs/superpowers/specs/2026-04-22-zimage-renderer-design.md`

**Repo + branch:** All work happens in `sidequest-daemon/` against `develop` (per `repos.yaml`). Feature branch: `feat/zimage-renderer-swap`.

---

## Preflight

- [ ] **Preflight Step 1: Create feature branch**

```bash
cd sidequest-daemon && git checkout develop && git pull && git checkout -b feat/zimage-renderer-swap
```

- [ ] **Preflight Step 2: Verify mflux Z-Image module is importable**

Run:
```bash
cd sidequest-daemon && uv run python -c "from mflux.models.z_image.variants.z_image import ZImage; from mflux.models.common.config import ModelConfig; print(ModelConfig.from_name('z-image'))"
```
Expected: prints a `ModelConfig` object with no error. If import fails, the installed mflux is too old — resolve with Task 1 first.

---

## Task 1: Bump mflux pin to a Z-Image-capable version

**Files:**
- Modify: `sidequest-daemon/pyproject.toml`

**Context:** Current pin is `"mflux>=0.17,<0.18"`. The comment (Task-4.2b) was tied to `FluxLoRAMapping.get_mapping()` shape validation in the worker we're about to delete, so the comment comes out with the pin bump. The installed `.venv` already has a newer mflux that ships Z-Image (preflight Step 2 confirmed), so resolve to whatever `uv lock` chooses with a looser ceiling.

- [ ] **Step 1: Find installed mflux version**

Run:
```bash
cd sidequest-daemon && uv run python -c "import importlib.metadata as m; print(m.version('mflux'))"
```
Record the printed version (call it `$MFLUX_VER`) for the pin below.

- [ ] **Step 2: Update pin**

In `sidequest-daemon/pyproject.toml`, replace this line:

```toml
    "mflux>=0.17,<0.18",  # pin: flux_mlx_worker depends on FluxLoRAMapping.get_mapping() shape and mflux.models.flux.* module layout (new in 0.17). Bump only after verifying.
```

with:

```toml
    "mflux>=$MFLUX_VER",
```

Substitute the literal version from Step 1 (e.g., `"mflux>=0.22"`).

- [ ] **Step 3: Resolve the lock**

Run:
```bash
cd sidequest-daemon && uv lock
```
Expected: `uv.lock` updates with no errors.

- [ ] **Step 4: Commit**

```bash
cd sidequest-daemon && git add pyproject.toml uv.lock && git commit -m "chore(deps): bump mflux pin to support z-image"
```

---

## Task 2: Create `zimage_config.py` with tier configs (TDD)

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/zimage_config.py`
- Create: `sidequest-daemon/tests/test_zimage_config.py`

**Context:** Mirrors the shape of the soon-to-be-deleted `flux_config.py`. Z-Image Base is one model (no dev/schnell split), so `model_variant` drops from the dataclass. Starting tier defaults reuse Flux's step counts as a reasonable anchor; guidance values are tuned for Z-Image Base 1.0 (CFG ~4.5 for Base per mflux defaults).

- [ ] **Step 1: Write the failing test**

Create `sidequest-daemon/tests/test_zimage_config.py`:

```python
"""Tests for Z-Image tier configuration table."""

from sidequest_daemon.media.zimage_config import (
    ZIMAGE_SUPPORTED_TIERS,
    ZIMAGE_TIER_CONFIGS,
    ZImageTierConfig,
)
from sidequest_daemon.renderer.models import RenderTier


def test_every_render_tier_has_a_config():
    """Every value in RenderTier must have a ZImageTierConfig entry."""
    for tier in RenderTier:
        assert tier in ZIMAGE_TIER_CONFIGS, f"Missing config for {tier!r}"


def test_supported_tiers_matches_config_keys():
    assert ZIMAGE_SUPPORTED_TIERS == frozenset(ZIMAGE_TIER_CONFIGS)


def test_tier_config_shape():
    for tier, cfg in ZIMAGE_TIER_CONFIGS.items():
        assert isinstance(cfg, ZImageTierConfig)
        assert cfg.steps > 0
        assert cfg.guidance >= 0.0
        assert cfg.width > 0 and cfg.height > 0


def test_tier_config_is_frozen():
    import dataclasses
    assert dataclasses.is_dataclass(ZImageTierConfig)
    sample = next(iter(ZIMAGE_TIER_CONFIGS.values()))
    try:
        sample.steps = 999  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("ZImageTierConfig should be frozen")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd sidequest-daemon && uv run pytest tests/test_zimage_config.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest_daemon.media.zimage_config'`.

- [ ] **Step 3: Write the config module**

Create `sidequest-daemon/sidequest_daemon/media/zimage_config.py`:

```python
"""Z-Image tier configuration — maps RenderTier to generation parameters.

Importable by the main package for tests and wiring. The worker subprocess
duplicates this table (it cannot import from sidequest_daemon).
"""

from __future__ import annotations

from dataclasses import dataclass

from sidequest_daemon.renderer.models import RenderTier


@dataclass(frozen=True)
class ZImageTierConfig:
    """Z-Image generation parameters for a specific render tier."""

    steps: int
    guidance: float
    width: int
    height: int


ZIMAGE_TIER_CONFIGS: dict[RenderTier, ZImageTierConfig] = {
    RenderTier.SCENE_ILLUSTRATION: ZImageTierConfig(
        steps=12, guidance=4.5, width=1024, height=768,
    ),
    RenderTier.PORTRAIT: ZImageTierConfig(
        steps=12, guidance=4.5, width=768, height=1024,
    ),
    RenderTier.PORTRAIT_SQUARE: ZImageTierConfig(
        steps=12, guidance=4.5, width=1024, height=1024,
    ),
    RenderTier.LANDSCAPE: ZImageTierConfig(
        steps=12, guidance=4.5, width=1024, height=768,
    ),
    RenderTier.TEXT_OVERLAY: ZImageTierConfig(
        steps=12, guidance=4.5, width=768, height=512,
    ),
    RenderTier.CARTOGRAPHY: ZImageTierConfig(
        steps=20, guidance=4.5, width=1024, height=1024,
    ),
    RenderTier.TACTICAL_SKETCH: ZImageTierConfig(
        steps=12, guidance=4.5, width=1024, height=1024,
    ),
}

ZIMAGE_SUPPORTED_TIERS: frozenset[RenderTier] = frozenset(ZIMAGE_TIER_CONFIGS)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd sidequest-daemon && uv run pytest tests/test_zimage_config.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd sidequest-daemon && git add sidequest_daemon/media/zimage_config.py tests/test_zimage_config.py && git commit -m "feat(renderer): add zimage_config with per-tier settings"
```

---

## Task 3: Create `zimage_mlx_worker.py` (TDD)

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py`
- Create: `sidequest-daemon/tests/test_zimage_mlx_worker.py`

**Context:** The new worker preserves the JSON-line stdin/stdout protocol of `flux_mlx_worker.py`: methods `ping`, `warm_up`, `render`, `shutdown`. It preserves the same response shape (`{image_url, width, height, elapsed_ms}`) so `SubprocessRenderer` keeps working unchanged. What it drops: `variant`/`preferred_model` override (Z-Image has one model), all LoRA params, `FluxLoRAMapping` validation. The `_compose_prompt` fallback for batch scripts (raw StageCue fields) is preserved. OTEL spans mirror the Flux worker's: tracer name `sidequest_daemon.media.workers.zimage_mlx_worker`, spans `zimage_mlx.load_model`, `zimage_mlx.warm_up`, `zimage_mlx.render`.

The `ZImage` API (verified from mflux source): `ZImage(quantize, model_path, lora_paths, lora_scales, model_config).generate_image(seed, prompt, num_inference_steps, height, width, guidance, image_path, image_strength, scheduler, negative_prompt) -> PIL.Image`. Pass `model_config=ModelConfig.from_name("z-image")` and `scheduler="flow_match_euler_discrete"` (Z-Image's default per its CLI).

- [ ] **Step 1: Write the failing test**

Create `sidequest-daemon/tests/test_zimage_mlx_worker.py`:

```python
"""Unit tests for ZImageMLXWorker.

The ZImage model is mocked — we test worker glue, not the inference pipeline.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from sidequest_daemon.media.workers.zimage_mlx_worker import ZImageMLXWorker


def _fake_pil_image(w: int = 64, h: int = 64) -> Image.Image:
    return Image.new("RGB", (w, h), color="black")


@pytest.fixture
def worker(tmp_path: Path) -> ZImageMLXWorker:
    return ZImageMLXWorker(output_dir=tmp_path)


def test_tier_configs_match_render_tier_enum(worker: ZImageMLXWorker):
    """Worker's internal tier table must cover every tier the composer emits."""
    assert "scene_illustration" in worker.TIER_CONFIGS
    assert "portrait" in worker.TIER_CONFIGS
    assert "landscape" in worker.TIER_CONFIGS
    assert "text_overlay" in worker.TIER_CONFIGS
    assert "tactical_sketch" in worker.TIER_CONFIGS


def test_render_unknown_tier_raises(worker: ZImageMLXWorker):
    with pytest.raises(ValueError, match="Unsupported tier"):
        worker.render({"tier": "not_a_tier", "positive_prompt": "x"})


def test_render_rejects_lora_params(worker: ZImageMLXWorker):
    """LoRA support is removed. Passing LoRA params must fail loudly."""
    mock_model = MagicMock()
    mock_model.generate_image.return_value = _fake_pil_image()
    worker.model = mock_model

    with pytest.raises(ValueError, match="LoRA"):
        worker.render(
            {
                "tier": "scene_illustration",
                "positive_prompt": "x",
                "lora_paths": ["anything.safetensors"],
            }
        )


def test_render_returns_expected_result_shape(worker: ZImageMLXWorker):
    """Successful render returns image_url + dims + elapsed_ms."""
    mock_model = MagicMock()
    mock_model.generate_image.return_value = _fake_pil_image()
    worker.model = mock_model

    result = worker.render(
        {
            "tier": "scene_illustration",
            "positive_prompt": "a dark forest",
            "negative_prompt": "blurry",
            "seed": 42,
        }
    )

    assert "image_url" in result
    assert Path(result["image_url"]).exists()
    assert result["width"] == 1024
    assert result["height"] == 768
    assert isinstance(result["elapsed_ms"], int)


def test_render_passes_negative_prompt_to_model(worker: ZImageMLXWorker):
    mock_model = MagicMock()
    mock_model.generate_image.return_value = _fake_pil_image()
    worker.model = mock_model

    worker.render(
        {
            "tier": "portrait",
            "positive_prompt": "a face",
            "negative_prompt": "photograph, realistic",
            "seed": 1,
        }
    )

    call_kwargs = mock_model.generate_image.call_args.kwargs
    assert call_kwargs["negative_prompt"] == "photograph, realistic"
    assert call_kwargs["prompt"] == "a face"
    assert call_kwargs["seed"] == 1


def test_compose_prompt_fallback_from_raw_fields(worker: ZImageMLXWorker):
    """Batch scripts pass raw StageCue fields instead of positive_prompt."""
    mock_model = MagicMock()
    mock_model.generate_image.return_value = _fake_pil_image()
    worker.model = mock_model

    worker.render(
        {
            "tier": "portrait",
            "subject": "an old knight",
            "mood": "somber",
            "tags": ["armor", "scarred face"],
            "seed": 0,
        }
    )

    called_prompt = mock_model.generate_image.call_args.kwargs["prompt"]
    assert "an old knight" in called_prompt
    assert "somber atmosphere" in called_prompt
    assert "armor" in called_prompt


def test_compose_prompt_requires_content(worker: ZImageMLXWorker):
    mock_model = MagicMock()
    mock_model.generate_image.return_value = _fake_pil_image()
    worker.model = mock_model

    with pytest.raises(ValueError, match="No prompt content"):
        worker.render({"tier": "scene_illustration", "seed": 0})
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd sidequest-daemon && uv run pytest tests/test_zimage_mlx_worker.py -v
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the worker**

Create `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py`:

```python
"""Z-Image image generation worker — Apple Silicon native via mflux.

Replaces FluxMLXWorker. Same interface contract: load_model(), warm_up(),
render(), cleanup(). Communicates via JSON-line protocol over stdin/stdout
when run as subprocess. No LoRA support.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from pathlib import Path

from opentelemetry import trace

log = logging.getLogger(__name__)


class ZImageMLXWorker:
    """Z-Image Base 1.0 image generation worker using Apple MLX via mflux."""

    # Tier config — KEEP IN SYNC with zimage_config.py and daemon.py IMAGE_TIERS.
    TIER_CONFIGS = {
        "scene_illustration": {"steps": 12, "guidance": 4.5, "w": 1024, "h": 768},
        "portrait":           {"steps": 12, "guidance": 4.5, "w": 768,  "h": 1024},
        "portrait_square":    {"steps": 12, "guidance": 4.5, "w": 1024, "h": 1024},
        "landscape":          {"steps": 12, "guidance": 4.5, "w": 1024, "h": 768},
        "text_overlay":       {"steps": 12, "guidance": 4.5, "w": 768,  "h": 512},
        "cartography":        {"steps": 20, "guidance": 4.5, "w": 1024, "h": 1024},
        "tactical_sketch":    {"steps": 12, "guidance": 4.5, "w": 1024, "h": 1024},
    }

    # Quantization level for model loading. None = full precision.
    QUANTIZE: int | None = None

    # Z-Image's default scheduler per its CLI.
    SCHEDULER: str = "flow_match_euler_discrete"

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model: object | None = None

    def load_model(self) -> None:
        """Load Z-Image Base 1.0 via mflux."""
        tracer = trace.get_tracer(
            "sidequest_daemon.media.workers.zimage_mlx_worker"
        )
        with tracer.start_as_current_span("zimage_mlx.load_model") as span:
            span.set_attribute("model.name", "z-image")
            span.set_attribute("model.quantize", self.QUANTIZE or 0)
            from mflux.models.common.config import ModelConfig
            from mflux.models.z_image.variants.z_image import ZImage

            self.model = ZImage(
                model_config=ModelConfig.from_name("z-image"),
                quantize=self.QUANTIZE,
            )

    def _ensure_loaded(self) -> None:
        if self.model is None:
            self.load_model()

    def warm_up(self) -> dict:
        """MLX graph compilation via dummy generation."""
        self._ensure_loaded()
        tracer = trace.get_tracer(
            "sidequest_daemon.media.workers.zimage_mlx_worker"
        )
        with tracer.start_as_current_span("zimage_mlx.warm_up") as span:
            start = time.monotonic()
            assert self.model is not None
            self.model.generate_image(  # type: ignore[attr-defined]
                seed=0,
                prompt="black",
                num_inference_steps=1,
                guidance=0.0,
                width=512,
                height=512,
                scheduler=self.SCHEDULER,
                negative_prompt=None,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            span.set_attribute("warmup.elapsed_ms", elapsed_ms)
            return {"warmup_ms": elapsed_ms}

    def render(self, params: dict) -> dict:
        """Generate image from StageCue params. Returns result dict."""
        tracer = trace.get_tracer(
            "sidequest_daemon.media.workers.zimage_mlx_worker"
        )
        with tracer.start_as_current_span("zimage_mlx.render") as span:
            try:
                tier_name = params.get("tier", "")
                if tier_name not in self.TIER_CONFIGS:
                    raise ValueError(f"Unsupported tier: {tier_name!r}")

                # LoRA support is removed. Reject callers that still send it.
                if any(
                    k in params
                    for k in ("lora_paths", "lora_scales", "lora_path", "lora_scale")
                ):
                    raise ValueError(
                        "LoRA support has been removed from the renderer. "
                        "Remove lora_paths/lora_scales from render params."
                    )

                tier_cfg = self.TIER_CONFIGS[tier_name]
                prompt = self._compose_prompt(params)
                negative_prompt = params.get("negative_prompt") or None
                seed = params.get("seed", 0)

                span.set_attribute("render.tier", tier_name)
                span.set_attribute("render.seed", seed)
                span.set_attribute("render.width", tier_cfg["w"])
                span.set_attribute("render.height", tier_cfg["h"])
                span.set_attribute("render.steps", tier_cfg["steps"])
                span.set_attribute("render.guidance", tier_cfg["guidance"])
                span.set_attribute("render.prompt_length", len(prompt))
                span.set_attribute(
                    "render.negative_length", len(negative_prompt or "")
                )

                log.info(
                    "ZIMAGE RENDER [%s] seed=%s w=%s h=%s steps=%s",
                    tier_name, seed, tier_cfg["w"], tier_cfg["h"], tier_cfg["steps"],
                )
                log.info("  prompt: %s", prompt[:150])

                self._ensure_loaded()
                assert self.model is not None

                start = time.monotonic()
                image = self.model.generate_image(  # type: ignore[attr-defined]
                    seed=seed,
                    prompt=prompt,
                    num_inference_steps=tier_cfg["steps"],
                    guidance=tier_cfg["guidance"],
                    width=tier_cfg["w"],
                    height=tier_cfg["h"],
                    scheduler=self.SCHEDULER,
                    negative_prompt=negative_prompt,
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)
                span.set_attribute("render.elapsed_ms", elapsed_ms)

                filename = f"render_{uuid.uuid4().hex[:8]}.png"
                image_path = self.output_dir / filename
                image.save(str(image_path))

                return {
                    "image_url": str(image_path),
                    "width": tier_cfg["w"],
                    "height": tier_cfg["h"],
                    "elapsed_ms": elapsed_ms,
                }
            except Exception as exc:
                span.set_status(trace.StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

    def _compose_prompt(self, params: dict) -> str:
        """Build positive prompt for Z-Image.

        If SubprocessRenderer already composed a prompt (with genre style
        suffix and location tag overrides), use it directly. Otherwise
        fall back to building from raw StageCue fields (used by batch
        scripts like generate_portraits.py).
        """
        if params.get("positive_prompt"):
            return params["positive_prompt"]
        if params.get("prompt"):
            return params["prompt"]

        tier = params.get("tier", "")
        is_text_overlay = tier == "text_overlay"

        parts: list[str] = []
        if params.get("subject"):
            subject = params["subject"]
            if is_text_overlay:
                subject = f"text reading {subject}"
            parts.append(subject)
        if params.get("mood"):
            parts.append(f"{params['mood']} atmosphere")
        if params.get("location"):
            parts.append(f"set in {params['location']}")
        if params.get("tags"):
            parts.extend(params["tags"])

        if is_text_overlay:
            parts.extend(["clean typography", "readable text", "sharp lettering"])

        if not parts:
            raise ValueError(
                "No prompt content: params has no positive_prompt, prompt, "
                f"subject, or tags. Params: {params}"
            )

        return ", ".join(parts)

    def cleanup(self) -> None:
        """Unload model, free GPU memory."""
        self.model = None


def _respond(
    req_id: str, *, result: dict | None = None, error: dict | None = None
) -> None:
    """Write a JSON response line to stdout."""
    resp: dict = {"id": req_id}
    if result is not None:
        resp["result"] = result
    if error is not None:
        resp["error"] = error
    print(json.dumps(resp), flush=True)


def main() -> None:
    """JSON-line protocol loop."""
    import tempfile

    output_dir = Path(tempfile.mkdtemp(prefix="sq-zimage-mlx-"))
    worker = ZImageMLXWorker(output_dir)

    worker.load_model()
    worker.warm_up()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
            req_id = req.get("id", "unknown")
            method = req.get("method")
            if not method:
                _respond(
                    req_id,
                    error={"code": "INVALID_REQUEST", "message": "Missing 'method'"},
                )
                continue
        except json.JSONDecodeError as e:
            _respond("unknown", error={"code": "PARSE_ERROR", "message": str(e)})
            continue
        params = req.get("params", {})

        if method == "ping":
            _respond(req_id, result={"status": "ok"})
        elif method == "shutdown":
            _respond(req_id, result={"status": "ok"})
            worker.cleanup()
            break
        elif method == "render":
            try:
                render_result = worker.render(params)
                _respond(req_id, result=render_result)
            except Exception as e:
                _respond(
                    req_id,
                    error={"code": "GENERATION_FAILED", "message": str(e)},
                )
        elif method == "warm_up":
            try:
                warm_result = worker.warm_up()
                _respond(req_id, result=warm_result)
            except Exception as e:
                _respond(
                    req_id,
                    error={"code": "WARMUP_FAILED", "message": str(e)},
                )
        else:
            _respond(
                req_id,
                error={"code": "UNKNOWN_METHOD", "message": f"Unknown: {method}"},
            )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run unit tests to verify they pass**

Run:
```bash
cd sidequest-daemon && uv run pytest tests/test_zimage_mlx_worker.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd sidequest-daemon && git add sidequest_daemon/media/workers/zimage_mlx_worker.py tests/test_zimage_mlx_worker.py && git commit -m "feat(renderer): add zimage_mlx_worker (no LoRA)"
```

---

## Task 4: Swap `renderer_factory.py` to Z-Image

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/renderer_factory.py`

**Context:** The factory spawns the subprocess and names the renderer. We swap the module path and the name. `FLUX_SUPPORTED_TIERS` → `ZIMAGE_SUPPORTED_TIERS`.

- [ ] **Step 1: Apply the edit**

Replace the imports block near the top of `renderer_factory.py`:

```python
from sidequest_daemon.media.flux_config import FLUX_SUPPORTED_TIERS
```

with:

```python
from sidequest_daemon.media.zimage_config import ZIMAGE_SUPPORTED_TIERS
```

Inside `_try_daemon`, change:

```python
            renderer_name="renderer-daemon",
            supported_tiers=FLUX_SUPPORTED_TIERS,
```

to:

```python
            renderer_name="renderer-daemon",
            supported_tiers=ZIMAGE_SUPPORTED_TIERS,
```

Inside `create_renderer`, change:

```python
        worker = MediaWorker(
            name="flux",
            command=[sys.executable, "-m", "sidequest_daemon.media.workers.flux_mlx_worker"],
            workdir=Path.cwd(),
            default_timeout=900.0,
        )
        await worker.start()

        return SubprocessRenderer(
            worker=worker,
            renderer_name="flux",
            supported_tiers=FLUX_SUPPORTED_TIERS,
            visual_style=visual_style,
        )
```

to:

```python
        worker = MediaWorker(
            name="zimage",
            command=[sys.executable, "-m", "sidequest_daemon.media.workers.zimage_mlx_worker"],
            workdir=Path.cwd(),
            default_timeout=900.0,
        )
        await worker.start()

        return SubprocessRenderer(
            worker=worker,
            renderer_name="zimage",
            supported_tiers=ZIMAGE_SUPPORTED_TIERS,
            visual_style=visual_style,
        )
```

- [ ] **Step 2: Verify lint/typecheck**

Run:
```bash
cd sidequest-daemon && uv run ruff check sidequest_daemon/media/renderer_factory.py
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd sidequest-daemon && git add sidequest_daemon/media/renderer_factory.py && git commit -m "feat(renderer): wire factory to zimage worker"
```

---

## Task 5: Rename `FLUX_TIERS` → `IMAGE_TIERS` in `daemon.py`

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/daemon.py`

**Context:** Purely a rename; the set contents (`scene_illustration`, `portrait`, `portrait_square`, `landscape`, `cartography`, `text_overlay`, `tactical_sketch`) stay identical. Also update the module docstring line that says "persistent Flux image renderer" to reflect Z-Image.

- [ ] **Step 1: Find every occurrence of FLUX_TIERS in daemon.py**

Run:
```bash
cd sidequest-daemon && grep -n "FLUX_TIERS\|FLUX_" sidequest_daemon/media/daemon.py
```
Record results for Step 2.

- [ ] **Step 2: Apply replacements**

In `sidequest_daemon/media/daemon.py`:

- Replace every `FLUX_TIERS` with `IMAGE_TIERS` (there should be a `frozenset({...})` definition and 1–2 usages).
- Update the module docstring's first line from `"""sidequest-renderer daemon — persistent Flux image renderer on Unix domain socket."""` to `"""sidequest-renderer daemon — persistent Z-Image renderer on Unix domain socket."""`.
- Update any "Hosts the Flux image worker" in the docstring to "Hosts the Z-Image worker".

- [ ] **Step 3: Verify no stale references**

Run:
```bash
cd sidequest-daemon && grep -n "FLUX_TIERS\|FLUX_" sidequest_daemon/media/daemon.py || echo "clean"
```
Expected: prints `clean`.

- [ ] **Step 4: Run the smoke test**

Run:
```bash
cd sidequest-daemon && uv run pytest tests/test_daemon_smoke.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-daemon && git add sidequest_daemon/media/daemon.py && git commit -m "refactor(daemon): rename FLUX_TIERS to IMAGE_TIERS"
```

---

## Task 6: Remove `_FLUX_FORCED_TIERS` from `prompt_composer.py`

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`

**Context:** The `_FLUX_FORCED_TIERS = {TEXT_OVERLAY, CARTOGRAPHY, TACTICAL_SKETCH}` set (line 41) gated prompt shaping on the assumption Flux was the renderer. Z-Image gets the same general prompt shape for every tier. Remove the set and any branches that key off it.

- [ ] **Step 1: Locate the set and all its references**

Run:
```bash
cd sidequest-daemon && grep -n "_FLUX_FORCED_TIERS" sidequest_daemon/media/prompt_composer.py
```
Record line numbers.

- [ ] **Step 2: Delete the set definition and inline any conditionals**

For each reference: read the surrounding branch. If the branch was "only do X for forced-flux tiers," delete the `if cue.tier in _FLUX_FORCED_TIERS:` guard so the body runs unconditionally **only if** that body is still appropriate for every tier; otherwise delete the entire block. Use judgment per branch — the common case is "flux-specific prompt hack no longer needed; delete the whole block." Finally, delete the `_FLUX_FORCED_TIERS = {...}` definition line.

- [ ] **Step 3: Verify the set is gone**

Run:
```bash
cd sidequest-daemon && grep -n "_FLUX_FORCED_TIERS\|FLUX_FORCED" sidequest_daemon/media/prompt_composer.py || echo "clean"
```
Expected: prints `clean`.

- [ ] **Step 4: Run prompt_composer tests**

Run:
```bash
cd sidequest-daemon && uv run pytest tests/ -k "prompt_composer or compose" -v
```
Expected: all tests pass. If a test was pinning the old forced-flux behavior, delete or rewrite it to match the new unconditional behavior (note in commit message).

- [ ] **Step 5: Commit**

```bash
cd sidequest-daemon && git add sidequest_daemon/media/prompt_composer.py tests/ && git commit -m "refactor(prompts): drop Flux-forced tier branch"
```

---

## Task 7: Delete Flux worker, config, and Flux-LoRA tests

**Files:**
- Delete: `sidequest-daemon/sidequest_daemon/media/workers/flux_mlx_worker.py`
- Delete: `sidequest-daemon/sidequest_daemon/media/flux_config.py`
- Delete: `sidequest-daemon/tests/test_flux_mlx_worker.py`
- Delete: `sidequest-daemon/tests/test_flux_mlx_worker_multilora.py`
- Delete: `sidequest-daemon/tests/test_flux_mlx_worker_matched_keys.py`
- Delete: `sidequest-daemon/tests/test_lora_loading_story_27_5.py`

**Context:** At this point nothing imports from `flux_mlx_worker` or `flux_config` (Tasks 4–6 rewired the one consumer, `renderer_factory.py`). The LoRA tests cover functionality that no longer exists. Verify orphan status before deleting.

- [ ] **Step 1: Confirm no live imports of flux_mlx_worker or flux_config**

Run:
```bash
cd sidequest-daemon && grep -rn "flux_mlx_worker\|flux_config\|FluxMLXWorker\|FLUX_TIER_CONFIGS\|FLUX_SUPPORTED_TIERS" sidequest_daemon/ --include="*.py" | grep -v __pycache__
```
Expected: no output. If anything prints other than the files we're about to delete, fix those references first.

- [ ] **Step 2: Delete the files**

Run:
```bash
cd sidequest-daemon && git rm sidequest_daemon/media/workers/flux_mlx_worker.py sidequest_daemon/media/flux_config.py tests/test_flux_mlx_worker.py tests/test_flux_mlx_worker_multilora.py tests/test_flux_mlx_worker_matched_keys.py tests/test_lora_loading_story_27_5.py
```
Expected: 6 files removed.

- [ ] **Step 3: Run the full test suite**

Run:
```bash
cd sidequest-daemon && uv run pytest -x
```
Expected: all remaining tests pass. If an unrelated test imports a deleted module, fix or delete that test.

- [ ] **Step 4: Commit**

```bash
cd sidequest-daemon && git commit -m "refactor(renderer): remove flux worker, flux_config, and LoRA tests"
```

---

## Task 8: Integration test — renderer factory wires up Z-Image

**Files:**
- Create: `sidequest-daemon/tests/test_zimage_renderer_wiring.py`

**Context:** CLAUDE.md requires every test suite to include at least one wiring test. The factory is the integration point; if it returns a `SubprocessRenderer` named `"zimage"` that points at `zimage_mlx_worker`, wiring is correct. We do not boot the model here — just check the subprocess command and renderer name.

- [ ] **Step 1: Write the failing test**

Create `sidequest-daemon/tests/test_zimage_renderer_wiring.py`:

```python
"""Wiring test: renderer_factory returns a Z-Image SubprocessRenderer."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sidequest_daemon.media.renderer_factory import create_renderer
from sidequest_daemon.media.renderer import SubprocessRenderer
from sidequest_daemon.media.gpu_detect import GPUInfo


@pytest.mark.asyncio
async def test_factory_returns_zimage_subprocess_renderer(tmp_path, monkeypatch):
    """With no running daemon and a GPU available, factory returns a
    SubprocessRenderer named 'zimage' that launches the zimage worker."""
    # Force the daemon-not-running branch
    from sidequest_daemon.media import renderer_factory as rf
    monkeypatch.setattr(rf, "_try_daemon", AsyncMock(return_value=None))

    # Pretend we have a GPU
    monkeypatch.setattr(
        rf, "detect_gpu", lambda: GPUInfo(available=True, backend="mps")
    )

    # Stub MediaWorker.start so we don't actually spawn a subprocess
    started: dict = {}

    async def fake_start(self):
        started["command"] = self._command if hasattr(self, "_command") else None
        started["name"] = self.name if hasattr(self, "name") else None

    from sidequest_daemon.media import worker as worker_mod
    monkeypatch.setattr(worker_mod.MediaWorker, "start", fake_start)

    renderer = await create_renderer(visual_style=None)

    assert isinstance(renderer, SubprocessRenderer)
    assert renderer.name == "zimage"
```

- [ ] **Step 2: Run and iterate**

Run:
```bash
cd sidequest-daemon && uv run pytest tests/test_zimage_renderer_wiring.py -v
```
Expected: PASS. If the test fails because `GPUInfo` has a different constructor shape or `MediaWorker` exposes command differently, read `sidequest_daemon/media/gpu_detect.py` and `sidequest_daemon/media/worker.py` and adjust the test to call real constructors / attributes — do not weaken the assertion on `renderer.name == "zimage"`.

- [ ] **Step 3: Commit**

```bash
cd sidequest-daemon && git add tests/test_zimage_renderer_wiring.py && git commit -m "test(renderer): wiring test for zimage factory"
```

---

## Task 9: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the daemon's full test suite**

Run:
```bash
cd sidequest-daemon && uv run pytest -v
```
Expected: all green, no skipped tests other than those explicitly requiring weights on disk.

- [ ] **Step 2: Run lint**

Run:
```bash
cd sidequest-daemon && uv run ruff check sidequest_daemon/
```
Expected: no errors.

- [ ] **Step 3: Grep for residual Flux runtime references**

Run:
```bash
cd sidequest-daemon && grep -rn -i "flux" sidequest_daemon/ --include="*.py" | grep -v __pycache__ | grep -v "# " || echo "clean"
```
Expected: any remaining hits are in comments, docstrings, or logging strings — no live imports or identifiers.

- [ ] **Step 4: Manual smoke (optional but recommended)**

Start the daemon locally and confirm it loads Z-Image without erroring:

```bash
cd sidequest-daemon && uv run sidequest-renderer --warmup=flux 2>&1 | head -40
```

Wait — the `--warmup=flux` flag survives from the previous design, which is fine (the string "flux" is just a warmup selector value), but the daemon now loads Z-Image behind it. Confirm the warmup line logs the Z-Image span and exits cleanly with Ctrl-C.

- [ ] **Step 5: Push the branch**

```bash
cd sidequest-daemon && git push -u origin feat/zimage-renderer-swap
```

- [ ] **Step 6: Open PR against `develop`**

```bash
cd sidequest-daemon && gh pr create --base develop --title "feat(renderer): swap Flux for Z-Image Base 1.0, remove LoRA" --body "$(cat <<'EOF'
## Summary
- Replaces FluxMLXWorker with ZImageMLXWorker (mflux's Z-Image Base 1.0 pipeline)
- Removes all LoRA code paths from the daemon renderer
- Renames FLUX_TIERS → IMAGE_TIERS; factory now returns a SubprocessRenderer named "zimage"

Spec: docs/superpowers/specs/2026-04-22-zimage-renderer-design.md
Plan: docs/superpowers/plans/2026-04-22-zimage-renderer-swap.md

## Test plan
- [x] zimage_config covers every RenderTier value
- [x] zimage_mlx_worker unit tests (mocked model)
- [x] Factory wiring test returns a SubprocessRenderer named "zimage"
- [x] Full `uv run pytest` passes
- [ ] Manual: daemon boots, warms up Z-Image, renders a SCENE_ILLUSTRATION
EOF
)"
```

---

## Self-Review Checklist

Ran the three checks from the skill against the committed spec and this plan:

**Spec coverage:**
- AC1 "Daemon runs on Z-Image for all tiers" → Tasks 2, 3, 4, 9 Step 4.
- AC2 "Flux files + LoRA code/tests removed" → Task 7.
- AC3 "mflux pin bumped" → Task 1.
- AC4 "Factory returns SubprocessRenderer named 'zimage'" → Task 4 + wiring test in Task 8.
- AC5 "Integration test for SCENE_ILLUSTRATION round-trip" → Task 8 covers the factory wiring; full round-trip through daemon ↔ worker requires the model to be loaded and is validated manually in Task 9 Step 4. Unit + wiring tests cover everything below the weight-loading boundary; end-to-end with weights is deliberately kept as a manual smoke to avoid CI depending on a 20GB model download.
- AC6 "OTEL spans emitted" → Task 3 implements `zimage_mlx.load_model`, `zimage_mlx.warm_up`, `zimage_mlx.render` with tier/seed/width/height/steps/guidance/prompt_length/negative_length attributes.

**Placeholder scan:** None. No TBDs, no "handle edge cases," no "add appropriate error handling." Every code-generating step contains the full code.

**Type consistency:** `ZImageTierConfig` (dataclass, frozen, fields `steps/guidance/width/height`) is defined once in Task 2 and only referenced, not redefined, afterward. `ZImageMLXWorker.TIER_CONFIGS` uses its own `{steps, guidance, w, h}` dict shape — consistent with the flux worker it replaces (the worker subprocess duplicates the table because it cannot import from the main package; this constraint is documented in a module comment). `renderer_name="zimage"` appears everywhere it's referenced. `FLUX_TIERS` → `IMAGE_TIERS` rename is applied atomically in Task 5.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-22-zimage-renderer-swap.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
