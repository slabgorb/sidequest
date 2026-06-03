"""Reconcile shared public-domain music DEMAND ∩ SUPPLY ∖ already-rendered.

This cross-repo media script:

1. Collects the shared-bucket music *demand* by reading every pack
   ``audio.yaml`` and pulling out the ``assets/audio/<bucket>/<file>``
   references (the shared PD library for ``<bucket>``, which defaults to
   ``classical_pd``; pack-local tracks are ignored).
2. Joins that demand against the *supply* — the composer catalog at
   ``genre_packs/assets/audio/<bucket>/catalog.yaml`` (``<bucket>`` defaults to
   ``classical_pd``). Any demanded track absent from the catalog raises
   :class:`UncataloguedTrackError` (loud, per CLAUDE.md "No Silent Fallbacks").
3. Drops anything already in R2 (per ``r2_manifest.json``).
4. Renders the gap via the ``composer`` CLI (subprocess — composer is left
   unmodified; the catalog entries ARE valid composer manifest entries).
5. Uploads the new OGGs via the existing ``scripts.r2_sync_packs.sync(...)``.
6. Regenerates ``r2_manifest.json`` from the live bucket via
   ``scripts/r2_manifest_from_bucket.py``.

The shared bucket is selected with ``--bucket`` (default ``classical_pd``);
e.g. ``--bucket ragtime_pd`` reconciles ``assets/audio/ragtime_pd/`` against the
catalog at ``genre_packs/assets/audio/ragtime_pd/catalog.yaml``.

Usage:
    uv run python scripts/render_pd_audio.py [--bucket <name>] [--pack <name>] [--dry-run] [--force]
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import tempfile
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = _ROOT / "sidequest-content"
COMPOSER_ROOT = _ROOT / "sidequest-composer"

MANIFEST_PATH = CONTENT_ROOT / "r2_manifest.json"
DEFAULT_BUCKET = "classical_pd"

# How audio.yaml spells demand vs. the r2 key prefix a shared bucket uses.
# These key forms MUST stay in lockstep with the server's shared-bucket rule in
# sidequest-server/sidequest/genre/audio_paths.py (`resolve_audio_relpath`,
# scope="shared"): an `assets/...` track resolves to `genre_packs/<rel>`. If
# that convention changes, update both sides together.


def shared_audio_prefix(bucket: str) -> str:
    """How audio.yaml spells a track in this shared bucket (demand side)."""
    return f"assets/audio/{bucket}/"


def shared_rel(bucket: str) -> str:
    """The R2 key prefix for this shared bucket (supply / manifest side)."""
    return f"genre_packs/assets/audio/{bucket}"


def shared_dir(bucket: str) -> Path:
    """The local directory the composer renders this bucket's OGGs into."""
    return CONTENT_ROOT / "genre_packs" / "assets" / "audio" / bucket


def catalog_path(bucket: str) -> Path:
    """The composer catalog (supply spec) for this shared bucket."""
    return shared_dir(bucket) / "catalog.yaml"


logger = logging.getLogger("render_pd_audio")


class UncataloguedTrackError(RuntimeError):
    """A demanded shared-PD track has no catalog entry (loud, no fallback)."""


def collect_demand(audio_configs: list[dict], *, shared_audio_prefix: str) -> set[str]:
    """Return the set of shared-PD filenames demanded across the audio configs.

    A track is "shared" if its ``path`` starts with ``shared_audio_prefix``
    (e.g. ``assets/audio/classical_pd/``); tracks for other buckets and
    pack-local paths (e.g. ``audio/music/foo.ogg``) are ignored.
    """
    demand: set[str] = set()
    for cfg in audio_configs:
        for tracks in (cfg.get("mood_tracks") or {}).values():
            for track in tracks:
                path = track.get("path", "")
                if path.startswith(shared_audio_prefix):
                    demand.add(path[len(shared_audio_prefix):])
    return demand


def load_catalog(path: Path) -> dict[str, dict]:
    """Load the composer catalog, keyed by ``out_name``."""
    if not path.is_file():
        raise FileNotFoundError(f"catalog not found at {path}")
    data = yaml.safe_load(path.read_text())
    return {e["out_name"]: e for e in data.get("entries", [])}


def plan_renders(
    demand: set[str],
    catalog: dict[str, dict],
    *,
    already_keys: set[str],
    shared_rel: str,
    catalog_path: Path | None = None,
) -> list[dict]:
    """Return catalog entries to render: demanded, catalogued, not yet in R2.

    Keys are formed as ``{shared_rel}/{name}`` to match the R2 manifest.
    Raises :class:`UncataloguedTrackError` if any demanded track is missing
    from the catalog (No Silent Fallbacks).
    """
    missing = sorted(d for d in demand if d not in catalog)
    if missing:
        listing = "\n  ".join(missing)
        where = f" in {catalog_path}" if catalog_path is not None else ""
        raise UncataloguedTrackError(
            f"{len(missing)} demanded shared-PD track(s) have no catalog entry"
            f"{where}:\n  {listing}\n"
            "Add a catalog entry (with a fetchable PD source_url) for each."
        )
    return [
        catalog[name]
        for name in sorted(demand)
        if f"{shared_rel}/{name}" not in already_keys
    ]


