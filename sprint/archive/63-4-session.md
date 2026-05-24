---
story_id: "63-4"
jira_key: ""
epic: "63"
workflow: "tdd"
---

# Story 63-4: Chrome rendering: theme injection, CSS route, hero, contents rail

## Story Details

- **ID:** 63-4
- **Title:** Chrome rendering: theme injection, CSS route, hero, contents rail
- **Jira Key:** (none — SideQuest doesn't use Jira)
- **Workflow:** tdd
- **Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
- **Branch:** feat/63-4-ref-chrome-theme-css-hero
- **Points:** 10
- **Priority:** p2

## Repos

| Repo | Path | Branch | Worktree Path |
|------|------|--------|---------------|
| server | /Users/slabgorb/Projects/oq-1/sidequest-server | feat/63-4-ref-chrome-theme-css-hero | /Users/slabgorb/Projects/oq-1/sidequest-server/.claude/worktrees/feat+63-4-ref-chrome-theme-css-hero |
| content | /Users/slabgorb/Projects/oq-1/sidequest-content | feat/63-4-ref-chrome-theme-css-hero | (in-place checkout) |

## Workflow Tracking

**Workflow:** tdd  
**Phase:** finish  
**Phase Started:** 2026-05-24T12:51:44Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-05-24T07:30:00Z | 2026-05-24T11:55:10Z | 4h 25m |
| green | 2026-05-24T11:55:10Z | 2026-05-24T12:18:11Z | 23m 1s |
| spec-check | 2026-05-24T12:18:11Z | 2026-05-24T12:21:37Z | 3m 26s |
| verify | 2026-05-24T12:21:37Z | 2026-05-24T12:29:29Z | 7m 52s |
| review | 2026-05-24T12:29:29Z | 2026-05-24T12:49:28Z | 19m 59s |
| spec-reconcile | 2026-05-24T12:49:28Z | 2026-05-24T12:51:44Z | 2m 16s |
| finish | 2026-05-24T12:51:44Z | - | - |

## SM Assessment (Setup)

### Scope: TDD Chrome Rendering (Tasks 18, 20–22)

This story implements server-side chrome for reference pages: per-pack theme injection (palette, fonts from theme.yaml), static CSS route serving bundled theme.css + styles.css, hero section with world name, and contents rail (TOC) with scroll-spy markup.

**Plan Reference:** docs/superpowers/plans/2026-05-23-reference-pages-v3.md  
Tasks 1–16 (v2 hyperlinks, protocol, UI) are merged on develop (PR #395, 2026-05-23).  
Task 19 (display_font_family) completed via story 63-3 (2026-05-24).  
This story covers Tasks 18, 20–22; Task 27 (validator + smoke tests) is story 63-5.

### Critical Dependencies & Constraints

1. **display_font_family dependency (63-3):** Must be in all genre_packs' theme.yaml before this story can assert AC2 (per-pack theme injection). Verified present in epic-63.yaml; 63-3 completed 2026-05-24. ✓

2. **Reference pages are server-rendered Python, not SPA:** The design bundle (docs/design-bundles/2026-05-23-lore-and-rules/) contains JSX prototypes and visual contracts. The renderer's job is to emit byte-equivalent HTML from the same inputs. No React, no client-side enrichment, no build step on the page. The bundle is a **visual contract, not runtime code.**

3. **Design-tool affordances must be stripped:** The bundled theme.css and styles.css include `.tweaks-panel`, `.tweaks-toggle`, `.tweaks-body` selectors used only during design iteration. These are **not product features**. AC4 requires they be verified absent from production CSS.

4. **Test discipline — no live-pack coupling:** Per project memory (no-content-coupled-tests), pytest must not load genre_packs/* and assert per-pack chrome properties. Unit tests use fixture packs. Live-pack coverage is the validator's job (separate CLI, not pytest). Task 24 (story 63-5) will implement the validator.

5. **No silent fallbacks — loud on missing fields:** Missing theme.yaml fields (display_font_family, archetype, dinkus.glyph.*, palette) must raise MissingThemeFieldError. Renderer routes must let it bubble to HTTP 500 + ERROR OTEL span. The bad-anchor banner (v2) already exists; new lore section falling back to pack name logs WARN, not silent.

6. **Rolled-in test gaps from 63-1 and 63-2 cancellations:**
   - AC5 (rolled-in from 63-1): write tests/server/test_reference_otel.py covering reference URL attached/skipped/failed spans against sidequest/telemetry/spans/reference.py helpers.
   - AC6 (rolled-in from 63-2): write sidequest-ui/src/components/__tests__/LocationPanel.reference.test.tsx mirroring CharacterSheet.reference.test.tsx pattern.
   These are included in acceptance criteria but not part of Tasks 18/20–22 proper work.

### Acceptance Criteria

1. Per-pack theme injection via `<html data-pack data-world data-archetype>` + palette/web_font_family/display_font_family from theme.yaml; missing fields = ERROR span, no fallback.
2. Static CSS route (`GET /reference/static/{theme,styles}.css`) returns 200 with correct content-type; CSS contains theme tokens (variables, fonts).
3. Dead .tweaks-* selectors verified absent from both production CSS files.
4. Hero section renders world name from lore.yaml + epigraph; falls back to pack name + WARN span if world unbound.
5. Contents rail (TOC) markup emitted server-side, locked (not toggleable), with IntersectionObserver scroll-spy hooks (~15 LOC inline JS).
6. Per-file section wrappers with stable `id` attributes; list-of-dict items namespaced (class-knight, culture-knight, etc.) per Task 2.
7. **ROLLED-IN from 63-1:** test_reference_otel.py covering reference URL spans against existing helpers.
8. **ROLLED-IN from 63-2:** LocationPanel.reference.test.tsx mirroring CharacterSheet pattern.

### Context Artifacts

- **Context file:** /Users/slabgorb/Projects/oq-1/sprint/context/context-story-63-4.md
- **Plan:** /Users/slabgorb/Projects/oq-1/docs/superpowers/plans/2026-05-23-reference-pages-v3.md (read Tasks 18, 20–22)
- **Design bundle:** /Users/slabgorb/Projects/oq-1/docs/design-bundles/2026-05-23-lore-and-rules/
- **Design spec:** /Users/slabgorb/Projects/oq-1/docs/superpowers/specs/2026-05-23-reference-pages-v2-design.md
- **v2 implementation (merged):** PR #395 on sidequest-server (Tasks 1–16: slugify, anchors, URL builders, protocol, UI panels)

### Blockers & Risks

- **None identified.** Branch state verified, dependencies met, worktree present.

---

## Delivery Findings

No upstream findings (setup phase).

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Gap** (blocking): AC8 (rolled-in from 63-2) requires writing `sidequest-ui/src/components/__tests__/LocationPanel.reference.test.tsx`, but `ui` is not in the story's `Repos` field and no UI branch was created at setup. Sm needs to either (a) expand 63-4's `Repos` to include `ui` and create a `feat/63-4-ref-chrome-theme-css-hero` branch on sidequest-ui so Dev can write+land the UI test alongside the server work, or (b) re-defer AC8 to a follow-up UI-only story and remove it from this story's AC list. TEA has flagged the UI test out of RED scope until this decision is made. Affects sprint coordination, not test code. *Found by TEA during test design.*

- **Improvement** (non-blocking): The design bundle at `docs/design-bundles/2026-05-23-lore-and-rules/` was missing from disk at RED start (in trash) and was restored mid-discovery by the user. The bundle is **not git-tracked** per the plan's Task 25 note ("the bundle is on disk but not yet git-tracked"). Task 25 (R2 upload of screenshots + README pointer + git-tracking the HTML/CSS/JSX) should sequence before this story's PR merges, or the bundle can be lost again and the next agent reading from `theme.css` / `styles.css` will hit a missing-file surprise. *Found by TEA during test design.*

- **Improvement** (non-blocking): `sidequest-server/sidequest/server/static/reference/reference.css` already exists on develop (Iteration 1's per-page stylesheet, 68 lines). After Task 20 wires theme.css + styles.css, the existing `_STYLESHEET_HREF = "/reference/static/reference.css"` constant in `reference_renderer.py:212` and the existing `test_stylesheet_route_serves_css` in `tests/server/test_reference_routes.py:111` will go stale. Dev should either delete reference.css and update both references, or document why it stays. RED tests do not enforce a decision here. *Found by TEA during test design.*

- **Gap** (non-blocking): The `archetype` field is not present in any current `theme.yaml` (verified against `sidequest-content/genre_packs/tea_and_murder/theme.yaml`). The design bundle's HTML pins specific values (`parchment`, `rugged`, `terminal`). Dev must add `archetype` to each `theme.yaml`, with paired content-side commits on the existing `feat/63-4-ref-chrome-theme-css-hero` branch in sidequest-content (per project memory [[project_genre_models_extra_forbid]] — content-only PRs for new fields are forbidden; needs paired server-side model update if a model validates theme.yaml). Coordinate with content team or extend Dev's scope. *Found by TEA during test design.*

- **Improvement** (non-blocking): The bundled `theme.css` (542 lines) and `styles.css` (1526 lines) **already have zero `.tweaks-*` selectors** — the strip step is preventive, not corrective. The `.tweaks-` UI lives only in the separate `tweaks-panel.jsx` file and the `<script type="text/babel" src="tweaks-panel.jsx">` tags in the bundle's demo HTML. Story description / SM assessment slightly overstate the cleanup work. AC4 regression-guard tests still ship to catch any future re-introduction. *Found by TEA during test design.*

---

## Design Deviations

None yet (setup phase).

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Hero/contents-rail tests split into a new file**
  - Spec source: context-story-63-4.md Task 21 + Task 22 "Test: `tests/server/test_reference_renderer.py` (new cases)"
  - Spec text: "Test: tests/server/test_reference_renderer.py (new cases)" for both Task 21 and Task 22
  - Implementation: Hero + contents-rail + scroll-spy tests live in a new file `tests/server/test_reference_chrome.py` (16 tests) instead of being appended to the existing `test_reference_renderer.py` (which is purely render_node/_render_dict unit tests).
  - Rationale: `test_reference_renderer.py` is 364 lines of pure-function walker tests; mixing in HTTP-style assemble_*_page chrome tests would dilute its focus. Keeping chrome tests separate makes the RED→GREEN diff for Dev cleaner and lets later refactors target one concern at a time.
  - Severity: minor
  - Forward impact: none — both files target the same module's behavior. Reviewer should expect chrome tests in `test_reference_chrome.py`, not in `test_reference_renderer.py`.

- **Deferred AC8 (UI test) out of RED scope**
  - Spec source: session ACs, AC8 (rolled-in from 63-2 cancellation)
  - Spec text: "ROLLED-IN from 63-2: LocationPanel.reference.test.tsx mirroring CharacterSheet pattern"
  - Implementation: No UI test written in RED. See blocking Delivery Finding above for the coordination gap.
  - Rationale: sidequest-ui is not in this story's `Repos` field; no UI branch was created at setup; writing a UI test in-place on sidequest-ui's develop checkout would create orphan commits per project memory [[feedback_subrepo_branches]].
  - Severity: major (one AC has zero test coverage in RED)
  - Forward impact: Dev cannot mark Story 63-4 as fully implemented until AC8 is either re-scoped (added back to a UI-aware setup) or formally re-deferred (removed from this story's AC list by SM). Reviewer must not approve the PR with AC8 unresolved.

---

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD workflow; 10-point story across new module, new routes, new markup, new spans.

**Test Files:**
- `tests/server/test_reference_theme.py` — 20 tests for Task 18 (ReferenceTheme loader, MissingThemeFieldError loud failures, `<html data-pack/data-world/data-archetype>` attribute emission, palette + font CSS-var injection, wiring test).
- `tests/server/test_reference_static.py` — 10 tests for Task 20 (`/reference/static/theme.css` + `/reference/static/styles.css` route surface, content-type + token-vocabulary checks, `.tweaks-panel/.tweaks-toggle/.tweaks-body` regression guards, `_wrap_document` emitting both link tags in correct order, negative paths).
- `tests/server/test_reference_chrome.py` — 16 tests for Tasks 21+22 (hero block contract: world name + epigraph + stable id + fallback + XSS escape, contents-rail markup: locked + scroll-spy hooks + file-section links + hero link, inline IntersectionObserver JS bounded ≤2KB, no external scroll-spy bundle, per-file section wrappers + Task 2 namespacing regression guards).
- `tests/server/test_reference_otel.py` — 13 tests for AC7 (rolled-in from 63-1: URL attached/skipped/failed span helpers) + new chrome-failure spans (SPAN_REFERENCE_THEME_MISSING for Task 18, SPAN_REFERENCE_HERO_UNBOUND for Task 21, plus FLAT_ONLY_SPANS registration).

**Tests Written:** 57 tests across 4 files (1,016 LOC).
**Status:** RED (43 failing, 14 passing — passes are pre-shipped behavior + negative guards).

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| No silent fallbacks | `test_missing_display_font_family_raises`, `test_missing_archetype_raises`, `test_missing_palette_primary_raises`, `test_missing_dinkus_glyph_raises`, `test_empty_theme_field_treated_as_missing`, `test_missing_theme_file_raises`, `test_wrap_document_loud_when_theme_missing` | failing |
| OTEL on subsystem decisions | `test_theme_missing_span_*`, `test_hero_unbound_span_*`, all five URL-span coverage tests (rolled-in 63-1) | failing (new spans) / passing (existing url spans) |
| One mechanism per problem | `test_no_external_scroll_spy_bundle`, `test_inline_scroll_spy_js_is_bounded` (rejects parallel SPA bundle) | passing (negative guard) / failing (waiting for inline JS) |
| XSS escape | `test_lore_page_hero_escapes_special_chars` (scoped to hero region) | failing |
| Wiring (component reachable from production paths) | `test_reference_theme_module_importable` | failing |
| Server-render only (no SPA bundle) | `test_no_external_scroll_spy_bundle` | passing |
| FLAT_ONLY_SPANS registration | `test_url_spans_registered_in_flat_only_set`, `test_chrome_failure_spans_registered_in_flat_only_set` | passing (URL) / failing (chrome) |
| Path-traversal hardening | `test_static_route_rejects_path_traversal` | passing |

**Rules checked:** 8 of 8 applicable project rules covered with test enforcement.
**Self-check:** 2 vacuous-pass tests caught and tightened (`test_lore_page_hero_includes_epigraph` and `test_lore_page_hero_escapes_special_chars` were passing because lore.yaml content flows through normal _render_scalar — anchored to hero region so they fail until the hero exists).

### Notes for Dev

1. **`reference_theme.py` is the right starting point.** All 20 tests in `test_reference_theme.py` depend on importing `load_reference_theme`, `MissingThemeFieldError`, `ReferenceTheme` from `sidequest.server.reference_theme`. Build that module first; many of the chrome and OTEL tests are unblocked once it exists.

2. **`_wrap_document` is the chrome hub.** Adding the theme link tags, data attributes, hero, contents rail, inline JS, and palette CSS-vars all funnel through one function in `reference_renderer.py:280`. Plan the rewrite as a single coherent function rather than a sequence of textual mutations to keep markup ordering testable.

3. **Add `archetype` to fixture and to all live `theme.yaml`.** The Gap finding above flags this. Until live packs have `archetype`, you can write the loader code, but live-pack smoke tests (story 63-5 territory) will fail. Coordinate the content-side commits on the existing `feat/63-4-ref-chrome-theme-css-hero` branch in `/Users/slabgorb/Projects/oq-1/sidequest-content`.

4. **Existing `reference.css` and its test.** `sidequest/server/static/reference/reference.css` still exists; `test_stylesheet_route_serves_css` at `tests/server/test_reference_routes.py:111` still tests for it. After theme.css + styles.css are wired, decide: delete reference.css (and that test) or keep both. Document the choice.

5. **Two existing tests will break shape after Task 18.** `test_reference_routes.py::test_rules_route_returns_html` asserts `assert r.headers["content-type"].startswith("text/html")`, which still holds. But any test that checks the literal `<html lang="en">` opener will break once data attrs land. Verify all current tests pass after green; do not delete a failing test until you've checked it's a stale-shape assertion, not a real regression.

6. **Span helpers follow `Span.open(name, attrs, tracer_override=_tracer)` pattern** — see `sidequest/telemetry/spans/reference.py` lines 64-126. Mirror that shape for the two new helpers (`reference_theme_missing_span`, `reference_hero_unbound_span`) — keyword-only args, contextmanager decorator, `_tracer` kwarg for tests. My OTEL tests inspect `tracer.start_as_current_span.call_args.kwargs["attributes"]` to verify attr dicts.

7. **The 14 passing tests are guard rails, not real green** — `test_no_external_scroll_spy_bundle` is a negative assertion that passes vacuously today and will keep passing as long as you don't add an external bundle. The Task 2 namespacing tests are regression guards for already-shipped behavior. The pre-shipped URL span tests confirm 63-1's intended coverage now exists. Do not interpret "14 passing" as "57% done" — the real RED→GREEN delta is 43 tests against new code.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for GREEN phase implementation.

---

### Dev (green)

- **Improvement** (non-blocking): Worktree symlinks `sidequest-content/` and `scenarios/` were added to `.claude/worktrees/` to let the full server suite resolve cross-repo path expectations (`Path(__file__).parents[N] / sidequest-content` resolves to `.claude/worktrees/sidequest-content/`). Without them, ~141 of 2058 server tests fail with `directory does not exist` from inside any subrepo worktree. These symlinks are local-only (the worktree's `.claude/` is gitignored), not committed. Worth a small dev-environment doc note or a `pf workflow setup` hook that creates them at worktree entry. *Found by Dev during green verification.*

- **Improvement** (non-blocking): The `test_genre` and `intent_test_pack` test fixtures lacked `archetype` in their `theme.yaml` and would have broken every consumer test on the new required field. I added `archetype: parchment` to both; flagging because a future story that adds another required theme.yaml field will hit the same surprise — these fixtures aren't currently in any "schema-coverage" lint that would catch the omission proactively. *Found by Dev during green verification.*

- **Decision recorded** (non-blocking): Deleted `sidequest/server/static/reference/reference.css` and removed `_STYLESHEET_HREF` constant rather than maintaining two stylesheet sources. The Task 20 bundle (theme.css + styles.css) fully supersedes the v1 single-stylesheet. Existing `test_stylesheet_route_serves_css` renamed to `test_stylesheet_route_serves_theme_css` and re-targeted at `/reference/static/theme.css`. *Recorded by Dev during green.*

---

### Dev (green)

- **archetype field added to test fixtures, not just live packs**
  - Spec source: context-story-63-4.md Risk Register §3 (test discipline)
  - Spec text: "Unit tests use fixture packs. Live-pack coverage is the validator's job."
  - Implementation: Added `archetype: parchment` to `tests/fixtures/packs/test_genre/theme.yaml` and `tests/fixtures/intent_test_pack/theme.yaml` (in addition to the new `tests/fixtures/packs/reference_v2_fixture/theme.yaml` and the 10 live `genre_packs/*/theme.yaml`).
  - Rationale: The new `archetype: str` field on `GenreTheme` (extra=forbid) is REQUIRED for the model to validate. Test fixtures that the model loads MUST have it — otherwise ~141 server tests across multiplayer, scene-harness, snapshot, encounter, and bootstrap suites fail with `1 validation error for GenreTheme`. This is not optional adjacent cleanup; it's a forced consequence of the model change. Documenting as a deviation only because it touches files outside the named Task 18/20-22 surfaces.
  - Severity: minor
  - Forward impact: none — fixtures now match the production model contract. Future theme.yaml fields will need the same fixture sync.

- **Existing `reference.css` deleted (TEA Improvement-3 disposition)**
  - Spec source: TEA Delivery Finding (improvement, non-blocking) — "Dev should either delete reference.css and update both references, or document why it stays."
  - Spec text: same
  - Implementation: Deleted the file and removed the constant + updated the existing test (`test_stylesheet_route_serves_css` → `test_stylesheet_route_serves_theme_css`). reference.css had a single tiny stylesheet of 68 lines totally superseded by the 2068-line bundle.
  - Rationale: Per memory `[[feedback_one_mechanism_per_problem]]` — never run two parallel stylesheets for the same surface.
  - Severity: minor
  - Forward impact: PR diff includes a file deletion and one test rename. Reviewer sees a clear "v1 → v3 chrome migration" delta.

- **Archetype assignment authored by Dev rather than escalated to content team**
  - Spec source: TEA Delivery Finding (gap, non-blocking) — "Dev must add `archetype` to each `theme.yaml`. Coordinate with content team or extend Dev's scope."
  - Spec text: same
  - Implementation: Dev picked `archetype` values for all 10 live packs (rugged/parchment/terminal) based on the design bundle's HTML files (5 packs are pinned there) and judgment for the remaining 5 (cosy-cosy → parchment, gritty/post-apoc/cowboy → rugged, sci-fi/dystopia → terminal).
  - Rationale: Async coordination with the content team would have stalled GREEN for an unbounded interval. Bundle-pinned packs follow the bundle. Non-pinned packs use the obvious tonal fit and are easy to change later (single-word string per pack).
  - Severity: minor
  - Forward impact: Content team / Sonia / playgroup may want to swap an archetype for a future world or pack. The trivial diff makes it cheap. Reviewer should flag if any assignment looks off — particularly for `road_warrior` and `spaghetti_western` which I gave `rugged` but `terminal` is also defensible for road_warrior (Mad Max signage typography). Architect's spec-check phase is the natural moment to challenge those.

---

## Dev Assessment

**Phase:** finish
**Status:** GREEN. 57/57 new 63-4 tests pass. Full server suite 1,891 passed / 0 failed / 167 skipped. Lint clean across all touched files. All 10 live `genre_packs/*/theme.yaml` validate against the new `GenreTheme.archetype` requirement.

### Implementation Summary

Two commits in two repos:
- **sidequest-server**: `363d662` on `feat/63-4-ref-chrome-theme-css-hero` (worktree at `.claude/worktrees/feat+63-4-ref-chrome-theme-css-hero`) — 17 files / +2434 / -98
- **sidequest-content**: `a5f9882` on `feat/63-4-ref-chrome-theme-css-hero` — 10 files / +10

These MUST land together. The server commit makes `archetype: str` required on `GenreTheme` (extra=forbid); the content commit adds the field to every pack. Either alone breaks the genre-pack loader.

### Files Changed

**New (server):**
- `sidequest/server/reference_theme.py` — 80 lines. `ReferenceTheme` dataclass + `load_reference_theme` loader + `MissingThemeFieldError`. Each missing-field path opens a `sidequest.reference.theme_missing` ERROR span and raises from inside it (correct OTEL error-status semantics).
- `sidequest/server/static/reference/theme.css` — 542 lines, copied verbatim from `docs/design-bundles/2026-05-23-lore-and-rules/project/theme.css`. Zero `.tweaks-*` selectors in source.
- `sidequest/server/static/reference/styles.css` — 1,526 lines, same bundle source.
- `tests/server/test_reference_theme.py`, `test_reference_static.py`, `test_reference_chrome.py`, `test_reference_otel.py` — TEA's RED tests, all now passing.
- `tests/fixtures/packs/reference_v2_fixture/theme.yaml` — new fixture file for the integration test pack.

**Modified (server):**
- `sidequest/server/reference_renderer.py` — `_wrap_document` overhaul; new private builders `_theme_style_block`, `_document_root_open`, `_build_contents_rail`, `_build_hero`, `_rail_entries_for`; inline 22-line IntersectionObserver `_SCROLL_SPY_SCRIPT` (≤1KB, guard-tested). `_STYLESHEET_HREF` constant removed. `assemble_rules_page` and `assemble_lore_page` now load theme + emit chrome data attrs + hero (lore only) + rail + dual stylesheet links.
- `sidequest/server/reference_routes.py` — only a stale comment update (was referencing `reference.css`; now `theme.css`).
- `sidequest/telemetry/spans/reference.py` — added `SPAN_REFERENCE_THEME_MISSING` + `SPAN_REFERENCE_HERO_UNBOUND` constants, registered both in `FLAT_ONLY_SPANS`, added their `@contextmanager` helpers following the established `Span.open(name, attrs, tracer_override=_tracer)` pattern.
- `sidequest/genre/models/theme.py` — `archetype: str` added to `GenreTheme` between `display_font_family` and `dinkus`. Inline comment notes the 3-value vocabulary (parchment/rugged/terminal) and the design-bundle origin.
- `tests/server/test_reference_routes.py` — `_seed_pack` writes a minimal theme.yaml; `test_stylesheet_route_serves_css` renamed and re-targeted to `theme.css`.
- `tests/server/test_reference_renderer.py` — `_write_pack` writes default theme.yaml unless caller overrides; one inline lore test got an explicit theme.yaml write.
- `tests/server/test_reference_renderer_bad_anchor.py` — `_make_fixture_pack` writes theme.yaml.
- `tests/fixtures/packs/test_genre/theme.yaml`, `tests/fixtures/intent_test_pack/theme.yaml` — `archetype: parchment` added (forced by the model change).

**Deleted (server):**
- `sidequest/server/static/reference/reference.css` — superseded by theme.css + styles.css.

**Modified (content):**
- `genre_packs/{caverns_and_claudes,heavy_metal,mutant_wasteland,road_warrior,spaghetti_western}/theme.yaml` — `archetype: rugged`.
- `genre_packs/{neon_dystopia,space_opera}/theme.yaml` — `archetype: terminal`.
- `genre_packs/{elemental_harmony,pulp_noir,tea_and_murder}/theme.yaml` — `archetype: parchment`.

### AC Coverage Check

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 — per-pack theme injection via data-pack/data-world/data-archetype, missing fields raise loud + ERROR span | `test_wrap_document_emits_data_*`, all `test_missing_*_raises`, `test_theme_missing_span_*` | passing |
| AC2 — static CSS route serves theme.css + styles.css with correct content-type, payload has theme tokens | `test_static_theme_css_*`, `test_static_styles_css_*`, `test_static_*_contains_*` | passing |
| AC3 — .tweaks-* selectors absent from production CSS (regression guard) | `test_static_theme_css_has_no_tweaks_selectors`, `test_static_styles_css_has_no_tweaks_selectors` | passing |
| AC4 — hero block with world name + epigraph, WARN-span fallback when unbound | `test_lore_page_emits_hero_with_world_name`, `test_lore_page_hero_includes_epigraph`, `test_lore_page_hero_falls_back_when_lore_missing`, `test_hero_unbound_span_*` | passing |
| AC5 — contents rail markup, locked, IntersectionObserver scroll-spy hooks | `test_lore_page_emits_contents_rail`, `test_contents_rail_is_locked_no_toggle`, `test_contents_rail_has_scroll_spy_hooks`, `test_inline_scroll_spy_js_*` | passing |
| AC6 — per-file section wrappers + Task 2 namespacing regression | `test_per_file_section_wrappers_have_stable_ids`, `test_listdict_item_ids_remain_namespaced` | passing |
| AC7 — rolled-in 63-1: reference URL spans (attached/skipped/failed) | all `test_url_*_span_*` | passing |
| **AC8 — rolled-in 63-2: LocationPanel.reference.test.tsx** | **NOT IMPLEMENTED** | **out of scope** |

### AC8 — Open Item for SM

**AC8 (rolled-in from 63-2) is not implemented in this story.** Per TEA's blocking Delivery Finding, sidequest-ui is not in the story's `Repos` field and no UI branch was created. I did not add UI scope unilaterally — that's SM's decision (Hawkeye). Two paths:

- (a) **SM expands 63-4's `Repos` to include `ui`**, creates `feat/63-4-ref-chrome-theme-css-hero` on sidequest-ui, and either I come back as Dev or a fresh dev pass handles the LocationPanel test against the now-merged PR for AC8 work.
- (b) **SM re-defers AC8 to a follow-up UI-only story** (e.g. `63-6` or `63-followup-A`), removes it from this story's AC list, and Reviewer treats 63-4 as scope-complete on the 7 server-side ACs above.

I have no opinion which is right — both are valid. The mismatch between the listed ACs and the listed Repos is the actual problem; either side can be adjusted.

### Quality Checks

| Check | Result |
|-------|--------|
| `uv run ruff check` on touched files | PASS — all checks passed |
| `uv run pytest -q tests/server/test_reference_*.py tests/server/test_reference_otel.py` (the four 63-4 files) | PASS — 57 passed |
| `uv run pytest -q tests/server/` (full server suite) | PASS — 1,891 passed / 0 failed / 167 skipped, 17.9s |
| Live-pack `GenreTheme.model_validate` smoke check | 10/10 packs validate cleanly |
| `git ls-files` on bundle dir before commit | bundle is gitignored / untracked per plan Task 25 — see TEA Improvement-2 |

### Notes for Architect (spec-check)

1. **Archetype vocabulary**: The bundle defines `[data-archetype="rugged"]` and `[data-archetype="terminal"]` rule families. There's no explicit `[data-archetype="parchment"]` rule family — `parchment` is presumably the default base style with no override needed. Architect should verify whether `parchment` is a documented archetype in the bundle's `theme.css` comments or just a label I derived. If the bundle only knows two archetypes (rugged + terminal) and an implicit default, my decision to call the default "parchment" might be wrong; alternatives: "base", "default", or simply leaving `archetype: rugged` for cosy packs too. Easy to refactor — single string per pack.
2. **Section id collision (pre-existing)**: When a world has `cultures.yaml` AND the pack also has `cultures.yaml` (which is the case for lore pages), the renderer emits two `<section class="file" id="file-cultures">` blocks. Browsers jump to the first on `#file-cultures` clicks. Not my regression — pre-existing since v2 — but the contents rail now makes it visible (two TOC entries point to the same id, second has "(genre)" suffix in the label only). Worth flagging for a real fix (e.g., `id="file-cultures-genre"` for the flavor section) but out of this story's scope.
3. **Inline `<style>` block injection vs CSS-route parameterization**: Per Risk Register §2 in context, I chose inline `<style>` blocks (per-request, varies by pack). Alternative was a `?pack=foo` CSS route parameter. Inline keeps the static route truly static + cacheable; per-pack tokens land in the document HEAD so styles.css can resolve them via `var(--ref-color-primary)`. Document this in the story-context update if Architect agrees.
4. **`reference_v2_fixture/theme.yaml`** is now committed. Previously it was missing from the fixture — the existing integration test passed without it because the renderer didn't require theme.yaml. Architect should note this is a *new constraint on the fixture pack* introduced by my story.

**Handoff:** To Architect (Major Margaret Houlihan) for spec-check phase.

---

### Architect (spec-check)

- **Decision recorded** (non-blocking): Verified bundle archetype vocabulary. `docs/design-bundles/2026-05-23-lore-and-rules/project/theme.css` defines exactly three `[data-archetype="..."]` rule families at lines 32 (`rugged`), 39 (`terminal`), and 233 (`parchment`). Dev's archetype assignments to the 10 live packs are architecturally sound. The bundle's `victoria` pack uses `parchment`; Dev's parity assignment of `tea_and_murder → parchment` follows the bundle's intent (cosy-mystery genre fit). No archetype-vocabulary deviation logged — Dev got it right. *Found by Architect during spec-check.*

- **Improvement** (non-blocking): The section-id collision Dev flagged (`<section id="file-cultures">` appearing twice on a lore page when world has cultures.yaml AND pack has cultures.yaml) is genuine but truly pre-existing — it predates 63-4 and would surface in any test that walks both source dirs. The contents rail makes the symptom more visible (two TOC entries pointing to the same anchor, browser jumps to first), but the underlying duplicate id is the v2 renderer's behavior. Recommend a follow-up story (`63-followup-A` or fold into `63-5` validator) to namespace flavor sections as `<section id="file-{stem}-genre">`. Architect endorses leaving the v2 behavior in place for this story. *Found by Architect during spec-check.*

- **Improvement** (non-blocking): Test-fixture theme.yaml duplication. The minimal-theme-yaml string appears verbatim across `test_reference_routes.py`, `test_reference_renderer.py`, `test_reference_renderer_bad_anchor.py`, `test_reference_chrome.py`, and `test_reference_static.py` (5 files). This mirrors the SDK-mock duplication 61-12 flagged for a follow-up story (`61-followup-D`). Recommend a paired follow-up to extract a shared `tests/server/_reference_fixtures.py` helper, OR fold both extractions into one larger "test-fixture-consolidation" story. Architect endorses the same defer-don't-refactor stance for 63-4's scope. TEA may surface this again in simplify-reuse during verify; the disposition stands. *Found by Architect during spec-check.*

---

### Architect (spec-check)

- **AC7 extended with two chrome-failure spans beyond 63-1 scope**
  - Spec source: session ACs, AC7 (rolled-in from 63-1)
  - Spec text: "ROLLED-IN from 63-1: test_reference_otel.py covering reference URL spans against existing helpers."
  - Implementation: Dev added two NEW span constants and helper context managers — `SPAN_REFERENCE_THEME_MISSING` / `reference_theme_missing_span` (for Task 18 missing-field path) and `SPAN_REFERENCE_HERO_UNBOUND` / `reference_hero_unbound_span` (for Task 21 unbound-world fallback). Both registered in `FLAT_ONLY_SPANS`. Tests in `test_reference_otel.py` cover all five span helpers (3 URL + 2 chrome).
  - Rationale: The AC named only URL-attached/skipped/failed coverage, but the new chrome-failure paths (theme.yaml missing field, lore.yaml unbound world) demand OTEL emission per the "OTEL on subsystem decisions" principle in `CLAUDE.md`. Without the two new spans, the GM panel would have no observability hook for chrome-render failures — exactly the "winging it" failure mode that doctrine forbids. Dev's extension is architecturally correct and load-bearing for AC1 (loud failure) and AC4 (WARN-span fallback) which both require OTEL.
  - Severity: minor
  - Forward impact: none — the additions strengthen observability without changing any public contract. Reviewer should treat the two new spans as legitimate Task 18/21 scope, not as AC7 over-spec.

- **AC5 inline scroll-spy script length: ~22 lines vs spec "~15 LOC"**
  - Spec source: session ACs, AC5
  - Spec text: "IntersectionObserver scroll-spy hooks (~15 LOC inline JS)"
  - Implementation: `_SCROLL_SPY_SCRIPT` in `reference_renderer.py` is approximately 22 lines (and well under 1KB minified). The load-bearing test (`test_inline_scroll_spy_js_is_bounded`) enforces ≤2KB rather than a line count.
  - Rationale: The spec used "~15" as an approximation, not a hard ceiling. The 22-line implementation includes the rootMargin tuning (`-30% 0px -60% 0px`), aria-current toggling for accessibility, and the `href^="#"` selector guard — all justified by the AC's intent (scroll-spy that works correctly). The byte-count test is the right invariant; line count is implementation detail.
  - Severity: trivial
  - Forward impact: none — no consumer relies on the script's exact line count.

- **AC8 (UI test) deferral remains open for SM**
  - Spec source: session ACs, AC8 (rolled-in from 63-2 cancellation)
  - Spec text: "ROLLED-IN from 63-2: LocationPanel.reference.test.tsx mirroring CharacterSheet pattern."
  - Implementation: Not implemented in 63-4. Out of scope per TEA + Dev assessments.
  - Rationale: Sidequest-ui is not in this story's `Repos` field. Adding it now would require setup-phase work (branch creation, fixture coordination) that the workflow does not support mid-implementation. TEA flagged blocking; Dev confirmed the path requires SM scope decision. Architect concurs: this is a sprint-coordination question, not an implementation question.
  - Severity: major (one AC has no test coverage)
  - Forward impact: Reviewer MUST NOT approve this story's PR until SM has formally dispositioned AC8 — either (a) expanding the story to include `ui` with paired branch + UI dev work, or (b) descoping AC8 to a follow-up story (e.g., `63-6` or `63-followup-A`) and removing it from this story's AC list. Both paths are valid; the choice is SM's. Architect's recommendation: **Option (b) — defer AC8 to a new UI-only story.** Reasoning: 63-4 is already 10 points and spans server + content with substantial scope (theme model, chrome renderer, CSS bundle copy, span helpers, fixture migrations). Adding UI scope mid-story risks blowing the points estimate AND mixes server-tier and ui-tier review concerns in a single PR. A dedicated 1-2pt UI-only follow-up keeps both diffs focused and reviewable.

---

## Architect Assessment (spec-check)

**Gate:** PASS (`gates/spec-check`). AC coverage table present, implementation flagged complete, both TEA and Dev deviation subsections properly formatted.

**Mismatch verdict:** Implementation aligns with spec on all 7 in-scope ACs. AC8 is the only outstanding gap and is a known coordination question, not a drift. No code changes required.

### AC-by-AC Alignment

| AC | Spec | Implementation | Mismatch | Severity | Resolution |
|----|------|----------------|----------|----------|------------|
| AC1 | data-pack/world/archetype + palette/fonts + loud-on-missing | `_document_root_open` emits attrs; `_theme_style_block` emits CSS vars; `MissingThemeFieldError` raises from inside `reference_theme_missing_span` | none | — | none |
| AC2 | `/reference/static/{theme,styles}.css` 200 + text/css + tokens | Bundle CSS copied + pre-existing route serves both | none | — | none |
| AC3 | .tweaks-* absent from production CSS | Bundle source had zero; regression guards committed | none | — | none |
| AC4 | Hero with world name + epigraph; pack-name + WARN-span fallback | `_build_hero` reads lore.yaml; two-branch fallback emits `reference_hero_unbound_span`; XSS-escaped via `escape(str(...))` | none | — | none |
| AC5 | Contents rail locked + scroll-spy ~15 LOC | `_build_contents_rail` + 22-line `_SCROLL_SPY_SCRIPT` (<1KB, guard-tested); no toggle markup | spec "~15" vs actual ~22 | trivial | A (update spec) — line count is approximate, byte-count test is the real contract |
| AC6 | Per-file section ids + Task 2 namespacing | Pre-existing behavior preserved; regression-guard tests committed | none | — | none |
| AC7 | Reference URL spans (3 helpers from 63-1 rollover) | All three URL span helpers covered; PLUS two new chrome-failure spans (theme_missing + hero_unbound) added | extra in code (2 new spans beyond 63-1 scope) | minor | A (update spec) — required by AC1/AC4 observability discipline, not over-spec |
| AC8 | LocationPanel.reference.test.tsx (UI repo) | NOT IMPLEMENTED | missing in code | major | D (defer to SM disposition before review) |

### Architectural Endorsements

1. **Module factoring is sound.** `reference_theme.py` as a thin loader with the dataclass is the right shape — no business logic mixed in, no premature abstractions, single responsibility. `_build_hero`, `_build_contents_rail`, `_theme_style_block`, `_document_root_open` are private helpers that read like the markup they produce. Easy to maintain.

2. **The "raise from inside a span" pattern is correct OTEL hygiene.** `_require_str` opens `reference_theme_missing_span` then raises `MissingThemeFieldError`. The span sees the exception status; the GM panel sees the failure as an ERROR-tier event with the missing-field attribute. This is the right shape for SideQuest's "OTEL on every subsystem decision" principle.

3. **The choice of inline `<style>` for per-pack CSS vars is correct.** Per-pack values vary per request (different pack → different palette); the static stylesheet route stays truly cacheable (single payload per file, no `?pack=foo` parameter). The inline `<style>` block is small (~250 bytes) and lives in HEAD where styles.css can resolve `var(--ref-color-primary)`. Architect confirms Dev's choice over the CSS-route parameterization alternative.

4. **The decision to delete `reference.css` is correct.** Per `[[feedback_one_mechanism_per_problem]]` and SideQuest's "no parallel systems" doctrine. The v1 stylesheet was fully superseded by the v3 bundle. Maintaining both would have invited drift.

5. **The reused FastAPI static route is correct reuse-first.** Dev did NOT introduce a new route subsystem — `/reference/static/{filename}` already existed from v1, just needed the new files dropped into `static/reference/`. Exactly the architectural restraint the agent role demands.

### Architectural Concerns Flagged for Follow-up (not blocking 63-4)

1. **Section-id collision** (Dev's #2 in handoff notes): pre-existing v2 behavior surfaces more visibly via the new contents rail. Two `<section id="file-cultures">` blocks when world + pack both have cultures.yaml; TOC links jump to first. Fix: namespace flavor sections as `<section id="file-{stem}-genre">` and update the rail builder to use the same id. Recommend a follow-up story.

2. **Test-fixture minimal-theme-yaml duplication** (5 test files now carry the same string). Mirror of the SDK-mock fixture duplication already flagged for `61-followup-D`. Recommend a paired or combined fixture-consolidation story; explicitly defer for 63-4 to keep the diff narrow.

3. **`reference_v2_fixture/theme.yaml` is now load-bearing** for the integration test pack. This was an implicit "the renderer doesn't need theme.yaml" assumption pre-63-4. Architect endorses making the fixture explicit; document this in the story-context update if a `63-followup-B` re-touches the integration test surface.

### Recommendation for SM (urgent — required before Reviewer can act)

**AC8 disposition is a blocker for PR creation.** SM must take ONE of these actions before the spec-reconcile phase (after Reviewer):

- **(a) Expand 63-4's `Repos` to `server,content,ui`**, create `feat/63-4-ref-chrome-theme-css-hero` on sidequest-ui, schedule a follow-up dev pass to add `LocationPanel.reference.test.tsx` mirroring `CharacterSheet.reference.test.tsx`. Estimate +1 point of work, total 11 points.
- **(b) Descope AC8 to a new UI-only story** (suggested name: `63-6 — Reference UI test parity for LocationPanel`, est. 1 point), remove AC8 from this story's AC list. **Architect recommends this option.** Cleaner separation of concerns; doesn't pollute the server diff with UI scope; the UI test is a small standalone piece that doesn't depend on rolling 63-4's server changes back into a worktree.

**Handoff:** To TEA (Radar O'Reilly) for verify phase (simplify + quality-pass).

---

### TEA (test verification)

- **No upstream findings during test verification.**

---

### TEA (test verification)

- **Verify-phase code edits applied beyond simplify-fix scope**
  - Spec source: TEA agent definition `<verify-workflow>` Step 5 ("Apply high-confidence fixes")
  - Spec text: "For each finding with confidence: high: Read the file at the specified line / Apply the suggestion (edit the file)"
  - Implementation: Verify phase edited 4 source files (reference_routes.py, reference_theme.py, reference_renderer.py, test_reference_static.py) and added one new integration test (`test_missing_theme_field_returns_500` in test_reference_routes.py). Total +68 / -17 across 5 files in commit `66e0376`. Three of the five fixes were HIGH-confidence simplify findings; one was LOW (rootMargin doc comment) applied opportunistically; one was a missing wiring test that the quality teammate flagged as HIGH on dead-code grounds.
  - Rationale: Per verify-workflow doctrine, the auto-apply scope is "high-confidence" findings. The rootMargin documentation comment was LOW but is a cheap boy-scout fix that adds no risk; flagging it as a deviation for traceability only. The integration test addition crosses the verify→red line (TEA writes a new test in verify, which usually only happens in red); justified because the test fills a HIGH-severity wiring gap the quality teammate identified and the verify-workflow gives the leader latitude to "auto-apply HIGH findings" without re-entering red.
  - Severity: minor
  - Forward impact: none — all changes preserve existing behavior; the new integration test adds coverage rather than changing it.

---

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed. Full server suite 1,892 passed / 0 failed / 167 skipped (1 more than green's 1,891 — the new MissingThemeFieldError integration test).

### Simplify Report

**Teammates:** simplify-reuse, simplify-quality, simplify-efficiency (Precognition crew)
**Files Analyzed:** 12 (5 production, 7 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | HIGH × 2 (theme-yaml string duplication across 5 test files; `_build_hero` two-branch fallback duplication). MED × 3 (pack-seeding helper overlap). |
| simplify-quality | 9 findings | HIGH × 4 (routes don't catch `MissingThemeFieldError` × 2; docstring/yaml.YAMLError mismatch; missing integration test for chrome-failure → 500). MED × 2 (type-safety in `_require_str`; archetype-field breaking-comment). LOW × 3 (naming bikeshed; rootMargin magic value; loose CSS-var assertion). |
| simplify-efficiency | clean | No findings — verified the 5 new private helpers (`_theme_style_block`, `_document_root_open`, `_build_contents_rail`, `_build_hero`, `_rail_entries_for`) all earn their existence per Architect's spec-check endorsement. |

**Applied (commit 66e0376):**

1. **reuse-HIGH**: Extracted `_hero_fallback(pack, world)` helper from `_build_hero`'s two identical fallback branches.
2. **quality-HIGH × 2**: Routes (`rules_page` + `lore_page`) now catch `(ValueError, MissingThemeFieldError)`. Imported `MissingThemeFieldError` from `reference_theme`. Real bug fix — without this, a pack with missing theme.yaml field would bubble as uncaught 500.
3. **quality-HIGH**: `load_reference_theme` wraps `yaml.safe_load` in `try/except yaml.YAMLError`, re-raising as `MissingThemeFieldError` to honor the docstring contract. Mirrors the existing pattern in `reference_renderer._render_file` line 258.
4. **quality-HIGH (dead-code)**: Added `test_missing_theme_field_returns_500` integration test in `test_reference_routes.py` covering both `/reference/rules/{pack}` and `/reference/lore/{pack}/{world}` paths returning 500 when theme.yaml lacks `archetype`. Was a wiring-test gap — `test_wrap_document_loud_when_theme_missing` proved the assembler raises, but no test covered the route catching it.
5. **quality-LOW (opportunistic)**: Documented the `_SCROLL_SPY_SCRIPT` rootMargin choice (`-30% 0px -60% 0px` defines the active band that avoids two-section flicker at boundaries). Cheap addition; no risk.
6. **quality-LOW**: Tightened `test_static_theme_css_contains_token_vocabulary` to require `--font-body` (a specific bundle token under `[data-archetype="parchment"]`) in addition to the generic `--` check. A truncated CSS copy would now trip the test.

**Dismissed (with rationale):**

- **reuse-HIGH** (`_MINIMAL_THEME_YAML` duplicated across 5 test files): Real duplication, but cross-test-file fixture imports are a documented project anti-pattern in SideQuest (no test module imports from another test module — verified by grep). Mirror of 61-12's same finding (SDK mock fixture duplication). The right fix is a `tests/server/_reference_fixtures.py` helper extracted in a dedicated follow-up story alongside the SDK mock extraction, in one atomic refactor. Out of scope for 63-4. Recommend `63-followup-A` or fold into `61-followup-D` if scoped together.
- **reuse-MED × 3** (pack-seeding helpers `_seed_pack` / `_write_pack` / `_make_fixture_pack`): Same disposition as above. The three helpers have subtly different signatures and serve subtly different test concerns; collapsing them is a refactor, not a simplify fix.

**Flagged for review (medium confidence, no auto-apply):**

- **quality-MED** (`_require_str` non-string coercion): `if value is None or (isinstance(value, str) and not value.strip())` accepts non-string scalars and silently coerces via `str(value)`. In practice, all theme.yaml fields are pydantic-validated upstream by `GenreTheme` (extra=forbid, all-string-typed). The renderer-side `load_reference_theme` is belt-and-suspenders — the model already rejected the non-string case before this loader runs. Tightening to `if not isinstance(value, str) or not value.strip()` is correct but unnecessary today. Defer; will become load-bearing if `GenreTheme` ever loses strict typing.
- **quality-MED** (archetype field comment doesn't note breaking nature): Real concern but the breaking nature is documented exhaustively in the Dev commit message (`a5f9882` content + `363d662` server, both reference "must land together"). A comment in `theme.py` would be redundant with prose that already exists. Defer.

**Noted (low confidence, no action):**

- **quality-LOW** (`_document_root_open` naming bikeshed): Reviewer can flag if they have a strong preference; rename touches every callsite for marginal clarity.

**Reverted:** 0.

**Overall:** `simplify: applied 5 high-confidence fixes + 1 low-confidence boy-scout fix`. All findings dispositioned with rationale.

### Quality Checks

| Check | Result |
|-------|--------|
| `uv run ruff check` on all 5 modified files | PASS — all checks passed |
| `uv run pytest -q tests/server/` (full server suite) | PASS — 1,892 passed / 0 failed / 167 skipped, 21.1s |
| `uv run pytest -q tests/server/test_reference_*.py` (63-4 scope + regression) | PASS — 121 passed / 3 skipped (live-pack tests) |
| `git log --oneline feat/63-4-ref-chrome-theme-css-hero` | 4 commits: RED → GREEN → simplify (66e0376) — clean phase progression |

### Live-Pack Sanity Check (Architect's spec-check #1 follow-up)

Spot-verified the rendered HTML for a fixture pack matches the Architect's spec endorsements:

- `data-archetype="parchment"` data-attr is correctly emitted on `<html>` for fixture packs whose theme.yaml carries `archetype: parchment`. The bundle's `[data-archetype="parchment"]` CSS rule (line 233 of bundle theme.css) will resolve at browser render time.
- Both `<link rel="stylesheet">` tags are emitted in correct order (theme.css before styles.css).
- Inline `<style>` block exposes `--ref-color-primary`, `--ref-color-accent`, `--ref-color-background`, `--ref-font-web`, `--ref-font-display` as CSS custom properties at `:root`.
- Hero block emitted for lore pages with stable `id="hero"`; falls back to pack name + WARN span when lore.yaml is absent (verified by `test_lore_page_hero_falls_back_when_lore_missing`).
- Contents rail `data-scroll-spy` markup present in both rules and lore pages with file-section anchor links.
- IntersectionObserver inline script under 1KB (the load-bearing 2KB ceiling).

### AC Coverage Confirmation (post-verify)

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 | `test_wrap_document_emits_data_*`, `test_missing_*_raises`, `test_theme_missing_span_*`, **NEW** `test_missing_theme_field_returns_500` | passing |
| AC2 | `test_static_theme_css_*`, `test_static_styles_css_*`, **TIGHTENED** `test_static_theme_css_contains_token_vocabulary` (now requires `--font-body`) | passing |
| AC3 | `test_static_theme_css_has_no_tweaks_selectors`, `test_static_styles_css_has_no_tweaks_selectors` | passing |
| AC4 | `test_lore_page_emits_hero_with_world_name`, `test_lore_page_hero_includes_epigraph`, `test_lore_page_hero_falls_back_when_lore_missing`, `test_hero_unbound_span_*` | passing |
| AC5 | `test_lore_page_emits_contents_rail`, `test_contents_rail_is_locked_no_toggle`, `test_contents_rail_has_scroll_spy_hooks`, `test_inline_scroll_spy_js_*` | passing |
| AC6 | `test_per_file_section_wrappers_have_stable_ids`, `test_listdict_item_ids_remain_namespaced` | passing |
| AC7 | all `test_url_*_span_*` + new chrome-failure span tests | passing |
| **AC8** | **NOT IMPLEMENTED — Architect recommended descope to follow-up story; still awaits SM disposition** | **deferred** |

### Follow-up Recommendations (for SM / Reviewer)

1. **`63-followup-A` (suggested): Test-fixture consolidation.** Extract `tests/server/_reference_fixtures.py` for the 5-file `_MINIMAL_THEME_YAML` + pack-seeding helpers. Pair with or rename `61-followup-D` (SDK mock extraction) for one atomic test-infrastructure refactor. Estimate 1-2 points.
2. **`63-6` (Architect-recommended): UI test parity for LocationPanel.** Address AC8 as a dedicated UI-only story. Mirror `CharacterSheet.reference.test.tsx` pattern. Estimate 1 point.
3. **`63-followup-B` (architectural debt): Section-id collision for pack flavor files.** Pre-existing v2 bug: `<section id="file-cultures">` emitted twice when world + pack both have cultures.yaml. The contents rail now makes this visible. Fix: namespace flavor sections as `file-{stem}-genre`. Estimate 1-2 points.

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

---

### Reviewer (review)

- **Improvement** (non-blocking): The `tests/genre/test_models/test_misc_models.py::TestGenreTheme::test_valid` regression that the preflight subagent caught is symptomatic of a verification-scope blindspot — Dev and Verify-phase TEA both ran `uv run pytest -q tests/server/` rather than the full project suite. Adding `archetype` to GenreTheme triggered the regression in a sibling `tests/genre/` test file that was outside the verification scope. Recommend a follow-up to either (a) widen the dev_exit / quality_pass gates to run the full project suite (not just `tests/server/`), or (b) introduce a small "schema-fixture coverage" lint that flags in-memory dict fixtures matching `GenreTheme.model_validate(_)` patterns when a required field is missing. Same class of issue as the test_genre/intent_test_pack fixture fixes Dev had to apply during green. *Found by Reviewer during code review.*

- **Improvement** (non-blocking): The python lang-review checklist (`.pennyfarthing/gates/lang-review/python.md`) is currently a manual self-review gate that Dev is expected to run pre-handoff. Reviewer caught the `open()` without `encoding=` violations (check #5) only by independently grepping the diff. Recommend wiring `pf check` (or a dev_exit gate extension) to actually invoke the python.md checklist as a haiku-model subagent during green-phase exit, so the violations surface before Reviewer. The current setup makes the checklist documentation rather than enforcement. *Found by Reviewer during code review.*

---

### Reviewer (review)

- **No deviations from spec.**

The Reviewer-phase fixes (test_misc_models.py fixture + 3 open() encoding= additions) are conformance corrections to existing spec requirements (lang-review check #5 + the implicit "tests pass" contract), not departures from spec. They restore the implementation to specification, not the other way around.

---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 blocking regression + 10 pre-existing worktree artifacts | confirmed 1 (FIXED in this phase), dismissed 10 (pre-existing per triage), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.edge_hunter: false` |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.silent_failure_hunter: false` |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.test_analyzer: false` |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.comment_analyzer: false` |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.type_design: false` |
| 7 | reviewer-security | Yes | findings | 2 (CSS injection medium, info-leakage low) | confirmed 2 (1 downgraded MINOR + recommend fix; 1 downgraded TRIVIAL + defer), dismissed 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.simplifier: false` |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.rule_checker: false` |

**All received:** Yes (2 enabled returned, 7 pre-filled as Skipped per settings)
**Total findings:** 5 confirmed (1 fixed in-phase, 2 from security, 2 from my own diff read), 0 dismissed, 0 deferred at gate level (some recommend-fix in this PR, some deferred to follow-up stories — see itemization)

---

## Reviewer Assessment

**Phase:** finish
**Status:** APPROVED WITH ONE PENDING SM ACTION (AC8 disposition).

### What changed in this phase

Commit `cf94e79` fixes two classes of finding the prior phases let through:

1. **[BLOCKING][TEST]** `tests/genre/test_models/test_misc_models.py::TestGenreTheme::test_valid` regression — one-line fix adding `"archetype": "parchment"` to the in-memory `_valid_data()` dict. Same fix Dev applied to the three YAML fixtures (`test_genre`, `intent_test_pack`, `reference_v2_fixture`) but missed because the dev/verify `pf check` scope was `tests/server/` only.

2. **[RULE][SEC-adjacent]** Three `path.open()` calls missing `encoding="utf-8"` parameter (python lang-review check #5, CWE-838). `reference_theme.py:69` (new), `reference_renderer.py:372` (new in 63-4), and `reference_renderer.py:292` (pre-existing, batched as boy-scout). Theme.yaml + lore.yaml carry unicode (dinkus `❧`, em-dashes, non-ASCII world names) — macOS-only deployment masks the bug, but the rule applies regardless and the pre-existing one was overdue.

### Rule Compliance

Read full python lang-review checklist (`.pennyfarthing/gates/lang-review/python.md`, 14 checks). Enumerating compliance for every type/function introduced or touched by this branch:

| # | Check | Surface | Verdict |
|---|-------|---------|---------|
| 1 | Silent exception swallowing | `reference_theme.py` (1 try/except), `reference_routes.py` (2 try/except), `reference_renderer.py` (1 try/except) | COMPLIANT — every except re-raises a typed domain error; no bare excepts; no `except: pass`. The `yaml.YAMLError → MissingThemeFieldError` chain in `reference_theme.py:70-78` is the gold standard for the rule. |
| 2 | Mutable default arguments | All new function signatures in `reference_theme.py`, `reference_renderer.py` (5 new private helpers), `spans/reference.py` (2 new ctxmgr helpers) | COMPLIANT — no mutable defaults. `_rail_entries_for(label_suffix: str = "")` uses empty str (immutable). |
| 3 | Type annotation gaps | All new public functions (`load_reference_theme`, `MissingThemeFieldError`, `ReferenceTheme`, `reference_theme_missing_span`, `reference_hero_unbound_span`) | COMPLIANT — full annotations on all public surfaces. `_require_str(value: Any, ...)` uses `Any` without explanatory comment (minor — `Any` is correct because YAML deserializes to mixed types; comment would be nice-to-have). |
| 4 | Logging coverage AND correctness | `reference_routes.py:115,126` (`_LOG.exception` inside except), no new `logger.info/warning/error` calls | COMPLIANT — `_LOG.exception` correctly used inside except blocks, no f-string log calls introduced, no sensitive data logged. The new chrome-failure paths use OTEL spans (theme_missing/hero_unbound) instead of stdlib logging which is the project pattern. |
| 5 | Path handling — `open()` without `encoding=` | `reference_theme.py:69`, `reference_renderer.py:292`, `reference_renderer.py:372` | **WAS NON-COMPLIANT, NOW FIXED in commit cf94e79.** All three calls now have `encoding="utf-8"`. |
| 6 | Test quality | All 4 new test files + 3 modified | COMPLIANT — no vacuous assertions (Radar caught two during red phase and tightened, plus simplify-quality flagged the loose `"--" in r.text` check which verify-phase tightened to `"--font-body"`). The Reviewer's fix to `test_misc_models.py` added a real field, not a vacuous assertion. |
| 7 | Resource leaks | All file opens in new code | COMPLIANT — all `path.open(...)` calls use `with` context manager. |
| 8 | Unsafe deserialization | `yaml.safe_load(fh)` at `reference_theme.py:71`, `reference_renderer.py:293` | COMPLIANT — both use `safe_load`, never `yaml.load`. No pickle, eval, exec, or shell=True. |
| 9 | Async/await pitfalls | `reference_routes.py` route handlers are `async def` | COMPLIANT — handlers await pure-Python work (`assemble_*_page` is sync, runs inline); no blocking I/O inside async, no missing awaits, no `asyncio.gather` introduced. |
| 10 | Import hygiene | All new imports | COMPLIANT — no star imports, no circular imports introduced (load_reference_theme imports from telemetry.spans.reference; reference_renderer imports from reference_theme — clean one-way dep). `Any` import is used. |
| 11 | Input validation at boundaries | `_resolve_pack_dir`, `_resolve_world_dir`, `_SAFE_STATIC_FILENAME` all pre-existing and unchanged | COMPLIANT — slug regex applied before any filesystem operation. `escape(...)` applied to all `world_name`, `epigraph`, `pack`, `world`, `archetype` values flowing into HTML attributes or element bodies. **HOWEVER:** see Reviewer-Security finding #1 — CSS values (palette, fonts) in the inline `<style>` block are NOT validated/escaped. Downgraded to MINOR given single-user trusted-content threat model; fix recommended in follow-up. |
| 12 | Dependency hygiene | `pyproject.toml` unchanged | COMPLIANT — no new dependencies. |
| 13 | Fix-introduced regressions | Verify-phase commit `66e0376` reviewed against checks #1-#12 | COMPLIANT — the verify-phase added new try/except (specific type), tightened an assertion, no new violations. The Reviewer-phase commit `cf94e79` re-verified: encoding= addition introduces no new check violations. |
| 14 | State cleanup ordering with fallible side effects | No queue/buffer/register pattern in the diff | N/A — 63-4 is request-time rendering, no one-shot lifecycle queues. |

### Findings Table (consolidated)

| Tag | File:Line | Severity | Source | Finding | Disposition |
|-----|-----------|----------|--------|---------|-------------|
| [TEST][RULE] | `tests/genre/test_models/test_misc_models.py:54` | **was BLOCKING** | preflight HIGH | `_valid_data()` dict missing `archetype` field after GenreTheme model change | **FIXED in commit cf94e79** |
| [RULE] | `sidequest/server/reference_theme.py:69` | MINOR | self-review (lang-review #5) | `theme_path.open()` without `encoding=` (CWE-838) | **FIXED in commit cf94e79** |
| [RULE] | `sidequest/server/reference_renderer.py:372` | MINOR | self-review (lang-review #5) | `lore_path.open()` without `encoding=` (CWE-838) | **FIXED in commit cf94e79** |
| [RULE][PRE-EXISTING] | `sidequest/server/reference_renderer.py:292` | MINOR | self-review (lang-review #5) | Pre-existing `path.open()` without `encoding=` in `_render_file` | **FIXED in commit cf94e79** (boy-scout, one-character batch with above) |
| [SEC][RULE] | `sidequest/server/reference_renderer.py:322-329` | MINOR (was MEDIUM) | reviewer-security | CSS injection: theme.yaml palette + font values interpolated into inline `<style>` block without sanitization | **CONFIRMED, downgrade rationale:** SideQuest threat model is single-user (Keith), content packs are operator-authored not user-uploaded. A CSS-injection by the operator is no worse than the operator already writing the renderer themselves. Per lang-review #11, escape is required for "user input" — pack YAML is not user input under the deployed threat model. **Recommend a follow-up story** (`63-followup-C`): add CSS-value validation in `_theme_style_block` — palette must match `/^#[0-9a-fA-F]{3,8}$/`, font-family must reject `{`, `}`, `;`, `(`, `)`. Estimate 1 point. Reviewer does NOT block on this for 63-4. |
| [SEC] | `sidequest/server/reference_routes.py:116,127` | TRIVIAL (was LOW) | reviewer-security | `detail=str(exc)` forwards raw exception message (including filesystem paths) to 500 response body | **CONFIRMED, downgrade rationale:** Cloudflare Zero Trust auth gate means only Keith ever sees these. The information leakage is to the operator who already has SSH access. Recommend a follow-up story (`63-followup-D`) to switch to a generic 500 body + structured server-side log + OTEL span, but not for 63-4. Reviewer does NOT block. |
| [DOC] | `sidequest/server/reference_theme.py:43` | TRIVIAL | self-review (lang-review #3) | `_require_str(value: Any, ...)` uses `Any` without explanatory comment | **DEFERRED** — `Any` is correct (YAML deserializes to mixed types); the function's role is to validate-and-coerce. Comment would be padding. Acceptable. |

### AC Coverage (final)

| AC | Status | Notes |
|----|--------|-------|
| AC1 — Per-pack theme injection + ERROR span on missing fields | ✅ PASS | Tests + integration test (added in verify) all green |
| AC2 — Static CSS route + tokens | ✅ PASS | Both files served, tokens verified via tightened assertion |
| AC3 — .tweaks-* selectors absent | ✅ PASS | Regression guards pass; bundle source had zero |
| AC4 — Hero with world name + WARN fallback | ✅ PASS | XSS escape scoped to hero region per Radar's tightening |
| AC5 — Contents rail + scroll-spy | ✅ PASS | ~22 LOC inline JS, under 1KB ceiling; locked (no toggle) |
| AC6 — Per-file section ids + Task 2 namespacing | ✅ PASS | Regression guards confirm pre-existing v2 behavior preserved |
| AC7 — Reference URL spans (rolled-in 63-1) | ✅ PASS | All 5 span helpers covered (3 URL + 2 new chrome-failure) |
| **AC8 — LocationPanel.reference.test.tsx (rolled-in 63-2)** | ⚠️ **PENDING SM** | Not implemented; Architect recommended descope to `63-6`. **Reviewer will NOT approve final PR until SM dispositions this.** |

### Final Quality Checks

| Check | Result |
|-------|--------|
| `uv run ruff check` on touched files | PASS — all checks passed |
| `uv run pytest -q` (full project suite) | 7,556 passed / 10 failed / 375 skipped |
| Of those 10 failures: genuine 63-4 regressions | **0** |
| Of those 10 failures: pre-existing worktree-environment artifacts | 10 (preflight triaged + Reviewer confirmed — all pass on canonical sidequest-server/ checkout) |
| Sub-suite `tests/server/` | 1,892 passed / 0 failed / 167 skipped |
| `tests/genre/test_models/test_misc_models.py` (newly-fixed) | 16 passed / 0 failed |
| `tests/server/test_reference_*.py` (63-4 + sibling) | 121 passed / 3 skipped (live-pack tests) |

### Disposition

**APPROVE-WITH-PENDING.** Code itself is ready. Two pre-merge conditions remain, NEITHER of which Reviewer can resolve:

1. **SM must disposition AC8.** Architect recommended Option (b): descope AC8 to a new UI-only story (`63-6`), remove from this story's AC list. Reviewer concurs. Once SM updates the story scope, this gate clears.

2. **PR has not yet been opened.** When SM creates the PR, both commits (server `cf94e79` + content `a5f9882`) must land together — the GenreTheme model change requires the content archetype field to be present.

If both conditions are met, Reviewer approves. The actual code review found no blocking technical defects after the in-phase fixes; the CSS injection finding is real but downgraded to a follow-up story under the single-user-operator threat model.

### Follow-up Stories Recommended (in addition to those TEA/Architect named)

- **`63-followup-C`**: CSS-value validation in `_theme_style_block`. Add allowlist for palette (`#XXX`/`#XXXXXX`/`rgb(...)`) and font-family (alphanumeric + space + comma + apostrophe + hyphen). Closes the security-medium finding. Estimate 1 point.
- **`63-followup-D`**: Generic 500 body + structured log for reference page render failures. Closes the security-low finding. Estimate 1 point.
- **`pennyfarthing-followup`** (orchestrator-side, not a SideQuest story): Wire the python lang-review checklist (`.pennyfarthing/gates/lang-review/python.md`) into the green-phase `dev_exit` gate or `pf check`, so the encoding= class of violation surfaces pre-handoff instead of at Reviewer time. Discussed in Reviewer Delivery Findings above.

**Handoff:** To Architect (Major Margaret Houlihan) for spec-reconcile phase (per workflow YAML: review → spec-reconcile → finish).

---

### Architect (reconcile)

- **No additional deviations found.**

Reviewed every entry under TEA (test design + verification), Dev (green), Architect (spec-check), and Reviewer (review). All deviation entries carry the required 6 fields. Spec sources cited resolve to real artifacts on disk (verified during spec-check: plan at `docs/superpowers/plans/2026-05-23-reference-pages-v3.md`, design bundle at `docs/design-bundles/2026-05-23-lore-and-rules/`, design spec at `docs/superpowers/specs/2026-05-23-reference-pages-v2-design.md`, context file at `sprint/context/context-story-63-4.md`, lang-review checklist at `.pennyfarthing/gates/lang-review/python.md`). Spec text quotations are accurate.

**Field-level audit notes:**

- TEA (test design) ×5 findings + 2 deviations: All 6 fields present where the deviation format requires them; Delivery Findings use the lighter Type/Urgency format which is also conformant. The "blocking" UI Gap finding (AC8) traces correctly through Dev, Architect, and Reviewer subsections — every downstream agent acknowledged and threaded the deferral.

- Dev (green) ×3 findings + 3 deviations: The "archetype field added to test fixtures, not just live packs" deviation correctly notes the forced consequence (Pydantic model + extra=forbid means fixture sync is mandatory, not optional). The "Existing reference.css deleted" deviation correctly cites TEA Improvement-3 as the spec source. The "Archetype assignment Dev-authored" deviation correctly notes the design-bundle parity for the 5 pinned packs and the judgment-call basis for the 5 non-pinned packs.

- Architect (spec-check) ×3 findings + 3 deviations: The AC7 chrome-failure-span extension is correctly characterized as architecturally load-bearing (Tasks 18/21 demand loud OTEL by SOUL.md doctrine), not over-spec. The AC5 ~22-vs-~15 LOC deviation correctly identifies the load-bearing test (byte-count ceiling, not line count) and properly downgrades severity to trivial. The AC8 deferral analysis correctly enumerates both resolution options for SM.

- TEA (test verification) ×1 finding + 1 deviation: The "verify-phase code edits beyond simplify-fix scope" deviation correctly notes the addition of one new integration test (`test_missing_theme_field_returns_500`) that crosses verify→red lines; the rationale (HIGH-severity wiring gap, verify-workflow latitude) is sound.

- Reviewer (review) ×2 findings + "No deviations from spec": The conformance characterization is correct — fixing the GenreTheme `_valid_data()` fixture and adding `encoding="utf-8"` to three `open()` calls restore compliance to existing spec contracts (model + lang-review check #5), not departures.

**AC deferral cross-check:**

The ac-completion gate (Dev exit) recorded one deferred AC: AC8 (LocationPanel.reference.test.tsx, rolled in from 63-2). Reviewer's findings did NOT inadvertently address or invalidate the deferral — every downstream agent (Dev, Architect, Reviewer) explicitly noted AC8 as out-of-scope pending SM disposition. The deferral remains in the same state at spec-reconcile time as it was at Dev-exit time:

- **AC8 status:** DEFERRED, pending SM scope-decision.
- **Recommended path (consensus of Architect + Reviewer):** Option (b) — descope AC8 from this story's AC list, create a new UI-only story (`63-6 — Reference UI test parity for LocationPanel`, 1 point) for the rolled-in test.
- **SM action required at finish-phase:** Either expand 63-4's `Repos` to include `ui` (and schedule additional UI dev work, ~+1 pt), OR create `63-6` and remove AC8 from this story's AC list before opening the PR.

**Final deviation manifest assertion:** Complete. Reviewer's APPROVE-WITH-PENDING verdict is the correct read of the work — the technical implementation is done and tested; the only open item is the sprint-coordination question on AC8.

**Handoff:** To SM (Hawkeye Pierce) for finish phase. SM must address the AC8 disposition (recommended: descope to `63-6`) before opening the PR.

---

## SM Finish — AC Disposition + Closeout

**Phase:** finish
**Status:** PRE-PR (sm-finish ceremony pending)

### AC8 disposition (recorded per Doctor's call 2026-05-24)

Doctor selected **Option (b): Descope AC8 to new `63-6`** (Architect + Reviewer's consensus recommendation).

**Actions taken:**
1. Created story `63-6 — Reference UI test parity for LocationPanel (rolled-in from 63-2)` (1 pt, p2, tdd workflow, repos: ui).
2. AC8 is hereby formally removed from 63-4's effective AC list. The original AC text remains in the SM Assessment (Setup) section above as historical record; the AC accountability table below is the authoritative current state.

### AC Accountability Table (final)

| AC | Original Text | Status | Resolution |
|----|---------------|--------|-----------|
| AC1 | Per-pack theme injection via `<html data-pack data-world data-archetype>` + palette/fonts; missing fields = ERROR span, no fallback | DONE | Implemented in `_wrap_document`, `_theme_style_block`, `_document_root_open`, `load_reference_theme`. Span: `sidequest.reference.theme_missing`. Tests: 20 in `test_reference_theme.py` + `test_missing_theme_field_returns_500` integration. |
| AC2 | Static CSS route `GET /reference/static/{theme,styles}.css` returns 200 + text/css; CSS contains theme tokens | DONE | Bundle CSS copied verbatim to `sidequest/server/static/reference/`. Existing static route serves both. Tests: 10 in `test_reference_static.py` (including tightened `--font-body` assertion from verify). |
| AC3 | Dead .tweaks-* selectors absent from both production CSS files | DONE | Bundle source had zero `.tweaks-` selectors; regression guards committed in `test_reference_static.py`. |
| AC4 | Hero with world name + epigraph; pack-name + WARN span fallback | DONE | `_build_hero` + `_hero_fallback` + `reference_hero_unbound_span`. XSS escape scoped to hero region (Radar's tightening). Tests cover both bound and unbound paths. |
| AC5 | Contents rail markup, locked (not toggleable), IntersectionObserver scroll-spy hooks (~15 LOC inline JS) | DONE | `_build_contents_rail` emits locked nav with `data-scroll-spy`. `_SCROLL_SPY_SCRIPT` is 22 LOC / ~585 bytes (under 2KB guard). Tests verify locked state and presence. |
| AC6 | Per-file section wrappers + Task 2 namespacing regression | DONE | Pre-existing v2 behavior preserved; regression guards in `test_reference_chrome.py`. |
| AC7 | ROLLED-IN from 63-1: test_reference_otel.py covering URL spans | DONE | All 3 URL span helpers tested (`reference_url_attached/skipped/failed_span`) + 2 new chrome-failure spans added in 63-4 (`reference_theme_missing_span`, `reference_hero_unbound_span`). 13 tests in `test_reference_otel.py`. |
| AC8 | ROLLED-IN from 63-2: LocationPanel.reference.test.tsx mirroring CharacterSheet pattern | **DESCOPED → 63-6** | Doctor disposition 2026-05-24: descoped to dedicated UI-only follow-up story `63-6` (1 pt). LocationPanel test will be authored against the post-merge 63-4 server state. |

### Phase Commit Summary

| Phase | Repo | Commit | Note |
|-------|------|--------|------|
| red | server | `4414704` | 4 new test files / 1,016 LOC failing tests |
| green | server | `363d662` | reference_theme.py + reference_renderer.py rewrite + GenreTheme model + CSS bundle copy + fixture updates |
| green | content | `a5f9882` | archetype added to 10 packs (rugged/parchment/terminal) |
| verify | server | `66e0376` | simplify fixes (5 high-confidence applied) |
| review | server | `cf94e79` | reviewer fixes (GenreTheme test fixture + 3× encoding= compliance) |

**5 commits total: 4 server + 1 content.** Both branches must land in their PRs together (server requires content's archetype field; content requires server's archetype model).

### Follow-up Stories Created / Recommended

| ID | Title | Points | Status |
|----|-------|--------|--------|
| 63-6 | Reference UI test parity for LocationPanel (rolled-in from 63-2) | 1 | **CREATED** during this finish phase per Doctor's disposition |
| 63-followup-A | Test-fixture consolidation (`_MINIMAL_THEME_YAML` + pack-seeding helpers) | 1-2 | RECOMMENDED (pair with `61-followup-D` SDK mock extraction) |
| 63-followup-B | Section-id collision for pack flavor files (`<section id="file-cultures">` duplicate) | 1-2 | RECOMMENDED (pre-existing v2 debt surfaced by contents rail) |
| 63-followup-C | CSS-value validation in `_theme_style_block` (closes security-medium finding) | 1 | RECOMMENDED |
| 63-followup-D | Generic 500 body + structured log for reference page render failures (closes security-low finding) | 1 | RECOMMENDED |
| (pennyfarthing-side) | Wire python lang-review checklist into `dev_exit` gate so encoding= class violations surface pre-handoff | — | Cross-project recommendation (orchestrator tooling) |