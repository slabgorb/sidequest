# AWN Plan 2 — Mutation Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `sidequest/mutation/` subsystem — MP economy, resume-safe acquisition, Strain-costed use, OTEL spans, chargen seeding, and the `use_mutation` narrator tool — so AWN mutation use is mechanically resolved, not improvised.

**Architecture:** A bespoke package `sidequest/mutation/` (sibling of `sidequest/magic/`, per spec P2-2), with `MutationState` as a pydantic field on `GameSnapshot` (mirroring `magic_state`), the catalog riding `GenrePack` as an optional field (mirroring `bestiary`), Strain costs routed through the existing `CwnRulesetModule.apply_system_strain`, and a `use_mutation` `@tool` as the production caller (mirroring `adjust_system_strain`). Randomness is deterministic SHA-256 (the `lull_escalation.py` house pattern) — no `random` module, resume-safe.

**Tech Stack:** Python 3.13 / pydantic v2 / pytest (uv-managed), OpenTelemetry spans via the house `Span`/`SPAN_ROUTES` registry.

**Spec:** `docs/superpowers/specs/2026-06-09-awn-plan2-mutations-design.md` (orchestrator repo). Read it first.

**Repo:** ALL work in `sidequest-server`. Branch `feat/awn-plan2-mutations` off `develop` (gitflow; PRs target `develop`). Create the worktree/branch via superpowers:using-git-worktrees at execution start.

**Run tests from the `sidequest-server` root:** `uv run pytest <path> -v`. Full suite is parallel by default (`-n auto`).

