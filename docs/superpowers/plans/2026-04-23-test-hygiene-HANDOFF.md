# Handoff — 2026-04-23 test hygiene + audio DJ wiring (paused)

**For next session.** Read this first, then read `.pennyfarthing/sidecars/dev-gotchas.md` → the "Python server test hygiene" section, which carries the durable lessons.

## One-line state

`sidequest-server` is on branch `feat/audio-dj-wiring` with 9 commits ahead of `develop`. Audio DJ plan is 3/5 tasks complete (through Task 3). Mid-plan we pivoted into a test-speed investigation because the suite was taking 6+ minutes per run. Daemon leak + fixture-pack retrofit landed. `ClaudeClient` leak is **not yet fixed** — that's the next action.

## The one thing blocking everything

**Real `claude -p` subprocesses spawn inside `_execute_narration_turn` via `LocalDM.decompose`.** Also `Orchestrator.run_narration_turn` when not mocked. Every server test that reaches `_handle_player_action` spawns real Claude by default. Caught in the act via `ps aux | grep claude` during the last pytest run — a `claude --model haiku` subprocess with the full DispatchPackage system prompt was running.

Fix: autouse conftest fixture that monkeypatches `ClaudeClient` at **all three import sites** (because `from X import Y` creates fresh per-module bindings):

```python
monkeypatch.setattr("sidequest.agents.orchestrator.ClaudeClient", _FakeClaudeClient)
monkeypatch.setattr("sidequest.agents.local_dm.ClaudeClient", _FakeClaudeClient)
monkeypatch.setattr("sidequest.server.session_handler.ClaudeClient", _FakeClaudeClient)
```

`_FakeClaudeClient` needs:
- `async def send_with_session(prompt, model, session_id, system_prompt, allowed_tools, env_vars) -> ClaudeResponse` — returns canned text with a valid JSON DispatchPackage body for LocalDM, canned narration + `game_patch` fence for Orchestrator. Dispatch by `model` arg or by inspecting `system_prompt` prefix.
- `async def send(...)` — similar.

With the daemon autouse guard and the ClaudeClient autouse guard together, the full server suite should run in seconds, not minutes. Verify by running `uv run pytest tests/server/test_event_log_wiring.py -v --durations=10` — it currently passes in **33 seconds** because LocalDM spawns real `claude -p`; after the guard it should be sub-second.

## Hard performance rule (locked this session)

- **30 seconds is the ceiling for the full Python server suite.** Python side is text munging — pydantic, JSON, YAML, SQLite, OTEL spans. No ML inference. If the number exceeds 30s, the right response is "look again" — diagnose a real-service leak, don't defend it. `ps aux | grep claude` and `lsof /tmp/sidequest-renderer.sock` catch the leaks in the act. TDD runs the suite 4-8 times per story; every minute over budget compounds into hours of dead wall time per workflow.

## What committed on `feat/audio-dj-wiring`

```
47fe3a8 test(fixtures): retrofit fixture pack across server tests
afc9dba test(server): drop TestClient from test_solo_single_slot
f547e6c test(server): drop TestClient from test_seat_claim
2869591 test(server): drop FastAPI TestClient from test_session_room_wired
305a49c test(fixtures): add frozen test_genre pack copied from mutant_wasteland
0a8c5cd test(server): autouse guard blocks DaemonClient
80d4500 feat(session): wire per-session LibraryBackend at connect     [Task 3]
465ed61 refactor(audio): build_audio_cue_payload returns AudioCuePayload  [Task 2]
6b17e7c feat(protocol): add AudioCuePayload + AudioCueMessage wire types  [Task 1]
```

Untracked-but-committed-in-spirit: `sidequest/audio/`, `sidequest/media/`, `sidequest/renderer/` exist in the working tree of every workspace that cloned this repo earlier but are NOT tracked on `feat/audio-dj-wiring` — they were lifted into place in an earlier session without being added to git. Task 1 and Task 2 commits reference them via `from sidequest.audio.*` imports; a fresh clone of the branch will fail imports. **Needs an infrastructure commit to stage those three directories.** Safe to `git add sidequest/audio sidequest/media sidequest/renderer` and commit as `feat(server): commit lifted audio/media/renderer modules` before anything else on a fresh clone.

