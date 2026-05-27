"""Story 65-1 Part B — YAML-derived R2 gap audit.

Builds the "should exist" R2 key set from authored YAML and diffs it against the
committed ``r2_manifest.json`` (and local files), reporting three gap classes:

  - authored-but-not-rendered: in YAML, absent from R2 and from disk
  - rendered-but-not-uploaded: on disk, absent from R2
  - orphans: in R2, no YAML references it

Key conventions are derived from the generators (``scripts/render_common.py``
``render_batch`` + ``generate_portrait_images``), NOT from prose — R2 keys are
the 1:1 local-relative paths the uploader mirrors:

  - POI:      genre_packs/<g>/worlds/<world>/assets/poi/<slug>.png
  - Portrait: genre_packs/<g>/images/portraits/<slug>.png   (genre-flat)
  - Music:    genre_packs/<g>/audio/music/<track>.ogg

Per CLAUDE.md (no silent fallbacks) malformed YAML fails loudly. Exits non-zero
on any gap.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from scripts.r2_manifest import load_manifest
from scripts.render_common import slugify as _poi_slugify

# Local media extensions that map 1:1 to R2 keys (subset of r2_sync_packs).
_MEDIA_EXTENSIONS = frozenset({".png", ".ogg"})

_MUSIC_PARAMS_SUFFIX = "_input_params.json"


def _slugify_name(name: str) -> str:
    """Portrait slug from a character name.

    Mirrors ``generate_portrait_images._slugify_name`` (which itself mirrors the
    daemon's ``CharacterCatalog._slugify_name``) so this audit derives the same
    ``<slug>.png`` the renderer writes. Kept local to keep the audit boto3- and
    daemon-import-free.
    """
    lowered = name.strip().lower()
    collapsed = re.sub(r"\s+", "_", lowered)
    return re.sub(r"[^a-z0-9_-]", "", collapsed)


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


@dataclass
class AuditResult:
    """Categorized gaps plus headline counts for the report."""

    authored_but_not_rendered: list[str] = field(default_factory=list)
    rendered_but_not_uploaded: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    expected_count: int = 0
    uploaded_count: int = 0

    @property
    def has_gaps(self) -> bool:
        return bool(
            self.authored_but_not_rendered
            or self.rendered_but_not_uploaded
            or self.orphans
        )


def _poi_keys(genre: str, genre_dir: Path) -> set[str]:
    keys: set[str] = set()
    for history_path in sorted(genre_dir.rglob("history.yaml")):
        rel_parts = history_path.relative_to(genre_dir).parts
        world = rel_parts[1] if len(rel_parts) >= 2 and rel_parts[0] == "worlds" else None
        data = _load_yaml(history_path)
        chapters = data.get("chapters") or []
        # Real history.yaml defines `chapters:` as a list of chapter dicts; a
        # mapping form is also tolerated. Normalize to an iterable of dicts.
        chapter_dicts = chapters if isinstance(chapters, list) else list(chapters.values())
        for chapter in chapter_dicts:
            if not isinstance(chapter, dict):
                continue
            for poi in chapter.get("points_of_interest", []) or []:
                # Mirror render_batch's slug resolution: an explicit `slug` is
                # used verbatim; otherwise the renderer falls back to
                # slugify(name). A POI with neither slug nor name is
                # underivable — fail loudly (no silent skip).
                slug = poi.get("slug")
                if not slug:
                    name = poi.get("name")
                    if not name:
                        raise ValueError(
                            f"POI entry has neither 'slug' nor 'name' in "
                            f"{history_path}: {poi!r}"
                        )
                    slug = _poi_slugify(name)
                if world is None:
                    raise ValueError(
                        f"POI {slug!r} in genre-level {history_path} has no world; "
                        f"POIs must live under worlds/<world>/history.yaml"
                    )
                keys.add(f"genre_packs/{genre}/worlds/{world}/assets/poi/{slug}.png")
    return keys


def _portrait_keys(genre: str, genre_dir: Path) -> set[str]:
    keys: set[str] = set()
    for manifest_path in sorted(genre_dir.rglob("portrait_manifest.yaml")):
        data = _load_yaml(manifest_path)
        for char in data.get("characters", []) or []:
            name = char.get("name")
            if not name and not char.get("id"):
                raise ValueError(
                    f"portrait entry missing both 'name' and 'id' in {manifest_path}: {char!r}"
                )
            slug = char.get("id") or _slugify_name(name)
            keys.add(f"genre_packs/{genre}/images/portraits/{slug}.png")
    return keys


def _music_keys(genre: str, genre_dir: Path) -> set[str]:
    keys: set[str] = set()
    music_dir = genre_dir / "audio" / "music"
    if not music_dir.is_dir():
        return keys
    for params in sorted(music_dir.glob(f"*{_MUSIC_PARAMS_SUFFIX}")):
        track = params.name[: -len(_MUSIC_PARAMS_SUFFIX)]
        keys.add(f"genre_packs/{genre}/audio/music/{track}.ogg")
    return keys


def expected_keys(content_root: Path) -> set[str]:
    """The set of R2 keys that authored YAML says should exist."""
    content_root = Path(content_root)
    packs_dir = content_root / "genre_packs"
    if not packs_dir.is_dir():
        raise FileNotFoundError(f"genre_packs/ not found under {content_root}")
    keys: set[str] = set()
    for genre_dir in sorted(packs_dir.iterdir()):
        if not genre_dir.is_dir():
            continue
        genre = genre_dir.name
        keys |= _poi_keys(genre, genre_dir)
        keys |= _portrait_keys(genre, genre_dir)
        keys |= _music_keys(genre, genre_dir)
    return keys


def _local_media_keys(content_root: Path) -> set[str]:
    content_root = Path(content_root)
    packs_dir = content_root / "genre_packs"
    keys: set[str] = set()
    if not packs_dir.is_dir():
        return keys
    for path in packs_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in _MEDIA_EXTENSIONS:
            keys.add(path.relative_to(content_root).as_posix())
    return keys


def _asset_type(key: str) -> str:
    if "/assets/poi/" in key:
        return "POI"
    if "/images/portraits/" in key:
        return "portrait"
    if "/audio/music/" in key:
        return "music"
    return "asset"


def audit(content_root: Path, manifest: list[dict[str, object]]) -> AuditResult:
    """Diff authored YAML against the manifest (and local disk)."""
    expected = expected_keys(content_root)
    manifest_keys = {str(e["key"]) for e in manifest}
    local = _local_media_keys(content_root)

    return AuditResult(
        authored_but_not_rendered=sorted(expected - manifest_keys - local),
        rendered_but_not_uploaded=sorted((expected & local) - manifest_keys),
        orphans=sorted(manifest_keys - expected),
        expected_count=len(expected),
        uploaded_count=len(manifest_keys),
    )


def format_report(result: AuditResult) -> str:
    """Human-readable report with per-entry asset type and a summary."""
    lines = ["R2 Asset Audit Report", "=" * 21, ""]

    def _section(title: str, keys: list[str]) -> None:
        lines.append(f"{title}:")
        if not keys:
            lines.append("  (none)")
        for key in keys:
            lines.append(f"  - {key} ({_asset_type(key)})")
        lines.append("")

    _section("Authored but not rendered", result.authored_but_not_rendered)
    _section("Rendered but not uploaded", result.rendered_but_not_uploaded)
    _section("Orphans (in R2, no YAML)", result.orphans)

    gaps = (
        len(result.authored_but_not_rendered)
        + len(result.rendered_but_not_uploaded)
        + len(result.orphans)
    )
    lines += [
        "Summary:",
        f"  Expected assets: {result.expected_count}",
        f"  Uploaded assets: {result.uploaded_count}",
        f"  Gaps found: {gaps}",
        f"  Exit code: {1 if result.has_gaps else 0}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--content-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sidequest-content",
        help="Path to the sidequest-content checkout",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to r2_manifest.json (default: <content-root>/r2_manifest.json)",
    )
    args = parser.parse_args(argv)

    manifest_path = args.manifest or (args.content_root / "r2_manifest.json")
    manifest = load_manifest(manifest_path)

    result = audit(args.content_root, manifest)
    print(format_report(result))
    return 1 if result.has_gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
