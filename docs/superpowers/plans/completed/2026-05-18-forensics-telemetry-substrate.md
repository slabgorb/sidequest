# Durable Telemetry Substrate for Save Forensics — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist every `_watcher_publish` payload verbatim, append-only, into the save itself — atomically with the turn that produced it — and surface it per-round in the forensics page via a pure read-time fold.

**Architecture:** A new append-only `turn_telemetry` table in `save.db`. A sink inside `publish_event` (`watcher_hub.py`) reuses the existing process-global `_event_store` binding (the same `SqliteStore._conn` the C2 turn transaction already uses — the debugged precedent is `_maybe_persist_encounter_row`). The sink branches on `sqlite3.Connection.in_transaction`: when a turn (C2) write transaction is open it joins it (no commit, atomic with `events`); otherwise it takes its own short transaction. The forensics read path opens the save strictly read-only (`_ro_connect`, `?mode=ro`), buckets telemetry rows per round by `event_seq` range (+ `round` column for NULL-`event_seq` rows), and a new pure `fold_turn_telemetry` (mirroring `fold_known_facts`) curates them at read time into a single collapsed UI lane.

**The load-bearing invariant (correctness rests on this):** in this codebase `sqlite3` connections use the default *deferred* isolation (`_configure_connection` sets `PRAGMA journal_mode=WAL` + `foreign_keys=ON`, never `isolation_level=None`). Therefore `conn.in_transaction` is `False` until the first DML on the connection and `True` only after it (until commit/rollback). In the turn path the first DML is the C2 `events` INSERT (`emitters.py` `append_in_transaction`). Hence **`conn.in_transaction == True` ⟺ this turn's `events` row already exists on this connection ⟺ `SELECT MAX(seq) FROM events` is that in-flight row**. One signal drives both the transaction mode *and* `event_seq` attribution, with zero ambiguity. Task 1 pins this invariant as a regression guard before anything is built on it.

**Tech Stack:** Python 3 / `sqlite3` (stdlib, no ORM), pytest + `caplog`, FastAPI route already in place, zero-JS static `forensics.html`.

**Owning repo / branch:** all work in `sidequest-server/`, on branch `feat/forensics-telemetry-substrate` cut from `develop`. Paths below are repo-relative to `sidequest-server/`.

**Project test-execution note:** under the Pennyfarthing TDD workflow, tests are run via the `testing-runner` subagent, **not** invoked directly (CLAUDE.md). Each step's `Run:` line gives the exact pytest selector the `testing-runner` should target and the expected result; treat it as the test contract, not a literal shell instruction.

**Scope discipline (No-Stubbing, No-Silent-Fallbacks, focused change):**
- **Out of scope, do not touch:** `_maybe_persist_encounter_row` (it has a pre-existing unconditional-`commit()` hazard gated to `field=="encounter"` ops — documented as a risk below, *not* refactored here; touching it goes exponential).
- **Out of scope (Phase 2/3):** no new watcher *instrumentation*, no macro-strip mechanical/world lanes, no backfill of existing saves.
- The sink reuses the existing `_event_store` binding. **Do not** add a session registry, **do not** thread a store through call sites, **do not** add a silent global fallback.

**Pre-flight (one-time, before Task 1):**

```bash
cd sidequest-server
git fetch origin
git switch develop && git pull --ff-only
git switch -c feat/forensics-telemetry-substrate
```

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `sidequest/game/persistence.py` | `SCHEMA_SQL` — add `turn_telemetry` table + 2 indexes | Modify (~line 179, end of `SCHEMA_SQL`) |
| `sidequest/telemetry/watcher_hub.py` | `_persist_turn_telemetry` sink + call from `publish_event` | Modify (new fn near `_maybe_persist_encounter_row` ~`:300`; call added in `publish_event` body ~`:436`) |
| `sidequest/game/forensic_fold.py` | New pure `fold_turn_telemetry(rows)` + `TelemetryRow`/`TelemetryFold` dataclasses | Modify (append to existing fold module) |
| `sidequest/game/forensic_query.py` | `build_turn_bundle` gains `telemetry`; missing-table→zero-rows guard; both empty-return dicts gain `telemetry` | Modify (`:187`, `:214-223`, full-return ~`:294-302`) |
| `sidequest/server/rest.py` | `debug_save_turn` `empty` literal gains `"telemetry": []` | Modify (`:462-470`) |
| `sidequest/server/static/forensics.html` | One collapsed `<details>` telemetry lane; macro-header sink-health count | Modify (lane before `</section>` ~`:320`; `.lbl` ~`:112-116`) |
| `tests/game/test_turn_telemetry_contract.py` | Task 1 characterization (the load-bearing invariant) | Create |
| `tests/game/test_persistence_turn_telemetry.py` | Task 2 schema test | Create |
| `tests/telemetry/test_turn_telemetry_sink.py` | Task 3 + 4 sink behavior + failure isolation | Create |
| `tests/server/test_turn_telemetry_wiring.py` | Task 5 mandatory wiring test | Create |
| `tests/game/test_forensic_fold.py` | Task 6 `fold_turn_telemetry` pure tests | Modify (append) |
| `tests/game/test_forensic_query.py` | Task 7 read-path + byte-identity | Modify (append) |
| `tests/server/test_forensics_routes.py` | Task 7 never-500 literal sync; Task 8 lane wiring | Modify |

---

## Task 1: Pin the load-bearing wiring contract (characterization, test-only)

**Why first:** the spec names this the plan's first task. The investigation already resolved it; this task *codifies* the resolution as an executable regression guard so every later task can rely on it. No production code changes — pure characterization of an existing seam.

**Files:**
- Test: `tests/game/test_turn_telemetry_contract.py` (create)

- [ ] **Step 1: Write the failing characterization test**

```python
# tests/game/test_turn_telemetry_contract.py
"""Characterization: pins the invariant the turn_telemetry sink rests on.

If any of these fail, the sink's transaction-mode + event_seq derivation
is unsound and the rest of the plan must not proceed.
"""
import sqlite3

from sidequest.game.persistence import SqliteStore
from sidequest.telemetry import watcher_hub
from sidequest.telemetry.watcher_hub import bind_event_store


def _store(tmp_path) -> SqliteStore:
    return SqliteStore.open(str(tmp_path / "save.db"))


def test_bind_event_store_binds_the_same_conn_object(tmp_path):
    """The process-global the sink reads (_event_store._conn) is the SAME
    connection object the C2 turn transaction writes events/projection_cache
    through. (connect.py binds this store, then wraps it as EventLog(store).)"""
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        assert watcher_hub._event_store is store
        assert watcher_hub._event_store._conn is store._conn
    finally:
        bind_event_store(None)
        store.close()


def test_deferred_isolation_in_transaction_invariant(tmp_path):
    """Default deferred isolation: SELECT does NOT open a write txn; the
    first DML flips in_transaction True; it stays True until commit; a
    `with conn:` block is True only after its first DML and False after
    the block. This is the exact signal the sink branches on."""
    store = _store(tmp_path)
    try:
        conn = store._conn
        assert conn.in_transaction is False  # quiescent
        conn.execute("SELECT 1").fetchone()
        assert conn.in_transaction is False  # SELECT does not begin a write txn
        with conn:
            conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) "
                "VALUES ('NARRATION', '{}', 't')"
            )
            assert conn.in_transaction is True  # first DML flipped it
            seq = conn.execute("SELECT MAX(seq) FROM events").fetchone()[0]
            assert seq == 1  # the in-flight row is visible within the txn
        assert conn.in_transaction is False  # `with conn:` committed + closed txn
    finally:
        store.close()
```

