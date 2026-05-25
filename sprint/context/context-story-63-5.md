# Story 63-5: Cleanup — live-pack validator, tropes exclusion, R2 screenshots, final gate

**Story ID:** 63-5
**Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
**Workflow:** TDD (red → green → spec-check → verify → review → spec-reconcile → finish)
**Plan Reference:** `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` Tasks 23–25
**Points:** 5 | **Priority:** p2
**Repos:** server, content
**Predecessor:** 63-4 (chrome rendering), 63-7 (markup contract alignment)

---

## Story Scope

Three discrete cleanup and validation tasks that wrap up epic 63:

1. **Task 23 — Live-pack validator CLI:** A click subcommand (`reference-chrome`) in the existing `sidequest.cli.validate` group. Walks a pack's `theme.yaml` and asserts every field the v3 reference renderer reads. Loud on missing fields (`[FAIL]` + non-zero exit). Fixture-driven tests only.

2. **Task 24 — Tropes exclusion from rendered pages:** `tropes.yaml` currently sits in `RULES_FILES` at `reference_renderer.py:337` and therefore renders on rules reference pages. Per the design bundle ("tropes section removed — keeper-side only"), it must be excluded. `seed_tropes.yaml` is already in `EXCLUDED_FILES`. Move `tropes.yaml` from `RULES_FILES` to `EXCLUDED_FILES`.

3. **Task 25 — R2 screenshot staging:** The plan specifies moving design-bundle screenshots to R2. **As of 2026-05-25, the `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/` directory does not exist** — no PNG/JPG files anywhere under the design bundle, no git history for that path. This task appears to be either already completed or the screenshots were never committed. **AC assessment: Task 25 is a no-op on this branch.** Verify during implementation; if screenshots surface, stage them per the plan.

---

## Task Surfaces

### Task 23: Live-pack validator (`reference-chrome`)

**Files:**
- Create: `sidequest-server/sidequest/cli/validate/reference_chrome.py`
- Modify: `sidequest-server/sidequest/cli/validate/__main__.py` — register subcommand
- Test: `sidequest-server/tests/cli/test_validate_reference_chrome.py` (new, fixture-driven)
- Orchestrator: `justfile` — add `content-validate` recipe

**Required chrome fields to validate:**
- `archetype` (string)
- `web_font_family` (string)
- `display_font_family` (string)
- `primary` (color, from palette)
- `accent` (color, from palette)
- `background` (color, from palette)
- `dinkus.glyph.light` (string)
- `dinkus.glyph.medium` (string)
- `dinkus.glyph.heavy` (string)

**Behavior:**
- Pass: all fields present → exit 0, `[OK]` line on stdout
- Fail: any field missing → exit 1, `[FAIL]` line on stderr with field name
- No silent fallbacks — `MissingThemeFieldError` propagates

**Integration point:** The existing `load_reference_theme()` in `reference_theme.py` (created by 63-4) already loads these fields and raises `MissingThemeFieldError`. The validator CLI wraps that loader — don't reinvent the validation logic.

