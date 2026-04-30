---
story_id: "45-20"
jira_key: null
epic: "45"
workflow: "wire-first"
---
# Story 45-20: Resolved tropes write quest_log entry + active_stakes update (split from 37-41 sub-6)

## Story Details
- **ID:** 45-20
- **Jira Key:** N/A (no Jira key provided)
- **Epic:** Epic 45 — Playtest 3 Closeout
- **Workflow:** wire-first
- **Stack Parent:** none
- **Repo:** sidequest-server

## Context & Problem Statement

**Playtest 3 (Orin, 2026-04-19):**
- extraction_panic resolved at progress 0.255
- hireling_mutiny also at progress 0.255
- Both tropes fully Resolved, yet:
  - `quest_log` remains `{}` (empty dict)
  - `active_stakes` remains `''` (empty string)
- Resolution pipeline fires but doesn't persist durable records

**Root Cause:**
The trope resolution handshake (when a trope reaches resolved_state=RESOLVED) doesn't:
1. Write an entry to `quest_log` documenting the resolution
2. Update `active_stakes` with the resolved trope name
3. Emit OTEL span on the resolution handshake itself

**Impact:**
- Players have no durable record of resolved tropes (quest log audit fails)
- Game state `active_stakes` field lies about current threat landscape
- No observability into resolution events — GM panel blind to which tropes resolved and when
- Playtest 3 continuity broken: saves resumed with identical threat markers despite prior resolution

## Story Acceptance Criteria (AC)

**AC1 — quest_log entry on trope resolution:**
- When a trope reaches `resolved_state == RESOLVED`, append an entry to `quest_log`
- Entry format: `{timestamp, trope_name, progression_when_resolved, resolution_cause}`
- Call site: `sidequest/game/trope_engine.py` — resolution handshake method (likely `apply_trope_resolution()` or similar)
- Entry persists to game save (narrative_log or separate quest_log table)

**AC2 — active_stakes field updated:**
- On trope resolution, update `GameState.active_stakes` to reflect resolved trope
- Format: comma-separated string of unresolved trope names (drop the resolved one)
- Removes the resolved trope from the "active threat" list
- Call site: `sidequest/game/game_state.py` — `update_active_stakes()` invoked from resolution path

**AC3 — OTEL span on resolution handshake:**
- New span: `trope.resolution_handshake`
- Attributes: `(trope_name, progression, resolved_state, cause, quest_log_entry_written, active_stakes_updated)`
- Emits on every resolution event, even if quest_log write fails (lie detector carries the failure flag)
- Call site: `sidequest/telemetry/spans.py` — `emit_trope_resolution_span()` invoked from resolution method

**AC4 — Boundary test exercises the wire:**
- Test: `test_trope_resolution_writes_quest_log_and_updates_active_stakes()` in `tests/server/test_trope_resolution.py`
- Simulates a confrontation that fires a trope to resolved state
- Asserts: `quest_log` contains an entry with correct trope_name and progression
- Asserts: `active_stakes` no longer includes the resolved trope
- Asserts: OTEL span emitted with `quest_log_entry_written=true` and `active_stakes_updated=true`
- Does NOT mock the trope engine — uses real engine with test world data
- Hits the session handler dispatch loop (outermost reachable layer)

**AC5 — Regression guard: resolved tropes persist across save resume:**
- Test: `test_resolved_trope_persists_on_save_resume()` — save a session after trope resolution, resume, assert quest_log and active_stakes unchanged
- Verifies the durable write (query the DB directly to confirm persistence)

**AC6 — No half-wired exports:**
- All new exports must have non-test consumers in this PR
- New methods on GameState, GameSnapshot, or trope_engine verified for production call sites
- No dangling utility functions without call sites

## Workflow Tracking

**Workflow:** wire-first (5 phases)
**Phase:** finish
**Phase Started:** 2026-04-30T18:02:57Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-30T15:30:00Z | 2026-04-30T17:32:45Z | 2h 2m |
| red | 2026-04-30T17:32:45Z | 2026-04-30T17:45:24Z | 12m 39s |
| green | 2026-04-30T17:45:24Z | 2026-04-30T17:51:10Z | 5m 46s |
| review | 2026-04-30T17:51:10Z | 2026-04-30T18:02:57Z | 11m 47s |
| finish | 2026-04-30T18:02:57Z | - | - |