**Two deliberate refinements of the spec (log as deviations in the PR description):**
1. **No new Strain `kind`** (spec P2-5 said `kind="mutation"`): the `kind` taxonomy in `apply_system_strain` is mechanical (temporary/permanent/rest/first_aid); mutation strain *is* temporary strain. Provenance rides `source=f"mutation:{id}"`, which the `cwn.system_strain.delta` span already carries. Adding a kind would duplicate `temporary`'s arithmetic for zero information gain.
2. **Class grant lives in the catalog, not `ClassDef`** (spec §5.5 pointed at the ADR-097 ClassDef seam): `mutant_wasteland` has **no `classes.yaml`** — its class names are display strings (loader's classes list is empty for this pack, see `loader.py:626` "packs without classes.yaml"). The catalog's `mp_economy.mutant_classes: ["Mutant"]` declares the grant — content-driven, works for class-name-only packs, and homebrew authors (Jade) can extend it without engine edits.

**Out of scope (next plan):** the narrator context block (spec §5.4), the "Use Mutation" beat dispatch marker (spec §6.3), and Story C content (the real 60+40 catalog, `magic.yaml` retirements, pack-validator rules — `sidequest-content` repo). This plan ships working, testable engine software: the tool is callable, spans fire, state persists.

---

## File Map

| File | Responsibility |
|---|---|
| Create `sidequest/mutation/__init__.py` | Public surface re-exports |
| Create `sidequest/mutation/models.py` | Catalog defs + structural validators |
| Create `sidequest/mutation/rolls.py` | Deterministic resume-safe rolls |
| Create `sidequest/mutation/state.py` | `MutationState` / per-character state |
| Create `sidequest/mutation/catalog.py` | YAML → `MutationCatalog`, fail-loud |
| Create `sidequest/mutation/acquire_ops.py` | Negative/positive/stigma acquisition + MP arithmetic |
| Create `sidequest/mutation/use_ops.py` | In-play use: ownership/limits/strain/save |
| Create `sidequest/mutation/chargen.py` | Chargen seeding (grant check + rolled negatives) |
| Create `sidequest/telemetry/spans/awn.py` | `awn.mutation.*` spans + routes |
| Create `sidequest/server/mutation_init.py` | Per-session init (peer of `magic_init.py`) |
| Create `sidequest/agents/tools/use_mutation.py` | Narrator tool (production caller) |
| Modify `sidequest/telemetry/spans/__init__.py` | `from .awn import *` re-export |
| Modify `sidequest/genre/models/pack.py` | `mutations: MutationCatalog \| None` field |
| Modify `sidequest/genre/loader.py` | Load genre-tier `mutations.yaml` |
| Modify `sidequest/game/session.py` | `GameSnapshot.mutation_state` field |
| Modify `sidequest/server/websocket_handlers/chargen_mixin.py` | Init call at chargen confirmation (2 sites) |
| Modify `sidequest/agents/tools/__init__.py` | Barrel import registers the tool |
| Create `tests/mutation/…` (5 files) | Unit tests, synthetic fixtures only |
| Create `tests/agents/test_use_mutation_tool.py` | Tool tests |
| Create `tests/integration/test_mutation_wiring.py` | End-to-end wiring test |

---

### Task 1: Catalog models with structural validators

**Files:**
- Create: `sidequest/mutation/__init__.py`
- Create: `sidequest/mutation/models.py`
- Test: `tests/mutation/__init__.py`, `tests/mutation/test_models.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mutation/__init__.py` (empty file), then `tests/mutation/test_models.py`:

```python
"""MutationCatalog structural validators — synthetic fixtures only.

Per spec P2-4: content invariants (10 positives per category, the real
d100 table) belong to the PACK validator in sidequest-content. These
tests cover engine-structural rules with minimal synthetic catalogs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.mutation.models import (
    MpEconomy,
    MutationCatalog,
    NegativeMutationDef,
    PositiveMutationDef,
    StigmaTables,
)


def _stigma() -> StigmaTables:
    return StigmaTables(
        body_part=[f"part_{i}" for i in range(6)],
        nature=[f"nature_{i}" for i in range(6)],
        flavor=[f"flavor_{i}" for i in range(12)],
    )


def _negative(id: str = "negative/withered_arm", lo: int = 1, hi: int = 100) -> NegativeMutationDef:
    return NegativeMutationDef(id=id, name="Withered Arm", roll_range=(lo, hi), effect="arm weak")


def _positive(
    id: str = "structure/crushing_jaws", category: str = "structure"
) -> PositiveMutationDef:
    return PositiveMutationDef(id=id, name="Crushing Jaws", category=category, effect="bite hard")


def _catalog(**overrides) -> MutationCatalog:
    kwargs = dict(
        mp_economy=MpEconomy(mutant_classes=["Mutant"]),
        stigma=_stigma(),
        negatives=[_negative()],
        positives=[_positive()],
    )
    kwargs.update(overrides)
    return MutationCatalog(**kwargs)


def test_minimal_catalog_validates() -> None:
    cat = _catalog()
    assert cat.positive_by_id("structure/crushing_jaws").name == "Crushing Jaws"
    assert cat.negative_for_roll(1).id == "negative/withered_arm"
    assert cat.negative_for_roll(100).id == "negative/withered_arm"


def test_d100_gap_rejected() -> None:
    with pytest.raises(ValidationError, match="partition"):
        _catalog(negatives=[_negative(lo=1, hi=40), _negative(id="negative/frail", lo=42, hi=100)])


def test_d100_overlap_rejected() -> None:
    with pytest.raises(ValidationError, match="partition"):
        _catalog(negatives=[_negative(lo=1, hi=50), _negative(id="negative/frail", lo=50, hi=100)])


def test_duplicate_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        _catalog(positives=[_positive(), _positive()])


def test_id_must_be_category_slash_slug() -> None:
    with pytest.raises(ValidationError, match="id"):
        _positive(id="CrushingJaws")


def test_positive_id_prefix_must_match_category() -> None:
    with pytest.raises(ValidationError, match="category"):
        _catalog(positives=[_positive(id="sense/crushing_jaws", category="structure")])


def test_negative_attr_penalty_floor() -> None:
    with pytest.raises(ValidationError, match="-2"):
        NegativeMutationDef(
            id="negative/ruined_spine",
            name="Ruined Spine",
            roll_range=(1, 100),
            effect="bad",
            attr_penalties={"STR": -3},
        )


def test_unknown_positive_id_raises() -> None:
    with pytest.raises(KeyError, match="not in catalog"):
        _catalog().positive_by_id("exotic/wings")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.mutation'`

- [ ] **Step 3: Write the implementation**

Create `sidequest/mutation/__init__.py`:

```python
"""AWN mutation subsystem — bespoke per AWN spec D5, NOT the MagicPlugin seam.

Spec: orc-quest docs/superpowers/specs/2026-06-09-awn-plan2-mutations-design.md
"""
```

Create `sidequest/mutation/models.py`:

```python
"""Mutation catalog models — structural validation only.

Content invariants (exactly 10 positives per category, the faithful AWN
d100 table) are enforced by the sidequest-content pack validator, not
here (spec P2-4). This module guarantees what RESOLUTION needs: unique
slug-shaped ids, a gapless/non-overlapping d100 partition, and the -2
attribute-penalty floor (AWN p.18).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CATEGORIES = ("structure", "sense", "hybrid", "cognition", "pseudo_psychic", "exotic")

_ID_RE = re.compile(r"^[a-z_]+/[a-z0-9_]+$")


class MutationAttack(BaseModel):
    """Natural-weapon block — resolves via the existing CWN attack stack."""

    model_config = {"extra": "forbid"}

    skill: str
    damage: str
    shock: str | None = None
    trauma_die: str | None = None
    trauma_rating: str | None = None


class SaveVs(BaseModel):
    """Save clause — same shape innate_v1 codified (stat None = auto-apply)."""

    model_config = {"extra": "forbid"}

    stat: str | None = None
    effect: str = "negates"


class PositiveMutationDef(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    name: str
    category: Literal[
        "structure", "sense", "hybrid", "cognition", "pseudo_psychic", "exotic"
    ]
    effect: str
    strain_cost: int = Field(default=0, ge=0)
    usage: Literal["at_will", "per_scene", "per_day"] = "at_will"
    uses_per_period: int = Field(default=1, ge=1)
    save: SaveVs | None = None
    attack: MutationAttack | None = None
    modifiers: dict[str, int] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def id_slug_shape(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError(f"mutation id {v!r} must match <category>/<snake_case>")
        return v

    @model_validator(mode="after")
    def id_prefix_matches_category(self) -> PositiveMutationDef:
        prefix = self.id.split("/", 1)[0]
        if prefix != self.category:
            raise ValueError(
                f"id prefix {prefix!r} must equal category {self.category!r} (id={self.id!r})"
            )
        return self


class NegativeMutationDef(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    name: str
    roll_range: tuple[int, int]
    effect: str
    attr_penalties: dict[str, int] = Field(default_factory=dict)
    modifiers: dict[str, int] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def id_slug_shape(cls, v: str) -> str:
        if not _ID_RE.match(v) or not v.startswith("negative/"):
            raise ValueError(f"negative mutation id {v!r} must match negative/<snake_case>")
        return v

    @field_validator("attr_penalties")
    @classmethod
    def penalty_floor(cls, v: dict[str, int]) -> dict[str, int]:
        for attr, pen in v.items():
            if pen < -2 or pen > 0:
                raise ValueError(
                    f"attr penalty {attr}={pen} out of range; AWN floors penalties at -2 (p.18)"
                )
        return v

    @model_validator(mode="after")
    def range_ordered(self) -> NegativeMutationDef:
        lo, hi = self.roll_range
        if not (1 <= lo <= hi <= 100):
            raise ValueError(f"roll_range {self.roll_range} must satisfy 1 <= lo <= hi <= 100")
        return self


class StigmaTables(BaseModel):
    """d6 body-part x d6 nature x d12 flavor (AWN p.17)."""

    model_config = {"extra": "forbid"}

    body_part: list[str]
    nature: list[str]
    flavor: list[str]

    @model_validator(mode="after")
    def table_sizes(self) -> StigmaTables:
        if len(self.body_part) != 6 or len(self.nature) != 6 or len(self.flavor) != 12:
            raise ValueError(
                f"stigma tables must be d6/d6/d12 — got "
                f"{len(self.body_part)}/{len(self.nature)}/{len(self.flavor)}"
            )
        return self


class MpEconomy(BaseModel):
    """The AWN MP economy numbers (p.16) — data, not code."""

    model_config = {"extra": "forbid"}

    mutant_classes: list[str]
    base_mp: int = 2
    per_negative_mp: int = 2
    max_negatives: int = 3
    concealable_stigma_cost: int = 1
    spend_random_positive: int = 1
    spend_pick_positive: int = 3
    spend_same_category: int = 3
    chargen_negatives_rolled: int = 1


class MutationCatalog(BaseModel):
    model_config = {"extra": "forbid"}

    mp_economy: MpEconomy
    stigma: StigmaTables
    negatives: list[NegativeMutationDef]
    positives: list[PositiveMutationDef]
    narrator_register: str = ""

    @model_validator(mode="after")
    def unique_ids(self) -> MutationCatalog:
        ids = [m.id for m in self.negatives] + [m.id for m in self.positives]
        seen: set[str] = set()
        dupes = {i for i in ids if i in seen or seen.add(i)}  # type: ignore[func-returns-value]
        if dupes:
            raise ValueError(f"duplicate mutation ids: {sorted(dupes)}")
        return self

    @model_validator(mode="after")
    def d100_partition(self) -> MutationCatalog:
        ranges = sorted(m.roll_range for m in self.negatives)
        cursor = 1
        for lo, hi in ranges:
            if lo != cursor:
                raise ValueError(
                    f"negative d100 table must partition 1-100 exactly; "
                    f"expected next range to start at {cursor}, got {lo}"
                )
            cursor = hi + 1
        if cursor != 101:
            raise ValueError(
                f"negative d100 table must partition 1-100 exactly; coverage ends at {cursor - 1}"
            )
        return self

    def positive_by_id(self, mutation_id: str) -> PositiveMutationDef:
        for m in self.positives:
            if m.id == mutation_id:
                return m
        raise KeyError(
            f"positive mutation {mutation_id!r} not in catalog; "
            f"known: {sorted(m.id for m in self.positives)}"
        )

    def negative_for_roll(self, roll: int) -> NegativeMutationDef:
        for m in self.negatives:
            lo, hi = m.roll_range
            if lo <= roll <= hi:
                return m
        raise ValueError(f"d100 roll {roll} matched no negative range (validator should prevent)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_models.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/mutation/ tests/mutation/
git commit -m "feat(mutation): catalog models with structural validators (AWN Plan 2)"
```

---

### Task 2: Deterministic resume-safe rolls

**Files:**
- Create: `sidequest/mutation/rolls.py`
- Test: `tests/mutation/test_rolls.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mutation/test_rolls.py`:

```python
from __future__ import annotations

from sidequest.mutation.rolls import deterministic_roll


def test_same_inputs_same_roll() -> None:
    a = deterministic_roll(session_id="s1", actor="Rux", purpose="negative_d100", sequence=1, sides=100)
    b = deterministic_roll(session_id="s1", actor="Rux", purpose="negative_d100", sequence=1, sides=100)
    assert a == b


def test_sequence_changes_roll_distribution() -> None:
    rolls = {
        deterministic_roll(session_id="s1", actor="Rux", purpose="negative_d100", sequence=i, sides=100)
        for i in range(50)
    }
    assert len(rolls) > 10  # not constant; 50 draws over d100 must vary


def test_in_range() -> None:
    for i in range(200):
        r = deterministic_roll(session_id="s1", actor="Rux", purpose="stigma_flavor", sequence=i, sides=12)
        assert 1 <= r <= 12


def test_actor_and_purpose_independent() -> None:
    a = deterministic_roll(session_id="s1", actor="Rux", purpose="p1", sequence=1, sides=100)
    b = deterministic_roll(session_id="s1", actor="Kel", purpose="p1", sequence=1, sides=100)
    c = deterministic_roll(session_id="s1", actor="Rux", purpose="p2", sequence=1, sides=100)
    assert not (a == b == c)  # at least one input dimension moves the result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_rolls.py -v`
Expected: FAIL with `ModuleNotFoundError` (rolls module missing)

- [ ] **Step 3: Write the implementation**

Create `sidequest/mutation/rolls.py`:

```python
"""Deterministic, resume-safe dice for mutation acquisition.

House pattern from lull_escalation.py: SHA-256 over stable identifiers,
NO ``random`` module, NO wallclock — a resume re-rolls identically
(spec P2-6 / ADR-128). The ``sequence`` input is MutationState.roll_sequence,
which is persisted on the snapshot: each consumed roll increments it, so a
save mid-chargen reloads to the same next roll.
"""

from __future__ import annotations

import hashlib


def deterministic_roll(*, session_id: str, actor: str, purpose: str, sequence: int, sides: int) -> int:
    """Return a 1..sides roll, fully determined by the inputs."""
    if sides < 1:
        raise ValueError(f"sides must be >= 1, got {sides}")
    payload = f"{session_id}|{actor}|{purpose}|{sequence}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") % sides + 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_rolls.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/mutation/rolls.py tests/mutation/test_rolls.py
git commit -m "feat(mutation): deterministic resume-safe rolls"
```

---

### Task 3: Mutation state models

**Files:**
- Create: `sidequest/mutation/state.py`
- Test: `tests/mutation/test_state.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mutation/test_state.py`:

```python
from __future__ import annotations

from sidequest.mutation.state import (
    CharacterMutationState,
    MutationState,
    StigmaRecord,
    UsageCounter,
)


def test_round_trip_serialization() -> None:
    state = MutationState()
    state.characters["Rux"] = CharacterMutationState(
        mp_remaining=3,
        negative_ids=["negative/withered_arm"],
        positive_ids=["structure/crushing_jaws"],
        stigma=[StigmaRecord(body_part="eyes", nature="luminous", flavor="amber", concealable=True)],
        usage={"structure/crushing_jaws": UsageCounter(period="per_scene", used=1)},
        acquisition_log=["negative/withered_arm", "structure/crushing_jaws"],
    )
    state.roll_sequence = 4
    reloaded = MutationState.model_validate(state.model_dump())
    assert reloaded == state


def test_reset_scene_clears_only_scene_counters() -> None:
    cs = CharacterMutationState(
        mp_remaining=0,
        usage={
            "sense/echo_location": UsageCounter(period="per_scene", used=1),
            "exotic/second_wind": UsageCounter(period="per_day", used=1),
        },
    )
    state = MutationState(characters={"Rux": cs})
    state.reset_scene()
    assert state.characters["Rux"].usage["sense/echo_location"].used == 0
    assert state.characters["Rux"].usage["exotic/second_wind"].used == 1


def test_reset_day_clears_both() -> None:
    cs = CharacterMutationState(
        mp_remaining=0,
        usage={
            "sense/echo_location": UsageCounter(period="per_scene", used=2),
            "exotic/second_wind": UsageCounter(period="per_day", used=1),
        },
    )
    state = MutationState(characters={"Rux": cs})
    state.reset_day()
    assert all(c.used == 0 for c in state.characters["Rux"].usage.values())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError` (state module missing)

- [ ] **Step 3: Write the implementation**

Create `sidequest/mutation/state.py`:

```python
"""MutationState — pydantic field on GameSnapshot (mirrors MagicState).

Per-character mutation crunch: MP pool, owned mutations, stigma, usage
counters. ``roll_sequence`` is the persisted cursor feeding
rolls.deterministic_roll — incrementing it is how a consumed roll
becomes un-rerollable across resumes (spec P2-6).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StigmaRecord(BaseModel):
    model_config = {"extra": "forbid"}

    body_part: str
    nature: str
    flavor: str
    concealable: bool = False


class UsageCounter(BaseModel):
    model_config = {"extra": "forbid"}

    period: Literal["per_scene", "per_day"]
    used: int = 0


class CharacterMutationState(BaseModel):
    model_config = {"extra": "forbid"}

    mp_remaining: int
    stigma: list[StigmaRecord] = Field(default_factory=list)
    negative_ids: list[str] = Field(default_factory=list)
    positive_ids: list[str] = Field(default_factory=list)
    usage: dict[str, UsageCounter] = Field(default_factory=dict)
    # Ordered acquisition history — the negatives-before-positives chargen
    # ordering (AWN p.16) is asserted against this log.
    acquisition_log: list[str] = Field(default_factory=list)


class MutationState(BaseModel):
    model_config = {"extra": "forbid"}

    characters: dict[str, CharacterMutationState] = Field(default_factory=dict)
    roll_sequence: int = 0

    def reset_scene(self) -> None:
        for cs in self.characters.values():
            for counter in cs.usage.values():
                if counter.period == "per_scene":
                    counter.used = 0

    def reset_day(self) -> None:
        for cs in self.characters.values():
            for counter in cs.usage.values():
                counter.used = 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_state.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/mutation/state.py tests/mutation/test_state.py
git commit -m "feat(mutation): MutationState models with usage-reset hooks"
```

---

### Task 4: Catalog YAML loader

**Files:**
- Create: `sidequest/mutation/catalog.py`
- Test: `tests/mutation/test_catalog.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mutation/test_catalog.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from sidequest.mutation.catalog import load_mutation_catalog

VALID_YAML = """
mp_economy:
  mutant_classes: [Mutant]
stigma:
  body_part: [eyes, skin, hands, spine, jaw, hair]
  nature: [luminous, scaled, withered, oversized, translucent, ridged]
  flavor: [amber, silver, weeping, cracked, humming, cold, hot, twitching, numb, bright, dark, shifting]
negatives:
  - id: negative/withered_arm
    name: Withered Arm
    roll_range: [1, 100]
    effect: one arm is weak
    attr_penalties: {STR: -1}
positives:
  - id: structure/crushing_jaws
    name: Crushing Jaws
    category: structure
    effect: bite as a Punch attack
    attack: {skill: Punch, damage: 1d8, shock: "2/AC15"}
"""


def test_loads_valid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "mutations.yaml"
    p.write_text(VALID_YAML, encoding="utf-8")
    cat = load_mutation_catalog(p)
    assert cat.positive_by_id("structure/crushing_jaws").attack.skill == "Punch"
    assert cat.mp_economy.mutant_classes == ["Mutant"]


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="mutations.yaml"):
        load_mutation_catalog(tmp_path / "mutations.yaml")


def test_invalid_yaml_fails_loud(tmp_path: Path) -> None:
    p = tmp_path / "mutations.yaml"
    p.write_text("mp_economy: {mutant_classes: [Mutant]}\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_mutation_catalog(p)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError` (catalog module missing)

- [ ] **Step 3: Write the implementation**

Create `sidequest/mutation/catalog.py`:

```python
"""mutations.yaml -> MutationCatalog. Fail-loud; absence is the CALLER's
decision (the genre loader treats a missing file as 'pack has no mutation
system' — a deliberate authoring choice, mirroring magic.yaml handling)."""

from __future__ import annotations

from pathlib import Path

import yaml

from sidequest.mutation.models import MutationCatalog


def load_mutation_catalog(path: Path) -> MutationCatalog:
    if not path.is_file():
        raise FileNotFoundError(f"mutation catalog not found: {path} (expected mutations.yaml)")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MutationCatalog.model_validate(raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_catalog.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/mutation/catalog.py tests/mutation/test_catalog.py
git commit -m "feat(mutation): fail-loud mutations.yaml catalog loader"
```

---

### Task 5: `awn.mutation.*` OTEL spans

**Files:**
- Create: `sidequest/telemetry/spans/awn.py`
- Modify: `sidequest/telemetry/spans/__init__.py` (add re-export next to line 53's `from .cwn import *`)
- Test: existing `tests/telemetry/test_routing_completeness.py` (no edit — it auto-discovers; this task makes it the gate)

- [ ] **Step 1: Write the span module**

Create `sidequest/telemetry/spans/awn.py` — copy the structure of `sidequest/telemetry/spans/cwn.py` exactly (constants, `SPAN_ROUTES` registration with `extract` lambdas, emit functions using `Span.open`):

```python
"""AWN-specific OTEL spans (mutation subsystem). GM panel = lie detector."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from ._core import SPAN_ROUTES, SpanRoute
from .span import Span

SPAN_AWN_MUTATION_ACQUIRED = "awn.mutation.acquired"
SPAN_ROUTES[SPAN_AWN_MUTATION_ACQUIRED] = SpanRoute(
    event_type="state_transition",
    component="awn",
    extract=lambda span: {
        "field": "mutation",
        "actor": (span.attributes or {}).get("actor", ""),
        "mutation_id": (span.attributes or {}).get("mutation_id", ""),
        "source": (span.attributes or {}).get("source", ""),
        "roll": (span.attributes or {}).get("roll", 0),
        "mp_delta": (span.attributes or {}).get("mp_delta", 0),
        "mp_remaining": (span.attributes or {}).get("mp_remaining", 0),
    },
)


def awn_mutation_acquired_span(
    *,
    actor: str,
    mutation_id: str,
    source: str,
    roll: int,
    mp_delta: int,
    mp_remaining: int,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "mutation",
        "actor": actor,
        "mutation_id": mutation_id,
        "source": source,
        "roll": roll,
        "mp_delta": mp_delta,
        "mp_remaining": mp_remaining,
        **attrs,
    }
    with Span.open(SPAN_AWN_MUTATION_ACQUIRED, attributes, tracer_override=_tracer):
        pass


SPAN_AWN_MUTATION_USED = "awn.mutation.used"
SPAN_ROUTES[SPAN_AWN_MUTATION_USED] = SpanRoute(
    event_type="state_transition",
    component="awn",
    extract=lambda span: {
        "field": "mutation",
        "actor": (span.attributes or {}).get("actor", ""),
        "mutation_id": (span.attributes or {}).get("mutation_id", ""),
        "strain_cost": (span.attributes or {}).get("strain_cost", 0),
        "uses_remaining": (span.attributes or {}).get("uses_remaining", -1),
        "save_stat": (span.attributes or {}).get("save_stat", ""),
        "save_result": (span.attributes or {}).get("save_result", ""),
    },
)


def awn_mutation_used_span(
    *,
    actor: str,
    mutation_id: str,
    strain_cost: int,
    uses_remaining: int,
    save_stat: str = "",
    save_result: str = "",
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "mutation",
        "actor": actor,
        "mutation_id": mutation_id,
        "strain_cost": strain_cost,
        "uses_remaining": uses_remaining,
        "save_stat": save_stat,
        "save_result": save_result,
        **attrs,
    }
    with Span.open(SPAN_AWN_MUTATION_USED, attributes, tracer_override=_tracer):
        pass


SPAN_AWN_MUTATION_REFUSED = "awn.mutation.refused"
SPAN_ROUTES[SPAN_AWN_MUTATION_REFUSED] = SpanRoute(
    event_type="state_transition",
    component="awn",
    extract=lambda span: {
        "field": "mutation",
        "actor": (span.attributes or {}).get("actor", ""),
        "mutation_id": (span.attributes or {}).get("mutation_id", ""),
        "reason": (span.attributes or {}).get("reason", ""),
    },
)


def awn_mutation_refused_span(
    *,
    actor: str,
    mutation_id: str,
    reason: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "mutation",
        "actor": actor,
        "mutation_id": mutation_id,
        "reason": reason,
        **attrs,
    }
    with Span.open(SPAN_AWN_MUTATION_REFUSED, attributes, tracer_override=_tracer):
        pass


SPAN_AWN_MUTATION_MP_SPEND = "awn.mutation.mp_spend"
SPAN_ROUTES[SPAN_AWN_MUTATION_MP_SPEND] = SpanRoute(
    event_type="state_transition",
    component="awn",
    extract=lambda span: {
        "field": "mutation_mp",
        "actor": (span.attributes or {}).get("actor", ""),
        "spend_kind": (span.attributes or {}).get("spend_kind", ""),
        "cost": (span.attributes or {}).get("cost", 0),
        "mp_remaining": (span.attributes or {}).get("mp_remaining", 0),
    },
)


def awn_mutation_mp_spend_span(
    *,
    actor: str,
    spend_kind: str,
    cost: int,
    mp_remaining: int,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "mutation_mp",
        "actor": actor,
        "spend_kind": spend_kind,
        "cost": cost,
        "mp_remaining": mp_remaining,
        **attrs,
    }
    with Span.open(SPAN_AWN_MUTATION_MP_SPEND, attributes, tracer_override=_tracer):
        pass
```

- [ ] **Step 2: Wire the re-export**

In `sidequest/telemetry/spans/__init__.py`, directly after the line `from .cwn import *  # noqa: F401, F403` (line 53), add:

```python
from .awn import *  # noqa: F401, F403
```

- [ ] **Step 3: Run the routing-completeness gate**

Run: `uv run pytest tests/telemetry/test_routing_completeness.py -v`
Expected: PASS — every new `SPAN_*` constant has a `SPAN_ROUTES` entry. If it FAILS with "Spans without a routing decision", a constant is missing its route — fix before proceeding.

- [ ] **Step 4: Commit**

```bash
git add sidequest/telemetry/spans/awn.py sidequest/telemetry/spans/__init__.py
git commit -m "feat(telemetry): awn.mutation.* spans with GM-panel routes"
```

---

### Task 6: Acquisition ops (MP arithmetic + negative-first ordering)

**Files:**
- Create: `sidequest/mutation/acquire_ops.py`
- Test: `tests/mutation/test_acquire_ops.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mutation/test_acquire_ops.py`. Reuse Task 1's synthetic-catalog helpers by importing them — add this catalog builder locally (tests must be self-contained per file):

```python
from __future__ import annotations

import pytest

from sidequest.mutation.acquire_ops import (
    acquire_positive,
    acquire_random_negative,
    roll_stigma,
)
from sidequest.mutation.models import (
    MpEconomy,
    MutationCatalog,
    NegativeMutationDef,
    PositiveMutationDef,
    StigmaTables,
)
from sidequest.mutation.state import CharacterMutationState, MutationState


def _catalog() -> MutationCatalog:
    return MutationCatalog(
        mp_economy=MpEconomy(mutant_classes=["Mutant"]),
        stigma=StigmaTables(
            body_part=["eyes", "skin", "hands", "spine", "jaw", "hair"],
            nature=["luminous", "scaled", "withered", "oversized", "translucent", "ridged"],
            flavor=["amber", "silver", "weeping", "cracked", "humming", "cold",
                    "hot", "twitching", "numb", "bright", "dark", "shifting"],
        ),
        negatives=[
            NegativeMutationDef(id="negative/withered_arm", name="Withered Arm",
                                roll_range=(1, 50), effect="weak arm"),
            NegativeMutationDef(id="negative/frail", name="Frail",
                                roll_range=(51, 100), effect="frail"),
        ],
        positives=[
            PositiveMutationDef(id="structure/crushing_jaws", name="Crushing Jaws",
                                category="structure", effect="bite"),
            PositiveMutationDef(id="structure/savage_claws", name="Savage Claws",
                                category="structure", effect="claws"),
            PositiveMutationDef(id="sense/echo_location", name="Echo Location",
                                category="sense", effect="sonar"),
        ],
    )


def _state(mp: int = 0) -> MutationState:
    return MutationState(characters={"Rux": CharacterMutationState(mp_remaining=mp)})


def test_negative_grants_mp_and_logs() -> None:
    state, cat = _state(), _catalog()
    result = acquire_random_negative(state, cat, actor="Rux", session_id="s1", source="chargen")
    assert result.applied
    cs = state.characters["Rux"]
    assert cs.mp_remaining == cat.mp_economy.per_negative_mp
    assert cs.negative_ids == [result.mutation_id]
    assert cs.acquisition_log == [result.mutation_id]
    assert state.roll_sequence > 0


def test_negative_cap_refused() -> None:
    state, cat = _state(), _catalog()
    cs = state.characters["Rux"]
    cs.negative_ids = ["negative/a", "negative/b", "negative/c"]
    result = acquire_random_negative(state, cat, actor="Rux", session_id="s1", source="chargen")
    assert not result.applied
    assert "max_negatives" in result.reason


def test_negative_reroll_on_duplicate_is_deterministic() -> None:
    s1, s2 = _state(), _state()
    cat = _catalog()
    for state in (s1, s2):
        acquire_random_negative(state, cat, actor="Rux", session_id="s1", source="chargen")
        acquire_random_negative(state, cat, actor="Rux", session_id="s1", source="chargen")
    assert s1.characters["Rux"].negative_ids == s2.characters["Rux"].negative_ids
    assert len(set(s1.characters["Rux"].negative_ids)) == 2  # both table entries, no dupe


def test_random_positive_costs_one() -> None:
    state, cat = _state(mp=2), _catalog()
    result = acquire_positive(state, cat, actor="Rux", session_id="s1", source="chargen")
    assert result.applied
    assert state.characters["Rux"].mp_remaining == 2 - cat.mp_economy.spend_random_positive
    assert result.mutation_id in {p.id for p in cat.positives}


def test_picked_positive_costs_three() -> None:
    state, cat = _state(mp=3), _catalog()
    result = acquire_positive(
        state, cat, actor="Rux", session_id="s1", source="chargen",
        mutation_id="sense/echo_location",
    )
    assert result.applied
    assert state.characters["Rux"].mp_remaining == 0
    assert state.characters["Rux"].positive_ids == ["sense/echo_location"]


def test_second_same_category_costs_three_even_random() -> None:
    state, cat = _state(mp=4), _catalog()
    state.characters["Rux"].positive_ids = ["structure/crushing_jaws"]
    result = acquire_positive(
        state, cat, actor="Rux", session_id="s1", source="chargen", category="structure",
    )
    assert result.applied
    assert result.mutation_id == "structure/savage_claws"
    assert state.characters["Rux"].mp_remaining == 4 - cat.mp_economy.spend_same_category


def test_insufficient_mp_refused() -> None:
    state, cat = _state(mp=0), _catalog()
    result = acquire_positive(state, cat, actor="Rux", session_id="s1", source="chargen")
    assert not result.applied
    assert "insufficient_mp" in result.reason
    assert state.characters["Rux"].positive_ids == []


def test_unknown_actor_raises() -> None:
    state, cat = _state(), _catalog()
    with pytest.raises(KeyError, match="Nobody"):
        acquire_random_negative(state, cat, actor="Nobody", session_id="s1", source="chargen")


def test_stigma_rolls_three_tables() -> None:
    state, cat = _state(), _catalog()
    record = roll_stigma(state, cat, actor="Rux", session_id="s1")
    assert record is not None
    assert record.body_part in cat.stigma.body_part
    assert record.nature in cat.stigma.nature
    assert record.flavor in cat.stigma.flavor
    assert state.characters["Rux"].stigma == [record]


def test_concealable_stigma_costs_mp_and_refuses_when_broke() -> None:
    state, cat = _state(mp=0), _catalog()
    record = roll_stigma(state, cat, actor="Rux", session_id="s1", concealable=True)
    assert record is None  # refused — no MP for concealment
    state2 = _state(mp=1)
    record2 = roll_stigma(state2, cat, actor="Rux", session_id="s1", concealable=True)
    assert record2 is not None and record2.concealable
    assert state2.characters["Rux"].mp_remaining == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_acquire_ops.py -v`
Expected: FAIL with `ModuleNotFoundError` (acquire_ops missing)

- [ ] **Step 3: Write the implementation**

Create `sidequest/mutation/acquire_ops.py`:

```python
"""Mutation acquisition — MP arithmetic + deterministic rolls + OTEL.

Refusals (cap hit, insufficient MP) return applied=False with a reason,
mirroring StrainResult — the narrator describes the limit, never
improvises past it. Engine misuse (unknown actor) raises loudly.
"""

from __future__ import annotations

from pydantic import BaseModel

from sidequest.mutation.models import MutationCatalog
from sidequest.mutation.rolls import deterministic_roll
from sidequest.mutation.state import CharacterMutationState, MutationState, StigmaRecord
from sidequest.telemetry.spans.awn import (
    awn_mutation_acquired_span,
    awn_mutation_mp_spend_span,
    awn_mutation_refused_span,
)


class AcquireResult(BaseModel):
    model_config = {"extra": "forbid"}

    applied: bool
    actor: str
    mutation_id: str = ""
    roll: int = 0
    mp_delta: int = 0
    mp_remaining: int = 0
    reason: str = ""


def _character(state: MutationState, actor: str) -> CharacterMutationState:
    if actor not in state.characters:
        raise KeyError(
            f"actor {actor!r} has no mutation state; known: {sorted(state.characters)}"
        )
    return state.characters[actor]


def acquire_random_negative(
    state: MutationState,
    catalog: MutationCatalog,
    *,
    actor: str,
    session_id: str,
    source: str,
) -> AcquireResult:
    cs = _character(state, actor)
    eco = catalog.mp_economy
    if len(cs.negative_ids) >= eco.max_negatives:
        awn_mutation_refused_span(actor=actor, mutation_id="", reason="max_negatives")
        return AcquireResult(
            applied=False, actor=actor, mp_remaining=cs.mp_remaining,
            reason=f"max_negatives ({eco.max_negatives}) reached",
        )
    # Bounded dedupe re-roll: deterministic because every attempt consumes
    # a persisted sequence number. Cap = table size, then fail loud.
    for _ in range(len(catalog.negatives) * 4):
        state.roll_sequence += 1
        roll = deterministic_roll(
            session_id=session_id, actor=actor, purpose="negative_d100",
            sequence=state.roll_sequence, sides=100,
        )
        nd = catalog.negative_for_roll(roll)
        if nd.id not in cs.negative_ids:
            cs.negative_ids.append(nd.id)
            cs.acquisition_log.append(nd.id)
            cs.mp_remaining += eco.per_negative_mp
            awn_mutation_acquired_span(
                actor=actor, mutation_id=nd.id, source=source, roll=roll,
                mp_delta=eco.per_negative_mp, mp_remaining=cs.mp_remaining,
            )
            return AcquireResult(
                applied=True, actor=actor, mutation_id=nd.id, roll=roll,
                mp_delta=eco.per_negative_mp, mp_remaining=cs.mp_remaining,
            )
    raise ValueError(
        f"could not roll a non-duplicate negative for {actor!r}; "
        f"owned={cs.negative_ids}, table={[n.id for n in catalog.negatives]}"
    )


def _positive_spend_cost(
    cs: CharacterMutationState, catalog: MutationCatalog, *, picked: bool, category: str
) -> tuple[int, str]:
    eco = catalog.mp_economy
    if picked:
        return eco.spend_pick_positive, "pick"
    if any(pid.split("/", 1)[0] == category for pid in cs.positive_ids):
        return eco.spend_same_category, "same_category"
    return eco.spend_random_positive, "random"


def acquire_positive(
    state: MutationState,
    catalog: MutationCatalog,
    *,
    actor: str,
    session_id: str,
    source: str,
    mutation_id: str | None = None,
    category: str | None = None,
) -> AcquireResult:
    """Picked (mutation_id given) or random (optionally within category)."""
    cs = _character(state, actor)

    if mutation_id is not None:
        target = catalog.positive_by_id(mutation_id)  # KeyError loud on bad id
        candidates = [target]
        picked = True
        resolved_category = target.category
    else:
        pool = [
            p for p in catalog.positives
            if p.id not in cs.positive_ids and (category is None or p.category == category)
        ]
        if not pool:
            awn_mutation_refused_span(actor=actor, mutation_id="", reason="pool_exhausted")
            return AcquireResult(
                applied=False, actor=actor, mp_remaining=cs.mp_remaining,
                reason=f"pool_exhausted (category={category!r})",
            )
        candidates = sorted(pool, key=lambda p: p.id)
        picked = False
        resolved_category = category or ""

    if picked and mutation_id in cs.positive_ids:
        awn_mutation_refused_span(actor=actor, mutation_id=mutation_id or "", reason="already_owned")
        return AcquireResult(
            applied=False, actor=actor, mutation_id=mutation_id or "",
            mp_remaining=cs.mp_remaining, reason="already_owned",
        )

    if not picked:
        state.roll_sequence += 1
        roll = deterministic_roll(
            session_id=session_id, actor=actor, purpose="positive_pick",
            sequence=state.roll_sequence, sides=len(candidates),
        )
        chosen = candidates[roll - 1]
        resolved_category = chosen.category
    else:
        roll = 0
        chosen = candidates[0]

    cost, spend_kind = _positive_spend_cost(cs, catalog, picked=picked, category=resolved_category)
    if cs.mp_remaining < cost:
        awn_mutation_refused_span(actor=actor, mutation_id=chosen.id, reason="insufficient_mp")
        return AcquireResult(
            applied=False, actor=actor, mutation_id=chosen.id, mp_remaining=cs.mp_remaining,
            reason=f"insufficient_mp (need {cost}, have {cs.mp_remaining})",
        )

    cs.mp_remaining -= cost
    cs.positive_ids.append(chosen.id)
    cs.acquisition_log.append(chosen.id)
    awn_mutation_mp_spend_span(
        actor=actor, spend_kind=spend_kind, cost=cost, mp_remaining=cs.mp_remaining,
    )
    awn_mutation_acquired_span(
        actor=actor, mutation_id=chosen.id, source=source, roll=roll,
        mp_delta=-cost, mp_remaining=cs.mp_remaining,
    )
    return AcquireResult(
        applied=True, actor=actor, mutation_id=chosen.id, roll=roll,
        mp_delta=-cost, mp_remaining=cs.mp_remaining,
    )


def roll_stigma(
    state: MutationState,
    catalog: MutationCatalog,
    *,
    actor: str,
    session_id: str,
    concealable: bool = False,
) -> StigmaRecord | None:
    """Roll d6 body-part x d6 nature x d12 flavor. Concealable costs MP;
    returns None (refusal) when the actor can't afford concealment."""
    cs = _character(state, actor)
    eco = catalog.mp_economy
    if concealable:
        if cs.mp_remaining < eco.concealable_stigma_cost:
            awn_mutation_refused_span(actor=actor, mutation_id="", reason="insufficient_mp_stigma")
            return None
        cs.mp_remaining -= eco.concealable_stigma_cost
        awn_mutation_mp_spend_span(
            actor=actor, spend_kind="concealable_stigma",
            cost=eco.concealable_stigma_cost, mp_remaining=cs.mp_remaining,
        )
    rolls: list[int] = []
    for purpose, sides in (("stigma_body", 6), ("stigma_nature", 6), ("stigma_flavor", 12)):
        state.roll_sequence += 1
        rolls.append(
            deterministic_roll(
                session_id=session_id, actor=actor, purpose=purpose,
                sequence=state.roll_sequence, sides=sides,
            )
        )
    record = StigmaRecord(
        body_part=catalog.stigma.body_part[rolls[0] - 1],
        nature=catalog.stigma.nature[rolls[1] - 1],
        flavor=catalog.stigma.flavor[rolls[2] - 1],
        concealable=concealable,
    )
    cs.stigma.append(record)
    return record
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_acquire_ops.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/mutation/acquire_ops.py tests/mutation/test_acquire_ops.py
git commit -m "feat(mutation): acquisition ops — MP economy, dedupe rerolls, stigma"
```

---

### Task 7: Use ops (ownership / limits / Strain / save-vs)

**Files:**
- Create: `sidequest/mutation/use_ops.py`
- Test: `tests/mutation/test_use_ops.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mutation/test_use_ops.py`. The Strain seam is exercised through the REAL `AwnRulesetModule` with a synthetic `CreatureCore` + `AwnConfig` — look at `tests/game/ruleset/test_awn_config.py` for how existing tests construct an `AwnConfig` (it needs the six-key `attribute_map`); mirror that construction here:

```python
from __future__ import annotations

from sidequest.game.creature_core import CreatureCore
from sidequest.game.ruleset.awn import AwnRulesetModule
from sidequest.game.system_strain import SystemStrainPool
from sidequest.genre.models.rules import AwnConfig
from sidequest.mutation.models import (
    MpEconomy,
    MutationCatalog,
    NegativeMutationDef,
    PositiveMutationDef,
    SaveVs,
    StigmaTables,
)
from sidequest.mutation.state import CharacterMutationState, MutationState
from sidequest.mutation.use_ops import use_mutation

_SIX = {
    "STRENGTH": "STR", "DEXTERITY": "DEX", "CONSTITUTION": "CON",
    "INTELLIGENCE": "INT", "WISDOM": "WIS", "CHARISMA": "CHA",
}


def _cfg() -> AwnConfig:
    return AwnConfig(attribute_map=_SIX)


def _core(strain_max: int = 10, strain_current: int = 0) -> CreatureCore:
    core = CreatureCore(name="Rux")
    core.system_strain = SystemStrainPool(current=strain_current, max=strain_max, permanent=0)
    return core


def _catalog() -> MutationCatalog:
    return MutationCatalog(
        mp_economy=MpEconomy(mutant_classes=["Mutant"]),
        stigma=StigmaTables(
            body_part=["a"] * 6, nature=["b"] * 6, flavor=["c"] * 12,
        ),
        negatives=[NegativeMutationDef(id="negative/frail", name="Frail",
                                       roll_range=(1, 100), effect="frail")],
        positives=[
            PositiveMutationDef(id="exotic/acid_spit", name="Acid Spit", category="exotic",
                                effect="spit acid", strain_cost=2, usage="per_scene",
                                save=SaveVs(stat="evasion", effect="negates")),
            PositiveMutationDef(id="sense/dark_sight", name="Dark Sight", category="sense",
                                effect="see in dark", strain_cost=0, usage="at_will"),
        ],
    )


def _state_with(*positive_ids: str) -> MutationState:
    return MutationState(characters={
        "Rux": CharacterMutationState(mp_remaining=0, positive_ids=list(positive_ids)),
    })


def test_at_will_passive_use_applies() -> None:
    result = use_mutation(
        state=_state_with("sense/dark_sight"), catalog=_catalog(),
        module=AwnRulesetModule(), cfg=_cfg(), core=_core(),
        actor="Rux", mutation_id="sense/dark_sight",
    )
    assert result.applied
    assert result.strain is None  # zero-cost: strain seam not touched


def test_strain_cost_flows_through_pool() -> None:
    core = _core()
    state = _state_with("exotic/acid_spit")
    result = use_mutation(
        state=state, catalog=_catalog(), module=AwnRulesetModule(), cfg=_cfg(), core=core,
        actor="Rux", mutation_id="exotic/acid_spit",
        save_resolver=lambda stat, target: "fail",
    )
    assert result.applied
    assert core.system_strain.current == 2
    assert state.characters["Rux"].usage["exotic/acid_spit"].used == 1


def test_strain_over_max_refused() -> None:
    core = _core(strain_max=2, strain_current=1)
    result = use_mutation(
        state=_state_with("exotic/acid_spit"), catalog=_catalog(),
        module=AwnRulesetModule(), cfg=_cfg(), core=core,
        actor="Rux", mutation_id="exotic/acid_spit",
        save_resolver=lambda stat, target: "fail",
    )
    assert not result.applied
    assert "strain" in result.reason
    assert core.system_strain.current == 1  # unchanged


def test_usage_limit_refused() -> None:
    state = _state_with("exotic/acid_spit")
    core = _core()
    kwargs = dict(
        state=state, catalog=_catalog(), module=AwnRulesetModule(), cfg=_cfg(), core=core,
        actor="Rux", mutation_id="exotic/acid_spit",
        save_resolver=lambda stat, target: "fail",
    )
    assert use_mutation(**kwargs).applied
    second = use_mutation(**kwargs)
    assert not second.applied
    assert "limit_exhausted" in second.reason


def test_not_owned_refused() -> None:
    result = use_mutation(
        state=_state_with(), catalog=_catalog(),
        module=AwnRulesetModule(), cfg=_cfg(), core=_core(),
        actor="Rux", mutation_id="exotic/acid_spit",
    )
    assert not result.applied
    assert "not_owned" in result.reason


def test_save_resolver_required_when_save_stat_set() -> None:
    import pytest

    with pytest.raises(ValueError, match="save_resolver"):
        use_mutation(
            state=_state_with("exotic/acid_spit"), catalog=_catalog(),
            module=AwnRulesetModule(), cfg=_cfg(), core=_core(),
            actor="Rux", mutation_id="exotic/acid_spit",
        )


def test_save_success_recorded() -> None:
    result = use_mutation(
        state=_state_with("exotic/acid_spit"), catalog=_catalog(),
        module=AwnRulesetModule(), cfg=_cfg(), core=_core(),
        actor="Rux", mutation_id="exotic/acid_spit",
        target_id="raider", save_resolver=lambda stat, target: "success",
    )
    assert result.applied
    assert result.save_stat == "evasion"
    assert result.save_result == "success"
```

If `CreatureCore(name=...)` requires more constructor fields, check `sidequest/game/creature_core.py` and supply the minimal required set — adjust the `_core` helper only, not the assertions.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_use_ops.py -v`
Expected: FAIL with `ModuleNotFoundError` (use_ops missing)

- [ ] **Step 3: Write the implementation**

Create `sidequest/mutation/use_ops.py`:

```python
"""In-play mutation use — ownership, usage limits, Strain, save-vs.

Strain routes through the EXISTING CwnRulesetModule.apply_system_strain
with kind="temporary" and source="mutation:<id>" (plan deviation note 1:
the kind taxonomy is mechanical; provenance rides source). Save-vs uses
the resolver-callable shape codified by innate_v1_cast.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from sidequest.game.creature_core import CreatureCore
from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.game.system_strain import StrainResult
from sidequest.genre.models.rules import SwnConfig
from sidequest.mutation.models import MutationCatalog
from sidequest.mutation.state import MutationState, UsageCounter
from sidequest.telemetry.spans.awn import (
    awn_mutation_refused_span,
    awn_mutation_used_span,
)

SaveResult = Literal["success", "fail"]
SaveResolver = Callable[[str, str], SaveResult]


class UseMutationResult(BaseModel):
    model_config = {"extra": "forbid"}

    applied: bool
    actor: str
    mutation_id: str
    reason: str = ""
    strain: StrainResult | None = None
    uses_remaining: int = -1  # -1 = at_will (unlimited)
    save_stat: str | None = None
    save_result: SaveResult | None = None
    effect: str = ""


def use_mutation(
    *,
    state: MutationState,
    catalog: MutationCatalog,
    module: CwnRulesetModule,
    cfg: SwnConfig | None,
    core: CreatureCore,
    actor: str,
    mutation_id: str,
    target_id: str = "",
    save_resolver: SaveResolver | None = None,
) -> UseMutationResult:
    cs = state.characters.get(actor)
    if cs is None or mutation_id not in cs.positive_ids:
        awn_mutation_refused_span(actor=actor, mutation_id=mutation_id, reason="not_owned")
        return UseMutationResult(
            applied=False, actor=actor, mutation_id=mutation_id,
            reason="not_owned" if cs is not None else "not_owned (actor has no mutation state)",
        )

    md = catalog.positive_by_id(mutation_id)

    # Usage limit
    uses_remaining = -1
    counter: UsageCounter | None = None
    if md.usage != "at_will":
        counter = cs.usage.setdefault(mutation_id, UsageCounter(period=md.usage))
        if counter.used >= md.uses_per_period:
            awn_mutation_refused_span(actor=actor, mutation_id=mutation_id, reason="limit_exhausted")
            return UseMutationResult(
                applied=False, actor=actor, mutation_id=mutation_id,
                reason=f"limit_exhausted ({md.usage}: {counter.used}/{md.uses_per_period})",
            )

    # Save-vs needs a resolver BEFORE any cost is paid
    if md.save is not None and md.save.stat is not None and save_resolver is None:
        raise ValueError(
            f"mutation {mutation_id!r} has save.stat={md.save.stat!r} but no "
            f"save_resolver was provided — the production caller must wire one."
        )

    # Strain cost
    strain: StrainResult | None = None
    if md.strain_cost > 0:
        strain = module.apply_system_strain(
            core=core, kind="temporary", amount=md.strain_cost,
            source=f"mutation:{mutation_id}", cfg=cfg,
        )
        if not strain.applied:
            awn_mutation_refused_span(actor=actor, mutation_id=mutation_id, reason="strain_over_max")
            return UseMutationResult(
                applied=False, actor=actor, mutation_id=mutation_id,
                reason=f"strain_over_max ({strain.reason})", strain=strain,
            )

    # Save-vs resolution (cost already paid — AWN: the power fires, the target saves)
    save_stat: str | None = None
    save_result: SaveResult | None = None
    if md.save is not None and md.save.stat is not None:
        assert save_resolver is not None  # guarded above
        save_stat = md.save.stat
        save_result = save_resolver(md.save.stat, target_id)

    if counter is not None:
        counter.used += 1
        uses_remaining = md.uses_per_period - counter.used

    awn_mutation_used_span(
        actor=actor, mutation_id=mutation_id, strain_cost=md.strain_cost,
        uses_remaining=uses_remaining,
        save_stat=save_stat or "", save_result=save_result or "",
    )
    return UseMutationResult(
        applied=True, actor=actor, mutation_id=mutation_id, strain=strain,
        uses_remaining=uses_remaining, save_stat=save_stat, save_result=save_result,
        effect=md.effect,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_use_ops.py -v`
Expected: all PASS. If `AwnConfig(attribute_map=...)` fails validation, read `sidequest/genre/models/rules.py`'s `_validate_awn`/`_validate_cwn` for required fields and supply them in `_cfg()` — change the fixture, not the op.

- [ ] **Step 5: Commit**

```bash
git add sidequest/mutation/use_ops.py tests/mutation/test_use_ops.py
git commit -m "feat(mutation): use ops — limits, strain via cwn seam, save-vs"
```

---

### Task 8: Chargen seeding

**Files:**
- Create: `sidequest/mutation/chargen.py`
- Test: `tests/mutation/test_chargen.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mutation/test_chargen.py` (reuse the `_catalog()` builder from Task 6's test file verbatim — copy it in; test files stay self-contained):

```python
from __future__ import annotations

from sidequest.mutation.chargen import seed_character_mutations
from sidequest.mutation.models import (
    MpEconomy,
    MutationCatalog,
    NegativeMutationDef,
    PositiveMutationDef,
    StigmaTables,
)
from sidequest.mutation.state import MutationState


def _catalog() -> MutationCatalog:
    return MutationCatalog(
        mp_economy=MpEconomy(mutant_classes=["Mutant"], chargen_negatives_rolled=1),
        stigma=StigmaTables(body_part=["a"] * 6, nature=["b"] * 6, flavor=["c"] * 12),
        negatives=[
            NegativeMutationDef(id="negative/withered_arm", name="W", roll_range=(1, 50), effect="x"),
            NegativeMutationDef(id="negative/frail", name="F", roll_range=(51, 100), effect="y"),
        ],
        positives=[
            PositiveMutationDef(id="structure/crushing_jaws", name="C",
                                category="structure", effect="bite"),
        ],
    )


def test_mutant_class_seeds_state() -> None:
    state = MutationState()
    cs = seed_character_mutations(
        state, _catalog(), actor="Rux", character_class="Mutant", session_id="s1",
    )
    assert cs is not None
    assert state.characters["Rux"] is cs
    # base_mp (2) + one rolled negative (+2)
    assert cs.mp_remaining == 4
    assert len(cs.negative_ids) == 1
    # negatives-first ordering: the log starts with the negative
    assert cs.acquisition_log[0].startswith("negative/")


def test_non_mutant_class_gets_none() -> None:
    state = MutationState()
    cs = seed_character_mutations(
        state, _catalog(), actor="Rux", character_class="Scavenger", session_id="s1",
    )
    assert cs is None
    assert "Rux" not in state.characters


def test_seeding_is_idempotent() -> None:
    state = MutationState()
    catalog = _catalog()
    first = seed_character_mutations(
        state, catalog, actor="Rux", character_class="Mutant", session_id="s1",
    )
    again = seed_character_mutations(
        state, catalog, actor="Rux", character_class="Mutant", session_id="s1",
    )
    assert again is first is not None
    assert len(state.characters["Rux"].negative_ids) == 1  # not re-rolled


def test_resume_safety_same_negative() -> None:
    catalogs = (_catalog(), _catalog())
    states = (MutationState(), MutationState())
    results = [
        seed_character_mutations(s, c, actor="Rux", character_class="Mutant", session_id="s1")
        for s, c in zip(states, catalogs)
    ]
    assert results[0] is not None and results[1] is not None
    assert results[0].negative_ids == results[1].negative_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_chargen.py -v`
Expected: FAIL with `ModuleNotFoundError` (chargen missing)

- [ ] **Step 3: Write the implementation**

Create `sidequest/mutation/chargen.py`:

```python
"""Chargen mutation seeding — the catalog's mutant_classes carries the
grant (plan deviation note 2: mutant_wasteland has no classes.yaml, so
the ClassDef seam can't; content-driven keeps it homebrew-extensible).

Negatives are rolled FIRST (AWN p.16 — burdens before gifts); the MP
they grant stays unspent for the guided in-play / chargen spend via
acquire_ops. Idempotent: an already-seeded actor returns the existing
state unchanged (re-entrant chargen handlers must not re-roll)."""

from __future__ import annotations

from sidequest.mutation.acquire_ops import acquire_random_negative
from sidequest.mutation.models import MutationCatalog
from sidequest.mutation.state import CharacterMutationState, MutationState


def seed_character_mutations(
    state: MutationState,
    catalog: MutationCatalog,
    *,
    actor: str,
    character_class: str,
    session_id: str,
) -> CharacterMutationState | None:
    if character_class not in catalog.mp_economy.mutant_classes:
        return None
    if actor in state.characters:
        return state.characters[actor]  # idempotent — never re-roll
    cs = CharacterMutationState(mp_remaining=catalog.mp_economy.base_mp)
    state.characters[actor] = cs
    for _ in range(catalog.mp_economy.chargen_negatives_rolled):
        acquire_random_negative(state, catalog, actor=actor, session_id=session_id, source="chargen")
    return cs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_chargen.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/mutation/chargen.py tests/mutation/test_chargen.py
git commit -m "feat(mutation): chargen seeding — catalog-declared class grant, negatives first"
```

---

### Task 9: Catalog rides GenrePack

**Files:**
- Modify: `sidequest/genre/models/pack.py` (field near `bestiary` at :209)
- Modify: `sidequest/genre/loader.py` (genre-tier load)
- Test: `tests/mutation/test_pack_loading.py`

- [ ] **Step 1: Write the failing test**

Create `tests/mutation/test_pack_loading.py`:

```python
"""GenrePack carries an optional MutationCatalog; absence = no mutation system."""

from __future__ import annotations

from sidequest.genre.models.pack import GenrePack
from sidequest.mutation.models import MutationCatalog


def test_genre_pack_has_mutations_field() -> None:
    assert "mutations" in GenrePack.model_fields
    field = GenrePack.model_fields["mutations"]
    assert field.default is None
    # The annotation is MutationCatalog | None
    assert MutationCatalog in getattr(field.annotation, "__args__", (field.annotation,))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/mutation/test_pack_loading.py -v`
Expected: FAIL with `AssertionError` ("mutations" not in model_fields)

- [ ] **Step 3: Add the field**

In `sidequest/genre/models/pack.py`, import at the top (alphabetical with the other `sidequest.` imports):

```python
from sidequest.mutation.models import MutationCatalog
```

Then add the field next to `bestiary: Bestiary | None = None` (line 209):

```python
    mutations: MutationCatalog | None = None
    """Genre-tier ``mutations.yaml`` (AWN Plan 2): the mutation catalog the
    awn ruleset's mutation subsystem resolves against. None = the pack has
    no mutation system (a deliberate authoring choice, like magic.yaml)."""
```

If this import creates a circular import (`genre.models` ← `mutation.models` — `mutation/models.py` imports nothing from `genre`, so it should not), run the test to confirm before proceeding.

- [ ] **Step 4: Wire the loader**

In `sidequest/genre/loader.py`, find the genre-tier `GenrePack(` construction site:

Run: `grep -n "GenrePack(" sidequest/genre/loader.py`

At that construction (where `rules=`, `prompts=`, etc. are passed), add a `mutations=` argument loaded the same way the optional genre-tier files are. Immediately before the construction, add (using the same `genre_root`/pack-dir variable in scope there — verify its name):

```python
    mutations_path = genre_root / "mutations.yaml"
    mutations = load_mutation_catalog(mutations_path) if mutations_path.is_file() else None
```

with the import at the top of `loader.py`:

```python
from sidequest.mutation.catalog import load_mutation_catalog
```

and pass `mutations=mutations` into the `GenrePack(...)` constructor. **Note:** absence is silent by design (matches the magic.yaml comment at `loader.py:1314-1318`); a *present but invalid* file fails loud via the loader's ValidationError.

- [ ] **Step 5: Run the test + the genre suite**

Run: `uv run pytest tests/mutation/test_pack_loading.py tests/genre/ -v`
Expected: new test PASSES; the existing genre suite stays green (the field is optional with default None, so all existing packs load unchanged).

- [ ] **Step 6: Commit**

```bash
git add sidequest/genre/models/pack.py sidequest/genre/loader.py tests/mutation/test_pack_loading.py
git commit -m "feat(genre): GenrePack.mutations — optional genre-tier mutations.yaml"
```

---

### Task 10: Snapshot field + per-session init

**Files:**
- Modify: `sidequest/game/session.py` (field next to `magic_state` at :1038)
- Create: `sidequest/server/mutation_init.py`
- Modify: `sidequest/server/websocket_handlers/chargen_mixin.py` (calls adjacent to `init_magic_state_for_session` at :895 and :1117)
- Test: `tests/mutation/test_mutation_init.py`

- [ ] **Step 1: Add the snapshot field**

In `sidequest/game/session.py`, directly after the `magic_state` field (line 1038), add:

```python
    # AWN mutation state (Plan 2). None on saves that predate mutations or
    # on packs without a mutations.yaml catalog.
    mutation_state: MutationState | None = None
```

with the import near the existing `MagicState` import:

```python
from sidequest.mutation.state import MutationState
```

- [ ] **Step 2: Write the failing init tests**

Create `tests/mutation/test_mutation_init.py`:

```python
from __future__ import annotations

from sidequest.game.session import GameSnapshot
from sidequest.mutation.models import (
    MpEconomy,
    MutationCatalog,
    NegativeMutationDef,
    PositiveMutationDef,
    StigmaTables,
)
from sidequest.server.mutation_init import init_mutation_state_for_session


def _catalog() -> MutationCatalog:
    return MutationCatalog(
        mp_economy=MpEconomy(mutant_classes=["Mutant"]),
        stigma=StigmaTables(body_part=["a"] * 6, nature=["b"] * 6, flavor=["c"] * 12),
        negatives=[NegativeMutationDef(id="negative/frail", name="F",
                                       roll_range=(1, 100), effect="y")],
        positives=[PositiveMutationDef(id="structure/crushing_jaws", name="C",
                                       category="structure", effect="bite")],
    )


def _snapshot() -> GameSnapshot:
    # Mirror the minimal-GameSnapshot construction used by existing tests:
    # grep "GameSnapshot(" tests/ for the lightest fixture and reuse its shape.
    return GameSnapshot.model_construct(mutation_state=None)


def test_no_catalog_skips_silently() -> None:
    snap = _snapshot()
    init_mutation_state_for_session(
        snap, catalog=None, character_name="Rux", character_class="Mutant", session_id="s1",
    )
    assert snap.mutation_state is None


def test_mutant_seeds_snapshot_state() -> None:
    snap = _snapshot()
    init_mutation_state_for_session(
        snap, catalog=_catalog(), character_name="Rux", character_class="Mutant", session_id="s1",
    )
    assert snap.mutation_state is not None
    assert "Rux" in snap.mutation_state.characters


def test_non_mutant_leaves_no_character_entry() -> None:
    snap = _snapshot()
    init_mutation_state_for_session(
        snap, catalog=_catalog(), character_name="Rux", character_class="Scavenger", session_id="s1",
    )
    # container may exist (created on first init), but no entry for a non-mutant
    if snap.mutation_state is not None:
        assert "Rux" not in snap.mutation_state.characters
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/mutation/test_mutation_init.py -v`
Expected: FAIL with `ModuleNotFoundError` (mutation_init missing)

- [ ] **Step 4: Write mutation_init**

Create `sidequest/server/mutation_init.py`:

```python
"""Per-session mutation-state initialization — peer of magic_init.py.

Called at chargen confirmation alongside init_magic_state_for_session.
Packs without a mutations.yaml catalog skip silently (deliberate
authoring choice, mirroring magic_init's absent-file doctrine)."""

from __future__ import annotations

import logging

from sidequest.game.session import GameSnapshot
from sidequest.mutation.chargen import seed_character_mutations
from sidequest.mutation.models import MutationCatalog
from sidequest.mutation.state import MutationState

logger = logging.getLogger(__name__)


def init_mutation_state_for_session(
    snapshot: GameSnapshot,
    *,
    catalog: MutationCatalog | None,
    character_name: str,
    character_class: str,
    session_id: str,
) -> None:
    if catalog is None:
        return  # pack has no mutation system — deliberate authoring choice
    if snapshot.mutation_state is None:
        snapshot.mutation_state = MutationState()
    seeded = seed_character_mutations(
        snapshot.mutation_state,
        catalog,
        actor=character_name,
        character_class=character_class,
        session_id=session_id,
    )
    if seeded is not None:
        logger.info(
            "mutation_init: seeded %r (class=%s) mp=%d negatives=%s",
            character_name, character_class, seeded.mp_remaining, seeded.negative_ids,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/mutation/test_mutation_init.py -v`
Expected: all PASS. If `GameSnapshot.model_construct(...)` is too loose for the assertions, find the lightest real `GameSnapshot` fixture: `grep -rn "GameSnapshot(" tests/server/ | head` and reuse that construction in `_snapshot()`.

- [ ] **Step 6: Wire chargen call sites**

In `sidequest/server/websocket_handlers/chargen_mixin.py`, locate BOTH `init_magic_state_for_session(` call sites (lines ~895 and ~1117). Immediately after each, add the peer call, sourcing the arguments from the variables already in scope at that site (the same handler already has the genre pack, the character name/class, and the session id for the magic call — reuse them):

```python
            init_mutation_state_for_session(
                snapshot,
                catalog=genre_pack.mutations if genre_pack is not None else None,
                character_name=character_name,
                character_class=character_class,
                session_id=session_id,
            )
```

Match the actual local variable names at each site (read the surrounding magic-init call for what the snapshot/pack/name/class/session variables are called there — they differ slightly between the two branches). Import at the top of the file:

```python
from sidequest.server.mutation_init import init_mutation_state_for_session
```

- [ ] **Step 7: Run the chargen handler suite**

Run: `uv run pytest tests/server/ -k "chargen" -v`
Expected: PASS (existing chargen tests exercise the call sites; the no-catalog path is a no-op for every existing pack fixture).

- [ ] **Step 8: Commit**

```bash
git add sidequest/game/session.py sidequest/server/mutation_init.py \
        sidequest/server/websocket_handlers/chargen_mixin.py tests/mutation/test_mutation_init.py
git commit -m "feat(mutation): snapshot state + per-session init at chargen confirmation"
```

---

### Task 11: `use_mutation` narrator tool

**Files:**
- Create: `sidequest/agents/tools/use_mutation.py`
- Modify: `sidequest/agents/tools/__init__.py` (barrel import)
- Test: `tests/agents/test_use_mutation_tool.py`

- [ ] **Step 1: Find the existing tool-test harness**

Run: `grep -rln "adjust_system_strain" sidequest-server/tests/ 2>/dev/null || grep -rln "adjust_system_strain" tests/`
Read the test file it finds. It shows how to build a fake/real `ToolContext` (repository, genre_pack, otel_span) for tool tests. Mirror that harness exactly in the next step — same fixtures, same invocation style.

- [ ] **Step 2: Write the failing tests**

Create `tests/agents/test_use_mutation_tool.py` with the harness from Step 1 and these cases (adapt the context/fixture construction to the harness; keep the assertions):

```python
# Cases to cover (assertions are the contract; harness comes from the
# adjust_system_strain test file found in Step 1):
#
# 1. test_refuses_non_cwn_family_pack:
#    pack with ruleset "native" -> ValueError mentioning "CWN-family"
#
# 2. test_not_found_for_unknown_actor:
#    awn pack, snapshot without the actor -> ToolResult status NOT_FOUND
#
# 3. test_happy_path_applies_strain_and_returns_result:
#    awn pack + snapshot with a Mutant actor owning a strain-costed mutation
#    -> result ok; payload["applied"] is True; the actor's
#    core.system_strain.current increased by the mutation's strain_cost;
#    repository.save was called
#
# 4. test_refusal_payload_round_trips:
#    exhausted per-scene usage -> result ok BUT payload["applied"] False and
#    payload["reason"] contains "limit_exhausted" (refusal is DATA for the
#    narrator, not an exception)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_use_mutation_tool.py -v`
Expected: FAIL with `ModuleNotFoundError` (tool module missing)

- [ ] **Step 4: Write the tool**

Create `sidequest/agents/tools/use_mutation.py`:

```python
"""Tool: use_mutation — the PRODUCTION CALLER for AWN mutation use.

Thin wrapper: all rules (ownership, usage limits, Strain, save-vs) live
in sidequest.mutation.use_ops. Mirrors adjust_system_strain's shape —
capability-gated on the module type, never a slug string."""

from __future__ import annotations

from pydantic import BaseModel, Field

from sidequest.agents.tool_registry import (
    ToolCategory,
    ToolContext,
    ToolResult,
    tool,
)
from sidequest.game.ruleset import get_ruleset_module
from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.mutation.use_ops import use_mutation as resolve_use_mutation


class UseMutationArgs(BaseModel):
    actor: str = Field(..., min_length=1, description="PC/NPC using the mutation.")
    mutation_id: str = Field(
        ..., min_length=1,
        description="Catalog id, e.g. 'structure/crushing_jaws'.",
    )
    target: str = Field(
        default="",
        description="Target name for save-vs mutations; empty for self/passive use.",
    )


@tool(
    name="use_mutation",
    description=(
        "Resolve an AWN mutation use mechanically: checks ownership and "
        "per-scene/per-day limits, pays the System Strain cost (refused if "
        "over max), and resolves the target save where the mutation has one. "
        "Returns applied=False with a reason on any refusal so the narrator "
        "describes the limit instead of improvising past it."
    ),
    category=ToolCategory.WRITE,
    ruleset="awn",
)
async def use_mutation(args: UseMutationArgs, ctx: ToolContext) -> ToolResult:
    session = ctx.repository.load()
    if session is None:
        return ToolResult.error("no active session", recoverable=False)

    pack = ctx.genre_pack
    module = (
        get_ruleset_module(pack.rules.ruleset)
        if pack is not None and pack.rules is not None
        else None
    )
    if not isinstance(module, CwnRulesetModule):
        ruleset = getattr(getattr(pack, "rules", None), "ruleset", None)
        raise ValueError(
            f"use_mutation requires a CWN-family ruleset (awn); "
            f"loaded pack has ruleset={ruleset!r}"
        )
    if pack.mutations is None:
        raise ValueError(
            "use_mutation called but the loaded pack has no mutations.yaml catalog"
        )

    snapshot = session.snapshot
    core = snapshot.find_creature_core(args.actor)
    if core is None:
        return ToolResult.not_found(f"unknown actor: {args.actor!r}")
    if snapshot.mutation_state is None:
        return ToolResult.not_found(
            f"no mutation state on this session; was {args.actor!r} seeded at chargen?"
        )

    cfg = pack.rules.ruleset_config()

    def _save_resolver(stat: str, target: str) -> str:
        # v1: the narrator narrates the target's save from the returned
        # save_stat; mechanical opposed-save wiring rides the dice protocol
        # in the next plan. Returning "fail" applies the full effect.
        return "fail"

    result = resolve_use_mutation(
        state=snapshot.mutation_state,
        catalog=pack.mutations,
        module=module,
        cfg=cfg,
        core=core,
        actor=args.actor,
        mutation_id=args.mutation_id,
        target_id=args.target,
        save_resolver=_save_resolver,
    )

    ctx.repository.save(snapshot)

    ctx.otel_span.set_attribute("tool.mutation.actor", args.actor)
    ctx.otel_span.set_attribute("tool.mutation.id", args.mutation_id)
    ctx.otel_span.set_attribute("tool.mutation.applied", result.applied)
    ctx.otel_span.set_attribute("tool.mutation.reason", result.reason)

    return ToolResult.ok(result.model_dump())
```

- [ ] **Step 5: Register in the barrel**

In `sidequest/agents/tools/__init__.py`, add `use_mutation` to the existing import list (alphabetical, alongside `adjust_system_strain`):

```python
    use_mutation,  # noqa: F401
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/agents/test_use_mutation_tool.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add sidequest/agents/tools/use_mutation.py sidequest/agents/tools/__init__.py \
        tests/agents/test_use_mutation_tool.py
git commit -m "feat(tools): use_mutation — production caller for AWN mutation resolution"
```

---

### Task 12: Wiring test (the lie detector)

**Files:**
- Create: `tests/integration/test_mutation_wiring.py`

- [ ] **Step 1: Write the wiring test**

The mandatory integration proof (server CLAUDE.md "Every Test Suite Needs a Wiring Test" + "assert spans, not source text"). Use the span-capture fixture the existing OTEL tests use — find it: `grep -rn "cwn.system_strain.delta" tests/ | head -3` and reuse that file's tracer/span-capture harness. The test:

```python
# tests/integration/test_mutation_wiring.py
#
# Proves end-to-end: a synthetic awn pack with a mutations catalog,
# chargen-init seeds a Mutant, the use_mutation TOOL (resolved through the
# default tool Registry — not called as a bare function) pays Strain, and
# BOTH the awn.mutation.used and cwn.system_strain.delta spans fire.
#
# Skeleton (adapt harness imports to the span-capture fixture found above):
#
# 1. Build a synthetic awn GenrePack fixture: copy the awn pack fixture from
#    tests/genre/test_mutant_wasteland_awn_binding.py and attach
#    `mutations=<the Task 6 synthetic catalog>` to it.
# 2. Build a snapshot with one character ("Rux", class Mutant) whose core has
#    a SystemStrainPool (max 10).
# 3. Call init_mutation_state_for_session(...) — assert mutation_state seeded.
# 4. Resolve the tool from the default registry by name:
#        from sidequest.agents.tool_registry import default_registry
#        handler = default_registry — look up "use_mutation" the way the
#        registry's own tests do (grep "default_registry" tests/agents/).
#    Asserting registry resolution IS the barrel-import wiring check.
# 5. Invoke it with a strain-costed mutation owned by Rux.
# 6. Assert: payload applied=True; core.system_strain.current == strain_cost;
#    captured span names include "awn.mutation.used" AND
#    "cwn.system_strain.delta".
```

Write the real test from this skeleton — every `grep` above lands on an existing harness to reuse; no new infrastructure.

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/integration/test_mutation_wiring.py -v`
Expected: PASS. **Note:** if OTEL span-count assertions deadlock under parallel xdist (known issue), run this file serially: `uv run pytest tests/integration/test_mutation_wiring.py -n0 -v`.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_mutation_wiring.py
git commit -m "test(mutation): end-to-end wiring test — registry tool to strain pool to spans"
```

---

### Task 13: Gate — lint, format, full suite

- [ ] **Step 1: Lint + format**

Run: `uv run ruff format . && uv run ruff check .`
Expected: clean (fix anything it flags).

- [ ] **Step 2: Type check**

Run: `uv run pyright sidequest/mutation/ sidequest/server/mutation_init.py sidequest/agents/tools/use_mutation.py sidequest/telemetry/spans/awn.py`
Expected: 0 errors in the new modules.

- [ ] **Step 3: Full suite**

Run: `uv run pytest`
Expected: green, modulo the documented pre-existing failures (OTEL span-count deadlocks under xdist — re-run affected files with `-n0`; the stale `test_message_type_complete_count` 54-vs-55 failure on develop is pre-existing and unrelated — do not "fix" it in this PR).

- [ ] **Step 4: Final commit + PR**

```bash
git add -A && git commit -m "chore(mutation): lint/format pass for AWN Plan 2 engine" --allow-empty
```

PR targets `develop` in `sidequest-server`. Title: `feat: AWN Plan 2 — mutation engine (MP economy, use ops, spans, use_mutation tool)`. Body must list the two spec deviations from the plan header and link the spec path.

---

## Self-Review (completed at authoring)

- **Spec coverage:** §5.1 package layout → Tasks 1–8 (context_builder deferred, declared out of scope); §5.2 seams → Task 7 (strain), Task 7 (save shape), Task 11 (capability gate), Task 2 (rolls); §5.3 tool → Task 11; §5.5 chargen → Tasks 8/10; §5.6 spans → Task 5; §6.2 ID contract → Task 1 validators. Out-of-scope items (context block, beat marker, Story C content) declared in header.
- **Placeholder scan:** Tasks 11 (step 2) and 12 (step 1) intentionally direct the engineer to an existing harness located by a specific grep, with the full assertion contract spelled out — the harness exists in-repo and the contract is complete; everything else is full code.
- **Type consistency:** `MutationState.characters: dict[str, CharacterMutationState]` used in Tasks 3/6/7/8/10; `AcquireResult.applied/reason` mirrors `StrainResult`; `use_mutation(*, state, catalog, module, cfg, core, actor, mutation_id, target_id, save_resolver)` is identical between Task 7 (op) and Task 11 (tool caller); span function names in Task 5 match the imports in Tasks 6/7.
