# Caverns & Claudes — B/X Saving Throws

**Date:** 2026-05-09
**Author:** Dev (Major Charles Emerson Winchester III)
**Source:** B/X D&D Basic Set Rulebook (Moldvay 1981) — `~/Downloads/D&D_Basic_Set_Rulebook_(B_X_ed.)_(Basic).pdf`. Saving Throws table B26; ability adjustments B7.
**Genre pack:** `caverns_and_claudes` (single pack scope)
**Status:** approved-design — pending writing-plans

## 1. Overview

PR #221 (`feat(magic): learned_v1 plugin`, merged 2026-05-09) ships B/X-canon spells (`sleep`, `charm_person`, `hold_person`, `phantasmal_force`, `web`) whose mechanical effect is gated by a saving throw. The spell catalog model (`SpellSave`) already declares `stat` and `effect` fields per spell — but no resolver consumes them, no class-by-attack-type save target table exists, and the cast path skips save resolution entirely. The narrator improvises whether sleep takes hold. Sebastien's lie-detector flag.

`learned_ops.cast()` (line 91-93) explicitly punts save resolution to its caller:

> "Caller (narration_apply) is responsible for save-vs-spells resolution (separate concern; it goes through C&C's opposed_check). cast() handles the magic-state mutations only."

This design wires that contract. The resolver is a thin call into the existing `resolve_opposed_check` primitive with the threat (POISON / SPELLS / DRAGON BREATH / etc.) standing in as a synthetic opponent whose roll equals the static save target from the B/X B26 table.

**Goal:** Make B/X saving throws a real mechanical event in C&C — visible on the dice overlay, audited via OTEL, fully class-distinct.

**Approach:** Minimal-touch (Approach 3 per the cnc-bx morale precedent). No new resolution mode, no new dispatch branch, no new dice path. The save resolver is a thin wrapper over `resolve_opposed_check` that synthesizes the threat as the opponent side. Spell catalog already has `SpellSave`; we add a `category` field. Class table is 5 ints × 4 classes per `ClassDef`, sourced from B26 verbatim.

**Deliverables:**
1. This spec (schema + resolver + content contract).
2. Server changes (Dev story) — see §4.
3. Content authoring (GM lane) — see §3, lands after Dev story merges.

## 2. Schema changes

All new fields are optional or have safe defaults; existing packs that don't migrate continue to load. `model_config = {"extra": "forbid"}` is preserved on every modified model except `NpcArchetype` (which is `extra: allow` by genre-pack convention).

### 2.1 — `SaveCategory` enum (new in `rules.py`)

```python
class SaveCategory(StrEnum):
    death_ray_or_poison = "death_ray_or_poison"
    magic_wands = "magic_wands"
    paralysis_or_stone = "paralysis_or_stone"
    dragon_breath = "dragon_breath"
    rods_staves_spells = "rods_staves_spells"
```

Five members, B/X B26 columns verbatim. Closed enum — adding a new category is a deliberate edit, not a string-typo accident.

### 2.2 — `SavingThrowsTable` (new in `rules.py`)

```python
class SavingThrowsTable(BaseModel):
    model_config = {"extra": "forbid"}
    death_ray_or_poison: int
    magic_wands: int
    paralysis_or_stone: int
    dragon_breath: int
    rods_staves_spells: int

    @model_validator(mode="after")
    def _validate(self) -> SavingThrowsTable:
        for f, v in self.model_dump().items():
            if not (2 <= v <= 20):
                raise ValueError(f"saving throw {f}={v} outside legal d20 range 2..20")
        return self

    def target_for(self, category: SaveCategory) -> int:
        return getattr(self, category.value)
```

### 2.3 — `ClassDef.saving_throws` (`character.py`)

```python
saving_throws: SavingThrowsTable | None = None
```

Optional for back-compat with non-C&C packs. Pack-load validates: if the pack has any spells with non-`none` save effect AND its `classes.yaml` has classes, then every class must declare `saving_throws` (loud-fail at load).

