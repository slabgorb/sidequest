# Shared Room.snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-session `sd.snapshot` ownership with a single `GameSnapshot` held on `SessionRoom` and shared by every WebSocket session bound to that slug. Drop the `_merge_peer_state_into_snapshot` band-aid wholesale (no MP saves on disk to migrate).

**Architecture:** `SessionRoom` gains `_snapshot` and `_store` fields plus `bind_world` / `save` / `close_store` methods, all protected by the existing `_lock`. Slug-connect's first occupant loads from store and binds; later occupants reuse the same snapshot reference. Every existing `sd.store.save(...)` site routes through `self._room.save()`. Mutations to `sd.snapshot.*` are unchanged — Python references guarantee every session sees them live.

**Tech Stack:** Python 3.14, `uv` for env, `pytest` (asyncio mode auto), `sqlite3`, dataclasses, `threading.RLock`. Server subrepo: `/Users/slabgorb/Projects/oq-1/sidequest-server`.

---

## File Structure

| File | Role |
|---|---|
| `sidequest/server/session_room.py` | Add `_snapshot` / `_store` fields + `bind_world` / `snapshot` / `store` / `save` / `close_store` methods. |
| `sidequest/server/session_handler.py` | Wire bind into slug-connect; replace 4 save sites with `self._room.save()`; delete `_merge_peer_state_into_snapshot` and its 3 call sites; clean up the chargen second-commit `sd.snapshot = existing_saved.snapshot` assignment that becomes redundant. |
| `tests/server/test_session_room.py` | Extend (or create if absent) with 3 binding/idempotency tests. |
| `tests/server/test_multiplayer_party_status.py` | Delete 5 merge tests + the `_saved_snapshot_with` helper; add 4 shared-room wiring tests. |

No UI / daemon / content changes. One subrepo, branch `develop`, working tree clean.

---

## Working Conventions

