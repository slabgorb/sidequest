---
story_id: "77-7"
jira_key: ""
epic: "77"
workflow: "tdd"
---
# Story 77-7: Engine lull-escalation — drive a Bang/complication when turns_since_meaningful climbs (ADR-024/025/128)

## Story Details
- **ID:** 77-7
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T17:18:27Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T16:33:29Z | 2026-06-05T16:35:37Z | 2m 8s |
| red | 2026-06-05T16:35:37Z | 2026-06-05T16:55:50Z | 20m 13s |
| green | 2026-06-05T16:55:50Z | 2026-06-05T17:09:55Z | 14m 5s |
| review | 2026-06-05T17:09:55Z | 2026-06-05T17:18:27Z | 8m 32s |
| finish | 2026-06-05T17:18:27Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The producer seam (handler ~line 1211, peer to `tick_seeds`) runs BEFORE the per-turn tension `observe()` at line 2415 inside `_execute_narration_turn`. So the lull step reads `boring_streak` as accumulated through the PRIOR turn, not including this turn's classification. This matches the story's "peer to tick_seeds" seam, but Dev should confirm it's intended. Affects `sidequest/server/websocket_session_handler.py` (selector call-site placement). *Found by TEA during test design.*
- **Question** (non-blocking): Cooldown state and the pending escalation directive MUST persist across save/resume for resume-safe re-fire (AC5). They therefore belong on `GameSnapshot` (persisted), NOT on `_SessionData` (ephemeral). Affects `sidequest/game/session.py` (`GameSnapshot` is `extra="ignore"` pydantic — new fields must be DECLARED, not set ad-hoc, or assignment raises). *Found by TEA during test design.*
- **Improvement** (non-blocking): On a fire, the consumer override (`_build_turn_context`, `session_helpers.py:~1204`) must set `pacing_hint.escalation_beat` to the stored directive REGARDLESS of the current `boring_streak` — the directive can outlive the boring streak the fire itself resets. `PacingHint` is `frozen=True`, so use `dataclasses.replace`. Affects `sidequest/server/session_helpers.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Story 82-2 (ADR-049) added `narrator_verbosity` / `narrator_vocabulary` to `GameSnapshot` but never placed them in a 61-5 governance registry, so `test_snapshot_field_governance::test_every_snapshot_field_is_categorized` was already RED on develop. Fixed opportunistically (classified both as `_BOUNDED_BY_CONSTRUCTION` enum-scalars). Affects `sidequest/server/session_helpers.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `heavy_metal/barsoom` (epic 89 draft world) fails the two content pack-validators (`test_all_live_packs_pass_content_validation`, `test_all_live_packs_pass_cross_reference_lint`) — missing `portrait_manifest.yaml`/`tropes.yaml`/`legends`/portrait+poi dirs. Pre-existing, content-only, unrelated to this Python diff; left for epic 89. Affects `sidequest-content/genre_packs/heavy_metal/worlds/barsoom`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): `_narrative_hint_for` silently returns `""` when the selected active seed's id is absent from `pack.seed_tropes` (a resumed save whose active seed predates a pack edit) or the seed's `narrative_hint` is empty. The lull then "fires" (`last_lull_fire_turn` armed, `SPAN_LULL_ESCALATION fired=True`) but injects no directive — a silent fallback (CLAUDE.md "No Silent Fallbacks") masking content/config drift, mitigated only by the OTEL span recording the fire. Consider emitting a watcher warning, or skipping a hint-less seed (treat as `none_available` / pick another). Affects `sidequest/game/lull_escalation.py` (`_narrative_hint_for` / the fire path). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Added a fourth `reason` value `"not_triggered"` for the below-threshold no-op**
  - Spec source: context-story-77-7.md, AC4
  - Spec text: "reason(fired|cooldown|none_available)"
  - Implementation: `LullEscalationResult.reason` may also be `"not_triggered"` (below threshold). The three spec'd reasons are the EMITTED-span reasons; `"not_triggered"` is the no-op return and emits NO span (AC1 no-op + AC4 "span when the step runs").
  - Rationale: AC1 requires below-threshold to be a no-op; AC4's three reasons are all "engaged" outcomes. A distinct return value lets the no-op be asserted without emitting a span.
  - Severity: minor
  - Forward impact: Dev's enum/literal must include `"not_triggered"`; the GM panel never sees it (no span).