## Audio DJ plan state

**Spec:** `docs/superpowers/specs/2026-04-23-audio-dj-wiring-design.md`
**Plan:** `docs/superpowers/plans/2026-04-23-audio-dj-wiring.md`

| Task | Status | Commit |
|---|---|---|
| 1. AudioCuePayload + AudioCueMessage protocol types | ✓ done (reviewed, quality-reviewed) | 6b17e7c |
| 2. build_audio_cue_payload returns AudioCuePayload | ✓ done (reviewed, quality-reviewed) | 465ed61 |
| 3. Per-session LibraryBackend wired at connect | ✓ done (subagent hung 40 min — turned out to be the slow-test issue, not the subagent; work was right) | 80d4500 |
| 4. `_maybe_dispatch_audio` at turn end | pending — not started | |
| 5. End-to-end wiring test for AUDIO_CUE emission | pending | |

**Task 4 next steps** (from the plan, steps are fully written out — just execute):
- Add `_AUDIO_INTERPRETER = AudioInterpreter()` module-level singleton.
- Add `_maybe_dispatch_audio`, `_audio_skip`, `_audio_dispatched` methods on `WebSocketSessionHandler`.
- Call from turn-end outbound assembly (parallel to `_maybe_dispatch_render`).
- Extend `tests/server/test_audio_dispatch.py` with 5 dispatcher tests.

## Test hygiene — what's done, what's left

### Done this session
1. **Daemon guard** — autouse conftest fixture replaces `DaemonClient` at both import sites (`session_handler.DaemonClient`, `lore_embedding.DaemonClient`) with `_UnavailableDaemonClient` whose `is_available() -> False`. Commit 0a8c5cd.
2. **Fixture genre pack** — `tests/fixtures/packs/test_genre/` (frozen copy of `mutant_wasteland`, 1 world, binaries stripped, loads in 128ms). Symlinks for every real slug (`caverns_and_claudes`, `elemental_harmony`, `heavy_metal`, `low_fantasy`, `neon_dystopia`, `space_opera`, `spaghetti_western`). Commit 305a49c.
3. **Fixture pack search path autouse** — conftest monkeypatches `sidequest.genre.loader.DEFAULT_GENRE_PACK_SEARCH_PATHS` to `[_FIXTURE_PACKS_DIR]`. ⚠ **Known issue:** `session_handler.py` does `from sidequest.genre.loader import DEFAULT_GENRE_PACK_SEARCH_PATHS` — creates its own binding, monkeypatch doesn't propagate. Tests that construct `WebSocketSessionHandler` without passing `genre_pack_search_paths` still use the original default. Either (a) also patch `sidequest.server.session_handler.DEFAULT_GENRE_PACK_SEARCH_PATHS`, or (b) refactor session_handler to read via module attribute. Commit 47fe3a8.
4. **FastAPI removed from 4 tests** — `test_session_room_wired.py`, `test_seat_claim.py`, `test_solo_single_slot.py`, `test_event_log_wiring.py`. All now drive `WebSocketSessionHandler.handle_message(msg)` directly with a fake `asyncio.Queue` out_queue. Each runs in 0.15s **except test_event_log_wiring (33s because ClaudeClient not yet mocked)**.

### Left — FastAPI removal

Per audit, 10 of the 15 server tests using `create_app()+TestClient+websocket_connect` don't need FastAPI. 4 done, 6 remaining:

| File | Pattern | Notes |
|---|---|---|
| `test_event_replay_on_reconnect.py` | direct-handler | single-socket, uses EventLog replay path |
| `test_sync_wiring.py` | two-socket direct-handler | share `RoomRegistry`, inject queue per handler |
| `test_pause_on_drop.py` | two-socket direct-handler | uses `room.detach_outbound` + `disconnect` |
| `test_party_wiring.py` | two-socket direct-handler | drop→pause→reconnect→resume |
| `test_presence_broadcast.py` | two-socket direct-handler | alice joins → bob joins → alice receives PLAYER_PRESENCE |
| `test_slug_wiring.py` | direct-handler | seed slug directly via `upsert_game()`, drop the REST POST |
| `test_server_e2e.py` | direct-handler (8 tests, 420 lines) | biggest; mocks GenreLoader + ClaudeClient already |
| `test_websocket.py` | **partial** — keep TestClient only for malformed-JSON framing test |

