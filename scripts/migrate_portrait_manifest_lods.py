"""Stub long/short/background LODs on existing portrait_manifest.yaml files.

Preserves existing `appearance` as `descriptions.solo`; flags remaining LODs
for human authoring with TODO markers. No silent fallback — the composer
will fail-loud when a TODO LOD is requested.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

_LODS = ("solo", "long", "short", "background")


def migrate_manifest(path: Path, *, in_place: bool = False) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    changed = False

    for char in data.get("characters", []):
        descriptions = char.get("descriptions")
        if descriptions and all(lod in descriptions for lod in _LODS):
            continue  # already migrated

        appearance = char.get("appearance", "")
        char["descriptions"] = {
            "solo": appearance,
            "long": f"TODO: author long LOD (15-25 tok) for {char.get('name', char.get('id', '?'))}",
            "short": f"TODO: author short LOD (5-10 tok) for {char.get('name', char.get('id', '?'))}",
            "background": f"TODO: author background LOD (1-3 tok) for {char.get('name', char.get('id', '?'))}",
        }
        char.setdefault(
            "id",
            char.get("name", "unknown").lower().replace(" ", "_"),
        )
        char["_needs_lod_authoring"] = True
        char.setdefault("default_pose", "neutral, standing")
        changed = True

    if changed and in_place:
        path.write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    for path in args.manifests:
        migrate_manifest(path, in_place=args.in_place)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
