# Session Aggregate Strangler-Fig — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a per-slug `Session` class as a strangler-fig over the post-port server tier so the orbital-map plan's clock + scene-end coordination has a real Python home, unblocking Task 5 and beyond of `2026-05-01-orbital-map-tracks-a-b.md`.

**Architecture:** New `Session` class in `sidequest/server/session.py`, owned by `SessionRoom._session`, reads/writes through `GameSnapshot.clock_t_hours` (the persistence boundary). Existing tier (`_SessionData`, `SessionRoom`, `WebSocketSessionHandler`, `GameSnapshot`) is not refactored — only extended with one field on each. Three scene-end call sites migrate from the free function `clear_scratch_on_scene_end()` to `room.session.end_scene(reason, turn=...)`; the location-change site stays on the free function.

**Tech Stack:** Python 3.12, FastAPI, pydantic, OpenTelemetry SDK, pytest, uv.

**Reference docs:**
- Spec: `docs/superpowers/specs/2026-05-01-session-aggregate-design.md`
- Drives revision of: Task 5 in `docs/superpowers/plans/2026-05-01-orbital-map-tracks-a-b.md` (this plan supersedes that task)
- ADR-067 (unified narrator), ADR-038 (WebSocket transport), ADR-082 (Rust→Python port)
- CLAUDE.md principles (No Silent Fallbacks, No Stubbing, Don't Reinvent, Wiring Tests)

**Branch:** `feat/orbital-map-tracks-a-b` on `sidequest-server` (already exists; created 2026-05-01).

**What this plan does NOT include:**
- `handle_rest()` and rest-as-a-behavior — no caller exists in the post-port server; deferred.
- Renaming `sidequest/game/session.py` → `snapshot.py` — the file is misnamed, but renaming touches every importer; out of scope.
- Promoting the `otel_capture` fixture to top-level `tests/conftest.py` — three copies remain for now.
- Renaming `sidequest/game/beat_kinds.py:BeatKind` → `MomentumBeatKind` — older code with broad usage; out of scope.

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `sidequest-server/sidequest/server/session.py` | `Session` class — per-slug aggregate over GameSnapshot. |
| `sidequest-server/tests/server/test_session_aggregate.py` | Unit tests for `Session`. |
| `sidequest-server/tests/server/test_session_room_session_binding.py` | `SessionRoom.session` lifecycle tests. |
| `sidequest-server/tests/server/test_clock_persistence.py` | `GameSnapshot.clock_t_hours` round-trip test. |
| `sidequest-server/tests/integration/test_session_clock_e2e.py` | Wiring test: scene-end → snapshot.clock_t_hours moves + spans fire. |

### Modified files

| Path | Change |
|---|---|
| `sidequest-server/sidequest/orbital/beats.py` | Rename `BeatKind`→`StoryBeatKind`, `Beat`→`StoryBeat`. |
| `sidequest-server/tests/orbital/test_beats.py` | Update references after rename. |
| `sidequest-server/sidequest/game/session.py` | Add `clock_t_hours: float` field to `GameSnapshot`. |
| `sidequest-server/sidequest/server/session_handler.py` | Add `_room: SessionRoom \| None = None` field to `_SessionData`. |
| `sidequest-server/sidequest/server/session_room.py` | Add `_session: Session \| None` field; bind in `bind_world`; `session` property. |
| `sidequest-server/sidequest/handlers/connect.py` | Pass `_room=room` into `_SessionData(...)` constructor at line ~618. |
| `sidequest-server/sidequest/server/narration_apply.py` | Add `room: SessionRoom` kwarg to `_apply_narration_result_to_snapshot`; replace `clear_scratch_on_scene_end` at line 1443 with `room.session.end_scene(...)`. Line 654 (location_change) untouched. |
| `sidequest-server/sidequest/server/dispatch/yield_action.py` | Add `room: SessionRoom` kwarg to `handle_yield`; replace `clear_scratch_on_scene_end` at line 107. |
| `sidequest-server/sidequest/handlers/dice_throw.py` | Replace `clear_scratch_on_scene_end` at line 162 with `sd._room.session.end_scene(...)`. |
| `sidequest-server/sidequest/handlers/yield_action.py` | Update caller at line 102 to pass `room=sd._room`. |
| `sidequest-server/sidequest/server/websocket_session_handler.py` | Update caller at line 1597 to pass `room=sd._room`. |

---

## Pre-Task 0: Rename `BeatKind`/`Beat` → `StoryBeatKind`/`StoryBeat`

The new orbital `BeatKind` (story-time: `encounter|rest|travel|downtime`) cognitively collides with the older `sidequest/game/beat_kinds.py:BeatKind` (combat momentum: `strike|brace|push|angle`). Rename the new orbital ones before they accumulate consumers.

**Files:**
- Modify: `sidequest-server/sidequest/orbital/beats.py`
- Modify: `sidequest-server/tests/orbital/test_beats.py`

- [ ] **Step 1: Rename in `sidequest/orbital/beats.py`**

In `sidequest-server/sidequest/orbital/beats.py`:

- `class BeatKind(Enum):` → `class StoryBeatKind(Enum):`
- `DEFAULT_DURATIONS_HOURS: dict[BeatKind, float]` → `dict[StoryBeatKind, float]`
- All `BeatKind.X` references inside the file → `StoryBeatKind.X` (in `DEFAULT_DURATIONS_HOURS` keys and `_resolve_duration`)
- `class Beat:` → `class StoryBeat:`
- `kind: BeatKind` field on `Beat` → `kind: StoryBeatKind` field on `StoryBeat`
- `def advance_clock_via_beat(clock: Clock, beat: Beat)` → `def advance_clock_via_beat(clock: Clock, beat: StoryBeat)`
- Inside `_resolve_duration(beat: Beat)` → `_resolve_duration(beat: StoryBeat)`

- [ ] **Step 2: Update `tests/orbital/test_beats.py`**

In `sidequest-server/tests/orbital/test_beats.py`:

- Update import:
```python
from sidequest.orbital.beats import (
    StoryBeat,
    StoryBeatKind,
    DEFAULT_DURATIONS_HOURS,
    advance_clock_via_beat,
)
```
- Replace every `Beat(` → `StoryBeat(`
- Replace every `BeatKind.` → `StoryBeatKind.`
- Replace `{k.value for k in BeatKind}` → `{k.value for k in StoryBeatKind}`
- The string assertion `"REST.*fixed at 8h"` etc. is unchanged (the error message uses `beat.kind.name`, which is `StoryBeatKind.REST.name == "REST"`).

- [ ] **Step 3: Run all orbital tests to verify rename is consistent**

```bash
cd sidequest-server && uv run pytest tests/orbital/ -v 2>&1 | tail -25
```

Expected: 36 tests pass (7 clock + 12 beats + 17 display).

- [ ] **Step 4: Verify no stragglers anywhere in the codebase**

```bash
grep -rn "from sidequest.orbital.beats import.*\bBeat\b\|orbital.beats.BeatKind\|orbital.beats.Beat\b" sidequest-server/sidequest --include="*.py" 2>/dev/null
```

Expected: no output. (At this point only the orbital module itself uses these names.)

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/orbital/beats.py tests/orbital/test_beats.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
refactor(orbital): rename BeatKind->StoryBeatKind, Beat->StoryBeat

Disambiguates from sidequest/game/beat_kinds.py:BeatKind (combat
momentum: strike|brace|push|angle). The new orbital story-time beat
taxonomy (encounter|rest|travel|downtime) gets a less generic name
before it accumulates consumers in Session.advance_via_beat (next
task).

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md.
EOF
)"
```

---

## Task A: `GameSnapshot.clock_t_hours` field + persistence round-trip test

Add the single new field on `GameSnapshot` that the `Session` aggregate writes through. Verify the existing `SqliteStore` save/load path covers it for free.

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py` (add field to `GameSnapshot`)
- Create: `sidequest-server/tests/server/test_clock_persistence.py`

