#!/usr/bin/env python3
"""Batch-generate portrait images for characters defined in portrait_manifest.yaml.

Usage:
    python3 scripts/generate_portrait_images.py                      # all genres
    python3 scripts/generate_portrait_images.py --genre victoria
    python3 scripts/generate_portrait_images.py --dry-run
    python3 scripts/generate_portrait_images.py --force              # regenerate existing
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from render_common import (
    GENRE_PACKS_DIR,
    TOKEN_LIMIT,
    deterministic_seed,
    estimate_tokens,
    load_visual_style,
    load_yaml,
    render_batch,
    truncate_to_tokens,
)

DEFAULT_STEPS = 15
log = logging.getLogger(__name__)


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


def compose_prompt(char: dict, visual_style: dict) -> tuple[str, str, str, int]:
    """Compose subject description, CLIP prompt, negative prompt, and seed.

    Returns the subject (not a pre-composed prompt). The daemon's PromptComposer
    handles style injection via art_style, visual_tag_overrides, and LoRA.
    """
    negative = visual_style.get("negative_prompt", "")
    base_seed = visual_style.get("base_seed", 42)

    parts = [f"{char['name']}, {char['role']}."]
    if char.get("appearance"):
        parts.append(char["appearance"])
    if char.get("culture_aesthetic"):
        parts.append(char["culture_aesthetic"])
    if char.get("element_visual"):
        parts.append(char["element_visual"])

    subject = " ".join(parts)
    subject = truncate_to_tokens(subject, TOKEN_LIMIT - 100)

    clip = "character portrait, detailed face, expressive"

    seed_key = f"{char['genre']}:{char['world']}:{char['name']}:portrait"
    seed = deterministic_seed(seed_key, base_seed)

    return subject, clip, negative, seed


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate character portrait images")
    parser.add_argument("--genre", help="Only process this genre pack")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without rendering")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--force", action="store_true", help="Regenerate even if image exists")
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

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
                    worlds_seen[w] = load_visual_style(genre_dir, w, tier="portrait")
                char["_visual_style"] = worlds_seen[w]
            all_chars.extend(chars)

    await render_batch(
        all_chars,
        compose_prompt,
        tier="portrait",
        image_subdir="portraits",
        dry_run=args.dry_run,
        steps=args.steps,
        force=args.force,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    asyncio.run(main())
