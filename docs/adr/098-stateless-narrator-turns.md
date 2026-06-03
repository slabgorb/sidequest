---
id: 98
title: "Stateless Narrator Turns — Drop --resume, Bounded Per-Turn Prompts"
status: accepted
status_rationale: "Brainstorm + spec + plan completed; supersedes ADR-066 which proved load-bearing in the opposite direction over long sessions."
date: 2026-05-10
deciders: ["Keith Avery"]
supersedes: [66]
superseded-by: null
related: [67]
tags: [agent-system, narrator]
implementation-status: live
implementation-pointer: null
---

# ADR-098: Stateless Narrator Turns — Drop --resume, Bounded Per-Turn Prompts

## Status

Accepted (2026-05-10). Supersedes ADR-066.

## Context

ADR-066 introduced persistent `--resume` Claude sessions per game to amortise cost
and preserve continuity. The premise was a spike result: warm-cache resume reduced
turn latency from ~22s to ~6s. In production the opposite outcome emerged. Anthropic-side
session memory accumulates every turn's conversation, so each subsequent turn replays a
growing history. Latency scaled with turn count; Playtest 3 ended in a server crash when
the session crossed the CLI's context budget and returned `context_window_full`.

The Amendment added to ADR-066 (2026-05-04) patched around the symptom: proactive
rotation (§7), hardened reactive fallback (§8), and a recap-bearing warm-reboot frame
(§9) — roughly 155 lines of recovery scaffolding. The scaffolding paper over the root
cause without removing it.

A deeper structural problem: `build_narrator_prompt` already re-injects full ground
truth every turn — NPC roster, chassis voices, party peers, game state, magic context,
recency-zone guardrails. These injections exist precisely because we do not trust the
model's session memory. The system was paying twice: for `--resume` (theoretically
buying a latency win) and again for per-turn re-injection (to undo session-memory drift).
Hidden growth — Anthropic-side session history we cannot inspect, trim, or audit —
compounded visible state-section growth and made `prompt_assembled` OTEL an incomplete
lie detector.

## Decision

Every narrator turn becomes a stateless `claude -p` call with no `--resume` and no
`--session-id`. No conversation history, no Full/Delta tier distinction, no recovery
scaffolding. The prompt is partitioned into a stable `system_prompt` (narrator identity,
voice, SOUL principles, output format — sections that are byte-identical across every
turn of the same game given fixed operator settings) and a turn-dynamic `user_message`
(NPC roster, party peers, game state, world context, retrieved lore, magic context,
active tropes, encounter context, recency-zone guardrails, player action). Prompt size
is bounded by section selection, not tier gating.

A retry-once policy replaces the §8 recovery scaffolding. Transient subprocess failure
(network blip, spawn failure, timeout) retries once with a fresh subprocess and the same
prompt. Malformed response gets no retry — retrying the same prompt gives the same broken
output. On unrecoverable failure the turn returns a degraded `NarrationTurnResult`
("The world holds its breath...") and the game continues. Turn counter is not advanced;
the player can retry.

Migration is bigbang. No feature flag, no per-save fallback. Saves carrying
`narrator_session_id` load with the field ignored.

Three properties follow by construction:

- **Bounded cost.** Prompt size is a function of current world scope, not turn count.
  Latency stays flat across long sessions.
- **No `context_window_full` crashes.** Structurally impossible. Worst case is a single
  oversized turn — a diagnosable bug, not a session collapse.
- **Complete OTEL audit.** `prompt_assembled` is the whole truth of what the model saw.
  The GM panel becomes a true lie detector with no hidden state. Every turn emits
  `prompt_assembled` with `system_len`, `user_len`, and `bounded: true`; the `tier`
  field is removed.

## Consequences

- `NarratorPromptTier`, `select_prompt_tier()`, `reset_narrator_session()`,
  `set_narrator_session_id()`, and the full §8 recovery scaffolding (~155 lines) are
  deleted from `orchestrator.py`.
- `build_narrator_prompt()` loses the `tier` and `rebuild_header` parameters. All
  `if is_full:` gates become unconditional.
- `process_action()` loses `is_first_turn` branching, the system_prompt swap, and the
  session-id read/write block.
- `narrator_session_id` field removed from save schema. Old saves with the field load
  with it ignored.
- A hard-budget guard (`PROMPT_BUDGET_BYTES_HARD ≈ 2_000_000`) refuses the SDK call
  when `len(system_prompt) + len(user_message)` exceeds the threshold. **Amended
  2026-05-23 by story 61-3** — was originally a soft canary that logged
  `logger.warning` and let the turn execute. Post-61-3 the same threshold becomes a
  hard refuse: `_check_oversized_prompt()` at `sidequest-server/sidequest/agents/orchestrator.py`.
  Constant was named `SOFT_PROMPT_BUDGET_BYTES` until renamed by 61-8 §C1 (the soft
  framing was misleading after the 61-3 promotion).
  returns `True` to make the caller short-circuit the SDK call, emits watcher event
  `prompt_oversized_hard` with `severity="error"`, and logs at `logger.error` level
  (`action=refuse`). The refused turn renders a distinct degraded line
  (`"[narrator-overload — operator paged]"`) so session-recording grep can
  distinguish budget-refuse from SDK-error-refuse. The original cost-runaway
  incident (2026-05-23, ~$313 in 48h) burned through a SOFT warning that
  scrolled past unread overnight; the LOUD hard refuse is the operator-page that
  the original ADR-098 §Bound canary section described as "canary, not circuit
  breaker." It is now a circuit breaker.

## Implementation

See plan: `docs/superpowers/plans/2026-05-10-stateless-narrator.md`. Implementation
landed across:
- sidequest-server: `feat/stateless-narrator-adr-098` branch (Tasks 1–17)
- sidequest-ui: `feat/stateless-narrator-adr-098` branch (Task 18)
- orchestrator: `stateless-narrator-adr-098` branch (this ADR)
