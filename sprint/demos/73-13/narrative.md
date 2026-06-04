# Narrative

## Problem Statement
**Problem:** During combat, when an enemy attacks first — in a surprise round, a legacy initiative path, or when a player takes a non-combat action — the panel that shows the enemy's attack results disappears entirely. The player is hit, but the screen shows nothing.

**Why it matters:** Players have no feedback that they were damaged. The "enemy hit you" readout added in the previous story (73-7) is silently swallowed. In a game where mechanical legibility matters — especially for players like Sebastien and Jade who want to see the numbers — a blank screen where damage feedback should be is a serious trust break with the UI.

---

## What Changed
The combat results panel had a single condition for becoming visible: *"does the player have a result?"* If yes, show the panel. If no — even if the enemy just landed a hit — hide everything.

The fix changes that condition to: *"does the player OR the enemy have a result?"* The panel now shows up whenever there's anything worth showing, and it handles the case where the player's half of the data hasn't arrived yet without hiding the enemy's half.

---

## Why This Approach
The original gate was written assuming the player always acts before the enemy — a reasonable assumption for the common case, but wrong for surprise rounds and initiative-reversed paths. The simplest correct fix is to widen the condition rather than restructure the flow. The panel already knew how to render partial data; it just wasn't being shown when only the enemy half was present. One condition change is the right-sized fix.

---

## Before/After
| | Before (73-12 and earlier) | After (73-13) |
|---|---|---|
| **Opponent acts first (surprise round)** | `BeatImpactPanel` hidden entirely — no feedback | Panel visible, opponent impact shown, player section absent |
| **Player submits non-combat action during confrontation** | Panel hidden — player sees nothing | Panel visible with opponent result |
| **Player acts first (common path)** | Panel shown normally | Unchanged — no regression |
| **Both sides have acted** | Panel shown normally | Unchanged |
| **Player sees enemy damage** | Only when player has also acted | Any time the enemy has a result |
