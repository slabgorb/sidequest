# OTEL Dashboard Relocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the 1042-line `scripts/playtest_dashboard.py` proxy server into a single FastAPI route at `GET /dashboard` on `sidequest-server`. The browser loads the dashboard from the server itself and opens a same-origin WebSocket against the existing `/ws/watcher` endpoint.

**Architecture:** The HTML is extracted from the proxy's `DASHBOARD_HTML` constant and shipped as a static asset inside the `sidequest.server` package. A new `dashboard.py` registers a single `GET /dashboard` route that returns it via `FileResponse`. The embedded JS is edited so its WebSocket connects to `/ws/watcher` instead of the proxy's `/ws`. The proxy script is deleted.

**Tech Stack:** Python 3.12, FastAPI, hatchling (build backend), pytest + httpx `TestClient`, just (task runner).

**Spec:** [`docs/superpowers/specs/2026-04-27-otel-dashboard-relocation-design.md`](../specs/2026-04-27-otel-dashboard-relocation-design.md)

---

## File Structure

| Path | Status | Responsibility |
|------|--------|----------------|
| `sidequest-server/sidequest/server/static/dashboard.html` | NEW | Shipped HTML+CSS+JS for the OTEL dashboard. |
| `sidequest-server/sidequest/server/dashboard.py` | NEW | ~25-line module exporting `dashboard_router` (`APIRouter`). |
| `sidequest-server/tests/server/test_dashboard_route.py` | NEW | Three tests: package-data shipping, HTTP response, JS path regression guard. |
| `sidequest-server/sidequest/server/app.py` | MODIFY | Import and `include_router(dashboard_router)`. |
| `justfile` | MODIFY | Replace `otel` recipe with a browser-opener. |
| `.claude/skills/pf-otel/skill.md` | MODIFY | Drop "proxy on 9765" prose; document new URL. |
| `.claude/skills/pf-otel/otel.md` | MODIFY | Same. |
| `.pennyfarthing/skills/pf-otel/skill.md` | MODIFY | Same. |
| `.pennyfarthing/skills/pf-otel/otel.md` | MODIFY | Same. |
| `docs/adr/058-claude-subprocess-otel-passthrough.md` | MODIFY | Update `playtest_dashboard.py` reference (around line 108). |
| `docs/prd/prd-procedural-world-grounding.md` | MODIFY | Update `scripts/playtest_dashboard.py` reference (around line 553). |
| `scripts/playtest_dashboard.py` | DELETE | 1042 LOC — entirely removed. |

The hatchling wheel target already declares `packages = ["sidequest"]`, which auto-ships every file under `sidequest/`. No `pyproject.toml` change is needed; Task 2 includes a wiring test that verifies this.

---

## Task 1: Failing test for package-data shipping

**Files:**
- Test: `sidequest-server/tests/server/test_dashboard_route.py`

- [ ] **Step 1.1: Write the package-data test**

Create `sidequest-server/tests/server/test_dashboard_route.py` with:

```python
"""Tests for the /dashboard route — relocates the OTEL dashboard from
``scripts/playtest_dashboard.py`` into the sidequest-server FastAPI app.
"""

from __future__ import annotations

from importlib.resources import files


def test_dashboard_html_ships_with_package() -> None:
    """The dashboard HTML must live inside the ``sidequest.server``
    package so it is included in the wheel. If this fails, the file
    was added under the wrong directory or the hatchling include
    config drifted.
    """
    asset = files("sidequest.server").joinpath("static/dashboard.html")
    assert asset.is_file(), f"dashboard.html missing from package: {asset}"
```

- [ ] **Step 1.2: Run the test and confirm it fails**

Run from `/Users/slabgorb/Projects/oq-1/sidequest-server/`:

```bash
uv run pytest tests/server/test_dashboard_route.py::test_dashboard_html_ships_with_package -v
```

Expected: FAIL with `AssertionError: dashboard.html missing from package: ...`

