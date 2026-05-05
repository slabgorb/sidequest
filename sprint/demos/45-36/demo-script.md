# Demo Script — 45-36

**Total runtime: ~8 minutes**

**Scene 1 — Title (0:00–0:30) | Slide 1**
Open on the title slide. "Today we're closing out the last item from the 45-10 review cycle. This is a 1-point cleanup story — no new features, but we're shipping it as a formal story because the gaps flagged were real reliability risks."

**Scene 2 — Problem (0:30–2:00) | Slide 2**
"The scrapbook coverage detector shipped in 45-10. A reviewer walked the code and found 15 items. I'll show you the three highest-risk ones."

- Point at the "silent gap detection" bullet. "The detector found gaps and did nothing observable. In production, we couldn't tell if it had fired."
- Point at the "vacuous test" bullet. "One test in our suite was passing every single day and asserting nothing. It was a false green light."
- Point at the "OTEL accumulation" bullet. "Our tracing fixture was accumulating state across the test run. Intermittent failures in any OTEL test could have been this — not the code under test."

**Scene 3 — What We Built (2:00–4:30) | Slide 3**
Live demo. In the terminal:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_scrapbook_coverage.py -v --tb=short 2>&1 | tail -30
```

Point at the passing test names. "Notice `test_non_contiguous_gap_pattern` and `test_out_of_range_rows_excluded` — those are the two new edge-case tests. Before this story, those failure modes were untested."

Then:
```bash
grep -n "logger.warning" sidequest/game/scrapbook_coverage.py
```
Show the output: `120:    logger.warning('scrapbook.coverage_gap_detected genre=%s world=%s slug=%s gap_count=%d gap_rounds=%s', ...)`
"Now every gap detection emits a structured log line the GM panel can read."

**Fallback for Scene 3:** If tests fail to run, switch to Slide 3 and read the before/after bullets. "The test output I'm showing here was captured this morning — here's what it looked like."

**Scene 4 — Why This Approach (4:30–5:30) | Slide 4**
"We kept every change as the minimum that eliminates the risk. No refactors, no new features. A reviewer flagged 15 items; we fixed all 15 with no scope creep."

**Scene 5 — Before/After (5:30–7:00) | Before/After Slide**
Walk through the comparison table on the slide (see Before/After section below).

**Scene 6 — Roadmap (7:00–7:45) | Roadmap Slide**
"This closes the 45-10 review cycle completely. The coverage detector is now production-observable, fully tested, and documented correctly. It's the foundation for the save-continuity work coming in epic 46."

**Scene 7 — Questions (7:45–8:00) | Questions Slide**

---
