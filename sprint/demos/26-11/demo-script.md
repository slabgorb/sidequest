# Demo Script — 26-11

**Total runtime: ~6 minutes**

**Slide 1 — Title (0:00–0:15)**
Introduce the story: "Today we're showing a reconnect fix that keeps the party together when someone drops and rejoins."

**Slide 2 — Problem (0:15–1:00)**
Walk through the failure scenario. Open two browser windows side by side representing two players. Start a session, move Player 2 to a new location (e.g., the tavern), then close and reopen Player 1's window to simulate a reconnect. Show Player 1 landing in the *old* location (the starting room) while Player 2 is in the tavern. Say: "The party is now split — and neither player knows it."

Fallback: If live demo fails, show the Before/After slide with the two divergent state screenshots.

**Slide 3 — What We Built (1:00–2:00)**
Show the reconciliation in action. Repeat the same reconnect sequence. This time, Player 1 reconnects and immediately appears in the tavern alongside Player 2. The GM panel shows a single unified location for both players.

Terminal command (if showing server logs):
```bash
just api-run
# Then in a separate pane:
wscat -c ws://localhost:3000/ws
```
Point to the log line showing `reconcile_party_locations` firing on reconnect with the resolved location value.

Fallback: Show Slide 3 static with the before/after location state JSON.

**Slide 4 — Why This Approach (2:00–2:45)**
Explain the reconnect seam concept. "We fix it at the exact moment the player reconnects — the one clean window where we can sync without interrupting the story."

**Slide 5 — Before/After (2:45–3:30)**
Walk the comparison table. Before: Player 1 at `location: starting_room`, Player 2 at `location: tavern`. After: both players at `location: tavern`, reconciled at reconnect timestamp.

**Slide 6 — Roadmap (3:30–4:30)**
Connect to session resilience roadmap.

**Slide 7 — Questions (4:30–6:00)**
Open floor.

---
