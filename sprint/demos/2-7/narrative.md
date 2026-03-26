# 2-7

## Problem

**Problem:** After the AI narrator finished telling a story beat — a fight, a chase, a character meeting a new NPC — the game's internal state didn't update reliably. HP changes were lost. NPC attitudes weren't recorded. Discovered locations weren't remembered. The client (what the player sees on screen) never received a signal that anything had changed, so the UI was stale or wrong. **Why it matters:** Every meaningful event in the game — combat, exploration, narrative twists — has to land in the game state and be reflected to the player instantly. Without this pipeline, the game engine was effectively narrating events into a void.

---

## What Changed

Think of the game engine like a scoreboard operator at a sporting event. Before this fix, the AI narrator could shout out "Thorn took 8 damage!" or "You've entered the Flickering Reach!" — but the scoreboard operator had no instructions for what to do with that information, so nothing changed on the board.

This story gave the scoreboard operator a complete, reliable rulebook:

- **Health changes** from combat or events now apply immediately to the right character or NPC
- **NPC attitudes** ("Marta the Innkeeper is now hostile") get translated and stored correctly
- **New locations and discovered routes** are added to the world map without creating duplicates
- **Quest progress** is merged in additively — completing one quest step doesn't wipe out others
- **Time of day, active stakes, and established lore** are now tracked fields the narrator can update
- Once all patches are applied, the engine **calculates exactly what changed** and pushes the right update messages to the player's screen — party health bars, location banners, map reveals, and combat events, each fired only when relevant

---

## Why This Approach

The AI narrator sends updates as small, targeted JSON "patches" — only describing what changed, not re-sending the entire world state. This is efficient and mirrors how real-time systems like live sports feeds work.

The key engineering decisions:

1. **Patches are strictly validated** — if the AI sends a field the engine doesn't recognize, it's rejected immediately rather than silently ignored. This catches narrator errors at the boundary.
2. **Discovery lists use append-and-deduplicate** — if the narrator says "the player discovers the Iron Road" twice, it only appears in the world map once. No corruption from repeated events.
3. **NPC identity is locked on first set** — once an NPC's pronouns and appearance are established, subsequent patches can't accidentally overwrite them. Characters feel consistent.
4. **Delta computation is separate from patching** — the engine takes a snapshot before and after applying changes, compares them, and only broadcasts the messages that are actually needed. No false updates, no missed ones.

---
