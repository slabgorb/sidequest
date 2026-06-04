**Slide 1: Title** — Introduce the story: "Combat E2E Tests: From Silent Failure to Green."

**Slide 2: Problem** — Show the raw error output (approximately 30 seconds):
```
pytest tests/e2e/test_encounter_wiring_e2e.py -v
```
Point to the output lines reading `ERROR tests/e2e/... fixture 'session_handler_factory' not found` and `ERROR tests/e2e/... fixture 'span_exporter' not found`. Emphasize: "These tests weren't failing — they were erroring before they could even start. The engine had no safety net."

**Slide 3: What We Built** — Walk through the fixture move (45 seconds). Show `tests/conftest.py` now containing `session_handler_factory` and `span_exporter`. No new logic — just new location.

**Slide 4: Why This Approach** — One sentence: "pytest looks for shared setup in parent directories; moving one level up is the minimal correct fix." (15 seconds)

**Slide 5: Before/After** — Side-by-side terminal output (60 seconds):
- Left column: the old `fixture not found` crash
- Right column, run live:
```
pytest tests/e2e/test_encounter_wiring_e2e.py -v
```
Expected output: both `test_combat_walkthrough_initiate_tick_resolve` and `test_xp_award_higher_in_combat_than_out` show `PASSED`.

*Fallback if live demo fails:* Show Slide 5 screenshot with the passing output pre-captured.

**Roadmap slide** — Explain what this unlocks (see below).

**Questions**

---