---
story_id: "63-8"
jira_key: ""
epic: "63"
workflow: "tdd"
---

# Story 63-8: Lore page POI images — render location landscape from R2 with cartography anchor

## Story Details
- **ID:** 63-8
- **Jira Key:** None (no Jira in this project)
- **Workflow:** tdd
- **Stack Parent:** none (stack root)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-25T22:29:15Z
**Round-Trip Count:** 1

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-25T19:24:35Z | 2026-05-25T21:44:59Z | 2h 20m |
| red | 2026-05-25T21:44:59Z | 2026-05-25T22:01:43Z | 16m 44s |
| green | 2026-05-25T22:01:43Z | 2026-05-25T22:09:57Z | 8m 14s |
| spec-check | 2026-05-25T22:09:57Z | 2026-05-25T22:11:04Z | 1m 7s |
| verify | 2026-05-25T22:11:04Z | 2026-05-25T22:14:04Z | 3m |
| review | 2026-05-25T22:14:04Z | 2026-05-25T22:20:30Z | 6m 26s |
| green | 2026-05-25T22:20:30Z | 2026-05-25T22:23:17Z | 2m 47s |
| spec-check | 2026-05-25T22:23:17Z | 2026-05-25T22:23:52Z | 35s |
| verify | 2026-05-25T22:23:52Z | 2026-05-25T22:24:53Z | 1m 1s |
| review | 2026-05-25T22:24:53Z | 2026-05-25T22:28:25Z | 3m 32s |
| spec-reconcile | 2026-05-25T22:28:25Z | 2026-05-25T22:29:15Z | 50s |
| finish | 2026-05-25T22:29:15Z | - | - |

## Story Context

The /reference/lore/<pack>/<world> pages currently render location text from cartography.yaml but show no images. Every world now has POI landscape PNGs in R2 at cdn.slabgorb.com/genre_packs/<pack>/worlds/<world>/assets/poi/<slug>.png.

### Work Breakdown

**Server (sidequest-server/sidequest/reference_renderer.py):**
- For each region in cartography.yaml, look up the matching POI slug from history.yaml points_of_interest[].slug
- Emit an <img> tag with src=cdn.slabgorb.com/genre_packs/... inside the location-<slug> anchor section
- Graceful degradation: if no POI image exists for a region, render text only (no broken image, no placeholder)

**Content (sidequest-content):**
- Verify slug consistency: cartography region keys must match history.yaml POI slugs for image lookup
- Add to pf-validate-locations (story 54-3) a check that every cartography region with a matching POI slug has an R2 image

