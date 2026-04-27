---
story_id: "45-2"
jira_key: "none"
epic: "epic-45"
workflow: "wire-first"
---
# Story 45-2: Turn barrier counts active turn-takers, not lobby connections

## Story Details
- **ID:** 45-2
- **Jira Key:** none (Jira integration not enabled)
- **Workflow:** wire-first
- **Stack Parent:** none
- **Branch:** feat/45-2-turn-barrier-active-turn-takers (sidequest-server)

## Story Context

### Background
Playtest 3 (2026-04-19) evropi session revealed a critical issue: when only one player (Rux) was actively playing, the structured-mode turn barrier would wait for all four lobby connections to submit turns, causing Rux to hit artificial barriers mid-solo play.

### Problem
The turn barrier counts total lobby participants rather than active turn-takers. Phantom lobby peers who never submit turns block progress.

### Fix Dimensions

**SELECTED APPROACH (Keith, 2026-04-27): implement #3 AND #4.**

Combined design — explicit lobby states with chargen as the gating event:

1. ~~Drop barrier slots for players who haven't submitted a turn within N seconds~~ (rejected — timeout-based pruning is racy and punishes slow players like Alex)
2. ~~Only count players whose characters have advanced past round 0~~ (rejected — round-0 heuristic doesn't address chargen abandonment)
3. **Explicit lobby joined-vs-playing states.** Lobby slots have lifecycle states (e.g. `connected` → `claiming_seat` → `chargen` → `playing`); only `playing` peers are counted by the turn barrier.
4. **Chargen-abandonment cancels the lobby slot.** Disconnect during chargen, or stalled chargen past a threshold, transitions the slot back to `available` (or `abandoned`) so the barrier doesn't wait on a phantom.

These two are complementary: #3 defines the state machine; #4 is the rule that drives the chargen→abandoned transition. Together they fix the evropi playtest scenario (4 lobby connections, only Rux in `playing`) without depending on time-based heuristics.

**Out-of-scope dimensions** (#1 and #2) are not blockers; if a real disconnect-during-play case appears in playtest, a follow-up story can layer in timeout pruning on top of the state machine.

### OTEL Requirements
Every barrier wait must emit:
- `lobby_participant_count` — total connections in lobby
- `active_turn_count` — players actually taking turns

GM panel must show which count drives the block.

## Workflow Tracking
**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-27T21:53:05Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T20:18:11Z | 2026-04-27T20:20:28Z | 2m 17s |
| red | 2026-04-27T20:20:28Z | 2026-04-27T21:08:46Z | 48m 18s |
| green | 2026-04-27T21:08:46Z | 2026-04-27T21:22:26Z | 13m 40s |
| review | 2026-04-27T21:22:26Z | 2026-04-27T21:33:17Z | 10m 51s |
| red | 2026-04-27T21:33:17Z | 2026-04-27T21:42:05Z | 8m 48s |
| green | 2026-04-27T21:42:05Z | 2026-04-27T21:46:23Z | 4m 18s |
| review | 2026-04-27T21:46:23Z | 2026-04-27T21:53:05Z | 6m 42s |
| finish | 2026-04-27T21:53:05Z | - | - |

## Sm Assessment

**Setup complete.** Story 45-2 ready for TEA red phase.

- **Story type:** Bug fix from Playtest 3 (2026-04-19 evropi session). 3 pts, p1, wire-first.
- **Repo:** sidequest-server only. Branch `feat/45-2-turn-barrier-active-turn-takers` created.
- **Design direction set by Keith (2026-04-27):** Implement fix dimensions #3 + #4 only (explicit lobby states + chargen-abandonment cancels slot). Dimensions #1 (timeout pruning) and #2 (round-0 heuristic) are explicitly out of scope. See `### Fix Dimensions` above for rationale.
- **OTEL requirement is load-bearing:** every barrier wait must emit `lobby_participant_count` AND `active_turn_count` so the GM panel (Sebastien's lie-detector) can show which count gates the wait. Per CLAUDE.md OTEL principle — every backend fix that touches a subsystem MUST add OTEL spans.
- **Wire-first discipline:** boundary tests must exercise the WebSocket transport path, not just internal turn-manager state. The phantom-peer scenario only manifests at the lobby ↔ turn-barrier seam.

**Hand off to:** TEA (Fezzik) for red phase — write failing boundary tests for the lobby state machine + chargen-abandonment transition + OTEL emissions on barrier wait.

## Tea Assessment

**Tests Required:** Yes
**Phase:** finish
**Status:** RED (confirmed — 17/17 new tests failing, 2609 pre-existing pass, zero collateral damage)

### Test Files Written

- `sidequest-server/tests/server/test_lobby_state_machine.py` (NEW, 11 tests) — unit-level state machine: enum, `_Seat.state`, predicates, transitions, OTEL spans, regression for `is_paused()`.
- `sidequest-server/tests/server/test_mp_turn_barrier_active_turn_count.py` (NEW, 6 tests) — wire-first boundary tests via `_handle_player_action`, including the evropi scenario, the negative AC1 test (4 PLAYING — must wait), the disconnect-driven abandonment variant, and three `barrier.wait` OTEL span tests.

**17 tests total** covering all six ACs from `sprint/context/context-story-45-2.md`.

### AC Coverage

| AC | Coverage | Tests |
|----|----------|-------|
| **AC1** Barrier fires only on PLAYING peers | wire-first | `test_barrier_fires_when_only_playing_peer_submits_evropi_scenario`, `test_barrier_does_not_fire_on_one_submission_when_all_are_playing`, `test_barrier_fires_after_chargen_peers_abandon_via_disconnect` |
| **AC2** Lobby state transitions explicit + observable | unit | `test_lobby_state_enum_has_five_named_values`, `test_room_exposes_playing_player_ids_and_count`, `test_seat_after_player_seat_starts_in_chargen_not_playing` |
| **AC3** Chargen-abandonment cancels seat | unit + wire | `test_disconnect_during_chargen_marks_seat_abandoned`, `test_disconnect_while_playing_keeps_seat_in_playing`, `test_barrier_fires_after_chargen_peers_abandon_via_disconnect` |
| **AC4** `barrier.wait` OTEL on every check | wire-first | `test_barrier_wait_span_fires_when_barrier_does_not_fire`, `test_barrier_wait_span_carries_lobby_and_active_counts`, `test_barrier_wait_span_fires_when_barrier_does_fire` |
| **AC5** `lobby.state_transition` + `lobby.seat_abandoned` spans | unit | `test_lobby_state_transition_span_fires_on_seat`, `test_lobby_seat_abandoned_span_fires_on_chargen_disconnect`, `test_no_seat_abandoned_span_when_playing_peer_disconnects` |
| **AC6** Existing pause semantics preserved | regression | `test_is_paused_still_true_for_disconnected_playing_peer`, `test_is_paused_false_when_only_chargen_peer_disconnects`, `test_abandoned_seats_excluded_from_seated_player_count_for_barrier` |

### RED Verification (testing-runner, RUN_ID 45-2-tea-red)

```
Total: 2609 passed, 44 failed, 37 skipped
Story 45-2 expected RED tests: 17 / 17 RED ✓
Pre-existing failures: 27 (unrelated, predate this story — see Delivery Findings)
New failures in pre-existing test files: 0 (zero collateral damage)
```

Failure signatures confirm "missing implementation" RED, not "broken test" RED:

- 10 × `ImportError: cannot import name 'LobbyState' from 'sidequest.server.session_room'` — the new enum doesn't exist yet
- 7 × `AssertionError` on missing methods (`playing_player_ids()`, `playing_player_count()`) and missing OTEL spans (`lobby.state_transition`, `lobby.seat_abandoned`, `barrier.wait`)

These are exactly the Dev surface area: implement the enum, add the `state` field on `_Seat`, add the predicates, wire the transitions at the five sites named in the context (`session_room.py:191/206/216`, `session_handler.py:~2597`, `session_handler.py:3222`), and emit the three OTEL spans.

### Rule Coverage (Python lang-review checklist)

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 Test quality — meaningful assertions | every test in both files asserts a specific value or shape, not just truthiness; no `assert True`, no `assert result`, no vacuous `is_some()` | enforced |
| #6 Test quality — patches at point of use | `barrier.wait` tests patch `sidequest.server.session_handler._watcher_publish` (where the call site lives); state-transition tests patch `_hub.publish_event` (the underlying hub) since transitions may fire from `session_room` | enforced |
| #4 Logging — error-path correctness | not directly applicable to TEA's red-phase tests (no logging code authored); Dev will exercise this at green |  N/A |
| #9 Async/await — no missing await | every `@pytest.mark.asyncio` test awaits handler methods correctly; `fake_execute` is `async def` | enforced |

**Self-check:** zero vacuous assertions. Every assertion checks a specific value, count, member presence, or message-name string. No `let _ =`, no `assert is_some()` on always-None.

**Rules checked:** 4 of 13 applicable Python lang-review rules have direct test-side relevance for this story (others apply to Dev's implementation, not TEA's tests).

### Wire-First Gate Self-Check

Per Epic 45 design theme #3 ("wire-first means the test exercises a real seam"):

- The barrier predicate seam (`session_handler.py:3222`) is exercised end-to-end via `_handle_player_action` in `test_mp_turn_barrier_active_turn_count.py`. ✓
- The chargen → abandoned transition is exercised via `room.disconnect()` (the actual call site) in `test_barrier_fires_after_chargen_peers_abandon_via_disconnect`. ✓
- The `chargen → playing` transition is covered at the unit level (state mutation + predicate) in the state machine file. A full chargen-walk MP test was scoped out — Dev should add one in green if the existing chargen test infrastructure supports it; the architectural scope is covered without it.

**Test fixtures used:** `session_handler_factory` (conftest.py:330) for MP wiring; `_FakeClaudeClient` (conftest.py:195) is auto-active so chargen completes deterministically when needed.

**Handoff:** To Dev (Inigo Montoya) for green phase — implement `LobbyState`, extend `_Seat`, add predicates, wire transitions, register OTEL spans + `SPAN_ROUTES`, and replace `seated_player_count()` with `playing_player_count()` at `session_handler.py:3222`.

## Delivery Findings

No upstream findings during test design.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Improvement** (non-blocking): the `sidequest-server` test suite shows 27 pre-existing failures (unrelated to this story) at the time of RED verification. Affects test hygiene at the epic level — Epic 45 should sweep these before sprint close, since a noisy test run obscures real regressions. *Found by TEA during test design.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- No deviations from spec.

The architect's context (`sprint/context/context-story-45-2.md`) was followed exactly — the test files, AC mappings, OTEL span names, and fixture choices all match the spec. The one judgment call (skipping a real-flow chargen → playing wire-test in `test_chargen_dispatch.py`) is documented in the Wire-First Gate Self-Check above as a scoped omission, not a deviation: the architectural seam is covered at the unit level and Dev can add the wire-flow test in green if their implementation makes it tractable.

## Dev Assessment

**Phase:** finish
**Status:** GREEN (17/17 RED tests now passing; 0 new failures vs RED baseline; 0 new ruff issues)

### Implementation Summary

Implemented the lobby state machine spec from `sprint/context/context-story-45-2.md` exactly. Six files changed, +243/-17 lines.

| File | Change |
|------|--------|
| `sidequest/server/session_room.py` | New `LobbyState` StrEnum (5 states); `_Seat.state` field; new methods `transition_to_playing()`, `playing_player_ids()`, `playing_player_count()`; modified `connect()`, `seat()`, `disconnect()`, `is_paused()` per spec; emits 2 new watcher events |
| `sidequest/server/session_handler.py` | Predicate swap at line 3222 (`seated_player_count` → `playing_player_count`); new `barrier.wait` watcher event on every barrier check (AC4); chargen-confirmation calls `transition_to_playing()` (line ~2989); `_handle_player_seat` returning-player path promotes seat to PLAYING |
| `tests/server/conftest.py` | MP fixture (`session_handler_factory` with `seat_players`) auto-promotes seated peers to PLAYING — preserves backward compat for ~20 pre-existing barrier tests |
| `tests/server/test_mp_cinematic_dispatch.py` | One test (`test_buffered_action_survives_buffer_owner_disconnect`) updated to call `transition_to_playing` before disconnect — pause semantics changed deliberately per spec, test's authorial intent preserved |
| `tests/server/test_mp_turn_barrier_active_turn_count.py` | One test precondition (`test_barrier_fires_after_chargen_peers_abandon_via_disconnect`) made explicit re fixture's auto-promote default |
| `tests/server/test_lobby_state_machine.py` | Auto-formatted by ruff (no semantic changes) |

### State machine wiring (where each LobbyState transition lands)

| Transition | Site | Watcher event |
|------------|------|---------------|
| `(new) → CONNECTED` | `session_room.connect()` | `lobby.state_transition(reason=ws_connect)` |
| `CONNECTED → CHARGEN` | `session_room.seat()` | `lobby.state_transition(reason=seat_claim)` |
| `CHARGEN → PLAYING` | `session_room.transition_to_playing()`, called from `_chargen_confirmation` post-build (`session_handler.py:2989`) and from `_handle_player_seat` returning-player branch | `lobby.state_transition(reason=chargen_complete)` |
| `CHARGEN → ABANDONED` | `session_room.disconnect()` | `lobby.state_transition(reason=chargen_disconnect)` + `lobby.seat_abandoned` |
| `PLAYING → PLAYING` (paused) | `session_room.disconnect()` | (no transition event — pause is observed via `is_paused()` / `absent_seated_player_ids()`) |

`CLAIMING_SEAT` is in the enum for completeness/observability but is not stored on `_Seat` — `seat()` always lands directly at `CHARGEN`. The brief moment between PLAYER_SEAT receipt and `seat()` call is a single function-call edge today; promoting it to a stored state is unnecessary churn. The enum value is exported so future code can use it without an enum change.

### AC Accountability

| AC | Status | Test(s) | Notes |
|----|--------|---------|-------|
| **AC1** Barrier fires only on PLAYING peers (evropi scenario) | DONE | 3 wire-first tests in `test_mp_turn_barrier_active_turn_count.py` | predicate swap at session_handler.py:3228 |
| **AC2** Lobby state transitions explicit + observable | DONE | 3 unit tests in `test_lobby_state_machine.py` | enum + state field + predicates |
| **AC3** Chargen-abandonment cancels seat | DONE | 3 tests across both files (unit + wire-first) | disconnect transitions CHARGEN → ABANDONED |
| **AC4** `barrier.wait` OTEL on every check | DONE | 3 tests in `test_mp_turn_barrier_active_turn_count.py` | emitted in `_handle_player_action` (lines 3239-3251), fires on every barrier check including no-fire waits |
| **AC5** `lobby.state_transition` + `lobby.seat_abandoned` spans | DONE | 3 tests in `test_lobby_state_machine.py` | emitted from session_room at all transition sites |
| **AC6** Existing pause semantics preserved | DONE | 3 regression tests in `test_lobby_state_machine.py`; `test_buffered_action_survives_buffer_owner_disconnect` updated to assert under new semantics | `is_paused()` re-keyed on PLAYING-but-disconnected — abandoned seats no longer pause (this is the explicit spec change) |

**All 6 ACs DONE.** Zero deferred.

### Verification

```
test_lobby_state_machine.py:                  11/11 PASSED ✓
test_mp_turn_barrier_active_turn_count.py:     6/6 PASSED ✓
test_mp_cinematic_dispatch.py (full file):    20/20 PASSED ✓
Full server suite:                            2626 passed, 27 failed, 37 skipped
                                              (27 = pre-existing baseline from RED run; ZERO new failures)
Ruff (changed files):                         0 new issues; 2 pre-existing SIM102/SIM105
                                              at session_handler.py:752/1108 are not in
                                              the lines this story touched
```

### Spec-Authority Hierarchy Applied

The two test edits (one in `test_mp_cinematic_dispatch.py`, one in `test_mp_turn_barrier_active_turn_count.py`) are pre-emption fallouts from the deliberate change to `is_paused()` semantics defined in the story context. Per the Spec Authority Hierarchy: **story scope** (the explicit `is_paused()` change in context-story-45-2.md AC6 / Technical Guardrails) > pre-existing test assertions written under the old semantics. Both test edits preserve the authorial intent of the original test.

### Handoff

To Reviewer (Westley) for review.

## Design Deviations
<!-- continued below -->

### Dev (implementation)

- **Conftest fixture auto-promote vs spec-default state**
  - Spec source: `sprint/context/context-story-45-2.md`, "Reuse, don't reinvent" section + state-machine table
  - Spec text: "Add an explicit lifecycle to `_Seat` — promote it from a `(player_id, character_slot)` pair to a state-bearing dataclass" with default `CHARGEN` after `seat()`.
  - Implementation: `_Seat.state` defaults to `LobbyState.CHARGEN` (matches spec); BUT the conftest MP fixture (`session_handler_factory` with `seat_players`) auto-calls `transition_to_playing()` on each seated peer.
  - Rationale: ~20 pre-existing barrier tests use `seat_players=[...]` to set up "post-chargen, in-game" multiplayer scenarios. They assume seated peers count toward the barrier. Without the fixture's auto-promote, every one of those tests would need explicit `transition_to_playing` calls — large blast radius for no behavioral benefit. The fixture's auto-promote captures its actual intent ("the post-chargen state, ready to play") and preserves backward compat. New tests that need a CHARGEN scenario explicitly override `_seated[pid].state = LobbyState.CHARGEN`.
  - Severity: trivial
  - Forward impact: none — the production code path is unchanged; only the test fixture behaves this way.

- **`SPAN_BARRIER_WAIT` constant + SPAN_ROUTES entry not added**
  - Spec source: `sprint/context/context-story-45-2.md`, OTEL spans table
  - Spec text: "Define in `sidequest/telemetry/spans.py` and register routes in `SPAN_ROUTES`"
  - Implementation: emitted as direct `_watcher_publish("barrier.wait", ...)` calls. Did NOT add a `SPAN_BARRIER_WAIT` constant in `spans.py` or a `SPAN_ROUTES` entry.
  - Rationale: the spec's OTEL guidance was modeled on tracer-span events that flow through SPAN_ROUTES (e.g. `SPAN_GAME_HANDSHAKE_DELTA_APPLIED`). However, the actual barrier event emission pattern in this codebase — including the existing `mp.barrier_fired` and `mp.round_dispatched` — uses direct `_watcher_publish` calls and does NOT register SPAN_ROUTES entries. The TEA tests verify the watcher-event payload (not tracer-span attributes), so following the existing pattern is consistent and minimal. If a tracer-span surface is needed later, this can be layered on without behavioral change.
  - Severity: minor
  - Forward impact: GM panel sees the `barrier.wait` event via the same `_watcher_publish` path as `mp.barrier_fired` today. No follow-up needed unless OTEL tracer-span coverage is later wanted; that would be a separate ADR-031 hygiene story.

- **`CLAIMING_SEAT` is enum-only, not stored**
  - Spec source: `sprint/context/context-story-45-2.md`, state-machine table
  - Spec text: "PLAYER_SEAT received | `connected` → `claiming_seat`"
  - Implementation: `LobbyState.CLAIMING_SEAT` is a member of the enum (the test asserts five named values), but `seat()` lands directly at `CHARGEN`. There is no observable `CLAIMING_SEAT` state on `_Seat`.
  - Rationale: the time between PLAYER_SEAT receipt and `seat()` call is a single function-call edge today (`_handle_player_seat` validates and immediately calls `room.seat()`). Promoting it to a stored state would require a partial-application API surface no current path needs. The enum value is exported so future code can write `LobbyState.CLAIMING_SEAT` without an enum change; only the storage / persistence path is omitted.
  - Severity: trivial
  - Forward impact: none — no consumer reads `CLAIMING_SEAT` today, and the chosen design preserves the spec's enum contract.

- **One test edit per spec-driven semantic shift in `is_paused()`**
  - Spec source: `sprint/context/context-story-45-2.md`, Technical Guardrails (`is_paused()` regression note) + AC6
  - Spec text: "`is_paused()` at session_room.py:299 is the existing predicate the UI's pause banner reads… must continue to return True for `playing`-but-disconnected peers" — combined with AC6's negative test that abandoned-only scenarios do NOT pause.
  - Implementation: `is_paused()` re-keyed on PLAYING-but-disconnected (was: any-seated-but-disconnected). Updated `test_buffered_action_survives_buffer_owner_disconnect` in `test_mp_cinematic_dispatch.py` to call `transition_to_playing()` on its peers before the disconnect, so the test still exercises a paused-with-buffered-action scenario under the new semantics.
  - Rationale: the test's authorial intent ("buffered action survives a disconnect when the game is paused") is preserved by adjusting the precondition; the spec change to `is_paused()` is intentional and documented in AC6.
  - Severity: minor
  - Forward impact: any other test that relied on the old "any-seated-disconnect pauses" semantics would surface during this run. None did — the regression count stayed at the baseline 27.

### Reviewer (audit)

- **Conftest fixture auto-promote vs spec-default state** → ✓ ACCEPTED by Reviewer: pragmatic backward-compat shim; the production `_Seat.state` default is correctly CHARGEN per spec, and the fixture's auto-promote is scoped to test infrastructure with documented opt-out for new CHARGEN-scenario tests.
- **`SPAN_BARRIER_WAIT` constant + SPAN_ROUTES entry not added** → ✓ ACCEPTED by Reviewer: the codebase's actual idiom for barrier events (`mp.barrier_fired`, `mp.round_dispatched`) is direct `_watcher_publish` without SPAN_ROUTES; the spec's tracer-span guidance is over-prescriptive for this surface and consistency with the existing pattern is correct. NOTE: this acceptance is contingent on `mp.round_dispatched.player_count` being internally consistent (see UNDOCUMENTED finding below — currently it is not).
- **`CLAIMING_SEAT` is enum-only, not stored** → ✗ FLAGGED by Reviewer: the rationale is sound, but the `LobbyState` class docstring at `session_room.py:42–44` actively LIES about it: "CONNECTED and CLAIMING_SEAT are observable via the lobby.state_transition watcher event but not stored." CLAIMING_SEAT is in fact NOT observable — no code path emits a state-transition event with `to_state=CLAIMING_SEAT`. The deviation itself is acceptable; the docstring describing it is not. This is finding **C2** in the Reviewer Assessment.
- **One test edit per spec-driven semantic shift in `is_paused()`** → ✓ ACCEPTED by Reviewer: the spec change is explicit (AC6), the test edit preserves authorial intent, and no other tests were affected. Clean.

### Reviewer (audit) — UNDOCUMENTED deviations

The following spec deviations were NOT logged by Dev but are real:

- **`mp.round_dispatched.player_count` reads `seated_player_count()` not `playing_count`:** Spec source: `sprint/context/context-story-45-2.md` Technical Guardrails — barrier-related OTEL must report `active_turn_count` (= playing). Code: `session_handler.py:3302` reports `seated_player_count()`. Internally inconsistent: the very next OTEL emit after the barrier fires uses a different count than the barrier itself evaluated. Severity: HIGH. Finding **R1** in Reviewer Assessment.
- **`barrier.wait.lobby_participant_count` reads raw `seated_count` not "non-abandoned" sum:** Spec source: `sprint/context/context-story-45-2.md` OTEL spans table — "lobby_participant_count (sum across all non-`abandoned` states)". Code: `session_handler.py:3257` reads `seated_player_count()` which includes ABANDONED. Severity: MEDIUM. Finding **A1** in Reviewer Assessment.
- **`LobbyState` docstring claims CLAIMING_SEAT is observable when no code emits it:** Spec source: spec doesn't address this directly, but the docstring asserts behavior that doesn't exist. Severity: HIGH (lying documentation actively misleads future maintainers). Finding **C2** in Reviewer Assessment.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (tests GREEN, no new failures, no new ruff) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.edge_hunter=false) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.silent_failure_hunter=false) |
| 4 | reviewer-test-analyzer | Yes | findings | 8 (2 high, 4 medium, 2 low) | confirmed 4, dismissed 0, deferred 4 (to follow-up — A4/A5/A6/A7/A8 too small for this rework) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (2 high, 1 medium) | confirmed 3, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.type_design=false) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.security=false) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.simplifier=false) |
| 9 | reviewer-rule-checker | Yes | findings | 2 (1 high actionable, 1 minor observation) | confirmed 1, dismissed 1 (R2 — callable() rescued by functional asserts immediately below), deferred 0 |

