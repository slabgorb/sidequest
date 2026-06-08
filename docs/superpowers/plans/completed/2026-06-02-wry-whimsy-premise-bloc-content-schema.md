# wry_whimsy Premise/Bloc Content Schema + Loader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the content-authored `Premise` / `Bloc` schema (per-world `premises.yaml`) and the genre-level witnessed-act vocabulary (`witnessed_acts.yaml`) to the genre pack loader, with fail-loud cross-reference validation and an Oz reference implementation that loads end-to-end — with **zero engine/runtime behavior** (that is Plan 2).

**Architecture:** New pydantic models in `genre/models/premises.py`; a genre-tier `witnessed_acts.yaml` (the act-archetype vocabulary — *mechanics-in-genre*) loaded onto `GenrePack`; a world-tier `premises.yaml` (the specific illusions and the populations that prop them — *flavor-in-world*) loaded onto `World`; a standalone fail-loud validator wired into `_load_single_world`. This is pure content-loading: models load, validate, and surface on the assembled pack. No `PremiseState`/`BlocState`, no belief flow, no UI — those are downstream plans that depend on this one.

**Tech Stack:** Python 3.12+, pydantic v2, `uv`/`pytest`, YAML genre packs. Follows ADR-120 (mechanics-in-genre / flavor-in-world), ADR-121 (layered content), and the project rules **No Silent Fallbacks** and **Every Test Suite Needs a Wiring Test**.

---

## Plan Series Context (decomposition — read before starting)

This plan implements **only the content/loader subsystem** of the spec `docs/superpowers/specs/2026-06-02-wry-whimsy-premise-belief-flow-design.md`. The spec spans multiple independent subsystems; per the writing-plans Scope Check it is split into a series. Each plan produces working, testable software on its own.

| # | Plan | Depends on | Ships when done |
|---|------|-----------|-----------------|
| **1** | **Premise/Bloc content schema + loader (THIS PLAN)** | — | Premise/Bloc/act-vocabulary YAML loads + validates on the pack; Oz reference content present; authoring test proves the content boundary. No runtime behavior. |
| 2 | Runtime engine: `PremiseState`/`BlocState` on the snapshot, `witnessed_act` dispatch subsystem (reuses ADR-113/123), belief drain + soft defiance coupling, collapse/tip thresholds, ADR-053 `BeliefFact` injection on witnessed acts, OTEL emits | 1 | A witnessed act in a live Oz session drains a Premise, raises bloc defiance, fires OTEL; integration wiring test green. |
| 3 | Confrontation integration: "Refuse the Premise" / "Expose the Humbug" social-confrontation victory **fires the same `witnessed_act` application path** (no new `VictoryMoveDef` — reuse Plan 2) | 2 | Winning the social confrontation applies a belief delta to the named Premise. |
| 4 | UI Standing panel: server `STANDING` projection (copy the `RELATIONSHIPS` projection + emit pattern), `StandingWidget` + registry tab, `useStateMirror` slice, belief-flow bars | 2 | Right-sidebar Standing tab shows dwindling belief / rising defiance with the witness named. |
| 5 | Spectacles toggle (per-world illusion render contract) — **net-new**, no existing overlay pattern. Open Q#3 = UX spike *before* this plan is written. | 2 (+ UX spike) | Clicking the green spectacles off re-renders the Emerald City as plain marble. |