**Visual:**
- Image renders at content width inside the location section, below the region name, above the description text
- Respect per-world visual_style.yaml palette (border/shadow tint from world's accent color)

## Acceptance Criteria

- [x] reference_renderer.py looks up POI slugs from history.yaml for each cartography region
- [x] <img> tags emitted with correct R2 URLs (cdn.slabgorb.com/genre_packs/...)
- [x] No broken image fallback; text-only display if image missing
- [x] Image renders at content width, positioned below region name, above description
- [x] Visual styling respects world's visual_style.yaml accent color for border/shadow
- [~] pf-validate-locations enhanced with slug consistency check (slug consistency ✓, R2-object existence deferred per Architect decision)
- [x] Server and content tests passing; no OTEL emits missing for image resolution failures

## Sm Assessment

**Scope:** Two repos — `server` (reference_renderer.py emits POI `<img>` tags) and `content` (slug consistency + pf-validate-locations check). Both branched `feat/63-8-lore-page-poi-images` off develop. 2pt, tdd, p2.

**Core risk for TEA/Dev — the join key:** the whole feature hinges on cartography.yaml region keys matching history.yaml `points_of_interest[].slug`. That lookup is where this breaks. Tests must cover the match, the no-match (text-only), and slug drift.

**Project landmines (read before writing tests):**
- **No content-coupled tests.** Do NOT write pytest that loads live `genre_packs/*` and asserts a POI image exists. The triad is: FIXTURES for server unit tests (synthetic cartography+history+visual_style), VALIDATORS for the live worlds (the pf-validate-locations enhancement IS the content-team surface), never direct unit tests on live pack output.
- **OTEL on the resolution decision.** Per the OTEL principle, the slug→image lookup is a subsystem decision and must emit a span (resolved / not-found) so the GM panel can verify the renderer actually ran the lookup vs. rendered nothing. "Image missing → render text only" is legitimate display degradation (POI images are genuinely optional), NOT a silent fallback — but it must be *observable*, not silent. Don't dress it up as an ERROR either; missing POI art is expected.
- **Reference pages are server-rendered** at request time by reference_renderer.py walking YAML — not a static site/SPA. The `<img>` src points at R2 (cdn.slabgorb.com), consistent with the images-to-R2 convention; no PNGs enter the repo.

**Routing:** Phased tdd → handing to TEA (Radar) for RED. TEA owns the failing tests; I do not plan the implementation.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes

**Test Files:**
- `sidequest-server/tests/server/test_reference_poi_images.py` — presenter behaviour (img emitted iff slug in `poi_image_slugs`; text-only otherwise; exact R2 URL via `resolve_asset_url`; placement below title/above body; per-pack accent border), presenter-fires-spans via the `otel_capture` real exporter, span-helper constants/attrs/flat-only registration, and an HTTP-route wiring test against the new `poi_fixture` world.
- `sidequest-server/tests/server/test_validate_locations_poi_images.py` — `pf-validate-locations` flags a dangling history POI slug (`poi_orphan_fixture`) and stays clean on a matched slug (`poi_fixture`).
- New fixtures: `reference_v2_fixture/worlds/poi_fixture/{world,locations,history}.yaml` and `.../poi_orphan_fixture/{world,locations,history}.yaml`.

**Tests Written:** 13 tests covering all 7 ACs.
**Status:** RED (verified) — 12 fail on unimplemented feature, 1 negative-case validator test passes (silent today; guards against over-flagging post-impl). Existing reference suite (integration/otel/presenters) still green: 67 passed.

**RED failure breakdown (all unimplemented-feature, no test-authoring bugs):**
- 6× `TypeError: PresenterContext.__init__() got an unexpected keyword 'poi_image_slugs'` — field not yet added.
- 4× `ImportError` — `SPAN_REFERENCE_POI_IMAGE_{RESOLVED,NOT_FOUND}` + helpers not yet defined.
- 1× `AssertionError: POI image missing` — `present_lore_geography` not yet emitting `<img>`.
- 1× `AssertionError: validator should flag the history POI slug` — validator not yet reading history.yaml.

### Rule Coverage

| Rule (source) | Test(s) | Status |
|------|---------|--------|
| OTEL on every subsystem decision (CLAUDE.md / SOUL Illusionism detector) | `test_presenter_fires_resolved_and_not_found_spans`, `test_poi_*_span_helper_emits_attrs`, `test_poi_spans_registered_in_flat_only_set` | RED |
| No silent fallbacks — text-only path must be *observable* not silent (CLAUDE.md) | `test_presenter_fires_resolved_and_not_found_spans` (not_found span fires for the un-imaged card) | RED |
| No content-coupled tests — fixtures + validator, never live packs (memory) | all tests use `reference_v2_fixture` + synthetic ctx; validator test is fixture-driven | RED |
| No source-text wiring tests — drive flow, assert behaviour/spans (CLAUDE.md) | HTTP-route wiring test + `otel_capture` span assertions; zero `read_text()` grep-asserts | RED |
| Reuse infra, don't reinvent — R2 URL via `resolve_asset_url` (CLAUDE.md) | `test_image_src_uses_resolve_asset_url` (asserts equality to `resolve_asset_url(...)`) | RED |
| python lang-review §test-quality (no vacuous asserts, no bare truthy checks, mock at use-site) | every test asserts specific values; spans asserted via real exporter not mis-targeted patch | RED |
| python lang-review §type-annotations (return types) | all test fns annotated `-> None` | n/a (passes lint) |

**Rules checked:** 7 of 7 applicable lang-review/project rules have coverage (async/resource-leak/path-handling categories N/A to a synchronous HTML-presenter feature).
**Self-check:** 0 vacuous tests. The one currently-passing test (`test_validator_clean_when_poi_slug_matches_location`) is a real negative-case assertion (matched slug must not error), not vacuous — it stays meaningful after implementation.

**Handoff:** To Dev for implementation.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-server):**
- `sidequest/telemetry/spans/reference.py` — `SPAN_REFERENCE_POI_IMAGE_RESOLVED` / `_NOT_FOUND` constants, FLAT_ONLY_SPANS registration, `reference_poi_image_resolved_span` / `reference_poi_image_not_found_span` helpers (pack/world/slug attrs).
- `sidequest/server/reference_presenters.py` — `PresenterContext.poi_image_slugs: frozenset[str]` field; `_poi_image_html` helper; `present_lore_geography` emits the R2 `<img>` (below title, above body, per-pack accent border) iff slug ∈ set, fires resolved/not_found spans.
- `sidequest/server/reference_renderer.py` — thread `poi_image_slugs` through `_render_dict`/`_render_list` child contexts, `_render_file`, `_file_renders_by_stem`; new `_load_poi_image_slugs(world_dir)` reads history.yaml POI slugs (slugify-normalised); `assemble_lore_page` builds and passes the set.
- `sidequest/cli/validate/locations.py` — `_history_poi_slugs` / `_location_card_slugs` / `_check_poi_image_slugs`; `_validate_one_world` flags a history POI slug with no matching location card (`POI_IMAGE_SLUG_UNMATCHED`, warning).

**Tests:** 13/13 story tests passing (GREEN). Regression: reference integration/otel/presenters + materialized-validator suites all green (68 passed). `ruff check` + `ruff format` clean on the 4 changed files.
**Branch:** `feat/63-8-lore-page-poi-images` (pushed, both repos).

