# Magic System Implementation — Caverns & Claudes (Loose-Vancian B/X)

**Date:** 2026-05-06
**Amended:** 2026-05-09 — dual-plugin pivot (see Amendment below)
**Status:** Design — partially shipped; remaining tasks tracked in §9
**Target playtest:** Keith + James + Alex + Sebastien, full Sünden session
**Amendment 2026-05-09b — slot bar naming and dual-bar v1 contract**

Spec text in §1, §3, §11 referenced `spell_slots_lN_<actor>` per-level bars. The shipped helper `seed_learned_v1_state` creates `slots_l<N>` bars (no `spell_` prefix); the existing flat `spell_slots` bar (cnc-bx ship) drains via `cast_spell.resource_deltas`. Both shapes coexist in v1: `spell_slots` is the **active drain bar** (compat with the cast_spell beat); `slots_l<N>` is the per-level shape introduced for L2+ readiness, **present but dormant** in v1. The spec is amended to reflect the as-shipped names. Follow-up (when L2 spells ship): migrate `cast_spell.resource_deltas` to drain `slots_l<level>` per cast and retire the flat `spell_slots` bar.

**Companion docs:**
- `docs/design/magic-taxonomy.md` (framework)
- `docs/superpowers/specs/2026-04-28-magic-system-coyote-reach-implementation-design.md` (vertical-slice precedent)
- `docs/superpowers/specs/2026-04-29-magic-system-coyote-reach-architect-addendum.md` (architecture detail)
- `docs/superpowers/specs/2026-05-08-cnc-bx-class-beats-morale-design.md` (cnc-bx class beats — shipped)
- `docs/adr/adr-014-diamonds-and-coal.md` (HP-removed; momentum/edge/fate replacement)

---

## Amendment 2026-05-09 — Dual-plugin pivot

