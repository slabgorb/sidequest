# Dogfight × SWN Compatibility — Design

**Date:** 2026-05-27
**Status:** Approved (design); pending implementation plan
**Repos:** sidequest-server, sidequest-content
**Related:** ADR-077 (Dogfight Subsystem), ADR-114 (Ablative HP Substrate), ADR-116 (A Confrontation Requires an Other), the SWN RulesetModule epic, space_opera→SWN binding
**Prerequisite:** Story 59-17 (dogfight must instantiate via the production path with a seated opponent) — see "Sequencing" below.

## Purpose

The dogfight (ADR-077) is the single confrontation in the space_opera pack that does **not** run on SWN rules. It resolves via a deterministic 16-cell maneuver cross-product: both pilots secretly commit a maneuver, the engine looks up the `(red, blue)` cell, and the cell *hard-codes* who gets a `gun_solution` and a hit severity (`graze`/`clean`/`devastating` → 5/15/30 vs a flat 10 "hull"). No dice, no attack roll, no pilot skill, no ship stats.

Everywhere else in space_opera, combat is faithful SWN (`d20 + attack_bonus + combat_skill + stat_mod` vs AC, HP ablation per ADR-114, weapon damage dice, armor soak, `hp_depletion` win condition). The mechanics-first players (Sebastien, Jade) specifically miss this crunch — Jade carried a 140-turn space_opera (`coyote_star`) game and felt the absence of the dice.

**Goal:** make the dogfight SWN-compatible **without gutting the maneuver cross-product that makes it the favorite feature.** The maneuver game stays the heart and decides *whether and how well-positioned* a shot is; SWN decides *if it hits and how much it hurts*; HP decides *who dies*.

## Design Principle

> The maneuver cross-product is a **positioning** engine. SWN is the **resolution** engine. They are layered, not merged.

Two orthogonal per-pilot tracks:
- **Energy** (unchanged) — the positioning budget: which maneuvers you can fly (loop costs 30, straight recovers). *Can I get the shot?*
- **HP** (new, authentic SWN) — the survival pool that ablates from weapon damage. *Can I survive the shot?*

## Locked Decisions (from brainstorming)

1. **Core approach:** Layer SWN onto the maneuvers. Keep the cross-product; SWN resolves the shot.
2. **Geometry → dice:** *Cell = opportunity only.* A cell yields `gun_solution` + range + aspect. SWN does 100% of hit and damage. Cells no longer carry damage.
3. **Statline source:** Authentic SWN strike-craft numbers (from the SWN Revised Free Edition SRD).
4. **Ship modeling:** Opponent ace's fighter stats authored on the dogfight ConfrontationDef (reuse the `hp_depletion` opponent-seeding seam); the PC's fighter is a pack-level default frame supplied by the scene/world. Pilot brings real SWN Pilot skill + attributes; the frame brings HP/AC/Armor/gun.
5. **Energy pool:** Keep as the maneuver economy (positioning track), orthogonal to HP (survival track).
6. **Implementation wiring:** Approach A — inline SWN shot resolution inside `resolve_sealed_letter_lookup`.
7. **Dice:** Player shot is a **client-side** Rapier d20 throw (`DiceThrowPayload`); NPC shot is **server-rolled** and surfaced via `DiceResultMessage`.

## Authentic SWN Reference (from the SRD)

**Strike Fighter hull:** HP 8 · AC 16 · Armor 5 · Speed 5 · 1 hardpoint · Fighter class.

**Multifocal Laser** (iconic fighter gun): `1d4` damage, **AP 20**, Fighter-class, 1 hardpoint. AP 20 ≫ Armor 5, so the laser fully penetrates a fighter's armor → ~3 damage per clean hit → **2–3 gun solutions to a kill**. Because the authentic fighter weapon is light (1d4, not the frigate-class 3d6 plasma) and the maneuver game gates *when* you get a shot, a duel runs several turns even at HP 8 — lethal, dramatic, genre-true.

**SWN ship gunnery rule (verbatim intent):** the gunner rolls `d20 + base_attack_bonus + better of INT/DEX mod + Shoot skill`; *for a fighter-class ship, Pilot may be used in place of Shoot.* On a result ≥ target AC, roll weapon damage + the same attribute mod, then subtract the target's Armor (which AP may negate). Ship Armor is **flat damage reduction**, not part of AC. Ship Speed adds to Pilot *checks* (maneuvers), not the gunnery attack — so it stays out of the to-hit (a future positioning hook).

