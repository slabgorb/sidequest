"""Tests for scripts.lora.train.preflight_dataset.

Task 2.1 covers the preflight (dataset validation) path only. The
actual training invocation (subprocess of mlx-examples/flux/ trainer)
lives behind a _cli() driver that is added when Task 2.3 exercises it
end-to-end against a real dataset.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lora.train import PreflightError, preflight_dataset


def test_preflight_rejects_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(PreflightError, match="does not exist"):
        preflight_dataset(tmp_path / "missing")


def test_preflight_rejects_unpaired_files(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"fake-jpg")
    (tmp_path / "b.jpg").write_bytes(b"fake-jpg")
    (tmp_path / "a.txt").write_text("caption a")
    # b.txt deliberately missing
    with pytest.raises(PreflightError, match="unpaired"):
        preflight_dataset(tmp_path)


def test_preflight_rejects_low_volume(tmp_path: Path) -> None:
    # 10 pairs — well below the 150 floor.
    for i in range(10):
        (tmp_path / f"{i}.jpg").write_bytes(b"fake")
        (tmp_path / f"{i}.txt").write_text(f"caption {i}")
    with pytest.raises(PreflightError, match="150"):
        preflight_dataset(tmp_path)


def test_preflight_passes_on_valid_dataset(tmp_path: Path) -> None:
    for i in range(150):
        (tmp_path / f"{i}.jpg").write_bytes(b"fake")
        (tmp_path / f"{i}.txt").write_text(f"caption {i}")
    summary = preflight_dataset(tmp_path)
    assert summary["images"] == 150
    assert summary["captions"] == 150
