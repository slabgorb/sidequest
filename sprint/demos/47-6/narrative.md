# 47-6

## Problem

**Problem:** The tea ritual — a key bonding moment between the player and their ship's AI in the Coyote Star campaign — was completely broken. Every time a player entered the Galley, nothing happened. No ritual, no bond growth, no record of the moment. The mechanic had been built and marked "done" in the previous sprint story, but a solo playtest revealed that across 22 turns, zero tea rituals fired despite multiple eligible moments.

**Why it matters:** SideQuest's narrator (Claude) is very good at improvising convincing story moments. Without the underlying mechanics actually running, the game engine was recording zero state changes while the narrator wrote beautiful prose about tea. For Keith — a 40-year GM who knows exactly what a real mechanical system looks like — this is the failure mode that breaks trust in the whole engine. The fix also matters for Sebastien, the group's mechanics-first player: if he can't see the system working in the GM dashboard, the tea ritual might as well not exist.

---

## What Changed

Think of the tea ritual as a combination lock with three tumblers, and a camera that should be recording when each tumbler turns. All three tumblers were broken, and the camera wasn't recording anything.

**Tumbler 1 — the room sign problem.** The engine was checking whether the player had entered "the Galley" by looking for a label like `kestrel:galley`. But the narrator was writing the room name as `"The Kestrel — Galley"` (with a long dash). The two labels didn't match, so the engine never even started checking eligibility. Fix: the engine now reads the narrator's display format and strips it down to the part it needs.

**Tumbler 2 — the wrong name tag.** When a player creates a character, the bond between that character and the ship's AI gets a temporary placeholder name: `"player_character"`. The engine was supposed to swap that placeholder for the real character name (e.g., "Zanzibar Jones") — but that swap was never implemented. So when the engine looked up whether Zanzibar Jones had a bond with the ship, it found nothing. Fix: at the moment a character creation completes, the real name is now written in.

**Tumbler 3 — the opening blind spot.** Even if both above bugs were fixed, there was a third problem: the very first moment of a game session completely skipped the room-entry check. If a player started their session already in the Galley with a strong enough bond, the tea ritual would never fire on turn 1. Fix: the session startup now runs the same room-entry evaluation that mid-game moves run.

**The camera (OTEL).** Before this fix, every one of those failure paths was completely invisible. The GM dashboard showed nothing — no indication that the ritual had been evaluated, skipped, or blocked. Now every path emits a labeled signal: "skipped — no bond found," "skipped — wrong room name," "evaluated — 1 candidate matched, 0 fired (on cooldown)." Sebastien can now watch the dashboard and know whether the mechanic is engaged.

---

## Why This Approach

All three bugs had to be fixed together as a single unit. Fixing just the room name parser still left the wrong-name-tag bug, meaning any bond lookup would return empty and the ritual still wouldn't fire. Fixing just the name tag still left the room-name mismatch. You can't verify the fix works until all three layers are corrected simultaneously — so they were tested and implemented as one coordinated story rather than three separate tickets.

The OTEL instrumentation wasn't optional polish. It's the only way to tell whether the engine is actually running the mechanic or whether the narrator is just improvising. Without visible span data in the GM dashboard, a "fixed" system that still silently failed would be indistinguishable from a working one. The dashboard is the lie detector.

The fix was also deliberately minimal. The room name parser now handles three formats (colon-prefix, bare room ID, and the narrator's display format), but doesn't try to be cleverer than that. The bond rebinding is idempotent — if a real name is already there, it's never overwritten. No new abstractions were introduced; the fix goes exactly as far as the three bugs require and stops.

---
