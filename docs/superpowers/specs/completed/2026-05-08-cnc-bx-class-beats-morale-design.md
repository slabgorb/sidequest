# Caverns & Claudes — B/X Class-Distinct Beats and Morale

**Date:** 2026-05-08
**Author:** GM (architect-flavored brainstorm)
**Source:** B/X D&D Basic Set Rulebook (Moldvay 1981) — `~/Downloads/D&D_Basic_Set_Rulebook_(B_X_ed.)_(Basic).pdf`
**Genre pack:** `caverns_and_claudes` (single pack scope)
**Status:** approved-design — pending writing-plans

## 1. Overview

This design ports two B/X mechanics into Caverns & Claudes:

- **(A) Class-distinct encounter beats.** B/X-flavored signature beats added to the existing `combat` confrontation pool. Each new beat carries an optional `class_filter`. Per-class `encounter_beat_choices` whitelist in `classes.yaml` is the runtime gate.
- **(C) Morale.** Optional `morale` block on `ConfrontationDef` (combat only). When a trigger fires, server rolls 2d6 against `score`; opponents that fail break off (chase escalation, surrender, or rout). `mindless: true` on an NPC archetype short-circuits the check.

**Goal:** Make C&C's four classes feel mechanically distinct in encounters, and give combat a way to end without a TPK.

**Why one design, not two:** Class-distinct beats and morale are tightly coupled — morale's `flee_consequence: chase` only resolves cleanly because the combat pool now includes the right shape of beats (e.g., `flee` is universal; class-specific signature beats determine what kept the fight going up to the morale check).

**Approach:** Minimal-touch — extend three existing pydantic models with optional fields rather than introducing new subsystems. Smallest blast radius; smallest Dev story; biggest playtest win per dollar. (Approaches 1 and 2 — schema-extension and new-subsystem — were considered and declined; see §9 Decisions.)

**Deliverables:**
1. This spec (content + server wiring contract).
2. Server changes (Dev story) — see §4.
3. Content authoring (GM lane) — see §3, lands after Dev story merges.

## 2. Schema changes

All new fields are optional; existing packs that don't migrate continue to load. `model_config = {"extra": "forbid"}` is preserved on every modified model.

### 2.1 — `BeatDef` (`sidequest-server/sidequest/genre/models/rules.py`)

```python
class_filter: list[str] | None = None
```

Validator: if not `None`, must be non-empty (loud-fail at pack-load on `[]`).

YAML:
```yaml
- id: cleave
  label: Cleave
  kind: strike
  base: 3
  stat_check: STR
  class_filter: [Fighter]
  effect: "Wide swing — opens up space against multiple foes"
  narrator_hint: "Two-handed sweep, momentum carrying through to the next stance."
```

Semantics:
- `None` or omitted → universal (e.g., `attack`, `defend`, `flee`).
- Non-empty list → only those classes see this beat at selection.
- Empty list `[]` → loud-fail at pack-load.

### 2.2 — `MoraleDef` (new model in `rules.py`)

```python
class MoraleTrigger(StrEnum):
    first_blood = "first_blood"
    half_killed = "half_killed"
    intimidated = "intimidated"
    leader_killed = "leader_killed"


class FleeConsequence(StrEnum):
    chase = "chase"
    surrender = "surrender"
    rout = "rout"


class MoraleDef(BaseModel):
    model_config = {"extra": "forbid"}
    score: int = 8                    # 2..12, B/X canon
    triggers: list[MoraleTrigger]     # non-empty
    flee_consequence: FleeConsequence = FleeConsequence.chase

    @model_validator(mode="after")
    def _validate(self) -> MoraleDef:
        if not (2 <= self.score <= 12):
            raise ValueError(f"morale score {self.score} not in 2..12")
        if not self.triggers:
            raise ValueError("morale.triggers must be non-empty")
        return self
```

### 2.3 — `ConfrontationDef` (`rules.py`)

```python
morale: MoraleDef | None = None
```