- Test command from `sidequest-server/`: `uv run pytest tests/server/ tests/agents/`
- Single-test runs: `uv run pytest tests/server/test_session_room.py::test_name -v`
- Baseline at start of work: **736 passed, 2 skipped**
- Expected end-state: **738 passed, 2 skipped** (delete 5 merge tests + add 4 + add 3 = +2 net)
- Each task ends with a commit. All commits stay on `develop` (no feature branch — small, sequential, low-risk).
- The `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer is required on every commit.

---

## Task 1: Add snapshot/store fields and bind_world to SessionRoom

**Files:**
- Modify: `sidequest/server/session_room.py:27-37` (SessionRoom dataclass field block)
- Modify: `sidequest/server/session_room.py:38` (add new methods after `__post_init__` style — actually as new method block before `connect`)
- Test: `tests/server/test_session_room.py` (extend or create)

- [ ] **Step 1: Check whether `tests/server/test_session_room.py` exists.**

```bash
ls /Users/slabgorb/Projects/oq-1/sidequest-server/tests/server/test_session_room.py 2>&1
```

If it exists, append the new tests after the last test in the file. If it does not, create it with the imports below. The remainder of this task assumes the test file is present.

- [ ] **Step 2: Write the three failing bind tests.**

Add to `tests/server/test_session_room.py` (or create the file):

```python
"""SessionRoom canonical-snapshot binding (ADR-037 Python port).

Locks in the contract that the room is the canonical owner of the
GameSnapshot and SqliteStore for its slug, so every WS session bound to
the room reads and writes the same in-memory object.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from sidequest.game.persistence import GameMode
from sidequest.game.session import GameSnapshot
from sidequest.server.session_room import SessionRoom


def _fresh_snapshot() -> GameSnapshot:
    return GameSnapshot(
        genre_slug="caverns_and_claudes",
        world_slug="mawdeep",
        location="Entrance",
    )


def test_bind_world_sets_snapshot_and_store_once() -> None:
    """First bind populates both fields; getters reflect them."""
    room = SessionRoom(slug="2026-04-25-test-mp", mode=GameMode.MULTIPLAYER)
    snap = _fresh_snapshot()
    store = MagicMock()

    assert room.snapshot is None
    assert room.store is None

    room.bind_world(snapshot=snap, store=store)

    assert room.snapshot is snap
    assert room.store is store


def test_bind_world_is_idempotent() -> None:
    """Second bind when already populated is a no-op (no overwrite, no raise).

    Guards against a race where two concurrent first-connects both try to
    bind. The first wins; the second silently observes the existing
    binding rather than stomping it.
    """
    room = SessionRoom(slug="slug", mode=GameMode.MULTIPLAYER)
    snap1 = _fresh_snapshot()
    store1 = MagicMock()
    snap2 = _fresh_snapshot()
    store2 = MagicMock()

    room.bind_world(snapshot=snap1, store=store1)
    room.bind_world(snapshot=snap2, store=store2)

    assert room.snapshot is snap1
    assert room.store is store1


def test_close_store_is_idempotent_and_calls_close_once() -> None:
    """close_store closes the bound store exactly once across N calls."""
    room = SessionRoom(slug="slug", mode=GameMode.MULTIPLAYER)
    store = MagicMock()
    room.bind_world(snapshot=_fresh_snapshot(), store=store)

    room.close_store()
    room.close_store()

    assert store.close.call_count == 1


def test_close_store_when_unbound_is_noop() -> None:
    """Pre-bind / never-bound rooms must not raise on close."""
    room = SessionRoom(slug="slug", mode=GameMode.MULTIPLAYER)
    room.close_store()  # must not raise
```

- [ ] **Step 3: Run the new tests to confirm they fail with AttributeError on snapshot/store/bind_world/close_store.**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_session_room.py -v
```

Expected: 4 FAILED with `AttributeError: 'SessionRoom' object has no attribute 'snapshot'` (or similar) — the methods don't exist yet.

- [ ] **Step 4: Add fields and methods to `SessionRoom`.**

In `sidequest/server/session_room.py`, top of file extend the imports:

```python
from sidequest.game.persistence import GameMode, SqliteStore
from sidequest.game.session import GameSnapshot
```

In the dataclass field block (currently lines 30-37 ending at `_outbound_queues`), append two fields:

```python
    _snapshot: GameSnapshot | None = field(default=None, repr=False)
    _store: SqliteStore | None = field(default=None, repr=False)
```

Immediately after the `_outbound_queues` field declaration and BEFORE the `connect` method, insert the new method block:

```python
    # ------------------------------------------------------------------
    # Canonical world state (ADR-037 Python port). The room owns the
    # GameSnapshot and SqliteStore; every WS session bound to this slug
    # reads and writes the same in-memory snapshot reference.
    # ------------------------------------------------------------------

    def bind_world(
        self,
        *,
        snapshot: GameSnapshot,
        store: SqliteStore,
    ) -> None:
        """Bind canonical snapshot + store to the room. Idempotent.

        First slug-connect on the room calls this with the loaded (or
        freshly constructed) snapshot. Subsequent connects observe the
        existing binding via the ``snapshot`` / ``store`` properties and
        do not call ``bind_world`` themselves; this idempotency is
        defense for any path that does retry the bind.
        """
        with self._lock:
            if self._snapshot is not None:
                return
            self._snapshot = snapshot
            self._store = store

    @property
    def snapshot(self) -> GameSnapshot | None:
        """Canonical snapshot for the slug, or None before first bind."""
        return self._snapshot

    @property
    def store(self) -> SqliteStore | None:
        """Canonical SqliteStore for the slug, or None before first bind."""
        return self._store

    def save(self) -> None:
        """Persist the canonical snapshot through the canonical store.

        Acquires ``_lock`` so concurrent saves from disconnect / turn-end
        / chargen-commit on different sessions don't interleave their
        write windows. No-op when the room hasn't been bound — paths
        that haven't reached slug-connect must not crash.
        """
        with self._lock:
            if self._snapshot is None or self._store is None:
                return
            self._store.save(self._snapshot)

    def close_store(self) -> None:
        """Close the canonical store exactly once. Idempotent.

        Called by ``RoomRegistry`` (or last-disconnect cleanup) so the
        underlying SQLite handle is released. Safe to call when never
        bound.
        """
        with self._lock:
            if self._store is None:
                return
            try:
                self._store.close()
            finally:
                self._store = None
```

- [ ] **Step 5: Run the binding tests to confirm they pass.**

```bash
uv run pytest tests/server/test_session_room.py -v
```

Expected: all 4 PASSED.

- [ ] **Step 6: Run the full server+agents sweep to confirm no regression.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `740 passed, 2 skipped` (baseline 736 + 4 new tests; nothing else changed yet so no deletions).

- [ ] **Step 7: Commit.**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/server/session_room.py tests/server/test_session_room.py
git commit -m "$(cat <<'EOF'
feat(server): add canonical snapshot + store binding to SessionRoom

ADR-037 Python port — SessionRoom gains _snapshot / _store fields and
bind_world / snapshot / store / save / close_store methods so the room
becomes the authoritative owner of the GameSnapshot for its slug.
Every WS session bound to the room will hold a Python reference to the
same snapshot object, eliminating the per-session divergence the
_merge_peer_state_into_snapshot band-aid currently masks.

bind_world is idempotent (first writer wins); save acquires the room
lock; close_store closes the SqliteStore exactly once across N calls.
No call sites are migrated in this commit — slug-connect rewiring and
band-aid removal land in subsequent commits.

Tests: 4 new in test_session_room.py covering bind / idempotent rebind
/ close-once / close-unbound. Server+agents sweep: 740 passed, 2
skipped (baseline 736 + 4 new).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Wire slug-connect to bind and read from the room snapshot

**Files:**
- Modify: `sidequest/server/session_handler.py:1281-1361` (slug-connect saved/fresh-snapshot block)
- Modify: `sidequest/server/session_handler.py:1333` (UUID-rename save)
- Test: `tests/server/test_multiplayer_party_status.py` (add wiring test)

- [ ] **Step 1: Write the failing wiring test.**

Append to `tests/server/test_multiplayer_party_status.py` after the last test:

```python
# ---------------------------------------------------------------------------
# Shared Room.snapshot wiring (ADR-037 Python port)
# ---------------------------------------------------------------------------


def test_two_handlers_share_room_snapshot_after_bind() -> None:
    """Two handlers bound to the same room observe the same snapshot
    object — mutating one's sd.snapshot.characters is visible to the
    other without any reload.

    This is the core regression guard for the per-session divergence
    that the _merge_peer_state_into_snapshot band-aid was masking.
    """
    from pathlib import Path as _Path
    from sidequest.server.session_handler import WebSocketSessionHandler

    room = SessionRoom(slug="2026-04-25-shared-test", mode=GameMode.MULTIPLAYER)
    snap = GameSnapshot(
        genre_slug="caverns_and_claudes",
        world_slug="mawdeep",
        location="Entrance",
    )
    snap.characters = []
    store = MagicMock()
    room.bind_world(snapshot=snap, store=store)

    laverne = _char("Laverne")
    shirley = _char("Shirley")

    # Two handlers, each with sd bound to the same room snapshot ref.
    handler_a = WebSocketSessionHandler(save_dir=_Path("/tmp/sq-test-saves"))
    handler_a._room = room
    sd_a = _sd("p:laverne", "Laverne", [])
    sd_a.snapshot = room.snapshot  # type: ignore[assignment]
    sd_a.store = room.store  # type: ignore[assignment]
    handler_a._session_data = sd_a

    handler_b = WebSocketSessionHandler(save_dir=_Path("/tmp/sq-test-saves"))
    handler_b._room = room
    sd_b = _sd("p:shirley", "Shirley", [])
    sd_b.snapshot = room.snapshot  # type: ignore[assignment]
    sd_b.store = room.store  # type: ignore[assignment]
    handler_b._session_data = sd_b

    # Mutate via handler_a's sd; handler_b sees it.
    handler_a._session_data.snapshot.characters.append(laverne)
    assert [c.core.name for c in handler_b._session_data.snapshot.characters] == [
        "Laverne",
    ]

    # And vice versa.
    handler_b._session_data.snapshot.characters.append(shirley)
    assert sorted(c.core.name for c in handler_a._session_data.snapshot.characters) == [
        "Laverne",
        "Shirley",
    ]
```

- [ ] **Step 2: Run the new test to confirm it fails.**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py::test_two_handlers_share_room_snapshot_after_bind -v
```

Expected: FAIL — `_session_data.snapshot` on each handler is currently set inside `_sd(...)` to a new GameSnapshot, so the assignment to `room.snapshot` overrides it but other downstream wiring isn't there yet. Actually this test will likely PASS on its own because it's pure assignment-and-reference. **If it passes immediately, that's still informative**: the assignment-by-reference works; what was missing is the production code path that actually does this assignment. Either way, proceed to Step 3 — the production path is what the rest of the task wires.

If it does pass: don't commit yet, the production path still needs the bind. Move on.
If it fails: that's a sign `_sd` is constructing something that conflicts; investigate before proceeding.

- [ ] **Step 3: Wire `bind_world` + per-session reference assignment into the slug-connect saved-snapshot path.**

In `sidequest/server/session_handler.py`, locate the saved-snapshot branch at line 1281 (`saved = store.load()`). Replace the entire if/else block at 1281–1361 with:

```python
            # Restore saved snapshot, or start fresh (Bug 2 fix: resume semantics).
            saved = store.load()
            if saved is not None:
                snapshot = saved.snapshot
                # Per-player chargen gate (playtest 2026-04-25). MP: a new
                # player_id joining a slug that already has a character must
                # route to chargen, not auto-claim the existing PC. Use the
                # snapshot.player_seats binding when present; fall back to
                # legacy "any character" gate for solo / pre-MP saves where
                # player_seats is empty.
                if snapshot.player_seats:
                    has_character = player_id in snapshot.player_seats
                    gate_branch = "player_seats"
                else:
                    has_character = bool(snapshot.characters)
                    gate_branch = "legacy_any_character"
                logger.info(
                    "session.chargen_gate slug=%s player_id=%s branch=%s "
                    "has_character=%s seat_count=%d character_count=%d",
                    slug,
                    player_id,
                    gate_branch,
                    has_character,
                    len(snapshot.player_seats),
                    len(snapshot.characters),
                )
                _watcher_publish(
                    "session_chargen_gate",
                    {
                        "slug": slug,
                        "player_id": player_id,
                        "branch": gate_branch,
                        "has_character": has_character,
                        "seat_count": len(snapshot.player_seats),
                        "character_count": len(snapshot.characters),
                        "seated_player_ids": list(snapshot.player_seats.keys()),
                    },
                    component="session",
                )
                # Rename-on-resume: pre-fix saves stored ``core.name`` as the
                # opaque player UUID because chargen used ``with_lobby_name``
                # AFTER the name fix landed. Detect the UUID pattern and
                # swap in the lobby display_name on resume, then persist so
                # the rename sticks and the next turn's PARTY_STATUS sees the
                # real name. See pingpong 2026-04-24 "Resumed character shows
                # UUID as name" (medium, user-visible everywhere).
                renamed = _rename_resumed_character_if_uuid(
                    snapshot=snapshot,
                    display_name=display_name,
                    player_id=player_id,
                )
                # ADR-037 Python port: bind the canonical snapshot to the
                # room BEFORE the rename-save below. Idempotent — if a peer
                # got here first, our load is discarded and we observe the
                # already-bound snapshot.
                room.bind_world(snapshot=snapshot, store=store)
                # All subsequent reads must come from the canonical room
                # binding (which may differ from our local ``snapshot`` if
                # we lost the bind race).
                snapshot = room.snapshot  # type: ignore[assignment]
                if renamed:
                    room.save()
                    logger.info(
                        "session.slug_resumed.renamed_uuid player_id=%s "
                        "old=%s new=%s",
                        player_id,
                        player_id,  # equal to the pre-rename value
                        display_name,
                    )
                logger.info(
                    "session.slug_resumed genre=%s world=%s slug=%s turn=%s",
                    row.genre_slug,
                    row.world_slug,
                    slug,
                    snapshot.turn_manager.interaction,
                )
            else:
                snapshot = GameSnapshot(
                    genre_slug=row.genre_slug,
                    world_slug=row.world_slug,
                    location="Unknown",
                )
                store.init_session(row.genre_slug, row.world_slug)
                # ADR-037 Python port: bind the fresh snapshot to the room
                # so the second-connect handler observes the same object.
                room.bind_world(snapshot=snapshot, store=store)
                snapshot = room.snapshot  # type: ignore[assignment]
                has_character = False
                logger.info(
                    "session.slug_new_session genre=%s world=%s slug=%s",
                    row.genre_slug,
                    row.world_slug,
                    slug,
                )
```

- [ ] **Step 4: Run the existing slug-connect tests to confirm no regression.**

```bash
uv run pytest tests/server/test_session_handler_slug_connect.py tests/server/test_session_handler_slug_resumed.py -v 2>&1 | tail -10
```

Expected: all PASS (existing 8 + 8 ≈ 16 tests).

- [ ] **Step 5: Run the new wiring test.**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py::test_two_handlers_share_room_snapshot_after_bind -v
```

Expected: PASS.

- [ ] **Step 6: Full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `741 passed, 2 skipped` (740 from Task 1 + 1 new from this task).

- [ ] **Step 7: Commit.**

```bash
git add sidequest/server/session_handler.py tests/server/test_multiplayer_party_status.py
git commit -m "$(cat <<'EOF'
feat(server): bind canonical snapshot to SessionRoom on slug-connect

ADR-037 Python port — slug-connect's first occupant loads the saved
snapshot (or constructs a fresh one) and calls room.bind_world to make
it the canonical reference for the slug. Subsequent connects observe
the existing binding (idempotent). The local ``snapshot`` variable is
rebound from ``room.snapshot`` after the bind so any subsequent reads
in the handler use the canonical object, even on the loser side of a
bind race.

UUID-rename-on-resume save now routes through ``room.save()`` instead
of the per-session ``store.save(snapshot)``.

Tests: +1 wiring test (test_two_handlers_share_room_snapshot_after_bind)
proves two handlers bound to the same room observe each other's
snapshot mutations live. Server+agents sweep: 741 passed, 2 skipped.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Bind sd.snapshot / sd.store to the room reference at every slug-connect

**Files:**
- Modify: `sidequest/server/session_handler.py` — search for the spot where `self._session_data` is constructed during slug-connect (in or near the saved-snapshot block above) and ensure `sd.snapshot` / `sd.store` reference the room's binding.

- [ ] **Step 1: Find where `_session_data` is assembled in the slug-connect path.**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -n "_session_data = _SessionData\|self._session_data = " sidequest/server/session_handler.py | head -10
```

Read the lines around the slug-connect site (the first match where `_state` is being set to `_State.Creating` or `_State.Playing` after the saved-snapshot block above). Identify the `_SessionData(...)` constructor call inside that block.

- [ ] **Step 2: Verify the `_SessionData` constructor takes `snapshot=` and `store=` kwargs.**

```bash
grep -n "class _SessionData\|@dataclass" sidequest/server/session_handler.py | head -5
```

Read the dataclass definition. The `snapshot` field should be of type `GameSnapshot` and `store` should be `SqliteStore`. Both must be assignable to the room's binding (which is the same type).

- [ ] **Step 3: Modify the slug-connect `_SessionData` construction to pass the room's snapshot/store directly.**

In the slug-connect block, change every `_SessionData(...)` constructor call inside the slug-connect branch so `snapshot=room.snapshot` and `store=room.store` (instead of the local `snapshot` / `store` variables). The local variables still exist for the chargen-gate logging above; they happen to be the same object (idempotent bind), but using `room.snapshot` makes the canonical-reference contract explicit at the call site.

If multiple `_SessionData` constructions exist in the slug-connect branch (one per state), update all of them. Do not change the legacy non-slug connect path.

If the construction reads `snapshot=snapshot, store=store` (using local names), the rebind on Step 3 of Task 2 (`snapshot = room.snapshot`) already ensures the local matches; this step is a defense-in-depth rename, not strictly required. Make the change anyway so future readers see the contract.

- [ ] **Step 4: Run the slug-connect / multiplayer test sweep.**

```bash
uv run pytest tests/server/test_session_handler_slug_connect.py tests/server/test_session_handler_slug_resumed.py tests/server/test_multiplayer_party_status.py tests/server/test_seat_claim.py tests/server/test_chargen_persist_and_play.py 2>&1 | tail -3
```

Expected: all PASS.

- [ ] **Step 5: Full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `741 passed, 2 skipped` (no count change — this task is a clarification, no new tests).

- [ ] **Step 6: Commit.**

```bash
git add sidequest/server/session_handler.py
git commit -m "$(cat <<'EOF'
refactor(server): make slug-connect SessionData take snapshot/store from room

ADR-037 Python port — slug-connect now constructs ``_SessionData`` with
``snapshot=room.snapshot`` and ``store=room.store`` directly, making
the canonical-reference contract explicit at the constructor call
site. Functionally identical to the local-variable form (the
idempotent ``bind_world`` already aligned them), but reads better and
prevents future drift if someone modifies the local variable after
the bind.

Tests: 741 passed, 2 skipped (no count change).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Route turn-end persist through `room.save()`

**Files:**
- Modify: `sidequest/server/session_handler.py:2917-2918` — turn-end save in `_execute_narration_turn`.

- [ ] **Step 1: Read the current turn-end save block.**

```bash
sed -n '2910,2935p' /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/session_handler.py
```

Note the existing code: `self._merge_peer_state_into_snapshot(sd)` (line ~2917) followed by `sd.store.save(snapshot)` (line ~2918).

- [ ] **Step 2: Replace the merge+save pair with a single `room.save()` call.**

Find the block:

```python
        try:
            # MP: merge peer chars / seats from persisted store before
            # save so Laverne's turn-end can't stomp Shirley's chargen-
            # commit (playtest 2026-04-25 multi-PC persistence loss).
            # snapshot is sd.snapshot (same identity) — merge mutates it
            # in place.
            self._merge_peer_state_into_snapshot(sd)
            sd.store.save(snapshot)
            narrative_entry = NarrativeEntry(
```

Replace with:

```python
        try:
            # ADR-037 Python port: room owns the canonical snapshot, so a
            # plain room.save() is sufficient — there is no per-session
            # divergence to merge. Falls back to sd.store.save when the
            # legacy non-slug path didn't bind a room.
            if self._room is not None:
                self._room.save()
            else:
                sd.store.save(snapshot)
            narrative_entry = NarrativeEntry(
```

- [ ] **Step 3: Run the chargen + narration tests to confirm save still works.**

```bash
uv run pytest tests/server/test_chargen_persist_and_play.py tests/server/test_session_handler.py tests/server/test_session_handler_decomposer.py tests/server/test_confrontation_dispatch_wiring.py 2>&1 | tail -3
```

Expected: all PASS.

- [ ] **Step 4: Full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `741 passed, 2 skipped` (no count change).

- [ ] **Step 5: Commit.**

```bash
git add sidequest/server/session_handler.py
git commit -m "$(cat <<'EOF'
refactor(server): turn-end persist routes through room.save()

ADR-037 Python port — turn-end save in _execute_narration_turn now
calls self._room.save() when the room is bound, which acquires the
room lock and writes the canonical snapshot. The pre-save
_merge_peer_state_into_snapshot call is removed: with the room as
canonical owner there is no divergence to merge.

Legacy non-slug path (no room bound) still falls back to
sd.store.save(snapshot) so unit tests that construct _SessionData
directly without a room continue to work.

Tests: 741 passed, 2 skipped.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Route chargen-commit persist through `room.save()`

**Files:**
- Modify: `sidequest/server/session_handler.py:2524` — chargen-commit save site.
- Modify: `sidequest/server/session_handler.py:2383` — second-commit `sd.snapshot = existing_saved.snapshot` becomes `sd.snapshot = self._room.snapshot` (or just removed entirely if redundant).

- [ ] **Step 1: Read the chargen-commit save block.**

```bash
sed -n '2518,2540p' /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/session_handler.py
```

The line `sd.store.save(sd.snapshot)` is wrapped in a `try` that updates session.persisted_at_chargen_complete telemetry. Keep the try/except shape; only swap the save call.

- [ ] **Step 2: Replace `sd.store.save(sd.snapshot)` at line ~2524.**

Find:

```python
            sd.store.save(sd.snapshot)
            span.add_event(
                "session.persisted_at_chargen_complete",
```

Replace the save call with the room-aware variant (the surrounding `try`/`span.add_event`/`logger.info` lines are untouched):

```python
            if self._room is not None:
                self._room.save()
            else:
                sd.store.save(sd.snapshot)
            span.add_event(
                "session.persisted_at_chargen_complete",
```

- [ ] **Step 3: Read the second-commit MP path (line 2383) and update.**

```bash
sed -n '2375,2400p' /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/session_handler.py
```

The current pattern is:

```python
        else:
            # MP second commit. Reuse the peer's persisted snapshot ...
            sd.snapshot = existing_saved.snapshot
            existing_names = {c.core.name for c in sd.snapshot.characters}
            if character.core.name not in existing_names:
                sd.snapshot.characters.append(character)
```

In the shared-snapshot world, `sd.snapshot` is already the room's canonical object — there is no need to re-load from the persisted store. Replace with:

```python
        else:
            # MP second commit. ADR-037 Python port: sd.snapshot is the
            # canonical room snapshot (already populated by the first
            # committer); just append our PC if not already present.
            existing_names = {c.core.name for c in sd.snapshot.characters}
            if character.core.name not in existing_names:
                sd.snapshot.characters.append(character)
```

(The `existing_saved` variable is still needed for the `is_first_commit` branch / span attributes — leave its `sd.store.load()` call alone.)

- [ ] **Step 4: Run the chargen tests.**

```bash
uv run pytest tests/server/test_chargen_persist_and_play.py tests/server/test_chargen_dispatch.py tests/server/test_chargen_summary.py tests/server/test_chargen_loadout.py 2>&1 | tail -3
```

Expected: all PASS.

- [ ] **Step 5: Run the multiplayer chargen test specifically.**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py -v 2>&1 | tail -10
```

Expected: all PASS, including the new `test_two_handlers_share_room_snapshot_after_bind`.

- [ ] **Step 6: Full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `741 passed, 2 skipped` (no count change yet).

- [ ] **Step 7: Commit.**

```bash
git add sidequest/server/session_handler.py
git commit -m "$(cat <<'EOF'
refactor(server): chargen-commit persist routes through room.save()

ADR-037 Python port — chargen-commit save now calls room.save() when
the room is bound. The MP second-commit path no longer reassigns
``sd.snapshot = existing_saved.snapshot`` because sd.snapshot is
already the canonical room reference; the second committer just
appends their character to it directly.

Legacy non-slug path falls back to sd.store.save(sd.snapshot).

Tests: 741 passed, 2 skipped.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Route disconnect-save through `room.save()` and remove the merge

**Files:**
- Modify: `sidequest/server/session_handler.py:992-1010` — disconnect save in WS cleanup.

- [ ] **Step 1: Read the disconnect-save block.**

```bash
sed -n '985,1015p' /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/session_handler.py
```

Current:

```python
            try:
                # MP: pull peer state from persisted store before saving
                # so a stale single-PC view can't stomp the multi-PC truth
                # (playtest 2026-04-25 "Multi-PC state does not survive
                # disconnect"). No-op for solo.
                self._merge_peer_state_into_snapshot(self._session_data)
                self._session_data.store.save(self._session_data.snapshot)
                logger.info(
                    "session.disconnect_save genre=%s world=%s player=%s "
                    "char_count=%d seat_count=%d",
                    ...
                )
            except Exception as exc:
                logger.error("session.disconnect_save_failed error=%s", exc)
```

- [ ] **Step 2: Replace the merge+save pair.**

```python
            try:
                # ADR-037 Python port: room owns the canonical snapshot,
                # so a plain room.save() persists it once for every
                # session that disconnects. Legacy non-slug path falls
                # back to the per-session store.
                if self._room is not None:
                    self._room.save()
                else:
                    self._session_data.store.save(self._session_data.snapshot)
                logger.info(
                    "session.disconnect_save genre=%s world=%s player=%s "
                    "char_count=%d seat_count=%d",
                    self._session_data.genre_slug,
                    self._session_data.world_slug,
                    self._session_data.player_name,
                    len(self._session_data.snapshot.characters),
                    len(self._session_data.snapshot.player_seats),
                )
            except Exception as exc:
                logger.error("session.disconnect_save_failed error=%s", exc)
```

- [ ] **Step 3: Run disconnect-related tests.**

```bash
uv run pytest tests/server/test_session_handler.py -v -k "disconnect or cleanup" 2>&1 | tail -10
```

Expected: all PASS (or "no tests collected" — the disconnect-save branch isn't always covered by name; that's OK, the broader sweep catches it).

- [ ] **Step 4: Full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `741 passed, 2 skipped`.

- [ ] **Step 5: Commit.**

```bash
git add sidequest/server/session_handler.py
git commit -m "$(cat <<'EOF'
refactor(server): disconnect-save routes through room.save()

ADR-037 Python port — disconnect-save in the WS cleanup path now calls
self._room.save() when the room is bound. The pre-save
_merge_peer_state_into_snapshot call is removed: with the room as
canonical owner the disconnecting session's view IS the canonical
view; nothing to merge.

Legacy non-slug path falls back to per-session store.save.

Tests: 741 passed, 2 skipped.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Delete `_merge_peer_state_into_snapshot` and its tests

**Files:**
- Modify: `sidequest/server/session_handler.py:3951+` — delete the helper method and its watcher import side effects (if any).
- Modify: `tests/server/test_multiplayer_party_status.py` — delete 5 merge tests + `_saved_snapshot_with` helper.

- [ ] **Step 1: Confirm no remaining call sites.**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -n "_merge_peer_state_into_snapshot" sidequest/server/session_handler.py
```

Expected output: only the method definition (no callers remaining after Tasks 4 / 5 / 6). If any callers are still listed, fix them before continuing.

- [ ] **Step 2: Delete the helper method.**

In `sidequest/server/session_handler.py`, find:

```python
    def _merge_peer_state_into_snapshot(self, sd: _SessionData) -> None:
        """Pull peer characters / seat bindings from the persisted store
        ...
