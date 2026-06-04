# Narrative

## Problem Statement
**Problem:** The combat/confrontation screen was visually cluttered and confusing — progress meters were hard to read, action buttons were squished to one side, and the dice roll results appeared in a disconnected panel that had no clear relationship to the action that triggered them. **Why it matters:** SideQuest is built for a specific group that includes mechanics-first players (Sebastien, Jade) who actively want to see the math and momentum of a confrontation. When the scoreboard is unreadable and the cause-effect chain is broken, the game feels like it's improvising rather than resolving — which is exactly the kind of opacity that loses trust with experienced players.

---

## What Changed
The confrontation screen — the part of the game that shows back-and-forth combat and dramatic standoffs — got a full visual overhaul. Think of it like redesigning a scoreboard at a sports venue.

**The scoreboard got a proper face-lift.** Previously, "YOU vs THEM" tension meters were small and blended into the dark background (especially at zero). Now they're displayed as a single tug-of-war bar: your team fills from the left, the opponent fills from the right. Numbers are large and easy to read, and an empty track is visually distinct from a full one — you can always tell the score at a glance.

**Action buttons now use the full width.** The available moves (called "beats") were all bunched to the left with a lot of wasted empty space to the right. The grid was reorganized so tiles stretch evenly across the available space, like a proper button toolbar.

**Dice rolls are now attached to the action that triggered them.** Before, when you clicked an action, the dice result appeared in a separate fixed panel disconnected from what you just clicked. Now the tile you clicked expands in place to show your roll versus the difficulty — the cause and the effect are one visual unit.

**Action labels stay inside their boxes.** Long action names were overflowing their tiles and getting cut off. Text now wraps properly or moves to an expandable area.

**A new beat-history ledger was added on the right.** The space freed up by removing the disconnected die panel is now a running three-line log: who acted, what they did, what they rolled, and how the dial moved. Players can see exactly why the tension changed — the math is on the table.

**Keyboard and screen-reader accessibility was improved.** Every action is reachable via keyboard in the correct order. When all moves are locked out, a screen reader hint explains why. Resolution moves (the dramatic finishers) are labeled distinctly — not just visually styled differently.

---

## Why This Approach
The core principle was *spatial coherence* — every cause should live next to its effect. A disconnected dice panel is like a scoreboard that shows points but not which player scored them; you get the data but lose the story.

The tug-of-war scoreboard design was chosen because it maps naturally to how players already think about confrontations: it's a push-pull, and the visual should say that immediately without needing a legend. Using large tabular numerals meets accessibility contrast requirements and is simply easier to read across a table.

The in-tile dice roll pattern (tile expands, shows roll vs difficulty, collapses) keeps the action and result in the same column of attention. Players don't need to shift their gaze across the screen to understand what just happened.

The beat-history ledger was the natural occupant of the right-side space. Rather than leaving it empty, it turns reclaimed real estate into exactly the information mechanics-first players were missing: a provenance trail for every dial movement.

---
