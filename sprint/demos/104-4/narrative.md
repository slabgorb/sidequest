# Narrative

## Problem Statement
**Problem:** In the SideQuest space-opera orrery — the interactive solar-system diagram players use to navigate between locations — belt labels like "broken drift" displayed upside-down on one side of the chart, making them illegible to players. Why it matters: the orrery is the primary navigation and world-flavor surface for space-opera sessions; unreadable labels erode the visual polish that sells the setting to players at a glance, and the affected worlds (coyote_star, aureate_span) are active play destinations.

---

## What Changed
Imagine text painted along the inside of a curved highway sign. If the painter uses the same brush stroke regardless of which side of the road the sign faces, half the signs end up readable and half are mirror-image. The orrery had exactly this problem: a single rule decided when to flip belt labels upright — a rule that was correct for full circular orbits but backwards for partial arc belts. A label like "broken drift" (a 90-degree arc in the upper half of the chart) had its text travelling in the wrong direction, so the renderer's automatic correction flipped it the wrong way.

The fix teaches the renderer to distinguish the two cases. Full orbital rings — which always curve through the bottom of the chart at their halfway point — keep the original rule. Partial arc belts now use a geometry-based test: if the arc's midpoint sits in the upper half of the diagram (where text naturally travels right-to-left), apply the 180° flip; otherwise leave it alone. A secondary cleanup synchronized the diagnostic telemetry so the internal "did we flip?" readout matches what actually appears on screen.

---

## Why This Approach
The spec offered two mechanical paths: reverse the SVG path direction, or flip the rendered glyphs 180°. The team chose the glyph-flip because the rotation machinery already existed and was already tested — adding a second path-construction branch would have been new surface area with no visual difference. The result is fewer lines changed, lower regression risk, and a fix that is easy to verify visually: "broken drift" now reads left-to-right regardless of which side of the chart it lands on.

The telemetry cleanup was also conservative: rather than adding new instrumentation (the original spec said none was needed for a cosmetic change), the team found that the existing OTEL measurement for this code path was unreachable in production — the suppression layer never routes arc-belt labels through the strategy path that emits the span. The fix corrects the formula anyway as defensive hygiene so the code and its own comments agree, but it carries zero production risk.

---

## Before/After
| | Before | After |
|---|---|---|
| **"broken drift" label** | Renders upside-down; text travels right-to-left along the arc, glyphs inverted | Renders upright; `rotate(180 21.57 -80.49)` applied about the label's own midpoint |
| **Lower-half arc belt** | Correctly unflipped (existing behavior preserved) | Correctly unflipped — no regression |
| **Full orbital ring labels** | Flipped at the bottom half-point (correct) | Unchanged — same rule, same behavior |
| **OTEL `textpath_upright_flip` span** | SVG flip and telemetry used two different heuristics (latent inconsistency) | Both derive from the same geometry-resolved value — code matches its own invariant comment |
| **Test coverage** | One test pinned the bug (`test_upper_arc_arc_belt_label_has_no_transform`) | Three tests guard both directions: upper-arc flipped, lower-arc not flipped, exact broken-drift shape (30°→120°) flipped; plus two re-baselined SVG snapshots |
| **Lines changed** | — | ~40 lines across `render.py` + test file + 2 SVG snapshots |
