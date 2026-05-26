---
id: 115
title: "Persistence Substrate Migration — SQLite-Per-Session to PostgreSQL"
status: proposed
date: 2026-05-26
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [23, 36, 37, 82, 103]
tags: [core-architecture, transport-infrastructure, project-lifecycle]
implementation-status: deferred
implementation-pointer: null
---

# ADR-115: Persistence Substrate Migration — SQLite-Per-Session to PostgreSQL

## Context

SideQuest stores each play session as a single SQLite file:
`~/.sidequest/saves/games/<slug>/save.db`. One file, one connection, many
tables (`game_state`, `events`, `projection_cache`, `narrative_log`,
`turn_telemetry`, `world_save`, `location_promotions`, the dungeon
region/frontier/mutation/ledger tables). This was the right call for a
single-player, single-process tool and it bought real things: trivial
archival (`cp save.db`), a file-based forensics page, offline save-repair,
`sqlite3` CLI inspection, durable-by-file retention, and zero server
dependency in `just up`.

Multiplayer broke the model's core assumption, and the system has been
paying compounding interest ever since.

### The triggering defect (2026-05-26 beneath_sunden MP playtest)

`turn_telemetry.sink_failed … sqlite3.OperationalError: database is locked`
fired 6× in a single 2-player turn, silently dropping the mechanical and
trope census — exactly the GM-panel lie-detector rows we most need under
load. Root cause, traced to ground:

- `handlers/connect.py` opens a **fresh** `SqliteStore(db)` per connecting
  player and calls `bind_event_store(store)` each time, so the telemetry
  sink is rebound to whichever player connected **last**. With two players
  the process holds **two connections** to one `save.db` (confirmed via
  `lsof`: two FD sets on the live file, one process).
- The C2 turn transaction runs on connection A (`event_log.store._conn`)
  and, *while that write transaction is still open*, fires
  `emit_mechanical_census`. The census publishes watcher events that route
  to `_persist_turn_telemetry`, which writes through connection B
  (`_event_store._conn`).
- Connection A holds the single WAL writer lock (open transaction).
  Connection B's `INSERT` waits on it via `busy_timeout=5000`. But A cannot
  commit until the synchronous census returns. **Deadlock** → 5 s timeout
  → `database is locked` → row dropped. Single-player never reproduces it:
  one connection means the census rides the same open transaction
  (`in_transaction` branch) and there is no second writer.

