# Reference Pages v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

---

## v3 amendment — chrome absorption from 2026-05-23 design bundle

**What changed (2026-05-24).** The v2 plan (17 tasks, hyperlinks + lobby + bad-anchor banner) had not yet started when a fresh design bundle landed at `docs/design-bundles/2026-05-23-lore-and-rules/` from the Claude Design tool. The bundle is a full visual redesign of `/reference/{rules,lore}/...`: per-pack chrome (palette + display font + dinkus glyphs), a contents rail, a hero with the world name, a new lore section sourced from `lore.yaml`, and removal of the keeper-only tropes section. v3 absorbs that scope without disturbing v2.

**Scope discipline.** The chrome amendment is *styling + wiki-like behavior only* — per-pack palette/typography from `theme.yaml`, world-name hero, lore section from `lore.yaml`, locked contents rail, anchored sections (already in v2), bad-anchor banner (already in v2). Anything beyond that — tweak panels, treatment switchers, density sliders, in-page settings UI — is **out of scope**. Bundle assets that exist only to let the *designer* compare variants are not features.

**Task count: 27 total** (17 v2 + 10 new chrome).

**Mechanism.** The pages stay **server-rendered Python** in `sidequest-server/sidequest/server/reference_renderer.py`. The bundle's `Lore and Rules*.html` + `*.jsx` files are a **visual contract, not runtime code** — Babel-standalone prototypes used by the design tool. The renderer's job is to emit byte-equivalent HTML. The bundle's `theme.css` + `styles.css` ship as-is via a static route. No React, no Babel, no build step on the page itself. The renderer emits the same DOM shape the bundle's JSX produces.

**Scope preservation.** Tasks 1–17 (v2) are correct and unstarted. They land first, in order, unchanged. The new chrome work is appended as Tasks 18–27. The v2 plan's anchor / URL / protocol / banner contracts are unchanged: the chrome wraps around them. AC10 (`just check-all` passes) is now subsumed by Task 27's gate, and the original Task 17 is skipped in favour of Task 27.

**Architecture decisions in this amendment (each documented + justified in the named tasks below):**

| Decision | Resolution | Task |
|---|---|---|
| `display_font_family` | **Add it to `theme.yaml`.** Content-controlled, same surface as `web_font_family`. No silent fallback — pack without it = LOUD error span. Per-pack mapping in `theme.css` from the design bundle becomes the seed data the content team commits into each `theme.yaml`. | 19 |
| CSS shipping | **Static asset route.** Existing `_STYLESHEET_HREF = "/reference/static/reference.css"` extends to also serve the bundled `theme.css` and `styles.css`. Renderer emits stable stylesheet `<link>` tags. No inlining — caching matters across page loads. | 20 |
| Screenshots in repo | **Move out of `docs/`.** 1.3 MB of PNGs in a docs tree violates the "images go to R2, not LFS" rule even though we're not committing through LFS. Solve: the bundle is on disk but not yet git-tracked. Task 25 stages screenshots to R2 at `cdn.slabgorb.com/design-bundles/2026-05-23-lore-and-rules/screenshots/` and replaces the local `screenshots/` dir with a README pointer. HTML / CSS / JSX / chat transcripts stay in the docs tree — those are the actual design intent. | 25 |
| Fixture pack extension | **Extend the existing Task 15 fixture pack** with a `theme.yaml` + `lore.yaml` + richer world layout (world name, history, cosmology, factions) so chrome tests reuse it. No second fixture pack — splitting would fracture test surface. Task 15's fixture authoring is amended in place via Task 26. | 26 |
| Live-pack assertions | **Validator only.** A new `python -m sidequest.cli.validate reference-chrome <pack>` subcommand walks every live pack's `theme.yaml` for the required chrome fields and reports gaps loudly. Lives inside the existing click group at `sidequest-server/sidequest/cli/validate/__main__.py` next to `locations` / `audio` / `projection-check`. No pytest reads `genre_packs/*`. | 23 |
| Tropes removal | **Author the kind-allowlist in `RENDERED_FILES` (or equivalent) explicitly.** v1 already excludes `npcs.yaml`; v3 adds `tropes.yaml` and `seed_tropes.yaml` to the exclusion. Loud — not silent. | 24 |
| One mechanism per problem | The renderer is the single emitter of chrome. We do NOT add a parallel client-side enricher or post-render JS injection. The bad-anchor banner inline script (v2 Task 4) is one inline script; the contents-rail uses native CSS sticky + a tiny `IntersectionObserver` snippet from the bundle (~15 LOC), kept inline so the page stays self-contained. | 18, 21 |

**Conflicts with the existing 17 tasks (and resolutions):**

- **Task 4's `_wrap_document`** emits a single `<link rel="stylesheet">`. v3 Task 20 extends it to (a) emit two stylesheet links (`theme.css`, `styles.css`), (b) accept and emit `<html>` `data-pack` / `data-world` / `data-archetype` attributes, (c) preserve the v2 JSON island + bad-anchor banner unchanged. Task 4 lands first; Task 20 amends.
- **Task 15's fixture pack** (`classes.yaml`, `cultures.yaml`, `worlds/fixture_world/{world,legends,locations}.yaml`) is fine for v2 anchor tests but lacks `theme.yaml` + `lore.yaml`. Task 26 amends the same fixture in place, adding the new files. Task 15's assertions stay valid (they don't read the new files).
- **Task 2's namespacing** of list-of-dict ids (`class-knight`) now also has to coexist with the new lore section's emitted ids (`#reckoning`, faction cards). v3 keeps the namespacing rule and adds `cult-<slug>`, `stratum-<slug>` to the kind table in Task 22.
- **Task 17's manual smoke** is replaced by Task 27, which also walks the new chrome (TOC sticks, hero shows world name, palette swap on `data-pack` change, validator surfaces a missing `display_font_family`).
- **No conflicts elsewhere.** Tasks 1, 3, 5–14, 16 are independent of chrome.

**Reading order for the implementer:**

1. Read this amendment header in full.
2. Execute Tasks 1–16 as written (v2).
3. **Skip the original Task 17** — Task 27 replaces it.
4. Execute Tasks 18–27 in order.

---

**Goal:** Wire structured-panel hyperlinks (CharacterSheet abilities + class, KnowledgeJournal entries, LocationPanel locations) and a lobby reference surface into the v1 reference pages, with a bad-anchor banner for loud failure. **v3 adds:** per-pack chrome (palette + fonts + dinkus + contents rail + hero + lore section) sourced from `theme.yaml` and `lore.yaml`, server-rendered, matching the design bundle at `docs/design-bundles/2026-05-23-lore-and-rules/` byte-equivalently.

**Architecture:** Server emits a `reference_url` on protocol objects at construction time, computed by a new `reference_anchors` module that shares a `slugify` helper with the page renderer. The v1 renderer is updated to emit kind-namespaced ids (`class-burglar`, `culture-thornberry`) so cross-file name collisions can't dead-link. UI panels render an entity name as `<a target="_blank">` iff its `reference_url` is non-null; a JSON island + ~10-line inline script on each reference page toggles a hidden "anchor not found" banner when `location.hash` isn't in the page's slug set.

**Tech Stack:** Python 3.12 / FastAPI / pydantic v2 (server), React 18 / TypeScript (UI), pytest + ruff + pyright (server), vitest (UI), OTEL spans for observability.

**Design spec:** `docs/superpowers/specs/2026-05-23-reference-pages-v2-design.md` — read before starting.

---

## Repo / branch hygiene

This plan touches three subrepos. Per project conventions:

- **Orchestrator** (`oq-1/`) — base branch `main`. No code changes here beyond this plan + spec docs (already on `main`).
- **`sidequest-server/`** — base branch `develop`. Create `feat/reference-v2` before any commit.
- **`sidequest-ui/`** — base branch `develop`. Create `feat/reference-v2` before any commit.
- **`sidequest-content/`** — base branch `develop`. Create `feat/reference-v2` for the one-line CLAUDE.md note.

Confirm subrepo branches exist before dispatching implementers (per memory: subrepo branches default to develop, not the orchestrator's branch).

```bash
cd sidequest-server  && git checkout develop && git pull && git checkout -b feat/reference-v2
cd ../sidequest-ui   && git checkout develop && git pull && git checkout -b feat/reference-v2
cd ../sidequest-content && git checkout develop && git pull && git checkout -b feat/reference-v2
```

---

## File Structure

### sidequest-server (new + modified)

| Path | Responsibility |
|---|---|
| `sidequest-server/sidequest/server/reference_slug.py` (new) | `slugify()` — single source of truth. |
| `sidequest-server/sidequest/server/reference_anchors.py` (new) | `build_rules_url()`, `build_lore_url()`, `reference_url_for_ability()`, `reference_url_for_class()`, `reference_url_for_journal_entry()`, `reference_url_for_location_entity()`. |
| `sidequest-server/sidequest/server/reference_renderer.py` (modify) | Import shared slug. Namespaced ids on list-of-dict items. Emit JSON island + bad-anchor banner. |
| `sidequest-server/sidequest/protocol/models.py` (modify) | Add `reference_url: str \| None = None` to `AbilityDefinition`. Add `class_reference_url: str \| None = None` to `PartyMember`. Add `reference_url: str \| None = None` to `JournalEntry`. Add `reference_url: str \| None = None` to `LocationEntity`. |
| `sidequest-server/sidequest/telemetry/spans.py` (modify) | Three new span helpers: `reference_url_attached`, `reference_url_failed`, `reference_url_skipped`. |
| `sidequest-server/tests/server/test_reference_slug.py` (new) | Unit tests for the slug helper. |
| `sidequest-server/tests/server/test_reference_anchors.py` (new) | Unit tests for URL builders + attach helpers + KnowledgeEntry category dispatch. |
| `sidequest-server/tests/server/test_reference_renderer_namespacing.py` (new) | Renderer namespaced-id behaviour. |
| `sidequest-server/tests/server/test_reference_renderer_bad_anchor.py` (new) | JSON island + banner element. |
| `sidequest-server/tests/server/test_reference_url_attach.py` (new) | Protocol-construction round-trip — fixture-driven, no live pack. |
| `sidequest-server/tests/fixtures/genre_packs/fixture_pack/...` (new) | Tiny fixture pack with one class (`Knight`), one culture also named `Knight` (collision case), one legend, one location. |

### sidequest-ui (modified)

| Path | Responsibility |
|---|---|
| `sidequest-ui/src/components/ReferenceLinks.tsx` (modify) | Add `disabled` prop; render `aria-disabled` span when disabled. |
| `sidequest-ui/src/screens/ConnectScreen.tsx` (modify) | Render `<ReferenceLinks>` next to the pack/world pickers. |
| `sidequest-ui/src/components/CharacterSheet.tsx` (modify) | Wrap ability name + class + race in anchor when `reference_url` present. |
| `sidequest-ui/src/components/KnowledgeJournal.tsx` (modify) | Wrap entry title in anchor when `reference_url` present. |
| `sidequest-ui/src/components/LocationPanel.tsx` (modify) | Wrap location/entity name in anchor when `reference_url` present. |
| `sidequest-ui/src/providers/GameStateProvider.tsx` (modify) | Extend `KnowledgeEntry` + ability + location TS types with optional `reference_url`. |
| `sidequest-ui/src/types/payloads.ts` (modify) | Mirror server schema additions. |
| `sidequest-ui/src/components/__tests__/CharacterSheet.reference.test.tsx` (new) | Anchor rendering + no-WS-send wiring. |
| `sidequest-ui/src/components/__tests__/KnowledgeJournal.reference.test.tsx` (new) | Same. |
| `sidequest-ui/src/components/__tests__/LocationPanel.reference.test.tsx` (new) | Same. |
| `sidequest-ui/src/components/__tests__/ReferenceLinks.disabled.test.tsx` (new) | Disabled-state coverage. |
| `sidequest-ui/src/screens/__tests__/ConnectScreen.reference.test.tsx` (new) | Lobby surface wiring + no-WS-send. |

### sidequest-content (modified)

| Path | Responsibility |
|---|---|
| `sidequest-content/CLAUDE.md` (modify) | Single-paragraph note: renaming a class/archetype/culture/legend/location without updating consumers breaks inbound reference-page links. |

---

## Task 1: Extract slug helper into its own module

**Files:**
- Create: `sidequest-server/sidequest/server/reference_slug.py`
- Modify: `sidequest-server/sidequest/server/reference_renderer.py:1-25`
- Test: `sidequest-server/tests/server/test_reference_slug.py`

This is a pure refactor with no behaviour change. Cement the shared contract before any new caller depends on it.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_reference_slug.py`:

```python
"""Unit tests for the shared slugify helper.

The helper is imported by both the page renderer and the URL builder so the
two surfaces cannot drift.
"""
from __future__ import annotations

import pytest

from sidequest.server.reference_slug import slugify


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Burglar", "burglar"),
        ("Cosh & Run", "cosh-run"),
        ("   Aunt Pemberton   ", "aunt-pemberton"),
        ("Lady Of The Hall", "lady-of-the-hall"),
        ("history.yaml", "history-yaml"),
        ("naïve", "na-ve"),
        ("", ""),
    ],
)
def test_slugify_cases(raw: str, expected: str) -> None:
    assert slugify(raw) == expected


def test_slugify_collapses_runs() -> None:
    assert slugify("a   b---c__d") == "a-b-c-d"


def test_slugify_strips_edges() -> None:
    assert slugify("-leading and trailing-") == "leading-and-trailing"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_slug.py -v
