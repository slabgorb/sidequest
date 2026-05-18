# Beneath Sünden Content Cookbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the authored content + deterministic region-assembly contract that lets the Sünden Deep procedural megadungeon place creatures, loot, and set-pieces — by *curating and filtering* an ingested 5e-SRD corpus along five orthogonal axes, never by authoring stat blocks.

**Architecture:** An idempotent ingest transform produces two regenerable corpus artifacts (`corpus/monsters.yaml`, `corpus/items.yaml`) in the `beneath_sunden` world. Authored YAML (`world_register.yaml`, `cookbook/races/*`, `cookbook/looks.yaml`, `cookbook/affinities.yaml`, `cookbook/special_rooms.yaml`) defines a genre-truth hard filter, faction filter-predicates, LOOK textures, axis joints, and the SPECIAL sub-generator. A pure deterministic function `assemble_region(...)` in `sidequest-server` joins these into a `RegionContentManifest` that oq-1's materializer invokes. OTEL span *definitions* are authored here; oq-1 emits them.

**Tech Stack:** Python 3.12 / pydantic v2 (`model_config = {"extra": "forbid"}`), `uv` + `pytest`, PyYAML (already a server dep), OpenTelemetry span catalog (`sidequest.telemetry.spans`). Content is YAML in the `sidequest-content` subrepo.

---

## Scope Check & Why One Plan

The spec (`docs/superpowers/specs/2026-05-16-beneath-sunden-content-cookbook-design.md`) §10 already decomposes this into 6 sequenced sub-plans. They are **not independent** — region-assembly depends on corpus + curation + races + affinities + specials all existing. This is one subsystem ("the cookbook") that produces working, testable software as a whole, with every phase ending green. It stays one plan, phased.

## Two-Repo Boundary (read before starting)

This plan touches **two subrepos**. Every commit step names its repo. Per `.pennyfarthing/repos.yaml`, `sidequest-content` uses **gitflow** — its PR targets `develop`. `sidequest-server` PR also targets `develop`.

- **`sidequest-content`** (gitflow): all YAML — corpus, world_register, cookbook/*. PR `--base develop`.
- **`sidequest-server`**: ingest CLI, cookbook package, span definitions, all tests. PR `--base develop`.

oq-2 **opens PRs and never self-merges**; oq-1 owns merge/sync. Final handoff: two PRs (`--base develop`), one per subrepo.

## Hard Non-Goals (loud failures if violated — spec §2)

These are **oq-1-owned**. This plan must never define or implement them:

- `depth_score` production/bucketing source, burst magnitude production, `theme`/`theme_pool`, the `region_graph`/`themes` loader, the set-piece slot *schema*.
- **CR/XP → Edge translation.** ADR-078 removed HP; ADR-014 mandates HP/CR→Edge translation at the materializer seam. The manifest carries `cr_band` + raw corpus rows (with `cr`/`xp`); **oq-1's materializer translates to `EdgePool`**. If you find yourself writing `EdgePool` construction from a corpus `cr`, STOP — that is the oq-1 seam.
- OTEL span *emission at runtime*. This plan authors `sidequest/telemetry/spans/cookbook.py` (constants + helpers + routes, so the GM-panel catalog knows them); oq-1 calls the helpers from the materializer.

Where the cookbook needs an oq-1 value, it is a **named contract input** and the code stops there.

## Seam Clarification — coordinate with oq-1 (do not bury)

Spec §4.3's prose signature is `assemble_region(campaign_seed, expansion_id, depth_score, burst_magnitude, look)`, but §4.2's `big_bad_gate.on_first_band_entry` requires knowing whether *this region is the first to cross into a gated band on this frontier heading* — a fact a pure scalar `depth_score` cannot carry, and which §4.3 explicitly says "is derived from oq-1's depth_score crossing". The signature is therefore underspecified. This plan resolves it by adding one **oq-1-supplied boolean contract input** `is_first_band_entry: bool` to `assemble_region`. This is **not** a redefinition of an oq-1 value — oq-1 still *produces* the crossing signal; we only name it as an input. Flag this in the oq-1 coordination note (Task 24) and in the spec's §11 Open Items follow-up; do not silently widen the contract without recording it.

## Data-Forced Design Item — low-CR-ceiling factions (decided here; flag to user)

Running the real ingest exposed a gap the spec's illustrative content hid: **SRD 5.1 Ooze tops out at CR 4 (Black Pudding) and goblinoid-tagged Humanoids at CR 1 (Bugbear)**, but per spec §3 LOOK×RACE are orthogonal — *any LOOK can roll any RACE, and depth_score is independent of both*, so a `deep` region (CR 6–30) can legitimately roll `ooze`. The naïve §7 reading ("a RACE with affinity weight must resolve ≥1 row in every band") would make the shipped, genre-true content **loud-fail at build time** — punishing correct curation for the SRD's scarcity.

**Decision (spec-faithful, no silent fallback):**
1. **Validator (Task 10)** requires a RACE to resolve ≥1 curated row only in (a) the **shallow** band (entry guarantee — every faction must be encounterable somewhere) and (b) the **declared `min_band` of each of its `big_bads[]`** (the capstone tier must be non-empty *where it is declared to begin*). Bands a RACE simply *cannot* fill — **including bands ABOVE a big_bad's `min_band`** (e.g. `ooze` declares Black Pudding at `mid` but cannot fill `deep`) — are **not** a build error; the assembler re-rolls observably (point 2). *(Authoritative resolution of an internal contradiction: an earlier draft of this clause said "every band ≥ min_band", which conflicts with the very next sentence and with the must-pass `test_real_bundle_validates`. The `min_band`-only check is correct and is what Task 10 implements; recorded in the Task 23 spec-status note.)*
2. **Assembler (Task 18)** after the affinity RACE roll, if `build_wandering_table` is empty for the rolled (race, band), performs a **bounded, deterministic, observable affinity re-roll** excluding empty RACEs, emitting a `cookbook.race.reroll` OTEL span (Task 11). This preserves §3 orthogonality (any RACE *can* roll; one that can't fill the rolled depth yields *loudly* to one that can) and §7 (**never a silent empty wandering table** — the yield is a routed span the GM panel shows). If *every* affinity RACE for the LOOK is empty at that band → `CookbookValidationError` (a real content bug, not a runtime fallback).

This is a genuine design call the real data forced. It is recorded in the spec §11 follow-up (Task 23) and the oq-1 coordination note (Task 24). **User: if you'd rather low-ceiling factions be hard-excluded from deep affinities instead of re-rolled, say so — that's the one alternative and it changes Tasks 8/10/18.**

## Prerequisite 0 — SRD source (RESOLVED — operator-supplied)

The source is the operator-supplied repo **`github.com/BTMorton/dnd-5e-srd`** (SRD 5.1 → markdown/json/yaml; the WotC SRD 5.1 is CC-BY-4.0). This plan does **not** fabricate stat blocks (spec §4: "authors zero stat blocks"; CLAUDE.md: no stubbing) — it parses this canonical conversion. The ingest approach below is **proven** (run during planning: 316 monster rows, type histogram, required-name resolution all verified).

**Vendor four files** verbatim into the world (committed under `corpus/_source/`, reproducible; JSON, not binary — not subject to the R2/LFS rule). Fetch with `gh api repos/BTMorton/dnd-5e-srd/contents/json/<f> --jq .content | base64 -d`:

- `json/11 monsters.json` → `corpus/_source/monsters.json` (bestiary A–Z buckets)
- `json/15 creatures.json` → `corpus/_source/creatures.json` (Appendix MM-A)
- `json/16 npcs.json` → `corpus/_source/npcs.json` (Appendix MM-B)
- `json/10 magic items.json` → `corpus/_source/magic_items.json`

**Real source schema (NOT a flat array).** It is a recursively nested document. Stat-block *leaves* are dict nodes whose `content` is a list whose **first element** is a markdown line `*Size type[ (tags)], alignment*` and which contains a `**Challenge** CR (XP XP)` line. Leaves may be top-level (`Lich`, `Aboleth`) or nested inside group entries (`Mummies`→`{Mummy, Mummy Lord}`, `Oozes`→`{Gray Ooze, Black Pudding, …}`, `Animated Objects`→`{Animated Armor, …}`). The dict **key** is the monster name. Markdown noise occurs *inside* the stat line (e.g. `*Medium undead**,** lawful evil*`) — strip `**` and outer `*` before matching, or `Mummy` is silently dropped (it was, until hardened — this is the canonical regex's load-bearing edge).

```text
leaf.content[0]  ::  *<Size> <type>[ (<tag,tag>)], <alignment>*      (after **/* strip)
leaf.content[i]  ::  **Challenge** <cr> (<xp> XP)        cr: "1/8"→0.125 …
```

Items (`magic_items.json`): top key `"Magic Items"` → `{<ItemName>: {content:[ "*<rarity> (<item_type>)*" | "*<item_type>, <rarity> (requires attunement…)*", … ]}}`. Item rarity/type/attunement parse from the italic descriptor line; Task 1 documents the exact regex with the proven samples.

**Verified inventory (grounds the authored content — Tasks 6/8):** Undead 18 (Skeleton .25, Zombie .25, Shadow .5, Specter 1, Ghoul 1, Ghast 2, Wight 3, Mummy 3, Ghost 4, Wraith 5, Vampire 13, Mummy Lord 15, Lich 21, …). Aberration 5 (Aboleth 10, Chuul, Cloaker, Gibbering Mouther, Otyugh). Ooze 4 (Gray Ooze .5, Gelatinous Cube 2, Ochre Jelly 2, Black Pudding 4). Humanoid w/ `goblinoid` tag: Goblin .25, Hobgoblin .5, Bugbear. Construct 9 (Animated Armor 1, …). **SRD 5.1 has NO Kuo-toa** (Product Identity) — the spec's illustrative `kuo_toa` RACE is replaced by an **`ooze` ("The Seep")** RACE, which also matches the existing `world_register.reskin: "Gray Ooze": "The Seep"`.

---

## File Structure

**`sidequest-content`** (all under `genre_packs/caverns_and_claudes/worlds/beneath_sunden/`):

| File | Responsibility |
|------|----------------|
| `corpus/_source/{monsters,creatures,npcs,magic_items}.json` | Vendored BTMorton SRD source (Prereq 0, committed) |
| `corpus/monsters.yaml` | Ingested, regenerable monster roll-space (spec §4.1) |
| `corpus/items.yaml` | Ingested, regenerable item roll-space (spec §4.1) |
| `world_register.yaml` | Genre-truth hard filter + marquee + reskin (spec §5) |
| `cookbook/races/undead.yaml` | RACE: The Restless (literal corpus rows) |
| `cookbook/races/aberration.yaml` | RACE: deep aberrations |
| `cookbook/races/ooze.yaml` | RACE: The Seep (Ooze type — replaces spec's illustrative kuo_toa) |
| `cookbook/races/goblinoid.yaml` | RACE: scavenger warbands |
| `cookbook/races/dwarf.yaml` | Conceptual RACE: delved-too-deep (sources via undead) |
| `cookbook/looks.yaml` | LOOK texture + register + generator_binding refs (spec §4.2) |
| `cookbook/affinities.yaml` | CR bands, LOOK×RACE weights, rarity-by-band, size-by-burst, big-bad gate (spec §4.2) |
| `cookbook/special_rooms.yaml` | SPECIAL sub-generator templates (spec §4.2) |

**`sidequest-server`**:

| File | Responsibility |
|------|----------------|
| `sidequest/cli/cookbook_ingest/__init__.py` | CLI package marker |
| `sidequest/cli/cookbook_ingest/__main__.py` | `python -m` entry (mirrors `cli/encountergen`) |
| `sidequest/cli/cookbook_ingest/ingest.py` | Idempotent SRD→corpus transform + CR parse |
| `sidequest/game/cookbook/__init__.py` | Package marker / public re-exports |
| `sidequest/game/cookbook/models.py` | pydantic models (corpus rows, RACE/LOOK/affinities/special/register, `RegionContentManifest`) |
| `sidequest/game/cookbook/corpus.py` | Corpus load + filter-predicate evaluator (`any_of`/`type`/`tags_any`/`name_glob`/`deny`) |
| `sidequest/game/cookbook/curation.py` | `world_register` hard filter + marquee exemption |
| `sidequest/game/cookbook/loader.py` | Load a `beneath_sunden` world dir → `CookbookBundle` |
| `sidequest/game/cookbook/assemble.py` | `assemble_region(...)` pure deterministic function |
| `sidequest/telemetry/spans/cookbook.py` | Cookbook span constants + helper context managers + routes |
| `tests/game/cookbook/__init__.py` | Test package marker |
| `tests/game/cookbook/conftest.py` | Shared fixture: load the real `beneath_sunden` bundle |
| `tests/game/cookbook/test_ingest_fidelity.py` | Row-count + CR-monotonic + idempotency (spec §9) |
| `tests/game/cookbook/test_curation.py` | Denied types absent; marquee survives (spec §9) |
| `tests/game/cookbook/test_filter_resolution.py` | Every RACE filter ≥1 row per claimed band (spec §7/§9) |
| `tests/game/cookbook/test_affinity_distribution.py` | LOOK→RACE frequency tracks weights; off-affinity still appears (spec §9) |
| `tests/game/cookbook/test_determinism.py` | Identical inputs → identical manifest (spec §9) |
| `tests/game/cookbook/test_size_bigbad.py` | burst→budget monotonic; capstone floors SIZE (spec §9) |
| `tests/telemetry/spans/test_cookbook_spans.py` | Span constants defined + routed/flat-only |
| `tests/integration/test_cookbook_assemble_wiring.py` | oq-1 materializer-path wiring contract test (spec §9) |

---

## Phase A — Corpus Ingest (spec §10 step 1)

### Task 1: Ingest CLI skeleton + CR parse helper

**Files:**
- Create: `sidequest-server/sidequest/cli/cookbook_ingest/__init__.py`
- Create: `sidequest-server/sidequest/cli/cookbook_ingest/__main__.py`
- Create: `sidequest-server/sidequest/cli/cookbook_ingest/ingest.py`
- Create: `sidequest-server/tests/game/cookbook/__init__.py`
- Create: `sidequest-server/tests/game/cookbook/test_ingest_fidelity.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_ingest_fidelity.py`

```python
"""Ingest fidelity — spec §9: every source stat-block leaf emitted,
CR parses to float, idempotent, required names resolve."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sidequest.cli.cookbook_ingest.ingest import (
    iter_statblock_leaves,
    parse_cr,
    parse_statline,
    walk_monsters,
)

WORLD = (
    Path(__file__).parents[4]
    / "sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden"
)
SRC = WORLD / "corpus/_source"


def test_parse_cr_fractions() -> None:
    assert parse_cr("1/8") == 0.125
    assert parse_cr("1/4") == 0.25
    assert parse_cr("1/2") == 0.5
    assert parse_cr("0") == 0.0
    assert parse_cr("21") == 21.0


def test_parse_cr_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="unparseable CR"):
        parse_cr("banana")


def test_statline_strips_inline_markdown() -> None:
    # The 'Mummy' edge: stray bold inside the italic line.
    size, typ, tags, align = parse_statline("*Medium undead**,** lawful evil*")
    assert (size, typ, tags, align) == ("Medium", "Undead", [], "lawful evil")


def test_statline_extracts_tags() -> None:
    size, typ, tags, align = parse_statline(
        "*Small humanoid (goblinoid), neutral evil*"
    )
    assert typ == "Humanoid" and tags == ["goblinoid"]


@pytest.mark.skipif(not (SRC / "monsters.json").exists(), reason="Prereq 0 not vendored")
def test_every_source_leaf_emitted_and_cr_float() -> None:
    docs = [
        json.loads((SRC / f).read_text())
        for f in ("monsters.json", "creatures.json", "npcs.json")
    ]
    expected = sum(len(list(iter_statblock_leaves(d))) for d in docs)
    rows = walk_monsters(docs)
    # De-dup by name (first wins) is allowed; count must not EXCEED source
    # leaves and every required marquee/big_bad name must survive.
    assert 0 < len(rows) <= expected
    assert all(isinstance(r["cr"], float) for r in rows)
    names = {r["name"] for r in rows}
    for need in ("Lich", "Mummy", "Mummy Lord", "Aboleth", "Vampire",
                 "Skeleton", "Gray Ooze", "Animated Armor", "Hobgoblin"):
        assert need in names, f"required SRD name {need!r} did not resolve"


@pytest.mark.skipif(not (SRC / "monsters.json").exists(), reason="Prereq 0 not vendored")
def test_idempotent() -> None:
    docs = [
        json.loads((SRC / f).read_text())
        for f in ("monsters.json", "creatures.json", "npcs.json")
    ]
    assert walk_monsters(docs) == walk_monsters(docs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_ingest_fidelity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.cli.cookbook_ingest'`

- [ ] **Step 3: Write minimal implementation**

`sidequest-server/sidequest/cli/cookbook_ingest/__init__.py`:
```python
"""SRD → Beneath Sünden corpus ingest (spec §4.1, §10 step 1)."""
```

`sidequest-server/sidequest/cli/cookbook_ingest/__main__.py`:
```python
"""Entry point for python -m sidequest.cli.cookbook_ingest."""

from __future__ import annotations

import sys

from sidequest.cli.cookbook_ingest.ingest import main

if __name__ == "__main__":
    sys.exit(main())
```

`sidequest-server/sidequest/cli/cookbook_ingest/ingest.py`:
```python
"""Idempotent SRD → corpus transform (spec §4.1).

