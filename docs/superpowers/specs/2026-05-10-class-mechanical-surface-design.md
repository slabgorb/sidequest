# Class Mechanical Surface — Design Spec

**Date:** 2026-05-10
**Author:** Architect (post-2026-05-10 playtest brainstorm)
**Origin:** `docs/design/class-mechanical-surface-handoff.md` and the C&C / caverns_sunden multiplayer playtest finding (Lv 1 Cleric and Thief sheets showing literal `"No abilities."`).
**Status:** Approved design, pending implementation plan via `superpowers:writing-plans`.

## 1. Problem Statement

A Lv 1 Cleric and Lv 1 Thief in `caverns_and_claudes` open the Abilities tab on the character sheet and see `"No abilities."`. The data is honestly empty (no `abilities` key on any class in `classes.yaml`); the UI is honestly rendering. The narrator is doing the heavy lifting through prose, but the sheet is silent.

Two of the four primary-audience players (Keith — 40-year B/X veteran; Sebastien — mechanics-first nephew) read the sheet first and the prose second. `"No abilities."` reads to them as a load failure or a missing class definition. The audience rubric in `CLAUDE.md` is the reason this matters.

## 2. The Deeper-Question Answer

> **Classes are a mechanical lane, not flavor-only.** Every class either has a magic plugin filling its signature mechanical slot, or carries one Class-source `AbilityDefinition` that does. Affinities (`progression.yaml`) remain the *growth* lane on top — the class signature is the *starting* mechanical lane. Both ship and coexist; neither replaces the other.

This is a load-bearing decision and likely warrants a new ADR adjacent to **ADR-014 (Diamonds and Coal)** and **ADR-021 (Progression System)**, or an amendment to ADR-021. ADR slot reserved during implementation planning.

## 3. Scope

**This spec covers `caverns_and_claudes` only.** Other 10 genre packs adopt the data shape lazily as they surface for playtest. The empty-class case (no signature, no plugin) renders the Class Moves chip row + Affinities — graceful, not broken, not silent.

Pattern documented for future per-genre rollout. No content fill outside C&C this story.

## 4. Architecture — Four Layers on the Abilities Tab

| # | Section | Source | Visibility | Implemented this story? |
|---|---|---|---|---|
| 1 | **Class signature** | `Class` | shown when ≥1 ability with `source=Class`; otherwise section *and* its header are hidden | Yes (Cleric/Fighter/Thief) |
| 2 | **Class moves** | derived from `encounter_beat_choices` | shown when `class_moves` non-empty | Yes — bare chip row |
| 3 | **From inventory** | `Item` | shown when ≥1 ability with `source=Item`; both section and header hidden when empty | **Hook only.** Wired path; empty list. |
| 4 | **Earned** | `Play` | always shown — Affinity progression panel | Already implemented |

The `<SensitivitiesSection>` (existing, magic-state) renders below all four sections, unchanged.

The hardcoded string `"No abilities."` does not appear anywhere in the rendered output for any class. It was the wrong abstraction; it dies in this change.

## 5. Data Shape

### 5.1 `classes.yaml` change (caverns_and_claudes)

**Add `taunt` to Fighter encounter beats:**

```yaml
- id: fighter
  encounter_beat_choices:
    - attack
    - defend
    - flee
    - shield_bash
    - cleave
    - parry
    - feint
    - taunt        # NEW
```

**Add optional `abilities:` key per class** carrying signature-ability content. The loader stamps `source: Class` on each entry — authors do not type it.

```yaml
- id: cleric
  abilities:
    - name: "Turn Undead"
      genre_description: >
        {writer agent fills — Affinity-prose voice, ~3-4 sentences,
        evokes raising the holy symbol and the unliving recoiling}
      mechanical_effect: >
        Resolves on 2d6 vs HD; loud (raises Keeper awareness);
        fails on intelligent unliving who have already chosen their side.
      involuntary: false

- id: fighter
  abilities:
    - name: "Taunt"
      genre_description: >
        {writer agent fills — tank-flavored voice, the Fighter making
        themselves the target so the squishies survive}
      mechanical_effect: >
        Forces enemy attention onto the Fighter for the next round of beats;
        attacker advantage shifts off allies; Fighter takes the next
        incoming hit on Edge before Composure.
      involuntary: false

- id: thief
  abilities:
    - name: "Backstab"
      genre_description: >
        {writer agent fills — opportunistic, professional, the precise
        removal of someone who didn't see you}
      mechanical_effect: >
        Requires unaware target (sneak/feint setup or surprise round);
        damage multiplier per genre Edge math; one-shot ends combat
        against single weak unaware targets.
      involuntary: false
```

