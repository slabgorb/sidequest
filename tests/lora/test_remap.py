"""Tests for scripts.lora.remap_mlx_to_mflux.

Task 1.3 covers the "unknown MLX key → hard fail" path exclusively.
The happy-path translation and transpose handling land in Task 1.4
once Phase 0 observations (see
docs/superpowers/notes/2026-04-20-mlx-examples-flux-notes.md) fix the
real key patterns that feed the toy fixture.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts.lora.remap_mlx_to_mflux import RemapError, remap_npz_to_safetensors


def test_unknown_mlx_key_hard_fails(tmp_path: Path, sample_keymap_path: Path) -> None:
    npz_path = tmp_path / "has_unknown.npz"
    np.savez(
        npz_path,
        **{
            "completely.unknown.key.lora_A": np.zeros((4, 32), dtype=np.float32),
        },
    )
    out_path = tmp_path / "out.safetensors"

    with pytest.raises(RemapError) as exc_info:
        remap_npz_to_safetensors(
            input_path=npz_path,
            output_path=out_path,
            keymap_path=sample_keymap_path,
        )

    assert "completely.unknown.key.lora_A" in str(exc_info.value)
    assert not out_path.exists(), "must not write partial output on failure"
