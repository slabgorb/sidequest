#!/usr/bin/env python3
"""One-shot migration: add YAML frontmatter to every ADR in docs/adr/ per ADR-088.

Parses existing prose metadata (old `## Status` blocks and new `**Status:**`
bold-key lines), enriches with:
- tags: from CLAUDE.md category groupings (TAG_MAP below)
- implementation-status: from ADR-087 verdict tables (IMPL_STATUS below)
- date: from git log first-commit date
- supersession: from the small curated map below

Writes frontmatter at the top of each file and strips the redundant bold-key
lines. Old `## Status` blocks are also stripped. Body prose is untouched.

Idempotent: skips files already starting with `---\n`.
"""
import re
import subprocess
from pathlib import Path

ADR_DIR = Path(__file__).parent.parent / "docs" / "adr"

# Tag assignments — derived from the CLAUDE.md compact ADR index categories.
# Controlled vocabulary defined in ADR-088.
TAG_MAP: dict[int, list[str]] = {
    **{i: ["core-architecture"] for i in range(1, 8)},
    8: ["prompt-engineering"], 9: ["prompt-engineering"],
    10: ["agent-system"], 11: ["agent-system"], 12: ["agent-system"], 13: ["agent-system"],
    **{i: ["game-systems"] for i in range(14, 26)},
    26: ["frontend-protocol"], 27: ["frontend-protocol"],
    28: ["multiplayer"], 29: ["multiplayer"], 30: ["multiplayer"],
    **{i: ["genre-mechanics"] for i in range(31, 35)},
    35: ["transport-infrastructure"], 38: ["transport-infrastructure"],
    46: ["transport-infrastructure"], 47: ["transport-infrastructure"],
    36: ["multiplayer"], 37: ["multiplayer"],
    39: ["narrator"], 40: ["narrator"], 49: ["narrator"], 52: ["narrator"], 57: ["narrator"],
    41: ["npc-character"], 42: ["npc-character"], 43: ["npc-character"], 53: ["npc-character"],
    44: ["media-audio"], 45: ["media-audio"], 48: ["media-audio"], 50: ["media-audio"],
    51: ["turn-management"],
    54: ["multiplayer", "media-audio"],
    55: ["room-graph"],
    56: ["code-generation", "agent-system"],
    58: ["observability"],
    59: ["code-generation", "agent-system"],
    **{i: ["codebase-decomposition"] for i in range(60, 66)},
    66: ["agent-system", "narrator"],
    67: ["agent-system", "narrator", "narrator-migration"],
    68: ["codebase-decomposition"],
    69: ["code-generation"],
    70: ["media-audio"],
    71: ["room-graph", "game-systems"],
    72: ["codebase-decomposition"],
    73: ["narrator-migration", "narrator"],
    74: ["game-systems", "frontend-protocol"],
    75: ["frontend-protocol"],
    76: ["narrator-migration", "narrator"],
    77: ["game-systems"], 78: ["game-systems"],
    79: ["frontend-protocol"],
    80: ["game-systems", "narrator"],
    81: ["game-systems"],
    82: ["project-lifecycle"],
    83: ["media-audio"], 84: ["media-audio"],
    85: ["project-lifecycle"],
    86: ["media-audio"],
    87: ["project-lifecycle"],
    88: ["project-lifecycle", "codebase-decomposition"],
}

# Implementation-status overrides. Any ADR not in this map defaults to "live"
# (for non-proposed/non-superseded) or derives from status.
# Format: id -> (status, pointer-adr-id or None)
IMPL_STATUS: dict[int, tuple[str, int | None]] = {
    # DRIFT per ADR-087 §5
    17: ("drift", 87), 18: ("drift", 87), 20: ("drift", 87),
    41: ("drift", 87), 42: ("drift", 87), 43: ("drift", 87),
    44: ("drift", 87), 53: ("drift", 87), 59: ("drift", 87),
    69: ("drift", 87),
    # PARTIAL per ADR-087 (Epic 28 VERIFY)
    33: ("partial", 87),
    # DEFERRED — Proposed ADRs not yet implemented
    29: ("deferred", None), 30: ("deferred", None), 34: ("deferred", None),
    65: ("deferred", None), 71: ("deferred", 87), 72: ("deferred", None),
    74: ("deferred", None), 75: ("deferred", None), 76: ("deferred", None),
    77: ("deferred", 87), 78: ("deferred", 87), 81: ("deferred", 87),
    83: ("deferred", None), 86: ("deferred", None),
    87: ("deferred", None), 88: ("deferred", None),
    # NOT-APPLICABLE — principle-layer ADRs with no implementation surface
    2: ("not-applicable", None),
    14: ("not-applicable", None),
    80: ("not-applicable", None),
}

