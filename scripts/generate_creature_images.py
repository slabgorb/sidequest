#!/usr/bin/env python3
"""Batch-generate creature/monster images from creatures.yaml files.

Usage:
    python scripts/generate_creature_images.py                           # all genres
    python scripts/generate_creature_images.py --genre caverns_and_claudes
    python scripts/generate_creature_images.py --genre caverns_and_claudes --dry-run
    python scripts/generate_creature_images.py --force                    # regenerate existing
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


def collect_creatures(genre_dir: Path) -> list[dict]:
    """Walk all creatures.yaml files and extract creature entries."""
    creatures = []
    genre_name = genre_dir.name

    for creatures_path in sorted(genre_dir.rglob("creatures.yaml")):
        data = load_yaml(creatures_path)
        rel = creatures_path.relative_to(genre_dir)
        world = rel.parts[1] if len(rel.parts) > 2 and rel.parts[0] == "worlds" else "default"

        creature_list = data.get("creatures", [])
        if isinstance(data, list):
            creature_list = data

        for creature in creature_list:
            creatures.append({
                "genre": genre_name,
                "world": world,
                "name": creature.get("name", "unknown"),
                "id": creature.get("id", "unknown"),
                "description": creature.get("description", ""),
                "threat_level": creature.get("threat_level", 1),
                "tags": creature.get("tags", []),
            })

    return creatures


def compose_prompt(creature: dict, visual_style: dict) -> tuple[str, str, str, int]:
    """Compose subject description, CLIP prompt, negative prompt, and seed.

    Returns the subject (not a pre-composed prompt). The daemon's PromptComposer
    handles style injection via art_style, visual_tag_overrides, and LoRA.
    """
    negative = visual_style.get("negative_prompt", "")
    base_seed = visual_style.get("base_seed", 42)

    description = creature.get("description", "")
    name = creature.get("name", "unknown")
    threat = creature.get("threat_level", 1)

    # Scale framing by threat level
    if threat >= 4:
        framing = "full page illustration, dramatic composition, imposing scale"
    elif threat >= 3:
        framing = "half page illustration, menacing pose"
    elif threat >= 2:
        framing = "quarter page illustration, lurking posture"
    else:
        framing = "spot illustration, small creature vignette"

    subject = truncate_to_tokens(description, TOKEN_LIMIT - 100)
    subject = f"{subject}, {framing}"

    clip = f"{name}, creature illustration"

    seed = deterministic_seed(f"creature-{creature['genre']}-{creature['id']}", base_seed)

    return subject, clip, negative, seed


def main():
    parser = argparse.ArgumentParser(description="Generate creature images from creatures.yaml")
    parser.add_argument("--genre", help="Only process this genre")
    parser.add_argument("--world", help="Only process this world (requires --genre)")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without rendering")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Inference steps")
    parser.add_argument("--force", action="store_true", help="Regenerate existing images")
    args = parser.parse_args()
    if args.world and not args.genre:
        parser.error("--world requires --genre")

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    genre_dirs = sorted(GENRE_PACKS_DIR.iterdir()) if not args.genre else [GENRE_PACKS_DIR / args.genre]
    genre_dirs = [d for d in genre_dirs if d.is_dir() and (d / "pack.yaml").exists()]

    if not genre_dirs:
        log.error("No genre packs found (genre=%s)", args.genre)
        return

    all_creatures = []
    for genre_dir in genre_dirs:
        visual_style = load_visual_style(genre_dir, tier="portrait")
        creatures = collect_creatures(genre_dir)
        if args.world:
            creatures = [c for c in creatures if c.get("world") == args.world]
        for c in creatures:
            c["_visual_style"] = visual_style
        all_creatures.extend(creatures)

    asyncio.run(
        render_batch(
            all_creatures,
            compose_prompt,
            "portrait",
            "creatures",
            genre_filter=args.genre,
            dry_run=args.dry_run,
            steps=args.steps,
            force=args.force,
        )
    )


if __name__ == "__main__":
    main()
