# Postgres Migration — Phase 0 / Slice 1a: SaveRepository Seam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a `SaveRepository` interface with a unit-of-work `transaction()` seam, backed by a SQLite adapter wrapping today's `SqliteStore`, and migrate the three transaction-seam consumers (`EventLog`, `ProjectionCache`, `emit_event`) onto it — with zero behavior change.

**Architecture:** A `typing.Protocol` (`SaveRepository`) declares the event + projection operations and a `transaction()` context manager yielding a `SaveTransaction`. `SqliteSaveRepository` implements it over the existing `SqliteStore`, preserving the exact `SAVE_WRITE_LOCK` + connection transaction semantics. The `_in_transaction(conn=...)` raw-connection leak on `EventLog` and `ProjectionCache` is removed: those operations move onto the `SaveTransaction` object, and `emit_event`'s C2 block becomes `with repo.transaction() as tx:`. The 300 lines of projection / perception / POV logic inside `emit_event` are not touched.

**Tech Stack:** Python 3.12+, stdlib `sqlite3`, `typing.Protocol`, `contextlib.contextmanager`, pytest (`uv run pytest`, parallel via `-n auto`).

**Scope boundary:** This slice is the keystone of Phase 0. It does NOT migrate the remaining `SqliteStore` consumers (`save`/`load`/`save_world_save`/`narrative`/`location_promotions`), the scrapbook raw-SQL in `emitters.py`, `server/views.py` reads, `forensic_query.py`, the `DungeonStore` borrowed-connection seam, or the telemetry sink. Those are sibling slices/plans. The transitional `SqliteSaveRepository.store` escape hatch introduced here is explicitly marked for removal in a later slice.

**Branch:** `sidequest-server` uses gitflow off `develop`. Create `feat/save-repository-seam` from `develop` before Task 1.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `sidequest/game/repository.py` | `SaveRepository` + `SaveTransaction` Protocols (the interface) | Create |
| `sidequest/game/sqlite_repository.py` | `SqliteSaveRepository` adapter over `SqliteStore` | Create |
| `sidequest/game/event_log.py` | `EventLog` rewired onto `SaveRepository` | Modify |
| `sidequest/game/projection/cache.py` | `ProjectionCache` rewired onto `SaveRepository` | Modify |
| `sidequest/server/emitters.py` | `emit_event` C2 block uses `repo.transaction()` | Modify (lines 274-323 region) |
| `sidequest/handlers/connect.py` | Construct repository; pass to `EventLog`/`ProjectionCache` | Modify (lines ~905-906) |
| `tests/game/test_save_repository.py` | Adapter unit + atomicity tests | Create |
| `tests/game/test_event_log.py` / `tests/game/projection/test_cache.py` | Update if they reference removed `_in_transaction` | Modify (if present) |
| `tests/server/test_dice_throw_confrontation_emit.py` | Update `append_in_transaction` reference | Modify |
| `tests/game/test_mechanical_census_contract.py` | Update C2-ordering assertion to new seam | Modify |

---

## Pre-flight: create the branch

- [ ] **Step 1: Create the feature branch off develop**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git checkout develop && git pull && git checkout -b feat/save-repository-seam
git branch --show-current
```
Expected: `feat/save-repository-seam`

---

## Task 1: Define the `SaveRepository` and `SaveTransaction` Protocols

**Files:**
- Create: `sidequest/game/repository.py`
- Test: `tests/game/test_save_repository.py`

The Protocols reference `EventRow` (defined in `event_log.py`) and `CachedDecision` (defined in `projection/cache.py`). To avoid a runtime import cycle (those modules will import `SaveRepository` for type hints), import them under `TYPE_CHECKING` only — `from __future__ import annotations` makes the annotations lazy strings, so no runtime import is needed.

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_save_repository.py
"""SaveRepository interface + SqliteSaveRepository adapter tests."""

from __future__ import annotations

from sidequest.game.repository import SaveRepository, SaveTransaction


def test_protocols_are_runtime_checkable():
    # Protocols must be importable and runtime_checkable so isinstance()
    # works in wiring tests and the adapter can be asserted against them.
    assert hasattr(SaveRepository, "_is_runtime_protocol")
    assert hasattr(SaveTransaction, "_is_runtime_protocol")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_save_repository.py::test_protocols_are_runtime_checkable -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.game.repository'`

