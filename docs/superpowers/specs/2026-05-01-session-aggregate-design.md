# Session Aggregate — Strangler-Fig Over the Post-Port Server Tier

**Date:** 2026-05-01
**Status:** Accepted (per brainstorm 2026-05-01)
**Drives:** revised Task 5 of `docs/superpowers/plans/2026-05-01-orbital-map-tracks-a-b.md`
**Related:** ADR-067 (unified narrator), ADR-038 (WebSocket transport), ADR-082 (Rust→Python port)

---

## Summary

The post-port Python server has a "Rust accent" — `sidequest/game/session.py` is named for a `Session` class it doesn't contain (it holds `GameSnapshot` and a pile of state pydantic models), scene-end is a free function `clear_scratch_on_scene_end()` called from three sites, and per-session state is split across `_SessionData` (per-connection), `SessionRoom` (per-slug), and `WebSocketSessionHandler` (per-WS-connection). There is no canonical "session object" with behavior.

The orbital-map plan (Tasks 5–17) needs a per-slug aggregate that owns a story-time clock, coordinates scene-end signals, and exposes orbital scope state to the renderer. Task 5 of that plan assumed a `Session` class with `Session.empty()`, `session.clock`, `session.handle_rest()`, `session.end_scene()` — none of which exist.

This spec introduces a narrow `Session` class as a strangler-fig: a new per-slug aggregate that lives alongside (not replacing) the existing tier, owns only what Task 5 needs today, and establishes a migration pattern for future inward-moving behavior.

## Goals

- Unblock orbital-map Task 5 with a real Python home for the clock + scene-end coordination.
- Establish a strangler-fig pattern: new behavior aggregate over existing data layer.
- Keep `GameSnapshot` as the persistence boundary; add exactly one new field.
- Preserve all existing scene-end semantics (scratch sweep on encounter resolution and location change still happens).

## Non-Goals

- **No** refactor of `_SessionData`, `SessionRoom`, `WebSocketSessionHandler`, or `GameSnapshot` beyond the single new field.
- **No** removal of `clear_scratch_on_scene_end()` — it becomes an implementation detail of `Session.end_scene` for scene-end sites; it remains the direct call for the location-change site.
- **No** rest-as-a-behavior implementation (no caller exists in the post-port server; deferred until a rest action is built).
- **No** rename of `sidequest/game/session.py` → `snapshot.py` (the file is misnamed, but renaming is its own change).

## Architecture

A new class `Session` lives in `sidequest-server/sidequest/server/session.py` (new file, no collision with the existing misnamed `sidequest/game/session.py`).

```
SessionRoom (per-slug, existing)
├── _snapshot: GameSnapshot                  ← existing; gains one field: clock_t_hours
├── _store: SqliteStore                      ← existing
├── _orchestrator: Orchestrator              ← existing
├── _session: Session | None                 ← NEW — bound when _snapshot is bound
├── ...
```

**Module layering:** `sidequest/orbital/` owns the primitives (clock, beats, display) — pure, no upward imports. `sidequest/server/session.py` holds the new aggregate, can import from `orbital/` (primitives) and `server/status_clear` (existing scene-end side effect). This keeps `orbital/` reusable by CLIs and tests without dragging in server tier.

**Strangler boundary:** `Session` is the new per-slug aggregate. `_SessionData` (per-connection) and `WebSocketSessionHandler` are unchanged except for one back-reference to the room. `GameSnapshot` gains exactly one field. Free functions stay; they become implementation details called by Session methods.

## Data Flow

### Read — `room.session.clock.t_hours`

`Session.clock` is a property returning a *fresh* `Clock` instance with `t_hours` read from `snapshot.clock_t_hours`. Read-only view: calling `.advance(x)` on the returned Clock mutates a throwaway and does not persist. Documented invariant; verified by test.

### Mutate — `room.session.advance_via_beat(beat)`

```
local = Clock(t_hours=snapshot.clock_t_hours)
duration = advance_clock_via_beat(local, beat)   # validation + emit clock.advance span
snapshot.clock_t_hours = local.t_hours
return duration
```

The existing `advance_clock_via_beat()` does the validation, mutation, and OTEL emission. `Session.advance_via_beat` is a thin adapter that handles the snapshot read/write around it.

### Scene-end — `room.session.end_scene(reason, *, turn)`

