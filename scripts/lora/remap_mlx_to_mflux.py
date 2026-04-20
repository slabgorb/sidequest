"""Translate mlx-examples Flux LoRA .npz → Kohya-convention .safetensors.

The output is consumable by mflux's `Flux1(lora_paths=[...])` without
further conversion. Hard-fails on any source key without a keymap rule
(no silent drops — per the project's no-silent-fallback discipline).

Task 1.3 implements the unknown-key hard-fail path. The happy-path
translation + safetensors write lands in Task 1.4 once Phase 0
observations (docs/superpowers/notes/2026-04-20-mlx-examples-flux-notes.md)
fix the real MLX key patterns the keymap must cover.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml


class RemapError(RuntimeError):
    """Raised when remapping cannot complete correctly."""


def _load_keymap(keymap_path: Path) -> list[dict[str, Any]]:
    with keymap_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    rules = data.get("rules") or []
    compiled: list[dict[str, Any]] = []
    for rule in rules:
        compiled.append(
            {
                "name": rule["name"],
                "mlx_re": re.compile(rule["mlx_pattern"]),
                "kohya_template": rule["kohya_pattern"],
                "transpose": bool(rule.get("transpose", False)),
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


def remap_npz_to_safetensors(
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
    npz = np.load(input_path)

    unknown: list[str] = []
    for key in npz.files:
        if _match_rule(key, rules) is None:
            unknown.append(key)

    if unknown:
        raise RemapError(
            "Unmapped MLX keys — extend scripts/lora/mlx_to_mflux_keymap.yaml:\n  "
            + "\n  ".join(unknown)
        )

    # Happy-path translation + safetensors write is implemented by Task 1.4.
    # We only reach this line when every key matched a rule, which Task 1.3's
    # test never exercises. Task 1.4 replaces this raise with the real logic.
    raise NotImplementedError(
        "Happy-path remap not yet implemented — awaits Task 1.4 + Phase 0 keymap data."
    )


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keymap", required=True, type=Path)
    args = parser.parse_args()

    summary = remap_npz_to_safetensors(args.input, args.output, args.keymap)
    print(f"Remap OK: {summary['translated']} keys translated, rank={summary['rank']}")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
