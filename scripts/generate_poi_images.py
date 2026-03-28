#!/usr/bin/env python3
"""Batch-generate landscape images for all Points of Interest in genre packs.

Walks every genre pack's history.yaml files, extracts points_of_interest,
composes prompts using the genre's visual_style.yaml, and sends render
requests to the running sidequest-renderer daemon over its Unix socket.

Usage:
    python scripts/generate_poi_images.py                      # all genres
    python scripts/generate_poi_images.py --genre low_fantasy   # one genre
    python scripts/generate_poi_images.py --dry-run             # preview prompts
    python scripts/generate_poi_images.py --steps 20            # more quality
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import shutil
import sys
import time
from pathlib import Path

SOCKET_PATH = Path("/tmp/sidequest-renderer.sock")
_root = Path(__file__).resolve().parent.parent
GENRE_PACKS_DIR = _root / "sidequest-content" / "genre_packs"

# Render config — landscape orientation, Flux dev for quality
DEFAULT_STEPS = 15
WIDTH = 1024
HEIGHT = 768
GUIDANCE = 3.5

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
    """Load YAML file. Uses PyYAML if available, falls back to simple parsing."""
    import yaml
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_visual_style(genre_dir: Path, world: str = "") -> dict:
    """Load visual_style.yaml, preferring world-level over genre-level."""
    # Try world-level first
    if world:
        world_vs = genre_dir / "worlds" / world / "visual_style.yaml"
        if world_vs.exists():
            log.debug("Using world visual_style: %s", world_vs)
            return load_yaml(world_vs)
    # Fall back to genre-level
    vs_path = genre_dir / "visual_style.yaml"
    if not vs_path.exists():
        return {}
    return load_yaml(vs_path)


def collect_pois(genre_dir: Path) -> list[dict]:
    """Walk all history.yaml files and extract points_of_interest entries."""
    pois = []
    genre_name = genre_dir.name

    for history_path in sorted(genre_dir.rglob("history.yaml")):
        data = load_yaml(history_path)
        # Determine world from path
        rel = history_path.relative_to(genre_dir)
        world = rel.parts[1] if len(rel.parts) > 2 and rel.parts[0] == "worlds" else "default"

        chapters = data.get("chapters", [])
        for chapter in chapters:
            chapter_id = chapter.get("id", "unknown")
            chapter_label = chapter.get("label", chapter_id)
            atmosphere = chapter.get("atmosphere", "")
            location = chapter.get("location", "")

            for poi in chapter.get("points_of_interest", []):
                pois.append({
                    "genre": genre_name,
                    "world": world,
                    "chapter_id": chapter_id,
                    "chapter_label": chapter_label,
                    "atmosphere": atmosphere,
                    "chapter_location": location,
                    "name": poi.get("name", "unknown"),
                    "description": poi.get("description", ""),
                    "region": poi.get("region", ""),
                    "type": poi.get("type", ""),
                })

    return pois


def resolve_location_tags(location: str, tag_overrides: dict[str, str]) -> str:
    """Match location against visual tag overrides."""
    loc_lower = location.lower()
    for key, tags in tag_overrides.items():
        if key in loc_lower:
            return tags
    return location


def compose_prompt(poi: dict, visual_style: dict) -> tuple[str, str, int]:
    """Compose positive prompt, CLIP prompt, and seed for a POI.

    Returns (positive_prompt, clip_prompt, seed).
    """
    style_suffix = visual_style.get("positive_suffix", "")
    tag_overrides = visual_style.get("visual_tag_overrides", {})
    base_seed = visual_style.get("base_seed", 42)

    # Build narrative from POI data
    parts = []

    # Lead with the POI name and description — this is the subject
    subject = f"{poi['name']}: {poi['description']}"
    parts.append(subject)

    # Add atmosphere from the chapter
    if poi["atmosphere"]:
        parts.append(poi["atmosphere"])

    # Match POI region against visual tag overrides (exact match first, then fuzzy)
    region = poi.get("region", "")
    if region and region in tag_overrides:
        region_style = tag_overrides[region]
        if isinstance(region_style, dict):
            parts.append(region_style.get("positive_suffix", ""))
        else:
            parts.append(region_style)
    else:
        # Fall back to matching POI name or chapter location
        location_text = poi["name"]
        location_tags = resolve_location_tags(location_text, tag_overrides)
        if location_tags != location_text:
            parts.append(location_tags)
        if poi["chapter_location"]:
            chapter_tags = resolve_location_tags(poi["chapter_location"], tag_overrides)
            if chapter_tags != poi["chapter_location"] and chapter_tags not in parts:
                parts.append(chapter_tags)

    # Token budget: style goes after narrative
    style_tokens = estimate_tokens(style_suffix)
    narrative = ", ".join(parts)
    narrative_tokens = estimate_tokens(narrative)

    if narrative_tokens + style_tokens > TOKEN_LIMIT:
        max_narrative = TOKEN_LIMIT - style_tokens - 10
        narrative = truncate_to_tokens(narrative, max_narrative)

    # Final prompt: style first (genre atmosphere), then narrative
    if style_suffix:
        positive = f"{style_suffix}, {narrative}"
    else:
        positive = narrative

    # CLIP prompt — short style keywords
    clip_parts = ["wide establishing shot, scenic vista, atmospheric"]
    if style_suffix:
        clip_parts.append(style_suffix)
    clip = ", ".join(clip_parts)

    # Deterministic seed from POI identity
    seed_key = f"{poi['genre']}:{poi['world']}:{poi['name']}:landscape"
    digest = hashlib.sha256(seed_key.encode()).hexdigest()
    seed = (int(digest[:8], 16) + base_seed) % (2**32)

    return positive, clip, seed


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    return (
        text.lower()
        .replace("'", "")
        .replace("'", "")
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


async def send_render(positive: str, clip: str, seed: int, steps: int) -> dict:
    """Send a render request to the daemon and return the result."""
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    req = {
        "id": f"poi-{seed}",
        "method": "render",
        "params": {
            "tier": "landscape",
            "positive_prompt": positive,
            "clip_prompt": clip,
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


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate POI landscape images")
    parser.add_argument("--genre", help="Only process this genre pack")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without rendering")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help=f"Inference steps (default: {DEFAULT_STEPS})")
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    # Collect all POIs
    all_pois = []
    for genre_dir in sorted(GENRE_PACKS_DIR.iterdir()):
        if not genre_dir.is_dir():
            continue
        if args.genre and genre_dir.name != args.genre:
            continue
        pois = collect_pois(genre_dir)
        if pois:
            # Group by world so each gets its own visual_style
            worlds_seen = {}
            for poi in pois:
                w = poi["world"]
                if w not in worlds_seen:
                    worlds_seen[w] = load_visual_style(genre_dir, w)
                poi["_visual_style"] = worlds_seen[w]
            all_pois.extend(pois)

    if not all_pois:
        log.error("No points of interest found!")
        sys.exit(1)

    log.info("Found %d points of interest across %d genre packs",
             len(all_pois), len(set(p["genre"] for p in all_pois)))

    # Deduplicate — same POI can appear in genre-level and world-level history
    seen = set()
    unique_pois = []
    for poi in all_pois:
        key = f"{poi['genre']}:{poi['name']}"
        if key not in seen:
            seen.add(key)
            unique_pois.append(poi)

    log.info("After deduplication: %d unique POIs", len(unique_pois))

    if not args.dry_run:
        if not await check_daemon():
            log.error("Daemon not running at %s — start with: sidequest-renderer", SOCKET_PATH)
            sys.exit(1)
        log.info("Daemon is alive at %s", SOCKET_PATH)

    # Process each POI
    total = len(unique_pois)
    success = 0
    failed = 0
    start_time = time.monotonic()

    for i, poi in enumerate(unique_pois, 1):
        visual_style = poi.pop("_visual_style")
        positive, clip, seed = compose_prompt(poi, visual_style)

        # Output path
        if args.output_dir:
            out_dir = args.output_dir / poi["genre"]
        else:
            out_dir = GENRE_PACKS_DIR / poi["genre"] / "images" / "poi"
        out_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(poi["name"])
        out_path = out_dir / f"{slug}.png"

        # Skip if already generated
        if out_path.exists() and not args.dry_run:
            log.info("[%d/%d] SKIP %s/%s (already exists)", i, total, poi["genre"], poi["name"])
            success += 1
            continue

        log.info("[%d/%d] %s / %s / %s", i, total, poi["genre"], poi["world"], poi["name"])

        if args.dry_run:
            print(f"\n{'='*80}")
            print(f"Genre: {poi['genre']}  World: {poi['world']}  Chapter: {poi['chapter_label']}")
            print(f"POI: {poi['name']}")
            print(f"Description: {poi['description']}")
            print(f"Seed: {seed}")
            print(f"\nPositive prompt ({estimate_tokens(positive)} tokens):")
            print(f"  {positive[:200]}...")
            print(f"\nCLIP prompt:")
            print(f"  {clip[:150]}...")
            print(f"\nOutput: {out_path}")
            continue

        try:
            result = await send_render(positive, clip, seed, args.steps)
            if "error" in result:
                log.error("  FAILED: %s", result["error"])
                failed += 1
                continue

            # Copy rendered image to output path
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


if __name__ == "__main__":
    asyncio.run(main())
