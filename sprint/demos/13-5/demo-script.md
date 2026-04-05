# Demo Script — 13-5

**Before you go on stage:** Have the game running in a browser at the GamePlay screen in Free Play mode. Have browser dev tools ready to toggle mode props if a live demo is needed.

**Slide 1: Title** *(0:00–0:30)*
Open with: "Before today, if a player asked 'why isn't my action doing anything?' — we had no answer visible on screen."

**Slide 2: Problem** *(0:30–1:30)*
Walk through the three modes and what makes each one distinct. Emphasize: Cinematic mode means the AI is driving. If you don't know you're in Cinematic, you'll keep typing and wondering why nothing is happening.

**Slide 3: What We Built** *(1:30–2:30)*
Switch to the live game UI. Point to the green **Free Play** badge in the corner. Say: "This is always visible. You never have to wonder." Hover over it — the tooltip reads *"Actions resolve immediately."* Then say: "Let me switch modes." In dev tools, change the mode prop to `structured`. The badge flashes and switches to blue, reading **Structured**. Hover: *"All players submit before the narrator responds."* Switch to `cinematic`. Badge turns purple: *"The narrator sets the pace."*

**Fallback:** If live mode switching fails, Slide 3 should show a static three-panel before/after with screenshots of each badge color and its tooltip.

**Slide 4: Why This Approach** *(2:30–3:15)*
"We didn't build a second mode system. We plugged into the one the engine already tracks. The badge can't lie — it reads directly from game state."

---
