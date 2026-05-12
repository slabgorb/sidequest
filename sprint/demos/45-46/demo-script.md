# Demo Script — 45-46

**Total time: 4 minutes**

**Slide 1 (Title) — 0:00–0:20**
"Today we're closing out a cleanup task that's easy to describe: we finished what we started. Three weeks ago we renamed an internal component. Today's story removes the safety net we used during that rename."

**Slide 2 (Problem) — 0:20–1:00**
"Compatibility shims are promises with expiration dates. We made a promise: 'old name works for one release, then it's gone.' This story is us keeping that promise. The risk of not doing this: other code quietly starts depending on the shim, and 'temporary' becomes permanent."

*If asked "what's a shim?"*: "It's a forwarding address. Old code sends mail to the old name; the shim intercepts it and delivers to the new name. Useful for a week, harmful for a year."

**Slide 3 (What We Built) — 1:00–2:00**
Live terminal — show the test suite passing:
```bash
uv run pytest tests/game/test_npc_encounter_log_tag_rename.py -v
```
Point to `test_scene_momentum_encounter_tag_unchanged` — note the last 3 lines assert `not hasattr(sidequest.game, "EncounterTag")`. "This is the regression guard. If the shim ever comes back, this test fails immediately. The suite is now the enforcer."

*Fallback if terminal unavailable:* Show Slide 4 and read the test name aloud.

**Slide 4 (Why This Approach) — 2:00–3:00**
"We could have left the shim indefinitely. The cost is invisible until it isn't — a future developer assumes the old name is stable, builds something on it, and now removing it breaks that thing. Removing on schedule keeps the codebase honest."

**Before/After slide — 3:00–3:30**
Walk through the before/after section below. "Before: 30 lines of shim code, 2 tests validating the warning. After: 0 shim lines, 1 test that asserts the old name stays gone."

**Questions — 3:30–4:00**

---
