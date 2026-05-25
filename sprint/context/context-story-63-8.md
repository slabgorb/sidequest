---
parent: context-epic-63.md
workflow: tdd
---

# Story 63-8: Lore page POI images — render location landscape from R2 with cartography anchor

**Story ID:** 63-8
**Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
**Workflow:** TDD (red → green → review)
**Points:** 2
**Priority:** p2
**Repos:** server, content
**Branch:** `feat/63-8-lore-page-poi-images` (both repos, off `develop`)

## Business Context

The lore reference page (`/reference/lore/<pack>/<world>`) renders location cards but no imagery, even though every world now has POI landscape PNGs in R2. This is the in-world wiki the DM (and curious players) browse; a location card with its landscape art is the difference between a reference stub and something that sells the world. The customer is the forever-DM building and showing off a world, so the lore page is product surface, not internal scaffolding. The work is pure integration: the images exist in R2, the location cards exist in the renderer — wire them together.

## Technical Guardrails

**Read this before writing tests — the story's wording does not match the code, but the intent maps cleanly. Verified against source 2026-05-25.**

1. **Injection point is `present_lore_geography`, not cartography iteration.** `sidequest-server/sidequest/server/reference_presenters.py:183` `present_lore_geography(node, ctx)` is registered for both `locations.yaml` (file-root `("locations", ())`) and `lore.geography`. It emits one `<article class="ref-card" id="location-{slug}">` per location, where `slug = slugify(item.get("id") or name)`. The story's "location-<slug> anchor section" IS this card. **`cartography.yaml` is in `EXCLUDED_FILES` (reference_renderer.py:374) and is never rendered** — do not add cartography iteration to the renderer. The image goes inside the existing location card.

2. **The image gate is the history.yaml POI-slug set.** `history.yaml points_of_interest[].slug` is the manifest of which locations have generated landscape art. Implementation: `assemble_lore_page` loads history.yaml, collects the POI slug set, and threads it into a NEW `PresenterContext` field (e.g. `poi_image_slugs: frozenset[str]`). `present_lore_geography` emits the `<img>` **iff the location's `slug` is in that set**; otherwise the card renders text-only (no `<img>`, no placeholder, no broken-image). `PresenterContext` currently carries only `pack, world, file_stem, key_path, theme, depth` (reference_presenters.py:24) — extending it is the core plumbing of this story. **This is "render text-only when absent" as a content decision, not a silent fallback** — but the emit/skip decision MUST fire an OTEL span (see #4) so it's observable.

3. **Build the URL with `resolve_asset_url`, never hardcode the CDN.** `sidequest-server/sidequest/server/asset_urls.py:47` `resolve_asset_url("genre_packs/...")` → `https://cdn.slabgorb.com/...`. `pack` and `world` are already on `PresenterContext`. Canonical asset path (project memory: world assets live at `worlds/<world>/assets/<kind>/`): `genre_packs/{pack}/worlds/{world}/assets/poi/{slug}.png`. Confirm this exact path against a real R2 object during green (the story description and a prior code sample disagree on whether `assets/` is in the path — `assets/poi/` is canonical per memory; verify before shipping the URL).

4. **OTEL on the resolution decision (project hard rule).** Add reference spans following `sidequest/telemetry/spans/reference.py` (flat-only, `sidequest.reference.*`, registered in `FLAT_ONLY_SPANS`): a `poi_image_resolved` span when the slug is in the set and an `<img>` is emitted, and a `poi_image_not_found` span when a rendered location has no matching POI image. Missing POI art is EXPECTED (not every location has a landscape) — `not_found` is INFO/DEBUG, NOT an ERROR. The point is the GM/dev panel can see the renderer actually ran the lookup rather than silently rendering nothing.

5. **Accent tint uses the already-loaded per-pack `theme.palette_accent`.** `ReferenceTheme.palette_accent` (reference_theme.py:43, from `theme.yaml`) is already on `ctx.theme`. The story says "per-world visual_style.yaml accent color," but `visual_style.yaml` is in `EXCLUDED_FILES`, is image-gen config (`extra=allow`, no canonical accent field), and loading it per-world just for a border tint is disproportionate for a 2pt story and would require a new genre-model field (which trips the `extra=forbid` model-coupling rule on sibling models). Use `ctx.theme.palette_accent` for the border/shadow tint. **This is a logged deviation (see Design Deviations); if Keith wants a genuinely per-world accent, that's a follow-up with a proper `visual_style` model field.**

6. **No content-coupled tests.** Do NOT write pytest that loads live `genre_packs/*` and asserts a POI image exists. Server tests use the `reference_v2_fixture` pack and synthetic `PresenterContext`. The "every cartography region with a matching POI slug has an R2 image" assertion is the CONTENT-side validator's job (AC-6), surfaced loudly — not a server unit test.

7. **No source-text wiring tests** (`sidequest-server/CLAUDE.md`). Don't grep the renderer source as a wiring assertion. Drive `assemble_lore_page` / `present_lore_geography` with fixtures and assert on emitted HTML + fired OTEL spans.

## Scope Boundaries

**In scope (server):**
- Extend `PresenterContext` with the POI-image-slug set (e.g. `poi_image_slugs: frozenset[str]`).
- `assemble_lore_page` loads `history.yaml`, extracts `points_of_interest[].slug`, threads the set into the context used for the geography/locations presenter.
- `present_lore_geography` emits `<img>` (content-width, below title, above `ref-card__body` description) when the location slug is in the set; text-only otherwise. Border/shadow tint from `ctx.theme.palette_accent`.
- New `sidequest.reference.poi_image_resolved` / `poi_image_not_found` OTEL spans, registered in `FLAT_ONLY_SPANS`.

