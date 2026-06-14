# WWN Dying Window + Solo-Actuator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Under a WWN binding, a solo PC dropped to 0 HP with no live hostile enters a real WWN dying window (mortally-wounded → d6-round stabilize → dead) that the downed player drives by hand, instead of going terminal-dead only.

**Architecture:** Sequential single-status state machine on existing infrastructure (the Mortal Injury status + `stabilize_mortal_injury` tool + #846 `created_turn` provenance). One input-gate carve lets the downed soloist keep submitting free-text actions; the player's own submissions tick an engine-owned clock; expiry converts the window to terminal. Three new OTEL spans make the clock GM-panel-auditable. No native-engine mechanic is touched (ADR-143).

**Tech Stack:** Python 3 / FastAPI, pydantic v2, pytest (`-n auto` via uv), OpenTelemetry spans (`sidequest/telemetry/spans/`).

**Spec:** `docs/superpowers/specs/2026-06-14-wwn-dying-window-solo-actuator-design.md`

**Repo:** `sidequest-server` (branch strategy: gitflow, base `develop`, feature branch `feat/wwn-dying-window-solo-actuator`). All paths below are relative to `sidequest-server/`. All commands run from `sidequest-server/`.

---

## File Structure

| File | Responsibility | Task |
|------|----------------|------|
| `sidequest/game/status.py` | Add `stabilizable` structured flag to `Status`. | 1 |
| `sidequest/telemetry/spans/wn.py` | `dying_window.{opened,tick,resolved}` emitters + routes; fold #846 `superseded_by_terminal` into the mortal-injury extract. | 2 |
| `sidequest/game/ruleset/without_number.py` | Window status carries `incapacitating=True` + `stabilizable=True`; `is_dying_window_status` helper. | 3 |
| `sidequest/server/dispatch/downed_seam.py` | Branch on live-hostile (terminal) vs no-live-hostile (window); emit `dying_window.opened`. | 4 |
| `sidequest/handlers/player_action.py` | Gate carve: terminal blocks; stabilizable permits + routes to narrator. | 5 |
| `sidequest/agents/tools/stabilize_mortal_injury.py` | Derive `rounds_elapsed` from provenance; fail-loud cross-check; set HP to 1 on success. | 6 |
| `sidequest/server/post_resolution_lethality.py` | Per-turn expiry check; emit `dying_window.tick` / `dying_window.resolved`. | 7 |
| `tests/server/test_wwn_dying_window_wiring.py` | End-to-end solo wiring test (the mandatory one). | 8 |

---

## Task 1: `Status.stabilizable` structured flag

The input gate must distinguish a terminal-dead status from a stabilizable dying window **without scraping status text** (CLAUDE.md: structured markers, not text scraping — same rationale as the existing `incapacitating` field).

**Files:**
- Modify: `sidequest/game/status.py` (the `Status` model, ~line 45–84)
- Test: `tests/game/test_status_stabilizable.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_status_stabilizable.py
"""Status.stabilizable — the structured flag the dying-window input gate reads."""

from sidequest.game.status import Status, StatusSeverity


def test_status_stabilizable_defaults_false():
    s = Status(text="Bruised", severity=StatusSeverity.Scratch)
    assert s.stabilizable is False


def test_status_stabilizable_roundtrips():
    s = Status(
        text="Mortal Injury — dies in 6 rounds unless stabilized",
        severity=StatusSeverity.Scar,
        incapacitating=True,
        stabilizable=True,
    )
    assert s.stabilizable is True
    # Survives serialization (saved/loaded through the pydantic store).
    assert Status.model_validate(s.model_dump()).stabilizable is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_status_stabilizable.py -v`
Expected: FAIL — `TypeError`/`ValidationError`, `stabilizable` is not a field.

- [ ] **Step 3: Add the field**

In `sidequest/game/status.py`, add the field next to `incapacitating` (after line 59), mirroring its docstring rationale:

```python
    incapacitating: bool = False
    stabilizable: bool = False
    """True only for the WWN dying-window Mortal Injury status. The turn-intake
    gate (handlers/player_action.py) reads this to PERMIT a downed soloist's
    free-text submission (and route it to the narrator) instead of blocking, the
    way a terminal-dead incapacitating status does. Structured marker, not text
    scraping (cf. ``incapacitating``)."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_status_stabilizable.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/status.py tests/game/test_status_stabilizable.py
git commit -m "feat(wwn): add Status.stabilizable structured flag for the dying-window gate"
```

---

## Task 2: Dying-window OTEL spans + fold the #846 dark span

Define the three lie-detector spans first (TDD: the emitters exist before any production code emits them) and fix the known-dark `superseded_by_terminal` attribute on the existing mortal-injury extract.

**Files:**
- Modify: `sidequest/telemetry/spans/wn.py`
- Test: `tests/telemetry/test_wn_dying_window_spans.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/telemetry/test_wn_dying_window_spans.py
"""dying_window.{opened,tick,resolved} emit slug-namespaced WN spans, and the
mortal-injury extract surfaces superseded_by_terminal (the #846 dark-span fold)."""

from sidequest.telemetry.spans.wn import (
    SPAN_ROUTES,
    dying_window_opened_span,
    dying_window_resolved_span,
    dying_window_tick_span,
)
from sidequest.telemetry.test_helpers import capture_spans  # in-repo span capture fixture


def test_dying_window_routes_registered_for_lethality_slugs():
    for slug in ("wwn", "cwn", "awn"):
        for event in ("dying_window.opened", "dying_window.tick", "dying_window.resolved"):
            assert f"{slug}.{event}" in SPAN_ROUTES


def test_opened_carries_reason_and_deadline():
    with capture_spans() as spans:
        dying_window_opened_span(
            ruleset="wwn", actor="Rux", created_turn=4,
            mortal_injury_rounds=6, deadline_round=10, reason="no_live_hostile",
        )
    span = spans.named("wwn.dying_window.opened")
    assert span.attributes["actor"] == "Rux"
    assert span.attributes["deadline_round"] == 10
    assert span.attributes["reason"] == "no_live_hostile"


def test_tick_carries_derived_rounds_and_stabilization_flag():
    with capture_spans() as spans:
        dying_window_tick_span(
            ruleset="wwn", actor="Rux", rounds_elapsed=2, difficulty=10,
            action_was_stabilization=True, roll=14, success=True,
        )
    span = spans.named("wwn.dying_window.tick")
    assert span.attributes["rounds_elapsed"] == 2
    assert span.attributes["difficulty"] == 10
    assert span.attributes["action_was_stabilization"] is True


def test_resolved_carries_outcome():
    with capture_spans() as spans:
        dying_window_resolved_span(
            ruleset="wwn", actor="Rux", outcome="died", final_rounds_elapsed=6,
            resulting_status="terminal-dead",
        )
    assert spans.named("wwn.dying_window.resolved").attributes["outcome"] == "died"


def test_mortal_injury_extract_surfaces_superseded():
    from sidequest.telemetry.spans.wn import SPAN_ROUTES

    route = SPAN_ROUTES["wwn.mortal_injury.declared"]

    class _Span:
        attributes = {"actor": "Rux", "rounds_to_die": 6, "superseded_by_terminal": True}

    assert route.extract(_Span())["superseded_by_terminal"] is True
```

> If `tests/telemetry/test_helpers.py::capture_spans` does not exist, use the same span-capture mechanism the existing `tests/telemetry/` lethality-span tests use (grep `tests/telemetry/` for how `mortal_injury_declared_span` is asserted) — do **not** invent a new capture harness.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_wn_dying_window_spans.py -v`
Expected: FAIL — `ImportError` for the three new emitters; the extract test fails (`superseded_by_terminal` absent).

- [ ] **Step 3: Fold the #846 dark span**

In `sidequest/telemetry/spans/wn.py`, extend `_mortal_injury_declared_extract` (~line 109) to surface the attribute the emitter already forwards via `**attrs`:

```python
def _mortal_injury_declared_extract(span: _SpanLike) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "mortal_injury",
        "actor": attrs.get("actor", ""),
        "rounds_to_die": attrs.get("rounds_to_die", 0),
        # #846: the supersede decision (terminal-dead overrode the stabilizable
        # window) must be visible to the GM panel, not dropped from the projection.
        "superseded_by_terminal": attrs.get("superseded_by_terminal", False),
    }
