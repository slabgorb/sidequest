---
id: 114
title: "Ablative HP Substrate — HP Reclaims the Lethality Track Beneath the Dials"
status: accepted
date: 2026-05-25
deciders: ["Keith Avery", "Sebastien", "Jade", "Leonard of Quirm (Architect)"]
supersedes: [78]
superseded-by: null
related: [14, 21, 33, 40, 74, 75]
tags: [game-systems]
implementation-status: partial
implementation-pointer: docs/superpowers/plans/completed/2026-05-25-swn-hp-substrate.md
---

# ADR-114: Ablative HP Substrate — HP Reclaims the Lethality Track Beneath the Dials

> **Supersedes ADR-078** (Edge / Composure Combat). ADR-078's central move —
> deleting HP and replacing it with EdgePool as the personal vitality track —
> is reversed here. The pieces of ADR-078 that were *not* the Edge-as-HP
> surrogate (push-currency rituals, the progression→engine advancement link)
> survive; see §4. Read ADR-078 for the history of why Edge was tried.

## Context

### The playgroup mandate

This is a direct, playgroup-level request, not an architecture-led optimization.
The two mechanics-first players — **Sebastien** and **Jade** (a forever-GM who
also authors content) — ran the 5-hour, 140+ turn `coyote_star` session *while
the confrontation engine was broken*. They carried it on narrative, NPC, and
relationship strength alone, and came away saying the same thing: they miss the
crunch. They want **SWN-style mechanics** — concrete, legible numbers under the
fiction. Keith authorized reintroducing ablative HP and explicitly accepted that
this supersedes ADRs: *"I want to please them, and it isn't like I want to die
on the hill."*

The full umbrella design is approved at
`docs/superpowers/specs/2026-05-25-swn-crunch-ablative-hp-design.md`. This ADR
executes **Part 1** of that spec — the engine reversal — and resolves the open
forks the spec handed to the Architect.

### What ADR-078 actually built, and what it cost

ADR-078 diagnosed a real bug: combat was "a story the narrator tells about a
number that does not exist" — HP fields existed on `CreatureCore` but no beat
ever wrote to them. Its fix was to **delete HP** and introduce `EdgePool`
(composure) as a deflection-against-pressure track: a level-10 fighter doesn't
eat fifteen sword blows, he *doesn't let the hit land* until his composure
breaks.

The diagnosis was correct. The fix overshot. In practice:

- **Edge became "HP with extra steps."** ADR-078 itself named this as its design
  failure mode (Risk §3). The smoke-gate that was supposed to let Keith *feel*
  the difference shipped, and the difference didn't land for the mechanics-first
  players. SWN — the system they're explicitly asking for — has **no composure
  track at all**. It has HP. Asking for SWN crunch and getting a bespoke
  composure abstraction is the mismatch.
- **The damage channel never wired anyway.** Per ADR-078's own implementation
  status (2026-05-02): the `composure_break` OTEL span has *zero hits*, per-class
  edge config is an unwired placeholder (`world_materialization.py`), and the
  advancement effects that mutate Edge are loaded-but-dark (Epic 39). The thing
  ADR-078 promised — engine-validated combat the GM panel can audit — is owed,
  not delivered.
- **We were already discarding authored HP.** Content YAML carries B/X HP today.
  `creature_edge_pool_from_hp()` (`creature_core.py`) translates that authored HP
  *away* into a composure pool at the materializer seam. We author HP, then throw
  the number out. This ADR's central move is largely **stop discarding what we
  already write.**

### The two-layer thesis (from the spec)

Give the crunch back **without** sacrificing the narrative layer that carried the
broken-engine game. Two layers, **not two rivals**:

1. **The dial / confrontation engine (ADR-033)** stays exactly as-is — the
   `momentum` / `leverage` / `engagement_range` metric dials and the
   strike/brace/angle/push beats. This is the **narrative pacing layer**. It
   answers *how the fiction moves this round*. James and Alex engage here.
