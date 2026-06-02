# Narrative

## Problem Statement
**Problem:** When the game engine encounters a character who has just entered the world but has no backstory yet, it was silently skipping the step that indexes that character for later retrieval — meaning the character could become "invisible" to the AI narrator. A previous sprint (75-6) fixed this skip, but there was no automated check to prove the fix would survive future code changes. Without a guard, the bug could quietly return undetected.

**Why it matters:** The AI narrator depends on an accurate, up-to-date index of every character in the scene. If a freshly-introduced character is never indexed, the narrator may act as if they don't exist, ignore their presence, or handle follow-up interactions inconsistently. For the playgroup — especially in sessions with several new NPCs introduced at once — this produces subtle, hard-to-diagnose narration failures that look like "the AI just forgot about that person."

---

## What Changed
Think of the game engine like a post office. When a new character walks into the game, the engine is supposed to hand that character a "file this person" ticket so the AI can look them up later. Story 75-6 fixed a broken rule that was preventing new characters (ones with no history yet) from getting that ticket.

Story 76-1 added an alarm on the mailroom door. Now, if anyone accidentally re-breaks that rule in the future — whether by refactoring nearby code or merging an incompatible change — an automated test immediately fires and says "STOP: the new-character filing step just stopped working." No human has to notice the bug creeping back in; the alarm catches it.

The only code added was the alarm itself. Zero production behavior changed.

---

## Why This Approach
When a bug fix handles a genuinely subtle edge case — a character who exists but has no history yet — it's the kind of code that can get accidentally reverted by someone who doesn't realize the case matters. Standard test coverage tends to focus on the common path (character + full history) and miss the rare one (character + zero history).

The test was written as a "mutation test": the team deliberately broke the fix, confirmed the alarm fired, then restored the fix and confirmed the alarm went quiet. That means the alarm is proven to catch exactly the failure it's guarding against — not just passing because nothing ran.

This pattern — pin the fix, prove the pin bites — is the lowest-cost, highest-confidence way to prevent a one-line regression from causing hours of narration debugging in a live session.

---

## Before/After
| | Before (76-1) | After (76-1) |
|---|---|---|
| **Scenario** | Character "Borin" enters the game with no backstory | Same |
| **Indexing step fires?** | Yes (75-6 fixed it) | Yes (unchanged) |
| **If someone accidentally reverts 75-6...** | Bug returns silently; narrator can't find Borin; no test fails | `test_dispatch_worker_spawns_on_entity_only_turn` FAILS immediately in CI |
| **How fast is the catch?** | Could go undetected for sessions or sprints | Caught at the next `pytest` run, before merge |
| **Production code changed?** | N/A | No — test-only addition (+62 lines, one file) |
| **Tests passing?** | 5/6 (new test not yet written) | 6/6 GREEN |
