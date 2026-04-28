# 45-3

## Problem

Problem: During confrontations, the momentum dial shown to players displayed the wrong number until after narration finished — sometimes several seconds after the dice were resolved. Why it matters: Sebastien, the mechanical-minded player in our primary playgroup, relies on the momentum meter as his primary feedback loop in combat. When the dial lies — showing pre-roll momentum while narration is already describing the result of the roll — the system looks broken and untrustworthy. For a player whose engagement is specifically around knowing the numbers, a lagging readout is not a cosmetic issue; it's a fundamental trust failure.

---

## What Changed

Think of a sports scoreboard that only updates at halftime, even though the goal was scored minutes ago. That was the momentum dial.

Before this fix: a player throws dice, the game resolves the beat, the narrator starts describing what happens — but the momentum meter on screen still shows the old value. The number only snapped to the correct reading after the narrator finished talking.

After this fix: the moment the dice resolve, the server sends the updated momentum value directly to the screen. The dial updates *before* the narrator says a word. The player sees the true number in real time, exactly when the dice land.

Nothing about how momentum is calculated changed. The fix was simply making sure the server broadcasts the result to the right place at the right moment — and twice (once on dice resolution, once after narration) so the dial stays correct across the full turn.

---

## Why This Approach

The server already knew the correct momentum value the instant the dice resolved. The UI already knew how to show it when a CONFRONTATION message arrived. The two pieces just weren't connected at the right point in the pipeline.

The fix wired an existing message type — already used elsewhere for confrontation state — into the dice-resolution path. No new data format, no new UI component, no new calculation. It plugged the existing infrastructure into the gap rather than building a parallel system.

A second connection point (after narration) was also confirmed and made observable. Both updates now emit telemetry events that the GM panel can inspect, making it possible to verify in real time that momentum is being communicated correctly — and to distinguish a dice-driven update from a narrator-driven one.

---
