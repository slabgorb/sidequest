**Setup:** Running server + UI locally. Navigate to a confrontation where the opponent is set up to act first (surprise round or legacy beat_selection path).

**Slide 2 — Problem:**
Walk through the broken behavior before the fix. Describe: "We added the enemy-hit readout in 73-7. But if the enemy swings first, this is what the player sees." Point to a blank combat panel. "Nothing. No damage number. No feedback. The hit happened — the server registered it — but the UI said nothing."

**Slide 3 — What We Built:**
Show the fix in plain terms: "We changed one gate from 'AND' to 'OR'. The panel used to require the player to have a result. Now it shows up for either side."

**Live demo sequence (if server is running):**

1. Start a confrontation in a genre that supports surprise rounds (e.g., `space_opera` / `coyote_star`)
2. Trigger an opponent-first beat — either via surprise round setup or by having the player submit a non-combat action
3. **Before fix:** Panel is absent. No combat feedback.
4. **After fix:** Panel appears with the opponent's attack result displayed. Player impact section is gracefully absent (not blank/broken — just not shown).

*Fallback if live demo fails:* Switch to the Before/After slide. Show the side-by-side screenshots of the blank panel vs. the populated panel.

**Slide 4 — Why This Approach:**
"We didn't restructure the combat flow. We widened a single visibility check. The panel already handled partial data — it just wasn't being asked to show up."

---