**All received:** Yes (4 active subagents returned, 5 disabled per settings)
**Total findings:** 8 confirmed, 1 dismissed (with rationale), 4 deferred

## Devil's Advocate

This code passes 17 new tests and the full suite shows zero regressions, but a determined attacker on the lie-detector will find it embarrassing. Sebastien — the mechanical-first audience this story names by name — is going to load the GM panel during a multiplayer session, watch the evropi scenario play out, and see the new `barrier.wait` event report `lobby_participant_count=4, active_turn_count=1`. Then the very next event, `mp.round_dispatched`, will report `player_count=4`. The same numbers Sebastien just trusted to explain why the barrier fired correctly are immediately contradicted by the next OTEL emit. The lie-detector tells two stories. Worse, it uses the same field name (`player_count`) that pre-45-2 code used to mean "seated", inviting Sebastien to assume the inconsistency is a bug in *something else*, not in the barrier fix. The fix that was supposed to make the GM panel honest just introduced a new line of dishonesty in the next event — a Story 14 ("Diamonds and Coal") inversion: a load-bearing observability surface was promoted to coal because Dev checked one site of the predicate swap and missed the second.

A second adversarial scenario: imagine a long-running multiplayer session where a few players have flaked out at chargen over the course of an evening. Each abandonment adds an ABANDONED entry to `_seated`. After three days of organic playtest churn, the room could have 10 ABANDONED seats, 3 PLAYING peers, and 1 CHARGEN peer mid-creation. The barrier itself is correct (only 3 PLAYING count), but `barrier.wait.lobby_participant_count` will report 14 — which is what the Dev's `seated_player_count()` returns. Sebastien sees `lobby_participant_count=14, active_turn_count=3` and concludes "11 phantoms are blocking the game" — but in reality 10 of those are stale abandoned-history entries, not active phantoms. The lie-detector lies again, in the opposite direction this time: it inflates the phantom count instead of suppressing it. The spec was specific about this: "sum across all non-abandoned states." Dev didn't subtract ABANDONED.

