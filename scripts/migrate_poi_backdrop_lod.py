"""Stub `backdrop` LOD on existing POI visual_prompt strings in history.yaml.

Promotes the existing string to `solo`; flags `backdrop` with a TODO for
human authoring.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def migrate_history(path: Path, *, in_place: bool = False) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    changed = False
    for chapter in data.get("chapters", []):
        for poi in chapter.get("points_of_interest", []):
            vp = poi.get("visual_prompt")
            if isinstance(vp, str):
                poi["visual_prompt"] = {
                    "solo": vp,
                    "backdrop": f"TODO: author backdrop LOD for {poi.get('slug', '?')}",
                }
                changed = True
            env = poi.get("environment")
            if isinstance(env, str):
                poi["environment"] = {
                    "solo": env,
                    "backdrop": f"TODO: author backdrop environment for {poi.get('slug', '?')}",
                }
                changed = True
    if changed and in_place:
        path.write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("histories", nargs="+", type=Path)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    for path in args.histories:
        migrate_history(path, in_place=args.in_place)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
