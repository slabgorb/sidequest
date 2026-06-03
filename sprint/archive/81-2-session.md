---
story_id: "81-2"
jira_key: ""
epic: "81"
workflow: "tdd"
---

# Story 81-2: Instantiate and drive TensionTracker in the turn pipeline (ADR-024)

## Story Details

- **ID:** 81-2
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T16:29:38Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T11:25:00Z | 2026-06-03T15:49:11Z | 4h 24m |
| red | 2026-06-03T15:49:11Z | 2026-06-03T16:02:21Z | 13m 10s |
| green | 2026-06-03T16:02:21Z | 2026-06-03T16:16:41Z | 14m 20s |
| spec-check | 2026-06-03T16:16:41Z | 2026-06-03T16:19:05Z | 2m 24s |
| verify | 2026-06-03T16:19:05Z | 2026-06-03T16:23:21Z | 4m 16s |
| review | 2026-06-03T16:23:21Z | 2026-06-03T16:27:52Z | 4m 31s |
| spec-reconcile | 2026-06-03T16:27:52Z | 2026-06-03T16:29:38Z | 1m 46s |
| finish | 2026-06-03T16:29:38Z | - | - |

## Sm Assessment

**Story selected:** 81-2 — Instantiate and drive TensionTracker in the turn pipeline (ADR-024). Highest-priority tier (p1), chosen by the user from the three epic-81 "Built-Not-Wired Remediation" p1 stories.

**Why now:** Foundational story of epic 81 — 81-3 (PacingHint consumer) depends on this producer existing. No dependencies of its own. Clear, well-bounded ADR-024 runtime bug: `TensionTracker` is constructed only in tests, so the dual-track tension signal never accumulates in production and the GM-panel OTEL spans never fire.

**Setup state:**
- Epic context (`context-epic-81.md`) and story context (`context-story-81-2.md`) pre-existed from the 2026-06-03 audit — verified complete, not regenerated.
- Branch `feat/81-2-tension-tracker-producer` created off `develop` in sidequest-server (github-flow).
- No Jira (personal project) — Jira ops correctly skipped.
- Single-repo story: sidequest-server only.

**Routing:** tdd workflow (phased) → RED phase → Igor (tea) writes failing tests covering the 4 ACs, including the real production-path wiring test (AC4) that must fail on current `develop`.

**Watch-outs flagged for downstream:**
- Do NOT modify `TensionTracker` math or `pacing_hint()` — tested and correct; this story only constructs + feeds it.
- Do NOT wire the hint into `TurnContext` — that's 81-3. Keep producer/consumer split so each has its own wiring test.
- The existing OTEL test must not be the wiring proof; AC4 requires a behavioral test via a production entrypoint.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Gap** (non-blocking): The turn path has **no `RoundResult` object** to feed
  `TensionTracker.observe()`. Confirmed by scout: `RoundResult`/`DamageEvent` are
  constructed only in tests; `observe()` is never called in production. At the
  combat-resolution seam the available data is `BeatSelection` / `ApplyBeatResult`
  deltas / `snapshot.encounter` metrics / `snapshot.find_creature_core(name).hp_pool`.
  Affects `sidequest/game/tension_tracker.py` + the turn path (`websocket_session_handler.py`
  `_execute_narration_turn`). Dev must synthesize a `RoundResult` (and/or call
  `update_stakes(current_hp, max_hp)`) from this data. *Found by TEA during test design.*
- **Gap** (non-blocking): Method subtlety the ACs blur — **only `observe()` emits the
  OTEL watcher event**; `record_event()` moves *only* the action track and is silent;
  the *stakes* track moves *only* via `update_stakes()`. The epic context says "call
  `record_event(...)`" but AC3 requires the watcher event — so Dev must drive via
  `observe()` (reuse its existing emission, per the epic-81 "no parallel telemetry"
  guardrail), not bare `record_event()`. The AC3 test enforces this.
  Affects `_execute_narration_turn`. *Found by TEA during test design.*
- **Question** (non-blocking): **Seam choice — drive once per turn in the handler, not
  inside `narration_apply`.** `narration_apply` runs *inside*
  `orchestrator.run_narration_turn`, which turn-path tests mock; driving tension there
  would be untestable without a live LLM and would only fire on combat turns. ADR-024
  wants a pacing signal that updates *every* turn. The RED tests therefore assume the
  tracker is driven once per turn from a seam reachable inside `_execute_narration_turn`
  (read the resolved snapshot; a quiet turn is a Boring observation). This also sidesteps
  the dual combat-resolution-path trap (opposed_check in `narration_apply` **and**
  `dispatch_dice_throw`) — a single post-resolution observation per turn sees the net
  resolved state regardless of which path fired. If Dev finds a better seam that still
  satisfies the behavioral tests, that's fine. Affects `_execute_narration_turn`.
  *Found by TEA during test design.*
