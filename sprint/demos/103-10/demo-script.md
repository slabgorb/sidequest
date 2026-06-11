**Total runtime: ~12 minutes**

---

**Slide 1 (Title) — 0:00–0:45**
Open with the slide. Say: "We're closing out the Seaboard of Saints — nine stories, two new mechanics, one new world. This last story is the proof that it all hangs together."

---

**Slide 2 (Problem) — 0:45–2:00**
Narrate the risk: "We had Saints. We had Stocks. We had OTEL spans wired in. But 'all the pieces exist' isn't the same as 'the pieces work together.' The specific failure mode we were guarding against: the game narrates as if a drawback fired, but the engine never ran it. Players with 40 years of table experience — Keith and Jade specifically — will notice when the crunch is hollow."

Point out the secondary risk: "There's also an existing world — flickering_reach — that is intentionally Wild-mutant only. No Saints. If the Saint plumbing leaked into it, every game set there would start loading content it shouldn't see."

---

**Slide 3 (What We Built) — 2:00–5:30**
*Live demo — terminal open, server running with `just server`, test suite ready.*

Type:
```bash
uv run pytest tests/integration/test_seaboard_e2e.py -v --tb=short
```

Walk the audience through the output as it prints:
- "See `test_animal_stock_chargen_to_save` — that's the full pipeline for an Animal-strain character."
- "Watch for the `awn.stock.applied` assertion — this is the span check. If it fails here, the stock mechanic didn't actually run."
- "Now `test_saint_drawback_fires_in_confrontation` — this one picks Saint Agatha, who has the *Burning Hands* drawback. It enters a confrontation, triggers the drawback condition, and asserts on `awn.saint.applied` with mutation ID `burning_hands_penalty`."

*If the test run fails for any reason → cut to Slide 3 static screenshot showing a green prior run output.*

Then:
```bash
uv run pytest tests/integration/test_flickering_reach_regression.py -v
```
"flickering_reach loads. Zero Saint spans. This world is clean."

---

**Slide 4 (Why This Approach) — 5:30–7:30**
"Why OTEL spans instead of asserting on the narrator's text? Because the narrator is Claude. It can write 'your Saint's curse burns through you' whether or not the engine decremented anything. The span is the receipt. No receipt, no mechanic."

Display the GM panel dashboard (`just otel`, open browser to `localhost:8765/dashboard`). Find the `awn.saint.applied` span in the trace viewer. "A GM running Seaboard of Saints can watch this in real time. If the span doesn't appear after a Saint drawback scene, something is broken — and they'll know before the session ends."

---

**Slide 5 (Before/After) — 7:30–9:00**
Walk the Before/After slide. See section below for specifics.

---

**Slide 6 (Roadmap) — 9:00–11:00**
See Roadmap section below.

---

**Slide 7 (Questions) — 11:00–12:00**

---