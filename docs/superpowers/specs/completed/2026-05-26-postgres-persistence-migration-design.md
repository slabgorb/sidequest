# Design: PostgreSQL Persistence Substrate — Direct Port

**Date:** 2026-05-26
**Author:** Major Margaret Houlihan (Architect) with Keith Avery
**Implements:** ADR-115 (`docs/adr/115-postgres-persistence-substrate.md`)
**Status:** Approved for planning — hand off to writing-plans
**Supersedes:** the phased-strangler framing in the prior revision of this
file (Phase 0 SQLite seam → Phase 1 Postgres → Phase 3 portability → Phase 2
cutover). See "Why a direct port" below.

## Purpose

Port SideQuest's per-session SQLite save store to a single PostgreSQL
database accessed through domain repository interfaces — in one coherent
push, not as a SQLite-seam-first strangler. This permanently deletes the
`database is locked` deadlock class and every piece of single-writer scar
tissue (`SAVE_WRITE_LOCK`, WAL/`busy_timeout` tuning, the load-path
checkpoint, the `?mode=ro` forensic discipline, the connection-identity
invariant), and makes concurrent multiplayer writers a first-class
capability.

## Why a direct port (reversing the phased strangler)

ADR-115 originally locked **Approach A — incremental strangler, Phase
0→1→3→2**, and rejected the big-bang port. Slice 1a shipped against that
framing (the `SaveRepository` + `transaction()` seam, PR #459). On scoping
Slice 1b — "migrate the remaining `SqliteStore` consumers onto the
interface, still backed by SQLite, defer the other repositories to later
slices" — the strangler framing fell apart on contact with the real
coupling:

**The backend is an all-or-nothing property of one shared connection.**
`DungeonStore`, the telemetry sink (`turn_telemetry`), the forensic reads,
the scrapbook writers, and the save tables are all handed the *same*
`sqlite3.Connection` off `SqliteStore`. You cannot put the save tables on
Postgres while leaving dungeon/telemetry/forensic on SQLite — the moment
that connection becomes a `psycopg_pool` pool, every consumer touching it
must already be off raw `sqlite3` access or it breaks. So:

- "Migrate the save domain to a repository, defer `ForensicReader` /
  `DungeonRepository` / `TelemetrySink` to later SQLite-backed slices" is
  **incoherent** — they ride the same connection and must port together.
- A Phase 0 that ships an *inert SQLite-only seam* as an independent,
  revertible milestone delivers no user value and parks the tree in a
  mixed state where every persistence edit forces the question *"is this
  consumer on the repository or raw? is this path SQLite or Postgres?"*
  That cognitive/maintenance cost exceeds the cost of just doing the port
  (Keith, 2026-05-26).

Therefore the migration unit is **everything that touches the shared
connection**, ported to Postgres in one direction. The repository
interfaces remain — they are good structure — but their concrete
implementation is Postgres, and 1a's `SaveRepository` is reused as the
foundation, not as a throwaway SQLite scaffold.

This reverses ADR-115's "reject big-bang" decision; ADR-115 is amended to
record the shared-connection rationale.

## Governing principle: the backend is a swappable detail behind the DAL

Done right, swapping SQLite for Postgres is — modulo dialect details —
*a library swap behind one data-access layer*. The only reason this port
is more than that is the accumulated raw-connection reach-through: ~30
call sites that hold `SqliteStore._conn` / `SqliteStore.connection()` and
run SQL directly instead of going through a typed method. **Every one of
those leaks is the bug; closing them is the port.**

The invariant that makes the backend swappable: **no raw connection ever
escapes a repository.** Once every persistence call goes through a typed
repository method, the concrete engine (`psycopg3` today, anything
SQL-compatible tomorrow) is isolated to the adapter implementations and
swappable without touching a single consumer. That isolated DAL — not
"Postgres" per se — is the durable deliverable; Postgres is the first
backend it cleanly hosts. This is why the work is "lift every consumer
onto the interface," and why a half-lifted tree (some calls typed, some
raw) is the failure mode to avoid: a DAL with leaks isn't a DAL.