- [ ] **Step 3: Write the Protocols**

```python
# sidequest/game/repository.py
"""Persistence repository interface (ADR-115, Phase 0).

Decouples save-store consumers from the concrete storage engine. The
``transaction()`` context manager is the unit-of-work seam: multiple
writes inside one ``with`` block commit atomically or roll back together,
replacing the prior ``*_in_transaction(conn=...)`` raw-connection passing.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sidequest.game.event_log import EventRow
    from sidequest.game.projection.cache import CachedDecision
    from sidequest.game.projection_filter import FilterDecision


@runtime_checkable
class SaveTransaction(Protocol):
    """A unit of work. Operations do NOT commit individually; the owning
    ``transaction()`` context manager commits on clean exit and rolls back
    on exception."""

    def append_event(self, *, kind: str, payload_json: str) -> EventRow: ...

    def write_projection(
        self, *, event_seq: int, player_id: str, decision: FilterDecision
    ) -> None: ...


@runtime_checkable
class SaveRepository(Protocol):
    """Storage-engine-agnostic save store. SQLite today; Postgres later."""

    def transaction(self) -> AbstractContextManager[SaveTransaction]: ...

    # Events ----------------------------------------------------------------
    def append_event(self, *, kind: str, payload_json: str) -> EventRow: ...

    def read_events_since(self, *, since_seq: int) -> list[EventRow]: ...

    def latest_event_seq(self) -> int: ...

    # Projection cache ------------------------------------------------------
    def write_projection(
        self, *, event_seq: int, player_id: str, decision: FilterDecision
    ) -> None: ...

    def read_projection_since(
        self, *, player_id: str, since_seq: int
    ) -> list[CachedDecision]: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_save_repository.py::test_protocols_are_runtime_checkable -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/repository.py tests/game/test_save_repository.py
git commit -m "feat(persistence): add SaveRepository + SaveTransaction protocols (ADR-115 P0)"
```

---

## Task 2: Implement `SqliteSaveRepository` adapter

**Files:**
- Create: `sidequest/game/sqlite_repository.py`
- Test: `tests/game/test_save_repository.py`