- [ ] **Step 2: Run to verify it fails (or passes-as-characterization)**

Run: `uv run pytest tests/game/test_turn_telemetry_contract.py -v`
Expected: **PASS** is acceptable here and is the goal — this is a *characterization* test of existing behavior. If `test_deferred_isolation_in_transaction_invariant` FAILS, STOP: the load-bearing invariant does not hold and the whole approach is unsound — escalate, do not proceed. If `SqliteStore` has no `.close()`, replace `store.close()` with `store._conn.close()` (verify the actual teardown method on `SqliteStore`).

- [ ] **Step 3: Commit**

```bash
git add tests/game/test_turn_telemetry_contract.py
git commit -m "test(telemetry): pin turn_telemetry load-bearing wiring invariant"
```

---

## Task 2: Schema — the `turn_telemetry` append-only table

**Files:**
- Modify: `sidequest/game/persistence.py` (`SCHEMA_SQL`, after the `world_save` block, end of the constant ~`:179`)
- Test: `tests/game/test_persistence_turn_telemetry.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_persistence_turn_telemetry.py
from sidequest.game.persistence import SqliteStore


def test_turn_telemetry_table_and_indexes_exist_on_fresh_save(tmp_path):
    store = SqliteStore.open(str(tmp_path / "save.db"))
    try:
        conn = store._conn
        cols = {
            r[1]: r[2]
            for r in conn.execute("PRAGMA table_info(turn_telemetry)").fetchall()
        }
        assert cols == {
            "seq": "INTEGER",
            "event_seq": "INTEGER",
            "round": "INTEGER",
            "ts": "TEXT",
            "component": "TEXT",
            "event_type": "TEXT",
            "payload_json": "TEXT",
        }
        idx = {
            r[1]
            for r in conn.execute(
                "SELECT * FROM sqlite_master WHERE type='index' "
                "AND tbl_name='turn_telemetry'"
            ).fetchall()
        }
        assert "idx_turn_telemetry_round" in idx
        assert "idx_turn_telemetry_event_seq" in idx
        # seq is AUTOINCREMENT PK: not supplied on INSERT, read via lastrowid
        cur = conn.execute(
            "INSERT INTO turn_telemetry "
            "(event_seq, round, ts, component, event_type, payload_json) "
            "VALUES (NULL, NULL, 't', 'c', 'e', '{}')"
        )
        assert cur.lastrowid == 1
    finally:
        store.close()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/game/test_persistence_turn_telemetry.py -v`
Expected: FAIL — `sqlite3.OperationalError: no such table: turn_telemetry`.

- [ ] **Step 3: Add the table to `SCHEMA_SQL`**

In `sidequest/game/persistence.py`, inside the `SCHEMA_SQL` string constant, append this block immediately after the `world_save` `CREATE TABLE` (the last table in the script, ~line 179). Match the existing 4-space-in-string indentation and `seq INTEGER PRIMARY KEY AUTOINCREMENT` house style (identical to `events.seq` at `:164`):

```sql
CREATE TABLE IF NOT EXISTS turn_telemetry (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_seq INTEGER,
    round INTEGER,
    ts TEXT NOT NULL,
    component TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_turn_telemetry_round ON turn_telemetry (round);
CREATE INDEX IF NOT EXISTS idx_turn_telemetry_event_seq ON turn_telemetry (event_seq);
```

No `_apply_migrations()` entry is needed: this is a brand-new table, so `executescript(SCHEMA_SQL)`'s `CREATE TABLE IF NOT EXISTS` creates it on the next open of any save (fresh or existing) — `_apply_migrations` is only for adding columns to *pre-existing* tables. Do **not** add `"turn_telemetry"` to `_PER_SLOT_TABLES` (`:39-46`): the table is append-only and never cleared (durable-retention is law).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/game/test_persistence_turn_telemetry.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/persistence.py tests/game/test_persistence_turn_telemetry.py
git commit -m "feat(persistence): add append-only turn_telemetry table + indexes"
```

---

## Task 3: The write sink — `_persist_turn_telemetry` in `watcher_hub.py`

**Files:**
- Modify: `sidequest/telemetry/watcher_hub.py` (new function adjacent to `_maybe_persist_encounter_row` ~`:300`; one call added inside `publish_event` ~`:436`)
- Test: `tests/telemetry/test_turn_telemetry_sink.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/telemetry/test_turn_telemetry_sink.py
import json

from sidequest.game.persistence import SqliteStore
from sidequest.telemetry.watcher_hub import bind_event_store, publish_event


def _store(tmp_path) -> SqliteStore:
    return SqliteStore.open(str(tmp_path / "save.db"))


def test_publish_outside_txn_writes_row_with_null_event_seq(tmp_path):
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        publish_event(
            "state_transition",
            {"field": "intent", "label": "explore", "round": 3},
            component="intent",
        )
        rows = store._conn.execute(
            "SELECT event_seq, round, component, event_type, payload_json "
            "FROM turn_telemetry"
        ).fetchall()
        assert len(rows) == 1
        event_seq, rnd, component, event_type, payload = rows[0]
        assert event_seq is None  # fired outside any turn (C2) transaction
        assert rnd == 3  # best-effort from fields["round"]
        assert component == "intent"
        assert event_type == "state_transition"
        assert json.loads(payload) == {
            "field": "intent",
            "label": "explore",
            "round": 3,
        }
    finally:
        bind_event_store(None)
        store.close()


def test_publish_inside_open_txn_joins_it_and_attributes_event_seq(tmp_path):
    """When a C2 turn transaction is open, the sink must NOT commit and must
    attribute event_seq = the in-flight events row. Atomicity: rolling back
    the turn rolls back the telemetry too."""
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        conn = store._conn
        # simulate a C2 turn transaction (events INSERT then more work)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO events (kind, payload_json, created_at) "
                    "VALUES ('NARRATION', '{}', 't')"
                )
                assert conn.in_transaction is True
                publish_event(
                    "state_transition",
                    {"field": "projection", "decision": "include"},
                    component="projection",
                )
                # telemetry visible within the same txn, not yet committed
                inflight = conn.execute(
                    "SELECT event_seq FROM turn_telemetry"
                ).fetchall()
                assert inflight == [(1,)]  # = MAX(seq) of the in-flight event
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass
        # turn rolled back -> telemetry rolled back atomically with it
        assert conn.execute("SELECT COUNT(*) FROM turn_telemetry").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    finally:
        bind_event_store(None)
        store.close()