def _audio_configs(pack: str | None) -> list[dict]:
    """Load every relevant ``audio.yaml`` (one pack or all packs)."""
    base = _ROOT / "sidequest-content" / "genre_packs"
    root = base / pack if pack else base
    configs: list[dict] = []
    for path in sorted(root.glob("**/audio.yaml")):
        data = yaml.safe_load(path.read_text())
        if data:
            configs.append(data)
    return configs


def _already_keys() -> set[str]:
    """Return the set of R2 keys already recorded in ``r2_manifest.json``."""
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"r2_manifest.json not found at {MANIFEST_PATH}")
    entries = json.loads(MANIFEST_PATH.read_text())
    return {e["key"] for e in entries}


def _composer_entries(todo: list[dict]) -> list[dict]:
    """Return copies of ``todo`` with a single trailing ``.ogg`` stripped.

    The composer (pipeline.py) builds its output filename as
    ``out_dir / f"{out_name}.{output_format}"`` — it *appends* ``.ogg``. Our
    catalog ``out_name`` already ends in ``.ogg`` (it equals the audio.yaml
    demand filename and the R2 key), so we must hand the composer the bare stem
    or it produces ``<name>.ogg.ogg``. Originals are left untouched: ``new_oggs``
    later relies on the original ``out_name`` (with ``.ogg``), which equals the
    composer's actual output ``<stem>.ogg``.
    """
    return [
        {**entry, "out_name": entry["out_name"].removesuffix(".ogg")}
        for entry in todo
    ]


def _write_temp_manifest(entries: list[dict]) -> Path:
    """Write a composer manifest holding ``entries`` and return its path."""
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="pd_manifest_", delete=False, encoding="utf-8"
    )
    with fh:
        yaml.safe_dump(
            {"loudness": -16, "entries": _composer_entries(entries)},
            fh,
            allow_unicode=True,
            sort_keys=False,
        )
    return Path(fh.name)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bucket",
        default=DEFAULT_BUCKET,
        help=f"Shared PD-music bucket to reconcile (default: {DEFAULT_BUCKET}).",
    )
    parser.add_argument("--pack", default=None, help="Restrict demand to one pack.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report the plan; render nothing."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the R2 manifest (treat everything as not-yet-rendered).",
    )
    args = parser.parse_args(argv)

    bucket = args.bucket
    bucket_dir = shared_dir(bucket)
    bucket_rel = shared_rel(bucket)
    bucket_catalog_path = catalog_path(bucket)

    catalog = load_catalog(bucket_catalog_path)
    demand = collect_demand(
        _audio_configs(args.pack), shared_audio_prefix=shared_audio_prefix(bucket)
    )
    already = set() if args.force else _already_keys()

    try:
        todo = plan_renders(
            demand,
            catalog,
            already_keys=already,
            shared_rel=bucket_rel,
            catalog_path=bucket_catalog_path,
        )
    except UncataloguedTrackError as e:
        # Fail loud but clean: operator sees the multi-line "no catalog entry"
        # message and a non-zero exit, not a Python traceback. Still names every
        # missing track (No Silent Fallbacks).
        logger.error("%s", e)
        return 1

    logger.info(
        "demand=%d catalogued=%d already=%d to-render=%d",
        len(demand),
        len(catalog),
        len(demand) - len(todo),
        len(todo),
    )

    if not todo:
        logger.info("Nothing to render — supply already covers demand.")
        return 0

    if args.dry_run:
        for entry in todo:
            logger.info("DRY would render: %s", entry["out_name"])
        return 0

    # --- Render via the composer CLI (subprocess; composer unmodified) -------
    manifest = _write_temp_manifest(todo)
    bucket_dir.mkdir(parents=True, exist_ok=True)
    logger.info("rendering %d track(s) into %s", len(todo), bucket_dir)
    subprocess.run(
        ["uv", "run", "composer", "render", str(manifest), "--out-dir", str(bucket_dir)],
        cwd=COMPOSER_ROOT,
        check=True,
    )

    # --- Upload the new OGGs via the existing R2 sync ------------------------
    # Original out_name (with .ogg) == the composer's actual output filename:
    # composer wrote `<stem>.ogg` from the stem in _composer_entries, and
    # out_name == f"{stem}.ogg". So this points at the real file on disk.
    new_oggs = [bucket_dir / e["out_name"] for e in todo]
    # Deferred import: keep boto3's import cost off the --dry-run path.
    from scripts import r2_sync_packs  # noqa: PLC0415

    counts = r2_sync_packs.sync(content_root=CONTENT_ROOT, files=new_oggs)
    logger.info(
        "uploaded=%d skipped=%d bytes_uploaded=%d",
        counts["uploaded"],
        counts["skipped"],
        counts["bytes_uploaded"],
    )

    # --- Regenerate the manifest from the live bucket ------------------------
    logger.info("regenerating r2_manifest.json from bucket")
    subprocess.run(
        ["uv", "run", "--project", ".", "python", "scripts/r2_manifest_from_bucket.py"],
        cwd=_ROOT,
        check=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
