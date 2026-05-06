# Magic System Implementation — Caverns & Claudes (Loose-Vancian B/X)

**Date:** 2026-05-06
**Status:** Design — pre-implementation
**Target playtest:** Keith + James + Alex + Sebastien, full Sünden session
**Companion docs:**
- `docs/design/magic-taxonomy.md` (framework)
- `docs/superpowers/specs/2026-04-28-magic-system-coyote-reach-implementation-design.md` (vertical-slice precedent)
- `docs/superpowers/specs/2026-04-29-magic-system-coyote-reach-architect-addendum.md` (architecture detail)
- `docs/adr/adr-014-diamonds-and-coal.md` (HP-removed; momentum/edge/fate replacement)

## Purpose

Stand the magic-system framework up the rest of the way for **Caverns & Claudes** so a full B/X-flavored Sünden delve can be played end-to-end with **Mage and Cleric mechanically casting prepared spells**, **scrolls/wands/potions/cursed items still firing on the existing `item_legacy_v1` track**, OTEL-observed, ledger-visible, and narrator-grounded.

The framework was vertical-sliced against Coyote Star (space_opera) on 2026-04-28. C&C is the second world to exercise it, and the first to require the deferred `learned_v1` plugin. Coyote Star validated `item_legacy_v1` and plugin composition; C&C validates `learned_v1` and prepared-spell economics against a tabletop-canon spell list.

## Approach

**Content-first, then plugin-first.** Author the C&C-side YAML (genre amendments, world magic.yaml, classes hookups, v1 spell catalog) before any Python lands. This is the same pattern that worked for Coyote Star: the authoring contract has to fight the schema before the schema is poured. Then build `learned_v1` against exactly what the v1 spell catalog uses, deferring every feature it doesn't.

## Audience anchors

Per CLAUDE.md, design decisions weigh against the actual playgroup:

- **Keith** (forever-GM-now-player, 40 years tabletop): Moldvay/Cook is the *vibe* of C&C — sending the L1-L6 spell list signals he wants canon authenticity. The narrator must surprise him; mechanical enforcement of slot economics and hard_limits is how it does that.
- **James** (narrative-first, played Rux in caverns_and_claudes): a casting Mage doesn't reduce his agency. The spell catalog is small enough to read quickly; spell prep is a pre-delve choice, not a turn-by-turn rules check.
- **Alex** (slow typist, freezes under pressure): no spellbook-transcription minigame (loose Vancian, not strict). Spell prep is a single declared verb at a safe site, not a multi-step UI.
- **Sebastien** (mechanics-first): the GM panel renders the slot economy live — known list, prepared list, slots remaining, cooldown to next prep window. This is *the* Sebastien feature for C&C.

## Locked decisions (this brainstorm, 2026-05-06)

1. **Loose Vancian** (option B). Mage knows N spells per level; at rest she chooses a daily preparation up to her per-level slots; cast = expended until next rest. No spellbook transcription.
2. **`learned_v1` plugin** (Approach 1) — un-defer the Coyote Star deferral and stand it up for C&C. Composes alongside `item_legacy_v1`; both ride the same `magic_state`.
3. **Saves = C&C native attribute checks**. The genre's `resolution_mode: opposed_check` and per-confrontation `stat_check` is the existing primitive. Save-vs-spells maps to the relevant attribute (Sleep → WIS, Fireball → DEX, Hold Person → STR, Charm → WIS). No new save tracks.
4. **Damage = momentum** (per ADR-014, no HP). Spell damage applies to whatever momentum/edge/fate currency the C&C combat layer uses today.
5. **v1 spell scope = Magic-User L1 + Cleric L1**. Schema designed to scale to L1-L6 / L1-L5 without rework. L2+ is content-authoring scaling, not architecture.
6. **No Elf class** in this pass. B/X race-as-class is a separable decision; the M-U/Elf shared spell list is authoring guidance for later, not v1 scope.
7. **Cleric is Vancian like Mage** (B/X canon: prep-at-rest, expended-on-cast). Not granted-on-the-fly.
8. **Cleric Turn Undead is in scope** as a class-special (not a spell), wired via the existing confrontation auto-fire pattern (`item_legacy_v1` precedent).
9. **Rest-to-prepare is an explicit verb** at any safe site (Lampwick, returning to Sünden Square, declared in-fiction).
10. **No spellbook transcription**. New spells acquired on level-up by player choice from the catalog; found scrolls remain one-shots in the `item_legacy_v1` track.

