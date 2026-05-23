# Handoff: implement -> review
**Story:** 61-3 — Hard-cap oversized-prompt canary
**Agent:** dev
**Timestamp:** 2026-05-23

## Summary

Promoted the oversized-prompt canary from SOFT (warn + proceed) to HARD
(refuse + loud emit) on both narration paths. Closed TEA's
load-bearing finding: the pre-61-3 canary was wired only into
`_run_narration_turn_synchronous` while the production default
(`_run_narration_turn_sdk`, ADR-101) — the path the 2026-05-23 $313
incident ran on — had no canary at all. Both paths now refuse
identically and page the operator via a `prompt_oversized_hard`
watcher event with `severity="error"`.

## Deliverables

- `sidequest-server/sidequest/agents/orchestrator.py`
  - Renamed `_maybe_emit_oversized_canary` → `_check_oversized_prompt`
    (returns `bool`; True = caller refuses; no raise).
  - Promoted log to `logger.error`; preserved `narrator.prompt_oversized`
    prefix so grep consumers keep working.
  - Emit changed: `prompt_oversized` (severity="info") →
    `prompt_oversized_hard` (severity="error"). Old soft event removed
    (no dead code per CLAUDE.md — no caller emits it anymore).
  - Wired the canary into the SDK path between `system_blocks`
    construction (3480-3484) and `complete_with_tools` (3567).
  - Synchronous path updated to act on the new return value.
  - `_degraded_result` extended with optional `narration=` kwarg.
- `sidequest-server/tests/agents/test_61_3_hard_cap_oversized_canary.py`
  - TEA's 5 tests (1 false-positive guard + 4 RED→GREEN promotions).
  - Removed an unused `ToolUseBlock` import to clear F401 lint
    (cosmetic; no assertion changes).
- `sidequest-server/tests/agents/test_orchestrator_oversized_canary.py`
  - Rewrote both tests for the HARD contract on the synchronous path
    (same story, same contract evolution).

Branch: `feat/61-3-hard-cap-oversized-canary` (pushed).
Commit: `657dc4b` — `feat(61-3): hard-cap oversized canary on SDK + sync paths`.

## Key Decisions

- **Degraded narration text:** distinct line
  `"[narrator-overload — operator paged]"` on budget-refuse so
  session-recording grep distinguishes it from SDK-error-refuse
  (which keeps the default `"The world holds its breath."`).
  Bracketed prefix + en-dash makes it grep-clean without false
  positives from real narration.
- **Cost-span shape on refuse:** early-return BEFORE entering
  `narration_turn_cost_span`. The watcher event with `severity="error"`
  is the GM-panel signal (locked design B); a cost span on a path
  with zero token cost would be misleading. The action span
  (`orchestrator_process_action_span`) still wraps the refuse so the
  turn shows in the trace tree.
- **Constant name:** kept `SOFT_PROMPT_BUDGET_BYTES` to minimize blast
  radius (rename would touch tests + docstrings across multiple
  files). The docstring now describes it as the hard cap; rename can
  be a follow-up if Reviewer asks for it.
- **Existing SOFT tests:** rewrote in this same commit (locked
  decision OQ3). Same contract evolution, same story.

## Open Questions

None for review — all three TEA OQs resolved (see session file
`## Green phase` for full rationale).

## Test Status

```
tests/agents/test_61_3_hard_cap_oversized_canary.py        5/5 PASS
tests/agents/test_orchestrator_oversized_canary.py         2/2 PASS
Full suite                                          7266 passed, 400 skipped
```

No regressions.

## Notes

- `ruff format` reformatted 107 unrelated files (preexisting drift
  across the repo). NOT committed — only the 3 story-relevant files
  are staged. The unrelated reformats remain dirty in the working
  tree for another commit / cleanup pass.
- One tiny in-file format collapse (line 190, a `and` continuation
  joined onto one line) hitched into `orchestrator.py` because I
  edited that file; it's a no-op format change.
