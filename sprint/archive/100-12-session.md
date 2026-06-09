---
story_id: "100-12"
jira_key: ""
epic: "100"
workflow: "tdd"
---
# Story 100-12: Phase 4 — Cutover: flip /reference/* to SPA, retire Python HTML emitters + islands.js, keep reference_visibility.py feeding the API

## Story Details
- **ID:** 100-12
- **Jira Key:** (none — SideQuest is Jira-free)
- **Workflow:** tdd
- **Type:** refactor
- **Points:** 5
- **Priority:** p2
- **Repos:** sidequest-server, sidequest-ui (TWO repositories → TWO PRs at finish)
- **Stack Parent:** none (final story of epic 100)

## Story Context

This is the FINAL Phase 4 story of epic 100 (Reference pages → React SPA migration). It completes the cutover from server-rendered HTML (/reference/* pages, islands.js) to a pure React SPA, while retaining reference_visibility.py as the server-side JSON projection API feeding the client.

**Key architectural constraints (from epic spec and ADR-135 amendment):**
- Server no longer emits HTML for /reference/* routes — only JSON projections (GET /reference/api/lore/{pack}/{world} and /reference/api/rules/{pack})
- React SPA handles all /reference/* client rendering (session-free routes)
- reference_visibility.py firewall remains the sole keeper-field projection gate (C1 — no keeper field crosses JSON boundary)
- Theme tokens delivered via projection JSON → CSS-var injector (C3 — session-free)
- **Deferred 100-9 finding:** wire useThemeTokens(data?.theme) into ReferenceRulesPage (currently only ReferenceLorePage is themed; /reference/rules/* renders unthemed — fold this in as part of cutover)

**Builds on:**
- Phase 1 (100-2…100-7): Server projections + firewall + theme tokens JSON
- Phase 2 (100-8, 100-9): React reference shell + session-free theme injector
- Phase 3 (100-10, 100-11): Shared d3-dag map component + React section components (POI, Cast, Timeline)

**Spec:** docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-09T07:27:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-09T07:27:00Z | - | - |

## Repos and Branches

### sidequest-server
- **Branch:** feat/100-12-reference-spa-cutover (off develop)
- **Tasks:**
  - Retire Python HTML emitters for /reference/* routes (reference_lore.py HTML templates, reference_rules.py HTML templates, islands.js integration)
  - Keep reference_visibility.py feeding the JSON API — ensure GET /reference/api/lore/{pack}/{world} and /reference/api/rules/{pack} remain operational
  - Verify /reference/* routes now redirect to or serve the React SPA (no server-rendered HTML)
  - OTEL spans for reference API endpoints (GM panel visibility)
  - Tests: pytest (SIDEQUEST_DATABASE_URL + SIDEQUEST_GENRE_PACKS environment variables required)

### sidequest-ui
- **Branch:** feat/100-12-reference-spa-cutover (off develop)
- **Tasks:**
  - Ensure React /reference/* SPA is the live target for /reference/* routes
  - **Fold in 100-9 finding:** Wire useThemeTokens(data?.theme) into ReferenceRulesPage (currently only ReferenceLorePage is themed; /reference/rules/* must also apply theme tokens)
  - Verify all section components (POI, Cast, Timeline) render with theme applied
  - Tests: just client-test / client-lint / client-build
  - Known baseline noise (NOT this story; filed 97-7/97-8):
    - UI client-build RED from 73-4/97-3 ConfrontationOverlay.beatimpact.test.tsx
    - lobby-start-ws-open.test.tsx flaky
    - Baseline-diff these on the UI side before attributing failures to this work

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Gap** (non-blocking): pre-existing xdist shared-manifest-path race in `tests/server/test_reference_poi_projection.py`. The fixture (`_world_dir_with_poi`) writes `r2_manifest.json` to `tmp_path.parent.parent` — the *session-shared* pytest base dir, not a per-test path — so parallel workers race on one file and 3 tests flake under `-n auto`. Passes 100% serially (`-n0`). Affects `sidequest-server/tests/server/test_reference_poi_projection.py` (write the manifest under a per-test subdir). *Found by Dev during implementation — NOT introduced by this story; the cutover's file deletions reshuffled the xdist work distribution and exposed the latent race.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Kept `load_poi_image_slugs` in reference_renderer (handoff keep-list omitted it)**
  - Spec source: handoff-red.md "Surviving seam" + team-lead GREEN brief keep-list
  - Spec text: keep-list named 11 renderer symbols (EXCLUDED_FILES, …, load_points_of_interest)
  - Implementation: also kept `load_poi_image_slugs` (+ its dep `load_r2_manifest_keys`)
  - Rationale: `websocket_handlers/map_emit.py:511` imports `load_poi_image_slugs` from the renderer — deleting it would break a live non-reference consumer. Verified via grep before trimming.
  - Severity: minor
  - Forward impact: none — correct keep-set; no consumer broken.
- **Deleted the `/reference/static/*` route + presenters.css/styles.css/theme.css (TEA flagged as open question)**
  - Spec source: handoff-red.md Open Questions
  - Spec text: "Static CSS … + the /reference/static route are orphaned post-cutover … Delete unless prod still links them — confirm before deleting theme.css"
  - Implementation: deleted all three CSS + islands.js + the static route. Confirmed via grep that the only linker was the now-deleted HTML chrome; the in-game ADR-079 path uses a *separate* `client_theme.css` over the WebSocket `theme_css` channel (different file, different delivery), untouched.
  - Rationale: No surviving consumer ⇒ dead code ⇒ delete in the same PR.
  - Severity: minor
  - Forward impact: none.
- **Repointed `test_reference_routes.py` resolver tests to the JSON API; rewrote smoke + theme tests rather than only deleting**
  - Spec source: team-lead GREEN brief ("delete/repoint stale tests")
  - Spec text: listed specific HTML route tests to delete
  - Implementation: deleted the HTML-emitter cases but **repointed** the surviving shared-resolver coverage (404-with-valid-list, path-traversal, no-search-paths-500, missing-root-404) onto `/reference/api/*`; repointed the live-pack smoke leak guard onto the JSON API (keeper-stem section guard); trimmed only the `_wrap_document` block from `test_reference_theme.py` (kept the `load_reference_theme` loud-failure loader contract).
  - Rationale: the resolver, the firewall-on-live-content, and the theme loader all SURVIVE the cutover; preserve their coverage instead of dropping it.
  - Severity: minor
  - Forward impact: none.
- **Added `test_reference_manifest_gate_span.py` (new file) to preserve OTEL coverage**
  - Spec source: CLAUDE.md OTEL Observability Principle
  - Spec text: "every subsystem decision emits a span … the GM panel is the lie detector"
  - Implementation: the only coverage of the live `sidequest.reference.manifest_loaded` span lived in the deleted HTML-path gate tests. Added a focused file that re-pins the span (name/attrs/flat-only) and asserts it fires once through the surviving `_gate_poi_slugs_on_manifest` (which `build_lore_projection` still calls).
  - Rationale: never drop observability coverage of a surviving subsystem during a deletion.
  - Severity: minor
  - Forward impact: none.

### TEA (test design)
- **C5 open question resolved toward history-fallback (not redirect).** The spec
  leaves "FastAPI serves SPA index for /reference/* (history-fallback)" vs
  "redirect-to-SPA-host" open. RED tests pin the **history-fallback**: with `ui_dist`
  injected, `GET /reference/rules|lore/*` returns the SPA shell (status 200, index.html
  body). Rationale: FastAPI ALREADY has `_install_spa_fallback` (app.py:460) — a catch-all
  `@app.get("/{full_path:path}")` registered LAST that serves index.html for unclaimed
  GETs. Removing the HTML routes makes /reference/* fall through to it for free; no new
  redirect code. If prod topology forces redirect instead, this is the deviation to flag.

## TEA Assessment

**Tests Required:** Yes (RED phase, two repos)

**Test Files:**
- `sidequest-server/tests/server/test_100_12_reference_spa_cutover.py` — 9 tests:
  5 RED (cutover work) + 4 GREEN (surviving-contract safety net).
- `sidequest-ui/src/screens/reference/__tests__/ReferenceRulesPage.theme.test.tsx` —
  2 RED (RulesPage theme-injector wiring; deferred 100-9 finding).

**Tests Written:** 11 (7 genuinely RED + 4 GREEN regression safety-net).
**Status:** RED confirmed in BOTH repos.

**Server (5 RED / 4 GREEN-guard):**
- RED (a) `/reference/rules/*` + `/reference/lore/*` serve the SPA shell, not server HTML.
- RED (b) `assemble_rules_page`/`assemble_lore_page` retired; `islands.js` bundle gone
  (file + no-longer-served).
- GREEN-guard (c) JSON API (`/reference/api/lore|rules/*`) + `reference_visibility.py`
  firewall survive; keeper NPC absent from both projections. **Load-bearing safety net —
  these stay GREEN through the cutover; if one goes RED, the cutover broke the firewall.**

**UI (2 RED):**
- `ReferenceRulesPage` applies `useThemeTokens(data?.theme)` to `:root` (no WebSocket),
  and cleans up on unmount — mirroring `ReferenceLorePage`. `RulesProjection.theme` and
  server attach already exist; only the page wiring is missing.

**SURVIVING SEAM — Dev must NOT delete these modules wholesale.** The surviving API
serializer `reference_projection.py` imports loaders/helpers from the trimmed modules
(reference_projection.py:21-47):
- `reference_renderer`: `EXCLUDED_FILES`, `LORE_WORLD_FILES`, `RULES_FILES`,
  `_cast_entry_is_projectable`, `_gate_cast_slugs_on_manifest`, `_gate_poi_slugs_on_manifest`,
  `_humanize_label`, `_is_devnote`, `load_cast_entries`, `load_poi_slug_map`,
  `load_points_of_interest` — **KEEP**. Delete only HTML assembly (`assemble_*_page`,
  `render_node`/`_render_dict`/`_render_list`/`_wrap_document`/`_build_toc`/`_build_hero`/
  the `<style>`/`<script>` chrome).
- `reference_presenters`: `cast_portrait_slug`, `poi_image_key`, `portrait_image_key` —
  **KEEP**. Delete the `present_*` / `lookup_presenter` HTML emitters.
- `reference_map`: `_edges_and_dangling`, `_npc_pins`, `load_cartography_config` — **KEEP**.
  Delete the SVG emit (`present_lore_map`).
- `reference_timeline`: `_temporal_of`, `_year_key`, `load_legends`, `load_lore_history` —
  **KEEP**. Delete the HTML emit (`present_lore_timeline`).

**Static tree:** `sidequest/server/static/reference/` holds `islands.js`, `presenters.css`,
`styles.css`, `theme.css`. islands.js is RED-guarded as deleted. The CSS files + the
`/reference/static/{filename}` route are now orphaned once HTML chrome is gone (the SPA
carries its own styles + theme via JSON) — Dev's call to delete; no surviving consumer.

**OLD-behavior tests Dev must delete/repoint in GREEN** (they pin retired HTML):
- `tests/server/test_reference_islands.py` — DELETE whole file (islands.js + lightbox +
  islands `<script>` tag in chrome).
- `tests/server/test_reference_routes.py` — the HTML-asserting cases (`test_rules_route_returns_html`,
  `test_rules_route_excludes_npcs`, `test_lore_route_returns_html`,
  `test_reference_router_registered_in_real_app` (asserts "sleuth" in HTML),
  `test_stylesheet_route_serves_theme_css`, `test_missing_theme_field_returns_500` via HTML
  route) — delete or repoint to the JSON API. 404 / path-traversal cases may move to API routes.
- Any `test_reference_{renderer,presenters,chrome,map,timeline,render_wiring,anchors}*`
  case that asserts on emitted HTML strings (not loaders/data-shaping) — repoint or delete.
  Run the full `tests/server/test_reference_*` suite after retiring emitters; every failure
  is either a test pinning deleted HTML (fix it) or a real regression (the safety net catches that).

**Handoff:** To Dev for GREEN (task #2).

## Dev Assessment

**Implementation Complete:** Yes (both repos)

**Files Changed:**

_sidequest-server_
- `sidequest/server/reference_routes.py` — deleted the two HTML routes (rules_page, lore_page) + the `/reference/static/{filename}` route; kept the JSON API (`/api/lore`, `/api/rules`) + shared resolver. `/reference/*` now falls through to the SPA history-fallback (C5).
- `sidequest/server/reference_renderer.py` — trimmed to data loaders only (EXCLUDED_FILES/LORE_WORLD_FILES/RULES_FILES, `_humanize_label`, `_is_devnote`, POI/Cast loaders + R2-manifest gates, `load_poi_image_slugs`). Deleted `assemble_rules_page`/`assemble_lore_page` + the entire render/TOC/hero/chrome/scroll-spy HTML chain.
- `sidequest/server/reference_presenters.py` — trimmed to `poi_image_key`/`portrait_image_key`/`cast_portrait_slug`; deleted the `PresenterContext` dispatch, `PRESENTERS` registry, `lookup_presenter`, and every `present_*` emitter.
- `sidequest/server/reference_map.py` — kept `load_cartography_config`/`_edges_and_dangling`/`_npc_pins`; deleted `present_lore_map` (SVG) + layout helpers.
- `sidequest/server/reference_timeline.py` — kept `load_legends`/`load_lore_history`/`_temporal_of`/`_year_key`; deleted `present_lore_timeline` (HTML) + `_Entry`.
- Deleted `sidequest/server/static/reference/{islands.js,presenters.css,styles.css,theme.css}` (dir now empty).
- Tests: deleted 17 HTML-pinning files; rewrote `test_reference_routes.py` (resolver→API) + `test_reference_smoke.py` (live→API leak guard); trimmed `_wrap_document` block from `test_reference_theme.py`; added `test_reference_manifest_gate_span.py` (preserves the live `manifest_loaded` OTEL span coverage).

_sidequest-ui_
- `src/screens/reference/ReferenceRulesPage.tsx` — wired `useThemeTokens(data?.theme)` (100-9 deferred finding), mirroring ReferenceLorePage (same hook, same unmount cleanup).

**Tests:**
- SERVER: `tests/server/test_reference_*` + `test_100_12_reference_spa_cutover` = **203 passed, 1 skipped** (serial `-n0`). TEA's 7 RED → GREEN; 4-test safety net stays GREEN (JSON API + firewall survive). Repo-wide collection clean (11458 tests, 0 import errors). ruff check + format clean. NOTE: under `-n auto`, 3 `test_reference_poi_projection.py` tests flake on a **pre-existing** xdist shared-manifest-path race (logged as a Delivery Finding) — green serially, not introduced here.
- UI: full vitest **1992 passed, 1 failed** — the 1 failure is the known-flaky `lobby-start-ws-open.test.tsx` (97-7/97-8 baseline). Reference UI suite 54/54 green. Lint 0 errors. Build RED is the documented `ConfrontationOverlay.beatimpact.test.tsx` TS2322 baseline (97-3/97-7) — zero new errors, none in any reference file.

**Branch:** feat/100-12-reference-spa-cutover (both repos, pushed)

**Handoff:** To Reviewer (task #3).

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** `/reference/rules|lore/{pack}` HTML route DELETED → falls through to pre-existing SPA history-fallback catch-all (`_install_spa_fallback`, app.py) → React Router. `/reference/api/{rules,lore}` JSON retained → `build_*_projection` → `reference_visibility.classify()` + `EXCLUDED_FILES` + `_cast_entry_is_projectable` firewall (untouched verbatim) → public-only JSON. UI `ReferenceRulesPage` fetches API → `useThemeTokens(data?.theme)` injects `:root` CSS vars (session-free, no WS).
**Surviving contract:** firewall NOT in diff (verbatim); API + classify() carve tests (`test_reference_visibility`, `test_visibility_classifier`, all `*_projection.py`) untouched/green.
**Deviations verified:** (3a) `load_poi_image_slugs` genuinely consumed by `map_emit.py:524` (in-game path) — correctly retained, not dead. (3b) `test_reference_manifest_gate_span.py` invokes the real surviving gate end-to-end via `otel_capture`, asserts the span fires once with census attrs — real OTEL coverage. (3c) repointed routes/smoke/theme tests not defanged; smoke leak guard strengthened to structural `section_ids & KEEPER_STEMS`.
**Orphans:** ZERO both repos — deleted emitter fn names appear only in docstrings; `theme_css` hits are the separate in-game ADR-079 WS channel.
**Gates:** SERVER full `tests/server/` xdist 2709 passed / 501 skip / 0 failed. UI vitest 1992 passed / 1 failed (97-8 lobby-ws flake, baseline) / lint 0 errors / build RED ×5 (97-7 ConfrontationOverlay, baseline) — both NOT in PR diff (provenance-attributed, no develop checkout).
**Observations (5+):** (1) HTML+static routes cleanly removed, API intact. (2) Firewall verbatim + fully wired into surviving projection. (3) All 4 trimmed modules retain only data-layer fns, each with a live consumer (no dead files). (4) Both new tests + UI theme test non-vacuous (fail on develop). (5) C2 no-session + C3 session-free WS-absence asserted in UI test. (6) [LOW, non-blocking] skipped `test_rules_route_against_live_tea_and_murder` still references the deleted `/reference/rules` HTML route + asserts `text/html`; epic-94 skip now moot since the route is gone — candidate for deletion in a follow-up.

**Handoff:** APPROVED — merging both PRs (#363 ui, #777 server).
