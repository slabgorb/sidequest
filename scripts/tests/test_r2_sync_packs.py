"""Tests for r2_sync_packs path filtering and content-type mapping."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.r2_sync_packs import (
    LFS_EXTENSIONS,
    content_type_for,
    iter_media_files,
)


def test_lfs_extensions_match_gitattributes() -> None:
    expected = {".ogg", ".png", ".wav", ".mp3", ".jpg", ".jpeg", ".webp", ".flac"}
    assert LFS_EXTENSIONS == expected


def test_content_type_for_known_extensions() -> None:
    assert content_type_for(Path("a.ogg")) == "audio/ogg"
    assert content_type_for(Path("a.png")) == "image/png"
    assert content_type_for(Path("a.jpg")) == "image/jpeg"
    assert content_type_for(Path("a.jpeg")) == "image/jpeg"
    assert content_type_for(Path("a.webp")) == "image/webp"
    assert content_type_for(Path("a.mp3")) == "audio/mpeg"
    assert content_type_for(Path("a.wav")) == "audio/wav"
    assert content_type_for(Path("a.flac")) == "audio/flac"


def test_content_type_for_unknown_extension_raises() -> None:
    with pytest.raises(ValueError, match="unsupported extension"):
        content_type_for(Path("a.txt"))


def test_iter_media_files_skips_yaml_and_text(tmp_path: Path) -> None:
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "track.ogg").write_bytes(b"x")
    (tmp_path / "config.yaml").write_text("ok")
    (tmp_path / "README.md").write_text("ok")
    found = sorted(p.name for p in iter_media_files(tmp_path))
    assert found == ["track.ogg"]


def test_iter_media_files_recurses(tmp_path: Path) -> None:
    deep = tmp_path / "worlds" / "dungeon" / "audio" / "music"
    deep.mkdir(parents=True)
    (deep / "combat.ogg").write_bytes(b"x")
    (tmp_path / "portraits" / "hero.png").parent.mkdir(parents=True)
    (tmp_path / "portraits" / "hero.png").write_bytes(b"y")
    found = sorted(p.relative_to(tmp_path).as_posix() for p in iter_media_files(tmp_path))
    assert found == [
        "portraits/hero.png",
        "worlds/dungeon/audio/music/combat.ogg",
    ]