**Mage receives no `abilities:` key.** The `magic_config` block is its signature surface. A class with both keys would populate both — design allows it; no class does it in C&C.

### 5.2 Pydantic genre model

`sidequest-server/sidequest/genre/models/character.py` — `ClassDefinition` gains:

```python
abilities: list[ClassAbilityDef] = Field(default_factory=list)
```

Where `ClassAbilityDef` mirrors `AbilityDefinition` *minus* `source` (loader stamps `source=AbilitySource.Class`). Separate model class so authors are not confused by a discriminator they do not fill in.

### 5.3 No model change to runtime types

`AbilityDefinition` (`sidequest-server/sidequest/game/character.py`) is reused as-is. `Character.abilities: list[AbilityDefinition]` already accepts mixed-source entries.

### 5.4 Future-proof notes (not implemented)

- A `level_unlocked: int = 1` field on `ClassAbilityDef` is the obvious place to grow when class-level-gated abilities land. Not authored now.
- A higher-level Turn Undead per-HD matrix would be expressed by additional entries with `level_unlocked > 1`. Out of scope.

## 6. Chargen Wiring

### 6.1 New seam: `_seed_class_abilities(char, class_def)`

Lives in the chargen finalization path (per ADR-015 `CharacterBuilderState`, after class is committed). Reads `class_def.abilities` and appends to `Character.abilities` with `source=AbilitySource.Class` stamped on each entry.

### 6.2 Sibling stub: `_seed_item_abilities(char, kit_def)`

Empty body, named integration point. Documented:

```python
def _seed_item_abilities(char: Character, kit_def: KitDefinition) -> None:
    """Populate Item-source abilities from starting kit.

    Stub — items don't grant abilities yet (see design doc 2026-05-10).
    Next story walks kit_def items and appends Item-source AbilityDefinitions.
    """
    return  # next story owns this
```

This is an explicit exception to the "no stubs" rule because the next story is *imminent* (it is the very next planned content surface). The empty body documents architectural commitment so the chargen call site does not need surgery next story. Code comment marks it explicitly so a future Reviewer does not delete it.

### 6.3 Magic plugin path — unchanged

Mage chargen continues to call `seed_learned_v1_state` for `known_spells` / `prepared_spells` / slot bars. Class abilities and magic surfaces are *separate* code paths; one is not a fallback for the other. A class with both keys would populate both.

### 6.4 Failure modes — loud, not silent

- Malformed `abilities:` entries → genre pack loader raises during startup. Pack fails to load. Server refuses to serve sessions in that genre.
- Absent `abilities:` key → empty list, no error. The Mage path; documented as the magic-plugin signal.
- `taunt` beat ID encountered by an engine build that does not know it → encounter engine raises. Implication: encounter engine must learn `taunt` *before or with* the YAML change ships.

### 6.5 OTEL emission

Per CLAUDE.md OTEL principle. New watcher events:

- `chargen.class_abilities.seeded` — payload `{class_id, ability_count, ability_names: list[str]}`.
- `encounter.taunt.activated` — payload `{actor_id, round, targets_redirected: int}`.
- `encounter.taunt.expired` — payload `{actor_id, round}`.

The GM panel (Keith / Sebastien tool, per memory) sees "Cleric → seeded 1 class ability: Turn Undead" and can verify the wiring is alive, not improvised.

## 7. Protocol & UI

### 7.1 Stop flattening abilities to strings

Current bug at `CharacterPanel.tsx:825` — `abilities: string[]`. The serializer dropped `AbilityDefinition` to `.name` somewhere upstream. Prose, source classification, involuntary flag — all lost.

Fix in `sidequest-server/sidequest/protocol/`:

```python
class CharacterStateForUi(BaseModel):
    # ...existing fields...
    abilities: list[AbilityDefinition]   # was: list[str]
    class_moves: list[str]               # NEW: filtered encounter_beat_choices
```

`class_moves` is server-pre-filtered: drops `attack`/`defend`/`flee` (universal beats) and any `auto-filled` scaffolding suffix. UI receives a clean list; it does not filter.

