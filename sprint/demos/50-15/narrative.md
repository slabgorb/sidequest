# 50-15

## Problem

**Problem:** The player Knowledge Journal was silently assigning its own made-up tracking numbers to discovered facts instead of using the identifiers the game narrator provides. **Why it matters:** When the same clue or piece of lore appeared through two different delivery paths — once when discovered mid-scene, and again when the journal was explicitly queried — the game treated them as two separate facts. Players saw duplicate entries in their journal, and the journal's memory of what was already known could not be trusted.

---

## What Changed

Imagine the narrator is a detective's notebook that gives every clue a unique case number. Before this fix, when a clue arrived at the front of the house (the UI), a doorman was crossing out the narrator's case number and stamping his own — `"Turn 3, footnote 2"` — on the envelope. That doorman-stamp changed every single turn, so the same clue coming in twice got two different stamps and ended up filed twice.

This fix fires the doorman. The UI now reads whatever case number the narrator wrote on the envelope and uses that, unchanged, forever. If an envelope arrives without any case number at all (meaning the narrator's pipeline had a problem), it's flagged and set aside rather than guessed at.

---

## Why This Approach

The narrator (the AI game engine) is the single source of truth for what a fact *is*. Letting the UI invent its own IDs was a design inversion — the front end was overriding the back end's identity system. The fix is a one-way alignment: the UI adopts the narrator's ID, full stop. Any footnote that arrives without an ID is treated as a data integrity signal (a loud warning, not a silent workaround), which keeps the pipeline honest. This also closes the gap between two message types — live narration footnotes and explicit journal responses — so they can now share a single deduplication ledger.

---
