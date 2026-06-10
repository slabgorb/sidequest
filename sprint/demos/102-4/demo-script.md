**Setup before the demo:**
- Start the server: `just server`
- Start the client: `just client`
- Load the `space_opera` genre with world `coyote_star` (SWN context)
- Have 2–3 test characters in a confrontation (use `just playtest-scenario swn_turn_model_fixture`)

---

**Scene 1 (Slide 2 — Problem): The old behavior**
*"Here's what WN combat looked like before today."*
- Open a confrontation round. Note that narration and action resolution happened in sequence, with each player seeing the previous outcome before committing.
- Point out: "There's no sealed commitment — player 2 saw player 1's result before deciding."
- *If live demo unavailable, show Slide 2's before/after screenshot.*

---

**Scene 2 (Slide 3 — What We Built): Commit phase**
*"Now watch what happens when the round opens."*
- In the confrontation overlay, show all players entering the commit phase simultaneously.
- Have player 1 select "Attack (STR)" — the action locks with a visual lock state. Their choice is hidden from the resolution pane.
- Have player 2 select "Evade" — same lock.
- Point to the UI: "Both players are locked in. No one sees the other's choice. The round is sealed."
- Show the OTEL dashboard (`just otel`): confirm `swn.round.committed` span fired.

---

**Scene 3 (Slide 3 continued): Initiative rolls**
*"Now the dice decide the order."*
- Trigger resolution. Show the 1d8+DEX dice roll animation (ADR-074 dice overlay).
- Example output to show: "Kira rolls 6+2 DEX = 8. Mox rolls 3+1 DEX = 4. Kira acts first."
- Initiative order appears in the confrontation panel, highest to lowest.
- OTEL: confirm `swn.round.initiative` span with participant order and roll values.

---

**Scene 4 (Slide 3 continued): Dead premise**
*"Here's the moment that makes WN feel different."*
- Set up a 3-participant scenario where participant C is targeting participant B, but participant A (higher initiative) drops B first.
- Run: `just playtest-scenario swn_dead_premise_fixture`
- When C's initiative slot resolves: **no damage applied to B** (who is already downed). The confrontation overlay shows a dead-premise callout: "Vasek's target is down — what does she do?"
- OTEL dashboard: confirm `dead_premise` event, confirm zero damage on B's HP row, confirm `swn.round.resolved` span.
- *Fallback: Slide 3's dead-premise sequence screenshot.*

---

**Scene 5 (Slide 4 — Why This Approach): Architecture callout**
*"One model, four game systems."*
- Show a quick `grep` in the terminal:
  ```bash
  grep -r "wn_turn_model" ../sidequest-server/sidequest/game/ruleset/ --include="*.py" -l
  ```
- Point out that swn.py, wwn.py, cwn.py, awn.py all reference the shared module — no duplication.

---