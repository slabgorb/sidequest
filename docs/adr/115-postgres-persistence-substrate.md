---
id: 115
title: "Persistence Substrate Migration — SQLite-Per-Session to PostgreSQL"
status: accepted
date: 2026-05-26
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [23, 36, 37, 82, 103]
tags: [core-architecture, transport-infrastructure, project-lifecycle]
implementation-status: live
implementation-pointer: "docs/superpowers/specs/2026-05-26-postgres-persistence-migration-design.md"
---

# ADR-115: Persistence Substrate Migration — SQLite-Per-Session to PostgreSQL

> **Amendment 2026-05-27 (direct port complete; SQLite retired to importer source).**
> The `psycopg3`-pooled Postgres backend is live and the engine is fully cut
> over. The single shared `sqlite3.Connection` and all of its scar tissue are
> **deleted**: `SqliteStore`, `SqliteSaveRepository`, the process-wide
> `SAVE_WRITE_LOCK` and its acquisition sites, `_configure_connection`'s
> WAL/`busy_timeout` tuning, and the load-path `wal_checkpoint(TRUNCATE)`/`.bak`
> machinery are gone. SQLite survives **only** as a read-only import *source*:
> `sidequest/game/importer.py` (`import_sqlite_save`) reads a legacy save
> RO-immutable and FK-ordered-inserts it into Postgres in one transaction. The
> whole-corpus argparse CLI (`python -m sidequest.cli.import_saves`, `--save-dir`,
> `--dry-run`, the intermediate JSON bundle) described in the original migration
> plan was **descoped 2026-05-26**: the real entry point is the
> `python -m sidequest.game.importer` one-shot, scoped to the single
> `coyote_star-mp` save.

