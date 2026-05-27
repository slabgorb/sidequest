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
**Phase:** review
**Phase Started:** 2026-05-27T17:48:53Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27 | 2026-05-27T15:44:33Z | 15h 44m |
| red | 2026-05-27T15:44:33Z | 2026-05-27T17:26:45Z | 1h 42m |
| green | 2026-05-27T17:26:45Z | 2026-05-27T17:42:44Z | 15m 59s |
| spec-check | 2026-05-27T17:42:44Z | 2026-05-27T17:43:43Z | 59s |
| verify | 2026-05-27T17:43:43Z | 2026-05-27T17:48:53Z | 5m 10s |
| review | 2026-05-27T17:48:53Z | - | - |

## Delivery Findings

No upstream findings (setup phase).

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (blocking): The ledger `md5` column has no runtime source. The runtime
  artifact uploader computes **sha256** (`hashlib.sha256(content_bytes).hexdigest()`) and
  embeds it in the key; no md5 is computed anywhere on the render path. Affects
  `sidequest-daemon/sidequest_daemon/media/r2_writer.py:91` and the ledger schema
  (`asset_ledger.md5`) — column should reuse the existing sha256, not compute a second
  hash. *Found by TEA during test design.*
- **Conflict** (blocking): Runtime renders and authored pack assets occupy **disjoint R2
  namespaces** — runtime → `artifacts/{world}/{session}/{kind}/{sha}.{ext}`; manifest/pack
  → `genre_packs/...` (the pack uploader *requires* the `genre_packs/` prefix). Affects
  `sidequest-daemon/.../r2_writer.py:196` and **AC6** (`scripts/r2_audit.py` ledger
  cross-reference): comparing ledger keys against the manifest compares disjoint sets, so
  every ledger row is spuriously "dangling" and orphan detection is meaningless as
  specified. AC6 needs redefinition (e.g. cross-ref against the `artifacts/` R2 listing,
  not the manifest) before it can be tested. *Found by TEA during test design.*
- **Gap** (blocking): The daemon image render result is mid-refactor —
  `sidequest-daemon/.../media/daemon.py` `dispatch_request` raises `NotImplementedError`
  for the image tier ("inline in `_handle_client` until Task 12"). Adding md5/size to the
  image render result (AC2) lands in code explicitly in flux; the wiring target is
  unstable. *Found by TEA during test design.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Architect (reconcile)
- **Drop `md5`/`size_bytes`; daemon out of scope**
  - Spec source: context-story-65-2.md, AC2 (prior rev) + Doctor decision 2026-05-27 "expand scope to daemon"
  - Spec text: "the daemon owns the bytes at R2-upload time, so it computes and returns `md5` + `size_bytes` in the image render result … ledger columns are therefore NOT NULL"
  - Implementation: ledger stores neither column; content sha256 is already embedded in `r2_key` (`artifacts/<world>/<session>/<kind>/<sha256>.<ext>`, `r2_writer.py:91`), so it is persisted for free via the PK; `size_bytes` has no resume consumer
  - Rationale: avoids a redundant second hash and an unnecessary change to in-flux image-tier daemon code (`dispatch_request` NotImplementedError, "Task 12"); reuse-first
  - Severity: major (reverses a Doctor decision on new evidence — flagged for veto)
  - Forward impact: `sidequest-daemon` exits scope; `size_bytes` re-addable in the AC6 follow-up if a consumer appears
- **AC6 (ledger↔manifest audit) deferred to a follow-up**
  - Spec source: context-story-65-2.md, AC6 (prior rev)
  - Spec text: "extends `audit()`/`AuditResult`: detects orphans (in manifest/R2…) and dangling rows (ledger row whose `r2_key` is absent from the manifest)"
  - Implementation: AC6 removed from 65-2; no RED test written for it; filed as "Runtime-artifact R2 audit" follow-up
  - Rationale: ledger keys (`artifacts/…`) and manifest keys (`genre_packs/…`) are disjoint namespaces (`r2_writer.py:196`), so the diff is all-noise; a real audit needs an R2-listing capability that does not exist + an undesigned retention policy
  - Severity: major (removes an AC cluster)
  - Forward impact: `scripts/` + `sidequest-content` exit scope; follow-up story owns runtime-artifact retention + R2 listing
