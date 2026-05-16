# Beneath Sünden Plan 4 — Theme Palette + Set-Piece Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the *authored content scaffold + loader + set-piece schema* for the Beneath Sünden theme palette — `sidequest/dungeon/themes.py` (strict, fail-loud `DungeonTheme`/`ThemePalette` schema + `load_theme_palette()`), `sidequest/dungeon/setpieces.py` (the set-piece *template* schema only — no roll/attach), and a minimal-but-real curated `themes/` directory in `caverns_and_claudes` exercising every interior generator class.

**Architecture:** Two new **top-level dungeon modules** (spec §8 layout): `setpieces.py` holds the set-piece *template* pydantic schema (component slots: layout/features/creatures/loot + trope/quest components); `themes.py` holds the `DungeonTheme`/`ThemePalette` schema and the `load_theme_palette(pack_dir)` strict loader. The loader is **standalone** — deliberately *not* wired into the generic `load_genre_pack` (a `themes/` dir is dungeon-specific to `beneath_sunden`; an optional generic loader would be a silent fallback that breaks the other 5 packs — CLAUDE.md No Silent Fallbacks). The runtime consumer (materializer building a depth-filtered `theme_pool`, rolling set-pieces) is Plan 7/Plan 6 — an **honest deferral identical to Plans 2 & 3's stance**, proven here by a wiring test that loads the *real shipped scaffold* and cross-validates it against the *real* Plan-1 `interiors.ALGORITHMS` and Plan-3 `depth_score` scale.

**Tech Stack:** Python 3, `pydantic` v2 (`BaseModel`, `ConfigDict(extra="forbid")`, `field_validator`, `model_validator`) mirroring `sidequest/genre/models/lethality.py`; `PyYAML` (`yaml.safe_load`) mirroring `sidequest/genre/lethality_policy_loader.py`; `pytest`. All commands via `uv run` (`python` is NOT on PATH in sidequest-server).

**Repos / branches:** Plan 4 touches **both** subrepos. Branch `feat/beneath-sunden-theme-palette` is created in **both** `sidequest-server` and `sidequest-content` off a freshly fetched+pulled `develop` (Task 0). PRs target `develop` (gitflow). oq-1/oq-2 collision awareness: fetch+pull before branching in each subrepo.

---

## §12 / scope decisions baked in here (tunable per-theme in YAML — reversible)

| Open item (spec §12) | Plan-4 decision | Where |
|---|---|---|
| `braid_ratio` defaults | labyrinth-trap theme = **0.0** (deliberately pristine perfect maze, spec §5.2); other maze themes (`depthfirst`/`prim`) = **0.3**; `cellular`/`roomcorridor` = **0.0** (not perfect mazes — braid is meaningless/inert there, `generate_interior` skips it when `<= 0.0`). Authored per-theme in YAML; schema range-validates `0.0 ≤ r ≤ 1.0`. | Tasks 3, 7 |
| `depth_score` → theme band eligibility | Bands are authored in **raw `depth_score` units** (Plan 3: `depth_per_hop=10.0`), NOT player-facing level buckets — `depth_score` is the authoritative gradient; "level" is "never an authoritative coordinate, key, or container" (spec §5). | Tasks 4, 6, 7 |
| Burst magnitude (`connection_burst`, threads-lit) | **OUT of Plan 4.** Not a per-theme field — it is a §5.1 region-graph / §7.1 ledger world-config knob (Plan 2 `JaquaysConfig` / Plan 6 ledger / Plan 7 world authoring). Not introduced here. | n/a (scope-noted) |
| Curation mechanism (LLM) | OUT — spec §12 defers it; Plan 4 ships hand-authored scaffold YAML, no curation pass. | n/a |
| Scaffold breadth | **5 themes** covering all 4 generator classes (`cellular`, `depthfirst`, `prim`, `roomcorridor`) **plus** the special braid-0.0 labyrinth-trap case. The *exhaustive* curated palette is Plan 8 (spec §10 step 8 explicitly defers "theme palette content"). Plan 4's scaffold is minimal-but-real: every theme loads, every set-piece has non-blank telegraph+outcome (spec §4). | Task 7 |

**Hard scope boundary (do NOT cross — Plan 6/7 territory):**
- No set-piece *roll*, no component instantiation, no trope `start`, no quest `seed`, no ledger. `setpieces.py` ships the **schema only**; Plan 6 extends the *same file* with roll/attach (real type now, methods later — exactly the Plan-3 `DepthReport` precedent; **not** a stub).
- No cross-resolution of `trope_id`/`quest_id`/`creature ref`/`loot ref` against `tropes.yaml`/scenario/monster-manual/`inventory.yaml`. Plan 4 validates them *structurally* (non-blank, well-formed); binding/resolution is Plan 6 attach.
- No `load_genre_pack` integration. No materializer, no OTEL spans, no session path. No new dice/combat mechanics — `save_or_die` is **inert reference data** consumed by ADR-074 at Plan-6 attach (spec §4 "No new mechanics engine").
- `encounters.rb` is reference-only — not ported (spec §6).

---

## File Structure

### sidequest-server

| File | Create/Modify | Responsibility |
|------|---------------|----------------|
| `sidequest/dungeon/setpieces.py` | Create | Set-piece **template** schema: `SlotOption`, `ComponentSlot`, `TropeComponent`, `QuestComponent`, `SaveOrDie`, `SetPiece`. Mandatory non-blank `telegraph`+`outcome` (spec §4). SCHEMA ONLY. |
| `sidequest/dungeon/themes.py` | Create | `DepthBand`, `InteriorSpec` (algorithm validated vs real `interiors.ALGORITHMS`), `NarratorFlavor`, `Adjacency`, `CreatureEntry`, `LootEntry`, `DungeonTheme`, `ThemePalette`; `ThemePaletteMissingError`; `load_theme_palette(pack_dir)`; pure helpers `theme_eligible_at_depth`. |
| `tests/dungeon/test_setpieces.py` | Create | `setpieces.py` schema unit tests. |
| `tests/dungeon/test_themes.py` | Create | `themes.py` schema + loader unit tests (synthetic `tmp_path` fixtures). |
| `tests/dungeon/test_themes_wiring.py` | Create | **Wiring test** — loads the *real shipped* `caverns_and_claudes/themes/` scaffold; cross-validates vs real `interiors.ALGORITHMS` + Plan-3 `depth_score` scale. |

### sidequest-content

| File | Create | Responsibility |
|------|--------|----------------|
| `genre_packs/caverns_and_claudes/themes/README.md` | Create | What the dir is; schema pointer; Plan-8 expansion note. |
| `genre_packs/caverns_and_claudes/themes/drowned_cavern.yaml` | Create | Organic class → `cellular`, braid `0.0`. |
| `genre_packs/caverns_and_claudes/themes/winding_catacomb.yaml` | Create | Labyrinthine → `depthfirst`, braid `0.3`. |
| `genre_packs/caverns_and_claudes/themes/labyrinth_trap.yaml` | Create | Labyrinth-trap → `depthfirst`, braid **`0.0`** (§12 deliberate). |
| `genre_packs/caverns_and_claudes/themes/bone_crypt.yaml` | Create | Structured → `prim`, braid `0.3`. |
| `genre_packs/caverns_and_claudes/themes/sunless_temple.yaml` | Create | Built → `roomcorridor`, braid `0.0`. |

> Note: `sidequest/dungeon/__init__.py` is a docstring-only package marker; `themes.py`/`setpieces.py` are imported by full module path (`from sidequest.dungeon.themes import ...`), consistent with how `region_graph`/`interiors` subpackages are consumed. No `__init__` aggregation needed.

---

## Task 0: Branch setup in BOTH subrepos

**Files:** none (git only).

- [ ] **Step 1: sidequest-server — fetch, pull, branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git fetch origin --quiet
git checkout develop
git pull --ff-only origin develop
git rev-parse --short HEAD   # expect 645171b (Plan-3 merge) or newer
git checkout -b feat/beneath-sunden-theme-palette
git branch --show-current   # expect feat/beneath-sunden-theme-palette
```

Expected: branch created off `develop` carrying Plans 1/2/3 (`sidequest.dungeon.interiors`, `region_graph`, `region_graph/depth`).

- [ ] **Step 2: sidequest-content — fetch, pull, branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git fetch origin --quiet
git checkout develop
git pull --ff-only origin develop
git rev-parse --short HEAD   # expect e4b02a0 or newer
git checkout -b feat/beneath-sunden-theme-palette
git branch --show-current   # expect feat/beneath-sunden-theme-palette
```

Expected: matching branch in the content subrepo. (No commit yet — Task 0 only establishes branches so no implementer pollutes `develop`.)

---

## Task 1: Set-piece component-slot primitives (`setpieces.py`)

**Files:**
- Create: `sidequest-server/sidequest/dungeon/setpieces.py`
- Test: `sidequest-server/tests/dungeon/test_setpieces.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/dungeon/test_setpieces.py`:

```python
"""Unit tests for sidequest.dungeon.setpieces (schema only — Plan 4)."""

import pytest
from pydantic import ValidationError

from sidequest.dungeon.setpieces import (
    ComponentSlot,
    QuestComponent,
    SlotOption,
    TropeComponent,
)


def test_slot_option_requires_positive_weight():
    o = SlotOption(value="collapsing_floor", weight=2.0)
    assert o.value == "collapsing_floor"
    assert o.weight == 2.0


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_slot_option_rejects_nonpositive_weight(bad):
    with pytest.raises(ValidationError):
        SlotOption(value="x", weight=bad)


def test_slot_option_rejects_blank_value():
    with pytest.raises(ValidationError):
        SlotOption(value="   ", weight=1.0)


def test_slot_option_default_weight_is_one():
    assert SlotOption(value="x").weight == 1.0


def test_component_slot_requires_at_least_one_option():
    with pytest.raises(ValidationError, match="at least one option"):
        ComponentSlot(name="layout", options=[])


def test_component_slot_rejects_blank_name():
    with pytest.raises(ValidationError):
        ComponentSlot(name=" ", options=[SlotOption(value="x")])


def test_trope_component_requires_nonblank_id():
    t = TropeComponent(trope_id="priest_demands_a_sacrifice", params={"victims": 1})
    assert t.trope_id == "priest_demands_a_sacrifice"
    assert t.params == {"victims": 1}
    with pytest.raises(ValidationError):
        TropeComponent(trope_id="")


def test_quest_component_requires_nonblank_id_and_defaults_empty_params():
    q = QuestComponent(quest_id="recover_the_drowned_ledger")
    assert q.quest_id == "recover_the_drowned_ledger"
    assert q.params == {}
    with pytest.raises(ValidationError):
        QuestComponent(quest_id="  ")


def test_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        SlotOption(value="x", weight=1.0, typo=True)  # type: ignore[call-arg]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_setpieces.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.setpieces'`

