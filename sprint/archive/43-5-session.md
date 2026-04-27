---
story_id: "43-5"
jira_key: ""
epic: "43"
workflow: "trivial"
---
# Story 43-5: Daemon single-spawn + worker singleton — dedupe justfile recipes, delete vestigial ZImageMLXWorker.main(), enforce one-instance invariant

## Story Details
- **ID:** 43-5
- **Jira Key:** (personal project, not tracked)
- **Workflow:** trivial
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p3

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-27T17:30:27Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T00:00:00Z | 2026-04-27T17:24:11Z | 17h 24m |
| implement | 2026-04-27T17:24:11Z | 2026-04-27T17:24:12Z | 1s |
| review | 2026-04-27T17:24:12Z | 2026-04-27T17:30:27Z | 6m 15s |
| finish | 2026-04-27T17:30:27Z | - | - |

## Story Context

Two related daemon split-brains, folded into one cleanup pass per 2026-04-24 audit.

**(1) Justfile spawn dedup:** 
- `justfile:41-49` (`daemon` recipe, foreground)
- `justfile:74-77` (`up` recipe, background) 
- Both duplicate the daemon spawn command: `SIDEQUEST_GENRE_PACKS={{content}} uv run sidequest-renderer --warmup`
- Extract shared private recipe (e.g. `_daemon-cmd`) so flag changes update one place
- Verify `just daemon` and `just up` produce identical invocations

**(2) Worker singleton invariant:**
- Two model-load entry points exist in the daemon:
  - (A) In-process via `WorkerPool.warm_up_image()` at `sidequest_daemon/media/daemon.py:102-113` (production path, called by `_run_daemon` and `_ensure_image()`)
  - (B) Standalone subprocess via `ZImageMLXWorker.main()` at `sidequest_daemon/media/workers/zimage_mlx_worker.py:243-end` (vestigial — has its own JSON-line protocol loop, no callers, no console_script entry)
- Only path A runs because nothing invokes B, but the second `python -m sidequest_daemon.media.workers.zimage_mlx_worker` from any future script/recipe/unit file would load a second ZImage on the same MPS device
- Z-Image survives this; Flux would OOM the M3 Max instantly

### Actions

1. **Delete vestigial code from ZImageMLXWorker:**
   - Delete `ZImageMLXWorker.main()` function (~line 429)
   - Delete `_respond()` helper (~line 417)
   - Delete standalone JSON-line dispatch loop (everything from line ~230 to EOF)

2. **Add singleton guard to ZImageMLXWorker.__init__:**
   - Add class-level `_instance` ref
   - Raise `RuntimeError` on second construction in the same process
   - Fail loudly per CLAUDE.md "No Silent Fallbacks"
   - Document the invariant in the class docstring

3. **Collapse redundant guards:**
   - Remove or simplify `_ensure_loaded()` inside the worker
   - Keep one guard since `WorkerPool` is the only caller and already guards via `_image_loaded`

4. **Wiring tests (per daemon CLAUDE.md "Every Test Suite Needs a Wiring Test"):**
   - Assert that constructing a second `ZImageMLXWorker` in the same process raises
   - Grep-based test confirms `WorkerPool.warm_up_image()` is the only production caller of `load_model()`

### Acceptance Criteria

1. Justfile dedup complete — `_daemon-cmd` recipe created and used by both `daemon` and `up`
2. Both `just daemon` and `just up` produce identical daemon invocations
3. `ZImageMLXWorker.main()`, `_respond()`, and JSON-line loop deleted
4. Singleton guard added to `ZImageMLXWorker.__init__` with RuntimeError on second construction
5. `_ensure_loaded()` simplified (one guard, not three)
6. Wiring test passes: second ZImageMLXWorker construction raises RuntimeError
7. Grep test passes: WorkerPool.warm_up_image() is the only production caller of load_model()

## Sm Assessment

Trivial 2pt cleanup. Two coupled changes: justfile dedup (orchestrator) + worker singleton (daemon). Hand to Dev.

## Dev Assessment

**Phase:** finish
**Status:** Complete — 2 commits across 2 repos, all 12 worker tests pass, full daemon suite passes (1 pre-existing socket test failure unrelated).

**Implementation:**

