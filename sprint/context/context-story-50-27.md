---
parent: context-epic-50.md
---

# Story 50-27: Parallelize pytest with pytest-xdist

## Business Context

The sidequest-server unit suite (~7,440 tests after the caverns_sunden skip block applied in `tests/conftest.py`) walks serially in 5–6 minutes on Keith's 10-core ARM Mac. Per-test runtime is already fine — median ~5–20 ms, slowest ~0.5 s on intentional timeout tests. The bottleneck is purely cardinality × serial execution. Dropping the wall-clock to ~1 minute by sharding across cores with pytest-xdist is the goal.

This surfaced during 50-9 GREEN phase (2026-05-21): the testing-runner reported "stuck at 81%" — investigation showed the suite was progressing normally, just large. Keith's directive: *"tests should be fast"* + *"we aren't doing rocket surgery here when the LLM is not involved."* Per-test speed already meets that bar; this story closes the wall-clock gap that comes from suite size alone.

## Current State (Codebase Survey, 2026-05-21)

### Test infrastructure

| Surface | Current state | After 50-27 |
|---------|---------------|-------------|
| `sidequest-server/pyproject.toml` dev deps | `pytest`, `pytest-asyncio`, `pytest-timeout`, `ruff`, `pyright`, `httpx` | + `pytest-xdist` |
| `[tool.pytest.ini_options].addopts` | `--ignore=tests/e2e --timeout=30 --timeout-method=thread` | + `-n auto` (default parallel) |
| `justfile` `server-test` recipe | `uv run pytest -v` | inherits `-n auto` from addopts (or explicit) |
| `.pennyfarthing/repos.yaml` `server.test_command` | `pytest` | bare `pytest` is fine — picks up addopts |
| Conftests | `tests/conftest.py` + 9 subdirectory conftests | unchanged unless isolation fix required |

### Singleton / shared-state inventory

The story's "known risks" list cited four potential collision surfaces. Survey results:

1. **OTEL `init_tracer()` singleton** — `sidequest/telemetry/setup.py:31` uses a **module-level `_initialized` bool** that sets the global TracerProvider. Under pytest-xdist each worker is a separate Python process — each worker gets its own `_initialized` and its own provider. **Per-process isolation is automatic; no fixture refactor required.** The existing `initialized_tracer` fixture in `tests/conftest.py:38` and the explicit `init_tracer()` calls scattered through smoke/magic/integration tests will all continue to work.

2. **SQLite saves at `~/.sidequest/saves/`** — `tests/conftest.py:30` already provides `tmp_save_dir` built on pytest's `tmp_path`, which xdist scopes per-worker. The remaining read-only references to real saves live in `tests/integration/` (test_glenross_replay_*.py, test_dual_track_dungeon_survivor.py) which the story's non-goals explicitly **exclude from parallelization**. SQLite supports concurrent readers, but parallelizing those tests is out of scope.

3. **Daemon Unix socket at `/tmp/sidequest-renderer.sock`** — `tests/server/conftest.py:19` explicitly states *"No server test ever talks to the real /tmp/sidequest-renderer.sock"*; tests stub the socket. **No collision surface.**

4. **Module-level paths in production code** that tests could indirectly hit:
   - `sidequest/corpus/writer.py:10` `_SAVE_ROOT = Path.home() / ".sidequest" / "saves"` — module-level constant. `tests/corpus/test_writer.py:61` already monkey-patches via `fake_home` to prevent real-save clobber.
   - `sidequest/server/render_diagnostics.py:52` — writes to `~/.sidequest/diagnostics/`. Check if any unit test triggers this without monkey-patching `Path.home()`.
   - `sidequest/game/monster_manual.py:114` — writes to `~/.sidequest/manuals/{genre}_{world}.json`. Same check.
   - `sidequest/genre/loader.py:79` — read-only lookup root. Fine.

### Scope clarification on AC-4

The story's AC-4 ("Any fixture refactored for worker isolation is annotated with a comment naming the global state it isolates from") only applies if a fixture is *changed* to add isolation. From the survey, fixture refactors may be needed for `render_diagnostics` or `monster_manual` write paths if any unit test hits them; otherwise the existing fixture set is already xdist-safe and no annotation work is required.

## Test Plan (TDD Red-to-Green)

### Red Phase Tests (this story)

All RED tests live in **`sidequest-server/tests/infrastructure/test_pytest_xdist_setup.py`** — new directory `tests/infrastructure/` is being introduced for cross-cutting test-infrastructure assertions. Each test maps to an AC or wiring obligation.

**1. `test_pytest_xdist_in_dev_dependencies`** — reads `pyproject.toml` and asserts `pytest-xdist` appears in `[project.optional-dependencies].dev`. Fails today.

