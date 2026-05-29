---
story_id: "67-7"
jira_key: ""
epic: "67"
workflow: "tdd"
---
# Story 67-7: Duplicate-socket reconnect loop strands solo session in AwaitingConnect — dice/action frames hard-rejected mid-confrontation

## Story Details
- **ID:** 67-7
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** server,ui

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-29T12:04:02Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-29T00:00:00Z | 2026-05-29T00:00:00Z | setup complete |
| red | 2026-05-29T00:00:00Z | 2026-05-29T11:47:26Z | 11h 47m |
| green | 2026-05-29T11:47:26Z | 2026-05-29T11:51:50Z | 4m 24s |
| spec-check | 2026-05-29T11:51:50Z | 2026-05-29T11:54:14Z | 2m 24s |
| verify | 2026-05-29T11:54:14Z | 2026-05-29T11:57:36Z | 3m 22s |
| review | 2026-05-29T11:57:36Z | 2026-05-29T12:02:35Z | 4m 59s |
| spec-reconcile | 2026-05-29T12:02:35Z | 2026-05-29T12:04:02Z | 1m 27s |
| finish | 2026-05-29T12:04:02Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### TEA (test design)
- **Gap** (blocking): the story is structured as diagnose-then-fix — AC1 (root
  cause) explicitly needs a live repro and AC4 (eliminate-loop vs
  buffer-until-Playing) is an unmade decision, so the AC2/AC3/AC6 reconnect-loop
  reproduction & regression tests are not faithfully authorable in RED.
  Affects `sidequest-ui/src/App.tsx` (slug-connect effect + ErrorBoundary remount
  path) and `sidequest-ui/src/hooks/useWebSocket.ts` (socket lifecycle) — Dev
  must pin the remount/bind trigger via live repro, record the AC4 angle, then
  add the reconnect-path regression coverage. *Found by TEA during test design.*
- **Improvement** (non-blocking): the unbound reject paths
  (`handlers/dice_throw.py:51-65`, `handlers/player_action.py`,
  `handlers/orbital_intent.py:37-49`) currently trace only via `logger.info`,
  which the GM panel never sees — they violate the OTEL Observability Principle
  independent of this bug. AC5's watcher event closes that gap for all three.
  *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **RED coverage scoped to AC5 only; AC2/AC3/AC6 reproduction deferred**
  - Spec source: context-story-67-7.md, AC-1 / AC-2 / AC-3 / AC-6
  - Spec text: "Root cause identified: the duplicate-socket / repeated
    ws.connection_accepted cycle is explained … *This likely requires a live
    repro of the dogfight churn.*" and "Regression coverage for the
    reconnect/bind path."
  - Implementation: RED phase delivers failing tests for AC5 only
    (`tests/server/test_unbound_rejection_telemetry_67_7.py`). No reproduction
    test for the duplicate-socket / remount loop (AC2/AC3) and no reconnect-path
    regression test (AC6) was authored.
  - Rationale: the remount/bind trigger is NOT pinned — the context itself marks
    root cause as needing a live repro (AC1) and the eliminate-loop vs
    buffer-until-Playing angle as undecided (AC4). A reproduction test written
    now would either pass vacuously against current code (the StrictMode
    ghost-socket fix is already in `useWebSocket.ts`) or test a fabricated
    trigger I'd be guessing at — both violate "No vacuous tests" / "No stubbing".
    AC5 is the one contract determinable without the diagnosis, and it is
    mechanism-agnostic (holds for either AC4 angle).
  - Severity: major
  - Forward impact: Dev must pin the root cause (live repro) and record the AC4
    decision, then author the AC2/AC3/AC6 reconnect-path regression coverage as
    part of GREEN; TEA verifies it in the verify phase. Flagged as a blocking
    delivery finding.

