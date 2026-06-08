# Reference Pages (Rules & Lore) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two server-rendered HTML reference pages (`/reference/rules/<pack>`, `/reference/lore/<pack>/<world>`) that read YAML on disk and render hypertext docs, plus two anchor links in the narrative panel that open them in a new tab.

**Architecture:** FastAPI route reads pack YAML on each request, walks the parsed tree with a recursive renderer, emits a self-contained HTML document with a default stylesheet. The React UI just adds `<a target="_blank">` links — no state, no JSON layer. See `docs/superpowers/specs/2026-05-23-reference-pages-design.md` for full design.

**Tech Stack:** Python 3 / FastAPI / PyYAML (server); React / TypeScript / vitest (UI).

---

## File Structure

**Created:**
- `sidequest-server/sidequest/server/reference_renderer.py` — YAML→HTML walker
- `sidequest-server/sidequest/server/reference_routes.py` — FastAPI router
- `sidequest-server/sidequest/server/static/reference.css` — default stylesheet
- `sidequest-server/tests/server/test_reference_renderer.py` — walker unit tests
- `sidequest-server/tests/server/test_reference_routes.py` — route unit + integration tests
- `sidequest-ui/src/components/ReferenceLinks.tsx` — two anchor links
- `sidequest-ui/src/components/__tests__/ReferenceLinks.test.tsx`

**Modified:**
- `sidequest-server/sidequest/server/app.py` — register `reference_router` and mount static
- `sidequest-ui/src/components/GameBoard/widgets/NarrativeWidget.tsx` — render `<ReferenceLinks>` above `<NarrativeView>`, accept `worldSlug` prop
- `sidequest-ui/src/components/GameBoard/GameBoard.tsx` — thread `worldSlug` into `NarrativeWidget`

The renderer and route modules are intentionally separate: the renderer is a pure function tree (easy to unit-test), the route module is the HTTP boundary (handles 404/500 and registry lookups).

---

## Conventions

**Test runs:** Use `uv run pytest ...` from `sidequest-server/`, and `npx vitest run ...` from `sidequest-ui/`. (CLAUDE.md doctrine: `just server-test` etc. for the full sweep; per-test commands are fine during TDD inner loop.)

**Commits:** One commit per task at minimum. Include `Co-Authored-By` per repo convention. Conventional-commit prefixes (`feat:`, `test:`, `chore:`).

**Branch:** Work happens on a feature branch per repo. Orchestrator targets `main`; subrepos target `develop`. See `.pennyfarthing/repos.yaml`.

---

### Task 1: Slug helper + walker scalar/dict case

**Files:**
- Create: `sidequest-server/sidequest/server/reference_renderer.py`
- Create: `sidequest-server/tests/server/test_reference_renderer.py`

- [ ] **Step 1: Write the failing test**

`sidequest-server/tests/server/test_reference_renderer.py`:

```python
"""Unit tests for the reference-page YAML→HTML walker.

Renderer must produce stable, escaped HTML from arbitrary YAML trees. The walker
is pure (input dict/list/scalar → output str); no IO, no globals.
"""
from sidequest.server.reference_renderer import render_node, slugify


def test_slugify_lowercases_and_hyphenates():
    assert slugify("Amateur Sleuth") == "amateur-sleuth"


def test_slugify_strips_non_ascii():
    assert slugify("Café Crème") == "caf-cr-me"


def test_slugify_collapses_runs_of_separators():
    assert slugify("a // b -- c") == "a-b-c"


def test_render_scalar_string_escapes_html():
    assert render_node("Hello <world>") == "<p>Hello &lt;world&gt;</p>"


def test_render_scalar_int():
    assert render_node(42) == "<p>42</p>"


def test_render_scalar_multiline_uses_pre_wrap():
    html = render_node("line1\nline2\nline3")
    assert 'class="multiline"' in html
    assert "line1\nline2\nline3" in html


def test_render_flat_dict_emits_section_per_key():
    html = render_node({"name": "Sleuth", "tier": "novice"})
    assert '<section id="name">' in html
    assert "<h2>name</h2>" in html
    assert "<p>Sleuth</p>" in html
    assert '<section id="tier">' in html
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: `ModuleNotFoundError: sidequest.server.reference_renderer` or `ImportError`.

- [ ] **Step 3: Write minimal implementation**

`sidequest-server/sidequest/server/reference_renderer.py`:

```python
"""Render parsed-YAML trees as a hypertext document.

Pure functions only. The HTTP boundary (404 / 500 / file IO) lives in
reference_routes.py. This module just walks dict/list/scalar trees and produces
HTML fragments.

Headings get stable slugified ``id`` attributes so future deep-link work can
target them without schema changes.
"""
from __future__ import annotations