- **Repos reduced to server + ui**
  - Spec source: epic-65.yaml 65-2 `repos: server,content,daemon,ui`
  - Spec text: "repos: server,content,daemon,ui"
  - Implementation: effective scope is `server, ui`; SM to update the field and retire the unused `feat/65-2-*` branches in `sidequest-daemon` and `sidequest-content`
  - Rationale: consequence of the two deviations above
  - Severity: minor
  - Forward impact: fewer branches to finish/merge at story close

### TEA (test design)
- **AC6 has no RED test (descoped)**
  - Spec source: context-story-65-2.md, AC6 (current rev)
  - Spec text: "AC6 — DEFERRED, not in this story. … No RED test is written for AC6 here; it moves to a follow-up story"
  - Implementation: no test authored for the ledger↔manifest audit; tracked as a DESCOPED AC, not a coverage gap
  - Rationale: the audit is incoherent against disjoint R2 namespaces and depends on a non-existent R2-listing capability (see Architect reconcile)
  - Severity: minor
  - Forward impact: follow-up story "Runtime-artifact R2 audit" owns it
- **Two RED tests pass vacuously (non-discriminating until GREEN)**
  - Spec source: context-story-65-2.md, AC3 + AC4
  - Spec text: "Unknown slug → 404 (loud)" / "The legacy local-tmpdir branch (`r2_key` falsy) writes no ledger row"
  - Implementation: `test_get_assets_404_for_unknown_slug` passes in RED because the route is absent (all paths 404); `test_render_without_r2_key_writes_no_ledger_row` passes because the hook is absent (MagicMock `.called` is False). Both remain valid, meaningful assertions once GREEN lands.
  - Rationale: kept deliberately — they guard the GREEN behavior; a RED-only failure isn't required for every assertion
  - Severity: trivial
  - Forward impact: none
## TEA Assessment

**Tests Required:** Yes
**Phase:** review — RED confirmed (failing, ready for Dev)

**Earlier blocking findings:** RESOLVED by the Architect reconciliation (2026-05-27) —
md5/sha256, disjoint-namespace AC6, and the daemon mid-refactor are all dispositioned in
the context + Design Deviations. RED was written against the reconciled context (scope:
server + ui).

**Test Files:**
- `sidequest-server/tests/persistence/test_pg_asset_ledger.py` — AC1 (table shape via
  migration; no md5/size; r2_key PK; FK) + AC2 (`PgAssetLedgerStore` upsert, isolation,
  injection-safety)
- `sidequest-server/tests/server/test_rest_session_assets.py` — AC4
  (`GET /api/sessions/{slug}/assets` round-trip, 404-on-unknown-slug, empty-list)
- `sidequest-server/tests/server/test_asset_ledger_write_wiring.py` — AC3 (mandatory
  wiring: ledger write fires from `_run_render_inner` on an r2_key reply + OTEL watcher
  event; local-only render writes nothing)
- `sidequest-ui/src/hooks/__tests__/useAssetPreload.test.ts` — AC5 (reconnect-edge fetch
  of the asset endpoint → preload callback; no fetch w/o slug; no double-fetch)

**Tests Written:** 20 (15 server + 5 ui) covering AC1–AC5. AC6 descoped (deferred).
**Status:** RED — 9 failed, 5 errors (missing-module fixtures), 2 vacuous-pass (noted as
deviations), UI collection error (missing hook). All trace to missing implementation.
**Env note:** the pg suite requires `SIDEQUEST_TEST_DATABASE_URL` (e.g.
`postgresql://$USER@localhost:5432/sidequest_test`, provisioned by `just pg-up`) — same
precondition as every existing `tests/persistence/*` test.

### Rule Coverage (lang-review)

| Rule (python.md / ts) | Test(s) | Status |
|------|---------|--------|
| #6 test quality — meaningful assertions | all assert specific values; 2 non-discriminating-in-RED flagged as deviations | satisfied |
| #11 parameterized SQL (no f-string injection) | `test_injection_safe_entity_ref_roundtrips_literally` | failing (RED) |
| #11 boundary validation — unknown input loud | `test_get_assets_404_for_unknown_slug` (404, not silent-empty) | green-vacuous in RED |
| #1 no silent fallback — local render writes nothing | `test_render_without_r2_key_writes_no_ledger_row` | green-vacuous in RED |
| OTEL principle — subsystem decision emits span | `test_render_ledger_write_emits_watcher_event` | failing (RED) |
| Wiring (CLAUDE.md) — fires from production path, no source-grep | `test_render_with_r2_key_writes_asset_ledger` (drives `_run_render_inner`) | failing (RED) |
| FK / PK integrity | `test_r2_key_is_primary_key`, `test_dangling_session_id_rejected` | failing (RED) |
| cross-session isolation | `test_cross_session_isolation` | error (missing module) |