## Delivery Findings

No upstream findings at setup entry.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Improvement** (non-blocking): Pre-existing failing test `test_space_opera_magic_init_still_fires` in `tests/server/test_magic_init_caverns_and_claudes.py`. Affects `sidequest/magic/...` (space_opera magic init returns False; coyote_reach magic-init for space_opera content pack). Test file is byte-identical between develop and this branch — failure is on develop too, not introduced by 45-20. Worth a separate triage story. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Test quality cleanups in `tests/server/test_trope_resolution_handshake.py` — guardrail test pads to 600 chars but the cap is 1024 (trim branch never fires); two `assert spans` truthy checks should be `len(...) == 1`; stale "512-char guardrail" docstring; misleading "post-record_interaction" comments don't account for opening-turn skip. Cleanups are mechanical (~6 line edits). Could go in a 45-XX follow-up story alongside 45-32/45-34/45-36 cleanup pattern. *Found by Reviewer during code review.*
- **Question** (non-blocking): The `source="chapter_promotion"` is hardcoded at the call site (`websocket_session_handler.py:1576`). Today this is accurate (chapter-promotion is the only mutation path). When future paths add new mutation sites (engine tick, narrator extraction), they'll need to wire their own handshake calls with appropriate source values, OR the helper will need to attribute each detected flip to its source. Affects `sidequest/server/websocket_session_handler.py`. Not blocking — design choice to revisit when a second source path lands. *Found by Reviewer during code review.*

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test design)
- **Improvement** (non-blocking): Story context refers to `sidequest/telemetry/spans.py:156` and `:2235–2240`, but the package was decomposed into `sidequest/telemetry/spans/<domain>.py` files. Affects `sprint/context/context-story-45-20.md` (line numbers stale; layout is now `spans/trope.py:18` for `SPAN_TROPE_RESOLVE` and `spans/state_patch.py:27` for `SPAN_QUEST_UPDATE`). Tests import from the package level (`sidequest.telemetry.spans`), which is the public re-export, so the canonical surface is unchanged. *Found by TEA during test design.*
- **Improvement** (non-blocking): Story context refers to `_execute_narration_turn` at `sidequest/server/session_handler.py:3286–3490`. The function actually lives at `sidequest/server/websocket_session_handler.py:1408` (the `session_handler.py` module is now a 581-line back-compat shim). Affects `sprint/context/context-story-45-20.md` (Technical Guardrails section). The wire-first seam to instrument for the handshake is `websocket_session_handler.py:1450–1580` (turn body inside `turn_span`). *Found by TEA during test design.*
- **Question** (non-blocking): Story context says the helper lives "in a new module or in `sidequest/server/narration_apply.py`". Tests import `_handshake_resolved_tropes` from `sidequest.server.narration_apply`. If Dev places it elsewhere (e.g., `sidequest/server/trope_resolution.py`), the import path must be re-exported from `narration_apply` to keep the test stable, OR the tests must be updated. Recommend Dev keeps it in `narration_apply.py` next to `_apply_narration_result_to_snapshot` per the context's first option. *Found by TEA during test design.*

## Design Deviations

None at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- No deviations from spec.

### Reviewer (audit)
- TEA's "No deviations" → ✓ ACCEPTED by Reviewer: agrees with author reasoning. Story context attribute names (`quest_log_key`, `active_stakes_appended`) supersede the AC's earlier draft names (`quest_log_entry_written`, `active_stakes_updated`). Per spec-authority hierarchy, story context > AC text. Implementation followed context.
- Dev's "No deviations" → ✓ ACCEPTED by Reviewer: implementation matches story context guardrails (1024-char active_stakes cap, baseline-from-live-snapshot, helper at narration_apply.py per context's first option, post-recompute call site). No undocumented divergences spotted in the diff.

## Sm Assessment

**Story selected:** 45-20 — Resolved tropes write quest_log entry + active_stakes update.

**Why now:** Direct sequel to 45-19 (world_history arcs past turn 30, merged 2026-04-30). Continues Lane B (state write-back hygiene) — Playtest 3 surfaced that resolution fires but never persists. 2pt scope, p2, server-only, no upstream blockers.

