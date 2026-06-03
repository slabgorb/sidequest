---
story_id: "81-1"
jira_key: ""
epic: "81"
workflow: "tdd"
---
# Story 81-1: Register magic plugins in production so MAGIC_PLUGINS is non-empty at runtime (ADR-126)

## Story Details
- **ID:** 81-1
- **Jira Key:** (not used — Jira disabled)
- **Epic:** 81
- **Workflow:** tdd
- **Stack Parent:** none

## Acceptance Criteria

1. Importing the production entrypoint 'import sidequest.magic' (NOT sidequest.magic.plugins directly) populates MAGIC_PLUGINS with all three plugin ids: innate_v1, item_legacy_v1, learned_v1.

2. magic_validate() for a descriptor-registered plugin_id no longer returns the plugin_known_but_not_registered flag (validator.py:107-123); plugin-side validation runs. A test asserts the DEEP_RED branch is NOT taken for a registered plugin.

3. No import cycle is introduced: the server app imports and boots cleanly (importing sidequest.server app / 'just server' start succeeds).

4. WIRING TEST: a test that imports only a production module (sidequest.magic or the narration_apply path) and asserts MAGIC_PLUGINS is non-empty — this test FAILS on the current code and PASSES after the fix. Full sidequest-server suite green (just server-test).

## Technical Context

**Root Cause:**
- `sidequest/magic/__init__.py:24` imports MAGIC_PLUGINS from `sidequest.magic.plugin` (the bare/empty registry)
- **Nothing in production** imports the `sidequest.magic.plugins` PACKAGE, whose star-imports (`plugins/__init__.py:8-10` → `innate_v1`, `item_legacy_v1`, `learned_v1`) are what populate MAGIC_PLUGINS at import
- Only tests import it (`tests/magic/conftest.py:24`, `tests/magic/test_wiring.py:29`)
- Result: in production, `MAGIC_PLUGINS is {}` and every `magic_validate()` call (sidequest/server/narration_apply.py:813) hits the `plugin_known_but_not_registered` DEEP_RED branch (validator.py:107-123)

**Fix Strategy:**
- Trigger registration from a production path by importing the plugins package in `sidequest/magic/__init__.py`
- Mirror the `sidequest/telemetry/spans/__init__.py` star-import-of-domain-modules pattern (documented in the plugins docstring)
- Guard against import cycles
- Ensure the fix does NOT rely on test-only imports