### Dev (implementation)
- **GREEN delivers AC5 telemetry only; AC1–AC4/AC6 root-cause + reproduction deferred**
  - Spec source: context-story-67-7.md, AC-1 / AC-2 / AC-3 / AC-4 / AC-6
  - Spec text: "Root cause identified … *This likely requires a live repro of the
    dogfight churn.*"; "No spurious second socket"; "First-attempt roll";
    "Decision recorded: eliminate-the-loop (preferred) and/or
    buffer-until-Playing"; "Regression coverage for the reconnect/bind path."
  - Implementation: implemented AC5 only — a watcher event on the three
    session-unbound reject paths (`_emit_unbound_rejection_event` in
    `session_helpers.py`, wired into `dice_throw.py`, `player_action.py`,
    `orbital_intent.py`). The duplicate-socket root cause was NOT diagnosed or
    fixed, and no socket-lifecycle change was made.
  - Rationale: pinning the remount/bind trigger requires a live multi-socket
    confrontation repro (per TEA's blocking finding and AC1's own text), which is
    not reliably reproducible from this automated implementation context. Per
    "Never say the right fix is X and then do Y" and "No Silent Fallbacks", I did
    not fabricate a root-cause fix or pick the AC4 angle (eliminate-loop vs
    buffer-until-Playing) without the diagnosis to justify it. The
    buffer-until-Playing angle is explicitly a cross-handler decision in #G3
    teardown territory and must not be done as a one-off.
  - Severity: major
  - Forward impact: AC1/AC2/AC3/AC4/AC6 remain open and should be carried into a
    diagnosis-led follow-up story (live repro in oq-2 → identify UI remount loop
    vs server bind race → record AC4 angle → reconnect-path regression coverage).
    The AC5 telemetry shipped here is the instrument that makes that repro
    legible in the GM panel.

## TEA Assessment

**Tests Required:** Yes (partial — AC5 only; see Design Deviations)
**Reason:** AC5 is the one mechanism-agnostic contract testable before the AC1
root-cause diagnosis. AC2/AC3/AC6 reproduction is gated on a live repro (see
blocking Delivery Finding).

**Test Files:**
- `sidequest-server/tests/server/test_unbound_rejection_telemetry_67_7.py` —
  unbound rejection of confrontation action frames must emit a panel-visible
  watcher event carrying the `session_unbound` classification (AC5).

**Tests Written:** 4 tests (3 RED + 1 specificity guard) covering AC5.
**Status:** RED (3 failing — no watcher event on the reject paths today; ready for Dev)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| OTEL Observability Principle (subsystem decision must emit a watcher event) | `test_dice_throw_unbound_emits_watcher_event`, `test_player_action_unbound_emits_watcher_event`, `test_orbital_intent_unbound_emits_watcher_event` | failing |
| No Silent Fallbacks (genuine unbound stays loud + classified, not swallowed) | all three + `test_creating_state_rejection_not_tagged_session_unbound` | 3 failing / 1 guard |
| No Source-Text Wiring Tests (behavior/OTEL assertion, not grep) | telemetry captured via `publish_event` spy, not source text | passing approach |
| Discriminator specificity (signal stays trustworthy) | `test_creating_state_rejection_not_tagged_session_unbound` | passing (guard) |

**Rules checked:** OTEL principle + No Silent Fallbacks + No Source-Text Wiring
(the load-bearing server rules for this surface) have test coverage.
**Self-check:** 0 vacuous tests. The lone passing test is an intentional
specificity guard (rejection class must NOT borrow the `session_unbound` tag),
which constrains the Dev's emit to the AwaitingConnect path — not a vacuous pass.

### AC coverage map

| AC | Covered in RED? | Notes |
|----|-----------------|-------|
| AC1 root cause identified | No | Process/doc AC — needs live repro (Dev/Architect). |
| AC2 no spurious second socket | No | Reproduction gated on AC1 trigger; would be vacuous-green today. |
| AC3 first-attempt roll | No | Engine resolves once Playing (works today); regression gated on AC1. |
| AC4 decision recorded | No | Design decision (Dev) — not a code test. |
| AC5 telemetry distinguishes unbound vs churn | **Yes (RED)** | Genuine-unbound half pinned; churn-detection half is mechanism-dependent. |
| AC6 regression coverage | Partial | AC5 telemetry is regression coverage for the reject path; reconnect/bind repro deferred. |