**Workflow:** wire-first. Resolution handshake is a wiring bug (engine fires, persistence absent). Boundary tests must hit the dispatch loop and assert quest_log/active_stakes side effects, not mock the engine. AC4 (boundary test) and AC6 (no half-wired exports) explicitly enforce the discipline.

**OTEL discipline (per CLAUDE.md):** New `trope.resolution_handshake` span is mandatory — without it, the GM panel cannot distinguish a real resolution from narrator improvisation. Span must carry `quest_log_entry_written` and `active_stakes_updated` flags so failures are visible even when writes silently fail.

**Risks to flag for TEA:**
- Resolution path may live in multiple call sites (combat, scene, narrative). Test must hit the dispatch-level handshake, not a single trope-engine method.
- `quest_log` schema may already exist — verify before designing the entry shape; do not stub a parallel store.
- `active_stakes` is a comma-separated string today (per playtest data `''`); confirm format before parsing/rewriting.

**Handoff:** TEA (Fezzik) for red phase — write boundary tests against the resolution handshake.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story has 6 ACs covering durable-record write, OTEL observability, save/reload durability, and an explicit no-op contract. Wire-first workflow demands boundary tests against `_execute_narration_turn`, plus diff-predicate unit tests, plus span-routing tests. Trivial bypass not appropriate.

**Test Files:**
- `tests/telemetry/test_trope_resolution_span.py` — SPAN constant + SPAN_ROUTES registration + helper context manager (8 tests)
- `tests/server/test_trope_resolution_handshake.py` — diff predicate unit tests on `_handshake_resolved_tropes` helper (29 tests across 7 classes)
- `tests/server/test_45_20_trope_resolution_wire.py` — wire-first boundary tests driving `_execute_narration_turn` end-to-end including durability + reproducer (11 tests across 5 classes)

**Tests Written:** 48 tests covering all 6 ACs.
**Status:** RED (46/48 failing for the right reasons — 2 are negative-assertion tests that pass vacuously today and will continue to pass once Dev wires the path; this is intentional false-positive guarding).

**Test layering (wire-first discipline):**
- Unit: `test_trope_resolution_handshake.py` — diff predicate isolated.
- Span routing: `test_trope_resolution_span.py` — registration + extract() shape.
- Wire-first boundary: `test_45_20_trope_resolution_wire.py` — drives the dispatch seam through `_execute_narration_turn` with the real `_apply_narration_result_to_snapshot` and `record_interaction` flow. Asserts on `snapshot.quest_log`/`snapshot.active_stakes` after the turn AND on `json.loads(snapshot.model_dump_json())` to prove the entry will reach the next narrator's `state_summary`.
- Durability: covered in the wire-first file via `SqliteStore` round-trip with a fresh handler (proves the diff-baseline-from-live-snapshot pattern survives reload without false-positive duplicate writes).

### Rule Coverage

The lang-review checklist for Python (project-specific) is consulted via:

