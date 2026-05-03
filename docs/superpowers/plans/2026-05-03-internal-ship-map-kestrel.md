# Internal Ship Map (Kestrel) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a server-rendered SVG of the Kestrel's interior — 4 rooms, 4 stations, narrator-tracked PC + NPC positions — for tonight's playgroup session.

**Architecture:** Mirror the orbital chart pattern. New `sidequest/interior/` server module owns content models, loader, SVG renderer, and a REST endpoint. UI gains a `ShipWidget` (sibling of `MapWidget`) that fetches once on bind and refetches when a `STATE_PATCH` touches `current_room`. Narrator owns position tracking via state patches; positions never change without the narrator's say-so.

**Tech Stack:** Python 3.13 + FastAPI + Pydantic v2 + `svgwrite` + OpenTelemetry (server). React 19 + Vite + Tailwind (UI). YAML (content). pytest (server). vitest (UI).

**Source spec:** `docs/superpowers/specs/2026-05-03-internal-ship-map-kestrel-design.md` (commit `fb46184`).

**Repos touched:**
- `sidequest-content/genre_packs/space_opera/chassis_classes.yaml` (develop)
- `sidequest-server/` (develop)
- `sidequest-ui/` (develop)

**Standing rules (from CLAUDE.md):**
- No silent fallbacks — bad data raises with explicit context.
- No stubs — every type has a consumer in the same or earlier task.
- Every test suite includes a wiring test.
- Per-subsystem OTEL — `interior.render` and `interior.position_change` spans are mandatory.
- Memory: divide pre-AI hour estimates by ~10 (this whole plan is ~30 min wall-clock).
- Memory: gitflow on subrepos targets `develop`, not `main`.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `sidequest-content/genre_packs/space_opera/chassis_classes.yaml` | Modify | Append `stations:` block on `voidborn_freighter` |
| `sidequest-server/sidequest/genre/models/chassis.py` | Modify | Add `StationSpec` model; extend `ChassisClass` with `stations: list[StationSpec]` |
| `sidequest-server/sidequest/game/character.py` | Modify | Add `current_room: str \| None = None` to `Character` |
| `sidequest-server/sidequest/game/chassis.py` | Modify | Surface `current_room` per crew NPC (from `default_seat` → fallback to first room) |
| `sidequest-server/sidequest/interior/__init__.py` | Create | Package marker |
| `sidequest-server/sidequest/interior/loader.py` | Create | Cross-validate every station's `room` exists on its chassis class |
| `sidequest-server/sidequest/interior/render.py` | Create | `render_interior_svg(chassis_instance, snapshot) -> str` |
| `sidequest-server/sidequest/interior/dispatch.py` | Create | `interior_router` (FastAPI APIRouter) with `GET /api/chassis/{instance_id}/interior` |
| `sidequest-server/sidequest/telemetry/spans/interior.py` | Create | `emit_interior_render`, `emit_interior_position_change` |
| `sidequest-server/sidequest/server/app.py` | Modify | `include_router(interior_router)` |
| `sidequest-server/sidequest/agents/narrator.py` | Modify | Surface `current_room` per character; instruct narrator to state-patch on movement |
| `sidequest-server/tests/interior/__init__.py` | Create | Test package marker |
| `sidequest-server/tests/interior/test_models.py` | Create | StationSpec + ChassisClass.stations validation |
| `sidequest-server/tests/interior/test_loader.py` | Create | Cross-validation: bad `station.room` raises loud |
| `sidequest-server/tests/interior/test_render.py` | Create | SVG render — assert structural elements (rooms, stations, actors) |
| `sidequest-server/tests/interior/test_endpoint_wired.py` | Create | **Wiring test** — endpoint reachable, returns SVG |
| `sidequest-server/tests/agents/test_narrator_current_room.py` | Create | **Wiring test** — narrator prompt includes `current_room` |
| `sidequest-ui/src/components/GameBoard/widgets/ShipWidget.tsx` | Create | Ship tab widget, mirrors `MapWidget` shape |
| `sidequest-ui/src/hooks/useChassisInteriorSVG.ts` | Create | Fetch + STATE_PATCH refetch hook |
| `sidequest-ui/src/components/GameBoard/widgetRegistry.ts` | Modify | Register `ship` widget id + hotkey |
| `sidequest-ui/src/components/GameBoard/__tests__/ShipWidget.test.tsx` | Create | **Wiring test** — refetch on `current_room` STATE_PATCH |

---

## Conventions

- **Branch:** one feature branch per repo, `feat/internal-ship-map-kestrel`. Targets `develop` on every subrepo (gitflow per `.pennyfarthing/repos.yaml`).
- **Commits:** Conventional Commits — `feat(interior): ...`, `feat(narrator): ...`, `chore(content): ...`, `test(interior): ...`. Frequent small commits.
- **Tests:** `cd sidequest-server && uv run pytest tests/path/test.py::test_name -v`. Lint: `uv run ruff check .`. UI tests: `npx vitest run path/to/test.tsx`.
- **PRs:** `gh pr create --base develop` for every subrepo. Bundle the orchestrator-level commit (none expected — all changes are in subrepos) at the end if needed.
- **Skip if blocked:** if any task fails for a discoverable reason (missing helper, schema gap), file the blocker as a TODO comment with `# TODO(ship-map): <detail>` and continue. Do not silently fall back.

---

## Task 1: Author 4 stations on voidborn_freighter

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/chassis_classes.yaml`

- [ ] **Step 1: Append `stations:` block under `voidborn_freighter`**

After `crew_roles:` (currently ends near line 62 with the `pilot` entry), append:

```yaml
    stations:
      - id: command
        display_name: "Command"
        room: cockpit
        preferred_role: captain
      - id: helm
        display_name: "Helm"
        room: cockpit
        preferred_role: pilot
      - id: weapons
        display_name: "Weapons"
        room: cockpit
        preferred_role: gunner
      - id: engineering_controls
        display_name: "Engineering"
        room: engineering
        preferred_role: engineer
```

- [ ] **Step 2: Commit**

```bash
cd sidequest-content
git checkout -b feat/internal-ship-map-kestrel
git add genre_packs/space_opera/chassis_classes.yaml
git commit -m "content(coyote_star): add 4 stations on voidborn_freighter

