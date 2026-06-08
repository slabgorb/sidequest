# Heavy Metal → Worlds Without Number: Faithful Ruleset Port

**Date:** 2026-06-04
**Status:** Draft (brainstorming) — epic-level design; Story 1 specified for implementation
**Author:** GM (Game Master)
**Sources of truth (faithful port, do not redesign):**
- Worlds Without Number SRD 1.0 — *Combat*, *Saving Throws*, *Damage & Healing*, *High Magic / Arts & Effort*
- Stars Without Number: Revised (Free Edition) — shared WN lethality chassis (Shock / Trauma / Mortal Injury), reference only
- **The live `elemental_harmony` WWN binding is the canonical working reference** — it is the first
  WWN pack and proves the entire engine path (`ruleset: wwn` + `wwn:` block, `cast_spell` beats,
  `spells_wwn.yaml`, `hp_depletion`, the downed seam). This port follows it.

---

## 1. Problem

`heavy_metal` runs the **`native` dial engine** (no `ruleset:` line). Its combat and magic are
**prose content with no mechanical backing** — the narrator improvises both, and no
`confrontation.*` / `wwn.*` spans fire in real play because no confrontation is bound to a
ruleset that uses them. This is exactly the failure mode the GM panel exists to catch.

Two further problems are specific to this pack:

1. **5e leftover content.** `rules.yaml` carries a D&D-5e class list (Fighter/Wizard/Warlock/
   Paladin/…), 5e races, and a 5e banned-spell list (Wish, Meteor Swarm, Power Word Kill, …).
   This is placeholder scaffolding that does not match the pack's authored voice and fights the
   WWN port.
2. **Over-flavored bespoke magic.** The pack's signature magic ("magic is never studied and
   cast — it is bargained for, inherited, or paid for in blood, soul, and flesh") was modeled as
   bespoke `ritual` and `debt_collection` confrontations plus `ledger_tracking` /
   `pact_cost_attribution` custom rules. Per Keith (2026-06-04) this framing **shades too hard
   into flavor** and is being **retired** in favor of the port.

The engine substrate is already complete. Unlike road_warrior → CWN (which needed a net-new
crew-seat primitive for the War Rig), heavy_metal → WWN requires **zero engine changes** — the
`elemental_harmony` binding already exercises every seam. This is the "Don't Reinvent — Wire Up
What Exists" principle: a **content port plus the standard calibration/OTEL wiring**.

## 2. Goal

Bind `heavy_metal` to the `wwn` ruleset as the **second WWN pack after `elemental_harmony`**, a
faithful SRD port:

- **Combat** — WWN personal combat: attack-vs-AC on the ablative `HpPool` (`win_condition:
  hp_depletion`), with the SWN-family lethality layer (Shock / Trauma / Mortal Injury / Major
  Injury) live via the `wwn` module.
- **Magic** — WWN High Magic: prepared spells cast against committed **Effort**, with **System
  Strain** as the body's running toll. Authored fresh in heavy_metal's grim idiom.
- **The doom/baroque identity survives in spell descriptions and narration**, not in a bespoke
  mechanical subsystem. The *feeling* that "every spell costs" is carried by WWN Effort + System
  Strain + grotesque spell-description flavor — not by a ledger.

