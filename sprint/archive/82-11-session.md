---
story_id: "82-11"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 82-11: Parse SIDEQUEST_NARRATOR_ITERATION_CAP once at startup, not per-turn (82-9 follow-up; narrator.py:86 + orchestrator.py:4125)

## Story Details
- **ID:** 82-11
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none

## Branch
- **Repository:** sidequest-server
- **Strategy:** gitflow (feat/82-11-iteration-cap-parse-once)
- **Base:** develop

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-05T21:19:43Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T21:03:59Z | 2026-06-05T21:05:34Z | 1m 35s |
| implement | 2026-06-05T21:05:34Z | 2026-06-05T21:10:20Z | 4m 46s |
| review | 2026-06-05T21:10:20Z | 2026-06-05T21:19:43Z | 9m 23s |
| finish | 2026-06-05T21:19:43Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): The `_clear_iteration_cap_cache` autouse fixture is file-local; three specialists (edge-hunter, silent-failure-hunter, test-analyzer) independently flagged that a future test file exercising the SDK narration path with the env set would not inherit the isolation guarantee under pytest-xdist shared workers. Latent today (grep confirms no other file sets `SIDEQUEST_NARRATOR_ITERATION_CAP`; legacy-path narration tests never reach the resolver). Affects `sidequest-server/tests/agents/conftest.py` (add a global autouse `resolve_narrator_iteration_cap.cache_clear()` fixture, or move the file-local one there). *Found by Reviewer during code review.*
- **Question** (non-blocking): An operator who exports `SIDEQUEST_NARRATOR_ITERATION_CAP=` (empty string, e.g. a blank .env line) gets a per-turn ValueError rather than "unset" — pre-existing behavior, arguably correct per No Silent Fallbacks (empty-as-unset would BE a silent fallback), but untested either way. Affects `sidequest-server/tests/agents/test_narrator_iteration_cap_toggle.py` (one parametrized case pinning empty-string → raise as intentional). *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** 1 findings (0 Gap, 0 Conflict, 1 Question, 0 Improvement)
**Blocking:** None

- **Question:** An operator who exports `SIDEQUEST_NARRATOR_ITERATION_CAP=` (empty string, e.g. a blank .env line) gets a per-turn ValueError rather than "unset" — pre-existing behavior, arguably correct per No Silent Fallbacks (empty-as-unset would BE a silent fallback), but untested either way. Affects `sidequest-server/tests/agents/test_narrator_iteration_cap_toggle.py`.

### Downstream Effects