import re
from html import escape

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase ASCII slug. Non-ASCII chars become separators; runs collapse."""
    lowered = text.lower()
    return _SLUG_RE.sub("-", lowered).strip("-")


def render_node(node: object) -> str:
    """Render a parsed-YAML node to an HTML fragment.

    Handles: dict, list (later tasks), scalar (str/int/float/bool/None).
    """
    if isinstance(node, dict):
        return _render_dict(node)
    return _render_scalar(node)


def _render_scalar(value: object) -> str:
    if value is None:
        return "<p><em>(none)</em></p>"
    text = str(value)
    if "\n" in text:
        return f'<p class="multiline">{escape(text)}</p>'
    return f"<p>{escape(text)}</p>"


def _render_dict(node: dict) -> str:
    parts: list[str] = []
    for key, value in node.items():
        slug = slugify(str(key))
        parts.append(f'<section id="{slug}">')
        parts.append(f"<h2>{escape(str(key))}</h2>")
        parts.append(render_node(value))
        parts.append("</section>")
    return "".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/reference_renderer.py \
        sidequest-server/tests/server/test_reference_renderer.py
git commit -m "feat(reference): YAML walker — slug, scalars, flat dicts"
```

---

### Task 2: Walker — lists of dicts and lists of scalars

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py`
- Modify: `sidequest-server/tests/server/test_reference_renderer.py`

- [ ] **Step 1: Write the failing tests** (append to existing test file)

```python
def test_render_list_of_scalars_emits_ul():
    html = render_node(["alpha", "beta", "gamma"])
    assert "<ul>" in html
    assert "<li>alpha</li>" in html
    assert "<li>beta</li>" in html
    assert "<li>gamma</li>" in html
    assert "</ul>" in html


def test_render_list_of_dicts_with_name_uses_h3_anchor():
    html = render_node([
        {"name": "Sleuth", "description": "Investigates."},
        {"name": "Detective", "description": "Investigates harder."},
    ])
    assert '<section id="sleuth">' in html
    assert "<h3>Sleuth</h3>" in html
    assert '<section id="detective">' in html


def test_render_list_of_dicts_falls_through_id_title_then_index():
    html = render_node([
        {"id": "tier-1", "value": "low"},
        {"title": "Tier Two", "value": "mid"},
        {"value": "high"},
    ])
    assert '<section id="tier-1">' in html
    assert "<h3>tier-1</h3>" in html
    assert '<section id="tier-two">' in html
    assert "<h3>Tier Two</h3>" in html
    assert '<section id="item-3">' in html
    assert "<h3>Item 3</h3>" in html


def test_render_nested_dict_inside_list_recurses():
    html = render_node([{"name": "A", "stats": {"hp": 5, "atk": 2}}])
    assert "<h3>A</h3>" in html
    assert "<h2>stats</h2>" in html
    assert "<p>5</p>" in html
    assert "<p>2</p>" in html


def test_render_empty_list_emits_em_placeholder():
    assert render_node([]) == "<p><em>(empty)</em></p>"


def test_render_empty_dict_emits_em_placeholder():
    assert render_node({}) == "<p><em>(empty)</em></p>"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 6 PASS (from Task 1), 6 FAIL (new list/empty tests).

- [ ] **Step 3: Extend the implementation**

In `reference_renderer.py`, replace `render_node` and add `_render_list`:

```python
def render_node(node: object) -> str:
    if isinstance(node, dict):
        return _render_dict(node) if node else "<p><em>(empty)</em></p>"
    if isinstance(node, list):
        return _render_list(node) if node else "<p><em>(empty)</em></p>"
    return _render_scalar(node)


_NAME_FIELDS = ("name", "id", "title")


def _heading_for_item(item: dict, index: int) -> tuple[str, str]:
    """Return (slug, display) for a list-of-dict item heading."""
    for field in _NAME_FIELDS:
        if field in item and item[field] is not None:
            value = str(item[field])
            return slugify(value), value
    fallback = f"Item {index + 1}"
    return slugify(fallback), fallback


def _render_list(items: list) -> str:
    if all(not isinstance(item, (dict, list)) for item in items):
        lis = "".join(f"<li>{escape(str(item))}</li>" for item in items)
        return f"<ul>{lis}</ul>"
    parts: list[str] = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            slug, display = _heading_for_item(item, index)
            parts.append(f'<section id="{slug}">')
            parts.append(f"<h3>{escape(display)}</h3>")
            parts.append(render_node(item))
            parts.append("</section>")
        else:
            parts.append(render_node(item))
    return "".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 12 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/reference_renderer.py \
        sidequest-server/tests/server/test_reference_renderer.py
git commit -m "feat(reference): walker handles lists of dicts and scalars"
```

---

### Task 3: Walker — depth cap with `<pre>` fallback

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py`
- Modify: `sidequest-server/tests/server/test_reference_renderer.py`

- [ ] **Step 1: Write the failing tests**

```python
import yaml as _yaml


def test_render_at_depth_cap_falls_back_to_pre():
    # Build a 7-deep nested dict, one level past the cap (6).
    deep = {"k": "leaf"}
    for _ in range(7):
        deep = {"k": deep}
    html = render_node(deep)
    assert "<pre>" in html
    assert "</pre>" in html


def test_pre_fallback_contains_yaml_redump():
    deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "leaf"}}}}}}}
    html = render_node(deep)
    # The yaml redump should appear inside the <pre> for the deepest sub-tree
    assert "leaf" in html


def test_below_depth_cap_renders_normally():
    nested = {"a": {"b": {"c": "deep_enough"}}}
    html = render_node(nested)
    assert "<pre>" not in html
    assert "<p>deep_enough</p>" in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 12 PASS, 3 FAIL.

- [ ] **Step 3: Extend the implementation**

Update `reference_renderer.py`:

```python
import yaml

_DEPTH_CAP = 6


def render_node(node: object, depth: int = 0) -> str:
    if depth >= _DEPTH_CAP and isinstance(node, (dict, list)) and node:
        dumped = yaml.safe_dump(node, sort_keys=False, default_flow_style=False)
        return f"<pre>{escape(dumped)}</pre>"
    if isinstance(node, dict):
        return _render_dict(node, depth) if node else "<p><em>(empty)</em></p>"
    if isinstance(node, list):
        return _render_list(node, depth) if node else "<p><em>(empty)</em></p>"
    return _render_scalar(node)


def _render_dict(node: dict, depth: int) -> str:
    parts: list[str] = []
    for key, value in node.items():
        slug = slugify(str(key))
        parts.append(f'<section id="{slug}">')
        parts.append(f"<h2>{escape(str(key))}</h2>")
        parts.append(render_node(value, depth + 1))
        parts.append("</section>")
    return "".join(parts)


def _render_list(items: list, depth: int) -> str:
    if all(not isinstance(item, (dict, list)) for item in items):
        lis = "".join(f"<li>{escape(str(item))}</li>" for item in items)
        return f"<ul>{lis}</ul>"
    parts: list[str] = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            slug, display = _heading_for_item(item, index)
            parts.append(f'<section id="{slug}">')
            parts.append(f"<h3>{escape(display)}</h3>")
            parts.append(render_node(item, depth + 1))
            parts.append("</section>")
        else:
            parts.append(render_node(item, depth + 1))
    return "".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 15 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/reference_renderer.py \
        sidequest-server/tests/server/test_reference_renderer.py
git commit -m "feat(reference): depth cap with yaml-redump fallback"
```

---

### Task 4: File mapping constants

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py`
- Modify: `sidequest-server/tests/server/test_reference_renderer.py`

- [ ] **Step 1: Write the failing tests**

```python
from sidequest.server.reference_renderer import (
    RULES_FILES,
    LORE_WORLD_FILES,
    LORE_PACK_FLAVOR_FILES,
    EXCLUDED_FILES,
)


def test_rules_files_in_documented_order():
    assert RULES_FILES == (
        "archetypes.yaml",
        "classes.yaml",
        "rules.yaml",
        "progression.yaml",
        "magic.yaml",
        "power_tiers.yaml",
        "achievements.yaml",
        "tropes.yaml",
        "equipment_tables.yaml",
        "inventory.yaml",
        "beat_vocabulary.yaml",
    )


def test_lore_world_files_in_documented_order():
    assert LORE_WORLD_FILES == (
        "world.yaml",
        "cultures.yaml",
        "history.yaml",
        "calendar.yaml",
        "demographics.yaml",
        "legends.yaml",
        "openings.yaml",
        "lore.yaml",
    )


def test_lore_pack_flavor_files_in_documented_order():
    assert LORE_PACK_FLAVOR_FILES == (
        "cultures.yaml",
        "lore.yaml",
        "history.yaml",
    )


def test_npcs_and_seed_tropes_are_excluded():
    assert "npcs.yaml" in EXCLUDED_FILES
    assert "seed_tropes.yaml" in EXCLUDED_FILES
    assert "prompts.yaml" in EXCLUDED_FILES


def test_no_overlap_between_included_and_excluded():
    included = set(RULES_FILES) | set(LORE_WORLD_FILES) | set(LORE_PACK_FLAVOR_FILES)
    overlap = included & EXCLUDED_FILES
    assert overlap == set(), f"file appears in both included and excluded: {overlap}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 15 PASS, 5 FAIL (`ImportError` on the constants).

- [ ] **Step 3: Add the constants to `reference_renderer.py`**

```python
# File-to-page mapping (see spec: 2026-05-23-reference-pages-design.md §File-to-Page Mapping)
RULES_FILES: tuple[str, ...] = (
    "archetypes.yaml",
    "classes.yaml",
    "rules.yaml",
    "progression.yaml",
    "magic.yaml",
    "power_tiers.yaml",
    "achievements.yaml",
    "tropes.yaml",
    "equipment_tables.yaml",
    "inventory.yaml",
    "beat_vocabulary.yaml",
)

LORE_WORLD_FILES: tuple[str, ...] = (
    "world.yaml",
    "cultures.yaml",
    "history.yaml",
    "calendar.yaml",
    "demographics.yaml",
    "legends.yaml",
    "openings.yaml",
    "lore.yaml",
)

LORE_PACK_FLAVOR_FILES: tuple[str, ...] = (
    "cultures.yaml",
    "lore.yaml",
    "history.yaml",
)

EXCLUDED_FILES: frozenset[str] = frozenset({
    # Spoiler-bearing — see iteration 2 of the spec
    "npcs.yaml",
    "seed_tropes.yaml",
    # System-tier / metadata / asset config (not player-facing content)
    "prompts.yaml",
    "pack.yaml",
    "theme.yaml",
    "visual_style.yaml",
    "audio.yaml",
    "portrait_manifest.yaml",
    "cartography.yaml",
    "axes.yaml",
    "lethality_policy.yaml",
    "visibility_baseline.yaml",
    "char_creation.yaml",
})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 20 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/reference_renderer.py \
        sidequest-server/tests/server/test_reference_renderer.py
git commit -m "feat(reference): file-to-page mapping constants"
```

---

### Task 5: Page assembler — load files into a single HTML doc

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py`
- Modify: `sidequest-server/tests/server/test_reference_renderer.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

import pytest


def _write_pack(tmp_path: Path, pack: str, files: dict[str, str]) -> Path:
    pack_dir = tmp_path / pack
    pack_dir.mkdir(parents=True)
    for name, contents in files.items():
        (pack_dir / name).write_text(contents)
    return pack_dir


def test_assemble_rules_page_includes_listed_files_in_order(tmp_path):
    from sidequest.server.reference_renderer import assemble_rules_page

    pack_dir = _write_pack(tmp_path, "demo", {
        "archetypes.yaml": "a: 1\n",
        "classes.yaml": "b: 2\n",
        "rules.yaml": "c: 3\n",
    })
    html = assemble_rules_page("demo", pack_dir)

    assert "<title>demo — Rules</title>" in html
    # Section order matches RULES_FILES ordering
    a_pos = html.index("archetypes.yaml")
    b_pos = html.index("classes.yaml")
    c_pos = html.index("rules.yaml")
    assert a_pos < b_pos < c_pos


def test_assemble_rules_page_skips_missing_optional_files(tmp_path):
    from sidequest.server.reference_renderer import assemble_rules_page

    pack_dir = _write_pack(tmp_path, "demo", {"archetypes.yaml": "a: 1\n"})
    html = assemble_rules_page("demo", pack_dir)

    assert "archetypes.yaml" in html
    assert "magic.yaml" not in html  # silently absent


def test_assemble_rules_page_never_renders_excluded_files(tmp_path):
    from sidequest.server.reference_renderer import assemble_rules_page

    pack_dir = _write_pack(tmp_path, "demo", {
        "archetypes.yaml": "a: 1\n",
        "npcs.yaml": "secret_villain: thedoctor\n",
        "seed_tropes.yaml": "spoilers: yes\n",
    })
    html = assemble_rules_page("demo", pack_dir)

    assert "thedoctor" not in html
    assert "seed_tropes" not in html.lower()


def test_assemble_lore_page_combines_world_and_pack_flavor(tmp_path):
    from sidequest.server.reference_renderer import assemble_lore_page

    pack_dir = tmp_path / "demo"
    world_dir = pack_dir / "worlds" / "demoworld"
    world_dir.mkdir(parents=True)
    (pack_dir / "lore.yaml").write_text("pack_flavor: yes\n")
    (pack_dir / "cultures.yaml").write_text("genre_cultures: yes\n")
    (world_dir / "world.yaml").write_text("world_name: Demoworld\n")
    (world_dir / "legends.yaml").write_text("legend: a tale\n")

    html = assemble_lore_page("demo", "demoworld", pack_dir, world_dir)

    assert "<title>demo / demoworld — Lore</title>" in html
    assert "Demoworld" in html
    assert "a tale" in html
    assert "pack_flavor" in html
    assert "genre_cultures" in html
    # World tier must precede pack flavor
    assert html.index("world.yaml") < html.index("(genre)")


def test_assemble_handles_malformed_yaml_with_loud_marker(tmp_path):
    from sidequest.server.reference_renderer import assemble_rules_page

    pack_dir = _write_pack(tmp_path, "demo", {
        "archetypes.yaml": ":\n  - this is: : not valid\n",
    })
    with pytest.raises(ValueError) as exc:
        assemble_rules_page("demo", pack_dir)
    assert "archetypes.yaml" in str(exc.value)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 20 PASS, 5 FAIL.

- [ ] **Step 3: Implement assemblers**

Append to `reference_renderer.py`:

```python
from pathlib import Path

_STYLESHEET_HREF = "/reference/static/reference.css"


def _render_file(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        with path.open() as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name}: malformed YAML: {exc}") from exc
    if data is None:
        body = "<p><em>(empty file)</em></p>"
    else:
        body = render_node(data)
    file_slug = slugify(path.stem)
    return (
        f'<section class="file" id="file-{file_slug}">'
        f"<h1>{escape(path.name)}</h1>"
        f"{body}"
        "</section>"
    )


def _render_file_with_label(path: Path, label: str) -> str:
    """Like _render_file but appends a parenthetical label to the file heading."""
    rendered = _render_file(path)
    if not rendered:
        return ""
    return rendered.replace(
        f"<h1>{escape(path.name)}</h1>",
        f"<h1>{escape(path.name)} <small>{escape(label)}</small></h1>",
        1,
    )


def _wrap_document(title: str, body: str) -> str:
    return (
        "<!doctype html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        f"<title>{escape(title)}</title>"
        f'<link rel="stylesheet" href="{_STYLESHEET_HREF}">'
        "</head>"
        "<body>"
        f"<h1 class=\"doc-title\">{escape(title)}</h1>"
        f"{body}"
        "</body>"
        "</html>"
    )


def assemble_rules_page(pack: str, pack_dir: Path) -> str:
    """Build the /reference/rules/<pack> HTML document."""
    body_parts: list[str] = []
    for filename in RULES_FILES:
        if filename in EXCLUDED_FILES:
            continue
        body_parts.append(_render_file(pack_dir / filename))
    body = "".join(body_parts)
    return _wrap_document(f"{pack} — Rules", body)


def assemble_lore_page(
    pack: str, world: str, pack_dir: Path, world_dir: Path
) -> str:
    """Build the /reference/lore/<pack>/<world> HTML document."""
    body_parts: list[str] = []
    for filename in LORE_WORLD_FILES:
        if filename in EXCLUDED_FILES:
            continue
        body_parts.append(_render_file(world_dir / filename))
    for filename in LORE_PACK_FLAVOR_FILES:
        if filename in EXCLUDED_FILES:
            continue
        body_parts.append(_render_file_with_label(pack_dir / filename, "(genre)"))
    body = "".join(body_parts)
    return _wrap_document(f"{pack} / {world} — Lore", body)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_renderer.py -v
```

Expected: 25 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/reference_renderer.py \
        sidequest-server/tests/server/test_reference_renderer.py
git commit -m "feat(reference): page assemblers for rules and lore"
```

---

### Task 6: FastAPI route module + 404 handling

**Files:**
- Create: `sidequest-server/sidequest/server/reference_routes.py`
- Create: `sidequest-server/tests/server/test_reference_routes.py`

- [ ] **Step 1: Write the failing tests**

`sidequest-server/tests/server/test_reference_routes.py`:

```python
"""HTTP boundary tests for /reference/rules/* and /reference/lore/*.

These tests use a tmp-path pack so they do not depend on the live
sidequest-content tree. A separate smoke test (test_reference_smoke.py,
later) hits the live tea_and_murder pack.
"""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sidequest.server.reference_routes import create_reference_router


def _build_app(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.genre_pack_search_paths = [tmp_path]
    app.include_router(create_reference_router())
    return TestClient(app)


def _seed_pack(tmp_path: Path) -> None:
    pack = tmp_path / "demo"
    world = pack / "worlds" / "demoworld"
    world.mkdir(parents=True)
    (pack / "archetypes.yaml").write_text("kinds:\n  - sleuth\n")
    (pack / "classes.yaml").write_text("amateur_sleuth:\n  signature: deduce\n")
    (pack / "npcs.yaml").write_text("villain: thedoctor\n")  # MUST be excluded
    (world / "world.yaml").write_text("name: Demoworld\n")
    (world / "legends.yaml").write_text("legend: a tale\n")


def test_rules_route_returns_html(tmp_path):
    _seed_pack(tmp_path)
    client = _build_app(tmp_path)
    r = client.get("/reference/rules/demo")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "sleuth" in r.text
    assert "deduce" in r.text


def test_rules_route_excludes_npcs(tmp_path):
    _seed_pack(tmp_path)
    client = _build_app(tmp_path)
    r = client.get("/reference/rules/demo")
    assert "thedoctor" not in r.text


def test_lore_route_returns_html(tmp_path):
    _seed_pack(tmp_path)
    client = _build_app(tmp_path)
    r = client.get("/reference/lore/demo/demoworld")
    assert r.status_code == 200
    assert "Demoworld" in r.text
    assert "a tale" in r.text


def test_unknown_pack_returns_404_with_valid_list(tmp_path):
    _seed_pack(tmp_path)
    client = _build_app(tmp_path)
    r = client.get("/reference/rules/nonesuch")
    assert r.status_code == 404
    assert "nonesuch" in r.text
    assert "demo" in r.text  # list of valid packs


def test_unknown_world_returns_404_with_valid_world_list(tmp_path):
    _seed_pack(tmp_path)
    client = _build_app(tmp_path)
    r = client.get("/reference/lore/demo/nonesuch")
    assert r.status_code == 404
    assert "nonesuch" in r.text
    assert "demoworld" in r.text


def test_pack_id_with_path_traversal_returns_404(tmp_path):
    _seed_pack(tmp_path)
    client = _build_app(tmp_path)
    r = client.get("/reference/rules/..%2Fevil")
    assert r.status_code == 404


def test_no_search_paths_configured_returns_500(tmp_path):
    app = FastAPI()
    app.state.genre_pack_search_paths = []
    app.include_router(create_reference_router())
    client = TestClient(app)
    r = client.get("/reference/rules/demo")
    assert r.status_code == 500
    assert "search paths" in r.text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_routes.py -v
```

Expected: `ModuleNotFoundError: sidequest.server.reference_routes`.

- [ ] **Step 3: Implement the router**

`sidequest-server/sidequest/server/reference_routes.py`:

```python
"""FastAPI routes for the player-facing reference pages.

Routes:
    GET /reference/rules/{pack}            — pack-tier YAML rendered as HTML
    GET /reference/lore/{pack}/{world}     — world-tier + pack flavor as HTML

The renderer is pure (sidequest.server.reference_renderer). This module owns
the HTTP boundary: registry lookups, 404/500, response shaping.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from sidequest.server.reference_renderer import (
    assemble_lore_page,
    assemble_rules_page,
)

_LOG = logging.getLogger(__name__)
_SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _resolve_pack_dir(request: Request, pack: str) -> Path:
    """Find the on-disk dir for ``pack``, or raise 404 with valid alternatives."""
    if not _SAFE_SLUG.match(pack):
        raise HTTPException(status_code=404, detail=f"Unknown pack: {pack}")
    paths = getattr(request.app.state, "genre_pack_search_paths", None) or []
    if not paths:
        raise HTTPException(
            status_code=500,
            detail="No genre pack search paths configured on app.state.",
        )
    for root in paths:
        candidate = Path(root) / pack
        if candidate.is_dir():
            return candidate
    valid = sorted({
        entry.name
        for root in paths
        for entry in Path(root).iterdir()
        if Path(root).is_dir() and entry.is_dir() and _SAFE_SLUG.match(entry.name)
    })
    raise HTTPException(
        status_code=404,
        detail=f"Pack '{pack}' not found. Valid packs: {', '.join(valid) or '(none)'}",
    )


def _resolve_world_dir(pack_dir: Path, world: str) -> Path:
    if not _SAFE_SLUG.match(world):
        raise HTTPException(status_code=404, detail=f"Unknown world: {world}")
    candidate = pack_dir / "worlds" / world
    if candidate.is_dir():
        return candidate
    worlds_root = pack_dir / "worlds"
    valid = sorted(
        entry.name for entry in worlds_root.iterdir()
        if worlds_root.is_dir() and entry.is_dir() and _SAFE_SLUG.match(entry.name)
    ) if worlds_root.exists() else []
    raise HTTPException(
        status_code=404,
        detail=(
            f"World '{world}' not found in pack '{pack_dir.name}'. "
            f"Valid worlds: {', '.join(valid) or '(none)'}"
        ),
    )


def create_reference_router() -> APIRouter:
    router = APIRouter(prefix="/reference", tags=["reference"])

    @router.get("/rules/{pack}", response_class=HTMLResponse)
    async def rules_page(request: Request, pack: str) -> HTMLResponse:
        pack_dir = _resolve_pack_dir(request, pack)
        try:
            html = assemble_rules_page(pack, pack_dir)
        except ValueError as exc:
            _LOG.exception("reference rules page: malformed YAML in %s", pack)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return HTMLResponse(content=html)

    @router.get("/lore/{pack}/{world}", response_class=HTMLResponse)
    async def lore_page(request: Request, pack: str, world: str) -> HTMLResponse:
        pack_dir = _resolve_pack_dir(request, pack)
        world_dir = _resolve_world_dir(pack_dir, world)
        try:
            html = assemble_lore_page(pack, world, pack_dir, world_dir)
        except ValueError as exc:
            _LOG.exception("reference lore page: malformed YAML in %s/%s", pack, world)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return HTMLResponse(content=html)

    return router
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_routes.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/reference_routes.py \
        sidequest-server/tests/server/test_reference_routes.py
git commit -m "feat(reference): FastAPI routes with strict 404 + 500"
```

---

### Task 7: Default stylesheet + static mount

**Files:**
- Create: `sidequest-server/sidequest/server/static/reference.css`
- Modify: `sidequest-server/sidequest/server/reference_routes.py`
- Modify: `sidequest-server/tests/server/test_reference_routes.py`

- [ ] **Step 1: Write the failing test** (append to test file)

```python
def test_stylesheet_route_serves_css(tmp_path):
    _seed_pack(tmp_path)
    client = _build_app(tmp_path)
    r = client.get("/reference/static/reference.css")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/css")
    assert "body" in r.text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_routes.py::test_stylesheet_route_serves_css -v
```

Expected: FAIL (404 — no static route yet).

- [ ] **Step 3: Create the stylesheet**

`sidequest-server/sidequest/server/static/reference.css`:

```css
/* Default reference-page stylesheet. Iteration 2 may pull in per-pack theme. */
:root {
    --max-w: 70ch;
    --fg: #1a1a1a;
    --muted: #555;
    --rule: #ddd;
}
body {
    color: var(--fg);
    font-family: Georgia, "Times New Roman", serif;
    line-height: 1.6;
    margin: 2em auto;
    max-width: var(--max-w);
    padding: 0 1em;
}
.doc-title {
    border-bottom: 2px solid var(--rule);
    padding-bottom: 0.5em;
    margin-bottom: 1em;
}
section.file {
    border-top: 1px solid var(--rule);
    margin-top: 2em;
    padding-top: 1em;
}
section.file > h1 {
    font-size: 1.4em;
    color: var(--muted);
}
section.file > h1 small {
    font-size: 0.7em;
    color: var(--muted);
    font-weight: normal;
}
h2 {
    margin-top: 1.5em;
    font-size: 1.25em;
}
h3 {
    margin-top: 1em;
    font-size: 1.1em;
}
ul {
    padding-left: 1.5em;
}
dl {
    margin-left: 1em;
}
dt {
    font-weight: bold;
    margin-top: 0.5em;
}
dd {
    margin-left: 1em;
}
p.multiline {
    white-space: pre-wrap;
    font-family: ui-monospace, "Courier New", monospace;
    background: #f5f5f5;
    padding: 0.5em;
    border-radius: 4px;
}
pre {
    background: #f0f0f0;
    padding: 0.75em;
    overflow-x: auto;
    font-size: 0.9em;
}
```

- [ ] **Step 4: Mount the static dir in the router**

In `reference_routes.py`, replace `create_reference_router` with:

```python
from fastapi.staticfiles import StaticFiles


