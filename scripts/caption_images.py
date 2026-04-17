"""Caption images via the sidequest-renderer daemon (dev profile).

Sends caption requests over the Unix socket to the Florence-2 CaptionWorker.
Writes .txt caption files alongside each image.

Usage:
    python scripts/caption_images.py /path/to/images/
    python scripts/caption_images.py /path/to/images/ --trigger eh_style
    python scripts/caption_images.py /path/to/images/ --metadata /path/to/metadata/
    python scripts/caption_images.py /path/to/images/ --mode tags
    python scripts/caption_images.py /path/to/images/ --dry-run
    python scripts/caption_images.py /path/to/images/ --overwrite

Requires the daemon running with --profile dev:
    sidequest-renderer --profile dev --no-warmup
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_common import SOCKET_PATH, check_daemon

log = logging.getLogger(__name__)


async def send_caption(image_path: str, mode: str, trigger_word: str) -> dict:
    """Send a single caption request to the daemon."""
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    req = {
        "id": f"caption-{Path(image_path).stem}",
        "method": "caption",
        "params": {
            "image_path": image_path,
            "mode": mode,
            "trigger_word": trigger_word,
        },
    }

    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()

    response_line = await reader.readline()
    writer.close()
    await writer.wait_closed()

    return json.loads(response_line.decode())


async def send_caption_batch(
    directory: str, mode: str, trigger_word: str, overwrite: bool
) -> dict:
    """Send a batch caption request to the daemon."""
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    req = {
        "id": "caption-batch",
        "method": "caption_batch",
        "params": {
            "directory": directory,
            "mode": mode,
            "trigger_word": trigger_word,
            "overwrite": overwrite,
        },
    }

    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()

    # Batch can take a long time — no timeout
    response_line = await reader.readline()
    writer.close()
    await writer.wait_closed()

    return json.loads(response_line.decode())


def enrich_with_metadata(image_dir: Path, metadata_dir: Path) -> None:
    """Merge structured metadata into Florence-2 captions.

    For each image with both a .txt caption and a matching JSON metadata file,
    prepend the structured data (artist, title, period) to the visual caption.
    """
    enriched = 0
    for txt_path in sorted(image_dir.glob("*.txt")):
        stem = txt_path.stem
        meta_path = metadata_dir / f"{stem}.json"
        if not meta_path.exists():
            continue

        caption = txt_path.read_text().strip()
        meta = json.loads(meta_path.read_text())

        parts = []
        if meta.get("artists"):
            parts.append(f"by {meta['artists'][0]}")
        if meta.get("dated"):
            parts.append(meta["dated"])
        if meta.get("title"):
            parts.append(f'"{meta["title"]}"')

        if parts:
            prefix = ", ".join(parts)
            enriched_caption = f"{prefix}. {caption}"
            txt_path.write_text(enriched_caption)
            enriched += 1

    log.info("Enriched %d captions with metadata", enriched)


async def run(args: argparse.Namespace) -> None:
    image_dir = Path(args.directory).resolve()
    if not image_dir.is_dir():
        log.error("Not a directory: %s", image_dir)
        sys.exit(1)

    image_files = sorted(
        p for p in image_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    log.info("Found %d images in %s", len(image_files), image_dir)

    if args.dry_run:
        # Preview what would be captioned
        existing = sum(1 for p in image_files if p.with_suffix(".txt").exists())
        to_caption = len(image_files) - existing if not args.overwrite else len(image_files)
        print(f"\nDry run:")
        print(f"  Images: {len(image_files)}")
        print(f"  Already captioned: {existing}")
        print(f"  Would caption: {to_caption}")
        print(f"  Mode: {args.mode}")
        print(f"  Trigger word: {args.trigger or '(none)'}")
        print(f"  Overwrite: {args.overwrite}")
        if args.metadata:
            print(f"  Metadata enrichment: {args.metadata}")
        return

    if not await check_daemon():
        log.error(
            "Daemon not running at %s — start with: sidequest-renderer --profile dev --no-warmup",
            SOCKET_PATH,
        )
        sys.exit(1)

    log.info("Daemon alive. Sending batch caption request...")
    result = await send_caption_batch(
        directory=str(image_dir),
        mode=args.mode,
        trigger_word=args.trigger or "",
        overwrite=args.overwrite,
    )

    if "error" in result:
        log.error("Batch caption failed: %s", result["error"])
        sys.exit(1)

    r = result["result"]
    elapsed_s = r["elapsed_ms"] / 1000
    print(f"\nCaptioning complete:")
    print(f"  Completed: {r['completed']}")
    print(f"  Skipped: {r['skipped']}")
    print(f"  Failed: {r['failed']}")
    print(f"  Elapsed: {elapsed_s:.1f}s")
    if r["completed"] > 0:
        print(f"  Avg: {elapsed_s / r['completed']:.1f}s per image")

    # Enrich with metadata if provided
    if args.metadata:
        metadata_dir = Path(args.metadata).resolve()
        if not metadata_dir.is_dir():
            log.error("Metadata directory not found: %s", metadata_dir)
            sys.exit(1)
        enrich_with_metadata(image_dir, metadata_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Caption images via sidequest-renderer daemon (dev profile)"
    )
    parser.add_argument("directory", help="Directory of images to caption")
    parser.add_argument("--mode", default="detailed", choices=["detailed", "tags", "brief"],
                        help="Caption mode (default: detailed)")
    parser.add_argument("--trigger", help="Trigger word to append (for LoRA training)")
    parser.add_argument("--metadata", help="Directory with JSON metadata to enrich captions")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .txt files")
    parser.add_argument("--dry-run", action="store_true", help="Preview without captioning")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
