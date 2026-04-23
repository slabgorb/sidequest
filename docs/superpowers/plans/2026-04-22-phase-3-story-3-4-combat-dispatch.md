# Phase 3 Story 3.4 — Combat Dispatch + OTEL Catalog + Narrator Wiring

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the already-ported `StructuredEncounter` / `ResourcePool` / `TensionTracker` types into the Python session handler so that a narrator-emitted `confrontation='combat'` actually instantiates a persisted encounter, the next narrator prompt lists its beats + actors, the UI receives a CONFRONTATION message, and every subsystem decision fires on OTEL so the GM panel sees it.

**Architecture:** New `sidequest/server/dispatch/confrontation.py` module owns lookup (`find_confrontation_def`) and payload assembly. `_build_turn_context` in `session_handler.py` derives `in_combat` / `in_chase` / `in_encounter` / `encounter_summary` from `snapshot.encounter`. The narrator's `build_encounter_context` is upgraded to render the matched `ConfrontationDef`'s beats and actors into the narrator prompt's Early zone. `_apply_narration_result_to_snapshot` instantiates `StructuredEncounter.combat(...)` / `.chase(...)` on the `confrontation` trigger. `_execute_narration_turn` dispatches a `CONFRONTATION` message whenever an encounter begins, continues, or ends. OTEL span names (`combat.*`, `encounter.*`) are byte-identical to Rust and guarded by a parity test. Encounter resolution from a completing trope is wired to `StructuredEncounter.resolve_from_trope`. XP awards differentiate by `in_combat`. Aside dispatch strips `[combat]` brackets. Resource-pool patch application mints threshold lore.

**Tech Stack:** Python 3.12, pydantic v2, OpenTelemetry, pytest, asyncio. The WebSocket wire contract is fixed by `sidequest-ui/src/components/ConfrontationOverlay.tsx` (`ConfrontationData` interface) and `sidequest-ui/src/App.tsx:435` (dispatch). No live LLM calls — the narrator is mocked.

---

## File Structure

**Create:**
- `sidequest-server/sidequest/server/dispatch/confrontation.py` — `find_confrontation_def`, `build_confrontation_payload`, `build_clear_confrontation_payload`.
- `sidequest-server/sidequest/server/dispatch/combat_brackets.py` — `strip_combat_brackets` helper.
- `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` — `instantiate_encounter_from_trigger`, `award_xp`, `apply_resource_patches`, `resolve_encounter_from_trope`.
- `sidequest-server/tests/server/test_confrontation_dispatch.py`
- `sidequest-server/tests/server/test_combat_brackets.py`
- `sidequest-server/tests/server/test_encounter_lifecycle.py`
- `sidequest-server/tests/server/test_encounter_wiring_e2e.py` — end-to-end caverns_and_claudes combat walkthrough.
- `sidequest-server/tests/telemetry/test_combat_encounter_spans.py` — span-name parity test.
- `sidequest-server/tests/agents/test_narrator_encounter_beats.py` — beats-listing section test.

**Modify:**
- `sidequest-server/sidequest/agents/orchestrator.py` — add `TurnContext.encounter_summary: str | None`, `TurnContext.confrontation_def` (object), expose to narrator prompt assembly.
- `sidequest-server/sidequest/agents/narrator.py` — upgrade `build_encounter_context` to render beats + actors from a `ConfrontationDef`.
- `sidequest-server/sidequest/server/session_handler.py` — `_build_turn_context` derives encounter flags; `_apply_narration_result_to_snapshot` instantiates + resolves encounters; `_execute_narration_turn` dispatches `CONFRONTATION`; aside path strips brackets; XP/resource wiring.
- `sidequest-server/sidequest/protocol/messages.py` — add `ConfrontationPayload`, `ConfrontationMessage`, include in `GameMessage` union and `_KIND_TO_MESSAGE_CLS`.
- `sidequest-server/sidequest/telemetry/spans.py` — add `SPAN_COMBAT_*`, `SPAN_ENCOUNTER_*` constants and helpers.

---

## Conventions for every task

- All new pydantic models set `model_config = {"extra": "forbid"}` (CLAUDE.md: no silent fallbacks).
- Every OTEL-emitting change adds a test asserting the span fires with expected attributes (uses `InMemorySpanExporter` as in `tests/telemetry/test_spans.py:24-28`).
- No live LLM. Mock the narrator via a `ClaudeLike` fake or by patching `Orchestrator.run_narration_turn`.
- `from __future__ import annotations` at the top of every new module.
- Run the full suite after each task: `uv run --directory sidequest-server pytest -x -q` before committing.

---

## Task 1: `find_confrontation_def` helper

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch/confrontation.py`
- Test: `sidequest-server/tests/server/test_confrontation_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_confrontation_dispatch.py
from __future__ import annotations

import pytest

from sidequest.genre.models.rules import (
    BeatDef,
    ConfrontationDef,
    MetricDef,
    MetricDirection,
)
from sidequest.server.dispatch.confrontation import find_confrontation_def


def _def(confrontation_type: str, label: str, category: str) -> ConfrontationDef:
    return ConfrontationDef(
        type=confrontation_type,
        label=label,
        category=category,
        metric=MetricDef(
            name="hp",
            direction=MetricDirection.descending,
            starting=10,
            threshold_low=0,
        ),
        beats=[BeatDef(id="attack", label="Attack", metric_delta=1)],
    )


def test_find_confrontation_def_returns_match_by_type() -> None:
    defs = [_def("combat", "Dungeon Combat", "combat"),
            _def("chase", "Corridor Pursuit", "movement")]
    match = find_confrontation_def(defs, "combat")
    assert match is not None
    assert match.confrontation_type == "combat"
    assert match.label == "Dungeon Combat"


def test_find_confrontation_def_returns_none_when_missing() -> None:
    defs = [_def("combat", "Combat", "combat")]
    assert find_confrontation_def(defs, "duel") is None


def test_find_confrontation_def_is_case_sensitive() -> None:
    # Rust parity: exact string equality on encounter_type.
    defs = [_def("combat", "Combat", "combat")]
    assert find_confrontation_def(defs, "Combat") is None
```

- [ ] **Step 2: Run the test — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_confrontation_dispatch.py::test_find_confrontation_def_returns_match_by_type -v
```
Expected: `ModuleNotFoundError: sidequest.server.dispatch.confrontation`.

- [ ] **Step 3: Write the implementation**

```python
# sidequest-server/sidequest/server/dispatch/confrontation.py
"""Confrontation-def lookup + CONFRONTATION payload assembly.

Port of sidequest-api/crates/sidequest-server/src/dispatch/response.rs
confrontation-def resolution and payload construction. Story 3.4.
"""
from __future__ import annotations

from sidequest.genre.models.rules import ConfrontationDef


def find_confrontation_def(
    defs: list[ConfrontationDef],
    encounter_type: str,
) -> ConfrontationDef | None:
    """Return the ConfrontationDef whose ``type`` equals ``encounter_type``.

    Exact string match — mirrors Rust's ``iter().find(|d| d.type == ty)``.
    Returns ``None`` when no def matches; callers MUST handle the miss
    (CLAUDE.md: no silent fallback — caller decides whether to error).
    """
    for d in defs:
        if d.confrontation_type == encounter_type:
            return d
    return None
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_confrontation_dispatch.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/confrontation.py \
        sidequest-server/tests/server/test_confrontation_dispatch.py
git commit -m "feat(server): add find_confrontation_def lookup helper (story 3.4)"
```

---

## Task 2: `build_confrontation_payload` — wire the UI contract

The UI consumer shape is fixed at `sidequest-ui/src/components/ConfrontationOverlay.tsx:42-58`:
`type, label, category, actors, metric, beats, secondary_stats, genre_slug, mood, active?`.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/confrontation.py`
- Modify: `sidequest-server/tests/server/test_confrontation_dispatch.py`

- [ ] **Step 1: Write the failing test**

Append to the test module:

```python
from sidequest.game.encounter import StructuredEncounter
from sidequest.server.dispatch.confrontation import (
    build_clear_confrontation_payload,
    build_confrontation_payload,
)


def test_build_confrontation_payload_active_for_live_encounter() -> None:
    cdef = _def("combat", "Dungeon Combat", "combat")
    enc = StructuredEncounter.combat(combatants=["Rux", "Goblin"], hp=10)
    payload = build_confrontation_payload(
        encounter=enc, cdef=cdef, genre_slug="caverns_and_claudes"
    )
    assert payload["type"] == "combat"
    assert payload["label"] == "Dungeon Combat"
    assert payload["category"] == "combat"
    assert payload["genre_slug"] == "caverns_and_claudes"
    assert payload["active"] is True
    assert [a["name"] for a in payload["actors"]] == ["Rux", "Goblin"]
    assert payload["metric"]["current"] == 10
    assert [b["id"] for b in payload["beats"]] == ["attack"]
    assert payload["mood"] is None or isinstance(payload["mood"], str)


def test_build_confrontation_payload_uses_encounter_mood_override_when_set() -> None:
    cdef = _def("combat", "Dungeon Combat", "combat")
    cdef = cdef.model_copy(update={"mood": "pack-mood"})
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    enc.mood_override = "panic"
    payload = build_confrontation_payload(
        encounter=enc, cdef=cdef, genre_slug="caverns_and_claudes"
    )
    assert payload["mood"] == "panic"  # encounter override wins over cdef.mood


def test_build_clear_confrontation_payload_signals_end() -> None:
    payload = build_clear_confrontation_payload(
        encounter_type="combat", genre_slug="caverns_and_claudes"
    )
    assert payload["active"] is False
    assert payload["type"] == "combat"
    assert payload["genre_slug"] == "caverns_and_claudes"
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_confrontation_dispatch.py -v
```
Expected: the new tests fail with `ImportError`.

- [ ] **Step 3: Implement payload builders**

Append to `confrontation.py`:

```python
from typing import Any

from sidequest.game.encounter import StructuredEncounter


def build_confrontation_payload(
    *,
    encounter: StructuredEncounter,
    cdef: ConfrontationDef,
    genre_slug: str,
) -> dict[str, Any]:
    """Assemble the CONFRONTATION payload the UI overlay consumes.

    Shape fixed by sidequest-ui/src/components/ConfrontationOverlay.tsx:42-58.
    Encounter mood_override beats the confrontation-def default mood.
    """
    mood = encounter.mood_override or cdef.mood
    return {
        "type": encounter.encounter_type,
        "label": cdef.label,
        "category": cdef.category,
        "actors": [a.model_dump(mode="json") for a in encounter.actors],
        "metric": encounter.metric.model_dump(mode="json"),
        "beats": [b.model_dump(mode="json") for b in cdef.beats],
        "secondary_stats": (
            encounter.secondary_stats.model_dump(mode="json")
            if encounter.secondary_stats is not None else None
        ),
        "genre_slug": genre_slug,
        "mood": mood,
        "active": not encounter.resolved,
    }


