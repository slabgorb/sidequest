#!/usr/bin/env python3
"""Validate ADR frontmatter per ADR-088 schema.

Exits 0 if all ADRs pass; 1 if any ADR has at least one error. Warnings do not
fail the run but are reported. Intended for pre-commit hooks and CI.

Usage:
    python3 scripts/validate_adr_frontmatter.py           # validate all
    python3 scripts/validate_adr_frontmatter.py FILES...  # validate specific files
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from regenerate_adr_indexes import (  # noqa: E402
    ADR_DIR,
    FM_BLOCK_RE,
    parse_yaml_lite,
)

VALID_STATUS = {"proposed", "accepted", "superseded", "deprecated", "historical"}
VALID_IMPL_STATUS = {
    "live", "drift", "partial", "deferred", "not-applicable", "retired",
}
VALID_TAGS = {
    "core-architecture", "prompt-engineering", "agent-system", "game-systems",
    "frontend-protocol", "multiplayer", "transport-infrastructure", "narrator",
    "npc-character", "media-audio", "turn-management", "room-graph",
    "code-generation", "observability", "codebase-decomposition",
    "narrator-migration", "genre-mechanics", "project-lifecycle",
}
REQUIRED_FIELDS = [
    "id", "title", "status", "date", "deciders",
    "supersedes", "superseded-by", "related", "tags",
    "implementation-status", "implementation-pointer",
]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
H1_RE = re.compile(r"^# ADR-\d+:\s*(.+)$", re.MULTILINE)


def validate_file(filepath: Path, all_frontmatters: dict[int, dict]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single ADR file."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        content = filepath.read_text()
    except OSError as e:
        return ([f"cannot read file: {e}"], [])

    m = FM_BLOCK_RE.match(content)
    if not m:
        return (["missing YAML frontmatter block (expected `---\\n...\\n---\\n` at top)"], [])

    fm = parse_yaml_lite(m.group(1))

    # 1. Filename ↔ id
    name_match = re.match(r"(\d+)-", filepath.name)
    if not name_match:
        errors.append("filename does not start with digits")
    else:
        expected_id = int(name_match.group(1))
        fm_id = fm.get("id")
        if fm_id != expected_id:
            errors.append(f"id={fm_id!r} does not match filename prefix {expected_id:03d}")

    # 2. Required fields present
    for f in REQUIRED_FIELDS:
        if f not in fm:
            errors.append(f"missing required field: {f}")

    # 3. Enum validation
    status = fm.get("status")
    if status not in VALID_STATUS:
        errors.append(f"invalid status: {status!r} (must be one of {sorted(VALID_STATUS)})")

    impl = fm.get("implementation-status")
    if impl not in VALID_IMPL_STATUS:
        errors.append(
            f"invalid implementation-status: {impl!r} (must be one of {sorted(VALID_IMPL_STATUS)})"
        )

    tags = fm.get("tags") or []
    if not isinstance(tags, list):
        errors.append(f"tags must be a list, got {type(tags).__name__}")
    elif not tags:
        errors.append("tags must not be empty (at least one tag required)")
    else:
        for t in tags:
            if t not in VALID_TAGS:
                errors.append(f"unknown tag: {t!r} (controlled vocabulary in ADR-088)")

    # 4. Date format
    d = fm.get("date")
    if not isinstance(d, str) or not DATE_RE.match(d):
        errors.append(f"date must be ISO 8601 YYYY-MM-DD, got: {d!r}")

    # 5. Title matches H1 (warn-only)
    h1 = H1_RE.search(content)
    if not h1:
        errors.append("no H1 heading matching '# ADR-XXX: <title>' found in body")
    else:
        h1_title = h1.group(1).strip()
        fm_title = fm.get("title")
        if fm_title != h1_title:
            warnings.append(f"title {fm_title!r} does not match H1 {h1_title!r}")

    # 6. Supersession consistency
    sb = fm.get("superseded-by")
    if status == "superseded" and sb is None:
        errors.append("status=superseded requires superseded-by to be set")
    if status in ("superseded", "historical") and impl != "retired":
        errors.append(
            f"status={status} requires implementation-status=retired, got {impl!r}"
        )
    # Symmetric supersession: if A.superseded-by = B, then B.supersedes must contain A
    if sb is not None:
        predecessor_id = fm.get("id")
        successor_fm = all_frontmatters.get(sb)
        if successor_fm is None:
            errors.append(
                f"superseded-by references ADR-{sb:03d} which does not exist"
            )
        else:
            succ_supersedes = successor_fm.get("supersedes") or []
            if predecessor_id not in succ_supersedes:
                errors.append(
                    f"supersession not symmetric: "
                    f"this ADR says superseded-by={sb}, "
                    f"but ADR-{sb:03d}.supersedes={succ_supersedes} does not include {predecessor_id}"
                )

    # Reverse check: if this ADR supersedes X, X.superseded-by must equal this.id
    my_id = fm.get("id")
    for pred in (fm.get("supersedes") or []):
        pred_fm = all_frontmatters.get(pred)
        if pred_fm is None:
            errors.append(f"supersedes references ADR-{pred:03d} which does not exist")
            continue
        pred_sb = pred_fm.get("superseded-by")
        if pred_sb != my_id:
            errors.append(
                f"supersession not symmetric: "
                f"this ADR says supersedes {pred}, "
                f"but ADR-{pred:03d}.superseded-by={pred_sb!r} (expected {my_id})"
            )

    # 7. Implementation-pointer required for drift / partial
    # (deferred allows null — many Proposed ADRs have no restoration plan yet)
    ptr = fm.get("implementation-pointer")
    if impl in ("drift", "partial") and ptr is None:
        errors.append(
            f"implementation-status={impl} requires implementation-pointer to be set"
        )

    return (errors, warnings)


def load_all_frontmatters(adr_dir: Path) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for p in adr_dir.glob("[0-9][0-9][0-9]-*.md"):
        try:
            content = p.read_text()
        except OSError:
            continue
        m = FM_BLOCK_RE.match(content)
        if not m:
            continue
        fm = parse_yaml_lite(m.group(1))
        adr_id = fm.get("id")
        if isinstance(adr_id, int):
            out[adr_id] = fm
    return out


def main() -> int:
    # Determine which files to validate
    if len(sys.argv) > 1:
        # Specific files — typically from pre-commit hook
        targets = [Path(arg).resolve() for arg in sys.argv[1:]]
        # Filter to only ADR files under docs/adr/
        targets = [
            p for p in targets
            if p.is_file()
            and p.parent == ADR_DIR.resolve()
            and re.match(r"\d{3}-.*\.md$", p.name)
        ]
    else:
        targets = sorted(ADR_DIR.glob("[0-9][0-9][0-9]-*.md"))

    if not targets:
        print("No ADR files to validate.")
        return 0

    # Load full frontmatter set for cross-reference checks (supersession symmetry, etc.)
    all_fm = load_all_frontmatters(ADR_DIR)

    total_errors = 0
    total_warnings = 0
    files_with_errors = 0

    for filepath in targets:
        errors, warnings = validate_file(filepath, all_fm)
        if errors or warnings:
            print(f"{filepath.relative_to(ADR_DIR.parent.parent)}:")
            for e in errors:
                print(f"  ERROR: {e}")
            for w in warnings:
                print(f"  WARN:  {w}")
        if errors:
            files_with_errors += 1
        total_errors += len(errors)
        total_warnings += len(warnings)

    print()
    if total_errors:
        print(
            f"FAIL: {total_errors} error(s) in {files_with_errors} file(s), "
            f"{total_warnings} warning(s). Fix errors before commit."
        )
        return 1
    elif total_warnings:
        print(f"OK: {total_warnings} warning(s), 0 errors.")
        return 0
    else:
        print(f"OK: {len(targets)} ADR file(s) validated, 0 errors.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