def create_reference_router() -> APIRouter:
    router = APIRouter(prefix="/reference", tags=["reference"])
    static_dir = Path(__file__).parent / "static"

    # StaticFiles is mounted at the prefix-relative path. We expose
    # /reference/static/* so the HTML's <link href="/reference/static/reference.css">
    # resolves correctly.
    router.mount(
        "/static",
        StaticFiles(directory=str(static_dir)),
        name="reference_static",
    )

    @router.get("/rules/{pack}", response_class=HTMLResponse)
    async def rules_page(request: Request, pack: str) -> HTMLResponse:
        pack_dir = _resolve_pack_dir(request, pack)
        try:
            html = assemble_rules_page(pack, pack_dir)
        except ValueError as exc:
            _LOG.exception("reference rules page: malformed YAML in %s", pack)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return HTMLResponse(content=html)

    @router.get("/lore/{pack}/{world}", response_class=HTMLResponse)
    async def lore_page(request: Request, pack: str, world: str) -> HTMLResponse:
        pack_dir = _resolve_pack_dir(request, pack)
        world_dir = _resolve_world_dir(pack_dir, world)
        try:
            html = assemble_lore_page(pack, world, pack_dir, world_dir)
        except ValueError as exc:
            _LOG.exception("reference lore page: malformed YAML in %s/%s", pack, world)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return HTMLResponse(content=html)

    return router
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_routes.py -v
```

Expected: 8 PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/static/reference.css \
        sidequest-server/sidequest/server/reference_routes.py \
        sidequest-server/tests/server/test_reference_routes.py
git commit -m "feat(reference): default stylesheet served from /reference/static"
```

