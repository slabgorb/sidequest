# Wire ADR-036 Cinematic Mode in `_handle_player_action` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing `TurnManager.submit_input()` barrier so multiplayer rooms run the narrator once per round with all players' actions combined, instead of once per player submission.

**Architecture:** Add a per-room action buffer (`pending_actions`) plus an `asyncio.Lock` and `last_dispatched_round` counter to elect exactly one dispatch per round. Each player's WebSocket handler writes its action to the buffer, calls `submit_input(player_id)`, and either returns (still waiting) or runs the elected dispatch (last submitter wins). The narrator's contract is unchanged — combined actions are concatenated as labeled prose in a single `action: str`.

**Tech Stack:** Python 3.14, asyncio, pytest, FastAPI, dataclasses, pydantic. Server lives at `sidequest-server/`. Tests run via `just server-test` (which runs `uv run pytest -v` under the hood).

**Spec:** `docs/superpowers/specs/2026-04-26-mp-cinematic-mode-wiring-design.md`

**Source finding:** `[S5-ARCH]` in `/Users/slabgorb/Projects/sq-playtest-pingpong.md`.

---

## File Structure

| File | Status | Responsibility |
|------|--------|----------------|
| `sidequest-server/sidequest/server/session_room.py` | Modify | Add `PendingAction` dataclass, three new fields (`_pending_actions`, `_dispatch_lock`, `_last_dispatched_round`), four new helpers (`record_pending_action`, `drain_pending_actions`, `seated_player_count`, plus property accessors for the lock + round counter). |
| `sidequest-server/sidequest/server/session_handler.py` | Modify | In `_handle_player_action` (~line 3460): after the existing `turn_status_active` broadcast, write to buffer, call `submit_input`, return early if still collecting, or enter the dispatch-elected branch when the barrier fires. |
| `sidequest-server/sidequest/telemetry/spans.py` | Modify (or `watcher.py`) | Add two watcher-event helpers: `mp.barrier_fired` and `mp.round_dispatched`. (If existing convention is plain `_watcher_publish` calls inline, add them inline in `session_handler.py` instead — Task 5 verifies which.) |
| `sidequest-server/tests/server/test_mp_cinematic_dispatch.py` | Create | Five wiring tests: 2-player barrier combine, solo immediate dispatch, concurrent-dispatch race, disconnect-buffer-survival, same-player overwrite. |
| `docs/adr/036-multiplayer-turn-coordination.md` | Modify | Append `## Implementation notes (2026-04-26)` block recording the Python-port gap and its resolution. |

All other files (orchestrator, narrator, local_dm, prompt framework, UI, daemon, content) are **untouched**.

---

## Task 1: Add `PendingAction` dataclass + buffer state to `SessionRoom`

**Files:**
- Modify: `sidequest-server/sidequest/server/session_room.py:1-60`
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py` (create new)

- [ ] **Step 1: Create the test file with the failing buffer-roundtrip test**

Create `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`:

```python
"""Wiring tests for ADR-036 Cinematic mode — see
docs/superpowers/specs/2026-04-26-mp-cinematic-mode-wiring-design.md.

These tests verify the multiplayer barrier + dispatch election. Each test
either calls SessionRoom helpers directly (unit) or drives
``_handle_player_action`` end-to-end with mocked Claude (integration).
"""
from __future__ import annotations

import asyncio
import pytest

from sidequest.game.persistence import GameMode
from sidequest.server.session_room import PendingAction, SessionRoom


def test_pending_action_dataclass_holds_character_and_action() -> None:
    pa = PendingAction(character_name="Gladstone", action="I prepare for the dungeon")
    assert pa.character_name == "Gladstone"
    assert pa.action == "I prepare for the dungeon"


def test_record_and_drain_returns_in_submission_order() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    room.record_pending_action("p1", "Gladstone", "I prepare for the dungeon")
    room.record_pending_action("p2", "Zanzibar Jones", "I get my pole")
    drained = room.drain_pending_actions()
    assert [pid for pid, _ in drained] == ["p1", "p2"]
    assert drained[0][1].character_name == "Gladstone"
    assert drained[0][1].action == "I prepare for the dungeon"
    assert drained[1][1].character_name == "Zanzibar Jones"
    assert drained[1][1].action == "I get my pole"


def test_drain_empties_the_buffer() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    room.record_pending_action("p1", "Glad", "act1")
    room.drain_pending_actions()
    assert room.drain_pending_actions() == []


def test_record_same_player_twice_is_last_write_wins() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    room.record_pending_action("p1", "Gladstone", "I changed my mind")
    room.record_pending_action("p1", "Gladstone", "I really changed my mind")
    drained = room.drain_pending_actions()
    assert len(drained) == 1
    assert drained[0][1].action == "I really changed my mind"
```

- [ ] **Step 2: Run test to verify import error**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py -v`
Expected: FAIL — `ImportError: cannot import name 'PendingAction' from 'sidequest.server.session_room'`

- [ ] **Step 3: Add `PendingAction` dataclass and buffer field to `session_room.py`**

In `sidequest-server/sidequest/server/session_room.py`, after the existing `_Seat` dataclass (around line 30–34), add:

