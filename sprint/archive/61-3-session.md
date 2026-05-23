---
story_id: "61-3"
jira_key: "none"
epic: "epic-61"
workflow: "tdd"
---
# Story 61-3: Hard-cap oversized-prompt canary

## Story Details
- **ID:** 61-3
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** 61-2 (hard dependency)
- **Points:** 2

## Summary
Promote the soft canary at `sidequest-server/sidequest/agents/orchestrator.py:2967-2997` from `logger.warning` + `_pub("prompt_oversized")` to a HARD response. When `len(system_prompt) + len(user_message) > SOFT_PROMPT_BUDGET_BYTES` (2M bytes), either refuse the SDK call (return degraded result + loud operator emit) or aggressively truncate the Valley payload (drop oldest entries first within bounded fields). The emit must be LOUD on the GM panel — not a buried warning that scrolled past during overnight debugging (the failure mode of the 2026-05-23 $313 incident).

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-05-23

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-23 | 2026-05-23 | - |
| red   | 2026-05-23 | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations.

## Context Links
- **Epic spec:** `/Users/slabgorb/Projects/oq-2/sprint/context/context-epic-61.md` §Layer 3 — Defense in depth (61-3, 61-4, 61-5)
- **Key incident:** Runaway Valley block 2026-05-23 — $313 burn in 48h due to uncached Valley payload carrying unslimmed snapshot × 8 tool-loop iterations. This story is defense-in-depth: catch and stop oversized prompts before they hit the API.
- **Prior work:** 61-2 (snapshot slim) is a prerequisite — establishes DROP-list and projection decisions so 61-3 has bounded payloads to work with
- **Prior diagnosis:** `sprint/archive/60-3-session.md` — Valley was "innocent" on cache-write churn, but guilty on unbounded growth multiplied by tool-loop
- **Architecture references:** ADR-098 (Stateless Narrator Turns §Bound canary), ADR-110 (Snapshot Slimming Phase A+B), ADR-048 (Lore RAG Store Phase E wiring)

## Implementation Notes

### Hard-cap strategy options (TDD test cases)

1. **Refuse-and-degrade:** When oversized is detected, don't call the SDK at all. Return a canned degraded response (e.g., "Oversized prompt limit exceeded. Narrator disabled. Operator alert issued.") + loud emit to the GM panel. Pro: simple, clear; Con: player sees degradation.