### 2.4 — `SpellSave.category` (`magic/spell_catalog.py`)

```python
class SpellSave(BaseModel):
    model_config = {"extra": "forbid"}
    stat: str | None                                   # existing — defender's ability mod source
    effect: str                                        # existing — none/negates/halves/partial:<text>
    category: SaveCategory = SaveCategory.rods_staves_spells   # NEW — which column of B26
```

**Default `rods_staves_spells`** matches B/X for arcane and divine spells (the catch-all magic column). Per-spell override exists for the rare Mage offensive spell that should hit the wands column (e.g., a future ray-type spell), or a Cleric spell that hits paralysis_or_stone (`Hold Person` is technically rods/staves/spells in B/X, but a future variant like `Stone to Flesh` would override).

**Validator:** if `category == dragon_breath`, `stat` must be `None` (B/X B7: WIS does not apply to Dragon Breath). Loud-fail otherwise.

### 2.5 — `NpcArchetype.saves_as_class` (`character.py`)

```python
saves_as_class: str = "Fighter"
```

NPCs save as the named class. B/X canon: monsters save as fighters by HD; we ship flat with `Fighter` as default. Per-archetype override lets the GM tag a Necromancer NPC as `saves_as_class: "Mage"` so its save vs `sleep` is the mage's 15, not the fighter's 16. The `mindless: true` flag (added by the cnc-bx morale story) takes precedence — see §4.4.

### 2.6 — Why `stat` and `category` both exist

`stat` is the defender's ability modifier source (what gets added to the d20). `category` is the save target column (what the d20 has to beat). They're orthogonal, and B/X uses them orthogonally — WIS modifies multiple categories, and Dragon Breath gets no modifier from any ability.

| Category              | Default `stat` | Notes                         |
|-----------------------|----------------|-------------------------------|
| death_ray_or_poison   | `null`         | WIS only if magical           |
| magic_wands           | `WIS`          | per B7                        |
| paralysis_or_stone    | `WIS`          | per B7                        |
| dragon_breath         | `null`         | enforced by validator         |
| rods_staves_spells    | `WIS`          | per B7                        |

The catalog's existing `stat: WIS` entries already comply. No content backfill needed beyond `category:` lines.

## 3. Content authoring (GM lane, post-Dev-story)

After Dev merges the wiring story, the GM authors the YAML below.

### 3.1 — `classes.yaml` — saving_throws block per class

Verbatim from B/X B26 (the C&C 4-class subset):

```yaml
- id: fighter
  saving_throws:
    death_ray_or_poison: 12
    magic_wands: 13
    paralysis_or_stone: 14
    dragon_breath: 15
    rods_staves_spells: 16

- id: mage
  saving_throws:
    death_ray_or_poison: 13
    magic_wands: 14
    paralysis_or_stone: 13
    dragon_breath: 16
    rods_staves_spells: 15

- id: cleric
  saving_throws:
    death_ray_or_poison: 11
    magic_wands: 12
    paralysis_or_stone: 14
    dragon_breath: 16
    rods_staves_spells: 15

- id: thief
  saving_throws:
    death_ray_or_poison: 13
    magic_wands: 14
    paralysis_or_stone: 13
    dragon_breath: 16
    rods_staves_spells: 15
```

### 3.2 — Spell catalogs — add `category` to every save block

Mage L1 (`spells/cc_arcane_l1.yaml`):

| Spell           | Category              | Stat | Effect       |
|-----------------|-----------------------|------|--------------|
| magic_missile   | (n/a — `stat: null, effect: none`) | — | — |
| sleep           | rods_staves_spells    | WIS  | negates      |
| charm_person    | rods_staves_spells    | WIS  | negates      |
| hold_portal     | (no save)             | —    | none         |
| read_languages  | (no save)             | —    | none         |
| read_magic      | (no save)             | —    | none         |
| shield          | (no save)             | —    | none         |
| ventriloquism   | rods_staves_spells    | WIS  | negates      |
| (… others per B/X canon)  |          |      |              |