## 3. Decisions (locked with Keith, 2026-06-04)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Faithful WWN 3-chassis** — Warrior / Expert / Mage + Foci; dark-fantasy flavor in descriptions. Mage "traditions" (necromancer, elementalist, pact-born, …) expressed as caster classes whose `cast_spell` pulls a themed spell list. | "A port is a port." Closest to WWN; the live mage traditions (esp. necromancy) are perfectly on-theme for doom fantasy. |
| D2 | **`magic_level: high`** (was `medium`) | Spells are central to the genre; matches the `elemental_harmony` precedent. |
| D3 | **Standard six, already present** (STR/DEX/CON/INT/WIS/CHA in `rules.yaml`). CHA is **engine-mandatory** (half the WWN **Mental save**, best-of WIS/CHA; the defender-save path fails loud without it), so it **stays** despite being a placeholder originally. **A complete `wwn.attribute_map` IS required** — the `wwn` validator (`rules.py:_validate_wwn`) raises without all six canonical keys (STRENGTH/CONSTITUTION/DEXTERITY/INTELLIGENCE/WISDOM/CHARISMA), each mapping to a declared `ability_score_names` entry. Because the stats are the standard abbreviations, the map is canonical→abbreviation: `STRENGTH: STR`, …, `CHARISMA: CHA`. (My earlier "no attribute_map" was wrong — verified against the validator.) | The save / gunnery / strain paths translate canonical SWN keys through `attribute_map`; it is mandatory, not optional. |
| D4 | **`lethality: high`**; `hp_depletion` + Trauma / Mortal Injury. **Remove the `edge_config` block** (heavy_metal currently runs ADR-078 Edge/Composure as its HP replacement) — under WWN the combatant is an ablative-HP character. This is the exact road_warrior D2 move (Edge → ablative HP). | `gritty_realism` rest, `lingering` injuries, `hard` death saves, "every empire is ending" — the WWN lethality layer is a glove fit; one combat model engine-wide. |
| D5 | **Retire the pact/ledger magic framing.** The `ritual` confrontation is replaced by WWN `cast_spell`; the `debt_collection` confrontation is **cut**; `ledger_tracking` / `pact_cost_attribution` custom rules drop. | Keith: the framing shades too hard into flavor — replace it with the port. |
| D6 | **Faithful SRD port, not a redesign.** Mechanics are lifted from the WWN SRD and the EH binding verbatim, not reinvented. | road_warrior precedent. |

## 4. Source mechanics (extracted, so the implementer need not re-read the SRD)

The `elemental_harmony` `rules.yaml` `wwn:` block is the authoritative encoding of these; the
extraction below explains *what each knob means* so heavy_metal's values are deliberate, not
copy-pasted.

### 4.1 Personal combat (WWN)
- Attack: `d20 + attack bonus + better(relevant modifier) + combat skill` vs target **ascending
  AC**. Hit → roll damage; **Shock** damage may apply on a miss for melee weapons vs low-AC foes.
- HP is the ablative pool; `win_condition: hp_depletion`. At ≤ 0 HP the **downed seam** fires
  (`run_cwn_wwn_downed_seam`, already gated for `cwn`/`wwn`): a Physical save vs Mortal Injury.
- **Saving throws** (3 categories, roll-high vs a level/attribute-derived target):
  - **Physical** = best of STR/CON · **Evasion** = best of DEX/INT · **Mental** = best of WIS/CHA.
  - The SWN module **fails loud** on a missing save attribute (no neutral-10 fallback). Every
    `opponent_default_stats` block MUST carry **all six** ability scores.
