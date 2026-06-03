# scripts/tests/test_feature_inventory.py
"""Tests for the feature-inventory generator (Phase 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.feature_inventory_verify import load_span_constants

ROOT = Path(__file__).parent.parent.parent  # repo root


def test_load_span_constants_parses_literals(tmp_path):
    spans_dir = tmp_path / "spans"
    spans_dir.mkdir()
    (spans_dir / "turn.py").write_text(
        'SPAN_TURN = "turn"\n'
        'SPAN_TURN_BARRIER = "turn.barrier"\n'
        "SPAN_ROUTES[SPAN_TURN] = SpanRoute(...)\n"
    )
    (spans_dir / "_core.py").write_text("SPAN_ROUTES = {}\n")
    names = load_span_constants(spans_dir)
    assert names == {"turn", "turn.barrier"}


def test_load_span_constants_against_real_registry():
    """Wiring: the real telemetry/spans dir parses and contains known spans."""
    real = ROOT / "sidequest-server" / "sidequest" / "telemetry" / "spans"
    names = load_span_constants(real)
    assert "turn" in names
    assert "turn.barrier" in names
    assert len(names) > 20  # registry is substantial


from scripts.feature_inventory_verify import wiring_test_exists, resolve_module


def test_wiring_test_exists(tmp_path):
    (tmp_path / "a.test.tsx").write_text("// test")
    assert wiring_test_exists("a.test.tsx", tmp_path) is True
    assert wiring_test_exists("missing.test.tsx", tmp_path) is False


def test_resolve_module_server_dotted(tmp_path):
    server = tmp_path / "sidequest-server" / "sidequest"
    (server / "game").mkdir(parents=True)
    (server / "game" / "encounter.py").write_text("# mod")
    # dotted and path forms both resolve under sidequest-server/sidequest/
    assert resolve_module("game.encounter", tmp_path) is not None
    assert resolve_module("game/encounter.py", tmp_path) is not None
    assert resolve_module("game.missing", tmp_path) is None


def test_resolve_module_ui_component(tmp_path):
    ui = tmp_path / "sidequest-ui" / "src" / "components"
    ui.mkdir(parents=True)
    (ui / "ConfrontationOverlay.tsx").write_text("// component")
    assert resolve_module("ConfrontationOverlay", tmp_path) is not None
    assert resolve_module("NopeOverlay", tmp_path) is None


# append to scripts/tests/test_feature_inventory.py
from scripts.feature_inventory_verify import adr_status, draft_world_is_draft


def test_adr_status_reads_frontmatter(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "033-confrontation.md").write_text(
        "---\nid: 33\nstatus: accepted\n---\n# body\n"
    )
    assert adr_status(33, tmp_path) == "accepted"
    assert adr_status(999, tmp_path) is None


def test_draft_world_predicate(tmp_path):
    world = tmp_path / "sidequest-content" / "genre_packs" / "tea_and_murder" / "worlds" / "blackthorn_moor"
    world.mkdir(parents=True)
    (world / "world.yaml").write_text("name: Blackthorn Moor\ndraft: true\n")
    assert draft_world_is_draft("tea_and_murder/blackthorn_moor", tmp_path) is True

    live = tmp_path / "sidequest-content" / "genre_packs" / "tea_and_murder" / "worlds" / "glenross"
    live.mkdir(parents=True)
    (live / "world.yaml").write_text("name: Glenross\n")  # no draft key
    assert draft_world_is_draft("tea_and_murder/glenross", tmp_path) is False


# append to scripts/tests/test_feature_inventory.py
from scripts.feature_inventory_verify import load_manifest, ManifestError


def test_load_manifest_parses_categories(tmp_path):
    d = tmp_path / "docs" / "feature-inventory"
    d.mkdir(parents=True)
    (d / "confrontation-engine.yaml").write_text(
        "category: Confrontation Engine\n"
        "features:\n"
        "  - id: confrontation_engine\n"
        "    name: Confrontation engine\n"
        "    modules: [game/encounter.py]\n"
        "    ui: ConfrontationOverlay\n"
        "    manual_test: Take a turn that triggers a confrontation\n"
        "    status: live_wired\n"
        "    evidence:\n"
        "      spans: [confrontation.resolved]\n"
        "      wiring_tests: [sidequest-ui/src/__tests__/confrontation-wiring.test.tsx]\n"
    )
    cats = load_manifest(tmp_path / "docs" / "feature-inventory")
    assert cats[0].category == "Confrontation Engine"
    assert cats[0].features[0].id == "confrontation_engine"
    assert cats[0].features[0].status == "live_wired"


def test_load_manifest_rejects_bad_status(tmp_path):
    d = tmp_path / "docs" / "feature-inventory"
    d.mkdir(parents=True)
    (d / "x.yaml").write_text(
        "category: X\nfeatures:\n  - id: a\n    name: A\n    status: bogus\n"
    )
    with pytest.raises(ManifestError, match="bogus"):
        load_manifest(d)


def test_load_manifest_rejects_duplicate_ids(tmp_path):
    d = tmp_path / "docs" / "feature-inventory"
    d.mkdir(parents=True)
    (d / "a.yaml").write_text("category: A\nfeatures:\n  - id: dup\n    name: A1\n    status: engineering\n")
    (d / "b.yaml").write_text("category: B\nfeatures:\n  - id: dup\n    name: B1\n    status: engineering\n")
    with pytest.raises(ManifestError, match="duplicate id"):
        load_manifest(d)


# append to scripts/tests/test_feature_inventory.py
from scripts.feature_inventory_verify import verify_feature, VerifyContext, Feature


def _ctx(tmp_path, span_names=("confrontation.resolved",)):
    return VerifyContext(
        repo_root=tmp_path,
        span_names=set(span_names),
    )


def test_live_wired_passes_with_span_and_wiring(tmp_path):
    wt = tmp_path / "wt.test.tsx"
    wt.write_text("// test")
    f = Feature(
        id="x", name="X", status="live_wired",
        evidence={"spans": ["confrontation.resolved"], "wiring_tests": ["wt.test.tsx"]},
    )
    ok, reason = verify_feature(f, _ctx(tmp_path))
    assert ok is True, reason


def test_live_wired_fails_when_span_unregistered(tmp_path):
    f = Feature(
        id="x", name="X", status="live_wired",
        evidence={"spans": ["ghost.span"], "wiring_tests": ["wt.test.tsx"]},
    )
    ok, reason = verify_feature(f, _ctx(tmp_path))
    assert ok is False
    assert "ghost.span" in reason


def test_module_existence_failure_blocks_any_status(tmp_path):
    f = Feature(
        id="x", name="X", status="engineering",
        modules=["game/does_not_exist.py"],
    )
    ok, reason = verify_feature(f, _ctx(tmp_path))
    assert ok is False
    assert "does_not_exist" in reason
