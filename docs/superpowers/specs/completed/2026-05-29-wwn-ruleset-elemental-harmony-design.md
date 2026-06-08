# Worlds Without Number Ruleset + `elemental_harmony` Binding

**Date:** 2026-05-29
**Status:** Design (approved for spec review)
**Author:** GM
**Decision-driver:** Keith Avery
**Builds on:** ADR-117 (Pluggable Ruleset Module System), the SWN module, the CWN module
**Methodology:** superpowers (brainstorm → plan → TDD execute), same as SWN and CWN
**Repos:** `sidequest-server` (module, config, magic seams, spans, tests), `sidequest-content` (`elemental_harmony` binding)

---

## 1. Why

The pluggable-ruleset map (`2026-05-26-pluggable-srd-ruleset-modules-design.md`) lists one faithful
SRD per genre pack. **Stars Without Number** shipped (bound to `space_opera`) and **Cities Without
Number** shipped (bound to `neon_dystopia`). The next in the "Without Number" family is **Worlds
Without Number** (WWN, Kevin Crawford / Sine Nomine, CC0), the fantasy entry — and the natural fit
is **`elemental_harmony`** (martial arts + elemental magic). The ability names already align with the
d20 six, there are no extant saves to migrate, and the playgroup has zero attachment to
elemental_harmony's current native rules — so this is the cleanest binding of the three.

The fidelity bar is unchanged: **faithful math.** A career GM (Keith) and the two mechanics-first
players (Sebastien, Jade) spot a fudged save in one round. WWN must reproduce its SRD's *actual*
resolution — real HP, real saves, real to-hit, real Effort economy — and every mechanical decision
must emit an OTEL span, because in this project **the GM panel is the lie detector**: narration with
no backing span means the narrator improvised.

## 2. The mechanical delta — WWN ≈ CWN minus cyberpunk, plus magic

The headline finding, grounded in the WWN SRD v1.0:

| Subsystem | WWN rule | Already implemented in… |
|---|---|---|
| Attribute mod curve | 3→−2, 4–7→−1, 8–13→0, 14–17→+1, 18→+2 | **SWN, identical** (`swn_attribute_modifier`) |
| Skill checks | 2d6 + mod + skill vs 6/8/10/12/14 | **SWN `check_params`, identical** |
| Saves | 1d20 ≥ (16 − level − best-of-two mod); Physical / Evasion / Mental **+ Luck** (16 − level, no mod) | **CWN `save_params`** (16−level ≡ SWN's 15−(level−1)) |
| Attack | d20 + attack bonus + Stab/Shoot/Punch + mod vs AC | **SWN `attack_params`, identical** |
| AC | ascending, 10 base + DEX, armor 10–19 | **SWN/CWN model** |
| Initiative | 1d8 + best DEX | **SWN `roll_initiative`, identical** |
| Shock (X/AC Y on a miss) | weapons carry Shock | **CWN `resolve_shock`** |
| Trauma | yes | **CWN `resolve_trauma`** |
| System Strain (max = CON score) | yes | **CWN `apply_system_strain`** |
| Mortal Injury (0 HP → dead in 6 rounds unless stabilized) | yes | **CWN `resolve_downed`** |
| Hacking / cyberspace | **none** | CWN-only — WWN **drops** it |
| Magic: Effort / Arts / spell slots | **WWN's signature axis** | **net-new** |
| Warrior Fray Die (auto-damage/round) | yes | **net-new** |

WWN is **not** "SWN plus stuff." It is **CWN's resolution engine minus hacking, plus a magic system.**
The entire lethality layer CWN built (Luck save, Shock, Trauma, System Strain, Mortal Injury) is
shared "Without Number" core that WWN needs verbatim.

### 2.1 The architecture decision: copy, do not abstract (decided)

The tempting move is to hoist the shared lethality layer out of `CwnRulesetModule` into a common base
that both CWN and WWN inherit. **Rejected for now.** Two reasons: (1) touching `cwn.py` risks
regressing `neon_dystopia`; (2) the right abstraction of the ruleset *library* is a separate, larger
planning effort that this story is not the place to force. So we **copy** CWN's lethality methods into
the new WWN module, adapted. The duplication (~5 near-identical methods across `cwn.py` and `wwn.py`)
is **intentional and accepted**. A future library-abstraction effort can deduplicate deliberately.

## 3. The magic integration — Approach C (hybrid), decided

Three approaches were weighed: A (data-on-rails, magic is mostly narrator prose), B (full
engine-resolved spells with structured per-spell data), C (hybrid). **C chosen.**

The principle: **the resource economy and the cast spine are engine-real with spans; the bespoke
*effect* of a non-damage spell stays narrator-adjudicated prose.** This honors the OTEL lie-detector
(you cannot fake a cast — the slot is gone, the save and damage are real rolls with spans) without
signing up to model every WWN spell's unique effect in Python (the unbounded task, and open-ended
adjudication is the Zork-problem design anyway).

