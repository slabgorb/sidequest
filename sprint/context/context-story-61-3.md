# Story 61-3 Context — Hard-cap oversized-prompt canary

**Parent epic:** [`context-epic-61.md`](context-epic-61.md) §Layer 3 — Defense in depth (61-3, 61-4, 61-5)
**Branch:** `feat/61-3-hard-cap-oversized-canary` (sidequest-server, off develop, post-61-2 merge)
**Workflow:** TDD
**Points:** 2

## What this story does

Today, `Orchestrator._maybe_emit_oversized_canary`
(`sidequest-server/sidequest/agents/orchestrator.py:2967-2997`) is a SOFT
warning: when `len(system_prompt) + len(user_message) >
SOFT_PROMPT_BUDGET_BYTES` (2,000,000 bytes / ~500K tokens), it logs at
WARNING level and publishes a `prompt_oversized` watcher event with
`severity="info"` (the default for `publish_event`). The SDK call then
proceeds with the oversized prompt and bills the model anyway.

The 2026-05-23 incident demonstrated this failure mode: the warning fired
during overnight debugging, scrolled past unread, and ~$313 burned over
48 hours.

**Story 61-3 promotes this seam from SOFT to HARD.** When a prompt exceeds
the budget, the SDK call MUST NOT fire; instead the narrator returns a
degraded `NarrationTurnResult` and emits a LOUD operator alert.

## Design decisions (locked in RED phase)

### A. Refuse + degraded result (no truncation)

When `total_bytes > SOFT_PROMPT_BUDGET_BYTES`, the orchestrator MUST:

1. **Skip the SDK call entirely.** No `complete_with_tools` invocation.
   No `_invoke_with_retry_once`. Zero billable tokens leave the process.