- [ ] **Step 1: Locate the `GameSnapshot` field block**

```bash
grep -n "^class GameSnapshot\|^    [a-z_]*: \|model_config" sidequest-server/sidequest/game/session.py | sed -n '/class GameSnapshot/,/^class \w/p' | head -30
```

Expected: identifies the field-declaration block of `GameSnapshot` (starts at line 401 per recon). Note the existing field-style — pydantic `Field(default=...)` form is already used on this model.

- [ ] **Step 2: Write the failing persistence round-trip test**

Create `sidequest-server/tests/server/test_clock_persistence.py`:

```python
"""Round-trip test for GameSnapshot.clock_t_hours.

Verifies the new field rides on the existing SqliteStore save/load path
without schema migrations. Old saves without the field load with default 0.0.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.persistence import SqliteStore
from sidequest.game.session import GameSnapshot


def test_clock_t_hours_round_trip(tmp_path: Path):
    """Save a GameSnapshot with non-zero clock_t_hours, load, verify."""
    db_path = tmp_path / "test.db"
    store = SqliteStore(db_path)

    snap = GameSnapshot(clock_t_hours=42.0)
    store.save_snapshot(snap)

    loaded = store.load_snapshot()
    assert loaded is not None
    assert loaded.clock_t_hours == 42.0


def test_clock_t_hours_default_zero():
    """Default value when not set."""
    snap = GameSnapshot()
    assert snap.clock_t_hours == 0.0


def test_clock_t_hours_preserved_through_dict_roundtrip():
    """Pydantic model_dump / model_validate round trip preserves field."""
    snap = GameSnapshot(clock_t_hours=17.5)
    data = snap.model_dump()
    assert data["clock_t_hours"] == 17.5
    restored = GameSnapshot.model_validate(data)
    assert restored.clock_t_hours == 17.5
```

- [ ] **Step 3: Run the test to verify it fails (field does not yet exist)**

```bash
cd sidequest-server && uv run pytest tests/server/test_clock_persistence.py -v 2>&1 | tail -20
```

Expected: FAIL — `GameSnapshot()` rejects `clock_t_hours=...` (Pydantic strict-extras).

If the test passes (i.e., `GameSnapshot` already permits `extra` fields silently), abort and investigate — the strict-extras assumption is what makes the tests meaningful. The expected pattern is that pydantic will reject the kwarg.

If the test errors with `SqliteStore(...)` constructor mismatch (signature differs from `SqliteStore(db_path)`), inspect `sidequest/game/persistence.py` for the actual constructor and adjust the test setup. Do not invent a fixture; match the existing API.

- [ ] **Step 4: Add the `clock_t_hours` field to `GameSnapshot`**

Edit `sidequest-server/sidequest/game/session.py`. Locate the `class GameSnapshot(BaseModel):` block (starts at line 401). Add the field — placement: alongside other top-level scalar state fields, ordered alphabetically among the new-style additions (the model uses pydantic Field() pattern):

```python
    clock_t_hours: float = Field(
        default=0.0,
        description=(
            "Story-time hours from world epoch. Advanced only via "
            "Session.advance_via_beat (which calls advance_clock_via_beat). "
            "See sidequest.server.session.Session and "
            "sidequest.orbital.clock.Clock."
        ),
    )
```

If `Field` is not yet imported in this file, the existing pydantic imports already include it (`from pydantic import BaseModel, Field, field_validator, model_validator` per recon at line 17). Confirm before editing; do not add a duplicate import.

- [ ] **Step 5: Run the persistence test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/server/test_clock_persistence.py -v 2>&1 | tail -15
```

Expected: 3 tests pass.

- [ ] **Step 6: Run the broader server test suite to confirm no regression**

```bash
cd sidequest-server && uv run pytest 2>&1 | tail -10
```

Expected: same pass/fail count as before this task (4 pre-existing failures noted in Task 0 of the orbital plan are unrelated to this change). Adding an optional defaulted field should not break any test that constructs `GameSnapshot()` without the field.

- [ ] **Step 7: Commit**

```bash
git -C sidequest-server add sidequest/game/session.py tests/server/test_clock_persistence.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
feat(session): add clock_t_hours to GameSnapshot

Single new pydantic field for the orbital story-time clock. Defaults to
0.0 so legacy saves load cleanly. Persistence rides on the existing
SqliteStore save/load path with no schema change.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md
§Components.
EOF
)"
```

---

## Task B: `Session` class + unit tests

Create the `Session` aggregate, fully tested in isolation against a bare `GameSnapshot` instance (no `SessionRoom` yet — that comes in Task C).

**Files:**
- Create: `sidequest-server/sidequest/server/session.py`
- Create: `sidequest-server/tests/server/test_session_aggregate.py`

- [ ] **Step 1: Write the failing tests for `Session`**

Create `sidequest-server/tests/server/test_session_aggregate.py`:

```python
"""Session aggregate unit tests.

Session is constructed directly over a GameSnapshot for these unit tests.
SessionRoom binding is covered separately in test_session_room_session_binding.
"""
from __future__ import annotations

import pytest

from sidequest.game.session import GameSnapshot
from sidequest.orbital.beats import StoryBeat, StoryBeatKind
from sidequest.orbital.clock import Clock
from sidequest.server.session import Session


def test_session_construction_starts_at_snapshot_t_hours_zero():
    snap = GameSnapshot()
    session = Session(snap)
    assert session.clock.t_hours == 0.0


def test_session_construction_honors_existing_t_hours():
    snap = GameSnapshot(clock_t_hours=72.0)
    session = Session(snap)
    assert session.clock.t_hours == 72.0


def test_session_clock_property_returns_clock_instance():
    snap = GameSnapshot(clock_t_hours=10.0)
    session = Session(snap)
    clk = session.clock
    assert isinstance(clk, Clock)
    assert clk.t_hours == 10.0


def test_session_clock_view_is_read_only():
    """Mutations on the returned Clock do NOT persist."""
    snap = GameSnapshot(clock_t_hours=5.0)
    session = Session(snap)
    clk = session.clock
    clk.advance(99.0)
    # Reading again gives original value — the prior Clock was a throwaway.
    assert session.clock.t_hours == 5.0
    assert snap.clock_t_hours == 5.0


def test_session_advance_via_beat_persists_to_snapshot():
    snap = GameSnapshot()
    session = Session(snap)
    session.advance_via_beat(StoryBeat(kind=StoryBeatKind.ENCOUNTER, trigger="test"))
    assert snap.clock_t_hours == 1.0
    assert session.clock.t_hours == 1.0


def test_session_advance_via_beat_returns_duration():
    snap = GameSnapshot()
    session = Session(snap)
    duration = session.advance_via_beat(
        StoryBeat(kind=StoryBeatKind.TRAVEL, duration_hours=24.0, trigger="route-x")
    )
    assert duration == 24.0
    assert snap.clock_t_hours == 24.0


