# OTEL Dashboard Relocation — Design

**Date:** 2026-04-27
**Status:** Design approved, awaiting plan
**Related:** ADR-090 (OTEL Dashboard Restoration), ADR-031 (Game Watcher Semantic Telemetry)

## Goal

Collapse the OTEL dashboard from a 1042-line standalone proxy script
(`scripts/playtest_dashboard.py`) into a single FastAPI route on the
existing `sidequest-server`, served at `GET /dashboard`. Eliminate the
second process and the WebSocket re-broadcast plumbing.

## In Scope

- New FastAPI route on `sidequest-server` returning the dashboard HTML.
- Extract embedded HTML to a static file shipped with the package.
- Modify the embedded JS so its WebSocket connects to `/ws/watcher`
  (same origin — no proxy).
- Delete `scripts/playtest_dashboard.py` entirely.
- Retarget `just otel` to open the new URL in a browser.
- Update `pf-otel` skill docs (both `.claude` and `.pennyfarthing`
  copies) and the ADR / PRD references that name the old script path.

## Out of Scope

- Any ADR-090 Phase 2 work (span emission re-implant, validator
  routing). The dashboard relocation is independent of those.
- Splitting the embedded HTML / CSS / JS into separate assets.
- Late-joiner event replay. Today the proxy keeps a 200-event ring
  buffer; after this change, a browser opening mid-game sees only
  events from connect-time onward.
- Any change to `WatcherHub`, `WatcherSpanProcessor`, or
  `/ws/watcher`. All three are reused as-is.

## Architecture

### Before

```
browser ──HTTP──▶ playtest_dashboard.py:9765   (serves HTML)
browser ──WS────▶ playtest_dashboard.py:9766   (re-broadcasts spans)
                          │
                          └──WS client──▶ sidequest-server:8765/ws/watcher
```

Two extra processes (HTTP listener + WS server), one upstream WS proxy
connection, a 200-event ring buffer for late joiners.

### After

```
browser ──HTTP──▶ sidequest-server:8765/dashboard       (HTMLResponse)
browser ──WS────▶ sidequest-server:8765/ws/watcher      (existing endpoint)
```

One process. No proxy. No ring buffer. The dashboard HTML's JS opens
its own WebSocket against the same origin.

## File Layout

### New files

| Path | Purpose |
|------|---------|
| `sidequest-server/sidequest/server/static/dashboard.html` | The HTML extracted verbatim from `DASHBOARD_HTML`, with one JS edit (see "JS Change"). |
| `sidequest-server/sidequest/server/dashboard.py` | ~25 LOC. Registers `GET /dashboard` and returns `FileResponse(static/dashboard.html)`. Sits next to `app.py` and `watcher.py`. |

### Modified files

| Path | Change |
|------|--------|
| `sidequest-server/sidequest/server/app.py` | Register the dashboard route during app construction (one line, alongside the existing `/ws/watcher` registration around line 200). |
| `sidequest-server/pyproject.toml` | Add `static/*.html` to package data so the file ships with installs. |
| `justfile` | Change the `otel` recipe to open `http://localhost:8765/dashboard` in a browser (use `python -m webbrowser` for cross-platform portability). |
| `.claude/skills/pf-otel/skill.md` | Replace "run `just otel` to start the proxy on 9765" prose with "open `http://localhost:8765/dashboard` (server must be running via `just up`)". |
| `.claude/skills/pf-otel/otel.md` | Same update. |
| `.pennyfarthing/skills/pf-otel/skill.md` | Same update. |
| `.pennyfarthing/skills/pf-otel/otel.md` | Same update. |
| `docs/adr/058-claude-subprocess-otel-passthrough.md` (around line 108) | Update the `playtest_dashboard.py` table entry to point at `sidequest-server/sidequest/server/dashboard.py`. |
| `docs/prd/prd-procedural-world-grounding.md` (around line 553) | Update the `scripts/playtest_dashboard.py` reference. |

### Deleted files

| Path | LOC | Notes |
|------|-----|-------|
| `scripts/playtest_dashboard.py` | 1042 | Entirely removed. The HTML is preserved in the new static file; the proxy plumbing is no longer needed. |

## JS Change

The embedded JS in `DASHBOARD_HTML` today has:

```js
const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${proto}//${location.host}/ws`);
```

The proxy rewrites that `/ws` path before serving. After the move, the
static file is served as-is, so we change the literal:

```js
const ws = new WebSocket(`${proto}//${location.host}/ws/watcher`);
```

That is the entire JS change. Everything else (state machine,
rendering, flame chart, NPC tables, trope display, etc.) is untouched.

## Tests

### New unit test

`sidequest-server/tests/server/test_dashboard_route.py`:

- `GET /dashboard` returns 200, `Content-Type: text/html`, body contains
  the dashboard's `<title>` text.
- Body contains the literal string `'/ws/watcher'`. This is a
  regression guard: anyone later editing the JS to point at a different
  path breaks this test.
- Wiring test: `from importlib.resources import files;
  files("sidequest.server").joinpath("static/dashboard.html").is_file()`
  confirms the package-data declaration is honored at install time.

### No JS test

The embedded JS already has zero test coverage. Adding a JS test is
out of scope for this change.

### Manual verification

`just up`, open `http://localhost:8765/dashboard`, run a turn, confirm
spans flow into the live event list.

## Risk and Rollout

**Low risk.** The server-side WebSocket and span infrastructure do not
change at all. The new route is purely additive. The only
externally-visible change is that `just otel` opens a browser instead
of starting a server on port 9765.

**One-time muscle-memory hit.** Anyone with `localhost:9765`
bookmarked needs to re-bookmark `localhost:8765/dashboard`. Worth a
note in the commit body.

**Backout.** `git revert` restores the script. Nothing destructive.
