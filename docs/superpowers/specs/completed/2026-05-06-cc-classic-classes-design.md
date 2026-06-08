# Caverns & Claudes — Classic Classes (v1)

**Date:** 2026-05-06
**Owner:** PM (Houlihan) → Dev
**Status:** spec — awaiting user approval before implementation plan
**Scope:** caverns_and_claudes genre pack only

## Problem

C&C chargen is currently anti-backstory but also anti-*identity* — every character emerges as `rpg_role_hint=jack_of_all_trades, jungian_hint=hero` because the scene flow hardcodes those hints. The pack already declares classic OSR fallback names (Fighter / Wizard / Cleric / Thief) and the server-side chargen builder already supports `class_hint` as a first-class mechanical effect, but no scene picks one. The result is mechanically identical delvers with no class fantasy.

## Goal

Let the player pick **Fighter, Mage, Cleric, or Thief** during chargen, with B/X-style prime-requisite gating against rolled stats. Class influences starting `max_edge`, starting equipment kit, and a forward-compatible slot for class-specific encounter beats and magic access (those are *future* work — empty in v1).

## Non-Goals

- **Race.** Deferred to a later story. This spec touches no race code, no race YAML, no `race_hint`.
- **Class encounter-beat choices.** Slot reserved (`encounter_beat_choices: []`), no logic.
- **Magic system access.** Slot reserved (`magic_access: null`), no logic. Mage's spellbook in v1 is narrator flavor only.
- **HP / Hit Dice.** Not introduced. Per ADR-014, this game uses momentum/edge/fate. Class influences `max_edge`, not HP.
- **Multi-classing, level limits, alignment, XP-for-prime-requisite bonuses.** Out.
- **Backwards compatibility for existing C&C saves.** Per project memory, legacy saves are throwaway.

## Existing Infrastructure to Reuse

This is a **wiring + content** story, not a build story.

| Surface | Already exists | What v1 adds |
|---|---|---|
| `Character.char_class: str` | yes (`sidequest-server/sidequest/game/character.py`) | nothing — populated via existing path |
| `class_hint` mechanical effect | yes (`builder.py`, ~line 160 / 365 / 778) | nothing |
| `rpg_role_hint` axis (Fighter/Wizard/Cleric/Thief fallback names) | yes (`axes.yaml`) | per-class mapping |
| `equipment_generation: random_table` | yes (`equipment_tables.yaml`) | adds 4 class-themed tables |
| Edge resource (`max_edge`) | yes | new `set_starting_max_edge` mechanical effect |

Other packs (`space_opera`, `elemental_harmony`, `mutant_wasteland`, `tea_and_murder`) already use `class_hint` in their `char_creation.yaml`. C&C is the outlier.

## Design

### §1 — `classes.yaml` (new file)

Path: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`

> The `flavor:` strings below are illustrative content — final wording is whoever-implements-it's call. The required *fields* (id, display_name, rpg_role, jungian_default, prime_requisite, minimum_score, starting_max_edge, kit_table, encounter_beat_choices, magic_access) are the spec.

```yaml
# Caverns & Claudes — Classic Classes
# B/X-flavored fighter / mage / cleric / thief.
# Class influences starting max_edge and equipment kit.
# Future hooks (encounter beats, magic access) are reserved as empty slots.

- id: fighter
  display_name: Fighter
  rpg_role: tank
  jungian_default: hero
  prime_requisite: STR
  minimum_score: 9
  starting_max_edge: 4
  kit_table: fighter_kit
  flavor: >-
    Plate, polearm, and the patience to be hit first. The Fighter does
    not flinch, does not strategize, and does not need to. The dungeon
    is solved with violence applied at the correct angle.
  encounter_beat_choices: []
  magic_access: null

- id: mage
  display_name: Mage
  rpg_role: control
  jungian_default: magician
  prime_requisite: INT
  minimum_score: 9
  starting_max_edge: 2
  kit_table: mage_kit
  flavor: >-
    Bookish, half-blind, and dangerous in the third round. The Mage
    is a glass cannon held together by component pouches and the
    nervous conviction that the spellbook is correct.
  encounter_beat_choices: []
  magic_access: null