The original 2026-05-06 design called for **migrating C&C from `innate_v1` to `learned_v1`** and rewriting Mage/Cleric `magic_access` accordingly. That conflicts with shipped work in the cnc-bx-class-beats sprint (story 47-9, merged 2026-05-08, plus content PR #193 / server PR #220 merged 2026-05-09):

- Mage/Cleric ship with `magic_access: innate_v1` in `caverns_and_claudes/classes.yaml`.
- The `cast_spell` beat ships in `caverns_and_claudes/rules.yaml` with `class_filter: [Mage]` and `resource_deltas: {spell_slots: -1.0}`.
- `narration_apply.py` reads `beat.resource_deltas` and decrements the actor's `magic_state` ledger (server commit `b4b211d`).
- `game/beat_filter.py:beats_available_for` already gates `cast_spell` on `spell_slots_remaining >= 1.0`.

Trying to migrate C&C onto `learned_v1` would either undo this work or fork it into a parallel path. Both are bad outcomes.

**The new design is dual-plugin:**

1. **`learned_v1` is infrastructure** — catalogs, pydantic models, MagicState collections (`known_spells` / `prepared_spells`), plugin operations (`prepare` / `cast` / `rest` / `turn_undead`), and the spell-catalog loader. **All of this has shipped** on PR #221 / PR #194 (merged 2026-05-09). It is *available* to any plugin that wants to use it.
2. **C&C stays on `innate_v1`** for cast resolution. The `cast_spell` beat keeps its existing slot-drain via `resource_deltas`.
3. **The new wiring** is a **prepared-list gate** in `beats_available_for`: if a beat has a spell selection, the spell must be in the actor's `MagicState.prepared_spells[level]` to be selectable. This is a **single-line addition to the existing filter** — not a new plugin path.

Two plugins, one feature. The spec sections below have been revised in place to reflect this. Where the old text said "`learned_v1` for C&C," it now says "`learned_v1` infrastructure consumed by `innate_v1`'s `cast_spell` beat."

---

## Purpose

Stand the magic-system framework up the rest of the way for **Caverns & Claudes** so a full B/X-flavored Sünden delve can be played end-to-end with **Mage and Cleric mechanically casting prepared spells**, **scrolls/wands/potions/cursed items still firing on the existing `item_legacy_v1` track**, OTEL-observed, ledger-visible, and narrator-grounded.

The framework was vertical-sliced against Coyote Star (space_opera) on 2026-04-28. C&C is the second world to exercise it. Coyote Star validated `item_legacy_v1` and plugin composition; C&C validates **(a)** the `learned_v1` infrastructure layer (catalog loading, prepared-spells state, slot economics) and **(b)** the `innate_v1` `cast_spell` beat as the player-facing surface that consumes that infrastructure.

## Approach

**Content-first, then plugin-first, then wire.** The C&C-side YAML (genre amendments, world magic.yaml, classes hookups, v1 spell catalog) was authored before any Python landed. The `learned_v1` infrastructure was then built against the v1 catalog shape, and the `innate_v1` wiring is the final small step that consumes that infrastructure from the player-facing beat.

## Audience anchors

Per CLAUDE.md, design decisions weigh against the actual playgroup:

- **Keith** (forever-GM-now-player, 40 years tabletop): Moldvay/Cook is the *vibe* of C&C — sending the L1-L6 spell list signals he wants canon authenticity. The narrator must surprise him; mechanical enforcement of slot economics, prepared-list gating, and hard_limits is how it does that.
- **James** (narrative-first, played Rux in caverns_and_claudes): a casting Mage doesn't reduce his agency. The spell catalog is small enough to read quickly; spell prep is a pre-delve choice, not a turn-by-turn rules check.
- **Alex** (slow typist, freezes under pressure): no spellbook-transcription minigame (loose Vancian, not strict). Spell prep is a single declared verb at a safe site, not a multi-step UI. Unprepared-spell declarations should *pulse* not *popup*.
- **Sebastien** (mechanics-first): the GM panel renders the slot economy live — known list, prepared list, slots remaining, cooldown to next prep window. Prepared-list gate decisions are visible as OTEL spans (`beat_filter.cast_spell.rejected_unprepared`). This is *the* Sebastien feature for C&C.

## Locked decisions (this brainstorm, 2026-05-06; amended 2026-05-09)

1. **Loose Vancian** (option B). Mage knows N spells per level; at rest she chooses a daily preparation up to her per-level slots; cast = expended until next rest. No spellbook transcription.
2. **Dual-plugin design** (amended 2026-05-09 — see Amendment above). `learned_v1` ships as infrastructure (catalogs, models, ops). C&C's `Mage`/`Cleric` keep `magic_access: innate_v1`. The `cast_spell` beat draws spells from the `learned_v1`-shaped `MagicState.prepared_spells` collection, gated by `beats_available_for`.
3. **Saves = C&C native attribute checks**. The genre's `resolution_mode: opposed_check` and per-confrontation `stat_check` is the existing primitive. Save-vs-spells maps to the relevant attribute (Sleep → WIS, Fireball → DEX, Hold Person → STR, Charm → WIS). No new save tracks. **Codified rule (new 2026-05-09):** `save.stat: null` means **auto-apply** — the spell's effect lands without a save (Magic Missile is the canonical case). The validator and narration-apply path both honor this branch.
4. **Damage = momentum** (per ADR-014, no HP). Spell damage applies to whatever momentum/edge/fate currency the C&C combat layer uses today. **Open question (§10):** the calibration of "1 momentum damage" against the cnc-bx beat economy is still open — see open question 3.
5. **v1 spell scope = Magic-User L1 + Cleric L1**. Schema designed to scale to L1-L6 / L1-L5 without rework. L2+ is content-authoring scaling, not architecture.
6. **No Elf class** in this pass. B/X race-as-class is a separable decision; the M-U/Elf shared spell list is authoring guidance for later, not v1 scope.
7. **Cleric is Vancian like Mage** (B/X canon: prep-at-rest, expended-on-cast). Not granted-on-the-fly.
8. **Cleric Turn Undead is in scope** as a class-special (not a spell), wired via the existing confrontation auto-fire pattern (`item_legacy_v1` precedent).
9. **Rest-to-prepare is an explicit verb** at any safe site (Lampwick, returning to Sünden Square, declared in-fiction).
10. **No spellbook transcription**. New spells acquired on level-up by player choice from the catalog; found scrolls remain one-shots in the `item_legacy_v1` track.
11. **Cantrip handling is unresolved** (new 2026-05-09 — see open question 2). v1 ships with no `cast_cantrip` beat; the L1 Mage's free repeatable awaits a follow-up design pass.

---

## 1. Content commitment — C&C's magic shape

### Plugin set (v1 ships these — three plugins composed, two surfaces)

- **`item_legacy_v1`** (existing, already wired). Mechanisms active: `discovery`, `mccoy` (a wandsmith counts), `relational`, `faction`. Subtypes used in C&C: `scroll`, `potion`, `wand`, `cursed_weapon`, `reliquary`. The genre's signature trap (cursed items) lives here.
- **`innate_v1`** (existing, wired by cnc-bx). The player-facing surface for spell casting in C&C. Owns the `cast_spell` beat in `combat` confrontation; consumes `learned_v1`-shaped prepared-spells data via the `beats_available_for` gate; drains `spell_slots_<actor>` via `beat.resource_deltas`.
- **`learned_v1`** (shipped 2026-05-09 as **infrastructure**). Owns: spell-catalog loader (`spells/*.yaml`), pydantic models (`Spell` / `SpellCatalog` / `SpellSave` / `SpellComponents` / `SpellReverse`), `MagicState.known_spells` / `prepared_spells` collections, plugin operations (`prepare` / `cast` / `rest` / `turn_undead`), and per-class slot-bar instantiation in `magic_init.seed_learned_v1_state`. **Not plugged into C&C's `magic_access`** — its data structures are read by `innate_v1`'s beat gate.

### Why three plugins

`item_legacy_v1` and `innate_v1` are the **player-facing surfaces**. `learned_v1` is the **data layer** — its operations and state are exposed to other plugins through `MagicState`. This is the same pattern as `item_legacy_v1`'s `bond_<item_id>` ledger bars: ledger state is plugin-scoped data, but consumption can happen across plugin boundaries via the shared `MagicState` and `beat.resource_deltas` grammar.

### Axes

- **World-knowledge** (genre default): `primary: folkloric` — commoners know stories, the Delver knows scrolls work, *and* the Delver knows Sleep can drop a man in his cups, *and* the Delver knows the cleric of the Three Rites can stop a wound from bleeding. Magic is uncommon but not classified or rare.
- **Visibility:** `permitted: [feared, dismissed]`, default `feared`. World may dial.
- **Intensity:** `0.3` (low-medium). B/X-baseline.
- **Player options:** `can_build_caster: true` (FLIP — was false; classes shipped in cnc-bx require this). `can_build_item_user: true`. `chargen_caster_classes: [mage, cleric]`.

### Hard limits

The five existing genre hard_limits stay as-is: no resurrection, no true creation, no unlimited high evocation, no plane shift, no permanence without renewal. **No new world-specific additions for Sünden in v1.** Hard-limit enforcement now runs against any working regardless of source — `item_legacy_v1` activations, `innate_v1` casts, and any future direct `learned_v1.cast` calls all flow through the same validator.

### Cost types

Genre adds `slot` to the existing `[components, backlash]`. **`slot`** is the per-level memorized-and-spent currency, drained by `cast_spell.resource_deltas`. **`components`** still applies (some scrolls/potions still cost ash/blood/the second-to-last torch). **`backlash`** still applies (cursed-item activation, mis-cast spell, the wand that bonded to the wrong delver).

### Ledger bars (v1 — four bar types)

| Bar | Scope | Direction | Threshold(s) | Confrontation hook | Drain mechanism |
|---|---|---|---|---|---|
| `spell_slots_l1_<actor>` | character | down (resets at rest) | 0 → `cast_spell` beat unselectable | — | `beat.resource_deltas: {spell_slots: -1.0}` |
| `bond_<item_id>` | item | bidirectional | low → item refusal, high → loyalty | narrator-discretion (existing) | `item_legacy_v1` ops |
| `item_history_<item_id>` | item | up | accumulates resonance | narrator-discretion (existing) | `item_legacy_v1` ops |
| `divine_favor_<actor>` | character | bidirectional | high → narrator may grant a "free" reliquary effect; low → cleric cannot Turn until restored | narrator-discretion | narrator-discretion + `learned_v1.turn_undead` gate |

`divine_favor` is the only character-scope bar new to C&C. It anchors Cleric's class identity beyond just "Mage but with a different spell list" — the cleric who heals freely, lies, breaks oaths, or fails to honor the rites of Sünden's Three drifts on this bar.

`spell_slots_lN` bars per spell level scale 1:1 with class spell-progression tables; v1 ships `spell_slots_l1` only. Bars are auto-instantiated by `seed_learned_v1_state` per actor at session init (helper exists; remaining wiring tracked in §9).

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
├── arcane_l1.yaml      # Mage L1   (shipped: 12 spells)
├── divine_l1.yaml      # Cleric L1 (shipped: 8 spells, 3 reverses)
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
      stat: null                # null = auto-apply (no save); or DEX/WIS/INT/STR/CON/CHA
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

The schema field `effect_template` is **deterministic** — not a free-form prompt for the narrator. It encodes the mechanical effect that the cast pipeline mutates into game state at parse-time (per ADR-001 / `claude -p` no-reactive-tools). `narrator_register` is the prose flavor that the narrator may quote or paraphrase; it does *not* drive mechanics.

### Damage convention

Spell damage is expressed in the same currency the C&C combat layer uses for momentum loss. v1 scope: Magic Missile = `1 momentum damage, auto-hit`. As C&C combat conventions evolve (edge / fate), the spell catalog evolves with them — the catalog is the surface for tuning, not the plugin code.

### Save convention (codified 2026-05-09)

`save.stat` references the C&C attribute used in the existing `opposed_check` resolution. `save.effect: negates | halves | partial:<text>` describes what success buys the defender. **No new save mechanic.**

**`save.stat: null` is the auto-apply branch** — the spell hits unconditionally; no opposed check is rolled; `save.effect` is ignored. Use cases: Magic Missile (canonical), Light (target is a thing, not a defender), Floating Disc (caster-targeted), Read Magic (self-targeted), all utility spells where the question "does it work?" is yes-by-fiat.

The pipeline branches on `save.stat is None`:
- `None` → skip opposed-check resolution; emit `save.skipped: auto_apply` OTEL attribute; apply `effect_template` directly.
- non-`None` → emit a structured save request to the C&C check resolver with `stat=save.stat`, `dc=class.save_dc_stat`-derived; on success apply `save.effect`'s reduction; on fail apply full `effect_template`.

This rule is enforced by the spell-catalog validator — `save.stat: null` requires `save.effect: none` (any other value is an authoring error: there is nothing for the defender to "halve" if there is no save). Authoring tests must cover this branch.

---

## 3. learned_v1 plugin — infrastructure layer

This section describes the **shipped infrastructure**. It is not a player-facing magic plugin in C&C — its surface is consumed by `innate_v1`'s `cast_spell` beat (see §3.5).

### State (per character, on `MagicState`)

```python
# MagicState additions (shipped in PR #221):
known_spells: dict[str, list[str]]              # actor_id -> list of spell IDs
prepared_spells: dict[str, dict[int, list[str]]] # actor_id -> level -> spell IDs
# spell_slots_<level>_<actor> bars live in MagicState.ledger as numeric bars
```

Plus typed pydantic models for catalog data: `Spell`, `SpellCatalog`, `SpellSave`, `SpellComponents`, `SpellReverse`.

### Plugin operations (shipped on `learned_ops.py`)

- `prepare(state, actor, prep_list)` — at safe site, character chooses spells from `known_spells[actor]` to fill slot budget; updates `prepared_spells[actor]`; emits `learned_v1.prepare` span.
- `cast(state, actor, spell_id, target_spec)` — validates: spell is in `prepared_spells[actor][spell.level]`, slot remaining via ledger lookup, hard_limits pass; returns structured `MagicWorking` (mechanism `studied` for Mage / `granted` for Cleric); decrements slot; emits `learned_v1.cast` span. **Currently called by direct-test paths; not yet called from the runtime player-turn pipeline — see §3.5 for how `innate_v1` consumes this layer instead.**
- `rest(state, actor)` — at safe site, restores all `spell_slots_lN_<actor>` ledger bars to max, clears `prepared_spells[actor]` (re-prep required); emits `learned_v1.rest` span.
- `turn_undead(state, actor, undead_hd)` — Cleric-only; opposed check vs. `divine_favor`; emits `learned_v1.turn_undead` span.

### Class-level slot tables

Stored in `caverns_and_claudes/classes.yaml` per class as `magic_config: ClassMagicConfig`, referenced by `seed_learned_v1_state` at session init:

```yaml
- id: mage
  magic_access: innate_v1     # AMENDED 2026-05-09 — was learned_v1
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

`magic_config` is read by `seed_learned_v1_state` regardless of `magic_access`. The two fields decouple: `magic_access` says which plugin owns the player-facing surface; `magic_config` says how the caster is shaped on the data layer.

---

## 3.5. innate_v1 — the C&C player-facing surface (added 2026-05-09)

This is the layer that turns the `learned_v1` infrastructure into a thing a player at the table can see and do.

### Beat: `cast_spell`

Lives in `caverns_and_claudes/rules.yaml` under `confrontations[id=combat].beats`. Already authored (commit `03a41f5`):

```yaml
- id: cast_spell
  trigger_word: cast_spell
  stat_check: INT
  class_filter: [Mage]
  risk: "Consumes a spell slot; without one, the verb does not exist"
  resource_deltas:
    spell_slots: -1.0
  effect: "The prepared spell unspools — page burns or memory empties"
  narrator_hint: "The morning's memorized syllables, spent in one pass."
```

### Gate extension — the unshipped piece

Today, `game/beat_filter.py:beats_available_for` filters on three checks:

1. `class_filter` whitelist
2. `class_def.encounter_beat_choices` intersection
3. `cast_spell` requires `spell_slots_remaining >= 1.0`

The pivot adds a **fourth check**:

4. **For `cast_spell`, the actor's `MagicState.prepared_spells[level]` must be non-empty.** A Mage who memorized nothing this morning has no `cast_spell` verb. A Mage who memorized two spells but spent them both is in case 3 (no slots remaining). A Mage who has slots but nothing prepared (rare — implies post-rest, pre-prep state) is in case 4.

This is a single-line addition to `beats_available_for` plus a small extension to its signature (it already takes `spell_slots_remaining: float`; it now also takes `prepared_levels: set[int]` or similar).

### Spell selection within the beat

`cast_spell` is currently a single beat with no per-spell variant. The narrator's free-text "what does the player do?" channel still admits "I cast Sleep" — the prompt context (§5) renders the prepared list, the LLM emits a beat selection that names the spell, and the existing structured-output sidecar (ADR-039) carries the spell ID through to `narration_apply`. **No new beat-per-spell explosion needed.**

If the player names an unprepared spell, the beat-filter rejects the turn and the narrator is instructed to render this as a **pulse, not a popup** (per Alex's pacing): the prepared list flickers in the UI, the unprepared spell name is struck through, the player is given a one-line nudge — no modal, no roll-back of game time.

### `resource_deltas` consumption (existing)

`narration_apply.py` reads `beat.resource_deltas` after a successful beat resolve and decrements the relevant `spell_slots_lN_<actor>` bar in `MagicState.ledger`. This logic shipped in cnc-bx (commit `b4b211d`).

Per-level slot routing: the current `resource_deltas: {spell_slots: -1.0}` drains a shared bar; the L1-only v1 scope means there is *one* bar (`spell_slots_l1_<actor>`) so the routing is implicit. When L2+ ships, the resource-delta key needs to vary with the cast spell's level — likely `{f"spell_slots_l{level}": -1.0}` resolved at apply-time. Tracked as a follow-up; not blocking v1.

### Cast resolution path

When `cast_spell` resolves successfully via `narration_apply`:

1. The structured sidecar carries `spell_id` and `target_spec`.
2. The cast handler looks up the spell in the world's `WorldMagicConfig.spell_catalogs[tradition]`.
3. **Save branch:** `if spell.save.stat is None` → auto-apply `effect_template`; else emit a structured save request to the C&C check resolver (`save.stat`, `dc` derived from caster's `save_dc_stat`); branch on result per `save.effect`.
4. Effects mutate game state (momentum, edge, fate, status conditions per `effect_template`).
5. OTEL: emit `innate_v1.cast` (player-surface span) carrying `spell_id`, `validator_outcome`, `save_skipped` boolean, `save_result` (when applicable), `damage_applied`.

The `learned_v1.cast` span continues to exist for direct calls (test paths, future plugins); `innate_v1.cast` is the production spell-cast span for C&C.

### Context block payload

`build_magic_context_block` extends to include, when the actor has `MagicState.prepared_spells` populated:

```
<learned-magic actor="rux" tradition="arcane">
  <known>magic_missile, sleep, charm_person, light, read_magic, detect_magic</known>
  <prepared>
    <l1>magic_missile, sleep</l1>
  </prepared>
  <slots><l1>1/2 remaining</l1></slots>
</learned-magic>
```

The narrator sees the prepared list and the slots remaining. Decisions to cast remain the player's; the narrator narrates outcomes parsed from the structured cast result. **Per ADR-009, the narrator must not improvise un-prepared spells** — the prompt-level invariant is that any spell named must appear in the `<prepared>` block.

---

## 4. Content surface — the YAML diff

### `caverns_and_claudes/magic.yaml` (amend)

- `permitted_plugins: [item_legacy_v1, innate_v1, learned_v1]` (amended 2026-05-09 — `learned_v1` is permitted as data-layer infra, even though no class names it as `magic_access`).
- `cost_types: [components, backlash, slot]`
- `narrator_register` rewritten: not "magic is found, not cast" — *both*. Mages who survive long enough to delve carry 1-2 prepared workings; clerics carry 1-2 granted ones; everyone carries scrolls and potions and prayers to whatever they think will help. Cursed items remain the genre's signature trap.
- Design-notes block (commented-out fields, lines 67-105) updated: `chargen_caster_classes: [mage, cleric]`, `can_build_caster: true`, `manifestation.modes: [item_channeled, innate_with_prepared_list]`.

### `caverns_and_claudes/rules.yaml` (already amended, cnc-bx)

- `magic_level: none` retired per the in-file note.
- Combat confrontation has per-class beats including `cast_spell` with `class_filter: [Mage]` and `resource_deltas`.
- No further change in this design pass.

### `caverns_and_claudes/classes.yaml` (amend — partial)

- `mage.magic_access: innate_v1` (amended 2026-05-09 — was `learned_v1` in original spec; cnc-bx shipped `innate_v1`).
- `mage.magic_config: { tradition: arcane, slots_by_class_level: {...}, starting_known_spells: 2, save_dc_stat: INT }` — **needs to be added**; cnc-bx didn't ship this block. Tracked in §9.
- `cleric.magic_access: innate_v1` (same amendment).
- `cleric.magic_config: { tradition: divine, slots_by_class_level: {...}, starting_known_spells: 2, save_dc_stat: WIS, turn_undead: true }` — **needs to be added**.
- `fighter.magic_access` and `thief.magic_access` stay `null`.

### `caverns_and_claudes/spells/arcane_l1.yaml` (shipped)

Twelve M-U L1 spells in C&C voice (Moldvay canon): Charm Person, Detect Magic, Floating Disc, Hold Portal, Light, Magic Missile, Protection from Evil, Read Languages, Read Magic, Shield, Sleep, Ventriloquism. Merged in PR #194 on 2026-05-09.

### `caverns_and_claudes/spells/divine_l1.yaml` (shipped)

Eight Cleric L1 spells in C&C voice (Moldvay canon): Cure Light Wounds (reverse: Cause Light Wounds), Detect Evil, Detect Magic, Light (reverse: Darkness), Protection from Evil, Purify Food and Water, Remove Fear (reverse: Cause Fear), Resist Cold. Merged in PR #194 on 2026-05-09.

### `worlds/caverns_sunden/magic.yaml` (new — needs to be added)

```yaml
world: caverns_sunden
genre: caverns_and_claudes

intensity: 0.3                  # genre baseline; Sünden does not amplify

active_plugins:
  - item_legacy_v1
  - innate_v1
  - learned_v1                  # data-layer; consumed by innate_v1's cast_spell

world_knowledge:
  primary: folkloric

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
  # spell_slots_lN bars are auto-instantiated by seed_learned_v1_state
  # per actor at session init — no static authoring needed in the world file.

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

`LedgerPanel` (existing, inside `CharacterPanel.tsx` per Coyote Star spec) extends to render the magic block when the character has a populated `MagicState.known_spells[actor]`. Three-tier display anticipated (per 2026-05-09 brainstorm — see open question 4 for confirmation):

- **Sebastien tier (numbers):** known spells list (collapsible), prepared spells per level with slot indicator (●●○), explicit "0/2 slots remaining" text, threshold markers on `divine_favor`.
- **Alex tier (prose):** "You know six tricks. You memorized two this morning. You have one cast left." Soft-wrapped, no parenthetical mechanics.
- **James tier (flavor):** terse poetic register matching narrator voice. "The Words sit heavy. One left." (default tier per genre register.)

Tier selection is per-player UI preference; default per genre is the flavor tier. Tier toggles are a genre-pack prompt-tuning surface, not a per-spell authoring concern.

UI behaviors:
- "Prepare spells" action button (enabled at safe sites; disabled mid-delve).
- Cleric only: `divine_favor` bar with current value and threshold markers.
- Cleric only: "Turn Undead" action button (enabled when undead in scene).
- **Unprepared-spell declaration is a pulse, not a popup.** When the beat-filter rejects a `cast_spell` for an unprepared spell, the prepared list flickers (CSS pulse animation, ~600ms), the unprepared spell name appears struck-through-but-visible in the cast-attempt log, and a one-line narrator nudge replaces the player's input. No modal. No undo prompt. Game time does not roll back.
- **Spent spells stay visible struck-through** until next rest, so the player can see what they had this morning. Sleep cast at turn 4 doesn't disappear; it just becomes ~~Sleep~~.

GM panel (OTEL dashboard) gets the same block in its character-state pane plus per-cast event log: who cast what, validator outcome, save result (or `auto_apply` skip), damage applied, slot bar transition.

---

## 6. OTEL spans

Spans split across plugin boundaries per §3.5:

| Span | Owner | Required attrs | Optional attrs |
|---|---|---|---|
| `learned_v1.prepare` | learned_v1 | actor_id, tradition, prepared_spells, slots_max | location, last_prep_turn |
| `learned_v1.rest` | learned_v1 | actor_id, slots_restored, location | turns_since_last_prep |
| `learned_v1.turn_undead` | learned_v1 | actor_id, undead_hd, divine_favor, outcome | undead_count, undead_type |
| `learned_v1.cast` | learned_v1 | actor_id, spell_id, validator_outcome | (test/direct paths only) |
| `innate_v1.cast` | innate_v1 | actor_id, spell_id, validator_outcome, slot_consumed, save_skipped | target_spec, save_stat, save_result, damage_applied |
| `innate_v1.cast_rejected_unprepared` | innate_v1 | actor_id, spell_id_attempted, prepared_at_level | turn_index |
| `confrontation.beat_filter` | beat_filter | actor_id, class, beat_id, decision (allowed/rejected_class/rejected_slots/rejected_unprepared) | confrontation_id (already shipped — extend with the new rejection reason) |
| `learned_v1.backlash` | learned_v1 | actor_id, spell_id, backlash_reason | hard_limit_violated |

Existing `magic.*` and `item_legacy_v1.*` spans unchanged.

---

## 7. Hard limits / constraints

- **ADR-001 — `claude -p` no reactive tools.** Spell resolution is parse-time-deterministic. Effects encoded in `effect_template`; cast resolution is mutated into game state by the existing `narration_apply.py` pipeline plus the new save-branch logic. Narrator does not "decide" outcomes mid-generation.
- **ADR-009 — narrator cannot narrate unlisted actions.** The prepared-list gate is the data side of this; the prompt-level invariant says the narrator may only name spells in the `<prepared>` block.
- **ADR-014 — no HP.** Damage applies to momentum/edge/fate per the C&C combat layer's existing currency. Spell catalog tracks damage in those terms, not in d6/d8 rolls (those are a B/X surface that doesn't translate; the *outcome shape* is what we keep, not the dice).
- **No silent fallbacks.** If `worlds/caverns_sunden/magic.yaml` is missing, current behavior is silent skip (per `magic_init.py` lines 65-69). v1 keeps that doctrine — silent skip is *correct* for worlds that genuinely have no magic. C&C now guarantees its worlds will author the file; absence in a future C&C world is an authoring bug, not a graceful degradation.
- **No stubbing.** `learned_v1` ships with all its v1 operations (prepare, cast, rest, turn_undead) wired end-to-end. The pivot to `innate_v1`-as-surface does **not** mean `learned_v1.cast` becomes dead code — it remains the data-layer cast operation invoked from tests and from any future plugin that wants direct catalog-driven casting.
- **Audience pacing.** Spell preparation is one declared verb; spell casting is one declared verb. No multi-turn UI rituals. Alex must be able to play a Mage without the table waiting on her. Unprepared-spell declarations pulse, never popup.

