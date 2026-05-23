"""Story 61-4 — Playtest preflight cost guard.

RED-phase gate (now GREEN + Architect spec-check D applied) for the
orchestrator-side preflight of 61-4 (ACs 4, 7). The server-side runtime
alarm tests live at
``sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py``
(ACs 2, 3, 6).

**Preflight guard** (AC4, AC7): ``scripts/playtest.py`` MUST print a
projected per-run cost before any scenario action fires, refuse to
proceed past ``--max-projected-cost-usd`` (default $0.50) without
``--confirm-cost``, and bypass cleanly when ``--confirm-cost`` is
supplied.

Architect spec-check D (2026-05-23): the original RED tests asserted
worst-case-no-cache math. That math made the cap refuse the canonical
``smoke_test.yaml`` (7 actions → ~$1.01 worst-case > $0.50 default),
which would have driven operators to alias ``--confirm-cost`` and
silenced the cap. The math is now cache-aware per ADR-101 (action 1
full-rate input, actions 2+ cached-read at $0.30/MTok). Cap stays at
$0.50; the runaway-shape test below pushes per-action input to 60K to
re-validate the refuse path.

Architect spec-check E (2026-05-23): ``write_meta_sidecar`` was cut —
no producer of ``/tmp/real_req_*.json`` exists in tree and no consumer
in the epic context, so the helper was a textbook "No Stubbing"
violation. AC5 is deferred until the SDK-replay capture path lands as
its own story.

Locked design decisions (see ``sprint/context/context-story-61-4.md``):

- **D. Preflight projection math.** Cache-aware per ADR-101: action 1
  pays full-rate input ($3/MTok); actions 2..N pay cached-read input
  ($0.30/MTok). Output always full-rate. 4 iters_assumed per action.
"""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PLAYTEST_PATH = SCRIPTS_DIR / "playtest.py"


