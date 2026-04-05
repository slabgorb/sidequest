# Demo Script — 16-9

**Setup:** Have sidequest-api running with the spaghetti_western genre pack loaded, sidequest-ui in dev mode. Open the game in a browser at localhost:5173. Pre-load a spaghetti western session in flickering_reach.

---

**Scene 1 — The Problem (Slide 2: Problem)**
*Timing: 1 minute*

Start in the old state (or describe it). Open the game without the new component. Trigger a non-combat encounter (e.g., enter a standoff by walking into the Last Chance Saloon in flickering_reach and insulting the outlaw at the bar). Show that the screen either falls back to a text log or displays nothing meaningful — no metric bar, no action buttons visible as encounter actions.

*Fallback if live demo isn't showing the broken state:* Slide 2 has the screenshot of the blank encounter screen from before this story.

---

**Scene 2 — The New Component: Standoff (Slide 3: What We Built)**
*Timing: 2 minutes*

With the new component active, trigger the same standoff. The screen transitions to:
- Widescreen letterbox bars top and bottom (black bars, cinematic crop)
- Two extreme close-up portrait cards facing each other — player left, outlaw right
- A tension bar labeled "TENSION" rising from 0 toward the threshold of 10, rendered in amber/sepia
- Four beat buttons at the bottom: **Size Up**, **Bluff**, **Flinch**, **Draw**

Click **Size Up**. Show the tension increment and the narrator's description of what the player learned about the opponent. Point out the metric bar advancing.

Click **Draw** to trigger resolution. Show the standoff resolve (or escalate to combat based on the roll).

*Fallback if live encounter doesn't trigger:* Navigate to `localhost:5173/dev/confrontation-preview?type=standoff&genre=spaghetti_western` — the dev preview harness renders the component in isolation with mock data.

---

**Scene 3 — Same Component, Different Genre (Slide 3: What We Built, continued)**
*Timing: 1.5 minutes*

Switch genre to pulp_noir. Trigger an interrogation scene. The same `ConfrontationOverlay` component renders, but now:
- No letterbox framing
- Resistance bar labeled "RESISTANCE" in noir red, descending
- Beats: **Pressure**, **Rapport**, **Evidence**, **Back Off**
- Portrait cards are shadowy, high-contrast

Point out: same React component, completely different look. The YAML confrontation declaration drove the labels, colors, and layout behavior. No new code was written.

*Fallback:* `localhost:5173/dev/confrontation-preview?type=interrogation&genre=pulp_noir`

---

**Scene 4 — Combat Regression Check (Slide 3, continued)**
*Timing: 45 seconds*

Trigger a combat encounter. Show that the CombatOverlay layout is visually unchanged — same HP bars, same attack buttons, same round counter. This component delegates to the existing combat display rather than replacing it. Zero visual regression.

*Fallback:* Screenshot on Slide 3 showing before/after combat side by side.

---
