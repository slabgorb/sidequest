# WWN Content Binding + End-to-End Wiring Plan (Plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the merged WWN magic engine **reachable from real play** and bind it to a real pack. This plan (a) authors the full `elemental_harmony` → `wwn` content binding (rules / inventory / classes / char-creation / a net-new WWN spell catalog), (b) wires the `cast_spell` beat to `WwnRulesetModule.resolve_spellcast` behind a **ruleset gate**, (c) builds the **day/long-rest trigger** (the one piece Plan 2 explicitly deferred) plus the chargen **initial-prepared** seeding so casters work turn 1, (d) wires the Warrior's **Killing Blow** rider and the **Effort/Art + Veteran's Luck** activation channel so all four archetypes are playable, and (e) proves the whole thing with **end-to-end wiring tests against the real `elemental_harmony` pack**.

After this plan, the cast spine, Effort economy, Killing Blow, Veteran's Luck, and the day/scene reclaim that Plan 2 unit-tested are **no longer dead in dispatch** — they fire from production code paths driven by the bound pack.

**Faithfulness is the whole point.** Mechanics come from the WWN SRD v1.0 (Crawford / Sine Nomine, CC0), recorded in the spec's 2026-05-29 amendment (§A–§I). A career GM (Keith) and the two mechanics-first players (Sebastien, Jade) catch a fudge in one round; every mechanical decision emits an OTEL span because the GM panel is the lie detector.

**Architecture (decided):**
- **Reuse, do not reinvent.** The engine (Plan 2), the lethality seam (Plan 1), the `cast_spell` beat machinery (47-10), the `beat_selection`/`hp_depletion` combat path (CWN/SWN), the `StoryBeatKind.REST` clock-beat, and the narrator tool-use sidecar pattern (ADR-102) all exist. Plan 3 is **integration**.
- **WWN bypasses the B/X magic system by design** (spec §A). It does NOT touch `magic_state`/`MagicState` (the C&C ledger) nor the B/X `Spell`/`SpellCatalog`. WWN spells are a **net-new content model** (`WwnSpell`/`WwnSpellCatalog`) that produces the engine's `CastInput`.
- **Ruleset gating, fail-loud.** Every new branch gates on `pack.rules.ruleset == "wwn"` (mirroring the `dice.py` downed seam `pack.rules.ruleset in ("cwn","wwn")`), so non-wwn packs are untouched and a drifted binding fails loud rather than silently no-ops.
- **Natural language over menus (SOUL).** The day/rest trigger and Art/Veteran's-Luck activation ride a **narrator sidecar** (the same shape as `beat_selections`/`items_gained`), not a UI button — the player says "we make camp for the night" and the narrator signals it.

**Tech Stack:** Python 3.12, pydantic v2, pytest (`-n0` for ordered runs), OpenTelemetry spans, `uv` (server); YAML genre packs (content). Server runs from `sidequest-server/`.

**Spec:** `docs/superpowers/specs/2026-05-29-wwn-ruleset-elemental-harmony-design.md` — **read the 2026-05-29 Amendment (§A–§I) first.** §6 is the content-binding spec; §I defines this plan's split.

