---
story_id: "67-1"
jira_key: null
epic: "67"
workflow: "tdd"
---

# Story 67-1: GameBoard render crash must not orphan the table's turn — survive client subtree errors server-side

## Story Details

- **ID:** 67-1
- **Epic:** 67 — Multiplayer resilience & presence
- **Jira Key:** None (SideQuest uses sprint YAML, not Jira)
- **Workflow:** tdd
- **Points:** 5
- **Priority:** p1
- **Type:** bug
- **Repos:** server, ui
- **Stack Parent:** none (independent)

## Acceptance Criteria

From epic 67 description (sq-playtest-pingpong.md finding):

A client-side GameBoard render crash must not tear down the WebSocket and orphan the whole table's in-flight turn.

**Acceptance Criteria (SM-derived — superseded by the crash-signal mechanism per TEA Conflict + Architect Option-A; see Delivery Findings):**
1. When a GameBoard subtree throws an error during render, the error boundary prevents the crash from propagating to the WebSocket layer.
2. The server's turn state is applied and persisted server-side *before* narration is rendered client-side.
3. On client reconnect, the server replays the persisted turn state so the table's turn is not lost.
4. A player who experiences a render crash can recover without orphaning other players' sessions.

**Implemented mechanism (authoritative, Keith-confirmed 2026-05-26):** a crashed client's ErrorBoundary sends `CLIENT_ERROR` over its still-open socket; the server drops it from the current interaction's barrier denominator (`effective_barrier_count` = PLAYING − crash-released) and re-evaluates the submit-and-wait barrier, dispatching with the remaining submitters. Releases ONLY on an explicit crash signal — never on a quiet slow typist.

## Epic Context (67 — Multiplayer resilience & presence)

**Playtest-3 findings:** MP turn/socket robustness and shared-turn presence.

Related stories in epic:
- 67-2: ACTION_REVEAL delivery resilience — retry/backfill on reconnect so a sealed peer never stalls at Composing
- 67-3: MP peer-visibility consolidation + slow-typist reassurance (one canonical surface, Composing/Sealed/Resolving)
- 67-4: MP identity mapping (player-vs-character) — stop rendering doubled 'X— X' header

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-26T13:08:28Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-26T10:03:53Z | 2026-05-26T10:10:37Z | 6m 44s |
| red | 2026-05-26T10:10:37Z | 2026-05-26T12:19:50Z | 2h 9m |
| green | 2026-05-26T12:19:50Z | 2026-05-26T12:33:52Z | 14m 2s |
| spec-check | 2026-05-26T12:33:52Z | 2026-05-26T12:36:30Z | 2m 38s (handed back to Dev — Major 3+ player gap) |
| green | 2026-05-26T12:36:30Z | 2026-05-26T12:49:00Z | 12m 30s |
| spec-check | 2026-05-26T12:49:00Z | 2026-05-26T12:49:50Z | 50s |
| verify | 2026-05-26T12:49:50Z | 2026-05-26T12:53:32Z | 3m 42s |
| review | 2026-05-26T12:53:32Z | 2026-05-26T12:58:53Z | 5m 21s |
| green | 2026-05-26T12:58:53Z | 2026-05-26T13:02:57Z | 4m 4s |
| spec-check | 2026-05-26T13:02:57Z | 2026-05-26T13:03:32Z | 35s |
| verify | 2026-05-26T13:03:32Z | 2026-05-26T13:04:29Z | 57s |
| review | 2026-05-26T13:04:29Z | 2026-05-26T13:07:30Z | 3m 1s |
| spec-reconcile | 2026-05-26T13:07:30Z | 2026-05-26T13:08:28Z | 58s |
| finish | 2026-05-26T13:08:28Z | - | - |

> NOTE: This session file was clobbered by a testing-runner cache-write (memory: testing-runner clobbers session files — it writes `.session/{STORY_ID}-session.md`) during the green rework and reconstructed from conversation context 2026-05-26. All assessments/findings/deviations below are restored verbatim.

## Sm Assessment

Setup complete; routing to TEA (Igor) for the RED phase. Verified the merge gate is clear (no open PRs), both repos branched (`feat/67-1-gameboard-crash-server-survive-turn` on sidequest-server and sidequest-ui off `develop`), and story marked `in_progress`. Parent epic context (`context-epic-67.md`) and story context (`context-story-67-1.md`) authored and validated.