- **`sidequest-server/tests/agents`** — 1 finding

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. (Story offered two acceptable resolutions — memoize OR document per-turn re-read as intentional; chose memoization via `functools.cache`, which is squarely within AC1's "startup or first-use memoization" wording, not a deviation.) → ✓ ACCEPTED by Reviewer: agrees with author reasoning — AC1 explicitly names "first-use memoization" as an accepted resolution; `functools.cache` is the minimal stdlib mechanism for it, and the docstring documents the contract (boot-fixed env, cache_clear seam, exceptions-not-cached).

### Reviewer (audit)
- No undocumented deviations found. The diff is exactly the AC1 memoization + AC2 test coverage; the orchestrator call site is untouched as the Dev Assessment states (verified: `orchestrator.py:4161` unchanged in `git diff develop...HEAD`).

## Sm Assessment

**Setup:** Complete. Session file, story context (`sprint/context/context-story-82-11.md`), and feature branch `feat/82-11-iteration-cap-parse-once` (sidequest-server, base develop) all verified present.

**Story:** 82-11 — 1pt p3 chore, trivial workflow. Single-repo (`sidequest-server`), two files in play: `sidequest/agents/narrator.py:86` (`resolve_narrator_iteration_cap()`) and its per-turn call site at `orchestrator.py:~4125`. Scope is tight and self-contained: parse the env once (or document per-turn re-read as intentional), preserve fail-loud ValueError on bad values, cover valid+invalid paths with a test. No cross-repo coordination, no protocol changes, no dependencies on other stories (82-10 is orthogonal — different files).

**Jira:** Skipped — personal project, no Jira integration (per server CLAUDE.md). Story claimed in sprint YAML (`in_progress`, Keith Avery).

**Routing:** trivial workflow is phased; next phase is `implement`, owner `dev` (Naomi Nagata). Dev has full context in the story description + ACs + context file.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/agents/narrator.py` — `resolve_narrator_iteration_cap()` decorated with `@functools.cache` (first-use memoization; `import functools` added). Docstring documents the 82-11 rationale: a running server's env is fixed at boot, so per-turn re-read bought nothing; `functools.cache` does not cache exceptions, so an invalid value re-raises on every call — fail-loud preserved, not one-shot.
- `sidequest-server/tests/agents/test_narrator_iteration_cap_toggle.py` — autouse fixture clears the cache before/after each test (this file mutates the env per-test; clearing both directions prevents leak-in from earlier worker tests and leak-out to other narrator-turn tests). Two new tests: `test_resolve_iteration_cap_is_memoized` (AC1 — env mutation after first call does not change the resolved value; `cache_clear()` is the explicit re-read seam) and `test_resolve_iteration_cap_invalid_value_raises_every_call` (AC2 — ValueError on every call, not one-shot).

**AC coverage:**
- AC1 (parse once, not per-turn): MET — memoized via `functools.cache`; pinned by `test_resolve_iteration_cap_is_memoized`.
- AC2 (fail-loud preserved + valid/invalid tests): MET — existing valid/non-int/non-positive tests retained and green; new every-call-raise test added.

**Call-site note:** `orchestrator.py:4161` unchanged — the call stays in the turn path but is now an O(1) cache hit after the first turn. No OTEL span added: this is a perf/hygiene chore on a config parse, not a subsystem decision (CLAUDE.md OTEL principle's cosmetic exemption); the cap's *effect* already emits `narrator.tool_loop.cap_hit`.

**Tests:** 9/9 targeted file; full `tests/agents/` suite 1768 passed, 1 pre-existing skip; ruff check + format clean (via testing-runner, RUN_ID 82-11-dev-green).
**Branch:** `feat/82-11-iteration-cap-parse-once` (sidequest-server, base develop) — pushed, commit 7de2813.

**Handoff:** To review phase.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (9/9 green, ruff clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 3 | confirmed 1 (merged conftest finding), dismissed 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 1 (merged conftest finding), dismissed 1 |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 1 (merged conftest finding), dismissed 4 |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none (4 rules checked, 0 violations) | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled via settings)
**Total findings:** 1 confirmed (deduplicated from 3 specialists), 7 dismissed (with rationale), 0 deferred

**Dismissal rationales:**
- [EDGE] cap<=0 raise-every-call path untested (low): dismissed — both ValueError sites sit below the same `@functools.cache` decorator boundary (narrator.py:87); the exceptions-not-cached property cannot differ per raise site within one decorated function.
- [EDGE] empty-string env hard-breaks turns (medium): dismissed as a *defect* — pre-existing behavior not introduced by this diff, and raising on `VAR=` is *compliant* with No Silent Fallbacks (treating empty as unset would BE a silent fallback). Recorded as a non-blocking test-coverage Question in Delivery Findings instead.
- [SILENT] is_streaming_enabled adjacency note (low): dismissed — explicitly out of diff scope, pre-existing, flagged by the specialist itself as context-only.
- [TEST] every-call-raise test couples to functools.cache property (medium): dismissed — the test pins the *product invariant* "invalid config raises on every resolution attempt" (No Silent Fallbacks); a future implementation that cached exceptions would violate that invariant and the test would correctly catch it. Asserting a contract currently guaranteed by a stdlib property is regression-guarding, not coupling.
- [TEST] memoization test's third assertion uses cache_clear() (medium): dismissed — `cache_clear()` is documented in the production docstring (narrator.py:98-99) as the explicit re-read seam; pinning a documented seam is acceptable coupling for a 1pt chore.
- [TEST] whitespace " 5 " accepted by int() (low): dismissed — Python-standard `int()` semantics, identical to the `SIDEQUEST_SESSION_COST_CEILING_USD` parser this function explicitly mirrors (docstring); changing strictness here would diverge from the mirrored pattern and is out of scope.
- [TEST] cap=1 boundary wiring test missing (low): dismissed — the AC4b wiring tests are pre-existing 82-9 deliverables, untouched by this diff; out of story scope.

## Rule Compliance

Functions in diff: `resolve_narrator_iteration_cap` (modified), `_clear_iteration_cap_cache` (test fixture, new), `test_resolve_iteration_cap_is_memoized` (new), `test_resolve_iteration_cap_invalid_value_raises_every_call` (new).

| Rule | Instance | Verdict |
|------|----------|---------|
| No Silent Fallbacks (CLAUDE.md) | `resolve_narrator_iteration_cap` narrator.py:88 | COMPLIANT — unset→None (documented no-cap), invalid→ValueError; exceptions not cached so the raise repeats every call (pinned by new AC2 test) |
| No Stubbing (CLAUDE.md) | entire diff | COMPLIANT — no stubs/placeholders; 61 added lines all live |
| Every Test Suite Needs a Wiring Test (CLAUDE.md) | test file | COMPLIANT — pre-existing AC4b tests drive a REAL `Orchestrator.run_narration_turn` through the memoized resolver and assert the `narrator.tool_loop.cap_hit` OTEL span; they pass post-change (9/9) |
| No Source-Text Wiring Tests (server CLAUDE.md) | new tests | COMPLIANT — no `read_text()` grep assertions; behavior + OTEL span assertions only |
| lang-review #1 silent exceptions | diff | COMPLIANT — no except blocks added |
| lang-review #2 mutable defaults | all 4 functions | COMPLIANT — no defaults at all |
| lang-review #3 type annotations | `resolve_narrator_iteration_cap` → `int \| None`; test functions → `None`; fixture is private (exempt, still typed via monkeypatch params) | COMPLIANT |
| lang-review #6 test quality | new tests | COMPLIANT — specific value assertions (==5, ==9, pytest.raises), no vacuous asserts, no skips, no mock-target errors |
| lang-review #9 async pitfalls | diff | COMPLIANT — no async code touched; `functools.cache` first-call race under concurrent turns is benign (both racers compute the identical value from the same env; verified narrator.py:104-117 is pure) |
| lang-review #10 import hygiene | `import functools` narrator.py:13 | COMPLIANT — stdlib, stdlib-group placement, ruff-clean; no cycles |
| lang-review #11 input validation | narrator.py:111-118 | COMPLIANT — type via int(), range via cap<=0 |
| OTEL Observability Principle (CLAUDE.md) | diff | COMPLIANT via exemption — perf/hygiene chore on a config parse, no subsystem *decision* changed; the cap's effect already emits `narrator.tool_loop.cap_hit` (asserted by AC4b tests) |

### Devil's Advocate

Argue this is broken. **One:** the entire premise — "env is fixed at boot" — is an assumption, not a law. If any test harness, scene harness (ADR-92), or future operator tooling mutates `os.environ` at runtime expecting the cap to take effect, memoization silently ignores it. I hunted for exactly this: grep shows zero production writes to the var and a single production call site (orchestrator.py:4161); the only mutators are this test file (which clears both directions) — the assumption holds *today*, and the docstring + memoization test pin it loudly enough that a future violator will hit a pinned test, not silence. **Two:** concurrency — narrator turns are async; two first-calls could race the cache. `functools.cache` under CPython holds the GIL per dict op; worst case both compute `int(raw)` from the same immutable env and store identical values. No torn state possible — the function is pure given the env. **Three:** the file-local fixture is the real crack: a stressed developer with `SIDEQUEST_NARRATOR_ITERATION_CAP=3` exported in their shell runs the full suite; narrator-turn tests in *other* files now run capped at 3 — and pre-change they *also* would have (per-turn re-read reads the same ambient env), so the memoization changes stickiness, not exposure; the negative-path test `test_no_toggle_means_no_cap_hit` deletes the env and clears cache via autouse, so it stays correct. Still, the cross-file inbound window is real once a future file sets the var — that's the confirmed conftest finding. **Four:** what would a confused operator do? Export `VAR=` empty, expecting off — gets a per-turn ValueError. Loud, immediate, debuggable: exactly what No Silent Fallbacks demands; pre-existing besides. **Five:** uvicorn `--reload` — module reimport rebuilds the decorated function and its cache; fresh env read on first turn after reload. Correct behavior, no staleness across reloads. Nothing here rises above the already-confirmed Medium.

## Reviewer Assessment

**Verdict:** APPROVED

**Observations (≥5):**
1. [VERIFIED] Memoization is sound for the stated contract — narrator.py:87 `@functools.cache` on a zero-arg pure function of process env; sole production caller orchestrator.py:4161; zero production env mutators (grep). Complies with No Silent Fallbacks: exceptions re-raise every call (pinned at test file :131-143).
2. [VERIFIED] Fail-loud preserved — narrator.py:111-118 unchanged parse/validate; new AC2 test asserts ValueError on consecutive calls; security specialist confirmed exceptions never enter the cache (currsize stays 0).
3. [VERIFIED] Wiring intact — AC4b tests drive a real `run_narration_turn` through the memoized resolver to the `narrator.tool_loop.cap_hit` span; 9/9 green post-change (preflight, RUN_ID 82-11 review).
4. [EDGE][SILENT][TEST] [MEDIUM] File-local autouse cache-clear fixture (test file :43) leaves future SDK-path narration test files without inherited isolation under xdist shared workers. Confirmed, non-blocking (latent — no other file sets the env today; both leak directions defended in the only file that does). Recorded as Delivery Finding → conftest.py home.
5. [VERIFIED] Test quality — specific-value assertions throughout (==5, ==9, parametrized raises); no vacuous asserts; complies with lang-review #6 and No Source-Text Wiring Tests.
6. [LOW] Empty-string env (`VAR=`) raises per-turn rather than reading as unset — pre-existing, rule-compliant (empty-as-unset would be a silent fallback), untested; recorded as non-blocking Question.
7. [SEC] [VERIFIED] Security clean — specialist checked 4 rules with 0 violations: no eval/exec/pickle (int() only, narrator.py:113), type+range validation at the boundary (:113-118), no DoS via cache (exceptions uncached; env not attacker-mutable), and the `raw!r` in the ValueError message (:116) carries an operator's own numeric-config typo, not credentials/PII — negligible leak risk, same pattern as the mirrored cost-ceiling parser.

**Data flow traced:** operator shell → `os.environ["SIDEQUEST_NARRATOR_ITERATION_CAP"]` → first narrator turn → `resolve_narrator_iteration_cap()` (parse+validate once, cached) → `iteration_cap=` kwarg at orchestrator.py:4161 → `complete_with_tools` soft cap → `narrator.tool_loop.cap_hit` OTEL span when crossed. Safe because: input is operator-set (not player-reachable), validated for type+range, and an invalid value fails the turn loudly rather than running uncapped.

**Pattern observed:** Good — docstring-documented memoization contract with an explicit test seam (`cache_clear()`, narrator.py:96-101), mirroring the `SIDEQUEST_SESSION_COST_CEILING_USD` parser family. Test fixture defends both leak directions (test file :43-53).

**Error handling:** ValueError on non-int (int() at narrator.py:113) and non-positive (explicit raise :114-118); both uncached, so misconfiguration cannot be masked after first raise — verified empirically by silent-failure specialist and pinned by test :131-143.

**Handoff:** To SM for finish-story.