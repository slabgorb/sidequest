# Story 73-6 Context

## Title
Rescope shared e2e fixtures so tests/e2e/test_encounter_wiring_e2e.py actually runs

## Metadata
- **Story ID:** 73-6
- **Type:** bug
- **Points:** 2
- **Priority:** p3
- **Workflow:** trivial
- **Repo:** sidequest-server
- **Epic:** 73 — Confrontation Engine Hardening

## Problem
Story 73-5 (Suppress re-fired encounter.confrontation_initiated span on resolution turn) was completed, but uncovered that `tests/e2e/test_encounter_wiring_e2e.py` is **currently INERT** — both e2e tests that validate combat-lifecycle end-to-end (`test_combat_walkthrough_initiate_tick_resolve` and `test_xp_award_higher_in_combat_than_out`) ERROR at setup with **"fixture not found"**.

The root cause: The shared fixtures they depend on (`session_handler_factory` and `span_exporter`) live in `tests/server/conftest.py`, which is **invisible to `tests/e2e/`**. Pytest fixture discovery is directory-scoped — `conftest.py` files in one test subdirectory cannot see fixtures defined in a sibling subdirectory.

**Consequence:** Combat-lifecycle e2e validation is completely absent. Regressions in resolution-turn behavior (like the one 73-5 fixed) have no end-to-end guard — the only coverage is unit tests in isolation.

## Technical Approach

### Root Cause
Pytest fixture scoping and discovery:
- `tests/server/conftest.py` defines `session_handler_factory` (line 561–752)
- `tests/e2e/test_encounter_wiring_e2e.py` requests `session_handler_factory` as a fixture argument
- When pytest collects `tests/e2e/`, it loads `tests/e2e/conftest.py` (does not exist), then walks up to `tests/conftest.py`
- It does NOT walk sideways into `tests/server/conftest.py` — different branch of the tree
- Result: "fixture not found" error at collection time

### Solution
Move the `session_handler_factory` fixture to `tests/conftest.py` (the top-level conftest visible to all test packages).

**Why this works:**
- pytest loads `tests/conftest.py` before any subdirectory conftest
- Any fixture in `tests/conftest.py` is available to `tests/e2e/`, `tests/server/`, `tests/game/`, etc. — the entire tree
- Pytest's fixture inheritance is hierarchical; fixtures in parent conftests are visible to children

**What to move:**
1. `session_handler_factory` (lines 561–752 of `tests/server/conftest.py`) — the full factory fixture

**What NOT to move:**
- `span_exporter` — it's already defined locally in `test_encounter_wiring_e2e.py` itself (line 24) for test isolation; leave it as-is

### Implementation
1. Copy `session_handler_factory` from `tests/server/conftest.py` to the end of `tests/conftest.py`
2. Keep all imports and type annotations intact
3. Verify `tests/e2e/test_encounter_wiring_e2e.py` tests collect without "fixture not found" errors
4. Verify both e2e tests can run (assertions pass/fail is out-of-scope; just need the fixture error gone)
5. Verify `tests/server/` tests that use the fixture still work (fixture inheritance)
6. Optional: Remove the duplicate from `tests/server/conftest.py` (can stay for backward compatibility if the duplicate is not causing issues)

## Acceptance Criteria

1. **`session_handler_factory` is defined in `tests/conftest.py`** — the root-level conftest, visible to all test packages
2. **E2E test collection succeeds** — `pytest tests/e2e/test_encounter_wiring_e2e.py --collect-only` reports 0 fixture-not-found errors
3. **E2E tests can run** — both `test_combat_walkthrough_initiate_tick_resolve` and `test_xp_award_higher_in_combat_than_out` can execute (no setup ERROR; assertions passing/failing is out-of-scope)
4. **Server tests unaffected** — `tests/server/` tests that depend on `session_handler_factory` still pass (fixture inheritance works correctly)
5. **No side effects** — no other fixtures or test behavior changes

## Scope

**In scope:**
- Move `session_handler_factory` to the root conftest so e2e tests can discover it
- Verify e2e tests collect and run without fixture setup errors

**Out of scope:**
- Fixing the combat encounter initialization logic that the e2e test assertions check (that's 73-5 or a follow-up story)
- Fixing test assertion failures (if assertions fail after the fixture is wired, that's a different issue)
- Adding new tests or test coverage
- Refactoring the fixture implementation itself (move as-is)

## Files Changed
- `tests/conftest.py` — Add `session_handler_factory` fixture at the end
- `tests/server/conftest.py` — Optional: Remove the duplicate definition (not required; fixtures in parent conftests shadow duplicates in children)

## Key References
- **Epic 73 context:** `sprint/context/context-epic-73.md` — Confrontation Engine Hardening overview
- **Story 73-5 context:** `sprint/context/context-story-73-5.md` — The story that discovered this fixture issue
- **E2E test file:** `sidequest-server/tests/e2e/test_encounter_wiring_e2e.py` — The tests that need the fixture
- **Source fixture:** `sidequest-server/tests/server/conftest.py` lines 561–752 — `session_handler_factory`
- **pytest fixture discovery:** https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-and-session (directory-scoped conftest.py loading)

## Test Commands

**Verify fixture collection (should show 0 "fixture not found" errors):**
```bash
cd sidequest-server && uv run pytest tests/e2e/test_encounter_wiring_e2e.py --collect-only
```

**Run the e2e tests (should no longer ERROR at setup):**
```bash
cd sidequest-server && uv run pytest tests/e2e/test_encounter_wiring_e2e.py -xvs
```

**Verify server tests still pass (fixture inheritance):**
```bash
cd sidequest-server && uv run pytest tests/server/test_confrontation_dispatch_wiring.py -xvs
```

---
_Generated for story 73-6 by sm-setup on 2026-06-04._
