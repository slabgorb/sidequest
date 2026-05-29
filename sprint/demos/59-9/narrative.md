# 59-9

## Problem

**Problem:** In multiplayer sessions, secret actions shared across the entire party could leak into the AI narrator's view, even when explicitly marked as hidden. **Why it matters:** SideQuest's fairness model depends on the narrator only knowing what it's *allowed* to know — if a hidden group action (a secret ambush, a sealed deal) bleeds through, the narrator improvises around information it was never supposed to have, and the illusion of a fair, surprise-preserving game collapses. This was the highest-stakes gap in the system's information firewall.

---

## What Changed

Think of the narrator like a dealer at a poker table who is only allowed to see certain cards. The game already had a "card-covering" step that hid the right cards *for individual players*. But when players took an action *together as a group*, that same card-covering step forgot to run — those cards went straight to the dealer face-up, even if they were supposed to be face-down. This fix adds the missing cover step for group actions, so the dealer only ever sees what the rules say it's allowed to see.

---

## Why This Approach

The fix follows the existing pattern exactly — it mirrors the individual-player filtering loop and applies it to the group-action channel. No new machinery, no new monitoring hooks, no API changes. Every other part of the system already treated individual and group actions symmetrically; the redactor was the lone exception. Closing the gap this way keeps behavior predictable and keeps the fix small enough to verify completely: six tests, all passing, covering the empty case, the fully-hidden case, and the mixed case where some group actions are hidden and some are not.

---