Note what did *not* save us, all already present and verified live:
`PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, and the reentrant
`SAVE_WRITE_LOCK` wrap. None can help, because the contention is between
two SQLite connections fighting over the one-writer-per-database lock, and
`SAVE_WRITE_LOCK` is a same-process `threading.RLock` that the same thread
re-enters freely.

### The accumulated scar tissue

This bug is one instance of a class. Everything below exists solely to work
around SQLite's single-writer-per-database model:

- **`SAVE_WRITE_LOCK`** — a process-wide reentrant `RLock` that every one of
  ~14 writer sites must acquire in a mandated order (lock-outside-txn, never
  the reverse, or the shared `check_same_thread=False` connection corrupts
  its per-statement state). New writers silently regress the moment they
  forget it.
- **WAL + `busy_timeout` tuning** in `_configure_connection`, plus a
  `PRAGMA wal_checkpoint(TRUNCATE)` on the load path that itself had to be
  wrapped in the lock (PR #447).
- **The connection-identity invariant** (`watcher_hub` docstring): the
  telemetry sink's connection *must be* the same one the C2 transaction uses.
  MP violates it; nothing enforces it.
- **Save-clobber discipline** — `SqliteStore.open()` writes on construction
  (schema + migrations + WAL flip), so all read-only/forensic access must go
  through a hand-rolled `?mode=ro` path (`forensic_query._ro_connect`) or it
  mutates the file it is inspecting.
- **Per-file flushing for preservation** — `cp save.db` loses the WAL tail;
  preservation requires copying the db+wal+shm trio then checkpointing the
  copy (ADR feedback notes).
- **Flagged-but-unfixed writers** — `dungeon/session_integration.py`,
  `dungeon/materializer.py`, `DungeonStore.ensure_schema` commit through the
  shared connection on paths that have not all been audited for the lock.

Each fix spawns the next. This is the "we don't know what's actually
happening" debugging cost the project explicitly tries to avoid.

### The product-direction fork

The decision hinges less on the bug than on where SideQuest is going:

- **A local tool for the table** (one host process, 2–5 players) does not
  *need* Postgres. A single shared connection per session (Alternative 1)
  fixes the deadlock and removes most scar tissue while preserving file
  portability.
- **A hosted, subscription, multi-tenant service** — the direction in
  `docs/prd/prd-creator-authoring-monetization.md` and
  `docs/prd/prd-monetization-web-subscription.md` (customer = the
  forever-DM, viral "friend of a player" acquisition) — *cannot* be backed
  by per-file SQLite. Concurrent sessions, cross-process workers, and a
  managed backup/restore story all assume a real client-server database.
  For that future, "too complicated" merely defers an inevitable cost to a
  worse time.

This ADR proposes Postgres on the premise that the hosted direction is real.
If it is not, Alternative 1 is the better call and this ADR should be
rejected in its favor.

## Decision

**Migrate the per-session SQLite save store to a single PostgreSQL database,
accessed through a repository/data-access layer. Sessions become rows keyed
by `session_slug`, not separate files. PostgreSQL's MVCC and row-level
locking replace `SAVE_WRITE_LOCK`, the WAL/`busy_timeout` tuning, the
load-path checkpoint, and the `?mode=ro` forensic discipline.**

Concretely:

1. **Driver / access layer.** `asyncpg` (or `psycopg3` async) behind a thin
   repository interface (`SaveRepository`) that mirrors the current
   `SqliteStore` surface (`save`, `load`, `append_narrative`,
   `query_encounter_events`, telemetry sink, dungeon persistence). Call
   sites depend on the interface, not on `sqlite3`. A connection **pool**
   replaces the single shared connection; each logical operation borrows a
   pooled connection, so two players' writes proceed on independent
   connections without a global lock.
2. **Schema.** One logical database. Existing per-table shapes are preserved
   but gain a `session_slug` (or integer `session_id`) column and composite
   indexes. The append-only `events` table keeps its `seq` semantics via a
   per-session sequence or `(session_id, seq)` primary key. Migrations move
   to **Alembic**.
3. **Concurrency.** Writers to different sessions never contend. Writers to
   the *same* session serialize naturally on row locks within a transaction
   — no application-level lock. The census write rides the same transaction
   as the turn (one pooled connection per turn), so the deadlock cannot
   recur. Readers (forensics, dashboard, `/api/debug/state`) are MVCC
   snapshots that never block writers — the entire read-only-connection
   discipline becomes unnecessary.
4. **Retirements.** Delete `SAVE_WRITE_LOCK` and its ~14 acquisition sites,
   `_configure_connection`'s WAL/`busy_timeout`, the
   `wal_checkpoint(TRUNCATE)` load path, `forensic_query._ro_connect`'s
   reason for existing, and the connection-identity invariant in
   `watcher_hub`.

## Consequences

### Positive

- **The `database is locked` class is gone**, permanently — not patched.
  Concurrent MP writers are a first-class capability, not a hazard.
- Readers never block writers. Forensics/dashboard/`/api/debug/state` become
  plain queries; the save-clobber discipline and `?mode=ro` plumbing retire.
- **Hosted-ready.** A subscription service can run many concurrent sessions
  against one managed database with one backup/restore story.
- One migration tool (Alembic), one schema, one connection-pool config —
  versus today's hand-rolled `_apply_migrations` + per-file lifecycle.
- Removes a whole category of "did this writer take the lock?" review load.

### Negative / cost

- **Large port.** `game/persistence.py` (~900 lines), `dungeon/persistence.py`,
  `event_log`, `projection_cache`, `forensic_query`, the telemetry sink, the
  ~14 lock sites, and the `rest.py` save-reading endpoints all touch the
  store. This is a multi-story epic, landing right after the Rust→Python
  port (ADR-082) — appetite and sequencing are real concerns.
- **Operational weight.** A Postgres server must run: added to `just up` /
  `just setup`, installed locally (Homebrew or a Docker compose service),
  and provided as a CI service container. `just up` stops being
  zero-dependency.
- **Loss of file portability — the sharpest trade.** `cp save.db`,
  file-based forensics, `_archive/` moves, offline save-repair, durable
  retention by file, and `sqlite3` CLI inspection all assume a file. These
  must be replaced by an explicit save-export/import tool (`pg_dump`-of-one-
  session to a portable artifact, or a logical JSON export) **before**
  cutover, or the workflows Keith relies on regress. This is a hard
  acceptance gate, not a follow-up.
- **Existing-save migration.** Live saves (beneath_sunden-mp, coyote_star,
  glenross, …) need a one-shot importer, or a clean break with a retained
  read-only SQLite reader for archived saves.

### Neutral

- The DAL could keep SQLite as a *test/dev* backend (dual-backend via the
  repository interface). This trims local/CI setup but reintroduces
  two-code-path risk; treat as optional, not a goal.
- `GameSnapshot` serialization, the WebSocket/protocol layer, and game logic
  are untouched — this is a substrate swap beneath the store interface.

## Alternatives Considered

### 1. One shared connection per session (SQLite) — the cheap fix *(recommended if staying local)*

Open exactly **one** `SqliteStore` per session at room creation; have every
player connect, the event log, the telemetry sink, and `save()` all use that
single connection. The current code already *assumes* this (the
`watcher_hub` invariant) — MP just violates it by opening per-player
connections. This eliminates the triggering deadlock and most of the
connection-identity scar tissue, **preserves every file-portability
workflow**, needs no new service, and is roughly one story.

It does **not** enable concurrent cross-process writers or hosted
multi-tenancy. If SideQuest stays a table tool, this is the correct,
proportionate fix and Postgres is over-engineering. This ADR should be
rejected in favor of this alternative unless the hosted direction is
committed.

### 2. Status quo + targeted lock patches

Keep finding and wrapping unlocked writers as they surface. Rejected: the
interest compounds, and the lie-detector keeps losing rows under exactly the
load where it matters most.

### 3. SQLite behind a single global writer queue (actor model)

Serialize all writes through one thread/queue. Works, but it is *more* scar
tissue, caps write throughput at one writer regardless of session count, and
still cannot serve cross-process workers. Strictly worse than Alternative 1
for local use and worse than Postgres for hosted use.

### 4. Another embedded/concurrent engine (DuckDB, etc.)

DuckDB is OLAP, not OLTP; wrong tool for transactional turn writes. Rejected.

## Migration Plan (phased, reversible per phase)

- **Phase 0 — DAL seam (no behavior change).** Introduce `SaveRepository`
  over the existing `SqliteStore`; migrate call sites to the interface.
  Ships value immediately (decouples ~70 game modules from `sqlite3`) and is
  independently revertible.
- **Phase 1 — Postgres backend.** Implement the repository against Postgres
  + asyncpg + Alembic. Run the existing suite against both backends.
- **Phase 2 — Importer + cutover.** One-shot importer for existing saves;
  switch the default backend; delete `SAVE_WRITE_LOCK` and the WAL
  machinery. Keep a read-only SQLite path for archived saves if needed.
- **Phase 3 — Portability tooling.** Save-export/import to a portable
  artifact so `cp save.db`-class workflows survive. **Gate Phase 2 on this.**

## What this ADR does **not** do

- Does not change `GameSnapshot`, the protocol, or game logic — only the
  store beneath the repository interface.
- Does not commit to dual-backend support; that is an optional dev/test
  convenience, not a requirement.
- Does not, by itself, decide the local-vs-hosted product question — it makes
  the technical consequences of each explicit so that decision can be made
  deliberately. Acceptance of this ADR *is* the commitment to the hosted
  direction.
