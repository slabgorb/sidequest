---
story_id: "65-9"
jira_key: ""
epic: "65"
workflow: "tdd"
---
# Story 65-9: Lore Cast section — public NPC projection + manifest-gated portraits

## Story Details
- **ID:** 65-9
- **Jira Key:** (not configured for this project; YAML-tracked only)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-02T09:18:45Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-02T05:57:09Z | 2026-06-02T05:59:11Z | 2m 2s |
| red | 2026-06-02T05:59:11Z | 2026-06-02T08:25:58Z | 2h 26m |
| green | 2026-06-02T08:25:58Z | 2026-06-02T08:51:35Z | 25m 37s |
| spec-check | 2026-06-02T08:51:35Z | 2026-06-02T08:57:21Z | 5m 46s |
| verify | 2026-06-02T08:57:21Z | 2026-06-02T09:03:22Z | 6m 1s |
| review | 2026-06-02T09:03:22Z | 2026-06-02T09:16:51Z | 13m 29s |
| spec-reconcile | 2026-06-02T09:16:51Z | 2026-06-02T09:18:45Z | 1m 54s |
| finish | 2026-06-02T09:18:45Z | - | - |

## Story Context

**Epic:** 65 — Content Infrastructure — R2 asset tracking and audit

### Technical Approach

Render the public NPC projection on the lore reference page with manifest-gated portrait `<img>`s — the portrait analog of 65-8's POI gate. 

**Reuse 65-8's machinery:**
- `load_r2_manifest_keys()` — fetch the R2 manifest keys
- Pack discovery rule: `pack_dir.parent.parent/r2_manifest.json`
- Gate-only-when-feature-is-present shape
- Add a portrait-key analog to `poi_image_key()` (e.g., `portrait_image_key()`)
- Emit `manifest_loaded` OTEL span
- Reuse existing `portrait_not_found` span family

**Primary References:**
- 65-8 (completed) — Lore POI gallery with manifest-gated images
- PR #573 (65-8 review) — carryover findings and deviations to fold in here

### Acceptance Criteria

