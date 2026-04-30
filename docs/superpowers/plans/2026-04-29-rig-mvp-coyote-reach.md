# Rig MVP — Coyote Star Vertical Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Kestrel speaking with bond-tier-correct name-forms in Coyote Star, with `the_tea_brew` running end-to-end (bond delta, three OTEL spans, GM-panel visibility, one cliché-judge hook).

**Architecture:** New chassis-state container (own pydantic + game-state + projection into `npc_registry`); voice resolver wired into the narrator prompt; bond mutation path that emits the three slice spans; one new auto-fire confrontation appended to the existing world `confrontations.yaml`. Reuses `LedgerBar`-shaped patterns from magic, `NpcRegistryEntry` for narrator continuity, `watcher_hub` for OTEL emission, `room_movement` post-hook for the auto-fire trigger.

**Tech Stack:** Python 3.12 (uv), Pydantic v2, FastAPI, pytest, OTEL spans via `sidequest.telemetry`. Content YAML in `sidequest-content/`. Server code in `sidequest-server/`. Doc edits in orchestrator repo.

**Spec:** `docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md`

---

## Cross-Spec Dependency — Magic Plan Phase 5

The auto-fire / outcome-processing pipeline for the world's `confrontations.yaml` (where this plan's `the_tea_brew` lives) is owned by **Phase 5 — Confrontations Wired** of `docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md`. Phases 1–3 of that plan have shipped (commit `ee5a5a2`); **Phase 5 has not**.

This plan is split into three phases that respect that boundary:

- **Phase A — Chassis state, spans, content (independent)** — Tasks 1–13. Ships immediately, no dependency on magic Phase 5. Produces a chassis registry, voice resolver, OTEL spans, the two new YAML files, and narrator integration. Kestrel speaks with bond-tier-correct name-forms even though `the_tea_brew` cannot fire yet.
- **Phase B — Doc additions (independent)** — Task 14. `confrontation-advancement.md` gets the three new outputs + tone-axis field. Lands without code dependency.
- **Phase C — `the_tea_brew` wiring (depends on magic Phase 5)** — Tasks 15–19. Auto-fire trigger, outcome handler, integration test, cliché-judge hook. Hold until magic Phase 5 has shipped.

If the operator wants the slice's full demo path now, magic Phase 5 must ship first. If they want partial value now, Phase A + B alone gets Kestrel speaking — bond just doesn't move.

---

## File structure

### Created

| Path | Responsibility |
|---|---|
| `sidequest-content/genre_packs/space_opera/chassis_classes.yaml` | Genre-layer chassis catalog (one class: `voidborn_freighter`) |
| `sidequest-content/genre_packs/space_opera/worlds/coyote_star/rigs.yaml` | World-layer chassis instances (one: Kestrel) |
| `sidequest-server/sidequest/genre/models/chassis.py` | Pydantic for `chassis_classes.yaml` (genre layer) |
| `sidequest-server/sidequest/genre/models/rigs_world.py` | Pydantic for `rigs.yaml` (world layer) |
| `sidequest-server/sidequest/game/chassis.py` | Game-state `ChassisInstance`, bond ledger, `apply_bond_event`, `apply_chassis_lineage_intimate`, tier derivation, `npc_registry` projection |
| `sidequest-server/sidequest/agents/subsystems/chassis_voice.py` | `resolve_chassis_name_form(chassis, character)` |
| `sidequest-server/sidequest/telemetry/spans/rig.py` | Three span emitters: `bond_event`, `voice_register_change`, `confrontation_outcome` |
| `sidequest-server/tests/genre/test_chassis_class_load.py` | Genre pydantic loads sample YAML |
| `sidequest-server/tests/genre/test_rigs_world_load.py` | World pydantic loads sample YAML |
| `sidequest-server/tests/game/test_chassis_bond.py` | Bond mutation + tier derivation |
| `sidequest-server/tests/agents/test_chassis_voice.py` | Voice resolver name-form output |
| `sidequest-server/tests/telemetry/test_rig_spans.py` | Span emit + attribute set |
| `sidequest-server/tests/integration/test_kestrel_chassis_registry.py` | World-load → chassis_registry → projection |
| `sidequest-server/tests/integration/test_kestrel_tea_brew.py` | End-to-end Galley fixture (Phase C) |

### Modified

| Path | Change |
|---|---|
| `sidequest-content/genre_packs/space_opera/worlds/coyote_star/confrontations.yaml` | Append `the_tea_brew` entry |
| `docs/design/confrontation-advancement.md` | Three new outputs + optional `register` field |
| `sidequest-server/sidequest/genre/loader.py` | `load_chassis_classes(genre_path)`; integrate into `load_genre_pack` |
| `sidequest-server/sidequest/game/world_materialization.py` | Load `rigs.yaml`, materialize `chassis_registry`, project into `npc_registry` |
| `sidequest-server/sidequest/game/session.py` | Add `chassis_registry` field on session/snapshot |
| `sidequest-server/sidequest/agents/prompt_framework/core.py` | Pull chassis voice into chassis-as-speaker prompt section |
| `sidequest-server/sidequest/game/room_movement.py` | Post-move hook: eligible-confrontation check (Phase C) |
| `sidequest-server/sidequest/server/dispatch/confrontation.py` | `the_tea_brew` outcome → bond + lineage outputs (Phase C) |
| `sidequest-server/sidequest/telemetry/spans/__init__.py` | Star-import `from .rig import *` |
| `docs/design/rig-taxonomy.md` (cliché-judge section) | Note hook #7 active in slice (Phase C) |

---

## Phase A — Chassis state, spans, content (independent)

### Task 1: Genre-layer pydantic for chassis_classes.yaml

**Files:**
- Create: `sidequest-server/sidequest/genre/models/chassis.py`
- Test: `sidequest-server/tests/genre/test_chassis_class_load.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/genre/test_chassis_class_load.py
"""Genre-layer chassis pydantic loads sample YAML."""
from __future__ import annotations

import textwrap

import yaml

from sidequest.genre.models.chassis import ChassisClassesConfig


SAMPLE = textwrap.dedent("""
    version: "0.1.0"
    genre: space_opera
    classes:
      - id: voidborn_freighter
        display_name: "Voidborn Freighter"
        class: freighter
        provenance: voidborn_built
        scale_band: vehicular
        crew_model: flexible_roles
        embodiment_model: singular
        crew_awareness: surface
        psi_resonance:
          default: receptive
          amplifies: [void_singing]
        default_voice:
          default_register: dry_warm
          vocal_tics: ["theatrical sigh"]
          silence_register: approving_or_sulking_context_dependent
          name_forms_by_bond_tier:
            severed: "Pilot"
            hostile: "Pilot"
            strained: "Pilot"
            neutral: "Pilot"
            familiar: "Mr. {last_name}"
            trusted: "{first_name}"
            fused: "{nickname}"
        interior_rooms:
          - id: galley
            display_name: "Galley"
            bond_eligible_for: [the_tea_brew]
        crew_roles:
          - id: pilot
            operates_hardpoints: "*"
            bond_eligible: true
            default_seat: galley
""")


def test_chassis_classes_yaml_loads() -> None:
    cfg = ChassisClassesConfig.model_validate(yaml.safe_load(SAMPLE))
    assert cfg.genre == "space_opera"
    assert len(cfg.classes) == 1
    cls = cfg.classes[0]
    assert cls.id == "voidborn_freighter"
    assert cls.crew_model == "flexible_roles"
    assert cls.default_voice.name_forms_by_bond_tier["trusted"] == "{first_name}"
    assert cls.interior_rooms[0].id == "galley"


def test_unknown_crew_model_rejected() -> None:
    bad = yaml.safe_load(SAMPLE)
    bad["classes"][0]["crew_model"] = "nonsense"
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ChassisClassesConfig.model_validate(bad)
```

- [ ] **Step 2: Run test to confirm failure**

```bash
cd sidequest-server && uv run pytest tests/genre/test_chassis_class_load.py -v
```

Expected: ImportError — `sidequest.genre.models.chassis` does not exist.

- [ ] **Step 3: Implement**

```python
# sidequest-server/sidequest/genre/models/chassis.py
"""Genre-layer chassis catalog pydantic models.

Mirrors `chassis_classes.yaml` shape per docs/design/rig-taxonomy.md.
Slice scope: only fields used by Coyote Star's voidborn_freighter +
the_tea_brew. Hardpoints, chassis_death, full provenance vocabulary
are deferred to follow-on specs.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CrewModel = Literal["single_pilot", "strict_roles", "flexible_roles"]
EmbodimentModel = Literal["singular", "crew_only", "ancillary", "swarm"]
CrewAwareness = Literal["none", "surface", "biometric", "interior", "total"]
ScaleBand = Literal[
    "personal", "vehicular", "capital_ship", "station_class"
]
BondTier = Literal[
    "severed", "hostile", "strained", "neutral",
    "familiar", "trusted", "fused",
]


class ChassisVoiceSpec(BaseModel):
    model_config = {"extra": "forbid"}
    default_register: str
    vocal_tics: list[str] = Field(default_factory=list)
    silence_register: str | None = None
    name_forms_by_bond_tier: dict[BondTier, str]


class PsiResonanceSpec(BaseModel):
    model_config = {"extra": "forbid"}
    default: Literal["receptive", "dampening", "neutral", "incomprehensible"]
    amplifies: list[str] = Field(default_factory=list)


class InteriorRoomSpec(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    display_name: str
    narrative_register: str | None = None
    default_occupants: list[str] = Field(default_factory=list)
    bond_eligible_for: list[str] = Field(default_factory=list)


class CrewRoleSpec(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    operates_hardpoints: str | list[str] = "*"
    bond_eligible: bool = False
    default_seat: str | None = None


class ChassisClass(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    id: str
    display_name: str
    # Field name conflict with python keyword: alias.
    chassis_class: str = Field(alias="class")
    provenance: str
    scale_band: ScaleBand
    crew_model: CrewModel
    embodiment_model: EmbodimentModel = "singular"
    crew_awareness: CrewAwareness = "none"
    psi_resonance: PsiResonanceSpec | None = None
    default_voice: ChassisVoiceSpec | None = None
    interior_rooms: list[InteriorRoomSpec] = Field(default_factory=list)
    crew_roles: list[CrewRoleSpec] = Field(default_factory=list)
    # Deferred per slice: hardpoints, chassis_death, ancillary_*.


class ChassisClassesConfig(BaseModel):
    model_config = {"extra": "forbid"}
    version: str
    genre: str
    classes: list[ChassisClass]
```

- [ ] **Step 4: Run test to confirm pass**

```bash
cd sidequest-server && uv run pytest tests/genre/test_chassis_class_load.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Lint**

```bash
cd sidequest-server && uv run ruff check sidequest/genre/models/chassis.py tests/genre/test_chassis_class_load.py
```

Expected: All checks passed.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/chassis.py tests/genre/test_chassis_class_load.py
git commit -m "feat(rig): genre-layer pydantic for chassis_classes.yaml

Slice scope only — voidborn_freighter fields. Hardpoints, chassis_death,
full provenance enum deferred. Spec: docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md"
```