def test_no_store_bound_is_noop_not_error(tmp_path):
    bind_event_store(None)  # legacy/in-memory session: no durable save
    publish_event("x", {"a": 1}, component="c")  # must not raise


def test_round_absent_or_non_int_is_stored_null(tmp_path):
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        publish_event("e", {"no_round_here": True}, component="c")
        publish_event("e", {"round": "not-an-int"}, component="c")
        rounds = [
            r[0]
            for r in store._conn.execute(
                "SELECT round FROM turn_telemetry ORDER BY seq"
            ).fetchall()
        ]
        assert rounds == [None, None]
    finally:
        bind_event_store(None)
        store.close()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/telemetry/test_turn_telemetry_sink.py -v`
Expected: FAIL — rows are not written (`assert len(rows) == 1` fails; `publish_event` has no telemetry sink yet).

- [ ] **Step 3: Add the sink function**

In `sidequest/telemetry/watcher_hub.py`, first verify the module has `import json`, `import sqlite3`, `from datetime import UTC, datetime`, and a module `logger` (the existing `_maybe_persist_encounter_row`/`publish_event` already use `json.dumps`, `sqlite3`, and `datetime.now(UTC).isoformat()`). If there is **no** module-level `logger`, add it near the other imports, matching `forensic_fold.py:8` style:

```python
import logging

