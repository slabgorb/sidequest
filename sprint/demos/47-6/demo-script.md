# Demo Script — 47-6

### Pre-demo setup
```bash
cd ~/Projects/oq-1
just up       # boots server + client + daemon
just otel     # opens GM dashboard in browser
```
Have two browser windows side by side: the SideQuest game UI on the left, the OTEL GM dashboard on the right.

---

**Slide 2: The Problem**

Open the session log from the playtest (reference only — don't need the actual save file):

> "Turn 22: Zanzibar Jones entered the Galley. The Kestrel hummed softly. A quiet ritual of tea and reflection began..."

Point to the narrative. Then show the server log excerpt (can be a screenshot):
```
state.location_update old='The Kestrel — Cockpit' new='The Kestrel — Galley'
```
...followed by nothing. No confrontation fire. No bond record. The narrator wrote the tea ritual; the engine did nothing.

---

**Slide 3: What We Built**

Live demo — start a new Coyote Star session as Zanzibar Jones. Point to the GM dashboard.

```bash
# In the game UI: start new game, choose Coyote Star / Kestrel
# Character name: Zanzibar Jones
# Complete character creation
```

Immediately after character creation completes, look at the GM dashboard. You should see:

```
room.entry_evaluated  chassis_id=kestrel  room_local_id=galley
                      eligible_count=1    fired_count=1
```

This is the **opening hook** fix — the session opened in the Galley, bond was `trusted`, and the tea ritual fired on turn 1 without the player having to move anywhere.

Fallback if live demo fails: Show screenshot of the span with the above values. Point to `eligible_count=1, fired_count=1` as the proof.

---

**Slide 3 continued: mid-session fire**

Navigate the character to the Cockpit, then back to the Galley (wait for cooldown — approximately 5 turns):

```
[In-game action] "I walk to the cockpit"
[In-game action] ...5 turns later... "I head back to the galley"
```

GM dashboard should now show a second `room.entry_evaluated` span. Point to it.

If cooldown hasn't elapsed yet, the span will show `eligible_count=1, fired_count=0`. That's intentional — explain: the mechanic was evaluated, the candidate matched the room and bond, but cooldown blocked the fire. **Before this fix, the dashboard showed nothing at all — you couldn't tell if the engine even tried.**

---

**Before/After slide**

Show the bond ledger in the GM dashboard (or screenshot):

**Before:** `bond_ledger[0].character_id = "player_character"` — the engine couldn't find Zanzibar Jones's bond because the name was never updated.

**After:** `bond_ledger[0].character_id = "Zanzibar Jones"` — correct, written at character creation completion.

---

**Slide 4: Why This Approach**

Walk through the three layers on the slide. Use the OTEL span as the "and here's how we know it works" punchline:

```
room.entry_skipped  reason=no_bond_for_actor   ← what it showed BEFORE Bug 2 fix
room.entry_skipped  reason=not_chassis_room    ← what it showed BEFORE Bug 1 fix
room.entry_evaluated  eligible_count=1  fired_count=1  ← what it shows NOW
```

---