- **Pinned the API surface (`apply_lull_escalation` signature + `LullEscalationResult` shape)**
  - Spec source: context-story-77-7.md, AC1–AC5 (behavior described, no signature given)
  - Spec text: "a new post-bump escalation step … select … fire … govern"
  - Implementation: `apply_lull_escalation(snapshot, pack, *, tracker, thresholds, session_id, now_turn) -> LullEscalationResult(fired, selected_seed_id, reason, directive)`
  - Rationale: RED needs a concrete callable. Signature mirrors the existing `tick_seeds`/`draw_engaged_seed` seam shape (snapshot + pack + keyword turn/session).
  - Severity: minor
  - Forward impact: Dev may rename with a logged deviation; tests assert this contract.
- **AC5 "next turn's narrator context carries the directive" realized as two real-seam tests, not one full two-turn handler sequence**
  - Spec source: context-story-77-7.md, AC5
  - Spec text: "drive a real lull turn through the handler and assert the NEXT turn's narrator context carries the seed-derived escalation directive"
  - Implementation: (a) producer — real `_execute_narration_turn` during a lull emits `SPAN_LULL_ESCALATION` (wired into the turn); (b) consumer — the real selector stores a directive, then the real `_build_turn_context` surfaces it on `TurnContext.pacing_hint.escalation_beat`. The consumer test drives the real producer (`apply_lull_escalation`) directly rather than threading it through a second full `_execute_narration_turn`.
  - Rationale: keeps the test storage-agnostic (never names the snapshot field) while still exercising both real seams; a single two-turn handler chain would couple the assertion to an unbuilt storage field and the mocked orchestrator hides the injected prompt.
  - Severity: minor
  - Forward impact: none — both real code paths are exercised.
- **AC6 (explicit non-goals) has no tests**
  - Spec source: context-story-77-7.md, AC6
  - Spec text: "DEFER … documented in the story, NOT built"
  - Implementation: no tests for NPC-autonomy / per-category quiet-turn detector / separate Bang-catalog struct.
  - Rationale: AC6 is a documentation AC for things explicitly not built; there is no behavior to assert.
  - Severity: minor
  - Forward impact: none.
- **`selected_seed_id` span attribute is `""` (empty string), not `None`, when nothing fired**
  - Spec source: context-story-77-7.md, AC4 ("selected_seed_id|null")
  - Spec text: "selected_seed_id|null"
  - Implementation: the OTEL span attribute carries `""` on cooldown/none_available (OTEL attributes reject `None`); `LullEscalationResult.selected_seed_id` is still `None`.
  - Rationale: mirrors the existing `pacing_hint_span` convention (`escalation_present` bool because "OTEL attributes reject None values").
  - Severity: minor
  - Forward impact: GM-panel extractor reads `""` as "no seed".

### Dev (implementation)
- **Implemented exactly to TEA's pinned API contract — no contract deviations**
  - Spec source: .session/77-7-session.md, TEA Assessment + tests
  - Spec text: `apply_lull_escalation(snapshot, pack, *, tracker, thresholds, session_id, now_turn) -> LullEscalationResult(fired, selected_seed_id, reason, directive)`; reasons fired/cooldown/none_available/not_triggered
  - Implementation: built precisely that surface in `sidequest/game/lull_escalation.py`.
  - Rationale: the RED tests are the contract; matched them verbatim.
  - Severity: none
  - Forward impact: none.
- **Classified two pre-existing 82-2 fields in the governance registry (out of strict story scope)**
  - Spec source: tests/server/test_snapshot_field_governance.py (61-5 architecture gate)
  - Spec text: "every top-level GameSnapshot field must be in exactly one bounding registry"
  - Implementation: added `narrator_verbosity` / `narrator_vocabulary` to `_BOUNDED_BY_CONSTRUCTION` alongside my own two new fields.
  - Rationale: the gate was already RED from 82-2; my two new fields would have to be classified anyway, and a red architecture gate would block/muddy verification. Trivial, correct, same-registry fix.
  - Severity: minor
  - Forward impact: none — pure categorization, no runtime behavior change.
