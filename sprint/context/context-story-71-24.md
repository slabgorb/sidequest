---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-24: perseus_cloud personal-melee combat beat bank — distinct from ship/dogfight beats

## Business Context

The 2026-05-27 `coyote_star` MP playtest (and the broader `space_opera`/SWN line that
`perseus_cloud` rides on) exposed that there is no personal-melee combat beat bank. When a
player swings a vibroblade, tackles, or stabs in a corridor or station bar, the engine has
no melee-specific beats to surface — the closest authored confrontation is `combat`
("Firefight"), whose beat bank is entirely ranged-firearm (`shoot`, `take_cover`,
`overload` the weapon, `retreat`). The `combat` type's `intent_verbs` already *advertise*
melee (`strike, slay, swing, stab` — `rules.yaml:321`), so a melee action matches into
Firefight and then the player is offered "Blaster bolts sear the corridor" beats for a
knife fight. That is exactly the "Claude wings convincing prose with no mechanical backing"
failure the OTEL principle exists to catch.

This matters for the load-bearing audience. Sebastien and Jade are mechanics-first and
specifically miss the crunch when the confrontation engine mis-fires (they carried a
140-turn `coyote_star` game *while* confrontation was broken). A melee fight that resolves
through blaster beats reads as the engine improvising — the opposite of "good enough to
fool a career GM." Delivering a distinct melee bank that ablates HP through the SWN strike
channel (ADR-114) restores legible, melee-appropriate mechanical resolution.

## Technical Guardrails

**Where confrontations and their beats live (content):**
- `sidequest-content/genre_packs/space_opera/rules.yaml` — `confrontations:` list. Each
  entry is keyed by `type:` (loaded as `confrontation_type`, alias at
  `sidequest-server/sidequest/genre/models/rules.py:428`) and carries `label`, `category`,
  `intent_verbs`, `on_intent_mismatch`, `resolution_mode`, `win_condition`, `mood`, and a
  `beats:` list. Current personal-combat type is `type: combat` ("Firefight",
  `rules.yaml:318`) — ranged beats only: `shoot`, `take_cover`, `overload`, `retreat`.
  `type: ship_combat` (`:221`) and `type: dogfight` (`:439`) are vehicle banks and must be
  left untouched as the contrast cases.
- Beat shape is `BeatDef` (`sidequest-server/sidequest/genre/models/rules.py:118`): `id`,
  `label`, `kind` (`BeatKind` — strike/brace/angle/push), `base`, `stat_check`,
  `damage_channel`, `attack_bonus`, `combat_skill`, optional `deltas`, etc. Mirror the
  Firefight `shoot`/`overload` beats: `kind: strike`, `damage_channel: strike`,
  `stat_check: Physique` for melee swings; `kind: brace` for a parry/guard.

**SWN ruleset + win condition (must match Firefight):**
- `space_opera` binds `ruleset: swn` (`rules.yaml:11`). Personal combat resolves
  `resolution_mode: beat_selection` + `win_condition: hp_depletion` (ablative HP, ADR-114,
  `sidequest/game/creature_core.py` `HpPool`). The melee bank must use the same pair so it
  routes through the same `hp_depletion` resolution as Firefight — see the combat
  cross-field validators in `rules.py:528-565` (a `category: combat` +
  `win_condition: hp_depletion` confrontation requires `opponent_default_stats` with
  `hp`/`armor_class` seed keys, exactly as Firefight declares at `rules.yaml:331-344`).

**How a type is matched + how beats are filtered:**
- Intent→type matching keys off `intent_verbs` per type (`RulesConfig.intent_verbs_by_type`,
  `rules.py:1202`; mismatch handling `on_intent_mismatch` at `:475`). The melee verbs
  (`swing, stab, slash, lunge, grapple, melee`, etc.) must move/copy onto the new melee
  type so they no longer resolve into Firefight.
- Beat availability per class is filtered by `sidequest/game/beat_filter.py` against
  `class.encounter_beat_choices` and per-beat `class_filter`. The loader validates these
  cross-references (`sidequest/genre/loader.py:576-619`): every `class_filter` class must
  exist in `classes.yaml`, every class's `encounter_beat_choices` must reference real beat
  ids, and any class in `allowed_classes` must have non-empty `encounter_beat_choices`.
  **Adding new melee beat ids means the eight `allowed_classes` (Officer, Operative, Pilot,
  Engineer, Medic, Smuggler, Diplomat, Soldier) may need their `encounter_beat_choices`
  updated, or the new beats must be universal (`class_filter: null`) so they survive
  beat_filter Gate 1.**

**Dispatch + lookup:**
- `sidequest/server/dispatch/confrontation.py` resolves a `ConfrontationDef` by exact
  string match on `confrontation_type` (`:91-101`) — no fuzzy fallback. A new melee type id
  is reachable only once `intent_verbs`/match logic routes to it.

**OTEL (the proof seam):**
- `encounter.confrontation_initiated` (`sidequest/telemetry/spans/encounter.py:88`) carries
  `confrontation_type`; `encounter.beat_applied` (`:54`) carries `beat_id`;
  `confrontation_intent` (`sidequest/telemetry/spans/confrontation_intent.py`) carries
  `matched_type` / `matched_tokens`. These spans are how a test proves a melee action
  surfaced melee beats, not Firefight beats.