```

Delete the entire method (definition through end of method body, up to but not including the next method def or class section header). The method is approximately 65 lines including its docstring.

- [ ] **Step 3: Delete the merge tests.**

In `tests/server/test_multiplayer_party_status.py`, delete:

- The header comment block `# --- _merge_peer_state_into_snapshot — playtest 2026-04-25 multi-PC persistence ---`
- The helper `def _saved_snapshot_with(...)`
- `test_merge_peer_state_pulls_peer_chars_and_seats_from_persisted`
- `test_merge_peer_state_local_wins_for_shared_character_names`
- `test_merge_peer_state_noop_for_solo`
- `test_merge_peer_state_noop_when_persisted_missing`
- `test_merge_peer_state_swallows_load_errors`

These all live in the section added by `2e41414`. Use grep to find the section start:

```bash
grep -n "_merge_peer_state\|_saved_snapshot_with" tests/server/test_multiplayer_party_status.py
```

Delete from the section header line through the last `assert ...` of the final test.

- [ ] **Step 4: Run the multiplayer party status suite.**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py -v 2>&1 | tail -15
```

Expected: 12 tests collected (was 17 before deletion of 5; +1 added in Task 2 = 13 — wait, recount).

Recount: pre-deletion count = 8 original + 4 resolver (Task from a73ad21) + 5 merge (2e41414) + 1 shared-room (Task 2 of this plan) = 18.
Post-deletion: 8 + 4 + 0 + 1 = 13. Expected 13 PASSED.

- [ ] **Step 5: Full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `736 passed, 2 skipped` (741 from Task 6 - 5 deleted tests = 736).

- [ ] **Step 6: Confirm the helper method is gone.**

```bash
grep -rn "_merge_peer_state_into_snapshot\|peer_state_merged" sidequest/ tests/ 2>&1
```

Expected: no matches (the helper, its callers, its log/watcher event, and its tests are all gone).

- [ ] **Step 7: Commit.**

```bash
git add sidequest/server/session_handler.py tests/server/test_multiplayer_party_status.py
git commit -m "$(cat <<'EOF'
refactor(server): delete _merge_peer_state_into_snapshot band-aid