- [ ] **Step 3: Write minimal implementation**

Create `sidequest-server/sidequest/dungeon/setpieces.py`:

```python
"""Set-piece TEMPLATE schema (spec: Beneath Sünden §4, §6; §10 step 4).

A set-piece is a template with randomized component slots. Plan 4 ships
the SCHEMA ONLY — Plan 6 extends THIS SAME MODULE with the seeded roll +
trope/quest attach + ledger wiring (a real type now, roll/attach methods
later — identical to Plan 3's DepthReport precedent; NOT a stub).

`telegraph` + `outcome` are mandatory and non-blank: spec §4 requires
every set-piece to carry the tell a careful party can read AND a hard,
legible outcome ("the dungeon plays fair"). `save_or_die` is INERT
reference data — ADR-074's existing player-facing dice protocol consumes
it at Plan-6 attach; spec §4 forbids a new mechanics engine, so nothing
here resolves a roll.

trope/quest components are validated STRUCTURALLY only (non-blank id +
free params). Cross-resolution against tropes.yaml / scenario is Plan 6
attach (spec §6: encounters.rb is reference-only, not ported).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _nonblank(v: str) -> str:
    if not v.strip():
        raise ValueError("must be a non-blank string")
    return v


class SlotOption(BaseModel):
    """One weighted candidate for a component slot. The seeded roll that
    picks among options is Plan 6 — here `weight` is validated > 0 only."""

    model_config = ConfigDict(extra="forbid")

    value: str
    weight: float = 1.0

    @field_validator("value")
    @classmethod
    def _v_value(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("weight")
    @classmethod
    def _v_weight(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("weight must be > 0")
        return v


class ComponentSlot(BaseModel):
    """A named slot (layout|features|creatures|loot) with >=1 option."""

    model_config = ConfigDict(extra="forbid")

    name: str
    options: list[SlotOption]

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("options")
    @classmethod
    def _v_options(cls, v: list[SlotOption]) -> list[SlotOption]:
        if not v:
            raise ValueError("a component slot needs at least one option")
        return v


class TropeComponent(BaseModel):
    """Reference to a trope that Plan 6 will START at attach. Plan 4 only
    checks the id is non-blank; resolution vs tropes.yaml is Plan 6."""

    model_config = ConfigDict(extra="forbid")

    trope_id: str
    params: dict = Field(default_factory=dict)

    @field_validator("trope_id")
    @classmethod
    def _v_id(cls, v: str) -> str:
        return _nonblank(v)


class QuestComponent(BaseModel):
    """Reference to a quest that Plan 6 will SEED at attach. Structural
    validation only here (non-blank id)."""

    model_config = ConfigDict(extra="forbid")

    quest_id: str
    params: dict = Field(default_factory=dict)

    @field_validator("quest_id")
    @classmethod
    def _v_id(cls, v: str) -> str:
        return _nonblank(v)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_setpieces.py -v`
Expected: PASS (all cases green)

- [ ] **Step 5: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/setpieces.py tests/dungeon/test_setpieces.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Commit message: write to `/tmp/p4t1.txt` with a `printf` heredoc (NOT the Write tool), then `git commit -F`. Verify cleanliness ONLY via the `od -c` byte dump — a `<system-reminder>` appearing after a git tool's output is harness injection, not commit content; do NOT amend unless `od -c` shows the literal `system-reminder` byte sequence.
> Message: `feat(dungeon): set-piece component-slot schema primitives (Plan 4 Task 1)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
printf 'feat(dungeon): set-piece component-slot schema primitives (Plan 4 Task 1)\n' > /tmp/p4t1.txt
git add sidequest/dungeon/setpieces.py tests/dungeon/test_setpieces.py
git commit -F /tmp/p4t1.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

---

## Task 2: `SaveOrDie` + `SetPiece` template (`setpieces.py`)

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/setpieces.py`
- Test: `sidequest-server/tests/dungeon/test_setpieces.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/dungeon/test_setpieces.py`:

