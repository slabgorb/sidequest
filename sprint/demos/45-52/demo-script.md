# Demo Script — 45-52

**Pre-show setup (5 min before):**
```bash
cd ~/Projects/sidequest-server
just server-check
```
Confirm output ends with `All 2693 tests passed`. Have the GM dashboard open at `http://localhost:8765/dashboard`.

---

**Scene 1 — Title** *(Slide 1, 0:00–1:00)*
Introduce the story: "This is a finishing move — we threw away scaffolding from a refactor we completed last week and made the monitoring panel tell the truth."

---

**Scene 2 — The Problem** *(Slide 2, 1:00–3:00)*
Show the before-state from the branch diff. Open `.session/archive/45-47-session.md` (Wave 2A session) and point to the note about `NpcRegistryEntry` being left as a compatibility shim. Say: "Nine test files were still pointing at the old class. If the new NPC system broke, all nine would still pass. That's a lie detector with dead batteries."

*Fallback if file isn't accessible:* Show Slide 2 — bullet: "9 of 9 NPC tests pointed at deprecated code."

---

**Scene 3 — What We Built** *(Slide 3, 3:00–6:00)*
Run the grep to show the old class is gone:
```bash
grep -r "NpcRegistryEntry" ~/Projects/sidequest-server/sidequest/
```
Expected output: **zero matches**. Then show the new span name:
```bash
grep -r "SPAN_NPC_EDGE_PUBLISHED" ~/Projects/sidequest-server/sidequest/
```
Expected: matches in `telemetry/spans/npc.py` and the wiring site.

*Fallback if grep fails:* Show Slide 3 — bullet: "Zero production references to `NpcRegistryEntry` remain."

---

**Scene 4 — The New Monitoring Counters** *(Slide 4, 6:00–9:00)*
Start the server and load a save:
```bash
just server
```
In a second terminal:
```bash
just playtest-scenario caverns_and_claudes
```
Open the GM dashboard and show the OTEL span table. Point to the `npc.pool_published` span and expand its attributes — you should see `malformed_npcs_skipped=0`, `nameless_entries_dropped=0`, `location_available=true`. Say: "These were dark before. Zero is the right answer today. If they're non-zero in a future session, that's a real signal, not silence."

*Fallback:* Show Slide 4 with the three new attribute names listed.

---

**Scene 5 — Before/After** *(Optional Before/After slide, 9:00–10:30)*
Pull up the Before/After section of this document on screen. Walk the audience through the two-column comparison.

---

**Scene 6 — Roadmap** *(Roadmap slide, 10:30–12:00)*
"This is the last cleanup story in Wave 2A. Wave 2B (location derivation, story 45-48) already shipped. The deprecation alias for the Wave 1 rename is still in place — that gets dropped in story 45-46, which is scheduled to land when the next wave of NPC work merges."

---

**Scene 7 — Questions** *(Questions slide, 12:00+)*

---