# Supersession — curated from CLAUDE.md index and recent ADR prose.
SUPERSEDED_BY: dict[int, int] = {
    10: 67,  # Intent-based routing → Unified Narrator
    13: 57,  # Lazy JSON → Narrator crunch separation
    32: 70,  # Genre LoRA → Z-Image
    39: 57,  # Narrator structured output → Narrator crunch separation
    56: 59,  # Script tool generators → Monster manual pregen
    84: 70,  # LoRA composition dimension → Z-Image
}
HISTORICAL: set[int] = {54}  # WebRTC voice chat — cut with TTS removal
PROPOSED: set[int] = {29, 30, 34, 65, 71, 72, 74, 75, 76, 77, 78, 81, 83, 86, 87}

# Build reverse map: successor -> [predecessors]
SUPERSEDES: dict[int, list[int]] = {}
for pred, succ in SUPERSEDED_BY.items():
    SUPERSEDES.setdefault(succ, []).append(pred)
for succ in SUPERSEDES:
    SUPERSEDES[succ].sort()


# --- Regexes ---
OLD_STATUS_RE = re.compile(r"^## Status\s*\n+([^\n]+)", re.MULTILINE)
NEW_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*([^\n]+)", re.MULTILINE)
NEW_DATE_RE = re.compile(r"^\*\*Date:\*\*\s*([^\n]+)", re.MULTILINE)
NEW_DECIDERS_RE = re.compile(r"^\*\*Deciders:\*\*\s*([^\n]+)", re.MULTILINE)
NEW_SUPERSEDES_RE = re.compile(r"^\*\*Supersedes:\*\*\s*([^\n]+)", re.MULTILINE)
NEW_RELATED_RE = re.compile(r"^\*\*Relate[sd]?(?:\s+to)?:\*\*\s*([^\n]+)", re.MULTILINE)
H1_RE = re.compile(r"^# ADR-(\d+):\s*(.+)$", re.MULTILINE)
ADR_REF_RE = re.compile(r"ADR[- ]?0*(\d+)")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def get_first_commit_date(filepath: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%aI", "--", str(filepath.name)],
            capture_output=True, text=True, cwd=filepath.parent,
        )
        dates = [d for d in result.stdout.strip().split("\n") if d]
        if dates:
            # First add = last in output (git log is reverse chronological)
            return dates[-1][:10]
    except Exception:
        pass
    return "2025-01-01"


def extract_adr_refs(text: str) -> list[int]:
    return sorted(set(int(m.group(1)) for m in ADR_REF_RE.finditer(text)))


def parse_deciders(text: str) -> list[str]:
    parts = [p.strip() for p in text.split(",")]
    return [p for p in parts if p]


def yaml_quote(s: str) -> str:
    """Quote a string for YAML flow context if it contains special chars."""
    if any(c in s for c in ',:[]{}&*!|>\'"%@`#') or s != s.strip() or not s:
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


def list_flow(items: list) -> str:
    if not items:
        return "[]"
    rendered = []
    for item in items:
        if isinstance(item, str):
            rendered.append(yaml_quote(item))
        else:
            rendered.append(str(item))
    return "[" + ", ".join(rendered) + "]"