**In scope (content):**
- Extend `sidequest-server/sidequest/cli/validate/locations.py` (`pf-validate-locations`, story 54-3) with a check: every cartography region (and/or history POI) whose slug should have a landscape image actually has the R2 object. Loud report on mismatch. (This validator is where the cartography↔history↔location slug-alignment the story describes actually gets enforced.)

**Out of scope:**
- Rendering `cartography.yaml` on the lore page (it's excluded by design).
- Loading `visual_style.yaml` into the renderer / adding a per-world accent model field (deferred — see deviation D2).
- Any `sidequest-ui` change (the reference page is server-rendered HTML; the UI only links in).
- Image generation or R2 upload (images already exist in R2).
- Per-image R2 existence checks at request time (the history.yaml POI set is the manifest; we don't hit R2 per render).

## AC Context

- **AC-1 — slug lookup:** `assemble_lore_page` collects `history.yaml points_of_interest[].slug` into a set and threads it to the geography presenter. Test: assemble a fixture world whose history.yaml lists slug `the-vicarage`; assert the resolved set reaches the presenter (observable via the emitted `<img>` and the `poi_image_resolved` span).
- **AC-2 — correct R2 `<img>`:** emitted `<img src>` equals `resolve_asset_url(f"genre_packs/{pack}/worlds/{world}/assets/poi/{slug}.png")`. Test asserts the exact `cdn.slabgorb.com/...` URL for a known pack/world/slug.
- **AC-3 — text-only when missing, no broken image:** a location whose slug is NOT in the POI set renders its card with zero `<img>` tags and no placeholder; the card's text (title/summary/body) is unchanged. Test: two locations, one in the set one not — assert exactly one `<img>` and it's inside the right `location-{slug}` card.
- **AC-4 — placement:** the `<img>` renders at content width, positioned **below the region/location name (`ref-card__title`) and above the description (`ref-card__body`)**. Test asserts ordering within the card HTML.
- **AC-5 — accent tint:** the `<img>` (or its wrapper) carries a border/shadow style derived from `ctx.theme.palette_accent`. Test asserts the accent value appears in the emitted style for the image element. (Deviation D2: per-pack theme accent, not per-world visual_style.)
- **AC-6 — validator:** `pf-validate-locations` gains a check that flags any location/region whose slug should map to a POI landscape image but has no R2 object. Test the validator against a fixture pack (not live packs): a fixture with a POI slug but missing image triggers a loud finding; a complete fixture passes.
- **AC-7 — OTEL + tests green:** `poi_image_resolved` fires on emit, `poi_image_not_found` fires on a rendered location lacking art; both registered in `FLAT_ONLY_SPANS`. Server suite + content validator green. No silent path: the skip is spanned, not silent.

**Test strategy summary for RED:**
1. **Unit (primary):** `present_lore_geography(node, ctx)` with a crafted node (≥2 locations) and an extended `PresenterContext` carrying `poi_image_slugs` + a theme with a known `palette_accent`. Assert: img present for in-set slug, absent for out-of-set; exact URL; placement order; accent in style; both OTEL spans fired. These FAIL initially (PresenterContext has no `poi_image_slugs`; presenter emits no img).
2. **Wiring/integration:** add an isolated fixture world (new dir under `reference_v2_fixture/worlds/`) with `locations.yaml` + `history.yaml`, call `assemble_lore_page`, assert `<img>` lands inside the matching `location-{slug}` card and not the unmatched one. Proves history.yaml → poi_image_slugs threading. Use a NEW world dir to avoid disturbing existing `long_fixture` lore-page tests.
3. **Content validator:** fixture-driven test of the new `pf-validate-locations` check (loud on missing image, clean on complete).

## Design Deviations

### TEA (test design)
- **D1 — cartography.yaml reinterpreted as locations.yaml + history.yaml**
  - Spec source: story 63-8 description, "Server (reference_renderer.py): For each region in cartography.yaml, look up the matching POI slug from history.yaml ... inside the location-<slug> anchor section."
  - Spec text: iterate cartography.yaml regions and emit `<img>` in the `location-<slug>` section.
  - Implementation: the renderer never renders cartography.yaml (it's in `EXCLUDED_FILES`); the `location-<slug>` cards are emitted by `present_lore_geography` from `locations.yaml`/`lore.geography`. Images are gated by the `history.yaml points_of_interest[].slug` set threaded through `PresenterContext`. The cartography↔history↔location slug alignment is enforced by the content validator (AC-6), not by renderer-side cartography iteration.
  - Rationale: matches the actual render pipeline; avoids un-excluding cartography.yaml (a spoiler/asset-config file) and duplicating location rendering. One mechanism per problem.
  - Severity: minor (wording vs. architecture; intent preserved).
  - Forward impact: AC-1/AC-4 tests assert against `location-{slug}` cards from locations.yaml, not cartography sections.
- **D2 — accent from per-pack theme.palette_accent, not per-world visual_style.yaml**
  - Spec source: story 63-8 description, "Respect the per-world visual_style.yaml palette (border/shadow tint from the world's accent color)."
  - Spec text: source the border/shadow tint from the world's `visual_style.yaml` accent color.
  - Implementation: use `ReferenceTheme.palette_accent` (per-pack, from `theme.yaml`, already on `ctx.theme`).
  - Rationale: `visual_style.yaml` is in `EXCLUDED_FILES`, is image-gen config with no canonical accent field (`extra=allow`), and wiring per-world accent for a border tint is disproportionate for 2pts and would need a new genre-model field (sibling models are `extra=forbid`). The renderer already has a loaded accent.
  - Severity: minor.
  - Forward impact: AC-5 tests assert the per-pack theme accent. If a genuinely per-world accent is wanted, follow-up story adds a typed `visual_style` accent field + loader.
