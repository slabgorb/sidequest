#!/usr/bin/env python3
"""Batch-generate portrait images for characters defined in portrait_manifest.yaml.

Usage:
    python3 scripts/generate_portrait_images.py                      # all genres
    python3 scripts/generate_portrait_images.py --genre tea_and_murder
    python3 scripts/generate_portrait_images.py --dry-run
    python3 scripts/generate_portrait_images.py --force              # regenerate existing
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import re

from render_common import (
    GENRE_PACKS_DIR,
    TOKEN_LIMIT,
    apply_shard,
    deterministic_seed,
    load_visual_style,
    load_yaml,
    parse_shard,
    render_batch,
    truncate_to_tokens,
)


def _slugify_name(name: str) -> str:
    """Mirror sidequest_daemon.media.catalogs._slugify_name so the script
    derives the same `npc:<slug>` ref the daemon's CharacterCatalog uses
    when reading portrait_manifest.yaml entries that lack an explicit `id`."""
    lowered = name.strip().lower()
    collapsed = re.sub(r"\s+", "_", lowered)
    return re.sub(r"[^a-z0-9_-]", "", collapsed)


DEFAULT_STEPS = 20
log = logging.getLogger(__name__)


def collect_characters(genre_dir: Path) -> list[dict]:
    """Walk all portrait_manifest.yaml files and extract character entries."""
    characters = []
    genre_name = genre_dir.name

    for manifest_path in sorted(genre_dir.rglob("portrait_manifest.yaml")):
        data = load_yaml(manifest_path)
        rel = manifest_path.relative_to(genre_dir)
        world = (
            rel.parts[1]
            if len(rel.parts) > 2 and rel.parts[0] == "worlds"
            else "default"
        )

        for char in data.get("characters", []):
            name = char.get("name", "unknown")
            slug = char.get("id") or _slugify_name(name)
            characters.append(
                {
                    "genre": genre_name,
                    "world": world,
                    "name": name,
                    "slug": slug,
                    "catalog_ref": f"npc:{slug}",
                    "role": char.get("role", ""),
                    "type": char.get("type", "npc_major"),
                    "appearance": char.get("appearance", ""),
                    "culture_aesthetic": char.get("culture_aesthetic", ""),
                    "element_visual": char.get("element_visual", ""),
                }
            )

    return characters


def compose_prompt(char: dict, visual_style: dict) -> tuple[str, str, int]:
    """Compose subject description, CLIP prompt, and seed.

    Returns the subject (not a pre-composed prompt). The daemon's PromptComposer
    handles style injection via art_style, visual_tag_overrides, and LoRA.
    """
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

    return subject, clip, seed


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate character portrait images")
    parser.add_argument("--genre", help="Only process this genre pack")
    parser.add_argument("--world", help="Only process this world (requires --genre)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview prompts without rendering"
    )
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument(
        "--force", action="store_true", help="Regenerate even if image exists"
    )
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Test render: keep PNGs local, do not upload to R2 or rebuild the manifest",
    )
    parser.add_argument(
        "--shard",
        help="Render only shard i/n of the work-list (e.g. 0/2 on one Mac, 1/2 on "
        "another) to split a batch across renderers. Partition is stable-sorted, "
        "so shards are disjoint and cover the whole set.",
    )
    args = parser.parse_args()
    if args.world and not args.genre:
        parser.error("--world requires --genre")
    shard = parse_shard(args.shard)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S"
    )

    all_chars = []
    for genre_dir in sorted(GENRE_PACKS_DIR.iterdir()):
        if not genre_dir.is_dir():
            continue
        if args.genre and genre_dir.name != args.genre:
            continue
        chars = collect_characters(genre_dir)
        if args.world:
            chars = [c for c in chars if c.get("world") == args.world]
        if chars:
            worlds_seen = {}
            for char in chars:
                w = char["world"]
                if w not in worlds_seen:
                    worlds_seen[w] = load_visual_style(genre_dir, w, tier="portrait")
                char["_visual_style"] = worlds_seen[w]
            all_chars.extend(chars)

    all_chars = apply_shard(
        all_chars, shard, key=lambda c: f"{c['genre']}:{c['world']}:{c['slug']}"
    )
    if shard is not None:
        log.info(
            "Shard %d/%d: rendering %d of the work-list",
            shard[0],
            shard[1],
            len(all_chars),
        )

    await render_batch(
        all_chars,
        compose_prompt,
        tier="portrait",
        image_subdir="portraits",
        dry_run=args.dry_run,
        steps=args.steps,
        force=args.force,
        output_dir=args.output_dir,
        catalog_compose=True,
        fidelity="high_fidelity",
        upload=not args.no_upload,
    )


if __name__ == "__main__":
    asyncio.run(main())