- id: cleric
  display_name: Cleric
  rpg_role: healer
  jungian_default: caregiver
  prime_requisite: WIS
  minimum_score: 9
  starting_max_edge: 3
  kit_table: cleric_kit
  flavor: >-
    Holy symbol, war-mace, and a faith that is mostly working so far.
    The Cleric does not believe the dungeon is evil; the Cleric knows
    it. The mace is the punctuation.
  encounter_beat_choices: []
  magic_access: null

- id: thief
  display_name: Thief
  rpg_role: stealth
  jungian_default: outlaw
  prime_requisite: DEX
  minimum_score: 9
  starting_max_edge: 2
  kit_table: thief_kit
  flavor: >-
    Lockpicks, leather, and a professional interest in being elsewhere.
    The Thief assumes every door is locked, every floor is trapped,
    and every coin belongs to whoever currently has it.
```

### §2 — `equipment_tables.yaml` (extend)

Add four class-themed kit tables alongside the existing generic `weapon/armor/light/consumable/utility` slots:

```yaml
class_tables:
  fighter_kit:
    weapon: [sword_long, sword_short, mace_iron, hand_axe, spear]
    armor:  [leather_armor, shield_wood, helmet_iron]
    light:  [torch]
    consumable: [rations_day, waterskin]
    utility: [rope_hemp, ten_foot_pole, iron_spikes]
  mage_kit:
    weapon: [dagger_iron, staff_wood]   # staff_wood may need to be added to inventory.yaml
    armor:  []
    light:  [torch]
    consumable: [rations_day, waterskin, potion_healing]
    utility: [spellbook, component_pouch, chalk]
  cleric_kit:
    weapon: [mace_iron, hammer_war]     # blunt-only flavor
    armor:  [leather_armor, shield_wood]
    light:  [torch]
    consumable: [rations_day, waterskin, potion_healing]
    utility: [holy_symbol, rope_hemp, chalk]
  thief_kit:
    weapon: [dagger_iron, sword_short]
    armor:  [leather_armor]
    light:  [torch, lantern_oil]
    consumable: [rations_day, waterskin]
    utility: [lockpicks, ten_foot_pole, chalk, sack_large]
