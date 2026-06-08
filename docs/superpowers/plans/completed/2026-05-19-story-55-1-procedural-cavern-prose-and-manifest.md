# Story 55-1: Procedural Cavern Description + Manifest Emit at Materialize Time

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the procedural cavern pipeline (`beneath_sunden` and any future cookbook-driven world) into Epic 54's typed location-manifest contract. Cookbook produces a deterministic `(prose, entities)` pair for every materialized region using its existing `LookDef.dressing` corpus and `SpecialRoom.telegraph` hints. The materializer persists both into a new `<world>/rooms/<id>.yaml` written alongside the ADR-096 mask, in **one single materializer rewrite** (spec §7.3 Approach C stitch). The 54-3 validator runs as a post-materialize check over the emitted YAMLs.

**Architecture:** Four concentric layers.

1. **Cookbook data model** — `RegionContentManifest` (`sidequest/game/cookbook/models.py`) gains `room_descriptions: list[GeneratedRoomDescription]`. The new `GeneratedRoomDescription` pydantic model carries `room_id`, `description: str`, and `entities: list[LocationEntity]` (the same shape 54-2 ships). Authored YAML never mutates; this is in-memory output the materializer consumes.

2. **Cookbook compose** — new `sidequest/game/cookbook/compose.py` module with one pure function `compose_room_prose(rng, look_def, special_rooms, room_id)` → `GeneratedRoomDescription`. RNG is the deterministic seeded RNG `(campaign_seed, expansion_id, room_id)`. Dressing lines selected for the room become `flavor_only` entities. `SpecialRoom.telegraph` references for any specials attached to this room become `real_object` entities with `binding.kind = location_feature` and affordances seeded from `SpecialRoom.mechanic`. `provenance="cookbook"` on every entity emitted by this path.

3. **Cookbook assembler integration** — `assemble_region(...)` in `sidequest/game/cookbook/assemble.py` calls `compose_room_prose` once per region node it knows about (v1: one region = one room — the megadungeon materializer treats each `RegionNode` as a single materialized room, per ADR-106). The resulting `GeneratedRoomDescription` list lands on `RegionContentManifest.room_descriptions`.

4. **Materializer integration** — `sidequest/dungeon/materializer.py:_stage_commit` is extended (Plan-7-aware: this is the **single rewrite** the spec calls out — no double-pass on `materializer.py`). After the existing ADR-096 mask emit and after `commit_expansion`, the materializer writes one `<world>/rooms/<region_id>.yaml` per newly-committed region carrying the cookbook-composed `description` and `entities[]`. Existing room YAMLs are never overwritten (idempotency — re-materialization of a frozen region is a no-op on the YAML, matching the freeze invariant). Validator post-check (`pf validate locations`) runs as a CI-level smoke after a fresh materialization in the test harness.

This story does NOT touch the resolver (54-6), the overlay system (54-7), the OTEL spans (54-8), or the UI (54-9). It produces the **content** those layers consume. Authored YAML for POI worlds (54-4, 54-5) is independent.

**Tech Stack:** Python 3.14, pydantic v2, pytest, the existing cookbook RNG primitives (`region_rng`), the existing materializer Plan-7 commit txn.

**Workflow:** tdd.

**Story points:** 5.

**Depends on:** 52-2 / 52-3 (Epic 52 mask emit lands first — the materializer rewrite sits at that seam), 54-2 (`LocationEntity` types), 54-3 (`pf validate locations` validator runs on the emitted YAMLs).

**Branch:** `feat/55-1-procedural-cavern-prose-and-manifest` (off `develop`; subrepo `sidequest-server`).