Cleric L1 (`spells/cc_divine_l1.yaml`):

| Spell                 | Category              | Stat | Effect       |
|-----------------------|-----------------------|------|--------------|
| cure_light_wounds     | (no save)             | —    | none         |
| detect_evil           | (no save)             | —    | none         |
| light                 | rods_staves_spells    | WIS  | negates      |
| protection_from_evil  | (no save)             | —    | none         |
| purify_food_and_drink | (no save)             | —    | none         |
| remove_fear           | (no save)             | —    | none         |
| resist_cold           | (no save)             | —    | none         |
| (… others per B/X canon)        |          |      |              |

Default `category: rods_staves_spells` is the type for every learned_v1 spell that has any save — content authoring only needs to override for the rare future case.

### 3.3 — `caverns_sunden/` — `saves_as_class` on archetypes that aren't fighters

Pass through caverns_sunden NPC archetypes; tag `saves_as_class` where canon supports a non-Fighter save:

- **Necromancer / cult-leader / spellcaster archetypes** → `saves_as_class: Mage`
- **Priest / inquisitor / undead-shepherd archetypes** → `saves_as_class: Cleric`
- **Burglar / scout / spy archetypes** → `saves_as_class: Thief`
- Everything else (warriors, brigands, beasts, dragons-as-monsters): leave default (`Fighter`)

`mindless: true` archetypes (skeletons, golems, oozes — already tagged by cnc-bx morale story) skip the save entirely for mind-affecting spells (§4.4); their `saves_as_class` is irrelevant for those spells but still applies to non-mind-affecting saves like Dragon Breath.

## 4. Server wiring (Dev story scope)

The filed Dev story covers everything in this section. Estimated **2–3 points**.

### 4.1 — Pydantic model changes

- `rules.py`: add `SaveCategory`, `SavingThrowsTable`. (See §2.1, §2.2.)
- `character.py`: add `ClassDef.saving_throws`, `NpcArchetype.saves_as_class`. (See §2.3, §2.5.)
- `magic/spell_catalog.py`: add `SpellSave.category` with default + dragon-breath validator. (See §2.4.)

### 4.2 — Pack-load validation

Loud-fail at pack-load if:
- Any class declares `saving_throws` with a value outside `2..20`.
- Pack has any spell with `save.effect != "none"` AND its `classes.yaml` has classes AND any class is missing `saving_throws`.
- Any `SpellSave` has `category: dragon_breath` with non-null `stat`.

### 4.3 — Save resolver: `resolve_save` (new in `game/saves.py`)

```python
@dataclass(frozen=True)
class SaveResult:
    defender_actor: str
    category: SaveCategory
    target: int
    roll: int
    mod: int
    total: int
    shift: int
    tier: RollOutcome
    threat_label: str   # for OTEL + dice-overlay chip ("POISON", "SPELLS", "DRAGON BREATH")


def resolve_save(
    *,
    defender: EncounterActor,
    defender_class: str,           # ClassDef.display_name; for NPCs, NpcArchetype.saves_as_class
    pack_classes: Mapping[str, ClassDef],
    category: SaveCategory,
    ability: str | None,           # SpellSave.stat — None means no ability modifier
    threat_label: str,             # human-readable for the dice-overlay chip
    rng: Random,
) -> SaveResult:
    """B/X save: defender rolls d20 + ability_mod, beats class[category] target.

    Implementation: synthesize a frozen ``EncounterActor`` whose
    per_actor_state.stats produces a modifier of zero, give the
    'opponent' a fixed roll equal to the table target, and call
    ``resolve_opposed_check``. The shift, tier, and OTEL fall out of
    the existing primitive."""
```

