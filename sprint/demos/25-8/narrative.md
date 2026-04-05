# 25-8

## Problem

**Problem:** Players had one way to read the game's story — a scrolling text feed that accumulated everything the AI narrator had said, session after session. As a story grew longer, finding the most recent beat meant scrolling past pages of earlier content, and players focused on a specific moment had no way to isolate it.

**Why it matters:** Narrative pacing is the soul of the game. A cluttered, hard-to-scan story panel breaks immersion and taxes the player's attention at exactly the moment the game should be pulling them in. Players have different reading styles; one layout can't serve all of them well.

---

## What Changed

The game's story panel now offers three distinct ways to read the narrative, selectable from the settings menu:

- **Scroll** — the original experience: a continuous feed of everything the narrator has said, newest at the bottom. Great for players who like to review history.
- **Focus** — one story beat fills the screen at a time, with Previous and Next arrows to step through the session. Shows "3 / 12" so you always know where you are. Automatically jumps to the latest beat when new narration arrives.
- **Cards** — every narrative moment becomes a card in a grid. On a wide screen you see three columns at a glance; on a phone it collapses to a single column. Good for players who want to scan the shape of a session quickly.

Whichever layout the player picks is remembered between sessions — close the browser, come back tomorrow, and it's still in focus mode (or cards, or scroll).

---

## Why This Approach

Three separate, self-contained display components — rather than one component with three modes bolted on — means each layout can evolve independently without risking the others. They all pull from the same underlying story data through a shared pipeline, so there's no risk of one layout showing different content than another.

Persistence is handled through the browser's built-in local storage under the project's standard `sq-narrative-layout` key, consistent with how every other user preference works in the app. No server round-trips, no sync complexity.

The core refactoring win here was collapsing the old narrative view from 835 lines of tangled logic down to 84 lines of clean dispatch code — less than one-tenth the original size. The complexity didn't disappear; it moved into purpose-built, individually testable units.

---