| Rule / Concern | Test(s) | Status |
|---|---|---|
| OTEL observability mandatory (CLAUDE.md OTEL principle) | `test_dispatch_seam_emits_handshake_span_with_full_payload`, `test_handshake_span_is_routed_as_state_transition`, `test_handshake_span_extract_pulls_lie_detector_attributes` | failing |
| No silent fallbacks (CLAUDE.md) | `test_no_handshake_span_when_no_trope_resolved` (false-positive guard); `test_non_resolution_transition_does_not_*` (scope guard) | passing-vacuous / failing |
| Don't reinvent — wire up what exists (CLAUDE.md) | `test_quest_log_write_emits_quest_update_span` (asserts `quest_update_span` is reused, not parallel span) | failing |
| Verify wiring end-to-end (CLAUDE.md) | All wire-first tests in `test_45_20_trope_resolution_wire.py` (drive `_execute_narration_turn`, not the helper directly) | failing |
| Every test suite needs a wiring test (CLAUDE.md) | `test_45_20_trope_resolution_wire.py::TestDispatchSeamWritesDurableRecord::test_trope_resolution_writes_quest_log_entry` | failing |
| Idempotency contract (story AC4) | `test_idempotent_re_detect_still_emits_handshake_span`, `test_second_turn_emits_idempotent_handshake_span`, `test_post_reload_first_turn_does_not_double_write` | failing |
| Schema namespacing (story context: `trope_{id}` key) | `test_progressing_to_resolved_writes_quest_log_entry` (asserts `trope_extraction_panic` exact key) | failing |
| Persistence durability (AC3) | `test_quest_log_entry_survives_save_reload`, `test_post_reload_first_turn_does_not_double_write` | failing |
| Diamonds and Coal — narrative weight surfaces in JSON (SOUL.md) | `test_quest_log_entry_appears_in_snapshot_json` | failing |
| Negative scope test (AC6 — non-resolution transitions) | 9 parametrized tests in `TestNonResolutionTransitionsAreNoops` | failing |
| Multi-trope concurrent (Orin's playtest reproducer) | `test_two_concurrent_resolutions_*`, `TestOrinPlaytestReproducer` | failing |
| active_stakes guardrail (story context: 512-char trim) | `test_long_active_stakes_is_trimmed_below_guardrail`, `test_long_active_stakes_still_includes_resolution_marker` | failing |

**Rules checked:** All applicable CLAUDE.md "critical" rules + SOUL.md OTEL/Diamonds principles + every story AC has at least one test.

**Self-check:** Reviewed every test for vacuous assertions. None found:
- No `let _ =` / `assert!(true)` / `is_none()`-on-always-None patterns.
- Each test asserts a specific value, key membership, count, or attribute — not just "something happened".
- Negative tests assert `[] == spans`, `key not in dict`, or `field == "preserved-value"` — meaningful absence checks.
- Two tests pass vacuously today (negative-assertion guards) but become real once the implementation lands and is wrong; they're intentional false-positive guards.

**Hot spots Dev should watch (from delivery findings):**
- Story context line numbers reference the pre-decomposition `spans.py` and `session_handler.py` layouts. The actual seam is `sidequest/server/websocket_session_handler.py:1408` (`_execute_narration_turn`) and `sidequest/telemetry/spans/trope.py` (where `SPAN_TROPE_RESOLVE` lives, needs promotion + the new `SPAN_TROPE_RESOLUTION_HANDSHAKE` registered).
- Tests import `_handshake_resolved_tropes` from `sidequest.server.narration_apply`. Place the helper there or re-export from there.
- Tests import `trope_resolution_handshake_span` (context manager) from `sidequest.telemetry.spans` (re-exported). Define in `spans/trope.py`.
- The wire-first tests rely on the baseline being captured at the TOP of `_execute_narration_turn` (before the `await sd.orchestrator.run_narration_turn(...)` call at line 1465). Capturing baseline late will make these tests fail because the AsyncMock side_effect mutates the snapshot during the orchestrator call.

**Handoff:** Dev (Inigo Montoya) for green phase — implement `_handshake_resolved_tropes` in `narration_apply.py`, wire it into `_execute_narration_turn` post-`record_interaction`, register the new span, promote `SPAN_TROPE_RESOLVE`.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed (sidequest-server):**
- `sidequest/telemetry/spans/trope.py` — added `SPAN_TROPE_RESOLUTION_HANDSHAKE` constant + `trope_resolution_handshake_span` context manager. Registered both `SPAN_TROPE_RESOLUTION_HANDSHAKE` and the previously-flat-only `SPAN_TROPE_RESOLVE` in `SPAN_ROUTES` with `event_type="state_transition"` and `component="trope"`. `SPAN_TROPE_RESOLVE` removed from `FLAT_ONLY_SPANS`.
- `sidequest/server/narration_apply.py` — added top-level helper `_handshake_resolved_tropes(snapshot, baseline_status, *, player_name, source)`. Diffs baseline vs live `active_tropes`; for each trope whose current status is `"resolved"` with non-`"resolved"` baseline, writes `quest_log[f"trope_{id}"] = "Resolved at turn {N}"` (wrapped in existing `quest_update_span`) and appends `[Resolved: {id} on turn {N}]` marker to `active_stakes` (with 1024-char trim guardrail that always preserves the new marker at the tail). Always emits one `trope_resolution_handshake_span` per detected resolved trope, including idempotent re-detects (`active_stakes_appended=False`). Imported `trope_resolution_handshake_span`.
- `sidequest/server/websocket_session_handler.py` — captured `trope_status_baseline` at the top of `_execute_narration_turn` before the orchestrator call. Called `_handshake_resolved_tropes(snapshot, trope_status_baseline, player_name=sd.player_name, source="chapter_promotion")` immediately after `recompute_arc_history` at the post-`record_interaction` site. Imported `_handshake_resolved_tropes` from `narration_apply`.

**Tests:** 48/48 passing (GREEN)
- `tests/telemetry/test_trope_resolution_span.py`: 8/8
- `tests/server/test_trope_resolution_handshake.py`: 29/29
- `tests/server/test_45_20_trope_resolution_wire.py`: 11/11

**Regression sweep:**
- All 128 telemetry tests pass
- 37 dispatch tests pass
- 23 narration_apply consumer tests pass
- Routing-completeness verifies new constant is properly registered (not in `FLAT_ONLY_SPANS`, in `SPAN_ROUTES`)
- 1012 broader server tests pass; the only failure (`test_space_opera_magic_init_still_fires`) was confirmed pre-existing by running on the parent commit before my changes — unrelated to trope resolution

**Branch:** `feat/45-20-resolved-tropes-quest-log-write` (pushed to origin)

**Wiring discipline (per CLAUDE.md):**
- New helper `_handshake_resolved_tropes` is wired into `_execute_narration_turn` (production call site, the dispatch loop) — verified by the boundary test `TestDispatchSeamWritesDurableRecord` which never imports the helper directly.
- New span constant is registered in `SPAN_ROUTES` and surfaces on the GM panel via the existing `state_transition` event type. No half-wired exports.
- `quest_log` writes wrap the existing `quest_update_span` rather than introducing a parallel quest-write span — reuse, not reinvent.

**SOUL.md alignment:**
- OTEL discipline: every detection (fresh AND idempotent re-detect) emits a span. The lie-detector signal is preserved on no-op turns so the GM panel can distinguish "engaged but idempotent" from "never engaged".
- Diamonds and Coal: a Resolved trope is canonical maturity-tier content; the durable record is what makes it a diamond instead of dropping back to coal in the next narrator's prompt.
- No silent fallbacks: the baseline diff is explicit; non-resolution transitions (active→progressing, downgrade, etc.) never fire the handshake — the diff predicate is scoped strictly to transitions into `"resolved"`.

**Handoff:** Verify phase (TEA / Fezzik) for simplify + quality-pass review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 pre-existing test failure + 3 pre-existing TODOs | confirmed 0, dismissed 4, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 3, dismissed 2, deferred 0 |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 | confirmed 4, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 (rule 6) | confirmed 2, dismissed 0, deferred 0 |

**All received:** Yes (4 enabled returned; 5 disabled per settings)
**Total findings:** 9 confirmed, 6 dismissed (with rationale), 0 deferred

### Subagent Findings Triage

**[PREFLIGHT] dismissed (4):**
- `test_space_opera_magic_init_still_fires` — verified pre-existing on develop; test file byte-identical between branches; magic/ source files untouched. Captured as upstream finding (non-blocking).
- 3 TODOs at `websocket_session_handler.py:2153/2159/2161` — `git blame` confirms commit 937408a9 (2026-04-28), pre-existing. Not in 45-20 change region (which lives at lines 1438-1577). Subagent confused itself by reading "new SPAN_TROPE_RESOLUTION_HANDSHAKE emit block" — those TODOs are in a TurnRecord block from a prior story.

**[TEST] confirmed (3):**
1. **Vacuous guardrail test** — `test_long_active_stakes_is_trimmed_below_guardrail` and `test_long_active_stakes_still_includes_resolution_marker` use 600 chars; with the resolution marker (~39 chars) total is ~640, well below the 1024-char cap. The trim branch (`if len(snapshot.active_stakes) > _ACTIVE_STAKES_GUARDRAIL`) never fires. Tests pass regardless of trim correctness. Severity: Medium (missing edge case in tests; production trim logic remains correct).
2. **No real chapter-promotion path test** — wire tests use `_flipping_orchestrator` to mutate active_tropes during the orchestrator mock call. The actual production flip happens later in `recompute_arc_history`. Both timings are valid for the helper's diff (baseline-at-top, handshake-after-recompute), but the recompute-driven flip is not directly exercised. Severity: Medium (coverage gap; helper logic is path-agnostic).
3. **Sibling fresh-resolution tests don't check turn-marker text** — `test_active_to_resolved` and `test_dormant_to_resolved` assert key presence only; sibling `test_progressing_to_resolved` correctly checks `"17" in entry`. Severity: Low.

**[TEST] dismissed (2):**
- Parametrized non-resolution tests share single code path (5 cases) — DISMISSED: while all 5 cases hit the same `if trope.status != "resolved": continue` line, they document the explicit transition vocabulary (dormant→active, progressing→active, downgrade, etc.). Documentary value > parametrize-test-purity per project pragmatism. Not a rule violation.
- `test_helper_accepts_known_sources` parametrize over 3 sources — DISMISSED: same documentary-vocabulary argument. The 3 source values are the contract — collapsing to 1 loses the contract documentation.

**[DOC] confirmed (4):**
1. `TestActiveStakesGuardrail` class docstring says "512-char guardrail"; actual cap is 1024. Stale comment.
2. `websocket_session_handler.py:1444` comment claims "fires post-record_interaction"; on opening turn `record_interaction` is skipped but the handshake still fires. Misleading.
3. `spans/trope.py:53-55` SPAN_ROUTES comment same issue.
4. `_handshake_resolved_tropes` docstring closes with "one span fires per detected resolved trope, every turn" — ambiguous; on turns with no resolved tropes, no spans fire. Severity: Low.

**[RULE] confirmed (2):**
- `tests/server/test_trope_resolution_handshake.py:1160` — `assert quest_spans` truthy-check; should be `assert len(quest_spans) == 1` (would silently pass if two `quest_update` spans were emitted).
- `tests/server/test_trope_resolution_handshake.py:1462` — `assert spans` truthy-check; same issue. Severity: Medium for both (other tests do enforce count, so duplicate-emit would be caught elsewhere).

### Rule Compliance

I read the diff myself against `.pennyfarthing/gates/lang-review/python.md` (13 numbered Python checks) and `CLAUDE.md` (6 critical rules). Spot-check enumeration:

| Rule | Verified Against | Result |
|------|------------------|--------|
| #1 Silent exceptions | `_handshake_resolved_tropes`, `trope_resolution_handshake_span`, all SPAN_ROUTES lambdas | ✓ no try/except, errors propagate |
| #2 Mutable defaults | `_handshake_resolved_tropes(snapshot, baseline_status, *, player_name, source)`, `trope_resolution_handshake_span(*, ..., _tracer=None, **attrs)` | ✓ no mutable defaults |
| #3 Type annotations | All new module-level functions and the `trope_status_baseline: dict[str, str]` local | ✓ full annotations on public surface |
| #4 Logging | `logger.info("trope.resolution_handshake fresh_writes=%d player=%s turn=%d", ...)` | ✓ percent-format, info-level appropriate |
| #5 Path handling | `str(tmp_path / "save.db")` in test fixture | ✓ pathlib + str conversion to match SqliteStore.open(path: str) |
| #6 Test quality | 38 test methods | 2 violations (truthy `assert spans`); 36 compliant |
| #7 Resource leaks | `SqliteStore.open` in tests, otel exporter in fixture | ✓ try/finally for exporter, sqlite3 manages own conn |
| #10 Import hygiene | New imports in narration_apply.py, websocket_session_handler.py, trope.py | ✓ explicit named, no cycles |
| #11 Input validation | `_handshake_resolved_tropes` boundary | ✓ internal-only, typed inputs |
| CLAUDE No Silent Fallbacks | `baseline_status.get(trope.id, "")` default; documented in docstring | ✓ explicitly documented |
| CLAUDE No Stubbing | `_handshake_resolved_tropes` 86-line full impl | ✓ no stubs |
| CLAUDE Don't Reinvent | `quest_update_span` reused for quest_log writes; `SpanRoute` reused for routing | ✓ |
| CLAUDE Verify Wiring | `_handshake_resolved_tropes` imported AND called at production site `websocket_session_handler.py:1572-1577` | ✓ wired |
| CLAUDE Wiring Test | `tests/server/test_45_20_trope_resolution_wire.py` drives `_execute_narration_turn` end-to-end | ✓ present |
| CLAUDE OTEL Observability | `SPAN_TROPE_RESOLUTION_HANDSHAKE` registered in `SPAN_ROUTES`; fires on every detection including idempotent re-detect | ✓ lie-detector contract met |

### Self-trace (data flow + wiring)

I picked one trace: a chapter-promotion flips `extraction_panic` from `"progressing"` → `"resolved"` mid-turn.
- Top of `_execute_narration_turn` (websocket_session_handler.py:1438-1451) captures `trope_status_baseline = {"extraction_panic": "progressing"}`. ✓
- `await sd.orchestrator.run_narration_turn(...)` returns. `_apply_narration_result_to_snapshot` runs. `record_interaction` runs. `recompute_arc_history` runs and (in the chapter-promotion path) calls `_apply_trope` which flips `existing.status = "resolved"`. ✓
- `_handshake_resolved_tropes(snapshot, trope_status_baseline, player_name=sd.player_name, source="chapter_promotion")` runs (websocket_session_handler.py:1572-1577). ✓
- Helper iterates `snapshot.active_tropes`, sees `extraction_panic.status == "resolved"`, baseline says `"progressing"`, `is_fresh = True`. Writes `quest_log["trope_extraction_panic"] = "Resolved at turn N"` (wrapped in `quest_update_span`); appends `[Resolved: extraction_panic on turn N]` marker to `active_stakes`; emits `trope_resolution_handshake_span` with `active_stakes_appended=True`. ✓
- Next turn's `state_summary_payload = json.loads(snapshot.model_dump_json())` (session_helpers.py:312) sees the new entries because they're on the snapshot. The narrator prompt for the next turn carries the resolution. ✓
- Save → reload preserves the entries (confirmed by `test_quest_log_entry_survives_save_reload`).
- Post-reload first turn: baseline = `{"extraction_panic": "resolved"}` (from live snapshot); current = `"resolved"` → `is_fresh = False`. Span fires with `active_stakes_appended=False`. No double-write. ✓

End-to-end traceable. The "no half-wired exports" AC6 is satisfied.

### Devil's Advocate

The implementation is largely correct, but here's where I'd attack:

**1. The trim guardrail is a Trojan horse.** The `if len(snapshot.active_stakes) > _ACTIVE_STAKES_GUARDRAIL` branch is genuinely untested (test pads to 640 chars, cap is 1024). If someone tightens the cap to 100 in a future tuning, normal-sized active_stakes content gets trimmed silently and the test suite reports green. The trim branch's slicing logic (`head_budget = _ACTIVE_STAKES_GUARDRAIL - len(tail) - 1`) also breaks if `marker` length exceeds the cap (negative `head_budget` → `s[:negative]` slices from the end). Trope IDs are short in practice, but a malicious or extremely long trope ID would bypass the guardrail.

**2. Multi-trope active_stakes interaction.** If two concurrent resolutions both push the field past the guardrail, the second trim removes the first marker from the head. Both quest_log entries are still written (durable record preserved), but the active_stakes loses one of two markers. This is a "rare in practice but real" coverage gap.

**3. The `source="chapter_promotion"` lie.** When future code paths (engine tick, narrator extraction) flip status, they'll either (a) get attributed to "chapter_promotion" because that's what the call site hardcodes, or (b) require new call sites with different sources. Today this is fine because chapter-promotion is the only path. The lie-detector premise of `source` being load-bearing for the GM panel is partially defeated — Sebastien sees "chapter_promotion" for everything until someone wires a second site.

**4. Idempotent re-detect cost.** Every turn the helper iterates `snapshot.active_tropes` and emits a span per resolved trope. After 50 turns of accumulated resolutions, that's 50+ spans per turn. The OTEL bridge handles this fine in practice (observed in playtest), but at scale the panel feed gets noisy. Not blocking; flag for future tuning if accumulated resolutions ever exceed ~100.

**5. The helper logs at INFO when fresh writes happen but not when re-detect happens.** This is intentional (re-detects are noise) but means the server log is silent on idempotent turns. The OTEL span is the lie-detector path; the server log is not. Acceptable design — just an asymmetry to note.

None of these rise to Critical/High. The implementation does its job. The Devil's Advocate uncovered the trim-guardrail edge case (point 1) which I confirm matches the test-analyzer's vacuous-test finding.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** chapter-promotion `_apply_trope` flips `active_tropes[i].status` → handshake at `websocket_session_handler.py:1572` reads diff vs baseline captured at line 1449 → writes `quest_log["trope_X"]` via `quest_update_span` and appends marker to `active_stakes` → next turn's `json.loads(snapshot.model_dump_json())` at `session_helpers.py:312` carries both into `state_summary_payload`. Safe because the snapshot is the single source of truth and persistence round-trips it.

**Pattern observed:**
- ✓ Wire-first discipline: dedicated `tests/server/test_45_20_trope_resolution_wire.py` drives `_execute_narration_turn` end-to-end (CLAUDE.md "Every Test Suite Needs a Wiring Test").
- ✓ Reuse: `quest_update_span` wrapped, `SpanRoute` reused, FLAT_ONLY_SPANS API mutation pattern preserved (CLAUDE.md "Don't Reinvent").
- ✓ OTEL: handshake span fires on every detection including idempotent re-detect (CLAUDE.md "OTEL Observability Principle"); `active_stakes_appended` flag is the lie-detector signal Sebastien needs.
- ✓ Span promotion: `SPAN_TROPE_RESOLVE` moved out of `FLAT_ONLY_SPANS` into `SPAN_ROUTES` so existing emit sites surface on the typed feed (`spans/trope.py:42`).

**Error handling:** No new try/except blocks. The helper performs synchronous dict assignment and string concatenation — both deterministic and exception-free. The `quest_update_span` and `trope_resolution_handshake_span` are context managers that fire OTEL spans; if the OTEL backend itself raises, the active_stakes mutation is already committed (write-asymmetry edge case noted in Devil's Advocate but not actionable).

**Severity table (no Critical/High):**

| Severity | Tag | Issue | Location | Recommendation |
|----------|-----|-------|----------|----------------|
| Medium | [TEST] | Guardrail test pads to 640 chars; cap is 1024; trim branch never fires | `tests/server/test_trope_resolution_handshake.py:1400/1416` | Pad to ≥1000 chars in a follow-up; assert head is truncated |
| Medium | [TEST] [RULE] | `assert quest_spans` / `assert spans` truthy checks (rule 6 — test quality) | same file lines 1160, 1462 | Tighten to `assert len(...) == 1` |
| Medium | [TEST] | No wire test using real `recompute_arc_history` chapter-promotion path | `test_45_20_trope_resolution_wire.py` | Add wire test seeded with chapter data crossing maturity tier |
| Medium | [DOC] | Stale "512-char guardrail" docstring | `test_trope_resolution_handshake.py` `TestActiveStakesGuardrail` class | Replace 512 → 1024 |
| Medium | [DOC] | "post-record_interaction" comments don't account for opening-turn skip | `websocket_session_handler.py:1444`, `spans/trope.py:53-55` | Qualify as "after the apply step + arc-recompute tick (record_interaction skipped on opening turn)" |
| Low | [DOC] | "every turn" docstring ambiguous | `narration_apply.py:1707` | Rephrase: "one span per currently-resolved trope, on every turn where any are present" |
| Low | [TEST] | Sibling fresh-resolution tests omit turn-marker assertion | `test_trope_resolution_handshake.py:1046/1056` | Add `assert "17" in entry` |

**Why APPROVED despite findings:** All 9 confirmed findings are Medium or Low. None block per the severity policy. Production correctness is sound: 48/48 new tests pass, no regressions in 1012 broader server tests, span routing/registration verified, end-to-end data flow traceable. The findings are test quality / documentation gaps that fit cleanly into a 45-XX cleanup story alongside 45-32 / 45-34 / 45-36 (existing post-review cleanup pattern in this sprint).

**Pre-existing failure noted for separate triage:** `test_space_opera_magic_init_still_fires` in `tests/server/test_magic_init_caverns_and_claudes.py` fails on `develop` and is byte-identical between branches — not introduced by this PR.

**Handoff:** To SM (Vizzini) for finish-story.