**Handoff:** To Dev (Major Charles Emerson Winchester III) for implementation —
pin the root cause via live repro, record the AC4 angle, make the AC5 watcher
events fire on all three reject paths, and add the AC2/AC3/AC6 reconnect-path
regression coverage that the diagnosis unblocks.
---
## Delivery Findings — Dev

### Dev (implementation)
- **Gap** (blocking): the duplicate-socket / remount-loop root cause (AC1–AC4, AC6)
  is undiagnosed and unfixed — only AC5 telemetry shipped. Affects
  `sidequest-ui/src/App.tsx` (slug-connect effect resets `slugConnectFired` on
  remount → new socket + new SESSION_EVENT) and `sidequest-ui/src/hooks/useWebSocket.ts`
  (socket lifecycle); needs a live confrontation repro to confirm UI remount loop
  vs server bind race before any socket-lifecycle change. *Found by Dev during implementation.*
- **Improvement** (non-blocking): the new `_emit_unbound_rejection_event` watcher
  event (`state_transition` / component=`session` / `recovery=session_unbound`)
  is the diagnostic instrument for that future repro — the GM panel can now count
  genuine unbound rejections per beat and tell them apart from transport churn.
  Affects `sidequest-server/sidequest/server/session_helpers.py`. *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes (for AC5 — the tested scope; AC1–AC4/AC6 deferred, see deviation + blocking finding)
**Files Changed:**
- `sidequest-server/sidequest/server/session_helpers.py` — new `_emit_unbound_rejection_event` helper (watcher event with `session_unbound` discriminator).
- `sidequest-server/sidequest/handlers/dice_throw.py` — emit on the non-Playing reject path.
- `sidequest-server/sidequest/handlers/player_action.py` — emit on the `session_unbound` branch only (not Creating/data-missing).
- `sidequest-server/sidequest/handlers/orbital_intent.py` — emit on the room-unbound reject path.

**Tests:** 19/19 passing (GREEN) across the new telemetry suite + existing
`test_session_unbound_rejection_code.py`, `test_dice_throw_wiring.py`,
`test_orbital_intent_handler.py` (no regressions). The 3 AC5 RED tests are now
GREEN; the specificity guard stays GREEN.
**Branch:** `feat/67-7-duplicate-socket-reconnect-loop` (pushed to origin, server repo)

**Scope honesty:** This story is structured diagnose-then-fix. AC5 (the
determinable, mechanism-agnostic contract) is delivered and tested. AC1/AC2/AC3/AC4/AC6
(root cause, no-spurious-socket, first-attempt-roll, angle decision, reconnect
regression) require a live repro and are deferred per TEA's blocking finding and
the Dev deviation above — no root-cause fix was fabricated.

**Handoff:** To Reviewer (Colonel Sherman Potter) — review the AC5 telemetry
implementation; the open root-cause work is flagged for a diagnosis-led follow-up.
---
## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (by design — diagnose-then-fix story; 1 of 6 ACs implemented)
**Mismatches Found:** 5 (AC1, AC2, AC3, AC4, AC6) — AC5 fully aligned

**Code verification (AC5):** Diff reviewed against `origin/develop`. The guard
was NOT weakened — every `_emit_unbound_rejection_event` call is purely additive,
placed before the existing reject `return`; the `_State`/`room is None` conditions
are untouched. player_action's emit is correctly co-located on the
`code="session_unbound"` branch only, never the Creating/data-missing class. No
scope creep. Implementation matches the Dev Assessment and honors the context
constraint "the rejection itself is CORRECT — do not weaken the guard blindly."

**Mismatches:**

- **AC5 telemetry distinguishes unbound vs reconnect churn** (Aligned — Behavioral, n/a)
  - Spec: "a span/log distinguishes genuine-unbound rejection from reconnect churn."
  - Code: `state_transition` watcher event (component=`session`,
    `recovery=session_unbound`) on all three reject paths; tested GREEN.
  - Recommendation: none — fully met. The genuine-unbound half is shipped; the
    churn-detection half is downstream (panel correlates absence of this tag).

