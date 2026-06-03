# scripts/feature_inventory_verify.py
"""Evidence verifiers for the feature-inventory generator (Phase 1).

Each function checks one anchor type against the live repo and is pure
(filesystem reads only, no markdown, no orchestration) so it can be unit
tested in isolation.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml  # PyYAML — available in the orchestrator uv env (used by render_common)

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