This is tractable because the engine **already** has:
- a mature, generic **`ResourcePool`** abstraction (`game/resource_pool.py`) — declared in `rules.yaml`,
  seeded at chargen, mutated by patches that auto-emit pool spans, with `decay_per_turn` + thresholds;
- a **hybrid ability layer** (`AbilityDefinition`: `genre_description` prose + `mechanical_effect` prose
  + selective engine resolution, e.g. Taunt mutates encounter state and fires a span);
- a **chargen materialization seam** (`CharacterBuilder`) that already seeds HP pools and abilities.

### 3.1 Effort

A **`ResourcePool`** declared per caster class (`voluntary: true`). Its `max` is computed at chargen
from the SRD formula — **Full class: `1 + relevant-skill-level + governing-attr-modifier`; Partial: `1
fewer, min 1`.** Commit-for-scene / commit-for-day is the pool decrementing on commit and **restoring
at the scene/day boundary**.

### 3.2 Spell slots

**`ResourcePool`s** (`spell_slots_1` … `spell_slots_N`), `voluntary: true`, **no decay**, recharged to
max at a long-rest boundary. Seeded at chargen from the class's slot progression.

### 3.3 The cast spine — `WwnRulesetModule.resolve_spellcast(...)` (new, engine-resolved)

1. **Validate** the caster has the slot (or committable Effort for an Art). No slot → **fail loud**,
   cast refused; the attempt is recorded on `wwn.spell.cast`.
2. **Spend** — decrement the slot pool (or commit Effort) via `apply_resource_patch` (emits a pool span).
3. **Force the save** when the spell allows one — reuse inherited `save_params` (Mental is the WWN default).
4. **Roll damage** when the spell is a damage spell — reuse inherited `resolve_damage`.
5. **Hand off the bespoke effect** (illusion / control / utility) to the narrator via the spell's
   `mechanical_effect` prose. The engine guarantees the economy and the rolls are real; the narrator
   adjudicates the open-ended effect.

### 3.4 Fray Die — `resolve_fray_die(...)` (new, small, modeled on `resolve_shock`)

A Warrior deals automatic die damage each round to a weaker foe, no attack roll. Applied via the
existing HP-channel path; emits `wwn.fray_die`.

### 3.5 Engine archetypes, content maps flavor onto them

The engine supports mechanical **archetypes**; content maps named flavor classes onto them
(Crunch-in-Genre / Flavor-in-World). The engine never hardcodes "Channeler."

1. **Slot + Effort caster** (Elementalist / High Mage model)
2. **Effort-only Art user** (the Vowed martial-artist model — Effort, no slots)
3. **Fray-Die warrior**
4. **Skill Expert**

### 3.6 Net server changes for magic (beyond the module methods)

