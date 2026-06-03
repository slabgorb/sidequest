# Feature Inventory Generator — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-maintained `docs/feature-inventory.md` status column with a generated, evidence-verified one — a manifest + generator that fails the build when a feature's claimed status lacks backing in `SPAN_ROUTES`, wiring tests, modules, ADR frontmatter, or `draft` flags.

**Architecture:** Mirror `scripts/regenerate_adr_indexes.py`: a per-category YAML manifest (`docs/feature-inventory/<category>.yaml`) is the single source; a generator parses it, verifies each feature's evidence anchors against the live repo, renders markdown tables into the marker-delimited region of `docs/feature-inventory.md`, and exits non-zero on any unverifiable claim. A `just feature-inventory-check` recipe regenerates + git-diffs, mirroring `just adr-check`.

**Tech Stack:** Python 3 (orchestrator `uv` env — PyYAML available via `render_common`), pytest (`scripts/tests/`), justfile.

**Phase boundary:** This phase ships static verification (`spans ∈ SPAN_ROUTES constants`, wiring-test/module existence, ADR status, draft predicate) and migrates ONE representative category as proof. `live_wired` is provisionally `routed ∧ wiring-tested` until Phase 2 adds observed-emission. Phases 2 (observed-emission capture) and 3 (coverage reports) get their own plans. Full migration of the remaining categories is a tracked follow-on chore once the machinery is proven.

**Spec:** `docs/superpowers/specs/2026-06-03-feature-inventory-surfacing-design.md`

> **Path note:** every `Run:` command executes from the repo root
> (`/Users/slabgorb/Projects/oq-1`). `{{root}}` inside the justfile recipes is
> the justfile's own pre-defined variable — leave it literal there.

---

## File Structure

- `scripts/feature_inventory_verify.py` — **create.** Pure, unit-testable verifiers: parse the SPAN constant set from `telemetry/spans/*.py`; check wiring-test file existence; resolve a module reference to a real file; read an ADR's `status`; resolve a `draft_world` predicate. No I/O orchestration, no markdown.
- `scripts/regenerate_feature_inventory.py` — **create.** Entry point: load manifest dir, run verification, render markdown tables, write between markers in `docs/feature-inventory.md`, exit non-zero on failure. Mirrors `regenerate_adr_indexes.py`.
- `docs/feature-inventory/confrontation-engine.yaml` — **create.** The one migrated category (proof-of-pipeline).
- `docs/feature-inventory.md` — **modify.** Insert `<!-- FEATURE-INVENTORY:GENERATED:BEGIN/END -->` markers; the migrated category's table is generated between them.
- `scripts/tests/test_feature_inventory.py` — **create.** Unit + wiring tests.
- `justfile` — **modify.** Add `feature-inventory-regen` and `feature-inventory-check` recipes.

Conventions to copy verbatim from `scripts/regenerate_adr_indexes.py`: `ROOT = Path(__file__).parent.parent`; HTML-comment markers; `replace_between_markers(filepath, body)` (preamble above BEGIN and prose below END preserved); glob-load of sources.

---

## Task 1: Span-constant registry parser

**Files:**
- Create: `scripts/feature_inventory_verify.py`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/test_feature_inventory.py
"""Tests for the feature-inventory generator (Phase 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.feature_inventory_verify import load_span_constants

ROOT = Path(__file__).parent.parent.parent  # repo root


def test_load_span_constants_parses_literals(tmp_path):
    spans_dir = tmp_path / "spans"
    spans_dir.mkdir()
    (spans_dir / "turn.py").write_text(
        'SPAN_TURN = "turn"\n'
        'SPAN_TURN_BARRIER = "turn.barrier"\n'
        "SPAN_ROUTES[SPAN_TURN] = SpanRoute(...)\n"
    )
    (spans_dir / "_core.py").write_text("SPAN_ROUTES = {}\n")
    names = load_span_constants(spans_dir)
    assert names == {"turn", "turn.barrier"}


def test_load_span_constants_against_real_registry():
    """Wiring: the real telemetry/spans dir parses and contains known spans."""
    real = ROOT / "sidequest-server" / "sidequest" / "telemetry" / "spans"
    names = load_span_constants(real)
    assert "turn" in names
    assert "turn.barrier" in names
    assert len(names) > 20  # registry is substantial
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py::test_load_span_constants_parses_literals -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.feature_inventory_verify'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/feature_inventory_verify.py
"""Evidence verifiers for the feature-inventory generator (Phase 1).

