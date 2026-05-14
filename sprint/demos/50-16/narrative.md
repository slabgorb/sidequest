# 50-16

## Problem

Problem: Every clue and piece of lore a player's character discovers was being labeled "Suspected" — permanently — regardless of how solid the evidence actually was. Why it matters: the in-game journal is supposed to track what your character knows and how confident they are: a wild rumor, a reasonable deduction, or a hard fact. With this bug, everything was pinned at "Suspected" forever, making the journal useless as a reliability guide and meaning the narrator's judgment about evidence quality was silently thrown away before it ever reached the player's screen.

---

## What Changed

Think of the journal like a detective's case board. Facts get pinned to it at two moments: once when the narrator first mentions them mid-scene (a quick sticky note — provisional, labeled "Suspected" until we know better), and again when the server sends an authoritative verdict after the turn resolves (the real evidence card, with the actual confidence level the game engine assigned).

Before this fix, the second card — the authoritative one — would arrive, get filed, and then get ignored: the UI kept the "Suspected" sticky note no matter what confidence level the server sent. The game could decide a clue was "Certain" or "Rumored"; the journal showed "Suspected" either way.

After this fix, the journal does what it always should have: the provisional sticky note defaults to "Suspected" while you're waiting, and when the server's authoritative verdict arrives it overwrites the sticky note with the real answer. Certain things look certain. Rumors look like rumors. The journal now tells the truth.

---

## Why This Approach

The fix has a clean two-stage contract that mirrors how the information actually flows through the system:

1. **Provisional stage** — when the narrator finishes a turn, new facts go into the journal immediately so players see them without delay. These correctly default to "Suspected" — we haven't gotten the server's verdict yet.
2. **Override stage** — when the server sends its `JOURNAL_RESPONSE` (the authoritative pass), any fact the server knows about replaces the provisional entry entirely, not just the confidence label — content, source, and evidence category all come from the authoritative record.

This keeps the journal responsive (no waiting for the server before displaying new clues) while keeping it accurate (the server's judgment always wins). The alternative — waiting for the server before showing anything — would create a visible delay mid-scene. The alternative — never overriding the provisional — was the bug.

A safety net was added for the edge case where the server sends a confidence value the UI doesn't recognize: the validator falls back to "Suspected" and logs a warning rather than crashing or silently accepting garbage data.

---