### Rework (round-trip 1 — reviewer findings)
- **[BLOCKING, resolved]** `palette_accent` now `html.escape()`'d before the `<img>` `style=` interpolation (reference_presenters.py:207) — closes the escaping-invariant break.
- **[LOW, resolved]** `ctx.world is None` branch now fires `reference_poi_image_not_found_span(world=None, slug=…)` before returning — no longer a silent skip.
- **[Improvement, deferred]** shared history.yaml POI-slug parser dedup (`_load_poi_image_slugs` vs `_history_poi_slugs`) — a refactor with a new-module placement decision, non-blocking; left as a logged follow-up rather than scope-creeping the rework. The two functions currently produce identical results (verified).
- Added regression test `test_image_accent_is_html_escaped`. Suite: 96 green; ruff clean.

**Handoff:** To Reviewer (re-review).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (13/13 story + 68 regression from Dev push; no code changed in verify)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (4 source + 2 test; YAML fixtures excluded)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding (medium) | history.yaml POI-slug parse duplicated across `_load_poi_image_slugs` (renderer) and `_history_poi_slugs` (validator) |
| simplify-quality | 1 high + 1 med + 2 low | high = pack-tier flavor files don't thread poi_image_slugs; med = lazy slugify import; low = naming, empty span bodies |
| simplify-efficiency | clean | frozenset threading is minimal/appropriate — not over-built |

**Applied:** 0 fixes.
**Dismissed (with rationale):**
- **[quality, HIGH] `_render_file_with_label` doesn't thread `poi_image_slugs` to pack-tier flavor files** — FALSE POSITIVE, not applied. POI landscape images are **world-tier** (the manifest is `world_dir/history.yaml`; assets live at `worlds/<world>/assets/poi/`). Pack-tier flavor files (`LORE_PACK_FLAVOR_FILES`: cultures/lore/history/factions, rendered with the `(genre)` label) describe genre-level content, not world POIs. The world-tier render path (`_render_file`, where `locations.yaml` and world `lore.yaml` flow) IS threaded correctly. Threading the world POI set into pack-tier rendering would risk a genre location whose slug coincidentally matches a world POI slug wrongly getting that world's image — a subtle bug, not a fix. Verified the world-tier path covers AC scope; pack-tier exclusion is correct by design.
- **[quality, LOW] empty `with span: pass` bodies** — correct per the established `sidequest.reference.*` span-helper pattern (all existing reference spans use `with ...: pass`); observability markers, not a smell.

**Flagged for Reviewer (medium — not auto-applied per verify policy):**
- **[reuse/quality, MEDIUM] Extract the shared history.yaml POI-slug parser.** `_load_poi_image_slugs` (reference_renderer.py) and `_history_poi_slugs` (cli/validate/locations.py) parse the identical schema (`chapters[].points_of_interest[].slug` + top-level) and slugify-normalise identically. This is the join the validator exists to police — if the two drift, the validator silently stops matching the renderer (the exact "validator says fine, image doesn't render" failure mode). Recommend extracting one shared helper (e.g. a small `reference_poi` module) that both import, so validate-time and render-time joins cannot diverge. Deferred to Reviewer because it's a cross-layer (cli→server) placement decision; both modules already share `reference_slug.slugify`, so the coupling precedent exists.
- **[quality, MEDIUM] lazy `slugify` imports in locations.py** — kept function-local deliberately to avoid a new cli→server module-load dependency; would fold naturally into the shared-helper extraction above. Noted for Reviewer's call.

**Quality Checks:** ruff check + ruff format clean on changed files (from green phase); suite green.
**Overall:** simplify: clean (0 applied, 1 high dismissed as false-positive with rationale, 2 medium flagged for Reviewer)
**Handoff:** To Reviewer for code review.

### Verify re-pass (round-trip 1)
Reviewer rework delta is 2 production lines (`escape(accent)`, `world-None` span) + 1 regression test, all reviewer-mandated and within the already-simplified `_poi_image_html`. No new complexity/duplication surface — full simplify fan-out not re-run for a defect-fix delta this small. Confirmed GREEN (65 passed across poi/validator/presenter/otel suites) + ruff check/format clean on all 4 source files. **Overall:** simplify: clean. Handoff: to Reviewer for re-review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with 3 logged Minor deviations — all sound)
**Mismatches Found:** 3 (all pre-logged by TEA/Dev; none require hand-back)

- **Cartography iteration → locations.yaml presenter** (Different behavior — Architectural, Minor)
  - Spec: "for each region in cartography.yaml ... emit `<img>` inside the location-<slug> anchor."
  - Code: image injected by `present_lore_geography` (renders `locations.yaml`/`lore.geography` as `location-{slug}` cards); cartography.yaml stays excluded. Gate is the history.yaml POI-slug set via `PresenterContext.poi_image_slugs`.
  - Recommendation: **A — update spec.** The code matches the real render pipeline; iterating cartography would mean un-excluding a spoiler/asset file and duplicating location rendering. Reuse-first: extended the existing dataclass + presenter, no new subsystem. Already logged (TEA D1).

