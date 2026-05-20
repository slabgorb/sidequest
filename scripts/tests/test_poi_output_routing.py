"""Auto-bridge POI render output paths (Story 58-1).

The server's `cover_poi` resolver in
`sidequest-server/sidequest/server/rest.py:215-218` builds the URL from

    f"genre_packs/{genre_slug}/worlds/{world_slug}/assets/poi/{cover_poi}.png"

The POI generator (`scripts/generate_poi_images.py` → `render_common.render_batch`)
currently writes to `genre_packs/<genre>/images/poi/<slug>.png`. Every world
promotion (e.g. burning_peace on 2026-05-19) therefore requires a manual
bridge step that copies the file into the resolver-expected location.

These tests pin the contract: POI renders must land at the resolver's
target path on first write, with no manual bridge step.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.render_common import render_batch, slugify


# ---------------------------------------------------------------------------
# Resolver-side contract (server). Pinned here so that if rest.py drifts, the
# wiring test in this file catches the mismatch even though we don't import
# from sidequest-server (cross-repo install boundary).
#
# Source of truth: sidequest-server/sidequest/server/rest.py:212-219
# ---------------------------------------------------------------------------
SERVER_COVER_POI_REL_TEMPLATE = (
    "genre_packs/{genre_slug}/worlds/{world_slug}/assets/poi/{slug}.png"
)


def _stub_compose(item: dict, visual_style: dict) -> tuple[str, str, str, int]:
    """Minimal compose_fn — render_batch only needs it to not raise in dry_run."""
    return ("subject", "clip", "negative", 42)


def _poi_item(*, genre: str, world: str, name: str = "Hakone Gate") -> dict:
    """A POI item shaped the way collect_pois() produces, with _visual_style attached."""
    return {
        "genre": genre,
        "world": world,
        "name": name,
        "slug": slugify(name),
        "description": "stone gate, cherry blossoms in spring",
        "visual_prompt": "stone torii at mount fuji's foot, cinematic light",
        "catalog_ref": f"where:{world}/{slugify(name)}",
        "_visual_style": {
            "positive_suffix": "",
            "negative_prompt": "",
            "base_seed": 42,
        },
    }


def _portrait_item(*, genre: str, world: str, name: str = "Old Mayor") -> dict:
    """A portrait item — catalog_compose=False path."""
    return {
        "genre": genre,
        "world": world,
        "name": name,
        "slug": slugify(name),
        "description": "weathered face",
        "visual_prompt": "elderly human, soft light",
        "catalog_ref": "",
        "_visual_style": {
            "positive_suffix": "",
            "negative_prompt": "",
            "base_seed": 42,
        },
    }


def _parse_output_path(captured_stdout: str) -> Path:
    """Pull the `Output: <path>` line that render_batch prints in dry_run mode."""
    match = re.search(r"^Output:\s+(\S.*?)\s*$", captured_stdout, re.MULTILINE)
    assert match is not None, (
        f"render_batch(dry_run=True) did not print an Output line; got:\n{captured_stdout}"
    )
    return Path(match.group(1))


# ===========================================================================
# AC: POI output writes to worlds/<w>/assets/poi/ (the resolver's location)
# ===========================================================================


async def test_poi_render_writes_to_world_scoped_assets_poi(capsys):
    """POI generator must write to `genre_packs/<genre>/worlds/<world>/assets/poi/`.

    Today render_common.render_batch routes to `<genre>/images/poi/`
    regardless of world — this test fails until the generator is world-aware.
    """
    items = [_poi_item(genre="elemental_harmony", world="burning_peace")]

    await render_batch(
        items,
        _stub_compose,
        tier="landscape",
        image_subdir="poi",
        dry_run=True,
        catalog_compose=True,
    )

    out_path = _parse_output_path(capsys.readouterr().out)
    expected_suffix = Path(
        "elemental_harmony/worlds/burning_peace/assets/poi/hakone_gate.png"
    )
    assert str(out_path).endswith(str(expected_suffix)), (
        f"POI landed at {out_path}; expected suffix {expected_suffix}. "
        f"The server's cover_poi resolver can only find files under "
        f"worlds/<world>/assets/poi/."
    )


# ===========================================================================
# AC: POI output is NOT written to legacy genre/images/poi/
# ===========================================================================


async def test_poi_render_does_not_write_to_legacy_images_poi(capsys):
    """No dual-write: the legacy `<genre>/images/poi/` path must not appear.

    A dual-write (legacy + new location) would leave stale art on disk after
    later regenerations and confuse future audits. Single canonical location.
    """
    items = [_poi_item(genre="elemental_harmony", world="burning_peace")]

    await render_batch(
        items,
        _stub_compose,
        tier="landscape",
        image_subdir="poi",
        dry_run=True,
        catalog_compose=True,
    )

    out_path = _parse_output_path(capsys.readouterr().out)
    posix = out_path.as_posix()
    assert "/images/poi/" not in posix, (
        f"POI output still routed through legacy /images/poi/ path: {out_path}"
    )


# ===========================================================================
# Regression guard: portrait routing unchanged
# ===========================================================================


async def test_portrait_render_path_remains_in_images_portraits(capsys):
    """Portraits keep their current home at `<genre>/images/portraits/`.

    The POI fix must not accidentally drag portrait output into worlds/<w>/.
    Portraits are bound to characters, not worlds, and the portrait_manifest
    resolver expects them at `images/portraits/`. This test passes today and
    must continue to pass after the POI fix.
    """
    items = [_portrait_item(genre="elemental_harmony", world="burning_peace")]

    await render_batch(
        items,
        _stub_compose,
        tier="portrait",
        image_subdir="portraits",
        dry_run=True,
        catalog_compose=False,
    )

    out_path = _parse_output_path(capsys.readouterr().out)
    posix = out_path.as_posix()
    assert "/images/portraits/" in posix, (
        f"Portrait output drifted from images/portraits/: {out_path}"
    )
    assert "/worlds/" not in posix, (
        f"Portrait output incorrectly bridged to a worlds/<w>/ path: {out_path}"
    )


# ===========================================================================
# Cross-repo wiring contract: generator path == server resolver path
# ===========================================================================


async def test_poi_generator_path_matches_server_resolver_template(capsys):
    """The path the generator writes MUST equal the path the server reads.

    Pins the cross-repo contract between
      - scripts/render_common.render_batch    (generator, this repo)
      - sidequest-server/.../rest.py:215-218  (resolver, separate repo)

    If either side drifts (e.g. resolver moves to `/poi/cover/` or generator
    forgets the `assets/` segment), this test fails and forces the change
    to be made in both places at once.
    """
    genre = "elemental_harmony"
    world = "burning_peace"
    name = "Hakone Gate"
    slug = slugify(name)

    # The exact relative path the server's cover_poi resolver constructs:
    server_rel = SERVER_COVER_POI_REL_TEMPLATE.format(
        genre_slug=genre, world_slug=world, slug=slug
    )

    items = [_poi_item(genre=genre, world=world, name=name)]
    await render_batch(
        items,
        _stub_compose,
        tier="landscape",
        image_subdir="poi",
        dry_run=True,
        catalog_compose=True,
    )
    out_path = _parse_output_path(capsys.readouterr().out)

    # The generator writes to an absolute path; the relative tail (from
    # genre_packs/ down) must match the server template exactly.
    out_posix = out_path.as_posix()
    assert out_posix.endswith(server_rel), (
        f"Generator path {out_posix} does not end with the server's "
        f"resolver-expected relative path {server_rel}."
    )


# ===========================================================================
# Server-side resolver contract pin (defense-in-depth)
# ===========================================================================


def test_server_cover_poi_resolver_template_pinned_to_rest_py():
    """Defensive pin: SERVER_COVER_POI_REL_TEMPLATE must match rest.py source.

    If the server changes its resolver path shape, this test fails on the
    constant in this file — forcing the dev to update the wiring contract
    consciously instead of letting a silent skew develop between repos.

    Reads `sidequest-server/sidequest/server/rest.py` to confirm the f-string
    `genre_packs/{genre_slug}/worlds/{world_slug}/assets/poi/{cover_poi}.png`
    is still the canonical resolver path shape.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    rest_py = repo_root / "sidequest-server" / "sidequest" / "server" / "rest.py"
    if not rest_py.exists():
        pytest.skip(f"sidequest-server not cloned at {rest_py}")

    source = rest_py.read_text(encoding="utf-8")
    # The resolver builds an f-string in two halves — match the full shape:
    assert (
        'f"genre_packs/{genre_slug}/worlds/{world_slug}"' in source
        and 'f"/assets/poi/{cover_poi}.png"' in source
    ), (
        "rest.py no longer builds cover_poi paths as "
        "'genre_packs/<genre>/worlds/<world>/assets/poi/<slug>.png'. "
        "Update SERVER_COVER_POI_REL_TEMPLATE in this file AND the generator "
        "routing in scripts/render_common.py to match."
    )


