# Epic 63: Reference pages v3 — chrome + wiki-like anchor links

**Jira Key:** None (personal project — no Jira)
**Priority:** p2
**Repos:** server, ui, content
**Status:** in_progress
**Stories:** 8 (63-3/4/5/7 done; 63-1/2 canceled; 63-6/8 backlog)

## Overview

The server-rendered `/reference/rules/<pack>` and `/reference/lore/<pack>/<world>` pages are SideQuest's in-world wiki. Epic 63 takes them from bare browser-default markup to the design bundle's full chrome (per-pack palettes and fonts, hero, locked contents rail) and wires the game-client panels (CharacterSheet, KnowledgeJournal, LocationPanel, ConnectScreen) to deep-link *into* those pages via server-emitted `reference_url` fields. Scope discipline for the whole epic: **just styling + wiki-like behavior** — no tweak/treatment/density panels (those are design-tool affordances, not product features).

## Background

These pages are rendered at request time by `sidequest-server/sidequest/server/reference_renderer.py`, which walks a world's YAML files and turns them into HTML. They are NOT a static site or an SPA — there is no separate front-end build for them; the React `sidequest-ui` only *links to* them. This is the load-bearing fact for every story in the epic: design "bundles" under `docs/design-bundles/` are the visual spec the renderer must reproduce in Python, never a new deployable target.

The epic's history is itself instructive. Story 63-4 shipped the bundled CSS and *some* chrome markup, but the class-name vocabulary it emitted (`.contents-rail`) did not match what the bundle's CSS targets (`.toc-sticky`/`.toc`), so production rendered with default browser styles while tests passed. 63-7 corrected that drift and added the missing markup-vs-CSS wiring test. The recurring lesson: **a reference-page test must assert behavior against the served artifact (the CSS bundle, the rendered HTML), not the existence of a class name or a source string.** `sidequest-server/CLAUDE.md` codifies this as "No Source-Text Wiring Tests."

Story 63-8 (the open implementation story) adds POI landscape imagery to the lore page's location cards, sourcing the images from R2.

## Technical Architecture

**Rendering pipeline (server-only for most stories):**

- `reference_routes.py` — FastAPI routes for `/reference/...`.
- `reference_renderer.py` — `assemble_lore_page(pack, world, pack_dir, world_dir)` and `assemble_rules_page(pack, pack_dir)` walk a fixed file allowlist (`LORE_WORLD_FILES`, `LORE_PACK_FLAVOR_FILES`) and dispatch each file/section through the presenter registry, falling back to a generic `<h2>key</h2>` walk. `EXCLUDED_FILES` (incl. `cartography.yaml`, `visual_style.yaml`, `theme.yaml`, spoiler files) are never rendered.
- `reference_presenters.py` — per-section pure functions `(node, PresenterContext) -> str`. `PresenterContext` carries `pack`, `world`, `file_stem`, `key_path`, `theme: ReferenceTheme`, `depth`. The registry `PRESENTERS[(file_stem, key_path)]` maps a file/section to its presenter. `present_lore_geography` (registered for `locations.yaml` and `lore.geography`) renders location cards as `<article class="ref-card" id="location-{slug}">`.
- `reference_theme.py` — per-pack palette/font/dinkus constants and the `PACK_*` tables (ported from the bundle's `app.jsx`).
- `reference_anchors.py` / `reference_slug.py` — slug helpers + the JSON anchor island used for deep-link validation.
- `reference_visibility.py` — player-facing vs keeper-only field classification.
- `asset_urls.py` — `resolve_asset_url(relative_path)` builds `https://cdn.slabgorb.com/<path>` (the R2 CDN). Reuse this for any asset URL; do not hardcode the base.
- `sidequest/telemetry/spans/reference.py` — `SPAN_REFERENCE_*` flat-only OTEL spans (`url_attached`, `theme_missing`, `hero_unbound`, `toc_missing`, …). New reference-subsystem decisions register here following the `FLAT_ONLY_SPANS` pattern.

**Key files table:**

| File | Role |
|------|------|
| `sidequest-server/sidequest/server/reference_renderer.py` | Page assembly, file walk, presenter dispatch |
| `sidequest-server/sidequest/server/reference_presenters.py` | Per-section HTML emitters incl. `present_lore_geography` |
| `sidequest-server/sidequest/server/reference_theme.py` | Per-pack palette/font/`PACK_*` constants |
| `sidequest-server/sidequest/server/asset_urls.py` | `resolve_asset_url` → cdn.slabgorb.com |
| `sidequest-server/sidequest/telemetry/spans/reference.py` | Reference OTEL spans |
| `sidequest-server/tests/fixtures/packs/reference_v2_fixture/` | Test fixture pack (world `long_fixture`) |
| `sidequest-server/sidequest/cli/validate/locations.py` | `pf-validate-locations` content validator (54-3) |

**Test discipline (epic-wide):** Tests run against the `reference_v2_fixture` pack and the committed CSS bundle — never live `genre_packs/*`. Live-pack coverage is the content-side validator's job, surfaced loudly, not a server unit test (project rule: no content-coupled tests).

## Planning Documents

| Document | Path | Relevant sections |
|----------|------|-------------------|
| Reference pages v3 plan | `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` | 27 tasks (17 anchor + 10 chrome); Tasks 20–22 chrome markup |
| Design bundle | `docs/design-bundles/2026-05-23-lore-and-rules/project/` | `app.jsx`, `theme.css`, `styles.css` — visual source of truth |

## Cross-Epic Dependencies

- **Depends on:** Story 54-3 (`pf-validate-locations` content validator) — 63-8 extends it with a POI-image check.
- **Depends on:** Story 63-4/63-7 chrome (the `ref-card`/location-card markup 63-8 injects images into).
- **Depended on by:** none currently open.
