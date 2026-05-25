# Demo Script — 64-6

**Total time:** ~4 minutes

**Slide 1 — Title (0:00–0:15)**
Introduce the story: "We fixed a hidden startup knot that was making one of our dungeon map tests unreliable."

**Slide 2 — Problem (0:15–1:00)**
Explain the symptom. Say: "If you ran the full test suite, everything looked green. But if you pulled out just this one test and ran it alone, it failed every time." Show the failing command:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/test_region_projection_wiring.py::test_dungeon_map_frame_is_emitted_to_ui -v
```

If live demo is not available, show Slide 2 with the error output screengrab (ImportError or partially-initialized module message).

**Slide 3 — What We Built (1:00–2:00)**
Show the fix in plain terms using the before/after slide. "Two modules were locked in a handshake loop at startup. We cut the loop by moving the backwards-compatibility shortcut out of the cycle."

**Slide 4 — Why This Approach (2:00–2:30)**
"We took the smallest cut that solved the whole problem. No architectural surgery, no new abstractions — just remove the thing that was causing the knot."

**Before/After slide (2:30–3:15)**
Walk through the comparison (see section below). Show the green test run:

```bash
uv run pytest tests/test_region_projection_wiring.py::test_dungeon_map_frame_is_emitted_to_ui -v
```

Expected output: `1 passed` with no import warnings.

Then show the full dungeon suite still green:

```bash
uv run pytest tests/ -k "dungeon" -v
```

Fallback: if the live terminal isn't cooperating, switch to the Before/After slide and narrate the difference.

**Roadmap slide (3:15–3:45)**
See section below.

**Questions (3:45–4:00)**

---