```

Expected: `ImportError: cannot import name 'slugify' from 'sidequest.server.reference_slug'` (module does not exist).

- [ ] **Step 3: Create the slug helper module**

Create `sidequest-server/sidequest/server/reference_slug.py`:

```python
"""Single source of truth for slug generation across the reference surface.

Both the HTML renderer (`reference_renderer`) and the URL builder
(`reference_anchors`) import from here so the two surfaces cannot drift.

Algorithm: lowercase, replace any run of non-`[a-z0-9]` chars with a single
hyphen, strip leading/trailing hyphens. ASCII-only; non-ASCII chars become
hyphen separators. Empty input returns empty string.
"""
from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase ASCII slug. Non-ASCII chars become separators; runs collapse."""
    return _SLUG_RE.sub("-", text.lower()).strip("-")
```

- [ ] **Step 4: Update the renderer to import from the new module**

In `sidequest-server/sidequest/server/reference_renderer.py`, replace the inline
slug definition (lines 17-25) with an import:

```python
from sidequest.server.reference_slug import slugify
```

Delete the local `_SLUG_RE = ...` and `def slugify(...)` block. Leave every
call site that uses `slugify(...)` untouched — they now resolve to the
imported symbol.

- [ ] **Step 5: Run tests to verify**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_slug.py tests/server/test_reference_renderer.py -v
```

Expected: PASS — slug tests pass, existing renderer tests still pass (no
behaviour change).

- [ ] **Step 6: Lint + type-check**

```bash
cd sidequest-server && uv run ruff check sidequest/server/reference_slug.py sidequest/server/reference_renderer.py && uv run ruff format sidequest/server/reference_slug.py && uv run pyright sidequest/server/reference_slug.py sidequest/server/reference_renderer.py
```

Expected: clean.

- [ ] **Step 7: Commit**

```bash
cd sidequest-server
git add sidequest/server/reference_slug.py sidequest/server/reference_renderer.py tests/server/test_reference_slug.py
git commit -m "refactor(reference): extract slugify into shared module

Single source of truth so the v2 URL builder cannot drift from the
renderer's anchor ids."
```

---

## Task 2: Namespace renderer anchor ids by file kind

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py:60-130`
- Test: `sidequest-server/tests/server/test_reference_renderer_namespacing.py` (new)

V1 emits flat slugs for list-of-dict items, so a class "Knight" and a culture
"Knight" both want `id="knight"`. v2 namespaces them by file stem so they
become `class-knight` and `culture-knight`. Implementation: thread the
containing-file's "kind" through `_render_file` → `_render_list` →
`_heading_for_item`. The kind is the singularised stem (`classes` → `class`,
`archetypes` → `archetype`, `cultures` → `culture`, `legends` → `legend`,
`locations` → `location`). Files with no singularisation (`history`,
`lore`, `world`, `calendar`, `demographics`, `openings`, `equipment_tables`,
`inventory`, `beat_vocabulary`, `power_tiers`, `progression`, `rules`,
`magic`, `achievements`, `tropes`, `pack`) use the stem as-is — for those
files we still want `<stem>-<slug>` (e.g. `history-the-rending`).

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_reference_renderer_namespacing.py`:

```python
"""Anchor ids on list-of-dict items must be namespaced by their containing
file's kind so cross-file name collisions produce distinct anchors.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sidequest.server.reference_renderer import (
    _render_file,
    _kind_for_stem,
)


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("classes", "class"),
        ("archetypes", "archetype"),
        ("cultures", "culture"),
        ("legends", "legend"),
        ("locations", "location"),
        ("history", "history"),
        ("lore", "lore"),
        ("world", "world"),
        ("achievements", "achievement"),
        ("tropes", "trope"),
    ],
)
def test_kind_for_stem(stem: str, expected: str) -> None:
    assert _kind_for_stem(stem) == expected


def test_namespaced_id_for_class_item(tmp_path: Path) -> None:
    path = tmp_path / "classes.yaml"
    path.write_text(yaml.safe_dump({"classes": [{"name": "Knight"}]}))
    rendered = _render_file(path)
    assert 'id="class-knight"' in rendered


def test_namespaced_id_for_culture_item(tmp_path: Path) -> None:
    path = tmp_path / "cultures.yaml"
    path.write_text(yaml.safe_dump({"cultures": [{"name": "Knight"}]}))
    rendered = _render_file(path)
    assert 'id="culture-knight"' in rendered


def test_class_and_culture_with_same_name_do_not_collide(tmp_path: Path) -> None:
    classes = tmp_path / "classes.yaml"
    cultures = tmp_path / "cultures.yaml"
    classes.write_text(yaml.safe_dump({"classes": [{"name": "Knight"}]}))
    cultures.write_text(yaml.safe_dump({"cultures": [{"name": "Knight"}]}))
    rendered_classes = _render_file(classes)
    rendered_cultures = _render_file(cultures)
    assert 'id="class-knight"' in rendered_classes
    assert 'id="culture-knight"' in rendered_cultures


def test_top_level_dict_keys_keep_flat_slug(tmp_path: Path) -> None:
    """Top-level keys are unique within the file so they don't need namespacing."""
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump({"core_rules": {"description": "x"}}))
    rendered = _render_file(path)
    # Top-level dict keys still emit flat slugs.
    assert 'id="core-rules"' in rendered


def test_file_wrapper_keeps_existing_id(tmp_path: Path) -> None:
    path = tmp_path / "classes.yaml"
    path.write_text(yaml.safe_dump({"classes": [{"name": "Knight"}]}))
    rendered = _render_file(path)
    assert 'id="file-classes"' in rendered
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer_namespacing.py -v
```

Expected: FAIL with `ImportError: cannot import name '_kind_for_stem'` and
`id="knight"` mismatches.

- [ ] **Step 3: Implement `_kind_for_stem` and thread it through the walker**

In `sidequest-server/sidequest/server/reference_renderer.py`, add this helper
above `_render_file`:

```python
# Singularised stems for files whose entries are individually named items.
# Entries inside these files become `<kind>-<slug>` anchors so cross-file
# name collisions cannot produce duplicate ids.
_KIND_OVERRIDES: dict[str, str] = {
    "classes": "class",
    "archetypes": "archetype",
    "cultures": "culture",
    "legends": "legend",
    "locations": "location",
    "achievements": "achievement",
    "tropes": "trope",
}


def _kind_for_stem(stem: str) -> str:
    """Return the namespaced anchor kind for a given file stem.

    Default behaviour is to use the stem as-is (e.g. `history` → `history`),
    so non-plural files still benefit from file-level namespacing while
    pluralised files get a cleaner singular form.
    """
    return _KIND_OVERRIDES.get(stem, stem)
```

Modify `_render_list` to accept a `kind: str | None = None` parameter and
pass it into `_heading_for_item`. Modify `_heading_for_item` to accept the
kind and prefix the slug with `f"{kind}-"` when kind is non-None and the
item is in a list (not a top-level dict). Modify `_render_dict` to pass
`kind=None` (top-level dict keys stay flat). Modify `render_node` to accept
an optional `kind` parameter that propagates to `_render_list` only.

In `_render_file`, derive `kind = _kind_for_stem(path.stem)` and pass it
into `render_node(data, kind=kind)`. The `<section id="file-{stem}">`
wrapper keeps its existing id.

Reference call-site change (apply consistently throughout):

```python
def _heading_for_item(item: dict, index: int, kind: str | None = None) -> tuple[str, str]:
    # ... existing name-resolution logic up through computing `slug` and
    # `value` (the display string) ...
    if kind:
        slug = f"{kind}-{slug}"
        fallback_slug = f"{kind}-{fallback_slug}"
    # ... existing return logic ...
```

```python
def _render_list(items: list, depth: int, kind: str | None = None) -> str:
    # ... existing list-of-scalars branch ...
    for index, item in enumerate(items):
        if isinstance(item, dict):
            slug, display = _heading_for_item(item, index, kind=kind)
            # ... existing emit logic ...
```

```python
def render_node(node: object, depth: int = 0, kind: str | None = None) -> str:
    # ... existing depth-cap branch ...
    if isinstance(node, dict):
        return _render_dict(node, depth) if node else "<p><em>(empty)</em></p>"
    if isinstance(node, list):
        return _render_list(node, depth, kind=kind) if node else "<p><em>(empty)</em></p>"
    return _render_scalar(node)
```

```python
def _render_file(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        with path.open() as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name}: malformed YAML: {exc}") from exc
    kind = _kind_for_stem(path.stem)
    body = "<p><em>(empty file)</em></p>" if data is None else render_node(data, kind=kind)
    file_slug = slugify(path.stem)
    return (
        f'<section class="file" id="file-{file_slug}">'
        f"<h1>{escape(path.name)}</h1>"
        f"{body}"
        "</section>"
    )
```

- [ ] **Step 4: Run namespacing tests**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer_namespacing.py -v
```

Expected: PASS.

- [ ] **Step 5: Run existing renderer tests to confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py tests/server/test_reference_routes.py -v
```

If pre-existing tests asserted flat ids like `id="burglar"`, update them to
the new `id="class-burglar"` shape. Document each updated assertion in the
commit body so reviewers can verify the migration was intentional.

- [ ] **Step 6: Lint + type-check**

```bash
cd sidequest-server && uv run ruff check sidequest/server/reference_renderer.py && uv run ruff format sidequest/server/reference_renderer.py && uv run pyright sidequest/server/reference_renderer.py
```

- [ ] **Step 7: Commit**

```bash
cd sidequest-server
git add sidequest/server/reference_renderer.py tests/server/test_reference_renderer_namespacing.py tests/server/test_reference_renderer.py tests/server/test_reference_routes.py
git commit -m "feat(reference): namespace list-of-dict anchor ids by file kind

Same-named entities in different files (e.g. a 'Knight' class and a
'Knight' culture) now produce distinct anchors (class-knight vs
culture-knight), required for v2 server-emitted URLs."
```

---

## Task 3: Build the URL builder module

**Files:**
- Create: `sidequest-server/sidequest/server/reference_anchors.py`
- Test: `sidequest-server/tests/server/test_reference_anchors.py`

Pure URL construction — no protocol attachment yet. Two builder functions
plus four kind-specific helpers that compose them.

- [ ] **Step 1: Write the failing tests**

Create `sidequest-server/tests/server/test_reference_anchors.py`:

```python
"""URL builders for reference-page anchors.

The builders are pure: in -> URL string. They use the shared slugify so the
emitted URLs match the renderer's anchor ids exactly. Unknown pack/world is
not the builders' concern — they're called only after the caller knows the
session's pack/world are loaded.
"""
from __future__ import annotations

import pytest

from sidequest.server.reference_anchors import (
    build_lore_url,
    build_rules_url,
    reference_url_for_ability,
    reference_url_for_class,
    reference_url_for_journal_entry,
    reference_url_for_location_entity,
)


def test_build_rules_url_class() -> None:
    assert build_rules_url("tea_and_murder", "class", "Burglar") == (
        "/reference/rules/tea_and_murder#class-burglar"
    )


def test_build_rules_url_class_signature() -> None:
    assert build_rules_url("tea_and_murder", "class", "Burglar", "signature", "Cosh & Run") == (
        "/reference/rules/tea_and_murder#class-burglar-signature-cosh-run"
    )


def test_build_lore_url_culture() -> None:
    assert build_lore_url("tea_and_murder", "glenross", "culture", "Thornberry") == (
        "/reference/lore/tea_and_murder/glenross#culture-thornberry"
    )


def test_build_lore_url_legend() -> None:
    assert build_lore_url("tea_and_murder", "glenross", "legend", "The Rending") == (
        "/reference/lore/tea_and_murder/glenross#legend-the-rending"
    )


def test_reference_url_for_class_ability_returns_url() -> None:
    # Caller passes the YAML-resolved binding: the class owns this ability.
    url = reference_url_for_ability(
        pack="tea_and_murder",
        source="Class",
        ability_name="Cosh",
        owning_class_name="Burglar",
    )
    assert url == "/reference/rules/tea_and_murder#class-burglar-signature-cosh"


def test_reference_url_for_non_class_ability_returns_none() -> None:
    # Race/Item/Play sources do not link to a class signature.
    assert reference_url_for_ability(
        pack="tea_and_murder",
        source="Race",
        ability_name="Keen Senses",
        owning_class_name=None,
    ) is None


def test_reference_url_for_class_ability_without_owner_returns_none() -> None:
    """If we don't know which class owns the ability, we cannot link."""
    assert reference_url_for_ability(
        pack="tea_and_murder",
        source="Class",
        ability_name="Cosh",
        owning_class_name=None,
    ) is None


def test_reference_url_for_class() -> None:
    assert reference_url_for_class(pack="tea_and_murder", class_name="Burglar") == (
        "/reference/rules/tea_and_murder#class-burglar"
    )


def test_reference_url_for_journal_entry_lore_dispatches_legend() -> None:
    """Lore category falls back to history once legends miss; here it hits legend."""
    url = reference_url_for_journal_entry(
        pack="tea_and_murder",
        world="glenross",
        category="Lore",
        content="The Rending",
        legend_names=("The Rending", "The Hollow Pact"),
        history_entries=(),
    )
    assert url == "/reference/lore/tea_and_murder/glenross#legend-the-rending"


def test_reference_url_for_journal_entry_lore_falls_back_to_history() -> None:
    url = reference_url_for_journal_entry(
        pack="tea_and_murder",
        world="glenross",
        category="Lore",
        content="Founding of Glenross",
        legend_names=(),
        history_entries=("Founding of Glenross",),
    )
    assert url == "/reference/lore/tea_and_murder/glenross#history-founding-of-glenross"


def test_reference_url_for_journal_entry_place() -> None:
    url = reference_url_for_journal_entry(
        pack="tea_and_murder",
        world="glenross",
        category="Place",
        content="The Vicarage",
        legend_names=(),
        history_entries=(),
        location_names=("The Vicarage",),
    )
    assert url == "/reference/lore/tea_and_murder/glenross#location-the-vicarage"


@pytest.mark.parametrize("category", ["Person", "Quest"])
def test_reference_url_for_journal_entry_person_quest_returns_none(category: str) -> None:
    """Person -> npcs.yaml is excluded; Quest has no rendered yaml. Plain text."""
    assert reference_url_for_journal_entry(
        pack="tea_and_murder",
        world="glenross",
        category=category,
        content="Aunt Pemberton",
        legend_names=(),
        history_entries=(),
    ) is None


def test_reference_url_for_journal_entry_unknown_entity_returns_none() -> None:
    assert reference_url_for_journal_entry(
        pack="tea_and_murder",
        world="glenross",
        category="Place",
        content="Nowhere",
        legend_names=(),
        history_entries=(),
        location_names=(),
    ) is None


def test_reference_url_for_location_entity_hits() -> None:
    url = reference_url_for_location_entity(
        pack="tea_and_murder",
        world="glenross",
        entity_name="The Vicarage",
        known_location_names=("The Vicarage",),
    )
    assert url == "/reference/lore/tea_and_murder/glenross#location-the-vicarage"


def test_reference_url_for_location_entity_miss_returns_none() -> None:
    assert reference_url_for_location_entity(
        pack="tea_and_murder",
        world="glenross",
        entity_name="A Bush",
        known_location_names=("The Vicarage",),
    ) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_anchors.py -v
```

Expected: FAIL with `ImportError` for the new module.

- [ ] **Step 3: Implement the URL builder module**

Create `sidequest-server/sidequest/server/reference_anchors.py`:

```python
"""Pure URL builders + kind-specific helpers for the reference surface.

The builders compose the page path with a hash fragment derived from
``slugify`` (shared with the renderer). They do NOT validate pack/world
existence — callers attach URLs only when they already hold a session
bound to a known pack/world, so existence validation is the renderer's
job at HTTP-handle time.

Kind-specific helpers (``reference_url_for_*``) encode the v2 routing rule:
mechanics link to /reference/rules/<pack>; content links to
/reference/lore/<pack>/<world>. A helper returns ``None`` when the kind
does not map to a rendered page or the keyed entity is not present in
the caller-supplied registry.
"""
from __future__ import annotations

from sidequest.server.reference_slug import slugify


