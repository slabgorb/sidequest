"""Shared utilities for image generation scripts.

Common code for portrait and POI batch renderers: daemon communication,
visual style loading, token estimation, slugification, and YAML helpers.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
from pathlib import Path

SOCKET_PATH = Path("/tmp/sidequest-renderer.sock")
_root = Path(__file__).resolve().parent.parent
GENRE_PACKS_DIR = _root / "sidequest-content" / "genre_packs"

# T5-XXL token limit
TOKEN_LIMIT = 512
TOKENS_PER_WORD = 1.3

log = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text.split()) * TOKENS_PER_WORD))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    words = text.split()
    max_words = int(max_tokens / TOKENS_PER_WORD)
    return " ".join(words[:max_words]) if max_words > 0 else ""


def load_yaml(path: Path) -> dict:
    import yaml
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_visual_style(genre_dir: Path, world: str = "") -> dict:
    """Load visual_style.yaml, preferring world-level over genre-level."""
    if world:
        world_vs = genre_dir / "worlds" / world / "visual_style.yaml"
        if world_vs.exists():
            log.debug("Using world visual_style: %s", world_vs)
            return load_yaml(world_vs)
    vs_path = genre_dir / "visual_style.yaml"
    if not vs_path.exists():
        return {}
    return load_yaml(vs_path)


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    return (
        text.lower()
        .replace("'", "")
        .replace("\u2019", "")
        .replace('"', "")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .replace(".", "")
        .replace(":", "")
        .replace("/", "-")
        .replace(" ", "_")
        .strip("_-")
    )


def deterministic_seed(key: str, base_seed: int) -> int:
    """Generate a deterministic seed from a string key and base seed."""
    digest = hashlib.sha256(key.encode()).hexdigest()
    return (int(digest[:8], 16) + base_seed) % (2**32)


async def send_render(
    tier: str,
    positive: str,
    clip: str,
    negative: str,
    seed: int,
    steps: int = 15,
) -> dict:
    """Send a render request to the daemon and return the result."""
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    req = {
        "id": f"{tier}-{seed}",
        "method": "render",
        "params": {
            "tier": tier,
            "positive_prompt": positive,
            "clip_prompt": clip,
            "negative_prompt": negative,
            "seed": seed,
        },
    }

    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()

    response_line = await reader.readline()
    writer.close()
    await writer.wait_closed()

    return json.loads(response_line.decode())


async def check_daemon() -> bool:
    """Check if the daemon is running."""
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
        req = {"id": "healthcheck", "method": "ping"}
        writer.write((json.dumps(req) + "\n").encode())
        await writer.drain()
        resp = await reader.readline()
        writer.close()
        await writer.wait_closed()
        data = json.loads(resp.decode())
        return data.get("result", {}).get("status") == "ok"
    except Exception:
        return False


async def render_batch(
    items: list[dict],
    compose_fn,
    tier: str,
    image_subdir: str,
    *,
    genre_filter: str | None = None,
    dry_run: bool = False,
    steps: int = 15,
    force: bool = False,
    output_dir: Path | None = None,
) -> None:
    """Generic batch render loop for any image type.

    Args:
        items: List of dicts, each with 'genre', 'world', 'name', '_visual_style'.
        compose_fn: Function(item, visual_style) -> (positive, clip, negative, seed).
        tier: Renderer tier ('portrait', 'landscape', etc.).
        image_subdir: Subdirectory under images/ ('portraits', 'poi', etc.).
        genre_filter: Only process items from this genre.
        dry_run: Preview prompts without rendering.
        steps: Inference steps.
        force: Regenerate even if image exists.
        output_dir: Override output directory.
    """
    import time

    if not items:
        log.error("No items found!")
        return

    log.info("Found %d items across %d genre packs",
             len(items), len(set(it["genre"] for it in items)))

    if not dry_run:
        if not await check_daemon():
            log.error("Daemon not running at %s — start with: sidequest-renderer", SOCKET_PATH)
            return
        log.info("Daemon is alive at %s", SOCKET_PATH)

    total = len(items)
    success = 0
    failed = 0
    start_time = time.monotonic()

    for i, item in enumerate(items, 1):
        visual_style = item.pop("_visual_style")
        positive, clip, negative, seed = compose_fn(item, visual_style)

        if output_dir:
            out_dir = output_dir / item["genre"]
        else:
            out_dir = GENRE_PACKS_DIR / item["genre"] / "images" / image_subdir
        out_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(item["name"])
        out_path = out_dir / f"{slug}.png"

        # Skip if already generated (unless --force)
        if out_path.exists() and not force and not dry_run:
            log.info("[%d/%d] SKIP %s/%s (already exists)", i, total, item["genre"], item["name"])
            success += 1
            continue

        label = item.get("role", item.get("chapter_label", ""))
        log.info("[%d/%d] %s / %s / %s%s", i, total, item["genre"], item["world"], item["name"],
                 f" ({label})" if label else "")

        if dry_run:
            print(f"\n{'='*80}")
            print(f"Genre: {item['genre']}  World: {item['world']}")
            print(f"Name: {item['name']}")
            print(f"Seed: {seed}")
            print(f"\nPositive prompt ({estimate_tokens(positive)} tokens):")
            print(f"  {positive}")
            print(f"\nCLIP prompt:")
            print(f"  {clip}")
            print(f"\nNegative prompt:")
            print(f"  {negative}")
            print(f"\nOutput: {out_path}")
            continue

        try:
            result = await send_render(tier, positive, clip, negative, seed, steps)
            if "error" in result:
                log.error("  FAILED: %s", result["error"])
                failed += 1
                continue

            rendered_path = Path(result["result"]["image_path"])
            shutil.copy2(rendered_path, out_path)
            elapsed = result["result"].get("elapsed_ms", 0)
            log.info("  OK (%.1fs) → %s", elapsed / 1000, out_path)
            success += 1

        except Exception as e:
            log.error("  FAILED: %s", e)
            failed += 1

    total_time = time.monotonic() - start_time

    print(f"\n{'='*80}")
    print(f"Done! {success}/{total} generated, {failed} failed")
    print(f"Total time: {total_time/60:.1f} minutes")
    if success > 0 and total_time > 0:
        print(f"Average: {total_time/success:.1f}s per image")