**Builds on:** Plan 1 (merged, PR #520) and Plan 2 (merged, PR #521 — commit `4b12cdc5`). The WWN module, `WwnConfig`, `MagicConfig`, per-core `EffortPool`/`SpellcastingState`/`CastInput`, `WwnClassMagic`/`WwnEffortSource`, `seed_wwn_magic`, the scene-end reclaim, and all `wwn.*` spans are present on `develop` and unit-tested against synthetic fixtures.

**Repos / branches:**
- `sidequest-server` (gitflow; base `develop`) → branch `feat/wwn-content-wiring`. Engine wiring + the WWN spell content model + tests.
- `sidequest-content` (gitflow; base `develop`) → branch `feat/wwn-elemental-harmony-binding`. The `elemental_harmony` pack binding.
- **Branch BOTH subrepos off `develop` before the first commit anywhere** (the pf commit hook scans all subrepos). Create + merge **one PR per repo** at finish.

**Reference sources to read and mirror (the proven idioms):**
- `sidequest-content/genre_packs/neon_dystopia/rules.yaml` — the CWN binding: `ruleset: cwn`, `attribute_map`, `cwn:` block (`system_strain`, `trauma`), and the **"Street Combat"** confrontation (`resolution_mode: beat_selection`, `win_condition: hp_depletion`, `opponent_default_stats` with `hp`/`armor_class`/`dexterity`, `shoot`/`melee` strike beats with `damage_channel: strike`, `take_cover` brace, `disengage` push). **This is the combat template to clone for "Martial Exchange".**
- `sidequest-content/genre_packs/space_opera/rules.yaml` — the SWN binding + the `overload` beat with `damage_override: {dice: "2d6"}` (the template for a heavier strike).
- `sidequest-content/genre_packs/space_opera/classes.yaml` — the class shape (`id`, `display_name`, `rpg_role`, `prime_requisite`, `encounter_beat_choices`, `magic_access`, `abilities: [{name, genre_description, mechanical_effect, involuntary}]`).
- `sidequest-content/genre_packs/neon_dystopia/inventory.yaml` — weapons with `damage: {dice, bonus, trauma_die, trauma_rating, shock, shock_ac}` and armor with `armor_class` + `mitigation`.
- `sidequest-server/sidequest/magic/spell_catalog.py` (`Spell`:130, `SpellCatalog`:152, `load_spell_catalog`:181) — the catalog idiom to **mirror in shape but NOT reuse** (B/X tradition/save columns are wrong for WWN).
- `sidequest-server/sidequest/server/narration_apply.py` — `_resolve_innate_cast_for_beat` (:116, the B/X resolver — the precedent for `_resolve_wwn_cast_for_beat`), the `cast_spell` branch (:3026), and `_apply_narration_result_to_snapshot(... pack ...)` (:1684, where `pack` is in scope).
- `sidequest-server/sidequest/server/dispatch/dice.py` — the strike→damage→downed seam (~:495 damage, :653 the `pack.rules.ruleset in ("cwn","wwn")` downed gate). The Killing Blow rider lands here.
- `sidequest-server/sidequest/server/session.py` — `Session.advance_via_beat` (:72) and `Session.end_scene` (:107, fires an ENCOUNTER `StoryBeat` + the wwn scene reclaim). The long-rest seam mirrors this with a REST beat.
- `sidequest-server/sidequest/orbital/beats.py` — `StoryBeatKind.REST` (:24, fixed 8h), `advance_clock_via_beat` (:53, emits `clock.advance`).
- `sidequest-server/sidequest/game/beat_filter.py` — `cast_spell` selectability (:70/:83/:104) gated on B/X `magic_state`; needs a wwn branch.
- `sidequest-server/sidequest/game/builder.py` — `seed_wwn_magic` (:97) + call site (:2322) + attach (:2352-2353); the chargen seam for initial-prepared.
- `sidequest-server/sidequest/game/ruleset/wwn.py` — the merged engine methods the wiring calls: `resolve_spellcast` (:466), `apply_killing_blow` (:590), `veterans_luck` (:620), `commit_effort` (:303), `reclaim_day_and_refresh` (:414).

---

## File Structure

### sidequest-server (`feat/wwn-content-wiring`)

| File | Responsibility | Action |
|---|---|---|
| `sidequest/genre/models/wwn_spell.py` | `WwnSpell` + `WwnSpellCatalog` content models; `WwnSpell.to_cast_input() -> CastInput`; `load_wwn_spell_catalog(path)` | Create |
| `sidequest/genre/models/pack.py` | `GenrePack.wwn_spell_catalog: WwnSpellCatalog \| None` field | Modify |
| `sidequest/genre/models/character.py` | `WwnClassMagic.starting_prepared: list[str]` (chargen initial prepared) | Modify |
| `sidequest/genre/loader.py` | Load `spells_wwn.yaml` → `pack.wwn_spell_catalog`; validate spell-id refs in `starting_prepared` / catalog | Modify |
| `sidequest/game/builder.py` | Seed `spellcasting.prepared` from `class_def.wwn_magic.starting_prepared` (capped at `prepared_by_level["1"]`) | Modify |
| `sidequest/game/beat_filter.py` | wwn branch for `cast_spell` selectability (gate on `core.spellcasting`, not `magic_state`) | Modify |
| `sidequest/agents/orchestrator.py` | `NarrationTurnResult` sidecar fields: `rest_signal` + `class_power_activations` | Modify |
| `sidequest/agents/tools/*` (narration tool schema) | Add `rest`/`class_power` to the narrator tool contract + descriptions (ADR-102) | Modify |
| `sidequest/server/narration_apply.py` | `_resolve_wwn_cast_for_beat`; ruleset gate at the `cast_spell` branch; `class_power` activation router (Effort/Art commit + Veteran's Luck); rest-signal handler | Modify |
| `sidequest/server/dispatch/dice.py` | Killing Blow rider in the wwn strike-damage seam (gated on wwn + Warrior) | Modify |
| `sidequest/server/session.py` | `Session.apply_long_rest(...)` — fires REST `StoryBeat` + `reclaim_day_and_refresh` + reprepare per PC core (ruleset-gated) | Modify |
| `sidequest/telemetry/spans/wwn.py` | `wwn.long_rest` span (rest reclaim + reprepare) | Modify |
| `tests/game/test_wwn_starting_prepared.py` | chargen seeds `prepared` from `starting_prepared`, capped | Create |
| `tests/game/models/test_wwn_spell_catalog.py` | `WwnSpell`/`WwnSpellCatalog` parse + `to_cast_input` + dup-id reject + loader | Create |
| `tests/game/test_wwn_beat_filter.py` | wwn `cast_spell` selectability gates on `spellcasting` | Create |
| `tests/server/test_wwn_cast_dispatch.py` | `_resolve_wwn_cast_for_beat` routes to `resolve_spellcast`, applies damage, runs downed seam, emits `wwn.spell.cast` | Create |
| `tests/server/test_wwn_killing_blow_wiring.py` | wwn Warrior strike adds the Killing Blow rider; non-Warrior / non-wwn untouched | Create |
| `tests/server/test_wwn_class_power_dispatch.py` | `class_power_activations` route to `commit_effort` / `veterans_luck` with spans | Create |
| `tests/server/test_wwn_long_rest.py` | `apply_long_rest` reclaims day Effort + refreshes casts + repreps + fires REST beat + `wwn.long_rest` | Create |
| `tests/integration/test_wwn_elemental_harmony_dispatch.py` | **WIRING — real pack**: load `elemental_harmony`, drive a `cast_spell` beat on the real combat path, assert it routes through `WwnRulesetModule` | Create |
| `tests/integration/test_wwn_elemental_harmony_chargen.py` | **WIRING — real pack**: build each archetype from the real pack; assert Effort pools + spellcasting + initial prepared land on the snapshot | Create |
| `tests/genre/test_elemental_harmony_loads_wwn.py` | **calibration (content-gated)**: pack loads clean under `ruleset: wwn`; combat/spell refs resolve | Create |

### sidequest-content (`feat/wwn-elemental-harmony-binding`)

| File | Responsibility | Action |
|---|---|---|
| `genre_packs/elemental_harmony/rules.yaml` | `ruleset: wwn` + `attribute_map`; `wwn:` block (`system_strain`, `trauma`, `magic`); rewrite **"Martial Exchange"** → `beat_selection` / `hp_depletion` with `opponent_default_stats`, strike + `cast_spell` beats | Modify |
| `genre_packs/elemental_harmony/inventory.yaml` | WWN weapon `damage:` (+ Shock on melee) and armor `armor_class` (10–19) + `mitigation`, themed wuxia | Modify |
| `genre_packs/elemental_harmony/classes.yaml` | **NEW** — 6 classes → 4 archetypes, each with `prime_requisite`, `abilities`, `encounter_beat_choices`, `magic_access`, and a `wwn_magic` block (incl. `starting_prepared`) | Create |
| `genre_packs/elemental_harmony/spells_wwn.yaml` | **NEW** — the casters' WWN spell catalog (id/level/save/damage + `genre_description`/`mechanical_effect` prose) | Create |
| `genre_packs/elemental_harmony/char_creation.yaml` | align the class list to `classes.yaml` (point-buy 30 stays) | Modify |
| `genre_packs/elemental_harmony/worlds/{burning_peace,shattered_accord}/` | verify no rules override (no rewrite expected) | Verify |

---

## Task 0: Branches + baseline

- [ ] **Step 1: Branch BOTH subrepos off `develop`** (hook scans all subrepos — do this before any commit):
```bash
cd sidequest-server && git checkout develop && git pull --ff-only && git checkout -b feat/wwn-content-wiring && cd ..
cd sidequest-content && git checkout develop && git pull --ff-only && git checkout -b feat/wwn-elemental-harmony-binding && cd ..
```

- [ ] **Step 2: Record the full-suite baseline** (both env vars; only a NEW failure is a regression — `tests/integration/` and content-gated `tests/genre/` are part of the gate, not a scoped subset):
```bash
cd sidequest-server
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
uv run pytest -q 2>&1 | tail -40
```
Save the failure/error list. (As of Plan 2 merge the baseline was content/audit/reference failures only — none in `tests/game/ruleset/`. Re-confirm; `elemental_harmony` currently has no `ruleset:` so any pre-existing calibration skips there are expected.)

> **Wiring-checklist reminder ([[project_without_number_module_wiring_checklist]]):** Plan 1 correctly left chargen + narrator-tool seams cwn-gated. **Plan 3 is exactly where wwn enters those seams** — `beat_filter` (Task 5), the narrator tool contract (Task 6), the cast branch (Task 7). Audit each for a cwn-only or B/X-only gate that now needs a wwn arm. **No source-text wiring assertions** (CLAUDE.md) — use OTEL span assertions + fixture-driven behavior tests + the real-pack integration tests.

---

## Task 1 (content): bind `elemental_harmony` rules.yaml to `wwn`

Clone the CWN/SWN binding shape. With **no save attachment** (the playgroup has zero attachment to current elemental_harmony rules — spec §1), the combat confrontation is **rewritten clean**, not migrated.

**File:** `sidequest-content/genre_packs/elemental_harmony/rules.yaml`.

- [ ] **Step 1: Add the ruleset binding + attribute_map** (the d20-six map is 1:1, no stat-check churn — spec §6):
```yaml
ruleset: wwn
wwn:
  attribute_map:
    STRENGTH: Strength
    DEXTERITY: Agility
    CONSTITUTION: Endurance
    INTELLIGENCE: Insight
    WISDOM: Spirit
    CHARISMA: Harmony
  system_strain:
    max_source: CONSTITUTION
    rest_recovery_per_night: 1
    first_aid_cost: 1
  trauma:
    default_trauma_target: 6
    mortal_injury_rounds: 6
    major_injury_save: physical
  magic:
    effort_base: 1
    killing_blow_divisor: 2
    day_reclaim_requires_comfort: true
    default_spell_save: mental
```
(Keep `ability_score_names` = the existing six flavor names. The `magic` block mirrors `MagicConfig` defaults — author explicitly so authors can see/tune them.)

- [ ] **Step 2: Rewrite "Martial Exchange"** to the `hp_depletion` template (clone neon_dystopia "Street Combat"):
```yaml
  - name: "Martial Exchange"
    encounter_type: combat
    resolution_mode: beat_selection
    win_condition: hp_depletion
    opponent_default_stats: { Strength: 10, Agility: 10, Endurance: 10, hp: 8, armor_class: 12, dexterity: 11 }
    beats:
      - { id: strike, label: "Strike", kind: strike, base: 2, stat_check: Strength, attack_bonus: 1, combat_skill: 1, damage_channel: strike }
      - { id: elemental_burst, label: "Elemental Burst", kind: strike, base: 4, stat_check: Strength, attack_bonus: 1, combat_skill: 1, damage_channel: strike, damage_override: { dice: "2d6", bonus: 0 }, risk: "Spirit flares wide — lose 2 momentum on any failure" }
      - { id: cast_spell, label: "Channel a Spell", kind: strike, stat_check: Spirit, damage_channel: none }
      - { id: guard, label: "Guard", kind: brace, base: 1, stat_check: Endurance }
      - { id: yield, label: "Yield", kind: push, stat_check: Agility, consequence: "Combat ends" }
```
(`cast_spell` carries `damage_channel: none` — its damage is rolled by `resolve_spellcast`, not the strike channel. Calibrate `hp`/`armor_class` per ADR-093: an unarmored wuxia mook is killable in 2–3 hits.)

- [ ] **Step 3:** Leave the social ("Diplomatic Council") and chase ("Pursuit") confrontations as-is (ruleset-transparent; they don't use HP). Verify they still parse under the new ruleset.

- [ ] **Step 4: Commit (content repo):**
```bash
cd sidequest-content && git add genre_packs/elemental_harmony/rules.yaml
git commit -m "feat(elemental_harmony): bind to wwn ruleset + hp_depletion Martial Exchange" && cd ..
```

---

## Task 2 (content): WWN weapons + armor in inventory.yaml

Mirror neon_dystopia/space_opera item shape; theme to wuxia. WWN damage dice + ascending AC (10–19).

**File:** `sidequest-content/genre_packs/elemental_harmony/inventory.yaml`.

- [ ] **Step 1: Add `damage:` to weapons** (melee carry Shock; SRD-faithful dice). Examples:
```yaml
- id: jian_steel        # straight sword
  damage: { dice: "1d8", bonus: 0, shock: 2, shock_ac: 15 }
- id: staff_ironwood
  damage: { dice: "1d6", bonus: 0, shock: 1, shock_ac: 13 }
- id: dao_broad
  damage: { dice: "1d8", bonus: 0, shock: 2, shock_ac: 15 }
- id: unarmed_strike    # Punch — Martial Artist default
  damage: { dice: "1d2", bonus: 0 }
- id: throwing_knives
  damage: { dice: "1d4", bonus: 0 }
```

- [ ] **Step 2: Add armor** (ascending AC 10–19, themed; robes are light):
```yaml
- id: silk_robes        # unarmored-ish
  armor_class: 11
- id: padded_war_robe
  armor_class: 13
  mitigation: 1
- id: lamellar
  armor_class: 16
  mitigation: 1
```
(Base unarmored AC = `WwnConfig.unarmored_ac` = 10 + DEX/Agility, inherited from SWN — armor items override per the SWN/CWN model.)

- [ ] **Step 3: Verify per-class starting equipment** still references valid item ids after edits.

- [ ] **Step 4: Commit (content):**
```bash
cd sidequest-content && git add genre_packs/elemental_harmony/inventory.yaml
git commit -m "feat(elemental_harmony): WWN weapon damage (+Shock) and ascending-AC armor" && cd ..
```

---

## Task 3 (server): `WwnSpell` + `WwnSpellCatalog` content model

Net-new (spec §A: the B/X `Spell` is NOT reused). Pure content data; produces the engine's `CastInput`. Mirror `spell_catalog.py`'s catalog idiom (dup-id check, `load_*` helper) without its B/X fields.

**Files:** create `sidequest/genre/models/wwn_spell.py`; create `tests/game/models/test_wwn_spell_catalog.py`.

- [ ] **Step 1: Write the failing tests** — parse a `WwnSpell`; `to_cast_input()` yields a `CastInput` with matching `id`/`level`/`save`/`damage_die`/`damage_per_level`; a no-save utility spell has `save=None`; `WwnSpellCatalog` rejects duplicate ids; `load_wwn_spell_catalog(tmp_path/yaml)` round-trips. Mirror `tests/.../test_*spell_catalog*` if one exists.

- [ ] **Step 2: Run, verify FAIL** (ImportError).

- [ ] **Step 3: Implement `wwn_spell.py`:**
```python
from sidequest.game.wwn_magic import CastInput, SaveCategory  # reuse the engine's SaveCategory literal

class WwnSpell(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    name: str
    level: int                                  # 1..max
    save: SaveCategory | None = None            # defender save category, or None
    damage_die: str | None = None               # "1d6" etc, or None for non-damage
    damage_per_level: bool = False              # caster_level x die when True
    genre_description: str                       # player-facing prose
    mechanical_effect: str                       # Approach C: narrator-adjudicated bespoke effect
    range: str = "near"                          # flavor
    target: str = "single"                       # flavor

    def to_cast_input(self) -> CastInput:
        return CastInput(id=self.id, level=self.level, save=self.save,
                         damage_die=self.damage_die, damage_per_level=self.damage_per_level)

class WwnSpellCatalog(BaseModel):
    model_config = {"extra": "forbid"}
    version: str = "1.0"
    spells: list[WwnSpell] = Field(default_factory=list)
    # model_validator: reject duplicate ids (mirror SpellCatalog._check_unique_spell_ids)
    def get(self, spell_id: str) -> WwnSpell: ...   # raise KeyError on miss (fail loud)

def load_wwn_spell_catalog(path: Path) -> WwnSpellCatalog: ...  # yaml.safe_load + model_validate
```

- [ ] **Step 4: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add sidequest/genre/models/wwn_spell.py tests/game/models/test_wwn_spell_catalog.py
git commit -m "feat(genre): WwnSpell + WwnSpellCatalog content model (-> CastInput)" && cd ..
```

---

## Task 4 (server + content): load the catalog onto the pack

Attach the WWN catalog to the `GenrePack` and load it from `spells_wwn.yaml`. Validate that `starting_prepared` (Task 8) and combat `cast_spell` refs resolve against it (fail loud on unknown ids).

**Files:** modify `sidequest/genre/models/pack.py`, `sidequest/genre/loader.py`; create `sidequest-content/.../spells_wwn.yaml`.

- [ ] **Step 1: Add the pack field** — `GenrePack.wwn_spell_catalog: WwnSpellCatalog | None = None`.

- [ ] **Step 2: Load it in `loader.py`** near the existing catalog seam (`has_spell_catalogs=(path / "spells").is_dir()`, ~:1160): if `(path / "spells_wwn.yaml").exists()`, `pack.wwn_spell_catalog = load_wwn_spell_catalog(...)`. Gate the load on `rules.ruleset == "wwn"` and **fail loud** if a wwn pack declares caster classes but ships no `spells_wwn.yaml` (No Silent Fallbacks).

- [ ] **Step 3: Author `spells_wwn.yaml`** (content) — the elemental_harmony caster spell list. A small faithful starter set (≈6–10 spells across levels 1–2), each with `genre_description` + `mechanical_effect`. Include at least: one damage spell (`damage_die`, `save: evasion`, save-for-half), one save-or-suffer control spell (`save: mental`, `damage_die: null`), one no-save utility (`save: null`). Example:
```yaml
version: "1.0"
spells:
  - id: cinder_lance
    name: "Cinder Lance"
    level: 1
    save: evasion
    damage_die: "1d6"
    damage_per_level: true
    genre_description: "A spear of living flame leaps from your fingertips."
    mechanical_effect: "Caster-level d6 fire damage; an Evasion save halves it."
  - id: still_the_breath
    name: "Still the Breath"
    level: 1
    save: mental
    genre_description: "You press the air from a foe's lungs with a gesture."
    mechanical_effect: "On a failed Mental save, the target is staggered and loses its next action (narrator-adjudicated)."
  - id: river_step
    name: "River Step"
    level: 1
    genre_description: "Your footing flows; the ground stops mattering."
    mechanical_effect: "Utility — no save. Narrator grants frictionless movement / a crossing this scene."
```

- [ ] **Step 4: Reference-validation test** — extend the calibration test (Task 16) OR add a loader unit test: a synthetic wwn pack with an unknown `starting_prepared` id raises at load (fail loud).

- [ ] **Step 5: Commit (both repos, separately):**
```bash
cd sidequest-server && git add sidequest/genre/models/pack.py sidequest/genre/loader.py
git commit -m "feat(genre): load spells_wwn.yaml onto GenrePack.wwn_spell_catalog (fail-loud refs)" && cd ..
cd sidequest-content && git add genre_packs/elemental_harmony/spells_wwn.yaml
git commit -m "feat(elemental_harmony): WWN caster spell catalog (spells_wwn.yaml)" && cd ..
```

---

## Task 5 (server): wwn branch in `beat_filter` (cast_spell selectability)

`cast_spell` selectability currently gates on the B/X `magic_state`/`prepared_spells` (`beat_filter.py:70/:104`). A wwn caster has no `magic_state` entry, so without a wwn arm the beat is wrongly filtered. Gate the wwn arm on `core.spellcasting` (prepared non-empty AND `casts_remaining > 0`).

**Files:** modify `sidequest/game/beat_filter.py`; create `tests/game/test_wwn_beat_filter.py`.

- [ ] **Step 1: Write failing tests** — for a wwn core: `cast_spell` selectable when `spellcasting.casts_remaining > 0` and `prepared` non-empty; rejected (with the right reason) when `casts_remaining == 0` or `prepared == []`; a wwn non-caster (`spellcasting is None`) rejects with the `"class"` reason. Reuse the `cast_spell_rejection_reason` contract.

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement** — add a `ruleset == "wwn"` (or `core.spellcasting is not None`) branch that reads `core.spellcasting` instead of `magic_state`. Keep the B/X branch untouched for non-wwn packs.

- [ ] **Step 4: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add sidequest/game/beat_filter.py tests/game/test_wwn_beat_filter.py
git commit -m "feat(beat_filter): wwn cast_spell selectability gates on core.spellcasting" && cd ..
```

---

## Task 6 (server): narrator sidecar contract — rest + class-power activation

The day/rest trigger and Art/Veteran's-Luck activation ride the narrator tool-use sidecar (SOUL: natural language, not a menu; ADR-102 tool contract). Add the fields + tool descriptions so the narrator can signal them; emit a watcher event when one fires (lie detector).

**Files:** modify `sidequest/agents/orchestrator.py` (`NarrationTurnResult`); modify the narration tool schema under `sidequest/agents/tools/`.

- [ ] **Step 1: Add `NarrationTurnResult` fields:**
```python
    rest_signal: RestSignal | None = None
    class_power_activations: list[ClassPowerActivation] = field(default_factory=list)
```
where (define near the result, or in a small sidecar module):
```python
@dataclass
class RestSignal:
    comfortable: bool = True          # gates day-Effort reclaim (SRD comfort rule)
    reprepare: list[str] | None = None  # spell ids to prepare this rest; None = keep current

@dataclass
class ClassPowerActivation:
    actor: str
    kind: str                          # "art" | "veterans_luck"
    source: str | None = None          # Effort source (Arts)
    points: int = 1                    # Effort committed (Arts)
    duration: str = "scene"            # maintained | scene | day (Arts)
    mode: str | None = None            # "force_hit" | "force_miss" (Veteran's Luck)
    label: str = ""
```

- [ ] **Step 2: Extend the narrator tool contract** — add `rest` and `class_power` to the tool schema with descriptions that tell the narrator when to emit them (e.g. "When the party takes a night's rest, emit `rest`. When a Vowed commits Effort to an Art or a Warrior spends Veteran's Luck, emit `class_power`."). Parse them into the new result fields. **Gate parsing on the bound ruleset being wwn** so non-wwn narrators never see/emit them.

- [ ] **Step 3: Tests** — extend the orchestrator/tool-parse tests: a tool call carrying `rest`/`class_power` populates the result fields; absent → defaults. (Behavior test on the parser, not a source grep.)

- [ ] **Step 4: Commit (server):**
```bash
cd sidequest-server && git add sidequest/agents/orchestrator.py sidequest/agents/tools/
git commit -m "feat(narrator): rest + class_power activation sidecar (wwn-gated tool contract)" && cd ..
```

---

## Task 7 (server): cast_spell → `resolve_spellcast` (the core mandate)

Add the ruleset-gated cast branch. When the bound ruleset is wwn, route `cast_spell` to a new `_resolve_wwn_cast_for_beat` that looks up the named spell, builds a `CastInput`, resolves the **defender**, calls `resolve_spellcast`, applies spell damage through the HP channel, and runs the existing wwn downed seam. Otherwise keep the B/X path.

**Files:** modify `sidequest/server/narration_apply.py`; create `tests/server/test_wwn_cast_dispatch.py`.

- [ ] **Step 1: Write the failing tests.** Synthetic wwn snapshot + bound pack with a `wwn_spell_catalog`, a caster PC core with `spellcasting` (prepared, casts), and an opponent core with HP. Drive the beat with a `BeatSelection(beat_id="cast_spell", spell_id="cinder_lance", ...)`:
  - **refuse path**: `casts_remaining=0` → no cast, `casts_remaining` unchanged, `wwn.spell.cast` fired with `refused=True` (assert via `InMemorySpanExporter`).
  - **damage spell**: casts decremented, defender's Evasion save rolled, `damage > 0` applied to opponent `core.hp.current` (save halves), `wwn.spell.cast` fired.
  - **0 HP**: a killing cast triggers the wwn downed seam (assert `resolve_downed`'s span / mortal-injury effect).
  - **unknown spell id** → fail loud (raise) with a watcher event (mirror `_resolve_innate_cast_for_beat`'s guard-logs).
  Pin `"wwn.spell.cast"` literally; pin rng via monkeypatch.

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement `_resolve_wwn_cast_for_beat`** (mirror `_resolve_innate_cast_for_beat`'s guard-log idiom):
```python
def _resolve_wwn_cast_for_beat(*, sel, actor, snapshot, pack):
    """WWN cast resolution (spec §D). Look up the prepared spell in
    pack.wwn_spell_catalog, build a CastInput, resolve the defender, call
    WwnRulesetModule.resolve_spellcast, apply damage through the HP channel,
    run the downed seam. Each missing precondition logs a watcher event
    (lie-detector) and the cast is refused-but-recorded, never a silent no-op."""
```
Resolve the module via `get_ruleset_module("wwn")`; the defender = opposite-side first actor (reuse `_opposite_side_first_actor` from dice.py's idiom or the encounter actors). Apply `SpellcastResult.damage` to the defender's `core.hp` exactly as the strike path applies `resolve_damage` output, then run the **same downed seam** the strike path uses (gated `pack.rules.ruleset in ("cwn","wwn")`). Then gate the branch:
```python
                if beat.id == "cast_spell":
                    if pack and pack.rules and pack.rules.ruleset == "wwn":
                        _resolve_wwn_cast_for_beat(sel=sel, actor=actor, snapshot=snapshot, pack=pack)
                    else:
                        _resolve_innate_cast_for_beat(sel=sel, actor=actor, snapshot=snapshot)
```

- [ ] **Step 4: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add sidequest/server/narration_apply.py tests/server/test_wwn_cast_dispatch.py
git commit -m "feat(narration_apply): route wwn cast_spell to resolve_spellcast (damage + downed seam)" && cd ..
```

> **Path trap ([[project_opposed_check_wiring_trap]]):** combat-mutation features must work on the path real play uses. `cast_spell` is narrator-nominated and resolves in `narration_apply` (47-10), but the strike/damage half of `hp_depletion` combat flows through `dice.py`. The **real-pack integration test (Task 14)** is what proves the cast actually fires in `elemental_harmony` play — do not declare this done on the synthetic test alone.

---

## Task 8 (server + content): chargen initial-prepared seeding

A fresh caster must be able to cast on turn 1, so `prepared` cannot stay `[]` until the first rest. The class def carries `starting_prepared`; the builder seeds it (capped at the level-1 prepared capacity).

**Files:** modify `sidequest/genre/models/character.py` (`WwnClassMagic.starting_prepared`); modify `sidequest/game/builder.py`; create `tests/game/test_wwn_starting_prepared.py`. (Content `starting_prepared` is authored in Task 11.)

- [ ] **Step 1: Add the field** — `WwnClassMagic.starting_prepared: list[str] = Field(default_factory=list)` (spell ids the class knows + prepares at chargen).

- [ ] **Step 2: Failing test** — `seed_wwn_magic` (or a follow-on in `build()`) seeds `spellcasting.prepared = starting_prepared[:capacity]` where `capacity = prepared_by_level.get("1", len(starting_prepared))`; a non-caster yields `prepared` untouched (no spellcasting); over-capacity is truncated (not an error).

- [ ] **Step 3: Implement** — extend `seed_wwn_magic` to populate `prepared` from `cm.starting_prepared` (capped). This is the consumer-side completion of the field Plan 2 left as capacity-only (`SpellcastingState.prepared` was seeded `[]`).

- [ ] **Step 4: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add sidequest/genre/models/character.py sidequest/game/builder.py tests/game/test_wwn_starting_prepared.py
git commit -m "feat(chargen): seed SpellcastingState.prepared from class starting_prepared (capped)" && cd ..
```

---

## Task 9 (server): Killing Blow rider in the strike-damage seam

Wire the merged `apply_killing_blow` (wwn.py:590) into the wwn strike path so a Warrior's strikes (and Shock) carry `+ceil(level/2)`. Gated on wwn **and** the actor being a Warrior-archetype class.

**Files:** modify `sidequest/server/dispatch/dice.py`; create `tests/server/test_wwn_killing_blow_wiring.py`.

- [ ] **Step 1: Failing test** — a wwn Warrior strike that deals base damage `D` lands `D + ceil(level/2)`; `wwn.killing_blow` span fires; a wwn non-Warrior and a non-wwn strike are unchanged (no span). Drive the real `dispatch_dice_throw` strike path with a synthetic wwn pack + Warrior core (fixture-driven, per CLAUDE.md).

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement** — in the dice.py strike-damage seam (after `resolve_damage`, near the downed seam ~:653), if `pack.rules.ruleset == "wwn"` and the actor's class is a Warrior archetype (read the class def's `wwn_magic`/an `is_warrior` marker, or a `class_filter`-style check — decide the cleanest signal; a `warrior: true` flag on the class def is acceptable and explicit), call `apply_killing_blow(base_total=dmg, level=actor_level, cfg=cfg, actor=name)` and use the returned total. Apply the same rider to Shock per SRD §1.5.18.

- [ ] **Step 4: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add sidequest/server/dispatch/dice.py tests/server/test_wwn_killing_blow_wiring.py
git commit -m "feat(dice): wire WWN Killing Blow rider into the wwn Warrior strike seam" && cd ..
```

---

## Task 10 (server): class-power activation router (Effort/Art + Veteran's Luck)

Route `class_power_activations` (Task 6 sidecar) to the merged engine methods so the Vowed (Effort-only Art user) and the Warrior's Veteran's Luck are live — otherwise two of four archetypes are half-wired.

**Files:** modify `sidequest/server/narration_apply.py`; create `tests/server/test_wwn_class_power_dispatch.py`.

- [ ] **Step 1: Failing tests** — a `ClassPowerActivation(kind="art", source="vowed", points=1, duration="scene")` calls `commit_effort` (assert `wwn.effort.commit` span + pool `available` decremented; over-commit refused-but-recorded); a `kind="veterans_luck", mode="force_hit"` calls `veterans_luck` (assert `wwn.veterans_luck` span; second same-scene call `applied=False`). Gate on wwn.

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement** — in `_apply_narration_result_to_snapshot`, after beat application, iterate `result.class_power_activations` (only when `pack.rules.ruleset == "wwn"`), resolve the actor core, and dispatch to `module.commit_effort(...)` / `module.veterans_luck(...)`. Each unknown actor / missing pool logs a watcher event (lie detector), never a silent skip.

- [ ] **Step 4: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add sidequest/server/narration_apply.py tests/server/test_wwn_class_power_dispatch.py
git commit -m "feat(narration_apply): wwn class-power router (Effort/Art commit + Veteran's Luck)" && cd ..
```

---

## Task 11 (content): `classes.yaml` — 6 classes → 4 archetypes

**NEW file.** Map the six `allowed_classes` onto the engine archetypes (spec §3.5 / §6), each with abilities (`genre_description` + `mechanical_effect`), `prime_requisite`, `encounter_beat_choices` (incl. `cast_spell` for casters), `magic_access`, and a `wwn_magic` block (`effort_sources`, `casts_per_day_by_level`, `max_spell_level_by_level`, `prepared_by_level`, `partial`, `starting_prepared`). Decide the magic-governing attribute here (spec leaves Spirit vs Harmony to authoring — **Spirit** for Channeler/Spirit Medium reads best; record the choice).

**File:** create `sidequest-content/genre_packs/elemental_harmony/classes.yaml`. Clone `space_opera/classes.yaml` structure.

- [ ] **Step 1: Casters** — **Channeler** + **Spirit Medium** = slot+Effort casters:
```yaml
- id: channeler
  display_name: Channeler
  rpg_role: caster
  prime_requisite: Spirit
  magic_access: wwn
  encounter_beat_choices: [strike, cast_spell, elemental_burst, guard, yield]
  abilities:
    - { name: "Elemental Attunement", genre_description: "...", mechanical_effect: "...", involuntary: false }
  wwn_magic:
    effort_sources:
      - { source: channeler, governing_attr: WISDOM, relevant_skill: Channel, starting_skill_level: 1 }
    casts_per_day_by_level: { "1": 2 }
    max_spell_level_by_level: { "1": 1 }
    prepared_by_level: { "1": 2 }
    starting_prepared: [cinder_lance, river_step]
    partial: false
```

- [ ] **Step 2: Vowed (Effort-only Art user)** — **Martial Artist**: `wwn_magic` with `effort_sources` (source `vowed`) but **no cast tables** (`seed_wwn_magic` yields `spellcasting = None` — Effort only). Its Arts are `abilities` whose use the narrator signals via `class_power` (Task 10). `encounter_beat_choices` excludes `cast_spell`.

- [ ] **Step 3: Warrior** — **Guardian**: no `wwn_magic` (no Effort/casts); mark it the Warrior archetype (the `warrior: true`/equivalent flag the Killing Blow gate reads, Task 9). Abilities reflect Killing Blow + Veteran's Luck in prose.

- [ ] **Step 4: Experts** — **Scholar** + **Wanderer**: no `wwn_magic`; skill-expert abilities; standard combat beats (no `cast_spell`).

- [ ] **Step 5: Commit (content):**
```bash
cd sidequest-content && git add genre_packs/elemental_harmony/classes.yaml
git commit -m "feat(elemental_harmony): classes.yaml — 6 classes mapped to WWN archetypes" && cd ..
```

---

## Task 12 (content): align char_creation.yaml

Point the class step at `classes.yaml`; point-buy 30 stays (spec §6). Narrative hint flow is unchanged.

**File:** `sidequest-content/genre_packs/elemental_harmony/char_creation.yaml`.

- [ ] **Step 1:** Ensure the class-hint choice values match the `classes.yaml` ids/display names (so `build()` resolves the ClassDef). Keep point-buy budget 30.
- [ ] **Step 2: Commit (content):**
```bash
cd sidequest-content && git add genre_packs/elemental_harmony/char_creation.yaml
git commit -m "feat(elemental_harmony): align char_creation class list to classes.yaml" && cd ..
```

---

## Task 13 (server): `Session.apply_long_rest` — the day/rest trigger

The piece Plan 2 deferred. A long rest fires a REST `StoryBeat` (existing clock infra), reclaims **day** Effort + refreshes `casts_remaining` (`reclaim_day_and_refresh`), and re-prepares spells — per PC core, ruleset-gated, with a `wwn.long_rest` span. Triggered by the `rest_signal` sidecar (Task 6) from `narration_apply`.

**Files:** modify `sidequest/server/session.py`; modify `sidequest/telemetry/spans/wwn.py` (add `wwn.long_rest`); modify `sidequest/server/narration_apply.py` (fire on `rest_signal`); create `tests/server/test_wwn_long_rest.py`.

- [ ] **Step 1: Add `wwn.long_rest` span** in `telemetry/spans/wwn.py` (mirror the Plan 2 span idiom; rides `test_routing_completeness` via the `__init__` re-export). Attrs: `actor`, `day_effort_reclaimed`, `casts_refreshed_to`, `reprepared`, `comfortable`.

- [ ] **Step 2: Failing test** — `Session.apply_long_rest(reason, *, turn, comfortable, reprepare)` on a wwn session: a PC core with a `day` Effort commitment + spent casts ends with day Effort reclaimed (respecting the comfort gate: `comfortable=False` leaves `day` committed per `MagicConfig.day_reclaim_requires_comfort`), `casts_remaining == casts_per_day`, `prepared` updated to `reprepare` (capped), a REST `StoryBeat` fired (assert `clock.advance` span with `beat_kind="rest"`), and `wwn.long_rest` emitted. Non-wwn session: method is a clock-only REST beat (no magic mutation). Mirror the `end_scene` test harness.

- [ ] **Step 3: Implement `apply_long_rest`** mirroring `end_scene` (:107): fire `self.advance_via_beat(StoryBeat(kind=StoryBeatKind.REST, trigger=f"rest-{reason}"))`; then if `self._ruleset == "wwn"`, resolve the module (assert `WwnRulesetModule`, fail loud on drift — mirror the end_scene guard), and per PC core call `reclaim_day_and_refresh(core=core, comfortable=comfortable, cfg=cfg)` and apply the reprepare (cap at the core's prepared capacity). Emit `wwn.long_rest` per core.

- [ ] **Step 4: Fire it from the sidecar** — in `_apply_narration_result_to_snapshot`, when `result.rest_signal is not None` and the bound ruleset is wwn, call `session.apply_long_rest(...)` with the signal's `comfortable`/`reprepare`. (Resolve the session from the existing seam; if `narration_apply` lacks a session handle, fire it from the caller in `websocket_session_handler`/the handler that owns the session — read how `end_scene` is reached from `dice_throw.py:377` and mirror the ownership.)

- [ ] **Step 5: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add sidequest/server/session.py sidequest/telemetry/spans/wwn.py sidequest/server/narration_apply.py tests/server/test_wwn_long_rest.py
git commit -m "feat(session): WWN long-rest trigger — REST beat + day Effort reclaim + casts refresh + reprepare" && cd ..
```

> This closes the Plan 2 deferral and the CWN-precedent gap: unlike CWN system-strain recovery (a method with no trigger), WWN day-reclaim now has a **real production trigger**. No half-wired feature.

---

## Task 14 (server): WIRING — cast dispatch against the real pack

The mandated end-to-end test (spec §7). Load the **real `elemental_harmony` pack**, build a caster, drive a `cast_spell` beat on the real combat path, assert it routes through `WwnRulesetModule` (not the B/X resolver, not free functions) — drive the actual `beat_selection`/`hp_depletion` path, not a synthetic fixture (the opposed/hp_depletion no-op trap).

**File:** create `tests/integration/test_wwn_elemental_harmony_dispatch.py`.

- [ ] **Step 1: Write the test** — set `SIDEQUEST_GENRE_PACKS`, load `elemental_harmony`, instantiate a "Martial Exchange" combat with a caster PC (prepared `cinder_lance`) vs an opponent, drive the `cast_spell` beat through the real narration-apply/dice path, and assert: `casts_remaining` decremented, opponent `hp.current` reduced, and **`wwn.spell.cast` fired** (span assertion = the lie detector; survives refactor). Add a negative assertion that the B/X `magic.cast_spell_*` watcher events did **not** fire (proves the wwn arm took the branch).

- [ ] **Step 2: Run, verify PASS** (this is the real proof the cast spine is alive in production). Commit (server):
```bash
cd sidequest-server && git add tests/integration/test_wwn_elemental_harmony_dispatch.py
git commit -m "test(wiring): wwn cast_spell routes through WwnRulesetModule on the real elemental_harmony pack" && cd ..
```

---

## Task 15 (server): WIRING — chargen against the real pack

Build each archetype from the **real pack** end-to-end; assert the magic state lands on the snapshot with correct computed values (spec §7).

**File:** create `tests/integration/test_wwn_elemental_harmony_chargen.py`.

- [ ] **Step 1: Write the test** — load `elemental_harmony`; for the Channeler: build, assert `core.effort["channeler"].max == effort_base + starting_skill_level + mod(Spirit)`, `core.spellcasting.casts_remaining == casts_per_day`, `core.spellcasting.prepared == starting_prepared[:capacity]`. For the Martial Artist (Vowed): `core.effort["vowed"]` present, `core.spellcasting is None`. For the Guardian (Warrior) + Experts: `core.effort == {}`, `core.spellcasting is None`. Assert the fields survive a snapshot serialize/deserialize round-trip.

- [ ] **Step 2: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add tests/integration/test_wwn_elemental_harmony_chargen.py
git commit -m "test(wiring): wwn chargen seeds Effort/spellcasting/prepared on the real elemental_harmony pack" && cd ..
```

---

## Task 16 (server): calibration — pack loads clean under wwn

Content-gated load test (spec §7).

**File:** create `tests/genre/test_elemental_harmony_loads_wwn.py`.

- [ ] **Step 1:** Load `elemental_harmony`; assert `pack.rules.ruleset == "wwn"`, `pack.rules.wwn` parses, `pack.wwn_spell_catalog` is present, every class `starting_prepared` id resolves in the catalog, and the "Martial Exchange" `cast_spell` beat is present. (Skips without `SIDEQUEST_GENRE_PACKS` — that's expected.)

- [ ] **Step 2: Run, verify PASS. Commit (server):**
```bash
cd sidequest-server && git add tests/genre/test_elemental_harmony_loads_wwn.py
git commit -m "test(genre): elemental_harmony loads clean under wwn (calibration)" && cd ..
```

---

## Task 17: Full-suite gate + PRs (both repos)

- [ ] **Step 1: Lint/format/types (server)**
```bash
cd sidequest-server && uv run ruff format . && uv run ruff check . && \
uv run pyright sidequest/genre/models/wwn_spell.py sidequest/genre/models/pack.py \
  sidequest/genre/models/character.py sidequest/genre/loader.py sidequest/game/builder.py \
  sidequest/game/beat_filter.py sidequest/agents/orchestrator.py \
  sidequest/server/narration_apply.py sidequest/server/dispatch/dice.py \
  sidequest/server/session.py sidequest/telemetry/spans/wwn.py && cd ..
```

- [ ] **Step 2: Full suite vs the Task 0 baseline** (both env vars — the new `test_wwn_*` + integration + genre tests pass; no NEW failures):
```bash
cd sidequest-server
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
uv run pytest -q
cd ..
```

- [ ] **Step 3: Content sanity** — run any content validator (`just` recipe / `python -m sidequest.cli.validate` against `elemental_harmony`) so the pack passes the same gate live packs do.

- [ ] **Step 4: Open one PR per repo** (gitflow, base `develop`; `env -u GITHUB_TOKEN` per the gh-token shadow gotcha):
```bash
env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-server -B develop \
  -t "feat(ruleset): WWN content wiring + elemental_harmony binding (Plan 3 of 3)" \
  -b "Plan 3 of 3 (docs/superpowers/plans/2026-05-29-wwn-content-binding.md; spec amendment §I). Wires the merged Plan 2 engine into production: cast_spell -> resolve_spellcast (ruleset-gated), WwnSpell/WwnSpellCatalog content model, chargen initial-prepared seeding, Killing Blow rider, class-power (Effort/Art + Veteran's Luck) router, and the day/long-rest trigger (REST beat + reclaim_day_and_refresh + reprepare). End-to-end wiring tests drive the real elemental_harmony pack. Pairs with sidequest-content PR for the binding."
env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-content -B develop \
  -t "feat(elemental_harmony): bind to WWN ruleset (Plan 3 of 3)" \
  -b "elemental_harmony -> wwn binding: rules.yaml (ruleset/attribute_map/wwn block + hp_depletion Martial Exchange), inventory (WWN damage+Shock, ascending-AC armor), classes.yaml (6 classes -> 4 archetypes with wwn_magic), spells_wwn.yaml (caster catalog), char_creation alignment. Pairs with sidequest-server PR for the engine wiring."
```

- [ ] **Step 5:** Verify both PRs reference each other; merge server + content together (the integration/calibration tests need both).

---

## Self-Review

**Spec coverage (this plan = §6 content binding + §I Plan-3 wiring):**
- §6 rules.yaml (ruleset/attribute_map/wwn block, hp_depletion Martial Exchange) → Task 1 ✓
- §6 inventory (WWN damage + Shock, AC 10–19) → Task 2 ✓
- §6 classes.yaml (6 → 4 archetypes, wwn_magic, abilities, beat choices, magic_access) → Task 11 ✓
- §6 char_creation alignment (point-buy 30) → Task 12 ✓
- §6 worlds verify (no override) → Task 0/16 ✓
- §I cast_spell dispatch branch → Task 7 ✓ (real-pack proof Task 14)
- §I day/long-rest trigger (Plan 2 deferral) → Task 13 ✓
- §I end-to-end wiring tests vs the real pack → Tasks 14, 15 ✓
- §C/§D the cast spine consumes a content `Spell` (the model Plan 2 left to Plan 3) → Tasks 3, 4 ✓
- §B/§E all four archetypes playable: caster (Tasks 5/7/8), Vowed Effort-Art (Task 10), Warrior Killing Blow + Veteran's Luck (Tasks 9/10), Experts (content only) → ✓

**Reuse-first (no reinvention):** the engine (Plan 2), lethality + downed seam (Plan 1, already wwn-gated — `_physical_save_target_for` needs NO change), the `cast_spell` beat machinery + `beat_filter` + `cast_spell_rejection_reason` (47-10), the `hp_depletion`/`beat_selection` combat template (CWN/SWN), `StoryBeatKind.REST` + `advance_clock_via_beat` (orbital clock), and the narrator tool-use sidecar (ADR-102) are all reused. Net-new is minimal and justified: `WwnSpell`/`WwnSpellCatalog` (B/X `Spell` is the wrong shape, spec §A), the two sidecar fields, and `apply_long_rest` (no production rest trigger existed).

**Wiring-test discipline (CLAUDE.md):** no source-text assertions anywhere. Wiring is proven by OTEL span assertions (`wwn.spell.cast`, `wwn.killing_blow`, `wwn.effort.commit`, `wwn.veterans_luck`, `wwn.long_rest`, `clock.advance`) + fixture-driven behavior tests + the two **real-pack** integration tests (Tasks 14, 15) + the content-gated load test (Task 16). Every new branch fail-loud / watcher-logs on a missed precondition (No Silent Fallbacks).

**Without-Number wiring checklist ([[project_without_number_module_wiring_checklist]]):** the new `wwn.long_rest` span rides the `__init__` re-export + `test_routing_completeness` (Task 13). The seams Plan 1 left cwn-gated are now given wwn arms deliberately: `beat_filter` (Task 5), the narrator tool contract (Task 6), the cast branch (Task 7). `dice.py` downed seam + `_physical_save_target_for` already include wwn (Plan 1) — confirmed, not re-touched except for the Killing Blow rider (Task 9).

**Type consistency:** `WwnSpell.to_cast_input() -> CastInput` (Task 3) feeds `resolve_spellcast` (Task 7). `WwnClassMagic.starting_prepared` (Task 8) → `SpellcastingState.prepared` (builder). `RestSignal`/`ClassPowerActivation` (Task 6) → `apply_long_rest` (Task 13) / the class-power router (Task 10). `GenrePack.wwn_spell_catalog` (Task 4) ← loader, → the cast branch.

**Known risks & mitigations:**
1. **hp_depletion no-op trap** ([[project_opposed_check_wiring_trap]]) — mitigated by the real-pack dispatch test (Task 14) driving the actual combat path, plus a negative assertion that the B/X path did not fire.
2. **Magic-governing attribute (Spirit vs Harmony)** — decided in `classes.yaml` (Task 11), recorded there; the engine reads `governing_attr` so a later retune is content-only.
3. **Combat HP calibration** (ADR-093) — `opponent_default_stats` cloned from neon_dystopia's killable-in-2–3-hits baseline; tune during playtest, not in this plan.
4. **Narrator tool-contract size** — three archetypes need the rest + class_power sidecar (Task 6); it is wwn-gated so non-wwn narrators are unaffected. If the contract change proves heavy in review, Tasks 10/13's *triggers* are a clean cut line (the engine methods + `apply_long_rest` still land), but the caster spine (Tasks 5/7/8) and Killing Blow (Task 9) do not depend on the sidecar and stay fully wired.
5. **Two-repo finish** ([[feedback_story_repos_no_cli_flag]], [[feedback_pf_hook_scans_subrepos]]) — branch both subrepos up front (Task 0); one PR per repo; merge together.
