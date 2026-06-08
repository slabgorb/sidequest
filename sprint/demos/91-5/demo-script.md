**Total runtime: ~12 minutes**

---

**Slide 1: Title — [1 min]**
Open with the framing: "Last week we found that roughly 97% of our Anthropic API bill was invisible to every cost tool we had. Today I'm going to show you the detector we built to make sure that never quietly happens again."

---

**Slide 2: Problem — [2 min]**
Reference the specific discovery: on June 4th, the system logged 575 Haiku API calls across a 70-turn game session — roughly 8 calls per turn when 1 was expected — and zero of those calls emitted a cost span. The daily Haiku bill was running $3.30–$3.50/day with a 4x spike on June 3rd. None of it was visible in any internal log table.

Show this concrete number: **97% of spend had no log line.**

---

**Slide 3: What We Built — [3 min, live demo]**

Run the reconciliation script live against the server:

```bash
export ANTHROPIC_ADMIN_KEY=sk-ant-admin-...
python scripts/reconcile_dark_spend.py --days 1
```

Point out the three output lines:
- `Reconciliation: billed=$X.XXXX instrumented=$Y.YYYY gap=Z.Z% alert=False`

If the demo is clean (gap ≤ 10%), say: "This is what success looks like — we can account for what we're spending."

To show what an alert looks like, explain the exit code behavior: exit 0 = clean, exit 1 = gap detected, exit 2 = can't reach Admin API.

To simulate an alert for demo purposes without real data, show the test:
```bash
cd sidequest-server && uv run pytest tests/agents/test_91_5_ledger_instrumented_total.py -v
```
Expected output: all 7 tests passing, including `test_instrumented_total_usd_sums_all_sessions`.

**Fallback if live demo fails:** Switch to Slide 3 static screenshot. Say: "The script ran in CI — here's the reconciliation output from this morning's run."

---

**Slide 3 continued: GM Dashboard — [2 min]**

Open the GM dashboard at `http://localhost:8765/dashboard`. Navigate to the cost panel. Show the `GET /api/debug/cost/instrumented` response:

```bash
curl http://localhost:8765/api/debug/cost/instrumented
# {"instrumented_usd": 0.1423, "session_count": 3}
```

Then show the reconciliation result stored on the server:
```bash
curl http://localhost:8765/api/debug/cost/reconciliation
# {"instrumented_usd": 0.1423, "billed_usd": 0.1501, "gap_pct": 5.2, "alert": false}
```

Point out: "The dashboard now has a live feed of whether our accounting is clean."

---

**Slide 4: Why This Approach — [2 min]**
Walk through the three-layer structure: (1) what we think we spent (instrumented spans from 91-1), (2) what Anthropic says we spent (Admin API), (3) the gap. Say: "We trust the Admin API over our own logs by design — internal logs can have bugs; the billing ledger can't."

Explain the 10% threshold with this framing: "Zero tolerance would page every night. Ten percent gives real-world breathing room while still catching the 97% problem that started this work."

---

**Roadmap slide — [1 min]**
Point to the cron integration next step and the sibling local-routing epic.

---

**Questions — open**

---