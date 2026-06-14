# F2a — Fate Action Classifier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A freeform natural-language player action, in a pack bound `ruleset: fate` with an active conflict, is classified by the Intent Router into a `fate_action` dispatch and routed through the dispatch bank to `dispatch_fate_action` (F1d) — emitting `fate.action.classified` so the GM panel can confirm the Fate action was *engaged from language*, not improvised. This is the freeform-text counterpart to F1d's explicit `FATE_ACTION` message channel; both converge on the one engine entry, `dispatch_fate_action`.

**Architecture:** F2a rides the existing pre-narrator spine (ADR-113) rather than building anything parallel. A new `fate_action` subsystem (`agents/subsystems/fate_action.py`) is registered in the dispatch bank; the router learns the Fate vocabulary (PC skills + live aspects) via a per-turn `fate` block in the state summary (gated on `pack.rules.ruleset == "fate"`) and a routing-rules section in its system prompt. The handler reads `dispatch.params`, builds a `FateActionPayload`, and calls the existing `dispatch_fate_action`. A precondition-gate entry drops a `fate_action` dispatched outside an active conflict (the in-conflict scope of `dispatch_fate_action`), and a new `fate.action.classified` OTEL span anchors the F2 lie-detector.

**Tech Stack:** Python 3.14, pydantic v2, pytest (`-n0`), OpenTelemetry SDK, `uv`. **All paths under `sidequest-server/`.** Branch off `develop` (gitflow); feature branch `feat/f2a-fate-action-classifier`.

**Decision of record:** ADR-144. **Design:** `docs/superpowers/specs/2026-06-14-fate-core-binding-replaces-native-design.md` §4.5, §6; epic map `docs/superpowers/plans/2026-06-14-f2-narrator-intent-router-integration.md`. **Depends on:** F1a–F1d merged (`FateRulesetModule`, `FateActionPayload`, `dispatch_fate_action`, the 12 live Fate spans).

---

## F2 slice map (context — this plan is F2a only)

| Slice | Scope | Status |
|-------|-------|--------|
| **F2a** | Fate action classifier (router → `fate_action` subsystem → `dispatch_fate_action`) | **this plan** |
| F2b | Aspects-as-prompt + invoke surfacing + compel proposal | next |
| F2c | Create-advantage rendering + Fate honesty lie-detector | after F2b |
| F2d | Opponent AI (deterministic proactive opponent action) | after F2a |

F2a settles the shared contracts (the `fate_action` subsystem, the `dispatch.params` shape, the `_build_fate_summary` projection, the `fate.action.classified` span). F2b/F2c/F2d build on them.

---

## Routing model (read before coding)

- **Two entry channels, one engine.** F1d added the **explicit** channel: a `FATE_ACTION` `GameMessage` → `FateActionHandler` → `dispatch_fate_action` (for the F3 UI / direct submissions). F2a adds the **freeform** channel: a player types prose → `IntentRouter` classifies it → a `fate_action` subsystem dispatch → `run_fate_action_dispatch` → **the same** `dispatch_fate_action`. No duplication of the engine entry.
- **Classification is the existing router (Haiku), not a new LLM call.** The `IntentRouter` already turns freeform text into a `DispatchPackage` via forced tool-use. F2a teaches it one new subsystem (`fate_action`) and gives it the Fate vocabulary; it does not add a second classifier (CLAUDE.md "Don't Reinvent").
- **Mechanical engagement is pre-narrator.** The bank engages `dispatch_fate_action` on the canonical snapshot BEFORE the narrator runs, so the narrator (F2b/F2c) narrates already-real Fate state — same producer-side Illusionism counter the confrontation subsystem delivers.
- **In-conflict scope.** `dispatch_fate_action` requires an active, unresolved encounter (it raises `FateConflictError` otherwise). F2a classifies in-conflict actions only; an out-of-conflict overcome (a plain `resolve_action` skill check) is a flagged follow-up (epic doc §7.1), not silently handled. The precondition gate enforces the scope.
- **Fail loud.** An invalid `action` param, a non-Fate ruleset, or an unseated actor all fail loud (`ValueError` / `FateConflictError`) — the bank records the error span and the watcher sees the gap (No Silent Fallbacks).

---

## File structure (F2a)

- **Modify** `sidequest/telemetry/spans/fate.py` — add `fate_action_classified_span` + its `SPAN_ROUTES` entry.
- **Create** `sidequest/agents/subsystems/fate_action.py` — `run_fate_action_dispatch`.
- **Modify** `sidequest/agents/subsystems/__init__.py` — register `fate_action` in `_register_defaults` + docstring.
- **Modify** `sidequest/server/intent_router_pass.py` — `_build_fate_summary` + the `fate`-block enrichment in `_build_state_summary`.
- **Modify** `sidequest/agents/intent_router.py` — `FATE_ROUTING_RULES` spliced into `_SYSTEM_PROMPT`.
- **Modify** `sidequest/agents/dispatch_precondition_gate.py` — `_fate_action_precondition_unmet` + map entries.
- **Create** `tests/telemetry/test_fate_action_classified_span.py` — span emits + routes.
- **Create** `tests/agents/subsystems/test_fate_action_dispatch.py` — handler builds payload, routes, emits, fails loud.
- **Create** `tests/server/test_fate_classifier_enrichment.py` — `fate` block present for Fate pack, absent otherwise.
- **Create** `tests/server/test_fate_classifier_wiring.py` — end-to-end through the real bank + precondition gate.

---

