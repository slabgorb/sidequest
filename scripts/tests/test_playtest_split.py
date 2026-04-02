"""Tests for story 21-1: playtest.py module split.

Verifies that playtest.py is correctly split into four modules:
- playtest.py — CLI, main(), mode dispatch
- playtest_dashboard.py — Dashboard HTML/JS, WebSocket, HTTP serving
- playtest_messages.py — MSG_STYLES, render_message(), message helpers
- playtest_otlp.py — Empty skeleton for story 21-2
"""

import importlib
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent


# ── AC-1: playtest.py contains only CLI parsing, main(), and mode dispatch ──


class TestPlaytestMain:
    """playtest.py should contain CLI and mode dispatch, nothing else."""

    def test_main_function_exists(self):
        """main() must be defined in playtest.py."""
        mod = _import_module("playtest")
        assert hasattr(mod, "main"), "playtest.py must export main()"
        assert callable(mod.main)

    def test_run_interactive_exists(self):
        """run_interactive must be accessible from playtest.py."""
        mod = _import_module("playtest")
        assert hasattr(mod, "run_interactive"), (
            "playtest.py must have run_interactive (defined or imported)"
        )

    def test_run_scripted_exists(self):
        """run_scripted must be accessible from playtest.py."""
        mod = _import_module("playtest")
        assert hasattr(mod, "run_scripted"), (
            "playtest.py must have run_scripted (defined or imported)"
        )

    def test_run_multiplayer_exists(self):
        """run_multiplayer must be accessible from playtest.py."""
        mod = _import_module("playtest")
        assert hasattr(mod, "run_multiplayer"), (
            "playtest.py must have run_multiplayer (defined or imported)"
        )

    def test_msg_styles_not_defined_in_main(self):
        """MSG_STYLES must NOT be defined directly in playtest.py — it belongs in playtest_messages."""
        source = (SCRIPTS_DIR / "playtest.py").read_text()
        # MSG_STYLES should be imported, not defined inline
        assert "MSG_STYLES = {" not in source, (
            "MSG_STYLES dict literal must not be in playtest.py — move to playtest_messages.py"
        )

    def test_dashboard_html_not_defined_in_main(self):
        """DASHBOARD_HTML must NOT be defined in playtest.py — it belongs in playtest_dashboard."""
        source = (SCRIPTS_DIR / "playtest.py").read_text()
        assert "DASHBOARD_HTML" not in source or "from playtest_dashboard" in source, (
            "DASHBOARD_HTML must not be defined in playtest.py — move to playtest_dashboard.py"
        )

    def test_render_message_not_defined_in_main(self):
        """render_message() must NOT be defined in playtest.py — it belongs in playtest_messages."""
        source = (SCRIPTS_DIR / "playtest.py").read_text()
        assert "def render_message(" not in source, (
            "render_message() must not be defined in playtest.py — move to playtest_messages.py"
        )


# ── AC-2: playtest_dashboard.py has dashboard infrastructure ────────────────


