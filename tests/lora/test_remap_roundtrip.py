"""Phase 1 Task 1.5: end-to-end remapper proof against the real daemon.

Takes the Phase 0 toy artifact (`~/mlx-toy-lora/final_adapters.safetensors`),
runs it through the remapper to produce a Kohya-convention safetensors,
then renders the same (prompt, seed) with and without that LoRA via the
live daemon. Asserts the two renders differ at the pixel level — if they
don't, the remapper/mflux pipeline is silently dropping the LoRA and the
whole Phase 1 chain is invalid.

This is the canonical silent-fallback detector. It is slow (~3 min) and
requires the daemon running at /tmp/sidequest-renderer.sock. Marked as
`slow` so fast CI can skip it.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytestmark = pytest.mark.slow


TOY_SAFETENSORS = Path.home() / "mlx-toy-lora" / "final_adapters.safetensors"
DAEMON_SOCK = Path("/tmp/sidequest-renderer.sock")


@pytest.mark.skipif(not TOY_SAFETENSORS.exists(), reason="Phase 0 toy artifact not produced")
@pytest.mark.skipif(not DAEMON_SOCK.exists(), reason="daemon not running (start via `just daemon-run`)")
def test_toy_lora_renders_differently_from_baseline(tmp_path: Path) -> None:
    from scripts.lora.remap_mlx_to_mflux import remap_mlx_safetensors
    from scripts.render_common import send_render

    remapped = tmp_path / "toy_kohya.safetensors"
    remap_mlx_safetensors(
        input_path=TOY_SAFETENSORS,
        output_path=remapped,
        keymap_path=Path(__file__).resolve().parents[2] / "scripts" / "lora" / "mlx_to_mflux_keymap.yaml",
    )
    assert remapped.stat().st_size > 0, "remap produced empty output"

    base_png = tmp_path / "baseline.png"
    lora_png = tmp_path / "with_lora.png"

    async def _render(lora_path: str | None, out: Path) -> None:
        params: dict = dict(
            tier="landscape",
            positive="a stone courtyard at midday",
            clip="a stone courtyard at midday",
            negative="",
            seed=424242,
            steps=8,   # minimum useful: we need *difference*, not quality
        )
        if lora_path is not None:
            params["lora_paths"] = [lora_path]
            params["lora_scales"] = [1.0]
        result = await send_render(**params)
        assert "error" not in result, f"daemon returned error: {result}"
        rendered = Path(result["result"].get("image_path") or result["result"]["image_url"])
        out.write_bytes(rendered.read_bytes())

    asyncio.run(_render(None, base_png))
    asyncio.run(_render(str(remapped), lora_png))

    a = np.array(Image.open(base_png).convert("RGB"))
    b = np.array(Image.open(lora_png).convert("RGB"))
    assert a.shape == b.shape, f"shape mismatch {a.shape} vs {b.shape}"
    diff_frac = float((a != b).any(axis=-1).mean())
    assert diff_frac > 0.001, (
        f"Remapped LoRA produced near-identical output to baseline "
        f"({diff_frac:.6f} fraction of pixels differ). "
        f"This is the silent-fallback the whole pipeline exists to prevent."
    )