---

### Task 2: World-layer pydantic for rigs.yaml

**Files:**
- Create: `sidequest-server/sidequest/genre/models/rigs_world.py`
- Test: `sidequest-server/tests/genre/test_rigs_world_load.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/genre/test_rigs_world_load.py
"""World-layer rigs pydantic loads sample YAML."""
from __future__ import annotations

import textwrap

import yaml

from sidequest.genre.models.rigs_world import RigsWorldConfig


SAMPLE = textwrap.dedent("""
    version: "0.1.0"
    world: coyote_star
    genre: space_opera
    chassis_instances:
      - id: kestrel
        name: "Kestrel"
        class: voidborn_freighter
        OCEAN: { O: 0.6, C: 0.7, E: 0.4, A: 0.5, N: 0.5 }
        voice:
          vocal_tics: ["dry as bonemeal"]
        interior_rooms: [cockpit, galley]
        bond_seeds:
          - character_role: player_character
            bond_strength_character_to_chassis: 0.45
            bond_strength_chassis_to_character: 0.45
            bond_tier_character: trusted
            bond_tier_chassis: trusted
            history_seeds:
              - "muscle memory from three jumps' worth of patch kits"
""")


def test_rigs_yaml_loads() -> None:
    cfg = RigsWorldConfig.model_validate(yaml.safe_load(SAMPLE))
    assert cfg.world == "coyote_star"
    assert len(cfg.chassis_instances) == 1
    inst = cfg.chassis_instances[0]
    assert inst.id == "kestrel"
    assert inst.bond_seeds[0].bond_tier_chassis == "trusted"
    assert inst.OCEAN.O == 0.6
```

- [ ] **Step 2: Run test to confirm failure**

```bash
cd sidequest-server && uv run pytest tests/genre/test_rigs_world_load.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# sidequest-server/sidequest/genre/models/rigs_world.py
"""World-layer rigs.yaml pydantic.

Each chassis instance picks a class from the genre's chassis_classes.yaml
and adds named state. Resolution into a runtime ChassisInstance happens
at world-load (sidequest/game/world_materialization.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from sidequest.genre.models.chassis import BondTier, ChassisVoiceSpec


class OceanScores(BaseModel):
    model_config = {"extra": "forbid"}
    O: float = 0.5
    C: float = 0.5
    E: float = 0.5
    A: float = 0.5
    N: float = 0.5


class BondSeed(BaseModel):
    model_config = {"extra": "forbid"}
    # `character_role` is a placeholder resolved at chargen time.
    # Currently only "player_character" is recognized; multi-PC slots later.
    character_role: str
    bond_strength_character_to_chassis: float = 0.0
    bond_strength_chassis_to_character: float = 0.0
    bond_tier_character: BondTier = "neutral"
    bond_tier_chassis: BondTier = "neutral"
    history_seeds: list[str] = Field(default_factory=list)


class ChassisInstanceConfig(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    id: str
    name: str
    chassis_class_id: str = Field(alias="class")
    OCEAN: OceanScores = Field(default_factory=OceanScores)
    voice: ChassisVoiceSpec | None = None
    # Slice scope: list of room ids the instance exposes (subset of class).
    interior_rooms: list[str] = Field(default_factory=list)
    bond_seeds: list[BondSeed] = Field(default_factory=list)
    # Deferred: subsystems, damage_history, registration, prior_captains.


class RigsWorldConfig(BaseModel):
    model_config = {"extra": "forbid"}
    version: str
    world: str
    genre: str
    chassis_instances: list[ChassisInstanceConfig]
```

- [ ] **Step 4: Run test to confirm pass**

```bash
cd sidequest-server && uv run pytest tests/genre/test_rigs_world_load.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/genre/models/rigs_world.py tests/genre/test_rigs_world_load.py
git add sidequest/genre/models/rigs_world.py tests/genre/test_rigs_world_load.py
git commit -m "feat(rig): world-layer pydantic for rigs.yaml"
```

---

### Task 3: Game-state chassis module — registry, bond ledger, tier derivation

**Files:**
- Create: `sidequest-server/sidequest/game/chassis.py`
- Test: `sidequest-server/tests/game/test_chassis_bond.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/game/test_chassis_bond.py
"""Bond mutation, tier derivation, lineage append."""
from __future__ import annotations

from sidequest.game.chassis import (
    BondLedgerEntry,
    BondHistoryEvent,
    ChassisInstance,
    ChassisLineageEntry,
    apply_bond_event,
    apply_chassis_lineage_intimate,
    derive_bond_tier,
)


def test_derive_bond_tier_thresholds() -> None:
    assert derive_bond_tier(-0.95) == "severed"
    assert derive_bond_tier(-0.6) == "hostile"
    assert derive_bond_tier(-0.2) == "strained"
    assert derive_bond_tier(0.0) == "neutral"
    assert derive_bond_tier(0.2) == "familiar"
    assert derive_bond_tier(0.5) == "trusted"
    assert derive_bond_tier(0.9) == "fused"


def _kestrel_with_player_bond() -> ChassisInstance:
    return ChassisInstance(
        id="kestrel",
        name="Kestrel",
        class_id="voidborn_freighter",
        bond_ledger=[
            BondLedgerEntry(
                character_id="player_character_1",
                bond_strength_character_to_chassis=0.45,
                bond_strength_chassis_to_character=0.45,
                bond_tier_character="trusted",
                bond_tier_chassis="trusted",
                history=[],
            ),
        ],
    )


def test_apply_bond_event_updates_strength_and_tier() -> None:
    chassis = _kestrel_with_player_bond()
    result = apply_bond_event(
        chassis=chassis,
        character_id="player_character_1",
        delta_character=0.04,
        delta_chassis=0.06,
        reason="the_tea_brew clear_win",
        confrontation_id="the_tea_brew",
        turn_id=12,
    )
    entry = chassis.bond_ledger[0]
    assert entry.bond_strength_chassis_to_character == 0.51
    assert entry.bond_strength_character_to_chassis == 0.49
    assert entry.bond_tier_chassis == "trusted"  # no boundary crossed yet
    assert entry.bond_tier_character == "trusted"
    assert len(entry.history) == 1
    assert entry.history[0].reason == "the_tea_brew clear_win"
    assert result.tier_chassis_crossed is False


def test_apply_bond_event_detects_tier_crossing() -> None:
    chassis = _kestrel_with_player_bond()
    chassis.bond_ledger[0].bond_strength_chassis_to_character = 0.83
    chassis.bond_ledger[0].bond_strength_character_to_chassis = 0.83
    result = apply_bond_event(
        chassis=chassis,
        character_id="player_character_1",
        delta_character=0.05,
        delta_chassis=0.05,
        reason="threshold cross test",
        confrontation_id="the_tea_brew",
        turn_id=20,
    )
    entry = chassis.bond_ledger[0]
    assert entry.bond_tier_chassis == "fused"
    assert entry.bond_tier_character == "fused"
    assert result.tier_chassis_crossed is True
    assert result.tier_character_crossed is True


def test_apply_chassis_lineage_intimate_appends() -> None:
    chassis = _kestrel_with_player_bond()
    apply_chassis_lineage_intimate(
        chassis=chassis,
        narrative_seed="the captain's tea cup left for the ghost of the previous captain",
        turn_id=12,
        confrontation_id="the_tea_brew",
    )
    assert len(chassis.lineage) == 1
    assert chassis.lineage[0].kind == "intimate"
    assert chassis.lineage[0].turn_id == 12
```

- [ ] **Step 2: Run test to confirm failure**

```bash
cd sidequest-server && uv run pytest tests/game/test_chassis_bond.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# sidequest-server/sidequest/game/chassis.py
"""Game-state chassis registry — chassis as first-class entities, not inventory.

Per docs/design/rig-taxonomy.md locked decision α (sibling framework) and
this slice's spec decision 3 (own container, projected into npc_registry).

Slice scope: ChassisInstance + bond ledger + lineage + bond mutation +
tier derivation + npc_registry projection. Hardpoints, subsystems,
damage_history, registration are deferred fields (not authored here).
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from sidequest.genre.models.chassis import BondTier, ChassisVoiceSpec
from sidequest.genre.models.rigs_world import OceanScores


# --- Tier derivation -----------------------------------------------------

# Slice-frozen thresholds. Tuned to the playthrough's tier-form ladder.
_TIER_THRESHOLDS: list[tuple[float, BondTier]] = [
    (-0.85, "severed"),
    (-0.45, "hostile"),
    (-0.10, "strained"),
    (0.10, "neutral"),
    (0.40, "familiar"),
    (0.80, "trusted"),
    (1.01, "fused"),  # > 0.80 lands here; sentinel ceiling
]


def derive_bond_tier(strength: float) -> BondTier:
    """Map a bond_strength scalar in [-1.0, 1.0] to a discrete tier."""
    for ceiling, tier in _TIER_THRESHOLDS:
        if strength < ceiling:
            return tier
    return "fused"


# --- State models --------------------------------------------------------


class BondHistoryEvent(BaseModel):
    model_config = {"extra": "forbid"}
    turn_id: int
    delta_character: float
    delta_chassis: float
    reason: str
    confrontation_id: str | None = None


class BondLedgerEntry(BaseModel):
    model_config = {"extra": "forbid"}
    character_id: str
    bond_strength_character_to_chassis: float = 0.0
    bond_strength_chassis_to_character: float = 0.0
    bond_tier_character: BondTier = "neutral"
    bond_tier_chassis: BondTier = "neutral"
    history: list[BondHistoryEvent] = Field(default_factory=list)


class ChassisLineageEntry(BaseModel):
    model_config = {"extra": "forbid"}
    turn_id: int
    kind: str  # "intimate" | "dramatic"
    narrative_seed: str
    confrontation_id: str | None = None


class ChassisInstance(BaseModel):
    """Live chassis state. Source of truth; npc_registry has a projection."""

    model_config = {"extra": "forbid"}

    id: str
    name: str
    class_id: str
    OCEAN: OceanScores = Field(default_factory=OceanScores)
    voice: ChassisVoiceSpec | None = None
    interior_rooms: list[str] = Field(default_factory=list)
    bond_ledger: list[BondLedgerEntry] = Field(default_factory=list)
    lineage: list[ChassisLineageEntry] = Field(default_factory=list)

    def bond_for(self, character_id: str) -> BondLedgerEntry | None:
        for entry in self.bond_ledger:
            if entry.character_id == character_id:
                return entry
        return None


# --- Mutation API --------------------------------------------------------


@dataclass
class BondEventResult:
    tier_character_before: BondTier
    tier_character_after: BondTier
    tier_chassis_before: BondTier
    tier_chassis_after: BondTier
    tier_character_crossed: bool
    tier_chassis_crossed: bool


def apply_bond_event(
    *,
    chassis: ChassisInstance,
    character_id: str,
    delta_character: float,
    delta_chassis: float,
    reason: str,
    confrontation_id: str | None,
    turn_id: int,
) -> BondEventResult:
    """Mutate the bond ledger; return tier-crossing info for the caller.

    Caller (e.g. confrontation outcome handler) is responsible for emitting
    the rig.bond_event span using the returned tier metadata. Span emission
    is intentionally NOT done in-line so unit tests don't pull in the
    OTEL exporter (per existing magic plugin pattern).
    """
    entry = chassis.bond_for(character_id)
    if entry is None:
        # CLAUDE.md no-silent-fallback: caller is expected to seed bond
        # at world-load. Missing entry is a bug, not a default-fill case.
        raise ValueError(
            f"chassis {chassis.id!r} has no bond ledger entry for "
            f"character {character_id!r} — was world-load bond_seed run?"
        )

    tier_char_before = entry.bond_tier_character
    tier_chassis_before = entry.bond_tier_chassis

    entry.bond_strength_character_to_chassis = max(
        -1.0,
        min(1.0, entry.bond_strength_character_to_chassis + delta_character),
    )
    entry.bond_strength_chassis_to_character = max(
        -1.0,
        min(1.0, entry.bond_strength_chassis_to_character + delta_chassis),
    )

    entry.bond_tier_character = derive_bond_tier(
        entry.bond_strength_character_to_chassis
    )
    entry.bond_tier_chassis = derive_bond_tier(
        entry.bond_strength_chassis_to_character
    )

    entry.history.append(
        BondHistoryEvent(
            turn_id=turn_id,
            delta_character=delta_character,
            delta_chassis=delta_chassis,
            reason=reason,
            confrontation_id=confrontation_id,
        )
    )

    return BondEventResult(
        tier_character_before=tier_char_before,
        tier_character_after=entry.bond_tier_character,
        tier_chassis_before=tier_chassis_before,
        tier_chassis_after=entry.bond_tier_chassis,
        tier_character_crossed=(
            tier_char_before != entry.bond_tier_character
        ),
        tier_chassis_crossed=(
            tier_chassis_before != entry.bond_tier_chassis
        ),
    )


def apply_chassis_lineage_intimate(
    *,
    chassis: ChassisInstance,
    narrative_seed: str,
    turn_id: int,
    confrontation_id: str | None,
) -> None:
    chassis.lineage.append(
        ChassisLineageEntry(
            turn_id=turn_id,
            kind="intimate",
            narrative_seed=narrative_seed,
            confrontation_id=confrontation_id,
        )
    )
```