2. **Return a `NarrationTurnResult` with `is_degraded=True`** carrying
   operator-facing narration text that surfaces the refusal to the
   player (so the playtest doesn't hang silently).

**Why not truncate?** Three reasons:

- **Project doctrine bans silent partial-success.** Memory
  `feedback_no_burying_bombs` ("don't bury bombs with null-checks") and
  the global CLAUDE.md "No Silent Fallbacks" rule both name "we kept it
  green by dropping the third-oldest journal entry" as exactly the kind
  of fix that hides downstream failures.
- **Post-61-2 a healthy prompt fits the budget.** 61-2 shipped the
  per-field projections that hold the Valley payload bounded. If the
  canary fires post-61-2, the prompt is anomalous and the operator
  needs to see it now, not have it papered over.
- **A Valley-aware truncator is out of scope for 2 points.** Building a
  priority order ("drop oldest journal first, then oldest room_states,
  then…") is its own design problem with its own test surface. Refuse
  is the cleaner contract.

**Degraded narration text** uses the project's "in-fiction stall"
convention already established by `_degraded_result`
(`orchestrator.py:2999-3005`, narration: `"The world holds its breath."`)
— extend the same shape with an oversized-specific variant so the operator
can distinguish refuse-on-budget from refuse-on-SDK-error in logs and
session recordings.

### B. "Loud" emit — three parts

1. **Log level promotion.** `logger.warning` → `logger.error`. ERROR
   lines surface in `just logs` and any future red-band log filter; the
   WARNING line was the exact failure mode the 2026-05-23 incident
   demonstrated (drowned in overnight debug noise).
2. **Distinct watcher event type + severity tag.** Emit
   **`prompt_oversized_hard`** (distinct from the existing
   `prompt_oversized` soft event) with **`severity="error"`** so the GM
   panel can red-band filter on a stable event name without inspecting
   field payloads. The existing soft `prompt_oversized` event remains
   wired (the call site stays, severity stays `"info"`) so any future
   "yellow band" (soft < n < hard) can still surface, but Story 61-3's
   delivered behavior at the SOFT threshold is the HARD refuse.
3. **No double-emit.** Two sequential calls to the canary path with the
   same oversized payload MUST emit exactly one
   `prompt_oversized_hard` event per refuse. The canary is per-call and
   the next call starts fresh — but during a sustained runaway loop a
   single oversized turn must not become a thousand events. Note: each
   distinct refuse fires once; this guards "loop within a single
   canary check," not "different oversized turns."

`publish_event` already accepts a `severity` kwarg
(`telemetry/watcher_hub.py:474-481`); pass `severity="error"` for the
hard event.

### C. Budget — single threshold at `SOFT_PROMPT_BUDGET_BYTES`

The hard cap is the existing `SOFT_PROMPT_BUDGET_BYTES = 2_000_000`
constant. No new constant introduced. Rationale:

- Post-61-2 a healthy narrator prompt is well under 2M bytes.
- A second threshold (e.g., soft@2M, hard@2.4M = +20%) doubles the
  test surface for ambiguous value.
- The 2026-05-23 incident's prompts blew past 2M; a tighter HARD cap
  buys no additional safety margin against the actual failure mode.

If a future incident calls for a yellow band, add it later as a
separate story; this story holds the line at one threshold.

### D. Wiring gap: SDK path must call the canary

**Currently the canary is wired ONLY into the synchronous (claude -p)
narration path** (`_run_narration_turn_synchronous`, line 3330). The
SDK path (`_run_narration_turn_sdk`, line 3356, the ADR-101 default and
the path the $313 incident burned through) **never calls
`_maybe_emit_oversized_canary` at all**. That is the load-bearing
wiring gap: the soft canary couldn't have fired in the incident even if
its severity had been ERROR, because it wasn't on the production code
path.

61-3 MUST wire the canary into the SDK path. Concretely, in
`_run_narration_turn_sdk`, after `system_blocks` is constructed (lines
3437-3441) and before `self._client.complete_with_tools(...)` (line
3546), compute the total bytes across all `system_blocks` plus
`user_message` and pass through the canary check. On refuse, return a
degraded `NarrationTurnResult` BEFORE entering the
`narration_turn_cost_span` (or inside it but before
`complete_with_tools`) so no SDK call fires and no cost span attributes
record a non-existent call.

The synchronous-path call stays for the (rare) non-SDK backend, so
both paths are guarded uniformly.

## Test contract

Test file: `sidequest-server/tests/agents/test_61_3_hard_cap_oversized_canary.py`

(New file — the existing `test_orchestrator_oversized_canary.py`
asserts the SOFT contract; keep it untouched in the RED phase and let
GREEN amend or supersede.)

### Tests (5)

1. **`test_oversized_prompt_refuses_sdk_call_and_returns_degraded`**
   — Drive `Orchestrator.run_narration_turn` through the SDK path with
   `FakeAnthropicSdkClient`; force the budget below realistic prompt
   size via `monkeypatch.setattr(orchestrator,
   "SOFT_PROMPT_BUDGET_BYTES", 10)`. Assert
   `fake.recorded_requests == []` (no SDK call) and the returned
   `NarrationTurnResult.is_degraded is True` with a non-empty
   `narration`.

2. **`test_under_budget_prompt_proceeds_normally`** — Same SDK-path
   driver, but with the budget left at its real default. Assert
   `len(fake.recorded_requests) == 1` (one SDK call fired) and the
   result is `is_degraded=False`. Guards against false positives where
   the canary engages on every turn.

3. **`test_oversized_canary_emits_loud_event_to_gm_panel`** — Drive
   the SDK path with a forced-small budget; subscribe a `_FakeSocket`
   to `watcher_hub`; assert a `prompt_oversized_hard` event reached
   the subscriber with `severity == "error"` and a `total_bytes`
   field. This is the wiring test (CLAUDE.md "Every Test Suite Needs
   a Wiring Test") — proves the loud emit reaches the GM-panel
   transport, not just `logger.error`.

4. **`test_oversized_canary_logs_at_error_level_not_warning`** —
   Drive the SDK path with forced-small budget; assert
   `caplog.records` contains a record at `logging.ERROR` whose
   message includes `narrator.prompt_oversized` (matching the
   existing log line prefix so log-tail consumers don't need to
   change their grep). Guards against an accidental
   `logger.warning` regression that would re-bury the alert.

5. **`test_canary_emits_exactly_once_per_oversized_call`** —
   Subscribe a `_FakeSocket`; call the canary twice in succession
   (either two `run_narration_turn` calls with forced-small budget,
   or two direct invocations of `_maybe_emit_oversized_canary`).
   Assert exactly two `prompt_oversized_hard` events total (one per
   call) — guards against an accidental loop or recursive emit
   inside the canary that would spam the GM panel during a
   sustained runaway. (The five-event bound is the trip wire: each
   call → exactly one event.)

### Why not also drive the synchronous path?

The existing `test_orchestrator_oversized_canary.py` already covers
the synchronous path's SOFT contract. The HARD-cap behavior is the
new contract; covering it on the SDK path (the production default per
ADR-101) is the load-bearing assertion. GREEN-phase Dev may extend
the existing sync-path tests to cover HARD behavior there too — that's
in scope for the same story, but the RED contract is fully expressed
by the five SDK-path tests above.

## Code surfaces for Dev (GREEN phase)

| Path | What changes |
|------|--------------|
| `sidequest-server/sidequest/agents/orchestrator.py:2967-2997` | Rewrite `_maybe_emit_oversized_canary` to return a boolean (or named result) indicating whether the prompt was rejected. Promote log to ERROR. Add `prompt_oversized_hard` publish with `severity="error"`. |
| `sidequest-server/sidequest/agents/orchestrator.py:3330` | Synchronous-path call site — on refuse, return `_degraded_result(...)` instead of proceeding. |
| `sidequest-server/sidequest/agents/orchestrator.py:3437-3441` (then jump to ~3546) | SDK-path — add the canary check AFTER `system_blocks` is built and BEFORE `complete_with_tools`. On refuse, return a degraded result; do not enter the cost span, or exit it cleanly with a sentinel attribute. |
| `sidequest-server/sidequest/agents/orchestrator.py:2999-3005` | `_degraded_result` already exists; consider an oversized-specific narration variant or a `reason="oversized_prompt"` kwarg so operator logs distinguish refuse-on-budget from refuse-on-SDK-error. |

## Open questions for Dev

1. **Degraded narration text wording.** `_degraded_result` currently
   returns `"The world holds its breath."` for any failure. The
   oversized refuse may want a distinct line so the player + operator
   can tell from the session recording that the budget tripped vs. an
   API timeout. RED leaves this open — pick during GREEN.
2. **Cost span behavior on refuse.** The SDK path enters
   `narration_turn_cost_span(...)` BEFORE `complete_with_tools` (line
   3485). On refuse the span should close cleanly without `tool_calls`
   or `cost_usd` attributes — or it could be entered AFTER the canary
   check. The latter is simpler. RED doesn't assert span shape on the
   refuse path; GREEN may emit a `narration.turn.refused_oversized=True`
   attribute for the GM panel's "what happened this turn" view, but
   that's a follow-up not a 61-3 deliverable.
3. **Synchronous path's existing SOFT test.** `tests/agents/
   test_orchestrator_oversized_canary.py::test_oversized_prompt_warns_but_completes`
   asserts the SDK call DID happen + warning fired. After 61-3 GREEN
   the synchronous path also refuses, so that test will fail. Dev
   should update it in GREEN — it's part of the same story's contract
   evolution, not a separate regression.

## Done means

- All five RED tests fail (real assertion failures, not import/collection
  errors).
- Story context (this file) checked into orchestrator.
- Session file updated with `## Red phase` section.
- Handoff `.session/61-3-handoff-red.md` written for Dev.
