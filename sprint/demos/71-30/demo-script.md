**Slide 1: Title** — "Telemetry Hygiene: Keeping the Filing Cabinet Clean"

**Slide 2: Problem** — Open with the analogy. The game's telemetry system has two destinations: the live GM panel (whiteboard) and the permanent database (filing cabinet). Rate-limit drop signals were going into the filing cabinet when they belong on the whiteboard.

*Timing: 60 seconds*

**Slide 3: What We Built** — Show the `_EPHEMERAL_EVENT_TYPES` frozenset. Point out the two entries:
```python
_EPHEMERAL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "action_reveal.composing",
        "action_reveal.dropped_rate_limit",
    }
)
```
Explain: "The first entry was the prior fix. The second is this fix. One line, one filing cabinet spill plugged."

*Timing: 60 seconds*

**Slide 4: Why This Approach** — Describe the "whiteboard vs. filing cabinet" doctrine. Show that the infrastructure already existed; this story is wiring it correctly, not inventing anything new.

*Timing: 45 seconds*

**Slide 5: Before/After** — *(See Before/After section below)* Show the before state (rate-limit drops go to database) and after state (rate-limit drops push live only).

*Timing: 45 seconds*

**Live demo (optional):** If a server is running, trigger a rapid burst of action input to fire the rate limiter, then open the GM panel database inspector and show that no `action_reveal.dropped_rate_limit` rows appear in `turn_telemetry`.
- Command to run tests: `uv run pytest tests/telemetry/test_action_reveal_ephemeral_not_persisted.py -v`
- Expected output: `2 passed` — membership test + seam test confirming the event is live-pushed but not persisted.
- **Fallback if demo fails:** Show Slide 5 (Before/After) with the raw numbers from the prior composing-storm incident (session 894: that one event type accounted for 30% of all telemetry rows). Frame this fix as preventative — catching the second leak before it compounds.

**Slide 6: Roadmap** — See Roadmap section below.

**Slide 7: Questions**

---