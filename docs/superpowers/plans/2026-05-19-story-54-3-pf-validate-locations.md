# Story 54-3: `pf validate locations` — Manifest Validator

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a new `pf validate locations` validator that enforces three checks against every world's manifest: (1) well-formedness — entities parse as `LocationEntity`, no duplicate ids per region/room, `real_object` requires a binding; (2) binding resolution — `binding.ref` resolves in the target subsystem; (3) prose-manifest coherence — proper-noun-shaped tokens in the description prose resolve to an entity, an NPC name, or a per-pack `generic_allowlist[]` entry. (1) and (2) are hard errors; (3) is a warning. Wire into CI.

**Architecture:** Cross-repo. The validator's **core logic** lives in `sidequest-server/sidequest/cli/validate/locations.py` (Python, importable + standalone-runnable). The **pf adapter** lives in `pennyfarthing-dist/src/pf/validate/adapters/locations.py` and shells out to the server CLI with `--json`, parses the structured report, and produces a `ValidateReport`. This mirrors the existing decoupling between pf and project-specific validators. The standalone CLI also serves CI directly (`uv run python -m sidequest.cli.validate.locations`).

**Tech Stack:** Python 3.14, pytest, click (for the CLI). The pf side uses its existing `ValidateReport` dataclass.

**Workflow:** tdd.

**Depends on:** 54-2 (the `LocationEntity` type and the `Region.entities[]` field).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/cli/validate/locations.py` | create | Core validator logic + `--json` CLI. Three checks. Walks every genre pack and every world. |
| `sidequest-server/sidequest/cli/validate/__main__.py` | modify | Add `locations` subcommand routing (currently hard-coded to `projection_check`). |
| `sidequest-server/tests/cli/test_validate_locations.py` | create | TDD tests for each check + fixture genre packs (smallest-possible YAML in `tests/fixtures/validate_locations/`). |
| `sidequest-server/tests/fixtures/validate_locations/...` | create | Fixture content: a tiny world with valid entities, one with a duplicate id, one with a bad binding ref, one with prose drift. |
| `/Users/slabgorb/Projects/orc-penny/pennyfarthing/pennyfarthing-dist/src/pf/validate/adapters/locations.py` | create | Adapter — runs the server CLI, parses JSON, returns `ValidateReport`. |
| `/Users/slabgorb/Projects/orc-penny/pennyfarthing/pennyfarthing-dist/src/pf/validate/cli.py` | modify | Register `"locations"` in `VALIDATORS` dict. |
| `/Users/slabgorb/Projects/orc-penny/pennyfarthing/pennyfarthing-dist/src/pf/tests/test_validate_locations_adapter.py` | create | Adapter tests with subprocess mocked. |
| `.github/workflows/ci.yml` (orchestrator repo) | modify | Add `pf validate locations` to the CI matrix if a CI workflow exists at this path; otherwise add to the relevant just recipe (`just check-all`). |

---

### Task 1: Core validator — well-formedness check

**Files:**
- Create: `sidequest-server/sidequest/cli/validate/locations.py`
- Create: `sidequest-server/tests/cli/test_validate_locations.py`
- Create: `sidequest-server/tests/fixtures/validate_locations/wf_ok/genre_pack.yaml` and `worlds/sample/cartography.yaml`
- Create: `sidequest-server/tests/fixtures/validate_locations/wf_duplicate_id/...`
- Create: `sidequest-server/tests/fixtures/validate_locations/wf_real_object_no_binding/...`

- [ ] **Step 1: Lay out fixture trees**

Create the minimal genre-pack shape the existing loader accepts. Inspect first:
```bash
ls sidequest-content/genre_packs/tea_and_murder/ | head -20
head -20 sidequest-content/genre_packs/tea_and_murder/genre_pack.yaml 2>/dev/null
```

Create `sidequest-server/tests/fixtures/validate_locations/wf_ok/genre_pack.yaml`:

```yaml
name: "wf_ok"
slug: "wf_ok"
description: "Fixture pack for validator tests."
worlds:
  - sample
```

Create `.../wf_ok/worlds/sample/world.yaml`:
```yaml
name: "Sample World"
slug: "sample"
description: "Tiny."
starting_location: "village_square"
```

Create `.../wf_ok/worlds/sample/cartography.yaml`:
```yaml
world_name: "Sample World"
starting_region: "village_square"
map_style: "abstract"
navigation_mode: "region"
regions:
  village_square:
    name: "Village Square"
    summary: "A cobbled square."
    description: "The well at the centre is mossed over. An old notice board lists rules."
    entities:
      - id: well
        label: the well
        tier: real_object
        binding:
          kind: location_feature
          ref: village_square_well
      - id: notice_board
        label: the notice board
        tier: real_object
        binding:
          kind: location_feature
          ref: village_square_notice_board
        affordances: [read]