A third scenario: the `LobbyState` docstring says CLAIMING_SEAT is observable via lobby.state_transition. A future engineer trying to wire a UI affordance to "show me peers in the seat-claim lifecycle" will trust this docstring, write a subscriber for `to_state=claiming_seat`, and see nothing. They'll spend an hour checking their subscriber's filter. The bug was the docstring all along.

A fourth: there is no test that drives `transition_to_playing()` through `_chargen_confirmation()` end-to-end. The conftest fixture calls `transition_to_playing()` directly on every seated peer, but if Dev had simply *forgotten* to add the `room.transition_to_playing(player_id)` line at `session_handler.py:2999`, the test suite would still pass. The fixture would still promote them, the tests would still see PLAYING peers, and the production seam would silently never fire. CLAUDE.md is firm on this: tests-pass-but-nothing-is-wired is a known failure mode, and AC2 of the story specifically calls for "transitions driven by real WS messages / `_chargen_confirmation()` calls, not by directly mutating `_Seat`." The spec was explicit; the fix is partial.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [RULE] | `mp.round_dispatched.player_count` reads `self._room.seated_player_count()`, contradicting the barrier's `playing_count` evaluated 60 lines earlier. GM panel shows two different numbers for the same round. | `sidequest/server/session_handler.py:3302` | Replace `self._room.seated_player_count()` with `playing_count` (already in scope as a local variable from line 3240). One-line fix. |
| [HIGH] [TEST] | No wire-first test drives `transition_to_playing()` through the production `_chargen_confirmation()` seam. If Dev had forgotten to add `self._room.transition_to_playing(player_id)` at line 2999, no test would catch it (CLAUDE.md "Verify Wiring, Not Just Existence" / AC2). | New test needed in `tests/server/test_chargen_dispatch.py` (or a new MP-chargen wire test file) | Add a wire-first test that walks chargen → confirmation in MP context (using `_FakeClaudeClient`) and asserts `room._seated[pid].state == LobbyState.PLAYING` after confirmation. |
| [HIGH] [DOC] | `LobbyState` docstring at `session_room.py:42–44` claims "CONNECTED and CLAIMING_SEAT are observable via the lobby.state_transition watcher event" but no code path emits a transition with `to_state=CLAIMING_SEAT`. Lying docstring actively misleads. | `sidequest/server/session_room.py:42–44` | Either emit a `lobby.state_transition` event with `to_state=CLAIMING_SEAT` from `_handle_player_seat` (between PLAYER_SEAT receipt and `seat()` call) — OR amend the docstring to: "CONNECTED is observable via lobby.state_transition (emitted in connect()). CLAIMING_SEAT is defined for completeness but is not currently emitted." Choose one and align the deviation log. |
| [MEDIUM] [TEST] [SIMPLE] | `barrier.wait.lobby_participant_count` reads raw `seated_count` (includes ABANDONED) instead of the spec-mandated "sum across all non-abandoned states". The OTEL test cannot catch this because no ABANDONED seat is in the fixture (1 PLAYING + 3 CHARGEN = 4 seated = 4 non-abandoned, indistinguishable). | `sidequest/server/session_handler.py:3257`; test fixture at `tests/server/test_mp_turn_barrier_active_turn_count.py:281–294` | (1) Compute `lobby_participant_count` as `seated_count - abandoned_count` or add a `non_abandoned_player_count()` predicate on `SessionRoom`. (2) Strengthen `test_barrier_wait_span_carries_lobby_and_active_counts`: add a 5th seated peer who was disconnected mid-CHARGEN (ABANDONED), assert `lobby_participant_count == 4` (excluding the abandoned one). |
| [MEDIUM] [DOC] | Pre-existing comment at `session_handler.py:3221–3228` says "Solo rooms (seated_player_count == 1) flip the barrier..." but the predicate is now `playing_player_count`. Solo player must be PLAYING (not just seated) for the barrier to fire. Comment names the wrong predicate. | `sidequest/server/session_handler.py:3221–3228` | Update comment to reference `playing_player_count() == 1` and note that a solo player must reach PLAYING before their first action will fire the barrier. |
| [MEDIUM] [DOC] | `is_paused()` docstring says "the only seats this predicate considers are CHARGEN-but-still-connected (no pause needed) and PLAYING (the original pause case)" — omits ABANDONED seats which are also iterated by the `any()` and silently filtered. | `sidequest/server/session_room.py:460–462` | Amend docstring: explicitly note that ABANDONED seats are excluded because `state != PLAYING`, and only PLAYING-but-disconnected peers trigger pause. |
| [MEDIUM] [TEST] | No test asserts that `transition_to_playing()` itself emits `lobby.state_transition` with `to_state=playing`. The CHARGEN → PLAYING edge — the most load-bearing transition for the GM panel — has zero direct OTEL coverage. | New test in `tests/server/test_lobby_state_machine.py` | Mirror `test_lobby_state_transition_span_fires_on_seat`: capture spans via `_hub.publish_event` swap, call `room.transition_to_playing()`, assert a span with `to_state in ("playing", "PLAYING")` and `reason == "chargen_complete"` fires. |