- [ ] **Step 1.3: Commit the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add tests/server/test_dashboard_route.py
git commit -m "test: add failing test for /dashboard package-data shipping"
```

---

## Task 2: Extract dashboard HTML into the package

**Files:**
- Create: `sidequest-server/sidequest/server/static/dashboard.html`

- [ ] **Step 2.1: Create the static directory**

```bash
mkdir -p /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/static
```

- [ ] **Step 2.2: Extract and patch the HTML**

The current dashboard HTML lives as a Python triple-quoted string at `scripts/playtest_dashboard.py:54-944` (constant `DASHBOARD_HTML`). One JS line needs editing during extraction so the browser hits `/ws/watcher` (the existing FastAPI endpoint) instead of `/ws` (the proxy's path).

Run this from `/Users/slabgorb/Projects/oq-1/`:

```bash
uv run --project sidequest-server python3 - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, "/Users/slabgorb/Projects/oq-1/scripts")
# The script has CLI machinery at module load. Importing the symbol
# from the file source avoids running argparse.
src = Path("/Users/slabgorb/Projects/oq-1/scripts/playtest_dashboard.py").read_text()
ns: dict = {}
# Execute only the constant assignment block — find the triple-quoted
# DASHBOARD_HTML and bind it.
start = src.index('DASHBOARD_HTML = """')
end = src.index('"""', start + len('DASHBOARD_HTML = """')) + 3
exec(src[start:end], ns)

html = ns["DASHBOARD_HTML"]
needle = "${proto}//${location.host}/ws`"
replacement = "${proto}//${location.host}/ws/watcher`"
assert needle in html, "expected JS WebSocket connect line not found"
html = html.replace(needle, replacement)

out = Path(
    "/Users/slabgorb/Projects/oq-1/sidequest-server/"
    "sidequest/server/static/dashboard.html"
)
out.write_text(html)
print(f"wrote {out} ({len(html)} bytes)")
PY
```

Expected: prints `wrote ...dashboard.html (NNNN bytes)` with NNNN somewhere around 35-40k.

- [ ] **Step 2.3: Verify the WebSocket path edit landed**

```bash
grep -c "/ws/watcher" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/static/dashboard.html
grep -c "/ws\`" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/static/dashboard.html
```

Expected: first command prints `1` (the connect line), second prints `0` (no leftover proxy path).

- [ ] **Step 2.4: Run the package-data test and confirm it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_dashboard_route.py::test_dashboard_html_ships_with_package -v
```

Expected: PASS.

- [ ] **Step 2.5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/server/static/dashboard.html
git commit -m "feat: ship dashboard.html as static asset in sidequest.server"
```

---

## Task 3: Failing test for the HTTP route

**Files:**
- Modify: `sidequest-server/tests/server/test_dashboard_route.py`

- [ ] **Step 3.1: Add the route test**

Append to `sidequest-server/tests/server/test_dashboard_route.py`:

```python
from fastapi.testclient import TestClient

from sidequest.server.app import create_app


def test_dashboard_route_returns_html() -> None:
    """``GET /dashboard`` must return the dashboard HTML directly from
    the FastAPI app (no separate proxy server)."""
    client = TestClient(create_app())
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>SideQuest OTEL Dashboard</title>" in response.text


def test_dashboard_html_connects_to_ws_watcher() -> None:
    """Regression guard: the embedded JS must open its WebSocket against
    ``/ws/watcher`` (the FastAPI watcher endpoint), not ``/ws`` (the old
    proxy path). If a future edit to the static asset changes this,
    fail loudly here rather than silently breaking the dashboard.
    """
    client = TestClient(create_app())
    response = client.get("/dashboard")
    assert "${proto}//${location.host}/ws/watcher`" in response.text
    assert "${proto}//${location.host}/ws`" not in response.text
```

- [ ] **Step 3.2: Run both new tests and confirm they fail**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_dashboard_route.py -v
```