### Task 24: Tropes exclusion

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py`
  - Remove `"tropes.yaml"` from `RULES_FILES` (currently at line ~337)
  - Add `"tropes.yaml"` to `EXCLUDED_FILES` (currently at line ~363)
- Test: `sidequest-server/tests/server/test_reference_renderer.py` — regression test

**Current state:**
- `tropes.yaml` is in `RULES_FILES` → it renders on rules pages (wrong)
- `seed_tropes.yaml` is already in `EXCLUDED_FILES` (correct)
- `_KIND_OVERRIDES` has `"tropes": "trope"` at line ~104 — this becomes dead code when tropes.yaml is excluded from rendering. Remove it (boy-scout, bounded).

### Task 25: R2 screenshot staging — LIKELY NO-OP

**Current state:** `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/` does not exist. No PNG files found anywhere under the design bundle directory. No git history for that path.

**If screenshots are found:** Upload to R2 at `cdn.slabgorb.com/design-bundles/2026-05-23-lore-and-rules/screenshots/`, delete local PNGs, leave pointer README.

**If screenshots are absent (current state):** Document as no-op in delivery findings. Skip the AC.

---

## Acceptance Criteria

**Task 23 (Validator):**
- AC-1: `sidequest-server/sidequest/cli/validate/reference_chrome.py` exists, implements a click command named `reference-chrome`
- AC-2: Subcommand registered in `sidequest-server/sidequest/cli/validate/__main__.py`
- AC-3: Validator asserts presence of: archetype, web_font_family, display_font_family, primary, accent, background, dinkus.glyph.{light,medium,heavy}
- AC-4: Missing field → non-zero exit + `[FAIL]` on stderr + field name in message
- AC-5: Tests at `tests/cli/test_validate_reference_chrome.py` — fixture-driven only (never reads live `genre_packs/*`)
- AC-6: `just content-validate` recipe added to orchestrator justfile (walks all live packs via the validator)

**Task 24 (Tropes Exclusion):**
- AC-7: `tropes.yaml` removed from `RULES_FILES` and added to `EXCLUDED_FILES`
- AC-8: Regression test in `test_reference_renderer.py` — fixture pack with `tropes.yaml` does NOT render trope content
- AC-9: No tropes section heading or content in rendered rules pages

**Task 25 (R2 Screenshots):**
- AC-10: If screenshots exist: uploaded to R2, local PNGs deleted, pointer README written
- AC-10-ALT: If screenshots directory is absent (current state): document as no-op, skip

---

## Constraints / Project Memory

- **No content-coupled tests** — validator tests use fixture packs with synthetic `theme.yaml`, never load live `genre_packs/*`. Live-pack validation is the CLI's job, not pytest's.
- **No silent fallbacks** — missing field = loud failure with field name in the message.
- **Images go to R2, not LFS** — if screenshots exist, they upload to R2.
- **Boy-scout bounded** — removing dead `_KIND_OVERRIDES["tropes"]` entry is acceptable since it's directly related to the tropes exclusion change.

---

## Testing Strategy

**Task 23 tests:** Use `click.testing.CliRunner` against fixture packs written to `tmp_path`:
- All-fields-present pack → exit 0
- Missing `display_font_family` → exit 1 + `[FAIL]` + field name
- Missing `dinkus.glyph.heavy` → exit 1 (nested field validation)
- Multiple missing fields → all reported

**Task 24 tests:** Add to existing `test_reference_renderer.py`:
- Fixture pack with `tropes.yaml` containing named tropes → `assemble_rules_page` output does NOT contain trope names or "tropes" section heading

**Wiring test:** Validator CLI is registered in `__main__.py` — test that `CliRunner().invoke(cli, ["reference-chrome", "--help"])` succeeds (proves registration).

---

## Existing Infrastructure to Reuse

- `sidequest/server/reference_theme.py` — `load_reference_theme()` and `MissingThemeFieldError` already exist (shipped in 63-4). The validator wraps this loader.
- `sidequest/cli/validate/__main__.py` — existing click group with `add_command()` pattern (see `audio.py`, `locations.py`, `projection_check.py`).
- `EXCLUDED_FILES` frozenset in `reference_renderer.py` — existing exclusion mechanism. Just add `tropes.yaml` to it.
- Test fixtures at `tests/fixtures/genre_packs/fixture_pack/` — Task 26 of the plan extended this with `theme.yaml` and `lore.yaml` (done in 63-7).

---

## Dependencies

- **63-4 (done 2026-05-24):** Chrome rendering, `reference_theme.py`, `load_reference_theme()`
- **63-7 (done 2026-05-24):** Markup contract alignment, wiring test, extended fixture pack
- **63-3 (done 2026-05-24):** `display_font_family` field in all live pack `theme.yaml` files

---

## Resources

- Plan: `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` (Tasks 23–25, lines 2857–3055)
- Design bundle: `docs/design-bundles/2026-05-23-lore-and-rules/`
- Sibling context: `sprint/context/context-story-63-4.md`, `sprint/context/context-story-63-7.md`
- CLAUDE.md feedback: no-content-coupled-tests, no-silent-fallbacks, images-to-r2