logger = logging.getLogger(__name__)
```

Add this function immediately after `_maybe_persist_encounter_row` (~`:336`):

```python
def _persist_turn_telemetry(event: dict) -> None:
    """Append one raw turn_telemetry row for every watcher publish.

    Reuses the same process-global ``_event_store`` binding that
    ``_maybe_persist_encounter_row`` uses (bound at connect time; its
    ``_conn`` is the same connection the C2 turn transaction writes
    events/projection_cache through).

    Transaction discipline (the load-bearing invariant): under this
    codebase's default *deferred* isolation, ``conn.in_transaction`` is
    True iff a write transaction is already open on the connection. In the
    turn path the first DML is the C2 ``events`` INSERT, so
    ``in_transaction`` True ⟺ this turn's event row already exists ⟺
    ``MAX(seq) FROM events`` is that in-flight row. So:

      * in_transaction  -> join the open turn txn (NO commit); attribute
        ``event_seq = MAX(seq)``; the row commits/rolls back atomically
        with ``events``/``projection_cache``.
      * not in_transaction -> own short ``with conn:`` txn; ``event_seq``
        is NULL (fired outside an event frame — the spec's NULL case).

    Fully wrapped: ANY failure logs loudly (``turn_telemetry.sink_failed``)
    and returns. Never raises, never stalls the turn, never writes to a
    different DB (No-Silent-Fallbacks).
    """
    store = _event_store
    if store is None:
        return  # legacy/in-memory session: no durable save bound (not an error)
    try:
        conn = store._conn
        component = event.get("component", "sidequest-server")
        event_type = event.get("event_type", "")
        fields = event.get("fields", {})
        payload_json = json.dumps(fields)
        rnd = fields.get("round") if isinstance(fields, dict) else None
        if not isinstance(rnd, int):
            rnd = None
        ts = datetime.now(UTC).isoformat()
        insert = (
            "INSERT INTO turn_telemetry "
            "(event_seq, round, ts, component, event_type, payload_json) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        if conn.in_transaction:
            ev_seq = conn.execute("SELECT MAX(seq) FROM events").fetchone()[0]
            conn.execute(
                insert, (ev_seq, rnd, ts, component, event_type, payload_json)
            )  # NO commit: rides the open turn (C2) transaction
        else:
            with conn:
                conn.execute(
                    insert, (None, rnd, ts, component, event_type, payload_json)
                )
    except Exception:  # noqa: BLE001 — telemetry must never crash a turn
        logger.warning(
            "turn_telemetry.sink_failed component=%s event_type=%s",
            event.get("component"),
            event.get("event_type"),
            exc_info=True,
        )
        return
```

- [ ] **Step 4: Call the sink from `publish_event`**

In `publish_event` (~`:427-438`), immediately after the existing
`_maybe_persist_encounter_row({"event_type": event_type, "fields": fields})`
line, add:

```python
    _persist_turn_telemetry(
        {"event_type": event_type, "fields": fields, "component": component}
    )
```

Leave the OTEL emission path (`_emit_watcher_span` / `watcher_hub.publish`) and `_maybe_persist_encounter_row` exactly as they are — the sink is independent and one failing path must never affect the other.

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/telemetry/test_turn_telemetry_sink.py -v`
Expected: PASS (all four tests).

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/watcher_hub.py tests/telemetry/test_turn_telemetry_sink.py
git commit -m "feat(telemetry): persist every watcher publish to turn_telemetry (C2-atomic)"
```

---

## Task 4: Sink failure isolation — a forced sink error never crashes a turn

**Files:**
- Test: `tests/telemetry/test_turn_telemetry_sink.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/telemetry/test_turn_telemetry_sink.py
def test_sink_failure_logs_loudly_and_does_not_crash_the_turn(
    tmp_path, monkeypatch, caplog
):
    """A forced sink error must produce a loud turn_telemetry.sink_failed
    WARNING and return — publish_event still completes normally."""
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        # force the INSERT to explode by dropping the table out from under it
        store._conn.execute("DROP TABLE turn_telemetry")
        store._conn.commit()
        with caplog.at_level("WARNING"):
            publish_event(
                "state_transition", {"field": "x"}, component="trope"
            )  # must NOT raise
        assert "turn_telemetry.sink_failed" in caplog.text
        assert "component=trope" in caplog.text
    finally:
        bind_event_store(None)
        store.close()
```

- [ ] **Step 2: Run to verify it passes**

Run: `uv run pytest tests/telemetry/test_turn_telemetry_sink.py::test_sink_failure_logs_loudly_and_does_not_crash_the_turn -v`
Expected: **PASS** — the `except Exception` wrapper added in Task 3 already provides this behavior. This test is the explicit *contract guard* the spec mandates ("Sink failure isolation test"); it should pass without new production code. If it FAILS, the Task 3 wrapper is wrong — fix the wrapper, do not weaken the test.

- [ ] **Step 3: Commit**

```bash
git add tests/telemetry/test_turn_telemetry_sink.py
git commit -m "test(telemetry): guard sink-failure isolation (loud, never crashes a turn)"
```

---

## Task 5: Mandatory wiring test — a real production turn writes `turn_telemetry`

**Why:** CLAUDE.md "Every Test Suite Needs a Wiring Test". Unit tests above call `publish_event` directly; this proves the sink is reached from a **real turn path that goes through `connect.py`'s `bind_event_store`**, not a hand-bound store.

**Files:**
- Test: `tests/server/test_turn_telemetry_wiring.py` (create)

- [ ] **Step 1: Locate the existing minimal end-to-end turn harness**

Before writing, identify the lightest existing test that drives a real turn through the server (a scenario-harness or websocket-session test that already produces `events` rows in a save). Search:

Run: `uv run pytest --collect-only -q tests/server | grep -i -E 'turn|scenario|session' | head -40`
Pick the existing helper that boots a slug-backed session (one that exercises `connect.py` so `bind_event_store` is called) and plays at least one turn. Reuse its fixtures — **do not** build a new server harness (reuse-first).

- [ ] **Step 2: Write the failing wiring test**

```python
# tests/server/test_turn_telemetry_wiring.py
"""Mandatory wiring test: a real production turn (through connect.py's
bind_event_store, not a hand-bound store) actually writes turn_telemetry
rows. Proves the sink is reached from the live turn path, not just
importable."""
# NOTE: <HARNESS_IMPORT> / <PLAY_ONE_TURN> below must be filled from the
# helper identified in Step 1. They are the ONLY two project-specific
# bindings; everything else is fixed by this plan.
from <HARNESS_IMPORT>  # e.g. tests.server.conftest scenario fixture


def test_a_real_turn_persists_turn_telemetry_rows(<harness_fixture>, tmp_path):
    save_db = <play_one_turn_and_return_save_db_path>(<harness_fixture>)
    import sqlite3

    conn = sqlite3.connect(f"file:{save_db}?mode=ro", uri=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM turn_telemetry").fetchone()[0]
        # a real turn emits many watcher publishes (intent, beat,
        # projection, state_transition, ...). Assert the sink is wired,
        # not an exact count (count is Phase-2 instrumentation territory).
        assert total > 0, "no turn_telemetry rows: sink is not wired into the live turn"
        # at least one row must be attributed to a real event frame
        attributed = conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry WHERE event_seq IS NOT NULL"
        ).fetchone()[0]
        assert attributed > 0, "no event_seq-attributed rows: C2 join path not exercised"
    finally:
        conn.close()
```

Fill `<HARNESS_IMPORT>`, `<harness_fixture>`, and `<play_one_turn_and_return_save_db_path>` from the Step-1 helper. If the chosen helper does not expose the save `.db` path, extend it minimally (one accessor) — do not fork a new harness.

- [ ] **Step 3: Run to verify it fails for the right reason first**

Run: `uv run pytest tests/server/test_turn_telemetry_wiring.py -v`
Expected sequence: it should **PASS** once Tasks 2–3 are merged (the sink is wired). To prove the test is non-vacuous, temporarily comment out the `_persist_turn_telemetry(...)` call added in Task 3 Step 4, re-run, confirm it **FAILS** with `"no turn_telemetry rows: sink is not wired"`, then restore the call and confirm it PASSES. Document this in the commit body.

- [ ] **Step 4: Commit**

```bash
git add tests/server/test_turn_telemetry_wiring.py
git commit -m "test(telemetry): wiring test — a real turn writes turn_telemetry rows

Verified non-vacuous: removing the publish_event sink call makes it fail
with 'sink is not wired into the live turn'."
```

---

## Task 6: Read-time fold — `fold_turn_telemetry` (pure, no I/O)

**Files:**
- Modify: `sidequest/game/forensic_fold.py` (append; mirrors `fold_known_facts` at `:54-101` verbatim in shape)
- Test: `tests/game/test_forensic_fold.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/game/test_forensic_fold.py
from sidequest.game.forensic_fold import (
    TelemetryFold,
    TelemetryRow,
    fold_turn_telemetry,
)


def _trow(seq, component, event_type, payload_json, ts="t"):
    # mirrors the sqlite3.Row-ish dict the read path passes the fold
    return {
        "seq": seq,
        "component": component,
        "event_type": event_type,
        "ts": ts,
        "payload_json": payload_json,
    }


def test_telemetry_empty_yields_empty():
    result = fold_turn_telemetry([])
    assert result == TelemetryFold(
        rows=(), by_component={}, total=0, unparseable_seqs=()
    )


def test_telemetry_groups_by_component_then_event_type_and_counts():
    rows = [
        _trow(1, "intent", "state_transition", '{"label":"explore"}'),
        _trow(2, "intent", "state_transition", '{"label":"talk"}'),
        _trow(3, "projection", "decision", '{"include":true}'),
    ]
    r = fold_turn_telemetry(rows)
    assert r.total == 3
    assert r.by_component == {
        "intent": {"state_transition": 2},
        "projection": {"decision": 1},
    }
    assert [(x.seq, x.component, x.event_type) for x in r.rows] == [
        (1, "intent", "state_transition"),
        (2, "intent", "state_transition"),
        (3, "projection", "decision"),
    ]
    assert r.rows[0].fields == {"label": "explore"}


def test_telemetry_rows_sorted_by_seq_regardless_of_input_order():
    rows = [
        _trow(3, "c", "e", "{}"),
        _trow(1, "c", "e", "{}"),
        _trow(2, "c", "e", "{}"),
    ]
    r = fold_turn_telemetry(rows)
    assert [x.seq for x in r.rows] == [1, 2, 3]


def test_telemetry_unparseable_payload_is_recorded_and_logged_not_dropped(caplog):
    bad = _trow(7, "c", "e", "{not json")
    good = _trow(8, "c", "e", '{"ok":1}')
    with caplog.at_level("WARNING"):
        r = fold_turn_telemetry([bad, good])
    assert r.unparseable_seqs == (7,)
    assert [x.seq for x in r.rows] == [8]  # good row still folds
    assert r.total == 1
    assert "forensic_fold.telemetry_unparseable_payload seq=7" in caplog.text


def test_telemetry_non_dict_payload_is_recorded_and_logged(caplog):
    bad = _trow(9, "c", "e", "[1,2,3]")  # valid JSON, not a dict
    with caplog.at_level("WARNING"):
        r = fold_turn_telemetry([bad])
    assert r.unparseable_seqs == (9,)
    assert r.rows == ()
    assert "forensic_fold.telemetry_non_dict_payload seq=9" in caplog.text


def test_telemetry_fold_never_raises_on_garbage_row_shape():
    # missing keys / None payload must not crash (defensive, like fold_known_facts)
    r = fold_turn_telemetry([{"seq": 1, "payload_json": None}])
    assert r.unparseable_seqs == (1,)
    assert r.rows == ()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/game/test_forensic_fold.py -v -k telemetry`
Expected: FAIL — `ImportError: cannot import name 'fold_turn_telemetry'`.

- [ ] **Step 3: Implement the fold**

Append to `sidequest/game/forensic_fold.py` (it already has `import json`, `import logging`, `logger`, `from dataclasses import dataclass, field`). Mirror `fold_known_facts`'s exact discipline: internal sort, `try/except (json.JSONDecodeError, TypeError)` → loud `logger.warning` + append to a local `unparseable` list, non-dict guard also loud+recorded, defensive `.get()` on every access, `unparseable` returned as a tuple, never raises:

```python
@dataclass(frozen=True)
class TelemetryRow:
    """One folded turn_telemetry row, ready for the forensics lane."""

    seq: int
    component: str
    event_type: str
    ts: str
    fields: dict


@dataclass(frozen=True)
class TelemetryFold:
    """Read-time curation of a round's turn_telemetry rows.

    ``rows`` are the parseable rows in seq order; ``by_component`` is
    component -> {event_type -> count}; ``unparseable_seqs`` records the
    loud-skipped rows (same contract as ``FoldResult.unparseable_seqs``)."""

    rows: tuple[TelemetryRow, ...] = ()
    by_component: dict = field(default_factory=dict)
    total: int = 0
    unparseable_seqs: tuple[int, ...] = ()


def fold_turn_telemetry(raw_rows: list) -> TelemetryFold:
    """Fold raw turn_telemetry rows (any order) into the forensics view.

    Pure, no I/O, never raises (mirrors ``fold_known_facts``):

    - A ``payload_json`` that fails JSON parsing, or parses to a non-dict,
      is skipped *loudly* (logged + recorded in ``unparseable_seqs``),
      never silently dropped.
    - A structurally broken row (missing seq, etc.) is recorded as
      unparseable rather than crashing the page.
    - Output rows are sorted by ``seq``; ``by_component`` counts events
      grouped component -> event_type.
    """
    folded: list[TelemetryRow] = []
    unparseable: list[int] = []
    by_component: dict[str, dict[str, int]] = {}

    def _key(row) -> int:
        try:
            return int(row.get("seq"))
        except (TypeError, ValueError, AttributeError):
            return -1

    for row in sorted(raw_rows, key=_key):
        try:
            seq = int(row["seq"])
            component = str(row.get("component") or "")
            event_type = str(row.get("event_type") or "")
            ts = str(row.get("ts") or "")
            raw_payload = row.get("payload_json")
        except (KeyError, TypeError, AttributeError):
            seq_val = row.get("seq") if hasattr(row, "get") else None
            logger.warning(
                "forensic_fold.telemetry_unparseable_payload seq=%s", seq_val
            )
            if isinstance(seq_val, int):
                unparseable.append(seq_val)
            continue
        try:
            payload = json.loads(raw_payload)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "forensic_fold.telemetry_unparseable_payload seq=%s", seq
            )
            unparseable.append(seq)
            continue
        if not isinstance(payload, dict):
            logger.warning(
                "forensic_fold.telemetry_non_dict_payload seq=%s", seq
            )
            unparseable.append(seq)
            continue
        folded.append(
            TelemetryRow(
                seq=seq,
                component=component,
                event_type=event_type,
                ts=ts,
                fields=payload,
            )
        )
        by_component.setdefault(component, {})
        by_component[component][event_type] = (
            by_component[component].get(event_type, 0) + 1
        )

    return TelemetryFold(
        rows=tuple(folded),
        by_component=by_component,
        total=len(folded),
        unparseable_seqs=tuple(unparseable),
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/game/test_forensic_fold.py -v -k telemetry`
Expected: PASS (all six telemetry tests). Also re-run the whole file to confirm no regression to `fold_known_facts`: `uv run pytest tests/game/test_forensic_fold.py -v` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/forensic_fold.py tests/game/test_forensic_fold.py
git commit -m "feat(forensics): pure fold_turn_telemetry — read-time telemetry curation"
```

---

## Task 7: Read path — `build_turn_bundle` gains `telemetry`; missing-table → zero rows

**Files:**
- Modify: `sidequest/game/forensic_query.py` (`build_turn_bundle` `:187`; empty-return dict `:214-223`; full-return dict ~`:294-302`)
- Modify: `sidequest/server/rest.py` (`debug_save_turn` `empty` literal `:462-470`)
- Test: `tests/game/test_forensic_query.py` (append); `tests/server/test_forensics_routes.py` (sync literals)

**Coupled literal edit sites — ALL of these must add `telemetry` together (the spec's key-set-drift hazard):**
1. `forensic_query.py` `build_turn_bundle` empty/unknown-round return (`:214-223`) → add `"telemetry": []`
2. `forensic_query.py` `build_turn_bundle` full success return (~`:294-302`) → add `"telemetry": <folded payload>`
3. `rest.py` `debug_save_turn` `empty` literal (`:462-470`) → add `"telemetry": []`
4. `tests/server/test_forensics_routes.py` `test_turn_bundle_unknown_slug_is_empty_not_500` literal (`:98-106`) → add `"telemetry": []`
5. `tests/server/test_forensics_routes.py` `test_turn_bundle_corrupt_save_is_empty_not_500` literal (`:118-126`) → add `"telemetry": []`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/game/test_forensic_query.py
import sqlite3

from sidequest.game.forensic_query import _ro_connect, build_turn_bundle


def test_bundle_telemetry_buckets_by_event_seq_range_and_round(tmp_path):
    """Telemetry rows for a round = event_seq within the round's seq
    range, PLUS rows whose `round` column matches (covers NULL-event_seq).
    Reuse _seed_rounds for events/narrative, then add turn_telemetry."""
    db = tmp_path / "save.db"
    # _seed_rounds is the existing helper in this test module; it writes
    # production-shaped narrative_log + events for N rounds.
    _seed_rounds(db, rounds=2)  # round 1 -> events seq 1..k1, round 2 -> k1+1..k2
    con = sqlite3.connect(str(db))
    con.executescript(
        "CREATE TABLE IF NOT EXISTS turn_telemetry ("
        " seq INTEGER PRIMARY KEY AUTOINCREMENT, event_seq INTEGER,"
        " round INTEGER, ts TEXT NOT NULL, component TEXT NOT NULL,"
        " event_type TEXT NOT NULL, payload_json TEXT NOT NULL);"
    )
    # determine round-1 seq window from the events the helper wrote
    r1 = con.execute("SELECT MIN(seq), MAX(seq) FROM events").fetchone()
    lo = r1[0]
    con.executemany(
        "INSERT INTO turn_telemetry "
        "(event_seq, round, ts, component, event_type, payload_json) "
        "VALUES (?,?,?,?,?,?)",
        [
            (lo, None, "t", "intent", "state_transition", '{"label":"a"}'),  # in r1 by seq
            (None, 1, "t", "beat", "selected", '{"beat":"b"}'),              # in r1 by round col
            (None, 2, "t", "intent", "state_transition", '{"label":"c"}'),   # r2, excluded
        ],
    )
    con.commit()
    con.close()

    conn = _ro_connect(db)
    try:
        bundle = build_turn_bundle(conn, 1)
        tel = bundle["telemetry"]
        assert tel["total"] == 2  # the seq-window row + the round-col row
        assert tel["by_component"] == {
            "intent": {"state_transition": 1},
            "beat": {"selected": 1},
        }
    finally:
        conn.close()


def test_bundle_missing_turn_telemetry_table_is_zero_rows_not_error(tmp_path):
    """Old saves predate the table. forensics is read-only and must NOT
    create it; a missing table behaves exactly like zero rows."""
    db = tmp_path / "save.db"
    _seed_rounds(db, rounds=1)  # NO turn_telemetry table created
    conn = _ro_connect(db)
    try:
        bundle = build_turn_bundle(conn, 1)
        assert bundle["telemetry"] == {
            "rows": [],
            "by_component": {},
            "total": 0,
            "unparseable_seqs": [],
        }
    finally:
        conn.close()


def test_bundle_unknown_round_includes_empty_telemetry_key(tmp_path):
    db = tmp_path / "save.db"
    _seed_rounds(db, rounds=1)
    conn = _ro_connect(db)
    try:
        bundle = build_turn_bundle(conn, 999)  # unknown round -> empty bundle
        assert bundle["telemetry"] == {
            "rows": [],
            "by_component": {},
            "total": 0,
            "unparseable_seqs": [],
        }
    finally:
        conn.close()


def test_telemetry_read_does_not_mutate_the_save(tmp_path):
    """Read-only byte-identity: a forensics read over a save WITH
    turn_telemetry leaves save.db byte-identical (mirrors
    test_list_saves_does_not_mutate_the_save)."""
    db = tmp_path / "save.db"
    _seed_rounds(db, rounds=1)
    con = sqlite3.connect(str(db))
    con.executescript(
        "PRAGMA journal_mode=DELETE;"
        "CREATE TABLE turn_telemetry (seq INTEGER PRIMARY KEY AUTOINCREMENT,"
        " event_seq INTEGER, round INTEGER, ts TEXT NOT NULL,"
        " component TEXT NOT NULL, event_type TEXT NOT NULL,"
        " payload_json TEXT NOT NULL);"
        "INSERT INTO turn_telemetry (event_seq,round,ts,component,event_type,payload_json)"
        " VALUES (1,1,'t','c','e','{}');"
    )
    con.commit()
    con.close()
    bytes_before = db.read_bytes()
    mtime_before = db.stat().st_mtime_ns

    conn = _ro_connect(db)
    try:
        build_turn_bundle(conn, 1)
    finally:
        conn.close()

    assert db.read_bytes() == bytes_before
    assert db.stat().st_mtime_ns == mtime_before
```

> If `_seed_rounds`'s exact signature differs (it lives in `tests/game/test_forensic_query.py:109`), match its real parameters; the assertions above only depend on it producing `events`+`narrative_log` for the requested rounds. If it does not expose the per-round seq window, derive it as shown (`MIN/MAX(seq) FROM events` for the single-round seeds).

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/game/test_forensic_query.py -v -k telemetry`
Expected: FAIL — `KeyError: 'telemetry'` (bundle has no telemetry key yet).

- [ ] **Step 3: Add the missing-table guard + the telemetry read to `build_turn_bundle`**

In `sidequest/game/forensic_query.py`, add a module-level helper (near `_safe_json` ~`:161`) and import the fold:

```python
from sidequest.game.forensic_fold import fold_known_facts, fold_turn_telemetry
```

```python
def _telemetry_for_round(
    conn: sqlite3.Connection, seq_start: int, seq_end: int, round_number: int
) -> dict:
    """Read this round's turn_telemetry, fold it. A missing table (old
    saves predating the substrate) is treated EXACTLY like zero rows —
    the read path is ?mode=ro and must never create the table."""
    has_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='turn_telemetry'"
    ).fetchone()
    if has_table is None:
        return {"rows": [], "by_component": {}, "total": 0, "unparseable_seqs": []}
    rows = conn.execute(
        "SELECT seq, event_seq, round, ts, component, event_type, payload_json "
        "FROM turn_telemetry "
        "WHERE (event_seq IS NOT NULL AND event_seq >= ? AND event_seq <= ?) "
        "   OR (round = ?) "
        "ORDER BY seq",
        (seq_start, seq_end, round_number),
    ).fetchall()
    fold = fold_turn_telemetry([dict(r) for r in rows])
    return {
        "rows": [
            {
                "seq": tr.seq,
                "component": tr.component,
                "event_type": tr.event_type,
                "ts": tr.ts,
                "fields": tr.fields,
            }
            for tr in fold.rows
        ],
        "by_component": fold.by_component,
        "total": fold.total,
        "unparseable_seqs": list(fold.unparseable_seqs),
    }


_EMPTY_TELEMETRY = {
    "rows": [],
    "by_component": {},
    "total": 0,
    "unparseable_seqs": [],
}
```

In `build_turn_bundle`, the **empty/unknown-round return** (`:214-223`) — add the key:

```python
        "telemetry": _EMPTY_TELEMETRY,
```

In `build_turn_bundle`, the **full success return** (~`:294-302`), after `seq_start, seq_end` are known (they come from `entry["seq_start"]`/`entry["seq_end"]` ~`:225`), compute and add:

```python
    telemetry = _telemetry_for_round(conn, seq_start, seq_end, round_number)
```

and add to the returned dict:

```python
        "telemetry": telemetry,
```

- [ ] **Step 4: Sync the coupled never-500 literals (sites 3–5)**

`sidequest/server/rest.py` `debug_save_turn` `empty` literal (`:462-470`) — add:

```python
            "telemetry": {"rows": [], "by_component": {}, "total": 0, "unparseable_seqs": []},
```

`tests/server/test_forensics_routes.py` — in BOTH `test_turn_bundle_unknown_slug_is_empty_not_500` (`:98-106`) and `test_turn_bundle_corrupt_save_is_empty_not_500` (`:118-126`) expected-dict literals, add the identical:

```python
        "telemetry": {"rows": [], "by_component": {}, "total": 0, "unparseable_seqs": []},
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/game/test_forensic_query.py tests/server/test_forensics_routes.py -v`
Expected: PASS — new telemetry read tests pass; the never-500 / byte-identity / "assembles all panels" tests still pass with the new key present.

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/forensic_query.py sidequest/server/rest.py tests/game/test_forensic_query.py tests/server/test_forensics_routes.py
git commit -m "feat(forensics): per-round telemetry read (event_seq+round bucket, ?mode=ro, missing-table=zero)"
```

---

## Task 8: Forensics UI — one collapsed "decision telemetry" evidence lane

**Files:**
- Modify: `sidequest/server/static/forensics.html` (new `<details>` before `</section>` ~`:320`)
- Modify: `tests/server/test_forensics_routes.py` (extend the wiring test to assert the lane string is served)

- [ ] **Step 1: Write the failing wiring assertion**

Append to the existing `test_forensics_route_is_wired_and_serves_html` in `tests/server/test_forensics_routes.py` (do not create a new test — extend the mandatory wiring test, `:145-154`):

```python
    assert "decision telemetry (this round)" in resp.text  # the new lane label
    assert "save predates the substrate" in resp.text  # honest-empty contract visible
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest "tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html" -v`
Expected: FAIL — neither string is in `forensics.html` yet.

- [ ] **Step 3: Add the lane to `forensics.html`**

In `sidequest/server/static/forensics.html`, the per-round bundle render builds a series of `<details>` lanes inside the evidence `<section>` (lanes end ~`:319`, section closes `'</section>'` ~`:320`). Following the KnownFacts-ledger lane pattern (`:271-277` content + `:304-305` wrapper), insert a new lane block. The bundle now carries `b.telemetry = {rows, by_component, total, unparseable_seqs}`. Add this just before the existing terminal-snapshot lane / the `'</section>'` close, using the existing `esc()` (`:78-79`) and `j()` (`:80`) helpers and the `.tier-absent` honest-empty shape (`:29`, `:264-288`):

```javascript
  const tel = (b.telemetry) || {rows:[],by_component:{},total:0,unparseable_seqs:[]};
  const telBody = tel.total
    ? Object.keys(tel.by_component).sort().map(comp => {
        const ets = tel.by_component[comp];
        const head = '<div class="seqs">'+esc(comp)+' — '+
          Object.keys(ets).sort().map(et => esc(et)+'×'+esc(ets[et])).join(', ')+
          '</div>';
        const lines = tel.rows.filter(r => r.component === comp).map(r =>
          '<tr><td class="tier-derived">'+esc(r.component)+'</td><td>'+
          esc(r.event_type)+'</td><td><pre style="margin:0">'+j(r.fields)+
          '</pre></td></tr>').join('');
        return head+'<table><tr><th>component</th><th>event_type</th>'+
          '<th>fields</th></tr>'+lines+'</table>';
      }).join('') +
      (tel.unparseable_seqs.length
        ? '<div class="tier-absent">— '+esc(tel.unparseable_seqs.length)+
          ' unparseable telemetry row(s) skipped (seq '+
          tel.unparseable_seqs.map(esc).join(', ')+')</div>'
        : '')
    : '<span class="tier-absent">— no decision telemetry (save predates the substrate)</span>';
```

and add the lane wrapper into the evidence-section string, immediately before the terminal-snapshot `<details>` (so it sits among the other lanes, before `'</section>'`):

```javascript
      '<details><summary>decision telemetry (this round)<span class="meta">'+
        esc(tel.total)+' signals</span></summary><div class="ev-body">'+
        telBody+'</div></details>'+
```

(Match the exact string-concatenation join style of the surrounding lane lines — every adjacent lane line ends with `+` and the section string finally closes with `'</section>'`.)

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest "tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html" -v`
Expected: PASS.

- [ ] **Step 5: Manual visual check (one real save)**

Boot the server, open `/forensics`, pick a save that has post-substrate rounds, click a round. Confirm: the "decision telemetry (this round) — N signals" lane appears collapsed, expands to component groups + rows, and a pre-substrate round shows exactly `— no decision telemetry (save predates the substrate)`. (Spec §5 / §Error-handling: absent must be honest, never fabricated.)

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/static/forensics.html tests/server/test_forensics_routes.py
git commit -m "feat(forensics): decision-telemetry evidence lane (honest-empty for old saves)"
```

---

## Task 9: Macro-header sink-health count (spec §Observability "note for the plan")

**Why:** the spec calls a save-wide "N telemetry rows this save" count in the macro header a "cheap sink-health tell for the GM." Lowest-priority tail; must not be invasive. The macro header is built in `selectSave()` from `list_saves` data — so add the count there (reuse the existing read path; do **not** reshape the timeline payload).

**Files:**
- Modify: `sidequest/game/forensic_query.py` (`list_saves` `:35`)
- Modify: `sidequest/server/static/forensics.html` (`.lbl` macro header `:112-116`)
- Test: `tests/game/test_forensic_query.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/game/test_forensic_query.py
def test_list_saves_includes_telemetry_row_count(tmp_path):
    saves = tmp_path / "saves"
    db = saves / "games" / "tel" / "save.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(
        "PRAGMA journal_mode=DELETE;"
        "CREATE TABLE session_meta (id INTEGER PRIMARY KEY CHECK (id=1),"
        " genre_slug TEXT NOT NULL, world_slug TEXT NOT NULL,"
        " created_at TEXT NOT NULL, last_played TEXT NOT NULL,"
        " schema_version INTEGER NOT NULL DEFAULT 1);"
        "INSERT INTO session_meta VALUES (1,'g','w','2026-05-18T00:00:00+00:00','2026-05-18T00:05:00+00:00',1);"
        "CREATE TABLE turn_telemetry (seq INTEGER PRIMARY KEY AUTOINCREMENT,"
        " event_seq INTEGER, round INTEGER, ts TEXT NOT NULL,"
        " component TEXT NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL);"
        "INSERT INTO turn_telemetry (event_seq,round,ts,component,event_type,payload_json)"
        " VALUES (1,1,'t','c','e','{}'),(2,1,'t','c','e','{}');"
    )
    con.commit()
    con.close()
    [save] = list_saves(saves)
    assert save["telemetry_rows"] == 2


def test_list_saves_telemetry_count_zero_when_table_missing(tmp_path):
    saves = tmp_path / "saves"
    db = saves / "games" / "old" / "save.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(
        "PRAGMA journal_mode=DELETE;"
        "CREATE TABLE session_meta (id INTEGER PRIMARY KEY CHECK (id=1),"
        " genre_slug TEXT NOT NULL, world_slug TEXT NOT NULL,"
        " created_at TEXT NOT NULL, last_played TEXT NOT NULL,"
        " schema_version INTEGER NOT NULL DEFAULT 1);"
        "INSERT INTO session_meta VALUES (1,'g','w','2026-05-18T00:00:00+00:00','2026-05-18T00:05:00+00:00',1);"
    )
    con.commit()
    con.close()
    [save] = list_saves(saves)
    assert save["telemetry_rows"] == 0  # missing table -> 0, not error
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/game/test_forensic_query.py -v -k telemetry_row`
Expected: FAIL — `KeyError: 'telemetry_rows'`.

- [ ] **Step 3: Add the count to `list_saves`**

In `list_saves` (`forensic_query.py:35`), where each per-save dict is assembled, add a defensive count using the already-open `_ro_connect` connection for that save (missing table → 0, never raise):

```python
        try:
            has_tt = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='turn_telemetry'"
            ).fetchone()
            telemetry_rows = (
                conn.execute("SELECT COUNT(*) FROM turn_telemetry").fetchone()[0]
                if has_tt
                else 0
            )
        except sqlite3.Error:
            telemetry_rows = 0
