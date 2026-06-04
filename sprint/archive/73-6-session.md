---
story_id: "73-6"
jira_key: ""
epic: "73"
workflow: "trivial"
---
# Story 73-6: Rescope shared e2e fixtures so tests/e2e/test_encounter_wiring_e2e.py actually runs

## Story Details
- **ID:** 73-6
- **Jira Key:** (none)
- **Epic:** 73 — Confrontation Engine Hardening
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-06-04

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04 | - | - |

## Delivery Findings

### Dev (implementation)
- **Gap** (non-blocking): The two `tests/e2e/test_encounter_wiring_e2e.py` tests now *execute* but *fail on stale assertions* that predate the dual-dial encounter migration (ADR-024). `test_combat_walkthrough_initiate_tick_resolve` asserts `sd.snapshot.encounter.metric.current`, but `StructuredEncounter` replaced the single `metric` field with `player_metric` + `opponent_metric` and a validator (`_reject_legacy_metric`, `sidequest/game/encounter.py:224`) now *actively rejects* the legacy `metric` field. `test_xp_award_higher_in_combat_than_out` expects an in-combat XP delta of 25 but observes 10. Affects `sidequest-server/tests/e2e/test_encounter_wiring_e2e.py` (tests must be rewritten against the dual-dial model, and the in-combat XP-award behavior verified/repaired). **Explicitly out of scope for 73-6** (story scopes assertion fixes out) — recommend a follow-up story under epic 73. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `session_handler_factory` now exists in both `tests/conftest.py` and `tests/server/conftest.py`. Story sanctioned keeping the duplicate, but a future DRY pass should delete the server-conftest copy so the fixture is genuinely shared from one place (avoids drift). Affects `sidequest-server/tests/server/conftest.py` (remove lines ~559–752 once verified). *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/tests/conftest.py` — Added `session_handler_factory` fixture (rescoped from `tests/server/conftest.py` to the root conftest so `tests/e2e/` can discover it); imports inlined into the fixture body; ruff-clean.

**Verification:**
- E2E collection: `pytest tests/e2e/test_encounter_wiring_e2e.py --collect-only` → 2 collected, **0 fixture-not-found errors** (previously both ERRORed at setup). AC-2 ✓
- E2E execution: both tests now **execute** (no fixture-setup ERROR) — AC-3 ✓. They fail on stale assertions (dual-dial `metric` migration + XP delta), which the story explicitly scopes OUT — see Delivery Findings.
- Server inheritance: `tests/server/test_confrontation_dispatch_wiring.py` → **7/7 passing** (fixture override intact). AC-4 ✓
- Lint: `ruff check tests/conftest.py` → all checks passed.

**Tests:** Fixture rescope GREEN — e2e tests de-inerted (run), 7/7 dependent server tests pass. (E2e assertion failures are out-of-scope stale tests, flagged for follow-up.)
**Branch:** feat/73-6-rescope-e2e-fixtures

**Handoff:** To review phase (team-lead coordinates).

## Design Deviations

### Dev (implementation)
- **Inlined fixture imports instead of copying module-level imports verbatim**
  - Spec source: context-story-73-6.md, "Implementation" step 2
  - Spec text: "Keep all imports and type annotations intact"
  - Implementation: The `session_handler_factory` copy in `tests/conftest.py` imports its dependencies (`TYPE_CHECKING`, `MagicMock`, `room_for`, and the `GameMode` TYPE_CHECKING-only import) inside the fixture function body rather than at module scope, because `tests/conftest.py` does not have those module-level imports that `tests/server/conftest.py` does. Behavior is byte-identical; only import *location* differs.
  - Rationale: Adding the imports at module scope in the shared root conftest would pull server/session internals into the import graph of every test package (game/, daemon/, etc.). Function-scoped imports keep the blast radius to the fixture itself and match how the original was structured (its deps were already module-level in the server conftest). `from __future__ import annotations` (line 3) makes the lazy string annotations safe.
  - Severity: minor
  - Forward impact: none — fixture is functionally identical to the server-conftest original.

- **Kept the duplicate `session_handler_factory` in `tests/server/conftest.py` (copy, not move)**
  - Spec source: context-story-73-6.md, AC-1 / "What to move" / Files Changed
  - Spec text: "tests/server/conftest.py — Optional: Remove the duplicate definition (not required; fixtures in parent conftests shadow duplicates in children)"
  - Implementation: Left the original definition in place. The root copy serves `tests/e2e/`; the server-conftest copy continues to serve `tests/server/` via pytest's child-overrides-parent fixture semantics. No redefinition error — same-named fixtures in parent vs child conftest is an override, not a collision.
  - Rationale: Removal is explicitly marked optional by the story. Minimalist discipline: no failing test demands the removal, and removing ~192 lines from the server conftest is a larger, riskier diff than the story requires. Flagged as a non-blocking Improvement finding for a future DRY pass.
  - Severity: minor
  - Forward impact: minor — two copies could drift over time; captured as a Delivery Finding.

---

## Technical Context

### Problem Statement
Story 73-5 (Suppress re-fired encounter.confrontation_initiated span on resolution turn) was completed, but discovered that `tests/e2e/test_encounter_wiring_e2e.py` is **currently inert and NEVER RUN** — both e2e tests (`test_combat_walkthrough_initiate_tick_resolve` and `test_xp_award_higher_in_combat_than_out`) ERROR at setup with **"fixture not found"**. The shared fixtures they depend on (`session_handler_factory` and `span_exporter`) live in `tests/server/conftest.py`, which is **invisible to `tests/e2e/`** — pytest fixture discovery is directory-scoped, and the e2e tests directory cannot see fixtures defined in a sibling test subdirectory.

The consequence: combat-lifecycle e2e validation is completely absent. Resolution-turn regressions (like the one 73-5 fixed) have no end-to-end guard.

### Solution
Move the shared fixtures to a conftest visible to both `tests/e2e/` and `tests/server/`: the top-level `tests/conftest.py`. This fixture file is visible to all test packages in the tree (pytest's directory-scoped fixture discovery hierarchy).

**Fixtures moved:**
- `session_handler_factory` — factory for synthetic session + handler; used by e2e tests to spin up combat scenarios
- `span_exporter` — in-memory OTEL span capture (already lives in the e2e test file itself; left as-is for isolation)

Actually: the `span_exporter` fixture is already defined locally in `test_encounter_wiring_e2e.py` (line 24). Only `session_handler_factory` needs to move.

### Technical Approach
1. **Move `session_handler_factory` from `tests/server/conftest.py` to `tests/conftest.py`** — This root-level conftest is already imported by pytest before any subdirectory conftest, so its fixtures are visible to `tests/server/`, `tests/e2e/`, and all other test packages.
2. **Verify the e2e test can now discover the fixture** — `pytest --collect-only` should no longer report "fixture not found" for `session_handler_factory`.
3. **Run the e2e tests** — They should no longer ERROR at setup. (Note: test failures on assertion logic are out-of-scope; we just need the fixture ERROR gone.)
4. **Leave the duplicate in `tests/server/conftest.py` or remove it** — Since pytest's fixture inheritance is hierarchical (child conftest can access parent), removing the duplicate from `tests/server/conftest.py` won't break server tests — they'll inherit from the root. For clarity and DRY, remove the duplicate.

### Acceptance Criteria
1. `session_handler_factory` is defined in `tests/conftest.py` (the root-level conftest).
2. Both `tests/e2e/test_encounter_wiring_e2e.py` tests can be collected without "fixture not found" errors.
3. Both e2e tests can run to at least the first assertion (no fixture-setup ERROR).
4. `tests/server/` tests that use `session_handler_factory` still pass (fixture inheritance works).
5. The e2e tests still collect and run (even if assertions fail — that's a different story).

### Scope
- **In scope:** Moving the fixture to the root conftest so e2e tests can discover it.
- **Out of scope:** Fixing the combat encounter initialization logic that the e2e tests assert on (that's 73-5 or a follow-up); fixing the test assertions themselves; adding new tests.

### Files Changed
- `tests/conftest.py` — Add `session_handler_factory` fixture (moved from `tests/server/conftest.py`)
- `tests/server/conftest.py` — Remove or keep the duplicate definition (optional; removing is cleaner)

### Key References
- Epic 73 context: `/Users/slabgorb/Projects/oq-3/sprint/context/context-epic-73.md`
- Story 73-5: `/Users/slabgorb/Projects/oq-3/sprint/context/context-story-73-5.md`
- E2E test file: `/Users/slabgorb/Projects/oq-3/sidequest-server/tests/e2e/test_encounter_wiring_e2e.py`
- Fixture source: `/Users/slabgorb/Projects/oq-3/sidequest-server/tests/server/conftest.py` (lines 561–752)