Expected: `test_dashboard_html_ships_with_package` PASSES; the two new tests FAIL with HTTP 404 (route not registered yet).

- [ ] **Step 3.3: Commit the failing tests**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/tests/server/test_dashboard_route.py
git commit -m "test: add failing tests for GET /dashboard route and JS path"
```

---

## Task 4: Implement the dashboard route

**Files:**
- Create: `sidequest-server/sidequest/server/dashboard.py`
- Modify: `sidequest-server/sidequest/server/app.py`

- [ ] **Step 4.1: Create the route module**

Write `sidequest-server/sidequest/server/dashboard.py`:

```python
"""HTTP route that serves the OTEL dashboard HTML.

The dashboard is a single self-contained HTML file (with embedded CSS
and JavaScript) shipped under ``sidequest/server/static/``. The browser
loads it from this route and opens its own WebSocket against
``/ws/watcher`` on the same origin. There is no separate proxy server.
"""

from __future__ import annotations

from importlib.resources import as_file, files

from fastapi import APIRouter
from fastapi.responses import FileResponse

dashboard_router = APIRouter()


@dashboard_router.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    """Return the dashboard HTML."""
    asset = files("sidequest.server").joinpath("static/dashboard.html")
    with as_file(asset) as path:
        return FileResponse(path, media_type="text/html")
```

- [ ] **Step 4.2: Register the router in `create_app`**

Open `sidequest-server/sidequest/server/app.py`. Add an import near the other server-route imports (around line 22-30), inserting after the existing `from sidequest.server.rest import create_rest_router` line:

```python
from sidequest.server.dashboard import dashboard_router
```

Then in `create_app`, register the router. Find the existing block at roughly line 208-210:

```python
    # --- REST routes ---
    rest_router = create_rest_router()
    app.include_router(rest_router)
```

Add immediately below it:

```python
    # --- /dashboard — OTEL dashboard HTML (browser opens its own WS). ---
    app.include_router(dashboard_router)
```

- [ ] **Step 4.3: Run the route tests and confirm they pass**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_dashboard_route.py -v
```

Expected: all three tests PASS.

- [ ] **Step 4.4: Run the full server-test suite to confirm nothing broke**

```bash
cd /Users/slabgorb/Projects/oq-1
just server-test
```

Expected: same pass/fail counts as before this work (the 27 pre-existing failures remain; nothing new fails).

- [ ] **Step 4.5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/server/dashboard.py sidequest-server/sidequest/server/app.py
git commit -m "feat: serve OTEL dashboard at GET /dashboard on sidequest-server"
```

---

## Task 5: Retarget the `just otel` recipe

**Files:**
- Modify: `justfile`

- [ ] **Step 5.1: Replace the `otel` recipe**

Open `/Users/slabgorb/Projects/oq-1/justfile`. Find lines 192-194:

```just
# OTEL dashboard — browser-friendly /ws/watcher viewer
otel port="9765":
    uv run python3 {{root}}/scripts/playtest_dashboard.py --dashboard-port {{port}}
```

Replace with:

```just
# OTEL dashboard — opens the browser-friendly /ws/watcher viewer
# served by sidequest-server itself. Server must already be running
# (e.g. via `just up` or `just server`).
otel:
    uv run python3 -m webbrowser http://localhost:8765/dashboard
```

- [ ] **Step 5.2: Verify the recipe works**

Make sure the server is running (`just up` in another shell), then:

```bash
just otel
```

Expected: a browser tab opens to `http://localhost:8765/dashboard` and the dashboard renders. (If the server is not running, the tab will fail to load — that's fine; this step is just the recipe-fires test.)

