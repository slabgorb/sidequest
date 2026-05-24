# Reference Pages v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire structured-panel hyperlinks (CharacterSheet abilities + class, KnowledgeJournal entries, LocationPanel locations) and a lobby reference surface into the v1 reference pages, with a bad-anchor banner for loud failure.

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

## Task 17: Run the full gate

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

## Self-Review

(Performed by the plan author against the spec.)

**Spec coverage:**

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
| AC10 (`just check-all` passes) | Task 17 |

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
