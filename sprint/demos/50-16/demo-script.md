# Demo Script — 50-16

**Setup:** Have the SideQuest stack running (`just up`). Load or start a `tea_and_murder` session with at least one scenario clue available. Have the Journal panel open on-screen.

**Slide 2: Problem** — Before walking the live demo, describe the bug verbally: "Every clue in the journal showed 'Suspected' regardless of what the game engine decided. A locked-room confession and a street rumor looked identical."

**Slide 3: What We Built** — Transition to the live session.

**Scene 1 (0:00–0:45) — "A clue arrives, Suspected"**
- Trigger a narrator turn that introduces a clue (any action that causes a scene advance with a scenario discovery).
- In the Journal panel, point to the new entry: it shows `Suspected` immediately.
- Say: "The sticky note goes up instantly — we're not waiting for the server."

**Scene 2 (0:45–1:30) — "The server upgrades it"**
- Wait for the JOURNAL_RESPONSE to arrive (typically within 1–2 seconds of the turn completing). The journal entry will visibly update: the confidence badge changes from `Suspected` to whatever the server assigned — for scenario clues this will typically be `Certain` or `Rumored`.
- Point to the badge: "The sticky note just got replaced by the real evidence card. The game engine decided this clue was [Certain/Rumored] — and now that's what you see."
- *Fallback if the live transition is too fast to see:* switch to Slide 4 (Why This Approach) and narrate the two-stage flow from the diagram.

**Scene 3 (1:30–2:00) — "Order doesn't matter"**
- Narrate: "The fix also handles the edge case where the server's answer arrives before the narrator's footnote — same result. The authoritative verdict always wins."
- No live demo needed for this; the point lands verbally.

**Slide 5 (optional Before/After):** Show a journal screenshot with all entries at "Suspected" (before) vs. the same session with mixed Certain/Rumored/Suspected entries (after). These can be pulled from the playtest archive.

**Slide 6: Roadmap** — hand off to the roadmap section.

---