def test_session_advance_via_beat_emits_clock_advance_span(otel_capture):
    snap = GameSnapshot(clock_t_hours=10.0)
    session = Session(snap)
    session.advance_via_beat(
        StoryBeat(kind=StoryBeatKind.TRAVEL, duration_hours=24.0, trigger="route-x")
    )
    spans = [s for s in otel_capture.get_finished_spans() if s.name == "clock.advance"]
    assert len(spans) == 1
    assert spans[0].attributes["beat_kind"] == "travel"
    assert spans[0].attributes["t_before_h"] == 10.0
    assert spans[0].attributes["t_after_h"] == 34.0
    assert spans[0].attributes["trigger"] == "route-x"


def test_session_advance_via_beat_propagates_validation_errors():
    """Malformed beats raise ValueError from advance_clock_via_beat."""
    snap = GameSnapshot()
    session = Session(snap)
    with pytest.raises(ValueError, match="REST.*fixed at 8h"):
        session.advance_via_beat(
            StoryBeat(kind=StoryBeatKind.REST, duration_hours=4.0, trigger="catnap")
        )


def test_session_end_scene_advances_clock_by_one_hour(otel_capture):
    snap = GameSnapshot()
    session = Session(snap)
    session.end_scene("scene_end", turn=1)
    assert snap.clock_t_hours == 1.0
    spans = [s for s in otel_capture.get_finished_spans() if s.name == "clock.advance"]
    assert len(spans) == 1
    assert spans[0].attributes["beat_kind"] == "encounter"
    assert spans[0].attributes["trigger"] == "scene-scene_end"


def test_session_end_scene_emits_both_spans(otel_capture):
    """end_scene fires encounter.scratch_clear (existing) + clock.advance (new)."""
    snap = GameSnapshot()
    session = Session(snap)
    session.end_scene("scene_end", turn=1)
    span_names = {s.name for s in otel_capture.get_finished_spans()}
    assert "clock.advance" in span_names
    assert "encounter.scratch_clear" in span_names
```

- [ ] **Step 2: Add `otel_capture` fixture to `tests/server/conftest.py` if not already accessible from new test file**

The `tests/server/test_session_aggregate.py` test file lives under `tests/server/`, which already has `tests/server/conftest.py` defining `otel_capture` (verified at recon time, line 1062). No new fixture needed; pytest will discover it via the directory-scoped conftest.

- [ ] **Step 3: Run the tests to verify they fail (Session class does not yet exist)**

```bash
cd sidequest-server && uv run pytest tests/server/test_session_aggregate.py -v 2>&1 | tail -20
```

Expected: ImportError / ModuleNotFoundError on `sidequest.server.session`.

- [ ] **Step 4: Implement the `Session` class**

Create `sidequest-server/sidequest/server/session.py`:

```python
"""Per-slug Session aggregate — strangler-fig over the post-port server tier.

Owned by SessionRoom; constructed when the room's snapshot binds.
Reads/writes session state through GameSnapshot (the persistent boundary).

Today this class owns only the orbital clock and scene-end coordination.
Future migrations move more behavior inward one method at a time.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sidequest.orbital.beats import StoryBeat, StoryBeatKind, advance_clock_via_beat
from sidequest.orbital.clock import Clock
from sidequest.server.status_clear import clear_scratch_on_scene_end

if TYPE_CHECKING:
    from sidequest.game.session import GameSnapshot


class Session:
    """Per-slug behavior aggregate.

    Constructed by ``SessionRoom.bind_world`` (and any future re-bind
    paths) over the canonical ``GameSnapshot``. The snapshot is the
    persistence boundary; ``Session`` is a thin behavior layer over it.
    """

    def __init__(self, snapshot: GameSnapshot) -> None:
        self._snapshot = snapshot

    @property
    def clock(self) -> Clock:
        """Read-only Clock view over ``snapshot.clock_t_hours``.

        Mutations on the returned Clock do NOT persist. To advance the
        clock, call ``advance_via_beat`` (which validates the beat,
        emits the OTEL span, and writes back to the snapshot).
        """
        return Clock(t_hours=self._snapshot.clock_t_hours)

    def advance_via_beat(self, beat: StoryBeat) -> float:
        """Advance the clock per the beat. Persists to snapshot. Emits span."""
        local = Clock(t_hours=self._snapshot.clock_t_hours)
        duration = advance_clock_via_beat(local, beat)
        self._snapshot.clock_t_hours = local.t_hours
        return duration

    def end_scene(self, reason: str, *, turn: int) -> None:
        """Scene-end signal: scratch sweep first, then ENCOUNTER beat.

        Called by encounter-resolution sites (narrator beat resolution,
        dice resolution, yielded). The location_change site stays on
        ``clear_scratch_on_scene_end`` directly — not a scene end
        semantically.
        """
        clear_scratch_on_scene_end(self._snapshot, reason=reason, turn=turn)
        self.advance_via_beat(
            StoryBeat(kind=StoryBeatKind.ENCOUNTER, trigger=f"scene-{reason}")
        )
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_session_aggregate.py -v 2>&1 | tail -20
```

Expected: 10 tests pass.

- [ ] **Step 6: Commit**

```bash
git -C sidequest-server add sidequest/server/session.py tests/server/test_session_aggregate.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
feat(session): add Session aggregate over GameSnapshot

Per-slug behavior class. Owns the orbital Clock view and scene-end
coordination; reads/writes through GameSnapshot.clock_t_hours. No
own state — the snapshot is the persistence boundary.

end_scene calls clear_scratch_on_scene_end (existing free function)
then emits an ENCOUNTER StoryBeat. Both spans (encounter.scratch_clear
and clock.advance) fire on every scene-end so the GM panel sees a
complete signal.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md
§Components and §Testing.
EOF
)"
```

---

## Task C: `SessionRoom._session` binding + lifecycle tests

Wire `Session` construction into `SessionRoom.bind_world`. Add the `session` property with the not-yet-bound `RuntimeError`.

**Files:**
- Modify: `sidequest-server/sidequest/server/session_room.py`
- Create: `sidequest-server/tests/server/test_session_room_session_binding.py`

- [ ] **Step 1: Write the failing tests for the lifecycle**

Create `sidequest-server/tests/server/test_session_room_session_binding.py`:

```python
"""SessionRoom.session lifecycle tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.persistence import SqliteStore
from sidequest.game.session import GameSnapshot
from sidequest.protocol.messages import GameMode
from sidequest.server.session import Session
from sidequest.server.session_room import SessionRoom


def _make_room(slug: str = "test_world") -> SessionRoom:
    return SessionRoom(slug=slug, mode=GameMode.SOLO)


def test_session_property_raises_before_bind_world():
    room = _make_room()
    with pytest.raises(RuntimeError, match="Session not yet bound"):
        _ = room.session


def test_session_property_returns_session_after_bind_world(tmp_path: Path):
    room = _make_room()
    snap = GameSnapshot()
    store = SqliteStore(tmp_path / "t.db")
    room.bind_world(snap, store)
    assert isinstance(room.session, Session)
    # Same snapshot reference — Session reads through.
    assert room.session is room.session  # property is stable post-bind
    snap.clock_t_hours = 5.0
    assert room.session.clock.t_hours == 5.0