```

and include `"telemetry_rows": telemetry_rows` in the dict appended for that save.

- [ ] **Step 4: Surface it in the macro header**

In `forensics.html` `selectSave()` (`:101-118`), the macro header `.lbl` is built as `'macro — '+esc(slug)+' · '+esc(tl.length)+' rounds · click a column'` (`:112-116`). `selectSave` already has the saves list available from the initial `/api/debug/saves` fetch (the list that rendered the clickable saves). Thread the selected save's `telemetry_rows` into the `.lbl`:

```javascript
    // `sv` = the selected save object from the /api/debug/saves list
    '<section><p class="lbl">macro — '+esc(slug)+' · '+esc(tl.length)+
      ' rounds · '+esc(sv && sv.telemetry_rows != null ? sv.telemetry_rows : 0)+
      ' telemetry rows · click a column</p><svg id="strip"></svg>'+
```

If `selectSave` does not already hold the selected save object, look it up from the saves array it already fetched (`saves.find(s => s.slug === slug)`) — do **not** add a new fetch.

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/game/test_forensic_query.py -v -k telemetry_row`
Expected: PASS. Manual: reopen `/forensics`, pick a save → macro header reads `… · N telemetry rows · …`.

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/forensic_query.py sidequest/server/static/forensics.html tests/game/test_forensic_query.py
git commit -m "feat(forensics): macro-header telemetry row count (sink-health tell)"
```

---

## Task 10: Hot-path cost measurement + go/no-go on coalescing

**Why:** the spec mandates "Plan must measure on a real turn; if pathological, coalesce per-turn." This is a measurement gate, not premature optimization (coalescing stays deferred unless the number says otherwise — YAGNI).

**Files:**
- Test: `tests/server/test_turn_telemetry_wiring.py` (append a measurement assertion to the existing wiring test infra)

- [ ] **Step 1: Add a measurement assertion**

Append to `tests/server/test_turn_telemetry_wiring.py`, reusing the same one-real-turn harness from Task 5:

```python
def test_turn_telemetry_insert_count_is_not_pathological(<harness_fixture>):
    """Sink cost guard: one real turn must not explode telemetry inserts.
    The C2 model batches in-txn inserts into one commit; out-of-txn
    publishes each take a short txn. This pins a sane ceiling; if a future
    change blows it, that is the signal to coalesce per-turn (spec risk)."""
    save_db = <play_one_turn_and_return_save_db_path>(<harness_fixture>)
    import sqlite3

    conn = sqlite3.connect(f"file:{save_db}?mode=ro", uri=True)
    try:
        n = conn.execute("SELECT COUNT(*) FROM turn_telemetry").fetchone()[0]
    finally:
        conn.close()
    # One turn's watcher publishes. Generous ceiling: this is a regression
    # tripwire, not a tight bound. If a real turn legitimately exceeds it,
    # raise the ceiling AND open a Phase-follow-on coalesce note — do not
    # silently bump it.
    assert 0 < n <= 500, f"one turn wrote {n} telemetry rows — investigate/coalesce"