- [ ] **Step 4: Run test**

```bash
cd sidequest-server && uv run pytest tests/game/test_chassis_bond.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/game/chassis.py tests/game/test_chassis_bond.py
git add sidequest/game/chassis.py tests/game/test_chassis_bond.py
git commit -m "feat(rig): chassis state — registry, bond ledger, tier derivation, lineage

Slice scope: ChassisInstance, BondLedgerEntry, BondHistoryEvent,
ChassisLineageEntry, derive_bond_tier, apply_bond_event,
apply_chassis_lineage_intimate. Hardpoints/subsystems/damage_history
deferred."
```

---

### Task 4: rig.* OTEL span emitters

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/rig.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py`
- Test: `sidequest-server/tests/telemetry/test_rig_spans.py`

- [ ] **Step 1: Confirm existing span pattern**

```bash
cat sidequest-server/sidequest/telemetry/spans/magic.py | head -80
```

Read this output. The new `rig.py` mirrors its constant declarations + helper signatures.

- [ ] **Step 2: Write the failing test**

```python
# sidequest-server/tests/telemetry/test_rig_spans.py
"""rig.* span emitters fire with the slice's three constant names + attrs."""
from __future__ import annotations

from sidequest.telemetry.spans import (
    SPAN_RIG_BOND_EVENT,
    SPAN_RIG_CONFRONTATION_OUTCOME,
    SPAN_RIG_VOICE_REGISTER_CHANGE,
    emit_rig_bond_event,
    emit_rig_confrontation_outcome,
    emit_rig_voice_register_change,
)
from tests._helpers.span_capture import captured_spans  # existing helper


def test_emit_rig_bond_event_fires_with_attrs() -> None:
    with captured_spans() as spans:
        emit_rig_bond_event(
            chassis_id="kestrel",
            actor_id="player_character_1",
            side="both",
            delta_character=0.04,
            delta_chassis=0.06,
            tier_character_before="trusted",
            tier_character_after="trusted",
            tier_chassis_before="trusted",
            tier_chassis_after="trusted",
            confrontation_id="the_tea_brew",
            register="intimate",
        )
    matching = [s for s in spans if s.name == SPAN_RIG_BOND_EVENT]
    assert len(matching) == 1
    attrs = matching[0].attributes
    assert attrs["chassis_id"] == "kestrel"
    assert attrs["delta_chassis"] == 0.06
    assert attrs["register"] == "intimate"


def test_emit_rig_voice_register_change_fires() -> None:
    with captured_spans() as spans:
        emit_rig_voice_register_change(
            chassis_id="kestrel",
            actor_id="player_character_1",
            register_before="trusted",
            register_after="fused",
            triggering_event="the_tea_brew",
        )
    matching = [s for s in spans if s.name == SPAN_RIG_VOICE_REGISTER_CHANGE]
    assert len(matching) == 1
    assert matching[0].attributes["register_after"] == "fused"


def test_emit_rig_confrontation_outcome_fires() -> None:
    with captured_spans() as spans:
        emit_rig_confrontation_outcome(
            chassis_id="kestrel",
            confrontation_id="the_tea_brew",
            register="intimate",
            branch="clear_win",
            outputs=["bond_strength_growth_via_intimacy", "chassis_lineage_intimate"],
        )
    matching = [s for s in spans if s.name == SPAN_RIG_CONFRONTATION_OUTCOME]
    assert len(matching) == 1
    assert matching[0].attributes["branch"] == "clear_win"
    assert "bond_strength_growth_via_intimacy" in matching[0].attributes["outputs"]
```

(If `tests/_helpers/span_capture.py:captured_spans` does not exist, replace its import with whatever the tests/ directory's existing span-capture helper is — `grep -rn "captured_spans\|InMemorySpanExporter" sidequest-server/tests/`. The Phase 2 magic-system commits added in-memory capture infrastructure; reuse it.)

- [ ] **Step 3: Run test to confirm failure**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_rig_spans.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement the spans module**

```python
# sidequest-server/sidequest/telemetry/spans/rig.py
"""rig.* OTEL span constants + emitters for the chassis framework.

Slice scope: three emitters. The taxonomy declares ten more; they ship
with their producing subsystems (subsystem install/remove with hardpoints;
damage_resolution with dogfight; ancillary_loss with ancillary support; etc.).
"""
from __future__ import annotations

from sidequest.telemetry.spans._core import FLAT_ONLY_SPANS, _SpanLike

SPAN_RIG_BOND_EVENT = "rig.bond_event"
SPAN_RIG_VOICE_REGISTER_CHANGE = "rig.voice_register_change"
SPAN_RIG_CONFRONTATION_OUTCOME = "rig.confrontation_outcome"

# These spans are not part of any larger trace tree — they fire on
# state mutation and are read flat by the GM panel.
FLAT_ONLY_SPANS.update({
    SPAN_RIG_BOND_EVENT,
    SPAN_RIG_VOICE_REGISTER_CHANGE,
    SPAN_RIG_CONFRONTATION_OUTCOME,
})


def emit_rig_bond_event(
    *,
    chassis_id: str,
    actor_id: str,
    side: str,  # "character_to_chassis" | "chassis_to_character" | "both"
    delta_character: float,
    delta_chassis: float,
    tier_character_before: str,
    tier_character_after: str,
    tier_chassis_before: str,
    tier_chassis_after: str,
    confrontation_id: str | None,
    register: str,
) -> None:
    with _SpanLike.open(SPAN_RIG_BOND_EVENT) as span:
        span.set_attribute("chassis_id", chassis_id)
        span.set_attribute("actor_id", actor_id)
        span.set_attribute("side", side)
        span.set_attribute("delta_character", delta_character)
        span.set_attribute("delta_chassis", delta_chassis)
        span.set_attribute("tier_character_before", tier_character_before)
        span.set_attribute("tier_character_after", tier_character_after)
        span.set_attribute("tier_chassis_before", tier_chassis_before)
        span.set_attribute("tier_chassis_after", tier_chassis_after)
        if confrontation_id is not None:
            span.set_attribute("confrontation_id", confrontation_id)
        span.set_attribute("register", register)


def emit_rig_voice_register_change(
    *,
    chassis_id: str,
    actor_id: str,
    register_before: str,
    register_after: str,
    triggering_event: str,
) -> None:
    with _SpanLike.open(SPAN_RIG_VOICE_REGISTER_CHANGE) as span:
        span.set_attribute("chassis_id", chassis_id)
        span.set_attribute("actor_id", actor_id)
        span.set_attribute("register_before", register_before)
        span.set_attribute("register_after", register_after)
        span.set_attribute("triggering_event", triggering_event)


def emit_rig_confrontation_outcome(
    *,
    chassis_id: str,
    confrontation_id: str,
    register: str,
    branch: str,
    outputs: list[str],
) -> None:
    with _SpanLike.open(SPAN_RIG_CONFRONTATION_OUTCOME) as span:
        span.set_attribute("chassis_id", chassis_id)
        span.set_attribute("confrontation_id", confrontation_id)
        span.set_attribute("register", register)
        span.set_attribute("branch", branch)
        # OTEL attribute values must be primitives or arrays of primitives.
        span.set_attribute("outputs", list(outputs))
```

(If the actual `_SpanLike.open` shape differs from the magic spans pattern, mirror exactly what `sidequest/telemetry/spans/magic.py` does — that file is the canonical reference for telemetry helpers in this codebase.)

- [ ] **Step 5: Wire into spans __init__.py**

Edit `sidequest-server/sidequest/telemetry/spans/__init__.py` — find the section with star-imports for existing domains (e.g. `from .magic import *`, `from .npc import *`) and append:

```python
from .rig import *  # noqa: F401, F403
```

- [ ] **Step 6: Run test**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_rig_spans.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Run the routing-completeness test**

```bash
cd sidequest-server && uv run pytest tests/telemetry -v
```

Expected: All telemetry tests pass — verifies the new constants are correctly registered in `FLAT_ONLY_SPANS`.

- [ ] **Step 8: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/telemetry/spans/rig.py tests/telemetry/test_rig_spans.py sidequest/telemetry/spans/__init__.py
git add sidequest/telemetry/spans/rig.py sidequest/telemetry/spans/__init__.py tests/telemetry/test_rig_spans.py
git commit -m "feat(rig): three OTEL span emitters — bond_event, voice_register_change, confrontation_outcome"
```

---

### Task 5: Voice resolver — name-form-by-bond-tier