def test_session_advance_via_room_persists_to_room_snapshot(tmp_path: Path):
    """Advancing via room.session writes to room._snapshot."""
    from sidequest.orbital.beats import StoryBeat, StoryBeatKind

    room = _make_room()
    snap = GameSnapshot()
    store = SqliteStore(tmp_path / "t.db")
    room.bind_world(snap, store)

    room.session.advance_via_beat(
        StoryBeat(kind=StoryBeatKind.ENCOUNTER, trigger="test")
    )
    # The room's snapshot is the canonical reference.
    assert room.snapshot is snap
    assert snap.clock_t_hours == 1.0


def test_bind_world_is_idempotent_on_session(tmp_path: Path):
    """Second bind_world call (idempotent per existing semantics) does not rebuild Session."""
    room = _make_room()
    snap = GameSnapshot()
    store = SqliteStore(tmp_path / "t.db")
    room.bind_world(snap, store)
    s1 = room.session
    # Second call is a no-op per existing bind_world idempotency contract.
    room.bind_world(snap, store)
    s2 = room.session
    assert s1 is s2
```

If `GameMode.SOLO` is not the actual enum value (recon at room init didn't disambiguate `SOLO` vs `SINGLE_PLAYER`), use whichever value is canonical in the codebase — locate via:

```bash
grep -n "class GameMode\|GameMode\.[A-Z]" sidequest-server/sidequest/protocol/messages.py | head -5
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_session_room_session_binding.py -v 2>&1 | tail -20
```

Expected: FAIL — `room.session` is `AttributeError` (property not yet defined).

- [ ] **Step 3: Add `_session` field and binding to `SessionRoom`**

Edit `sidequest-server/sidequest/server/session_room.py`. Add to imports at the top:

```python
from sidequest.server.session import Session
```

Inside the `SessionRoom` dataclass body, add the field alongside the existing `_snapshot` / `_store` fields (around line 106 per recon):

```python
    _session: Session | None = field(default=None, init=False, repr=False)
```

Modify `bind_world` (around line 150-160 per recon) to construct the Session after the snapshot is bound. The existing body is:

```python
def bind_world(self, snapshot: GameSnapshot, store: SqliteStore) -> None:
    """..."""
    with self._lock:
        if self._snapshot is not None:
            return
        self._snapshot = snapshot
        self._store = store
```

Add one line at the end of the lock body:

```python
def bind_world(self, snapshot: GameSnapshot, store: SqliteStore) -> None:
    """..."""
    with self._lock:
        if self._snapshot is not None:
            return
        self._snapshot = snapshot
        self._store = store
        self._session = Session(snapshot)
```

Add a `session` property below the existing `snapshot` / `store` properties (around line 163-172 per recon):

```python
    @property
    def session(self) -> Session:
        """Per-slug Session aggregate. Raises if not yet bound to a world."""
        if self._session is None:
            raise RuntimeError(
                "Session not yet bound; call bind_world(snapshot, store) first."
            )
        return self._session
```

- [ ] **Step 4: Run the lifecycle tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_session_room_session_binding.py -v 2>&1 | tail -15
```

Expected: 4 tests pass.

- [ ] **Step 5: Run the server test suite to confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/server/ 2>&1 | tail -10
```

Expected: same pass/fail count as before this task; the existing 4 pre-existing failures persist; no new failures.

- [ ] **Step 6: Commit**

```bash
git -C sidequest-server add sidequest/server/session_room.py tests/server/test_session_room_session_binding.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
feat(session): SessionRoom binds Session in bind_world

The room is the canonical per-slug owner; bind_world is the single
snapshot binding point (idempotent). Session is constructed alongside
the snapshot and exposed via room.session, which raises a loud
RuntimeError if accessed before binding.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md
§Components.
EOF
)"
```

---

## Task D: `_SessionData._room` back-reference

Add a back-reference from `_SessionData` to its owning `SessionRoom` so any function with `sd` in scope can reach `room.session`. Wire population from the connect handler.

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` (add field to `_SessionData`)
- Modify: `sidequest-server/sidequest/handlers/connect.py` (pass `_room=room` into `_SessionData(...)` constructor at line ~618)

- [ ] **Step 1: Add `_room` field to `_SessionData`**

Edit `sidequest-server/sidequest/server/session_handler.py`. The class is at line 415. Add an import at the top of the file (near the other `from sidequest.server` imports):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.server.session_room import SessionRoom
```

(If a `TYPE_CHECKING` block already exists in this file, just append the import.)

Add the field on `_SessionData`. Place it after `store: SqliteStore` (around line 422 per recon) so it's grouped with the canonical-references block:

```python
    # Back-reference to the per-slug SessionRoom. Populated by the connect
    # handler at construction time so any function with `sd` in scope can
    # reach `sd._room.session`. Optional only because pre-slug-connect
    # paths construct _SessionData without a room — the slug-connect path
    # always sets this.
    _room: SessionRoom | None = None
```

The dataclass already uses default-factory and Optional patterns, so a `| None = None` default conforms.

- [ ] **Step 2: Pass `_room=room` from the connect handler**

Edit `sidequest-server/sidequest/handlers/connect.py`. The construction site is at line 618. The existing call is:

```python
session._session_data = _SessionData(
    genre_slug=row.genre_slug,
    world_slug=row.world_slug,
    player_name=display_name,
    player_id=player_id,
    snapshot=room.snapshot,
    store=room.store,
    genre_pack=genre_pack,
    orchestrator=shared_orchestrator,
    builder=builder,
    opening_seed=opening_seed,
    opening_directive=opening_directive,
    world_context=world_context,
    audio_backend=audio_backend,
    game_slug=slug,
    mode=GameMode(row.mode),
    image_pacing_throttle=(...)
)
```

Add the new kwarg `_room=room` alongside the other room-derived fields:

```python
session._session_data = _SessionData(
    genre_slug=row.genre_slug,
    ...
    snapshot=room.snapshot,
    store=room.store,
    _room=room,  # NEW — back-reference for downstream Session access
    genre_pack=genre_pack,
    ...
)
```

`room` is in scope at this site (set at line 231 earlier in the same handler). No other plumbing needed.

- [ ] **Step 3: Verify dataclass accepts the new field**

```bash
cd sidequest-server && uv run python -c "
from sidequest.server.session_handler import _SessionData
import inspect
fields = list(_SessionData.__dataclass_fields__.keys())
assert '_room' in fields, f'_room not in fields: {fields}'
print('OK — _room field present')
"
```

Expected: `OK — _room field present`.

- [ ] **Step 4: Run the broader server test suite to confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/server/ tests/integration/ 2>&1 | tail -10
```

Expected: same pass/fail count as before. No tests construct `_SessionData(...)` without the new optional field — the default `None` keeps the construction valid.

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/server/session_handler.py sidequest/handlers/connect.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
feat(session): _SessionData._room back-reference

Adds a back-reference from per-connection _SessionData to its owning
per-slug SessionRoom so any function with `sd` in scope can reach
`sd._room.session`. Populated at construction time in handlers/connect
(line 618) where `room` is already in scope.