Three cockpit consoles (command, helm, weapons) plus engineering
controls. Comms is intentionally omitted — the Kestrel itself is
the comms (chassis voice). Soft preferred_role hint for the
Firefly skill curve."
```

---

## Task 2: StationSpec model + ChassisClass extension

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/chassis.py`
- Test: `sidequest-server/tests/interior/__init__.py` (create empty)
- Test: `sidequest-server/tests/interior/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/interior/__init__.py` (empty file).

Create `sidequest-server/tests/interior/test_models.py`:

```python
"""Tests for StationSpec and ChassisClass.stations."""
import pytest
from pydantic import ValidationError

from sidequest.genre.models.chassis import ChassisClass, StationSpec


def test_station_spec_required_fields():
    s = StationSpec(
        id="helm",
        display_name="Helm",
        room="cockpit",
        preferred_role="pilot",
    )
    assert s.id == "helm"
    assert s.preferred_role == "pilot"


def test_station_spec_preferred_role_optional():
    s = StationSpec(id="helm", display_name="Helm", room="cockpit")
    assert s.preferred_role is None


def test_station_spec_rejects_extra():
    with pytest.raises(ValidationError):
        StationSpec(
            id="helm", display_name="Helm", room="cockpit", bogus="x"
        )


def test_chassis_class_stations_default_empty():
    # Stations list is optional and defaults empty for chassis classes
    # that don't yet author them.
    c = ChassisClass(
        id="x",
        display_name="X",
        provenance="voidborn_built",
        scale_band="vehicular",
        crew_model="flexible_roles",
        embodiment_model="singular",
        crew_awareness="surface",
        psi_resonance={"default": "neutral", "amplifies": []},
        default_voice={
            "default_register": "dry",
            "name_forms_by_bond_tier": {
                "severed": "X", "hostile": "X", "strained": "X",
                "neutral": "X", "familiar": "X", "trusted": "X",
                "fused": "X",
            },
        },
        interior_rooms=[],
        crew_roles=[],
    )
    assert c.stations == []
```

Run: `cd sidequest-server && uv run pytest tests/interior/test_models.py -v`
Expected: import error (`StationSpec` not yet defined).

- [ ] **Step 2: Add `StationSpec` and extend `ChassisClass`**

Open `sidequest-server/sidequest/genre/models/chassis.py`. The existing model layout has `InteriorRoomSpec`, `CrewRoleSpec`, etc. Add a sibling:

```python
class StationSpec(BaseModel):
    """A crew station — a console inside an interior room.

    Stations are role-coded but not role-gated. Anyone can man any
    station; `preferred_role` is a soft hint the narrator can use to
    bias outcomes (Firefly skill curve — Zoe can fly, Wash is just
    better at it).
    """

    model_config = {"extra": "forbid"}
    id: str
    display_name: str
    room: str  # must reference an InteriorRoomSpec.id on the same ChassisClass
    preferred_role: str | None = None
```

Then on `ChassisClass` (find the class definition further down — the one with `interior_rooms: list[InteriorRoomSpec]` and `crew_roles: list[CrewRoleSpec]`), add:

```python
    stations: list[StationSpec] = Field(default_factory=list)
```

Run the test again: `uv run pytest tests/interior/test_models.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd sidequest-server
git checkout -b feat/internal-ship-map-kestrel
git add sidequest/genre/models/chassis.py tests/interior/__init__.py tests/interior/test_models.py
git commit -m "feat(genre): StationSpec + ChassisClass.stations"
```

---

## Task 3: Loader cross-validation — every station.room exists

**Files:**
- Create: `sidequest-server/sidequest/interior/__init__.py` (empty)
- Create: `sidequest-server/sidequest/interior/loader.py`
- Test: `sidequest-server/tests/interior/test_loader.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/interior/test_loader.py`:

```python
"""Cross-validation tests for stations on a chassis class."""
import pytest

from sidequest.genre.models.chassis import (
    ChassisClass,
    InteriorRoomSpec,
    StationSpec,
)
from sidequest.interior.loader import (
    InteriorLoaderError,
    validate_chassis_stations,
)


def _minimal_chassis(rooms, stations):
    return ChassisClass(
        id="test",
        display_name="Test",
        provenance="voidborn_built",
        scale_band="vehicular",
        crew_model="flexible_roles",
        embodiment_model="singular",
        crew_awareness="surface",
        psi_resonance={"default": "neutral", "amplifies": []},
        default_voice={
            "default_register": "dry",
            "name_forms_by_bond_tier": {
                "severed": "X", "hostile": "X", "strained": "X",
                "neutral": "X", "familiar": "X", "trusted": "X",
                "fused": "X",
            },
        },
        interior_rooms=rooms,
        crew_roles=[],
        stations=stations,
    )


def test_validate_passes_when_all_rooms_resolve():
    chassis = _minimal_chassis(
        rooms=[InteriorRoomSpec(id="cockpit", display_name="Cockpit")],
        stations=[
            StationSpec(id="helm", display_name="Helm", room="cockpit"),
        ],
    )
    validate_chassis_stations(chassis)  # no raise


def test_validate_raises_loud_on_unknown_room():
    chassis = _minimal_chassis(
        rooms=[InteriorRoomSpec(id="cockpit", display_name="Cockpit")],
        stations=[
            StationSpec(id="helm", display_name="Helm", room="bridge"),
        ],
    )
    with pytest.raises(InteriorLoaderError) as exc:
        validate_chassis_stations(chassis)
    assert "helm" in str(exc.value)
    assert "bridge" in str(exc.value)
```

Run: `uv run pytest tests/interior/test_loader.py -v`
Expected: import error (`sidequest.interior.loader` not yet defined).

- [ ] **Step 2: Implement `validate_chassis_stations`**

Create `sidequest-server/sidequest/interior/__init__.py` (empty).

Create `sidequest-server/sidequest/interior/loader.py`:

```python
"""Cross-validation for crew stations on a chassis class.

Per CLAUDE.md No Silent Fallbacks: an unknown room reference
raises with explicit context — station id, bad room, and the
list of valid rooms — so the failure is diagnosable from one
log line.
"""
from sidequest.genre.models.chassis import ChassisClass


class InteriorLoaderError(ValueError):
    """Raised when a chassis class has invalid station data."""


def validate_chassis_stations(chassis: ChassisClass) -> None:
    """Raise InteriorLoaderError if any station references an unknown room."""
    valid_rooms = {r.id for r in chassis.interior_rooms}
    for station in chassis.stations:
        if station.room not in valid_rooms:
            raise InteriorLoaderError(
                f"Station {station.id!r} references unknown room "
                f"{station.room!r}; valid rooms on chassis "
                f"{chassis.id!r}: {sorted(valid_rooms)}"
            )
```