**Files:**
- Create: `sidequest-server/sidequest/agents/subsystems/chassis_voice.py`
- Test: `sidequest-server/tests/agents/test_chassis_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/agents/test_chassis_voice.py
"""Voice resolver returns name-form for current bond tier."""
from __future__ import annotations

from sidequest.agents.subsystems.chassis_voice import resolve_chassis_name_form
from sidequest.game.chassis import (
    BondLedgerEntry,
    ChassisInstance,
    apply_bond_event,
)
from sidequest.genre.models.chassis import ChassisVoiceSpec


def _kestrel(strength: float = 0.45) -> ChassisInstance:
    return ChassisInstance(
        id="kestrel",
        name="Kestrel",
        class_id="voidborn_freighter",
        voice=ChassisVoiceSpec(
            default_register="dry_warm",
            vocal_tics=["theatrical sigh"],
            silence_register="approving_or_sulking_context_dependent",
            name_forms_by_bond_tier={
                "severed": "Pilot",
                "hostile": "Pilot",
                "strained": "Pilot",
                "neutral": "Pilot",
                "familiar": "Mr. {last_name}",
                "trusted": "{first_name}",
                "fused": "{nickname}",
            },
        ),
        bond_ledger=[
            BondLedgerEntry(
                character_id="zee",
                bond_strength_character_to_chassis=strength,
                bond_strength_chassis_to_character=strength,
                bond_tier_character="trusted",
                bond_tier_chassis="trusted",
            ),
        ],
    )


class _FakeCharacter:
    """Mirrors the shape resolve_chassis_name_form expects."""
    def __init__(self, *, id: str, first_name: str, last_name: str, nickname: str | None = None) -> None:
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.nickname = nickname


def test_resolves_first_name_at_trusted_tier() -> None:
    chassis = _kestrel(0.45)
    zee = _FakeCharacter(id="zee", first_name="Zee", last_name="Jones")
    assert resolve_chassis_name_form(chassis, zee) == "Zee"


def test_resolves_last_name_form_after_drop_to_familiar() -> None:
    chassis = _kestrel(0.45)
    apply_bond_event(
        chassis=chassis,
        character_id="zee",
        delta_character=-0.10,
        delta_chassis=-0.10,
        reason="contrived",
        confrontation_id=None,
        turn_id=1,
    )
    zee = _FakeCharacter(id="zee", first_name="Zee", last_name="Jones")
    assert resolve_chassis_name_form(chassis, zee) == "Mr. Jones"


def test_no_voice_returns_default_pilot() -> None:
    chassis = _kestrel(0.45)
    chassis.voice = None
    zee = _FakeCharacter(id="zee", first_name="Zee", last_name="Jones")
    assert resolve_chassis_name_form(chassis, zee) == "Pilot"


def test_missing_nickname_at_fused_falls_back_to_first_name() -> None:
    chassis = _kestrel(0.85)
    chassis.bond_ledger[0].bond_tier_chassis = "fused"
    zee = _FakeCharacter(id="zee", first_name="Zee", last_name="Jones", nickname=None)
    # Fallback is documented in spec §7 — fused with no nickname source
    # falls back to {first_name}, returns "Zee", not "{nickname}".
    assert resolve_chassis_name_form(chassis, zee) == "Zee"
```

- [ ] **Step 2: Run test to confirm failure**

```bash
cd sidequest-server && uv run pytest tests/agents/test_chassis_voice.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# sidequest-server/sidequest/agents/subsystems/chassis_voice.py
"""Resolve a chassis's current address-form for a named character.

The narrator prompt builder calls this when generating chassis-as-speaker
dialogue. Asymmetric bond: the chassis's *own* tier (chassis_to_character)
governs how it addresses the character, regardless of how the character
feels about the chassis.

If the chassis has no voice block, the chassis does not speak — return
the default "Pilot" form so any accidental narrator dialogue at least
stays cliché-judge-flagged at the YELLOW level rather than producing
out-of-band prose.
"""
from __future__ import annotations

from typing import Protocol

from sidequest.game.chassis import ChassisInstance


class _CharacterLike(Protocol):
    id: str
    first_name: str
    last_name: str
    nickname: str | None


_DEFAULT_FORM = "Pilot"


def resolve_chassis_name_form(
    chassis: ChassisInstance,
    character: _CharacterLike,
) -> str:
    """Return the chassis's current address-form for the character."""
    if chassis.voice is None:
        return _DEFAULT_FORM

    entry = chassis.bond_for(character.id)
    if entry is None:
        return _DEFAULT_FORM

    template = chassis.voice.name_forms_by_bond_tier.get(
        entry.bond_tier_chassis, _DEFAULT_FORM,
    )

    # Per spec §7 open question: {nickname} with no nickname source
    # falls back to {first_name} rather than rendering literal placeholder.
    if "{nickname}" in template and not character.nickname:
        template = chassis.voice.name_forms_by_bond_tier.get(
            "trusted", _DEFAULT_FORM,
        )

    return template.format(
        first_name=character.first_name,
        last_name=character.last_name,
        nickname=character.nickname or character.first_name,
    )
```

- [ ] **Step 4: Run test**

```bash
cd sidequest-server && uv run pytest tests/agents/test_chassis_voice.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/agents/subsystems/chassis_voice.py tests/agents/test_chassis_voice.py
git add sidequest/agents/subsystems/chassis_voice.py tests/agents/test_chassis_voice.py
git commit -m "feat(rig): voice resolver — chassis name-form by bond tier (asymmetric)"
```

---

### Task 6: Author chassis_classes.yaml

**Files:**
- Create: `sidequest-content/genre_packs/space_opera/chassis_classes.yaml`

- [ ] **Step 1: Write the file**

```yaml
# sidequest-content/genre_packs/space_opera/chassis_classes.yaml
# Genre-layer chassis catalog for space_opera.
# Slice scope (2026-04-29): one class — voidborn_freighter.
#
# Deferred classes (see rig MVP follow-on roadmap):
#   - prospector_skiff
#   - hegemonic_patrol_cruiser
#   - fighter
#   - station_hull
#   - courier_skiff
#
# Spec: docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md

version: "0.1.0"
genre: space_opera

coverage:
  authored: [voidborn_freighter]
  deferred:
    - prospector_skiff
    - hegemonic_patrol_cruiser
    - fighter
    - station_hull
    - courier_skiff

classes:
  - id: voidborn_freighter
    display_name: "Voidborn Freighter"
    class: freighter
    provenance: voidborn_built
    scale_band: vehicular
    crew_model: flexible_roles
    embodiment_model: singular
    crew_awareness: surface
    psi_resonance:
      default: receptive
      amplifies: [void_singing, far_listening]
    default_voice:
      default_register: dry_warm
      vocal_tics:
        - "almost-but-legally-distinct from a laugh"
        - "theatrical sigh exactly long enough to register as judgement"
        - "drops to a discreet murmur"
      silence_register: approving_or_sulking_context_dependent
      name_forms_by_bond_tier:
        severed: "Pilot"
        hostile: "Pilot"
        strained: "Pilot"
        neutral: "Pilot"
        familiar: "Mr. {last_name}"
        trusted: "{first_name}"
        fused: "{nickname}"
    interior_rooms:
      - id: cockpit
        display_name: "Cockpit"
        default_occupants: [pilot]
      - id: engineering
        display_name: "Engineering"
        default_occupants: [engineer]
      - id: galley
        display_name: "Galley"
        bond_eligible_for: [the_tea_brew]
      - id: deck_three_corridor
        display_name: "Deck Three Corridor"
        narrative_register: liminal_warm
    crew_roles:
      - id: pilot
        operates_hardpoints: "*"
        bond_eligible: true
        default_seat: cockpit
```

- [ ] **Step 2: Validate via the pydantic loader**

```bash
cd sidequest-server && uv run python -c "
import yaml
from pathlib import Path
from sidequest.genre.models.chassis import ChassisClassesConfig

p = Path('../sidequest-content/genre_packs/space_opera/chassis_classes.yaml')
cfg = ChassisClassesConfig.model_validate(yaml.safe_load(p.read_text()))
print(f'OK: {len(cfg.classes)} class(es)')
"
```

Expected: `OK: 1 class(es)`. If validation fails, fix the YAML to match the pydantic from Task 1.

- [ ] **Step 3: Commit (in sidequest-content subrepo)**

```bash
cd sidequest-content
git add genre_packs/space_opera/chassis_classes.yaml
git commit -m "content(space_opera): chassis_classes.yaml — voidborn_freighter

Slice scope per docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md.
Other classes (prospector_skiff, hegemonic_patrol_cruiser, fighter,
station_hull, courier_skiff) deferred to follow-on."
```

---

### Task 7: Author rigs.yaml for Coyote Star

**Files:**
- Create: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/rigs.yaml`

- [ ] **Step 1: Write the file**

```yaml
# sidequest-content/genre_packs/space_opera/worlds/coyote_star/rigs.yaml
# World-layer chassis instances for Coyote Star.
# Slice scope (2026-04-29): one instance — Kestrel.
#
# Deferred instances (see rig MVP follow-on roadmap):
#   - bright_margin (escort target; npc_registry classifies as ally)
#   - tide_singer (voidborn freighter; future patron-pact bargain)
#   - hegemonic_patrol_cruiser instances (Grand Gate enforcement)
#
# Spec: docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md

version: "0.1.0"
world: coyote_star
genre: space_opera

coverage:
  authored: [kestrel]
  deferred: [bright_margin, tide_singer, hegemonic_patrol_cruisers]

chassis_instances:
  - id: kestrel
    name: "Kestrel"
    class: voidborn_freighter
    OCEAN: { O: 0.6, C: 0.7, E: 0.4, A: 0.5, N: 0.5 }
    voice:
      default_register: dry_warm
      vocal_tics:
        - "almost-but-legally-distinct from a laugh"
        - "theatrical sigh exactly long enough to register as judgement"
        - "dry as bonemeal"
        - "drops to a discreet murmur"
      silence_register: approving_or_sulking_context_dependent
      name_forms_by_bond_tier:
        severed: "Pilot"
        hostile: "Pilot"
        strained: "Pilot"
        neutral: "Pilot"
        familiar: "Mr. {last_name}"
        trusted: "{first_name}"
        fused: "{nickname}"
    interior_rooms: [cockpit, engineering, galley, deck_three_corridor]
    bond_seeds:
      - character_role: player_character
        bond_strength_character_to_chassis: 0.45
        bond_strength_chassis_to_character: 0.45
        bond_tier_character: trusted
        bond_tier_chassis: trusted
        history_seeds:
          - "muscle memory from at least three jumps' worth of patch kits"
```

- [ ] **Step 2: Validate**

```bash
cd sidequest-server && uv run python -c "
import yaml
from pathlib import Path
from sidequest.genre.models.rigs_world import RigsWorldConfig

p = Path('../sidequest-content/genre_packs/space_opera/worlds/coyote_star/rigs.yaml')
cfg = RigsWorldConfig.model_validate(yaml.safe_load(p.read_text()))
print(f'OK: {len(cfg.chassis_instances)} chassis instance(s)')
"
```

Expected: `OK: 1 chassis instance(s)`.

- [ ] **Step 3: Commit (sidequest-content)**

```bash
cd sidequest-content
git add genre_packs/space_opera/worlds/coyote_star/rigs.yaml
git commit -m "content(coyote_star): rigs.yaml — Kestrel