**2. `test_pytest_xdist_module_importable`** — uses `importlib.util.find_spec("xdist")` (avoids hard-import that would break collection if missing). Fails today. Wiring-test: proves `uv sync` actually ran after the dep was added.

**3. `test_pytest_addopts_engages_parallel_mode`** — reads `[tool.pytest.ini_options].addopts` and asserts it contains `-n` followed by `auto` (or a numeric worker count). Fails today.

**4. `test_orchestrator_justfile_server_test_recipe_parallel`** — reads orchestrator `justfile` and asserts the `server-test` recipe either explicitly contains `-n` OR is a bare `pytest` call (relying on addopts inheritance — the `-v` flag is fine). Fails today.

**5. `test_pf_check_server_invokes_parallel_unit_suite`** — reads `.pennyfarthing/repos.yaml` and asserts either `server.test_command` contains `-n`, OR the addopts in pyproject does. (One of the two ramps must be lit; both is fine.) Fails today.

**6. `test_tmp_save_dir_fixture_isolated_from_real_home`** *(regression guard, passes today)* — instantiates the `tmp_save_dir` fixture and asserts the returned path is NOT under `Path.home() / ".sidequest"`. Documents the existing isolation contract; future refactor that breaks it would fail this test.

### Acceptance Criteria (from session)

- **AC-1:** Full unit suite (`tests/` minus `tests/integration/`, `tests/e2e/`) under 90 s with `-n auto`. *Verified by testing-runner during VERIFY phase.*
- **AC-2:** No regressions under `-n auto`. *Verified by testing-runner pass/fail count.*
- **AC-3:** `just server-test` and `pf check` invoke parallel mode by default. *Tested in RED #4 and #5.*
- **AC-4:** Fixture refactor annotations. *Enforced by review — TEA writes no test, since "refactored for isolation" depends on what Dev actually changes. If Dev changes a fixture, Reviewer checks for the comment.*
- **AC-5:** Story 50-9 verify-loop under 90 s after this lands. *Verified by re-running 50-9's check after merge.*

### Documented opt-out (per AC-3)

Devs needing serial execution for debugging (single-threaded breakpoints, race-condition isolation) can run `uv run pytest -n0 -v` to override addopts. This should be documented in `sidequest-server/CLAUDE.md` under build commands.

## Non-Goals (from session)

- Parallelize `tests/integration/` — separate audit required, more shared state.
- Change individual test logic to enable parallelism — fix the **fixture**, not the test.
- Raise the per-test 30 s timeout — it's a leak-catcher and stays.

## File Inventory

### Server (sidequest-server)

| File | Role | Change |
|------|------|--------|
| `pyproject.toml` | Dev dependencies + pytest config | + pytest-xdist dep, + `-n auto` in addopts |
| `tests/infrastructure/test_pytest_xdist_setup.py` | RED tests for this story | NEW |
| `tests/conftest.py` | Shared fixtures | Touch only if survey finds a hidden collision |
| `tests/server/conftest.py`, `tests/integration/conftest.py`, others | Subdir fixtures | Touch only if survey finds a hidden collision |
| `uv.lock` | Lockfile | Regenerated by `uv sync` |

### Orchestrator (this repo)

| File | Role | Change |
|------|------|--------|
| `justfile` | `server-test` recipe at line 260 | Inherits addopts (no edit) OR explicit `-n auto` |
| `.pennyfarthing/repos.yaml` | `server.test_command` | Stays `pytest` (addopts carries `-n auto`) |

## Outstanding Questions

1. **Will `--timeout-method=thread` interact badly with xdist workers?** pytest-timeout's thread method spawns a daemon thread per test; xdist workers are separate processes, so each worker still uses its own thread pool. Should be fine, but a smoke run will confirm.
2. **Does `tests/scripts/` or `tests/smoke/` have any per-suite ordering requirements?** Unlikely — smoke tests are idempotent — but a parallel run may reorder enough to expose latent ordering bugs in test fixtures.
3. **Will `tests/server/test_recurring_npc_presence.py` and other long-running tests dominate one worker?** xdist's `--dist loadfile` keeps tests in the same file on one worker; the default `--dist load` round-robins. A `--dist loadfile` choice may reduce per-test setup overhead for test classes that share expensive fixtures.

## References

- **Story 50-9 surfacing context:** `sprint/archive/50-9-session.md` (the "stuck at 81%" investigation).
- **pytest-xdist docs:** distribution modes (`load`, `loadfile`, `loadscope`), `worker_id` fixture, `--tx popen` transport.
- **CLAUDE.md:** "Every Test Suite Needs a Wiring Test" — the addopts/justfile/repos.yaml triad here IS the wiring test.