**Load-bearing handoff note for TEA:** this is a *verify-and-close-the-gap* story, not greenfield. Setup recon found the resilience substrate already largely exists — GameBoard is already wrapped in `ErrorBoundary name="Game"` (`sidequest-ui/src/App.tsx:2019`), the server already persists each turn (`websocket_session_handler.py:3996-4044`), and reconnect already replays per-player filtered events (`handlers/connect.py:1073-1270`). Write failing tests that reproduce the *orphaned-turn* scenario first; the fix is closing the recovery/teardown coupling gap, not rebuilding working pieces. The story body has NO authored ACs — the five in `context-story-67-1.md` are SM-derived from the epic. Respect the ADR-104/105 perception firewall, and emit an OTEL watcher event on the survival/replay seam. No silent fallbacks.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected
**Mismatches Found:** 2 (1 Major — handed back & now fixed; 1 intentional — Option A)

- **Crash-release denominator NOT honored by the normal submit path (3+ player stall)** (Different behavior — Behavioral, **Major**)
  - Code: `client_error.py` reduced the denominator via crash-release, but `player_action.py:498` set `playing_count = playing_player_count()` (crashed player still PLAYING, still counted).
  - Trace (3 PLAYING): p1 submits → p2 crashes (effective 2, 1≥2 no fire) → p3 submits → `set_player_count(3)` resets denominator, 2≥3 → barrier never fires. Turn orphaned. The crash-release only worked when the crash itself was the last awaited slot (the 2-player tests).
  - Recommendation: **B — fix code.** Centralize via `SessionRoom.effective_barrier_count()` used by BOTH paths; add a 3-player regression. → **RESOLVED in green rework (see Dev Assessment Rework).**
- **Implementation targets crash-signal, not stale context ACs** (Architectural, Minor; already resolved)
  - Recommendation: **A — update spec.** Correct mechanism (Keith-confirmed); context ACs should be rewritten. No code action. For spec-reconcile/SM.

**Decision (round 1):** Handed back to Dev for the Major gap. Re-check pending after rework.

**Decision (round 3, 2026-05-26, post-review-rework):** No new spec drift. The Reviewer's security fix (bind `crashed_id` to `sd.player_id`; reject unresolvable player; underflow warn) is pure hardening that *strengthens* ADR-104/105 Agency — it removes the player-eviction vector rather than changing the feature contract. Verified by code read + 67-1 suite 10/10 + 28 regression GREEN. **Proceed to verify (TEA).**

**Decision (round 2, 2026-05-26):** Major gap RESOLVED. Verified the fix by code read: `SessionRoom.effective_barrier_count()` (PLAYING − crash-released) is now the single denominator, consumed by `player_action.py:498` (normal submit) and `client_error.py` (crash path) — the 3-player stall trace no longer holds (p3's submit is measured against effective 2, fires on {p1,p3}). The new `test_crash_release_in_three_player_room_then_remaining_submit_fires` plus 28/28 MP barrier + cinematic-dispatch regression confirm no behavior drift from the centralization. Architecture is reuse-first and one-mechanism. **Proceed to verify (TEA).** Remaining mismatch #2 (stale context ACs) stays Option A for spec-reconcile/SM — no code action.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (server, branch `feat/67-1-gameboard-crash-server-survive-turn`, pushed):**
- `sidequest/protocol/enums.py` — `MessageType.CLIENT_ERROR`
- `sidequest/protocol/messages.py` — `ClientErrorPayload`, `ClientErrorMessage`, union member
- `sidequest/game/turn.py` — `TurnManager.recheck_barrier(effective_count)`
- `sidequest/server/session_room.py` — `_crash_released` per-interaction set (cleared on drain), `mark_crash_released`, `crash_released_count`, `has_pending_actions`, `effective_barrier_count`
- `sidequest/handlers/player_action.py` — extracted `dispatch_fired_barrier()`; submit path uses `effective_barrier_count()`
- `sidequest/handlers/client_error.py` — new `ClientErrorHandler` + `HANDLER`; emits `mp.player_crash_released`
- `sidequest/server/websocket_session_handler.py` — registered `CLIENT_ERROR` in `_MESSAGE_HANDLERS`
- `tests/protocol/test_enums.py` — MessageType count 51 → 52

**Files Changed (ui, same branch, pushed):**
- `src/types/protocol.ts` — `CLIENT_ERROR`
- `src/components/ErrorBoundary.tsx` — `onCrashReport` prop invoked in `componentDidCatch` (guarded)
- `src/App.tsx` — `handleGameCrash` → `send(CLIENT_ERROR)`, wired to `<ErrorBoundary name="Game">`
- `src/__tests__/error-boundary-crash-signal-67-1.test.tsx` — removed unused import (lint)

**Tests:** Story 67-1 GREEN — server 9/9 (incl. 3-player regression) + protocol 73/73; UI 4/4. MP barrier + cinematic-dispatch regression 28/28 confirms the `dispatch_fired_barrier` extraction and `effective_barrier_count` change are behavior-preserving. Typecheck clean; changed-file lint clean.

**Rework (spec-check round, 2026-05-26):** Fixed the Architect's Major 3+ player stall. Added `SessionRoom.effective_barrier_count()` (PLAYING − crash-released) as the single denominator source; routed `player_action.py` (normal submit) and `client_error.py` (crash path) through it (one-mechanism per `feedback_one_mechanism_per_problem`). Added `test_crash_release_in_three_player_room_then_remaining_submit_fires` (per-player handlers sharing one room — `_handle_player_action` submits as the handler's OWN bound player). GREEN 9/9 + 28 regression. Pushed sidequest-server 3e4d474.