def build_rules_url(pack: str, kind: str, *keys: str) -> str:
    """Construct a rules-page URL with a kind-namespaced fragment.

    Example:
        build_rules_url("p", "class", "Burglar", "signature", "Cosh")
        -> "/reference/rules/p#class-burglar-signature-cosh"
    """
    if not keys:
        raise ValueError("build_rules_url requires at least one key segment")
    segments = [kind, *keys]
    fragment = "-".join(slugify(s) for s in segments)
    return f"/reference/rules/{pack}#{fragment}"


def build_lore_url(pack: str, world: str, kind: str, *keys: str) -> str:
    """Construct a lore-page URL with a kind-namespaced fragment."""
    if not keys:
        raise ValueError("build_lore_url requires at least one key segment")
    segments = [kind, *keys]
    fragment = "-".join(slugify(s) for s in segments)
    return f"/reference/lore/{pack}/{world}#{fragment}"


# --- Kind-specific helpers --------------------------------------------------


def reference_url_for_class(pack: str, class_name: str) -> str:
    """URL to a class section on the rules page."""
    return build_rules_url(pack, "class", class_name)


def reference_url_for_ability(
    *,
    pack: str,
    source: str,
    ability_name: str,
    owning_class_name: str | None,
) -> str | None:
    """URL to a class signature ability, or None if not a class-source ability.

    Only ``source == "Class"`` produces a URL, and only when the caller
    knows which class owns the ability. Race / Item / Play sources, or a
    class-source ability whose owner cannot be determined, return None
    (the UI renders plain text in that case).
    """
    if source != "Class" or not owning_class_name:
        return None
    return build_rules_url(
        pack, "class", owning_class_name, "signature", ability_name
    )


def reference_url_for_journal_entry(
    *,
    pack: str,
    world: str,
    category: str,
    content: str,
    legend_names: tuple[str, ...] = (),
    history_entries: tuple[str, ...] = (),
    location_names: tuple[str, ...] = (),
) -> str | None:
    """Map a journal entry to a lore-page URL.

    Routing:
      - Lore     -> first legend match, then history match, else None
      - Place    -> location match, else None
      - Person   -> None (npcs.yaml is excluded from rendering)
      - Quest    -> None (no rendered yaml)
      - Ability  -> handled by reference_url_for_ability instead; here None
    """
    if category == "Lore":
        if content in legend_names:
            return build_lore_url(pack, world, "legend", content)
        if content in history_entries:
            return build_lore_url(pack, world, "history", content)
        return None
    if category == "Place":
        if content in location_names:
            return build_lore_url(pack, world, "location", content)
        return None
    return None


def reference_url_for_location_entity(
    *,
    pack: str,
    world: str,
    entity_name: str,
    known_location_names: tuple[str, ...],
) -> str | None:
    """URL to a named location entity, or None if the world has no such location."""
    if entity_name not in known_location_names:
        return None
    return build_lore_url(pack, world, "location", entity_name)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_anchors.py -v
```

Expected: PASS.

- [ ] **Step 5: Lint + type-check**

```bash
cd sidequest-server && uv run ruff check sidequest/server/reference_anchors.py tests/server/test_reference_anchors.py && uv run ruff format sidequest/server/reference_anchors.py tests/server/test_reference_anchors.py && uv run pyright sidequest/server/reference_anchors.py
```

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/server/reference_anchors.py tests/server/test_reference_anchors.py
git commit -m "feat(reference): add URL builders for v2 anchor links

build_rules_url / build_lore_url compose page path + namespaced
fragment using the shared slugify. Kind-specific helpers encode the
mechanics->genre / content->world routing rule and the FactCategory
dispatch table for KnowledgeEntry."
```

---

## Task 4: Add JSON island + bad-anchor banner to rendered pages

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` (`_wrap_document`, `assemble_rules_page`, `assemble_lore_page`)
- Test: `sidequest-server/tests/server/test_reference_renderer_bad_anchor.py` (new)

Collect every `id="..."` emitted in the body, serialise as a JSON island,
and emit a hidden banner + tiny inline script. No external JS.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_reference_renderer_bad_anchor.py`:

```python
"""JSON island + bad-anchor banner are injected into rendered pages."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from sidequest.server.reference_renderer import assemble_rules_page


def _make_fixture_pack(root: Path) -> Path:
    pack = root / "fixture_pack"
    pack.mkdir()
    (pack / "classes.yaml").write_text(
        yaml.safe_dump({"classes": [{"name": "Knight"}, {"name": "Burglar"}]})
    )
    (pack / "rules.yaml").write_text(yaml.safe_dump({"core_rules": "Roll d6."}))
    return pack


def _extract_anchor_island(html: str) -> list[str]:
    match = re.search(
        r'<script id="ref-anchors" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match, "ref-anchors JSON island missing from rendered HTML"
    return json.loads(match.group(1))


def test_json_island_contains_namespaced_ids(tmp_path: Path) -> None:
    pack_dir = _make_fixture_pack(tmp_path)
    html = assemble_rules_page("fixture_pack", pack_dir)
    anchors = _extract_anchor_island(html)
    assert "class-knight" in anchors
    assert "class-burglar" in anchors
    assert "core-rules" in anchors
    assert "file-classes" in anchors
    assert "file-rules" in anchors


def test_anchor_island_has_no_duplicates(tmp_path: Path) -> None:
    pack_dir = _make_fixture_pack(tmp_path)
    html = assemble_rules_page("fixture_pack", pack_dir)
    anchors = _extract_anchor_island(html)
    assert len(anchors) == len(set(anchors))


def test_bad_anchor_banner_is_hidden_by_default(tmp_path: Path) -> None:
    pack_dir = _make_fixture_pack(tmp_path)
    html = assemble_rules_page("fixture_pack", pack_dir)
    assert '<div id="ref-bad-anchor" hidden>' in html


def test_bad_anchor_script_present(tmp_path: Path) -> None:
    pack_dir = _make_fixture_pack(tmp_path)
    html = assemble_rules_page("fixture_pack", pack_dir)
    # Look for the hash-check + banner-toggle behaviour.
    assert "location.hash" in html
    assert "ref-anchors" in html
    assert "ref-bad-anchor" in html
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer_bad_anchor.py -v
```

Expected: FAIL — the JSON island and banner are not emitted yet.

- [ ] **Step 3: Implement anchor collection + island + banner**

In `sidequest-server/sidequest/server/reference_renderer.py`, add an
anchor-collection mechanic. The simplest implementation: after `_wrap_document`
receives the rendered body, regex-extract every `id="..."` occurrence into
a sorted unique list, then inject the island + banner + inline script just
inside `<body>`:

```python
import json
# (add near the top, with the other imports)

_ID_ATTR_RE = re.compile(r'\bid="([a-z0-9][a-z0-9_-]*)"')


def _collect_anchor_ids(body: str) -> list[str]:
    """Return the deduplicated, source-order list of id values in ``body``."""
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _ID_ATTR_RE.finditer(body):
        anchor = match.group(1)
        if anchor in seen:
            continue
        seen.add(anchor)
        ordered.append(anchor)
    return ordered


_BAD_ANCHOR_BANNER = '<div id="ref-bad-anchor" hidden>Anchor not found on this page.</div>'

_BAD_ANCHOR_SCRIPT = (
    "<script>"
    "(function(){"
    "var h=location.hash.replace(/^#/,'');"
    "if(!h)return;"
    "var el=document.getElementById('ref-anchors');"
    "if(!el)return;"
    "var anchors=JSON.parse(el.textContent);"
    "if(anchors.indexOf(h)!==-1)return;"
    "var b=document.getElementById('ref-bad-anchor');"
    "b.textContent=\"Anchor '#\"+h+\"' not found on this page.\";"
    "b.hidden=false;"
    "})();"
    "</script>"
)


def _wrap_document(title: str, body: str) -> str:
    anchors = _collect_anchor_ids(body)
    island = (
        '<script id="ref-anchors" type="application/json">'
        f"{json.dumps(anchors)}"
        "</script>"
    )
    return (
        "<!doctype html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        f"<title>{escape(title)}</title>"
        f'<link rel="stylesheet" href="{_STYLESHEET_HREF}">'
        "</head>"
        "<body>"
        f"{_BAD_ANCHOR_BANNER}"
        f"{island}"
        f"{_BAD_ANCHOR_SCRIPT}"
        f'<h1 class="doc-title">{escape(title)}</h1>'
        f"{body}"
        "</body>"
        "</html>"
    )
```

The id regex is conservative (matches only the lowercase-alnum-hyphen ids
the renderer emits) so it won't false-match the inline script string.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer_bad_anchor.py tests/server/test_reference_renderer.py tests/server/test_reference_routes.py -v
```

Expected: PASS. If any pre-existing test asserted exact HTML byte length
or absence of `<script>` tags, update it to reflect the new island/banner
presence.

- [ ] **Step 5: Lint + type-check + commit**

```bash
cd sidequest-server
uv run ruff check sidequest/server/reference_renderer.py
uv run ruff format sidequest/server/reference_renderer.py
uv run pyright sidequest/server/reference_renderer.py
git add sidequest/server/reference_renderer.py tests/server/test_reference_renderer_bad_anchor.py tests/server/test_reference_renderer.py tests/server/test_reference_routes.py
git commit -m "feat(reference): emit anchor island + bad-anchor banner

Each rendered reference page now carries a JSON island of every
emitted anchor id plus a 10-line inline script that toggles a
hidden banner when location.hash misses the set. Satisfies the v2
spec's loud-failure requirement for stale hyperlinks."
```

---

## Task 5: Add OTEL span helpers

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py` (or wherever existing span helpers live — grep first)
- Test: `sidequest-server/tests/server/test_reference_otel.py` (new)

Per CLAUDE.md OTEL principle, every subsystem decision emits a span. v2
attaches `reference_url` in three observable outcomes:

- `sidequest.reference.url_attached` — INFO, fires when a builder returns a non-None URL and the protocol object is constructed with it.
- `sidequest.reference.url_skipped` — INFO, fires when the keyed entity is not present in the YAML registry (recoverable, content drift).
- `sidequest.reference.url_failed` — ERROR, reserved for programmer error (unknown pack/world flowing into the builders post-attach, should never fire in practice).

- [ ] **Step 1: Locate the telemetry helper module**

```bash
cd sidequest-server && grep -rn "def emit_event\|watcher_event\|otel_span\|@with_span" sidequest/telemetry/ | head -10
```

The implementer must adapt the wrapper style used by the project (e.g.
`sidequest.telemetry.watcher.emit_event(...)`). All three new spans follow
the same shape as existing reference-of `narration.turn`-style spans —
read one example before authoring.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/server/test_reference_otel.py`. Use the
existing OTEL test harness (the in-memory exporter pattern used by
`tests/server/test_*_otel.py` — pick one and mirror its setup):

```python
"""OTEL coverage for reference URL attachment."""
from __future__ import annotations

# Adapt this import to the project's existing span helpers.
from sidequest.telemetry.reference import (
    emit_reference_url_attached,
    emit_reference_url_skipped,
)
# Adapt this import to the project's in-memory exporter fixture.
from tests.helpers.otel_capture import captured_spans


def test_url_attached_span_carries_kind_and_pack() -> None:
    with captured_spans() as spans:
        emit_reference_url_attached(kind="class", pack="tea_and_murder", world=None, keys=("Burglar",))
    [span] = [s for s in spans if s.name == "sidequest.reference.url_attached"]
    assert span.attributes["reference.kind"] == "class"
    assert span.attributes["reference.pack"] == "tea_and_murder"
    assert span.attributes["reference.keys"] == "Burglar"


def test_url_skipped_span_for_unknown_entity() -> None:
    with captured_spans() as spans:
        emit_reference_url_skipped(
            kind="location",
            pack="tea_and_murder",
            world="glenross",
            keys=("A Bush",),
            reason="not_in_locations_yaml",
        )
    [span] = [s for s in spans if s.name == "sidequest.reference.url_skipped"]
    assert span.attributes["reference.reason"] == "not_in_locations_yaml"
```

(The exact captured-spans helper varies by project — replace with the
existing pattern. Run an existing OTEL test first to confirm the
in-memory exporter shape before authoring this one.)

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_otel.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement the span helpers**

Create or extend `sidequest-server/sidequest/telemetry/reference.py` with
three thin wrappers around the existing watcher-event API. Each helper
accepts named kwargs and emits a span with attributes prefixed
`reference.*` so dashboard queries can filter cleanly. Follow the same
shape as the project's existing watcher-event helpers — do not invent a
new mechanism.

- [ ] **Step 5: Run tests + commit**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_otel.py -v
uv run ruff check sidequest/telemetry/reference.py tests/server/test_reference_otel.py
uv run pyright sidequest/telemetry/reference.py
git add sidequest/telemetry/reference.py tests/server/test_reference_otel.py
git commit -m "feat(reference): OTEL spans for url attached / skipped / failed

Per CLAUDE.md OTEL principle every subsystem decision emits a span.
v2 reference URL attachment is observable for the GM panel: attached
(INFO) when the URL was set, skipped (INFO) on content drift, failed
(ERROR) on programmer error."
```

---

## Task 6: Protocol — `AbilityDefinition.reference_url`

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py:42-58` (`AbilityDefinition`)
- Modify: Whatever module(s) construct `AbilityDefinition` with `source=AbilitySource.Class` — `grep -rn "AbilityDefinition(" sidequest/` to enumerate.
- Test: `sidequest-server/tests/server/test_reference_url_attach.py` (new)

- [ ] **Step 1: Locate ability construction sites**

```bash
cd sidequest-server && grep -rn "AbilityDefinition(" sidequest/ | grep -v __pycache__ | head -30
```

Note each call site that passes `source=AbilitySource.Class` (or
`source="Class"`). Common locations: chargen / class-binding modules, party
state assembly, journal handler. The implementer attaches the URL at the
**construction site**, not in a post-hoc enrichment pass — this keeps the
attached URL flowing through the entire protocol layer.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/server/test_reference_url_attach.py` (this file will grow across Tasks 6–9):

```python
"""Server-side attachment of reference_url on protocol objects.

These tests are fixture-driven — no live genre_packs assertions. Per the
no-content-coupled-tests rule, live-pack validation lives in the separate
validator (see Task 14).
"""
from __future__ import annotations

from sidequest.protocol.models import AbilityDefinition, AbilitySource


def test_ability_definition_accepts_reference_url() -> None:
    ability = AbilityDefinition(
        name="Cosh",
        genre_description="A swift bludgeon.",
        mechanical_effect="Stun on hit.",
        source=AbilitySource.Class,
        reference_url="/reference/rules/tea_and_murder#class-burglar-signature-cosh",
    )
    assert ability.reference_url == (
        "/reference/rules/tea_and_murder#class-burglar-signature-cosh"
    )


def test_ability_definition_reference_url_defaults_to_none() -> None:
    ability = AbilityDefinition(
        name="Keen Senses",
        genre_description="Notice things.",
        mechanical_effect="Advantage on perception.",
        source=AbilitySource.Race,
    )
    assert ability.reference_url is None


def test_ability_definition_serialises_reference_url() -> None:
    ability = AbilityDefinition(
        name="Cosh",
        genre_description="A swift bludgeon.",
        mechanical_effect="Stun on hit.",
        source=AbilitySource.Class,
        reference_url="/reference/rules/p#class-burglar-signature-cosh",
    )
    payload = ability.model_dump(mode="json")
    assert payload["reference_url"] == "/reference/rules/p#class-burglar-signature-cosh"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_url_attach.py -v
```

