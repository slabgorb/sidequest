"""Tests for scripts.r2_manifest_from_bucket — live-R2-scan manifest rebuild.

Network-free: the boto3 client (``_build_client``) is monkeypatched with a fake
whose paginator yields canned ``list_objects_v2`` pages. Schema parity with
``r2_manifest.build_manifest_entry`` (key/md5/size_bytes/source/uploaded_at) is
asserted directly so this script's output drops into the same manifest the
other writers produce.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import r2_manifest_from_bucket as mfb


class _FakePaginator:
    def __init__(self, pages: list[dict]) -> None:
        self._pages = pages

    def paginate(self, **_kwargs):  # noqa: ANN003 - mirrors boto3 signature
        return iter(self._pages)


class _FakeClient:
    def __init__(self, pages: list[dict]) -> None:
        self._pages = pages

    def get_paginator(self, name: str) -> _FakePaginator:
        assert name == "list_objects_v2"
        return _FakePaginator(self._pages)


def _obj(key: str, etag: str = "abc123", size: int = 7) -> dict:
    return {
        "Key": key,
        "ETag": f'"{etag}"',
        "Size": size,
        "LastModified": datetime(2026, 5, 27, 1, 2, 3, tzinfo=timezone.utc),
    }


def _patch_client(monkeypatch: pytest.MonkeyPatch, pages: list[dict]) -> None:
    monkeypatch.setattr(mfb, "_build_client", lambda: _FakeClient(pages))


# ── scan_bucket: schema + field derivation ──────────────────────────────

def test_scan_bucket_entry_has_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, [{"Contents": [_obj("genre_packs/g/audio/music/x.ogg")]}])
    entry = mfb.scan_bucket("sidequest", "genre_packs/")[0]
    assert set(entry) >= {"key", "md5", "size_bytes", "source", "uploaded_at"}


def test_scan_bucket_md5_is_etag_without_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, [{"Contents": [_obj("k.png", etag="deadbeef")]}])
    assert mfb.scan_bucket("sidequest", "genre_packs/")[0]["md5"] == "deadbeef"


def test_scan_bucket_source_is_bucket_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, [{"Contents": [_obj("k.png")]}])
    assert mfb.scan_bucket("sidequest", "genre_packs/")[0]["source"] == "r2_bucket_scan"


def test_scan_bucket_size_from_object(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, [{"Contents": [_obj("k.png", size=4242)]}])
    assert mfb.scan_bucket("sidequest", "genre_packs/")[0]["size_bytes"] == 4242


def test_scan_bucket_uploaded_at_is_iso8601_z(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, [{"Contents": [_obj("k.png")]}])
    uploaded = mfb.scan_bucket("sidequest", "genre_packs/")[0]["uploaded_at"]
    assert uploaded == "2026-05-27T01:02:03Z"
    datetime.fromisoformat(uploaded.replace("Z", "+00:00"))  # round-trips


def test_scan_bucket_paginates_multiple_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(
        monkeypatch,
        [
            {"Contents": [_obj("a.png"), _obj("b.png")]},
            {"Contents": [_obj("c.png")]},
            {},  # empty trailing page must not break iteration
        ],
    )
    keys = {e["key"] for e in mfb.scan_bucket("sidequest", "genre_packs/")}
    assert keys == {"a.png", "b.png", "c.png"}


def test_scan_bucket_records_multipart_etag_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    # Multipart uploads carry a compound ETag (<hash>-<parts>); recorded as-is.
    _patch_client(monkeypatch, [{"Contents": [_obj("big.png", etag="abc123-4")]}])
    assert mfb.scan_bucket("sidequest", "genre_packs/")[0]["md5"] == "abc123-4"


# ── main(): wiring + No-Silent-Fallbacks guard ──────────────────────────

def test_main_writes_manifest_via_writer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """main() must route the scan through write_manifest to the target path."""
    _patch_client(
        monkeypatch,
        [{"Contents": [_obj("genre_packs/g/audio/music/x.ogg"), _obj("genre_packs/g/p.png")]}],
    )
    out = tmp_path / "r2_manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        ["r2_manifest_from_bucket.py", "--manifest", str(out)],
    )
    assert mfb.main() == 0
    keys = {e["key"] for e in json.loads(out.read_text(encoding="utf-8"))}
    assert keys == {"genre_packs/g/audio/music/x.ogg", "genre_packs/g/p.png"}


def test_main_empty_bucket_refuses_to_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # No Silent Fallbacks: an empty scan must not clobber the manifest.
    _patch_client(monkeypatch, [{}])
    out = tmp_path / "r2_manifest.json"
    out.write_text('[{"key": "keep.png"}]', encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["r2_manifest_from_bucket.py", "--manifest", str(out)],
    )
    with pytest.raises(SystemExit):
        mfb.main()
    # Original manifest untouched.
    assert json.loads(out.read_text(encoding="utf-8")) == [{"key": "keep.png"}]


def test_main_dry_run_does_not_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_client(monkeypatch, [{"Contents": [_obj("genre_packs/g/p.png")]}])
    out = tmp_path / "r2_manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        ["r2_manifest_from_bucket.py", "--manifest", str(out), "--dry-run"],
    )
    assert mfb.main() == 0
    assert not out.exists()
