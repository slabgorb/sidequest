# PostgreSQL Migration — The Port (Pool + Repositories + Consumer Lift + Importer + Cutover) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port SideQuest's per-session SQLite save store to the single PostgreSQL database stood up in Task-Group 1 — in one direction, no SQLite dual-path — by building a pooled `psycopg3` backend behind grown repository interfaces, lifting every raw-connection consumer onto typed methods, importing the live saves, flipping the live backend to Postgres, and deleting the single-writer scar tissue (`SAVE_WRITE_LOCK`, WAL/`busy_timeout`, the load-path checkpoint, the `in_transaction`/`MAX(seq)` census heuristic, `?mode=ro`, `SqliteStore.connection()`/`.store`).

**Architecture:** One logical Postgres database (schema already created by TG1's `0001_initial_unified_schema`). A single module-level `psycopg_pool.ConnectionPool` fed by `db_config.database_url()` is the only connection source. Domain repositories — `SaveRepository`, `DungeonRepository`, `TelemetrySink`, `ForensicReader` — expose **typed methods only**; no raw connection ever escapes a repository (the invariant that makes the backend swappable). Per-session writes serialize on a `SELECT … FOR UPDATE` row lock on the `sessions` row, so different sessions never contend and same-session writers serialize without any application-level lock. The mechanical-census write shares the turn's `SaveTransaction`, which is *why* the two-connection deadlock cannot recur. SQLite survives only as the read-only importer source.

**Tech Stack:** Python 3.12+ (running 3.14), `uv`, `psycopg[binary]` 3.x + `psycopg_pool.ConnectionPool`, `alembic` (migrations only), PostgreSQL 18 (local `postgresql@18` keg-only at `/opt/homebrew/opt/postgresql@18/bin`; CI `services: postgres:18`), `pytest` (xdist `-n auto`, 30 s timeout) against ephemeral real Postgres via the TG1 harness (`tests/persistence/conftest.py`).

---

## Context the engineer needs before starting

You are working in `sidequest-server/` (a subrepo of the `oq-1` orchestrator). The branch `feat/postgres-substrate` already exists and is checked out — **all work in this plan lands on it** (TG1 is already committed there; do not branch off, do not merge to `develop`; the backend flips inside this plan, in the cutover task-group).

Read these first — they are the design authority:
- `docs/superpowers/specs/2026-05-26-postgres-persistence-migration-design.md` (the design; especially "Governing principle: the backend is a swappable detail behind the DAL", "Target architecture", "Concurrency model").
- `docs/superpowers/plans/2026-05-26-postgres-migration-tg1-infra-schema-alembic.md` — its "Schema translation decisions" section is **locked**; the adapters in this plan write to that exact schema (a `sessions` table with `session_id BIGINT GENERATED ALWAYS AS IDENTITY` PK + `session_slug TEXT UNIQUE`; every per-session table carries `session_id BIGINT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE`; `events` PK `(session_id, seq)`; timestamps stay `TEXT` ISO-8601; booleans stay `INTEGER` 0/1; `BYTEA` for `dungeon_map.mask`; `scenario_archive.scenario_session_id TEXT` + `session_id BIGINT PK`).

### What already exists (reuse, do not rebuild)
- **TG1:** `sidequest/game/db_config.py` (`database_url()` → plain `postgresql://…` conninfo, fail-loud; `alembic_url()` → `postgresql+psycopg://…`; `MissingDatabaseUrlError`). `alembic/versions/0001_initial_unified_schema.py` (all 17 tables). `tests/persistence/conftest.py` (`migrated_db` session-scoped per-xdist-worker throwaway DB that runs `alembic upgrade head`; `pg_conn` rollback-isolated `psycopg.Connection`).
- **Slice 1a (merged to develop, carried on this branch):** `sidequest/game/repository.py` (`SaveRepository`/`SaveTransaction` Protocols — currently events + projection only). `sidequest/game/sqlite_repository.py` (`SqliteSaveRepository` over `SqliteStore`, with the transitional `.store` hatch). `EventLog`, `ProjectionCache`, and `emitters.emit_event`'s "C2 block" already go through the repository.

### The current SQLite reach-through you are replacing (from the codebase map)
- **Save store:** `sidequest/game/persistence.py::SqliteStore` — full typed surface (`save`/`load`/`init_session`/`append_narrative`/`max_narrative_round`/`recent_narrative`/`load_world_save`/`save_world_save`/`list_location_promotions`/`upsert_location_promotion`/`close`/`connection`), module fns (`upsert_game`/`get_game`/`set_claude_session_id`/`query_encounter_events`/`db_path_for_slug`), `SCHEMA_SQL`, `_configure_connection` (WAL/`busy_timeout`/`foreign_keys`), the load-path `PRAGMA wal_checkpoint(TRUNCATE)`, and **10 `with SAVE_WRITE_LOCK` acquisition sites** (`persistence.py:398,415,446,485,571,661,673,773,867,894`; `sqlite_repository.py:72`; `emitters.py:50,101`; `watcher_hub.py:329,398`).
- **Raw `_conn` consumers to lift:** `server/views.py:340,354,371,380` (narration backfill — 4 reads); `server/emitters.py:51,102` (scrapbook INSERT + image-url UPDATE); `game/scrapbook_coverage.py:89` (turn-id coverage read); `handlers/connect.py:1108` (scrapbook image-url replay map); `telemetry/watcher_hub.py:330,334` (encounter-row `INSERT INTO events` + commit) and `:382,400,401` (`_persist_turn_telemetry`: `conn=store._conn`, `SELECT MAX(seq)`, `INSERT INTO turn_telemetry`); `dungeon/materializer.py:1777` (`persistence._conn` Plan-5 boundary + `:1857` commit / `:1863` rollback).
- **Dungeon borrow sites (`.connection()`):** `server/session_helpers.py:601`, `server/websocket_session_handler.py:1249`, `dungeon/session_integration.py:116` (+ `conn.commit()` at `:164`).
- **Typed-method consumers needing only retyping (`SqliteStore` → `SaveRepository`):** ~17 `agents/tools/*.py` (`ctx.store.load()/.save()`), `websocket_session_handler.py` (`sd.store.save` 1783/3107/4007, `.append_narrative` 4029/4037, `.max_narrative_round` 4058, `.close` 1878), `session_helpers.py:1207` (`.recent_narrative`), `rest.py` (`get_game`/`upsert_game`/`query_encounter_events`/`load_world_save`/`initialize`/`close` across the debug+games endpoints), `scene_harness_router.py:154-158`, `handlers/connect.py:269-273,651`, `location_resolver.py:194,219,247` + `location_view.py:61`.
- **Forensic RO readers:** `game/forensic_query.py` (`_ro_connect` `?mode=ro`, `list_saves`/`build_timeline`/`build_turn_bundle`/`mechanical_strip`/`open_save_readonly`), `corpus/save_reader.py` (`SaveReader`, `?mode=ro&immutable=1`, `iter_events`/`iter_narrative_log`).
- **Injection points:** `_SessionData.store: SqliteStore` at `server/session_state.py:152`; `bind_event_store(store)` at `telemetry/watcher_hub.py:284`, called from `handlers/connect.py:270-272`; `SqliteStore(...)` construction at `connect.py:268`, `rest.py:592/612/632/709/725/749` (+ `.open` at `:334`), `scene_harness_router.py:154`.

### CLAUDE.md rules that bite here
- **No Silent Fallbacks / NO fallbacks (hard ban):** a missing pool/URL raises; a retired mechanism gets zero backstop; never a "degraded → silent alternative path".
- **One mechanism per problem:** there is exactly one writable backend (Postgres) and one delivery path; SQLite is read-only importer source only. No dual writable backend, ever.
- **Every test suite needs a wiring test; No Source-Text Wiring Tests:** prove wiring with `information_schema`/behavior/OTEL-span assertions or fixture-driven behavior — never `read_text()`/`inspect.getsource` of source.
- **No content-coupled tests:** never load live `genre_packs/*` and assert; use fixtures.
- **No Stubbing / Verify Wiring, Not Just Existence:** every new repository method gets a non-test consumer by the end of the cutover task-group; a half-lifted tree (some calls typed, some raw) is the failure mode to avoid.
- **Durable retention / save preservation:** the importer is a hard cutover gate; dry-run on a *copy* (db+wal+shm trio, then checkpoint the copy) before any live file is touched. Never sacrifice a save.
- **Do not `git stash`** (use branches/commits); never skip git hooks.

### Concurrency contract (the heart of the port)
Every write goes through `SaveRepository.transaction()`, which:
1. borrows one connection from the pool inside `with pool.connection() as conn:` (the connection never escapes that scope or crosses threads),
2. immediately takes the per-session row lock: `conn.execute("SELECT 1 FROM sessions WHERE session_id = %s FOR UPDATE", (session_id,))`,
3. yields a `SaveTransaction` bound to that connection,
4. commits on clean exit, rolls back on exception (psycopg's `with conn:` transaction semantics).

Different sessions lock different rows → never contend. Same-session writers serialize on the row lock → no `SAVE_WRITE_LOCK`. The census/telemetry write is issued **on the same `SaveTransaction`** (method `write_telemetry`), so it shares the turn's connection and transaction — the A-vs-B two-connection deadlock is structurally impossible, and the old `in_transaction`/`MAX(seq)` heuristic is deleted. From async handlers, repository calls offload via `anyio.to_thread.run_sync` so two players' turns run on independent pooled connections.

`events.seq` is assigned per-session inside the locked transaction:
```sql
INSERT INTO events (session_id, seq, kind, payload_json, created_at)
VALUES (%s, (SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE session_id = %s), %s, %s, %s)
RETURNING seq
```
The row lock guarantees the `MAX(seq)+1` read-modify-write is serialized within the session.

---

## File Structure

New code lands as a **package, split by domain** (spec "new repository code → packages, not single files"; ~2k-line buffer ceiling):

- `sidequest/game/db_pool.py` — the module-level `ConnectionPool` (lazy open from `db_config.database_url()`, `get_pool()`, `close_pool()`); the only place a pool is created.
- `sidequest/game/pg/__init__.py` — exports `PgSaveRepository`, `PgDungeonRepository`, `PgTelemetrySink`, `PgForensicReader`, `resolve_session_id`.
- `sidequest/game/pg/_conn.py` — internal helpers: `session_tx(pool, session_id)` context manager (borrow + `FOR UPDATE` + commit/rollback), row-mapping helpers.
- `sidequest/game/pg/sessions.py` — session lifecycle (`ensure_session`, `get_game`, `resolve_session_id`, `init_session`).
- `sidequest/game/pg/events.py` — events + projection (the `SaveTransaction` impl lives here).
- `sidequest/game/pg/snapshot.py` — `game_state` + `world_save`.
- `sidequest/game/pg/narrative.py` — `narrative_log` + the narration-backfill reads.
- `sidequest/game/pg/scrapbook.py` — `scrapbook_entries` writes/reads + coverage + image-url map.
- `sidequest/game/pg/promotions.py` — `location_promotions`.
- `sidequest/game/pg/save_repository.py` — `PgSaveRepository` composing the above into the grown `SaveRepository` Protocol + `transaction()`.
- `sidequest/game/pg/dungeon.py` — `PgDungeonRepository` (all 13 dungeon methods + `transaction()` boundary).
- `sidequest/game/pg/telemetry.py` — `PgTelemetrySink` (standalone out-of-frame `record`; in-frame writes ride `SaveTransaction.write_telemetry`).
- `sidequest/game/pg/forensic.py` — `PgForensicReader` (MVCC reads: `list_saves`/`build_timeline`/`build_turn_bundle`/…).
- `sidequest/game/importer.py` — SQLite-RO → versioned JSON bundle → Postgres FK-ordered import.

Interfaces grow in place:
- `sidequest/game/repository.py` — `SaveRepository`/`SaveTransaction` Protocols grow to the full typed surface; new `DungeonRepository`, `TelemetrySink`, `ForensicReader` Protocols added (or a sibling `repositories.py` if `repository.py` grows past the buffer — split if it exceeds ~400 lines).

Modified consumers (cutover task-group): `server/session_state.py` (`_SessionData` fields), `handlers/connect.py`, `server/views.py`, `server/emitters.py`, `game/scrapbook_coverage.py`, `telemetry/watcher_hub.py`, `dungeon/materializer.py`, `dungeon/session_integration.py`, `server/session_helpers.py`, `server/websocket_session_handler.py`, `server/rest.py`, `server/scene_harness_router.py`, `agents/tools/*.py`, `game/location_resolver.py`, `game/location_view.py`.

Retired at cutover: `SAVE_WRITE_LOCK` + 10 sites, `_configure_connection` WAL/busy_timeout, the load-path `wal_checkpoint`, `SqliteStore.connection()` + all `._conn` external access, `SqliteSaveRepository` + its `.store` hatch, the `in_transaction`/`MAX(seq)` census branch, `?mode=ro` opens. `SqliteStore` itself shrinks to the read-only shape the importer consumes (or is replaced by `corpus/save_reader.py`'s reader).

---

## Conventions for every task below
- **TDD:** write the failing test, run it RED, implement, run it GREEN, commit. Postgres tests use the TG1 fixtures (`pg_conn` for shape/behavior; build repositories over a pool pointed at the `migrated_db` URL).
- **Env for local runs:** `SIDEQUEST_TEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test"` and `SIDEQUEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test"` (`$USER` = `slabgorb`; PG 18 service already running).
- **Paramstyle:** psycopg uses `%s` placeholders (never `?`). `executemany` for batch inserts.
- **Timestamps:** keep writing ISO-8601 `TEXT` via `datetime.now(tz=UTC).isoformat()` (do not switch to `now()`/`TIMESTAMPTZ` — honors "does not change game logic"). The one SQLite `datetime('now')` in `resolve_thread` becomes a Python ISO string passed as a param.
- **Commit cadence:** one commit per task (per the `git add … && git commit -m …` step). Conventional-commit prefixes: `feat(persistence)`, `test(persistence)`, `refactor(persistence)`, `perf`, `chore`.

---

## TASK-GROUP A — Pool foundation + the grown SaveRepository over Postgres

Builds the pool and the complete Postgres `SaveRepository` (every save-domain table), unit-tested against ephemeral Postgres. **No live wiring changes** — `SqliteStore` is still what sessions construct; this group leaves the tree green by adding new, tested, not-yet-wired code.

### Task A1: The connection pool

**Files:**
- Create: `sidequest/game/db_pool.py`
- Test: `tests/persistence/test_db_pool.py`

- [ ] **Step 1: Write the failing test**

```python
"""ConnectionPool foundation — single source, lazy, fail-loud (ADR-115)."""

from __future__ import annotations

import psycopg
import pytest

from sidequest.game import db_pool


def test_get_pool_uses_database_url(monkeypatch, migrated_db: str) -> None:
    # migrated_db is the +psycopg form; the pool wants the plain conninfo.
    plain = migrated_db.replace("postgresql+psycopg://", "postgresql://", 1)
    monkeypatch.setenv("SIDEQUEST_DATABASE_URL", plain)
    db_pool.close_pool()  # reset any cached pool
    pool = db_pool.get_pool()
    with pool.connection() as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1
    db_pool.close_pool()


def test_get_pool_is_singleton(monkeypatch, migrated_db: str) -> None:
    plain = migrated_db.replace("postgresql+psycopg://", "postgresql://", 1)
    monkeypatch.setenv("SIDEQUEST_DATABASE_URL", plain)
    db_pool.close_pool()
    assert db_pool.get_pool() is db_pool.get_pool()
    db_pool.close_pool()


def test_get_pool_fails_loud_when_url_unset(monkeypatch) -> None:
    monkeypatch.delenv("SIDEQUEST_DATABASE_URL", raising=False)
    db_pool.close_pool()
    from sidequest.game.db_config import MissingDatabaseUrlError

    with pytest.raises(MissingDatabaseUrlError):
        db_pool.get_pool()
```

- [ ] **Step 2: Run it RED**

`cd /Users/slabgorb/Projects/oq-1/sidequest-server && SIDEQUEST_TEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run pytest tests/persistence/test_db_pool.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.db_pool'`.

- [ ] **Step 3: Implement the pool**

```python
"""Process-global Postgres connection pool (ADR-115).

The single source of Postgres connections. Lazily opened from
db_config.database_url(). No Silent Fallbacks: an unset URL raises via the
resolver. Connections are borrowed inside `with get_pool().connection()`
scopes and never escape them or cross threads.
"""

from __future__ import annotations

import threading

from psycopg_pool import ConnectionPool

from sidequest.game.db_config import database_url

_POOL: ConnectionPool | None = None
_LOCK = threading.Lock()


def get_pool() -> ConnectionPool:
    """Return the process-global pool, opening it on first use."""
    global _POOL
    if _POOL is None:
        with _LOCK:
            if _POOL is None:
                _POOL = ConnectionPool(
                    conninfo=database_url(),
                    min_size=1,
                    max_size=16,
                    open=True,
                    name="sidequest-save",
                )
    return _POOL


def close_pool() -> None:
    """Close and discard the pool (shutdown / test reset)."""
    global _POOL
    with _LOCK:
        if _POOL is not None:
            _POOL.close()
            _POOL = None
```

- [ ] **Step 4: Run it GREEN**

`… uv run pytest tests/persistence/test_db_pool.py -q` → Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run ruff check --fix sidequest/game/db_pool.py tests/persistence/test_db_pool.py && uv run ruff format sidequest/game/db_pool.py tests/persistence/test_db_pool.py && git add sidequest/game/db_pool.py tests/persistence/test_db_pool.py && git commit -m "feat(persistence): psycopg_pool ConnectionPool foundation (ADR-115)"
```

### Task A2: Session lifecycle + the locked transaction helper

**Files:**
- Create: `sidequest/game/pg/__init__.py` (empty for now), `sidequest/game/pg/_conn.py`, `sidequest/game/pg/sessions.py`
- Test: `tests/persistence/test_pg_sessions.py`

- [ ] **Step 1: Write the failing test**

```python
"""Session lifecycle + per-session row-lock transaction (ADR-115)."""

from __future__ import annotations

import psycopg
import pytest

from sidequest.game import db_pool
from sidequest.game.pg import sessions


@pytest.fixture
def pool(monkeypatch, migrated_db: str):
    plain = migrated_db.replace("postgresql+psycopg://", "postgresql://", 1)
    monkeypatch.setenv("SIDEQUEST_DATABASE_URL", plain)
    db_pool.close_pool()
    yield db_pool.get_pool()
    db_pool.close_pool()


def test_ensure_session_inserts_then_returns_same_id(pool) -> None:
    sid1 = sessions.ensure_session(
        pool, slug="g_w", mode="solo", genre_slug="g", world_slug="w"
    )
    sid2 = sessions.ensure_session(
        pool, slug="g_w", mode="solo", genre_slug="g", world_slug="w"
    )
    assert sid1 == sid2  # upsert on session_slug, not a second row


def test_resolve_session_id_returns_none_for_unknown(pool) -> None:
    assert sessions.resolve_session_id(pool, slug="missing") is None


def test_get_game_roundtrips(pool) -> None:
    sessions.ensure_session(pool, slug="g_w", mode="multiplayer", genre_slug="g", world_slug="w")
    row = sessions.get_game(pool, slug="g_w")
    assert row is not None and row.mode == "multiplayer" and row.genre_slug == "g"
```

- [ ] **Step 2: Run it RED** → `ModuleNotFoundError: sidequest.game.pg`.

- [ ] **Step 3: Implement `_conn.py`**

```python
"""Internal Postgres helpers: the per-session locked transaction (ADR-115)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool


@contextmanager
def session_tx(pool: ConnectionPool, session_id: int) -> Iterator[psycopg.Connection]:
    """Borrow a pooled connection, take the per-session row lock, yield it.

    Commits on clean exit, rolls back on exception. The row lock on the
    sessions row serializes same-session writers (replacing SAVE_WRITE_LOCK);
    different sessions lock different rows and never contend.
    """
    with pool.connection() as conn:  # psycopg commits on clean __exit__
        conn.execute("SELECT 1 FROM sessions WHERE session_id = %s FOR UPDATE", (session_id,))
        yield conn
```

- [ ] **Step 4: Implement `sessions.py`**

```python
"""Session lifecycle over Postgres (ADR-115). Absorbs session_meta + games."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from psycopg_pool import ConnectionPool

_PER_SESSION_TABLES = (
    "projection_cache", "events", "narrative_log", "lore_fragments",
    "scenario_archive", "scrapbook_entries", "world_save", "turn_telemetry",
    "location_promotions", "game_state",
)


@dataclass(frozen=True)
class GameRow:
    slug: str
    mode: str
    genre_slug: str
    world_slug: str
    claude_session_id: str | None
    created_at: str


def resolve_session_id(pool: ConnectionPool, *, slug: str) -> int | None:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT session_id FROM sessions WHERE session_slug = %s", (slug,)
        ).fetchone()
    return int(row[0]) if row else None


def ensure_session(
    pool: ConnectionPool, *, slug: str, mode: str, genre_slug: str, world_slug: str
) -> int:
    """Create the sessions row if absent (idempotent on session_slug); return session_id."""
    now = datetime.now(tz=UTC).isoformat()
    with pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO sessions (session_slug, mode, genre_slug, world_slug, created_at, last_played)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_slug) DO UPDATE SET last_played = excluded.last_played
            RETURNING session_id
            """,
            (slug, mode, genre_slug, world_slug, now, now),
        ).fetchone()
    return int(row[0])


def get_game(pool: ConnectionPool, *, slug: str) -> GameRow | None:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT session_slug, mode, genre_slug, world_slug, claude_session_id, created_at "
            "FROM sessions WHERE session_slug = %s",
            (slug,),
        ).fetchone()
    if row is None:
        return None
    return GameRow(slug=row[0], mode=row[1], genre_slug=row[2], world_slug=row[3],
                   claude_session_id=row[4], created_at=row[5])


def init_session(pool: ConnectionPool, *, session_id: int) -> None:
    """Slot reinitialization — clear every per-session row for a fresh start.

    The sessions row (genre/world/mode/slug) is preserved; the cascade is NOT
    used here because we keep the session identity and only wipe its content.
    """
    with pool.connection() as conn, conn.transaction():
        conn.execute("SELECT 1 FROM sessions WHERE session_id = %s FOR UPDATE", (session_id,))
        for table in _PER_SESSION_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE session_id = %s", (session_id,))
```

> Note: `init_session`'s table list is a fixed allowlist (not user input) — the f-string is safe. `dungeon_*` tables are wiped by the DungeonRepository's own reset in Task-Group B if a slot reinit must clear the dungeon; the save-slot reinit here matches today's `_PER_SLOT_TABLES` scope.

- [ ] **Step 5: Update `pg/__init__.py`** to export `resolve_session_id` (leave the repository exports as you add them):
```python
from sidequest.game.pg.sessions import GameRow, ensure_session, get_game, init_session, resolve_session_id  # noqa: F401
```

- [ ] **Step 6: Run it GREEN** → 3 passed.

- [ ] **Step 7: Commit**
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run ruff check --fix sidequest/game/pg/ tests/persistence/test_pg_sessions.py && uv run ruff format sidequest/game/pg/ tests/persistence/test_pg_sessions.py && git add sidequest/game/pg/__init__.py sidequest/game/pg/_conn.py sidequest/game/pg/sessions.py tests/persistence/test_pg_sessions.py && git commit -m "feat(persistence): pg session lifecycle + per-session row-lock transaction (ADR-115)"
```

### Task A3: Events + projection (the SaveTransaction impl)

**Files:**
- Create: `sidequest/game/pg/events.py`
- Test: `tests/persistence/test_pg_events.py`

- [ ] **Step 1: Write the failing test**

```python
"""Events seq assignment + projection upsert over Postgres (ADR-115)."""

from __future__ import annotations

import pytest

from sidequest.game import db_pool
from sidequest.game.pg import sessions
from sidequest.game.pg.events import PgEventStore
from sidequest.game.projection_filter import FilterDecision


@pytest.fixture
def store(monkeypatch, migrated_db: str):
    plain = migrated_db.replace("postgresql+psycopg://", "postgresql://", 1)
    monkeypatch.setenv("SIDEQUEST_DATABASE_URL", plain)
    db_pool.close_pool()
    pool = db_pool.get_pool()
    sid = sessions.ensure_session(pool, slug="g_w", mode="solo", genre_slug="g", world_slug="w")
    yield PgEventStore(pool, session_id=sid)
    db_pool.close_pool()


def test_append_event_assigns_monotonic_per_session_seq(store) -> None:
    a = store.append_event(kind="NARRATION", payload_json="{}")
    b = store.append_event(kind="NARRATION", payload_json="{}")
    assert (a.seq, b.seq) == (1, 2)


def test_read_events_since(store) -> None:
    store.append_event(kind="A", payload_json="{}")
    store.append_event(kind="B", payload_json="{}")
    rows = store.read_events_since(since_seq=1)
    assert [r.kind for r in rows] == ["B"]


def test_latest_event_seq_zero_when_empty(store) -> None:
    assert store.latest_event_seq() == 0


def test_projection_upsert_then_read(store) -> None:
    ev = store.append_event(kind="NARRATION", payload_json="{}")
    store.write_projection(event_seq=ev.seq, player_id="p1",
                           decision=FilterDecision(include=True, payload_json='{"x":1}'))
    store.write_projection(event_seq=ev.seq, player_id="p1",
                           decision=FilterDecision(include=False, payload_json=None))
    rows = store.read_projection_since(player_id="p1", since_seq=0)
    assert len(rows) == 1 and rows[0].include is False
```

- [ ] **Step 2: Run it RED.**

- [ ] **Step 3: Implement `events.py`**

```python
"""Events (per-session seq) + projection_cache over Postgres (ADR-115).

PgSaveTransaction is the unit-of-work bound to one locked connection; the
census/telemetry write rides the same transaction via write_telemetry.
"""

from __future__ import annotations

from datetime import UTC, datetime

import psycopg
from psycopg_pool import ConnectionPool

from sidequest.game.event_log import EventRow
from sidequest.game.pg._conn import session_tx
from sidequest.game.projection.cache import CachedDecision
from sidequest.game.projection_filter import FilterDecision
from sidequest.telemetry.spans import projection_cache_fill_span

_INSERT_EVENT = """
INSERT INTO events (session_id, seq, kind, payload_json, created_at)
VALUES (%s, (SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE session_id = %s), %s, %s, %s)
RETURNING seq
"""

_UPSERT_PROJECTION = """
INSERT INTO projection_cache (session_id, event_seq, player_id, include, payload_json)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (session_id, event_seq, player_id) DO UPDATE SET
    include = excluded.include, payload_json = excluded.payload_json
"""

_INSERT_TELEMETRY = """
INSERT INTO turn_telemetry (session_id, event_seq, round, ts, component, event_type, payload_json)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


class PgSaveTransaction:
    """Operations bound to one locked connection; no individual commit."""

    def __init__(self, conn: psycopg.Connection, session_id: int) -> None:
        self._conn = conn
        self._sid = session_id

    def append_event(self, *, kind: str, payload_json: str) -> EventRow:
        now = datetime.now(tz=UTC).isoformat()
        seq = self._conn.execute(
            _INSERT_EVENT, (self._sid, self._sid, kind, payload_json, now)
        ).fetchone()[0]
        return EventRow(seq=int(seq), kind=kind, payload_json=payload_json, created_at=now)

    def write_projection(self, *, event_seq: int, player_id: str, decision: FilterDecision) -> None:
        with projection_cache_fill_span(event_seq=event_seq, player_id=player_id):
            payload = decision.payload_json if decision.include else None
            self._conn.execute(
                _UPSERT_PROJECTION,
                (self._sid, event_seq, player_id, 1 if decision.include else 0, payload),
            )

    def write_telemetry(
        self, *, event_seq: int | None, round: int | None, ts: str,
        component: str, event_type: str, payload_json: str,
    ) -> None:
        """Census/telemetry write riding the turn's transaction (event_seq is
        the real seq from append_event in-frame, or None out-of-frame)."""
        self._conn.execute(
            _INSERT_TELEMETRY,
            (self._sid, event_seq, round, ts, component, event_type, payload_json),
        )


class PgEventStore:
    """Convenience facade over single-statement event/projection ops (each in
    its own locked transaction). The owning PgSaveRepository delegates here."""

    def __init__(self, pool: ConnectionPool, *, session_id: int) -> None:
        self._pool = pool
        self._sid = session_id

    def append_event(self, *, kind: str, payload_json: str) -> EventRow:
        with session_tx(self._pool, self._sid) as conn:
            return PgSaveTransaction(conn, self._sid).append_event(kind=kind, payload_json=payload_json)

    def write_projection(self, *, event_seq: int, player_id: str, decision: FilterDecision) -> None:
        with session_tx(self._pool, self._sid) as conn:
            PgSaveTransaction(conn, self._sid).write_projection(
                event_seq=event_seq, player_id=player_id, decision=decision
            )

    def read_events_since(self, *, since_seq: int) -> list[EventRow]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT seq, kind, payload_json, created_at FROM events "
                "WHERE session_id = %s AND seq > %s ORDER BY seq ASC",
                (self._sid, since_seq),
            ).fetchall()
        return [EventRow(seq=r[0], kind=r[1], payload_json=r[2], created_at=r[3]) for r in rows]

    def latest_event_seq(self) -> int:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events WHERE session_id = %s", (self._sid,)
            ).fetchone()
        return int(row[0])

    def read_projection_since(self, *, player_id: str, since_seq: int) -> list[CachedDecision]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT event_seq, include, payload_json FROM projection_cache "
                "WHERE session_id = %s AND player_id = %s AND event_seq > %s ORDER BY event_seq ASC",
                (self._sid, player_id, since_seq),
            ).fetchall()
        return [CachedDecision(event_seq=r[0], include=bool(r[1]), payload_json=r[2]) for r in rows]