**Rules checked:** Python #1, #6, #11 + OTEL + wiring + integrity have coverage.
**Self-check:** no `assert True` / `let _ =` / always-None assertions; the two
non-discriminating-in-RED tests are intentional GREEN guards, logged as trivial deviations.

### Contract defined for Dev (GREEN)
- `sidequest.game.pg.asset_ledger.PgAssetLedgerStore(pool, *, session_id)` with
  `.append(r2_key, asset_type, entity_ref, created_turn)` (upsert on r2_key) and
  `.list_assets()`.
- `PgSaveRepository.append_asset_ledger(...)` composing the store (mirrors
  `append_scrapbook_entry`).
- New Alembic revision (down_revision `0001`) creating `asset_ledger`.
- `GET /api/sessions/{slug}/assets` in `rest.py` (resolve slug→session_id; 404 on miss).
- Ledger write + `state_transition field=asset_ledger op=write` watcher event in
  `_run_render_inner` when the reply carries `r2_key`.
- `sidequest-ui` `@/hooks/useAssetPreload` ({slug, connected, onAssets}) fetching the
  endpoint on the (re)connect edge.

### Delivery Findings (red phase)
- No new upstream findings during test design (the three blocking findings were resolved
  pre-RED by the Architect reconciliation).

**Handoff:** To Dev for implementation.
## Dev Assessment

**Implementation Complete:** Yes for the RED suite (21/21 green); **AC5 app-wiring is NOT
done — see blocking finding below.**

**Files Changed (server):**
- `alembic/versions/0002_asset_ledger.py` (new) — asset_ledger table migration
- `sidequest/game/pg/asset_ledger.py` (new) — `PgAssetLedgerStore` (upsert + list)
- `sidequest/game/pg/save_repository.py` — compose store + `append_asset_ledger`/`list_asset_ledger`
- `sidequest/game/repository.py` — `SaveRepository` Protocol: `session_id`, asset-ledger methods
- `sidequest/server/rest.py` — `GET /api/sessions/{slug}/assets`
- `sidequest/server/websocket_session_handler.py` — ledger write + OTEL event in `_run_render_inner`
- `tests/persistence/test_pg_asset_ledger.py` — fixture fix (per-test-unique r2_keys)

**Files Changed (ui):**
- `sidequest-ui/src/hooks/useAssetPreload.ts` (new) — reconnect-edge fetch hook

**Tests:** 21/21 new GREEN (16 server + 5 ui). Regression: render + save_repo + rest
suites 36/36 pass. ruff + eslint clean; pyright adds 0 new errors (asset_ledger.py 0;
rest.py's 11 are pre-existing at unrelated lines).
**Branches:** `feat/65-2-per-session-asset-ledger` pushed (sidequest-server, sidequest-ui).
**Env:** pg suite needs `SIDEQUEST_TEST_DATABASE_URL` (provisioned by `just pg-up`).

### Delivery Findings

#### Dev (implementation)
- **Gap** (blocking): `useAssetPreload` has **no production consumer** — it is built and
  unit-tested (AC5) but not mounted in `App.tsx`, and there is no defined path to feed
  fetched CDN URLs into the image pipeline. `ImageBusProvider` is a pure reducer over a
  `messages` array (Architect constraint) with no imperative input, so "feed the preload
  into the gallery" needs a design decision (synthetic IMAGE messages vs. a new ImageBus
  input seam). The AC5 RED test exercises the hook in isolation only — there is no
  app-integration/wiring test. Affects `sidequest-ui/src/App.tsx` +
  `providers/ImageBusProvider.tsx`. **This is a half-wired feature** per CLAUDE.md; it
  needs either an in-story wiring task (mount + ImageBus feed + a wiring test) or an
  explicit split to a UI follow-up. *Found by Dev during implementation.*