**Wiring Doctrine:**
This story directly serves ADR-126 runtime wiring: the plugins subsystem is fully built and tested in isolation, but never wired into a production code path. The fix verifies via a production-only import test (AC#4) that MAGIC_PLUGINS is populated without importing `sidequest.magic.plugins` directly — failing on current code, passing after the fix.

## Sm Assessment

Setup complete and routed to RED (tea). This is the only-p1 tier of the sprint (Epic 81, Built-Not-Wired Remediation) — the project's cardinal anti-pattern: a subsystem (`sidequest.magic.plugins`) fully built and unit-tested but with **no production consumer**, so `MAGIC_PLUGINS` is empty at runtime and every `magic_validate()` falls through the DEEP_RED `plugin_known_but_not_registered` branch.

Root cause is pre-diagnosed in the story (down to file:line), so the implementation surface is small (a guarded import in `sidequest/magic/__init__.py`). The real work is the **test contract**: the existing `tests/magic/test_wiring.py` is a false-green because it imports the plugins package directly. AC#4 is the load-bearing criterion — the new wiring test must import only a production entrypoint (`import sidequest.magic`) and assert `MAGIC_PLUGINS` is non-empty, failing on current code and passing after the fix.

**For The Architect (tea):** prioritize the production-only wiring test (AC#4) and the negative assertion that the DEEP_RED branch is not taken for a registered plugin (AC#2). Watch for import cycles when wiring the plugins package into `magic/__init__.py` (AC#3 — server boots clean). Mirror the `telemetry/spans/__init__.py` pattern the plugins docstring already cites.

Single repo (sidequest-server), branch `feat/81-1-register-magic-plugins` off develop. No stack parent, no cross-repo coordination, no ADR change needed (ADR-126 already accepted; this closes its wiring gap).

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Reason:** ADR-126 runtime wiring bug with a behavioral contract to enforce.

**Test Files:**
- `sidequest-server/tests/magic/test_production_registration_wiring.py` — 4 tests, subprocess-isolated where the bug must be proven through the production import path.

**Tests Written:** 4 tests covering 4 ACs
**Status:** RED — 3 failing (drive the fix), 1 passing (negative guard)

**Key design decision — subprocess isolation.** `tests/magic/conftest.py:22-24` has a
`scope="session", autouse=True` fixture that imports `sidequest.magic.plugins` for the
whole magic test session, populating the process-global `MAGIC_PLUGINS`. Any *in-process*
assertion about the production path is therefore masked — it passes even against the broken
code. This is the same false-green that `tests/magic/test_wiring.py::test_plugin_registry_has_innate_and_item_legacy`
suffers from (it imports the plugins package directly). The three production-path tests run
in a fresh interpreter via `subprocess.run([sys.executable, "-c", ...])` that imports ONLY
`sidequest.magic` (or `sidequest.server.narration_apply`) and never references
`sidequest.magic.plugins`. This is the only way to make the test genuinely RED. Verified
manually: `import sidequest.magic` → registry `[]`; `import sidequest.magic.plugins` →
`['innate_v1','item_legacy_v1','learned_v1']`.

| Test | AC | Now |
|------|----|-----|
| `test_production_import_alone_populates_registry` | 1, 4 | **FAIL** (registry empty via prod path) |
| `test_validator_does_not_misfire_for_registered_plugin_via_production_path` | 2 (positive) | **FAIL** (registered plugin gets false `plugin_known_but_not_registered`) |
| `test_production_validation_module_imports_without_cycle` | 3 + 1 | **FAIL** (narration_apply imports clean today, but leaves registry empty) |
| `test_validator_still_flags_genuinely_unregistered_plugin` | 2 (negative guard) | **PASS** (protects the branch from being deleted) |

**Note on the "no cycle" half of AC#3:** the import-without-error half passes today (no
cycle exists yet) and must stay green; the registry-non-empty half of the same test is RED
now. Both flip-points live in one prod-path probe so the dev can't satisfy one by breaking
the other.

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|------|---------|--------|
| #6 Test quality — isolation (conftest pollution) | all 3 subprocess tests run in fresh interpreters | enforced |
| #6 Test quality — meaningful assertions | every test asserts a specific reason/registry membership, not truthiness alone | enforced |
| No Silent Fallbacks (CLAUDE.md) | a try/except-swallow "fix" leaves the registry empty → `test_production_import_alone_populates_registry` still FAILS | enforced |
| No Source-Text Wiring Tests (CLAUDE.md) | tests assert registry contents + validator output (behavior), never grep source | complied |

**Rules checked:** 2 of ~8 lang-review rules apply to test code at RED (the rest govern the
dev's GREEN implementation); both applicable rules covered.
**Self-check:** 0 vacuous tests. Every assertion checks a specific value (registry id set
membership, presence/absence of the `plugin_known_but_not_registered` reason).

### Guidance for Agent Smith (dev / GREEN)

The fix per ADR-126 + story context: make `MAGIC_PLUGINS` populate via a production import
path — preferred is importing the plugins package from `sidequest/magic/__init__.py`,
mirroring the `sidequest/telemetry/spans/__init__.py` star-import pattern the plugins
docstring cites. **Fail loud** — do NOT wrap the import in a try/except that swallows
ImportError. If wiring into `magic/__init__.py` creates a cycle (the plugins submodules
import from `sidequest.magic.plugin`/`models`), log a Design Deviation and relocate the
import to the next-narrowest prod entrypoint (validator module or app startup) per the story
context — the subprocess tests assert the *outcome* (registry populated through the prod
path), not the specific file, so the relocation still satisfies them.

**Handoff:** To Dev for implementation (GREEN).

## Dev Assessment

**Phase:** finish
**Status:** GREEN — all 4 tests pass; full server suite green.

**Files changed:**
- `sidequest-server/sidequest/magic/__init__.py` — added `import sidequest.magic.plugins` (side-effect registration) with an explanatory comment. One-line functional change.

**Implementation.** Exactly the preferred fix from the story/context: the magic package
`__init__` now imports the plugins package, firing each plugin submodule's import-time
mutation of `MAGIC_PLUGINS`. Mirrors the `sidequest/telemetry/spans` star-import pattern the
plugins docstring cites. **Fail-loud** — a plain `import`, no try/except swallow (honors No
Silent Fallbacks). ruff's isort sorted the side-effect import to the top of the import block;
verified cycle-safe in that order because the plugin submodules import
`sidequest.magic.models`/`.plugin` as standalone modules that never reach back into the
partially-initialized `sidequest.magic` package. Comment updated to reflect the order-agnostic
cycle-safety rather than a specific placement.

**Verification:**
| Check | Result |
|-------|--------|
| New tests `test_production_registration_wiring.py` | 4 passed (was 3 failed / 1 passed) |
| Magic suite `tests/magic/` | 215 passed, 50 skipped |
| Full server suite `uv run pytest` | **9877 passed, 365 skipped, 0 failed** |
| AC#3 boot — `import sidequest.server.app` | OK, no cycle |
| Prod path — `import sidequest.magic` → `MAGIC_PLUGINS` | `['innate_v1','item_legacy_v1','learned_v1']` |
| ruff (changed files) | clean |
| pyright (changed files) | 0 errors |

**OTEL note (deliberate, see deviation).** No new span added. This fix restores the existing
production validation path; it introduces no new per-turn decision point. The existing
`magic.working` OTEL span (narration_apply Task 3.5) already instruments every working — the
fix makes that span carry *correct* plugin-validation flags instead of the false
`plugin_known_but_not_registered`. Observability is improved by making the existing signal
truthful, which is the intent of the OTEL principle.

**Pre-existing lint debt (not mine):** `uv run ruff check .` reports 10 import-org errors in
unrelated `game/`/`server/` files (tracked by story 76-10). My two changed files are
lint-clean; I left the unrelated debt untouched (scope discipline).

**Handoff:** To Reviewer (verify phase first per tdd workflow).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`sidequest/magic/__init__.py`, `tests/magic/test_production_registration_wiring.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 (1 low-confidence note: existing `_import_in_fresh_interpreter` in `tests/server/test_session_handler_import_cycle.py` is import-only; my `_run_isolated` runs arbitrary scripts — no duplication, extraction would be over-engineering for one consumer) |
| simplify-quality | clean | 0 |
| simplify-efficiency | clean | 0 |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 1 low-confidence observation (reuse note above — no action; subprocess isolation is load-bearing, not over-engineering, per all three teammates)
**Reverted:** 0

**Overall:** simplify: clean

### Quality Checks

| Check (changed files) | Result |
|------|--------|
| `ruff check sidequest/magic/__init__.py tests/magic/test_production_registration_wiring.py` | clean |
| `pyright` (changed files) | 0 errors, 0 warnings |
| `tests/magic/test_production_registration_wiring.py` | 4 passed |
| Full server suite (green phase) | 9877 passed, 0 failed |

**Pre-existing lint debt (NOT a verify blocker):** `ruff check .` repo-wide reports 10
import-org errors in files untouched by this story (owned by 76-10; logged by Dev). Quality
gate is assessed against the changeset — the changed files are clean. Did not run repo-wide
`pf check` as the quality-pass signal because it would conflate this story's quality with the
76-10 debt; targeted checks on the diff are the honest measure.

**Handoff:** To Reviewer (The Merovingian) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (one minor pre-existing carve-out, deferred)
**Mismatches Found:** 1 (minor, out-of-scope)

**Per-AC substantive check:**
- **AC#1** — Aligned. `import sidequest.magic.plugins` in `magic/__init__.py` populates `MAGIC_PLUGINS` via the production entrypoint; `test_production_import_alone_populates_registry` (subprocess-isolated) passes.
- **AC#2** — Aligned. Registered plugin no longer hits `plugin_known_but_not_registered`; the negative guard confirms a genuinely-unknown id still does. Both behaviors tested.
- **AC#3** — Aligned. `import sidequest.server.app` boots clean; no import cycle. Verified the chosen import order is cycle-safe because plugin submodules import `sidequest.magic.models`/`.plugin` as standalone modules.
- **AC#4** — Substantially aligned. Wiring tests were genuinely RED→GREEN; full suite 9877 passed. See mismatch below on the literal "server-lint clean."

**Mismatch:**
- **`server-lint clean` is repo-wide-dirty from pre-existing debt** (Different behavior — Cosmetic, Minor)
  - Spec: AC#4 "`just server-lint` clean."
  - Code: `ruff check .` reports 10 import-org errors — all in files Dev did not touch (`game/political_state.py`, `game/session.py`, `tests/game/*`, `tests/server/test_premise_bind.py`). Dev's two changed files are ruff-clean and pyright-clean.
  - Recommendation: **D — Defer.** The debt predates 81-1 and is owned by story 76-10 ("Clear pre-existing sidequest-server ruff…"). Fixing it here would be cross-scope churn touching unrelated files. Dev correctly logged it as a delivery finding. Not a blocker.

**Architectural note (affirming Dev's OTEL deviation):** Concur with the deliberate no-new-span
decision. This is a reuse-first wiring fix — it adds *zero* new infrastructure, reusing the
existing star-import registration mechanism that the plugins docstring already specified as
the intended pattern. It creates no new per-turn decision point; the existing `magic.working`
span now carries truthful plugin-validation flags instead of the false
`plugin_known_but_not_registered`. Adding a boot-time span would be noise. The fix is exactly
the minimal change the design called for.

**Decision:** Proceed to review (TEA verify next per tdd workflow).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | success/GREEN | none (9877 passed, 0 failed, 0 smells; changed files ruff-clean) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled returned, both clean; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

The two enabled specialists returned clean; the change is a one-line production side-effect import plus a subprocess-isolated wiring test. I read the full diff and both files myself. With six of the diff-based specialists disabled, I personally covered their domains below (edge, test-quality, type, simplifier, comment, silent-failure).

### Rule Compliance (python lang-review + CLAUDE.md, enumerated over the diff)

| Rule | Instances in diff | Verdict |
|------|-------------------|---------|
| #1 No silent exception swallowing / No Silent Fallbacks | the new `import sidequest.magic.plugins` (no try/except wrapper) | **Compliant** — bare import; a broken plugin raises `ImportError` to the caller. Confirmed by [SEC]. |
| #2 Mutable default args | `_run_isolated(script)`, `_fail_message(label, proc)`, 4 test fns | **Compliant** — no mutable defaults. |
| #3 Type annotations at boundaries | `_run_isolated(script: str) -> subprocess.CompletedProcess[str]`, `_fail_message(label: str, proc: ...) -> str` | **Compliant** — both module-level helpers fully annotated; pytest test fns exempt (internal). |
| #4 Logging correctness | none (no logging in either file) | **N/A** |
| #5 Path handling | none (no path/file ops; `subprocess` uses argv list) | **N/A** |
| #6 Test quality | 4 tests + 2 helpers | **Compliant** — every test has a specific assertion (registry membership / reason presence-absence), no `assert True`, no skips, no vacuous truthy checks. |
| #7 Resource leaks | `subprocess.run(...)` (not `Popen`) | **Compliant** — `run` is self-contained, no leaked handle. |
| #8 Unsafe deserialization | `subprocess.run([sys.executable, "-c", literal])` | **Compliant** — hardcoded script string, no `shell=True`, no untrusted input, no pickle/yaml/eval. Confirmed by [SEC]. |
| No Source-Text Wiring Tests (CLAUDE.md) | the 4 wiring tests | **Compliant** — they assert registry contents + validator output (behavior), never `read_text()`/grep of source. |
| Verify Wiring, Not Just Existence (CLAUDE.md) | the production change | **Compliant** — the fix gives the plugins package a *production* consumer; AC#1/#4 tests assert reachability from a prod entrypoint. This is the doctrine, satisfied. |

### Observations

- [VERIFIED] Production import is fail-loud — `sidequest/magic/__init__.py:19` is a bare `import sidequest.magic.plugins` with no surrounding try/except; a broken plugin propagates `ImportError`. Complies with No Silent Fallbacks. Corroborated by [SEC].
- [VERIFIED] Subprocess is not an injection vector — `tests/.../test_production_registration_wiring.py:39-44` passes `[sys.executable, "-c", literal_script]`, no `shell=True`, the lone f-string interpolates only the module-level `_EXPECTED_PLUGIN_IDS` set via `!r`. Corroborated by [SEC].
- [VERIFIED] Tests are genuinely RED→GREEN and isolation-correct — the subprocess design defeats the conftest autouse fixture that would otherwise mask the bug; I independently confirmed `import sidequest.magic` → `[]` before fix, populated after.
- [VERIFIED] No import cycle — `test_production_validation_module_imports_without_cycle` drives `import sidequest.server.app`/`narration_apply` in a fresh interpreter; preflight's full suite (9877 passed) includes the app-boot paths.
- [LOW] Possibly-redundant `# noqa: E402` at `sidequest/magic/__init__.py:19` — no executable code precedes the import (only docstring + comments), so E402 may not fire; the `F401` is genuinely required (side-effect import). Harmless — ruff passes clean, so no unused-noqa (RUF100) complaint. Not worth a change.
- [LOW] Positive validator test exercises only `innate_v1`; `item_legacy_v1`/`learned_v1` plugin-side validation isn't directly driven. Acceptable — the registry-population test covers all three ids, and this is a wiring story, not a per-plugin validation story.

### Devil's Advocate

Let me argue this is broken. First attack: import ordering. ruff's isort hoisted the side-effect import to the *top* of the block, ahead of `.models`/`.plugin`. If a plugin submodule reached back into the still-initializing `sidequest.magic` package (e.g. `from sidequest.magic import get_plugin`), Python would hand it a half-built module and raise `ImportError` at boot — a catastrophic, fail-at-startup regression. Why doesn't it? Because the plugin submodules import the *leaf modules* `sidequest.magic.models` and `sidequest.magic.plugin` directly, not the package surface; those leaves don't depend on the parent `__init__` completing. I verified this empirically (`import sidequest.server.app` boots clean) and structurally (the import targets are leaves). The comment now correctly claims order-independence rather than a specific placement, so a future refactor that reshuffles imports won't silently reintroduce risk.

Second attack: the false-green trap reasserting itself. The whole point of this story is that an in-process test is masked by the conftest autouse fixture. Could the *new* tests fall into the same trap? Three of them spawn a fresh interpreter, so no. The one in-process test (`test_validator_still_flags_genuinely_unregistered_plugin`) is immune by construction — it asserts a plugin id (`divine_v1`) that is *never* registered in any path, so fixture pollution cannot change its outcome. Good.

Third attack: a confused future maintainer "simplifies" the subprocess tests into plain imports to make them faster, silently re-breaking the guarantee. This is the real long-term risk. It is mitigated, not eliminated: the module docstring and the TEA deviation entry both explain why the subprocess is load-bearing. A reviewer who reads them will stop the regression; one who doesn't could reintroduce the bug. That is a documentation-dependent safeguard, which is the best available without a custom lint rule — acceptable.

Fourth attack: what if a plugin module has a genuine bug and now crashes server startup that previously "worked"? That is the *intended* behavior — fail loud at boot beats a silently empty registry that mis-flags every magic working in play. The trade is correct per project doctrine. No finding.

Nothing in the devil's advocate pass rises to a finding.

### Deviation Audit

See `### Reviewer (audit)` under Design Deviations — all three prior deviations stamped ACCEPTED.

**Data flow traced:** narrator emits `magic_working` → `narration_apply.py:813` `magic_validate(working, config)` → `validator.validate` → `get_plugin(working.plugin)`. Pre-fix: empty registry → KeyError → false `plugin_known_but_not_registered`. Post-fix: registry populated at import → real `plugin.validate_working` runs. Safe and correct.
**Pattern observed:** star-import-of-domain-modules side-effect registration, mirroring `sidequest/telemetry/spans/__init__.py` — `sidequest/magic/__init__.py:19`.
**Error handling:** fail-loud import; no swallow. Validator's existing KeyError→flag branch retained as a guard (tested).
**Handoff:** To SM for finish-story (via spec-reconcile if the workflow routes there).

## Workflow Tracking
**Workflow:** tdd (phased)
**Phase:** finish
**Phase Started:** 2026-06-03T16:05:49Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T22:00:00+00:00 | 2026-06-03T15:43:57Z | -22563s |
| red | 2026-06-03T15:43:57Z | 2026-06-03T15:50:46Z | 6m 49s |
| green | 2026-06-03T15:50:46Z | 2026-06-03T15:55:52Z | 5m 6s |
| spec-check | 2026-06-03T15:55:52Z | 2026-06-03T15:57:22Z | 1m 30s |
| verify | 2026-06-03T15:57:22Z | 2026-06-03T15:59:55Z | 2m 33s |
| review | 2026-06-03T15:59:55Z | 2026-06-03T16:04:43Z | 4m 48s |
| spec-reconcile | 2026-06-03T16:04:43Z | 2026-06-03T16:05:49Z | 1m 6s |
| finish | 2026-06-03T16:05:49Z | - | - |

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- No upstream findings during code review. Both enabled specialists (preflight, security) clean; full suite green; changed files lint/type-clean. The pre-existing repo-wide ruff debt is already captured by Dev/TEA findings and tracked under story 76-10.

### Dev (implementation)
- **Improvement** (non-blocking): `uv run ruff check .` reports 10 pre-existing import-organization errors in unrelated files (`sidequest/game/political_state.py`, `sidequest/game/session.py`, `tests/game/test_entity_sync.py`, `tests/game/test_political_belief_injection.py`, `tests/game/test_retrieval_orchestration.py`, `tests/server/test_premise_bind.py`). Unrelated to 81-1 and tracked by story 76-10. Left untouched per scope discipline. *Found by Dev during implementation.*

### TEA (test design)
- **Improvement** (non-blocking): `tests/magic/test_wiring.py::test_plugin_registry_has_innate_and_item_legacy` and `test_every_plugin_py_file_registers_in_magic_plugins` import `sidequest.magic.plugins` directly, so they stay green regardless of production wiring (the original false-green this story fixes). Affects `sidequest-server/tests/magic/test_wiring.py` (consider converting the registry-population assertion to the production-path/subprocess form now covered by `test_production_registration_wiring.py`, or deleting it as redundant once the fix lands). *Found by TEA during test design.*
- **Improvement** (non-blocking): `sidequest/magic/confrontations.py:71` emits a pydantic `UserWarning` — field `register` shadows a `BaseModel` attribute. Pre-existing, unrelated to 81-1, but noisy in every magic test run. Affects `sidequest-server/sidequest/magic/confrontations.py` (rename the field or add `model_config` to silence). *Found by TEA during test design.*

## Impact Summary

**Upstream Effects:** 2 findings (0 Gap, 0 Conflict, 0 Question, 2 Improvement)
**Blocking:** None

- **Improvement:** `tests/magic/test_wiring.py::test_plugin_registry_has_innate_and_item_legacy` and `test_every_plugin_py_file_registers_in_magic_plugins` import `sidequest.magic.plugins` directly, so they stay green regardless of production wiring (the original false-green this story fixes). Affects `sidequest-server/tests/magic/test_wiring.py`.
- **Improvement:** `sidequest/magic/confrontations.py:71` emits a pydantic `UserWarning` — field `register` shadows a `BaseModel` attribute. Pre-existing, unrelated to 81-1, but noisy in every magic test run. Affects `sidequest-server/sidequest/magic/confrontations.py`.

### Downstream Effects

Cross-module impact: 2 findings across 2 modules

- **`sidequest-server/sidequest/magic`** — 1 finding
- **`sidequest-server/tests/magic`** — 1 finding

### Deviation Justifications

2 deviations

- **Subprocess-based wiring tests instead of in-process assertions**
  - Rationale: `tests/magic/conftest.py` has a session-scoped autouse fixture that imports `sidequest.magic.plugins`, populating the process-global registry and masking the bug for any in-process test in `tests/magic/`. A subprocess is the only way to honor the AC's "production entrypoint only" requirement and make the test genuinely RED.
  - Severity: minor
  - Forward impact: GREEN/verify dev should keep the subprocess form; do not "simplify" these into in-process imports (that reintroduces the false-green). Subprocess startup adds ~0.8s to the file's runtime — acceptable.
- **No new OTEL span for the registration wiring**
  - Rationale: the fix introduces no new per-turn decision point — it restores the existing validation path. The existing `magic.working` span (narration_apply Task 3.5) already instruments every working; the fix makes that span report correct plugin-validation flags instead of the false `plugin_known_but_not_registered`. A boot-time, process-global import side-effect is not a per-turn subsystem decision, so a dedicated span would be noise.
  - Severity: minor
  - Forward impact: none — observability of magic workings is unchanged in shape, improved in accuracy.

## Design Deviations

No deviations logged at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Subprocess-based wiring tests instead of in-process assertions**
  - Spec source: context-story-81-1.md, AC#1 and AC#4
  - Spec text: "A test imports `import sidequest.magic` (NOT `sidequest.magic.plugins`) and asserts `MAGIC_PLUGINS` contains ... — if the test imports the plugins package it proves nothing"
  - Implementation: the production-path assertions run in a fresh interpreter via `subprocess.run([sys.executable, "-c", ...])` rather than as ordinary in-process pytest assertions
  - Rationale: `tests/magic/conftest.py` has a session-scoped autouse fixture that imports `sidequest.magic.plugins`, populating the process-global registry and masking the bug for any in-process test in `tests/magic/`. A subprocess is the only way to honor the AC's "production entrypoint only" requirement and make the test genuinely RED.
  - Severity: minor
  - Forward impact: GREEN/verify dev should keep the subprocess form; do not "simplify" these into in-process imports (that reintroduces the false-green). Subprocess startup adds ~0.8s to the file's runtime — acceptable.

### Dev (implementation)
- **No new OTEL span for the registration wiring**
  - Spec source: CLAUDE.md, "OTEL Observability Principle" ("Every backend fix that touches a subsystem MUST add OTEL watcher events")
  - Spec text: "Magic / class abilities — when a power activates, with cost and effect"
  - Implementation: added the plugins import side-effect only; no new span emitted
  - Rationale: the fix introduces no new per-turn decision point — it restores the existing validation path. The existing `magic.working` span (narration_apply Task 3.5) already instruments every working; the fix makes that span report correct plugin-validation flags instead of the false `plugin_known_but_not_registered`. A boot-time, process-global import side-effect is not a per-turn subsystem decision, so a dedicated span would be noise.
  - Severity: minor
  - Forward impact: none — observability of magic workings is unchanged in shape, improved in accuracy.

### Reviewer (audit)
- **TEA: Subprocess-based wiring tests instead of in-process assertions** → ✓ ACCEPTED by Reviewer: this is not a shortcut but the only correct way to defeat the conftest autouse fixture; without it the test is a false-green. Sound and load-bearing.
- **Dev: No new OTEL span for the registration wiring** → ✓ ACCEPTED by Reviewer: agrees with author reasoning. The fix adds no new per-turn decision point; the existing `magic.working` span (narration_apply Task 3.5) now carries truthful plugin-validation flags. A boot-time import side-effect does not warrant its own span. Consistent with the OTEL principle's intent (observe per-turn subsystem decisions).
- No undocumented deviations found — the diff matches the story's prescribed fix exactly (import the plugins package from `magic/__init__.py`, mirroring telemetry/spans).

### Architect (reconcile)

**Existing deviation entries — verified:**
- *TEA: Subprocess-based wiring tests* — VERIFIED accurate. Spec source `sprint/context/context-story-81-1.md` exists; AC#1 text quoted ("A test imports `import sidequest.magic` (NOT `sidequest.magic.plugins`) … if the test imports the plugins package it proves nothing") matches the file. Implementation description matches the code: `tests/magic/test_production_registration_wiring.py` runs three probes via `subprocess.run([sys.executable, "-c", …])`. All 6 fields present. Forward impact (don't simplify to in-process) is correct and now also guarded by the Reviewer's Devil's Advocate note.
- *Dev: No new OTEL span for the registration wiring* — VERIFIED accurate. Spec source CLAUDE.md "OTEL Observability Principle" quoted correctly. Implementation matches: the diff adds only the side-effect import, no span. Rationale is sound — the fix adds no per-turn decision point; the existing `magic.working` span (narration_apply Task 3.5) now reports truthful plugin-validation flags. All 6 fields present.

**Missed deviations:** No additional deviations found. The implementation is the minimal, spec-prescribed change (import `sidequest.magic.plugins` from `sidequest/magic/__init__.py`, mirroring the `sidequest/telemetry/spans/__init__.py` star-import pattern). ruff's hoisting of the side-effect import to the top of the block is an isort formatting detail, not a spec deviation — the outcome (registry populated via the production path) is order-independent and verified.

**AC deferrals:** None. All four ACs are DONE. (The pre-existing repo-wide ruff debt logged as a delivery finding is owned by story 76-10; it is not an AC of 81-1 and was not deferred from this story's scope.)