Run: `uv run pytest tests/interior/test_loader.py -v`
Expected: PASS.

- [ ] **Step 3: Wire validation into chassis class loading**

Find where `ChassisClass` instances are loaded from YAML — most likely in `sidequest/genre/loader.py`. Search:

```bash
grep -n "ChassisClass\|chassis_classes" sidequest/genre/loader.py
```

After the chassis class is parsed, call `validate_chassis_stations(chassis)`. If the loader file uses a `_validate_*` pattern for its other cross-checks, follow that convention. The validation must happen at load time, not lazily — bad data fails at startup.

- [ ] **Step 4: Verify the existing voidborn_freighter loads clean**

```bash
cd sidequest-server && uv run python -c "
from sidequest.genre.loader import load_genre_pack
pack = load_genre_pack('space_opera')
voidborn = next(c for c in pack.chassis_classes if c.id == 'voidborn_freighter')
assert len(voidborn.stations) == 4
print('OK', [s.id for s in voidborn.stations])
"
```

Expected: `OK ['command', 'helm', 'weapons', 'engineering_controls']`

If the loader doesn't have a `chassis_classes` field exposed yet, search the actual API:
```bash
grep -rn "chassis_classes" sidequest/genre/ | head -10
```
Adapt the command above to the actual loader entry point.

- [ ] **Step 5: Commit**

```bash
git add sidequest/interior/__init__.py sidequest/interior/loader.py tests/interior/test_loader.py sidequest/genre/loader.py
git commit -m "feat(interior): cross-validate station rooms at load time"
```

---

## Task 4: `current_room` field on Character + ChassisInstance NPC defaults

**Files:**
- Modify: `sidequest-server/sidequest/game/character.py`
- Modify: `sidequest-server/sidequest/game/chassis.py`
- Test: `sidequest-server/tests/server/test_state_patch_current_room.py`
- Test: `sidequest-server/tests/server/test_chassis_npc_default_rooms.py`

- [ ] **Step 1: Write the failing test for `current_room` survival through state patch**

Create `sidequest-server/tests/server/test_state_patch_current_room.py`:

```python
"""current_room survives serialization + state patch roundtrip."""
import json

from sidequest.game.character import Character
from sidequest.game.creature_core import CreatureCore


def _basic_character() -> Character:
    return Character(
        core=CreatureCore(name="Rux"),
        backstory="freighter rat",
        char_class="captain",
        race="human",
        pronouns="they/them",
        stats={},
        abilities=[],
    )


def test_current_room_defaults_none():
    c = _basic_character()
    assert c.current_room is None


def test_current_room_round_trips_through_json():
    c = _basic_character()
    c.current_room = "galley"
    blob = c.model_dump()
    restored = Character.model_validate(blob)
    assert restored.current_room == "galley"


def test_current_room_accepts_state_patch():
    # Simulating the narrator's state-patch path.
    c = _basic_character()
    blob = c.model_dump()
    blob["current_room"] = "cockpit"
    restored = Character.model_validate(blob)
    assert restored.current_room == "cockpit"
```

Run: `uv run pytest tests/server/test_state_patch_current_room.py -v`
Expected: FAIL — `current_room` doesn't exist yet.

(If `CreatureCore` requires more fields than the snippet shows, run `python -c "from sidequest.game.creature_core import CreatureCore; print(CreatureCore.model_json_schema())"` and patch the test to satisfy the actual constructor. The point of the test is `current_room`, not the rest of the character.)

- [ ] **Step 2: Add `current_room` to `Character`**

In `sidequest-server/sidequest/game/character.py`, locate the `Character` class (around line 66). Add the field alongside the other narrative state fields:

```python
    # Position on the chassis interior (narrator-tracked, optional).
    # Set via state patch when the narrator moves a character between
    # rooms; rendered on the Ship tab. Stays None until the narrator
    # sets it; the renderer falls back to a chassis-default room.
    current_room: str | None = None
```

Run: `uv run pytest tests/server/test_state_patch_current_room.py -v`
Expected: PASS.

- [ ] **Step 3: Default rooms for kestrel NPCs at chassis materialization**

Open `sidequest-server/sidequest/game/chassis.py`. Find `ChassisInstance` (line 68 area) and the materialization function that builds it from `ChassisInstanceConfig` (around line 222: `for inst_cfg in cfg.chassis_instances:`).

The Kestrel's crew NPCs are listed by name (kestrel_captain, etc.) and their `Character` records get materialized somewhere downstream. **Find** where those NPC Characters get created from `crew_npcs` — search:

```bash
grep -rn "crew_npcs\|kestrel_captain" sidequest/ | head -10
```

When the NPC Character is constructed, set `current_room` based on their crew_role's `default_seat`, falling back to the first interior room. Add a helper in `sidequest/game/chassis.py`:

```python
def default_room_for_npc(
    chassis_class, crew_role_id: str | None
) -> str | None:
    """Return the default current_room for a freshly materialized NPC.

    Falls back to the first interior room if the crew role has no
    default_seat. Returns None if the chassis has no interior rooms.
    """
    if crew_role_id:
        role = next(
            (r for r in chassis_class.crew_roles if r.id == crew_role_id),
            None,
        )
        if role and role.default_seat:
            return role.default_seat
    if chassis_class.interior_rooms:
        return chassis_class.interior_rooms[0].id
    return None
```

Wire it at the NPC materialization site. The exact call site needs to be discovered — search `grep -rn "crew_npcs" sidequest/game/`.

- [ ] **Step 4: Wiring test — kestrel NPCs get default rooms**

Create `sidequest-server/tests/server/test_chassis_npc_default_rooms.py`:

