# Heavy Metal → WWN — Story 2: Classes & Chargen (Faithful Port)

**Date:** 2026-06-05
**Status:** Approved (brainstorming → spec). Story 87-2 of epic 87.
**Author:** Architect (Leonard of Quirm), with Keith
**Parent epic spec:** `docs/superpowers/specs/2026-06-04-heavy-metal-wwn-port-design.md`
**Canonical working reference:** the live `elemental_harmony` WWN binding — `genre_packs/elemental_harmony/classes.yaml` is the template this port follows.

---

## 1. Directive

> "I don't care one bit about what is there now. Don't bother 'remapping'. Just replace with the port." — Keith, 2026-06-05

This is a **wholesale replacement**, not a field-by-field translation of the existing 5e
content. Author the faithful WWN classes & chargen and replace the 5e scaffolding **everywhere
it appears** — genre tier **and** the live `evropi` world's chargen path. Nothing about the old
5e structure is preserved for its own sake. "A port is a port, not a redesign": mechanics come
from the WWN SRD and the EH binding verbatim; flavor is heavy_metal's grim idiom.

Story 1 (87-1, merged) already bound `ruleset: wwn`, the `wwn:` block, ablative-HP combat,
`magic_level: high`, and `lethality: high`. This story does **classes & chargen**. Spells are
**Story 3** — no spell content and no `cast_spell` wiring here.

## 2. Decisions (locked with Keith, 2026-06-05)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **5 classes, faithful WWN 3-chassis.** Warrior and Expert stay as the vanilla WWN chassis (grim flavor in descriptions, not renamed). The **Mage** chassis is expressed as the three epic-D1 traditions as caster classes: **Necromancer, Elementalist, Pact-born**. | Most faithful reading of epic D1 ("Warrior / Expert / Mage + Foci; Mage traditions expressed as caster classes"); least name-invention. `warrior`/`expert` ids are trivially renamable later. |
| D2 | **One signature ability per class (ADR-095); no separate Foci construct.** Abilities live in the class `abilities:` list, exactly as EH does it. | EH already collapsed WWN "Foci" into the `abilities` signature pattern. The epic's "+ Foci" is WWN-descriptive, not a mandate for a new content primitive. |
| D3 | **Story-2 casters carry `effort_sources` only** — Effort pool seeded at chargen, **no** `casts_per_day_by_level` / `max_spell_level_by_level` / `prepared_by_level` / `starting_prepared`. | Proven safe by EH's "Vowed" `martial_artist` (`magic_access: wwn` + `effort_sources`, no cast tables → `SpellcastingState` seeds as `None`). Avoids dangling spell-id references before Story 3 authors `spells_wwn.yaml`. |
| D4 | **Wholesale replace, genre + live world.** Replace 5e `class_hint`s in genre `char_creation.yaml` **and** `evropi/char_creation.yaml`; replace `power_tiers.yaml` keys; replace world `typical_classes:`. No "defer the world to Story 4." | Keith's directive; "no half-wired features" — the evropi play path must show WWN classes the moment this lands. |
| D5 | **`class_label: Calling`.** | Fits the elegiac/vocational register; player-facing on the reference page + chargen summary, the way EH uses "Discipline". |
| D6 | **Story-4 baggage stays put.** `ledger_tracking` / `pact_cost_attribution` custom_rules and the `pact_working` / `debt_collection` confrontations are **not** touched here — their retirement is epic D5 / Story 4. | Keeps this story to classes & chargen; those are dial confrontations that still load. |

## 3. The class roster (`classes.yaml`, new)

Modeled on `elemental_harmony/classes.yaml`. heavy_metal uses the **abbreviation** ability
names (`STR/DEX/CON/INT/WIS/CHA` in `rules.yaml` `ability_score_names`), so `prime_requisite`
uses the abbreviation, and caster `effort_sources.governing_attr` uses the **canonical WWN key**
(`INTELLIGENCE` / `CHARISMA`) per the `wwn.attribute_map` already in `rules.yaml`.

Required-but-inert fields follow the EH/space_opera convention: `minimum_score: 9` (point_buy
pack, no roll-minimum gate), `kit_table: <id>_kit` (descriptive placeholder — starting kit is
keyed by display_name in `inventory.yaml`, not via a class_kit path), `jungian_default`.

`encounter_beat_choices` reference the **real beat ids** from heavy_metal `rules.yaml`
confrontations as they exist after Story 1 — combat ("Blade-work"): `strike`, `brace`,
`committed_blow`, `break_contact`; negotiation ("Cold Negotiation"): `argue`,
`press_obligation`, `yield`, `withdraw`; chase ("Pursuit"): `run`, `read_the_ground`,
`cut_through`, `vanish`. **`cast_spell` is NOT added in this story** (Story 3) — no class lists
it yet.

### 3.1 Warrior chassis