- **Per-pack accent vs per-world visual_style.yaml** (Different behavior — Behavioral, Minor)
  - Spec: "border/shadow tint from the per-world visual_style.yaml accent color."
  - Code: uses `ReferenceTheme.palette_accent` (per-pack, already on `ctx.theme`).
  - Recommendation: **A — update spec.** visual_style.yaml is excluded image-gen config with no typed accent field; a per-world accent would need a new genre-model field (siblings are `extra=forbid`) — disproportionate for 2pts. Already logged (TEA D2 / Dev). Per-world accent is a clean follow-up.

- **AC-6 R2-object-existence half deferred** (Missing in code — Behavioral, Minor)
  - Spec: session AC-6 is "slug consistency check" (implemented ✓); the work-breakdown's "has an R2 image" half is not.
  - Code: `_check_poi_image_slugs` flags dangling history POI slugs (no matching location card). No R2 HEAD/local-mirror existence probe.
  - Recommendation: **D — defer.** The session-level AC (highest authority) is satisfied; the existence-probe mechanism is genuinely undecided (HEAD vs mirror vs manifest-is-truth). Logged as TEA question + Dev gap.

**Architectural notes:** Implementation is reuse-first and clean — `poi_image_slugs` threads through the existing `PresenterContext` (no new state object), the URL uses the existing `resolve_asset_url`, and the two new spans follow the established `sidequest.reference.*` flat-only pattern. The validator's slug normalization shares the renderer's `slugify`, so validate-time and render-time joins cannot diverge. No architectural concerns.

**Decision:** Proceed to review (verify). No hand-back to Dev.