**Key architectural decisions locked for this series (rationale in the spec + the 2026-06-02 codebase map):**
- **No population-belief rollup in v1.** `belief_reserve`/`defiance` are new authoritative aggregate dials (Plan 2), *not* a sum over per-NPC `BeliefState`. The fixed-pool conservation law (spec §11, Neo's spike) stays v2. This is why Plan 1 stores `belief_reserve` as a plain authored integer.
- **Act vocabulary is genre-tier; Premise/Bloc declarations are world-tier.** Answers spec open Q#2 (per-world files under a genre vocabulary) and Q#4 (one `witnessed_act` subsystem in Plan 2, not per-archetype intents).
- **Magnitudes are tuned on the per-world binding**, not on the genre archetype — keeps the archetype pure vocabulary (`mechanics-in-genre`) while letting each world tune its illusions (`flavor-in-world`).

---

## File Structure

| File | Responsibility | Plan 1 action |
|------|----------------|---------------|
| `sidequest-server/sidequest/genre/models/premises.py` | All Premise/Bloc/act pydantic models | **Create** |
| `sidequest-server/sidequest/genre/models/__init__.py` | Re-export model types | **Modify** (add exports) |
| `sidequest-server/sidequest/genre/premise_validate.py` | Fail-loud cross-reference validator | **Create** |
| `sidequest-server/sidequest/genre/models/pack.py` | `World` + `GenrePack` aggregate roots | **Modify** (add fields) |
| `sidequest-server/sidequest/genre/loader.py` | Discovers + loads YAML into models | **Modify** (genre + world load hooks) |
| `sidequest-content/genre_packs/wry_whimsy/witnessed_acts.yaml` | Genre-tier act-archetype vocabulary | **Create** |
| `sidequest-content/genre_packs/wry_whimsy/worlds/oz/premises.yaml` | Oz reference: Wizard's humbug + Munchkin/Winkie blocs | **Create** |
| `sidequest-server/tests/genre/test_premise_models.py` | Model unit tests | **Create** |
| `sidequest-server/tests/genre/test_premise_validate.py` | Validator unit tests | **Create** |
| `sidequest-server/tests/genre/test_premise_loader.py` | Loader wiring + Oz + authoring-boundary tests | **Create** |

All server commands run from `sidequest-server/` and use `uv run`. Run a single test with:
`uv run pytest tests/genre/test_premise_models.py::test_name -v`

---

### Task 1: Premise/Bloc/act-vocabulary models

**Files:**
- Create: `sidequest-server/sidequest/genre/models/premises.py`
- Test: `sidequest-server/tests/genre/test_premise_models.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/test_premise_models.py`:

```python
"""Unit tests for Premise/Bloc content models (Plan 1, Task 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
    PremisesFile,
    WitnessedActArchetype,
    WitnessedActsFile,
)


def test_witnessed_act_archetype_is_vocabulary_only():
    act = WitnessedActArchetype(id="expose_the_humbug", label="Expose the Humbug")
    assert act.id == "expose_the_humbug"
    assert act.description == ""


def test_witnessed_acts_file_holds_a_list():
    f = WitnessedActsFile(
        witnessed_acts=[WitnessedActArchetype(id="refuse_the_premise", label="Refuse the Premise")]
    )
    assert len(f.witnessed_acts) == 1


def test_premise_def_round_trips():
    p = PremiseDef(
        premise_id="the_wizards_humbug",
        authority="the_wizard",
        claim=PremiseClaim(subject="the_wizard", proposition="The Wizard is great and terrible."),
        belief_reserve=90,
        propped_by=["munchkins"],
        drained_by=[PremiseDrain(act="expose_the_humbug", belief_delta=25, cost="public, risky")],
        collapse=PremiseCollapse(threshold=20, outcome="The Wizard flees in his balloon."),
    )
    assert p.belief_reserve == 90
    assert p.drained_by[0].belief_delta == 25
    assert p.collapse.vacuum_hook == ""


def test_bloc_def_round_trips():
    b = BlocDef(
        bloc_id="munchkins",
        grants_belief_to=["the_wizards_humbug"],
        awakening_acts=[BlocAwakening(act="show_defiance_survives", defiance_delta=15)],
        tipping_threshold=70,
        tipped_outcome="The Munchkins raise a revolt.",
    )
    assert b.defiance == 0  # starts low
    assert b.awakening_acts[0].defiance_delta == 15


def test_belief_reserve_is_bounded_0_to_100():
    with pytest.raises(ValidationError):
        PremiseDef(
            premise_id="x",
            authority="y",
            claim=PremiseClaim(subject="y", proposition="z"),
            belief_reserve=101,
            collapse=PremiseCollapse(threshold=0, outcome="o"),
        )


def test_drain_delta_must_be_positive():
    with pytest.raises(ValidationError):
        PremiseDrain(act="a", belief_delta=0)


def test_extra_keys_are_forbidden():
    with pytest.raises(ValidationError):
        PremiseDef.model_validate(
            {
                "premise_id": "x",
                "authority": "y",
                "claim": {"subject": "y", "proposition": "z"},
                "collapse": {"threshold": 0, "outcome": "o"},
                "typo_field": True,
            }
        )


def test_premises_file_defaults_to_empty_lists():
    f = PremisesFile()
    assert f.premises == []
    assert f.blocs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/test_premise_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.genre.models.premises'`

- [ ] **Step 3: Write the models**

Create `sidequest-server/sidequest/genre/models/premises.py`:

```python
"""Premise / Bloc content models for the wry_whimsy political substrate.

Content-tier only (Plan 1): these models load and validate authored YAML. They
carry NO runtime behavior — the live ``belief_reserve``/``defiance`` dials,
belief flow, and thresholds are Plan 2's ``PremiseState``/``BlocState`` on the
session snapshot.

Boundary (ADR-120): the witnessed-act *vocabulary* is genre-tier mechanics
(``witnessed_acts.yaml``); the *illusions* (which authority, which population,
how much each act moves) are world-tier flavor (``premises.yaml``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WitnessedActArchetype(BaseModel):
    """Genre-tier vocabulary: a kind of witnessed act that can move belief.

    Premises bind these by ``id`` in ``drained_by``; blocs bind them in
    ``awakening_acts``. The archetype is pure vocabulary — magnitude is tuned
    per-world on the binding (mechanics-in-genre, flavor-in-world).
    """

    model_config = {"extra": "forbid"}

    id: str
    label: str
    description: str = ""


class WitnessedActsFile(BaseModel):
    """Genre-tier ``witnessed_acts.yaml`` — the act-archetype vocabulary."""

    model_config = {"extra": "forbid"}

    witnessed_acts: list[WitnessedActArchetype] = Field(default_factory=list)


class PremiseClaim(BaseModel):
    """The proposition a population must believe for the authority to hold power.

    Plan 2 expresses this as an ADR-053 ``BeliefClaim``; at content tier it is
    the ``subject`` (who/what the claim is about — typically an NPC id) plus the
    believed ``proposition`` text.
    """

    model_config = {"extra": "forbid"}

    subject: str
    proposition: str


class PremiseDrain(BaseModel):
    """A witnessed-act archetype that contradicts a premise, with its tuned cost."""

    model_config = {"extra": "forbid"}

    act: str  # references WitnessedActArchetype.id
    belief_delta: int = Field(ge=1, le=100)
    cost: str = ""  # narrator-facing flavor: turns / risk / exposure


class PremiseCollapse(BaseModel):
    """What happens when ``belief_reserve`` falls to ``threshold`` or below."""

    model_config = {"extra": "forbid"}

    threshold: int = Field(ge=0, le=100)
    outcome: str
    vacuum_hook: str = ""  # the loose thread the collapse leaves behind


class PremiseDef(BaseModel):
    """A world-tier illusion that sustains an authority's power."""

    model_config = {"extra": "forbid"}

    premise_id: str
    authority: str  # references an AuthoredNpc id in the same world
    claim: PremiseClaim
    belief_reserve: int = Field(default=100, ge=0, le=100)
    propped_by: list[str] = Field(default_factory=list)  # bloc_ids
    drained_by: list[PremiseDrain] = Field(default_factory=list)
    collapse: PremiseCollapse


class BlocAwakening(BaseModel):
    """A witnessed-act archetype that raises a bloc's defiance, with tuned magnitude."""

    model_config = {"extra": "forbid"}

    act: str  # references WitnessedActArchetype.id
    defiance_delta: int = Field(ge=1, le=100)


class BlocDef(BaseModel):
    """A world-tier population the outsider can move."""

    model_config = {"extra": "forbid"}

    bloc_id: str
    defiance: int = Field(default=0, ge=0, le=100)  # starts low
    grants_belief_to: list[str] = Field(default_factory=list)  # premise_ids
    awakening_acts: list[BlocAwakening] = Field(default_factory=list)
    tipping_threshold: int = Field(default=70, ge=0, le=100)
    tipped_outcome: str
    flavor: str = ""


class PremisesFile(BaseModel):
    """World-tier ``premises.yaml`` — a world's illusions and the blocs that prop them."""

    model_config = {"extra": "forbid"}

    premises: list[PremiseDef] = Field(default_factory=list)
    blocs: list[BlocDef] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/genre/test_premise_models.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/models/premises.py tests/genre/test_premise_models.py
git commit -m "feat(genre): add Premise/Bloc content models for wry_whimsy political substrate"
```

---

### Task 2: Export the models from the package

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/__init__.py`
- Test: `sidequest-server/tests/genre/test_premise_models.py` (add one import-surface test)

- [ ] **Step 1: Add the failing test**

Append to `sidequest-server/tests/genre/test_premise_models.py`:

```python
def test_models_are_exported_from_package_root():
    # Wiring: types must be importable from the package root like every other model.
    from sidequest.genre.models import (  # noqa: F401
        BlocDef,
        PremiseDef,
        PremisesFile,
        WitnessedActArchetype,
        WitnessedActsFile,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/test_premise_models.py::test_models_are_exported_from_package_root -v`
Expected: FAIL — `ImportError: cannot import name 'PremiseDef' from 'sidequest.genre.models'`

- [ ] **Step 3: Add the export block**

In `sidequest-server/sidequest/genre/models/__init__.py`, add this import block alongside the other `from sidequest.genre.models.* import (...)` blocks (place it after the `pack` import block, keeping alphabetical-ish grouping — exact position is not load-bearing, only that it is a top-level import in this file):

```python
from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
    PremisesFile,
    WitnessedActArchetype,
    WitnessedActsFile,
)
```

If this file maintains an `__all__` list, add each of the nine names to it. (Check the bottom of the file; if there is no `__all__`, the import block alone is sufficient — re-export works via module namespace.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/genre/test_premise_models.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/models/__init__.py tests/genre/test_premise_models.py
git commit -m "feat(genre): export Premise/Bloc models from package root"
```

---

### Task 3: Fail-loud cross-reference validator

**Files:**
- Create: `sidequest-server/sidequest/genre/premise_validate.py`
- Test: `sidequest-server/tests/genre/test_premise_validate.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/test_premise_validate.py`:

```python
"""Unit tests for the Premise/Bloc cross-reference validator (Plan 1, Task 3)."""

from __future__ import annotations

import pytest

from sidequest.genre.error import GenreValidationError
from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
)
from sidequest.genre.premise_validate import validate_premises


def _premise(**over):
    base = dict(
        premise_id="the_wizards_humbug",
        authority="the_wizard",
        claim=PremiseClaim(subject="the_wizard", proposition="The Wizard is great."),
        belief_reserve=90,
        propped_by=["munchkins"],
        drained_by=[PremiseDrain(act="expose_the_humbug", belief_delta=25)],
        collapse=PremiseCollapse(threshold=20, outcome="He flees."),
    )
    base.update(over)
    return PremiseDef(**base)


def _bloc(**over):
    base = dict(
        bloc_id="munchkins",
        grants_belief_to=["the_wizards_humbug"],
        awakening_acts=[BlocAwakening(act="show_defiance_survives", defiance_delta=15)],
        tipping_threshold=70,
        tipped_outcome="They revolt.",
    )
    base.update(over)
    return BlocDef(**base)


_NPCS = {"the_wizard"}
_ACTS = {"expose_the_humbug", "show_defiance_survives"}


def test_valid_set_passes():
    validate_premises(
        premises=[_premise()],
        blocs=[_bloc()],
        authored_npc_ids=_NPCS,
        valid_act_ids=_ACTS,
        world_slug="oz",
    )  # no raise


def test_unknown_authority_fails():
    with pytest.raises(GenreValidationError, match="authority"):
        validate_premises(
            premises=[_premise(authority="nobody")],
            blocs=[_bloc()],
            authored_npc_ids=_NPCS,
            valid_act_ids=_ACTS,
            world_slug="oz",
        )


def test_propped_by_unknown_bloc_fails():
    with pytest.raises(GenreValidationError, match="propped_by"):
        validate_premises(
            premises=[_premise(propped_by=["ghosts"])],
            blocs=[_bloc()],
            authored_npc_ids=_NPCS,
            valid_act_ids=_ACTS,
            world_slug="oz",
        )


def test_drain_act_outside_vocabulary_fails():
    with pytest.raises(GenreValidationError, match="vocabulary"):
        validate_premises(
            premises=[_premise(drained_by=[PremiseDrain(act="invent_act", belief_delta=5)])],
            blocs=[_bloc()],
            authored_npc_ids=_NPCS,
            valid_act_ids=_ACTS,
            world_slug="oz",
        )


def test_grants_belief_to_unknown_premise_fails():
    with pytest.raises(GenreValidationError, match="grants_belief_to"):
        validate_premises(
            premises=[_premise()],
            blocs=[_bloc(grants_belief_to=["no_such_premise"])],
            authored_npc_ids=_NPCS,
            valid_act_ids=_ACTS,
            world_slug="oz",
        )


def test_awakening_act_outside_vocabulary_fails():
    with pytest.raises(GenreValidationError, match="vocabulary"):
        validate_premises(
            premises=[_premise()],
            blocs=[_bloc(awakening_acts=[BlocAwakening(act="invent_act", defiance_delta=5)])],
            authored_npc_ids=_NPCS,
            valid_act_ids=_ACTS,
            world_slug="oz",
        )


def test_empty_content_is_valid():
    validate_premises(
        premises=[],
        blocs=[],
        authored_npc_ids=set(),
        valid_act_ids=set(),
        world_slug="oz",
    )  # no raise — a world with no politics is a valid authoring choice
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/test_premise_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.genre.premise_validate'`

- [ ] **Step 3: Write the validator**

Create `sidequest-server/sidequest/genre/premise_validate.py`:

```python
"""Fail-loud cross-reference validation for a world's Premise/Bloc content.

Per the project rule **No Silent Fallbacks**: a dangling reference (authority
that is not an authored NPC, a bloc/premise id that does not exist, an act
outside the genre vocabulary) raises on the first violation rather than loading
a half-wired political layer.
"""

from __future__ import annotations

from collections.abc import Collection

from sidequest.genre.error import GenreValidationError
from sidequest.genre.models.premises import BlocDef, PremiseDef


def validate_premises(
    *,
    premises: list[PremiseDef],
    blocs: list[BlocDef],
    authored_npc_ids: Collection[str],
    valid_act_ids: Collection[str],
    world_slug: str,
) -> None:
    """Validate Premise/Bloc cross-references for one world.

    Args:
        premises: The world's authored premises.
        blocs: The world's authored blocs.
        authored_npc_ids: Ids of NPCs authored in this world (premise authorities
            must resolve to one of these).
        valid_act_ids: Ids in the genre-tier witnessed-act vocabulary
            (every ``drained_by`` / ``awakening_acts`` act must be one of these).
        world_slug: World identifier, for error messages.

    Raises:
        GenreValidationError: On the first dangling reference found.
    """
    npc_ids = set(authored_npc_ids)
    act_ids = set(valid_act_ids)
    premise_ids = {p.premise_id for p in premises}
    bloc_ids = {b.bloc_id for b in blocs}

    for p in premises:
        if p.authority not in npc_ids:
            raise GenreValidationError(
                f"[{world_slug}] premise '{p.premise_id}' authority "
                f"'{p.authority}' is not an authored NPC id in this world"
            )
        for prop in p.propped_by:
            if prop not in bloc_ids:
                raise GenreValidationError(
                    f"[{world_slug}] premise '{p.premise_id}' propped_by "
                    f"'{prop}' is not a declared bloc_id"
                )
        for d in p.drained_by:
            if d.act not in act_ids:
                raise GenreValidationError(
                    f"[{world_slug}] premise '{p.premise_id}' drained_by act "
                    f"'{d.act}' is not in the genre witnessed-act vocabulary"
                )

    for b in blocs:
        for pid in b.grants_belief_to:
            if pid not in premise_ids:
                raise GenreValidationError(
                    f"[{world_slug}] bloc '{b.bloc_id}' grants_belief_to "
                    f"'{pid}' is not a declared premise_id"
                )
        for a in b.awakening_acts:
            if a.act not in act_ids:
                raise GenreValidationError(
                    f"[{world_slug}] bloc '{b.bloc_id}' awakening act "
                    f"'{a.act}' is not in the genre witnessed-act vocabulary"
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/genre/test_premise_validate.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/premise_validate.py tests/genre/test_premise_validate.py
git commit -m "feat(genre): add fail-loud Premise/Bloc cross-reference validator"
```

---

### Task 4: Add `witnessed_acts` to `GenrePack` and `premises`/`blocs` to `World`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/pack.py`

This task is model-field additions only; the loader populates them in Task 5. The loader test in Task 5 is the wiring test that proves these fields are filled from real content.

- [ ] **Step 1: Add the import**

In `sidequest-server/sidequest/genre/models/pack.py`, add to the import section (alongside the other `from sidequest.genre.models.* import` lines):

```python
from sidequest.genre.models.premises import BlocDef, PremiseDef, WitnessedActArchetype
```

- [ ] **Step 2: Add fields to `World`**

In `sidequest-server/sidequest/genre/models/pack.py`, in the `World` model, add these fields next to `scenarios` (immediately after the `scenarios: dict[str, ScenarioPack] = Field(default_factory=dict)` field and its docstring):

```python
    premises: list[PremiseDef] = Field(default_factory=list)
    """World-tier political illusions (``worlds/<slug>/premises.yaml``), spec
    2026-06-02 wry_whimsy substrate. Empty list when the world authors none — a
    valid authoring choice (a world with no humbug to topple), NOT a fallback to
    any genre default. Content-tier only in Plan 1; Plan 2 hydrates the live
    ``PremiseState`` dials from these."""
    blocs: list[BlocDef] = Field(default_factory=list)
    """World-tier populations the outsider can move (``worlds/<slug>/premises.yaml``).
    Empty list when the world authors none."""
```

- [ ] **Step 3: Add field to `GenrePack`**

In `sidequest-server/sidequest/genre/models/pack.py`, in the `GenrePack` model, add this field next to the other genre-tier list fields (e.g. after the `archetypes` field):

```python
    witnessed_acts: list[WitnessedActArchetype] = Field(default_factory=list)
    """Genre-tier witnessed-act vocabulary (``witnessed_acts.yaml``), spec
    2026-06-02. The act archetypes a world's premises/blocs bind by id. Empty
    list when the pack ships no political layer (mechanics-in-genre per ADR-120)."""
```

- [ ] **Step 4: Verify nothing broke (model still imports + existing genre tests pass)**

Run: `uv run pytest tests/genre/test_premise_models.py -v && uv run python -c "from sidequest.genre.models.pack import World, GenrePack; print('ok')"`
Expected: model tests PASS; prints `ok`

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/models/pack.py
git commit -m "feat(genre): add witnessed_acts to GenrePack and premises/blocs to World"
```

---

### Task 5: Loader — load the genre vocabulary and per-world premises, validate, surface

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py`
- Test: `sidequest-server/tests/genre/test_premise_loader.py`

This is the **wiring test** for the subsystem (project rule): it proves the new content files are loaded into the assembled pack from real disk content, and that validation runs at load time.

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-server/tests/genre/test_premise_loader.py`:

```python
"""Loader wiring + Oz reference + authoring-boundary tests (Plan 1, Task 5)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from sidequest.genre.error import GenreValidationError, GenreLoadError
from sidequest.genre.loader import load_genre_pack

# Resolve the live content repo relative to this test file.
# tests/genre/ -> sidequest-server/ -> oq-3/ -> sidequest-content/
_CONTENT = (
    Path(__file__).resolve().parents[2]
    / "sidequest-content"
    / "genre_packs"
    / "wry_whimsy"
)


@pytest.mark.skipif(not _CONTENT.exists(), reason="sidequest-content not checked out beside server")
def test_wry_whimsy_loads_witnessed_act_vocabulary():
    pack = load_genre_pack(_CONTENT)
    act_ids = {a.id for a in pack.witnessed_acts}
    assert "expose_the_humbug" in act_ids
    assert "refuse_the_premise" in act_ids


@pytest.mark.skipif(not _CONTENT.exists(), reason="sidequest-content not checked out beside server")
def test_oz_loads_the_wizards_humbug_premise_and_blocs():
    pack = load_genre_pack(_CONTENT)
    oz = pack.worlds["oz"]
    premise_ids = {p.premise_id for p in oz.premises}
    bloc_ids = {b.bloc_id for b in oz.blocs}
    assert "the_wizards_humbug" in premise_ids
    assert {"munchkins", "winkies"} <= bloc_ids
    humbug = next(p for p in oz.premises if p.premise_id == "the_wizards_humbug")
    assert humbug.authority == "the_wizard"  # resolves to oz/npcs.yaml id


def _write_minimal_world_with_premises(tmp_path: Path, premises_yaml: str) -> Path:
    """Build a tiny fixture pack with one world carrying a premises.yaml.

    Copies the real wry_whimsy pack so all mandatory genre + world files exist,
    then overwrites only the target world's premises.yaml. Proves a NEW premise
    loads with ZERO engine changes (the content boundary, spec §12).
    """
    import shutil

    dst = tmp_path / "wry_whimsy"
    shutil.copytree(_CONTENT, dst)
    (dst / "worlds" / "oz" / "premises.yaml").write_text(
        textwrap.dedent(premises_yaml), encoding="utf-8"
    )
    return dst


@pytest.mark.skipif(not _CONTENT.exists(), reason="sidequest-content not checked out beside server")
def test_authoring_a_new_premise_needs_no_engine_change(tmp_path):
    # A "stub Wonderland-style humbug" authored against the same engine, bound to
    # an existing oz NPC id + existing genre acts, loads clean.
    pack = load_genre_pack(
        _write_minimal_world_with_premises(
            tmp_path,
            """
            premises:
              - premise_id: the_painted_court
                authority: the_wizard
                claim:
                  subject: the_wizard
                  proposition: "The court's rule is real and absolute."
                belief_reserve: 80
                propped_by: [munchkins]
                drained_by:
                  - act: refuse_the_premise
                    belief_delta: 30
                    cost: "public defiance"
                collapse:
                  threshold: 15
                  outcome: "The painted court scatters like cards."
            blocs:
              - bloc_id: munchkins
                grants_belief_to: [the_painted_court]
                awakening_acts:
                  - act: show_defiance_survives
                    defiance_delta: 20
                tipping_threshold: 60
                tipped_outcome: "The little folk stop bowing."
            """,
        )
    )
    oz = pack.worlds["oz"]
    assert any(p.premise_id == "the_painted_court" for p in oz.premises)


@pytest.mark.skipif(not _CONTENT.exists(), reason="sidequest-content not checked out beside server")
def test_dangling_authority_fails_loud_at_load(tmp_path):
    with pytest.raises((GenreValidationError, GenreLoadError), match="authority"):
        load_genre_pack(
            _write_minimal_world_with_premises(
                tmp_path,
                """
                premises:
                  - premise_id: bad
                    authority: not_a_real_npc
                    claim:
                      subject: x
                      proposition: y
                    collapse:
                      threshold: 0
                      outcome: o
                blocs: []
                """,
            )
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/test_premise_loader.py -v`
Expected: FAIL — `test_wry_whimsy_loads_witnessed_act_vocabulary` fails with `AttributeError`/empty `pack.witnessed_acts`, and the Oz/authoring tests fail because `premises.yaml` does not exist yet and the loader doesn't read it. (Some failures resolve only after Task 6 adds the content; that is expected — Step 4 below re-runs after Task 6.)

- [ ] **Step 3: Wire the loader**

In `sidequest-server/sidequest/genre/loader.py`:

**(3a)** Add the import near the top with the other `from sidequest.genre.models.* import` / model imports:

```python
from sidequest.genre.models.premises import PremisesFile, WitnessedActsFile
from sidequest.genre.premise_validate import validate_premises
```

**(3b)** In `_load_single_world`, change the signature to accept the genre act-id vocabulary. Replace the existing signature:

```python
def _load_single_world(
    world_path: Path,
    genre_tropes: list[TropeDefinition],
    genre_root: Path,
    *,
    genre_theme: GenreTheme | None = None,
) -> World | None:
```

with:

```python
def _load_single_world(
    world_path: Path,
    genre_tropes: list[TropeDefinition],
    genre_root: Path,
    *,
    genre_theme: GenreTheme | None = None,
    valid_act_ids: frozenset[str] = frozenset(),
) -> World | None:
```

**(3c)** In `_load_single_world`, immediately after the world-tier scenarios load block (the lines that assign `world_scenarios = _load_subdirectories(world_path, "scenarios", _load_single_scenario)`) and **before** the `return World(` statement, insert:

```python
    # === World-tier premises.yaml — OPTIONAL (spec 2026-06-02) ===
    # The world's political illusions and the blocs that prop them. Absent file
    # → no political layer (a valid authoring choice, NOT a fallback). When
    # present, cross-references are validated fail-loud against this world's
    # authored NPCs and the genre-tier witnessed-act vocabulary.
    premises_file = _load_yaml_optional(world_path / "premises.yaml", PremisesFile)
    world_premises = list(premises_file.premises) if premises_file is not None else []
    world_blocs = list(premises_file.blocs) if premises_file is not None else []
    if premises_file is not None:
        validate_premises(
            premises=world_premises,
            blocs=world_blocs,
            authored_npc_ids={npc.id for npc in authored_npcs},
            valid_act_ids=valid_act_ids,
            world_slug=world_path.name,
        )
```

**(3d)** In the same `return World(` call, add the two new keyword arguments (next to `scenarios=world_scenarios,`):

```python
        premises=world_premises,
        blocs=world_blocs,
```

**(3e)** In `load_genre_pack`, load the genre-tier vocabulary and thread its ids into the world loader. Find the worlds-load block:

```python
    worlds_raw: dict[str, World | None] = _load_subdirectories(
        path, "worlds", lambda p: _load_single_world(p, genre_tropes, path, genre_theme=theme)
    )
```

Replace it with:

```python
    # Genre-tier witnessed-act vocabulary (spec 2026-06-02). OPTIONAL — packs
    # without a political layer omit the file. World premises/blocs validate
    # their act bindings against these ids.
    witnessed_acts_file = _load_yaml_optional(path / "witnessed_acts.yaml", WitnessedActsFile)
    genre_witnessed_acts = (
        list(witnessed_acts_file.witnessed_acts) if witnessed_acts_file is not None else []
    )
    valid_act_ids = frozenset(a.id for a in genre_witnessed_acts)

    worlds_raw: dict[str, World | None] = _load_subdirectories(
        path,
        "worlds",
        lambda p: _load_single_world(
            p, genre_tropes, path, genre_theme=theme, valid_act_ids=valid_act_ids
        ),
    )
```

**(3f)** In the `GenrePack(` construction call inside `load_genre_pack` (where `scenarios=scenarios,` etc. are passed), add:

```python
        witnessed_acts=genre_witnessed_acts,
```

- [ ] **Step 4: (Defer full pass to Task 6) — verify wiring compiles and the vocabulary-load path is reachable**

Run: `uv run python -c "import sidequest.genre.loader; print('loader imports ok')"`
Expected: prints `loader imports ok` (no import/syntax errors).

The content-dependent assertions in `test_premise_loader.py` go green after Task 6 creates the YAML. Proceed to Task 6, then return here.

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/loader.py tests/genre/test_premise_loader.py
git commit -m "feat(genre): loader reads witnessed_acts.yaml + per-world premises.yaml with fail-loud validation"
```

---

### Task 6: Author the genre vocabulary + Oz reference content

**Files:**
- Create: `sidequest-content/genre_packs/wry_whimsy/witnessed_acts.yaml`
- Create: `sidequest-content/genre_packs/wry_whimsy/worlds/oz/premises.yaml`

NPC ids referenced below are the real ids in `sidequest-content/genre_packs/wry_whimsy/worlds/oz/npcs.yaml` (`the_wizard` is "Oz, the Great and Terrible"; the Munchkin/Winkie blocs are populations, not single NPCs).

- [ ] **Step 1: Create the genre-tier act vocabulary**

Create `sidequest-content/genre_packs/wry_whimsy/witnessed_acts.yaml`:

```yaml
# Genre-tier witnessed-act vocabulary (spec 2026-06-02 wry_whimsy substrate).
# These are the KINDS of act that can move belief/defiance. Worlds bind them by
# id in worlds/<slug>/premises.yaml and tune the magnitude there
# (mechanics-in-genre, flavor-in-world; ADR-120).
witnessed_acts:
  - id: expose_the_humbug
    label: Expose the Humbug
    description: >-
      Reveal, in front of witnesses, that the authority's power is theatre — pull
      the curtain, name the trick, show the lever behind the great floating head.
  - id: refuse_the_premise
    label: Refuse the Premise
    description: >-
      Decline, publicly and without consequence, to play by the rule the authority
      claims is absolute. The refusal is the contradiction.
  - id: do_the_forbidden_and_survive
    label: Do the Forbidden and Survive
    description: >-
      Break a rule the authority says cannot be broken — and walk away unharmed,
      where everyone can see it.
  - id: show_defiance_survives
    label: Show Defiance Survives
    description: >-
      Demonstrate to a cowed population that someone defied the authority and was
      not destroyed for it — proof the fear is bigger than the threat.
  - id: organize_a_first_small_refusal
    label: Organize a First Small Refusal
    description: >-
      Help a population take one concrete, collective act of refusal together — the
      first time they move as a bloc rather than as scattered individuals.
```

- [ ] **Step 2: Create the Oz reference premises**

Create `sidequest-content/genre_packs/wry_whimsy/worlds/oz/premises.yaml`:

```yaml
# Oz reference implementation (spec 2026-06-02). The Wizard's power is a Premise:
# a humbug sustained by belief. Munchkins and Winkies are blocs that prop it and
# can be awakened. Magnitudes are tuned here, per-world.
premises:
  - premise_id: the_wizards_humbug
    authority: the_wizard
    claim:
      subject: the_wizard
      proposition: "The Wizard is great and terrible, and only he decides Oz."
    belief_reserve: 90
    propped_by: [munchkins, winkies]
    drained_by:
      - act: expose_the_humbug
        belief_delta: 35
        cost: "Must be done publicly — pulling the curtain in an empty room moves nothing."
      - act: refuse_the_premise
        belief_delta: 20
        cost: "Refuse his decree to his face, before witnesses."
      - act: do_the_forbidden_and_survive
        belief_delta: 15
        cost: "Defy a thing he forbade and be seen unharmed after."
    collapse:
      threshold: 20
      outcome: >-
        Oz the Great and Terrible is revealed as a Nebraska balloonist with no magic
        at all; he loses the city's deference and prepares his balloon to flee.
      vacuum_hook: >-
        The Emerald City has no ruler. General Jinjur's not-yet-raised Army of Revolt
        sees its moment; Glinda watches from the South.

blocs:
  - bloc_id: munchkins
    defiance: 5
    grants_belief_to: [the_wizards_humbug]
    awakening_acts:
      - act: show_defiance_survives
        defiance_delta: 20
      - act: organize_a_first_small_refusal
        defiance_delta: 25
    tipping_threshold: 70
    tipped_outcome: >-
      The Munchkins — only just freed from the Witch of the East — stop deferring to
      the Emerald City and raise their own banner.
    flavor: >-
      Newly unchained and blinking in the light; quick to follow anyone who proves the
      tyrant can be defied.

  - bloc_id: winkies
    defiance: 0
    grants_belief_to: [the_wizards_humbug]
    awakening_acts:
      - act: show_defiance_survives
        defiance_delta: 15
      - act: organize_a_first_small_refusal
        defiance_delta: 20
    tipping_threshold: 75
    tipped_outcome: >-
      The Winkies, freed of the Witch of the West, refuse to bow to a second distant
      master and rally to the Tin Woodman.
    flavor: >-
      Long enslaved, slow to trust a new voice — but immovable once they decide a
      master's authority was never real.
```

- [ ] **Step 3: Run the loader wiring test (now content exists)**

Run (from `sidequest-server/`): `uv run pytest tests/genre/test_premise_loader.py -v`
Expected: PASS (5 tests) — vocabulary loads, Oz premise/blocs load with `authority == "the_wizard"`, the authoring-boundary test loads a new premise with zero engine change, and the dangling-authority test fails loud.

- [ ] **Step 4: Run the full new-test surface + a broad genre regression to confirm no load breakage**

Run: `uv run pytest tests/genre/test_premise_models.py tests/genre/test_premise_validate.py tests/genre/test_premise_loader.py -v`
Expected: PASS (all)

Then confirm the real pack still loads cleanly through any existing whole-pack test:
Run: `uv run pytest tests/genre/ -k "load or wry or world" -v`
Expected: PASS (no regressions from the loader changes)

- [ ] **Step 5: Commit (two repos)**

The content lives in the `sidequest-content` subrepo; the code in `sidequest-server`. Commit each in its own repo. **Before committing in a subrepo, confirm you are on the intended branch and rebased on its base (`develop`) — per the dual-clone subrepo branch hazard.**

```bash
# content repo
cd sidequest-content
git add genre_packs/wry_whimsy/witnessed_acts.yaml genre_packs/wry_whimsy/worlds/oz/premises.yaml
git commit -m "content(wry_whimsy): add witnessed-act vocabulary + Oz Wizard's-humbug premise & blocs"
cd ..

# server repo — already committed in prior tasks; nothing new here unless Step 4 surfaced a fix
```

---

## Self-Review

**1. Spec coverage (Plan 1 scope only — the content/loader subsystem of the spec):**
- Spec §4.1 `Premise` (premise_id, authority, claim, belief_reserve, propped_by, drained_by, collapse) → Task 1 `PremiseDef` ✓
- Spec §4.2 `Bloc` (bloc_id, defiance, grants_belief_to, awakening_acts, tipping_threshold, tipped_outcome, flavor) → Task 1 `BlocDef` ✓
- Spec §8 Premise-as-content, genre vocabulary + per-world declarations, loader-validated → Tasks 4–6 ✓
- Spec §8 "Jade adds a humbug without touching the server" / §12 authoring test (second premise loads with zero engine changes) → Task 5 `test_authoring_a_new_premise_needs_no_engine_change` ✓
- Spec §11 "Oz as the single reference implementation" → Task 6 ✓
- **Deliberately NOT in Plan 1 (downstream plans):** §4.3 `PremiseState`/`BlocState` runtime, §4.4 soft coupling, §5 belief-flow mechanics, §6 consequences, §7 Standing panel + spectacles, §10 OTEL emits. These are Plans 2–5. Plan 1 is content + loader only.

**2. Placeholder scan:** No `TBD`/`implement later`/"add validation"-without-code. Every code step shows complete code; every run step shows the command + expected output. ✓

**3. Type consistency:**
- `PremiseDef.drained_by: list[PremiseDrain]`; `PremiseDrain.act: str` / `belief_delta: int (ge=1)` — used identically in Tasks 1, 3, 5, 6. ✓
- `BlocDef.awakening_acts: list[BlocAwakening]`; `BlocAwakening.act` / `defiance_delta` — consistent across tasks. ✓
- `validate_premises(*, premises, blocs, authored_npc_ids, valid_act_ids, world_slug)` — same signature in Task 3 (def) and Task 5 (call). The loader passes `authored_npc_ids={npc.id for npc in authored_npcs}` (matches `AuthoredNpc.id`, confirmed in loader). ✓
- `_load_single_world(..., valid_act_ids: frozenset[str] = frozenset())` — Task 5 defines the new param and the `load_genre_pack` lambda passes it. ✓
- `World.premises` / `World.blocs` (Task 4) populated by `return World(premises=..., blocs=...)` (Task 5). `GenrePack.witnessed_acts` (Task 4) populated by `GenrePack(witnessed_acts=...)` (Task 5). ✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-02-wry-whimsy-premise-bloc-content-schema.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach? (Or: shall I write Plan 2 — the runtime engine — next?)
