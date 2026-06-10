# Narrative

## Problem Statement
**Problem:** In WN-family games (Stars/Worlds/Cities/Ashes Without Number), everyone at the table sees combat resolve in real-time order — each player waits to see what happened before deciding their next action. This turns tactical combat into a game of reading the room rather than committing to a plan. And when a target drops mid-round, the engine was silently making decisions it shouldn't: reassigning the now-pointless attack rather than flagging it as a narrative moment.

**Why it matters:** The hallmark of WN-family combat is *blind commitment* — you declare your action before you know what anyone else will do, then fate (dice) determines the order. That tension — "did I swing at a corpse?" — is the drama. Without it, WN combat plays like any other turn-taker. This also directly serves the playgroup's existing submit-and-wait rhythm: what Alex experiences as "patient pacing" is now mechanically meaningful, not just a courtesy.

---

## What Changed
Think of it like a sealed-bid auction. Before this change, players called out their moves one by one and the room adapted in real time. Now the round works in two distinct phases:

**Phase 1 — Everyone writes their name on a folded piece of paper.** Each player picks their action and locks it in. No one knows what anyone else picked yet. The table sees who's ready, but not what they chose.

**Phase 2 — A die decides the order, then the envelopes open one at a time.** Each participant rolls 1d8 and adds their Dexterity bonus. Highest goes first. The game resolves each action in that order — and here's the key part: if your action was "stab the pirate," but the pirate already got cut down two slots before yours, the game doesn't quietly redirect your stab at someone else. It surfaces a *dead premise* flag — the narrator gets to say what your character does when their moment comes and their target is already on the floor.

The player-facing UI reflects this: during the commit phase you see a lock icon next to confirmed actions; during resolution you see the initiative order with rolls visible, then watch events play out in sequence.

---

## Why This Approach
Three reasons this was done inside SideQuest's existing table engine rather than as a separate system:

1. **The plumbing already existed for the social layer.** Alex's protected pacing (everyone submits before narration starts) and the MP session barrier are both already in place. The sealed-commit phase *is* that barrier — the WN engine just rides it rather than reinventing it.

2. **Dead premises must be narrator decisions, not engine guesses.** Auto-redirecting a stale attack is invisible but wrong — it's the engine playing the character. Surfacing a typed event lets the narrator make a real choice in fiction (press a different enemy? dive for cover? the fiction decides) without the engine taking over agency.

3. **All four WN variants share one turn model.** Rather than building separate commit loops for SWN, WWN, CWN, and AWN, the logic lives behind a shared module seam. Space opera, dark fantasy, urban dystopia, and post-apocalyptic all get the same mechanical treatment from one implementation.

---
