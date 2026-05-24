# Demo Script — 53-5

**Setup before presenting:**
```bash
# Start the stack
just up
# Let server warm up (~10s), then navigate to http://localhost:5173
```

**Scene 1 (Slide 2 — Problem): "What players used to see"**
- Open an existing Road Warrior save file (any world with a vehicle user)
- Show the character sheet panel — draw attention to the absence of any vehicle health indicator
- Say: "Three stories of backend work built the crash system. Players couldn't see any of it."

**Scene 2 (Slide 3 — What We Built): "The new character sheet"**
- Start a new Road Warrior session with a driver character
- Navigate to the character sheet
- Show the **Composure bar** (green, full) — point out the label "Rig Composure" and the current/max numbers (e.g., "12/12")
- Show the **Edge bar** directly below it — both pools visible together
- Say: "First time a player can see their vehicle's health in real time."

**Scene 3 (Slide 3 continued): "Taking damage"**
- Using the playtest driver or narrator command, deal rig damage (or use a prepared save with partial composure)
- The bar updates live — show it at, say, "4/12" with the bar visually ~33% full
- Say: "Every hit is visible immediately."

**Scene 4 (Slide 3 continued): "After a crash"**
- Use a save where the character has crashed (composure hit 0), or trigger one
- Show the **injury tags**: red chips reading "injury" and "dismounted" appear on the card
- Say: "The crash handler fires the status, the UI surfaces it automatically — no extra wiring needed."

**Fallback if live demo fails:** Show Slide 3 static screenshot (take one before the demo). The before/after slide showing an empty character sheet vs. the new composure + injury tag layout is self-explanatory.

**Exact commands for headless verification:**
```bash
# Run the UI test suite to confirm all 1545 tests pass
cd /path/to/sidequest-ui && npx vitest run

# Check the server suite
cd /path/to/sidequest-server && uv run pytest -v tests/server/test_party_member_rig_composure.py
```

---