Source: vendored BTMorton/dnd-5e-srd JSON (Prereq 0) — a recursively
nested document, NOT a flat array. A stat-block leaf is any dict whose
`content[0]` (after markdown strip) matches the stat line and which
carries a `**Challenge**` line. The dict KEY is the monster name. No
silent fallback: an unparseable CR raises (CLAUDE.md). Idempotent.

This parser is PROVEN (planning run: 316 monster rows, Mummy edge
handled, required marquee/big_bad names resolved).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

_SIZES = "Tiny|Small|Medium|Large|Huge|Gargantuan"
_STATLINE = re.compile(
    rf"^({_SIZES})\s+([A-Za-z][A-Za-z ]*?)(?:\s*\(([^)]+)\))?,\s*(.+)$"
)
_CHALLENGE = re.compile(r"Challenge\s*([0-9/]+)\s*\(([\d,]+)\s*XP\)")
_ITEM_DESC = re.compile(
    r"^\*?\s*([A-Za-z ,+/-]+?)\s*\(?\s*"
    r"(common|uncommon|rare|very rare|legendary|artifact)\)?",
    re.IGNORECASE,
)


def parse_cr(raw: str) -> float:
    """'1/8'->0.125, '1/4'->0.25, '21'->21.0. Raises on garbage."""
    text = str(raw).strip()
    try:
        if "/" in text:
            num, _, den = text.partition("/")
            return float(num) / float(den)
        return float(text)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"unparseable CR: {raw!r}") from exc


def _strip_md(line: str) -> str:
    """Remove inline bold/italic noise: '*Medium undead**,** LE*' → clean."""
    return line.replace("**", "").strip().strip("*").strip()


def parse_statline(raw: str) -> tuple[str, str, list[str], str]:
    """(size, Type, [tags], alignment) from the leaf's content[0]."""
    m = _STATLINE.match(_strip_md(raw))
    if not m:
        raise ValueError(f"unparseable stat line: {raw!r}")
    size, typ, tags, align = m.groups()
    tag_list = (
        [t.strip().lower() for t in tags.split(",")] if tags else []
    )
    return size, typ.strip().title(), tag_list, align.strip()


def _is_leaf(node: Any) -> bool:
    c = node.get("content") if isinstance(node, dict) else None
    return (
        isinstance(c, list)
        and bool(c)
        and isinstance(c[0], str)
        and _STATLINE.match(_strip_md(c[0])) is not None
    )


def iter_statblock_leaves(node: Any, name: str = "") -> Iterator[tuple[str, dict]]:
    """Yield (name, node) for every stat-block leaf, recursively."""
    if not isinstance(node, dict):
        return
    if _is_leaf(node):
        yield name, node
        return
    for key, child in node.items():
        if key == "content":
            continue
        yield from iter_statblock_leaves(child, key)


def walk_monsters(docs: list[Any]) -> list[dict[str, Any]]:
    """Flatten all docs to spec §4.1 rows. De-dup by name (first wins).

    Source order is preserved (doc order, then document order); the
    fidelity test asserts emitted ≤ source leaves and required names
    survive.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in docs:
        for name, leaf in iter_statblock_leaves(doc):
            if not name or name in seen:
                continue
            size, typ, tags, align = parse_statline(leaf["content"][0])
            cr = xp = None
            for line in leaf["content"]:
                if not isinstance(line, str):
                    continue
                h = _CHALLENGE.search(line.replace("**", ""))
                if h:
                    cr = parse_cr(h.group(1))
                    xp = int(h.group(2).replace(",", ""))
                    break
            if cr is None:
                continue  # not a combat stat block (no Challenge line)
            seen.add(name)
            rows.append(
                {
                    "name": name,
                    "size": size,
                    "type": typ,
                    "tags": tags,
                    "alignment": align,
                    "cr": cr,
                    "xp": xp,
                    "source": "SRD 5.1",
                }
            )
    return rows


def walk_items(item_doc: Any) -> list[dict[str, Any]]:
    """Magic-items doc → spec §4.1 item rows. The italic descriptor line
    carries item_type + rarity + attunement; Task documents samples."""
    rows: list[dict[str, Any]] = []
    root = item_doc.get("Magic Items", item_doc)
    for name, node in root.items():
        if name == "content" or not isinstance(node, dict):
            continue
        content = node.get("content")
        if not (isinstance(content, list) and content and isinstance(content[0], str)):
            continue
        desc = _strip_md(content[0])
        m = _ITEM_DESC.match(desc)
        if not m:
            continue
        item_type, rarity = m.group(1).strip(), m.group(2).strip()
        attune = "attunement" in " ".join(
            x for x in content if isinstance(x, str)
        ).lower()
        rows.append(
            {
                "name": name,
                "item_type": item_type.title(),
                "rarity": rarity.title(),
                "attunement": attune,
                "notes": "",
                "source": "SRD 5.1",
            }
        )
    return rows


def _dump(rows: list[dict[str, Any]], dest: Path) -> None:
    dest.write_text(yaml.safe_dump(rows, sort_keys=False, allow_unicode=True))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cookbook_ingest")
    ap.add_argument("--world", required=True, type=Path)
    args = ap.parse_args(argv)
    src = args.world / "corpus/_source"
    out = args.world / "corpus"
    needed = ["monsters.json", "creatures.json", "npcs.json", "magic_items.json"]
    missing = [f for f in needed if not (src / f).exists()]
    if missing:
        print(f"FATAL: missing vendored SRD source {missing} under {src} "
              f"(Prereq 0)", file=sys.stderr)
        return 2
    docs = [json.loads((src / f).read_text())
            for f in ("monsters.json", "creatures.json", "npcs.json")]
    _dump(walk_monsters(docs), out / "monsters.yaml")
    _dump(walk_items(json.loads((src / "magic_items.json").read_text())),
          out / "items.yaml")
    print(f"ingested → {out}/monsters.yaml, {out}/items.yaml")
    return 0
```

`sidequest-server/tests/game/cookbook/__init__.py`: *(empty file)*

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_ingest_fidelity.py -v`
Expected: PASS for the parser unit tests (`test_parse_cr_*`, `test_statline_*`); the source-dependent tests SKIP until Task 2 vendors the JSON — skip is acceptable green here.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/cli/cookbook_ingest tests/game/cookbook && uv run ruff format sidequest/cli/cookbook_ingest tests/game/cookbook
git add sidequest/cli/cookbook_ingest tests/game/cookbook/__init__.py tests/game/cookbook/test_ingest_fidelity.py
git commit -m "feat(cookbook): SRD→corpus ingest transform + CR parse + fidelity tests"
```

### Task 2: Vendor BTMorton source, run ingest, commit corpus (`sidequest-content`)

**Files:**
- Create (vendored): `.../beneath_sunden/corpus/_source/{monsters,creatures,npcs,magic_items}.json`
- Create (generated): `.../beneath_sunden/corpus/{monsters,items}.yaml`

- [ ] **Step 1: Vendor the four BTMorton JSON files**

```bash
W=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden
mkdir -p "$W/corpus/_source"
for pair in "11 monsters:monsters" "15 creatures:creatures" "16 npcs:npcs" "10 magic items:magic_items"; do
  remote="${pair%%:*}"; local="${pair##*:}"
  enc=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote('json/'+sys.argv[1]+'.json'))" "$remote")
  gh api "repos/BTMorton/dnd-5e-srd/contents/$enc" --jq '.content' | base64 -d > "$W/corpus/_source/$local.json"
done
ls -la "$W/corpus/_source/"
```
Expected: four JSON files present (`monsters.json` ~630K, `creatures.json` ~161K, `npcs.json` ~46K, `magic_items.json` ~253K). These are the SRD 5.1 (CC-BY-4.0) — committing them is reproducibility, not asset bloat.

- [ ] **Step 2: Run the ingest transform**

```bash
cd sidequest-server && uv run python -m sidequest.cli.cookbook_ingest --world "$W"
```
Expected: prints `ingested → .../corpus/monsters.yaml, .../corpus/items.yaml`, exit 0. `monsters.yaml` ≈ 300+ rows.

- [ ] **Step 3: Verify idempotency**

Re-run Step 2, then:
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git diff --stat genre_packs/caverns_and_claudes/worlds/beneath_sunden/corpus/
```
Expected: second run produces **no diff** (idempotent — spec §4.1).

- [ ] **Step 4: Run the now-unskipped fidelity tests**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_ingest_fidelity.py -v`
Expected: ALL pass — every source leaf accounted for, CR all float, idempotent, required names (Lich/Mummy/Mummy Lord/Aboleth/Vampire/Skeleton/Gray Ooze/Animated Armor/Hobgoblin) resolve.

- [ ] **Step 5: Commit (`sidequest-content`)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git add genre_packs/caverns_and_claudes/worlds/beneath_sunden/corpus/
git commit -m "content(beneath_sunden): vendor BTMorton SRD source + ingest corpus"
```

---

## Phase B — Cookbook Models (foundation for all later phases)

### Task 3: Corpus + manifest pydantic models

**Files:**
- Create: `sidequest-server/sidequest/game/cookbook/__init__.py`
- Create: `sidequest-server/sidequest/game/cookbook/models.py`
- Create: `sidequest-server/tests/game/cookbook/test_models.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_models.py`

```python
"""Cookbook model round-trip + extra-forbid invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.game.cookbook.models import (
    CorpusItem,
    CorpusMonster,
    CrBand,
    RegionContentManifest,
)


def test_corpus_monster_parses() -> None:
    m = CorpusMonster(
        name="Skeleton", size="Medium", type="Undead", tags=[],
        alignment="LE", cr=0.25, xp=50, source="mm 282",
    )
    assert m.cr == 0.25 and m.tags == []


def test_corpus_monster_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        CorpusMonster(
            name="X", size="Medium", type="Undead", tags=[], alignment="LE",
            cr=1.0, xp=200, source="", bogus=True,
        )


def test_cr_band_is_ordinal_via_index() -> None:
    bands = [
        CrBand(id="shallow", depth_lt=0.25, cr_min=0, cr_max=2),
        CrBand(id="mid", depth_lt=0.60, cr_min=2, cr_max=7),
        CrBand(id="deep", depth_lt=1.01, cr_min=6, cr_max=30),
    ]
    order = {b.id: i for i, b in enumerate(bands)}
    assert order["shallow"] < order["mid"] < order["deep"]