**Re-spec-check (round-trip 1):** The reviewer rework (`html.escape` on accent, span on the world-None path, +1 regression test) is a defect fix, not a spec change — no new mismatches, deviations D1/D2 unchanged. Spec alignment still: Aligned. Proceed.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (13 story + 83 regression green, ruff clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — self-assessed below |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — self-assessed below |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — self-assessed below |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — self-assessed below |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — self-assessed below |
| 7 | reviewer-security | Yes | findings | 2 (1 Medium, 1 Low) | confirmed 2, dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — self-assessed below |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — self-assessed below |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents` settings)
**Total findings:** 2 confirmed, 0 dismissed, 0 deferred

**Round-trip 1 re-review (re-ran enabled subagents on the reworked branch):**
- reviewer-preflight — Received: Yes; clean (96 green, ruff check/format clean, 0 smells).
- reviewer-security — Received: Yes; both round-1 findings **RESOLVED** (high confidence), 0 new issues; src/alt still escaped, slug injection-safe, `yaml.safe_load` throughout.

## Reviewer Assessment

**Verdict:** REJECTED (round 1) → **RESOLVED in round-trip 1; final verdict APPROVED — see "Reviewer Assessment (re-review)" below.** (Both fixes localized to `_poi_image_html`.)

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM][SEC] | `palette_accent` interpolated **unescaped** into the `<img>` inline `style=` attribute, breaking the renderer's uniform `html.escape()` invariant. Not remotely exploitable today (theme.yaml is first-party trusted content), but a crafted accent (`#fff" onerror="…`) would break out of the attribute. The creator-authoring roadmap (pack content from less-trusted channels) turns this into a real stored-XSS. **Blocking by project rule** ("escape every interpolation") + "no we'll-fix-it-later" (CLAUDE.md) — the fix is one line, so it does not get deferred. | `sidequest/server/reference_presenters.py:210-211` | Wrap with `html.escape(accent)` in both the border and box-shadow interpolations. Optionally validate `palette_accent` against a CSS-color pattern in `load_reference_theme` so it fails loudly at pack-load. |
| [LOW][SEC] | `if ctx.world is None: return ""` early-returns with **no OTEL span** — a silent skip vs the no-silent-fallbacks rule. Path is effectively unreachable (geography only renders on lore pages where world is set), so it is dead-defensive code. | `sidequest/server/reference_presenters.py:201-202` | Recommended (not blocking on its own): either remove the unreachable guard, or fire an observable span before returning. Dev's call. |

**Data flow traced:** lore route → `assemble_lore_page` → `_load_poi_image_slugs(world_dir)` (history.yaml, `yaml.safe_load`) → `frozenset` threaded via `PresenterContext.poi_image_slugs` → `present_lore_geography` → `_poi_image_html` membership check `slug in ctx.poi_image_slugs` → `<img src=escape(resolve_asset_url(...))>`. The only interpolation that escapes the escaping discipline is `accent`.

**Dispatch-tag coverage:**
- `[SEC]` — security subagent: 2 findings confirmed (above). `src`/`alt` correctly escaped; slug path-injection-safe (slugify `[a-z0-9-]`); `yaml.safe_load` used throughout; not-found path is spanned (observable).
- `[EDGE]` (subagent disabled — self-assessed): boundary cases covered by tests — slug in set / not in set / empty set / locations.yaml as list vs `{locations: [...]}` dict; history.yaml absent → empty frozenset (early return). No unhandled boundary found.
- `[SILENT]` (disabled — self-assessed): the text-only path fires `poi_image_not_found` span (good); the **one** silent skip is the `ctx.world is None` return (flagged LOW above).
- `[TEST]` (disabled — self-assessed): 13 tests, all with concrete assertions; presenter spans asserted via real `otel_capture` exporter (not mocked-at-wrong-site); HTTP-route wiring test present. No vacuous assertions. **Gap:** no test asserts the accent is escaped — TEA should add it during rework.
- `[DOC]` (disabled — self-assessed): docstrings on `_poi_image_html`, `_load_poi_image_slugs`, `_check_poi_image_slugs` are accurate; no stale comments.
- `[TYPE]` (disabled — self-assessed): `poi_image_slugs: frozenset[str]` is correctly immutable; no stringly-typed leakage. Pre-existing pyright debt at line 895 (magic presenter) is untouched/out-of-scope (Dev finding).
- `[SIMPLE]` (disabled — self-assessed; verify-phase simplify already ran): frozenset threading is minimal; the only noted item is the `_history_poi_slugs`/`_load_poi_image_slugs` duplication (flagged to me by verify — see audit below).
- `[RULE]` (disabled — self-assessed): OTEL-on-decision ✓ (resolved/not_found spans, FLAT_ONLY registered); no-content-coupled-tests ✓ (fixtures only); images-to-R2 ✓ (`resolve_asset_url`, no PNG in tree); reuse-first ✓. **Violation:** escape-every-interpolation (accent) — the blocking finding.

### Rule Compliance

- **Escape every HTML interpolation (CLAUDE.md XSS):** `src` ✓ (line 209), `alt` ✓ (line 209), `accent` ✗ (lines 210-211) → REJECT.
- **No silent fallbacks (CLAUDE.md `<critical>`):** not-found path ✓ spanned; `world is None` path ✗ silent (LOW, dead path).
- **OTEL on every subsystem decision:** ✓ both outcomes spanned, both in `FLAT_ONLY_SPANS`, attrs carry pack/world/slug.
- **No content-coupled tests:** ✓ fixtures (`poi_fixture`/`poi_orphan_fixture`) + validator; no live-pack assertions.
- **Reuse, don't reinvent:** ✓ extended `PresenterContext`, reused `resolve_asset_url` + `slugify` + existing span pattern.
- **yaml.safe_load only:** ✓ both readers.

### Devil's Advocate

Assume this is broken. A malicious actor's only lever is pack content (theme.yaml / locations.yaml / history.yaml), since the route inputs (pack, world) are server-side directory names validated by the loader and the slug is `slugify`-clamped to `[a-z0-9-]` — no `../` escape into the R2 path. The live attack is the accent color: `palette_accent` flows raw into a `style=` attribute. Today the pack repo is first-party and gated behind Cloudflare Zero Trust, so the operator would have to attack themselves — not a real threat. But this project's own strategic memory says the customer is the *creator/DM* and the roadmap is creator-authored content and pack uploads (`prd-creator-authoring-monetization`). The day a pack arrives from a subscriber, `palette_accent` becomes attacker-controlled and this line is a stored XSS executing in the game origin (which holds the WebSocket session). `_require_str` only checks non-empty, so a malicious value sails through pack-load. That is precisely why the renderer escapes *everything else* — and why this one exception must not merge. A confused content author is a softer version of the same bug: a typo'd accent with a stray quote silently corrupts every location card on the page with no loud failure. Second angle: the `world is None` guard returns an empty string with no telemetry — if a future caller wires geography onto a worldless surface, images vanish with zero signal in the GM panel, exactly the "is it engaged or is Claude winging it?" blindness OTEL exists to prevent. Third angle: history/locations slug normalization lives in two functions that currently agree by luck of identical code; a future edit to one drifts the validator from the renderer silently — the validator would green-light a pack whose images never render. None of these are blast-radius-now, but two are one-line closes and the third is a flagged follow-up. Shipping the escape gap when the fix is `html.escape(accent)` violates "do X, don't say X and do Y."

**Handoff:** Back to Dev (via TEA — the accent-escape warrants a security regression test first).

## Reviewer Assessment (re-review — round-trip 1)

**Verdict:** APPROVED

| Round-1 finding | Status | Evidence |
|-----------------|--------|----------|
| [MEDIUM][SEC] unescaped `palette_accent` in `<img>` style= | ✅ RESOLVED | `accent = escape(ctx.theme.palette_accent)` (reference_presenters.py:213); a crafted `#fff" onerror=…` is escaped to `&quot;` and cannot break out. New regression test `test_image_accent_is_html_escaped` passes. |
| [LOW][SEC] silent `ctx.world is None` return | ✅ RESOLVED | branch now fires `reference_poi_image_not_found_span(world=None, slug=…)` before returning (reference_presenters.py:202-205) — observable, not silent. |
| [Improvement] shared history.yaml POI-slug parser dedup | ⏭ DEFERRED (non-blocking) | Both preflight and security subagents concur it's acceptable cross-call-site separation; logged as a follow-up. The two functions produce identical results today. |

**Dispatch-tag coverage (re-review):** `[SEC]` both findings resolved, 0 new (security subagent, high confidence). `[TEST]` new escaping regression test passes; full suite 96 green (preflight). `[EDGE]/[SILENT]/[DOC]/[TYPE]/[SIMPLE]/[RULE]` — unchanged from round-1 self-assessment above; the rework delta (one `escape()`, one span, one test) introduced no new surface in those domains.

**Data flow re-traced:** theme accent → `escape()` → style= attribute (safe); world-None → observable span; all other interpolations (src, alt) remain escaped; slug remains `slugify`-clamped.

**Devil's Advocate (re-review):** The one live attack vector (accent breakout) is now closed by `html.escape`, restoring the renderer's uniform escaping invariant — so the creator-authored-pack future no longer turns this line into stored XSS. The world-None branch is now observable, closing the GM-panel blind spot. The remaining duplication is a maintainability risk, not a correctness/security one, and it's logged. Nothing blocking remains.

**Handoff:** To SM/Architect for finish (spec-reconcile → finish).

## Delivery Findings

<!-- Append-only. Each agent appends under its own subheading. -->

### TEA (test design)
- **Question** (non-blocking): AC-6's "every region with a matching POI slug **has an R2 image**" needs a defined existence-check mechanism. R2 objects can't be filesystem-checked at validate time, and a network HEAD per slug is undesirable in a content validator. The RED tests cover the deterministic half (slug consistency: a history POI slug must map to a renderable location). Affects `sidequest-server/sidequest/cli/validate/locations.py` (decide: local asset mirror check vs. HTTP HEAD vs. treat history-presence AS the manifest). *Found by TEA during test design.*
- **Improvement** (non-blocking): the slug join needs normalization consistency — location card slug is `slugify(id|name)` (hyphenated) while authored history POI slugs are often underscore-style (`the_glenross_arms`). `assemble_lore_page` should `slugify()` history POI slugs when building `poi_image_slugs` so the membership check resolves. Affects `reference_renderer.py` (`assemble_lore_page`). Captured in story context guardrail #2; not separately unit-tested to avoid prescribing the normalization site. *Found by TEA during test design.*
- **Gap** (non-blocking): story setup produced no story/epic context (sm-setup-exit gate passed without it — the `.session` real-dir/symlink drift at repo root likely masked the `story-context-validated` recovery). TEA authored both context docs via `/pf-context` before writing tests. Affects sprint setup tooling / the `.session` path topology. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): AC-6's R2-object existence check is NOT implemented — only deterministic slug consistency (history POI slug → renderable location card). Implementing "the PNG actually exists in R2" needs a decision (HTTP HEAD vs local mirror vs treat history-presence as the manifest); deferred per TEA's open question. Affects `sidequest-server/sidequest/cli/validate/locations.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): pre-existing pyright error in `reference_presenters.py` `present_rules_root` magic-limits block (`rows = "".join(...)` at the `Hard Limits` branch — "str not assignable to declared list[str]"). Byte-identical to HEAD (unrelated to this story); pyright is not in `just check-all` (ruff + pytest only). Left out of scope. Affects `sidequest-server/sidequest/server/reference_presenters.py`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (blocking): `palette_accent` is interpolated unescaped into the `<img>` `style=` attribute, breaking the renderer's escape-everything invariant (stored-XSS once pack content becomes less-trusted per the creator-authoring roadmap). Affects `sidequest-server/sidequest/server/reference_presenters.py:210-211` (wrap with `html.escape`; optionally validate accent as a CSS color at pack-load). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `ctx.world is None` path returns `""` with no span — silent skip on a dead-defensive branch. Affects `sidequest-server/sidequest/server/reference_presenters.py:201-202` (span it or remove the unreachable guard). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `_history_poi_slugs` (validator) and `_load_poi_image_slugs` (renderer) duplicate the history.yaml POI-slug parse + slugify-normalize; they agree only by identical code and will silently drift (validator stops matching renderer). Affects `sidequest-server/{sidequest/cli/validate/locations.py, sidequest/server/reference_renderer.py}` (extract one shared parser). Flagged by verify-phase simplify; recommend folding into the rework. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, **re-review resolution**): the two blocking/low findings above (accent escaping, world-None silent return) were fixed in round-trip 1 and confirmed by re-run security + preflight subagents. The shared-parser dedup remains the **only** open follow-up — a candidate for a small standalone chore (extract `load_history_poi_slugs` into a leaf module both repos import). Non-blocking; story APPROVED without it. *Found by Reviewer during code review (re-review).*

## Impact Summary

**Upstream Effects:** 3 findings (1 Gap, 0 Conflict, 1 Question, 1 Improvement)
**Blocking:** 1 BLOCKING items — see below

**BLOCKING:**
- **Gap:** `palette_accent` is interpolated unescaped into the `<img>` `style=` attribute, breaking the renderer's escape-everything invariant (stored-XSS once pack content becomes less-trusted per the creator-authoring roadmap). Affects `sidequest-server/sidequest/server/reference_presenters.py:210-211`.

- **Question:** AC-6's "every region with a matching POI slug **has an R2 image**" needs a defined existence-check mechanism. R2 objects can't be filesystem-checked at validate time, and a network HEAD per slug is undesirable in a content validator. The RED tests cover the deterministic half (slug consistency: a history POI slug must map to a renderable location). Affects `sidequest-server/sidequest/cli/validate/locations.py`.
- **Improvement:** `ctx.world is None` path returns `""` with no span — silent skip on a dead-defensive branch. Affects `sidequest-server/sidequest/server/reference_presenters.py:201-202`.

### Downstream Effects

Cross-module impact: 3 findings across 2 modules

- **`sidequest-server/sidequest/server`** — 2 findings
- **`sidequest-server/sidequest/cli/validate`** — 1 finding

### Deviation Justifications

5 deviations

- **D1 — cartography.yaml reinterpreted as locations.yaml + history.yaml**
  - Rationale: matches actual render pipeline; avoids un-excluding the spoiler/asset-config cartography file and duplicating location rendering. One mechanism per problem.
  - Severity: minor (wording vs architecture; intent preserved).
  - Forward impact: AC-1/AC-4 tests assert against `location-{slug}` cards from locations.yaml; cartography↔history↔location alignment is the validator's job (AC-6).
- **D2 — accent from per-pack `theme.palette_accent`, not per-world visual_style.yaml**
  - Rationale: `visual_style.yaml` is in `EXCLUDED_FILES`, is image-gen config with no canonical accent field (`extra=allow`); wiring a per-world accent for a border tint is disproportionate for 2pts and would need a new genre-model field (sibling models are `extra=forbid`). Renderer already has a loaded accent.
  - Severity: minor.
  - Forward impact: AC-5 tests assert the per-pack theme accent. A genuinely per-world accent is a follow-up with a typed `visual_style` accent field.
- **Validator checks against locations.yaml card slugs, not cartography region keys**
  - Rationale: the lore page renders location cards from `locations.yaml`/`lore.geography`, never from `cartography.yaml` (excluded). A POI slug matching only a cartography region but no card would never render an image — checking cartography would mask exactly the dead-image case the validator exists to catch. Consistent with deviation D1.
  - Severity: minor.
  - Forward impact: matches `present_lore_geography` behaviour; if cartography↔locations alignment also needs validating, that's a separate region-key check.
- **POI image placed immediately after the card title (before meta chips)**
  - Rationale: visually anchors the landscape under the location name; still strictly above the `ref-card__body` description per AC-4 (test asserts title < img < body).
  - Severity: trivial.
  - Forward impact: none.
- **AC-6 implemented as slug-consistency only; the R2-object-existence probe is deferred**
  - Rationale: the session-level AC (highest spec authority) is "slug consistency check" and is fully met; the work-breakdown's "has an R2 image" needs a runtime existence mechanism (HTTP HEAD vs local mirror vs treating the history manifest as truth) that is genuinely undecided. A network HEAD per slug in a content validator is undesirable. Logged as TEA question + Dev gap + Reviewer follow-up.
  - Severity: minor (partial AC coverage; deterministic half delivered, network half deferred with a clear reason).
  - Forward impact: a follow-up chore should (a) decide the R2-existence mechanism and (b) extract the shared `history.yaml` POI-slug parser (the `_history_poi_slugs`/`_load_poi_image_slugs` dedup) so validate-time and render-time joins cannot drift.

## Design Deviations

### TEA (test design)
- **D1 — cartography.yaml reinterpreted as locations.yaml + history.yaml**
  - Spec source: context-story-63-8.md, story description "Server (reference_renderer.py): For each region in cartography.yaml ... inside the location-<slug> anchor section."
  - Spec text: iterate cartography.yaml regions and emit `<img>` in the `location-<slug>` section.
  - Implementation: tests target the real pipeline — `present_lore_geography` (renders `locations.yaml`/`lore.geography` as `location-{slug}` cards); `cartography.yaml` is in `EXCLUDED_FILES` and never rendered. Image gate is the `history.yaml points_of_interest[].slug` set threaded via `PresenterContext.poi_image_slugs`.
  - Rationale: matches actual render pipeline; avoids un-excluding the spoiler/asset-config cartography file and duplicating location rendering. One mechanism per problem.
  - Severity: minor (wording vs architecture; intent preserved).
  - Forward impact: AC-1/AC-4 tests assert against `location-{slug}` cards from locations.yaml; cartography↔history↔location alignment is the validator's job (AC-6).
- **D2 — accent from per-pack `theme.palette_accent`, not per-world visual_style.yaml**
  - Spec source: context-story-63-8.md, story description "Respect the per-world visual_style.yaml palette (border/shadow tint from the world's accent color)."
  - Spec text: source the tint from the world's `visual_style.yaml` accent colour.
  - Implementation: `test_image_border_uses_theme_accent` asserts `ReferenceTheme.palette_accent` (per-pack, from theme.yaml, already on `ctx.theme`).
  - Rationale: `visual_style.yaml` is in `EXCLUDED_FILES`, is image-gen config with no canonical accent field (`extra=allow`); wiring a per-world accent for a border tint is disproportionate for 2pts and would need a new genre-model field (sibling models are `extra=forbid`). Renderer already has a loaded accent.
  - Severity: minor.
  - Forward impact: AC-5 tests assert the per-pack theme accent. A genuinely per-world accent is a follow-up with a typed `visual_style` accent field.

### Dev (implementation)
- **Validator checks against locations.yaml card slugs, not cartography region keys**
  - Spec source: context-story-63-8.md, AC-6 / story content bullet "cartography region keys must match history.yaml POI slugs."
  - Spec text: validate that cartography regions with a matching POI slug have an image.
  - Implementation: `_check_poi_image_slugs` flags a history POI slug that has no matching **locations.yaml location card** slug (the renderer's actual image-attach target), not against cartography region keys.
  - Rationale: the lore page renders location cards from `locations.yaml`/`lore.geography`, never from `cartography.yaml` (excluded). A POI slug matching only a cartography region but no card would never render an image — checking cartography would mask exactly the dead-image case the validator exists to catch. Consistent with deviation D1.
  - Severity: minor.
  - Forward impact: matches `present_lore_geography` behaviour; if cartography↔locations alignment also needs validating, that's a separate region-key check.
- **POI image placed immediately after the card title (before meta chips)**
  - Spec source: context-story-63-8.md, AC-4.
  - Spec text: "below the region name, above the description text."
  - Implementation: `<img>` inserted directly after `<h3 class="ref-card__title">` and before the meta-chips/summary/body — satisfying "below name, above description."
  - Rationale: visually anchors the landscape under the location name; still strictly above the `ref-card__body` description per AC-4 (test asserts title < img < body).
  - Severity: trivial.
  - Forward impact: none.

### Reviewer (audit)
- **TEA D1 (cartography → locations.yaml)** → ✓ ACCEPTED: matches the real render pipeline; Architect concurred. Sound.
- **TEA D2 / Dev (per-pack theme.palette_accent vs per-world visual_style.yaml)** → ✓ ACCEPTED: proportionate for 2pts; per-world accent is a clean follow-up. (Note: the *escaping* of that accent value is the separate blocking finding — the deviation about *which* accent to use is fine; the defect is failing to escape it.)
- **Dev (validator checks locations.yaml card slugs, not cartography regions)** → ✓ ACCEPTED: correctly matches the renderer's actual image-attach target; checking cartography would mask the dead-image case.
- **Dev (image placed after title, before meta chips)** → ✓ ACCEPTED: satisfies AC-4 (title < img < body), test-verified.
- No undocumented spec deviations found beyond the escaping defect (logged as a blocking Delivery Finding, not a deviation — it is a bug, not an intentional divergence).

### Architect (reconcile)

**Existing entries verified:**
- TEA **D1** (cartography → locations.yaml + history.yaml): spec source `context-story-63-8.md` exists; quoted spec text accurate against the story description; implementation matches code (`present_lore_geography` renders `locations.yaml`/`lore.geography`; `cartography.yaml` ∈ `EXCLUDED_FILES`). All 6 fields present. **Accurate.**
- TEA **D2** / Dev (per-pack `theme.palette_accent` vs per-world `visual_style.yaml`): spec text accurate; implementation matches (`ctx.theme.palette_accent`, now `html.escape`'d). All 6 fields present. **Accurate.**
- Dev (validator checks `locations.yaml` card slugs, not cartography regions): accurate; matches `_check_poi_image_slugs`. **Accurate.**
- Dev (image placed after title, before meta): accurate; AC-4 test-verified. **Accurate.**

**Missed deviation formalized:**
- **AC-6 implemented as slug-consistency only; the R2-object-existence probe is deferred**
  - Spec source: `sprint/context/context-story-63-8.md`, AC-6 + Work Breakdown (Content).
  - Spec text: "Add to pf-validate-locations (story 54-3) a check that every cartography region with a matching POI slug **has an R2 image**." (Session-level AC-6 reads "pf-validate-locations enhanced with slug consistency check.")
  - Implementation: `_check_poi_image_slugs` validates the deterministic half — every `history.yaml` POI slug must map to a renderable `locations.yaml` card slug (flags dangling slugs). It does NOT probe R2/object existence.
  - Rationale: the session-level AC (highest spec authority) is "slug consistency check" and is fully met; the work-breakdown's "has an R2 image" needs a runtime existence mechanism (HTTP HEAD vs local mirror vs treating the history manifest as truth) that is genuinely undecided. A network HEAD per slug in a content validator is undesirable. Logged as TEA question + Dev gap + Reviewer follow-up.
  - Severity: minor (partial AC coverage; deterministic half delivered, network half deferred with a clear reason).
  - Forward impact: a follow-up chore should (a) decide the R2-existence mechanism and (b) extract the shared `history.yaml` POI-slug parser (the `_history_poi_slugs`/`_load_poi_image_slugs` dedup) so validate-time and render-time joins cannot drift.

**AC deferral check:** No ACs were formally DESCOPED via an ac-completion accountability table; AC-6 is the only partial (above). All other ACs (1–5, 7) are fully implemented and test-covered. The Reviewer's two findings were resolved in round-trip 1, not deferred.

**No further undocumented deviations found.**