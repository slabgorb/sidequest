# 71-8

## Problem

**Problem:** A type-checking error existed in the game server's magic reference presenter — a variable named `rows` was used first to hold a single HTML text string, then later in the same function to hold a list of strings. The type-checker (pyright) correctly flagged this as contradictory and refused to validate the file cleanly.

**Why it matters:** Pyright errors in the codebase are silent landmines. They don't break the running game today, but they tell future developers "this code is type-unsafe here" — which means the type-checker stops being a reliable safety net. If errors accumulate, the tool becomes noise and gets ignored, and that's when real bugs start slipping through uncaught.

---

## What Changed

Think of it like a mislabeled folder at the office. Someone put a single sticky note into a folder labeled "Stack of Reports." The filing system (pyright) complained: "a sticky note is not a stack of reports." The fix was simple — give the sticky note its own correctly-labeled folder: rename the variable from `rows` (which sounds like "a list of things") to `limit_rows` (which clearly means "a single line of hard-limit text"). The list that legitimately deserved the name `rows` kept it. One variable rename, two lines changed, zero behavior change.

---

## Why This Approach

The cleanest fix for a name collision is to give one of the colliding names a more precise, descriptive name. `limit_rows` is actually a *better* name than `rows` for what it holds — a formatted HTML string representing a magic system's hard limits. Alternatives like suppressing the error with a `# type: ignore` comment would silence the warning without fixing the underlying ambiguity, which is exactly the kind of debt we want to eliminate, not paper over.

---
