# Demo Script — 45-3

**Setup before presenting:** Have SideQuest running with the caverns_and_claudes genre pack. Load a save file that is in an active confrontation (or start one). Have a second browser window open to the GM panel OTEL dashboard. Have the server terminal visible.

---

**Slide 1: Title** *(30 seconds)*

"Today we're showing a small fix that has a big effect on game feel — specifically for mechanically-minded players. The change is two lines of server code and a telemetry hook. The impact is that the momentum dial now tells the truth in real time."

---

**Slide 2: Problem** *(60 seconds)*

"Here's what we were dealing with. Sebastien — our most mechanics-focused player — reported that the momentum readout didn't feel right. He couldn't articulate why at first, but the data told the story."

Show the confrontation overlay from a recorded session. Point to the momentum bar. "The bar doesn't move when the dice resolve. It moves several seconds later, after narration runs. If you're watching the numbers, this looks like the system is guessing."

"The momentum dial is supposed to be the lie detector — the thing that proves the mechanical system is engaged, not that Claude is improvising. A lagging dial defeats that entirely."

*Fallback if live footage isn't available: Slide 2 screenshot showing the confrontation overlay with the old update timing annotated.*

---

**Slide 3: What We Built** *(90 seconds)*

"What we built is not a new feature. It's a missing wire."

Walk to the terminal. Run:

```bash
just server
```

Open a new game session in the browser. Start a confrontation. Open the OTEL dashboard in the second window:

```bash
just otel
```

"Now watch the OTEL panel as I throw dice." Throw dice in the game. Point to the GM panel. "There — `encounter.momentum_broadcast` with `source=dice_throw`. That fired the instant the dice resolved. And the dial on the player screen updated at the same moment."

"Run the narration turn to completion." Point to the second span in OTEL: `encounter.momentum_broadcast` with `source=narration_apply`. "That's the second confirmation — after narration, the system re-broadcasts with the final state. Two checkpoints, both visible, no gap."

*Fallback if live demo fails: Slide 3 has a screenshot of the OTEL dashboard showing both span entries with `player_metric_after: 4` and `opponent_metric_after: 2` as example values.*

---

**Slide 4: Why This Approach** *(60 seconds)*

"The server already knew the answer. The UI already knew how to show it. We just weren't sending the message at the right moment."

"The alternative would have been to poll the server for state after every dice throw, or to build a separate momentum channel. Both would have introduced new failure modes. The actual fix reused an existing message type — CONFRONTATION — that the UI already handled. We plugged it into the dice-resolution path. One additional broadcast per throw, carrying the values the system already computed."

"The two OTEL hooks mean we can verify this is working in production — during a live session, from the GM panel — without needing to pause the game."

---

**Before/After slide (optional):** *(30 seconds)*

Before: dice throw fires → narration runs → momentum bar updates. Gap: 2–5 seconds during narration.
After: dice throw fires → momentum bar updates immediately → narration runs → momentum bar confirms.

---

**Roadmap slide** *(45 seconds)*

"This fix is part of a larger sprint closing out the correctness gaps from Playtest 3. The momentum sync was the most visible player-facing miss. The same sprint includes the turn barrier fix — making sure multiplayer sessions don't get stuck waiting on phantom players — and the sealed-letter world-state sync that prevents the narrator from inventing physical separations between party members."

"Together, these three stories make the mechanical layer trustworthy. That's the prerequisite for the next set of work: trope progression tuning, scrapbook coverage, and the arc-embedding pipeline — all of which depend on the base state being correct."

---

**Questions slide** *(open-ended)*

---
