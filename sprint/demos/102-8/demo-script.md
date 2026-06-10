**Audience:** Engineering leadership, product owner, sprint reviewers.
**Duration:** ~6 minutes.
**Format:** Side-by-side diff view + DRIFT.md before/after.

**Slide 1 — Title (0:00–0:30)**
Open with the slide. Say: "This story is a two-pointer that closes out Epic 102. It's about documentation, not behavior. No game logic changed — but the map finally matches the territory."

**Slide 2 — Problem (0:30–1:30)**
Point to the before snippet. Say: "Here's `wwn.py` as it existed before this story. Line 42 reads `# not wired to dispatch (Plan 3)` right above `apply_killing_blow`. That method has been live — wired at `dice.py:644` and `dice.py:725` — since story 102-1 shipped on June 10th. Any developer reading this comment today would waste hours trying to find a gap that doesn't exist."

**Slide 3 — What We Built (1:30–2:30)**
Show the diff. Say: "The change is simple: we removed the stale markers from `wwn.py`, `swn.py`, and `cwn.py`, and updated `DRIFT.md` to reflect the post-102 state of the WN module family. `veterans_luck` now correctly notes it has a narrator tool rather than being labelled deferred."

**Slide 4 — Why This Approach (2:30–3:30)**
Say: "We kept this strictly non-behavioral. No logic touched, no tests changed for behavior, no new code added. The PR is safe to review in under ten minutes. The payoff is that the next developer who opens `wwn.py` gets an accurate picture of what's live — and that protects the reliability work the whole sprint delivered."

**Before/After slide (3:30–4:30)**
Live terminal fallback:
```bash
grep -n "not wired\|deferred" ../sidequest-server/sidequest/game/ruleset/wwn.py
```
If the file is clean, the command returns nothing — that's the demo. Say: "No output. The stale markers are gone."

If that command fails or the repo isn't checked out, fall back to Slide 5 (Before/After) and walk through the diff screenshot.

**Roadmap slide (4:30–5:30)**
Say: "Epic 102 delivered seven stories. This is the eighth and final one — it retires the last paper debt from the sprint. Stories 102-5 (narrator tool contract) and 102-6 (psionics) are still in the backlog but represent genuine future work, not documentation lag."

**Questions (5:30–6:00)**

---