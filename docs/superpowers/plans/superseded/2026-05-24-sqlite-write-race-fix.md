# SQLite Write-Race Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the doctrine the `SqliteStore.open` docstring already promises — every write through `SqliteStore._conn` is serialized by a single process-wide reentrant mutex — eliminating the `sqlite3.OperationalError: database is locked` warnings that have eaten MP telemetry on every 2026-05-18 and 2026-05-24 playtest.

**Architecture:** Add `SAVE_WRITE_LOCK = threading.RLock()` at module scope in `sidequest/game/persistence.py`. Wrap every save-DB write site (14 sites across 3 modules — full inventory below) in `with SAVE_WRITE_LOCK:` outside the existing `with conn:` transaction. Remove `watcher_hub._persist_lock` and route its two acquisitions through the new shared lock. Reentrant because the C2 event-append path calls `emit_mechanical_census(...)` inside its own transaction, which re-enters `_persist_turn_telemetry`. No schema change. No storage backend change. Single new test file enforces the contract for future writers.

**Tech Stack:** Python 3.12, `threading.RLock`, stdlib `sqlite3` (WAL, `check_same_thread=False`), pytest (+ `caplog`), `concurrent.futures.ThreadPoolExecutor` for the concurrent regression test.

**Source spec:** [`docs/superpowers/specs/2026-05-24-sqlite-write-race-fix-design.md`](../specs/2026-05-24-sqlite-write-race-fix-design.md).

---

## Pre-flight: spec deviations the plan resolves

The spec was written from a code-walk on 2026-05-24 and contains four name mismatches and one schema misstatement against `main`. The plan corrects them inline; an implementer following the plan does not need to re-read the spec for the corrections.

| Spec §4 row | Spec name | Actual name in code | Actual line |
|-------------|-----------|----------------------|-------------|
| #3 | `SqliteStore.reinitialize_slot` | **`SqliteStore.init_session`** | `persistence.py:380` |
| #8 | `emitters.insert_scrapbook_entry` | **`emitters.persist_scrapbook_entry`** | `emitters.py:29` |
| #10 | `emitters._emit_event_frame` | **`emitters.emit_event`** (the `with conn:` block at line 276 inside the larger function body) | `emitters.py:171` (func) / `emitters.py:276` (txn) |
| #11 | `persistence.ensure_game` | **`persistence.upsert_game`** | `persistence.py:794` |

**Schema deviation — FK is not present.** Spec §2 and §5 assertion #4 claim a `FOREIGN KEY (event_seq) REFERENCES events(seq) ON DELETE CASCADE` on `turn_telemetry`. The actual `CREATE TABLE turn_telemetry` at `persistence.py:184-192` declares **no FK** at all — just an integer column and an index. The architectural goal (telemetry rides the event-frame transaction atomically) is real and is enforced behaviorally by the `in_transaction` branch in `_persist_turn_telemetry` (`watcher_hub.py:396-400`). Adding the FK is **out of scope** for this fix (would be a schema migration touching every existing save file). The plan adjusts the regression test's §5 assertion #4 to a behavioral check: every non-NULL `turn_telemetry.event_seq` matches an `events.seq` row that exists in the same store — *atomicity-by-rollback*, not FK enforcement.

**One more note on `_configure_connection`.** `SqliteStore.open_in_memory()` (`persistence.py:330`) intentionally skips `_configure_connection`. That's fine; the lock fix does not depend on PRAGMAs. The regression test uses `SqliteStore.open(tmp_path / "save.db")` (file-backed) so PRAGMAs match production.

---

## File structure

Changes touch three files and add one test file. No new modules.