```

- [ ] **Step 2: Run and record the real number**

Run: `uv run pytest "tests/server/test_turn_telemetry_wiring.py::test_turn_telemetry_insert_count_is_not_pathological" -v -s`
Expected: PASS. **Record the actual `n`** in the commit body. If `n` is surprisingly large (hundreds), note it for the spec-check Architect (it may warrant a Phase follow-on coalesce sub-project — do **not** implement coalescing in this plan; the spec explicitly defers it).

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_turn_telemetry_wiring.py
git commit -m "test(telemetry): hot-path cost guard — one turn wrote N rows (N=<fill>)"
```

---

## Final gate (before handoff to review)

- [ ] **Full server suite green:**

Run: `uv run pytest -q` (via `testing-runner`, `REPOS: server`)
Expected: full suite passes, 0 failed. Confirm no pre-existing forensics/telemetry test regressed and the new files are all collected.

- [ ] **Lint/format clean:**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: clean. (`# noqa: BLE001` on the two intentional broad excepts matches the existing `rest.py:476` / fold conventions.)

- [ ] **Push the branch:**

```bash
git push -u origin feat/forensics-telemetry-substrate
```

Dev does NOT open the PR (per project handoff rules). Hand off to the spec-check Architect → review → merge. The module-level `SCHEMA_SQL` change means existing live saves gain the `turn_telemetry` table on their next open by the running server (forward-only, no backfill — pre-substrate rounds honestly show the empty lane).

