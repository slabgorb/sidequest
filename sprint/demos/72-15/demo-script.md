**Total runtime:** ~8 minutes

**Slide 1 (Title) — 0:00–0:30**
Introduce the story: "Today we're closing a test coverage gap in the monster-seeding system."

**Slide 2 (Problem) — 0:30–2:00**
Show the before state. Open a terminal and run:
```bash
cd ~/Projects/sidequest-server
git show HEAD~1:tests/conftest.py | grep -A5 "_CAVERNS_SUNDEN_DEPRECATED_TESTS"
```
Point out `"server/dispatch/test_pregen.py"` in the skip list. Then show what that looked like at test time:
```bash
git stash  # temporarily restore old state for demo
uv run pytest tests/server/dispatch/test_pregen.py -v 2>&1 | tail -20
```
Expected output: `17 skipped` — zero tests ran, zero tests failed, zero tests warned. Silent.
Fallback: show Slide 2 screenshot of the "17 skipped, 0 passed" output if stash is messy.

**Slide 3 (What We Built) — 2:00–4:30**
Restore current code (`git stash pop`), then run the tests live:
```bash
uv run pytest tests/server/dispatch/test_pregen.py -v
```
Expected: `17 passed, 0 skipped`. Show the test names scrolling — `test_seed_manual_two_cultures`, `test_seed_manual_no_cultures_falls_back`, `test_e2e_fixture_populates_manual`, etc. Point out that the e2e now references `test_genre/flickering_reach`, not `caverns_sunden`.

To confirm the old world reference is gone:
```bash
grep -n "caverns_sunden" tests/server/dispatch/test_pregen.py
```
Expected: one comment line only, no code references.

**Slide 4 (Why This Approach) — 4:30–5:30**
Show the fixture world briefly:
```bash
ls tests/fixtures/packs/test_genre/worlds/flickering_reach/
```
Point out `cultures.yaml`, `creatures.yaml` — a minimal self-contained world that lives in the repo and doesn't change with content migrations.

**Before/After slide — 5:30–6:30**
Refer to Before/After section below.

**Roadmap slide — 6:30–7:30**
Brief forward-look (see Roadmap section).

**Questions — 7:30–8:00**

---