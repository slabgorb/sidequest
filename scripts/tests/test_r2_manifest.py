"""RED tests for Story 65-1 Part A — r2_manifest.json writer.

Targets the not-yet-existing `scripts.r2_manifest` module and the Part A
integration into `scripts.r2_sync_packs.sync()`. All logic here is boto3-free
except the wiring test, which imports `sync` (boto3 added to dev deps).

Key conventions are derived from `r2_sync_packs.sync()`: the manifest key MUST
equal `rel.as_posix()` relative to content-root — the same string used as the
R2 object key. See sprint/context/context-story-65-1.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.r2_manifest import (
    build_manifest_entry,
    load_manifest,
    write_manifest,
)


def _make_media(content_root: Path, rel: str, data: bytes = b"hello") -> Path:
    p = content_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def _entry(key: str, md5: str = "0", size: int = 1) -> dict:
    return {
        "key": key,
        "md5": md5,
        "size_bytes": size,
        "uploaded_at": "2026-05-27T00:00:00Z",
        "source": "r2_sync_packs",
    }


# ── AC1: build_manifest_entry ────────────────────────────────────────────

def test_build_manifest_entry_has_all_required_fields(tmp_path: Path) -> None:
    p = _make_media(tmp_path, "genre_packs/g/audio/music/theme.ogg", b"abc")
    entry = build_manifest_entry(p, tmp_path)
    assert set(entry) >= {"key", "md5", "size_bytes", "uploaded_at", "source"}


def test_build_manifest_entry_md5_size_and_source(tmp_path: Path) -> None:
    p = _make_media(tmp_path, "genre_packs/g/audio/music/theme.ogg", b"abc")
    entry = build_manifest_entry(p, tmp_path)
    assert entry["md5"] == hashlib.md5(b"abc", usedforsecurity=False).hexdigest()
    assert entry["size_bytes"] == 3
    assert entry["source"] == "r2_sync_packs"


def test_build_manifest_entry_key_matches_sync_key(tmp_path: Path) -> None:
    # The manifest key must be the exact R2 key sync() uses: rel.as_posix().
    p = _make_media(tmp_path, "genre_packs/g/images/portraits/jane_doe.png")
    entry = build_manifest_entry(p, tmp_path)
    assert entry["key"] == p.relative_to(tmp_path).as_posix()


def test_build_manifest_entry_uploaded_at_is_iso8601(tmp_path: Path) -> None:
    p = _make_media(tmp_path, "genre_packs/g/audio/music/theme.ogg")
    entry = build_manifest_entry(p, tmp_path)
    # ISO-8601 has a 'T' date/time separator; round-trips through fromisoformat.
    from datetime import datetime

    assert "T" in entry["uploaded_at"]
    datetime.fromisoformat(entry["uploaded_at"].replace("Z", "+00:00"))


# ── AC1: write_manifest — sorted, pretty, atomic, idempotent ─────────────

def test_write_manifest_is_key_sorted(tmp_path: Path) -> None:
    out = tmp_path / "r2_manifest.json"
    write_manifest([_entry("b.png"), _entry("a.png")], out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [e["key"] for e in data] == ["a.png", "b.png"]


def test_write_manifest_is_pretty_printed(tmp_path: Path) -> None:
    out = tmp_path / "r2_manifest.json"
    write_manifest([_entry("a.png")], out)
    text = out.read_text(encoding="utf-8")
    assert "\n  " in text  # 2-space indent => newline + indentation present


def test_write_manifest_idempotent_byte_identical(tmp_path: Path) -> None:
    entries = [_entry("b.png"), _entry("a.png"), _entry("c.png")]
    out1 = tmp_path / "m1.json"
    out2 = tmp_path / "m2.json"
    write_manifest(entries, out1)
    write_manifest(list(reversed(entries)), out2)
    assert out1.read_bytes() == out2.read_bytes()


def test_write_manifest_leaves_no_temp_file(tmp_path: Path) -> None:
    # Atomic write: temp + os.replace must not leave partial/temp files behind.
    out = tmp_path / "r2_manifest.json"
    write_manifest([_entry("a.png")], out)
    leftovers = sorted(p.name for p in tmp_path.iterdir())
    assert leftovers == ["r2_manifest.json"]


def test_write_manifest_empty_list_is_valid(tmp_path: Path) -> None:
    out = tmp_path / "r2_manifest.json"
    write_manifest([], out)
    assert json.loads(out.read_text(encoding="utf-8")) == []


# ── AC1: load_manifest round-trip + loud failure ─────────────────────────

def test_load_manifest_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "r2_manifest.json"
    write_manifest([_entry("a.png"), _entry("b.png")], out)
    loaded = load_manifest(out)
    assert {e["key"] for e in loaded} == {"a.png", "b.png"}


def test_load_manifest_missing_file_raises(tmp_path: Path) -> None:
    # No silent fallback (CLAUDE.md): a missing manifest must fail loudly.
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "does_not_exist.json")


# ── AC4: wiring — sync() produces the manifest ───────────────────────────

def test_sync_dry_run_writes_manifest_one_entry_per_file(tmp_path: Path) -> None:
    """Part A must be reachable from the uploader, not just a standalone helper.

    Uses dry_run so no R2 client/network is needed. Asserts sync() emits a
    manifest whose keys are the 1:1 mirror of every candidate media file.
    """
    from scripts.r2_sync_packs import sync

    _make_media(tmp_path, "genre_packs/g/audio/music/theme.ogg", b"abc")
    _make_media(tmp_path, "genre_packs/g/images/portraits/jane.png", b"xyz")
    manifest = tmp_path / "r2_manifest.json"

    sync(tmp_path, dry_run=True, manifest_path=manifest)

    keys = {e["key"] for e in load_manifest(manifest)}
    assert keys == {
        "genre_packs/g/audio/music/theme.ogg",
        "genre_packs/g/images/portraits/jane.png",
    }
