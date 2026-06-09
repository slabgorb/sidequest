# Narrative

## Problem Statement
**Problem:** The player-facing reference pages (`/reference/rules/…` and `/reference/lore/…`) were built as 2,000 lines of Python that assembled raw HTML on the server. Every page update required the Python server to re-run string templates, and interactive map layouts were duplicated in two places — once in Python, once in TypeScript — kept in sync by hand. Why it matters: that duplication was a reliability time-bomb (two copies = two places to break), and the Python-built HTML couldn't be tested, animated, or styled with the same tools as the rest of the game client.

---

## What Changed
Imagine the reference pages used to be like a restaurant where the chef handwrote the menu, printed it, and mailed it to every table. Now the chef still decides what's on the menu, but a digital display at each table shows it — and everyone uses the same display system as every other screen in the restaurant.

Specifically:

- **The Python server stopped writing HTML.** It now produces a clean data packet (JSON) that says "here are the public facts about this world" — nothing more.
- **The React front-end took over rendering.** The same UI engine that runs the game itself now draws the reference pages: character portraits, points of interest, timeline events, the world map.
- **The world map became one shared component.** Previously the map was drawn twice — once by Python (for the reference page) and once by TypeScript (for the in-game overlay). Both are now replaced by a single React component using d3-dag for a clean, deterministic layout.
- **The old plumbing was deleted.** `reference_renderer.py`, `reference_presenters.py`, `reference_map.py`, `reference_timeline.py`, the `islands.js` hydration script — gone. The Python firewall that decides *what data is safe to show publicly* (`reference_visibility.py`) was kept and now gates the JSON API.
- **Theme (colors, fonts, genre feel) now arrives in the data packet** rather than requiring a live game session.

---

## Why This Approach
The firewall was already doing the right job — it had been battle-tested across every pack and world to ensure spoiler data (secret NPC motives, hidden trope seeds, keeper notes) never leaked to players. Keeping that logic in Python and moving only the *display* work to React was the safe play: the security boundary didn't move, only where pixels get painted.

Using d3-dag (a deterministic graph layout algorithm) for the map ensures the same world always produces the same picture. The old split-brain between Python and TypeScript meant any layout change had to be made in two languages simultaneously — a coordination tax that had already produced drift.

Hosting reference pages inside the SPA also means they automatically inherit every theme, font, and accessibility improvement made to the game client going forward. They're no longer a maintenance island.

---
