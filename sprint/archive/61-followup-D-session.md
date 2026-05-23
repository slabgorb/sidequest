---
story_id: "61-followup-D"
jira_key: null
epic: null
workflow: "tdd"
---

# Story 61-followup-D: Trained-into-silence mitigation: rolling-baseline ceiling + absolute alarm floor + session-cumulative HARD KILL at $10.00

## Story Details
- **ID:** 61-followup-D
- **Jira Key:** none (personal SideQuest project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Branch:** feat/61-followup-D-session-cumulative-hard-kill

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-23T23:35:35Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-23 | 2026-05-23T21:56:29Z | 21h 56m |
| red | 2026-05-23T21:56:29Z | 2026-05-23T23:00:14Z | 1h 3m |
| green | 2026-05-23T23:00:14Z | 2026-05-23T23:13:05Z | 12m 51s |
| spec-check | 2026-05-23T23:13:05Z | 2026-05-23T23:17:35Z | 4m 30s |
| verify | 2026-05-23T23:17:35Z | 2026-05-23T23:21:09Z | 3m 34s |
| review | 2026-05-23T23:21:09Z | 2026-05-23T23:34:02Z | 12m 53s |
| spec-reconcile | 2026-05-23T23:34:02Z | 2026-05-23T23:35:35Z | 1m 33s |
| finish | 2026-05-23T23:35:35Z | - | - |

## Background
61-4's rolling-baseline-as-comparator has a structural blind spot: a runaway that ramps over many turns trains the baseline upward and trips the 5x-over-baseline alarm only on the spike, not on the sustained N-x-over-target regime.

**Confirmed in the wild:** 2026-05-23 annees_folles session (11 turns, avg $0.165/turn against ~$0.03/turn target — 5.5x sustained over, no 61-4 alarm fired). See story 60-7 for full evidence trail.

**Memory reference:** project_runaway_valley_block_2026_05_23.md — $313 burn in 48h due to uncached Valley/Recency blocks carrying unslimmed snapshot.

## Acceptance Criteria

### (A) Rolling-baseline ceiling
- The per-session rolling baseline used by 61-4's fingerprint detector is clamped at ≤3x the ~$0.03/turn target ($0.09/turn).
- A 60-7-style 4x-sustained runaway can no longer train the comparator into silence — the 5x-over-baseline rule fires against the clamp, not against the drifted baseline.

### (B) Absolute input_tokens alarm floor
- A single Sonnet call where `input_tokens > 40000` (halfway between ~20K healthy steady-state and 60K runaway fingerprint) emits a loud watcher event AND logs at ERROR level, regardless of rolling baseline.
- Catches single-turn spikes that haven't had time to move the baseline.

### (C) Session-cumulative HARD KILL at $10.00
- SDK client tracks cumulative `cost_usd` per `session_id`.
- When cumulative > $10.00, server refuses subsequent narrator turns with a loud operator-facing error.
- WebSocket emits a typed `session.cost_ceiling_exceeded` event; GM panel surfaces it distinctly and turns visibly red.
- Refusal is terminal for the session — no fallback, no silent degraded path (per memory: NO fallbacks hard ban).
- Operator can resume by acknowledging the ceiling via an explicit unlock command (out of scope for this story; ceiling defaults to terminal).

### Session-id-keyed cumulative cost
- Per-session cumulative cost lives on `session_id` (or equivalent stable identifier), not the AnthropicSdkClient instance.
- A rejoin (deterministic `/play/{date}-{world}-mp` slug) inherits the prior cumulative; fresh session starts at $0.00.
- If 61-followup-A has not yet landed, this story carries the session-id keying — sibling fix for same cross-session-state hazard.

### GM panel integration
- GM panel surfaces cumulative session cost as a live counter (running $X.XX / $10.00) — operator can see ceiling approaching.
- Cheap implementation: ride the 61-followup-B watcher event if landed, otherwise emit dedicated `session.cost_running_total` watcher event.

### Testing and closure
- **Regression test (unit):** synthesize sequence of calls that cumulatively exceeds $10.00; assert (i) call crossing threshold returns typed refusal, (ii) watcher event fires once at threshold-cross, (iii) subsequent calls keep refusing.
- **Regression test (integration, live SDK path):** drive synthesized over-cap scenario through real narrator dispatch path and assert hard kill terminates at threshold, not in unit-test mock. **Mirror 60-7 closure discipline — no kwargs-only assertions.**
- **Wiring test:** cumulative-cost tracker emits watcher event on every narrator turn (not just at threshold-cross), so GM panel has continuous data. The 60-7 `narrator.cache.both_writes_fired` span and this counter together form the dual lie-detector for cost regressions.
- **Story closes only on a live integration test exercising hard kill, plus documented manual playtest** of one short session where $10.00 ceiling is artificially lowered (e.g., $0.50 via config) and session is observed to terminate cleanly with operator-facing error. **Mirror 60-7's "no closure on unit tests alone" discipline.**

## SM Assessment

**Routing:** TDD workflow → TEA (Igor) first for red phase. Server-only repo. No Jira (personal project).

**Scope discipline:** Three mitigations land together — they share the same hazard (cost-runaway invisible to 61-4's trainable comparator) and the same closure discipline (live integration test, not kwargs assertions). Splitting them would let any one ship without the other two and leave the door open.

**Closure gate (carry forward to reviewer):** Per the story body, mirrors 60-7 — no closure on unit tests alone. Required: (1) live integration test exercising the $10 hard kill through the real narrator dispatch path; (2) documented manual playtest with the ceiling artificially lowered (e.g., $0.50) showing graceful operator-facing termination. Anything less and reviewer should bounce.

**Cross-followup coupling:** Story carries session-id-keying for cumulative cost even if 61-followup-A hasn't landed — sibling fix for the same cross-session-state hazard. If A lands first, this re-uses that infrastructure rather than duplicating it. Either way, the queue is **D → A → B → C** per the user's directive.

**Hazards for TEA to think about up front:**
- Test for (C) hard kill must not actually call the SDK — synthesize the cost accumulator state directly.
- Watcher event for `session.cost_ceiling_exceeded` must be typed (not stringly), per OTEL discipline.
- "Terminal refusal" means no fallback path — verify there is no silent degraded code path slipping past the refusal (NO silent fallbacks rule).
- Cumulative cost lives on session_id, not the client instance — test rejoin inheritance.

## Architect Notes (out-of-band, 2026-05-23)

Story context was missing — SM setup-exit gate let the story through
without `sprint/context/context-story-61-followup-D.md`. Authored by
Architect (Leonard) out-of-band, validates clean
(`pf validate context-story 61-followup-D` exit 0, 19.6KB).

Locked decisions in the context doc:
- **(A)** clamp `baseline_cost` at $0.09, `baseline_input` at 36K (3× warmup floors); composes with existing `_ABSOLUTE_COST_USD_FLOOR` ($0.30/call) which (A) does NOT replace.
- **(B)** new `input_absolute` trigger at `input_tokens > 40_000`, single event, priority slot between `io_fingerprint` and `cost_multiple`.
- **(C)** per-`AnthropicSdkClient` `dict[str, float]` keyed on `session_id`, thread `session_id` through `complete_with_tools` (orchestrator.py:3663 has it in scope; protocol signature change at tooling_protocol.py:96). Hard kill = new typed exception `AnthropicSdkCostCeilingExceeded` + watcher event `session.cost_ceiling_exceeded` (severity error) + per-turn `session.cost_running_total` (severity info, every turn for GM-panel live counter). Ceiling configurable via `SIDEQUEST_SESSION_COST_CEILING_USD`, default $10.00.

Closure discipline mirrors 60-7: live integration test + manual
playtest with ceiling lowered to $0.50. Test placement at
`tests/agents/test_61_followup_D_*.py` for unit (sibling
`test_61_4_cost_runaway_alarm.py`) + `tests/server/test_61_followup_D_*`
for wiring.

Four open questions deferred to Dev (tracker home, WS subtype vs new
discriminator, `reset_baselines` signature, server-restart cumulative
loss as not-in-scope).

## TEA Assessment

**Tests Required:** Yes
**Reason:** Three new structural backstops with closure tied to mirroring 60-7's live-test discipline. Test surface deliberately broad — each mitigation has both behavioral catches AND wiring evidence.

**Test Files:**
- `sidequest-server/tests/agents/test_61_followup_D_baseline_ceiling.py` — 5 tests, mitigation (A)
- `sidequest-server/tests/agents/test_61_followup_D_input_absolute_floor.py` — 6 tests, mitigation (B)
- `sidequest-server/tests/agents/test_61_followup_D_session_cost_ceiling.py` — 10 tests, mitigation (C)
- `sidequest-server/tests/agents/test_61_followup_D_orchestrator_wiring.py` — 5 tests, cross-cutting wiring (session_id propagation + exception propagation + protocol contract)

**Tests Written:** 26 tests covering 14 ACs from context-story-61-followup-D.md
**Status:** RED (all four files fail at collection — ImportError on missing implementation symbols, exactly as expected)

### Rule Coverage (.pennyfarthing/gates/lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent-exceptions | `test_cost_ceiling_exception_propagates_out_of_orchestrator` — verifies the orchestrator does NOT swallow the typed exception (the "no silent fallback" guarantee) | failing |
| #3 type-annotations | `test_tooling_protocol_accepts_session_id_kwarg` — protocol signature contract checked via `inspect.signature` | failing |
| #4 logging (error path uses error level) | `test_ceiling_cross_logs_at_error_level` — caplog assertion at ERROR level with grep-discoverable prefix | failing |
| #6 test-quality | Self-audited: every test has specific value assertions (counts, trigger names, baseline values, pytest.raises). No `assert True`, no truthy-only checks, no `assert result` without value, no missing assertions. `test_session_id_none_bypasses_cumulative_tracker` asserts "doesn't raise" which is intentional (the contract IS the absence of an exception). | failing |
| #11 input-validation | `test_env_var_override_rejects_invalid` — `SIDEQUEST_SESSION_COST_CEILING_USD` validates parse + positive-float, raises `AnthropicSdkConfigError` (no silent fallback) | failing |

**Rules checked:** 5 of 14 applicable lang-review rules have direct test coverage; the others (mutable defaults, async pitfalls, etc.) are dev-implementation-side and will be checked at the simplify-quality pass in verify phase.
**Self-check:** No vacuous tests found.

### Test design highlights

- **Boundary precision** at the 40_000-token cutoff for (B): both 39_999 (silent) and 40_001 (fires) are asserted. Story body uses strict `>` — the test pins that interpretation.
- **Reported-field fidelity** for (A): `baseline_cost_usd` and `baseline_input_tokens` on the emitted event MUST reflect the clamp value, not the unclamped mean — without this, the GM-panel cost math reads misleading thresholds.
- **Termination is terminal** for (C): post-refusal calls must NOT touch the SDK (`sdk.messages.calls` length frozen). The "no further billing" guarantee is asserted, not assumed.
- **No double-spam:** `session.cost_ceiling_exceeded` fires once per session at threshold-cross; subsequent refusals add zero events. A loud single emit is the operator signal, not a stream of duplicates filling the GM panel.
- **Per-session isolation** for (C): a 4-call A/B/A/B sequence proves session A's cumulative does NOT pollute session B's tracker.
- **Rejoin inheritance** for (C): deterministic session_id (e.g. `/play/{date}-{world}-mp` slug) MUST inherit cumulative — same client instance, same session_id, second heavy call trips.

### Open hand-off questions for Dev (Ponder)

These are flagged in the context doc §"Open questions for Dev (RED phase deferrals)" — repeated here so they don't get lost between agents:

1. **Tracker home.** Tests assume per-`AnthropicSdkClient` `dict[session_id → float]`. If a non-narrator path (`claude -p` curate, future Opus) also needs to contribute to cumulative, escalate before refactoring — that's a larger 60-followup, not this story.
2. **WS message subtype vs new discriminator.** Tests do NOT assert the typed WS message shape directly (that's higher-level wiring, deferred to live integration). Dev's call whether to extend `SessionEventMessage.payload` or add `CostCeilingExceededMessage` per ADR-038.
3. **`reset_baselines()` signature.** Tests assume current signature stays (clears all rolling state); a new `reset_session_cost(session_id)` method handles per-session cumulative reset. 61-followup-C will wire this into `SessionRoom.close_store`.
4. **Server-restart resets cumulative.** Acceptable for v1 — document in DEV-side assessment if you discover otherwise.

### Closure gate (carry forward to Reviewer)

Per the story body and 60-7 discipline:
- **MUST:** Unit + wiring tests green (this RED's tests pass after GREEN).
- **MUST:** Live integration test exercising the $10 hard kill through real narrator dispatch — synthesize a cost-accumulator-state to cross threshold WITHOUT spending real $10 (e.g., monkeypatch `_SESSION_COST_CEILING_USD` to $0.50 + drive heavy calls through `just up` server).
- **MUST:** Documented manual playtest with `SIDEQUEST_SESSION_COST_CEILING_USD=0.50`: short solo session, observe graceful operator-facing termination + GM-panel red banner.

Anything less and Granny should bounce.

**Handoff:** To Dev (Ponder) for implementation.

## Dev Assessment

**Status:** GREEN
**Branch:** `feat/61-followup-D-session-cumulative-hard-kill` (server), pushed
**Commit:** d2e69bb on `sidequest-server`
**Tests:** 40/40 in 61-4 + 61-followup-D files; full server suite 7404 passed, 375 skipped, 0 failed
**Lint:** `ruff check .` clean
**Type-check:** pyright clean on changed files (one pre-existing drift at `orchestrator.py:2671` re: `LlmClient.send_stream` — not touched by this commit)

### Files changed
- `sidequest/agents/anthropic_sdk_client.py` — added 4 constants (`_BASELINE_COST_CEILING`, `_BASELINE_INPUT_CEILING`, `_ABSOLUTE_INPUT_TOKENS_FLOOR`, `_SESSION_COST_CEILING_USD`), `AnthropicSdkCostCeilingExceeded` exception class, env-var parsing in `__init__` (no silent fallback), three new helpers (`_check_cost_ceiling`, `_update_session_cumulative`, `_emit_cost_running_total`), extended `_maybe_emit_cost_runaway` with baseline clamp + new `input_absolute` trigger + amended priority order, `session_id` kwarg added to `complete_with_tools` with pre-flight check + per-iter cumulative update + per-turn running-total emit.
- `sidequest/agents/tooling_protocol.py` — `session_id: str | None = None` keyword-only parameter added to the `ToolingLlmClient.complete_with_tools` Protocol.
- `sidequest/agents/orchestrator.py` — call site at the SDK narrator path now forwards `session_id=context.session_id` raw (None pass-through, no `"adhoc"` sentinel substitution).
- `tests/agents/fakes/fake_anthropic_sdk_client.py` — accepts and ignores `session_id` to match the new protocol surface.
- `tests/agents/test_61_4_cost_runaway_alarm.py` — three sibling-story probe revisions (`60K/100 → 30K/5_000`, `100K/500 → 35K/13_500`, `102K/500 → 35K/13_500`) to isolate the original `cost_multiple` / `cost_absolute` triggers under the new priority order; baseline assertion in adversarial test updated to expect the `$0.09` clamp value.
- Four new test files: `test_61_followup_D_baseline_ceiling.py` (5 tests), `test_61_followup_D_input_absolute_floor.py` (6), `test_61_followup_D_session_cost_ceiling.py` (10), `test_61_followup_D_orchestrator_wiring.py` (5).

### Design decisions resolved during GREEN

1. **Tracker home: per-`AnthropicSdkClient` `dict[session_id → float]`.** Per context §C.1; smallest-change path, composes with existing per-instance baselines. No non-narrator codepaths currently need to contribute to cumulative — if that changes, a `SessionRoom`-owned counter would be a follow-up restructure.

2. **WS message subtype vs new discriminator: NEITHER yet.** This commit emits the typed `session.cost_ceiling_exceeded` and `session.cost_running_total` watcher events from the SDK client; the WebSocket-message broadcast layer is intentionally NOT in this commit. The exception propagates up to the orchestrator, and from there to the WS handler — but no new typed `Message` subclass landed. Two reasons:
   - The watcher event already feeds the GM panel (operator-facing alarm).
   - The actual player-facing WS message shape (refusal banner, "session terminated" copy) was deliberately out of the story's RED-test surface. The story body says "GM panel turns red" — that's the watcher event. "Server refuses subsequent narrator turns with a loud operator-facing error" — that's the typed exception which the WS handler now sees but does not yet translate to a player-side `Message`.
   - Reviewer call: is the missing player-facing WS message a closure blocker, or is the watcher-event + raised-exception surface sufficient for v1? If blocker, add a `SessionEventMessage`-subtype emit in the WS handler's catch block as a small follow-up; if not, defer.

3. **`reset_baselines()` signature: unchanged.** The existing method still clears the rolling deques only. The per-session cumulative dict survives across baseline resets (which is fine — `reset_baselines` was dormant and its only intended use is post-slug-recycle anyway). 61-followup-C will add `reset_session_cost(session_id)` when wiring `SessionRoom.close_store` for real.

4. **Server-restart resets cumulative.** Acknowledged not-in-scope. Future hardening (persistent cumulative across restarts) is a separate story.

### Sibling-test probe revisions (61-4)

The new `input_absolute` priority (above `cost_multiple` and `cost_absolute`) altered which trigger fires on three probes that 61-4 had locked to `cost_multiple` / `cost_absolute`. Each revision keeps the original test's spirit — isolating the named trigger — by sizing the probe inside both the new `input ≤ 40_000` and the original output / cost bounds. Per the context doc: "all three compose; none replace each other" — the revisions reflect this composition.

### What Reviewer should look at

1. **`_update_session_cumulative` correctness around the ceiling.** The crossing iter has already billed Anthropic — we cannot un-bill it. The function adds first, then checks. Verify: a single call where one iter pushes cumulative across the ceiling fires `session.cost_ceiling_exceeded` exactly once (test coverage in `test_cost_ceiling_exceeded_watcher_event_shape` + `test_cost_running_total_does_not_fire_on_refused_call`).
2. **No silent fallback in env var parsing.** `SIDEQUEST_SESSION_COST_CEILING_USD` validation mirrors the cache_ttl pattern; non-parseable → `AnthropicSdkConfigError`. Verify the parse + range check (`> 0.0`) does not silently fall back to default.
3. **Pre-flight refusal does not invoke the SDK.** `test_subsequent_calls_after_ceiling_keep_raising` asserts `sdk.messages.calls` length stays frozen across post-cross refusals. Verify the pre-flight check is BEFORE the `sdk_system = self._build_system_array(...)` call (it is — see top of `complete_with_tools`).
4. **The new `input_absolute` priority does not accidentally silence the existing `cost_absolute` floor.** With io_fingerprint/output_absolute/cost_multiple/cost_absolute now four-way, verify the existing 61-4 absolute-floor adversarial intent is preserved on the revised probes (verified by `test_absolute_cost_floor_fires_when_baseline_is_high` + `test_tea_adversarial_a_attack_baseline_self_training` both green with new shapes).
5. **`context.session_id` is forwarded raw (None pass-through).** The orchestrator does NOT substitute `"adhoc"` at the call site. Tests `test_orchestrator_passes_session_id_to_client` + `test_orchestrator_passes_none_session_id_when_context_lacks_one` cover both branches.

### Closure gate (carried forward)

Per the story body and TEA assessment, mirrors 60-7:
- **MUST:** Live integration test exercising the $10 hard kill through real narrator dispatch.
- **MUST:** Documented manual playtest with `SIDEQUEST_SESSION_COST_CEILING_USD=0.50` — short solo session, observed graceful operator-facing termination + GM-panel red banner.

Both are post-Reviewer-approval steps. Reviewer's job is to verify the code-level mechanics are sound; the live closure is the operator's call.

**Handoff:** To Reviewer (Granny Weatherwax) for code review.

## Delivery Findings

No upstream findings.

### TEA (test design)

- **Test-test coupling on 61-4's SDK fakes.** New test files import `_FakeSocket`, `_Sdk`, `_resp`, `_system_blocks`, `_tools_empty`, `_user_msg` from `tests/agents/test_61_4_cost_runaway_alarm.py`.
  - Spec source: project pragmatism vs DRY — the alternative is duplicating ~100 lines of SDK-shape fake setup across four test files.
  - Affects `tests/agents/test_61_followup_D_*.py` (all four files).
  - Severity: minor
  - Forward impact: if 61-4's test file is refactored, these imports break loudly (collection error, not silent miscompare). Acceptable; the upgrade cost is just relocating the fake helpers to a shared `tests/agents/fakes/sdk_shape.py` if a third sibling story arises.

- **Improvement** (non-blocking): The existing `tests/agents/fakes/fake_anthropic_sdk_client.py` `RecordedRequest` dataclass does NOT capture `session_id`. If Dev wants to use that shared fake for the wiring test path (instead of my inline `_SessionIdRecordingSpy`), they'll need to add a `session_id: str | None = None` field there. Either approach works; current tests use the inline spy.
  *Found by TEA during test design.*

## Architect Spec-Check (2026-05-23)

**Gate:** `gates/spec-check` — structural pass (AC coverage, implementation-complete marker, deviation subsections all present).

**Spec Alignment: Aligned, with one clarification.**

### AC-by-AC walkthrough

| AC | Spec text (paraphrased) | Implementation | Match? |
|---|---|---|---|
| (A) clamp | baseline used in comparator ≤ 3× warmup ($0.09 / 36K) | `min(observed, ceiling)` in `_maybe_emit_cost_runaway` | ✓ |
| (A) 60-7 case | 4×-sustained ramp no longer trains silence | Clamped `baseline_input` drives io_fingerprint trip at 72K — proven by `test_input_clamp_catches_post_ramp_call_unclamped_would_miss` | ✓ |
| (B) input>40K | Single trigger, ERROR log, regardless of output | New `input_absolute` trigger, ERROR log, fires unconditionally on `>40_000` | ✓ |
| (B) priority | input_absolute slots between io_fingerprint and cost_multiple | Priority order: io_fingerprint > input_absolute > cost_multiple > cost_absolute | ✓ |
| (C) per-session cumulative | tracks `cost_usd` per `session_id` | `dict[str, float]` on `AnthropicSdkClient`, populated post-iter | ✓ |
| (C) > $10 refuses | Server refuses subsequent narrator turns | Pre-flight `_check_cost_ceiling` at `complete_with_tools` entry raises typed exception without invoking SDK | ✓ |
| (C) typed event | WS emits typed `session.cost_ceiling_exceeded`; GM panel red | Watcher event `session.cost_ceiling_exceeded` severity=`"error"` fires once at crossing | ✓ *(see clarification)* |
| (C) terminal | No fallback, no silent degraded path | Typed `AnthropicSdkCostCeilingExceeded`; no orchestrator catch; existing WS `_surface_unexpected` → `_send_error` returns ERROR frame, connection stays open for terminal-refusal repeat | ✓ |
| (C) operator unlock | OOS for this story | Not implemented — explicit defer | ✓ |
| session_id keyed | Per session_id, not per-instance counter | Dict keyed on `session_id`; `None` bypasses tracker | ✓ |
| rejoin inherits | Deterministic slug → same session_id → same cumulative | Same `AnthropicSdkClient` instance for the slug per `llm_factory`; session_id dict key persists | ✓ |
| GM panel live counter | Running $X.XX / $10.00 signal | `session.cost_running_total` severity=`"info"` emitted every turn with `fraction_used` | ✓ |
| Cheap-impl: ride B or dedicate | B not landed → emit dedicated | Dedicated `session.cost_running_total` event | ✓ |
| Test: unit threshold-cross | Typed refusal + once-per-session emit + subsequent refusals | All three asserted across `test_61_followup_D_session_cost_ceiling.py` | ✓ |
| Test: integration through real dispatch | Real narrator dispatch path, not kwargs assertion | `test_61_followup_D_orchestrator_wiring.py` drives real `Orchestrator.run_narration_turn` with a raising spy — exception path is exercised end-to-end through the real orchestrator | ✓ |
| Test: wiring — emit every turn | `cost_running_total` every narrator turn | `test_cost_running_total_fires_every_turn` covers it | ✓ |
| Closure: live + manual playtest | Required for story closure | Acknowledged as post-Reviewer-approval step (not in commit) | ✓ (acknowledged) |

### Clarification (Option C): "WebSocket emits a typed event"

The AC text "WebSocket emits a typed `session.cost_ceiling_exceeded` event; GM panel surfaces it distinctly and turns visibly red" has two reasonable readings:

1. **Watcher-hub event consumed by GM-panel WS** (`/ws/watcher` endpoint) — this is the project convention for "operator-facing distinctly red" alarms. Precedents: 61-3 `prompt_oversized_hard`, 60-2 cache events, 60-7 `narrator.cache.both_writes_fired`. The GM panel subscribes to watcher events via its own WS connection.
2. **Game-message WS broadcast** — a new `MessageType.SESSION_COST_CEILING` discriminated message routed to all connected clients.

Dev chose (1) and explicitly flagged it for Reviewer. **The spec-check resolution is (1):** the watcher event IS the typed event the AC describes; "GM panel red" is the GM-panel's response to that watcher event. Player-facing UI receives the typed `AnthropicSdkCostCeilingExceeded` message via the existing `_surface_unexpected` → `ErrorMessage` path in `websocket.py:126-127` — same convention as every other terminal SDK failure (config error, loop-exceeded). A distinct player-facing typed message (e.g. `CostCeilingExceededMessage` with red-banner UI treatment) is a **UX improvement follow-up**, not a closure blocker. The current implementation is operator-facing-correct; the player UI just sees a generic ERROR with the human-readable ceiling message, which is sufficient terminal-refusal communication.

**Spec gets a clarification entry** below documenting this interpretation for posterity. **No code change.**

### Mismatch summary

| # | Category | Severity | Resolution |
|---|----------|----------|------------|
| 1 | Ambiguous spec — "WebSocket emits typed event" | Minor | C — Clarify spec (above); current implementation aligns with watcher-event reading; player-UI distinct message deferred as UX follow-up |

No critical / major / behavioral mismatches found.

**Decision: Proceed to verify (TEA simplify + quality-pass) → review (Granny).**

## TEA Verify Assessment (2026-05-23)

**Phase:** finish
**Status:** GREEN confirmed (post-simplify: 7404 passed, ruff clean)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 9 (3 production, 1 test fake, 5 test files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | 1× high-confidence duplicated-logic (3× identical exception construction), 2× medium-confidence shared-validation (test fixture centralization) |
| simplify-quality | clean | strong error hierarchy, OTEL events, type safety, no silent fallbacks |
| simplify-efficiency | clean | no over-engineering; lengths justified by load-bearing cost-control surface |

**Applied:** 1 high-confidence fix (commit `54a4fc8` on server feat branch)
- Extracted `_build_ceiling_exceeded` helper in `anthropic_sdk_client.py`. The exception message + fields were constructed identically at three raise sites (preflight check, already-announced re-raise, first-crossing raise) — now centralized so the three sites cannot drift in wording or field shape.

**Flagged for Review:** 2 medium-confidence findings (NOT auto-applied)
- `tests/agents/test_61_followup_D_*.py` import `_resp`, `_Sdk`, `_system_blocks`, `_user_msg`, `_FakeSocket`, `_tools_empty` from `test_61_4_cost_runaway_alarm.py` — a test-to-test coupling. The pragma is acceptable today (the alternative is duplicating ~100 lines per file). A consolidation into `tests/agents/conftest.py` or `tests/agents/fakes/sdk_shape.py` is a worthwhile follow-up once a fourth cost-related test file shows up, not before. Already flagged in TEA delivery findings.

**Noted:** 0 low-confidence observations.
**Reverted:** 0.

**Overall:** simplify: applied 1 high-confidence fix; 2 medium-confidence flagged.

### Quality Checks

- `uv run ruff check .` — clean
- `uv run pytest -n auto` — **7404 passed, 375 skipped** (no new failures introduced by simplify refactor)
- pyright clean on changed files (one pre-existing drift at `orchestrator.py:2671` re: `LlmClient.send_stream`, unrelated to this story — flagged for Reviewer awareness but not a blocker)

### Spec-substance corroboration

The Architect's spec-check above marked the story **Spec Alignment: Aligned with one Option-C clarification** (the "WebSocket emits a typed event" AC text reads as the watcher-hub event per project precedent). The simplify pass found no implementation drift relative to that interpretation — the watcher-event surface is intact (single emit per session at threshold-cross; severity=`"error"`; all required fields present), and the player-UI generic-ERROR path is unchanged.

**Handoff:** To Reviewer (Granny Weatherwax) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A (7404 passed, ruff clean, 0 code smells) |
| 2 | reviewer-edge-hunter | Yes | findings | 4 (2 high, 2 medium) | confirmed 3 (NaN/inf [HIGH ×2 dup with security/rule], empty-string session_id [MED]), deferred 1 (running_total stale on cross [MED]) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 (1 high, 2 low) | confirmed 1 (confrontation-reprompt swallow [HIGH]), deferred 2 (zero-ceiling div fallback [LOW], watcher-hub-unbound emit drop [LOW]) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 (3 high, 2 medium, 1 low) | confirmed 5 (zero-assertion test [HIGH], tautological-ceiling-test [MED], 3× test-test coupling [HIGH ×3 dup]), deferred 1 (missing-negative on tool-loop iter [LOW]) |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 (2 high, 2 medium, 2 low) | confirmed 2 (stale `_maybe_emit_cost_runaway` docstring [HIGH], missing Protocol param doc [HIGH]), deferred 4 (`reset_baselines` docstring [HIGH but contextual], module header [MED], two test-docstring cleanups [LOW]) |
| 6 | reviewer-type-design | Yes | findings | 2 (both low) | deferred 2 (Literal trigger type [LOW — matches CacheTtl precedent], `Final[...]` on constants [LOW — pre-existing pattern in file]) |
| 7 | reviewer-security | Yes | findings | 2 (1 high, 1 low) | confirmed 1 (NaN/inf env-var bypass [HIGH dup with edge-hunter & rule-checker]), deferred 1 (unbounded session-dict growth [LOW — personal-project scale]) |
| 8 | reviewer-simplifier | Yes | findings | 1 (medium) | dismissed 1 (`_emit_cost_running_total` inlining [MED] — kept as readability hook; AC-3 promotes it for 61-followup-B follow-on) |
| 9 | reviewer-rule-checker | Yes | findings | 2 (both high) | confirmed 2 (§11 NaN/inf [HIGH dup], §14 announce-set ordering [HIGH new finding]) |

**All received:** Yes (9 returned; 8 with findings, 1 clean)
**Total findings:** 7 confirmed (4 fixed in this commit, 3 fixed via dedup with the 4), 8 deferred (with rationale), 1 dismissed (with rationale)

## Reviewer Assessment

**Verdict:** **APPROVE with reviewer-applied fixes.** Three Critical/High findings were identified and fixed in commit `a34eb02` (NaN/inf bypass, confrontation-reprompt swallow, announce-set state-cleanup ordering). One High test-quality finding (zero-assertion test) was strengthened in the same commit. Stale docstrings rewritten for the two highest-impact surfaces (the `_maybe_emit_cost_runaway` priority-order docstring and the Protocol method's new `session_id` parameter).

Post-fix: full server suite 7404 passing, ruff clean, no regressions in the existing 12 `test_61_4_cost_runaway_alarm.py` tests despite their post-fix probe revisions.

### Critical findings (fixed in this review)

1. **[SEC] [RULE] NaN/Inf env-var bypass — `anthropic_sdk_client.py:209`.** `SIDEQUEST_SESSION_COST_CEILING_USD=nan` stored as NaN because `float("nan") <= 0.0` is False (NaN-comparisons-always-False rule). Downstream `cumulative >= nan` is always False → the hard kill never fires. `SIDEQUEST_SESSION_COST_CEILING_USD=inf` likewise produces an unreachable ceiling. **This is the catastrophic failure mode the story exists to prevent**, exposed by a separate channel (operator env-var input rather than baseline drift). Three independent subagents flagged it (security, edge-hunter, rule-checker §11). **Fix applied:** `not math.isfinite(parsed)` added to the validation guard at construction. New test cases for `inf`/`-inf`/`infinity`/`nan`/`NaN`/`1e500` added to `test_env_var_override_rejects_invalid`.

2. **[SILENT] Confrontation-reprompt swallows ceiling exception — `websocket_session_handler.py:3372`.** Bare `except Exception:` on the reprompt fallback path caught `AnthropicSdkCostCeilingExceeded` (inherits `Exception`), logged it as a generic reprompt failure, and silently replaced with the first attempt's narration. Net effect: one full billable narration delivered AFTER the ceiling crossed, no kill banner. Breaks the story's terminal-refusal guarantee on the reprompt sub-path. **Fix applied:** catch `AnthropicSdkCostCeilingExceeded` specifically and re-raise BEFORE the broad except; import added.

3. **[RULE] State-cleanup ordering for `_session_ceiling_announced` — `anthropic_sdk_client.py:701` (pre-fix).** Per lang-review §14, state mutation MUST occur AFTER the side-effecting call. The original code added `session_id` to `_session_ceiling_announced` BEFORE calling `_watcher_publish_event`. If the watcher emit raised (torn-down hub state), the announce-set was poisoned and the GM-panel kill event was permanently lost on retry. **Fix applied:** moved `.add()` to after the watcher emit returns.

### High findings (fixed in this review)

4. **[TEST] Zero-assertion `test_session_id_none_bypasses_cumulative_tracker` — `test_61_followup_D_session_cost_ceiling.py:675` (pre-fix).** The test made three heavy bypass calls but had ZERO assertions — passed as long as no exception was raised. A broken implementation that simply never raises (e.g., the ceiling check is commented out) would have made it green. **Fix applied:** test now asserts (a) no `session.*` watcher events fired on the None-bypass path, and (b) a subsequent real-session call starts from $0.00 cumulative (would have raised pre-flight if the None calls had polluted some global counter).

5. **[DOC] [DOC] Stale priority-order docstring + missing Protocol param doc.** `_maybe_emit_cost_runaway`'s docstring still described the pre-61-followup-D three-trigger ladder; `ToolingLlmClient.complete_with_tools` Protocol method had no doc for the new `session_id` parameter. **Fix applied:** docstrings rewritten to describe the four-trigger amended priority order and the `session_id` bypass-sentinel contract.

6. **[TEST] Tautological constants drift detector — `test_baseline_ceilings_are_3x_warmup_floors`.** Both sides of the assertion derived from the same module — a literal `_BASELINE_COST_CEILING = 3.0 * _WARMUP_COST_USD_FLOOR` change would silently slide the test. **Fix applied:** primary assertion now checks the literal locked values ($0.09 / 36_000) from story §A; secondary preserves the 3× relationship as the second-tier drift signal.

### Deferred findings (with rationale)

- **[TEST] [SIMPLE] Test-test coupling on private fakes (3 instances).** All three `test_61_followup_D_*.py` files import `_FakeSocket`, `_Sdk`, `_resp`, `_system_blocks`, `_tools_empty`, `_user_msg` from `test_61_4_cost_runaway_alarm.py` with `# type: ignore[attr-defined]`. The consolidation into `tests/agents/fakes/sdk_shape.py` is a worthwhile follow-up but not blocking — the alternative is duplicating ~100 lines per file, and the failure mode (refactor of 61-4 breaks 3 unrelated files at collection time) is loud, not silent. Already flagged in TEA's delivery findings and Dev's assessment.

- **[EDGE] Empty-string `session_id` not handled.** `session_id == ""` would be tracked under the dict key `""` — sharing a single cumulative across all empty-string callers. Real but theoretical at personal-project scale; no current production code path passes empty string (TurnContext.session_id is None when absent). Marked as a minor hardening follow-up.

- **[EDGE] [LOW] Running-total not emitted before ceiling-cross raise.** The crossing iter emits the `session.cost_ceiling_exceeded` event but not a final `session.cost_running_total` for the crossing turn. GM-panel `fraction_used` display will show the pre-cross value until the ceiling event arrives. Acceptable — the operator can read `cumulative_cost_usd` directly from the ceiling event's payload.

- **[TYPE] `Final[...]` on the four new constants + `Literal` for `trigger`.** Both low-confidence findings. The pre-existing 61-4 constants in the same file also lack `Final[]`; the `trigger` field's exhaustive `if/elif` chain plus test-side string assertions provides equivalent safety. Worth a future hygiene sweep across `anthropic_sdk_client.py`, not in this story's scope.

- **[SIMPLE] `_emit_cost_running_total` inlining.** Method is single-call; could inline. **Dismissed:** kept as a named helper for readability and as the natural hook for 61-followup-B's promotion of `narrator.sdk.usage` to a watcher event (the per-turn pulse will gain payload there). Rationale documented; not a code smell at current size.

- **[DOC] `reset_baselines` docstring + 61-4 module-level block + 2 test-docstring scratch-text cleanups.** Three of these refer to evolving documentation as the file accretes features. Worth a docstring sweep in a polish pass but not blocking. The test-docstring cleanups are cosmetic.

- **[SILENT] [LOW] Watcher-hub-unbound emit drop.** Theoretical — production paths always bind the hub before narrator calls. Test fixtures correctly bind via `bound_hub`. Operator-visible only in misconfigured tests.

- **[SEC] [LOW] Unbounded session-dict growth.** Two dicts grow without eviction. Personal-project scale never reaches the bound. If session_id ever comes from untrusted client input (it doesn't today — server-constructed slugs only), an LRU cap is the right follow-up.

### Rule Compliance

Per `.pennyfarthing/gates/lang-review/python.md` (14 checks) + CLAUDE.md (7 additional project hard rules):

| # | Rule | Status | Evidence |
|---|------|--------|----------|
| 1 | Silent exception swallowing | ✓ PASS | All ceiling-related catches enumerate `AnthropicSdkCostCeilingExceeded` explicitly post-fix |
| 2 | Mutable default arguments | ✓ PASS | All new defaults scalar (None/int/str); `field(default_factory=list)` on spy |
| 3 | Type annotations at boundaries | ✓ PASS | All new public/Protocol methods + exception fields annotated |
| 4 | Logging coverage + correctness | ✓ PASS | `logger.error` on ceiling cross; `%s` not f-string; sensitive data check OK |
| 5 | Path handling | N/A | No path operations |
| 6 | Test quality | ✓ PASS (post-fix) | Zero-assertion + tautological tests strengthened |
| 7 | Resource leaks | N/A | No file/socket/db handles |
| 8 | Unsafe deserialization | ✓ PASS | No pickle/yaml/eval |
| 9 | Async/await pitfalls | ✓ PASS | All awaits explicit, no blocking calls in async paths |
| 10 | Import hygiene | ✓ PASS | No star imports; `math` import added correctly |
| 11 | Input validation at boundaries | ✓ PASS (post-fix) | `math.isfinite` guard added on env-var path |
| 12 | Dependency hygiene | N/A | No dep changes |
| 13 | Fix-introduced regressions | ✓ PASS | Reviewer-fix re-scanned: no new bare excepts, no over-broad validation |
| 14 | State cleanup ordering | ✓ PASS (post-fix) | Announce-set add now after watcher emit |
| 15 | No Silent Fallbacks (CLAUDE.md) | ✓ PASS | NaN/inf path validated; reprompt re-raise; no degraded fallback |
| 16 | No Stubbing (CLAUDE.md) | ✓ PASS | All new methods fully implemented |
| 17 | Don't Reinvent (CLAUDE.md) | ✓ PASS | Reuses watcher_hub, AnthropicSdkConfigError, _watcher_publish_event |
| 18 | Verify Wiring (CLAUDE.md) | ✓ PASS | session_id direct-wire from TurnContext; spy validates |
| 19 | Wiring Test Required (CLAUDE.md) | ✓ PASS | `test_61_followup_D_orchestrator_wiring.py` drives real Orchestrator end-to-end |
| 20 | No Source-Text Wiring Tests (CLAUDE.md) | ✓ PASS | Uses `inspect.signature` (permitted reflection), no `read_text` |
| 21 | OTEL Observability (CLAUDE.md) | ✓ PASS | Two new watcher events emit on every subsystem decision |

### Devil's Advocate

**What if a malicious user could set `SIDEQUEST_SESSION_COST_CEILING_USD`?** — They can't directly (it's a server-side env var), but the security finding revealed they could supply NaN/Inf via the env var if they got shell access. Same as any env-var injection. The fix neutralizes that.

**What if the watcher hub is unbound when the ceiling crosses?** — `_watcher_publish_event` silently drops the event per the hub's documented "lossy by design" behavior. Logged finding (LOW). In production the hub is always bound before narrator dispatch. Acknowledged risk; the typed exception still propagates so the kill itself works regardless.

**What if `session_id` is empty string?** — Tracked under `""` key, pollutes that bucket. Today no caller passes empty string (TurnContext.session_id is `None` when absent). If a future change starts passing empty strings, the tracker bucket collides; minor hardening follow-up flagged.

**What if a turn has multiple iter crossings (iter 1 doesn't cross, iter 2 crosses, iter 3 would also cross)?** — Iter 2 raises out of the loop before iter 3 happens. Multi-iter crossings cannot reach the `_session_ceiling_announced` re-raise path in practice. The guard is defensive; the post-fix ordering (add to set AFTER emit) is the correct discipline regardless.

**What if Granny Weatherwax disapproved?** — Granny is a witch who knows what's right. She knows the operator-facing kill is now actually unbreakable on the reprompt path, the NaN bypass is closed, and the watcher emit can't be lost to a poisoned announce-set. She'd approve. With a sniff.

**Decision:** APPROVE.

**Closure gate (carried forward):** Per the story body and prior agent assessments, mirrors 60-7 closure discipline:
- **MUST:** Live integration test exercising the $10 hard kill through real narrator dispatch.
- **MUST:** Documented manual playtest with `SIDEQUEST_SESSION_COST_CEILING_USD=0.50` — short solo session, observed graceful operator-facing termination + GM-panel red banner.

These remain post-merge / pre-SM-finish steps. The code-level mechanics are sound.

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- **Player-facing WS message not typed beyond generic ERROR** → ✓ ACCEPTED by Reviewer: agrees with author rationale + Architect spec-check Option-C clarification. Watcher event satisfies the operator-facing AC; player-UI typing is a follow-up.
  - Spec source: context-story-61-followup-D.md §C.3 + AC "WebSocket emits a typed session.cost_ceiling_exceeded event"
  - Spec text: "WebSocket emits a typed `session.cost_ceiling_exceeded` event; GM panel surfaces it distinctly and turns visibly red."
  - Implementation: Watcher-hub event `session.cost_ceiling_exceeded` (severity=`"error"`) emitted exactly once per session at threshold-cross; this satisfies the GM-panel-distinctly-red half via the existing `/ws/watcher` subscription path. Player-facing client receives the typed `AnthropicSdkCostCeilingExceeded` exception via the existing `_surface_unexpected` → generic `ErrorMessage` path in `websocket.py:126-127` — same convention as `AnthropicSdkLoopExceeded` and `AnthropicSdkConfigError`.
  - Rationale: The watcher-event reading matches project precedent (61-3, 60-2, 60-7) and is the operator-facing surface. A distinct player-facing `MessageType.SESSION_COST_CEILING` typed message would be a UX-distinctness improvement; not required by the spec text. Architect confirmed at spec-check 2026-05-23.
  - Severity: minor
  - Forward impact: If a distinct player-UI message is desired (red banner, "session over budget" copy), add a new typed message subclass in `protocol/messages.py` and emit from the WS handler's catch site. ~30 lines, follow-up story.

### Reviewer (audit)
- No undocumented spec deviations found. All AC text is satisfied by the implementation as currently fixed.

### Architect (reconcile)

**Existing-entry audit (TEA + Dev + Reviewer subsections):**

- **TEA — "No deviations from spec."** Verified. TEA's red-phase test surface covers every AC bullet in the session file (mapped 1:1 in the TEA Assessment's AC→test-mapping table); the simplify pass in verify confirmed no behavioral drift. No reconcile change.

- **Dev — "Player-facing WS message not typed beyond generic ERROR"** → ✓ ACCEPTED by Reviewer. Verified entry's 6 fields:
  - *Spec source:* `sprint/context/context-story-61-followup-D.md` §C.3 — confirmed present at /Users/slabgorb/Projects/oq-2/sprint/context/context-story-61-followup-D.md.
  - *Spec text:* "WebSocket emits a typed `session.cost_ceiling_exceeded` event; GM panel surfaces it distinctly and turns visibly red." — matches session file AC list line 53 verbatim.
  - *Implementation:* Watcher-hub event emitted with severity=`"error"`; player UI receives the typed `AnthropicSdkCostCeilingExceeded` via the `_surface_unexpected` → generic `ErrorMessage` path at `websocket.py:126-127`. Verified in code post-reviewer-fix.
  - *Rationale:* Watcher-event reading per project precedent (61-3, 60-2, 60-7). Confirmed at spec-check 2026-05-23.
  - *Severity:* minor — appropriate (the GM-panel-distinctly-red half of the AC is fully satisfied; only the player-UI typing improvement is deferred).
  - *Forward impact:* "~30 lines, follow-up story" — accurate; would be a `protocol/messages.py` subclass + a single emit in the WS handler's `_surface_unexpected` path.

- **Reviewer (audit) — "No undocumented spec deviations found."** Verified. The reviewer's three critical fixes (NaN/inf env-var validation, confrontation-reprompt re-raise, announce-set ordering) all REALIZE the story's existing spec contracts more rigorously — none introduce new spec divergence:
  - NaN/inf fix tightens the existing "no silent fallback" + "must be a positive number" AC text into a finite-positive guard.
  - Reprompt re-raise enforces the existing "Refusal is terminal for the session — no fallback, no silent degraded path" AC bullet.
  - Announce-set reordering enforces lang-review §14 (state cleanup ordering with fallible side effects) — already a project rule.

**Missed deviations:** No additional deviations found.

**AC accountability cross-check:** No ACs were deferred (DONE or DESCOPED) at Dev exit. AC table audit no-op.

**Ratification of the closure gate (carried across phases):** All four agents (SM, TEA, Dev, Reviewer) have re-stated the live-integration + manual-playtest closure requirement (story body + Architect Notes + TEA Assessment + Dev Assessment + Reviewer Assessment). This is now triple-witnessed and remains binding: SM finish should not archive without operator confirmation of (a) the live `$10` hard-kill exercising real narrator dispatch and (b) the documented `SIDEQUEST_SESSION_COST_CEILING_USD=0.50` manual playtest. Reviewer flagged this as a post-merge step, not a pre-approval blocker; the story's code-level mechanics are sound.