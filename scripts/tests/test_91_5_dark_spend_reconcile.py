"""Story 91-5 — Dark-spend detector: reconciliation script tests (RED).

Epic 91 ("Dark Spend") doctrine: NO UNINSTRUMENTED TOKEN. Stories 91-1
through 91-4 wired every Anthropic call through a choke-point that logs
``llm.request`` spans and feeds the ``SessionCostLedger``. Story 91-5
closes the loop: a daily reconciliation script compares what our
instrumentation logged (instrumented total) against what the Anthropic
Admin API reports as billed, and fires a loud alert when the gap exceeds
the threshold. The GM dashboard surfaces the latest result.

These tests pin the reconciliation script's contract
(``scripts/reconcile_dark_spend.py``):

**AC-1 — Gap computation and alert threshold.**
``compute_gap(instrumented_usd, billed_usd)`` returns a ``ReconcileResult``
with ``gap_pct`` and ``alert``. The alert fires when
``gap_pct > DARK_SPEND_ALERT_THRESHOLD_PCT`` (10.0).
A gap at or below 10% must not trigger an alert. This is the core
invariant — a silently-wrong threshold constant is the failure mode.

**AC-2 — Loud alert path.**
When ``alert=True``, the main function (or the reconcile runner) must:
- Log at ERROR level (not WARNING — this is a billing alarm)
- Return a non-zero exit code so cron/CI fails visibly

**AC-3 — Admin API fetch error propagates loudly.**
When the Admin API returns an HTTP error, the fetch function raises
(not sys.exit) so callers can catch, log, and surface the error clearly.
Silent swallowing violates No Silent Fallbacks.

**AC-4 — Edge case: zero spend on both sides.**
When both instrumented_usd and billed_usd are 0, gap is 0% and no alert
fires. Division-by-zero must not crash.

**AC-5 — Edge case: fully dark spend.**
When instrumented_usd=0 and billed_usd>0, gap is 100% and alert fires.
This is the worst case the epic was written to catch.

**AC-6 — DARK_SPEND_ALERT_THRESHOLD_PCT constant is exactly 10.0.**
Pinning the constant prevents drift — if someone halves the threshold in
a hot-fix and creates false-positive alert storms, this test catches it.
If the threshold needs changing, it must come through review.

**AC-7 — No-admin-key path fails loudly at fetch time.**
Missing ANTHROPIC_ADMIN_KEY raises a clear error before any network call.
The error message must name the env variable so the operator knows how
to fix it.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Script import helper (mirrors test_61_4_playtest_cost_guard.py pattern)
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
RECONCILE_PATH = SCRIPTS_DIR / "reconcile_dark_spend.py"


def _import_reconcile() -> Any:
    """Import scripts/reconcile_dark_spend.py as a module."""
    if "reconcile_dark_spend" in sys.modules:
        del sys.modules["reconcile_dark_spend"]
    spec = importlib.util.spec_from_file_location("reconcile_dark_spend", str(RECONCILE_PATH))
    assert spec is not None and spec.loader is not None, (
        f"Cannot import {RECONCILE_PATH} — file missing or unparseable. "
        "Dev must create scripts/reconcile_dark_spend.py."
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["reconcile_dark_spend"] = mod
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# AC-6 — Threshold constant is exactly 10.0 (pinned, must go through review)
# ===========================================================================


def test_dark_spend_alert_threshold_is_10_pct() -> None:
    """The alert threshold constant must be exactly 10.0 (percent).

    Pinning this prevents a hot-fix from silently halving the threshold,
    which would create alert storms on healthy servers. Any intentional
    change must come through a code review that updates this test.
    """
    mod = _import_reconcile()
    assert hasattr(mod, "DARK_SPEND_ALERT_THRESHOLD_PCT"), (
        "reconcile_dark_spend.py must export DARK_SPEND_ALERT_THRESHOLD_PCT "
        "as a module-level constant so the GM panel and ops docs can cite it"
    )
    assert mod.DARK_SPEND_ALERT_THRESHOLD_PCT == 10.0, (
        f"threshold is {mod.DARK_SPEND_ALERT_THRESHOLD_PCT}, expected 10.0 — "
        "if you intentionally changed this, update the test too"
    )


# ===========================================================================
# AC-1 — Gap computation and alert threshold
# ===========================================================================


def test_compute_gap_below_threshold_no_alert() -> None:
    """A 5% gap (well below the 10% threshold) must not trigger an alert."""
    mod = _import_reconcile()
    result = mod.compute_gap(instrumented_usd=0.95, billed_usd=1.00)
    assert result.gap_pct == pytest.approx(5.0, abs=0.01), (
        f"gap_pct should be ~5.0 for instrumented=0.95 billed=1.00, got {result.gap_pct}"
    )
    assert result.alert is False, (
        "a 5% gap is below the 10% threshold and must NOT trigger an alert"
    )


def test_compute_gap_above_threshold_fires_alert() -> None:
    """A 15% gap (above the 10% threshold) must trigger an alert."""
    mod = _import_reconcile()
    result = mod.compute_gap(instrumented_usd=0.85, billed_usd=1.00)
    assert result.gap_pct == pytest.approx(15.0, abs=0.01), (
        f"gap_pct should be ~15.0 for instrumented=0.85 billed=1.00, got {result.gap_pct}"
    )
    assert result.alert is True, (
        "a 15% gap exceeds the 10% threshold and MUST trigger an alert"
    )


def test_compute_gap_result_carries_raw_figures() -> None:
    """ReconcileResult must echo back instrumented_usd and billed_usd
    so the GM dashboard can display exact figures, not just the pct."""
    mod = _import_reconcile()
    result = mod.compute_gap(instrumented_usd=0.80, billed_usd=1.00)
    assert result.instrumented_usd == pytest.approx(0.80), (
        f"result.instrumented_usd should echo back 0.80, got {result.instrumented_usd}"
    )
    assert result.billed_usd == pytest.approx(1.00), (
        f"result.billed_usd should echo back 1.00, got {result.billed_usd}"
    )


# ===========================================================================
# AC-4 — Edge case: zero spend on both sides (no division by zero)
# ===========================================================================


def test_compute_gap_zero_both_sides_no_alert_no_crash() -> None:
    """Both instrumented and billed at zero must compute 0% gap without
    crashing (division-by-zero guard is required)."""
    mod = _import_reconcile()
    result = mod.compute_gap(instrumented_usd=0.0, billed_usd=0.0)
    assert result.alert is False, (
        "zero instrumented / zero billed = 0% dark spend, no alert should fire"
    )
    assert result.gap_pct == pytest.approx(0.0, abs=0.01), (
        f"zero-zero gap should be 0.0%, got {result.gap_pct}"
    )


def test_compute_gap_small_positive_billed_no_crash() -> None:
    """Very small but non-zero billed amounts must not cause float
    instability or false positives."""
    mod = _import_reconcile()
    result = mod.compute_gap(instrumented_usd=0.0001, billed_usd=0.0001)
    assert result.alert is False, (
        "matching tiny amounts should not trigger an alert"
    )


# ===========================================================================
# AC-5 — Fully dark spend (instrumented=0, billed>0)
# ===========================================================================


def test_compute_gap_fully_dark_fires_alert() -> None:
    """100% dark spend (instrumented=0, real spend=$3.50/day from the
    2026-06-05 incident) must fire an alert with gap_pct=100%."""
    mod = _import_reconcile()
    result = mod.compute_gap(instrumented_usd=0.0, billed_usd=3.50)
    assert result.gap_pct == pytest.approx(100.0, abs=0.01), (
        f"zero instrumented against billed=3.50 should be 100% gap, got {result.gap_pct}"
    )
    assert result.alert is True, (
        "100% dark spend must fire the alert — this is the exact failure "
        "mode epic 91 was written to catch (the Jun 3 Haiku blind spot)"
    )


def test_compute_gap_partial_dark_above_threshold_fires_alert() -> None:
    """Even partial instrumentation gap above 10% triggers alert —
    not just the fully-dark case."""
    mod = _import_reconcile()
    # instrumented=0.3 of 1.0 billed → 70% gap
    result = mod.compute_gap(instrumented_usd=0.30, billed_usd=1.00)
    assert result.alert is True, (
        "70% gap (far above 10% threshold) must fire the alert"
    )
    assert result.gap_pct == pytest.approx(70.0, abs=0.01)


# ===========================================================================
# AC-2 — Loud alert path: ERROR-level log + non-zero exit
# ===========================================================================


def test_run_reconcile_alert_logs_at_error_level(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """When the reconciliation fires an alert, the log must be at ERROR
    level — not WARNING or INFO. This is a billing alarm, not a health
    notice. (Python rule #4: error paths use logger.error().)"""
    mod = _import_reconcile()
    caplog.set_level(logging.ERROR)
    # Inject pre-computed result with alert=True instead of driving Admin API
    result = mod.compute_gap(instrumented_usd=0.0, billed_usd=3.50)
    assert result.alert is True  # paranoia sanity check

    # The module must expose a `emit_alert(result)` or `run_reconcile` that
    # logs an error when alert is True.
    assert hasattr(mod, "emit_alert") or hasattr(mod, "run_reconcile"), (
        "reconcile_dark_spend.py must expose emit_alert(result) or "
        "run_reconcile(result) so callers (cron, main) can trigger the loud path"
    )
    if hasattr(mod, "emit_alert"):
        mod.emit_alert(result)
    else:
        mod.run_reconcile(result)

    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records, (
        "alert path must log at ERROR level — a billing alarm that logs at "
        "WARNING can be silently suppressed by log-level config"
    )
    # The error message must name the gap so an operator can act
    assert any("gap" in r.getMessage().lower() or "dark" in r.getMessage().lower()
               for r in error_records), (
        "the ERROR log must mention the gap or dark spend so an operator "
        "knows immediately why it fired"
    )


def test_main_exits_nonzero_on_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() must return (or raise SystemExit with) a non-zero code when
    the alert fires — so cron jobs and CI pipelines see a visible failure
    and can page on it."""
    mod = _import_reconcile()
    monkeypatch.setattr(sys, "argv", ["reconcile_dark_spend.py"])
    # Patch fetch functions to return a dark-spend scenario (100% dark)
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "sk-ant-admin-test")
    with (
        patch.object(mod, "fetch_billed_usd", return_value=3.50),
        patch.object(mod, "fetch_instrumented_usd", return_value=0.0),
    ):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code != 0, (
            "main() must sys.exit with a non-zero code when dark spend is "
            "detected — a zero exit on an alert means cron sees success and "
            "the operator is never paged"
        )


def test_main_exits_zero_on_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() must exit 0 when the gap is within tolerance — no false alarms."""
    mod = _import_reconcile()
    monkeypatch.setattr(sys, "argv", ["reconcile_dark_spend.py"])
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "sk-ant-admin-test")
    with (
        patch.object(mod, "fetch_billed_usd", return_value=1.00),
        patch.object(mod, "fetch_instrumented_usd", return_value=0.96),  # 4% gap, under threshold
    ):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 0, (
            "main() must exit 0 when the reconciliation passes — non-zero on "
            "clean would cause unnecessary oncall pages"
        )