## Task 1: `fate.action.classified` OTEL span

**Files:**
- Modify: `sidequest/telemetry/spans/fate.py`
- Test: `tests/telemetry/test_fate_action_classified_span.py`

- [ ] **Step 1: Write the failing test**

Create `tests/telemetry/test_fate_action_classified_span.py`:

```python
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.telemetry.spans._core import SPAN_ROUTES
from sidequest.telemetry.spans.fate import fate_action_classified_span


def _otel():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_span_emits_with_attributes():
    exporter, tracer = _otel()
    fate_action_classified_span(
        actor="Hero", action="attack", skill="Fight", target="Thug",
        confidence=0.91, _tracer=tracer,
    )
    spans = {s.name: s for s in exporter.get_finished_spans()}
    assert "fate.action.classified" in spans
    attrs = spans["fate.action.classified"].attributes
    assert attrs["actor"] == "Hero"
    assert attrs["action"] == "attack"
    assert attrs["skill"] == "Fight"
    assert attrs["target"] == "Thug"


def test_span_is_routed_for_the_gm_panel():
    # Registered as a typed state_transition route so the GM panel surfaces it.
    assert "fate.action.classified" in SPAN_ROUTES
    route = SPAN_ROUTES["fate.action.classified"]
    extracted = route.extract(
        type("S", (), {"attributes": {"actor": "Hero", "action": "overcome", "skill": "Notice"}})()
    )
    assert extracted["field"] == "action_classified"
    assert extracted["action"] == "overcome"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_fate_action_classified_span.py -n0 -q`
Expected: FAIL — `ImportError: cannot import name 'fate_action_classified_span' from 'sidequest.telemetry.spans.fate'`

- [ ] **Step 3: Add the route + the emitter**

In `sidequest/telemetry/spans/fate.py`, add the `SPAN_ROUTES` entry immediately after the F1c block (after the `SPAN_ROUTES["fate.conceded"] = ...` entry, ~line 297):

```python
# --- F2a: classification span (GM panel = lie detector) ----------------------
# The router classified a freeform action into one of the four Fate actions and
# the bank engaged dispatch_fate_action. Literal key (no SPAN_* constant) — the
# routing-completeness lint only inspects SPAN_* module constants.
SPAN_ROUTES["fate.action.classified"] = SpanRoute(
    event_type="state_transition",
    component="fate",
    extract=lambda span: {
        "field": "action_classified",
        "actor": (span.attributes or {}).get("actor", ""),
        "action": (span.attributes or {}).get("action", ""),
        "skill": (span.attributes or {}).get("skill", ""),
        "target": (span.attributes or {}).get("target", ""),
        "confidence": (span.attributes or {}).get("confidence", 0.0),
    },
)
```

Add the emitter after `fate_conceded_span` (~line 387, before `__all__`):

```python
def fate_action_classified_span(
    *,
    actor: str,
    action: str,
    skill: str,
    target: str = "",
    confidence: float = 0.0,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit ``fate.action.classified`` — the Intent Router classified a freeform
    player action into one of the four Fate actions (F2a). The GM-panel evidence
    that a Fate action was engaged from natural language, not improvised."""
    attributes: dict[str, Any] = {
        "field": "action_classified",
        "actor": actor,
        "action": action,
        "skill": skill,
        "target": target,
        "confidence": confidence,
        **attrs,
    }
    with Span.open("fate.action.classified", attributes, tracer_override=_tracer):
        pass
```

Add `"fate_action_classified_span",` to the `__all__` list (keep it alphabetized — it goes first).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/telemetry/test_fate_action_classified_span.py -n0 -q`
Expected: PASS (2 tests)

- [ ] **Step 5: Guard the routing-completeness lint**

Run: `uv run pytest tests/telemetry/test_routing_completeness.py -n0 -q`
Expected: PASS — a literal-keyed `SPAN_ROUTES` entry needs no `SPAN_*` constant, so the lint is unaffected (same pattern as the F1b/F1c Fate routes).

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans/fate.py tests/telemetry/test_fate_action_classified_span.py
git commit -m "feat(fate): fate.action.classified span (ADR-144 F2a)"
```

---

## Task 2: `run_fate_action_dispatch` handler + registration

**Files:**
- Create: `sidequest/agents/subsystems/fate_action.py`
- Modify: `sidequest/agents/subsystems/__init__.py`
- Test: `tests/agents/subsystems/test_fate_action_dispatch.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/subsystems/test_fate_action_dispatch.py`:

```python
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.agents.subsystems import SubsystemOutput, get_registered
from sidequest.agents.subsystems.fate_action import run_fate_action_dispatch
from sidequest.game.character import Character
from sidequest.game.creature_core import CreatureCore
from sidequest.game.encounter import EncounterActor, EncounterMetric, StructuredEncounter
from sidequest.game.fate_sheet import Aspect, FateSheet
from sidequest.game.session import GameSnapshot, Npc
from sidequest.protocol.dispatch import SubsystemDispatch, VisibilityTag


def _otel():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # The handler emits through the global tracer (no _tracer kwarg on the bank
    # path), so install this provider as the process tracer for the assertion.
    from opentelemetry import trace

    trace.set_tracer_provider(provider)
    return exporter


def _pc(name: str, skills: dict[str, int]) -> Character:
    core = CreatureCore(
        name=name, description="d", personality="p", fate_sheet=FateSheet(skills=skills)
    )
    return Character(core=core, char_class="Agent", race="Human", backstory="b")


def _depleted_thug() -> Npc:
    sheet = FateSheet(skills={"Athletics": 0})
    for b in sheet.stress["physical"].boxes:
        b.checked = True
    for c in sheet.consequences:
        c.aspect = Aspect(text="old wound", kind="consequence", free_invokes=0)
    return Npc(core=CreatureCore(name="Thug", description="d", personality="p", fate_sheet=sheet))


def _solo_combat() -> tuple[GameSnapshot, StructuredEncounter]:
    enc = StructuredEncounter(
        encounter_type="duel",
        category="combat",
        player_metric=EncounterMetric(name="p", threshold=10),
        opponent_metric=EncounterMetric(name="o", threshold=10),
        actors=[
            EncounterActor(name="Hero", role="lead", side="player"),
            EncounterActor(name="Thug", role="foe", side="opponent"),
        ],
    )
    snap = GameSnapshot(genre_slug="fate_test", characters=[_pc("Hero", {"Fight": 4})], encounter=enc)
    snap.npcs.append(_depleted_thug())
    return snap, enc


def _fate_pack():
    return SimpleNamespace(rules=SimpleNamespace(ruleset="fate"))


def _dispatch(action: str, **params) -> SubsystemDispatch:
    return SubsystemDispatch(
        subsystem="fate_action",
        params={"action": action, **params},
        idempotency_key="fate_action_t1",
        visibility=VisibilityTag(visible_to="all"),
        confidence=0.95,
    )


def test_handler_builds_payload_routes_and_emits_classified_span():
    exporter = _otel()
    snap, enc = _solo_combat()
    out = asyncio.run(
        run_fate_action_dispatch(
            _dispatch("attack", skill="Fight", target="Thug"),
            snapshot=snap,
            pack=_fate_pack(),
            player_name="Hero",
        )
    )
    assert isinstance(out, SubsystemOutput)
    # Routed to dispatch_fate_action → solo barrier closed → exchange resolved.
    assert enc.find_actor("Thug").withdrawn is True
    assert enc.resolved is True
    names = [s.name for s in exporter.get_finished_spans()]
    assert "fate.action.classified" in names
    assert "fate.exchange.resolved" in names


def test_invalid_action_fails_loud():
    snap, _ = _solo_combat()
    with pytest.raises(ValueError):
        asyncio.run(
            run_fate_action_dispatch(
                _dispatch("parry", skill="Fight", target="Thug"),  # not one of the four
                snapshot=snap,
                pack=_fate_pack(),
                player_name="Hero",
            )
        )


def test_fate_action_is_a_registered_subsystem():
    # Runtime registry membership (not a source grep) — the bank can resolve it.
    assert "fate_action" in get_registered()


def test_non_fate_ruleset_returns_error_not_silent_success():
    snap, enc = _solo_combat()
    out = asyncio.run(
        run_fate_action_dispatch(
            _dispatch("attack", skill="Fight", target="Thug"),
            snapshot=snap,
            pack=SimpleNamespace(rules=SimpleNamespace(ruleset="native")),  # NOT fate
            player_name="Hero",
        )
    )
    assert out.data.get("error") == "fate_dispatch_error"  # dispatch_fate_action raised, caught loud
    assert enc.resolved is False  # nothing engaged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/subsystems/test_fate_action_dispatch.py -n0 -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.agents.subsystems.fate_action'`

- [ ] **Step 3: Create the handler**

Create `sidequest/agents/subsystems/fate_action.py`:

```python
"""fate_action subsystem dispatch handler — Intent Router live engager for the
Fate Core channel (ADR-144 F2a).

The router (``sidequest/agents/intent_router.py``) classifies a freeform player
action in a Fate-bound pack and emits a ``SubsystemDispatch`` with
``subsystem="fate_action"`` and ``params`` mirroring ``FateActionPayload``
(action / skill / target / difficulty / invoke_aspect / aspect_text). This
handler is the freeform-text counterpart to F1d's explicit ``FATE_ACTION``
message channel: it builds the payload and routes it to the SAME engine entry,
``dispatch_fate_action`` (which ``isinstance``-gates to the Fate engine and seals
or resolves the exchange).

Engagement happens BEFORE the narrator runs, so the narrator (F2b/F2c) narrates
already-real Fate state. Returns an empty ``SubsystemOutput`` on success — the
engagement is the directive (the resolved exchange is the narrator's grounding
truth), exactly like ``run_confrontation_dispatch``.

No silent fallbacks: an invalid action propagates as ``ValueError`` (the bank
records the error span); a non-Fate ruleset / no active encounter / an unseated
actor surface as ``FateConflictError`` from ``dispatch_fate_action``, caught and
returned as ``data["error"]`` so the bank continues and the watcher sees the gap.
"""

from __future__ import annotations

import logging
import random

from sidequest.agents.subsystems import SubsystemOutput
from sidequest.game.ruleset import get_ruleset_module
from sidequest.game.session import GameSnapshot
from sidequest.genre.models.pack import GenrePack
from sidequest.protocol.dispatch import SubsystemDispatch
from sidequest.protocol.fate import FateActionPayload
from sidequest.server.dispatch.fate_conflict import FateConflictError, dispatch_fate_action
from sidequest.telemetry.spans.fate import fate_action_classified_span

logger = logging.getLogger(__name__)

_VALID_ACTIONS = ("overcome", "create_advantage", "attack", "concede")


async def run_fate_action_dispatch(
    dispatch: SubsystemDispatch,
    *,
    snapshot: GameSnapshot,
    pack: GenrePack,
    player_name: str,
) -> SubsystemOutput:
    """Engage one classified Fate action on the canonical snapshot."""
    params = dispatch.params
    action = params.get("action")
    if action not in _VALID_ACTIONS:
        # No silent fallback: a fate_action dispatch with no valid action is a
        # router-output bug. The bank's exception-catch wraps this as an error
        # span; the watcher then sees zero engagement.
        raise ValueError(
            f"fate_action dispatch has invalid params['action']={action!r}; "
            f"must be one of {_VALID_ACTIONS}"
        )

    skill = str(params.get("skill", ""))
    raw_target = params.get("target")
    target = str(raw_target) if raw_target else None
    payload = FateActionPayload(
        request_id=dispatch.idempotency_key,
        action=action,
        skill=skill,
        target=target,
        difficulty=int(params.get("difficulty", 0) or 0),
        invoke_aspect=str(params.get("invoke_aspect", "")),
        aspect_text=str(params.get("aspect_text", "")),
    )

    # The F2 lie-detector anchor: a Fate action was classified from language.
    # Emitted before dispatch so the classification is recorded even if the
    # engine rejects the action (the GM panel then shows classify-without-engage).
    fate_action_classified_span(
        actor=player_name,
        action=action,
        skill=skill,
        target=target or "",
        confidence=float(dispatch.confidence),
    )

    ruleset = get_ruleset_module(pack.rules.ruleset)
    try:
        dispatch_fate_action(
            payload=payload,
            actor_name=player_name,
            encounter=snapshot.encounter,
            ruleset=ruleset,
            snapshot=snapshot,
            rng=random,
            round_number=snapshot.turn_manager.interaction,
        )
    except FateConflictError as exc:
        logger.warning("fate_action.dispatch_error error=%s", exc)
        return SubsystemOutput(data={"error": "fate_dispatch_error"})
    return SubsystemOutput()


__all__ = ["run_fate_action_dispatch"]
```