ADR-037 Python port — the load-merge-save helper is no longer needed:
SessionRoom now owns the canonical GameSnapshot, every WS session
holds a Python reference to the same object, and every save site
routes through room.save(). There is no per-session divergence to
merge.

Removed:
- sidequest/server/session_handler.py: _merge_peer_state_into_snapshot
  method (was ~65 LOC) and its session.peer_state_merged log line +
  watcher event.
- tests/server/test_multiplayer_party_status.py: 5 merge tests +
  _saved_snapshot_with helper.

The 4 resolver tests added in a73ad21 (which test the orthogonal
_resolve_self_character helper) are kept; they remain relevant.

Tests: 736 passed, 2 skipped (-5 deleted, baseline restored).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Add the remaining shared-room wiring tests

**Files:**
- Modify: `tests/server/test_multiplayer_party_status.py` — add 3 more shared-room tests on top of the 1 added in Task 2.

- [ ] **Step 1: Append the additional tests.**

Append to `tests/server/test_multiplayer_party_status.py`:

```python
def test_chargen_commit_visible_to_peer_handler_immediately() -> None:
    """ADR-037 regression: when peer commits chargen, our handler's
    sd.snapshot reflects both PCs and both seats without reload.
    """
    from pathlib import Path as _Path
    from sidequest.server.session_handler import WebSocketSessionHandler

    room = SessionRoom(slug="2026-04-25-chargen-share", mode=GameMode.MULTIPLAYER)
    snap = GameSnapshot(
        genre_slug="caverns_and_claudes",
        world_slug="mawdeep",
        location="Entrance",
    )
    snap.characters = []
    snap.player_seats = {}
    store = MagicMock()
    room.bind_world(snapshot=snap, store=store)

    handler_a = WebSocketSessionHandler(save_dir=_Path("/tmp/sq-test-saves"))
    handler_a._room = room

    handler_b = WebSocketSessionHandler(save_dir=_Path("/tmp/sq-test-saves"))
    handler_b._room = room

    # Player A's chargen-commit equivalent: append PC + record seat in
    # the canonical snapshot.
    laverne = _char("Laverne")
    room.snapshot.characters.append(laverne)
    room.snapshot.player_seats["p:laverne"] = "Laverne"

    # Player B observes both immediately via the same reference.
    assert [c.core.name for c in room.snapshot.characters] == ["Laverne"]
    assert room.snapshot.player_seats == {"p:laverne": "Laverne"}

    # Player B's chargen-commit equivalent: same snapshot.
    shirley = _char("Shirley")
    room.snapshot.characters.append(shirley)
    room.snapshot.player_seats["p:shirley"] = "Shirley"

    # Player A observes both immediately.
    assert sorted(c.core.name for c in room.snapshot.characters) == [
        "Laverne",
        "Shirley",
    ]
    assert room.snapshot.player_seats == {
        "p:laverne": "Laverne",
        "p:shirley": "Shirley",
    }


def test_room_save_routes_through_canonical_store() -> None:
    """room.save() persists the canonical snapshot via the canonical
    store. Verifies the per-session store.save calls have been removed
    in favor of the room-level save.
    """
    room = SessionRoom(slug="slug", mode=GameMode.MULTIPLAYER)
    snap = GameSnapshot(
        genre_slug="caverns_and_claudes",
        world_slug="mawdeep",
        location="Entrance",
    )
    store = MagicMock()
    room.bind_world(snapshot=snap, store=store)

    room.save()

    store.save.assert_called_once_with(snap)


def test_solo_path_unaffected_by_shared_room_model() -> None:
    """Single-occupant SOLO room round-trips through bind/save with
    identical semantics to multiplayer. Regression guard for the
    'don't break solo' constraint in the shared-snapshot refactor.
    """
    room = SessionRoom(slug="2026-04-25-solo", mode=GameMode.SOLO)
    snap = GameSnapshot(
        genre_slug="caverns_and_claudes",
        world_slug="mawdeep",
        location="Entrance",
    )
    snap.characters = [_char("Solo")]
    store = MagicMock()
    room.bind_world(snapshot=snap, store=store)

    assert room.snapshot is snap
    assert [c.core.name for c in room.snapshot.characters] == ["Solo"]

    room.save()
    store.save.assert_called_once_with(snap)
```