class TestPlaytestDashboard:
    """playtest_dashboard.py must contain all dashboard-related code."""

    def test_module_importable(self):
        """playtest_dashboard module must exist and be importable."""
        mod = _import_module("playtest_dashboard")
        assert mod is not None

    def test_dashboard_html_constant(self):
        """DASHBOARD_HTML constant must be in playtest_dashboard."""
        mod = _import_module("playtest_dashboard")
        assert hasattr(mod, "DASHBOARD_HTML"), (
            "playtest_dashboard.py must export DASHBOARD_HTML"
        )
        assert isinstance(mod.DASHBOARD_HTML, str)
        assert len(mod.DASHBOARD_HTML) > 1000, (
            "DASHBOARD_HTML should be the full HTML dashboard (>1000 chars)"
        )

    def test_dashboard_handler_function(self):
        """_dashboard_handler async function must be in playtest_dashboard."""
        mod = _import_module("playtest_dashboard")
        # May be exported with or without leading underscore
        handler_name = None
        for name in ("_dashboard_handler", "dashboard_handler"):
            if hasattr(mod, name):
                handler_name = name
                break
        assert handler_name is not None, (
            "playtest_dashboard.py must have a dashboard_handler function"
        )
        assert inspect.iscoroutinefunction(getattr(mod, handler_name))

    def test_broadcast_to_dashboards_function(self):
        """broadcast_to_dashboards async function must be in playtest_dashboard."""
        mod = _import_module("playtest_dashboard")
        func_name = None
        for name in ("_broadcast_to_dashboards", "broadcast_to_dashboards"):
            if hasattr(mod, name):
                func_name = name
                break
        assert func_name is not None, (
            "playtest_dashboard.py must have a broadcast_to_dashboards function"
        )
        assert inspect.iscoroutinefunction(getattr(mod, func_name))

    def test_run_dashboard_server_function(self):
        """run_dashboard_server async function must be in playtest_dashboard."""
        mod = _import_module("playtest_dashboard")
        assert hasattr(mod, "run_dashboard_server"), (
            "playtest_dashboard.py must export run_dashboard_server"
        )
        assert inspect.iscoroutinefunction(mod.run_dashboard_server)

    def test_serve_dashboard_http_function(self):
        """HTTP serving function must be in playtest_dashboard."""
        mod = _import_module("playtest_dashboard")
        func_name = None
        for name in ("_serve_dashboard_http", "serve_dashboard_http"):
            if hasattr(mod, name):
                func_name = name
                break
        assert func_name is not None, (
            "playtest_dashboard.py must have a serve_dashboard_http function"
        )


# ── AC-3: playtest_messages.py has message styles and rendering ─────────────


class TestPlaytestMessages:
    """playtest_messages.py must contain message rendering infrastructure."""

    def test_module_importable(self):
        """playtest_messages module must exist and be importable."""
        mod = _import_module("playtest_messages")
        assert mod is not None

    def test_msg_styles_dict(self):
        """MSG_STYLES must be a dict mapping message types to styles."""
        mod = _import_module("playtest_messages")
        assert hasattr(mod, "MSG_STYLES"), (
            "playtest_messages.py must export MSG_STYLES"
        )
        assert isinstance(mod.MSG_STYLES, dict)
        assert "NARRATION" in mod.MSG_STYLES, (
            "MSG_STYLES must include NARRATION"
        )
        assert "ERROR" in mod.MSG_STYLES, (
            "MSG_STYLES must include ERROR"
        )

    def test_render_message_function(self):
        """render_message() must be in playtest_messages."""
        mod = _import_module("playtest_messages")
        assert hasattr(mod, "render_message"), (
            "playtest_messages.py must export render_message"
        )
        assert callable(mod.render_message)

    def test_make_connect_msg(self):
        """make_connect_msg() must be in playtest_messages."""
        mod = _import_module("playtest_messages")
        assert hasattr(mod, "make_connect_msg"), (
            "playtest_messages.py must export make_connect_msg"
        )
        result = mod.make_connect_msg("test_genre", "test_world", "TestPlayer")
        assert isinstance(result, dict)
        assert result["type"] == "SESSION_EVENT"
        assert result["payload"]["genre"] == "test_genre"

    def test_make_action_msg(self):
        """make_action_msg() must be in playtest_messages."""
        mod = _import_module("playtest_messages")
        assert hasattr(mod, "make_action_msg"), (
            "playtest_messages.py must export make_action_msg"
        )
        result = mod.make_action_msg("look around")
        assert isinstance(result, dict)
        assert result["type"] == "PLAYER_ACTION"
        assert result["payload"]["action"] == "look around"

    def test_make_chargen_choice(self):
        """make_chargen_choice() must be in playtest_messages."""
        mod = _import_module("playtest_messages")
        assert hasattr(mod, "make_chargen_choice"), (
            "playtest_messages.py must export make_chargen_choice"
        )
        result = mod.make_chargen_choice("warrior")
        assert isinstance(result, dict)

    def test_make_chargen_confirm(self):
        """make_chargen_confirm() must be in playtest_messages."""
        mod = _import_module("playtest_messages")
        assert hasattr(mod, "make_chargen_confirm"), (
            "playtest_messages.py must export make_chargen_confirm"
        )
        result = mod.make_chargen_confirm()
        assert isinstance(result, dict)