Expected: FAIL — `reference_url` is an unknown field (extra="forbid").

- [ ] **Step 4: Add the field**

In `sidequest-server/sidequest/protocol/models.py`, extend `AbilityDefinition`:

```python
class AbilityDefinition(BaseModel):
    """Dual-voice ability representation.

    ... existing docstring ...
    reference_url: URL into /reference/rules/<pack> for the class signature
    that grants this ability. Populated server-side when source == Class
    and the ability resolves to a known classes.yaml signature; None for
    Race/Item/Play sources or when the binding cannot be resolved.
    """

    model_config = {"extra": "forbid"}

    name: str
    genre_description: str
    mechanical_effect: str
    involuntary: bool = False
    source: AbilitySource
    reference_url: str | None = None
```

- [ ] **Step 5: Wire the construction sites**

For each construction site discovered in Step 1 that builds a Class-source
ability, import and call the helper from Task 3:

```python
from sidequest.server.reference_anchors import reference_url_for_ability
from sidequest.telemetry.reference import (
    emit_reference_url_attached,
    emit_reference_url_skipped,
)
```

At the call site:

```python
url = reference_url_for_ability(
    pack=session_pack_id,
    source=source.value if isinstance(source, AbilitySource) else source,
    ability_name=ability_name,
    owning_class_name=class_name_or_none,
)
if url is not None:
    emit_reference_url_attached(
        kind="ability", pack=session_pack_id, world=None,
        keys=(class_name_or_none, ability_name),
    )
else:
    emit_reference_url_skipped(
        kind="ability", pack=session_pack_id, world=None,
        keys=(class_name_or_none or "?", ability_name),
        reason="non_class_or_no_owner",
    )
ability = AbilityDefinition(
    # ... existing fields ...
    reference_url=url,
)
```

- [ ] **Step 6: Run protocol + integration tests**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_url_attach.py tests/protocol/ -v
```

Expected: PASS. Resolve any protocol-schema tests that lock in the
allowed-field set (`extra="forbid"` will reject `reference_url` until they
acknowledge the new field).

- [ ] **Step 7: Lint + type-check + commit**

```bash
cd sidequest-server
uv run ruff check sidequest/protocol/models.py
uv run pyright sidequest/protocol/models.py
git add sidequest/protocol/models.py tests/server/test_reference_url_attach.py
# also add whatever construction-site modules were modified in Step 5
git commit -m "feat(protocol): AbilityDefinition.reference_url for class signature links

Server attaches the rules-page anchor URL when constructing
Class-source abilities; Race/Item/Play sources leave it None.
Observable via reference.url_attached / url_skipped spans."
```

---

## Task 7: Protocol — `PartyMember.class_reference_url`

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py:383-413` (`PartyMember`)
- Modify: Whatever module(s) construct `PartyMember` for PARTY_STATUS — `grep -rn "PartyMember(" sidequest/`
- Test: append to `sidequest-server/tests/server/test_reference_url_attach.py`

- [ ] **Step 1: Locate the PartyMember construction site**

```bash
cd sidequest-server && grep -rn "PartyMember(" sidequest/ | grep -v __pycache__ | head -10
```

Expected: one or two sites in the PARTY_STATUS assembler. Note the path.

- [ ] **Step 2: Write the failing test**

Append to `tests/server/test_reference_url_attach.py`:

```python
from sidequest.protocol.models import PartyMember


def test_party_member_accepts_class_reference_url() -> None:
    member = PartyMember(
        player_id="p1",
        name="Keith",
        character_name="Mr. Pip",
        current_hp=10,
        max_hp=10,
        statuses=[],
        **{"class": "Burglar"},
        level=1,
        class_reference_url="/reference/rules/tea_and_murder#class-burglar",
    )
    assert member.class_reference_url == "/reference/rules/tea_and_murder#class-burglar"


def test_party_member_class_reference_url_defaults_to_none() -> None:
    member = PartyMember(
        player_id="p1",
        name="Keith",
        character_name="Mr. Pip",
        current_hp=10,
        max_hp=10,
        statuses=[],
        **{"class": "Burglar"},
        level=1,
    )
    assert member.class_reference_url is None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_url_attach.py -v
```

Expected: FAIL — unknown field.

- [ ] **Step 4: Add the field**

In `sidequest-server/sidequest/protocol/models.py`, extend `PartyMember`:

```python
class PartyMember(ProtocolBase):
    # ... existing fields through `inventory: InventoryPayload | None = None` ...
    class_reference_url: str | None = None
    """URL to /reference/rules/<pack>#class-<slug>. Populated when the class
    is a known classes.yaml entry; None otherwise."""
```

- [ ] **Step 5: Attach at construction site**

In the PARTY_STATUS assembler, for each `PartyMember(...)` call, compute:

```python
from sidequest.server.reference_anchors import reference_url_for_class
from sidequest.telemetry.reference import emit_reference_url_attached, emit_reference_url_skipped

class_url = (
    reference_url_for_class(pack=session_pack_id, class_name=class_name)
    if class_name_is_known_in_classes_yaml
    else None
)
if class_url is not None:
    emit_reference_url_attached(kind="class", pack=session_pack_id, world=None, keys=(class_name,))
else:
    emit_reference_url_skipped(kind="class", pack=session_pack_id, world=None, keys=(class_name,), reason="not_in_classes_yaml")
```

"Known in `classes.yaml`" must be sourced from the loaded genre pack — the
implementer uses whatever pack-registry accessor exists today (find via
`grep -rn "classes.yaml\|class_definitions" sidequest/genre/`).

- [ ] **Step 6: Test + commit**

```bash
cd sidequest-server
uv run pytest tests/server/test_reference_url_attach.py -v
uv run ruff check sidequest/protocol/models.py
uv run pyright sidequest/protocol/models.py
git add sidequest/protocol/models.py tests/server/test_reference_url_attach.py
# add modified PARTY_STATUS assembler module(s)
git commit -m "feat(protocol): PartyMember.class_reference_url

PARTY_STATUS now carries the rules-page anchor URL for each
member's class, attached server-side from classes.yaml lookup."
```

---

## Task 8: Protocol — `JournalEntry.reference_url`

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py:111-131` (`JournalEntry`)
- Modify: Whatever module builds `JOURNAL_RESPONSE` rows — `grep -rn "JournalEntry(" sidequest/`
- Test: append to `sidequest-server/tests/server/test_reference_url_attach.py`

- [ ] **Step 1: Locate construction site**

```bash
cd sidequest-server && grep -rn "JournalEntry(" sidequest/ | grep -v __pycache__ | head -10
```

- [ ] **Step 2: Write the failing test**

Append to `tests/server/test_reference_url_attach.py`:

```python
from sidequest.protocol.models import FactCategory, JournalEntry


def test_journal_entry_accepts_reference_url() -> None:
    entry = JournalEntry(
        fact_id="abc",
        content="The Vicarage smells of rosewater.",
        category=FactCategory.Place,
        source="Observation",
        confidence="confirmed",
        learned_turn=3,
        reference_url="/reference/lore/tea_and_murder/glenross#location-the-vicarage",
    )
    assert entry.reference_url == (
        "/reference/lore/tea_and_murder/glenross#location-the-vicarage"
    )


def test_journal_entry_reference_url_defaults_to_none() -> None:
    entry = JournalEntry(
        fact_id="abc",
        content="Some quest.",
        category=FactCategory.Quest,
        source="Observation",
        confidence="confirmed",
        learned_turn=3,
    )
    assert entry.reference_url is None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_url_attach.py -v
```

Expected: FAIL.

- [ ] **Step 4: Add the field**

```python
class JournalEntry(ProtocolBase):
    # ... existing fields ...
    reference_url: str | None = None
    """URL into the lore page for legend / history / location entries.
    None for Person (npcs excluded), Quest (no rendered yaml), Ability
    (handled via AbilityDefinition.reference_url), and Lore/Place entries
    whose content text doesn't match a known YAML entity."""
```

- [ ] **Step 5: Attach at construction site**

In the JOURNAL_RESPONSE assembler, gather the registry sets once per call
(not per entry), then pass them into the helper:

```python
from sidequest.server.reference_anchors import reference_url_for_journal_entry

legend_names = tuple(world.legend_names)        # from the loaded world
history_entries = tuple(world.history_entry_titles)
location_names = tuple(world.location_names)

for known_fact in known_facts:
    url = reference_url_for_journal_entry(
        pack=session_pack_id,
        world=session_world_id,
        category=known_fact.category.value,
        content=known_fact.summary,
        legend_names=legend_names,
        history_entries=history_entries,
        location_names=location_names,
    )
    # emit attach / skip span based on (url is not None)
    entries.append(JournalEntry(
        # ... existing fields ...
        reference_url=url,
    ))
```

The accessors `world.legend_names` / `world.history_entry_titles` /
`world.location_names` are illustrative. The implementer adapts these to
whatever the loaded world object actually exposes (grep
`world.yaml\|legends.yaml\|history.yaml` in the genre loader to find the
attribute names). If the loader does not yet expose these as collections,
add a small read-only helper there — do not loop the YAML files inside the
JOURNAL_RESPONSE assembler.

- [ ] **Step 6: Test + commit**

```bash
cd sidequest-server
uv run pytest tests/server/test_reference_url_attach.py -v
git add sidequest/protocol/models.py tests/server/test_reference_url_attach.py
# add modified JOURNAL_RESPONSE assembler + any genre loader changes
git commit -m "feat(protocol): JournalEntry.reference_url

JOURNAL_RESPONSE entries carry an optional lore-page anchor URL
based on FactCategory (Lore -> legend|history, Place -> location)
and entity registry lookup. Person/Quest entries stay plain text."
```

---

## Task 9: Protocol — `LocationEntity.reference_url`

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py:492-540` (`LocationEntity`)
- Modify: Whatever module builds `LOCATION_DESCRIPTION` / `LocationEntity` — `grep -rn "LocationEntity(" sidequest/`
- Test: append to `sidequest-server/tests/server/test_reference_url_attach.py`

- [ ] **Step 1: Locate construction site**

```bash
cd sidequest-server && grep -rn "LocationEntity(" sidequest/ | grep -v __pycache__ | head -10
```

- [ ] **Step 2: Write the failing test**

```python
from sidequest.protocol.models import LocationEntity


def test_location_entity_accepts_reference_url() -> None:
    entity = LocationEntity(
        # ... whatever required fields LocationEntity needs; read the model first ...
        reference_url="/reference/lore/tea_and_murder/glenross#location-the-vicarage",
    )
    assert entity.reference_url == (
        "/reference/lore/tea_and_murder/glenross#location-the-vicarage"
    )
```

The implementer reads `LocationEntity`'s required fields from
`models.py` before authoring the test — substitute placeholder field
values as needed.

- [ ] **Step 3: Add the field**

```python
class LocationEntity(BaseModel):
    # ... existing fields ...
    reference_url: str | None = None
    """URL into the lore page for this entity when it has a matching
    locations entry in the world YAML. None otherwise."""
```

- [ ] **Step 4: Attach at construction site**

```python
from sidequest.server.reference_anchors import reference_url_for_location_entity

url = reference_url_for_location_entity(
    pack=session_pack_id,
    world=session_world_id,
    entity_name=entity.name,
    known_location_names=known_location_names,
)
# emit attach / skip span
entity_dto = LocationEntity(
    # ... existing fields ...
    reference_url=url,
)
```

- [ ] **Step 5: Test + commit**

```bash
cd sidequest-server
uv run pytest tests/server/test_reference_url_attach.py -v
git add sidequest/protocol/models.py tests/server/test_reference_url_attach.py
# add modified LOCATION_DESCRIPTION assembler module
git commit -m "feat(protocol): LocationEntity.reference_url

LOCATION_DESCRIPTION entities carry an optional lore-page anchor
URL when the entity matches a world locations entry."
```

---

## Task 10: UI types — mirror server schema additions

**Files:**
- Modify: `sidequest-ui/src/types/payloads.ts`
- Modify: `sidequest-ui/src/providers/GameStateProvider.tsx` (KnowledgeEntry interface)
- Modify: `sidequest-ui/src/components/CharacterSheet.tsx` (AbilityDefinition interface — line 3)

No new behaviour — just keeping TS in lockstep with the server. Without
this, the panels in Tasks 12-14 cannot reference the new fields.

- [ ] **Step 1: Grep current TS shapes**

```bash
cd sidequest-ui && grep -rn "AbilityDefinition\|KnowledgeEntry\|LocationEntity\|class PartyMember\|class_name" src/types/payloads.ts src/providers/GameStateProvider.tsx src/components/CharacterSheet.tsx | head -30
```

- [ ] **Step 2: Add `reference_url?: string | null` everywhere it now exists server-side**

- `AbilityDefinition` in `CharacterSheet.tsx`:

```ts
export interface AbilityDefinition {
  name: string;
  genre_description: string;
  mechanical_effect: string;
  involuntary?: boolean;
  source: AbilitySource;
  reference_url?: string | null;
}
```

- `KnowledgeEntry` in `GameStateProvider.tsx`:

```ts
export interface KnowledgeEntry {
  // ... existing fields ...
  reference_url?: string | null;
}
```

- `PartyMember` and `LocationEntity` in `payloads.ts`: add the
  corresponding optional `class_reference_url?: string | null` and
  `reference_url?: string | null` next to existing fields.

- [ ] **Step 3: Type-check**

```bash
cd sidequest-ui && npx tsc --noEmit
```

Expected: clean. (No production code yet consumes these — Tasks 11–14 wire
them up.)

- [ ] **Step 4: Commit**

```bash
cd sidequest-ui
git add src/types/payloads.ts src/providers/GameStateProvider.tsx src/components/CharacterSheet.tsx
git commit -m "feat(types): mirror server reference_url additions

AbilityDefinition, KnowledgeEntry, PartyMember.class_reference_url,
LocationEntity.reference_url — all optional, no behaviour change yet."
```

---

## Task 11: UI — ReferenceLinks disabled state + ConnectScreen integration

**Files:**
- Modify: `sidequest-ui/src/components/ReferenceLinks.tsx`
- Modify: `sidequest-ui/src/screens/ConnectScreen.tsx`
- Test: `sidequest-ui/src/components/__tests__/ReferenceLinks.disabled.test.tsx` (new)
- Test: `sidequest-ui/src/screens/__tests__/ConnectScreen.reference.test.tsx` (new)

- [ ] **Step 1: Read the existing ReferenceLinks component**

```bash
cd sidequest-ui && cat src/components/ReferenceLinks.tsx
```

