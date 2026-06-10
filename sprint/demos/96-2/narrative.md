# Narrative

## Problem Statement
**Problem:** Characters in the *Barsoom* world (a sword-and-planet setting inside the Heavy Metal genre pack) were receiving a special "Earthman" racial bonus even when they weren't Earthmen — and the bonus was being stamped as coming from the genre ruleset rather than the world where it belongs. **Why it matters:** Race-specific bonuses that bleed through tier boundaries corrupt character sheets silently. A player who picks a Red Martian or Green Martian ends up with stats they didn't earn, the character creation screen shows misleading attribution ("Race" when it should say "Barsoom World Trait"), and any downstream system that audits trait provenance — advancement, balance checks, the GM panel — reads garbage.

---

## What Changed
Think of the game's content as a layer cake: the bottom layer is the genre (WWN rules, shared across all worlds in the pack), and on top sits each specific world (Barsoom, with its own characters, lore, and race rules).

The Earthman boon is a Barsoom thing — it only makes sense in that world, for that race. But the code was handing it out at the genre layer, where every character in every Heavy Metal world could pick it up. Worse, it was labeling the bonus as coming from "Race" (a character-choice category) instead of "Barsoom World Trait" (where it actually lives in the content files).

The fix moves the boon back where it belongs — applied only when the world is Barsoom *and* the character's race is Earthman — and corrects the provenance label so the audit trail is accurate.

---

## Why This Approach
The content system has a strict two-tier rule: genre-tier data is shared and world-agnostic; world-tier data is local and world-specific. The Earthman boon violated that contract by living in world content but being applied by genre-level code. Rather than patching the symptom (guarding the genre-tier application point with a world-name check), the fix relocates the application logic entirely to the world-tier resolution path. That's the correct seam — it means adding future world-specific race boons will naturally go through the same path without needing extra guards, and the genre layer stays clean.

---

## Before/After
| | **Before (broken)** | **After (fixed)** |
|---|---|---|
| Red Martian character traits | Includes Earthman Strength boon | No Earthman boon (correct) |
| Green Martian character traits | Includes Earthman Strength boon | No Earthman boon (correct) |
| Earthman character traits | Includes Earthman Strength boon | Includes Earthman Strength boon (correct) |
| Trait provenance label | `source: Race` | `source: Barsoom World Trait` |
| Resolver that applies the boon | Genre-tier (shared across all Heavy Metal worlds) | World-tier (Barsoom only) |
| GM panel audit column | `genre:heavy_metal` | `world:barsoom` |
| Failing test on old build | `test_earthman_boon_not_applied_to_non_earthman` — FAIL | PASS |