# ── AC-4: playtest_otlp.py exists as empty skeleton ─────────────────────────


class TestPlaytestOtlp:
    """playtest_otlp.py must exist as an empty module for story 21-2."""

    def test_module_exists(self):
        """playtest_otlp.py file must exist in scripts/."""
        path = SCRIPTS_DIR / "playtest_otlp.py"
        assert path.exists(), "playtest_otlp.py must exist in scripts/"

    def test_module_importable(self):
        """playtest_otlp module must be importable."""
        mod = _import_module("playtest_otlp")
        assert mod is not None

    def test_module_is_minimal(self):
        """playtest_otlp.py should be a skeleton — under 20 lines."""
        path = SCRIPTS_DIR / "playtest_otlp.py"
        lines = path.read_text().strip().splitlines()
        assert len(lines) < 20, (
            f"playtest_otlp.py should be a minimal skeleton, got {len(lines)} lines"
        )


# ── AC-5: CLI still works ───────────────────────────────────────────────────


class TestCLIIntegration:
    """Verify that the CLI entry point still functions after the split."""

    def test_help_flag(self):
        """playtest.py --help must produce output and exit 0."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "playtest.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"--help failed: {result.stderr}"
        assert "playtest" in result.stdout.lower() or "usage" in result.stdout.lower(), (
            f"--help output doesn't look right: {result.stdout[:200]}"
        )

    def test_dashboard_only_flag_exists(self):
        """--dashboard-only flag must be recognized (even if it can't connect)."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "playtest.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "--dashboard-only" in result.stdout, (
            "--dashboard-only flag must appear in help output"
        )


# ── AC-6: No functional changes — cross-module integration ─────────────────


class TestCrossModuleIntegration:
    """Verify modules integrate correctly — no circular imports, no missing refs."""

    def test_no_circular_imports(self):
        """Importing all four modules must not raise ImportError."""
        errors = []
        for name in ("playtest_messages", "playtest_dashboard", "playtest_otlp", "playtest"):
            try:
                _import_module(name)
            except ImportError as e:
                errors.append(f"{name}: {e}")
        assert not errors, f"Import errors: {'; '.join(errors)}"

    def test_receiver_function_exists(self):
        """receiver() async function must be accessible from playtest.py."""
        mod = _import_module("playtest")
        assert hasattr(mod, "receiver"), (
            "playtest.py must have receiver function (defined or imported)"
        )
        assert inspect.iscoroutinefunction(mod.receiver)

    def test_message_functions_used_by_main(self):
        """playtest.py must import message helpers from playtest_messages."""
        source = (SCRIPTS_DIR / "playtest.py").read_text()
        # Should import from playtest_messages, not define locally
        assert "playtest_messages" in source, (
            "playtest.py must import from playtest_messages"
        )

    def test_dashboard_functions_used_by_main(self):
        """playtest.py must import dashboard functions from playtest_dashboard."""
        source = (SCRIPTS_DIR / "playtest.py").read_text()
        assert "playtest_dashboard" in source, (
            "playtest.py must import from playtest_dashboard"
        )


# ── Helpers ─────────────────────────────────────────────────────────────────


def _import_module(name: str):
    """Import a module from the scripts directory by name."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    # Clear from cache to get fresh imports
    if name in sys.modules:
        del sys.modules[name]
    return importlib.import_module(name)