- **Trauma / Mortal Injury** layer (copied from CWN by the SWN-family module): `default_trauma_target`,
  `mortal_injury_rounds`, `major_injury_save`. EH uses `6 / 6 / physical`; heavy_metal's higher
  lethality may tune these (Keith's crunch call during Story 1).

### 4.2 System Strain (WWN)
- A running bodily toll, `max_source: CONSTITUTION`. Spent by healing, certain magic, and
  hardship; recovered slowly (`rest_recovery_per_night`). `first_aid_cost` is the strain price of
  stabilizing. This is the mechanical home for "magic costs the body."

### 4.3 High Magic / Effort (WWN)
- Mages **prepare** spells and cast against committed **Effort** (a pool reclaimed on rest;
  `day_reclaim_requires_comfort` gates the daily reclaim on a safe rest). `effort_base` sets the
  baseline pool; `killing_blow_divisor` governs the lethal-cast rider; `default_spell_save: mental`.
- The `cast_spell` beat (a combat beat with `class_filter` to caster classes) is the runtime
  entry point; `spells_wwn.yaml` is the spell content. Without `class_filter`, the cast resource
  gate never fires (the beat is offered to non-casters and the gate is skipped).

### 4.4 The mapping

| WWN source | heavy_metal |
|---|---|
| Warrior / Expert / Mage chassis + Foci | the class set (D1) |
| Mage traditions / spell lists | necromancer / elementalist / pact-born caster classes, themed `spells_wwn.yaml` lists |
| Ablative HP + Trauma/Mortal Injury | the lethality of a dying world (D4) |
| Effort + System Strain | "every spell costs" — the toll the body and the day pay |
| Mental save (WIS/CHA) | the sixth attribute, engine-mandatory (D3) |
| `cast_spell` beat | replaces the retired `ritual` confrontation (D5) |

## 5. Epic decomposition (single epic — no deferred special subsystem)

Because there is **no net-new engine primitive**, this is a single content-port epic of ~4
stories, ordered by dependency. Story 1 is specified in §6; the rest are scoped here and get
their own specs when reached. Each story is its own plan → PR cycle.

- **Story 1 — WWN binding + combat foundation** *(this spec, §6; de-risking)*. `ruleset: wwn`;
  standard six (add CHA); `magic_level: high`; `lethality: high`; a `combat` confrontation with
  `win_condition: hp_depletion` + a complete `opponent_default_stats` block; calibration
  migration; wiring-checklist **verify** + OTEL span-assertion test. Mirrors road_warrior Plan 1.
- **Story 2 — Classes & chargen.** Author `classes.yaml` (Warrior/Expert/Mage + Foci, grim
  flavor); remap `archetypes.yaml` / `char_creation.yaml` / `power_tiers.yaml` /
  `archetype_constraints.yaml` off the 5e names; drop the 5e `allowed_classes` / `allowed_races` /
  `banned_spells` from `rules.yaml`.
- **Story 3 — Magic content.** Author `spells_wwn.yaml` in heavy_metal's idiom (costly,
  grotesque, doom-soaked — this is where the retired ledger flavor is re-homed); wire `cast_spell`
  beats with `class_filter` to the caster classes; finalize the `wwn.magic` config.
- **Story 4 — Content sweep + calibration + OTEL playtest.** Remove the `ritual` /
  `debt_collection` confrontations and the `ledger_tracking` / `pact_cost_attribution` custom
  rules; exhaustive 5e-baggage sweep across all content files; full-suite calibration; OTEL
  playtest pass across both worlds (`evropi`, `long_foundry`).

## 6. Story 1 — WWN binding + combat foundation (implementable)

