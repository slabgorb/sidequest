**Deck structure:** Slide 1 (Title) → Slide 2 (Problem) → Slide 3 (What We Built) → Slide 4 (Why This Approach) → Slide 5 (Before/After) → Slide 6 (Roadmap) → Slide 7 (Questions)

---

**Scene 1 — Open (0:00–0:45) | Slide 1: Title**

Open with the title slide. Deliver one sentence: "We added an alarm that makes sure the AI narrator can always find newly-introduced characters — and that the alarm actually bites if the protection breaks."

---

**Scene 2 — Problem Setup (0:45–2:00) | Slide 2: Problem**

Walk through the problem. Reference the post-office analogy. The key data point to anchor: the broken behavior was **silent** — no error, no crash, just a character the narrator quietly couldn't find. Ask the audience: "How would you know?" That's the setup for why the fix alone wasn't enough.

*Fallback if live demo unavailable: stay on Slide 2 and describe the scenario verbally using "Borin, a new character just introduced with no backstory" as a concrete example.*

---

**Scene 3 — Live Demo (2:00–4:30) | Slide 3: What We Built**

Run the test suite from the terminal to show the guard in action.

```bash
cd sidequest-server
uv run pytest tests/server/dispatch/test_lore_embed.py -v
```

Expected output to call out:
```
tests/server/dispatch/test_lore_embed.py::test_dispatch_worker_spawns_on_entity_only_turn PASSED
```

Then show the guard biting. Temporarily revert the dispatch gate to its broken state and re-run:

```bash
# (pre-staged broken version — swap in lore-only gate)
uv run pytest tests/server/dispatch/test_lore_embed.py::test_dispatch_worker_spawns_on_entity_only_turn -v
```

Expected output: `FAILED` — point out the exact assertion that fires: `assert isinstance(sd.embed_task, asyncio.Task)`. Say: "This is the alarm going off. The system caught it before any human had to."

Restore the fixed gate, re-run, show GREEN. Takes 30 seconds total.

*Fallback if test environment unavailable: skip to Slide 5 (Before/After) and use the static diff screenshot.*

---

**Scene 4 — Approach rationale (4:30–5:30) | Slide 4: Why This Approach**

This is a one-liner: "We proved the alarm bites by breaking the fix on purpose, watching it fail, then restoring the fix." Reference the before/after. Note that zero production code changed — this is purely defensive.

---

**Scene 5 — Before/After (5:30–6:00) | Slide 5: Before/After**

Point to the comparison. Keep it brief; the live demo already showed it.

---

**Scene 6 — Roadmap (6:00–7:00) | Slide 6: Roadmap**

Two follow-ups logged for epic 76 (both non-blocking for this story):
1. Add a complementary test for the "both stores empty" case — the other side of the gate.
2. Close a test-configuration hygiene gap for future tests that run the worker fully.

Emphasize: neither blocks this story; both are minor hardening.

---

**Scene 7 — Questions (7:00+) | Slide 7: Questions**

---