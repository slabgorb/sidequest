# Beneath Sünden WWN Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the `caverns_and_claudes` pack (sole world: `beneath_sunden`) from the native dial engine to the WWN SRD ruleset, reusing heavy_metal's already-balanced WWN artifacts with zero new balancing.

**Architecture:** Pure content port per `docs/superpowers/specs/2026-06-12-beneath-sunden-wwn-port-design.md`. `WwnRulesetModule` is production-live; we bind to it via `rules.yaml`, replace the B/X class/magic surface with the three WWN chassis copied from heavy_metal, and prove wiring with one server-side integration test adapted from the EH exemplar. The ADR-106 procedural megadungeon is untouched.

**Tech Stack:** YAML genre packs (sidequest-content), pack validator (`just content-validate`), pytest integration test (sidequest-server).

**Repos & branches (per repos.yaml / dual-clone doctrine):**
- `sidequest-content` — branch `feat/wwn-port-caverns`, PR base `develop`
- `sidequest-server` — branch `feat/wwn-caverns-wiring-test`, PR base `develop`
- Orchestrator carries only spec/plan docs (already on `feat/beneath-sunden-wwn-port-spec`, PR base `main`)

**Validation gate used throughout:** `just content-validate caverns_and_claudes` (runs `sidequest.cli.validate pack` from sidequest-server against the pack). Content invariants live in the validator, NOT in pytest (project rule).

**Source artifacts being reused (read them before editing):**
- `genre_packs/heavy_metal/classes.yaml` — 3-chassis template (Warrior/Expert/casters)
- `genre_packs/heavy_metal/spells_wwn.yaml` — balanced WWN spell catalog
- `genre_packs/heavy_metal/rules.yaml` — wwn config block + WWN combat def
- `genre_packs/heavy_metal/lethality_policy.yaml` — lethal policy template
- `sidequest-server/tests/integration/test_wwn_elemental_harmony_dispatch.py` — wiring-proof template

---

### Task 1: Branches

**Files:** none (git only)

- [ ] **Step 1: Create the content branch**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content
git checkout develop && git pull origin develop
git checkout -b feat/wwn-port-caverns
```

- [ ] **Step 2: Create the server branch**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-server
git checkout develop && git pull origin develop
git checkout -b feat/wwn-caverns-wiring-test
```

- [ ] **Step 3: Baseline — confirm the pack validates BEFORE the port**

```bash
cd /Users/slabgorb/Projects/oq-3 && just content-validate caverns_and_claudes
```

Expected: PASS (exit 0). If it fails before we touch anything, STOP and report — pre-existing breakage is not ours to silently absorb.

---

### Task 2: spells_wwn.yaml — copy the balanced catalog

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/spells_wwn.yaml`

- [ ] **Step 1: Copy heavy_metal's catalog verbatim**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content/genre_packs
cp heavy_metal/spells_wwn.yaml caverns_and_claudes/spells_wwn.yaml
```

- [ ] **Step 2: Replace the file header comment** (everything above `version: "1.0"`) with:

```yaml
# Caverns & Claudes — WWN High Magic (spells_wwn.yaml)
#
# A faithful PORT of WWN High Magic spells, copied from
# genre_packs/heavy_metal/spells_wwn.yaml (story 87-2 lineage). Mechanics
# are the WWN SRD verbatim (level, save category, damage die, per-level
# scaling) — DO NOT retune; the catalog is the balanced artifact being
# reused (2026-06-12 beneath-sunden-wwn-port spec, "no new balancing").
# Prose is reskinned for the Sünden register where the source idiom named
# heavy_metal-specific institutions (the 999 Crimson Gods, the forge
# cities, the guild quarters).
#
# Engine contract (sidequest/genre/models/wwn_spell.py → WwnSpell):
#   - save: one of physical / evasion / mental / luck (or omitted for none)
#   - damage_die + damage_per_level: caster_level × die on a failed save
#   - range / target: flavor only
#   - mechanical_effect: narrator-adjudicated bespoke effect
#
# Loaded into pack.wwn_spell_catalog by the wwn loader. Every class
# starting_prepared id in classes.yaml MUST resolve here (loader fails loud).
```

- [ ] **Step 3: Reflavor prose that names heavy_metal institutions**

Find every heavy_metal-specific proper noun or institution in `genre_description` / `mechanical_effect` prose:

```bash
grep -n "Crimson God\|forge cit\|guild\|pact-bearer\|Pact\|doom\|Barsoom\|Lothar\|ninth ray\|radium\|Mars\|flier" caverns_and_claudes/spells_wwn.yaml
```

Rules for the rewrite — **prose only; never touch `id`, `level`, `save`, `damage_die`, `damage_per_level`, `range`, `target`, or any numeric value**:
- Debt/decay/account idiom (e.g. `wracking_bolt`, `sleepless_tithe`) already suits the dwarfhold — keep nearly as-is.
- "Forge cities / guild quarters" (e.g. `foundation_of_flame`) → the dwarfholds' dead forges: e.g. "the banked forge-heat of Sünden Deep, called up through stone that remembers being worked."
- "Pact / 999 Crimson Gods" (e.g. `lance_of_darkness`) → what was bargained with at the bottom of the shaft — the thing that answered the digging. No named patron pantheon.
- Barsoom-tradition spells (`phantom_bowmen`, `mind_veil`, `disintegration_ray`, `invisibility_compound`, and any other Mentalist/Super-scientist entries): **DELETE these entries entirely.** They are pulp-science workings for a different setting; no caverns class prepares them, and dead catalog entries are dead code. (If the validator later complains about a dangling reference, that reference is a bug to fix, not a reason to keep the entry.)