---

### Task 8: Wire router into the FastAPI app

**Files:**
- Modify: `sidequest-server/sidequest/server/app.py` (around line 269 where other routers are registered)

- [ ] **Step 1: Write the wiring test**

Append to `sidequest-server/tests/server/test_reference_routes.py`:

```python
def test_reference_router_registered_in_real_app(monkeypatch, tmp_path):
    """Wiring test: the production app.py registers create_reference_router().

    Per CLAUDE.md doctrine — every test suite needs at least one test that
    verifies the component is reachable from production code paths.
    """
    from sidequest.server.app import create_app

    # Seed a minimal valid pack so the route returns 200.
    pack = tmp_path / "demo"
    pack.mkdir()
    (pack / "archetypes.yaml").write_text("kinds:\n  - sleuth\n")

    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(tmp_path))
    app = create_app()
    client = TestClient(app)
    r = client.get("/reference/rules/demo")
    assert r.status_code == 200
    assert "sleuth" in r.text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_routes.py::test_reference_router_registered_in_real_app -v
```

Expected: FAIL (404 — router not registered).

- [ ] **Step 3: Register the router in `app.py`**

Find the block around line 269 that does `app.include_router(rest_router)` and add immediately after:

```python
from sidequest.server.reference_routes import create_reference_router
app.include_router(create_reference_router())
```