Default None preserves backward compat for pre-slug-connect construction
paths; the slug-connect path always sets this.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md
§Components.
EOF
)"
```

---

## Task E.1: Front-door wiring — `handle_yield`

Add `room: SessionRoom` keyword-only argument to `handle_yield`; replace the scene-end call. Update the upstream caller at `handlers/yield_action.py:102`.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/yield_action.py`
- Modify: `sidequest-server/sidequest/handlers/yield_action.py`

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-server/tests/server/test_yield_action_session_wiring.py`:

```python
"""Wiring test: handle_yield advances the room's session clock on scene end."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.encounter import StructuredEncounter, EncounterActor
from sidequest.game.persistence import SqliteStore
from sidequest.game.session import GameSnapshot
from sidequest.protocol.messages import GameMode
from sidequest.server.dispatch.yield_action import handle_yield
from sidequest.server.session_room import SessionRoom


def _make_room_with_yield_ready_encounter(tmp_path: Path) -> tuple[SessionRoom, GameSnapshot]:
    """Set up a room/snapshot with a yieldable encounter and one player actor."""
    room = SessionRoom(slug="test_world", mode=GameMode.SOLO)
    snap = GameSnapshot()
    # Construct a minimal encounter with one player-side actor not yet withdrawn.
    actor = EncounterActor(
        name="TestActor",
        side="player",
        actor_kind="character",
        withdrawn=True,  # mark withdrawn so handle_yield finds the yielding actor
    )
    enc = StructuredEncounter(
        encounter_type="negotiation",
        actors=[actor],
        resolved=False,
    )
    snap.encounter = enc
    room.bind_world(snap, SqliteStore(tmp_path / "t.db"))
    return room, snap


def test_handle_yield_advances_session_clock(tmp_path, otel_capture):
    room, snap = _make_room_with_yield_ready_encounter(tmp_path)
    assert snap.clock_t_hours == 0.0

    handle_yield(snap, room=room, player_id="p1", player_name="TestActor")

    assert snap.clock_t_hours == 1.0
    span_names = {s.name for s in otel_capture.get_finished_spans()}
    assert "clock.advance" in span_names
    assert "encounter.scratch_clear" in span_names
```

If the encounter / actor field shapes differ from what's shown (the StructuredEncounter / EncounterActor signatures are inferred from earlier recon), inspect the actual classes:

```bash
grep -n "^class StructuredEncounter\|^class EncounterActor" sidequest-server/sidequest/game/encounter.py
```

…and adjust the test setup to match the real constructor. The shape of the encounter is incidental to the test; the assertion is purely on clock advancement.

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_yield_action_session_wiring.py -v 2>&1 | tail -20
```

Expected: FAIL — `handle_yield(...)` rejects `room=` kwarg (TypeError: unexpected keyword argument).

- [ ] **Step 3: Add `room` parameter to `handle_yield`**

Edit `sidequest-server/sidequest/server/dispatch/yield_action.py`. The function is at line 43.

Add an import near the top:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.server.session_room import SessionRoom
```

Modify the signature:

```python
def handle_yield(
    snapshot: GameSnapshot,
    *,
    room: SessionRoom,        # NEW — required keyword-only
    player_id: str,
    player_name: str,
) -> None:
```

Replace the existing scene-end call at line 107 (currently `from sidequest.server.status_clear import clear_scratch_on_scene_end` then `clear_scratch_on_scene_end(snapshot, reason="scene_end", turn=...)`):

```python
    # Yielded out of the encounter — scene ended for the party. Sweep
    # Scratch (Playtest 2026-04-26 Bug #1). Wound/Scar persist; this is
    # the same trigger as narrator-beat / dice-beat resolution.
    room.session.end_scene(
        "scene_end",
        turn=snapshot.turn_manager.interaction,
    )
```

Remove the `from sidequest.server.status_clear import clear_scratch_on_scene_end` line if it appears only here (grep within the file to confirm before removing the import).

- [ ] **Step 4: Update the caller at `handlers/yield_action.py:102`**

Edit `sidequest-server/sidequest/handlers/yield_action.py`. The call site is at line 102. Existing:

```python
handle_yield(sd.snapshot, player_id=player_id, player_name=player_name)
```

Update:

```python
handle_yield(sd.snapshot, room=sd._room, player_id=player_id, player_name=player_name)
```

`sd._room` is reachable here because `_SessionData._room` is populated by the connect handler (Task D). If `sd._room` is `None` at this site (only possible if the slug-connect branch was bypassed — e.g., legacy non-slug-connect paths), the immediate `room.session` access in `handle_yield` will fail loudly with `AttributeError: 'NoneType' object has no attribute 'session'`. Acceptable per "No Silent Fallbacks" — surfaces a real wiring bug.

If we want a more explicit error, wrap the caller:

```python
if sd._room is None:
    return [_error_msg("Internal error: session not bound to a room")]
handle_yield(sd.snapshot, room=sd._room, player_id=player_id, player_name=player_name)
```

Use the explicit guard form — it produces a structured error to the client instead of a stack trace.

- [ ] **Step 5: Run the wiring test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/server/test_yield_action_session_wiring.py -v 2>&1 | tail -15
```

Expected: 1 test passes.

- [ ] **Step 6: Run any existing yield_action tests to confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/ -k "yield" -v 2>&1 | tail -20
```

Expected: existing yield tests must update if they call `handle_yield` directly. If they fail, update each call site to pass `room=` kwarg (likely needs a `SessionRoom` fixture in those tests). If existing yield tests currently call through `HANDLER.handle()` rather than `handle_yield()` directly, no test-level change needed — only the handler's internal call site changed.

- [ ] **Step 7: Commit**

```bash
git -C sidequest-server add \
    sidequest/server/dispatch/yield_action.py \
    sidequest/handlers/yield_action.py \
    tests/server/test_yield_action_session_wiring.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
feat(session): wire handle_yield through Session.end_scene

handle_yield gains a required room: SessionRoom kwarg. Caller in
handlers/yield_action.py passes sd._room, with a structured error
guard for the (theoretically-impossible-in-slug-connect) None path.

Replaces the direct clear_scratch_on_scene_end call with
room.session.end_scene("scene_end", turn=...) so every yield-out
encounter resolution emits both encounter.scratch_clear (existing)
and clock.advance (new).

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md
§Components and §Testing.
EOF
)"
```

---

## Task E.2: Front-door wiring — `_apply_narration_result_to_snapshot`

Add `room: SessionRoom` keyword-only argument; replace the scene-end call at line 1443. Update the caller at `websocket_session_handler.py:1597`. The location-change site at line 654 stays untouched.

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py`
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py`

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-server/tests/server/test_narration_apply_session_wiring.py`:

```python
"""Wiring test: _apply_narration_result_to_snapshot fires scene-end through Session."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sidequest.game.persistence import SqliteStore
from sidequest.game.session import GameSnapshot
from sidequest.protocol.messages import GameMode
from sidequest.server.narration_apply import _apply_narration_result_to_snapshot
from sidequest.server.session_room import SessionRoom


@dataclass
class _StubResult:
    """Minimal stand-in for narration result that triggers scene_end path."""
    # Fields populated to walk the encounter-resolution branch in
    # _apply_narration_result_to_snapshot. The exact shape comes from the
    # production result type — the test author identifies which fields
    # the line-1443 branch reads (final_player_metric, encounter_resolved,
    # location, status_changes — verified at impl time via grep).
    location: str | None = None
    encounter_resolved_via_narrator_beat: bool = True
    # ... (extend with whatever the actual branch reads)


