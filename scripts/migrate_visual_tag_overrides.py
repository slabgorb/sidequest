"""Port `visual_tag_overrides` (from world visual_style.yaml) into either
the matching archetypal place's environment description, or into a human-
review report for unmatched overrides.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def migrate_world(genre_root: Path, world: str, *, in_place: bool = False) -> dict:
    style_path = genre_root / "worlds" / world / "visual_style.yaml"
    places_path = genre_root / "places.yaml"
    style_data = yaml.safe_load(style_path.read_text()) or {}
    overrides = style_data.get("visual_tag_overrides", {}) or {}
    places_data = yaml.safe_load(places_path.read_text()) if places_path.exists() else {}
    places_data = places_data or {}

    matched: list[str] = []
    unmatched: list[str] = []

    for slug, tokens in overrides.items():
        if slug in places_data:
            env = places_data[slug].setdefault("environment", {})
            env["solo"] = (env.get("solo", "") + ", " + tokens).strip(", ")
            matched.append(slug)
        else:
            unmatched.append(slug)

    if in_place:
        places_path.write_text(yaml.safe_dump(places_data, sort_keys=False))
        style_data.pop("visual_tag_overrides", None)
        style_path.write_text(yaml.safe_dump(style_data, sort_keys=False))

    return {"matched": matched, "unmatched": unmatched}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("genre_root", type=Path)
    parser.add_argument("world")
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    report = migrate_world(args.genre_root, args.world, in_place=args.in_place)
    print(f"Matched ({len(report['matched'])}): {report['matched']}")
    print(f"Unmatched ({len(report['unmatched'])}): {report['unmatched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
