# SideQuest Relationship Systems — Reference Guide

**Audience:** Architect, Dev, world-builder agents, future me. Now also the reference for *what the player sees*, since the relationship state finally reaches the table (ADR-136).
**Purpose:** Single source of truth for *what relationship machinery exists today* and *what does not*, so design work doesn't reinvent worse versions of systems that already ship.

> **Why this exists:** Multiple times during the openings-redesign brainstorm, the assistant proposed ad-hoc fields like `bond_to_pc_strength`, `bond_to_pc_tier`, `crew_membership.bond` that duplicated — badly — the chassis bond ledger and NPC disposition systems. This guide is the antidote. Read it before adding any field that smells like a relationship.

> **Governing ADRs:** This guide tracks four. **ADR-125** (chassis as a first-class entity) and **ADR-128** (the NPC development ladder, among other things) are now the architecture-of-record for systems that previously had none. **ADR-136** added the player-facing surface — relationship state is no longer dev-only. **ADR-053** owns the belief layer the firewall protects.

## The relationship axes

SideQuest tracks several different kinds of "relationship" today. Each lives in a different model and uses a different mutation surface. **They are not interchangeable.**

| Axis | What it models | Where | Status |
|---|---|---|---|
| **PC ↔ Chassis** | A character's bond with a specific ship | `game/chassis.py` (BondLedgerEntry, apply_bond_event) | Live, fully wired (ADR-125) |
| **PC group ↔ NPC** | An NPC's attitude toward the player party | `Npc.disposition` (`game/disposition.py` + `game/session.py`) | Live, wired, **now player-visible** (ADR-020 + ADR-136) |
| **NPC enrichment over time** | An NPC's depth growing on sustained interest (`spawn → acquaintance → established`) | `game/npc_development.py`, `Npc.resolution_tier` | **Live** (ADR-128) — was "field only" pre-2026-05-31 |
| **Player-facing projection** | What the table *sees* of the two axes above | `game/projection/relationships.py`, `RELATIONSHIPS` message | Live (ADR-136) |

There is **no** PC ↔ NPC pairwise bond, and no NPC ↔ NPC relationship system. Disposition is **global** — a single scalar per NPC toward the whole party; per-PC standing is explicitly out of scope (ADR-136, YAGNI). If your design needs either, you are proposing a new system; flag it explicitly and weigh against deferring.

---

## 1. PC ↔ Chassis bond ledger (LIVE — ADR-125)

This is the load-bearing relationship system. The PC's bond with their ship drives ship voice, confrontation eligibility, and visible mechanical state. ADR-125 is the architecture-of-record; ADR-014 (Diamonds and Coal) supplies the underlying philosophy — a ship earns a richer relationship as the crew invests in it.

A chassis is a **first-class entity** (`ChassisInstance`), a sibling of both inventory and the NPC roster — **not** an NPC and **not** an item. It is materialized at world-load into `GameSnapshot.chassis_registry` and reaches the narrator through a dedicated chassis-voice prompt section, never the cast list.

### Data shape

- **Two-way strengths**, both clamped to `[-1.0, 1.0]` at the pydantic boundary (`ge=-1.0, le=1.0`) and re-clamped on every mutation:
  - `bond_strength_character_to_chassis` — how the character feels about the ship
  - `bond_strength_chassis_to_character` — how the ship feels about the character
  - The two directions are **independent scalars** and move separately.
- **Seven discrete tiers** derived from a strength via `derive_bond_tier` against the fixed ladder `_TIER_THRESHOLDS`:
  ```
  s < -0.85           → severed
  -0.85 ≤ s < -0.45   → hostile
  -0.45 ≤ s < -0.10   → strained
  -0.10 ≤ s <  0.10   → neutral
   0.10 ≤ s <  0.40   → familiar
   0.40 ≤ s <  0.80   → trusted
   0.80 ≤ s           → fused
  ```
  Each side caches its own derived tier (`bond_tier_character`, `bond_tier_chassis`). The seven names are a closed `Literal` (`BondTier`).
- **Per-character ledger** on `ChassisInstance.bond_ledger` (each PC gets their own `BondLedgerEntry`).
- **Audit trail** — every mutation appends a `BondHistoryEvent` with `turn_id`, both deltas, `reason`, and optional `confrontation_id`.
- **Lineage** — a parallel append-only log of intimate moments (`ChassisLineageEntry`, appended by `apply_chassis_lineage_intimate`).

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

### The placeholder rebind (`"player_character"`)

