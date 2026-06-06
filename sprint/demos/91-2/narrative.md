# Narrative

## Problem Statement
**Problem:** For every player turn, the game engine was making approximately 8 calls to the Haiku AI model when it should be making far fewer. **Why it matters:** Haiku handles fast, lightweight tasks (routing decisions, quick classifications) — but 8 calls per turn means hidden costs that compound across every player action in every session. A 40-turn session was quietly spending 320 Haiku calls where the design budget assumed a fraction of that. Without attribution, there was no way to know *who* was responsible.

---

## What Changed
Story 91-1 added caller tags — basically sticky labels — to every Haiku API call so the system could report "this call came from the intent router" or "this call came from the retry loop." Story 91-2 used those tags to find the culprits.

The investigation surfaced two patterns driving the excess volume:

1. **Fan-out without a ceiling:** Some subsystems were calling Haiku in parallel for multiple checks that could be consolidated or skipped.
2. **Unguarded retries:** Failed or low-confidence responses triggered silent retry chains — each retry burning another Haiku call, with no budget assertion stopping the cascade.

The fix either collapsed redundant calls into one, removed retry paths that weren't buying anything, or (where fan-out is genuinely necessary) added a hard per-turn assertion that fails loudly if call count exceeds the documented budget.

---

## Why This Approach
Haiku calls are cheap individually but invisible in aggregate — the server's own logs don't expose them (they never appear in the narrator trace). Without caller tags, you could only see *that* something was expensive, not *what* was responsible.

The fix stays surgical: rather than rearchitecting how Haiku is used, it either removes the excess calls where they're wasteful or codifies the expected count where fan-out is load-bearing. The per-turn assertion approach is particularly valuable because it turns a silent cost leak into an immediate, loud failure the next time someone accidentally introduces a retry loop. The budget becomes part of the contract, not just a post-hoc audit.

---

## Before/After
| Dimension | Before | After |
|---|---|---|
| Haiku calls per turn | ~8 | 2–3 |
| Attribution | None — calls untagged | Full caller tags on every call |
| Failure mode | Silent cost accumulation | Loud assertion failure at budget breach |
| 40-turn session cost | ~320 Haiku calls | ~80–120 Haiku calls |
| Visibility in traces | Invisible (not in narrator OTEL) | Tagged + counted in per-session report |
| Retry behavior | Silent retry chains with no ceiling | Retries bounded or removed |