*Daemon (commit 3cebe21, 3 files +161/−87):*
- `sidequest_daemon/media/workers/zimage_mlx_worker.py`:
  - Added class-level `_instance: ZImageMLXWorker | None = None` singleton handle.
  - `__init__` raises `RuntimeError` on second construction with named guidance to route through WorkerPool or reset for tests.
  - Removed `_ensure_loaded()` lazy-load helper; `warm_up()` and `render()` now `assert self.model is not None` per "No Silent Fallbacks".
  - `cleanup()` releases the singleton slot (`_instance = None`) so a fresh process or test fixture can construct.
  - Deleted vestigial `_respond()`, `main()`, JSON-line dispatch loop, and `if __name__ == "__main__"` trailer (~80 lines).
  - Dropped now-unused `import json` and `import sys`.
  - Updated class docstring to document the per-process invariant.
- `tests/conftest.py` (new): autouse fixture resets `ZImageMLXWorker._instance` before/after every test in the suite so per-file fixtures don't leak the singleton across files.
- `tests/test_zimage_mlx_worker.py`:
  - Added `Generator` + `re` imports for new tests + autouse cleanup.
  - Added local autouse fixture (now redundant with conftest, kept for explicit per-test reset).
  - New `TestSingletonInvariant` class with `test_second_construction_raises` and `test_cleanup_releases_singleton_slot`.
  - New `test_load_model_only_called_by_workerpool` — greps daemon production tree for `_image.load_model(` callers and asserts only `media/daemon.py` (`WorkerPool.warm_up_image`) holds an entry point.

*Orchestrator (commit 102452c, 1 file +13/−8):*
- `justfile`: extracted shared private `_daemon-cmd *flags` recipe; `daemon` recipe (foreground tee) and `up` recipe (background redirect) now both call it. A flag change updates one place. Verified `just --show daemon` and `just --show up` parse cleanly; `_daemon-cmd` is hidden from `just --list` per just's underscore convention.

**Test verification:**
- `uv run pytest tests/test_zimage_mlx_worker.py -v` → 12 passed (was 9; +3 new tests for singleton + wiring).
- `uv run pytest` (full daemon suite) → 226 passed, 1 pre-existing failure (`test_daemon_smoke.py::test_daemon_ping` — needs live daemon socket; verified pre-existing on develop via `git stash` round-trip).
- `just --show daemon` / `just --show up` / `just --show _daemon-cmd` all parse and expand correctly.

**AC checklist:**
1. ✓ `_daemon-cmd` private recipe extracted; both `daemon` and `up` call it.
2. ✓ `ZImageMLXWorker.main()`, `_respond()`, JSON-line dispatch loop deleted.
3. ✓ Class-level `_instance` singleton handle in `__init__` raises `RuntimeError` on second construction.
4. ✓ Class docstring documents the per-process invariant.
5. ✓ `_ensure_loaded()` removed; assertions added to `warm_up`/`render`.
6. ✓ `test_second_construction_raises` passes.
7. ✓ `test_load_model_only_called_by_workerpool` passes.

**Branches:**
- `sidequest-daemon`: `feat/43-5-daemon-singleton-and-justfile-dedup` (1 commit).
- `orchestrator`: `feat/43-5-daemon-singleton-and-justfile-dedup` (1 commit).

**Handoff:** To Reviewer.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 12/12 worker tests pass; pre-existing lint + pre-existing justfile-fmt style note (none in diff) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 4 (1 medium duplicate fixture, 3 high: narrow regex, tautological assert, missing contract tests) | confirmed 4 (all fixed) |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 (1 medium memory claim, 3 high: docstring "import or", "silently load", `_image_worker` regex doc) | confirmed 4 (all fixed) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 (high: `assert` stripped under `-O`, vestigial dup assert, narrow regex, spurious `# type: ignore`) | confirmed 4 (all fixed) |

**All received:** Yes (4 active, 5 skipped per settings)
**Total findings:** 8 distinct issues across 3 subagents (several corroborated each other); all 8 fixed in-flight; 0 dismissed; 0 deferred.

### Confirmed and fixed during review (amended commit 3cebe21 → revised)

