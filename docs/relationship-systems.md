# SideQuest Relationship Systems — Reference Guide

**Audience:** Architect, Dev, world-builder agents, future me.
**Purpose:** Single source of truth for *what relationship machinery exists today* and *what does not*, so design work doesn't reinvent worse versions of systems that already ship.

> **Why this exists:** Multiple times during the openings-redesign brainstorm, the assistant proposed ad-hoc fields like `bond_to_pc_strength`, `bond_to_pc_tier`, `crew_membership.bond` that duplicated — badly — the chassis bond ledger and NPC disposition systems. This guide is the antidote. Read it before adding any field that smells like a relationship.

## Three relationship axes

SideQuest tracks three different kinds of "relationship" today. Each lives in a different model and uses a different mutation surface. **They are not interchangeable.**

| Axis | What it models | Where | Status |
|---|---|---|---|
| **PC ↔ Chassis** | A character's bond with a specific ship | `game/chassis.py` (BondLedgerEntry, apply_bond_event) | Live, fully wired |
| **PC group ↔ NPC** | An NPC's attitude toward the player party | `Npc.disposition` in `game/session.py` | Live, drift (per-PC missing) |
| **NPC enrichment over time** | An NPC's archetype maturity ("spawn → resolved") | `Npc.resolution_tier`, `Npc.non_transactional_interactions` | Field only, P2-deferred |

There is **no** PC ↔ NPC pairwise bond, and no NPC ↔ NPC relationship system. If your design needs either, you are proposing a new system; flag it explicitly and weigh against deferring.

---

## 1. PC ↔ Chassis bond ledger (LIVE)

This is the load-bearing relationship system. The PC's bond with their ship drives ship voice, confrontation eligibility, and visible mechanical state.

### Data shape

- **Two-way strengths**, both in `[-1.0, 1.0]`:
  - `bond_strength_character_to_chassis` — how the character feels about the ship
  - `bond_strength_chassis_to_character` — how the ship feels about the character
- **Seven discrete tiers** derived from strength via `derive_bond_tier`:
  ```
  severed ≤ -0.85 < hostile ≤ -0.45 < strained ≤ -0.10 <
  neutral ≤ 0.10 < familiar ≤ 0.40 < trusted ≤ 0.80 < fused
  ```
- **Per-character ledger** on `ChassisInstance.bond_ledger` (each PC gets their own `BondLedgerEntry`)
- **Audit trail** — every mutation logs a `BondHistoryEvent` with turn_id, deltas, reason, optional confrontation_id

### Authoring (world tier)

In `worlds/{slug}/rigs.yaml`, each `chassis_instance` declares `bond_seeds` — initial values for any character role that boards. Example from `coyote_star/rigs.yaml`:

```yaml
chassis_instances:
  - id: kestrel
    bond_seeds:
      - character_role: player_character
        bond_strength_character_to_chassis: 0.45
        bond_strength_chassis_to_character: 0.45
        bond_tier_character: trusted
        bond_tier_chassis: trusted
        history_seeds:
          - "muscle memory from at least three jumps' worth of patch kits"
```

Pre-bonding at `trusted` is what makes the ship call the PC by their first name on turn 1.

### Mutation

Call `apply_bond_event(chassis, character_id, delta_character, delta_chassis, reason, confrontation_id, turn_id)`. Returns a `BondEventResult` with tier-crossing flags. Caller emits the OTEL span.

### Voice integration

`ChassisVoiceSpec.name_forms_by_bond_tier` maps each tier to a name template:

```yaml
voice:
  name_forms_by_bond_tier:
    severed:  "Pilot"
    hostile:  "Pilot"
    strained: "Pilot"
    neutral:  "Pilot"
    familiar: "Mr. {last_name}"
    trusted:  "{first_name}"
    fused:    "{nickname}"
```

The narrator prompt receives the resolved form. **A bond-tier upgrade lands as a moment in narration** — the ship's name for the PC changes.

### OTEL spans

- `rig.bond_event` — every mutation, includes deltas + tier-crossing flags
- `rig.voice_register_change` — when the resolved name-form changes
- `rig.confrontation_outcome` — when a bond-eligible confrontation resolves

### Confrontation hookup

`InteriorRoomSpec.bond_eligible_for: list[str]` declares which confrontations a room can auto-fire. Example: galley with `bond_eligible_for: [the_tea_brew]`. When a PC with `bond_tier ≥ familiar` enters the room, the confrontation is eligible. Wires through the existing confrontation dispatch path (`server/dispatch/confrontation.py`).

