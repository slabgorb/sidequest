**Setup (before the demo):**
- Start the server: `just server`
- Open the GM dashboard in a browser (port 8765, `/dashboard`)
- Have the Subsystems tab selected, not the RAW tab
- Load a WWN (Worlds Without Number) magic-capable character into a test scene

**Scene 1 — The Problem (Slide 2: Problem)**
*(~90 seconds)*
Switch to the RAW console tab. Trigger a scene load with a magic-capable character:
```bash
curl -X POST http://localhost:8765/dev/scene-harness/load \
  -H "Content-Type: application/json" \
  -d '{"character_class": "mage", "genre": "caverns_and_claudes"}'
```
Point to the raw log flooding with events. Then click the Subsystems tab. Show that the magic row is **empty** — no initialization events appear. Say: *"The engine fired two signals confirming magic loaded correctly. Neither one reached this panel."*

**Fallback if server unavailable:** Show Slide 2 screenshot of the empty Subsystems magic row captured pre-fix.

**Scene 2 — After the Fix (Slide 3: What We Built)**
*(~90 seconds)*
Switch to a branch with the fix applied (or show pre-captured recording). Run the same scene load command. Click the Subsystems tab. Point to the magic row — it now shows:
- `magic.state_hydrated` — with component label `magic`, type `state_transition`, timestamp
- `wwn.magic_hydrated` — same row, confirming WWN-specific magic loaded

Say: *"Same engine, same events — now they route to the right panel. The GM can see at a glance that magic initialized before the first spell fires."*

**Fallback:** Show Slide 3 screenshot of the populated Subsystems row post-fix.

**Scene 3 — Why It Matters (Slide 4: Why This Approach)**
*(~60 seconds)*
Navigate to the Subsystems tab and show a full spell cast sequence: `magic.state_hydrated` → `wwn.magic_hydrated` → `wwn.spell.cast` → `wwn.effort.commit`. Say: *"Before this fix, the first two rows were missing. You couldn't tell if magic came up clean before the cast. Now the full chain is visible — the lie-detector works."*

---