- [ ] **Step 5.3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add justfile
git commit -m "chore(justfile): retarget just otel to served /dashboard route"
```

---

## Task 6: Delete the old proxy script

**Files:**
- Delete: `scripts/playtest_dashboard.py`

- [ ] **Step 6.1: Confirm no other code references the script**

```bash
grep -rn "playtest_dashboard" /Users/slabgorb/Projects/oq-1 \
  --include='*.py' --include='*.md' --include='justfile' --include='*.yaml' --include='*.yml' \
  | grep -v "/.venv/" | grep -v "__pycache__" | grep -v "/node_modules/"
```

Expected: only matches in `docs/adr/058-claude-subprocess-otel-passthrough.md`, `docs/prd/prd-procedural-world-grounding.md`, and ADR-090 (those are doc references — handled in Task 8). No live code or recipe references.

- [ ] **Step 6.2: Delete the script**

```bash
rm /Users/slabgorb/Projects/oq-1/scripts/playtest_dashboard.py
```

- [ ] **Step 6.3: Run the full server suite once more**

```bash
cd /Users/slabgorb/Projects/oq-1
just server-test
```

Expected: same as Step 4.4 — no new failures.

- [ ] **Step 6.4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add scripts/playtest_dashboard.py
git commit -m "chore: remove scripts/playtest_dashboard.py — superseded by served /dashboard"
```

---

## Task 7: Update `pf-otel` skill docs

**Files:**
- Modify: `.claude/skills/pf-otel/skill.md`
- Modify: `.claude/skills/pf-otel/otel.md`
- Modify: `.pennyfarthing/skills/pf-otel/skill.md`
- Modify: `.pennyfarthing/skills/pf-otel/otel.md`

The four skill docs all describe `just otel` as starting a proxy on port 9765 with HTML on the dashboard port and WS on dashboard_port+1. After Task 5, that's wrong.

- [ ] **Step 7.1: Read each file to see exactly what needs editing**

```bash
grep -n "9765\|9766\|playtest_dashboard\|just otel\|--dashboard-port" \
  /Users/slabgorb/Projects/oq-1/.claude/skills/pf-otel/skill.md \
  /Users/slabgorb/Projects/oq-1/.claude/skills/pf-otel/otel.md \
  /Users/slabgorb/Projects/oq-1/.pennyfarthing/skills/pf-otel/skill.md \
  /Users/slabgorb/Projects/oq-1/.pennyfarthing/skills/pf-otel/otel.md
```

Note every line that mentions the old proxy.

- [ ] **Step 7.2: Edit each file**

In each of the four files, replace any prose along the lines of "run `just otel` to start the dashboard proxy on port 9765" with:

```markdown
The OTEL dashboard is served by `sidequest-server` itself at
`http://localhost:8765/dashboard`. Start it with `just up` (or `just
server`) and run `just otel` to open it in a browser. The dashboard
opens its own WebSocket against `/ws/watcher` on the same origin —
there is no separate proxy server.
```

Replace any `--dashboard-port` flag reference with a note that the port is no longer configurable (it follows whatever port `sidequest-server` is bound to).

If the same prose appears in `.claude/skills/pf-otel/` and `.pennyfarthing/skills/pf-otel/`, make the edits identical — these directories shadow the same skill.

- [ ] **Step 7.3: Re-grep to confirm no stale references remain**

```bash
grep -n "9765\|9766\|playtest_dashboard\|--dashboard-port" \
  /Users/slabgorb/Projects/oq-1/.claude/skills/pf-otel/*.md \
  /Users/slabgorb/Projects/oq-1/.pennyfarthing/skills/pf-otel/*.md
```

Expected: no matches.