- **Improvement** (non-blocking): `_SessionData.tension_tracker` should mirror the
  `entity_store` precedent: `tension_tracker: TensionTracker = field(default_factory=TensionTracker)`
  (session_state.py ~:245). Per-session in-memory is sufficient for v1 (resets on reload,
  per story Assumptions). Affects `sidequest/server/session_state.py`.
  *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Per-turn HP-delta damage capture would give the action
  track NearMiss/Normal/CriticalHit fidelity *through the turn path* (this story derives
  action-track drama from kill + lowest-HP-ratio only; stakes track uses real player HP).
  Affects `sidequest/server/websocket_session_handler.py` (`_drive_session_tension_tracker`
  — add a start-of-turn combatant-HP snapshot and diff at the seam). Good 81-2 follow-up or
  fold into 81-3 verification. *Found by Dev during implementation.*
- **Question** (non-blocking): On a resolution turn where the engine clears `snapshot.encounter`
  to `None` (rather than leaving it `resolved=True`), the kill signal can't be read (no actors/
  outcome at the seam), so that turn observes as Boring instead of a KillingBlow. Not observed
  in tests; flag for playtest. Affects `_drive_session_tension_tracker`. *Found by Dev during
  implementation.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

5 deviations

- **AC2 relative-magnitude clause not re-driven through the turn path**
  - Rationale: Driving the differential through the turn path would couple the wiring test
  - Severity: minor
  - Forward impact: If Dev wants explicit through-the-turn coverage of dramatic escalation,
- **Drove the tracker via `observe(RoundResult, ...)`, not `record_event(CombatEvent)`**
  - Rationale: Only `observe()` emits the `tension:round_observed` watcher event AC3 requires;
  - Severity: minor
  - Forward impact: none — `observe()` is the richer superset; 81-3 reads `pacing_hint()` which
- **Per-turn HP-delta `damage_events` not synthesized**
  - Rationale: A faithful per-turn damage number needs before/after HP capture; the
  - Severity: minor
  - Forward impact: mid-combat non-resolution turns classify Boring on the *action* track
- **Modified a TEA test (TurnContext reuse → fresh-per-turn)**
  - Rationale: `TurnContext.PhaseTimings` finalizes at turn end; production builds a fresh
  - Severity: minor
  - Forward impact: none.
