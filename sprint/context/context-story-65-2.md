---
parent: context-epic-65.md
workflow: tdd
---

# Story 65-2: Per-session asset ledger — track runtime-generated images per save file

## Business Context

Story 65-1 closed the *authored-asset* loop: a committed `r2_manifest.json` plus a
YAML-vs-reality audit (`r2_audit.py`) so either clone can answer "what pack art is in
R2?" without re-rendering. This story closes the **runtime** loop. During play, the
narrator triggers fresh renders — portraits for newly-named NPCs, scene illustrations,
POI landscapes — and the daemon uploads each to R2. Today nothing records *which save*
caused a given upload. When a player resumes, the UI cannot rehydrate those images from
R2; they are effectively orphaned, and the audit cannot tell a save-referenced asset
(permanent) from a stray one (reapable).

The ledger links each save (Postgres `sessions` row) to the R2 keys it generated, so
(a) the UI preloads prior-turn art on reconnect with no re-render, and (b) the audit can
distinguish durable, save-referenced assets from orphans. This serves Keith's two-clone
content workflow and the resume experience for the whole playgroup.

## Technical Guardrails

> **SUBSTRATE CORRECTION — read first.** The session ACs were authored against the
> *retired* SQLite-per-session store. Per **ADR-115** (accepted, implementation
> complete, 2026-05-26) the live substrate is a **single PostgreSQL database** keyed by
> `session_slug`, with schema managed by **Alembic**. `SqliteStore` survives only as a
> read-only import *source* (`sidequest.game.importer`). Therefore:
> - There is **no** `SqliteStore` schema migration and **no** `~/.sidequest/saves/*.db`.
> - There is **no** `daemon_client.upload_complete()` function.
> - The intent of every AC survives; the *mechanism* is restated below against current
>   code. Each restatement is logged as a TEA/Architect deviation.

**Substrate & schema (replaces "SqliteStore schema migration"):**
- New table `asset_ledger` is added via a **new Alembic migration** under
  `sidequest-server/alembic/versions/` (the only existing revision is
  `0001_initial_unified_schema.py`; follow its raw-SQL `op.execute()` + `downgrade()`
  pattern and set `down_revision = "0001"`).
- Follow the `pg/` store pattern: a `PgAssetLedgerStore(pool, *, session_id)` module in
  `sidequest-server/sidequest/game/pg/`, mirroring `pg/scrapbook.py`
  (`PgScrapbookStore`), and surfaced through `pg/save_repository.py`
  (`PgSaveRepository` already composes `PgScrapbookStore` at line ~68 — add the ledger
  store the same way). Do **not** hand-roll a second sqlite connection.
- `session_id` is the internal FK (BIGINT) on every per-session table; the user-facing
  `slug` resolves via `pg_sessions.resolve_session_id(pool, slug=slug)`
  (`sidequest/game/pg/sessions.py:39`).

**Reuse decision — `scrapbook_entries` is adjacent, not a substitute.** The existing
`scrapbook_entries` table (migration line 92) records **one row per turn** for *scene
illustrations* (`image_url`, `render_status`, `turn_id`, `location`, `npcs_present`) and
is consumed by `ImageBusProvider` via `SCRAPBOOK_ENTRY`/`IMAGE` messages. It does **not**
store `r2_key`, asset type, portraits, POIs, or content hashes. The ledger is a
different grain — **one row per R2 asset, all asset types** — so a dedicated table is
justified. Reuse the *store pattern* and the *write hook*, not the scrapbook table.
Cross-link: ledger rows for illustrations can carry the originating `turn_id` so the two
stay reconcilable.

**Write hook (replaces "daemon_client.upload_complete()"):** the render result arrives
in `sidequest/server/websocket_session_handler.py::_run_render_inner()`. At
**line ~3030**, `r2_key = reply.get("r2_key")` is the insertion point — when `r2_key` is
truthy (R2 path, not the legacy local-tmpdir branch), write a ledger row before the
`ImageMessage` is emitted. Available there: `r2_key`, `render_id`, `params` (carries
`tier`, subject/entity hints), `player_id`, and the session. The ledger write must be
idempotent (`INSERT ... ON CONFLICT (r2_key) DO UPDATE`).

**`md5` / `size_bytes` sourcing — RESOLVED: enrich the daemon reply (Doctor decision
2026-05-27).** The image render `reply` currently carries only
`{image_url, r2_key, width, height, elapsed_ms}` — **no `md5`, no `size_bytes`**
(verified in `_run_render_inner` and `sidequest-daemon/.../media/daemon.py`), and
`r2_manifest.json` tracks authored pack assets only, so it cannot supply them for runtime
renders. **Decision:** the daemon owns the bytes at R2-upload time, so it computes and
returns `md5` + `size_bytes` in the image render result. The server then writes them onto
the ledger row. Therefore:
- **`sidequest-daemon` is in scope.** The image render result (`media/daemon.py`, image
  tier — note image dispatch is still inline in `_handle_client`; the result-wrapping
  near lines ~338/351 is where md5/size get added) must include `md5` (hex digest of the
  uploaded bytes) and `size_bytes` (int).