```
clear_scratch_on_scene_end(snapshot, reason=reason, turn=turn)
self.advance_via_beat(StoryBeat(kind=ENCOUNTER, trigger=f"scene-{reason}"))
```

Scratch sweep first (existing semantics preserved), beat emit second. The OTEL dashboard sees both spans for every scene-end: `encounter.scratch_clear` (existing) and `clock.advance` (new).

### Persistence

`GameSnapshot` is a pydantic `BaseModel`; the existing `SqliteStore` save/load path serializes the full model. Adding `clock_t_hours: float = Field(default=0.0)` gives free persistence. Old saves load with the default 0.0 (acceptable per project memory: legacy saves are throwaway, no backward-compat ceremony needed).

## Components

### New file: `sidequest/server/session.py`

```python
"""Per-slug Session aggregate — strangler-fig over the post-port server tier.

Owned by SessionRoom. Reads/writes session state through GameSnapshot
(the persistent boundary). Today this class owns only the orbital clock
and scene-end coordination.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sidequest.orbital.beats import StoryBeat, StoryBeatKind, advance_clock_via_beat
from sidequest.orbital.clock import Clock
from sidequest.server.status_clear import clear_scratch_on_scene_end

if TYPE_CHECKING:
    from sidequest.game.session import GameSnapshot


class Session:
    """Per-slug behavior aggregate. Constructed by SessionRoom when snapshot binds."""

    def __init__(self, snapshot: GameSnapshot) -> None:
        self._snapshot = snapshot

    @property
    def clock(self) -> Clock:
        """Read-only Clock view over snapshot.clock_t_hours.

        Mutations on the returned Clock do NOT persist — use advance_via_beat.
        """
        return Clock(t_hours=self._snapshot.clock_t_hours)

    def advance_via_beat(self, beat: StoryBeat) -> float:
        local = Clock(t_hours=self._snapshot.clock_t_hours)
        duration = advance_clock_via_beat(local, beat)
        self._snapshot.clock_t_hours = local.t_hours
        return duration

    def end_scene(self, reason: str, *, turn: int) -> None:
        """Scene-end signal — scratch sweep first, then ENCOUNTER beat.

        Called by encounter-resolution sites (narrator beat, dice resolution,
        yielded). The location_change site stays on clear_scratch_on_scene_end
        directly — not a scene end semantically.
        """
        clear_scratch_on_scene_end(self._snapshot, reason=reason, turn=turn)
        self.advance_via_beat(
            StoryBeat(kind=StoryBeatKind.ENCOUNTER, trigger=f"scene-{reason}")
        )
```

### `GameSnapshot` field addition (`sidequest/game/session.py`)

```python
clock_t_hours: float = Field(
    default=0.0,
    description="Story-time hours; advanced by Session.advance_via_beat.",
)
```

### `_SessionData` field addition (`sidequest/server/session_handler.py`)

```python
# Populated by WebSocketSessionHandler.attach_room_context
_room: SessionRoom | None = None
```

### `WebSocketSessionHandler.attach_room_context` extension

After binding `self._room`, also set `self._session_data._room = self._room` if `_session_data` is not `None`. The exact lifecycle (which is bound first) needs implementation-time verification; the implementation plan must include an explicit ordering check.

### `SessionRoom` extension (`sidequest/server/session_room.py`)

```python
# New field on the existing dataclass:
_session: Session | None = field(default=None, init=False, repr=False)

# Bind alongside existing snapshot binding (existing entry point identified at impl time):
def _bind_snapshot(self, snapshot: GameSnapshot) -> None:
    self._snapshot = snapshot
    self._session = Session(snapshot)

@property
def session(self) -> Session:
    if self._session is None:
        raise RuntimeError("Session not yet bound; call _bind_snapshot first.")
    return self._session
```

The exact existing snapshot-binding entry on `SessionRoom` is identified during implementation. There may be more than one; all paths that bind `_snapshot` must also bind `_session`.

### Function signature updates (front-door wiring)

Three functions add a required `room: SessionRoom` keyword-only argument:

| File | Function | Existing signature change |
|---|---|---|
| `server/narration_apply.py:488` | `_apply_narration_result_to_snapshot` | adds `*, room: SessionRoom` |
| `server/dispatch/yield_action.py:43` | `handle_yield` | adds `*, room: SessionRoom` |
| `handlers/dice_throw.py` | `DiceThrowHandler.handle` | already has `sd: _SessionData`; uses `sd._room.session.end_scene(...)` |

