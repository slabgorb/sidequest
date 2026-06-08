# Narrative

## Problem Statement
**Problem:** Up to 97% of daily Anthropic API spend was invisible to every internal accounting tool. **Why it matters:** When most of the bill can't be seen, you can't tell if costs are trending up, if a bug is running unbounded API calls, or if a configuration change quietly removed cost controls. Silent spending is a structural risk — you only find out when the monthly statement arrives.

---

## What Changed
Think of it like a bank reconciliation for AI spend. Every night, this new system asks two questions: "How much did Anthropic charge us?" and "How much of that can we account for in our own logs?" If those two numbers differ by more than 10%, an alarm goes off — loud.

Three things were built:

1. **A reconciliation script** (`scripts/reconcile_dark_spend.py`) that calls the Anthropic Admin API to get the actual billed amount, asks the running game server for the internally-tracked spend, computes the gap, and fires an error-level alert if the gap exceeds 10%.

2. **A new ledger method** on the server's cost tracker (`SessionCostLedger.instrumented_total_usd()`) that sums up every dollar the server knows it spent — across all game sessions running that day.

3. **Two REST endpoints** on the game server (`GET /api/debug/cost/instrumented` and `GET/POST /api/debug/cost/reconciliation`) that let the script fetch the instrumented total and push its result back so the GM dashboard can display it.

The script exits with code 0 (clean), 1 (gap detected — alert fired), or 2 (couldn't reach the Admin API — something is broken upstream).

---

## Why This Approach
The core principle here is **"no silent fallbacks."** The old state of the world was that billing problems were invisible — the logs never told you what you didn't log. The new approach makes invisibility itself the alarm condition: if billed spend exceeds what we can account for by more than 10%, that gap is the signal.

Using the Anthropic Admin API as the source of truth rather than trusting internal logs exclusively is intentional. Internal logs can have bugs (that's literally what epic 91 is about — the logs were missing 97% of calls). The Admin API is the external, authoritative ledger that doesn't lie.

The 10% threshold rather than 0% acknowledges the real world: there's always a small lag between when API calls happen and when spans are flushed to logs. A 0% threshold would produce constant false alarms; 10% gives real-world breathing room while still catching the "97% invisible" magnitude of the problem this epic was created to fix.

Structuring the reconciliation as a standalone script (rather than embedding it in the server) means it can run as a cron job independently of whether the game server is up, and it fails loudly with a named exit code rather than silently producing bad data.

---