Pre-bonded at trusted tier (0.45) per spec §1. Bright Margin, Tide-Singer,
Hegemonic patrol cruisers deferred."
```

---

### Task 8: Genre loader extension — load chassis_classes.yaml

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py`
- Modify: existing `GenrePack` model (find with `grep -n "class GenrePack" sidequest/genre/loader.py`)
- Test: extend or create `sidequest-server/tests/genre/test_genre_pack_load.py`

- [ ] **Step 1: Read the existing load_genre_pack to find the integration site**

```bash
cd sidequest-server && grep -n "def load_genre_pack\|chassis_classes\|class GenrePack" sidequest/genre/loader.py | head -10
```

This identifies (a) the function to extend, and (b) whether `GenrePack` is dataclass or pydantic.

- [ ] **Step 2: Write a failing test**

```python
# sidequest-server/tests/genre/test_genre_pack_load.py
# Add (or extend if file exists) — test that loading the space_opera pack
# now exposes the chassis_classes catalog.
from __future__ import annotations

from pathlib import Path

from sidequest.genre.loader import load_genre_pack

REPO_ROOT = Path(__file__).resolve().parents[3]
SPACE_OPERA = REPO_ROOT / "sidequest-content" / "genre_packs" / "space_opera"


def test_genre_pack_exposes_chassis_classes() -> None:
    pack = load_genre_pack(SPACE_OPERA)
    assert hasattr(pack, "chassis_classes"), \
        "GenrePack should expose chassis_classes after rig MVP Task 8"
    assert pack.chassis_classes is not None
    ids = {cls.id for cls in pack.chassis_classes.classes}
    assert "voidborn_freighter" in ids


def test_genre_pack_without_chassis_classes_is_valid() -> None:
    """Genres without chassis_classes.yaml load with pack.chassis_classes is None."""
    # Pick a genre that does not yet have chassis_classes.yaml authored.
    genre_with_no_chassis = REPO_ROOT / "sidequest-content" / "genre_packs" / "caverns_and_claudes"
    pack = load_genre_pack(genre_with_no_chassis)
    assert pack.chassis_classes is None
```

