---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-35: Seat present FRIENDLY companions as side=player combatants in confrontations (ADR-116 / Guitar Solo)

> Source: sq-playtest ping-pong GAP "Allied NPCs don't participate mechanically in
> confrontations — narrated into the fight but never seated as actors" (wry_whimsy/oz,
> sessions `2026-06-02-oz-3` Kalidah fight + `2026-06-03-oz` turn-9 dark-forest fight).
> Architect (White Queen) triaged the design 2026-06-02; operator (Keith) decided allies
> seat as `side:player` mechanical participants, not flavor. The original "Cut story
> 59-30" routing was lost (59-30 became a different political-spine story), so this GAP
> fell through the crack until DRIVER re-surfaced it 2026-06-04. **This story is that
> re-route — the ally-seating work that was never `pf sprint story add`-ed.**

## Business Context

A companion the narrator actively writes into a fight contributes **zero** mechanically.
In the Kalidah fight the Cowardly Lion (Warm/ally) is narrated throwing himself between
Susan and the monsters — *"I am going to roar now"* — but the encounter `actors` list is
only `Susan (player, combatant)` + `The Kalidahs (opponent, combatant)`. Same in the
`2026-06-03-oz` turn-9 dark-forest fight: The Scarecrow and The Tin Woodman (both
`role=companion`, both narrated alongside Susan) are **not seated**; it's a 1-v-1
`footing` dial race with the allies as pure narrative garnish.

This is a narration↔state divorce that breaks two load-bearing commitments:

- **The Guitar Solo (SOUL.md):** companions must be *reachable, mechanical participants*,
  not a silent audience. When the engine doesn't know an ally exists, the player can't
  rely on them, coordinate with them, or watch them take a hit — the band has stopped.
- **ADR-116 (A Confrontation Requires an Other):** explicitly *allows* a confrontation to
  seat more than one participant. The infrastructure already models multi-actor sides; it
  just isn't populated for allies.

The opponent side is already mechanically real (the Kalidahs' `footing` advanced 0→2 as
Susan's beats partly failed), so antagonist representation works. The gap is **allies
only**. For the crunch-axis players (Sebastien/Jade) a narrated ally that the sheet
doesn't know about is exactly the kind of "the prose said it but nothing backed it" miss
the OTEL principle exists to catch.

## Technical Guardrails

**This is reuse, not new infrastructure — the Architect's 2026-06-02 design (honor it):**

- **Seam:** add an ally-seating pass inside `instantiate_encounter_from_trigger`
  (`sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py`), parallel to the
  existing opponent `_npc_fallback_at_location`. Seat present **FRIENDLY-disposition**
  roster NPCs as `side=player` actors.
- **Scene-presence gate:** use the canonical `is_npc_in_scene` predicate
  (`sidequest/game/npc_scene.py`) — do not invent a second presence test. Gate disposition
  via ADR-020 `Attitude.FRIENDLY`. Only seat NPCs that are *both* present and friendly.
- **Resolution engine is already side-driven — do NOT touch it:** `beat_kinds.apply_beat`
  (`sidequest/game/beat_kinds.py`) keys entirely off `actor.side` — a `side=player` actor
  advances the *player* dial, targets opponents, and is strike-reachable.
  `numerical_advantage_modifier` already models engaged `side=player` allies. **Nothing in
  the dial/beat resolution changes.** If you find yourself editing resolution math, stop —
  that's a Design Deviation.
- **Hit-taking (ablative HP, ADR-114):** under the `hp_depletion` win condition, extend the
  existing opponent HP-seeding to `side=player` ally NPCs — back a `CreatureCore` from an
  additive `ally_default_hp`; a downed ally sets `withdrawn=True`. Keep this additive; do
  not regress the opponent seeding.
- **OTEL (the lie-detector — mandatory):** reuse `participant_joined_span`
  (`sidequest/telemetry/spans/encounter.py`) with `side='player', source='ally_present'`,
  plus disposition / beats / seed_hp attributes. The GM panel must be able to read "this
  ally was seated, here's why" — without the span, we can't prove the seating fired vs the
  narrator improvising.

**No-regression invariants (the design preserves these by construction — keep them):**
- The 59-13 chase Other-seater: the FRIENDLY ally gate is *disjoint* from the
  `side=opponent` chase fallback; the ally pass is strictly additive.
- The 59-23 ship_combat materialized-Other path: untouched.
- No new ADR — ADR-116 + the Guitar Solo are *enacted* on the existing seam.

## Scope Boundaries

**In scope:**
- The ally-seating pass in `instantiate_encounter_from_trigger` (present + FRIENDLY roster
  NPCs → `side=player` actors with beats, dial contribution, strike-reachability).
- Ally HP seeding for `hp_depletion` confrontations + `withdrawn` on down.
- The `participant_joined_span(side='player', source='ally_present')` OTEL emission.
- A behavioral wiring test (fixture-driven: real dispatch path + OTEL span assertion — NOT
  a source-text grep) proving a present friendly companion gets seated `side=player`.

**Out of scope:**
- Any change to beat/dial resolution math (`apply_beat`, dial thresholds) — already
  side-driven.
- Hostile/neutral NPC seating, the chase Other-seater, ship_combat (other seams/stories).
- Narrator prose changes — the narrator already writes allies in; this makes the engine
  agree.
- A player-facing UI for ally beats (separate UI story if wanted).

## AC Context

1. **Friendly present companion is seated `side=player`.** In a confrontation
   instantiated while a FRIENDLY-disposition roster NPC is in-scene (per
   `is_npc_in_scene`), the encounter `actors` list includes that NPC as a `side=player`
   combatant — verified on the `2026-06-03-oz` shape (Scarecrow/Tin Woodman alongside
   Susan vs The Unseen Watcher).
2. **The seated ally is mechanically live.** The ally has beats and contributes to the
   *player* dial via the existing `apply_beat`/`numerical_advantage_modifier` paths (assert
   a player-dial delta attributable to an ally beat); no resolution-engine code changed.
3. **Allies can take a hit (hp_depletion).** In an `hp_depletion` confrontation the seated
   ally has a seeded `CreatureCore` HP pool; a downed ally is marked `withdrawn=True` and
   stops contributing.
4. **OTEL proves it.** A `participant_joined_span` fires with `side='player'`,
   `source='ally_present'`, disposition + seed_hp attributes, readable on the GM panel.
5. **No regressions.** 59-13 chase Other-seater and 59-23 ship_combat paths unchanged
   (their suites stay green); hostile/neutral NPCs are NOT auto-seated as allies.
6. **Wiring test.** At least one fixture-driven behavioral test drives the real dispatch
   path and asserts the seating + span (refactor-stable, not a grep).
