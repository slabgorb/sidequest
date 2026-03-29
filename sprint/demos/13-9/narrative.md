# 13-9

## Problem

**Problem:** When a player went AFK or was too slow to submit their turn action before the timer expired, the game silently proceeded as if everyone had acted — ignoring the timeout entirely. **Why it matters:** Players watching the narration had no idea why certain characters did nothing, and the AI narrator had no knowledge that some actions were involuntary or absent — leading to incoherent story narration and a confusing multiplayer experience.

---

## What Changed

Think of it like a board game where if a player doesn't move in time, the referee makes a move for them and announces it to the table. Before this fix, the referee just... did nothing, and the game pretended everyone moved normally.

Now:
1. **The timer actually does something.** When it expires, the game detects which players didn't submit.
2. **Missing actions are filled in automatically.** Each silent player gets a placeholder action — "hesitates, waiting" — inserted on their behalf.
3. **Everyone is notified.** A broadcast goes out to all players in the session saying who was auto-resolved and what default action was used.
4. **The narrator is informed.** The AI storyteller now knows the difference between "this character chose to wait" and "this player actually submitted an action" — so the narration reflects reality.

---

## Why This Approach

The timeout detection code already existed — it returned a `timed_out` flag. The bug was that nothing downstream ever *checked* that flag; both paths (everyone submitted vs. timeout fired) ran the same code. The fix is minimal and surgical: branch on `timed_out`, call the existing `force_resolve_turn()` mechanism for missing players, then thread the auto-resolution metadata into the narrator context. No new architecture — just connecting wires that were already there.

The "hesitates, waiting" default text is intentionally neutral. It gives the narrator something grammatically coherent to work with without inventing player intent.

---