**Sequence (spec §7.4):** lands last in the rollout, after both Epic 52 (materializer-with-mask-emit) and Epic 54 (manifest types + validator) have settled.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/game/cookbook/models.py` | modify | Add `GeneratedRoomDescription` model; add `room_descriptions: list[GeneratedRoomDescription]` to `RegionContentManifest`. |
| `sidequest-server/sidequest/game/cookbook/compose.py` | create | `compose_room_prose(rng, *, look_def, special_rooms, room_id)` — deterministic. Returns `GeneratedRoomDescription`. |
| `sidequest-server/sidequest/game/cookbook/assemble.py` | modify | After picking specials, call `compose_room_prose` per region node; thread results onto `RegionContentManifest.room_descriptions`. |
| `sidequest-server/sidequest/game/cookbook/__init__.py` | modify | Re-export `compose_room_prose` + `GeneratedRoomDescription`. |
| `sidequest-server/sidequest/dungeon/materializer.py` | modify | New `_stage_emit_room_yamls(...)` helper called from `_stage_commit` after the mask emit + `commit_expansion`. Writes one `<world>/rooms/<region_id>.yaml` per newly-committed region. Idempotent: a YAML that exists is not overwritten (freeze invariant). |
| `sidequest-server/sidequest/dungeon/room_yaml_emit.py` | create | Pure file-system helper `write_room_yaml(world_dir, room_id, description, entities, *, overwrite=False)` — keeps the materializer slim and gives the test a direct seam. |
| `sidequest-server/tests/game/cookbook/test_compose_room_prose.py` | create | Deterministic, returns flavor_only + real_object entities, idempotent over seed, raises loudly on missing register. |
| `sidequest-server/tests/game/cookbook/test_region_content_manifest_room_descriptions.py` | create | `RegionContentManifest.room_descriptions` defaults to `[]`; pydantic round-trip; assemble_region populates it. |
| `sidequest-server/tests/dungeon/test_room_yaml_emit.py` | create | `write_room_yaml` round-trips through `room_file_loader.load_room_payload`. |
| `sidequest-server/tests/dungeon/test_materializer_room_yaml.py` | create | End-to-end wiring: materialize a fresh expansion → one `<world>/rooms/<id>.yaml` per region → re-materialization is a no-op. |
| `sidequest-server/tests/integration/test_pf_validate_locations_on_materialized.py` | create | Post-materialize, `pf validate locations` (from 54-3) reports no hard errors on the emitted YAMLs. |

---

### Task 1: Add `GeneratedRoomDescription` + `room_descriptions` to manifest

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/models.py`
- Test: `sidequest-server/tests/game/cookbook/test_region_content_manifest_room_descriptions.py`

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/game/cookbook/test_region_content_manifest_room_descriptions.py`:

```python
"""RegionContentManifest carries room_descriptions[] (Story 55-1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.game.cookbook.models import (
    GeneratedRoomDescription,
    RegionContentManifest,
)
from sidequest.protocol.models import LocationEntity


def test_manifest_defaults_room_descriptions_empty():
    manifest = RegionContentManifest(
        race="ooze",
        cr_band="shallow",
        size_budget={"wandering_rolls": 1, "special_rooms": 0, "loot_rolls": 1},
        wandering_table=[],
        loot_table=[],
        special_rooms=[],
    )
    assert manifest.room_descriptions == []


def test_manifest_accepts_room_descriptions():
    rd = GeneratedRoomDescription(
        room_id="region_42",
        description="A narrow chamber slick with damp.",
        entities=[
            LocationEntity(
                id="slick_floor",
                label="the slick floor",
                tier="flavor_only",
                provenance="cookbook",
            ),
        ],
    )
    manifest = RegionContentManifest(
        race="ooze",
        cr_band="shallow",
        size_budget={"wandering_rolls": 1, "special_rooms": 0, "loot_rolls": 1},
        wandering_table=[],
        loot_table=[],
        special_rooms=[],
        room_descriptions=[rd],
    )
    assert len(manifest.room_descriptions) == 1
    assert manifest.room_descriptions[0].room_id == "region_42"
    assert manifest.room_descriptions[0].entities[0].provenance == "cookbook"


def test_generated_room_description_rejects_empty_room_id():
    with pytest.raises(ValidationError):
        GeneratedRoomDescription(
            room_id="",
            description="anything",
            entities=[],
        )


def test_generated_room_description_extra_field_rejected():
    with pytest.raises(ValidationError):
        GeneratedRoomDescription(  # type: ignore[call-arg]
            room_id="x",
            description="x",
            entities=[],
            surprise="!",
        )
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/game/cookbook/test_region_content_manifest_room_descriptions.py -v
```
Expected: ImportError on `GeneratedRoomDescription`.

- [ ] **Step 3: Add the model + field**

In `sidequest-server/sidequest/game/cookbook/models.py`, add the import at the top (alongside existing imports):

```python
from sidequest.protocol.models import LocationEntity
```

Then add `GeneratedRoomDescription` just before `RegionContentManifest` (around line 154):

```python
class GeneratedRoomDescription(BaseModel):
    """Cookbook-composed room prose + manifest for ONE materialized region.

    Story 55-1 / ADR-109. Produced by ``compose_room_prose`` from
    ``LookDef.dressing`` lines and any attached ``SpecialRoom.telegraph``
    references. All entities carry ``provenance="cookbook"``. Authored
    YAML never produces this shape — the materializer writes the
    resulting YAML and authored content for POI worlds is independent.
    """

    model_config = _FORBID

    room_id: str = Field(min_length=1)
    description: str
    entities: list[LocationEntity] = Field(default_factory=list)
```

(`Field` is already imported via the file's existing pydantic imports — verify with `grep -n "from pydantic" sidequest-server/sidequest/game/cookbook/models.py | head -2` and add it to the existing import list if missing.)

Then add the field to `RegionContentManifest`:

```python
class RegionContentManifest(BaseModel):
    """The deterministic contract output oq-1's materializer consumes.

    Carries cr_band + raw corpus rows. CR→Edge translation is the
    oq-1 materializer seam (ADR-014/078) — NOT done here.

    Story 55-1 / ADR-109: ``room_descriptions`` carries the
    cookbook-composed (prose, entities[]) tuple for each region the
    materializer will write to ``<world>/rooms/<id>.yaml``.
    """

    model_config = _FORBID
    race: str
    cr_band: str
    size_budget: dict[str, int]
    wandering_table: list[dict]
    loot_table: list[dict]
    special_rooms: list[dict]
    big_bad: dict | None = None
    # Story 55-1 / ADR-109: cookbook-composed per-region prose + manifest.
    # Empty list for legacy callers that don't supply room_descriptions
    # at construction time (e.g. existing tests that build a manifest by
    # hand); assemble_region populates this once the new compose path is
    # wired (Task 3).
    room_descriptions: list[GeneratedRoomDescription] = Field(default_factory=list)
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/cookbook/test_region_content_manifest_room_descriptions.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Confirm no regression in the cookbook suite**

```bash
cd sidequest-server && uv run pytest tests/game/cookbook/ -v
```
Expected: green. Existing tests build `RegionContentManifest` with the old field set; the new field is optional + defaults to `[]`.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/cookbook/models.py \
        sidequest-server/tests/game/cookbook/test_region_content_manifest_room_descriptions.py
git commit -m "feat(55-1): GeneratedRoomDescription + RegionContentManifest.room_descriptions

Cookbook contract gains a per-room (prose, entities[]) carrier.
Defaults to empty list so existing manifest construction sites
remain valid; assemble_region populates it after the compose path
lands. ADR-109 §5.2 / §4.2."
```

---

### Task 2: `compose_room_prose` — deterministic per-room composition

**Files:**
- Create: `sidequest-server/sidequest/game/cookbook/compose.py`
- Test: `sidequest-server/tests/game/cookbook/test_compose_room_prose.py`

- [ ] **Step 1: Read the existing RNG + dressing patterns**

Read `sidequest-server/sidequest/game/cookbook/assemble.py` lines 220–294 (already explored upstream — `region_rng(campaign_seed, expansion_id)` is the entry point). Also skim `sidequest-server/sidequest/game/cookbook/models.py` lines 86–95 (LookDef) and lines 130–138 (SpecialRoom). The compose function consumes:

- `rng` — must be a stable `random.Random` keyed off `(campaign_seed, expansion_id, room_id)` so two materializations of the same region produce identical prose + manifest.
- `look_def: LookDef` — provides `dressing: list[str]` and `register: str`.
- `special_rooms: list[SpecialRoom]` — the specials attached to *this* region (the materializer passes the per-region subset, not the full bundle list).
- `room_id: str` — the region/room id (used for the entity-id derivation, never for prose text).

- [ ] **Step 2: Write failing tests**

Create `sidequest-server/tests/game/cookbook/test_compose_room_prose.py`:

```python
"""compose_room_prose — deterministic per-room composition (Story 55-1)."""

from __future__ import annotations

import random

import pytest

from sidequest.game.cookbook.compose import compose_room_prose
from sidequest.game.cookbook.models import LookDef, SpecialRoom
from sidequest.protocol.models import LocationEntity


def _look(*, dressing: list[str]) -> LookDef:
    return LookDef(
        id="damp_cavern",
        generator_binding="cellular",
        register="grim",
        dressing=dressing,
    )


def _special(
    *,
    id: str = "echoing_pool",
    telegraph: str = "a black pool reflects the torchlight",
    mechanic: str = "drink_to_scry",
) -> SpecialRoom:
    return SpecialRoom(
        id=id,
        telegraph=telegraph,
        mechanic=mechanic,
        outcome="vision",
        min_band="shallow",
    )


def _rng(seed: int = 42) -> random.Random:
    r = random.Random()
    r.seed(seed)
    return r


def test_dressing_lines_become_flavor_only_entities():
    look = _look(
        dressing=[
            "A slick green crust coats the walls.",
            "Water drips in regular plinks.",
            "The air smells of old iron.",
        ]
    )
    result = compose_room_prose(
        rng=_rng(),
        look_def=look,
        special_rooms=[],
        room_id="region_42",
    )
    flavor = [e for e in result.entities if e.tier == "flavor_only"]
    assert len(flavor) >= 1
    for e in flavor:
        assert e.provenance == "cookbook"
        assert e.binding is None
    assert result.description, "compose must emit non-empty prose"


def test_special_room_becomes_real_object_entity():
    look = _look(dressing=["A slick green crust coats the walls."])
    result = compose_room_prose(
        rng=_rng(),
        look_def=look,
        special_rooms=[_special(id="echoing_pool")],
        room_id="region_42",
    )
    real_objects = [e for e in result.entities if e.tier == "real_object"]
    assert len(real_objects) == 1
    e = real_objects[0]
    assert e.provenance == "cookbook"
    assert e.binding is not None
    assert e.binding.kind == "location_feature"
    assert e.binding.ref == "echoing_pool"
    # Affordances seeded from SpecialRoom.mechanic ("drink_to_scry").
    assert "drink_to_scry" in e.affordances


def test_deterministic_given_same_inputs():
    look = _look(
        dressing=[
            "Line A.",
            "Line B.",
            "Line C.",
            "Line D.",
            "Line E.",
        ]
    )
    a = compose_room_prose(
        rng=_rng(seed=1234),
        look_def=look,
        special_rooms=[],
        room_id="region_42",
    )
    b = compose_room_prose(
        rng=_rng(seed=1234),
        look_def=look,
        special_rooms=[],
        room_id="region_42",
    )
    assert a.description == b.description
    assert [e.id for e in a.entities] == [e.id for e in b.entities]


def test_different_seeds_produce_different_compositions():
    look = _look(
        dressing=[f"Line {i}." for i in range(20)]
    )
    a = compose_room_prose(
        rng=_rng(seed=1),
        look_def=look,
        special_rooms=[],
        room_id="region_42",
    )
    b = compose_room_prose(
        rng=_rng(seed=999),
        look_def=look,
        special_rooms=[],
        room_id="region_42",
    )
    assert a.description != b.description or a.entities != b.entities


def test_room_id_is_propagated_to_result():
    look = _look(dressing=["A slick green crust coats the walls."])
    result = compose_room_prose(
        rng=_rng(),
        look_def=look,
        special_rooms=[],
        room_id="region_99",
    )
    assert result.room_id == "region_99"


def test_empty_dressing_pool_raises_loudly():
    """No silent fallback — a LookDef with no dressing means the bundle
    failed validation upstream. Compose refuses to fabricate prose."""
    look = _look(dressing=[])
    with pytest.raises(ValueError, match="dressing"):
        compose_room_prose(
            rng=_rng(),
            look_def=look,
            special_rooms=[],
            room_id="region_42",
        )


def test_entity_ids_are_unique_within_a_room():
    look = _look(
        dressing=[
            "A slick green crust coats the walls.",
            "Water drips in regular plinks.",
            "The air smells of old iron.",
            "A slick green crust coats the walls.",  # duplicate text
        ]
    )
    result = compose_room_prose(
        rng=_rng(),
        look_def=look,
        special_rooms=[_special(id="echoing_pool"), _special(id="echoing_pool")],
        room_id="region_42",
    )
    ids = [e.id for e in result.entities]
    assert len(ids) == len(set(ids)), (
        f"compose must dedupe entity ids within a room; got {ids}"
    )
```

- [ ] **Step 3: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/game/cookbook/test_compose_room_prose.py -v
```
Expected: ImportError.

- [ ] **Step 4: Write `compose.py`**

Create `sidequest-server/sidequest/game/cookbook/compose.py`:

```python
"""compose_room_prose — deterministic per-region prose + manifest.