---

## 8. Out of scope (deferred)

- L2-L6 Magic-User spells (content scaling).
- L2-L5 Cleric spells (content scaling).
- Elf class (B/X race-as-class; separable decision).
- Spellbook transcription / scrolls-add-to-known-list (option A from brainstorm; un-locked, available later).
- Multi-session confrontations on `divine_favor` / "The Wall Notices".
- Cross-character spell sharing (e.g., cleric cast on mage).
- Counter-magic (`anti_magic_zone`, `save_or_die`, `destroy_source` are listed in genre magic.yaml design notes but are not v1 mechanics).
- **Mid-delve spell swap** (open question 5; defer until playtest pressure says yes).
- **Cantrips / `cast_cantrip` beat** (open question 2; v1 ships without).
- Per-level `resource_deltas` routing for L2+ slot drains (§3.5 follow-up).

---

## 9. Implementation order — shipped vs. remaining

### Shipped (PR #220, #193, #221, #194 — all merged 2026-05-09)

- ✅ `MagicWorking.mechanism` extended with `studied`/`granted`; `spell_id` and `slot_level` fields.
- ✅ `ClassDef.magic_config: ClassMagicConfig` typed and re-exported.
- ✅ `MagicState.known_spells` and `prepared_spells` collections + helper methods.
- ✅ `magic/spell_catalog.py` — pydantic models and loader with duplicate-id rejection and save-effect validator.
- ✅ `WorldMagicConfig.spell_catalogs` discovery via `magic_loader`.
- ✅ `magic/plugins/learned_v1.{yaml,py}` registered in `MAGIC_PLUGINS`.
- ✅ `magic/learned_ops.py` — `prepare` / `cast` / `rest` / `turn_undead`.
- ✅ `magic_init.seed_learned_v1_state` helper (function exists; not yet called from session init — see remaining task 1).
- ✅ `caverns_and_claudes/spells/arcane_l1.yaml` (12 spells).
- ✅ `caverns_and_claudes/spells/divine_l1.yaml` (8 spells, 3 reverses).
- ✅ `cast_spell` beat in `caverns_and_claudes/rules.yaml` with class filter and `resource_deltas`.
- ✅ `game/beat_filter.beats_available_for` with class filter + slot gate.
- ✅ `narration_apply.py` consumes `beat.resource_deltas` to decrement slot bars.
- ✅ `confrontation.beat_filter` OTEL span (per-PC filter decisions).