- **Added `drama_thresholds=None` to the shared `session_fixture` MagicMock pack**
  - Spec source: tests/server/conftest.py (shared fixture)
  - Spec text: n/a (fixture infrastructure)
  - Implementation: the new producer reads `genre_pack.drama_thresholds or DramaThresholds()` in the turn path; a bare MagicMock returned a truthy auto-mock there, crashing 3 existing tension-wiring tests. Pinned `None` (realistic "no pacing.yaml" value) — same pattern as the fixture's existing `progression=ProgressionConfig()`.
  - Rationale: root-cause fix (incomplete fixture) rather than defensive isinstance-guarding production code against a test mock.
  - Severity: minor
  - Forward impact: none — None is the realistic default; tests that need thresholds set them explicitly.

### Reviewer (audit)
- **TEA: `not_triggered` reason added** → ✓ ACCEPTED: AC4's three reasons are the *emitted-span* reasons; a distinct no-op return that emits no span is the correct way to satisfy AC1 (no-op) + AC4 (span only when engaged).
- **TEA: pinned `apply_lull_escalation` API surface** → ✓ ACCEPTED: signature parallels `tick_seeds`/`draw_engaged_seed`; Dev implemented it verbatim.
- **TEA: AC5 split into producer-span + consumer-directive real-seam tests** → ✓ ACCEPTED: both seams are exercised through real code (`_execute_narration_turn`, `_build_turn_context`); storage-agnostic, refactor-stable, fails on develop. Stronger than a single mocked two-turn chain.
- **TEA: AC6 has no tests** → ✓ ACCEPTED: AC6 is documentation-only ("not built"); nothing to assert.
- **TEA: span `selected_seed_id` is `""` not `None` when not fired** → ✓ ACCEPTED: OTEL attributes reject `None`; mirrors the existing `pacing_hint_span.escalation_present` bool convention.
- **Dev: implemented exactly to TEA's contract** → ✓ ACCEPTED: verified against the diff — no contract drift.
- **Dev: classified pre-existing 82-2 `narrator_verbosity`/`narrator_vocabulary` in `_BOUNDED_BY_CONSTRUCTION`** → ✓ ACCEPTED: the 61-5 governance gate was already RED on develop; both fields are enum-scalars (correct category); a 2-line fix in a file already touched, with my two new fields, that unblocks the architecture gate. Incidental but correct and well-documented.
- **Dev: `drama_thresholds=None` on the shared `session_fixture`** → ✓ ACCEPTED: root-cause fix for the new turn-path read of `genre_pack.drama_thresholds`; `None` is the realistic "no pacing.yaml" value and mirrors the fixture's existing `progression=ProgressionConfig()` precedent. Preferable to defensive isinstance-guarding production against a test mock.
- **No undocumented deviations found.** The diff matches the logged deviations; the producer-seam placement, consumer override, and persistence all match the design and TEA's three Delivery Findings.

## Implementation Notes

**Story Classification:** Engine lull-escalation, mechanics-first with OTEL instrumentation.

**REUSE MAP (per story description):**
- **Lull Signal:** TensionTracker (game/tension_tracker.py) computes boring_streak + drama_weight every turn; pacing_hint() trips escalation_beat at boring_streak >= escalation_streak (lines ~359-383).
- **Seed Catalog:** seed_tropes deck (ADR-128) — game/seed_deck.py (deterministic draw via SHA-256), game/seed_tick.py (ensure_initial_draw/draw_engaged_seed/tick_seeds), rendered by agents/seed_context_builder.py. SeedTrope.narrative_hint (genre/models/tropes.py:81).
- **Governance:** game/trope_tuning.py — MAX_SIMULTANEOUS_ACTIVE, FIRE_COOLDOWN_TURNS.
- **OTEL Span:** SPAN_SEED_FIRED (telemetry/spans/seed.py) — needs first real consumer. NEW: SPAN_LULL_ESCALATION.
- **Seam Location:** websocket_session_handler.py:~1170-1191 (tick_seeds) — the escalation step runs peer to tick_seeds, post-record_interaction, reads sd.tension_tracker, mutates snapshot.active_seeds in place.

