"""Story 65-1 Part A — r2_manifest.json build/write/load.

A committed record of every binary uploaded to R2. R2 mirrors local paths 1:1,
so each entry's ``key`` is the file's path relative to ``content_root`` — the
exact object key ``r2_sync_packs.sync()`` uploads under.

Boto3-free by design: this module holds the pure manifest logic so it tests
without AWS deps. ``r2_sync_packs`` imports it to emit the manifest after a
sync. Per CLAUDE.md (no silent fallbacks) a missing manifest fails loudly.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Matches r2_sync_packs.sync()'s ``source`` attribution.
SOURCE = "r2_sync_packs"


def _md5_of(path: Path) -> str:
    """MD5 of a file, streamed in 1 MiB chunks (mirrors r2_sync_packs)."""
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest_entry(path: Path, content_root: Path) -> dict[str, object]:
    """Build one manifest entry for ``path``, keyed relative to ``content_root``.

    The ``key`` equals ``rel.as_posix()`` — identical to the R2 object key
    ``sync()`` uses — so the manifest and R2 stay in lockstep.
    """
    path = Path(path)
    content_root = Path(content_root)
    rel = path.resolve().relative_to(content_root.resolve())
    return {
        "key": rel.as_posix(),
        "md5": _md5_of(path),
        "size_bytes": path.stat().st_size,
        "uploaded_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": SOURCE,
    }


def write_manifest(entries: list[dict[str, object]], path: Path) -> None:
    """Write the manifest: key-sorted, pretty (2-space), atomic.

    Sorting by ``key`` (and ``sort_keys`` within each entry) keeps git diffs
    stable across runs. The write is atomic — a temp file is fully written then
    ``os.replace``d into place, so an interrupt never leaves a partial manifest.
    """
    path = Path(path)
    ordered = sorted(entries, key=lambda e: e["key"])
    text = json.dumps(ordered, indent=2, sort_keys=True) + "\n"
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_manifest(path: Path) -> list[dict[str, object]]:
    """Load a manifest. Raises ``FileNotFoundError`` if absent (no fallback)."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