### What it cannot do (today)

- Cross-chassis transfers (bond doesn't "follow" a PC if they switch ships)
- Hardpoints, subsystems, damage history, registration — all deferred per the rig MVP slice
- Bond between characters and *items* (item-legacy plugin uses LedgerBar but is its own system)

### References

- ADR-014 (Diamonds and Coal — accepted)
- `docs/superpowers/specs/2026-04-29-rig-mvp-coyote-star-design.md` (or `coyote-reach` — pre-rename)
- `docs/design/rig-taxonomy.md`
- `sidequest/game/chassis.py`
- `sidequest/genre/models/rigs_world.py` (BondSeed, ChassisInstanceConfig)
- `sidequest/genre/models/chassis.py` (BondTier, ChassisVoiceSpec)
- `sidequest/telemetry/spans/rig.py`

---

## 2. PC group ↔ NPC disposition (LIVE — drift)

This is the simpler, older system. ADR-020. It works, it's wired, but it has known gaps.

### Data shape

```python
class Npc(BaseModel):
    disposition: int = 0  # range [-100, 100]
    # ...
```

### Attitude mapping (hardcoded in `attitude()`)

| Disposition | Attitude |
|---|---|
| `> 10` | `friendly` |
| `-10 to 10` | `neutral` |
| `< -10` | `hostile` |

Three tiers. Thresholds hardcoded; ADR notes they should move to genre-pack config.

### Mutation

The narrator emits a `WorldStatePatch` containing:

```python
npc_attitudes: dict[str, int] = {"Mira Vesh": +5, "Hegemony Inspector": -10}
```

Applied in `session.py:838`:

```python
npc.disposition = max(-100, min(100, npc.disposition + delta))
```

OTEL: `disposition.shift` fires per mutation with before/after/delta.

### Authoring

Today: NPCs default to `disposition: 0` (neutral) on auto-registration. There is **no authoring surface** for pre-seeding disposition — every NPC starts neutral until the narrator shifts them.

**For authored named NPCs (this design):** `AuthoredNpc.initial_disposition: int = 0` is a clean pre-seed. World materialization copies it into `Npc.disposition` when the runtime instance is created.

### Known gaps (called out in ADR-020)

- **Single int per NPC, party-wide** — even in MP, all PCs share the same disposition with each NPC. Mira can't like Zanzibar more than she likes Kael.
- **Three tiers only** — `wary, grateful, terrified, infatuated, contemptuous` etc. don't exist. Designs that need granularity bump against this.
- **Thresholds hardcoded** — should move to genre-pack config (ADR-020 future-work).

### When to use it

Any NPC-as-target relationship rendering — friendly innkeeper, hostile guard, neutral merchant. Crew NPCs in this design pre-seed at `+50` to `+70` (firmly friendly, narrator renders them as warmly disposed).

### When NOT to use it

- Per-PC differentiation (the system can't express it; don't try to fake it with naming tricks)
- Nuance beyond three tiers (don't add wary/grateful/etc. as schema fields; that's a system upgrade, not a per-design hack)
- Character-to-character pairwise (NPC↔NPC) — not what this system models

### References

- ADR-020 (NPC Disposition System — accepted, drift)
- `sidequest/game/session.py` (Npc, npc_attitudes patch, attitude())
- `sidequest/telemetry/spans/disposition.py` (SPAN_DISPOSITION_SHIFT)

---

## 3. NPC resolution tier (FIELD ONLY — P2-deferred)

A planned system for NPC enrichment over time. The longer a PC interacts with an NPC non-transactionally (small talk, repeat encounters not driven by a quest), the more "resolved" the NPC becomes — gaining archetype, OCEAN, deeper backstory.

### Data shape (present, mostly inert)

```python
class Npc(BaseModel):
    resolution_tier: str = "spawn"
    non_transactional_interactions: int = 0
    jungian_id: str | None = None
    rpg_role_id: str | None = None
    npc_role_id: str | None = None
    resolved_archetype: str | None = None
```

### Status

The fields exist for JSON round-trip parity. The counter and tier are **not actively driven** by anything in the runtime today. Don't treat `resolution_tier` as load-bearing. Don't read it from designs.

### When this gets real

Out of scope for any current design. If a future story needs NPC enrichment, that's the moment to read this section more carefully.

---

## Adjacent — often confused with relationship systems

### `BeliefState` (scenario knowledge)

Per-NPC knowledge bubble for mystery scenarios. **What the NPC knows, not how they feel.** Used by Epic 7 (scenario system, `pulp_noir/scenarios/midnight_express`). Mutated by gossip / clue propagation.

If your design is about "Mira knows about Zanzibar's wirework past," that's BeliefState territory, not disposition.

### `Affinity`

Per-affinity tier tracking for *ability progression* (`character.py:53`). Character ↔ skill, not character ↔ character. P6-deferred. Don't confuse with relationship axes.

---

## Don'ts (lessons from past brainstorms)

When designing anything that smells like "relationship," check these first:

1. **Don't add `bond_to_pc_strength` / `bond_to_pc_tier` / `relationship_strength` to NPCs.** Use `disposition` (existing) — and accept its limitations until ADR-020's gaps are properly addressed in a system-upgrade story.

2. **Don't model NPC↔NPC relationships in prose-adjacent fields.** Today the only place they live is authored prose (history_seeds, lore). If a system needs to track "Mira and Ott are a couple" mechanically, that's a new system — design it explicitly, not as a side effect.

3. **Don't conflate chassis bond with NPC disposition.** They have different ranges, different tier counts, different ladders, different OTEL spans, different authoring surfaces. They model different things.

4. **Don't pre-seed NPC disposition by inventing fields elsewhere.** Pre-seeding goes on `AuthoredNpc.initial_disposition`, copied to `Npc.disposition` at world materialization. Single canonical pre-seed surface.

5. **Don't treat `resolution_tier` as a relationship axis.** It's NPC depth, not PC↔NPC connection.

6. **Don't propose granular attitudes (`wary`, `grateful`) without tackling ADR-020's threshold-config gap.** If you need granularity, the right move is a story to lift thresholds into genre-pack config and add tiers there — not to shadow the system with per-design hacks.

7. **Don't track "crew membership" as a relationship.** It's a structural fact ("this NPC is aboard this ship"). Use `chassis_instance.crew_npcs: list[npc_id]` — a flat reference list, no behavior wrapper.

---

## Decision tree for new design work

When a feature needs "relationship-shaped" data:

```
Does the relationship involve a CHASSIS (ship/rig) on one side?
  → Use chassis bond ledger. Pre-seed via rigs.yaml bond_seeds; mutate via apply_bond_event.

Else, does it involve PCs collectively reacting to an NPC (or vice versa)?
  → Use NPC disposition. Pre-seed via AuthoredNpc.initial_disposition;
    mutate via npc_attitudes patches.

Else, is it pairwise PC↔NPC (per-PC differentiation)?
  → STOP. No system today. Either:
     (a) Defer — render the felt relationship in prose, don't track it
     (b) Open a system-design story — this is real new infrastructure

Else, is it NPC↔NPC?
  → STOP. No system today. Render in authored prose (history_seeds, lore);
    do not invent a field.

Else, is it about an NPC growing more "real" over repeated play?
  → resolution_tier exists as a field. Don't depend on it driving anything
    until that subsystem is wired (P2-deferred).
```

---

## Reference index

| Concern | File | Notes |
|---|---|---|
| Chassis bond runtime | `sidequest/game/chassis.py` | BondLedgerEntry, apply_bond_event, derive_bond_tier |
| Chassis bond authoring | `sidequest/genre/models/rigs_world.py` | BondSeed on ChassisInstanceConfig |
| Chassis voice + tiers | `sidequest/genre/models/chassis.py` | BondTier (Literal), ChassisVoiceSpec |
| Chassis OTEL | `sidequest/telemetry/spans/rig.py` | rig.bond_event, rig.voice_register_change |
| NPC runtime | `sidequest/game/session.py` | Npc.disposition, attitude(), npc_attitudes patch |
| NPC OTEL | `sidequest/telemetry/spans/disposition.py` | disposition.shift |
| Bond ADR | `docs/adr/014-diamonds-and-coal.md` | accepted |
| Disposition ADR | `docs/adr/020-npc-disposition.md` | accepted, drift |
| Rig MVP slice | `docs/superpowers/specs/2026-04-29-rig-mvp-coyote-star-design.md` | implementation reference |
| Rig taxonomy | `docs/design/rig-taxonomy.md` | framework |
| Authored NPCs (this design) | `docs/superpowers/specs/2026-05-01-canned-openings-design.md` | introduces AuthoredNpc |

---

*Last updated: 2026-05-01. When you add or change a relationship-shaped system, update this guide.*
