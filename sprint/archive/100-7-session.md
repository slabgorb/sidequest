---
story_id: "100-7"
jira_key: ""
epic: "100"
workflow: "tdd"
---
# Story 100-7: Phase 1 — Theme tokens in projection JSON (theme.yaml -> CSS-var token set, C3)

## Story Details
- **ID:** 100-7
- **Jira Key:** (N/A — SideQuest does not use Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p2
- **Repos:** sidequest-server

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-09T00:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-09 | - | - |

## Story Context

Part of epic 100 (Reference pages → React SPA migration). This story projects a pack's `theme.yaml` (palette/fonts/dinkus — CSS STYLING, genre/app-tier) into the projection JSON as a CSS-var token set. This feeds the Phase-2 session-free theme injector (story 100-9, UI) which sets CSS vars from the projection JSON instead of the WS `theme_css` channel.

**Key Facts:**
- `theme.yaml` is STYLING, not Rules/Lore flavor — it is public CSS tokens, NOT keeper-firewalled content like lore/rules
- Just-merged siblings to mirror projection mechanics: 100-2 (generic section), 100-4 (POI), 100-5 (Timeline), 100-6 (Rules page — closest analog, pack/genre-tier)
- TEA should still confirm `theme.yaml` carries no GM-only/keeper fields before assuming the whole file is safe to project
- Epic spec: `docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md`

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `ReferenceTheme` (`reference_theme.py`) only loads `primary/accent/background` from the palette — it does NOT carry `secondary/surface/text`. The pinned CSS-var contract requires all six palette vars (the shared `useGenreTheme` contract). Dev must either extend `ReferenceTheme` + `load_reference_theme` to load secondary/surface/text, or read `theme.yaml` directly in `build_theme_tokens`. *Found by TEA during test design.*
- **Conflict** (non-blocking): attaching `theme` INSIDE `build_rules_projection` would break the merged sibling test `test_reference_rules_projection.py::test_rules_projection_omits_absent_files` (seeds an empty pack, no theme.yaml, expects `sections == []`). If theme load is unconditional inside the projector, that case now raises `MissingThemeFieldError`. **Recommended:** attach the token set at the ROUTE layer (`rules_api`/`lore_api` set `doc["theme"] = build_theme_tokens(...)`), keeping the pure projection builders + their tests untouched. The theme tests assert the OBSERVABLE HTTP contract (`resp.json()["theme"]`), so either seam passes — route-layer avoids touching a merged story's test. *Found by TEA during test design.*
- **Improvement** (non-blocking): `archetype` is an HTML attribute-selector value (`[data-archetype="..."]`), NOT a CSS var — intentionally EXCLUDED from the token dict. If the Phase-2 injector needs it, expose it as a sibling doc key (`doc["archetype"]`), not inside `doc["theme"]`. Not pinned by these tests. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The rules/lore JSON endpoints now require a pack `theme.yaml`
  (loud 500 on absent/incomplete), consistent with the existing HTML rules/lore routes which already
  require it via `load_reference_theme`. Three sibling synthetic endpoint fixtures were under-shaped —
  they seeded packs with no `theme.yaml` and so 500'd after this change. I seeded a minimal prod-faithful
  `theme.yaml` in each (`test_reference_api_lore`, `test_reference_rules_projection`,
  `test_reference_timeline_projection`). **Forward note:** any future test driving
  `GET /reference/api/{rules,lore}` against a synthetic pack must seed `theme.yaml`. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **No keeper-firewall dimension (vs. literal task framing).** The task said "confirm theme.yaml carries no GM-only/keeper field; if it does, add a firewall test." CONFIRMED there is none: `GenreTheme` (`genre/models/theme.py`) is `extra="forbid"` over styling-only fields, and `reference_visibility.py` has no `theme` carve. So NO `classify()`/keeper-absence test was written. Instead the security spine is an **allowlist** test: an internal non-CSS field (`border_style`, `dinkus.cooldown/default_weight`, `session_opener`, an authored `_note`) must NOT leak into the CSS-var token set. Positive-control (`test_raw_splat_would_leak_internal_but_tokens_do_not`) mutation-proves non-vacuity: the value IS in raw theme.yaml, ABSENT from tokens.
- **CSS-var contract pinned.** Six palette vars `--primary/--secondary/--accent/--background/--surface/--text` (shared `useGenreTheme` contract, non-negotiable); fonts `web_font_family→--font-body`, `display_font_family→--font-display`; dinkus `light/medium/heavy→--dinkus-{light,medium,heavy}`. Return shape: FLAT `dict[str,str]` (`{"--var": "value"}`) for direct `setProperty` iteration by the 100-9 injector. Attachment: top-level `doc["theme"]` on BOTH `/reference/api/rules/{pack}` and `/reference/api/lore/{pack}/{world}`.
- **No live-pack assertions (overrides "verify against space_opera").** Per project rule, the end-to-end tests point the real FastAPI router at a SYNTHETIC tmp pack mirroring space_opera's theme.yaml shape, not the live pack.
- **All presence/absence asserts use `json.dumps(ensure_ascii=False)`** (firewall-test discipline carry-forward) so non-ASCII dinkus glyphs (✦ ⬡ †) are verbatim and substring checks are non-vacuous.

### Dev (implementation)
- **Route-layer attachment (heeded TEA's Conflict finding).**
  - Spec source: session Delivery Findings, TEA Conflict (non-blocking)
  - Spec text: "attach the token set at the ROUTE layer, keeping the pure projection builders + their tests untouched"
  - Implementation: `doc["theme"] = build_theme_tokens(pack, pack_dir=pack_dir)` in BOTH `rules_api` and `lore_api` (`reference_routes.py`), inside the existing `try` so `MissingThemeFieldError` surfaces as the route's existing 500. `build_rules_projection`/`build_lore_projection` are untouched.
  - Rationale: keeps the merged `test_rules_projection_omits_absent_files` (empty pack, no theme.yaml) green and the projection builders pure.
  - Severity: minor
  - Forward impact: none — Phase-2 (100-9) consumes `doc["theme"]` regardless of seam.
- **`build_theme_tokens` reads theme.yaml directly; shared loader extracted (heeded TEA's Gap finding).**
  - Spec source: session Delivery Findings, TEA Gap (non-blocking)
  - Spec text: "`ReferenceTheme` ... does NOT carry `secondary/surface/text` ... read `theme.yaml` directly in `build_theme_tokens`"
  - Implementation: extracted `_read_theme_yaml(pack_dir) -> (data, pack)` in `reference_theme.py` (the existing file-load/loud-fail boilerplate, now shared by `load_reference_theme`); `build_theme_tokens` in `reference_projection.py` reads the raw dict and maps the curated 11-key allowlist via the existing `_require_str` loud-fail helper. `ReferenceTheme` left unchanged (no need to grow the chrome dataclass for three styling-only fields).
  - Rationale: DRY reuse of the loud-failure machinery without expanding the chrome model; allowlist (not splat) is the security spine.
  - Severity: minor
  - Forward impact: none.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New projection contract — `theme.yaml` → CSS-var token set in projection JSON.

**Test Files:**
- `sidequest-server/tests/server/test_reference_theme_projection.py` — 14 tests, 4 groups (unit token dict, allowlist firewall, loud-failure, end-to-end HTTP wiring on both rules + lore endpoints).

**Tests Written:** 14 tests
**Status:** RED — `ImportError: cannot import name 'build_theme_tokens'` (contract function does not exist yet; correct RED reason).

**Pinned contract:**
- `build_theme_tokens(pack: str, *, pack_dir: Path) -> dict[str, str]` in `reference_projection.py`. Flat CSS-var dict, curated allowlist:
  `--primary --secondary --accent --background --surface --text` (palette, from theme.yaml six colours),
  `--font-body` (web_font_family), `--font-display` (display_font_family),
  `--dinkus-light/-medium/-heavy` (dinkus.glyph.*). Missing required field → `MissingThemeFieldError` (loud).
- Attaches as top-level `doc["theme"]` on `GET /reference/api/rules/{pack}` AND `GET /reference/api/lore/{pack}/{world}` (route-layer attachment recommended — see Delivery Findings).
- **No keeper-firewall dimension** (theme.yaml is public styling). Security = allowlist discipline (no internal config leaks into token set).

**Handoff:** To Dev for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/server/reference_theme.py` — extracted shared `_read_theme_yaml(pack_dir) -> (data, pack)` (the existing file-load + loud-fail boilerplate); `load_reference_theme` now delegates to it.
- `sidequest-server/sidequest/server/reference_projection.py` — added `build_theme_tokens(pack, *, pack_dir) -> dict[str, str]`: curated 11-key CSS-var allowlist (six palette + two font + three dinkus), loud-fail via `_require_str`. No keeper firewall (public styling); allowlist discipline is the security spine.
- `sidequest-server/sidequest/server/reference_routes.py` — attach `doc["theme"] = build_theme_tokens(...)` at the route layer in BOTH `rules_api` and `lore_api` (inside existing try → 500 on missing theme).
- `sidequest-server/tests/server/test_reference_api_lore.py`, `test_reference_rules_projection.py`, `test_reference_timeline_projection.py` — seeded a minimal prod-faithful `theme.yaml` in each endpoint fixture (these synthetic packs were under-shaped; real packs always carry theme.yaml).

**Tests:** 12/12 new (`test_reference_theme_projection.py`) passing. Full `tests/server/` suite: **3100 passed, 0 failed, 501 skipped** (GREEN, no regressions — the 4 sibling endpoint tests fixed by prod-faithful fixtures).
**Lint/format:** `ruff check` + `ruff format --check` clean on all 7 diff files (incl. TEA's test file). `pyright` 0 errors on changed source.
**Branch:** `feat/100-7-theme-tokens-projection-json` (pushed)

**Handoff:** To review.