Story 55-1 / ADR-109 §5.2. Pure function consumed by
``assemble_region``. The dressing pool feeds ``flavor_only`` entities;
the per-region special rooms feed ``real_object`` entities with
``binding.kind = location_feature`` and affordances seeded from the
special's mechanic id.

All entities carry ``provenance="cookbook"`` — this is the seam the
ADR-100 KnownFacts / 54-6 promotion paths use to tell authored content
from procedurally composed content.

The RNG must be seeded by the caller from
``(campaign_seed, expansion_id, room_id)`` so re-materialization of the
same region produces identical output. ``assemble_region`` derives this
seed from its existing ``region_rng`` plus the ``room_id`` so the
deterministic chain is end-to-end.

The function refuses to fabricate prose: a LookDef with an empty
dressing pool raises ``ValueError`` loudly (No Silent Fallbacks).
``validate_bundle`` is the upstream guard that should catch this at
load time; the runtime guard here is a final safety net.
"""

from __future__ import annotations

import random
import re

from sidequest.game.cookbook.models import (
    GeneratedRoomDescription,
    LookDef,
    SpecialRoom,
)
from sidequest.protocol.models import (
    LocationEntity,
    LocationEntityBinding,
)

# v1 dressing sample size: 2 lines per room minimum, 3 maximum. Tuned per
# spec §8 ("Cookbook dressing pool size matters. Author 8-12 dressing
# lines per look minimum; assembler samples 2-3 per room").
DRESSING_PICK_MIN = 2
DRESSING_PICK_MAX = 3

_ID_TRIM_RE = re.compile(r"[^a-z0-9]+")


def _id_from_text(text: str) -> str:
    """Stable id derived from a dressing line. Lower-snake-ish."""
    base = _ID_TRIM_RE.sub("_", text.lower()).strip("_")
    # Truncate to a reasonable id length so DB joins remain ergonomic.
    return base[:48] or "flavor"


def compose_room_prose(
    *,
    rng: random.Random,
    look_def: LookDef,
    special_rooms: list[SpecialRoom],
    room_id: str,
) -> GeneratedRoomDescription:
    """Compose deterministic prose + manifest for one materialized region.

    See module docstring for contract notes. Raises ``ValueError`` when
    the LookDef has no dressing pool — that is an upstream bundle bug
    that must surface loudly (CLAUDE.md No Silent Fallbacks).
    """
    if not look_def.dressing:
        raise ValueError(
            f"compose_room_prose: LookDef {look_def.id!r} has empty dressing pool; "
            "cannot compose prose for room {room_id!r}. validate_bundle should "
            "have caught this at load time."
        )

    pool = list(look_def.dressing)
    pick_n = min(len(pool), rng.randint(DRESSING_PICK_MIN, DRESSING_PICK_MAX))
    # Sample without replacement so the same line never appears twice in
    # one room's prose.
    chosen_lines = rng.sample(pool, k=pick_n)

    # Build prose: dressing lines first (the base scene), then a single
    # paragraph break, then any special-room telegraph lines. This
    # ordering matches the spec's "base then special" hint flow.
    paragraphs: list[str] = list(chosen_lines)
    for special in special_rooms:
        if special.telegraph:
            paragraphs.append(special.telegraph)
    description = "\n\n".join(paragraphs)

    entities: list[LocationEntity] = []
    seen_ids: set[str] = set()

    # flavor_only entities from chosen dressing.
    for line in chosen_lines:
        entity_id = _id_from_text(line)
        if entity_id in seen_ids:
            continue
        seen_ids.add(entity_id)
        entities.append(
            LocationEntity(
                id=entity_id,
                label=line,
                tier="flavor_only",
                provenance="cookbook",
            )
        )

    # real_object entities from attached specials.
    for special in special_rooms:
        entity_id = _id_from_text(special.id)
        if entity_id in seen_ids:
            continue
        seen_ids.add(entity_id)
        entities.append(
            LocationEntity(
                id=entity_id,
                label=special.telegraph or special.id,
                tier="real_object",
                binding=LocationEntityBinding(
                    kind="location_feature",
                    ref=special.id,
                ),
                affordances=[special.mechanic] if special.mechanic else [],
                provenance="cookbook",
            )
        )

    return GeneratedRoomDescription(
        room_id=room_id,
        description=description,
        entities=entities,
    )
```

- [ ] **Step 5: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/cookbook/test_compose_room_prose.py -v
```
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/cookbook/compose.py \
        sidequest-server/tests/game/cookbook/test_compose_room_prose.py
git commit -m "feat(55-1): compose_room_prose — deterministic cookbook composition

Samples 2-3 dressing lines per room (spec §8 pool-size guidance) as
flavor_only entities; promotes per-region special rooms to real_object
entities with binding.kind=location_feature and affordances seeded
from the SpecialRoom.mechanic id. All entities carry provenance=
'cookbook'. Empty dressing pool raises ValueError (No Silent Fallbacks
— upstream validate_bundle is the real guard)."
```

---

### Task 3: Thread compose into `assemble_region`

**Files:**
- Modify: `sidequest-server/sidequest/game/cookbook/assemble.py`
- Modify: `sidequest-server/sidequest/game/cookbook/__init__.py`

`assemble_region` currently produces one `RegionContentManifest` per region. v1 of the manifest carries the `(prose, entities)` pair for the ONE region the assembler was called for — `room_descriptions` is always a single-element list in this story. (Multi-room-per-region is a future seam.)

- [ ] **Step 1: Extend `assemble_region`'s signature**

The caller (materializer) already passes `campaign_seed` and `expansion_id`. To compose per-room prose we need an additional `room_id` and the per-region `LookDef`. The look is already resolved inside `assemble_region` via `roll_race(bundle, look, rng)` consuming the `look` string param; the corresponding `LookDef` lives in `bundle.looks` keyed by id. v1: the `look` arg IS the look_def id; look it up at the compose call.

In `sidequest-server/sidequest/game/cookbook/assemble.py`, change the signature of `assemble_region` to accept `room_id`:

```python
def assemble_region(
    bundle: CookbookBundle,
    *,
    campaign_seed: str,
    expansion_id: str,
    depth_score: float,
    burst_magnitude: int,
    look: str,
    is_first_band_entry: bool,
    room_id: str,
) -> RegionContentManifest:
```

This adds a **new required keyword**. The materializer call site is updated in Task 4. Any other in-repo callers (`grep -rn "assemble_region(" sidequest-server/sidequest sidequest-server/tests`) must be updated to pass `room_id=`; tests that build a manifest standalone should pass `room_id="test_region"` or similar.

- [ ] **Step 2: Resolve the `LookDef` inside `assemble_region`**

After the existing race-roll block resolves `race`, look up the `LookDef`:

```python
    look_def = bundle.looks.get(look)
    if look_def is None:
        raise CookbookValidationError(
            f"cookbook: assemble_region received look={look!r} which is "
            f"not in bundle.looks (have: {sorted(bundle.looks)}). "
            "validate_bundle should have caught this."
        )
```

(Check `bundle.looks` shape with `grep -n "looks" sidequest-server/sidequest/game/cookbook/loader.py` — if `CookbookBundle.looks` is a `dict[str, LookDef]` the above works; otherwise adapt to the actual accessor.)

- [ ] **Step 3: Filter the per-region specials**

`pick_specials(...)` already returns the specials selected for this region. Convert each pick into the `SpecialRoom` model by id (the same id is `pick["id"]` per the dict shape):

```python
    region_specials: list[SpecialRoom] = []
    for sp in specials:
        sp_id = sp.get("id") if isinstance(sp, dict) else getattr(sp, "id", None)
        if sp_id is None:
            continue
        sp_def = bundle.special_rooms.get(sp_id)
        if sp_def is not None:
            region_specials.append(sp_def)
```

(Verify `bundle.special_rooms` is the right accessor; if the bundle stores them as a list, adapt to `{s.id: s for s in bundle.special_rooms}` inline.)

- [ ] **Step 4: Compose per-room and attach**

Just before the `return RegionContentManifest(...)`, add:

```python
    from sidequest.game.cookbook.compose import compose_room_prose

    # Deterministic per-room RNG seeded from (campaign_seed,
    # expansion_id, room_id). Reusing region_rng's pattern keeps the
    # seed derivation in one place; compose_room_prose receives a fresh
    # Random instance so its sampling does not perturb the outer rng's
    # stream (assemble_region's other rolls must remain stable).
    room_rng = random.Random()
    room_rng.seed((campaign_seed, expansion_id, room_id).__hash__())
    composed = compose_room_prose(
        rng=room_rng,
        look_def=look_def,
        special_rooms=region_specials,
        room_id=room_id,
    )
```

Add `import random` at the top of the file if not already present.

Then update the `return`:

```python
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
        room_descriptions=[composed],
    )
```

- [ ] **Step 5: Re-export**

In `sidequest-server/sidequest/game/cookbook/__init__.py`, add to the existing re-export block:

```python
from sidequest.game.cookbook.compose import compose_room_prose  # noqa: F401
from sidequest.game.cookbook.models import GeneratedRoomDescription  # noqa: F401
```

- [ ] **Step 6: Update the manifest-construction test**

Append to `sidequest-server/tests/game/cookbook/test_region_content_manifest_room_descriptions.py`:

```python
def test_assemble_region_populates_room_descriptions(tmp_path):
    """assemble_region threads compose_room_prose's output onto the manifest."""
    from sidequest.game.cookbook.assemble import assemble_region
    from sidequest.game.cookbook.loader import load_bundle

    # Use the real caverns_and_claudes cookbook bundle as the fixture
    # — the same bundle the megadungeon materializer drives in prod.
    from pathlib import Path

    here = Path(__file__).resolve()
    repo = here.parents[3]
    bundle_root = (
        repo
        / "sidequest-content"
        / "genre_packs"
        / "caverns_and_claudes"
        / "cookbook"
    )
    bundle = load_bundle(bundle_root)

    # Pick one valid look id from the bundle so the rolls land somewhere.
    look_id = next(iter(bundle.looks.keys()))

    manifest = assemble_region(
        bundle,
        campaign_seed="campaign-seed-1",
        expansion_id="expansion-1",
        depth_score=0.1,
        burst_magnitude=1,
        look=look_id,
        is_first_band_entry=True,
        room_id="region_42",
    )

    assert len(manifest.room_descriptions) == 1
    rd = manifest.room_descriptions[0]
    assert rd.room_id == "region_42"
    assert rd.description, "composed prose must be non-empty"
    assert any(e.tier == "flavor_only" for e in rd.entities)