```

- [ ] **Step 4: Run it GREEN** → 4 passed.

- [ ] **Step 5: Commit**
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run ruff check --fix sidequest/game/pg/events.py tests/persistence/test_pg_events.py && uv run ruff format sidequest/game/pg/events.py tests/persistence/test_pg_events.py && git add sidequest/game/pg/events.py tests/persistence/test_pg_events.py && git commit -m "feat(persistence): pg events seq-assignment + projection + telemetry-on-tx (ADR-115)"
```

### Task A4: Snapshot + world_save adapter

**Files:** Create `sidequest/game/pg/snapshot.py`; Test `tests/persistence/test_pg_snapshot.py`.

- [ ] **Step 1: Failing test** — assert `save_snapshot`/`load_snapshot` round-trip a `GameSnapshot`, `load_snapshot` returns `None` when absent, `save_world_save`/`load_world_save` round-trip. Build a `PgSnapshotStore(pool, session_id=sid)` (ensure_session first). Use the project's existing `GameSnapshot`/`WorldSave`/`SavedSession` constructors (import from `sidequest.game.state` / wherever `SqliteStore.save`/`load` use them — check `persistence.py` imports). Assert the loaded snapshot's `snapshot_json` equals what was saved.

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `snapshot.py`** with `PgSnapshotStore`:
  - `save_snapshot(snapshot)`:
    ```sql
    INSERT INTO game_state (session_id, snapshot_json, saved_at) VALUES (%s, %s, %s)
    ON CONFLICT (session_id) DO UPDATE SET snapshot_json = excluded.snapshot_json, saved_at = excluded.saved_at
    ```
    then `UPDATE sessions SET last_played = %s WHERE session_id = %s`. Both inside one `session_tx`. Serialize the snapshot exactly as `SqliteStore.save` does (reuse the same `snapshot.to_json()` / serialization helper — read `persistence.py:save` to copy the exact call). Emit the same `state_transition`/`snapshot_saved` spans `SqliteStore.save` emits.
  - `load_snapshot() -> SavedSession | None`: `SELECT snapshot_json FROM game_state WHERE session_id = %s`; rehydrate via the same deserialization `SqliteStore.load` uses; assemble `SavedSession` with `_load_meta`-equivalent fields read from `sessions` (`genre_slug`/`world_slug`/`created_at`/`last_played`) and `recent_narrative(3)` (delegate to the narrative store — pass it in, or read inline). Raise `SaveSchemaIncompatibleError` on the same condition `SqliteStore.load` raises it. **No `wal_checkpoint`, no `.bak` copy** — those retire under Postgres.
  - `load_world_save() -> WorldSave`: `SELECT payload_json FROM world_save WHERE session_id = %s` (mirror `SqliteStore.load_world_save`'s empty-default behavior exactly).
  - `save_world_save(ws)`: `INSERT … ON CONFLICT (session_id) DO UPDATE …` for `world_save`.

- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): pg game_state + world_save adapter (ADR-115)`.

### Task A5: Narrative adapter + narration-backfill reads

**Files:** Create `sidequest/game/pg/narrative.py`; Test `tests/persistence/test_pg_narrative.py`.

- [ ] **Step 1: Failing test** — `append_narrative` then `recent_narrative(limit)` returns newest-N in ascending order; `max_narrative_round` returns the max (0 when empty); and the backfill reads (below) return the expected seqs given a seeded `events` set. Seed events via `PgEventStore`.

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `narrative.py`** with `PgNarrativeStore(pool, session_id)`:
  - `append_narrative(entry)`: `INSERT INTO narrative_log (session_id, round_number, author, content, tags, created_at) VALUES (%s,%s,%s,%s,%s,%s)` (created_at = ISO now). Inside `session_tx`.
  - `max_narrative_round() -> int`: `SELECT COALESCE(MAX(round_number), 0) FROM narrative_log WHERE session_id = %s`.
  - `recent_narrative(limit) -> list[NarrativeEntry]`:
    ```sql
    SELECT round_number, author, content, tags FROM (
        SELECT round_number, author, content, tags, id FROM narrative_log
        WHERE session_id = %s ORDER BY id DESC LIMIT %s
    ) sub ORDER BY id ASC
    ```
  - `generate_recap() -> str | None`: delegate to `recent_narrative(3)` + the existing `_generate_recap` (import it from `persistence.py`).
  - **The four `views.py` backfill reads** as one typed method `read_narration_backfill(*, player_id, limit) -> list[object]`, moving the SQL into the adapter (translate `?`→`%s`, add `session_id = %s` to every WHERE, keep the `CHAPTER_MARKER`/`COALESCE(MAX(seq)…)` subquery shape verbatim, and fold in the `_cached_payload` read `SELECT include, payload_json FROM projection_cache WHERE session_id=%s AND player_id=%s AND event_seq=%s`). Return the same assembled objects `views.backfill_last_narration_block` returns today (read `server/views.py:301-400` and reproduce the assembly exactly — the SQL moves to the adapter, the assembly logic stays a thin wrapper in `views.py` calling this method).

- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): pg narrative_log + narration-backfill reads (ADR-115)`.