The `auto-filled` filter currently in the UI (line 831) moves server-side and dies on the client.

### 7.2 `AbilitiesContent` restructure

`sidequest-ui/src/components/CharacterPanel.tsx:820-909` becomes a four-section component using the visibility table in §4.

**Visual treatment:**

- **Class signature** — styled card matching FOLIO theme. Display font for name, body font for genre prose, muted small-text italic for mechanical-effect/limits line. Same visual weight as Affinity unlock cards (consistency across the four sources).
- **Class moves** — horizontal chip row. Bare labels, no icons, no prose. The current letter-square treatment (lines 870-887) is dropped for chips — chips signal "menu reference," cards signal "rich ability."
- **From inventory** — Class-signature card styling when populated. Empty = entire section header suppressed.
- **Earned** — current Affinity rendering, unchanged.

### 7.3 Multiplayer concern

Per ADR-028 (perception rewriter) and ADR-037 (shared/per-player state split), each player sees only their own character's abilities tab. The new four-section payload is per-character, sent only to the owning player's WS connection. **No change to perception filtering.**

## 8. Engine — Taunt Beat Handler

`taunt` is a new beat ID. The encounter engine handler:

- **Resolution:** sets per-encounter `taunt_active_actor: actor_id`, `taunt_remaining_rounds: 1` on encounter state.
- **Targeting hook:** existing enemy beat-selection logic adds a precondition — when `taunt_active_actor` is set and the chosen enemy has line of sight to that actor, prefer that actor as target. Bias the selection, do not force it. (Stupid enemies near 100%; intelligent enemies less so. Implementation tunes the weight; for L1 ship, full bias is acceptable.)
- **Damage routing:** while flag is active, enemy damage to any ally is rerouted to the taunter, capped at one redirect per round. Prevents a 5-enemy round all redirecting to one Fighter.
- **Decay:** `taunt_remaining_rounds` decrements at end of round; at 0, targeting bias and damage routing return to baseline.

**Out of scope:** smart-enemy resistance check (a 2d6 vs INT/WIS roll for "did the enemy fall for it"). Future evolution; ship taunt as auto-success at L1.

## 9. Content Authoring

### 9.1 Three signature abilities — writer agent task

Each ability is `name + genre_description + mechanical_effect + involuntary=false`. Voice match: Affinity unlocks in `progression.yaml` (sense-memory, second-person, ~3-4 sentences for genre prose, one-clause for mechanical effect). The "experience / limits" pattern of Affinity prose is the model to imitate.

- **Cleric — Turn Undead.** Genre prose evokes raising the holy symbol, the unliving recoiling. Mechanical effect: 2d6 vs HD; loud; fails on intelligent unliving.
- **Fighter — Taunt.** Genre prose evokes the deliberate act of becoming the most attractive target — eye contact, an insult, a half-step forward. Mechanical effect per §8.
- **Thief — Backstab.** Genre prose evokes the precise removal of someone who didn't see the Thief coming — quiet, brief, complete. Mechanical effect: requires unaware target; damage multiplier; one-shot single weak unaware targets.

**Writer-agent constraints:**

- ~3-4 sentences for `genre_description`. No more.
- `mechanical_effect` is engine-facing — write as a clause the encounter engine can route on, not a paragraph.
- `involuntary: false` — these are all player-chosen.
- Match C&C voice (wry, B/X-flavored, illuminated-manuscript register). Not Heavy Metal voice; not Tea & Murder voice.

### 9.2 What the writer agent does NOT touch

- Mage signature: magic plugin fills the slot. No `abilities:` key on Mage.
- Other encounter beats (`shield_bash`, `cleave`, `parry`, `feint`, `pray`, `sneak`). Bare chip labels; no prose authored this story.
- Affinity prose (already authored).

## 10. Testing Strategy

### 10.1 Server unit tests

- Chargen population per class: parametrized tests assert `Character.abilities` after chargen for Cleric/Fighter/Thief contains exactly one entry with correct name and `source=AbilitySource.Class`. Mage produces empty `abilities` and non-empty magic state.
- Genre-pack loader strictness: malformed `abilities:` raises during pack load; well-formed `abilities:` round-trips to `ClassAbilityDef`.
- Item-stub contract: `_seed_item_abilities` is callable, returns `None`, leaves `Character.abilities` untouched. (Locks the stub against accidental Reviewer deletion.)
- OTEL emission: `chargen.class_abilities.seeded` event fires with correct payload.