```

- [ ] **Step 4: Add the dying-window extracts, routes, and emitters**

In `sidequest/telemetry/spans/wn.py`, add three extracts to the `_WN_LETHALITY_EXTRACTS` dict (~line 131) so they route for `wwn`/`cwn`/`awn` via the existing `WN_LETHALITY_SLUGS` loop:

```python
def _dying_window_opened_extract(span: _SpanLike) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "dying_window_opened",
        "actor": attrs.get("actor", ""),
        "created_turn": attrs.get("created_turn", 0),
        "mortal_injury_rounds": attrs.get("mortal_injury_rounds", 0),
        "deadline_round": attrs.get("deadline_round", 0),
        "reason": attrs.get("reason", ""),
    }


def _dying_window_tick_extract(span: _SpanLike) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "dying_window_tick",
        "actor": attrs.get("actor", ""),
        "rounds_elapsed": attrs.get("rounds_elapsed", 0),
        "difficulty": attrs.get("difficulty", 0),
        "action_was_stabilization": attrs.get("action_was_stabilization", False),
        "roll": attrs.get("roll", 0),
        "success": attrs.get("success", False),
    }


def _dying_window_resolved_extract(span: _SpanLike) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "dying_window_resolved",
        "actor": attrs.get("actor", ""),
        "outcome": attrs.get("outcome", ""),
        "final_rounds_elapsed": attrs.get("final_rounds_elapsed", 0),
        "resulting_status": attrs.get("resulting_status", ""),
    }