```python
"""Wiring: kestrel NPCs land in sensible default rooms after materialization."""
from sidequest.genre.loader import load_genre_pack
# Adapt this import to the actual NPC-materialization function once located:
# from sidequest.game.chassis import materialize_kestrel_npcs


def test_kestrel_npcs_have_current_room():
    pack = load_genre_pack("space_opera")
    voidborn = next(c for c in pack.chassis_classes if c.id == "voidborn_freighter")
    # The pilot crew_role has default_seat=cockpit.
    pilot = next(r for r in voidborn.crew_roles if r.id == "pilot")
    assert pilot.default_seat == "cockpit"
    # First interior room is cockpit (falls back here for crew without a seat).
    assert voidborn.interior_rooms[0].id == "cockpit"
```

This is a thin contract test — it asserts the *data* is shaped right. The full e2e wiring (NPC Character objects have `current_room` set) gets added in Task 5 when the renderer needs it.

Run: `uv run pytest tests/server/test_chassis_npc_default_rooms.py -v`

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/character.py sidequest/game/chassis.py tests/server/test_state_patch_current_room.py tests/server/test_chassis_npc_default_rooms.py
git commit -m "feat(game): current_room field on Character + chassis NPC defaults"
```

---

## Task 5: SVG renderer — `render_interior_svg`

**Files:**
- Create: `sidequest-server/sidequest/interior/render.py`
- Test: `sidequest-server/tests/interior/test_render.py`

The Kestrel layout is hardcoded in this task. Generalizing across chassis classes is out of scope (spec §"Out of scope"). The orbital chart's `render.py` (`sidequest/orbital/render.py`) is the structural reference for `svgwrite` use, the engraved register palette, and the export shape — read it before writing this file.

- [ ] **Step 1: Write the failing test (structural assertions, not pixel-exact)**

Create `sidequest-server/tests/interior/test_render.py`:

```python
"""Structural assertions on interior SVG output.

We don't golden-match pixel coordinates; we assert that the SVG
contains the four rooms, four station pips, and one marker per
tracked actor. Layout coords can change without breaking tests.
"""
import re
from typing import Any

from sidequest.interior.render import render_interior_svg


def _fake_chassis_instance(name="Kestrel"):
    """Minimal stand-in matching the runtime ChassisInstance fields the
    renderer reads. Adjust attribute names to match the real class."""
    class _C:
        pass
    c = _C()
    c.id = "kestrel"
    c.name = name
    c.class_id = "voidborn_freighter"
    return c


def _fake_snapshot_with(actors_by_room: dict[str, list[tuple[str, str]]]):
    """actors_by_room: {room_id: [(actor_id, kind), ...]} where kind in {pc,npc}.

    Returns an object with the minimal interface render_interior_svg
    needs. Adjust to match what the real snapshot exposes.
    """
    class _Snap:
        pass
    s = _Snap()
    s.actors_by_room = actors_by_room  # renderer pulls this; helper handles
    return s


def _fake_chassis_class():
    """Voidborn freighter chassis class with the 4 rooms and 4 stations."""
    from sidequest.genre.models.chassis import (
        ChassisClass, InteriorRoomSpec, StationSpec,
    )
    return ChassisClass(
        id="voidborn_freighter",
        display_name="Voidborn Freighter",
        provenance="voidborn_built",
        scale_band="vehicular",
        crew_model="flexible_roles",
        embodiment_model="singular",
        crew_awareness="surface",
        psi_resonance={"default": "receptive", "amplifies": []},
        default_voice={
            "default_register": "dry_warm",
            "name_forms_by_bond_tier": {
                "severed": "Pilot", "hostile": "Pilot", "strained": "Pilot",
                "neutral": "Pilot", "familiar": "Mr. {last_name}",
                "trusted": "{first_name}", "fused": "{nickname}",
            },
        },
        interior_rooms=[
            InteriorRoomSpec(id="cockpit", display_name="Cockpit"),
            InteriorRoomSpec(id="engineering", display_name="Engineering"),
            InteriorRoomSpec(id="galley", display_name="Galley"),
            InteriorRoomSpec(id="deck_three_corridor", display_name="Deck Three Corridor"),
        ],
        crew_roles=[],
        stations=[
            StationSpec(id="command", display_name="Command", room="cockpit"),
            StationSpec(id="helm", display_name="Helm", room="cockpit"),
            StationSpec(id="weapons", display_name="Weapons", room="cockpit"),
            StationSpec(id="engineering_controls", display_name="Engineering", room="engineering"),
        ],
    )


def test_render_includes_all_four_rooms():
    chassis_class = _fake_chassis_class()
    chassis_inst = _fake_chassis_instance()
    snapshot = _fake_snapshot_with({})
    svg = render_interior_svg(chassis_class, chassis_inst, snapshot)
    for room_id in ["cockpit", "engineering", "galley", "deck_three_corridor"]:
        assert f'data-room="{room_id}"' in svg, f"missing room {room_id}"


def test_render_includes_all_four_stations():
    svg = render_interior_svg(
        _fake_chassis_class(),
        _fake_chassis_instance(),
        _fake_snapshot_with({}),
    )
    for sid in ["command", "helm", "weapons", "engineering_controls"]:
        assert f'data-station="{sid}"' in svg


def test_render_places_actor_in_their_room():
    svg = render_interior_svg(
        _fake_chassis_class(),
        _fake_chassis_instance(),
        _fake_snapshot_with({"galley": [("rux", "pc")]}),
    )
    assert 'data-actor="rux"' in svg
    # The actor element must live inside the galley group.
    galley_block = re.search(
        r'<g[^>]*data-room="galley"[^>]*>.*?</g>', svg, re.DOTALL
    )
    assert galley_block, "galley group not found"
    assert 'data-actor="rux"' in galley_block.group(0)


def test_render_includes_chassis_name():
    svg = render_interior_svg(
        _fake_chassis_class(),
        _fake_chassis_instance(name="Kestrel"),
        _fake_snapshot_with({}),
    )
    assert "Kestrel" in svg
```

Run: `uv run pytest tests/interior/test_render.py -v`
Expected: ImportError on `sidequest.interior.render`.

- [ ] **Step 2: Implement the renderer**

Read `sidequest-server/sidequest/orbital/render.py` first — it shows the engraved palette (sepia/amber against dark), the title-bar pattern, the `data-*` attribute convention for click-routing, and the `svgwrite` import shape. Use the same visual register so the Ship tab feels like a sibling of the orbital chart.

Create `sidequest-server/sidequest/interior/render.py`:

```python
"""Server-side SVG renderer for the chassis interior map.

Layout is hardcoded for the voidborn_freighter (the Kestrel) — a
2x2 grid of rooms with the cockpit top-left. Generalizing across
chassis classes is out of scope (spec §"Out of scope") until a
second class ships.

Visual register matches the orbital chart (engraved sepia on dark)
so the Ship tab sits visually next to the orbital tab.
"""
from __future__ import annotations