**`warrior`** — display **Warrior** · role tank/dps · prime **STR** · jungian `hero`
- `warrior: true` (gates Killing Blow + Veteran's Luck dispatch seams in server `dice.py`).
- No `magic_access`, no `wwn_magic`.
- Signature ability (ADR-095): the WWN Warrior **Killing Blow** (bonus damage = half level on a
  successful strike, once/scene), reskinned in the doom idiom — "an act of completion, not rage."
  (EH's Guardian carries both Killing Blow and Veteran's Luck; one signature is the ADR-095 floor —
  the Dev/writer may author Killing Blow as the single signature and fold Veteran's Luck into its
  prose, or list both as EH did. Either is acceptable; both require `warrior: true`.)
- Grim flavor: the oath-bound blade who fights because a debt, a house, or a person stands behind
  them — "a settled absence of urgency about their own survival."

### 3.2 Expert chassis

**`expert`** — display **Expert** · role skirmisher/support · prime **DEX** · jungian `explorer`
- No magic. No `warrior` flag.
- Signature ability: a "read the situation" expertise beat — once/confrontation, identify an
  exploitable tag / weakness (the next strike on that tag resolves at advantage), mirroring EH's
  Scholar "Lore Advantage". Reskinned: reading the ledger of a fight the way others read a face.
- Grim flavor: the strata-walker / reckoner who has been into the old ruins and the older
  accounts and come back — competence earned, not inherited.

### 3.3 Mage chassis — three caster traditions

All three: `magic_access: wwn`; `wwn_magic.effort_sources` **only** (D3); `partial: false`.
Effort `relevant_skill` + `starting_skill_level: 1` per the EH caster shape. No cast tables.

**`necromancer`** — display **Necromancer** · role control · prime **INT** · jungian `magician`
- `effort_sources: [{ source: necromancer, governing_attr: INTELLIGENCE, relevant_skill: Magic, starting_skill_level: 1 }]`
- Signature ability: an Effort-spend control/dread effect (decay, the unquiet dead, the ledger of
  the unpaid). Story-2 mechanics are Effort-gated, not spell-gated.
- Flavor: magic as the accounting of death — what the body owes, collected early.

**`elementalist`** — display **Elementalist** · role striker · prime **INT** · jungian `artist`
- `effort_sources: [{ source: elementalist, governing_attr: INTELLIGENCE, relevant_skill: Magic, starting_skill_level: 1 }]`
- Signature ability: an Effort-spend damage/forge effect (fire, slag, stone) — the guild-quarter
  trade whose craft scars the craftsman.
- Flavor: the daylight workings of the forge cities, paid for in burns and residue.

**`pact_born`** — display **Pact-born** · role dps/control · prime **CHA** · jungian `outlaw`
- `effort_sources: [{ source: pact_born, governing_attr: CHARISMA, relevant_skill: Magic, starting_skill_level: 1 }]`
  — governing_attr `CHARISMA` (the bargain) is a deliberate divergence from the Arcane-INT
  traditions; **tunable in Story 3** if the spell math wants INT. Decided now because Effort is
  seeded at chargen.
- Signature ability: an Effort-spend covenant effect — power bargained, not learned (the Crimson
  Gods, inherited covenants). The monkey's-paw cost is carried in narration/System Strain, not a
  bespoke ledger.
- Flavor: the warlock whose pact has become their public identity.

## 4. File changes (replacement list)

`classes.yaml` ids are the **single source of truth**. Every reference below uses those exact
display names / ids. Reference-page anchors derive from `name`/`label` via slugify
(content CLAUDE.md) — name stability = anchor stability, so author once, reference consistently.

### 4.1 `genre_packs/heavy_metal/classes.yaml` — **new file**
Author the 5 classes per §3, EH-shaped. Include the file-level header comment documenting:
prime_requisite uses abbreviations; caster `governing_attr` uses canonical WWN keys; `cast_spell`
is excluded until Story 3; required-but-inert fields per space_opera convention.

### 4.2 `genre_packs/heavy_metal/rules.yaml`
- **Drop** `allowed_classes` (5e 12-list), `allowed_races` (5e `Human/Dwarf/Elf/Halfling`),
  `banned_spells` (the entire 5e spell-ban list — WWN gates spell access by class spell list in
  Story 3, not a ban list). Genre `cultures.yaml` is `[]` (cultures are world-tier), so genre
  `allowed_races` has nothing legitimate to hold — it goes.
- **Replace** `default_class: Fighter` → `default_class: warrior`. **Drop** `default_race: Human`
  (races are world-tier; the reference/chargen frame falls back cleanly on the `or []` paths in
  `reference_presenters.py` / `chargen_summary.py`).
- **Add** `class_label: Calling`.
- **Leave** `custom_rules` (`ledger_tracking`, `pact_cost_attribution`, `rest_variant`,
  `injuries`, `death_saves`, …), the `wwn:` block, and the `pact_working` / `debt_collection`
  confrontations **untouched** — Story 4 (D6).

### 4.3 `genre_packs/heavy_metal/char_creation.yaml` (genre, crucible scene)
Replace the five `class_hint`s (`Paladin/Warlock/Cleric/Wizard/Fighter`) with the new ids.
Suggested mapping (writer may adjust; each choice keeps its existing flavor prose):
- "A covenant inherited" → `warrior` · "A pact of your own making" → `pact_born` ·
  "A tithe you were born into" → `necromancer` (the feeding/tithe-priest reads as death-accounting)
  · "A craft that costs the craftsman" → `elementalist` · "A refusal, quietly maintained" →
  `expert`.

### 4.4 `genre_packs/heavy_metal/worlds/evropi/char_creation.yaml` (crucible scene) — **live path**
Replace the six `class_hint`s (`Fighter/Rogue/Cleric/Warlock/Wizard/Monk`) with the new ids
(many-to-one is fine): Mistos-blade → `warrior` · Waz-court intrigue → `expert` · Njörkte healing
→ `necromancer` · Crimson God bargain → `pact_born` · the mis-copied Book → `necromancer` or
`elementalist` (writer's call) · the long refusal → `expert`.

### 4.5 `genre_packs/heavy_metal/power_tiers.yaml`
Replace the **12 5e-class-keyed** blocks (`Fighter/Ranger/Rogue/Cleric/Druid/Bard/Barbarian/
Monk/Wizard/Warlock/Sorcerer/Paladin`) with **5 blocks** keyed by the new display names
(`Warrior`, `Expert`, `Necromancer`, `Elementalist`, `Pact-born`). Author fresh grim per-tier
visual descriptions in the existing baroque-elegy voice (the file's purpose is per-class,
per-tier visual flavor for portrait/power-tier rendering). The five keys **must** match the
`classes.yaml` display names exactly.

### 4.6 World `typical_classes:` lists
- `worlds/evropi/archetypes.yaml` (8 archetypes) and `worlds/long_foundry/archetypes.yaml`
  (7 archetypes): replace 5e class names in `typical_classes:` with the new ids/display names.

### 4.7 No-ops (verify, do not edit)
- `genre_packs/heavy_metal/archetypes.yaml` is `[]` (archetypes are world-tier) — untouched.
- `genre_packs/heavy_metal/archetype_constraints.yaml` references only Jungian × rpg_role pairs,
  **no 5e class names** (grep hits were prose substrings) — untouched.

## 5. Engine / test impact (sidequest-server)

**No engine changes.** This is content. But the suite must stay green and prove wiring:

- **Wiring is the gate, not validation.** Per the project's standing lesson, `validate pack`
  passing is **not** proof a pack loads — run `load_genre_pack` for heavy_metal and confirm the
  5 classes parse, `magic_access: wwn` casters seed an Effort pool with **no** `SpellcastingState`
  (EH-vowed behavior), and chargen resolves `default_class: warrior`.
- **Chargen integration:** at least one test driving chargen for heavy_metal to a built
  character per class — confirming `class_label` ("Calling"), the `class_hint`→class resolution
  for both the genre and `evropi` crucible scenes, and (for a caster) a seeded Effort pool.
- **No-dangling-refs check:** assert no `class_hint` / `typical_classes` / `power_tiers` key
  references a class id absent from `classes.yaml` (the consistency contract, §4). A small
  cross-file test prevents the reference-page anchor breakage content CLAUDE.md warns about.
- **Full-suite baseline:** gate on the FULL suite with `SIDEQUEST_DATABASE_URL` +
  `SIDEQUEST_GENRE_PACKS` set; record the baseline failure list first. Story 1's `hp_depletion`
  migration already settled `test_heavy_metal_pack_loads_with_dual_dial_schema`; no new
  calibration migration is expected here, but any new failure must be checked against the baseline,
  not assumed pre-existing.

## 6. Non-goals
- **No spells, no `cast_spell` wiring, no `spells_wwn.yaml`** (Story 3). Casters are Effort-only.
- **No retirement** of `pact_working` / `debt_collection` confrontations or `ledger_tracking` /
  `pact_cost_attribution` custom rules (Story 4).
- **No engine/Python changes** beyond tests. No new UI. No asset work.
- No `long_foundry` portrait rendering (still pending; out of scope).

## 7. Risks
- **Cross-file id drift** — the 5 ids appear in `classes.yaml`, `rules.yaml`, two
  `char_creation.yaml` files, `power_tiers.yaml`, and two world archetype files. A typo silently
  breaks a `class_hint` resolution or a reference anchor. Mitigation: the §5 consistency-contract
  test.
- **Caster-without-spells reads as inert** — a player picking Necromancer in Story 2 gets Effort
  but no spells. Acceptable and expected (story title: "No spells yet"); the narrator should not
  imply castable spells. Flag in the class `flavor` that the working is bargained/Effort-paid, not
  a spell list, so the Story-2 state isn't a lie.
- **power_tiers rewrite is the bulk of the prose** — 12 blocks → 5, fresh per-tier visuals. Largest
  single chunk; it is flavor-only (no mechanics), so low-risk but writer-heavy.
- **`pact_born` governing_attr (CHA)** — seeded at chargen now; if Story 3's spell math wants INT,
  re-seeding existing saves is a migration. Flagged as tunable; CHA chosen deliberately for the
  bargain idiom.
