# Demo Script — 13-9

**Setup:** Two-player session open in browser. One player has submitted; the other is sitting idle.

**Scene 1 — Slide 2 (Problem): Show the broken behavior**
- Start a turn, have Player 2 go idle.
- Let the timer expire.
- Point out that the narration proceeds normally, with no indication Player 2 did nothing. Zero notification. The narrator treats it as if Player 2 acted.
- *"Before this fix — the game just moved on. The narrator made up context it didn't have."*

**Scene 2 — Slide 3 (What We Built): Show the fixed behavior**
- Run the same scenario with the fix deployed.
- When the timer expires, a `TURN_AUTO_RESOLVED` notification appears in the UI listing Player 2 as auto-resolved.
- Show the combined action context in the server log: Player 1's submitted action alongside Player 2's injected `"hesitates, waiting"` entry, tagged `auto_resolved: true`.
- *"Now the game acknowledges what actually happened."*

**Scene 3 — Slide 3 continued: Show narrator output**
- Read the narration aloud. Player 2's character hesitates or holds back — coherent with the auto-fill.
- Contrast with the pre-fix narration where Player 2's character acted normally despite submitting nothing.

**Scene 4 — Slide 4 (Why This Approach): Code branch**
- Show the diff: the single `if result.timed_out` branch. One branch, three connected behaviors.
- *"Smallest possible change. The wires were already there."*

**Fallback:** If live demo fails at any scene, show the before/after slide instead and read the narrator output examples directly.

---