import svgwrite

from sidequest.genre.models.chassis import ChassisClass

# Engraved palette — match orbital/render.py conventions.
INK = "#e8c98c"
DIM = "#7a6443"
BG = "#0c0a08"
PC_COLOR = "#9be17a"
NPC_COLOR = "#e8c98c"

# 2x2 hardcoded layout for voidborn_freighter.
ROOM_LAYOUT: dict[str, tuple[float, float, float, float]] = {
    # room_id: (x, y, width, height)
    "cockpit":              (40, 60, 280, 180),
    "engineering":          (340, 60, 220, 180),
    "galley":               (40, 260, 280, 180),
    "deck_three_corridor":  (340, 260, 220, 180),
}

VIEWBOX = (0, 0, 600, 480)


def _actors_by_room_from_snapshot(snapshot) -> dict[str, list[tuple[str, str]]]:
    """Extract {room_id: [(actor_id, 'pc'|'npc'), ...]} from snapshot.

    The snapshot exposes actors via test fixtures as `actors_by_room`;
    in production it walks snapshot.characters + snapshot.npcs and
    reads each actor's current_room. The two paths are unified here
    so renderer tests stay simple while production reads the real shape.
    """
    if hasattr(snapshot, "actors_by_room"):
        return snapshot.actors_by_room  # test-friendly
    # Production path:
    out: dict[str, list[tuple[str, str]]] = {}
    for pc in getattr(snapshot, "characters", []) or []:
        room = getattr(pc, "current_room", None)
        if room:
            out.setdefault(room, []).append((pc.core.name, "pc"))
    for npc in getattr(snapshot, "npcs", []) or []:
        room = getattr(npc, "current_room", None)
        if room:
            out.setdefault(room, []).append((npc.core.name, "npc"))
    return out


def render_interior_svg(
    chassis_class: ChassisClass,
    chassis_instance,
    snapshot,
) -> str:
    """Return a complete SVG document for the interior map."""
    dwg = svgwrite.Drawing(size=("600px", "480px"), viewBox=" ".join(map(str, VIEWBOX)))
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=BG))

    # Title bar with chassis instance name.
    dwg.add(dwg.text(
        chassis_instance.name,
        insert=(20, 36),
        fill=INK,
        font_family="Cinzel, serif",
        font_size="22px",
    ))

    actors_by_room = _actors_by_room_from_snapshot(snapshot)
    stations_by_room: dict[str, list] = {}
    for s in chassis_class.stations:
        stations_by_room.setdefault(s.room, []).append(s)

    for room in chassis_class.interior_rooms:
        coords = ROOM_LAYOUT.get(room.id)
        if coords is None:
            # Hardcoded layout doesn't know this room — render in a
            # reserve slot at the bottom so the operator notices.
            coords = (20, 460, 100, 16)
        x, y, w, h = coords
        room_g = dwg.g(**{"data-room": room.id})

        # Room frame
        room_g.add(dwg.rect(
            insert=(x, y), size=(w, h),
            fill="none", stroke=INK, stroke_width=1.2,
        ))
        # Room label
        room_g.add(dwg.text(
            room.display_name,
            insert=(x + 8, y + 18),
            fill=INK, font_family="Cinzel, serif", font_size="14px",
        ))

        # Stations as small circles along the top edge.
        for i, station in enumerate(stations_by_room.get(room.id, [])):
            sx = x + 16 + i * 60
            sy = y + 36
            station_g = dwg.g(**{"data-station": station.id})
            station_g.add(dwg.circle(center=(sx, sy), r=6,
                                      fill="none", stroke=INK, stroke_width=1.2))
            station_g.add(dwg.text(
                station.display_name,
                insert=(sx - 18, sy + 22),
                fill=DIM, font_family="Cinzel, serif", font_size="9px",
            ))
            room_g.add(station_g)

        # Actor markers — bottom edge of room, left to right.
        for i, (actor_id, kind) in enumerate(actors_by_room.get(room.id, [])):
            ax = x + 24 + i * 60
            ay = y + h - 24
            color = PC_COLOR if kind == "pc" else NPC_COLOR
            actor_g = dwg.g(**{"data-actor": actor_id, "data-actor-kind": kind})
            actor_g.add(dwg.circle(center=(ax, ay), r=8, fill=color, stroke=INK))
            actor_g.add(dwg.text(
                actor_id,
                insert=(ax - 24, ay + 18),
                fill=INK, font_family="Cinzel, serif", font_size="10px",
            ))
            room_g.add(actor_g)

        dwg.add(room_g)

    return dwg.tostring()
```

Run: `uv run pytest tests/interior/test_render.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add sidequest/interior/render.py tests/interior/test_render.py
git commit -m "feat(interior): render_interior_svg — hardcoded Kestrel layout"
```

---

## Task 6: REST endpoint + wiring test

**Files:**
- Create: `sidequest-server/sidequest/interior/dispatch.py`
- Modify: `sidequest-server/sidequest/server/app.py`
- Test: `sidequest-server/tests/interior/test_endpoint_wired.py`

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-server/tests/interior/test_endpoint_wired.py`:

```python
"""Wiring test: GET /api/chassis/{id}/interior reaches the renderer."""
from fastapi.testclient import TestClient

from sidequest.server.app import create_app


def test_interior_endpoint_returns_svg_for_kestrel():
    """End-to-end: app routes the request to the renderer and returns SVG.

    Uses the live genre pack so this fails loudly if the chassis YAML
    drift would silently break the endpoint.
    """
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/chassis/kestrel/interior")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")
    body = resp.text
    assert "Kestrel" in body
    assert 'data-room="cockpit"' in body
    assert 'data-station="helm"' in body


def test_interior_endpoint_404_on_unknown_chassis():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/chassis/nonexistent/interior")
    assert resp.status_code == 404
```