def _import_playtest():
    """Import scripts/playtest.py as ``playtest`` (mirrors
    test_playtest_fixture_flag.py and test_playtest_split.py)."""
    if "playtest" in sys.modules:
        del sys.modules["playtest"]
    spec = importlib.util.spec_from_file_location("playtest", str(PLAYTEST_PATH))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["playtest"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_scenario(tmp_path: Path, *, name: str, actions: list[str]) -> Path:
    """Write a minimal valid scenario YAML for projection tests."""
    p = tmp_path / f"{name}.yaml"
    p.write_text(
        "name: " + name + "\n"
        "genre: mutant_wasteland\n"
        "world: flickering_reach\n"
        "character:\n"
        "  strategy: auto\n"
        "actions:\n" + "".join(f"  - {a!r}\n" for a in actions)
    )
    return p


# ============================================================================
# 1. AC4 — Preflight prints projected cost AND advertises the new flags in --help
# ============================================================================


def test_help_advertises_max_projected_cost_usd_flag() -> None:
    """``playtest.py --help`` MUST advertise ``--max-projected-cost-usd``
    so the cost guard is discoverable without reading the source.

    Subprocess-driven (matches test_playtest_fixture_flag pattern) so
    transitive import failures don't mask the argparse surface check.
    """
    result = subprocess.run(
        [sys.executable, str(PLAYTEST_PATH), "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"playtest --help exited {result.returncode}; stderr:\n{result.stderr}"
    )
    assert "--max-projected-cost-usd" in result.stdout, (
        "playtest --help MUST advertise --max-projected-cost-usd so the "
        f"61-4 cost guard is discoverable. Got stdout:\n{result.stdout}"
    )
    assert "--confirm-cost" in result.stdout, (
        "playtest --help MUST advertise --confirm-cost so operators can "
        f"discover the bypass. Got stdout:\n{result.stdout}"
    )


def test_parse_args_accepts_max_projected_cost_usd_with_default_0_50() -> None:
    """``parse_args`` MUST default ``--max-projected-cost-usd`` to 0.50
    (decision D + AC4 verbatim — "~16x the per-turn target")."""
    playtest = _import_playtest()
    ns = playtest.parse_args(
        ["--scenario", "scenarios/smoke_test.yaml"]
    )
    assert hasattr(ns, "max_projected_cost_usd"), (
        "argparse Namespace MUST expose .max_projected_cost_usd after the "
        "61-4 wiring; missing attribute means the flag wasn't added."
    )
    assert ns.max_projected_cost_usd == 0.50, (
        "Default MUST be 0.50 (AC4 verbatim). Got "
        f"max_projected_cost_usd={ns.max_projected_cost_usd!r}"
    )
    assert hasattr(ns, "confirm_cost"), (
        ".confirm_cost MUST be on the Namespace as a boolean flag."
    )
    assert ns.confirm_cost is False, (
        f"Default confirm_cost MUST be False. Got {ns.confirm_cost!r}"
    )


# ============================================================================
# 2. AC4 + AC7 — Refuses to run past cap without --confirm-cost
# ============================================================================


def test_preflight_refuses_over_cap_scenario_without_confirm(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC7 (regression test for the preflight): a scenario whose
    projected cost exceeds ``--max-projected-cost-usd`` MUST halt the
    run BEFORE any action fires. The bail surface is loud (printed
    cost, printed cap, exit non-zero) — the operator sees both the
    projection and the cap they exceeded.

    50-action scenario with cache-aware projection (Architect spec-check
    D, ADR-101): action 1 = $0.156, actions 2..50 = 49 × $0.0264 ≈
    $1.29, total ~$1.45 — comfortably over $0.50 default cap. The cap
    fires for genuinely-large scenarios; not for healthy
    small-to-medium playtests (see ``test_smoke_test_projection_*``).

    Tests the preflight FUNCTION directly (not a full subprocess) so
    we don't need a running server. The function is expected at
    ``playtest.preflight_cost_check(scenario_dict, max_usd,
    confirm)`` returning a bool/raising — exact API left to Dev,
    test checks BEHAVIOR (return value falsey / SystemExit / both).
    """
    playtest = _import_playtest()

    scenario_path = _make_scenario(
        tmp_path,
        name="overcap",
        actions=[f"action {i}" for i in range(50)],
    )
    scenario = playtest.load_scenario(scenario_path)

    assert hasattr(playtest, "preflight_cost_check"), (
        "playtest MUST export preflight_cost_check(scenario, "
        "max_projected_cost_usd, confirm_cost) per 61-4 AC4. Without it "
        "the preflight surface doesn't exist."
    )

    # The function should refuse — either by returning False or by raising
    # SystemExit. Both shapes are operator-actionable; test accepts either.
    refused = False
    try:
        result = playtest.preflight_cost_check(
            scenario,
            max_projected_cost_usd=0.50,
            confirm_cost=False,
        )
        if result is False or result is None:
            refused = True
    except SystemExit:
        refused = True

    assert refused, (
        "preflight_cost_check MUST refuse (return falsey or SystemExit) "
        "when a 50-action scenario projects ~$7.20 against the $0.50 cap "
        "without --confirm-cost. Otherwise the runaway can land silently."
    )

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "$" in combined or "USD" in combined.upper() or "cost" in combined.lower(), (
        "Refusal MUST print operator-facing cost text (the May 23 incident "
        "happened because nothing was ever printed). Got stdout:\n"
        f"{captured.out}\nstderr:\n{captured.err}"
    )


def test_preflight_proceeds_when_confirm_cost_bypass_supplied(
    tmp_path: Path,
) -> None:
    """``--confirm-cost`` MUST bypass the cap. The over-cap 50-action
    scenario from the prior test should proceed (return True / no
    SystemExit) when ``confirm_cost=True`` is passed.

    Operator-actionable: the cost is still printed (for the audit trail),
    but the run proceeds. This is the explicit opt-in path AC4 reserves.
    """
    playtest = _import_playtest()

    scenario_path = _make_scenario(
        tmp_path,
        name="overcap_confirmed",
        actions=[f"action {i}" for i in range(50)],
    )
    scenario = playtest.load_scenario(scenario_path)

    # Must not raise SystemExit.
    try:
        result = playtest.preflight_cost_check(
            scenario,
            max_projected_cost_usd=0.50,
            confirm_cost=True,
        )
    except SystemExit as exc:
        pytest.fail(
            f"--confirm-cost MUST bypass the cap; got SystemExit({exc.code!r}) "
            "instead of a clean proceed signal."
        )

    # Truthy return signals "proceed". Allow True or None — the API
    # contract is "no SystemExit + no falsey-refuse"; the exact return
    # type is Dev's call.
    assert result is not False, (
        "preflight_cost_check with confirm_cost=True MUST NOT return False "
        f"(that's the refuse signal). Got {result!r}."
    )


def test_preflight_proceeds_for_under_cap_scenario_no_confirm_needed(
    tmp_path: Path,
) -> None:
    """A tiny scenario (2 actions) projects well under $0.50 — preflight
    MUST proceed without requiring --confirm-cost.

    Cache-aware projection (ADR-101): action 1 = $0.156, action 2 =
    $0.0264, total ≈ $0.18, under the $0.50 default cap.

    Regression guard against "preflight refuses everything" / "default
    cap set to 0".
    """
    playtest = _import_playtest()

    scenario_path = _make_scenario(
        tmp_path,
        name="undercap",
        actions=["a", "b"],
    )
    scenario = playtest.load_scenario(scenario_path)

    # Must not refuse on an under-cap scenario without confirm.
    try:
        result = playtest.preflight_cost_check(
            scenario,
            max_projected_cost_usd=0.50,
            confirm_cost=False,
        )
    except SystemExit as exc:
        pytest.fail(
            f"Under-cap scenario MUST proceed; got SystemExit({exc.code!r}). "
            "Cap may be set too low or projection too pessimistic — see "
            "decision D."
        )
    assert result is not False, (
        "Under-cap scenario MUST proceed (return truthy / None, not "
        f"False). Got {result!r}."
    )


# ============================================================================
# 3. Architect spec-check D — cache-aware projection vs the canonical smoke_test
# ============================================================================


def test_smoke_test_projection_stays_under_default_cap(tmp_path: Path) -> None:
    """``smoke_test.yaml`` (the canonical sanity scenario, 7 actions) MUST
    project under the $0.50 default cap.

    Architect spec-check D (2026-05-23): the original worst-case math
    projected smoke_test at ~$1.01 and refused it by default — every
    real scenario except 1-3-action fixtures was refused, which would
    drive operators to alias ``--confirm-cost=$true`` and silence the
    cap. Cache-aware math (ADR-101) preserves the cap as a real signal:
    smoke_test projects ~$0.34 (under $0.50), the 50-action runaway
    scenario still projects > $0.50 and refuses.

    Math check (cache-aware): action 1 = ~$0.156, actions 2..7 = 6 ×
    ~$0.0264 = ~$0.159, total ~$0.315 — comfortably under $0.50.
    """
    playtest = _import_playtest()

    # Reproduce the smoke_test action count without coupling the test to
    # the live scenario file (file is part of the orchestrator repo but
    # the test contract is on the projection function, not the file).
    scenario_path = _make_scenario(
        tmp_path,
        name="smoke_test_shape",
        actions=[
            "look around",
            "talk to the nearest person",
            "examine my surroundings more carefully",
            "/status",
            "/inventory",
            "pick up something interesting",
            "head somewhere new",
        ],
    )
    scenario = playtest.load_scenario(scenario_path)

    # Direct projection check — projection MUST be under cap.
    projected = playtest._project_preflight_cost_usd(len(scenario["actions"]))
    assert projected < 0.50, (
        "Architect spec-check D: smoke_test.yaml (7 actions) MUST project "
        f"under the $0.50 default cap (got ${projected:.4f}). If this "
        "test fails the cache-aware projection has regressed to "
        "worst-case math, which would refuse the canonical sanity "
        "scenario by default and drive operators to alias "
        "--confirm-cost. See sprint/context decision D."
    )

    # And the preflight MUST proceed without --confirm-cost.
    result = playtest.preflight_cost_check(
        scenario,
        max_projected_cost_usd=0.50,
        confirm_cost=False,
    )
    assert result is not False, (
        "smoke_test.yaml shape MUST proceed under the default cap "
        f"without --confirm-cost. Got {result!r}."
    )


def test_runaway_scenario_still_refuses(tmp_path: Path) -> None:
    """The cap still fires for actual-runaway-shaped scenarios.

    Architect spec-check D safety net: cache-aware math must not over-
    correct and miss a genuine runaway. Synthesize a 50-action scenario
    with per-action input bloat at 60K tokens (simulating snapshot bloat
    pre-61-2). At 60K input the per-action cost rises 5x and the
    projection MUST still exceed $0.50.

    Because per-action input is hard-coded in playtest.py (operator
    can't dial it from a flag), this test exercises the same scaling
    by lifting the constant via monkeypatch to a runaway value, then
    confirms refusal.
    """
    playtest = _import_playtest()

    scenario_path = _make_scenario(
        tmp_path,
        name="runaway_shape",
        actions=[f"action {i}" for i in range(50)],
    )
    scenario = playtest.load_scenario(scenario_path)

    # Lift the per-action input constant to 60K (5x the healthy 12K).
    # Cache-aware math at 60K input: action 1 = ~$0.732, actions 2..50
    # = 49 × ~$0.084 = ~$4.12, total ~$4.85 — well over $0.50.
    original = playtest._PREFLIGHT_INPUT_TOKENS_PER_ACTION
    try:
        playtest._PREFLIGHT_INPUT_TOKENS_PER_ACTION = 60_000
        projected = playtest._project_preflight_cost_usd(
            len(scenario["actions"])
        )
        assert projected > 0.50, (
            f"Runaway-shape scenario MUST exceed the $0.50 cap (got "
            f"${projected:.4f}). If this fails, the cache rebate is "
            "swallowing a real runaway signal — the cap is no longer "
            "operator-actionable."
        )

        # The preflight MUST refuse.
        result = playtest.preflight_cost_check(
            scenario,
            max_projected_cost_usd=0.50,
            confirm_cost=False,
        )
        assert result is False, (
            "Runaway-shape scenario MUST refuse without --confirm-cost. "
            f"Got {result!r}."
        )
    finally:
        playtest._PREFLIGHT_INPUT_TOKENS_PER_ACTION = original


# ============================================================================
# 4. Architect spec-check E — sidecar writer cut (no producer, no consumer)
# ============================================================================


def test_write_meta_sidecar_removed_per_architect_e() -> None:
    """Architect spec-check E (2026-05-23): ``write_meta_sidecar`` was a
    textbook CLAUDE.md "No Stubbing" violation — no producer of
    ``/tmp/real_req_*.json`` exists in tree, and the epic context has
    no near-term consumer. Re-implement when the SDK-replay capture
    path lands as its own story (AC5 is deferred to that work).

    This negative test exists to make the deletion intentional. If a
    future change re-adds ``write_meta_sidecar`` without a producer +
    consumer, this test fails and forces the question.
    """
    playtest = _import_playtest()

    assert not hasattr(playtest, "write_meta_sidecar"), (
        "Architect spec-check E (2026-05-23): write_meta_sidecar was cut "
        "as a stub (no producer of /tmp/real_req_*.json, no consumer). "
        "Re-introduce only alongside a real capture path (its own story)."
    )