## Turn Data Flow

1. **Commit (unchanged):** both pilots secretly pick a maneuver; energy gates legality. TurnBarrier + existing maneuver-picker UI.
2. **Geometry (unchanged cross-product):** `resolve_sealed_letter_lookup` looks up the `(red, blue)` cell and applies its view deltas to each pilot's `per_actor_state` — bearing, range, aspect, closure, energy, `gun_solution`. Cells carry geometry only.
3. **Shot phase (new), split into two beats:**
   - **(i) Reveal beat:** for each pilot with `per_actor_state["gun_solution"] == True`, compute SWN attack params. **NPC shots roll server-side and are held.** If the **player** has a shot, issue a `DiceRequestMessage` (reusing existing `dispatch_dice_throw` plumbing) and suspend.
   - **(ii) Resolve beat:** on the player's `DiceThrowPayload` (or immediately if only the NPC shoots), resolve **all held shots simultaneously against pre-shot HP** → damage → HP ablation.
4. **Resolve check:** after all shots, run the shared `hp_depletion` check — any pilot ≤0 HP ends the duel.
5. **Narration (unchanged seam):** narrator reads `per_actor_state` + shot outcome, renders cockpit POV prose.

**Mutual gun solutions** (e.g. loop vs kill_rotation) resolve simultaneously against pre-shot HP, so a mutual kill is possible (`mutual_destruction` outcome). The **extend-and-return** rule (geometry resets to merge when the engagement breaks apart with no gun solution) is unchanged.

## Content Changes (sidequest-content)

**(a) Interaction table — strip damage, keep geometry.** `space_opera/dogfight/interactions_mvp.yaml` and the `InteractionCell`/`InteractionTable` models drop `hit_severity`, `damage_increments`, `starting_hull`. Cells keep `pair`, `name`, `shape`, `red_view`/`blue_view` (bearing, range, aspect, closure, energy deltas, `gun_solution`), `narration_hint`, `tags`.

**(b) Opponent ace statline on the dogfight ConfrontationDef.** Reuse the `hp_depletion` opponent-seeding seam (`_seed_combat_hp_depletion_to_npcs`). The dogfight ConfrontationDef gains: `opponent_hp: 8`, `opponent_armor_class: 16`, opponent `armor: 5` (soak), the NPC's `pilot_skill` + `attack_bonus` + attribute mod (reserved keys, like the existing `dexterity`), and the ace's weapon.

**(c) PC fighter frame — pack-level default.** space_opera defines a standard `strike_fighter` frame (HP 8 / AC 16 / Armor 5 / multifocal laser) applied to the PC pilot at dogfight instantiation. The PC's **Pilot skill and attributes come from their real character sheet**; the frame supplies HP/AC/Armor/gun. A world may override the default. No new owned-entity modeling.

**(d) Geometry → to-hit modifier (authored & tunable).** A `geometry_modifiers` block (proposed starting calibration — tunable in content):
- **Aspect:** `tail_on +2`, `quartering +1`, `crossing −1`, `head_on −2`.
- **Range:** `gun +2`, `close 0`, `medium −2`, `far −4`.

**(e) Weapon + Armor-Piercing.** The fighter gun is authored as a weapon with `damage: 1d4`, `armor_piercing: 20`, name "multifocal laser." This requires a new **`armor_piercing` field** on the weapon/damage spec: AP reduces the target's effective Armor before subtraction (`effective_armor = max(0, armor − AP)`).

## Server Changes (sidequest-server)

**(1) SWN module gains a ship-gunnery method.** `SwnRulesetModule.ship_attack_params(...)` keeps the SWN rule (Pilot-in-place-of-Shoot, better of INT/DEX) in the ruleset module. Returns `AttackRollParams(modifier = attack_bonus + pilot_skill + max(INT,DEX) mod + geometry_modifier, target_number = target_fighter_AC)`. Mirrors the existing `attack_params()`.

**(2) `resolve_sealed_letter_lookup` shot phase.** After applying geometry deltas, detect gun solutions and run the two-beat shot phase above (server NPC roll held; player `DiceRequestMessage`/await). Reuses the existing combat dice request/throw round-trip pattern.