```

Add them to the existing `_WN_LETHALITY_EXTRACTS` dict (so the existing loop registers `{slug}.dying_window.*` routes — do not write a new loop):

```python
_WN_LETHALITY_EXTRACTS = {
    "system_strain.delta": _system_strain_delta_extract,
    "trauma.roll": _trauma_roll_extract,
    "shock.applied": _shock_applied_extract,
    "mortal_injury.declared": _mortal_injury_declared_extract,
    "major_injury.roll": _major_injury_roll_extract,
    "dying_window.opened": _dying_window_opened_extract,
    "dying_window.tick": _dying_window_tick_extract,
    "dying_window.resolved": _dying_window_resolved_extract,
}
```

Then add the three emitters near `mortal_injury_declared_span` (~line 234), mirroring its shape:

```python
def dying_window_opened_span(
    *,
    ruleset: str,
    actor: str,
    created_turn: int,
    mortal_injury_rounds: int,
    deadline_round: int,
    reason: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit ``{ruleset}.dying_window.opened`` — the WWN dying window opened (vs terminal)."""
    attributes: dict[str, Any] = {
        "field": "dying_window_opened",
        "actor": actor,
        "created_turn": created_turn,
        "mortal_injury_rounds": mortal_injury_rounds,
        "deadline_round": deadline_round,
        "reason": reason,
        **attrs,
    }
    with Span.open(f"{ruleset}.dying_window.opened", attributes, tracer_override=_tracer):
        pass


def dying_window_tick_span(
    *,
    ruleset: str,
    actor: str,
    rounds_elapsed: int,
    difficulty: int,
    action_was_stabilization: bool,
    roll: int = 0,
    success: bool = False,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit ``{ruleset}.dying_window.tick`` — one dying-window turn (engine-owned clock)."""
    attributes: dict[str, Any] = {
        "field": "dying_window_tick",
        "actor": actor,
        "rounds_elapsed": rounds_elapsed,
        "difficulty": difficulty,
        "action_was_stabilization": action_was_stabilization,
        "roll": roll,
        "success": success,
        **attrs,
    }
    with Span.open(f"{ruleset}.dying_window.tick", attributes, tracer_override=_tracer):
        pass


def dying_window_resolved_span(
    *,
    ruleset: str,
    actor: str,
    outcome: str,
    final_rounds_elapsed: int,
    resulting_status: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit ``{ruleset}.dying_window.resolved`` — window exit (stabilized | died)."""
    attributes: dict[str, Any] = {
        "field": "dying_window_resolved",
        "actor": actor,
        "outcome": outcome,
        "final_rounds_elapsed": final_rounds_elapsed,
        "resulting_status": resulting_status,
        **attrs,
    }
    with Span.open(f"{ruleset}.dying_window.resolved", attributes, tracer_override=_tracer):
        pass
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/telemetry/test_wn_dying_window_spans.py -v`
Expected: PASS (all five).

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans/wn.py tests/telemetry/test_wn_dying_window_spans.py
git commit -m "feat(wwn): dying_window OTEL spans + fold #846 superseded_by_terminal into mortal-injury extract"
```

---

## Task 3: Window status carries `incapacitating` + `stabilizable`

Today `resolve_downed` mints the Mortal Injury window status **non-incapacitating** and **only when not superseded**. The window must become incapacitating-for-normal-play AND stabilizable so the gate can tell it from terminal. Add a reusable predicate so the gate and expiry path don't re-scrape text.

**Files:**
- Modify: `sidequest/game/ruleset/without_number.py` (`resolve_downed`, ~line 498–512; add module-level helper)
- Test: `tests/game/ruleset/test_wwn_dying_window_status.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/game/ruleset/test_wwn_dying_window_status.py
"""resolve_downed mints a dying-window status that is incapacitating + stabilizable."""

import random

from sidequest.game.ruleset.without_number import (
    WithoutNumberRulesetModule,
    is_dying_window_status,
)
from sidequest.game.ruleset.registry import get_ruleset_module
from tests.fixtures.wwn import make_wwn_cfg, make_downed_pc_core  # see note below


def test_window_status_is_incapacitating_and_stabilizable():
    module = get_ruleset_module("wwn")
    assert isinstance(module, WithoutNumberRulesetModule)
    cfg = make_wwn_cfg()
    core = make_downed_pc_core(name="Rux")  # hp.current == 0, no statuses
    module.resolve_downed(
        core=core, save_target=10, scene_traumatic=False, cfg=cfg,
        rng=random.Random(1), created_turn=3, created_in_encounter="combat",
        superseded_by_terminal=False,
    )
    window = next(s for s in core.statuses if is_dying_window_status(s))
    assert window.incapacitating is True
    assert window.stabilizable is True
    assert window.created_turn == 3


def test_superseded_mints_no_window():
    module = get_ruleset_module("wwn")
    cfg = make_wwn_cfg()
    core = make_downed_pc_core(name="Rux")
    module.resolve_downed(
        core=core, save_target=10, scene_traumatic=False, cfg=cfg,
        rng=random.Random(1), created_turn=3, created_in_encounter="combat",
        superseded_by_terminal=True,
    )
    assert not any(is_dying_window_status(s) for s in core.statuses)
```

> **Fixture note:** if `tests/fixtures/wwn.py` helpers don't exist, build the cfg/core inline the way the nearest existing `resolve_downed` test does — grep `tests/` for `resolve_downed(` and reuse that construction. Do not stub a new ruleset config.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_wwn_dying_window_status.py -v`
Expected: FAIL — `ImportError` for `is_dying_window_status`; window status lacks `stabilizable`/`incapacitating`.

- [ ] **Step 3: Add the predicate + flags**

In `sidequest/game/ruleset/without_number.py`, add a module-level helper (near the top, after imports) keyed on the structured flag, not text:

```python
def is_dying_window_status(status) -> bool:
    """True for the WWN dying-window Mortal Injury status (stabilizable + incapacitating).

    Structured marker (``stabilizable``), never a text scrape — the one place the
    gate and the expiry pass agree on "is this the live dying window?".
    """
    return bool(getattr(status, "stabilizable", False))
```

Then in `resolve_downed`, set both flags on the minted window status (~line 501):

```python
        if not superseded_by_terminal:
            core.statuses.append(
                Status(
                    text=f"Mortal Injury — dies in {rounds} rounds unless stabilized",
                    severity=StatusSeverity.Scar,
                    created_turn=created_turn,
                    created_in_encounter=created_in_encounter,
                    incapacitating=True,
                    stabilizable=True,
                )
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_wwn_dying_window_status.py -v`
Expected: PASS (both).

- [ ] **Step 5: Guard the existing suite (the window is now incapacitating — a behavior change)**

Run: `uv run pytest tests/game/ruleset -v`
Expected: PASS. If a prior test asserted the window status was non-incapacitating, update it to the new truth (the window is now incapacitating-for-normal-play) and note it as an intentional change in the commit body.

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/ruleset/without_number.py tests/game/ruleset/test_wwn_dying_window_status.py
git commit -m "feat(wwn): dying-window status is incapacitating+stabilizable; add is_dying_window_status predicate"
```

---

## Task 4: Branch on live-hostile in the downed seam (window vs terminal)

The down event chooses: **live hostile → terminal** (today's behavior, supersede the window); **no live hostile → open the window**. Emit `dying_window.opened` on the window branch.

**Files:**
- Modify: `sidequest/server/dispatch/downed_seam.py` (`run_cwn_wwn_downed_seam`, ~line 159–178; add a helper)
- Test: `tests/server/dispatch/test_downed_seam_live_hostile_branch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/server/dispatch/test_downed_seam_live_hostile_branch.py
"""The downed seam opens the dying window only when no live hostile remains."""

import random

from sidequest.game.ruleset.without_number import is_dying_window_status
from sidequest.server.dispatch.downed_seam import run_cwn_wwn_downed_seam
from tests.fixtures.wwn import make_wwn_pack, make_solo_encounter  # reuse existing fixtures


def _run(*, hostile_alive: bool):
    pack = make_wwn_pack()
    # PC "Rux" on the player side at 0 HP; one opponent "Brute" on actor_side.
    snapshot, encounter, cdef = make_solo_encounter(
        pc="Rux", pc_hp=0, opponent="Brute", opponent_hp=(3 if hostile_alive else 0),
    )
    run_cwn_wwn_downed_seam(
        ruleset=pack.rules.ruleset_module(),
        snapshot=snapshot, encounter=encounter, cdef=cdef, pack=pack,
        actor_side="opponent", rng=random.Random(1),
    )
    core = snapshot.find_creature_core("Rux")
    return core


def test_no_live_hostile_opens_window():
    core = _run(hostile_alive=False)
    assert any(is_dying_window_status(s) for s in core.statuses)


def test_live_hostile_goes_terminal_no_window():
    # A live hostile means terminal-dead path; the stabilizable window must NOT open
    # (regression guard for the #846 single-status coherence).
    core = _run(hostile_alive=True)
    assert not any(is_dying_window_status(s) for s in core.statuses)
```

> Reuse whatever solo/encounter fixture the existing `tests/server/dispatch/` downed-seam tests use; if none seats an opponent at chosen HP, extend that fixture rather than stubbing a new encounter.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/dispatch/test_downed_seam_live_hostile_branch.py -v`
Expected: FAIL — with no live hostile, today's seam still supersedes only on an already-present incapacitating status, so no window opens for the env/solo down.

- [ ] **Step 3: Add the live-hostile predicate + branch**

In `sidequest/server/dispatch/downed_seam.py`, add a helper above `run_cwn_wwn_downed_seam`:

```python
def _has_live_hostile_on_side(snapshot, encounter, *, hostile_side: str) -> bool:
    """True if any non-withdrawn actor on ``hostile_side`` still has HP > 0.

    ``actor_side`` IS the hostile side relative to the downed PC (the PC is the
    first live actor on the OPPOSITE side, per ``_opposite_side_first_actor``).
    A live hostile means the PC gets no last stand — terminal, as today. Field
    cleared (no live hostile) is the scoped solo case — open the dying window.
    """
    for a in encounter.actors:
        if a.side == hostile_side and not a.withdrawn:
            hostile_core = snapshot.find_creature_core(a.name)
            if hostile_core is not None and hostile_core.hp.current > 0:
                return True
    return False
```

Then replace the supersede decision (~line 168) so it folds in the live-hostile branch and emits `opened` on the window path:

```python
    # sq-playtest #239 (death dual-status): if the genre lethality policy has
    # ALREADY ruled this actor terminally dead, an incapacitating terminal status
    # is present — supersede the window (one coherent status). 108-6: under a WN
    # binding we ALSO go terminal when a live hostile can still act on the PC (no
    # last stand at sword-point). The stabilizable window opens ONLY for an
    # ordinary down with the field cleared — the scoped solo case.
    already_terminal = any(getattr(s, "incapacitating", False) for s in down_core.statuses)
    live_hostile = _has_live_hostile_on_side(snapshot, encounter, hostile_side=actor_side)
    superseded = already_terminal or live_hostile
    ruleset.resolve_downed(
        core=down_core,
        save_target=save_target,
        scene_traumatic=scene_traumatic,
        cfg=cfg,
        rng=rng,
        created_turn=snapshot.turn_manager.interaction,
        created_in_encounter=encounter.encounter_type,
        superseded_by_terminal=superseded,
    )
    if not superseded:
        from sidequest.telemetry.spans.wn import dying_window_opened_span

        created_turn = snapshot.turn_manager.interaction
        dying_window_opened_span(
            ruleset=ruleset.slug,
            actor=down_name,
            created_turn=created_turn,
            mortal_injury_rounds=cfg.trauma.mortal_injury_rounds,
            deadline_round=created_turn + cfg.trauma.mortal_injury_rounds,
            reason="no_live_hostile",
        )
```

> **Doctrine check (ADR-143):** this is a *seating/branch* decision keyed on whether a hostile is alive — not a native beat/dial tune. No native mechanic is converted or gated.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/dispatch/test_downed_seam_live_hostile_branch.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/dispatch/downed_seam.py tests/server/dispatch/test_downed_seam_live_hostile_branch.py
git commit -m "feat(wwn): downed seam opens dying window only when no live hostile; emit dying_window.opened"
```

---

## Task 5: Input-gate carve — terminal blocks, stabilizable permits

The turn-intake gate at `player_action.py:534–589` blocks any incapacitating status. Carve it: a stabilizable window permits the submission and falls through to narrator dispatch; terminal still blocks.

**Files:**
- Modify: `sidequest/handlers/player_action.py` (~line 547–589)
- Test: `tests/handlers/test_player_action_dying_window_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/handlers/test_player_action_dying_window_gate.py
"""The turn-intake gate permits a stabilizable dying-window submission, blocks terminal."""

import pytest

from sidequest.game.status import Status, StatusSeverity
from sidequest.protocol.enums import MessageType
from tests.fixtures.session import make_player_action_session  # reuse existing harness


def _statuses_on(session, name, status):
    core = next(c.core for c in session._session_data.snapshot.characters if c.core.name == name)
    core.statuses.append(status)


@pytest.mark.asyncio
async def test_terminal_status_blocks_submission(monkeypatch):
    session, handler, action_msg = make_player_action_session(actor="Rux")
    _statuses_on(session, "Rux", Status(
        text="Slain", severity=StatusSeverity.Scar, incapacitating=True, stabilizable=False,
    ))
    out = await handler(action_msg, session)
    assert any(m.type == MessageType.CHARACTER_INCAPACITATED for m in out)


@pytest.mark.asyncio
async def test_stabilizable_window_permits_and_routes_to_narrator(monkeypatch):
    session, handler, action_msg = make_player_action_session(actor="Rux")
    _statuses_on(session, "Rux", Status(
        text="Mortal Injury — dies in 6 rounds unless stabilized",
        severity=StatusSeverity.Scar, incapacitating=True, stabilizable=True,
    ))
    narrator_called = {"hit": False}
    # Patch the narrator-dispatch entry the handler calls after the gate so we
    # only assert the gate PERMITTED + ROUTED (unit scope; full loop is Task 8).
    monkeypatch.setattr(
        "sidequest.handlers.player_action._dispatch_to_narrator",  # confirm the real symbol
        lambda *a, **k: narrator_called.__setitem__("hit", True) or [],
    )
    out = await handler(action_msg, session)
    assert not any(m.type == MessageType.CHARACTER_INCAPACITATED for m in out)
    assert narrator_called["hit"] is True
```

> Confirm the actual narrator-dispatch symbol the handler calls after the gate (grep `player_action.py` for the call that follows line 589) and patch that exact name. Do not assert on source text.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/handlers/test_player_action_dying_window_gate.py -v`
Expected: FAIL — the stabilizable case is blocked today (gate treats all incapacitating statuses alike), so `CHARACTER_INCAPACITATED` is emitted and the narrator is never reached.

- [ ] **Step 3: Carve the gate**

In `sidequest/handlers/player_action.py`, after resolving `downed_status` (line 547), let a stabilizable window fall through instead of blocking:

```python
        downed_status = find_incapacitating_status(downed_core) if downed_core is not None else None
        # 108-6 dying-window carve: a stabilizable window is incapacitating-for-
        # normal-play but the downed soloist may still ACT (free-text) to try to
        # stabilize. Permit + route to the narrator; only a TERMINAL status blocks.
        # The clock is ticked by the player's own submission (post_resolution).
        if downed_status is not None and getattr(downed_status, "stabilizable", False):
            from sidequest.telemetry.spans.encounter import (
                player_action_dying_window_permitted_span,
            )

            with player_action_dying_window_permitted_span(
                character=acting_name, status_text=downed_status.text,
            ):
                pass
            downed_status = None  # fall through to narrator dispatch below
        if downed_status is not None:
            # ... existing terminal-block body unchanged (build_incapacitated_message) ...
```

Add the permit span to `sidequest/telemetry/spans/encounter.py` next to `player_action_blocked_incapacitated_span`, mirroring its shape (it is a context manager). Register its route the same way the blocked span is registered.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/handlers/test_player_action_dying_window_gate.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add sidequest/handlers/player_action.py sidequest/telemetry/spans/encounter.py tests/handlers/test_player_action_dying_window_gate.py
git commit -m "feat(wwn): gate carve — stabilizable dying window permits+routes, terminal still blocks"
```

---

## Task 6: Engine-owned `rounds_elapsed` + HP-to-1 on stabilize

`stabilize_mortal_injury` trusts a narrator-supplied `rounds_elapsed`. Derive it from the window's `created_turn` provenance, keep the narrator arg only as a fail-loud cross-check, and actually restore HP to 1 on success (today the tool appends "Frail — recovering at 1 HP" but never sets HP).

**Files:**
- Modify: `sidequest/agents/tools/stabilize_mortal_injury.py`
- Test: `tests/agents/tools/test_stabilize_rounds_elapsed_derivation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/tools/test_stabilize_rounds_elapsed_derivation.py
"""rounds_elapsed is engine-derived from created_turn; mismatch fails loud; HP -> 1."""

import pytest

from sidequest.agents.tools.stabilize_mortal_injury import stabilize_mortal_injury, StabilizeMortalInjuryArgs
from tests.fixtures.wwn import make_stabilize_ctx  # reuse existing tool-ctx harness


@pytest.mark.asyncio
async def test_difficulty_uses_derived_rounds_not_supplied():
    # Window opened at turn 3; current interaction is 5 -> derived rounds_elapsed == 2,
    # difficulty == 10. roll 10 succeeds; a roll of 9 (which would pass the narrator's
    # bogus rounds_elapsed=0 difficulty of 8) must FAIL against the derived difficulty.
    ctx = make_stabilize_ctx(actor="Rux", created_turn=3, current_turn=5)
    args = StabilizeMortalInjuryArgs(actor="Rux", rounds_elapsed=2, roll=9)
    result = await stabilize_mortal_injury(args, ctx)
    assert result.data["difficulty"] == 10
    assert result.data["success"] is False


@pytest.mark.asyncio
async def test_success_sets_hp_to_one_and_downgrades_to_frail():
    ctx = make_stabilize_ctx(actor="Rux", created_turn=3, current_turn=4)  # derived == 1, diff 9
    args = StabilizeMortalInjuryArgs(actor="Rux", rounds_elapsed=1, roll=15)
    result = await stabilize_mortal_injury(args, ctx)
    assert result.data["success"] is True
    core = ctx.repository.load().snapshot.find_creature_core("Rux")
    assert core.hp.current == 1
    assert any("Frail" in s.text for s in core.statuses)
    assert not any(s.stabilizable for s in core.statuses)


@pytest.mark.asyncio
async def test_mismatch_between_supplied_and_derived_fails_loud():
    ctx = make_stabilize_ctx(actor="Rux", created_turn=3, current_turn=5)  # derived == 2
    args = StabilizeMortalInjuryArgs(actor="Rux", rounds_elapsed=0, roll=20)
    with pytest.raises(ValueError, match="rounds_elapsed"):
        await stabilize_mortal_injury(args, ctx)
```

> `make_stabilize_ctx` must seat a PC carrying the stabilizable window (created at `created_turn`) and set `snapshot.turn_manager.interaction = current_turn`. Reuse/extend the existing stabilize-tool test fixture.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/tools/test_stabilize_rounds_elapsed_derivation.py -v`
Expected: FAIL — difficulty uses the supplied value; HP is never set to 1; no mismatch guard.

- [ ] **Step 3: Derive, cross-check, and set HP**

In `stabilize_mortal_injury` (`sidequest/agents/tools/stabilize_mortal_injury.py`), after resolving `core` (the `snapshot.find_creature_core(args.actor)` block), replace the `difficulty = 8 + args.rounds_elapsed` line:

```python
    from sidequest.game.ruleset.without_number import is_dying_window_status

    window = next((s for s in core.statuses if is_dying_window_status(s)), None)
    if window is None:
        return ToolResult.error(
            f"{args.actor!r} carries no stabilizable dying window to stabilize", recoverable=False
        )

    # Engine-owned clock: difficulty rises with REAL elapsed rounds (created_turn
    # provenance), never a narrator guess (lie-detector — No Silent Fallbacks).
    derived_rounds = max(0, snapshot.turn_manager.interaction - window.created_turn)
    if args.rounds_elapsed != derived_rounds:
        raise ValueError(
            f"stabilize_mortal_injury rounds_elapsed mismatch: narrator supplied "
            f"{args.rounds_elapsed}, engine-derived {derived_rounds} "
            f"(created_turn={window.created_turn}, current={snapshot.turn_manager.interaction}). "
            "Refusing to resolve on a fudged clock."
        )
    rounds_elapsed = derived_rounds
    difficulty = 8 + rounds_elapsed
    success = args.roll >= difficulty

    if success:
        core.statuses = [s for s in core.statuses if not is_dying_window_status(s)]
        core.statuses.append(Status(text=_FRAIL_TEXT, severity=StatusSeverity.Wound))
        core.hp.adjust(1 - core.hp.current)  # recover at exactly 1 HP (was never set before)
```

Update the remaining references in the function from `args.rounds_elapsed` to `rounds_elapsed` (the OTEL attribute and the `ToolResult.ok({...})` payload), and change the `StabilizeMortalInjuryArgs.rounds_elapsed` field description to note it is a cross-check the engine validates, not the authority.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agents/tools/test_stabilize_rounds_elapsed_derivation.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Guard the existing stabilize suite**

Run: `uv run pytest tests/agents/tools -k stabilize -v`
Expected: PASS. Update any prior test that constructed the actor without a dying-window status (the tool now requires one) — that is the intended new contract.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/tools/stabilize_mortal_injury.py tests/agents/tools/test_stabilize_rounds_elapsed_derivation.py
git commit -m "feat(wwn): stabilize derives rounds_elapsed from provenance (fail-loud), restores HP to 1"
```

---

## Task 7: Per-turn expiry + tick/resolved spans

Every dying-window turn must tick the clock and, on deadline, convert the window to terminal — even when the player's action was not a stabilization. This lives in the per-PC post-resolution pass (`apply_post_resolution_lethality`), which runs after each action resolves, so a wasted round still advances toward death.

**Files:**
- Modify: `sidequest/server/post_resolution_lethality.py` (`apply_post_resolution_lethality`, ~line 177)
- Test: `tests/server/test_dying_window_expiry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/server/test_dying_window_expiry.py
"""A dying window expires to terminal-dead on the deadline round, even on a non-stabilize turn."""

from sidequest.game.status import Status, StatusSeverity
from sidequest.game.ruleset.without_number import is_dying_window_status
from sidequest.server.post_resolution_lethality import apply_post_resolution_lethality
from tests.fixtures.wwn import make_post_resolution_inputs  # reuse existing harness


def _seat_window(core, *, created_turn, rounds):
    core.statuses.append(Status(
        text=f"Mortal Injury — dies in {rounds} rounds unless stabilized",
        severity=StatusSeverity.Scar, created_turn=created_turn,
        incapacitating=True, stabilizable=True,
    ))


def test_window_survives_before_deadline():
    inputs = make_post_resolution_inputs(actor="Rux", current_turn=5)
    _seat_window(inputs.core, created_turn=3, rounds=6)  # deadline 9, now 5
    apply_post_resolution_lethality(**inputs.kwargs)
    assert any(is_dying_window_status(s) for s in inputs.core.statuses)


def test_window_expires_to_terminal_on_deadline():
    inputs = make_post_resolution_inputs(actor="Rux", current_turn=9)
    _seat_window(inputs.core, created_turn=3, rounds=6)  # deadline 9, now 9
    apply_post_resolution_lethality(**inputs.kwargs)
    assert not any(is_dying_window_status(s) for s in inputs.core.statuses)
    assert any(s.incapacitating and not s.stabilizable for s in inputs.core.statuses)
```

> Confirm the exact call signature of `apply_post_resolution_lethality` and what `make_post_resolution_inputs` must supply (snapshot, encounter outcome, genre policy). Reuse the existing post-resolution-lethality test fixture; extend it to seat the window if needed.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_dying_window_expiry.py -v`
Expected: FAIL — nothing expires the window; on the deadline turn the window persists and no terminal status is applied.

- [ ] **Step 3: Add the expiry pass**

In `sidequest/server/post_resolution_lethality.py`, inside `apply_post_resolution_lethality`, for each handled PC core, before/alongside the existing lethality decision add the dying-window tick+expiry (only under a WN binding with `cfg.trauma`):

```python
    from sidequest.game.ruleset.without_number import is_dying_window_status

    window = next((s for s in core.statuses if is_dying_window_status(s)), None)
    if window is not None:
        rounds_elapsed = max(0, snapshot.turn_manager.interaction - window.created_turn)
        rounds = cfg.trauma.mortal_injury_rounds
        difficulty = 8 + rounds_elapsed
        expired = snapshot.turn_manager.interaction >= window.created_turn + rounds

        from sidequest.telemetry.spans.wn import (
            dying_window_resolved_span,
            dying_window_tick_span,
        )

        dying_window_tick_span(
            ruleset=ruleset.slug, actor=core.name, rounds_elapsed=rounds_elapsed,
            difficulty=difficulty, action_was_stabilization=False,
        )
        if expired:
            core.statuses = [s for s in core.statuses if not is_dying_window_status(s)]
            core.statuses.append(Status(
                text="Slain — succumbed to mortal wounds",
                severity=StatusSeverity.Scar, incapacitating=True, stabilizable=False,
                created_turn=window.created_turn, created_in_encounter=window.created_in_encounter,
            ))
            dying_window_resolved_span(
                ruleset=ruleset.slug, actor=core.name, outcome="died",
                final_rounds_elapsed=rounds_elapsed, resulting_status="terminal-dead",
            )
```

> **Where exactly:** insert this so it runs for the downed PC on every post-resolution pass. Confirm `ruleset`/`cfg`/`snapshot` are in scope in `apply_post_resolution_lethality`; if the function resolves the bound module elsewhere, reuse that handle rather than re-resolving. The `resolved(outcome="stabilized")` span fires from the stabilize tool's success branch (Task 6) — add that emit there: on success, after setting HP to 1, call `dying_window_resolved_span(..., outcome="stabilized", resulting_status="Frail")`.

- [ ] **Step 4: Add the stabilized-resolved span to Task 6's success branch**

In `stabilize_mortal_injury`, inside the `if success:` block (after HP set), emit the exit span so both outcomes are covered:

```python
        from sidequest.telemetry.spans.wn import dying_window_resolved_span

        dying_window_resolved_span(
            ruleset=module.slug, actor=args.actor, outcome="stabilized",
            final_rounds_elapsed=rounds_elapsed, resulting_status="Frail",
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/server/test_dying_window_expiry.py tests/agents/tools/test_stabilize_rounds_elapsed_derivation.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/post_resolution_lethality.py sidequest/agents/tools/stabilize_mortal_injury.py tests/server/test_dying_window_expiry.py
git commit -m "feat(wwn): per-turn dying-window expiry to terminal + tick/resolved spans"
```

---

## Task 8: End-to-end solo wiring test (mandatory)

Prove the loop actually turns: a solo PC drops with no live hostile, is **not** halted, drives the window by hand through the real `player_action` entry, and reaches both terminal outcomes. This is the test that fails on `develop` today and passes only when every seam is wired through to dispatch.

**Files:**
- Test: `tests/server/test_wwn_dying_window_wiring.py`

- [ ] **Step 1: Write the wiring test**

```python
# tests/server/test_wwn_dying_window_wiring.py
"""End-to-end: solo WWN dying window drives by player submission to both outcomes.

Wiring assertions are behavioral + OTEL-span based (CLAUDE.md: no source-text
wiring tests). Drives the real player_action handler against a WWN session.
"""

import pytest

from sidequest.game.ruleset.without_number import is_dying_window_status
from sidequest.protocol.enums import MessageType
from tests.fixtures.wwn import make_live_wwn_solo_session  # full session harness (server fixtures)
from tests.telemetry.test_helpers import capture_spans


@pytest.mark.asyncio
async def test_solo_pc_down_is_not_halted_and_can_stabilize():
    # PC clears the room, then succumbs: drop to 0 HP with NO live hostile.
    session, submit, pc = make_live_wwn_solo_session(pc="Rux")
    with capture_spans() as spans:
        await session.down_pc_with_no_live_hostile("Rux")

    core = session.core("Rux")
    assert any(is_dying_window_status(s) for s in core.statuses), "window must open in solo"
    assert spans.named("wwn.dying_window.opened").attributes["reason"] == "no_live_hostile"

    # The loop is NOT halted: a free-text submission is permitted and reaches the narrator.
    out = await submit("Rux", "I press both hands to the wound and bind it with my cloak")
    assert not any(m.type == MessageType.CHARACTER_INCAPACITATED for m in out)
    assert spans.any("wwn.dying_window.tick"), "the player's submission must tick the clock"


@pytest.mark.asyncio
async def test_solo_pc_stalling_past_deadline_dies():
    session, submit, pc = make_live_wwn_solo_session(pc="Rux")
    await session.down_pc_with_no_live_hostile("Rux")
    rounds = session.cfg.trauma.mortal_injury_rounds

    with capture_spans() as spans:
        # Burn every round on non-stabilization actions; the clock cannot be paused.
        for _ in range(rounds + 1):
            await submit("Rux", "I shout for help and crawl toward the door")

    core = session.core("Rux")
    assert not any(is_dying_window_status(s) for s in core.statuses)
    assert any(s.incapacitating and not s.stabilizable for s in core.statuses), "must be terminal"
    assert spans.named("wwn.dying_window.resolved").attributes["outcome"] == "died"
```

> Build `make_live_wwn_solo_session` on the existing server session test harness (grep `tests/server/` for the fixture that drives `player_action` against a real session + genre pack). `down_pc_with_no_live_hostile` drives damage through the real strike/lethality path so the down is genuine, not hand-stamped. If the narrator is mocked in this harness, stub it to call `stabilize_mortal_injury` for a stabilization-shaped action and to no-op for others — the point is the *engine* wiring (gate → tick → expiry), not LLM behavior.

- [ ] **Step 2: Run to verify it fails on the integrated path**

Run: `uv run pytest tests/server/test_wwn_dying_window_wiring.py -v`
Expected: PASS once Tasks 1–7 are in. If either test fails, a seam is unwired — fix the seam, not the test.

- [ ] **Step 3: Full gate**

Run: `uv run pytest -q && uv run ruff check . && uv run pyright`
Expected: all green. Investigate any failure before proceeding.

- [ ] **Step 4: Commit**

```bash
git add tests/server/test_wwn_dying_window_wiring.py
git commit -m "test(wwn): end-to-end solo dying-window wiring (gate -> tick -> both outcomes)"
```

---

## Self-Review

**Spec coverage:**
- Section 1 (state machine, single status, live-hostile branch, overkill predicate) → Tasks 3, 4. *Overkill→skip-window:* the live-hostile branch + the existing `already_terminal` supersede (Task 4) cover the instakill path — an overkill verdict stamps the incapacitating terminal status first, so `already_terminal` is True and no window opens. **Confirm** during Task 4 that an explicit instakill verdict reaches the seam already-incapacitated; if it can arrive *before* the verdict, add the overkill predicate to the branch explicitly.
- Section 2 (input carve, free-text, monkey's-paw) → Task 5. Monkey's-paw "burns a round, accomplishes nothing" is narrator behavior over the permitted lane; the engine guarantee (a burned round still advances expiry) is Task 7.
- Section 3 (engine-owned clock, fail-loud, expiry home) → Tasks 6, 7.
- Section 4 (three spans + #846 fold) → Task 2, emitted in Tasks 4, 6, 7.
- Section 5 (test strategy, wiring test) → tests in every task + Task 8.

**Placeholder scan:** No "TBD"/"handle edge cases" steps. Fixture-construction notes (`make_*`) point at reusing existing harnesses with a named fallback (grep the neighboring suite) rather than inventing stubs — the spec forbids new stubs, and the exact fixture shape depends on harnesses the Dev can see. Symbols to confirm against live code are flagged inline (`_dispatch_to_narrator`, `apply_post_resolution_lethality` scope of `ruleset`/`cfg`).

**Type consistency:** `is_dying_window_status` (Task 3) used identically in Tasks 4, 6, 7. `Status.stabilizable` (Task 1) read everywhere via that predicate, never by text. Span emitter names (`dying_window_opened_span`/`_tick_span`/`_resolved_span`) consistent across Tasks 2, 4, 7. `created_turn` provenance is the single clock source in Tasks 6 and 7 (`current − created_turn`), so the difficulty the tool checks and the expiry the pass computes cannot drift.

**One open verification carried to execution:** the exact insertion point and in-scope handles (`ruleset`, `cfg`, `snapshot`) inside `apply_post_resolution_lethality` (Task 7, Step 3) — the Dev confirms against the live function. This is a scope confirmation, not a design gap.
