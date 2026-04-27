---
parent: sprint/epic-45.yaml
workflow: tdd
---

# Story 45-26: Delete legacy /api/saves/* endpoints + (genre, world, player) save-path helper

## Business Context

MP-03 landed the unified slug-keyed save model: one `.db` per game slug,
stored at `<save_dir>/games/<slug>/save.db`, addressed by the `game_slug`
the client now sends on every SESSION_EVENT{connect}. The slug-mode UI is
the *only* live caller — `sidequest-ui/src/App.tsx` exclusively sends
`game_slug` (verified: `grep "game_slug"` → 11 references; `grep "genre.*world.*player_name"`
finds only the dead-branch comment at `App.tsx:1306` "Uses game_slug — no
legacy genre+world+player fallback").

Three legacy REST routes survived the migration as `deprecated=True`
shims, plus a (genre, world, player)-tuple save-path helper that those
routes call. Both are dead code that survived ADR-082's port to be on
the safe side. Per ADR-085 (tracker hygiene during the Rust→Python
port), these are exactly the kind of post-port residue the epic should
mop up: cleanup is cheap, and dead code masks coverage gaps —
`tests/server/test_rest.py:208–325` and `tests/e2e/test_server_e2e.py:300–301`
are the only callers, and the assertions there will silently pass even
if the underlying behavior breaks for everyone else.

There is one **non-test caller** that still uses the legacy helper
inside the server itself: the legacy genre+world+player branch of
`_handle_connect()` at `sidequest-server/sidequest/server/session_handler.py:2065–2314`,
which calls `db_path_for_session()` at `:2094`. Because the UI no longer
sends `payload.genre/world/player_name` — it always sends `game_slug` —
this branch is also unreachable from production traffic. The story's
"clean grep" acceptance criterion forces the legacy branch out as well.

Audience framing: invisible to the playgroup. This is engineering
hygiene that frees the next story author from having to ask "do I need
to maintain the legacy endpoint while I change save semantics?" The
answer becomes "no" once this lands. ADR-082's port-drift cleanup ends
when threads like this one are tied off.

## Technical Guardrails

### Files to delete and modify

**Delete from `sidequest-server/sidequest/server/rest.py` (verified):**

- Lines `283–363` — `@router.get("/api/saves", deprecated=True)` →
  `list_saves(request)`. Walks `save_dir/{genre}/{world}/{player}/save.db`,
  returns `{saves: [...]}`. Calls into `SqliteStore.open` for metadata.
- Lines `365–416` — `@router.post("/api/saves/new", deprecated=True)` →
  `create_save(request)`. Validates body, calls `db_path_for_session()`,
  initializes a fresh `GameSnapshot`. **Calls `db_path_for_session()` at
  `:392`.**
- Lines `418–462` — `@router.delete("/api/saves/{genre_slug}/{world_slug}/{player_name}", deprecated=True)`
  → `delete_save(...)`. Calls `db_path_for_session()` at `:435`, unlinks
  the file, attempts to clean parent dirs.

**Also delete from `rest.py`:**

- The module docstring lines `5–7` that advertise the three routes.
- The `db_path_for_session` import at `:31` (unused after the routes go).

**Delete from `sidequest-server/sidequest/game/persistence.py` (verified
at `:403–413`):**

```python
def db_path_for_session(
    save_dir: Path,
    genre_slug: str,
    world_slug: str,
    player_name: str,
) -> Path:
    """Compute the .db file path for a genre/world/player triple."""
    safe = "".join(...).lower() or "default"
    return save_dir / genre_slug / world_slug / safe / "save.db"
```

The replacement helper that **stays** is `db_path_for_slug()` at
`persistence.py:427–429`:

```python
def db_path_for_slug(save_dir: Path, slug: str) -> Path:
    """New slug-keyed DB path. One .db per game slug."""
    return save_dir / "games" / slug / "save.db"
```

This is the helper the surviving slug-connect path uses
(`session_handler.py:1334`). It is the canonical save-path helper post-MP-03.

### Non-test caller — legacy `_handle_connect` branch

`sidequest-server/sidequest/server/session_handler.py:62` imports
`db_path_for_session`; `:2094` calls it. The call lives inside the
legacy branch of `_handle_connect()` that runs from line ~2065 (after
the `payload.game_slug` happy path returns at ~2063) through the end
of the method around line ~2314. This branch:

- Reads `payload.genre`, `payload.world`, `payload.player_name`.
- Validates their presence (errors otherwise).
- Calls `db_path_for_session(self._save_dir, genre_slug, world_slug,
  player_name)`.
- Opens the SQLite store, loads or initializes a session, and falls
  through to chargen / replay / bootstrap broadcasts.

**The UI does not exercise this branch.** `App.tsx` (verified) sends
`game_slug` on every connect; the legacy `payload.genre/world/player_name`
shape is gone client-side. The branch is unreachable from production
traffic and exists only because the port-era cutover left it as a
fallback.

The clean-grep AC requires deleting this branch. The handler's body
shrinks from ~990 lines to ~735 lines (1320–~2065). The early-return at
`:2063` becomes the function's terminal path; the slug path becomes the
only path. Remove the `db_path_for_session` import at `:62` after the
branch is gone.

### Tests to delete and retarget

**Delete (legacy-route coverage, retargets to nothing):**

- `tests/server/test_rest.py:208–325` — every test in the `GET /api/saves`,
  `POST /api/saves/new`, and `DELETE /api/saves/...` blocks. The module
  docstring at `:3` advertises these routes; update it to reflect the
  remaining surface (`/api/genres`, `/api/sessions`, `/api/debug/state`).
- `tests/game/test_session_persistence.py:271–289` — three tests of the
  helper (`test_db_path_for_session`, `test_db_path_sanitizes_player_name`,
  `test_db_path_empty_player_name_becomes_default`). Delete the
  `db_path_for_session` import at `:18`. The slug-keyed helper
  `db_path_for_slug` already has its own coverage; if it does not,
  add one trivial test as compensating coverage.
- `tests/e2e/test_server_e2e.py:300–301` — two assertions that
  `/api/saves` and `/api/saves/new` are registered. Delete those two
  lines; the surrounding test still validates `/api/genres`,
  `/api/sessions`, `/ws`. Also at `:409–411` the test imports
  `db_path_for_session` and uses it to compute a save path
  (`test_e2e_npc_emit_via_real_handler` or similar). Retarget that
  call to `db_path_for_slug(saves_dir, "<some-slug>")` and update the
  test's setup to match the slug-keyed layout (`saves_dir / "games" / "<slug>" / "save.db"`).
  Confirm the test still drives the same NPC emit assertion.

**Search for any remaining call sites before merging:**

```
rg "db_path_for_session" sidequest-server sidequest-ui sidequest-daemon scripts
rg "/api/saves" sidequest-server sidequest-ui sidequest-daemon scripts docs
```

Both must return zero hits in production code. (Verified at story
authoring time: zero hits in `sidequest-daemon`, zero in `scripts`. The
only hits are in `sidequest-server` itself — the routes, the helper,
the `session_handler.py:62/2094` import + call, the test files listed
above, and the `docs/port-notes/game-phase1-slice.md` migration
manifest. The docs entry can stay as historical record or be updated;
not a release-blocker.)

### TDD shape — tests-before-deletion

The TDD framing for a deletion story is *negative-space tests*: write
tests that assert the absence of the deleted artifacts, watch them fail
red against the current code, then make them pass by deleting the code.

**Test 1 — route registration is empty.** New test in
`tests/server/test_rest.py` (or `tests/server/test_rest_legacy_removed.py`):

```python
def test_legacy_save_routes_are_not_registered(tmp_path):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    app = create_app(genre_pack_search_paths=[tmp_path], save_dir=saves_dir)
    route_paths = sorted(
        r.path for r in app.routes if hasattr(r, "path")
    )
    assert "/api/saves" not in route_paths
    assert "/api/saves/new" not in route_paths
    assert not any(p.startswith("/api/saves/") for p in route_paths)
```

Today this fails (the routes are registered). After deletion it passes.

**Test 2 — helper is gone.** New test in
`tests/game/test_session_persistence.py`:

```python
def test_legacy_db_path_for_session_helper_removed():
    import sidequest.game.persistence as p
    assert not hasattr(p, "db_path_for_session"), (
        "db_path_for_session was removed in 45-26 — use db_path_for_slug"
    )
```

Today this fails. After deletion it passes.

**Test 3 — wiring test (CLAUDE.md mandate).** The slug-connect happy
path must continue to work end-to-end after the legacy branch is
deleted. Either confirm an existing test drives the slug-connect path
(`tests/server/test_session_event_connect_slug.py` or equivalent — find
via `grep -l "game_slug" tests/server/`), or add one that:

- Spins up `create_app` with a save_dir.
- POSTs `/api/games` to mint a slug.
- Opens `/ws`, sends `SESSION_EVENT{event: "connect", game_slug: <slug>, player_name: "tester"}`.
- Asserts the server responds with the connected/bootstrap broadcast.

This is the wire-first integration test that proves the deletion
didn't kill the only surviving connect path. Without it, the
deletion-only PR could green-light a regression where the slug branch
was *also* broken and we wouldn't notice because the legacy branch
was masking it.

### What the OTEL story is, and isn't

This is a **deletion story**. No new spans. The routes being deleted
do not currently emit OTEL — they log warnings (`logger.warning(
"legacy GET /api/saves called — prefer POST /api/games")` at `:290`,
`:372`, `:429`). Those log lines disappear with the routes. No
GM-panel observability is lost.

### Daemon and other subrepos

Verified clean:

- `sidequest-daemon` — zero references to `/api/saves` or
  `db_path_for_session`. Daemon does not touch the save layer.
- `sidequest-ui` — zero references to `/api/saves` (UI uses
  `/api/games` and `/api/genres`). UI sends `game_slug` exclusively.
- `scripts/` — zero references.

The only consumer outside `sidequest-server` is the historical
`docs/port-notes/game-phase1-slice.md` migration manifest, which
mentions the helper as part of the original port slice. That file is
historical and can be left untouched (it documents what *was* ported;
the deletion is a later-epoch event).

## Scope Boundaries

**In scope:**

- Delete `list_saves`, `create_save`, `delete_save` route handlers in
  `rest.py` (lines 283–462).
- Delete the `db_path_for_session` import at `rest.py:31`.
- Delete the obsolete docstring lines at `rest.py:5–7`.
- Delete `db_path_for_session()` in `persistence.py` (lines 403–413).
- Delete the legacy genre+world+player branch in
  `session_handler.py:2065–~2314` and its
  `db_path_for_session` import at `:62`.
- Retarget `tests/e2e/test_server_e2e.py:409–411` from
  `db_path_for_session` to `db_path_for_slug`.
- Delete legacy-route tests in `tests/server/test_rest.py:208–325` and
  helper tests in `tests/game/test_session_persistence.py:271–289`.
- Add the three TDD negative-space + wiring tests described above.

**Out of scope:**

- Any change to save-load semantics. Saves continue to live at
  `~/.sidequest/saves/games/<slug>/save.db` (the existing slug-keyed
  layout). On-disk format and schema are unchanged.
- Any change to `db_path_for_slug()` (`persistence.py:427–429`),
  `SqliteStore`, `upsert_game`, `get_game`, or any other surviving
  persistence helper.
- Updating `docs/port-notes/game-phase1-slice.md` — historical
  document, leave alone.
- New routes or new save semantics. This is deletion-only.
- Migration of any on-disk legacy
  `<save_dir>/<genre>/<world>/<player>/save.db` files left over from
  the pre-MP-03 era — out of scope. If a user has these files on disk,
  they will become orphaned but not corrupted; a follow-up cleanup
  story can sweep them up if any playgroup member surfaces a complaint.

## AC Context

1. **Legacy `/api/saves/*` routes are removed from `rest.py`.**
   - Test: `test_legacy_save_routes_are_not_registered` (new).
     Asserts `/api/saves`, `/api/saves/new`, and any
     `/api/saves/*` path are absent from the registered route list of
     a freshly-created `app`.
   - Source-level: `grep -n "/api/saves" sidequest-server/sidequest/server/rest.py`
     returns nothing.

2. **Old `(genre, world, player)`-tuple save-path helper in
   `persistence.py` is removed.**
   - Test: `test_legacy_db_path_for_session_helper_removed` (new).
     Asserts `hasattr(sidequest.game.persistence, "db_path_for_session")`
     is False.
   - Source-level: `grep -n "db_path_for_session" sidequest-server/sidequest/game/persistence.py`
     returns nothing.

3. **No call sites remain (grep is clean).**
   - Verification commands (must run clean in PR description as
     evidence):
     ```
     rg "db_path_for_session" sidequest-server sidequest-ui sidequest-daemon scripts
     rg "/api/saves" sidequest-server sidequest-ui sidequest-daemon scripts
     ```
     Both must return zero hits in production code (the
     `docs/port-notes/...` historical file can be excluded with `--glob '!docs/**'`
     if it's left intact).
   - The legacy `_handle_connect` branch in `session_handler.py:2065–~2314`
     is also gone (it was the only non-test consumer of the helper).

4. **All existing tests pass; legacy-helper tests are deleted or
   retargeted.**
   - `tests/server/test_rest.py` legacy-route tests deleted (`:208–325`).
   - `tests/game/test_session_persistence.py` helper tests deleted
     (`:271–289`); import at `:18` removed.
   - `tests/e2e/test_server_e2e.py:300–301` route-registration
     assertions deleted; `:409–411` retargeted to `db_path_for_slug`.
   - `just server-check` passes.

5. **Slug-connect handshake is still wired (regression guard).**
   - Wire-first test (new or existing): drive the slug-connect WS
     path end-to-end against a real `create_app` instance and assert
     the server responds with the expected bootstrap. This guards
     against the deletion accidentally breaking the surviving
     connect path — which would otherwise be invisible because the
     legacy branch had been masking it.
