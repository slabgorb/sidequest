# Demo Script — 59-12

**Total runtime: ~6 minutes**

---

**Slide 1 — Title (0:00–0:30)**
Introduce the story: "Today we're closing a session-stopper in the dungeon crawl. If your character tried to enter a dungeon, the game crashed immediately. Here's what we fixed."

---

**Slide 2 — Problem (0:30–1:30)**
Walk through the two failure modes:
- "When a PC transitioned from the world surface into a dungeon entry node, they weren't registered on the dungeon graph. The movement engine had no record of them."
- "Any movement command — north, south, into the next room — immediately threw an unresolved dispatch error."
- "A second bug caused the movement call to fire twice. The second call was missing keyword arguments and produced a second exception."

If you have logs available: show the exception output — `run_movement_dispatch` raising on a None node lookup, followed immediately by a TypeError for missing kwargs.

*Fallback if log isn't available: Slide 2 bullet points are sufficient.*

---

**Slide 3 — What We Built (1:30–3:00)**

**Live demo portion:**

```bash
# Start a session and enter a dungeon
just server
# In a second terminal, run a playtest scenario that transitions surface → dungeon
just playtest-scenario dungeon_entry
```

Show the player character:
1. Starting on the surface (session log shows node: `surface_hub`)
2. Descending into the dungeon (transition event fires)
3. **Movement immediately working** — the PC is on node `dungeon_entry_0` and can navigate north, south, into corridors

Point to the specific log line that confirms graph registration: something like `[graph] PC bound to node dungeon_entry_0` — this is the line that didn't exist before the fix.

*Fallback if server isn't running: show the Before/After slide.*

---

**Slide 4 — Why This Approach (3:00–4:00)**
"We didn't add a safety net that silently handles 'character not found.' We fixed the graph so the character is always there. Silent fallbacks hide problems — we want loud, correct behavior."

Reference the project's No Silent Fallbacks principle if the audience is familiar with it.

---

**Before/After Slide (4:00–4:45)**
Walk through the comparison table (see section below).

---

**Roadmap Slide (4:45–5:30)**
"This unblocks the full dungeon-crawl loop. Room-to-room navigation, encounter triggers, and the procedural megadungeon work all depend on a reliable graph. This is the foundation."

---

**Questions (5:30–6:00)**

---