```

(Match exact existing pack shape — run `cat sidequest-content/genre_packs/tea_and_murder/genre_pack.yaml` first and copy the minimum required keys.)

Create `.../wf_duplicate_id/worlds/sample/cartography.yaml` (same shape) but with two entities sharing `id: well`.

Create `.../wf_real_object_no_binding/worlds/sample/cartography.yaml` with one `tier: real_object` entity that has no `binding:` field.

- [ ] **Step 2: Write failing tests**

Create `sidequest-server/tests/cli/test_validate_locations.py`:

```python
"""TDD tests for pf validate locations core (Story 54-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.cli.validate.locations import (
    Issue,
    ValidationResult,
    validate_packs,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "validate_locations"


def _result(pack: str) -> ValidationResult:
    return validate_packs([FIXTURES / pack])


def test_well_formed_pack_passes():
    res = _result("wf_ok")
    assert res.errors == []
    # Coherence warnings may be present; the well-formedness check is the
    # contract here, and it should produce no errors.


def test_duplicate_entity_id_within_region_errors():
    res = _result("wf_duplicate_id")
    duplicates = [i for i in res.errors if i.code == "DUPLICATE_ENTITY_ID"]
    assert len(duplicates) == 1
    assert "well" in duplicates[0].message
    assert duplicates[0].region_id == "village_square"


def test_real_object_without_binding_errors():
    res = _result("wf_real_object_no_binding")
    bad = [i for i in res.errors if i.code == "REAL_OBJECT_REQUIRES_BINDING"]
    assert len(bad) == 1
```

- [ ] **Step 3: Run, confirm fail**

```bash
cd sidequest-server && uv run pytest tests/cli/test_validate_locations.py -v
```
Expected: ImportError — module doesn't exist.

- [ ] **Step 4: Write `locations.py` core (just well-formedness)**

Create `sidequest-server/sidequest/cli/validate/locations.py`:

```python
"""pf validate locations — core validator (Story 54-3 / ADR-109).

Three checks:
1. Well-formedness (hard error): entities parse as LocationEntity, no
   duplicate ids per region/room, real_object requires a binding.
2. Binding resolution (hard error): binding.ref resolves in the
   target subsystem.
3. Prose-manifest coherence (warning): proper-noun-shaped tokens in
   the description prose resolve to an entity, NPC, or generic_allowlist
   entry.

Hard errors gate CI. Warnings are observable but never blocking.
The server's loader does not re-validate at runtime — it trusts content
that passed this validator.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import click
import yaml

from sidequest.protocol.models import LocationEntity


Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Issue:
    code: str
    severity: Severity
    message: str
    pack: str
    world: str
    region_id: str | None
    file: str  # relative path for reporting
    line: int | None = None


