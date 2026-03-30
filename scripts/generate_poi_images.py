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
    estimate_tokens,
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


def compose_prompt(poi: dict, visual_style: dict) -> tuple[str, str, str, int]:
    """Compose positive prompt, CLIP prompt, negative prompt, and seed for a POI."""
    style_suffix = visual_style.get("positive_suffix", "")
    negative = visual_style.get("negative_prompt", "")
    tag_overrides = visual_style.get("visual_tag_overrides", {})
    base_seed = visual_style.get("base_seed", 42)

    parts = [f"{poi['name']}: {poi['description']}"]

    if poi.get("atmosphere"):
        parts.append(poi["atmosphere"])

    # Match POI region against visual tag overrides
    region = poi.get("region", "")
    if region and region in tag_overrides:
        region_style = tag_overrides[region]
        if isinstance(region_style, dict):
            parts.append(region_style.get("positive_suffix", ""))
        else:
            parts.append(region_style)
    else:
        location_text = poi["name"]
        location_tags = resolve_location_tags(location_text, tag_overrides)
        if location_tags != location_text:
            parts.append(location_tags)
        if poi.get("chapter_location"):
            chapter_tags = resolve_location_tags(poi["chapter_location"], tag_overrides)
            if chapter_tags != poi["chapter_location"] and chapter_tags not in parts:
                parts.append(chapter_tags)

    style_tokens = estimate_tokens(style_suffix)
    narrative = ", ".join(parts)
    narrative_tokens = estimate_tokens(narrative)
    if narrative_tokens + style_tokens > TOKEN_LIMIT:
        narrative = truncate_to_tokens(narrative, TOKEN_LIMIT - style_tokens - 10)

    # Style first for landscapes (genre atmosphere sets the scene)
    positive = f"{style_suffix}, {narrative}" if style_suffix else narrative

    clip_parts = ["wide establishing shot, scenic vista, atmospheric"]
    if style_suffix:
        clip_parts.append(style_suffix)
    clip = ", ".join(clip_parts)

    seed_key = f"{poi['genre']}:{poi['world']}:{poi['name']}:landscape"
    seed = deterministic_seed(seed_key, base_seed)

    return positive, clip, negative, seed


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate POI landscape images")
    parser.add_argument("--genre", help="Only process this genre pack")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without rendering")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    all_pois = []
    for genre_dir in sorted(GENRE_PACKS_DIR.iterdir()):
        if not genre_dir.is_dir():
            continue
        if args.genre and genre_dir.name != args.genre:
            continue
        pois = collect_pois(genre_dir)
        if pois:
            worlds_seen = {}
            for poi in pois:
                w = poi["world"]
                if w not in worlds_seen:
                    worlds_seen[w] = load_visual_style(genre_dir, w)
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
    )


if __name__ == "__main__":
    asyncio.run(main())
