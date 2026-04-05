# Demo Script — 25-8

**Setup before presenting:** Start the dev server with `npm run dev` from `sidequest-ui/`. Have a save file loaded with at least 8–10 narration beats so all three layouts look populated. Have the Settings panel accessible.

---

**Scene 1 — The problem (Slide 2: Problem) — ~90 seconds**

Open the game to the narrative view with a mid-session save. The scroll feed is running. Slowly scroll up to show that the story has accumulated 10+ passages. Point out: "Right now this is the only way to read the story — one long scroll. If you want the most recent beat, you scroll down. If you want to find something from earlier, you scroll up. There's no other mode."

*If demo connection fails: Show Slide 2 static screenshot of the scroll view.*

---

**Scene 2 — Settings toggle (Slide 3: What We Built) — ~60 seconds**

Open the Settings panel. Show the layout mode selector: three buttons labeled **Scroll**, **Focus**, **Cards** in a pill group. The Scroll button is highlighted (active state). Point out: "One setting. Three buttons. No modal, no page reload."

Click **Focus**. The narration area immediately switches to show a single passage, centered, with "← Prev" and "Next →" controls and a counter like **"7 / 10"** at the bottom. "The game jumped straight to the latest beat."

*If settings panel fails to open: Show the Slide 3 before/after screenshot.*

---

**Scene 3 — Focus mode navigation (Slide 3 continued) — ~90 seconds**

With Focus mode active, click **← Prev** twice. The counter changes: `7 / 10` → `6 / 10` → `5 / 10`. Each press swaps out one story beat for the previous one. Point out that **Next →** grays out at the last beat and **← Prev** grays out at the first — you can't navigate off the edge.

Type a player action in the input bar (e.g., `I search the ruins for survivors`) and submit it. Watch the counter automatically jump from `5 / 10` to `1 / 11` as the new narration arrives and Focus auto-advances.

*Fallback: Show Slide 3 screenshot showing the counter at "3 / 10" with Prev/Next buttons.*

---

**Scene 4 — Cards mode (Slide 3 continued) — ~60 seconds**

Click **Cards** in the selector. The view switches to a grid: each narration moment now appears as a rounded card with a subtle border. On the demo screen (full-width browser) show three columns. Resize the browser window narrower — live, the grid snaps to two columns, then one. "Responsive out of the box."

---

**Scene 5 — Persistence (Slide 4: Why This Approach) — ~45 seconds**

While in Cards mode, hard-refresh the browser (⌘R / F5). The page reloads cold — no game state passed. The narrative view comes back in **Cards** mode. Open browser DevTools → Application → Local Storage → `localhost:5173`. Show the key `sq-narrative-layout` with value `{"mode":"cards"}`. "The preference lives in the browser. No server round-trip, no login required."

*Fallback: Show Slide 4 with the local-storage screenshot.*

---

**Scene 6 — Test coverage (Slide 4 continued) — ~30 seconds**

In the terminal:
```bash
cd sidequest-ui && npx vitest run src/__tests__/layout-modes.test.tsx
```
38 tests, all green. Point out the test count: "38 tests across all three layouts, the selector, the hook, and the wiring into the main view."

---