**Design Direction (v1 — enacts ADR-024/025/128, NO new ADR):**
1. **TRIGGER:** reuses live signal — boring_streak >= escalation_streak (pacing_hint.escalation_beat present). Ride ADR-024 tension track, no new ADR-025 per-category detector in v1.
2. **SELECT:** pick one seed from snapshot.active_seeds (prefer scene-fit via flavor_tags/delivery_hints; deterministic resume-safe tie-break from (session_id, turn, drawn_ids)). If empty, draw one first (reuse draw_engaged_seed).
3. **FIRE:** convert selected seed's narrative_hint into concrete escalation directive for NEXT turn's narrator context, REPLACING generic escalation_beat text. Mark seed fired (SPAN_SEED_FIRED first consumer) and advance lifespan via tick.
4. **GOVERN:** respect FIRE_COOLDOWN_TURNS — never fire consecutive turns.
5. **SEAM:** post-bump, peer to tick_seeds (websocket_session_handler.py:~1170-1191), reads sd.tension_tracker, mutates snapshot.active_seeds in place.
6. **OTEL (LOAD-BEARING):** new routed SPAN_LULL_ESCALATION carries: boring_streak, drama_weight, fired(bool), selected_seed_id|null, reason(fired|cooldown|none_available). Must light pacing/tension subsystem on GM panel ③ grid.

**Acceptance Criteria (from epic-77.yaml:94-100):**
- AC1: Lull trigger reuses live signal; below threshold = no-op. Test: synthetic snapshot with boring_streak at/below threshold.
- AC2: Select-and-fire active seed → its narrative_hint becomes escalation directive in NEXT turn's context, replacing generic text. If empty, draw first. Test: active seed → hint injected; empty → seed drawn then fired.
- AC3: Respect ADR-128 governor — never fire consecutive turns (FIRE_COOLDOWN_TURNS). Test: two lull turns → fires turn 1, cooldown-skips turn 2 with reason=cooldown.
- AC4: OTEL (LOAD-BEARING) — emit ROUTED SPAN_LULL_ESCALATION every run, carrying boring_streak, drama_weight, fired, selected_seed_id|null, reason. Light GM panel ③ pacing/tension. SPAN_SEED_FIRED gains first real consumer on fire. Test: span asserted on fire AND cooldown-skip with correct reason.
- AC5: Seam + resume safety + wiring — post-record_interaction, peer to tick_seeds, deterministic selection. Resume re-fires identically. Test: drive real lull turn through handler, assert NEXT turn's narrator context carries seed-derived escalation directive.
- AC6 (explicit non-goals, documented not built): (a) NPC-autonomous-goal escalation (ADR-053 dormant); (b) full ADR-025 per-category quiet-turn detector; (c) separate Bang-catalog struct distinct from seed_tropes. v1 = wire existing lull signal to fire existing seed with OTEL proof.

**Branch:** feat/77-7-engine-lull-escalation
**Branch Strategy:** gitflow (feat/77-7-engine-lull-escalation branches from develop)

## Sm Assessment

**Routing decision:** Hand to TEA (Radar) for the RED phase. tdd workflow, single repo (sidequest-server → develop). Jira skipped — personal project, no key.

**Why this story is well-formed for RED:** The Architect's design is a reuse-first, NO-new-ADR v1 slice with named seams and a six-point AC set already in the session. The lull SIGNAL (TensionTracker.pacing_hint escalation_beat), the Bang CATALOG (ADR-128 seed deck), the governor (FIRE_COOLDOWN_TURNS), and the unconsumed SPAN_SEED_FIRED all already exist — this story wires a SELECTOR between them and adds SPAN_LULL_ESCALATION. That makes the failing tests concrete and the surface area bounded.

**Where TEA should aim the failing tests (per AC1–AC5):**
- The selector seam runs peer to `tick_seeds` in `websocket_session_handler.py:~1170-1191`, reads `sd.tension_tracker`, mutates `snapshot.active_seeds` in place — so at least one test must drive a real lull turn through the handler (AC5 wiring test), not just the selector in isolation. Per project doctrine, a unit test on the selector is necessary but NOT sufficient.
- OTEL is LOAD-BEARING, not decoration (AC4): assert the routed `SPAN_LULL_ESCALATION` fires on BOTH the fire path and the cooldown-skip path, with the correct `reason` field — this is the lie detector for "engine pushed" vs "Claude improvised."
- Determinism: selection tie-break must reuse the seed_deck SHA-256 (session_id, turn, drawn_ids) pattern — NO wallclock/Math.random. A resume-safety test (re-fire identically) belongs in RED.