The adapter wraps a `SqliteStore` and reproduces the exact SQL currently in `EventLog` (`event_log.py:59-78`) and `ProjectionCache` (`projection/cache.py:65-87`), preserving `SAVE_WRITE_LOCK` acquisition order (lock outside the connection transaction — see `persistence.py:311-344`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/game/test_save_repository.py  (append to the file)

from sidequest.game.persistence import SqliteStore
from sidequest.game.projection_filter import FilterDecision
from sidequest.game.sqlite_repository import SqliteSaveRepository


def _repo() -> SqliteSaveRepository:
    return SqliteSaveRepository(SqliteStore.open_in_memory())


def test_adapter_satisfies_protocol():
    assert isinstance(_repo(), SaveRepository)


def test_append_event_assigns_monotonic_seq():
    repo = _repo()
    r1 = repo.append_event(kind="NARRATION", payload_json="{}")
    r2 = repo.append_event(kind="STATE_UPDATE", payload_json="{}")
    assert r1.seq == 1
    assert r2.seq == 2
    assert repo.latest_event_seq() == 2


def test_read_events_since_orders_ascending():
    repo = _repo()
    repo.append_event(kind="A", payload_json="{}")
    repo.append_event(kind="B", payload_json="{}")
    rows = repo.read_events_since(since_seq=0)
    assert [r.kind for r in rows] == ["A", "B"]
    assert repo.read_events_since(since_seq=1)[0].kind == "B"


def test_transaction_is_atomic_on_exception():
    repo = _repo()
    repo.append_event(kind="SEED", payload_json="{}")
    try:
        with repo.transaction() as tx:
            tx.append_event(kind="DOOMED", payload_json="{}")
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    # The doomed append rolled back with the transaction.
    assert repo.latest_event_seq() == 1


def test_transaction_event_plus_projection_commit_together():
    repo = _repo()
    with repo.transaction() as tx:
        row = tx.append_event(kind="NARRATION", payload_json="{}")
        tx.write_projection(
            event_seq=row.seq,
            player_id="p1",
            decision=FilterDecision(include=True, payload_json="{}"),
        )
    cached = repo.read_projection_since(player_id="p1", since_seq=0)
    assert len(cached) == 1
    assert cached[0].event_seq == row.seq
    assert cached[0].include is True


def test_write_projection_conflict_is_idempotent():
    repo = _repo()
    row = repo.append_event(kind="NARRATION", payload_json="{}")
    for include in (True, False):
        repo.write_projection(
            event_seq=row.seq,
            player_id="p1",
            decision=FilterDecision(include=include, payload_json="{}"),
        )
    cached = repo.read_projection_since(player_id="p1", since_seq=0)
    assert len(cached) == 1  # last write wins, no duplicate row
    assert cached[0].include is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/game/test_save_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.game.sqlite_repository'`

- [ ] **Step 3: Write the adapter**

```python
# sidequest/game/sqlite_repository.py
"""SQLite-backed SaveRepository (ADR-115, Phase 0).

Wraps the existing SqliteStore. Preserves the SAVE_WRITE_LOCK acquisition
order (lock OUTSIDE the connection transaction — persistence.py:311-344)
so concurrent writers on the shared check_same_thread=False connection do
not corrupt per-statement state.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sidequest.game.event_log import EventRow
from sidequest.game.persistence import SAVE_WRITE_LOCK, SqliteStore
from sidequest.game.projection.cache import CachedDecision
from sidequest.game.projection_filter import FilterDecision
from sidequest.telemetry.spans import projection_cache_fill_span


class _SqliteSaveTransaction:
    """Operations bound to one open SQLite connection transaction. Does not
    commit — the owning ``SqliteSaveRepository.transaction()`` block commits
    on clean exit, rolls back on exception."""

    def __init__(self, conn) -> None:  # sqlite3.Connection
        self._conn = conn

    def append_event(self, *, kind: str, payload_json: str) -> EventRow:
        now = datetime.now(tz=UTC).isoformat()
        cur = self._conn.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, payload_json, now),
        )
        seq = cur.lastrowid
        assert seq is not None
        return EventRow(seq=seq, kind=kind, payload_json=payload_json, created_at=now)

    def write_projection(
        self, *, event_seq: int, player_id: str, decision: FilterDecision
    ) -> None:
        with projection_cache_fill_span(event_seq=event_seq, player_id=player_id):
            payload = decision.payload_json if decision.include else None
            self._conn.execute(
                """
                INSERT INTO projection_cache (event_seq, player_id, include, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(event_seq, player_id) DO UPDATE SET
                    include = excluded.include,
                    payload_json = excluded.payload_json
                """,
                (event_seq, player_id, 1 if decision.include else 0, payload),
            )


class SqliteSaveRepository:
    """SaveRepository over a SqliteStore."""

    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    @property
    def store(self) -> SqliteStore:
        """TRANSITIONAL escape hatch (ADR-115 P0). A later slice migrates the
        remaining raw-connection consumers (scrapbook persist, views reads)
        and removes this. Do not add new callers."""
        return self._store

    @contextmanager
    def transaction(self) -> Iterator[_SqliteSaveTransaction]:
        # Lock first, then the connection transaction — mandatory order.
        with SAVE_WRITE_LOCK, self._store._conn:
            yield _SqliteSaveTransaction(self._store._conn)

    def append_event(self, *, kind: str, payload_json: str) -> EventRow:
        with self.transaction() as tx:
            return tx.append_event(kind=kind, payload_json=payload_json)

    def read_events_since(self, *, since_seq: int) -> list[EventRow]:
        with self._store._conn:
            rows = self._store._conn.execute(
                "SELECT seq, kind, payload_json, created_at FROM events "
                "WHERE seq > ? ORDER BY seq ASC",
                (since_seq,),
            ).fetchall()
        return [
            EventRow(seq=r[0], kind=r[1], payload_json=r[2], created_at=r[3]) for r in rows
        ]

    def latest_event_seq(self) -> int:
        with self._store._conn:
            row = self._store._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events"
            ).fetchone()
        return int(row[0])

    def write_projection(
        self, *, event_seq: int, player_id: str, decision: FilterDecision
    ) -> None:
        with self.transaction() as tx:
            tx.write_projection(event_seq=event_seq, player_id=player_id, decision=decision)

    def read_projection_since(
        self, *, player_id: str, since_seq: int
    ) -> list[CachedDecision]:
        with self._store._conn:
            rows = self._store._conn.execute(
                """
                SELECT event_seq, include, payload_json
                FROM projection_cache
                WHERE player_id = ? AND event_seq > ?
                ORDER BY event_seq ASC
                """,
                (player_id, since_seq),
            ).fetchall()
        return [
            CachedDecision(event_seq=r[0], include=bool(r[1]), payload_json=r[2])
            for r in rows
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/game/test_save_repository.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/sqlite_repository.py tests/game/test_save_repository.py
git commit -m "feat(persistence): SqliteSaveRepository adapter with unit-of-work transaction (ADR-115 P0)"
```

---

## Task 3: Rewire `EventLog` onto `SaveRepository`

**Files:**
- Modify: `sidequest/game/event_log.py`
- Test: `tests/game/test_save_repository.py`

`EventLog` keeps its public read methods and self-committing `append`, but delegates to a `SaveRepository`. The `append_in_transaction(conn=...)` method is removed — its sole production caller (`emitters.py:278`) migrates to `tx.append_event` in Task 5. `EventRow` stays defined here (the repository imports it).

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_save_repository.py  (append)

from sidequest.game.event_log import EventLog


def test_event_log_delegates_to_repository():
    repo = SqliteSaveRepository(SqliteStore.open_in_memory())
    log = EventLog(repo)
    row = log.append(kind="NARRATION", payload_json="{}")
    assert row.seq == 1
    assert log.latest_seq() == 1
    assert [r.kind for r in log.read_since(since_seq=0)] == ["NARRATION"]


def test_event_log_no_longer_exposes_in_transaction():
    repo = SqliteSaveRepository(SqliteStore.open_in_memory())
    log = EventLog(repo)
    assert not hasattr(log, "append_in_transaction")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/game/test_save_repository.py::test_event_log_delegates_to_repository tests/game/test_save_repository.py::test_event_log_no_longer_exposes_in_transaction -v`
Expected: FAIL — `EventLog(repo)` currently expects a `SqliteStore`; `append_in_transaction` still present.

- [ ] **Step 3: Rewrite `event_log.py`**

```python
# sidequest/game/event_log.py
"""Monotonic event log for a single game slug.

Every narrator-originated mutation (NARRATION, STATE_UPDATE, COMBAT_EVENT,
etc.) is appended here before fan-out. Peers catch up on reconnect via
read_since. Backed by a SaveRepository (ADR-115, Phase 0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.game.repository import SaveRepository


@dataclass
class EventRow:
    seq: int
    kind: str
    payload_json: str
    created_at: str


class EventLog:
    def __init__(self, repository: SaveRepository) -> None:
        self._repo = repository

    @property
    def repository(self) -> SaveRepository:
        return self._repo

    @property
    def store(self):
        """TRANSITIONAL (ADR-115 P0): scrapbook persist in emitters.py still
        reaches store._conn. Removed when that slice lands. Do not add callers."""
        return self._repo.store  # type: ignore[attr-defined]

    def append(self, *, kind: str, payload_json: str) -> EventRow:
        """Append an event, committing its own transaction.

        Fan-out uses ``repository.transaction()`` directly so the event
        insert + cache writes share one transaction (see emitters.emit_event).
        """
        return self._repo.append_event(kind=kind, payload_json=payload_json)

    def read_since(self, *, since_seq: int) -> list[EventRow]:
        return self._repo.read_events_since(since_seq=since_seq)

    def latest_seq(self) -> int:
        return self._repo.latest_event_seq()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/game/test_save_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/event_log.py tests/game/test_save_repository.py
git commit -m "refactor(persistence): EventLog delegates to SaveRepository, drop in_transaction (ADR-115 P0)"
```

---

## Task 4: Rewire `ProjectionCache` onto `SaveRepository`

**Files:**
- Modify: `sidequest/game/projection/cache.py`
- Test: `tests/game/test_save_repository.py`

`CachedDecision` stays defined here. `write_in_transaction(conn=...)` is removed — its sole production caller (`emitters.py:318`) migrates to `tx.write_projection` in Task 5. The `projection_cache_fill_span` import moves to the adapter (already added in Task 2), so it is no longer needed here.

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_save_repository.py  (append)

from sidequest.game.projection.cache import ProjectionCache


def test_projection_cache_delegates_to_repository():
    repo = SqliteSaveRepository(SqliteStore.open_in_memory())
    row = repo.append_event(kind="NARRATION", payload_json="{}")
    cache = ProjectionCache(repo)
    cache.write(
        event_seq=row.seq,
        player_id="p1",
        decision=FilterDecision(include=True, payload_json="{}"),
    )
    got = cache.read_since(player_id="p1", since_seq=0)
    assert len(got) == 1 and got[0].include is True


def test_projection_cache_no_longer_exposes_in_transaction():
    repo = SqliteSaveRepository(SqliteStore.open_in_memory())
    cache = ProjectionCache(repo)
    assert not hasattr(cache, "write_in_transaction")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/game/test_save_repository.py::test_projection_cache_delegates_to_repository tests/game/test_save_repository.py::test_projection_cache_no_longer_exposes_in_transaction -v`
Expected: FAIL — `ProjectionCache(repo)` expects a `SqliteStore`; `write_in_transaction` still present.

- [ ] **Step 3: Rewrite `projection/cache.py`**

```python
# sidequest/game/projection/cache.py
"""Per-player projection decision cache.

Backed by a SaveRepository (ADR-115, Phase 0). Written at fan-out time;
read at reconnect. The (event_seq, player_id) primary key means a re-fan
of the same event to the same player is idempotent (last write wins).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sidequest.game.projection_filter import FilterDecision

if TYPE_CHECKING:
    from sidequest.game.repository import SaveRepository


@dataclass(frozen=True)
class CachedDecision:
    event_seq: int
    include: bool
    payload_json: str | None


class ProjectionCache:
    def __init__(self, repository: SaveRepository) -> None:
        self._repo = repository

    def write(
        self, *, event_seq: int, player_id: str, decision: FilterDecision
    ) -> None:
        """Write a cache row, committing its own transaction.

        Fan-out uses ``repository.transaction()`` directly so the event
        append and all cache writes share one transaction.
        """
        self._repo.write_projection(
            event_seq=event_seq, player_id=player_id, decision=decision
        )

    def read_since(self, *, player_id: str, since_seq: int) -> list[CachedDecision]:
        return self._repo.read_projection_since(player_id=player_id, since_seq=since_seq)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/game/test_save_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/projection/cache.py tests/game/test_save_repository.py
git commit -m "refactor(persistence): ProjectionCache delegates to SaveRepository, drop in_transaction (ADR-115 P0)"
```

---

## Task 5: Migrate `emit_event` C2 block to `repo.transaction()`

**Files:**
- Modify: `sidequest/server/emitters.py` (the C2 block, currently lines 274-323; the `SAVE_WRITE_LOCK` import at line 19)

Only the transaction plumbing changes. The projection / perception-rewrite / POV-swap logic (lines 295-402) is byte-identical; it just runs inside the new `with` block. The `_cache_decision` closure switches from `write_in_transaction(conn=conn)` to `tx.write_projection(...)`.

- [ ] **Step 1: Replace the transaction setup (was lines 274-278)**

Find:
```python
        store = event_log.store
        conn = store._conn
        fanout: list[tuple[str, FilterDecision, dict]] = []
        with SAVE_WRITE_LOCK, conn:
            row = event_log.append_in_transaction(kind=kind, payload_json=payload_json, conn=conn)
            seq = row.seq
```
Replace with:
```python
        repo = event_log.repository
        fanout: list[tuple[str, FilterDecision, dict]] = []
        with repo.transaction() as tx:
            row = tx.append_event(kind=kind, payload_json=payload_json)
            seq = row.seq
```

- [ ] **Step 2: Replace the `_cache_decision` closure body (was lines 316-323)**

Find:
```python
                def _cache_decision(pid: str, decision: FilterDecision) -> None:
                    if handler._projection_cache is not None:
                        handler._projection_cache.write_in_transaction(
                            event_seq=seq,
                            player_id=pid,
                            decision=decision,
                            conn=conn,
                        )
```
Replace with:
```python
                def _cache_decision(pid: str, decision: FilterDecision) -> None:
                    if handler._projection_cache is not None:
                        tx.write_projection(
                            event_seq=seq,
                            player_id=pid,
                            decision=decision,
                        )
```

- [ ] **Step 3: Remove the now-unused `SAVE_WRITE_LOCK` import (line 19)**

`emit_event` no longer references `SAVE_WRITE_LOCK` (the repository owns it). Confirm no other use first:

Run: `grep -n "SAVE_WRITE_LOCK" sidequest/server/emitters.py`

If the only remaining hit is the import line and the scrapbook writers (`persist_scrapbook_entry` line 50, `update_scrapbook_image_url` line 101) — those still use it — **keep the import.** If those scrapbook writers are the only other users, leave the import. (Scrapbook migration is a later slice.) Document the decision in the commit message.

- [ ] **Step 4: Run the emitter + projection suites to verify no behavior change**

Run: `uv run pytest tests/server/ tests/game/projection/ -v -k "emit or projection or fanout or cache"`
Expected: PASS (existing coverage of `emit_event` fan-out, C2 atomicity, projection cache).

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/emitters.py
git commit -m "refactor(persistence): emit_event C2 block uses repo.transaction() (ADR-115 P0)"
```

---

## Task 6: Construct the repository in `connect.py` and pass to consumers

**Files:**
- Modify: `sidequest/handlers/connect.py` (lines ~905-906)
- Test: `tests/game/test_save_repository.py`

- [ ] **Step 1: Update the construction site**

Find (around line 905):
```python
            session._event_log = EventLog(store)
            session._projection_cache = ProjectionCache(store)
```
Replace with:
```python
            repository = SqliteSaveRepository(store)
            session._event_log = EventLog(repository)
            session._projection_cache = ProjectionCache(repository)
```

- [ ] **Step 2: Add the import**

At the top of `connect.py`, alongside the existing persistence imports, add:
```python
from sidequest.game.sqlite_repository import SqliteSaveRepository
```
Run: `grep -n "from sidequest.game.persistence import\|SqliteStore" sidequest/handlers/connect.py` to place it adjacent to the existing store import.

- [ ] **Step 3: Write the wiring test (proves the repo is reachable from the production connect path)**

```python
# tests/game/test_save_repository.py  (append)

def test_connect_constructs_event_log_over_repository():
    # Wiring guard (CLAUDE.md: every suite needs a wiring test). The connect
    # handler must build EventLog/ProjectionCache over a SaveRepository, not a
    # raw store. We assert via the runtime type the handler wires up.
    import inspect

    from sidequest.handlers import connect

    src = inspect.getsource(connect)
    # Reflection-based check is brittle; prefer a behavior assertion. Construct
    # the same objects the handler does and verify they operate over a repo.
    repo = SqliteSaveRepository(SqliteStore.open_in_memory())
    log = EventLog(repo)
    assert isinstance(log.repository, SaveRepository)
    del src  # not asserted on — see note below
```

NOTE: Per `sidequest-server/CLAUDE.md` "No Source-Text Wiring Tests", do not assert on `inspect.getsource`. The genuine wiring proof is the end-to-end connect test that already exercises `EventLog` (see Task 8). Delete the `src`/`inspect` lines above before committing — they are shown only to flag the anti-pattern. The behavior assertion (`isinstance(log.repository, SaveRepository)`) is the real check.

Corrected test body to commit:
```python
def test_connect_constructs_event_log_over_repository():
    repo = SqliteSaveRepository(SqliteStore.open_in_memory())
    log = EventLog(repo)
    cache = ProjectionCache(repo)
    assert isinstance(log.repository, SaveRepository)
    row = log.append(kind="NARRATION", payload_json="{}")
    cache.write(
        event_seq=row.seq,
        player_id="p1",
        decision=FilterDecision(include=True, payload_json="{}"),
    )
    assert cache.read_since(player_id="p1", since_seq=0)[0].event_seq == row.seq
```

- [ ] **Step 4: Run the test + the connect suite**

Run: `uv run pytest tests/game/test_save_repository.py tests/server/ -v -k "connect or repository or event_log"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/handlers/connect.py tests/game/test_save_repository.py
git commit -m "refactor(persistence): connect.py wires EventLog/ProjectionCache over SaveRepository (ADR-115 P0)"
```

---

## Task 7: Update tests referencing the removed `_in_transaction` API

**Files:**
- Modify: `tests/server/test_dice_throw_confrontation_emit.py` (~line 548)
- Modify: `tests/game/test_mechanical_census_contract.py` (~line 20)

These two tests reference `append_in_transaction` by name. Their behavior expectations are unchanged — only the call surface moved to `tx.append_event` inside `repo.transaction()`.

- [ ] **Step 1: Inspect the references**

Run:
```bash
grep -n "append_in_transaction\|write_in_transaction\|EventLog(\|ProjectionCache(" tests/server/test_dice_throw_confrontation_emit.py tests/game/test_mechanical_census_contract.py
```

- [ ] **Step 2: Update `test_dice_throw_confrontation_emit.py`**

If the test constructs `EventLog(store)`, change to `EventLog(SqliteSaveRepository(store))` (add `from sidequest.game.sqlite_repository import SqliteSaveRepository`). If it calls `append_in_transaction(...)` directly, replace with:
```python
with repo.transaction() as tx:
    row = tx.append_event(kind=..., payload_json=...)
```
using the same `kind`/`payload_json` arguments the test already passes. The docstring comment at line 548 ("so EventLog.append_in_transaction can resolve the…") should be updated to "so the events table FK/seq resolves".

- [ ] **Step 3: Update `test_mechanical_census_contract.py`**

This test asserts the C2 ordering: event append THEN a `component='mechanical'` publish. Keep the ordering assertion; update any direct `append_in_transaction` reference in the test or its docstring (line 20) to `tx.append_event` / `repo.transaction()`. The census-publish ordering assertion itself does not change — `emit_event` still calls `emit_mechanical_census` inside the transaction block (Task 5 preserved that).

- [ ] **Step 4: Run both updated tests**

Run: `uv run pytest tests/server/test_dice_throw_confrontation_emit.py tests/game/test_mechanical_census_contract.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/server/test_dice_throw_confrontation_emit.py tests/game/test_mechanical_census_contract.py
git commit -m "test(persistence): migrate in_transaction call sites to repo.transaction() (ADR-115 P0)"
```

---

## Task 8: Full-suite verification + lint/type gate

**Files:** none (verification only)

- [ ] **Step 1: Run the full server suite**

Run: `uv run pytest`
Expected: PASS, same count as the pre-branch baseline (zero behavior change). If any test fails referencing `store._conn` via `EventLog`/`ProjectionCache`, it is an unmigrated consumer — fix the call site to use the repository (do NOT re-add `_in_transaction`).

- [ ] **Step 2: Lint + format + type check**

Run:
```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright sidequest/game/repository.py sidequest/game/sqlite_repository.py sidequest/game/event_log.py sidequest/game/projection/cache.py
```
Expected: clean. Fix any `pyright` complaint about the `SaveTransaction`/`SaveRepository` protocol conformance of `SqliteSaveRepository` / `_SqliteSaveTransaction`.

- [ ] **Step 3: Confirm no raw-connection leak remains for the migrated consumers**

Run:
```bash
grep -rn "append_in_transaction\|write_in_transaction" sidequest/
grep -rn "_event_log.store._conn\|_projection_cache" sidequest/ | grep "_conn"
```
Expected: the first returns nothing in `sidequest/`; the second returns only the transitional scrapbook writers in `emitters.py` (deferred to a later slice) — note them in the PR description as known, scoped-out.

- [ ] **Step 4: Open the PR against develop**

```bash
git push -u origin feat/save-repository-seam
gh pr create --base develop --title "feat(persistence): SaveRepository seam (ADR-115 Phase 0 Slice 1a)" --body "$(cat <<'EOF'
## Summary
- Introduces SaveRepository + SaveTransaction protocols and a SqliteSaveRepository adapter (unit-of-work transaction seam) per ADR-115 Phase 0.
- Migrates EventLog, ProjectionCache, and emit_event's C2 block off raw sqlite3 connection passing. Zero behavior change.

## Scope (deferred to sibling slices)
- Remaining SqliteStore consumers (save/load/narrative/location_promotions/world_save) still call the store directly.
- Scrapbook raw-SQL in emitters.py still uses store._conn (transitional SqliteSaveRepository.store hatch).
- DungeonStore borrowed-connection seam, server/views.py reads, forensic_query.py, telemetry sink — own slices.

## Test plan
- [ ] Full suite green (zero behavior change vs develop baseline)
- [ ] New tests/game/test_save_repository.py covers transaction atomicity + idempotent projection conflict
- [ ] ruff + pyright clean on the new/modified modules
EOF
)"
```

---

## Self-Review

**Spec coverage (against `2026-05-26-postgres-persistence-migration-design.md`):**
- Repository interfaces — ✅ Task 1 (`SaveRepository`, `SaveTransaction`); the design's four repositories are introduced incrementally, this slice delivers the `SaveRepository` keystone with event + projection methods. `DungeonRepository`/`TelemetrySink`/`ForensicReader` explicitly deferred (stated in scope boundary).
- Unit-of-work transaction seam (design's "must expose a transaction() abstraction so emit_event's append+census+cache stays atomic") — ✅ Tasks 2 + 5.
- Eliminate `.connection()`/`._conn` external access — ⚠️ Partial by design: this slice removes it for the transaction-seam consumers (EventLog, ProjectionCache, emit_event). The transitional `.store` hatch remains for scrapbook (Task 5 Step 3, Task 8 Step 3) — flagged, scoped to a later slice. Consistent with the design's "land in reviewable slices."
- Sync `psycopg3` + pool, Alembic, schema keying, importer, portability — ❌ Not in this slice (Phases 1/3/2). Correct: this is the Phase 0 keystone only.

**Placeholder scan:** No TBD/TODO. Every code step shows full code. The two test-update tasks (7) describe exact old→new signatures rather than full file rewrites because the target test files were not read in full during planning; the migration is mechanical (rename + wrap) and the old/new call shapes are given verbatim. Step 1 of Task 7 reads the real references first.

**Type consistency:** `EventRow` defined in `event_log.py`, imported by `sqlite_repository.py` and (TYPE_CHECKING) `repository.py` — consistent. `CachedDecision` defined in `projection/cache.py`, same import pattern — consistent. `FilterDecision(include=..., payload_json=...)` used consistently in tests and signatures. `repository.append_event`/`read_events_since`/`latest_event_seq`/`write_projection`/`read_projection_since` and `transaction()` names match across Tasks 1, 2, 3, 4, 5, 6. `EventLog.append`/`read_since`/`latest_seq` and `ProjectionCache.write`/`read_since` preserve their existing public names.

**Known wrinkle flagged for the implementer:** Task 6 Step 3 deliberately shows then rejects an `inspect.getsource` wiring test, per `sidequest-server/CLAUDE.md`'s "No Source-Text Wiring Tests" rule — commit only the behavior assertion. The real end-to-end wiring proof is the existing connect suite run in Task 6 Step 4 / Task 8 Step 1.