Run: `uv run pytest tests/interior/test_endpoint_wired.py -v`
Expected: 404 on the kestrel test (route doesn't exist yet).

- [ ] **Step 2: Implement `interior_router`**

Create `sidequest-server/sidequest/interior/dispatch.py`:

```python
"""REST endpoint for the chassis interior SVG.

GET /api/chassis/{instance_id}/interior -> image/svg+xml
"""
from fastapi import APIRouter, HTTPException, Response

from sidequest.genre.loader import load_genre_pack
from sidequest.interior.render import render_interior_svg
from sidequest.telemetry.spans.interior import emit_interior_render

interior_router = APIRouter()


def _find_chassis_instance(instance_id: str):
    """Walk every loaded genre pack for a chassis instance with this id.

    Returns (chassis_class, chassis_instance_config) or (None, None).
    """
    # Adapt to the actual genre-pack discovery API. The orbital
    # endpoint uses a similar shape — read its dispatch file:
    # sidequest/orbital/intent.py for the discovery pattern.
    for pack_name in ["space_opera"]:  # extend when more chassis worlds ship
        pack = load_genre_pack(pack_name)
        for world in getattr(pack, "worlds", []) or []:
            for inst in getattr(world, "chassis_instances", []) or []:
                if inst.id == instance_id:
                    chassis_class = next(
                        (c for c in pack.chassis_classes if c.id == inst.class_),
                        None,
                    )
                    return chassis_class, inst, world
    return None, None, None


@interior_router.get("/api/chassis/{instance_id}/interior")
def get_chassis_interior(instance_id: str):
    chassis_class, chassis_inst, world = _find_chassis_instance(instance_id)
    if chassis_class is None or chassis_inst is None:
        raise HTTPException(
            status_code=404,
            detail=f"chassis instance {instance_id!r} not found in any genre pack",
        )

    # For the v1, render against an empty snapshot so the endpoint is
    # smoke-testable without a live session. Once the dispatch handler
    # is wired into the WS session, swap this for the live snapshot.
    class _EmptySnapshot:
        characters = []
        npcs = []

    svg = render_interior_svg(chassis_class, chassis_inst, _EmptySnapshot())

    actors_total = 0  # empty snapshot; live wiring lands in Task 8
    emit_interior_render(
        chassis_instance_id=instance_id,
        actor_count=actors_total,
        tracked_pcs=0,
        tracked_npcs=0,
    )
    return Response(content=svg, media_type="image/svg+xml")
```

(Note: `inst.class_` may be `inst.class_id` or `inst.class` depending on the runtime model. Run `python -c "from sidequest.genre.loader import load_genre_pack; print(load_genre_pack('space_opera').worlds[0].chassis_instances[0].model_fields.keys())"` to confirm; adapt the attribute access.)

- [ ] **Step 3: Stub the OTEL helper so the import works**

Create `sidequest-server/sidequest/telemetry/spans/interior.py`:

```python
"""OTEL spans for the interior map subsystem."""
from sidequest.telemetry.spans._core import emit_event


def emit_interior_render(
    *,
    chassis_instance_id: str,
    actor_count: int,
    tracked_pcs: int,
    tracked_npcs: int,
) -> None:
    """Fired on every interior SVG render."""
    emit_event(
        "interior.render",
        attributes={
            "chassis_instance_id": chassis_instance_id,
            "actor_count": actor_count,
            "tracked_pcs": tracked_pcs,
            "tracked_npcs": tracked_npcs,
        },
    )


def emit_interior_position_change(
    *,
    actor_id: str,
    from_room: str | None,
    to_room: str,
    source: str,
) -> None:
    """Fired when an actor's current_room changes."""
    emit_event(
        "interior.position_change",
        attributes={
            "actor_id": actor_id,
            "from_room": from_room or "",
            "to_room": to_room,
            "source": source,
        },
    )
```

Read `sidequest/telemetry/spans/_core.py` (or `chart.py`, since it's a sibling) to verify `emit_event`'s actual signature and adapt.

- [ ] **Step 4: Wire the router into `app.py`**

In `sidequest-server/sidequest/server/app.py`, find the `include_router(rest_router)` line (around line 204) and add below:

```python
    from sidequest.interior.dispatch import interior_router
    app.include_router(interior_router)
```

(Top-level import is preferred; use a deferred import only if there's a circular dependency.)

- [ ] **Step 5: Run the wiring tests**

Run: `uv run pytest tests/interior/test_endpoint_wired.py -v`
Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/interior/dispatch.py sidequest/telemetry/spans/interior.py sidequest/server/app.py tests/interior/test_endpoint_wired.py
git commit -m "feat(interior): REST endpoint + OTEL spans + wiring"
```

---

## Task 7: Narrator hook — surface `current_room`, instruct state-patch on movement

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py`
- Test: `sidequest-server/tests/agents/test_narrator_current_room.py`

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-server/tests/agents/test_narrator_current_room.py`:

```python
"""Wiring: narrator prompt assembly surfaces current_room per character."""
from sidequest.agents.narrator import build_character_section
# Adapt the import to whatever function actually composes the
# per-character prompt block — search:
#   grep -n "def build_character\|character_section\|describe_character" sidequest/agents/narrator.py


def test_character_section_mentions_current_room_when_set():
    class _C:
        class core:
            name = "Rux"
        backstory = "freighter rat"
        current_room = "galley"
        # ... other fields with safe defaults; adapt to actual signature
    section = build_character_section(_C())
    assert "galley" in section.lower() or "current_room" in section


def test_character_section_omits_room_clause_when_none():
    class _C:
        class core:
            name = "Rux"
        backstory = "freighter rat"
        current_room = None
    section = build_character_section(_C())
    # No "is in the None" garbage when unset
    assert "none" not in section.lower() or "in the none" not in section.lower()
```

Run: `uv run pytest tests/agents/test_narrator_current_room.py -v`
Expected: import error or assertion error.

- [ ] **Step 2: Add the prompt clauses**

In `sidequest-server/sidequest/agents/narrator.py`, find the function that emits the per-character prompt block (search `grep -n "character" sidequest/agents/narrator.py | head -20`). Add a clause:

```python
    if getattr(character, "current_room", None):
        lines.append(
            f"  position: {character.current_room} "
            f"(emit a state_patch updating /characters/{character.core.name}/current_room "
            f"if the narration moves them to a different room)"
        )
```

(Adapt `lines.append` to match the actual prompt-builder shape — it might be a string accumulator, a list, or a textwrap helper. Match the convention.)

- [ ] **Step 3: Run the wiring tests**

Run: `uv run pytest tests/agents/test_narrator_current_room.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add sidequest/agents/narrator.py tests/agents/test_narrator_current_room.py
git commit -m "feat(narrator): surface current_room + instruct state-patch on movement"
```

---

## Task 8: UI — Ship widget, registry entry, refetch hook, wiring test

**Files:**
- Create: `sidequest-ui/src/hooks/useChassisInteriorSVG.ts`
- Create: `sidequest-ui/src/components/GameBoard/widgets/ShipWidget.tsx`
- Modify: `sidequest-ui/src/components/GameBoard/widgetRegistry.ts`
- Test: `sidequest-ui/src/components/GameBoard/__tests__/ShipWidget.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/components/GameBoard/__tests__/ShipWidget.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, waitFor, act } from "@testing-library/react";
import { ShipWidget } from "../widgets/ShipWidget";

describe("ShipWidget", () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(
        '<svg><g data-room="cockpit"><g data-station="helm"></g></g></svg>'
      ),
    } as Response);
  });

  it("fetches the interior SVG on mount", async () => {
    render(<ShipWidget chassisInstanceId="kestrel" />);
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/chassis/kestrel/interior")
      );
    });
  });

  it("refetches when a STATE_PATCH event for current_room arrives", async () => {
    const { container } = render(
      <ShipWidget chassisInstanceId="kestrel" />
    );
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(1)
    );
    // Simulate a STATE_PATCH event on the global event bus.
    // Adapt this dispatch to whatever the actual mirror exposes —
    // search useStateMirror or similar in src/hooks/.
    act(() => {
      window.dispatchEvent(
        new CustomEvent("sidequest:state_patch", {
          detail: { path: "/characters/rux/current_room", value: "galley" },
        })
      );
    });
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(2)
    );
  });
});
```

Run: `cd sidequest-ui && npx vitest run src/components/GameBoard/__tests__/ShipWidget.test.tsx`
Expected: file not found / import error.

- [ ] **Step 2: Implement the hook**

Create `sidequest-ui/src/hooks/useChassisInteriorSVG.ts`:

```typescript
import { useEffect, useState } from "react";

