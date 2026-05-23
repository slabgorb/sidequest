---
story_id: "53-4"
jira_key: ""
epic: "53"
workflow: "tdd"
---
# Story 53-4: OTEL spans: rig_pool delta + rig_crash_event per ADR-031

## Story Details
- **ID:** 53-4
- **Jira Key:** (none — SideQuest never uses Jira)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-23T10:51:51Z (re-entered after Reviewer REJECT)

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-23 | 2026-05-23T08:44:05Z | 8h 44m |
| red | 2026-05-23T08:44:05Z | 2026-05-23T09:02:29Z | 18m 24s |
| green | 2026-05-23T09:02:29Z | 2026-05-23T09:09:59Z | 7m 30s |
| spec-check | 2026-05-23T09:09:59Z | 2026-05-23T09:12:39Z | 2m 40s |
| verify | 2026-05-23T09:12:39Z | 2026-05-23T09:18:44Z | 6m 5s |
| review | 2026-05-23T09:18:44Z | 2026-05-23T09:29:57Z | 11m 13s |
| spec-reconcile | 2026-05-23T09:29:57Z | 2026-05-23T09:30:00Z (rolled back, Reviewer REJECT not honored by gate) | 0m 3s |
| green | 2026-05-23T09:30:00Z | 2026-05-23T10:40:36Z | 1h 10m |
| spec-check | 2026-05-23T10:40:36Z | 2026-05-23T10:42:01Z | 1m 25s |
| verify | 2026-05-23T10:42:01Z | 2026-05-23T10:43:31Z | 1m 30s |
| review | 2026-05-23T10:43:31Z | 2026-05-23T10:50:31Z | 7m |
| spec-reconcile | 2026-05-23T10:50:31Z | 2026-05-23T10:51:51Z | 1m 20s |
| finish | 2026-05-23T10:51:51Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

**Initial Assessment (setup phase):**
- Code already fully implemented: RigComposurePool emits rig_pool.created, rig_pool.delta, rig_pool.zero_crossing spans on construct/delta/zero-crossing (story 53-1)
- Crash handler emits rig_pool.crash_event span when Composure→0 fires consequences (story 53-3)
- Span constants defined in sidequest/telemetry/spans/rig.py, registered in FLAT_ONLY_SPANS

### TEA (test design)
- **Gap** (non-blocking): The four `rig_pool.*` spans are in `FLAT_ONLY_SPANS` and so only reach the GM dashboard as generic `agent_span_close` events. The audio / chargen / cavern_room / NPC / lore precedents all use `SPAN_ROUTES` + `state_transition` so their Subsystems-tab panels render typed events. Affects `sidequest-server/sidequest/telemetry/spans/rig.py` (move the four constants from `FLAT_ONLY_SPANS` into `SPAN_ROUTES` with `event_type="state_transition"`, `component="rig"`, and `extract` lambdas). *Found by TEA during test design.*
- **Gap** (non-blocking): `rig_pool.crash_event` span carries only the inputs (`character_id`, `chassis_id`, `location`, `attacker`) — none of the three consequence outcomes (Edge delta, post-crash Edge, injury status, dismount status) are on the span. ADR-031 Layer-2 spec ("structured spans … with fields capturing what was decided") requires the outcomes. Affects `sidequest-server/sidequest/game/rig_crash.py` (extend the `Span.open(SPAN_RIG_POOL_CRASH_EVENT, attrs={...})` block to include `edge_delta`, `edge_after`, `injury_status_text`, `dismounted_status_text`). *Found by TEA during test design.*
- **Improvement** (non-blocking): The 53-4 sm-setup did not create `sprint/context/context-story-53-4.md`; TEA had to invoke `/pf-context create story 53-4` mid-RED to satisfy the context gate. Recent stories (60-1 through 60-4) had a story context. Affects sm-setup workflow — the gate recovery_config exists (`create_context, max_attempts: 1, type: story`) but is not auto-triggered. Worth confirming whether sm-setup should pre-create the file rather than relying on TEA to invoke pf-context. *Found by TEA during test design.*
- **Question** (non-blocking): The `realized vs. requested` semantics of `edge_delta` on the crash_event span is a TEA call that Dev may push back on (see Design Deviations §2). If Dev or Reviewer disagrees with "edge_delta = realized delta after EdgePool flooring," flag here before flipping the test — it's a design call worth a brief alignment, not a unilateral Dev decision. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): the testing-runner subagent overwrote `.session/53-4-session.md` with its own verification summary during the GREEN run. This is the same failure mode recorded in memory `[[testing_runner_overwrites_session]]` (originally observed on story 49-2). Session was reconstructed from conversation context. Affects `pennyfarthing-dist/agents/testing-runner.md` (or equivalent) — the runner should report to its caller, never write to `.session/`. Worth a sweep to confirm whether the testing-runner agent's tool permissions or instructions allow Write at all. *Found by Dev during implementation.*
- **Question** (non-blocking): Confirmed TEA's `edge_delta = realized` pin is sound — implemented as `edge_delta = edge_after - edge_before` in `handle_rig_crash`, no pushback. The EdgePool floor case (driver at 0 Edge) is now covered cleanly with `edge_delta == 0` and `edge_after == 0`. No alignment needed. *Found by Dev during implementation.*
- No other upstream findings during implementation.

### TEA (test verification)
- **Improvement** (non-blocking): TEA's RED phase and Dev's GREEN run both relied on `uv run pytest` alone, neither ran `uv run pyright` against the new test files. The verify-phase quality-pass gate caught a 5-error pyright failure in `tests/telemetry/test_rig_pool_routes.py` (`_FakeSpan.attributes` annotation didn't satisfy the `_SpanLike` Protocol's mutable invariance constraint). The fix was trivial (one annotation widening, commit `065f609`), but the pattern is a process gap: phase-exit gates should include pyright for any new .py file. Affects TEA/Dev phase-exit checklists — worth wiring `pf check` (or equivalent) to run pyright on changed files at red/green exit, not just verify. *Found by TEA during test verification.*
- Second-pass re-verify: no upstream findings. Rework was tightly additive (mirrored established patterns the first-pass simplify triad already cleared), quality-pass gate clean (ruff / pyright / 85 tests passing). Simplify triad explicitly skipped with rationale in the verify assessment.

### Reviewer (code review)
- **Gap** (blocking): AC1 sub-clause "repeated damage on wrecked rig publishes delta with new_current=0" — premise check exists but doesn't assert field values. Affects `tests/integration/test_rig_pool_wiring.py:240` (3 added assertions). *Found by Reviewer during code review (F1).*
- **Gap** (blocking): AC2 sub-clause "re-cross after heal publishes second crossing event" — entirely untested. Affects `tests/integration/test_rig_pool_wiring.py` (new ~15-line test). The most likely regression surface for edge-triggered semantics. *Found by Reviewer during code review (F2).*
- **Gap** (blocking): AC3 negative case "zero_crossing without crash_event independence" — entirely untested. Affects `tests/integration/test_rig_pool_wiring.py` (new ~12-line test). The AC explicitly calls these "independent gates"; nothing pins the independence. *Found by Reviewer during code review (F3).*
- **Gap** (blocking): Stale module docstring at `sidequest/telemetry/spans/rig.py:3` still says "three flat-only emitters"; post-migration the file has 5 flat-only + 4 routed. Affects `sidequest-server/sidequest/telemetry/spans/rig.py:3` (one preamble rewrite). *Found by Reviewer during code review (F4).*
- **Improvement** (non-blocking, deferred): AC4 `model_construct(...)` contract could be pinned by a test (~5 lines) in addition to Architect's deviation-log pin. Production impact: negligible. Defer to follow-up unless a pydantic upgrade lands. *Found by Reviewer during code review (F5).*
- **Conflict** (non-blocking, process bug): The approval gate's reviewer-verdict check did not act on the explicit "Verdict: REJECTED" token. `pf handoff complete-phase 53-4 tdd review spec-reconcile approval` advanced the phase to spec-reconcile despite the REJECT, ignoring the gate's `recovery_config: {reviewer-verdict: {action: rework, target_phase: green}}`. Session was manually rolled back to green so Dev can pick up the F1–F4 fix pass cleanly. Affects `pennyfarthing-dist/gates/approval.md` (or the `pf` runtime that parses the gate file): the verdict-parsing logic appears to only check that ANY verdict-shaped string exists, not that the verdict is APPROVED. Worth wiring `reviewer-verdict: pass iff verdict == "APPROVED"` and triggering the rework recovery action on any non-APPROVED verdict. *Found by Reviewer during code review.*
- No other upstream findings during code review.
- Second-pass review (post-rework): **APPROVED**. F1–F4 all verified closed. Two new non-blocking docstring-accuracy nits surfaced (NF1: rig.py:34 inline comment "these three" vs four routed entries; NF2: F2 test docstring says "second crash" should say "second zero_crossing event"). Both are trivial polish, NOT gating merge. Recommend Dev land them as a follow-up commit on the same branch before merge, OR address in a follow-up cleanup story. *Found by Reviewer during second code review pass.*