2. **Ablative HP** returns as the **lethality substrate underneath**. It answers
   *how close to dead you are*. Concrete, visible, dice-driven. Sebastien and
   Jade engage here.

The broken-engine session is the proof: with the dials not firing, there was
*neither* layer. Restoring HP gives a floor of mechanical truth even when only
the narrative is running. HP is **additive under the dials** — it does not
replace them.

### What we take from SWN, and what we don't

> **Steal the nouns and the flavor. Leave SWN's resolution math.**

- **Adopt:** the ablative HP lethality model; SWN-native damage dice
  (`1d6 … 2d12`) so values are concrete and feed the existing dice overlay.
- **Skip:** SWN's d20-to-hit-vs-Armor-Class, 2d6 roll-under skill checks, the
  saving-throw table, Strength-based encumbrance. SideQuest keeps its own
  resolution (the dials + the existing player-facing dice system). HP is the
  piece being adopted, not the whole SWN combat procedure.

## Decision

### 1. HP returns as a first-class runtime vitality pool (`HpPool`)

`CreatureCore` carries an `HpPool` — `current` / `max` / `base_max` — as its
personal vitality track. This replaces `EdgePool` in the damage/lethality role.

```python
class HpPool(BaseModel):
    model_config = {"extra": "forbid"}
    current: int      # clamped to [0, max]
    max: int
    base_max: int     # pre-advancement ceiling
```

**Seeding follows ADR-078's own CON-mod amendment, re-pointed at HP.** The
2026-05-10 amendment to ADR-078 established `base_max = class_base + CON_modifier`
(floored at 1). That seed logic was sound; only its *target* changes. Chargen
seeds HP from `rules.yaml`'s class baseline plus the CON modifier
(`floor((CON − 10) / 2)`), floored at 1. The genre lever (`base_max_by_class`)
and the "everyone has some vitality" invariant both carry forward intact.

**De-risk: this is mostly deletion of a translation, not new construction.** The
content YAML already carries B/X HP. The materializer seam
(`world_materialization.py` `_apply_npc()` and the dungeon CR→Edge path) currently
runs `creature_edge_pool_from_hp()` to *convert HP into composure*. That
conversion is **removed**: the authored `hp` integer now seeds `HpPool` directly
(`current == max == base_max == authored_hp`, floored at 1). The single canonical
translator becomes `hp_pool_from_hp()` — an identity-ish seeder, not a
re-interpretation. ADR-014's requirement that creatures materialize with a vitality
pool is satisfied by HP rather than Edge; the "gaslight the narrator with game
state" doctrine (materialize creatures into `snap.npcs` with real vitality) is
unchanged in shape.

### 2. The HP-damage channel on the confrontation engine (Fork 2)

The dials are untouched. Beats keep `momentum` / `leverage` / `engagement_range`
semantics. Underneath, beats gain an **optional damage channel** declared on
`BeatDef`:

```python
# genre/models/rules.py — BeatDef, parallel to the existing edge_delta/gold_delta fields
damage_channel: DamageChannel = DamageChannel.none   # none | strike | brace
damage_override: DamageSpec | None = None            # creature natural attacks (no catalog weapon)
mitigation_override: int | None = None               # brace beats with no armor item
```

Resolution at beat-apply time:

- **`strike`** — the engine looks up the acting actor's equipped-weapon
  `CatalogItem.damage` (§3); if the actor has no catalog weapon, it falls back to
  `damage_override` on the beat (a creature's claws/bite) or the genre's declared
  `unarmed_damage` default. That damage **rolls through the existing player-facing
  dice system** (ADR-074 protocol, ADR-075 3D overlay) — the same
  `DiceRequestPayload` → Rapier → `resolve_dice_with_faces` flow that already
  resolves beat checks. The settled total, minus the target's mitigation, is
  applied to `target.hp`. **The damage roll is a 3D roll the whole table watches.**
  This *is* Sebastien's "show me the math" — the rail already exists; HP gives it
  something to subtract from.
- **`brace`** — applies the actor's armor mitigation (`CatalogItem.mitigation`, §3)
  or `mitigation_override` as damage reduction against incoming strikes for the
  round. Brace is the SWN-flavored "soak," not a heal.
- **`angle` / `push`** — `damage_channel: none`. Pure dial beats. They move the
  narrative metric and never touch HP. The narrative pacing layer is preserved
  exactly.

**Why a tagged channel and not a flat `hp_delta`.** A flat integer baked into the
beat would bypass the dice overlay and make every strike deal identical damage
regardless of weapon — the opposite of legible crunch. Tagging the beat with
*intent* (`strike`/`brace`) and sourcing the *number* from the equipped weapon's
dice means the catalog (Lane A) carries lethality, the dice overlay shows it
resolve, and authoring a combat beat stays a one-line `damage_channel: strike`.
**Reuse-first:** no new dice plumbing — the beat-check path in
`server/dispatch/dice.py` already builds `DiceRequestPayload` from `DieSpec` /
`DieSides`; damage dice are the same payload with the weapon's faces.

**Relationship to the existing `apply_damage` narrator tool (2026-05-25 addendum).**
There is *already* a narrator-side damage path: `agents/tools/apply_damage.py`
translates the narrator's `apply_damage(target, amount)` into a vitality delta and
emits a `tool.damage.*` OTEL span. Under ADR-078 it debited Edge; under this ADR it
debits HP (`apply_hp_delta`, span attribute `tool.damage.target_hp_after`). The two
paths are **kept as complementary surfaces, not merged** (decided 2026-05-25):
- The **beat `strike`/`brace` channel** is the *player-facing dice-combat* path — the
  player clicks a beat, the weapon's damage dice roll on the 3D overlay, the table
  watches the wound land.
- The **`apply_damage` tool** is the *narrator's freeform-adjudication* path — the
  trap, the fall, the off-screen sniper, the environmental hazard the narrator
  prices without a player beat.
Both mutate the same `HpPool` and both emit a `state_patch`/`tool.damage` span, so
the GM panel audits either route. This is a "wire up what exists" correction: the
narrator damage tool predates this ADR and is re-pointed, not reinvented.

The criterion ADR-078 established for combat ConfrontationDefs ("must include at
least one Edge-recovery beat") is **retired** — attrition is no longer a composure
ratchet. Its HP analogue is the genre's choice to author rest/medkit/`Lift`-stim
recovery beats or items (Lane A pharmacopeia), not an engine requirement.

### 3. `CatalogItem.damage` and `CatalogItem.mitigation` schema (Fork 3)

`CatalogItem` is `extra="forbid"` (`genre/models/inventory.py`), so this is
a model change. Two optional fields are added:

```python
class DamageSpec(BaseModel):
    model_config = {"extra": "forbid"}
    dice: str            # SWN-native: "1d6", "1d8", "1d10", "1d12", "2d6", "2d12"…
    bonus: int = 0       # flat add to the rolled total

class CatalogItem(BaseModel):
    # … existing fields unchanged …
    damage: DamageSpec | None = None        # weapons
    mitigation: int | None = None           # armor: flat damage reduction (SWN "soak")
```

- `damage.dice` is parsed by the **existing** dice grammar and must validate at
  **pack-load time** — an unparseable or unsupported-face string fails loudly
  (`extra="forbid"` discipline; no silent fallback). The supported faces
  (`D4/D6/D8/D10/D12/D20/D100` in `protocol/dice.py`) cover the full SWN
  `1d6…2d12` range, so every SWN weapon value maps directly to a roll the overlay
  renders.
- `mitigation` is a flat integer (SWN armor reduces damage by a small constant);
  no AC, no to-hit table — consistent with "skip SWN's resolution math."
- **Coordination with Lane A.** The gear/pharmacopeia plan
  (`docs/superpowers/plans/2026-05-25-swn-gear-pharmacopeia.md`) explicitly
  deferred the `damage` field to this ADR ("rides Plan #1 — HP substrate"). That
  plan authored relative lethality via `power_level` / `tags` as a placeholder.
  Once this model change lands, Lane A weapons gain concrete `damage:` descriptors
  and armor gains `mitigation:`, and the stim pharmacopeia's HP-relevant items
  (`Lift`, `Lazarus patch`, `Bezoar`) wire to the HP pool. **The field is added
  here; the catalog values are authored in Lane A.** No stubs in between — the
  field lands with real consumers (Lane A) in the same wave.

### 4. Fate of Edge's non-damage roles (Fork 1) — RESOLVED

ADR-078 gave Edge three jobs. They are disposed of as follows.

**4a. Vitality / damage track → RETIRED.** HP reclaims it (§1). `EdgePool` is
removed from `CreatureCore` as the personal vitality field. SWN — the target
system — has no composure track, and keeping Edge *alongside* HP would be a third
vitality-shaped number competing with both HP and the dials: exactly the "HP with
extra steps" trap, doubled. The dials already *are* the pressure/poise layer
(§Context). One vitality number (HP) + the narrative dials is the clean two-layer
model. **Edge as a composure track is retired, not repurposed.**

**4b. Push-currency rituals → UNTOUCHED (they were never Edge).** ADR-078 §6 built
spellcraft push currencies (`voice` / `flesh` / `ledger`) as genre-declared
**`ResourcePool`s** (ADR-033 Pillar 2), debited via `BeatDef.resource_deltas` —
*not* via Edge. Retiring Edge does not touch them. The `pact_working` confrontation
and its `commit_cost` beat keep their typed `ResourcePool` debits exactly as
authored. This fork's framing ("push-currency rituals on Edge") was a misreading of
ADR-078; the rituals ride a separate, surviving primitive. No action required.

**4c. Mechanical advancement → REPOINTED at HP (preserve the hard link).** ADR-078's
genuinely new contribution was *"the first hard link from ADR-021 progression to
engine state"* — the `AdvancementEffect` enum that mutates per-character beat costs
and capacity at level-up. We keep that link; we re-point its vitality-shaped
variants from Edge to HP:

| ADR-078 variant | Disposition under ADR-114 |
|---|---|
| `EdgeMaxBonus { amount }` | → **`HpMaxBonus { amount }`** — grows `HpPool.base_max` at a tier |
| `EdgeRecovery { trigger, amount }` | → **`HpRecovery { trigger, amount }`** — HP restored on the named trigger |
| `BeatDiscount { … }` | **Kept as-is** — discounts `resource_deltas` (push currencies) and dial costs; never referenced HP |
| `LeverageBonus { … }` | **Kept as-is** — pure dial effect (`target_*_delta_mod`) |
| `LoreRevealBonus { … }` | **Kept as-is** — narrator-side reveal hook |

Per ADR-078's implementation status, these effects are **loaded data, not yet
wired** (Epic 39 was never completed). So this is a rename at the data-shape layer
with no live wiring to migrate — the cheapest possible disposition. The
progression→engine link survives the supersession intact; it simply grows HP
instead of composure when it is finally wired.

### 5. 0-HP outcome via `lethality_policy.yaml` (Fork 4)

The `LethalityArbiter` (`agents/lethality_arbiter.py`) already fires per-genre
verdicts when `core.edge.current == 0`, reading `verdicts_on_zero_edge` from
`lethality_policy.yaml` (`genre/models/lethality.py`). This whole machine is
retained and **re-pointed from edge to HP**:

- `LethalityPolicy.verdicts_on_zero_edge` → **`verdicts_on_zero_hp`** (same
  `VerdictsOnZeroEdge` shape: `pc` and `npc` verdict kinds). YAML key renames in
  every pack's `lethality_policy.yaml`.
- The arbiter trigger changes from `core.edge.current == 0` to
  `core.hp.current == 0`.
- `LethalityVerdictKind`, `Reversibility`, and the `must_narrate` /
  `must_not_narrate` envelope are unchanged — the verdict *shape* and the
  narrator-tone constraint envelope carry forward. `space_opera` stays moderate;
  `beneath_sunden` stays harsher. Per-genre lethality is exactly what this model
  already expresses; we change only the field that fires it.

So "what happens at 0 HP" remains **genre-authored content**, not engine-hardcoded
— a mortal wound, an unconsciousness, a capture, or a death, per the pack's policy.

### 6. OTEL — every HP mutation emits `state_patch` (Fork 5)

Per the project OTEL Observability Principle, the GM panel is the lie detector for
combat. **Every HP delta emits the existing `state_patch` span** — damage from a
strike, mitigation-adjusted application, healing from a `Lift` stim, the
`Lazarus patch` stabilize-at-0. The span carries `{ actor, delta, source
(beat_id | item_id), current, max }` so the GM panel shows the arithmetic behind
every wound. No HP changes without a span; a silent HP mutation is a bug.

The 0-HP lethality verdict continues to emit through the arbiter's existing path.
ADR-078's `encounter.composure_break` span (which had zero hits — it was never
wired) is **dropped**; its intent is served by `state_patch` (the delta that
reaches 0) plus the lethality verdict span. This closes the audit gap ADR-078 left
open rather than re-opening it.

### 7. Ships are unchanged

HP reintroduction is **personal-scale only**. Ships keep their narrative
**condition-tracks** (shields / hull / engines / weapons degrading) via
`RigComposurePool` and the dogfight subsystem (ADR-077). That model is *already*
ablative — multi-track HP with narrative labels — and preserves the "losing your
ship is a death in the family" design. No ship change in this ADR.

### 8. Player-visible HP — narrow amendment to ADR-040 (see Amendments)

The HP number is **shown** on the character sheet. This is a deliberate, narrow
bend of ADR-040 (No Raw Stats) for the lethality number specifically — recorded as
an amendment to ADR-040 below. Every other stat stays narrative. The justification:
the two mechanics-first players asked for legible lethality, the dice overlay
already shows damage rolling, and a hidden HP number behind a "badly wounded" band
defeats the entire point of the reintroduction.

## Scope and sequencing

- **This ADR + the HP substrate** are `space_opera`-first to prove the two-layer
  model in a live playtest, then **backported to `beneath_sunden`** under its own
  (harsher) `lethality_policy.yaml` (umbrella spec Part 3 / Plan #5). Sünden
  content already carries B/X HP, so the backport is the same "stop discarding"
  move on a second pack.
- The Dev implementation plan for the substrate is written to
  `docs/superpowers/plans/2026-05-25-swn-hp-substrate.md` (Plan #1, foundational —
  gates the mechanical meaning of Lane A's damage values).

## Consequences

### Positive

- **The crunch the playgroup asked for, in the system they named.** SWN is HP-based;
  this delivers HP, dice-rolled damage, and armor soak — concrete and legible for
  Sebastien and Jade without sacrificing the dial/narrative layer James and Alex
  engage with.
- **Combat stops being a phantom — for real this time.** ADR-078 promised
  engine-validated combat and left the damage channel and `composure_break` span
  unwired. HP + the mandatory `state_patch` span on every delta makes the GM panel
  a true polygraph on combat.
- **Mostly deletion.** The central move is removing the HP→composure translation at
  the materializer seam. We author HP today and throw it away; we stop.
- **The progression→engine hard link survives** (§4c) — repointed, not lost.
- **Reuse-first throughout.** The dice overlay (ADR-074/075), the lethality arbiter,
  the `ResourcePool` push currencies, and the dial engine (ADR-033) are all reused;
  the genuinely new surface is one pool type, one tagged beat channel, two
  `CatalogItem` fields, and a YAML key rename.

### Negative

- **A second supersession of the combat-vitality model in ~6 weeks.** ADR-078
  replaced HP with Edge on 2026-04-15; this replaces Edge with HP on 2026-05-25.
  That is real churn. Mitigation: ADR-078's damage channel never actually wired, so
  there is little *live* code to unwind — mostly data-shape renames and the
  deletion of a translation seam. The churn is in the design record, not in a
  working subsystem.
- **ADR-040's no-raw-stats invariant gets a permanent exception.** Mitigated by
  keeping the exception narrow (the lethality number only) and explicit (amendment
  below).
- **Legacy Edge-based saves.** Per project policy, legacy playtest saves are
  throwaway (`feedback_legacy_saves.md`); no Edge→HP save migration is built. Fresh
  sessions seed HP from content. Old saves carrying `EdgePool` are not load-bearing.

### Risks

- **"HP feels like attrition with no agency."** The exact mirror of ADR-078's "Edge
  with extra steps." Mitigation: HP is *additive under the dials* — the narrative
  beats still drive the scene; HP is the floor, not the whole game. The playtest
  acceptance gate is a `space_opera` combat turn that shows **both** a dice-rolled
  HP hit **and** a dial beat moving the fiction in the same turn.
- **Damage tuning.** First-pass weapon dice (Lane A) may be too swingy or too soft.
  Mitigation: damage lives entirely in YAML (`CatalogItem.damage.dice`) — retune
  without code changes, same as ADR-078's `edge_delta` tuning lever.

## Alternatives Considered

### A: Keep Edge as composure, add HP as a second track beneath it

Rejected. Two personal vitality-shaped numbers (composure + HP) plus the narrative
dials is three layers where the spec calls for two. SWN — the requested system —
has no composure track. This is the "HP with extra steps" failure mode doubled. The
dials already serve as the pressure/poise layer; HP is the lethality floor. One
vitality number is the clean model.

### B: Flat `hp_delta` integer on each beat (no dice)

Rejected. Bypasses the dice overlay (ADR-074/075) that *is* the legible-math
payoff for the mechanics-first players, and makes every strike deal identical
damage regardless of weapon. Sourcing damage from the equipped weapon's dice and
rolling it on the table is the entire point.

### C: AC + to-hit (full SWN combat procedure)

Rejected per the spec's dividing line — "steal the nouns, leave the math."
SideQuest's resolution is the dials plus its own dice system. Adopting SWN's
d20-vs-AC and saving-throw tables would replace a working resolution layer to no
benefit. We adopt only the HP lethality model and the damage dice.

### D: Don't supersede — amend ADR-078 to add HP alongside Edge

Rejected. ADR-078's load-bearing decision was *"`CreatureCore.hp / max_hp / ac`
are deleted… `EdgePool` replaces them."* Re-adding HP as the vitality track
directly reverses that decision; an amendment claiming "HP and Edge coexist" would
misrepresent a reversal as an addition and leave the design record incoherent. The
honest record is supersession (§ADR housekeeping), with explicit preservation of
the parts of 078 that survive (§4b, §4c).

## ADR housekeeping

- **ADR-078** → `status: superseded`, `superseded-by: 114`,
  `implementation-status: retired`. Symmetric with this ADR's `supersedes: [78]`
  (only 78 — the sole ADR whose `superseded-by` points back here).
- **ADR-040** → amended (HP number visible); `related` gains 114. Status stays
  `accepted` / `live`. Amendment text added to ADR-040 (see below).
- **ADR-033** → re-slotted (dials sit atop HP, not instead of it); `related` gains
  114. Status/impl-status unchanged. Re-slot note added to ADR-033 body.
- **ADR-014** → touch only (vitality materialization is now HP, not Edge);
  `related` gains 114. Principle ADR, `not-applicable` impl-status unchanged.

## Amendments to other ADRs (text to land in this wave)

**ADR-040 amendment (2026-05-25):**

> ### Amendment 2026-05-25 — HP lethality number is visible (ADR-114)
> ADR-114 reintroduces ablative HP as the personal lethality substrate and, by
> direct playgroup mandate, exposes the **HP number** on the character sheet. This
> is a deliberate, narrow exception to this ADR's no-raw-stats decision: the
> lethality number only. All other stats (abilities, ability scores, non-lethality
> mechanical effects) remain narrative per the original decision. The six-band
> `describe_health()` framing may continue alongside the raw number; the number is
> additive, not a replacement of the narrative health language.

**ADR-033 re-slot note (2026-05-25):**

> ### Re-slot 2026-05-25 — dials sit atop the HP substrate (ADR-114)
> ADR-114 reintroduces ablative HP as a lethality substrate *underneath* the
> confrontation dials. The `momentum` / `leverage` / `engagement_range` metric
> dials and the beat structure described here are unchanged — they remain the
> narrative pacing layer. Beats additionally gain an optional HP-damage channel
> (`strike` deals dice-rolled weapon damage to HP; `brace` mitigates) that runs
> beneath the dials without altering them. The dials are not a replacement for HP
> and HP is not a replacement for the dials; they are two layers in one turn.

## Amendment 2026-05-28 — composure scope clarification (personal Edge gone, vessel rig survives)

Reconciling §1 and §7 against the shipped code, to prevent the reading
"all composure is gone." **Personal-creature** Edge/Composure is fully
removed: there is no `EdgePool` class anywhere in the server
(`grep "class EdgePool"` → none; the name survives only as a history
reference in the `HpPool` docstring at `creature_core.py`).
`CreatureCore` now carries `hp: HpPool` (`creature_core.py`; `HpPool`
defined at `creature_core.py`) as the sole personal vitality track —
the §1 reversal, as shipped. **But the vessel `RigComposurePool` survives
separately** (`creature_core.py`, `rig_pool: RigComposurePool | None`;
class in `sidequest/game/rig_composure_pool.py`) — it is the ship/dogfight
condition-track machinery of §7 (ADR-077), **not** part of the HP reversal.
The HP↔Edge swap is a *personal-scale* change only; the rig composure pool
is untouched and intentionally retained.

**Per-genre survivability doctrine.** HP is the live personal lethality
track now, and is genre-authored at the edges (`lethality_policy.yaml`
verdicts on zero HP per §5; pluggable ruleset modules per ADR-117). The
retired Edge/Composure substrate is *planned to return* as the **Fate SRD**
ruleset module — ADR-117 names "the planned Fate module [as] the intended
home for the retired Edge/Composure substrate" (ADR-117 §References, the
"`bx`/Fate/PbtA/5e additional modules … not implemented" note). So
composure is not erased from the design — it is relocated from a hardcoded
personal track to (a) the still-live vessel rig pool and (b) a future Fate
ruleset module. This ADR's reversal is scoped to the personal-creature
vitality field; it does not claim to delete composure from the system
wholesale.

## References

- Umbrella design: `docs/superpowers/specs/2026-05-25-swn-crunch-ablative-hp-design.md`
- Implementation plan (this ADR's Dev handoff): `docs/superpowers/plans/2026-05-25-swn-hp-substrate.md`
- Lane A gear/pharmacopeia (consumes `CatalogItem.damage`): `docs/superpowers/plans/2026-05-25-swn-gear-pharmacopeia.md`
- Superseded predecessor: [ADR-078](078-edge-composure-advancement-rituals.md)
- Materializer seam (translation removed): `sidequest-server/sidequest/game/world_materialization.py` `_apply_npc()`
- Vitality pool home: `sidequest-server/sidequest/game/creature_core.py`
- CatalogItem model: `sidequest-server/sidequest/genre/models/inventory.py`
- Lethality policy model + arbiter: `sidequest-server/sidequest/genre/models/lethality.py`, `sidequest-server/sidequest/agents/lethality_arbiter.py`
- Dice protocol / dispatch (damage rolls reuse this): `sidequest-server/sidequest/protocol/dice.py`, `sidequest-server/sidequest/server/dispatch/dice.py`
- `state_patch` span: `sidequest-server/sidequest/telemetry/spans/state_patch.py`