- **AC1 root cause identified** (Missing in code — Architectural, Major)
  - Spec: "the duplicate-socket / repeated ws.connection_accepted cycle is
    explained … *This likely requires a live repro of the dogfight churn.*"
  - Code: not addressed — no diagnosis performed.
  - Recommendation: **D (Defer)** — the story's own text gates this on a live
    repro that cannot be staged from an automated implementation context. Belongs
    to a diagnosis-led follow-up. Handing back to Dev is futile (same constraint).

- **AC2 no spurious second socket** (Missing in code — Behavioral, Major)
  - Spec: "a solo confrontation session no longer opens a second socket /
    re-runs the connect handshake."
  - Code: no socket-lifecycle change (`App.tsx` / `useWebSocket.ts` untouched).
  - Recommendation: **D (Defer)** — gated on the AC1 trigger; a fix now would be
    a guess. Follow-up after diagnosis.

- **AC3 first-attempt roll** (Missing in code — Behavioral, Major)
  - Spec: "committing a dogfight beat lands its DICE_THROW on the first attempt."
  - Code: not addressed — the engine already resolves once Playing (context
    confirms); the churn that strands AwaitingConnect is unfixed.
  - Recommendation: **D (Defer)** — downstream of AC1/AC2.

- **AC4 decision recorded** (Missing in code → partially resolved here — Architectural, Major)
  - Spec: "Decision recorded: eliminate-the-loop (preferred) and/or
    buffer-until-Playing; if the latter, applied across affected handlers uniformly."
  - Code: Dev deferred the decision (correctly — would not pick an angle without
    the diagnosis to justify it).
  - Recommendation: **A (record decision now)** — ARCHITECTURAL DECISION: pursue
    **angle 1 (eliminate the loop)**, NOT buffer-until-Playing. Rationale: (1) the
    guard rejection is correct per context — the defect is the churn that keeps
    the session unbound, so the fix must remove the churn, not paper over it;
    (2) buffer-until-Playing is #G3 heavy-hammer WS-teardown territory, a
    cross-handler behavior change that risks "No Silent Fallbacks" (a buffer masks
    the real bind failure); (3) the AC5 telemetry shipped here is the instrument
    to pin the remount/bind trigger. The follow-up should eliminate the
    duplicate-socket/remount cycle; buffering is explicitly rejected as the primary
    remedy. *Implementation* of angle 1 remains deferred (needs the live repro).

- **AC6 regression coverage for reconnect/bind path** (Missing in code — Behavioral, Major)
  - Spec: "Regression coverage for the reconnect/bind path."
  - Code: AC5 telemetry is regression coverage for the *reject* path; the
    reconnect/bind reproduction is not covered.
  - Recommendation: **D (Defer)** — authored against the AC1 trigger in the follow-up.