---

## 1. Content commitment — C&C's magic shape

### Plugin set (v1 ships these two)

- **`item_legacy_v1`** (existing, already wired). Mechanisms active: `discovery`, `mccoy` (a wandsmith counts), `relational`, `faction`. Subtypes used in C&C: `scroll`, `potion`, `wand`, `cursed_weapon`, `reliquary`. The genre's signature trap (cursed items) lives here.
- **`learned_v1`** (new). Mechanisms active: `studied` (Mage → arcane catalog) and `granted` (Cleric → divine catalog). One catalog per `tradition`; tradition gates which spells a class may know.

### Axes

- **World-knowledge** (genre default): `primary: folkloric` — commoners know stories, the Delver knows scrolls work, *and* the Delver knows Sleep can drop a man in his cups, *and* the Delver knows the cleric of the Three Rites can stop a wound from bleeding. Magic is uncommon but not classified or rare.
- **Visibility:** `permitted: [feared, dismissed]`, default `feared`. World may dial.
- **Intensity:** `0.3` (low-medium). B/X-baseline.
- **Player options:** `can_build_caster: true` (FLIP — was false; classes shipped this sprint require this). `can_build_item_user: true`. `chargen_caster_classes: [mage, cleric]`.

### Hard limits

The five existing genre hard_limits stay as-is: no resurrection, no true creation, no unlimited high evocation, no plane shift, no permanence without renewal. **No new world-specific additions for Sünden in v1.** All are now enforced against `learned_v1` casts as well as item activations — the validator already runs hard_limits against any working regardless of source.

### Cost types

Genre adds `slot` to the existing `[components, backlash]`. **`slot`** is the per-level memorized-and-spent currency. **`components`** still applies (some scrolls/potions still cost ash/blood/the second-to-last torch). **`backlash`** still applies (cursed-item activation, mis-cast spell, the wand that bonded to the wrong delver).

### Ledger bars (v1 — four bar types)

| Bar | Scope | Direction | Threshold(s) | Confrontation hook |
|---|---|---|---|---|
| `slots_l1_<class>_<actor>` | character | down (resets at rest) | 0 → can't cast L1 spells until rest | — |
| `bond_<item_id>` | item | bidirectional | low → item refusal, high → loyalty | narrator-discretion (existing) |
| `item_history_<item_id>` | item | up | accumulates resonance | narrator-discretion (existing) |
| `divine_favor_<actor>` | character | bidirectional | high → narrator may grant a "free" reliquary effect; low → cleric cannot Turn until restored | narrator-discretion |

`divine_favor` is the only character-scope bar new to C&C. It anchors Cleric's class identity beyond just "Mage but with a different spell list" — the cleric who heals freely, lies, breaks oaths, or fails to honor the rites of Sünden's Three drifts on this bar.

`slots_lN` bars per spell level scale 1:1 with class spell-progression tables; v1 ships `slots_l1` only.

### Named confrontations (v1 — exactly two)

1. **Magical Backlash** — auto-fires when a cast fails its validator (mis-targeted, wrong tradition, hard-limit violation). Pulls `backlash` cost from the genre's existing cost grammar.
2. **The Wall Notices** — narrator-discretion confrontation that fires when high-level magic (L3+, deferred) is cast in Sünden Square or within sight of the Wall. Sünden-flavored: the Wallwrights record what magic was cast, when, by whom; long-term campaign drift.

