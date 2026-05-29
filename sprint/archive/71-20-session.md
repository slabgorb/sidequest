---
story_id: "71-20"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-20: Fail loud at startup when Postgres schema is behind alembic head

## Story Details
- **ID:** 71-20
- **Jira Key:** (none — this project does not use Jira)
- **Workflow:** tdd
- **Epic:** 71 — Playtest bugfix — uncovered findings (coyote_star MP, 2026-05-27)
- **Stack Parent:** none

## Story Context

### Problem Statement

**Violation:** The dev DB was stamped at alembic `0001` while head was `0002` (0002_asset_ledger.py from Story 65-2 had never been applied). The server BOOTED FINE and ran for many turns; the only symptom was `'relation "asset_ledger" does not exist'` ERROR on every scene render's ledger write—a failure surfacing deep in a turn, far from the root cause (a behind-head schema).

This is a textbook **No Silent Fallbacks** breach: a misconfigured/behind-head DB should fail LOUD at boot, not limp along and explode mid-turn at the first write to the missing table.

### Context: ADR-115 and Database Startup

**ADR-115** already implements fail-loud behavior when Postgres is **unreachable**: `MissingDatabaseUrlError` is raised at startup, and the connection pool wait timeout is set to 10s. This story extends that contract to cover the case where Postgres is **reachable but the schema is behind the alembic head**.

### Design Decision

Two approaches are under consideration:

1. **(A) Fail-loud-assert (PREFERRED)**
   - At startup, assert that the connected DB's alembic current revision == alembic heads
   - If the DB is behind (or divergent), fail loud AT BOOT with a clear error naming the current vs head revision
   - Migration stays an explicit, visible operator step (not hidden/silenced in the boot process)
   - Aligns with No-Silent-Fallbacks doctrine
   - Operator runs `alembic upgrade head` or `just <recipe>` explicitly

2. **(B) Auto-upgrade-on-boot (REJECTED)**
   - Have boot / `just up` run `alembic upgrade head` automatically
   - **Rejected:** Silently mutating the schema at boot is itself a silent action and can surprise on a shared DB
   - Convenience does not outweigh the risk of hidden state mutation

**Decision:** Implement (A) fail-loud-assert.

### Technical Approach

1. **Startup location:** Server startup path (app lifespan hook / `db_config` / connection pool initialization)
2. **Check mechanism:** Use alembic API to compare current revision against heads via `SIDEQUEST_DATABASE_URL`
3. **Failure mode:** Clear error message at boot naming current revision, head revision, and remediation steps
4. **Reuse:** Extend existing ADR-115 fail-loud startup contract (same failure class/hierarchy, same operator experience)
5. **Logging:** Emit startup log entry with schema-version check result (current rev, head rev, pass/fail) so operator/GM panel can verify DB is at head

### Acceptance Criteria

1. Server startup asserts the connected Postgres DB's alembic revision equals alembic heads; if the DB is behind (or divergent), the server fails loud **AT BOOT** with a clear error naming the current vs head revision—never deferring the failure to a mid-turn write.
2. The startup failure message tells the operator exactly how to fix it (e.g. run `alembic upgrade head` / `just <recipe>`).
3. **DECISION recorded in story:** fail-loud-assert (A) vs auto-upgrade-on-boot (B). Boot / `just up` does NOT silently mutate the schema—migration stays an explicit, visible operator step.
4. Reuses/extends the existing ADR-115 fail-loud startup contract (MissingDatabaseUrlError / pool-wait timeout) rather than adding a parallel mechanism.
5. **Test coverage:** (a) Booting against a behind-head DB raises the loud startup error; (b) Booting against a head-current DB succeeds; (c) Failure is at startup, not at render-write time.
6. Startup logs the schema-version check result (current rev, head rev, pass/fail) so the operator/GM panel can see the DB is at head.

### Related ADRs & References

- **ADR-115:** Persistence Substrate Migration — SQLite-Per-Session to PostgreSQL (fail-loud contract on unreachable DB)
- **Story 65-2:** Database schema migration that introduced 0002_asset_ledger.py (root cause of the behind-head scenario)
- `.pennyfarthing/guides/save-management.md`: Migration procedures (linked in story description)

## Sm Assessment

**Setup complete — routing to red phase (TEA).**