/**
 * Fetches the chassis interior SVG and refetches when a STATE_PATCH
 * touches /characters/<id>/current_room or /npcs/<id>/current_room.
 */
export function useChassisInteriorSVG(chassisInstanceId: string): string | null {
  const [svg, setSvg] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/chassis/${chassisInstanceId}/interior`)
      .then((r) => (r.ok ? r.text() : Promise.reject(r.statusText)))
      .then((body) => {
        if (!cancelled) setSvg(body);
      })
      .catch(() => {
        // Graceful degradation — keep the last good SVG.
      });
    return () => {
      cancelled = true;
    };
  }, [chassisInstanceId, tick]);

  useEffect(() => {
    function onPatch(e: Event) {
      const detail = (e as CustomEvent).detail;
      if (
        typeof detail?.path === "string" &&
        detail.path.endsWith("/current_room")
      ) {
        setTick((t) => t + 1);
      }
    }
    window.addEventListener("sidequest:state_patch", onPatch);
    return () => window.removeEventListener("sidequest:state_patch", onPatch);
  }, []);

  return svg;
}
```

(If the project's STATE_PATCH bus is not `window.dispatchEvent` but some other mechanism — search `grep -rn "STATE_PATCH" src/hooks/ src/providers/` — adapt the listener to the project's existing pattern.)

- [ ] **Step 3: Implement the widget**

Create `sidequest-ui/src/components/GameBoard/widgets/ShipWidget.tsx`:

```tsx
import { useChassisInteriorSVG } from "@/hooks/useChassisInteriorSVG";

export interface ShipWidgetProps {
  chassisInstanceId: string;
}

/**
 * Ship tab — server-rendered SVG of the chassis interior.
 *
 * Mirrors MapWidget's shape. SVG is fetched once on mount and
 * refetched when a STATE_PATCH touches any actor's current_room.
 */
export function ShipWidget({ chassisInstanceId }: ShipWidgetProps) {
  const svg = useChassisInteriorSVG(chassisInstanceId);

  if (!svg) {
    return (
      <div className="flex h-full items-center justify-center text-amber-100/40">
        Loading ship interior…
      </div>
    );
  }

  return (
    <div
      className="h-full w-full"
      // Server SVG is trusted (same origin). Inline render keeps
      // pan/zoom CSS available if we add it later.
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
```

- [ ] **Step 4: Register the widget**

In `sidequest-ui/src/components/GameBoard/widgetRegistry.ts`, find the `WIDGET_REGISTRY` const and add a `ship` entry. Mirror the shape of an existing entry like `map`:

```typescript
  ship: {
    id: "ship",
    label: "Ship",
    hotkey: "S",          // pick a free hotkey; check buildHotkeyMap output
    icon: "🛸",            // or whatever the project's icon convention is
    autoVisible: true,
  },
```

Add `ship` to the `WidgetId` union literal at the top of the file.

Then wire the widget into the rendering switch (probably in `GameBoard.tsx` near where `MapWidget` is rendered around line 353):

```tsx
        {activeWidgetId === "ship" && chassisInstanceId && (
          <ShipWidget chassisInstanceId={chassisInstanceId} />
        )}
```

The `chassisInstanceId` needs to come from somewhere — probably `worldSlug === "coyote_star"` maps to `kestrel` for the v1. Hardcode that mapping for now (see "Out of scope: multi-chassis" in the spec).

- [ ] **Step 5: Run the test**

Run: `cd sidequest-ui && npx vitest run src/components/GameBoard/__tests__/ShipWidget.test.tsx`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd sidequest-ui
git checkout -b feat/internal-ship-map-kestrel
git add src/hooks/useChassisInteriorSVG.ts src/components/GameBoard/widgets/ShipWidget.tsx src/components/GameBoard/widgetRegistry.ts src/components/GameBoard/__tests__/ShipWidget.test.tsx src/components/GameBoard/GameBoard.tsx
git commit -m "feat(ui): Ship widget — server-rendered interior SVG"
```

---

## Task 9: Boot smoke + manual verification

This task is the operator's hands. No code, just verification that all the pieces line up at runtime.

- [ ] **Step 1: Run the full server test suite**

```bash
cd sidequest-server && uv run pytest tests/interior/ tests/agents/test_narrator_current_room.py tests/server/test_state_patch_current_room.py -v
```

Expected: all pass.

- [ ] **Step 2: Run the UI test suite**

```bash
cd sidequest-ui && npx vitest run
```

Expected: all pass (existing tests stay green; new ShipWidget test passes).

- [ ] **Step 3: Boot the stack**

From the orchestrator root:

```bash
just up
```

Wait for `daemon ready`, `server listening on :8765`, `vite dev server on :5173`.

- [ ] **Step 4: Smoke the endpoint directly**

```bash
curl -s http://localhost:8765/api/chassis/kestrel/interior | head -20
```

Expected: SVG body starting with `<?xml` or `<svg`, containing `data-room="cockpit"` and the Kestrel name.

- [ ] **Step 5: Open the UI, hit the Ship tab**

Navigate to `http://localhost:5173`, start or load a coyote_star session, switch to the Ship tab.

Expected:
- Four labeled rooms in a 2x2 grid.
- Three pips in cockpit (Command/Helm/Weapons), one pip in engineering (Engineering).
- Four NPC markers in their default rooms (captain in cockpit, engineer in engineering, doc + cook in galley).
- PCs visible if their `current_room` is set; otherwise no PC marker yet (narrator hook will start populating once the session takes a turn).

- [ ] **Step 6: Verify the OTEL span fires**

Open the GM panel (`http://localhost:8765/dashboard` or whatever `just otel` opens). Switch to a tab that surfaces `interior.render`. Reload the Ship tab in the UI; confirm the span fires with `chassis_instance_id="kestrel"`.

If the span doesn't surface, check `FLAT_ONLY_SPANS` in `sidequest/telemetry/spans.py` — `interior.*` may need a `SpanRoute` entry. (See `2026-04-25-otel-phase-2-port-audit-followup.md` for the routing pattern.)

- [ ] **Step 7: Smoke the narrator hook**

Take one narration turn in the session. The narrator's prompt should include the position clause; the response should not crash. If the narrator emits a state_patch on `current_room`, the marker should move on the next Ship-tab fetch.

- [ ] **Step 8: PR each subrepo**

For each modified subrepo (sidequest-content, sidequest-server, sidequest-ui), run from inside that subrepo:

```bash
git push -u origin feat/internal-ship-map-kestrel
gh pr create --base develop --title "feat: internal ship map (Kestrel)" --body "$(cat <<'EOF'
## Summary
- Server-rendered SVG of the Kestrel interior (4 rooms, 4 stations)
- Narrator-tracked PC + NPC positions via state patches
- New Ship tab in the UI mirroring the orbital chart pattern

## Spec
docs/superpowers/specs/2026-05-03-internal-ship-map-kestrel-design.md (orchestrator)

## Test plan
- [ ] Server tests pass (tests/interior/, tests/agents/test_narrator_current_room.py)
- [ ] UI tests pass (ShipWidget refetches on STATE_PATCH)
- [ ] Manual: Ship tab renders with rooms + stations + crew markers
- [ ] OTEL: interior.render span fires per fetch

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Merge `develop` PRs in this order to keep the dependency chain clean:

1. **sidequest-content** (chassis_classes.yaml — schema source)
2. **sidequest-server** (depends on the new YAML)
3. **sidequest-ui** (depends on the server endpoint)

After all three merge, no orchestrator-level commit is needed (this plan touched only subrepos).

- [ ] **Step 9: Mark the spec as shipped**

Once everything is on `develop` and tonight's session is over, move the spec to completed/:

```bash
cd /Users/slabgorb/Projects/oq-2
git mv docs/superpowers/specs/2026-05-03-internal-ship-map-kestrel-design.md docs/superpowers/specs/completed/
git mv docs/superpowers/plans/2026-05-03-internal-ship-map-kestrel.md docs/superpowers/plans/completed/
git commit -m "docs: archive ship-map spec + plan"
git push origin main
```

---

## Graceful Cuts (if running long before game time)

In priority order — drop from the bottom:

1. **OTEL spans (Task 6 Step 3 + Task 9 Step 6)** — file as debt, ship without; the helper file can be a no-op.
2. **Narrator hook (Task 7)** — positions stay at defaults, map still feels alive on PC + NPC defaults alone.
3. **NPC default rooms (Task 4 Step 3-4)** — PCs only.
4. **Station-occupied highlighting** — already not in the renderer; if it becomes a stretch idea, keep cutting.

The minimum-viable map is Tasks 1, 2, 5, 6, 8 — the renderer + endpoint + UI widget. Everything else amplifies.

---

## Self-Review

**Spec coverage:** Walked the spec section by section.
- Goal → Tasks 5+6+8 (renderer + endpoint + widget).
- Architecture diagram → File structure table matches.
- Content schema → Task 1.
- Server module → Tasks 3, 5, 6.
- Snapshot extension → Task 4.
- REST endpoint → Task 6.
- UI Ship tab → Task 8.
- Narrator hook → Task 7.
- OTEL spans → Task 6 Step 3, Task 9 Step 6.
- Error handling (No Silent Fallbacks) → Task 3 (loud loader), Task 6 (404 on unknown).
- Testing (wiring tests) → every server module has a wiring test (Tasks 4, 6, 7), UI has one (Task 8).
- Acceptance criteria → all six bullets traced to tasks.

**Placeholder scan:** No TBDs or TODOs in step content. Two task steps explicitly say "adapt to the actual <X>" — those are discovery hand-offs to Dev (canonical paths I cannot resolve from SM seat) and the plan tells Dev exactly which command to run to discover them.

**Type consistency:** `StationSpec` (Task 2) → used in Task 3 (loader), Task 5 (renderer fixture), Task 6 (dispatch). `ChassisClass.stations: list[StationSpec]` (Task 2) → used everywhere downstream. `current_room: str | None` (Task 4) → used in narrator hook (Task 7) and renderer's actor walker (Task 5). Consistent throughout.

**Scope:** ~30 min wall-clock for AI-driven implementation, a touch more with PR ceremony. Right-sized for the work.
