# Demo Script — 45-26

**Scene 1 — Title (Slide 1, 0:00–0:30)**
Welcome the audience. Set context: "We're wrapping up a cleanup story — not a feature, but the kind of work that makes every future feature faster and safer."

**Scene 2 — Problem (Slide 2, 0:30–2:00)**
Show Slide 2. Explain the two-save-system problem with the library analogy. Point out: the old system was still reachable by anything that could call the API, even though the UI stopped using it months ago. "Dead code that's still live is the worst kind."

**Scene 3 — What We Built (Slide 3, 2:00–4:00)**
Show Slide 3. Open a terminal and demonstrate the absence of the old routes:

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run python -c "
from sidequest.server.app import create_app
from pathlib import Path
import tempfile, os
with tempfile.TemporaryDirectory() as d:
    app = create_app(genre_pack_search_paths=[Path(d)], save_dir=Path(d))
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    legacy = [p for p in routes if '/api/saves' in p]
    print('Legacy /api/saves routes found:', legacy or 'NONE — clean')
    print('Active routes:', [p for p in routes if p.startswith('/api')])
"
```

Expected output: `Legacy /api/saves routes found: NONE — clean`. If this fails, show Slide 3 static screenshot of the route list instead.

**Scene 4 — Why This Approach (Slide 4, 4:00–5:30)**
Show Slide 4. Highlight the bug that was discovered during cleanup: "Removing dead code isn't just tidying — it forces you to verify the live path works correctly end-to-end. We found and fixed a bug where new games were silently skipping their opening scene."

**Scene 5 — Before/After (5:30–6:30)**
Show the before/after diagram slide. Narrate the two-path → one-path simplification. Reference the net line count: 1,718 lines removed, 818 added — ~900 lines net deleted from a safety-critical subsystem.

**Scene 6 — Test Guardrails (6:30–7:30)**
Run the enforcement test live:

```bash
uv run pytest tests/server/test_legacy_save_endpoints_removed.py -v
```

Expected: 3 tests pass — AC-1 (routes absent), AC-2 (helper absent), AC-3 (zero references in production code). If pytest hangs, show the test file directly and explain what each test checks.

**Scene 7 — Roadmap (Slide: Roadmap, 7:30–8:30)**
Show Roadmap slide. "This clears the last blocker for multiplayer save sharing — every game now has one canonical ID."

**Scene 8 — Questions (8:30+)**
Open floor.

---