(v1 spell scope is L1-only; "The Wall Notices" is authored-but-dormant until L3 spells ship. It's listed here so its scaffold goes in with the world magic.yaml.)

### Cleric Turn Undead

Class-special, not a spell, not slot-gated. Cleric declares "I turn"; opposed check on `divine_favor` × cleric class level vs. undead HD. On success, undead flee or are destroyed per B/X table. Auto-fires no confrontation but emits an OTEL span (`learned_v1.turn_undead`) for the GM panel. Detailed B/X turn table is authored in the spell catalog as a class-special block (sibling to spells, not a spell).

---

## 2. Spell catalog schema

Spell catalog files live at:

```
sidequest-content/genre_packs/caverns_and_claudes/spells/
├── arcane_l1.yaml      # Mage L1
├── divine_l1.yaml      # Cleric L1
└── (future) arcane_l2.yaml, divine_l2.yaml, ...
```

Each catalog is a list of spell entries:

```yaml
spells:
  - id: magic_missile
    name: "Magic Missile"
    level: 1
    tradition: arcane           # arcane | divine
    range: near                 # touch | close | near | far | unlimited
    target: single              # single | area | self | object
    duration: instant           # instant | until_rest | turns:N | permanent
    save:
      stat: null                # null = auto-hit; or DEX/WIS/INT/etc.
      effect: none              # none | negates | halves | partial:<text>
    effect_template: "Force dart strikes target — 1 momentum damage, auto-hit"
    components:
      verbal: true
      somatic: true
      material: null            # null | "<material description>"
    backlash: null              # null | "<backlash description>"
    narrator_register: |
      A bolt of glowing force, half-thought, half-aimed. The dart finds
      what the caster pointed at, even in dark, even around a corner if
      the corner is short. It does not miss. It also does not impress.
    hard_limits_check: []       # spell-specific limit IDs to enforce
    otel_attrs:
      - cast_intent             # what target/effect the player declared
      - validator_outcome       # ok | rejected_<reason>

  - id: sleep
    name: "Sleep"
    level: 1
    tradition: arcane
    range: near
    target: area
    duration: turns:1d4+1
    save:
      stat: WIS
      effect: negates
    effect_template: "Up to 4d4 HD of creatures (lowest HD first); save WIS or unconscious"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: |
      A slow, kind weight. The eyes go first, then the knees. The smallest
      foes drop first; the strongest may yet stand and look at you.
    hard_limits_check: []
    otel_attrs: [cast_intent, hd_affected, saves_made, saves_failed]
```

The schema field `effect_template` is **deterministic** — not a free-form prompt for the narrator. It encodes the mechanical effect that `learned_v1` mutates into game state at parse-time (per ADR-001 / `claude -p` no-reactive-tools). `narrator_register` is the prose flavor that the narrator may quote or paraphrase; it does *not* drive mechanics.

### Damage convention

Spell damage is expressed in the same currency the C&C combat layer uses for momentum loss. v1 scope: Magic Missile = `1 momentum damage, auto-hit`. As C&C combat conventions evolve (edge / fate), the spell catalog evolves with them — the catalog is the surface for tuning, not the plugin code.

### Save convention

`save.stat` references the C&C attribute used in the existing `opposed_check` resolution. `save.effect: negates | halves | partial:<text>` describes what success buys the defender. **No new save mechanic.** The plugin emits a structured save request; the existing C&C check resolver handles the roll.

---

## 3. learned_v1 plugin — minimum viable surface

### State (per character)

```python
@dataclass
class LearnedState:
    tradition: str                       # "arcane" | "divine"
    known_spells: list[str]              # spell IDs from catalog
    prepared_spells: dict[int, list[str]]  # level -> list of prepared spell IDs
    slots_remaining: dict[int, int]      # level -> count remaining
    slots_max: dict[int, int]            # level -> count granted by class level
    last_prepared_at_turn: int | None
```

### Plugin operations

- `prepare(actor, prep_list)` — at safe site, character chooses spells from `known_spells` to fill slot budget; emits `learned_v1.prepare` span with prepared list.
- `cast(actor, spell_id, target_spec)` — validates: spell is prepared, slot remaining, hard_limits pass; returns structured `MagicWorking`; decrements slot; emits `learned_v1.cast` span.
- `rest(actor)` — at safe site, restores `slots_remaining = slots_max`, clears `prepared_spells` (re-prep required); emits `learned_v1.rest` span.
- `turn_undead(actor, undead_hd)` — Cleric-only; opposed check vs. `divine_favor`; emits `learned_v1.turn_undead` span.

### Class-level slot tables

Stored in `caverns_and_claudes/classes.yaml` per class, referenced by the plugin:

```yaml
- id: mage
  magic_access: learned_v1
  magic_config:
    tradition: arcane
    slots_by_class_level:
      1: { 1: 1 }                 # class level 1: 1 L1 slot
      2: { 1: 2 }
      3: { 1: 2, 2: 1 }
      # ... B/X canon up to class L14
    starting_known_spells: 2      # at chargen: pick 2 L1 spells from arcane catalog
    save_dc_stat: INT             # save DCs scale with caster's INT
```

### Context block payload

`build_magic_context_block` extends to include, when `learned_v1` is active for the character:

```
<learned-magic actor="rux" tradition="arcane">
  <known>magic_missile, sleep, charm_person, light, read_magic, detect_magic</known>
  <prepared>
    <l1>magic_missile, sleep</l1>
  </prepared>
  <slots><l1>1/2 remaining</l1></slots>
</learned-magic>
```

The narrator sees the prepared list and the slots remaining. Decisions to cast remain the player's; the narrator narrates outcomes parsed from the structured `MagicWorking`.

---

## 4. Content surface — the YAML diff

### `caverns_and_claudes/magic.yaml` (amend)

- `permitted_plugins: [item_legacy_v1, learned_v1]`
- `cost_types: [components, backlash, slot]`
- `narrator_register` rewritten: not "magic is found, not cast" — *both*. Mages who survive long enough to delve carry 1-2 prepared workings; clerics carry 1-2 granted ones; everyone carries scrolls and potions and prayers to whatever they think will help. Cursed items remain the genre's signature trap.
- Design-notes block (commented-out fields, lines 67-105) updated: `chargen_caster_classes: [mage, cleric]`, `can_build_caster: true`, `manifestation.modes: [item_channeled, learned]`.

### `caverns_and_claudes/rules.yaml` (amend)

- Leave `magic_level: none` alone — the field is being retired (per the in-file note dated 2026-04-27). The truth lives in `magic.yaml` (`intensity`, `allowed_sources`, `permitted_plugins`).
- Update the deprecation comment block on lines 4-7: the "no caster classes" justification for the field is now actively wrong (Mage/Cleric ship with `magic_access: learned_v1`). Leave the retirement intent intact; revise the rationale to say *the genre has casters, but `magic_level` was never load-bearing for that and is still being retired in favor of `magic.yaml`*.
- (Out of scope but noted for the implementer): `allowed_classes: [Delver]` on line 9-10 is stale relative to `classes.yaml`'s fighter/mage/cleric/thief. Confirm at implementation time which list the chargen loader actually consults; do not silently fix here.

### `caverns_and_claudes/classes.yaml` (amend)

- `mage.magic_access: learned_v1` + `magic_config: { tradition: arcane, slots_by_class_level: {...}, starting_known_spells: 2, save_dc_stat: INT }`.
- `cleric.magic_access: learned_v1` + `magic_config: { tradition: divine, slots_by_class_level: {...}, starting_known_spells: 2, save_dc_stat: WIS, turn_undead: true }`.
- `fighter.magic_access` and `thief.magic_access` stay `null`.

### `caverns_and_claudes/spells/arcane_l1.yaml` (new)

Twelve M-U L1 spells in C&C voice (Moldvay canon): Charm Person, Detect Magic, Floating Disc, Hold Portal, Light, Magic Missile, Protection from Evil, Read Languages, Read Magic, Shield, Sleep, Ventriloquism.

### `caverns_and_claudes/spells/divine_l1.yaml` (new)

Eight Cleric L1 spells in C&C voice (Moldvay canon): Cure Light Wounds (reverse: Cause Light Wounds), Detect Evil, Detect Magic, Light (reverse: Darkness), Protection from Evil, Purify Food and Water, Remove Fear (reverse: Cause Fear), Resist Cold.

### `worlds/caverns_sunden/magic.yaml` (new)

```yaml
world: caverns_sunden
genre: caverns_and_claudes

intensity: 0.3                  # genre baseline; Sünden does not amplify

active_plugins:
  - item_legacy_v1
  - learned_v1

world_knowledge:
  primary: folkloric
  # The Three Towns know magic exists. The Wallwrights record which delvers
  # came back changed by what; the Confraternity has private files on which
  # cleric of which rite has been seen calling on something. Nobody talks
  # about it in joint session.

visibility:
  primary: feared

can_build_caster: true
can_build_item_user: true

cost_types_active: [components, backlash, slot]

ledger_bars:
  - id: divine_favor
    scope: character
    direction: bidirectional
    range: [-1.0, 1.0]
    threshold_high: 0.7
    threshold_low: -0.7
    consequence_on_high_cross: "narrator-discretion: cleric receives one free reliquary effect within the session"
    consequence_on_low_cross: "narrator-discretion: cleric cannot Turn until favor is restored at the Confessional / Workhouse / Masquerade"
    starts_at_chargen: 0.0
    applies_to_classes: [cleric]
  # slots_lN bars are auto-instantiated by learned_v1 plugin per actor
  # at chargen — no static authoring needed in the world file.

narrator_register: |
  Sünden has known magic for as long as it has known the three sins. The
  Wallwrights cut a name shallower for a delver who came back with the
  Words still in their head. The Confraternity does not name what Brother
  Hesh's lay-monastic discipline taught him, and Brother Hesh does not
  volunteer. The Lampwick keeps a back-room candle for the rare cleric
  passing through who needs one full night of unmolested rest and asks
  for it without elaboration. Magic is folkloric here. The folklore is
  also the truth.
```

---

## 5. UI surface

`LedgerPanel` (existing, inside `CharacterPanel.tsx` per Coyote Star spec) extends to render the `learned_v1` block when the character has `magic_access: learned_v1`:

- Known spells list (collapsible)
- Prepared spells (per-level grouping, slots indicator: ●●○ etc.)
- "Prepare spells" action button (enabled at safe sites; disabled mid-delve)
- Cleric only: `divine_favor` bar with current value and threshold markers
- Cleric only: "Turn Undead" action button (enabled when undead in scene)

GM panel (OTEL dashboard) gets the same block in its character-state pane plus per-cast event log: who cast what, validator outcome, save result, damage applied.

---

## 6. OTEL spans

New spans under `learned_v1.*`:

| Span | Required attrs | Optional attrs |
|---|---|---|
| `learned_v1.prepare` | actor_id, tradition, prepared_spells, slots_max | location, last_prep_turn |
| `learned_v1.cast` | actor_id, spell_id, validator_outcome, slot_consumed | target_spec, save_stat, save_result, damage_applied |
| `learned_v1.rest` | actor_id, slots_restored, location | turns_since_last_prep |
| `learned_v1.turn_undead` | actor_id, undead_hd, divine_favor, outcome | undead_count, undead_type |
| `learned_v1.backlash` | actor_id, spell_id, backlash_reason | hard_limit_violated |

Existing `magic.*` and `item_legacy_v1.*` spans unchanged.

---

## 7. Hard limits / constraints

- **ADR-001 — `claude -p` no reactive tools.** Spell resolution is parse-time-deterministic. Effects encoded in `effect_template`; `MagicWorking` is mutated into game state by the existing `narration_apply.py` pipeline. Narrator does not "decide" outcomes mid-generation.
- **ADR-014 — no HP.** Damage applies to momentum/edge/fate per the C&C combat layer's existing currency. Spell catalog tracks damage in those terms, not in d6/d8 rolls (those are a B/X surface that doesn't translate; the *outcome shape* is what we keep, not the dice).
- **No silent fallbacks.** If `worlds/caverns_sunden/magic.yaml` is missing, current behavior is silent skip (per `magic_init.py` lines 65-69). v1 keeps that doctrine — silent skip is *correct* for worlds that genuinely have no magic. C&C now guarantees its worlds will author the file; absence in a future C&C world is an authoring bug, not a graceful degradation.
- **No stubbing.** `learned_v1` ships with all its v1 operations (prepare, cast, rest, turn_undead) wired end-to-end or it doesn't ship.
- **Audience pacing.** Spell preparation is one declared verb; spell casting is one declared verb. No multi-turn UI rituals. Alex must be able to play a Mage without the table waiting on her.

