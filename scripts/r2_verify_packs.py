"""Phase A verification — HEAD every local media file via cdn.slabgorb.com.

Aborts on any non-200; per CLAUDE.md a missing object is loud, not silent.
"""
from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import urllib3

from scripts.r2_sync_packs import iter_media_files

logger = logging.getLogger("r2_verify_packs")
DEFAULT_BASE = "https://cdn.slabgorb.com"


def head_one(http: urllib3.PoolManager, base: str, key: str) -> tuple[str, int]:
    url = f"{base.rstrip('/')}/{key.lstrip('/')}"
    resp = http.request("HEAD", url, retries=False, timeout=10.0)
    return key, resp.status


def verify(content_root: Path, base: str = DEFAULT_BASE, workers: int = 16) -> int:
    """Returns the count of failed checks. 0 means perfect."""
    http = urllib3.PoolManager(num_pools=4, maxsize=workers)
    keys = [
        p.relative_to(content_root).as_posix()
        for p in iter_media_files(content_root / "genre_packs")
    ]
    failures = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(head_one, http, base, k): k for k in keys}
        for fut in as_completed(futs):
            key, status = fut.result()
            if status == 200:
                logger.info("OK %s", key)
            else:
                logger.error("FAIL status=%d %s", status, key)
                failures += 1
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--content-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sidequest-content",
    )
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--log-file", type=Path, default=Path("/tmp/r2-verify.log"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(args.log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    failures = verify(args.content_root, base=args.base, workers=args.workers)
    if failures:
        logger.error("VERIFY FAILED count=%d", failures)
        return 1
    logger.info("VERIFY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
