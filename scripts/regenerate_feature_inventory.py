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


def generate(repo_root: Path = ROOT, span_names: set[str] | None = None) -> int:
    """Load → verify → render → write. Return process exit code."""
    manifest_dir = repo_root / "docs" / "feature-inventory"
    doc = repo_root / "docs" / "feature-inventory.md"
    spans_dir = repo_root / "sidequest-server" / "sidequest" / "telemetry" / "spans"
    if span_names is None:
        span_names = load_span_constants(spans_dir)

    if not manifest_dir.is_dir():
        raise SystemExit(f"manifest dir not found: {manifest_dir}")
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