The resolver is a thin layer over `resolve_opposed_check`. The "opponent" is a one-shot synthetic `EncounterActor("threat:" + category.value)` with `per_actor_state={"stats": {}}` and `opponent_default_stats` patched to give a 0 modifier; opponent's d20 is hard-pinned to the table target via a kwarg path (see §4.5 for the small surface change to `resolve_opposed_check` to admit a `fixed_opponent_roll: int | None` parameter).

### 4.4 — Mindless gate (mind-affecting spells)

Spell catalog gets one new optional field: `requires_mind: bool = False`. When `True`, targets with `NpcArchetype.mindless = True` are skipped before the save call entirely (no roll, no save, the spell does nothing to them — B/X canon: undead and mindless constructs are immune to charm/sleep/hold).

The mindless flag was added by the in-flight cnc-bx morale story (commit `2435762`). Composition is clean: morale skips mindless opponents from breaking; saves skip mindless targets from being affected by mind-control spells. Both are reads of the same flag.

### 4.5 — Tiny `resolve_opposed_check` extension

Add an optional kwarg:

```python
def resolve_opposed_check(
    *,
    ...,
    fixed_opponent_roll: int | None = None,   # NEW
    ...,
) -> OpposedRollResult:
```

When `fixed_opponent_roll` is passed, the resolver skips rolling for the opponent and uses the passed value as the d20 face. Validator: `1..20`. Behavior is otherwise identical. This is the minimum-incision surgery to let saves ride the existing primitive without faking an opponent roll inside the caller. Five-line change.

### 4.6 — narration_apply integration

Where the just-merged `learned_v1` working flows through `narration_apply` (the spot the plugin docstring punts to), add:

```python
if working.spell_id is not None:
    spell = catalog.get(working.spell_id)
    cast_result = learned_ops.cast(magic_state, working=working)
    for target_actor in working.targets:
        target_archetype = lookup_archetype(target_actor)  # NPCs have one; PCs return None
        if spell.requires_mind and target_archetype and target_archetype.mindless:
            emit_save_skipped_span(target_actor, "mindless")
            continue   # spell has no effect; do not apply spell deltas
        if spell.save.effect == "none":
            apply_spell_effect(target_actor, spell, RollOutcome.Fail)   # auto-hit
            continue
        save = resolve_save(
            defender=target_actor,
            defender_class=class_for_actor(target_actor),
            pack_classes=pack.classes_by_name,
            category=spell.save.category,
            ability=spell.save.stat,
            threat_label=spell.name.upper(),  # "SLEEP", "CHARM PERSON"
            rng=session_rng,
        )
        emit_saving_throw_span(save)
        apply_spell_effect(target_actor, spell, save.tier)   # tier-aware
```

`apply_spell_effect` is a new free function that maps `(spell, RollOutcome)` to mechanical deltas. The mapping respects `SpellSave.effect`:

| `effect`   | tier=CritSuccess | Success | Tie | Fail | CritFail |
|------------|------------------|---------|-----|------|----------|
| `none`     | (full effect, regardless — auto-hit) | full | full | full | full+bonus |
| `negates`  | no effect, defender shrugs | no effect | tied — narrator-fiat half | full effect | full + status |
| `halves`   | no effect | quarter | half | full | full + status |
| `partial:` | narrator branches on tier per effect_template | | | | |

`partial:` deferred to v1.5 (most common partial shapes can be authored as `negates` or `halves` with prose flavor).

### 4.7 — OTEL span: `encounter.saving_throw_resolved`

| Span | Attributes |
|---|---|
| `encounter.saving_throw_resolved` | defender_actor, defender_class, category, ability, threat_label, target, roll, mod, total, shift, tier, mindless_gate (bool — true if skipped before roll), spell_id, encounter_type |

Fires once per save attempt. Mindless-skipped targets fire with `mindless_gate=true` and `tier=null` so the GM panel can show "skipped: mindless" rather than blank. CLAUDE.md OTEL principle: missing span → subsystem isn't engaged → bug.