**Scope note:** Full-suite shows 16 pre-existing failures outside this diff's blast radius (compaction/corpus/dogfight/CSS across epics 59/61/63/66) — documented in Delivery Findings; NOT introduced by 67-1.

**Rework (review round, 2026-05-26):** Addressed Granny's two MUST-FIX + one SHOULD-FIX. (1+2) `client_error.py` now binds `crashed_id = sd.player_id` (sender's own socket — ignores client-controlled `msg.player_id`, closing the player-eviction spoof) and rejects an unresolvable player loudly (`logger.warning` + return; closes the `No Silent Fallbacks` `or ""` violation). (3) `session_room.effective_barrier_count()` warns on negative underflow instead of silently freezing. Added `test_crash_signal_attribution_binds_to_sender_not_spoofed_player_id`; updated the 2-player crash tests to route the signal through the crashing player's OWN handler (realistic socket model). GREEN: 67-1 suite 10/10 + 28 regression; ruff clean. Pushed sidequest-server 9074c28. Deferred: finding 3 (unlocked `_submitted` read) — matches established codebase idiom, safe under asyncio.

**Handoff:** Back through spec-check (Leonard) → verify (Igor) → review (Granny) per the rework loop.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8 (changed server + ui code files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | 1 HIGH `_broadcast_cleared_to_party`/`_emit_action_reveal_cleared` dup (pre-existing, out of diff); 1 MED PhaseTimings init dup; 1 LOW lore_context=None reasoning |
| simplify-quality | 5 findings | reason getattr default (MED), aside extraction (LOW), ACTION_REVEAL cast (MED, pre-existing), onCrashReport swallow (MED), `_submitted` `__getattribute__` (MED, established pattern) |
| simplify-efficiency | 1 finding | HIGH `crash_released_count()` dead code |

**Applied (1 high-confidence, in-diff):**
- Removed dead `SessionRoom.crash_released_count()` — both call sites use `effective_barrier_count()`; zero callers. Committed sidequest-server e80da15. Re-verified: 37/37 (67-1 + MP barrier + cinematic-dispatch), ruff clean.

**Flagged for Review (medium, not auto-applied):**
- PhaseTimings init pattern duplicated across `client_error.py` and `player_action.py` (2 lines) — marginal extraction, left for Reviewer judgment.
- `ErrorBoundary.onCrashReport` failure is console.error-only and `handleGameCrash` send() is unwrapped — boundary already try/catch-guards the reporter so a failed send can't break recovery; low risk, flagged.
- `client_error.py` `getattr(payload, "reason", ...)` redundant given the pydantic default — harmless belt-and-suspenders.

**Dismissed (out of scope — pre-existing code / established patterns, not this diff):**
- `_broadcast_cleared_to_party` vs `_emit_action_reveal_cleared` duplication (pre-existing; refactoring shared broadcast code is scope creep).
- `as unknown as GameMessage` cast at App.tsx:1270 (pre-existing ACTION_REVEAL path).
- `object.__getattribute__(tm, "_submitted")` — the established codebase pattern for the intentionally-non-pydantic runtime `_submitted` set (turn.py:75/94/120); matching surrounding code is correct.

**Overall:** simplify: applied 1 fix (dead code removed).

**Verify (round 2, 2026-05-26, post-review-rework):** Delta since round-1 verify is the security hardening only — `client_error.py` (`crashed_id = sd.player_id` + unresolvable-player guard), `session_room.py` (underflow warn), and test updates (+1 spoof-guard test, 2-player crash tests routed through the crashing player's own handler). Self-assessed the delta across the three simplify lenses (Opus, ~30 lines): no new duplication (reuse), clean naming + clear guard comments (quality), the underflow check is a trivial `max(0, raw)` + warn — no over-engineering (efficiency). No fixes to apply. Re-confirmed GREEN: 67-1 suite 10/10 + 28 MP regression; ruff clean. A full 3-agent re-fan-out on a small, already-adversarially-reviewed security delta was judged low-value (context discipline) — the round-1 fan-out covered the substantive surface.

**Quality Checks:** Targeted suites GREEN (37/37); ruff clean; typecheck clean (Dev phase). Pre-existing baseline reds (16, documented in Delivery Findings) are outside this diff's blast radius.

**Handoff:** To Reviewer (Granny) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (114/114 tests, ruff/tsc clean, 0 smells) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 4 | confirmed 2 (MUST), confirmed 1 (SHOULD), deferred 1 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled returned; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 3 confirmed (2 MUST-FIX, 1 SHOULD-FIX), 0 dismissed, 1 deferred

## Reviewer Assessment

**Verdict:** REJECTED — hand back to Dev. Two MUST-FIX findings, both on `sidequest-server/sidequest/handlers/client_error.py:101`, one of which is a clean `No Silent Fallbacks` project-rule match (cannot be dismissed per reviewer rules).

**Preflight:** GREEN — 114/114 (67-1 suite 9, MP barrier 7, cinematic 21, protocol 73, UI 4); ruff/tsc clean; 0 smells; wiring test present. No blockers from mechanical checks.

### Confirmed — MUST-FIX (block merge)

1. **[SEC] CLIENT_ERROR player_id spoofing — Agency / barrier integrity** (`client_error.py:101`, security finding 1, Medium). `crashed_id = (msg.player_id or sd.player_id or "")` trusts the client-controlled wire field `msg.player_id`. Player A can send `CLIENT_ERROR{player_id: B}` to crash-release B from the barrier without B crashing — the system drops B's turn without B's consent (SOUL.md Agency; ADR-104/105 Agency). The honest UI already sends `player_id=""`, so binding to the sender's own socket is strictly more correct with zero downside.
2. **[SEC] Silent empty-string fallback — `No Silent Fallbacks` (CLAUDE.md, hard rule)** (`client_error.py:101`, security finding 2, High). The `or ""` tail lets the handler proceed with `crashed_id=""`, marking an empty-string participant crash-released and silently corrupting `effective_barrier_count`; OTEL logs `player_id=""` with no alarm. Clean project-rule match — not dismissible.

**Combined fix (one locus):**
```python
crashed_id = sd.player_id or ""          # ignore client-controlled msg.player_id
if not crashed_id:
    logger.warning("session.client_error_no_player_id slug=%s", room.slug)
    return []
```
Add a regression test: a CLIENT_ERROR whose `msg.player_id` names a *different* player must NOT release that other player (attribution binds to the sender's session).

### Confirmed — SHOULD-FIX

3. **[SEC] `effective_barrier_count()` underflow → silent turn-freeze** (`session_room.py:511`, security finding 4, Medium). If crash-released entries ever meet/exceed PLAYING, the effective count hits 0/negative and `recheck_barrier`'s `<= 0` guard permanently no-ops the interaction with no operator signal. Largely mitigated once finding 1 binds release to the sender (a socket can only release itself), but add a defensive floor + warn so an all-crashed table is observable rather than silently frozen:
```python
raw = playing - len(self._crash_released)
if raw < 1:
    logger.warning("session.effective_barrier_underflow slug=%s playing=%d released=%d", self.slug, playing, len(self._crash_released))
return max(0, raw)   # keep 0 semantics for recheck_barrier; just surface the anomaly
```

### Deferred

4. **[SEC] Unlocked `_submitted` read** (`client_error.py:75`, security finding 3, Low). `object.__getattribute__(tm, "_submitted")` outside a lock — but this is the established codebase idiom for the intentionally-non-pydantic runtime set (`turn.py:75/94/120`, `player_action.py:506`), safe under the single-threaded asyncio model. Matches surrounding code; not a regression introduced here. Deferred — revisit only if TurnManager work ever moves to a thread-pool context.

### Confirmed clean
Perception firewall / Agency on the dispatch path: VERIFIED no leak — `dispatch_fired_barrier` drains only `_pending_actions` (the crashed player never submitted), and the already-submitted guard prevents acting on a submitter. UI sender confirmed to send `player_id=""`.

**Decision:** Hand back to Dev (Ponder) for the two MUST-FIX items (+ SHOULD-FIX floor). Small, localized to `client_error.py` + `session_room.py` + one new test.

## Reviewer Assessment (round 2 — re-review of security fixes)

### Subagent Results (round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (115/115 tests, ruff/tsc clean, 0 smells) | confirmed 0 |
| 2-6,8-9 | (edge/silent/test/comment/type/simplifier/rule) | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 0 new; 4 prior dispositioned | 3 RESOLVED, 1 deferred-acceptable |

**All received:** Yes (2 enabled returned; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 new; all round-1 findings resolved/accepted.

**Verdict:** APPROVED.

**[SEC] prior-finding disposition (re-verified by reviewer-security):**
- **[SEC] #1 player_id spoofing → RESOLVED.** `client_error.py:63` `crashed_id = sd.player_id or ""` reads identity only from the server-side session binding; a spoofed `CLIENT_ERROR{player_id: victim}` can only release the sender's own seat. ADR-104/105 Agency satisfied. Regression test `test_crash_signal_attribution_binds_to_sender_not_spoofed_player_id` passes.
- **[SEC] #2 silent empty-string fallback → RESOLVED.** `client_error.py:63-69` guards `if not crashed_id: logger.warning(...); return []` — no phantom participant; loud per No Silent Fallbacks.
- **[SEC] #3 unlocked `_submitted` read → DEFERRED (acceptable).** Matches established asyncio single-event-loop idiom; no new concurrent-mutation surface introduced.
- **[SEC] #4 effective_barrier_count underflow → RESOLVED.** `session_room.py` warns on negative underflow and returns `max(0, raw)`; `recheck_barrier`'s `<= 0` guard then conservatively declines to fire on a fully-crashed cohort.

**Preflight:** GREEN — 115/115 (67-1 suite 10, MP barrier, cinematic, protocol, UI 4); ruff/tsc clean; 0 smells. The lone eslint warning (`App.tsx:1752 displayName`) is pre-existing, not in this diff.

**Decision:** Approve → spec-reconcile (Architect) → finish (SM). The two MUST-FIX items are closed; one Low finding deferred with rationale.

## Delivery Findings

Agents record upstream observations discovered during their phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (non-blocking): The story body has no authored ACs; the five SM-derived ACs in `context-story-67-1.md` point at the wrong mechanism ("persist before render" + "reconnect replays"). Code investigation proved the real orphan is the *submit-and-wait barrier hanging forever* on a crashed-but-socket-open player — persistence and reconnect-replay already work. Affects `sprint/context/context-story-67-1.md` (ACs should be updated to the crash-signal mechanism Keith confirmed 2026-05-26). *Found by TEA during test design.*
- **Gap** (blocking for GREEN): The fix requires NEW surfaces — `MessageType.CLIENT_ERROR`, `ClientErrorMessage`/`ClientErrorPayload`, a `handlers/client_error.py` handler registered in `_MESSAGE_HANDLERS`, a crash-release path mirroring abandonment, and the `mp.player_crash_released` OTEL span. *Found by TEA during test design.*
- **Gap** (blocking for GREEN): UI wiring — `ErrorBoundary` needs an `onCrashReport` prop invoked in `componentDidCatch`, and `App.tsx` must wire it to `send()` a `CLIENT_ERROR`. App→socket wiring is not unit-testable in isolation — Reviewer should verify by inspection. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The App→socket wire (`handleGameCrash` → `send({type: CLIENT_ERROR})`, App.tsx ~1165 + ~2019) is verified by inspection + typecheck only — no automated test drives a real GameBoard crash through App. Reviewer (Granny) should confirm by inspection. *Found by Dev during implementation.*
- **Gap** (non-blocking): Full-suite regression shows 16 failures OUTSIDE this story's blast radius, pre-existing on the baseline (no import/call edge from the 67-1 diff): 9 in `tests/agents/test_61_12_output_format_compaction.py`, 4 corpus-audit (missing `genre_packs/*/corpus/*.txt`), 1 `test_three_turn_dogfight_resolves_through_production_path`, 2 UI `chrome-archetype-css.test.ts`. NOT introduced by 67-1. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Pre-existing eslint warning at `sidequest-ui/src/App.tsx` reconnect-handshake `useEffect` — missing `displayName` dependency. Outside 67-1's changed lines; left untouched. *Found by Dev during implementation.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Crash-release dispatch builds TurnContext with lore_context=None**
  - Spec source: context-story-67-1.md (Technical Guardrails) + handlers/player_action.py normal path
  - Spec text: the PLAYER_ACTION path calls `_retrieve_lore_for_turn(sd, action)` and passes the result into `_build_turn_context`.
  - Implementation: the CLIENT_ERROR crash-release path passes `lore_context=None`.
  - Rationale: a crash-release has no single submitting action to retrieve lore for — the dispatched prose is the *combined* pending buffer, assembled inside `dispatch_fired_barrier` at drain time (after context is built). The narrator still receives every submitter's action via `combined_action`.
  - Severity: minor
  - Forward impact: none — lore enrichment on a crash-released turn is slightly thinner; no sibling story depends on it.

### TEA (test design)
- **Tests target the crash-signal mechanism, not the literal SM-derived ACs**
  - Spec source: context-story-67-1.md, AC-1/2/3
  - Spec text: "The server's turn state is applied and persisted server-side before narration is rendered client-side; on reconnect the server replays the persisted turn state."
  - Implementation: RED tests assert a `CLIENT_ERROR` crash-signal → barrier-release → dispatch path. Persistence/reconnect-replay were verified already-working; they are not the orphan mechanism.
  - Rationale: Code investigation proved the orphan is the barrier hanging on a crashed-but-socket-open player. Keith confirmed the crash-signal approach 2026-05-26.
  - Severity: major
  - Forward impact: `context-story-67-1.md` ACs should be rewritten to the crash-signal mechanism (flagged as a Conflict finding).

### Architect (reconcile)
Reviewed the TEA (test design) and Dev (implementation) deviation entries above: both are accurate — spec sources exist, quoted spec text is faithful, and the implementation descriptions match the merged code. No corrections needed. AC accountability: no ACs were formally deferred/descoped (the story carried no authored ACs; the SM-derived set was superseded, not deferred), so the deferral cross-check is a no-op.

The headline deviation the boss should note (consolidated, self-contained):
- **Delivered mechanism supersedes the SM-derived acceptance criteria**
  - Spec source: `sprint/context/context-story-67-1.md`, "AC Context" (SM-derived AC-1/2/3)
  - Spec text: "When a GameBoard subtree throws an error during render, the error boundary prevents the crash from propagating to the WebSocket layer; the server's turn state is applied and persisted server-side before narration is rendered client-side; on client reconnect the server replays the persisted turn state."
  - Implementation: shipped a `CLIENT_ERROR` crash-signal that releases the crashed player from the submit-and-wait barrier denominator (`SessionRoom.effective_barrier_count`), dispatching with the remaining submitters; attribution is bound to the sender's own socket. Persistence + reconnect-replay were confirmed already-working and are NOT the orphan mechanism.
  - Rationale: code investigation (TEA RED phase) proved the orphan is the barrier hanging forever on a crashed-but-socket-open player — a render crash never closes the socket, so the server keeps awaiting the crashed player. Keith confirmed the crash-signal approach via AskUserQuestion on 2026-05-26.
  - Severity: major
  - Forward impact: SM should update `context-story-67-1.md`'s ACs (and, if desired, the epic-67 story line) to describe the crash-signal mechanism so the archived audit trail and any future sibling stories (67-2/3/4) reference the real contract. No code impact.
- No additional (un-logged) deviations found.