> **Amendment 2026-05-26 (sequencing reversal).** This ADR originally locked
> an incremental strangler (Phase 0 SQLite seam → Phase 1 Postgres → Phase 3
> portability → Phase 2 cutover) and rejected the big-bang port. After Slice
> 1a shipped (`SaveRepository` seam, PR #459), scoping Slice 1b exposed that
> the backend is an **all-or-nothing property of one shared
> `sqlite3.Connection`**: `DungeonStore`, the telemetry sink, forensic reads,
> the scrapbook writers, and the save tables all ride the same connection,
> so they must port together — a save-domain-only Postgres swap is
> unbuildable, and an inert SQLite-only Phase-0 milestone parks the tree in a
> high-cost "which backend / typed-or-raw?" limbo. The migration is therefore
> a **direct port of every connection-sharing consumer**, reversing the
> big-bang rejection. The driver is **`psycopg3` (sync) + `psycopg_pool`**,
> not `asyncpg`. See the design spec (implementation-pointer above) for the
> governing DAL-isolation principle and task-group decomposition.

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

### Two orthogonal axes (do not conflate them)

A common error — made in this ADR's first draft — is to equate "Postgres"
with "cloud/hosted." They are independent decisions:

1. **Embedded single-writer DB vs client-server multi-writer DB.** This is
   the concurrency decision. SQLite serializes all writes to a database;
   Postgres gives MVCC + row-level locking so concurrent writers proceed.
   This benefit is identical whether Postgres runs as a `brew`/launchd
   daemon on the dev box, a box in the closet on the LAN, or a managed cloud
   instance. **This is what this ADR is actually about.**
2. **Where the database runs.** Same machine, the closet server, the LAN,
   or a cloud provider. This is a *deployment* decision, fully separable and
   deferrable. The internet (and Postgres) predate cloud services; a
   self-hosted Postgres is a first-class, boring option.

So the real trade for SideQuest **as it exists today** (a local table tool,
one host process, 2–5 players) is not "local vs hosted." It is:

- **Postgres (runnable locally):** permanently deletes the
  `database is locked` class and all the lock scar tissue, gives concurrency
  headroom, and — should a hosted/subscription future
  (`docs/prd/prd-creator-authoring-monetization.md`,
  `docs/prd/prd-monetization-web-subscription.md`) ever arrive — is already
  the right substrate. Costs a running daemon and the loss of file
  portability (below).
- **One shared connection per session (SQLite, Alternative 1):** the minimal
  fix — kills the specific deadlock, keeps `cp save.db` portability and
  zero-ops, but leaves the embedded single-writer ceiling in place.

The decision turns on how much weight to put on *permanently* killing the
lock class + concurrency headroom versus file-portability + zero added ops.
It does **not** require committing to cloud hosting or multi-tenancy.

## Decision

**Migrate the per-session SQLite save store to a single PostgreSQL database,
accessed through a repository/data-access layer. Sessions become rows keyed
by `session_slug`, not separate files. PostgreSQL's MVCC and row-level
locking replace `SAVE_WRITE_LOCK`, the WAL/`busy_timeout` tuning, the
load-path checkpoint, and the `?mode=ro` forensic discipline.**

Concretely:

1. **Driver / access layer.** **`psycopg3` (sync) + `psycopg_pool.ConnectionPool`**
   behind domain repository interfaces (`SaveRepository`, `DungeonRepository`,
   `TelemetrySink`, `ForensicReader`) that together cover the full
   `SqliteStore`/shared-connection surface. Call sites depend on the
   interfaces, not on `sqlite3` — **no raw connection ever escapes a
   repository** (the invariant that makes the backend a swappable detail).
   The pool replaces the single shared connection; each logical operation
   borrows a pooled connection, so two players' writes proceed on independent
   connections without a global lock. Calls from async handlers offload via
   `anyio.to_thread`. The Postgres instance runs natively (Homebrew/launchd
   locally, `services: postgres` in CI); **no Docker** dependency in
   `just up`, and cloud is **not** implied or required.
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
- **Deployment-flexible.** Runs as a local daemon on the dev box, a server
  in the closet, or a LAN box — and *if* a hosted/subscription future ever
  arrives, the same substrate serves it. The concurrency win is identical in
  all cases; hosting is a later, separate decision, not a prerequisite.
- One migration tool (Alembic), one schema, one connection-pool config —
  versus today's hand-rolled `_apply_migrations` + per-file lifecycle.
- Removes a whole category of "did this writer take the lock?" review load.

### Negative / cost

- **Large port.** `game/persistence.py` (~960 lines), `dungeon/persistence.py`,
  `event_log`, `projection_cache`, `forensic_query`, the telemetry sink, the
  33 lock sites, and the `rest.py` save-reading endpoints all touch the
  store. This is a multi-task epic. Per the 2026-05-26 amendment it is done
  as one direct port (not phased), decomposed into task-groups within a
  single plan; the difficulty is concentrated in the accumulated
  raw-connection reach-through, which the DAL closes.
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

It does **not** lift the embedded single-writer ceiling — write throughput
stays one-at-a-time per session and there is no path to concurrent
cross-process writers. The choice between this and the Decision is the
file-portability-and-zero-ops vs kill-the-lock-class-permanently trade
described above — **not** a local-vs-hosted question (Postgres runs locally
just fine). Reject ADR-115 in favor of this alternative if preserving
`cp save.db` portability and adding no running service outweighs
permanently removing the lock class.

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

## Migration Plan (direct port, per 2026-05-26 amendment)

The original phased strangler is superseded — see the amendment note at the
top of this ADR. Because the backend is an all-or-nothing property of the
one shared connection, the port is a single coherent direction, decomposed
into task-groups inside one plan (not independently-shipped phases). 1a's
`SaveRepository` seam (PR #459) is the reused foundation.

1. **Postgres infra + schema + Alembic** — brew/launchd local, CI
   `services: postgres`, `sessions` table + `session_id`/`session_slug`
   keying, `events` PK `(session_id, seq)`.
2. **`psycopg3` pooled backend for every repository** — `SaveRepository`,
   `DungeonRepository`, `TelemetrySink`, `ForensicReader`, all on one pool.
3. **Lift every consumer onto the interfaces** — the ~30 raw-connection /
   `SqliteStore` reach-through sites, no carve-outs; this is the DAL.
4. **Importer (ahead of cutover, dry-run on a save copy)** — SQLite
   read-only reader → versioned JSON bundle → Postgres, FK-ordered.
5. **Cutover + retirements** — flip the backend, import the live saves
   (`beneath_sunden-mp`, `coyote_star`, `glenross`), delete `SAVE_WRITE_LOCK`
   + WAL machinery + `?mode=ro` plumbing + `SqliteStore.connection()`.

The importer / portability tooling is a **hard cutover gate** (durable-
retention doctrine: existing saves are never sacrificed). A read-only SQLite
reader is retained for archived saves.

Full design and task-group detail:
`docs/superpowers/specs/2026-05-26-postgres-persistence-migration-design.md`.

## What this ADR does **not** do

- Does not change `GameSnapshot`, the protocol, or game logic — only the
  store beneath the repository interface.
- Does not commit to dual-backend support; that is an optional dev/test
  convenience, not a requirement.
- Does **not** decide where the database runs or commit to cloud hosting /
  multi-tenancy. Acceptance commits only to a client-server DB substrate;
  deployment (local daemon, closet/LAN server, or — if ever wanted — cloud)
  is a separate, deferred decision. Self-hosted is expected to be the
  default, not a fallback.

## Amendment (2026-05-31): SQLite→Postgres Importer Design Contract

ADR-115 tracked the SQLite→Postgres importer only as a **TG-E work item** in the
Migration Plan ("Importer (ahead of cutover, dry-run on a save copy)") and
referenced `forensic_query._ro_connect` in passing as the read-only discipline
the migration retires. This amendment records the importer's **design
decisions** as a standing contract, so a future maintainer who runs it against a
richer save than the one it was built for understands exactly what it guarantees
— and what it deliberately does not. The importer is live at
`sidequest-server/sidequest/game/importer.py`.

### What the importer is

`import_sqlite_save(sqlite_path, pool)` (`importer.py`) is a **one-shot,
single-save** importer, not the whole-corpus tool the original plan sketched. It
returns a per-table `ImportSummary` (`importer.py`) for a round-trip check.

### Design decision 1 — source opened READ-ONLY + IMMUTABLE

The legacy save is opened via the SQLite URI
`file:{sqlite_path}?mode=ro&immutable=1` (`importer.py`). It is never
written, checkpointed, or copy-then-mutated — the original save is treated as
precious and immutable (`importer.py`, `66-67`). `immutable=1` additionally
asserts the file will not change underneath us, letting SQLite skip locking
entirely. This is the import-time analogue of the read-only forensic discipline
(`forensic_query._ro_connect`) the migration otherwise retires on the Postgres
side.

### Design decision 2 — FK-ordered bulk INSERT in ONE transaction

The whole import runs inside a single `pool.connection()` / `conn.transaction()`
block (`importer.py`), so a partial failure rolls the **entire** import back
— no half-imported session. Rows are inserted in foreign-key order
(`importer.py`):

1. `sessions` first (`importer.py`), `RETURNING session_id` — the FK
   every per-session row needs.
2. Per-session tables next — `game_state`, `narrative_log`, `scrapbook_entries`,
   `events`, `turn_telemetry` (`importer.py`).
3. `projection_cache` **last** (`importer.py`) because its
   `(session_id, event_seq)` FK references `events`, which must already be
   present.

The INSERTs are **raw**, intentionally **not** routed through the `Pg*Store`
write methods: those stamp a fresh `created_at = now`, which would destroy the
historical timeline. Raw INSERTs preserve source `seq` / `round` / `payload` /
`content` verbatim (`importer.py`, `212-213`). Note `events.seq` is
preserved exactly (PK `(session_id, seq)`), while IDENTITY columns
(`narrative_log.id`, `scrapbook_entries.id`, `turn_telemetry.seq`) are **not**
re-inserted (`importer.py`, `190`, `227`).

### Design decision 3 — NO silent drop of unhandled tables (safety invariant)

The importer hard-codes the set of tables a `coyote_star-mp` save populates
(`_handled`, `importer.py`). It then enumerates every real table in the
source via `sqlite_master` (`importer.py`) and, for any unhandled table
carrying a **non-zero** row count, **raises** rather than silently skipping it
(`importer.py`). An empty/missing source table simply contributes 0 to
its count; only genuinely-populated unhandled tables raise. This is the No Silent
Fallbacks rule applied to data loss: a reuse against a richer save is caught, not
quietly lossy. The module explicitly calls out that **`beneath_sunden-mp` has
dungeon data the guard currently rejects** (`importer.py`,
`131-137`) — `world_save`, `location_promotions`, `scenario_archive`,
`lore_fragments`, and `dungeon_*` are all unhandled. A maintainer importing such
a save must extend `_handled` and add the corresponding FK-ordered INSERT blocks;
the guard ensures they cannot forget.

### Design decision 4 — timestamp normalization (`_norm_ts`)

`_norm_ts` (`importer.py`) routes every text timestamp
(`created_at` / `last_played` / `saved_at` / `ts`) through
`datetime.fromisoformat(...).isoformat()`. SQLite writes the space-separated form
(`YYYY-MM-DD HH:MM:SS`); `fromisoformat` accepts it and re-emits the `T`
separator, and is idempotent on already-`T` values (preserving tz offset and
microseconds). This is **load-bearing** because `PgForensicReader.build_timeline`
lexically sorts `created_at` and dropped its prior `_NORM_EV_TS` normalization —
a mixed space/`T` separator would mis-bound rounds in the forensic timeline
(`importer.py`, `47-56`). `_norm_ts` never touches
`seq` / `round` / `payload` / `content`.

### Explicitly rejected scope (descoped 2026-05-26)

The importer deliberately omits the machinery the original migration plan
sketched (`importer.py`, `271-279`):

- **No argparse / whole-corpus CLI** (no `python -m sidequest.cli.import_saves`,
  no `--save-dir`). The entry point is the `python -m sidequest.game.importer`
  one-shot whose `__main__` block hard-targets the single
  `coyote_star-mp` save path (`importer.py`).
- **No `--dry-run` flag** — the single-transaction rollback-on-failure is the
  safety net instead.
- **No intermediate versioned JSON bundle** — the import goes SQLite → Postgres
  directly.
- **No corpus loop** over `~/.sidequest/saves/games/*` — exactly one save at a
  time.

These were descoped on 2026-05-26 because the migration only had to carry the
handful of live saves across the cutover, not service an open-ended fleet. A
maintainer who needs the broader corpus path should treat that as new work, not a
regression of this contract.