## Scope decisions (locked, carried forward from ADR-115)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Driver + concurrency | **sync `psycopg3` + `psycopg_pool.ConnectionPool`** | The concurrency win is the pool + Postgres MVCC, not async I/O. Store calls keep their synchronous shape; calls from async handlers offload via `anyio.to_thread` so independent turns run on independent pooled connections. (Corrects ADR-115's `asyncpg` draft text.) |
| Writable backend | **Postgres-only; SQLite demoted to read-only importer source** | One writable backend. A dual writable backend is the parallel-mechanism trap. |
| Provisioning | **Native Homebrew + `launchd` locally (pinned major); GitHub Actions `services: postgres` of the same major in CI** | No Docker dependency added to `just up`. |
| Portability / importer | **Versioned logical JSON bundle, per session** | Backend-agnostic, diff-able, human-inspectable; doubles as archive format and the existing-save importer's intermediate representation. `pg_dump` for whole-instance ops backups only. |
| Session keying | **integer surrogate `session_id` PK + unique `session_slug` natural key; `events` PK `(session_id, seq)`** | Preserves append-only `seq` semantics and the `projection_cache → events.seq` FK. |
| Migrations | **Alembic** | Replaces hand-rolled `_apply_migrations` + `ALTER TABLE`-in-`try`. |
| Existing saves | **Importer is mandatory; saves are never sacrificed** | Keith plays in years-not-weeks units (durable-retention doctrine). The importer runs on the live saves at cutover; it is a hard gate, not a follow-up. |

## Already shipped (reused, not rebuilt)

