#!/usr/bin/env python3
"""Batch-generate portrait images for characters defined in portrait_manifest.yaml.

Walks every genre pack's worlds looking for portrait_manifest.yaml files,
composes prompts using the genre's visual_style.yaml, and sends render
requests to the running sidequest-renderer daemon over its Unix socket.

Usage:
    python3 scripts/generate_portrait_images.py                      # all genres
    python3 scripts/generate_portrait_images.py --genre elemental_harmony
    python3 scripts/generate_portrait_images.py --dry-run
    python3 scripts/generate_portrait_images.py --force              # regenerate existing
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

# Render config — portrait orientation, Flux dev for quality
DEFAULT_STEPS = 15
WIDTH = 768
HEIGHT = 1024
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


def collect_characters(genre_dir: Path) -> list[dict]:
    """Walk all portrait_manifest.yaml files and extract character entries."""
    characters = []
    genre_name = genre_dir.name

    for manifest_path in sorted(genre_dir.rglob("portrait_manifest.yaml")):
        data = load_yaml(manifest_path)
        rel = manifest_path.relative_to(genre_dir)
        world = rel.parts[1] if len(rel.parts) > 2 and rel.parts[0] == "worlds" else "default"

        for char in data.get("characters", []):
            characters.append({
                "genre": genre_name,
                "world": world,
                "name": char.get("name", "unknown"),
                "role": char.get("role", ""),
                "type": char.get("type", "npc_major"),
                "appearance": char.get("appearance", ""),
                "culture_aesthetic": char.get("culture_aesthetic", ""),
                "element_visual": char.get("element_visual", ""),
            })

    return characters


def compose_prompt(char: dict, visual_style: dict) -> tuple[str, str, int]:
    """Compose positive prompt, CLIP prompt, and seed for a character portrait.

    Returns (positive_prompt, clip_prompt, seed).
    """
    style_suffix = visual_style.get("positive_suffix", "")
    base_seed = visual_style.get("base_seed", 42)

    # Build narrative: appearance leads, then culture and element visuals
    parts = []
    parts.append(f"Portrait of {char['name']}, {char['role']}.")
    if char["appearance"]:
        parts.append(char["appearance"])
    if char["culture_aesthetic"]:
        parts.append(char["culture_aesthetic"])
    if char["element_visual"]:
        parts.append(char["element_visual"])

    narrative = " ".join(parts)

    # Token budget: style goes after narrative for portraits
    style_tokens = estimate_tokens(style_suffix)
    narrative_tokens = estimate_tokens(narrative)

    if narrative_tokens + style_tokens > TOKEN_LIMIT:
        max_narrative = TOKEN_LIMIT - style_tokens - 10
        narrative = truncate_to_tokens(narrative, max_narrative)

    # Final prompt: narrative first (character is the subject), then style
    if style_suffix:
        positive = f"{narrative}, {style_suffix}"
    else:
        positive = narrative

    # CLIP prompt — portrait-focused
    clip_parts = ["character portrait, bust shot, dramatic lighting"]
    if style_suffix:
        clip_parts.append(style_suffix)
    clip = ", ".join(clip_parts)

    # Deterministic seed from character identity
    seed_key = f"{char['genre']}:{char['world']}:{char['name']}:portrait"
    digest = hashlib.sha256(seed_key.encode()).hexdigest()
    seed = (int(digest[:8], 16) + base_seed) % (2**32)

    return positive, clip, seed


def slugify(text: str) -> str:
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


async def send_render(positive: str, clip: str, seed: int, steps: int) -> dict:
    """Send a render request to the daemon and return the result."""
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    req = {
        "id": f"portrait-{seed}",
        "method": "render",
        "params": {
            "tier": "portrait",
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
    parser = argparse.ArgumentParser(description="Generate character portrait images")
    parser.add_argument("--genre", help="Only process this genre pack")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without rendering")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help=f"Inference steps (default: {DEFAULT_STEPS})")
    parser.add_argument("--force", action="store_true", help="Regenerate even if image exists")
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    # Collect all characters
    all_chars = []
    for genre_dir in sorted(GENRE_PACKS_DIR.iterdir()):
        if not genre_dir.is_dir():
            continue
        if args.genre and genre_dir.name != args.genre:
            continue
        chars = collect_characters(genre_dir)
        if chars:
            worlds_seen = {}
            for char in chars:
                w = char["world"]
                if w not in worlds_seen:
                    worlds_seen[w] = load_visual_style(genre_dir, w)
                char["_visual_style"] = worlds_seen[w]
            all_chars.extend(chars)

    if not all_chars:
        log.error("No portrait manifests found!")
        sys.exit(1)

    log.info("Found %d characters across %d genre packs",
             len(all_chars), len(set(c["genre"] for c in all_chars)))

    if not args.dry_run:
        if not await check_daemon():
            log.error("Daemon not running at %s — start with: sidequest-renderer", SOCKET_PATH)
            sys.exit(1)
        log.info("Daemon is alive at %s", SOCKET_PATH)

    total = len(all_chars)
    success = 0
    failed = 0
    start_time = time.monotonic()

    for i, char in enumerate(all_chars, 1):
        visual_style = char.pop("_visual_style")
        positive, clip, seed = compose_prompt(char, visual_style)

        if args.output_dir:
            out_dir = args.output_dir / char["genre"]
        else:
            out_dir = GENRE_PACKS_DIR / char["genre"] / "images" / "portraits"
        out_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(char["name"])
        out_path = out_dir / f"{slug}.png"

        # Skip if already generated (unless --force)
        if out_path.exists() and not args.force and not args.dry_run:
            log.info("[%d/%d] SKIP %s/%s (already exists)", i, total, char["genre"], char["name"])
            success += 1
            continue

        log.info("[%d/%d] %s / %s / %s (%s)", i, total, char["genre"], char["world"], char["name"], char["role"])

        if args.dry_run:
            print(f"\n{'='*80}")
            print(f"Genre: {char['genre']}  World: {char['world']}")
            print(f"Character: {char['name']} — {char['role']}")
            print(f"Type: {char['type']}")
            print(f"Seed: {seed}")
            print(f"\nPositive prompt ({estimate_tokens(positive)} tokens):")
            print(f"  {positive[:300]}...")
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