- **Improvement** (non-blocking): the `asset_ledger.r2_key` global PK is correct only
  because production keys embed the session (`artifacts/<world>/<session>/...`). If a
  future change ever content-addresses runtime artifacts session-independently, the same
  asset reused across two saves would `ON CONFLICT`-collapse to one row under whichever
  session wrote first, losing the second reference. Affects
  `sidequest/game/pg/asset_ledger.py`. *Found by Dev during implementation.*

## Design Deviations (Dev)

### Dev (implementation)
- **asset_type derived from the r2_key `<kind>` segment**
  - Spec source: context-story-65-2.md, AC3
  - Spec text: "`asset_type` … derived from `params`/turn state"
  - Implementation: derived from the `<kind>` path segment of
    `artifacts/<world>/<session>/<kind>/<sha>.<ext>` (the segment R2 actually used),
    falling back to `params["tier"]` only if the key has too few segments
  - Rationale: the key segment is ground truth (what R2 stored) and matches the RED
    fixtures; more reliable than re-deriving from the render tier
  - Severity: minor
  - Forward impact: none
- **Test-fixture fix: per-test-unique r2_keys**
  - Spec source: tests/persistence/test_pg_asset_ledger.py (TEA RED)
  - Spec text: reused hardcoded `r2_key` strings across distinct test sessions
  - Implementation: gave colliding tests (idempotent, injection, cross-session,
    append_then_list) distinct r2_keys; assertions unchanged
  - Rationale: `r2_key` is a GLOBAL PK; the session-scoped test DB is shared across
    tests, so reused keys hit `ON CONFLICT` on a prior test's row and the new session
    saw zero rows. Production keys embed the session, so this matches reality.
  - Severity: minor (test hygiene; no assertion weakened)
  - Forward impact: none
- **SaveRepository Protocol gained `session_id` + asset-ledger methods**
  - Spec source: sidequest/game/repository.py
  - Spec text: Protocol declared scrapbook methods but not `session_id`
  - Implementation: added `session_id` property + `append_asset_ledger`/`list_asset_ledger`
  - Rationale: the render hook accesses both via the Protocol-typed `sd.repository`;
    PgSaveRepository already satisfies them
  - Severity: trivial
  - Forward impact: none

**Handoff:** To next phase — but flag the blocking AC5 wiring gap above.

### Dev (implementation) — AC5 app-wiring descope (Doctor decision 2026-05-27)
- **AC5 app-integration split to a follow-up story**
  - Spec source: context-story-65-2.md, AC5
  - Spec text: "A reconnect at the WebSocket-owning level fetches `/api/sessions/{slug}/assets` … feeds the returned CDN URLs into the image pipeline"
  - Implementation: the `useAssetPreload` hook (fetch-on-reconnect-edge) is delivered and
    unit-tested; mounting it in `App.tsx` and defining how preloaded CDN URLs enter the
    (pure-reducer) ImageBus pipeline is split to a UI follow-up per the Doctor's decision
  - Rationale: the ImageBus feed needs a design decision (synthetic IMAGE messages vs. a
    new input seam) that touches the Architect's "keep ImageBus pure" constraint; doing it
    untested under this story would be a half-wired hack
  - Severity: major (an AC's app-integration leaves this story)
  - Forward impact: **SM to file follow-up** "Mount useAssetPreload in App + ImageBus
    preload feed (with wiring test)"; the prior blocking Dev finding is thereby downgraded
    to this planned descope (no longer blocks 65-2)

**Status update:** the AC5 app-wiring finding above is **resolved as a planned descope**,
not a blocker. 65-2 delivers: backend ledger fully wired+tested (migration→store→repo→
REST→render-write, incl. the production-path wiring test) + the tested preload hook.
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with one Doctor-approved deferral)
**Mismatches Found:** 2 (both already dispositioned — no drift to chase)

- **AC5 app-integration not in code** (Missing in code — Behavioral, Major)
  - Spec: reconnect fetches the asset endpoint and feeds CDN URLs into the image pipeline
  - Code: `useAssetPreload` hook delivered + unit-tested; not mounted in App, no ImageBus feed
  - Recommendation: **D — Defer.** Already approved by the Doctor (2026-05-27) as a UI
    follow-up; logged under Dev deviations. The ImageBus feed is a genuine design decision
    (pure-reducer constraint). Not drift — a planned scope split. SM files the follow-up.