> `random` (the module) is the `rng` the production handler passes (matches `FateActionHandler` and `dispatch_dice_throw`). `snapshot.turn_manager.interaction` is the round number the dice/Fate handlers use.

- [ ] **Step 4: Register the subsystem**

In `sidequest/agents/subsystems/__init__.py`, in `_register_defaults` (line 176): add the import alongside the others (alphabetical, after `run_environment_clock_dispatch`):

```python
    from sidequest.agents.subsystems.fate_action import run_fate_action_dispatch
```

Add the registry tuple (after the `("environment_clock", run_environment_clock_dispatch),` entry):

```python
        ("fate_action", run_fate_action_dispatch),
```

Update the module docstring's handler list (after the `witnessed_act` bullet, ~line 29) to add:

```
  - ``fate_action`` → ``run_fate_action_dispatch`` — engages one classified
    Fate action (overcome/create_advantage/attack/concede) via
    ``dispatch_fate_action`` on a ``ruleset: fate`` pack (ADR-144 F2a).
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/agents/subsystems/test_fate_action_dispatch.py -n0 -q`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/subsystems/fate_action.py sidequest/agents/subsystems/__init__.py tests/agents/subsystems/test_fate_action_dispatch.py
git commit -m "feat(fate): run_fate_action_dispatch subsystem + registry (ADR-144 F2a)"
```

---

## Task 3: Router Fate vocabulary (state-summary enrichment + routing rules)

**Files:**
- Modify: `sidequest/server/intent_router_pass.py`
- Modify: `sidequest/agents/intent_router.py`
- Test: `tests/server/test_fate_classifier_enrichment.py`

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_fate_classifier_enrichment.py`:

```python
from __future__ import annotations

from types import SimpleNamespace

from sidequest.game.character import Character
from sidequest.game.creature_core import CreatureCore
from sidequest.game.encounter import EncounterActor, EncounterMetric, StructuredEncounter
from sidequest.game.fate_sheet import Aspect, FateSheet
from sidequest.game.session import GameSnapshot
from sidequest.server.intent_router_pass import _build_fate_summary, _build_state_summary


def _pc(name: str, skills: dict[str, int], fate_points: int = 3) -> Character:
    sheet = FateSheet(skills=skills, fate_points=fate_points)
    sheet.aspects.append(Aspect(text="Last Honest Cop in Vega", kind="high_concept"))
    return Character(
        core=CreatureCore(name=name, description="d", personality="p", fate_sheet=sheet),
        char_class="Agent", race="Human", backstory="b",
    )


def _conflict_snapshot() -> GameSnapshot:
    enc = StructuredEncounter(
        encounter_type="duel", category="combat",
        player_metric=EncounterMetric(name="p", threshold=10),
        opponent_metric=EncounterMetric(name="o", threshold=10),
        actors=[EncounterActor(name="Vance", role="lead", side="player")],
    )
    enc.situation_aspects.append(Aspect(text="Overturned Table", kind="situation", free_invokes=1))
    return GameSnapshot(genre_slug="pulp_noir", characters=[_pc("Vance", {"Fight": 3, "Notice": 2})], encounter=enc)


def _fate_pack():
    return SimpleNamespace(rules=SimpleNamespace(ruleset="fate", confrontations=[]), worlds=None, witnessed_acts=None)


def _native_pack():
    return SimpleNamespace(rules=SimpleNamespace(ruleset="native", confrontations=[]), worlds=None, witnessed_acts=None)


def test_build_fate_summary_shape():
    summary = _build_fate_summary(_conflict_snapshot())
    assert summary["skills"]["Vance"] == {"Fight": 3, "Notice": 2}
    assert summary["fate_points"]["Vance"] == 3
    assert "Last Honest Cop in Vega" in summary["character_aspects"]["Vance"]
    assert summary["scene_aspects"] == ["Overturned Table"]
    assert summary["active_conflict"] is True


def test_state_summary_carries_fate_block_for_fate_pack():
    summary = _build_state_summary(_conflict_snapshot(), pack=_fate_pack())
    assert "fate" in summary
    assert summary["fate"]["active_conflict"] is True


def test_state_summary_omits_fate_block_for_non_fate_pack():
    summary = _build_state_summary(_conflict_snapshot(), pack=_native_pack())
    assert "fate" not in summary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_fate_classifier_enrichment.py -n0 -q`
