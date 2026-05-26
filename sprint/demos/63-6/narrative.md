# 63-6

## Problem

**Problem:** When a player explores a new region in SideQuest, the location panel shows the region name as plain text — a dead end. Players who want to learn more about a location (its history, lore, points of interest) have to leave the game and navigate the wiki manually. Why it matters: SideQuest's reference wiki is already packed with rich world-building content for every location in every genre pack, but players had no way to jump directly from the game to the relevant wiki page. The system knew where they were; it just wasn't telling them.

---

## What Changed

Think of it like turning a street name on a map into a clickable link. Before this story, the location panel in the game showed your current region as unlinked text — "The Iron Quarter" — and that was it. Now, when the game engine knows that "The Iron Quarter" has a corresponding wiki entry, the region name becomes a hyperlink. Click it, and a new tab opens directly on that location's reference page, complete with lore, history, and points of interest.

Under the hood, three things changed:

1. **The game server now looks up whether a location has a wiki page.** Every time the server sends a location update to your screen, it checks whether the current region matches a known point of interest with a wiki anchor. If yes, it packages the link alongside the location data. If no match exists, the field is simply left empty — no broken links, no guessing.

2. **The game client now knows what to do with that link.** The location panel checks whether a link arrived with the location update. If it did, the region name becomes a clickable anchor that opens the wiki in a new tab. If no link came through, the region name stays as plain text — identical to what players saw before.

3. **The GM dashboard can now verify location links are firing.** A new telemetry signal was added so the game master panel (the "lie detector" for the engine) shows whether location anchors are resolving correctly — not just character sheet and journal links.

---

## Why This Approach

The engineering team already built this exact pattern for the character sheet: when a player's class has a wiki entry, the class name in the character sheet becomes a hyperlink. This story applied the same pattern to locations — reusing all the same anchor-building machinery, the same server-side lookup logic, and the same frontend rendering convention. No new infrastructure. No new concepts. Just connecting an existing pipe to a new socket.

The safety rails are deliberately conservative. The server only emits a link when it can confirm a matching wiki anchor exists — it never guesses or constructs a plausible URL that might 404. If anything goes wrong (missing content, misconfigured world data), the feature degrades silently to plain text. Players never see a broken link.

The Zork doctrine — the deliberate rule that individual items and entities inside a location are *not* rendered as links — was explicitly preserved and verified by an automated test. The link applies only to the region header itself, keeping the panel clean and focused.

---
