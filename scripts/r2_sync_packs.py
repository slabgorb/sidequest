"""Phase A — sync sidequest-content/genre_packs/ into R2.

Walks the local content tree, uploads every LFS-tracked binary to R2 under
the same relative path, and is idempotent across re-runs (compares local MD5
to remote ETag and skips matches).

Per CLAUDE.md no-silent-fallbacks rule: any HTTP error aborts the run.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

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


def _md5_of(path: Path) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def sync(content_root: Path, bucket: str = "sidequest", dry_run: bool = False) -> dict[str, int]:
    """Walk content_root and upload every LFS-tracked file. Returns counts."""
    if not (content_root / "genre_packs").is_dir():
        raise FileNotFoundError(f"genre_packs/ not found under {content_root}")

    client = None if dry_run else _build_client()
    skipped = 0
    uploaded = 0
    bytes_uploaded = 0

    for path in iter_media_files(content_root / "genre_packs"):
        rel = path.relative_to(content_root).as_posix()
        key = rel  # 1:1 mirror, e.g. genre_packs/<genre>/audio/<f>.ogg
        size = path.stat().st_size
        local_md5 = _md5_of(path)

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
    parser.add_argument("--log-file", type=Path, default=Path("/tmp/r2-sync.log"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(args.log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    counts = sync(args.content_root, bucket=args.bucket, dry_run=args.dry_run)
    logger.info(
        "DONE uploaded=%d skipped=%d bytes=%d",
        counts["uploaded"], counts["skipped"], counts["bytes_uploaded"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