- [ ] **Step 2: Run the multiplayer party status suite.**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py -v 2>&1 | tail -10
```

Expected: 16 PASSED (13 from after Task 7 + 3 new).

- [ ] **Step 3: Full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `739 passed, 2 skipped` (736 from Task 7 + 3 new = 739).

Wait — recount: end-state target from the spec is 738 = baseline 736 - 5 deleted + 4 (party_status) + 3 (session_room) = 738. We added 1 in Task 2 + 3 here = 4 in party_status. + 4 in session_room (3 from Task 1 + the 4th was `test_close_store_when_unbound_is_noop` — that's still 4 in session_room). 736 - 5 + 4 + 4 = 739.

So actual end-state: **739 passed, 2 skipped**. The spec's "738" was off by one — Task 1 added 4 session_room tests (bind, idempotent, close-once, close-unbound) not 3. This is fine; the spec acceptance criterion stays "all tests green" and the count reconciles.

- [ ] **Step 4: Commit.**

```bash
git add tests/server/test_multiplayer_party_status.py
git commit -m "$(cat <<'EOF'
test(server): add shared-room wiring tests for ADR-037 Python port

Three additional tests in test_multiplayer_party_status.py covering:
- chargen_commit_visible_to_peer_handler_immediately — both characters
  + player_seats entries appear in the shared snapshot for both
  handlers as soon as one mutates.