- The ledger columns are therefore **NOT NULL** — every R2 runtime asset has a known
  hash and size at write time. RED tests assert the daemon result carries both and that
  the ledger row persists them (non-null).
- Compute md5 from the same bytes uploaded to R2 (the upload already streams them);
  do not re-read from disk or recompute from a stale path (No Silent Fallbacks).

**REST endpoint (corrects "/api/session/{slug}/assets"):** add
`@router.get("/api/sessions/{slug}/assets")` — note plural `sessions`, matching the
existing convention (`sidequest/server/rest.py:689`
`/api/sessions/{slug}/encounter_events`). Resolve slug→session_id with
`pg_sessions.resolve_session_id`; return a JSON array of ledger rows. Unknown slug → 404,
not a silent empty list (No Silent Fallbacks).

**UI reconnect preload — IN SCOPE (Doctor decision 2026-05-27):** this story ships the
full resume experience end-to-end, so `sidequest-ui` work is part of 65-2 (not a
follow-up). **ImageBus reconnect preload (corrects "ImageBus reads on reconnect"):**
`ImageBusProvider`
(`sidequest-ui/src/providers/ImageBusProvider.tsx`) is a **pure `useMemo` reducer over
message history** — it has no side effects and no WebSocket lifecycle. Reconnect lives in
`hooks/useGameSocket.ts` / `hooks/useWebSocket.ts`. The preload fetch
(`GET /api/sessions/{slug}/assets`) belongs in a `useEffect` at the WebSocket-owning
level (App / GameStateProvider), feeding fetched CDN URLs into the existing image
pipeline. Do **not** add fetch/lifecycle logic inside `ImageBusProvider`.

**Audit extension (corrects "cross-reference *.db files"):** extend
`scripts/r2_audit.py` (the 65-1 artifact: `AuditResult` dataclass line 59, `audit()`
line 178, `format_report()` line 193). The ledger lives in **Postgres**, not SQLite
files — cross-referencing reads the `asset_ledger` table over a DB connection
(`SIDEQUEST_DATABASE_URL`), not `~/.sidequest/saves/*.db`. Add: orphan detection
(in `r2_manifest`/R2 but no ledger reference) and dangling-row detection (ledger
references a key absent from the manifest). Reuse `AuditResult`'s category-list shape;
do not fork the report formatter.

