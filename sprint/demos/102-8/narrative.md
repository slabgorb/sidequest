# Narrative

## Problem Statement
**Problem:** After a major engineering sprint (Epic 102), the codebase contained outdated warning labels — comments inside ruleset files and architecture documents saying "not wired" or "deferred" for features that had, in fact, already been shipped. **Why it matters:** These stale labels are landmines. A future developer sees "not wired to dispatch (Plan 3)" in `wwn.py`, believes the feature is missing, and either builds it again (wasted effort) or skips a test because they assume the system won't respond. In a combat system where lives-of-PCs depend on the right code firing, a misleading comment is a reliability risk.

---

## What Changed
Think of it like updating the map after you've finished building the roads.

The engineering team spent Epic 102 building and shipping seven stories of new combat mechanics for the "Without Number" family of game rules (Worlds Without Number, Stars Without Number, Cities Without Number, Ashes Without Number). When each piece shipped, the code worked correctly — but the sticky-note labels inside the files still said "TODO: wire this up" even after it was wired. Similarly, the architecture decision log (`DRIFT.md`) still listed these features as deferred.

This story was a focused cleanup pass:
- **Before:** `wwn.py`, `swn.py`, and `cwn.py` contained comments like `# not wired to dispatch (Plan 3)` next to `apply_killing_blow` — even though `apply_killing_blow` had been live and fully wired at `dice.py` lines 644 and 725 since earlier in the sprint. `veterans_luck` was similarly labelled as unwired despite having a functioning narrator tool.
- **After:** Every `# not wired` / `# deferred` marker that no longer reflects reality has been removed or corrected. `DRIFT.md` and the WN plan documents now accurately describe which features are live vs. genuinely still pending.

---

## Why This Approach
Documentation drift is a form of technical debt that compounds silently. When a comment says a feature is deferred and it isn't, every subsequent reader has to do extra investigation to trust their own understanding of the system. This is especially costly in a project like SideQuest, where the GM panel's OTEL telemetry is the primary lie-detector for whether game mechanics are actually firing — if a developer doesn't trust the code comments, they can't quickly verify whether a span is missing because it's broken or because it was never wired.

The two-point scope was deliberate: this was not a feature story, not a refactor, and not a bug fix. It was a **hygiene pass** — surgical removal of stale labels with no behavioral change. Keeping it small and targeted ensures there's no risk of accidentally altering behavior while cleaning up prose. It also closes the gap between what the team built and what the documentation says they built, which directly unblocks future developers working in this module.

---