- room_save_routes_through_canonical_store — room.save() calls
  store.save(snapshot) exactly once with the canonical reference.
- solo_path_unaffected_by_shared_room_model — single-occupant SOLO
  round-trip behaves identically to MP (regression guard).

Tests: 739 passed, 2 skipped (+3 from this commit).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Final verification, lint pass, push

**Files:** none modified.

- [ ] **Step 1: Lint the changed files.**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/server/session_room.py sidequest/server/session_handler.py tests/server/test_session_room.py tests/server/test_multiplayer_party_status.py 2>&1 | tail -10
```

Expected: 0 new errors. Pre-existing errors in untouched code are out of scope (do not fix them in this branch).

- [ ] **Step 2: Format-check.**

```bash
uv run ruff format --check sidequest/server/session_room.py sidequest/server/session_handler.py tests/server/test_session_room.py tests/server/test_multiplayer_party_status.py
```

If any formatting issues are flagged, fix them with `uv run ruff format <files>` and `git add` + amend the most recent commit.

- [ ] **Step 3: Final full sweep.**

```bash
uv run pytest tests/server/ tests/agents/ 2>&1 | tail -3
```

Expected: `739 passed, 2 skipped`.

- [ ] **Step 4: Push develop.**

```bash
git push origin develop
```

Expected: 8 commits land on origin/develop (Task 1 through Task 8 — Task 9 has no commit).

- [ ] **Step 5: Update the ping-pong file with a brief note.**

The shared-room work isn't a ping-pong-tracked bug, but Keith asked "fix this properly" — leaving a one-paragraph note in the ping-pong's "OQ-2 sync follow-up" section helps OQ-2 know the band-aid is gone. Append:

```markdown
## OQ-1 architectural note — 2026-04-25 (shared Room.snapshot, ADR-037)