Each function checks one anchor type against the live repo and is pure
(filesystem reads only, no markdown, no orchestration) so it can be unit
tested in isolation.
"""
from __future__ import annotations

import re
from pathlib import Path

_SPAN_CONST_RE = re.compile(r'^SPAN_[A-Z0-9_]+\s*=\s*"([^"]+)"', re.MULTILINE)


def load_span_constants(spans_dir: Path) -> set[str]:
    """Return the set of span name literals declared in telemetry/spans/*.py.

    A span name is 'known to the engine' iff it is declared as a
    ``SPAN_* = "literal"`` module constant. Static parse (no import) keeps
    this doc tool free of server runtime deps, matching the ADR generator.
    """
    names: set[str] = set()
    for path in sorted(spans_dir.glob("*.py")):
        names.update(_SPAN_CONST_RE.findall(path.read_text()))
    return names
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -v`
Expected: PASS (both span tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/feature_inventory_verify.py scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): span-constant registry parser"
```

---

## Task 2: Wiring-test and module existence verifiers

**Files:**
- Modify: `scripts/feature_inventory_verify.py`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test**

```python
# append to scripts/tests/test_feature_inventory.py
from scripts.feature_inventory_verify import wiring_test_exists, resolve_module


def test_wiring_test_exists(tmp_path):
    (tmp_path / "a.test.tsx").write_text("// test")
    assert wiring_test_exists("a.test.tsx", tmp_path) is True
    assert wiring_test_exists("missing.test.tsx", tmp_path) is False


def test_resolve_module_server_dotted(tmp_path):
    server = tmp_path / "sidequest-server" / "sidequest"
    (server / "game").mkdir(parents=True)
    (server / "game" / "encounter.py").write_text("# mod")
    # dotted and path forms both resolve under sidequest-server/sidequest/
    assert resolve_module("game.encounter", tmp_path) is not None
    assert resolve_module("game/encounter.py", tmp_path) is not None
    assert resolve_module("game.missing", tmp_path) is None


def test_resolve_module_ui_component(tmp_path):
    ui = tmp_path / "sidequest-ui" / "src" / "components"
    ui.mkdir(parents=True)
    (ui / "ConfrontationOverlay.tsx").write_text("// component")
    assert resolve_module("ConfrontationOverlay", tmp_path) is not None
    assert resolve_module("NopeOverlay", tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "wiring_test_exists or resolve_module" -v`
Expected: FAIL — `ImportError: cannot import name 'wiring_test_exists'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/feature_inventory_verify.py


def wiring_test_exists(rel_path: str, base: Path) -> bool:
    """True iff `rel_path` resolves to an existing file under `base`."""
    return (base / rel_path).is_file()


def resolve_module(ref: str, repo_root: Path) -> Path | None:
    """Resolve a module reference to a real file, or None.

    Server refs (dotted `game.encounter` or path `game/encounter.py`) resolve
    under sidequest-server/sidequest/. A bare CamelCase name resolves as a UI
    component basename glob under sidequest-ui/src/.
    """
    server_root = repo_root / "sidequest-server" / "sidequest"
    if ref.endswith(".py") or "/" in ref:
        candidate = server_root / ref
        return candidate if candidate.is_file() else None
    if "." in ref:  # dotted server module
        candidate = server_root / (ref.replace(".", "/") + ".py")
        return candidate if candidate.is_file() else None
    # bare name → UI component basename glob
    ui_root = repo_root / "sidequest-ui" / "src"
    if ui_root.is_dir():
        for ext in (".tsx", ".ts"):
            matches = list(ui_root.rglob(ref + ext))
            if matches:
                return matches[0]
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "wiring_test_exists or resolve_module" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/feature_inventory_verify.py scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): wiring-test and module verifiers"
```

---

## Task 3: ADR-status and draft-world verifiers

**Files:**
- Modify: `scripts/feature_inventory_verify.py`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test**

```python
# append to scripts/tests/test_feature_inventory.py
from scripts.feature_inventory_verify import adr_status, draft_world_is_draft


def test_adr_status_reads_frontmatter(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "033-confrontation.md").write_text(
        "---\nid: 33\nstatus: accepted\n---\n# body\n"
    )
    assert adr_status(33, tmp_path) == "accepted"
    assert adr_status(999, tmp_path) is None


def test_draft_world_predicate(tmp_path):
    world = tmp_path / "sidequest-content" / "genre_packs" / "tea_and_murder" / "worlds" / "blackthorn_moor"
    world.mkdir(parents=True)
    (world / "world.yaml").write_text("name: Blackthorn Moor\ndraft: true\n")
    assert draft_world_is_draft("tea_and_murder/blackthorn_moor", tmp_path) is True

    live = tmp_path / "sidequest-content" / "genre_packs" / "tea_and_murder" / "worlds" / "glenross"
    live.mkdir(parents=True)
    (live / "world.yaml").write_text("name: Glenross\n")  # no draft key
    assert draft_world_is_draft("tea_and_murder/glenross", tmp_path) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "adr_status or draft_world" -v`
Expected: FAIL — `ImportError: cannot import name 'adr_status'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/feature_inventory_verify.py
import yaml  # PyYAML — available in the orchestrator uv env (used by render_common)

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def adr_status(adr_id: int, repo_root: Path) -> str | None:
    """Return the `status` frontmatter value of ADR `adr_id`, or None."""
    adr_dir = repo_root / "docs" / "adr"
    matches = list(adr_dir.glob(f"{adr_id:03d}-*.md"))
    if not matches:
        return None
    m = _FM_RE.match(matches[0].read_text())
    if not m:
        return None
    fm = yaml.safe_load(m.group(1)) or {}
    status = fm.get("status")
    return str(status) if status is not None else None


def draft_world_is_draft(world_ref: str, repo_root: Path) -> bool:
    """True iff `<pack>/<world>` has `draft: true` in its world.yaml."""
    pack, _, world = world_ref.partition("/")
    wy = (
        repo_root / "sidequest-content" / "genre_packs" / pack
        / "worlds" / world / "world.yaml"
    )
    if not wy.is_file():
        return False
    data = yaml.safe_load(wy.read_text()) or {}
    return data.get("draft") is True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "adr_status or draft_world" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/feature_inventory_verify.py scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): ADR-status and draft-world verifiers"
```

---

## Task 4: Manifest loader + schema validation

**Files:**
- Modify: `scripts/feature_inventory_verify.py`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test**

```python
# append to scripts/tests/test_feature_inventory.py
from scripts.feature_inventory_verify import load_manifest, ManifestError


def test_load_manifest_parses_categories(tmp_path):
    d = tmp_path / "docs" / "feature-inventory"
    d.mkdir(parents=True)
    (d / "confrontation-engine.yaml").write_text(
        "category: Confrontation Engine\n"
        "features:\n"
        "  - id: confrontation_engine\n"
        "    name: Confrontation engine\n"
        "    modules: [game/encounter.py]\n"
        "    ui: ConfrontationOverlay\n"
        "    manual_test: Take a turn that triggers a confrontation\n"
        "    status: live_wired\n"
        "    evidence:\n"
        "      spans: [confrontation.resolved]\n"
        "      wiring_tests: [sidequest-ui/src/__tests__/confrontation-wiring.test.tsx]\n"
    )
    cats = load_manifest(tmp_path / "docs" / "feature-inventory")
    assert cats[0].category == "Confrontation Engine"
    assert cats[0].features[0].id == "confrontation_engine"
    assert cats[0].features[0].status == "live_wired"


def test_load_manifest_rejects_bad_status(tmp_path):
    d = tmp_path / "docs" / "feature-inventory"
    d.mkdir(parents=True)
    (d / "x.yaml").write_text(
        "category: X\nfeatures:\n  - id: a\n    name: A\n    status: bogus\n"
    )
    with pytest.raises(ManifestError, match="bogus"):
        load_manifest(d)


def test_load_manifest_rejects_duplicate_ids(tmp_path):
    d = tmp_path / "docs" / "feature-inventory"
    d.mkdir(parents=True)
    (d / "a.yaml").write_text("category: A\nfeatures:\n  - id: dup\n    name: A1\n    status: engineering\n")
    (d / "b.yaml").write_text("category: B\nfeatures:\n  - id: dup\n    name: B1\n    status: engineering\n")
    with pytest.raises(ManifestError, match="duplicate id"):
        load_manifest(d)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k load_manifest -v`
Expected: FAIL — `ImportError: cannot import name 'load_manifest'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/feature_inventory_verify.py
from dataclasses import dataclass, field

VALID_STATUSES = {
    "live_wired", "live_partial", "dark", "deferred", "draft", "engineering",
}


class ManifestError(Exception):
    """Raised when a manifest file violates the schema."""


@dataclass
class Feature:
    id: str
    name: str
    status: str
    modules: list[str] = field(default_factory=list)
    ui: str = "—"
    manual_test: str = ""
    evidence: dict = field(default_factory=dict)


@dataclass
class Category:
    category: str
    features: list[Feature]


def load_manifest(manifest_dir: Path) -> list[Category]:
    """Load + validate every <category>.yaml. Raise ManifestError on violation."""
    categories: list[Category] = []
    seen_ids: dict[str, str] = {}
    for path in sorted(manifest_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        cat_name = data.get("category")
        if not cat_name:
            raise ManifestError(f"{path.name}: missing 'category'")
        feats: list[Feature] = []
        for raw in data.get("features", []):
            fid = raw.get("id")
            if not fid:
                raise ManifestError(f"{path.name}: feature missing 'id'")
            if fid in seen_ids:
                raise ManifestError(
                    f"duplicate id '{fid}' in {path.name} and {seen_ids[fid]}"
                )
            seen_ids[fid] = path.name
            status = raw.get("status")
            if status not in VALID_STATUSES:
                raise ManifestError(
                    f"{path.name}: feature '{fid}' has invalid status '{status}'"
                )
            feats.append(Feature(
                id=fid, name=raw.get("name", fid), status=status,
                modules=raw.get("modules", []), ui=raw.get("ui", "—"),
                manual_test=raw.get("manual_test", ""),
                evidence=raw.get("evidence", {}) or {},
            ))
        categories.append(Category(category=cat_name, features=feats))
    return categories
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k load_manifest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/feature_inventory_verify.py scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): manifest loader + schema validation"
```

---

## Task 5: Status-verification rule engine

**Files:**
- Modify: `scripts/feature_inventory_verify.py`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test**

```python
# append to scripts/tests/test_feature_inventory.py
from scripts.feature_inventory_verify import verify_feature, VerifyContext


def _ctx(tmp_path, span_names=("confrontation.resolved",)):
    return VerifyContext(
        repo_root=tmp_path,
        span_names=set(span_names),
    )


def test_live_wired_passes_with_span_and_wiring(tmp_path):
    wt = tmp_path / "wt.test.tsx"
    wt.write_text("// test")
    f = Feature(
        id="x", name="X", status="live_wired",
        evidence={"spans": ["confrontation.resolved"], "wiring_tests": ["wt.test.tsx"]},
    )
    ok, reason = verify_feature(f, _ctx(tmp_path))
    assert ok is True, reason


def test_live_wired_fails_when_span_unregistered(tmp_path):
    f = Feature(
        id="x", name="X", status="live_wired",
        evidence={"spans": ["ghost.span"], "wiring_tests": ["wt.test.tsx"]},
    )
    ok, reason = verify_feature(f, _ctx(tmp_path))
    assert ok is False
    assert "ghost.span" in reason


def test_module_existence_failure_blocks_any_status(tmp_path):
    f = Feature(
        id="x", name="X", status="engineering",
        modules=["game/does_not_exist.py"],
    )
    ok, reason = verify_feature(f, _ctx(tmp_path))
    assert ok is False
    assert "does_not_exist" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "live_wired or module_existence" -v`
Expected: FAIL — `ImportError: cannot import name 'verify_feature'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/feature_inventory_verify.py


@dataclass
class VerifyContext:
    repo_root: Path
    span_names: set[str]


def verify_feature(f: Feature, ctx: VerifyContext) -> tuple[bool, str]:
    """Verify a feature's claimed status against its evidence.

    Returns (ok, reason). reason is '' on success, else the named failure.
    """
    # Module existence is mandatory for every status (catches silent renames).
    for mod in f.modules:
        if resolve_module(mod, ctx.repo_root) is None:
            return False, f"module '{mod}' does not resolve to a file"

    ev = f.evidence
    spans = ev.get("spans", [])
    routed = [s for s in spans if s in ctx.span_names]
    unrouted = [s for s in spans if s not in ctx.span_names]
    wiring_ok = any(
        wiring_test_exists(w, ctx.repo_root) for w in ev.get("wiring_tests", [])
    )

    if f.status == "live_wired":
        if not routed:
            return False, f"live_wired but no declared span is registered: {unrouted}"
        if not wiring_ok:
            return False, "live_wired but no declared wiring test file exists"
        return True, ""
    if f.status == "live_partial":
        if routed or wiring_ok or ev.get("adr"):
            return True, ""
        return False, "live_partial but no span, wiring test, or ADR evidence"
    if f.status == "dark":
        if ev.get("adr") and adr_status(ev["adr"], ctx.repo_root):
            return True, ""
        return False, "dark requires an `adr` anchor with a readable status"
    if f.status == "deferred":
        st = adr_status(ev["adr"], ctx.repo_root) if ev.get("adr") else None
        if st in {"deferred", "proposed"}:
            return True, ""
        return False, f"deferred but ADR status is {st!r} (need deferred/proposed)"
    if f.status == "draft":
        if ev.get("draft_world") and draft_world_is_draft(ev["draft_world"], ctx.repo_root):
            return True, ""
        return False, "draft requires a `draft_world` that resolves draft: true"
    if f.status == "engineering":
        return True, ""  # modules already checked above
    return False, f"unknown status {f.status!r}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "live_wired or module_existence" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/feature_inventory_verify.py scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): status-verification rule engine"
```

---

## Task 6: Markdown renderer + marker writer

**Files:**
- Create: `scripts/regenerate_feature_inventory.py`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test**

```python
# append to scripts/tests/test_feature_inventory.py
from scripts.regenerate_feature_inventory import render_body, replace_between_markers, MARKER_BEGIN, MARKER_END


def test_render_body_emits_category_table(tmp_path):
    cats = [Category("Confrontation Engine", [
        Feature(id="x", name="Conf engine", status="live_wired",
                modules=["game/encounter.py"], ui="ConfrontationOverlay",
                manual_test="trigger a confrontation"),
    ])]
    body = render_body(cats, {"x": "Live & Wired"})
    assert "### Confrontation Engine" in body
    assert "Conf engine" in body
    assert "Live & Wired" in body
    assert "ConfrontationOverlay" in body


def test_replace_between_markers_preserves_surrounds(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(f"PRE\n{MARKER_BEGIN}\nold\n{MARKER_END}\nPOST\n")
    replace_between_markers(f, "NEW")
    out = f.read_text()
    assert "PRE" in out and "POST" in out and "NEW" in out and "old" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "render_body or replace_between" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.regenerate_feature_inventory'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/regenerate_feature_inventory.py
#!/usr/bin/env python3
"""Regenerate docs/feature-inventory.md from the verified manifest (Phase 1).

The per-category tables between the GENERATED markers are derived from
docs/feature-inventory/<category>.yaml and rendered ONLY after each feature's
claimed status is verified against the live repo. Any unverifiable claim makes
the script exit non-zero (no doc is written), so drift fails the build.
"""
from __future__ import annotations

import sys
from pathlib import Path

from scripts.feature_inventory_verify import (
    Category, VerifyContext, load_manifest, load_span_constants, verify_feature,
)

ROOT = Path(__file__).parent.parent
DOC = ROOT / "docs" / "feature-inventory.md"
MANIFEST_DIR = ROOT / "docs" / "feature-inventory"
SPANS_DIR = ROOT / "sidequest-server" / "sidequest" / "telemetry" / "spans"

MARKER_BEGIN = "<!-- FEATURE-INVENTORY:GENERATED:BEGIN -->"
MARKER_END = "<!-- FEATURE-INVENTORY:GENERATED:END -->"

STATUS_LABEL = {
    "live_wired": "Live & Wired", "live_partial": "Live (partial)",
    "dark": "Dark", "deferred": "Deferred", "draft": "Draft",
    "engineering": "Engineering",
}


def render_body(categories: list[Category], status_label: dict[str, str]) -> str:
    lines = [
        "> **Generated.** Do not edit between the markers by hand. Update the "
        "per-category manifests in `docs/feature-inventory/` and run "
        "`just feature-inventory-regen`.",
        "",
    ]
    for cat in categories:
        lines.append(f"### {cat.category}")
        lines.append("")
        lines.append("| Feature | Status | Module(s) | UI | Manual test |")
        lines.append("|---------|--------|-----------|----|-------------|")
        for f in cat.features:
            label = status_label.get(f.id, STATUS_LABEL.get(f.status, f.status))
            mods = ", ".join(f"`{m}`" for m in f.modules) or "—"
            lines.append(
                f"| {f.name} | {label} | {mods} | {f.ui} | {f.manual_test} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def replace_between_markers(filepath: Path, body: str) -> None:
    text = filepath.read_text()
    if MARKER_BEGIN not in text or MARKER_END not in text:
        raise SystemExit(
            f"{filepath} is missing the GENERATED markers; add them once by hand."
        )
    begin = text.index(MARKER_BEGIN)
    end = text.index(MARKER_END, begin) + len(MARKER_END)
    new = (
        text[:begin] + MARKER_BEGIN + "\n\n" + body + "\n" + MARKER_END + text[end:]
    )
    filepath.write_text(new)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "render_body or replace_between" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/regenerate_feature_inventory.py scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): markdown renderer + marker writer"
```

---

## Task 7: Entry point — verify-then-write, with fail-loud exit

**Files:**
- Modify: `scripts/regenerate_feature_inventory.py`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test**

```python
# append to scripts/tests/test_feature_inventory.py
from scripts.regenerate_feature_inventory import generate


def test_generate_fails_on_unverifiable_claim(tmp_path, capsys):
    (tmp_path / "docs" / "feature-inventory").mkdir(parents=True)
    (tmp_path / "docs" / "feature-inventory" / "x.yaml").write_text(
        "category: X\nfeatures:\n  - id: a\n    name: A\n    status: live_wired\n"
        "    evidence:\n      spans: [ghost.span]\n"
    )
    doc = tmp_path / "docs" / "feature-inventory.md"
    doc.write_text(f"PRE\n{MARKER_BEGIN}\n{MARKER_END}\nPOST\n")
    rc = generate(repo_root=tmp_path, span_names={"real.span"})
    assert rc != 0
    assert "ghost.span" in capsys.readouterr().err


def test_generate_writes_doc_when_all_verify(tmp_path):
    (tmp_path / "docs" / "feature-inventory").mkdir(parents=True)
    (tmp_path / "docs" / "feature-inventory" / "x.yaml").write_text(
        "category: X\nfeatures:\n  - id: a\n    name: A\n    status: engineering\n"
    )
    doc = tmp_path / "docs" / "feature-inventory.md"
    doc.write_text(f"PRE\n{MARKER_BEGIN}\n{MARKER_END}\nPOST\n")
    rc = generate(repo_root=tmp_path, span_names=set())
    assert rc == 0
    assert "### X" in doc.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k generate -v`
Expected: FAIL — `ImportError: cannot import name 'generate'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/regenerate_feature_inventory.py


def generate(repo_root: Path = ROOT, span_names: set[str] | None = None) -> int:
    """Load → verify → render → write. Return process exit code."""
    manifest_dir = repo_root / "docs" / "feature-inventory"
    doc = repo_root / "docs" / "feature-inventory.md"
    spans_dir = repo_root / "sidequest-server" / "sidequest" / "telemetry" / "spans"
    if span_names is None:
        span_names = load_span_constants(spans_dir)

    categories = load_manifest(manifest_dir)
    ctx = VerifyContext(repo_root=repo_root, span_names=span_names)
    failures: list[str] = []
    for cat in categories:
        for f in cat.features:
            ok, reason = verify_feature(f, ctx)
            if not ok:
                failures.append(f"  [{cat.category}] {f.id}: {reason}")
    if failures:
        print("Feature-inventory verification FAILED:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1

    replace_between_markers(doc, render_body(categories, {}))
    print(f"Wrote {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(generate())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add scripts/regenerate_feature_inventory.py scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): entry point with fail-loud verification"
```

---

## Task 8: Add markers to the doc + migrate the Confrontation Engine category

**Files:**
- Modify: `docs/feature-inventory.md`
- Create: `docs/feature-inventory/confrontation-engine.yaml`

- [ ] **Step 1: Add the GENERATED markers to `docs/feature-inventory.md`**

Find the existing `### Confrontation Engine` section in `docs/feature-inventory.md`. Replace that section's table with the two marker lines (the generator fills between them). Insert exactly:

```markdown
<!-- FEATURE-INVENTORY:GENERATED:BEGIN -->
<!-- FEATURE-INVENTORY:GENERATED:END -->
```

Leave all other sections (preamble, Legend, other categories) untouched — Phase 1 migrates only this one category; the rest stay as static prose until their manifests land.

- [ ] **Step 2: Author the migrated manifest**

Read the current `### Confrontation Engine` rows in `docs/feature-inventory.md` (before deleting them in Step 1 — copy the Feature/Module/UI/Manual-test text). For each row, find a backing span by grepping the registry:

Run: `grep -rhnE '^SPAN_[A-Z_]+ = "(confrontation|encounter)' sidequest-server/sidequest/telemetry/spans/`

Create `docs/feature-inventory/confrontation-engine.yaml` with one feature entry per migrated row, each declaring real evidence (a span literal that the grep confirmed exists, and a wiring test from `sidequest-ui/src/__tests__/confrontation-wiring.test.tsx` if applicable). Example shape:

```yaml
category: Confrontation Engine
features:
  - id: confrontation_engine
    name: Confrontation engine (genre-typed resource pools)
    modules: [game/encounter.py, game/resource_pool.py]
    ui: ConfrontationOverlay
    manual_test: "Take a turn that triggers a confrontation → overlay shows momentum/resource bars"
    status: live_partial   # downgrade from live_wired if no observed-emission yet (Phase 1)
    evidence:
      adr: 33
      wiring_tests: [sidequest-ui/src/__tests__/confrontation-wiring.test.tsx]
```

> Use the status the evidence actually supports. If a row claimed "Live & Wired" but you cannot find a registered span for it, that is exactly the drift this system exists to catch — record `live_partial` with the wiring-test/ADR anchor and note it, rather than forcing `live_wired`.

- [ ] **Step 3: Run the generator**

Run: `cd {{repo root}} && uv run python scripts/regenerate_feature_inventory.py`
Expected: `Wrote .../docs/feature-inventory.md` and exit 0. If it exits non-zero, the message names the row + reason — fix the manifest's status/evidence to match reality (do NOT weaken the verifier).

- [ ] **Step 4: Confirm the doc regenerated and re-running is a no-op**

Run: `cd {{repo root}} && uv run python scripts/regenerate_feature_inventory.py && git diff --stat docs/feature-inventory.md`
Expected: second run leaves no diff (idempotent).

- [ ] **Step 5: Commit**

```bash
git add docs/feature-inventory.md docs/feature-inventory/confrontation-engine.yaml
git commit -m "feat(feature-inventory): migrate Confrontation Engine category to verified manifest"
```

---

## Task 9: `just` guard recipes (mirror `adr-check`)

**Files:**
- Modify: `justfile`
- Test: `scripts/tests/test_feature_inventory.py`

- [ ] **Step 1: Write the failing test (drift guard behavior)**

```python
# append to scripts/tests/test_feature_inventory.py
def test_check_recipe_detects_drift(tmp_path):
    """A hand-edit inside the markers must be reverted by regen → git sees drift."""
    # This is a behavioral contract test for the recipe; assert the generator
    # rewrites a tampered region back to canonical.
    (tmp_path / "docs" / "feature-inventory").mkdir(parents=True)
    (tmp_path / "docs" / "feature-inventory" / "x.yaml").write_text(
        "category: X\nfeatures:\n  - id: a\n    name: A\n    status: engineering\n"
    )
    doc = tmp_path / "docs" / "feature-inventory.md"
    doc.write_text(f"PRE\n{MARKER_BEGIN}\nTAMPERED\n{MARKER_END}\nPOST\n")
    from scripts.regenerate_feature_inventory import generate
    generate(repo_root=tmp_path, span_names=set())
    assert "TAMPERED" not in doc.read_text()
    assert "### X" in doc.read_text()
```

- [ ] **Step 2: Run test to verify it passes (generator already supports this)**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k check_recipe -v`
Expected: PASS (proves the regen overwrites tampering; the recipe wraps this in a git-diff gate)

- [ ] **Step 3: Add the recipes to `justfile`**

Find the existing `adr-check:` / `adr-regen:` recipes (around line 599) and add, mirroring them:

```just
# Regenerate the feature inventory from the verified manifest
feature-inventory-regen:
    cd {{root}} && uv run python3 {{root}}/scripts/regenerate_feature_inventory.py

# CI guard: regen must produce no diff and no verification failure
feature-inventory-check:
    cd {{root}} && uv run python3 {{root}}/scripts/regenerate_feature_inventory.py > /dev/null
    cd {{root}} && git diff --quiet docs/feature-inventory.md || (echo "feature-inventory.md is stale. Run: just feature-inventory-regen (then stage + commit)" && exit 1)
```

- [ ] **Step 4: Verify the recipes run**

Run: `cd {{repo root}} && just feature-inventory-regen && just feature-inventory-check`
Expected: regen writes the doc; check exits 0 (clean tree after regen). Introduce a tampering edit inside the markers and re-run `just feature-inventory-check` → exits 1 with the stale message.

- [ ] **Step 5: Commit**

```bash
git add justfile scripts/tests/test_feature_inventory.py
git commit -m "feat(feature-inventory): just regen + check guard recipes"
```

---

## Task 10: Wiring test — the generator is reachable from the guard

**Files:**
- Modify: `scripts/tests/test_feature_inventory.py`

Per project doctrine ("Every Test Suite Needs a Wiring Test"), prove the generator is actually invoked by the committed `just` guard and writes the committed doc path — not just unit-correct in isolation.

- [ ] **Step 1: Write the failing test**

```python
# append to scripts/tests/test_feature_inventory.py


def test_check_recipe_is_wired_in_justfile():
    """The guard recipe exists and invokes the real generator + the doc path."""
    justfile = (ROOT / "justfile").read_text()
    assert "feature-inventory-check:" in justfile
    assert "regenerate_feature_inventory.py" in justfile
    assert "git diff --quiet docs/feature-inventory.md" in justfile


def test_real_repo_regenerates_clean():
    """End-to-end: the committed manifest verifies and the committed doc is
    already in sync (no drift) against the live registry."""
    from scripts.regenerate_feature_inventory import generate
    rc = generate(repo_root=ROOT)
    assert rc == 0, "committed manifest fails verification against the live repo"
    # doc must be unchanged after regen (committed state is canonical)
    import subprocess
    diff = subprocess.run(
        ["git", "diff", "--stat", "docs/feature-inventory.md"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert diff.stdout.strip() == "", "committed feature-inventory.md is stale"
```

- [ ] **Step 2: Run test to verify it fails (if anything is unwired) then passes**

Run: `cd {{repo root}} && uv run pytest scripts/tests/test_feature_inventory.py -k "wired_in_justfile or regenerates_clean" -v`
Expected: PASS once Tasks 8–9 are committed. If `regenerates_clean` fails, run `just feature-inventory-regen`, commit the doc, and re-run.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_feature_inventory.py
git commit -m "test(feature-inventory): wiring test — generator reachable from guard"
```

---

## After Phase 1

- **Follow-on chore (own tasks):** migrate the remaining `docs/feature-inventory.md` categories into per-category manifests, one at a time, each run through the generator so every stale claim surfaces mechanically. The legacy prose for an un-migrated category stays outside the markers until its manifest lands.
- **Phase 2 plan:** observed-emission capture (`scenarios/feature-evidence/*.yaml`, `just feature-evidence`, `docs/feature-evidence/observed-spans.json`, three-legged `live_wired` rule, freshness guard).
- **Phase 3 plan:** coverage reports (declared-but-never-fired → FAIL; registered-but-never-observed → WARN) wired into CI.