```python
@dataclass
class PendingAction:
    """A buffered player action awaiting the round barrier (ADR-036).

    Resolved at submit time so the elected dispatcher reads the labeled
    prose back without re-resolving foreign player_ids without their
    session data. See spec
    docs/superpowers/specs/2026-04-26-mp-cinematic-mode-wiring-design.md.
    """
    character_name: str
    action: str
```

Then, in the `SessionRoom` dataclass field block (after `_orchestrator` around line 60), add:

```python
    # ADR-036 Cinematic mode — round-level action buffer keyed by player_id.
    # Drained by the elected dispatcher when TurnManager.submit_input flips
    # the barrier from InputCollection to IntentRouting. See spec
    # docs/superpowers/specs/2026-04-26-mp-cinematic-mode-wiring-design.md.
    _pending_actions: dict[str, PendingAction] = field(default_factory=dict)
```

- [ ] **Step 4: Add `record_pending_action` and `drain_pending_actions` helpers**

In `session_room.py`, find the existing helper block near `seated_player_ids` (around line 203). Add after `absent_seated_player_ids`:

```python
    def record_pending_action(
        self, player_id: str, character_name: str, action: str,
    ) -> None:
        """Buffer one player's action for the current round (ADR-036).

        Last-write-wins on duplicate submissions for the same player_id.
        """
        with self._lock:
            self._pending_actions[player_id] = PendingAction(
                character_name=character_name, action=action,
            )

    def drain_pending_actions(self) -> list[tuple[str, PendingAction]]:
        """Return buffered actions in submission order and clear the buffer.

        Returns ``[(player_id, PendingAction), ...]``. Order matters because
        the combined-prose builder labels speakers in this order.
        """
        with self._lock:
            drained = list(self._pending_actions.items())
            self._pending_actions.clear()
        return drained
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py -v`
Expected: PASS — all four tests green.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/session_room.py sidequest-server/tests/server/test_mp_cinematic_dispatch.py
git commit -m "$(cat <<'EOF'
feat(mp): add PendingAction buffer to SessionRoom (ADR-036 step 1)

First slice of [S5-ARCH] cinematic-mode wiring. Adds the per-round
action buffer (record_pending_action + drain_pending_actions) keyed by
player_id. No callers yet — Task 3 wires _handle_player_action to it.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add dispatch-election state to `SessionRoom`

**Files:**
- Modify: `sidequest-server/sidequest/server/session_room.py`
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`

- [ ] **Step 1: Add the failing tests for the new fields and helper**

Append to `tests/server/test_mp_cinematic_dispatch.py`:

```python
def test_dispatch_lock_is_an_asyncio_lock() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    assert isinstance(room.dispatch_lock, asyncio.Lock)


def test_last_dispatched_round_starts_at_zero() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    assert room.last_dispatched_round == 0


def test_last_dispatched_round_is_writable() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    room.last_dispatched_round = 5
    assert room.last_dispatched_round == 5


def test_seated_player_count_returns_zero_when_no_seats() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    assert room.seated_player_count() == 0


def test_seated_player_count_after_seat() -> None:
    room = SessionRoom(slug="test-slug", mode=GameMode.MULTIPLAYER)
    room.connect("p1", socket_id="s1")
    room.seat("p1", character_slot="Gladstone")
    room.connect("p2", socket_id="s2")
    room.seat("p2", character_slot="Zanzibar Jones")
    assert room.seated_player_count() == 2
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_dispatch_lock_is_an_asyncio_lock -v`
Expected: FAIL — `AttributeError: 'SessionRoom' object has no attribute 'dispatch_lock'`

- [ ] **Step 3: Add the new fields and `seated_player_count` helper**

In `session_room.py`, in the `SessionRoom` dataclass field block (right after the `_pending_actions` field added in Task 1), add:

```python
    # Election primitives for one-dispatch-per-round (ADR-036). The lock
    # serializes the elected handlers; the round counter is the CAS guard
    # so a second handler that wakes after the first commits the round
    # short-circuits its dispatch instead of re-running the narrator.
    _dispatch_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _last_dispatched_round: int = 0
```

Then in the public-helper region (after `seated_player_ids` at line 203), add:

```python
    @property
    def dispatch_lock(self) -> asyncio.Lock:
        """The per-room dispatch election lock (ADR-036)."""
        return self._dispatch_lock

    @property
    def last_dispatched_round(self) -> int:
        """Highest round number for which a narrator dispatch has fired."""
        return self._last_dispatched_round

    @last_dispatched_round.setter
    def last_dispatched_round(self, value: int) -> None:
        self._last_dispatched_round = value

    def seated_player_count(self) -> int:
        """Number of seated players, regardless of connection state."""
        return len(self.seated_player_ids())
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py -v`
Expected: PASS — nine tests green (four from Task 1 + five new).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/session_room.py sidequest-server/tests/server/test_mp_cinematic_dispatch.py
git commit -m "$(cat <<'EOF'
feat(mp): add dispatch-lock + round counter to SessionRoom (ADR-036 step 2)

Election primitives for the one-dispatch-per-round guarantee. The lock
serializes elected handlers; the round counter is the CAS guard so a
second handler that wakes after the first commits the round will short-
circuit instead of re-running the narrator. No callers yet — Task 4
wires the elected branch.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Wire buffer + barrier into `_handle_player_action` (still-collecting path)

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py:~3460`
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`

This task wires the **early-return** path — when the submission is *not* the last one, the handler buffers and returns `[]`. The dispatch-elected branch lands in Task 4.

- [ ] **Step 1: Add the failing test for "first of two players returns empty"**

Append to `tests/server/test_mp_cinematic_dispatch.py`:

```python
from unittest.mock import AsyncMock, MagicMock

