# Demo Script — 61-17

**Estimated runtime:** 8 minutes

**Slide 1: Title** — "Story 61-17: Test Hygiene After a Caching Optimization"

**Scene 1 (0:00–1:30) — Slide 2: The Problem**
Open with: "Three weeks ago we made the AI narrator faster. Today we're closing the paperwork on that improvement."

Explain the two-bucket model in one sentence: "The narrator has permanent rules (cached, always available) and turn-by-turn instructions (fresh, written each turn)."

Say: "Story 61-10 promoted narrator_constraints to the permanent bucket. The test suite didn't get the memo."

**Scene 2 (1:30–3:00) — Live demo: show the failing test**
In terminal, checkout the commit *before* the fix and run:
```bash
cd ~/Projects/sidequest-server
git stash  # or checkout pre-fix commit hash dffcf5b^
uv run pytest tests/agents/test_prompt_cache_attribution_otel.py::test_zones_carry_cache_boundary_flag -v
```
Show output: `FAILED — assert True is False`. Point out: "The code is telling the truth. The test is lying."

*Fallback if demo environment unavailable: show Slide 3 with the assertion before/after snippet.*

**Scene 3 (3:00–5:00) — Slide 3: What We Built**
Return to current code. Show the one-line change:
```bash
git show dffcf5b -- tests/agents/test_prompt_cache_attribution_otel.py
```
Point to: `assert section["cached"] is True  # was: is False`

Run the test now:
```bash
uv run pytest tests/agents/test_prompt_cache_attribution_otel.py -v
```
Show: `9 passed`. Say: "Nine tests, all green, including the one that was lying."

**Scene 4 (5:00–6:30) — Slide 4: Why This Approach**
"We could have moved the card back to the notepad. We didn't — because the optimization was correct and the test was stale. The guard rail still catches real regressions; it's just pointed at the right place now."

Optional: run the full server suite count:
```bash
uv run pytest --co -q 2>/dev/null | tail -3
```
Show: 7543 tests, 6 pre-existing content failures unrelated to this change.

**Scene 5 (6:30–8:00) — Roadmap slide, then Questions**
"This closes the 61-10 optimization loop cleanly. Next up: 61-18 audits whether another constraint (CONFRONTATION_TRIGGER_CONSTRAINT) is also misrouted — same class of problem, same discipline."

---