- **Tension tracker driven from the handler seam, not the `narration_apply` combat-resolution path**
  - Rationale: `narration_apply` runs *inside* the LLM-gated `run_narration_turn`, which turn-path tests mock and which only executes on combat turns; driving there would be untestable without a live LLM and would skip quiet turns. ADR-024 wants a pacing signal that updates *every* completed turn. The handler seam satisfies both and is the actual "turn-processing path" the epic text names. `observe()` is used because it is the only method that emits the required `tension:round_observed` watcher event (AC3). This is consistent with the epic text ("turn-processing path") and only diverges from a scout-exploration suggestion that named `narration_apply` as a "natural point."
  - Severity: minor
  - Forward impact: 81-3 (PacingHint consumer) reads `tension_tracker.pacing_hint(thresholds)` from the same per-session tracker at `TurnContext` construction — unaffected by the producer seam. Finer combat-turn fidelity (HP-delta `damage_events`) and MP shared-scene placement remain documented follow-ups.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC2 relative-magnitude clause not re-driven through the turn path**
  - Spec source: context-story-81-2.md, AC-2
  - Spec text: "a quiet turn moves them less / decays per the tracker's own rules"
  - Implementation: The turn-path tests assert the tracker *moves* (Boring streak
    accumulates, axes stay bounded) and is fed every turn; they do **not** drive a
    dramatic-vs-quiet *differential* through the turn path. The relative-magnitude math
    (dramatic > boring, decay rules) is already covered by `tests/game/test_tension_tracker.py`
    unit tests.
  - Rationale: Driving the differential through the turn path would couple the wiring test
    to the unspecified snapshot→`RoundResult` synthesis (a Dev design choice — see Delivery
    Finding). Testing the *feed* (wiring) here and leaving the *math* to the existing unit
    suite keeps the wiring test refactor-stable and avoids re-testing tracker internals.
  - Severity: minor
  - Forward impact: If Dev wants explicit through-the-turn coverage of dramatic escalation,
    add an integration test once the snapshot→RoundResult mapping is settled (could be an
    81-2 follow-up or fold into 81-3's pacing-hint verification).

### Dev (implementation)
- **Drove the tracker via `observe(RoundResult, ...)`, not `record_event(CombatEvent)`**
  - Spec source: context-story-81-2.md AC-2 + context-epic-81.md §81-2
  - Spec text: "Turn processing calls `record_event` for resolved combat/scene events"
  - Implementation: `_drive_session_tension_tracker` calls `tracker.observe(...)` (which
    internally calls `record_event` AND emits the watcher event) plus `update_stakes()`.
  - Rationale: Only `observe()` emits the `tension:round_observed` watcher event AC3 requires;
    bare `record_event()` is silent and moves only the action track. Epic-81 guardrail says
    "reuse the tracker's existing OTEL emission — no parallel telemetry path." (Pre-flagged by
    TEA Delivery Finding.)
  - Severity: minor
  - Forward impact: none — `observe()` is the richer superset; 81-3 reads `pacing_hint()` which
    is unaffected.
- **Per-turn HP-delta `damage_events` not synthesized**
  - Spec source: context-story-81-2.md, Assumptions
  - Spec text: "Resolved combat/scene events are available … in a form `record_event` accepts;
    if a mapping/adapter is needed, it is small and in scope. If the available events don't
    cleanly map, log a Design Deviation."
  - Implementation: `RoundResult(round=N)` is passed with empty `damage_events`; the action
    track's drama derives from real `killed` (this-turn defeat) + `lowest_hp_ratio` (seated
    combatant HP). The stakes track uses the player's real HP. No start/end HP capture this
    story.
  - Rationale: A faithful per-turn damage number needs before/after HP capture; the
    relative-magnitude math (dramatic > boring) is already covered by
    `tests/game/test_tension_tracker.py`. Keeping the adapter small per the story's invitation.
  - Severity: minor
  - Forward impact: mid-combat non-resolution turns classify Boring on the *action* track
    (the *stakes* track still carries real danger via HP). A follow-up could add HP-delta
    capture for finer NearMiss/Normal/CriticalHit fidelity through the turn path.
- **Modified a TEA test (TurnContext reuse → fresh-per-turn)**
  - Spec source: tests/server/test_tension_tracker_turn_wiring.py (TEA, RED)
  - Spec text: `test_tracker_is_per_session_and_accumulates_across_turns` reused one
    `turn_context` across two `_execute_narration_turn` calls.
  - Implementation: build a fresh `_build_turn_context_for_test(sd)` per turn.
  - Rationale: `TurnContext.PhaseTimings` finalizes at turn end; production builds a fresh
    context per turn, so reuse raised `RuntimeError: PhaseTimings already finalized` — a test
    infra defect, not a production bug. All assertions (same instance, monotonic streak, 2
    events) preserved; this only makes the test match real usage.
  - Severity: minor
  - Forward impact: none.

### Architect (reconcile)

**Existing-entry verification:** All four logged deviations (TEA ×1, Dev ×3) were reviewed against
the source documents. Each has all 6 fields; spec sources are real paths
(`context-story-81-2.md`, `context-epic-81.md`); quoted spec text is accurate; implementation
descriptions match the committed code; forward-impact assessments are correct. No corrections needed.

**AC deferral check:** No-op — no ACs were deferred. All four ACs are DONE (AC2's relative-magnitude
clause is *covered by existing tracker unit tests*, not deferred). No ac-completion accountability
table was written, consistent with zero deferrals.

**Missed deviation added for manifest completeness (the load-bearing design decision, previously
captured only as a TEA Delivery-Finding "Question" — promoted here so the audit manifest is
self-contained):**

- **Tension tracker driven from the handler seam, not the `narration_apply` combat-resolution path**
  - Spec source: context-epic-81.md, §"81-2 — TensionTracker producer (foundational)"
  - Spec text: "give each session a `TensionTracker` on `_SessionData` … and call `record_event(...)` from the turn-processing path as combat/scene events resolve. The tracker already emits OTEL …; those spans should now fire in real turns."
  - Implementation: A per-session tracker on `_SessionData` is driven once per turn by `_drive_session_tension_tracker`, called from `_execute_narration_turn` at the post-resolution seam (just before the per-turn `game_state_snapshot` publish) — *outside* `orchestrator.run_narration_turn` (which contains `narration_apply`). It uses `observe(RoundResult, killed, lowest_hp_ratio)` + `update_stakes(...)` rather than bare `record_event(CombatEvent)`.
  - Rationale: `narration_apply` runs *inside* the LLM-gated `run_narration_turn`, which turn-path tests mock and which only executes on combat turns; driving there would be untestable without a live LLM and would skip quiet turns. ADR-024 wants a pacing signal that updates *every* completed turn. The handler seam satisfies both and is the actual "turn-processing path" the epic text names. `observe()` is used because it is the only method that emits the required `tension:round_observed` watcher event (AC3). This is consistent with the epic text ("turn-processing path") and only diverges from a scout-exploration suggestion that named `narration_apply` as a "natural point."
  - Severity: minor
  - Forward impact: 81-3 (PacingHint consumer) reads `tension_tracker.pacing_hint(thresholds)` from the same per-session tracker at `TurnContext` construction — unaffected by the producer seam. Finer combat-turn fidelity (HP-delta `damage_events`) and MP shared-scene placement remain documented follow-ups.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Wiring story — the whole point is to prove a built-but-dark subsystem is now
