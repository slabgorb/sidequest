"""Translate mlx-examples Flux LoRA safetensors → Kohya-convention safetensors.

The output is consumable by mflux's `Flux1(lora_paths=[...])` without
further conversion. Hard-fails on any source key without a keymap rule
(no silent drops — per the project's no-silent-fallback discipline).

Format note: Phase 0 observation
(docs/superpowers/notes/2026-04-20-mlx-examples-flux-notes.md) confirmed
mlx-examples outputs .safetensors directly. Earlier plan versions
referenced .npz; that was incorrect and has been corrected here.

MLX shape convention:
    lora_a : (input_dim, rank)
    lora_b : (rank, output_dim)

Kohya/mflux shape convention:
    lora_down.weight : (rank, input_dim)
    lora_up.weight   : (output_dim, rank)

Every keymap rule sets `transpose: true` to flip axes [0, 1]. Some rules
also set `replicate: N` (default 1) for fused-QKV / Q+K+V+MLP layers —
mflux's BFL loader splits the down matrix into N rank-chunks, so we must
hand it a pre-stacked (N×r, in) tensor by tiling the original (r, in)
shared down N times along axis 0. Without this, mflux extracts a rank=1
slice from a rank=4 down and the runtime matmul fails on shape mismatch
(the silent-fallback Task 1.5's roundtrip test was built to detect).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from safetensors import safe_open
from safetensors.torch import save_file


class RemapError(RuntimeError):
    """Raised when remapping cannot complete correctly."""


def _load_keymap(keymap_path: Path) -> list[dict[str, Any]]:
    with keymap_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    rules = data.get("rules") or []
    compiled: list[dict[str, Any]] = []
    for rule in rules:
        replicate = int(rule.get("replicate", 1))
        if replicate < 1:
            raise RemapError(f"rule '{rule['name']}': replicate must be >= 1")
        compiled.append(
            {
                "name": rule["name"],
                "mlx_re": re.compile(rule["mlx_pattern"]),
                "kohya_template": rule["kohya_pattern"],
                "transpose": bool(rule.get("transpose", False)),
                "replicate": replicate,
            }
        )
    return compiled


def _match_rule(
    key: str, rules: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, str]] | None:
    for rule in rules:
        m = rule["mlx_re"].match(key)
        if m is not None:
            return rule, m.groupdict()
    return None


def remap_mlx_safetensors(
    input_path: Path,
    output_path: Path,
    keymap_path: Path,
) -> dict[str, int]:
    """Remap MLX LoRA weights into mflux-compatible safetensors.

    Raises RemapError on any unmapped MLX key. Does not write output
    when unknown keys are present — partial remaps are never shipped.

    Returns a summary dict with translated count and rank estimate.
    """
    rules = _load_keymap(keymap_path)

    translated: dict = {}
    unknown: list[str] = []
    source_rank: int | None = None

    with safe_open(str(input_path), framework="pt") as f:
        for key in f.keys():
            matched = _match_rule(key, rules)
            if matched is None:
                unknown.append(key)
                continue
            rule, groups = matched
            tensor = f.get_tensor(key)
            # Capture rank from any lora_a (mlx layout (input, rank)) before
            # any reshape, so it survives downstream replication.
            if source_rank is None and key.endswith(".lora_a"):
                source_rank = int(min(tensor.shape))
            if rule["transpose"]:
                tensor = tensor.transpose(0, 1).contiguous()
            if rule["replicate"] > 1:
                tensor = tensor.repeat(rule["replicate"], 1).contiguous()
            new_key = rule["kohya_template"].format(**groups)
            translated[new_key] = tensor

    if unknown:
        raise RemapError(
            "Unmapped MLX keys — extend scripts/lora/mlx_to_mflux_keymap.yaml:\n  "
            + "\n  ".join(unknown)
        )

    save_file(translated, str(output_path))
    return {"translated": len(translated), "rank": source_rank or 0}


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keymap", required=True, type=Path)
    args = parser.parse_args()

    summary = remap_mlx_safetensors(args.input, args.output, args.keymap)
    print(f"Remap OK: {summary['translated']} keys translated, rank={summary['rank']}")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
