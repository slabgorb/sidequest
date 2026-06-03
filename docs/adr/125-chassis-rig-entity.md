---
id: 125
title: "Chassis/Rig as a First-Class Entity — Bidirectional Bond Ledger, Seven-Tier Threshold Ladder, and Interior Render"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [7, 20, 99, 114]
tags: [game-systems, npc-character]
implementation-status: live
implementation-pointer: null
---

# ADR-125: Chassis/Rig as a First-Class Entity

> **Documents a system already live in code.** The `ChassisInstance` state model,
> its bidirectional bond ledger, the seven-tier threshold ladder, the
> `"player_character"` placeholder rebind, the chassis-voice prompt section, and
> the chassis-interior SVG renderer all shipped during the Coyote Star rig MVP
> (Wave 2A, stories 45-47 / 47-6) without a governing ADR. This record closes
> that architecture-of-record gap and states what the decision *was*.

## Context

`space_opera`'s Coyote Star world needed a named ship — the Kestrel — that the
table relates to *as a someone*, not as a line in the inventory. A rig in this
mold has a personality, remembers the moments the crew shared with it, addresses
the pilot differently as trust grows or curdles, and has interior spaces the
party physically occupies. None of the existing entity containers fit:

- **Inventory** is a flat bag of items with no personality, no per-character
  relationship, and no interior. Modeling a ship as an item would have forced
  bond strength, OCEAN, and rooms into item metadata — exactly the kind of
  stringly-typed contortion the project avoids.
- **The NPC roster** (ADR-020) models *people the party meets* with a single
  disposition scalar toward the party. A ship is not met; it is *crewed*, and its
  relationship is per-character and bidirectional, not a single party-wide
  disposition. Worse, projecting the chassis into the NPC roster (the pre-Wave-2A
  approach) put it in the wrong prompt zone and conflated "the AI that speaks
  through the hull" with "the bartender across the room." The legacy
  `npc_registry` projection was dropped in story 45-52.

The locked design (`docs/design/rig-taxonomy.md` decision α — "sibling
framework"; slice spec `docs/superpowers/specs/2026-04-29-rig-mvp-coyote-star-design.md`
§2.1) is that chassis state lives in **its own container**, a sibling of both
inventory and the NPC roster, and reaches the narrator through a **dedicated
voice section** rather than the cast list.

## Decision

**A chassis/rig is a first-class game-state entity — `ChassisInstance` — distinct
from both inventory and the NPC roster. It carries OCEAN, a per-character
bidirectional bond ledger, an intimate-moment lineage, and interior rooms; it is
materialized at world-load from `worlds/<world>/rigs.yaml` into
`GameSnapshot.chassis_registry`; and it reaches the narrator through a dedicated
chassis-voice prompt section, never the NPC roster.**

### Chassis entity model

`ChassisInstance` (`sidequest-server/sidequest/game/chassis.py`) is a
pydantic `BaseModel` (`extra="forbid"`) with: `id`, `name`, `class_id`,
`OCEAN: OceanScores`, an optional `voice: ChassisVoiceSpec`, `interior_rooms:
list[str]`, a `bond_ledger`, and a `lineage`. It lives in its own snapshot
container — `GameSnapshot.chassis_registry: dict[str, ChassisInstance]`
(`sidequest-server/sidequest/game/session.py`), keyed by chassis id —
separate from inventory and from the (now-dropped) `npc_registry`. The module
docstring states the sibling-framework intent and the removal of the NPC
projection (`chassis.py`).

### Bidirectional bond scalars

A bond is **two independent scalars**, not one. `BondLedgerEntry`
(`chassis.py`) holds, per `character_id`:

- `bond_strength_character_to_chassis: float` (how the character feels about the
  ship), and
- `bond_strength_chassis_to_character: float` (how the ship feels about the
  character),

each `Field(default=0.0, ge=-1.0, le=1.0)` — clamped to the closed interval
`[-1.0, 1.0]` at the model boundary. The two directions move independently:
`apply_bond_event` (`chassis.py`) takes separate `delta_character` and
`delta_chassis` and clamps each independently with `max(-1.0, min(1.0, …))`
(`chassis.py`). Each entry also caches a derived tier per side
(`bond_tier_character`, `bond_tier_chassis`) and a `history: list[BondHistoryEvent]`,
where each event records `turn_id`, both deltas, a `reason`, and the optional
`confrontation_id` (`chassis.py`). `lineage` is a parallel append-only log
of intimate moments (`ChassisLineageEntry`, `chassis.py`; appended by
`apply_chassis_lineage_intimate`, `chassis.py`).

### Seven-tier threshold ladder

A bond scalar maps to a discrete tier via a fixed ascending ladder,
`_TIER_THRESHOLDS` (`chassis.py`), consumed by `derive_bond_tier`
(`chassis.py`):

