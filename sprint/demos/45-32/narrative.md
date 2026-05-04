# 45-32

## Problem

**Problem:** A previous code review flagged eight specific quality issues in test files — stale comments, a misleading test assertion that would pass even on wrong answers, and overly permissive checks that let bugs hide. **Why it matters:** Tests are only useful if they can actually catch problems. A test that passes on a wrong answer is worse than no test at all — it creates false confidence. Stale comments pointing to deleted code mean the next developer wastes time chasing a ghost.

---

## What Changed

Imagine a set of smoke detectors in a building. Story 45-2 installed them. Story 45-32 is the follow-up inspection that found: one detector was labeled with the wrong room number, one would sound the alarm regardless of whether there was actually smoke, and one would only trigger if smoke was *exactly* the right shade of grey.

Four files were touched — three test files and one production comment. Nothing that the game actually runs changed. This was purely about making the safety net more honest.

**Specifically:**
- A test comment that said "this test is failing" was updated to say "this test is passing" (the underlying bug was fixed in 45-2; nobody updated the label).
- A test that checked "did we get *any* response?" was upgraded to "did we get the *correct* response type?" — the old version would have passed even if the server returned an error.
- A test that accepted two spellings of the same word (`"chargen"` or `"CHARGEN"`) was locked to the authoritative spelling. If the code ever starts using the wrong spelling, now the test fails loudly.
- A code comment that described a function's behavior was rewritten to be unambiguous.

---

## Why This Approach

Reviewers flagged these as non-blocking, meaning they didn't prevent shipping — but they were specifically logged as "clean up before the next sprint." Addressing them immediately keeps the test suite honest and prevents the findings from going stale a second time.

The team also caught that the reviewer's own suggestions had two errors: the suggested assertion referenced a message type that doesn't exist in the protocol, and referenced a file that code had since moved out of. Rather than blindly implementing wrong fixes, the team verified against the actual running code and made the fixes correct. This is the right call — following a prescription without reading the label is how bugs get introduced during cleanup.

---