(If imports must live at the top of the file per project style, move the
`from sidequest.server.reference_routes import ...` to the top with the
other `sidequest.server.*` imports, and keep `app.include_router(...)` in the
sequence at line 269+.)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_routes.py::test_reference_router_registered_in_real_app -v
```

Expected: PASS.

- [ ] **Step 5: Run the full server check**

```bash
cd sidequest-server && uv run ruff check . && uv run pytest tests/server/ -v
```

Expected: lint clean, all server tests PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/app.py \
        sidequest-server/tests/server/test_reference_routes.py
git commit -m "feat(reference): wire reference router into FastAPI app"
```

---

### Task 9: Live-pack smoke test

**Files:**
- Create: `sidequest-server/tests/server/test_reference_smoke.py`

- [ ] **Step 1: Write the smoke test**

```python
"""Smoke test against the live tea_and_murder genre pack.

This is the FIXTURE-vs-LIVE separation called out in repo conventions: this
test asserts the route returns 200 against the actually-shipping content and
that critical spoiler files do not leak. It does not assert specific content
of any class or culture — that's a content-team deliverable, not a server
concern.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _has_live_pack() -> bool:
    paths = os.environ.get("SIDEQUEST_GENRE_PACKS", "")
    for root in paths.split(os.pathsep):
        if root and (Path(root) / "tea_and_murder").is_dir():
            return True
    # Fallback: the orchestrator-relative path
    repo_relative = Path(__file__).resolve().parents[3] / "sidequest-content" / "genre_packs"
    return (repo_relative / "tea_and_murder").is_dir()


pytestmark = pytest.mark.skipif(
    not _has_live_pack(),
    reason="live tea_and_murder pack not on SIDEQUEST_GENRE_PACKS path",
)


@pytest.fixture()
def client(monkeypatch):
    # Ensure SIDEQUEST_GENRE_PACKS points at the in-repo content dir if not set
    if "SIDEQUEST_GENRE_PACKS" not in os.environ:
        repo_relative = Path(__file__).resolve().parents[3] / "sidequest-content" / "genre_packs"
        monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(repo_relative))
    from sidequest.server.app import create_app
    return TestClient(create_app())


def test_rules_route_against_live_tea_and_murder(client):
    r = client.get("/reference/rules/tea_and_murder")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    # Spec ACs: archetypes and classes are non-optional for tea_and_murder
    assert "archetypes.yaml" in r.text
    assert "classes.yaml" in r.text


def test_live_lore_does_not_leak_npcs_or_seed_tropes(client):
    r = client.get("/reference/lore/tea_and_murder/glenross")
    assert r.status_code == 200
    # File-level exclusion (v1) — even if files exist they must not render
    assert "npcs.yaml" not in r.text
    assert "seed_tropes.yaml" not in r.text


def test_live_rules_does_not_leak_seed_tropes(client):
    r = client.get("/reference/rules/tea_and_murder")
    assert r.status_code == 200
    assert "seed_tropes.yaml" not in r.text
    assert "prompts.yaml" not in r.text
```

