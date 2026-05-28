# 59-12

## Problem

**Problem:** When a player character descended from the surface into a dungeon, the game's movement system couldn't figure out where they were — so any attempt to move them triggered a crash instead of actual movement. A secondary bug caused movement commands to fire twice, the second time with missing information, producing a second crash.

**Why it matters:** This blocked all dungeon navigation. Players who entered a dungeon were immediately stuck — unable to move, explore rooms, or continue the session. The entire dungeon-crawl gameplay loop was broken at the entry point.

---

## What Changed

Imagine a hotel where every guest needs a room key to use the elevator. A new guest arrives at the lobby, but the front desk forgets to issue them a key. When they try to call the elevator, it rejects them — not because anything is wrong with the elevator, but because the system doesn't know they exist yet.

That's what was happening. When a PC stepped off the surface and into the dungeon, the game's "room map" (the dungeon graph) wasn't told the character had arrived. So when the movement engine asked the graph "where is this person?", it got silence back — and crashed.

The fix does two things:
1. **Issues the room key on arrival** — the moment a PC enters the dungeon, they're formally registered on the dungeon graph at their entry node.
2. **Fixes a miscounted door knock** — a second bug was causing movement to be requested twice; the second request was missing required details and caused a second crash. The double-tap is now suppressed.

---

## Why This Approach

The dungeon graph is the source of truth for where everyone is. Rather than patching the movement engine to handle "I don't know where this person is" gracefully (which would be a silent fallback — explicitly against this project's principles), the fix ensures the graph is always correct *before* movement is attempted.

The surface→dungeon handoff is a well-defined transition point. Attaching the registration step there is clean, explicit, and impossible to accidentally skip. The kwargs fix is similarly surgical: the double-dispatch was a call-site artifact, not a systemic design flaw, so it's resolved at the source rather than with defensive checks downstream.

---