---

## Documented out-of-scope risks (for the spec-check Architect, not tasks)

1. **Pre-existing `_maybe_persist_encounter_row` unconditional-commit hazard.** It does `_event_store._conn.execute(...)` then `.commit()` unconditionally (`watcher_hub.py:315-319`). If it ever fires *inside* an open C2 turn transaction it would prematurely commit it. It is gated to `field=="encounter"` ops and largely fires outside the C2 block, which is why it has not corrupted atomicity. **This plan does not touch it** (out of scope; fixing it goes exponential). The *new* sink deliberately does **not** repeat that mistake — it branches on `conn.in_transaction`. Flag for a possible future hardening sub-project.
2. **`round` is best-effort.** `turn_manager` is unreachable from `publish_event`'s scope (stateless free function); `round` is taken from `fields["round"]` when a caller included it, else NULL. Per-round bucketing is primarily by `event_seq` range; the `round` column only rescues NULL-`event_seq` rows. Phase 2 (watcher instrumentation) can make `round` reliably present in more publishes.
3. **Payloads may embed narration snippets.** Accepted per spec (the save is a local GM/dev artifact, not player-facing). Noted, not gated.
4. **Raw payload drift over time** is intentional (raw substrate). The read fold is defensive by contract (`esc`, never-raise, loud-skip) — same posture as `fold_known_facts`.