| Scalar range            | Tier        |
|-------------------------|-------------|
| `s < -0.85`             | `severed`   |
| `-0.85 ≤ s < -0.45`     | `hostile`   |
| `-0.45 ≤ s < -0.10`     | `strained`  |
| `-0.10 ≤ s < 0.10`      | `neutral`   |
| `0.10 ≤ s < 0.40`       | `familiar`  |
| `0.40 ≤ s < 0.80`       | `trusted`   |
| `0.80 ≤ s` (≥ 0.80)     | `fused`     |

`derive_bond_tier` walks the ladder and returns the first tier whose ceiling the
scalar is below; the final sentinel ceiling (`1.01`) guarantees that anything at
or above `0.80` falls through to `fused`. The seven tier names are a closed
`Literal` (`BondTier`, `sidequest-server/sidequest/genre/models/chassis.py`).
Both directions are tiered independently from their own scalar
(`chassis.py`).

### Placeholder rebind (`"player_character"`)

World-load and chargen are decoupled flows: `init_chassis_registry` runs at
session bind, before the real player character exists, so it cannot key bond
seeds to a real id. It instead seeds each ledger entry against the placeholder
`character_id="player_character"` taken from the YAML `bond_seeds[].character_role`
(`chassis.py`). `rebind_chassis_bonds_to_character`
(`chassis.py`) closes the loop: at chargen-complete it rewrites every
ledger entry still keyed to `"player_character"` to the real chargen character
id. It is **idempotent** — a second call no-ops entries already keyed to a real
id, and multi-PC scenarios (deferred) will *add* entries rather than overwrite an
existing real-id entry. The rebind is invoked from the chargen mixin alongside
`init_chassis_registry` (`sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py,840`).

### Chassis-voice prompt section (not the NPC roster)

The chassis reaches the narrator through `register_chassis_voice_section`
(`sidequest-server/sidequest/agents/prompt_framework/core.py`), wired
from the orchestrator's prompt assembly (`orchestrator.py`). The
section renders, per voiced chassis, its `default_register`, vocal tics, silence
register, and — critically — the **current bond-tier address form**: the chassis
addresses the active character using `name_forms_by_bond_tier`
(`genre/models/chassis.py`), resolved via `resolve_chassis_name_form`. It
is placed in the Early/State zone alongside (but distinct from) the NPC roster,
because chassis voice is acute identity data, not background lore
(`core.py`). Empty registry or a no-`voice` chassis registers **no
section** (zero-byte-leak discipline, `core.py,733-734`).

## Invariants / Contracts

- **Bond range.** Both `bond_strength_character_to_chassis` and
  `bond_strength_chassis_to_character` are constrained to `[-1.0, 1.0]` at the
  pydantic boundary (`ge=-1.0, le=1.0`, `chassis.py`) and re-clamped on
  every mutation (`chassis.py`). The two directions are independent
  scalars.
- **Tier thresholds.** Tier derivation is the single ladder in
  `_TIER_THRESHOLDS`; `derive_bond_tier` is the only mapping function, and the
  same ladder is mirrored for `bond_tier_min` comparison in confrontation fire
  conditions (`sidequest-server/sidequest/magic/confrontations.py`). The
  seven tier strings are a closed `Literal`.
- **Registry load from `rigs.yaml`.** `init_chassis_registry`
  (`chassis.py`) loads `worlds/<world_slug>/rigs.yaml`, validates it as
  `RigsWorldConfig`, and writes each chassis into
  `snapshot.chassis_registry[chassis.id]`. It is **fail-loud / no-silent-fallback
  on misconfiguration**: when `confrontations.yaml` exists but `magic_state` is
  uninitialized it raises `RuntimeError` (`chassis.py`) — a bind-path
  ordering invariant. It is, however, a deliberate graceful **no-op** (not a
  fallback) when the genre has no `chassis_classes`, the pack has no on-disk
  `source_dir`, or the world authored no `rigs.yaml` (`chassis.py`):
  packs that don't use rigs are simply not rig packs.
- **Bond-mutation precondition.** `apply_bond_event` raises `ValueError` if the
  chassis has no ledger entry for the character — explicitly prompting "was
  world-load bond_seed run?" (`chassis.py`). No silent insert.
- **Interior station integrity.** `validate_chassis_stations`
  (`sidequest-server/sidequest/interior/loader.py`) raises
  `InteriorLoaderError` if any station references a room not in the chassis
  class's `interior_rooms`, listing the valid rooms — fail-loud per No Silent
  Fallbacks.

## Observability

Per the project OTEL Observability Principle (the GM panel is the lie detector),
bond mutations emit telemetry. `apply_bond_event` is intentionally span-free
itself — it returns a `BondEventResult` (`chassis.py`) carrying both
before/after tiers and the two `tier_*_crossed` booleans, and leaves emission to
the caller so unit tests don't pull in the OTEL exporter (`chassis.py`).
The live caller, `_h_bond_strength_growth_via_intimacy`
(`sidequest-server/sidequest/magic/outputs.py`), calls
`emit_rig_bond_event` (`sidequest-server/sidequest/telemetry/spans/rig.py`,
span `rig.bond_event`) with both deltas, both before/after tiers, side,
`confrontation_id`, and register; and when the chassis-side tier *crosses* it
additionally fires `emit_rig_voice_register_change` (`rig.voice_register_change`,
`rig.py`) so a tier-driven change in how the ship speaks is visible in
the panel rather than improvised. Interior renders emit `interior.render`
(`emit_interior_render`, called from `interior/dispatch.py`).