```

(If the caverns_and_claudes cookbook bundle path is different, run `find sidequest-content/genre_packs/caverns_and_claudes -name "looks.yaml" -o -name "special_rooms.yaml"` to find the real bundle root.)

- [ ] **Step 7: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/cookbook/ -v
```
Expected: full cookbook suite green (including the existing `assemble_region` tests — they must be updated to pass `room_id=`).

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/game/cookbook/assemble.py \
        sidequest-server/sidequest/game/cookbook/__init__.py \
        sidequest-server/tests/game/cookbook/test_region_content_manifest_room_descriptions.py
git commit -m "feat(55-1): assemble_region threads compose_room_prose result

New required room_id= kwarg + per-room deterministic RNG seeded from
(campaign_seed, expansion_id, room_id). The composed prose + manifest
land on RegionContentManifest.room_descriptions[0]. Multi-room-per-
region is a future seam (v1: one region = one room per ADR-106).
Existing callers updated to pass room_id."
```

---

### Task 4: `write_room_yaml` filesystem helper

**Files:**
- Create: `sidequest-server/sidequest/dungeon/room_yaml_emit.py`
- Test: `sidequest-server/tests/dungeon/test_room_yaml_emit.py`

Keeping the YAML write in its own module gives the materializer a thin call site and the test a direct seam.

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/dungeon/test_room_yaml_emit.py`:

```python
"""write_room_yaml — round-trips through room_file_loader (Story 55-1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.dungeon.room_yaml_emit import write_room_yaml
from sidequest.game.room_file_loader import load_room_payload
from sidequest.protocol.models import (
    LocationEntity,
    LocationEntityBinding,
)


def _entities() -> list[LocationEntity]:
    return [
        LocationEntity(
            id="echoing_pool",
            label="a black pool reflects the torchlight",
            tier="real_object",
            binding=LocationEntityBinding(kind="location_feature", ref="echoing_pool"),
            affordances=["drink_to_scry"],
            provenance="cookbook",
        ),
        LocationEntity(
            id="slick_walls",
            label="A slick green crust coats the walls.",
            tier="flavor_only",
            provenance="cookbook",
        ),
    ]


def test_write_creates_yaml_file(tmp_path: Path):
    world_dir = tmp_path / "world"
    write_room_yaml(
        world_dir=world_dir,
        room_id="region_42",
        description="A narrow chamber slick with damp.",
        entities=_entities(),
    )
    assert (world_dir / "rooms" / "region_42.yaml").is_file()


def test_round_trip_via_room_file_loader(tmp_path: Path):
    world_dir = tmp_path / "world"
    write_room_yaml(
        world_dir=world_dir,
        room_id="region_42",
        description="A narrow chamber slick with damp.",
        entities=_entities(),
    )
    payload = load_room_payload(world_dir, "region_42")
    assert len(payload.entities) == 2
    assert payload.entities[0].id == "echoing_pool"
    assert payload.entities[0].binding is not None
    assert payload.entities[0].provenance == "cookbook"


def test_overwrite_false_refuses_existing_file(tmp_path: Path):
    world_dir = tmp_path / "world"
    write_room_yaml(
        world_dir=world_dir,
        room_id="region_42",
        description="first",
        entities=[],
    )
    with pytest.raises(FileExistsError):
        write_room_yaml(
            world_dir=world_dir,
            room_id="region_42",
            description="second",
            entities=[],
            overwrite=False,
        )


def test_overwrite_true_replaces_existing_file(tmp_path: Path):
    world_dir = tmp_path / "world"
    write_room_yaml(
        world_dir=world_dir,
        room_id="region_42",
        description="first",
        entities=[],
    )
    write_room_yaml(
        world_dir=world_dir,
        room_id="region_42",
        description="second",
        entities=[],
        overwrite=True,
    )
    yaml_path = world_dir / "rooms" / "region_42.yaml"
    assert "second" in yaml_path.read_text()


def test_creates_rooms_directory_if_missing(tmp_path: Path):
    world_dir = tmp_path / "world"
    assert not (world_dir / "rooms").exists()
    write_room_yaml(
        world_dir=world_dir,
        room_id="region_42",
        description="anything",
        entities=[],
    )
    assert (world_dir / "rooms").is_dir()
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/dungeon/test_room_yaml_emit.py -v
```
Expected: ImportError.

- [ ] **Step 3: Write the helper**

Create `sidequest-server/sidequest/dungeon/room_yaml_emit.py`:

```python
"""Writes a per-region YAML at ``<world>/rooms/<room_id>.yaml``.

Story 55-1 / ADR-109 §5.2. Called by the materializer after the
ADR-096 mask emit and after ``commit_expansion``. Idempotent: existing
YAMLs are not overwritten (freeze invariant — a re-materialization of
a frozen region must not rewrite content). The materializer passes
``overwrite=False`` for production paths; tests can pass
``overwrite=True`` when they want to verify replacement behavior.

The on-disk shape is the same one ``room_file_loader.load_room_payload``
consumes from the 54-2 path: a top-level ``description`` plus a top-
level ``entities`` list of ``LocationEntity`` model dumps. No
materializer state leaks into the file — the YAML is the durable
contract output, separately re-readable by the 54-3 validator and the
runtime loader.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

from sidequest.protocol.models import LocationEntity


def write_room_yaml(
    *,
    world_dir: Path,
    room_id: str,
    description: str,
    entities: Iterable[LocationEntity],
    overwrite: bool = False,
) -> Path:
    """Write one ``<world_dir>/rooms/<room_id>.yaml`` and return its path.

    Raises ``FileExistsError`` when the target file is already present
    and ``overwrite`` is False — this is the freeze invariant. Creates
    ``<world_dir>/rooms/`` if missing.
    """
    rooms_dir = Path(world_dir) / "rooms"
    rooms_dir.mkdir(parents=True, exist_ok=True)
    target = rooms_dir / f"{room_id}.yaml"

    if target.exists() and not overwrite:
        raise FileExistsError(
            f"write_room_yaml: {target!s} already exists and overwrite=False. "
            "Re-materialization of a frozen region must not rewrite content "
            "(freeze invariant — ADR-106 §7)."
        )

    payload: dict = {
        "description": description,
        "entities": [e.model_dump(mode="json") for e in entities],
    }
    target.write_text(yaml.safe_dump(payload, sort_keys=False))
    return target
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/dungeon/test_room_yaml_emit.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon/room_yaml_emit.py \
        sidequest-server/tests/dungeon/test_room_yaml_emit.py
git commit -m "feat(55-1): write_room_yaml — durable per-region YAML emit

Idempotent (overwrite=False refuses existing files — the freeze
invariant for a re-materialized frozen region). Round-trips through
room_file_loader.load_room_payload (54-2's loader path) so the
materializer's output and the runtime loader's input share a contract."
```

