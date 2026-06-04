# Narrative

## Problem Statement
Problem: Two end-to-end tests that verify combat behavior were silently broken — they crashed before running a single line of actual test code, every time. Why it matters: SideQuest's combat system is one of the most mechanically complex parts of the engine, and the team had zero automated coverage proving it works end-to-end. A regression could ship undetected.

---

## What Changed
Think of tests as workers, and `conftest.py` files as the supply closets those workers draw tools from. The combat end-to-end tests lived in one hallway (`tests/e2e/`), but the tools they needed were locked in a supply closet down a different hallway (`tests/server/`). Every time those tests tried to run, they reached for their tools and found nothing — then crashed with "fixture not found" before doing any work at all.

The fix: move the shared tools to a supply closet at the top of the building (`tests/conftest.py`) where every test suite can reach them. Nothing about the tests themselves changed — just where the shared setup lives.

---

## Why This Approach
pytest's fixture scoping rules are hierarchical — a `conftest.py` file only donates its fixtures to tests in the same directory and below. Copying fixtures into the e2e file itself would create duplication to maintain. Moving them one level up to the root `tests/` directory is the minimal, correct solution: one source of truth, visible to all test suites, no copies to drift apart.

---

## Before/After
| | Before | After |
|---|---|---|
| `test_combat_walkthrough_initiate_tick_resolve` | `ERROR: fixture 'session_handler_factory' not found` — never ran | `PASSED` — full combat lifecycle verified |
| `test_xp_award_higher_in_combat_than_out` | `ERROR: fixture 'span_exporter' not found` — never ran | `PASSED` — XP differential between combat and non-combat confirmed |
| Combat regression safety net | None — any combat-resolution bug could ship undetected | Automated — CI will catch initiate/tick/resolve breakage |
| Fixture location | `tests/server/conftest.py` (invisible to e2e suite) | `tests/conftest.py` (visible to all test suites) |
