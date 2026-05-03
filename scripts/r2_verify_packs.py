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


def head_one(http: urllib3.PoolManager, base: str, key: str) -> tuple[str, int, str]:
    """HEAD one URL. Returns (key, status, error_msg).

    A network exception (DNS / TLS / timeout / connection reset) is converted
    to status=0 with the exception class+message as error_msg, so a single
    transient blip during a 900-key sweep counts as one failure rather than
    aborting the entire run. The full sweep still surfaces every failure
    loudly (and exits non-zero) — this just trades "abort on first blip"
    for "complete the sweep and report all blips."
    """
    url = f"{base.rstrip('/')}/{key.lstrip('/')}"
    try:
        resp = http.request("HEAD", url, retries=False, timeout=10.0)
    except urllib3.exceptions.HTTPError as exc:
        return key, 0, f"{exc.__class__.__name__}: {exc}"
    return key, resp.status, ""


def verify(content_root: Path, base: str = DEFAULT_BASE, workers: int = 16) -> int:
    """Returns the count of failed checks. 0 means perfect."""
    http = urllib3.PoolManager(num_pools=max(4, workers), maxsize=workers)
    keys = [
        p.relative_to(content_root).as_posix()
        for p in iter_media_files(content_root / "genre_packs")
    ]
    failures = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(head_one, http, base, k): k for k in keys}
        for fut in as_completed(futs):
            key, status, error = fut.result()
            if status == 200:
                logger.debug("OK %s", key)
            elif status == 0:
                logger.error("FAIL network %s — %s", key, error)
                failures += 1
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
