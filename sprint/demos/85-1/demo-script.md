**Before you start:** Launch the game server (`just up`), open a browser to `localhost:5173`, and start or resume a session that has reached a confrontation. If a live session isn't available, use the scene harness fixture: `just playtest-scenario confrontation_smoke` and navigate to the confrontation view.

---

**Slide 1 (Title) — 0:00–0:30**
Open the presentation. State: *"Today we're showing the confrontation panel redesign — the screen players spend the most time looking at during action sequences."*

---

**Slide 2 (Problem) — 0:30–2:00**
Show the before-state screenshot (or load an old build if available). Walk through the three visible defects:
- Point at the dark-on-dark meter: *"Can you tell THEM has 0 tension? Neither can the player."*
- Point at the bunched button row: *"Four beats crammed left, half the screen empty."*
- Point at the disconnected dice panel: *"I clicked 'Seize the Initiative' up there. The dice appeared down here. Why? Nobody knows."*

---

**Slide 3 (What We Built) — 2:00–4:30**
Switch to the live build (or after-state screenshot).

1. **Dial scoreboard:** Show a confrontation at roughly 6 YOU / 4 THEM. The bar should visually lean toward YOU. Drop THEM to 0 — confirm the empty track is visibly pale/neutral, not black-on-black. *"Zero is legible. The score is obvious from across the table."*

2. **Beat grid:** Show the full button row stretching edge-to-edge. *"Four actions, four equal tiles, no orphaned space."*

3. **In-tile dice roll:** Click an available beat (e.g., *Press the Advantage*). The tile expands in-place to show something like: `Rolled 14 vs DC 12 → Strong Hit`. *"The action and the result are one thing. You don't hunt for the outcome."*

4. **Beat-history ledger:** Point to the right panel showing the last three lines: e.g., `Rux · Press the Advantage · 14 vs DC 12 · YOU +1`. *"Sebastien and Jade can audit the last three moves without asking the narrator what happened."*

5. **Caption overflow fix:** Click a beat with a long description. *"Text wraps inside the tile. Nothing bleeds off the edge."*

**Fallback (if live demo fails):** Go to the after-state screenshot on Slide 3 and walk through the same five points with static images.

---

**Slide 4 (Why This Approach) — 4:30–5:30**
Stay on or return to the deck. *"Every change follows one rule: cause and effect in the same spatial unit. Roll lives next to the action that triggered it. Dial change lives next to the history that caused it."*

---

**Optional Before/After slide — 5:30–6:00**
Side-by-side. No narration needed — let the room react.

---

**Roadmap & Questions — 6:00–7:00**
Reference the roadmap slide, then open for questions.

---