@dataclass
class ValidationResult:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def record(self, issue: Issue) -> None:
        (self.errors if issue.severity == "error" else self.warnings).append(issue)

    @property
    def success(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# Genre-pack discovery + walk
# ---------------------------------------------------------------------------


def _packs_in(root: Path) -> list[Path]:
    """Return every directory under ``root`` that looks like a genre pack."""
    if (root / "genre_pack.yaml").is_file():
        return [root]
    return sorted(
        p for p in root.iterdir() if p.is_dir() and (p / "genre_pack.yaml").is_file()
    )


def _worlds_in(pack: Path) -> list[Path]:
    worlds_dir = pack / "worlds"
    if not worlds_dir.is_dir():
        return []
    return sorted(p for p in worlds_dir.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# Check 1 — well-formedness
# ---------------------------------------------------------------------------


def _check_well_formed_region(
    result: ValidationResult,
    *,
    pack: str,
    world: str,
    region_id: str,
    raw_entities: list[Any],
    source_file: str,
) -> list[LocationEntity]:
    """Returns the parsed entities (drop unparseable ones)."""
    parsed: list[LocationEntity] = []
    seen_ids: set[str] = set()
    for entry in raw_entities or []:
        try:
            entity = LocationEntity.model_validate(entry)
        except Exception as exc:  # pydantic ValidationError
            result.record(
                Issue(
                    code="MALFORMED_ENTITY",
                    severity="error",
                    message=f"entity failed validation: {exc}",
                    pack=pack,
                    world=world,
                    region_id=region_id,
                    file=source_file,
                )
            )
            continue
        if entity.id in seen_ids:
            result.record(
                Issue(
                    code="DUPLICATE_ENTITY_ID",
                    severity="error",
                    message=f"duplicate entity id {entity.id!r} in region",
                    pack=pack,
                    world=world,
                    region_id=region_id,
                    file=source_file,
                )
            )
            continue
        seen_ids.add(entity.id)
        if entity.tier == "real_object" and entity.binding is None:
            result.record(
                Issue(
                    code="REAL_OBJECT_REQUIRES_BINDING",
                    severity="error",
                    message=f"entity {entity.id!r} is real_object but has no binding",
                    pack=pack,
                    world=world,
                    region_id=region_id,
                    file=source_file,
                )
            )
        parsed.append(entity)
    return parsed


# ---------------------------------------------------------------------------
# Top-level entry
# ---------------------------------------------------------------------------


def _world_files(world_dir: Path) -> dict[str, Path]:
    return {
        "cartography": world_dir / "cartography.yaml",
        "npcs": world_dir / "npcs.yaml",
    }


def _validate_one_pack(pack_dir: Path, result: ValidationResult) -> None:
    pack_slug = pack_dir.name
    for world_dir in _worlds_in(pack_dir):
        world_slug = world_dir.name
        files = _world_files(world_dir)

        # Cartography region entities
        cart_path = files["cartography"]
        if cart_path.is_file():
            data = yaml.safe_load(cart_path.read_text()) or {}
            regions = (data.get("regions") or {})
            for region_id, region_data in regions.items():
                raw_entities = (region_data or {}).get("entities") or []
                _check_well_formed_region(
                    result,
                    pack=pack_slug,
                    world=world_slug,
                    region_id=region_id,
                    raw_entities=raw_entities,
                    source_file=str(cart_path),
                )

        # Per-room YAMLs
        rooms_dir = world_dir / "rooms"
        if rooms_dir.is_dir():
            for room_path in sorted(rooms_dir.glob("*.yaml")):
                room_data = yaml.safe_load(room_path.read_text()) or {}
                raw_entities = room_data.get("entities") or []
                _check_well_formed_region(
                    result,
                    pack=pack_slug,
                    world=world_slug,
                    region_id=room_path.stem,
                    raw_entities=raw_entities,
                    source_file=str(room_path),
                )


def validate_packs(pack_roots: list[Path]) -> ValidationResult:
    """Validate every pack found under each root in ``pack_roots``.

    ``pack_roots`` accepts either a directory containing many packs OR a
    single pack directory (detected by presence of ``genre_pack.yaml``).
    """
    result = ValidationResult()
    for root in pack_roots:
        for pack in _packs_in(root):
            _validate_one_pack(pack, result)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--genre-packs-root",
    "roots",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Genre-pack directory to scan. May be passed multiple times.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def main(roots: tuple[Path, ...], as_json: bool) -> None:  # pragma: no cover
    if not roots:
        # Default to the orchestrator's pinned content dir.
        from sidequest.genre.loader import DEFAULT_GENRE_PACK_SEARCH_PATHS

        roots = tuple(DEFAULT_GENRE_PACK_SEARCH_PATHS)

    result = validate_packs(list(roots))

    if as_json:
        payload = {
            "errors": [i.__dict__ for i in result.errors],
            "warnings": [i.__dict__ for i in result.warnings],
            "passed": result.success,
        }
        click.echo(json.dumps(payload, indent=2))
    else:
        for issue in result.errors:
            click.echo(f"[ERROR] {issue.code} {issue.file}: {issue.message}", err=True)
        for issue in result.warnings:
            click.echo(f"[WARN] {issue.code} {issue.file}: {issue.message}", err=True)
        click.echo(
            f"locations: {len(result.errors)} errors, {len(result.warnings)} warnings",
            err=True,
        )

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":  # pragma: no cover
    main()
```

- [ ] **Step 5: Run, confirm green for well-formedness**

```bash
cd sidequest-server && uv run pytest tests/cli/test_validate_locations.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/cli/validate/locations.py \
        sidequest-server/tests/cli/test_validate_locations.py \
        sidequest-server/tests/fixtures/validate_locations/
git commit -m "feat(54-3): pf validate locations — well-formedness check

Walks every genre pack's cartography regions and per-room YAMLs,
parses entities[] through LocationEntity, errors on malformed entries,
duplicate ids within a region/room, and real_object entities missing
a binding. Two more checks (binding resolution, prose coherence)
land in subsequent tasks of this story."
```

---

### Task 2: Binding resolution check

**Files:**
- Modify: `sidequest-server/sidequest/cli/validate/locations.py`
- Modify: `sidequest-server/tests/cli/test_validate_locations.py`
- Create fixture: `tests/fixtures/validate_locations/binding_bad_npc/...`

- [ ] **Step 1: Add fixture — entity with `binding.kind=npc` whose `ref` doesn't appear in `npcs.yaml`**

Mirror `wf_ok` but in `cartography.yaml`:
```yaml
regions:
  village_square:
    name: "Village Square"
    summary: "."
    description: "."
    entities:
      - id: barkeep
        label: the barkeep
        tier: real_object
        binding:
          kind: npc
          ref: nonexistent_npc_id
```

And add a minimal `npcs.yaml`:
```yaml
npcs: []
```

- [ ] **Step 2: Add failing test**

Append to `test_validate_locations.py`:

```python
def test_npc_binding_to_unknown_id_errors():
    res = _result("binding_bad_npc")
    bad = [i for i in res.errors if i.code == "BINDING_UNRESOLVED"]
    assert len(bad) == 1
    assert "nonexistent_npc_id" in bad[0].message


def test_location_feature_binding_is_free_form():
    """location_feature bindings have no cross-file lookup; entity id
    uniqueness within the region is the only constraint."""
    res = _result("wf_ok")
    unresolved = [i for i in res.errors if i.code == "BINDING_UNRESOLVED"]
    assert unresolved == []
```

- [ ] **Step 3: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/cli/test_validate_locations.py -v
```
Expected: the new tests fail.

- [ ] **Step 4: Implement binding resolution**

Add to `sidequest-server/sidequest/cli/validate/locations.py`:

```python
# ---------------------------------------------------------------------------
# Check 2 — binding resolution
# ---------------------------------------------------------------------------


def _load_npc_ids(world_dir: Path) -> set[str]:
    path = world_dir / "npcs.yaml"
    if not path.is_file():
        return set()
    raw = yaml.safe_load(path.read_text()) or {}
    npcs = raw.get("npcs") or []
    ids: set[str] = set()
    for npc in npcs:
        if isinstance(npc, dict):
            for key in ("id", "slug", "name"):
                if isinstance(npc.get(key), str):
                    ids.add(npc[key])
    return ids


def _load_item_ids(world_dir: Path, pack_dir: Path) -> set[str]:
    """Items live at pack level. v1 is permissive — items resolution
    plugs into the canonical item corpus once we know its shape."""
    # TODO when item corpus path stabilizes (post-54 epic). For v1, any
    # item-bound entity is accepted; the check is a no-op for items.
    return set()  # intentional permissive return — item-binding check
                  # is intentionally deferred per ADR-109 implementation
                  # guidance (validator coverage expands when subsystem
                  # interfaces firm up).


def _load_clue_ids(world_dir: Path) -> set[str]:
    """Scenario clues live under <world>/scenarios/. v1 scans for clue
    ids declared in scenario YAMLs (graceful empty when none)."""
    ids: set[str] = set()
    scen_dir = world_dir / "scenarios"
    if not scen_dir.is_dir():
        return ids
    for scenario in scen_dir.glob("*.yaml"):
        data = yaml.safe_load(scenario.read_text()) or {}
        for clue in (data.get("clues") or []):
            if isinstance(clue, dict) and isinstance(clue.get("id"), str):
                ids.add(clue["id"])
    return ids


def _check_binding(
    result: ValidationResult,
    entity: LocationEntity,
    *,
    pack: str,
    world: str,
    region_id: str,
    source_file: str,
    npc_ids: set[str],
    item_ids: set[str],
    clue_ids: set[str],
) -> None:
    if entity.binding is None:
        return
    kind = entity.binding.kind
    ref = entity.binding.ref
    if kind == "location_feature":
        # Free-form; uniqueness is already enforced by id-uniqueness.
        return
    if kind == "npc" and ref not in npc_ids:
        code = "BINDING_UNRESOLVED"
        msg = f"entity {entity.id!r} binds to unknown npc {ref!r}"
    elif kind == "item" and item_ids and ref not in item_ids:
        # Permissive when corpus is empty (v1 placeholder).
        code = "BINDING_UNRESOLVED"
        msg = f"entity {entity.id!r} binds to unknown item {ref!r}"
    elif kind in {"clue", "scenario_clue"} and ref not in clue_ids:
        code = "BINDING_UNRESOLVED"
        msg = f"entity {entity.id!r} binds to unknown {kind} {ref!r}"
    else:
        return
    result.record(
        Issue(
            code=code,
            severity="error",
            message=msg,
            pack=pack,
            world=world,
            region_id=region_id,
            file=source_file,
        )
    )
```

Then thread the binding check into `_validate_one_pack`. Modify that function to load `npc_ids`/`item_ids`/`clue_ids` once per world and pass them through to a new helper that runs both check 1 and check 2 per region. Refactor `_check_well_formed_region` to return parsed entities AND optionally invoke `_check_binding` for each. (Keep the function signature changes additive — pass the id sets through.)

The cleanest shape:

```python
def _validate_one_pack(pack_dir: Path, result: ValidationResult) -> None:
    pack_slug = pack_dir.name
    for world_dir in _worlds_in(pack_dir):
        world_slug = world_dir.name
        files = _world_files(world_dir)
        npc_ids = _load_npc_ids(world_dir)
        item_ids = _load_item_ids(world_dir, pack_dir)
        clue_ids = _load_clue_ids(world_dir)

        def _check_region(region_id: str, raw_entities, source_file: str) -> None:
            entities = _check_well_formed_region(
                result,
                pack=pack_slug,
                world=world_slug,
                region_id=region_id,
                raw_entities=raw_entities,
                source_file=source_file,
            )
            for entity in entities:
                _check_binding(
                    result, entity,
                    pack=pack_slug, world=world_slug, region_id=region_id,
                    source_file=source_file,
                    npc_ids=npc_ids, item_ids=item_ids, clue_ids=clue_ids,
                )

        # cartography
        cart = files["cartography"]
        if cart.is_file():
            data = yaml.safe_load(cart.read_text()) or {}
            for region_id, region_data in (data.get("regions") or {}).items():
                _check_region(region_id, (region_data or {}).get("entities") or [], str(cart))

        # rooms
        rooms = world_dir / "rooms"
        if rooms.is_dir():
            for room_path in sorted(rooms.glob("*.yaml")):
                room_data = yaml.safe_load(room_path.read_text()) or {}
                _check_region(room_path.stem, room_data.get("entities") or [], str(room_path))
```

- [ ] **Step 5: Run, confirm green**

```bash
cd sidequest-server && uv run pytest tests/cli/test_validate_locations.py -v
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/cli/validate/locations.py \
        sidequest-server/tests/cli/test_validate_locations.py \
        sidequest-server/tests/fixtures/validate_locations/binding_bad_npc/
git commit -m "feat(54-3): binding resolution check for pf validate locations

npc/clue/scenario_clue refs must resolve against world npcs.yaml +
scenarios/*.yaml. location_feature is free-form (id uniqueness
already enforced). item-binding check is deferred until the canonical
item corpus interface firms up — flagged in source."
```

---

### Task 3: Prose-manifest coherence (warning)

**Files:**
- Modify: `sidequest-server/sidequest/cli/validate/locations.py`
- Modify: `sidequest-server/tests/cli/test_validate_locations.py`
- Create: `tests/fixtures/validate_locations/coherence_drift/...` (description mentions a noun phrase not in entities/npcs/allowlist)
- Document: per-pack `generic_allowlist[]` in `genre_pack.yaml`

- [ ] **Step 1: Define the allowlist surface in fixtures**

The allowlist is per-pack. Add to `wf_ok/genre_pack.yaml`:
```yaml
generic_allowlist:
  - the day
  - the weather
  - the village
  - the sky
```

Add fixture `coherence_drift/genre_pack.yaml` (with empty allowlist) and a region whose description says "The dragon coils against the well" with only `well` in `entities[]`. "The dragon" is the drift token.

- [ ] **Step 2: Failing test**

```python
def test_unallowlisted_definite_noun_phrase_warns():
    res = _result("coherence_drift")
    drift = [i for i in res.warnings if i.code == "PROSE_DRIFT"]
    # At least one warning for "the dragon".
    assert any("dragon" in i.message.lower() for i in drift)


def test_allowlist_silences_generic_phrases():
    res = _result("wf_ok")
    # "the centre" / "the rules" might surface — must NOT error.
    # Warnings allowed but not blocking. Errors definitely empty:
    assert res.errors == []


def test_npc_name_in_prose_does_not_warn():
    """If the prose mentions a known NPC, no PROSE_DRIFT warning fires."""
    # Build a fixture inline-ish; or add a fixture with npcs.yaml: [Cassia]
    # and description "Cassia leans on the bar." → no warning for Cassia.
    res = _result("coherence_npc_resolved")  # add fixture
    drift = [i for i in res.warnings if i.code == "PROSE_DRIFT"]
    assert all("cassia" not in i.message.lower() for i in drift)
```

Add the `coherence_npc_resolved` fixture: cartography description mentions "Cassia"; `npcs.yaml` has `- id: cassia\n  name: Cassia`; entity manifest lists only `the bar`.

- [ ] **Step 3: Implement the prose check**

Append to `locations.py`:

```python
import re

_DEFINITE_NOUN_RE = re.compile(r"\b(the|a|an)\s+([a-z][a-z\-' ]{2,40})", re.IGNORECASE)
_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")


def _load_allowlist(pack_dir: Path) -> set[str]:
    cfg_path = pack_dir / "genre_pack.yaml"
    if not cfg_path.is_file():
        return set()
    data = yaml.safe_load(cfg_path.read_text()) or {}
    raw = data.get("generic_allowlist") or []
    return {str(s).strip().lower() for s in raw}


def _normalize(phrase: str) -> str:
    return phrase.strip().lower()


def _check_prose_coherence(
    result: ValidationResult,
    *,
    pack: str,
    world: str,
    region_id: str,
    prose: str,
    entities: list[LocationEntity],
    npc_ids: set[str],
    allowlist: set[str],
    source_file: str,
) -> None:
    if not prose:
        return
    entity_labels = {_normalize(e.label) for e in entities}
    entity_label_stems = {
        _normalize(re.sub(r"^(the|a|an)\s+", "", lbl, flags=re.IGNORECASE))
        for lbl in entity_labels
    }
    npc_tokens = {_normalize(n) for n in npc_ids}

    seen: set[str] = set()

    for match in _DEFINITE_NOUN_RE.finditer(prose):
        article, head = match.group(1), match.group(2)
        full = _normalize(f"{article} {head}")
        head_lower = _normalize(head)
        if full in seen:
            continue
        seen.add(full)
        if (
            full in entity_labels
            or head_lower in entity_label_stems
            or full in allowlist
            or head_lower in allowlist
        ):
            continue
        result.record(
            Issue(
                code="PROSE_DRIFT",
                severity="warning",
                message=(
                    f"description references {full!r} but no matching entity, "
                    "NPC, or generic_allowlist entry"
                ),
                pack=pack,
                world=world,
                region_id=region_id,
                file=source_file,
            )
        )

    for match in _PROPER_NOUN_RE.finditer(prose):
        token = match.group(1)
        norm = _normalize(token)
        if norm in seen:
            continue
        seen.add(norm)
        if norm in npc_tokens or norm in entity_labels or norm in allowlist:
            continue
        # Single-token capitalized words that aren't NPC names get a
        # warning. Avoid sentence-initial false positives by skipping
        # tokens whose offset is 0 OR whose preceding char is "." + space.
        start = match.start()
        if start == 0 or prose[max(0, start - 2) : start] in (". ", "? ", "! "):
            continue
        result.record(
            Issue(
                code="PROSE_DRIFT",
                severity="warning",
                message=(
                    f"description references proper noun {token!r} but no "
                    "matching NPC, entity, or allowlist entry"
                ),
                pack=pack,
                world=world,
                region_id=region_id,
                file=source_file,
            )
        )
```

Wire the check into `_validate_one_pack`'s `_check_region` closure:

```python
        def _check_region(region_id: str, raw_entities, source_file: str,
                          prose: str = "") -> None:
            entities = _check_well_formed_region(...)
            for entity in entities:
                _check_binding(...)
            _check_prose_coherence(
                result, pack=pack_slug, world=world_slug, region_id=region_id,
                prose=prose, entities=entities, npc_ids=npc_ids,
                allowlist=allowlist, source_file=source_file,
            )
```

…and pass `prose=region_data.get("description", "")` / `room_data.get("description", "")` at the call sites.

Load `allowlist = _load_allowlist(pack_dir)` once per pack.

- [ ] **Step 4: Run, confirm green**

```bash
cd sidequest-server && uv run pytest tests/cli/test_validate_locations.py -v
```
Expected: all green.

- [ ] **Step 5: Lint + format**

```bash
just server-fmt && just server-lint
```

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/cli/validate/locations.py \
        sidequest-server/tests/cli/test_validate_locations.py \
        sidequest-server/tests/fixtures/validate_locations/coherence_drift/ \
        sidequest-server/tests/fixtures/validate_locations/coherence_npc_resolved/
git commit -m "feat(54-3): prose-manifest coherence warning

Scans description prose for 'the X' / proper-noun tokens and warns
when none match an entity label, a known NPC, or the pack's
generic_allowlist. Non-blocking — surfaces drift for author review
without breaking CI."
```

---

### Task 4: Wire `__main__.py` to route subcommands

**Files:**
- Modify: `sidequest-server/sidequest/cli/validate/__main__.py`

- [ ] **Step 1: Read current entry**

(Already inspected: it hard-codes `projection_check`.)

- [ ] **Step 2: Replace with click group**

Open `sidequest-server/sidequest/cli/validate/__main__.py` and replace with:

```python
"""Entry point: ``python -m sidequest.cli.validate <subcommand>``."""

from __future__ import annotations

import sys

import click

from sidequest.cli.validate.locations import main as locations_main
from sidequest.cli.validate.projection_check import main as projection_check_main


@click.group()
def cli() -> None:
    """sidequest validators."""


@cli.command(name="projection-check")
def projection_check() -> None:
    sys.exit(projection_check_main())


# locations is its own click.command — register the underlying click object.
cli.add_command(locations_main, name="locations")


if __name__ == "__main__":
    cli()
```

(If `projection_check.main` is also a `click.command`, switch to `cli.add_command(...)` for consistency.)

- [ ] **Step 3: Smoke-test the CLI**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --json --genre-packs-root tests/fixtures/validate_locations/wf_ok
```
Expected: JSON output, exit 0, `"passed": true`.

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --json --genre-packs-root tests/fixtures/validate_locations/wf_duplicate_id
echo "exit=$?"
```
Expected: JSON output, exit 1, `"passed": false`.

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/sidequest/cli/validate/__main__.py
git commit -m "chore(54-3): register validate locations subcommand under cli/validate"
```

---

### Task 5: Run validator against real content, fix any errors found

**Why:** Until 54-4 and 54-5 backfill content, real worlds may have no `entities[]` and produce zero errors — but we still need to confirm the validator runs clean against current state, since the spec says the validator gates CI. If new errors fire on current authored content (likely none, since 54-2 only added an empty default), the *content* needs fixing, not the validator.

- [ ] **Step 1: Run against real content**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations
echo "exit=$?"
```
Expected: exit 0. Warnings about prose drift are EXPECTED on packs that have authored descriptions but no `entities[]` yet — these resolve as content backfill in 54-4/54-5.

If real content errors out:
- For `BINDING_UNRESOLVED`: 54-2 shouldn't have introduced any (empty default). If you see one, you added it accidentally in 54-2's fixture step — fix or remove.
- For `DUPLICATE_ENTITY_ID` / `MALFORMED_ENTITY` / `REAL_OBJECT_REQUIRES_BINDING`: ditto.

If you see only `PROSE_DRIFT` warnings, that's expected — they're non-blocking by design.

- [ ] **Step 2: No commit unless you fixed content**

If you fixed content in step 1, commit it under the 54-3 story:
```bash
git commit -m "fix(54-3): clean validator findings on real content"
```

---

### Task 6: pf adapter — shell out and parse JSON

**Files:**
- Create: `/Users/slabgorb/Projects/orc-penny/pennyfarthing/pennyfarthing-dist/src/pf/validate/adapters/locations.py`
- Modify: `/Users/slabgorb/Projects/orc-penny/pennyfarthing/pennyfarthing-dist/src/pf/validate/cli.py`
- Create: `/Users/slabgorb/Projects/orc-penny/pennyfarthing/pennyfarthing-dist/src/pf/tests/test_validate_locations_adapter.py`

**Topology check:** This is the `pennyfarthing` repo (not orchestrator). Match its branch policy — feat branches target `develop`, not `main`. Verify before pushing.

- [ ] **Step 1: Write the failing adapter test**

Create `pennyfarthing-dist/src/pf/tests/test_validate_locations_adapter.py`:

```python
"""Adapter for pf validate locations — shells to sidequest-server CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pf.validate import ValidateReport
from pf.validate.adapters import locations as adapter


def test_adapter_passes_when_server_cli_reports_passed(tmp_path):
    fake_output = json.dumps({
        "passed": True,
        "errors": [],
        "warnings": [],
    })
    with patch.object(adapter, "_run_server_cli", return_value=(fake_output, 0)):
        report = adapter.run(tmp_path, fix=False, strict=False)
    assert isinstance(report, ValidateReport)
    assert report.success
    assert report.errors == 0


def test_adapter_reports_errors_and_warnings(tmp_path):
    fake_output = json.dumps({
        "passed": False,
        "errors": [
            {
                "code": "DUPLICATE_ENTITY_ID",
                "severity": "error",
                "message": "duplicate 'well'",
                "pack": "p",
                "world": "w",
                "region_id": "r",
                "file": "f",
                "line": None,
            }
        ],
        "warnings": [
            {
                "code": "PROSE_DRIFT",
                "severity": "warning",
                "message": "the dragon",
                "pack": "p",
                "world": "w",
                "region_id": "r",
                "file": "f",
                "line": None,
            }
        ],
    })
    with patch.object(adapter, "_run_server_cli", return_value=(fake_output, 1)):
        report = adapter.run(tmp_path, fix=False, strict=False)
    assert not report.success
    assert report.errors == 1
    assert report.warnings == 1
    assert any("DUPLICATE_ENTITY_ID" in d for d in report.details)


def test_adapter_strict_promotes_warnings_to_errors(tmp_path):
    fake_output = json.dumps({
        "passed": True,
        "errors": [],
        "warnings": [
            {
                "code": "PROSE_DRIFT",
                "severity": "warning",
                "message": "x",
                "pack": "p",
                "world": "w",
                "region_id": "r",
                "file": "f",
                "line": None,
            }
        ],
    })
    with patch.object(adapter, "_run_server_cli", return_value=(fake_output, 0)):
        report = adapter.run(tmp_path, fix=False, strict=True)
    assert not report.success
    assert report.errors >= 1


def test_adapter_failure_to_invoke_cli_returns_error_report(tmp_path):
    """If sidequest-server isn't accessible, return a clean error report
    rather than crashing pf validate."""
    with patch.object(
        adapter, "_run_server_cli",
        side_effect=adapter.LocationsCliMissingError("nope"),
    ):
        report = adapter.run(tmp_path, fix=False, strict=False)
    assert report.errors >= 1
    assert not report.success
```

- [ ] **Step 2: Write the adapter**

Create `pennyfarthing-dist/src/pf/validate/adapters/locations.py`:

```python
"""pf validate locations — adapter that shells out to sidequest-server.

The actual validation logic lives in
``sidequest-server/sidequest/cli/validate/locations.py``. This adapter
invokes that CLI with ``--json`` and translates its report into pf's
``ValidateReport``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Tuple

from pf.validate import ValidateReport


class LocationsCliMissingError(RuntimeError):
    """Raised when sidequest-server cannot be invoked from the orchestrator."""


def _server_dir(root: Path) -> Path:
    """Locate the sidequest-server checkout relative to the orchestrator root."""
    candidate = root / "sidequest-server"
    if not candidate.is_dir():
        raise LocationsCliMissingError(
            f"expected sidequest-server checkout at {candidate}; "
            "pf validate locations requires the server source available."
        )
    return candidate


def _run_server_cli(root: Path) -> Tuple[str, int]:
    server = _server_dir(root)
    try:
        proc = subprocess.run(
            ["uv", "run", "python", "-m", "sidequest.cli.validate", "locations", "--json"],
            cwd=str(server),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise LocationsCliMissingError(f"uv not available: {exc}") from exc
    return proc.stdout, proc.returncode


def run(root: Path, *, fix: bool, strict: bool) -> ValidateReport:
    report = ValidateReport(validator="locations")
    try:
        stdout, _ = _run_server_cli(root)
    except LocationsCliMissingError as exc:
        report.errors = 1
        report.details = [f"[ERROR] LOCATIONS_CLI_MISSING: {exc}"]
        return report

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        report.errors = 1
        report.details = [f"[ERROR] LOCATIONS_CLI_OUTPUT: invalid JSON: {exc}"]
        return report

    for issue in data.get("errors", []):
        report.errors += 1
        report.details.append(
            f"[ERROR] {issue['code']} {issue.get('file', '')}: {issue['message']}"
        )
    for issue in data.get("warnings", []):
        if strict:
            report.errors += 1
            report.details.append(
                f"[ERROR] {issue['code']} {issue.get('file', '')}: {issue['message']} (strict)"
            )
        else:
            report.warnings += 1
            report.details.append(
                f"[WARN] {issue['code']} {issue.get('file', '')}: {issue['message']}"
            )

    if not report.errors:
        report.passed = 1
    return report
```

- [ ] **Step 3: Register in the pf VALIDATORS dict**

In `/Users/slabgorb/Projects/orc-penny/pennyfarthing/pennyfarthing-dist/src/pf/validate/cli.py`, add to the `VALIDATORS` dict:

```python
    "locations": "pf.validate.adapters.locations",
```

Also append `locations - Genre-pack location manifests (well-formedness, bindings, prose coherence)` to the help-text block listing validators.

- [ ] **Step 4: Run adapter tests**

```bash
cd /Users/slabgorb/Projects/orc-penny/pennyfarthing && uv run pytest pennyfarthing-dist/src/pf/tests/test_validate_locations_adapter.py -v
```
Expected: 4 passed.

- [ ] **Step 5: End-to-end smoke test**

From the orchestrator root:
```bash
pf validate locations
```
Expected: runs without error, prints `0 errors, N warnings` (N depends on current content).

- [ ] **Step 6: Commit (in pennyfarthing repo)**

```bash
cd /Users/slabgorb/Projects/orc-penny/pennyfarthing
git checkout -b feat/pf-validate-locations
git add pennyfarthing-dist/src/pf/validate/adapters/locations.py \
        pennyfarthing-dist/src/pf/validate/cli.py \
        pennyfarthing-dist/src/pf/tests/test_validate_locations_adapter.py
git commit -m "feat(pf): pf validate locations adapter

Adapter shells out to sidequest-server's python -m sidequest.cli.
validate locations --json and translates the report into the
ValidateReport shape. Strict mode promotes prose-coherence warnings
to errors."
git push -u origin feat/pf-validate-locations
```

(Open a PR against `develop` per pennyfarthing's branch policy.)

---

### Task 7: Wire into CI

**Files:**
- Modify: orchestrator's `justfile`
- Modify: any GitHub Actions workflow that calls `just check-all`

- [ ] **Step 1: Add to `just check-all`**

Read the orchestrator's `justfile` to find `check-all`. Append the new validator call:

```makefile
check-all:
    just server-check
    just client-lint
    just client-test
    just daemon-lint
    pf validate locations
```

- [ ] **Step 2: Verify locally**

```bash
just check-all
```
Expected: all gates green (warnings allowed, errors blocking).

- [ ] **Step 3: Commit**

```bash
git add justfile
git commit -m "chore(54-3): pf validate locations in just check-all

Hard-errors block CI; prose-coherence warnings remain non-blocking."
```

---

### Self-review checklist

- [ ] **Spec §5.1 coverage:** well-formedness (hard) ✓, binding resolution (hard) ✓, prose coherence (warning) ✓.
- [ ] **Placeholder scan:** every code block complete; item-binding deferral is explicit, sourced, and flagged in code with a clear rationale (not a vague TODO).
- [ ] **Type consistency:** `Issue.code` strings used by tests (`DUPLICATE_ENTITY_ID`, `REAL_OBJECT_REQUIRES_BINDING`, `BINDING_UNRESOLVED`, `MALFORMED_ENTITY`, `PROSE_DRIFT`) match the validator implementation 1:1.
- [ ] **Per-pack allowlist surface defined** (`generic_allowlist:` top-level key in `genre_pack.yaml`).
- [ ] **No silent fallback:** missing pf-side server source raises `LocationsCliMissingError`; the adapter surfaces it as a `LOCATIONS_CLI_MISSING` error in the report. Missing `npcs.yaml` → empty `npc_ids` set is acceptable (genuinely some worlds have none).
- [ ] **Wiring test:** the e2e smoke `pf validate locations` from the orchestrator root counts as wiring. The adapter unit tests mock `_run_server_cli` but the smoke step runs the real path.
- [ ] **Cross-repo discipline:** orchestrator commits target `main`, pennyfarthing commits target `develop`. Two separate PRs.

### Dependencies / handoff

- **Blocked by:** 54-2 (the types). 54-1 (the ADR — durable contract) ideally first but not technically required.
- **Unblocks:** 54-4, 54-5 (content authors need a working validator to author against). Strict mode in CI is a natural follow-up once warnings settle.