```

Any item_ids that don't yet exist in `inventory.yaml` (`staff_wood`, `spellbook`, `component_pouch`, `holy_symbol`, `lockpicks`, `hammer_war`) get added with one-line definitions in v1. The existing wiring test already enforces "every kit-table id must exist in `item_catalog`."

The `rolls_per_slot` override (3 torches, 3 consumables, 3 utility) carries forward unchanged.

### §3 — `char_creation.yaml` (modify)

Five scenes (was four). Order: **Roll → Class → Pronouns → Kit → Mouth**.

> Scene **narration copy** is content-author choice and not part of this spec. The mechanical contract below is what's load-bearing. Whoever implements this rewrites the prose freely.

**Scene 1 — stat roll** (existing, modify mechanics):
- Keep `stat_generation: roll_3d6_strict`.
- **Add** `class_qualification_loop: true`. After rolling, server computes qualifying classes; if empty, server rerolls until ≥1 class qualifies. UI sees only the final stats. (Reroll fires emit OTEL — see §5.)
- **Remove** the hardcoded `jungian_hint: hero` and `rpg_role_hint: jack_of_all_trades` defaults. Scene 2 sets them based on class choice.

**Scene 2 — class choice** (new):
- `choices` dynamically generated from `qualifying_classes(stats)`. Each generated choice carries `mechanical_effects: { class_hint: <id>, rpg_role_hint: <role>, jungian_hint: <jungian_default>, set_starting_max_edge: <int> }`. Non-qualifying classes are not shown.
- `allows_freeform: false`.

**Scene 3 — pronouns** (existing, moves to position 3). Unchanged.

**Scene 4 — kit** (existing, modify): `equipment_generation: class_kit` instead of `random_table`. The class chosen in Scene 2 selects which `class_tables.{kit_table}` rolls.

**Scene 5 — dungeon mouth** (existing). No mechanical change.

### §4 — Server wiring

Three small additions to `sidequest-server`:

1. **Class-qualification function** — pure, testable, in `sidequest/genre/` (next to existing pack loaders):
   ```python
   def qualifying_classes(stats: dict[str, int], classes: list[ClassDef]) -> list[ClassDef]:
       return [c for c in classes if stats.get(c.prime_requisite, 0) >= c.minimum_score]
   ```

2. **`set_starting_max_edge` mechanical effect** — extend the dispatch in `builder.py` to read this field and write it to the accumulator. Applied when `Character` is finalized, sets `core.edge.max` and `core.edge.current`.

3. **`equipment_generation: class_kit`** — extend the kit-rolling function to read `class_tables[chosen_class.kit_table]` instead of the top-level generic tables.

4. **Reroll loop** — Scene 1's `class_qualification_loop: true` triggers: after rolling stats, if `qualifying_classes()` is empty, reroll and re-narrate. Pure server logic; UI sees only the final stats.

### §5 — OTEL events (project rule)

Emit on each chargen run:
- `chargen.class_qualifying` — list of qualifying class ids after rolls
- `chargen.class_chosen` — the player's pick
- `chargen.class_max_edge_set` — the value applied
- `chargen.class_kit_rolled` — the resolved item ids
- `chargen.class_qualification_reroll` — fired *only* when the reroll loop trips, with the rejected stats

GM panel reads these to confirm the subsystem ran.

### §6 — Testing

- **Pack content tests**:
  - `classes.yaml` validates against a new pydantic schema in `sidequest/genre/`.
  - Every `kit_table` id resolves to a `class_tables` block.
  - Every item id in every class kit exists in `inventory.yaml.item_catalog`.
  - Every `rpg_role` in `classes.yaml` exists in `axes.yaml.rpg_roles`.

- **Qualification function unit tests**:
  - All-low rolls → empty list
  - Strong STR only → `[fighter]`
  - Strong everything → all four
  - Boundary: prime_requisite exactly 9 → qualifies; 8 → does not.

- **Chargen integration test (the wiring test)**:
  - End-to-end chargen for `caverns_and_claudes` produces a `Character` with `char_class != ""`, `core.edge.max == class.starting_max_edge`, and inventory drawn from the class kit.
  - The archetype-resolution gate (Story 45-6) passes — both `jungian_hint` and `rpg_role_hint` populated.

- **Reroll-loop test**: deterministic stats fixture forces all stats <9 on first roll, ≥9 on second; verifies Scene 1 fires twice and the final qualifying set is non-empty.

- **Manual smoke**: Playtest c&c, roll a Cleric, verify GM panel shows the five OTEL events, verify starting kit contains a holy symbol and a mace.

## Risks & Open Questions

- **`staff_wood`, `spellbook`, etc. need `inventory.yaml` entries.** Trivial. Flagged so Dev doesn't get blocked.
- **The reroll loop is silent on the wire.** Final-stats-only is the right player-facing behavior, but the OTEL event makes it visible to the GM. No tension.
- **Mage with no magic in v1 is awkward.** Acceptable — flavor carries it. Future work attaches the magic engine via `magic_access: arcane`.
- **Existing `archetype_funnels.yaml` in `caverns_sunden`** may reference the old `hero/jack_of_all_trades` default. Implementation pass should grep and confirm no funnel breaks when the default goes away.

## Out-of-scope follow-ups (for the backlog, not this story)

1. Race system (Human / Elf / Dwarf with stat mods + traits-as-narrator-hints).
2. Class-specific encounter beat choices (Fighter cleave, Thief backstab, Cleric turn-undead, Mage area-burn).
3. Mage / Cleric magic access wired to the magic system.
4. Class progression (level-up effects beyond the existing four-track progression).