---

### Task 5: Materializer integration — `_stage_emit_room_yamls`

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/materializer.py`
- Test: `sidequest-server/tests/dungeon/test_materializer_room_yaml.py`

This is the **single materializer rewrite** the spec calls out (§7.3 Approach C stitch). Hook the YAML emit at the end of `_stage_commit`, AFTER the existing `commit_expansion` call and AFTER the existing mask emit (which lands in Epic 52). Each region in `expansion.new_nodes` gets one YAML write driven by its `RegionContentManifest.room_descriptions[0]` (Task 3 guarantees a single-element list per region in v1).

- [ ] **Step 1: Identify the per-region manifest source inside `_stage_commit`**

Run:
```bash
grep -n "region_manifests\|RegionContentManifest" sidequest-server/sidequest/dungeon/materializer.py | head -20
```

The manifests are produced by the design/curate stages and threaded into the commit call. Check the `_stage_commit` parameter list and trace whichever object carries the per-region manifests (likely `attach_result.region_manifests` or similar — confirm with the grep result).

- [ ] **Step 2: Determine the world directory**

The materializer needs to know which `<world>` directory to write into. Run:
```bash
grep -n "world_slug\|world_dir\|MaterializationRequest" sidequest-server/sidequest/dungeon/materializer.py | head -15
```

Most likely `MaterializationRequest` already carries `world_slug` (the materializer is per-world). Confirm. If `world_slug` is present, resolve `world_dir` the same way `_maybe_emit_location_description` does (54-2 uses `GenreLoader.find(genre_slug) / "worlds" / world_slug`). If the request doesn't carry `genre_slug`, surface that as a TODO surfaced in this story's design — but checked beforehand, the megadungeon materializer is invoked from a session that knows both, so `MaterializationRequest` is the natural seam. Add a new field if needed.

- [ ] **Step 3: Write the failing wiring test**

Create `sidequest-server/tests/dungeon/test_materializer_room_yaml.py`:

```python
"""Materializer writes <world>/rooms/<id>.yaml per region (Story 55-1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.dungeon.materializer import _stage_emit_room_yamls
from sidequest.game.cookbook.models import GeneratedRoomDescription
from sidequest.protocol.models import LocationEntity


def _composed(room_id: str) -> GeneratedRoomDescription:
    return GeneratedRoomDescription(
        room_id=room_id,
        description=f"Prose for {room_id}.",
        entities=[
            LocationEntity(
                id=f"{room_id}_cobwebs",
                label="cobwebs",
                tier="flavor_only",
                provenance="cookbook",
            ),
        ],
    )


def test_emits_one_yaml_per_region(tmp_path: Path):
    world_dir = tmp_path / "caverns_sunden"
    composed_by_region = {
        "region_1": _composed("region_1"),
        "region_2": _composed("region_2"),
        "region_3": _composed("region_3"),
    }
    _stage_emit_room_yamls(
        world_dir=world_dir,
        composed_by_region=composed_by_region,
    )
    rooms_dir = world_dir / "rooms"
    assert {p.name for p in rooms_dir.iterdir()} == {
        "region_1.yaml",
        "region_2.yaml",
        "region_3.yaml",
    }


def test_existing_yaml_is_not_overwritten(tmp_path: Path):
    """Freeze invariant: a region that already has a YAML on disk is left alone."""
    world_dir = tmp_path / "caverns_sunden"
    (world_dir / "rooms").mkdir(parents=True)
    (world_dir / "rooms" / "region_1.yaml").write_text(
        "description: pre-existing\nentities: []\n"
    )
    composed_by_region = {
        "region_1": _composed("region_1"),
        "region_2": _composed("region_2"),
    }
    _stage_emit_room_yamls(
        world_dir=world_dir,
        composed_by_region=composed_by_region,
    )
    # region_1 untouched.
    assert "pre-existing" in (world_dir / "rooms" / "region_1.yaml").read_text()
    # region_2 written.
    assert (world_dir / "rooms" / "region_2.yaml").is_file()


def test_empty_composed_map_is_a_noop(tmp_path: Path):
    world_dir = tmp_path / "caverns_sunden"
    _stage_emit_room_yamls(world_dir=world_dir, composed_by_region={})
    # No rooms/ directory created when there's nothing to write.
    # (The helper's behavior on empty input: do not create empty dirs.)
    assert not (world_dir / "rooms").exists() or not any(
        (world_dir / "rooms").iterdir()
    )


def test_emit_helper_has_a_caller_in_production_code():
    """Wiring proof per CLAUDE.md — the helper must be called from
    _stage_commit, not just exist as a function."""
    from pathlib import Path as _P

    src = (
        _P(__file__).resolve().parents[3]
        / "sidequest-server"
        / "sidequest"
        / "dungeon"
        / "materializer.py"
    ).read_text()
    assert "def _stage_emit_room_yamls(" in src
    # def + at least one call site from inside _stage_commit.
    assert src.count("_stage_emit_room_yamls(") >= 2
```

- [ ] **Step 4: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/dungeon/test_materializer_room_yaml.py -v
```
Expected: ImportError on `_stage_emit_room_yamls`.

- [ ] **Step 5: Add `_stage_emit_room_yamls` to the materializer**

In `sidequest-server/sidequest/dungeon/materializer.py`, add (near the other `_stage_*` helpers, alphabetically — likely just before `_stage_fill`):

```python
def _stage_emit_room_yamls(
    *,
    world_dir: Path,
    composed_by_region: dict[str, "GeneratedRoomDescription"],
) -> None:
    """Story 55-1 / ADR-109 §5.2: write one <world_dir>/rooms/<id>.yaml
    per region using the cookbook's composed (prose, entities[]).

    Idempotent — existing YAMLs are NEVER overwritten (freeze invariant
    matches the rest of the Plan 7 commit stage; a re-materialization
    of a frozen region must not rewrite its content). The 54-3
    validator runs as a post-materialize check on the emitted YAMLs.

    Empty ``composed_by_region`` is a clean no-op — no empty rooms/
    directory is created.
    """
    from sidequest.dungeon.room_yaml_emit import write_room_yaml

    for region_id, composed in composed_by_region.items():
        target = world_dir / "rooms" / f"{region_id}.yaml"
        if target.exists():
            continue
        write_room_yaml(
            world_dir=world_dir,
            room_id=region_id,
            description=composed.description,
            entities=composed.entities,
            overwrite=False,
        )
```

Add the forward-ref import at the top of the file (or use a `TYPE_CHECKING` block if a circular import surfaces):

```python
from sidequest.game.cookbook.models import GeneratedRoomDescription, RegionContentManifest
```

(`RegionContentManifest` is already imported in the file per the earlier grep; just add `GeneratedRoomDescription` to the same import.)

- [ ] **Step 6: Call the helper from `_stage_commit`**

Inside `_stage_commit`, immediately after the successful `conn.commit()` (the txn-success path), add:

```python
        # Story 55-1 / ADR-109: write per-region YAMLs alongside the
        # ADR-096 mask sidecar. AFTER the commit so we never emit
        # content for a region whose persistence rolled back.
        composed_by_region: dict[str, GeneratedRoomDescription] = {}
        for node in expansion.new_nodes:
            manifest = attach_result.region_manifests.get(node.id)
            if manifest is None or not manifest.room_descriptions:
                continue
            composed_by_region[node.id] = manifest.room_descriptions[0]

        if composed_by_region:
            world_dir = _resolve_world_dir(request)
            _stage_emit_room_yamls(
                world_dir=world_dir,
                composed_by_region=composed_by_region,
            )
```

…and add the `_resolve_world_dir` helper near the top of the file:

```python
def _resolve_world_dir(request: "MaterializationRequest") -> Path:
    """Resolve <genre_pack_root>/worlds/<world_slug> for the current request.

    The materializer is invoked from a session that has already resolved
    both genre and world. ``MaterializationRequest`` carries
    ``genre_slug`` and ``world_slug`` so this lookup is deterministic.
    """
    from sidequest.genre.loader import DEFAULT_GENRE_PACK_SEARCH_PATHS, GenreLoader

    loader = GenreLoader(search_paths=DEFAULT_GENRE_PACK_SEARCH_PATHS)
    pack_root = loader.find(request.genre_slug)
    return pack_root / "worlds" / request.world_slug
```

If `MaterializationRequest` does NOT carry `genre_slug` / `world_slug` (verify with `grep -n "class MaterializationRequest" sidequest-server/sidequest/dungeon/materializer.py` and read the field list), add the two fields in the same Task 5 patch — they are needed for the materializer to know where to write. Update every caller to pass them; tests should pass `genre_slug="caverns_and_claudes"`, `world_slug="caverns_sunden"`.

- [ ] **Step 7: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/dungeon/test_materializer_room_yaml.py -v
```
Expected: 4 passed.

- [ ] **Step 8: Run the broader materializer suite**

```bash
cd sidequest-server && uv run pytest tests/dungeon/ -v --timeout=60
```
Expected: full green. Existing materializer integration tests should be unaffected — the new emit runs after `commit_expansion` and is a no-op when `attach_result.region_manifests` produces no `room_descriptions` (which is the case for any test that builds a `RegionContentManifest` with the default empty `room_descriptions=[]`).

- [ ] **Step 9: Lint + format**

```bash
just server-fmt && just server-lint
```

- [ ] **Step 10: Commit**

```bash
git add sidequest-server/sidequest/dungeon/materializer.py \
        sidequest-server/tests/dungeon/test_materializer_room_yaml.py
git commit -m "feat(55-1): materializer emits <world>/rooms/<id>.yaml per region

New _stage_emit_room_yamls helper runs after _stage_commit's
conn.commit() so a rolled-back expansion never produces orphan
YAMLs. Idempotent: an existing YAML on disk is skipped (freeze
invariant — re-materialization of a frozen region must not rewrite
content). Single materializer rewrite per spec §7.3 Approach C
stitch."
```

---

### Task 6: Validator post-check integration test

**Files:**
- Create: `sidequest-server/tests/integration/test_pf_validate_locations_on_materialized.py`

After the materializer writes a fresh batch of YAMLs, the 54-3 validator (`pf validate locations`) should report zero hard errors over the emitted set. This integration test materializes a small expansion against a real cookbook bundle, then invokes the validator programmatically and asserts the result.

- [ ] **Step 1: Inspect 54-3's validator entry point**

Run:
```bash
grep -rn "def validate_locations\|class LocationValidator\|pf.cli.validate.locations" sidequest-server/sidequest sidequest-server/tests | head -10
```

Story 54-3 ships the validator; this test invokes its programmatic entry. If the API is `validate_locations_in_world(world_dir)` returning a `ValidationReport` with `.errors` / `.warnings`, use that. If it's only a CLI, invoke it via `subprocess.run(["pf", "validate", "locations", ...])` and parse exit code (less elegant but lives in the file 54-3 ships).

- [ ] **Step 2: Write the integration test**

Create `sidequest-server/tests/integration/test_pf_validate_locations_on_materialized.py`:

```python
"""Post-materialize, pf validate locations finds zero hard errors (Story 55-1)."""

from __future__ import annotations

from pathlib import Path

import pytest

# Story 55-1 wiring test against 54-3's validator. The exact import
# below MUST match the API 54-3 lands; if 54-3 lands the function under
# a different name, update this import only.
from sidequest.cli.validate import validate_locations_in_world  # type: ignore[import]


@pytest.fixture
def materialized_world(tmp_path: Path) -> Path:
    """Run a small fresh materialization producing N rooms YAMLs."""
    from sidequest.dungeon.materializer import materialize, MaterializationRequest
    from sidequest.dungeon.persistence import DungeonStore

    # Use the real caverns_and_claudes cookbook bundle so the dressing /
    # special-room corpora the validator scans are the production ones.
    repo_root = Path(__file__).resolve().parents[3]
    world_dir = tmp_path / "caverns_sunden"
    world_dir.mkdir()

    store_db = tmp_path / "save.db"
    store = DungeonStore.open(store_db)

    request = MaterializationRequest(
        campaign_seed=1234,
        expansion_id=1,
        genre_slug="caverns_and_claudes",
        world_slug="caverns_sunden",
        # Minimal expansion: 2-3 regions is enough to exercise the validator.
        burst_magnitude=2,
        # Other fields per MaterializationRequest's real signature.
    )

    # The real materialize() is async; use asyncio.run for the test.
    import asyncio

    asyncio.run(materialize(request, store=store))
    return world_dir


def test_pf_validate_locations_reports_no_hard_errors(materialized_world: Path):
    report = validate_locations_in_world(materialized_world)
    # 55-1 emits ``provenance="cookbook"`` entities with binding only on
    # real_object tier — the well-formedness + binding-resolution hard
    # checks (54-3 spec §5.1) must pass on every emitted YAML.
    assert report.errors == [], (
        f"validator hard errors on materialized YAMLs: {report.errors}"
    )
```

(The two `# type: ignore` comments and the API names — `validate_locations_in_world`, `report.errors`, `MaterializationRequest`, `materialize` — must be updated to match the real shape 54-3 / Epic 52 ship. The test is **structural**: a materialize-then-validate round trip whose contract is "no hard errors". Adjust call shapes as needed when running it for the first time; the assertion is the load-bearing part.)

- [ ] **Step 3: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/integration/test_pf_validate_locations_on_materialized.py -v
```

Expected: green. If the materializer test setup needs additional fields on `MaterializationRequest` (depth_score, palette path, etc.) that this scaffold elides, follow the failing-test error message to fill them in — the existing materializer integration tests in `tests/dungeon/` are the reference for a working request shape.

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/tests/integration/test_pf_validate_locations_on_materialized.py
git commit -m "test(55-1): pf validate locations clean on materialized YAMLs

End-to-end: real cookbook bundle → materialize fresh expansion →
54-3 validator reports zero hard errors over the emitted
<world>/rooms/<id>.yaml set. The validator is the CI-level smoke
that closes the producer/consumer loop between Epic 52 (materializer
+ mask emit), Epic 54 (manifest types + validator), and this story."
```

---

### Task 7: Full server suite + check-all

- [ ] **Step 1: Full server suite**

```bash
just server-test
```
Expected: green. The cookbook tests now require `room_id=` on `assemble_region`; if a downstream test fails because it called the old signature, update the call.

- [ ] **Step 2: Lint + format**

```bash
just server-fmt && just server-lint
```

- [ ] **Step 3: Aggregate gate**

```bash
just check-all
```
Expected: green.

- [ ] **Step 4: Live materializer smoke**

```bash
just up
# In another shell: connect a client and start a fresh beneath_sunden session,
# materialize the entrance + one expansion, then inspect:
ls sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/
```
Expected: at least one `<region_id>.yaml` per newly-materialized region. Each YAML has a non-empty `description` and a non-empty `entities` list with `provenance: cookbook`. Re-materialization of the same expansion does NOT rewrite the YAMLs (freeze invariant — check `mtime` doesn't change on a second run).

Then:
```bash
pf validate locations caverns_and_claudes caverns_sunden
```
Expected: zero hard errors, low warning count.

If the live smoke turns up content gaps (e.g. a LookDef whose dressing pool is too thin), that's authored-content debt for the cookbook author — NOT a 55-1 implementation bug. Surface it as a Delivery Finding and move on.

---

### Self-review checklist

- [ ] **Spec §5.2 coverage:** `compose_room_prose(rng, look_def, special_rooms, room_id)` → `(prose, entities[])` ✓; deterministic seeded from `(campaign_seed, expansion_id, room_id)` ✓; dressing lines become flavor_only entities ✓; SpecialRoom.telegraph references become real_object entities with `binding.kind=location_feature` and affordances seeded from `SpecialRoom.mechanic` ✓.
- [ ] **Spec §4.2 coverage:** `<world>/rooms/<room_id>.yaml` carries top-level `description` + `entities[]` ✓; round-trips through `room_file_loader.load_room_payload` (54-2's loader) ✓.
- [ ] **Spec §7.3 coverage:** single materializer rewrite ✓; emits AFTER existing commit_expansion + mask emit ✓; freeze invariant — existing YAMLs never rewritten ✓.
- [ ] **Spec §5.1 coverage:** validator post-check on emitted rooms ✓ (`test_pf_validate_locations_on_materialized.py`).
- [ ] **Placeholder scan:** no TBDs. Every code block is a real implementation. The Task 6 integration test names exact APIs that depend on 54-3's surface — if 54-3 lands them under different names this test is the seam to update, not a placeholder.
- [ ] **Type consistency:** `LocationEntity.provenance="cookbook"` literal matches 54-2's model declaration; `GeneratedRoomDescription` shape matches the per-room contract; `RegionContentManifest.room_descriptions` reads cleanly across `assemble_region` → materializer.
- [ ] **No silent fallback:** empty dressing pool raises `ValueError` (compose layer); missing `LookDef` raises `CookbookValidationError` (assemble layer); existing YAML raises `FileExistsError` when `overwrite=False` (emit layer); `_stage_emit_room_yamls` skips a region whose YAML exists rather than failing the whole materialization (the skip IS the freeze invariant — it's not silent, it's explicit in the function docstring AND has its own test).
- [ ] **No stub:** every code path implemented. The materializer integration is a real call; the emit helper writes real YAML; the validator integration test calls the real 54-3 entry point.
- [ ] **Freeze invariant honored:** `_stage_emit_room_yamls` runs AFTER `conn.commit()` (rolled-back expansions produce no YAMLs); existing files are never rewritten; on-disk content for a frozen region survives a re-materialization unchanged. The covering tests are `test_existing_yaml_is_not_overwritten` (Task 5) and the existing materializer `_stage_commit` rollback tests (already in the dungeon suite — not modified by this story).
- [ ] **Wiring tests present:** `test_emit_helper_has_a_caller_in_production_code` proves `_stage_emit_room_yamls` has at least one non-test caller (the def + the `_stage_commit` call site); the integration test `test_pf_validate_locations_on_materialized.py` proves the full producer/consumer chain runs end-to-end.

### Dependencies / handoff

- **Blocked by:** 52-2 / 52-3 (Epic 52 mask emit must land first — the YAML emit sits at the same `_stage_commit` seam), 54-2 (`LocationEntity` model + `room_file_loader` round-trip), 54-3 (`pf validate locations` programmatic entry the integration test calls).
- **Unblocks:** Nothing — Epic 55 is the closing stitch.
- **Out of scope:**
  - Cookbook dressing pool **content** authoring (story scope is the wiring; thin pools surface as authoring debt, not 55-1 bugs).
  - Multi-room-per-region (v1: one region = one room per ADR-106 — the spec is explicit; multi-room is a future seam at `assemble_region`'s `room_id` param).
  - Image generation bound to cookbook-composed entities (spec §2 out-of-scope).
  - Player-facing prose tuning (the validator's warning channel surfaces drift; tuning is author work, not a 55-1 patch).
  - Cross-region entities (NPCs already go via the NPC subsystem per spec §2 out-of-scope).