**Durable retention (AC is correct — reinforce):** save-referenced R2 keys are
**permanent**. Never add timer/TTL reaping to ledger-referenced keys. This matches the
server CLAUDE.md ("Saves are durable by default — never reap save-referenced
artifacts"). Orphans (no ledger reference anywhere) are the only reap-eligible class, and
even then reaping is out of scope here — this story only *detects*.

**Cross-cutting rules:**
- **OTEL:** the ledger write is a subsystem decision — emit a watcher span at the write
  hook (`asset_ledger.write` with `r2_key`, `asset_type`, `session_id`, `turn`). The GM
  panel is the lie detector; an un-instrumented write cannot be verified.
- **No source-text wiring tests** (server CLAUDE.md): prove the write fires via a
  fixture-driven behavior test (drive `_run_render_inner` with a synthetic r2_key reply,
  assert a row landed + span fired), or an OTEL span assertion — never grep the handler
  source.
- **No silent fallbacks / no stubs:** unknown slug, missing session, malformed reply all
  fail loudly.

## Scope Boundaries

**In scope:**
- **Daemon:** image render result returns `md5` (hex digest of uploaded bytes) +
  `size_bytes` (`sidequest-daemon`, `media/daemon.py` image tier).
- **Server:** `asset_ledger` Postgres table via new Alembic migration (columns:
  `r2_key` PK, `asset_type`, `entity_ref`, `created_turn`, `md5` NOT NULL,
  `size_bytes` NOT NULL, `session_id` FK, `created_at`).
- `PgAssetLedgerStore` + wiring into `PgSaveRepository`.
- Idempotent ledger write hooked into `_run_render_inner` at the `r2_key` extraction
  point (reading md5/size from the enriched reply), with an OTEL span.
- `GET /api/sessions/{slug}/assets` REST endpoint.
- **UI:** App/GameStateProvider-level reconnect preload that fetches the endpoint and
  feeds the image pipeline (`sidequest-ui`).
- **Scripts:** `r2_audit.py` extension — orphan + dangling-row detection against the
  Postgres ledger.

**Scope note — repos (Doctor decision 2026-05-27):** the real surface is **four repos** —
`sidequest-server` (table, store, hook, REST), `sidequest-daemon` (md5/size in render
result), `sidequest-ui` (reconnect preload), and the orchestrator `scripts/` (audit; the
`r2_manifest.json` artifact is committed under `sidequest-content/`). The session's
`repos: server, content` field is **undercounted** — SM must add `daemon` + `ui` and cut
their feature branches before Dev's GREEN phase.

**Out of scope:**
- Any **reaping/TTL** of orphaned R2 assets — this story detects, never deletes.
- Backfilling ledger rows for assets generated before this story shipped.
- Migrating or extending `scrapbook_entries` — adjacent table, left untouched.
- Real R2 network round-trips in tests — mock the reply/DB; test logic + contract.

## AC Context

> ACs below preserve the session's *intent* and restate the *mechanism* against the
> live Postgres/Alembic substrate (ADR-115). Divergences from the session prose are
> logged under `## Design Deviations` → `### TEA (test design)`.

**AC1 — `asset_ledger` table exists via Alembic migration.**
- New revision under `alembic/versions/` (down_revision `0001`) creating `asset_ledger`:
  `r2_key TEXT PRIMARY KEY`, `asset_type TEXT NOT NULL` (portrait|illustration|poi),
  `entity_ref TEXT NOT NULL`, `created_turn INTEGER NOT NULL`,
  `session_id BIGINT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE`,
  `md5 TEXT NOT NULL`, `size_bytes INTEGER NOT NULL`, `created_at TEXT NOT NULL`. Index
  on `(session_id)`.
- `upgrade()`/`downgrade()` symmetric (downgrade drops the table), mirroring `0001`.
- Test: applying the migration creates the table with the expected columns/constraints;
  `asset_type` outside the enum and a dangling `session_id` are rejected.

**AC2 — daemon render result carries md5 + size_bytes; ledger write is idempotent and
durable.**
- The image render result includes `md5` (hex digest of the bytes uploaded to R2) and
  `size_bytes` (int). Daemon test: a render result for an R2 upload exposes both, derived
  from the uploaded bytes (not recomputed from a stale path).
- `PgAssetLedgerStore.append(...)` performs `INSERT ... ON CONFLICT (r2_key) DO UPDATE`
  — writing the same `r2_key` twice yields one row (upsert), not a duplicate or crash.
- `md5`/`size_bytes` are NOT NULL and are persisted from the enriched reply; a write
  missing either fails loudly (No Silent Fallbacks).
- Durable retention: nothing in the write path schedules reaping of a ledger-referenced
  key.

**AC3 — ledger write fires from the production render path (WIRING).**
- Driving `_run_render_inner` with a synthetic reply containing an `r2_key` lands exactly
  one ledger row for the active session, with `asset_type`/`entity_ref`/`created_turn`
  derived from `params`/turn state.
- An OTEL `asset_ledger.write` span fires with `r2_key`, `asset_type`, `session_id`.
- The legacy local-tmpdir branch (`r2_key` falsy) writes **no** ledger row.
- This is the mandatory integration/wiring test — no source-text grep.

**AC4 — `GET /api/sessions/{slug}/assets` returns the ledger.**
- Returns a JSON array of ledger rows for the resolved session (slug→session_id via
  `resolve_session_id`).
- Reachable on resume/reconnect. Unknown slug → 404 (loud), not an empty 200.
- Test: seeded ledger rows round-trip through the endpoint; unknown slug → 404.

**AC5 — UI preloads prior-turn art on reconnect (no re-render).**
- A reconnect at the WebSocket-owning level fetches `/api/sessions/{slug}/assets` and
  feeds the returned CDN URLs into the image pipeline; portraits/illustrations from prior
  turns appear without a new daemon render.
- `ImageBusProvider` stays a pure reducer — the fetch/lifecycle lives outside it.
- Test (vitest): on reconnect, the fetch is issued and resolved URLs reach the gallery;
  no render request is emitted for already-ledgered assets.

**AC6 — `r2_audit.py` cross-references the ledger.**
- Extends `audit()`/`AuditResult`: detects orphans (in manifest/R2, referenced by no
  ledger row across all sessions) and dangling rows (ledger row whose `r2_key` is absent
  from the manifest), reporting path + affected session(s).
- Reads the ledger from Postgres (`SIDEQUEST_DATABASE_URL`), not `*.db` files.
- `format_report` gains the two categories without forking; `main()` exit code stays
  `0` clean / `1` on gaps.
- Test: synthetic manifest + seeded ledger produce the expected orphan/dangling split;
  no false positives.

## Assumptions

- A new Alembic revision is the accepted schema-change mechanism (only `0001` exists
  today; this is the first follow-on migration — confirm the revision-id convention with
  Dev if `alembic/env.py` enforces a format).
- The active `session_id` is reachable from `_run_render_inner` (via the session/handler
  context); if it is not directly in scope at line ~3030, threading it there is part of
  the wiring work, not a blocker.
- `entity_ref` and `asset_type` are derivable from the render `params` (tier + subject
  hints). If a render lacks a resolvable entity_ref, fail loudly rather than writing a
  placeholder — coordinate the exact param keys with Dev during GREEN.
- The audit's Postgres read is acceptable in the orchestrator `scripts/` context (it
  already depends on pyyaml; psycopg becomes a new audit-time dep — flag if contentious,
  mirroring 65-1's boto3 note).
