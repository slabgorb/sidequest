**Setup (before the session):** Have the `coyote_star` world loaded in the orrery viewer. You need two screenshots or renders — pre-fix and post-fix — since the fix has already merged. If you want a live diff, check out the commit before `feat/104-4-orrery-arc-label-sweep` and render the orrery, then check out the fix commit and re-render.

**Slide 1 (Title) — 30 seconds**
Open with "SideQuest Sprint Update — Story 104-4: Orrery Label Polish." One sentence: "A cosmetic fix that makes belt labels readable on both sides of the system map."

**Slide 2 (Problem) — 90 seconds**
Show the before-state screenshot of the `coyote_star` orrery. Point to the "broken drift" arc belt in the upper-left quadrant. Zoom in: the label text is rotated ~180°, rendering upside-down relative to a player reading the screen. Say: "This is the `broken drift` orbital belt — a named navigational hazard in the coyote_star system. Players navigating to it saw the label inverted. It looked like a rendering glitch."

If the screenshot isn't available, show Slide 2 alone and describe: "The label appeared as if you were reading the map from the back of the page."

**Slide 3 (What We Built) — 90 seconds**
Show the after-state screenshot with "broken drift" reading left-to-right, upright. Then show the two-line geometry condition (`sin(mid_deg) > 0`) on screen as a code snippet. Say: "We taught the renderer two separate rules — one for full orbital rings, one for partial arc belts. The math is straightforward: if the arc's midpoint is in the upper half of the diagram, the text needs the flip; otherwise it doesn't. Four files changed, 384 tests green."

Exact terminal command for live verification:
```bash
cd ~/Projects/sidequest-server && uv run pytest tests/orbital/test_render_orrery_v2.py -v -k "upright_flip or broken_drift"
```
Expected: 3 tests collected, 3 passed. Output includes `test_broken_drift_shaped_belt_is_flipped`, `test_upper_arc_arc_belt_label_is_flipped`, `test_lower_arc_arc_belt_label_has_no_transform`.

If pytest fails (stale env): fall back to Slide 3 with the snapshot image and the test names listed as bullets.

**Slide 4 (Why This Approach) — 60 seconds**
"We reused the existing flip mechanism rather than rebuilding the path geometry. Same visual result, smaller change, lower risk."

**Before/After slide — 60 seconds**
Side-by-side of the SVG snapshots. Left: `broken drift` with the upside-down transform. Right: `broken drift` with `rotate(180 21.57 -80.49)` applied correctly about its own midpoint. These are the actual regression-guarded snapshot files at `tests/orbital/snapshots/coyote_star_callouts_system_t0.svg`.

**Roadmap slide — 45 seconds**
"This closes the cosmetic gap for Epic 104 — the single-system orrery collapse work. Next stories wire the lore-page Map section to the cartography graph and add NPC portrait pins to system locations."

**Questions — open**

---