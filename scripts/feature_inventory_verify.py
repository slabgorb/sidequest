# scripts/feature_inventory_verify.py
"""Evidence verifiers for the feature-inventory generator (Phase 1).

Each function checks one anchor type against the live repo and is pure
(filesystem reads only, no markdown, no orchestration) so it can be unit
tested in isolation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
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