Both are **additions at existing seams**, not new subsystems:
- (a) `CharacterBuilder` seeds the Effort pool max from the formula, and seeds spell-slot pools.
- (b) A **real scene/day Effort-reset hook** (per-turn `decay` exists; scene-scoped reset was deferred —
  we wire it for real here rather than fake it with per-turn decay).

## 4. Component: `WwnRulesetModule` (server)

**File:** `sidequest-server/sidequest/game/ruleset/wwn.py` → `class WwnRulesetModule(SwnRulesetModule)`,
`slug = "wwn"`. Registered in `registry.py`.

**Inherited from `SwnRulesetModule` verbatim** (identical in WWN): `stat_modifier`, `check_params`,
`attack_params`, `roll_initiative`, `resolve_damage`, `find_confrontation`, `apply_beat`.

**Copied from `CwnRulesetModule` into `wwn.py`** (adapted, not hoisted): `save_params` (Luck variant),
`resolve_shock`, `resolve_trauma`, `apply_system_strain`, `resolve_downed` (Mortal Injury).

**Dropped / fail-loud:** `resolve_hacking` left at base default (no WWN cyberspace);
`ship_attack_params` **overridden to raise `NotImplementedError`** (WWN has no ship gunnery — fail loud
beats silently inheriting SWN's dogfight math).

**New:** `resolve_spellcast`, Effort commit/reclaim, `resolve_fray_die` (§3).

### 4.1 Config — `WwnConfig`

In `genre/models/rules.py`, extending `SwnConfig` exactly as `CwnConfig` does:
- inherits `unarmored_ac` (10), `save_base` (15), `difficulties`, `attribute_map`
- **reuses** `SystemStrainConfig` and `TraumaConfig` (reuse the models; copy the behavior)
- adds a small new `MagicConfig` (Effort-max formula params, Fray Die rules, spell-save defaults)
- `RulesConfig` gains `wwn: WwnConfig | None` + a validator mirroring the `swn`/`cwn` ones

## 5. Component: OTEL spans

New `sidequest-server/sidequest/telemetry/spans/wwn.py`, distinct **`wwn.*`** namespace so the GM panel
separates `elemental_harmony` (`wwn.*`) from `neon_dystopia` (`cwn.*`):

- **Magic:** `wwn.spell.cast` (slot/Effort spent, save target, damage), `wwn.effort.commit` /
  `wwn.effort.reclaim` (incl. scene/day reset), `wwn.fray_die`.
- **Lethality (copied from `cwn` spans, renamed):** `wwn.shock.applied`, `wwn.trauma.roll`,
  `wwn.system_strain.delta`, `wwn.mortal_injury.declared`, `wwn.major_injury.roll`.
- **Dropped:** `cwn.hacking.security_check` (no WWN analog).

## 6. Component: `elemental_harmony` content binding (content lane)

The six ability names map **1:1** onto the d20 six — clean `attribute_map`, **no rename/stat-check
churn** (unlike `neon_dystopia`):

| WWN | elemental_harmony |
|---|---|
| STRENGTH | Strength |
| DEXTERITY | Agility |
| CONSTITUTION | Endurance |
| INTELLIGENCE | Insight |
| WISDOM | Spirit |
| CHARISMA | Harmony |

Spirit↔WISDOM and Harmony↔CHARISMA are thematically apt. **The magic-governing attribute will be Spirit
or Harmony, tuned during authoring.**

Work (all content YAML):
- **`rules.yaml`** — add `ruleset: wwn` + `attribute_map`; add `wwn:` config block (`system_strain`,
  `trauma`, `magic`); declare `effort` + `spell_slots_*` resource pools. With no save attachment, the
  "Martial Exchange" combat confrontation is **rewritten clean** to `resolution_mode: beat_selection` +
  `win_condition: hp_depletion`, with `opponent_default_stats` (hp / armor_class / dexterity), strike
  beats carrying `damage_channel` / `damage_override` + Shock, and **`cast_spell` beats** for casters.
- **`inventory.yaml`** — WWN armor (AC 10–19) and weapon (damage + Shock) tables, themed to the
  wuxia/elemental aesthetic (staff, spear, jian, unarmed/Punch, bow; robes, war robe, lamellar) but
  mechanically WWN.
- **`classes.yaml` (new)** — map the six `allowed_classes` onto the engine archetypes:
  **Channeler / Spirit Medium → slot+Effort casters**, **Martial Artist → Effort-only Art user (Vowed
  model)**, **Guardian → Fray-Die Warrior**, **Scholar / Wanderer → Experts**. Each gets
  `prime_requisite`, `abilities` (`genre_description` + `mechanical_effect`; Arts/spells for casters),
  `encounter_beat_choices`, `magic_access`.
- **`char_creation.yaml`** — minor alignment to the class list (point-buy 30 stays).
- **Worlds** (`burning_peace`, `shattered_accord`) — lore/cultures/archetypes are ruleset-transparent
  NPC flavor; verify neither has a rules override; no content rewrite expected.

## 7. Testing & wiring

Follows the existing `tests/game/ruleset/` layout and naming.

**Unit tests (server):**
- `test_wwn_module.py` — config defaults parse; attribute curve inherited (3→−2, 18→+2); **Luck save
  present** (no attr mod); `ship_attack_params` raises (fail-loud).
- `test_wwn_shock.py`, `test_wwn_trauma.py`, `test_wwn_system_strain.py`, `test_wwn_downed.py` — the
  copied lethality behaviors (mirror the `cwn` tests; WWN's tests pin WWN's behavior independently so a
  future CWN change cannot silently alter WWN).
- `test_wwn_spellcast.py` — refuses with no slot (fail loud); spends slot/Effort on success; forces the
  Mental save; rolls damage on a damage spell; asserts `wwn.spell.cast` fires.
- `test_wwn_effort.py` — Effort max formula (Full = 1+skill+mod; Partial = 1 fewer, min 1);
  commit/reclaim; scene/day reset restores the pool.
- `test_wwn_fray_die.py` — auto-damage applied, span emitted.

**Binding + registry:**
- `test_registry.py` extension — `wwn` resolves + is a singleton.
- `test_loader_binding.py` extension — `ruleset: wwn` parses; unknown still rejected.

**Wiring tests (mandated end-to-end — "every test suite needs a wiring test"):**
- `test_wwn_dispatch_routing.py` — load **the real `elemental_harmony` pack**, drive a combat/cast beat,
  assert it routes through `WwnRulesetModule` (not free functions). Drive the **opposed /
  `beat_selection` path against the actual pack**, not a synthetic fixture (per the known trap that
  dispatch-only wiring no-ops in real `hp_depletion` play).
- `test_wwn_chargen_wiring.py` — build an `elemental_harmony` caster end-to-end; assert the Effort pool
  + spell-slot pools land on the snapshot with the correct computed max.

**Content load (calibration, content-gated):** `elemental_harmony` loads clean under `ruleset: wwn`.

**Gate discipline:** run the **full** suite with both `SIDEQUEST_DATABASE_URL` (postgres test DB) **and**
`SIDEQUEST_GENRE_PACKS` set; record the baseline failure list first — only a *new* failure is a
regression. Include `tests/integration/` and content-gated `tests/genre/` calibration tests, not a
scoped subset.

## 8. Scope

**In scope:** the `WwnRulesetModule` (copied CWN lethality minus hacking, inherits SWN); `WwnConfig` +
`MagicConfig`; Effort + spell-slot pools with chargen seeding and a real scene/day reset hook; the cast
spine; the Fray Die; `wwn.*` OTEL spans; the full `elemental_harmony` binding (rules, inventory, classes,
char-creation); unit + binding + wiring + content-load tests.

**Explicitly deferred / out of scope:**
- the shared-ruleset-library abstraction (copy, don't abstract — §2.1);
- mechanizing every WWN spell's bespoke non-damage effect (narrator-adjudicated by design);
- authoring the *entire* WWN spell list (we author `elemental_harmony`'s casters' spells/Arts, not all
  of WWN);
- WWN ships / dogfights (no analog; `ship_attack_params` fails loud);
- WWN factions, major projects, and the faction turn.

## 9. Risks & mitigations

- **Copy drift between `cwn.py` and `wwn.py`.** Accepted (§2.1). Mitigation: WWN's lethality tests pin
  WWN's behavior independently, so the two can diverge safely and intentionally.
- **`beat_selection` / `hp_depletion` wiring no-ops in real play** (the opposed-check trap from the SWN
  rollout). Mitigation: the dispatch-routing wiring test drives the real pack on the real combat path,
  not a synthetic fixture.
- **Scene/day Effort reset is partially-deferred infra.** Mitigation: wire a real hook; cover it with
  `test_wwn_effort.py`; do not fake it with per-turn decay.
- **Magic-governing attribute ambiguity (Spirit vs Harmony).** Mitigation: decided during content
  authoring against the elemental_harmony class concepts; recorded in `classes.yaml`.

---

## Amendment — 2026-05-29: Faithful magic substrate (supersedes §3's ResourcePool choice)

**Author:** The Man in Black (architect) · **Decision-driver:** Keith Avery · **Status:** approved, supersedes §3/§3.1/§3.2/§3.4 substrate language.

§3 chose the generic session `ResourcePool` for Effort/spell-slots on the premise that the engine "already has" a per-character, chargen-seeded, auto-span pool. Investigation of the live engine + a read of the WWN SRD v1.0 (Crawford, Sine Nomine, CC0) showed both halves of that premise are wrong, and Keith's directive is unambiguous: **build the most-WWN-faithful model; the playgroup has zero attachment to current mechanics; reuse only the *interaction* plumbing (dice resolution, OTEL spans, beat dispatch, per-core pools, builder seeding) that the SWN and CWN ports already proved — not any existing magic *rules*.**

### A. Why `ResourcePool` is rejected as the substrate
- `ResourcePool` is **session-scoped** (`GameSnapshot.resources: dict[str, ResourcePool]`); `CreatureCore` has no resource-pool field. Effort is inherently **per-character** and even **per-class-source**.
- `init_resource_pools` / `apply_pool_decay` have **zero production callers**; pool OTEL spans were deferred (story 42-4). So "seeded at chargen, mutated by patches that auto-emit spans" is aspirational.
- The WWN SRD models Effort and spells far more richly than a scalar pool (below). Forcing them onto `ResourcePool` or the C&C `MagicState` ledger would be unfaithful.

The faithful pattern is the one the SWN/CWN ports already use for per-character resources: a **bespoke per-`CreatureCore` pool model** (cf. `HpPool`, `SystemStrainPool`) seeded by the builder (cf. `seed_system_strain`), mutated by ruleset-module methods that **emit `wwn.*` spans explicitly**. New `CreatureCore` fields are authorized.

### B. Effort — per-source commitment pools (SRD §1.4.4)
Per character, `effort: dict[str, EffortPool]` keyed by class-source (High Mage / Vowed / Elementalist…); "points from one class cannot fuel another." Each `EffortPool` = `max: int` + `commitments: list[EffortCommitment]`, where `EffortCommitment = {points:int, duration: "maintained"|"scene"|"day", label:str}`; `available = max − sum(committed)`. `max = 1 + relevant_skill_level + governing_attr_mod` (Partial class: −1, min 1). Reclaim: **maintained** = explicit Instant action; **scene** = scene-end hook; **day** = night's-rest hook (comfort-gated — no recovery if hungry/cold/sick/sleeping rough).

### C. Spells — prepared list + daily casts + max level (SRD §4.2), NOT per-level Vancian
Per character, `SpellcastingState = {prepared: list[spell_id], casts_remaining:int, casts_per_day:int, max_spell_level:int}`. A cast spends **one** from the daily `casts_remaining` pool on **any** prepared spell of level ≤ `max_spell_level`; the same spell may be cast repeatedly while casts remain; refresh `casts_remaining → casts_per_day` on a night's rest. (The C&C `learned_v1` per-level slot ledger is the wrong shape and is **not** reused.)

### D. Cast spine — `WwnRulesetModule.resolve_spellcast(...)` (Approach C upheld)
1. Validate: spell is prepared, `casts_remaining > 0`, `spell.level ≤ max_spell_level` → else **fail loud / cast refused**, recorded on `wwn.spell.cast` (`refused=True`). 2. Spend one cast. 3. If the spell offers a save, the **defender** rolls their own save via inherited `save_params` (the spell names the category; Mental is the common default). 4. If a damage spell, roll `caster_level × die` via inherited `resolve_damage`, halved on a made save. 5. Bespoke non-damage effect → **narrator prose** (`mechanical_effect`). Engine guarantees economy + rolls are real; effect stays open-ended.

### E. Warrior — Fray Die was an SWN mis-import; corrected to the real WWN abilities (SRD §1.5.18)
WWN Warriors have **no Fray Die**. Replace with: **Killing Blow** — add `ceil(level/2)` to the damage of any attack/spell/ability **and** to Shock (a rider in `resolve_damage`; span `wwn.killing_blow`); and **Veteran's Luck** — once/scene, Instant action, turn one own miss into a hit *or* one enemy hit-on-you into a miss (scene-scoped used-flag reset at scene end; span `wwn.veterans_luck`). `resolve_fray_die` and the `wwn.fray_die` span are **struck from the design.**

### F. Per-class magic data lives on the class-def model
The Effort-max formula and the casts/prepared/max-level tables are **per-class** → carried on the class-def magic config (model extended in Plan 2, authored in Plan 3), consumed by the builder at seed time.

**Skill-level gap (resolved):** WWN is skill-based but the engine has no per-character skill registry (skill level is a roll-time wire integer only). Resolution: the caster's *relevant magic skill* and its *chargen starting level* are authored on the class magic config and consumed by the builder for the Effort-max formula. A full per-character skill system is **out of scope / deferred**.

### G. Spans (emitted explicitly by the module, per the port pattern)
`wwn.spell.cast`, `wwn.effort.commit`, `wwn.effort.reclaim` (incl. scene/day reset), `wwn.killing_blow`, `wwn.veterans_luck`. (Pool-mutation auto-spans are deferred infra and are NOT relied upon.)

### H. Reset hooks (wired for real, per CWN system-strain recovery precedent)
Scene-end Effort reclaim at `Session.end_scene`; day/long-rest Effort reclaim + `casts_remaining` refresh at a fired rest boundary. Not faked with per-turn decay.

### I. Plan split (revises §7/§8)
- **Plan 2 (server magic engine, this plan):** `MagicConfig`; per-core `EffortPool`/`EffortCommitment`/`SpellcastingState`; class-def magic-config model extension; `WwnRulesetModule` methods (`commit_effort`, `reclaim_effort`, `resolve_spellcast`, Killing Blow rider, `veterans_luck`, scene/day reset); chargen seeding helper; `wwn.*` magic spans; **unit tests against synthetic fixtures** (mirroring Plan 1's lethality tests).
- **Plan 3 (content + end-to-end):** the `elemental_harmony` binding (rules/inventory/classes/char-creation), the `cast_spell` dispatch-routing branch, and the end-to-end wiring tests against the real pack.
- **Known deferral (flagged loudly):** like `resolve_downed` in Plan 1, the cast spine is **dead in production dispatch until Plan 3 wires the `cast_spell` beat**. Plan 2 builds + unit-tests the engine; Plan 3 wires + integration-tests it against the bound pack.