---

## 8. Out of scope (deferred)

- L2-L6 Magic-User spells (content scaling).
- L2-L5 Cleric spells (content scaling).
- Elf class (B/X race-as-class; separable decision).
- Spellbook transcription / scrolls-add-to-known-list (option A from brainstorm; un-locked, available later).
- Multi-session confrontations on `divine_favor` / "The Wall Notices".
- Cross-character spell sharing (e.g., cleric cast on mage).
- Counter-magic (`anti_magic_zone`, `save_or_die`, `destroy_source` are listed in genre magic.yaml design notes but are not v1 mechanics).

---

## 9. Implementation order (for the writing-plans pass)

1. **Plugin: `learned_v1.py` + `learned_v1.yaml`** (`sidequest-server/sidequest/magic/plugins/`). Models, validator, state, save-roll integration with `opposed_check`, OTEL emission. Built against existing `item_legacy_v1` as the structural template.
2. **Genre amendments** (`caverns_and_claudes/magic.yaml`, `rules.yaml`, `classes.yaml`).
3. **Spell catalog** (`spells/arcane_l1.yaml`, `spells/divine_l1.yaml`).
4. **World magic.yaml** (`worlds/caverns_sunden/magic.yaml`).
5. **Loader extension** — `magic_loader.py` reads spell catalogs and binds them to plugin instances per class.
6. **Context builder extension** — `magic/context_builder.py` renders `<learned-magic>` block.
7. **UI** — `LedgerPanel` block for learned_v1 + Cleric divine_favor bar + prepare/turn-undead action buttons.
8. **OTEL spans** — `telemetry/spans/magic.py` extends with `learned_v1.*`.
9. **Tests**: unit per-plugin, wiring test for end-to-end prepare→cast→rest cycle in a Sünden session, integration test confirming context block reaches narrator.

