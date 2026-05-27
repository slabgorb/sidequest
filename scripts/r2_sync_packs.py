"""Phase A — sync sidequest-content/genre_packs/ into R2.

Walks the local content tree, uploads every LFS-tracked binary to R2 under
the same relative path, and is idempotent across re-runs (compares local MD5
to remote ETag and skips matches).

Per CLAUDE.md no-silent-fallbacks rule: any HTTP error aborts the run.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from scripts.r2_manifest import _md5_of, build_manifest_entry, write_manifest

LFS_EXTENSIONS: frozenset[str] = frozenset(
    {".ogg", ".png", ".wav", ".mp3", ".jpg", ".jpeg", ".webp", ".flac"}
)

_CONTENT_TYPES: dict[str, str] = {
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

CACHE_CONTROL_IMMUTABLE = "public, max-age=31536000, immutable"

logger = logging.getLogger("r2_sync_packs")


def content_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in _CONTENT_TYPES:
        raise ValueError(f"unsupported extension: {ext}")
    return _CONTENT_TYPES[ext]


def iter_media_files(root: Path) -> Iterator[Path]:
    """Yield all LFS-tracked media files under root, recursively."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in LFS_EXTENSIONS:
            continue
        yield path


def _remote_etag(client: BaseClient, bucket: str, key: str) -> str | None:
    try:
        resp = client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    etag = resp.get("ETag", "").strip('"')
    return etag or None


def _build_client() -> BaseClient:
    endpoint = os.environ["R2_S3_ENDPOINT"]
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def sync(
    content_root: Path,
    bucket: str = "sidequest",
    dry_run: bool = False,
    files: list[Path] | None = None,
    manifest_path: Path | None = None,
) -> dict[str, int]:
    """Upload LFS-tracked media to R2. Returns counts.

    By default walks ``content_root/genre_packs`` and uploads every tracked
    file. If ``files`` is given, only those paths are uploaded (still keyed by
    their location relative to ``content_root``) — every file must be a real,
    LFS-tracked media file under ``content_root`` or the run aborts (no silent
    skip, per CLAUDE.md).

    If ``manifest_path`` is given, a committed-style manifest (one entry per
    candidate file, keyed by its R2 key) is written atomically after the run —
    even on a ``dry_run`` so the manifest can be regenerated without uploading.
    See Story 65-1 / scripts/r2_manifest.py.
    """
    content_root = content_root.resolve()
    if not (content_root / "genre_packs").is_dir():
        raise FileNotFoundError(f"genre_packs/ not found under {content_root}")

    if files is None:
        candidates: list[Path] = list(iter_media_files(content_root / "genre_packs"))
    else:
        candidates = []
        for raw in files:
            path = (raw if raw.is_absolute() else content_root / raw).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"--files entry not found: {raw}")
            if path.suffix.lower() not in LFS_EXTENSIONS:
                raise ValueError(f"--files entry is not a tracked media type: {raw}")
            try:
                path.relative_to(content_root.resolve())
            except ValueError as exc:
                raise ValueError(f"--files entry is outside content-root: {raw}") from exc
            candidates.append(path)

    client = None if dry_run else _build_client()
    skipped = 0
    uploaded = 0
    bytes_uploaded = 0
    manifest_entries: list[dict[str, object]] = []

    for path in candidates:
        rel = path.relative_to(content_root.resolve()).as_posix()
        key = rel  # 1:1 mirror, e.g. genre_packs/<genre>/audio/<f>.ogg
        size = path.stat().st_size
        local_md5 = _md5_of(path)
        if manifest_path is not None:
            manifest_entries.append(build_manifest_entry(path, content_root))

        if dry_run:
            logger.info("DRY would upload key=%s size=%d md5=%s", key, size, local_md5)
            uploaded += 1
            bytes_uploaded += size
            continue

        assert client is not None
        remote = _remote_etag(client, bucket, key)
        if remote == local_md5:
            logger.info("SKIP key=%s (matches remote)", key)
            skipped += 1
            continue

        ctype = content_type_for(path)
        with path.open("rb") as f:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=f,
                ContentType=ctype,
                CacheControl=CACHE_CONTROL_IMMUTABLE,
            )
        logger.info(
            "PUT key=%s size=%d ctype=%s md5=%s", key, size, ctype, local_md5
        )
        uploaded += 1
        bytes_uploaded += size

    if manifest_path is not None:
        write_manifest(manifest_entries, manifest_path)

    return {"uploaded": uploaded, "skipped": skipped, "bytes_uploaded": bytes_uploaded}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--content-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sidequest-content",
        help="Path to sidequest-content checkout",
    )
    parser.add_argument("--bucket", default="sidequest")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--files",
        type=Path,
        nargs="+",
        default=None,
        help=(
            "Upload only these files instead of walking the whole tree. "
            "Paths may be absolute or relative to --content-root; each must be "
            "a tracked media type under --content-root."
        ),
    )
    parser.add_argument("--log-file", type=Path, default=Path("/tmp/r2-sync.log"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "Write a committed r2_manifest.json (one entry per file, keyed by "
            "R2 key) after the run. Pass e.g. <content-root>/r2_manifest.json."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(args.log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    counts = sync(
        args.content_root,
        bucket=args.bucket,
        dry_run=args.dry_run,
        files=args.files,
        manifest_path=args.manifest,
    )
    logger.info(
        "DONE uploaded=%d skipped=%d bytes=%d",
        counts["uploaded"], counts["skipped"], counts["bytes_uploaded"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