- **asset_type derived from r2_key `<kind>` segment, not from `params`** (Different
  behavior — Cosmetic, Trivial)
  - Spec: "asset_type derived from params/turn state"
  - Code: derived from the `<kind>` path segment of the r2_key (ground truth of what R2
    stored), with `params["tier"]` fallback
  - Recommendation: **A — Update spec.** The key segment is more reliable than the tier;
    the context already reflects this. Logged under Dev deviations. No action.

**Backend alignment:** AC1–AC4 fully aligned — migration, store, REST, and the
production-path render-write (with OTEL event) all match the reconciled context and are
covered by passing tests, including the mandatory wiring test. AC6 deferred at context
level (disjoint-namespace audit).

**Decision:** Proceed to verify. No hand-back to Dev — both mismatches are
already-decided deferrals/improvements, not unaddressed drift.
## TEA Assessment (verify)

**Phase:** review
**Status:** GREEN confirmed (21/21 new tests; 36 render/rest/save-repo regression tests pass)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7 impl/test files (both repos)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | 1 high (CDN url resolution) applied; 1 high (extract resolve_session_id_or_404) flagged-scope; 1 medium (asset_type helper) flagged |
| simplify-quality | 3 findings | 1 high (CDN url, same as reuse) applied; 1 medium (hasattr silent-skip guard) applied; 1 low (unused `request` param) flagged |
| simplify-efficiency | clean | only low-confidence observations on the render-hook guard/key-parse — superseded by the applied guard removal |

**Applied:** 2 fixes
- `rest.py` `get_session_assets`: resolve each `r2_key` → absolute `url` via
  `resolve_asset_url` (two teammates flagged high; closes the cross-repo contract gap
  with `SessionAsset.url`). REST test extended to assert `url`.
- `websocket_session_handler.py` `_run_render_inner`: removed the
  `hasattr(sd.repository, "append_asset_ledger")` guard — a silent-skip fallback the
  `<critical>` No-Silent-Fallbacks rule forbids; the Protocol guarantees the method.

**Flagged for Review (not applied):**
- **Extract `resolve_session_id_or_404(pool, slug)`** (reuse, high) — genuine DRY across
  5 REST endpoints, but 4 are pre-existing and out of this story's scope. Good
  standalone cleanup chore. *Not applied — scope.*
- **Unused `request: Request` param** on `get_session_assets` (quality, low) — matches
  the sibling `get_encounter_events`/`get_game_endpoint` convention; left for consistency.
- **`asset_type` extraction helper** (reuse, medium) — single call site today; extract
  only if a second consumer appears.

**Reverted:** 0

**Overall:** simplify: applied 2 fixes

**Quality Checks:** ruff clean; pyright adds 0 new errors (rest.py's 11 are pre-existing
at unrelated lines); eslint clean; render/rest/save-repo regression 36/36 green.

### Delivery Findings (verify)
- **Improvement** (non-blocking): `resolve_session_id_or_404` helper would dedupe the
  slug→404 pattern across 5 REST endpoints. Affects `sidequest/server/rest.py`
  (good standalone chore). *Found by TEA during test verification.*