from sidequest.game.persistence import GameMode


@pytest.mark.asyncio
async def test_first_of_two_players_buffers_and_returns_empty(
    session_handler_factory,
) -> None:
    """When player 1 submits in a 2-seat room, the action is buffered and
    the handler returns [] (still waiting on player 2). The narrator must
    NOT run yet."""
    handler, sd, room = session_handler_factory(
        slug="test-mp-grimvault",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone"), ("p2", "Zanzibar Jones")],
        active_player=("p1", "Gladstone"),
    )
    # Spy on _execute_narration_turn — it must NOT be called this turn.
    handler._execute_narration_turn = AsyncMock(  # type: ignore[method-assign]
        return_value=[],
    )

    result = await handler._handle_player_action("I prepare for the dungeon")

    assert result == []
    handler._execute_narration_turn.assert_not_called()
    # Buffer holds Gladstone's action.
    drained = room.drain_pending_actions()
    assert len(drained) == 1
    assert drained[0][0] == "p1"
    assert drained[0][1].character_name == "Gladstone"
    assert drained[0][1].action == "I prepare for the dungeon"
```

If `session_handler_factory` does not yet provide a multiplayer-room signature, extend the existing `conftest.py` fixture in the same task — see Step 2 below before running.

- [ ] **Step 2: Verify or extend the test fixture**

Read `sidequest-server/tests/server/conftest.py:332-400` (the `session_handler_factory` fixture) to confirm it accepts `slug`, `mode`, `seat_players`, and `active_player` kwargs. If it does not, add support for them — the fixture must construct a `SessionHandler` whose `_room` is a `SessionRoom` configured per the kwargs, with the `_session_data.player_id` and `_session_data.player_name` matching `active_player`. The fixture should also `bind_world` a snapshot whose `turn_manager.player_count` starts at 1 (the default — `set_player_count` is called by the handler, not the fixture).

If extending the fixture is non-trivial, do it as the first action of this task and commit it as a separate "test infra" commit before continuing with Step 3.

- [ ] **Step 3: Run test to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_first_of_two_players_buffers_and_returns_empty -v`
Expected: FAIL — `assert result == []` fails because the current handler dispatches narration immediately, calling the AsyncMock.

- [ ] **Step 4: Add the buffer-and-barrier wiring**

Open `sidequest-server/sidequest/server/session_handler.py` and find the end of the `turn_status_active` broadcast block (currently around line 3458, the `logger.warning("session.turn_status_active_broadcast_failed error=%s", exc)` line). Then look at line 3459–3461 — the existing `lore_context = await self._retrieve_lore_for_turn(...)` / `turn_context = ...` / `return await self._execute_narration_turn(...)` triple.

Replace the call site so the buffer write and barrier come *before* `_execute_narration_turn`, and the still-collecting path returns early. The new structure (with imports added at top of file if not already present — `from sidequest.game.turn import TurnPhase`):

```python
        lore_context = await self._retrieve_lore_for_turn(sd, action)
        turn_context = _build_turn_context(sd, lore_context=lore_context, room=self._room)

        # ADR-036 Cinematic mode wiring. In multiplayer, every player's
        # submission goes into the per-room buffer and calls submit_input()
        # on the TurnManager barrier. If the barrier hasn't fired yet
        # (still in InputCollection), this handler returns []; another
        # player's later submission will fire the barrier and dispatch the
        # narrator with the combined action. Solo rooms (seated_player_count
        # == 1) flip the barrier on the first call and continue into the
        # elected branch immediately — zero overhead.
        if self._room is not None:
            self._room.record_pending_action(
                sd.player_id, acting_name, action,
            )
            snapshot.turn_manager.set_player_count(self._room.seated_player_count())
            snapshot.turn_manager.submit_input(sd.player_id)
            if snapshot.turn_manager.get_phase() == TurnPhase.InputCollection:
                # Still waiting on other seated players. Broadcasts already
                # delivered turn_status_active above; the dispatcher will
                # handle the actual narration when the last submission arrives.
                return []
            # Barrier fired — fall through to the elected dispatch branch
            # added in Task 4.
            pass  # NOTE: Task 4 replaces this with the elected branch.

        return await self._execute_narration_turn(sd, action, turn_context)
```

Two prep changes the spec didn't enumerate but the wiring needs:

1. `acting_name` — the broadcast block already computes this via `_resolve_acting_character_name(sd, self._room)` at line 3431 inside the `try` block. Refactor that lookup so `acting_name` is in scope for the buffer write *outside* the try. Concretely: hoist `acting_name = _resolve_acting_character_name(sd, self._room) if self._room is not None and sd.player_name else sd.player_name` up to *just before* the `if self._room is not None and sd.player_name:` line, then change the inner `acting_name = _resolve_acting_character_name(sd, self._room)` to reuse the outer variable. The fallback (`sd.player_name`) preserves single-player behavior where `_room is None`.
2. The `snapshot` reference — pulled from `sd.snapshot` like in `_execute_narration_turn` at line 3482. Add `snapshot = sd.snapshot` at the top of the new block (or reuse if already in scope).