---

## Self-Review (run against the spec)

**Spec coverage:** Component 1 schema → Task 2. Component 2 write sink (resolve-the-unknown + C2-atomic + fully-wrapped) → Task 1 (invariant) + Task 3 + Task 4. Component 3 read path (`_ro_connect`, event_seq+round bucket, `build_turn_bundle.telemetry`) → Task 7. Component 4 pure `fold_turn_telemetry` mirroring `fold_known_facts` → Task 6. Component 5 UI lane (collapsed `<details>`, honest-empty, `esc()`) → Task 8. §Testing's five named tests → Tasks 6 (pure fold), 7 (read + never-500 + byte-identity), 5 (mandatory wiring), 4 (sink-failure isolation). §Observability macro-header count → Task 9. §Risks hot-path measurement → Task 10. §Migration forward-only / read-must-not-create → Task 2 (no `_PER_SLOT_TABLES`, `IF NOT EXISTS`) + Task 7 (`sqlite_master` guard, `?mode=ro`). §"Open implementation question (plan's first task)" → resolved by investigation, codified as Task 1; verdict: reuse the existing `_event_store` binding (path **c**), no registry, no call-site threading. No gaps.

**Placeholder scan:** the only intentional fill-ins are `<HARNESS_IMPORT>` / `<harness_fixture>` / `<play_one_turn_and_return_save_db_path>` in Tasks 5 & 10 — these are explicitly *bounded* (Step 1 of Task 5 names exactly how to discover them via `pytest --collect-only`, and forbids forking a new harness). Every code-bearing step contains complete code. No "TBD"/"add error handling"/"similar to Task N".

**Type/name consistency:** `TelemetryRow`/`TelemetryFold`/`fold_turn_telemetry` defined in Task 6 are consumed with matching field names (`rows`, `by_component`, `total`, `unparseable_seqs`, and `TelemetryRow.{seq,component,event_type,ts,fields}`) in Task 7's `_telemetry_for_round` and Task 8's UI render. `_persist_turn_telemetry` (Task 3) is the exact name called from `publish_event`. The `turn_telemetry` column list (`event_seq, round, ts, component, event_type, payload_json` + autoincrement `seq`) is identical across Task 2 DDL, Task 3 INSERT, Task 7 SELECT, and Task 9 COUNT. The empty-telemetry literal `{"rows":[],"by_component":{},"total":0,"unparseable_seqs":[]}` is identical across the five coupled sites in Task 7. Consistent.
