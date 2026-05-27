"""RED tests for Story 65-1 Part B — r2_audit.py YAML-derived gap audit.

Targets the not-yet-existing `scripts.r2_audit` module. Pure pyyaml — no R2
network. The load-bearing tests pin the CORRECT key conventions (derived from
the generators), which differ from the original story prose:
  - POI:      genre_packs/<g>/worlds/<w>/assets/poi/<slug>.png   (NOT images/pois/)
  - Portrait: genre_packs/<g>/images/portraits/<slug>.png        (genre-flat, NOT world-scoped)
  - Music:    genre_packs/<g>/audio/music/<track>.ogg
See sprint/context/context-story-65-1.md and scripts/render_common.render_batch.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from scripts.r2_audit import audit, expected_keys, format_report, main


def _build_pack(root: Path) -> Path:
    """Synthetic content tree: one genre 'demo', one world 'village'."""
    gp = root / "genre_packs" / "demo"
    world = gp / "worlds" / "village"
    world.mkdir(parents=True)
    # Real history.yaml shapes `chapters:` as a LIST of chapter dicts (see
    # genre_packs/*/worlds/*/history.yaml), not a mapping — the fixture must
    # match reality or the audit passes tests but crashes on real data.
    (world / "history.yaml").write_text(
        textwrap.dedent(
            """
            chapters:
              - id: ch1
                label: Chapter One
                points_of_interest:
                  - slug: the_inn
                    name: The Inn
                  - slug: the_well
                    name: The Well
            """
        ),
        encoding="utf-8",
    )
    (world / "portrait_manifest.yaml").write_text(
        textwrap.dedent(
            """
            characters:
              - name: Jane Doe
                role: innkeeper
              - name: John Smith
                role: farmer
            """
        ),
        encoding="utf-8",
    )
    music = gp / "audio" / "music"
    music.mkdir(parents=True)
    (music / "theme_input_params.json").write_text("{}", encoding="utf-8")
    return root


def _write_manifest(root: Path, keys: list[str]) -> Path:
    path = root / "r2_manifest.json"
    entries = [
        {"key": k, "md5": "0", "size_bytes": 1, "uploaded_at": "t", "source": "s"}
        for k in keys
    ]
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


# ── AC2: expected_keys — correct conventions ─────────────────────────────

def test_expected_keys_poi_uses_world_assets_poi(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    keys = expected_keys(tmp_path)
    assert "genre_packs/demo/worlds/village/assets/poi/the_inn.png" in keys
    assert "genre_packs/demo/worlds/village/assets/poi/the_well.png" in keys
    # The wrong convention from the original story prose must NOT appear.
    assert "genre_packs/demo/images/pois/the_inn.png" not in keys


def test_expected_keys_portrait_is_genre_flat(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    keys = expected_keys(tmp_path)
    assert "genre_packs/demo/images/portraits/jane_doe.png" in keys
    assert "genre_packs/demo/images/portraits/john_smith.png" in keys
    # Portraits are genre-flat, not world-scoped.
    assert "genre_packs/demo/worlds/village/images/portraits/jane_doe.png" not in keys


def test_expected_keys_music(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    keys = expected_keys(tmp_path)
    assert "genre_packs/demo/audio/music/theme.ogg" in keys


def test_expected_keys_poi_without_slug_falls_back_to_name(tmp_path: Path) -> None:
    # Real history.yaml has narrative POIs with a name but no slug; the renderer
    # falls back to slugify(name), so the audit must too (not raise).
    gp = tmp_path / "genre_packs" / "demo" / "worlds" / "v"
    gp.mkdir(parents=True)
    (gp / "history.yaml").write_text(
        "chapters:\n  - id: c\n    points_of_interest:\n      - name: The Study\n",
        encoding="utf-8",
    )
    keys = expected_keys(tmp_path)
    assert "genre_packs/demo/worlds/v/assets/poi/the_study.png" in keys


def test_expected_keys_poi_without_slug_or_name_fails_loudly(tmp_path: Path) -> None:
    # No silent fallback (CLAUDE.md): a POI with neither slug nor name is
    # underivable and must raise.
    gp = tmp_path / "genre_packs" / "demo" / "worlds" / "v"
    gp.mkdir(parents=True)
    (gp / "history.yaml").write_text(
        "chapters:\n  - id: c\n    points_of_interest:\n      - type: room\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        expected_keys(tmp_path)


# ── AC2: audit categorization ────────────────────────────────────────────

def test_audit_flags_authored_but_not_rendered(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    # Only music uploaded; POIs + portraits are authored but absent from R2.
    result = audit(tmp_path, [{"key": "genre_packs/demo/audio/music/theme.ogg"}])
    assert "genre_packs/demo/worlds/village/assets/poi/the_inn.png" in result.authored_but_not_rendered
    assert "genre_packs/demo/images/portraits/jane_doe.png" in result.authored_but_not_rendered
    # The uploaded music key must NOT be flagged.
    assert "genre_packs/demo/audio/music/theme.ogg" not in result.authored_but_not_rendered


def test_audit_flags_orphans(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    result = audit(tmp_path, [{"key": "genre_packs/demo/images/portraits/ghost.png"}])
    assert "genre_packs/demo/images/portraits/ghost.png" in result.orphans


def test_audit_flags_rendered_but_not_uploaded(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    # A local POI render exists on disk but is not in the manifest.
    local = tmp_path / "genre_packs/demo/worlds/village/assets/poi/the_inn.png"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(b"img")
    result = audit(tmp_path, [])
    assert "genre_packs/demo/worlds/village/assets/poi/the_inn.png" in result.rendered_but_not_uploaded


def test_audit_clean_when_everything_uploaded(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    keys = list(expected_keys(tmp_path))
    result = audit(tmp_path, [{"key": k} for k in keys])
    assert not result.authored_but_not_rendered
    assert not result.orphans


# ── AC3: report readability ──────────────────────────────────────────────

def test_format_report_includes_context_and_summary(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    result = audit(tmp_path, [])
    report = format_report(result)
    assert "the_inn" in report
    assert "poi" in report.lower()
    assert "expected" in report.lower()  # summary counts present


# ── AC4: CLI exit codes ──────────────────────────────────────────────────

def test_main_exits_zero_when_clean(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    keys = list(expected_keys(tmp_path))
    manifest = _write_manifest(tmp_path, keys)
    rc = main(["--content-root", str(tmp_path), "--manifest", str(manifest)])
    assert rc == 0


def test_main_exits_one_on_gap(tmp_path: Path) -> None:
    _build_pack(tmp_path)
    manifest = _write_manifest(tmp_path, [])  # nothing uploaded => gaps
    rc = main(["--content-root", str(tmp_path), "--manifest", str(manifest)])
    assert rc == 1
