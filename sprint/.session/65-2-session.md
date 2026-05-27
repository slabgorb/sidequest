---
story_id: "65-2"
jira_key: null
epic: "65"
workflow: "tdd"
---
# Story 65-2: Per-session asset ledger — track runtime-generated images per save file

## Story Details
- **ID:** 65-2
- **Jira Key:** TBD (will be assigned when claimed)
- **Epic:** 65 — Content Infrastructure — R2 asset tracking and audit
- **Workflow:** tdd
- **Repos:** server, content
- **Points:** 3
- **Priority:** P1
- **Type:** feature
- **Stack Parent:** none

## Problem Statement

Runtime-generated images (portraits, scene illustrations, POI renders triggered during play) are uploaded to R2 by the daemon but never recorded against the save file that caused them. When a player resumes a session, those images are orphaned — the UI can't find them because nothing links the save to its R2 keys.

## Acceptance Criteria

### Server: SQLite schema and asset_ledger table
- [ ] Add `asset_ledger` table to `SqliteStore` schema migration with columns:
  - `r2_key` (TEXT, PRIMARY KEY) — full R2 path (e.g., `genre_packs/caverns_and_claudes/images/portraits/slug.png`)
  - `asset_type` (TEXT, NOT NULL) — enum: portrait | illustration | poi
  - `entity_ref` (TEXT, NOT NULL) — NPC slug, scene ID, or POI slug (the thing the asset represents)
  - `created_turn` (INTEGER, NOT NULL) — turn number when asset was generated
  - `md5` (TEXT, NOT NULL) — MD5 hash from r2_manifest.json
  - `size_bytes` (INTEGER, NOT NULL) — file size from r2_manifest.json

### Server: daemon_client asset ledger writes
- [ ] `daemon_client.upload_complete()` receives R2 upload result (r2_key, asset_type, entity_ref, turn, md5, size_bytes) and writes asset_ledger row
- [ ] Ledger write is idempotent (upsert on r2_key)
- [ ] Respects durable-retention-by-default: never reap save-referenced R2 assets on a timer

### Server: REST API
- [ ] `GET /api/session/{slug}/assets` returns full asset_ledger for the save (JSON array of ledger rows)
- [ ] Endpoint is available during session resume and accessible to the UI on reconnect

### UI: ImageBus ledger read on reconnect
- [ ] `ImageBus` reads `/api/session/{slug}/assets` on reconnect (when WebSocket reconnects after a player returns to a saved session)
- [ ] Preloads CDN URLs for portraits and illustrations from previous turns — no re-rendering needed
- [ ] Maps asset_type + entity_ref to the correct UI component slots (portrait gallery, scene context, POI backgrounds)

### Audit: r2_audit.py cross-references asset_ledger
- [ ] `r2_audit.py` (from story 65-1) cross-references asset_ledger tables across all saves in `~/.sidequest/saves/*.db`
- [ ] Detects orphaned R2 keys: uploaded to R2 but no save references them (in r2_manifest but missing from all asset_ledgers)
- [ ] Detects dangling ledger rows: save references an R2 key that no longer exists (in asset_ledger but missing from r2_manifest)
- [ ] Reports both categories with path, MD5, and affected save files

## Technical Notes

**Dependencies:** Completes the loop started in story 65-1 (r2_manifest.json). The manifest provides the durable record; the asset_ledger links saves to their assets.

**Durable retention:** Never apply reaping logic to save-referenced assets. If a save's asset_ledger references an R2 key, that key must remain in R2 indefinitely. Orphaned keys (in manifest but unrefenced) are fair game for eventual cleanup, but save-referenced keys are permanent.

**Entity refs:** Store the canonical reference (NPC slug, scene ID, POI slug) so the UI can map back to the right component. The audit then uses these refs to validate that YAML entities still exist.

**No re-render on resume:** The whole point — when a player loads a save, the UI should find the portraits and illustrations in the ledger and load from CDN without triggering new daemon renders. This requires ledger writes to be *eager* and *complete* on each upload.

## Sm Assessment

**Disposition:** Ready for RED. Story is fully scoped — six AC clusters spanning server (SQLite `asset_ledger` schema, `daemon_client` upsert writes, `GET /api/session/{slug}/assets`), UI (`ImageBus` reconnect read + CDN preload), and audit (`r2_audit.py` cross-reference). Direct continuation of 65-1, which landed `r2_manifest.json` and `r2_audit.py`; this story closes the loop by linking saves to their R2 keys.

**Technical approach for TEA/Dev:**
- Schema migration adds `asset_ledger` keyed on `r2_key` (upsert/idempotent); columns enumerated in AC.
- Write path hangs off `daemon_client.upload_complete()` — verify the daemon already returns r2_key/md5/size_bytes (65-1's manifest plumbing) so this is wiring, not reinvention.
- REST endpoint must be reachable on resume/reconnect; `ImageBus` consumes it to preload portraits/illustrations without re-rendering.
- Audit reuses 65-1's `r2_audit.py` — extend, don't fork — to flag orphans (manifest∖ledgers) and dangling rows (ledger∖manifest).

**Durable-retention invariant:** save-referenced R2 keys are permanent — never reaped on a timer. RED tests must pin this.

**Wiring gate:** per project rules, RED must include an integration test proving the ledger write fires from the production upload path and the endpoint is hit by `ImageBus` on reconnect — not just unit coverage of the table.

**Risks:** cross-repo (server + content + ui touched by ACs though `repos: server,content` — UI ACs may spill into sidequest-ui; flag if so). No blockers; 65-1 merged.

## Workflow Tracking

**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-05-27T15:44:33Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27 | 2026-05-27T15:44:33Z | 15h 44m |
| red | 2026-05-27T15:44:33Z | - | - |

## Delivery Findings

No upstream findings (setup phase).

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->