### Remaining (one cohesive story)

The remaining work is **memorization wiring** — the gate, the init, the save branch, the cantrip placeholder, the UI panel, and the smoke playtest.

1. **Wire `seed_learned_v1_state` into `init_magic_state_for_session`.** Helper exists; production init path doesn't call it. Adds `MagicState.known_spells[actor]`, `MagicState.prepared_spells[actor]={}`, and `spell_slots_lN_<actor>` ledger bars at session start. Wiring test required (per CLAUDE.md "Every Test Suite Needs a Wiring Test").
2. **`classes.yaml` `magic_config` blocks** for Mage and Cleric (B/X canon slot tables). Authoring task in `sidequest-content`.
3. **`worlds/caverns_sunden/magic.yaml`** — author with `divine_favor` bar and active_plugins list (see §4 for canonical content).
4. **Extend `beats_available_for`** with the prepared-list gate (§3.5). Signature gains a `prepared_levels: set[int]` or `prepared_spells: dict[int, list[str]]` parameter; `cast_spell` rejects when no spells are prepared at any level. OTEL: `confrontation.beat_filter` gains `decision: rejected_unprepared`.
5. **Cast resolution save-branch** in the cast handler — `save.stat is None ⇒ auto-apply` per §2. Spell-catalog validator rejects `save.stat: null` paired with non-`none` `save.effect`. OTEL: `innate_v1.cast` gains `save_skipped: bool`.
6. **Per-level `resource_deltas` routing** — currently drains `spell_slots` (level-implicit); needs to drain `spell_slots_l<spell.level>` at apply-time. Out of scope until L2 ships, but the routing is a one-line change so do it now if convenient.
7. **Context block** — `magic/context_builder.py` renders `<learned-magic>` block per §3.5 when `prepared_spells[actor]` is populated. ADR-009 invariant test required.
8. **UI** — `LedgerPanel` magic block (known / prepared / slots / divine_favor / Turn Undead button). Pulse animation on unprepared rejection. Strikethrough on spent spells. Three-tier display flag (defer the toggle UI; ship the flavor tier as default).
9. **`innate_v1.cast` OTEL span** — the player-facing span complementing `learned_v1.cast` (which stays for direct/test calls).
10. **Integration test** — Mage in Sünden: chargen → walk to Grimvault → prepare Sleep + Magic Missile at safe site → cast Magic Missile (auto-apply, no save) → cast Sleep (WIS save, defender either succeeds or fails) → exhaust slots → return to Lampwick → rest → re-prepare. All five OTEL spans fire. Test runs against a real session, not mocks (per CLAUDE.md "No Stubbing" and integration-test feedback memory).
11. **Smoke playtest** — full Sünden delve with Mage and Cleric playable; OTEL dashboard observed by Keith.

