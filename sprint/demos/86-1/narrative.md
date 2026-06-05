# Narrative

## Problem Statement
**Problem:** Road Warrior combat was a stage magician with no magic — every fight was pure improv, with zero mechanical backing. The game engine was telling the narrator "someone got shot" but had no rules to determine whether the shot landed, how bad the wound was, or when the fight was actually over. Why it matters: Keith's playgroup (particularly Sebastien and Jade, both mechanics-first players) could feel the difference between a fight that *resolved* and one that just... stopped narrating. Real tension requires real stakes, and real stakes require a working damage model.

---

## What Changed
Imagine a board game where the combat cards were all blank — the GM had to make up results every time. This story printed the real rules on the cards.

Road Warrior now runs on the **Cities Without Number (CWN)** ruleset — the same proven system that powers the neon_dystopia genre pack. Every driver character has a proper set of six core stats (Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma) instead of improvised flavor names that meant slightly different things each session. The old "Driver Edge" resource pool — which sounded cool but did nothing — was removed and replaced with a real **ablative HP system**: Shock damage chips away at your stamina, Trauma cuts deeper, Mortal wounds mean you're on borrowed time, and Major Injuries leave marks. Combat now has a finish line: the engine tracks hit points, applies damage math, and declares a winner when HP hits zero — no narrator judgment call required.

---

## Why This Approach
Three reasons CWN was the right fit:

1. **Proven seams, not new plumbing.** The engine already speaks CWN natively — neon_dystopia proved the architecture. Road Warrior is a content binding, not an infrastructure project. That means faster delivery and fewer places for things to break.

2. **Ablative HP fits the genre.** Post-apocalyptic road combat is *supposed* to feel grinding and cumulative. Shock damage that adds up over a chase, a Mortal wound that forces a hard choice — that's Road Warrior, not D&D. HP tracks that story naturally.

3. **The wiring checklist exists for a reason.** Previous Without-Number integrations (SWN for space_opera, WWN for elemental_harmony) each discovered the same three missing wires late in review. This story applied the checklist up front, including mandatory telemetry tests that prove the engine is actually firing — not just that the code compiles.

---

## Before/After
| Dimension | Before (Road Warrior, pre-86-1) | After (Road Warrior, 86-1) |
|---|---|---|
| **Combat resolution** | Narrator improvises — no engine involvement | Engine runs CWN damage math, declares winner at HP=0 |
| **Attributes** | Flavor names (`injury_system`, non-standard) | Standard CWN six: STR/DEX/CON/INT/WIS/CHA |
| **Damage model** | "Driver Edge" pool (visual, no mechanical effect) | Ablative HP: Shock → Trauma → Mortal → Major Injury tiers |
| **Win condition** | Narrator judgment | `hp_depletion: true` fires when opponent HP reaches 0 |
| **OTEL observability** | No combat spans — impossible to verify engine ran | `cwn_strike`, `shock_damage`, `win_condition_met` spans on every turn |
| **Character classes** | Genre-specific flavor names (untranslated) | CWN class + foci system, properly bound |
| **Test coverage** | Pack loads (schema only) | Pack loads + dual-dial migration + cwn spans fire on real turn |
| **Player experience** | Fights feel soft — outcomes arbitrary | Damage accumulates turn-by-turn; tension is mechanical, not narrative |
