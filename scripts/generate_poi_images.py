#!/usr/bin/env python3
"""Batch-generate landscape images for all Points of Interest in genre packs.

Usage:
    python scripts/generate_poi_images.py                      # all genres
    python scripts/generate_poi_images.py --genre low_fantasy   # one genre
    python scripts/generate_poi_images.py --dry-run             # preview prompts
    python scripts/generate_poi_images.py --steps 20            # more quality
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
    load_visual_style,
    load_yaml,
    render_batch,
    truncate_to_tokens,
)

DEFAULT_STEPS = 15
log = logging.getLogger(__name__)


def collect_pois(genre_dir: Path) -> list[dict]:
    """Walk all history.yaml files and extract points_of_interest entries."""
    pois = []
    genre_name = genre_dir.name

    for history_path in sorted(genre_dir.rglob("history.yaml")):
        data = load_yaml(history_path)
        rel = history_path.relative_to(genre_dir)
        world = rel.parts[1] if len(rel.parts) > 2 and rel.parts[0] == "worlds" else "default"

        chapters = data.get("chapters", [])
        for chapter in chapters:
            chapter_id = chapter.get("id", "unknown")
            chapter_label = chapter.get("label", chapter_id)

            for poi in chapter.get("points_of_interest", []):
                # visual_prompt schema migrated from string → {solo, backdrop}.
                # Landscape POI renders use solo (place fills the frame).
                vp = poi.get("visual_prompt", "")
                if isinstance(vp, dict):
                    visual_prompt = vp.get("solo", "")
                else:
                    visual_prompt = vp or ""

                # catalog_ref is set only when the POI is eligible for the
                # daemon's PlaceCatalog (has slug + visual prose). Worlds that
                # haven't authored visual_prompt entries fall back to the
                # legacy local-composition path inside render_batch.
                slug = poi.get("slug", "")
                catalog_ref = (
                    f"where:{world}/{slug}" if slug and visual_prompt else ""
                )

                pois.append({
                    "genre": genre_name,
                    "world": world,
                    "slug": slug,
                    "chapter_id": chapter_id,
                    "chapter_label": chapter_label,
                    "name": poi.get("name", "unknown"),
                    "description": poi.get("description", ""),
                    "visual_prompt": visual_prompt,
                    "catalog_ref": catalog_ref,
                    "region": poi.get("region", ""),
                    "type": poi.get("type", ""),
                })

    return pois


def compose_prompt(poi: dict, visual_style: dict) -> tuple[str, str, str, int]:
    """Compose subject description, CLIP prompt, negative prompt, and seed for a POI.

    Returns the subject (not a pre-composed prompt). The daemon's PromptComposer
    handles style injection via art_style, visual_tag_overrides, and LoRA — those
    are passed through render_common.send_render from the visual_style dict.
    """
    negative = visual_style.get("negative_prompt", "")
    base_seed = visual_style.get("base_seed", 42)

    # visual_prompt is Flux-native (single trigger + renderable subject).
    # description is narrator-facing prose and is only used when the
    # art-director has not yet authored a visual_prompt for this POI.
    if poi.get("visual_prompt"):
        subject = poi["visual_prompt"]
    else:
        subject = f"{poi['name']}: {poi['description']}"

    subject = truncate_to_tokens(subject, TOKEN_LIMIT - 100)

    clip = "wide establishing shot, atmospheric"

    seed_key = f"{poi['genre']}:{poi['world']}:{poi['name']}:landscape"
    seed = deterministic_seed(seed_key, base_seed)

    return subject, clip, negative, seed


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate POI landscape images")
    parser.add_argument("--genre", help="Only process this genre pack")
    parser.add_argument("--world", help="Only process this world (requires --genre)")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without rendering")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    args = parser.parse_args()
    if args.world and not args.genre:
        parser.error("--world requires --genre")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    all_pois = []
    for genre_dir in sorted(GENRE_PACKS_DIR.iterdir()):
        if not genre_dir.is_dir():
            continue
        if args.genre and genre_dir.name != args.genre:
            continue
        pois = collect_pois(genre_dir)
        if args.world:
            pois = [p for p in pois if p.get("world") == args.world]
        if pois:
            worlds_seen = {}
            for poi in pois:
                w = poi["world"]
                if w not in worlds_seen:
                    worlds_seen[w] = load_visual_style(genre_dir, w, tier="landscape")
                poi["_visual_style"] = worlds_seen[w]
            all_pois.extend(pois)

    # Deduplicate — same POI can appear in genre-level and world-level history
    seen = set()
    unique_pois = []
    for poi in all_pois:
        key = f"{poi['genre']}:{poi['name']}"
        if key not in seen:
            seen.add(key)
            unique_pois.append(poi)

    log.info("After deduplication: %d unique POIs", len(unique_pois))

    await render_batch(
        unique_pois,
        compose_prompt,
        tier="landscape",
        image_subdir="poi",
        dry_run=args.dry_run,
        steps=args.steps,
        force=True,  # POIs don't have --force flag, always regenerate
        output_dir=args.output_dir,
        catalog_compose=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