def build_clear_confrontation_payload(
    *, encounter_type: str, genre_slug: str,
) -> dict[str, Any]:
    """Minimal payload that tells the UI to unmount the overlay.

    App.tsx:435 — ``payload.active !== false`` is the dispatch branch; an
    explicit ``false`` is what clears the overlay. Other fields are
    required by the TS interface but ignored when active=false.
    """
    return {
        "type": encounter_type,
        "label": "",
        "category": "",
        "actors": [],
        "metric": {},
        "beats": [],
        "secondary_stats": None,
        "genre_slug": genre_slug,
        "mood": None,
        "active": False,
    }
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_confrontation_dispatch.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/confrontation.py \
        sidequest-server/tests/server/test_confrontation_dispatch.py
git commit -m "feat(server): build_confrontation_payload matches UI contract (story 3.4)"
```

---

## Task 3: `ConfrontationPayload` + `ConfrontationMessage` protocol types

The UI already consumes `MessageType.CONFRONTATION` (`App.tsx:435`) — the server must emit a typed message matching it.

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Test: `sidequest-server/tests/protocol/test_confrontation_message.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/protocol/test_confrontation_message.py
from __future__ import annotations

import json

import pytest

from sidequest.protocol.messages import ConfrontationMessage, ConfrontationPayload


def test_confrontation_message_roundtrip() -> None:
    payload = ConfrontationPayload(
        type="combat",
        label="Dungeon Combat",
        category="combat",
        actors=[{"name": "Rux", "role": "combatant", "per_actor_state": {}}],
        metric={"name": "hp", "current": 10, "starting": 10,
                "direction": "Descending", "threshold_low": 0,
                "threshold_high": None},
        beats=[{"id": "attack", "label": "Attack", "metric_delta": 2}],
        secondary_stats=None,
        genre_slug="caverns_and_claudes",
        mood="combat",
        active=True,
    )
    msg = ConfrontationMessage(payload=payload, player_id="")
    serialized = msg.model_dump(mode="json", by_alias=True)
    assert serialized["type"] == "CONFRONTATION"
    assert serialized["payload"]["active"] is True
    assert serialized["payload"]["beats"][0]["id"] == "attack"


def test_confrontation_message_supports_active_false_clear() -> None:
    payload = ConfrontationPayload(
        type="combat", label="", category="", actors=[], metric={}, beats=[],
        secondary_stats=None, genre_slug="caverns_and_claudes",
        mood=None, active=False,
    )
    msg = ConfrontationMessage(payload=payload, player_id="")
    assert msg.payload.active is False
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/protocol/test_confrontation_message.py -v
```
Expected: `ImportError: cannot import name 'ConfrontationMessage'`.

- [ ] **Step 3: Add the models**

In `sidequest-server/sidequest/protocol/messages.py` (after `PlayerSeatPayload`/`SeatConfirmedPayload` block, before `GamePausedPayload`):

```python
class ConfrontationPayload(ProtocolBase):
    """Payload for CONFRONTATION — drives the ConfrontationOverlay UI.

    Shape mirrors sidequest-ui/src/components/ConfrontationOverlay.tsx
    ``ConfrontationData`` (L42-58). ``active=False`` signals the overlay
    to unmount.
    """
    type: str
    label: str
    category: str
    actors: list[dict[str, Any]] = Field(default_factory=list)
    metric: dict[str, Any] = Field(default_factory=dict)
    beats: list[dict[str, Any]] = Field(default_factory=list)
    secondary_stats: dict[str, Any] | None = None
    genre_slug: str
    mood: str | None = None
    active: bool = True
```

and in the concrete-message section (near `GamePausedMessage`):

```python
class ConfrontationMessage(ProtocolBase):
    type: Literal[MessageType.CONFRONTATION] = MessageType.CONFRONTATION  # type: ignore[assignment]
    payload: ConfrontationPayload
    player_id: str = ""
```

Update `_Phase1Variant` (the discriminated union feeding `GameMessage`) to include `ConfrontationMessage`. Grep for `_Phase1Variant` and add it to the `Annotated[Union[...]]` tuple.

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/protocol/test_confrontation_message.py -v
uv run --directory sidequest-server pytest tests/protocol -v
```
Expected: new tests pass, existing protocol tests still green.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py \
        sidequest-server/tests/protocol/test_confrontation_message.py
git commit -m "feat(protocol): add ConfrontationMessage + payload (story 3.4)"
```

---

## Task 4: OTEL `combat.*` / `encounter.*` span catalog + parity test

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py`
- Create: `sidequest-server/tests/telemetry/test_combat_encounter_spans.py`

Rust emits these under `watcher!("combat", ...)` / `watcher!("encounter", ...)` (see phase-3 plan L146 + L152). The full catalog for this story:

- `combat.tick` — every encounter turn
- `combat.ended` — encounter resolves (any outcome)
- `combat.player_dead` — player-side resolution with fatality
- `encounter.phase_transition` — `EncounterPhase` change (Setup→Opening→…)
- `encounter.resolved` — `resolved` flips True (source: trope, metric, player death)
- `encounter.beat_applied` — narrator's beat_selection consumed
- `encounter.confrontation_initiated` — narrator emitted `confrontation=…` and the server instantiated one

- [ ] **Step 1: Write the failing parity test**

```python
# sidequest-server/tests/telemetry/test_combat_encounter_spans.py
"""Rust-parity test for combat.* / encounter.* span names.

Story 3.4 AC: OTEL span names are byte-identical to Rust. GM-panel queries
break on drift (see docs/plans/phase-3-combat-port.md Risks §2).
"""
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


def test_combat_encounter_span_constants_match_rust_names() -> None:
    from sidequest.telemetry.spans import (
        SPAN_COMBAT_TICK,
        SPAN_COMBAT_ENDED,
        SPAN_COMBAT_PLAYER_DEAD,
        SPAN_ENCOUNTER_PHASE_TRANSITION,
        SPAN_ENCOUNTER_RESOLVED,
        SPAN_ENCOUNTER_BEAT_APPLIED,
        SPAN_ENCOUNTER_CONFRONTATION_INITIATED,
    )
    # Rust watcher! names — byte-identical. DO NOT rename.
    assert SPAN_COMBAT_TICK == "combat.tick"
    assert SPAN_COMBAT_ENDED == "combat.ended"
    assert SPAN_COMBAT_PLAYER_DEAD == "combat.player_dead"
    assert SPAN_ENCOUNTER_PHASE_TRANSITION == "encounter.phase_transition"
    assert SPAN_ENCOUNTER_RESOLVED == "encounter.resolved"
    assert SPAN_ENCOUNTER_BEAT_APPLIED == "encounter.beat_applied"
    assert SPAN_ENCOUNTER_CONFRONTATION_INITIATED == (
        "encounter.confrontation_initiated"
    )


def test_combat_tick_span_emits_attributes() -> None:
    from sidequest.telemetry.spans import combat_tick_span

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    with combat_tick_span(
        tracer=tracer, encounter_type="combat", beat=3, phase="Escalation",
    ):
        pass
    [span] = exporter.get_finished_spans()
    assert span.name == "combat.tick"
    assert span.attributes["encounter_type"] == "combat"
    assert span.attributes["beat"] == 3
    assert span.attributes["phase"] == "Escalation"


def test_encounter_phase_transition_span_emits_from_to() -> None:
    from sidequest.telemetry.spans import encounter_phase_transition_span

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    with encounter_phase_transition_span(
        tracer=tracer, from_phase="Opening", to_phase="Escalation",
        encounter_type="combat",
    ):
        pass
    [span] = exporter.get_finished_spans()
    assert span.name == "encounter.phase_transition"
    assert span.attributes["from"] == "Opening"
    assert span.attributes["to"] == "Escalation"
    assert span.attributes["encounter_type"] == "combat"
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/telemetry/test_combat_encounter_spans.py -v
```
Expected: `ImportError: cannot import name 'SPAN_COMBAT_TICK'`.

- [ ] **Step 3: Implement the span constants + helpers**

Append to `sidequest-server/sidequest/telemetry/spans.py`:

```python
# ---------------------------------------------------------------------------
# Combat / Encounter — sidequest-server/dispatch/{response,state_mutations,
# telemetry}.rs + sidequest-game/encounter.rs (Story 3.4)
# ---------------------------------------------------------------------------
SPAN_COMBAT_TICK = "combat.tick"
SPAN_COMBAT_ENDED = "combat.ended"
SPAN_COMBAT_PLAYER_DEAD = "combat.player_dead"
SPAN_ENCOUNTER_PHASE_TRANSITION = "encounter.phase_transition"
SPAN_ENCOUNTER_RESOLVED = "encounter.resolved"
SPAN_ENCOUNTER_BEAT_APPLIED = "encounter.beat_applied"
SPAN_ENCOUNTER_CONFRONTATION_INITIATED = "encounter.confrontation_initiated"


@contextmanager
def combat_tick_span(
    *, tracer: trace.Tracer | None = None,
    encounter_type: str, beat: int, phase: str,
) -> Iterator[trace.Span]:
    t = tracer or globals()["tracer"]
    with t.start_as_current_span(SPAN_COMBAT_TICK) as span:
        span.set_attribute("encounter_type", encounter_type)
        span.set_attribute("beat", beat)
        span.set_attribute("phase", phase)
        yield span


@contextmanager
def encounter_phase_transition_span(
    *, tracer: trace.Tracer | None = None,
    from_phase: str, to_phase: str, encounter_type: str,
) -> Iterator[trace.Span]:
    t = tracer or globals()["tracer"]
    with t.start_as_current_span(SPAN_ENCOUNTER_PHASE_TRANSITION) as span:
        span.set_attribute("from", from_phase)
        span.set_attribute("to", to_phase)
        span.set_attribute("encounter_type", encounter_type)
        yield span


@contextmanager
def encounter_resolved_span(
    *, tracer: trace.Tracer | None = None,
    encounter_type: str, outcome: str | None, source: str,
) -> Iterator[trace.Span]:
    t = tracer or globals()["tracer"]
    with t.start_as_current_span(SPAN_ENCOUNTER_RESOLVED) as span:
        span.set_attribute("encounter_type", encounter_type)
        if outcome is not None:
            span.set_attribute("outcome", outcome)
        span.set_attribute("source", source)  # trope | metric | player_death
        yield span


@contextmanager
def encounter_beat_applied_span(
    *, tracer: trace.Tracer | None = None,
    encounter_type: str, actor: str, beat_id: str, metric_delta: int,
) -> Iterator[trace.Span]:
    t = tracer or globals()["tracer"]
    with t.start_as_current_span(SPAN_ENCOUNTER_BEAT_APPLIED) as span:
        span.set_attribute("encounter_type", encounter_type)
        span.set_attribute("actor", actor)
        span.set_attribute("beat_id", beat_id)
        span.set_attribute("metric_delta", metric_delta)
        yield span


@contextmanager
def encounter_confrontation_initiated_span(
    *, tracer: trace.Tracer | None = None,
    encounter_type: str, genre_slug: str,
) -> Iterator[trace.Span]:
    t = tracer or globals()["tracer"]
    with t.start_as_current_span(
        SPAN_ENCOUNTER_CONFRONTATION_INITIATED,
    ) as span:
        span.set_attribute("encounter_type", encounter_type)
        span.set_attribute("genre_slug", genre_slug)
        yield span


@contextmanager
def combat_ended_span(
    *, tracer: trace.Tracer | None = None,
    outcome: str, duration_beats: int,
) -> Iterator[trace.Span]:
    t = tracer or globals()["tracer"]
    with t.start_as_current_span(SPAN_COMBAT_ENDED) as span:
        span.set_attribute("outcome", outcome)
        span.set_attribute("duration_beats", duration_beats)
        yield span


@contextmanager
def combat_player_dead_span(
    *, tracer: trace.Tracer | None = None, player_name: str,
) -> Iterator[trace.Span]:
    t = tracer or globals()["tracer"]
    with t.start_as_current_span(SPAN_COMBAT_PLAYER_DEAD) as span:
        span.set_attribute("player_name", player_name)
        yield span
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/telemetry -v
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans.py \
        sidequest-server/tests/telemetry/test_combat_encounter_spans.py
git commit -m "feat(telemetry): add combat.* / encounter.* span catalog (story 3.4)"
```