**Do NOT touch:** `ship_combat`, `dogfight`, `chase`, `negotiation` confrontations; the
`swn.py` ruleset module; `creature_core.py` HpPool. This is a content addition (+ minimal
intent-verb rerouting and class beat-choice wiring), not an engine change.

## Scope Boundaries

**In scope:**
- A new personal-melee confrontation type in `space_opera` `rules.yaml` (e.g.
  `type: melee`) with a melee-appropriate `beats:` bank (strike/brace/push kinds, Physique
  stat checks, strike damage_channel), `category: combat`,
  `resolution_mode: beat_selection`, `win_condition: hp_depletion`, and
  `opponent_default_stats` seeding `hp`/`armor_class`.
- Reroute melee `intent_verbs` (`swing, stab, slash, lunge, grapple`, etc.) off `combat`
  (Firefight) onto the new melee type so a melee action matches melee.
- Whatever class `encounter_beat_choices` / `class_filter` wiring is needed for the new
  beat ids to pass `loader.py:576-619` validation and surface to the eight allowed classes.
- OTEL coverage demonstrating a melee confrontation initiates with the melee
  `confrontation_type` and applies melee `beat_id`s.

**Out of scope:**
- Ship/dogfight/chase beat banks (untouched).
- New SWN engine mechanics, new weapon items, or melee-specific damage rules beyond reusing
  the existing strike `damage_channel` + ablative HP path.
- Porting the melee bank to other `space_opera` worlds (`coyote_star`, `aureate_span`) or
  other genre packs — this story is scoped to the `space_opera` genre bank as consumed by
  `perseus_cloud`. (If the bank is authored at genre tier it is inherited by all
  `space_opera` worlds; that is acceptable and is the natural home per "crunch in the genre."
  No per-world melee override is required.)

## AC Context

**AC1 — a personal-melee confrontation surfaces melee-appropriate beats (not ship/dogfight
beats).**
- A confrontation initiated from a melee intent must resolve to the melee
  `confrontation_type`, NOT `ship_combat` or `dogfight`. Test: drive a melee action through
  the real intent-match path and assert the resolved `ConfrontationDef.confrontation_type`
  is the melee type (or assert via the `confrontation_intent` span's `matched_type`).
- The beats offered must be the melee bank, not Firefight's. Test: load the `space_opera`
  pack, fetch the melee `ConfrontationDef`, assert its `beats` ids are the melee set and
  that none of them are `shoot`/`overload`/`take_cover` (the Firefight ranged ids), and
  that none are `broadside`/`evasive_maneuver` (ship) or `straight`/`kill_rotation`
  (dogfight).
- Edge: the new beats must pass the loader cross-reference validators — a beat id absent
  from any `allowed_classes` class's `encounter_beat_choices` (when class-filtered) or a
  `class_filter` naming an unknown class must raise `PackError` at load. A passing-load test
  proves the wiring is consistent.

**AC2 — resolvable through the production path with OTEL proof.**
- A melee confrontation must run to resolution via `hp_depletion` (a combatant reaching
  0 HP), using the same SWN strike/ablative-HP path Firefight uses. Test: seat an opponent
  with the melee type's `opponent_default_stats` (`hp`, `armor_class`), apply melee strike
  beats, assert HP ablates and the encounter resolves on 0 HP.
- OTEL proof (per the OTEL Observability Principle / "wiring test" rule): assert
  `encounter.confrontation_initiated` fired with `confrontation_type` == the melee type, and
  at least one `encounter.beat_applied` span carries a melee `beat_id`. This is the
  integration assertion that the bank is wired end-to-end, not just present in YAML.
- Edge: a Firefight (ranged) action must STILL match `combat` and surface ranged beats —
  i.e. rerouting melee verbs must not break ranged matching. A regression test should drive
  a `shoot`-style intent and assert it still resolves to `type: combat`.

## Assumptions

- **Genre-tier authoring is correct.** Personal-melee crunch is mechanics, so the bank
  belongs in the `space_opera` GENRE `rules.yaml`, inherited by `perseus_cloud` (and other
  worlds). No `perseus_cloud`-specific melee override is needed. If the table wants
  melee-but-world-flavored, that is flavor and out of scope here.
- **The intent-match layer is the right reroute point.** Melee verbs currently live on
  `combat` (`rules.yaml:321`); moving them to the new type is sufficient to redirect melee
  actions. If matching is instead driven elsewhere (e.g. the IntentRouter's narrator-chosen
  type), the dispatch lookup at `confrontation.py:91` is still the canonical resolution and
  the test should anchor on the resolved `confrontation_type` regardless of match site.
- **ADR-114 ablative HP (Part 1) is live** and `win_condition: hp_depletion` resolves for
  `category: combat` confrontations exactly as Firefight already proves at runtime.
- **The eight `allowed_classes` should all get melee beats** (melee is universal, unlike a
  pilot-only maneuver). Default to universal beats (`class_filter: null`) unless the spec
  calls for class-gated melee signatures.

If any assumption proves wrong (e.g. melee must be a per-world bank, or matching is
narrator-driven not verb-driven), log a Design Deviation and notify SM before widening
scope.