These items can be authored as a single story (suggested ID range 47-N continuing the magic epic) since they compose into one playtest acceptance.

## 10. Open questions

1. ~~All architectural decisions locked.~~ **Five open questions emerged in the 2026-05-09 brainstorm.** Listed below.
2. **`cast_cantrip` mechanics** — deferred. The L1 Mage's free repeatable (B/X has implicit cantrip behavior; modern D&D codified it) is not v1 scope. Open: does C&C ship cantrips at all? If yes, are they (a) a separate beat with no slot cost, (b) a class-special like Turn Undead, or (c) zero-level slots that auto-refresh per encounter? **Resolution path:** revisit after L1 playtest. Keith's pacing call.
3. **Momentum scale calibration** — the cnc-bx beats use momentum at some scale (1-3? 1-10?). Magic Missile = "1 momentum damage, auto-hit" needs to be checked against `melee_strike` / `sneak_attack` damage to confirm it's neither overpowered nor a wet noodle. **Resolution path:** read the cnc-bx beat YAML for momentum values, calibrate spell catalog's `effect_template` numbers in a content-only pass.
4. **UI three-tier display ordering** — per §5, three tiers anticipated (Sebastien numbers, Alex prose, James flavor). Open: per-player toggle vs. genre default vs. character-class default. **Resolution path:** ship flavor tier as default, build the toggle in a follow-up story once playtest pressure says someone wants it.
5. **Mid-delve spell swap** — wild card from the brainstorm. Could a Mage who finds a moment of safety mid-delve re-prep one spell? B/X canon says no (full rest required). Story-Now pressure says maybe. **Resolution path:** defer until playtest. If Alex says "I wish I could swap Read Magic for Sleep right now" we revisit.