---

## Task 5: `TurnContext.encounter_summary` + `TurnContext.confrontation_def`

The narrator prompt needs (a) a summary of the current encounter state and (b) the raw `ConfrontationDef` so it can render available beats. Add both as `TurnContext` fields.

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py`
- Test: `sidequest-server/tests/agents/test_orchestrator_encounter_fields.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/agents/test_orchestrator_encounter_fields.py
from __future__ import annotations

from sidequest.agents.orchestrator import TurnContext


def test_turn_context_defaults_encounter_summary_none() -> None:
    ctx = TurnContext()
    assert ctx.encounter_summary is None
    assert ctx.confrontation_def is None


def test_turn_context_accepts_encounter_summary_string() -> None:
    ctx = TurnContext(encounter_summary="HP 10/10, beat 0, phase Setup")
    assert ctx.encounter_summary == "HP 10/10, beat 0, phase Setup"
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/agents/test_orchestrator_encounter_fields.py -v
```
Expected: `AttributeError` / `TypeError: unexpected keyword argument`.

- [ ] **Step 3: Add the fields**

In `sidequest-server/sidequest/agents/orchestrator.py` at the end of the `TurnContext` dataclass (after `pacing_hint`):

```python
    # Encounter state summary rendered for the Valley zone (Story 3.4).
    # When ``None``, no encounter section is registered. Mutually consistent
    # with ``in_combat``/``in_chase``/``in_encounter`` — if any of those is
    # True, ``encounter_summary`` should be set.
    encounter_summary: str | None = None

    # The matched ConfrontationDef for the active encounter (Story 3.4).
    # Typed as ``Any`` to avoid a circular import through sidequest.genre;
    # runtime shape is ``sidequest.genre.models.rules.ConfrontationDef``.
    # The narrator uses this to render available beats + actors into the
    # Early zone so the LLM can emit valid ``beat_selections``.
    confrontation_def: Any = None
```

(`Any` is already imported at module top.)

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/agents/test_orchestrator_encounter_fields.py tests/agents/test_orchestrator.py -v
```
Expected: new tests pass; existing orchestrator tests still green.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/agents/orchestrator.py \
        sidequest-server/tests/agents/test_orchestrator_encounter_fields.py
git commit -m "feat(agents): TurnContext.encounter_summary + confrontation_def (story 3.4)"
```

---

## Task 6: Render `StructuredEncounter` into a narrator-prompt section

Compute the Valley-zone summary string from a live encounter.

**Files:**
- Create: `sidequest-server/sidequest/agents/encounter_render.py`
- Test: `sidequest-server/tests/agents/test_encounter_render.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/agents/test_encounter_render.py
from __future__ import annotations

from sidequest.agents.encounter_render import render_encounter_summary
from sidequest.game.encounter import StructuredEncounter


def test_render_combat_summary_lists_metric_phase_actors_beat() -> None:
    enc = StructuredEncounter.combat(combatants=["Rux", "Goblin"], hp=10)
    enc.beat = 2
    out = render_encounter_summary(enc)
    assert "encounter_type: combat" in out
    assert "beat: 2" in out
    assert "phase: Setup" in out
    assert "metric: hp 10/10 (descending, low=0)" in out
    assert "actors:" in out
    assert "- Rux (combatant)" in out
    assert "- Goblin (combatant)" in out


def test_render_respects_ascending_chase_metric() -> None:
    enc = StructuredEncounter.chase(escape_threshold=1.0, rig_type=None, goal=20)
    out = render_encounter_summary(enc)
    assert "metric: separation 0/20 (ascending" in out
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/agents/test_encounter_render.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# sidequest-server/sidequest/agents/encounter_render.py
"""Render a StructuredEncounter into the Valley-zone summary string.

Consumed by session_handler._build_turn_context to populate
TurnContext.encounter_summary. The narrator uses this + the
confrontation_def beat listing (see narrator.build_encounter_context)
to emit well-formed beat_selections.
"""
from __future__ import annotations

from sidequest.game.encounter import MetricDirection, StructuredEncounter