**(3) Damage + AP.** Reuse `damage_roll.py`: weapon dice + attr mod; apply `armor_piercing` to reduce effective Armor (`mitigation`); `apply_hp_delta` ablates the target `HpPool`; damage floors at 0.

**(4) Shared depletion check.** Extract the `hp_depletion` check currently inline in `beat_kinds.py` into a shared `check_hp_depletion(enc, edge_resolver)` helper callable from both the beat loop and the sealed-letter path. Sets `enc.resolved`/`enc.outcome`, emits `encounter_resolved_span(source="hp_depletion")`.

**(5) OTEL.** Keep `dogfight.confrontation_started` / `maneuver_committed` / `cell_resolved`. Add `dogfight.shot_attempted` (shooter, target, d20 total, AC, hit/miss, geometry_modifier, source=player|npc) and `dogfight.shot_damage` (dice, AP, armor negated, applied, target HP after). Per CLAUDE.md, every shot decision emits a span so the GM panel can prove the dice fired and weren't improvised.

**(6) Remove dead deterministic damage.** Delete the `damage_increments`/`starting_hull` bookkeeping and cell-damage application; `_apply_view_deltas` keeps applying geometry only.

## Edge Cases & No-Silent-Fallbacks

- **No gun solution (most turns):** geometry/energy change only; no dice, no HP change.
- **Mutual gun solution:** both shots roll against pre-shot HP; double-KO → `mutual_destruction` (lethality policy must handle it).
- **AP vs Armor:** `effective_armor = max(0, armor − AP)`; damage floors at 0 (a fully-soaked hit narrates as a non-penetrating graze).
- **Player dice never arrives (disconnect/timeout):** follow combat's *existing* dice-timeout behavior — no new silent path (no auto-hit, no silently-skipped shot).
- **gun_solution but missing weapon / target AC / target HP:** fail loud (`ValueError`), never a silent no-op. Depends on a seated opponent with stats (see Sequencing).
- **Already-resolved encounter:** guard — no further shots after HP hits 0.
- **Non-SWN pack with a dogfight:** none exists today; assert SWN binding at instantiation and fail loud otherwise.

## Testing

- **Unit:** `ship_attack_params` modifier composition; AP/Armor math (AP≥armor full, AP<armor partial, floor 0); geometry-modifier table (tail_on+gun = +4 … head_on+far = −6).
- **Resolver:** NPC-only gun solution → server-rolled shot ablates player HP; player gun solution → `DiceRequestMessage` issued, resolves on `DiceThrowPayload`; mutual solution → simultaneous resolution + `mutual_destruction` on double-KO.
- **Depletion:** target to 0 → `enc.resolved`, correct outcome, `encounter_resolved_span(source="hp_depletion")`.
- **Wiring test (CLAUDE.md mandatory):** full dogfight through the **production path** — router instantiation → opponent seated from ConfrontationDef stats → maneuver commits → gun solution → shot (server NPC + client player throw) → HP ablation → resolve — asserting OTEL spans fire in order.
- **OTEL:** `dogfight.shot_attempted` / `dogfight.shot_damage` carry the real d20 total, AC, applied damage.
- **Regression:** deterministic `damage_increments` tests retire (replaced by dice); geometry / extend-and-return / energy-economy tests stay green.

## Sequencing

This story sits **on top of Story 59-17** (dogfight confrontation fails to instantiate via the production path — opponent never seated because the router supplies `npcs_present=[]` and sealed-letter skips the location fallback). Without a seated opponent carrying stats, none of the shot resolution above can run. 59-17 must land first.

## Out of Scope

- **PvP dogfights** (both pilots players, both client-rolling). The model assumes the opponent is an NPC ace from the ConfrontationDef.
- **Capital `ship_combat`** (already on `hp_depletion`).
- **Ship Speed → maneuver/positioning modifiers** (future hook; Speed stays out of the to-hit for MVP).
- **First-class owned Ship/Strikecraft entities** with persistence (rejected in favor of the pack-level frame + ConfrontationDef opponent).
- **Cockpit HUD / orrery visualization** of geometry (current UI reuses the beat/maneuver picker).