Confirm the current prop shape (likely `{ pack: string; world?: string }`)
and how it composes its two anchors.

- [ ] **Step 2: Write the failing tests**

Create `sidequest-ui/src/components/__tests__/ReferenceLinks.disabled.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ReferenceLinks } from '@/components/ReferenceLinks';


describe('ReferenceLinks (lobby disabled states)', () => {
  it('renders both buttons enabled when pack and world are set', () => {
    render(<ReferenceLinks pack="tea_and_murder" world="glenross" />);
    const rules = screen.getByRole('link', { name: /rules/i });
    const lore = screen.getByRole('link', { name: /lore/i });
    expect(rules).toHaveAttribute('href', '/reference/rules/tea_and_murder');
    expect(lore).toHaveAttribute(
      'href',
      '/reference/lore/tea_and_murder/glenross',
    );
  });

  it('renders Lore as aria-disabled when world is missing', () => {
    render(<ReferenceLinks pack="tea_and_murder" world={null} />);
    const lore = screen.getByText(/lore/i).closest('[aria-disabled="true"]');
    expect(lore).not.toBeNull();
  });

  it('renders nothing meaningful when pack is missing', () => {
    render(<ReferenceLinks pack={null} world={null} />);
    expect(screen.queryByRole('link', { name: /rules/i })).toBeNull();
    expect(screen.queryByRole('link', { name: /lore/i })).toBeNull();
  });
});
```

Create `sidequest-ui/src/screens/__tests__/ConnectScreen.reference.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ConnectScreen from '@/screens/ConnectScreen';
// Adjust mocks to whatever providers ConnectScreen requires today —
// snapshot the current ConnectScreen test setup first and copy its shape.


describe('ConnectScreen reference surface', () => {
  it('shows enabled Rules and disabled Lore when only pack is selected', () => {
    // Render ConnectScreen with selectedPack="tea_and_murder", selectedWorld=null
    // (use whatever provider/mocks the existing ConnectScreen tests use).
    // ...
    const rules = screen.getByRole('link', { name: /rules/i });
    expect(rules).toHaveAttribute('href', '/reference/rules/tea_and_murder');
    const lore = screen.getByText(/lore/i).closest('[aria-disabled="true"]');
    expect(lore).not.toBeNull();
  });

  it('shows both buttons enabled once pack and world are selected', () => {
    // Render with both set.
    const lore = screen.getByRole('link', { name: /lore/i });
    expect(lore).toHaveAttribute(
      'href',
      '/reference/lore/tea_and_murder/glenross',
    );
  });

  it('does not dispatch a websocket message when a reference link is clicked', async () => {
    const send = vi.fn();
    // Render ConnectScreen with a mocked socket whose send is `send`.
    // (Match the existing ConnectScreen test harness.)
    const user = userEvent.setup();
    await user.click(screen.getByRole('link', { name: /rules/i }));
    expect(send).not.toHaveBeenCalled();
  });
});
```

Use the existing ConnectScreen test (`src/screens/__tests__/ConnectScreen.test.tsx`
or similar) as the harness template; do not invent a new mocking
approach. The implementer copy-pastes that file's provider wiring and
adds the three cases above.

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd sidequest-ui && npx vitest run src/components/__tests__/ReferenceLinks.disabled.test.tsx src/screens/__tests__/ConnectScreen.reference.test.tsx
```

Expected: FAIL.

- [ ] **Step 4: Implement the disabled state in ReferenceLinks**

In `sidequest-ui/src/components/ReferenceLinks.tsx`, change the prop
contract so `pack` and `world` may be `null`. Render rule for each button:
if its required props are present, emit `<a href=...>`; otherwise emit
`<span aria-disabled="true" className="ref-link ref-link--disabled">…</span>`.

```tsx
type Props = {
  pack: string | null;
  world: string | null;
};