**Data flow traced:** The killer path — playtest 3 evropi scenario — is correctly fixed at `session_handler.py:3242` (`set_player_count(playing_count)`). With 4 seated peers (1 PLAYING + 3 CHARGEN), the barrier sees player_count=1 and fires on Rux's solo submission. The state-machine model (`LobbyState` enum, `_Seat.state` field, `transition_to_playing()` helper) is sound and the locking is correct (RLock acquired for state mutation, released before `_hub.publish_event` to avoid holding the lock across patched callables). [VERIFIED] The barrier predicate seam at `session_handler.py:3242` reads `playing_count` derived from `room.playing_player_count()` — evidence: code at line 3240 explicitly calls the new method.

**Pattern observed:** [VERIFIED] State machine is implemented as a true state machine (transitions named, idempotent on no-op, lock-protected) — not as a parallel boolean. Evidence: `transition_to_playing()` at `session_room.py:323–351` reads → checks → writes under lock, then emits outside the lock. Compare with `disconnect()` at line 255–296 which uses the same pattern. This matches Epic 45 design theme #1 ("explicit lifecycle states beat implicit booleans").

**Error handling:** [VERIFIED] `transition_to_playing()` is idempotent and safe under the returning-player race (no seat → silent return; already PLAYING → silent return without duplicate event). Both no-op paths are documented. [VERIFIED] `disconnect()` correctly captures the abandon payload under the lock and emits outside, avoiding lock-during-IO. Evidence: `session_room.py:260–296`.