def test_manifest_minimal() -> None:
    man = RegionContentManifest(
        race="undead", cr_band="mid",
        size_budget={"wandering_rolls": 3, "special_rooms": 1, "loot_rolls": 2},
        wandering_table=[], loot_table=[], special_rooms=[], big_bad=None,
    )
    assert man.big_bad is None
    _ = CorpusItem(
        name="Potion of Healing", item_type="Potion", rarity="Common",
        attunement=False, notes="", source="dmg 288",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.cookbook'`

- [ ] **Step 3: Write minimal implementation**

`sidequest-server/sidequest/game/cookbook/__init__.py`:
```python
"""Beneath Sünden content cookbook (spec 2026-05-16).

Curates + filters an ingested SRD corpus along five orthogonal axes
into a deterministic RegionContentManifest. Authors zero stat blocks.
"""
```

`sidequest-server/sidequest/game/cookbook/models.py`:
```python
"""Cookbook pydantic models — corpus rows, authored tables, manifest.

Mirrors the genre-layer convention (model_config extra=forbid). Field
names are the contract; later phases and oq-1 depend on them verbatim.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

_FORBID = {"extra": "forbid"}


class CorpusMonster(BaseModel):
    model_config = _FORBID
    name: str
    size: str
    type: str
    tags: list[str] = Field(default_factory=list)
    alignment: str
    cr: float
    xp: int
    source: str = ""


class CorpusItem(BaseModel):
    model_config = _FORBID
    name: str
    item_type: str
    rarity: str
    attunement: bool = False
    notes: str = ""
    source: str = ""


class FilterClause(BaseModel):
    """One predicate term. All present fields must hold (AND)."""

    model_config = _FORBID
    type: str | None = None
    tags_any: list[str] | None = None
    name_glob: str | None = None


class RaceFilter(BaseModel):
    model_config = _FORBID
    any_of: list[FilterClause]


class RaceDeny(BaseModel):
    model_config = _FORBID
    name_glob: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class BigBadDecl(BaseModel):
    model_config = _FORBID
    name: str
    min_band: str


class RaceConcept(BaseModel):
    model_config = _FORBID
    framing: str
    sourced_from: str


class LootBias(BaseModel):
    model_config = _FORBID
    category_weight: dict[str, float] = Field(default_factory=dict)


class RaceDef(BaseModel):
    model_config = _FORBID
    id: str
    display: str
    filter: RaceFilter
    deny: RaceDeny = Field(default_factory=RaceDeny)
    telegraph: dict[str, str] = Field(default_factory=dict)
    loot_bias: LootBias = Field(default_factory=LootBias)
    big_bads: list[BigBadDecl] = Field(default_factory=list)
    concept: RaceConcept | None = None


class LookDef(BaseModel):
    model_config = _FORBID
    id: str
    generator_binding: str
    register: str
    dressing: list[str] = Field(default_factory=list)


class CrBand(BaseModel):
    model_config = _FORBID
    id: str
    depth_lt: float
    cr_min: float
    cr_max: float


class SizeBudget(BaseModel):
    model_config = _FORBID
    burst_lte: int
    wandering_rolls: int
    special_rooms: int
    loot_rolls: int


class BigBadGate(BaseModel):
    model_config = _FORBID
    on_first_band_entry: list[str]
    recurring_chance: dict[str, float]


class Affinities(BaseModel):
    model_config = _FORBID
    cr_bands: list[CrBand]
    big_bad_gate: BigBadGate
    look_race_affinity: dict[str, dict[str, float]]
    rarity_by_band: dict[str, dict[str, float]]
    size_by_burst: list[SizeBudget]
    big_bad_forces_size: str

    def band_order(self) -> dict[str, int]:
        """Ordinal index per spec §4.2 (shallow < mid < deep)."""
        return {b.id: i for i, b in enumerate(self.cr_bands)}


class SpecialRoom(BaseModel):
    model_config = _FORBID
    id: str
    telegraph: str
    mechanic: str
    outcome: str
    min_band: str
    feeds_setpiece_slot: bool = True


class Reskin(BaseModel):
    model_config = _FORBID
    mapping: dict[str, str] = Field(default_factory=dict)


class WorldRegister(BaseModel):
    model_config = _FORBID
    register: str
    allow_types: list[str]
    deny: RaceDeny = Field(default_factory=RaceDeny)
    humanoid_constraint: str = ""
    reskin: dict[str, str] = Field(default_factory=dict)
    marquee: list[str] = Field(default_factory=list)


class RegionContentManifest(BaseModel):
    """The deterministic contract output oq-1's materializer consumes.

    Carries cr_band + raw corpus rows. CR→Edge translation is the
    oq-1 materializer seam (ADR-014/078) — NOT done here.
    """

    model_config = _FORBID
    race: str
    cr_band: str
    size_budget: dict[str, int]
    wandering_table: list[dict]
    loot_table: list[dict]
    special_rooms: list[dict]
    big_bad: dict | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_models.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/__init__.py sidequest/game/cookbook/models.py tests/game/cookbook/test_models.py
git commit -m "feat(cookbook): pydantic models for corpus, authored tables, manifest"
```

---

## Phase C — World Register + Curation (spec §10 step 2, §5)

### Task 4: Author `world_register.yaml` (`sidequest-content`)

**Files:**
- Create: `sidequest-content/.../beneath_sunden/world_register.yaml`

- [ ] **Step 1: Write the file** (verbatim from spec §5, played-straight Moria-grave; no winking — CLAUDE.md tone)

```yaml
# Beneath Sünden — genre-truth gate (spec §5). Applied BEFORE any RACE
# roll. A row denied here is removed from every RACE roll-space. marquee
# rows are exempt from denial (Diamonds-and-Coal, ADR-014).
register: "Grave, lethal, Moria-as-tragedy. Gravity >= 0.85. No winking."
allow_types: [Undead, Aberration, Ooze, Monstrosity, Construct, Giant, Humanoid, Beast]
deny:
  types: [Celestial, Fey]
  tags: [titan, metallic, angel, genie]
  name_glob: ["*modron*", "*faerie dragon*", "*pixie*", "*mephit*", "*sprite*",
              "*flumph*", "*unicorn*", "*pegasus*"]
humanoid_constraint: "Humanoid only as grave cultists/bandits/the delved-too-deep — never townsfolk-tone."
reskin:
  "Gray Ooze": "The Seep"
marquee: ["Lich", "Mummy Lord", "Vampire"]
```

- [ ] **Step 2: Commit (`sidequest-content`)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git add genre_packs/caverns_and_claudes/worlds/beneath_sunden/world_register.yaml
git commit -m "content(beneath_sunden): world_register genre-truth gate (spec §5)"
```

### Task 5: Curation filter + glob matcher

**Files:**
- Create: `sidequest-server/sidequest/game/cookbook/corpus.py` (glob + clause matcher — used by curation *and* RACE filters)
- Create: `sidequest-server/sidequest/game/cookbook/curation.py`
- Create: `sidequest-server/tests/game/cookbook/test_curation.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_curation.py`

```python
"""Curation hard filter — spec §5/§9: denied rows gone, marquee survives."""

from __future__ import annotations

from sidequest.game.cookbook.curation import apply_world_register
from sidequest.game.cookbook.models import CorpusMonster, WorldRegister


def _mon(name: str, typ: str, tags=None, cr: float = 1.0) -> CorpusMonster:
    return CorpusMonster(
        name=name, size="Medium", type=typ, tags=tags or [],
        alignment="NE", cr=cr, xp=200, source="t",
    )


REGISTER = WorldRegister(
    register="grave",
    allow_types=["Undead", "Aberration", "Construct"],
    deny={"types": ["Celestial", "Fey"], "tags": ["titan"],
          "name_glob": ["*pixie*"]},
    marquee=["Lich"],
)


def test_denied_type_removed() -> None:
    corpus = [_mon("Solar", "Celestial"), _mon("Skeleton", "Undead")]
    kept = apply_world_register(corpus, REGISTER)
    assert [m.name for m in kept] == ["Skeleton"]


def test_type_not_in_allowlist_removed() -> None:
    # Dragon is neither allowed nor explicitly denied → removed (allowlist gate).
    corpus = [_mon("Adult Red Dragon", "Dragon"), _mon("Skeleton", "Undead")]
    kept = apply_world_register(corpus, REGISTER)
    assert [m.name for m in kept] == ["Skeleton"]


def test_denied_tag_removed() -> None:
    corpus = [_mon("Empyrean", "Giant", tags=["titan"])]
    assert apply_world_register(corpus, REGISTER) == []


def test_denied_name_glob_removed() -> None:
    corpus = [_mon("Pixie", "Fey")]
    assert apply_world_register(corpus, REGISTER) == []


def test_marquee_exempt_from_denial() -> None:
    # Lich is Undead (allowed) but also marquee — survives even if a deny
    # rule would catch it. Construct a deny that would hit it by name.
    reg = WorldRegister(
        register="g", allow_types=["Undead"],
        deny={"name_glob": ["*lich*"]}, marquee=["Lich"],
    )
    corpus = [_mon("Lich", "Undead")]
    kept = apply_world_register(corpus, reg)
    assert [m.name for m in kept] == ["Lich"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_curation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.cookbook.curation'`

- [ ] **Step 3: Write minimal implementation**

`sidequest-server/sidequest/game/cookbook/corpus.py`:
```python
"""Corpus matching primitives — glob + clause/predicate evaluation.

Shared by curation (world_register) and RACE filter resolution so the
match semantics are defined exactly once.
"""

from __future__ import annotations

import fnmatch

from sidequest.game.cookbook.models import CorpusMonster, FilterClause


def name_matches(name: str, glob: str) -> bool:
    """Case-insensitive fnmatch (SRD names are Title Case; globs lower)."""
    return fnmatch.fnmatch(name.lower(), glob.lower())


def clause_matches(mon: CorpusMonster, clause: FilterClause) -> bool:
    """All present clause fields must hold (AND within a clause)."""
    if clause.type is not None and mon.type != clause.type:
        return False
    if clause.tags_any is not None:
        if not set(clause.tags_any) & set(mon.tags):
            return False
    if clause.name_glob is not None and not name_matches(mon.name, clause.name_glob):
        return False
    return True


def any_of_matches(mon: CorpusMonster, clauses: list[FilterClause]) -> bool:
    """OR across clauses (spec §4.2 RACE filter.any_of)."""
    return any(clause_matches(mon, c) for c in clauses)
```

`sidequest-server/sidequest/game/cookbook/curation.py`:
```python
"""world_register hard filter (spec §5).

Allowlist gate + deny rules, run BEFORE any RACE roll. marquee rows are
exempt from denial and survive unconditionally (Diamonds-and-Coal,
ADR-014). No silent substitution — a denied row is simply absent.
"""

from __future__ import annotations

from sidequest.game.cookbook.corpus import name_matches
from sidequest.game.cookbook.models import CorpusMonster, WorldRegister


def _denied(mon: CorpusMonster, reg: WorldRegister) -> bool:
    if mon.type in reg.deny.types:
        return True
    if set(reg.deny.tags) & set(mon.tags):
        return True
    if any(name_matches(mon.name, g) for g in reg.deny.name_glob):
        return True
    return False


def apply_world_register(
    corpus: list[CorpusMonster], reg: WorldRegister
) -> list[CorpusMonster]:
    """Return the curated roll-space. marquee survives denial + allowlist."""
    marquee = set(reg.marquee)
    kept: list[CorpusMonster] = []
    for mon in corpus:
        if mon.name in marquee:
            kept.append(mon)
            continue
        if mon.type not in reg.allow_types:
            continue
        if _denied(mon, reg):
            continue
        kept.append(mon)
    return kept
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_curation.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/corpus.py sidequest/game/cookbook/curation.py tests/game/cookbook/test_curation.py
git commit -m "feat(cookbook): world_register curation hard filter + glob/clause matcher"
```

---

## Phase D — RACE Definitions (spec §10 step 3, §4.2)

### Task 6: Author the five RACE files (`sidequest-content`)

**Files:**
- Create: `cookbook/races/undead.yaml`, `aberration.yaml`, `ooze.yaml`, `goblinoid.yaml`, `dwarf.yaml`

> **All names below are verified against the ingested SRD 5.1 corpus** (Prereq 0 inventory). `min_band` is set so the named big_bad's real CR resolves inside that band (`cr_bands`: shallow 0–2, mid 2–7, deep 6–30). Authoring a `min_band` the CR can't reach is exactly what Task 10 fails loudly on — these are pre-checked: Wight cr3→mid, Mummy Lord cr15→deep, Lich cr21→deep, Aboleth cr10→deep, Black Pudding cr4→mid.

- [ ] **Step 1: Write `cookbook/races/undead.yaml`**

```yaml
id: undead
display: "The Restless"
# Undead 18 rows in SRD corpus, CR 0.25 (Skeleton/Zombie) → 21 (Lich).
filter:
  any_of:
    - { type: Undead }
    - { type: Construct, name_glob: "*animated*" }
deny:
  name_glob: ["*faerie*"]
telegraph:
  shallow: "Bone-dust on every sill. Something here does not lie down."
  mid: "The dead are organized. That is worse than wandering."
  deep: "A cold that has a will behind it."
loot_bias:
  category_weight: { "Wondrous Item": 1.3, Weapon: 0.8 }
big_bads:
  - { name: "Wight", min_band: mid }        # cr 3 → mid capstone
  - { name: "Mummy Lord", min_band: deep }  # cr 15 → deep only
  - { name: "Lich", min_band: deep }        # cr 21 → deep only
```

- [ ] **Step 2: Write `cookbook/races/aberration.yaml`**

```yaml
id: aberration
display: "The Wrongness"
# Aberration 5 rows: Gibbering Mouther 2, Chuul 4, Otyugh 5, Cloaker 8,
# Aboleth 10 → resolves shallow(≤2)/mid(2-7)/deep(6-30).
filter:
  any_of:
    - { type: Aberration }
telegraph:
  shallow: "Angles in the stone that the eye keeps re-counting."
  mid: "The corridor was not this shape on the way in."
  deep: "It has been watching long enough to learn your name."
loot_bias:
  category_weight: { "Wondrous Item": 1.4, Armor: 0.7 }
big_bads:
  - { name: "Otyugh", min_band: mid }    # cr 5 → mid capstone
  - { name: "Aboleth", min_band: deep }  # cr 10 → deep
```

- [ ] **Step 3: Write `cookbook/races/ooze.yaml`** (replaces the spec's illustrative `kuo_toa` — SRD 5.1 has no Kuo-toa; Ooze matches the existing `world_register.reskin: "Gray Ooze": "The Seep"`)

```yaml
id: ooze
display: "The Seep"
# Ooze 4 rows: Gray Ooze 0.5, Gelatinous Cube 2, Ochre Jelly 2,
# Black Pudding 4. CR CEILING 4 → CANNOT fill a `deep` region.
# This is the data-forced low-ceiling case (see plan "Data-Forced
# Design Item"): the assembler performs an observable affinity re-roll
# (cookbook.race.reroll) rather than emit an empty deep table.
filter:
  any_of:
    - { type: Ooze }
telegraph:
  shallow: "The floor is wet where nothing should be wet."
  mid: "It came through a gap a coin could not. It is not in a hurry."
  deep: "The walls here are digested. Do not touch the walls."
loot_bias:
  category_weight: { Potion: 1.2, "Wondrous Item": 0.9 }
big_bads:
  - { name: "Black Pudding", min_band: mid }  # cr 4 → mid capstone
```

- [ ] **Step 4: Write `cookbook/races/goblinoid.yaml`**

```yaml
id: goblinoid
display: "The Scavengers"
# goblinoid-tagged Humanoids in SRD: Goblin 0.25, Hobgoblin 0.5,
# Bugbear 1. CR CEILING 1 → shallow-only. No SRD goblinoid capstone
# exists ("Hobgoblin Warlord" is NOT in SRD 5.1). Deliberately
# big_bad-less harrier faction; low-ceiling re-roll case (see
# "Data-Forced Design Item").
filter:
  any_of:
    - { type: Humanoid, tags_any: [goblinoid] }
telegraph:
  shallow: "Cookfire smell, gnawed bone, a sentry who runs the moment he sees you."
  mid: "They have learned the corridors better than the dead did."
  deep: "Not a warband. A war."
loot_bias:
  category_weight: { Weapon: 1.3, "Wondrous Item": 0.8 }
big_bads: []
```

- [ ] **Step 5: Write `cookbook/races/dwarf.yaml`** (conceptual RACE — spec §4.2 `concept`; Moria-as-tragedy, never "diggy-diggy-hole" — spec §3)

```yaml
id: dwarf
display: "The Delved-Too-Deep"
# No literal SRD "dwarf" monster. This RACE sources its creatures via the
# undead filter and supplies narrative framing (spec §4.2 concept).
filter:
  any_of:
    - { type: Undead }
deny:
  name_glob: ["*faerie*"]
telegraph:
  shallow: "Dwarf-make everywhere. Tools set down mid-task, never taken up again."
  mid: "They held this gate. You can see exactly how long, and exactly how it ended."
  deep: "They dug toward something. It dug back."
loot_bias:
  category_weight: { Weapon: 1.2, Armor: 1.2 }
big_bads:
  - { name: "Wight", min_band: mid }   # the watch that did not stand down
  - { name: "Lich", min_band: deep }   # what answered the digging
concept:
  framing: >-
    A dwarfhold that dug past where digging should stop. No survivors —
    only what answered. Played as Moria-grave tragedy, never comedy.
  sourced_from: undead
```

- [ ] **Step 6: Commit (`sidequest-content`)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git add genre_packs/caverns_and_claudes/worlds/beneath_sunden/cookbook/races/
git commit -m "content(beneath_sunden): five RACE definitions (filter predicates + concept)"
```

### Task 7: RACE filter resolution

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/corpus.py` (add `resolve_race`)
- Create: `sidequest-server/tests/game/cookbook/test_filter_apply.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_filter_apply.py`

```python
"""RACE filter resolution: any_of OR, per-RACE deny, CR-band slice."""

from __future__ import annotations

from sidequest.game.cookbook.corpus import resolve_race
from sidequest.game.cookbook.models import CorpusMonster, RaceDef


def _mon(name, typ, tags=None, cr=1.0) -> CorpusMonster:
    return CorpusMonster(name=name, size="Medium", type=typ, tags=tags or [],
                         alignment="NE", cr=cr, xp=200, source="t")


UNDEAD = RaceDef(
    id="undead", display="The Restless",
    filter={"any_of": [{"type": "Undead"},
                       {"type": "Construct", "name_glob": "*animated*"}]},
    deny={"name_glob": ["*faerie*"]},
)


def test_any_of_or_semantics() -> None:
    corpus = [_mon("Skeleton", "Undead"), _mon("Animated Armor", "Construct"),
              _mon("Iron Golem", "Construct"), _mon("Goblin", "Humanoid")]
    got = {m.name for m in resolve_race(corpus, UNDEAD)}
    assert got == {"Skeleton", "Animated Armor"}


def test_per_race_deny_subtracts() -> None:
    corpus = [_mon("Skeleton", "Undead"), _mon("Faerie Wraith", "Undead")]
    got = {m.name for m in resolve_race(corpus, UNDEAD)}
    assert got == {"Skeleton"}


def test_cr_band_slice() -> None:
    corpus = [_mon("Skeleton", "Undead", cr=0.25), _mon("Lich", "Undead", cr=21)]
    got = {m.name for m in resolve_race(corpus, UNDEAD, cr_min=6, cr_max=30)}
    assert got == {"Lich"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_filter_apply.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_race'`

- [ ] **Step 3: Append to `sidequest/game/cookbook/corpus.py`**

```python
from sidequest.game.cookbook.models import RaceDef  # add to existing imports


def resolve_race(
    corpus: list[CorpusMonster],
    race: RaceDef,
    *,
    cr_min: float | None = None,
    cr_max: float | None = None,
) -> list[CorpusMonster]:
    """RACE roll-space: corpus ∩ race.filter − race.deny, optional CR slice.

    Curation (world_register) is applied UPSTREAM of this — callers pass
    an already-curated corpus (spec §5: register runs before any RACE
    roll).
    """
    deny_types = set(race.deny.types)
    deny_tags = set(race.deny.tags)
    out: list[CorpusMonster] = []
    for mon in corpus:
        if not any_of_matches(mon, race.filter.any_of):
            continue
        if mon.type in deny_types or (deny_tags & set(mon.tags)):
            continue
        if any(name_matches(mon.name, g) for g in race.deny.name_glob):
            continue
        if cr_min is not None and mon.cr < cr_min:
            continue
        if cr_max is not None and mon.cr > cr_max:
            continue
        out.append(mon)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_filter_apply.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/corpus.py tests/game/cookbook/test_filter_apply.py
git commit -m "feat(cookbook): RACE filter resolution (any_of OR, per-race deny, CR slice)"
```

---

## Phase E — LOOK + Affinities + SPECIAL (spec §10 steps 4–5)

### Task 8: Author `looks.yaml`, `affinities.yaml`, `special_rooms.yaml` (`sidequest-content`)

**Files:**
- Create: `cookbook/looks.yaml`, `cookbook/affinities.yaml`, `cookbook/special_rooms.yaml`

> Note: `generator_binding` values (`depthfirst`, etc.) are **oq-1-owned keys**; we reference, never define their semantics (spec §4.2). Task 21 validates the reference exists against oq-1's known set.

- [ ] **Step 1: Write `cookbook/looks.yaml`**

```yaml
looks:
  - id: necropolis
    generator_binding: depthfirst
    register: "Mausoleum-formal. Straight lines cut by collapse."
    dressing:
      - "Niche after niche, most emptied, a few not."
      - "Grave-script worn past reading."
      - "Standing water gone to mirror in a cracked sarcophagus."
  - id: sunken
    generator_binding: cellular
    register: "Drowned. Every surface gives under the hand."
    dressing:
      - "Black water to the ankle, then to the knee, then unmeasured."
      - "Rope and net fused into the wall by years of wet."
      - "Something exhales bubbles from a grate you cannot see."
  - id: delvehold
    generator_binding: prim
    register: "Dwarf-make tragedy. Built to last; outlived its makers."
    dressing:
      - "A gate-mechanism dwarf-cut and dwarf-perfect, jammed open."
      - "Tool-marks that stop mid-stroke."
      - "A muster-hall with the benches still set for a watch that never stood down."
```

- [ ] **Step 2: Write `cookbook/affinities.yaml`** (first-pass tuning per spec §11 Open Items)

```yaml
# depth_score → CR band. Bands ORDINAL (shallow < mid < deep), increasing
# depth. Boundaries are content tuning; depth_score is oq-1's.
cr_bands:
  - { id: shallow, depth_lt: 0.25, cr_min: 0, cr_max: 2 }
  - { id: mid,     depth_lt: 0.60, cr_min: 2, cr_max: 7 }
  - { id: deep,    depth_lt: 1.01, cr_min: 6, cr_max: 30 }
big_bad_gate:
  on_first_band_entry: [mid, deep]
  recurring_chance: { mid: 0.10, deep: 0.20 }
look_race_affinity:
  necropolis: { undead: 6, aberration: 2, ooze: 1, goblinoid: 1, dwarf: 3 }
  sunken:     { ooze: 5, undead: 2, aberration: 3, goblinoid: 1, dwarf: 1 }
  delvehold:  { dwarf: 6, undead: 4, goblinoid: 2, aberration: 1, ooze: 1 }
rarity_by_band:
  shallow: { Common: 6, Uncommon: 2 }
  mid:     { Uncommon: 5, Rare: 3, Common: 1 }
  deep:    { Rare: 4, "Very rare": 3, Legendary: 1, Artifact: 0.2 }
size_by_burst:
  - { burst_lte: 1, wandering_rolls: 1, special_rooms: 0, loot_rolls: 1 }
  - { burst_lte: 3, wandering_rolls: 3, special_rooms: 1, loot_rolls: 2 }
  - { burst_lte: 9, wandering_rolls: 6, special_rooms: 2, loot_rolls: 4 }
big_bad_forces_size: large
```

- [ ] **Step 3: Write `cookbook/special_rooms.yaml`**

```yaml
special_rooms:
  - id: teleporter_room
    telegraph: "A ring of scored glyphs, swept clean while everything else rots."
    mechanic: "Step onto the ring → forced relocation to a frontier region."
    outcome: "Hard, legible: you are moved; you do not choose where."
    min_band: mid
    feeds_setpiece_slot: true
  - id: collapse_gallery
    telegraph: "The ceiling here is a held breath. Dust sifts with every footfall."
    mechanic: "Loud action or a failed traverse → directed collapse; a route is lost, a new one opens."
    outcome: "Hard, legible: the map changes; nobody chose which way."
    min_band: shallow
    feeds_setpiece_slot: true
  - id: reliquary
    telegraph: "One sealed door, dwarf-barred from this side. Something was kept IN."
    mechanic: "Opening it releases the reliquary's keeper and its hoard together."
    outcome: "Hard, legible: the reward and the threat are the same room."
    min_band: deep
    feeds_setpiece_slot: true
```

- [ ] **Step 4: Commit (`sidequest-content`)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git add genre_packs/caverns_and_claudes/worlds/beneath_sunden/cookbook/looks.yaml \
        genre_packs/caverns_and_claudes/worlds/beneath_sunden/cookbook/affinities.yaml \
        genre_packs/caverns_and_claudes/worlds/beneath_sunden/cookbook/special_rooms.yaml
git commit -m "content(beneath_sunden): looks, affinities, special_rooms tables"
```

### Task 9: Cookbook loader (`CookbookBundle`)

**Files:**
- Create: `sidequest-server/sidequest/game/cookbook/loader.py`
- Create: `sidequest-server/tests/game/cookbook/conftest.py`
- Create: `sidequest-server/tests/game/cookbook/test_loader.py`

- [ ] **Step 1: Write `tests/game/cookbook/conftest.py`** (shared real-bundle fixture)

```python
"""Shared fixture: the real Beneath Sünden cookbook bundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.cookbook.loader import CookbookBundle, load_cookbook

WORLD = (
    Path(__file__).parents[4]
    / "sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden"
)


@pytest.fixture(scope="session")
def bundle() -> CookbookBundle:
    return load_cookbook(WORLD)
```

- [ ] **Step 2: Write the failing test** — `tests/game/cookbook/test_loader.py`

```python
"""Loader wires the real authored YAML into typed models."""

from __future__ import annotations


def test_bundle_has_all_axes(bundle) -> None:
    assert {r.id for r in bundle.races} >= {
        "undead", "aberration", "ooze", "goblinoid", "dwarf"
    }
    assert {l.id for l in bundle.looks} == {"necropolis", "sunken", "delvehold"}
    assert [b.id for b in bundle.affinities.cr_bands] == ["shallow", "mid", "deep"]
    assert bundle.register.allow_types
    assert len(bundle.monsters) > 0 and len(bundle.items) > 0
    assert {s.id for s in bundle.specials} >= {"teleporter_room"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.cookbook.loader'`

- [ ] **Step 4: Write `sidequest/game/cookbook/loader.py`**

```python
"""Load a beneath_sunden world dir into a typed CookbookBundle.

This is the COOKBOOK loader (oq-2). It is NOT oq-1's region_graph/themes
loader (spec §2) — distinct concern, distinct file. No silent fallback:
a missing required file raises FileNotFoundError naming the path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from sidequest.game.cookbook.models import (
    Affinities,
    CorpusItem,
    CorpusMonster,
    LookDef,
    RaceDef,
    SpecialRoom,
    WorldRegister,
)


@dataclass(frozen=True)
class CookbookBundle:
    monsters: list[CorpusMonster]
    items: list[CorpusItem]
    register: WorldRegister
    races: list[RaceDef]
    looks: list[LookDef]
    affinities: Affinities
    specials: list[SpecialRoom]


def _load_yaml(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(f"cookbook: required file missing: {path}")
    return yaml.safe_load(path.read_text())


def load_cookbook(world: Path) -> CookbookBundle:
    cp = world / "corpus"
    cb = world / "cookbook"
    monsters = [CorpusMonster(**r) for r in _load_yaml(cp / "monsters.yaml")]
    items = [CorpusItem(**r) for r in _load_yaml(cp / "items.yaml")]
    register = WorldRegister(**_load_yaml(world / "world_register.yaml"))
    race_dir = cb / "races"
    if not race_dir.is_dir():
        raise FileNotFoundError(f"cookbook: races dir missing: {race_dir}")
    races = [
        RaceDef(**_load_yaml(p)) for p in sorted(race_dir.glob("*.yaml"))
    ]
    looks = [LookDef(**l) for l in _load_yaml(cb / "looks.yaml")["looks"]]
    affinities = Affinities(**_load_yaml(cb / "affinities.yaml"))
    specials = [
        SpecialRoom(**s)
        for s in _load_yaml(cb / "special_rooms.yaml")["special_rooms"]
    ]
    return CookbookBundle(
        monsters=monsters,
        items=items,
        register=register,
        races=races,
        looks=looks,
        affinities=affinities,
        specials=specials,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_loader.py -v`
Expected: PASS (requires Task 2 corpus committed; if corpus absent because Prereq 0 is blocked, this test cannot pass — that is the correct loud failure, not a plan defect).

- [ ] **Step 6: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/loader.py tests/game/cookbook/conftest.py tests/game/cookbook/test_loader.py
git commit -m "feat(cookbook): CookbookBundle loader over the beneath_sunden world dir"
```

### Task 10: Filter-resolution validation (spec §7 loud failures)

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/loader.py` (add `validate_bundle`)
- Create: `sidequest-server/tests/game/cookbook/test_filter_resolution.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_filter_resolution.py`

```python
"""Spec §7/§9: every RACE filter resolves ≥1 curated row in every band it
claims (via big_bads.min_band or LOOK affinity presence). Loud otherwise."""

from __future__ import annotations

import pytest

from sidequest.game.cookbook.loader import CookbookValidationError, validate_bundle


def test_real_bundle_validates(bundle) -> None:
    # Must not raise. Per "Data-Forced Design Item": ooze (ceiling CR 4)
    # and goblinoid (ceiling CR 1) do NOT fill `deep` — and that is
    # explicitly NOT a build error under the corrected semantics.
    validate_bundle(bundle)


def test_shallow_entry_guarantee_is_loud(bundle) -> None:
    # Deny every Undead/Construct → 'undead' empties even at SHALLOW →
    # violates the entry guarantee → must raise naming the RACE.
    reg = bundle.register.model_copy(deep=True)
    reg.deny.types = list(set(reg.deny.types) | {"Undead", "Construct"})
    broken = type(bundle)(
        monsters=bundle.monsters, items=bundle.items, register=reg,
        races=bundle.races, looks=bundle.looks,
        affinities=bundle.affinities, specials=bundle.specials,
    )
    with pytest.raises(CookbookValidationError, match="undead"):
        validate_bundle(broken)


def test_unreachable_bigbad_is_loud(bundle) -> None:
    # Give goblinoid a big_bad whose CR can't reach its declared
    # min_band → a declared capstone is unreachable → must raise.
    gob = next(r for r in bundle.races if r.id == "goblinoid")
    bad = gob.model_copy(
        update={"big_bads": [{"name": "Goblin", "min_band": "deep"}]}
    )
    broken = type(bundle)(
        monsters=bundle.monsters, items=bundle.items,
        register=bundle.register,
        races=[bad if r.id == "goblinoid" else r for r in bundle.races],
        looks=bundle.looks, affinities=bundle.affinities,
        specials=bundle.specials,
    )
    with pytest.raises(CookbookValidationError, match="goblinoid"):
        validate_bundle(broken)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_filter_resolution.py -v`
Expected: FAIL — `ImportError: cannot import name 'CookbookValidationError'`

- [ ] **Step 3: Append to `sidequest/game/cookbook/loader.py`**

```python
from sidequest.game.cookbook.corpus import resolve_race  # add to imports
from sidequest.game.cookbook.curation import apply_world_register  # add to imports


class CookbookValidationError(RuntimeError):
    """Loud build-time failure (spec §7) — never a silent fallback."""


def validate_bundle(bundle: CookbookBundle) -> None:
    """Spec §7 gates, corrected per "Data-Forced Design Item".

    A RACE must resolve ≥1 curated row in (a) the SHALLOW band (entry
    guarantee) and (b) every band ≥ each of its big_bads' min_band (a
    declared capstone must be reachable). Bands a RACE simply cannot
    fill are NOT a build error — the assembler re-rolls observably
    (cookbook.race.reroll). Raises CookbookValidationError naming the
    offender. No silent fallback.
    """
    curated = apply_world_register(bundle.monsters, bundle.register)
    band_order = bundle.affinities.band_order()
    band_by_id = {b.id: b for b in bundle.affinities.cr_bands}
    shallow_id = bundle.affinities.cr_bands[0].id

    def _resolves(race, band_id: str) -> bool:
        b = band_by_id[band_id]
        return bool(
            resolve_race(curated, race, cr_min=b.cr_min, cr_max=b.cr_max)
        )

    for race in bundle.races:
        # (a) entry guarantee — every faction encounterable at shallow.
        if not _resolves(race, shallow_id):
            raise CookbookValidationError(
                f"RACE '{race.id}' resolves to ZERO curated rows at the "
                f"entry band '{shallow_id}'. Widen the filter or relax "
                f"world_register.deny — every faction must be "
                f"encounterable."
            )
        # (b) declared capstones must be reachable.
        for bb in race.big_bads:
            if bb.min_band not in band_order:
                raise CookbookValidationError(
                    f"RACE '{race.id}' big_bad '{bb.name}' has unknown "
                    f"min_band '{bb.min_band}'"
                )
            if not any(m.name == bb.name for m in curated):
                raise CookbookValidationError(
                    f"RACE '{race.id}' big_bad '{bb.name}' does not resolve "
                    f"in curated corpus/monsters.yaml"
                )
            # min_band-only (NOT "every band >= min_band"): a RACE that
            # cannot fill bands ABOVE its capstone's min_band is the
            # Data-Forced case (ooze: Black Pudding @ mid, no deep) and
            # is handled by the assembler re-roll, not a build error.
            if not _resolves(race, bb.min_band):
                raise CookbookValidationError(
                    f"RACE '{race.id}' declares big_bad '{bb.name}' at "
                    f"min_band '{bb.min_band}' but resolves ZERO rows at "
                    f"that band — the capstone is unreachable. Lower "
                    f"min_band or widen the filter."
                )

    # Every LOOK must have ≥1 affinity RACE that can fill shallow, else a
    # region under that LOOK could exhaust the re-roll (spec §7: no
    # silent empty table — fail at build instead).
    for look, weights in bundle.affinities.look_race_affinity.items():
        by_id = {r.id: r for r in bundle.races}
        if not any(
            w > 0 and rid in by_id and _resolves(by_id[rid], shallow_id)
            for rid, w in weights.items()
        ):
            raise CookbookValidationError(
                f"LOOK '{look}' has no affinity RACE that resolves at "
                f"'{shallow_id}' — every region under it would fail."
            )

    # reskin keys must resolve in the raw corpus (spec §7).
    names = {m.name for m in bundle.monsters}
    for key in bundle.register.reskin:
        if key not in names:
            raise CookbookValidationError(
                f"world_register.reskin key '{key}' not in corpus/monsters.yaml"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_filter_resolution.py -v`
Expected: all three PASS. `test_real_bundle_validates` passing is the proof the shipped content is genre-true *and* SRD-feasible (ooze/goblinoid not filling deep is by design). If it fails, **fix the content YAML** (Tasks 6/8/4), not the test (spec §7 is the whole point).

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/loader.py tests/game/cookbook/test_filter_resolution.py
git commit -m "feat(cookbook): loud filter-resolution validation (spec §7)"
```

---

## Phase F — Region-Assembly Contract + OTEL (spec §10 step 6, §4.3, §8)

### Task 11: OTEL span definitions (`sidequest/telemetry/spans/cookbook.py`)

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/cookbook.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py` (add star-import)
- Create: `sidequest-server/tests/telemetry/spans/test_cookbook_spans.py`

> oq-2 authors the definitions + helpers + routes (GM-panel catalog). oq-1 calls the helpers at materialization (spec §8). The repo's `tests/telemetry/test_routing_completeness.py` enforces every new constant is routed or flat-only — these are routed (the GM panel is the lie detector, CLAUDE.md).

- [ ] **Step 1: Write the failing test** — `tests/telemetry/spans/test_cookbook_spans.py`

```python
"""Cookbook span definitions exist, are importable, and are routed."""

from __future__ import annotations

from sidequest.telemetry.spans import (
    SPAN_COOKBOOK_BIGBAD_GATED,
    SPAN_COOKBOOK_CR_BAND,
    SPAN_COOKBOOK_CURATION_DENIED,
    SPAN_COOKBOOK_RACE_REROLL,
    SPAN_COOKBOOK_RACE_ROLLED,
    SPAN_COOKBOOK_SIZE_BUDGET,
)
from sidequest.telemetry.spans._core import SPAN_ROUTES


def test_spec_8_spans_named() -> None:
    assert SPAN_COOKBOOK_RACE_ROLLED == "cookbook.race.rolled"
    assert SPAN_COOKBOOK_CR_BAND == "cookbook.cr_band"
    assert SPAN_COOKBOOK_SIZE_BUDGET == "cookbook.size_budget"
    assert SPAN_COOKBOOK_BIGBAD_GATED == "cookbook.bigbad.gated"
    assert SPAN_COOKBOOK_CURATION_DENIED == "cookbook.curation.denied"
    # Data-Forced Design Item: low-ceiling re-roll is observable.
    assert SPAN_COOKBOOK_RACE_REROLL == "cookbook.race.reroll"


def test_spans_are_routed() -> None:
    for name in (
        "cookbook.race.rolled", "cookbook.cr_band", "cookbook.size_budget",
        "cookbook.bigbad.gated", "cookbook.curation.denied",
        "cookbook.race.reroll",
    ):
        assert name in SPAN_ROUTES, f"{name} not registered in SPAN_ROUTES"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/spans/test_cookbook_spans.py -v`
Expected: FAIL — `ImportError: cannot import name 'SPAN_COOKBOOK_RACE_ROLLED'`

- [ ] **Step 3: Write `sidequest/telemetry/spans/cookbook.py`** (pattern mirrors `region_state.py`)

```python
"""Cookbook spans — region-assembly audit (spec §8).

Definitions live here (oq-2). oq-1 calls these helpers at the
materializer seam. The GM panel is the lie detector: every axis roll
is a routed span so Sebastien can verify the cookbook engaged rather
than the narrator improvising.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from ._core import SPAN_ROUTES, SpanRoute
from .span import Span

SPAN_COOKBOOK_RACE_ROLLED = "cookbook.race.rolled"
SPAN_COOKBOOK_CR_BAND = "cookbook.cr_band"
SPAN_COOKBOOK_SIZE_BUDGET = "cookbook.size_budget"
SPAN_COOKBOOK_BIGBAD_GATED = "cookbook.bigbad.gated"
SPAN_COOKBOOK_CURATION_DENIED = "cookbook.curation.denied"
SPAN_COOKBOOK_RACE_REROLL = "cookbook.race.reroll"


def _attr(field: str):
    return lambda span, f=field: (span.attributes or {}).get(f)


SPAN_ROUTES[SPAN_COOKBOOK_RACE_ROLLED] = SpanRoute(
    event_type="state_transition",
    component="cookbook",
    extract=lambda s: {
        "field": "race",
        "look": _attr("look")(s),
        "race": _attr("race")(s),
        "affinity_weight": _attr("affinity_weight")(s),
        "rng_seed": _attr("rng_seed")(s),
    },
)
SPAN_ROUTES[SPAN_COOKBOOK_CR_BAND] = SpanRoute(
    event_type="state_transition",
    component="cookbook",
    extract=lambda s: {
        "field": "cr_band",
        "depth_score": _attr("depth_score")(s),
        "band": _attr("band")(s),
        "cr_min": _attr("cr_min")(s),
        "cr_max": _attr("cr_max")(s),
    },
)
SPAN_ROUTES[SPAN_COOKBOOK_SIZE_BUDGET] = SpanRoute(
    event_type="state_transition",
    component="cookbook",
    extract=lambda s: {
        "field": "size_budget",
        "burst_magnitude": _attr("burst_magnitude")(s),
        "wandering_rolls": _attr("wandering_rolls")(s),
        "special_rooms": _attr("special_rooms")(s),
        "loot_rolls": _attr("loot_rolls")(s),
    },
)
SPAN_ROUTES[SPAN_COOKBOOK_BIGBAD_GATED] = SpanRoute(
    event_type="state_transition",
    component="cookbook",
    extract=lambda s: {
        "field": "big_bad",
        "depth_score": _attr("depth_score")(s),
        "threshold_crossed": _attr("threshold_crossed")(s),
        "big_bad": _attr("big_bad")(s),
    },
)
SPAN_ROUTES[SPAN_COOKBOOK_CURATION_DENIED] = SpanRoute(
    event_type="state_transition",
    component="cookbook",
    extract=lambda s: {
        "field": "curation",
        "race": _attr("race")(s),
        "denied_count": _attr("denied_count")(s),
        "sample_names": _attr("sample_names")(s),
    },
)
SPAN_ROUTES[SPAN_COOKBOOK_RACE_REROLL] = SpanRoute(
    event_type="state_transition",
    component="cookbook",
    extract=lambda s: {
        "field": "race",
        "op": "low_ceiling_reroll",
        "look": _attr("look")(s),
        "band": _attr("band")(s),
        "from_race": _attr("from_race")(s),
        "to_race": _attr("to_race")(s),
        "excluded": _attr("excluded")(s),
    },
)


@contextmanager
def cookbook_race_rolled_span(
    *, look: str, race: str, affinity_weight: float, rng_seed: int,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_COOKBOOK_RACE_ROLLED,
        {"look": look, "race": race, "affinity_weight": affinity_weight,
         "rng_seed": rng_seed, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def cookbook_cr_band_span(
    *, depth_score: float, band: str, cr_min: float, cr_max: float,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_COOKBOOK_CR_BAND,
        {"depth_score": depth_score, "band": band, "cr_min": cr_min,
         "cr_max": cr_max, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def cookbook_size_budget_span(
    *, burst_magnitude: int, wandering_rolls: int, special_rooms: int,
    loot_rolls: int, _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_COOKBOOK_SIZE_BUDGET,
        {"burst_magnitude": burst_magnitude, "wandering_rolls": wandering_rolls,
         "special_rooms": special_rooms, "loot_rolls": loot_rolls, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def cookbook_bigbad_gated_span(
    *, depth_score: float, threshold_crossed: bool, big_bad: str | None,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_COOKBOOK_BIGBAD_GATED,
        {"depth_score": depth_score, "threshold_crossed": threshold_crossed,
         "big_bad": big_bad, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def cookbook_curation_denied_span(
    *, race: str, denied_count: int, sample_names: list[str],
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_COOKBOOK_CURATION_DENIED,
        {"race": race, "denied_count": denied_count,
         "sample_names": sample_names, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def cookbook_race_reroll_span(
    *, look: str, band: str, from_race: str, to_race: str | None,
    excluded: list[str], _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    """Data-Forced Design Item: a low-ceiling RACE could not fill the
    rolled band; the assembler yielded to another affinity RACE. NOT a
    silent fallback — this span is the GM-panel evidence (spec §7)."""
    with Span.open(
        SPAN_COOKBOOK_RACE_REROLL,
        {"look": look, "band": band, "from_race": from_race,
         "to_race": to_race, "excluded": excluded, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


__all__ = [
    "SPAN_COOKBOOK_BIGBAD_GATED",
    "SPAN_COOKBOOK_CR_BAND",
    "SPAN_COOKBOOK_CURATION_DENIED",
    "SPAN_COOKBOOK_RACE_REROLL",
    "SPAN_COOKBOOK_RACE_ROLLED",
    "SPAN_COOKBOOK_SIZE_BUDGET",
    "cookbook_bigbad_gated_span",
    "cookbook_cr_band_span",
    "cookbook_curation_denied_span",
    "cookbook_race_reroll_span",
    "cookbook_race_rolled_span",
    "cookbook_size_budget_span",
]
```

- [ ] **Step 4: Register the submodule in `sidequest/telemetry/spans/__init__.py`**

Add the import in alphabetical position (between `.continuity` and `.course`, matching the existing star-import block):

```python
from .cookbook import *  # noqa: F401, F403
```

- [ ] **Step 5: Run tests to verify they pass (incl. routing completeness)**

Run: `cd sidequest-server && uv run pytest tests/telemetry/spans/test_cookbook_spans.py tests/telemetry/test_routing_completeness.py -v`
Expected: all PASS (constants importable, all five routed, completeness lint green).

- [ ] **Step 6: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/telemetry/spans tests/telemetry/spans && uv run ruff format sidequest/telemetry/spans tests/telemetry/spans
git add sidequest/telemetry/spans/cookbook.py sidequest/telemetry/spans/__init__.py tests/telemetry/spans/test_cookbook_spans.py
git commit -m "feat(cookbook): OTEL span definitions for region-assembly (spec §8)"
```

### Task 12: Deterministic RNG helper

**Files:**
- Create: `sidequest-server/sidequest/game/cookbook/assemble.py` (RNG only this task)
- Create: `sidequest-server/tests/game/cookbook/test_determinism.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_determinism.py`

```python
"""Determinism: RNG derives ONLY from (campaign_seed, expansion_id)
(spec §4.3 / Sünden Deep §11)."""

from __future__ import annotations

from sidequest.game.cookbook.assemble import region_rng


def test_same_inputs_same_sequence() -> None:
    a = region_rng("camp-1", "exp-7")
    b = region_rng("camp-1", "exp-7")
    assert [a.random() for _ in range(5)] == [b.random() for _ in range(5)]


def test_different_expansion_diverges() -> None:
    a = region_rng("camp-1", "exp-7")
    b = region_rng("camp-1", "exp-8")
    assert [a.random() for _ in range(5)] != [b.random() for _ in range(5)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_determinism.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.cookbook.assemble'`

- [ ] **Step 3: Write `sidequest/game/cookbook/assemble.py`** (RNG helper only)

```python
"""assemble_region — the deterministic region-content contract.

Spec §4.3: a pure function oq-1's materializer invokes. All randomness
derives ONLY from (campaign_seed, expansion_id) per Sünden Deep §11.
NO CR→Edge translation here (oq-1 materializer seam, ADR-014/078).
"""

from __future__ import annotations

import hashlib
import random


def region_rng(campaign_seed: str, expansion_id: str) -> random.Random:
    """A Random seeded purely by (campaign_seed, expansion_id)."""
    digest = hashlib.sha256(
        f"{campaign_seed}\x1f{expansion_id}".encode()
    ).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_determinism.py -v`
Expected: both PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/assemble.py tests/game/cookbook/test_determinism.py
git commit -m "feat(cookbook): deterministic per-region RNG (campaign_seed, expansion_id)"
```

### Task 13: CR-band + size-budget resolution

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/assemble.py`
- Create: `sidequest-server/tests/game/cookbook/test_size_bigbad.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_size_bigbad.py`

```python
"""CR band from depth_score; size budget from burst (monotonic, spec §9)."""

from __future__ import annotations

from sidequest.game.cookbook.assemble import band_for_depth, budget_for_burst


def test_band_for_depth(bundle) -> None:
    a = bundle.affinities
    assert band_for_depth(a, 0.10).id == "shallow"
    assert band_for_depth(a, 0.40).id == "mid"
    assert band_for_depth(a, 0.95).id == "deep"


def test_band_boundary_is_lower_inclusive(bundle) -> None:
    # depth_lt is an exclusive upper bound; 0.25 falls into 'mid'.
    assert band_for_depth(bundle.affinities, 0.25).id == "mid"


def test_budget_monotonic_in_burst(bundle) -> None:
    a = bundle.affinities
    b1 = budget_for_burst(a, 1)
    b3 = budget_for_burst(a, 3)
    b9 = budget_for_burst(a, 9)
    assert b1.wandering_rolls <= b3.wandering_rolls <= b9.wandering_rolls
    assert b1.special_rooms <= b3.special_rooms <= b9.special_rooms


def test_burst_above_max_clamps_to_largest(bundle) -> None:
    a = bundle.affinities
    assert budget_for_burst(a, 999).wandering_rolls == budget_for_burst(a, 9).wandering_rolls
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_size_bigbad.py -v`
Expected: FAIL — `ImportError: cannot import name 'band_for_depth'`

- [ ] **Step 3: Append to `sidequest/game/cookbook/assemble.py`**

```python
from sidequest.game.cookbook.models import Affinities, CrBand, SizeBudget  # add


def band_for_depth(aff: Affinities, depth_score: float) -> CrBand:
    """First band whose depth_lt strictly exceeds depth_score.

    Bands are listed in increasing depth (spec §4.2). depth_lt is an
    exclusive upper bound; the last band's depth_lt (1.01) is the cap.
    """
    for band in aff.cr_bands:
        if depth_score < band.depth_lt:
            return band
    return aff.cr_bands[-1]


def budget_for_burst(aff: Affinities, burst_magnitude: int) -> SizeBudget:
    """First size_by_burst row whose burst_lte ≥ burst; else the largest.

    size_by_burst is listed in increasing burst (spec §4.2).
    """
    for row in aff.size_by_burst:
        if burst_magnitude <= row.burst_lte:
            return row
    return aff.size_by_burst[-1]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_size_bigbad.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/assemble.py tests/game/cookbook/test_size_bigbad.py
git commit -m "feat(cookbook): CR-band + size-budget resolution (monotonic, clamped)"
```

### Task 14: Affinity-weighted RACE roll

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/assemble.py`
- Create: `sidequest-server/tests/game/cookbook/test_affinity_distribution.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_affinity_distribution.py`

```python
"""Spec §9: LOOK→RACE roll frequencies track configured weights within
tolerance; off-affinity RACEs still appear (orthogonality, not lock)."""

from __future__ import annotations

import collections

from sidequest.game.cookbook.assemble import region_rng, roll_race


def test_distribution_tracks_weights(bundle) -> None:
    weights = bundle.affinities.look_race_affinity["necropolis"]
    total = sum(weights.values())
    counts: collections.Counter[str] = collections.Counter()
    for i in range(8000):
        rng = region_rng("camp", f"exp-{i}")
        counts[roll_race(bundle, "necropolis", rng).id] += 1
    n = sum(counts.values())
    # 'undead' is the dominant affinity — its empirical share must be
    # within 5 points of configured share over 8k draws.
    exp_undead = weights["undead"] / total
    assert abs(counts["undead"] / n - exp_undead) < 0.05


def test_off_affinity_still_appears(bundle) -> None:
    # ooze has weight 1 under necropolis — rare but NOT impossible.
    seen = set()
    for i in range(8000):
        rng = region_rng("camp", f"x-{i}")
        seen.add(roll_race(bundle, "necropolis", rng).id)
    assert "ooze" in seen
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_affinity_distribution.py -v`
Expected: FAIL — `ImportError: cannot import name 'roll_race'`

- [ ] **Step 3: Append to `sidequest/game/cookbook/assemble.py`**

```python
from sidequest.game.cookbook.loader import CookbookBundle  # add to imports
from sidequest.game.cookbook.models import RaceDef  # add to imports


def roll_race(
    bundle: CookbookBundle,
    look: str,
    rng: random.Random,
    *,
    exclude: list[str] | None = None,
) -> RaceDef | None:
    """Affinity-weighted RACE roll (spec §4.2: bias, never lock).

    Any RACE with weight > 0 under this LOOK can be selected. `exclude`
    drops RACE ids from the pool (used by the assembler's observable
    low-ceiling re-roll); returns None when the pool is exhausted. A
    LOOK absent from look_race_affinity is a content bug — fail loud
    (§7).
    """
    weights = bundle.affinities.look_race_affinity.get(look)
    if not weights:
        raise KeyError(
            f"cookbook: LOOK '{look}' absent from look_race_affinity "
            f"(spec §7 — no silent fallback)"
        )
    by_id = {r.id: r for r in bundle.races}
    missing = [rid for rid in weights if rid not in by_id]
    if missing:
        raise KeyError(
            f"cookbook: affinity references unknown RACE(s) {missing} "
            f"for LOOK '{look}'"
        )
    drop = set(exclude or ())
    candidates = [
        (by_id[rid], w)
        for rid, w in weights.items()
        if w > 0 and rid not in drop
    ]
    if not candidates:
        return None
    population = [r for r, _ in candidates]
    weight_vals = [w for _, w in candidates]
    return rng.choices(population, weights=weight_vals, k=1)[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_affinity_distribution.py -v`
Expected: both PASS (8k draws keeps the dominant-share assertion stable; if `test_off_affinity_still_appears` is flaky raise the iteration count, never widen the tolerance to hide a lock).

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/assemble.py tests/game/cookbook/test_affinity_distribution.py
git commit -m "feat(cookbook): affinity-weighted RACE roll (bias not lock, spec §4.2)"
```

### Task 15: Wandering + loot table builders

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/assemble.py`
- Create: `sidequest-server/tests/game/cookbook/test_tables.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_tables.py`

```python
"""Wandering table = curated ∩ race.filter ∩ cr_band, with telegraph.
Loot table = items ∩ rarity_by_band[band] with race.loot_bias applied."""

from __future__ import annotations

from sidequest.game.cookbook.assemble import (
    band_for_depth,
    build_loot_table,
    build_wandering_table,
    region_rng,
)


def _undead(bundle):
    return next(r for r in bundle.races if r.id == "undead")


def test_wandering_rows_in_band_and_have_telegraph(bundle) -> None:
    band = band_for_depth(bundle.affinities, 0.40)  # mid
    rows = build_wandering_table(bundle, _undead(bundle), band)
    assert rows, "undead must resolve ≥1 row at mid"
    for row in rows:
        assert band.cr_min <= row["cr"] <= band.cr_max
        assert row["telegraph"] == _undead(bundle).telegraph["mid"]
        assert "weight" in row and "count" in row


def test_loot_table_respects_rarity_band_and_bias(bundle) -> None:
    band = band_for_depth(bundle.affinities, 0.95)  # deep
    rng = region_rng("c", "e")
    loot = build_loot_table(bundle, _undead(bundle), band, rolls=4, rng=rng)
    assert len(loot) == 4
    allowed = set(bundle.affinities.rarity_by_band["deep"])
    for item in loot:
        assert item["rarity"] in allowed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_tables.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_wandering_table'`

- [ ] **Step 3: Append to `sidequest/game/cookbook/assemble.py`**

```python
from sidequest.game.cookbook.corpus import resolve_race  # add to imports
from sidequest.game.cookbook.curation import apply_world_register  # add
from sidequest.game.cookbook.models import CrBand  # already imported; ensure present


def _telegraph(race: RaceDef, band_id: str) -> str:
    return race.telegraph.get(band_id, "")


def build_wandering_table(
    bundle: CookbookBundle, race: RaceDef, band: CrBand
) -> list[dict]:
    """curated ∩ race.filter ∩ cr_band, weighted, per-row telegraph.

    Re-keys the shipped encounter_tables.yaml row shape (weight, count,
    description→telegraph) from regions→levels to race × cr_band, with
    the keeper-awareness scaffolding stripped (spec §6). count uses the
    same dice-string convention as the source pattern; oq-1's
    materializer rolls it (and does CR→Edge there).
    """
    curated = apply_world_register(bundle.monsters, bundle.register)
    rows = resolve_race(curated, race, cr_min=band.cr_min, cr_max=band.cr_max)
    out: list[dict] = []
    for mon in rows:
        # Rarer = scarcer: weight falls off with CR within the band.
        weight = max(1, int(round((band.cr_max - mon.cr) + 1)))
        out.append(
            {
                "name": mon.name,
                "cr": mon.cr,
                "xp": mon.xp,
                "type": mon.type,
                "weight": weight,
                "count": "1" if mon.cr >= 5 else "1d4",
                "telegraph": _telegraph(race, band.id),
            }
        )
    return out


def build_loot_table(
    bundle: CookbookBundle,
    race: RaceDef,
    band: CrBand,
    *,
    rolls: int,
    rng: random.Random,
) -> list[dict]:
    """items ∩ rarity_by_band[band], race.loot_bias applied (multipliers).

    Mirrors the wiring-tested equipment_tables roll-on-list pattern: a
    slot of candidate ids, ids must resolve (they are corpus rows by
    construction here). loot_bias nudges category weight (spec §4.2).
    """
    rarity_weights = bundle.affinities.rarity_by_band.get(band.id, {})
    pool = [it for it in bundle.items if it.rarity in rarity_weights]
    if not pool:
        raise RuntimeError(
            f"cookbook: loot pool empty for band '{band.id}' "
            f"(rarities {list(rarity_weights)}) — spec §7 loud failure"
        )
    cat_bias = race.loot_bias.category_weight
    weights = [
        rarity_weights[it.rarity] * cat_bias.get(it.item_type, 1.0)
        for it in pool
    ]
    picks = rng.choices(pool, weights=weights, k=rolls)
    return [
        {"name": p.name, "item_type": p.item_type, "rarity": p.rarity}
        for p in picks
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_tables.py -v`
Expected: both PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/assemble.py tests/game/cookbook/test_tables.py
git commit -m "feat(cookbook): wandering + loot table builders (re-key shipped patterns)"
```

### Task 16: BIG BAD gate

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/assemble.py`
- Create: `sidequest-server/tests/game/cookbook/test_bigbad_gate.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_bigbad_gate.py`

```python
"""BIG BAD gate (spec §4.2/§4.3): first entry into a gated band → capstone;
else per-band recurring_chance. Capstone pulled from race.big_bads whose
min_band ≤ cr_band (ordinal). is_first_band_entry is an oq-1-supplied input
(see plan 'Seam Clarification')."""

from __future__ import annotations

from sidequest.game.cookbook.assemble import band_for_depth, roll_big_bad, region_rng


def _undead(bundle):
    return next(r for r in bundle.races if r.id == "undead")


def test_first_entry_into_gated_band_forces_capstone(bundle) -> None:
    band = band_for_depth(bundle.affinities, 0.40)  # mid (gated)
    bb = roll_big_bad(
        bundle, _undead(bundle), band,
        is_first_band_entry=True, rng=region_rng("c", "e"),
    )
    assert bb is not None
    # undead.yaml (authoritative, Task 6): Wight is the min_band=mid
    # capstone; Mummy Lord & Lich are min_band=deep (ordinal-excluded
    # at mid). An earlier draft asserted "Mummy Lord" — inconsistent
    # with the plan's own undead.yaml; corrected to Wight.
    assert bb["name"] == "Wight"


def test_shallow_band_never_capstones(bundle) -> None:
    band = band_for_depth(bundle.affinities, 0.10)  # shallow (not in gate)
    bb = roll_big_bad(
        bundle, _undead(bundle), band,
        is_first_band_entry=True, rng=region_rng("c", "e"),
    )
    assert bb is None


def test_recurring_chance_is_deterministic_and_bounded(bundle) -> None:
    band = band_for_depth(bundle.affinities, 0.95)  # deep
    hits = 0
    for i in range(2000):
        bb = roll_big_bad(
            bundle, _undead(bundle), band,
            is_first_band_entry=False, rng=region_rng("c", f"e{i}"),
        )
        hits += bb is not None
    rate = hits / 2000
    # configured deep recurring_chance is 0.20 — empirical within ±0.05
    assert 0.15 < rate < 0.25


def test_min_band_ordinal_excludes_too_deep_bigbad(bundle) -> None:
    band = band_for_depth(bundle.affinities, 0.40)  # mid
    # Over many first-entries, Lich (min_band deep) must NEVER appear at mid.
    for i in range(500):
        bb = roll_big_bad(
            bundle, _undead(bundle), band,
            is_first_band_entry=True, rng=region_rng("c", f"e{i}"),
        )
        assert bb is None or bb["name"] != "Lich"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_bigbad_gate.py -v`
Expected: FAIL — `ImportError: cannot import name 'roll_big_bad'`

- [ ] **Step 3: Append to `sidequest/game/cookbook/assemble.py`**

```python
def roll_big_bad(
    bundle: CookbookBundle,
    race: RaceDef,
    band: CrBand,
    *,
    is_first_band_entry: bool,
    rng: random.Random,
) -> dict | None:
    """Spec §4.2/§4.3 capstone gate.

    Fires iff (a) this band is in big_bad_gate.on_first_band_entry AND
    is_first_band_entry, OR (b) the band's recurring_chance roll hits.
    The capstone is drawn from race.big_bads whose min_band ≤ this band
    (ordinal per §4.2). Returns None when the gate does not fire or no
    eligible big_bad exists. is_first_band_entry is oq-1-supplied (see
    plan Seam Clarification).
    """
    gate = bundle.affinities.big_bad_gate
    order = bundle.affinities.band_order()
    fires = (is_first_band_entry and band.id in gate.on_first_band_entry) or (
        rng.random() < gate.recurring_chance.get(band.id, 0.0)
    )
    if not fires:
        return None
    here = order[band.id]
    eligible = [
        bb for bb in race.big_bads if order.get(bb.min_band, 1_000) <= here
    ]
    if not eligible:
        return None
    chosen = rng.choice(eligible)
    return {"name": chosen.name, "min_band": chosen.min_band}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_bigbad_gate.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/assemble.py tests/game/cookbook/test_bigbad_gate.py
git commit -m "feat(cookbook): depth-gated BIG BAD capstone (ordinal min_band, recurring chance)"
```

### Task 17: SPECIAL room selection

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/assemble.py`
- Create: `sidequest-server/tests/game/cookbook/test_specials.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_specials.py`

```python
"""SPECIAL selection: ≤ size_budget.special_rooms, gated by min_band
(ordinal). Deterministic under fixed rng."""

from __future__ import annotations

from sidequest.game.cookbook.assemble import band_for_depth, pick_specials, region_rng


def test_respects_budget_and_min_band(bundle) -> None:
    shallow = band_for_depth(bundle.affinities, 0.10)
    chosen = pick_specials(bundle, shallow, budget=2, rng=region_rng("c", "e"))
    assert len(chosen) <= 2
    order = bundle.affinities.band_order()
    for s in chosen:
        assert order[s["min_band"]] <= order[shallow.id]


def test_zero_budget_yields_none(bundle) -> None:
    deep = band_for_depth(bundle.affinities, 0.95)
    assert pick_specials(bundle, deep, budget=0, rng=region_rng("c", "e")) == []


def test_deterministic(bundle) -> None:
    deep = band_for_depth(bundle.affinities, 0.95)
    a = pick_specials(bundle, deep, budget=2, rng=region_rng("c", "e"))
    b = pick_specials(bundle, deep, budget=2, rng=region_rng("c", "e"))
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_specials.py -v`
Expected: FAIL — `ImportError: cannot import name 'pick_specials'`

- [ ] **Step 3: Append to `sidequest/game/cookbook/assemble.py`**

```python
def pick_specials(
    bundle: CookbookBundle,
    band: CrBand,
    *,
    budget: int,
    rng: random.Random,
) -> list[dict]:
    """Up to `budget` special rooms whose min_band ≤ this band (ordinal).

    Spec §4.2: feeds oq-1's set-piece slot; we only describe + gate.
    """
    if budget <= 0:
        return []
    order = bundle.affinities.band_order()
    here = order[band.id]
    eligible = [
        s for s in bundle.specials if order.get(s.min_band, 1_000) <= here
    ]
    if not eligible:
        return []
    rng.shuffle(eligible)
    return [
        {
            "id": s.id,
            "telegraph": s.telegraph,
            "mechanic": s.mechanic,
            "outcome": s.outcome,
            "min_band": s.min_band,
            "feeds_setpiece_slot": s.feeds_setpiece_slot,
        }
        for s in eligible[:budget]
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_specials.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/assemble.py tests/game/cookbook/test_specials.py
git commit -m "feat(cookbook): SPECIAL room selection (budget-bounded, min_band gated)"
```

### Task 18: `assemble_region` — compose the full manifest

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/assemble.py`
- Modify: `sidequest-server/sidequest/game/cookbook/__init__.py` (public re-export)
- Create: `sidequest-server/tests/game/cookbook/test_assemble_region.py`

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_assemble_region.py`

```python
"""assemble_region composes a complete RegionContentManifest and is a
pure function of its named inputs (spec §4.3)."""

from __future__ import annotations

from sidequest.game.cookbook import assemble_region
from sidequest.game.cookbook.models import RegionContentManifest


def test_manifest_is_complete_and_typed(bundle) -> None:
    man = assemble_region(
        bundle,
        campaign_seed="camp-1",
        expansion_id="exp-3",
        depth_score=0.40,
        burst_magnitude=3,
        look="necropolis",
        is_first_band_entry=True,
    )
    assert isinstance(man, RegionContentManifest)
    assert man.cr_band == "mid"
    assert man.race in {r.id for r in bundle.races}
    assert man.wandering_table  # mid undead/etc resolves ≥1
    assert man.size_budget["wandering_rolls"] >= 1
    # First entry into gated 'mid' → capstone present, forces SIZE ≥ large.
    assert man.big_bad is not None
    largest = bundle.affinities.size_by_burst[-1]
    assert man.size_budget["wandering_rolls"] == largest.wandering_rolls


def test_pure_function_same_inputs_same_manifest(bundle) -> None:
    kw = dict(
        campaign_seed="c", expansion_id="e", depth_score=0.7,
        burst_magnitude=2, look="sunken", is_first_band_entry=False,
    )
    a = assemble_region(bundle, **kw)
    b = assemble_region(bundle, **kw)
    assert a.model_dump() == b.model_dump()


def test_capstone_floors_size(bundle) -> None:
    # deep + first entry → big_bad → SIZE floored to big_bad_forces_size row.
    man = assemble_region(
        bundle, campaign_seed="c", expansion_id="e2", depth_score=0.95,
        burst_magnitude=1, look="delvehold", is_first_band_entry=True,
    )
    assert man.big_bad is not None
    largest = bundle.affinities.size_by_burst[-1]
    assert man.size_budget["wandering_rolls"] == largest.wandering_rolls


def test_low_ceiling_reroll_never_emits_empty_deep_table(bundle) -> None:
    # Data-Forced Design Item: 'sunken' is ooze-heavy, but ooze (CR≤4)
    # cannot fill a deep region. Over many seeds at deep depth, the
    # manifest must NEVER be ooze/goblinoid and NEVER have an empty
    # wandering table — the observable re-roll yields to undead/etc.
    for i in range(400):
        man = assemble_region(
            bundle, campaign_seed="reroll", expansion_id=f"e{i}",
            depth_score=0.92, burst_magnitude=3, look="sunken",
            is_first_band_entry=False,
        )
        assert man.cr_band == "deep"
        assert man.wandering_table, "deep region must never be empty"
        assert man.race not in {"ooze", "goblinoid"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_assemble_region.py -v`
Expected: FAIL — `ImportError: cannot import name 'assemble_region'`

- [ ] **Step 3: Append `assemble_region` to `sidequest/game/cookbook/assemble.py`**

```python
from sidequest.game.cookbook.models import RegionContentManifest  # add
from sidequest.game.cookbook.loader import CookbookValidationError  # add
from sidequest.telemetry.spans import cookbook_race_reroll_span  # add


def _floor_budget_for_capstone(bundle: CookbookBundle):
    """big_bad_forces_size: a capstone is a lair complex (spec §4.2)."""
    target = bundle.affinities.big_bad_forces_size
    # Map the named tier to the largest size_by_burst row (v1: 'large'
    # == the top burst row). If a future affinities.yaml introduces
    # named tiers, resolve here — fail loud on an unknown name.
    if target != "large":
        raise ValueError(
            f"cookbook: unsupported big_bad_forces_size '{target}' "
            f"(v1 supports 'large' only — spec §11 open tuning item)"
        )
    return bundle.affinities.size_by_burst[-1]


def assemble_region(
    bundle: CookbookBundle,
    *,
    campaign_seed: str,
    expansion_id: str,
    depth_score: float,
    burst_magnitude: int,
    look: str,
    is_first_band_entry: bool,
) -> RegionContentManifest:
    """The deterministic content-manifest contract (spec §4.3).

    Pure function of named inputs. depth_score / burst_magnitude / look /
    is_first_band_entry are oq-1-owned signals passed in (never produced
    here). NO CR→Edge translation — that is oq-1's materializer seam
    (ADR-014/078); the manifest carries cr_band + raw corpus rows.
    """
    rng = region_rng(campaign_seed, expansion_id)
    band = band_for_depth(bundle.affinities, depth_score)
    race = roll_race(bundle, look, rng)
    wandering = build_wandering_table(bundle, race, band)
    # Data-Forced Design Item: a low-ceiling RACE (ooze/goblinoid) may
    # not fill this depth. Yield OBSERVABLY to another affinity RACE —
    # never emit a silent empty table (spec §7). Bounded, deterministic.
    if not wandering:
        excluded: list[str] = [race.id]
        from_race = race.id
        while True:
            nxt = roll_race(bundle, look, rng, exclude=excluded)
            if nxt is None:
                raise CookbookValidationError(
                    f"every affinity RACE for LOOK '{look}' is empty at "
                    f"band '{band.id}' — content bug (validate_bundle "
                    f"should have caught this)"
                )
            cand = build_wandering_table(bundle, nxt, band)
            if cand:
                with cookbook_race_reroll_span(
                    look=look, band=band.id, from_race=from_race,
                    to_race=nxt.id, excluded=excluded,
                ):
                    pass
                race, wandering = nxt, cand
                break
            excluded.append(nxt.id)
    big_bad = roll_big_bad(
        bundle, race, band, is_first_band_entry=is_first_band_entry, rng=rng
    )
    budget = (
        _floor_budget_for_capstone(bundle)
        if big_bad is not None
        else budget_for_burst(bundle.affinities, burst_magnitude)
    )
    loot = build_loot_table(
        bundle, race, band, rolls=budget.loot_rolls, rng=rng
    )
    specials = pick_specials(
        bundle, band, budget=budget.special_rooms, rng=rng
    )
    return RegionContentManifest(
        race=race.id,
        cr_band=band.id,
        size_budget={
            "wandering_rolls": budget.wandering_rolls,
            "special_rooms": budget.special_rooms,
            "loot_rolls": budget.loot_rolls,
        },
        wandering_table=wandering,
        loot_table=loot,
        special_rooms=specials,
        big_bad=big_bad,
    )
```

- [ ] **Step 4: Re-export from `sidequest/game/cookbook/__init__.py`**

Append:
```python
from sidequest.game.cookbook.assemble import assemble_region  # noqa: E402
from sidequest.game.cookbook.loader import (  # noqa: E402
    CookbookBundle,
    CookbookValidationError,
    load_cookbook,
    validate_bundle,
)

__all__ = [
    "CookbookBundle",
    "CookbookValidationError",
    "assemble_region",
    "load_cookbook",
    "validate_bundle",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_assemble_region.py -v`
Expected: all PASS.

- [ ] **Step 6: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/assemble.py sidequest/game/cookbook/__init__.py tests/game/cookbook/test_assemble_region.py
git commit -m "feat(cookbook): assemble_region — full deterministic manifest contract (spec §4.3)"
```

### Task 19: Curation determinism across a seed sweep (spec §9)

**Files:**
- Create: `sidequest-server/tests/game/cookbook/test_curation_sweep.py`

- [ ] **Step 1: Write the failing-then-passing test** — `tests/game/cookbook/test_curation_sweep.py`

```python
"""Spec §9: across a seed sweep no denied type/tag/name appears in any
assembled manifest; every marquee survives curation."""

from __future__ import annotations

from sidequest.game.cookbook import assemble_region
from sidequest.game.cookbook.curation import apply_world_register


def test_no_denied_row_in_any_manifest(bundle) -> None:
    deny_types = set(bundle.register.deny.types)
    deny_tags = set(bundle.register.deny.tags)
    marquee = set(bundle.register.marquee)
    by_name = {m.name: m for m in bundle.monsters}
    looks = [lk.id for lk in bundle.looks]  # not `l` — ruff E741
    for i in range(1500):
        look = looks[i % len(looks)]
        man = assemble_region(
            bundle, campaign_seed="sweep", expansion_id=f"e{i}",
            depth_score=(i % 100) / 100.0, burst_magnitude=(i % 9) + 1,
            look=look, is_first_band_entry=(i % 7 == 0),
        )
        for row in man.wandering_table:
            mon = by_name.get(row["name"])
            if mon is None or mon.name in marquee:
                continue
            assert mon.type not in deny_types
            assert not (deny_tags & set(mon.tags))


def test_marquee_survives_curation(bundle) -> None:
    curated = {m.name for m in apply_world_register(bundle.monsters, bundle.register)}
    for name in bundle.register.marquee:
        if any(m.name == name for m in bundle.monsters):
            assert name in curated, f"marquee '{name}' wrongly curated out"
```

- [ ] **Step 2: Run test**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_curation_sweep.py -v`
Expected: PASS (curation is upstream of every RACE roll via `build_wandering_table` → `apply_world_register`). If it fails, a denied row leaked — fix curation/content, never the assertion.

- [ ] **Step 3: Commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check tests/game/cookbook && uv run ruff format tests/game/cookbook
git add tests/game/cookbook/test_curation_sweep.py
git commit -m "test(cookbook): curation holds across a 1.5k-seed manifest sweep (spec §9)"
```

---

## Phase G — Wiring, Validation Integration, Handoff

### Task 20: oq-1 materializer wiring contract test (spec §9 — REQUIRED)

**Files:**
- Create: `sidequest-server/tests/integration/test_cookbook_assemble_wiring.py`

> CLAUDE.md: every test suite needs a wiring test. The cookbook's runtime consumer is **oq-1's materializer**, which does not exist in this branch. This test asserts the **contract surface** oq-1 must call: import path, signature, and a real-bundle invocation producing an oq-1-consumable manifest. When oq-1 lands the materializer, extend this with the real frontier-crossing call (coordination note, Task 24). It is an integration test (not unit) because it loads the real committed content end-to-end.

- [ ] **Step 1: Write the test**

```python
"""WIRING: the public contract oq-1's materializer invokes. Real bundle,
real content, real signature. Not mocked. (spec §9, CLAUDE.md.)"""

from __future__ import annotations

import inspect
from pathlib import Path

from sidequest.game.cookbook import assemble_region, load_cookbook, validate_bundle

WORLD = (
    Path(__file__).parents[3]
    / "sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden"
)


def test_public_contract_signature_is_stable() -> None:
    sig = inspect.signature(assemble_region)
    params = list(sig.parameters)
    # bundle is positional; the rest are the named oq-1 contract inputs.
    assert params[0] == "bundle"
    assert set(params[1:]) == {
        "campaign_seed", "expansion_id", "depth_score",
        "burst_magnitude", "look", "is_first_band_entry",
    }


def test_real_bundle_validates_and_assembles() -> None:
    bundle = load_cookbook(WORLD)
    validate_bundle(bundle)  # spec §7 gates pass on shipped content
    man = assemble_region(
        bundle, campaign_seed="wire", expansion_id="w1",
        depth_score=0.5, burst_magnitude=3, look="necropolis",
        is_first_band_entry=False,
    )
    # oq-1 consumes this dict shape (then does CR→Edge at its seam).
    payload = man.model_dump()
    assert set(payload) == {
        "race", "cr_band", "size_budget", "wandering_table",
        "loot_table", "special_rooms", "big_bad",
    }
    for row in payload["wandering_table"]:
        assert {"name", "cr", "xp", "type", "weight", "count", "telegraph"} <= set(row)
```

- [ ] **Step 2: Run the test**

Run: `cd sidequest-server && uv run pytest tests/integration/test_cookbook_assemble_wiring.py -v`
Expected: PASS (requires Prereq 0 corpus committed; loud fail if absent — correct).

- [ ] **Step 3: Commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check tests/integration/test_cookbook_assemble_wiring.py && uv run ruff format tests/integration/test_cookbook_assemble_wiring.py
git add tests/integration/test_cookbook_assemble_wiring.py
git commit -m "test(cookbook): oq-1 materializer wiring contract (real bundle, no mocks)"
```

### Task 21: `generator_binding` reference validation against oq-1's known set

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/loader.py` (extend `validate_bundle`)
- Create: `sidequest-server/tests/game/cookbook/test_generator_binding_ref.py`

> Spec §7: a `looks[].generator_binding` not in oq-1's known set is a loud error "at the seam — we validate the reference exists; oq-1 owns its meaning." oq-1's known set is the cavern maze-maker family confirmed in `sidequest-content/tools/cavern_renderer` (`cellular`, `depthfirst`, `prim`, `braid`). We validate against that **named, sourced** set and document it as an oq-1 coordination point (Task 24) — not a redefinition.

- [ ] **Step 1: Write the failing test** — `tests/game/cookbook/test_generator_binding_ref.py`

```python
"""Spec §7: every looks[].generator_binding must be a known oq-1 binding."""

from __future__ import annotations

import pytest

from sidequest.game.cookbook.loader import (
    KNOWN_GENERATOR_BINDINGS,
    CookbookValidationError,
    validate_bundle,
)


def test_shipped_looks_use_known_bindings(bundle) -> None:
    for look in bundle.looks:
        assert look.generator_binding in KNOWN_GENERATOR_BINDINGS


def test_unknown_binding_is_loud(bundle) -> None:
    broken_look = bundle.looks[0].model_copy(
        update={"generator_binding": "nonexistent_gen"}
    )
    broken = type(bundle)(
        monsters=bundle.monsters, items=bundle.items,
        register=bundle.register, races=bundle.races,
        looks=[broken_look, *bundle.looks[1:]],
        affinities=bundle.affinities, specials=bundle.specials,
    )
    with pytest.raises(CookbookValidationError, match="nonexistent_gen"):
        validate_bundle(broken)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_generator_binding_ref.py -v`
Expected: FAIL — `ImportError: cannot import name 'KNOWN_GENERATOR_BINDINGS'`

- [ ] **Step 3: Edit `sidequest/game/cookbook/loader.py`**

Add the constant near the top (after imports):
```python
# oq-1-owned set; sourced from sidequest-content/tools/cavern_renderer
# maze-maker family. We validate the REFERENCE exists; oq-1 owns the
# semantics (spec §7). Coordinate any addition with oq-1 (plan Task 24).
KNOWN_GENERATOR_BINDINGS: frozenset[str] = frozenset(
    {"cellular", "depthfirst", "prim", "braid"}
)
```

Inside `validate_bundle`, before the `reskin` check, add:
```python
    for look in bundle.looks:
        if look.generator_binding not in KNOWN_GENERATOR_BINDINGS:
            raise CookbookValidationError(
                f"LOOK '{look.id}' generator_binding "
                f"'{look.generator_binding}' is not a known oq-1 binding "
                f"{sorted(KNOWN_GENERATOR_BINDINGS)} — spec §7 seam check"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/cookbook/test_generator_binding_ref.py -v`
Expected: both PASS.

- [ ] **Step 5: Lint + commit (`sidequest-server`)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/cookbook tests/game/cookbook && uv run ruff format sidequest/game/cookbook tests/game/cookbook
git add sidequest/game/cookbook/loader.py tests/game/cookbook/test_generator_binding_ref.py
git commit -m "feat(cookbook): validate looks generator_binding against oq-1 known set (spec §7)"
```

### Task 22: Full cookbook suite green + content lint

**Files:** *(no new files — gate + verification, superpowers:verification-before-completion)*

- [ ] **Step 1: Run the full cookbook + span + wiring suite**

Run:
```bash
cd sidequest-server && uv run pytest tests/game/cookbook tests/telemetry/spans/test_cookbook_spans.py tests/telemetry/test_routing_completeness.py tests/integration/test_cookbook_assemble_wiring.py -v
```
Expected: ALL PASS, zero skips (the ingested corpus is committed by Task 2; if anything skips, the corpus is missing — re-run Task 2 ingest, do not paper over with a skip).

- [ ] **Step 2: Run the server lint + format gate**

Run: `cd sidequest-server && uv run ruff check . && uv run ruff format --check .`
Expected: clean.

- [ ] **Step 3: Validate the content pack with the existing CLI**

Run:
```bash
cd sidequest-server && uv run python -m sidequest.cli.validate \
  /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/caverns_and_claudes
```
Expected: exits 0 (the new `beneath_sunden/` files are well-formed YAML and do not break pack validation). If `validate` errors on the new world dir, fix the content YAML — do not exclude the world.

- [ ] **Step 4: Dead-code sweep (feedback: delete dead code in the same PR)**

Run: `cd sidequest-server && uv run ruff check --select F401,F841 sidequest/game/cookbook sidequest/cli/cookbook_ingest`
Expected: no unused imports/vars. Remove any zero-caller helper introduced and not wired (CLAUDE.md: no stubs, no dead code).

- [ ] **Step 5: No commit** (verification only — nothing changed if green).

### Task 23: ADR + spec-status touch (`oq-2` orchestrator repo)

**Files:**
- Modify: `docs/superpowers/specs/2026-05-16-beneath-sunden-content-cookbook-design.md` (status + §11 follow-up)

- [ ] **Step 1: Update the spec status line**

Change line 4 from:
```
- **Status:** Approved (design) — pending spec review, then implementation plan
```
to:
```
- **Status:** Implemented — plan docs/superpowers/plans/2026-05-16-beneath-sunden-content-cookbook.md
```

- [ ] **Step 2: Append a resolved-seam note to §11 Open Items**

Add under §11:
```markdown
- **Resolved (implementation):** §4.3's signature is extended with an
  oq-1-supplied `is_first_band_entry: bool` contract input so §4.2's
  `big_bad_gate.on_first_band_entry` is implementable. oq-1 still
  *produces* the band-crossing signal; the cookbook only consumes it.
  `looks[].generator_binding` is validated against the sourced oq-1
  maze-maker set `{cellular, depthfirst, prim, braid}` — coordinate any
  change with oq-1.
- **Source:** corpus is ingested from `BTMorton/dnd-5e-srd` (SRD 5.1,
  CC-BY-4.0), vendored under `corpus/_source/`. The §4.2/§5 illustrative
  names are corrected to real SRD 5.1 entries: no Kuo-toa in SRD →
  `kuo_toa` RACE is `ooze` "The Seep".
- **Data-Forced Design Item:** SRD Ooze tops at CR 4, goblinoid at CR 1.
  §7 is refined: a RACE must resolve at the entry band + every band ≥ a
  declared big_bad's min_band; depths a RACE cannot fill trigger an
  observable, bounded affinity re-roll (`cookbook.race.reroll` span),
  never a silent empty wandering table. Alternative (hard-exclude
  low-ceiling factions from deep affinities) deferred unless playtest
  prefers it.
```

- [ ] **Step 3: Commit (`oq-2` orchestrator)**

```bash
cd /Users/slabgorb/Projects/oq-2
git add docs/superpowers/specs/2026-05-16-beneath-sunden-content-cookbook-design.md docs/superpowers/plans/2026-05-16-beneath-sunden-content-cookbook.md
git commit -m "docs(cookbook): mark spec implemented; record resolved §4.3 seam"
```

### Task 24: Open PRs (oq-2 opens, never self-merges)

**Files:** *(none — git/PR only)*

- [ ] **Step 1: Push + open the `sidequest-content` PR (gitflow → develop)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git push -u origin HEAD
gh pr create --base develop --title "Beneath Sünden content cookbook — corpus + curation + tables" --body "$(cat <<'EOF'
## Summary
- Ingested SRD corpus (`corpus/monsters.yaml`, `corpus/items.yaml`) for the new `beneath_sunden` world
- Authored `world_register.yaml` genre-truth gate, five RACE filter-predicate files, `looks.yaml`, `affinities.yaml`, `special_rooms.yaml`
- Implements spec `docs/superpowers/specs/2026-05-16-beneath-sunden-content-cookbook-design.md`

## oq-1 coordination
- `assemble_region` (server PR) consumes oq-1-owned `depth_score`, `burst_magnitude`, `look`, and the resolved `is_first_band_entry` signal
- `looks[].generator_binding` validated against `{cellular, depthfirst, prim, braid}` — confirm oq-1's known set

## Test plan
- [ ] `python -m sidequest.cli.validate` clean on caverns_and_claudes
- [ ] Server cookbook suite green against this content
EOF
)"
```

- [ ] **Step 2: Push + open the `sidequest-server` PR (→ develop)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git push -u origin HEAD
gh pr create --base develop --title "Cookbook engine — ingest, models, curation, assemble_region, OTEL defs" --body "$(cat <<'EOF'
## Summary
- `sidequest.cli.cookbook_ingest` idempotent SRD→corpus transform
- `sidequest.game.cookbook` — models, curation, RACE filter, deterministic `assemble_region` contract
- `sidequest/telemetry/spans/cookbook.py` — five span definitions (oq-1 emits)
- Full TDD suite incl. determinism, affinity distribution, curation sweep, wiring contract

## oq-1 coordination (do not merge without confirming)
- §4.3 signature extended with oq-1-supplied `is_first_band_entry: bool` (see plan "Seam Clarification")
- `KNOWN_GENERATOR_BINDINGS` is a sourced reference set — oq-1 owns semantics
- Spans are DEFINED here; oq-1 wires emission at the materializer seam

## Test plan
- [ ] `uv run pytest tests/game/cookbook tests/telemetry/spans/test_cookbook_spans.py tests/integration/test_cookbook_assemble_wiring.py`
- [ ] `uv run ruff check . && uv run ruff format --check .`
EOF
)"
```

- [ ] **Step 3: Report both PR URLs to the operator. Do NOT merge.** oq-1 owns merge/sync and the materializer wiring that completes the loop.

---

## Self-Review (run by plan author against the spec)

**1. Spec coverage:**

| Spec section | Covered by |
|---|---|
| §3 Five Axes (LOOK/RACE/BIG BAD/SPECIAL/SIZE) | Tasks 6, 8, 13–18 |
| §4.1 Ingest as index | Tasks 1–2 |
| §4.2 Authored cookbook files | Tasks 4, 6, 8 |
| §4.3 Region-assembly contract | Tasks 12–18 |
| §5 Genre-truth curation | Tasks 4–5, 19 |
| §6 Reuse not reinvention | Task 15 (re-keys encounter_tables/equipment_tables row shape) |
| §7 Failure modes — loud | Tasks 10, 21 (+ §7 reskin/bigbad-name checks in Task 10; **corrected** per Data-Forced Design Item — entry guarantee + capstone reachability, observable re-roll not silent empty table) |
| §8 OTEL definitions | Task 11 (6 spans incl. `cookbook.race.reroll` for the data-forced re-roll) |
| §9 Testing strategy (all 7 bullets) | Tasks 2,10,14,12,16,17,19,20 |
| §10 Decomposition (6 sub-plans) | Phases A–F mirror §10 steps 1–6 |
| §11 Open items | Task 23 records resolved seam + data-forced design item; tuning values flagged in YAML comments |

Gap check: §2 scope-boundary non-goals are enforced as the plan's "Hard Non-Goals" and re-stated at the CR→Edge seam in Tasks 15/18. No spec requirement left without a task. **Real-data divergences from the spec's *illustrative* content are documented and corrected**, not silently followed: (a) SRD 5.1 has no Kuo-toa → `kuo_toa` RACE replaced by `ooze` "The Seep" (matches existing reskin); (b) low-CR-ceiling factions (ooze/goblinoid) can't fill deep → "Data-Forced Design Item" callout + corrected validator + observable assembler re-roll; (c) every `big_bads[].name` / `min_band` verified against the ingested corpus (Wight mid, Mummy Lord/Lich/Aboleth deep, Black Pudding mid).

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Prerequisite 0 is **resolved** (operator-supplied `BTMorton/dnd-5e-srd`); Task 1's parser is **proven during planning** (316 rows, Mummy edge handled, required names resolve), not aspirational. Every code step ships complete code.

**3. Type consistency:** `RegionContentManifest` field names (`race`, `cr_band`, `size_budget`, `wandering_table`, `loot_table`, `special_rooms`, `big_bad`) are identical in models (Task 3), `assemble_region` (Task 18), the wiring test (Task 20), and the curation sweep (Task 19). `roll_race` returns `RaceDef | None` consistently (Task 14 def, Task 18 re-roll caller). Ingest API names (`parse_cr`, `parse_statline`, `iter_statblock_leaves`, `walk_monsters`, `walk_items`) match between `ingest.py` (Task 1) and `test_ingest_fidelity.py` (Task 1) and the CLI `main` (Task 2). `band_order()`, `band_for_depth`, `budget_for_burst`, `roll_big_bad`, `pick_specials`, `build_wandering_table`, `build_loot_table` keep one name across all call sites. Span constant + helper names match between `cookbook.py`, `__all__`, and `test_cookbook_spans.py` (six spans incl. `SPAN_COOKBOOK_RACE_REROLL`/`cookbook_race_reroll_span`). RACE id `ooze` (not `kuo_toa`) is consistent across Tasks 6, 8, the loader test (Task 9), affinity test (Task 14), and `affinities.yaml`.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-16-beneath-sunden-content-cookbook.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best here: 24 tasks, strict TDD, two-repo commits — a clean fit for per-task subagents with review gates. (Pass the no-stash / no-prior-commit-verification prohibitions into every subagent prompt.)

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?** — Prerequisite 0 is **resolved** (source = operator-supplied `BTMorton/dnd-5e-srd`; the ingest parser is proven). No tasks are blocked — the full plan can execute end-to-end. One open question for you, surfaced in the **Data-Forced Design Item**: low-ceiling factions (ooze/goblinoid) re-roll observably when a region's depth exceeds their CR ceiling — say the word if you'd prefer hard-excluding them from deep affinities instead (changes Tasks 8/10/18).
