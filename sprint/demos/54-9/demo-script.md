# Demo Script — 54-9

**Pre-demo setup:** Have the game running with a session in progress — ideally inside a dungeon or interior location so the overlay pip is visible. Load the `caverns_and_claudes` pack.

---

**Scene 1 — The Problem (Slide 2: Problem)**  
*~60 seconds*

Open the game at a mid-session state. Show the narration stream. Scroll up to find where the GM described entering the current room. Count how many turns of text have piled on top of it. Point out: "If Alex (our slower reader) wants to recall what this room looks like, this is what they'd have to do every time."

---

**Scene 2 — The New Tab (Slide 3: What We Built)**  
*~90 seconds*

Point to the tab bar in the right panel. Identify the three tabs: **Map | Location | Knowledge**. Click **Location**.

Show the panel now displaying the current room's prose description — for example: *"A low-ceilinged passage carved from wet limestone. Iron sconces, long burned out, line the northern wall. The air smells of old ash and something metallic."*

Scroll down (or point to) the overlay suffix section — the additional text that layers in because the party is in a dungeon overlay. Show the active pip indicator glowing next to the tab label.

Move the party to a new room (submit a move action). Watch the Location panel update automatically, no page reload, no scrolling.

*Fallback if live demo fails: Switch to Slide 3 and describe the behavior verbally — "The panel auto-updates; here's a screenshot of the before and after state."*

---

**Scene 3 — Why It Works This Way (Slide 4: Why This Approach)**  
*~45 seconds*

"We didn't build new plumbing for this. The Location tab uses the same live data connection the Knowledge Journal uses — it just subscribes to location updates instead of lore entries. That's why we could ship this in 3 story points instead of 10."

---

**Scene 4 — The Pip Detail (optional, if time allows)**  
*~30 seconds*

Point to the active pip. "This small dot tells you whether you're in a layered location — a dungeon sub-level, an interior room inside a larger space. When you surface back to the overworld, it goes dark. No separate UI state to manage."

---
