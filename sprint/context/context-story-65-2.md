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

**Content hash / size — RE-RECONCILED 2026-05-27 (Architect; supersedes the earlier
"enrich the daemon reply" decision).** TEA's RED grounding surfaced three facts that make
the daemon enrichment unnecessary and unwise:
1. **The content hash is already in the key.** `r2_writer.upload_artifact` computes
   `sha256(content_bytes)` and *embeds it in the returned key*:
   `artifacts/<world>/<session>/<kind>/<sha256>.<ext>`
   (`sidequest-daemon/.../media/r2_writer.py:91`; the image worker returns this `r2_key`
   at `workers/zimage_mlx_worker.py:529`). Since the ledger's PK **is** `r2_key`, the
   content hash is already persisted — for free. No daemon change is needed to obtain it.
2. **It's sha256, not md5.** There is no md5 anywhere on the runtime path. Forcing md5
   would mean a redundant second hash of every render.
3. **`size_bytes` serves no resume function.** The UI rehydrate path needs
   `r2_key → CDN URL`, asset type, and entity ref — not a byte count. `size_bytes` was
   inherited from the `r2_manifest` model (authored pack assets), which does not apply to
   runtime artifacts.

**Decisions:**
- **Drop the `md5` column.** If a queryable hash is wanted, add `content_sha256` derived
  from the key basename at write time (`r2_key.rsplit("/",1)[-1].split(".")[0]`) — zero
  daemon work. The context treats `content_sha256` as **optional/derived**, not required.
- **Drop the `size_bytes` column from v1.** Re-add only alongside the deferred
  daemon-enrichment follow-up if a real consumer appears.
- **`sidequest-daemon` drops OUT of scope.** This also sidesteps the in-flux image-tier
  dispatch refactor (`dispatch_request` `NotImplementedError`, "Task 12"). The render
  result already returns `r2_key`; that is all the ledger needs.
- *This reverses the 2026-05-27 "expand scope to daemon" decision on new evidence (hash
  is free, size is non-load-bearing). Flagged for the Doctor: re-expand only if you
  specifically want `size_bytes` surfaced now.*

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

**Audit cross-reference (AC6) — DEFERRED to a follow-up story (Architect 2026-05-27).**
The original AC6 — cross-reference the ledger against `r2_manifest.json` — **cannot be
built and is not coherent** against the live code:
- The ledger tracks **runtime** keys under `artifacts/<world>/<session>/...`; the manifest
  tracks **authored pack** keys under `genre_packs/...`. The two namespaces are
  **disjoint** (the pack uploader *requires* the `genre_packs/` prefix,
  `r2_writer.py:196`). Diffing them flags every ledger row as "dangling" — noise, not
  signal.
- A real runtime-asset audit ("does this ledger `r2_key` still exist in R2?") needs an
  **R2 listing/HEAD capability that does not exist anywhere** in `r2_writer.py` or
  `scripts/` — that is net-new boto3 work, not a 65-1 `r2_audit.py` extension.
- A runtime **retention/reaping policy** (when may an unreferenced `artifacts/` object be
  deleted?) is also undesigned.

**Decision:** AC6 leaves this story. 65-2 delivers the *durable record itself* (the
ledger + write + REST + UI preload) — exactly as 65-1 delivered the manifest before any
pack audit existed. File a follow-up: "Runtime-artifact R2 audit — ledger-vs-R2-listing +
retention policy." `scripts/` / `sidequest-content` drop out of this story's scope.

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
- **Server:** `asset_ledger` Postgres table via new Alembic migration (columns:
  `r2_key` PK, `asset_type`, `entity_ref`, `created_turn`, `session_id` FK,
  `created_at`; optional derived `content_sha256`). No `md5`, no `size_bytes`.
- `PgAssetLedgerStore` + wiring into `PgSaveRepository`.
- Idempotent ledger write hooked into `_run_render_inner` at the `r2_key` extraction
  point, with an OTEL span. (`r2_key` already carries the sha256; nothing else needed
  from the render reply.)
- `GET /api/sessions/{slug}/assets` REST endpoint.
- **UI:** App/GameStateProvider-level reconnect preload that fetches the endpoint and
  feeds the image pipeline (`sidequest-ui`).

**Scope note — repos (RE-RECONCILED 2026-05-27, Architect):** the real surface is
**two repos** — `sidequest-server` (table, store, hook, REST) and `sidequest-ui`
(reconnect preload), plus the orchestrator for sprint/session artifacts. The earlier
expansion to `daemon` (md5/size) and `content`/`scripts` (AC6 audit) is **withdrawn** on
new evidence (hash is free in the key; AC6 is deferred). **SM action:** set
`repos: server, ui` and retire the now-unused `feat/65-2-*` branches in
`sidequest-daemon` and `sidequest-content` (cut earlier when scope looked four-repo).

**Out of scope:**
- **`sidequest-daemon` changes** — the render reply already supplies `r2_key` (with the
  sha256 in it); no enrichment needed.
- **AC6 audit / `r2_audit.py`** — deferred to a follow-up (see Audit cross-reference
  above). `scripts/` + `sidequest-content` not touched here.
- `size_bytes` / `md5` columns — dropped from v1.
- Any **reaping/TTL** of orphaned R2 assets — out of scope; the follow-up owns retention.
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
  `created_at TEXT NOT NULL`. Index on `(session_id)`. **No `md5` / `size_bytes`** (the
  content sha256 already lives inside `r2_key`; see Content hash / size guardrail).
- `upgrade()`/`downgrade()` symmetric (downgrade drops the table), mirroring `0001`.
- Test: applying the migration creates the table with the expected columns/constraints;
  `asset_type` outside the enum and a dangling `session_id` are rejected.

**AC2 — ledger write is idempotent and durable.**
- `PgAssetLedgerStore.append(...)` performs `INSERT ... ON CONFLICT (r2_key) DO UPDATE`
  — writing the same `r2_key` twice yields one row (upsert), not a duplicate or crash.
- The write reads only fields already present on the render reply (`r2_key`) + turn/params
  context; no daemon-supplied hash or size is required.
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

**AC6 — DEFERRED, not in this story.** The ledger-vs-manifest cross-reference compares
disjoint R2 namespaces and depends on an R2-listing capability that does not exist (see
*Audit cross-reference* guardrail). No RED test is written for AC6 here; it moves to a
follow-up story ("Runtime-artifact R2 audit"). TEA: log this as a descoped AC in the
AC-accountability table, not a test gap.

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
