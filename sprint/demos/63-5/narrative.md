# 63-5

## Problem

Problem: The v3 reference pages shipped without a way to verify that a genre pack is correctly configured for the new chrome system, and the rules reference pages were accidentally rendering trope content that belongs only to Game Masters.

Why it matters: A pack author adding a new genre (or updating an existing one) had no automated check to catch missing theme fields — they'd discover the gap only when the page rendered broken in production. Separately, players visiting rules reference pages were seeing GM-side trope tables that were never intended to be player-facing.

---

## What Changed

Three things got cleaned up as the final gate before epic 63 closed:

**1. A new safety check for pack authors.** There's now a command — `just content-validate` — that walks every live genre pack and checks whether its visual configuration file (`theme.yaml`) has all the fields the v3 reference page renderer needs. If anything is missing, the command prints a loud `[FAIL]` with the exact field name and exits with an error. Nothing is guessed or silently skipped.

**2. Tropes removed from player-facing reference pages.** The reference renderer was accidentally treating `tropes.yaml` (the GM's escalation mechanics) the same as rules files — so trope tables were showing up on pages meant for players. One three-line change moved tropes to the excluded list. Players no longer see GM-only mechanical content on reference pages.

**3. A dead code entry cleaned up.** The renderer had an old lookup that mapped "tropes" to a display label — but since tropes no longer render, that lookup was orphaned. It was removed as part of the tropes exclusion, and the test that had been checking for it was updated to match.

A fourth task (staging design-bundle screenshots to cloud storage) turned out to be a no-op: the screenshot directory never existed in the repository, so there was nothing to move.

---

## Why This Approach

**The validator wraps existing code, not new logic.** The renderer already had a function (`load_reference_theme`) that knew which fields were required and would raise a loud error if any were missing. The new CLI command is a thin shell around that same function — so "what fields are required" is defined in exactly one place, and the validator and the renderer can never disagree. Duplicating the field list into a separate validator would have been a latent bug waiting to happen.

**The exclusion mechanism already existed.** The reference renderer already had an `EXCLUDED_FILES` list for files that should never render (e.g. NPC tables, seed data). Adding `tropes.yaml` to that list required three lines and zero new infrastructure. The right fix was the minimal one.

**No silent fallbacks, anywhere.** A genre pack with a broken `theme.yaml` doesn't render with defaults — it fails loudly with the field name. This is a deliberate project rule: silent alternatives mask configuration problems and lead to hours of debugging "why isn't this quite right."

---