### Keep TestClient (but apply `app.dependency_overrides`)

- `test_rest.py` — actual HTTP endpoints (GET /api/genres, /api/saves, DELETE, CORS)
- `test_games_endpoints.py` — already does it right (bare `FastAPI()` + REST router mount, no `create_app()` bloat). Reference pattern for the others.
- `tests/smoke/test_skeleton_starts.py` — verifies `create_app()` constructs and `/health` responds

For these, use `app.dependency_overrides` to inject mocks for heavy dependencies (genre loader, Claude factory). Reference: https://fastapi.tiangolo.com/advanced/testing-dependencies/

### Genre pack caching

290 tests × 128ms fixture load = 37s just in pack loading. Exceeds the 30s budget by itself. Fix:

- Option A: `load_genre_pack_cached` (exists in `sidequest/genre/loader.py`) — make it the default path in the GenreLoader used by tests. Process-lifetime module-level cache already present.
- Option B: session-scoped pytest fixture that loads the pack once and exposes it to every test.

Option A is less invasive.

### test_chargen_e2e.py (separate decision)

Per audit, this is a deliberate integration canary — "no mocked genre pack, no mocked session handler." With the fixture pack retrofit, it now loads the fixture (128ms) instead of `caverns_and_claudes`/`elemental_harmony`, so it should be fast. Decision point: keep as the one opt-in real-content test, or retire in favor of the fixture-backed slice. **Default: keep.**

## Durable lessons → sidecar

`.pennyfarthing/sidecars/dev-gotchas.md` → "Python server test hygiene (2026-04-23 incident — the full-session disaster)" section captures:

- First ask wins (Keith asked about Claude subprocesses on the first pushback; I ignored it for an hour)
- Keith's questions are never curiosity — they're steers, diagnoses, or directives
- Full real-service audit: ClaudeClient (twice per turn via Orchestrator + LocalDM), DaemonClient (180s timeout), real genre pack loading
- `from X import Y` breaks monkeypatching — patch at the import site
- FastAPI is transport; `handle_message()` return value IS the test
- `app.dependency_overrides` is the right tool for the few legit TestClient uses
- Don't run slow tests to diagnose slow tests — READ THE CODE (ps aux, lsof, grep)
- 30s ceiling on the full server suite; above that = look again, don't defend
- Diagnostic pytest needs full output (`-v --durations=20`), never `-q | tail`

## Next-session first steps, in order

1. Read `.pennyfarthing/sidecars/dev-gotchas.md` → "Python server test hygiene" section.
2. On `feat/audio-dj-wiring`, commit the three untracked module dirs (`sidequest/audio`, `sidequest/media`, `sidequest/renderer`) as an infrastructure commit so Task 1 and Task 2 commits actually build on a fresh clone.
3. Write the `_FakeClaudeClient` + autouse fixture in `tests/server/conftest.py`. Patch all three import sites.
4. Run `uv run pytest tests/server/test_event_log_wiring.py -v --durations=10` — expect sub-second.
5. Run the full server suite with `-v --durations=30`. Target: under 30s total.
6. If still >30s, grep durations for outliers and investigate each one specifically (no more full-suite re-runs).
7. Once suite is fast, do the remaining 6 FastAPI removals (straightforward pattern, copy from the four already done).
8. Once tests are clean, resume the audio DJ plan at Task 4.

## What not to do next session

- Don't spawn more research/retrofit subagents on the same files concurrently — the fixture retrofit agent was independent, but adding more would create conflicts.
- Don't rerun the full suite as a first diagnostic step. Grep the code for real-service call sites first.
- Don't use `-q | tail` during diagnosis. Verbose output always.
- Don't say "follow-up work" or "separate pass" about anything test-hygiene-related. If it's slow, it's in scope now.
