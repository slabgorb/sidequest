---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-23: Chassis-vs-chassis ship_combat — materialize the named threat as the Other + ablative ship-hull HP resolution

## Business Context

space_opera/coyote_star is a mechanics-first pack (the Sebastien/Jade lane), and
the dogfight is its signature high-drama loop. Playtest 2026-05-28 drove a
`ship_combat` confrontation off a narrative trigger ("the orrery lights up,
pirates, I scramble to the fighter") and found the encounter **structurally
broken two ways at once** (findings #C3 + #C4): the wrong combatants were
seated, and the fight could never end. The beat engine itself works (SWN beats,
dice→momentum→narration all fire), which is exactly what makes it dangerous —
the prose is convincing while the mechanics are hollow. This story makes a
ship-to-ship fight actually *resolvable* against the *right enemy*, delivering
the crunch the SWN-crunch reintroduction (`docs/superpowers/specs/2026-05-25-swn-crunch-ablative-hp-design.md`)
exists to provide.

The two defects are folded into one story because they are a single
half-implemented slice: #C3 alone yields a correct Other that still can't
resolve; #C4 alone has no valid Other to deplete. They share the
chassis-vs-chassis instantiation seam.

## Technical Guardrails

**Provenance — root-caused, do NOT re-investigate from scratch.** Both defects
were traced during the 2026-05-28 playtest FIXER pass (see
`~/Projects/sq-playtest-pingpong.md` #C3/#C4). The findings below are pinned;
this story implements the fix, it is not a rediscovery.

### #C3 — wrong Other seated (the seating seam)

- The live confrontation dispatch (`sidequest/agents/subsystems/confrontation.py`)
  arrives with `npcs_present=[]` — the router dispatches with a hardcoded empty
  actor list (`sidequest/server/intent_router_pass.py`).
- `instantiate_encounter_from_trigger` (`sidequest/server/dispatch/encounter_lifecycle.py:452`)
  then calls `_npc_fallback_at_location(..., adversarial=True, adversary_only=False)`
  (~line 554). That fallback (`:376`) sets `default_side = "opponent" if adversarial else "neutral"`
  (~line 431) and seats **every** NPC at the player's location — the player's own
  crew — as `side="opponent"`. The pirates were never materialized as NPC
  entities, so the crew are the only bodies in the room.
- **DO NOT** "fix" this by applying the `_npc_is_adversary` filter to the
  non-sealed path. The comment at `encounter_lifecycle.py:410-415` documents that
  seating all present NPCs as opponents is **intentional** for chases/brawls
  (story 59-13's chase dial depends on a neutral-disposition pursuer still
  seating). Blanket-filtering would regress chases across every pack.
- The correct fix is the **gaslight-the-narrator materialization** pattern: when
  the trigger names a threat that is not an existing NPC entity, materialize it as
  adversary NPC(s) via `sidequest/game/world_materialization._apply_npc` (hostile
  disposition / adversarial role) and seat THAT as the Other (ADR-116 "a
  confrontation requires an Other"). The threat description must be threaded from
  the narrator/router into the instantiation seam.

### #C4 — degenerate/unwinnable win condition (the resolution seam)

- `ship_combat` declares `win_condition: hp_depletion`. For that condition the
  constructor **intentionally** synthesizes inert placeholder metrics
  `MetricDef(name="hp", starting=0, threshold=1_000_000)` (`encounter_lifecycle.py:726-735`).
  The `1_000_000` sentinel is **not a bug** — `apply_beat` gates dial resolution on
  `win_condition`, so the placeholders never gate.
- `hp_depletion` is meant to resolve on **ablative HP** (ADR-114) reaching zero.
  But chassis hull HpPools are never seeded for ship-vs-ship, so the dogfight can
  never resolve and beat momentum visibly leaks into the unused player placeholder
  dial (the driver saw the player bar climb 0→2/1000000 on a crit). Personal HP
  (Vela 10/10) is fine — it is the *ship* hull that is uninitialized.
- ADR-114 is **partial — only Part 1 (personal HP) is live**; ship-scale ablative
  HP is Part 2+. Hull HpPools must be seeded from chassis/threat data, and dogfight
  strikes routed through HP depletion (ADR-077 dogfight subsystem,
  `sidequest/game/ruleset/` SWN binding per ADR-117).

### Constraints

- **No Silent Fallbacks / No Stubbing (CLAUDE.md):** if no Other can be
  materialized or sourced, fail loud (`NoOpponentAvailableError`, ADR-116) and
  render prose — never instantiate a fake/stub opponent or seat the crew.
- **OTEL Observability Principle:** the materialized Other and every hull-HP delta
  must emit spans so the GM panel can verify the fight is HP-driven, not
  dial-improvised.
- Builds on **59-17** (dogfight instantiation via the production path, done) and
  **59-19**.

## Scope Boundaries

**In scope:**
- Materialize a narrator-named threat as adversary NPC(s) and seat it as the Other
  for `ship_combat`/`dogfight` triggers.
- Seed real ship-hull `HpPool`s (player ship + threat) from chassis/threat data.
- Route dogfight strike resolution through hull-HP depletion so `hp_depletion`
  actually resolves the encounter.
- OTEL spans for the materialized Other and per-hull-HP deltas.

**Out of scope:**
- Personal-scale ablative HP (ADR-114 Part 1 — already live).
- Chase/brawl location-NPC seating behavior (story 59-13 — must NOT be regressed).
- The beat/dice/momentum engine itself (works; not touched beyond wiring strikes
  to HP).
- Kestrel interior navigation / ship-as-POI (#C2 — explicitly ON HOLD, separate
  brainstorm).
- Multi-ship (>1 threat) fleet encounters unless trivially supported by the
  materialization pass.

## AC Context

1. **Threat materialized, crew never seated:** A `ship_combat`/`dogfight` trigger
   naming a threat not present as an NPC entity materializes adversary NPC(s) and
   seats them `side=opponent`; the player's own crew are never on the opponent
   side. *Test:* trigger with friendly crew in-scene → assert opponent actors are
   the materialized threat, crew are not in `actors` as opponents.
2. **No friendly conscription / fail-loud:** The location-NPC fallback is not used
   to source opponents for a narrative-named-threat ship_combat; if no Other can
   be materialized/sourced, `NoOpponentAvailableError` is raised and prose is
   rendered. *Edge:* empty scene + unnamable threat → fail loud, no encounter.
3. **Chase not regressed:** An existing/new chase test still seats a present
   location NPC as the pursuer/opponent (story 59-13 dial advances).
4. **Real hull metrics seeded:** Chassis-vs-chassis ship_combat seeds hull HpPools
   from chassis/threat data, not `0/0/1_000_000`. *Test:* assert instantiated
   encounter carries non-sentinel hull values for both sides.
5. **Depletion resolves the fight:** A resolved player attack reduces the
   *opponent* ship's hull (not the player's own bar); when a side's hull hits 0
   the encounter resolves (`resolved_encounter=True`). *Test:* drive N rounds of
   successful strikes → hull→0 → resolved.
6. **Observability:** A `participant.joined` span shows the materialized threat as
   the Other (source distinguishes materialized vs router-named vs
   location-fallback); a `state_patch_hp`/`hp_depletion` span fires per hull delta.
7. **End-to-end regression:** A ship_combat triggered by a narrative threat with
   friendly crew present seats the materialized threat (#C3) AND a multi-round
   exchange depletes a hull to zero and resolves (#C4).

## Assumptions

- The narrator/router trigger carries (or can be made to carry) enough threat
  description to materialize a sensible adversary NPC — if it does not, threading
  that signal is part of this story.
- Chassis data (the Kestrel and authored threat chassis) exposes hull/shield
  values usable to seed an `HpPool`; if seed values are missing, content (chassis
  data) may need a small addition (flag as a content sub-task).
- ADR-077 dogfight beats can be retargeted to drive hull-HP depletion without a
  new beat schema.
- This may split into two sub-stories during planning (materialize-Other, then
  ablative-hull-resolution); if so, materialize-Other lands first but neither is
  player-complete alone.