- **`sidequest/game/persistence.py`** — defines `SAVE_WRITE_LOCK` at module scope; nine writer sites acquire it (sites #1–#7, #11, #12). Class docstring on `SqliteStore` gets a one-line addendum.
- **`sidequest/server/emitters.py`** — three writer sites acquire `SAVE_WRITE_LOCK` (sites #8, #9, #10). The C2 site #10 is the reentry case — its inner `emit_mechanical_census(...)` call publishes events that re-enter `_persist_turn_telemetry`, which re-acquires the same lock.
- **`sidequest/telemetry/watcher_hub.py`** — `_persist_lock` deleted; `SAVE_WRITE_LOCK` imported from `sidequest.game.persistence`; sites #13, #14 acquire the imported lock.
- **`tests/server/test_save_write_lock.py`** — new file. Concurrent-writer regression test + reentrancy assertion + watcher-rename smoke test.

---

## Sequencing

The plan is structured TDD-style with one twist: the regression test cannot meaningfully fail RED until at least the lock symbol exists and one writer site is wrapped, because the pre-fix codebase silently swallows `sqlite3.OperationalError` inside `_persist_turn_telemetry`'s `try/except`. So Task 1 defines the symbol, Task 2 writes the failing test (and we verify it fails on `main` by *running it on the un-wrapped codebase* — at this point only the symbol exists, no sites use it, so the test should observe lock-races and OperationalErrors under load). Tasks 3–6 implement the wrapping site-by-site. Task 7 re-runs the test green. Tasks 8–10 finalize.

Frequent commits: one commit per task (Tasks 1–7), final commits for lint+type and smoke.

---

## Task 1: Define `SAVE_WRITE_LOCK` and document it

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py` (insert at module scope, near top, after the existing `threading` ... wait, `threading` is not currently imported — add the import too)
- Modify: `sidequest-server/sidequest/game/persistence.py:311-316` (`SqliteStore` class docstring addendum)

### Step 1.1 — Add `threading` to imports

- [ ] **Step 1.1.1: Inspect the existing import block**

Run: `sed -n '1,40p' sidequest-server/sidequest/game/persistence.py`
Expected: imports include `json`, `shutil`, `sqlite3`, `from datetime import ...`, `from pathlib import Path`, etc. `threading` is not present.

- [ ] **Step 1.1.2: Add `import threading` alphabetically among the stdlib imports**

In the stdlib import block of `persistence.py`, add:

```python
import threading
```

Place it after `import sqlite3` and before `import shutil` (alphabetical within the stdlib group). If the imports are not alphabetized, just add it in the stdlib cluster.

### Step 1.2 — Define `SAVE_WRITE_LOCK` at module scope

- [ ] **Step 1.2.1: Add the lock + doc block just above `class SqliteStore` (currently around line 308-311 — the "# SqliteStore" comment banner)**

Insert this block immediately before the `# ---...---` banner that introduces `SqliteStore`:

```python
# ---------------------------------------------------------------------------
# Process-wide save-DB write lock
# ---------------------------------------------------------------------------

# All writes through any SqliteStore._conn (or any sqlite3.Connection owned
# by SqliteStore) MUST be made inside:
#
#     with SAVE_WRITE_LOCK:
#         with conn:           # SQLite implicit transaction
#             conn.execute(...)
#
# The acquire order is mandatory: SAVE_WRITE_LOCK outside the transaction,
# never the reverse. Acquiring the transaction first and the lock second
# lets two threads both call ``conn.__enter__`` on the shared connection
# (the connection is opened with ``check_same_thread=False``, see
# ``SqliteStore.open``), corrupting the connection's per-statement state
# and producing ``sqlite3.OperationalError: database is locked``.
#
# The lock is reentrant (``threading.RLock``) because the C2 event-append
# transaction in ``sidequest.server.emitters.emit_event`` calls
# ``emit_mechanical_census(...)`` inside its open transaction, which
# publishes watcher events that re-enter ``_persist_turn_telemetry``
# (`sidequest.telemetry.watcher_hub`). Without reentrancy that re-entry
# from the same thread would deadlock.
#
# Consumer modules (kept in sync as writer sites are added):
#   - sidequest.game.persistence
#   - sidequest.server.emitters
#   - sidequest.telemetry.watcher_hub
#
# Future writers landing in any other module must import this lock and
# wrap their writes. The authoritative regression test is
# ``tests/server/test_save_write_lock.py`` — anyone adding a 15th write
# site without acquiring the lock will see it fail under concurrent load.
SAVE_WRITE_LOCK: threading.RLock = threading.RLock()
```

### Step 1.3 — Addendum to `SqliteStore` class docstring

- [ ] **Step 1.3.1: Append one sentence to the `SqliteStore` docstring**

Find the current docstring at the top of `class SqliteStore`:

```python
class SqliteStore:
    """SQLite-backed session store. One .db file per save slot.

    Uses singleton tables (session_meta, game_state) plus append-only
    narrative_log. Built on stdlib sqlite3.
    """
```

Replace with:

```python
class SqliteStore:
    """SQLite-backed session store. One .db file per save slot.

    Uses singleton tables (session_meta, game_state) plus append-only
    narrative_log. Built on stdlib sqlite3.

    All writes through ``self._conn`` must hold ``SAVE_WRITE_LOCK`` from
    this module — see the lock's module-level doc block above.
    """
```

### Step 1.4 — Verify nothing broke

- [ ] **Step 1.4.1: Run the existing persistence/telemetry tests**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_turn_telemetry_sink.py tests/game/test_persistence.py -v` (the second path may not exist — if so, just run the first).
Expected: all pre-existing tests pass. (The lock exists but nothing uses it yet — this is a no-op behavior change.)

### Step 1.5 — Commit

- [ ] **Step 1.5.1**

```bash
git -C sidequest-server add sidequest/game/persistence.py
git -C sidequest-server commit -m "feat(persistence): add SAVE_WRITE_LOCK (RLock) + acquire-order doc"
```

---

## Task 2: Write the failing regression test

**Files:**
- Create: `sidequest-server/tests/server/test_save_write_lock.py`

### Step 2.1 — Write the test file

- [ ] **Step 2.1.1: Create the test file with the full body below**

```python
"""Concurrent-writer regression test for ``SAVE_WRITE_LOCK``.

Source spec: docs/superpowers/specs/2026-05-24-sqlite-write-race-fix-design.md
Source plan: docs/superpowers/plans/2026-05-24-sqlite-write-race-fix.md

Fires concurrent writes from N=8 threads against a file-backed
``SqliteStore`` simulating one MP playtest's worth of activity:
    - 2 threads: ``store.save(snapshot)``      — snapshot-save path (site #4)
    - 2 threads: ``store.append_narrative(e)`` — narrative log     (site #6)
    - 2 threads: C2 event-append + mechanical_census stand-in
                                                — reentry case   (site #10 → #14)
    - 2 threads: bare ``publish_event(...)``   — telemetry only   (site #14)

Pre-fix (sites unwrapped): the watcher path swallows
``sqlite3.OperationalError: database is locked`` in its try/except, so
this test detects races via ``caplog`` for the
``turn_telemetry.sink_failed`` warning AND via OperationalError surfacing
from any non-telemetry writer.

Post-fix: zero failures, zero swallowed warnings, every non-NULL
``event_seq`` in ``turn_telemetry`` matches a real ``events.seq``.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from sidequest.game.persistence import SAVE_WRITE_LOCK, SqliteStore
from sidequest.telemetry.watcher_hub import bind_event_store, publish_event


# -------- helpers --------

def _open_store(tmp_path) -> SqliteStore:
    return SqliteStore.open(str(tmp_path / "save.db"))


def _append_synthetic_event(store: SqliteStore, kind: str = "NARRATION") -> int:
    """Insert one row into ``events`` and return its seq.

    Used by the C2 stand-in thread group to fire the in-transaction
    reentry path through ``publish_event`` → ``_persist_turn_telemetry``.
    """
    conn = store._conn
    cur = conn.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        (kind, "{}", "t"),
    )
    seq = cur.lastrowid
    assert seq is not None
    return int(seq)


# -------- fixtures --------

@pytest.fixture
def store(tmp_path):
    s = _open_store(tmp_path)
    bind_event_store(s)
    try:
        yield s
    finally:
        bind_event_store(None)
        s.close()


# -------- the main concurrent regression --------

ITERATIONS_PER_THREAD = 60  # 60 * 8 = 480 total ops, ≈ one playtest's worth


def test_concurrent_writers_no_race(store, caplog):
    """N=8 concurrent writers across all 4 thread groups; expect zero
    OperationalErrors and zero ``turn_telemetry.sink_failed`` warnings."""
    caplog.set_level(logging.WARNING)

    errors: list[BaseException] = []
    errors_lock = threading.Lock()

    def record(exc: BaseException) -> None:
        with errors_lock:
            errors.append(exc)

    # --- Group A: snapshot save ---
    def saver():
        from sidequest.game.session import GameSnapshot

        for _ in range(ITERATIONS_PER_THREAD):
            try:
                # Minimal snapshot — model_dump_json round-trips fine
                # even with mostly-default fields.
                snap = GameSnapshot()
                store.save(snap)
            except sqlite3.OperationalError as exc:
                record(exc)
            except Exception as exc:  # noqa: BLE001
                record(exc)

    # --- Group B: narrative append ---
    def narrator():
        from sidequest.game.session import NarrativeEntry

        for i in range(ITERATIONS_PER_THREAD):
            try:
                store.append_narrative(
                    NarrativeEntry(
                        timestamp=0,
                        round=i,
                        author="player",
                        content="x",
                        tags=[],
                    )
                )
            except sqlite3.OperationalError as exc:
                record(exc)
            except Exception as exc:  # noqa: BLE001
                record(exc)

    # --- Group C: C2 event-append + reentry through publish_event ---
    def c2_stand_in():
        """Simulates the production C2 path: hold SAVE_WRITE_LOCK and a
        ``with conn:`` open, append an event, then call publish_event
        which re-enters _persist_turn_telemetry which re-acquires the
        lock. With RLock this must not deadlock."""
        conn = store._conn
        for i in range(ITERATIONS_PER_THREAD):
            try:
                with SAVE_WRITE_LOCK:
                    with conn:
                        _append_synthetic_event(store)
                        # In-transaction publish — reentry case.
                        publish_event(
                            "state_transition",
                            {"field": "mechanical", "round": i},
                            component="mechanical_census",
                        )
            except sqlite3.OperationalError as exc:
                record(exc)
            except Exception as exc:  # noqa: BLE001
                record(exc)

    # --- Group D: telemetry-only (no open turn txn) ---
    def telemetry_only():
        for i in range(ITERATIONS_PER_THREAD):
            try:
                publish_event(
                    "state_transition",
                    {"field": "intent", "label": "explore", "round": i},
                    component="intent",
                )
            except sqlite3.OperationalError as exc:
                record(exc)
            except Exception as exc:  # noqa: BLE001
                record(exc)

    workers = [saver, saver, narrator, narrator, c2_stand_in, c2_stand_in, telemetry_only, telemetry_only]

    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futures = [pool.submit(fn) for fn in workers]
        for f in as_completed(futures):
            f.result()  # surface any uncaught thread exception

    # Assertion 1: no OperationalError observed in any thread.
    op_errors = [e for e in errors if isinstance(e, sqlite3.OperationalError)]
    assert op_errors == [], f"OperationalErrors leaked: {op_errors!r}"

    # Assertion 2: no other surprise exceptions.
    other_errors = [e for e in errors if not isinstance(e, sqlite3.OperationalError)]
    assert other_errors == [], f"unexpected thread errors: {other_errors!r}"

    # Assertion 3: telemetry sink never logged ``sink_failed``.
    sink_failed = [
        rec for rec in caplog.records
        if "turn_telemetry.sink_failed" in rec.getMessage()
    ]
    assert sink_failed == [], (
        f"turn_telemetry.sink_failed warnings: "
        f"{[r.getMessage() for r in sink_failed]}"
    )

    # Assertion 4 (atomicity, replaces spec assertion #4 — no FK in schema):
    # every non-NULL ``turn_telemetry.event_seq`` matches an existing
    # ``events.seq``. Holds iff the in-transaction branch's "ride the open
    # event-frame transaction" path persisted atomically with the event row.
    orphans = store._conn.execute(
        "SELECT t.event_seq FROM turn_telemetry t "
        "LEFT JOIN events e ON e.seq = t.event_seq "
        "WHERE t.event_seq IS NOT NULL AND e.seq IS NULL"
    ).fetchall()
    assert orphans == [], f"telemetry rows with orphan event_seq: {orphans!r}"

    # Assertion 5: at least *some* telemetry rows landed with a non-NULL
    # event_seq — proves the C2 reentry path actually fired. If this is
    # zero, group C never reached the in_transaction branch and the test
    # is testing something weaker than intended.
    inflight = store._conn.execute(
        "SELECT COUNT(*) FROM turn_telemetry WHERE event_seq IS NOT NULL"
    ).fetchone()[0]
    assert inflight > 0, "no in-transaction telemetry rows — group C never fired"


# -------- reentrancy unit test --------

def test_save_write_lock_is_reentrant():
    """The lock must be a ``threading.RLock``-shaped object that allows
    the same thread to re-acquire without blocking."""
    acquired_twice = SAVE_WRITE_LOCK.acquire(blocking=False)
    try:
        assert acquired_twice
        re = SAVE_WRITE_LOCK.acquire(blocking=False)
        try:
            assert re, "SAVE_WRITE_LOCK must be reentrant (RLock)"
        finally:
            if re:
                SAVE_WRITE_LOCK.release()
    finally:
        if acquired_twice:
            SAVE_WRITE_LOCK.release()


# -------- watcher_hub rename smoke --------

def test_watcher_hub_uses_save_write_lock():
    """After the rename, ``watcher_hub`` no longer owns a private
    ``_persist_lock``. Future writers grepping for "persist lock" should
    land on the doc block in ``persistence.py`` and nothing else."""
    from sidequest.telemetry import watcher_hub

    assert not hasattr(watcher_hub, "_persist_lock"), (
        "watcher_hub._persist_lock should have been removed and replaced "
        "by SAVE_WRITE_LOCK imported from sidequest.game.persistence"
    )
    # And the imported symbol must be the same object (not a copy).
    assert watcher_hub.SAVE_WRITE_LOCK is SAVE_WRITE_LOCK
```

### Step 2.2 — Verify the test fails RED on the un-wrapped codebase

- [ ] **Step 2.2.1: Run the new test**

Run: `cd sidequest-server && uv run pytest tests/server/test_save_write_lock.py -v`
Expected: **FAIL** on `test_concurrent_writers_no_race` — either an `OperationalError` leaked through one of the non-telemetry writer threads, or `turn_telemetry.sink_failed` was logged (the telemetry path's silent swallow). `test_watcher_hub_uses_save_write_lock` also fails because `_persist_lock` still exists.

If the test happens to pass (race conditions are stochastic), bump `ITERATIONS_PER_THREAD` to `120` and re-run. The 2026-05-18 and 2026-05-24 playtest evidence in the spec says these races fire reliably under any concurrent load; flaky-pass on first run is unlikely but not impossible.

`test_save_write_lock_is_reentrant` should **PASS** even pre-fix (Task 1 already defined the RLock).

### Step 2.3 — Commit the failing test

- [ ] **Step 2.3.1**

```bash
git -C sidequest-server add tests/server/test_save_write_lock.py
git -C sidequest-server commit -m "test(persistence): RED — concurrent SAVE_WRITE_LOCK regression"
```

---

## Task 3: Wrap all `persistence.py` writer sites (sites #1, #2, #3, #4, #5, #6, #7, #11, #12)

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py` — nine sites.

The pattern: every existing `with self._conn:` (or `with store._conn:`) becomes:

```python
with SAVE_WRITE_LOCK:
    with self._conn:
        ...
```

For sites without an explicit transaction wrapper (`append_narrative` uses `conn.execute(...)` + `conn.commit()`), wrap the whole execute+commit pair in `with SAVE_WRITE_LOCK:`.

### Step 3.1 — Site #1: `SqliteStore._init_schema` (`persistence.py:353`)

- [ ] **Step 3.1.1: Wrap the entire body**

Current:

```python
    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        self._apply_migrations()
        self._conn.commit()
```

Replace with:

```python
    def _init_schema(self) -> None:
        with SAVE_WRITE_LOCK:
            self._conn.executescript(SCHEMA_SQL)
            self._apply_migrations()
            self._conn.commit()
```

### Step 3.2 — Site #2: `SqliteStore._apply_migrations` (`persistence.py:358-374`)

- [ ] **Step 3.2.1: Wrap the ALTER TABLE in the lock**

Current:

```python
    def _apply_migrations(self) -> None:
        """Idempotent column adds ..."""
        # Story 45-31: scrapbook_entries.render_status — degradation
        # marker for the unavailable-fallback path. Older DBs created
        # before this column existed need it added.
        try:
            self._conn.execute("ALTER TABLE scrapbook_entries ADD COLUMN render_status TEXT")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
```

Replace the `try:` body with a locked variant:

```python
    def _apply_migrations(self) -> None:
        """Idempotent column adds ..."""
        # Story 45-31: scrapbook_entries.render_status — degradation
        # marker for the unavailable-fallback path. Older DBs created
        # before this column existed need it added.
        with SAVE_WRITE_LOCK:
            try:
                self._conn.execute("ALTER TABLE scrapbook_entries ADD COLUMN render_status TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
```

Note: `_init_schema` (site #1) already holds the lock when it calls `_apply_migrations`. The RLock makes this nested acquisition safe.

### Step 3.3 — Site #3: `SqliteStore.init_session` (`persistence.py:380`, txn at line 400)

- [ ] **Step 3.3.1: Wrap the existing `with self._conn:`**

Note — the SELECTs at lines 395-398 (`prior_narrative_count`, `prior_event_count`) are reads, not writes; they don't need the lock. Wrap only the write transaction:

Current (line 400-409 block):

```python
        with self._conn:
            for tbl in _PER_SLOT_TABLES:
                self._conn.execute(f"DELETE FROM {tbl}")
            now = _now_rfc3339()
            self._conn.execute(
                """INSERT OR REPLACE INTO session_meta
                   (id, genre_slug, world_slug, created_at, last_played, schema_version)
                   VALUES (1, ?, ?, ?, ?, 1)""",
                (genre_slug, world_slug, now, now),
            )
```

Replace with:

```python
        with SAVE_WRITE_LOCK:
            with self._conn:
                for tbl in _PER_SLOT_TABLES:
                    self._conn.execute(f"DELETE FROM {tbl}")
                now = _now_rfc3339()
                self._conn.execute(
                    """INSERT OR REPLACE INTO session_meta
                       (id, genre_slug, world_slug, created_at, last_played, schema_version)
                       VALUES (1, ?, ?, ?, ?, 1)""",
                    (genre_slug, world_slug, now, now),
                )
```

### Step 3.4 — Site #4: `SqliteStore.save` (`persistence.py:424`, txn at line 439)

- [ ] **Step 3.4.1: Wrap the existing `with self._conn:`**

Snapshot serialization (`snapshot.model_dump_json()` at line 436) is expensive and stays **outside** the lock — only the `INSERT/UPDATE` transaction goes inside. Per spec §6 "Behavior under load".

Current (line 439-448):

```python
        with self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO game_state (id, snapshot_json, saved_at)
                   VALUES (1, ?, ?)""",
                (state_json, now_str),
            )
            self._conn.execute(
                "UPDATE session_meta SET last_played = ? WHERE id = 1",
                (now_str,),
            )
```

Replace with:

```python
        with SAVE_WRITE_LOCK:
            with self._conn:
                self._conn.execute(
                    """INSERT OR REPLACE INTO game_state (id, snapshot_json, saved_at)
                       VALUES (1, ?, ?)""",
                    (state_json, now_str),
                )
                self._conn.execute(
                    "UPDATE session_meta SET last_played = ? WHERE id = 1",
                    (now_str,),
                )
```

### Step 3.5 — Site #5: `SqliteStore.save_world_save` (`persistence.py:600`, txn at line 605)

- [ ] **Step 3.5.1: Wrap the existing `with self._conn:`**

Current:

```python
        with self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO world_save (id, payload_json, saved_at)
                   VALUES (1, ?, ?)""",
                (payload_json, now.isoformat()),
            )
```

Replace with:

```python
        with SAVE_WRITE_LOCK:
            with self._conn:
                self._conn.execute(
                    """INSERT OR REPLACE INTO world_save (id, payload_json, saved_at)
                       VALUES (1, ?, ?)""",
                    (payload_json, now.isoformat()),
                )
```

### Step 3.6 — Site #6: `SqliteStore.append_narrative` (`persistence.py:612`)

- [ ] **Step 3.6.1: Wrap execute + commit (no existing transaction wrapper)**

Current (line 612-622):

```python
    def append_narrative(self, entry: NarrativeEntry) -> None:
        """Append a narrative entry to the log."""
        import json

        tags_json = json.dumps(entry.tags)
        self._conn.execute(
            """INSERT INTO narrative_log (round_number, author, content, tags)
               VALUES (?, ?, ?, ?)""",
            (entry.round, entry.author, entry.content, tags_json),
        )
        self._conn.commit()
```

Replace with:

```python
    def append_narrative(self, entry: NarrativeEntry) -> None:
        """Append a narrative entry to the log."""
        import json

        tags_json = json.dumps(entry.tags)
        with SAVE_WRITE_LOCK:
            self._conn.execute(
                """INSERT INTO narrative_log (round_number, author, content, tags)
                   VALUES (?, ?, ?, ?)""",
                (entry.round, entry.author, entry.content, tags_json),
            )
            self._conn.commit()
```

### Step 3.7 — Site #7: `SqliteStore.upsert_location_promotion` (`persistence.py:708`, txn at line 716)

- [ ] **Step 3.7.1: Wrap the existing `with self._conn:`**

Current:

```python
        with self._conn:
            self._conn.execute(
                """INSERT INTO location_promotions ( ... )""",
                ( ... ),
            )
```

Replace the outer `with self._conn:` with:

```python
        with SAVE_WRITE_LOCK:
            with self._conn:
                self._conn.execute(
                    """INSERT INTO location_promotions ( ... )""",
                    ( ... ),
                )
```

(Keep the full SQL exactly as-is — just indent one level deeper.)

### Step 3.8 — Site #11: `upsert_game` (`persistence.py:794`, txn at line 810)

- [ ] **Step 3.8.1: Wrap the existing `with store._conn:`**

Note: this is a **module-level function**, not a method on `SqliteStore`. It takes `store: SqliteStore` as a parameter and accesses `store._conn` directly. The lock is module-level in the same module, so just reference `SAVE_WRITE_LOCK` directly.

Current (line 810-816):

```python
    with store._conn:
        store._conn.execute(
            """INSERT INTO games (slug, mode, genre_slug, world_slug, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(slug) DO NOTHING""",
            (slug, mode.value, genre_slug, world_slug, _now_rfc3339()),
        )
```

Replace with:

```python
    with SAVE_WRITE_LOCK:
        with store._conn:
            store._conn.execute(
                """INSERT INTO games (slug, mode, genre_slug, world_slug, created_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(slug) DO NOTHING""",
                (slug, mode.value, genre_slug, world_slug, _now_rfc3339()),
            )
```

### Step 3.9 — Site #12: `set_claude_session_id` (`persistence.py:836`, txn at line 837)

- [ ] **Step 3.9.1: Wrap the existing `with store._conn:`**

Current:

```python
def set_claude_session_id(store: SqliteStore, slug: str, claude_session_id: str) -> None:
    with store._conn:
        store._conn.execute(
            "UPDATE games SET claude_session_id = ? WHERE slug = ?",
            (claude_session_id, slug),
        )
```

Replace with:

```python
def set_claude_session_id(store: SqliteStore, slug: str, claude_session_id: str) -> None:
    with SAVE_WRITE_LOCK:
        with store._conn:
            store._conn.execute(
                "UPDATE games SET claude_session_id = ? WHERE slug = ?",
                (claude_session_id, slug),
            )
```

### Step 3.10 — Sanity: existing tests still pass

- [ ] **Step 3.10.1: Run unit-suite slice**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_turn_telemetry_sink.py tests/server/test_save_write_lock.py -v`
Expected:
- `tests/telemetry/test_turn_telemetry_sink.py` — all pass (no behavior change at the telemetry-only level since watcher_hub still uses its own `_persist_lock`).
- `tests/server/test_save_write_lock.py::test_save_write_lock_is_reentrant` — PASS.
- `tests/server/test_save_write_lock.py::test_concurrent_writers_no_race` — likely still FAIL (sites #8, #9, #10 not wrapped yet; also watcher path still on its own lock, so cross-contamination remains possible).
- `tests/server/test_save_write_lock.py::test_watcher_hub_uses_save_write_lock` — still FAIL.

### Step 3.11 — Commit

- [ ] **Step 3.11.1**

```bash
git -C sidequest-server add sidequest/game/persistence.py
git -C sidequest-server commit -m "feat(persistence): wrap 9 writer sites in SAVE_WRITE_LOCK"
```

---

## Task 4: Wrap `emitters.py` scrapbook sites (sites #8, #9)

**Files:**
- Modify: `sidequest-server/sidequest/server/emitters.py` — two sites.

### Step 4.1 — Add the import

- [ ] **Step 4.1.1: Inspect the existing import block**

Run: `sed -n '1,30p' sidequest-server/sidequest/server/emitters.py`

- [ ] **Step 4.1.2: Add `SAVE_WRITE_LOCK` import**

Add this import near the other runtime (non-TYPE_CHECKING) imports at the top of the file:

```python
from sidequest.game.persistence import SAVE_WRITE_LOCK
```

Place it near `from sidequest.agents.perception_rewriter import rewrite_for_recipient` and `from sidequest.agents.pov_swap import swap_to_second_person` (the existing runtime imports), not inside the `TYPE_CHECKING` block.

### Step 4.2 — Site #8: `persist_scrapbook_entry` (`emitters.py:29`, txn at line 49)

- [ ] **Step 4.2.1: Wrap the existing `with store._conn:`**

Current (line 49-66):

```python
    with store._conn:
        store._conn.execute(
            "INSERT INTO scrapbook_entries "
            "(turn_id, scene_title, scene_type, location, image_url, "
            " narrative_excerpt, world_facts, npcs_present, render_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payload.turn_id,
                ...
            ),
        )
```

Replace the outer `with store._conn:` with:

```python
    with SAVE_WRITE_LOCK:
        with store._conn:
            store._conn.execute(
                "INSERT INTO scrapbook_entries "
                ...
                (payload.turn_id, ...),
            )
```

(Indent the existing block one extra level. Do not change any SQL or arguments.)

### Step 4.3 — Site #9: `update_scrapbook_image_url` (`emitters.py:69`, txn at line 100)

- [ ] **Step 4.3.1: Wrap the existing `with store._conn:` — note the outer `try/except`**

Current (line 99-117):

```python
    try:
        with store._conn:
            cur = store._conn.execute(
                "UPDATE scrapbook_entries SET image_url = ? "
                ...
            )
            return cur.rowcount > 0
    except Exception as exc:  # noqa: BLE001 — render path must not crash on a backfill miss
        logger.warning( ... )
        return False
```

Replace with:

```python
    try:
        with SAVE_WRITE_LOCK:
            with store._conn:
                cur = store._conn.execute(
                    "UPDATE scrapbook_entries SET image_url = ? "
                    ...
                )
                return cur.rowcount > 0
    except Exception as exc:  # noqa: BLE001 — render path must not crash on a backfill miss
        logger.warning( ... )
        return False
```

The `try/except` stays where it is (outside the lock) so that a writer failure still releases the lock cleanly via `with`'s normal exit — and any exception's logging path doesn't itself need the lock.

### Step 4.4 — Commit

- [ ] **Step 4.4.1**

```bash
git -C sidequest-server add sidequest/server/emitters.py
git -C sidequest-server commit -m "feat(emitters): wrap scrapbook write sites in SAVE_WRITE_LOCK"
```

---

## Task 5: Wrap `emitters.py` C2 event-append (site #10) — the reentry case

**Files:**
- Modify: `sidequest-server/sidequest/server/emitters.py` — one site, large block.

This is the load-bearing case. The C2 block (`with conn:` at `emitters.py:276`) contains:
- `event_log.append_in_transaction(...)` — INSERT into `events`
- `emit_mechanical_census(room, snapshot)` — fires watcher events that re-enter `_persist_turn_telemetry`, which will re-acquire `SAVE_WRITE_LOCK` via the rename in Task 6
- Per-recipient `_cache_decision(...)` calls — INSERT into `projection_cache`

`SAVE_WRITE_LOCK` must wrap the entire `with conn:` block. The RLock allows the inner `publish_event` → `_persist_turn_telemetry` chain to re-acquire from the same thread without deadlocking.

### Step 5.1 — Wrap the C2 `with conn:` in `emit_event`

- [ ] **Step 5.1.1: Inspect the full C2 block**

Run: `sed -n '267,402p' sidequest-server/sidequest/server/emitters.py`
Expected: the block starts at line 267 with the comment `# C2: event append + all cache writes share a single transaction.` and the `with conn:` opens at line 276 and closes at line 401 (the line just before `# Build emitter's message.`).

- [ ] **Step 5.1.2: Wrap the `with conn:` block in `with SAVE_WRITE_LOCK:`**

Find this line (`emitters.py:274-276`):

```python
        store = event_log.store
        conn = store._conn
        fanout: list[tuple[str, FilterDecision, dict]] = []
        with conn:
```

Replace with:

```python
        store = event_log.store
        conn = store._conn
        fanout: list[tuple[str, FilterDecision, dict]] = []
        with SAVE_WRITE_LOCK:
            with conn:
```

Then indent the **entire body of the `with conn:` block** (lines 277-401 in the un-wrapped file — the `row = event_log.append_in_transaction(...)` line through the last `if project_emitter and emitter_player_id is not None:` block) one additional level (4 spaces).

> **Important:** Indent only the body of `with conn:`. The `# Build emitter's message.` comment and everything below it (the socket fan-out at lines 467+) must **stay outside** the lock, because they perform WebSocket queue puts that do not touch the DB and should never block other writers. The original C2 design (spec §6) explicitly wants the fan-out outside the transaction for the same reason; the lock follows the same boundary.

After the edit, the indentation looks like:

```python
        store = event_log.store
        conn = store._conn
        fanout: list[tuple[str, FilterDecision, dict]] = []
        with SAVE_WRITE_LOCK:
            with conn:
                row = event_log.append_in_transaction(kind=kind, payload_json=payload_json, conn=conn)
                seq = row.seq

                if kind == "NARRATION" and event_log is not None:
                    # Phase 2: photograph every seated PC's mechanical state ...
                    from sidequest.game.mechanical_census import (
                        emit_mechanical_census,
                    )

                    emit_mechanical_census(
                        room,
                        handler._session_data.snapshot if handler._session_data else None,
                    )

                if room is not None and projection_filter is not None:
                    ...
                    # (all existing logic indented one extra level)

        # Build emitter's message.  ← stays at the original indent (outside the lock)
        emitter_payload: object
        ...
```

- [ ] **Step 5.1.3: Verify indentation with a syntax check**

Run: `cd sidequest-server && uv run python -c "import ast; ast.parse(open('sidequest/server/emitters.py').read())"`
Expected: no output (clean parse). If `IndentationError` or `SyntaxError` is raised, re-do the indent — the most common slip is mixing tabs with the existing space indentation, or forgetting to indent one of the nested `if` / `for` blocks inside the C2 region.

### Step 5.2 — Verify the test still fails until watcher_hub is renamed

- [ ] **Step 5.2.1: Run the regression test**

Run: `cd sidequest-server && uv run pytest tests/server/test_save_write_lock.py -v`
Expected:
- `test_save_write_lock_is_reentrant` — PASS.
- `test_watcher_hub_uses_save_write_lock` — still **FAIL** (rename not done).
- `test_concurrent_writers_no_race` — likely still FAIL, because group D (bare `publish_event`) drives `_persist_turn_telemetry` which still acquires the old `_persist_lock`, decoupled from `SAVE_WRITE_LOCK` — so its writes can still race against any persistence-wrapped writer holding `SAVE_WRITE_LOCK`. **This is the next task's job.**

### Step 5.3 — Commit

- [ ] **Step 5.3.1**

```bash
git -C sidequest-server add sidequest/server/emitters.py
git -C sidequest-server commit -m "feat(emitters): wrap C2 event-append in SAVE_WRITE_LOCK (RLock reentry)"
```

---

## Task 6: Migrate `watcher_hub.py` to `SAVE_WRITE_LOCK` (sites #13, #14)

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/watcher_hub.py`

### Step 6.1 — Delete `_persist_lock` definition; import the shared lock

- [ ] **Step 6.1.1: Update imports**

The file currently imports `threading` and defines `_persist_lock = threading.Lock()` at module scope. Inspect the top-of-file imports:

Run: `sed -n '1,40p' sidequest-server/sidequest/telemetry/watcher_hub.py`

Add the import (place near other `sidequest.*` imports — the file already imports from `sidequest`, look for an existing block):

```python
from sidequest.game.persistence import SAVE_WRITE_LOCK
```

If no existing `sidequest.*` runtime import exists at module scope (some are inside functions to avoid cycles), add it at module scope at the bottom of the import group. The cycle direction is fine: `persistence` does not import `watcher_hub` at module scope (it calls `_watcher_publish` via a lazy local import — confirm by `grep -n "watcher_hub\|telemetry" sidequest/game/persistence.py | head` — if any non-lazy import shows up, hoist the new import inside `_maybe_persist_encounter_row` and `_persist_turn_telemetry` instead).

- [ ] **Step 6.1.2: Verify import direction is acyclic**

Run: `cd sidequest-server && grep -n "from sidequest.telemetry\|import sidequest.telemetry" sidequest/game/persistence.py`
Expected: zero hits at module scope (any matches should be inside function bodies — lazy imports — which do not participate in import-time cycles).

If a module-scope import does exist, fall back to a function-local import of `SAVE_WRITE_LOCK` inside each of the two callers in `watcher_hub.py` instead of the module-scope variant.

### Step 6.2 — Remove the old lock definition + comment block

- [ ] **Step 6.2.1: Delete the `_persist_lock` definition (`watcher_hub.py:272-282`)**

Current:

```python
# Serializes the persistence helpers below across publisher threads. The
# bound store's sqlite3 connection is opened with
# ``check_same_thread=False`` so that ``publish_event`` is safe to call
# from narrator workers / renderer / daemon threads; this lock is what
# makes that flag safe. Without it, two threads can interleave inside a
# single ``conn.execute`` / ``with conn:`` and race to BEGIN a write
# transaction — which manifested as the 2026-05-18 MP playtest
# ``sqlite3.OperationalError: database is locked`` warnings on every
# census / trope_census event. Held only across the sqlite call, never
# while constructing payloads, so contention is bounded.
_persist_lock = threading.Lock()
```

Replace this entire block (the comment and the assignment) with:

```python
# Per-write save-DB serialization is now provided by the process-wide
# ``SAVE_WRITE_LOCK`` (RLock) from ``sidequest.game.persistence``. See
# that module's doc block for the acquire-order rule and the consumer
# list. Imported at module top so the two persistence helpers below
# acquire the same lock as every other writer (persistence.py,
# server/emitters.py).
```

(If you used the function-local import fallback from Step 6.1.2, the comment can simply say `Imported lazily inside the persistence helpers below`.)

### Step 6.3 — Site #13: `_maybe_persist_encounter_row` (`watcher_hub.py:328`)

- [ ] **Step 6.3.1: Rename `_persist_lock` → `SAVE_WRITE_LOCK`**

Current (line 327-333):

```python
    try:
        with _persist_lock:
            _event_store._conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (kind, payload),
            )
            _event_store._conn.commit()
```

Replace with:

```python
    try:
        with SAVE_WRITE_LOCK:
            _event_store._conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (kind, payload),
            )
            _event_store._conn.commit()
```

### Step 6.4 — Site #14: `_persist_turn_telemetry` (`watcher_hub.py:395`)

- [ ] **Step 6.4.1: Rename `_persist_lock` → `SAVE_WRITE_LOCK`**

Current (line 394-403):

```python
        with _persist_lock:
            if conn.in_transaction:
                ev_seq = conn.execute("SELECT MAX(seq) FROM events").fetchone()[0]
                conn.execute(
                    insert, (ev_seq, rnd, ts, component, event_type, payload_json)
                )  # NO commit: rides the open turn (C2) transaction
            else:
                with conn:
                    conn.execute(insert, (None, rnd, ts, component, event_type, payload_json))
```

Replace with:

```python
        with SAVE_WRITE_LOCK:
            if conn.in_transaction:
                ev_seq = conn.execute("SELECT MAX(seq) FROM events").fetchone()[0]
                conn.execute(
                    insert, (ev_seq, rnd, ts, component, event_type, payload_json)
                )  # NO commit: rides the open turn (C2) transaction
            else:
                with conn:
                    conn.execute(insert, (None, rnd, ts, component, event_type, payload_json))
```

### Step 6.5 — Sanity check: confirm `_persist_lock` is gone

- [ ] **Step 6.5.1: Grep for any residual references**

Run: `cd sidequest-server && grep -rn "_persist_lock" sidequest/ tests/`
Expected: zero matches.

If a match shows up, remove or update it (likely a stale comment in `watcher_hub.py`).

### Step 6.6 — Commit

- [ ] **Step 6.6.1**

```bash
git -C sidequest-server add sidequest/telemetry/watcher_hub.py
git -C sidequest-server commit -m "refactor(watcher_hub): use shared SAVE_WRITE_LOCK; drop _persist_lock"
```

---

## Task 7: Verify the regression test passes GREEN

### Step 7.1 — Run the new test file

- [ ] **Step 7.1.1**

Run: `cd sidequest-server && uv run pytest tests/server/test_save_write_lock.py -v`
Expected: **all three tests PASS**:
- `test_concurrent_writers_no_race` — no OperationalErrors, no swallowed warnings, no orphan telemetry rows, at least one in-transaction telemetry row.
- `test_save_write_lock_is_reentrant` — PASS.
- `test_watcher_hub_uses_save_write_lock` — PASS.

If `test_concurrent_writers_no_race` is flaky (passes most runs but occasionally fails), the wrapping is incomplete. Re-grep:

```bash
cd sidequest-server && grep -rn "with self._conn:\|with store._conn:\|with conn:" sidequest/ | grep -v "SAVE_WRITE_LOCK\|# " | head -30
```

Every match should be inside or immediately adjacent to a `with SAVE_WRITE_LOCK:` block. Any naked transaction wrapper without a guarding lock is a missed site — fix it before continuing.

### Step 7.2 — Run a broader slice of related tests

- [ ] **Step 7.2.1: Persistence + telemetry + emitter neighborhoods**

Run: `cd sidequest-server && uv run pytest tests/telemetry/ tests/server/test_save_write_lock.py tests/server/test_61_followup_C_close_store_wiring.py -v`
Expected: all pass. No new failures.

### Step 7.3 — Full server test suite

- [ ] **Step 7.3.1**

Run: `cd sidequest-server && uv run pytest -v`
Expected: same pass/fail count as before this branch — if any test newly fails, it's a regression from the lock wrapping. Most likely failure mode is a test that monkey-patched `with self._conn:` semantics and didn't account for the lock — fix the test, not the lock.

### Step 7.4 — Lint + format

- [ ] **Step 7.4.1**

Run: `cd sidequest-server && uv run ruff check . && uv run ruff format --check .`
Expected: clean. If `ruff` reports unused imports (e.g. lingering `import threading` in `watcher_hub.py`), remove them.

### Step 7.5 — Type check

- [ ] **Step 7.5.1**

Run: `cd sidequest-server && uv run pyright`
Expected: no new errors. If pyright complains about `SAVE_WRITE_LOCK: threading.RLock` (Python's `threading.RLock` is a factory function, not a class — `threading.RLock` annotation can be flagged), change the annotation to `threading.RLock = threading.RLock()` without the type hint, OR use the documented escape `# type: ignore[valid-type]` on that line. The simplest is to drop the annotation entirely:

```python
SAVE_WRITE_LOCK = threading.RLock()
```

This is the conventional spelling and avoids the type-checker complaint. (Adjust Task 1 retroactively if needed.)

### Step 7.6 — Commit any lint/type cleanup

- [ ] **Step 7.6.1**

```bash
git -C sidequest-server add -A
git -C sidequest-server diff --cached --quiet || git -C sidequest-server commit -m "chore: ruff/pyright cleanup for SAVE_WRITE_LOCK"
```

(The `|| commit` form skips the commit if there are no changes — keeps the history clean.)

---

## Task 8: Manual smoke under `just up`

The regression test proves correctness in isolation; the manual smoke proves the real WS pipeline doesn't deadlock on the C2 reentry case (since the regression test stubs `mechanical_census` via `_append_synthetic_event` rather than driving the full path).

### Step 8.1 — Boot the full stack

- [ ] **Step 8.1.1: Confirm nothing is already on :8765**

Run: `lsof -i :8765 || true`
Expected: empty. If a previous `just up` is still running, run `just down` first.

- [ ] **Step 8.1.2: Boot**

From the orchestrator root (`/Users/slabgorb/Projects/oq-2`):

```bash
just up
```

Tail the merged log until the server reports it's listening on `0.0.0.0:8765`. Leave it running.

### Step 8.2 — Drive one solo turn

- [ ] **Step 8.2.1: Open the client and play one narration turn**

Open `http://localhost:5173` in a browser, pick any genre that loads cleanly (e.g. `caverns_and_claudes`), start a new session, submit one action, wait for narration to land.

### Step 8.3 — Grep the server log for race signatures

- [ ] **Step 8.3.1**

Run:

```bash
grep -E "database is locked|turn_telemetry\.sink_failed|deadlock" /tmp/sidequest-server.log
```

Expected: **zero matches** for any of those strings during the post-`just up` session window. If matches show up, the fix is incomplete — capture the surrounding 20 lines (`grep -B5 -A15 ...`) and re-open Task 7's wrapping audit.

### Step 8.4 — Tear down

- [ ] **Step 8.4.1**

```bash
just down
```

### Step 8.5 — No commit

This task is verification-only; no code changes to commit.

---

## Task 9: Subrepo branch + PR

The `sidequest-server` subrepo follows GitHub-flow against `develop` (see [feedback_gitflow_content](../../../memory/feedback_gitflow_content.md)). Commits from Tasks 1–7 need a branch + squash PR.

### Step 9.1 — Confirm branch state

- [ ] **Step 9.1.1**

Run: `git -C sidequest-server status -sb && git -C sidequest-server log --oneline -10`
Expected: on a feature branch like `feat/save-write-lock`, ahead of `develop` by 5–7 commits. If the work was done on `develop` directly, branch retroactively:

```bash
git -C sidequest-server switch -c feat/save-write-lock
git -C sidequest-server push -u origin feat/save-write-lock
```

### Step 9.2 — Push and open PR

- [ ] **Step 9.2.1**

```bash
git -C sidequest-server push -u origin HEAD
env -u GITHUB_TOKEN gh -R slabgorb/sidequest-server pr create \
  --base develop \
  --title "fix(persistence): serialize all save-DB writes via SAVE_WRITE_LOCK" \
  --body "$(cat <<'EOF'
## Summary

- Adds module-level ``SAVE_WRITE_LOCK = threading.RLock()`` in ``sidequest/game/persistence.py`` per [spec](https://github.com/slabgorb/orc-quest/blob/main/docs/superpowers/specs/2026-05-24-sqlite-write-race-fix-design.md).
- Wraps every save-DB write site (14 sites across persistence.py / emitters.py / watcher_hub.py) in the lock.
- Removes ``watcher_hub._persist_lock`` and replaces both of its acquisitions with the shared lock.
- Adds ``tests/server/test_save_write_lock.py`` — concurrent N=8 thread regression + reentrancy unit + rename smoke.

Fixes the Bomb #3 race from the [2026-05-24 Sunday playgroup post-mortem](https://github.com/slabgorb/orc-quest/blob/main/docs/playtest-reports/2026-05-24-sunday-playgroup-post-mortem.md).

## Test plan

- [x] ``uv run pytest tests/server/test_save_write_lock.py -v`` — 3/3 pass
- [x] ``uv run pytest -v`` — full server suite, no new failures
- [x] ``uv run ruff check . && uv run pyright`` — clean
- [x] Manual smoke: ``just up`` + 1 solo turn; ``grep "database is locked\|sink_failed" /tmp/sidequest-server.log`` returns zero matches
EOF
)"
```

### Step 9.3 — Merge once green

- [ ] **Step 9.3.1**

After CI green:

```bash
env -u GITHUB_TOKEN gh -R slabgorb/sidequest-server pr merge --squash --auto
```

---

## Task 10: Orchestrator-side PR (sprint/ADR notes)

If this work is tracked in a sprint story (`docs/playtest-reports/2026-05-24-sunday-playgroup-post-mortem.md` Bomb #3, plus the related design doc commit `4bd35d0`), update the orchestrator sprint YAML / ADR drift status accordingly.

### Step 10.1 — Decide whether a sprint story exists

- [ ] **Step 10.1.1**

Run: `pf sprint status` and `grep -lir "write-race\|SAVE_WRITE_LOCK\|2026-05-24-sqlite" sprint/`
Expected: either a story id (e.g. `59-X`) referencing this work, or nothing.

If a story exists, append the implementation status:

```bash
pf sprint story finish <story-id>
```

If no story exists and the user wants one, run `pf sprint backlog story create ...`. **Otherwise skip this task entirely** — per the [SideQuest-is-personal feedback](../../../memory/feedback_playtest_no_jira.md), missing sprint-tracking is fine; not every bug-fix needs a story.

### Step 10.2 — No additional commit unless sprint YAML changed

---

## Risks / known gotchas

1. **Pyright + `threading.RLock` annotation.** Documented in Step 7.5; switch to the unannotated form if pyright complains.
2. **`_configure_connection` not called for `open_in_memory`.** Not a blocker for the lock fix — the fixture uses `SqliteStore.open(tmp_path / "save.db")` which calls `_configure_connection`. Flagged for the implementer in case a future test author reaches for `open_in_memory()` and is surprised by missing PRAGMAs.
3. **Flake threshold.** If `test_concurrent_writers_no_race` passes consistently on `main` even before the fix, the working assumption (race is reliably triggered at 480 ops) was wrong — bump `ITERATIONS_PER_THREAD` until at least one of three pre-fix runs fails, then proceed with the fix. The 2026-05-18 and 2026-05-24 playtest evidence makes this unlikely; flagged for completeness.
4. **Future writer landing in a fourth module.** The lock's doc block lists three consumer modules. If a new writer lands somewhere else (a new `cli/` script, a new `media/` sidecar persister), the regression test won't catch it automatically — it only exercises the four thread groups it knows about. The doc block is the human-readable enforcement; the test is the existence-of-races enforcement under load.
5. **Holding the lock across `emit_mechanical_census` widens hold time.** Per spec §6, lock-hold under C2 grows to span census + projection cache writes — still sub-100ms under measured load, but if profiling later shows contention, the WebSocket fan-out (already correctly outside the lock per Task 5) is already hoisted; the next step would be making `emit_mechanical_census` itself release-and-reacquire around any slow LLM/IO call (none currently). Out of scope here.

---

## Self-review notes

**Spec coverage:**
- §3.1 lock definition — Task 1.
- §3.2 acquire order — documented in lock comment (Task 1.2.1) + enforced by the wrapping pattern in Tasks 3–6.
- §3.3 reentrancy — RLock chosen in Task 1; verified by `test_save_write_lock_is_reentrant` (Task 2.1) and end-to-end by `test_concurrent_writers_no_race`'s group C (Task 2.1).
- §3.4 every writer site — Tasks 3, 4, 5, 6 cover all 14 (with corrected names noted up front).
- §3.5 documentation discipline — Task 1.2 + Task 1.3.
- §5 regression test — Task 2 (with assertion #4 adjusted to behavioral, per the FK schema deviation noted up front).
- §6 migration notes — no schema change, smoke verifies behavior (Task 8).
- §9 implementation outline — followed in order.

**Placeholder scan:** zero TBDs, every code change has the exact `old → new` text or a structured wrapping recipe.

**Type/name consistency:** `SAVE_WRITE_LOCK` used identically across all five wrapping tasks; `threading.RLock()` defined once in Task 1; import statement is identical in `emitters.py` and `watcher_hub.py`.

**Spec corrections caught:** four function-name mismatches and one schema misstatement, documented in the pre-flight section so the implementer does not need to re-read the spec to find them.
