---
story_id: "97-4"
jira_key: ""
epic: "97"
workflow: "tdd"
---
# Story 97-4: Scratch sweep fires on same-region drift — clear_scratch_on_scene_end keys on the raw location-string gate #739 fixed for encounters

## Story Details
- **ID:** 97-4
- **Jira Key:** (not tracked)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p2
- **Type:** bug

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T21:58:35Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T21:43:11.848168Z | 2026-06-10T21:44:43Z | 1m 31s |
| red | 2026-06-10T21:44:43Z | 2026-06-10T21:50:14Z | 5m 31s |
| green | 2026-06-10T21:50:14Z | 2026-06-10T21:52:38Z | 2m 24s |
| review | 2026-06-10T21:52:38Z | 2026-06-10T21:58:35Z | 5m 57s |
| finish | 2026-06-10T21:58:35Z | - | - |

## Story Context

**Root Cause:** Same-region scene-title drift in region-mode worlds triggers the raw `old_loc != result.location` string gate in `clear_scratch_on_scene_end`, wiping scratch state that should survive when the party stays in the same region.

**Parent Issue:** Mirrors server #739 (region-drift encounter abandonment), which was fixed by consulting the `_same_region_drift` signal in `narration_apply.py`. This story applies the same pattern to the scratch-sweep gate.

**Acceptance Criteria:**
- Same-region drift does not clear scratch; a genuine region change still does
- OTEL/log evidence on the keep-vs-sweep decision