### 4.8 — Dice overlay (UI side)

The existing 3D dice overlay (ADR-074, ADR-075) renders two dice for opposed checks: the player's settled die and the opponent's chip. Saves reuse the same widget — the opponent chip displays `threat_label` (e.g., "SLEEP — 15") instead of "Carl the Drake — 14". No client wiring change beyond a passthrough field on the dice-result message; the chip already shows the opponent's `total` and the result tier. The label is the only visible difference.

This is the entirety of the UI surface for v1. No new screens, no new modals.

### 4.9 — Out of Dev story scope

- **Level scaling.** B/X Basic itself is flat (B26 footnote); per-level adjustment is Expert-set behavior. Add later when XP advancement crosses a level boundary in C&C — extend `SavingThrowsTable` to `dict[level, SavingThrowsTable]` or add a `saves_by_level` block.
- **Saves vs traps and environment.** Traps subsystem is a separate B/X brainstorm; this design wires the resolver and table only.
- **Player-side voluntary failure.** B/X allows characters to voluntarily fail a save vs a beneficial spell. Defer.
- **Magic items granting save bonuses.** Cloak of Protection, Ring of Protection — defer to magic-item story.
- **Pretty result UX (success animation, status icon flash).** v1 ships the chip + dice settle; polish later.

## 5. Testing strategy

### 5.1 — Schema tests (new `tests/genre/test_models/test_saving_throws.py`)
- `SavingThrowsTable` rejects values <2 and >20.
- `SaveCategory` enum closed (5 members).
- `SpellSave.category=dragon_breath` with non-null `stat` raises.
- `SpellSave.category` defaults to `rods_staves_spells`.

### 5.2 — Pack-load tests (`tests/genre/test_pack_load.py` extension)
- C&C: every class in `classes.yaml` has `saving_throws` populated.
- Targets match B26 verbatim (Fighter Spells = 16, Mage Spells = 15, Cleric Spells = 15, Thief Spells = 15).

### 5.3 — Resolver tests (new `tests/game/test_saves.py`)
- Mage rolling d20=10 + WIS=+1 vs target 15: total 11, shift -4, Fail.
- Mage rolling d20=20: nat20 → CritSuccess regardless of target.
- Mage rolling d20=1: nat1 → CritFail regardless.
- Fighter rolling vs Spells (target 16) and Mage rolling vs Spells (target 15) on identical d20+mod produce different shifts.
- Dragon Breath save with `ability=None` ignores defender's WIS score entirely.
- Synthetic-opponent path: `fixed_opponent_roll=15` makes opponent's roll deterministic.

### 5.4 — Integration tests (new `tests/integration/test_save_resolution_e2e.py`)
- Mage casts `sleep` on 1 fighter NPC: save fires, OTEL span emits, tier branches correct.
- Mage casts `sleep` on 1 mindless skeleton NPC: save SKIPPED, OTEL span fires with `mindless_gate=true`, no mechanical effect.
- Mage casts `magic_missile` (no save): no save fires, full effect applied.
- Mage casts `charm_person` on a `saves_as_class: Cleric` NPC: target lookup hits Cleric's 15 (not Fighter's 16).

### 5.5 — OTEL tests (`tests/telemetry/`)
- `encounter.saving_throw_resolved` emits exactly once per save call with required attrs.
- Span absent on `effect: none` spells.
- Span emits with `mindless_gate=true` and null tier when skipped.

