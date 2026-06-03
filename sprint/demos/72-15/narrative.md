# Narrative

## Problem Statement
**Problem:** Seventeen automated safety checks for the game's monster-seeding system were silently turned off — and had been for months. A single outdated test referencing a retired game world caused the entire test file to be skipped, sweeping away 16 unrelated checks that have nothing to do with that world.

**Why it matters:** The monster-seeding system (which pre-populates NPCs and encounters as players enter new areas) is live and active in every game session. With its tests dark, any bug introduced into that system would sail through the automated pipeline undetected — no alarm, no failure, no warning. This is exactly the kind of silent coverage gap that causes production regressions.

---

## What Changed
Think of it like a smoke detector whose battery died. The detector was still physically there, but it wasn't testing anything. This story replaces the battery.

Specifically: one end-to-end test in the file was wired to a game world ("Caverns of Sünden") that the team retired months ago. Rather than surgically removing just that test, someone had marked the **entire file** as "skip this" — which accidentally silenced 16 other tests that had nothing to do with that old world.

Three fixes were made, all in test files only (no production code touched):

1. **The fake pack was updated.** The unit tests use a simplified "stub" version of a game pack to test in isolation. That stub had gotten out of sync with how the real production code now calls it — it was answering a question the code no longer asks. The stub was updated to speak the current API.

2. **The outdated end-to-end test was redirected.** Instead of pointing at the retired Caverns of Sünden world, it now points at a dedicated synthetic test fixture — a minimal fake world that lives inside the test suite itself, never changes under the tests, and has no dependency on live content migrations happening elsewhere.

3. **The skip was removed.** With the stub fixed and the end-to-end test re-pointed, the whole file was un-silenced. All 17 tests now run.

---

## Why This Approach
The tempting shortcut would have been to simply delete the outdated end-to-end test entirely. That would have un-silenced the 16 unit tests, but it would have left a gap in end-to-end coverage.

Instead, the test was *moved* — redirected to a hermetic fixture that will never be disrupted by live content work. This approach:

- **Preserves end-to-end coverage** without coupling the test to the content migration already in flight (Epic 71-31).
- **Reuses existing infrastructure.** The team found a `test_genre/flickering_reach` fixture pack already in the test suite that had nearly everything needed. One small adjustment (converting its name-generation from corpus-based lookup to a simple word list) made it fully self-contained and eliminated any dependency on files that don't exist in CI.
- **Follows the "tests must not point at live content" rule.** Coupling an automated test to a live game world means the test can break whenever content authors edit that world — a false failure completely unrelated to the code under test. The fixture approach seals the test from that risk.

---

## Before/After
| | Before | After |
|---|---|---|
| **test_pregen.py status** | 100% skipped (17/17 tests never ran) | 17/17 tests pass |
| **Coverage of pregen system** | None — regressions would pass CI silently | Unit + end-to-end, hermetic |
| **_stub_pack API** | Exposed `.cultures` (removed attribute) | Implements `effective_cultures(world)` returning correct 2-tuple |
| **End-to-end test target** | `caverns_sunden` (deprecated, retired world) | `test_genre/flickering_reach` (in-repo fixture, stable) |
| **Content coupling** | Tied to a live world (fragile) | Tied to a fixture (immune to content migration) |
| **CI behavior on a pregen bug** | Silent pass | Failing test |
