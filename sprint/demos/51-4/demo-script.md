# Demo Script — 51-4

**Total runtime: ~6 minutes**

**Setup before presenting:**
```bash
# In oq-1/sidequest-server
cd /Users/slabgorb/Projects/oq-1
just up
```
Wait for server ready message (`Uvicorn running on http://0.0.0.0:8765`).

---

**Slide 1 — Title (30 seconds)**
Open with: "SideQuest's scenario library used to be a secret. Today it's a menu."

---

**Slide 2 — Problem (60 seconds)**
Show this terminal command — this is what it used to take to access the fixture library:
```bash
DEV_SCENES=1 SIDEQUEST_FIXTURES_DIR=/Users/slabgorb/Projects/oq-1/scenarios/fixtures just server
```
Point out: "If you forgot the flag, or ran `just serve` like a real player would, this entire feature silently disappeared. No error. Just gone."

Fallback if terminal is unavailable: Stay on Slide 2 and read the env var verbally — its length makes the point.

---

**Slide 3 — What We Built (90 seconds)**

**Part A: The API (30 seconds)**
Open a browser tab to `http://localhost:8765/dev/scenes`. Show the JSON response:
```
[
  {"name": "combat_brawl_wasteland", "genre": "mutant_wasteland", "world": "...", "description": "..."},
  {"name": "tavern_rumble_caverns", "genre": "caverns_and_claudes", ...},
  ...
]
```
"Twelve fixture files, all now discoverable from a single endpoint. No startup flags."

**Part B: The UI (60 seconds)**
Navigate to `http://localhost:5173`. Show the ConnectScreen. Point to the "Scene Library" section below the server URL field. Show 3–4 fixture cards with genre badges (e.g. `Mutant Wasteland` in orange, `Caverns & Claudes` in green).

Click one card — e.g. `combat_brawl_wasteland`. Watch the URL update to `/?scene=combat_brawl_wasteland` and the game load directly into that encounter.

"That's the whole flow. Pick a scenario. Click. You're in combat."

Fallback if server isn't running: Show Slide 3 static screenshot of the Scene Library section. Narrate the card structure: name, genre badge, description, click behavior.

---

**Slide 4 — Why This Approach (60 seconds)**
"We didn't build a permissions system. We didn't build an admin panel. We removed a lock that was on a door we already own. The Cloudflare tunnel is the real bouncer — it has been for months. The env var was a second lock on the same door that just made our own lives harder."

---

**Before/After Slide (optional, 30 seconds)**
- **Before:** `DEV_SCENES=1` required, `just serve` = fixture library hidden, no in-app discovery
- **After:** Always on, Scene Library in ConnectScreen, one click to play

---

**Roadmap Slide (30 seconds)**
"This is the last story in the fixture library wave. Fixtures are now a first-class entry point. The path forward is authoring more of them."

---
