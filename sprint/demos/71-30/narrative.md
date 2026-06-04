# Narrative

## Problem Statement
Problem: A specific live-status signal — a "rate limit drop" notification that fires when the game throttles rapid player input — was being permanently written to the database even though it carries no lasting diagnostic or mechanical value. Why it matters: Every keystroke-level signal that gets written to the database is wasted storage, wasted write operations, and noise that crowds out the records that actually matter for debugging and game forensics.

---

## What Changed
Think of the game's telemetry system like a whiteboard next to a filing cabinet. Some information belongs on the whiteboard — it's momentary, like "this player is currently typing" or "this message got briefly throttled." Other information belongs in the filing cabinet — permanent records of real decisions and mechanical outcomes.

We had already identified one whiteboard-only signal (the "player is composing" indicator) and moved it off the permanent-record list during a prior fix. But its sibling — a signal that fires when a rapid burst of input gets rate-limited — was still going into the filing cabinet. This fix adds that signal to the "whiteboard only" list, so it broadcasts live to the Game Master panel but is never written to disk.

---

## Why This Approach
The system already had the infrastructure to handle this correctly — a small set called `_EPHEMERAL_EVENT_TYPES` that marks specific signals as live-push-only. The prior fix (the "composing storm" fix) established the pattern, validated it, and proved it safe. This fix is a direct sibling: same mechanism, same reasoning, one more entry in the list.

The alternative — persisting these signals — would mean every time a rapid-fire player triggers the throttle, the system writes a database row with zero diagnostic return. The fix is minimal, surgical, and follows the exact pattern already tested and approved.

---

## Before/After
| | Before | After |
|---|---|---|
| `action_reveal.dropped_rate_limit` event fires | Broadcast to GM panel **and** written to `turn_telemetry` database table | Broadcast to GM panel only — database write suppressed |
| Player triggers rate limiter repeatedly | One database row per throttle event | Zero database rows; live signal only |
| GM forensics query on a session with heavy typing | Results include rate-limit noise rows | Results contain only mechanically meaningful events |
| Test coverage | No test for this specific event's persistence behavior | Two tests: membership in ephemeral set + seam test confirming live-push-only behavior |