### 10.2 Engine tests — Taunt

- Activation: Fighter selects `taunt`; encounter state acquires `taunt_active_actor` and `taunt_remaining_rounds=1`.
- Targeting bias: with taunt active, enemy beat selection prefers Fighter over allies (≥10 trials, seeded RNG).
- Damage redirect: enemy attack on ally during taunt round reroutes to Fighter, capped at one redirect per round.
- Decay: `taunt_remaining_rounds` decrements; at 0, baseline restored.
- OTEL: `encounter.taunt.activated` and `encounter.taunt.expired` fire with correct payloads.

### 10.3 Protocol contract tests

- WS state-mirror payload: `CharacterStateForUi.abilities` serializes as full `AbilityDefinition` JSON, not strings. Pin with snapshot against a Cleric fixture.
- `class_moves` filtering: server pre-filters `attack/defend/flee` and auto-filled scaffolding. Pin with snapshot.

### 10.4 UI tests (Vitest)

- Four-section render: props with mixed-source abilities render correct sections in correct order; class signature shows full prose card; class moves render as chip row.
- Empty-state: Mage props (no Class abilities) hide Class signature *header*. Empty Item-source list hides From-inventory header. The string `"No abilities."` does not appear in any rendered output.
- Auto-filled scaffolding regression guard: leaked `auto-filled` entries absent from rendered output.

### 10.5 Integration / wiring test (CLAUDE.md mandatory)

End-to-end: spin up server with C&C genre pack, create a Cleric via the chargen WS flow, capture the state-mirror message, parse as `CharacterStateForUi`, assert the parsed object's `abilities` contains a Turn Undead entry with `source="Class"` and a non-empty `genre_description` (real prose, not the `{writer agent fills}` placeholder). Assert `class_moves` contains `pray, shield_bash, turn_undead` and excludes `attack, defend, flee`.

This test fails today (because the protocol path flattens to `string[]`) and proves green-end-to-end when this story ships. Must be in CI; must pass before merge.

### 10.6 Explicitly NOT tested

- Affinity prose rendering (existing tests cover).
- Magic plugin spell-list rendering (existing tests cover).
- B/X save matrices in the UI (out of scope).
- Item-source population beyond the stub-contract test (next story).

## 11. Out of Scope (Named for the Boundary)

- B/X save-throw matrices in the UI.
- Race-source abilities (race packs not shipped).
- Item-source ability population (next story; only the hook lands here).
- Cross-genre rollout to 10 other packs (deferred; pattern documented).
- Prose authoring is delegated to writer agent during implementation; architect specifies what they need to deliver, not the prose itself.
- Smart-enemy resistance check on Taunt.

## 12. Locked Decisions (Inputs, Not Topics)

These were settled before the brainstorm:

- Affinities ship and stay. Whatever the class abilities answer, Affinities continue as the growth lane.
- L1 Cleric has zero spells. B/X canon, intentional.
- Magic plugins handle casters. `magic_access: innate_v1` and `magic_config` are the casting surface.
- The Zork Problem stands. Natural-language declaration remains the primary verb input. Ability cards are reference, not menus.

## 13. Estimated Lift

- Engine Taunt handler: ~½ day
- Genre-loader extension + Pydantic model: ~½ day
- Chargen seam + `_seed_class_abilities` + stub: ~½ day
- Protocol shape change + server-side `class_moves` filtering: ~½ day
- UI four-section restructure: ~1 day
- Content authoring (3 abilities, writer agent): ~½ day
- Tests across all layers: ~1 day

**Total: 4-5 days, single story.** Possibly splittable into a backend story (engine + chargen + protocol) and a frontend story (UI restructure + UI tests), with the integration test bridging.

## 14. Open Questions for Implementation Plan

- Confirm exact location of chargen finalization in `sidequest-server` (likely `character_builder.py` or similar); spec assumes but does not pin.
- Confirm exact protocol message that carries character state to UI (likely under `sidequest-server/sidequest/protocol/`); spec assumes but does not pin.
- Confirm whether Affinity rendering is in `AbilitiesContent` today or elsewhere (CharacterPanel only shows the abilities tab; Affinities may live in a sibling component). UI restructure scope depends on this.

These are implementation-research questions, not design questions. The implementation plan resolves them.