World-load and chargen are decoupled. `init_chassis_registry` runs at session bind, **before** the real player character exists, so it seeds each ledger entry against the placeholder `character_id="player_character"` (taken from `bond_seeds[].character_role`). At chargen-complete, `rebind_chassis_bonds_to_character` rewrites every entry still keyed to `"player_character"` to the real chargen id. It is **idempotent** — a second call no-ops entries already keyed to a real id. A session-start handler that forgets to rebind leaves bonds keyed to the placeholder, and `apply_bond_event` will then raise for the real character id (no silent insert).

### Mutation

Call `apply_bond_event(chassis, character_id, delta_character, delta_chassis, reason, confrontation_id, turn_id)`. It clamps each direction independently and returns a `BondEventResult` carrying before/after tiers and `tier_*_crossed` flags. It is intentionally **span-free** — the caller emits the OTEL span. It **raises `ValueError`** if the chassis has no ledger entry for the character ("was world-load bond_seed run?").

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

The chassis-voice prompt section (`register_chassis_voice_section`) resolves the current address form via `resolve_chassis_name_form` and places it in the Early/State zone — acute identity data, distinct from the NPC roster. An empty registry or a no-`voice` chassis registers **no section** (zero-byte-leak discipline). **A bond-tier upgrade lands as a moment in narration** — the ship's name for the PC changes.

### OTEL spans

- `rig.bond_event` — every mutation, includes both deltas + before/after tiers + side + tier-crossing flags
- `rig.voice_register_change` — when the chassis-side tier crosses and the resolved name-form changes
- `interior.render` — interior renders

### Confrontation hookup

`InteriorRoomSpec.bond_eligible_for: list[str]` declares which confrontations a room can auto-fire. `bond_tier_min` fire conditions are compared against the **chassis-side** bond tier using the same `_TIER_THRESHOLDS` ladder (`magic/confrontations.py`). Wires through the existing confrontation dispatch path.

### What it cannot do (today)