`None`/omitted → no morale checks fire (back-compat for chase, negotiation, and any pack that hasn't migrated).

### 2.4 — `NpcArchetype` (`sidequest-server/sidequest/genre/models/character.py`)

```python
mindless: bool = False
```

NpcArchetype already allows extras. Making `mindless` an explicit field beats implicit per CLAUDE.md fail-loud principle. When `mindless: true`, the NPC is skipped during morale checks (B/X canon — no Intelligence score, no morale check).

### 2.5 — `ClassDef` — no schema change

`encounter_beat_choices: list[str]` and `magic_access: str | None` already exist (`character.py:90-91`) and are documented as "reserved for future class-specific subsystems." This design wires them up.

## 3. Content authoring (GM lane, post-Dev-story)

After Dev merges the wiring story, the GM authors the YAML below.

### 3.1 — Beat slate (in `rules.yaml` `combat` confrontation pool)

**Universal beats** (no `class_filter`): `attack`, `defend`, `flee`.

**Re-tagged existing beats:**
- `shield_bash` → `class_filter: [Fighter, Cleric]`
- `feint` → `class_filter: [Fighter, Thief]`

**New beats:**

| id | label | kind | stat | class_filter | flavor |
|---|---|---|---|---|---|
| `cleave` | Cleave | strike | STR | [Fighter] | Felling-blow follow-through |
| `parry` | Parry | brace | DEX | [Fighter] | Trade momentum for a guarantee |
| `backstab` | Backstab | strike | DEX | [Thief] | High `base`; setup via `Off-Balance` tag |
| `sneak` | Slip Behind | angle | DEX | [Thief] | Grants `Off-Balance` tag |
| `cast_cantrip` | Cast Cantrip | strike | INT | [Mage] | Free; small base |
| `cast_spell` | Cast Spell | strike | INT | [Mage] | Consumes 1 from `spell_slots` ledger |
| `turn_undead` | Turn Undead | push | WIS | [Cleric] | Drives off `mindless: true` undead |
| `pray` | Pray for Aid | brace | WIS | [Cleric] | Edge recovery |

### 3.2 — `classes.yaml` — encounter_beat_choices and magic_access

```yaml
- id: fighter
  encounter_beat_choices: [attack, defend, flee, shield_bash, cleave, parry, feint]

- id: mage
  encounter_beat_choices: [attack, defend, flee, cast_cantrip, cast_spell]
  magic_access: innate_v1

- id: cleric
  encounter_beat_choices: [attack, defend, flee, shield_bash, turn_undead, pray]
  magic_access: innate_v1

- id: thief
  encounter_beat_choices: [attack, defend, flee, feint, backstab, sneak]
```

### 3.3 — `rules.yaml` — morale block + housekeeping

Add to the `combat` confrontation only (chase, negotiation untouched in v1):
```yaml
morale:
  score: 8
  triggers: [first_blood, half_killed, intimidated, leader_killed]
  flee_consequence: chase
```

Sync stale top-level fields:
```yaml
allowed_classes: [Fighter, Mage, Cleric, Thief]   # was [Delver]
```

Drop stale `custom_rules` flags that contradict the post-pivot reality:
```yaml
custom_rules:
  treasure_as_xp: "true"
  keeper_awareness: "true"
  resource_ticks: "true"
  extraction_phase: "true"
  encumbrance: "strict"
  injuries: "permanent"
  # REMOVED: no_classes, no_races, no_spells (contradict the B/X pivot in magic.yaml)
```

### 3.4 — `worlds/caverns_sunden/` — archetype mindless tags

Pass through caverns_sunden NPC archetypes; tag `mindless: true` where canon supports:
- Skeletons, zombies, animated armor, oozes, golems, mind-controlled thralls → `mindless: true`
- Goblins, kobolds, brigands, cultists, dragons, mages → leave default (`false`)

This is per-world content work; the spec commits to doing it for `caverns_sunden` as part of the GM authoring pass that follows the Dev story.

## 4. Server wiring (Dev story scope)

The filed Dev story covers everything in this section. Estimated **3–5 points**.

### 4.1 — Pydantic model changes

- `rules.py`: add `BeatDef.class_filter`, new `MoraleDef`, `ConfrontationDef.morale`. (See §2.)
- `character.py`: add `NpcArchetype.mindless`. (See §2.4.)

### 4.2 — Pack-load validation

Loud-fail at pack-load if:
- A beat's `class_filter` references a class not in `classes.yaml`.
- A class's `encounter_beat_choices` references a beat ID not in any confrontation pool.
- A class's `encounter_beat_choices` is empty for a class that participates in any confrontation.
- `MoraleDef.triggers` is empty.

### 4.3 — Beat filtering at selection time

Replace direct iteration over `confrontation.beats` in narration paths with a single helper:

```python
def beats_available_for(
    confrontation: ConfrontationDef,
    character: Character,
    spell_slots_remaining: float,
) -> list[BeatDef]:
    class_name = character.char_class
    class_def = lookup_class(class_name)
    if not class_def.encounter_beat_choices:
        raise PackError(f"class {class_name!r} has empty encounter_beat_choices")
    pool = [
        b for b in confrontation.beats
        if b.class_filter is None or class_name in b.class_filter
    ]
    pool = [b for b in pool if b.id in class_def.encounter_beat_choices]
    # Resource gating: cast_spell requires available spell slot.
    pool = [
        b for b in pool
        if b.id != "cast_spell" or spell_slots_remaining >= 1.0
    ]
    return pool
```

Find the call site (likely in `server/narration_apply.py` or `agents/narrator.py` context-builder) and replace the direct iteration with this helper.

### 4.4 — Morale check function

New module: `sidequest-server/sidequest/game/morale.py`. Single entry function:

```python
def maybe_check_morale(
    confrontation: ConfrontationDef,
    opponent_side_state: OpponentSideState,
    trigger: MoraleTrigger,
    rng: Random,
) -> MoraleOutcome:
    """Returns MoraleOutcome.stay or MoraleOutcome.flee.
    No-op (Stay) if confrontation.morale is None or trigger not in morale.triggers.
    Skips opponents flagged mindless=True (the side stays as long as
    any non-mindless opponent is still standing; mindless opponents
    keep fighting even when allies break)."""
```

**Trigger emission points** (in `narration_apply.py` after beat resolution):

| Trigger | When |
|---|---|
| `first_blood` | Opponent side count drops by 1 from initial (fires once per side per confrontation) |
| `half_killed` | Opponent side count crosses ≤ ⌊initial/2⌋ |
| `leader_killed` | An opponent tagged `is_leader: true` is downed |
| `intimidated` | Narrator JSON sidecar (ADR-039) carries `morale_event: intimidated` |

**Roll:** 2d6, **stay if total ≤ score**, flee if total > score. **Per-side**, not per-opponent (B/X canon).

**Mindless handling:** mindless opponents are filtered out of the morale roll's "side considered for breaking." If any non-mindless opponent remains and the side fails morale, only the non-mindless opponents flee; mindless ones stay and fight.

**Flee outcome** (`flee_consequence`):
- `chase` → confrontation escalates to the chase confrontation type.
- `surrender` → opponents drop weapons; combat ends; narrator handles disposition.
- `rout` → opponents flee scattered; combat ends without chase.

### 4.5 — `cast_spell` consumption — plug-in point for memorization story

When a beat with `id == "cast_spell"` resolves successfully: decrement `spell_slots` resource ledger by 1.0. If ledger is at 0, the beat is **filtered out at selection time** by `beats_available_for` (§4.3). At resolution time, if somehow selected with empty ledger, raise `PackError`. **No silent fallback.**

This is the seam for future story #2 (B/X memorization). Once `character.memorized_spells` exists, the filter additionally requires a memorized spell of the right level. The plug-in shape is: extend the filter, not replace it.

### 4.6 — OTEL spans (mandatory per CLAUDE.md OTEL principle)

Two new spans in `sidequest-server/sidequest/telemetry/spans/combat.py`:

| Span | Attributes |
|---|---|
| `confrontation.beat_filter` | character_class, confrontation_type, pool_size, filtered_size, beat_ids, mindless_opponents_count |
| `confrontation.morale_check` | trigger, score, roll, total, outcome (stay/flee), opponent_side_label, mindless_opponents_count, flee_consequence |

Both fire on every relevant call, never suppressed. Missing spans → GM panel shows the subsystem isn't engaged → bug.

### 4.7 — Narrator prompt zone invariant

The narrator improvises actions outside the schema unless told not to. Add a one-line invariant to the per-turn prompt zone (per ADR-009 attention-aware zones; near the existing turn-context block):

> "The player's available actions for this turn are listed above. Do not narrate actions outside that list as performed."

This is a single-line prompt edit in the narrator agent's context-builder. Belongs in this Dev story, not as content authoring — the prompt template lives in server code.

### 4.8 — Out of Dev story scope

- Memorization wiring (story #2 — separate; this story creates the seam at §4.5).
- New confrontation types (chase, negotiation untouched in v1).
- Player-side morale (B/X canon: players choose).
- Race-as-class (4 classes only).
- Combat-effect math rebalancing (`base` values match existing C&C tier).

## 5. Testing strategy

### 5.1 — Pack-load tests (`tests/genre/test_pack_load.py`)
- C&C combat confrontation has `morale` block with non-empty triggers.
- Every `class_filter` entry references an existing class.
- Every `encounter_beat_choices` entry references an existing beat ID.
- No class has empty `encounter_beat_choices`.

### 5.2 — Schema tests (new `tests/genre/test_models/test_morale.py`)
- `MoraleDef` rejects empty `triggers`.
- `MoraleDef` rejects `score < 2` or `score > 12`.
- `BeatDef` rejects empty `class_filter` (must be `None` or non-empty).

### 5.3 — Beat-filter tests (`tests/server/test_apply_beat.py` extension)
- Fighter at combat sees [attack, defend, flee, shield_bash, cleave, parry, feint] — exactly.
- Mage at combat does NOT see shield_bash, cleave, backstab.
- Mage with empty `spell_slots` ledger does NOT see `cast_spell`.

### 5.4 — Morale tests (new `tests/game/test_morale.py`)
- 2d6 outcomes deterministic via injected RNG: `stay` ≤ score; `flee` > score.
- Mindless opponents on a fleeing side stay and fight.
- `first_blood` fires exactly once per side per confrontation.
- `half_killed` fires when opponent count crosses ≤ ⌊initial/2⌋.
- `leader_killed` fires only when an `is_leader: true` opponent goes down.
- `intimidated` fires only when narrator sidecar carries the explicit signal.
- No morale check on a confrontation with `morale: None`.

### 5.5 — OTEL tests (existing pattern in `tests/telemetry/`)
- `confrontation.beat_filter` emits on every selection call with required attrs.
- `confrontation.morale_check` emits exactly once per trigger event with the rolled value.

### 5.6 — Playtest exit criteria (caverns_sunden)
1. Each of the four classes shows a visibly different beat menu in combat (verified via `confrontation.beat_filter` span).
2. A multi-NPC combat against goblins ends in flight or surrender at least once across a 5-turn fight (verified via `confrontation.morale_check` span; opponent side transitions to fleeing/surrendering).
3. Combat against skeletons (mindless) does NOT trigger morale checks for the mindless side (verified via span absence + `mindless_opponents_count` attr).
4. A Mage casting `cast_spell` shows a `spell_slots` ledger drop from 1.0 → 0.0 (regression check tied to 47-2 PARTIAL-PASS).

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Schema break in other packs | Low — fields are optional | Pack-load tests stay green for non-C&C packs; back-compat: `morale: None` = no checks |
| Beat-filter performance | Very low — small lists | Not optimizing pre-emptively |
| Narrator improvises restricted moves ("the Mage cleaves") | Medium — Claude doesn't read schema | Narrator prompt zone gets a one-line invariant: "the player's available actions for this turn are listed; do not narrate actions outside that list as performed" |
| `intimidated` trigger relies on narrator sidecar | Medium — sidecars drift | Wired through ADR-039 sidecar block; tested with fixture sidecar event |
| Memorization story #2 changes `cast_spell` filter shape | Medium — small surface | §4.5 plug-in point: extend the filter, don't replace it |
| `turn_undead` filter-by-opponent scope creep | Low — easy to descope | If Dev finds it unwieldy, drop the conditional; Cleric always sees turn_undead in v1 |

## 7. Out of scope

- B/X spell **memorization** (story #2 — separate brainstorm; this design creates the seam at §4.5).
- B/X **reaction rolls** — separate brainstorm.
- B/X **saving throws** — separate brainstorm.
- B/X **wandering monster clock + light tracking** — separate brainstorm.
- B/X **race-as-class** (Dwarf/Elf/Halfling) — separate brainstorm if/when scope opens.
- B/X **retainers** — separate brainstorm (Tier 2, larger).
- B/X **alignment** (Law/Neutral/Chaos) — separate brainstorm if/when product wants it.
- Generalizing morale or class-filter to other genre packs — only adopt when a second pack actually needs it.
- Player-side morale — B/X canon: players choose.
- Combat-effect math rebalancing.

## 8. Sequencing

1. **This story** — schema + wiring + content + OTEL + tests. Filed as one Dev story.
2. **Story #2 (B/X memorization)** — extends `cast_spell` filter to require `memorized_spells` non-empty for the level. Plug-in point already designed in §4.5.
3. **Future Tier 1 brainstorms** — reaction rolls, saving throws, dungeon clock — independent; can be ordered by playtest pressure.

## 9. Decisions

Each row records a decision made during brainstorming, with the alternative and why it was declined.

| # | Decision | Alternative | Why declined |
|---|---|---|---|
| 1 | Bundle A (class beats) and C (morale) into one design | Ship A first, C later | They're tightly coupled — morale's `flee_consequence` only resolves cleanly with class-aware beats; one Dev story is smaller than two |
| 2 | Mage/Cleric beats are spell-agnostic until story #2 | Beats consume `spell_slots` from existing ledger only | Cleanest staging; `cast_cantrip` is free, `cast_spell` consumes a slot — memorization adds named-spell binding without reshape |
| 3 | Stay at 4 classes (Fighter/Mage/Cleric/Thief) | Expand to B/X 7 (race-as-class) | Smallest scope; race-as-class is a separate brainstorm; sync `allowed_classes` to match `classes.yaml` |
| 4 | Class-filter IDs filter the universal pool | Per-class full BeatDef definitions; or fully per-class confrontations | Single source of truth (the pool); minimal authoring duplication |
| 5 | Morale fires on canonical B/X triggers + intimidation | Continuous morale every round; or single endpoint check | Faithful to B/X cadence + Living World responsiveness without round-by-round breakage |
| 6 | Spec covers content + Dev wiring | Author content only and let Dev figure out wiring | Matches "no half-wired features" CLAUDE.md principle |
| 7 | Approach 3 (minimal-touch) over Approach 2 (new subsystem) | Approach 2 — `morale.yaml` + new subsystem modules | C&C is one of 11 packs; no second consumer yet; premature generalization burns Sprint 3 closeout budget. Approach 2 becomes natural refactor when a second pack needs morale |
| 8 | `mindless: true` short-circuits morale on individual opponents, not whole sides | Whole-side mindless flag | Mixed groups are common (skeletons + necromancer); per-archetype is more faithful and only marginally harder |

## 10. References

- B/X D&D Basic Set Rulebook (Moldvay 1981) — `~/Downloads/D&D_Basic_Set_Rulebook_(B_X_ed.)_(Basic).pdf`. Morale: B27 (Optional). Class abilities: B9–B10. Monster reactions: B24.
- ADR-039 — Narrator Structured Output (JSON Sidecar Block). Used by `intimidated` trigger.
- ADR-033 — Confrontation engine + resource pools. Foundation for the existing combat ConfrontationDef.
- ADR-067 — Unified Narrator Agent. Narrator prompt zone modification (§4.7) lives here.
- ADR-009 — Attention-aware prompt zones. Insertion point for the §4.7 invariant.
- `sidequest-server/sidequest/genre/models/rules.py` — BeatDef, MetricDef, ConfrontationDef.
- `sidequest-server/sidequest/genre/models/character.py` — ClassDef, NpcArchetype.
- `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml` — confrontations + class config.
- `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml` — class definitions with empty `encounter_beat_choices`.
- `sidequest-content/genre_packs/caverns_and_claudes/magic.yaml` — innate magic + slot ledger frame.
- Sprint 3 backlog candidate stories (2026-05-08 session handoff) — story #2 (B/X memorization wiring) follows this story.