### 5.6 — Playtest exit criteria (caverns_sunden)
1. Mage casts `sleep` on a goblin patrol; the dice overlay shows the goblin's d20 chip labeled `SLEEP — 15` and the goblin's d20 settled result. Some succeed, some fail.
2. Mage casts `sleep` on a mixed group with skeletons and goblins; the GM panel shows skeletons skipped (`mindless_gate=true`), goblins rolling.
3. Cleric casts `hold_person` on a brigand; the brigand saves vs Spells at 16 (Fighter target), not the Cleric's 15.
4. GM panel shows `encounter.saving_throw_resolved` spans with correct attributes for every save.

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `fixed_opponent_roll` extension breaks existing opposed_check call sites | Low — new kwarg defaults to None | Existing tests must remain green; add explicit None test |
| Spell catalog migration: every spell needs `category` | Low — default + content authoring lane | Default `rods_staves_spells` covers every existing learned_v1 spell that has a save; new field is optional in YAML |
| Narrator prose claims "the troll resists your sleep!" when the troll is mindless | Medium — narrator improvises | OTEL span (`mindless_gate=true`) gives GM panel the lie-detector; if prose drifts, file a narrator-prompt-zone story to add invariant |
| Saves vs Death Ray with magical poison — when does WIS apply? | Low — B7 says "depending" | v1 ships with `stat: null` for `death_ray_or_poison`; per-spell override sets `stat: WIS` for magical poisons. Punted to spell author judgment, not a system rule |
| Per-level save scaling needed before XP advancement lands | Low — Basic is flat | When advancement crosses a level, extend `SavingThrowsTable` to per-level form; doesn't break v1 |
| Synthetic opponent leaks to OTEL `encounter.opposed_roll_resolved` and pollutes combat dashboards | Medium — same span, different intent | Saves emit `encounter.saving_throw_resolved` (separate span). The `resolve_opposed_check` call path stays clean because the save resolver wraps it and emits its own span |

## 7. Out of scope