- Cross-chassis transfers (bond doesn't "follow" a PC if they switch ships)
- Hardpoints, subsystems, damage history, registration/death — all named-but-unauthored per the rig MVP slice
- Returning-save rehydration of the registry — deferred
- The interior renderer is **single-class** (hardcodes the voidborn_freighter 2×2 / Kestrel layout); the REST endpoint renders against a stub snapshot, not the live session
- Bond between characters and *items* (item-legacy plugin uses LedgerBar but is its own system)
- **Combat resilience.** A ship's dogfight Edge/Composure track is `RigComposurePool` (`game/rig_composure_pool.py`, ADR-114) — an orthogonal substrate. `ChassisInstance` carries no HP; `RigComposurePool` carries no bond ledger. Don't conflate identity with lethality.

### References

- ADR-125 (Chassis/Rig as a First-Class Entity — accepted, live) — **architecture-of-record**
- ADR-014 (Diamonds and Coal — accepted) — philosophy
- ADR-114 (Ablative HP Substrate) — the orthogonal `RigComposurePool` combat track
- `docs/design/rig-taxonomy.md`
- `sidequest/game/chassis.py` (BondLedgerEntry, apply_bond_event, derive_bond_tier, _TIER_THRESHOLDS, rebind_chassis_bonds_to_character)
- `sidequest/genre/models/rigs_world.py` (BondSeed, ChassisInstanceConfig)
- `sidequest/genre/models/chassis.py` (BondTier, ChassisVoiceSpec)
- `sidequest/telemetry/spans/rig.py`

---

## 2. PC group ↔ NPC disposition (LIVE — ADR-020, now player-visible)

The simpler, older system (ADR-020). It works and it's wired. Two things changed since this guide's first draft: disposition is now a **typed wrapper** with **configurable** thresholds (not a raw hardcoded int), and the state finally reaches the player (ADR-136, §4 below).

### Data shape

Disposition is no longer a bare `int`. It is a `Disposition` wrapper (`game/disposition.py`) over a clamped int in `[-100, +100]`:

```python
class Npc(BaseModel):
    disposition: Disposition = Field(default_factory=Disposition)  # session.py
    # ...
```

`Disposition` clamps in its constructor, exposes `.value` and an `.attitude()` method, and supports pydantic coercion from a raw int (`Npc(disposition=15)` still works). `int(npc.disposition)` reads the clamped value.

### Attitude mapping (configurable — ADR-020 future-work, now done)

`.attitude()` returns an `Attitude` enum via `AttitudeThresholds` (story 50-13 lifted the thresholds out of hardcode into config):

| Disposition | Attitude (default thresholds) |
|---|---|
| `> friendly_at` (default `10`) | `FRIENDLY` |
| between the two | `NEUTRAL` |
| `< hostile_at` (default `-10`) | `HOSTILE` |

Three engine tiers. The defaults match the old hardcoded values, but they now live in `AttitudeThresholds` config — the ADR-020 "thresholds should move to genre-pack config" gap is closed.

> **Note the two band vocabularies.** The engine `Attitude` enum is 3-level (FRIENDLY/NEUTRAL/HOSTILE). The *player-facing* display band (§4) is 5-level (Hostile/Cool/Neutral/Warm/Devoted) — a presentation label computed at projection that does **not** alter the engine enum. Keep them separate: presentation tuning never touches engine thresholds.

### Mutation

The narrator emits a `WorldStatePatch` containing:

```python
npc_attitudes: dict[str, int] = {"Mira Vesh": +5, "Hegemony Inspector": -10}
```

Applied in `session.py` (the `npc_attitudes` branch, ~line 1664) — the canonical mutation site:

```python
before = int(npc.disposition)
npc.disposition = Disposition(before + delta)   # clamps to ±100 in __init__
after = int(npc.disposition)
# ... emit disposition.shift span ...
npc.record_disposition_beat(turn=..., delta=delta, reason=..., location=...)
```

The constructor clamps; there is no separate `max/min` call. **Every mutation site must call `record_disposition_beat`** — a missed site silently drops history (ADR-136 standing coupling; mitigated by routing all mutations through the one seam plus a wiring test).

OTEL: `disposition.shift` fires per mutation with before/after/delta; `relationship.beat_recorded` fires per beat appended.

### The disposition beat-log (ADR-136)

`Npc.disposition_log: list[DispositionBeat]` is a bounded ring buffer. Each `DispositionBeat` (`game/disposition.py`) carries `turn`, `delta`, `reason`, `location`. It **persists the delta + reason the engine already computes** — data that previously lived only in transient OTEL spans. This is what makes the surface a relationship *story* (ADR-014), not a reputation bar. The recent-window trend is **derived** (sign of summed deltas), not stored.

### Authoring

NPCs default to `disposition: 0` (neutral) on auto-registration. Pre-seeding goes on `AuthoredNpc.initial_disposition: int = 0`, copied into `Npc.disposition` at world materialization. This is the single canonical pre-seed surface — do not invent pre-seed fields elsewhere. Crew NPCs are typically pre-seeded `+50`–`+70` (firmly friendly).

### Known gaps

- **Single int per NPC, party-wide** — even in MP, all PCs share one disposition with each NPC. Mira can't like Zanzibar more than she likes Kael. Per-PC standing is a separate, larger ADR (ADR-136 keeps it out of scope, YAGNI).
- **Three engine tiers** — `wary, grateful, terrified, infatuated` etc. don't exist in the engine enum. The 5-level *display* band adds presentation nuance but the engine still resolves three.

### When to use it

Any NPC-as-target relationship rendering — friendly innkeeper, hostile guard, neutral merchant — and any felt warmth/cooling the table should see.

### When NOT to use it

- Per-PC differentiation (the system can't express it; don't fake it with naming tricks)
- More than three *engine* tiers as schema fields (don't add `wary`/`grateful` to the enum; that's a system upgrade)
- Character-to-character pairwise (NPC↔NPC) — not what this system models

### References

- ADR-020 (NPC Disposition System — accepted)
- ADR-136 (player-facing surface, beat-log)
- `sidequest/game/disposition.py` (Disposition, DispositionBeat, Attitude, AttitudeThresholds)
- `sidequest/game/session.py` (Npc, npc_attitudes patch, record_disposition_beat)
- `sidequest/telemetry/spans/disposition.py` (SPAN_DISPOSITION_SHIFT)
- `sidequest/telemetry/spans/relationship.py` (relationship.beat_recorded)

---

## 3. NPC development ladder (LIVE — ADR-128)

> **Status change.** This section used to read "FIELD ONLY — P2-deferred." It is no longer. ADR-128 (story 72-1) revived the dormant ADR-014 coal→diamond promotion path for NPCs. The fields are now **actively driven**.

The longer a PC engages an NPC non-transactionally (small talk, repeat encounters not driven by a quest), the more "resolved" the NPC becomes — earning depth along a monotonic, named tier ladder.

### Data shape (live)

```python
class Npc(BaseModel):
    resolution_tier: str = "spawn"
    non_transactional_interactions: int = 0
    # ... resolved_archetype, jungian_id, rpg_role_id, etc. (round-trip fields) ...
```

### The ladder

```
spawn → acquaintance → established
```

`develop_npc_on_engagement(npc) -> DevelopmentTick` (`game/npc_development.py`) runs on each **non-transactional** engagement — a narrator cite that resolves to an existing stateful `Npc` (the `npcs_hit` branch of narration apply):

- `non_transactional_interactions` increments (the interest signal).
- `resolution_tier` escalates via `tier_for_interactions(...)` at fixed thresholds: `ACQUAINTANCE_AT = 3`, `ESTABLISHED_AT = 8`.
- `disposition` warms by `DISPOSITION_DRIFT_PER_MILESTONE = 2` **on each tier escalation** (not per mention — renamed from `…_PER_ENGAGEMENT` per the 2026-06-07 ping-pong), applied through the clamping `Disposition` constructor.

The function returns a frozen `DevelopmentTick` (before/after tier, disposition, attitude); the caller emits the development-tick and `disposition.shift` spans from it.

### Load-bearing invariant: threshold > 1

**A single engagement — or a lone combat hit — never promotes.** The lowest earned tier (`acquaintance`) requires 3 interactions. Depth is *earned over sustained interest*, not bought with one mechanical touch. This keeps drive-by combat from inflating the stateful-NPC roster, and it is exactly ADR-014's "player shows genuine interest" trigger expressed for NPCs.

### References

- ADR-128 (Trope Governor + Seed Deck + NPC Development Ladder — accepted, live)
- ADR-014 (Diamonds and Coal)
- `sidequest/game/npc_development.py` (develop_npc_on_engagement, tier_for_interactions, DevelopmentTick, constants)

---

## 4. Player-facing relationship surface (LIVE — ADR-136)

> **New since 2026-06-01.** Until this shipped, all of the above was **server-only** — the disposition dial moved correctly but none of it reached the table. ADR-136 put it on the wire and on screen, serving both the narrative players (a band) and the mechanics-first players (the number, on demand).

### The reactive `RELATIONSHIPS` message

A dedicated reactive message (`RelationshipsMessage` / `RelationshipsPayload`), following the per-domain message+panel pattern (KNOWLEDGE, LOCATION, MAP each have their own — ADR-026/027). It is emitted **when the relationship set changes** (a disposition shift, a new NPC promoted into the stateful roster, a claim recorded) — **not every turn** (Cost Scales with Drama). It carries one `RelationshipEntry` per NPC in `snapshot.npcs` — the **promoted, stateful roster** (people the party actually engaged), **not** the transient `npc_pool`.

### Hybrid fidelity (the ADR-040 reconciliation)

The resting display is a **narrative attitude band with a trend arrow** (ADR-040-compliant — no raw stats by default). The **raw disposition integer and recent deltas reveal on demand** (progressive disclosure / expand). Narrative players (James/Alex) see a band; mechanics-first players (Sebastien/Jade) pop the number. The same hybrid governs personality: a narrative **personality read** by default, the numeric `OceanProfile` (0..10) on a further expand.

### The 5-level display band

A presentation label computed at projection (`game/projection/relationships.py`):

| Disposition value | Band |
|---|---|
| `≥ 50` | Devoted |
| `≥ 10` | Warm |
| `> -10` | Neutral |
| `> -50` | Cool |
| `< -50` (`≤ -50`) | Hostile |

This is presentation only — it does **not** change the engine's 3-level `Attitude` enum.

### OCEAN materialization

The materializer copies `AuthoredNpc.ocean` (authored 0..1 scale, short keys) → `Npc.ocean` via `OceanProfile.from_authored()` (×10 to the runtime 0..10 scale). NPCs with **no** authored OCEAN keep `ocean=None` and the panel shows no personality read — **absence is shown as absence, never fabricated** (No Silent Fallbacks). This is what stopped authored OCEAN (`sidequest-content #318`) from being dead data.

### The claims-only belief firewall (the spoiler boundary)

This is the load-bearing rule that lets belief depth be shown at all in a mystery world. At projection, `claims_to_party(belief_state)` filters `belief_state.beliefs` to **`BeliefClaim` entries only** (things the NPC has openly expressed to the party), plus a coarse `credibility_hint`. **All `BeliefFact` and `BeliefSuspicion` entries are dropped** — they are the mystery's solution (ADR-053). The murderer's private guilt-knowledge can never reach a panel row. A test plants a Fact and a Suspicion and asserts neither crosses.

### OTEL

- `relationship.beat_recorded` — every beat appended to a disposition log (the second lie-detector on a subsystem that previously emitted only ephemeral spans).

### References

- ADR-136 (Player-Facing Relationship Surface — accepted, live)
- ADR-040 (Narrative Character Sheet — No Raw Stats) — the doctrine the hybrid reconciles
- ADR-104/105 (perception firewall) — the projection composes with this chain
- `sidequest/game/projection/relationships.py` (band logic, claims_to_party)
- `sidequest/protocol/messages.py` (RelationshipsMessage/Payload), `sidequest/protocol/models.py` (RelationshipEntry)
- `sidequest/genre/models/ocean.py` (OceanProfile.from_authored), materialized in `sidequest/game/world_materialization.py`
- `sidequest-ui` relationship panel (PRs sidequest-server#574, sidequest-ui#311)

---

## Adjacent — often confused with relationship systems

### `BeliefState` (scenario knowledge — ADR-053)

Per-NPC knowledge bubble for mystery scenarios. **What the NPC knows, not how they feel.** Three epistemic categories: `BeliefFact` (known true), `BeliefSuspicion` (uncertain), `BeliefClaim` (stated to others, credibility-weighted). Lives in `game/belief_state.py`; bound via `game/scenario_state.py`.

If your design is about "Mira knows about Zanzibar's wirework past," that's BeliefState territory, not disposition. The **only** belief category that crosses into the player-facing relationship panel is `BeliefClaim`, via the §4 firewall — Facts and Suspicions never leave the server.

> **Restoration note:** ADR-053 is marked `partial` because the Python port left the live-mutation engines dark. Those have since been restored: `game/gossip_engine.py` (two-phase propagation, credibility decay) and `game/accusation.py` (verdict scoring) now exist. Treat ADR-053's "what is dark" list as historical; verify current behavior against the code before relying on it.

### `AffinityState` (ability progression)

Per-affinity tier tracking for *ability progression* (`game/character.py`, `Character.affinities`). Character ↔ skill, not character ↔ character. P6-deferred. Don't confuse with relationship axes.

### Trope governor & seed deck (ADR-128, non-relationship half)

ADR-128 also governs trope tempo (`trope_tuning.py`, `trope_tick.py`, `trope_time_skip.py`) and the resume-safe seed-trope deck (`seed_deck.py`, `seed_tick.py`). These are **pacing** systems, not relationships — listed here only so you don't go looking for them under "relationships." The NPC development ladder (§3) is the one relationship-relevant piece of ADR-128.

---

## Don'ts (lessons from past brainstorms)

When designing anything that smells like "relationship," check these first:

1. **Don't add `bond_to_pc_strength` / `bond_to_pc_tier` / `relationship_strength` to NPCs.** Use `disposition` (existing) — now a typed `Disposition` wrapper with configurable thresholds.

2. **Don't model NPC↔NPC relationships in prose-adjacent fields.** Today the only place they live is authored prose (history_seeds, lore). A mechanical "Mira and Ott are a couple" tracker is a new system — design it explicitly.

3. **Don't conflate chassis bond with NPC disposition.** Different ranges (`[-1,1]` vs `[-100,100]`), tier counts (7 vs 3 engine / 5 display), ladders, OTEL spans, authoring surfaces, and entity homes (a chassis is its own first-class entity, ADR-125 — not an NPC, not an item). They model different things.

4. **Don't pre-seed NPC disposition by inventing fields elsewhere.** Pre-seeding goes on `AuthoredNpc.initial_disposition`, copied to `Npc.disposition` at world materialization. Single canonical pre-seed surface.

5. **Don't treat `resolution_tier` as a relationship *axis*.** It's NPC depth (now live, ADR-128), not PC↔NPC connection. But do *not* treat it as inert anymore either — it is actively driven.

6. **Don't reach for the player-facing band in engine logic.** The 5-level display band is a projection label; engine decisions read the 3-level `Attitude` enum. Two vocabularies, kept deliberately separate.

7. **Don't leak Facts or Suspicions into any player surface.** The relationship panel shows `BeliefClaim` only. If you add a new player-facing belief view, it goes through `claims_to_party` — never the raw `belief_state`.

8. **Don't track "crew membership" as a relationship.** It's a structural fact ("this NPC is aboard this ship"). Use `chassis_instance.crew_npcs: list[npc_id]` — a flat reference list, no behavior wrapper.

9. **Don't add a disposition mutation site without `record_disposition_beat`.** A missed seam silently drops history. Route every mutation through the one seam.

---

## Decision tree for new design work

When a feature needs "relationship-shaped" data:

```
Does the relationship involve a CHASSIS (ship/rig) on one side?
  → Use chassis bond ledger (ADR-125). Pre-seed via rigs.yaml bond_seeds;
    mutate via apply_bond_event. (Combat resilience is RigComposurePool, not this.)

Else, does it involve PCs collectively reacting to an NPC (or vice versa)?
  → Use NPC disposition (ADR-020). Pre-seed via AuthoredNpc.initial_disposition;
    mutate via npc_attitudes patches; always record_disposition_beat.

Else, does the player need to SEE the relationship?
  → It's already projected. The RELATIONSHIPS message (ADR-136) renders disposition
    band + trend, OCEAN read, and claims. Don't build a second surface; extend the
    projection. New belief views go through claims_to_party.

Else, is it about an NPC growing more "real" over repeated play?
  → Use the development ladder (ADR-128). It's live: develop_npc_on_engagement
    drives resolution_tier on sustained non-transactional interest (threshold > 1).

Else, is it pairwise PC↔NPC (per-PC differentiation)?
  → STOP. No system today (ADR-136 keeps it out of scope). Either:
     (a) Defer — render the felt relationship in prose, don't track it
     (b) Open a system-design story — this is real new infrastructure

Else, is it NPC↔NPC?
  → STOP. No system today. Render in authored prose (history_seeds, lore);
    do not invent a field.
```

---

## Reference index

| Concern | File | Notes |
|---|---|---|
| Chassis bond runtime | `sidequest/game/chassis.py` | BondLedgerEntry, apply_bond_event, derive_bond_tier, _TIER_THRESHOLDS, rebind_chassis_bonds_to_character |
| Chassis bond authoring | `sidequest/genre/models/rigs_world.py` | BondSeed on ChassisInstanceConfig |
| Chassis voice + tiers | `sidequest/genre/models/chassis.py` | BondTier (Literal), ChassisVoiceSpec |
| Chassis OTEL | `sidequest/telemetry/spans/rig.py` | rig.bond_event, rig.voice_register_change |
| NPC disposition model | `sidequest/game/disposition.py` | Disposition, DispositionBeat, Attitude, AttitudeThresholds |
| NPC runtime | `sidequest/game/session.py` | Npc, npc_attitudes patch (~:1664), record_disposition_beat |
| NPC development ladder | `sidequest/game/npc_development.py` | develop_npc_on_engagement, tier_for_interactions, DevelopmentTick |
| Disposition OTEL | `sidequest/telemetry/spans/disposition.py` | disposition.shift |
| Relationship projection | `sidequest/game/projection/relationships.py` | 5-level band, claims_to_party firewall |
| Relationship message | `sidequest/protocol/messages.py`, `.../models.py` | RelationshipsMessage/Payload, RelationshipEntry |
| OCEAN normalization | `sidequest/genre/models/ocean.py` | OceanProfile.from_authored (0..1 → 0..10); applied in `game/world_materialization.py` |
| Relationship OTEL | `sidequest/telemetry/spans/relationship.py` | relationship.beat_recorded |
| Belief state | `sidequest/game/belief_state.py` | BeliefFact/Suspicion/Claim, BeliefState |
| Scenario binding | `sidequest/game/scenario_state.py` | ScenarioState, from_genre_pack |
| Affinity | `sidequest/game/character.py` | AffinityState (P6-deferred) |
| Chassis ADR | `docs/adr/125-chassis-rig-entity.md` | accepted, live |
| Disposition ADR | `docs/adr/020-npc-disposition-system.md` | accepted |
| Development-ladder ADR | `docs/adr/128-trope-governor-seed-deck.md` | accepted, live |
| Player-surface ADR | `docs/adr/136-player-facing-relationship-surface.md` | accepted, live |
| Scenario ADR | `docs/adr/053-scenario-system.md` | accepted, partial |
| Diamonds and Coal | `docs/adr/014-diamonds-and-coal.md` | philosophy |

---

*Last updated: 2026-06-09 (story 99-1 — rewrite to ADR-125/128/136/053). When you add or change a relationship-shaped system, update this guide.*
