#!/usr/bin/env python3
"""Walk per-track JSON params files in a genre pack and dispatch each
to the daemon for ACE-Step generation.

Source of truth: `<pack>/audio/music/*_input_params.json` files.
Output: R2 at `genre_packs/<pack>/audio/music/<track>.ogg`.

Usage:
    python scripts/generate_music.py --genre <pack>           # all missing
    python scripts/generate_music.py --genre <pack> --track combat
    python scripts/generate_music.py --genre <pack> --force   # re-render existing
    python scripts/generate_music.py --genre <pack> --dry-run

See docs/superpowers/specs/2026-05-09-daemon-between-session-music-generation-design.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests

SOCKET_PATH = Path("/tmp/sidequest-renderer.sock")
_root = Path(__file__).resolve().parent.parent
GENRE_PACKS_DIR = _root / "sidequest-content" / "genre_packs"

log = logging.getLogger(__name__)

_GENRE_PACKS_RE = re.compile(r".*?(genre_packs/.*?)/audio/music/(.+?)_input_params\.json$")


def discover_jobs(pack_dir: Path) -> list[tuple[Path, str]]:
    jobs = []
    for json_path in pack_dir.glob("**/audio/music/*_input_params.json"):
        m = _GENRE_PACKS_RE.match(str(json_path))
        if not m:
            continue
        pack_path, name = m.group(1), m.group(2)
        r2_key = f"{pack_path}/audio/music/{name}.ogg"
        jobs.append((json_path, r2_key))
    return jobs


def filter_jobs_by_track(jobs: list[tuple[Path, str]], track: str) -> list[tuple[Path, str]]:
    target = f"{track}_input_params.json"
    return [(jp, key) for jp, key in jobs if jp.name == target]


def _asset_base_url() -> str:
    return os.environ.get("SIDEQUEST_ASSET_BASE_URL", "https://cdn.slabgorb.com").rstrip("/")


def is_in_r2(r2_key: str) -> bool:
    url = f"{_asset_base_url()}/{r2_key.lstrip('/')}"
    resp = requests.head(url, timeout=5)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False


async def _read_reply(reader: asyncio.StreamReader, req_id: str, timeout: float) -> dict:
    """Read lines until we get the JSON-RPC reply matching `req_id`.

    The daemon emits unsolicited heartbeat frames (`{"event":"heartbeat",...}`)
    on every client connection, which would otherwise be mistaken for the
    reply by a one-shot readline. Skip frames that aren't our reply.
    """
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise asyncio.TimeoutError(f"no reply for id={req_id} within {timeout}s")
        line = await asyncio.wait_for(reader.readline(), timeout=remaining)
        if not line:
            raise EOFError(f"daemon closed socket before replying to id={req_id}")
        msg = json.loads(line.decode())
        if msg.get("id") == req_id:
            return msg


async def send_render(json_path: Path) -> dict:
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
    req_id = f"music-{json_path.stem}-{int(time.time())}"
    req = {
        "id": req_id,
        "method": "render",
        "params": {"tier": "music", "json_params_path": str(json_path)},
    }
    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()
    try:
        return await _read_reply(reader, req_id, timeout=900)
    finally:
        writer.close()
        await writer.wait_closed()


async def check_daemon() -> bool:
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
        req_id = "healthcheck"
        req = {"id": req_id, "method": "ping"}
        writer.write((json.dumps(req) + "\n").encode())
        await writer.drain()
        try:
            reply = await _read_reply(reader, req_id, timeout=5)
        finally:
            writer.close()
            await writer.wait_closed()
        return reply.get("result", {}).get("status") == "ok"
    except Exception:
        return False


async def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ACE-Step music tracks for a genre pack")
    parser.add_argument("--genre", required=True, help="Genre pack slug")
    parser.add_argument("--track", help="Only generate this track (file stem, e.g. 'combat')")
    parser.add_argument("--force", action="store_true", help="Re-render even if R2 already has the object")
    parser.add_argument("--dry-run", action="store_true", help="List jobs without sending to daemon")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    pack_dir = GENRE_PACKS_DIR / args.genre
    if not pack_dir.is_dir():
        log.error("Pack directory not found: %s", pack_dir)
        return 1

    jobs = discover_jobs(pack_dir)
    if args.track:
        jobs = filter_jobs_by_track(jobs, args.track)
        if not jobs:
            log.error("No JSON params file matched --track %r in %s", args.track, pack_dir)
            return 1

    if args.dry_run:
        for jp, key in jobs:
            print(f"  {jp.name}  →  {key}")
        print(f"\n{len(jobs)} job(s) discovered.")
        return 0

    if not await check_daemon():
        log.error("Daemon not running at %s — start with: just daemon", SOCKET_PATH)
        return 1

    generated = 0
    skipped = 0
    failed = 0
    t_start = time.monotonic()

    for jp, r2_key in jobs:
        if not args.force and is_in_r2(r2_key):
            log.info("SKIP %s (in R2)", r2_key)
            skipped += 1
            continue
        log.info("GEN  %s", r2_key)
        try:
            result = await send_render(jp)
            if "error" in result:
                log.error("  FAILED: %s", result["error"])
                failed += 1
                continue
            elapsed = result["result"].get("elapsed_ms", 0)
            log.info("  OK (%.1fs)", elapsed / 1000)
            generated += 1
        except Exception as exc:
            log.error("  FAILED: %s: %s", type(exc).__name__, exc)
            failed += 1

    total = time.monotonic() - t_start
    print(f"\n{'=' * 60}")
    print(f"generated: {generated}  skipped: {skipped}  failed: {failed}")
    print(f"total: {total:.1f}s")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
