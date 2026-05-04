# Rig MVP — Coyote Star Vertical Slice

**Date:** 2026-04-29
**Status:** Design — pre-implementation
**Target playtest:** Keith solo, fresh Coyote Star session, Kestrel speaking
**Companion docs:**
- `docs/design/rig-taxonomy.md` (framework)
- `docs/design/magic-plugins/item_legacy_v1.md` (subsystems are item-legacy items)
- `docs/design/confrontation-advancement.md` (output catalog — extended here)
- `docs/superpowers/specs/2026-04-28-magic-system-coyote-reach-implementation-design.md` (peer slice — magic system uses the same wiring patterns this spec follows)

## Purpose

Stand up the rig framework far enough that **Kestrel speaks in narration with bond-tier-correct name-forms, and `the_tea_brew` runs end-to-end with bond delta, span emission, GM-panel visibility, and cliché-judge enforcement**. Vertical slice — one class, one chassis, one confrontation. Everything else (Bright Margin, Tide-Singer, Hegemonic patrol cruiser, hardpoints, subsystems, damage history, registration, dogfight wiring, ancillary model, crew_awareness, UI sheet) is explicitly deferred.

The slice is graded against the 2026-04-26 Coyote Star playthrough's central observation: Kestrel was the dominant register in 13 of 18 turns, name-forms upgraded across the session, and the chassis-as-speaker felt mechanically real even though there was no mechanical backing. This slice puts mechanical backing under that one register and proves the framework can carry it.

## Approach

**Wire-up first, author second, deferral aggressive.** Per CLAUDE.md "Don't Reinvent — Wire Up What Exists." Most of the framework's surface is already present in different shapes:

- **Genre/world loader** (`sidequest/genre/loader.py`, `magic_loader.py`) — extended, not duplicated.
- **Pydantic models** (`sidequest/genre/models/`) — new file `chassis.py` joins the existing 26.
- **NpcRegistryEntry projection** (`sidequest/game/session.py:145`) — chassis is projected through this for narrator prompt context, but lives in its own state container.
- **Magic plugin scaffold** (`sidequest/magic/plugins/item_legacy_v1.py`) — pattern reused for chassis-state plugin lookups; bond ledger reuses `LedgerBar` (`sidequest/magic/state.py:32`).
- **Confrontation dispatch** (`sidequest/server/dispatch/confrontation.py`) — `the_tea_brew` is one more entry in the existing dispatch path.
- **OTEL span infrastructure** (`sidequest/telemetry/spans/`) — new `rig.py` joins existing `npc.py` and `magic.py`.
- **Confrontations.yaml in coyote_star world** — already loads; add one entry, do not fork the file.
- **Room movement** (`sidequest/game/room_movement.py`) — used unchanged; Galley is a room.

The slice is implementable in a single coherent change because most of the work is wiring, not new infrastructure.

## Audience anchors

Per CLAUDE.md, weighed against the actual playgroup:
- **Keith** (forever-GM-now-player, solo first run): the slice must surprise him. The bond-tier name-form upgrade has to land *as a moment* — Kestrel calling him "Mr. Jones" instead of "Pilot" because something happened, not because a counter ticked. Mechanical enforcement of the bond-tier register and the cliché-judge name-form check are how it does that.
- **Sebastien** (mechanics-first): the GM panel must show `rig.bond_event`, `rig.voice_register_change`, and `rig.confrontation_outcome` spans firing in concert during the_tea_brew. If he can't see the bond tick from the panel, the slice fails for him.
- **James** (narrative-first): the slice must not require fast typing or special commands. The_tea_brew is auto-fire when the player navigates to the Galley with bond_tier ≥ neutral; no `/tea` command needed. Defer command surfacing.
- **Alex** (slow typist): same as James — auto-fire pacing, no time pressure on a single confrontation.

## Locked decisions (this brainstorm)