# ===========================================================================
# AC-3 — Admin API fetch error propagates loudly (not swallowed)
# ===========================================================================


def test_fetch_billed_usd_http_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """An Admin API 401/403/500 must raise an exception, not call sys.exit
    or return 0.0 silently. Swallowing the error makes a broken Admin key
    look like zero billed — which suppresses the very alert this story builds.
    (Python rule #1: explicit exception handling at API boundaries.)"""
    mod = _import_reconcile()
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "sk-ant-admin-test")

    fake_error = urllib.error.HTTPError(
        url="https://api.anthropic.com/v1/organizations/cost_report",
        code=401,
        msg="Unauthorized",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(b'{"error": "invalid_api_key"}'),
    )

    with patch("urllib.request.urlopen", side_effect=fake_error):
        with pytest.raises(Exception) as exc_info:  # any non-SystemExit exception
            mod.fetch_billed_usd("sk-ant-admin-test", days=1)
        assert not isinstance(exc_info.value, SystemExit), (
            "fetch_billed_usd must raise, not sys.exit — callers need the "
            "exception to distinguish 'API error' from 'alert condition'"
        )


def test_fetch_billed_usd_network_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network failures must also raise, not return 0.0."""
    mod = _import_reconcile()
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "sk-ant-admin-test")
    network_error = urllib.error.URLError("Connection refused")

    with patch("urllib.request.urlopen", side_effect=network_error):
        with pytest.raises(Exception) as exc_info:
            mod.fetch_billed_usd("sk-ant-admin-test", days=1)
        assert not isinstance(exc_info.value, SystemExit)


# ===========================================================================
# AC-7 — No-admin-key path fails loudly at fetch time
# ===========================================================================


def test_fetch_billed_usd_no_admin_key_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing ANTHROPIC_ADMIN_KEY must fail loudly BEFORE making a network
    call — the failure message must name the env variable so the operator
    knows immediately how to fix it. (No Silent Fallbacks doctrine.)"""
    mod = _import_reconcile()
    monkeypatch.delenv("ANTHROPIC_ADMIN_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # both absent

    with pytest.raises(Exception, match="ANTHROPIC_ADMIN_KEY"):
        mod.fetch_billed_usd(admin_key=None, days=1)  # type: ignore[arg-type]


def test_main_no_admin_key_fails_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() without an admin key must fail loudly — not produce a fake
    0.0 billed total that suppresses the alert."""
    mod = _import_reconcile()
    monkeypatch.delenv("ANTHROPIC_ADMIN_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises((SystemExit, Exception)) as exc_info:
        mod.main()
    if isinstance(exc_info.value, SystemExit):
        assert exc_info.value.code != 0, (
            "main() without admin key must exit non-zero — a zero exit "
            "would look like a clean reconciliation"
        )


# ===========================================================================
# Rule coverage: type annotations on public API (Python rule #3)
# ===========================================================================


def test_compute_gap_has_type_annotations() -> None:
    """compute_gap() is a public boundary function and must have annotated
    parameters and return type (Python review checklist rule #3)."""
    import inspect
    mod = _import_reconcile()
    sig = inspect.signature(mod.compute_gap)
    hints = {
        k: v
        for k, v in (getattr(mod.compute_gap, "__annotations__", None) or {}).items()
    }
    assert "instrumented_usd" in hints or sig.parameters["instrumented_usd"].annotation != inspect.Parameter.empty, (
        "compute_gap() must have type annotation on instrumented_usd"
    )
    assert "billed_usd" in hints or sig.parameters["billed_usd"].annotation != inspect.Parameter.empty, (
        "compute_gap() must have type annotation on billed_usd"
    )
    assert "return" in hints or sig.return_annotation != inspect.Parameter.empty, (
        "compute_gap() must have return type annotation"
    )