- [ ] **Step 7.4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add .claude/skills/pf-otel/ .pennyfarthing/skills/pf-otel/
git commit -m "docs(pf-otel): update skill for /dashboard route relocation"
```

---

## Task 8: Update ADR / PRD references

**Files:**
- Modify: `docs/adr/058-claude-subprocess-otel-passthrough.md`
- Modify: `docs/prd/prd-procedural-world-grounding.md`

- [ ] **Step 8.1: Update ADR-058**

Open `docs/adr/058-claude-subprocess-otel-passthrough.md`. The table around line 108 has a row:

```markdown
| `playtest_dashboard.py` | HTML/JS dashboard, WebSocket server, HTTP serving |
```

Replace with:

```markdown
| `sidequest-server` /dashboard route | HTML/JS dashboard, served same-origin (see ADR-090 follow-up 2026-04-27) |
```

- [ ] **Step 8.2: Update the PRD reference**

Open `docs/prd/prd-procedural-world-grounding.md`. Around line 553:

```markdown
The GM dashboard (`scripts/playtest_dashboard.py`) must show:
```

Replace with:

```markdown
The GM dashboard at `http://localhost:8765/dashboard` (served by `sidequest-server`) must show:
```

- [ ] **Step 8.3: Confirm no other doc references remain**

```bash
grep -rn "scripts/playtest_dashboard\|playtest_dashboard\.py" /Users/slabgorb/Projects/oq-1/docs
```

Expected: matches only in ADR-090 (which is a historical ADR documenting the prior state — leave it alone) and possibly archived sprint files. No live PRD or current ADR references.

- [ ] **Step 8.4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add docs/adr/058-claude-subprocess-otel-passthrough.md docs/prd/prd-procedural-world-grounding.md
git commit -m "docs: update ADR-058 and PRD to point at served /dashboard route"
```

---

## Task 9: Manual end-to-end verification

This is a smoke check the test suite cannot perform — it spins the real ASGI app and a real browser.

- [ ] **Step 9.1: Boot the server**

```bash
cd /Users/slabgorb/Projects/oq-1
just up
```

Wait for the merged log tail to show `Application startup complete`.

- [ ] **Step 9.2: Open the dashboard**

```bash
just otel
```

Expected: a browser tab opens at `http://localhost:8765/dashboard`. The dashboard's connection indicator (`#dot` / `#conn-status`) should turn green / "Connected" within ~1s — that confirms the JS connected to `/ws/watcher` on the same origin and the server's `WatcherSpanProcessor` is wired.

- [ ] **Step 9.3: Trigger a span and confirm it surfaces**

In another terminal, run any action that emits a span — for example, hit the health endpoint or run a quick playtest scenario. The simplest signal is the hello-frame the watcher endpoint sends on connect (see `sidequest/server/watcher.py:170`). It should already appear in the dashboard's event list.

For a stronger signal, run:

```bash
just playtest-scenario <any scenario name with sub-second turnaround>
```

Expected: turn-related spans appear in the dashboard's flame chart and turn list.

- [ ] **Step 9.4: Tear down**

```bash
just down
```

- [ ] **Step 9.5: No commit — this task is verification only**

If anything in 9.1-9.3 failed, **stop** and diagnose. Do not paper over.

---

## Self-review checklist (post-write)

This was checked before publishing the plan; recorded here for traceability.

- **Spec coverage:**
  - ✓ New FastAPI route — Tasks 3, 4
  - ✓ Static file under package — Tasks 1, 2
  - ✓ JS edit `/ws` → `/ws/watcher` — Task 2 (extraction script) + Task 3 (regression test)
  - ✓ Delete old script — Task 6
  - ✓ Retarget `just otel` — Task 5
  - ✓ Skill doc updates (4 files) — Task 7
  - ✓ ADR + PRD doc updates — Task 8
  - ✓ Manual verification — Task 9
  - Out-of-scope items (no replay, no asset split, no WatcherHub change) are honored — no task touches those.

- **Placeholder scan:** No TBD / TODO / "implement later". Each step has either exact code or an exact command.

- **Type / name consistency:**
  - `dashboard_router` is the symbol exported from `dashboard.py` and imported in `app.py`. Consistent across Tasks 4.1 and 4.2.
  - `static/dashboard.html` is the asset path used in Tasks 1, 2, 3, and 4. Consistent.
  - `/dashboard` is the URL used in Tasks 3, 4, 5, 7, 8, 9. Consistent.
