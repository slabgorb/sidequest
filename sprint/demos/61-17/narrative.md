# 61-17

## Problem

**Problem:** A test that was supposed to verify how the game engine caches AI narrator instructions started failing — not because the code broke, but because a previous improvement made the code *better*, and nobody updated the test to match.

**Why it matters:** Failing tests that nobody trusts are worse than no tests at all. When a test fails for the wrong reason, it creates noise that masks real problems. Engineers stop trusting the suite, red starts meaning nothing, and the first real regression slips through undetected. A stale assertion is a broken smoke alarm — it's always beeping, so nobody runs when smoke appears.

---

## What Changed

Think of the game's AI narrator as a chef who keeps certain recipe cards permanently pinned to the wall (cached, always-available) versus others on a notepad they rewrite each time (uncached, fresh each turn).

A recent improvement (Story 61-10) moved the "narrator constraints" card — the rules reminding the AI how to behave — from the notepad pile to the pinned-to-the-wall pile. That was a smart, deliberate optimization: those rules never change during a session, so why rewrite them every turn?

The problem: a test was still checking the *old* location. It expected to find the card on the notepad (`cached = False`), but the card had been properly promoted to the wall (`cached = True`). The test failed every single run, screaming "card is in the wrong place!" — when actually the card was exactly where it should be.

The fix: update the test to check the correct location. One line changed. The comment explaining *why* was also corrected, because it was still describing the old notepad world.

---

## Why This Approach

The production code was right. The test was wrong. The correct move was to fix the test, not revert the optimization.

Reverting the code would have been the "easy" fix — make the test pass by moving the card back to the notepad. But that would undo a real performance improvement that reduces redundant work on every AI narrator call. "Don't break a working optimization to appease a stale test" is a foundational engineering principle.

The harder check — which the reviewer explicitly performed — was confirming the updated test still *means something*. A test that always passes is also worthless. The team verified that the revised assertion still catches a real class of bugs: if someone accidentally removes narrator_constraints from the cached section in the future, the test will fail again, correctly this time. The guard rail is intact; it's just pointing at the right thing.

---
