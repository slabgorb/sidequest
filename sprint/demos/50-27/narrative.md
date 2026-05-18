# 50-27

## Problem

**Problem:** A quality-gate test that verifies SideQuest's honesty about how it stores game data was failing — not because the code broke, but because the test was checking for an old phrase that no longer appeared in the page. **Why it matters:** This single failing test was blocking a separate, already-approved feature (the A/B evaluation harness, story 48-4) from being merged. Nothing could ship from the `develop` branch while the test suite showed red.

---

## What Changed

Think of it like a smoke detector that was wired to detect the word "fire" — but the warning label on the detector was rewritten to say "flames" instead. The detector still works perfectly; the label just changed. This fix updated the detector to listen for the new word.

Specifically: one line in one test file was updated. The test used to check that the page contained the phrase `"NOT a stored snapshot"`. That exact phrase was reworded in the page itself (to the clearer `"stores no per-round snapshot"`) during an earlier round of improvements — but the test wasn't updated to match. This fix syncs the test to the current page wording. The page itself was not touched.

**One line changed. One file changed. Nothing else.**

---

## Why This Approach

The test exists for a specific reason: to prove that SideQuest is honest with the game master about what data it actually keeps. The game engine doesn't store a complete snapshot of every round — it stores one persistent snapshot and *derives* the rest. If that honesty-contract message ever disappears from the GM panel, a career game master could be misled into trusting derived state as if it were ground truth.

Two options existed:
1. Reword the page back to the old phrase
2. Update the test to match the new (better) phrase on the page

Option 2 was chosen because the page's current wording — *"stores no per-round snapshot"* — is actually a stronger and more explicit statement of the contract than the old wording was. The page is the ground truth; the test's job is to verify the page, not the other way around.

A third candidate phrase existed on line 314 of the HTML, but it contained a typographic "curly apostrophe" character — a fragile target that could break silently if the file encoding ever changed. The team chose the robust plain-ASCII phrase on line 295 instead.

---