def emit_frontmatter(fm: dict) -> str:
    lines = ["---"]
    lines.append(f"id: {fm['id']}")
    title_esc = fm["title"].replace('\\', '\\\\').replace('"', '\\"')
    lines.append(f'title: "{title_esc}"')
    lines.append(f"status: {fm['status']}")
    lines.append(f"date: {fm['date']}")
    lines.append(f"deciders: {list_flow(fm['deciders'])}")
    lines.append(f"supersedes: {list_flow(fm['supersedes'])}")
    sb = fm["superseded-by"]
    lines.append(f"superseded-by: {sb if sb is not None else 'null'}")
    lines.append(f"related: {list_flow(fm['related'])}")
    lines.append(f"tags: {list_flow(fm['tags'])}")
    lines.append(f"implementation-status: {fm['implementation-status']}")
    ip = fm["implementation-pointer"]
    lines.append(f"implementation-pointer: {ip if ip is not None else 'null'}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def migrate_adr(filepath: Path) -> int | None:
    content = filepath.read_text()

    m = re.match(r"(\d+)-", filepath.name)
    if not m:
        return None
    adr_id = int(m.group(1))

    if content.startswith("---\n"):
        print(f"  ADR-{adr_id:03d}: already has frontmatter, skipping")
        return None

    h1 = H1_RE.search(content)
    if not h1:
        print(f"  ADR-{adr_id:03d}: no H1 found, skipping")
        return None
    title = h1.group(2).strip()

    # Determine status
    if adr_id in HISTORICAL:
        status = "historical"
    elif adr_id in SUPERSEDED_BY:
        status = "superseded"
    elif adr_id in PROPOSED:
        status = "proposed"
    else:
        status_text = None
        m2 = NEW_STATUS_RE.search(content)
        if m2:
            status_text = m2.group(1).strip()
        else:
            m2 = OLD_STATUS_RE.search(content)
            if m2:
                status_text = m2.group(1).strip()
        if status_text:
            s = status_text.lower()
            if "superseded" in s:
                status = "superseded"
            elif "proposed" in s:
                status = "proposed"
            elif "historical" in s:
                status = "historical"
            elif "accepted" in s:
                status = "accepted"
            else:
                status = "accepted"
        else:
            status = "accepted"

    # Date
    date = None
    m2 = NEW_DATE_RE.search(content)
    if m2:
        date_m = DATE_RE.search(m2.group(1))
        if date_m:
            date = date_m.group(1)
    if date is None:
        date = get_first_commit_date(filepath)

    # Deciders
    m2 = NEW_DECIDERS_RE.search(content)
    if m2:
        deciders = parse_deciders(m2.group(1))
    else:
        deciders = ["Keith Avery"]

    # Supersedes / superseded-by
    supersedes = SUPERSEDES.get(adr_id, [])
    if not supersedes:
        m2 = NEW_SUPERSEDES_RE.search(content)
        if m2:
            supersedes = extract_adr_refs(m2.group(1))
    superseded_by = SUPERSEDED_BY.get(adr_id)

    # Related
    m2 = NEW_RELATED_RE.search(content)
    related = extract_adr_refs(m2.group(1)) if m2 else []
    related = [r for r in related if r != adr_id and r not in supersedes and r != superseded_by]

    # Tags
    tags = TAG_MAP.get(adr_id, ["core-architecture"])

    # Implementation-status
    if adr_id in IMPL_STATUS:
        impl_status, impl_pointer = IMPL_STATUS[adr_id]
    elif status in ("superseded", "historical"):
        impl_status, impl_pointer = "retired", None
    elif status == "proposed":
        impl_status, impl_pointer = "deferred", None
    else:
        impl_status, impl_pointer = "live", None

    # Consistency enforcement
    if status in ("superseded", "historical"):
        impl_status = "retired"
        impl_pointer = None

    fm = {
        "id": adr_id,
        "title": title,
        "status": status,
        "date": date,
        "deciders": deciders,
        "supersedes": supersedes,
        "superseded-by": superseded_by,
        "related": related,
        "tags": tags,
        "implementation-status": impl_status,
        "implementation-pointer": impl_pointer,
    }

    fm_text = emit_frontmatter(fm)

    # Strip redundant headers
    new_content = content
    # Old-style `## Status\n<value>\n`
    new_content = re.sub(
        r"^## Status\s*\n+[^\n]+\n+", "", new_content, count=1, flags=re.MULTILINE
    )
    # New-style bold-key lines
    new_content = re.sub(
        r"^\*\*(?:Status|Date|Deciders|Supersedes|Relate[sd]?(?:\s+to)?):\*\*[^\n]*\n",
        "", new_content, flags=re.MULTILINE,
    )
    # Collapse runs of blank lines
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)

    final = fm_text + "\n" + new_content.lstrip()
    filepath.write_text(final)
    return adr_id


def main() -> None:
    adrs = sorted(ADR_DIR.glob("[0-9][0-9][0-9]-*.md"))
    migrated = 0
    skipped = 0
    for adr in adrs:
        result = migrate_adr(adr)
        if result is not None:
            migrated += 1
            print(f"  ADR-{result:03d}: migrated")
        else:
            skipped += 1
    print(f"\nMigrated: {migrated}   Skipped: {skipped}   Total: {len(adrs)}")


if __name__ == "__main__":
    main()