1. **Scope = thin vertical slice (option c).** One class (`voidborn_freighter`), one chassis (Kestrel), one confrontation (`the_tea_brew`), no hardpoints/subsystems/damage/registration. Genre-complete and world-complete options deferred to follow-on specs.
2. **Existing `the_salvage` collision deferred.** Coyote Star's existing `the_salvage` (item-discovery shape) stays untouched in this slice. The taxonomy's rig-shaped `the_salvage` (subsystem-strip shape) lands when subsystems land. The slice's `the_tea_brew` is additive only.
3. **Chassis state lives in its own container (option a) with a projection into `npc_registry` for narrator prompt continuity.** Chassis registry is the source of truth (typed, schema-rich); npc_registry receives a projected entry for each chassis at world-load and on every chassis state mutation. No dual-write — one writer, one reader path.
4. **Pre-bonded at world-load.** Kestrel ships with `bond_strength: 0.45, bond_tier: trusted` in `rigs.yaml`. Without a non-zero seed, the name-form-upgrade demo doesn't fire in a single session. This matches the playthrough's reference state (Zee had been her captain "for at least three jumps' worth of patch kits").
5. **Tone axis backport is minimal.** `confrontation-advancement.md` gains an optional `register: dramatic | intimate | domestic | quiet` field. Existing confrontations are NOT retrofitted — `register` defaults to `dramatic` if absent. The_tea_brew is the first authored `intimate` confrontation; future confrontations declare register at authoring time.
6. **Advancement output ratification is minimal.** Only the outputs `the_tea_brew` actually produces are added to `confrontation-advancement.md` in this slice: `bond_strength_growth_via_intimacy`, `bond_tier_threshold_cross`, `chassis_lineage_intimate`. The full taxonomy catalog (`chassis_tier`, `subsystem_acquisition`, `damage_history_entry`, `registration_state_change`, etc.) ratifies in follow-on specs.
7. **Three OTEL spans only.** `rig.bond_event`, `rig.voice_register_change`, `rig.confrontation_outcome`. The other ten span types in the taxonomy ship with their respective subsystems (subsystem_install/remove with hardpoints; damage_resolution with dogfight; ancillary_loss with ancillary support; etc.).
8. **Cliché-judge gets one new hook in this slice.** Hook #7 from the taxonomy: name-form-vs-bond-tier mismatch is YELLOW. The other 14 hooks ship with their respective subsystems — they have nothing to fire against until the schema fields they reference exist on chassis.
9. **Auto-fire trigger for the_tea_brew.** When the player character moves into the Galley interior_room with bond_tier ≥ `familiar`, the_tea_brew is eligible to auto-fire (with cooldown so it doesn't fire every Galley visit). No player-facing command. Reuses the existing confrontation dispatch path.

---

## 1. Content commitment

### `space_opera/chassis_classes.yaml` — slice scope

```yaml
version: "0.1.0"
genre: space_opera
classes:
  - id: voidborn_freighter
    display_name: "Voidborn Freighter"
    class: freighter
    provenance: voidborn_built
    scale_band: vehicular
    crew_model: flexible_roles
    embodiment_model: singular
    crew_awareness: surface
    psi_resonance:
      default: receptive
      amplifies: [void_singing, far_listening]
    default_voice:
      default_register: dry_warm
      vocal_tics:
        - "almost-but-legally-distinct from a laugh"
        - "theatrical sigh exactly long enough to register as judgement"
        - "drops to a discreet murmur"
      silence_register: approving_or_sulking_context_dependent
      name_forms_by_bond_tier:
        severed: "Pilot"
        hostile: "Pilot"
        strained: "Pilot"
        neutral: "Pilot"
        familiar: "Mr. {last_name}"
        trusted: "{first_name}"
        fused: "{nickname}"
    interior_rooms:
      - id: cockpit
        display_name: "Cockpit"
        default_occupants: [pilot]
      - id: engineering
        display_name: "Engineering"
        default_occupants: [engineer]
      - id: galley
        display_name: "Galley"
        bond_eligible_for: [the_tea_brew]
      - id: deck_three_corridor
        display_name: "Deck Three Corridor"
        narrative_register: liminal_warm
    crew_roles:
      - id: pilot
        operates_hardpoints: "*"
        bond_eligible: true
        default_seat: cockpit
    # Deferred to follow-on: hardpoints, chassis_death, full crew_roles list.
```

**Deferred classes:** `prospector_skiff`, `hegemonic_patrol_cruiser`, `fighter`, `station_hull`, `courier_skiff`. Their absence is documented in a `coverage:` block at the file head.

### `worlds/coyote_star/rigs.yaml` — slice scope

```yaml
version: "0.1.0"
world: coyote_star
genre: space_opera
chassis_instances:
  - id: kestrel
    name: "Kestrel"
    class: voidborn_freighter
    OCEAN: { O: 0.6, C: 0.7, E: 0.4, A: 0.5, N: 0.5 }
    voice:
      # Inherits class default; declares override-overrides only.
      vocal_tics:
        - "almost-but-legally-distinct from a laugh"
        - "theatrical sigh exactly long enough to register as judgement"
        - "dry as bonemeal"
        - "drops to a discreet murmur"
    interior_rooms: [cockpit, engineering, galley, deck_three_corridor]
    bond_seeds:
      - character_role: player_character
        bond_strength_character_to_chassis: 0.45
        bond_strength_chassis_to_character: 0.45
        bond_tier_character: trusted
        bond_tier_chassis: trusted
        history_seeds:
          - "muscle memory from at least three jumps' worth of patch kits"
    # Deferred to follow-on: damage_history, registration, subsystems, prior_captains.
```

**Deferred instances:** Bright Margin, Tide-Singer, Hegemonic patrol cruisers. Their absence is documented in a `coverage:` block at the file head.

### `worlds/coyote_star/confrontations.yaml` — additive entry

Append to existing file (do not rewrite, do not fork):

```yaml
- id: the_tea_brew
  label: "The Tea Brew"
  register: intimate
  plugin_tie_ins: [item_legacy_v1]   # for the tea-set itself, when authored as a subsystem-item
  rig_tie_ins: [voidborn_freighter]
  auto_fire: true
  fire_conditions:
    interior_room_present: galley
    bond_tier_min: familiar
    cooldown_turns: 6
  rounds: 1
  resource_pool:
    primary: bond
  description: |
    Site-of-life ritual. Captain offers a personal preference (incense,
    music, a tea variety) to the chassis. The chassis registers the
    offering. The room remembers.
  outcomes:
    clear_win:
      mandatory_outputs:
        - bond_strength_growth_via_intimacy
        - chassis_lineage_intimate
    refused:
      mandatory_outputs: [chassis_lineage_intimate]
```

### `confrontation-advancement.md` — additive sections

Three new outputs registered:
- `bond_strength_growth_via_intimacy` — small bond delta (default `+0.04` character side, `+0.06` chassis side) on intimate/domestic-register confrontation. Compoundable, the primary engine of Wayfarer-register bond.
- `bond_tier_threshold_cross` — fires when a bond_strength change crosses a tier boundary. Triggers narrative callbacks; may unlock new confrontation eligibility.
- `chassis_lineage_intimate` — warm-small history entry on the chassis ledger. Distinct from `chassis_lineage_dramatic` (which lands with `the_wrecking` etc.).

One new optional schema field on confrontations: `register: dramatic | intimate | domestic | quiet`, default `dramatic`. Existing entries unchanged. Future confrontations declare register at authoring time.

---

## 2. Server changes

### 2.1 New module: `sidequest/game/chassis.py`

Pydantic models (single file, joins the 38 other game-state files):

- `ChassisVoice` — `default_register`, `vocal_tics`, `silence_register`, `name_forms_by_bond_tier` (dict).
- `ChassisInteriorRoom` — `id`, `display_name`, `narrative_register?`, `default_occupants?`, `bond_eligible_for?`.
- `ChassisCrewRole` — `id`, `operates_hardpoints` (`"*"` or list), `bond_eligible`, `default_seat?`.
- `ChassisBondLedgerEntry` — `character_id`, `bond_strength_character_to_chassis`, `bond_strength_chassis_to_character`, `bond_tier_character`, `bond_tier_chassis`, `history` (list of `BondHistoryEvent`).
- `ChassisInstance` — `id`, `name`, `class_id`, `OCEAN`, `voice`, `interior_rooms`, `bond_ledger` (list), plus `class` join at projection time.
- `BondHistoryEvent` — `turn_id`, `delta_character`, `delta_chassis`, `reason`, `confrontation_id?`.

Bond-tier derivation function `derive_bond_tier(strength: float) -> str` shared with `chassis_classes.yaml` consumers. Tier thresholds are constants in this file.

### 2.2 New module: `sidequest/genre/models/chassis.py`

Pydantic models for `chassis_classes.yaml` (genre layer):
- `ChassisClass` — `id`, `display_name`, `class`, `provenance`, `scale_band`, `crew_model`, `embodiment_model`, `crew_awareness`, `psi_resonance`, `default_voice` (`ChassisVoice` reused), `interior_rooms`, `crew_roles`. Optional: `hardpoints`, `chassis_death` (deferred).
- `ChassisClassesConfig` — top-level pydantic for the YAML.

Loaded by extending `sidequest/genre/loader.py` — one new method `load_chassis_classes(genre_path) -> list[ChassisClass]`. Returns empty list if file absent (graceful degradation: rig-less genres are valid).

### 2.3 New module: `sidequest/genre/models/rigs_world.py`

Pydantic for `rigs.yaml` (world layer):
- `RigsWorldConfig` — `version`, `world`, `genre`, `chassis_instances` (list of `ChassisInstanceConfig`).
- `ChassisInstanceConfig` — what's in the YAML; resolved into `ChassisInstance` at world-load by joining with the genre's `ChassisClass`.

Loaded by extending world-load path. Resolves into game-state `ChassisInstance` records and writes to a new `session.chassis_registry: dict[str, ChassisInstance]`.

### 2.4 Session state

`sidequest/game/session.py`:
- New field on the session: `chassis_registry: dict[str, ChassisInstance]`.
- World-load path materializes `chassis_registry` from `rigs.yaml` and projects each chassis into `npc_registry` so narrator prompt context keeps working unchanged.
- Projection function `project_chassis_to_npc_registry(chassis) -> NpcRegistryEntry` lives next to the registry. Called on world-load and on any chassis mutation that affects projected fields (currently only `name`; later `last_seen_location` etc.).

### 2.5 Voice resolver

`sidequest/agents/subsystems/chassis_voice.py` (new):

```python
def resolve_chassis_name_form(
    chassis: ChassisInstance,
    speaker_to: Character,
) -> str:
    """Returns the chassis's current address-form for the named character."""
```

Looks up the bond_ledger entry for the character, derives the active tier via `bond_tier_chassis` (chassis-side asymmetry), maps to the chassis's `voice.name_forms_by_bond_tier` dict, fills `{first_name}`, `{last_name}`, `{nickname}` from the character record. Returns string. Used by the narrator prompt builder when generating chassis-as-speaker dialogue.

Wired into `sidequest/agents/prompt_framework/core.py` — when the prompt builder sees a chassis in `npc_registry`, it ALSO pulls the chassis's voice block from `chassis_registry` and passes name-form + vocal_tics + register into the chassis-as-speaker section of the prompt.

### 2.6 Bond mutation path

New module `sidequest/game/chassis_bond.py`:
- `apply_bond_event(chassis_id, character_id, delta_character, delta_chassis, reason, confrontation_id) -> BondEventResult`.
- Writes to the bond_ledger; appends a `BondHistoryEvent`; recomputes both tiers; if either tier crossed a boundary, records that on the result.
- Emits `rig.bond_event` span via the new spans module.
- If voice register changes (name-form upgrade), emits `rig.voice_register_change` span and updates the projected `npc_registry` entry's projection cache (not the projected fields themselves — voice-register is a derived prompt field, not a registry field).

### 2.7 OTEL spans

`sidequest/telemetry/spans/rig.py` (new file, joins `npc.py`, `magic.py`):

Three span emitters in this slice:

```python
def emit_rig_bond_event(*, chassis_id, actor_id, side, delta_character,
                        delta_chassis, tier_character_before, tier_character_after,
                        tier_chassis_before, tier_chassis_after,
                        confrontation_id, register): ...

def emit_rig_voice_register_change(*, chassis_id, actor_id,
                                   register_before, register_after,
                                   triggering_event): ...

def emit_rig_confrontation_outcome(*, chassis_id, confrontation_id, register,
                                   branch, outputs): ...
```

Each emitter calls into `watcher_hub` like the existing `npc.py` and `magic.py` patterns. GM panel picks them up automatically via existing dashboard wiring (per ADR-090).

The other taxonomy spans (`rig.maneuver`, `rig.subsystem_install`, `rig.subsystem_remove`, `rig.damage_resolution`, `rig.salvage`, `rig.embodiment_action`, `rig.crew_awareness_read`, `rig.ancillary_loss`, `rig.refusal`, `rig.registration_event`) are not authored in this slice — their consumers don't exist yet.

### 2.8 Confrontation dispatch

`sidequest/server/dispatch/confrontation.py` already routes confrontations. The_tea_brew gets:
- A new auto-fire eligibility check at room-movement time (player enters Galley + bond_tier_min met + cooldown elapsed). Lives in `sidequest/game/room_movement.py` post-move hook.
- An outcome-application path that writes `bond_strength_growth_via_intimacy` and `chassis_lineage_intimate` into the chassis state, calling `apply_bond_event` and `apply_chassis_lineage_intimate`.
- Emits `rig.confrontation_outcome` span on resolution.

`apply_chassis_lineage_intimate(chassis_id, narrative_seed, turn_id)` is a new function in `chassis.py` — appends to the chassis's `lineage` field (new field on ChassisInstance, slice-introduced).

### 2.9 Cliché-judge hook

The cliché-judge agent (read-only, per its description) gets one new check in its rubric file:
- **Hook 7 (slice scope):** When narrator prose contains a chassis address-form (e.g., the chassis calls the captain by name), the form must match the chassis's current `bond_tier_chassis`. Mismatch is **YELLOW (suspicious)**. Source: chassis_registry.

Cliché-judge already reads world state; this is one more rule in its prompt. No code change in cliché-judge itself; just a documentation update at `pf-cliche-judge` definition or the rig-taxonomy doc.

---

## 3. Wiring tests

Per CLAUDE.md "Every Test Suite Needs a Wiring Test." Three required:

1. **End-to-end Galley fixture test** — `tests/integration/test_rig_kestrel_tea_brew.py`. Loads coyote_star world fixture, advances player into Galley, asserts the_tea_brew auto-fires, asserts bond_strength_chassis_to_character increased by 0.06, asserts a `rig.bond_event` span fired with correct attributes, asserts the projected npc_registry entry still resolves Kestrel by name.
2. **Voice resolver wiring test** — `tests/unit/test_chassis_voice.py`. Loads Kestrel at `bond_tier_chassis = trusted` for a fixture character with first_name "Zee", asserts `resolve_chassis_name_form` returns `"Zee"`. Drops bond_strength below the trusted threshold via `apply_bond_event`, asserts the next call returns `"Mr. {last_name}"` form. Tests the name-form *change* mechanism on a single boundary the slice authors (familiar ↔ trusted), not the `fused` boundary which has no nickname source in the slice.
3. **Span-firing wiring test** — `tests/integration/test_rig_spans_emit.py`. Triggers a synthetic the_tea_brew outcome, asserts all three rig spans fired (bond_event, voice_register_change *if tier crossed*, confrontation_outcome) with correct attribute sets.

The end-to-end test is the load-bearing one — it's the one that catches "schema exists but isn't wired into anything that reads it."

## 4. Demo path

What "done" looks like, played through:

1. Keith starts a fresh Coyote Star session (`just up`, new save).
2. World loads. `chassis_registry` has Kestrel; `npc_registry` projection has Kestrel as a `ship_ai`. Bond ledger is at `0.45 / 0.45, trusted / trusted`.
3. Narrator's first prose mentions Kestrel; chassis-as-speaker fires; Kestrel addresses Keith by `"{first_name}"` (her current trusted-tier form).
4. Keith navigates into Galley (room movement).
5. The_tea_brew auto-fires. Narrator prose offers a small-ritual moment. Outcome: clear_win.
6. Bond delta applies: chassis side `+0.06` → `0.51` (still trusted, but closer to fused threshold). Lineage entry written. Spans fire.
7. GM panel shows: `rig.bond_event` (delta and tier-state visible), `rig.confrontation_outcome` (outputs visible). Sebastien-mode test passes.
8. Subsequent narrator prose continues with name-forms appropriate to the new bond state. If a future tea_brew (cooldown elapsed) crosses into `fused`, the next chassis dialogue uses the nickname form, and `rig.voice_register_change` fires alongside `rig.bond_event`. Cliché-judge would flag a mismatch if it occurred; it doesn't.

If any step does not occur, the slice is incomplete.

## 5. Out of scope (explicit)

The following are **named here so they do not creep into this slice**. Each becomes a follow-on spec.

- **All other space_opera chassis classes** — `prospector_skiff`, `hegemonic_patrol_cruiser`, `fighter`, `station_hull`, `courier_skiff`.
- **Bright Margin, Tide-Singer, named Hegemonic ships** — instances beyond Kestrel.
- **Hardpoints, subsystems, `installed_in` integration** — locked decision S2 in the taxonomy stays unimplemented; no `rig.subsystem_install`/`remove` in the slice.
- **Damage history** — schema slot in pydantic is a future field, not authored in slice.
- **Registration** — slot-only, deferred. No `the_customs_inspection`.
- **Dogfight wiring** — no `rig.damage_resolution` spans, no per-location HP routing.
- **Ancillary embodiment** — Kestrel is `singular`. The whole ancillary register (Justice of Toren) is a future world's problem.
- **`crew_awareness` enforcement** — Kestrel is `surface` per spec but the cliché-judge hook for `>= biometric` empathy claims is not added here.
- **Magic plugin chassis interfaces** — the taxonomy's MI2 says innate_v1's place-loci, bargained_for_v1's patron-scopes, learned_v1's prerequisite_gates, divine_v1's sacred-sites all accept chassis IDs. None of those interfaces is touched in this slice; magic plugins are unchanged.
- **All other rig confrontations** — `the_refit`, `the_wrecking`, `the_heroic_stand`, `the_mutiny`, `the_sale`, `the_customs_inspection`, `the_bond`, `the_refusal`, `the_long_quiet`, `the_engineers_litany`, `the_shared_watch`, `the_maintenance_communion`, `the_naming`, `the_crew_change`, `the_storm_passage`. None authored.
- **Existing `the_salvage` rewrite** — current item-discovery shape stays. Rig-shaped subsystem-strip variant lands when subsystems land.
- **Full advancement output catalog ratification** — only the three outputs `the_tea_brew` produces are added; the rest land with their producing confrontations.
- **Tone axis retrofit on existing confrontations** — they keep the default `dramatic`; only new authored confrontations declare register.
- **UI surfacing (chassis sheet)** — slice ships GM-panel visibility (via spans) only. Player-facing chassis sheet is a follow-on UI spec.
- **Open-issue items** — cross-genre passport, mid-mission swap, group-mind chassis, mounts as chassis, body-prosthetic as chassis, ancillary individuation, multi-chassis MP turns. All deferred.

## 6. Sequencing

This slice is one spec → one implementation plan → one PR. The follow-on roadmap (named here for orientation, not committed):

1. **rigs MVP slice** — *this spec*.
2. **Coyote Star world-complete** — Bright Margin, Tide-Singer, Hegemonic patrol cruisers; remaining intimate confrontations (`the_engineers_litany`, `the_shared_watch`, `the_long_quiet`); registration friction + `the_customs_inspection`.
3. **Hardpoints + subsystems** — locked decision S2 lights up; `installed_in` pointers; the rig-shaped `the_salvage` rewrite; `rig.subsystem_install`/`remove` spans; cliché-judge hooks 5/6.
4. **Dogfight wiring** — `rig.damage_resolution` spans from the dogfight scene-mechanic; per-location HP routing; damage_history ledger; `the_wrecking` and `the_heroic_stand` confrontations.
5. **Magic plugin chassis interfaces** — innate_v1 place-locus, bargained_for_v1 patron-scope, learned_v1 prerequisite_gate against chassis-state.
6. **Player-facing UI** — chassis sheet, bond visualization, subsystem inventory.
7. **Ancillary support** — first imperial_radch / radch_remnant world authoring.

Each follow-on adds its own outputs to `confrontation-advancement.md`, its own spans, its own cliché-judge hooks. The slice's three-output / three-span / one-hook minimum sets a per-feature ratification template the follow-ons follow.

## 7. Open questions deferred to implementation

- **Cooldown unit** for `the_tea_brew` — is `cooldown_turns: 6` the right shape? Real-time, turn-based, scene-based? Pick during implementation; correct in playtest if wrong.
- **Bond seed character_id resolution** — `rigs.yaml` uses `character_role: player_character` because the player character's id isn't known at world-load. Resolved at character-creation time (player chargen → bond_seed copied with player.id). Verify the existing chargen pipeline has a hook.
- **`bond_tier_threshold_cross` granularity** — does crossing trusted → fused fire a single output or both `bond_strength_growth_via_intimacy` AND `bond_tier_threshold_cross`? Proposal: both, where the threshold cross is metadata on the same outcome. Confirm at implementation.
- **Voice block inheritance precedence** — when the world `voice` overrides the class `default_voice`, is it whole-block replacement or field-level merge? Proposal: field-level merge with world fields winning. `vocal_tics` lists are replaced, not concatenated, to keep authoring control tight.
- **Nickname source** — the `{nickname}` name-form template has no source field in this slice (no nickname in `bond_seeds` or chargen). The slice authors only the `severed → trusted` portion of the name-form ladder; `fused`-tier dialogue won't fire because nothing seeds the nickname. Proposal: defer nickname authoring until either (a) chargen gains an optional nickname field, or (b) a confrontation (`the_naming` from the taxonomy) lands in a follow-on. The slice's behavior at `bond_tier_chassis = fused` is "fall back to `{first_name}` form with a fallback-warning span attribute" — i.e., the schema permits the tier, the prose just stays at the previous form.

## 8. Sign-off

This spec is the smallest authored slice that proves the rig framework can carry the chassis-as-speaker register the playthrough demonstrated. Done = Kestrel speaks, bond moves, spans fire, GM panel shows the work, cliché-judge can call a name-form lie.

— Count Rugen, taking meticulous notes
