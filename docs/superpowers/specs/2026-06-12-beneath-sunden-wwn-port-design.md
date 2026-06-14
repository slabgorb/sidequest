# Beneath Sünden WWN Port — Design

**Date:** 2026-06-12
**Status:** Approved (brainstorm with Keith, 2026-06-12) — **PARTIALLY SUPERSEDED 2026-06-14 by ADR-143 (combat model).**
**Repos:** sidequest-content (primary), sidequest-server (integration test only)

> **⛔ CORRECTION (2026-06-14, ADR-143 + gm-decisions.md).** This doc's combat
> section (§2) tells you to keep `resolution_mode: beat_selection` and layer WWN
> resolution on top of the native beat shape (copying `heavy_metal` "Blade-work").
> **That is the native/WWN hybrid Keith ruled a DEAD END.** WWN combat does **not**
> use `beat_selection`, native beats, `edge_config`, Brace, or the per-beat
> auto-reprisal. Under a WWN binding, combat resolves through the Without Number
> initiative-round engine (`wn_round.py`); the native beat scaffolding is **removed,
> not balanced.** We bind WWN so we don't have to balance. Read **ADR-143** before
> touching WWN combat content. The rest of this doc (procedural dungeon, classes,
> magic, bestiary, dial chase/negotiation) stands.

## Goal

Port the `caverns_and_claudes` pack — whose only world is `beneath_sunden` — from
the native dial/confrontation engine to the **WWN (Worlds Without Number) SRD
ruleset**. The product goal is exactly two things:

1. **A procedural, forever dungeon** — the ADR-106 Sünden Deep runtime
   megadungeon, which is unique in SideQuest and is the star of this pack.
2. **The WWN SRD ruleset** as the resolution layer beneath it.

Nothing else is sacred. Flavor (lore, class prose, tone copy) was written to
support the old B/X stopgap mechanics and **gets rewritten wherever it
conflicts with WWN** — flavor follows mechanics here, not the other way
around.

## Non-Goals

- **No new balancing.** Every class chassis, signature ability, spell catalog,
  and lethality dial is **copied from the already-balanced WWN packs**
  (`heavy_metal`, `elemental_harmony`) and re-flavored. WWN's published math is
  the math. If a design choice would require tuning numbers, it's the wrong
  choice.
- **No changes to the procedural dungeon engine.** ADR-106 expansion,
  Complication Ledger, room templates, and cartography are untouched. WWN
  becomes the resolution layer; the dungeon generator is not modified.
- **No server-side ruleset code.** `WwnRulesetModule`
  (`sidequest-server/sidequest/game/ruleset/wwn.py`) is production-live with
  two packs bound to it. This is a **content port** — per the Jade doctrine,
  if the port required engine changes, that would be a failure of the content
  surface.

## Precedent

The **heavy_metal WWN port (story 87-2)** is the exact template. It converted a
fantasy pack from native dials to WWN and its files show the full shape:
`rules.yaml` wwn block, 3-chassis `classes.yaml`, `spells_wwn.yaml`, WWN combat
confrontation, dial chase/negotiation retained, dial scaffolding dropped.
`elemental_harmony` is the secondary reference (first WWN binding, integration
test exemplar).

## Current State (what changes from)

`caverns_and_claudes/rules.yaml` today: B/X stopgap — `roll_3d6_strict`,
Fighter/Mage/Cleric/Thief, `magic_level: none` (with a draft note admitting the
flag is misleading), opposed-check combat on momentum dials, `edge_config`,
`morale` block. `magic.yaml` carries the 2026-05-07 B/X pivot
(`innate_v1`/`learned_v1` spell-slot plugins + `item_legacy_v1`).

**Key discovery:** `beneath_sunden/bestiary.yaml` is **already authored in the
WWN generic stat-line format** (level==HD, hp==4.5/HD, ascending
`armor_class`, `attack_bonus`, `damage`, `morale` 2d12, `skill`,
`save` 15−⌊level/2⌋) — byte-compatible with what `heavy_metal/barsoom` uses for
live WWN combat. The largest content surface needs essentially no rework; only
its header comment ("native dial engine") is stale.

## Design

### 1. rules.yaml