**Decision:** Proceed to review — on the AC5 telemetry slice, which is clean,
tested, and independently valuable (it is the diagnostic instrument for the
deferred work). The AC1/AC2/AC3/AC6 root-cause work is a legitimate, well-documented
deferral (TEA + Dev blocking findings; the story's own AC1 text); AC4's angle is
decided here (eliminate-the-loop). **Recommendation to SM/PM:** carry AC1/AC2/AC3/AC6
into a diagnosis-led follow-up story (live repro in oq-2 → confirm UI remount loop
vs server bind race → eliminate the loop per AC4 → reconnect-path regression),
rather than marking 67-7's behavioral bug-fix complete. Not handing back to Dev —
no in-context fix is possible and the AC5 code needs no changes.
---
## TEA Assessment (verify phase)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (4 production + 1 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | helper correctly extracted; 3 identical call sites are the same mechanical op — no further extraction warranted |
| simplify-quality | 2 findings (dismissed) | claimed `_emit_unbound_rejection_event` must be re-exported in `session_handler.py.__all__` per the module's back-compat docstring |
| simplify-efficiency | clean | single-responsibility helper, no over-parameterization; extraction saves ~12 lines × 3 sites |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0
**Noted:** 1 low-confidence (naming verbosity) — dismissed
**Reverted:** 0

**Triage detail (simplify-quality, dismissed as false positive):** The finding
assumed the `session_handler.py` re-export covers *all* helpers. Verified it does
not — re-export is **selective** (15 of 21 helpers), scoped to *back-compat*
symbols that previously lived in `session_handler.py`. `_emit_unbound_rejection_event`
is brand new, imported directly by the three handlers from `session_helpers`, and
follows the established pattern of other new watcher-emitting helpers that are
NOT re-exported (`_emit_auto_mint_skip`, `_publish_image_unavailable`). Adding it
to the back-compat re-export would be incorrect and inconsistent. No change made.

**Overall:** simplify: clean (no changes applied; all findings clean or dismissed-on-verification)

**Quality Checks:** ruff clean (5 files); 19/19 tests passing
(`test_unbound_rejection_telemetry_67_7.py` + existing
`test_session_unbound_rejection_code.py`, `test_dice_throw_wiring.py`,
`test_orbital_intent_handler.py`) — no regressions.

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review of the AC5
telemetry slice. Note the standing scope context: AC1/AC2/AC3/AC6 are a documented
deferral (diagnosis-led follow-up, live repro required), AC4's angle is decided in
the Architect spec-check assessment (eliminate-the-loop).

## Delivery Findings — TEA verify

### TEA (test verification)
- No upstream findings during test verification. The AC5 implementation is clean,
  lint-passing, and regression-free; the deferred AC1/AC2/AC3/AC6 scope is already
  captured as blocking findings by TEA (test design) and Dev (implementation) above.
---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; tests 4/4 GREEN; ruff clean | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings (assessed by Reviewer — see obs #2/#4) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (assessed by Reviewer — see obs #5) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings (assessed by Reviewer — comments accurate) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (assessed by Reviewer — helper fully annotated) |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (assessed by Reviewer + TEA verify — see obs #8) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (Reviewer ran lang-review manually — see Rule Compliance) |

**All received:** Yes (2 enabled subagents returned: preflight GREEN, security clean; 7 disabled and assessed by Reviewer)
**Total findings:** 0 confirmed blocking, 1 low (severity-label note, no change), 0 deferred

## Reviewer Observations

1. `[VERIFIED]` **Guard not weakened** — the emit is additive-only, inserted before the unconditional reject `return` in all three handlers (`dice_throw.py:64`, `orbital_intent.py:50`, `player_action.py:265`). The `_State`/`room is None` conditions and the `code="session_unbound"` returns are byte-for-byte unchanged from `origin/develop`. Honors the story constraint "the rejection itself is CORRECT — do not weaken the guard blindly."
2. `[VERIFIED]` **Telemetry cannot crash the reject path** — `publish_event` is exception-safe for this payload: `WatcherHub.publish()` is fire-and-forget (`asyncio.run_coroutine_threadsafe`, never awaits, `_broadcast` self-guards serialization + per-subscriber send); `_maybe_persist_encounter_row` returns early because `fields["field"]=="session_binding"` ≠ `"encounter"` and is fully wrapped regardless; `_persist_turn_telemetry` is fully `try/except`-wrapped ("Never raises", `watcher_hub.py`), and its one pre-`try` `json.dumps` operates on all-string fields. A telemetry failure therefore cannot convert a clean rejection into a 500.
3. `[SEC]` **No sensitive / user-controlled data in telemetry** (confirmed by reviewer-security + own read) — `message_type` is a string literal at each call site; `state_name` is `session._state.name`, a server-side 3-value enum name. No PII, tokens, action text, or injection surface in the five published fields.
4. `[VERIFIED]` **No Silent Fallback** — the genuine rejection stays loud: the `ERROR{code=session_unbound}` frame and the pre-existing `logger.info` both remain; the watcher event is purely additive. Dropping the watcher event when no dashboard is subscribed is correct lossy-telemetry design (`watcher_hub.publish` docstring), not a masked rejection.
5. `[TEST]` **Test quality sound** (test_analyzer disabled — assessed by Reviewer) — assertions are non-vacuous (error code, watcher-call presence, `session_unbound` discriminator, frame type, state) and a negative test proves Creating-state does NOT borrow the tag. Mock target is correct: patches `sidequest.telemetry.watcher_hub.publish_event`; the helper's call-time `from ... import publish_event` resolves the patched attribute (proven by GREEN). `_flatten_values` substring matching is loose but intentionally decoupled from field names — acceptable.
6. `[LOW]` **Severity-label nuance** — the watcher event uses `severity="warning"` while the co-located `logger.info` is INFO. Mild inconsistency, but "warning" is defensible (story wants the rejection "loud") and lang-review #4 permits client-error→warning. No change required.
7. `[VERIFIED]` **Per-handler unbound semantics preserved** — `dice_throw` emits for any non-Playing state (incl. Creating) while `player_action` excludes Creating; this faithfully mirrors each handler's PRE-EXISTING `session_unbound` branch (dice_throw already returned that code for any non-Playing; player_action already excluded Creating). The asymmetry is pre-existing and out of scope.
8. `[SIMPLE]` **Helper extraction correct** (simplifier disabled — assessed by Reviewer + TEA verify) — `_emit_unbound_rejection_event` is appropriately DRY across 3 call sites and correctly NOT added to `session_handler.__all__` (re-export is selective/back-compat-only; new watcher helpers like `_emit_auto_mint_skip` follow the direct-import pattern). TEA dismissed the false-positive re-export finding in verify.

### Rule Compliance (lang-review/python.md — applied exhaustively to the diff)

| # | Rule | Verdict |
|---|------|---------|
| 1 | Silent exception swallowing | Pass — no new try/except in production code; persist-side swallows are pre-existing and loud-logged |
| 2 | Mutable default arguments | Pass — none introduced |
| 3 | Type annotations at boundaries | Pass — `_emit_unbound_rejection_event(message_type: str, state_name: str) -> None` fully annotated; 3 call sites pass literals/enum name |
| 4 | Logging coverage & correctness | Pass — existing `logger.info` retained; `%s` lazy-formatting; `severity="warning"` appropriate (obs #6) |
| 5 | Path handling | N/A — no path ops |
| 6 | Test quality | Pass — meaningful assertions, correct mock target, negative case (obs #5) |
| 7 | Resource leaks | N/A — no resources opened |
| 8 | Unsafe deserialization | N/A — no pickle/eval/yaml on input |
| 9 | Async/await pitfalls | Pass — helper is sync, calls only the fire-and-forget `publish_event`; no blocking call in async handler, no missing await |
| 10 | Import hygiene | Pass — call-time import in helper (avoids circular import + enables test patching); no star imports; no `__all__` change needed (private, direct-imported) |
| 11 | Input validation at boundaries | Pass — telemetry args server-derived, not user input; message-boundary validation unchanged |
| 12 | Dependency hygiene | N/A — no dependency changes |
| 13 | Fix-introduced regressions | Pass — additive change; re-scan against #1–#12 clean |

### Devil's Advocate

Let me argue this code is broken. First attack: telemetry in a hot reject path. A malicious or merely unlucky client could spray DICE_THROW frames at an `AwaitingConnect` session — now every one fires `publish_event`. Could that be a DoS amplifier? No: `publish()` is O(subscribers) fire-and-forget, the event is bounded and tiny, and the reject path already logged + returned before — the watcher buffer is the same one every subsystem uses and is self-pruning. The spray DoS, if any, pre-existed the rejection guard itself and is unchanged. Second attack: what if `session._state` is a `MagicMock` (as in tests) or somehow not a real enum in production — `session._state.name` would yield a Mock attribute and `json.dumps` could choke. In production `_state` is always a real `_State` enum (set by the FSM); the Mock case is test-only and `_json_default` would `str()` it anyway. Third attack: ordering — could the emit run when the session is actually fine? The emit sits strictly inside the existing `session_unbound` branch in all three handlers; I traced each branch and the condition is unchanged, so it fires exactly when the pre-existing rejection fired — no false positives that would pollute the GM panel's lie-detector signal. Fourth attack: the confused-user angle — a player mid-confrontation sees nothing different; the ERROR frame and recovery contract (`code=session_unbound` → client re-fires SESSION_EVENT) are untouched, so UX is unchanged. Fifth, and the real one: a confused *operator* could read "67-7 merged" as "the duplicate-socket bug is fixed." It is NOT. This change ships only the AC5 instrument; the remount/bind loop that strands the session (AC1/AC2/AC3/AC6) is undiagnosed and unfixed. That is the genuine risk here — not a code defect, but a story-completion-semantics trap. I am recording it as a blocking delivery finding so the boss/SM do not close epic-67's playability bug on the strength of a telemetry slice. The code that exists is correct; the story it belongs to is not yet done.

### Reviewer (audit)
- **TEA (test design) — RED coverage scoped to AC5 only** → ✓ ACCEPTED by Reviewer: the deferral is sound and matches the story's own AC1 "requires a live repro" framing; fabricating reproduction tests would have been vacuous.
- **Dev (implementation) — GREEN delivers AC5 telemetry only** → ✓ ACCEPTED by Reviewer: correct restraint — no fabricated root-cause fix; "Never say the right fix is X and do Y" honored.
- **Architect (spec-check) — AC4 angle decided (eliminate-the-loop, not buffer)** → ✓ ACCEPTED by Reviewer: architecturally sound; buffer-until-Playing is #G3 teardown territory and risks a silent fallback.
- No undocumented deviations found beyond the scope deferral already captured by all three prior agents.

## Reviewer Assessment

**Verdict:** APPROVED

The delivered AC5 telemetry slice is correct, exception-safe, lint-clean, and well-tested. No Critical or High findings. Data flow traced: a pre-handshake action frame (`DICE_THROW`/`PLAYER_ACTION`/`ORBITAL_INTENT`) → handler's existing `session_unbound` guard → new `_emit_unbound_rejection_event` → `publish_event("state_transition", component="session", recovery="session_unbound")` → GM panel; the rejection `ERROR{code=session_unbound}` return is unchanged and unconditional. Pattern observed: shared private helper in `session_helpers.py:1264` reused at three call sites, mirroring the existing watcher-helper pattern (`_emit_auto_mint_skip`, `_publish_image_unavailable`). Error handling: telemetry is fire-and-forget and fully wrapped — cannot crash the reject path (obs #2). `[SEC]` reviewer-security returned clean: the five published fields carry no PII/tokens/action text and no user-controlled input (`message_type` literal, `state_name` = server-side enum name), so there is no info-leak or injection surface.

**Scope caveat (not a code defect):** this story delivers 1 of 6 ACs. The duplicate-socket root cause (AC1/AC2/AC3/AC6) is a documented, legitimate deferral; AC4's angle is decided. The AC5 code is mergeable on its own merits, but 67-7 must NOT be treated as resolving epic-67's playability bug — see the blocking delivery finding for the required diagnosis-led follow-up.

**Handoff:** To Architect for spec-reconcile, then SM for finish-story.

## Delivery Findings — Reviewer

### Reviewer (code review)
- **Gap** (blocking): story 67-7 ships only AC5 (telemetry); the behavioral duplicate-socket fix (AC1 root cause, AC2 no-spurious-socket, AC3 first-attempt-roll, AC6 reconnect regression) is undiagnosed and deferred. Affects `sidequest-ui/src/App.tsx` + `sidequest-ui/src/hooks/useWebSocket.ts` (needs a live confrontation repro to pin UI remount loop vs server bind race, then eliminate-the-loop per AC4). Epic-67's playability bug must NOT be closed on this PR — a diagnosis-led follow-up story is required. *Found by Reviewer during code review.*
- No code-quality findings: the AC5 implementation is correct, exception-safe, and regression-free. *Found by Reviewer during code review.*
### Architect (reconcile)

**Verification of prior deviation entries (all accurate, all 6 fields present):**
- TEA (test design) and Dev (implementation) entries both cite a real spec source
  (`sprint/context/context-story-67-7.md`, confirmed on disk); their quoted spec
  text matches the context verbatim (AC1 "Root cause identified … *This likely
  requires a live repro*", AC4 "Decision recorded: eliminate-the-loop (preferred)",
  AC6 "Regression coverage for the reconnect/bind path"). The Implementation and
  Forward-impact fields accurately describe the shipped code (AC5 watcher emit on
  three reject paths; no socket-lifecycle change). Reviewer audit stamped all three
  prior entries ACCEPTED. No corrections required.

**Definitive manifest (self-contained for boss audit):**
- **Story 67-7 ships 1 of 6 ACs — AC5 (telemetry) only; AC1/AC2/AC3/AC6 deferred, AC4 decided**
  - Spec source: `sprint/context/context-story-67-7.md`, AC-1 through AC-6
  - Spec text: AC1 "Root cause identified: the duplicate-socket / repeated
    ws.connection_accepted cycle is explained (UI remount vs server bind race)
    with log/OTEL evidence … *This likely requires a live repro of the dogfight
    churn.*"; AC2 "No spurious second socket"; AC3 "First-attempt roll … committing
    a dogfight beat lands its DICE_THROW on the first attempt"; AC4 "Decision
    recorded: eliminate-the-loop (preferred) and/or buffer-until-Playing"; AC5
    "Telemetry: a span/log distinguishes genuine-unbound rejection from reconnect
    churn"; AC6 "Regression coverage for the reconnect/bind path".
  - Implementation: AC5 fully delivered — `_emit_unbound_rejection_event`
    (`sidequest-server/sidequest/server/session_helpers.py`) emits a
    `state_transition` watcher event (component=`session`, `recovery=session_unbound`)
    on the unbound-reject branch of `dice_throw.py`, `player_action.py`,
    `orbital_intent.py`; 4 tests GREEN. AC4 DECIDED here (spec-check): pursue
    angle 1, eliminate-the-loop, NOT buffer-until-Playing. AC1/AC2/AC3/AC6 NOT
    implemented — no diagnosis, no socket-lifecycle change.
  - Rationale: the story is diagnose-then-fix; AC1's own text gates the root cause
    on a live multi-socket confrontation repro that cannot be staged from an
    automated implementation context. Per "No Silent Fallbacks" and "Never say the
    right fix is X and do Y", no root-cause fix was fabricated and no AC4 angle was
    chosen without the diagnosis — except AC4's *recommendation*, which is an
    architectural call (eliminate the churn; buffering is #G3 teardown territory
    and would mask the bind failure). AC5 is the determinable, mechanism-agnostic
    contract and is the diagnostic instrument the deferred work needs.
  - Severity: major
  - Forward impact: epic-67's playability bug (the duplicate-socket loop that
    strands confrontations in AwaitingConnect) is NOT resolved by this story. A
    diagnosis-led follow-up is required: live repro in oq-2 → confirm UI remount
    loop (`sidequest-ui/src/App.tsx` slug-connect/ErrorBoundary remount,
    `useWebSocket.ts`) vs server bind race → eliminate the loop per AC4 →
    reconnect-path regression (AC2/AC3/AC6). SM/PM should open that story before
    closing epic-67's #C5 finding. No sibling story in the current sprint depends
    on the deferred behavior; 59-20 (per-recipient firewall) and #G3 (WS teardown)
    are adjacent but distinct seams.

- No additional undocumented deviations found beyond the AC5-only delivery already
  captured by TEA, Dev, and Reviewer.

**AC deferral cross-reference:** No formal ac-completion accountability table was
emitted for this story; the TEA "AC coverage map" serves that role. Cross-checked
against the Reviewer's findings — the AC1/AC2/AC3/AC6 deferral was not inadvertently
addressed or invalidated during review (Reviewer confirmed no socket-lifecycle code
shipped). Deferral status stands: AC5 DONE, AC4 DECIDED, AC1/AC2/AC3/AC6 DEFERRED.