**Test Harness Reference:** tests/server/test_region_drift_encounter_continue.py (from server #739)

**Modified Files:** 
- sidequest/game/scratch.py (clear_scratch_on_scene_end function)
- sidequest/game/narration_apply.py (access _same_region_drift signal)

## Sm Assessment

**Story is well-scoped and ready for RED.** This is a 2-point bug fix with a known-good pattern to mirror — server #739 already solved the same root-cause family (region-drift) by consulting the `_same_region_drift` signal in `narration_apply.py`. This story applies that exact fix one gate over, at the scratch-sweep gate in `clear_scratch_on_scene_end` (`sidequest/game/scratch.py`).

**Why low risk:** The fix is a signal-substitution at a single gate (raw `old_loc != result.location` string compare → `_same_region_drift` signal), not new architecture. The test harness already exists — `tests/server/test_region_drift_encounter_continue.py` from #739 — so TEA has a proven scaffold to extend rather than build from scratch.

**RED phase guidance for TEA:** Write failing tests that prove (1) a same-region scene-title drift in a region-mode world does NOT clear scratch state, and (2) a genuine cross-region change DOES still clear it. Per project doctrine (OTEL is the lie detector), assert on the keep-vs-sweep decision being logged so the GM panel can verify the gate fired correctly. Mirror the #739 harness structure.

**Scope discipline:** Server-only, no UI/content/daemon involvement. Don't widen beyond the scratch-sweep gate — encounter abandonment (#739) is already fixed; this is the deliberately-deferred sibling residual flagged in the 2026-06-07 ping-pong FIXER notes.

## Branch Strategy
gitflow (feat/97-4-scratch-sweep-region-drift)

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): SM assessment located the fix at `sidequest/game/scratch.py` inside `clear_scratch_on_scene_end`. The actual fix locus is the **call site** in `sidequest/server/narration_apply.py:3934` (the gate `if old_loc and old_loc != result.location:`); the function itself lives in `sidequest/server/status_clear.py` and is correct as-is — it's a party-wide sweep with no knowledge of region drift. Dev must gate the *call*, not the function. Affects `sidequest/server/narration_apply.py` (wrap the `clear_scratch_on_scene_end(...)` call in `if not _same_region_drift:` and emit the keep span in the skip branch). *Found by TEA during test design.*
- **Improvement** (non-blocking): `_same_region_drift` is computed at three sites upstream of the gate (narration_apply.py:3696 rejected heading, :3758 heading-resolves-to-current-region, :3880 unresolved-POI) and is already in scope at line 3934 — no recomputation needed. The encounter-abandon ladder directly below the sweep (line ~3980+) already consumes the same flag (#739), so the fix is symmetric with proven code. *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. TEA's finding (fix locus at `narration_apply.py:3934`, not `scratch.py`) was confirmed exactly — the function in `status_clear.py` is correct as a party-wide sweep and needed no change. Fix landed in one file with no surprises.

### Reviewer (code review)
- **Improvement** (non-blocking): The second keep-test under-asserts (Scratch only, not Boon) and there is no multi-PC sweep test. Affects `tests/server/test_scratch_sweep_region_drift.py` (add a Boon assertion to `test_heading_resolving_to_current_region_keeps_scratch` and an optional two-PC drift test). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The test module docstring's "Contract for Dev (RED phase, TEA):" label is stale now that the implementation has landed GREEN. Affects `tests/server/test_scratch_sweep_region_drift.py` (retitle to "Implementation contract:"). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec. Both ACs are covered (AC1 same-region drift keeps scratch / genuine change still sweeps; AC2 OTEL evidence on the keep-vs-sweep decision). Added three guard tests beyond the AC minimum (room-graph world still sweeps; session-start no-op; Boon coverage alongside Scratch) — additive coverage, not a scope change.

### Dev (implementation)
- No deviations from spec. Implemented exactly the fix TEA specified: gated the `clear_scratch_on_scene_end(...)` call at `narration_apply.py:3934` on `if not _same_region_drift:`, with an `else:` branch emitting the `scratch_sweep_skipped_same_region_drift` watcher event (component="encounter") + a paired `logger.info`. The encounter-abandon ladder below the gate is untouched. No new types, no new imports beyond the existing deferred `clear_scratch_on_scene_end` import.

### Reviewer (audit)
- **TEA "No deviations from spec"** → ✓ ACCEPTED by Reviewer: both ACs covered; the 3 guard tests are additive, not scope creep. Agrees with author reasoning.
- **Dev "No deviations from spec"** → ✓ ACCEPTED by Reviewer: landed code matches the TEA contract byte-for-byte (gate, watcher event name, fields, `component="encounter"`, encounter ladder untouched). Verified against `narration_apply.py:3946-3978`.
- No undocumented deviations found. The deferred-import move (from outer block into the `if not _same_region_drift:` branch) is tighter scoping, not a spec deviation — the import only loads when the sweep will actually run, matching the pre-existing deferred-import discipline at this call site.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/narration_apply.py` — gated the scratch-sweep call on `not _same_region_drift`; on a same-region drift, skip the sweep and emit the `scratch_sweep_skipped_same_region_drift` keep span (OTEL lie-detector) + a paired info log. ~40 lines, all within the existing `if old_loc and old_loc != result.location:` block. The function `clear_scratch_on_scene_end` (status_clear.py) and the encounter-abandon ladder are unchanged.

**Approach:** Minimal signal-substitution, symmetric with #739. `_same_region_drift` is already computed upstream (lines 3696/3758/3880) and in scope at the gate — no recomputation. The keep span is emitted from `narration_apply` (where the flag lives), so it reaches the GM panel via `narration_apply._watcher_publish` exactly as the test harness observes.

**Tests:** 30/30 passing (5 new in `test_scratch_sweep_region_drift.py` + 25 sibling baseline in `test_region_drift_encounter_continue.py` + `test_status_clear.py`). Wider net (`-k region/location/scratch/status_clear/narration_apply`): 311 passed, 12 skipped. Lint clean (`ruff check` + `ruff format` no-op). Pyright: 0 new errors in the edited range (37 pre-existing errors elsewhere in this 4000-line file, none from this change).

**Branch:** `feat/97-4-scratch-sweep-region-drift` (pushed to origin)

**Self-review:**
- Wired: keep span flows through the production `_apply_narration_result_to_snapshot` path, verified by the suite driving that path (not the helper in isolation).
- Project patterns: mirrors the adjacent `confrontation_continued_same_region_drift` keep-span pattern (#739) — same flag, same component, same field shape.
- ACs met: AC1 (drift keeps scratch / genuine change sweeps) + AC2 (OTEL keep-vs-sweep evidence).
- Error handling: none needed — the gate is a boolean branch over already-validated state; no user-controlled I/O introduced (lang-review #1/#7/#8 N/A to this change).

**Handoff:** To verify phase (TEA — Amos Burton) for simplify + quality-pass.

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Reason:** Behavior bug fix with observable state + OTEL contract — needs failing tests before the fix.

**Test Files:**
- `tests/server/test_scratch_sweep_region_drift.py` — 5 tests mirroring the #739 region-drift harness, targeting the scratch-sweep gate.

**Tests Written:** 5 tests covering 2 ACs (+ 3 guards)
**Status:** RED — 2 failing (the two same-region-drift "keep" cases), 3 passing (guards that assert *existing* correct behavior: genuine region change sweeps, room-graph world sweeps, session-start no-op).

Failing for the right reason — verified: `test_sub_location_drift_keeps_scene_bounded_status` fails with `got statuses=['Bruised Ribs']`, i.e. the buggy gate swept Scratch ("Choked") + Boon while Wound correctly persisted. The two failures resolve once Dev gates the sweep call on `_same_region_drift` and emits the keep span.

### Test → AC / behavior map

| Test | Covers | RED status |
|------|--------|------------|
| `test_sub_location_drift_keeps_scene_bounded_status` | AC1 (drift keeps Scratch+Boon) + AC2 (keep span fields) | **failing** |
| `test_heading_resolving_to_current_region_keeps_scratch` | AC1 (current-region heading drift) + AC2 (keep span fires) | **failing** |
| `test_genuine_region_change_still_sweeps_scratch` | AC1 guard (real boundary still sweeps) + AC2 (no keep span) | passing (existing behavior) |
| `test_room_graph_world_unresolved_heading_still_sweeps_scratch` | region-mode gating guard | passing (existing behavior) |
| `test_first_location_set_does_not_emit_keep_event` | `old_loc is None` session-start guard | passing (existing behavior) |

### Rule Coverage (lang-review/python.md)

| Rule | Coverage | Status |
|------|----------|--------|
| #6 Test quality (meaningful assertions, no vacuous asserts) | Every test asserts on specific status-text membership and exact keep-event field values; no `assert True` / bare-truthy / assertion-free tests | enforced |
| #4 Logging/OTEL evidence | AC2 asserts the `scratch_sweep_skipped_same_region_drift` watcher event + its `component`/fields — the GM-panel lie-detector contract | enforced |

**Rules checked:** 2 of 10 lang-review rules apply to a test-only RED change (the rest — silent-except, mutable-defaults, resource-leaks, deserialization, async — govern Dev's production edit; flagged for Dev/Reviewer). **Self-check:** 0 vacuous tests found.

**Wiring:** The suite drives the real production path `_apply_narration_result_to_snapshot` (not the helper in isolation), so it is itself the wiring test — the keep span must be emitted through `narration_apply._watcher_publish` to be observed, which is exactly where the GM panel reads it.

**Handoff:** To Dev (Naomi Nagata) for GREEN — see Delivery Findings for the precise fix locus (`narration_apply.py:3934`, NOT `scratch.py`).
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (30/30 green, lint+format clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 2 (MEDIUM/LOW, non-blocking), dismissed 1 (mock-note), deferred 1 (multi-PC) |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 | confirmed 1 (LOW, non-blocking) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | none (16 rules, 31 instances, 0 violations) | N/A |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 0 confirmed blocking; 3 confirmed non-blocking (MEDIUM/LOW), 1 dismissed (with rationale), 1 deferred

## Reviewer Assessment

**Verdict:** APPROVED

A tight, correct, well-tested 2-point bug fix. No Critical or High findings across the enabled review panel (preflight, test-analyzer, comment-analyzer, rule-checker). The production change is a single `_same_region_drift` gate around the existing scratch-sweep call, symmetric with the #739 encounter-ladder fix that uses the same upstream signal.

**Data flow traced:** narrator-emitted `result.location` → `_apply_narration_result_to_snapshot` location_update block → `_same_region_drift` computed upstream (narration_apply.py:3578 init; set True at :3696/:3758/:3880, all in region-mode worlds only) → scratch-sweep gate at :3946. On same-region drift the sweep is skipped and a `scratch_sweep_skipped_same_region_drift` watcher event fires (component="encounter"); otherwise the sweep runs. Safe because the flag is only True when the party is genuinely scene-continuous within one cartography region — scene-bounded status (Scratch/Boon) should persist within a scene by design.

**Pattern observed:** Mirrors the adjacent `confrontation_continued_same_region_drift` keep span (narration_apply.py:4151) — same flag, same component, same field shape. Two sibling gates now share one computed truth value rather than re-deriving the region comparison. Correct pattern (narration_apply.py:3946-3978).

**Error handling:** No new error surface — the gate is a boolean branch over already-validated internal game state; no user-controlled I/O. The skip decision is explicitly logged (logger.info) and observable (watcher event) — No Silent Fallbacks honored (narration_apply.py:3954-3978).

### Rule Compliance (lang-review/python.md + CLAUDE.md/SOUL.md)

Exhaustive check via reviewer-rule-checker (16 rules, 31 instances, 0 violations), independently corroborated:
- **#1 Silent exceptions** — none introduced; deferred import inside a plain conditional, no try/except. ✓
- **#3 Type annotations** — `_apply_narration_result_to_snapshot` fully annotated; test helpers are private/exempt. ✓
- **#4 Logging** — `logger.info("...%r...%s", ...)` lazy %-style (not f-string); INFO level correct for an informational skip decision; no sensitive data (game character/region names). ✓
- **#6 Test quality** — all 15 assertions are specific value checks; no vacuous asserts; monkeypatch targets `narration_apply._watcher_publish` (where used). ✓
- **#10 Import hygiene** — deferred import correctly scoped into the `if not _same_region_drift:` branch (tighter than before); no star imports; no new circular risk. ✓
- **OTEL Observability (CLAUDE.md)** — the skip decision emits a watcher event with all required fields, wired through the module-level `_watcher_publish` and verified by the test capturing exactly one event. ✓
- **No Source-Text Wiring Tests (CLAUDE.md)** — wiring asserted via OTEL-span capture (the approved pattern), not source grep. ✓

### Observations

- [VERIFIED] Comment referents accurate — `_same_region_drift` "computed above" (set at :3696/:3758/:3880, all precede gate :3946) and `confrontation_continued_same_region_drift` keep span "below" (at :4151). Evidence: grep confirms line ordering.
- [VERIFIED] OTEL keep span is wired, not dead code — `_watcher_publish` aliased at narration_apply.py:128, called in-module at :3969; test `test_sub_location_drift_keeps_scene_bounded_status` asserts exactly one event with `component="encounter"` and all five fields. Real production-path assertion.
- [VERIFIED] Skip is correctly scoped to region-mode worlds only — `_same_region_drift` is gated by `_is_region_mode_world` at all three set-sites, so room-graph worlds keep sweep-on-leave (test_room_graph_world_unresolved_heading_still_sweeps_scratch passes). Evidence: narration_apply.py:3695-3696, :3753, :3848-3880.
- [TEST][MEDIUM] `test_heading_resolving_to_current_region_keeps_scratch` (test file ~line 206) asserts only Scratch survives, not Boon — the sibling POI-drift test checks both. Non-blocking: the production gate wraps the *entire* `clear_scratch_on_scene_end` call (which handles Scratch+Boon uniformly via `_SCENE_BOUNDED_SEVERITIES`), and the first keep test already proves both survive on a drift, so a "Boon-only sweep on this branch" regression is structurally implausible. Recommend adding the one-line Boon assertion on a future touch.
- [TEST][MEDIUM/deferred] No multi-PC test. The sweep iterates all `snapshot.characters`; a two-PC same-region-drift case would exercise the cohort-follow + sweep interaction. Deferred — the single-PC fixture is the correct repro shape for the original perseus bug; multi-PC is additive hardening, not a coverage hole for the ACs.
- [TEST][dismissed] Mock-coupling note (capture targets narration_apply._watcher_publish): dismissed — the `len == 1` assertion catches a moved emit site, and emitting from narration_apply is the correct architecture (the flag lives there). No action needed.
- [DOC][LOW] Test module docstring labels the contract block "Contract for Dev (RED phase, TEA):" — now stale since the implementation landed GREEN in the same PR. Content is accurate; only the label misleads about current state. Non-blocking; recommend retitle to "Implementation contract:" on a future touch.
- [LOW][acceptable] The keep span fires on every same-region drift even when the party carries no scene-bounded status. Minor: it is a decision marker ("engine chose not to sweep"), consistent with the encounter ladder's per-drift continue span. Not noise worth gating.

### Devil's Advocate

Argue this is broken. First attack: does skipping the sweep ever strand a Scratch that *should* clear? `_same_region_drift` is True only in region-mode worlds when the heading is a sub-location, a heading resolving to the current region, or a rejected heading — all cases where `current_region` does not advance. Scene-bounded status is defined to persist within a scene, and "same region, no current_region advance" is the engine's definition of scene-continuity (the same definition #739 uses to keep combat alive). So a stranded Scratch would require the status to *deserve* clearing mid-scene — but the only scene-bounded clear triggers are scene_end and location_change, and this turn is neither. No strand.

Second attack: double-fire or ordering. Could both the sweep AND the keep span fire? No — the `if/else` is mutually exclusive. Could the keep span fire when `old_loc == result.location`? No — the outer `if old_loc and old_loc != result.location` guards it; identical strings skip the whole block (session-start test + the outer guard cover this).

Third attack: a confused author moves the emit into status_clear during a refactor → the test's monkeypatch (on narration_apply) misses it and the count silently drops to 0. But the test asserts `len == 1`, so it would *fail loudly*, not silently — the regression is caught. The only residual is that `component=="encounter"` is a weak discriminant of emit-site, already noted as a dismissed low.

Fourth attack: a genuine region change in a region-mode world where the narrator drifts the title mid-move. The flag is set True only when `current_region == known_region_id` (same region) or the heading is an unresolved POI; a heading resolving to a *different* region sets the flag False and advances `current_region` — the sweep runs and the keep event does not (test_genuine_region_change_still_sweeps_scratch proves exactly this, including Wound persistence). No leak of walk-away semantics.

Fifth attack: performance/noise. One extra watcher event per same-region-drift turn in region-mode worlds. The encounter ladder already emits an analogous event on the same turns; this is symmetric and within the OTEL "every decision logged" doctrine. Conclusion: the attacks surface only the already-noted non-blocking test/doc nits; no production defect.

**Handoff:** To SM (Camina Drummer) for finish-story. Non-blocking test/doc nits (Boon assertion, stale RED-phase label, multi-PC test) recorded for an optional future touch — they do not gate this merge.

### Dispatch Tag Coverage

All 8 specialist tags accounted for (5 specialists disabled via `workflow.reviewer_subagents` settings — pre-filled Skipped in the Subagent Results table, not run this review):
- `[TEST]` — test-analyzer: 4 findings, 3 confirmed non-blocking / 1 dismissed (see Observations).
- `[DOC]` — comment-analyzer: 1 finding confirmed LOW (stale RED-phase docstring label).
- `[RULE]` — rule-checker: clean, 0 violations across 16 rules / 31 instances.
- `[EDGE]` — edge-hunter: disabled via settings; reviewer self-covered boundary analysis in Devil's Advocate (old_loc None, equal strings, genuine vs same-region change) — no edge defects.
- `[SILENT]` — silent-failure-hunter: disabled via settings; reviewer self-covered — the skip branch is explicitly logged + emits a watcher event (No Silent Fallbacks honored), no swallowed errors introduced.
- `[TYPE]` — type-design: disabled via settings; reviewer self-covered — no new types/signatures; existing annotations intact (rule-checker #3 clean).
- `[SEC]` — security: disabled via settings; reviewer self-covered — no new input surface; operates on trusted internal game state only (rule-checker #11 clean).
- `[SIMPLE]` — simplifier: disabled via settings; reviewer self-covered — the change is minimal (single gate + observability), deferred import tightened, no dead code or over-engineering.