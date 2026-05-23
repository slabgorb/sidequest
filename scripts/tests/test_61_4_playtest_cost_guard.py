"""Story 61-4 — Playtest preflight cost guard + SDK-replay sidecar.

RED-phase gate for the orchestrator-side half of 61-4 (ACs 4, 5, 7).
The server-side runtime alarm tests live at
``sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py``
(ACs 2, 3, 6).

Two surfaces here:

1. **Preflight guard** (AC4, AC7): ``scripts/playtest.py`` MUST print
   a projected per-run cost before any scenario action fires, refuse
   to proceed past ``--max-projected-cost-usd`` (default $0.50)
   without ``--confirm-cost``, and bypass cleanly when ``--confirm-cost``
   is supplied.

2. **SDK-replay sidecar** (AC5): a ``write_meta_sidecar`` helper
   exposed from ``scripts/playtest.py`` (importable under the name
   ``playtest``) MUST take a ``/tmp/real_req_*.json`` dump path and
   write a sibling ``.meta.json`` carrying input_tokens +
   projected_cost_per_replay_usd + per-iter projection on the locked
   schema (see ``sprint/context/context-story-61-4.md`` decision E).

Locked design decisions (see ``sprint/context/context-story-61-4.md``):

- **D. Preflight projection math.** Conservative worst-case:
  ``N_actions × 12_000 input × 4 iters_assumed × Sonnet input rate
  + 200 output × 4 iters × Sonnet output rate``. No cache rebate.
- **E. Sidecar schema.** ``{request_file, input_tokens, iters_assumed,
  per_iter_projection_usd[], projected_cost_per_replay_usd, model,
  captured_at, schema_version=1}``. Sidecar assumes cache rebate
  (replays run warm against the same prefix).
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
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

    50-action scenario × 12_000 input × 4 iters × $3/Mtok ≈ $7.20
    worst-case, comfortably over $0.50 default cap.

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
    """A tiny scenario (3 actions) projects well under $0.50 — preflight
    MUST proceed without requiring --confirm-cost.

    3 × 12_000 × 4 × $3/Mtok ≈ $0.43, under the $0.50 default cap.
    Adjusted assertion: use 2 actions for a comfortable headroom
    (~$0.29) so the test isn't brittle to ±10% projection rounding
    decisions Dev might make.

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
# 3. AC5 — Sidecar .meta.json schema for /tmp/real_req_*.json dumps
# ============================================================================


def test_write_meta_sidecar_creates_sibling_with_required_fields(
    tmp_path: Path,
) -> None:
    """AC5: any ``/tmp/real_req_*.json`` dump gets a sibling
    ``.meta.json`` carrying input_tokens + projected_cost_per_replay_usd
    + per-iter projection.

    Synthesizes a request-dump fixture, calls the sidecar writer, and
    asserts the resulting file shape matches decision E.

    The dump format isn't owned by 61-4 (no producer exists today —
    `grep -rn real_req` finds only doc references). Test uses a
    minimal plausible shape with an Anthropic-style messages payload
    that the sidecar can compute input_tokens against. If Dev's
    sidecar requires a different input shape, adjust the fixture
    rather than collapse the contract.
    """
    playtest = _import_playtest()

    assert hasattr(playtest, "write_meta_sidecar"), (
        "playtest MUST export write_meta_sidecar(dump_path) -> Path per "
        "61-4 AC5. Without it the sidecar surface doesn't exist."
    )

    # Synthesize a request dump. ``input_tokens`` is the load-bearing
    # field; we provide it pre-computed so the sidecar doesn't need a
    # tokenizer dependency. (Real producer can compute it during capture.)
    dump_path = tmp_path / "real_req_001.json"
    dump_path.write_text(json.dumps({
        "model": "claude-sonnet-4-6",
        "input_tokens": 12_345,
        "messages": [{"role": "user", "content": "stub"}],
        "system": [{"type": "text", "text": "stub system"}],
    }))

    sidecar_path = playtest.write_meta_sidecar(dump_path)

    assert sidecar_path.exists(), (
        f"Sidecar MUST be written to {sidecar_path}; file does not exist."
    )
    # Path convention: sibling .meta.json (real_req_001.json →
    # real_req_001.meta.json or real_req_001.json.meta.json — either
    # acceptable as long as it sits next to the dump).
    assert sidecar_path.parent == dump_path.parent, (
        f"Sidecar MUST be a sibling of {dump_path.name}; got "
        f"{sidecar_path}."
    )
    assert sidecar_path.name.endswith(".meta.json"), (
        f"Sidecar name MUST end in .meta.json; got {sidecar_path.name!r}."
    )

    meta = json.loads(sidecar_path.read_text())

    # Required fields per decision E (locked schema).
    for key in (
        "input_tokens",
        "projected_cost_per_replay_usd",
        "per_iter_projection_usd",
        "model",
        "schema_version",
    ):
        assert key in meta, (
            f"Sidecar schema MUST include {key!r} (decision E). "
            f"Got keys={sorted(meta)}."
        )

    assert meta["input_tokens"] == 12_345, (
        "input_tokens MUST be propagated from the dump verbatim. Got "
        f"{meta['input_tokens']!r}"
    )
    assert meta["schema_version"] == 1, (
        f"schema_version MUST be 1 (initial). Got {meta['schema_version']!r}"
    )
    assert isinstance(meta["per_iter_projection_usd"], list), (
        "per_iter_projection_usd MUST be a list (one entry per assumed "
        f"replay iter). Got type={type(meta['per_iter_projection_usd']).__name__}"
    )
    assert len(meta["per_iter_projection_usd"]) >= 1, (
        "per_iter_projection_usd MUST contain at least one entry "
        "(the first/cold iter). Empty list means projection wasn't "
        "computed."
    )
    # Sanity: projected_cost_per_replay_usd ≈ sum(per_iter_projection_usd).
    iter_sum = sum(meta["per_iter_projection_usd"])
    assert abs(meta["projected_cost_per_replay_usd"] - iter_sum) < 1e-6, (
        "projected_cost_per_replay_usd MUST equal "
        "sum(per_iter_projection_usd) per decision E. Got "
        f"projected={meta['projected_cost_per_replay_usd']!r}, "
        f"sum={iter_sum!r}"
    )
    # Cold first iter > warm later iters (cache rebate assumption in
    # decision E). Guards against "all iters projected at uncached rate".
    if len(meta["per_iter_projection_usd"]) >= 2:
        assert meta["per_iter_projection_usd"][0] > meta["per_iter_projection_usd"][1], (
            "Per decision E, replay sidecar ASSUMES cache rebate after "
            "iter 1. First iter projection MUST exceed subsequent iters. "
            f"Got {meta['per_iter_projection_usd'][:2]}"
        )