---

## 11. Success criteria

1. A Mage character in Sünden can be created via the existing 5-scene chargen, walks down to Grimvault, casts Magic Missile on a creature in the Sorting Floor, and the cast appears in the OTEL dashboard as an `innate_v1.cast` span with `spell_id=magic_missile`, `save_skipped=true` (auto-apply branch), `slot_consumed`, and `damage_applied`.
2. The same character returns to the Lampwick, declares "I prepare spells" in fiction, and the slots reset; OTEL shows a `learned_v1.rest` span and a `learned_v1.prepare` span.
3. A Mage tries to cast Fireball (not in `prepared_spells`); the beat-filter rejects it; UI pulses (does not popup); OTEL emits `confrontation.beat_filter` with `decision=rejected_unprepared`; game time does not roll back.
4. A Cleric character casts Cure Light Wounds on the Mage; momentum is restored; OTEL spans fire correctly with `save_skipped=true` (CLW is null-stat); `divine_favor` is unchanged (acting in role).
5. A Cleric character lies to Brother Hesh; narrator-discretion call drops `divine_favor` below threshold; OTEL surfaces the bar transition; cleric attempts to Turn and is blocked; GM panel shows the block reason.
6. The narrator's prompt context block contains the `<learned-magic>` block when a casting character is in scene; the narrator references prepared spells in narration when appropriate; ADR-009 invariant holds (no improvisation of un-prepared spells).
7. Existing `item_legacy_v1` flows (scrolls, wands, potions, cursed weapons) continue to work unchanged; all three plugins coexist on `magic_state`.
8. Sebastien can read the GM panel and explain to Alex what just happened mechanically: "she had two L1 slots, she cast Magic Missile so now she has one, and the spell auto-hit because Magic Missile has no save."

---

*End of design. Amended 2026-05-09.*