- [ ] **Step 4: Hard-limit audit (spec §4 — flag, don't rebalance)**

Check every remaining spell against `caverns_and_claudes/magic.yaml` `hard_limits` (no_resurrection, no_true_creation, no_unlimited_high_evocation, no_plane_shift, no_permanence_without_renewal). For any conflict, list the spell in the PR description under **"Hard-limit calls for Keith"** with options (drop spell vs. drop limit). Do not resolve unilaterally; do not modify spell mechanics.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content
git add genre_packs/caverns_and_claudes/spells_wwn.yaml
git commit -m "feat(caverns): WWN spell catalog, ported from heavy_metal (no retuning)"
```

(Validator is expected RED from here until Task 7 — classes/rules/magic land next. That's fine; the gate is enforced at Task 7 before the PR.)

---

### Task 3: classes.yaml — the three WWN chassis

**Files:**
- Rewrite: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`

- [ ] **Step 1: Replace the entire file with the content below.**

Mechanics fields (saving_throws, wwn_magic numbers, warrior flag, ability mechanical_effects) are byte-faithful to heavy_metal's chassis; only flavor prose, beat ids, and starting_prepared selection differ. Beat ids reference the Task 4 rules.yaml confrontations (combat: strike/brace/committed_blow/break_contact; chase: sprint/duck_through/barricade/douse_torch; negotiation: talk_up_the_haul/swear_its_not_cursed/plead_poverty/flash_the_coin/walk_toward_the_door).

```yaml
# Caverns & Claudes — Callings (Classes)
#
# Faithful WWN 3-chassis port (Warrior / Expert / Mage), per
# docs/superpowers/specs/2026-06-12-beneath-sunden-wwn-port-design.md.
# Mechanics copied from genre_packs/heavy_metal/classes.yaml (story 87-2
# lineage) — DO NOT retune. Flavor rewritten for the Sünden register.
#
# Design contract (this pack uses standard ABBREVIATION ability names —
# STR/DEX/CON/INT/WIS/CHA in rules.yaml ability_score_names):
#   - prime_requisite uses the ABBREVIATION (STR, DEX, INT).
#   - the Mage's wwn_magic.effort_sources.governing_attr uses the CANONICAL
#     WWN KEY (INTELLIGENCE), mapped by rules.yaml wwn.attribute_map.
#
# class_label in rules.yaml: "Calling".
#
# cast_spell is NOT listed in any class's encounter_beat_choices — the
# rules.yaml combat class_filter [Mage] is the ONLY gate that offers it,
# so the WWN cast resource gate fires correctly (heavy_metal/EH pattern).
#
# Required-but-inert fields follow the space_opera / EH / heavy_metal
# convention: minimum_score: 9 (point_buy pack, no roll-minimum gate);
# kit_table: <id>_kit (descriptive placeholder); jungian_default.
#
# saving_throws (B/X B26 table) is authored on EVERY class — the pack
# ships a spell catalog, so the loader validator requires it.
#
# Per ADR-095: one signature ability per class. The Warrior carries the
# WWN Warrior pair (Killing Blow + Veteran's Luck), gated on warrior: true.

# ── Warrior chassis ──────────────────────────────────────────────────────────

- id: warrior
  display_name: Warrior
  rpg_role: tank
  jungian_default: hero
  minimum_score: 9
  kit_table: warrior_kit
  prime_requisite: STR
  flavor: >-
    The Warrior goes down the rope because someone has to walk in front,
    and they have stopped pretending it should be anyone else. Seven
    delves in, the fear is still there — it has simply been filed, like
    everything else in the camp, under things that are owed and will be
    paid. They carry the torch-side of the line, take the first blow at
    every door, and keep an honest count of which of those doors they
    expect to come back through.
  encounter_beat_choices:
    - strike
    - brace
    - committed_blow
    - break_contact
    - sprint
    - barricade
    - talk_up_the_haul
    - flash_the_coin
    - walk_toward_the_door
  # WWN Warrior archetype. No magic_access, no wwn_magic.
  # warrior: true gates the Killing Blow + Veteran's Luck dispatch seams in
  # sidequest-server dice.py.
  warrior: true
  saving_throws:
    death_ray_or_poison: 12
    magic_wands: 13
    paralysis_or_stone: 14
    dragon_breath: 15
    rods_staves_spells: 16
  abilities:
    - name: "Killing Blow"
      genre_description: >-
        A Warrior who has the measure of a thing will, at the moment the
        fight pivots, put everything available into a single committed
        strike. Not rage — arithmetic. The body executes what the mind
        decided three moves ago, in the dark, while counting torches.
      mechanical_effect: >-
        Once per scene, on a successful strike beat, deal bonus damage equal
        to half your character level (minimum 1, rounded down). This is the
        WWN Warrior Killing Blow (SRD §1.5.18). Requires warrior: true.
      involuntary: false
    - name: "Veteran's Luck"
      genre_description: >-
        Survivors of the shaft develop a quality that looks from the
        outside like luck and is in fact the accumulated consequence of
        having walked out of rooms that were statistically a grave. When
        the odds turn, something shifts slightly in the wrong direction
        for whatever is trying to kill them.
      mechanical_effect: >-
        Once per scene, convert a missed attack that targeted you into a
        near-miss instead — you suffer no damage or secondary effect from
        the attack. This is the WWN Warrior Veteran's Luck (SRD §1.5.18).
        Requires warrior: true.
      involuntary: false

# ── Expert chassis ───────────────────────────────────────────────────────────

- id: expert
  display_name: Expert
  rpg_role: skirmisher
  jungian_default: explorer
  minimum_score: 9
  kit_table: expert_kit
  prime_requisite: DEX
  flavor: >-
    The Expert has been into the old workings and the older records and
    come back from both. Their competence is earned, not inherited: they
    read a room's exits the way other people read a face, know which
    silences in a dead gallery are safe to walk through and which are
    not, and keep their accounts with the camp's quartermaster scrupulously
    clean, because a delver who owes nothing can leave at any time.
  encounter_beat_choices:
    - strike
    - brace
    - break_contact
    - sprint
    - duck_through
    - douse_torch
    - talk_up_the_haul
    - swear_its_not_cursed
    - plead_poverty
    - flash_the_coin
    - walk_toward_the_door
  saving_throws:
    death_ray_or_poison: 13
    magic_wands: 14
    paralysis_or_stone: 13
    dragon_breath: 16
    rods_staves_spells: 15
  abilities:
    - name: "Read the Ledger"
      genre_description: >-
        When the Expert recognizes what they are dealing with — a trap's
        maker, a creature's habit, the shape of a bargain going wrong —
        they do not just know the theory. They know the theory's gap:
        the weakness its maker assumed no one would live to read about.
      mechanical_effect: >-
        Once per confrontation, spend your beat in study to identify a single
        weakness or exploitable tag on the opponent. The next strike that
        targets that tag resolves at advantage. Works against any opponent
        with a discernible technique or pattern — not against random violence.
      involuntary: false

# ── Mage chassis ─────────────────────────────────────────────────────────────

- id: mage
  display_name: Mage
  rpg_role: control
  jungian_default: magician
  minimum_score: 9
  kit_table: mage_kit
  prime_requisite: INT
  flavor: >-
    The Mage works the old arithmetic of the deep — workings copied from
    pages that came up the rope in dead men's packs, practised by lamplight
    until the body learned what the page could not say. Every working is
    paid for out of the caster: in Effort, in System Strain, in the slow
    residue the craft leaves in the hands and the eyes. The camp does not
    trust them. The camp also does not go down without them.
  encounter_beat_choices:
    - strike
    - brace
    - break_contact
    - sprint
    - duck_through
    - plead_poverty
    - flash_the_coin
    - walk_toward_the_door
  magic_access: wwn
  # governing_attr INTELLIGENCE → INT (rules.yaml attribute_map).
  wwn_magic:
    effort_sources:
      - source: mage
        governing_attr: INTELLIGENCE
        relevant_skill: Magic
        starting_skill_level: 1
    casts_per_day_by_level:
      "1": 2
    max_spell_level_by_level:
      "1": 1
    prepared_by_level:
      "1": 2
    starting_prepared:
      - wracking_bolt
      - sleepless_tithe
    partial: false
  saving_throws:
    death_ray_or_poison: 13
    magic_wands: 14
    paralysis_or_stone: 13
    dragon_breath: 16
    rods_staves_spells: 15
  abilities:
    - name: "Read the Worked Stone"
      genre_description: >-
        The Mage can put a palm to stone the hold once worked and ask it
        what it remembers — which hands cut it, what passed this way, what
        the seam ahead was doing when the digging stopped. The stone
        answers slowly, in the manner of something that has had two
        lifetimes to compose its account, and it does not lie.
      mechanical_effect: >-
        Spend 1 Effort (Effort-1) to extract one concrete fact about the
        immediate area from worked stone — adjudicated by the narrator (a
        direction, a former purpose, a warning). Once per scene. Cannot
        activate at Effort 0. Works only on stone shaped by tools; the
        unworked deep keeps no accounts.
      involuntary: false
```

- [ ] **Step 2: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content
git add genre_packs/caverns_and_claudes/classes.yaml
git commit -m "feat(caverns): WWN 3-chassis Callings (Warrior/Expert/Mage), heavy_metal mechanics"
```

---

### Task 4: rules.yaml — ruleset binding + WWN combat

**Files:**
- Rewrite: `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`

- [ ] **Step 1: Replace the entire file with the content below.**

What's kept from the old file verbatim: `custom_rules`, `stat_display_fields`, `encounter_base_tension`, `initiative_rules`, `default_location`, `default_time_of_day`, the **chase** and **negotiation** confrontations (dial-resolved, unchanged per spec §2). What's gone: `allowed_races`/`default_race`/`banned_spells`/`magic_level` (B/X scaffolding, 87-2 precedent), `edge_config`, the dial combat def with its momentum metrics and `morale:` block.

```yaml
stat_generation: point_buy
point_buy_budget: 27

# WWN port (2026-06-12 beneath-sunden-wwn-port spec). B/X scaffolding
# (allowed_races / default_race / banned_spells / magic_level) removed per
# the heavy_metal 87-2 precedent: races are world-tier and WWN gates spell
# access by class spell list, not a ban list. allowed_classes is NOT 5e
# residue — encountergen's humanoid-enemy path exits 1 without it, and the
# loader validates every listed class declares encounter_beat_choices.
# Keep it in sync with classes.yaml display names.
allowed_classes:
  - Warrior
  - Expert
  - Mage

custom_rules:
  treasure_as_xp: "true"
  keeper_awareness: "true"
  resource_ticks: "true"
  extraction_phase: "true"
  encumbrance: "strict"
  injuries: "permanent"

# default_class is the class DISPLAY NAME (not the id) — the chargen builder
# resolves the default ClassDef by display_name (builder.py), with no id
# fallback. A freeform character with no class_hint falls through to this
# default, so it MUST be a real display_name. Matches the EH/heavy_metal
# convention.
default_class: Warrior
class_label: Calling
default_location: "The mouth of the dungeon"
default_time_of_day: dawn

ability_score_names:
  - STR
  - DEX
  - CON
  - INT
  - WIS
  - CHA

lethality: high

ruleset: wwn
wwn:
  # Required by _validate_wwn: all six canonical WWN attribute keys, each
  # mapping to a declared ability_score_names entry. This pack uses the
  # standard abbreviations, so the map is canonical -> abbreviation.
  attribute_map:
    STRENGTH: STR
    DEXTERITY: DEX
    CONSTITUTION: CON
    INTELLIGENCE: INT
    WISDOM: WIS
    CHARISMA: CHA
  system_strain:
    # max_source must be a canonical KEY of attribute_map (not "CON").
    max_source: CONSTITUTION
    rest_recovery_per_night: 1
    first_aid_cost: 1
  trauma:
    # Faithful WWN/heavy_metal baseline; lethality tuning is Keith's call.
    default_trauma_target: 6
    mortal_injury_rounds: 6
    major_injury_save: physical
  magic:
    effort_base: 1
    killing_blow_divisor: 2
    day_reclaim_requires_comfort: true
    default_spell_save: mental

stat_display_fields:
  - torches
  - rations
  - encumbrance
  - gold

encounter_base_tension:
  random: 0.15
  ambush: 0.40
  boss: 0.50
  final: 0.60

initiative_rules:
  combat:
    primary_stat: DEX
    description: "Reflexes and speed determine who strikes first"
  chase:
    primary_stat: DEX
    description: "Agility and footwork set the pace"
  social:
    primary_stat: CHA
    description: "Force of personality controls the conversation"
  exploration:
    primary_stat: WIS
    description: "Awareness determines who notices things first"

# ── Confrontations ──────────────────────────────────────────
confrontations:
  - type: combat
    label: Dungeon Combat
    intent_verbs: [strike, attack, fight, kill, slay, swing, shoot, hit, stab]
    on_intent_mismatch: reprompt
    category: combat
    # WWN personal combat: attack-vs-AC + hp_depletion on the ablative
    # HpPool. Trauma / Mortal Injury layer on via the wwn ruleset module.
    resolution_mode: beat_selection
    win_condition: hp_depletion
    opponent_default_stats:
      # ALL SIX ability scores must be authored so the WWN defender-save
      # path can resolve any save (Mental = best-of WIS/CHA, etc.). The SWN
      # module fails loud on a missing save attribute — an incomplete block
      # KeyErrors.
      STR: 10
      DEX: 10
      CON: 10
      INT: 10
      WIS: 10
      CHA: 10
      # Reserved combat-seed keys (not ability scores): hp = HP pool;
      # armor_class = ascending AC the attack rolls against; dexterity =
      # initiative (1d8 + DEX). A starveling of the shaft: AC 12, HP 10.
      hp: 10
      armor_class: 12
      dexterity: 11
    # Opponent reprisal damage. Without this the seeded Other hits but deals
    # 0 HP (toothless-Other class of bug: EH playtest #16 / ADR-139
    # Invariant 3). 1d8: lethality: high, and the deep does not pull its
    # blows. Read only on the opponent's turn; never caps the player's own
    # weapon.
    opponent_damage: {dice: "1d8", bonus: 0}
    beats:
      - id: strike
        label: Strike
        kind: strike
        base: 2
        stat_check: STR
        attack_bonus: 1
        combat_skill: 1
        damage_channel: strike
        effect: "Target takes damage this round"
        narrator_hint: >-
          Steel on stone-dark air. Describe the blow with specificity —
          which grip, which angle, what gave way. Combat in the deep is
          work, not choreography; narrate it like labor that can kill.
      - id: cast_spell
        label: Cast Spell
        kind: strike
        base: 2
        stat_check: INT
        attack_bonus: 1
        combat_skill: 1
        damage_channel: none
        # class_filter restricts this beat to the caster Calling. Display
        # name (loader validates class_filter against classes.yaml
        # display_name). This is the ONLY gate that offers cast_spell, so
        # the WWN cast resource gate fires (heavy_metal/EH pattern).
        class_filter: [Mage]
        effect: "Cast a prepared spell — damage rolled by the WWN spell engine"
        narrator_hint: >-
          The Mage spends a prepared working. Describe the cost as
          concretely as the effect — what the working takes from the body
          that served as its gate, by torchlight, in front of people who
          are counting on it.
      - id: brace
        label: Brace
        kind: brace
        base: 1
        stat_check: CON
        effect: "Reduce incoming damage this round"
        narrator_hint: >-
          Shield up, back to the worked wall, weight forward. The character
          sets themselves and takes the impact; the body pays for it later.
      - id: committed_blow
        label: Committed Blow
        kind: strike
        base: 4
        stat_check: STR
        attack_bonus: 1
        combat_skill: 1
        damage_channel: strike
        damage_override: {dice: "2d6", bonus: 0}
        deltas:
          crit_fail:
            own: -3
        risk: "Overcommits — a botched all-in swing costs you (−3 on a critical failure)"
        effect: "Target takes heavy damage"
        narrator_hint: >-
          An all-in swing; the character is not planning a follow-up.
          Describe the violence as expensive — to the one making it as
          well as the one receiving it. The deep keeps the receipt.
      - id: break_contact
        label: Break Contact
        kind: push
        stat_check: DEX
        consequence: "Combat ends — the character withdraws deeper into the dungeon, or the enemy lets them go"
        narrator_hint: >-
          Disengagement is a real choice in the deep, and it always costs
          ground. Describe what is given up: the room, the body, the light.
    mood: combat
  - type: chase
    label: Corridor Pursuit
    intent_verbs: [chase, pursue, flee, run, escape, follow]
    on_intent_mismatch: reprompt
    category: movement
    player_metric:
      name: separation
      starting: 0
      threshold: 7
    opponent_metric:
      name: pursuit
      starting: 0
      threshold: 7
    beats:
      - id: sprint
        label: Sprint
        kind: push
        base: 2
        stat_check: DEX
        narrator_hint: Boots echo off stone as the quarry bolts down the passage.
      - id: duck_through
        label: Duck Through
        kind: angle
        target_tag: "Out of Sight"
        stat_check: INT
        narrator_hint: Squeeze through a side passage too narrow for pursuers.
      - id: barricade
        label: Barricade
        kind: brace
        base: 1
        stat_check: INT
        effect: "Topple debris to slow pursuit"
      - id: douse_torch
        label: Douse Torch
        kind: push
        base: 1
        stat_check: DEX
        consequence: "Chase ends in darkness — quarry vanishes"
    mood: tension
  - type: negotiation
    label: "Haggling at the Counter"
    intent_verbs: [haggle, bargain, barter, offer, deal, price, sell, buy, negotiate]
    on_intent_mismatch: warn
    category: social
    player_metric:
      name: leverage
      starting: 0
      threshold: 7
    opponent_metric:
      name: leverage
      starting: 3
      threshold: 7
    beats:
      - id: talk_up_the_haul
        label: "Talk Up the Haul"
        kind: strike
        base: 2
        stat_check: CHA
        effect: "merchant entertains the asking price — their eyebrow does the thing"
        narrator_hint: "The delver pitches the goods like a town crier."
      - id: swear_its_not_cursed
        label: "Swear It's Not Cursed"
        kind: strike
        base: 3
        deltas:
          crit_fail:
            own: -1
        stat_check: CHA
        risk: "if the bluff fails, merchant knocks 50% off the offer"
        effect: "merchant accepts the suspicious item — with a receipt, carefully worded"
        narrator_hint: "Running-joke territory. Lean all the way in."
      - id: plead_poverty
        label: "Plead Poverty"
        kind: angle
        target_tag: "Sympathetic"
        stat_check: WIS
        effect: "merchant softens — sets up a leverage tag for the closer"
        narrator_hint: "The delver goes for the sympathy play."
      - id: flash_the_coin
        label: "Flash the Coin"
        kind: brace
        base: 1
        stat_check: CHA
        effect: "merchant's disposition tightens — the real price slips out"
        narrator_hint: "A small concession now to read the shop properly."
      - id: walk_toward_the_door
        label: "Walk Toward the Door"
        kind: push
        base: 1
        stat_check: WIS
        consequence: "Negotiation ends — leave with the merchant's last offer"
    mood: comedic
```

- [ ] **Step 2: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content
git add genre_packs/caverns_and_claudes/rules.yaml
git commit -m "feat(caverns): bind ruleset wwn — point-buy, WWN combat, drop dial scaffolding"
```

---

### Task 5: magic.yaml rewrite + retire the B/X spell surface

**Files:**
- Rewrite: `sidequest-content/genre_packs/caverns_and_claudes/magic.yaml`
- Delete: `sidequest-content/genre_packs/caverns_and_claudes/spellbook.yaml`
- Delete: `sidequest-content/genre_packs/caverns_and_claudes/spells/` (arcane_l1.yaml, divine_l1.yaml)

- [ ] **Step 1: Replace magic.yaml with:**

```yaml
# magic.yaml — caverns_and_claudes genre layer
#
# 2026-06-12: WWN port (beneath-sunden-wwn-port spec). The B/X spell-slot
# surface (innate_v1 / learned_v1, spellbook.yaml, spells/*_l1.yaml) is
# RETIRED — player casting now runs through the wwn ruleset module
# (classes.yaml wwn_magic + spells_wwn.yaml catalog: prepared spells,
# Effort, System Strain). This file governs the ITEM magic surface, which
# remains core crawl gameplay: scrolls, potions, wands, cursed relics.

genre: caverns_and_claudes

# Runtime sources. ``item_based`` only — caster-class magic is the wwn
# module's concern, not a magic.yaml plugin.
allowed_sources: [item_based]

# ``item_legacy_v1`` covers scrolls, potions, wands, cursed swords, sealed
# reliquaries.
permitted_plugins: [item_legacy_v1]

intensity:
  default: 0.3

# Folkloric is the load-bearing C&C register: commoners know stories, the
# Delver knows scrolls work because they've seen them work. The camp's
# Mage is not a scholar of an academy — there are no academies — but a
# practitioner of recovered workings; folkloric still holds above ground.
world_knowledge_default:
  primary: folkloric

hard_limits:
  - id: no_resurrection
    description: "Death is permanent. No resurrection magic — finding a 'true' resurrection scroll IS the campaign hook, never the answer."
  - id: no_true_creation
    description: "Magic does not create matter ex nihilo. Items conjure, transmute, or summon-from-elsewhere; nothing is made from nothing."
  - id: no_unlimited_high_evocation
    description: "Fire/lightning/blast effects exist but are bounded — wand charges, scroll one-shots, potion durations, Effort and System Strain. No infinite blasters."
  - id: no_plane_shift
    description: "Player characters do not travel between planes. Things may bleed through; players cannot follow."
  - id: no_permanence_without_renewal
    description: "All magic decays or is consumable. Wands run out, scrolls burn, potions drain. Even reliquaries demand upkeep."

# Cost vocabulary for the ITEM surface. ``components`` covers
# item-activation physical price (ash, blood, the second-to-last torch);
# ``backlash`` covers consequence-of-use (cursed item awakens, attention
# drawn). The B/X ``spell_slots`` / ``divine_favor`` cost types are retired
# with the plugins that consumed them — WWN casting costs (casts/day,
# Effort, System Strain) are tracked by the wwn module, not the ledger.
cost_types: [components, backlash]

narrator_register: |
  Magic in the deep is found AND prepared. The Mage spends the morning
  over recovered pages, fixing a working in the mind; so many castings a
  day, and each one paid for out of the body — Effort spent, System
  Strain carried, the residue of the craft visible in the hands by lamp-
  light. Items sit alongside the workings: scrolls flake to ash on first
  reading, potions drain to the rind, wands count down to dead bone.
  Every working surfaces its cost in the same beat as its effect. Do not
  narrate magic as ambient atmosphere. Do not narrate cost-free workings.
  Do not narrate spells outside the canonical spells_wwn.yaml catalog; if
  a player names a working that isn't in the catalog, the page is blank
  and the working does not exist in the world. Cursed items remain the
  genre's signature trap — desirable until the bill arrives, and the bill
  arrives. The hands that wrote these pages went down the same rope the
  players did. Most did not come back up. Some are still down there.
```

- [ ] **Step 2: Delete the retired B/X files**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content/genre_packs/caverns_and_claudes
git rm spellbook.yaml spells/arcane_l1.yaml spells/divine_l1.yaml
```

- [ ] **Step 3: Check the world tier for B/X magic references**

```bash
grep -rn "spell_slots\|divine_favor\|innate_v1\|learned_v1\|spellbook" worlds/beneath_sunden/
```

If any hits (e.g. a world-tier spellbook.yaml or a `divine_favor` bar instantiation): remove those blocks too — they reference a retired subsystem and would be dead config. Include them in this commit.

- [ ] **Step 4: Commit**

```bash
git add -A genre_packs/caverns_and_claudes
git commit -m "feat(caverns): retire B/X spell-slot surface — item magic + WWN module casting"
```

(Run from the sidequest-content repo root.)

---

### Task 6: char_creation.yaml — point-buy, three Callings

**Files:**
- Rewrite: `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml`

- [ ] **Step 1: Replace the entire file with the content below.**

Point-buy packs carry no stat-roll scene (EH/heavy_metal precedent — stats come from `rules.yaml stat_generation`); the B/X `the_roll` and `the_arrangement` scenes are dropped. The Brecca framing and the remaining scene skeleton (calling → story → kit → mouth) are kept — the FSM hints (`class_hint`, `identity_capture`, `equipment_generation`) are unchanged shapes.

```yaml
# Character creation — Caverns & Claudes (WWN era)
# 4 scenes: calling → story → kit → mouth.
# Point-buy pack (rules.yaml stat_generation: point_buy) — no roll/arrange
# scenes; the builder seeds attributes from the point-buy budget, per the
# elemental_harmony / heavy_metal precedent. The B/X visible-3d6 scenes
# were retired in the 2026-06-12 WWN port.

- id: the_calling
  title: "What You'll Be Called"
  narration: |
    You sit at a scarred table in a lamplit room that smells of tallow and
    old sweat. Brecca Half-Hand — missing three fingers from her left hand,
    seven-delve veteran — opens the ledger and looks at you the way she
    looks at rope: checking for the flaw that will kill someone later.

    "Three trades go down the rope," she says. "Pick the one you'll die as.
    The dungeon doesn't care which. The records do."
  choices:
    - label: "Warrior"
      description: "Mail, a long blade, and the patience to be hit first."
      mechanical_effects:
        class_hint: Warrior
        rpg_role_hint: tank
        jungian_hint: hero
    - label: "Expert"
      description: "Lockpicks, leather, and a professional interest in being elsewhere."
      mechanical_effects:
        class_hint: Expert
        rpg_role_hint: skirmisher
        jungian_hint: explorer
    - label: "Mage"
      description: "Recovered pages, a steady hand, and a body that pays for every working."
      mechanical_effects:
        class_hint: Mage
        rpg_role_hint: control
        jungian_hint: magician
  allows_freeform: false

- id: the_story
  title: "For The Tally"
  narration: |
    Brecca dips the quill and looks up. "For the tally," she says. "In case
    you don't come back."

    She wants three things: how to refer to you, what you did before, and
    what you look like. Or you can let her make something up.
  loading_text: "Brecca writes in the ledger..."
  choices: []
  allows_freeform: true
  mechanical_effects:
    identity_capture:
      pronouns_required: true
      background_optional: true
      description_optional: true
    background_autogen_source: backstory_tables

- id: the_kit
  title: "What You Have"
  narration: |
    Brecca reaches beneath the table and drops a canvas sack in front of you.
    It lands with a dull thud. "Standard kit," she says. "Sized to the trade.
    Some of it's useful. Some of it isn't. All of it's yours now."
  choices: []
  allows_freeform: false
  mechanical_effects:
    equipment_generation: class_kit

- id: the_mouth
  title: "The Dungeon Waits"
  narration: |
    Dawn. The mouth of the dungeon is a crack in the hillside, edged with
    moss and old tooth-marks in the stone. Cold air breathes outward, carrying
    the smell of wet rock and something older.

    Behind you, the town is already forgetting your name. Ahead, the dark
    waits with the patience of something that has swallowed better than you.
  choices: []
  allows_freeform: false
```

- [ ] **Step 2: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content
git add genre_packs/caverns_and_claudes/char_creation.yaml
git commit -m "feat(caverns): point-buy chargen, three WWN Callings"
```

---

### Task 7: Coupled surfaces — lethality, cash, archetypes, bestiary header — then validator GREEN

**Files:**
- Rewrite: `sidequest-content/genre_packs/caverns_and_claudes/lethality_policy.yaml`
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml` (starting-cash block, ~line 405)
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/archetypes.yaml` (typical_classes lists)
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/bestiary.yaml` (header comment only)

- [ ] **Step 1: Replace lethality_policy.yaml entirely**

The current policy (`comedic_danger_no_permadeath`, humiliated-on-zero-HP) contradicts both `lethality: high` + WWN Mortal Injury and the world register's "grave, lethal, Moria-as-tragedy." New content, modeled on heavy_metal's:

```yaml
genre_key: caverns_and_claudes
default_reversibility: permanent
verdicts_on_zero_hp:
  pc: dead
  npc: dead
soul_md_constraint: "genre_truth:lethal_for_this_genre"
must_narrate: "Render the death with specific, grave detail — the deep is a working that kills workers, and the camp keeps a Board of the Unreturned for a reason. Honor the promise of lethality; record the cost."
must_not_narrate: "narrate survival; invent an ally's last-second intervention; soften the damage after the fact; play the death for comedy — the name goes on the Board, and the Board is never funny"
```

- [ ] **Step 2: inventory.yaml — re-key the starting-cash map**

Replace the class-keyed cash block (currently `Delver: 10 / Fighter: 60 / Cleric: 50 / Mage: 80 / Thief: 75` with its comment, ~lines 404–415) with:

```yaml
  # deterministic mid-band values. Tuned so every class can engage the
  # Sünden Recruiter's Post (two-silver-bond gate) at chargen-end —
  # patron-power-fantasy was unreachable with 0 gold (playtest 2026-05-06,
  # Carl-the-Cleric vs Brenna). Re-keyed for the WWN Callings (2026-06-12
  # port): Warrior carries the heavier starting kit, Expert and Mage lean
  # on cash for tools and recovered pages.
  Delver: 10
  Warrior: 60
  Expert: 75
  Mage: 80
```

(Values are the old per-role values carried over — Fighter→Warrior 60, Thief→Expert 75, Mage→Mage 80. Cleric's 50 retires with the class. No retuning.)

- [ ] **Step 3: worlds/beneath_sunden/archetypes.yaml — re-key typical_classes**

Four lists reference the old classes. Apply the mapping Fighter→Warrior, Thief→Expert, Cleric→Mage (the rite-keeper niche folds into the camp's recovered-workings practitioner):

- ~line 36 (`typical_classes: [Fighter]`) → `[Warrior]`
- ~line 81 (`[Fighter, Thief]`) → `[Warrior, Expert]`
- ~line 127 (`[Fighter, Thief, Cleric]`) → `[Warrior, Expert, Mage]`
- ~line 220 (`[Thief]`) → `[Expert]`

- [ ] **Step 4: bestiary.yaml — fix the stale header line**

In the header comment, replace the line:

```
# SRD-aligned generic stat lines (caverns_and_claudes native dial engine,
```

with:

```
# SRD-aligned generic stat lines (wwn ruleset module — see rules.yaml,
```

The stat-block fields themselves are already WWN-shaped (level/hp/armor_class/attack_bonus/damage/morale/skill/save); change nothing else in this file.

- [ ] **Step 5: Sweep for surviving stale references**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content/genre_packs/caverns_and_claudes
grep -rn "Fighter\|Cleric\|Thief\|Magic-User\|edge_config\|spell_slots\|roll_3d6" . | grep -v "fallback_name\|Carl-the-Cleric"
```

Expected: no hits. (`archetype_constraints.yaml`'s `fallback_name: "Fighter"/"Cleric"/"Thief"` entries are NPC archetype titles, not class references — they stay. The Carl-the-Cleric playtest comment is history — it stays.) Fix any other hit by the same mapping.

- [ ] **Step 6: Run the validator — this is the gate**

```bash
cd /Users/slabgorb/Projects/oq-3 && just content-validate caverns_and_claudes
```

Expected: PASS (exit 0). Likely first-run failures and their meanings:
- `starting_prepared id ... does not resolve` → spell id typo'd or deleted in Task 2; restore/fix the id in spells_wwn.yaml.
- `classes missing saving_throws` → a class block lost its saving_throws table.
- `class_filter ... not a display_name` → rules.yaml `class_filter: [Mage]` vs classes.yaml `display_name` mismatch.
- `attribute_map` errors → a canonical key missing or mapping to an undeclared ability name.

Iterate until green. Do NOT silence a failure by deleting the thing it points at without understanding it.

- [ ] **Step 7: Run the server test suite against the new pack** (catches loader-level regressions the validator doesn't own)

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-server && uv run pytest tests/ -x -q -k "caverns or genre_loader or pack"
```

Expected: PASS, or failures that are demonstrably the pre-existing OTEL-deadlock / MessageType-count knowns (verify against the failure text before dismissing; if a failure names caverns content, it's ours).

- [ ] **Step 8: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content
git add -A genre_packs/caverns_and_claudes
git commit -m "feat(caverns): lethal policy, re-keyed cash/archetypes, bestiary header — validator green"
```

---

### Task 8: Server wiring proof — test_wwn_caverns_dispatch.py

**Files:**
- Create: `sidequest-server/tests/integration/test_wwn_caverns_dispatch.py`
- Read first: `sidequest-server/tests/integration/test_wwn_elemental_harmony_dispatch.py` (the template — read it END TO END before writing)

- [ ] **Step 1: Copy the EH test as the starting point**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-server
cp tests/integration/test_wwn_elemental_harmony_dispatch.py tests/integration/test_wwn_caverns_dispatch.py
```

- [ ] **Step 2: Apply the caverns substitutions**

Every EH-specific value has a caverns counterpart. Replace:

| EH value | caverns value |
|---|---|
| `elemental_harmony` (pack name, `find_pack_path`, docstrings) | `caverns_and_claudes` |
| `_OPPONENT_HP = 8` | `_OPPONENT_HP = 10` (rules.yaml `opponent_default_stats.hp`) |
| `_OPPONENT_AC = 12` | `_OPPONENT_AC = 12` (unchanged) |
| `_EXPECTED_PREPARED = ["cinder_lance", "river_step"]` | `_EXPECTED_PREPARED = ["wracking_bolt", "sleepless_tithe"]` |
| `_DAMAGE_SPELL = "cinder_lance"` | `_DAMAGE_SPELL = "wracking_bolt"` (1d6, damage_per_level, save: physical) |
| `Channeler` (class name, helper names, followup text) | `Mage` |
| "Martial Exchange" (combat label in the seat helper) | `"Dungeon Combat"` |

- [ ] **Step 3: Rewrite the chargen walk for the caverns scene list**

The EH walk picks choice 0 on the origins scene to land a Channeler. The caverns scene list (Task 6) opens with `the_calling`, where **Mage is choice index 2**. Replace the builder-walk loop's choice logic with:

```python
    # Drive scenes to confirmation. the_calling choice 2 is the Mage;
    # every other scene is advanced generically.
    _guard = 0
    while not builder.is_confirmation():
        _guard += 1
        assert _guard < 50, "chargen walk did not reach confirmation"
        if builder.is_awaiting_followup():
            builder.answer_followup("Mage of the Ropefoot camp")
            continue
        scene = builder.current_scene()
        if not scene.choices:
            try:
                builder.apply_auto_advance()
            except Exception:
                builder.apply_freeform(name)
            continue
        if scene.id == "the_calling":
            builder.apply_choice(2)  # Mage
        else:
            builder.apply_choice(0)
```

Keep the rest of the helper (CharacterBuilder construction, `with_equipment_tables`, `with_classes`, `build(name)`) byte-identical to the EH version.

- [ ] **Step 4: Keep all four EH assertions, retargeted**

1. `caster.core.spellcasting.casts_remaining` decremented (2 → 1);
2. opponent `core.hp.current` reduced below `_OPPONENT_HP` (wracking_bolt damage through the HP channel);
3. `wwn.spell.cast` span fired (InMemorySpanExporter);
4. NEGATIVE: the B/X `magic.cast_spell_*` watcher events did NOT fire — doubly load-bearing here, since this port just retired the B/X innate path for this pack.

Keep the rng monkeypatch pinning and the content-not-on-disk skip pattern unchanged.

- [ ] **Step 5: Run the test — expect it to FAIL first if content branch isn't checked out**

The test reads the real pack from disk. Make sure the sidequest-content checkout is on `feat/wwn-port-caverns`, then:

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-server
uv run pytest tests/integration/test_wwn_caverns_dispatch.py -v -n0
```

Expected: PASS (all assertions). `-n0` because OTEL span-count tests deadlock under parallel xdist (known). If it fails, debug the actual failure — common trap: the chargen walk not landing the Mage (assert `character.char_class == "Mage"` early in the test to localize).

- [ ] **Step 6: Lint + commit**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-server
uv run ruff check tests/integration/test_wwn_caverns_dispatch.py && uv run ruff format tests/integration/test_wwn_caverns_dispatch.py
git add tests/integration/test_wwn_caverns_dispatch.py
git commit -m "test(wwn): caverns_and_claudes end-to-end wiring proof — Mage cast through real dispatch"
```

---

### Task 9: Full gates, PRs

- [ ] **Step 1: Full validator + server check**

```bash
cd /Users/slabgorb/Projects/oq-3 && just content-validate caverns_and_claudes
cd /Users/slabgorb/Projects/oq-3/sidequest-server && uv run ruff check . && uv run pytest tests/ -q -n0 -k "wwn"
```

Expected: validator exit 0; all wwn-tagged tests pass.

- [ ] **Step 2: Headless playtest smoke (optional but recommended)**

With server running (`just server` in another pane):

```bash
cd /Users/slabgorb/Projects/oq-3 && just playtest --genre caverns_and_claudes
```

Watch for a combat to seat and `state_patch_hp` spans on the GM dashboard (`just otel`). The lie detector: if combat narrates but no HP spans fire, the binding didn't take.

- [ ] **Step 3: Push + PR — content repo (base develop)**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-content
git push -u origin feat/wwn-port-caverns
gh pr create --base develop --title "feat(caverns): port caverns_and_claudes / Beneath Sünden to WWN" --body "$(cat <<'EOF'
Ports the pack (sole world: beneath_sunden) from native dials to the WWN SRD ruleset per docs/superpowers/specs/2026-06-12-beneath-sunden-wwn-port-design.md (orchestrator repo).

- ruleset: wwn + full config block; point-buy 27; lethality: high
- Three Callings (Warrior/Expert/Mage) — heavy_metal chassis, mechanics unretuned
- WWN combat (beat_selection / hp_depletion, opponent_damage 1d8); chase + negotiation stay dials
- spells_wwn.yaml ported from heavy_metal; B/X spell-slot surface (spellbook.yaml, spells/, innate_v1/learned_v1) retired
- lethality_policy now permanent-death (was comedic-no-permadeath — contradicted the world register)
- bestiary stat blocks were already WWN-shaped; header comment fixed

## Hard-limit calls for Keith
<list any spells flagged in Task 2 Step 4, or "none">

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 4: Push + PR — server repo (base develop)**

```bash
cd /Users/slabgorb/Projects/oq-3/sidequest-server
git push -u origin feat/wwn-caverns-wiring-test
gh pr create --base develop --title "test(wwn): caverns_and_claudes wiring proof" --body "$(cat <<'EOF'
End-to-end wiring proof for the caverns_and_claudes WWN port (content PR: sidequest-content feat/wwn-port-caverns — merge that first; this test reads the real pack from disk).

Real Mage chargen → real Dungeon Combat seat → cast_spell through _apply_narration_result_to_snapshot → asserts casts decrement, opponent HP reduction, wwn.spell.cast span, and NO B/X magic.cast_spell_* events.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: Note the cross-repo merge order in both PRs**

Content PR merges first; the server test PR's CI will read the content from whatever ref CI checks out — if CI pins content to develop, the server PR stays red until the content PR lands. That ordering is correct and expected; do not "fix" it by weakening the test's skip condition.

---

## Self-Review Notes

- **Spec coverage:** §1 ruleset binding → Task 4; §2 combat/dials → Task 4; §3 classes → Task 3; §4 spells+magic → Tasks 2, 5; §5 chargen → Task 6; §6 bestiary → Task 7; §7 flavor → embedded in each rewritten file; §8 wiring proof → Task 8; lethality contradiction (found during planning, not in spec) → Task 7 Step 1.
- **Known leave-alones:** `archetype_constraints.yaml` fallback_names (NPC titles, not classes); `progression.yaml` (affinity-based, class-agnostic); `equipment_tables.yaml` (item-id tables, class-agnostic); `beat_vocabulary.yaml` (obstacle vocab, no beat-id coupling); the ADR-106 dungeon engine and all of `worlds/beneath_sunden/rooms|cookbook|corpus|cartography`.
- **Deliberate scope cut:** heavy_metal's Barsoom-only spells are deleted from the copied catalog rather than carried as dead entries (No Stubbing / dead code is worse than no code).
