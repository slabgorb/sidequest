"""Tests for scripts.lora.remap_mlx_to_mflux.

Tasks covered here:
  - 1.3: unknown-key hard-fail
  - 1.4: happy-path translation + transpose + safetensors output

Phase 0 established the real format is safetensors, not .npz. The old
np.savez-based fixtures and tests have been migrated to safetensors.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import torch
from safetensors import safe_open
from safetensors.torch import save_file

from scripts.lora.remap_mlx_to_mflux import RemapError, remap_mlx_safetensors


# ─── Task 1.3: unknown-key hard-fail ────────────────────────────────────


def test_unknown_mlx_key_hard_fails(tmp_path: Path, empty_keymap_path: Path) -> None:
    """An input key that matches no keymap rule raises RemapError, no output written."""
    input_path = tmp_path / "has_unknown.safetensors"
    save_file(
        {"completely.unknown.key.lora_a": torch.zeros(4, 32)},
        str(input_path),
    )
    out_path = tmp_path / "out.safetensors"

    with pytest.raises(RemapError) as exc_info:
        remap_mlx_safetensors(
            input_path=input_path,
            output_path=out_path,
            keymap_path=empty_keymap_path,
        )

    assert "completely.unknown.key.lora_a" in str(exc_info.value)
    assert not out_path.exists(), "must not write partial output on failure"


# ─── Task 1.4: happy-path translation ───────────────────────────────────


def test_happy_path_translates_known_keys(
    tmp_path: Path, toy_safetensors_path: Path, real_keymap_path: Path
) -> None:
    """All four toy MLX keys translate to correctly-named Kohya keys."""
    out_path = tmp_path / "kohya.safetensors"

    summary = remap_mlx_safetensors(
        input_path=toy_safetensors_path,
        output_path=out_path,
        keymap_path=real_keymap_path,
    )

    assert summary["translated"] == 4
    assert summary["rank"] == 4
    assert out_path.exists()

    with safe_open(str(out_path), framework="pt") as f:
        keys = sorted(f.keys())

    assert keys == [
        "lora_unet_double_blocks_0_img_attn_proj.lora_down.weight",
        "lora_unet_double_blocks_0_img_attn_proj.lora_up.weight",
        "lora_unet_single_blocks_0_linear1.lora_down.weight",
        "lora_unet_single_blocks_0_linear1.lora_up.weight",
    ]


# ─── Task 1.4: transpose correctness ────────────────────────────────────


def test_transpose_flips_axes(tmp_path: Path, real_keymap_path: Path) -> None:
    """MLX (input, rank) → Kohya (rank, input); axes [0, 1] swap."""
    in_path = tmp_path / "tiny.safetensors"
    # A lora_a with distinguishable axes so we can see the swap.
    original = torch.arange(12, dtype=torch.float32).reshape(3, 4)   # MLX: (input=3, rank=4)
    save_file({"double_blocks.0.img_attn.proj.lora_a": original}, str(in_path))

    out_path = tmp_path / "out.safetensors"
    remap_mlx_safetensors(
        input_path=in_path,
        output_path=out_path,
        keymap_path=real_keymap_path,
    )

    with safe_open(str(out_path), framework="pt") as f:
        kohya = f.get_tensor("lora_unet_double_blocks_0_img_attn_proj.lora_down.weight")

    assert tuple(kohya.shape) == (4, 3), "Kohya lora_down expects (rank, input_dim)"
    # Verify values too — a transpose preserves the data, just flips axes.
    assert torch.equal(kohya, original.transpose(0, 1))


# ─── Task 1.5 fix: replicate fused-QKV down for mflux's BFL slicer ──────


def test_fused_qkv_down_is_replicated_three_times(
    tmp_path: Path, real_keymap_path: Path
) -> None:
    """double_blocks.*.img_attn.qkv.lora_a must tile ×3 along rank axis.

    mflux's BFL loader splits the down rank-axis into Q/K/V chunks; mlx
    trains it as a single shared rank-r down. Tiling ×3 means each chunk
    mflux extracts equals the original transposed D — mathematically the
    same delta as the fused mlx form.
    """
    in_path = tmp_path / "fused.safetensors"
    original = torch.randn(32, 4)   # MLX: (input=32, rank=4)
    save_file({"double_blocks.0.img_attn.qkv.lora_a": original}, str(in_path))

    out_path = tmp_path / "out.safetensors"
    remap_mlx_safetensors(
        input_path=in_path,
        output_path=out_path,
        keymap_path=real_keymap_path,
    )

    with safe_open(str(out_path), framework="pt") as f:
        kohya = f.get_tensor("lora_unet_double_blocks_0_img_attn_qkv.lora_down.weight")

    assert tuple(kohya.shape) == (12, 32), "rank-axis must be tiled to 3×r=12"
    # Each rank-r chunk must be identical to the original transposed D.
    chunk_q = kohya[0:4, :]
    chunk_k = kohya[4:8, :]
    chunk_v = kohya[8:12, :]
    expected = original.transpose(0, 1)
    assert torch.equal(chunk_q, expected)
    assert torch.equal(chunk_k, expected)
    assert torch.equal(chunk_v, expected)


def test_single_linear1_down_is_replicated_four_times(
    tmp_path: Path, real_keymap_path: Path
) -> None:
    """single_blocks.*.linear1.lora_a must tile ×4 (Q/K/V/MLP) along rank axis."""
    in_path = tmp_path / "fused_single.safetensors"
    original = torch.randn(32, 4)   # MLX: (input=32, rank=4)
    save_file({"single_blocks.0.linear1.lora_a": original}, str(in_path))

    out_path = tmp_path / "out.safetensors"
    summary = remap_mlx_safetensors(
        input_path=in_path,
        output_path=out_path,
        keymap_path=real_keymap_path,
    )

    assert summary["rank"] == 4, "summary should report SOURCE rank, not tiled rank"

    with safe_open(str(out_path), framework="pt") as f:
        kohya = f.get_tensor("lora_unet_single_blocks_0_linear1.lora_down.weight")

    assert tuple(kohya.shape) == (16, 32), "rank-axis must be tiled to 4×r=16"
    expected = original.transpose(0, 1)
    for i in range(4):
        assert torch.equal(kohya[i * 4:(i + 1) * 4, :], expected)