Expected: FAIL — `ImportError: cannot import name '_build_fate_summary' from 'sidequest.server.intent_router_pass'`

- [ ] **Step 3: Add `_build_fate_summary` + the enrichment**

In `sidequest/server/intent_router_pass.py`, add the builder just above `_build_state_summary` (~line 228):

```python
def _build_fate_summary(snapshot: GameSnapshot) -> dict[str, Any]:
    """Compact Fate vocabulary for the router (ADR-144 F2a).

    Gives the Haiku classifier the per-PC skills it can name, the fate points it
    can spend, the character aspects + live situation aspects it can invoke, and
    whether a conflict is active (the in-conflict scope of dispatch_fate_action).
    Only PCs with a Fate sheet contribute; on a non-Fate pack the caller never
    invokes this builder.
    """
    skills: dict[str, dict[str, int]] = {}
    fate_points: dict[str, int] = {}
    character_aspects: dict[str, list[str]] = {}
    for ch in snapshot.characters:
        sheet = ch.core.fate_sheet
        if sheet is None:
            continue
        skills[ch.core.name] = dict(sheet.skills)
        fate_points[ch.core.name] = sheet.fate_points
        character_aspects[ch.core.name] = [a.text for a in sheet.all_aspects()]
    enc = snapshot.encounter
    scene_aspects = [a.text for a in enc.situation_aspects] if enc is not None else []
    return {
        "skills": skills,
        "fate_points": fate_points,
        "character_aspects": character_aspects,
        "scene_aspects": scene_aspects,
        "active_conflict": enc is not None and not enc.resolved,
    }
```

In `_build_state_summary`, add the enrichment immediately after the `confrontation_types` block (after the `intent_router_confrontation_vocabulary_span` `with`/`pass`, ~line 349):

```python
    # Fate vocabulary (ADR-144 F2a): when the pack binds the Fate ruleset, the
    # router needs the PCs' skills + the live aspects to classify a freeform
    # action into one of the four Fate actions. Gated on the ruleset slug so no
    # non-Fate pack's router prompt carries this block (same conditional-vocab
    # discipline as confrontation_types / witnessed_act_vocabulary above).
    if pack is not None and getattr(pack.rules, "ruleset", "") == "fate":
        summary["fate"] = _build_fate_summary(snapshot)
```

> `GameSnapshot`, `Any`, and `pack` are already in scope in this module (the confrontation block above uses all three). No new imports.

- [ ] **Step 4: Run the enrichment test to verify it passes**

Run: `uv run pytest tests/server/test_fate_classifier_enrichment.py -n0 -q`
Expected: PASS (3 tests)

- [ ] **Step 5: Add the routing rules to the router system prompt**

In `sidequest/agents/intent_router.py`, define the routing-rules constant near the top of the module (after the existing prompt-fragment imports / above `_SYSTEM_PROMPT`):

```python
FATE_ROUTING_RULES = """
## Fate action classification (only when <game_state> contains a "fate" block)

When — and ONLY when — the game state includes a top-level "fate" object, this is
a Fate Core pack. Classify a player's freeform action that engages the four-action
core into a single dispatch with subsystem "fate_action" and these params:
  - action: one of "overcome", "create_advantage", "attack", "concede"
      * attack — they try to harm/defeat an opponent (deals stress).
      * create_advantage — they set up a situation aspect (pin, distract, scout).
      * overcome — they push past an obstacle that isn't an opponent's defense.
      * concede — they choose to lose on their own terms (pre-roll, voluntary).
  - skill: the Fate skill used, chosen from the acting PC's skills in
    fate.skills[<character>]. Pick the single best-fitting skill name verbatim.
  - target: the opposed actor's name for an attack/create_advantage against a
    foe; null otherwise.
  - difficulty: the passive opposition rung (integer) when there is no opposed
    target; 0 when target is set.
  - invoke_aspect: the exact text of an aspect from fate.scene_aspects or
    fate.character_aspects[<character>] the player explicitly leverages for +2;
    "" if none.
  - aspect_text: for create_advantage, the short name of the situation aspect
    being placed (e.g. "Pinned Down"); "" otherwise.

Only emit a fate_action dispatch when fate.active_conflict is true. Do NOT emit
it for narration, movement, or table-talk. Do NOT emit a confrontation dispatch
for the same action — fate_action operates inside an already-active conflict.
"""
```

Splice it into the assembled system prompt. Locate the `_SYSTEM_PROMPT` definition (it interpolates `CONFRONTATION_TRIGGER_CORE`); append `FATE_ROUTING_RULES` to its content so the Fate rules sit alongside the confrontation-trigger rules. For example, if `_SYSTEM_PROMPT` is built by concatenation/f-string, add `+ FATE_ROUTING_RULES` (or `{FATE_ROUTING_RULES}`) at the end of the rules section.