- `ruleset: wwn` + full `wwn:` config block **copied from heavy_metal**:
  - `attribute_map`: identity (STRENGTH→STR … CHARISMA→CHA; pack already uses
    standard abbreviations).
  - `system_strain`: `max_source: CONSTITUTION`, `rest_recovery_per_night: 1`,
    `first_aid_cost: 1`.
  - `trauma`: `default_trauma_target: 6`, `mortal_injury_rounds: 6`,
    `major_injury_save: physical`.
  - `magic`: `effort_base: 1`, `killing_blow_divisor: 2`,
    `day_reclaim_requires_comfort: true`, `default_spell_save: mental`.
- `stat_generation: point_buy`, `point_buy_budget: 27` (heavy_metal value),
  `lethality: high`.
- `allowed_classes: [Warrior, Expert, Mage]` (required — encountergen's
  humanoid-enemy path exits 1 without it; keep in sync with classes.yaml
  display names). `default_class: Warrior` (display name, per the
  chargen-builder display_name resolution). `class_label: Calling`.
- Drop B/X scaffolding: `allowed_races` / `default_race` / `banned_spells`
  (races are world-tier; WWN gates spells by class list, per the 87-2
  precedent), `magic_level` draft flag resolved by the port.
- Keep: `stat_display_fields` (torches/rations/encumbrance/gold — the crawl
  resource loop is orthogonal to the ruleset), `custom_rules` resource ticks /
  extraction phase / strict encumbrance, `encounter_base_tension`,
  `initiative_rules`, `default_location` / `default_time_of_day`.

### 2. Combat confrontation → WWN

> **⛔ SUPERSEDED 2026-06-14 by ADR-143.** Everything below in this subsection
> describes the native/WWN **hybrid** (`beat_selection` + native beats + Brace +
> `edge_config` + per-beat reprisal with WWN math layered on). Keith ruled that hybrid
> a **dead end** — we bind WWN to stop balancing, not to balance native against it.
> WWN combat resolves through the Without Number initiative-round engine
> (`wn_round.py`); there is **no `beat_selection` combat def, no native beat list, no
> Brace, no `edge_config`.** Do **not** author the shape below. (The `opponent_damage`
> DamageSpec requirement — ADR-139 Invariant 3 — and the "chase/negotiation stay dial"
> rule do carry forward.) See ADR-143 and gm-decisions.md (2026-06-14).

Replace the dial combat def with the heavy_metal Blade-work shape:

- `resolution_mode: beat_selection`, `win_condition: hp_depletion`.
- `opponent_default_stats`: **all six** ability scores (10s) + reserved seed
  keys `hp`, `armor_class`, `dexterity` — the SWN defender-save path KeyErrors
  on a missing attribute, so the block must be complete.