### Task A6: Scrapbook + location_promotions adapters

**Files:** Create `sidequest/game/pg/scrapbook.py`, `sidequest/game/pg/promotions.py`; Tests `tests/persistence/test_pg_scrapbook.py`, `tests/persistence/test_pg_promotions.py`.

- [ ] **Step 1: Failing tests.** Scrapbook: `append_scrapbook_entry(...)` then a read returns it; `update_scrapbook_image_url(turn_id, url)` updates the most-recent NULL-image row for that turn and returns True (False when none); `scrapbook_turn_ids(max_turn)` returns the distinct turn_ids ≤ max_turn; `scrapbook_image_url_map()` returns `{turn_id: image_url}` for non-null images. Promotions: `upsert_location_promotion(row)` then `list_location_promotions(region_id)` round-trips, and a second upsert with the same `(region_id, entity_id)` updates rather than duplicates.

- [ ] **Step 2: RED.**

- [ ] **Step 3a: Implement `scrapbook.py`** `PgScrapbookStore(pool, session_id)`:
  - `append_scrapbook_entry(*, turn_id, scene_title, scene_type, location, image_url, narrative_excerpt, world_facts, npcs_present, render_status)`:
    `INSERT INTO scrapbook_entries (session_id, turn_id, scene_title, scene_type, location, image_url, narrative_excerpt, world_facts, npcs_present, render_status, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)` inside `session_tx`. (Match `emitters.persist_scrapbook_entry`'s field order/values exactly; read `emitters.py:30-67`.)
  - `update_scrapbook_image_url(*, turn_id, image_url) -> bool`: Postgres has no `rowid`; the SQLite `WHERE rowid=(SELECT rowid … ORDER BY rowid DESC LIMIT 1)` becomes a CTE on the identity `id`:
    ```sql
    UPDATE scrapbook_entries SET image_url = %s
    WHERE id = (
        SELECT id FROM scrapbook_entries
        WHERE session_id = %s AND turn_id = %s AND image_url IS NULL
        ORDER BY id DESC LIMIT 1
    )
    ```
    Return `cur.rowcount > 0`.
  - `scrapbook_turn_ids(*, max_turn) -> set[int]`: `SELECT DISTINCT turn_id FROM scrapbook_entries WHERE session_id = %s AND turn_id >= 1 AND turn_id <= %s` (from `scrapbook_coverage.py:89`).
  - `scrapbook_image_url_map() -> dict[int, str]`: `SELECT turn_id, image_url FROM scrapbook_entries WHERE session_id = %s AND image_url IS NOT NULL` (from `connect.py:1108`).

- [ ] **Step 3b: Implement `promotions.py`** `PgPromotionStore(pool, session_id)` — translate `SqliteStore.list_location_promotions`/`upsert_location_promotion` (drop `save_id`; key by `session_id`; `ON CONFLICT (session_id, region_id, entity_id) DO UPDATE …`). `LocationPromotionRow` loses `save_id` — **flag this**: the `LocationPromotionRow` dataclass currently carries `save_id`; in the consumer-lift task-group its callers (`location_resolver.py`, `location_view.py`) stop passing `save_id`. For this adapter, accept the row without `save_id`. If the dataclass must keep `save_id` for the SQLite importer-read path, add a separate `PgLocationPromotionRow` without it (do not contort the live type).

- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): pg scrapbook + location_promotions adapters (ADR-115)`.

### Task A7: Compose `PgSaveRepository` + grow the Protocol

**Files:** Create `sidequest/game/pg/save_repository.py`; Modify `sidequest/game/repository.py`; Test `tests/persistence/test_pg_save_repository.py`.

- [ ] **Step 1: Failing test** — construct `PgSaveRepository.for_slug(pool, slug=…, mode=…, genre_slug=…, world_slug=…)` (ensures the session, stores `session_id`), then exercise the full surface through the ONE object: `transaction()` appends an event + writes a projection atomically; `save`/`load` snapshot; `append_narrative`/`recent_narrative`; and assert `isinstance(repo, SaveRepository)` (runtime_checkable Protocol). Add a **rollback test**: inside `with repo.transaction() as tx:` append an event then `raise RuntimeError`; afterwards `latest_event_seq()` is unchanged (the row lock + rollback held).

- [ ] **Step 2: RED.**

- [ ] **Step 3: Grow the Protocols in `repository.py`.** Add to `SaveTransaction`: `write_telemetry(*, event_seq, round, ts, component, event_type, payload_json) -> None`. Add to `SaveRepository` the full typed surface (signatures only — Protocol): `save(snapshot)`, `load() -> SavedSession | None`, `init_session()`, `append_narrative(entry)`, `max_narrative_round() -> int`, `recent_narrative(limit) -> list[NarrativeEntry]`, `generate_recap() -> str | None`, `load_world_save() -> WorldSave`, `save_world_save(ws)`, `list_location_promotions(*, region_id)`, `upsert_location_promotion(row)`, `append_scrapbook_entry(...)`, `update_scrapbook_image_url(*, turn_id, image_url) -> bool`, `scrapbook_turn_ids(*, max_turn) -> set[int]`, `scrapbook_image_url_map() -> dict[int, str]`, `read_narration_backfill(*, player_id, limit) -> list[object]`, `ensure_session(...)`/`get_game(*, slug)`/`close()`. Keep `append_event`/`read_events_since`/`latest_event_seq`/`write_projection`/`read_projection_since`/`transaction()`. If `repository.py` exceeds ~400 lines, split the new repos' Protocols into `repositories.py` and re-export.

- [ ] **Step 4: Implement `save_repository.py`** — `PgSaveRepository` holds a `pool` + `session_id` and composes `PgEventStore`, `PgSnapshotStore`, `PgNarrativeStore`, `PgScrapbookStore`, `PgPromotionStore`; `transaction()` is:
```python
@contextmanager
def transaction(self) -> Iterator[PgSaveTransaction]:
    with session_tx(self._pool, self._sid) as conn:
        yield PgSaveTransaction(conn, self._sid)
