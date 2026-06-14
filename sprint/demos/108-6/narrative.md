# Narrative

## Problem Statement
**Problem:** When a player character drops to zero hit points in a Without-Number (WWN) rules session, the game immediately declares them dead — no window, no chance to fight for survival. The WWN rulebook says there should be a d6-round "dying window" where the character is mortally wounded but not yet gone, giving them (and their allies) a brief, desperate chance to stabilize.

**Why it matters:** This missing window collapses a pivotal dramatic moment into nothing. In the tabletop original, "mortally wounded" is one of the most memorable states in the game — the clock is ticking, choices have weight, and survival is genuinely uncertain. SideQuest was skipping it entirely and going straight to the death screen. For a game built around delivering the depth of a real tabletop session, a missing death-save window is a gaping hole in genre fidelity.

A second, harder problem surfaced during design: in solo play, nothing can advance that clock once the player is down. Input is disabled for an incapacitated character, so a "d6-round countdown" with no mechanism to tick it forward is just a permanent frozen state — worse than no clock at all.

---

## What Changed
The engine now treats "going to zero HP" as the beginning of a sequence rather than the end of the story:

1. **Mortally wounded status** — when a PC hits zero with no live enemy still standing, the game mints a new status: mortally wounded. The character is incapacitated but not dead.
2. **A player-driven clock** — the solo-actuator problem is solved by letting the player's own free-text submissions tick the clock. Each action the downed player submits ("I try to press my hand against the wound," "I call out for help") counts as a round. The engine tracks how many rounds have elapsed.
3. **Escalating difficulty** — stabilizing gets harder each round (difficulty = 8 + rounds elapsed). The longer you wait, the worse it gets.
4. **Two branches at the moment of collapse:**
   - **Enemy still standing** → terminal death immediately. You don't get a last stand at sword-point.
   - **No live enemy** → the dying window opens. You have a chance.
5. **Expiry fires automatically** — when the round limit runs out without a successful stabilize, the engine transitions to terminal dead. No frozen states.

The fix also closes a long-standing debt: cancelled story 106-5 promised this dying-window work would be folded in "later." It's now done.

---

## Why This Approach
The core insight is that the player is the actuator. In solo play there's no party member to stabilize you — but there *is* a player typing. Every submission they make represents a round of desperate action. This turns a mechanical problem (who ticks the clock?) into a design feature: the player is fighting for their character's life through the words they type.

The engine cross-checks its own round count against any value the narrator reports, failing loudly if they diverge. This prevents the narrator from quietly fudging the timeline — a clock that can be silently overridden isn't a clock at all.

The "enemy still present → instant death" branch preserves WWN's actual intent: the dying window is a quiet-battlefield mechanic, not a license to crawl away while someone is still swinging at you.

---

## Before/After
| | Before (pre-108-6) |After (108-6) |
|---|---|---|
| **PC hits 0 HP, no live enemies** | `terminal_dead` fires immediately | `mortally_wounded` status created; dying window opens |
| **Player input while downed** | Blocked (incapacitated gate) | Permitted for stabilizable window; each submission ticks the clock |
| **Clock mechanics** | None | Engine-derived round count; narrator-supplied value cross-checked; fail-loud on mismatch |
| **Stabilization difficulty** | N/A | `8 + rounds_elapsed`; climbs each round |
| **Deadline expires** | N/A (no window) | Transition fires to terminal dead automatically |
| **PC hits 0 HP with live enemy present** | `terminal_dead` fires immediately | `terminal_dead` fires immediately (unchanged — no last stand at sword-point) |
| **Solo play viability** | Broken (no actuator for any future clock) | Player submissions ARE the clock; no external actuator needed |
| **106-5 dying-window debt** | Cancelled, promised to fold in later | Delivered |
