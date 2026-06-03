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
