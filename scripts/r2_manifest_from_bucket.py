"""Rebuild ``r2_manifest.json`` from a live R2 bucket scan.

``r2_manifest.py`` (boto3-free) builds entries from *local* files, and
``r2_sync_packs.py --manifest`` only records the files a sync actually
touched. Neither can capture objects that live on R2 but were never on this
clone's disk (e.g. a world rendered on another machine and uploaded there).
This script closes that gap: it LISTs the bucket and writes one manifest entry
per live object, so the committed manifest mirrors R2 exactly.

This is the tool behind the ``source: "r2_bucket_scan"`` entries already in the
manifest. Object ``md5`` is the R2 ETag (quotes stripped) — identical to what
``r2_sync_packs`` compares against for change detection. Multipart-uploaded
objects carry a compound ETag (``<hash>-<parts>``) that is not a plain MD5;
those are recorded verbatim (they are still R2's content identifier) and
counted separately so the operator knows.

Per CLAUDE.md (No Silent Fallbacks): missing R2 creds raise (KeyError) rather
than silently producing an empty manifest, and an empty bucket is reported, not
written over a populated manifest without notice.

Usage:
    uv run --project . python scripts/r2_manifest_from_bucket.py
    uv run --project . python scripts/r2_manifest_from_bucket.py --dry-run
    uv run --project . python scripts/r2_manifest_from_bucket.py --prefix genre_packs/
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from scripts.r2_manifest import write_manifest
from scripts.r2_sync_packs import _build_client

log = logging.getLogger("r2_manifest_from_bucket")

SOURCE = "r2_bucket_scan"


def scan_bucket(bucket: str, prefix: str) -> list[dict[str, object]]:
    """Return one manifest entry per live R2 object under ``prefix``.

    Entry schema matches ``r2_manifest.build_manifest_entry``:
    ``key``, ``md5``, ``size_bytes``, ``source``, ``uploaded_at``.
    """
    client = _build_client()
    entries: list[dict[str, object]] = []
    multipart = 0
    for page in client.get_paginator("list_objects_v2").paginate(
        Bucket=bucket, Prefix=prefix
    ):
        for obj in page.get("Contents", []):
            etag = obj["ETag"].strip('"')
            if "-" in etag:
                multipart += 1
            entries.append(
                {
                    "key": obj["Key"],
                    "md5": etag,
                    "size_bytes": obj["Size"],
                    "source": SOURCE,
                    "uploaded_at": obj["LastModified"]
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z"),
                }
            )
    if multipart:
        log.warning(
            "%d object(s) have multipart ETags (not plain MD5); recorded verbatim",
            multipart,
        )
    return entries


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="sidequest")
    parser.add_argument("--prefix", default="genre_packs/")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=repo_root / "sidequest-content" / "r2_manifest.json",
        help="Path to r2_manifest.json (default: <repo>/sidequest-content/r2_manifest.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts without writing the manifest.",
    )
    args = parser.parse_args()

    entries = scan_bucket(args.bucket, args.prefix)
    log.info(
        "scanned bucket=%s prefix=%s -> %d objects", args.bucket, args.prefix, len(entries)
    )
    if not entries:
        # Loud, not silent: refuse to clobber a populated manifest with nothing.
        raise SystemExit(
            f"bucket scan returned 0 objects under prefix {args.prefix!r} — refusing to "
            "overwrite the manifest (No Silent Fallbacks)"
        )

    if args.dry_run:
        log.info("DRY-RUN: would write %d entries to %s", len(entries), args.manifest)
        return 0

    write_manifest(entries, args.manifest)
    log.info("wrote %d entries to %s", len(entries), args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