def test_narration_apply_advances_clock_on_scene_end(tmp_path, otel_capture):
    """Narrator-beat-resolved encounter triggers Session.end_scene path."""
    # NOTE: This test requires a representative narration result that walks
    # the line-1443 branch. The implementer should:
    # 1. Read the branch condition surrounding line 1443 to identify which
    #    result fields gate the scene_end emission.
    # 2. Construct a result fixture (real type or test stub) that satisfies
    #    those conditions.
    # 3. Construct a snapshot with a matching encounter to satisfy the
    #    branch's pre-conditions.
    pytest.skip(
        "Implementer: construct fixture once branch conditions for line "
        "1443 are mapped. Skeleton in place; complete before commit."
    )
```

This test is intentionally a skip+TODO at this step — the line-1443 branch has rich pre-conditions (encounter resolution via narrator beat) that need codebase-specific fixtures. Step 3 below maps the branch and replaces the skip with a real assertion.

- [ ] **Step 2: Map the line-1443 branch conditions**

Read `sidequest-server/sidequest/server/narration_apply.py` lines 1430–1450 to identify:
- The enclosing branch condition (what makes the code reach line 1443?)
- The pre-condition fields on `result` and `snapshot.encounter` that gate this path.

Write the branch conditions into the test. Replace the `pytest.skip(...)` with a real fixture and assertion that mirrors the production branch:

```python
def test_narration_apply_advances_clock_on_scene_end(tmp_path, otel_capture):
    room = SessionRoom(slug="test_world", mode=GameMode.SOLO)
    snap = GameSnapshot()
    # ... set up encounter + result that walks the line-1443 branch
    room.bind_world(snap, SqliteStore(tmp_path / "t.db"))

    _apply_narration_result_to_snapshot(
        snap,
        result,
        "TestPlayer",
        room=room,
        pack=None,
        # ...
    )

    span_names = {s.name for s in otel_capture.get_finished_spans()}
    assert "clock.advance" in span_names
    assert snap.clock_t_hours == 1.0
```

Also add a complementary test that the location-change path at line 654 does NOT advance the clock:

```python
def test_narration_apply_does_not_advance_clock_on_location_change(tmp_path, otel_capture):
    """Walking to a new room is not a scene end; clock must stay at 0."""
    room = SessionRoom(slug="test_world", mode=GameMode.SOLO)
    snap = GameSnapshot()
    # ... set up result with a new location and an existing snapshot location
    room.bind_world(snap, SqliteStore(tmp_path / "t.db"))

    _apply_narration_result_to_snapshot(snap, result, "TestPlayer", room=room, ...)

    assert snap.clock_t_hours == 0.0
    span_names = {s.name for s in otel_capture.get_finished_spans()}
    assert "clock.advance" not in span_names
    # encounter.scratch_clear DOES still fire on location_change because
    # clear_scratch_on_scene_end is called directly at line 654.
    assert "encounter.scratch_clear" in span_names
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_narration_apply_session_wiring.py -v 2>&1 | tail -15
```

Expected: FAIL — function rejects `room=` kwarg.

- [ ] **Step 4: Add `room` parameter to `_apply_narration_result_to_snapshot`**

Edit `sidequest-server/sidequest/server/narration_apply.py`. Function signature is at line 488 per recon. Add `room: SessionRoom` as a required keyword-only argument:

```python
def _apply_narration_result_to_snapshot(
    snapshot: GameSnapshot,
    result: object,
    player_name: str,
    *,
    room: SessionRoom,                    # NEW
    pack: GenrePack | None = None,
    dice_failed: bool | None = None,
    dice_actor: str | None = None,
    from_explicit_action: bool = False,
    opposed_player_d20: int | None = None,
    opposed_player_beat_id: str | None = None,
    opposed_player_actor: str | None = None,
) -> NarrationApplyOutcome:
```

Add the import at the top of the file (under the existing imports):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.server.session_room import SessionRoom
```

(If a `TYPE_CHECKING` block already exists, append.)

- [ ] **Step 5: Replace the scene-end call at line 1443**

The existing block at lines 1438–1448:

```python
                    # Scratch sweep at encounter resolution. Encounter end
                    # is the canonical "scene end" trigger that the Scratch
                    # severity tier promises in game/status.py — without
                    # this sweep, Scratches accumulate forever (Bug #1).
                    from sidequest.server.status_clear import (
                        clear_scratch_on_scene_end,
                    )
                    clear_scratch_on_scene_end(
                        snapshot,
                        reason="scene_end",
                        turn=turn_num,
                    )
                    break
```

Becomes:

```python
                    # Scratch sweep at encounter resolution. Encounter end
                    # is the canonical "scene end" trigger that the Scratch
                    # severity tier promises in game/status.py — without
                    # this sweep, Scratches accumulate forever (Bug #1).
                    # Now also advances the story-time clock via Session.
                    room.session.end_scene("scene_end", turn=turn_num)
                    break
```

The `from sidequest.server.status_clear import clear_scratch_on_scene_end` is still needed for the location-change site at line 654, so do NOT remove the import — just remove this one local re-import block.

- [ ] **Step 6: Update the caller at `websocket_session_handler.py:1597`**

Edit `sidequest-server/sidequest/server/websocket_session_handler.py`. The call site at line 1597 currently has:

```python
                    _apply_narration_result_to_snapshot(
                        snapshot,
                        result,
                        sd.player_name,
                        pack=sd.genre_pack,
                        dice_failed=dice_failed,
                        ...
                    )
```

Update to pass `room=sd._room`:

```python
                    if sd._room is None:
                        # Slug-connect branch always sets _room; this is a
                        # programming-error path. Surface as a hard error.
                        raise RuntimeError(
                            "_apply_narration_result_to_snapshot: sd._room "
                            "is None — slug-connect wiring missing"
                        )
                    _apply_narration_result_to_snapshot(
                        snapshot,
                        result,
                        sd.player_name,
                        room=sd._room,
                        pack=sd.genre_pack,
                        dice_failed=dice_failed,
                        ...
                    )
```

- [ ] **Step 7: Run the wiring tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_narration_apply_session_wiring.py -v 2>&1 | tail -15
```

Expected: both tests pass (encounter-resolution advances clock; location-change does not).

- [ ] **Step 8: Run existing narration_apply tests to confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/ -k "narration_apply or narration_result" -v 2>&1 | tail -20
```

Expected: existing tests pass. If any test directly calls `_apply_narration_result_to_snapshot(...)` without `room=`, update those test setups to construct a fresh `SessionRoom` and pass `room=room`. (`_apply_narration_result_to_snapshot` is module-private but is exported via `session_handler.py:566` `__all__` per recon — so direct callers from tests are likely.)

- [ ] **Step 9: Commit**

```bash
git -C sidequest-server add \
    sidequest/server/narration_apply.py \
    sidequest/server/websocket_session_handler.py \
    tests/server/test_narration_apply_session_wiring.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
feat(session): wire narration_apply scene-end through Session.end_scene

_apply_narration_result_to_snapshot gains a required room: SessionRoom
kwarg. The encounter-resolution path at line 1443 now calls
room.session.end_scene("scene_end", turn=...) instead of the local
clear_scratch_on_scene_end import. The location-change path at line 654
is intentionally untouched — walking to a new room is not a scene end.

Caller at websocket_session_handler.py:1597 passes sd._room with a
structured error guard. Existing test call sites updated to thread a
SessionRoom fixture through.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md.
EOF
)"
```

---

## Task E.3: Front-door wiring — `DiceThrowHandler.handle`

Replace the scene-end call at `handlers/dice_throw.py:162`. The handler already has `session: WebSocketSessionHandler` in scope, and `sd._room` is now populated.

