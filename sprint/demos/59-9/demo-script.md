# Demo Script — 59-9

**Slide 1: Title** — Introduce the story: "A one-point fix that closes the highest-stakes hole in our information firewall."

**Slide 2: Problem** — Walk through the poker-table analogy. Emphasize the word *secret*: this is about whether the narrator can be trusted to narrate fairly when the players are keeping secrets from each other or from it.

*Timing: ~90 seconds.*

**Slide 3: What We Built** — Show the before/after table (see section below). Point out: "One new loop, three new tests, zero regressions across 1,143 checks."

*Timing: ~60 seconds.*

**Slide 4: Why This Approach** — "We didn't reinvent anything. Every other part of the engine already treated individual and group actions the same way — we just made the redactor match."

*Timing: ~45 seconds.*

**Before/After slide** — Show the comparison (see below). If doing a live demo, run:

```bash
cd sidequest-server
uv run pytest tests/agents/test_prompt_redaction.py -v
```

Expected output: `6 passed` — three pre-existing individual-player tests plus three new group-action tests. If the command fails, switch to the Before/After slide and walk through the table verbally.

*Fallback: show the Before/After slide and read the "After" column aloud.*

**Roadmap slide** — "The fix closes the primary hole. A follow-up story will harden the lie-detector — our OTEL audit log — so it also watches group-action channels, not just individual ones."

**Questions.**

---