2. **Truncate Valley aggressively:** If Valley is the culprit (likely after 61-2's slim work), drop oldest entries from bounded fields (e.g., oldest journal entries, oldest room_states history) until total fits. Pro: keeps narrator on; Con: complexity, need clear priority order for what to drop.

The epic spec §Layer 3 says "refuse-or-truncate" — implementation should decide on a primary strategy + fallback. TDD approach: write failing test(s) for both cases, implement the primary strategy, keep fallback as a guard.

### Test structure (TDD red-phase)

Three test cases to start:

1. `test_canary_refuses_oversized_system_prompt` — construct an oversized prompt (push Valley size past budget via synthetic snapshot), assert SDK call does NOT happen, assert loud emit fires, assert degraded result returned.

2. `test_canary_truncates_valley_if_truncation_fits` — construct oversized but-fixable prompt (Valley too large, but under budget after old entries dropped), assert SDK call DOES happen with truncated Valley, assert OTEL span records truncation action.

3. `test_canary_emits_loud_to_gm_panel` — verify the emit on both refuse + truncate cases reaches the watcher/GM panel (not buried in logger.warning).

### Wiring checks post-implementation

- Verify `_maybe_emit_oversized_canary` is called BEFORE the SDK invocation (currently it is, via `orchestrator.py:2967`)
- Verify the degraded-result path surfaces in the test without a spy (actual SDK path avoidance)
- Verify OTEL emit carries sufficient detail for the GM panel (action taken, bytes over, suggested action) — see ADR-031 / ADR-090 §OTEL Observability Principle

### Known constraints

- The canary sits at the orchestrator level (before SDK call), NOT inside `anthropic_sdk_client.py` — so it must make the refuse/truncate decision before `self._client.complete_with_tools` at orchestrator.py:3546
- Valley is the uncached, growing block — that's the truncation target if we go that route
- Refuse-path should return a `NarrationTurnResult` with a clear reason in the narration text (so the player/operator knows why the narrator went silent)

### Reference implementation shape

The soft canary is at orchestrator.py:2967-2997. The hard-cap implementation should:

1. Keep the struct (check `total > SOFT_PROMPT_BUDGET_BYTES`)
2. Add a branch: `if oversized: (refuse-or-truncate)`
3. If refuse: early-return degraded result, emit loud
4. If truncate: modify Valley text in-place, emit truncation detail to OTEL + watcher, proceed with SDK call
5. Update the system_blocks construction (lines 3437-3441) if Valley was truncated

## Red phase (TEA — 2026-05-23)

### Design decisions locked

**A. Refuse + degraded result (NOT truncate).** On `total_bytes > SOFT_PROMPT_BUDGET_BYTES`,
short-circuit before the SDK call and return `NarrationTurnResult(is_degraded=True, narration=…)`.
Rationale: truncation invites silent-failure ("dropped third-oldest journal entry") that the
project actively bans (feedback_no_burying_bombs, CLAUDE.md No Silent Fallbacks); a Valley-aware
truncator is its own design problem out of scope for 2pt. The `_degraded_result` helper at
`orchestrator.py:2999-3005` is the shape to reuse (consider a `reason="oversized_prompt"` kwarg
in GREEN so operator logs distinguish refuse-on-budget from refuse-on-SDK-error).

**B. Loud emit = log promotion + distinct watcher event + no double-emit.**
1. `logger.warning` → `logger.error` (same `narrator.prompt_oversized` prefix so log-tail grep
   consumers don't change).
2. NEW watcher event `prompt_oversized_hard` with `severity="error"` so GM panel can red-band
   filter on a stable event name. Existing `prompt_oversized` soft-event call site stays.
3. One emit per oversized turn (no internal loop / no recursive emit).

`publish_event` already accepts `severity` kwarg (`watcher_hub.py:474-481`).

**C. Single threshold at existing `SOFT_PROMPT_BUDGET_BYTES = 2_000_000`** (no new constant).
Post-61-2 healthy prompts are well under it; a second threshold doubles test surface for
ambiguous safety value.

**D. Wiring gap (load-bearing finding).** Pre-61-3 the canary is wired ONLY into
`_run_narration_turn_synchronous` (`orchestrator.py:3330`), NOT into `_run_narration_turn_sdk`.
The SDK path is the ADR-101 default and the path the $313 incident ran on — the soft canary
couldn't have fired in the incident even if its severity had been ERROR, because it wasn't on
the production code path. **61-3 GREEN must wire the canary into the SDK path** (after
`system_blocks` is built at `orchestrator.py:3437-3441`, before `complete_with_tools` at
`orchestrator.py:3546`).

### Test file
`sidequest-server/tests/agents/test_61_3_hard_cap_oversized_canary.py`

### Failing tests (RED state — 4 fail, 1 already-green guard)

| Test | Status | Failure mode |
|------|--------|--------------|
| `test_oversized_prompt_refuses_sdk_call_and_returns_degraded` | RED ✗ | SDK call DOES fire today (1 recorded_request) and `is_degraded=False` — wiring gap (canary not on SDK path) + soft contract (warn-then-proceed). |
| `test_under_budget_prompt_proceeds_normally` | GREEN ✓ | Already-correct behavior — false-positive guard. |
| `test_oversized_canary_emits_loud_event_to_gm_panel` | RED ✗ | `prompt_oversized_hard` event type does not exist; only `prompt_oversized` (severity="info") today, and not on SDK path. |
| `test_oversized_canary_logs_at_error_level_not_warning` | RED ✗ | No `narrator.prompt_oversized` log line fires at all on SDK path (the canary isn't called). |
| `test_canary_emits_exactly_once_per_oversized_call` | RED ✗ | Zero `prompt_oversized_hard` events today. |

All four failures are real assertion failures (not import/collection errors). Pre-existing
`tests/agents/test_orchestrator_oversized_canary.py` (synchronous-path SOFT contract) still
passes — that test will need GREEN-phase update once the synchronous path also refuses.

### Open questions for Dev

1. **Degraded narration text wording.** Reuse `"The world holds its breath."` or distinct
   variant so session recordings distinguish budget-refuse from SDK-error-refuse?
2. **Cost span shape on refuse.** Enter `narration_turn_cost_span` AFTER the canary check
   (simpler) or inside with a `narration.turn.refused_oversized=True` attribute (GM-panel
   visibility, follow-up)?
3. **Synchronous path's existing SOFT test will fail in GREEN.** Update it as part of 61-3
   GREEN (not a separate regression — same contract evolution).

### TEA Assessment

**Tests Required:** Yes
**Test Files:**
- `sidequest-server/tests/agents/test_61_3_hard_cap_oversized_canary.py` — 5 tests, 4 RED.

**Tests Written:** 5 tests covering 4 contract layers (refuse / no-false-positive / loud-emit /
log-level / no-spam).
**Status:** RED (4 failing as expected; 1 false-positive guard already green).

**Handoff:** To Dev (`.session/61-3-handoff-red.md`) for GREEN implementation.

## Dev Checklist
- [x] Branch created: `feat/61-3-hard-cap-oversized-canary` off develop in sidequest-server
- [x] Red-phase tests written (5 test cases, 4 failing for the right reasons)
- [x] Refuse strategy implemented (primary)
- [x] Canary wired into SDK path (`_run_narration_turn_sdk`)
- [x] Log level promoted to ERROR
- [x] `prompt_oversized_hard` watcher event with severity="error"
- [x] Existing `test_orchestrator_oversized_canary.py` SOFT test updated to HARD contract
- [x] Green-phase tests passing
- [ ] Code review (against TDD flow + OTEL principle)
- [ ] Merge to develop

## Green phase (Dev — 2026-05-23)

### Implementation summary

- Renamed `_maybe_emit_oversized_canary` → `_check_oversized_prompt` (returns `bool`; True = caller must refuse). Control flow stays in the caller — no raise.
- Log promoted: `logger.warning` → `logger.error`. Prefix preserved (`narrator.prompt_oversized`) so log-tail grep consumers keep working. Added `action=refuse` suffix for clarity.
- Watcher event renamed: `prompt_oversized` (severity="info", soft) → `prompt_oversized_hard` (severity="error", hard). Old soft event removed — no caller emits it anymore (no dead code per CLAUDE.md).
- Wired canary into SDK path at `orchestrator.py:3485` (between system_blocks construction at 3480-3484 and `complete_with_tools` at 3567) — closes the load-bearing wiring gap TEA caught.
- Synchronous path updated to act on return value (refuse on True).
- `_degraded_result` extended with optional `narration` kwarg so callers can override the default in-fiction stall text.

### Open question resolutions

1. **Degraded narration text** — went with distinct line `"[narrator-overload — operator paged]"`. Bracketed prefix + en-dash makes it grep-clean (`grep -F '[narrator-overload'`) without false positives from real narration. Default `"The world holds its breath."` still serves the SDK-error-refuse path via `_degraded_result(...)` with no narration kwarg.
2. **Cost-span shape on refuse** — went with early-return BEFORE entering `narration_turn_cost_span`. Rationale: the `prompt_oversized_hard` watcher event with severity="error" is the GM-panel signal (locked design B). Adding a cost span with `refused_oversized=True` would imply token cost where there isn't any — the cost-rollup span is for actual API calls. The action span (`orchestrator_process_action_span`) still wraps the refuse path, so the turn is visible in the trace tree; the watcher event is the dashboard-actionable signal.
3. **Existing `test_orchestrator_oversized_canary.py` SOFT test** — rewrote both tests for the HARD contract on the synchronous path. Same story, same commit (contract evolution, not a separate regression).

### OTEL coverage (per CLAUDE.md OTEL Observability Principle)

The refuse path emits `prompt_oversized_hard` with severity="error" carrying `total_bytes`, `budget`, `sections` (per-section char breakdown), and `action="refuse"` fields. GM panel can red-band filter on the event type alone; the fields show the operator how far over the budget the prompt was and which sections were the culprits.

### Test status

- `tests/agents/test_61_3_hard_cap_oversized_canary.py` — 5/5 green (4 promoted from RED, 1 false-positive guard).
- `tests/agents/test_orchestrator_oversized_canary.py` — 2/2 green (rewritten for HARD contract on synchronous path).
- Full suite: 7266 passed, 400 skipped, no regressions.

### Notes for SM / Reviewer

- `ruff format` reformatted 107 unrelated files (preexisting drift across the repo). NOT committed — only the 3 story-relevant files are staged. One tiny in-file format collapse (line 190, a `and` continuation joined onto one line) hitched a ride in `orchestrator.py` because I edited that file; it's a no-op format change.
- Removed an unused `ToolUseBlock` import from the TEA-authored test file to clear F401 lint. Pure cosmetic; no assertion changes.
- Kept constant name `SOFT_PROMPT_BUDGET_BYTES` to minimize blast radius (would touch ~3 test files and a docstring across orchestrator + tests). The docstring now describes it as the hard cap; rename can be a follow-up if Reviewer wants it.

## Spec-Check (Architect — 2026-05-23)

### Verdict: spec-aligned

The GREEN implementation honors epic 61 §Layer 3 (refuse-or-truncate, refuse chosen), ADR-101 (default SDK backend is the path now guarded — the load-bearing wiring fix), and the OTEL Observability Principle (the watcher event + ERROR log are the GM-panel lie-detector signal that was missing on 2026-05-23). No 61-3-scope changes required before Reviewer.

### Architect Assessment

**Decision verified:** Refuse + degraded result on both narration paths; identical canary contract; new `prompt_oversized_hard` watcher event at severity=error.

**Rationale verified:** Refuse matches existing degraded-turn convention (`_invoke_with_retry_once` failure already returns `_degraded_result`); the turn counter `record_interaction()` advances on any non-opening turn regardless of `is_degraded` (`websocket_session_handler.py:3449`), so the player loses the turn on refuse exactly as they would on a transient SDK failure — no new doctrine introduced.

**Alternatives considered (and correctly rejected):**
- Truncate Valley aggressively: rejected by Dev (locked in RED phase A) for project-doctrine reasons (No Silent Fallbacks).
- Cost-span attribute `refused_oversized=True`: rejected; the watcher event is the actionable signal. The action span (`orchestrator_process_action_span`) still wraps the refuse, so the trace tree shows the turn — a span attribute would be belt-and-suspenders, not load-bearing.

### Findings on the six spec questions (one-line each)

**A. Refuse doctrine + player action handling.** Refuse is correct; the player's action consumes the interaction counter on refuse exactly as it does on `_invoke_with_retry_once` SDK-error refuse (`record_interaction()` at session_handler.py:3449 fires for any non-opening turn regardless of `is_degraded`) — Dev's path matches the existing degraded-turn convention, no new doctrine introduced.

**B. SDK + synchronous parity.** Not byte-identical surfaces (sync calls `send_stateless` one-shot at orchestrator.py:2914; SDK calls `complete_with_tools` with a tool-loop at anthropic_sdk_client.py:122), but the canary is correctly placed at prompt-construction time on both — same `SOFT_PROMPT_BUDGET_BYTES` check against `len(system_prompt) + len(user_message)`. The SDK path computes `system_prompt_total` from `stable_text + valley_text + recency_text` (the three-zone join) which mirrors the sync path's `compose_split` join; tools-array bytes are excluded on both (immaterial against 2M budget, ~50KB delta).

**C. Watcher event taxonomy / soft-event removal.** Verified safe: `grep` across `sidequest-server` and `sidequest-ui` finds zero non-orchestrator subscribers for either `prompt_oversized` or `prompt_oversized_hard` (only the orchestrator emit site itself, plus historical ADR-098 / plan docs). The UI has no panel subscriber yet — when one lands it will need to subscribe to `prompt_oversized_hard`. No silent break.

**D. Constant naming `SOFT_PROMPT_BUDGET_BYTES`.** Mild "lying name" — *not* a CLAUDE.md "say X, do Y" violation because Dev openly flagged it and the docstring now describes it as the hard cap. Recommend: rename to `PROMPT_BUDGET_BYTES_HARD` as a small follow-up story (post-merge), not in-PR (~3 test-file touches across the green diff would inflate the review surface without changing behavior). The current name was load-bearing in the RED contract decisions — keeping it through merge preserves the "single threshold (locked decision C)" reading.

**E. Span attribute `refused_oversized=True`.** Not required for 61-3 scope. The action span (`orchestrator_process_action_span`) is open when the refuse fires (line 3485 lives inside the `with` block at line 3402), so Dev *could* call `span.set_attribute(...)` — but the watcher event at severity=error is the GM-panel signal (locked design B). Adding the span attribute is a small follow-up if a future GM-panel "turns this session" view wants per-turn coloring; today the loud watcher event suffices. Don't gate the merge on it.

**F. 61-4 implications.** 61-3 and 61-4 are correctly orthogonal: 61-3 catches "the initial prompt was already too fat" at prompt-construction time (orchestrator-level); 61-4 catches "the loop hammered the SDK with no new output" at call-result-inspection time (sdk-client-level). The SDK tool-loop continuation messages grow across iterations (anthropic_sdk_client.py:122 `running_messages` accumulates tool_use/tool_result pairs) — but the canary at 61-3 only inspects the INITIAL prompt, so a turn that starts just under budget and balloons mid-loop is exactly 61-4's zone. No accidental short-circuit.

### ADR amendment recommendations

- **ADR-098 §Bound canary:** wording is now stale (says "canary, not circuit breaker"). Amend with a note that 61-3 promoted it to a hard refuse on both narration paths post-2026-05-23 incident, and reference the new watcher event name `prompt_oversized_hard`. Small amendment, not a successor ADR.
- **ADR-101:** no amendment needed. The default-backend wiring discussion stands; 61-3's contribution is that the canary now covers it.
- **No new "hard-cap doctrine" ADR needed.** Epic 61's defense-in-depth story is the doctrine container; ADR-098 is the architectural anchor; an amendment there closes the loop without spawning a new ADR.

### Follow-ups to propose (do not create)

1. **Constant rename** `SOFT_PROMPT_BUDGET_BYTES` → `PROMPT_BUDGET_BYTES_HARD`. Trivial mechanical change across orchestrator + ~3 test files. Post-61-3 merge.
2. **GM-panel red-band subscriber** for `prompt_oversized_hard`. Not in 61-3 scope (no UI work in this story), but the loud emit isn't actually "loud" until something consumes it in the panel. Likely belongs in an epic-61 epilogue or follow-up.
3. **ADR-098 amendment** per above. ~5 lines of "post-61-3" status note.

### Handoff: to Reviewer

## Verify phase (TEA — 2026-05-23)

### Verdict: ready-for-Reviewer

Independent re-verification of GREEN commit `657dc4b`. No flake, no regression, no
contract divergence. One adversarial probe added (sync+SDK parity) — passes.
Verify-phase HEAD: `e0ab5bb` on `feat/61-3-hard-cap-oversized-canary`.

### 1. Full suite reproduction

`uv run pytest -q` on `feat/61-3-hard-cap-oversized-canary` HEAD (post-probe-add):
**7266 passed, 400 skipped, 948 warnings in 26.16s** — matches Dev's number exactly,
no flake.

### 2. Per-file stability (5 runs each)

| File | Tests | Runs | Pass | Variance |
|------|-------|------|------|----------|
| `tests/agents/test_61_3_hard_cap_oversized_canary.py` (pre-probe) | 5 | 5 | 5/5 every run | None |
| `tests/agents/test_61_3_hard_cap_oversized_canary.py` (post-probe) | 6 | 5 | 6/6 every run | None |
| `tests/agents/test_orchestrator_oversized_canary.py` | 2 | 5 | 2/2 every run | None |

No order-dependent or non-deterministic behavior detected. The short-circuit
refuse + watcher-emit path is stable across xdist worker schedules.

### 3. Adversarial probe — sync+SDK parity

**Chosen:** Sync+SDK parity probe (TEA agreed with the recommendation —
ratifies Architect's B answer empirically, protects against future drift).

**Test:** `test_sdk_and_synchronous_paths_refuse_with_identical_shape` at
`tests/agents/test_61_3_hard_cap_oversized_canary.py:299`. Drives the SAME
oversized prompt through both `_run_narration_turn_sdk` (via `FakeAnthropicSdkClient`,
a `ToolingLlmClient` → dispatch routes to SDK path) and `_run_narration_turn_synchronous`
(via `AsyncMock` → dispatch routes to sync path). Asserts byte-identical refuse shape:

1. `is_degraded == True` — both paths.
2. `narration == "[narrator-overload — operator paged]"` — both paths (the distinct
   budget-refuse text Dev locked in open-question 1; matters for grep-friendly
   session-recording forensics).
3. Watcher event `prompt_oversized_hard` fires exactly once per refused turn on
   each path.
4. `severity == "error"` on both — GM-panel red-band filter depends on this.
5. `fields["action"] == "refuse"` on both — distinguishes hard-refuse from a
   future truncate variant (epic 61 §Layer 3).
6. Neither path billed (no SDK/client call recorded).

**Result:** Contract holds — all six assertions pass. The two narration code paths
produce identical refuse shape under the same SOFT_PROMPT_BUDGET_BYTES trigger.

**Commit:** `e0ab5bb test(61-3): adversarial sync+SDK parity probe` (read-only
against production code per verify charter; only the existing 61-3 test file
was extended).

### Flakes / regressions warranting a hold

None.

### Handoff: to Reviewer (do not invoke from TEA — SM dispatches)