Also add at the top of `session_handler.py` (with the other `from sidequest.game.turn import ...` imports):

```python
from sidequest.game.turn import TurnPhase
```

(Verify with `grep -n "from sidequest.game.turn" sidequest-server/sidequest/server/session_handler.py` — `TurnManager` may already be imported; just add `TurnPhase` to the same line.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_first_of_two_players_buffers_and_returns_empty -v`
Expected: PASS.

- [ ] **Step 6: Run the full session_handler test suite to catch regressions**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_handler.py tests/server/test_session_handler_decomposer.py tests/server/test_multiplayer_party_status.py -v`
Expected: PASS. Existing tests should be unaffected because they're either single-player (room is None or seat count == 1, where the barrier flips immediately and dispatch falls through) or test paths upstream of the new block.

If a single-player test fails because `_room is not None` and `seated_player_count == 1` is now flipping the barrier and falling through to `_execute_narration_turn`, that's correct behavior (Task 4 will add the elected branch). For now, the `pass` placeholder leaves the existing dispatch in place — the test should pass.

If a multiplayer test fails because it relied on per-submission narration, mark it for review in Task 4 — that test was encoding the bug.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_mp_cinematic_dispatch.py sidequest-server/tests/server/conftest.py
git commit -m "$(cat <<'EOF'
feat(mp): wire buffer+barrier early-return path (ADR-036 step 3)

In multiplayer, _handle_player_action now buffers actions into
SessionRoom.pending_actions and calls TurnManager.submit_input. When
the barrier hasn't fired yet (still InputCollection), the handler
returns [] — broadcasts already delivered turn_status_active. Solo
rooms flip the barrier immediately and fall through to the existing
dispatch path (unchanged). The elected branch lands in Task 4.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add the dispatch-elected branch (combined-prose narrator call)

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`

- [ ] **Step 1: Add the failing test "two players combine into one narrator dispatch"**

Append to `tests/server/test_mp_cinematic_dispatch.py`:

```python
@pytest.mark.asyncio
async def test_two_players_combine_into_one_narrator_dispatch(
    session_handler_factory,
) -> None:
    """When player 2 submits in a 2-seat room (player 1 already submitted),
    the barrier fires and exactly one narrator dispatch happens with both
    actions concatenated as labeled prose."""
    handler1, sd1, room = session_handler_factory(
        slug="test-mp-grimvault",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone"), ("p2", "Zanzibar Jones")],
        active_player=("p1", "Gladstone"),
    )
    handler2, sd2, _ = session_handler_factory(
        slug="test-mp-grimvault",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone"), ("p2", "Zanzibar Jones")],
        active_player=("p2", "Zanzibar Jones"),
        existing_room=room,
    )
    # Spy on _execute_narration_turn for both handlers — same room, both
    # methods bound to the room's snapshot.
    captured: list[str] = []

    async def fake_execute(sd, action, turn_context):
        captured.append(action)
        return []

    handler1._execute_narration_turn = fake_execute  # type: ignore[method-assign]
    handler2._execute_narration_turn = fake_execute  # type: ignore[method-assign]

    # Player 1 submits — buffers and returns [].
    r1 = await handler1._handle_player_action("I prepare for the dungeon")
    assert r1 == []
    assert captured == []  # narrator NOT called yet

    # Player 2 submits — barrier fires, elected branch combines and dispatches.
    r2 = await handler2._handle_player_action("I get my pole")
    # Exactly one narrator call with both actions.
    assert len(captured) == 1
    combined = captured[0]
    assert "Gladstone: I prepare for the dungeon" in combined
    assert "Zanzibar Jones: I get my pole" in combined
    # round counter advanced
    assert room.last_dispatched_round == room.snapshot.turn_manager.round
```

The fixture extension may need an `existing_room=` kwarg so two handlers can share the same SessionRoom. If `session_handler_factory` doesn't support it yet, add it now (return the fresh room when `existing_room` is None, otherwise bind the new handler to the passed-in room).

- [ ] **Step 2: Run test to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_two_players_combine_into_one_narrator_dispatch -v`
Expected: FAIL — either `assert len(captured) == 1` fails (currently 0 because Task 3 falls through to the existing single-action dispatch which gets a *single-player action string* like `"I get my pole"`, not the combined one) or it fails with `assert "Gladstone: I prepare for the dungeon" in combined`.

- [ ] **Step 3: Replace the `pass` placeholder with the elected branch**

In `sidequest-server/sidequest/server/session_handler.py`, find the `pass  # NOTE: Task 4 replaces this with the elected branch.` line added in Task 3. Replace that whole `if self._room is not None: ... pass` block's tail (from `if snapshot.turn_manager.get_phase() == TurnPhase.InputCollection: return []` onward) so the structure becomes:

```python
        if self._room is not None:
            self._room.record_pending_action(
                sd.player_id, acting_name, action,
            )
            snapshot.turn_manager.set_player_count(self._room.seated_player_count())
            snapshot.turn_manager.submit_input(sd.player_id)
            if snapshot.turn_manager.get_phase() == TurnPhase.InputCollection:
                # Still waiting on other seated players.
                return []

            # Barrier fired — elect a single dispatcher per round via
            # asyncio.Lock + last_dispatched_round CAS guard.
            async with self._room.dispatch_lock:
                current_round = snapshot.turn_manager.round
                if self._room.last_dispatched_round >= current_round:
                    # Lost the race; another handler already dispatched.
                    return []
                self._room.last_dispatched_round = current_round
                pending = self._room.drain_pending_actions()

            combined_action = "\n".join(
                f"{p.character_name}: {p.action}" for _, p in pending
            )
            result = await self._execute_narration_turn(
                sd, combined_action, turn_context,
            )
            snapshot.turn_manager.record_interaction()
            return result

        # Single-player path (room is None) — preserve original behavior.
        return await self._execute_narration_turn(sd, action, turn_context)
```

Note the structure: the multiplayer block returns its own `result`; the unconditional `return await self._execute_narration_turn(...)` at the bottom now applies *only* to the legacy `room is None` case. If your codebase always has a room (verify via `grep -n "self._room = None\|self._room = " sidequest-server/sidequest/server/session_handler.py`), the legacy fallback may be dead code — leave it for safety, file a follow-up if you confirm it's unreachable.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_two_players_combine_into_one_narrator_dispatch -v`
Expected: PASS.

- [ ] **Step 5: Run the full session_handler suite to catch regressions**

Run: `cd sidequest-server && uv run pytest tests/server/ -v -x`
Expected: PASS. If a multiplayer test fails because it expected per-submission narration, that test was encoding the bug — fix the test by following the new pattern (one dispatch per round) and note it in the commit message.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_mp_cinematic_dispatch.py sidequest-server/tests/server/conftest.py
git commit -m "$(cat <<'EOF'
feat(mp): add dispatch-elected branch — narrator runs once per round (ADR-036 step 4)

Completes [S5-ARCH] — when the barrier fires, the elected handler
acquires dispatch_lock, CAS-checks last_dispatched_round, drains the
buffer, builds the combined-prose action string, and calls
_execute_narration_turn exactly once. record_interaction() advances the
turn counter. Other handlers that lose the CAS short-circuit with [].

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add solo-immediate-dispatch test

**Files:**
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`

- [ ] **Step 1: Add the test**

Append to `tests/server/test_mp_cinematic_dispatch.py`:

```python
@pytest.mark.asyncio
async def test_solo_room_dispatches_immediately_no_buffering_observable(
    session_handler_factory,
) -> None:
    """A single seated player triggers the barrier on their first submission.
    The narrator runs exactly once on that submission with the player's raw
    action (no labeled-prose combining needed)."""
    handler, sd, room = session_handler_factory(
        slug="test-solo-grimvault",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone")],
        active_player=("p1", "Gladstone"),
    )
    captured: list[str] = []

    async def fake_execute(sd, action, turn_context):
        captured.append(action)
        return []

    handler._execute_narration_turn = fake_execute  # type: ignore[method-assign]

    result = await handler._handle_player_action("I look around")

    assert result == []
    assert len(captured) == 1
    # With one seated player, the combined-prose builder still runs but the
    # output is just one line.
    assert "Gladstone: I look around" in captured[0]
    assert room.last_dispatched_round == 1
```

- [ ] **Step 2: Run test to verify it passes (no implementation change required)**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_solo_room_dispatches_immediately_no_buffering_observable -v`
Expected: PASS.

If it FAILS because the solo path is currently still going through the legacy `room is None` branch (i.e., the room exists but is being short-circuited elsewhere), trace the divergence and fix by ensuring the solo room path goes through the same buffer + barrier flow. The barrier flips immediately on the first `submit_input` when `player_count == 1`, so no special-casing is needed.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_mp_cinematic_dispatch.py
git commit -m "test(mp): solo dispatches immediately, no buffer overhead (ADR-036)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Add concurrent-dispatch race test

**Files:**
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`

- [ ] **Step 1: Add the test**

Append to `tests/server/test_mp_cinematic_dispatch.py`:

```python
@pytest.mark.asyncio
async def test_concurrent_submissions_dispatch_exactly_once(
    session_handler_factory,
) -> None:
    """Two _handle_player_action calls awaited concurrently via asyncio.gather.
    The dispatch_lock + last_dispatched_round CAS must guarantee exactly one
    narrator call."""
    handler1, sd1, room = session_handler_factory(
        slug="test-mp-grimvault-race",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone"), ("p2", "Zanzibar Jones")],
        active_player=("p1", "Gladstone"),
    )
    handler2, sd2, _ = session_handler_factory(
        slug="test-mp-grimvault-race",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone"), ("p2", "Zanzibar Jones")],
        active_player=("p2", "Zanzibar Jones"),
        existing_room=room,
    )
    captured: list[str] = []

    async def fake_execute(sd, action, turn_context):
        # Yield to the event loop so the two handlers can interleave.
        await asyncio.sleep(0)
        captured.append(action)
        return []

    handler1._execute_narration_turn = fake_execute  # type: ignore[method-assign]
    handler2._execute_narration_turn = fake_execute  # type: ignore[method-assign]

    r1, r2 = await asyncio.gather(
        handler1._handle_player_action("I prepare for the dungeon"),
        handler2._handle_player_action("I get my pole"),
    )
    assert r1 == [] and r2 == []
    assert len(captured) == 1, f"expected exactly one dispatch, got {len(captured)}"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_concurrent_submissions_dispatch_exactly_once -v`
Expected: PASS.

If it FAILS with `len(captured) == 2`, the CAS check is not happening before the dispatch — verify Task 4's elected-branch order: `last_dispatched_round` must be set *inside* the `async with dispatch_lock` block, *before* any `await` that releases the loop, so the second handler entering the lock sees the bumped counter and short-circuits.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_mp_cinematic_dispatch.py
git commit -m "test(mp): concurrent-submission race elects exactly one dispatcher (ADR-036)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Add disconnect-buffer-survival test

**Files:**
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`

- [ ] **Step 1: Add the test**

Append to `tests/server/test_mp_cinematic_dispatch.py`:

```python
def test_buffered_action_survives_buffer_owner_disconnect() -> None:
    """If a player submits, then disconnects before the barrier fires, the
    buffered PendingAction stays in the room buffer. (Pause-gate semantics
    happen at the handler entry point — this test covers the buffer-state
    invariant.)"""
    room = SessionRoom(slug="test-disc", mode=GameMode.MULTIPLAYER)
    room.connect("p1", socket_id="s1")
    room.seat("p1", character_slot="Gladstone")
    room.connect("p2", socket_id="s2")
    room.seat("p2", character_slot="Zanzibar Jones")

    # p1 submits.
    room.record_pending_action("p1", "Gladstone", "I prepare for the dungeon")

    # p1 disconnects (simulating WS drop).
    room.disconnect(socket_id="s1")
    assert "p1" in [s.player_id for s in room._seated.values()]  # still seated
    assert "p1" in room.absent_seated_player_ids()
    assert room.is_paused()

    # Buffered action survives.
    drained = room.drain_pending_actions()
    assert len(drained) == 1
    assert drained[0][0] == "p1"
    assert drained[0][1].action == "I prepare for the dungeon"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_buffered_action_survives_buffer_owner_disconnect -v`
Expected: PASS — the buffer is room-scoped, not socket-scoped, so disconnect doesn't touch it.

If it FAILS, the `disconnect` method is incorrectly clearing buffered actions — a regression that needs fixing in `session_room.py`. The buffer should never be cleared by connection state; only `drain_pending_actions` clears it.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_mp_cinematic_dispatch.py
git commit -m "test(mp): buffered action survives submitter disconnect (ADR-036)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Add OTEL events `mp.barrier_fired` and `mp.round_dispatched`

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_mp_cinematic_dispatch.py`

The spec mandates two new watcher events. Use the existing `_watcher_publish` helper used elsewhere in `session_handler.py`.

- [ ] **Step 1: Add the failing OTEL test**

Append to `tests/server/test_mp_cinematic_dispatch.py`:

```python
from unittest.mock import patch


@pytest.mark.asyncio
async def test_otel_events_emitted_on_barrier_fire_and_dispatch(
    session_handler_factory,
) -> None:
    """The GM panel needs to see when the barrier fires and when the
    elected dispatcher runs the narrator (CLAUDE.md OTEL principle)."""
    handler1, sd1, room = session_handler_factory(
        slug="test-otel-grimvault",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone"), ("p2", "Zanzibar Jones")],
        active_player=("p1", "Gladstone"),
    )
    handler2, sd2, _ = session_handler_factory(
        slug="test-otel-grimvault",
        mode=GameMode.MULTIPLAYER,
        seat_players=[("p1", "Gladstone"), ("p2", "Zanzibar Jones")],
        active_player=("p2", "Zanzibar Jones"),
        existing_room=room,
    )

    async def fake_execute(sd, action, turn_context):
        return []

    handler1._execute_narration_turn = fake_execute  # type: ignore[method-assign]
    handler2._execute_narration_turn = fake_execute  # type: ignore[method-assign]

    # Patch the _watcher_publish symbol used inside session_handler.
    with patch("sidequest.server.session_handler._watcher_publish") as wp:
        await handler1._handle_player_action("I prepare for the dungeon")
        await handler2._handle_player_action("I get my pole")

    event_names = [call.args[0] for call in wp.call_args_list]
    # turn_status broadcasts (per-submission) + mp.barrier_fired (once on
    # last submission) + mp.round_dispatched (once on dispatch entry).
    assert "mp.barrier_fired" in event_names
    assert "mp.round_dispatched" in event_names
    # Each fires exactly once for this round.
    assert event_names.count("mp.barrier_fired") == 1
    assert event_names.count("mp.round_dispatched") == 1
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_otel_events_emitted_on_barrier_fire_and_dispatch -v`
Expected: FAIL — events not in the captured list.

- [ ] **Step 3: Add the OTEL emissions**

In `session_handler.py`'s `_handle_player_action`, in the multiplayer block from Task 4:

After the `submit_input` call, just before the `if snapshot.turn_manager.get_phase() == TurnPhase.InputCollection:` check, add:

```python
            if snapshot.turn_manager.get_phase() != TurnPhase.InputCollection:
                # Barrier just fired on this submission — emit before the
                # dispatch CAS so a failed dispatch still leaves the
                # barrier-fired event visible.
                _watcher_publish(
                    "mp.barrier_fired",
                    {
                        "slug": self._room.slug,
                        "round": snapshot.turn_manager.round,
                        "player_count": self._room.seated_player_count(),
                        "submitter_player_id": sd.player_id,
                    },
                    component="multiplayer",
                )
```

(Note: keep the original `if snapshot.turn_manager.get_phase() == TurnPhase.InputCollection: return []` check; it's the negation of the new emit-and-fall-through guard. Order is: emit on flip, then early-return on still-collecting.)

Then, inside the `async with self._room.dispatch_lock:` block, after the CAS guard succeeds and `last_dispatched_round` is set, add:

```python
                _watcher_publish(
                    "mp.round_dispatched",
                    {
                        "slug": self._room.slug,
                        "round": current_round,
                        "player_count": self._room.seated_player_count(),
                        "action_lengths": {
                            pid: len(p.action) for pid, p in pending
                        },
                        "combined_action_len": sum(
                            len(p.action) for _, p in pending
                        ) + sum(len(p.character_name) + 2 for _, p in pending),
                    },
                    component="multiplayer",
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py::test_otel_events_emitted_on_barrier_fire_and_dispatch -v`
Expected: PASS.

- [ ] **Step 5: Run the full new test file to confirm no regressions in earlier tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py -v`
Expected: PASS — all tests green.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_mp_cinematic_dispatch.py
git commit -m "$(cat <<'EOF'
feat(otel): emit mp.barrier_fired and mp.round_dispatched on cinematic dispatch

Per CLAUDE.md OTEL principle — every subsystem decision must be visible
to the GM panel. The barrier flip and elected-dispatch entry now emit
watcher events with slug, round, player_count, and per-player action
metadata. Without these, you can't tell whether the cinematic-mode
wiring engaged or whether the legacy FreePlay path is still firing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Update ADR-036 implementation-notes block

**Files:**
- Modify: `docs/adr/036-multiplayer-turn-coordination.md`

- [ ] **Step 1: Append the implementation-notes section to ADR-036**

Open `docs/adr/036-multiplayer-turn-coordination.md`. After the existing "Consequences" section (or wherever the document ends, before any trailing horizontal rule / footer), append:

```markdown

## Implementation notes (2026-04-26)

ADR-082 port from Rust to Python (~2026-04-19) carried over the
`TurnManager.submit_input()` barrier API at
`sidequest-server/sidequest/game/turn.py:93–101` but did **not** re-implement
the dispatch-side wiring. `_handle_player_action` continued to call
`_execute_narration_turn` immediately on every WebSocket submission,
which is FreePlay semantics regardless of player count. The barrier
existed in the codebase as dead code with zero production callers
(`grep -rn submit_input sidequest-server/sidequest --include='*.py' | grep -v tests`
returned only the definition).

This was discovered live in the 2026-04-26 caverns_and_claudes/grimvault
playtest — both players submitted, both received independent narrations,
neither acknowledged the other's action. Filed as `[S5-ARCH]` in the
playtest pingpong.

The Cinematic mode is now wired in `_handle_player_action` via:

- `SessionRoom.pending_actions: dict[str, PendingAction]` — round-level
  action buffer keyed by player_id.
- `SessionRoom.dispatch_lock: asyncio.Lock` — serializes elected handlers.
- `SessionRoom.last_dispatched_round: int` — CAS guard against duplicate
  dispatch when two handlers wake from the same barrier flip.

The Rust `TurnBarrier` (tokio::Notify) and `AtomicU64` CAS were not ported
literally — Python's asyncio Lock + plain int counter cover the same
guarantees with simpler primitives. The "last submitter runs the
dispatch" pattern replaces the CAS-then-Notify-then-claim sequence; it's
equivalent for single-event-loop asyncio servers because no two handlers
can be inside the same `async with` block simultaneously.

`AdaptiveTimeout` and the "remains silent" default are still deferred per
CLAUDE.md primary-audience guidance (Alex / slow typist). v1 blocks the
round indefinitely; the table waits, the narrator does not gallop ahead.
Reintroduce the timeout when player feedback demands it.

OTEL events `mp.barrier_fired` and `mp.round_dispatched` are emitted on
every multiplayer round so the GM panel can audit the engagement of the
cinematic-mode pipeline.

Spec: `docs/superpowers/specs/2026-04-26-mp-cinematic-mode-wiring-design.md`.
Plan: `docs/superpowers/plans/2026-04-26-mp-cinematic-mode-wiring.md`.
```

- [ ] **Step 2: Verify the ADR file parses cleanly**

Run: `cd /Users/slabgorb/Projects/oq-1 && python scripts/regenerate_adr_indexes.py 2>&1 | tail -10`
Expected: Clean run, no warnings about ADR-036.

If `regenerate_adr_indexes.py` doesn't exist or errors, just visually verify the markdown renders by opening the file — the appended block uses standard markdown so a syntax error is unlikely.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/036-multiplayer-turn-coordination.md
git commit -m "$(cat <<'EOF'
docs(adr-036): implementation notes for Python-port cinematic-mode wiring

Records the port-era gap (ADR-082 carried over TurnManager.submit_input
with no callers) and its resolution. Pointers to spec + plan for
traceability.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Run the full server test suite + lint, then update pingpong

**Files:**
- Verify: `sidequest-server` full suite
- Modify: `/Users/slabgorb/Projects/sq-playtest-pingpong.md`

- [ ] **Step 1: Run the full server gate**

Run: `cd /Users/slabgorb/Projects/oq-1 && just server-check`
Expected: PASS (lint + test, all green).

If anything fails, fix inline. Do not move on with red tests.

- [ ] **Step 2: Update pingpong S5-ARCH status**

Open `/Users/slabgorb/Projects/sq-playtest-pingpong.md`. Find the `### [S5-ARCH]` block under Session 5 Findings. Change the last line:

```markdown
- **Status:** open — architectural recommendation filed, awaiting story creation by SM (Vizzini)
```

to:

```markdown
- **Status:** verified-pending — implementation landed (PR #N), awaiting live 2-player verification by Keith. Test suite green. ADR-036 implementation-notes block updated.
```

(Replace `#N` with the actual PR number once the PR is open. If running locally without a PR yet, mark as `merged-locally pending live verification`.)

- [ ] **Step 3: Commit pingpong update**

```bash
git add /Users/slabgorb/Projects/sq-playtest-pingpong.md
git commit -m "chore(pingpong): mark S5-ARCH verified-pending, awaiting live test"
```

(Note: the pingpong file lives outside the orchestrator repo — it may be in its own repo or untracked. If `git add` fails because it's outside the working tree, simply edit the file in place; no commit required for that path.)

- [ ] **Step 4: Final verification**

Run: `cd sidequest-server && uv run pytest tests/server/test_mp_cinematic_dispatch.py -v`
Expected: All ten tests pass.

Run: `cd sidequest-server && uv run pytest tests/server/ -v --tb=short 2>&1 | tail -5`
Expected: No regressions in the broader server suite.

- [ ] **Step 5: Hand off for live verification**

Notify the user (Keith) that the implementation is ready for live verification:
- Start the stack with `just up`
- Open two browsers / two players, join the same `caverns_and_claudes/grimvault` slug as Gladstone and Zanzibar Jones
- Each player submits a different action
- Verify in the server log: only one `narrator.session_resume` and one `Claude CLI returned narration` per round (not two)
- Verify in the GM panel: `mp.barrier_fired` and `mp.round_dispatched` events appear once per round
- Verify on each player's screen: the narration acknowledges *both* players' actions

If any verification fails, file a follow-up finding in pingpong as `[S5-ARCH-FOLLOWUP]` and reopen the story.

---

## Self-review

**Spec coverage:**
- Action shape (concatenated prose) — Task 4 (combined_action builder) ✓
- Last-submitter-runs dispatch — Task 4 ✓
- Per-room buffer (`pending_actions`) — Task 1 ✓
- `dispatch_lock` + `last_dispatched_round` — Task 2 ✓
- `record_pending_action` / `drain_pending_actions` / `seated_player_count` — Tasks 1–2 ✓
- `_handle_player_action` wiring (early-return + elected branch) — Tasks 3–4 ✓
- "Don't touch" preserves: turn_status_active broadcast, pause gate, LocalDM decompose — verified by test 6 (full suite passes) ✓
- Five spec-mandated tests: barrier-combine (Task 4), solo (Task 5), concurrent-race (Task 6), disconnect-buffer-survival (Task 7), same-player-overwrite (Task 1) ✓
- OTEL events — Task 8 ✓
- ADR-036 implementation-notes update — Task 9 ✓
- Definition-of-done verification — Task 10 ✓

No spec gaps detected.

**Placeholder scan:**
- "TBD" — none in steps; only inside the ADR-036 implementation-notes prose where the original spec carried it forward as part of the documentation.
- "TODO" / "implement later" — none.
- "Add appropriate error handling" — none. Error-handling decisions are spelled out per scenario in Task 4's elected-branch code.
- "Similar to Task N" — none.
- All test code blocks are complete and runnable.

**Type consistency check:**
- `PendingAction` — defined Task 1 with `character_name: str, action: str`. Used in Task 1 (record / drain), Task 4 (combined_action builder reads `p.character_name` / `p.action`), Task 8 (action_lengths reads `len(p.action)`). Consistent ✓.
- `record_pending_action(player_id, character_name, action)` signature — defined Task 1, called Task 3 with the same three positional args. Consistent ✓.
- `drain_pending_actions() -> list[tuple[str, PendingAction]]` — defined Task 1, consumed Task 4 (`for _, p in pending`) and Task 8 (`for pid, p in pending`). Consistent ✓.
- `dispatch_lock` (property), `last_dispatched_round` (property+setter), `seated_player_count()` (method) — defined Task 2, consumed Tasks 3–4 and Task 8. Consistent ✓.
- `TurnPhase.InputCollection` — imported from `sidequest.game.turn` in Task 3, used in Task 3 and Task 8 (negation form). Consistent ✓.
- `_watcher_publish` — referenced in Task 8. Verified in scoping note (Task 8 Step 1 mentions "the existing `_watcher_publish` helper used elsewhere in `session_handler.py`"). The implementer must verify the import path with `grep -n _watcher_publish sidequest-server/sidequest/server/session_handler.py` before adding the calls.

No type-consistency issues detected.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-26-mp-cinematic-mode-wiring.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh Dev subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