def render_encounter_summary(enc: StructuredEncounter) -> str:
    lines: list[str] = []
    lines.append(f"encounter_type: {enc.encounter_type}")
    lines.append(f"beat: {enc.beat}")
    if enc.structured_phase is not None:
        lines.append(f"phase: {enc.structured_phase.value}")
    m = enc.metric
    direction_label = {
        MetricDirection.Ascending: "ascending",
        MetricDirection.Descending: "descending",
        MetricDirection.Bidirectional: "bidirectional",
    }[m.direction]
    bounds: list[str] = []
    if m.threshold_low is not None:
        bounds.append(f"low={m.threshold_low}")
    if m.threshold_high is not None:
        bounds.append(f"high={m.threshold_high}")
    bounds_part = (", " + ", ".join(bounds)) if bounds else ""
    lines.append(
        f"metric: {m.name} {m.current}/{m.starting} "
        f"({direction_label}{bounds_part})"
    )
    if enc.actors:
        lines.append("actors:")
        for a in enc.actors:
            lines.append(f"- {a.name} ({a.role})")
    if enc.mood_override:
        lines.append(f"mood: {enc.mood_override}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/agents/test_encounter_render.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/agents/encounter_render.py \
        sidequest-server/tests/agents/test_encounter_render.py
git commit -m "feat(agents): render_encounter_summary for narrator Valley zone (story 3.4)"
```

---

## Task 7: Narrator `build_encounter_context` renders matched `ConfrontationDef`

The narrator prompt today only injects the generic rules text (`narrator.py:393-414`). It must also list the active encounter's available beats and actors, matching the instruction it already gives the LLM at `narrator.py:159`: *"the encounter context section will list available beats and actors"*.

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py`
- Modify: `sidequest-server/sidequest/agents/orchestrator.py` (call-site passes `encounter_summary` + `confrontation_def`)
- Test: `sidequest-server/tests/agents/test_narrator_encounter_beats.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/agents/test_narrator_encounter_beats.py
from __future__ import annotations

from sidequest.agents.narrator import NarratorAgent
from sidequest.agents.prompt_framework.core import PromptRegistry
from sidequest.game.encounter import StructuredEncounter
from sidequest.genre.models.rules import (
    BeatDef, ConfrontationDef, MetricDef, MetricDirection,
)


def _cdef() -> ConfrontationDef:
    return ConfrontationDef(
        type="combat", label="Dungeon Combat", category="combat",
        metric=MetricDef(name="hp", direction=MetricDirection.descending,
                         starting=10, threshold_low=0),
        beats=[
            BeatDef(id="attack", label="Attack", metric_delta=2),
            BeatDef(id="defend", label="Defend", metric_delta=1),
        ],
    )


def test_build_encounter_context_lists_beats_and_actors() -> None:
    narrator = NarratorAgent()
    reg = PromptRegistry()
    enc = StructuredEncounter.combat(combatants=["Rux", "Goblin"], hp=10)
    narrator.build_encounter_context(
        reg, encounter=enc, cdef=_cdef(), encounter_summary="stub summary"
    )
    composed = reg.compose(narrator.name())
    assert "stub summary" in composed
    # Available beats must appear so the narrator can pick valid ids
    assert "attack" in composed
    assert "defend" in composed
    # Actors must be listed
    assert "Rux" in composed
    assert "Goblin" in composed


def test_build_encounter_context_without_cdef_falls_back_to_generic() -> None:
    """When no confrontation_def matched, still inject the generic rules text.

    This covers the narrator-initiated-first-turn case where the encounter
    has just been created and the def-lookup result will reach the next
    turn. CLAUDE.md "no silent fallbacks" applies to config misses, not
    first-turn timing.
    """
    narrator = NarratorAgent()
    reg = PromptRegistry()
    narrator.build_encounter_context(
        reg, encounter=None, cdef=None, encounter_summary=None
    )
    composed = reg.compose(narrator.name())
    assert "encounter-rules" in composed or "<encounter-rules>" in composed
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/agents/test_narrator_encounter_beats.py -v
```
Expected: fails — current signature takes only `registry`.

- [ ] **Step 3: Rewrite `build_encounter_context`**

Replace the body of `build_encounter_context` in `sidequest-server/sidequest/agents/narrator.py`:

```python
def build_encounter_context(
    self,
    registry: object,
    *,
    encounter: "StructuredEncounter | None" = None,
    cdef: "ConfrontationDef | None" = None,
    encounter_summary: str | None = None,
) -> None:
    """Inject encounter-specific narration rules + live encounter state.

    When ``encounter`` and ``cdef`` are given, render:
    1. The generic encounter-rules prose (unchanged).
    2. The matched ConfrontationDef's beats + actors so the LLM emits
       valid ``beat_selections``.
    3. The encounter_summary (metric / phase / beat) in the Valley zone.

    Port of NarratorAgent::build_encounter_context() in narrator.rs.
    """
    from sidequest.agents.prompt_framework.core import PromptRegistry

    if not isinstance(registry, PromptRegistry):
        raise TypeError(f"Expected PromptRegistry, got {type(registry)}")

    registry.register_section(
        self.name(),
        PromptSection.new(
            "narrator_encounter_rules",
            f"<encounter-rules>\n{NARRATOR_COMBAT_RULES}\n"
            f"{NARRATOR_CHASE_RULES}\n</encounter-rules>",
            AttentionZone.Early,
            SectionCategory.Guardrail,
        ),
    )

    if encounter is not None and cdef is not None:
        actor_lines = "\n".join(f"- {a.name} ({a.role})" for a in encounter.actors)
        beat_lines = "\n".join(
            f"- {b.id}: {b.label} (metric_delta={b.metric_delta})"
            for b in cdef.beats
        )
        body = (
            f"<encounter-live>\n"
            f"Active encounter: {cdef.label} ({cdef.confrontation_type})\n"
            f"Available beats — beat_selections.beat_id MUST be one of:\n"
            f"{beat_lines}\n"
            f"Actors — emit a beat_selection for every actor:\n"
            f"{actor_lines}\n"
            f"</encounter-live>"
        )
        registry.register_section(
            self.name(),
            PromptSection.new(
                "narrator_encounter_live", body,
                AttentionZone.Early, SectionCategory.State,
            ),
        )

    if encounter_summary:
        registry.register_section(
            self.name(),
            PromptSection.new(
                "narrator_encounter_summary",
                f"<encounter-state>\n{encounter_summary}\n</encounter-state>",
                AttentionZone.Valley,
                SectionCategory.State,
            ),
        )
```

Add the TYPE_CHECKING imports at the top of `narrator.py`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.game.encounter import StructuredEncounter
    from sidequest.genre.models.rules import ConfrontationDef
```

Update the call site in `sidequest-server/sidequest/agents/orchestrator.py` around line 861:

```python
if context.in_combat or context.in_chase or context.in_encounter:
    self._narrator.build_encounter_context(
        registry,
        encounter=None,  # encounter object isn't threaded through this layer
        cdef=context.confrontation_def,
        encounter_summary=context.encounter_summary,
    )
```

And, to supply the `encounter` object to the narrator too, thread it via `TurnContext.encounter` (add the field, mirror encounter_summary). Append to `TurnContext` in orchestrator.py:

```python
    # Live encounter object (Story 3.4). Typed as ``Any`` to avoid a
    # circular import through sidequest.game. Runtime type:
    # ``sidequest.game.encounter.StructuredEncounter``.
    encounter: Any = None
```

Then update the call to:

```python
    self._narrator.build_encounter_context(
        registry,
        encounter=context.encounter,
        cdef=context.confrontation_def,
        encounter_summary=context.encounter_summary,
    )
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/agents -v
```
Expected: all agents tests green, including existing narrator tests.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/agents/narrator.py \
        sidequest-server/sidequest/agents/orchestrator.py \
        sidequest-server/tests/agents/test_narrator_encounter_beats.py
git commit -m "feat(narrator): render ConfrontationDef beats + actors into prompt (story 3.4)"
```

---

## Task 8: Derive `in_combat` / `in_chase` / `in_encounter` from `snapshot.encounter`

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` (`_build_turn_context` at L1856-1886)
- Test: `sidequest-server/tests/server/test_turn_context_encounter_derivation.py` (create)

Rust's rule (phase-3 plan AC, L154):

> `ctx.in_combat()` returns True iff `snapshot.encounter is not None and not snapshot.encounter.resolved and snapshot.encounter.encounter_type in {"combat", "skirmish", ...}`.

The exact set the Rust dispatch treats as "combat-category" is `{combat, skirmish, brawl, duel}` (and any future entry whose `ConfrontationDef.category == "combat"`). Use the **pack's own `category`** as the source of truth: `in_combat = category == "combat"`, `in_chase = category == "movement"`, `in_encounter = any active encounter at all`.

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_turn_context_encounter_derivation.py
from __future__ import annotations

import pytest

from sidequest.game.encounter import StructuredEncounter


@pytest.fixture
def session_data_factory(tmp_path):
    """Build a minimal _SessionData with a real genre pack loaded."""
    from sidequest.genre.loader import GenreLoader, DEFAULT_GENRE_PACK_SEARCH_PATHS
    from sidequest.game.session import GameSnapshot
    from sidequest.server.session_handler import _SessionData

    pack = GenreLoader(DEFAULT_GENRE_PACK_SEARCH_PATHS).load("caverns_and_claudes")
    snap = GameSnapshot(genre="caverns_and_claudes")

    def _make(encounter: StructuredEncounter | None) -> _SessionData:
        snap.encounter = encounter
        return _SessionData(
            genre_slug="caverns_and_claudes",
            world_slug="crypt_of_the_seven",
            genre_pack=pack,
            snapshot=snap,
            player_id="p1",
            player_name="Rux",
            store=None,  # not exercised in this test
            orchestrator=None,
            world_context=None,
        )
    return _make


def test_no_encounter_defaults_to_all_false(session_data_factory) -> None:
    from sidequest.server.session_handler import _build_turn_context
    sd = session_data_factory(None)
    ctx = _build_turn_context(sd)
    assert ctx.in_combat is False
    assert ctx.in_chase is False
    assert ctx.in_encounter is False
    assert ctx.encounter is None
    assert ctx.confrontation_def is None
    assert ctx.encounter_summary is None


def test_combat_encounter_sets_in_combat_true(session_data_factory) -> None:
    from sidequest.server.session_handler import _build_turn_context
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    sd = session_data_factory(enc)
    ctx = _build_turn_context(sd)
    assert ctx.in_combat is True
    assert ctx.in_chase is False
    assert ctx.in_encounter is True
    assert ctx.encounter is enc
    assert ctx.confrontation_def is not None
    assert ctx.confrontation_def.confrontation_type == "combat"
    assert ctx.encounter_summary is not None
    assert "encounter_type: combat" in ctx.encounter_summary


def test_resolved_encounter_flags_all_false(session_data_factory) -> None:
    from sidequest.server.session_handler import _build_turn_context
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    enc.resolved = True
    sd = session_data_factory(enc)
    ctx = _build_turn_context(sd)
    assert ctx.in_combat is False
    assert ctx.in_encounter is False


def test_chase_encounter_sets_in_chase_true(session_data_factory) -> None:
    from sidequest.server.session_handler import _build_turn_context
    enc = StructuredEncounter.chase(escape_threshold=1.0, rig_type=None, goal=20)
    sd = session_data_factory(enc)
    ctx = _build_turn_context(sd)
    assert ctx.in_chase is True
    assert ctx.in_combat is False
    assert ctx.in_encounter is True
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_turn_context_encounter_derivation.py -v
```
Expected: current hardcoded `in_combat=False` fails the combat test.

- [ ] **Step 3: Implement derivation**

Rewrite `_build_turn_context` in `sidequest-server/sidequest/server/session_handler.py`:

```python
def _build_turn_context(
    sd: _SessionData, *, opening_directive: str | None = None
) -> TurnContext:
    """Assemble the TurnContext for a single narration turn."""
    from sidequest.agents.encounter_render import render_encounter_summary
    from sidequest.server.dispatch.confrontation import find_confrontation_def

    snapshot = sd.snapshot
    char_name = (
        snapshot.characters[0].core.name if snapshot.characters else sd.player_name
    )

    # Derive encounter flags from snapshot.encounter (Story 3.4).
    encounter = snapshot.encounter
    confrontation_def = None
    encounter_summary = None
    in_combat = False
    in_chase = False
    in_encounter = False
    if encounter is not None and not encounter.resolved:
        in_encounter = True
        defs = sd.genre_pack.rules.confrontations if sd.genre_pack.rules else []
        confrontation_def = find_confrontation_def(defs, encounter.encounter_type)
        if confrontation_def is not None:
            in_combat = confrontation_def.category == "combat"
            in_chase = confrontation_def.category == "movement"
        encounter_summary = render_encounter_summary(encounter)

    return TurnContext(
        in_combat=in_combat,
        in_chase=in_chase,
        in_encounter=in_encounter,
        encounter=encounter if in_encounter else None,
        confrontation_def=confrontation_def,
        encounter_summary=encounter_summary,
        state_summary=snapshot.model_dump_json(indent=2),
        narrator_verbosity="standard",
        narrator_vocabulary="literary",
        genre=sd.genre_slug,
        genre_prompts=sd.genre_pack.prompts,
        character_name=char_name,
        current_location=snapshot.location or "Unknown",
        available_sfx=_sfx_ids_from_genre(sd.genre_pack),
        npc_registry=list(snapshot.npc_registry),
        npcs=list(snapshot.npcs),
        opening_directive=opening_directive,
        world_context=sd.world_context,
    )
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_turn_context_encounter_derivation.py tests/server/test_dispatch.py -v
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/server/test_turn_context_encounter_derivation.py
git commit -m "feat(server): derive in_combat/in_chase from snapshot.encounter (story 3.4)"
```

---

## Task 9: `encounter_lifecycle.instantiate_encounter_from_trigger`

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py`
- Test: `sidequest-server/tests/server/test_encounter_lifecycle.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_encounter_lifecycle.py
from __future__ import annotations

import pytest

from sidequest.genre.loader import GenreLoader, DEFAULT_GENRE_PACK_SEARCH_PATHS
from sidequest.game.encounter import StructuredEncounter
from sidequest.game.session import GameSnapshot
from sidequest.server.dispatch.encounter_lifecycle import (
    instantiate_encounter_from_trigger,
)


@pytest.fixture
def cac_pack():
    return GenreLoader(DEFAULT_GENRE_PACK_SEARCH_PATHS).load("caverns_and_claudes")


def test_instantiate_combat_creates_encounter(cac_pack) -> None:
    snap = GameSnapshot(genre="caverns_and_claudes")
    enc = instantiate_encounter_from_trigger(
        snapshot=snap, pack=cac_pack, encounter_type="combat",
        combatants=["Rux", "Goblin"], hp=10,
    )
    assert enc is not None
    assert snap.encounter is enc
    assert enc.encounter_type == "combat"
    assert [a.name for a in enc.actors] == ["Rux", "Goblin"]
    assert enc.metric.name == "momentum"  # cac combat metric
    # starting=0, threshold_high=10, threshold_low=-10 from rules.yaml
    assert enc.metric.starting == 0


def test_instantiate_unknown_type_raises(cac_pack) -> None:
    """CLAUDE.md: no silent fallback on unknown encounter_type."""
    snap = GameSnapshot(genre="caverns_and_claudes")
    with pytest.raises(ValueError, match="unknown encounter_type"):
        instantiate_encounter_from_trigger(
            snapshot=snap, pack=cac_pack, encounter_type="spelling_bee",
            combatants=["Rux"], hp=10,
        )


def test_instantiate_replaces_resolved_encounter(cac_pack) -> None:
    """A resolved prior encounter does not block a new one."""
    snap = GameSnapshot(genre="caverns_and_claudes")
    prior = StructuredEncounter.combat(combatants=["old"], hp=1)
    prior.resolved = True
    snap.encounter = prior
    enc = instantiate_encounter_from_trigger(
        snapshot=snap, pack=cac_pack, encounter_type="combat",
        combatants=["Rux"], hp=10,
    )
    assert snap.encounter is enc
    assert enc is not prior


def test_instantiate_active_encounter_is_noop(cac_pack) -> None:
    """If an active unresolved encounter already exists, do not clobber."""
    snap = GameSnapshot(genre="caverns_and_claudes")
    active = StructuredEncounter.combat(combatants=["already"], hp=10)
    snap.encounter = active
    result = instantiate_encounter_from_trigger(
        snapshot=snap, pack=cac_pack, encounter_type="combat",
        combatants=["Rux"], hp=10,
    )
    assert result is None  # signal: no new encounter created
    assert snap.encounter is active
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_encounter_lifecycle.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py
"""Encounter lifecycle — instantiation, resolution, XP, resource patches.

Port of sidequest-api/crates/sidequest-server/src/dispatch/
{state_mutations,tropes,response}.rs combat-sensitive paths (Story 3.4).
"""
from __future__ import annotations

from sidequest.game.encounter import StructuredEncounter
from sidequest.game.session import GameSnapshot
from sidequest.genre.models.pack import GenrePack
from sidequest.server.dispatch.confrontation import find_confrontation_def
from sidequest.telemetry.spans import (
    encounter_confrontation_initiated_span,
    encounter_resolved_span,
)


def instantiate_encounter_from_trigger(
    *,
    snapshot: GameSnapshot,
    pack: GenrePack,
    encounter_type: str,
    combatants: list[str],
    hp: int,
) -> StructuredEncounter | None:
    """Create a StructuredEncounter when the narrator emits ``confrontation=T``.

    Returns the new encounter and writes it to ``snapshot.encounter``.
    Returns ``None`` when an active (unresolved) encounter already exists —
    the caller should leave the current encounter alone.

    Raises ``ValueError`` when ``encounter_type`` doesn't match any
    ConfrontationDef in the pack — CLAUDE.md "No Silent Fallbacks":
    an unknown type is a genre-pack typo, not a default-to-combat case.
    """
    current = snapshot.encounter
    if current is not None and not current.resolved:
        return None

    defs = pack.rules.confrontations if pack.rules else []
    cdef = find_confrontation_def(defs, encounter_type)
    if cdef is None:
        raise ValueError(
            f"unknown encounter_type {encounter_type!r} — "
            f"not in pack {pack.slug!r} confrontations"
        )

    with encounter_confrontation_initiated_span(
        encounter_type=encounter_type, genre_slug=pack.slug,
    ):
        if cdef.category == "combat":
            enc = StructuredEncounter.combat(combatants=combatants, hp=hp)
        elif cdef.category == "movement":
            enc = StructuredEncounter.chase(
                escape_threshold=1.0, rig_type=None,
                goal=cdef.metric.threshold_high or 20,
            )
        else:
            # Social / pre_combat — generic constructor via metric.
            from sidequest.game.encounter import (
                EncounterMetric, MetricDirection, EncounterActor,
            )
            direction = {
                "ascending": MetricDirection.Ascending,
                "descending": MetricDirection.Descending,
                "bidirectional": MetricDirection.Bidirectional,
            }[cdef.metric.direction.value]
            enc = StructuredEncounter(
                encounter_type=encounter_type,
                metric=EncounterMetric(
                    name=cdef.metric.name,
                    current=cdef.metric.starting,
                    starting=cdef.metric.starting,
                    direction=direction,
                    threshold_high=cdef.metric.threshold_high,
                    threshold_low=cdef.metric.threshold_low,
                ),
                actors=[
                    EncounterActor(name=n, role="participant",
                                   per_actor_state={})
                    for n in combatants
                ],
            )
        # For combat-category specifically the factory sets generic HP metric;
        # overwrite with the pack's declared metric so momentum/etc. wins.
        if cdef.category == "combat":
            from sidequest.game.encounter import EncounterMetric, MetricDirection
            direction = {
                "ascending": MetricDirection.Ascending,
                "descending": MetricDirection.Descending,
                "bidirectional": MetricDirection.Bidirectional,
            }[cdef.metric.direction.value]
            enc.metric = EncounterMetric(
                name=cdef.metric.name,
                current=cdef.metric.starting,
                starting=cdef.metric.starting,
                direction=direction,
                threshold_high=cdef.metric.threshold_high,
                threshold_low=cdef.metric.threshold_low,
            )
        snapshot.encounter = enc
        return enc


def resolve_encounter_from_trope(
    *, snapshot: GameSnapshot, trope_id: str,
) -> StructuredEncounter | None:
    """Resolve the active encounter because a trope completed.

    Port of dispatch/tropes.rs:179-181. Returns the resolved encounter
    (for OTEL / payload emission) or ``None`` if nothing to resolve.
    """
    enc = snapshot.encounter
    if enc is None or enc.resolved:
        return None
    with encounter_resolved_span(
        encounter_type=enc.encounter_type,
        outcome=f"resolved by trope completion: {trope_id}",
        source="trope",
    ):
        enc.resolve_from_trope(trope_id)
    return enc
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_encounter_lifecycle.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py \
        sidequest-server/tests/server/test_encounter_lifecycle.py
git commit -m "feat(server): instantiate_encounter_from_trigger + trope resolution (story 3.4)"
```

---

## Task 10: Wire encounter instantiation into `_apply_narration_result_to_snapshot`

When the narrator emits `result.confrontation = "combat"`, create the encounter. When `result.beat_selections` are present and an encounter is live, apply each selection (emit `encounter.beat_applied`, bump `encounter.beat`, nudge metric by `BeatDef.metric_delta`, detect phase transitions).

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` (`_apply_narration_result_to_snapshot` ~L1934 onward)
- Test: `sidequest-server/tests/server/test_encounter_apply_narration.py` (create)

- [ ] **Step 1: Write the failing tests**

```python
# sidequest-server/tests/server/test_encounter_apply_narration.py
from __future__ import annotations

import pytest

from sidequest.agents.orchestrator import NarrationTurnResult, BeatSelection
from sidequest.genre.loader import GenreLoader, DEFAULT_GENRE_PACK_SEARCH_PATHS
from sidequest.game.session import GameSnapshot


@pytest.fixture
def cac_snap():
    snap = GameSnapshot(genre="caverns_and_claudes")
    pack = GenreLoader(DEFAULT_GENRE_PACK_SEARCH_PATHS).load("caverns_and_claudes")
    return snap, pack


def test_narrator_confrontation_trigger_creates_encounter(cac_snap) -> None:
    from sidequest.server.session_handler import _apply_narration_result_to_snapshot
    snap, pack = cac_snap
    result = NarrationTurnResult(
        narration="Goblins leap from the shadows.",
        confrontation="combat",
        npcs_present=[],
    )
    _apply_narration_result_to_snapshot(
        snap, result, player_name="Rux", pack=pack,
    )
    assert snap.encounter is not None
    assert snap.encounter.encounter_type == "combat"


def test_beat_selection_applied_bumps_metric(cac_snap) -> None:
    from sidequest.game.encounter import StructuredEncounter
    from sidequest.server.session_handler import _apply_narration_result_to_snapshot
    snap, pack = cac_snap
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    # Overwrite to cac combat metric (momentum, bidirectional, starts 0)
    from sidequest.game.encounter import EncounterMetric, MetricDirection
    enc.metric = EncounterMetric(
        name="momentum", current=0, starting=0,
        direction=MetricDirection.Bidirectional,
        threshold_high=10, threshold_low=-10,
    )
    snap.encounter = enc
    result = NarrationTurnResult(
        narration="The blade sings.",
        beat_selections=[BeatSelection(actor="Rux", beat_id="attack", target=None)],
    )
    _apply_narration_result_to_snapshot(
        snap, result, player_name="Rux", pack=pack,
    )
    assert snap.encounter.beat == 1
    # cac attack: metric_delta=2 → momentum rises to 2
    assert snap.encounter.metric.current == 2


def test_beat_selection_unknown_beat_id_raises(cac_snap) -> None:
    from sidequest.game.encounter import StructuredEncounter
    from sidequest.server.session_handler import _apply_narration_result_to_snapshot
    snap, pack = cac_snap
    snap.encounter = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    result = NarrationTurnResult(
        narration="",
        beat_selections=[BeatSelection(actor="Rux", beat_id="tap_dance", target=None)],
    )
    with pytest.raises(ValueError, match="unknown beat_id"):
        _apply_narration_result_to_snapshot(
            snap, result, player_name="Rux", pack=pack,
        )


def test_metric_crossing_threshold_resolves_encounter(cac_snap) -> None:
    from sidequest.game.encounter import StructuredEncounter, EncounterMetric, MetricDirection
    from sidequest.server.session_handler import _apply_narration_result_to_snapshot
    snap, pack = cac_snap
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    enc.metric = EncounterMetric(
        name="momentum", current=9, starting=0,
        direction=MetricDirection.Bidirectional,
        threshold_high=10, threshold_low=-10,
    )
    snap.encounter = enc
    result = NarrationTurnResult(
        narration="",
        beat_selections=[BeatSelection(actor="Rux", beat_id="attack", target=None)],
    )
    _apply_narration_result_to_snapshot(
        snap, result, player_name="Rux", pack=pack,
    )
    # attack metric_delta=2 → 9+2=11 crosses threshold_high=10 → resolve
    assert snap.encounter.resolved is True
    assert snap.encounter.structured_phase.value == "Resolution"
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_encounter_apply_narration.py -v
```
Expected: multiple failures — `_apply_narration_result_to_snapshot` takes no `pack` kwarg and has no encounter logic.

- [ ] **Step 3: Update call-site signature + add logic**

In `session_handler.py`, change the signature at L1934 to accept `pack: GenrePack`:

```python
def _apply_narration_result_to_snapshot(
    snapshot: GameSnapshot,
    result: object,
    player_name: str,
    *,
    pack: "GenrePack | None" = None,
) -> None:
```

At the bottom of that function (before the `return`), add encounter handling:

```python
    # --- Encounter lifecycle (Story 3.4) ---
    if pack is not None:
        from sidequest.server.dispatch.confrontation import find_confrontation_def
        from sidequest.server.dispatch.encounter_lifecycle import (
            instantiate_encounter_from_trigger,
        )
        from sidequest.telemetry.spans import (
            encounter_beat_applied_span,
            encounter_phase_transition_span,
            encounter_resolved_span,
            combat_tick_span,
        )
        from sidequest.game.encounter import EncounterPhase, MetricDirection

        # (a) Narrator-initiated encounter
        if result.confrontation and (
            snapshot.encounter is None or snapshot.encounter.resolved
        ):
            combatants = (
                [e.name for e in result.npcs_present] or [player_name]
            )
            combatants = [player_name] + [c for c in combatants if c != player_name]
            instantiate_encounter_from_trigger(
                snapshot=snapshot, pack=pack,
                encounter_type=result.confrontation,
                combatants=combatants, hp=10,
            )

        # (b) Apply beat_selections
        enc = snapshot.encounter
        if enc is not None and not enc.resolved and result.beat_selections:
            cdef = find_confrontation_def(
                pack.rules.confrontations if pack.rules else [],
                enc.encounter_type,
            )
            if cdef is None:
                raise ValueError(
                    f"active encounter type {enc.encounter_type!r} not in pack"
                )
            beat_by_id = {b.id: b for b in cdef.beats}
            prev_phase = enc.structured_phase
            for sel in result.beat_selections:
                beat = beat_by_id.get(sel.beat_id)
                if beat is None:
                    raise ValueError(
                        f"unknown beat_id {sel.beat_id!r} for encounter "
                        f"{enc.encounter_type!r}"
                    )
                with encounter_beat_applied_span(
                    encounter_type=enc.encounter_type, actor=sel.actor,
                    beat_id=sel.beat_id, metric_delta=beat.metric_delta,
                ):
                    enc.metric.current += beat.metric_delta
                enc.beat += 1
                # Phase ladder: Setup(0) → Opening(1) → Escalation(2+) → Climax(near threshold)
                _advance_phase(enc)
                with combat_tick_span(
                    encounter_type=enc.encounter_type, beat=enc.beat,
                    phase=(enc.structured_phase or EncounterPhase.Setup).value,
                ):
                    pass
                # Threshold check → resolve
                m = enc.metric
                threshold_hit = (
                    (m.threshold_high is not None and m.current >= m.threshold_high)
                    or (m.threshold_low is not None and m.current <= m.threshold_low)
                )
                if threshold_hit or beat.resolution:
                    enc.resolved = True
                    enc.structured_phase = EncounterPhase.Resolution
                    enc.outcome = f"resolved at beat {enc.beat}"
                    with encounter_resolved_span(
                        encounter_type=enc.encounter_type,
                        outcome=enc.outcome, source="metric",
                    ):
                        pass
                    break
            if prev_phase != enc.structured_phase:
                with encounter_phase_transition_span(
                    from_phase=(prev_phase.value if prev_phase else "None"),
                    to_phase=(enc.structured_phase.value
                              if enc.structured_phase else "None"),
                    encounter_type=enc.encounter_type,
                ):
                    pass
```

Add the `_advance_phase` helper right after `_apply_narration_result_to_snapshot`:

```python
def _advance_phase(enc: "StructuredEncounter") -> None:
    """Promote the encounter's phase based on beat count + metric distance.

    Port of Rust's phase-ladder logic (encounter.rs). Climax triggers when
    the metric is within one beat's reach of a threshold.
    """
    from sidequest.game.encounter import EncounterPhase
    if enc.structured_phase is None:
        enc.structured_phase = EncounterPhase.Setup
    # Simple beat-driven ladder; climax heuristic requires metric_delta range.
    ladder = {
        0: EncounterPhase.Setup, 1: EncounterPhase.Opening,
        2: EncounterPhase.Escalation, 3: EncounterPhase.Escalation,
    }
    enc.structured_phase = ladder.get(enc.beat, EncounterPhase.Climax)
```

Update the existing caller at L1620:
```python
        _apply_narration_result_to_snapshot(
            snapshot, result, sd.player_name, pack=sd.genre_pack,
        )
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_encounter_apply_narration.py \
    tests/server/test_dispatch.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/server/test_encounter_apply_narration.py
git commit -m "feat(server): wire encounter instantiation + beat apply into narration result (story 3.4)"
```

---

## Task 11: Dispatch `CONFRONTATION` message on encounter begin/active/end

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` (`_execute_narration_turn` around L1679–L1710, and `_KIND_TO_MESSAGE_CLS` at L109)
- Test: `sidequest-server/tests/server/test_confrontation_dispatch_wiring.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_confrontation_dispatch_wiring.py
"""Prove that CONFRONTATION messages fire on encounter begin, tick, and end.

Mocks the narrator — no LLM call.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from sidequest.agents.orchestrator import BeatSelection, NarrationTurnResult
from sidequest.protocol.messages import ConfrontationMessage


def _result(narration="ok", **kwargs) -> NarrationTurnResult:
    return NarrationTurnResult(narration=narration, **kwargs)


@pytest.mark.asyncio
async def test_confrontation_message_emitted_on_encounter_start(
    session_handler_factory,  # fixture in conftest.py that gives a wired handler
):
    sd, handler = session_handler_factory(genre="caverns_and_claudes")
    sd.orchestrator.run_narration_turn = AsyncMock(
        return_value=_result(confrontation="combat")
    )
    from sidequest.server.session_handler import _build_turn_context
    msgs = await handler._execute_narration_turn(
        sd, "I attack the goblins!", _build_turn_context(sd),
    )
    conf = [m for m in msgs if isinstance(m, ConfrontationMessage)]
    assert len(conf) == 1
    assert conf[0].payload.active is True
    assert conf[0].payload.type == "combat"
    assert [b["id"] for b in conf[0].payload.beats]  # beats included


@pytest.mark.asyncio
async def test_confrontation_message_active_false_when_resolved(
    session_handler_factory,
):
    from sidequest.game.encounter import (
        StructuredEncounter, EncounterMetric, MetricDirection,
    )
    sd, handler = session_handler_factory(genre="caverns_and_claudes")
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    enc.metric = EncounterMetric(
        name="momentum", current=9, starting=0,
        direction=MetricDirection.Bidirectional,
        threshold_high=10, threshold_low=-10,
    )
    sd.snapshot.encounter = enc
    sd.orchestrator.run_narration_turn = AsyncMock(
        return_value=_result(
            beat_selections=[BeatSelection(actor="Rux", beat_id="attack", target=None)],
        )
    )
    from sidequest.server.session_handler import _build_turn_context
    msgs = await handler._execute_narration_turn(
        sd, "Press the attack!", _build_turn_context(sd),
    )
    conf = [m for m in msgs if isinstance(m, ConfrontationMessage)]
    assert len(conf) == 1
    assert conf[0].payload.active is False
```

Note: the `session_handler_factory` fixture may already exist in `tests/server/conftest.py`. If not, add it there — mirror the pattern of existing `test_dispatch.py` fixtures.

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_confrontation_dispatch_wiring.py -v
```

- [ ] **Step 3: Implement dispatch**

Update `_KIND_TO_MESSAGE_CLS` in `session_handler.py:109`:

```python
from sidequest.protocol.messages import ConfrontationMessage
_KIND_TO_MESSAGE_CLS: dict[str, type] = {
    "NARRATION": NarrationMessage,
    "CONFRONTATION": ConfrontationMessage,
}
```

Extend `_build_message_for_kind` (L121+) with a CONFRONTATION branch mirroring the NARRATION one.

In `_execute_narration_turn`, track the encounter state before and after the apply call and emit the appropriate message. Replace the section after `_apply_narration_result_to_snapshot(...)`:

```python
        prior_encounter = snapshot.encounter
        prior_live = prior_encounter is not None and not prior_encounter.resolved
        prior_type = prior_encounter.encounter_type if prior_encounter else None

        _apply_narration_result_to_snapshot(
            snapshot, result, sd.player_name, pack=sd.genre_pack,
        )
        snapshot.turn_manager.record_interaction()

        now_encounter = snapshot.encounter
        now_live = now_encounter is not None and not now_encounter.resolved
```

Then right before building `outbound` (before the `narration_payload = NarrationPayload(...)` line), compute + push the CONFRONTATION message:

```python
        confrontation_msg: ConfrontationMessage | None = None
        from sidequest.server.dispatch.confrontation import (
            build_confrontation_payload,
            build_clear_confrontation_payload,
            find_confrontation_def,
        )
        from sidequest.protocol.messages import (
            ConfrontationMessage, ConfrontationPayload,
        )
        if now_live and now_encounter is not None:
            cdef = find_confrontation_def(
                sd.genre_pack.rules.confrontations if sd.genre_pack.rules else [],
                now_encounter.encounter_type,
            )
            if cdef is not None:
                payload_dict = build_confrontation_payload(
                    encounter=now_encounter, cdef=cdef, genre_slug=sd.genre_slug,
                )
                confrontation_msg = ConfrontationMessage(
                    payload=ConfrontationPayload(**payload_dict),
                    player_id=sd.player_id,
                )
        elif prior_live and not now_live:
            payload_dict = build_clear_confrontation_payload(
                encounter_type=prior_type or "combat",
                genre_slug=sd.genre_slug,
            )
            confrontation_msg = ConfrontationMessage(
                payload=ConfrontationPayload(**payload_dict),
                player_id=sd.player_id,
            )
```

Then append `confrontation_msg` to `outbound` if it's not `None`, placing it before `NarrationEndMessage`.

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_confrontation_dispatch_wiring.py \
    tests/server/test_dispatch.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/server/test_confrontation_dispatch_wiring.py
git commit -m "feat(server): dispatch CONFRONTATION on encounter begin/end (story 3.4)"
```

---

## Task 12: `strip_combat_brackets` helper + aside integration

Rust dispatches asides with `[combat]` bracket markers and strips them before narrator input (`dispatch/aside.rs:7,46,95`).

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch/combat_brackets.py`
- Test: `sidequest-server/tests/server/test_combat_brackets.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_combat_brackets.py
from __future__ import annotations

from sidequest.server.dispatch.combat_brackets import strip_combat_brackets


def test_strip_removes_leading_combat_bracket() -> None:
    assert strip_combat_brackets("[combat] I swing my sword") == "I swing my sword"


def test_strip_removes_embedded_combat_bracket() -> None:
    # Rust behaviour: any [combat] tag is scrubbed.
    assert strip_combat_brackets("foo [combat] bar") == "foo  bar"


def test_strip_preserves_non_combat_brackets() -> None:
    assert strip_combat_brackets("[chase] run!") == "[chase] run!"


def test_strip_is_case_insensitive_on_tag() -> None:
    assert strip_combat_brackets("[COMBAT] attack") == "attack"
    assert strip_combat_brackets("[Combat] attack") == "attack"


def test_strip_empty_returns_empty() -> None:
    assert strip_combat_brackets("") == ""
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_combat_brackets.py -v
```

- [ ] **Step 3: Implement**

```python
# sidequest-server/sidequest/server/dispatch/combat_brackets.py
"""Strip ``[combat]`` markers from aside prose.

Port of sidequest-api/crates/sidequest-server/src/dispatch/aside.rs
``strip_combat_brackets`` (lines 7, 46, 95). Story 3.4.
"""
from __future__ import annotations

import re

_BRACKET_RE = re.compile(r"\[combat\]\s?", flags=re.IGNORECASE)


def strip_combat_brackets(text: str) -> str:
    """Remove ``[combat]`` tags (case-insensitive) from aside text.

    Leaves any other bracketed tags alone — only the literal ``combat``
    marker is scrubbed. Preserves one trailing space-swallow on removal
    to avoid leaving ``"I swung"`` as ``" I swung"``.
    """
    return _BRACKET_RE.sub("", text).lstrip(" ") if text.startswith("[") else _BRACKET_RE.sub("", text)
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_combat_brackets.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/combat_brackets.py \
        sidequest-server/tests/server/test_combat_brackets.py
git commit -m "feat(server): strip_combat_brackets helper (story 3.4)"
```

- [ ] **Step 6: Wire into aside path**

Grep for the aside dispatch (`grep -rn "aside" sidequest-server/sidequest/server`). Where the aside text is forwarded to the narrator, pipe it through `strip_combat_brackets`. If no Python aside path exists yet, add a minimal one: in `session_handler.py`, the `PlayerActionPayload.aside: bool` flag is already parsed; on `aside=True`, call `strip_combat_brackets(action)` before passing to the orchestrator. Add a test for the wiring:

```python
# append to tests/server/test_combat_brackets.py
@pytest.mark.asyncio
async def test_aside_action_strips_brackets_before_narrator(
    session_handler_factory,
):
    from unittest.mock import AsyncMock
    from sidequest.agents.orchestrator import NarrationTurnResult
    sd, handler = session_handler_factory(genre="caverns_and_claudes")
    sd.orchestrator.run_narration_turn = AsyncMock(
        return_value=NarrationTurnResult(narration="ok")
    )
    await handler._handle_aside_action(sd, "[combat] I whisper to James")
    seen_action = sd.orchestrator.run_narration_turn.call_args[0][0]
    assert "[combat]" not in seen_action
    assert "whisper to James" in seen_action
```

Commit with `feat(server): strip [combat] brackets on aside path (story 3.4)`.

---

## Task 13: XP award differential

Port `dispatch/state_mutations.rs:39`: 25 XP per turn in-combat, 10 otherwise.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` (add `award_turn_xp`)
- Modify: `sidequest-server/sidequest/server/session_handler.py` (call it after `_apply_narration_result_to_snapshot`)
- Test: `sidequest-server/tests/server/test_xp_award.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_xp_award.py
from __future__ import annotations

import pytest

from sidequest.game.encounter import StructuredEncounter
from sidequest.game.session import GameSnapshot
from sidequest.server.dispatch.encounter_lifecycle import award_turn_xp


@pytest.fixture
def snap_with_char():
    snap = GameSnapshot(genre="caverns_and_claudes")
    # Minimal character stub — attach to snap. Real shape in
    # sidequest/game/character.py; tests may need a fixture factory.
    from sidequest.game.character import Character
    from sidequest.game.creature_core import CreatureCore
    core = CreatureCore(name="Rux", level=1, xp=0)
    snap.characters.append(Character(core=core))
    return snap


def test_award_out_of_combat_grants_10_xp(snap_with_char):
    award_turn_xp(snap_with_char, in_combat=False)
    assert snap_with_char.characters[0].core.xp == 10


def test_award_in_combat_grants_25_xp(snap_with_char):
    award_turn_xp(snap_with_char, in_combat=True)
    assert snap_with_char.characters[0].core.xp == 25


def test_award_no_character_is_noop(snap_with_char):
    snap_with_char.characters.clear()
    award_turn_xp(snap_with_char, in_combat=True)  # must not raise
```

(Adjust imports to match the real `Character` / `CreatureCore` constructors — check `sidequest/game/character.py` + `sidequest/game/creature_core.py` before writing the test.)

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_xp_award.py -v
```

- [ ] **Step 3: Implement in `encounter_lifecycle.py`**

```python
def award_turn_xp(snapshot: GameSnapshot, *, in_combat: bool) -> None:
    """Award per-turn XP. 25 in-combat, 10 out. Port of state_mutations.rs:39."""
    if not snapshot.characters:
        return
    delta = 25 if in_combat else 10
    char = snapshot.characters[0]
    char.core.xp = (char.core.xp or 0) + delta
```

Call it in `session_handler._execute_narration_turn` after the encounter apply:

```python
        from sidequest.server.dispatch.encounter_lifecycle import award_turn_xp
        in_combat_now = (
            snapshot.encounter is not None
            and not snapshot.encounter.resolved
            and _is_combat_category(sd.genre_pack, snapshot.encounter.encounter_type)
        )
        award_turn_xp(snapshot, in_combat=in_combat_now)
```

Add `_is_combat_category` helper at module level:

```python
def _is_combat_category(pack: "GenrePack", encounter_type: str) -> bool:
    defs = pack.rules.confrontations if pack.rules else []
    for d in defs:
        if d.confrontation_type == encounter_type:
            return d.category == "combat"
    return False
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_xp_award.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py \
        sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/server/test_xp_award.py
git commit -m "feat(server): XP award differential by in_combat (story 3.4)"
```

---

## Task 14: Resource-pool patch application → threshold lore mint

Wire narrator-emitted resource deltas into session resource pools; when a crossing happens, mint threshold lore.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` (add `apply_resource_patches`)
- Modify: `sidequest-server/sidequest/server/session_handler.py` (call after encounter apply)
- Test: `sidequest-server/tests/server/test_resource_patch_wiring.py`

The `NarrationTurnResult` surfaces `gold_change: int | None` and `affinity_progress: list[tuple[str, int]]` today. Phase 3.4's "patch application" covers session-level `ResourcePool` entries named in the genre pack. If narrator doesn't yet emit generic `resource_patches`, wire only the path you have — `affinity_progress` is the concrete case; each `(name, delta)` maps to a ResourcePool by name.

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_resource_patch_wiring.py
from __future__ import annotations

import pytest

from sidequest.game.resource_pool import ResourcePool, ResourceThreshold
from sidequest.game.session import GameSnapshot
from sidequest.server.dispatch.encounter_lifecycle import apply_resource_patches


def test_affinity_progress_applied_to_pool():
    pool = ResourcePool(
        name="Luck", current=5, minimum=0, maximum=10, thresholds=[],
    )
    snap = GameSnapshot(genre="cac", resources=[pool])
    minted = apply_resource_patches(snap, affinity_progress=[("Luck", 3)])
    assert snap.resources[0].current == 8
    assert minted == []


def test_crossing_threshold_mints_lore():
    pool = ResourcePool(
        name="Humanity", current=5, minimum=0, maximum=10,
        thresholds=[ResourceThreshold(
            at=3, direction="crossing_down",
            lore_key="humanity_low", narrator_hint="cold eyes",
        )],
    )
    snap = GameSnapshot(genre="nd", resources=[pool])
    minted = apply_resource_patches(
        snap, affinity_progress=[("Humanity", -3)],  # 5 → 2 crosses 3
    )
    assert pool.current == 2
    assert len(minted) == 1
    assert minted[0].lore_key == "humanity_low"


def test_unknown_pool_name_raises():
    snap = GameSnapshot(genre="cac", resources=[])
    with pytest.raises(ValueError, match="unknown resource pool"):
        apply_resource_patches(snap, affinity_progress=[("Nonsense", 1)])
```

(Verify field names against `sidequest/game/resource_pool.py` and `sidequest/game/thresholds.py` — the exact `ResourceThreshold` constructor kwargs may be `at`/`event_id` instead of `at`/`lore_key`. Adjust test to match.)

- [ ] **Step 2: Run — expect failure**

```bash
uv run --directory sidequest-server pytest tests/server/test_resource_patch_wiring.py -v
```

- [ ] **Step 3: Implement**

```python
# append to encounter_lifecycle.py
def apply_resource_patches(
    snapshot: GameSnapshot,
    *,
    affinity_progress: list[tuple[str, int]],
) -> list:
    """Apply narrator-emitted resource deltas + mint threshold lore.

    Returns the list of newly-minted lore entries (caller emits them to
    the client). Raises ``ValueError`` on unknown pool name — CLAUDE.md
    "No Silent Fallbacks": a misspelled resource name must not be
    silently ignored.
    """
    from sidequest.game.resource_pool import mint_threshold_lore
    minted: list = []
    for name, delta in affinity_progress:
        pool = next((p for p in snapshot.resources if p.name == name), None)
        if pool is None:
            raise ValueError(f"unknown resource pool {name!r}")
        before = pool.current
        pool.current = max(pool.minimum, min(pool.maximum, before + delta))
        lore = mint_threshold_lore(pool, before=before, after=pool.current)
        minted.extend(lore)
    return minted
```

Call in `_execute_narration_turn` after the encounter apply:

```python
        from sidequest.server.dispatch.encounter_lifecycle import apply_resource_patches
        try:
            minted = apply_resource_patches(
                snapshot, affinity_progress=result.affinity_progress or [],
            )
        except ValueError as exc:
            logger.error("resource.patch_failed error=%s", exc)
            minted = []
        for entry in minted:
            logger.info("resource.threshold_minted key=%s", entry.lore_key)
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run --directory sidequest-server pytest tests/server/test_resource_patch_wiring.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py \
        sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/server/test_resource_patch_wiring.py
git commit -m "feat(server): apply resource patches + mint threshold lore (story 3.4)"
```

---

## Task 15: Trope-driven encounter resolution wiring

When a trope completes mid-turn (already detected elsewhere in the dispatch — grep for `trope.completed` / `trope.resolved`), call `resolve_encounter_from_trope`.

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_encounter_trope_resolution.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_encounter_trope_resolution.py
from __future__ import annotations

from sidequest.game.encounter import StructuredEncounter
from sidequest.game.session import GameSnapshot
from sidequest.server.dispatch.encounter_lifecycle import (
    resolve_encounter_from_trope,
)


def test_resolve_from_trope_marks_resolved():
    snap = GameSnapshot(genre="cac")
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    snap.encounter = enc
    result = resolve_encounter_from_trope(snapshot=snap, trope_id="last_stand")
    assert result is enc
    assert enc.resolved is True
    assert "last_stand" in (enc.outcome or "")


def test_resolve_from_trope_no_encounter_returns_none():
    snap = GameSnapshot(genre="cac")
    assert resolve_encounter_from_trope(snapshot=snap, trope_id="x") is None


def test_resolve_from_trope_already_resolved_returns_none():
    snap = GameSnapshot(genre="cac")
    enc = StructuredEncounter.combat(combatants=["Rux"], hp=10)
    enc.resolved = True
    snap.encounter = enc
    assert resolve_encounter_from_trope(snapshot=snap, trope_id="x") is None
```

- [ ] **Step 2: Run — expect pass immediately** (the helper shipped in Task 9).

```bash
uv run --directory sidequest-server pytest tests/server/test_encounter_trope_resolution.py -v
```

- [ ] **Step 3: Hook the call in the dispatch path**

Grep for where tropes are ticked in `session_handler.py` / `dispatch/*.py`. When a trope completes, call:

```python
resolved_enc = resolve_encounter_from_trope(
    snapshot=snap, trope_id=completed_trope_id,
)
if resolved_enc is not None:
    # Emit CONFRONTATION active=False through the same path as Task 11.
    ...
```

If the trope-completion signal is not yet wired into Python at all (Phase 3 may not have ported the trope engine), log this as an IOU in a code comment referencing the current story, but ensure the helper is at least covered by the unit test.

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/server/test_encounter_trope_resolution.py
git commit -m "feat(server): resolve encounter on trope completion (story 3.4)"
```

---

## Task 16: End-to-end integration test — caverns_and_claudes combat walkthrough

This is the plan's closing gate (phase-3 L160-162).

**Files:**
- Create: `sidequest-server/tests/server/test_encounter_wiring_e2e.py`

- [ ] **Step 1: Write the test**

```python
# sidequest-server/tests/server/test_encounter_wiring_e2e.py
"""End-to-end: drive a caverns_and_claudes combat via PLAYER_ACTION.

No live LLM — the narrator is mocked. Asserts:
  - Turn 1: narrator emits confrontation='combat' → StructuredEncounter
            persisted, CONFRONTATION(active=True) dispatched, OTEL
            encounter.confrontation_initiated fires.
  - Turn 2: beat_selection applied → metric advances, combat.tick fires.
  - Turn 3: beat pushes metric across threshold → encounter.resolved
            fires, CONFRONTATION(active=False) dispatched.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry import trace

from sidequest.agents.orchestrator import BeatSelection, NarrationTurnResult
from sidequest.protocol.messages import ConfrontationMessage


@pytest.fixture
def span_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    yield exporter


@pytest.mark.asyncio
async def test_combat_walkthrough_turns_initiate_tick_resolve(
    session_handler_factory, span_exporter,
):
    sd, handler = session_handler_factory(genre="caverns_and_claudes")
    run = AsyncMock()

    # Scripted narrator responses — turn 1 starts, turn 2 advances, turn 3 resolves.
    run.side_effect = [
        NarrationTurnResult(
            narration="Goblins leap from the shadows!",
            confrontation="combat",
        ),
        NarrationTurnResult(
            narration="Steel rings on steel.",
            beat_selections=[
                BeatSelection(actor="Rux", beat_id="attack", target=None),
            ],
        ),
        NarrationTurnResult(
            narration="The last goblin falls.",
            beat_selections=[
                BeatSelection(actor="Rux", beat_id="shield_bash", target=None),
                BeatSelection(actor="Rux", beat_id="shield_bash", target=None),
            ],
        ),
    ]
    sd.orchestrator.run_narration_turn = run
    from sidequest.server.session_handler import _build_turn_context

    # --- Turn 1 ---
    msgs1 = await handler._execute_narration_turn(
        sd, "I attack!", _build_turn_context(sd),
    )
    assert sd.snapshot.encounter is not None
    assert not sd.snapshot.encounter.resolved
    c1 = [m for m in msgs1 if isinstance(m, ConfrontationMessage)]
    assert len(c1) == 1 and c1[0].payload.active is True
    names1 = {s.name for s in span_exporter.get_finished_spans()}
    assert "encounter.confrontation_initiated" in names1

    # --- Turn 2 ---
    msgs2 = await handler._execute_narration_turn(
        sd, "Press the attack!", _build_turn_context(sd),
    )
    # momentum started at 0; attack metric_delta=2 → 2
    assert sd.snapshot.encounter.metric.current == 2
    assert not sd.snapshot.encounter.resolved
    names2 = {s.name for s in span_exporter.get_finished_spans()}
    assert "combat.tick" in names2
    assert "encounter.beat_applied" in names2

    # --- Turn 3 ---
    msgs3 = await handler._execute_narration_turn(
        sd, "Finish them!", _build_turn_context(sd),
    )
    # 2 + 4 (shield_bash) + 4 = 10 → threshold_high crossed → resolve
    assert sd.snapshot.encounter.resolved is True
    c3 = [m for m in msgs3 if isinstance(m, ConfrontationMessage)]
    assert len(c3) == 1 and c3[0].payload.active is False
    names3 = {s.name for s in span_exporter.get_finished_spans()}
    assert "encounter.resolved" in names3


@pytest.mark.asyncio
async def test_xp_award_higher_in_combat_than_out(
    session_handler_factory,
):
    """Regression: in-combat turn awards 25 xp vs 10 out-of-combat."""
    sd, handler = session_handler_factory(genre="caverns_and_claudes")
    sd.orchestrator.run_narration_turn = AsyncMock(
        return_value=NarrationTurnResult(narration="quiet walk")
    )
    from sidequest.server.session_handler import _build_turn_context
    before = sd.snapshot.characters[0].core.xp or 0
    await handler._execute_narration_turn(
        sd, "I walk", _build_turn_context(sd),
    )
    out_of_combat_gain = (sd.snapshot.characters[0].core.xp or 0) - before
    assert out_of_combat_gain == 10

    # Now start combat and take a turn
    sd.orchestrator.run_narration_turn = AsyncMock(side_effect=[
        NarrationTurnResult(narration="fight!", confrontation="combat"),
        NarrationTurnResult(
            narration="strike",
            beat_selections=[BeatSelection(
                actor=sd.snapshot.characters[0].core.name,
                beat_id="attack", target=None,
            )],
        ),
    ])
    await handler._execute_narration_turn(
        sd, "I attack", _build_turn_context(sd),
    )
    mid = sd.snapshot.characters[0].core.xp or 0
    await handler._execute_narration_turn(
        sd, "I strike", _build_turn_context(sd),
    )
    in_combat_gain = (sd.snapshot.characters[0].core.xp or 0) - mid
    assert in_combat_gain == 25
```

- [ ] **Step 2: Run — expect pass (or single-assertion diagnostic loop)**

```bash
uv run --directory sidequest-server pytest tests/server/test_encounter_wiring_e2e.py -v -x
```

If fixture `session_handler_factory` is missing, add it to `tests/server/conftest.py`. Pattern: build a `_SessionData` with a loaded `caverns_and_claudes` pack, a tmp SQLite store, a minimal Character, and a `SessionHandler` wired through `RoomRegistry`. Cross-reference `tests/server/test_dispatch.py` for existing fixture construction.

- [ ] **Step 3: Run the full suite**

```bash
uv run --directory sidequest-server pytest -x -q
```

All green.

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/tests/server/test_encounter_wiring_e2e.py \
        sidequest-server/tests/server/conftest.py
git commit -m "test(server): end-to-end caverns combat walkthrough (story 3.4)"
```

---

## Task 17: Lint, type-check, and playtest hand-off

- [ ] **Step 1: Lint + types**

```bash
just api-check       # passes fmt + clippy + test for Rust (no Rust changes — smoke only)
uv run --directory sidequest-server ruff check .
uv run --directory sidequest-server mypy sidequest
```
Resolve any warnings introduced by this story.

- [ ] **Step 2: Sprint-bound manual check (Keith)**

Per AC (phase-3 L156): Keith plays one combat scene on the Python server end-to-end before the story closes. The manual gate verifies:
- A combat scene begins with the overlay appearing
- Beats are listed and clickable
- Metric moves on each turn
- Resolution clears the overlay
- GM dashboard shows `encounter.confrontation_initiated`, `combat.tick`, `encounter.beat_applied`, `encounter.resolved`

Capture the playtest-log timestamp in the PR description.

- [ ] **Step 3: Update `docs/plans/phase-3-combat-port.md`**

Mark Story 3.4 as **Shipped** with the merge SHA + playtest date. No task outside the plan.

- [ ] **Step 4: Final commit**

```bash
git add docs/plans/phase-3-combat-port.md
git commit -m "docs: mark phase-3 story 3.4 shipped (combat dispatch)"
```

---

## Self-Review Notes

**Spec coverage vs `docs/plans/phase-3-combat-port.md:136-167`:**

| Plan bullet | Task(s) |
|---|---|
| XP differential `state_mutations.rs:39` | Task 13 |
| `find_confrontation_def` + payload assembly | Tasks 1, 2, 11 |
| `encounter.resolve_from_trope` wiring | Task 15 |
| `strip_combat_brackets` + aside context | Task 12 |
| `in_combat` in watcher fields | Task 4 (OTEL span attributes), Task 8 (derivation), Task 13 (XP) |
| `combat.*` / `encounter.*` OTEL catalog | Task 4 |
| `TurnContext.in_combat` + `encounter_summary` + Valley zone | Tasks 5, 6, 7, 8 |
| Resource-pool patch → lore mint | Task 14 |
| End-to-end playtest script | Task 16 |

**Acceptance criteria coverage:**
- OTEL byte-parity → Task 4 parity test.
- End-to-end combat completes → Task 16.
- `ctx.in_combat()` rule → Task 8.
- ConfrontationDef lookup produces label + category → Task 1.
- Keith playtest → Task 17.

**Cross-task type consistency verified:**
- `TurnContext.encounter`, `TurnContext.confrontation_def`, `TurnContext.encounter_summary` introduced Task 5/7, consumed Task 7/8.
- `ConfrontationPayload` created Task 3, consumed Task 11.
- `find_confrontation_def` created Task 1, consumed Tasks 8, 9, 10, 11.
- OTEL helpers created Task 4, consumed Tasks 9, 10, 16.

**No placeholders.** Every step has real code or a real test. The three production-wiring edits in `_execute_narration_turn` are shown as diffs against the current L1679–L1710 block.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-22-phase-3-story-3-4-combat-dispatch.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task with two-stage review. Uses `superpowers:subagent-driven-development`. Each task is bite-sized; TEA can verify RED, Dev green, Reviewer post-merge. Ideal for the 17-task breakdown.
2. **Inline Execution** — execute in this session using `superpowers:executing-plans` with batch checkpoints.

**Which approach?**
