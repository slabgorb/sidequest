# Demo Script — 50-27

**Scene 1 — Title (Slide 1, ~30 seconds)**
Open with: "This is a one-line fix that unblocked a week's worth of feature work."

**Scene 2 — The Problem (Slide 2, ~60 seconds)**
Show the failing test output. Exact command:
```bash
cd sidequest-server && uv run pytest tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html -v
```
Expected pre-fix output:
```
FAILED tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html
AssertionError: assert 'NOT a stored snapshot' in [page text]
```
*Fallback if live demo fails: show Slide 2 with the pre-fix error text above.*

**Scene 3 — What We Built (Slide 3, ~60 seconds)**
Show the diff — it's literally one line:
```
- assert "NOT a stored snapshot" in resp.text  # honesty contract visible
+ assert "stores no per-round snapshot" in resp.text  # honesty contract visible
```
Point to `forensics.html` line 295 in a browser: open `http://localhost:8765/forensics`, navigate to any round's drill-down, show the comparison panel label containing the exact phrase.

**Scene 4 — Why This Approach (Slide 4, ~45 seconds)**
Explain the honesty contract: "The GM panel exists so a 40-year game master can't be fooled. If this phrase disappears from the screen, the test fails loudly. That's the tripwire."

**Scene 5 — Before/After (optional, ~30 seconds)**
Show the full test suite run:
```bash
uv run pytest -q
```
Expected output: `6338 passed, 0 failed, 400 skipped`
*Fallback: show screenshot of the green run from the session log.*

**Scene 6 — Roadmap (Slide: Roadmap, ~30 seconds)**
"This clears the gate for the A/B evaluation harness merge — that's the next thing up."

---