`_merge_peer_state_into_snapshot` is removed. `SessionRoom` now owns
the canonical `GameSnapshot` for its slug; every WS session holds a
Python reference to the same object, and every save site routes
through `room.save()`. The "Multi-PC state does not survive
disconnect" bug (status: verified) remains fixed — the band-aid was
never doing the heavy lifting once the design was right. Spec at
`docs/superpowers/specs/2026-04-25-shared-room-snapshot-design.md`.

Per-session world-state divergence concerns flagged in the deferred
"Each player's narrative pane shows the other player's narration too"
entry are NOT addressed here — that's perception-rewriter / projection
filter wiring (separate story).
```

Edit `/Users/slabgorb/Projects/sq-playtest-pingpong.md` to add this section. Do not commit (the ping-pong file is not in any repo).

---

## Self-Review

**Spec coverage:** Every section of the spec maps to a task:

- "SessionRoom additions" → Task 1
- "Slug-connect bind path" → Tasks 2 + 3
- "Save sites" — disconnect / chargen / turn-end / UUID-rename → Tasks 6 / 5 / 4 / 2 (UUID-rename rolled into Task 2 because it lives in the same block)
- "Removed _merge_peer_state_into_snapshot" → Task 7
- "_SessionData changes" → Tasks 2 + 3
- "Solo path" — covered by `test_solo_path_unaffected_by_shared_room_model` in Task 8
- "Concurrency" — handled by `_lock` in Task 1
- "Compatibility" — implicitly by leaving the legacy non-slug path's `sd.store.save` fallback in Tasks 4 / 5 / 6
- All 6 acceptance criteria are verified by the test counts and the final sweep at Task 9 step 3.

**Placeholder scan:** No "TBD"/"TODO"/vague-handler steps. Every code block contains the actual code; every command has expected output.

**Type / signature consistency:** `bind_world(snapshot=, store=)` (Task 1) is called with the same kwarg shape in Task 2. `room.snapshot` / `room.store` are used as properties everywhere. `room.save()` takes no args everywhere.

**One acknowledged drift from the spec:** The spec said end-state "738 passed, 2 skipped"; the actual end-state per Task 9 is 739 because Task 1 adds 4 session_room tests instead of the 3 the spec listed (the 4th being `test_close_store_when_unbound_is_noop`, which is small and worth keeping for a clean "no-bind safety" guard). The acceptance criterion "all tests green" still holds.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-25-shared-room-snapshot.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

The plan is sequential (each task depends on the previous), so subagent-driven gets less benefit than usual but still helps with context isolation per task. Inline execution is fine here — 8 small commits, all on `develop`, no parallelism gain available.

Which approach?
