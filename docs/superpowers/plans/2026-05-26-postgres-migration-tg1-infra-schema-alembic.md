# PostgreSQL Migration — Task-Group 1: Infra + Schema + Alembic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the PostgreSQL substrate — driver/Alembic dependencies, local + CI provisioning, and one Alembic migration that creates the entire unified single-database schema (a `sessions` table plus `session_id`/`session_slug` keying across every per-session save and dungeon table).

**Architecture:** This is task-group 1 of the ADR-115 direct port (spec: `docs/superpowers/specs/2026-05-26-postgres-persistence-migration-design.md`). It builds the Postgres schema and the test harness that every later task-group reuses, but wires **no consumer onto Postgres yet** — the live store still runs SQLite through the Slice-1a `SaveRepository` until task-group 2 swaps the backend. All five task-groups land on one feature branch `feat/postgres-substrate`; the backend flips (cutover) only in task-group 5, so nothing here parks an inert milestone in `develop`. The schema is authored as raw SQL inside Alembic `op.execute(...)` blocks — **no SQLAlchemy ORM models** (Alembic brings SQLAlchemy transitively; we use it only as the migration runner and connection factory).

**Tech Stack:** Python 3.12+ (running 3.14), `uv` package manager, `psycopg[binary]` 3.x + `psycopg_pool`, `alembic`, PostgreSQL 18 (pinned major — Keith's local install is `postgresql@18`, keg-only at `/opt/homebrew/opt/postgresql@18/bin`), Homebrew + `launchd` locally, GitHub Actions `services: postgres` in CI, `pytest` (xdist `-n auto`, 30 s timeout).

---

## Context the engineer needs before starting

You are working in `sidequest-server/` (a subrepo of the `oq-1` orchestrator checkout). Key facts:

- **Backend language is Python/FastAPI** (ADR-082). The save store today is `sidequest/game/persistence.py::SqliteStore` — one SQLite `.db` file per game session at `~/.sidequest/saves/<genre>_<world>.db`.
- **Slice 1a already shipped** (`sidequest/game/repository.py` + `sidequest/game/sqlite_repository.py`): a `SaveRepository`/`SaveTransaction` Protocol and a SQLite adapter. **Do not modify those files in this task-group** — task-group 2 swaps their backend. This task-group only adds the Postgres schema + harness alongside them.
- **Subrepo branching (load-bearing):** `sidequest-server` is its own git repo on the `develop` default branch. Create `feat/postgres-substrate` in `sidequest-server` **before** writing any code, or commits land on `develop`. (See the orchestrator note: subrepo branches are independent of the orchestrator.)
- **No SQLite dual-path in tests.** Per the spec, the test substrate is ephemeral *real* Postgres. There is currently **no** `.github/workflows/` in `sidequest-server` — you are creating the first CI workflow.
- **CLAUDE.md rules that bite here:** No Silent Fallbacks (a missing DB URL must raise, never default silently); Every Test Suite Needs a Wiring Test; No Source-Text Wiring Tests (assert behavior/schema introspection, never `read_text()` of source); No Stubbing.
- **The complete current SQLite schema you are porting** lives in two string constants:
  - Save domain: `sidequest/game/persistence.py::SCHEMA_SQL` (tables `session_meta`, `game_state`, `narrative_log`, `lore_fragments`, `scenario_archive`, `scrapbook_entries`, `games`, `events`, `projection_cache`, `world_save`, `turn_telemetry`, `location_promotions`).
  - Dungeon domain: `sidequest/dungeon/persistence.py::DUNGEON_SCHEMA_SQL` (tables `dungeon_map`, `dungeon_edge`, `dungeon_frontier`, `dungeon_mutation_overlay`, `dungeon_complication_ledger`, `dungeon_meta`).

### Schema translation decisions (locked for this migration)

These decisions are baked into Task 5's migration and you must follow them exactly so later task-groups and the importer line up:

1. **`sessions` table absorbs `session_meta` + `games`.** Both are session-level singletons keyed by the save slug. The new `sessions` table carries the integer surrogate `session_id BIGINT GENERATED ALWAYS AS IDENTITY` PK and the unique natural key `session_slug TEXT UNIQUE`, plus the union of their columns (`genre_slug`, `world_slug`, `mode`, `claude_session_id`, `created_at`, `last_played`, `schema_version`).
2. **Every per-session table gains `session_id BIGINT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE`.**
3. **`events` keeps per-session append-only `seq`:** PK `(session_id, seq)` where `seq BIGINT NOT NULL`. **`seq` is assigned by the repository** (task-group 2) as `MAX(seq)+1` within the session under the row lock — it is **not** a global IDENTITY (a global identity would not be per-session monotonic). This migration only creates the column + composite PK.
4. **`projection_cache` FK follows the composite events PK:** columns `(session_id, event_seq, player_id)`, PK `(session_id, event_seq, player_id)`, `FOREIGN KEY (session_id, event_seq) REFERENCES events(session_id, seq)`.
5. **Timestamps stay `TEXT` (ISO-8601), not `TIMESTAMPTZ`.** The Slice-1a repository and every consumer read/write ISO strings (`datetime.now(tz=UTC).isoformat()`). Keeping `TEXT` means task-groups 2/3 do not have to touch a single date-handling call site, honoring the spec's "does not change game logic." (The one exception: `sessions.created_at`/`last_played` also stay `TEXT` for the same reason.)
6. **Booleans stay `INTEGER` (0/1).** Columns `projection_cache.include`, `dungeon_edge.hidden`, `dungeon_edge.shortcut` are written as `1`/`0` today; `INTEGER` avoids a bool-adapter churn across consumers.
7. **`BLOB` → `BYTEA`** (`dungeon_map.mask`). **`REAL` → `DOUBLE PRECISION`** (`*.depth_score`, `*.spawn_depth_score`, `*.started_at_depth_score`).
8. **Global surrogate `AUTOINCREMENT` PKs that carry no cross-session meaning become global `BIGINT GENERATED ALWAYS AS IDENTITY` + a `session_id` FK column** (`narrative_log.id`, `scrapbook_entries.id`, `turn_telemetry.seq`, `dungeon_edge.edge_id`, `dungeon_mutation_overlay.mutation_id`). Queries filter by `session_id`; the surrogate stays globally unique, which is fine.
9. **`location_promotions.save_id TEXT` is replaced by `session_id`** (the slug now lives only on `sessions`). PK `(session_id, region_id, entity_id)`.
10. **`scenario_archive` disambiguation:** the table's existing `session_id TEXT PRIMARY KEY` is the *scenario clue-graph* session id, **not** the save session. Rename that column to `scenario_session_id TEXT` and key the table by the save `session_id BIGINT` PK (one scenario archive row per save). This avoids two different `session_id`s in one table.
11. **`session_meta.schema_version` is preserved on `sessions`** but Alembic now owns DDL versioning; `schema_version` is retained only as importer-fidelity data.

> Note on `psycopg` vs SQLAlchemy URL schemes: Alembic uses a SQLAlchemy `Engine`, so its URL is `postgresql+psycopg://...`. The runtime pool (task-group 2) will use a plain psycopg conninfo `postgresql://...`. This task-group introduces one resolver (`sidequest/game/db_config.py::database_url`) returning the plain conninfo; the Alembic `env.py` derives the `+psycopg` form from it. Single source, no divergence.

---

## File Structure

Files created or modified in this task-group:

- **Create** `sidequest/game/db_config.py` — `database_url()` resolver: reads `SIDEQUEST_DATABASE_URL`, fail-loud if unset. One consumer now (Alembic `env.py`); the pool consumes it in task-group 2.
- **Create** `alembic.ini` — Alembic config (script location, no hardcoded URL — `env.py` resolves it).
- **Create** `alembic/env.py` — migration runner; resolves the URL via `db_config.database_url()`, runs migrations online with raw SQL (no autogenerate, no target metadata).
- **Create** `alembic/script.py.mako` — standard Alembic revision template.
- **Create** `alembic/versions/0001_initial_unified_schema.py` — the one migration that creates the full unified schema (all 17 tables + indexes + FKs).
- **Create** `tests/persistence/__init__.py` and `tests/persistence/conftest.py` — the reusable ephemeral-Postgres fixtures (`pg_admin_conninfo`, `migrated_db`).
- **Create** `tests/persistence/test_initial_migration.py` — the migration-applies + schema-shape + wiring test.
- **Create** `.github/workflows/server-ci.yml` — first server CI workflow with `services: postgres:16`, running lint + the suite (including the Postgres-backed migration test).
- **Modify** `pyproject.toml` — add `psycopg[binary]`, `psycopg-pool`, `alembic` to deps; add `alembic` to dev tooling is not needed (it's a runtime dep for migrations at deploy).
- **Modify** `justfile` (orchestrator root, `/Users/slabgorb/Projects/oq-1/justfile`) — add `pg-up` / `pg-status` recipes (provisioning convenience). *(If the engineer prefers, server-local docs suffice; the recipe is the documented path.)*
- **Modify** `sidequest-server/README.md` — a short "Local Postgres for development" section (provisioning steps). *(Only if a README exists; otherwise skip — do not create a README solely for this.)*

---

## Task 1: Create the feature branch and add dependencies

**Files:**
- Modify: `sidequest-server/pyproject.toml:5-17` (the `dependencies` array)

- [ ] **Step 1: Create the subrepo feature branch**

Run (from the orchestrator root):
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git checkout develop && git pull --ff-only && git checkout -b feat/postgres-substrate
```
Expected: `Switched to a new branch 'feat/postgres-substrate'`.

- [ ] **Step 2: Add the runtime dependencies**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv add "psycopg[binary]>=3.2" "psycopg-pool>=3.2" "alembic>=1.13"
```
Expected: `pyproject.toml` `[project].dependencies` now lists `psycopg[binary]`, `psycopg-pool`, `alembic`; `uv.lock` updated; the three packages install.

- [ ] **Step 3: Verify the imports resolve**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run python -c "import psycopg, psycopg_pool, alembic; print(psycopg.__version__, alembic.__version__)"
```
Expected: prints two version strings, no `ModuleNotFoundError`.

> If you hit `ModuleNotFoundError` despite a successful `uv sync`, check `head -1 .venv/bin/python` — a stale shebang pointing at another checkout's venv is a known failure; fix with `rm -rf .venv && uv sync --all-extras`.

- [ ] **Step 4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git add pyproject.toml uv.lock && git commit -m "build(persistence): add psycopg3 + psycopg-pool + alembic (ADR-115 TG1)"
```

---

## Task 2: Local Postgres provisioning + the URL resolver

**Files:**
- Create: `sidequest-server/sidequest/game/db_config.py`
- Test: `sidequest-server/tests/persistence/test_db_config.py`
- Modify: `/Users/slabgorb/Projects/oq-1/justfile` (add `pg-up`, `pg-status`)

- [ ] **Step 1: Write the failing test for the URL resolver**

Create `sidequest-server/tests/persistence/__init__.py` (empty file), then create `sidequest-server/tests/persistence/test_db_config.py`:

```python
"""db_config.database_url resolver — fail-loud, no silent default (ADR-115 TG1)."""

from __future__ import annotations

import pytest

from sidequest.game.db_config import MissingDatabaseUrlError, alembic_url, database_url


def test_database_url_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_DATABASE_URL", "postgresql://u@localhost:5432/sq")
    assert database_url() == "postgresql://u@localhost:5432/sq"


def test_database_url_unset_fails_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDEQUEST_DATABASE_URL", raising=False)
    with pytest.raises(MissingDatabaseUrlError):
        database_url()


def test_alembic_url_adds_psycopg_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_DATABASE_URL", "postgresql://u@localhost:5432/sq")
    assert alembic_url() == "postgresql+psycopg://u@localhost:5432/sq"


def test_alembic_url_idempotent_if_already_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_DATABASE_URL", "postgresql+psycopg://u@localhost/sq")
    assert alembic_url() == "postgresql+psycopg://u@localhost/sq"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/persistence/test_db_config.py -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.game.db_config'`.

- [ ] **Step 3: Implement the resolver**

Create `sidequest-server/sidequest/game/db_config.py`:

```python
"""Database URL resolution for the Postgres substrate (ADR-115).

Single source of the connection string. The runtime pool (task-group 2)
and the Alembic migration runner both resolve through here so the URL is
never defined twice. No Silent Fallbacks: an unset URL raises rather than
defaulting to a localhost guess that masks a misconfigured deploy.
"""

from __future__ import annotations

import os

_ENV_VAR = "SIDEQUEST_DATABASE_URL"
_PLAIN_SCHEME = "postgresql://"
_PSYCOPG_SCHEME = "postgresql+psycopg://"


class MissingDatabaseUrlError(RuntimeError):
    """Raised when SIDEQUEST_DATABASE_URL is required but unset."""


def database_url() -> str:
    """Return the psycopg conninfo URL from the environment.

    Raises ``MissingDatabaseUrlError`` if unset (fail loud — never guess a
    localhost default that hides a deploy misconfiguration).
    """
    url = os.environ.get(_ENV_VAR)
    if not url:
        raise MissingDatabaseUrlError(
            f"{_ENV_VAR} is not set. The Postgres substrate requires an explicit "
            f"connection URL (e.g. postgresql://USER@localhost:5432/sidequest). "
            f"No silent localhost default (ADR-115 / No Silent Fallbacks)."
        )
    return url


def alembic_url() -> str:
    """The SQLAlchemy/Alembic form of the URL (``postgresql+psycopg://``).

    Alembic uses a SQLAlchemy Engine, which selects the driver from the URL
    scheme; the runtime psycopg pool uses the plain ``postgresql://`` form.
    """
    url = database_url()
    if url.startswith(_PSYCOPG_SCHEME):
        return url
    if url.startswith(_PLAIN_SCHEME):
        return _PSYCOPG_SCHEME + url[len(_PLAIN_SCHEME) :]
    return url
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/persistence/test_db_config.py -q
```
Expected: PASS (4 passed).

- [ ] **Step 5: Add the provisioning just recipes**

In `/Users/slabgorb/Projects/oq-1/justfile`, add these recipes (match the file's existing recipe style — bare recipe name + indented commands):

```just
# Postgres substrate (ADR-115) — local dev provisioning (Homebrew + launchd)
# postgresql@18 is keg-only, so its bin dir is not on PATH — reference it explicitly.
pg-up:
    brew install postgresql@18
    brew services start postgresql@18
    /opt/homebrew/opt/postgresql@18/bin/createdb sidequest 2>/dev/null || true
    /opt/homebrew/opt/postgresql@18/bin/createdb sidequest_test 2>/dev/null || true
    @echo "Postgres 18 running. Set SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest"
    @echo "Tests use SIDEQUEST_TEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test"

pg-status:
    brew services info postgresql@18
```

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git add sidequest/game/db_config.py tests/persistence/__init__.py tests/persistence/test_db_config.py && git -C /Users/slabgorb/Projects/oq-1 add justfile && git commit -m "feat(persistence): SIDEQUEST_DATABASE_URL resolver + brew/launchd provisioning recipes (ADR-115 TG1)"
```

> Note: the `justfile` lives in the orchestrator repo (`oq-1`), a different git repo than `sidequest-server`. The compound commit above stages files in both working trees but commits in `sidequest-server`. Commit the orchestrator change separately: `cd /Users/slabgorb/Projects/oq-1 && git add justfile && git commit -m "build(just): pg-up/pg-status recipes for the Postgres substrate (ADR-115)"`.

---

## Task 3: Alembic scaffolding (config, env, template)

**Files:**
- Create: `sidequest-server/alembic.ini`
- Create: `sidequest-server/alembic/env.py`
- Create: `sidequest-server/alembic/script.py.mako`
- Create: `sidequest-server/alembic/versions/` (directory, add a `.gitkeep` so the empty dir is tracked until Task 5 fills it)

- [ ] **Step 1: Create `alembic.ini`**

Create `sidequest-server/alembic.ini`:

```ini
# Alembic config for the SideQuest Postgres substrate (ADR-115).
# The DB URL is resolved at runtime in alembic/env.py via
# sidequest.game.db_config.alembic_url() — intentionally NOT set here so
# there is one source of the connection string and no secret in the repo.

[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Create `alembic/env.py`**

Create `sidequest-server/alembic/env.py`:

```python
"""Alembic migration environment (ADR-115).

Resolves the connection URL from sidequest.game.db_config (single source),
runs migrations online against a real Postgres. We author raw SQL in each
revision via op.execute(...); there is no SQLAlchemy model metadata and no
autogenerate, so target_metadata stays None.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from sidequest.game.db_config import alembic_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# A URL set programmatically (tests pass one via set_main_option) wins;
# otherwise resolve from the environment. No silent localhost default.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", alembic_url())

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Create `alembic/script.py.mako`**

Create `sidequest-server/alembic/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 4: Track the empty versions directory**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && mkdir -p alembic/versions && touch alembic/versions/.gitkeep
```

- [ ] **Step 5: Verify Alembic loads its config (offline check, no DB needed)**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && SIDEQUEST_DATABASE_URL=postgresql://u@localhost/x uv run alembic history
```
Expected: exits 0 with no revisions listed (empty history) and no traceback. This proves `alembic.ini` + `env.py` import cleanly and the URL resolver is wired.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git add alembic.ini alembic/env.py alembic/script.py.mako alembic/versions/.gitkeep && git commit -m "feat(persistence): alembic scaffolding wired to db_config URL resolver (ADR-115 TG1)"
```

---

## Task 4: The ephemeral-Postgres test harness

This task builds the reusable fixtures every later task-group's Postgres test depends on: a session-scoped fixture that creates a uniquely-named throwaway database, runs `alembic upgrade head` into it, yields its conninfo, and drops it on teardown. Under xdist (`-n auto`) each worker gets its own database name, so parallel workers never collide.

**Files:**
- Create: `sidequest-server/tests/persistence/conftest.py`

- [ ] **Step 1: Implement the fixtures**

Create `sidequest-server/tests/persistence/conftest.py`:

```python
"""Ephemeral real-Postgres fixtures for the persistence suite (ADR-115).

Strategy: a session-scoped fixture creates a uniquely-named database
(per pytest-xdist worker), runs `alembic upgrade head` into it, yields its
conninfo URL, and DROPs it on teardown. No SQLite dual-path. If
SIDEQUEST_TEST_DATABASE_URL is unset, the suite SKIPS with a loud reason
(local devs run `just pg-up`; CI sets it from `services: postgres`).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config

_ADMIN_ENV = "SIDEQUEST_TEST_DATABASE_URL"


def _admin_conninfo() -> str:
    url = os.environ.get(_ADMIN_ENV)
    if not url:
        pytest.skip(
            f"{_ADMIN_ENV} unset — start local Postgres with `just pg-up` and export "
            f"{_ADMIN_ENV}=postgresql://$USER@localhost:5432/sidequest_test, or run in CI."
        )
    return url


def _swap_dbname(conninfo: str, dbname: str) -> str:
    """Return ``conninfo`` with its path (database name) replaced by ``dbname``."""
    head, _, _tail = conninfo.partition("?")
    base, _slash, _olddb = head.rpartition("/")
    rebuilt = f"{base}/{dbname}"
    if _tail:
        rebuilt = f"{rebuilt}?{_tail}"
    return rebuilt


@pytest.fixture(scope="session")
def migrated_db(worker_id: str) -> Iterator[str]:
    """A freshly-migrated throwaway Postgres database; conninfo URL yielded.

    ``worker_id`` is injected by pytest-xdist ("gw0", "gw1", ... or "master"
    when serial); it namespaces the db so parallel workers do not collide.
    """
    admin = _admin_conninfo()
    db_name = f"sq_test_{worker_id}_{uuid.uuid4().hex[:8]}"

    # CREATE/DROP DATABASE cannot run inside a transaction block.
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{db_name}"')

    target = _swap_dbname(admin, db_name)
    try:
        cfg = Config("alembic.ini")
        cfg.set_main_option("script_location", "alembic")
        # Alembic uses the +psycopg SQLAlchemy form of the target URL.
        cfg.set_main_option(
            "sqlalchemy.url",
            target if target.startswith("postgresql+psycopg://")
            else target.replace("postgresql://", "postgresql+psycopg://", 1),
        )
        command.upgrade(cfg, "head")
        yield target
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (db_name,),
            )
            conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')


@pytest.fixture
def pg_conn(migrated_db: str) -> Iterator[psycopg.Connection]:
    """A connection to the migrated db, wrapped in a transaction that always
    rolls back — per-test isolation without re-running migrations."""
    with psycopg.connect(migrated_db) as conn:
        try:
            yield conn
        finally:
            conn.rollback()
```

- [ ] **Step 2: Verify the harness imports without a DB (collection-only)**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/persistence/conftest.py --co -q
```
Expected: collection succeeds (0 tests collected from the conftest itself), no import error. (`psycopg`/`alembic` import cleanly; the fixtures are lazy.)

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git add tests/persistence/conftest.py && git commit -m "test(persistence): ephemeral-Postgres fixtures (per-worker db + rollback isolation) (ADR-115 TG1)"
```

---

## Task 5: The initial unified-schema migration

This is the core deliverable: one Alembic revision that builds the entire unified single-database schema following the translation decisions above.

**Files:**
- Create: `sidequest-server/alembic/versions/0001_initial_unified_schema.py`
- Test: `sidequest-server/tests/persistence/test_initial_migration.py`

- [ ] **Step 1: Write the failing schema-shape test**

Create `sidequest-server/tests/persistence/test_initial_migration.py`:

```python
"""Initial unified schema migration applies and has the ADR-115 shape.

Behavior/introspection assertions only — never a source-text grep
(CLAUDE.md: No Source-Text Wiring Tests). `migrated_db` already ran
`alembic upgrade head`, so reaching it at all proves the migration applied.
"""

from __future__ import annotations

import psycopg
import pytest

ALL_TABLES = {
    "sessions",
    "game_state",
    "narrative_log",
    "lore_fragments",
    "scenario_archive",
    "scrapbook_entries",
    "events",
    "projection_cache",
    "world_save",
    "turn_telemetry",
    "location_promotions",
    "dungeon_map",
    "dungeon_edge",
    "dungeon_frontier",
    "dungeon_mutation_overlay",
    "dungeon_complication_ledger",
    "dungeon_meta",
}

PER_SESSION_TABLES = ALL_TABLES - {"sessions"}


def _columns(conn: psycopg.Connection, table: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def test_all_tables_exist(pg_conn: psycopg.Connection) -> None:
    rows = pg_conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    present = {r[0] for r in rows}
    assert ALL_TABLES <= present, f"missing tables: {ALL_TABLES - present}"


def test_sessions_has_surrogate_and_natural_key(pg_conn: psycopg.Connection) -> None:
    cols = _columns(pg_conn, "sessions")
    assert cols["session_id"] == "bigint"
    assert "session_slug" in cols
    # session_slug is UNIQUE
    uniq = pg_conn.execute(
        """
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'sessions' AND tc.constraint_type = 'UNIQUE'
          AND ccu.column_name = 'session_slug'
        """
    ).fetchone()
    assert uniq is not None


@pytest.mark.parametrize("table", sorted(PER_SESSION_TABLES))
def test_every_per_session_table_has_session_id_fk(
    pg_conn: psycopg.Connection, table: str
) -> None:
    cols = _columns(pg_conn, table)
    assert cols.get("session_id") == "bigint", f"{table} missing session_id bigint"
    fk = pg_conn.execute(
        """
        SELECT ccu.table_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
          AND kcu.column_name = 'session_id'
        """,
        (table,),
    ).fetchone()
    assert fk is not None and fk[0] == "sessions", f"{table}.session_id must FK -> sessions"


def test_events_pk_is_session_id_seq(pg_conn: psycopg.Connection) -> None:
    pk_cols = pg_conn.execute(
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'events' AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
        """
    ).fetchall()
    assert [r[0] for r in pk_cols] == ["session_id", "seq"]


def test_projection_cache_fk_targets_composite_events_pk(pg_conn: psycopg.Connection) -> None:
    # Inserting a projection row for a non-existent (session_id, event_seq)
    # must be rejected by the composite FK.
    sid = pg_conn.execute(
        "INSERT INTO sessions (session_slug, genre_slug, world_slug, mode, created_at, last_played) "
        "VALUES ('t', 'g', 'w', 'solo', '2026-01-01', '2026-01-01') RETURNING session_id"
    ).fetchone()[0]
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        pg_conn.execute(
            "INSERT INTO projection_cache (session_id, event_seq, player_id, include, payload_json) "
            "VALUES (%s, 999, 'p1', 1, NULL)",
            (sid,),
        )


def test_cascade_delete_removes_child_rows(pg_conn: psycopg.Connection) -> None:
    sid = pg_conn.execute(
        "INSERT INTO sessions (session_slug, genre_slug, world_slug, mode, created_at, last_played) "
        "VALUES ('c', 'g', 'w', 'solo', '2026-01-01', '2026-01-01') RETURNING session_id"
    ).fetchone()[0]
    pg_conn.execute(
        "INSERT INTO events (session_id, seq, kind, payload_json, created_at) "
        "VALUES (%s, 1, 'k', '{}', '2026-01-01')",
        (sid,),
    )
    pg_conn.execute("DELETE FROM sessions WHERE session_id = %s", (sid,))
    remaining = pg_conn.execute(
        "SELECT count(*) FROM events WHERE session_id = %s", (sid,)
    ).fetchone()[0]
    assert remaining == 0


def test_mask_is_bytea(pg_conn: psycopg.Connection) -> None:
    assert _columns(pg_conn, "dungeon_map")["mask"] == "bytea"
```

- [ ] **Step 2: Run the test to verify it fails**

Run (requires a local Postgres; see Task 2 `just pg-up`):
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && SIDEQUEST_TEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run pytest tests/persistence/test_initial_migration.py -q
```
Expected: FAIL — `alembic upgrade head` finds no revisions, so the `migrated_db` fixture creates an empty database and `test_all_tables_exist` fails on the missing tables (or the upgrade is a no-op). The failure confirms the migration does not exist yet.

- [ ] **Step 3: Write the migration**

Create `sidequest-server/alembic/versions/0001_initial_unified_schema.py`:

```python
"""initial unified Postgres schema (ADR-115 direct port)

Revision ID: 0001
Revises:
Create Date: 2026-05-26

Ports the per-session SQLite schema (game/persistence.py SCHEMA_SQL +
dungeon/persistence.py DUNGEON_SCHEMA_SQL) to one unified Postgres database:
a `sessions` table (integer surrogate PK + unique slug natural key,
absorbing session_meta + games) and a session_id FK on every per-session
table. Raw SQL via op.execute — no ORM models. See the plan's "Schema
translation decisions" for every type/key choice.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE sessions (
            session_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_slug      TEXT NOT NULL UNIQUE,
            mode              TEXT NOT NULL CHECK (mode IN ('solo', 'multiplayer')),
            genre_slug        TEXT NOT NULL,
            world_slug        TEXT NOT NULL,
            claude_session_id TEXT,
            schema_version    INTEGER NOT NULL DEFAULT 1,
            created_at        TEXT NOT NULL,
            last_played       TEXT NOT NULL
        );

        CREATE TABLE game_state (
            session_id    BIGINT NOT NULL PRIMARY KEY
                          REFERENCES sessions(session_id) ON DELETE CASCADE,
            snapshot_json TEXT NOT NULL,
            saved_at      TEXT NOT NULL
        );

        CREATE TABLE world_save (
            session_id   BIGINT NOT NULL PRIMARY KEY
                         REFERENCES sessions(session_id) ON DELETE CASCADE,
            payload_json TEXT NOT NULL,
            saved_at     TEXT NOT NULL
        );

        CREATE TABLE narrative_log (
            id           BIGINT GENERATED ALWAYS AS IDENTITY,
            session_id   BIGINT NOT NULL
                         REFERENCES sessions(session_id) ON DELETE CASCADE,
            round_number INTEGER NOT NULL,
            author       TEXT NOT NULL,
            content      TEXT NOT NULL,
            tags         TEXT,
            created_at   TEXT NOT NULL,
            PRIMARY KEY (session_id, id)
        );
        CREATE INDEX idx_narrative_round ON narrative_log (session_id, round_number);
        CREATE INDEX idx_narrative_author ON narrative_log (session_id, author);

        CREATE TABLE lore_fragments (
            session_id    BIGINT NOT NULL
                          REFERENCES sessions(session_id) ON DELETE CASCADE,
            id            TEXT NOT NULL,
            category      TEXT NOT NULL,
            content       TEXT NOT NULL,
            source        TEXT NOT NULL,
            turn_created  INTEGER,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at    TEXT NOT NULL,
            PRIMARY KEY (session_id, id)
        );
        CREATE INDEX idx_lore_category ON lore_fragments (session_id, category);

        CREATE TABLE scenario_archive (
            session_id          BIGINT NOT NULL PRIMARY KEY
                                REFERENCES sessions(session_id) ON DELETE CASCADE,
            scenario_session_id TEXT,
            scenario_json       TEXT NOT NULL,
            saved_at            TEXT NOT NULL
        );

        CREATE TABLE scrapbook_entries (
            id                BIGINT GENERATED ALWAYS AS IDENTITY,
            session_id        BIGINT NOT NULL
                              REFERENCES sessions(session_id) ON DELETE CASCADE,
            turn_id           INTEGER NOT NULL,
            scene_title       TEXT,
            scene_type        TEXT,
            location          TEXT NOT NULL,
            image_url         TEXT,
            narrative_excerpt TEXT NOT NULL,
            world_facts       TEXT NOT NULL DEFAULT '[]',
            npcs_present      TEXT NOT NULL DEFAULT '[]',
            render_status     TEXT NOT NULL DEFAULT 'rendered',
            created_at        TEXT NOT NULL,
            PRIMARY KEY (session_id, id)
        );
        CREATE INDEX idx_scrapbook_turn ON scrapbook_entries (session_id, turn_id);

        CREATE TABLE events (
            session_id   BIGINT NOT NULL
                         REFERENCES sessions(session_id) ON DELETE CASCADE,
            seq          BIGINT NOT NULL,
            kind         TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            PRIMARY KEY (session_id, seq)
        );

        CREATE TABLE projection_cache (
            session_id   BIGINT NOT NULL,
            event_seq    BIGINT NOT NULL,
            player_id    TEXT NOT NULL,
            include      INTEGER NOT NULL,
            payload_json TEXT,
            PRIMARY KEY (session_id, event_seq, player_id),
            FOREIGN KEY (session_id, event_seq)
                REFERENCES events(session_id, seq) ON DELETE CASCADE
        );
        CREATE INDEX idx_projection_cache_player
            ON projection_cache (session_id, player_id, event_seq);

        CREATE TABLE turn_telemetry (
            seq          BIGINT GENERATED ALWAYS AS IDENTITY,
            session_id   BIGINT NOT NULL
                         REFERENCES sessions(session_id) ON DELETE CASCADE,
            event_seq    BIGINT,
            round        INTEGER,
            ts           TEXT NOT NULL,
            component    TEXT NOT NULL,
            event_type   TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (session_id, seq)
        );
        CREATE INDEX idx_turn_telemetry_round ON turn_telemetry (session_id, round);
        CREATE INDEX idx_turn_telemetry_event_seq ON turn_telemetry (session_id, event_seq);

        CREATE TABLE location_promotions (
            session_id        BIGINT NOT NULL
                              REFERENCES sessions(session_id) ON DELETE CASCADE,
            region_id         TEXT NOT NULL,
            entity_id         TEXT NOT NULL,
            provenance        TEXT NOT NULL,
            label             TEXT NOT NULL,
            promoted_at_turn  INTEGER NOT NULL,
            promoted_canon    TEXT NOT NULL,
            new_tier          TEXT NOT NULL DEFAULT 'yes_and',
            new_binding_kind  TEXT,
            new_binding_ref   TEXT,
            PRIMARY KEY (session_id, region_id, entity_id)
        );
        CREATE INDEX idx_location_promotions_region
            ON location_promotions (session_id, region_id);

        CREATE TABLE dungeon_map (
            session_id        BIGINT NOT NULL
                              REFERENCES sessions(session_id) ON DELETE CASCADE,
            region_id         TEXT NOT NULL,
            expansion_id      INTEGER NOT NULL,
            depth_score       DOUBLE PRECISION,
            generator_version TEXT NOT NULL,
            payload           TEXT NOT NULL,
            mask              BYTEA,
            created_at        TEXT NOT NULL,
            PRIMARY KEY (session_id, region_id)
        );
        CREATE INDEX idx_dungeon_map_expansion ON dungeon_map (session_id, expansion_id);
        CREATE INDEX idx_dungeon_map_depth ON dungeon_map (session_id, depth_score);

        CREATE TABLE dungeon_edge (
            edge_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_id   BIGINT NOT NULL
                         REFERENCES sessions(session_id) ON DELETE CASCADE,
            expansion_id INTEGER NOT NULL,
            a            TEXT NOT NULL,
            b            TEXT NOT NULL,
            kind         TEXT NOT NULL,
            hidden       INTEGER NOT NULL,
            shortcut     INTEGER NOT NULL,
            payload      TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );
        CREATE INDEX idx_dungeon_edge_a ON dungeon_edge (session_id, a);
        CREATE INDEX idx_dungeon_edge_b ON dungeon_edge (session_id, b);
        CREATE INDEX idx_dungeon_edge_expansion ON dungeon_edge (session_id, expansion_id);

        CREATE TABLE dungeon_frontier (
            session_id        BIGINT NOT NULL
                              REFERENCES sessions(session_id) ON DELETE CASCADE,
            frontier_edge_id  TEXT NOT NULL,
            from_region_id    TEXT NOT NULL,
            heading           TEXT NOT NULL,
            spawn_depth_score DOUBLE PRECISION NOT NULL,
            payload           TEXT NOT NULL,
            created_at        TEXT NOT NULL,
            PRIMARY KEY (session_id, frontier_edge_id)
        );
        CREATE INDEX idx_dungeon_frontier_from
            ON dungeon_frontier (session_id, from_region_id);

        CREATE TABLE dungeon_mutation_overlay (
            mutation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_id  BIGINT NOT NULL
                        REFERENCES sessions(session_id) ON DELETE CASCADE,
            region_id   TEXT NOT NULL,
            kind        TEXT NOT NULL,
            payload     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
        CREATE INDEX idx_dungeon_mutation_region
            ON dungeon_mutation_overlay (session_id, region_id);

        CREATE TABLE dungeon_complication_ledger (
            session_id            BIGINT NOT NULL
                                  REFERENCES sessions(session_id) ON DELETE CASCADE,
            thread_id             TEXT NOT NULL,
            origin_region_id      TEXT NOT NULL,
            kind                  TEXT NOT NULL,
            status                TEXT NOT NULL,
            started_at_depth_score DOUBLE PRECISION NOT NULL,
            payload               TEXT NOT NULL,
            created_at            TEXT NOT NULL,
            resolved_at           TEXT,
            PRIMARY KEY (session_id, thread_id)
        );
        CREATE INDEX idx_dungeon_ledger_status
            ON dungeon_complication_ledger (session_id, status);
        CREATE INDEX idx_dungeon_ledger_origin
            ON dungeon_complication_ledger (session_id, origin_region_id);

        CREATE TABLE dungeon_meta (
            session_id    BIGINT NOT NULL PRIMARY KEY
                          REFERENCES sessions(session_id) ON DELETE CASCADE,
            campaign_seed BIGINT NOT NULL,
            created_at    TEXT NOT NULL
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS dungeon_meta;
        DROP TABLE IF EXISTS dungeon_complication_ledger;
        DROP TABLE IF EXISTS dungeon_mutation_overlay;
        DROP TABLE IF EXISTS dungeon_frontier;
        DROP TABLE IF EXISTS dungeon_edge;
        DROP TABLE IF EXISTS dungeon_map;
        DROP TABLE IF EXISTS location_promotions;
        DROP TABLE IF EXISTS turn_telemetry;
        DROP TABLE IF EXISTS projection_cache;
        DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS scrapbook_entries;
        DROP TABLE IF EXISTS scenario_archive;
        DROP TABLE IF EXISTS lore_fragments;
        DROP TABLE IF EXISTS narrative_log;
        DROP TABLE IF EXISTS world_save;
        DROP TABLE IF EXISTS game_state;
        DROP TABLE IF EXISTS sessions;
        """
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && SIDEQUEST_TEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run pytest tests/persistence/test_initial_migration.py -q
```
Expected: PASS (all table/key/FK/cascade/bytea assertions green).

- [ ] **Step 5: Verify the downgrade is reversible (round-trip)**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && SIDEQUEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run alembic upgrade head && SIDEQUEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run alembic downgrade base && SIDEQUEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run alembic upgrade head
```
Expected: each command exits 0; `upgrade → downgrade → upgrade` leaves a clean schema with no error (proves `downgrade()` drops in FK-safe order). Then reset for a clean test db: `SIDEQUEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run alembic downgrade base`.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git add alembic/versions/0001_initial_unified_schema.py tests/persistence/test_initial_migration.py && git rm --cached alembic/versions/.gitkeep && git commit -m "feat(persistence): initial unified Postgres schema migration + shape test (ADR-115 TG1)"
```

---

## Task 6: CI workflow with services: postgres

This adds the first `sidequest-server` CI workflow so the Postgres-backed suite runs on every push — the wiring guarantee that the migration test actually executes in CI (not just locally).

**Files:**
- Create: `sidequest-server/.github/workflows/server-ci.yml`

- [ ] **Step 1: Write the workflow**

Create `sidequest-server/.github/workflows/server-ci.yml`:

```yaml
name: server-ci

on:
  push:
    branches: [develop, "feat/**"]
  pull_request:
    branches: [develop]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_USER: sidequest
          POSTGRES_PASSWORD: sidequest
          POSTGRES_DB: sidequest_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U sidequest"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      SIDEQUEST_TEST_DATABASE_URL: postgresql://sidequest:sidequest@localhost:5432/sidequest_test
      SIDEQUEST_DATABASE_URL: postgresql://sidequest:sidequest@localhost:5432/sidequest_test
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Sync dependencies
        run: uv sync --all-extras
      - name: Lint
        run: uv run ruff check .
      - name: Test
        run: uv run pytest -q
```

- [ ] **Step 2: Validate the workflow YAML parses**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/server-ci.yml').read_text()); print('ok')"
```
Expected: prints `ok` (valid YAML).

- [ ] **Step 3: Confirm the migration test is discovered by the same command CI runs**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/persistence/ --co -q | tail -20
```
Expected: lists `tests/persistence/test_db_config.py` and `tests/persistence/test_initial_migration.py` cases — proving CI's `uv run pytest -q` will collect them.

- [ ] **Step 4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git add .github/workflows/server-ci.yml && git commit -m "ci(server): first workflow — services: postgres:18, lint + suite (ADR-115 TG1)"
```

---

## Task 7: Full-suite regression gate

The whole point of keeping SQLite live this task-group is that nothing else breaks. Confirm the existing suite still passes (the SQLite store is untouched), with the new Postgres tests added.

**Files:** none (verification only)

- [ ] **Step 1: Run the full unit suite with Postgres available**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && SIDEQUEST_TEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" SIDEQUEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test" uv run pytest -q 2>&1 | tail -25
```
Expected: the full suite passes; the `tests/persistence/` tests run (not skipped). Pre-existing env-coupled failures (namegen-audit, pack-validator, dogfight-smoke, prompt-compaction live-tree tests) may show — confirm any failure is pre-existing by checking it fails identically on `develop`, not introduced here.

- [ ] **Step 2: Run lint + format**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run ruff check . && uv run ruff format --check .
```
Expected: clean (or only pre-existing format-debt files flagged — do not reformat out-of-scope files).

- [ ] **Step 3: Confirm SQLite store is genuinely untouched**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git diff develop --stat -- sidequest/game/persistence.py sidequest/game/repository.py sidequest/game/sqlite_repository.py sidequest/dungeon/persistence.py
```
Expected: **empty output** — this task-group adds the Postgres substrate alongside SQLite without modifying any live store file. (If non-empty, you went out of scope; revert those edits — the backend swap is task-group 2.)

---

## Self-Review

**1. Spec coverage (task-group 1 = spec's "1. Postgres infra + schema + Alembic"):**
- "Local brew/launchd (pinned major)" → Task 2 `just pg-up` (postgresql@18). ✓
- "CI services: postgres of the same major" → Task 6 (`postgres:18`). ✓
- "Alembic init" → Task 3 (config/env/template) + Task 5 (initial revision). ✓
- "the `sessions` table + `session_id`/`session_slug` keying across every per-session table" → Task 5 migration + Task 5 introspection test covering all 16 per-session tables. ✓
- "sync `psycopg3` + `psycopg_pool`" dependency present → Task 1. (The pool *usage* is task-group 2.) ✓
- Spec testing rules: ephemeral real Postgres (Task 4), no SQLite dual-path (Task 4 skips rather than falling back to SQLite), no source-text wiring tests (Task 5 uses `information_schema` introspection + FK-violation behavior, never `read_text()`), every suite has a wiring test (Task 6 proves CI runs the migration test; Task 5's cascade/FK behavior tests prove the schema is reachable). ✓
- Out of scope and correctly deferred: pooled backend (TG2), consumer lift (TG3), importer (TG4), cutover/retirements (TG5). Task 7 Step 3 enforces the SQLite files stay untouched.

**2. Placeholder scan:** No `TODO`/`TBD`/"similar to Task N"/"add error handling" — every code step is complete. The migration DDL is fully written for all 17 tables. ✓

**3. Type/name consistency:** `database_url()`/`alembic_url()`/`MissingDatabaseUrlError` defined in Task 2 and consumed verbatim in Task 3 `env.py`. `migrated_db`/`pg_conn` fixtures defined in Task 4 and consumed in Task 5's test. `SIDEQUEST_DATABASE_URL` (runtime) vs `SIDEQUEST_TEST_DATABASE_URL` (test admin) used consistently. Table set in the test (`ALL_TABLES`) matches the migration's `CREATE TABLE` statements exactly (17 tables). ✓

**Known seams flagged for later task-groups (not gaps):**
- `events.seq` assignment (MAX+1 under row lock) is TG2 — this migration only creates the column + PK.
- The `psycopg_pool.ConnectionPool` and `anyio.to_thread` offload are TG2.
- `scenario_archive.scenario_session_id` rename is recorded so the TG4 importer maps the old `session_id TEXT` → `scenario_session_id`.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-26-postgres-migration-tg1-infra-schema-alembic.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach? (And note: this is task-group 1 of 5 — after it lands on `feat/postgres-substrate`, I write the task-group 2 plan against the same branch.)
