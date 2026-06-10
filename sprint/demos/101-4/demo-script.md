**Total runtime: ~4 minutes**

**Slide 1 (Title) — 00:00–00:20**
Open with the slide. Introduce the story as a "quiet win" — the kind of work that keeps the engine running smoothly over time.

**Slide 2 (Problem) — 00:20–01:00**
Walk through the problem. "We had two things in the codebase that looked important but did nothing. `OverlayType` had no importers — zero files referenced it. `groupPortraitSegments` was being called but the function body had no effect. Every new developer who encounters these has to stop and investigate."

**Slide 3 (What We Built) — 01:00–01:45**
Show the before/after. "Before: these definitions existed, taking up space and attention. After: gone. The app still loads, all tests pass, nothing changed for players."

*Live demo option:* Open the terminal and run `just client-test` to show green tests:
```bash
just client-test
```
If the test run fails for unrelated reasons, switch to Slide 3 and point to the diff showing the deletions directly.

**Slide 4 (Why This Approach) — 01:45–02:30**
"We don't leave scaffolding up after the building is finished. Dead code is scaffolding. Removing it now means the next engineer who opens this file sees only what matters."

**Roadmap slide — 02:30–03:30**
Connect to the broader sprint 101 cleanup work. "This is part of a series of hygiene passes across the UI layer — each one tightening what the codebase claims to do versus what it actually does."

**Questions — 03:30–04:00**
Open floor.

*Fallback for any live demo failure:* Show the diff slide with the two deletions highlighted. The story tells itself visually — two blocks of code, then nothing.

---