## 10. Open questions (none locked at brainstorm)

None. All architectural decisions locked. v1 spell catalog text is authoring work, not architecture; class-level slot tables are pure B/X canon transcription; OTEL attributes are listed above.

---

## 11. Success criteria

1. A Mage character in Sünden can be created via the existing 5-scene chargen, walks down to Grimvault, casts Magic Missile on a creature in the Sorting Floor, and the cast appears in the OTEL dashboard as a `learned_v1.cast` span with the correct spell_id, slot consumed, and damage applied.
2. The same character returns to the Lampwick, declares "I prepare spells" in fiction, and the slots reset; OTEL shows a `learned_v1.rest` span and a `learned_v1.prepare` span.
3. A Cleric character casts Cure Light Wounds on the Mage; momentum is restored; OTEL spans fire correctly; `divine_favor` is unchanged (acting in role).
4. A Cleric character lies to Brother Hesh; narrator-discretion call drops `divine_favor` below threshold; OTEL surfaces the bar transition; cleric attempts to Turn and is blocked; GM panel shows the block reason.
5. The narrator's prompt context block contains the `<learned-magic>` block when a casting character is in scene; the narrator references prepared spells in narration when appropriate; no improvisation of un-prepared spells.
6. Existing `item_legacy_v1` flows (scrolls, wands, potions, cursed weapons) continue to work unchanged; both plugins coexist on `magic_state`.

---

*End of design.*