**The contract pattern (rule-checker §3 + §4 + test-analyzer §4):** The single most consequential finding. Two subagents independently noted that `assert self.model is not None` in `warm_up()` and `render()` would be stripped by Python `-O` (optimized mode), turning the intended fail-loud contract check into a silent `AttributeError: 'NoneType' object has no attribute 'generate_image'`. Per the project's "No Silent Fallbacks" principle, both checks now use `if self.model is None: raise RuntimeError(...)`. The vestigial bare `assert self.model is not None` inside the `warm_up()` OTEL span (a holdover from before `_ensure_loaded()` removal, rule-checker §4) is gone. Tests `test_warm_up_without_load_model_raises` and `test_render_without_load_model_raises` exercise both new RuntimeError paths.

**Wiring grep narrowness (test-analyzer §2 + comment-analyzer §4 + rule-checker §2):** The original regex `\b(?:_image|_image_worker)\.load_model\(` only matched two specific variable names; future callers using any other binding (`worker.`, `img.`, `pool._image.`) would silently pass. `_image_worker` was also a dead alternative (no such attribute exists). Replaced with `\.load_model\(` (catches any call site) plus a `def load_model` exclusion to skip declarations, plus a `_ALLOWED_LOAD_MODEL_CALLER` Path constant resolved exactly (no name/substring shortcut that future sibling files could match accidentally). The test now genuinely guards the wiring invariant.

**Tautological assertion (test-analyzer §3):** `assert second is not first` could not fail. Replaced with `assert ZImageMLXWorker._instance is second`, which actually verifies `__init__` reinstalls the singleton slot.

**Duplicate singleton-reset fixture (test-analyzer §1):** Removed the in-file autouse fixture; conftest's `_reset_zimage_singleton` already covers both sides. The `worker` fixture's redundant `_instance = None` assignment was also dropped (replaced with a comment pointing to conftest).

**Spurious `# type: ignore[name-defined]` (rule-checker §1):** The string-literal annotation + ignore was unnecessary because `Generator` is imported unconditionally. Removed along with the redundant fixture.

**Doc accuracy (comment-analyzer §1, §2, §3):** Class docstring's "(~10GB)" memory claim about Z-Image is unverified — dropped. Conftest fixture docstring said "at import or fixture-build time" — corrected; importing the module doesn't construct an instance, only `ZImageMLXWorker(...)` does. Wiring test docstring said "silently load a second model" but the singleton guard now makes that loud — reworded to focus on bypass of guard + idempotency.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `WorkerPool.warm_up_image()` (`media/daemon.py:152`) → guards via `_image_loaded` → calls `self._image.load_model()` (canonical entry point) → `self._image.warm_up()` → sets `_image_loaded = True`. The wiring grep test asserts `media/daemon.py` is the only file in the daemon production tree containing a `.load_model(` call. Render path: `WorkerPool._ensure_image()` → `warm_up_image()` if cold → `self._image.render(params)`. Worker's internal `__init__` singleton guard prevents any code path that constructs a second `ZImageMLXWorker` from succeeding silently.

**Pattern observed:** Singleton-via-class-level-`_instance` with `cleanup()` releasing the slot is straightforward Python, properly fail-loud per CLAUDE.md. The conftest autouse fixture handles cross-file test interaction cleanly. Justfile dedup uses `_daemon-cmd` private recipe (just convention) so both `daemon` and `up` callers share one source of truth without sacrificing their distinct output redirection.

**Error handling:** `RuntimeError` raised on (a) second worker construction, (b) `warm_up()` before `load_model()`, (c) `render()` before `load_model()`. All three paths covered by tests. `cleanup()` is idempotent — releases the slot regardless of model load state.

### Findings table

All 8 findings from the review pass were confirmed and fixed in-flight. No remaining Critical or High severity findings.