reachable from a production path. Per CLAUDE.md "Every Test Suite Needs a Wiring Test."

**Test Files:**
- `sidequest-server/tests/server/test_tension_tracker_turn_wiring.py` — behavioral
  turn-pipeline wiring for the per-session `TensionTracker` (4 tests).

**Tests Written:** 4 tests covering 4 ACs
**Status:** RED (failing — ready for Dev). Verified via `testing-runner`: clean collection,
all 4 fail on the missing wiring; the AC3 OTEL assertion fails non-vacuously at line 165
(`0 >= 1` — zero `tension:round_observed` events, while `lore`/`retrieval` events *do* fire,
proving the turn runs real subsystem code).

**AC → test map:**
| AC | Test | What it pins |
|----|------|--------------|
| AC1 (per-session tracker exists) | `test_session_data_has_per_session_tension_tracker` | `_SessionData` dataclass field + default-constructed `TensionTracker` starting at zero (reflection tripwire — allowed runtime-type check, not a source grep) |
| AC1 (persists) + AC2 (cadence) | `test_tracker_is_per_session_and_accumulates_across_turns` | same instance across two turns; boring_streak monotonically accumulates; exactly one tension event per turn |
| AC2 (feed) + AC3 (OTEL) + AC4 (wiring) | `test_turn_drives_session_tracker_and_emits_tension_watcher_event` | one real `_execute_narration_turn` emits ≥1 `tension:round_observed` event AND moves the *session* tracker off zero (proves it's the per-session tracker, not a throwaway) |
| AC2 (edge) | `test_event_less_turn_does_not_crash_and_leaves_valid_state` | event-less turn does not raise; all axes stay in `[0,1]` |

### Rule Coverage

| Rule (python.md) | Test(s) / Self-check | Status |
|------|---------|--------|
| #6 test-quality: no vacuous assertions | AC3 OTEL assert verified to fail `0>=1` (non-vacuous); no `assert True` | clean |
| #6 test-quality: mock patches correct target | `monkeypatch` of `watcher_hub.publish_event` at source module (lazy-import target) | clean |
| #6 test-quality: every test asserts | all 4 carry meaningful assertions (field/instance, event count, accumulation, bounded ranges) | clean |
| #3 type annotations | fixture + helper + tests annotated (`-> None`, `-> list[dict]`, `Iterator[...]`) | clean |
| #9 async pitfalls | `@pytest.mark.asyncio` + `await` on turn fn; `AsyncMock` for orchestrator; no blocking calls | clean |
| #10 import hygiene | no star imports; reuses conftest helpers (established `_build_turn_context_for_test` precedent) | clean |

**Rules checked:** 6 of 13 lang-review rules apply to a pure-test diff (the rest target
production/source code Dev will write in GREEN); all applicable ones covered.
**Self-check:** 0 vacuous tests found (AC3 assertion explicitly measured non-vacuous).

**Handoff:** To Dev (Ponder Stibbons) for GREEN. Implementation shape: add
`tension_tracker: TensionTracker = field(default_factory=TensionTracker)` to `_SessionData`
(entity_store precedent), then drive `sd.tension_tracker.observe(...)` once per turn from a
seam inside `_execute_narration_turn` (reusing observe's OTEL emission). See the three TEA
Delivery Findings for the RoundResult-synthesis gap, the observe-vs-record_event subtlety,
and the seam rationale.
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/server/session_state.py` — `_SessionData` gains `tension_tracker: TensionTracker = field(default_factory=TensionTracker)` (per-session, mirrors the `entity_store` precedent) + import.
- `sidequest/server/websocket_session_handler.py` — new module-level `_drive_session_tension_tracker(sd, snapshot, *, encounter_resolved_this_turn)` helper + `RoundResult` import; called once per turn from `_execute_narration_turn` at the post-resolution seam (just before the per-turn `game_state_snapshot` publish, outside the validator guard so it fires every turn).
- `tests/server/test_tension_tracker_turn_wiring.py` — fixed a TurnContext-reuse defect (fresh context per turn); all assertions preserved.

**How it works:** Each turn, the helper feeds the per-session tracker — `update_stakes()` from the acting player's real HP (stakes track) and `observe(RoundResult, killed, lowest_hp_ratio)` (action track + spike + OTEL). `killed` is set only on a this-turn defeat (`player_victory`/`opponent_victory`); `lowest_hp_ratio` from seated combatant HP; a quiet turn is a Boring observation. `observe()` emits the existing `tension:round_observed` watcher event — the GM-panel pacing signal, previously dead in production.

**Tests:** 4/4 new wiring tests GREEN. Full server suite: **8803 passed, 0 failed, 1439 skipped** (no regressions). Lint clean (`ruff check`), format clean (`ruff format --check`), `session_state.py` 0 pyright errors and no new pyright errors in the handler (the 25 reported are pre-existing in that file; pyright is not in the project gate).

**Branch:** `feat/81-2-tension-tracker-producer` (pushed to origin).

**AC status:**
- AC1 (per-session tracker exists + persists) — done (field + same-instance/accumulation tests green).
- AC2 (turn events feed tracker; edge no-crash) — done (action+stakes fed each turn; empty-turn test green). Relative-magnitude math deferred to tracker unit tests (TEA deviation).
- AC3 (OTEL fires in a real turn) — done (`tension:round_observed` emitted every turn via `observe()`).
- AC4 (real wiring test, fails on develop) — done (behavioral OTEL+state assertions; was RED on develop, now GREEN).

**Self-review:**
- [x] Wired to production path (`_execute_narration_turn`), not just unit-tested — verified via the behavioral OTEL test.
- [x] Follows project patterns (entity_store default_factory precedent; reuses existing OTEL emission; no parallel telemetry).
- [x] All ACs met (with documented deviations).
- [x] Error handling: every read None/zero-guarded so the drive can't raise on the hot path (no try/except swallow — the tests require it to actually run).

**Handoff:** To Igor (TEA) for the verify phase (simplify + quality-pass).
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None (all 4 ACs met; TEA + Dev deviations properly logged)

Verified the committed diff against the story context AC-by-AC:
- AC1 — `tension_tracker` per-session field on `_SessionData` via `field(default_factory=...)`, exactly the `entity_store` precedent. ✓
- AC2 — driven once per turn (`update_stakes` from real PC HP + `observe()`); empty-turn guarded. ✓ (relative-magnitude math deferred to tracker unit tests — logged TEA/Dev deviation, sound).
- AC3 — `observe()` emits the existing `tension:round_observed` watcher event every turn; reuses emission, no parallel telemetry (epic-81 guardrail honored). ✓
- AC4 — behavioral wiring test (OTEL + accumulated state) red on develop, green after. ✓

**Reuse-first check:** No new infrastructure. Reuses `TensionTracker`/`observe()`/its OTEL emission and the `entity_store` per-session pattern. Helper is a pure, testable module-level function. Pragmatic-restraint satisfied.

**Non-blocking architectural observations (NOT spec mismatches — recorded for downstream):**

- **MP tension-signal placement** (Architectural — Minor; recommend **D — Defer**)
  - The tracker is on per-connection `_SessionData`; in MP `_execute_narration_turn` is driven by the rotating barrier driver, so tension accumulates on whichever player drove that turn — the shared-scene signal fragments across players' trackers.
  - This is *consistent with the `entity_store` precedent* (same per-`_SessionData` placement) and the story's explicit "per-session in-memory is acceptable for v1" assumption. A correct MP fix (host the tracker on `SessionRoom`/shared session) is a broader pattern change touching the same precedent and belongs to a follow-up — likely alongside 81-3 (pacing-hint consumer) or a dedicated MP-pacing story. No action this story.

- **Hot-path safety of the drive** (Behavioral robustness — Minor; recommend Reviewer consider **B** during review)
  - `_drive_session_tension_tracker` is the only per-turn watcher emission in `_execute_narration_turn` not wrapped in try/except — the sibling `game_state_snapshot`, bridge-diagnostic, and force-flush blocks all guard their emits. It is currently fully None/zero-guarded so it cannot raise except via `watcher_hub.publish_event`; wrapping it (suppress + log) would match the established hot-path-safety pattern and ADR-006 graceful degradation. Low actual risk today; a clean defensive add for the verify/review pass. Not gating.

**Decision:** Proceed to verify (TEA). No hand-back to Dev — spec is aligned; both observations are non-blocking Defer/note items.
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (4/4 wiring tests; full server suite 8803 passed, 0 failed)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`session_state.py`, `websocket_session_handler.py`, `test_tension_tracker_turn_wiring.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | HIGH: test fixtures (`captured_watcher_events`/`_tension_events`) duplicated from `tests/game/test_tension_tracker_otel_wiring.py`. MED: split `_drive_session_tension_tracker` into 4 helpers. LOW: single call-site coupling (no action). |
| simplify-quality | 2 findings | HIGH: error-handling gap — drive is the only unwrapped per-turn watcher emit. MED: docstring overstates "can never raise". |
| simplify-efficiency | clean | No findings — walrus comprehension + guards justified, helper not over-engineered. |

**Applied (1 high + 1 coupled medium):**
- **HIGH error-handling gap** — wrapped `_drive_session_tension_tracker(...)` in `try/except Exception: logger.exception(...)` at the call site, matching the sibling per-turn watcher emits (`game_state_snapshot`, bridge-diagnostic, force-flush) and ADR-006 graceful degradation. Corroborated by the architect spec-check.
- **MED docstring accuracy** (coupled to the above) — corrected the helper's overstated "the drive can never raise on the hot path" to accurately describe the input guards + the call-site try/except.

**Flagged for review / deferred (not auto-applied):**
- **HIGH test-fixture duplication** — deliberately NOT applied. Extracting `captured_watcher_events`/`_tension_events` to a shared `tests/conftest.py` is a cross-package refactor touching an *unrelated existing test file* (`tests/game/test_tension_tracker_otel_wiring.py`) and the test-discovery surface — scope creep on a wiring story, and the duplication pre-dates this story (the OTEL test had the pattern first). Good standalone cleanup; recommend a dedicated follow-up. Reviewer may weigh in.
- **MED helper-split** — deferred. simplify-efficiency rated the helper clean/not over-engineered; splitting into 4 sub-helpers is a reasonable 81-3 refactor candidate, not warranted now.

**Reverted:** 0
**Overall:** simplify: applied 1 fix (+ coupled docstring); 2 findings flagged/deferred.

**Quality Checks:** Full server suite 8803 passed / 0 failed / 1439 skipped; `ruff check` clean; `ruff format --check` clean; no new pyright errors.

**Handoff:** To Reviewer (Granny Weatherwax) for code review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (4/4 green, lint+format clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — edges assessed by Reviewer |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — assessed by Reviewer |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed by Reviewer |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — assessed by Reviewer |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — simplify ran in verify phase |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — rule-by-rule done by Reviewer |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents`, assessed directly)
**Total findings:** 1 medium, 1 low confirmed; 0 dismissed; 0 deferred-unaddressed (both documented for follow-up)

## Rule Compliance (python.md, 13 checks vs the diff)

1. **Silent exception swallowing** — COMPLIANT. The one broad `except Exception` (call site) logs via `logger.exception("tension_tracker.drive_failed: ...")` and matches the sibling per-turn emits (`game_state_snapshot`, bridge-diagnostic). Logged, not swallowed; ADR-006 graceful degradation for a non-critical per-turn producer.
2. **Mutable default args** — COMPLIANT. No mutable default literals; `tension_tracker` uses `field(default_factory=TensionTracker)` (correct dataclass idiom, the `entity_store` precedent).
3. **Type annotations** — COMPLIANT. `_drive_session_tension_tracker(sd: _SessionData, snapshot: GameSnapshot, *, encounter_resolved_this_turn: bool) -> None`; locals `killed: str | None`, `lowest_hp_ratio: float | None`.
4. **Logging** — COMPLIANT. Error path uses `logger.exception` inside the `except`; correct level for an unexpected hot-path failure.
5. **Path handling** — N/A (no path ops).
6. **Test quality** — COMPLIANT. No vacuous asserts (AC3 measured `0>=1` on develop); `monkeypatch` targets `watcher_hub.publish_event` at the source module (correct lazy-import target).
7. **Resource leaks** — N/A.
8. **Unsafe deserialization** — N/A.
9. **Async pitfalls** — COMPLIANT. Helper is sync, correctly called without `await` from the async turn; no blocking I/O (in-process watcher publish).
10. **Import hygiene** — COMPLIANT. Explicit imports (`RoundResult`, `TensionTracker`); no star imports; no new cycle (tension_tracker imports only genre.models.ocean + lazy watcher_hub).
11. **Input validation at boundaries** — N/A (internal producer; reads own session state).
12. **Dependency hygiene** — N/A (no dep changes).
13. **Fix-introduced regressions** — COMPLIANT. The verify-phase wrap added no new issues; full suite green.

## Reviewer Observations

- **[MEDIUM] [EDGE] Stakes track keys off `sd.player_name`, not the seated character name** at `websocket_session_handler.py:173`. This file's own `perspective_character_name(sd)` (:127) exists because the authoritative acting-character key is `player_seats[player_id]` (falling back to `player_name`); line 2698 uses it for `party_location`. `find_creature_core(sd.player_name)` will silently return `None` when the seated character name differs from `player_name` (MP, or a renamed character), so the stakes track no-ops while the action track still works. Single-player (the primary playtest path, where `player_name == core.name`) is unaffected. Non-blocking; recommend `find_creature_core(perspective_character_name(sd))`. Rides with the architect's deferred MP-tension item.
- **[LOW] The drive fires on the opening (scene-set) turn too** (call site is not under an `is_opening_turn` guard). On the opening turn the encounter is typically `None`, producing a Boring observation that nudges the gambler's ramp before the player's first real action. Cosmetic (drama_weight ~0.05); harmless.
- **[VERIFIED] [SILENT] The broad `except` is logged, not a silent fallback** — `websocket_session_handler.py:2300-2310`: `except Exception as exc: logger.exception("tension_tracker.drive_failed: %s", exc)`. Matches the sibling `game_state_snapshot` block and ADR-006. Complies with "No Silent Fallbacks" (the failure is loud in logs; the producer is non-critical to the turn).
- **[VERIFIED] No ZeroDivision / ValueError on the hot path** — `:174` guards `pc.hp.max > 0` before `update_stakes` (which raises on `max_hp <= 0`) and before the `:182` division; `:186` guards `min(ratios)` with `if ratios`. Evidence: tension_tracker.py:346 raises only on `max_hp <= 0`, excluded by the guard.
- **[VERIFIED] [TYPE] Inputs to `observe()` are correctly typed, not stringly-typed** — `RoundResult(round=int)`, `killed: str | None`, `lowest_hp_ratio: float | None` match `observe(self, round: RoundResult, killed: str | None, lowest_hp_ratio: float | None)` at tension_tracker.py:394. No unsafe casts.
- **[VERIFIED] [SIMPLE] Helper is not over-engineered** — simplify-efficiency (verify phase) rated it clean; the walrus comprehension avoids a double `find_creature_core` call. Single call site; no premature abstraction.
- **[VERIFIED] [RULE] Per-session field follows the established precedent** — `session_state.py` `tension_tracker: TensionTracker = field(default_factory=TensionTracker)` mirrors `entity_store` (:245). Correct dataclass idiom; round-trips like the other in-memory per-session fields.
- **[VERIFIED] [DOC] Docstring is accurate post-verify** — the overstated "can never raise" claim was corrected in the verify phase to describe the input guards + call-site try/except.
- **[VERIFIED] [SEC] No security surface** — internal per-session producer; reads own session snapshot state, no auth/input/secret/tenant boundary. No injection or info-leak vector.
- **[VERIFIED] [TEST] OTEL reuse, no parallel telemetry** — `observe()` emits the existing `tension:round_observed` watcher event (tension_tracker.py:440); the code reuses it rather than adding a parallel channel (epic-81 guardrail honored).

### Devil's Advocate

Suppose this code is broken. The most credible attack is the **stakes track silently dying**: `find_creature_core(sd.player_name)` is a name-string lookup, and SideQuest identity is notoriously a case-folded name string split across stores (see NPC Identity Hardening, epic 72). If `sd.player_name` ever drifts from the seated `core.name` — a renamed PC, an MP seat, a reconnect that re-derives `player_name` — the lookup returns `None`, `update_stakes` never runs, and `stakes_tension` stays pinned at 0.0 forever. The GM panel would show a tension signal that *looks* alive (the action/boring ramp moves) while half the dual-track model is quietly dead — precisely the "convincing but mechanically hollow" failure the OTEL principle exists to catch. The action track masks it, so nobody notices. That is the one finding I'd insist be tracked.

What else? A **watcher-hub outage**: if `publish_event` raises every turn, the new `try/except` swallows it (logged) — good, the turn survives — but then `observe()` *also* never completes its state mutation for that turn (the publish is the last statement inside observe), so tension silently stops accumulating while the turn proceeds. Acceptable degradation, and loud in logs. **Performance**: the comprehension calls `find_creature_core` (an O(characters+npcs) scan) per actor, so a turn is O(actors × roster) — but encounters seat a handful of actors and rosters are small; not a real cost. **Degraded turns**: if the narrator path raises before the seam, the drive is skipped entirely and that turn contributes no tension observation (unlike the TurnRecord, which has a degraded fallback). That is a *gap*, not a *bug* — a crashed turn has no real outcome to observe — but it means "fires every turn" is really "fires every *completed* turn." **Confused author**: a homebrew pack with `hp.max = 0` on a creature would be skipped by the guard (no crash), correct. None of these rise to Critical/High. The stakes-keying issue is the real one, and it's MEDIUM because single-player works and MP tension is already a deferred follow-up.

### Reviewer (audit)

Deviation audit — every logged deviation stamped:
- **TEA: AC2 relative-magnitude clause not re-driven through the turn path** → ✓ ACCEPTED by Reviewer: sound — the dramatic>boring/decay math is the tracker's own responsibility and is covered by `tests/game/test_tension_tracker.py`; re-driving it through the turn path would couple the wiring test to the unspecified RoundResult synthesis.
- **Dev: Drove via `observe()` not `record_event()`** → ✓ ACCEPTED by Reviewer: required — only `observe()` emits the `tension:round_observed` event AC3 demands; reuses the existing emission per the epic-81 no-parallel-telemetry guardrail.
- **Dev: Per-turn HP-delta `damage_events` not synthesized** → ✓ ACCEPTED by Reviewer: the story Assumptions explicitly invited this; real signal is still present via stakes (PC HP) + kill (resolution) + NearMiss (lowest HP ratio). Finer fidelity is a documented follow-up.
- **Dev: Modified a TEA test (TurnContext reuse → fresh-per-turn)** → ✓ ACCEPTED by Reviewer: a genuine test-infra defect (`PhaseTimings` finalizes per turn; production builds a fresh context per turn). All assertions preserved; the change makes the test match real usage.

No undocumented deviations found beyond the observations above (the `sd.player_name` keying is a code finding, not a spec deviation — the spec didn't specify the key).

### Reviewer (code review)
- **Improvement** (non-blocking): Stakes track keys off `sd.player_name` instead of the seated acting-character name. Affects `sidequest/server/websocket_session_handler.py` (`_drive_session_tension_tracker` — use `find_creature_core(perspective_character_name(sd))` so the stakes track doesn't silently no-op when the seated name differs from `player_name`, e.g. MP/rename). Pairs with the architect's deferred MP-tension item. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The per-turn drive is unconditional, so the opening scene-set turn produces a pre-action Boring observation. Affects `_drive_session_tension_tracker` call site (consider skipping when `is_opening_turn`). Cosmetic. *Found by Reviewer during code review.*

## Reviewer Assessment

**Verdict:** APPROVED

No Critical or High findings. Implementation is a clean, well-tested integration that wires ADR-024's TensionTracker into the production turn pipeline with real mechanical backing and reuses the existing OTEL emission (the GM-panel pacing signal, previously dead).

**Data flow traced:** player action → `_execute_narration_turn` → (narration resolves, snapshot mutated) → `_drive_session_tension_tracker(sd, snapshot, encounter_resolved_this_turn)` reads the acting PC's HP (stakes) + encounter actors' HP / this-turn defeat (action) → `sd.tension_tracker.observe(...)` accumulates per-session state and emits `tension:round_observed`. Safe because every read is None/zero-guarded and the call is wrapped so a watcher hiccup can't crash the turn.

**Pattern observed:** per-session producer on `_SessionData` via `field(default_factory=...)` — mirrors the `entity_store` precedent (session_state.py); driven once per turn in the handler, not the LLM-gated narration path, so the signal updates every completed turn.

**Error handling:** `try/except Exception: logger.exception(...)` at the call site (websocket_session_handler.py:2300-2310) — matches sibling per-turn watcher emits and ADR-006; loud in logs, non-fatal to the turn.

**Subagent dispatch tags:** [EDGE] stakes-keying (MEDIUM) + edges enumerated; [SILENT] broad-except is logged (verified); [TEST] non-vacuous, correct mock target (verified); [DOC] docstring accurate post-verify (verified); [TYPE] correctly typed observe() inputs (verified); [SEC] no security surface (verified); [SIMPLE] not over-engineered (verified); [RULE] all 13 python.md checks compliant. (8 diff-subagents disabled via settings; each domain assessed directly.)

**Non-blocking follow-ups:** stakes-keying → `perspective_character_name(sd)`; opening-turn pre-ramp. Both recorded as delivery findings; neither gates this story.

**Handoff:** To SM for finish-story.