# ===========================================================================
# Path-handling discipline (Python lang-review rule #5)
# ===========================================================================


def test_render_common_uses_pathlib_not_string_concat_for_poi_routing():
    """Path operations must use pathlib, never string concatenation (CWE-838 / lang-review #5).

    Specifically guards against the easy-but-wrong fix:
        out_dir = GENRE_PACKS_DIR / item["genre"] / "worlds/" + item["world"] + "/assets/poi"
    """
    source_path = Path(__file__).resolve().parent.parent / "render_common.py"
    source = source_path.read_text(encoding="utf-8")

    # Heuristic scan: no `+ "/"` or `"/" +` patterns that build path segments
    # from strings. pathlib.Path / "segment" is the only acceptable join.
    assert '+ "/"' not in source, (
        "render_common.py uses string-concat path joining; use pathlib `Path / segment`."
    )
    assert '"/" +' not in source, (
        "render_common.py uses string-concat path joining; use pathlib `Path / segment`."
    )


# ===========================================================================
# Slug stability (cover_poi key must match generated filename slug)
# ===========================================================================


def test_slugify_matches_world_yaml_cover_poi_key_shape():
    """world.yaml authors write `cover_poi: hakone_gate` (lowercase, underscore).
    The generator's slugify(name) must produce the same form, otherwise the
    resolver builds `<key>.png` but the file on disk is `<slug>.png`.

    Real example: world.yaml at
      sidequest-content/genre_packs/elemental_harmony/worlds/burning_peace/world.yaml
    has `cover_poi: hakone_gate` and the POI's display name is "Hakone Gate".
    """
    assert slugify("Hakone Gate") == "hakone_gate"
    # Other real production POI names (from the audit):
    assert slugify("Salt Camp") == "salt_camp"
    assert slugify("The Glenross Arms") == "the_glenross_arms"
    assert slugify("Sangre del Paso Main Street") == "sangre_del_paso_main_street"


# ===========================================================================
# Generator wiring sanity: the world parameter actually reaches render_batch
# ===========================================================================


def test_generate_poi_images_passes_world_to_render_batch():
    """Wiring sanity — generate_poi_images.collect_pois extracts the `world`
    field from the history.yaml path layout, and that value MUST be present
    on every item handed to render_batch.

    If `world` ever stops being attached to items, world-scoped routing
    cannot work (render_batch would have to guess).
    """
    source_path = Path(__file__).resolve().parent.parent / "generate_poi_images.py"
    source = source_path.read_text(encoding="utf-8")
    # The collect_pois() function must build each POI dict with a 'world' key:
    assert '"world": world' in source, (
        "generate_poi_images.collect_pois no longer attaches a 'world' field "
        "to each POI item — world-scoped routing in render_batch will break."
    )
