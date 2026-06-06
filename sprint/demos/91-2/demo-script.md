**Total runtime: ~8 minutes**

**Scene 1 — Set the stage (Slide 2: Problem), ~1.5 min**
Open with the cost forensics dashboard from the Admin API or the GM panel OTEL view. Show a pre-fix session trace. Point to the Haiku call count per turn and say: "Each one of these dots is a Haiku API call. A healthy turn should have two or three. This session had eight per turn, every turn." If live OTEL isn't available, fall back to Slide 2 with the annotated screenshot of the caller-tag breakdown.

**Scene 2 — Show the attribution (Slide 3: What We Built), ~2 min**
Run the sq-llm-costs report or show the caller-tag summary from story 91-1's instrumentation:
```bash
uv run python -m sidequest.telemetry.llm_cost_report --session <session_id> --group-by caller
```
Walk through the output table. Point to the rows with the highest call counts. Say: "Before 91-1, this table didn't exist. Now we can see exactly which subsystem is responsible for each call." Highlight the offending caller(s) — likely the intent router retry path or a fan-out classification step.

**Scene 3 — Before/After (Before/After slide), ~2 min**
Show two side-by-side OTEL traces or the call-count table:
- **Before:** 8 Haiku calls/turn, unattributed, no ceiling
- **After:** 2–3 Haiku calls/turn, each tagged, assertion fires if count exceeds budget

If the live system isn't available, show the static diff of the assertion added to the turn pipeline — a single `assert haiku_call_count <= HAIKU_BUDGET_PER_TURN` line with a clear error message.

**Scene 4 — The assertion in action (Slide 3 continued), ~1.5 min**
Trigger a synthetic turn and show the OTEL span confirming the call count is within budget. If a live demo isn't feasible, show the test output:
```bash
cd sidequest-server && uv run pytest tests/ -k "haiku_budget" -v
```
Expected output: `PASSED tests/test_haiku_budget.py::test_per_turn_call_count_within_budget`

**Fallback:** If any live step fails, jump to the Before/After slide and walk through the static numbers.

---