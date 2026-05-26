# Design: PostgreSQL Persistence Substrate Migration

**Date:** 2026-05-26
**Author:** Major Margaret Houlihan (Architect) with Keith Avery
**Implements:** ADR-115 (`docs/adr/115-postgres-persistence-substrate.md`)
**Status:** Approved for planning — hand off to writing-plans

## Purpose

Migrate SideQuest's per-session SQLite save store to a single PostgreSQL
database accessed through domain repository interfaces. This permanently
deletes the `database is locked` deadlock class and all the single-writer
scar tissue (`SAVE_WRITE_LOCK`, WAL/`busy_timeout` tuning, the load-path
checkpoint, the `?mode=ro` forensic discipline, the connection-identity
invariant), and gives concurrent multiplayer writers as a first-class
capability.

This is the **full-epic** spec covering all four phases. It is structured
phase-by-phase so `writing-plans` can decompose each phase into its own plan.

## Scope decisions (locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Driver + concurrency | **sync `psycopg3` + `psycopg_pool.ConnectionPool`** | The concurrency win comes from the pool + Postgres MVCC, not async I/O. Keeps the port's blast radius small; store calls keep their synchronous shape. Calls from async handlers are offloaded via `anyio.to_thread`/`run_in_executor` so independent turns run on independent pooled connections. |
| End-state backend | **Postgres-only writable; SQLite read-only archive reader** | One writable backend. A dual writable backend is the parallel-mechanism trap (two code paths, backend-divergent test results). |
| Provisioning | **Native Homebrew + `launchd` locally (pinned major); GitHub Actions `services: postgres` of same major in CI** | No Docker dependency added to `just up`. (Docker Compose was considered and rejected per Keith 2026-05-26.) |
| Portability artifact | **Versioned logical JSON bundle, per session** | Backend-agnostic, diff-able, human-inspectable, survives schema drift via the importer. Doubles as the archive format and the existing-save importer's intermediate representation. `pg_dump` available for whole-instance ops backups only. |
| Session keying | **integer surrogate `session_id` PK + unique `session_slug` natural key; `events` PK `(session_id, seq)`** | Preserves append-only `seq` semantics and the existing `projection_cache → events.seq` FK. |
| Migrations | **Alembic** | Replaces hand-rolled `_apply_migrations` + `ALTER TABLE`-in-`try`. |
| Sequencing | **Approach A — incremental strangler, dependency-ordered** (Phase 0 → 1 → 3 → 2) | Each phase independently revertible; ships value at Phase 0; honors ADR-115's "gate cutover on portability." Dual-write (B) and big-bang (C) rejected. |

## Ground truth (verified against the live tree, 2026-05-26)

The ADR's estimates were approximate; the real coupling is what the design
must address:

- `SAVE_WRITE_LOCK`: **33 references across 3 files** —
  `game/persistence.py`, `server/emitters.py`, `telemetry/watcher_hub.py`.
- `game/persistence.py`: **962 lines**; `SqliteStore` exposes 16 public
  methods plus a `connection()` raw-handle escape hatch.
- **~23 files** reference `SqliteStore` (not "~70 modules").
- `bind_event_store`: only **2 files** (`watcher_hub.py`, `handlers/connect.py`)
  — the per-player rebinding bug is localized.
- **The real SQLite coupling is raw-connection reach-through**, not the
  method surface:
  - `DungeonStore` is constructed from `SqliteStore.connection()`
    (`server/session_helpers.py:601`, `server/websocket_session_handler.py:1249`)
    and runs ~20 raw `execute()` sites on the shared connection
    (`dungeon/persistence.py`).
  - `dungeon/materializer.py:1777` reaches `persistence._conn` directly —
    explicitly documented as the "Plan-5 caller-owned-boundary seam."
  - Raw SQL on `store._conn` is scattered across `server/emitters.py` and
    `game/event_log.py` (writes); `server/views.py`,
    `game/forensic_query.py`, `game/projection/cache.py`,
    `game/scrapbook_coverage.py` (reads); `telemetry/watcher_hub.py` (the
    telemetry sink); `handlers/connect.py`.
  - `corpus/save_reader.py` already implements a separate `?mode=ro` reader.

**Implication:** Phase 0's labor is lifting every raw-SQL reach-through into
a typed repository method and eliminating all external `.connection()` /
`._conn` access. Until no consumer holds a raw connection, Phase 1 cannot
swap the backend.

## Target architecture

A set of **domain repository interfaces** that expose typed methods only —
no raw connection ever leaves a repository.

- **`SaveRepository`** — `game_state`, `events`, `narrative_log`,
  `projection_cache`, `location_promotions`, `world_save`, `scrapbook`.
  Mirrors `SqliteStore`'s 16 methods and absorbs the raw SQL currently in
  `event_log.py`, `views.py`, `projection/cache.py`, `scrapbook_coverage.py`.
- **`DungeonRepository`** — the dungeon tables now in `DungeonStore`. Stops
  being constructed from a borrowed `sqlite3.Connection`; shares the session
  pool/transaction through the interface. Replaces the
  `materializer.py:1777` `persistence._conn` seam with a named method.
