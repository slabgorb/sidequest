# 52-5

## Problem

Problem: The tactical grid (the dungeon map overlay that appears during underground exploration) was not reliably pulling cave images from the live game server — it was either showing nothing, showing a stale placeholder, or silently falling back to a default. Why it matters: when the map renders a wrong or missing image, the GM has no way to know whether the underground visuals are real or improvised, undermining the whole point of the dungeon-crawl experience. Without a verified signal in the observability dashboard, the team also had no way to confirm the fix was holding in production.

---

## What Changed

Think of it like a TV that was sometimes tuned to the wrong channel without telling anyone. We updated the tactical grid component — the dungeon map view players see during underground scenes — so it now:

1. **Fetches the cave image from the live game server** every time a new room loads, instead of relying on whatever happened to be cached or hardcoded.
2. **Lights up a signal in the GM dashboard** (a green checkmark in the observability panel) confirming the image actually arrived from the server and was displayed — not guessed at.

The end-to-end test we added proves both of those things happen together, automatically, every time the code changes.

---

## Why This Approach

The simplest fix would have been to hard-wire a default cave image and call it done. We didn't, because that's exactly the kind of invisible workaround that hides problems for months. Instead, we made the component explicitly reach out to the server for the URL, and we made it *say so* in the telemetry log — so the GM panel becomes the source of truth, not wishful thinking. The automated test locks that behavior in: if a future change breaks the wiring, the test fails loudly before it ever ships.

---