**Repos:** `sidequest-content` (heavy_metal YAML) + `sidequest-server` (calibration tests / wiring
verify). **Pattern precedent:** `elemental_harmony`→WWN (the live first binding) and the
road_warrior→CWN Plan 1 (#658 epic).

### 6.1 Content changes — `genre_packs/heavy_metal/rules.yaml`
- Add `ruleset: wwn`.
- Add the `wwn:` block with a **complete `attribute_map`** (required — see D3): canonical→
  abbreviation (`STRENGTH: STR`, `DEXTERITY: DEX`, `CONSTITUTION: CON`, `INTELLIGENCE: INT`,
  `WISDOM: WIS`, `CHARISMA: CHA`). Author `system_strain` (`max_source: CONSTITUTION` — a canonical
  *key* of the map, not `CON`), `trauma`, and `magic` sub-blocks. Start from the EH values
  (`trauma: 6 / 6 / physical`; `magic` effort_base 1, killing_blow_divisor 2,
  day_reclaim_requires_comfort true, default_spell_save mental); `trauma`/lethality tuning is
  Keith's crunch call.
- `ability_score_names` is **already** `STR, DEX, CON, INT, WIS, CHA` — leave it unchanged.
- **Remove the `edge_config` block** (ADR-078 Edge/Composure) — the combatant becomes an
  ablative-HP WWN character (D4). Also remove `display_fields` that reference `edge`/`max_edge`/
  `composure_state`.
- `magic_level: high` (was `medium`).
- Set `lethality: high`.
- **Convert the existing `combat` confrontation ("Blade-work")** from
  `resolution_mode: opposed_check` + momentum dials to `resolution_mode: beat_selection` +
  `win_condition: hp_depletion`. Replace its `opponent_default_stats` (currently `STR/DEX/CON: 12`,
  the pre-calibration parity number) with a block carrying **all six** ability scores (≤ 10) **plus**
  the reserved seed keys `hp`, `armor_class`, `dexterity` (initiative). Keep the existing
  strike/brace/push beats; drop the now-unused `player_metric`/`opponent_metric`. The `cast_spell`
  beat is added in Story 3.
- Leave the `negotiation` ("Cold Negotiation") and `chase` ("Pursuit") dial confrontations in
  place — they are generic and survive (mirrors EH keeping negotiation + chase).
- Leave the bespoke `pact_working` ("Working the Rite") + `debt_collection` ("The Collector at the
  Door") confrontations and the `ledger_tracking` / `pact_cost_attribution` custom rules in place
  for Story 1 (they are dial confrontations that pass the migrated load test); their full
  retirement is **Story 4**. Flag clearly — no silent implication of mechanical backing.

### 6.2 Engine changes — `sidequest-server`
- **No new module.** `wwn` already exists and is wired (EH). Confirm `heavy_metal` loads through
  `get_ruleset_module("wwn")` (fail-loud at load).
- Apply the **Without-Number module wiring checklist** as a **verify** (not rebuild) — the seams
  are already `wwn`-aware from the EH/WWN Plan 1 work: spans `__init__` re-export includes `wwn`;
  `dice.py` downed seam + `_physical_save_target_for` already cover `wwn` (`downed_seam.py`
  `run_cwn_wwn_downed_seam` gates on `ruleset in ("cwn","wwn")`); OTEL span-assertion tests exist
  for the `wwn.*` lethality spans.
- **Calibration migration** (documented trap, narrower than road_warrior's): heavy_metal is **not**
  in `COMBAT_PACKS` or `SHIPPED_PACKS` (`tests/genre/test_confrontation_calibration.py`), so there
  is **nothing to drop there**. The **only** test that migrates is
  `test_heavy_metal_pack_loads_with_dual_dial_schema` (`tests/genre/test_pack_load.py:44`): once the
  combat confrontation is metricless `hp_depletion`, the unconditional `player_metric.threshold`
  loop NPEs on it. Fix it to the EH/space_opera shape — filter to
  `win_condition == "dial_threshold"` confrontations and assert at least one remains. **Do not**
  treat this as a pre-existing failure.

### 6.3 OTEL / wiring test (mandatory — the GM panel is the lie detector)
- Seed a heavy_metal combat encounter; run a turn through narrator context build; assert the
  `wwn` personal-combat spans fire (attack resolution, Shock/Trauma) and HP depletes on the
  ablative pool — not improvised prose.
- At least one integration test proving the bound ruleset is reachable from a production turn
  path, not just unit-tested in isolation.

## 7. Non-goals (Story 1)
- No class authoring (Story 2), no spell content / `cast_spell` wiring (Story 3), no bespoke-
  confrontation removal or full 5e sweep (Story 4). Story 1 stops at: a working WWN pack with
  ablative-HP combat, the standard six, high lethality, and a clean foundation.
- **No engine changes** beyond calibration-test migration and wiring verification — this port
  adds no new Python primitives.
- No new UI. No asset work (`long_foundry` portraits remain pending; out of scope).

## 8. Risks
- **5e-baggage sweep breadth** (Story 4) — classes, races, banned-spells, and any 5e stat
  references must be swept exhaustively or the narrator references dead content. Larger surface
  than a pure `ruleset:` flip.
- **Calibration-test false alarms** — the `hp_depletion` migration regresses two tests **by
  design**; easy to misread as a regression. Gate on the FULL suite with `SIDEQUEST_DATABASE_URL`
  + `SIDEQUEST_GENRE_PACKS` set; record the baseline failure list first.
- **Flavor loss** — retiring the gorgeous `ritual` / `debt_collection` prose. Mitigation: re-home
  its voice into spell descriptions and narrator hints (Story 3) so the doom-cost *feeling*
  survives even though the mechanics are vanilla WWN Effort / System Strain.
- **Second-pack assumptions** — the EH binding is the only prior WWN pack, and EH uses *flavor*
  ability names (Strength/Agility/…) so its `attribute_map` values differ from its keys.
  heavy_metal uses the *abbreviations* (STR/DEX/…), so its map is canonical→abbreviation
  (`CONSTITUTION: CON`). Verified against `_validate_wwn`: this is well-formed (values must be in
  `ability_score_names`; `max_source` must be a canonical *key*). This is the one structural way
  heavy_metal differs from EH — the wiring/load test must exercise it on the real pack.
