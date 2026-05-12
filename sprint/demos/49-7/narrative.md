# 49-7

## Problem

**Problem:** Every player in a multiplayer combat session was shown every possible action in the game — a Fighter saw spell buttons they couldn't cast, a Cleric saw Backstab moves that don't exist in their kit, a Thief saw Turn Undead. The action panel was showing 16 buttons to everyone regardless of class. **Why it matters:** Players had to mentally filter out irrelevant options mid-combat, which breaks immersion and slows decisions — especially for Alex, who already freezes under time pressure. A Fighter staring at "Cast Fireball" is a UX failure that signals the game doesn't actually know who they are.

---

## What Changed

Imagine a waiter who memorizes every item on every menu in the restaurant, then reads the entire thing aloud to every table. That's what the game was doing. This story teaches the waiter to read the table first — "You're a Fighter? Here's the Fighter menu." — and only bring the relevant choices.

Technically: the server now builds a separate action list for each connected player before sending it out. A Fighter's panel shows fighter moves. A Cleric with no spell slots left doesn't see the "Cast Spell" button at all. Each player gets their own tailored list, assembled fresh for their character at the moment combat begins. The GM's view of the AI narrator's decision-making is unchanged — the narrator still sees everything; only the player-facing panel is filtered.

---

## Why This Approach

The filter runs on the server, not in the browser, for two reasons. First, it's the only place that knows the full character state — spell slots remaining, class definition, prepared spells — without a round-trip. Second, doing it in the browser would mean sending the full 16-button list to every player and trusting each client to hide the right buttons. That's fragile (a determined player could see options they shouldn't) and wasteful (sending data you immediately throw away). Server-side projection is the clean answer: each player receives only what they're allowed to see, nothing more.

The AI narrator's prompt is deliberately left alone. The narrator needs to see all possible moves to write coherent combat narration — "Carl doesn't have magic, so he charges instead" only makes sense if the narrator knows what magic is. The player panel and the narrator prompt are now two separate filtered views of the same data, each tuned for its audience.

---