## Consequences

**Positive**

- A ship can be a character-grade *relationship* without being a character or an
  NPC: bidirectional, per-PC, with memory (history + lineage) and a tier-driven
  voice — exactly the Firefly/Serenity texture Coyote Star wants.
- Clean separation of zones: the chassis voice is acute identity data in its own
  prompt section, not buried in the cast roster, so the narrator keeps the ship's
  register consistent turn to turn.
- World authors express a rig entirely in content (`rigs.yaml` instances +
  `chassis_classes.yaml`) with no engine change, honoring the homebrew-authoring
  requirement.
- Fail-loud load and mutation preconditions surface misconfiguration early.

**Negative / cost**

- **Dual keying across the world-load → chargen seam.** The
  `"player_character"` placeholder plus `rebind_chassis_bonds_to_character` is a
  real moving part; a session-start handler that forgets to rebind leaves bonds
  keyed to a placeholder, and `apply_bond_event` will then raise for the real
  character id.
- **Renderer is single-class.** `render_interior_svg`
  (`sidequest-server/sidequest/interior/render.py`) hardcodes the
  voidborn_freighter 2×2 layout and Kestrel crew defaults; generalizing across
  chassis classes is deferred until a second class ships, and the REST endpoint
  currently renders against an empty/stub snapshot (`interior/dispatch.py`)
  rather than the live session — live PC/NPC placement is a follow-on.
- **Slice fields deferred.** Hardpoints, subsystems, damage history, and chassis
  registration/death are named-but-unauthored (`chassis.py`), and returning
  save rehydration of the registry is deferred to a follow-on
  (`chassis.py`).

## Alternatives considered

- **Chassis as an NPC (the pre-Wave-2A approach).** The ship was once projected
  into `npc_registry` as a ship_ai-style NPC. Rejected and removed (story 45-52):
  the NPC model (ADR-020) carries a single party-wide disposition, not a
  per-character bidirectional bond, and it placed the ship in the wrong prompt
  zone (cast roster) where its speaker-voice was indistinguishable from a
  bystander. The dedicated chassis-voice section replaced it.
- **Chassis as inventory.** Rejected: inventory has no personality, no
  per-character relationship scalar, no tier ladder, and no interior — modeling a
  named, OCEAN-bearing, bond-tracked, room-having ship as an item would have
  pushed all of that into item metadata, the stringly-typed contortion the
  project rejects. A rig is an entity, not a possession.

## Reconciliation with existing ADRs

- **ADR-007 (Unified Character Model).** A chassis is **not** a character. It does
  not run through chargen, has no class/level/HP-as-PC sheet, and is not a turn
  actor. It *borrows* OCEAN (the same `OceanScores` shape, `chassis.py`) and
  the relationship vocabulary, but as a distinct `ChassisInstance` type in its own
  registry — ADR-007 governs the player/NPC character model and does not reach the
  chassis data model. The placeholder rebind exists precisely *because* the
  chassis is not a character and is materialized before chargen.
- **ADR-020 (NPC Disposition System).** A chassis is **not** an NPC. ADR-020
  models met persons with a single disposition toward the party; the chassis bond
  is per-character and bidirectional, and the legacy NPC-roster projection was
  removed (story 45-52). ADR-020 governs the NPC roster; the chassis lives in
  `chassis_registry` and surfaces via the chassis-voice section, not the roster —
  ADR-020 does not govern the chassis data model.
- **ADR-099 (Coyote Object Salvage Hooks).** ADR-099's room-entry trigger
  references `fire_conditions: {interior_room_present, bond_tier_min, …}`
  (ADR-099 §"Room-entry trigger"). Those conditions are *consumers* of this
  ADR's model: `interior_room_present` reads the chassis interior, and
  `bond_tier_min` is compared against the **chassis-side** bond tier using this
  ADR's ladder (`sidequest-server/sidequest/magic/confrontations.py,193,247-249`).
  ADR-099 governs the salvage auto-fire hooks; it depends on, but does not define,
  the chassis entity, its bond ledger, or the tier ladder.
- **ADR-114 (Ablative HP Substrate).** ADR-114 mentions `rig_composure_pool.py`
  (ADR-114 ~line 462) as the ship/dogfight **vessel resource pool** —
  `RigComposurePool` (`sidequest-server/sidequest/game/rig_composure_pool.py`),
  the Edge/Composure combat substrate for a vessel in a dogfight. That is the
  ship's *combat-resilience track*, an orthogonal concern from this ADR's
  *relationship/identity* model: `ChassisInstance` carries no HP/composure, and
  `RigComposurePool` carries no bond ledger, OCEAN, voice, or interior. ADR-114
  governs the vessel's lethality/composure substrate; it does not govern the
  chassis-as-entity data model.