(Path resolution above uses `parents[3]` — adjust to wherever this test file lands relative to repo root. Confirm with `pwd` from the test file's directory.)

- [ ] **Step 3: Run failing test**

```bash
cd sidequest-server && uv run pytest tests/genre/test_genre_pack_load.py::test_genre_pack_exposes_chassis_classes -v
```

Expected: AttributeError or AssertionError.

- [ ] **Step 4: Add `chassis_classes` field to GenrePack and implement loader**

In `sidequest-server/sidequest/genre/loader.py`:

1. Import the new pydantic at the top:

```python
from sidequest.genre.models.chassis import ChassisClassesConfig
```

2. Add a field to the `GenrePack` model (find its definition; add alongside other optional configs like the magic config):

```python
chassis_classes: ChassisClassesConfig | None = None
```

3. In `load_genre_pack`, after the existing genre-pack-yaml loads, add:

```python
chassis_classes_path = path / "chassis_classes.yaml"
chassis_classes = None
if chassis_classes_path.exists():
    try:
        raw = yaml.safe_load(chassis_classes_path.read_text(encoding="utf-8"))
        chassis_classes = ChassisClassesConfig.model_validate(raw)
    except Exception as exc:
        # Per CLAUDE.md no-silent-fallback: surface the error, don't swallow.
        raise GenreError(
            f"chassis_classes.yaml in {path} failed to load: {exc}"
        ) from exc
```

4. Pass `chassis_classes` into the `GenrePack(...)` construction call.

(Adjust to whatever shape `GenrePack` and `GenreError` actually use — the existing `magic` config load is the closest pattern. `grep -n "magic" sidequest/genre/loader.py` will show the canonical example to mirror.)

- [ ] **Step 5: Run test**

```bash
cd sidequest-server && uv run pytest tests/genre/test_genre_pack_load.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/genre/loader.py tests/genre/test_genre_pack_load.py
git add sidequest/genre/loader.py tests/genre/test_genre_pack_load.py
git commit -m "feat(rig): genre loader reads chassis_classes.yaml; absent = None"
```

---

### Task 9: World materialization — load rigs.yaml + build chassis_registry

**Files:**
- Modify: `sidequest-server/sidequest/game/world_materialization.py`
- Test: `sidequest-server/tests/integration/test_kestrel_chassis_registry.py`

- [ ] **Step 1: Read materialize_world to find the integration site**

```bash
cd sidequest-server && grep -n "def materialize_world\|chassis\|magic_state" sidequest/game/world_materialization.py | head -20
```

The magic_state load is the closest precedent.

- [ ] **Step 2: Write the integration test**

```python
# sidequest-server/tests/integration/test_kestrel_chassis_registry.py
"""World-load → chassis_registry → npc_registry projection."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.world_materialization import materialize_world


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.integration
def test_coyote_star_load_materializes_kestrel(coyote_star_snapshot) -> None:
    """coyote_star_snapshot fixture lives in conftest.py — see existing magic
    integration tests for the shape; reuse the same fixture pattern."""
    snap = coyote_star_snapshot
    # World materialization should have already run — assert state.
    assert "kestrel" in snap.chassis_registry
    kestrel = snap.chassis_registry["kestrel"]
    assert kestrel.name == "Kestrel"
    assert len(kestrel.bond_ledger) >= 1
    # npc_registry projection
    names = {entry.name for entry in snap.npc_registry}
    assert "Kestrel" in names
```

- [ ] **Step 3: Add a fixture if missing**

Check `sidequest-server/tests/conftest.py` for an existing `coyote_star_snapshot` fixture. If absent, add:

```python
# in sidequest-server/tests/conftest.py
@pytest.fixture
def coyote_star_snapshot(tmp_path):
    """Load a fresh Coyote Star world snapshot for integration tests."""
    from sidequest.game.world_materialization import materialize_world
    from sidequest.game.persistence import new_snapshot_for_world  # use whatever the existing helper is
    snap = new_snapshot_for_world(genre="space_opera", world="coyote_star")
    materialize_world(snap, chapters=[])
    return snap
```

(If `new_snapshot_for_world` does not exist by that exact name, use whatever the magic-system Phase 2 commit uses — `grep -n "def new_snapshot\|def make_snapshot\|materialize_world(" tests/`.)

- [ ] **Step 4: Run failing test**

```bash
cd sidequest-server && uv run pytest tests/integration/test_kestrel_chassis_registry.py -v
```

Expected: AttributeError on `snap.chassis_registry` (field does not exist on snapshot yet — Task 10 adds it).

- [ ] **Step 5: Implement materialization**

In `sidequest-server/sidequest/game/world_materialization.py`:

1. Add imports:

```python
import yaml

from sidequest.game.chassis import (
    BondLedgerEntry,
    ChassisInstance,
    NpcRegistryEntry,
)
from sidequest.genre.models.rigs_world import RigsWorldConfig
```

2. After the existing world-yaml + magic load, add a chassis-load helper:

```python
def _load_chassis_registry(
    snapshot: Any,
    pack_path: Path,
    world_slug: str,
) -> None:
    """Load rigs.yaml for the world; materialize chassis_registry; project
    each chassis as an entry in npc_registry for narrator continuity."""
    rigs_path = pack_path / "worlds" / world_slug / "rigs.yaml"
    if not rigs_path.exists():
        # No rigs in this world is valid — many worlds don't use them.
        return

    raw = yaml.safe_load(rigs_path.read_text(encoding="utf-8"))
    cfg = RigsWorldConfig.model_validate(raw)

    for inst_cfg in cfg.chassis_instances:
        bond_seeds = [
            BondLedgerEntry(
                # Resolution from "player_character" placeholder happens
                # at chargen — until then, we keep the placeholder id.
                # Phase C / chargen-hook task does the rebind.
                character_id=seed.character_role,
                bond_strength_character_to_chassis=seed.bond_strength_character_to_chassis,
                bond_strength_chassis_to_character=seed.bond_strength_chassis_to_character,
                bond_tier_character=seed.bond_tier_character,
                bond_tier_chassis=seed.bond_tier_chassis,
            )
            for seed in inst_cfg.bond_seeds
        ]
        chassis = ChassisInstance(
            id=inst_cfg.id,
            name=inst_cfg.name,
            class_id=inst_cfg.chassis_class_id,
            OCEAN=inst_cfg.OCEAN,
            voice=inst_cfg.voice,
            interior_rooms=inst_cfg.interior_rooms,
            bond_ledger=bond_seeds,
        )
        snapshot.chassis_registry[chassis.id] = chassis
        # Project into npc_registry — narrator already reads this for prose.
        snapshot.npc_registry.append(_project_chassis_to_npc(chassis))


def _project_chassis_to_npc(chassis: ChassisInstance) -> NpcRegistryEntry:
    return NpcRegistryEntry(
        name=chassis.name,
        role="ship_ai",  # slice: only voidborn_freighter; future tiers
                        # will pick role from class_id mapping.
        pronouns="she/her",  # slice default; class-level field follows later
    )
```

3. Call `_load_chassis_registry(snapshot, pack_path, world_slug)` from inside `materialize_world` at the same level as the existing magic-state load.

(`pack_path` and `world_slug` will be available where the existing world-yaml is loaded — adjust to the function's actual locals.)

- [ ] **Step 6: Run test**

```bash
cd sidequest-server && uv run pytest tests/integration/test_kestrel_chassis_registry.py -v
```

Expected: still failing on `snap.chassis_registry` until Task 10 lands.

- [ ] **Step 7: Defer commit until Task 10 lands** — these two tasks are co-dependent. Move on, return to commit after both pass.

---

### Task 10: Session.chassis_registry field

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py`

- [ ] **Step 1: Find the GameSnapshot definition**

```bash
cd sidequest-server && grep -n "class GameSnapshot\|npc_registry:" sidequest/game/session.py | head -10
```

- [ ] **Step 2: Add the field**

In `GameSnapshot` (mirror placement of `npc_registry`), add:

```python
from sidequest.game.chassis import ChassisInstance

# ... in GameSnapshot:
chassis_registry: dict[str, ChassisInstance] = Field(default_factory=dict)
```

- [ ] **Step 3: Run integration test from Task 9**

```bash
cd sidequest-server && uv run pytest tests/integration/test_kestrel_chassis_registry.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Run full server test suite to catch regressions**

```bash
cd sidequest-server && uv run pytest -x
```

Expected: All pre-existing tests still pass + the new ones.

- [ ] **Step 5: Lint + commit (combined Tasks 9 + 10)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/world_materialization.py sidequest/game/session.py tests/integration/test_kestrel_chassis_registry.py tests/conftest.py
git add sidequest/game/world_materialization.py sidequest/game/session.py tests/integration/test_kestrel_chassis_registry.py tests/conftest.py
git commit -m "feat(rig): world-load materializes chassis_registry + npc_registry projection

Tasks 9+10 commit together (co-dependent). Kestrel loads from rigs.yaml
into snapshot.chassis_registry and projects to npc_registry as ship_ai
for narrator prompt continuity."
```

---

### Task 11: Narrator prompt — pull chassis voice into chassis-as-speaker section

**Files:**
- Modify: `sidequest-server/sidequest/agents/prompt_framework/core.py`
- Test: `sidequest-server/tests/agents/test_prompt_framework_chassis.py`

- [ ] **Step 1: Read the existing prompt builder around line 360 (NpcRegistryEntry handling)**

```bash
cd sidequest-server && sed -n '355,400p' sidequest/agents/prompt_framework/core.py
```

- [ ] **Step 2: Write the failing test**

```python
# sidequest-server/tests/agents/test_prompt_framework_chassis.py
"""Narrator prompt includes chassis voice + name-form when chassis is in registry."""
from __future__ import annotations

from sidequest.agents.prompt_framework.core import build_chassis_voice_section
from sidequest.game.chassis import BondLedgerEntry, ChassisInstance
from sidequest.genre.models.chassis import ChassisVoiceSpec


def _kestrel() -> ChassisInstance:
    return ChassisInstance(
        id="kestrel",
        name="Kestrel",
        class_id="voidborn_freighter",
        voice=ChassisVoiceSpec(
            default_register="dry_warm",
            vocal_tics=["theatrical sigh"],
            silence_register="approving_or_sulking_context_dependent",
            name_forms_by_bond_tier={
                "severed": "Pilot", "hostile": "Pilot", "strained": "Pilot",
                "neutral": "Pilot", "familiar": "Mr. {last_name}",
                "trusted": "{first_name}", "fused": "{nickname}",
            },
        ),
        bond_ledger=[
            BondLedgerEntry(
                character_id="zee",
                bond_strength_character_to_chassis=0.45,
                bond_strength_chassis_to_character=0.45,
                bond_tier_character="trusted",
                bond_tier_chassis="trusted",
            ),
        ],
    )


class _FakePC:
    id = "zee"
    first_name = "Zee"
    last_name = "Jones"
    nickname = None


def test_chassis_voice_section_emits_register_tics_and_name_form() -> None:
    chassis_registry = {"kestrel": _kestrel()}
    section = build_chassis_voice_section(
        chassis_registry=chassis_registry,
        active_character=_FakePC(),
    )
    assert "Kestrel" in section
    assert "dry_warm" in section
    assert "Zee" in section  # current name-form
    assert "theatrical sigh" in section


def test_chassis_voice_section_empty_when_no_chassis_with_voice() -> None:
    section = build_chassis_voice_section(
        chassis_registry={},
        active_character=_FakePC(),
    )
    assert section == ""
```

- [ ] **Step 3: Run failing test**

```bash
cd sidequest-server && uv run pytest tests/agents/test_prompt_framework_chassis.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `build_chassis_voice_section` in core.py**

Append a new function to `sidequest/agents/prompt_framework/core.py`:

```python
def build_chassis_voice_section(
    chassis_registry: dict[str, "ChassisInstance"],
    active_character: Any,
) -> str:
    """Render the chassis-as-speaker prompt fragment.

    Lives next to build_npc_registry_section. The narrator already reads
    npc_registry for chassis identity; this section adds register, vocal
    tics, current name-form, and silence-register so chassis dialogue
    matches the locked taxonomy voice.
    """
    from sidequest.agents.subsystems.chassis_voice import resolve_chassis_name_form

    if not chassis_registry:
        return ""

    lines: list[str] = []
    for chassis in chassis_registry.values():
        if chassis.voice is None:
            continue
        name_form = resolve_chassis_name_form(chassis, active_character)
        tics = "; ".join(chassis.voice.vocal_tics)
        lines.append(
            f"- {chassis.name} (chassis voice — {chassis.voice.default_register}): "
            f"addresses you as \"{name_form}\". Vocal tics: {tics}. "
            f"Silence reads as: {chassis.voice.silence_register}."
        )

    if not lines:
        return ""
    return "Chassis voices in scene:\n" + "\n".join(lines)
```

(Add the necessary import at the top: `from sidequest.game.chassis import ChassisInstance`.)

Then locate the existing prompt-assembly function (the one that calls `build_npc_registry_section`) and add a parallel call to `build_chassis_voice_section`, passing the snapshot's `chassis_registry` and the active character. The exact integration site mirrors the existing npc_registry call.

- [ ] **Step 5: Run test**

```bash
cd sidequest-server && uv run pytest tests/agents/test_prompt_framework_chassis.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/agents/prompt_framework/core.py tests/agents/test_prompt_framework_chassis.py
git add sidequest/agents/prompt_framework/core.py tests/agents/test_prompt_framework_chassis.py
git commit -m "feat(rig): narrator prompt — chassis voice section with bond-tier name-form"
```

---

### Task 12: Phase A wiring smoke test

**Files:**
- Test: extend `sidequest-server/tests/integration/test_kestrel_chassis_registry.py`

- [ ] **Step 1: Add a smoke test that exercises the full Phase A path**

```python
# Append to tests/integration/test_kestrel_chassis_registry.py
@pytest.mark.integration
def test_kestrel_voice_section_renders_in_prompt(coyote_star_snapshot) -> None:
    """End-of-Phase-A: world load → chassis_registry → voice section in prompt."""
    from sidequest.agents.prompt_framework.core import build_chassis_voice_section

    class _PC:
        id = "player_character"  # bond_seed placeholder id
        first_name = "Zee"
        last_name = "Jones"
        nickname = None

    section = build_chassis_voice_section(
        chassis_registry=coyote_star_snapshot.chassis_registry,
        active_character=_PC(),
    )
    assert "Kestrel" in section
    assert "Zee" in section  # trusted-tier first-name form
    assert "theatrical sigh" in section
```

- [ ] **Step 2: Run**

```bash
cd sidequest-server && uv run pytest tests/integration/test_kestrel_chassis_registry.py -v
```

Expected: all integration tests pass — world materializes Kestrel, prompt renders her voice, name-form is "Zee" because the bond_seed put her at trusted.

- [ ] **Step 3: Run the aggregate gate**

```bash
cd /Users/slabgorb/Projects/oq-2 && just check-all
```

Expected: All checks green. If anything else broke, fix before continuing.

- [ ] **Step 4: Commit**

```bash
cd sidequest-server
git add tests/integration/test_kestrel_chassis_registry.py
git commit -m "test(rig): Phase A smoke — world load → chassis voice in prompt"
```

---

### Task 13: Phase A cut-point — manual playtest verification

- [ ] **Step 1: Boot the stack**

```bash
cd /Users/slabgorb/Projects/oq-2 && just up
```

- [ ] **Step 2: Start a fresh Coyote Star session in the UI (port 5173)**

Pick `space_opera`/`coyote_star`, walk through chargen with first_name "Zee" last_name "Jones" (or any). Begin play.

- [ ] **Step 3: Verify GM panel shows Kestrel in chassis state**

Open the OTEL/GM panel (per ADR-090). Confirm `chassis_registry` is populated. No `rig.*` spans yet (none fire in Phase A).

- [ ] **Step 4: Verify narrator prose addresses player as "Zee"**

Look at the first one or two narrator turns. The chassis-as-speaker prose, when it occurs, should use "Zee" (first_name form, trusted tier). If it says "Pilot" or anything else, the voice section isn't reaching the prompt — debug in `agents/prompt_framework/core.py`.

- [ ] **Step 5: Phase A done.** No commit (cut-point only). Phase A delivers: Kestrel exists in chassis_registry, projects to npc_registry, voice + bond-tier-correct name-form reach narrator prose. The_tea_brew does not yet fire — Phase C blocked on magic Phase 5.

---

## Phase B — Doc additions (independent of magic Phase 5)

### Task 14: confrontation-advancement.md — three new outputs + tone axis

**Files:**
- Modify: `docs/design/confrontation-advancement.md`

- [ ] **Step 1: Read the existing output catalog section**

```bash
grep -n "^##\|^###" /Users/slabgorb/Projects/oq-2/docs/design/confrontation-advancement.md | head -30
```

Identify the section that lists existing outputs (`item_history_increment`, `bond_increment`, `notice_increment`, etc.) and the section (if any) that declares confrontation schema fields.

- [ ] **Step 2: Append three new output entries**

In the output-catalog section, add (matching the file's existing entry shape):

```markdown
### `bond_strength_growth_via_intimacy`

Per-character per-chassis bond delta produced by intimate or domestic-register
confrontations. Default magnitude: `+0.04` character-side, `+0.06` chassis-side
(asymmetric — chassis side typically grows faster on shared-life moments).
Compoundable; the primary engine of Wayfarer-register bond growth.

Producing confrontations: `the_tea_brew`, `the_engineers_litany`, `the_long_quiet`,
`the_shared_watch`, `the_maintenance_communion` (slice ships only `the_tea_brew`).

### `bond_tier_threshold_cross`

Fires alongside `bond_strength_growth_via_intimacy` (or any other bond-mutating
output) when the resulting bond_strength change crosses a tier boundary
(neutral → familiar → trusted → fused, or downward). Triggers narrative
callbacks via the narrator and may unlock new confrontation eligibility on
the chassis (e.g., `the_refit` requires `bond_tier ≥ trusted`).

### `chassis_lineage_intimate`

Appends a warm-small entry to a chassis's lineage ledger. Distinct from
`chassis_lineage_dramatic` (named battles, refits, wrecks, sales).
Sub-types under the `chassis_lineage` family declared in
docs/design/rig-taxonomy.md.

Producing confrontations: same set as `bond_strength_growth_via_intimacy`,
plus `the_naming` and `the_bond` (the latter two ship in follow-on specs).
```

- [ ] **Step 3: Add tone-axis schema field**

In the section that declares confrontation schema (or in a new "Confrontation Schema Additions — 2026-04-29" subsection if no central schema section exists), add:

```markdown
### Optional `register` field on confrontations

A confrontation may declare `register: dramatic | intimate | domestic | quiet`.
Default when absent: `dramatic`. This axis governs:

- Narration register hint to the narrator (intimate/domestic confrontations
  resist escalatory prose).
- Cliché-judge expectation: an intimate-register confrontation that escalates
  to combat outputs is YELLOW.
- Output magnitude defaults: `bond_strength_growth_via_intimacy` is keyed
  off intimate/domestic register; dramatic-register bond changes are keyed
  off the larger `bond_strength` step-change output.

Existing confrontations are not retrofitted. The first authored
intimate-register confrontation is `the_tea_brew` (Coyote Star,
docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md).
```

- [ ] **Step 4: Commit (in the orchestrator repo root)**

```bash
cd /Users/slabgorb/Projects/oq-2
git add docs/design/confrontation-advancement.md
git commit -m "docs(rig): three new outputs + tone-axis register field

Adds bond_strength_growth_via_intimacy, bond_tier_threshold_cross,
chassis_lineage_intimate to the output catalog. Optional register field
on confrontations (dramatic | intimate | domestic | quiet, default dramatic).
Existing confrontations unchanged. Spec:
docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md"
```

---

## Phase C — `the_tea_brew` wiring (BLOCKED on magic plan Phase 5)

**Before starting Phase C:** verify magic Phase 5 (Confrontations Wired) has shipped.

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git log --oneline | grep -iE "phase 5|confrontations wired|tea_brew|confront.*loader" | head -5
```

If nothing matches, magic Phase 5 has not landed; Phase C cannot start. Pause this plan and notify the operator.

If it has shipped: identify the confrontation outcome handler and the auto-fire eligibility hook with:

```bash
cd sidequest-server && grep -rn "auto_fire\|fire_conditions\|MagicConfrontation\|world_confrontation" sidequest/ --include="*.py" | head -20
```

The pseudocode in Tasks 15–19 below assumes the magic-Phase-5 outcome handler is centralized in some `apply_world_confrontation_outcome(snapshot, confrontation_id, branch, *outputs)` function and that the auto-fire eligibility check lives in a hook called from `room_movement.py` after the player moves rooms. Adjust file paths and function names in the steps below to match what magic Phase 5 actually shipped.

---

### Task 15: Append `the_tea_brew` to coyote_star confrontations.yaml

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/confrontations.yaml`

- [ ] **Step 1: Append (do not rewrite existing entries)**

After the existing five confrontations, add:

```yaml
  - id: the_tea_brew
    label: "The Tea Brew"
    register: intimate
    plugin_tie_ins: [item_legacy_v1]
    rig_tie_ins: [voidborn_freighter]
    auto_fire: true
    fire_conditions:
      interior_room_present: galley
      bond_tier_min: familiar
      cooldown_turns: 6
    rounds: 1
    resource_pool:
      primary: bond
    description: |
      Site-of-life ritual. Captain offers a personal preference (incense,
      music, a tea variety) to the chassis. The chassis registers the
      offering. The room remembers.
    outcomes:
      clear_win:
        mandatory_outputs:
          - bond_strength_growth_via_intimacy
          - chassis_lineage_intimate
      refused:
        mandatory_outputs:
          - chassis_lineage_intimate
```

- [ ] **Step 2: Validate via the magic-Phase-5 confrontations loader**

```bash
cd sidequest-server && uv run python -c "
# Adjust import to the magic-Phase-5 loader name once it's known
from sidequest.magic.confrontations import load_world_confrontations  # likely
cfg = load_world_confrontations('space_opera', 'coyote_star')
ids = {c.id for c in cfg.confrontations}
assert 'the_tea_brew' in ids
print('OK')
"
```

If the import fails, find the actual loader (`grep -rn "def load.*confront" sidequest/`) and use it.

- [ ] **Step 3: Commit (sidequest-content)**

```bash
cd sidequest-content
git add genre_packs/space_opera/worlds/coyote_star/confrontations.yaml
git commit -m "content(coyote_star): append the_tea_brew confrontation

First intimate-register confrontation; bond + lineage outputs.
Auto-fires on Galley entry with bond_tier ≥ familiar."
```

---

### Task 16: Wire `the_tea_brew` outputs into the magic confrontation outcome handler

**Files:**
- Modify: whatever module magic Phase 5 shipped that maps `mandatory_outputs` to state mutations (likely `sidequest/magic/state.py` or `sidequest/server/dispatch/confrontation.py` — confirm with `grep -rn "mandatory_outputs\|apply_outcome" sidequest/`).
- Test: `sidequest-server/tests/integration/test_kestrel_tea_brew_outputs.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/integration/test_kestrel_tea_brew_outputs.py
"""the_tea_brew clear_win mutates bond ledger and chassis lineage; spans fire."""
from __future__ import annotations

import pytest

from sidequest.telemetry.spans import (
    SPAN_RIG_BOND_EVENT,
    SPAN_RIG_CONFRONTATION_OUTCOME,
)


@pytest.mark.integration
def test_clear_win_runs_outputs(coyote_star_snapshot, captured_spans):
    snap = coyote_star_snapshot
    # Assume magic-Phase-5 entrypoint is named apply_world_confrontation_outcome.
    # Adjust to actual name.
    from sidequest.magic.confrontations import apply_world_confrontation_outcome

    kestrel_before = snap.chassis_registry["kestrel"]
    bond_before = kestrel_before.bond_ledger[0].bond_strength_chassis_to_character
    lineage_before = len(kestrel_before.lineage)

    apply_world_confrontation_outcome(
        snapshot=snap,
        confrontation_id="the_tea_brew",
        branch="clear_win",
        actor_id="player_character",
        chassis_id="kestrel",
        turn_id=10,
    )

    kestrel = snap.chassis_registry["kestrel"]
    assert kestrel.bond_ledger[0].bond_strength_chassis_to_character > bond_before
    assert len(kestrel.lineage) == lineage_before + 1
    assert kestrel.lineage[-1].kind == "intimate"

    span_names = {s.name for s in captured_spans}
    assert SPAN_RIG_BOND_EVENT in span_names
    assert SPAN_RIG_CONFRONTATION_OUTCOME in span_names
```

- [ ] **Step 2: Run failing test**

```bash
cd sidequest-server && uv run pytest tests/integration/test_kestrel_tea_brew_outputs.py -v
```

Expected: outputs not yet wired — the test fails because either the function doesn't recognize `the_tea_brew` outputs or the mutations don't reach the chassis.

- [ ] **Step 3: Wire the three outputs into the outcome handler**

In whatever Phase-5 module hosts the outcome dispatch, add cases for the three new output names:

```python
from sidequest.game.chassis import (
    apply_bond_event,
    apply_chassis_lineage_intimate,
)
from sidequest.telemetry.spans import (
    emit_rig_bond_event,
    emit_rig_confrontation_outcome,
    emit_rig_voice_register_change,
)


def _apply_bond_strength_growth_via_intimacy(
    snapshot, *, chassis_id, actor_id, register, confrontation_id, turn_id
):
    chassis = snapshot.chassis_registry[chassis_id]
    result = apply_bond_event(
        chassis=chassis,
        character_id=actor_id,
        delta_character=0.04,
        delta_chassis=0.06,
        reason=f"{confrontation_id} clear_win",
        confrontation_id=confrontation_id,
        turn_id=turn_id,
    )
    emit_rig_bond_event(
        chassis_id=chassis_id,
        actor_id=actor_id,
        side="both",
        delta_character=0.04,
        delta_chassis=0.06,
        tier_character_before=result.tier_character_before,
        tier_character_after=result.tier_character_after,
        tier_chassis_before=result.tier_chassis_before,
        tier_chassis_after=result.tier_chassis_after,
        confrontation_id=confrontation_id,
        register=register,
    )
    if result.tier_chassis_crossed:
        emit_rig_voice_register_change(
            chassis_id=chassis_id,
            actor_id=actor_id,
            register_before=result.tier_chassis_before,
            register_after=result.tier_chassis_after,
            triggering_event=confrontation_id,
        )


def _apply_chassis_lineage_intimate(
    snapshot, *, chassis_id, confrontation_id, turn_id, narrative_seed
):
    chassis = snapshot.chassis_registry[chassis_id]
    apply_chassis_lineage_intimate(
        chassis=chassis,
        narrative_seed=narrative_seed,
        turn_id=turn_id,
        confrontation_id=confrontation_id,
    )


# Register both in the magic-Phase-5 OUTPUT_HANDLERS dispatch dict
# (or whatever the equivalent registration is — mirror existing pattern).
OUTPUT_HANDLERS["bond_strength_growth_via_intimacy"] = _apply_bond_strength_growth_via_intimacy
OUTPUT_HANDLERS["chassis_lineage_intimate"] = _apply_chassis_lineage_intimate
```

After every confrontation outcome resolution call, append:

```python
emit_rig_confrontation_outcome(
    chassis_id=chassis_id,
    confrontation_id=confrontation_id,
    register=register,  # from the confrontation def
    branch=branch,
    outputs=output_names_applied,
)
```

(The exact integration point depends on Phase-5 shape — find the spot where outputs are applied in a loop and emit the span at end-of-loop.)

- [ ] **Step 4: Run test**

```bash
cd sidequest-server && uv run pytest tests/integration/test_kestrel_tea_brew_outputs.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Lint + commit**

```bash
cd sidequest-server && uv run ruff check $(git diff --name-only HEAD)
git add -A
git commit -m "feat(rig): wire bond + lineage outputs into magic Phase-5 outcome handler

Routes bond_strength_growth_via_intimacy and chassis_lineage_intimate
into chassis state. Emits rig.bond_event, rig.voice_register_change
(when tier crosses), and rig.confrontation_outcome on every outcome."
```

---

### Task 17: Auto-fire hook on Galley entry

**Files:**
- Modify: `sidequest-server/sidequest/game/room_movement.py`
- Test: `sidequest-server/tests/integration/test_galley_autofires_tea_brew.py`

- [ ] **Step 1: Inspect room_movement post-hook**

```bash
cd sidequest-server && grep -n "def \|on_room_enter\|after_move\|post_move" sidequest/game/room_movement.py | head -10
```

Identify the function called *after* the player has moved into a new room. If no such hook exists yet, the simplest seam is the function that updates `current_room` (likely the bottom of the move-resolution function).

- [ ] **Step 2: Write the failing test**

```python
# sidequest-server/tests/integration/test_galley_autofires_tea_brew.py
"""When player moves into Galley with bond_tier ≥ familiar, the_tea_brew auto-fires."""
from __future__ import annotations

import pytest


@pytest.mark.integration
def test_galley_entry_triggers_tea_brew(coyote_star_snapshot):
    snap = coyote_star_snapshot
    from sidequest.game.room_movement import move_player_to_room  # actual fn name may differ

    # Pre: Kestrel bond at trusted (0.45 from world-load).
    bond_before = snap.chassis_registry["kestrel"].bond_ledger[0].bond_strength_chassis_to_character

    move_player_to_room(snap, "kestrel:galley")  # adjust to actual room id format

    # Post: bond grew → the_tea_brew fired clear_win path.
    bond_after = snap.chassis_registry["kestrel"].bond_ledger[0].bond_strength_chassis_to_character
    assert bond_after > bond_before


@pytest.mark.integration
def test_galley_entry_respects_cooldown(coyote_star_snapshot):
    snap = coyote_star_snapshot
    from sidequest.game.room_movement import move_player_to_room

    move_player_to_room(snap, "kestrel:galley")
    bond_after_first = snap.chassis_registry["kestrel"].bond_ledger[0].bond_strength_chassis_to_character

    # Move out and back in immediately — cooldown 6 turns means no second fire.
    move_player_to_room(snap, "kestrel:cockpit")
    move_player_to_room(snap, "kestrel:galley")
    bond_after_second = snap.chassis_registry["kestrel"].bond_ledger[0].bond_strength_chassis_to_character
    assert bond_after_second == bond_after_first
```

- [ ] **Step 3: Run failing test**

```bash
cd sidequest-server && uv run pytest tests/integration/test_galley_autofires_tea_brew.py -v
```

Expected: bond doesn't change because no auto-fire wired.

- [ ] **Step 4: Add the post-move auto-fire eligibility check**

In `room_movement.py`, after the player's `current_room` is updated:

```python
def _check_chassis_autofire_confrontations(snapshot, room_id: str) -> None:
    """If the entered room is bond_eligible_for any auto-fire confrontation
    and the player meets the fire_conditions, fire it."""
    # Find any chassis interior_room matching this room_id.
    for chassis in snapshot.chassis_registry.values():
        if room_id not in {f"{chassis.id}:{r}" for r in chassis.interior_rooms}:
            continue

        bond = chassis.bond_for(snapshot.active_character_id)
        if bond is None:
            continue

        # Look up the world-confrontation definitions for auto-fire entries
        # bound to this room. Mirror the magic-Phase-5 lookup pattern.
        from sidequest.magic.confrontations import (
            find_autofire_confrontations_for_room,  # adjust to actual name
        )
        eligible = find_autofire_confrontations_for_room(
            snapshot=snapshot,
            chassis_id=chassis.id,
            room_local_id=room_id.split(":", 1)[1],
            bond_tier_chassis=bond.bond_tier_chassis,
        )

        for cdef in eligible:
            # Check cooldown via existing magic-Phase-5 cooldown ledger.
            if not _cooldown_elapsed(snapshot, cdef.id, chassis.id):
                continue
            from sidequest.magic.confrontations import (
                apply_world_confrontation_outcome,
            )
            apply_world_confrontation_outcome(
                snapshot=snapshot,
                confrontation_id=cdef.id,
                branch="clear_win",  # auto-fire defaults to clear_win;
                                     # narrator may later override
                actor_id=snapshot.active_character_id,
                chassis_id=chassis.id,
                turn_id=snapshot.current_turn,
            )
            _stamp_cooldown(snapshot, cdef.id, chassis.id, snapshot.current_turn)


# Call this from the existing post-move site:
def move_player_to_room(snapshot, target_room_id: str) -> None:
    # ... existing logic ...
    snapshot.current_room = target_room_id
    _check_chassis_autofire_confrontations(snapshot, target_room_id)
```

(`_cooldown_elapsed` and `_stamp_cooldown` should reuse magic-Phase-5's cooldown bookkeeping. If Phase 5 doesn't ship one, the slice owns adding cooldown state on the snapshot — a `dict[(confrontation_id, chassis_id), turn_stamped]` field. Note this in the commit if so.)

- [ ] **Step 5: Run test**

```bash
cd sidequest-server && uv run pytest tests/integration/test_galley_autofires_tea_brew.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/game/room_movement.py tests/integration/test_galley_autofires_tea_brew.py
git add sidequest/game/room_movement.py tests/integration/test_galley_autofires_tea_brew.py
git commit -m "feat(rig): auto-fire the_tea_brew on Galley entry with bond_tier check + cooldown"
```

---

### Task 18: Cliché-judge hook — name-form mismatch

**Files:**
- Modify: `docs/design/rig-taxonomy.md` (Cliché-Judge Hooks section) — mark hook #7 as ACTIVE in slice
- Modify: cliché-judge agent's rubric file (find with `grep -rn "cliche-judge\|cliche_judge" .claude/agents/ ~/.claude/agents/ 2>/dev/null | head -5`)

- [ ] **Step 1: Find the cliché-judge agent definition**

```bash
ls /Users/slabgorb/Projects/oq-2/.claude/agents/ 2>/dev/null | grep -i cliche
ls ~/.claude/agents/ 2>/dev/null | grep -i cliche
```

- [ ] **Step 2: Add the slice hook to the rubric**

In the cliché-judge agent definition (likely `.claude/agents/cliche-judge.md` or similar), append to its rubric section:

```markdown
### Rig framework hooks (slice scope, 2026-04-29)

- **Hook 7 (YELLOW)** — When narrator prose contains a chassis address-form
  (e.g., the chassis calls a character by name), the form must match the
  chassis's current `bond_tier_chassis` per the chassis's
  `voice.name_forms_by_bond_tier` mapping. Mismatch is suspicious — flag as
  YELLOW. Source of truth: `snapshot.chassis_registry[chassis_id].bond_ledger`,
  joined with the chassis's voice block.

  Other rig hooks (1–6, 8–15 from docs/design/rig-taxonomy.md §Cliché-Judge
  Hooks) ship with their producing subsystems and are not active in this slice.
```

- [ ] **Step 3: Mark hook #7 active in rig-taxonomy.md**

In `docs/design/rig-taxonomy.md`, in the "Cliché-Judge Hooks" section, prepend a status line:

```markdown
**Slice activation status (2026-04-29):** Hook #7 active per
docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md.
Hooks #1–6 and #8–15 not yet active; ship with their producing subsystems.
```

- [ ] **Step 4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2
git add docs/design/rig-taxonomy.md .claude/agents/cliche-judge.md  # adjust path
git commit -m "docs(rig): activate cliché-judge hook #7 — chassis name-form vs bond tier"
```

---

### Task 19: End-to-end Phase C wiring test + manual playtest

**Files:**
- Test: `sidequest-server/tests/integration/test_kestrel_tea_brew.py`

- [ ] **Step 1: Write the end-to-end test**

```python
# sidequest-server/tests/integration/test_kestrel_tea_brew.py
"""End-to-end: world load → Galley entry → tea_brew fires → bond moves → spans + projection updated."""
from __future__ import annotations

import pytest

from sidequest.telemetry.spans import (
    SPAN_RIG_BOND_EVENT,
    SPAN_RIG_CONFRONTATION_OUTCOME,
)


@pytest.mark.integration
def test_kestrel_tea_brew_full_loop(coyote_star_snapshot, captured_spans):
    """The slice's demo path, end-to-end."""
    snap = coyote_star_snapshot
    from sidequest.game.room_movement import move_player_to_room

    # 1. World loaded, Kestrel materialized, npc_registry projection done.
    assert "kestrel" in snap.chassis_registry
    assert "Kestrel" in {e.name for e in snap.npc_registry}

    kestrel = snap.chassis_registry["kestrel"]
    bond_before = kestrel.bond_ledger[0].bond_strength_chassis_to_character
    lineage_before = len(kestrel.lineage)
    assert kestrel.bond_ledger[0].bond_tier_chassis == "trusted"

    # 2. Player moves into Galley.
    move_player_to_room(snap, "kestrel:galley")

    # 3. the_tea_brew fired clear_win — bond grew.
    bond_after = kestrel.bond_ledger[0].bond_strength_chassis_to_character
    assert bond_after == pytest.approx(bond_before + 0.06, abs=1e-6)

    # 4. Lineage entry written.
    assert len(kestrel.lineage) == lineage_before + 1
    assert kestrel.lineage[-1].kind == "intimate"

    # 5. Spans fired.
    span_names = {s.name for s in captured_spans}
    assert SPAN_RIG_BOND_EVENT in span_names
    assert SPAN_RIG_CONFRONTATION_OUTCOME in span_names

    # 6. Voice resolver still returns trusted-tier name-form
    #    (bond didn't cross fused threshold yet).
    from sidequest.agents.subsystems.chassis_voice import resolve_chassis_name_form

    class _PC:
        id = "player_character"
        first_name = "Zee"
        last_name = "Jones"
        nickname = None

    assert resolve_chassis_name_form(kestrel, _PC()) == "Zee"
```

- [ ] **Step 2: Run**

```bash
cd sidequest-server && uv run pytest tests/integration/test_kestrel_tea_brew.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Run aggregate gate**

```bash
cd /Users/slabgorb/Projects/oq-2 && just check-all
```

Expected: All green.

- [ ] **Step 4: Manual playtest — full slice demo**

```bash
just up
```

In the UI:
1. Fresh Coyote Star session, character first_name=Zee last_name=Jones.
2. Verify narrator addresses player as "Zee" in chassis dialogue (trusted tier).
3. Navigate to Galley.
4. Verify `the_tea_brew` fires (narrator describes the offering ritual).
5. Open GM panel — confirm `rig.bond_event`, `rig.confrontation_outcome` spans visible.
6. Continue play; navigate out and back to Galley before 6 turns elapse — verify cooldown holds (no second fire).
7. After 6+ turns, re-enter Galley — verify second fire.
8. Repeat enough firings to cross into `fused` (each clear_win adds +0.06 chassis-side; from 0.45 to 0.85 takes ~7 fires). On the cross-event, verify `rig.voice_register_change` span fires AND narrator dialogue shifts name-form (will fall back to "Zee" in slice scope per nickname-deferral, but the span should still fire and GM panel should reflect the tier change).

- [ ] **Step 5: Commit the test**

```bash
cd sidequest-server
git add tests/integration/test_kestrel_tea_brew.py
git commit -m "test(rig): end-to-end Phase C — Galley entry → tea_brew → bond + spans"
```

- [ ] **Step 6: Slice complete.** No release commit; this is a feature branch ready for review and merge per the project's normal flow.

---

## Self-Review

Cross-checked plan against spec:

**1. Spec coverage:**
- Spec §1 content commitment → Tasks 1, 2, 6, 7, 14, 15 ✓
- Spec §2 server changes → Tasks 1–5, 8–11, 16, 17 ✓
- Spec §3 wiring tests → Tasks 12, 16, 17, 19 ✓
- Spec §4 demo path → Tasks 13, 19 ✓
- Spec §5 out-of-scope items → not implemented (correctly absent) ✓
- Spec §6 sequencing → Phase A/B/C structure preserves it ✓
- Spec §7 open questions → addressed inline at point of need (cooldown unit in Task 15 YAML; bond seed character_id resolution in Task 9 comment; voice block precedence in Task 11 default-merge logic; nickname fallback in Task 5 voice resolver) ✓

**2. Placeholder scan:** No "TBD" / "TODO" / "fill in details" / "similar to Task N" / "implement appropriately" patterns. Tasks 8/9/16/17 contain explicit "(adjust to actual function name)" instructions in steps that refer to magic-Phase-5 surface area not yet known — this is intentional dependency-noting, not a placeholder.

**3. Type consistency:**
- `derive_bond_tier` return type `BondTier` consistent in Tasks 1, 3, 5, 11.
- `apply_bond_event` signature: `chassis`, `character_id`, `delta_character`, `delta_chassis`, `reason`, `confrontation_id`, `turn_id` — used identically in Tasks 3, 16.
- `resolve_chassis_name_form(chassis, character)` — Task 5 + Task 11 + Task 19.
- `BondLedgerEntry` fields: `character_id`, `bond_strength_character_to_chassis`, `bond_strength_chassis_to_character`, `bond_tier_character`, `bond_tier_chassis`, `history` — consistent throughout.
- `ChassisInstance` fields: `id`, `name`, `class_id`, `OCEAN`, `voice`, `interior_rooms`, `bond_ledger`, `lineage` — consistent throughout.
- Span constant names: `SPAN_RIG_BOND_EVENT`, `SPAN_RIG_VOICE_REGISTER_CHANGE`, `SPAN_RIG_CONFRONTATION_OUTCOME` — consistent in Tasks 4, 16, 19.

No issues found.

---

## Phase summary

- **Phase A (Tasks 1–13)** — chassis state, spans, content, narrator wiring. Independent. Ships now. Delivers Kestrel speaking with bond-tier-correct name-forms.
- **Phase B (Task 14)** — output catalog + tone-axis doc additions. Independent. Ships now.
- **Phase C (Tasks 15–19)** — `the_tea_brew` end-to-end. Blocked on magic plan Phase 5. Hold.

End of plan.
