"""RED tests for Story 65-1 Part B — r2_audit.py YAML-derived gap audit.

Targets the not-yet-existing `scripts.r2_audit` module. Pure pyyaml — no R2
network. The load-bearing tests pin the CORRECT key conventions (derived from
the generators), which differ from the original story prose:
  - POI:      genre_packs/<g>/worlds/<w>/assets/poi/<slug>.png   (NOT images/pois/)
  - Portrait: genre_packs/<g>/worlds/<w>/assets/portraits/<slug>.png  (world-scoped — Story 65-6)
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


def test_expected_keys_portrait_is_world_scoped(tmp_path: Path) -> None:
    # Story 65-6: portraits moved from genre-flat images/portraits/ to
    # world-scoped worlds/<w>/assets/portraits/ (parity with POIs).
    _build_pack(tmp_path)
    keys = expected_keys(tmp_path)
    assert "genre_packs/demo/worlds/village/assets/portraits/jane_doe.png" in keys
    assert "genre_packs/demo/worlds/village/assets/portraits/john_smith.png" in keys
    # The legacy genre-flat convention must NOT appear.
    assert "genre_packs/demo/images/portraits/jane_doe.png" not in keys


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
    assert (
        "genre_packs/demo/worlds/village/assets/portraits/jane_doe.png"
        in result.authored_but_not_rendered
    )
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


# ── Story 65-15: expected_keys() must parse pack audio.yaml ───────────────
#
# DEFECT (Architect audit 2026-06-03): expected_keys() learns music ONLY from
# audio/music/*_input_params.json; it never parses audio.yaml. So every track
# referenced via audio.yaml `path:` is missing from the expected set — shared
# classical_pd/ragtime_pd tracks get mis-flagged as Orphans, and a genuine audio
# 404 (a YAML path with no R2 object) is never caught. The resolution rule is
# canonical — sidequest-server/.../audio_paths.py::resolve_audio_relpath:
#   path startswith "assets/"  -> genre_packs/<path>          (shared, NO slug)
#   else (pack-local)          -> genre_packs/<slug>/<path>
# Manifest keys are literal relpaths (spaces/parens preserved), verified against
# sidequest-content/r2_manifest.json.

# A shared classical_pd track name with spaces + parens, to pin literal
# preservation (the real manifest key form).
_SHARED_TRACK = "assets/audio/classical_pd/Grieg - Morning Mood (Peer Gynt).ogg"
_SHARED_KEY = "genre_packs/assets/audio/classical_pd/Grieg - Morning Mood (Peer Gynt).ogg"
# The WRONG naive key — pack-slug-prefixed — that #338 made invalid.
_SHARED_KEY_WRONG = (
    "genre_packs/demo/assets/audio/classical_pd/Grieg - Morning Mood (Peer Gynt).ogg"
)


def _build_audio_pack(root: Path, audio_yaml: str, genre: str = "demo") -> Path:
    """Minimal content tree: one genre with only an audio.yaml (no POIs/portraits)."""
    gp = root / "genre_packs" / genre
    gp.mkdir(parents=True)
    (gp / "audio.yaml").write_text(textwrap.dedent(audio_yaml), encoding="utf-8")
    return root


_SHARED_AUDIO_YAML = f"""
    mood_tracks:
      exploration:
        - path: {_SHARED_TRACK}
          title: "Morning Mood"
          bpm: 70
"""


def test_expected_keys_shared_audio_path_is_slugless(tmp_path: Path) -> None:
    # AC1: an `assets/`-prefixed audio.yaml path resolves to the shared bucket
    # WITHOUT the pack slug. Spaces and parentheses are preserved verbatim.
    _build_audio_pack(tmp_path, _SHARED_AUDIO_YAML)
    keys = expected_keys(tmp_path)
    assert _SHARED_KEY in keys
    # The naive pack-slug-prefixed key (pre-#338 convention) must NOT appear.
    assert _SHARED_KEY_WRONG not in keys


def test_expected_keys_pack_local_audio_path_is_slug_prefixed(tmp_path: Path) -> None:
    # AC2: a pack-local (non-`assets/`) audio.yaml path resolves under
    # genre_packs/<slug>/.
    _build_audio_pack(
        tmp_path,
        """
        mood_tracks:
          combat:
            - path: audio/music/exploration_full.ogg
              title: "Exploration"
        """,
    )
    keys = expected_keys(tmp_path)
    assert "genre_packs/demo/audio/music/exploration_full.ogg" in keys


def test_expected_keys_absolute_url_audio_path_is_not_a_key(tmp_path: Path) -> None:
    # Edge: resolve_audio_relpath passes http(s):// and server-absolute paths
    # through untouched — they are not R2-managed keys and must not enter the
    # expected set (else they'd be perpetual "authored but not rendered" noise).
    _build_audio_pack(
        tmp_path,
        """
        mood_tracks:
          warm:
            - path: https://cdn.example.com/external.ogg
              title: "External"
        """,
    )
    keys = expected_keys(tmp_path)
    assert not any("external.ogg" in k for k in keys)


def test_audit_does_not_flag_shared_track_as_orphan(tmp_path: Path) -> None:
    # AC3 (headline regression): a shared classical_pd track that is in R2 AND
    # referenced by audio.yaml must NOT be reported as an orphan.
    _build_audio_pack(tmp_path, _SHARED_AUDIO_YAML)
    result = audit(tmp_path, [{"key": _SHARED_KEY}])
    assert _SHARED_KEY not in result.orphans
    # And it is fully accounted for: not a gap of any class.
    assert _SHARED_KEY not in result.authored_but_not_rendered


def test_audit_catches_audio_yaml_404(tmp_path: Path) -> None:
    # AC4 (the symmetric half): a track referenced by audio.yaml whose resolved
    # key is in neither R2 nor on disk MUST be caught as authored-but-not-rendered.
    # Today this is impossible because the key never enters the expected set.
    _build_audio_pack(tmp_path, _SHARED_AUDIO_YAML)
    result = audit(tmp_path, [])  # nothing uploaded, nothing on disk
    assert _SHARED_KEY in result.authored_but_not_rendered


def test_expected_keys_missing_audio_yaml_is_not_an_error(tmp_path: Path) -> None:
    # AC5: audio.yaml is optional. A pack with params-derived music but no
    # audio.yaml must still return the params key and must not raise. (Regression
    # guard for the existing _input_params.json path.)
    _build_pack(tmp_path)  # builds music via theme_input_params.json, no audio.yaml
    keys = expected_keys(tmp_path)
    assert "genre_packs/demo/audio/music/theme.ogg" in keys


def test_expected_keys_audio_yaml_entry_without_path_fails_loudly(tmp_path: Path) -> None:
    # AC6 / rule #8-adjacent (no silent fallback, CLAUDE.md): a mood_tracks entry
    # that is a mapping but missing `path:` is underivable and must raise — mirror
    # of _poi_keys raising on a POI with neither slug nor name.
    _build_audio_pack(
        tmp_path,
        """
        mood_tracks:
          tension:
            - title: "Pathless"
              bpm: 90
        """,
    )
    with pytest.raises(ValueError):
        expected_keys(tmp_path)