> Confirm the exact `_SYSTEM_PROMPT` assembly shape when you open the file (it is a module-level constant around line 103–263). The rules are behaviorally conditional — they instruct the model to emit `fate_action` ONLY when the `fate` block is present — so adding them to the static (cached) system prompt is safe for non-Fate packs: those packs never carry a `fate` block, so the model never emits a `fate_action`. This mirrors how `CONFRONTATION_TRIGGER_CORE` lives in the static prompt while the per-type vocabulary rides the per-turn state summary.

- [ ] **Step 6: Run the router suite to confirm the prompt still assembles**

Run: `uv run pytest tests/agents/ -k "intent_router" -n0 -q`
Expected: PASS — the additive prompt section breaks no existing router test; the system prompt still builds.

- [ ] **Step 7: Commit**

```bash
git add sidequest/server/intent_router_pass.py sidequest/agents/intent_router.py tests/server/test_fate_classifier_enrichment.py
git commit -m "feat(fate): router Fate vocabulary + classification rules (ADR-144 F2a)"
```

---

## Task 4: Precondition gate — drop `fate_action` outside an active conflict

**Files:**
- Modify: `sidequest/agents/dispatch_precondition_gate.py`
- Test: `tests/agents/test_fate_action_precondition_gate.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_fate_action_precondition_gate.py`:

```python
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.agents.dispatch_precondition_gate import (
    _fate_action_precondition_unmet,
    run_dispatch_precondition_gate,
)
from sidequest.game.character import Character
from sidequest.game.creature_core import CreatureCore
from sidequest.game.encounter import EncounterActor, EncounterMetric, StructuredEncounter
from sidequest.game.fate_sheet import FateSheet
from sidequest.game.session import GameSnapshot
from sidequest.protocol.dispatch import (
    DispatchPackage,
    PlayerDispatch,
    SubsystemDispatch,
    VisibilityTag,
)


def _pc(name: str) -> Character:
    return Character(
        core=CreatureCore(name=name, description="d", personality="p", fate_sheet=FateSheet()),
        char_class="Agent", race="Human", backstory="b",
    )


def _package() -> DispatchPackage:
    return DispatchPackage(
        turn_id="t1",
        per_player=[
            PlayerDispatch(
                player_id="p1", raw_action="I shoot the thug",
                dispatch=[
                    SubsystemDispatch(
                        subsystem="fate_action",
                        params={"action": "attack", "skill": "Fight", "target": "Thug"},
                        idempotency_key="fate_action_t1",
                        visibility=VisibilityTag(visible_to="all"),
                        confidence=0.95,
                    )
                ],
            )
        ],
        confidence_global=0.95,
    )


def _otel():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_precondition_unmet_with_no_encounter():
    snap = GameSnapshot(genre_slug="pulp_noir", characters=[_pc("Vance")])
    assert _fate_action_precondition_unmet(snap) is not None


def test_precondition_met_with_active_conflict():
    enc = StructuredEncounter(
        encounter_type="duel", category="combat",
        player_metric=EncounterMetric(name="p", threshold=10),
        opponent_metric=EncounterMetric(name="o", threshold=10),
        actors=[EncounterActor(name="Vance", role="lead", side="player")],
    )
    snap = GameSnapshot(genre_slug="pulp_noir", characters=[_pc("Vance")], encounter=enc)
    assert _fate_action_precondition_unmet(snap) is None


def test_gate_drops_fate_action_with_no_conflict_and_emits_span():
    snap = GameSnapshot(genre_slug="pulp_noir", characters=[_pc("Vance")])  # no encounter
    exporter, tracer = _otel()
    filtered = run_dispatch_precondition_gate(package=_package(), snapshot=snap, tracer=tracer)
    assert filtered.per_player[0].dispatch == []  # dropped
    assert "intent_router.dispatch.gated" in [s.name for s in exporter.get_finished_spans()]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/test_fate_action_precondition_gate.py -n0 -q`
Expected: FAIL — `ImportError: cannot import name '_fate_action_precondition_unmet'`

- [ ] **Step 3: Add the predicate + register it**

In `sidequest/agents/dispatch_precondition_gate.py`, add the predicate after `_magic_working_precondition_unmet` (~line 128):

```python
def _fate_action_precondition_unmet(snapshot: GameSnapshot) -> str | None:
    # ``fate_action`` engages dispatch_fate_action, which is conflict-scoped: it
    # requires an active, unresolved encounter and raises FateConflictError
    # otherwise. With no live conflict the dispatch can never engage, so it is
    # structurally inert (an out-of-conflict overcome is a separate, unbuilt
    # path — epic F2 §7.1, flagged not silently handled). The gate's loud
    # intent_router.dispatch.gated span keeps the GM panel honest about the skip.
    enc = snapshot.encounter
    if enc is None or enc.resolved:
        return "snapshot.encounter is None or resolved (no active Fate conflict to act within)"
    return None
```

Add it to `_INERT_PRECONDITIONS` (~line 130):

```python
_INERT_PRECONDITIONS: dict[str, Callable[[GameSnapshot], str | None]] = {
    "scenario_clue": _scenario_clue_precondition_unmet,
    "witnessed_act": _witnessed_act_precondition_unmet,
    "magic_working": _magic_working_precondition_unmet,
    "fate_action": _fate_action_precondition_unmet,
}
```

Add the identifying param for the gated span's `dispatched_type` (~line 139):