Callers update by threading `room` through. Each caller already has the WebSocketSessionHandler / `_SessionData` and can grab `_room` (or a direct `room` parameter is added one level up if not).

### Call site updates

Three sites switch from `clear_scratch_on_scene_end(...)` to `room.session.end_scene(reason, turn=...)`:

- `narration_apply.py:1443` (`reason="scene_end"` — encounter resolved via narrator beat)
- `dispatch/yield_action.py:107` (`reason="scene_end"` — yielded out of encounter)
- `handlers/dice_throw.py:162` (`reason="scene_end"` — encounter resolved via dice)

**Untouched** (location-change is not a scene end semantically; no story-time beat fires):

- `narration_apply.py:654` (`reason="location_change"` — party walked to a new room)

### Rename `BeatKind`/`Beat` → `StoryBeatKind`/`StoryBeat`

The existing `sidequest/game/beat_kinds.py:BeatKind` (combat momentum: `strike|brace|push|angle`) is older and broader; renaming it would touch combat dispatch and is out of scope for orbital-map work. The new orbital `BeatKind` (story-time: `encounter|rest|travel|downtime`) is the only one with current callers in our control.

Rename, in `sidequest/orbital/beats.py` and `tests/orbital/test_beats.py`:

- `class BeatKind(Enum)` → `class StoryBeatKind(Enum)`
- `class Beat` → `class StoryBeat`
- All references in tests + the new `Session` class.

~10–12 references total. Done as a small cleanup commit before Task 5 implementation begins. No production callers exist outside the orbital module today.

## Error Handling

| Failure | Behavior |
|---|---|
| `room.session` accessed before `_bind_snapshot` | `RuntimeError("Session not yet bound; call _bind_snapshot first.")`. Loud — no silent fallback. |
| Malformed `StoryBeat` (REST 4h, TRAVEL no duration, etc.) | `ValueError` propagated from existing `advance_clock_via_beat()`. Already covered by Task 2 tests. |
| Caller forgets `room=` kwarg | Python `TypeError` at call site (required keyword-only). Caught at import/boot time by the test suite. |
| Mutation via `room.session.clock.advance(x)` | Mutates a throwaway Clock; does not persist. Documented invariant; locked by test. |
| Legacy save missing `clock_t_hours` | Pydantic default `0.0`. No migration ceremony (legacy saves are throwaway). |

## Testing

### `Session` unit tests — new `tests/server/test_session_aggregate.py`

- Construction reads `snapshot.clock_t_hours` correctly (start zero; non-zero start).
- `session.clock` returns Clock with current snapshot value.
- **Read-only invariant:** `session.clock.advance(99)` then `session.clock.t_hours` returns the *original* value.
- `session.advance_via_beat(StoryBeat(ENCOUNTER, "test"))` advances `snapshot.clock_t_hours` by 1.0.
- `session.advance_via_beat(...)` emits `clock.advance` span.
- `session.end_scene("scene_end", turn=1)` emits **both** `encounter.scratch_clear` and `clock.advance` spans, with `clock.advance` carrying `trigger="scene-scene_end"`.
- Malformed beat propagates `ValueError`.

### SessionRoom lifecycle tests — `tests/server/test_session_room.py` (new or extended)

- `room.session` before `_bind_snapshot` raises `RuntimeError`.
- `room.session` after `_bind_snapshot` returns the bound Session.
- Re-binding produces a new Session over the new snapshot.

### Front-door wiring tests — one per migrated function

- `handle_yield(snapshot, room=room, ...)` advances `room.session.clock.t_hours` by 1h and emits the span.
- `_apply_narration_result_to_snapshot(..., room=room)` advances clock when an encounter resolves; does *not* advance on a `location_change` path.
- `DiceThrowHandler.handle` advances `sd._room.session.clock.t_hours` when `outcome.encounter_resolved` is true.

### Persistence round-trip — `tests/server/test_clock_persistence.py`

- `GameSnapshot(clock_t_hours=42.0)` → save → load → `clock_t_hours == 42.0`. Verifies pydantic+SQL path covers the new field with no schema change.

### Wiring test (CLAUDE.md mandate) — `tests/integration/test_session_clock_e2e.py`

Drive a `WebSocketSessionHandler` through a real scene-end (e.g. dice-resolved encounter via the dispatch path). After dispatch returns, assert:

- `room._snapshot.clock_t_hours` advanced from `0.0` to `1.0`.
- `otel_capture` recorded one `clock.advance` span (`beat_kind="encounter"`, `trigger="scene-scene_end"`).
- `otel_capture` recorded one `encounter.scratch_clear` span (existing signal still fires).

This is the mandated wiring test — proves the strangler-fig is wired into a production code path, not just tested in isolation.

### Existing tests stay green

- `tests/orbital/test_clock.py` — Clock primitive unchanged.
- `tests/orbital/test_beats.py` — references updated to `StoryBeatKind`/`StoryBeat`.
- All snapshot persistence tests — new field defaults `0.0`.

## Revised Task 5 Body (for the orbital-map plan)

The implementation plan for this spec replaces the existing Task 5 in `docs/superpowers/plans/2026-05-01-orbital-map-tracks-a-b.md`. The revised task structure:

### Pre-task: BeatKind rename cleanup

Rename `BeatKind`→`StoryBeatKind` and `Beat`→`StoryBeat` in `sidequest/orbital/beats.py` and `tests/orbital/test_beats.py`. Single commit. Verify all `tests/orbital/` still green.

### Step A: GameSnapshot field

Add `clock_t_hours: float = Field(default=0.0, ...)` to `GameSnapshot`. Add a persistence round-trip test. Verify existing snapshot tests still green.

### Step B: Session class + tests

Create `sidequest/server/session.py` with the class shown above. Create `tests/server/test_session_aggregate.py` with the unit tests listed in §Testing. Tests must pass (using a fresh `GameSnapshot` instance directly — no SessionRoom yet).

### Step C: SessionRoom binding

Add `_session: Session | None` field to `SessionRoom`. Bind in the existing snapshot-binding entry point(s). Add `session` property with the not-yet-bound RuntimeError. Add lifecycle tests.

### Step D: `_SessionData._room` back-reference

Add `_room: SessionRoom | None = None` to `_SessionData`. Wire population from `WebSocketSessionHandler.attach_room_context` after `_session_data` is created.

### Step E: Front-door wiring (three functions)

Add `room: SessionRoom` keyword-only parameter to `_apply_narration_result_to_snapshot`, `handle_yield`. Update three scene-end call sites to call `room.session.end_scene(reason, turn=...)`. Update upstream callers to thread `room` through (they have it via `WebSocketSessionHandler._room` or `_SessionData._room`).

### Step F: Wiring tests

Add the three front-door wiring tests + the e2e integration test from §Testing.

### Step G: Full test pass + commit

`just server-test` green. Single commit per step (or grouped Steps A+B, C+D, E+F).

---

## Open Questions / Follow-ups

1. **`game/session.py` rename.** The file is misnamed (contains `GameSnapshot`, not `Session`). Renaming to `game/snapshot.py` is the obvious next step but touches every import of `from sidequest.game.session import ...`. Out of scope here; flagged as a follow-up.
2. **`otel_capture` fixture promotion.** Three copies exist (`tests/server/conftest.py`, `tests/agents/conftest.py`, `tests/orbital/conftest.py` — added in Task 3). Promotion to top-level `tests/conftest.py` is a one-line rebase; out of scope here.
3. **`handle_rest` and rest-as-a-behavior.** Deferred until a rest action exists in the post-port server. The `on_long_rest` field on genre rules is currently unconsumed config.
4. **Combat `BeatKind` rename.** The older `sidequest/game/beat_kinds.py:BeatKind` would more honestly be named `MomentumBeatKind` or `CombatBeatKind`. ~50+ references; out of scope here.

## Why this design works

- **Small.** One new file (~50 lines), one new field on `GameSnapshot`, one back-reference on `_SessionData`, three function signature changes, three call site changes, one rename. ~150 lines of net change.
- **Honest.** No fictional `Session.empty()`, no `handle_rest()` without a caller, no rest behavior we don't have. Matches the post-port reality.
- **Strangler-fig.** Existing tier untouched in shape; future migrations move behavior inward one method at a time. The pattern is set: per-slug aggregate over the room, methods over free functions.
- **GM-panel honest.** Every scene-end fires `clock.advance` *and* the existing `encounter.scratch_clear`. Both visible. No "did the system advance time, or did Claude narrate that it did" ambiguity.
