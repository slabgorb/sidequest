# Demo Script — 45-24

**Pre-demo setup:**
- Have SideQuest UI running locally at `http://localhost:5173`
- Have a screen reader available (macOS VoiceOver: `Cmd+F5` to toggle)
- Have browser DevTools open to the Elements tab
- Have a second browser tab with `ConnectScreen.tsx` open in an editor showing lines 384–395

---

**Scene 1 — Title (Slide 1)**
*Time: 0:00–0:30*
Open with the slide. Introduce the story: "This is a one-point accessibility fix that makes SideQuest screen-reader-friendly at the exact moment players hit a connection error."

---

**Scene 2 — The Problem (Slide 2)**
*Time: 0:30–1:30*
Navigate to the SideQuest connect screen in the browser. Stop the server (or disconnect from network) so the genres fetch fails. The error state appears: grey message reading "Could not load worlds. Is the server running?" with a Retry button below it.

Enable VoiceOver (`Cmd+F5`). Tab to the Retry button. VoiceOver announces: *"Retry, button."* — nothing else.

Say: "A screen reader user hears 'Retry' with no context. Retry *what*? They have to navigate backward to find the error, then return. That's friction we can eliminate at essentially zero cost."

*Fallback if live demo fails: Show Slide 2 with the before/after VoiceOver transcript as bullet text.*

---

**Scene 3 — What We Built (Slide 3)**
*Time: 1:30–2:30*
Switch to the editor tab showing `ConnectScreen.tsx`. Point to the two changed lines:

```
Line 386:  <p id="genre-load-error" ...>
Line 393:  <button aria-describedby="genre-load-error" ...>
```

Say: "Two attributes. The paragraph gets a name tag. The button gets a pointer to that name tag. That's the entire diff."

Return to the browser. Tab to the Retry button again with VoiceOver on. Now it announces: *"Retry, button. Could not load worlds. Is the server running?"*

*Fallback: Show Slide 3 with a side-by-side "before code / after code" screenshot.*

---

**Scene 4 — Why This Approach (Slide 4)**
*Time: 2:30–3:00*
Show Slide 4. Emphasize: standard ARIA pattern, zero visual change, 1,373/1,373 tests passing, ships in under 3 minutes of engineering time.

---

**Scene 5 — Roadmap (Roadmap Slide)**
*Time: 3:00–3:30*
Transition to what's next for accessibility. Mention the deferred improvement: adding automated a11y test assertions when the team wires in `axe-core` or `vitest-axe`.

---

**Scene 6 — Questions**
*Time: 3:30–end*
Open floor.

---