```python
_GATE_DISPATCHED_TYPE_KEY: dict[str, str] = {
    "scenario_clue": "fact_id",
    "witnessed_act": "act_id",
    "magic_working": "actor",
    "fate_action": "action",
}
```

> Unlike `magic_working`, `fate_action` does NOT also emit `dispatch_engagement.*.mismatch` from the gate — a Fate action with no live conflict is the same unavoidable-on-every-out-of-conflict-turn shape as the `scenario_clue` quiet-gate (epic §7.1's out-of-conflict overcome is the real fix), so the `intent_router.dispatch.gated` span alone is the right signal. The `run_dispatch_precondition_gate` magic-only `if g.subsystem == "magic_working"` branch already scopes the extra emission; no change needed there.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agents/test_fate_action_precondition_gate.py -n0 -q`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/dispatch_precondition_gate.py tests/agents/test_fate_action_precondition_gate.py
git commit -m "feat(fate): precondition-gate fate_action to active conflicts (ADR-144 F2a)"
```

---

## Task 5: End-to-end wiring — freeform action through the real bank

**Files:**
- Test: `tests/server/test_fate_classifier_wiring.py`

- [ ] **Step 1: Write the wiring test**

Create `tests/server/test_fate_classifier_wiring.py`:

```python
"""Wiring net for the freeform Fate action channel (ADR-144 F2a).

Neither assertion is a source grep (server CLAUDE.md "No Source-Text Wiring
Tests"):
  1. Runtime registry — ``fate_action`` resolves to its handler in the live bank
     registry (get_registered()).
  2. End-to-end — a fate_action SubsystemDispatch driven through the REAL
     run_dispatch_bank (with the real fate ruleset from get_ruleset_module)
     reaches dispatch_fate_action → run_fate_exchange: the exchange resolves and
     both fate.action.classified and fate.exchange.resolved fire.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.agents.subsystems import get_registered, run_dispatch_bank
from sidequest.game.character import Character
from sidequest.game.creature_core import CreatureCore
from sidequest.game.encounter import EncounterActor, EncounterMetric, StructuredEncounter
from sidequest.game.fate_sheet import Aspect, FateSheet
from sidequest.game.session import GameSnapshot, Npc
from sidequest.protocol.dispatch import (
    DispatchPackage,
    PlayerDispatch,
    SubsystemDispatch,
    VisibilityTag,
)


def _pc(name: str, skills: dict[str, int]) -> Character:
    return Character(
        core=CreatureCore(name=name, description="d", personality="p", fate_sheet=FateSheet(skills=skills)),
        char_class="Agent", race="Human", backstory="b",
    )


def _depleted_thug() -> Npc:
    sheet = FateSheet(skills={"Athletics": 0})
    for b in sheet.stress["physical"].boxes:
        b.checked = True
    for c in sheet.consequences:
        c.aspect = Aspect(text="old wound", kind="consequence", free_invokes=0)
    return Npc(core=CreatureCore(name="Thug", description="d", personality="p", fate_sheet=sheet))


def _solo_combat() -> tuple[GameSnapshot, StructuredEncounter]:
    enc = StructuredEncounter(
        encounter_type="duel", category="combat",
        player_metric=EncounterMetric(name="p", threshold=10),
        opponent_metric=EncounterMetric(name="o", threshold=10),
        actors=[
            EncounterActor(name="Hero", role="lead", side="player"),
            EncounterActor(name="Thug", role="foe", side="opponent"),
        ],
    )
    snap = GameSnapshot(genre_slug="fate_test", characters=[_pc("Hero", {"Fight": 4})], encounter=enc)
    snap.npcs.append(_depleted_thug())
    return snap, enc


def test_fate_action_is_registered_in_the_live_bank():
    assert "fate_action" in get_registered()


def test_freeform_fate_action_engages_the_exchange_through_the_bank():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    snap, enc = _solo_combat()
    pack = SimpleNamespace(rules=SimpleNamespace(ruleset="fate"))
    package = DispatchPackage(
        turn_id="t1",
        per_player=[
            PlayerDispatch(
                player_id="p1", raw_action="I lunge at the thug with my blade",
                dispatch=[
                    SubsystemDispatch(
                        subsystem="fate_action",
                        params={"action": "attack", "skill": "Fight", "target": "Thug"},
                        idempotency_key="fate_action_t1",
                        visibility=VisibilityTag(visible_to="all"),
                        confidence=0.95,
                    )
                ],
            )
        ],
        confidence_global=0.95,
    )

    result = asyncio.run(
        run_dispatch_bank(package, context={"snapshot": snap, "pack": pack, "player_name": "Hero"})
    )

    # Bank engaged the engine (confidence 0.95 ≥ 0.6 default), not degraded.
    assert result.decisions[0]["decision"] == "engaged"
    assert enc.find_actor("Thug").withdrawn is True
    assert enc.resolved is True
    names = [s.name for s in exporter.get_finished_spans()]
    assert "fate.action.classified" in names
    assert "fate.exchange.resolved" in names
```

> This drives the **real** `run_dispatch_bank` and **real** `get_ruleset_module("fate")` (via the handler), so it proves the full pre-narrator path — registry → confidence gate → handler → `dispatch_fate_action` → exchange. The `SimpleNamespace` pack stands in only for `pack.rules.ruleset`; the engine, registry, and span emission are all production code.

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/server/test_fate_classifier_wiring.py -n0 -q`
Expected: PASS (2 tests) — F2a is wired end-to-end.

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_fate_classifier_wiring.py
git commit -m "test(fate): end-to-end wiring for the freeform Fate classifier (ADR-144 F2a)"
```

---

## Task 6: Gate — lint, format, types, suites (+ non-Fate spine untouched)

**Files:** none (verification only)

- [ ] **Step 1: Lint the changed files (scoped)**

Run: `uv run ruff check sidequest/telemetry/spans/fate.py sidequest/agents/subsystems/fate_action.py sidequest/agents/subsystems/__init__.py sidequest/server/intent_router_pass.py sidequest/agents/intent_router.py sidequest/agents/dispatch_precondition_gate.py tests/telemetry/test_fate_action_classified_span.py tests/agents/subsystems/test_fate_action_dispatch.py tests/server/test_fate_classifier_enrichment.py tests/agents/test_fate_action_precondition_gate.py tests/server/test_fate_classifier_wiring.py`
Expected: `All checks passed!`

- [ ] **Step 2: Format the changed files (scoped)**

Run: `uv run ruff format <same file list>`
Expected: unchanged or reformatted in place (commit any reformat).

- [ ] **Step 3: Type check**

Run: `uv run pyright sidequest/agents/subsystems/fate_action.py sidequest/server/intent_router_pass.py sidequest/agents/dispatch_precondition_gate.py sidequest/telemetry/spans/fate.py`
Expected: `0 errors`

- [ ] **Step 4: Run the F2a + Fate + router suites**

Run: `uv run pytest tests/telemetry/test_fate_action_classified_span.py tests/agents/subsystems/test_fate_action_dispatch.py tests/server/test_fate_classifier_enrichment.py tests/agents/test_fate_action_precondition_gate.py tests/server/test_fate_classifier_wiring.py tests/server/dispatch/test_fate_dispatch_routing.py tests/telemetry/test_routing_completeness.py -n0 -q`
Expected: PASS — the F2a stack green, routing-completeness lint green.

- [ ] **Step 5: Prove the non-Fate dispatch spine is untouched**

Run: `uv run pytest tests/agents/subsystems/ tests/agents/ -k "dispatch or precondition or confrontation or router" -n0 -q`
Expected: PASS — the existing subsystems, the precondition/unregistered gates, and the confrontation path are unaffected; `fate_action` is a purely additive registry entry + a behaviorally-conditional prompt section.

- [ ] **Step 6: Commit any fixups**

```bash
git add -p
git commit -m "chore(fate): lint/format/type fixups (ADR-144 F2a)"
```

---

## Self-review (done against the spec + epic doc)

- **Spec §4.5 "Narrator (F2): action→{four-action, skill} classify":** the router classifies a freeform action into a `fate_action` dispatch with `action ∈ {overcome, create_advantage, attack, concede}` + `skill` from the PC's sheet — Task 2/3. ✓
- **Don't Reinvent (CLAUDE.md):** reuses the existing `IntentRouter` + dispatch bank + `dispatch_fate_action` (F1d); the only net-new engine surface is the `fate_action` handler that bridges params→payload — no second classifier, no duplicate engine entry. ✓
- **Two channels, one engine:** the freeform path (`fate_action` subsystem) and F1d's explicit `FATE_ACTION` message both terminate in `dispatch_fate_action`. ✓
- **OTEL (spec §6, server CLAUDE.md):** `fate.action.classified` added + routed (Task 1); the exchange/engagement spans (F1) fire through the real path (Task 5 asserts `fate.exchange.resolved`); the precondition skip emits `intent_router.dispatch.gated` (Task 4). The GM panel can confirm a Fate action was engaged from language. ✓
- **No Silent Fallbacks:** invalid `action` → `ValueError` (bank error span); non-Fate ruleset / no conflict / unseated actor → `FateConflictError` surfaced as `data["error"]`; the precondition gate's drop is loud, not silent — Task 2/4. ✓
- **Conditional vocabulary:** the `fate` state-summary block is gated on `pack.rules.ruleset == "fate"` (Task 3) and the routing rules are behaviorally conditional ("only when a `fate` block is present"), so no non-Fate pack emits a `fate_action` — Task 3 enrichment test asserts the block is absent for a native pack. ✓
- **Wiring tests are behavior/OTEL, not source greps:** runtime `get_registered()` membership + an end-to-end bank drive asserting span emission + encounter state change — Task 5. ✓
- **In-conflict scope is explicit, not silent:** the precondition gate drops out-of-conflict `fate_action`s and the epic doc §7.1 flags the out-of-conflict overcome as a named follow-up — Task 4. ✓
- **Placeholder scan:** none — every code/command step is concrete. The single "confirm the `_SYSTEM_PROMPT` assembly shape" note (Task 3 Step 5) points the implementer at the real symbol to splice into (the same style as the F1d plan's resolver-name note), with the full `FATE_ROUTING_RULES` content given.
- **Type consistency:** `run_fate_action_dispatch`, `fate_action_classified_span`, `_build_fate_summary`, `_fate_action_precondition_unmet`, the `fate_action` subsystem key, and the `dispatch.params` keys (`action`/`skill`/`target`/`difficulty`/`invoke_aspect`/`aspect_text`) are named identically across tasks and match `FateActionPayload` (`protocol/fate.py`) and `dispatch_fate_action` (F1d). ✓
- **Out of F2a scope (correct):** aspects-as-prompt + invoke + compel (F2b), create-advantage rendering + honesty watcher (F2c), opponent AI (F2d), out-of-conflict overcome (§7.1 follow-up).