- [ ] **Step 2: Run the smoke test**

```bash
cd sidequest-server && uv run pytest tests/server/test_reference_smoke.py -v
```

Expected: 3 PASS (if live pack present), or 3 SKIP (if env not set).

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_reference_smoke.py
git commit -m "test(reference): live-pack smoke (spoiler exclusion verified)"
```

---

### Task 10: UI — ReferenceLinks component

**Files:**
- Create: `sidequest-ui/src/components/ReferenceLinks.tsx`
- Create: `sidequest-ui/src/components/__tests__/ReferenceLinks.test.tsx`

- [ ] **Step 1: Write the failing test**

`sidequest-ui/src/components/__tests__/ReferenceLinks.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ReferenceLinks } from "@/components/ReferenceLinks";


describe("ReferenceLinks", () => {
  it("renders Rules and Lore links with correct hrefs", () => {
    render(<ReferenceLinks pack="tea_and_murder" world="glenross" />);
    const rules = screen.getByRole("link", { name: /^rules$/i });
    const lore = screen.getByRole("link", { name: /^lore$/i });
    expect(rules).toHaveAttribute("href", "/reference/rules/tea_and_murder");
    expect(lore).toHaveAttribute("href", "/reference/lore/tea_and_murder/glenross");
  });

  it("opens links in a new tab with noopener", () => {
    render(<ReferenceLinks pack="tea_and_murder" world="glenross" />);
    const rules = screen.getByRole("link", { name: /^rules$/i });
    expect(rules).toHaveAttribute("target", "_blank");
    expect(rules).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("renders nothing when pack is missing", () => {
    const { container } = render(<ReferenceLinks pack={null} world="glenross" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders only Rules link when world is missing", () => {
    render(<ReferenceLinks pack="tea_and_murder" world={null} />);
    expect(screen.queryByRole("link", { name: /^rules$/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^lore$/i })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-ui && npx vitest run src/components/__tests__/ReferenceLinks.test.tsx
```

Expected: import error (component does not exist).

- [ ] **Step 3: Implement the component**

`sidequest-ui/src/components/ReferenceLinks.tsx`:

```tsx
interface ReferenceLinksProps {
  pack: string | null | undefined;
  world: string | null | undefined;
}

export function ReferenceLinks({ pack, world }: ReferenceLinksProps) {
  if (!pack) return null;
  return (
    <div className="reference-links flex gap-3 px-3 py-1 text-sm" data-testid="reference-links">
      <a
        className="reference-links__link underline hover:no-underline"
        href={`/reference/rules/${pack}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        Rules
      </a>
      {world ? (
        <a
          className="reference-links__link underline hover:no-underline"
          href={`/reference/lore/${pack}/${world}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Lore
        </a>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-ui && npx vitest run src/components/__tests__/ReferenceLinks.test.tsx
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/ReferenceLinks.tsx \
        sidequest-ui/src/components/__tests__/ReferenceLinks.test.tsx
git commit -m "feat(ui): ReferenceLinks component (Rules + Lore anchors)"
```

---

### Task 11: Wire ReferenceLinks into NarrativeWidget + GameBoard

**Files:**
- Modify: `sidequest-ui/src/components/GameBoard/widgets/NarrativeWidget.tsx`
- Modify: `sidequest-ui/src/components/GameBoard/GameBoard.tsx` (around line 428 where `NarrativeWidget` is rendered)
- Create: `sidequest-ui/src/components/GameBoard/widgets/__tests__/NarrativeWidget.test.tsx`

- [ ] **Step 1: Write the wiring test**

`sidequest-ui/src/components/GameBoard/widgets/__tests__/NarrativeWidget.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { NarrativeWidget } from "@/components/GameBoard/widgets/NarrativeWidget";


describe("NarrativeWidget — reference links wiring", () => {
  it("renders the ReferenceLinks when pack and world are supplied", () => {
    render(
      <NarrativeWidget
        messages={[]}
        genreSlug="tea_and_murder"
        worldSlug="glenross"
      />,
    );
    expect(screen.getByTestId("reference-links")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /^rules$/i }),
    ).toHaveAttribute("href", "/reference/rules/tea_and_murder");
    expect(
      screen.getByRole("link", { name: /^lore$/i }),
    ).toHaveAttribute("href", "/reference/lore/tea_and_murder/glenross");
  });

  it("does not render reference links when genreSlug is missing", () => {
    render(<NarrativeWidget messages={[]} />);
    expect(screen.queryByTestId("reference-links")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-ui && npx vitest run src/components/GameBoard/widgets/__tests__/NarrativeWidget.test.tsx
```

Expected: FAIL — `worldSlug` prop not accepted, no reference-links node.

- [ ] **Step 3: Update NarrativeWidget**

Replace `sidequest-ui/src/components/GameBoard/widgets/NarrativeWidget.tsx` with:

```tsx
import { NarrativeView } from "@/screens/NarrativeView";
import { ReferenceLinks } from "@/components/ReferenceLinks";
import type { GameMessage } from "@/types/protocol";

interface NarrativeWidgetProps {
  messages: GameMessage[];
  thinking?: boolean;
  /** Genre slug — passes through to the narrator-thinking indicator AND the
   *  reference links. */
  genreSlug?: string | null;
  /** World slug — passes through to the lore reference link. */
  worldSlug?: string | null;
}

export function NarrativeWidget({
  messages,
  thinking,
  genreSlug,
  worldSlug,
}: NarrativeWidgetProps) {
  return (
    <div className="narrative-widget flex flex-col flex-1 min-h-0">
      <ReferenceLinks pack={genreSlug} world={worldSlug} />
      <NarrativeView messages={messages} thinking={thinking} genreSlug={genreSlug} />
    </div>
  );
}
```

- [ ] **Step 4: Update GameBoard to pass `worldSlug`**

In `sidequest-ui/src/components/GameBoard/GameBoard.tsx`, around line 428:

```tsx
return <NarrativeWidget messages={messages} thinking={thinking} genreSlug={genreSlug} worldSlug={worldSlug} />;
```

(Add `worldSlug` to the existing call. `worldSlug` is already in scope in this
function — confirmed at line 202 / 262.)

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd sidequest-ui && npx vitest run src/components/GameBoard/widgets/__tests__/NarrativeWidget.test.tsx \
                                src/components/__tests__/ReferenceLinks.test.tsx
```

Expected: 6 PASS.

- [ ] **Step 6: Run the full UI test suite to catch regressions**

```bash
cd sidequest-ui && npx vitest run
```

Expected: all PASS. If GameBoard tests fail because they don't supply `worldSlug`, that's expected — the prop is optional and renders nothing when absent. Verify no regressions in NarrationScroll / NarrationFocus / NarrationCards (those still receive `genreSlug` via NarrativeView).

- [ ] **Step 7: Commit**

```bash
git add sidequest-ui/src/components/GameBoard/widgets/NarrativeWidget.tsx \
        sidequest-ui/src/components/GameBoard/widgets/__tests__/NarrativeWidget.test.tsx \
        sidequest-ui/src/components/GameBoard/GameBoard.tsx
git commit -m "feat(ui): wire ReferenceLinks into narrative widget"
```

---

### Task 12: Final acceptance run

**Files:** none (verification only)

- [ ] **Step 1: Run the full server check**

```bash
cd sidequest-server && uv run ruff check . && uv run pytest
```

Expected: lint clean, full pytest suite PASS.

- [ ] **Step 2: Run the full UI suite**

```bash
cd sidequest-ui && npx vitest run && npm run build
```

Expected: tests PASS, build succeeds.

- [ ] **Step 3: Manual verification against a running stack**

Start the services:

```bash
just up
```

In a browser, with the live `tea_and_murder` / `glenross` session running:

1. Open `http://localhost:8765/reference/rules/tea_and_murder` — confirm sections
   for archetypes, classes, rules, progression, power_tiers, achievements,
   tropes, equipment_tables, inventory, beat_vocabulary appear in that order.
   Confirm `npcs.yaml`, `seed_tropes.yaml`, `prompts.yaml` strings are absent.
2. Open `http://localhost:8765/reference/lore/tea_and_murder/glenross` —
   confirm world tier (world, cultures, history, calendar, demographics,
   legends, openings, lore) followed by pack flavor with `(genre)` labels.
3. Open `http://localhost:5173/` and start/join a `tea_and_murder/glenross`
   session. Confirm "Rules" and "Lore" links appear above the narration panel.
   Click each — verify they open in a new tab and the page renders styled HTML.
4. Confirm clicking the links does NOT consume a turn (no new player turn state,
   no WebSocket activity in the network tab, no narrator response triggered).

- [ ] **Step 4: Run the orchestrator aggregate gate**

```bash
just check-all
```

Expected: pass.

- [ ] **Step 5: Acceptance criteria checklist**

Tick each item from `docs/superpowers/specs/2026-05-23-reference-pages-design.md`:

- [ ] AC1: `GET /reference/rules/tea_and_murder` returns 200 `text/html` with sections in order.
- [ ] AC2: `GET /reference/lore/tea_and_murder/glenross` returns 200 with world tier + pack flavor.
- [ ] AC3: Lore route contains no content from `npcs.yaml` or `seed_tropes.yaml`.
- [ ] AC4: Unknown pack/world returns 404 with list of valid ids.
- [ ] AC5: NarrativeView (via NarrativeWidget) renders "Rules" and "Lore" links opening in new tab; absent before session starts.
- [ ] AC6: Clicking either link does not post any WebSocket message or alter game state.
- [ ] AC7: All headings have stable slugified `id` attributes.
- [ ] AC8: `just check-all` passes.

- [ ] **Step 6: Open PR(s)**

Per `.pennyfarthing/repos.yaml` topology:
- Orchestrator changes (the design doc + this plan) → PR to `main`
- `sidequest-server` changes → PR to `develop`
- `sidequest-ui` changes → PR to `develop`

Use `gh pr create` with body summarizing the spec and ACs. Link spec + plan from each subrepo PR description so reviewers can find them.

---

## Out of Scope (Iteration 2 — DO NOT IMPLEMENT HERE)

The spec calls these out and the implementation must NOT pre-build them:

- Field-level spoiler / audience filter (`?audience=player|gm` flag)
- Re-inclusion of `npcs.yaml` and `seed_tropes.yaml` with public projections
- Deep-link anchors from in-game panels (class signature buttons → `#class-...`)
- Pack-themed stylesheet (`client_theme.css` integration)
- Lobby surface (`/reference` index, in-lobby links)
- Markdown rendering of scalar string values
- World↔pack override merging

If any of these become tempting during implementation, stop and flag — that's a scope change, not a refinement.