## Sm Assessment

**Scope:** OTEL telemetry stitch for the Road Warrior rig subsystem. Stories 53-1/2/3 (pool, materializer, crash handler) merged. This is the watcher-visibility closer for the epic per ADR-031.

**Sm-setup's "already implemented" claim — treat as a lead, not a conclusion.** Source-presence of `rig_pool.delta` / `rig_pool.crash_event` constants and emit calls is not the same as the spans actually reaching the watcher / dashboard end-to-end. Per project doctrine: log-absence ≠ deadness, but presence-in-source ≠ wiring either. RED must prove the spans fire AND are reachable via the production telemetry path, not just that emit functions are called.

**ADR-031 is the contract.** Read it before authoring tests. The span schema (attributes, names, FLAT_ONLY registration) is dictated there. If the existing implementation drifts from ADR-031 (wrong attribute names, missing required fields), file a Delivery Finding and TEA writes the failing test against the spec, not against current code shape.

**Required RED coverage (TEA's call, not mine):**
- `rig_pool.delta` fires on damage and repair with correct delta sign + before/after values
- `rig_pool.crash_event` fires when Composure crosses to 0, capturing dismount + injury tag + Edge hit (the three consequences of 53-3)
- At least one **wiring/integration test** that drives the spans through a production code path (not a unit-test stub) — see CLAUDE.md "Every Test Suite Needs a Wiring Test"
- Watcher event surfaces — confirm spans land in the dispatch path that the GM panel reads (ADR-090 dashboard restoration)

**Hazards / land mines:**
- "OTEL two streams" memory: don't conflate ADR-058 Claude-subprocess HTTP/JSON (playtest_otlp/dashboard) with the ADR-103 server-tracer→gRPC→Jaeger path. Rig spans are subsystem game-watcher spans, not narrator turn spans — ADR-031 layer.
- No content-coupled tests. Fixtures for rig pool / vessel item, not live `genre_packs/road_warrior` loads.
- No silent fallbacks. If the emit path can fail silently (missing tracer, no watcher subscribed), that itself is a failure mode worth a test.
- 2 points — keep scope to the four-ish span types named in the title. Don't promote into a broader telemetry audit.

**Branch:** feat/53-4-rig-otel-spans on sidequest-server (base develop).
**Next:** TEA — RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Subsystem telemetry wiring + attribute-contract expansion; per CLAUDE.md OTEL Observability Principle, every backend fix that touches a subsystem MUST add OTEL watcher events, and per "Every Test Suite Needs a Wiring Test" the integration path needs at least one end-to-end test.

**Test Files:**
- `sidequest-server/tests/telemetry/test_rig_pool_routes.py` — NEW. 9 unit tests on the SpanRoute extract lambdas for the four rig_pool spans + the `{field, op}` canonical envelope + the new crash_event consequence attrs (edge_delta, edge_after, injury_status_text, dismounted_status_text) + None-coercion handling on optional inputs.
- `sidequest-server/tests/integration/test_rig_pool_wiring.py` — NEW. 6 end-to-end async tests that install a real `TracerProvider` + `WatcherSpanProcessor`, subscribe a fake sock to `watcher_hub`, drive production rig flow (`RigComposurePool(...)`, `apply_delta`, `handle_rig_crash`), and assert the typed `state_transition` events with `component="rig"` arrive in order with the right `fields`. Mirrors `tests/integration/test_audio_wiring.py`.
- `sidequest-server/tests/game/test_rig_composure_pool.py` — EDITED 1 test (`test_rig_pool_spans_are_flat_only` → `test_rig_pool_spans_are_routed_state_transition`); inverted FLAT_ONLY assertions to SPAN_ROUTES + state_transition + component="rig".
- `sidequest-server/tests/game/test_rig_crash_handler.py` — EDITED 1 test (same flip) + ADDED 2 tests (`test_handle_rig_crash_span_captures_consequence_outcomes`, `test_handle_rig_crash_span_consequences_floor_edge_at_zero`).

**Tests Written:** 17 new tests + 2 edited assertions covering AC1–AC6.
**Status:** RED (19 failing for the right reasons — articulating the SPAN_ROUTES migration + consequence-attr expansion. 64 unaffected existing tests still pass. routing-completeness intact: production state is consistent FLAT_ONLY, no overlap.)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| CLAUDE.md "Every Test Suite Needs a Wiring Test" | `tests/integration/test_rig_pool_wiring.py::test_rig_crash_full_sequence_publishes_ordered_events` (canonical end-to-end), 5 supporting integration tests | failing |
| CLAUDE.md "No Source-Text Wiring Tests" | All wiring tests drive real production code paths + assert against the watcher_hub fan-out; no `read_text()` or regex against source | n/a (avoided) |
| CLAUDE.md "Verify Wiring, Not Just Existence" | Integration tests subscribe a real `_Sock` and assert typed events arrive — not just span constants exist | failing |
| CLAUDE.md OTEL Observability Principle ("every backend fix that touches a subsystem MUST add OTEL watcher events") | Route-extract tests + integration tests both | failing |
| sidequest-server/CLAUDE.md "No Silent Fallbacks" | `test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero` has premise check (asserts `delta` event DID publish before asserting `zero_crossing` did NOT) | failing |
| Project memory `[[one_mechanism_per_problem]]` | Design Deviation pins SpanRoute as the single mechanism; no parallel direct watcher_publish | failing (drives consolidation) |
| Project memory `[[no_content_coupled_tests]]` | All tests use synthetic `_mounted_core(...)` fixtures, not `genre_packs/road_warrior` loads | n/a (avoided) |
| Test self-check (vacuous assertions) | Pre-handoff sweep caught the originally-vacuous "no re-fire" test; strengthened with a premise check | resolved |

**Rules checked:** 8 of 8 applicable rules have coverage or are explicitly avoided.
**Self-check:** 1 vacuous test caught and fixed before handoff (`test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero`).

**Handoff:** To Dev (Major Charles Emerson Winchester III) for GREEN — implement the SpanRoute migration in `sidequest-server/sidequest/telemetry/spans/rig.py` (move four constants from `FLAT_ONLY_SPANS` to `SPAN_ROUTES` with `state_transition` + `component="rig"` + `{field, op, ...}` extracts) and extend the crash_event emit at `sidequest-server/sidequest/game/rig_crash.py` to include the four consequence attrs. Read the Design Deviations section before starting — the SpanRoute-vs-direct-publish choice and the realized-delta semantics are TEA-pinned but defensible if Dev finds structural reasons to revisit.

## Dev Assessment

**Status:** GREEN (7214 passed / 0 failed / 400 skipped across full sidequest-server suite; 19 RED tests flipped; both game test files at 100%; routing-completeness invariant intact).

**Production Changes:**

1. **`sidequest-server/sidequest/telemetry/spans/rig.py`** — SpanRoute migration.
   The four `rig_pool.*` span constants (`created`, `delta`, `zero_crossing`, `crash_event`) moved from `FLAT_ONLY_SPANS.update({...})` to individual `SPAN_ROUTES[...] = SpanRoute(event_type="state_transition", component="rig", extract=lambda ...)` registrations. Each extract returns the canonical `{field, op, …}` envelope per the audio.py / chargen.py / cavern_room.py precedent — `field="rig_pool"`, `op` discriminates the four lifecycle stages, remaining keys are the original span attrs surfaced verbatim. The five legacy rig spans (`rig.bond_event`, `rig.voice_register_change`, `rig.confrontation_outcome`, `room.entry_skipped`, `room.entry_evaluated`) stay in `FLAT_ONLY_SPANS` — out of scope per TEA's "keep to four span types" guardrail.

2. **`sidequest-server/sidequest/game/rig_crash.py`** — crash_event consequence attrs.
   `handle_rig_crash` now captures `edge_before = core.edge.current` before the `apply_edge_delta(DRIVER_EDGE_HIT)` call, then `edge_after = core.edge.current` and `edge_delta = edge_after - edge_before`. The `Span.open(SPAN_RIG_POOL_CRASH_EVENT, attrs={...})` block gains four new attrs: `edge_delta` (realized, not requested), `edge_after`, `injury_status_text` (`INJURY_STATUS_TEXT` constant), `dismounted_status_text` (`DISMOUNTED_STATUS_TEXT` constant). TEA's `..._floor_edge_at_zero` test confirms a 0-Edge driver crashing emits `edge_delta=0` and `edge_after=0` — the dashboard sees the Edge pool floored rather than printing a phantom `-1`.

**TEA Design Deviations — all confirmed:**
- **SpanRoute (not direct watcher_publish):** Implemented as TEA pinned. No structural blockers; the audio precedent ported cleanly.
- **Realized-delta semantics on `edge_delta`:** Implemented as TEA pinned. Cleaner than carrying a requested constant — the dashboard renders the post-flooring outcome, which is what Sebastien-the-mechanics-player needs for the lie detector. No alignment dispute.
- **Premise check on the "no re-fire" wiring test:** GREEN confirms the strengthening worked — the `delta` event publishes (premise satisfied) AND `zero_crossing` does not republish (the property under test).

**Approach notes (no code comments warranted, captured here for Reviewer):**
- Extract lambdas use `(span.attributes or {}).get(key, default)` defensive pattern — matches audio.py exactly. The `or {}` covers the OTEL ReadableSpan invariant where `.attributes` can be `None` for unattributed spans; the `.get(key, default)` covers the case where an attr was dropped by OTEL coercion (e.g., a `None` value silently elided). Production code paths always provide all attrs; the defaults exist for translator robustness, not as silent fallbacks.
- `edge_delta` is computed at the emit site rather than threaded from `apply_edge_delta` because the latter returns the new value, not the delta — extracting before/after locally is two lines and avoids a public-API change on `CreatureCore.apply_edge_delta` that isn't in 53-4 scope.
- No changes needed to `sidequest/game/rig_composure_pool.py` — its three existing `Span.open(...)` blocks already emit the right attrs (`character_id, chassis_id, current/max` for created; `character_id, chassis_id, delta, old_current, new_current` for delta; `character_id, chassis_id, old_current, new_current` for zero_crossing). The migration was purely additive at the registration layer.

**Verification:**
- All 19 RED tests now pass.
- `tests/game/test_rig_composure_pool.py`: 36/0 (was 35/1).
- `tests/game/test_rig_crash_handler.py`: 30/0 (was 27/3).
- `tests/telemetry/test_routing_completeness.py`: 2/2 — no SPAN_ROUTES ∩ FLAT_ONLY overlap, no unrouted spans, all event_types in the known set (state_transition is whitelisted).
- Full suite: 7214 passed / 0 failed / 400 skipped — no unintended side effects from the global `SPAN_ROUTES` dict mutation.

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review. Two files changed, ~78 insertions / ~12 deletions. No new ADR, no API changes outside the rig telemetry layer.

## TEA Assessment (verify phase, second pass)

**Phase:** finish (re-entry after Dev rework)
**Status:** GREEN confirmed.

### Rework scope (commit `e639247`)

Two files touched, narrow additive surface:
- `sidequest/telemetry/spans/rig.py` — module docstring rewrite only (F4). No logic change.
- `tests/integration/test_rig_pool_wiring.py` — 3 added field-value assertions inside an existing test (F1) + 2 new tests (F2 re-cross-after-heal, F3 zero_crossing-without-crash-event).

### Simplify (skipped with rationale)

The first-pass simplify triad (reuse, quality, efficiency) ran clean on all six files in the original diff. The rework only modifies two of those files and the new code mirrors patterns the triad already cleared:
- F2/F3 tests use the same `_setup(monkeypatch, label)` / `_mounted_core(...)` / `await asyncio.sleep(0.05)` / `_rig_state_transitions(captured)` helpers that the original 6 integration tests use.
- F1 assertions inline `delta_fields["delta"] == -3` etc. — identical assertion style to the existing `len(typed) == 1; fields["x"] == y` shape.
- F4 docstring expands an existing docstring without changing the file's interface or structure.

Per the verify workflow's pragmatic guidance, re-spawning the simplify triad on rework that mirrors established and already-vetted patterns would produce a third clean report with no new signal. Skipping the triad and going straight to quality-pass.

### Quality-Pass Gate

| Check | Result |
|-------|--------|
| `uv run ruff check` on the 2 changed files | PASS — "All checks passed!" |
| `uv run pyright` on the 2 changed files | PASS — 0 errors, 0 warnings, 0 informations |
| `uv run pytest` on the 5 touched test files | PASS — 85 passed / 0 failed (was 83 in first verify pass; +2 from F2 + F3 tests) |
| Routing-completeness invariant | PASS — `test_routing_completeness.py` still 2/2 |

### Decision

Proceed to re-review. The rework closes the four Reviewer findings cleanly, no regressions, no new defects.

**Handoff:** To Reviewer (Colonel Potter) for re-review — same diff lens as the first pass, with attention to whether F1–F4 are actually closed by `e639247`.

## TEA Assessment (verify phase)

**Phase:** finish
**Status:** GREEN confirmed (83/0 across the five touched test files; full suite previously 7214/0 in Dev's verification)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (`sidequest/game/rig_crash.py`, `sidequest/telemetry/spans/rig.py`, `tests/game/test_rig_composure_pool.py`, `tests/game/test_rig_crash_handler.py`, `tests/integration/test_rig_pool_wiring.py`, `tests/telemetry/test_rig_pool_routes.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | The four SpanRoute extract lambdas match audio.py precedent exactly. `_mounted_core` duplication in integration vs game test files is intentional per docstring ("integration tests should not cross-import from sibling test suites"). Per-route extract tests in `test_rig_pool_routes.py` are healthy explicit coverage. |
| simplify-quality | clean | All comments are load-bearing (explain WHY non-obvious). Test names meaningful. Constant imports correct. Pattern adherence to audio.py / chargen.py / cavern_room.py is exact. No dead imports. |
| simplify-efficiency | 1 finding (low confidence) | `_mounted_core` is identical across `test_rig_crash_handler.py` and `test_rig_pool_wiring.py`. Agent flagged at low confidence, noting the duplication matches the project-wide integration-vs-unit isolation pattern (audio, inventory, npc, lore, state_patch, disposition, combat all do it). |

**Applied:** 0 high-confidence fixes (none surfaced)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 1 low-confidence observation (`_mounted_core` duplication) — explicitly NOT applied per project convention. Cross-suite test fixture isolation is established practice across 8 integration wiring test files; extracting a shared helper would diverge from precedent for marginal LOC savings. If the convention itself needs revisiting, that is a project-wide refactor, not a 53-4 deliverable.
**Reverted:** 0

**Overall:** simplify: clean (1 low-confidence note, not actionable in scope)

### Quality-Pass Gate

| Check | Result | Detail |
|-------|--------|--------|
| `pf check` (orchestrator root) | PASS | Lint passed; tests/typecheck skipped (no orchestrator-side config) |
| `uv run ruff check` on 6 changed files | PASS | "All checks passed!" |
| `uv run pyright` on 4 changed .py files | INITIALLY 5 ERRORS → FIXED → PASS | `_FakeSpan.attributes` was annotated `dict[str, Any]`, mismatching the `_SpanLike` protocol's `dict[str, Any] | None` (invariant because mutable). Widened the annotation; commit `065f609` covers the fix. Tests still pass after the fix (test fixtures always pass a concrete dict). |
| `uv run pytest` on touched files | PASS | 83/0 across `test_rig_pool_routes.py`, `test_rig_pool_wiring.py`, `test_rig_composure_pool.py`, `test_rig_crash_handler.py`, `test_routing_completeness.py` |

### Verify findings

- The pyright surprise is worth a flag: TEA's RED phase didn't run pyright before handing to Dev; Dev's GREEN run did pytest only (no type-check). The verify gate caught it. Worth noting in process: TEA/Dev should both run pyright on new test files before exit, not just at verify. Captured as a finding below.

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Reviewer Assessment (second pass, post-rework)

**Verdict: APPROVED.** Rework commit `e639247` cleanly closes all four blocking findings from the first review (F1, F2, F3, F4). Two minor docstring-accuracy nits surface in this pass — non-blocking polish, not gating merge.

**Specialist subagent coverage in this assessment** (enabled subagents had findings or clean status; disabled subagents got an inline manual check):

[TEST] active — test-analyzer scanned the rework diff and confirmed F1, F2, F3, F4 all closed with correct semantics. F1 field-value assertions match AC1 contract. F2 correctly drives 1→0→1→0 with `captured.clear()` between phases. F3 uses `apply_delta(-2)` alone with both positive and negative assertions. No new gaps; no new vacuous assertions; no race conditions in `captured.clear()` sequencing.

[DOC] active — comment-analyzer found 2 doc-accuracy nits (NF1, NF2 below) and 1 low-confidence label concern (NF3 below). All are docstring-only; none block merge.

[RULE] active — rule-checker re-ran 20 rules / 68 instances against the rework diff. Zero violations. The new field-value assertions in F1 satisfy Rule #6 (test quality, no vacuous assertions). The F2/F3 new tests follow the established `_setup`/`_mounted_core`/`asyncio.sleep(0.05)` pattern with no async pitfalls (Rule #9). No new imports / no circular risk (Rule #10).

[EDGE] no subagent ran (disabled via setting). Manual edge-case audit: the F2 test specifically guards against the most likely future regression (`has_crossed_zero` flag becoming permanent), and F3 guards against accidental coupling of `apply_delta` to `handle_rig_crash`. The rework adds coverage exactly where the first review identified gaps. No remaining [EDGE] concerns.

[SILENT] no subagent ran (disabled). Manual audit: no try/except, no `contextlib.suppress`, no bare except in the rework diff. The `captured.clear()` sequencing in F2 is correctly ordered (sleep before clear ensures prior events drain; clear before action; sleep after action before assertion) — no silent timing failure. No [SILENT] concerns.

[TYPE] no subagent ran (disabled). pyright clean on the rework diff. No new type contracts introduced; F2/F3 mirror existing test type patterns exactly. No [TYPE] concerns.

[SEC] no subagent ran (disabled). Manual audit: rework changes are docstring + test additions only. Zero attack surface introduced. No [SEC] concerns.

[SIMPLE] no subagent ran (disabled). TEA's re-verify skipped the simplify triad explicitly with rationale (the rework mirrors patterns the first-pass triad already cleared). The two new F2/F3 tests follow the integration-test convention without adding new helpers or abstractions. No [SIMPLE] concerns.

## Subagent Results

| # | Subagent | Received | Decision | Notes |
|---|----------|----------|----------|-------|
| 1 | reviewer-preflight | Yes | N/A (clean) | 85/0 tests, ruff clean, pyright clean. 87 warnings — pre-existing `register` BaseModel shadow debt, unrelated to rig. |
| 2 | reviewer-edge-hunter | Skipped | disabled | `workflow.reviewer_subagents.edge_hunter: false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | Disabled via setting |
| 4 | reviewer-test-analyzer | Yes | All 4 prior findings (F1, F2, F3, F4) verified closed | No new findings |
| 5 | reviewer-comment-analyzer | Yes | 2 confirmed (NF1, NF2 below) / 1 dismissed (NF3) | Non-blocking doc-accuracy nits |
| 6 | reviewer-type-design | Skipped | disabled | Disabled via setting |
| 7 | reviewer-security | Skipped | disabled | Disabled via setting |
| 8 | reviewer-simplifier | Skipped | disabled | Disabled via setting (TEA re-verify also skipped simplify triad with rationale) |
| 9 | reviewer-rule-checker | Yes | N/A (clean) | 20 rules / 68 instances / 0 violations |

**All received: Yes** (4 enabled subagents returned; 5 disabled per project config and pre-filled as Skipped per agent definition).

### F1–F4 Closure Verification

| First-pass finding | Closed by | Verification |
|--------------------|-----------|--------------|
| F1 — premise check missed field values | `test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero:254-261` | Adds `delta_fields["delta"] == -3`, `["old_current"] == 0`, `["new_current"] == 0`. Catches the AC1 sub-clause that the bare `len(deltas) == 1` premise check could not. |
| F2 — re-cross-after-heal untested | new `test_rig_pool_zero_crossing_re_fires_after_repair_and_re_damage` | Drives 1→0→1→0 with `captured.clear()` between phases; asserts exactly one `zero_crossing` in post-clear window with `old_current=1, new_current=0`. Pins edge-triggered semantics. |
| F3 — zero_crossing/crash_event independence untested | new `test_rig_pool_zero_crossing_independent_of_crash_event` | Calls only `apply_delta(-2)` with no `handle_rig_crash`. Both positive (`len(crossings) == 1`) and negative (`crashes == []`) assertions present. |
| F4 — stale module docstring | `sidequest/telemetry/spans/rig.py:1-21` rewrite | Now enumerates 5 flat-only (`bond_event`, `voice_register_change`, `confrontation_outcome`, `room.entry_skipped`, `room.entry_evaluated`) and 4 routed `state_transition` (`rig_pool.*`) with audio.py/chargen.py/cavern_room.py precedent rationale. Matches code reality. |

### New Findings (non-blocking, recommended polish)

#### NF1 — `sidequest/telemetry/spans/rig.py:34` inline comment count drift *(non-blocking, polish)*

- **Source:** reviewer-comment-analyzer.
- **Issue:** The inline comment block introducing the `rig_pool.*` routes says "RigComposurePool emits these three on construct / delta / zero-crossing" — *technically* accurate (RigComposurePool the *class* emits exactly three; `crash_event` is emitted by `rig_crash.py`), but the comment sits at the top of a section that registers FOUR routes in a row. A reader scanning top-to-bottom counts four SpanRoute registrations against the "these three" reference and pauses.
- **Recommended fix:** Either reword the comment to "RigComposurePool emits these three on construct/delta/zero-crossing; rig_crash.py emits the fourth (crash_event) — all four are routed below" OR move the lead comment to apply to all four routes.
- **Severity:** Trivial (doc clarity, no behavior or test impact).
- **Decision:** **Recommend polish** but **NOT blocking merge**. Dev can address in a follow-up commit on this branch before merge, or land as-is and address in a follow-up cleanup story.

#### NF2 — F2 test docstring conflates "crash" and "zero_crossing event" *(non-blocking, polish)*

- **Source:** reviewer-comment-analyzer.
- **Issue:** `tests/integration/test_rig_pool_wiring.py` in the F2 test docstring (~line 277) reads "a regression that tracks 'has ever crossed' as a one-way flag would silence the second **crash** and break the GM dashboard's repeat-encounter signal." The hazard described would silence the second **zero_crossing event**, not a "crash" — zero_crossing and crash_event are explicitly decoupled (proven by the very next test F3). The word "crash" in this sentence misrepresents the regression hazard.
- **Recommended fix:** Replace "would silence the second crash" with "would silence the second zero_crossing event".
- **Severity:** Trivial (docstring readability, no test logic impact).
- **Decision:** **Recommend polish** but **NOT blocking merge**.

#### NF3 — F3 test "AC3 negative case" label scope *(dismissed — low confidence)*

- **Source:** reviewer-comment-analyzer.
- **Issue:** F3 test docstring labels itself "AC3 negative case" but also exercises an AC2-adjacent positive assertion (`len(crossings) == 1`) as a premise check.
- **Reviewer's view:** The "AC3 negative case" label is correct — AC3 in context-story-53-4.md explicitly includes the negative case "A pool zero-crossing where the crash handler isn't invoked still publishes `rig_pool.zero_crossing` but NOT `rig_pool.crash_event` (these are independent gates)." The premise positive assertion on `crossings` is the anti-vacuous pattern (without it, the test would pass trivially if all wiring were dead). Same pattern TEA applied to the F1 premise check. Label is accurate.
- **Decision:** **DISMISSED.** Low confidence finding; the label is technically correct and the positive premise check is a defensive testing pattern, not a scope leak.

### Rule Compliance

| Rule (lang-review/python.md) | Cluster | Status |
|------------------------------|---------|--------|
| #1 Silent exception swallowing | N/A — no try/except in rework | PASS |
| #2 Mutable default arguments | 6 instances re-checked | PASS |
| #3 Type annotation gaps at boundaries | 8 instances re-checked | PASS |
| #4 Logging coverage and correctness | N/A — no logging | PASS |
| #5 Path handling | N/A — no file I/O | PASS |
| #6 Test quality | 19 test functions, including the 3 new/edited from rework | PASS (no vacuous assertions; F1 field-value additions satisfy the rule's intent specifically) |
| #7 Resource leaks | N/A | PASS |
| #8 Unsafe deserialization | N/A | PASS |
| #9 Async/await pitfalls | 8 instances (incl. F2's `captured.clear()` sequencing) | PASS |
| #10 Import hygiene | 5 files re-checked | PASS |
| #11 Input validation at boundaries | N/A | PASS |
| #12 Dependency hygiene | N/A | PASS |
| #13 Fix-introduced regressions (meta) | 5 rework changes re-scanned | PASS |
| #14 State cleanup ordering | 3 sites (incl. `captured.clear()`) | PASS |
| Additional A (No Silent Fallbacks) | 4 sites | PASS |
| Additional B (No Stubbing) | 5 sites | PASS |
| Additional C (Don't Reinvent) | 2 sites | PASS |
| Additional D (Every Test Suite Needs a Wiring Test) | 1 wiring test file | PASS |
| Additional E (No Source-Text Wiring Tests) | 3 test files | PASS |
| Additional F (OTEL Observability Principle) | 1 subsystem extended | PASS |

Zero rule violations across 20 rules / 68 instances. The two NF findings are documentation-accuracy nits outside the rule-compliance scope.

### Decision

**Verdict: APPROVED.** Rework closes F1–F4 cleanly; NF1 and NF2 are recommended polish (docstring accuracy) that Dev MAY address in a follow-up commit before merge but are not gating. The story's behavior is correct, the test coverage now matches the AC1–AC3 sub-clauses the first review identified as gaps, and AC4 remains pinned via Architect's spec-check Design Deviation.

Proceeding to spec-reconcile (Architect) for the final deviation manifest.

**Handoff:** To Architect (Major Houlihan) for spec-reconcile.

## Reviewer Assessment (first pass — RECORDED, superseded by second-pass APPROVED above)

**Verdict: REJECTED.** Rework required. The implementation is correct and the wiring works, but three story-AC sub-clauses are unimplemented in tests ([TEST] findings F1, F2, F3) and one production docstring is stale ([DOC] finding F4). All four fixes are small and additive — this is a finish-the-job pass, not a redesign. Target phase for rework: **green**. Recovery action: Dev to address F1–F4, then re-run verify and re-review.

**Specialist subagent coverage in this assessment** (enabled-subagents had findings or clean status; disabled-subagents had no scan but reviewer documented the equivalent manual check inline so every tag appears below at least once):

[TEST] active — see findings F1, F2, F3 (confirmed), F5 (deferred), F7/F8/F9 (dismissed).
[DOC] active — see findings F4 (confirmed), F6 (dismissed).
[RULE] active — rule-checker subagent ran clean: 20 rules / 68 instances / zero violations. Detail in the Rule Compliance section below.
[EDGE] no subagent ran (disabled via `workflow.reviewer_subagents.edge_hunter: false`). Reviewer's manual edge-case audit identified three real gaps that surface as findings F1, F2, F3 below — no additional [EDGE] concerns.
[SILENT] no subagent ran (disabled). Reviewer's manual silent-failure audit: zero try/except, zero `contextlib.suppress`, zero bare-except in the diff. The only default-bearing pattern is `(span.attributes or {}).get(key, default)` in route extracts which the rule-checker confirmed is project convention (audio.py precedent), translator robustness — not a silent fallback at any emit site. No [SILENT] concerns.
[TYPE] no subagent ran (disabled). TEA's verify pass caught and fixed the only type concern (`_FakeSpan.attributes` annotation against `_SpanLike` Protocol — commit `065f609`); current pyright run is clean. No new type contracts beyond matching the audio.py SpanRoute shape exactly. No [TYPE] concerns.
[SEC] no subagent ran (disabled). Reviewer's manual security audit: zero external input handling, zero SQL, zero path manipulation, zero deserialization, zero auth code. The diff is internal OTEL routing + integer arithmetic. No [SEC] concerns.
[SIMPLE] no subagent ran (disabled). TEA's verify phase already ran the simplify triad (reuse, quality, efficiency) and produced 1 low-confidence finding (`_mounted_core` cross-suite duplication) explicitly NOT applied per project-wide integration-test isolation convention (audio, inventory, npc, lore, state_patch, disposition, combat integration tests all use the same pattern). No [SIMPLE] concerns.

## Subagent Results

| # | Subagent | Received | Decision | Notes |
|---|----------|----------|----------|-------|
| 1 | reviewer-preflight | Yes | N/A (clean) | 83/0 across touched test files, ruff clean, pyright clean. Routing-completeness gate intact. |
| 2 | reviewer-edge-hunter | Skipped | disabled | Disabled via `workflow.reviewer_subagents.edge_hunter: false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | Disabled via setting |
| 4 | reviewer-test-analyzer | Yes | 3 confirmed (F1, F2, F3) / 1 deferred (F5) / 4 dismissed (F7, F8, F9 + medium F1-pre-existing) | 9 findings — see below |
| 5 | reviewer-comment-analyzer | Yes | 1 confirmed (F4) / 1 dismissed (F6) | 2 findings — see below |
| 6 | reviewer-type-design | Skipped | disabled | Disabled via setting |
| 7 | reviewer-security | Skipped | disabled | Disabled via setting (no security-relevant changes anyway) |
| 8 | reviewer-simplifier | Skipped | disabled | Disabled via setting (TEA verify ran simplify triad — clean) |
| 9 | reviewer-rule-checker | Yes | N/A (clean) | 20 rules / 68 instances checked. Zero violations. |

**All received: Yes** (4 enabled subagents returned; 5 disabled per project config and pre-filled as Skipped per agent definition).

**Specialist tag coverage** (one entry per category; subagents disabled via project settings get an explicit dismissal):

`[TEST]`: Test-analyzer findings F1, F2, F3 confirmed blocking; F5 deferred per Architect's spec-check pin; F7/F8/F9 dismissed (low-confidence defensive suggestions that don't match project precedent).

`[DOC]`: Comment-analyzer finding F4 confirmed blocking (stale module docstring); F6 dismissed (block-comment is correctly placed at the surprising line, not the obvious one).

`[RULE]`: Rule-checker clean — 20 rules / 68 instances checked, zero violations. Every numbered python.md lang-review rule plus 6 project-specific additional rules (No Silent Fallbacks, No Stubbing, Don't Reinvent, Verify Wiring, No Source-Text Wiring Tests, OTEL Observability Principle) checked exhaustively.

`[EDGE]`: No edge-case-hunter subagent ran (disabled via `workflow.reviewer_subagents.edge_hunter: false`). Manual diff read by reviewer covers edge cases — and finds three that TEA missed (F1, F2, F3 surface those gaps). No additional edge-case dismissals.

`[SILENT]`: No silent-failure-hunter subagent ran (disabled via setting). Manual diff read by reviewer: zero try/except, zero `contextlib.suppress`, zero bare-except in the diff. The only default-bearing pattern is `(span.attributes or {}).get(key, default)` in route extract lambdas — rule-checker confirmed this is project convention (audio.py precedent), translator robustness rather than a silent fallback at the emit site. No silent failure concerns.

`[TYPE]`: No type-design subagent ran (disabled via setting). TEA's verify pass caught and fixed the only type concern (`_FakeSpan.attributes` annotation against `_SpanLike` Protocol — commit `065f609`); current pyright run is clean. No new type contracts beyond matching the audio.py SpanRoute shape exactly.

`[SEC]`: No security subagent ran (disabled via setting). Manual diff read by reviewer: zero external input handling, zero SQL, zero path manipulation, zero deserialization, zero auth code. The diff is internal OTEL routing + integer arithmetic — no attack surface introduced.

`[SIMPLE]`: No simplifier subagent ran (disabled via setting). TEA's verify phase already ran the simplify triad (reuse, quality, efficiency) and produced 1 low-confidence finding (`_mounted_core` cross-suite duplication) explicitly NOT applied per project-wide integration-test isolation convention.

### Findings

#### F1 — `test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero` premise check doesn't pin delta payload values *(BLOCKING — High confidence)*

- **Source:** reviewer-test-analyzer.
- **File:** `tests/integration/test_rig_pool_wiring.py:240` (the strengthened "no re-fire" test).
- **Spec source:** `context-story-53-4.md` AC1 sub-clause: "Repeated damage on a wrecked rig (current already 0, delta=-3) publishes a delta with `new_current=0` and does NOT re-publish a `zero_crossing` event."
- **Gap:** TEA's premise check (added during RED to fix the originally-vacuous test) asserts a delta event arrived — but never inspects `fields["new_current"]`, `fields["old_current"]`, or `fields["delta"]`. A regression where `apply_delta` on a 0-pool emits with stale or unclamped `old_current=-3, new_current=-3` would pass the current assertion. The AC explicitly names `new_current=0` as a contract value.
- **Fix:** Add three assertions after `len(deltas) == 1`:
  ```python
  assert deltas[0]["fields"]["delta"] == -3
  assert deltas[0]["fields"]["old_current"] == 0
  assert deltas[0]["fields"]["new_current"] == 0
  ```
- **Severity:** Major. The whole point of the strengthened premise check was anti-vacuousness; this gap re-introduces a weaker form of the same problem.

#### F2 — AC2 "re-cross after heal" is untested *(BLOCKING — High confidence)*

- **Source:** reviewer-test-analyzer.
- **File:** `tests/integration/test_rig_pool_wiring.py` (gap, no test exists).
- **Spec source:** `context-story-53-4.md` AC2: "Healing back to 1 and damaging to 0 again publishes the crossing event a second time."
- **Gap:** The edge-triggered vs level-triggered distinction is the load-bearing semantic for `zero_crossing`. A regression that introduces a `has_crossed` flag set permanently on first crossing (instead of resetting on heal) would break the spec but pass every existing test — the existing zero-crossing tests only exercise the first crossing.
- **Fix:** Add one integration test (~15 lines): pool at 0 → `apply_delta(+1)` (repair, no crossing) → `apply_delta(-1)` (second crossing) → sleep → assert exactly one `op=zero_crossing` event arrives in the captured window after clearing prior events.
- **Severity:** Major. This is the AC sub-clause most likely to regress and most expensive to debug post-deploy because a wrecked-rig dashboard would silently lie.

#### F3 — AC3 "zero_crossing without crash_event" independence is untested *(BLOCKING — High confidence)*

- **Source:** reviewer-test-analyzer.
- **File:** `tests/integration/test_rig_pool_wiring.py` (gap, no test exists).
- **Spec source:** `context-story-53-4.md` AC3 negative case: "A pool zero-crossing where the crash handler isn't invoked still publishes `rig_pool.zero_crossing` but NOT `rig_pool.crash_event` (these are independent gates)."
- **Gap:** Existing tests pair `apply_delta` to zero WITH `handle_rig_crash` invocation, or skip both. The independence — that `apply_delta` alone produces `zero_crossing` but no `crash_event` — has no test. A regression where `apply_delta` accidentally calls `handle_rig_crash` (or vice versa) would break the gate semantics; the AC prose calls them "independent gates" which is exactly the kind of phrasing that needs a test to keep it true.
- **Fix:** Add one integration test (~12 lines): construct pool with `composure=2`, call `apply_delta(-2)` directly without `handle_rig_crash` → sleep → assert exactly one `op=zero_crossing` AND zero `op=crash_event` events in captured.
- **Severity:** Major. Same reasoning as F2 — load-bearing AC prose with no test to pin it.

#### F4 — Module docstring in `sidequest/telemetry/spans/rig.py:3` is stale *(BLOCKING — High confidence)*

- **Source:** reviewer-comment-analyzer.
- **File:** `sidequest-server/sidequest/telemetry/spans/rig.py:3`.
- **Stale text:** `"""Slice scope: three flat-only emitters. The taxonomy declares ten more..."""`
- **Reality after 53-4:** Five flat-only emitters (`bond_event`, `voice_register_change`, `confrontation_outcome`, `room.entry_skipped`, `room.entry_evaluated`) AND four routed `state_transition` emitters (`rig_pool.created`, `rig_pool.delta`, `rig_pool.zero_crossing`, `rig_pool.crash_event`). The "three" count was off pre-53-4 too (already five FLAT_ONLY), but the migration adds a routed family that the docstring entirely omits.
- **Fix:** Update the preamble to: `"""Slice scope: five flat-only emitters (rig bond/voice/confrontation + two room entry events) and four routed state_transition emitters (rig_pool.* lifecycle). The taxonomy declares ten more; they ship with their producing subsystems."""`
- **Severity:** Minor (docstring), but blocking because future readers will misjudge the file's scope.

#### F5 — AC4 `model_construct(...)` contract is unpinned *(non-blocking with rationale — Defer to follow-up)*

- **Source:** reviewer-test-analyzer.
- **Spec source:** `context-story-53-4.md` AC4: "A `model_construct(...)` (validation-bypass) path also fires, OR explicitly does not — pin the contract."
- **Architect spec-check resolution:** Architect (Major Houlihan) pinned this contract in the spec-check phase via Design Deviation: "Pydantic v2's default behavior is that `model_construct(...)` bypasses both validation AND post-init hooks, so the span does NOT fire on the `model_construct` path."
- **Reviewer's view:** Architect's pin is correct, but the test-analyzer's point is also fair: a one-line test would make the contract self-verifying ("a pydantic upgrade that changes this semantics would fail the test loudly"). Architect explicitly chose to pin via deviation log instead of test, citing production-impact-negligible (no production code uses `model_construct`).
- **Decision:** **Accept Architect's pin.** This is non-blocking. Optionally a follow-up story can add a one-line test (`assert exporter.get_finished_spans() == []` after `RigComposurePool.model_construct(...)`) if a future pydantic upgrade lands in the project. Documented as **deferred** in the Architect's deviation entry already.

#### F6 — Comment placement in `sidequest/game/rig_crash.py:106` *(non-blocking — DISMISSED)*

- **Source:** reviewer-comment-analyzer.
- **Suggestion:** Move the "Realized delta" block-comment from line 106 (between `edge_after = …` and `edge_delta = …`) to line 103 (before `edge_before = …`).
- **Reviewer's view:** The current placement is correct. The comment annotates the *subtraction* (the surprising line — why "realized delta after EdgePool flooring" matters), not the before/apply/after sequence (which is straightforward state capture). Moving it ahead of `edge_before` would over-explain three lines that are obvious for the sake of one line that isn't.
- **Decision:** **DISMISSED.** Project convention is "comments explain WHY non-obvious"; the comment is correctly placed at the non-obvious line.

#### F7–F9 — Low-confidence test-analyzer findings *(non-blocking)*

- **F7:** Exact-key shape assertion (`set(fields.keys()) == {...}`) on the route extract output. Defensive but matches no existing project precedent — audio/chargen tests don't pin output shape this way. **Decision:** Not requested.
- **F8:** Missing-keys (vs empty-string) test case for the crash event route's optional attrs. Real but trivially covered in spirit by the existing empty-string case (the `.get(key, "")` path is the same). **Decision:** Not requested.
- **F9:** `asyncio.sleep(0.05)` vs `asyncio.sleep(0)` style critique. Changing this in 53-4 alone would diverge from the 8 sibling integration wiring tests that all use 0.05. Cross-suite consistency wins. **Decision:** Not requested.

### Rule Compliance

| Rule (lang-review/python.md) | Cluster | Status |
|------------------------------|---------|--------|
| #1 Silent exception swallowing | N/A — no try/except in diff | PASS |
| #2 Mutable default arguments | 6 instances | PASS |
| #3 Type annotation gaps at boundaries | 2 public functions | PASS |
| #4 Logging coverage and correctness | N/A — no logging in diff | PASS |
| #5 Path handling | N/A — no file I/O in diff | PASS |
| #6 Test quality | 19 new/edited test functions | PASS (per rule-checker; F1–F3 are AC coverage gaps not rule-#6 violations) |
| #7 Resource leaks | 1 Span.open context | PASS |
| #8 Unsafe deserialization | N/A | PASS |
| #9 Async/await pitfalls | 7 async sites | PASS |
| #10 Import hygiene | 3 import sites | PASS |
| #11 Input validation at boundaries | N/A — internal API | PASS |
| #12 Dependency hygiene | N/A — pyproject unchanged | PASS |
| #13 Fix-introduced regressions (meta) | 4 new code blocks re-scanned | PASS |
| #14 State cleanup ordering | 5 sites | PASS |
| Additional A (No Silent Fallbacks) | 6 sites | PASS |
| Additional B (No Stubbing) | 5 sites | PASS |
| Additional C (Don't Reinvent — wire up what exists) | 4 sites | PASS |
| Additional D (Every Test Suite Needs a Wiring Test) | 1 wiring test file | PASS |
| Additional E (No Source-Text Wiring Tests) | 4 test files scanned | PASS |
| Additional F (OTEL Observability Principle) | 4 spans + 4 attrs | PASS |

Zero rule violations across 20 rules / 68 instances. The F1–F4 findings are AC coverage gaps and stale-comment issues, not project-rule violations — but they're blocking because they're AC-required.

### Decision

**Verdict: REJECTED.** Hand back to Dev (Major Winchester) at the **green** phase for a focused fix pass on F1, F2, F3, F4. All four are small additive changes:

- F1: 3 extra assertions in an existing test
- F2: 1 new ~15-line integration test
- F3: 1 new ~12-line integration test
- F4: 1 docstring update

Total estimated work: under 50 LOC, all in files Dev already touched. F5–F9 are accepted/dismissed/deferred per individual rationale (F5 deferred per Architect's spec-check pin; F6 dismissed as correctly-placed comment; F7/F8/F9 dismissed as low-confidence defensive suggestions that don't match project precedent).

After Dev fixes, re-run testing-runner against the touched files + routing-completeness to confirm GREEN, then route back through verify (TEA simplify) + review (this) before proceeding to spec-reconcile.

## Dev Assessment (rework pass)

**Status:** GREEN (second pass). 85 passed / 0 failed across the five touched test files (was 83 pre-rework — two new integration tests landed clean). ruff clean. pyright clean. routing-completeness invariant still intact.

**Findings closed:**

- **F1 closed** — `tests/integration/test_rig_pool_wiring.py::test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero`. Added three field-value assertions after the premise check: `delta == -3`, `old_current == 0`, `new_current == 0`. A regression that fails to clamp the delta payload on a wrecked rig would now fail.
- **F2 closed** — new test `test_rig_pool_zero_crossing_re_fires_after_repair_and_re_damage`. Drives pool 1 → 0 → 1 → 0; clears captured events before the second damage; asserts exactly one zero_crossing in the post-clear window with `old_current=1, new_current=0`. Pins AC2's re-cross-after-heal contract.
- **F3 closed** — new test `test_rig_pool_zero_crossing_independent_of_crash_event`. Drives pool 2 → 0 via `apply_delta` only (no `handle_rig_crash`); asserts one zero_crossing fires and crash_event does not. Pins AC3's "independent gates" claim.
- **F4 closed** — module docstring at `sidequest/telemetry/spans/rig.py:1` rewritten. Now accurately enumerates five flat-only emitters and four routed `state_transition` emitters with the precedent rationale (audio.py/chargen.py/cavern_room.py).

**Findings accepted from prior review (no change required):**

- F5 (AC4 `model_construct` test) — deferred per Architect's spec-check deviation pin. No code change.
- F6 (block-comment placement) — dismissed. No code change.
- F7/F8/F9 — dismissed low-confidence defensive suggestions. No code change.

**Production changes in this rework commit (`e639247`):**

1. `sidequest/telemetry/spans/rig.py`: module docstring rewrite (F4). No code logic change.
2. `tests/integration/test_rig_pool_wiring.py`: 3 added assertions to existing test (F1), 2 new tests (F2, F3). Existing tests untouched.

No changes to `sidequest/game/rig_crash.py` — the production logic was correct in the first pass. The rework is entirely additive test coverage + a docstring fix.

**Verification:**
- Full set of touched tests: 85 passed / 0 failed (was 83 in the original GREEN run).
- ruff check on changed files: All checks passed!
- pyright on changed files: 0 errors, 0 warnings, 0 informations.
- routing-completeness still passes.

**Handoff:** To Architect (Major Houlihan) for re-spec-check, then TEA (Radar) for re-verify, then Reviewer (Colonel Potter) for re-review. The rework is small enough that the second pass should move quickly — no AC re-interpretation, no contract drift, just closing the four gaps the first review identified.

## Architect Assessment (spec-check, second pass)

**Spec Alignment:** Aligned (one minor unpinned contract — unchanged from first pass)
**Mismatches Found:** 0 new mismatches introduced by the rework

### Rework AC-by-AC re-walkthrough

| AC | First-pass status | Rework change | Second-pass status |
|----|-------------------|---------------|--------------------|
| AC1 — `rig_pool.delta` damage + repair via watcher | Aligned, but sub-clause "wrecked rig publishes delta with `new_current=0`" had no field-value assertion (F1 from Reviewer) | Premise check at `test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero:254-261` now asserts `delta == -3, old_current == 0, new_current == 0` | **Aligned** |
| AC2 — `rig_pool.zero_crossing` once per downward crossing | Aligned, but sub-clause "heal back to 1 and damage to 0 again publishes a second crossing" had no test (F2 from Reviewer) | New test `test_rig_pool_zero_crossing_re_fires_after_repair_and_re_damage` drives 1→0→1→0, clears captured, asserts exactly one zero_crossing in the second-damage window with `old_current=1, new_current=0` | **Aligned** |
| AC3 — `rig_pool.crash_event` consequence outcomes | Aligned for the positive case, but negative case "zero_crossing without crash_event are independent gates" had no test (F3 from Reviewer) | New test `test_rig_pool_zero_crossing_independent_of_crash_event` drives `apply_delta(-2)` without `handle_rig_crash`, asserts one zero_crossing fires and crash_event does NOT | **Aligned** |
| AC4 — `rig_pool.created` via watcher path + `model_construct` contract | Drift detected (Ambiguous spec) — pinned via Design Deviation as "explicitly does not fire" | **Unchanged.** Reviewer's F5 noted a test could harden the pin; deferred per the spec-check decision. Production impact remains negligible. | **Drift detected (unchanged)** |
| AC5 — Canonical integration wiring test | Aligned | No change | **Aligned** |
| AC6 — Single emission mechanism | Aligned | No change | **Aligned** |

### Additional re-check: docstring drift

The Reviewer's F4 found stale text in `sidequest/telemetry/spans/rig.py:1-3` claiming "three flat-only emitters" — wrong both pre- and post-53-4. The rework rewrote the preamble to accurately enumerate five flat-only emitters (`rig.bond_event`, `rig.voice_register_change`, `rig.confrontation_outcome`, `room.entry_skipped`, `room.entry_evaluated`) and four routed `state_transition` emitters (`rig_pool.created/delta/zero_crossing/crash_event`) with the precedent rationale. Verified accurate against the current code.

### Decision

**Proceed to TEA verify (second pass).** The rework closes the three test-coverage gaps from the first review cleanly, with no spec drift introduced. AC4's `model_construct` pin remains via Design Deviation — that decision still stands; no need to relitigate. The story is in better shape than at the first verify entry: more behavioral test coverage on the AC sub-clauses that matter most (re-cross-after-heal is the highest-value addition; that was the most likely silent-regression surface).

**Handoff:** To TEA (Radar O'Reilly) for re-verify — simplify + quality-pass on the rework diff.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (one minor unpinned contract — see AC4)
**Mismatches Found:** 1 (Trivial / Cosmetic — does not block review)

### AC-by-AC walkthrough (against `sprint/context/context-story-53-4.md`)

| AC | Spec | Code | Status |
|----|------|------|--------|
| AC1 — `rig_pool.delta` damage + repair via watcher | Both signs publish; no-op publishes; wrecked-rig damage publishes delta but not zero_crossing | `apply_delta` emits on every call regardless of sign; SpanRoute carries delta/old/new; integration test `test_rig_pool_delta_reaches_watcher_via_span_route` covers damage; existing unit tests cover repair semantics | **Aligned** |
| AC2 — `rig_pool.zero_crossing` once per downward crossing | Exactly one event per downward crossing; no re-fire when already 0; healing-and-re-damaging fires again | `apply_delta` gates emission on `zero_crossed = old > 0 and new == 0`; integration test `test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero` proves no-re-fire with a premise check (delta DID publish, crossing did NOT). The "heal-and-re-damage fires twice" sub-clause is structurally guaranteed by the `old > 0` guard but has no explicit test. Minor coverage gap, not a code gap. | **Aligned** |
| AC3 — `rig_pool.crash_event` carries consequence outcomes | Span attrs include `edge_delta` (realized), `edge_after`, `injury_status_text`, `dismounted_status_text`; negative cases (handler returns None / zero_crossing without crash handler) emit nothing | All four attrs present; `edge_delta` computed as realized delta after EdgePool flooring (`edge_after - edge_before`); pre-existing idempotency + not-destroyed guards retained; `test_handle_rig_crash_does_not_emit_span_on_idempotent_call` and `test_handle_rig_crash_does_not_emit_span_when_rig_not_destroyed` still pass for the negative cases | **Aligned** |
| AC4 — `rig_pool.created` publishes via the watcher | Direct construction AND `model_validate_json` round-trip both fire; "A `model_construct(...)` (validation-bypass) path also fires, OR explicitly does not — **pin the contract**." | `model_post_init` emits; direct construction + round-trip both covered. **`model_construct` is unpinned in tests and unpinned in code comments.** Pydantic v2's default behavior is that `model_construct` skips `model_post_init`, so the span does NOT fire on that path — but this contract is implicit, not explicit. | **Drift detected (Ambiguous spec)** |
| AC5 — Integration / wiring test (canonical end-to-end) | Real `watcher_hub.subscribe` path; bind loop; drive pool → damage to crash → handle_rig_crash; assert ordered events with crash_event consequence attrs | `test_rig_crash_full_sequence_publishes_ordered_events` is exactly this shape; asserts `["created", "delta", "zero_crossing", "crash_event"]` in order. Canonical wiring test for the story. | **Aligned** |
| AC6 — Single emission mechanism | All four spans use same shape (SpanRoute OR direct watcher_publish, not both); preferred: spans in SPAN_ROUTES, removed from FLAT_ONLY_SPANS | All four registered in `SPAN_ROUTES` with `state_transition + component="rig"` extract lambdas; all four removed from `FLAT_ONLY_SPANS.update(...)`; `routing-completeness` test enforces no overlap; `test_rig_pool_spans_are_routed_state_transition` and `test_span_rig_pool_crash_event_is_routed_state_transition` directly assert membership | **Aligned** |

### Mismatch detail

- **AC4 — `model_construct` contract for `rig_pool.created` span emission** (Ambiguous spec — Cosmetic — Trivial)
  - **Spec (context-story-53-4.md AC4):** "A `model_construct(...)` (validation-bypass) path also fires, OR explicitly does not — pin the contract."
  - **Code (rig_composure_pool.py:90):** Emits via `model_post_init`. Pydantic v2's default behavior is that `model_construct(...)` bypasses both validation AND post-init hooks, so the span does NOT fire on the `model_construct` path. This is the de-facto contract but is implicit — neither a code comment nor a test pins it.
  - **Production impact:** Negligible. `model_construct` is a pydantic test convenience for building instances without validation; production code (save/load via `model_validate_json`, materializer instantiation, runtime mutations) never uses it. The save-load path goes through `model_validate_json`, which DOES fire `model_post_init`, so the GM dashboard sees every `rig_pool.created` event in real gameplay.
  - **Recommendation:** **Option C — clarify spec**. Add a Design Deviation note (this assessment serves as the pin) and OPTIONALLY in a follow-up: a one-line code comment on `model_post_init` documenting the contract. No code change required for 53-4; the implicit behavior is correct.

### Decision

**Proceed to TEA verify.** The single mismatch is Trivial / Cosmetic and pinned by this assessment. AC4 is satisfied because the spec offered an "OR explicitly does not" branch and the code matches pydantic v2's default behavior — the only gap is that the contract was implicit rather than explicit. This assessment makes it explicit; no rework needed.

**Architect spec-check sign-off:** clean. Two production files (`sidequest/telemetry/spans/rig.py`, `sidequest/game/rig_crash.py`), additive at the route registration layer + attribute expansion at the emit site. Pattern adherence to audio.py / chargen.py is exact. TEA's two pinned design contracts (SpanRoute mechanism, realized-delta semantics) are both implemented as specified and were correct calls — Dev confirmed without pushback. The Dev assessment's defensive-pattern explanation (`(span.attributes or {}).get(key, default)`) is consistent with the project-wide translator robustness convention.

**Handoff:** To TEA (Radar O'Reilly) for verify phase — simplify + quality-pass.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Pinned SpanRoute as the wiring mechanism (rejected the direct watcher_publish alternative).**
  - Spec source: context-story-53-4.md, Technical Guardrails §1 ("Pick **one** approach for the wiring").
  - Spec text: "either a direct watcher publish at each emit site (magic precedent) or a SpanRoute registration removing them from FLAT_ONLY_SPANS — and apply it consistently."
  - Implementation: Tests force SpanRoute migration. The four rig_pool spans must be registered in `SPAN_ROUTES` with `event_type="state_transition"`, `component="rig"`, and an `extract` lambda returning `{field, op, ...}`; spans must be REMOVED from `FLAT_ONLY_SPANS`.
  - Rationale: Audio, chargen, cavern_room, NPC auto-register, and lore-established all use `SPAN_ROUTES + state_transition`. Magic uses direct `_watcher_publish` only for high-volume per-cost emissions (`magic.unrouted_cost`), not for routine state transitions. Rig pool deltas / crash events are state-transition shaped; following the dominant precedent keeps the dashboard taxonomy consistent.
  - Severity: minor
  - Forward impact: If Dev finds a structural reason SpanRoute can't work for the rig family (e.g., the extract lambda can't reach a needed attr), log on the GREEN side and re-pick the mechanism.
- **Pinned crash_event consequence-attr contract (edge_delta, edge_after, injury_status_text, dismounted_status_text).**
  - Spec source: context-story-53-4.md, Technical Guardrails §2 + AC3.
  - Spec text: "`rig_pool.crash_event` MUST include the three consequence outcomes as attributes so the dashboard renders the crash deterministically."
  - Implementation: Tests pin specific attribute names (`edge_delta`, `edge_after`, `injury_status_text`, `dismounted_status_text`) and specific semantics — particularly that `edge_delta` is the REALIZED delta (post-flooring), not the requested `DRIVER_EDGE_HIT`.
  - Rationale: ADR-031 Layer-2 says "structured spans … with fields capturing what was decided." The "realized vs. requested" distinction matters because EdgePool floors at 0; a driver at 0 Edge takes a crash and the dashboard must reflect that no Edge was actually subtracted rather than printing `-1` against a 0→0 transition. Sebastien's lie detector says what happened, not what was asked. Test `..._floor_edge_at_zero` is the canonical pin.
  - Severity: minor
  - Forward impact: If Dev prefers "edge_delta = requested + edge_after = actual," that's defensible but requires re-running these two tests with inverted contract + updating the route extract lambda. Bring back to TEA before flipping.
- **Strengthened the "no re-fire" wiring test to require a positive premise check.**
  - Spec source: TEA self-check ("EVERY TEST MUST ASSERT SOMETHING MEANINGFUL — could the assertion pass even if the behavior is wrong?").
  - Spec text: "Does any test use `let _ = result;` — this is vacuous."
  - Implementation: `test_rig_pool_zero_crossing_does_not_re_fire_when_already_zero` now first asserts the `delta` event DID publish before asserting `zero_crossing` did NOT — without the premise check, the test passed vacuously when no wiring existed at all (the pre-53-4 production state).
  - Rationale: First pytest run had this test passing under FLAT_ONLY production state because the captured-events list was empty. Caught by self-check.
  - Severity: minor (caught and fixed pre-handoff)
  - Forward impact: none.

### Dev (implementation)
- No deviations from spec. All three TEA-pinned contracts (SpanRoute mechanism, realized-delta semantics, no-re-fire premise check) implemented as specified — no GREEN-side flips required.
- Rework pass (commit `e639247`): no deviations. All four Reviewer findings (F1–F4) addressed exactly as recommended — strengthened premise check with field-value assertions (F1), added re-cross-after-heal test (F2), added zero_crossing-without-crash-event test (F3), rewrote stale module docstring (F4). No production logic changes; rework is purely additive test coverage + a documentation fix.

### Architect (spec-check)
- **Pinned the `model_construct(...)` contract for `rig_pool.created` span emission.**
  - Spec source: context-story-53-4.md, AC4.
  - Spec text: "A `model_construct(...)` (validation-bypass) path also fires, OR explicitly does not — pin the contract."
  - Implementation: Pydantic v2 `model_construct(...)` bypasses both validators AND post-init hooks by default. `RigComposurePool.model_post_init` is the emit site for `rig_pool.created`. Therefore the span does NOT fire on the `model_construct` path. This is the de-facto contract; this entry makes it explicit.
  - Rationale: `model_construct` is a pydantic test convenience for building instances without validation; production paths (save/load via `model_validate_json`, materializer instantiation, runtime mutations) never use it. The save-load round-trip fires `model_post_init` correctly per pydantic v2 semantics, so the GM dashboard sees every `rig_pool.created` event in real gameplay.
  - Severity: trivial (the spec offered "OR explicitly does not" as an acceptable branch; this assessment chooses that branch)
  - Forward impact: If a future story makes test fixtures use `model_construct(...)` for `RigComposurePool` and expects the span to fire, that test will silently observe zero events. A one-line code comment on `model_post_init` in a follow-up cleanup story would harden the contract; not required for 53-4. Reviewer's F5 re-raised this in the first review pass — re-confirmed deferred per the spec-check decision.
- **Second-pass re-spec-check.** Re-walked AC1–AC6 against the rework commit (`e639247`). No new mismatches introduced. The three new test additions (F1 field-value assertions, F2 re-cross-after-heal, F3 zero-crossing-without-crash-event) close the first-pass AC sub-clause gaps that the Reviewer surfaced. AC4 status unchanged. No deviation entries required for the rework itself — it implements the spec as originally written.

### Architect (reconcile)

**Deviation manifest verification:** All in-flight deviation entries from TEA (3 entries), Dev (1 positive-null entry + 1 rework note), and Architect (1 spec-check entry + 1 re-spec-check note) have been re-read. Every entry carries the required 6 fields per `pennyfarthing-dist/guides/deviation-format.md`. Spec source paths (`sprint/context/context-story-53-4.md`, `pennyfarthing-dist/templates/deviation-format.md`-style TEA self-check) are real and verified. Quoted spec text is accurate against the source documents. Implementation descriptions match the code as it stands at commit `e639247`.

**AC deferral cross-reference:** One AC sub-clause was formally deferred and remains deferred at story close:

- **AC4 `model_construct(...)` contract not pinned by test** — deferred per Architect (spec-check) deviation §1. Pydantic v2's `model_construct` bypasses both validators and `model_post_init`, so `RigComposurePool.model_construct(...)` does not emit `rig_pool.created`. This is the "explicitly does not fire" branch the spec offered. Reviewer's F5 (first pass) re-raised the option of pinning the contract via a one-line test; Reviewer accepted the deferral on second-pass APPROVE. Production impact: negligible — production paths use `model_validate_json` (which fires `model_post_init`), not `model_construct`. A future story may add the one-line pin test if a pydantic upgrade looms.

No additional missed deviations from spec found. The two non-blocking docstring nits the Reviewer surfaced (NF1 `rig.py:34` inline comment "these three" carry-over, NF2 F2 test docstring "second crash" misnomer) are documentation-accuracy issues within Dev's implementation, not deviations from `sprint/context/context-story-53-4.md`. They were flagged as "recommended polish" with merge approved; no spec authority was bypassed. Dev/SM may land a polish commit on this branch before merge or defer to a follow-up cleanup story — either route honors the approved verdict.

**Process deviations (out of story scope but worth recording for the project, not the story):**

The Reviewer's first-pass REJECT did not trigger the approval gate's `recovery_config.reviewer-verdict.action: rework` path; the gate's verdict-parser appears to accept any verdict token rather than requiring `APPROVED` specifically. Session was manually rolled back to green and Dev addressed F1–F4 cleanly. This is a tooling bug in `pf` / the approval gate, not a story deviation. Captured under Delivery Findings → Reviewer (code review) and explicitly NOT counted as a spec deviation here.

**Conclusion:** Deviation manifest complete. No additional Architect-side reconcile deviations to log. Ready for SM finish.