**Watch-for (escalate, don't patch):** If the selector policy — which seed wins, and how cooldown composes with the ADR-128 governor's MAX_SIMULTANEOUS_ACTIVE — turns out to need ratification during the first design pass, escalate to the Architect for a thin ADR (epic-59 pattern) rather than forcing a decision in code.

**Out of scope (AC6, documented not built):** NPC-autonomous-goal escalation (ADR-053 dormant), the full ADR-025 per-category quiet-turn detector, and any separate Bang-catalog struct distinct from seed_tropes. Don't let RED tests creep into these.

**Gate status:** session ✓, context ✓ (6978 bytes w/ ACs + technical approach), server branch ✓, status in_progress ✓, Jira skipped (explicit). Clear to hand off.

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-pt engine feature with load-bearing OTEL; pure-chore bypass does not apply.

**Test Files:** (commit `b06f3074`)
- `tests/game/test_lull_escalation.py` — selector/fire/cooldown/determinism (AC1–AC3 + resume-safe selection). 9 tests.
- `tests/telemetry/test_lull_escalation_span.py` — `SPAN_LULL_ESCALATION` route + emission on fire / cooldown / none_available / below-threshold, plus `SPAN_SEED_FIRED` first-engine-consumer (AC4). 9 tests.
- `tests/server/test_lull_escalation_turn_wiring.py` — producer span through real `_execute_narration_turn`, negative non-lull, consumer directive through real `_build_turn_context` (AC5). 3 tests.

**Tests Written:** 21 tests covering 5 ACs (AC6 is documentation-only → no tests, see deviation).
**Status:** RED — all 21 fail. Unit + telemetry fail on `ModuleNotFoundError: sidequest.game.lull_escalation`; server tests fail on missing module / `ImportError: SPAN_LULL_ESCALATION`. The two producer wiring tests REACH their assertions (the real turn path executes cleanly with the augmented fixture), so they are meaningful once Dev wires the span. Helper assumptions (DramaThresholds kwarg, `boring_streak` increment, SeedState/active_seeds construction, threshold boundary) independently validated against live code — the GREEN target is reachable.

### Rule Coverage

| Rule (lang-review/python.md) | Test(s) | Status |
|------|---------|--------|
| #6 Test quality (no vacuous asserts) | self-check: every test asserts a specific value (reason/seed_id/directive/span attrs), no `assert True`, no bare-truthy, no skips | enforced |
| #3 Type annotations at boundaries | pinned via `apply_lull_escalation` typed signature + `LullEscalationResult` field asserts | failing |
| #1 No silent swallow / no-op | `test_empty_active_and_empty_deck_is_none_available` (empty deck reports `none_available`, never silent) | failing |
| #9 Async correctness | producer tests `await` the real `_execute_narration_turn` (`@pytest.mark.asyncio`) | failing |
| OTEL Observability (CLAUDE.md, ADR-031) | `SPAN_LULL_ESCALATION` routed + emitted on all 3 engaged outcomes; `SPAN_SEED_FIRED` consumer on fire | failing |
| #2,#5,#7,#8,#11,#12 | N/A — pure in-memory selector: no mutable defaults, no path/IO, no resources, no deserialization, no user-input boundary, no new deps | N/A |

**Rules checked:** 5 of 5 applicable lang-review rules have test coverage (7 rules N/A for a pure in-memory selector).
**Self-check:** 0 vacuous tests found (all assertions check specific values; no `assert True` / bare-truthy / skipped tests).

**Handoff:** To Dev (Winchester) for GREEN. Build order suggestion: (1) `sidequest/game/lull_escalation.py` (`apply_lull_escalation` + `LullEscalationResult`) → unblocks the unit suite; (2) `SPAN_LULL_ESCALATION` in `spans/pacing.py` (component `tension`) + emission inside the selector → unblocks telemetry; (3) wire the producer peer to `tick_seeds` in `websocket_session_handler.py` and the consumer override in `_build_turn_context` (`session_helpers.py`) → unblocks the server suite. Mind the three Delivery Findings: seam ordering (lull reads prior-turn streak), persist cooldown + directive ON the snapshot (declared fields, `extra="ignore"`), and override `escalation_beat` regardless of current streak (`dataclasses.replace`, `PacingHint` is frozen).

---
## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/lull_escalation.py` (new) — `apply_lull_escalation` + `LullEscalationResult`; deterministic resume-safe selection (SHA-256 over `session_id|turn|sorted(ids)`), cooldown via `FIRE_COOLDOWN_TURNS`, draw-on-empty via `draw_engaged_seed`.
- `sidequest/telemetry/spans/pacing.py` — `SPAN_LULL_ESCALATION` (routed, `component="tension"`) + `lull_escalation_span` helper.
- `sidequest/game/session.py` — `GameSnapshot.pending_escalation_directive` + `last_lull_fire_turn` (persisted; resume-safe cooldown + directive carry).
- `sidequest/server/websocket_session_handler.py` — producer wiring peer to `tick_seeds` (post-`record_interaction`, before the per-turn tension `observe()`).
- `sidequest/server/session_helpers.py` — consumer override of `escalation_beat` in `_build_turn_context` (consume-once); + classified the pre-existing 82-2 `narrator_verbosity`/`narrator_vocabulary` fields in the 61-5 governance registry.
- `tests/server/conftest.py` — pinned `drama_thresholds=None` on the shared fixture pack (root-cause fix for the turn-path read).

**Tests:** 21/21 new tests GREEN. Full server suite: **9745 passed, 1471 skipped, 2 failed** — both failures are the pre-existing `heavy_metal/barsoom` draft-world content-validators (epic 89), unrelated to this Python-only diff. Lint (`ruff check`), format (`ruff format --check`), and `pyright` all clean on every changed file (0 errors in new code; the 27 pyright errors in `websocket_session_handler.py` are all pre-existing, lines 2765–3123, nowhere near the ~1237 insertion).
**Branch:** `feat/77-7-engine-lull-escalation` (pushed).

**AC coverage:** AC1 (live-signal trigger / below-threshold no-op) ✓; AC2 (select-and-fire, draw-on-empty, directive = narrative_hint) ✓; AC3 (FIRE_COOLDOWN_TURNS governor) ✓; AC4 (routed `SPAN_LULL_ESCALATION` on fire/cooldown/none_available + `SPAN_SEED_FIRED` consumer) ✓; AC5 (producer span through real `_execute_narration_turn` + consumer directive through real `_build_turn_context`) ✓; AC6 (non-goals documented, not built) ✓.

### Delivery Findings Capture
See `### Dev (implementation)` under `## Delivery Findings` above (pre-existing 82-2 governance gap fixed; pre-existing Barsoom content-validator failures noted).

**Handoff:** To Reviewer (Colonel Potter) for code review.

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 LOW notes (hoist deferred imports; 82-2 classification incidental) + GREEN mechanical gate | confirmed 0, dismissed 2 (with rationale), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [EDGE]) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [SILENT]) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [TYPE]) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [SEC]) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — domain covered by Reviewer (see [RULE] / Rule Compliance) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents`, domains covered directly by Reviewer)
**Total findings:** 1 MEDIUM (non-blocking) + 3 LOW (non-blocking) confirmed; 2 preflight LOW notes dismissed with rationale; 0 Critical/High; 0 deferred

### Preflight finding decisions
- **Hoist the two deferred imports in `websocket_session_handler.py` to module level** → **DISMISSED.** The surrounding block already uses deferred `# noqa: PLC0415` imports as local convention (`tick_tropes` at :1200, `draw_engaged_seed` at :1228 — same `if`/peer block). Matching that pattern is *more* consistent than hoisting two of N sibling imports; no behavior impact.
- **The 82-2 `narrator_verbosity`/`narrator_vocabulary` classification is incidental to this story** → **DISMISSED as a concern (confirmed intentional).** Dev logged it as a deviation; the 61-5 governance gate was already RED on develop and would block this PR's suite. A 2-line correct categorization in a file already touched is the right call. See deviation audit.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player action → `_execute_narration_turn` (handler) → post-`record_interaction`, `apply_lull_escalation(snapshot, pack, tracker=sd.tension_tracker, thresholds=pack.drama_thresholds or DramaThresholds(), session_id=seed_session_id, now_turn=interaction)` (handler:1254, peer to `tick_seeds`, NOT nested in the dispatch `if` — verified at indent 20) → on a lull, fires a seed and writes `snapshot.pending_escalation_directive` → NEXT turn `_build_turn_context` (session_helpers:1217) reads it, overrides `pacing_hint.escalation_beat` via `dataclasses.replace`, clears it (consume-once) → reaches the narrator's `## Escalation Beat`. Both ends behaviorally tested through real code (`test_lull_escalation_turn_wiring.py`). Safe: single producer/single consumer on a persisted snapshot field under the per-session row lock (no race); deterministic, no user-controlled input in the hash.

