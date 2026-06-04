# Narrative

## Problem Statement
**Problem:** During combat in SideQuest, players saw only their own action's outcome on screen — with no visibility into what the opponent just did. When a player landed a clean defensive move (correctly recorded as "no pressure gained"), the overlay showed nothing about the enemy's simultaneous counterattack racking up +2 pressure. Mechanics-focused players like Sebastien and Jade read this as the game being broken: "mine moved 0 but theirs did" — implying their action failed silently.

**Why it matters:** For players who want to see the math (Sebastien and Jade specifically), a one-sided readout is a trust-breaker. If you can't see both sides of the scoreboard, you can't tell whether the game is working correctly or cheating you. This was surfaced as a concrete confusion during 73-4 bug reproduction and was blocking confidence in the confrontation system for the mechanics-first half of the playgroup.

---

## What Changed
Think of the confrontation overlay as a scoreboard. Before this change, the scoreboard only showed your team's score. After this change, it shows both: "you: clean exit · them: +2 pressure."

Specifically:
- The game server now bundles the opponent's last combat result alongside the player's when it sends a status update to the screen.
- The Beat Impact Panel (the small readout that appears during combat) now displays two rows of numbers instead of one — your dial delta and theirs, side by side.
- Nothing about how combat is actually *calculated* changed. The server already quietly tracked both sides; this work just taught the screen to show it.

---

## Why This Approach
The data was already there — the server has been recording both the player's and opponent's combat results since the engine was built. The fix was purely about surfacing it, not re-engineering anything underneath.

Rather than renaming existing fields (which would have broken the already-working player-side readout from the previous sprint), the team added a clean sibling field alongside it. Old behavior is untouched; new behavior is additive. This is the smallest safe change that delivers the full legibility win.

The approach also means future visual polish (color-coding, icons, labels) can be layered on in a follow-up story (73-10) without revisiting the data wiring.

---
