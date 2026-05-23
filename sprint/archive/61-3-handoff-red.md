# Handoff: red -> green
**Story:** 61-3 — Hard-cap oversized-prompt canary
**Agent:** tea
**Timestamp:** 2026-05-23

## Summary

Wrote 5 RED-phase tests against a new file
`sidequest-server/tests/agents/test_61_3_hard_cap_oversized_canary.py` that
drive the SDK path through `FakeAnthropicSdkClient` and assert the hard-cap
contract: (1) SDK call is NOT invoked when prompt exceeds budget, (2) a
degraded `NarrationTurnResult` is returned, (3) the loud emit reaches the
GM-panel watcher transport as a `prompt_oversized_hard` event with
`severity="error"`, (4) the log level is ERROR (not WARNING), and (5) no
double-emit during sustained refusal. Story context with locked design
decisions and Dev guidance lives at
`sprint/context/context-story-61-3.md`. The single load-bearing finding
beyond the original story spec: **the pre-61-3 canary is wired only into
the synchronous (claude -p) narration path, NOT into the SDK path** — the
default per ADR-101 and the path the $313 incident actually ran. Wiring
that gap is part of GREEN.

## Deliverables

- `sprint/context/context-story-61-3.md` — full design rationale (A/B/C/D
  decisions, test contract, code surfaces, open questions). Read this
  first; it IS the GREEN spec.
- `sidequest-server/tests/agents/test_61_3_hard_cap_oversized_canary.py` —
  5 tests. 4 fail with real assertion failures, 1 passes as the
  false-positive guard for under-budget prompts.
- `.session/61-3-session.md` — `## Red phase` section updated with locked
  decisions, failure modes per test, and open questions.

## Key Decisions (locked in RED)

- **A.** Refuse + degraded result, NOT truncate. (Silent-partial-success
  is project-banned doctrine.)
- **B.** Loud = `logger.error` + new `prompt_oversized_hard` watcher event
  with `severity="error"` + exactly-one-emit-per-refuse.
- **C.** Single threshold at existing `SOFT_PROMPT_BUDGET_BYTES = 2_000_000`
  (no new constant).
- **D.** Wire canary into `_run_narration_turn_sdk` (today only synchronous
  path has it).

## Open Questions for Dev (GREEN)

1. Degraded narration text — reuse `"The world holds its breath."` or a
   distinct line so session recordings show the budget-refuse
   distinctly?
2. Cost-span shape on refuse — enter span after canary check (simpler)
   or inside with a `narration.turn.refused_oversized=True` attribute
   (GM-panel signal)?
3. The pre-existing `tests/agents/test_orchestrator_oversized_canary.py`
   asserts SOFT behavior on the synchronous path. After GREEN that path
   also refuses, so that test will fail. Update it as part of 61-3 GREEN
   — same contract evolution, same story.

## Test Status

```
tests/agents/test_61_3_hard_cap_oversized_canary.py
  test_oversized_prompt_refuses_sdk_call_and_returns_degraded   FAIL (RED ✓)
  test_under_budget_prompt_proceeds_normally                    PASS (false-positive guard)
  test_oversized_canary_emits_loud_event_to_gm_panel            FAIL (RED ✓)
  test_oversized_canary_logs_at_error_level_not_warning         FAIL (RED ✓)
  test_canary_emits_exactly_once_per_oversized_call             FAIL (RED ✓)

4 failed, 1 passed in 0.22s
```

Pre-existing `tests/agents/test_orchestrator_oversized_canary.py` (2 tests)
still passes — its SOFT-path contract holds today; will need GREEN-phase
update.

## Self-Review

- [x] Tests fail for the right reasons (real assertions, not import errors)
- [x] No implementation code written (orchestrator.py untouched)
- [x] Correct branch (sidequest-server on `feat/61-3-hard-cap-oversized-canary`)
- [x] All ACs covered: refuse (1), no-false-positive (2), loud emit (3),
      error log level (4), no-spam (5)
- [x] Wiring test included (3 — subscriber receives the event from real
      production path)
- [x] No source-text wiring tests (per sidequest-server CLAUDE.md)
- [x] Working tree status — test file + context + session updates only;
      nothing else touched.