- `opponent_damage: {dice: "1d8", bonus: 0}` — required or the seeded Other is
  toothless (playtest #16 / ADR-139 Invariant 3 class of bug).
- Beats: strike / brace / committed_blow / break_contact pattern with
  `attack_bonus` / `combat_skill` / `damage_channel`, plus `cast_spell`
  (`damage_channel: none`, `class_filter: [Mage]` — the class_filter is the
  ONLY gate that offers it, so the WWN cast resource gate fires; cast_spell is
  NOT listed in any class's `encounter_beat_choices`). Keep `intent_verbs` /
  `on_intent_mismatch` from the current defs. Beat flavor rewritten for the
  grave dwarfhold register.
- **Chase and negotiation stay dial confrontations** (player_metric /
  opponent_metric), exactly as heavy_metal kept them — they are not
  WWN-specific. Beat lists may be trimmed/re-flavored but their resolution
  model is unchanged.
- **Drop**: `edge_config`, combat `momentum` metrics, the `morale:` block on
  the combat def (WWN lethality + bestiary per-creature `morale` replace it).

### 3. classes.yaml (new file)

The three WWN SRD chassis, **copied from heavy_metal / elemental_harmony and
re-flavored only**:

- **Warrior** — heavy_metal Warrior verbatim mechanics: `warrior: true`
  (gates Killing Blow + Veteran's Luck dispatch seams in dice.py),
  `prime_requisite: STR`, B/X saving_throws table, ADR-095 signature-ability
  pair.
- **Expert** — the Expert chassis (skill specialist), `prime_requisite: DEX`
  or `INT` per the source chassis — whichever the copied definition carries;
  do not retune.
- **Mage** — a single caster Calling carrying **full `wwn_magic`** (Effort
  sources with canonical-key `governing_attr: INTELLIGENCE`, cast tables,
  `starting_prepared`) wired to a reused spell catalog (§4). Real WWN
  High-Magic, not Effort-only, per the heavy_metal 2026-06-05 amendment.
- Required-but-inert fields per convention: `minimum_score: 9`, `kit_table`
  placeholders, `jungian_default`.
- `encounter_beat_choices` reference real beat IDs from the new rules.yaml
  confrontations (combat + chase + negotiation lists).
- All flavor prose rewritten for Beneath Sünden's register; mechanics fields
  byte-faithful to the source chassis.

### 4. Magic: spells_wwn.yaml + magic.yaml

- **spells_wwn.yaml (new):** copy heavy_metal's WWN spell catalog and
  re-flavor names/prose where the source flavor is pack-specific. No new
  spells, no level/effect changes — the catalog is the balanced artifact being
  reused.
- **magic.yaml:** rewrite for the WWN posture. `wwn_magic` (via classes) is
  the player casting surface; **item magic stays** (`item_legacy_v1` —
  scrolls, potions, wands, cursed relics are core crawl loot). The B/X
  `innate_v1` / `learned_v1` spell-slot plugins are retired with the rest of
  the B/X stopgap. Hard limits (no_resurrection etc.) are reviewed against
  the reused spell catalog: any catalog spell that violates a limit is
  resolved by **dropping the limit or excluding the spell — Keith's call at
  implementation time, flagged in the story**, never by rebalancing the spell.

### 5. char_creation.yaml

Point the chargen surface at the three Callings (display names matching
classes.yaml), point-buy flow, `class_label: Calling`. Any class_hint /
crucible paths must resolve to real display names (no-id-fallback rule).

### 6. bestiary.yaml / creatures.yaml

Near-zero mechanical work: verify every entry carries the WWN stat-line fields
(level, hp, armor_class, attack_bonus, damage, morale, skill, save) — they
already do — and update the stale "native dial engine" header comment to name
the wwn ruleset module. Capstone linkage, world_register genre-truth gate, and
the cookbook RACE factions are unchanged.

### 7. Flavor pass

Lore/tone copy is rewritten **only where it contradicts WWN mechanics** (e.g.
"no caster classes" claims in magic.yaml comments, folkloric-knowledge framing
that denies a player Mage exists). The grave Moria-as-tragedy register itself
is kept — it happens to suit `lethality: high`, but it is a consequence of the
port, not a constraint on it.

### 8. Wiring proof (sidequest-server, test-only)

Adapt `tests/integration/test_wwn_elemental_harmony_dispatch.py` to
caverns_and_claudes: real pack load, real chargen for a Warrior and a Mage,
real combat dispatch through `_apply_narration_result_to_snapshot`, asserting:

- the `wwn.spell.cast` OTEL span fires when a Mage `cast_spell` beat resolves,
- `state_patch_hp` spans fire on HP deltas,
- pack load resolves `ruleset: wwn` through the registry (fail-loud on typo).

Pack validator (`sidequest validate` CLI) must pass clean. Per the
no-content-in-unit-tests rule, content invariants (all classes declare
encounter_beat_choices, spell ids resolve) belong to the validator, not pytest.

## Story Decomposition (~3 stories)

1. **rules.yaml port** — ruleset binding, wwn config block, WWN combat
   confrontation, drop dial scaffolding, point-buy. Validator green.
2. **Classes + magic** — classes.yaml (3 chassis), spells_wwn.yaml,
   magic.yaml rewrite, char_creation.yaml. Validator green.
3. **Bestiary verify + wiring proof** — bestiary header/field audit,
   integration test in sidequest-server, headless playtest smoke of a combat
   in the Deep.

Stories 1–2 are content-repo (`sidequest-content`, base `develop`); story 3
spans content + server (server base `develop`).

## Risks

- **Chargen display-name coupling:** `default_class` and `class_filter`
  resolve by display_name with no id fallback — a mismatch silently yields a
  classless character. Mitigation: validator + the wiring test exercise both.
- **Incomplete opponent stat blocks KeyError** in the SWN save path —
  mitigated by authoring all six abilities per the heavy_metal comment.
- **Spell catalog vs world hard-limits** (no_resurrection etc.) — resolution
  rule defined in §4; surfaced as an explicit checklist item in story 2.