**Wiring:** [VERIFIED] `transition_to_playing()` IS called from production code at two sites: `session_handler.py:1149` (`_handle_player_seat` returning-player branch) and `session_handler.py:2999` (`_chargen_confirmation` post-build). [SEMI-VERIFIED] The chargen → barrier seam is wired correctly (Dev did the work), but per [HIGH] finding above, no test exercises this end-to-end — so wiring is not test-verified.

**Security analysis:** [VERIFIED] No new user-input boundaries introduced. `player_id` and `socket_id` come from already-validated WebSocket session dispatch. `LobbyState` values are server-controlled, never user-supplied. No SQL, no HTML, no path operations changed.

**Devil's Advocate consequences:** Two scenarios from the section above translate into the [HIGH] and [MEDIUM] findings on `mp.round_dispatched.player_count` and `barrier.wait.lobby_participant_count`. The lying-docstring scenario is the [HIGH] CLAIMING_SEAT finding. The missing-wire-test scenario is the [HIGH] AC2 finding.

**Tags applied:** [EDGE] [SILENT] [TEST] [DOC] [TYPE] [SEC] [SIMPLE] [RULE] — all 8 tags accounted for in the findings table or the Subagent Results section above (EDGE/SILENT/TYPE/SEC/SIMPLE subagents disabled per settings; their domains were spot-checked by Reviewer's own analysis: edge cases (disconnect-during-CHARGEN-ABANDONED-reclaim path is sound), silent failures (transition_to_playing no-ops are documented and intentional), type design (LobbyState as StrEnum is correct), security (no new boundaries), simplification (no over-engineering — the state machine fits the surface area).

**Handoff:** Back to TEA for red rework. Findings R1 + A1 require a strengthened OTEL test with ABANDONED in the fixture; Finding A3 requires a new wire-first test for chargen → playing → barrier through `_chargen_confirmation()`; Finding A2 requires a unit test for `transition_to_playing` OTEL emission. Once tests exist, Dev follows up with the three code fixes (R1: `mp.round_dispatched.player_count`; A1: `barrier.wait.lobby_participant_count`; C2: `LobbyState` docstring) and the two MEDIUM doc fixes (C1, C3). Total scope: ~3-4 small test additions + ~5 line edits in production code + 3 doc fixes. Estimate: under 60 minutes total rework.

### Rule Compliance

Per `.pennyfarthing/gates/lang-review/python.md` (13 numbered checks). The reviewer-rule-checker subagent enumerated 89 instances; below is the consolidated map.

| Rule | Result | Evidence |
|------|--------|----------|
| #1 Silent exception swallowing | PASS | No new bare excepts or swallowed errors. The pre-existing `except Exception: pass` at session_handler.py:1110 is not in this diff (pre-existing SIM105 noted by ruff). |
| #2 Mutable default arguments | PASS | All dataclass fields use `field(default_factory=...)` for mutables; new code uses immutable defaults (str, str|None, LobbyState enum). |
| #3 Type annotation gaps | PASS | All new public methods on SessionRoom annotated. Test helpers (private) exempt per rule wording. |
| #4 Logging coverage AND correctness | PASS for new code | session_room.py is intentionally logger-free (architectural — logging happens in session_handler). The architectural decision is consistent with the existing module. The MP_round_dispatched player_count divergence (R1) is an OTEL-payload issue, not a logging-level issue. |
| #5 Path handling | PASS | No new path operations. |
| #6 Test quality | PASS with notes | All new tests have meaningful assertions; mock targets correctly aim at usage site (session_handler._watcher_publish) or hub module attribute (_hub.publish_event). callable(getattr) at test_lobby_state_machine.py:65–68 is rescued by the immediate functional asserts. NOTE: `barrier.wait` test fixture lacks an ABANDONED peer (Finding A1) — a coverage gap, not a vacuous-assertion violation. |
| #7 Resource leaks | PASS | No new resources opened without context manager. |
| #8 Unsafe deserialization | PASS | No pickle/yaml.load/eval. |
| #9 Async/await pitfalls | PASS | All `await` calls correct. Sync calls into `_hub.publish_event` from `connect/disconnect/seat/transition_to_playing` are fire-and-forget and consistent with the existing pattern. No blocking calls in async functions. |
| #10 Import hygiene | PASS | No star imports, no new circular imports. `from enum import StrEnum` and `import sidequest.telemetry.watcher_hub as _hub` are explicit. |
| #11 Input validation at boundaries | PASS | No new user-input boundaries. |
| #12 Dependency hygiene | PASS | pyproject.toml unchanged. |
| #13 Fix-introduced regressions | FAIL | The fix introduced `mp.round_dispatched.player_count` divergence — Dev correctly updated `mp.barrier_fired.player_count` at line 3274 but missed the symmetric update at line 3302. This is exactly the meta-check #13 was written to catch.

## Tea Assessment (rework round 2)

**Phase:** finish (rework)
**Status:** RED targeted (2 of 3 code findings now have failing tests; 4 of 4 test-coverage findings now have GREEN passing tests)

### Reviewer findings → test mapping

| Reviewer finding | TEA action | Test status |
|------------------|------------|-------------|
| **R1** (HIGH) `mp.round_dispatched.player_count` divergence at session_handler.py:3302 | NEW test `test_mp_round_dispatched_player_count_matches_barrier_predicate` pins cross-event consistency | RED — Dev fix needed |
| **A1** (MEDIUM) `barrier.wait.lobby_participant_count` includes ABANDONED | STRENGTHENED `test_barrier_wait_span_carries_lobby_and_active_counts`: added 5th ABANDONED peer to fixture | RED — Dev fix needed |
| **A2** (MEDIUM) No test for `transition_to_playing` OTEL span | NEW tests `test_transition_to_playing_emits_state_transition_span` + `test_transition_to_playing_is_idempotent_no_duplicate_span` | GREEN — code already correct, now test-covered |
| **A3** (HIGH) No wire-first test for chargen → PLAYING seam | NEW FILE `tests/server/test_45_2_chargen_to_playing_wire.py` — drives slug-connect chargen flow end-to-end with caverns_and_claudes | GREEN — code already correct, now wire-tested |
| **C1** (MEDIUM) Stale comment session_handler.py:3221-3228 about "Solo rooms (seated_player_count == 1)" | No test (documentation) — flagged for Dev manual fix | Doc fix |
| **C2** (HIGH) LobbyState docstring lies about CLAIMING_SEAT observability | No test (documentation) — flagged for Dev manual fix | Doc fix |
| **C3** (MEDIUM) is_paused docstring inaccurate about seat states "considered" | No test (documentation) — flagged for Dev manual fix | Doc fix |

### Test counts (round 2 delta)

```
Round 1 final: 17 new tests, all GREEN at hand-off (then RED via Reviewer audit).
Round 2 added: 4 new tests (3 GREEN, 0 RED standalone) + 1 strengthened (now RED).

After round 2:
  test_lobby_state_machine.py:                    11 + 2 new = 13 (all GREEN)
  test_mp_turn_barrier_active_turn_count.py:       6 + 1 new = 7 (5 GREEN, 2 RED)
  test_45_2_chargen_to_playing_wire.py:                  NEW = 1 (GREEN)
  -----------------------------------------------------------------
  Total new + strengthened:                              21 tests
  GREEN now:                                             19
  RED for Dev to fix:                                     2 (R1, A1)
```

### RED Verification (round 2)

```
Targeted suite (3 files):  19 passed, 2 failed (the 2 expected RED)
Full server suite:         2628 passed, 29 failed, 37 skipped
                           29 = 27 pre-existing baseline + 2 new RED
                           Zero collateral damage in pre-existing tests
```

The 2 RED tests both fail with descriptive messages naming the exact line that needs to change:

- `test_barrier_wait_span_carries_lobby_and_active_counts` — fails with "If this is 5, the implementation is using raw seated_player_count() which incorrectly counts ABANDONED slots."
- `test_mp_round_dispatched_player_count_matches_barrier_predicate` — fails with "If this is 4, session_handler.py:3302 is still reading seated_player_count() instead of playing_count."

Dev should be able to address both in <10 minutes:
- R1: change `self._room.seated_player_count()` → `playing_count` at session_handler.py:3302 (one line)
- A1: replace `seated_count = self._room.seated_player_count()` at session_handler.py:3257 with a non-abandoned count, or add a `non_abandoned_player_count()` predicate on SessionRoom that filters out `state == ABANDONED`. Recommended: add the predicate (small, named, testable) over inline subtraction.

Plus three doc edits (C1, C2, C3) per the Reviewer Assessment severity table.

### Wire-First Self-Check (round 2)

Per Epic 45 design theme #3 ("wire-first means the test exercises a real seam"):

- The chargen → PLAYING seam at `session_handler.py:2999` is now exercised end-to-end via `test_chargen_confirmation_transitions_seat_to_playing` — slug-connect → PLAYER_SEAT → walk caverns chargen → confirmation → assert `_seated[player_id].state == PLAYING`. ✓
- The `mp.round_dispatched` consistency seam is now exercised via `test_mp_round_dispatched_player_count_matches_barrier_predicate` — driving `_handle_player_action` end-to-end and pinning all three OTEL events to the same player_count value. ✓
- The `lobby_participant_count` non-abandoned semantic is now testable (the fixture distinguishes raw seated from non-abandoned). ✓

CLAUDE.md "Verify Wiring, Not Just Existence" gap closed: if `session_handler.py:2999` is removed, `test_chargen_confirmation_transitions_seat_to_playing` will fail with "After _chargen_confirmation success, seat MUST transition to PLAYING."

### Deviation Log (round 2)

- No deviations from the Reviewer's findings. All 7 findings (3 HIGH, 4 MEDIUM) addressed: 2 RED tests written for code-fix findings, 3 GREEN tests written for missing-test findings, 3 doc fixes flagged for Dev manual application.

**Handoff:** To Dev (Inigo Montoya) for green rework — apply 2 small code fixes (R1, A1) to make the RED tests GREEN, plus 3 doc edits (C1, C2, C3) to address the Reviewer's documentation findings.

## Dev Assessment (rework round 2)

**Phase:** finish (rework)
**Status:** GREEN (21/21 Story-45-2 tests passing; 0 new failures vs pre-existing baseline; 0 new ruff issues)

### Reviewer findings → Dev fix mapping

| Reviewer finding | Dev fix | File:line | Verification |
|------------------|---------|-----------|--------------|
| **R1** (HIGH) `mp.round_dispatched.player_count` divergence | One-line edit: `self._room.seated_player_count()` → `playing_count` (in scope as local from line 3240) | `session_handler.py:3308` | `test_mp_round_dispatched_player_count_matches_barrier_predicate` GREEN |
| **A1** (MEDIUM) `barrier.wait.lobby_participant_count` includes ABANDONED | Added `SessionRoom.non_abandoned_player_count()` predicate (filters `state != ABANDONED`); replaced `seated_count` source at the barrier emit site | `session_room.py:non_abandoned_player_count`, `session_handler.py:3243-3244` | `test_barrier_wait_span_carries_lobby_and_active_counts` GREEN |
| **C1** (MEDIUM) Stale "Solo rooms (seated_player_count == 1)" comment | Updated comment to reference `playing_player_count() == 1` and note the chargen → PLAYING precondition for solo barrier fire | `session_handler.py:3221-3230` | Doc edit (visual review) |
| **C2** (HIGH) LobbyState docstring lies about CLAIMING_SEAT observability | Rewrote storage/observability paragraph: CONNECTED emitted-not-stored, CLAIMING_SEAT reserved-for-forward-extensibility (not currently emitted) | `session_room.py:31-54` | Doc edit (visual review) |
| **C3** (MEDIUM) `is_paused` docstring inaccurate about "considered" seat states | Rewrote iteration paragraph: predicate iterates every seat in `_seated` (including ABANDONED) and filters by `state == PLAYING`; ABANDONED stays in `_seated` for forensics but never contributes to pause | `session_room.py:is_paused` | Doc edit (visual review) |

All 7 Reviewer findings addressed. Two HIGH and one MEDIUM are now test-protected (R1, A1, plus the chargen→PLAYING wire seam from TEA round 2 which is GREEN with the wire test in place).

### Verification

```
test_lobby_state_machine.py:                       13/13 PASSED ✓
test_mp_turn_barrier_active_turn_count.py:          7/7  PASSED ✓
test_45_2_chargen_to_playing_wire.py:               1/1  PASSED ✓
Story 45-2 total:                                  21/21 PASSED ✓

Full server suite:    2630 passed, 27 failed (= pre-existing baseline), 37 skipped
                      0 new failures introduced by this rework.
Ruff (changed files): 0 new issues.
```

### Spec-Authority Hierarchy Applied

The new `non_abandoned_player_count()` predicate name was chosen to honor the spec text directly — `sprint/context/context-story-45-2.md` says "lobby_participant_count (sum across all non-`abandoned` states)". The predicate name surfaces this contract; future readers searching for "where does lobby_participant_count come from" find a predicate that names the spec's exclusion rule.

### Cross-Story Impact

`non_abandoned_player_count()` is a public predicate on `SessionRoom`. It joins the existing predicate family (`connected_player_ids`, `seated_player_ids`, `absent_seated_player_ids`, `playing_player_ids`, `playing_player_count`). No other call sites today; available for any future GM-panel telemetry that wants the same "active lobby members, not historical orphans" semantics.

### Handoff

To Reviewer (Westley) for re-review. The 5 fixes are surgical (one-line, one new predicate + 2 site edits, three doc paragraphs) and all map directly to the prior Reviewer findings. Round-trip count is now 1.

## Design Deviations
<!-- continued below -->

### Dev (rework round 2)

- No deviations from the Reviewer's findings. All 7 (R1/A1/A2/A3/C1/C2/C3) addressed:
  - **R1, A1** → code fixes turn the round-2 RED tests GREEN.
  - **A2, A3** → tests written by TEA in round 2; production code already correct from round 1, now test-covered.
  - **C1, C2, C3** → documentation aligned with implementation.

### Reviewer (audit) — round 2

All round-1 deviations and findings re-audited against the rework delta:

- **R1** `mp.round_dispatched.player_count` → ✓ FIXED. Verified at `session_handler.py:3311` reads `playing_count` (local from line 3244). Cross-event consistency restored.
- **A1** `lobby_participant_count` excludes ABANDONED → ✓ FIXED. New `SessionRoom.non_abandoned_player_count()` predicate added at `session_room.py:397–415`; barrier emit at `session_handler.py:3245` uses it. Test fixture strengthened with 5th ABANDONED peer.
- **A2** OTEL coverage for `transition_to_playing` → ✓ TEST ADDED. Direct + idempotent negative-case tests at `test_lobby_state_machine.py`.
- **A3** Wire-first chargen→PLAYING seam → ✓ WIRE TEST ADDED. `tests/server/test_45_2_chargen_to_playing_wire.py` walks slug-connect → PLAYER_SEAT → chargen scenes → confirmation in MP context with caverns_and_claudes. Pins `session_handler.py:2999`.
- **C1** Stale Solo-rooms comment → ✓ FIXED. `session_handler.py:3221–3230` references `playing_player_count()` and the chargen→PLAYING precondition.
- **C2** LobbyState CLAIMING_SEAT lie → ✓ FIXED. `session_room.py:31–55` accurately documents CONNECTED as emitted-not-stored, CLAIMING_SEAT as reserved-not-emitted.
- **C3** `is_paused` docstring → ✓ FIXED. `session_room.py:478–492` correctly explains iteration semantics + ABANDONED exclusion via the filter.

### Reviewer (audit) — UNDOCUMENTED deviations (round 2)

Two new minor doc-vs-code drifts introduced in the round-2 test additions (TEA-authored). Non-blocking but flagged so they don't compound:

- **Stale "RED today" docstring on now-GREEN test:** `tests/server/test_mp_turn_barrier_active_turn_count.py:430` — `test_mp_round_dispatched_player_count_matches_barrier_predicate` docstring says "RED today: mp.round_dispatched.player_count == 4 because session_handler.py:3302 still calls seated_player_count()." Dev's fix made it GREEN; the docstring was not updated. Same shape as round 1's CLAIMING_SEAT lie but in an internal test file, not a public class API. Severity: MEDIUM.
- **Stale line number in assertion message:** `tests/server/test_mp_turn_barrier_active_turn_count.py:508` — assertion message says "If this is 4, session_handler.py:3302 is still reading seated_player_count()" but line 3302 is now inside the `_watcher_publish` dict body. The fix line is 3311. A future debugger landing here would look at the wrong line. Severity: MEDIUM.

## Subagent Results (round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 4 (all LOW lint — F401 unused imports + I001 order in test files) | confirmed 4, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 6 (1 MEDIUM truthy-assert + 5 LOW coverage/casing) | confirmed 1, dismissed 1 (skip-guard false alarm), deferred 4 (LOW coverage nits) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (2 MEDIUM stale TDD comments + 1 LOW framing) | confirmed 3, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 (1 Rule#6 truthy assert + 1 Rule#10 unused import) | confirmed 2 (corroborate preflight + test-analyzer), dismissed 0, deferred 0 |

**All received:** Yes (4 active subagents returned, 5 disabled per settings)
**Total findings:** 8 confirmed (after dedup), 1 dismissed (skip-guard false alarm), 4 deferred (LOW coverage nits)

**Cross-corroboration check:** the round-1 high-severity findings (R1, A1, A2, A3, C1, C2, C3) were all flagged by multiple subagents as RESOLVED in round 2 — preflight saw 21/21 GREEN + zero new failures; rule-checker explicitly verified the Rule #13 fix at `session_handler.py:3311`; comment-analyzer verified C1/C2/C3 docstring fixes; test-analyzer noted the strengthened ABANDONED fixture. No subagent challenges any prior fix.

## Devil's Advocate (round 2)

Round 1's adversarial scenarios — Sebastien seeing two different player_counts on the same round, the lobby_participant_count inflating with abandoned-history orphans, the lying CLAIMING_SEAT docstring, and the missing chargen→PLAYING wire-test — are all closed. The fixes are surgical and verified at file:line. The new code (`non_abandoned_player_count`) follows the existing predicate-family pattern with proper lock discipline.

The remaining concerns are second-order: a malicious / confused engineer reading a test docstring that says "RED today" might run the test, see GREEN, and lose 30 seconds figuring out the docstring is stale. The truthy `assert out` at line 123 of the wire test would let a regression in `handle_message` return the wrong message type without failing — but the test's load-bearing assertion (seat is PLAYING after confirmation) would still catch the underlying bug. The unused imports and import-order issues are pure tooling churn; they cause no behavior. None of these are story-blocking.

What I cannot find in this rework: a regression in the prior fixes, a new logic bug, a security exposure, a wire-test gap that was previously absent and now still is, a stale comment on a public API, or any divergence between the spec and the implementation. Adversarially, the story is shippable.

## Reviewer Assessment (round 2)

**Verdict:** APPROVED

| Severity | Issue | Location | Fix Recommended (non-blocking) |
|----------|-------|----------|--------------------------------|
| [MEDIUM] [TEST] [RULE] | Stale "RED today" docstring on now-GREEN test | `tests/server/test_mp_turn_barrier_active_turn_count.py:430` | Replace the RED paragraph with a GREEN statement reflecting the fix at `session_handler.py:3311`. |
| [MEDIUM] [DOC] | Stale line number in assertion message ("session_handler.py:3302") | `tests/server/test_mp_turn_barrier_active_turn_count.py:508` | Update to reference the current `mp.round_dispatched` `_watcher_publish` site (~line 3311). |
| [MEDIUM] [TEST] [RULE] | Bare truthy `assert out, "connect must produce SESSION_CONNECTED"` | `tests/server/test_45_2_chargen_to_playing_wire.py:123` | Replace with type-checking assertion: `assert any(getattr(m, 'type', None) == 'SESSION_CONNECTED' for m in out)`. |
| [LOW] [RULE] | Unused imports `SessionEventMessage`, `SessionEventPayload` (F401) | `tests/server/test_45_2_chargen_to_playing_wire.py:39–40` | `uv run ruff check --fix tests/server/test_45_2_chargen_to_playing_wire.py` |
| [LOW] [RULE] | Unused local `LobbyState` import (F401) | `tests/server/test_lobby_state_machine.py:439` | `uv run ruff check --fix tests/server/test_lobby_state_machine.py` |
| [LOW] [RULE] | I001 import order | `tests/server/test_45_2_chargen_to_playing_wire.py` | Same `--fix` invocation as above. |
| [LOW] [DOC] | "Other direction" framing in `non_abandoned_player_count` docstring | `sidequest/server/session_room.py:405` | Replace "filters in the other direction (only PLAYING)" with "requires `state == PLAYING`; a CHARGEN seat is counted here but not there." |
| [LOW] [TEST] | from_state OR-clause accepts both 'chargen' and 'CHARGEN' (StrEnum always emits lowercase) | `tests/server/test_lobby_state_machine.py:471, 474` | Tighten to exact equality; the uppercase branch is dead. |

**Why APPROVED despite 8 findings:** All 7 round-1 blocking findings are verifiably closed (5 code fixes + 2 missing tests added). The round-2 findings are all in test files / internal docstrings / lint, with zero CRITICAL or HIGH. Per the severity rubric, only Critical and High block the verdict. The MEDIUM cluster is doc-vs-code drift TEA introduced in their own round-2 additions (the `RED today` markers were boilerplate from the failing-test phase that didn't get updated when Dev's fix made them GREEN — the same shape of drift that was the round-1 blocker, but contained in test docstrings rather than a public API). The fixes are mechanical (4× `ruff --fix`, 3 docstring edits, 1 assertion strengthening) and well within the scope of an SM-coordinated cleanup commit before merge.

**Data flow traced (round 2 delta):** [VERIFIED] Sebastien's lie-detector now reads consistent counts across all three barrier-related events for a single round. Evidence: `session_handler.py:3244` captures `playing_count` once; `barrier.wait` (line 3261) reads it as `active_turn_count`; `mp.barrier_fired` (line 3278) reads it as `player_count`; `mp.round_dispatched` (line 3311) reads it as `player_count`. All four paths read from the same local variable — divergence is structurally impossible. [VERIFIED] `lobby_participant_count` (line 3261) reads from `non_abandoned_player_count()` which filters out ABANDONED seats — `session_room.py:407–415` evidence: `sum(1 for seat in self._seated.values() if seat.state != LobbyState.ABANDONED)`.

**Pattern observed:** [VERIFIED] The new predicate joins the existing `*_player_ids()` / `*_player_count()` family on `SessionRoom` cleanly. Naming convention preserved (`non_abandoned_player_count` parallels `playing_player_count`). Lock acquired with same idiom (`with self._lock`). Implementation chooses sum-with-generator over list-and-len, mildly more efficient for the count-only use-case but consistent with surrounding style.

**Error handling:** [VERIFIED] No new error paths in the rework. Existing idempotency / no-op paths in `transition_to_playing` and `disconnect` unchanged.

**Wiring:** [VERIFIED] The new wire-first test `test_chargen_confirmation_transitions_seat_to_playing` exercises `session_handler.py:2999` end-to-end via `handle_message` dispatch through caverns_and_claudes chargen content. Evidence: lines 186–204 of the wire test send a real CHARACTER_CREATION confirmation message and assert the seat is in PLAYING state afterward, with a diagnostic message naming the load-bearing line. If `session_handler.py:2999` is removed, the test fails with a clear error.

**Security analysis:** [VERIFIED] No new boundaries, no user-input changes, no auth or tenant changes. Pure additive predicate + OTEL field renames in the rework delta.

**Tags applied:** [TEST] [DOC] [RULE] across all 8 findings. EDGE/SILENT/TYPE/SEC/SIMPLE subagents disabled per settings; their domains were spot-checked by Reviewer's own code reads (no edge cases or silent failures introduced; type design follows existing predicate-family pattern; security boundary unchanged; no over-engineering — `non_abandoned_player_count` is a 4-line method with a clear contract).

**Handoff:** To SM (Vizzini) for finish-story. The cleanup items (8 findings, MEDIUM and LOW) can be addressed in a `chore(45-2): post-review cleanup` commit before merge — recommend SM coordinate this with Dev as a quick sweep prior to PR creation. Alternatively, file as a small follow-up story; the production behavior is correct and ship-ready as-is.

### Rule Compliance (round 2 — delta-only)

Per `.pennyfarthing/gates/lang-review/python.md`. Round 1's exhaustive 89-instance pass remains valid; this is the round-2 delta check.

| Rule | Result | Evidence |
|------|--------|----------|
| #1 Silent exception swallowing | PASS | No new try/except in the rework delta. |
| #2 Mutable default arguments | PASS | `non_abandoned_player_count` has no params. Test helpers use immutable defaults. |
| #3 Type annotation gaps | PASS | `non_abandoned_player_count(self) -> int` annotated; new test helpers annotated. |
| #4 Logging | PASS | No new error paths added. |
| #5 Path handling | PASS | Wire test uses `pathlib.Path` correctly. |
| #6 Test quality | FAIL (LOW) | T1 truthy `assert out` at wire test:123. Other 19 round-2 assertions are specific. |
| #7 Resource leaks | PASS | `_seed_mp_save` SqliteStore opens, populates, closes — explicit close in non-exception path is fine for test-only seeding. |
| #8 Unsafe deserialization | PASS | `GameMessage.model_validate` is Pydantic, not pickle/yaml. |
| #9 Async/await | PASS | All `await` calls correct in the wire test; new tests properly `@pytest.mark.asyncio` via auto mode. |
| #10 Import hygiene | FAIL (LOW) | T2/T3 unused imports in test files; T4 import order. |
| #11 Input validation | PASS | No new boundaries. |
| #12 Dependency hygiene | PASS | No pyproject changes. |
| #13 Fix-introduced regressions | PASS | The Rule #13 fix from round 1 is verified genuine; no new regressions introduced. |