- **Scope:** Single-repo (sidequest-server), 3pt TDD. Extend the existing ADR-115 fail-loud startup contract to cover "Postgres reachable but schema behind alembic head." No new parallel mechanism — same failure class, same operator experience.
- **Design decision pre-recorded in the story context (AC#3):** approach (A) fail-loud-assert is preferred and recommended; approach (B) auto-upgrade-on-boot is rejected as itself a silent action. TEA should write tests against (A). If the implementer wants to revisit, that's a Design Deviation, logged.
- **Doctrine fit:** This is a textbook No Silent Fallbacks story. The whole point is moving the failure from a deep mid-turn write to a loud boot-time assert. Tests must prove the failure fires AT STARTUP, not at render time (AC#5c).
- **OTEL/logging:** AC#6 requires a startup log entry of the schema check (current rev, head rev, pass/fail) so the operator can verify the DB is at head — keep this in the red test surface.
- **Branch:** `feat/71-20-fail-loud-schema-behind-head` on sidequest-server.
- **No blockers.** Clean handoff to Radar for the red phase.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (7 failing, 1 passing control — ready for Dev)

**Test Files:**
- `tests/persistence/test_schema_at_head_check.py` — function-level guard contract (6 tests).
- `tests/server/test_startup_schema_guard_wiring.py` — behavior-level wiring: real `create_app()` lifespan startup fails loud on a behind-head DB (2 tests).
- `tests/conftest.py` — new shared `behind_head_db` fixture (a real Postgres DB upgraded only to base `0001` — deliberately behind head; mirrors `migrated_db`).

**Target API the tests pin (Dev implements this):**
- New module `sidequest/game/db_schema_check.py` with:
  - `class SchemaBehindHeadError(RuntimeError)` — raised when DB revision != alembic head.
  - `def assert_schema_at_head() -> None` — resolves the URL via `db_config` (reuses `MissingDatabaseUrlError` on unset, AC#4), reads the DB's current alembic revision, compares to the script head, **logs** current+head (logger `sidequest.game.db_schema_check`, AC#6), and raises `SchemaBehindHeadError` naming current vs head + the `alembic upgrade head` remediation if behind. Returns `None` on success.
- Wire `assert_schema_at_head()` into the server startup path (alongside/after `_open_db_pool` in `app.py:244` — the existing ADR-115 fail-loud hook) so a behind-head DB aborts boot.

**RED evidence:** `7 failed, 1 passed` — all 7 failures are `ModuleNotFoundError: No module named 'sidequest.game.db_schema_check'`. Zero skips (DB env wired via `.env` → `SIDEQUEST_TEST_DATABASE_URL`). The 1 pass is `test_startup_succeeds_on_head_current_db` — the intended false-positive control (a head-current DB already boots clean today and must keep doing so).

### Rule Coverage (lang-review: python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent-exceptions (fail loud, no swallow) | `test_behind_head_db_fails_loud`, `test_startup_fails_loud_on_behind_head_db` | RED |
| #4 logging coverage (current+head, failure AND success path) | `test_check_logs_result_when_behind`, `test_check_logs_result_at_head` | RED |
| #6 test-quality (own tests) | self-check below | pass |

**Rules checked:** 3 of 13 applicable (the rest — mutable defaults, deserialization, async-gather, import hygiene, SQL/input validation, deps — have no surface in this change; #3 type-annotations, #7 resource-leaks (DB conn via `with`), and #9 sync-DB-read-in-async-startup are Dev implementation concerns flagged in Delivery Findings).
**Self-check:** 0 vacuous tests. Every test asserts a specific value: `pytest.raises(<specific type>)` + substring checks on the message, `is None` on the success contract, `status_code == 200`, or log-message content. No `assert True`, no bare truthy checks, no `let _`-equivalents.

**Decision note (AC#3):** The (A) fail-loud-assert vs (B) auto-upgrade decision is recorded in `context-story-71-20.md` and the SM Assessment; the tests enforce **(A)** by construction (they assert boot *raises*, never that the schema is silently mutated/upgraded). See the TEA deviation below re: why "decision is recorded in a code comment" is not itself a test.

**Handoff:** To Dev (Winchester) for GREEN — implement `db_schema_check.py` + wire into `app.py` startup.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 8/8 target tests GREEN; 200/200 regression slice (persistence + test_app.py + smoke) GREEN. ruff + pyright clean on changed files.

**Files Changed:**
- `sidequest/game/db_schema_check.py` (NEW) — `SchemaBehindHeadError(RuntimeError)` + `assert_schema_at_head() -> None`. Resolves the URL via `db_config.database_url()` (so unset → the same ADR-115 `MissingDatabaseUrlError`, AC#4), reads the DB's current revision from the `alembic_version` table, compares to the script head (`ScriptDirectory.get_current_head()`), logs current+head on both paths (logger `sidequest.game.db_schema_check`, AC#6), and raises naming current vs head + the `alembic upgrade head` remediation when behind (AC#1/#2/#5). The (A) fail-loud vs (B) auto-upgrade decision is recorded in the module docstring (AC#3). DB connection uses a `with` context manager (TEA finding #7); public signature annotated (#3).
- `sidequest/server/app.py` — wired `assert_schema_at_head()` into the existing `_open_db_pool` startup hook, right after `pool.wait()` and before the `db_pool.startup_wired` log, so a behind-head DB aborts boot. Sync call inside the async hook mirrors the established `pool.wait()` pattern (TEA finding #9), not a new async path.

**Implementation notes:**
- Verified the dev `sidequest` DB and the `sidequest_test` DB are both at head (0002), so wiring the guard into `_open_db_pool` does not break the many existing `with TestClient(app)` startup tests (confirmed: 200 passed).
- Added a defensive fail-loud path for an unmigrated DB (no `alembic_version` table → `current = None` → raises, labeled "(unmigrated)") and for a missing alembic head — both extend the No-Silent-Fallbacks contract beyond the literal AC.

**Branch:** `feat/71-20-fail-loud-schema-behind-head` (pushed)
**Handoff:** To TEA (Radar) for the verify phase (simplify + quality-pass).

### Dev Rework (review verdict: REJECTED — mechanical only)

Addressed both Reviewer findings (lint/format on the new test files; the red/verify phases had linted only production files):
- **SIM117** — combined the nested `with` statements in `tests/persistence/test_schema_at_head_check.py` (`caplog.at_level` + `pytest.raises`) and `tests/server/test_startup_schema_guard_wiring.py` (`pytest.raises` + `TestClient`). Semantically equivalent; no behaviour change.
- **format** — ran `ruff format` on the two test files.

**Verification after rework:** `ruff check` (all 5 changed files) clean; `ruff format --check` clean; `pyright` clean; 200/200 regression slice GREEN. The two Reviewer LOW deferred notes (multi-head `fetchone`, "Behind" class also covers ahead-of-head) are accepted as-is — not in scope for this story.
**Handoff:** Back to Reviewer (Colonel Potter) for re-review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

AC-by-AC verification against `context-story-71-20.md`:

| AC | Verdict | Evidence |
|----|---------|----------|
| #1 boot-time assert, fails loud naming current vs head | ✓ | `assert_schema_at_head()` raises `SchemaBehindHeadError` with both revisions; wired into `_open_db_pool` after `pool.wait()` (app.py:255) so it fires at boot, not at write. |
| #2 actionable message | ✓ | Error names `alembic upgrade head` (+ `just pg-up` for a fresh DB). |
| #3 decision recorded (A vs B) | ✓ | Module docstring (db_schema_check.py:12-17) records (A) fail-loud-assert and the rejection of (B) auto-upgrade as a silent action. No silent schema mutation at boot. |
| #4 reuses ADR-115 contract | ✓ | Resolves via `db_config.database_url()` → same `MissingDatabaseUrlError`; `SchemaBehindHeadError(RuntimeError)` mirrors the existing class style; lives in the same `_open_db_pool` fail-loud hook. Not a parallel mechanism. |
| #5 test coverage (behind raises, head passes, failure at startup) | ✓ | 8/8 green incl. behavior-level wiring test driving real `create_app()` lifespan. |
| #6 logs current+head, pass/fail | ✓ | `logger.info` ("OK: db at alembic head") on success, `logger.error` (current+head) on failure, logger `sidequest.game.db_schema_check`. |

**Commendations (no action):**
- The check uses `current == head` equality, which catches **divergent/ahead** schemas too, not just "behind" — stricter than the literal AC and aligned with the context's "behind (or divergent)" language.
- `_current_revision` guards the `alembic_version` read with an `EXISTS` subquery so an unmigrated DB returns `None` (→ fails loud) rather than raising `UndefinedTable` — no swallowed exception, clean fail-loud extension.
- Lazy import of `assert_schema_at_head` inside the startup hook keeps import-time cost off the module graph (import hygiene).

**Deviation review:** Dev's logged deviation (current revision read from `alembic_version` directly vs `MigrationContext`) is sound and correctly scoped — `alembic_version` is alembic's own state table, and avoiding a SQLAlchemy engine on the hot boot path is the right call. The linear single-head history makes `get_current_head()` safe; multi-head handling is correctly deferred. No additional deviations found.

**Decision:** Proceed to review (via TEA verify).

**Spec-check re-run (post-rework):** The Dev rework was lint/format only (combined nested `with`s + `ruff format` on two test files) — zero behavioural change. Spec alignment unchanged: still Aligned, no drift, no new deviations.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (200/200 persistence + test_app.py + smoke; ruff + pyright clean)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (db_schema_check.py, app.py, conftest.py, + 2 test files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | `_head_revision`/`_alembic_head` dup (high); conftest fixture dup (medium) |
| simplify-quality | 3 findings | EXISTS SQL clarity (medium); behind-head naming (low); error-propagation doc gap (medium) |
| simplify-efficiency | 2 findings | EXISTS SQL redundancy (medium); conftest fixture dup (high) |

**Applied:** 1 change — added a clarifying comment + docstring note in `db_schema_check.py::_current_revision` (addresses the EXISTS-SQL clarity finding flagged by BOTH quality and efficiency, and the quality error-propagation doc-gap finding). Comment/docstring only — zero behaviour change, re-verified 200/200 green.

**Flagged for Review (not applied):**
- **conftest fixture duplication** (`behind_head_db` mirrors `migrated_db`, ~30 lines). reuse=medium, efficiency=high — the teammates *disagree* on confidence. Not applied because extracting a shared helper requires refactoring the **pre-existing, suite-wide `migrated_db` session fixture** (lifted to conftest in ADR-115 D5, used across the whole persistence suite) — that is scope creep beyond this story and risks a regression far worse than the duplication. The two fixtures also read clearly as distinct test conditions (clean vs stale schema). Recommend Reviewer accept as-is or spin a separate refactor story.

**Dismissed:**
- **`_head_revision` "duplication"** (reuse, high): the test's `_alembic_head()` is an *intentionally independent oracle* — it computes the expected head separately from the production code under test. Merging them would couple the assertion to the implementation and let a buggy head computation pass. Keeping them separate is correct test design, not redundancy.
- **behind-head hyphenation** (quality, low): "behind-head" is correct English prose for the concept; the Python identifier is `behind_head_db`. No inconsistency.

**Overall:** simplify: applied 1 clarity fix; 1 finding flagged for Reviewer; 2 dismissed with rationale.

**Quality Checks:** All passing (ruff, pyright, 200 tests).
**Handoff:** To Reviewer (Colonel Potter) for code review.

### Verify re-run (post-rework)

The Dev rework since the first verify pass was mechanical only — combined nested `with`s + `ruff format` on the two test files; production code (`db_schema_check.py`, `app.py`) unchanged. No new simplify surface, so the prior 3-teammate report stands; a full fan-out re-run would be wasteful churn. Re-confirmed quality gates: `ruff check` clean (all 5 files), `ruff format --check` clean, `pyright` 0 errors, 200/200 regression slice green. **Overall:** simplify: clean (no new findings). Handoff to Reviewer.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | tests GREEN (200), types PASS, **lint FAIL (2× SIM117), format FAIL (1 file)** | confirmed 2 (lint+format), 0 dismissed |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings (assessed by Reviewer — see [SILENT]) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings (assessed by Reviewer — see [TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings (assessed by Reviewer — see [DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings (assessed by Reviewer — see [TYPE]) |
| 7 | reviewer-security | Yes | clean | none | N/A — confirmed clean |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (verify phase ran simplify — see [SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings (lint rules verified by Reviewer — see [RULE]) |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents`, assessed directly)
**Total findings:** 2 confirmed (both mechanical, blocking the merge gate), 0 dismissed, 2 deferred (LOW, multi-head/ahead — see below)

## Reviewer Assessment

**Verdict:** REJECTED — mechanical gate failure only (lint + format on test files). Substantively the implementation is clean and correct; it cannot merge until the ruff gate is green.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [LOW]→blocking | `[RULE]` SIM117 nested-`with` — project ruff config enforces SIM117; `ruff check` exits 1, CI/`just server-lint` would fail | `tests/persistence/test_schema_at_head_check.py:120`, `tests/server/test_startup_schema_guard_wiring.py:36` | Combine the two `with` statements into one (`with A, B:`) — semantically equivalent in both cases — or add `# noqa: SIM117` with a one-line reason. |
| [LOW]→blocking | `[RULE]` `ruff format` would reformat the file; `ruff format --check` exits 1 | `tests/persistence/test_schema_at_head_check.py` | Run `uv run ruff format tests/persistence/test_schema_at_head_check.py`. |

**Why REJECT for LOW issues:** Neither is a logic flaw, but both fail the project's ruff gate (`just server-lint`). Approving would push a guaranteed CI failure into SM's finish/PR step. Root cause: the red + verify phases linted only the production files, never the new test files. Fix is ~3 lines; route to Dev (green rework).

### Observations (tagged)

- `[SEC]` **VERIFIED clean** (subagent + own read): static SQL, no interpolation (`db_schema_check.py` `_current_revision` query); conninfo (may carry credentials) is never logged nor included in any exception — logs only revision ids (`logger.info`/`logger.error`) and the raise carries only `current_label`/`head`. No CWE-89, no secret leak.
- `[SILENT]` **VERIFIED** (analyzer disabled; assessed directly): no swallowed errors. Genuine connection/query errors propagate by design (documented in `_current_revision` docstring); unset URL reuses `MissingDatabaseUrlError` via `database_url()`. Complies with No Silent Fallbacks.
- `[TEST]` **VERIFIED** (analyzer disabled; assessed directly): every test asserts specific values — `pytest.raises(<specific type>)` + message-substring checks, `is None`, `status_code == 200`, log-message content. No vacuous assertions. `behind_head_db` fixture correctly provisions a stale DB (`conftest.py` upgrades to `0001`, not head). Wiring test drives real `create_app()` lifespan — not a source-text grep.
- `[DOC]` **VERIFIED** (analyzer disabled; assessed directly): comments are accurate and explain non-obvious behavior (the EXISTS guard; the deliberate error-propagation). No stale/misleading docs. AC#3 decision recorded in the module docstring — confirms TEA's forward-impact ask.
- `[TYPE]` **VERIFIED** (analyzer disabled; assessed directly): full annotations on all functions; `_head_revision` correctly handles alembic's `str | None` return by failing loud. `SchemaBehindHeadError(RuntimeError)` mirrors the existing `MissingDatabaseUrlError(RuntimeError)` style.
- `[SIMPLE]` Verify phase already ran the 3 simplify teammates: 1 clarity fix applied, fixture-duplication deferred with rationale. No additional complexity concerns.
- `[RULE]` Two confirmed ruff violations (above) — the only blocking items. All other lang-review rules pass (see Rule Compliance).
- `[EDGE]` **VERIFIED** (hunter disabled; assessed directly): empty `alembic_version` (0 rows) → `None` → fails loud; missing table → `None` → fails loud; ahead-of-head → mismatch → fails loud.
- `[LOW][deferred]` Multi-head history: `_current_revision` uses `fetchone()`, which would read only one of multiple `alembic_version` rows; `_head_revision` uses `get_current_head()`, which would RAISE on multiple script heads. Latent, unreachable under the current linear history — consistent with Dev's logged multi-head deferral. Not a blocker.
- `[LOW][deferred]` Cosmetic: `SchemaBehindHeadError` also fires when the DB is AHEAD of head; the message shows accurate current/head values so it is not misleading. Not worth a fix.

### Rule Compliance (lang-review: python.md)

| Rule | Verdict | Evidence |
|------|---------|----------|
| #1 silent exceptions | PASS | No bare/blanket except; EXISTS guard avoids a swallowing try/except; errors propagate. |
| #3 type annotations | PASS | `assert_schema_at_head() -> None`, `_current_revision(conninfo: str) -> str \| None`, `_head_revision() -> str`. |
| #4 logging | PASS | `logger.info` (success) / `logger.error` (failure), lazy `%s` form, no sensitive data. |
| #5 path handling | PASS (note) | `Config("alembic.ini")` relative to CWD — consistent with existing `alembic/env.py` + conftest usage; no `open()` w/o encoding. |
| #6 test quality | PASS (substance) | Meaningful assertions; **but ruff hygiene fails (#SIM117 + format) — the blocking finding.** |
| #7 resource leaks | PASS | `with psycopg.connect()` context-managed. |
| #9 async pitfalls | PASS | Sync DB read in async startup hook mirrors the established `pool.wait()` pattern. |
| #10 import hygiene | PASS | Explicit imports; lazy import inside the startup hook avoids import-time cost/cycles. |
| #11 SQL injection | PASS | Static query, no interpolation of external input. |

### Devil's Advocate

Trying to break it: (1) **Multi-row `alembic_version`.** `_current_revision` calls `fetchone()` — if a future multi-head migration leaves two rows in `alembic_version`, the check reads an arbitrary one and could mis-pass/mis-fail. Today the history is linear (single head) and `get_current_head()` would itself raise on multiple script heads, so the window is closed — but the DB-side `fetchone()` is the quieter half. Logged as LOW/deferred, matching Dev's multi-head deviation. (2) **CWD dependence.** `Config("alembic.ini")` is resolved relative to the process working directory. Launch uvicorn from the wrong directory and `get_current_head()` returns `None` → raises "alembic has no head" — fail-loud (good) but a misleading message (the real cause is CWD, not missing migrations). Consistent with the rest of the codebase (env.py, conftest both assume CWD = repo root), so acceptable. (3) **Empty/NULL version_num.** A truncated `alembic_version` (0 rows) or NULL value resolves to `current=None` → "(unmigrated)" → fails loud. Correct. (4) **Malicious input.** `conninfo` comes from `SIDEQUEST_DATABASE_URL`; an attacker who controls that already owns the deploy — out of threat model, and the value is never echoed to logs. (5) **Concurrency.** Boot reads a schema snapshot; migrations are explicit operator steps, not concurrent with startup — no race in practice. Conclusion: the only thing actually standing between this and merge is the ruff gate. The logic is sound.

**Handoff:** Back to Dev (Winchester) for the mechanical lint/format fix (green rework).

---

## Subagent Results

*(Re-review after green rework. Rework diff `af3b6c0..HEAD` touched ONLY the two test files — combined nested `with`s + `ruff format`; zero production/SQL change. Security surface unchanged from the prior clean pass; preflight re-run to confirm the mechanical gate is now green.)*

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | lint CLEAN, format CLEAN, pyright CLEAN, tests 200/0/0 — prior SIM117×2 + format diff CONFIRMED FIXED | N/A — gate green |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings (assessed by Reviewer — see [TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none — reused prior clean pass; no production/SQL delta in the rework | N/A — confirmed clean |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings (ruff rules verified green by preflight) |

**All received:** Yes (preflight re-run clean; security carried from prior clean pass — production code unchanged in the rework)
**Total findings:** 0 confirmed, 0 dismissed, 2 deferred (LOW multi-head / ahead-of-head — unchanged from first review)

## Reviewer Assessment

**Verdict:** APPROVED

The prior REJECT was mechanical-only (2× SIM117 + 1 format diff in the new test files). Dev's rework (`1496e98`) combined the nested `with` statements and ran `ruff format` — verified semantically equivalent from the diff (`af3b6c0..HEAD`): the `caplog.at_level + pytest.raises` and `pytest.raises + TestClient` contexts behave identically combined vs nested. No production/SQL code changed.

- `[RULE]` Both prior ruff violations **resolved** — `ruff check` + `ruff format --check` clean on all 5 files (preflight re-run).
- `[SEC]` Unchanged from first pass — no production/SQL delta; prior security result was clean (static SQL, no credential leak, no source-text wiring tests).
- `[TEST]` `with`-combine preserves test semantics; 200/0/0 green re-confirmed. Tests still assert specific values.
- `[SILENT]` / `[TYPE]` / `[DOC]` / `[EDGE]` / `[SIMPLE]` — production code untouched since the first-pass VERIFIED-clean review; all prior verdicts stand.
- Two `[LOW][deferred]` notes (multi-head `fetchone`; "Behind" class also covers ahead-of-head) carry forward unchanged — not blocking.

**Data flow traced:** `SIDEQUEST_DATABASE_URL` (env) → `database_url()` → psycopg connection → `SELECT version_num FROM alembic_version` → compared to alembic script head; mismatch raises `SchemaBehindHeadError` at boot. Safe: conninfo never logged; static SQL.
**Pattern observed:** extends the ADR-115 `_open_db_pool` fail-loud startup hook (`app.py`) rather than adding a parallel mechanism.
**Error handling:** genuine DB errors propagate (fail loud by design); unset URL reuses `MissingDatabaseUrlError`.

**Handoff:** To SM (Hawkeye) for finish-story.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-29T09:41:33Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-29T09:02:43Z | 2026-05-29T09:04:49Z | 2m 6s |
| red | 2026-05-29T09:04:49Z | 2026-05-29T09:16:40Z | 11m 51s |
| green | 2026-05-29T09:16:40Z | 2026-05-29T09:21:33Z | 4m 53s |
| spec-check | 2026-05-29T09:21:33Z | 2026-05-29T09:22:43Z | 1m 10s |
| verify | 2026-05-29T09:22:43Z | 2026-05-29T09:26:51Z | 4m 8s |
| review | 2026-05-29T09:26:51Z | 2026-05-29T09:33:16Z | 6m 25s |
| green | 2026-05-29T09:33:16Z | 2026-05-29T09:35:38Z | 2m 22s |
| spec-check | 2026-05-29T09:35:38Z | 2026-05-29T09:36:17Z | 39s |
| verify | 2026-05-29T09:36:17Z | 2026-05-29T09:37:03Z | 46s |
| review | 2026-05-29T09:37:03Z | 2026-05-29T09:40:29Z | 3m 26s |
| spec-reconcile | 2026-05-29T09:40:29Z | 2026-05-29T09:41:33Z | 1m 4s |
| finish | 2026-05-29T09:41:33Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### TEA (test design)
- **Improvement** (non-blocking): the new schema check opens a DB connection at boot to read the current alembic revision — it MUST use a `with` context manager (lang-review #7 resource-leaks) and annotate the public `assert_schema_at_head` signature (#3). Affects `sidequest/game/db_schema_check.py` (Dev to author). *Found by TEA during test design.*
- **Question** (non-blocking): the check runs inside an `async` startup hook but does sync DB I/O — this follows the established `_open_db_pool`/`pool.wait()` pattern in `app.py:244` (sync-blocking-at-boot is acceptable for a one-shot startup gate), but Dev should mirror that pattern rather than introduce a new async path (lang-review #9). Affects `sidequest/server/app.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): `.env` / `.env.example` now carry `SIDEQUEST_TEST_DATABASE_URL` so `just server-test` runs the persistence suite instead of skipping it — previously the DB-backed tests silently SKIPped unless the operator hand-exported the var. Affects `.env`, `.env.example`. *Found by TEA during test design (operator request mid-phase).*
- **Improvement** (non-blocking): `tests/conftest.py` `behind_head_db` and the pre-existing `migrated_db` share ~30 lines of DB provision/cleanup; a future refactor could extract a `_provision_pg_db(target_revision, prefix)` helper. Deferred from this story because it would touch the suite-wide `migrated_db` session fixture (regression risk). Affects `tests/conftest.py` (candidate for a standalone test-infra refactor story). *Found by TEA during test verification.*

### Dev (implementation)
- **Improvement** (non-blocking): the guard now also fails loud on a *never-migrated* DB (no `alembic_version` table) and on a missing alembic head, not only on a behind-head DB — these were not in the literal ACs but are the same No-Silent-Fallbacks class. Affects `sidequest/game/db_schema_check.py`. *Found by Dev during implementation.*
- **Question** (non-blocking): a future ADR could fold this boot-time schema assertion into a `/health` readiness probe so orchestration can gate traffic on it (out of scope here — story explicitly excludes a health endpoint). Affects `sidequest/server/app.py`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (blocking): new test files were never run through ruff — 2× SIM117 + 1 format failure block `just server-lint`/CI. Affects `tests/persistence/test_schema_at_head_check.py`, `tests/server/test_startup_schema_guard_wiring.py` (combine the nested `with`s / run `ruff format`). *Found by Reviewer during code review.*
- **Process** (non-blocking): the red and verify phases should lint the *test* files they author/touch, not only the production files — this gap let a guaranteed CI failure reach review. Affects the TDD red/verify checklist. *Found by Reviewer during code review.*
- **Resolved** (re-review): the blocking lint/format gap above was fixed by Dev rework `1496e98` (combined `with`s + `ruff format`); re-review preflight confirms ruff check + format + pyright clean, 200/0/0 green. Verdict upgraded REJECTED → APPROVED. *Noted by Reviewer during re-review.*

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

### TEA (test design)
- **AC#3 (decision recorded) has no runtime test**
  - Spec source: context-story-71-20.md, AC#3
  - Spec text: "Decision recorded: (A) fail-loud-assert vs (B) auto-upgrade, with rationale, written into the story/ADR/code comment."
  - Implementation: No test asserts the decision is "recorded." Instead the tests enforce the *consequence* of decision (A) — boot raises on a behind-head DB and never silently mutates the schema. The recording itself lives in `context-story-71-20.md` + the SM Assessment, and the code-comment artifact is a Reviewer concern.
  - Rationale: Asserting on a code comment or doc string would be a source-text grep, banned by CLAUDE.md "No Source-Text Wiring Tests." Behavior (A) is testable; "a comment exists" is not (meaningfully).
  - Severity: minor
  - Forward impact: Reviewer should confirm Dev recorded the (A)-vs-(B) rationale in a code comment / docstring in `db_schema_check.py`.

### Dev (implementation)
- **Current revision read directly from `alembic_version` instead of via MigrationContext**
  - Spec source: context-story-71-20.md, Technical Guardrails
  - Spec text: "Compare `alembic current` vs `alembic heads` via the alembic API against `SIDEQUEST_DATABASE_URL`."
  - Implementation: HEAD is read via the alembic API (`ScriptDirectory.get_current_head()`); CURRENT is read with a direct `SELECT version_num FROM alembic_version` over a psycopg connection, rather than `alembic.runtime.migration.MigrationContext.get_current_revision()`.
  - Rationale: `MigrationContext.configure(connection=...)` expects a SQLAlchemy Connection; the runtime path uses psycopg, not a SQLAlchemy engine. Reading alembic's own `alembic_version` table directly is the same source of truth without dragging a SQLAlchemy engine into the hot boot path, and it lets the unmigrated-DB case (table absent) fail loud cleanly.
  - Severity: minor
  - Forward impact: none — `alembic_version` is alembic's documented state table; a future multi-head history would need `get_heads()`/multi-row handling, but the current schema is linear (single head).

### Reviewer (audit)
- **TEA: "AC#3 (decision recorded) has no runtime test"** → ✓ ACCEPTED by Reviewer: correct call — asserting on a comment would be a banned source-text grep. Forward-impact discharged: the (A)-vs-(B) rationale IS recorded in the `db_schema_check.py` module docstring (verified).
- **Dev: "Current revision read directly from `alembic_version` instead of via MigrationContext"** → ✓ ACCEPTED by Reviewer: sound — `alembic_version` is alembic's own state table; reading it via psycopg avoids dragging a SQLAlchemy engine onto the boot path, and the `fetchone()` multi-row caveat is correctly scoped to a deferred multi-head future (single-head history today). No undocumented deviations found beyond these.

### Architect (reconcile)

Definitive deviation manifest for Story 71-20 (sidequest-server only; no Jira; no PRD beyond the story/epic context). Cross-referenced against `context-story-71-20.md`, `context-epic-71.md`, sibling epic-71 ACs, and the in-flight TEA/Dev deviation logs.

**Existing deviations — verified accurate and complete (all 6 fields):**

1. **TEA — "AC#3 (decision recorded) has no runtime test."** Spec source verified: `context-story-71-20.md:85` ("Decision recorded: (A) fail-loud-assert vs (B) auto-upgrade, with rationale…"). Accurate: no test asserts on the recorded decision (a comment-grep would violate No Source-Text Wiring Tests); the decision IS recorded in the `db_schema_check.py` module docstring, and the tests enforce consequence (A) by construction. Severity minor, forward impact discharged. **Confirmed.**

2. **Dev — "Current revision read from `alembic_version` directly, not via MigrationContext."** Spec source verified: `context-story-71-20.md:34` ("Compare `alembic current` vs `alembic heads` via the alembic API"). Accurate: HEAD uses the alembic API (`ScriptDirectory.get_current_head()`); CURRENT is read via `SELECT version_num FROM alembic_version` to avoid a SQLAlchemy engine on the boot path. `alembic_version` is alembic's own state table — same source of truth. Severity minor, forward impact none (multi-head correctly deferred). **Confirmed.**

**AC deferral check:** None — all 6 ACs are DONE (verified at spec-check and by the Reviewer's APPROVED verdict). No deferred or descoped ACs to reconcile.

**Missed deviations:** No additional deviations found. The extra fail-loud paths (unmigrated DB, missing alembic head) and the `.env`/`.env.example` test-DB wiring are enhancements within the story's No-Silent-Fallbacks intent and the test-infra scope — they extend, but do not contradict, any AC, so they are captured as Delivery Findings rather than spec deviations.