- Saves vs traps (B/X B22) — separate brainstorm.
- Saves vs environmental hazards (falling, drowning) — separate.
- Per-level save scaling (B/X Expert) — defer until XP advancement crosses a level.
- Magic-item save bonuses — defer to magic-item story.
- Voluntary save failure on beneficial spells — defer.
- Player-rolled physical save dice (the player picking up dice and rolling for a fellow player's save) — v1 is server-side d20 only; defer to a multiplayer save-rolling story.
- Generalizing saves to other genre packs — only adopt when a second pack actually wants saves; the model fields are optional so non-C&C packs continue to load.

## 8. Sequencing

1. **This story (saves).** Schema + resolver + content + OTEL + tests. Filed as one Dev story.
2. **Story #N — saves vs traps.** Reuses `resolve_save` with `category=death_ray_or_poison` and a trap-specific threat label. Trivial extension.
3. **Story #N — magic-item save bonuses.** Adds an additive modifier path on the resolver (`extra_mod: int = 0`).
4. **Story #N — per-level save scaling.** Schema migration on `SavingThrowsTable`; touched when XP advancement crosses a level boundary in C&C.

The cnc-bx morale story (in flight on a parallel session) is independent — different file, different subsystem, no merge collision. They share the `mindless` flag (already merged via PR #220's commit `2435762`) but in non-conflicting ways.

## 9. Decisions

Each row records a decision made during brainstorming, with the alternative and why it was declined.

| # | Decision | Alternative | Why declined |
|---|---|---|---|
| 1 | Reuse `resolve_opposed_check` with synthetic opponent (`fixed_opponent_roll`) | Build a parallel `_classify_legacy_tier`-based one-side resolver | The just-merged plugin docstring (`learned_ops.py:91-93`) explicitly says "goes through C&C's opposed_check"; honoring stated intent beats inventing a parallel primitive. Also: the same dice grammar (d20 + (score-10)/2 mod, shift bands) gives criticals for free |
| 2 | Add `SaveCategory` enum + `category` field to `SpellSave` | Use the existing `stat` field as both ability and category | They're orthogonal in B/X (WIS modifies multiple categories; Dragon Breath gets none); collapsing them loses canonical fidelity and the dragon-breath validator |
| 3 | Default `category: rods_staves_spells` on `SpellSave` | Require explicit category on every spell | Every existing learned_v1 spell with a save lands here; default minimizes content backfill churn |
| 4 | NPCs save by `saves_as_class: str = "Fighter"` | NPCs save by HD (B/X canon: monsters save as fighters by HD) | C&C is single-tier flat for v1; HD-based save scaling is a B/X Expert feature. Save-as-Fighter is the right floor; per-archetype override handles the casters and rogues |
| 5 | Mindless gate skips the save entirely for mind-affecting spells | Mindless rolls and auto-fails | B/X canon: mindless creatures aren't IMPACTED by sleep/charm — not "easily impacted." Skipping the roll is faithful and gives a cleaner OTEL signal |
| 6 | One-line `requires_mind: bool` on Spell | A taxonomy of damage-type tags (mind/fire/cold/poison/...) | Bigger surface, no other consumer yet. Punt the taxonomy to the next genre that needs it |
| 7 | Crit bands inherited from `_tier_from_shift` give save criticals (CritSuccess save = bonus, CritFail = worse) | Binary save/no-save per B/X canon | SOUL.md "Tabletop first, then better" axis. Sebastien's GM panel sees the shift and tier; the narrator can flavor the critical (a CritSuccess save vs sleep = "your eyes flash open as the spell shatters against your will"). Free with the existing primitive |
| 8 | Five-line `fixed_opponent_roll` kwarg on `resolve_opposed_check` | Build the synthetic opponent's d20 elsewhere and let it fall through naturally | The opponent's d20 is currently rolled inside `resolve_opposed_check`; the simplest path is to let callers pin it. No surgery on the call path |
| 9 | UI is the existing dice overlay with relabeled chip | New "saving throw" modal | "Just have the little circle say POISON instead of Monster Guy." Same widget, different noun. Zero new client surface |
| 10 | Saves are server-side d20 only in v1; no player-rolled dice | Player rolls their own save dice | Multiplayer save-rolling raises sealed-letter / who-rolls-for-allies questions that don't belong in a v1 mechanical-fidelity story. Defer to a save-rolling-coordination story when playtest pressure surfaces it |

## 10. References

- B/X D&D Basic Set Rulebook (Moldvay 1981) — `~/Downloads/D&D_Basic_Set_Rulebook_(B_X_ed.)_(Basic).pdf`. Saving Throws table: B26. Ability adjustments (WIS): B7.
- ADR-001 — Claude CLI Only. Constrains save resolution to deterministic server-side dice; narrator does not call tools.
- ADR-074 — Dice Resolution Protocol — Player-Facing Rolls via WebSocket.
- ADR-075 — 3D Dice Rendering — Three.js + Rapier Physics Overlay.
- `sidequest-server/sidequest/game/opposed_check.py` — `resolve_opposed_check`, `_ability_modifier`, `_stat_score_from_actor`, `_tier_from_shift`. Save resolver rides this primitive.
- `sidequest-server/sidequest/server/narration_apply.py:2620-2661` — `_classify_legacy_tier`, `_opposed_dc`. Reference shape for one-side d20-vs-DC.
- `sidequest-server/sidequest/magic/learned_ops.py:91-93` — explicit save-resolution handoff to caller.
- `sidequest-server/sidequest/magic/spell_catalog.py` — `SpellSave` already has `stat` and `effect`; this spec adds `category`.
- `sidequest-server/sidequest/genre/models/character.py` — `ClassDef`, `NpcArchetype` (with `mindless` from PR #220).
- `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml` — target file for §3.1 saving_throws blocks.
- `sidequest-content/genre_packs/caverns_and_claudes/spells/cc_arcane_l1.yaml`, `cc_divine_l1.yaml` — target files for §3.2 category fields.
- `docs/superpowers/specs/2026-05-08-cnc-bx-class-beats-morale-design.md` — sister B/X story (in flight, parallel session). Mindless flag and OTEL pattern shared.