**Files:**
- Modify: `sidequest-server/sidequest/handlers/dice_throw.py`

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-server/tests/server/test_dice_throw_session_wiring.py`:

```python
"""Wiring test: dice_throw resolution advances the room's session clock."""
from __future__ import annotations

import pytest


def test_dice_throw_advances_clock_on_encounter_resolved():
    """Encounter-resolved dice outcome → clock advances + spans fire.

    NOTE: DiceThrowHandler.handle is async and consumes a full
    WebSocketSessionHandler with bound _SessionData and _room. Setting
    this up requires either:
      (a) a session-wide harness fixture (existing test_dice_throw_*
          tests in tests/server/ likely have one), or
      (b) a direct call to the inner dispatch path that the handler
          delegates to.

    Implementer: locate an existing dice_throw test fixture pattern
    (grep tests/server for 'DiceThrowHandler' or 'dispatch_dice_throw')
    and reuse it. The assertion is unchanged: after a resolved dice
    throw, room._snapshot.clock_t_hours == 1.0 and clock.advance span
    fires.
    """
    pytest.skip(
        "Implementer: reuse existing dice_throw test fixture pattern. "
        "Replace skip with assertion: clock_t_hours advanced, spans fired."
    )
```

This test is the hardest of the three because the dice flow is async + handler-driven. Step 2 maps the existing test pattern.

- [ ] **Step 2: Locate the existing dice_throw test pattern**

```bash
grep -rln "DiceThrowHandler\|dispatch_dice_throw\b" sidequest-server/tests --include="*.py"
```

Read one of the existing tests to identify the harness fixture (likely in `tests/server/conftest.py` or inline). Use the same fixture in the new test, replacing the skip with the actual assertion:

```python
@pytest.mark.asyncio
async def test_dice_throw_advances_clock_on_encounter_resolved(
    # ... existing dice_throw fixtures from server/conftest.py
    otel_capture,
):
    # ... set up snapshot with active encounter and roll-ready actor
    # ... drive DiceThrowHandler.handle with a resolved-encounter outcome
    # ... assert
    assert sd._room.session.clock.t_hours == 1.0
    span_names = {s.name for s in otel_capture.get_finished_spans()}
    assert "clock.advance" in span_names
```

If no existing dice_throw test pattern exists (unlikely given the codebase has `dice_throw.py`), document the gap as a follow-up and skip this wiring test until E2E (Task F) can cover it.

- [ ] **Step 3: Run the test to verify it fails (or skips)**

```bash
cd sidequest-server && uv run pytest tests/server/test_dice_throw_session_wiring.py -v 2>&1 | tail -10
```

Expected: FAIL — `sd._room.session.end_scene` not called yet (or skip if fixture pattern not yet ported).

- [ ] **Step 4: Replace the scene-end call at `handlers/dice_throw.py:162`**

Edit `sidequest-server/sidequest/handlers/dice_throw.py`. The existing block at line 158–168:

```python
        if outcome.encounter_resolved:
            from sidequest.server.status_clear import clear_scratch_on_scene_end

            clear_scratch_on_scene_end(
                snapshot,
                reason="scene_end",
                turn=snapshot.turn_manager.interaction,
            )
```

Becomes:

```python
        if outcome.encounter_resolved:
            if sd._room is None:
                # Slug-connect branch always sets _room; this is a
                # programming-error path. Surface as a hard error.
                raise RuntimeError(
                    "DiceThrowHandler: sd._room is None — slug-connect "
                    "wiring missing"
                )
            sd._room.session.end_scene(
                "scene_end",
                turn=snapshot.turn_manager.interaction,
            )
```

Remove the local `from sidequest.server.status_clear import clear_scratch_on_scene_end` line — `clear_scratch_on_scene_end` is no longer called from this site.

- [ ] **Step 5: Run the wiring test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/server/test_dice_throw_session_wiring.py -v 2>&1 | tail -15
```

Expected: 1 test passes (or remains a skip with a follow-up note if the fixture port was deferred).

- [ ] **Step 6: Run existing dice_throw tests to confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/ -k "dice_throw" -v 2>&1 | tail -20
```

Expected: existing tests still pass. The handler's external behavior is unchanged — it still emits scene-end signals on encounter resolution, just through a different code path.

- [ ] **Step 7: Commit**

```bash
git -C sidequest-server add \
    sidequest/handlers/dice_throw.py \
    tests/server/test_dice_throw_session_wiring.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
feat(session): wire dice_throw scene-end through Session.end_scene

DiceThrowHandler.handle now calls sd._room.session.end_scene("scene_end",
turn=...) when outcome.encounter_resolved, replacing the direct
clear_scratch_on_scene_end import. Structured RuntimeError if sd._room
is None (slug-connect branch always sets it).

