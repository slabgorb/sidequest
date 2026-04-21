"""Shared fixtures for LoRA pipeline tests.

Phase 0 observations (docs/superpowers/notes/2026-04-20-mlx-examples-flux-notes.md)
established that mlx-examples outputs `.safetensors`, not `.npz`. These
fixtures therefore build safetensors inputs. Real MLX key patterns are
used, with small dimensions (rank 4, hidden 32 instead of 3072) so tests
run fast.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import torch
from safetensors.torch import save_file


@pytest.fixture
def toy_safetensors_path(tmp_path: Path) -> Path:
    """Write a minimal synthetic MLX-native Flux LoRA safetensors.

    Contains one double-block and one single-block module pair so both
    keymap patterns and the transpose helper are exercised. Shapes are
    tiny (hidden 32, rank 4) relative to real Flux (hidden 3072), purely
    for test speed. The name patterns are exactly those observed in Phase 0.
    """
    path = tmp_path / "toy_adapters.safetensors"
    hidden = 32
    rank = 4
    data: dict[str, torch.Tensor] = {
        # MLX shape convention: lora_a = (input_dim, rank), lora_b = (rank, output_dim)
        "double_blocks.0.img_attn.proj.lora_a": torch.randn(hidden, rank),
        "double_blocks.0.img_attn.proj.lora_b": torch.randn(rank, hidden),
        "single_blocks.0.linear1.lora_a": torch.randn(hidden, rank),
        "single_blocks.0.linear1.lora_b": torch.randn(rank, hidden * 3),
    }
    save_file(data, str(path))
    return path


@pytest.fixture
def empty_keymap_path(tmp_path: Path) -> Path:
    """Keymap YAML with zero rules.

    Used by tests that check the remapper's unknown-key failure
    behaviour — every input key is trivially unmapped.
    """
    path = tmp_path / "empty_keymap.yaml"
    path.write_text(
        "version: 1\n"
        "rules: []\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def real_keymap_path() -> Path:
    """Path to the production keymap shipped in scripts/lora/.

    Task 1.4's happy-path tests use this rather than a handwritten
    fixture copy, so any drift in the real keymap is caught by the
    same tests that exercise the remapper.
    """
    return Path(__file__).resolve().parents[2] / "scripts" / "lora" / "mlx_to_mflux_keymap.yaml"
