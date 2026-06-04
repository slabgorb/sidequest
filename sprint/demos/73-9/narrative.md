# Narrative

## Problem Statement
Problem: The confrontation engine shipped new beat-impact feedback in stories 73-4, 73-7, and 73-8, but several specific behaviors were never tested — meaning a future code change could silently break them and the test suite would give a false green. Why it matters: A bug in beat-impact feedback (the "you scored a backfire," "opponent took a setback" readout players see after each combat action) is invisible until someone is sitting at the table and the numbers don't add up. For mechanics-first players like Sebastien and Jade — who specifically play *to see the math work* — a silent regression in this layer is a trust-breaker.

---

## What Changed
Imagine you've just installed a burglar alarm. The alarm works great. But nobody ever tested whether it would go off if someone broke the back window instead of the front door — so you don't actually know if you're covered.

That's what this story fixed. The team added a set of safety tests for the combat feedback system — specifically for the tricky edge cases: what happens when an action backfires, when an opponent stumbles in a strange way, when two players act at the same moment, when a fight ends cleanly with nothing to report, and when the display has to handle a partially-missing data set without crashing. None of the game's actual behavior changed. The tests now prove it works in all those corners.

Two old tests that were essentially checking "does *anything* exist here?" were also replaced with precise checks: "does *this specific value* exist here?" — a much stronger guarantee.

---

## Why This Approach
When a team ships meaningful new behavior (as 73-4/73-7/73-8 did), the ideal is to write the safety tests alongside the code. That didn't fully happen — the stories were complex and the test gaps were noted but deferred. Rather than letting that debt accumulate silently, this story pays it down in one focused pass: test-only, no production touch, no risk of introducing a new bug while fixing a coverage gap.

This is also the right time to do it — the behavior is fresh, the original authors are close to it, and the team is about to move on to styling the impact feedback (73-10). If the tests aren't in place before that work starts, any regression from 73-10 would be much harder to diagnose.

---
