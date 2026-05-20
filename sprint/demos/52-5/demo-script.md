# Demo Script — 52-5

**Setup (before the demo, ~2 min):**
- Have the SideQuest server running locally (`just server`)
- Have the UI running (`just client`) pointed at `localhost:8765`
- Have the GM dashboard open at `localhost:8765/dashboard` in a second browser tab
- Load a `caverns_and_claudes` session with at least one underground room

---

**Scene 1 — The Problem (Slide 2: Problem)**
*(~60 seconds)*

Open the GM dashboard and point to the OTEL span list. Show that — before this fix — there was no `tactical_grid.image_resolved` event appearing when the map loaded. Say: "The map was rendering, but we had no proof it was showing the right image. It could have been anything."

*Fallback if dashboard is empty:* Show Slide 2 directly — the bullet "No telemetry signal = no confidence in what the map is showing."

---

**Scene 2 — The Fix in Action (Slide 3: What We Built)**
*(~90 seconds)*

In the UI, navigate into an underground room. Watch the tactical grid panel load. Switch to the GM dashboard tab.

Point to the new `tactical_grid.image_resolved` span. It should show:
- `source: runtime`
- `url: https://r2.sidequest.io/genre_packs/caverns_and_claudes/.../<room_slug>.png` (or similar)
- `status: 200`

Say: "That span is the lie detector. If the image came from the server and loaded cleanly, it lights up green here. If it's missing or fell back to a default, we see a warning instead."

*Fallback if span doesn't appear:* Show Slide 3 screenshot of the span captured during QA — exact URL and status code visible.

---

**Scene 3 — The Automated Test (Slide 3 continued)**
*(~45 seconds)*

In a terminal, run:
```bash
just client-test --reporter=verbose --grep "TacticalGridRenderer"
```

Show the test output:
- `✓ renders cavern_image_url from server response`
- `✓ emits tactical_grid.image_resolved OTEL span with source=runtime`

Say: "This runs on every commit. If someone accidentally breaks the wiring, CI catches it before it reaches a playtest."

*Fallback:* Show Slide 3 bullet: "Automated guard — test fails if image source reverts to placeholder."

---

**Scene 4 — Roadmap tee-up (Slide: Roadmap)**
*(~30 seconds)*

"Now that the grid reliably shows server-sourced images and the GM can verify it in real time, the next step is adding room-transition animations and per-room image caching — both of which depend on this wiring being solid."

---