**Handoff:** To Reviewer for code review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; 21/21 tests GREEN; lint clean on story files | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — assessed manually (see [EDGE]) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — assessed manually (see [SILENT]) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — assessed manually (see [TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed manually (see [DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed manually (see [TYPE]) |
| 7 | reviewer-security | Yes | findings | 6 (all med/low) | confirmed 6 (all downgraded to LOW), dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — verify-phase simplify already applied 2 fixes (see [SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — assessed manually (see [RULE]) |

**All received:** Yes (2 enabled returned; 7 disabled via workflow.reviewer_subagents)
**Total findings:** 6 confirmed (all LOW, non-blocking), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** daemon render reply `r2_key` → `_run_render_inner` (asset_type from key `<kind>` segment, entity_ref from params) → `PgSaveRepository.append_asset_ledger` → `asset_ledger` row (parameterized, session-scoped) → `GET /api/sessions/{slug}/assets` resolves each row to a CDN `url` → `useAssetPreload` fetches on reconnect edge. Safe: every DB query is parameterized and carries `session_id = %s`; the endpoint 404s on unknown slug; no cross-session read path.

**Pattern observed:** `PgAssetLedgerStore` faithfully mirrors `PgScrapbookStore` (session_tx writes, pooled reads, session_id predicate) — `sidequest/game/pg/asset_ledger.py`. Good consistency with the ADR-115 pg-store family.

**Error handling:** render-path ledger write wrapped in try/except that logs `error` + emits `op=write_failed` watcher event (loud, not swallowed) and deliberately does not fail image delivery — `websocket_session_handler.py:3050`. Justified `noqa: BLE001` with comment.

### Observations (subagent findings tagged + manual coverage for disabled lanes)

- **[SEC]** 6 findings, all confirmed at **LOW**: (a) 404 echoes slug — matches 3 pre-existing sibling endpoints, codebase convention; (b) public unauth endpoint — entire REST surface is unauth by design (LAN server, trusted playgroup); (c) `encodeURIComponent(slug)` missing in the hook — cheap hardening, folds into AC5 follow-up; (d) UI soft-fail logs to console (not silent); (e) asset_type `or ""` fallback — see [SILENT]/[RULE]; (f) entity_ref in OTEL — watcher is a localhost GM tool, names in the GM panel are the intended operator view, not PII leakage.
- **[SILENT]** (lane disabled — manual): render-hook `except` logs+emits a watcher event (not silent); UI `!resp.ok` path logs via `console.error` then soft-returns — acceptable for a best-effort preload. The `asset_type = … else params.get("tier") or ""` fallback is the one genuine silent-fallback smell — see [RULE]. **[LOW]**
- **[EDGE]** (disabled — manual): boundaries covered by tests — unknown slug→404, known-session-no-assets→`[]`, no-`r2_key`→no write, reconnect rising edge, idempotent re-write, cross-session isolation, FK/PK violations. No unhandled path found.
- **[TEST]** (disabled — manual): 21 tests incl. the mandatory production-path wiring test (`test_render_with_r2_key_writes_asset_ledger` drives `_run_render_inner`). Two RED-vacuous tests (404, no-write) noted by TEA — valid GREEN guards. Assertions check values, not truthiness. Good.
- **[DOC]** (disabled — manual): docstrings present + accurate on the store, endpoint, hook; the no-hasattr rationale is commented. **[LOW]** stale: `epic-65.yaml` 65-2 *description* still carries the pre-reconciliation prose (SqliteStore/daemon_client/md5) — it's the original story text, not code; the context-story doc + deviations are authoritative. Non-blocking.
- **[TYPE]** (disabled — manual): `SaveRepository` Protocol surface extended honestly (`session_id` property, `append_asset_ledger`, `list_asset_ledger`); `PgSaveRepository` satisfies it; pyright adds 0 new errors. `list_assets() -> list[dict]` is loosely typed but matches the codebase's pg-store return convention. **[LOW]**
- **[SIMPLE]** (disabled — manual): verify-phase simplify already applied 2 fixes (CDN url resolution, dead hasattr-guard removal). The render-hook block is linear and readable. No over-engineering.
- **[RULE]** (disabled — manual): python.md #11 parameterized SQL — ✓ all 4 queries; #1 no silent swallow — render-hook except is loud (✓); OTEL principle — `asset_ledger.write` watcher event present (✓); **No-Silent-Fallbacks `<critical>`** — the asset_type `… or ""` fallback is a CONFIRMED rule-matching finding, downgraded to **[LOW]** because the branch is unreachable with the real daemon (`upload_artifact` always emits a 5-segment key) and the tier-fallback is a documented Architect/Dev design choice. Recommend tightening (raise/skip-loud on a truly-unparseable key) as a fast-follow.

### Rule Compliance

| Rule (python.md / CLAUDE.md) | Instances checked | Verdict |
|---|---|---|
| #11 Parameterized SQL (no f-string) | append INSERT, list_assets SELECT, resolve_session_id, ensure_session | Compliant (all `%s`) |
| #11 Input validation at boundary | REST slug → resolve_session_id → 404 | Compliant |
| #1 No silent exception swallow | render-hook except (logs error + watcher event) | Compliant |
| No-Silent-Fallbacks `<critical>` | asset_type key-parse fallback | LOW finding (unreachable branch; documented) — confirmed, not dismissed |
| OTEL: subsystem decision emits span | `asset_ledger` write/write_failed watcher events | Compliant |
| Session isolation (session_id predicate) | append, list_assets, REST resolution | Compliant |
| Durable retention (no reaping) | no timer/TTL on ledger keys | Compliant |

### Devil's Advocate

Suppose this is broken. A malicious or confused caller hits `GET /api/sessions/<guess>/assets`: the endpoint is public and unauthenticated, so a slug-guesser learns a session's r2_keys (which encode world/session/kind/sha) and entity_refs (character/NPC names). Is that a breach? For a LAN game server with a trusted playgroup it is the same exposure as every sibling REST endpoint (encounter_events, games/{slug}) — consistent, deliberate, and the slug is high-entropy (date+world+mode). Not a new hole. A confused dev mounting the hook later passes a slug with a slash — `encodeURIComponent` is absent, so the fetch could land on a different same-origin route; mitigated because FastAPI `{slug}` won't match `/`, and the server resolves via DB lookup not filesystem. The daemon could send a malformed `r2_key`: asset_type then silently becomes the tier or `""` — a real data-quality smell, but `upload_artifact` provably emits the 5-segment artifact key, so the bad branch is dead today. A stressed DB: `session_tx` takes a per-session row lock and commits on clean exit; a write failure logs + emits + does not lose the image (correct priority — the player still sees their art). Race: two renders for the same r2_key upsert idempotently. The UI hook fired twice on a flapping connection: the rising-edge ref (`!wasConnected.current`) collapses it to one fetch per reconnect. Nothing here corrupts state or loses the player's image. The worst real outcome is an unlabeled ledger row on a daemon contract violation that cannot occur with current code. No Critical/High surfaces.

### Deviation Audit

(See `### Reviewer (audit)` under Design Deviations.)

**Handoff:** To SM for finish-story.

### Reviewer (audit)
All logged deviations reviewed and stamped:
- **TEA: AC6 has no RED test (descoped)** → ✓ ACCEPTED — AC6 is incoherent against disjoint R2 namespaces (Architect-verified); correctly deferred.
- **TEA: two RED-vacuous tests** → ✓ ACCEPTED — both remain meaningful GREEN guards; agrees with author reasoning.
- **Architect: drop md5/size_bytes; daemon out of scope** → ✓ ACCEPTED — sha256 is provably embedded in `r2_key` (`upload_artifact`, r2_writer.py:91); avoiding a redundant hash + in-flux daemon code is sound.
- **Architect: AC6 deferred to follow-up** → ✓ ACCEPTED — disjoint namespaces + no R2-listing capability; cannot be built as a 65-1 extension.
- **Architect: repos reduced to server+ui** → ✓ ACCEPTED — consequence of the above; branches retired cleanly.
- **Dev: asset_type from r2_key `<kind>` segment** → ✓ ACCEPTED — key segment is ground truth; tier fallback documented (note: tighten the `or ""` tail — see LOW finding).
- **Dev: test-fixture per-test-unique r2_keys** → ✓ ACCEPTED — correct; global PK + shared session-scoped test DB required it; no assertion weakened.
- **Dev: SaveRepository Protocol gained session_id + ledger methods** → ✓ ACCEPTED — honest Protocol surface; satisfied by PgSaveRepository.
- **Dev: AC5 app-wiring split to follow-up** → ✓ ACCEPTED — Doctor-approved (2026-05-27); ImageBus pure-reducer feed is a genuine separate design. SM must file the follow-up.

### Reviewer (code review)
- **Improvement** (non-blocking): Tighten asset_type derivation — raise/skip-loud on an r2_key that doesn't match `artifacts/<world>/<session>/<kind>/<sha>.<ext>` instead of falling back to `tier or ""`. Affects `sidequest/server/websocket_session_handler.py` (~line 3043). Unreachable with the current daemon; matches the No-Silent-Fallbacks rule. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Add `encodeURIComponent(slug)` + an `onError` callback to `useAssetPreload`; fold into the AC5 app-wiring follow-up. Affects `sidequest-ui/src/hooks/useAssetPreload.ts`. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `epic-65.yaml` 65-2 *description* still carries pre-reconciliation prose (SqliteStore/daemon_client/md5/AC6); the context-story doc + deviations are authoritative, but the stale epic text could mislead. Affects `sprint/epic-65.yaml`. *Found by Reviewer during code review.*
- **Reminder** (non-blocking): SM to file the AC5 app-wiring follow-up story ("Mount useAssetPreload in App + ImageBus preload feed, with wiring test; include encodeURIComponent + onError"). *Found by Reviewer during code review.*