1. **Cast section render:** Render the public NPC projection with a portrait `<img>` gated on `r2_manifest.json` presence (portrait analog of 65-8's POI gate); authored-but-not-on-R2 NPCs render text-only, no broken image. Reuse `load_r2_manifest_keys()` + pack_dir.parent.parent discovery; add a `portrait_image_key()` analog to `poi_image_key()`.

2. **No-Silent-Fallback e2e proof:** Add a route-level test that `GET /reference/lore/{pack}/{world}` for a feature-bearing world whose `r2_manifest.json` is ABSENT returns 500 (loud), not a silently image-free page. This closes the gap the 65-8 reviewer flagged for the shared gate.

3. **Loud-fail branch coverage:** Add `test_load_manifest_entry_missing_key_raises_loudly` — a manifest list whose entry is a dict missing 'key' must raise `ValueError`. Second loud-fail branch of `load_r2_manifest_keys`, currently uncovered.

4. **Assertion tightening:** The `manifest_loaded` span test must assert the EXACT fixture `entry_count` (== N), not >= 1, so it also proves the gate read the fixture manifest rather than the production one (guards pack_dir.parent.parent resolution).

5. **Docstring accuracy:** Fix three 65-8 docstrings while editing those files — `_gate_poi_slugs_on_manifest` 'one span per render' (false for feature-less worlds), `load_r2_manifest_keys` 'once per process' (imprecise vs `lru_cache`), and `poi_image_key` (document that it returns a RAW R2 key compared directly to the manifest; the presenter must wrap it in `resolve_asset_url`, the gate must NOT).

6. **Type annotations:** Annotate the two test helpers — `_entry` -> `dict[str, object]` and the `gated_client` fixture -> `Iterator[TestClient]` — in `test_reference_poi_manifest_gate.py` (and mirror in the new Cast test module).

7. **Cache staleness runbook:** Add a runbook note that `load_r2_manifest_keys` is `lru_cached` with no TTL/mtime — a manifest regenerated after an asset upload is not picked up until server restart (safe-failing: text-only, never broken). Optionally key the cache on the manifest file mtime so a regenerated manifest is picked up live.

8. **Optional observability:** If a GM authoring-completeness view is wanted, add a distinct `reference_cast_image_not_in_manifest` span so 'authored but not on R2' is distinguishable from 'not authored' (today both collapse into `portrait_image_not_found`). Defer unless the dashboard needs it.

## Sm Assessment

**Setup complete — routing to RED (TEA).**

- **Story scope:** 3pt P1, server-only. Portrait analog of the just-merged/landed 65-8 POI manifest gate. This is the lone P1 in the backlog and builds directly on machinery already on `develop`.
- **Branch:** `feat/65-9-lore-cast-public-npc-projection` created off `sidequest-server/develop` (correct base per repos.yaml — NOT main).
- **Jira:** none (story is YAML-tracked; jira_key empty). Explicitly skipped, not an error.
- **Merge gate:** clear — 0 open PRs across all subrepos at setup time (ADR-136 PRs #311/#574 landed immediately prior).
- **TEA focus for RED:** Write failing tests for the eight ACs, anchored on AC2 (No-Silent-Fallback e2e: absent `r2_manifest.json` on a feature-bearing world must 500, not silently render image-free) and AC3 (loud-fail branch: manifest entry dict missing `key` raises `ValueError`). Reuse the 65-8 test patterns in `test_reference_poi_manifest_gate.py`. Assert EXACT fixture `entry_count` (AC4), not `>= 1`.
- **Watch:** Per OTEL principle, the new `portrait_image_key` gate path must emit spans (`manifest_loaded`, reuse `portrait_not_found` family) so the GM panel can confirm the gate engaged rather than Claude improvising a text-only render.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (7 failing + 1 pre-passing characterization guard — ready for Dev)

**Test Files:**
- `tests/server/test_reference_cast_manifest_gate.py` (NEW) — 8 tests pinning the Cast-gate contract.
- `tests/server/test_reference_poi_manifest_gate.py` (EDITED, AC6) — type-annotation-only; still 11/11 green.

**Fixtures authored:**
- `tests/fixtures/packs/reference_v2_fixture/worlds/cast_gated_fixture/{world.yaml,portrait_manifest.yaml}` — 2 NPCs: Vivian Harbormaster (on-R2) + Thessaly Dunmore (authored-but-absent).
- `tests/fixtures/r2_manifest.json` — added Vivian's world-scoped portrait key (now 3 entries; AC4 asserts `== 3` dynamically via file read).

**Contract pinned for Dev (RED → must turn green):**
- `portrait_image_key(pack, world, slug) -> str` in `reference_presenters.py` = `genre_packs/{pack}/worlds/{world}/assets/portraits/{slug}.png` (the 65-6 world-scoped key, NOT the legacy pack-level `images/portraits/`).
- `assemble_lore_page` builds a **Cast** section from `portrait_manifest.yaml`; each card `id="cast-{slug}"`, `slug = slugify_player_name(name)`; portrait `<img>` emitted iff `portrait_image_key(...)` ∈ loaded manifest, else text-only.
- Reuse `load_r2_manifest_keys` + `pack_dir.parent.parent` discovery + `reference_manifest_loaded_span`. Reuse `scrapbook.npc_portrait_{resolved,not_found}` per-NPC.
- Absent manifest on a Cast world → clean **HTTP 500** (route handler must catch the `FileNotFoundError`, today it only catches `ValueError`/`MissingThemeFieldError`).

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent-exceptions (No Silent Fallbacks) | `test_absent_manifest_on_cast_world_returns_500`, `test_load_manifest_entry_missing_key_raises_loudly` | 500-test failing (RED) / loud-fail PASS |
| #3 type-annotations at boundaries (AC6) | `_entry -> dict[str, object]`, `gated_client -> Iterator[TestClient]` (both modules) | applied |
| #5 path-handling (manifest discovery, `encoding=`) | gate route tests exercise `pack_dir.parent.parent` discovery | failing (RED) |
| #6 test-quality (exact assertion, AC4) | `test_cast_render_fires_manifest_loaded_span_with_exact_count` (`== N`, not `>= 1`) | failing (RED) |
| #8 unsafe-deserialization (manifest parse loud) | `test_load_manifest_entry_missing_key_raises_loudly` | PASS (pins existing guard) |
| OTEL principle (per-subsystem span) | `test_cast_portrait_decisions_emit_spans`, AC4 span test | failing (RED) |

**Rules checked:** 6 of 13 lang-review rules are applicable to this gate/render change and have test coverage. (#2/#4/#7/#9/#10/#11/#12/#13 N/A — no mutable defaults, no new logging surface beyond the 500 path, no resource handles, no async, no SQL/user-input boundary, no deps.)
**Self-check:** 0 vacuous tests. Every test asserts a specific value/exception/span attribute; `test_load_manifest_entry_missing_key_raises_loudly` asserts a real `ValueError` branch (pre-passing characterization, not vacuous).

**Handoff:** To Dev (Winchester) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 8/8 cast gate + 11/11 POI gate GREEN; 419 passed / 1 skipped across the broader `-k reference` suite (no regression). Lint + format clean on all changed files.
**Branch:** `feat/65-9-lore-cast-public-npc-projection` (pushed)

**Files Changed:**
- `sidequest/server/reference_presenters.py` — `portrait_image_key()` (world-scoped, raw-key, AC1); `_cast_portrait_img_html()` (per-NPC `<img>` + reuse of the 65-6 `scrapbook.npc_portrait_{resolved,not_found}` spans); `present_lore_cast()` (Cast section builder, `id="cast-{slug}"` cards, text-only when not on R2). AC5 docstring fix on `poi_image_key` (raw-key vs `resolve_asset_url`).
- `sidequest/server/reference_renderer.py` — `load_cast_entries()` (reads `portrait_manifest.yaml`, `yaml.safe_load`, shape-tolerant); `_gate_cast_slugs_on_manifest()` (portrait analog of the POI gate, reuses `load_r2_manifest_keys` + `pack_dir.parent.parent` discovery + `reference_manifest_loaded_span`); `_int_to_roman()` + Cast wiring into `assemble_lore_page` (section appended to body, TOC entry with `num`). AC5 docstring fixes on `load_r2_manifest_keys` (lru_cache precision) and `_gate_poi_slugs_on_manifest` (span-when-feature-present); AC7 cache-staleness runbook note on `load_r2_manifest_keys`.
- `sidequest/server/reference_routes.py` — `lore_page` now catches `FileNotFoundError` → clean 500 (AC2, the seam TEA flagged).

**AC coverage:** AC1 ✅ (gate + text-only), AC2 ✅ (clean 500), AC3 ✅ (pre-existing loud-fail, now pinned), AC4 ✅ (exact entry_count), AC5 ✅ (3 docstrings), AC6 ✅ (annotations, TEA), AC7 ✅ (runbook note), AC8 ⏸️ deferred per spec (reused scrapbook family; no `reference_cast_*` span added).

**Wiring proof (non-test consumer):** `present_lore_cast`/`portrait_image_key`/`_gate_cast_slugs_on_manifest` are all reached from the live `GET /reference/lore/{pack}/{world}` route via `assemble_lore_page` — the route tests exercise the real handler, not isolated units (CLAUDE.md "Verify Wiring, Not Just Existence").

**Handoff:** To Architect (Houlihan) for SPEC-CHECK.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned — all 8 ACs substantively met.
**Mismatches Found:** 1 (Minor, architectural-hygiene; non-blocking on the ACs)

**Structural gate:** PASS (AC coverage, implementation-complete, TEA + Dev deviation subsections all present).

**Per-AC substance review (against context-story-65-9.md + the diff):**
- **AC1** ✅ `portrait_image_key` is world-scoped (`…/worlds/{world}/assets/portraits/{slug}.png`), matching the 65-6 `_resolve_npc_portrait_url` construction — exemplary reuse, not reinvention. `present_lore_cast` gates the `<img>` on the manifest set; absent → text-only. Cards `id="cast-{slug}"`, slug via `slugify_player_name`.
- **AC2** ✅ Route now catches `FileNotFoundError` → clean 500; verified the gate raises it on absent manifest for a cast-bearing world.
- **AC3** ✅ Loud-fail branch (entry-missing-`key` → `ValueError`) pinned; pre-existing 65-8 behavior, correctly characterized.
- **AC4** ✅ Exact `entry_count` assertion (reads the fixture manifest len).
- **AC5** ✅ All three docstrings corrected (raw-key/`resolve_asset_url` boundary, `lru_cache` precision, span-when-feature-present).
- **AC6** ✅ Type annotations applied (TEA).
- **AC7** ✅ Cache-staleness runbook note present and accurate (no TTL/mtime; restart-to-refresh).
- **AC8** ⏸️ Legitimately deferred per spec ("Defer unless the dashboard needs it"); scrapbook family reused per AC1. Correct call.

**Reuse discipline:** Strong. The implementation extends 65-8's gate machinery and 65-6's portrait key/slug convention rather than introducing parallel infrastructure. `load_r2_manifest_keys`, `pack_dir.parent.parent` discovery, `reference_manifest_loaded_span`, and `scrapbook.npc_portrait_{resolved,not_found}` are all reused. The one net-new helper (`_int_to_roman`) is bounded, justified, and necessary to conform to the `_build_toc` `num` contract.

**Mismatch 1 — undefined CSS classes on the Cast section (Extra-in-code / convention divergence — architectural, Minor)**
  - Spec (architecture doc): `reference_renderer.py` module docstring + `test_reference_chrome_wiring.py` enforce a chrome contract — *every* `class="…"` token must match the served CSS bundle (`theme.css`+`styles.css`) or sit in `SEMANTIC_ALLOWLIST`. Stated intent: "drift like shipping `.contents-rail` again will fail loud."
  - Code: `present_lore_cast` emits `class="ref-section__title"` (heading) and `class="ref-card__portrait"` (img). Neither is in the CSS bundle nor the allowlist. `ref-section__title` also diverges from the sibling convention — `present_lore_geography`/`present_lore_factions` emit **no** in-section heading, and the generic path uses a **bare** `<h2>` (reference_renderer.py:340) — so the new themed class renders unstyled (browser-default `<h2>`).
  - Why the suite passed: the chrome-wiring guard renders `space_opera/coyote_star`, a world with **no** `portrait_manifest.yaml` (and no `history.yaml` POIs), so the Cast section — and even the existing `ref-card__poi` — is **never emitted through the guard**. The classes escaped validation by a coverage gap, not by validity. `ref-card__portrait` faithfully mirrors the pre-existing (equally-unguarded) `ref-card__poi` precedent and is inline-styled, so it is visually correct; `ref-section__title` is the genuine anomaly.
  - **Recommendation: C/B (route to downstream gates, do not bounce green).** Spec ACs are fully met and the issue is Minor/cosmetic/non-breaking, so I am **not** handing back to Dev from spec-check. I route two concrete fixes to the verify/review gates:
    1. **Dev/Reviewer (this PR, before merge):** drop the undefined class — use a bare `<h2>Cast</h2>` (matches the line-340 convention), or add `ref-section__title` + `ref-card__portrait` to `SEMANTIC_ALLOWLIST` with justification (mirroring how inline-styled decorative classes are handled).
    2. **TEA (verify / follow-up):** extend the chrome-wiring fixture (`_seed_space_opera_world`) to author a `portrait_manifest.yaml` (and ideally a gated POI) so the guard actually renders — and thus protects — the Cast and POI image classes. This closes a **pre-existing** blind spot 65-9 inherits (`ref-card__poi` is unguarded today).

**Decision:** Proceed to TEA verify. Spec alignment is clean (8/8 ACs); the one finding is a Minor chrome-contract-hygiene matter explicitly routed (non-silently) to the verify and review gates that exist to handle it.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (419 passed / 1 skipped; cast 8/8 + POI 11/11; chrome-wiring still green; lint + format clean)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (3 source + 2 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | Cast/POI parallelism is justified — different architectural contexts (presenter-threaded POI vs page-assembled Cast), different span families/signatures. Extraction would obscure intent. No action. |
| simplify-quality | 2 findings (both high-conf) | (1) `ref-section__title` undefined CSS + non-conventional → **APPLIED** (bare `<h2>`). (2) `ref-card__portrait` undefined, suggested rename to `ref-card__poi` → **REJECTED** (verified `ref-card__poi` is *also* undefined + semantically wrong; carried to Reviewer). |
| simplify-efficiency | 2 findings | (1) `_int_to_roman` "premature abstraction" (high-conf) → **DISMISSED** (a correct bounded 12-line helper; a hardcoded I–XX table is not clearly better and risks bugs). (2) two-gate double span (low-conf) → **KEPT** (intentional per docstrings; Dev already logged). |

**Applied:** 1 high-confidence fix — `present_lore_cast` heading `<h2 class="ref-section__title">` → bare `<h2>Cast</h2>` (commit `faa3b703`). Removes a chrome-contract violation and restores the sibling-section heading convention.
**Flagged for Review:** 1 — `ref-card__portrait` (undefined, inline-styled, consistent with the pre-existing `ref-card__poi` precedent). The simplify-quality rename suggestion was **incorrect** (target also undefined); the correct systemic fix is the Architect's rec #2 — extend the chrome-wiring fixture to render a cast+POI world and allowlist the inline-styled image classes (closes a pre-existing blind spot). Not half-applied in verify.
**Noted (no action):** `_int_to_roman` (style opinion, dismissed); two-gate double-span (intentional/observability — Defer).
**Reverted:** 0.

**Overall:** simplify: applied 1 fix.

**Quality Checks:** All passing (ruff check + format clean; full reference suite green; regression check post-fix GREEN).
**Handoff:** To Reviewer (Colonel Potter) for code review. **Open item for Reviewer:** the `ref-card__portrait` / chrome-wiring-fixture chrome-contract finding (see Delivery Findings → Architect + the corrected analysis above).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; 9623 pass, 1 pre-existing fail (not regression); lint/format/type clean on branch files | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (1 med-conf gap, 4 low) | confirmed 5 (all non-blocking), dismissed 0, deferred 0 |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (both high-conf, med/low severity) | confirmed 2, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 (all test-file, LOW); production clean on all 18 rules | confirmed 3, dismissed 0, deferred 0 |

**All received:** Yes (4 ran, 5 disabled-skipped)
**Total findings:** 10 confirmed (all Medium/Low, none blocking), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `GET /reference/lore/{pack}/{world}` → `_resolve_pack_dir`/`_resolve_world_dir` (404 on miss, *outside* try) → `assemble_lore_page` → `load_cast_entries(world_dir)` reads `portrait_manifest.yaml` (first-party content) → `_gate_cast_slugs_on_manifest` loads `r2_manifest.json` (absent → `FileNotFoundError` → caught → clean 500) → `present_lore_cast` emits `id="cast-{slug}"` cards, portrait `<img>` iff slug ∈ gated set, all fields `html.escape()`d. Safe end-to-end: no XSS surface, no 404→500 masking, no silent image-free page.

### Rule Compliance (lang-review/python.md — 13 rules, 47 instances)

Production code (`reference_presenters.py`, `reference_renderer.py`, `reference_routes.py`) is **clean on all 13 lang-review rules + 5 additional project rules** (rule-checker, exhaustive). Confirmed compliant exemplars:
- **#1 silent-exceptions** `[VERIFIED]` — `load_cast_entries` re-raises YAMLError as ValueError `from exc` (reference_renderer.py:1225); route converts to logged HTTP 500. No swallowing.
- **#3 type-annotations** — all new public/private functions annotated. *Violation:* test fixture params `gated_client, otel_capture` untyped at test_reference_cast_manifest_gate.py:200,225 (LOW, mirrors pre-existing POI-test pattern).
- **#5 path-handling** `[VERIFIED]` — pathlib `/` throughout; `open(encoding="utf-8")` everywhere; `.exists()` guards.
- **#6 test-quality** — all assertions specific (values/exceptions/span attrs). *One LOW:* no `cache_clear()` isolation (latent, benign — lru_cache only caches successes, tmp_paths unique).
- **#8 unsafe-deserialization** `[VERIFIED]` — `yaml.safe_load` (never `yaml.load`); `json.load` from filesystem oracle, not HTTP body. No pickle/eval/exec.
- **#11 security/input-validation** `[VERIFIED]` — pack/world regex-validated pre-resolution; every NPC field `html.escape()`d before HTML insertion (reference_presenters.py present_lore_cast + _cast_portrait_img_html).
- **A1 No Silent Fallbacks** `[VERIFIED]` — absent manifest → loud (FNF→500); malformed JSON/entry → ValueError; absent `portrait_manifest.yaml` → `[]` (skip, *documented as intentional*, not a config-masking fallback).
- **A2 No Source-Text Wiring Tests** `[VERIFIED]` — all 8 cast tests use behavior/span/HTTP assertions; zero `read_text()` on production source.
- **A3 OTEL spans** `[VERIFIED]` — every decision spanned (resolved/not_found/manifest_loaded) with real attributes; tested.
- **A5 FileNotFoundError masking** `[VERIFIED]` — surgical, NOT broad: `HTTPException(404)` raised *before* the try (never caught); all file opens in `assemble_lore_page` except `load_r2_manifest_keys` use `.exists()`/`.is_file()` guards; only the manifest (the intended AC2 target) is unguarded. *Independently traced by me at reference_routes.py:121-125, then confirmed by rule-checker A5.*

### Observations (≥5)

1. `[VERIFIED]` **404 not masked by the FileNotFoundError catch** — reference_routes.py:121-125; `_resolve_world_dir` raises `HTTPException(404)` (line 77) outside the try; `HTTPException` ∉ caught tuple. Corroborated by rule-checker A5 (high conf).
2. `[VERIFIED]` **XSS-safe** — every interpolation escaped (name/role/appearance/slug/src/palette_accent). Corroborated by rule-checker #11.
3. `[VERIFIED]` **Reuse discipline** — Cast machinery is a faithful portrait-analog of POI + 65-6 (`portrait_image_key` world-scoped key, `slugify_player_name`, scrapbook spans). simplify-reuse (verify) + rule-checker confirm no clarity-improving extraction exists.
4. `[DOC][MEDIUM]` **Misleading OTEL span semantics** — `_cast_portrait_img_html` reuses `scrapbook.npc_portrait_{resolved,not_found}`, whose docstrings (scrapbook.py:133,152) describe scene-time scrapbook-ref attachment; on the reference page no scrapbook ref exists, so the panel description misleads. *The span still fires with correct slug/world/genre attrs — engagement IS detectable; only the prose misleads.* Dev followed AC1 ("reuse the portrait not_found family"); the clean fix is AC8's dedicated `reference_portrait_*` spans (deferred per spec) or a docstring note. **Non-blocking.**
5. `[DOC][LOW]` **Lying docstring** — `load_cast_entries` (reference_renderer.py:1218) claims it "mirrors the genre loader … non-dict items are dropped"; the genre loader's `_load_portrait_manifest` does NOT drop non-dicts (it `model_validate`s and would raise). Two-shape tolerance is shared; non-dict-drop is not. **Non-blocking.**
6. `[TEST][MEDIUM]` **Span test missing complements** — `test_cast_portrait_decisions_emit_spans` asserts present∈resolved / absent∈not_found but not the complements, so a gate that *always* resolved would pass it. *Mitigated:* gate suppression is independently proven by `test_cast_authored_but_absent_npc_renders_textonly` (`<img` absence). **Non-blocking.**
7. `[TEST][LOW]` `match=` on the loud-fail `pytest.raises`; `[TEST][LOW]` 500-test not manifest-specific; `[TEST][LOW]` no test for a world lacking `portrait_manifest.yaml` (graceful `[]` path untested). **Non-blocking.**
8. `[RULE][LOW]` (lang-review #3) test fixture params untyped (lines 200,225) — pre-existing pattern; rule-checker confirmed production code clean on all 13 lang-review + 5 additional rules. **Non-blocking.**
9. `[CHROME][carried, MEDIUM/LOW]` `ref-card__portrait` undefined CSS class (consistent with the pre-existing `ref-card__poi` precedent) + the chrome-wiring fixture renders no cast/POI world so neither is guarded. From Architect spec-check + my verify pass. **Non-blocking.**
10. `[VERIFIED]` **Preflight clean** — 0 code smells, 9623 pass; the 1 failure (`test_aside_channel_wiring`) and 7 lint errors are pre-existing on develop.

### Devil's Advocate

Let me argue this is broken. *What if `portrait_manifest.yaml` is malformed?* `load_cast_entries` raises `ValueError` on YAMLError → 500 — loud, correct. *What if it's `{characters: 42}` (non-list)?* `data.get("characters", [])` → `42`; `[c for c in 42 ...]` raises `TypeError` — **not** caught by the route's `(ValueError, FileNotFoundError, MissingThemeFieldError)` → unhandled 500. That's still a 500 (no silent fallback), but an *un*-logged-cleanly one. However: a scalar `characters:` is an authoring error in first-party content, the result is a loud 500 either way, and no AC requires graceful handling of that specific malformation — so it's a LOW latent edge, not a defect. *What if an NPC name slugifies to empty (e.g. name = "***")?* `slugify_player_name("***")` → `""`; the card gets `id="cast-"` and the portrait key ends `/.png` — never in the manifest → text-only, no crash. Harmless. *What if two NPCs slugify to the same slug?* Duplicate `id="cast-{slug}"` anchors — invalid HTML but non-fatal; the same collision risk exists for POI `location-{slug}` and is unaddressed project-wide; out of scope here. *What if the manifest has 10,000 entries?* `load_r2_manifest_keys` is `lru_cache`d; a frozenset membership test is O(1); `world_key_count` is one O(n) scan per gated render — acceptable. *Could a confused operator misread the GM panel?* Yes — finding #4 (scrapbook span on a reference render). Real, logged, non-blocking. *Race conditions?* The lru_cache is read-mostly; no mutation. *Stressed filesystem?* A mid-read truncation → `json.JSONDecodeError` (ValueError) → loud 500. **Conclusion:** the devil finds rough edges (non-list `characters:` → unclean-but-loud 500; slug collisions) but no Critical/High defect. The feature is correct, fails loud, and is XSS-safe.

### Verdict rationale

Zero Critical/High findings. Production code is clean on all 18 rules; the load-bearing 404/500 and No-Silent-Fallbacks behaviors are surgically correct (independently verified + rule-checker-confirmed); security/XSS clean; all 8 ACs met and proven by the passing gate suite. The 10 confirmed findings are all Medium/Low quality refinements (doc accuracy, test rigor, chrome-class hygiene) — none block. Per this project's established pattern (epic 76 ← 75-6 review follow-ups), non-blocking review findings are carried into a follow-up. **APPROVED**, with a complete findings record below and a recommended epic-65 follow-up story.

**Handoff:** To SM (Hawkeye) for finish-story.

## Delivery Findings

No upstream findings.

No upstream findings.

### TEA (test design)
- **Improvement** (non-blocking): AC3's loud-fail branch (`load_r2_manifest_keys` on an entry-missing-`key`) is **already satisfied** by 65-8's loader — the new test passes immediately. It now pins a previously-uncovered branch; Dev needs no new code for it. Affects `sidequest/server/reference_renderer.py` (no change required; coverage only). *Found by TEA during test design.*
- **Question** (non-blocking): The route handler (`reference_routes.py:lore_page`) catches only `(ValueError, MissingThemeFieldError)`. The absent-manifest path raises `FileNotFoundError`, so AC2's clean-500 requires either widening the catch or raising a `ValueError` subclass from the gate. Affects `sidequest/server/reference_routes.py` (Dev picks the seam). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): A world authoring BOTH POIs and Cast NPCs now emits **two** `reference_manifest_loaded` spans per render (one per gate), not one — each gate consults the manifest independently. `load_r2_manifest_keys` is `lru_cache`d so the file is read once, but the span fires per gate. Honest (two consultations) and no test asserts a global one-span-per-render invariant, but a future GM-panel metric that counts manifest loads per render should expect one-per-gated-feature. Affects `sidequest/server/reference_renderer.py` (`assemble_lore_page`). A unifying refactor (load once, pass keys to both gates, emit one span) is deferred — no failing test demands it. *Found by Dev during implementation.*

### Architect (spec-check)
- **Improvement** (non-blocking, **Reviewer must resolve before merge**): The Cast section emits two undefined CSS classes — `ref-section__title` and `ref-card__portrait` — that satisfy neither the served CSS bundle nor `SEMANTIC_ALLOWLIST`, violating the chrome contract (`reference_renderer.py` module docstring + `test_reference_chrome_wiring.py`). They passed only because the chrome-wiring guard renders `coyote_star`, a world with no `portrait_manifest.yaml`, so the Cast section never reaches the guard. `ref-section__title` also diverges from the bare-`<h2>` section convention and renders unstyled. Affects `sidequest/server/reference_presenters.py:present_lore_cast` (use a bare `<h2>Cast</h2>` or allowlist the classes with justification). *Found by Architect during spec-check.*
- **Gap** (non-blocking): The chrome-wiring guard's fixture (`tests/server/test_reference_chrome_wiring.py:_seed_space_opera_world`) authors no `portrait_manifest.yaml` and no gated POIs, so the lore-page image classes (`ref-card__poi` pre-existing, `ref-card__portrait` new) are **never validated** by the contract guard. Pre-existing blind spot 65-9 inherits. Affects the chrome-wiring fixture (extend it to render a cast+POI-bearing world). *Found by Architect during spec-check.*

### Reviewer (code review)
**All Medium/Low — none blocking. Recommend an epic-65 follow-up story (pattern: epic 76 ← 75-6 review) to clear them.**
- **Improvement** (non-blocking): Misleading OTEL span semantics — `_cast_portrait_img_html` emits `scrapbook.npc_portrait_{resolved,not_found}` on the reference page, but those spans are documented (scrapbook.py:133,152) as scene-time scrapbook-ref events ("its scrapbook ref carries no portrait_url"). The span fires with correct slug/world/genre attrs (engagement IS detectable) but the panel description misleads in the reference-render context. Affects `sidequest/server/reference_presenters.py` + `sidequest/telemetry/spans/scrapbook.py` (add a dual-use docstring note, or — cleaner — implement AC8's dedicated `reference_portrait_*` spans, which also delivers the GM authoring-completeness distinction). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Lying docstring — `load_cast_entries` (reference_renderer.py:1218) claims it "mirrors the genre loader … non-dict items are dropped"; the genre loader's `_load_portrait_manifest` (loader.py:792) does NOT drop non-dicts (it `model_validate`s and would raise). Affects `sidequest/server/reference_renderer.py` (rewrite to: shared two-shape tolerance; non-dict drop is local to this function, unlike the genre loader). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Strengthen `test_cast_portrait_decisions_emit_spans` with complement assertions (`_ABSENT_SLUG not in resolved`, `_PRESENT_SLUG not in not_found`) so the span test alone can distinguish a correct gate from an always-resolve gate (suppression is currently proven only by the sibling text-only test). Also: add `match=r"missing 'key'"` to `test_load_manifest_entry_missing_key_raises_loudly`; add a `load_r2_manifest_keys.cache_clear()` isolation guard; add a body assertion that the AC2 500 is manifest-specific; add a no-`portrait_manifest.yaml` graceful-`[]` test. Affects `tests/server/test_reference_cast_manifest_gate.py`. *Found by Reviewer (via test-analyzer + rule-checker) during code review.*
- **Improvement** (non-blocking): Annotate test fixture params `gated_client: TestClient, otel_capture` at test_reference_cast_manifest_gate.py:200,225 (lang-review #3; pre-existing pattern in the POI suite too). *Found by Reviewer during code review.*
- **Improvement** (non-blocking, latent edge): A non-list `characters:` (e.g. `characters: 42`) in `portrait_manifest.yaml` raises an *uncaught* `TypeError` → unhandled (still loud) 500 rather than the clean logged 500. First-party authoring error; loud either way. Consider guarding `chars` with `isinstance(chars, list)` in `load_cast_entries`. Affects `sidequest/server/reference_renderer.py`. *Found by Reviewer (devil's advocate) during code review.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Cast card HTML marker `id="cast-{slug}"` is test-imposed**
  - Spec source: context-story-65-9.md, AC1 (and session AC1)
  - Spec text: "Render the public NPC projection with a portrait `<img>` gated on `r2_manifest.json` presence"
  - Implementation: Tests pin each NPC card as `<article id="cast-{slug}">…</article>`, mirroring the POI gate's `id="location-{slug}"` convention, so `_card()` can slice a single card.
  - Rationale: The AC leaves the markup open; a stable per-card id is required to assert image-present-vs-text-only per NPC. Mirrors the established sibling pattern.
  - Severity: minor
  - Forward impact: Dev must emit this id (or Architect re-specs it in spec-check and the test updates).
- **Per-NPC decision reuses the scrapbook portrait span family**
  - Spec source: context-story-65-9.md, AC1 / AC8
  - Spec text: AC1 "reuse the existing portrait not_found span family"; AC8 (optional) "add a distinct `reference_cast_image_not_in_manifest` span"
  - Implementation: `test_cast_portrait_decisions_emit_spans` pins `scrapbook.npc_portrait_{resolved,not_found}` (the 65-6 family) keyed by slug — the non-optional observability floor.
  - Rationale: AC1 mandates reuse; AC8's reference-namespaced span is explicitly optional/deferred. Pinning the existing family keeps RED honest without forcing the deferred work.
  - Severity: minor
  - Forward impact: If Architect/Dev elects AC8's reference span, this test migrates to it. AC8 itself is **not** tested (deferred per spec).
- **AC5 (docstrings) and AC7 (cache-staleness runbook) have no failing tests**
  - Spec source: context-story-65-9.md, AC5 + AC7
  - Spec text: AC5 "Fix three 65-8 docstrings"; AC7 "Add a runbook note that `load_r2_manifest_keys` is `lru_cache`d…"
  - Implementation: No test authored — docstring/comment/runbook prose is not behaviorally assertable (and source-text wiring tests are forbidden per server CLAUDE.md).
  - Rationale: These are Dev documentation tasks verified at review, not RED-testable behavior.
  - Severity: minor
  - Forward impact: Reviewer must confirm AC5/AC7 prose landed; they are not gated by the test suite.

### Dev (implementation)
- **Added `_int_to_roman` helper to number the dynamically-appended Cast TOC entry**
  - Spec source: context-story-65-9.md, AC1
  - Spec text: "Render the public NPC projection … on the lore reference page"
  - Implementation: `_build_toc` requires every TOC entry to carry a Roman-numeral `num` field (DEFAULT_TOC/PACK_TOC shape). Since the Cast section is appended at render time (not a static PACK_TOC entry), I added a small `_int_to_roman()` and number the Cast entry `len(kept_toc)+1`.
  - Rationale: The Cast entry must conform to the existing TOC entry contract or `_build_toc` raises `KeyError('num')`. A bounded Roman converter (≤ C) is the minimal way to match the established `num` convention rather than introduce an inconsistent numbering scheme.
  - Severity: minor
  - Forward impact: none — internal helper; no public surface change.
- **AC8 deferred — reused the scrapbook portrait span family, added no `reference_cast_*` span**
  - Spec source: context-story-65-9.md, AC8
  - Spec text: "Defer unless the dashboard needs it"
  - Implementation: Per-NPC decisions emit `scrapbook.npc_portrait_{resolved,not_found}` (AC1's mandated reuse). No distinct `reference_cast_image_not_in_manifest` span was added.
  - Rationale: AC8 is explicitly optional and the GM dashboard has no stated need today; adding it now would be speculative scope. "Authored vs not-on-R2" is still observable via the resolved/not_found split.
  - Severity: minor
  - Forward impact: If a GM authoring-completeness view later needs to distinguish "authored-but-absent" from "not-authored", add the reference-namespaced span then; `test_cast_portrait_decisions_emit_spans` would migrate to it.
- Otherwise: no deviations — the implementation conformed to TEA's pinned contract (`id="cast-{slug}"`, world-scoped `portrait_image_key`, scrapbook span reuse, exact-count manifest span, clean-500).

### Reviewer (audit)
- **TEA — Cast card marker `id="cast-{slug}"`** → ✓ ACCEPTED: sound; mirrors the established `id="location-{slug}"` POI convention and is required to assert per-NPC image-vs-text. Implemented as specified.
- **TEA — Per-NPC reuses the scrapbook portrait span family** → ✓ ACCEPTED (with noted consequence): correctly implements AC1's mandated reuse. The semantic-mismatch consequence (scrapbook docstrings describe scene-time refs) is captured as a non-blocking Reviewer finding; the deviation itself is sound and spec-driven.
- **TEA — AC5/AC7 have no failing tests** → ✓ ACCEPTED: docstring/runbook prose is not behaviorally assertable and source-text wiring tests are forbidden (server CLAUDE.md). I independently verified AC5's three docstrings and AC7's runbook note landed and are accurate (comment-analyzer corroborated, except the separate `load_cast_entries` "mirrors" inaccuracy, logged as a finding).
- **Dev — `_int_to_roman` helper** → ✓ ACCEPTED: necessary to satisfy `_build_toc`'s `num` contract for the dynamically-appended Cast TOC entry; bounded, pure, correct. simplify-efficiency's "premature abstraction" flag was reasonably dismissed at verify (a hardcoded I–XX table is not clearly better).
- **Dev — AC8 deferred (no `reference_cast_*` span)** → ✓ ACCEPTED: AC8 is explicitly optional ("Defer unless the dashboard needs it"). Note: implementing it later cleanly resolves the misleading-span-semantics finding too — recommended for the follow-up, not required now.
- **No undocumented deviations found.** The verify-phase change (`ref-section__title` → bare `<h2>`) is a logged simplify fix, not a spec deviation. All 8 ACs are met as specified; no behavior diverged from spec without a corresponding logged entry.

### Architect (reconcile)

**In-flight log verification:** All TEA (×3) and Dev (×2) deviation entries were checked against their cited spec sources (`sprint/context/context-story-65-9.md` — exists; ACs 1/5/7/8 quoted accurately) and against the merged code. Every entry's 6 fields are present, substantive, and the Implementation descriptions match what the code does. No corrections required. The Reviewer audit correctly stamped all five ACCEPTED.

**AC deferral verification:** AC8 (optional `reference_cast_image_not_in_manifest` span) is the only deferred AC. Spec text: *"Defer unless the dashboard needs it."* Cross-referenced against the Reviewer's findings: AC8 was **not** inadvertently addressed or invalidated during review — it remains validly deferred. Status unchanged: DEFERRED (justified). The Reviewer noted, and I concur, that implementing AC8 in the follow-up cleanly resolves the misleading-span-semantics finding. All other ACs (1–7) are DONE.

**Missed deviations formalized** (captured during build/review as Delivery Findings, promoted here to the deviation manifest for audit completeness):

- **Two `reference_manifest_loaded` spans per render for a both-features world**
  - Spec source: context-story-65-9.md, AC1 (and the inherited 65-8 span contract)
  - Spec text: "Reuse `load_r2_manifest_keys()` + pack_dir.parent.parent discovery; … Emit `manifest_loaded` OTEL span" — and the sibling 65-8 test `test_lore_render_fires_manifest_loaded_span_once` encodes "exactly one manifest_loaded span per render."
  - Implementation: `_gate_cast_slugs_on_manifest` mirrors `_gate_poi_slugs_on_manifest` as an independent gate, each emitting its own `reference_manifest_loaded` span. A world authoring BOTH POIs and Cast NPCs therefore emits TWO spans per render (the file is read once — `load_r2_manifest_keys` is `lru_cache`d — but the span fires per gate).
  - Rationale: parallel-gate structure keeps each feature self-contained (simplify-reuse confirmed extraction would reduce clarity); the per-feature span is arguably honest observability. No fixture exercises a both-features world, so no test regresses.
  - Severity: minor
  - Forward impact: a future GM-panel metric counting manifest loads per render must expect one-span-per-gated-feature, not one-per-render. A unifying refactor (single load, one span, keys passed to both gates) is the clean resolution; deferred to the follow-up — no failing test demands it now.

- **Cast section emits an undefined CSS class (`ref-card__portrait`) outside the chrome-contract guard's reach**
  - Spec source: architecture doc — `reference_renderer.py` module docstring + `tests/server/test_reference_chrome_wiring.py` (chrome contract)
  - Spec text: "every `class="…"` token the renderer emits … is [in] the served CSS bundle OR is in the deliberately-small `SEMANTIC_ALLOWLIST`" — "drift like shipping `.contents-rail` again will fail loud."
  - Implementation: `_cast_portrait_img_html` emits `class="ref-card__portrait"`, which is in neither the served CSS bundle nor `SEMANTIC_ALLOWLIST`. It is inline-styled (visually correct) and faithfully parallels the pre-existing, equally-undefined `ref-card__poi` (65-8). The verify pass already removed the genuinely-anomalous `ref-section__title` (→ bare `<h2>`). The chrome-wiring guard renders `coyote_star` (no `portrait_manifest.yaml`, no gated POIs), so neither image class is validated — a pre-existing blind spot 65-9 inherits.
  - Rationale: AC1 mandated the portrait-analog of the POI path; the Dev matched the sibling `ref-card__poi` precedent exactly. Resolving it properly is a coordinated test+source change (extend the fixture + allowlist the inline-styled image classes) better done as a deliberate follow-up than half-applied at verify.
  - Severity: minor (non-breaking; inline-styled; image renders correctly)
  - Forward impact: until the chrome-wiring fixture is extended to render a cast+POI world, the lore-page image classes remain unguarded against future CSS drift. Recommended for the epic-65 follow-up alongside the other non-blocking findings.

**Definitive manifest status:** Every spec divergence is now explicitly logged and either ACCEPTED (Reviewer) or carried as a non-blocking follow-up. Nothing slips through undocumented. The story is spec-reconciled and ready for SM finish.