- **`TelemetrySink`** — `turn_telemetry` writes (today in `watcher_hub.py` /
  `emitters.py`).
- **`ForensicReader`** — read-only queries (`forensic_query.py`,
  `corpus/save_reader.py`, `rest.py` read endpoints).

**Backend:** sync `psycopg3` + `psycopg_pool.ConnectionPool`. Each logical
operation borrows a pooled connection inside a `with pool.connection()`
scope; the connection never escapes that scope or crosses threads. From
async handlers, store calls are offloaded via `anyio.to_thread` so two
players' turns proceed on independent connections. The per-turn transaction
borrows one connection and the mechanical-census write rides **that same**
transaction — structurally why the two-connection deadlock cannot recur.

**Retired at cutover:** `SAVE_WRITE_LOCK` and its 33 sites,
`_configure_connection`'s WAL/`busy_timeout`, the load-path
`wal_checkpoint(TRUNCATE)`, the `watcher_hub` connection-identity invariant,
and the `?mode=ro` discipline (MVCC readers never block writers).

## Schema

One logical database. Existing per-table shapes preserved, each per-session
table gaining an integer `session_id` FK. A `sessions` table carries the
unique `session_slug` natural key. The append-only `events` table keeps its
`seq` semantics via composite PK `(session_id, seq)`, preserving the current
`projection_cache → events.seq` foreign key. Alembic owns all migrations.

## Concurrency model

- Writers to **different** sessions touch different rows — never contend.
- Writers to the **same** session serialize on row locks within a
  transaction — no application-level lock.
- The mechanical-census write shares the turn's transaction/connection, so
  the A-vs-B two-connection deadlock is structurally impossible.
- Readers (forensics, dashboard, `/api/debug/state`) are MVCC snapshots —
  never block writers.

## Phases (dependency-ordered, each independently revertible)

### Phase 0 — DAL seam over existing SQLite (zero behavior change)
Define the four repository interfaces. Lift every raw-SQL reach-through into
a typed method; delete `.connection()` and all external `._conn` access.
Re-point the ~23 consumers at interfaces. `DungeonStore` becomes
`DungeonRepository` sharing the session connection through the interface.
Replace the `materializer.py:1777` "Plan-5 seam" with a named repository
method (requires Architect sign-off — it is an intentional architectural
seam, not a mechanical swap). Backed by the existing `SqliteStore`; default
unchanged. **Land in reviewable slices — one repository at a time — not one
mega-PR.** Behaviorally inert and suite-guarded.

### Phase 1 — Postgres backend behind the interfaces
Implement each repository against Postgres with `psycopg3` + pool + Alembic.
Run the full suite against an ephemeral Postgres. SQLite implementation
still present and default; no cutover. Add a wiring test proving the
Postgres backend is reachable from a production code path (project
wiring-test rule).

### Phase 3 — Portability + importer (built and verified before cutover)
Versioned per-session JSON bundle:
`{schema_version, session_slug, exported_at, tables: {<table>: [rows...]}}`,
FK-ordered for import. Two producers (SQLite read-only reader → bundle,
extending `corpus/save_reader.py`; Postgres → bundle), two consumers
(bundle → Postgres import; bundle inspection). The existing-save importer is
SQLite-reader → bundle → Postgres. Importer applies forward migrations on
load so old bundles survive schema drift. **Hard gate on Phase 2.**

### Phase 2 — Cutover
Flip the default backend to Postgres. Run the importer on active saves
(`beneath_sunden-mp`, `coyote_star`, `glenross`). Delete `SAVE_WRITE_LOCK`
and the WAL machinery. Demote SQLite to the read-only archive reader. Gated
on Phase 3 complete and verified.

## Testing

Single backend everywhere: ephemeral real Postgres (CI `services: postgres`,
local brew/launchd, pinned major). Per-test isolation via
transaction-rollback or schema-per-test. No SQLite dual-path. The repository
interface lets unit tests mock the interface where the DB is not the system
under test. Phase 0 ships behaviorally inert, so the existing suite is the
green-to-green safety net.

## Risks / watch-items

1. **Phase 0 is the dragon** — a wide pure-refactor across ~8 raw-SQL
   modules. Mitigation: behaviorally inert, suite-guarded, landed in
   per-repository slices.
2. **`DungeonStore`'s borrowed-connection seam** (`materializer.py:1777`)
   is the trickiest lift; the replacement method needs Architect sign-off.
3. **Sync-in-threadpool correctness** — one pooled connection per worker
   thread; never share a connection across threads; verify no connection
   escapes its `with pool.connection()` scope.
4. **Stale ADR text** — strike the "right after the Rust→Python port"
   appetite clause from ADR-115's Negative section when it is next touched;
   the port was weeks ago and the project is in a stable bugfixing period.

## What this design does NOT do

- Does not change `GameSnapshot`, the WebSocket/protocol layer, or game
  logic — only the store beneath the repository interfaces.
- Does not commit to dual writable backends.
- Does not decide where Postgres runs in production or commit to cloud
  hosting / multi-tenancy. Deployment is a separate, deferred axis;
  self-hosted is the expected default, not a fallback (see ADR-115).