| Severity | Issue | Location | Status |
|----------|-------|----------|--------|
| `[HIGH] [RULE]` | `assert` stripped by Python `-O` — silent contract violation under optimization. | `zimage_mlx_worker.py:300, 357 (pre-amend)` | Fixed: replaced with `if/raise RuntimeError`. |
| `[HIGH] [RULE]` | Vestigial bare `assert self.model is not None` inside `warm_up` OTEL span. | `zimage_mlx_worker.py:308 (pre-amend)` | Fixed: deleted. |
| `[HIGH] [TEST] [RULE]` | Wiring grep regex too narrow (`_image|_image_worker` only); presents false-completeness. | `test_zimage_mlx_worker.py:208 (pre-amend)` | Fixed: broadened to `\.load_model\(` with `def` exclusion + Path-equal allowlist. |
| `[HIGH] [TEST]` | No tests for the new RuntimeError paths in `warm_up`/`render` when model is None. | `test_zimage_mlx_worker.py` | Fixed: added `TestPreLoadContract` with two tests exercising both paths. |
| `[HIGH] [TEST]` | `assert second is not first` is tautological. | `test_zimage_mlx_worker.py:186 (pre-amend)` | Fixed: replaced with `_instance is second` assertion. |
| `[HIGH] [DOC]` | Conftest docstring claimed singleton trips "at import" — imports don't construct. | `tests/conftest.py:19 (pre-amend)` | Fixed: corrected to "at fixture-build time" with parenthetical. |
| `[HIGH] [DOC]` | Wiring test docstring said "silently load a second model" but singleton guard makes it loud. | `test_zimage_mlx_worker.py:204 (pre-amend)` | Fixed: docstring rewritten to focus on bypass-of-guard. |
| `[MEDIUM] [TYPE]` | Spurious `# type: ignore[name-defined]` since `Generator` is imported. | `test_zimage_mlx_worker.py:32 (pre-amend)` | Fixed: redundant fixture removed entirely. |
| `[MEDIUM] [TEST]` | Duplicate singleton-reset fixture (conftest + in-file + manual). | `test_zimage_mlx_worker.py:31 (pre-amend)` | Fixed: in-file fixture removed; manual reset in `worker` fixture removed. |
| `[MEDIUM] [DOC]` | Class docstring's "(~10GB)" Z-Image memory claim unverified. | `zimage_mlx_worker.py:204 (pre-amend)` | Fixed: parenthetical dropped. |

### Rule Compliance

Rule-checker enumerated 13 lang-review rules (31 instances) plus 5 CLAUDE.md additional rules. After in-flight fixes: zero remaining violations. Both contract checks (`warm_up`/`render` pre-load) now use `if/raise RuntimeError` per "No Silent Fallbacks". Wiring test now provides genuine cross-caller coverage rather than name-bound coverage. The new singleton invariant + test trio (`test_second_construction_raises` + `test_cleanup_releases_singleton_slot` + `test_warm_up_without_load_model_raises` + `test_render_without_load_model_raises` + `test_load_model_only_called_by_workerpool`) collectively satisfies "Every Test Suite Needs a Wiring Test" for both layers (singleton guard + caller-contract enforcement + production-tree caller invariant).

### Devil's Advocate

The biggest open argument against this diff is now the singleton guard's process-locality. A class-level `_instance` survives across imports within one Python process but does *nothing* if a future script spawns a second daemon process and each loads its own model. Counter: the story explicitly scopes the invariant to "per-process" — multi-process is a separate concern handled at the systemd / launchctl / WorkerPool-spawning layer, not the worker class. Two: `cleanup()` clearing `_instance` could in principle race with another thread constructing a worker (read-then-write on `_instance`). Counter: the worker is single-threaded by design (Z-Image renders are serialized through WorkerPool), and Python's GIL serializes attribute access at this granularity; cross-thread construction of image workers isn't a real scenario. Three: the new wiring grep would falsely flag a future legitimate utility script (e.g., a CLI that loads the model standalone for benchmarking). Counter: that's the desired forcing function — any new entry point should explicitly route through WorkerPool or get added to the allowlist with deliberate justification. Four: deleting `_ensure_loaded()` removed a graceful-recovery path. Callers that violated the contract used to silently work; now they raise loudly. Counter: that's the entire point of the change — silent recovery hid bugs that the noisy raise will surface immediately. Five: the justfile dedup's `just _daemon-cmd` invocation from inside `up`'s background subshell adds a small startup overhead (a second `just` parse + recipe lookup). Counter: ~5–10ms vs the daemon's multi-second model warmup is negligible, and the maintenance benefit (one source of truth for the spawn) is the right tradeoff. Diff ships.

**Handoff:** To Vizzini (SM) for finish.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->