This is the third and final scene-end call site to migrate to the
front-door pattern. The location-change site in narration_apply.py:654
stays on the free function (not a scene end semantically).

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md.
EOF
)"
```

---

## Task F: E2E wiring test

Drive a real `WebSocketSessionHandler` through a scene-end and assert that the snapshot's clock advanced and spans fired. CLAUDE.md mandates a wiring test per test suite — this is the integration test that proves the strangler-fig is actually consumed by production code paths.

**Files:**
- Create: `sidequest-server/tests/integration/test_session_clock_e2e.py`

- [ ] **Step 1: Locate an existing integration test pattern**

```bash
ls sidequest-server/tests/integration/
grep -rln "WebSocketSessionHandler\|attach_room_context\|RoomRegistry" sidequest-server/tests/integration --include="*.py"
```

Use the same fixture/harness pattern as an existing integration test that exercises a full session lifecycle. The most likely candidate is `tests/integration/test_dogfight_playtest_smoke.py` (per recon — it uses InMemorySpanExporter and drives a real session).

- [ ] **Step 2: Write the integration test**

Create `sidequest-server/tests/integration/test_session_clock_e2e.py`. Use the existing harness from a dogfight or chargen integration test as a base:

```python
"""End-to-end wiring test: scene-end advances Session clock + emits spans.

Drives a real WebSocketSessionHandler through a scene-end-producing
event (yield, dice resolution, or narrator beat resolution — whichever
has the simplest harness in the existing integration tests). Asserts
the snapshot clock advanced and both clock.advance and
encounter.scratch_clear spans fired.

Mandated wiring test per CLAUDE.md ("Every Test Suite Needs a Wiring
Test"): proves the Session strangler-fig is reachable from production
code paths, not just unit-tested in isolation.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_session_clock_advances_through_yield_e2e(otel_capture, tmp_path):
    """Pick the simplest of the three migrated paths (yield, narration_apply,
    dice_throw) for E2E. Yield is the simplest — single message, single
    handler, no narrator round-trip.

    Reuse the SessionRoom + WebSocketSessionHandler fixture pattern from
    one of the existing integration tests. The implementer maps the
    fixture name(s) at impl time.
    """
    pytest.skip(
        "Implementer: reuse the integration-harness pattern from "
        "test_dogfight_playtest_smoke or similar. Drive a YIELD message "
        "through the WebSocketSessionHandler flow and assert: "
        "(1) room._snapshot.clock_t_hours == 1.0; "
        "(2) clock.advance span recorded; "
        "(3) encounter.scratch_clear span recorded."
    )
```

Map the fixture pattern from the existing integration test, then replace the skip with the real test body. The assertion is the load-bearing part:

```python
assert room._snapshot.clock_t_hours == pytest.approx(1.0)
span_names = {s.name for s in otel_capture.get_finished_spans()}
assert "clock.advance" in span_names
assert "encounter.scratch_clear" in span_names

clock_span = next(s for s in otel_capture.get_finished_spans() if s.name == "clock.advance")
assert clock_span.attributes["beat_kind"] == "encounter"
assert clock_span.attributes["trigger"] == "scene-scene_end"
```

- [ ] **Step 3: Run the integration test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/integration/test_session_clock_e2e.py -v 2>&1 | tail -15
```

Expected: 1 test passes (after replacing the skip with the real harness).

- [ ] **Step 4: Commit**

```bash
git -C sidequest-server add tests/integration/test_session_clock_e2e.py && \
git -C sidequest-server commit -m "$(cat <<'EOF'
test(session): E2E wiring test — scene-end through Session

Drives a real WebSocketSessionHandler through a scene-end via the YIELD
path (simplest of the three migrated handlers — no narrator round-trip).
Asserts clock_t_hours moved and both clock.advance + encounter.scratch_clear
spans fired.

Mandated wiring test per CLAUDE.md: proves the Session strangler-fig is
reachable from production code paths, not just unit-tested in isolation.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md
§Testing.
EOF
)"
```

---

## Task G: Final test pass + cross-test verification

Run the full server test suite and integration suite. Confirm we haven't broken anything outside the scope of this plan.

- [ ] **Step 1: Run the full server test suite**

```bash
cd sidequest-server && uv run pytest 2>&1 | tail -20
```

Expected: pass count is +N (where N = total new tests added across Tasks 0–F: ~3 persistence + 10 session aggregate + 4 lifecycle + 1 yield wiring + 2 narration wiring + 1 dice wiring + 1 e2e = ~22 new tests). Existing failures unchanged (4 pre-existing failures from the orbital-map plan Task 0 baseline are still present and still unrelated).

- [ ] **Step 2: Run the orbital test suite to confirm rename is clean**

```bash
cd sidequest-server && uv run pytest tests/orbital/ -v 2>&1 | tail -10
```

Expected: 36 tests pass (no behavioral change from the rename).

- [ ] **Step 3: Verify no leftover `clear_scratch_on_scene_end` calls in scene_end paths**

```bash
grep -rn "clear_scratch_on_scene_end" sidequest-server/sidequest --include="*.py" | grep -v test
```

Expected: only the location-change site in `narration_apply.py:654` and the function definition in `status_clear.py` itself. Three other call sites should be gone.

- [ ] **Step 4: Run client + daemon test suites for completeness**

```bash
cd /Users/slabgorb/Projects/oq-2 && just client-test 2>&1 | tail -10
cd /Users/slabgorb/Projects/oq-2 && just daemon-test 2>&1 | tail -10
```

Expected: same pass/fail count as before this plan started (no client or daemon code touched). If anything regressed, the change is out of scope and must be investigated.

- [ ] **Step 5: Update the orbital-map plan's Task 5 entry**

Edit `docs/superpowers/plans/2026-05-01-orbital-map-tracks-a-b.md`. Replace the body of `## Task 5: Wire beat advances into rest + encounter flows` with a pointer to this plan:

```markdown
## Task 5: Wire beat advances into scene-end flows (revised)

**This task has been replaced by a separate strangler-fig plan.**

The original Task 5 assumed a `Session` class with `Session.empty()`,
`session.handle_rest()`, and `session.end_scene()` — none of which
existed in the post-port server. Discovery during execution surfaced
that `sidequest/game/session.py` is misnamed (contains `GameSnapshot`,
not `Session`), scene-end is a free function called from three sites,
and there is no rest-as-a-behavior implementation.

The revised Task 5 work is in:

→ **`docs/superpowers/plans/2026-05-01-session-aggregate-strangler.md`**

Scope changes from the original Task 5:
- Adds a strangler-fig `Session` class to give the orbital aggregate a
  real Python home before wiring.
- Migrates *only* scene-end (encounter resolution) sites; rest-beat
  emission is deferred until rest-as-a-behavior exists in the post-port
  server.
- Renames orbital `BeatKind`/`Beat` → `StoryBeatKind`/`StoryBeat` to
  disambiguate from the existing combat momentum `BeatKind`.

Resume Task 6 (Pydantic models for orbits.yaml + chart.yaml) once the
strangler plan is complete.
```

- [ ] **Step 6: Commit the plan-pointer update**

```bash
cd /Users/slabgorb/Projects/oq-2 && \
git add docs/superpowers/plans/2026-05-01-orbital-map-tracks-a-b.md && \
git commit -m "$(cat <<'EOF'
docs(plan): point orbital-map Task 5 to strangler plan

Original Task 5 assumed a Session class that did not exist in the
post-port server. Replaces the task body with a pointer to the new
strangler-fig implementation plan, which builds the Session class
before wiring scene-end coordination through it.

Per spec docs/superpowers/specs/2026-05-01-session-aggregate-design.md.
EOF
)"
```

---

## Self-Review Checklist (run after writing the plan)

The author of this plan ran the following self-review:

**1. Spec coverage:**
- [x] §Architecture (Session lives on SessionRoom): Tasks B, C
- [x] §Data Flow (read/mutate/scene-end/persistence paths): Tasks A, B
- [x] §Components (Session class, GameSnapshot field, _SessionData._room, SessionRoom binding, function signatures, call site updates, BeatKind rename): Pre-task 0, Tasks A–E
- [x] §Error Handling (RuntimeError on unbound, malformed beat ValueError, kwarg TypeError, read-only invariant, legacy save default): Tasks B, C, E
- [x] §Testing (Session unit, lifecycle, three wiring tests, persistence, e2e): Tasks A, B, C, E.1, E.2, E.3, F

**2. Placeholder scan:** Two skipped-by-default tests in Tasks E.2, E.3, F intentionally include `pytest.skip(...)` with explicit "Implementer:" instructions to map test fixtures from existing patterns at impl time. The skips are temporary — Step 2 of each task replaces the skip with a real assertion. Acceptable per the plan's constraint that the line-1443 narration branch and the dice_throw async harness require codebase-specific fixtures that are cheaper to map at write-time than to predict here. Every skip has explicit unblock instructions.

No `TBD`, `TODO`, `implement later`, or vague "add error handling" phrasing in any production code step.

**3. Type consistency:**
- `Session.advance_via_beat(beat: StoryBeat) -> float` consistent across Tasks B, C, E.1–E.3, F
- `Session.end_scene(self, reason: str, *, turn: int) -> None` consistent across Tasks B, E.1–E.3, F
- `_SessionData._room: SessionRoom | None = None` field name consistent across Tasks D, E.1–E.3
- `SessionRoom.session` property consistent across Tasks C, E.1–E.3, F
- `StoryBeat`/`StoryBeatKind` rename applied consistently in Pre-task 0 and onwards
- `clock_t_hours: float` field on GameSnapshot consistent across Tasks A, B, C

No issues.

---

## Execution

**Plan complete and saved to `docs/superpowers/plans/2026-05-01-session-aggregate-strangler.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task with two-stage review between tasks (spec-compliance + code-review). Best for this plan because Tasks E.1–E.3 each touch multiple production files and benefit from focused implementer + reviewer attention.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch with checkpoints for review at task boundaries. Faster but pollutes the controller's context with task-by-task implementation detail.

**Which approach?**