```
and the convenience methods delegate to the sub-stores. Add `for_slug(pool, *, slug, mode, genre_slug, world_slug)` classmethod that calls `sessions.ensure_session` then constructs.

- [ ] **Step 5: GREEN. Step 6: Commit** `feat(persistence): compose PgSaveRepository + grow SaveRepository protocol (ADR-115)`.

### Task A8: Task-group A regression gate

- [ ] **Step 1:** `… uv run pytest tests/persistence/ -q` → all green.
- [ ] **Step 2:** `uv run ruff check sidequest/game/pg sidequest/game/db_pool.py && uv run ruff format --check sidequest/game/pg sidequest/game/db_pool.py` → clean.
- [ ] **Step 3:** Confirm live store untouched: `git diff develop --stat -- sidequest/game/persistence.py sidequest/game/sqlite_repository.py` → empty. (We have only ADDED the pg/ package + pool; nothing live changed yet.)

---

## TASK-GROUP B — DungeonRepository over Postgres

Gives the dungeon domain a `PgDungeonRepository` over the shared pool and a named caller-owned transaction boundary that replaces the `materializer.py:1777` `persistence._conn` seam. **No live wiring yet.**

### Task B1: PgDungeonRepository (reads + writes)

**Files:** Create `sidequest/game/pg/dungeon.py`; Modify `sidequest/game/repository.py` (add `DungeonRepository` Protocol); Test `tests/persistence/test_pg_dungeon.py`.

- [ ] **Step 1: Failing test** — over a `migrated_db` pool + an ensured session: `set_campaign_seed`/`get_campaign_seed` (write-once raises on second set); `commit_expansion` then `load_map`/`load_masks` round-trips a `RegionGraph` (build a minimal one via the existing constructors used in `tests/dungeon/test_persistence.py` — read that file for fixtures); `put_frontier`/`load_frontier`; `record_mutation`/`load_mutations`; `open_thread`/`get_thread`/`open_threads`/`resolve_thread` (resolve sets status + resolved_at, raises `NotFoundError` on unknown). Reuse the dungeon model types from `sidequest/dungeon/persistence.py` (`FrontierEdge`, `DungeonMutation`, `ComplicationThread`, `RegionGraph`).

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `dungeon.py`** `PgDungeonRepository(pool, session_id)` — port every `DungeonStore` method (signatures from the map) with these dialect translations:
  - **No `ensure_schema`** — the schema is Alembic-owned; drop the method (its callers in Task-Group D stop calling it).
  - `get/set_campaign_seed`: `dungeon_meta` keyed by `session_id` (PK), not `id=1`. `set` is write-once: `INSERT INTO dungeon_meta (session_id, campaign_seed, created_at) VALUES (%s,%s,%s)`; on `psycopg.errors.UniqueViolation` raise the same write-once error `DungeonStore.set_campaign_seed` raises.
  - `commit_expansion`: `executemany` the node inserts (`INSERT INTO dungeon_map (session_id, region_id, expansion_id, depth_score, generator_version, payload, mask, created_at) VALUES (%s,…)`, `mask` as `bytes`/`None` → BYTEA) and edge inserts (`INSERT INTO dungeon_edge (session_id, expansion_id, a, b, kind, hidden, shortcut, payload, created_at) VALUES (…)`; `hidden`/`shortcut` as `1`/`0` INTEGER). On `psycopg.errors.IntegrityError` → `PersistError` (freeze violation), same as today.
  - `load_map`: `SELECT payload FROM dungeon_map WHERE session_id=%s`; `SELECT payload FROM dungeon_edge WHERE session_id=%s ORDER BY edge_id`. `load_masks`: `SELECT region_id, mask FROM dungeon_map WHERE session_id=%s AND mask IS NOT NULL ORDER BY region_id` (mask BYTEA → `bytes` → utf-8 JSON, same decode as today).
  - `put_frontier`: SQLite `INSERT OR REPLACE` → `INSERT … ON CONFLICT (session_id, frontier_edge_id) DO UPDATE SET …`. `load_frontier`: `… WHERE session_id=%s ORDER BY frontier_edge_id`.
  - `record_mutation`: append `INSERT INTO dungeon_mutation_overlay (session_id, region_id, kind, payload, created_at) VALUES (…)`. `load_mutations`: `… WHERE session_id=%s ORDER BY mutation_id`.
  - `open_thread`/`get_thread`/`resolve_thread`/`open_threads`: keyed by `(session_id, thread_id)`; `resolve_thread` SQLite `datetime('now')` → Python ISO string param; rowcount 0 → `NotFoundError`. Emit the same `ledger_add_span`/`ledger_resolve_span`.
  - Add `transaction()` ctx-manager (via `session_tx`) — the named caller-owned boundary that replaces `materializer`'s raw `conn.commit()/rollback()`. Add a `reset()` (DELETE all dungeon_* rows for the session) only if a slot reinit needs it (check `session_integration.py` — if seed bootstrap is idempotent, you may not need reset; do not add unused methods).
  - Add `DungeonRepository` Protocol to `repository.py` covering these methods.

- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): PgDungeonRepository + caller-owned transaction boundary (ADR-115)`.

