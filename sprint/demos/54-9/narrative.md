# 54-9

## Problem

**Problem:** Players exploring the game world had no persistent reference for *where they are*. Location descriptions appeared briefly in the narration stream and immediately scrolled away — by the time a player wanted to recall the details of a room or region, they'd have to scroll back through many turns of story text to find it. **Why it matters:** This creates friction at exactly the wrong moment — when a player is trying to make a decision ("do I go left or right?") and needs the information the GM just described. It's especially punishing for slower readers and players who get absorbed in conversation while the narration moves on.

---

## What Changed

Think of it like adding a "You Are Here" sticky note to the game screen that never falls off.

Before this change, the game had two persistent side panels: one showing the map, and one showing the knowledge journal (lore and clues the party has collected). Between those two, there was nothing dedicated to *the current location*.

Now there's a third tab — **Location** — that sits right between Map and Knowledge. It always shows:
- A written description of wherever the party currently stands
- Extra details that apply when a special overlay (like a dungeon level) is active
- A small indicator dot ("pip") that lights up when an overlay location is in effect

The tab stays put. It updates automatically whenever the party moves. The player never has to scroll through narration to remember what the room looks like.

---

## Why This Approach

The team already had a proven pattern from the Knowledge Journal: a panel that listens to the game's live data feed, renders structured text, and stays in sync with game state automatically. Rather than invent something new, this feature followed that same blueprint exactly — same connection approach, same update mechanism, same tab registration system.

The "overlay suffix" design (base description + extra detail when underground or in a special area) means location text is always accurate to exactly where the player is, without cluttering the view when the extra detail doesn't apply.

---