**Observations (12; all 8 specialist domains covered directly since subagents are disabled):**
1. `[VERIFIED]` Producer call site is reachable production code at the correct seam — `websocket_session_handler.py:1254`, indent 20, peer to the 22-5 `if (_dispatch_package…)` block and the `tick_seeds`/`tick_tropes` ticks; runs every turn at the seam, not gated behind the dispatch `if`. Evidence: `awk` indent dump shows lull block at 20, dispatch body at 24. Wired end-to-end (CLAUDE.md "Verify Wiring").
2. `[VERIFIED]` Consumer consume-once override — `session_helpers.py:1217-1221`: reads `snapshot.pending_escalation_directive`, `dataclasses.replace(pacing_hint, escalation_beat=…)` (PacingHint is `frozen=True` — replace is correct), then sets the field to `None`. Mirrors the established `next_turn_directives` populate-then-consume discipline. Applied regardless of current `boring_streak` (correct: the directive outlives the streak the fire reset).
3. `[VERIFIED]` Persistence/resume-safety — `session.py:835-846`: `pending_escalation_directive` + `last_lull_fire_turn` are declared `GameSnapshot` fields (model is `extra:ignore`, so declaration is required — TEA's finding honored), so cooldown + pending directive survive save/load and a resume re-fires identically.
4. `[VERIFIED]` Determinism — `lull_escalation.py:_select_seed_id` hashes `session_id|turn|sorted(ids)` via SHA-256, `% len`. No `random`/wallclock; `sorted()` makes selection order-independent so a save/load reorder of `active_seeds` re-selects the same seed. Modulo bias over a 256-bit digest is negligible for tiny candidate sets and irrelevant to the determinism contract.
5. `[SILENT][MEDIUM]` (non-blocking) Silent fallback in `_narrative_hint_for` (`lull_escalation.py:73`): returns `""` when the selected seed id is absent from `pack.seed_tropes`. Normally impossible (actives are drawn from the deck), but a **resumed save whose active seed predates a pack edit** would silently fire with an empty directive — `last_lull_fire_turn` armed, `SPAN_LULL_ESCALATION fired=True`, yet the consumer skips injection (`if _lull_directive:` treats `""` as falsy). Per CLAUDE.md "No Silent Fallbacks" this masks a content/config drift. Mitigations already present: the OTEL span records the fire with `selected_seed_id`, so it is *not* invisible to the GM panel. Non-blocking for v1; recorded as a Delivery Finding (consider emitting a watcher warning or skipping a hint-less seed).
6. `[EDGE][LOW]` (non-blocking) An authored seed with empty `narrative_hint` (the `SeedTrope.narrative_hint` default is `""`) hits the same path as #5 — fires, arms cooldown, but injects nothing. Content-quality dependent; tied to #5's mitigation.
7. `[TYPE][LOW]` (non-blocking) `LullEscalationResult.reason: str` is stringly-typed; a `Literal["fired","cooldown","none_available","not_triggered"]` would make the four-value contract type-enforced. Minor; the tests pin the literals and the span extractor reads them verbatim. Acceptable for v1.
8. `[TEST][VERIFIED]` Test quality is sound — 0 vacuous assertions (grep clean), 0 `skip`/`xfail`, strong assertion density (29/9, 28/9, 9/3), specific-value asserts (reason/seed_id/directive/span attrs), and the AC5 wiring tests drive the REAL `_execute_narration_turn` and REAL `_build_turn_context` (not source-grep) — compliant with "No Source-Text Wiring Tests."
9. `[DOC][VERIFIED]` Comments and docstrings are accurate and proportionate (module docstring, per-function docstrings, the `not_triggered`/`""`-not-`None` conventions documented inline). No stale or misleading comments introduced; the session.py + handler comments correctly cite ADR-024/025/128 and the seam ordering.
10. `[SEC][VERIFIED]` No security surface — pure in-memory selector. No user input reaches the hash (session_id + integer turn + internal seed ids), no auth/tenant/secret/deserialization/SQL/path/injection vectors. `session_id` is a non-secret reproducibility key (same use as the existing seed_deck). Nothing to leak.
11. `[SIMPLE][LOW]` (non-blocking, dismissed) Deferred imports (`# noqa: PLC0415`) in the handler and `import dataclasses` in `_build_turn_context` could be hoisted, but they match the immediate local convention (sibling deferred imports in the same handler block). Hoisting two of N siblings would be *less* consistent. No change required.
12. `[RULE][VERIFIED]` Python lang-review checklist pass — see `### Rule Compliance`.

### Rule Compliance (python lang-review checklist)
- **#1 Silent exception swallowing:** No bare `except`, no `except: pass`. One silent *value* fallback (`_narrative_hint_for → ""`) flagged as `[SILENT][MEDIUM]` #5 — non-blocking, telemetered.
- **#2 Mutable default arguments:** None. No function in the diff uses a mutable default; `getattr(pack, "seed_tropes", []) or []` builds a fresh list.
- **#3 Type annotations at boundaries:** All public functions fully annotated (`apply_lull_escalation`, `_select_seed_id`, `_narrative_hint_for`, `lull_escalation_span`); `LullEscalationResult` fields typed. `Any` used only for the duck-typed `pack` (same convention as `tick_seeds`/`draw_engaged_seed`).
- **#4 Logging/observability:** Subsystem decisions emit OTEL (`SPAN_LULL_ESCALATION` on every engaged run, `SPAN_SEED_FIRED` on fire) — satisfies the CLAUDE.md OTEL Observability Principle (the lie detector for this exact "engine pushed vs improvised" risk).
- **#6 Test quality:** Pass (observation #8).
- **#10 Import hygiene:** Deferred imports follow local convention; no star imports added (`pacing.py` exports via the existing `from .pacing import *` with public names); no circular imports (lull_escalation imports downward into game/telemetry only).
- **#5/#7/#8/#11/#12 (paths/resources/deserialization/input-validation/deps):** N/A — pure in-memory selector, no I/O, no new dependencies.

### Devil's Advocate
Assume this is broken. **Attack 1 — double-fire in one turn.** If `apply_lull_escalation` were somehow called twice in the same turn, would it fire twice and pile up Bangs against the ADR-128 governor? No: the first call sets `last_lull_fire_turn = now_turn`; the second sees `now_turn - last = 0 < FIRE_COOLDOWN_TURNS` → `cooldown`. Idempotent within a turn. **Attack 2 — directive leaks to multiple turns.** Could the directive injected on turn N+1 also bleed into N+2, double-dipping the narrator? No: the consumer clears the field the moment it reads a truthy value. The only leak path is the empty-string fire (#5/#6) where the field stays `""` (falsy) — but that injects *nothing*, so there is nothing to leak; worst case is a wasted cooldown. **Attack 3 — resume corruption.** A malicious/old save sets `last_lull_fire_turn` to a huge future value; then `now_turn - last` is negative, `< FIRE_COOLDOWN_TURNS` is true → permanent cooldown (engine never pushes). That is a degraded-but-safe failure (the pre-77-7 status quo of a passive engine), not a crash or corruption; and saves are trusted local state under the per-session lock. **Attack 4 — empty/huge candidate set.** Empty `active_seeds` with empty deck → `none_available` (span emitted, no crash). A pathologically huge `active_seeds` only enlarges the sorted-join string fed to SHA-256 — O(n log n) sort, bounded by the seed-deck cardinality which is small by construction (`_BOUNDED_BY_CONSTRUCTION`). **Attack 5 — confused author.** A content author ships a seed with no `narrative_hint`; the engine "fires" but the player sees no new complication. This is the genuine soft spot (#5/#6) — surfaced as a Delivery Finding so a future story can fail-louder. None of these rise to Critical/High; the worst outcome is the engine declining to push (status-quo-safe), never corrupting state or crashing a turn.

**Pattern observed:** Reuse-first wiring — the selector composes existing primitives (`pacing_hint`, `draw_engaged_seed`, `SPAN_SEED_FIRED`, `FIRE_COOLDOWN_TURNS`) rather than reinventing, and the consumer reuses the `next_turn_directives` consume-once idiom. Exactly the "Wire Up What Exists" doctrine.

**Error handling:** Graceful, fail-safe-toward-passive on every off-nominal path (cooldown / none_available / not_triggered / missing-hint) — each either no-ops or emits a telemetered non-fire. The one residual gap (silent empty-hint) is non-blocking and recorded.

**Handoff:** To SM (Hawkeye) for finish-story.