---

## TASK-GROUP C — TelemetrySink + ForensicReader over Postgres

### Task C1: PgTelemetrySink

**Files:** Create `sidequest/game/pg/telemetry.py`; Modify `repository.py` (add `TelemetrySink` Protocol); Test `tests/persistence/test_pg_telemetry.py`.

- [ ] **Step 1: Failing test** — (a) **in-frame:** open `repo.transaction()`, `append_event` (seq=N), then `tx.write_telemetry(event_seq=N, round=1, ts=…, component="mechanical", event_type="x", payload_json="{}")`; after commit, the row exists with `event_seq=N` AND the event exists — proving they shared the transaction (rollback the event → telemetry row also gone). (b) **out-of-frame:** `PgTelemetrySink(pool, session_id).record(round=1, ts=…, component="x", event_type="y", payload_json="{}")` writes a row with `event_seq IS NULL` in its own short transaction. (c) **the encounter-row write** (`_maybe_persist_encounter_row` analogue): `sink.append_encounter_event(kind="ENCOUNTER_START", payload_json="{}")` appends to `events` and returns the seq.

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `telemetry.py`** `PgTelemetrySink(pool, session_id)`:
  - `record(*, round, ts, component, event_type, payload_json)`: out-of-frame standalone write with `event_seq = NULL`, in its own `session_tx`. (Mirrors today's `else: with conn:` branch.)
  - `append_encounter_event(*, kind, payload_json) -> EventRow`: delegate to a `session_tx` + `PgSaveTransaction.append_event` (replaces `_maybe_persist_encounter_row`'s raw `INSERT INTO events … CURRENT_TIMESTAMP` + commit; created_at becomes ISO now for consistency).
  - The **in-frame** path is NOT a method here — it is `SaveTransaction.write_telemetry` (Task A3), called by `emit_mechanical_census` inside the open `emit_event` transaction in Task-Group D. The sink object exists for the out-of-frame + encounter cases. Document this clearly in the module docstring (one sink, two entry points: ride-the-tx vs standalone — mirrors today's `in_transaction` branch, NOT a parallel mechanism).
  - Add `TelemetrySink` Protocol (`record`, `append_encounter_event`).

- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): PgTelemetrySink riding the turn transaction (ADR-115)`.

### Task C2: PgForensicReader

**Files:** Create `sidequest/game/pg/forensic.py`; Modify `repository.py` (add `ForensicReader` Protocol); Test `tests/persistence/test_pg_forensic.py`.

- [ ] **Step 1: Failing test** — seed a session with events/narrative/telemetry/scrapbook via the Task-A/C stores, then assert `build_timeline(session_id)` returns the expected round boundaries; `build_turn_bundle(session_id, round_number)` returns events in `[lo,hi]`, the projection rows, the scrapbook rows, and the folded telemetry; `list_saves()` returns the session with its `genre_slug`/`world_slug`/`last_played` + telemetry counts. (No `?mode=ro` — these are plain pool reads under MVCC.)

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `forensic.py`** `PgForensicReader(pool)` — port `forensic_query.py`'s functions to pooled Postgres reads filtered by `session_id`:
  - `list_saves() -> list[dict]`: read from `sessions` (replaces the per-file `session_meta WHERE id=1` walk) joined/aggregated with `turn_telemetry` counts (`COUNT(*)`, `COUNT(*) FILTER (WHERE component='mechanical')`). No `sqlite_master` existence probes — the tables always exist.
  - `build_timeline(session_id)`: port `_round_boundaries`/`_events_for_round`. Replace the SQLite `substr/replace` timestamp-normalization (`_NORM_EV_TS`) with a Postgres-side normalization or — since timestamps are ISO TEXT — a direct string compare (read `forensic_query.py:120-173` and reproduce the boundaries semantics; ISO-8601 sorts lexically, so the normalization may be unnecessary — verify against a seeded fixture).
  - `build_turn_bundle(session_id, round_number)`: port the `narrative_log`/`events [lo,hi]`/`events <= hi` fold/`projection_cache`/`scrapbook_entries`/`_telemetry_for_round`/`_mechanical_for_round` reads, all `WHERE session_id = %s`. Reuse the existing `forensic_fold` helper unchanged (it folds Python dicts, engine-agnostic).
  - Keep the same return shapes so the REST endpoints in Task-Group D need only swap the data source.
  - Add `ForensicReader` Protocol.

- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): PgForensicReader (MVCC reads, retires ?mode=ro) (ADR-115)`.

---

## TASK-GROUP D — Lift every consumer + flip construction to Postgres (the cutover core)

This is the one-direction flip. By the end, `_SessionData` carries Postgres repositories, every consumer calls typed methods, and no live path touches `SqliteStore` for writes. Order the tasks so the suite returns to green at the **end of the task-group** (run against ephemeral Postgres); intermediate commits may be red — that is acceptable for a coordinated cutover, but keep each task as self-contained as possible and run the full suite at D-final.

> Before starting D, set the test/run env so the live path has a Postgres URL: the existing test harness already provides ephemeral DBs; for the dev server, `SIDEQUEST_DATABASE_URL` must be set (the resolver fails loud otherwise — that is intended).

### Task D1: `_SessionData` gains repository accessors; construction flips

**Files:** Modify `sidequest/server/session_state.py` (the `_SessionData` dataclass at `:143`), `sidequest/handlers/connect.py` (`:268-273`), `sidequest/server/scene_harness_router.py` (`:154-158`).

- [ ] **Step 1: Failing test** (fixture-driven wiring test, not source-text) — construct a session via the connect path against a `migrated_db` pool and assert `sd.repository` is a `PgSaveRepository` (isinstance `SaveRepository`), `sd.dungeon_repository` is a `PgDungeonRepository`, and `sd.telemetry_sink` is a `PgTelemetrySink`. (Use the smallest real connect entrypoint; if connect is too heavy, assert on the constructor helper you extract.)
- [ ] **Step 2: RED.**
- [ ] **Step 3:** Add fields to `_SessionData`: `repository: SaveRepository`, `dungeon_repository: DungeonRepository`, `telemetry_sink: TelemetrySink` (replace `store: SqliteStore`). In `connect.py`, replace `SqliteStore(db)` + `store.initialize()` + `bind_event_store(store)` with: resolve the pool (`db_pool.get_pool()`), `PgSaveRepository.for_slug(pool, slug=…, mode=…, genre_slug=…, world_slug=…)`, construct the dungeon repo + telemetry sink on the same `session_id`, and `bind_event_store(repository)` (see D5). `scene_harness_router.py` likewise. **Keep `SqliteStore` importable** — the importer (Task-Group E) and forensic-archive reads still use it read-only; just stop constructing it as the live write store.
- [ ] **Step 4: GREEN (this test). Step 5: Commit** `refactor(persistence): _SessionData carries pg repositories; connect constructs over the pool (ADR-115)`.

### Task D2: Lift the typed-method consumers (retype + rename)

**Files:** `agents/tools/*.py` (~17), `server/websocket_session_handler.py`, `server/session_helpers.py`, `server/rest.py`, `handlers/connect.py`, `game/location_resolver.py`, `game/location_view.py`.

- [ ] **Step 1:** These already call interface-shaped methods; the lift is mechanical: `ctx.store` / `sd.store` → `ctx.repository` / `sd.repository`; `.load()`/`.save()`/`.append_narrative()`/`.recent_narrative()`/`.max_narrative_round()`/`.close()`/`.load_world_save()` resolve to the grown `SaveRepository`. `upsert_game`/`get_game`/`query_encounter_events` module-fn calls → `repository.ensure_session`/`repository.get_game`/`repository.query_encounter_events` (add `query_encounter_events` to the protocol + adapter if a consumer needs it — `rest.py:711`). `location_resolver.py`/`location_view.py` drop `save_id` and call `repository.list_location_promotions(region_id=…)`/`upsert_location_promotion(row)`.
- [ ] **Step 2:** Where these run inside `async` handlers, wrap the (sync) repository calls in `await anyio.to_thread.run_sync(...)` so the pooled DB work leaves the event loop (match the existing await pattern at the call site; if the call site is sync, leave it sync). Verify no connection escapes a `with` scope.
- [ ] **Step 3:** Run the relevant existing suites (`tests/agents/tools/…`, `tests/server/…`) against ephemeral Postgres; fix breakage by fitting tests to the new repository shape (never revert features, never xfail in-flight features — per project rule). Commit per cohesive cluster (tools, wss_handler, rest) with `refactor(persistence): lift <cluster> onto SaveRepository typed methods (ADR-115)`.

### Task D3: Lift the raw-`_conn` reads (views, scrapbook-coverage, connect replay)

**Files:** `server/views.py` (`:301-400`), `game/scrapbook_coverage.py` (`:89`), `handlers/connect.py` (`:1108`).

- [ ] **Step 1:** Replace `views.backfill_last_narration_block`'s four `store._conn.execute(...)` reads with a single `sd.repository.read_narration_backfill(player_id=…, limit=…)` call (the SQL now lives in `pg/narrative.py` from Task A5); keep the assembly/return shape identical (a fixture-driven test asserts the same output for a seeded event set). Replace `scrapbook_coverage.detect_scrapbook_coverage_gaps`'s `store._conn.execute("SELECT DISTINCT turn_id …")` with `repository.scrapbook_turn_ids(max_turn=…)`. Replace `connect.py:1108`'s replay `SELECT turn_id,image_url …` with `repository.scrapbook_image_url_map()`.
- [ ] **Step 2:** Run `tests/server/test_*backfill*`, scrapbook-coverage tests against ephemeral PG; fit to the new shape. Commit `refactor(persistence): lift narration-backfill + scrapbook-coverage + replay reads onto typed methods (ADR-115)`.

### Task D4: Lift the scrapbook writers (emitters)

**Files:** `server/emitters.py` (`persist_scrapbook_entry` `:30-67`, `update_scrapbook_image_url` `:70-118`).

- [ ] **Step 1:** Replace the `with SAVE_WRITE_LOCK, store._conn:` + raw INSERT/UPDATE with `handler.<session>.repository.append_scrapbook_entry(...)` / `update_scrapbook_image_url(turn_id=…, image_url=…)` (Task A6). Drop the `SAVE_WRITE_LOCK` import from this file.
- [ ] **Step 2:** Run scrapbook emit tests against ephemeral PG; fit. Commit `refactor(persistence): lift scrapbook writers onto SaveRepository (ADR-115)`.

### Task D5: The census/telemetry lift — ride the turn transaction

**Files:** `server/emitters.py` (`emit_event` C2 block `:172`, `emit_mechanical_census` call `:289`), `telemetry/watcher_hub.py` (`bind_event_store` `:284`, `_maybe_persist_encounter_row` `:312`, `_persist_turn_telemetry` `:353`, `publish_event` `:516`).

- [ ] **Step 1: Failing test** (fixture-driven) — drive one `emit_event` turn that also emits a mechanical census; assert that on success BOTH the `events` row and the `turn_telemetry` row (with `event_seq` = that event's seq) exist, and on a forced failure inside the turn BOTH roll back (shared transaction). Assert the standalone (out-of-frame) census path writes `event_seq IS NULL`.
- [ ] **Step 2: RED.**
- [ ] **Step 3:** Rework so the census write happens **inside** the `emit_event` `with repository.transaction() as tx:` block: `emit_mechanical_census` receives the open `tx` and calls `tx.write_telemetry(event_seq=<the appended event's seq>, …)`. `watcher_hub.publish_event` no longer reaches `_event_store._conn`; instead `bind_event_store` binds the **`TelemetrySink`** (and the repository), and the out-of-frame path calls `sink.record(...)`. `_maybe_persist_encounter_row` calls `sink.append_encounter_event(...)`. **Delete** the `in_transaction`/`MAX(seq)` heuristic, the `conn = store._conn`, and the `with SAVE_WRITE_LOCK` wrappers in `watcher_hub.py`. The `tests/server/test_save_write_lock.py` regression is reframed: the deadlock-impossibility is now structural (one connection/transaction per turn) — replace that test with one asserting the census rides the turn transaction (the D5 Step-1 test covers it; delete or rewrite the lock test rather than keep it asserting a deleted lock).
- [ ] **Step 4: GREEN. Step 5: Commit** `refactor(persistence): census rides the turn transaction; delete in_transaction/MAX(seq) heuristic (ADR-115)`.

### Task D6: Lift the dungeon borrow sites

**Files:** `server/session_helpers.py` (`:601`), `server/websocket_session_handler.py` (`:1249`), `dungeon/session_integration.py` (`:116-164`), `dungeon/materializer.py` (`:1777,1857,1863`).

- [ ] **Step 1:** Replace `DungeonStore(sd.store.connection())` at the two read sites with `sd.dungeon_repository.load_map(entrance_id=…)`. In `session_integration.py`, the seed-bootstrap (`ensure_schema`/`get_campaign_seed`/`set_campaign_seed` + explicit `conn.commit()`) becomes `dungeon_repository.get_campaign_seed()` / `set_campaign_seed(seed)` (no `ensure_schema` — Alembic owns DDL; no manual `conn.commit()` — the repo's `transaction()` owns it). In `materializer._stage_commit`, replace `conn = persistence._conn` + `persistence.commit_expansion(...)` + `conn.commit()`/`conn.rollback()` with `with dungeon_repository.transaction() as tx: tx.commit_expansion(...); tx.put_frontier(...)` (the boundary method from Task B1) — the `PersistError` rollback is the context manager's exception path.
- [ ] **Step 2:** Run dungeon materializer/session-integration suites against ephemeral PG; fit. Commit `refactor(persistence): lift DungeonStore borrow sites onto PgDungeonRepository boundary (ADR-115)`.

### Task D7: Lift the forensic/REST reads

**Files:** `server/rest.py` (debug + games + encounter endpoints), `game/forensic_query.py` consumers, `corpus/save_reader.py` consumers (live-read only — the importer keeps its SQLite reader).

- [ ] **Step 1:** Point the REST debug endpoints (`/api/debug/state|saves|save/{slug}/timeline|turn|snapshot`, `/api/sessions/{slug}/encounter_events`, `/api/games/{slug}|/hub`, `POST /api/games`) at `PgForensicReader` / `repository` instead of `SqliteStore(db)` + `open_save_readonly`. `debug_state` reads `repository.load()` (or `PgForensicReader.snapshot(session_id)`); the timeline/turn endpoints call `PgForensicReader.build_timeline/ build_turn_bundle(session_id, …)` (resolve `slug → session_id` via `resolve_session_id`). Keep the try/except → lossy-empty behavior (a missing session yields the empty bundle, not a 500) — but **no silent SQLite fallback**.
- [ ] **Step 2:** Run `tests/server/test_*rest*` / forensic endpoint tests against ephemeral PG; fit. Commit `refactor(persistence): point REST forensic/games endpoints at PgForensicReader (ADR-115)`.

### Task D8: Task-group D regression gate

- [ ] **Step 1:** Full suite against ephemeral PG: `SIDEQUEST_TEST_DATABASE_URL=… SIDEQUEST_DATABASE_URL=… uv run pytest -q` → green except the known pre-existing env-coupled set (test_61_12 compaction, namegen-audit, dogfight-smoke, pack-validator) and the OTel xdist flake; confirm any *new* red is fixed, not deferred.
- [ ] **Step 2:** Grep-audit for leftover reach-through (this is a behavior/wiring check, run as a command, not a source-text *test*): `rg "SqliteStore|SAVE_WRITE_LOCK|\._conn|\.store\b|mode=ro" sidequest/ --glob '!**/persistence.py' --glob '!**/importer.py' --glob '!**/save_reader.py'` → only importer/forensic-archive read paths should remain; everything live must be lifted. List any stragglers and lift them. Commit `chore(persistence): close remaining raw-connection stragglers (ADR-115)`.

---

## TASK-GROUP E — The importer (lands before cutover so it can be dry-run)

> **DESCOPED 2026-05-26 — superseded by the as-built one-shot.** Tasks E1–E3
> below describe a versioned-JSON-bundle exporter (`export_bundle`/`import_bundle`),
> a whole-corpus `python -m sidequest.cli.import_saves --save-dir … --database-url …`
> CLI, and a multi-save dry-run loop. **None of that was built.** The shipped
> importer is a single-save, no-CLI, no-bundle one-shot: `sidequest/game/importer.py`
> exposes `import_sqlite_save(sqlite_path, pool) -> ImportSummary`, which opens the
> SQLite save RO+IMMUTABLE and does a direct FK-ordered INSERT (NO intermediate
> JSON, raw rows, `created_at`/`last_played` normalized to T-isoformat) inside one
> transaction. The entry point is `python -m sidequest.game.importer`, hardcoded to
> the single `coyote_star-mp` save. Read the E1–E3 steps as historical design intent;
> the module docstring is authoritative. `sidequest/cli/import_saves.py` does not exist.

### Task E1: SQLite-RO reader → versioned JSON bundle

**Files:** Create `sidequest/game/importer.py`; Test `tests/persistence/test_importer_bundle.py`.

- [ ] **Step 1: Failing test** — build a tiny SQLite save fixture (use `SqliteStore.open_in_memory()` + write a session_meta/game_state/events/narrative/scrapbook/world_save/location_promotions/dungeon_* set, OR point at a copied real save), call `export_bundle(sqlite_path) -> dict`, and assert the bundle has a `schema_version`, the `session` block (slug/mode/genre/world/created_at/last_played), and the per-table row lists with the OLD column names (incl. `scenario_archive.session_id` as the clue-graph id, to be mapped on import).
- [ ] **Step 2: RED.**
- [ ] **Step 3:** Implement `export_bundle` — open the SQLite DB read-only via `corpus/save_reader.py`'s reader (extend it as needed) or a local `?mode=ro&immutable=1` connection; read every table; emit a versioned dict (`{"bundle_version": 1, "session": {...}, "events": [...], "narrative_log": [...], …, "dungeon_map": [...], …}`). Preserve `seq`, `round_number`, ISO timestamps verbatim. This is the only place `?mode=ro` survives (importer source).
- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): SQLite→JSON bundle exporter (importer phase 1) (ADR-115)`.

### Task E2: Bundle → Postgres FK-ordered import + round-trip test

**Files:** Modify `sidequest/game/importer.py`; Test `tests/persistence/test_importer_roundtrip.py`.

- [ ] **Step 1: Failing test (round-trip)** — `export_bundle(sqlite_fixture)` → `import_bundle(pool, bundle)` into a `migrated_db`, then read back via the Task-A/B/C repositories and assert equivalence: same events (seq + kind + payload), same snapshot, same narrative, same scrapbook, same dungeon graph, same location promotions; and `scenario_archive`'s old `session_id` landed in `scenario_session_id` while the row is keyed by the new surrogate `session_id`.
- [ ] **Step 2: RED.**
- [ ] **Step 3:** Implement `import_bundle(pool, bundle)` — in one transaction: `ensure_session` (get surrogate `session_id`), then insert FK-ordered (sessions → game_state/world_save → events → projection_cache → narrative_log/lore/scenario_archive/scrapbook/turn_telemetry/location_promotions → dungeon_map → dungeon_edge → dungeon_frontier/mutation/ledger/meta). Map `scenario_archive.session_id (old TEXT) → scenario_session_id`; map `location_promotions.save_id → session_id`; translate booleans/`BLOB`→`BYTEA`. Preserve `events.seq` exactly (insert explicit seq, do NOT re-derive — `INSERT INTO events (session_id, seq, …) VALUES (…)`).
- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): JSON-bundle→Postgres importer + round-trip test (ADR-115)`.

### Task E3: Importer CLI + dry-run on a save copy

**Files:** Create `sidequest/cli/import_saves.py` (or extend an existing CLI module); Test `tests/persistence/test_importer_cli.py`.

- [ ] **Step 1: Failing test** — the CLI resolves a save dir, exports+imports each `.db`, and is idempotent (re-running `ensure_session` on the same slug does not duplicate). Drive it against a copied fixture DB + ephemeral PG.
- [ ] **Step 2: RED. Step 3:** Implement a `python -m sidequest.cli.import_saves --save-dir ~/.sidequest/saves --database-url …` entry that copies each save (db+wal+shm trio, checkpoint the copy — per the save-preservation rule), exports, imports, and reports a per-save summary. **Never mutate the source DB.**
- [ ] **Step 4: GREEN. Step 5: Commit** `feat(persistence): importer CLI with copy-first dry-run safety (ADR-115)`.

- [ ] **Step 6: Operator dry-run (manual, documented, not a test):** On a **copy** of a live save (`coyote_star`), run the CLI against a scratch Postgres DB and eyeball the summary. Record the result in the PR description. Do not touch live files.

---

## TASK-GROUP F — Cutover + retirements

### Task F1: Retire the SQLite write machinery

**Files:** `sidequest/game/persistence.py`, `sidequest/game/sqlite_repository.py`, `sidequest/telemetry/watcher_hub.py`, and any remaining importers.

- [ ] **Step 1:** Delete `SAVE_WRITE_LOCK` and its now-zero remaining acquisition sites (verify zero with `rg SAVE_WRITE_LOCK sidequest/`), `_configure_connection`'s WAL/`busy_timeout` tuning, the load-path `PRAGMA wal_checkpoint(TRUNCATE)` + `.canonicalize.bak` copy, `SqliteStore.connection()`, the `SqliteSaveRepository` class + its `.store` hatch (verify no live importer needs it). Shrink `SqliteStore` to the read-only surface the importer/forensic-archive reader uses (or replace it with `corpus/save_reader.py`'s reader entirely if nothing else needs it). Keep `db_path_for_slug` if the importer uses it.
- [ ] **Step 2:** Run the full suite against ephemeral PG → green (minus the known pre-existing set). Fix any straggler. 
- [ ] **Step 3: Commit** `refactor(persistence): retire SAVE_WRITE_LOCK + WAL tuning + load-path checkpoint + .store hatch (ADR-115)`.

### Task F2: Wire pool lifecycle into app startup/shutdown

**Files:** `sidequest/server/app.py` (or wherever FastAPI lifespan/startup lives — grep `@app.on_event` / `lifespan`).

- [ ] **Step 1:** Open the pool at app startup (`db_pool.get_pool()`), close it at shutdown (`db_pool.close_pool()`). Add a startup probe that runs `SELECT 1` and **fails loud** if the DB is unreachable (no silent degrade). Fixture-driven test: the lifespan opens a usable pool.
- [ ] **Step 2: Commit** `feat(persistence): open/close the pool in the app lifespan; fail-loud startup probe (ADR-115)`.

### Task F3: Run the importer on the live saves (operator gate)

- [ ] **Step 1 (manual, documented) — descoped to the single coyote_star-mp save:** With the dev server stopped, `just pg-up` confirmed, the real `sidequest` DB migrated (`alembic upgrade head`), and `SIDEQUEST_DATABASE_URL` pointed at the real `sidequest` DB (not `sidequest_test`), run the one-shot `python -m sidequest.game.importer` (hardcoded to `~/.sidequest/saves/games/2026-05-17-coyote_star-mp/save.db`; the `import_saves` CLI and `--save-dir`/`beneath_sunden-mp`/`glenross` multi-save loop were descoped 2026-05-26). It reads the save RO+IMMUTABLE (original preserved — verify mtime/WAL unchanged after) and prints the per-table `ImportSummary`; verify the counts match (sessions 1, game_state 1, events 236, narrative_log 234, scrapbook_entries 118, turn_telemetry 59, projection_cache 706). This is a HARD GATE — do not proceed to F4 if the import fails. Record results in the PR.

### Task F4: Cutover verification + ADR/docs update

**Files:** `docs/adr/115-postgres-persistence-substrate.md` (status/amendment), the orchestrator `justfile` (ensure `just up` documents `SIDEQUEST_DATABASE_URL`), `sidequest-server/README.md` (Postgres section).

- [ ] **Step 1:** Full `just check-all` (server-check + client + daemon) against the live Postgres + ephemeral test PG.
- [ ] **Step 2:** Live smoke: `just up`, start a fresh session in a genre/world, take a few turns, confirm narration/state/scrapbook persist and a forensic timeline renders — verify the GM panel shows the turn_telemetry spans (OTEL is the lie detector). Confirm an imported save (`coyote_star`) loads and continues.
- [ ] **Step 3:** Update ADR-115 status to reflect the completed direct port; note the retired mechanisms. Update README/justfile docs.
- [ ] **Step 4: Commit** `docs(adr): ADR-115 direct port complete — Postgres live, SQLite retired to importer source`.

---

## Self-Review

**1. Spec coverage** (spec "The port (one direction, decomposed into task-groups)"):
- "Postgres infra + schema + Alembic" → TG1 (separate plan, done). ✓
- "psycopg3 pooled backend for every repository; census rides the turn transaction" → TG-A (SaveRepository + pool), TG-B (Dungeon), TG-C (Telemetry+Forensic), TG-D5 (census on tx). ✓
- "Lift every remaining consumer off raw connection/SqliteStore onto typed methods; SessionData gains a repository; no carve-outs" → TG-D1–D8 (every mapped site: tools, wss_handler, session_helpers, rest, views, emitters, scrapbook_coverage, connect, watcher_hub, dungeon borrow sites, location_resolver/view). ✓
- "Importer lands ahead of cutover so it can be dry-run; extends save_reader; dry-run on a copy" → TG-E1–E3. ✓
- "Cutover + retirements: flip backend, run importer on live saves, delete SAVE_WRITE_LOCK + WAL + ?mode=ro + connection()/.store" → TG-F1–F4. ✓
- Concurrency model (row-lock per session, MVCC reads, census on turn tx) → the `session_tx` FOR UPDATE contract (A2) + `write_telemetry` on the tx (A3/D5). ✓
- Testing rules (ephemeral PG, no SQLite dual-path, no source-text wiring tests, no content-coupled tests, importer round-trip) → all tasks use `migrated_db`/`pg_conn`, behavior/fixture assertions, round-trip in E2. ✓

**2. Placeholder scan:** Foundational/tricky pieces (pool, `session_tx`, seq assignment, `PgSaveTransaction.write_telemetry`, the dungeon boundary, importer round-trip) carry complete code. Mechanical CRUD adapter methods (A4/A5/A6/B1/C2) carry exact signatures + verbatim Postgres SQL + the source file:line to mirror — complete enough to transcribe without invention. The consumer-lift tasks (D2–D7) reference exact file:line from the codebase map. No "TODO"/"add error handling"/"similar to Task N".

**3. Type/name consistency:** `database_url()`/`MissingDatabaseUrlError` (TG1) consumed by `db_pool`. `get_pool()`/`close_pool()` consumed everywhere. `session_tx(pool, session_id)` used by every write store. `PgSaveTransaction` (events.py) is the single tx type yielded by `PgSaveRepository.transaction()` and carries `append_event`/`write_projection`/`write_telemetry`. `EventRow`/`CachedDecision`/`FilterDecision`/`NarrativeEntry`/`GameSnapshot`/`WorldSave`/`SavedSession`/`LocationPromotionRow` reused from existing modules (no new shapes except `GameRow` in sessions.py and the optional `PgLocationPromotionRow`). `resolve_session_id`/`ensure_session`/`get_game`/`init_session` defined in sessions.py and consumed by save_repository + importer + REST lift.

**Known seams / decisions flagged for the implementer (not gaps):**
- The `SaveTransaction` Protocol grows `write_telemetry`; the SQLite `SqliteSaveRepository` is NOT grown to match (it is deleted in F1, not maintained) — the live concrete is `PgSaveRepository` from D1 onward.
- `LocationPromotionRow.save_id` removal: prefer dropping it from the live type; if the importer-read path needs it, use a separate read-only row type rather than contorting the live one (A6).
- The forensic timestamp-normalization (`_NORM_EV_TS`) may be unnecessary under ISO-TEXT lexical ordering — verify against a fixture before porting it (C2).
- `tests/server/test_save_write_lock.py` asserts a lock that F1 deletes — it is rewritten in D5 to assert the structural (one-connection-per-turn) deadlock-impossibility, not kept asserting the deleted lock.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-26-postgres-migration-tg2-full-port.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration. Given the size (6 task-groups), this keeps each task's context tight.

**2. Inline Execution** — execute in this session with checkpoints.

Which approach?