export function ReferenceLinks({ pack, world }: Props) {
  const rulesHref = pack ? `/reference/rules/${pack}` : null;
  const loreHref = pack && world ? `/reference/lore/${pack}/${world}` : null;
  return (
    <div className="ref-links">
      {rulesHref ? (
        <a className="ref-link" href={rulesHref} target="_blank" rel="noopener">
          Rules
        </a>
      ) : (
        <span className="ref-link ref-link--disabled" aria-disabled="true">
          Rules
        </span>
      )}
      {loreHref ? (
        <a className="ref-link" href={loreHref} target="_blank" rel="noopener">
          Lore
        </a>
      ) : (
        <span className="ref-link ref-link--disabled" aria-disabled="true">
          Lore
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Wire into ConnectScreen**

In `sidequest-ui/src/screens/ConnectScreen.tsx`, render `<ReferenceLinks pack={selectedPack} world={selectedWorld} />` next to the pack/world pickers. Source the selected values from whatever state ConnectScreen already maintains (do not introduce a new store).

- [ ] **Step 6: Tests + lint + commit**

```bash
cd sidequest-ui
npx vitest run src/components/__tests__/ReferenceLinks.disabled.test.tsx src/screens/__tests__/ConnectScreen.reference.test.tsx
npx eslint src/components/ReferenceLinks.tsx src/screens/ConnectScreen.tsx
git add src/components/ReferenceLinks.tsx src/screens/ConnectScreen.tsx src/components/__tests__/ReferenceLinks.disabled.test.tsx src/screens/__tests__/ConnectScreen.reference.test.tsx
git commit -m "feat(ui): lobby reference surface

ReferenceLinks gains aria-disabled state; ConnectScreen renders
Rules (enabled when pack picked) and Lore (enabled only when pack
and world picked). Clicking links never posts a WebSocket message."
```

---

## Task 12: UI — CharacterSheet anchor wrapping

**Files:**
- Modify: `sidequest-ui/src/components/CharacterSheet.tsx`
- Test: `sidequest-ui/src/components/__tests__/CharacterSheet.reference.test.tsx` (new)

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { CharacterSheet } from '@/components/CharacterSheet';

const baseAbility = {
  name: 'Cosh',
  genre_description: 'Bonk.',
  mechanical_effect: 'Stun.',
  source: 'Class' as const,
};

const baseData = {
  name: 'Mr. Pip',
  // fill in whatever required fields CharacterSheetProps['data'] needs —
  // copy from the existing CharacterSheet test.
  abilities: [],
};


describe('CharacterSheet reference hyperlinks', () => {
  it('renders an ability with reference_url as a target=_blank anchor', () => {
    render(
      <CharacterSheet
        data={{
          ...baseData,
          abilities: [
            { ...baseAbility, reference_url: '/reference/rules/p#class-burglar-signature-cosh' },
          ],
        }}
      />,
    );
    const link = screen.getByRole('link', { name: /cosh/i });
    expect(link).toHaveAttribute(
      'href',
      '/reference/rules/p#class-burglar-signature-cosh',
    );
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('renders an ability without reference_url as plain text', () => {
    render(
      <CharacterSheet
        data={{
          ...baseData,
          abilities: [{ ...baseAbility, reference_url: null }],
        }}
      />,
    );
    expect(screen.queryByRole('link', { name: /cosh/i })).toBeNull();
    expect(screen.getByText(/cosh/i)).toBeInTheDocument();
  });

  it('clicking an ability anchor does not dispatch any websocket message', async () => {
    const send = vi.fn();
    // Wrap in whatever provider supplies useGameSocket — the existing
    // CharacterSheet test should already mock this; copy its harness.
    render(
      <CharacterSheet
        data={{
          ...baseData,
          abilities: [
            { ...baseAbility, reference_url: '/reference/rules/p#class-burglar-signature-cosh' },
          ],
        }}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole('link', { name: /cosh/i }));
    expect(send).not.toHaveBeenCalled();
  });
});
```

Extend with two more cases mirroring the above but for the class name and
the race/archetype name — both should follow the same anchor-when-url
pattern.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-ui && npx vitest run src/components/__tests__/CharacterSheet.reference.test.tsx
```

Expected: FAIL.

- [ ] **Step 3: Implement anchor wrapping in `CharacterSheet.tsx`**

For each ability in the abilities list, wrap the displayed name:

```tsx
{data.abilities.map((ability) => {
  const label = ability.name;
  const node = ability.reference_url ? (
    <a href={ability.reference_url} target="_blank" rel="noopener">
      {label}
    </a>
  ) : (
    label
  );
  return (
    <li key={ability.name}>
      {node}
      <span className="ml-2 text-xs uppercase">{ability.source}</span>
    </li>
  );
})}
```

For the class name in the header subtitle, do the same: if
`data.class_reference_url` is truthy, wrap the class name in an anchor.
Likewise for race/archetype if the data carries
`race_reference_url` / `archetype_reference_url`. Only wire fields that
already exist in the props' TS shape; do not add fields the protocol
doesn't carry.

- [ ] **Step 4: Tests + commit**

```bash
cd sidequest-ui
npx vitest run src/components/__tests__/CharacterSheet.reference.test.tsx src/components/__tests__/CharacterSheet.test.tsx
git add src/components/CharacterSheet.tsx src/components/__tests__/CharacterSheet.reference.test.tsx
git commit -m "feat(ui): CharacterSheet hyperlinks abilities to reference page

Class-source abilities, class names, and archetype names render as
target=_blank anchors when the server attached a reference_url;
plain text otherwise. Click never dispatches a WebSocket message."
```

---

## Task 13: UI — KnowledgeJournal anchor wrapping

**Files:**
- Modify: `sidequest-ui/src/components/KnowledgeJournal.tsx`
- Test: `sidequest-ui/src/components/__tests__/KnowledgeJournal.reference.test.tsx` (new)

- [ ] **Step 1: Write the failing test**

Mirror the CharacterSheet test pattern: render an entry with
`reference_url`, expect an anchor; without, expect plain text. Click an
anchor, expect no WebSocket send. (Use the existing KnowledgeJournal test
file's mocks as the harness template.)

- [ ] **Step 2: Run test to verify it fails, then implement**

In `KnowledgeJournal.tsx`, find the row renderer that prints
`entry.content` (or `entry.title`) and wrap in an anchor when
`entry.reference_url` is present.

- [ ] **Step 3: Tests + commit**

```bash
cd sidequest-ui
npx vitest run src/components/__tests__/KnowledgeJournal.reference.test.tsx src/components/__tests__/KnowledgeJournal.test.tsx
git add src/components/KnowledgeJournal.tsx src/components/__tests__/KnowledgeJournal.reference.test.tsx
git commit -m "feat(ui): KnowledgeJournal hyperlinks entries to lore page

Entries with a server-attached reference_url render as target=_blank
anchors; entries without render as plain text. Click never dispatches
a WebSocket message."
```

---

## Task 14: UI — LocationPanel anchor wrapping

**Files:**
- Modify: `sidequest-ui/src/components/LocationPanel.tsx`
- Test: `sidequest-ui/src/components/__tests__/LocationPanel.reference.test.tsx` (new)

- [ ] **Step 1: Read LocationPanel to find the entity render site**

```bash
cd sidequest-ui && grep -n "entities\|entity\.name\|LocationEntity" src/components/LocationPanel.tsx
```

Locate where each location entity's name is printed.

- [ ] **Step 2: Write the failing test**

Same pattern as Tasks 12-13: entity with `reference_url` → anchor;
without → plain text; click → no WebSocket send.

- [ ] **Step 3: Implement + test + commit**

```bash
cd sidequest-ui
npx vitest run src/components/__tests__/LocationPanel.reference.test.tsx src/components/__tests__/LocationPanel.test.tsx
git add src/components/LocationPanel.tsx src/components/__tests__/LocationPanel.reference.test.tsx
git commit -m "feat(ui): LocationPanel hyperlinks entities to lore page

Location entities with a server-attached reference_url render as
target=_blank anchors; otherwise plain text. Click never dispatches
a WebSocket message."
```

---

## Task 15: Server integration test against a fixture pack

**Files:**
- Create: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/classes.yaml`
- Create: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/cultures.yaml`
- Create: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/world.yaml`
- Create: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/legends.yaml`
- Create: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/locations.yaml`
- Test: `sidequest-server/tests/server/test_reference_integration.py` (new)

End-to-end check: hit `/reference/rules/fixture_pack` and
`/reference/lore/fixture_pack/fixture_world`, assert namespaced anchors,
JSON island, banner, and a known cross-file collision (a class "Knight"
and a culture "Knight") produce distinct ids.

- [ ] **Step 1: Author the fixture pack**

```yaml
# tests/fixtures/genre_packs/fixture_pack/classes.yaml
classes:
  - name: Knight
    signature_ability:
      name: Lance Charge
      description: A brave charge.
  - name: Burglar
    signature_ability:
      name: Cosh
      description: A swift bludgeon.
```

```yaml
# tests/fixtures/genre_packs/fixture_pack/cultures.yaml
cultures:
  - name: Knight
    description: A noble culture, sharing the name with the class by design.
```

```yaml
# tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/world.yaml
name: fixture_world
description: Test world.
```

```yaml
# tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/legends.yaml
legends:
  - name: The Rending
    description: A test legend.
```

```yaml
# tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/locations.yaml
locations:
  - name: The Vicarage
    description: A test location.
```

- [ ] **Step 2: Write the integration test**

```python
"""End-to-end test: render the fixture pack via the live router.

Per project rules, no assertions against live genre_packs — only against
this fixture pack which is part of the test suite and version-controlled.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidequest.server.app import create_app


FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "genre_packs"


@pytest.fixture
def client() -> TestClient:
    app = create_app()  # whatever factory the project uses
    app.state.genre_pack_search_paths = [str(FIXTURE_ROOT)]
    return TestClient(app)


def _anchor_island(html: str) -> list[str]:
    match = re.search(
        r'<script id="ref-anchors" type="application/json">(.*?)</script>',
        html, re.DOTALL,
    )
    assert match, "anchor island missing"
    return json.loads(match.group(1))


def test_rules_page_emits_namespaced_anchors(client: TestClient) -> None:
    response = client.get("/reference/rules/fixture_pack")
    assert response.status_code == 200
    anchors = _anchor_island(response.text)
    assert "class-knight" in anchors
    assert "class-burglar" in anchors


def test_lore_page_emits_namespaced_anchors(client: TestClient) -> None:
    response = client.get("/reference/lore/fixture_pack/fixture_world")
    assert response.status_code == 200
    anchors = _anchor_island(response.text)
    assert "culture-knight" in anchors
    assert "legend-the-rending" in anchors
    assert "location-the-vicarage" in anchors


def test_class_and_culture_share_name_without_anchor_collision(
    client: TestClient,
) -> None:
    rules = client.get("/reference/rules/fixture_pack").text
    lore = client.get("/reference/lore/fixture_pack/fixture_world").text
    assert 'id="class-knight"' in rules
    assert 'id="culture-knight"' in lore
    assert 'id="class-knight"' not in lore
    assert 'id="culture-knight"' not in rules


def test_bad_anchor_banner_present_on_both_pages(client: TestClient) -> None:
    for path in (
        "/reference/rules/fixture_pack",
        "/reference/lore/fixture_pack/fixture_world",
    ):
        html = client.get(path).text
        assert '<div id="ref-bad-anchor" hidden>' in html
        assert "location.hash" in html
```

- [ ] **Step 3: Run integration test**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_integration.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd sidequest-server
git add tests/fixtures/genre_packs/fixture_pack/ tests/server/test_reference_integration.py
git commit -m "test(reference): integration test against fixture pack

Covers namespaced anchors, JSON island, banner element, and the
cross-file name-collision invariant (class Knight vs culture Knight
produce distinct ids on their respective pages)."
```

---

## Task 16: Content-team authoring note

**Files:**
- Modify: `sidequest-content/CLAUDE.md` (append a paragraph to the appropriate section, or under a new "Reference page anchors" subsection if no analogous one exists)

- [ ] **Step 1: Read the current CLAUDE.md**

```bash
cd sidequest-content && cat CLAUDE.md
```

- [ ] **Step 2: Add the authoring note**

Append (under a "Reference page anchors" subsection):

```markdown
## Reference page anchors

The running game wires hyperlinks from character sheets, knowledge entries,
and location panels into anchors on `/reference/rules/<pack>` and
`/reference/lore/<pack>/<world>`. Anchor ids are derived from each entity's
`name` field via a slugify function: lowercase, ASCII, hyphenated. Renaming
a class, archetype, culture, legend, or location without coordinating with
in-game consumers (party state, knowledge journal, location entities)
breaks every inbound link to its anchor; the reference page will show a
visible "Anchor not found" banner. There is no `slug:` override field in
v2 — slug stability is name stability.
```

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add CLAUDE.md
git commit -m "docs: note reference-page anchor stability constraint

Renaming a class / archetype / culture / legend / location without
coordinating with in-game consumers breaks reference-page hyperlinks.
v2 has no slug override; slug stability follows name stability."
```

---

## Task 17: SUPERSEDED — see Task 27

> **v3:** This task is replaced by Task 27 (the full chrome-aware gate). Do not execute Task 17 in v3 mode; the chrome work in Tasks 18–26 changes the rendered HTML enough that Task 17's smoke steps would fail without the corresponding chrome assertions. Skip ahead to Task 18, then run Task 27 as the final gate.
>
> The original Task 17 content is preserved below for traceability only.

- [ ] **Step 1: Server**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest -v
```

Expected: clean.

- [ ] **Step 2: UI**

```bash
cd sidequest-ui && npx tsc --noEmit && npx eslint src && npx vitest run
```

Expected: clean.

- [ ] **Step 3: Aggregate gate**

```bash
cd /Users/slabgorb/Projects/oq-1 && just check-all
```

Expected: clean.

- [ ] **Step 4: Manual smoke (run only after the above gates are clean)**

```bash
cd /Users/slabgorb/Projects/oq-1 && just up
```

Then in a browser:

1. Open `http://localhost:5173/`. On the ConnectScreen, before selecting a
   pack, both Rules and Lore should appear as visibly-disabled spans (not
   clickable). Select a pack → Rules becomes a real link, Lore is still
   disabled. Select a world → Lore becomes a real link. Click each — each
   opens the corresponding reference page in a new tab.
2. Join a session, finish chargen, and load the character sheet. A
   class-source ability whose name matches a `classes.yaml` signature
   should render as a hyperlink. Click it — the rules page should open at
   the right anchor. Hash-not-found case: manually edit the URL to
   `…#class-this-does-not-exist`, reload — the "Anchor not found" banner
   should appear.
3. Open the KnowledgeJournal. A Lore-category fact that matches a known
   legend (e.g. "The Rending" in glenross) should render as a hyperlink to
   the lore page. A Person-category fact ("Aunt Pemberton") should stay
   plain text.
4. Check the GM panel. After the above interactions, the
   `sidequest.reference.url_attached` span should appear at least once;
   if a fact matched no YAML entry, `url_skipped` should appear with the
   reason.

If any of the four steps fails, stop, file the bug, do not merge.

- [ ] **Step 5: Push branches and open PRs**

For each subrepo:

```bash
git push -u origin feat/reference-v2
# Open PR targeting `develop` for the subrepo, NOT main.
```

For the orchestrator (plan + spec doc), the plan was already committed to
`main` upstream of execution; no extra PR needed there.

---

## Task 18: Renderer reads `theme.yaml` and emits chrome data attributes

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` (`assemble_rules_page`, `assemble_lore_page`, `_wrap_document`)
- New: `sidequest-server/sidequest/server/reference_theme.py` — pure loader that returns a `ReferenceTheme` dataclass from a pack's `theme.yaml` and (optionally) a world's `lore.yaml`.
- Test: `sidequest-server/tests/server/test_reference_theme.py` (new)

The bundle's HTML is keyed on `<html data-pack="heavy_metal" data-world="long_foundry" data-archetype="rugged" class="dark">`. Every per-pack rule in `theme.css` selects on those attributes. Without them the page renders as a no-pack default and looks broken. v3 reads the values from `theme.yaml` (`archetype` is already a field there per the heavy_metal example, plus `web_font_family`, palette, `dinkus.glyph.*`) and emits them.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_reference_theme.py`:

```python
"""Pure loader for reference-page chrome theme inputs."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sidequest.server.reference_theme import (
    ReferenceTheme,
    MissingThemeFieldError,
    load_reference_theme,
)


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data))


def test_load_required_fields(tmp_path: Path) -> None:
    pack_dir = tmp_path / "fixture_pack"
    pack_dir.mkdir()
    _write(pack_dir / "theme.yaml", {
        "archetype": "rugged",
        "web_font_family": "IM Fell English",
        "display_font_family": "Pirata One",
        "primary": "#8B0000",
        "accent": "#B8860B",
        "background": "#0F0A0A",
        "dinkus": {"glyph": {"light": "†", "medium": "✠", "heavy": "⸸  ☥  ⸸"}},
    })
    theme = load_reference_theme(pack="fixture_pack", pack_dir=pack_dir)
    assert theme.pack == "fixture_pack"
    assert theme.archetype == "rugged"
    assert theme.web_font_family == "IM Fell English"
    assert theme.display_font_family == "Pirata One"
    assert theme.dinkus_light == "†"
    assert theme.dinkus_medium == "✠"
    assert theme.dinkus_heavy == "⸸  ☥  ⸸"


def test_missing_display_font_raises_loudly(tmp_path: Path) -> None:
    pack_dir = tmp_path / "fixture_pack"
    pack_dir.mkdir()
    _write(pack_dir / "theme.yaml", {
        "archetype": "rugged",
        "web_font_family": "IM Fell English",
        # display_font_family intentionally absent
        "primary": "#8B0000",
        "dinkus": {"glyph": {"light": "†", "medium": "✠", "heavy": "⸸"}},
    })
    with pytest.raises(MissingThemeFieldError) as exc:
        load_reference_theme(pack="fixture_pack", pack_dir=pack_dir)
    assert "display_font_family" in str(exc.value)


def test_missing_archetype_raises_loudly(tmp_path: Path) -> None:
    pack_dir = tmp_path / "fixture_pack"
    pack_dir.mkdir()
    _write(pack_dir / "theme.yaml", {"web_font_family": "x", "display_font_family": "y"})
    with pytest.raises(MissingThemeFieldError):
        load_reference_theme(pack="fixture_pack", pack_dir=pack_dir)
```

- [ ] **Step 2: Implement the loader**

Create `sidequest-server/sidequest/server/reference_theme.py`:

```python
"""Loader for reference-page chrome theme inputs.

Reads <pack>/theme.yaml and returns a frozen ReferenceTheme dataclass.
Missing required fields raise MissingThemeFieldError — no silent fallback.
The renderer uses this to emit <html data-pack data-world data-archetype>
attributes and pack-keyed inline CSS variables.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class MissingThemeFieldError(KeyError):
    """Raised when theme.yaml is missing a field required by the renderer."""


_REQUIRED = (
    "archetype",
    "web_font_family",
    "display_font_family",
    "primary",
    "accent",
    "background",
)


@dataclass(frozen=True)
class ReferenceTheme:
    pack: str
    archetype: str
    web_font_family: str
    display_font_family: str
    primary: str
    accent: str
    background: str
    dinkus_light: str
    dinkus_medium: str
    dinkus_heavy: str


def load_reference_theme(*, pack: str, pack_dir: Path) -> ReferenceTheme:
    theme_path = pack_dir / "theme.yaml"
    if not theme_path.exists():
        raise MissingThemeFieldError(f"{pack}: theme.yaml not found at {theme_path}")
    with theme_path.open() as fh:
        data = yaml.safe_load(fh) or {}
    for field in _REQUIRED:
        if field not in data:
            raise MissingThemeFieldError(f"{pack}: theme.yaml missing required field '{field}'")
    dinkus = (data.get("dinkus") or {}).get("glyph") or {}
    for w in ("light", "medium", "heavy"):
        if w not in dinkus:
            raise MissingThemeFieldError(f"{pack}: theme.yaml missing dinkus.glyph.{w}")
    return ReferenceTheme(
        pack=pack,
        archetype=data["archetype"],
        web_font_family=data["web_font_family"],
        display_font_family=data["display_font_family"],
        primary=data["primary"],
        accent=data["accent"],
        background=data["background"],
        dinkus_light=dinkus["light"],
        dinkus_medium=dinkus["medium"],
        dinkus_heavy=dinkus["heavy"],
    )
```

- [ ] **Step 3: Wire into the renderer's page assemblers**

In `reference_renderer.py`, modify `assemble_rules_page(pack, pack_dir)` and `assemble_lore_page(pack, world, pack_dir, world_dir)` to call `load_reference_theme(pack=pack, pack_dir=pack_dir)` and thread the resulting `ReferenceTheme` into `_wrap_document(...)` (signature gains a `theme: ReferenceTheme` parameter). On `MissingThemeFieldError` the route handler must let it bubble — Task 24's validator is the proactive surface; the route handler converts to HTTP 500 with an `ERROR` OTEL span (`sidequest.reference.theme_missing`).

- [ ] **Step 4: Run tests, lint, commit**

```bash
cd sidequest-server
uv run pytest tests/server/test_reference_theme.py tests/server/test_reference_renderer.py tests/server/test_reference_routes.py -v
uv run ruff check sidequest/server/reference_theme.py sidequest/server/reference_renderer.py
uv run pyright sidequest/server/reference_theme.py sidequest/server/reference_renderer.py
git add sidequest/server/reference_theme.py sidequest/server/reference_renderer.py tests/server/test_reference_theme.py
git commit -m "feat(reference): load theme.yaml chrome inputs for renderer

ReferenceTheme dataclass collects archetype, palette, web/display
font, and the three dinkus glyphs from a pack's theme.yaml. Missing
required field raises MissingThemeFieldError — loud, no fallback."
```

---

## Task 19: Add `display_font_family` to `theme.yaml` schema

**Files:**
- Modify: `sidequest-content/CLAUDE.md` (append authoring note)
- Modify: `sidequest-content/genre_packs/<each pack>/theme.yaml` — add `display_font_family:` (see seed table below)
- Modify: `sidequest-content/genre_workshopping/<each pack>/theme.yaml` — same
- Test: covered by Task 24's validator (no pytest)

The design tool worked around `theme.yaml` having no display-font field by hardcoding the choice per pack in `theme.css`. v3 elevates that to a content-controlled field. Seed values come straight from the bundle's `theme.css` per-pack `--folio-font-display` lines + the design tool's note in `chats/chat1.md` (final assistant message).

| Pack | `display_font_family` (seed value) |
|---|---|
| `heavy_metal` | `Pirata One` |
| `caverns_and_claudes` | `Pirata One` |
| `victoria` (if shipped) / `tea_and_murder` | `Playfair Display` |
| `mutant_wasteland` | `Special Elite` |
| `space_opera` | `Orbitron` |
| `neon_dystopia` | `Orbitron` |
| `pulp_noir` | `Playfair Display` (default — content team confirms) |
| `road_warrior` | `Special Elite` (default — content team confirms) |
| `spaghetti_western` | `Special Elite` (default — content team confirms) |
| `elemental_harmony` | `Playfair Display` (default — content team confirms) |

- [ ] **Step 1: Add the authoring note to `sidequest-content/CLAUDE.md`**

Append under the existing "Reference page anchors" section from v2 Task 16, or at end:

```markdown
## Reference page chrome

Every `theme.yaml` must declare:

- `web_font_family` — body / narrative serif. Already shipped.
- `display_font_family` — hero title / `<h1>` font. **Required by v3.** No silent fallback; missing field = pack fails to render its reference page and the validator surfaces the gap.
- `archetype` — one of `rugged`, `terminal`, `parchment`. Selects the structural font stack (`--font-body`, `--font-ui`) and the page's `data-archetype` attribute.
- `dinkus.glyph.{light,medium,heavy}` — three ornamental glyphs used between sections. All three required.

When picking `display_font_family`, prefer a Google Font already imported by `reference/static/theme.css` to avoid network fetches: Pirata One, Playfair Display, Special Elite, Orbitron, IM Fell English, Rajdhani, Share Tech Mono.
```

- [ ] **Step 2: Edit each live pack's `theme.yaml`**

Per the seed table. Each edit is a one-line addition. Do not change existing fields.

- [ ] **Step 3: Run the validator (Task 24, once it lands) to confirm green**

If Tasks 23 and 19 race, ship Task 19's content edits behind a `feat/reference-v3-display-font` content branch and merge after Task 23 is green on `develop`.

- [ ] **Step 4: Commit (in `sidequest-content`)**

```bash
cd sidequest-content
git add CLAUDE.md genre_packs/*/theme.yaml genre_workshopping/*/theme.yaml
git commit -m "feat(theme): add display_font_family to every pack's theme.yaml

Required by sidequest-server reference-page chrome (v3). Seed values
match the design bundle's per-pack mapping; content team owns the
choice going forward."
```

---

## Task 20: Static CSS route serves bundled `theme.css` + `styles.css`

**Files:**
- Create: `sidequest-server/sidequest/server/reference_static.py` — small FastAPI sub-router serving the two CSS files.
- Move: `docs/design-bundles/2026-05-23-lore-and-rules/project/{theme,styles}.css` → `sidequest-server/sidequest/server/static/reference/{theme,styles}.css` (these become production assets; the bundle copies are the historical source).
- Modify: `sidequest-server/sidequest/server/reference_routes.py` — mount the static sub-router at `/reference/static/`.
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` — `_wrap_document` now emits `<link rel="stylesheet" href="/reference/static/theme.css">` and `<link rel="stylesheet" href="/reference/static/styles.css">` in that order (theme first so styles wins on conflict).
- Test: `sidequest-server/tests/server/test_reference_static.py` (new)

- [ ] **Step 1: Write the failing test**

```python
"""The static CSS sub-router serves the bundled theme + styles."""
from __future__ import annotations

from fastapi.testclient import TestClient

from sidequest.server.app import create_app


def test_theme_css_served() -> None:
    client = TestClient(create_app())
    response = client.get("/reference/static/theme.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    # Bundle marker present (matches the first @import line).
    assert "fonts.googleapis.com" in response.text


def test_styles_css_served() -> None:
    client = TestClient(create_app())
    response = client.get("/reference/static/styles.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
```

- [ ] **Step 2: Move the CSS files into the server tree**

```bash
mkdir -p sidequest-server/sidequest/server/static/reference
cp docs/design-bundles/2026-05-23-lore-and-rules/project/theme.css \
   sidequest-server/sidequest/server/static/reference/theme.css
cp docs/design-bundles/2026-05-23-lore-and-rules/project/styles.css \
   sidequest-server/sidequest/server/static/reference/styles.css
```

(Do not delete the bundle copies — they remain the historical design source. The server copy is the production artifact.)

- [ ] **Step 3: Implement the static sub-router**

```python
# sidequest-server/sidequest/server/reference_static.py
from pathlib import Path
from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

router = APIRouter()
_STATIC_ROOT = Path(__file__).parent / "static" / "reference"
router.mount("/", StaticFiles(directory=_STATIC_ROOT), name="reference-static")
```

Mount it in `reference_routes.py`:

```python
from sidequest.server.reference_static import router as reference_static_router
app.include_router(reference_static_router, prefix="/reference/static")
```

- [ ] **Step 4: Update `_wrap_document` to emit both stylesheets + chrome attrs**

```python
def _wrap_document(title: str, body: str, theme: ReferenceTheme, world: str | None = None) -> str:
    anchors = _collect_anchor_ids(body)
    island = (
        '<script id="ref-anchors" type="application/json">'
        f"{json.dumps(anchors)}"
        "</script>"
    )
    world_attr = f' data-world="{escape(world)}"' if world else ""
    return (
        "<!doctype html>"
        f'<html lang="en" class="dark" data-pack="{escape(theme.pack)}"{world_attr} data-archetype="{escape(theme.archetype)}">'
        "<head>"
        '<meta charset="utf-8">'
        f"<title>{escape(title)}</title>"
        '<link rel="stylesheet" href="/reference/static/theme.css">'
        '<link rel="stylesheet" href="/reference/static/styles.css">'
        "</head>"
        "<body>"
        '<div class="background-canvas" aria-hidden="true"></div>'
        f"{_BAD_ANCHOR_BANNER}"
        f"{island}"
        f"{_BAD_ANCHOR_SCRIPT}"
        f'<div class="page">{body}</div>'
        "</body>"
        "</html>"
    )
```

The bundle's HTML wraps `<body>` content in `<div class="page">…<div class="layout">…</div></div>`; `_wrap_document` only emits the outer `.page`. The hero (Task 21) + layout + TOC (Task 22) + sections live inside `body`.

- [ ] **Step 5: Test + lint + commit**

```bash
cd sidequest-server
uv run pytest tests/server/test_reference_static.py tests/server/test_reference_renderer_bad_anchor.py -v
uv run ruff check sidequest/server/reference_static.py sidequest/server/reference_renderer.py
git add sidequest/server/reference_static.py sidequest/server/static/reference/ sidequest/server/reference_routes.py sidequest/server/reference_renderer.py tests/server/test_reference_static.py
git commit -m "feat(reference): static CSS route + chrome data attrs

Bundled theme.css + styles.css are served from /reference/static/.
Renderer emits <html data-pack data-world data-archetype> so per-pack
selectors in theme.css fire. JSON island + banner from v2 preserved."
```

---

## Task 21: Emit the hero section with world name

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` — new `_render_hero(theme, lore_data)` helper called inside both `assemble_*` functions.
- Modify: `assemble_lore_page` and `assemble_rules_page` to load `lore.yaml` (lore page: world-level; rules page: pack-level) and pass it into the hero.
- Test: `sidequest-server/tests/server/test_reference_renderer_hero.py` (new)

The hero block from the bundle (see `app.jsx` `Hero` component, lines 100-180):

```html
<header class="hero">
  <div class="hero-eyebrow">
    <span class="glyph">{dinkus_medium}</span>
    <span class="eyebrow gilt">SideQuest · {pack_label} · World Reference</span>
    <span class="rule"></span>
  </div>
  <div class="hero-kicker">{first sentence of world.description}</div>
  <h1 class="hero-title">{world.name or pack_label}</h1>
  <div class="hero-sub">{pack_label} · Lore &amp; Rules</div>
  <div class="hero-epigraph narrative-flourish">{pack_epigraph_body}<span class="attrib">{attrib}</span></div>
</header>
```

For the rules page (no world), `world.name` defaults to the pack's display label; `kicker` defaults to the pack's blurb. World names live in `worlds/<world>/lore.yaml` under `world.name` (per the bundle's `Hero` reading `lore?.world?.name`); the loader (Task 18 extension) returns it.

- [ ] **Step 1: Extend the theme loader to optionally read `lore.yaml`**

Modify `reference_theme.py` to add `load_reference_lore(world_dir: Path) -> dict`. Loud on missing file (no fallback): if a lore page is requested but `worlds/<world>/lore.yaml` doesn't exist, raise `MissingLoreFileError`. For rules pages, this loader is not called.

- [ ] **Step 2: Author `PACK_LABELS` + `PACK_EPIGRAPHS` from the bundle**

The bundle's `app.jsx` lines 12-67 hold the per-pack label, blurb, glyph, and epigraph. v3 ports those into a single Python constant in `reference_theme.py`:

```python
PACK_LABELS: dict[str, str] = {
    "heavy_metal": "Heavy Metal",
    "space_opera": "Space Opera",
    "victoria": "Victoria",
    "tea_and_murder": "Tea and Murder",
    "mutant_wasteland": "Mutant Wasteland",
    "caverns_and_claudes": "Caverns & Claudes",
    "neon_dystopia": "Neon Dystopia",
    "pulp_noir": "Pulp Noir",
    "road_warrior": "Road Warrior",
    "spaghetti_western": "Spaghetti Western",
    "elemental_harmony": "Elemental Harmony",
}
```

Same shape for `PACK_BLURBS` and `PACK_EPIGRAPHS` (port verbatim from `app.jsx`). An unknown pack key falls through to `(pack_key.title(), "", ...)` — but unknown packs are themselves a loud-fail upstream (the renderer never gets there), so this is dead-but-defensible.

- [ ] **Step 3: Write the failing test**

```python
def test_hero_includes_world_name(tmp_path: Path) -> None:
    # Use the Task 27 fixture pack — fixture_pack has theme.yaml + worlds/fixture_world/lore.yaml.
    html = assemble_lore_page("fixture_pack", "fixture_world", FIXTURE_PACK_DIR, FIXTURE_WORLD_DIR)
    assert '<h1 class="hero-title">Fixture World</h1>' in html
    assert 'class="hero"' in html
    assert 'class="hero-eyebrow"' in html

def test_hero_falls_back_to_pack_label_on_rules_page(tmp_path: Path) -> None:
    html = assemble_rules_page("fixture_pack", FIXTURE_PACK_DIR)
    # Rules page has no world; hero title = pack display label.
    assert '<h1 class="hero-title">Fixture Pack</h1>' in html
```

- [ ] **Step 4: Implement `_render_hero(theme, lore_data | None)` and wire**

Standard string-escape every interpolation. Use `escape()` consistently (already imported). Stat strip (the bundle's `.stat-strip` block reading from `rules.yaml` / `progression.yaml`) is **deferred to Task 22** as part of the section walk — the hero only emits eyebrow + kicker + title + sub + epigraph.

- [ ] **Step 5: Test + commit**

```bash
cd sidequest-server
uv run pytest tests/server/test_reference_renderer_hero.py -v
git commit -m "feat(reference): emit hero block with world name from lore.yaml

Lore page hero shows world.name (e.g. 'The Long Foundry') instead of
pack label. Rules page hero falls back to pack display label.
Eyebrow, kicker, title, sub, epigraph all match bundle markup."
```

---

## Task 22: Emit the contents rail (TOC) + layout + per-file section markup

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` — wrap the existing per-file body in `<div class="layout"><aside class="toc-sticky">…</aside><main>…</main></div>`. Each `_render_file` output gets wrapped in a `<section class="section" id="<num-id>">` with `<SectionHead>` markup.
- Modify: same — extend the `_kind_for_stem` table to include `cult` and `stratum` for lore-tier list-of-dict items (from `lore.yaml` factions).
- Inline: ~15 LOC `IntersectionObserver` snippet (from `app.jsx` `Toc` component lines 220-262) for active-section highlight.
- Test: `sidequest-server/tests/server/test_reference_renderer_toc.py` (new)

The bundle's TOC is **not toggleable** per Keith's directive ("lock in contents rail we want that"). v3 emits it on every page.

- [ ] **Step 1: Author the per-pack TOC table**

The bundle's `PACK_TOC` (in `app.jsx` lines 183-218) lists the section numbering per pack. Port into `reference_theme.py`:

```python
PACK_TOC: dict[str, list[dict[str, str]]] = {
    "heavy_metal": [
        {"num": "I",    "id": "reckoning",      "label": "The Reckoning"},
        {"num": "II",   "id": "bearing",        "label": "Bearing & Make"},
        {"num": "III",  "id": "edge",           "label": "The Edge"},
        {"num": "IV",   "id": "confrontations", "label": "Confrontations"},
        {"num": "V",    "id": "affinities",     "label": "Affinities"},
        {"num": "VI",   "id": "power-tiers",    "label": "Power Tiers"},
        {"num": "VII",  "id": "inventory",      "label": "Inventory"},
        {"num": "VIII", "id": "vocab",          "label": "Beat Vocabulary"},
    ],
    # ... rest from bundle ...
}
```

Unknown packs fall through to a **two-item default** (`[{"num": "I", "id": "reckoning", "label": "The World"}, {"num": "II", "id": "bearing", "label": "Bearing & Make"}]`) AND an ERROR span `sidequest.reference.toc_missing` so the GM panel surfaces the gap. (Not silent — surfaces clearly that this pack has no TOC table yet.)

- [ ] **Step 2: Write the failing test**

```python
def test_toc_sticky_emitted(tmp_path: Path) -> None:
    html = assemble_rules_page("fixture_pack", FIXTURE_PACK_DIR)
    assert '<aside class="toc-sticky">' in html
    assert '<nav class="toc">' in html
    assert "Contents" in html

def test_toc_active_highlight_script_present(tmp_path: Path) -> None:
    html = assemble_rules_page("fixture_pack", FIXTURE_PACK_DIR)
    assert "IntersectionObserver" in html
    assert "toc-num" in html

def test_layout_wraps_main(tmp_path: Path) -> None:
    html = assemble_rules_page("fixture_pack", FIXTURE_PACK_DIR)
    # Hero outside layout, TOC + main inside.
    assert '<div class="layout">' in html
    assert '<main>' in html
```

- [ ] **Step 3: Implement the rail + layout wrap + inline observer**

Inline observer script (port from `app.jsx` `Toc.useEffect`):

```python
_TOC_OBSERVER_SCRIPT = """
<script>
(function(){
  var ids=Array.from(document.querySelectorAll('aside.toc-sticky nav.toc a')).map(function(a){return a.getAttribute('href').slice(1);});
  var sections=ids.map(function(id){return document.getElementById(id);}).filter(Boolean);
  var links={};
  document.querySelectorAll('aside.toc-sticky nav.toc a').forEach(function(a){links[a.getAttribute('href').slice(1)]=a;});
  if(!sections.length)return;
  var obs=new IntersectionObserver(function(entries){
    var visible=entries.filter(function(e){return e.isIntersecting;}).sort(function(a,b){return a.boundingClientRect.top-b.boundingClientRect.top;});
    if(visible[0]){
      Object.values(links).forEach(function(a){a.classList.remove('active');});
      var top=visible[0].target.id;
      if(links[top])links[top].classList.add('active');
    }
  },{rootMargin:'-20% 0% -60% 0%',threshold:0});
  sections.forEach(function(s){obs.observe(s);});
})();
</script>
"""
```

This is the **second inline script** on the page (the first is the bad-anchor banner from v2). Both are minimal, no framework. No other inline JS is permitted.

- [ ] **Step 4: Extend `_kind_for_stem` for lore items**

```python
_KIND_OVERRIDES: dict[str, str] = {
    # ... existing v2 entries ...
    "factions": "cult",       # NEW — lore.yaml.factions
    # 'stratum' is derived inline (factions filtered by name suffix per the bundle's Lore component);
    # _kind_for_stem stays clean — the section emitter handles the split.
}
```

- [ ] **Step 5: Test + commit**

```bash
cd sidequest-server
uv run pytest tests/server/test_reference_renderer_toc.py tests/server/test_reference_renderer_namespacing.py -v
git commit -m "feat(reference): emit contents rail + IntersectionObserver

Per-pack TOC table from the bundle; ~15-line vanilla-JS observer
highlights the active section. Layout wraps hero outside; TOC +
main inside (matches bundle DOM)."
```

---

## Task 23: Live-pack validator — `python -m sidequest.cli.validate reference-chrome`

**Files:**
- Create: `sidequest-server/sidequest/cli/validate/reference_chrome.py`
- Modify: `sidequest-server/sidequest/cli/validate/__main__.py` — register new subcommand next to `locations` / `audio` / `projection-check`.
- Test: `sidequest-server/tests/cli/test_validate_reference_chrome.py` (new) — fixture-driven only, never reads `genre_packs/*`.

Per the no-content-coupled-tests rule, every "Heavy Metal renders correctly" claim is the **validator's** job, not pytest's. The validator walks one pack's `theme.yaml` (or all live packs) and reports missing chrome fields with a non-zero exit code and a loud `[FAIL]` line per gap.

- [ ] **Step 1: Failing test**

```python
"""Reference-chrome validator: fixture-driven, fail-loud."""
from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from sidequest.cli.validate.reference_chrome import main


def _pack(tmp_path: Path, name: str, theme: dict) -> Path:
    p = tmp_path / name
    p.mkdir()
    (p / "theme.yaml").write_text(yaml.safe_dump(theme))
    return p


def test_passes_when_all_chrome_fields_present(tmp_path: Path) -> None:
    pack = _pack(tmp_path, "good", {
        "archetype": "rugged",
        "web_font_family": "IM Fell English",
        "display_font_family": "Pirata One",
        "primary": "#8B0000", "accent": "#B8860B", "background": "#0F0A0A",
        "dinkus": {"glyph": {"light": "†", "medium": "✠", "heavy": "⸸"}},
    })
    result = CliRunner().invoke(main, [str(pack)])
    assert result.exit_code == 0, result.output


def test_fails_loudly_on_missing_display_font(tmp_path: Path) -> None:
    pack = _pack(tmp_path, "bad", {
        "archetype": "rugged",
        "web_font_family": "x",
        # display_font_family missing
        "primary": "#000", "accent": "#000", "background": "#000",
        "dinkus": {"glyph": {"light": "†", "medium": "✠", "heavy": "⸸"}},
    })
    result = CliRunner().invoke(main, [str(pack)])
    assert result.exit_code != 0
    assert "display_font_family" in result.output
    assert "[FAIL]" in result.output
```

- [ ] **Step 2: Implement the click command**

```python
# sidequest-server/sidequest/cli/validate/reference_chrome.py
from __future__ import annotations
from pathlib import Path
import click
from sidequest.server.reference_theme import load_reference_theme, MissingThemeFieldError


@click.command(name="reference-chrome")
@click.argument("pack_dir", type=click.Path(exists=True, file_okay=False))
def main(pack_dir: str) -> None:
    """Validate that <pack_dir>/theme.yaml carries every field the reference renderer requires."""
    pack_path = Path(pack_dir)
    pack_name = pack_path.name
    try:
        theme = load_reference_theme(pack=pack_name, pack_dir=pack_path)
    except MissingThemeFieldError as exc:
        click.echo(f"[FAIL] {pack_name}: {exc}", err=True)
        raise SystemExit(1)
    click.echo(f"[OK]   {pack_name}: theme={theme.archetype}/{theme.display_font_family}")
```

Register in `__main__.py`:

```python
from sidequest.cli.validate.reference_chrome import main as reference_chrome_main
cli.add_command(reference_chrome_main, name="reference-chrome")
```

- [ ] **Step 3: Add `just content-validate` recipe (orchestrator)**

```bash
# justfile
content-validate:
    for d in sidequest-content/genre_packs/*/ ; do \
        uv run --project sidequest-server python -m sidequest.cli.validate reference-chrome "$$d" || exit 1; \
    done
```

- [ ] **Step 4: Test + commit**

```bash
cd sidequest-server
uv run pytest tests/cli/test_validate_reference_chrome.py -v
git commit -m "feat(validate): reference-chrome subcommand

Walks a pack's theme.yaml and asserts every field the v3 reference
renderer reads. Fail-loud with [FAIL] line + non-zero exit. Lives
in the existing validate click group next to locations/audio."
```

---

## Task 24: Explicit exclusion of `tropes.yaml` + `seed_tropes.yaml` from rendering

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` — wherever `RENDERED_FILES` / the file walker decides what to render, add `tropes.yaml`, `seed_tropes.yaml` to the exclusion alongside `npcs.yaml`.
- Test: `sidequest-server/tests/server/test_reference_renderer.py` — add a regression assertion that a fixture pack with `tropes.yaml` does NOT include trope content in the rendered HTML.

Per the bundle's chat transcript ("Tropes section removed — keeper-side only") and Keith's table-talk principle (GM panel = dev tool, players don't see keeper artifacts), tropes are excluded from the player-facing reference page.

- [ ] **Step 1: Read the current exclusion list**

```bash
cd sidequest-server && grep -n "npcs\|RENDERED_FILES\|EXCLUDED\|skip" sidequest/server/reference_renderer.py | head -10
```

- [ ] **Step 2: Add the regression test**

```python
def test_tropes_yaml_excluded(tmp_path: Path) -> None:
    pack_dir = tmp_path / "fixture_pack"
    pack_dir.mkdir()
    (pack_dir / "tropes.yaml").write_text(yaml.safe_dump({"tropes": [{"name": "Keeper Only Trope"}]}))
    # Plus the minimum theme.yaml so assemble_rules_page doesn't fail upstream.
    _write_min_theme(pack_dir)
    html = assemble_rules_page("fixture_pack", pack_dir)
    assert "Keeper Only Trope" not in html
    assert "tropes" not in html.lower()  # No section heading either.
```

- [ ] **Step 3: Implement + commit**

```bash
cd sidequest-server
git commit -m "fix(reference): exclude tropes.yaml from rendered pages

Tropes are keeper-side per the design bundle; players never see them
on /reference/{rules,lore}. Joins npcs.yaml in the explicit exclusion
list. Loud — the exclusion is a named set, not a silent skip."
```

---

## Task 25: Stage screenshots to R2, replace local dir with pointer

**Files:**
- Move: `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/*.png` → R2 at `cdn.slabgorb.com/design-bundles/2026-05-23-lore-and-rules/screenshots/`.
- Create: `docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/README.md` with the R2 URL pattern.
- Delete (after upload): the local PNG files.

Per Keith's "images go to R2, not LFS" memory rule. The screenshots are reference material, not source code — they belong in object storage.

- [ ] **Step 1: Audit current dir**

```bash
ls -lh docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/ | head
du -sh docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/
```

- [ ] **Step 2: Upload to R2** (use whatever R2 CLI / `wrangler` / `rclone` Keith uses — same path he uses for genre-pack portraits).

```bash
# Example — adapt to actual tool
rclone copy docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/ \
    r2:slabgorb-cdn/design-bundles/2026-05-23-lore-and-rules/screenshots/
```

- [ ] **Step 3: Write the pointer README**

```markdown
# Screenshots — moved to R2

The 1.3 MB of PNG references that lived here at design-handoff time were uploaded to R2 on 2026-05-24 per the project's "images go to R2, not LFS" convention.

Browse: `https://cdn.slabgorb.com/design-bundles/2026-05-23-lore-and-rules/screenshots/`

Naming follows the original bundle: `{NN}-{world-tag}.png`. See `chats/chat1.md` (final assistant message) for the per-page mapping.
```

- [ ] **Step 4: Remove local PNGs + commit**

```bash
rm docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/*.png
git add docs/design-bundles/2026-05-23-lore-and-rules/project/screenshots/README.md
git commit -m "chore(docs): move design-bundle screenshots to R2

1.3 MB of reference PNGs out of the docs tree; pointer README left
in place. Keith's 'images go to R2, not LFS' rule. HTML / CSS / JSX
/ chat transcripts stay — those are the actual design intent."
```

---

## Task 26: Extend Task 15's fixture pack with `theme.yaml` + `lore.yaml`

**Files:**
- Modify: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/theme.yaml` (new)
- Modify: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/lore.yaml` (new — pack-level)
- Modify: `sidequest-server/tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/lore.yaml` (new — world-level)

This is an in-place extension. The Task 15 fixture (`classes.yaml`, `cultures.yaml`, `worlds/fixture_world/{world,legends,locations}.yaml`) keeps its existing files; v3 chrome tests (Tasks 18, 21–24) read these additions.

```yaml
# tests/fixtures/genre_packs/fixture_pack/theme.yaml
archetype: rugged
web_font_family: IM Fell English
display_font_family: Pirata One
primary:    "#8B0000"
secondary:  "#2A1A1A"
accent:     "#B8860B"
background: "#0F0A0A"
surface:    "#1C1414"
text:       "#E8DFC8"
dinkus:
  enabled: true
  glyph:
    light:  "†"
    medium: "✠"
    heavy:  "⸸  ☥  ⸸"
```

```yaml
# tests/fixtures/genre_packs/fixture_pack/lore.yaml  (pack-level)
pack_description: A small fixture pack for renderer tests. Not a real genre.
history:
  - Once upon a time, the test world was authored just enough to satisfy the chrome.
cosmology:
  - The cosmos here exists only to populate a pull-quote.
factions:
  - name: The Test Cult
    summary: A test faction.
    description: This faction exists to verify the lore section emits cult cards.
    disposition: wary
```

```yaml
# tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/lore.yaml
world:
  name: Fixture World
  description: A small test world. Exists so the hero shows a world name.
  history:
    - The first sentence of world history. Two sentences here for the drop-cap test.
  factions:
    - name: The Vicarage Council
      summary: World-tier faction.
      description: Verifies world-tier factions render alongside pack-tier ones.
      disposition: cautious
```

- [ ] Add the three YAML files. No test file change required — Tasks 18, 21–24 reference these paths via the fixture root constant.
- [ ] Commit:

```bash
cd sidequest-server
git add tests/fixtures/genre_packs/fixture_pack/theme.yaml tests/fixtures/genre_packs/fixture_pack/lore.yaml tests/fixtures/genre_packs/fixture_pack/worlds/fixture_world/lore.yaml
git commit -m "test(reference): extend fixture pack with theme + lore yaml

In-place extension of the Task 15 fixture so Tasks 18, 21-24 can
test the chrome end-to-end without touching live genre_packs/.
Single fixture pack — no test surface fragmentation."
```

---

## Task 27: Full chrome-aware gate (replaces Task 17)

- [ ] **Step 1: Server**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest -v
```

- [ ] **Step 2: UI**

```bash
cd sidequest-ui && npx tsc --noEmit && npx eslint src && npx vitest run
```

- [ ] **Step 3: Live content validator**

```bash
cd /Users/slabgorb/Projects/oq-1 && just content-validate
```

If any pack lacks `display_font_family` or another required field, this fails. Fix the content edit (Task 19) before proceeding.

- [ ] **Step 4: Aggregate gate**

```bash
cd /Users/slabgorb/Projects/oq-1 && just check-all
```

- [ ] **Step 5: Manual smoke**

```bash
cd /Users/slabgorb/Projects/oq-1 && just up
```

Then in a browser:

1. **Lobby surface (v2 AC5)** — same as the original Task 17 step 1. ConnectScreen disabled-state flows.
2. **Hero shows world name** — open `/reference/lore/heavy_metal/long_foundry`. The hero `<h1>` shows "The Long Foundry", NOT "Heavy Metal" or "heavy_metal". On `/reference/rules/heavy_metal` (no world), the hero shows "Heavy Metal".
3. **Per-pack chrome swap** — open `/reference/rules/heavy_metal` and then `/reference/rules/space_opera`. The two pages must look visibly different: heavy_metal = iron-red/brass on void-black with Pirata One title and IM Fell English body; space_opera = console blue/holo amber on near-black with Orbitron title and Rajdhani body.
4. **Contents rail** — scroll the lore page; the TOC on the left sticks; the active item highlights as each section enters view; clicking a TOC link scrolls smoothly to the section.
5. **Dinkus glyphs** — the three weights `† / ✠ / ⸸ ☥ ⸸` render between sections on heavy_metal (Noto Sans Symbols 2 must load for the heavy glyph to show).
6. **No tropes** — `/reference/rules/heavy_metal` does not show a "Tropes" heading or any trope content. (View page source; grep for "trope".)
7. **Bad-anchor banner (v2 AC7)** — manually edit URL to `…#class-this-does-not-exist`; reload; banner appears.
8. **Validator catches missing field** — temporarily delete `display_font_family` from `sidequest-content/genre_packs/heavy_metal/theme.yaml`. Run `just content-validate`. Expect `[FAIL]` line naming the pack and field, exit code != 0. Restore the line.
9. **OTEL** — check GM panel. `sidequest.reference.url_attached`, `url_skipped`, `theme_missing` (if step 8 ran while a route was hit), `toc_missing` (only if an unknown pack was requested) — at least the first two must appear.

If any of these fails, stop, file the bug, do not merge.

- [ ] **Step 6: Push branches and open PRs**

For each subrepo (`sidequest-server`, `sidequest-ui`, `sidequest-content`):

```bash
git push -u origin feat/reference-v3
# Open PR targeting `develop`, NOT main.
```

For the orchestrator (plan + spec doc), the v3 plan was already committed to `main` upstream of execution; no extra PR needed there.

---

## Self-Review

(Performed by the plan author against the v2 spec + the v3 amendment.)

**v2 spec coverage:**

| Spec AC | Plan task(s) |
|---|---|
| AC1 (Character sheet ability hyperlinks) | Tasks 6, 10, 12 |
| AC2 (Class + archetype hyperlinks) | Tasks 7, 10, 12 |
| AC3 (KnowledgeJournal hyperlinks) | Tasks 8, 10, 13 |
| AC4 (LocationPanel hyperlinks) | Tasks 9, 10, 14 |
| AC5 (ConnectScreen lobby buttons) | Task 11 |
| AC6 (no WebSocket message on click) | Tests in 11, 12, 13, 14 |
| AC7 (bad-anchor banner) | Task 4 |
| AC8 (shared slug helper, no duplicate) | Task 1 |
| AC8a (namespaced anchor ids, collision case) | Tasks 2, 15 |
| AC9 (OTEL spans) | Task 5 + attach call sites in 6, 7, 8, 9 |
| AC10 (`just check-all` passes) | Task 27 (replaces Task 17) |

**v3 chrome scope coverage:**

| v3 deliverable | Plan task(s) |
|---|---|
| Per-pack palette + font + dinkus from `theme.yaml` | Tasks 18, 19, 20 |
| `display_font_family` added to schema | Task 19 |
| Static CSS route serving bundled theme.css + styles.css | Task 20 |
| Hero shows world name from `lore.yaml` | Task 21 |
| Contents rail (TOC) — locked, not toggleable | Task 22 |
| Lore section emitted from `lore.yaml` | Task 21 (loader) + Task 22 (section walk) |
| Tropes section removed | Task 24 |
| Dinkus glyphs from pack | Tasks 18, 22 |
| Noto Sans Symbols 2 font stack | Shipped in bundled `theme.css` (Task 20) |
| Live-pack chrome validator | Task 23 |
| Fixture pack extended for chrome tests | Task 26 |
| Screenshots staged to R2 | Task 25 |
| OTEL coverage for new chrome subsystems | Spans in Tasks 18 (`theme_missing`), 22 (`toc_missing`); v2's `url_*` spans unchanged |
| No content-coupled tests | Enforced by Task 23's validator + Task 26's fixture |

All v2 ACs + all v3 deliverables covered.

All ten ACs covered. Spec routing-table kinds (class, signature, archetype,
culture, legend, location, history) all have tests in Task 3.

**Placeholder scan:** No "TBD" / "TODO" / "implement later" remain. Steps
that say "use the existing test harness as a template" are concrete
pointers, not placeholders — the implementer is told which file to mirror.

**Type consistency:** `reference_url: str | None = None` is consistent
across `AbilityDefinition`, `PartyMember.class_reference_url`,
`JournalEntry`, `LocationEntity`. Helper names match between the source
module (Task 3) and the call sites that import them (Tasks 6-9).
`_kind_for_stem` is defined in Task 2 and referenced nowhere else
(internal to the renderer). `slugify` is defined in Task 1 and imported by
the renderer (Task 1, 2) and the URL builders (Task 3).

**Risk notes:**

- Task 5's OTEL test uses a placeholder `captured_spans` import; the
  implementer must substitute the project's actual in-memory exporter
  helper before authoring. Step 1 of Task 5 instructs them to grep for
  it first.
- Tasks 6-9 each include a "locate construction site" step that the
  implementer must complete before authoring the attach code. Construction
  sites for protocol objects vary by handler and are not statically known
  from the spec — the grep is mandatory.
- The integration test in Task 15 assumes a `create_app()` factory or
  equivalent; the implementer adapts to the project's actual app
  initialiser.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-23-reference-pages-v2.md`. Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. The grep-first construction-site discovery in Tasks 6-9 fits this model well.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