Slice 1a (PR #459, merge `e72049a`) introduced:
- `sidequest/game/repository.py` — `SaveRepository` + `SaveTransaction`
  Protocols (the unit-of-work seam).
- `sidequest/game/sqlite_repository.py` — `SqliteSaveRepository` adapter
  with `transaction()` preserving the `SAVE_WRITE_LOCK` order.
- `EventLog`, `ProjectionCache`, `emit_event`'s C2 block, and `connect.py`
  migrated off raw `sqlite3` connection passing.

The interface and the migrated consumers carry forward. What changes: the
concrete backend becomes Postgres, the interface grows to cover every
connection-sharing domain, and the transitional `SqliteSaveRepository.store`
hatch is deleted (its consumers — scrapbook writers in `emitters.py`,
narration-recap reads in `views.py`, the `connect._replay` image-url map —
move onto typed methods or the Postgres reader).

## Target architecture

Domain repository interfaces exposing typed methods only — no raw
connection ever leaves a repository — **all backed by one Postgres pool.**
The split is for cohesion and testability, *not* so any one domain can run
a different backend (they share the DB):

- **`SaveRepository`** — `game_state`, `events`, `narrative_log`,
  `projection_cache`, `location_promotions`, `world_save`, `scrapbook`,
  `games`/session lifecycle. Absorbs the raw SQL currently in
  `event_log.py`, `views.py` (narration recap), `projection/cache.py`,
  `scrapbook_coverage.py`, and the `emitters.py` scrapbook writers.
- **`DungeonRepository`** — the dungeon region/frontier/mutation/ledger
  tables now in `DungeonStore`. Stops being constructed from a borrowed
  `sqlite3.Connection`; shares the session pool through the interface.
  Replaces the `materializer.py:1777` `persistence._conn` "Plan-5 seam"
  with a named method (Architect sign-off: the replacement is an
  intentional caller-owned-boundary method, not a mechanical swap).
- **`TelemetrySink`** — `turn_telemetry` writes (today in `watcher_hub.py`
  / `emitters.py`). The census write borrows the **same** pooled
  connection/transaction as the turn, which is structurally why the
  two-connection deadlock cannot recur.
- **`ForensicReader`** — read-only queries (`forensic_query.py`,
  `corpus/save_reader.py`, `rest.py` read endpoints). Against Postgres
  these are plain MVCC-snapshot reads; the `?mode=ro` discipline retires.

**Backend:** sync `psycopg3` + `psycopg_pool.ConnectionPool`. Each logical
operation borrows a pooled connection inside a `with pool.connection()`
scope; the connection never escapes that scope or crosses threads. From
async handlers, store calls offload via `anyio.to_thread` so two players'
turns proceed on independent connections.

**Retired at cutover:** `SAVE_WRITE_LOCK` and its 33 sites,
`_configure_connection`'s WAL/`busy_timeout`, the load-path
`wal_checkpoint(TRUNCATE)`, the `watcher_hub` connection-identity
invariant, the `?mode=ro` discipline, `SqliteStore.connection()` and all
external `._conn` access, and the 1a transitional `.store` hatch.

## Schema

One logical database. Existing per-table shapes preserved, each per-session
table gaining an integer `session_id` FK. A `sessions` table carries the
unique `session_slug` natural key. The append-only `events` table keeps its
`seq` semantics via composite PK `(session_id, seq)`, preserving the
`projection_cache → events.seq` foreign key. Alembic owns all migrations.

## Concurrency model

- Writers to **different** sessions touch different rows — never contend.
- Writers to the **same** session serialize on row locks within a
  transaction — no application-level lock.
- The mechanical-census write shares the turn's transaction/connection, so
  the A-vs-B two-connection deadlock is structurally impossible.
- Readers (forensics, dashboard, `/api/debug/state`) are MVCC snapshots —
  never block writers.

## The port (one direction, decomposed into task-groups)

One plan, many tasks, one PR direction — no SQLite-only milestone parked in
the tree. Suggested task-group ordering (the plan refines this):

1. **Postgres infra + schema + Alembic.** Local brew/launchd (pinned
   major), CI `services: postgres`, Alembic init, the `sessions` table +
   `session_id`/`session_slug` keying across every per-session table.
2. **`psycopg3` pooled backend for every repository.** `SaveRepository`,
   `DungeonRepository`, `TelemetrySink`, `ForensicReader` — all against the
   one pool. The census write rides the turn transaction.
3. **Lift every remaining consumer off raw connection / `SqliteStore`
   access onto typed methods** — the ~25-30 save-domain consumers, the
   `DungeonStore` borrowed-connection sites (`session_helpers.py:601`,
   `websocket_session_handler.py:1249`, `dungeon/session_integration.py`),
   the telemetry sink, the forensic reads, and the `rest.py` endpoints.
   No carve-outs. `SessionData` gains a `repository` (and dungeon/telemetry
   accessors); `SqliteStore` direct method calls disappear.
4. **Importer (lands ahead of cutover so it can be dry-run).** SQLite
   read-only reader → versioned JSON bundle → Postgres import, FK-ordered.
   Extends `corpus/save_reader.py`. Dry-run on a *copy* of an active save
   (e.g. `coyote_star`) before touching live files.
5. **Cutover + retirements.** Flip the backend to Postgres, run the
   importer on the live saves (`beneath_sunden-mp`, `coyote_star`,
   `glenross`), delete `SAVE_WRITE_LOCK` + the WAL machinery + the
   `?mode=ro` plumbing + `SqliteStore.connection()`/`.store` hatch.

## Decomposition for buildability (Keith's buffer note)

Large files are buffer-hostile (the practical working window is ~2k lines).
Where the port lets us extract a cohesive unit cheaply, do it; where it
would balloon into an unrelated refactor, keep edits to minimal line-range
changes at the call sites.

- **New repository code → packages, not single files.** The Postgres
  adapter(s) split by domain (`events`, `snapshot`, `narrative`,
  `promotions`, `scrapbook`, `games`, `dungeon`, `telemetry`, `forensic`)
  so no adapter file approaches the buffer limit.
- **`websocket_session_handler.py` (6842 lines)** and
  **`session_helpers.py` (2011 lines)** are *not* decomposed wholesale here
  — that is its own spec. The port touches them only at the call sites
  (`save`, `append_narrative`, `max_narrative_round`, `close`, the
  `DungeonStore` constructions), as minimal line-range edits. Flag the
  wss_handler decomposition as a separate recommended spec.

## Testing

Single backend everywhere: ephemeral real Postgres (CI `services:
postgres`, local brew/launchd, pinned major). Per-test isolation via
transaction-rollback or schema-per-test. **No SQLite dual-path.** The
repository interfaces let unit tests mock the interface where the DB is not
the system under test.

Per `sidequest-server/CLAUDE.md`: every test suite needs a wiring test, but
**no source-text wiring tests** (no `inspect.getsource`/grep-of-source
asserts) — use OTEL-span or fixture-driven behavior assertions. **No
content-coupled tests** (don't load live `genre_packs/*` and assert). The
importer gets a round-trip test: SQLite fixture → bundle → Postgres →
assert equivalence.

## Risks / watch-items

1. **This is a big single-direction port**, not a series of inert milestones.
   Mitigation: decomposed into task-groups within one plan; the importer
   lands ahead of cutover and is dry-run on a save *copy*; the existing
   suite (run against ephemeral Postgres) is the green-to-green net.
2. **`DungeonStore`'s borrowed-connection seam** (`materializer.py:1777`)
   is the trickiest lift; the replacement method has Architect sign-off as
   an intentional boundary method.
3. **Sync-in-threadpool correctness** — one pooled connection per worker
   thread; never share a connection across threads; verify no connection
   escapes its `with pool.connection()` scope.
4. **Existing-save data loss is unacceptable** — the importer is a hard
   cutover gate; dry-run on a copy before any live file is touched; the
   read-only SQLite reader is retained for archived saves.
5. **Stale ADR text** — `asyncpg` (superseded by `psycopg3`) and the "right
   after the Rust→Python port" appetite clause are struck in the ADR-115
   amendment.

## What this design does NOT do

- Does not change `GameSnapshot`, the WebSocket/protocol layer, or game
  logic — only the store beneath the repository interfaces.
- Does not commit to dual *writable* backends (SQLite is read-only importer
  source only).
- Does not decide where Postgres runs in production or commit to cloud
  hosting / multi-tenancy. Deployment is a separate, deferred axis;
  self-hosted is the expected default, not a fallback (see ADR-115).
