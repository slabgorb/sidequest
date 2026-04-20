"""Wrapper around mlx-examples/flux/ LoRA training.

Task 2.1 scope: preflight (dataset validation) only.
The subprocess invocation (CLI driver + `build_training_command`) lands
when Task 2.3 kicks off the first real overnight training run and
needs the full pipeline end-to-end.
"""
from __future__ import annotations

from pathlib import Path


MIN_IMAGES = 150
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


class PreflightError(RuntimeError):
    """Raised when the dataset can't be used for training."""


def preflight_dataset(dataset_dir: Path) -> dict[str, int]:
    """Validate a LoRA training dataset before spawning the trainer.

    Rules:
      - Directory must exist.
      - Every image (.jpg/.jpeg/.png) must have a same-stem .txt caption.
      - At least MIN_IMAGES paired entries (matches /sq-lora Step 3 floor).

    Returns {'images': N, 'captions': N} on success. Raises PreflightError
    with a diagnostic message otherwise.
    """
    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise PreflightError(f"Dataset directory does not exist: {dataset_dir}")

    images = sorted(p for p in dataset_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    caption_stems = {p.stem for p in dataset_dir.iterdir() if p.suffix.lower() == ".txt"}

    unpaired = [p.name for p in images if p.stem not in caption_stems]
    if unpaired:
        summary = ", ".join(unpaired[:5])
        if len(unpaired) > 5:
            summary += f" ... (+{len(unpaired) - 5} more)"
        raise PreflightError(
            f"Images without paired .txt captions (unpaired): {summary}"
        )

    if len(images) < MIN_IMAGES:
        raise PreflightError(
            f"Dataset has {len(images)} images; minimum {MIN_IMAGES} required. "
            f"See /sq-lora Step 3 assessment gate."
        )

    return {"images": len(images), "captions": len(caption_stems)}