```python
from sidequest.dungeon.setpieces import SaveOrDie, SetPiece


def _minimal_setpiece(**over) -> SetPiece:
    base = dict(
        id="false_floor",
        name="The False Floor",
        telegraph="A seam of newer mortar rings hollow underfoot.",
        outcome="The slab drops; anyone on it falls onto upturned stakes.",
        depth_band={"min": 0.0, "max": 60.0},
        slots=[
            {"name": "layout", "options": [{"value": "ten_foot_pit"}]},
            {"name": "loot", "options": [{"value": "rotted_pack", "weight": 2.0}]},
        ],
        trope_components=[],
        quest_components=[],
    )
    base.update(over)
    return SetPiece.model_validate(base)


def test_setpiece_minimal_valid():
    sp = _minimal_setpiece()
    assert sp.id == "false_floor"
    assert sp.save_or_die is None
    assert sp.depth_band.min == 0.0 and sp.depth_band.max == 60.0
    assert [s.name for s in sp.slots] == ["layout", "loot"]


@pytest.mark.parametrize("field", ["telegraph", "outcome", "name"])
def test_setpiece_rejects_blank_mandatory_text(field):
    with pytest.raises(ValidationError):
        _minimal_setpiece(**{field: "   "})


def test_setpiece_save_or_die_is_inert_reference_data():
    sp = _minimal_setpiece(save_or_die={"save": "reflex", "dc": 15})
    assert isinstance(sp.save_or_die, SaveOrDie)
    assert sp.save_or_die.save == "reflex" and sp.save_or_die.dc == 15


def test_save_or_die_rejects_blank_save_and_nonpositive_dc():
    with pytest.raises(ValidationError):
        SaveOrDie(save="", dc=10)
    with pytest.raises(ValidationError):
        SaveOrDie(save="reflex", dc=0)


def test_setpiece_depth_band_inverted_rejected():
    with pytest.raises(ValidationError, match="max .* >= .* min"):
        _minimal_setpiece(depth_band={"min": 90.0, "max": 30.0})


def test_setpiece_carries_trope_and_quest_components():
    sp = _minimal_setpiece(
        trope_components=[{"trope_id": "priest_demands_a_sacrifice"}],
        quest_components=[{"quest_id": "seal_the_breach", "params": {"days": 3}}],
    )
    assert sp.trope_components[0].trope_id == "priest_demands_a_sacrifice"
    assert sp.quest_components[0].params == {"days": 3}


def test_setpiece_duplicate_slot_names_rejected():
    with pytest.raises(ValidationError, match="duplicate component slot"):
        _minimal_setpiece(
            slots=[
                {"name": "layout", "options": [{"value": "a"}]},
                {"name": "layout", "options": [{"value": "b"}]},
            ]
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_setpieces.py -k "setpiece or save_or_die" -v`
Expected: FAIL — `ImportError: cannot import name 'SaveOrDie'`

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest-server/sidequest/dungeon/setpieces.py` (and add `model_validator` to the pydantic import line — change it to `from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator`):

```python
class DepthBand(BaseModel):
    """Raw depth_score eligibility window (Plan 3 units, depth_per_hop=10).

    NOT player-facing level buckets — depth_score is the authoritative
    gradient; "level" is never an authoritative key (spec §5). `max=None`
    means unbounded-deep (eligible arbitrarily far down)."""

    model_config = ConfigDict(extra="forbid")

    min: float = 0.0
    max: float | None = None

    @field_validator("min")
    @classmethod
    def _v_min(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("depth_band.min must be >= 0")
        return v

    @model_validator(mode="after")
    def _v_band(self) -> "DepthBand":
        if self.max is not None and self.max < self.min:
            raise ValueError("depth_band.max must be >= depth_band.min")
        return self


class SaveOrDie(BaseModel):
    """INERT reference data for ADR-074's existing dice protocol — Plan 6
    feeds this to the player-facing roll. Spec §4: no new mechanics
    engine; nothing here resolves anything."""

    model_config = ConfigDict(extra="forbid")

    save: str
    dc: int

    @field_validator("save")
    @classmethod
    def _v_save(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("dc")
    @classmethod
    def _v_dc(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("dc must be > 0")
        return v


class SetPiece(BaseModel):
    """An authored, telegraphed, lethal set-piece TEMPLATE (Tomb of
    Horrors, spec §4). Plan 4 = schema; Plan 6 rolls slots / starts trope
    & quest components / writes the ledger."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    telegraph: str
    outcome: str
    depth_band: DepthBand = Field(default_factory=DepthBand)
    save_or_die: SaveOrDie | None = None
    slots: list[ComponentSlot] = Field(default_factory=list)
    trope_components: list[TropeComponent] = Field(default_factory=list)
    quest_components: list[QuestComponent] = Field(default_factory=list)

    @field_validator("id", "name", "telegraph", "outcome")
    @classmethod
    def _v_text(cls, v: str) -> str:
        return _nonblank(v)

    @model_validator(mode="after")
    def _v_unique_slots(self) -> "SetPiece":
        names = [s.name for s in self.slots]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError(f"duplicate component slot name(s): {sorted(dupes)}")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_setpieces.py -v`
Expected: PASS (Task 1 + Task 2 cases all green)

- [ ] **Step 5: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/setpieces.py tests/dungeon/test_setpieces.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Message (printf-heredoc → `/tmp/p4t2.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): SetPiece template + SaveOrDie schema (Plan 4 Task 2)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
printf 'feat(dungeon): SetPiece template + SaveOrDie schema (Plan 4 Task 2)\n' > /tmp/p4t2.txt
git add sidequest/dungeon/setpieces.py tests/dungeon/test_setpieces.py
git commit -F /tmp/p4t2.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

---

## Task 3: `InteriorSpec` — algorithm validated against the REAL Plan-1 interiors (`themes.py`)

**Files:**
- Create: `sidequest-server/sidequest/dungeon/themes.py`
- Test: `sidequest-server/tests/dungeon/test_themes.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/dungeon/test_themes.py`:

```python
"""Unit tests for sidequest.dungeon.themes (schema + loader — Plan 4)."""

import pytest
from pydantic import ValidationError

from sidequest.dungeon.interiors import ALGORITHMS
from sidequest.dungeon.themes import InteriorSpec


def test_interior_spec_accepts_every_real_algorithm():
    # WIRING: the schema validates against the REAL Plan-1 coordinator
    # registry, not a hard-coded copy.
    for algo in ALGORITHMS:
        spec = InteriorSpec(algorithm=algo, params={}, braid_ratio=0.0)
        assert spec.algorithm == algo


def test_interior_spec_rejects_unknown_algorithm():
    with pytest.raises(ValidationError, match="unknown interior algorithm"):
        InteriorSpec(algorithm="voronoi", params={}, braid_ratio=0.0)


@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0])
def test_interior_spec_braid_ratio_out_of_range_rejected(bad):
    with pytest.raises(ValidationError, match="braid_ratio"):
        InteriorSpec(algorithm="depthfirst", braid_ratio=bad)


def test_interior_spec_braid_ratio_bounds_inclusive():
    assert InteriorSpec(algorithm="depthfirst", braid_ratio=0.0).braid_ratio == 0.0
    assert InteriorSpec(algorithm="depthfirst", braid_ratio=1.0).braid_ratio == 1.0


def test_interior_spec_defaults():
    s = InteriorSpec(algorithm="cellular")
    assert s.params == {} and s.braid_ratio == 0.0


def test_interior_spec_extra_forbidden():
    with pytest.raises(ValidationError):
        InteriorSpec(algorithm="cellular", oops=1)  # type: ignore[call-arg]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.themes'`

- [ ] **Step 3: Write minimal implementation**

Create `sidequest-server/sidequest/dungeon/themes.py`:

```python
"""Theme palette schema + strict loader (spec: Beneath Sünden §5.2, §6;
§10 step 4).

The pack ships a curated `themes/` directory; each theme keys an interior
generator, declares its depth_score eligibility band (Plan 3 raw units —
NOT player-facing level buckets, spec §5), creature/loot tables, narrator
register, adjacency affinities, and a set-piece library.

Loader is STANDALONE and fail-loud (CLAUDE.md No Silent Fallbacks):
deliberately NOT wired into the generic load_genre_pack — a `themes/` dir
is dungeon-specific to beneath_sunden; an optional generic loader would
silently no-op for the other 5 packs. The runtime consumer (Plan 7's
materializer building a depth-filtered theme_pool + Plan 6's set-piece
roll) is an honest deferral, identical to Plan 2/3's stance — proven by
tests/dungeon/test_themes_wiring.py loading the REAL shipped scaffold.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sidequest.dungeon.interiors import ALGORITHMS


class InteriorSpec(BaseModel):
    """Which ported maze-maker generator fills this theme's interiors.

    `algorithm` is validated against the REAL Plan-1 coordinator registry
    (`interiors.ALGORITHMS`) — a genuine cross-module wire, not a copied
    enum. `braid_ratio` is range-checked here; `generate_interior` itself
    skips the braid post-process when it is <= 0.0 (spec §5.2: labyrinth-
    trap stays a pristine perfect maze at 0.0)."""

    model_config = ConfigDict(extra="forbid")

    algorithm: str
    params: dict = Field(default_factory=dict)
    braid_ratio: float = 0.0

    @field_validator("algorithm")
    @classmethod
    def _v_algorithm(cls, v: str) -> str:
        if v not in ALGORITHMS:
            raise ValueError(
                f"unknown interior algorithm {v!r}; "
                f"known: {sorted(ALGORITHMS)}"
            )
        return v

    @field_validator("braid_ratio")
    @classmethod
    def _v_braid(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("braid_ratio must be in [0.0, 1.0]")
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes.py -v`
Expected: PASS

- [ ] **Step 5: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/themes.py tests/dungeon/test_themes.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Message (printf-heredoc → `/tmp/p4t3.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): InteriorSpec validated vs real interiors registry (Plan 4 Task 3)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
printf 'feat(dungeon): InteriorSpec validated vs real interiors registry (Plan 4 Task 3)\n' > /tmp/p4t3.txt
git add sidequest/dungeon/themes.py tests/dungeon/test_themes.py
git commit -F /tmp/p4t3.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

---

## Task 4: `DungeonTheme` model + supporting types (`themes.py`)

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/themes.py`
- Test: `sidequest-server/tests/dungeon/test_themes.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/dungeon/test_themes.py`:

```python
from sidequest.dungeon.themes import (
    Adjacency,
    CreatureEntry,
    DepthBand,
    DungeonTheme,
    LootEntry,
    NarratorFlavor,
)


def _theme(**over) -> DungeonTheme:
    base = dict(
        id="bone_crypt",
        display_name="The Bone Crypt",
        generator_class="structured",
        interior={"algorithm": "prim", "braid_ratio": 0.3},
        depth_band={"min": 30.0, "max": 120.0},
        narrator={
            "register": "grave",
            "flavor": "Dry air, stacked femurs, dust that remembers names.",
            "motifs": ["ossuary", "silence"],
        },
        adjacency={"prefers": ["winding_catacomb"], "avoids": ["drowned_cavern"]},
        creature_table=[{"ref": "bone_drake", "weight": 1.0}],
        loot_table=[{"ref": "grave_silver", "weight": 2.0}],
        set_pieces=[
            {
                "id": "false_floor",
                "name": "The False Floor",
                "telegraph": "Newer mortar rings hollow underfoot.",
                "outcome": "The slab drops onto upturned stakes.",
                "depth_band": {"min": 30.0, "max": 120.0},
                "slots": [{"name": "layout", "options": [{"value": "ten_foot_pit"}]}],
            }
        ],
    )
    base.update(over)
    return DungeonTheme.model_validate(base)


def test_dungeon_theme_minimal_valid():
    t = _theme()
    assert t.id == "bone_crypt"
    assert t.interior.algorithm == "prim"
    assert isinstance(t.depth_band, DepthBand)
    assert t.set_pieces[0].telegraph.startswith("Newer mortar")


@pytest.mark.parametrize(
    "gen_class, algo",
    [
        ("organic", "cellular"),
        ("labyrinthine", "depthfirst"),
        ("structured", "prim"),
        ("built", "roomcorridor"),
    ],
)
def test_generator_class_must_match_algorithm_family(gen_class, algo):
    # spec §5.2 mapping table is enforced as a hard invariant
    t = _theme(generator_class=gen_class, interior={"algorithm": algo})
    assert t.generator_class == gen_class


def test_generator_class_mismatch_rejected():
    with pytest.raises(ValidationError, match="generator_class .* does not match"):
        _theme(generator_class="built", interior={"algorithm": "cellular"})


def test_adjacency_same_id_in_prefers_and_avoids_rejected():
    with pytest.raises(ValidationError, match="both prefers and avoids"):
        Adjacency(prefers=["x"], avoids=["x"])


def test_adjacency_self_in_avoids_rejected_self_in_prefers_ok():
    # "flooded clusters" (spec §6) -> a theme may prefer adjacency to itself
    Adjacency(prefers=["drowned_cavern"], avoids=[])  # validated at palette level
    with pytest.raises(ValidationError, match="cannot avoid itself"):
        # self-avoidance is only detectable with the owning id; the model
        # rejects the trivially-nonsensical empty-string form here
        Adjacency(prefers=[], avoids=[" "])


def test_narrator_flavor_requires_nonblank_register_and_flavor():
    with pytest.raises(ValidationError):
        NarratorFlavor(register=" ", flavor="x")
    with pytest.raises(ValidationError):
        NarratorFlavor(register="grave", flavor="  ")


def test_creature_and_loot_entries_require_positive_weight_and_ref():
    CreatureEntry(ref="bone_drake", weight=1.0)
    LootEntry(ref="grave_silver", weight=1.0)
    with pytest.raises(ValidationError):
        CreatureEntry(ref="", weight=1.0)
    with pytest.raises(ValidationError):
        LootEntry(ref="x", weight=0.0)


def test_theme_blank_id_rejected():
    with pytest.raises(ValidationError):
        _theme(id="  ")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes.py -k "theme or generator_class or adjacency or narrator or creature or loot" -v`
Expected: FAIL — `ImportError: cannot import name 'Adjacency'`

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest-server/sidequest/dungeon/themes.py` (add `model_validator` to the pydantic import: `from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator`; add `from sidequest.dungeon.setpieces import SetPiece` to the imports):

```python
from sidequest.dungeon.setpieces import SetPiece

# spec §5.2 — theme class -> generator family (hard invariant)
_CLASS_ALGORITHM = {
    "organic": "cellular",
    "labyrinthine": "depthfirst",
    "structured": "prim",
    "built": "roomcorridor",
}


def _nonblank(v: str) -> str:
    if not v.strip():
        raise ValueError("must be a non-blank string")
    return v


class DepthBand(BaseModel):
    """Raw depth_score eligibility window (Plan 3 units). max=None ->
    unbounded-deep. NOT player-facing level buckets (spec §5)."""

    model_config = ConfigDict(extra="forbid")

    min: float = 0.0
    max: float | None = None

    @field_validator("min")
    @classmethod
    def _v_min(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("depth_band.min must be >= 0")
        return v

    @model_validator(mode="after")
    def _v_band(self) -> "DepthBand":
        if self.max is not None and self.max < self.min:
            raise ValueError("depth_band.max must be >= depth_band.min")
        return self


class NarratorFlavor(BaseModel):
    """Register + flavor seed for Plan 7's prompt assembly. Beneath
    Sünden plays grave/lethal (spec §3) — register & flavor non-blank."""

    model_config = ConfigDict(extra="forbid")

    register: str
    flavor: str
    motifs: list[str] = Field(default_factory=list)

    @field_validator("register", "flavor")
    @classmethod
    def _v_text(cls, v: str) -> str:
        return _nonblank(v)


class Adjacency(BaseModel):
    """Theme-placement affinities (spec §6: 'tomb -> crypt deepens;
    flooded clusters'). Palette-level cross-resolution (ids must exist,
    no self-avoidance) is enforced in load_theme_palette."""

    model_config = ConfigDict(extra="forbid")

    prefers: list[str] = Field(default_factory=list)
    avoids: list[str] = Field(default_factory=list)

    @field_validator("prefers", "avoids")
    @classmethod
    def _v_nonblank_ids(cls, v: list[str]) -> list[str]:
        for item in v:
            _nonblank(item)
        return v

    @model_validator(mode="after")
    def _v_disjoint(self) -> "Adjacency":
        both = set(self.prefers) & set(self.avoids)
        if both:
            raise ValueError(
                f"theme id(s) in both prefers and avoids: {sorted(both)}"
            )
        return self


class CreatureEntry(BaseModel):
    """Weighted creature ref. Resolution vs monster manual is Plan 6."""

    model_config = ConfigDict(extra="forbid")

    ref: str
    weight: float = 1.0
    depth_band: DepthBand | None = None

    @field_validator("ref")
    @classmethod
    def _v_ref(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("weight")
    @classmethod
    def _v_weight(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("weight must be > 0")
        return v


class LootEntry(BaseModel):
    """Weighted loot ref. Resolution vs inventory.yaml is Plan 6."""

    model_config = ConfigDict(extra="forbid")

    ref: str
    weight: float = 1.0
    depth_band: DepthBand | None = None

    @field_validator("ref")
    @classmethod
    def _v_ref(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("weight")
    @classmethod
    def _v_weight(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("weight must be > 0")
        return v


class DungeonTheme(BaseModel):
    """One curated themed zone definition (spec §6)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    generator_class: str
    interior: InteriorSpec
    depth_band: DepthBand
    narrator: NarratorFlavor
    adjacency: Adjacency = Field(default_factory=Adjacency)
    creature_table: list[CreatureEntry] = Field(default_factory=list)
    loot_table: list[LootEntry] = Field(default_factory=list)
    set_pieces: list[SetPiece] = Field(default_factory=list)

    @field_validator("id", "display_name")
    @classmethod
    def _v_text(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("generator_class")
    @classmethod
    def _v_class(cls, v: str) -> str:
        if v not in _CLASS_ALGORITHM:
            raise ValueError(
                f"unknown generator_class {v!r}; "
                f"known: {sorted(_CLASS_ALGORITHM)}"
            )
        return v

    @model_validator(mode="after")
    def _v_class_matches_algorithm(self) -> "DungeonTheme":
        expected = _CLASS_ALGORITHM[self.generator_class]
        if self.interior.algorithm != expected:
            raise ValueError(
                f"generator_class {self.generator_class!r} does not match "
                f"interior.algorithm {self.interior.algorithm!r} "
                f"(spec §5.2 expects {expected!r})"
            )
        return self
```

> Note: `DepthBand` is defined here AND in `setpieces.py`. They are intentionally separate cohesive copies (one per module's concern) — Plan 4 keeps the two schema modules dependency-light and one-directional (`themes` imports `SetPiece` from `setpieces`; `setpieces` imports nothing from `themes`). Do NOT refactor into a shared module in Plan 4 (YAGNI; a shared types module is a Plan-5/6 decision if a third consumer appears). The duplication is two ~15-line value objects with identical, separately-tested invariants.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes.py -v`
Expected: PASS (Task 3 + Task 4 cases all green)

- [ ] **Step 5: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/themes.py tests/dungeon/test_themes.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Message (printf-heredoc → `/tmp/p4t4.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): DungeonTheme model + §5.2 class/algorithm invariant (Plan 4 Task 4)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
printf 'feat(dungeon): DungeonTheme model + §5.2 class/algorithm invariant (Plan 4 Task 4)\n' > /tmp/p4t4.txt
git add sidequest/dungeon/themes.py tests/dungeon/test_themes.py
git commit -F /tmp/p4t4.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

---

## Task 5: `ThemePalette` + `load_theme_palette` strict loader (`themes.py`)

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/themes.py`
- Test: `sidequest-server/tests/dungeon/test_themes.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/dungeon/test_themes.py`:

```python
import textwrap
from pathlib import Path

from sidequest.dungeon.themes import (
    ThemePalette,
    ThemePaletteMissingError,
    load_theme_palette,
)

_GOOD_A = """
id: drowned_cavern
display_name: The Drowned Cavern
generator_class: organic
interior:
  algorithm: cellular
  braid_ratio: 0.0
depth_band: {min: 0.0, max: 50.0}
narrator:
  register: grave
  flavor: Black water, no echo, the cold of deep stone.
  motifs: [flood, silence]
adjacency:
  prefers: [drowned_cavern]
  avoids: [bone_crypt]
creature_table:
  - {ref: blind_eel, weight: 1.0}
loot_table:
  - {ref: silt_pearl, weight: 1.0}
set_pieces:
  - id: siphon
    name: The Siphon
    telegraph: A steady suck of current pulls toward a black slot in the floor.
    outcome: The current takes the careless under the rock and does not give them back.
    depth_band: {min: 0.0, max: 50.0}
    save_or_die: {save: reflex, dc: 14}
    slots:
      - name: layout
        options: [{value: funnel_chamber, weight: 1.0}]
"""

_GOOD_B = """
id: bone_crypt
display_name: The Bone Crypt
generator_class: structured
interior: {algorithm: prim, braid_ratio: 0.3}
depth_band: {min: 30.0, max: 120.0}
narrator:
  register: grave
  flavor: Dust that remembers names.
  motifs: [ossuary]
adjacency:
  prefers: []
  avoids: [drowned_cavern]
set_pieces:
  - id: false_floor
    name: The False Floor
    telegraph: Newer mortar rings hollow underfoot.
    outcome: The slab drops onto upturned stakes.
"""


def _write(d: Path, name: str, body: str) -> None:
    (d / name).write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")


def test_load_palette_happy_path(tmp_path: Path):
    td = tmp_path / "themes"
    td.mkdir()
    _write(td, "drowned_cavern.yaml", _GOOD_A)
    _write(td, "bone_crypt.yaml", _GOOD_B)
    pal = load_theme_palette(tmp_path)
    assert isinstance(pal, ThemePalette)
    assert set(pal.themes) == {"drowned_cavern", "bone_crypt"}
    assert pal.get("drowned_cavern").interior.algorithm == "cellular"


def test_load_palette_missing_dir_raises(tmp_path: Path):
    with pytest.raises(ThemePaletteMissingError):
        load_theme_palette(tmp_path)


def test_load_palette_empty_dir_raises(tmp_path: Path):
    (tmp_path / "themes").mkdir()
    with pytest.raises(ValueError, match="no theme files"):
        load_theme_palette(tmp_path)


def test_load_palette_duplicate_id_raises(tmp_path: Path):
    td = tmp_path / "themes"
    td.mkdir()
    _write(td, "a.yaml", _GOOD_A)
    _write(td, "a_copy.yaml", _GOOD_A)  # same id inside
    with pytest.raises(ValueError, match="duplicate theme id"):
        load_theme_palette(tmp_path)


def test_load_palette_dangling_affinity_raises(tmp_path: Path):
    td = tmp_path / "themes"
    td.mkdir()
    _write(td, "drowned_cavern.yaml", _GOOD_A)  # avoids bone_crypt — absent
    with pytest.raises(ValueError, match="unknown theme id"):
        load_theme_palette(tmp_path)


def test_load_palette_self_avoidance_raises(tmp_path: Path):
    td = tmp_path / "themes"
    td.mkdir()
    bad = _GOOD_B.replace("avoids: [drowned_cavern]", "avoids: [bone_crypt]")
    _write(td, "bone_crypt.yaml", bad)
    with pytest.raises(ValueError, match="cannot avoid itself"):
        load_theme_palette(tmp_path)


def test_load_palette_schema_violation_is_loud(tmp_path: Path):
    td = tmp_path / "themes"
    td.mkdir()
    broken = _GOOD_A.replace("algorithm: cellular", "algorithm: voronoi")
    _write(td, "drowned_cavern.yaml", broken)
    with pytest.raises(ValueError, match="drowned_cavern.yaml"):
        load_theme_palette(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes.py -k "palette" -v`
Expected: FAIL — `ImportError: cannot import name 'ThemePalette'`

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest-server/sidequest/dungeon/themes.py` (add to the top-of-module imports: `from pathlib import Path` and `import yaml`):

```python
class ThemePaletteMissingError(FileNotFoundError):
    """Raised when a pack directory has no `themes/` directory at all —
    fail loud, never an empty-palette silent fallback (CLAUDE.md)."""

    def __init__(self, pack_dir: Path) -> None:
        self.pack_dir = pack_dir
        super().__init__(f"themes/ directory missing in {pack_dir}")


class ThemePalette(BaseModel):
    """The loaded, cross-validated curated palette, keyed by theme id."""

    model_config = ConfigDict(extra="forbid")

    themes: dict[str, DungeonTheme] = Field(default_factory=dict)

    def get(self, theme_id: str) -> DungeonTheme:
        """Fail-loud lookup — unknown id is a bug, not an empty default."""
        if theme_id not in self.themes:
            raise KeyError(
                f"no theme {theme_id!r} in palette; "
                f"have: {sorted(self.themes)}"
            )
        return self.themes[theme_id]

    def themes_for_depth(self, depth_score: float) -> list[DungeonTheme]:
        """Themes eligible at a raw depth_score (Plan 3 units), sorted by
        id for deterministic theme_pool construction. The runtime caller
        (Plan 7's materializer) is the consumer; this is the pure helper."""
        return [
            self.themes[tid]
            for tid in sorted(self.themes)
            if theme_eligible_at_depth(self.themes[tid], depth_score)
        ]


def theme_eligible_at_depth(theme: DungeonTheme, depth_score: float) -> bool:
    """True iff depth_score falls in the theme's raw depth_band
    (inclusive; max=None == unbounded-deep). Spec §5: depth_score is the
    authoritative gradient driving theme-band eligibility."""
    band = theme.depth_band
    if depth_score < band.min:
        return False
    return band.max is None or depth_score <= band.max


def load_theme_palette(pack_dir: Path) -> ThemePalette:
    """Strict loader for `<pack_dir>/themes/*.yaml`.

    Fail-loud (CLAUDE.md No Silent Fallbacks):
      - no themes/ dir            -> ThemePaletteMissingError
      - themes/ but no *.yaml     -> ValueError
      - schema violation          -> ValueError (filename in message)
      - duplicate theme id        -> ValueError
      - affinity id not in palette-> ValueError
      - self-avoidance            -> ValueError

    Standalone by design — NOT called from load_genre_pack (a themes/
    dir is dungeon-specific to beneath_sunden). Plan 7's materializer is
    the runtime caller.
    """
    themes_dir = pack_dir / "themes"
    if not themes_dir.is_dir():
        raise ThemePaletteMissingError(pack_dir)

    yaml_files = sorted(
        p for p in themes_dir.glob("*.yaml") if p.is_file()
    )
    if not yaml_files:
        raise ValueError(f"no theme files (*.yaml) in {themes_dir}")

    themes: dict[str, DungeonTheme] = {}
    for path in yaml_files:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        try:
            theme = DungeonTheme.model_validate(raw)
        except Exception as e:  # pydantic ValidationError et al.
            raise ValueError(f"{path.name}: {e}") from e
        if theme.id in themes:
            raise ValueError(
                f"duplicate theme id {theme.id!r} "
                f"(seen again in {path.name})"
            )
        themes[theme.id] = theme

    # Palette-level cross-validation: affinities must resolve, and a theme
    # cannot avoid itself (preferring itself IS valid — spec §6 'flooded
    # clusters').
    known = set(themes)
    for tid, theme in themes.items():
        for ref in (*theme.adjacency.prefers, *theme.adjacency.avoids):
            if ref not in known:
                raise ValueError(
                    f"theme {tid!r} adjacency references unknown theme id "
                    f"{ref!r}; known: {sorted(known)}"
                )
        if tid in theme.adjacency.avoids:
            raise ValueError(f"theme {tid!r} cannot avoid itself")

    return ThemePalette(themes=themes)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes.py -v`
Expected: PASS (Tasks 3–5 all green)

- [ ] **Step 5: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/themes.py tests/dungeon/test_themes.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Message (printf-heredoc → `/tmp/p4t5.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): ThemePalette + fail-loud load_theme_palette loader (Plan 4 Task 5)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
printf 'feat(dungeon): ThemePalette + fail-loud load_theme_palette loader (Plan 4 Task 5)\n' > /tmp/p4t5.txt
git add sidequest/dungeon/themes.py tests/dungeon/test_themes.py
git commit -F /tmp/p4t5.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

---

## Task 6: `theme_eligible_at_depth` / `themes_for_depth` against the Plan-3 depth_score scale

**Files:**
- Test only: `sidequest-server/tests/dungeon/test_themes.py` (append) — no new production code (helpers shipped in Task 5; this task locks the Plan-3 cross-plan contract with a focused test).

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/dungeon/test_themes.py`:

```python
from sidequest.dungeon.region_graph import DepthConfig
from sidequest.dungeon.themes import theme_eligible_at_depth


def test_eligibility_uses_raw_depth_score_not_level_buckets():
    shallow = _theme(id="s", depth_band={"min": 0.0, "max": 50.0})
    deep = _theme(id="d", depth_band={"min": 90.0, "max": None})
    # Plan 3: depth_per_hop=10 -> 3 hops == depth_score 30 (NOT "level 1")
    assert theme_eligible_at_depth(shallow, 0.0) is True
    assert theme_eligible_at_depth(shallow, 50.0) is True       # inclusive max
    assert theme_eligible_at_depth(shallow, 50.01) is False
    assert theme_eligible_at_depth(deep, 89.9) is False
    assert theme_eligible_at_depth(deep, 90.0) is True           # inclusive min
    assert theme_eligible_at_depth(deep, 100000.0) is True       # max=None


def test_themes_for_depth_is_sorted_and_filters(tmp_path: Path):
    td = tmp_path / "themes"
    td.mkdir()
    _write(td, "a.yaml", _GOOD_A)  # drowned_cavern  band 0..50
    _write(
        td,
        "b.yaml",
        _GOOD_B.replace("avoids: [drowned_cavern]", "avoids: []"),
    )  # bone_crypt band 30..120
    pal = load_theme_palette(tmp_path)
    at0 = [t.id for t in pal.themes_for_depth(0.0)]
    at40 = [t.id for t in pal.themes_for_depth(40.0)]
    at200 = [t.id for t in pal.themes_for_depth(200.0)]
    assert at0 == ["drowned_cavern"]
    assert at40 == ["bone_crypt", "drowned_cavern"]   # sorted by id
    assert at200 == []                                # nothing eligible that deep


def test_depthconfig_scale_sanity_for_authoring():
    # Documents the authoring contract: bands are RAW depth_score units.
    # 9 ordinary hops at the Plan-3 default == depth_score 90.
    cfg = DepthConfig()
    assert cfg.depth_per_hop == 10.0
    assert 9 * cfg.depth_per_hop == 90.0
```

- [ ] **Step 2: Run test to verify it fails (then passes — no prod code)**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes.py -k "eligibility or for_depth or scale_sanity" -v`
Expected: PASS immediately (helpers exist from Task 5; this task pins the Plan-3 contract). If `import DepthConfig` fails, the region_graph package is not on the branch — STOP and re-verify Task 0 branched off the Plan-3 `develop`.

> This task adds no production code by design — `theme_eligible_at_depth`/`themes_for_depth` shipped in Task 5. Its value is the **cross-plan contract lock**: depth bands are raw `depth_score` units (Plan 3), never player-facing level buckets (spec §5). Keeping it a separate task keeps the TDD log honest about *what each test proves*.

- [ ] **Step 3: Full dungeon regression + lint + typecheck**

Run: `cd sidequest-server && uv run pytest tests/dungeon/ -q && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/themes.py sidequest/dungeon/setpieces.py tests/dungeon/test_themes.py tests/dungeon/test_setpieces.py`
Expected: all green (Plan 1 interiors + Plan 2/3 region_graph + Plan 4 schema), ruff clean, pyright 0

- [ ] **Step 4: Commit**

> Message (printf-heredoc → `/tmp/p4t6.txt`, `git commit -F`, `od -c` verify):
> `test(dungeon): depth_score eligibility cross-plan contract lock (Plan 4 Task 6)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
printf 'test(dungeon): depth_score eligibility cross-plan contract lock (Plan 4 Task 6)\n' > /tmp/p4t6.txt
git add tests/dungeon/test_themes.py
git commit -F /tmp/p4t6.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

---

## Task 7: Author the real `themes/` scaffold + the wiring test

This task spans **both subrepos**: author the curated YAML in `sidequest-content` (branch `feat/beneath-sunden-theme-palette`), and add the wiring test in `sidequest-server` (same branch name) that loads the *real shipped* scaffold. TDD order: write the failing wiring test first, then author content until it is green.

**Files:**
- Create (content): `sidequest-content/genre_packs/caverns_and_claudes/themes/README.md` + 5 theme YAMLs.
- Create (server): `sidequest-server/tests/dungeon/test_themes_wiring.py`.

- [ ] **Step 1: Write the failing wiring test (server repo)**

Create `sidequest-server/tests/dungeon/test_themes_wiring.py`:

```python
"""WIRING: load the REAL shipped caverns_and_claudes themes/ scaffold and
cross-validate it against the REAL Plan-1 interiors registry + Plan-3
depth_score scale.

Per CLAUDE.md "Every Test Suite Needs a Wiring Test": Plan 4's runtime
consumer (Plan 7's materializer building a depth-filtered theme_pool,
Plan 6's set-piece roll) is an honest deferral — same stance as Plans
2 & 3. This test proves the loader is wired to real content + real
sibling modules, not unit-isolated against synthetic fixtures only.
"""

import pytest

from sidequest.dungeon.interiors import ALGORITHMS
from sidequest.dungeon.themes import ThemePalette, load_theme_palette


@pytest.fixture(scope="module")
def palette(content_dir) -> ThemePalette:
    pack = content_dir / "genre_packs" / "caverns_and_claudes"
    return load_theme_palette(pack)


def test_scaffold_loads_and_covers_every_generator_class(palette: ThemePalette):
    classes = {t.generator_class for t in palette.themes.values()}
    assert classes == {"organic", "labyrinthine", "structured", "built"}


def test_scaffold_exercises_every_real_interior_algorithm(palette: ThemePalette):
    used = {t.interior.algorithm for t in palette.themes.values()}
    assert used == set(ALGORITHMS)  # cellular, depthfirst, prim, roomcorridor


def test_labyrinth_trap_is_pristine_perfect_maze(palette: ThemePalette):
    # spec §5.2 / §12: labyrinth-trap braid_ratio == 0.0 deliberately
    lt = palette.get("labyrinth_trap")
    assert lt.interior.algorithm == "depthfirst"
    assert lt.interior.braid_ratio == 0.0


def test_other_maze_themes_are_braided(palette: ThemePalette):
    # §12: non-trap depthfirst/prim themes braid at 0.3
    for tid in ("winding_catacomb", "bone_crypt"):
        assert palette.get(tid).interior.braid_ratio == pytest.approx(0.3)


def test_every_setpiece_is_telegraphed_and_has_a_hard_outcome(
    palette: ThemePalette,
):
    # spec §4: the dungeon plays fair — every set-piece carries the tell
    # AND a hard, legible outcome (both non-blank, enforced by schema;
    # asserted here against the REAL authored content).
    seen = 0
    for theme in palette.themes.values():
        for sp in theme.set_pieces:
            assert sp.telegraph.strip()
            assert sp.outcome.strip()
            seen += 1
    assert seen >= 5  # at least one real set-piece per theme


def test_depth_bands_tile_the_scale_with_no_gap_from_the_surface(
    palette: ThemePalette,
):
    # At least one theme must be eligible at the entrance (depth_score 0)
    # and the bands must reach deep (Plan 3 raw units).
    assert palette.themes_for_depth(0.0), "no theme eligible at the surface"
    assert palette.themes_for_depth(90.0), "no theme eligible 9 hops down"


def test_adjacency_graph_is_closed(palette: ThemePalette):
    # load_theme_palette already enforces this; assert it explicitly so the
    # wiring test fails loudly if the scaffold drifts.
    known = set(palette.themes)
    for t in palette.themes.values():
        for ref in (*t.adjacency.prefers, *t.adjacency.avoids):
            assert ref in known
```

- [ ] **Step 2: Run the wiring test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes_wiring.py -v`
Expected: FAIL — `ThemePaletteMissingError: themes/ directory missing in .../caverns_and_claudes` (the scaffold does not exist yet)

- [ ] **Step 3: Author the content scaffold (content repo)**

In `sidequest-content` (on branch `feat/beneath-sunden-theme-palette` from Task 0), create the directory and files.

Create `sidequest-content/genre_packs/caverns_and_claudes/themes/README.md`:

```markdown
# Beneath Sünden — Theme Palette (scaffold)

Curated themed zone definitions for the `beneath_sunden` world. Loaded by
`sidequest.dungeon.themes.load_theme_palette` (server-native, spec §6/§8).
Schema authority: `sidequest-server/sidequest/dungeon/themes.py` +
`setpieces.py`.

**This is the Plan-4 scaffold** — one theme per interior generator class
(`cellular`/`depthfirst`/`prim`/`roomcorridor`) plus the deliberately
pristine `labyrinth_trap` (braid_ratio 0.0, spec §5.2). The *exhaustive*
curated palette + curation passes are **Plan 8** (spec §10 step 8).

- `depth_band` values are RAW `depth_score` units (Plan 3:
  `depth_per_hop = 10.0`), never player-facing "level" buckets.
- Every set-piece carries non-blank `telegraph` + `outcome` (spec §4 —
  the dungeon plays fair).
- `braid_ratio`: labyrinth-trap `0.0`; other maze themes `0.3`;
  `cellular`/`roomcorridor` `0.0` (braid is inert for non-perfect-maze
  generators).
```

Create `sidequest-content/genre_packs/caverns_and_claudes/themes/drowned_cavern.yaml`:

```yaml
id: drowned_cavern
display_name: The Drowned Cavern
generator_class: organic
interior:
  algorithm: cellular
  # Real gen_cave kwargs (verified vs interiors/cellular.py): density,
  # cutoff, passes. Plan 4 does NOT dispatch these (params is a free dict
  # until Plan 7's materializer) — correct names ship now so Plan 7 has
  # no TypeError landmine.
  params: {density: 0.45, cutoff: 5, passes: 4}
  braid_ratio: 0.0
depth_band: {min: 0.0, max: 60.0}
narrator:
  register: grave
  flavor: >-
    Black standing water that gives back no echo; the cold of stone that
    has never been warm. Footing is never certain.
  motifs: [flood, drowning, silence, cold]
adjacency:
  prefers: [drowned_cavern, winding_catacomb]
  avoids: [sunless_temple]
creature_table:
  - {ref: blind_cave_eel, weight: 2.0}
  - {ref: drowned_revenant, weight: 1.0, depth_band: {min: 30.0}}
loot_table:
  - {ref: silt_pearl, weight: 2.0}
  - {ref: waterlogged_strongbox, weight: 1.0}
set_pieces:
  - id: the_siphon
    name: The Siphon
    telegraph: >-
      A steady, patient suck of current draws toward a black slot in the
      cavern floor; loose grit slides into it and does not come back.
    outcome: >-
      Anyone who enters the pull without a fixed line is taken under the
      rock and is not returned. The line holds or it does not.
    depth_band: {min: 0.0, max: 60.0}
    save_or_die: {save: reflex, dc: 15}
    slots:
      - name: layout
        options:
          - {value: funnel_chamber, weight: 2.0}
          - {value: flooded_gallery, weight: 1.0}
      - name: loot
        options:
          - {value: drowned_porters_pack, weight: 1.0}
    trope_components:
      - trope_id: the_thing_that_followed_you_down
        params: {from_region: surface}
```

Create `sidequest-content/genre_packs/caverns_and_claudes/themes/winding_catacomb.yaml`:

```yaml
id: winding_catacomb
display_name: The Winding Catacomb
generator_class: labyrinthine
interior:
  algorithm: depthfirst
  params: {}
  braid_ratio: 0.3
depth_band: {min: 20.0, max: 110.0}
narrator:
  register: grave
  flavor: >-
    Niche after niche of the stacked anonymous dead; every turn looks like
    the last turn and none of them lead back the way you think.
  motifs: [bones, repetition, disorientation]
adjacency:
  prefers: [bone_crypt, drowned_cavern]
  avoids: []
creature_table:
  - {ref: ossuary_crawler, weight: 2.0}
  - {ref: lamp_wight, weight: 1.0, depth_band: {min: 50.0}}
loot_table:
  - {ref: grave_silver, weight: 2.0}
  - {ref: sealed_reliquary, weight: 1.0}
set_pieces:
  - id: the_counting_niche
    name: The Counting Niche
    telegraph: >-
      One niche in this row holds a skull that faces outward when every
      other faces in; the dust before it has been disturbed recently.
    outcome: >-
      Disturbing the marked niche drops the corridor's portcullis behind
      and ahead at once; the only way on is the unlit side passage.
    depth_band: {min: 20.0, max: 110.0}
    slots:
      - name: features
        options:
          - {value: dropping_portcullis_pair, weight: 1.0}
      - name: creatures
        options:
          - {value: lamp_wight_ambush, weight: 1.0}
    quest_components:
      - quest_id: find_the_unlit_way_out
        params: {pressure: high}
```

Create `sidequest-content/genre_packs/caverns_and_claudes/themes/labyrinth_trap.yaml`:

```yaml
id: labyrinth_trap
display_name: The Labyrinth
generator_class: labyrinthine
interior:
  algorithm: depthfirst
  params: {}
  braid_ratio: 0.0
depth_band: {min: 60.0, max: null}
narrator:
  register: grave
  flavor: >-
    A perfect maze, built by something that understood despair. There is
    exactly one path between any two points and it is never the one you
    want.
  motifs: [maze, despair, no_shortcut, the_long_way]
adjacency:
  prefers: [labyrinth_trap]
  avoids: [drowned_cavern]
creature_table:
  - {ref: minotaur_of_the_deep, weight: 1.0, depth_band: {min: 90.0}}
  - {ref: starved_seeker, weight: 2.0}
loot_table:
  - {ref: predecessors_journal, weight: 1.0}
set_pieces:
  - id: the_only_path
    name: The Only Path
    telegraph: >-
      Scratch-tallies on the wall climb into the hundreds and then stop
      mid-stroke. Whoever counted them did not finish.
    outcome: >-
      There is no shortcut here and the schema guarantees it: a single
      dead-true perfect maze. Rationing fails before the maze does.
    depth_band: {min: 60.0, max: null}
    slots:
      - name: layout
        options:
          - {value: dead_true_perfect_maze, weight: 1.0}
    trope_components:
      - trope_id: the_resource_clock_you_can_see
        params: {resource: light}
```

Create `sidequest-content/genre_packs/caverns_and_claudes/themes/bone_crypt.yaml`:

```yaml
id: bone_crypt
display_name: The Bone Crypt
generator_class: structured
interior:
  algorithm: prim
  params: {}
  braid_ratio: 0.3
depth_band: {min: 30.0, max: 130.0}
narrator:
  register: grave
  flavor: >-
    Dry air, stacked femurs sorted by length, dust that still remembers
    names it will not say. Someone keeps this place.
  motifs: [ossuary, order, the_keeper, dust]
adjacency:
  prefers: [winding_catacomb, sunless_temple]
  avoids: [drowned_cavern]
creature_table:
  - {ref: bone_drake, weight: 1.0, depth_band: {min: 60.0}}
  - {ref: crypt_warden, weight: 2.0}
loot_table:
  - {ref: grave_silver, weight: 2.0}
  - {ref: wardens_keyring, weight: 1.0}
set_pieces:
  - id: the_false_floor
    name: The False Floor
    telegraph: >-
      One flagstone's mortar is a shade newer than its neighbours and
      rings hollow when the pole touches it.
    outcome: >-
      Weight on the slab drops it onto upturned iron in the pit beneath.
      The pole finds it; the careless foot finds it too late.
    depth_band: {min: 30.0, max: 130.0}
    save_or_die: {save: reflex, dc: 16}
    slots:
      - name: layout
        options:
          - {value: ten_foot_spiked_pit, weight: 2.0}
          - {value: oubliette, weight: 1.0}
      - name: loot
        options:
          - {value: prior_victims_effects, weight: 1.0}
    trope_components:
      - trope_id: the_keeper_notices_the_disturbance
        params: {patience: low}
```

Create `sidequest-content/genre_packs/caverns_and_claudes/themes/sunless_temple.yaml`:

```yaml
id: sunless_temple
display_name: The Sunless Temple
generator_class: built
interior:
  algorithm: roomcorridor
  # Real gen_roomcorridor kwargs (verified vs interiors/roomcorridor.py):
  # max_rooms, room_min, room_max (NOT min_room/max_room/room_attempts).
  # gen_roomcorridor returns silent all-wall below 12x12 — Plan 7's
  # materializer must validate region dims before dispatch (carry-forward
  # gotcha); not Plan 4's concern (params undispatched here).
  params: {max_rooms: 16, room_min: 4, room_max: 9}
  braid_ratio: 0.0
depth_band: {min: 45.0, max: null}
narrator:
  register: grave
  flavor: >-
    Deliberate halls, squared and colonnaded, raised to something that
    expected to be fed. The architecture itself is a demand.
  motifs: [temple, sacrifice, the_old_demand, deliberate_stone]
adjacency:
  prefers: [bone_crypt]
  avoids: [drowned_cavern]
creature_table:
  - {ref: temple_acolyte_shade, weight: 2.0}
  - {ref: altar_horror, weight: 1.0, depth_band: {min: 80.0}}
loot_table:
  - {ref: votive_gold, weight: 2.0}
  - {ref: sacrificial_regalia, weight: 1.0}
set_pieces:
  - id: the_altar_that_waits
    name: The Altar That Waits
    telegraph: >-
      The approach is swept clean and the channels cut into the altar
      stone are dark and dry — and recently scrubbed. It is ready.
    outcome: >-
      The temple's bargain begins the moment the expansion attaches, not
      when you arrive: the demand is already counting when you walk in.
    depth_band: {min: 45.0, max: null}
    slots:
      - name: features
        options:
          - {value: blood_channel_altar, weight: 1.0}
      - name: creatures
        options:
          - {value: waking_acolytes, weight: 2.0}
          - {value: the_thing_the_temple_feeds, weight: 1.0}
    trope_components:
      - trope_id: priest_demands_a_sacrifice
        params: {countdown_expansions: 2}
    quest_components:
      - quest_id: deny_or_feed_the_altar
        params: {irreversible: true}
```

- [ ] **Step 4: Run the wiring test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/test_themes_wiring.py -v`
Expected: PASS (7 tests green — scaffold loads, all classes/algorithms covered, labyrinth_trap pristine, others braided, every set-piece telegraphed, bands tile, adjacency closed)

- [ ] **Step 5: Lint + typecheck (server)**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright tests/dungeon/test_themes_wiring.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit the content scaffold (content repo)**

> Message (printf-heredoc → `/tmp/p4t7c.txt`, `git commit -F`, `od -c` verify):
> `feat(beneath_sunden): theme palette scaffold — 5 curated themes (Plan 4 Task 7)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git branch --show-current   # MUST be feat/beneath-sunden-theme-palette (Task 0)
printf 'feat(beneath_sunden): theme palette scaffold — 5 curated themes (Plan 4 Task 7)\n' > /tmp/p4t7c.txt
git add genre_packs/caverns_and_claudes/themes/
git commit -F /tmp/p4t7c.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

- [ ] **Step 7: Commit the wiring test (server repo)**

> Message (printf-heredoc → `/tmp/p4t7s.txt`, `git commit -F`, `od -c` verify):
> `test(dungeon): wiring — load real shipped theme scaffold (Plan 4 Task 7)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git branch --show-current   # MUST be feat/beneath-sunden-theme-palette
printf 'test(dungeon): wiring — load real shipped theme scaffold (Plan 4 Task 7)\n' > /tmp/p4t7s.txt
git add tests/dungeon/test_themes_wiring.py
git commit -F /tmp/p4t7s.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

---

## Task 8: Full regression, honest-deferral docs, push both branches

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/themes.py` + `setpieces.py` (docstring deferral note only — no behavior change)

- [ ] **Step 1: Confirm the honest-deferral declaration is explicit**

Both module docstrings (written in Tasks 1 & 3) MUST state the deferral. Verify `sidequest/dungeon/themes.py` and `setpieces.py` each contain a line naming the deferred runtime consumer (Plan 6 set-piece roll / Plan 7 materializer) and the Plan-2/3 precedent. If absent, append to the module docstring (do not change code):

```text
Honest deferral (Plan 2/3 precedent): no runtime/session/OTEL consumer
in Plan 4 — the materializer (Plan 7) builds the depth-filtered
theme_pool and Plan 6 rolls set-pieces / starts trope+quest components /
writes the ledger. Proven not-a-stub by tests/dungeon/test_themes_wiring.py
loading the real shipped scaffold against the real interiors registry.
```

- [ ] **Step 2: Full dungeon suite + targeted pyright**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/dungeon/ -q
uv run ruff check sidequest/dungeon tests/dungeon
uv run pyright sidequest/dungeon/themes.py sidequest/dungeon/setpieces.py tests/dungeon/test_themes.py tests/dungeon/test_setpieces.py tests/dungeon/test_themes_wiring.py
```
Expected: all dungeon tests green (Plan 1 interiors + Plan 2/3 region_graph + Plan 4 themes/setpieces), ruff clean, **pyright 0 on production AND all three new test files** (project standard).

- [ ] **Step 3: Full server-suite regression (additive-only proof)**

Plan 4 adds two new modules + tests and **zero** edits to existing production code (no `load_genre_pack` change). Prove the whole suite is unaffected:

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest -q`
Expected: **6214 passed, 1 failed** — the single failure is the KNOWN UNRELATED PRE-EXISTING one: `tests/server/test_chargen_dispatch.py::TestSliceAWiring::test_caverns_delver_loadout_wired_into_snapshot` (`rations_day` missing from a caverns loadout — sidequest-content drift, NOT dungeon-related, predates Plan 4). Any *other* failure is a real Plan-4 regression — investigate, do not wave it through. Do NOT "fix" the chargen test in this branch (out of scope; tracked separately).

- [ ] **Step 4: Commit the docstring note (if Step 1 required an append)**

> Only if Step 1 appended text. Message (printf-heredoc → `/tmp/p4t8.txt`, `git commit -F`, `od -c` verify):
> `docs(dungeon): explicit Plan 6/7 honest-deferral note (Plan 4 Task 8)`

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
printf 'docs(dungeon): explicit Plan 6/7 honest-deferral note (Plan 4 Task 8)\n' > /tmp/p4t8.txt
git add sidequest/dungeon/themes.py sidequest/dungeon/setpieces.py
git commit -F /tmp/p4t8.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "REAL LEAK — re-author" || echo "commit clean"
```

- [ ] **Step 5: Push BOTH branches**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git push -u origin feat/beneath-sunden-theme-palette

cd /Users/slabgorb/Projects/oq-1/sidequest-content
git push -u origin feat/beneath-sunden-theme-palette
```

(Two PRs — server + content — both targeting `develop`, created as the finishing step after the final whole-implementation review. Content PR should merge first or together: the server wiring test depends on the shipped scaffold being on the sibling checkout, but in CI the test reads the working tree, not `origin` — confirm CI checks out the matching content branch, or note in the PR that the wiring test requires the content branch present. Local review runs against the working tree where both branches are checked out.)

---

## Self-Review

**1. Spec coverage**

| Spec requirement | Task |
|---|---|
| §6 curated `themes/` directory; each theme: interior algo+params(+braid_ratio), creature/loot tables, narrator flavor/register, depth_score band eligibility, adjacency affinities, set-piece library | Tasks 3,4,5,7 |
| §6 set-piece = template with randomized component slots (layout/features/creatures/loot + trope/quest components) | Tasks 1,2 |
| §6 `encounters.rb` reference-only, not ported | Scope boundary (not implemented) |
| §6 trope components instantiate/start, quest components seed AT ATTACH | OUT — Plan 6 (schema-only ref here; boundary documented) |
| §5.2 theme class → generator mapping (organic/labyrinthine/structured/built) | Task 4 (`_CLASS_ALGORITHM` hard invariant) |
| §5.2 / §12 braid_ratio: labyrinth-trap 0.0, other maze 0.3 | Tasks 3,7 (range-validated + authored + wiring-asserted) |
| §5 depth_score drives theme-band eligibility (authoritative gradient, not level buckets) | Tasks 4,6 (`DepthBand` raw units, `theme_eligible_at_depth`) |
| §4 every set-piece telegraphed + hard legible outcome | Task 2 (non-blank validators) + Task 7 (asserted vs real content) |
| §4 roll rides ADR-074, no new mechanics engine | Task 2 (`SaveOrDie` inert reference data, documented) |
| §8 `themes.py` loader + `setpieces.py` | Tasks 3-5 / 1-2 (top-level dungeon modules per §8 layout) |
| §8 standalone server-native, no daemon/CLI/IPC on runtime path | Task 5 (pure loader; not wired into load_genre_pack — rationale documented) |
| §10 step 4 "authored content scaffold + loader" | Tasks 5,7 (scaffold = Plan 4; exhaustive palette = Plan 8) |
| CLAUDE.md No Silent Fallbacks | Task 5 (missing dir/empty/dup/dangling/schema all raise) |
| CLAUDE.md No Stubbing | `setpieces.py` schema has a real consumer (themes loader) + real tests; roll/attach is Plan 6 same-file extension (DepthReport precedent) |
| CLAUDE.md Every Test Suite Needs a Wiring Test | Task 7 (`test_themes_wiring.py` loads real scaffold vs real interiors registry) |
| §12 burst magnitude | OUT (scope-noted: §5.1/§7.1 world-config knob, not per-theme) |
| Carry-forward: feat/* branches in BOTH subrepos off freshly-pulled develop | Task 0 |
| Carry-forward: commit-hygiene od -c authoritative check | Every commit step |

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Every code step has literal code; every YAML file is fully written out in Task 7. The Task 6 "no new production code" is explicit and justified (helpers shipped in Task 5; task = contract-lock test), not a placeholder.

**3. Type consistency:** `SlotOption(value, weight)`, `ComponentSlot(name, options)`, `TropeComponent(trope_id, params)`, `QuestComponent(quest_id, params)`, `SaveOrDie(save, dc)`, `SetPiece(id,name,telegraph,outcome,depth_band,save_or_die,slots,trope_components,quest_components)` consistent Tasks 1/2/7. `InteriorSpec(algorithm,params,braid_ratio)` consistent Tasks 3/4/7. `DungeonTheme` field set identical Tasks 4/5/7. `DepthBand(min,max)` identical in both modules. `load_theme_palette(pack_dir)->ThemePalette`, `theme_eligible_at_depth(theme,depth_score)->bool`, `ThemePalette.get/themes_for_depth` identical Tasks 5/6/7. `ThemePaletteMissingError` identical Tasks 5/7. `_CLASS_ALGORITHM` keys (organic/labyrinthine/structured/built) match the §5.2 table and the Task-4/Task-7 tests.

---

## Execution Handoff

Per the Beneath Sünden carry-forward: **subagent-driven** — fresh subagent per task, two-stage spec-then-quality review per task, plus a final whole-implementation review, on `feat/beneath-sunden-theme-palette` in **both** `sidequest-server` and `sidequest-content` (branched in Task 0 off freshly-pulled `develop`). Two PRs (server + content) target `develop` after the final review.

---

## Post-Implementation Corrections (as-built — CODE IS AUTHORITATIVE)

Executed 2026-05-16, subagent-driven, two-stage review per task + opus final whole-impl review. Server branch `feat/beneath-sunden-theme-palette` (off `645171b`): T1 `b767e59`, T2 `c67cd86`+`a0c6b0a`, T3 `b37bca7`, T4 `5880110`+`8febfb6`, T5 `3a7ead2`+`501065f`, T6 `2017848`, T7 `360865b`+`7640a89`, final-review `560227c`. Content branch (off `e4b02a0`): T7 `1170374`, final-review `5c7735c`. Dungeon suite **251 passed**, full server suite **6273 passed / 0 failed** (the plan-named pre-existing `test_chargen_dispatch` failure was resolved upstream independently — gone, not Plan-4-related), production+all 3 test files pyright-0, ruff clean, 0 commit-hygiene leaks (od -c authoritative, both repos). Reconcile to these if the plan is re-run:

- **Module placement (deliberate, per §8):** `themes.py` + `setpieces.py` are **top-level `sidequest/dungeon/` modules**, NOT inside `region_graph/` (unlike Plan-3's `depth.py`, which extends `RegionNode`/`RegionGraph` so it joined that package). themes/setpieces are content-schema — a distinct concern; one-directional dep: `themes` imports only `SetPiece` from `setpieces`; `setpieces` imports nothing from `themes`. The `DepthBand`/`_nonblank` duplication across the two modules is intentional cohesion (final review verified the two `DepthBand` definitions did NOT drift — byte-identical invariants).
- **Loader is STANDALONE — NOT wired into `load_genre_pack`** (a `themes/` dir is `beneath_sunden`-specific; a generic optional loader would silently no-op the other 5 packs — No Silent Fallbacks). Runtime consumer = Plan 7 materializer / Plan 6 set-piece roll. Honest deferral, Plan-2/3 precedent, proven not-a-stub by `test_themes_wiring.py` loading the real shipped scaffold against the real `interiors.ALGORITHMS` + real `region_graph.DepthConfig`.
- **`setpieces.py` is schema-only by design; Plan 6 extends the SAME module** with roll/attach/trope-start/quest-seed/ledger (real type now, methods later — `DepthReport` precedent, NOT a stub; verified: `DungeonTheme.set_pieces: list[SetPiece]` is a real consumer).
- **Plan-literal code defects corrected as-built (more faithful to spec):** T2 `DepthBand` inverted-band message uses a space before the trailing `min` (`"…>= depth_band min"`) so it satisfies the plan's own `match="max .* >= .* min"` regex (`depth_band.min`'s dot would fail it) — semantically identical. T2 review added `"id"` to the `test_setpiece_rejects_blank_mandatory_text` parametrize (the plan omitted the spec-mandated non-blank `id`). T4 `Adjacency` split into `_v_prefers`/`_v_avoids` (inline blank checks; a whitespace `avoids` entry raises a message containing "cannot avoid itself" to satisfy both relevant tests); ruff auto-fixed `UP037` (string forward-ref annotations → bare, valid under the file's `from __future__ import annotations`); all test imports consolidated top-of-file (ruff E402). T4 review added a `NarratorFlavor.motifs` blank guard (consistency with `register`/`flavor`) + renamed the misleading `test_adjacency_self_in_avoids_...` → `test_adjacency_blank_avoids_entry_rejected`. T5 review future-tensed the `themes.py` docstring's `test_themes_wiring.py` reference (present-tense at a commit where the file didn't exist yet).
- **§5.2 invariant:** `_CLASS_ALGORITHM = {organic:cellular, labyrinthine:depthfirst, structured:prim, built:roomcorridor}` enforced by `DungeonTheme` model_validator; matches the real `interiors.ALGORITHMS` and the spec §5.2 table exactly; all 5 shipped themes obey it (final-review loader probe).
- **Scaffold interior `params` use the REAL generator kwargs** (verified pre-execution against `interiors/*.py`): `drowned_cavern` cellular `{density:0.45, cutoff:5, passes:4}`; `sunless_temple` roomcorridor `{max_rooms:16, room_min:4, room_max:9}`; `winding_catacomb`/`labyrinth_trap` depthfirst `{}`; `bone_crypt` prim `{}`. Plan 4 never dispatches them (free dict until Plan 7) — correct names ship now so Plan 7 has no `TypeError` landmine. §12 braid: `labyrinth_trap` 0.0 (pristine perfect maze), `winding_catacomb`+`bone_crypt` 0.3, `drowned_cavern`+`sunless_temple` 0.0.
- **T7 wiring-test bijection assertions KEPT (not weakened) but documented as deliberate gates:** `test_scaffold_covers_exactly_the_four_generator_classes` (`classes == {4}`) and `test_scaffold_exercises_exactly_every_interior_algorithm` (`used == set(ALGORITHMS)`) are an intentional Plan-4 completeness contract (a registered generator with no authored theme is a silent dead path — No Silent Fallbacks). A reviewer flagged Plan-8 failure-locality; resolved by renaming + an in-code comment stating a future-algorithm failure here is the contract working, not an interiors regression — **Plan 8 must add a theme for any new `interiors.ALGORITHMS` entry, or consciously relax this gate.**
- **Final-review §3/§4 content fix (`5c7735c`):** two set-piece `outcome` strings shipped with fourth-wall engine vocabulary (`labyrinth_trap` "the schema guarantees it"; `sunless_temple` "the moment the expansion attaches") — a spec §3 (no genre-winking) / §4 (hard in-fiction outcome) violation the per-task reviews missed; rewritten to pure in-world grave consequences. Also: `load_theme_palette` `yaml.safe_load` moved INSIDE the `try` so malformed-YAML errors are filename-prefixed ValueErrors (was a bare parser error); `sunless_temple` carry-forward comment corrected (`gen_roomcorridor` *raises* ValueError below 5x5 — it does NOT silent-all-wall below 12x12; the real silent risk is its room-placement retry loop at valid-but-small dims).
- **`NarratorFlavor.register` shadows `ABCMeta.register` (known, ACCEPTED, deliberately NOT renamed):** spec §6-mandated field name; round-trips correctly as an instance attr. Final-review bonus finding: 3 pre-existing production models (`magic/confrontations.py`, `genre/models/narrative.py`, `orbital/models.py`) already do this — Plan 4 follows house style; renaming only this one would *create* inconsistency. **Plan 7 carry-forward:** consume `flavor.register` (instance attribute — verified correct), never `NarratorFlavor.register(...)` as an ABC call. One `UserWarning` at import; project pytest config has no `filterwarnings=["error"]`.
- **Depth-band staircase (no surface gap, generous deep overlap; raw Plan-3 units):** `drowned_cavern`[0,60], `winding_catacomb`[20,110], `bone_crypt`[30,130], `sunless_temple`[45,∞], `labyrinth_trap`[60,∞]. surface(0.0) → drowned_cavern only (deterministic flooded entry register); 60.0 is the all-five-eligible inflection — **Plan 7's materializer should weight the theme_pool, not draw uniformly, at crossover depths.**

**Plan 5+ carry-forward:** Plan 4 ships `sidequest.dungeon.themes` (`DungeonTheme`, `ThemePalette`, `InteriorSpec`, `DepthBand`, `NarratorFlavor`, `Adjacency`, `CreatureEntry`, `LootEntry`, `ThemePaletteMissingError`, `load_theme_palette`, `theme_eligible_at_depth`) + `sidequest.dungeon.setpieces` (`SetPiece`, `SlotOption`, `ComponentSlot`, `TropeComponent`, `QuestComponent`, `SaveOrDie`, `DepthBand`) — all schema+loader, no runtime consumer. The exhaustive curated palette + curation passes are **Plan 8** (spec §10 step 8). Set-piece roll / trope-start / quest-seed / ledger = **Plan 6** (extends `setpieces.py`). Materializer building the depth-filtered `theme_pool` from `ThemePalette.themes_for_depth` + OTEL spans = **Plan 7**.
