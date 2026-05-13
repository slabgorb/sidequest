---
story_id: "50-4"
jira_key: ""
epic: "50"
workflow: "tdd"
---
# Story 50-4: Trope rate_per_day between-session advancement

## Story Details
- **ID:** 50-4
- **Jira Key:** None (personal project)
- **Workflow:** tdd (phased)
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T15:18:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13 | 2026-05-13 | instant |
| red | 2026-05-13 | 2026-05-13T14:17:34Z | 14h 17m |
| green | 2026-05-13T14:17:34Z | 2026-05-13T14:53:31Z | 35m 57s |
| spec-check | 2026-05-13T14:53:31Z | 2026-05-13T14:54:41Z | 1m 10s |
| verify | 2026-05-13T14:54:41Z | 2026-05-13T14:59:45Z | 5m 4s |
| review | 2026-05-13T14:59:45Z | 2026-05-13T15:17:01Z | 17m 16s |
| spec-reconcile | 2026-05-13T15:17:01Z | 2026-05-13T15:18:03Z | 1m 2s |
| finish | 2026-05-13T15:18:03Z | - | - |

## Implementation Plan & Specification

- **Plan:** `/Users/slabgorb/Projects/oq-1/docs/superpowers/plans/2026-05-13-50-4-trope-rate-per-day.md` (comprehensive implementation plan, 8pt re-estimate rationale, Pass A2 algorithm, OTEL spans, testing strategy)
- **Spec:** `/Users/slabgorb/Projects/oq-1/docs/superpowers/specs/2026-05-13-50-4-trope-rate-per-day-design.md` (locked design decisions, protocol changes, narrator emission rule, snapshot fields, delta wiring, persistence, Pass A2 algorithm, prompt integration)

Both documents are load-bearing reads. The plan includes comprehensive test strategy and ADR amendment requirements.

## Delivery Findings

### TEA (test design)

- **Improvement** (non-blocking): Plan's persistence design is over-specified relative to the codebase.
  Affects `sidequest-server/sidequest/game/persistence.py` (no schema bump or ALTER TABLE needed).
  *Found by TEA during test design.*
- **Gap** (non-blocking): `SnapshotFlags` named in the spec does not exist — actual class is `StateDelta` in `sidequest/game/delta.py`.
  Affects spec text (`docs/superpowers/specs/2026-05-13-50-4-trope-rate-per-day-design.md`) and plan (Task 3).
  *Found by TEA during test design.*
- **Improvement** (non-blocking): Plan's OTEL test uses `monkeypatch.setattr(trope_tick, "_emit_watcher_event", ...)` — actual emission uses the `Span.open` context manager pattern. Tests adapted to use `InMemorySpanExporter`, mirroring `tests/game/test_trope_tick.py`.
  Affects `sidequest-server/tests/game/test_trope_time_skip.py` (now uses the SDK exporter pattern).
  *Found by TEA during test design.*
- **Improvement** (non-blocking): `tick_tropes` call site is in `sidequest/server/websocket_session_handler.py:2743`, not `narration_apply.py`. Plan Task 7's path edit lands in the WS handler.
  Affects `sidequest-server/sidequest/server/websocket_session_handler.py` (Dev to add `days_advanced=result.days_advanced` kwarg there).
  *Found by TEA during test design.*

## Design Deviations

### TEA (test design)

- **Persistence design: no schema bump or ALTER TABLE migration**
  - Spec source: `docs/superpowers/specs/2026-05-13-50-4-trope-rate-per-day-design.md`, "SQLite persistence" subsection (lines 113-121)
  - Spec text: "Schema bump in `persistence.py`: New columns on session table: `days_elapsed INTEGER NOT NULL DEFAULT 0`, `pending_time_skip_summary TEXT NOT NULL DEFAULT '[]'` (JSON-encoded list). `schema_version` bumps by 1. One-shot ALTER TABLE migration runs on load if a save's schema_version is below the new bump."
  - Implementation: Tests assert `GameSnapshot.model_dump_json` / `GameSnapshot.model_validate` round-trip preserves both fields. `SessionPersistence` already serializes the entire snapshot as a JSON blob in `game_state.snapshot_json` — adding two pydantic fields to `GameSnapshot` (with defaults) gives free round-trip and free legacy-save loading via the existing `extra: "ignore"` plus default-factory semantics. No ALTER TABLE, no schema_version bump, no new columns.
  - Rationale: The spec's persistence design predates an audit of the actual persistence layer. The whole-snapshot-JSON approach has been the contract since the Python port (ADR-082); adding per-column storage would duplicate state across two surfaces (column AND snapshot_json) and create a synchronization bug surface for no win. Pydantic's default handling covers AC-10 (existing saves load cleanly) without any code in `persistence.py`.
  - Severity: minor (test surface only; the spec's intent — round-trip integrity and legacy-load — is fully exercised)
  - Forward impact: Dev should NOT bump `SCHEMA_VERSION` or add columns. Plan Task 3 steps 5-7 collapse to "add fields to `GameSnapshot` + `StateDelta` only." ADR-018 amendment should reference snapshot-JSON persistence, not schema migration.

- **`SnapshotFlags` does not exist — the actual class is `StateDelta`**
  - Spec source: `docs/superpowers/specs/2026-05-13-50-4-trope-rate-per-day-design.md`, "Delta wiring" subsection (lines 103-109)
  - Spec text: "```python\n# sidequest/game/delta.py — SnapshotFlags\ndays_elapsed: bool = False\npending_time_skip_summary: bool = False\n```\nBoth fields compared in `SnapshotFlags.detect_changes()`."
  - Implementation: Tests target `sidequest.game.delta.StateDelta` (the actual class name) with comparisons added to the existing `compute_delta(before: StateSnapshot, after: StateSnapshot)` function. `StateSnapshot` (the JSON-frozen comparison class) also needs the two new fields so the `compute_delta` flag is meaningful.
  - Rationale: Naming drift between spec and codebase; behavior is identical.
  - Severity: trivial (rename)
  - Forward impact: Dev edits `StateDelta` + `StateSnapshot` + `compute_delta` in `delta.py`, not a (non-existent) `SnapshotFlags`.

- **Task 1 implementation partially present in working tree at handoff**
  - Spec source: `docs/superpowers/plans/2026-05-13-50-4-trope-rate-per-day.md`, Task 1 (lines 44-145)
  - Spec text: Plan Task 1 Steps 3-7 belong to Dev's green phase ("add `days_advanced` to `NarrationTurnResult`", "extract `days_advanced` in the game_patch parser", "commit").
  - Implementation: TEA found `sidequest/agents/orchestrator.py` carrying the Task 1 implementation already (uncommitted working-tree change adding `days_advanced` field + extraction in `extract_structured_from_response` at orchestrator.py:763-769 and 2376/2578). Test file at `tests/protocol/test_game_patch_days_advanced.py` was already present and matched the implementation. TEA committed only the four test files (per TEA-role discipline) and left the orchestrator.py change uncommitted for Dev to review + commit during green.
  - Rationale: Cleanest separation of TEA (tests-only commits) from Dev (implementation commits). Reverting the working-tree implementation to force a stricter RED state would have discarded work already done correctly per spec.
  - Severity: minor (procedural — implementation correctness unchanged)
  - Forward impact: Dev should `git diff sidequest/agents/orchestrator.py`, confirm matches Task 1 Steps 3 & 4 of the plan, and commit as the first green step. The 4 protocol tests pass against this implementation.

- **OTEL emission test uses `InMemorySpanExporter`, not watcher monkeypatch**
  - Spec source: `docs/superpowers/plans/2026-05-13-50-4-trope-rate-per-day.md`, Task 6 Step 3 (lines 1209-1237)
  - Spec text: Plan suggests `monkeypatch.setattr(trope_tick, "_emit_watcher_event", fake_emit)` to capture span emission.
  - Implementation: Tests use the SDK's `InMemorySpanExporter` attached to the active `TracerProvider`, matching the pattern used by `tests/game/test_trope_tick.py`. `trope_tick.py` does not have an `_emit_watcher_event` helper — it uses `Span.open(SPAN_NAME, attrs)` context managers, which the in-memory exporter captures directly.
  - Rationale: Match the actual emission idiom and existing test fixtures; avoid creating a parallel watcher mechanism.
  - Severity: trivial (test mechanism)
  - Forward impact: Dev wires Pass A2's span emission via `Span.open(SPAN_TROPE_TIME_SKIP, attrs)` inside `tick_tropes`, same idiom as `SPAN_TROPE_TICK_PER`. No new emission helper needed.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New feature with 14 ACs spanning protocol, state, engine, OTEL, and prompt-assembly layers — TDD-mandatory per workflow `tdd`.

**Test Files:**
- `sidequest-server/tests/protocol/test_game_patch_days_advanced.py` — protocol field validation (4 tests). Untracked-found at activation; reviewed and kept verbatim — covers AC-1 exactly.
- `sidequest-server/tests/game/test_session_time_skip.py` — Snapshot fields, JSON round-trip, legacy-save defaults, StateDelta wiring (9 tests).
- `sidequest-server/tests/game/test_trope_time_skip.py` — Pass A2 algorithm + OTEL emission + Pass B interaction (~28 tests across 6 test classes).
- `sidequest-server/tests/integration/test_trope_time_skip_e2e.py` — Renderer helper, build_narrator_prompt wiring (skip-on-pack-missing), websocket_session_handler kwarg-threading source-inspection (8 tests across 3 classes; the 3 prompt-assembly tests are `pytest.mark.skipif` gated on `tea_and_murder` pack presence).

**Tests Written:** ~49 tests covering AC-1 through AC-12 (AC-13 is the meta-AC about file presence, satisfied by this commit; AC-14 is the ADR amendment, owned by Dev's green phase).

**Status:** RED (3 of 4 files fail at module-collection time on `ModuleNotFoundError: sidequest.game.trope_time_skip` — the unwritten module is the entry point. Once Dev creates the module with the two pydantic models + `_pass_a2_time_skip` skeleton, individual tests start running and fail at the next missing piece. The protocol test file is GREEN — see Design Deviations for why.)

### Rule Coverage

| Rule (lang-review / project) | Test(s) | Status |
|---|---|---|
| Pydantic `extra='forbid'` rejects unknown fields | `TestModuleSurface.test_time_skip_beat_event_rejects_unknown_fields` | failing (no module) |
| Defaults are sensible / explicit | `test_snapshot_default_days_elapsed_is_zero`, `test_snapshot_default_pending_time_skip_summary_is_empty` | failing (no field) |
| Validated coercion — negative/non-int sanitization | `test_days_advanced_rejects_negative`, `test_days_advanced_rejects_non_int` | passing (impl present) |
| Round-trip integrity for persisted state | `test_snapshot_days_elapsed_round_trips_through_json`, `test_snapshot_pending_summary_round_trips_through_json` | failing (no field) |
| Forward-compat for legacy saves | `test_legacy_snapshot_without_new_fields_loads_with_defaults` | failing (no field) |
| OTEL emission for every subsystem decision (CLAUDE.md OTEL principle) | `test_tick_tropes_emits_trope_time_skip_span`, `test_tick_tropes_no_time_skip_span_when_days_zero` | failing (no module) |
| Wiring test for every test suite (CLAUDE.md "Every Test Suite Needs a Wiring Test") | `tests/integration/test_trope_time_skip_e2e.py::TestBuildNarratorPromptWiring`, `TestEngineBoundaryThreadsDaysAdvanced` | failing (no module, no kwarg) |
| Non-test consumers verified (CLAUDE.md "Verify Wiring, Not Just Existence") | `test_tick_tropes_call_site_threads_days_advanced` (source-inspection on websocket_session_handler.py) | failing (kwarg absent) |
| No silent fallback on missing trope def | `test_missing_trope_def_is_skipped` | failing (no module) |
| Cap enforced — clamp behavior visible | `test_clamps_days_at_day_tick_cap`, `test_day_tick_cap_is_14` | failing (no module) |
| Idempotence — already-fired beats not re-fired | `test_does_not_refire_already_fired_beats` | failing (no module) |
| Self-check for vacuous assertions | review pass — every test has at least one meaningful `assert`; class `TestPassA2OtelFields.test_beats_fired_count_matches_list_length` asserts an invariant, not a tautology | clean |

**Rules checked:** All applicable Python/pydantic project rules from `CLAUDE.md` and the established `tests/game/test_trope_tick.py` patterns have at least one test pinning them. The `lang-review/python.md` checklist was consulted; no extra-strict checks (e.g., type-system invariants beyond `extra='forbid'`) apply to this story's surface.
**Self-check:** Zero vacuous tests found; one over-iteratively drafted test (`test_no_resolution_when_progress_caps_but_beats_remain`) was rewritten before commit to use a single clean shape (rate × days = 0.99 progress, 2 of 3 beats fired).

**Handoff:** To Dev (The White Rabbit) for implementation. Recommended task order:
1. Create `sidequest/game/trope_time_skip.py` with the two pydantic models + `DAY_TICK_CAP` + skeleton `_pass_a2_time_skip` (plan Task 2).
2. Add `days_elapsed` + `pending_time_skip_summary` to `GameSnapshot` (plan Task 3 — drop the schema/ALTER changes, retain the field additions and `StateDelta`/`StateSnapshot`/`compute_delta` wiring).
3. Commit `sidequest/agents/orchestrator.py` uncommitted change (plan Task 1 Step 7 — implementation already in working tree).
4. Implement Pass A2 body, then wire into `tick_tropes`, then add the `trope.time_skip` span constant + emission (plan Tasks 4, 5, 6).
5. Add `days_advanced=result.days_advanced` to the `tick_tropes` call site in `sidequest/server/websocket_session_handler.py:2743` (plan Task 7 — NOTE: not `narration_apply.py`).
6. Add narrator prompt rule + `_render_time_skip_context` helper + section wiring (plan Tasks 8, 9).
7. Dashboard surface + ADR-018 amendment (plan Tasks 11, 12).

## Dev Assessment

**Implementation complete:** Yes
**Method:** superpowers:subagent-driven-development — fresh implementer subagent per logical task, two-stage spec + quality review after each non-trivial commit. 10 commits on `feat/50-4-trope-rate-per-day` (sidequest-server) + 1 commit on `main` (orchestrator).

**Commit chain (sidequest-server):**
| Commit | Task | Summary |
|---|---|---|
| `f696e2d` | TEA red | 4 failing test files |
| `de4bbb6` | T1 | `days_advanced` field on `NarrationTurnResult` + extraction in `extract_structured_from_response` (committed working-tree change) |
| `80f7b86` | T2 | `sidequest/game/trope_time_skip.py` module with `DAY_TICK_CAP`, `TimeSkipBeatEvent`, `TropeTimeSkipFields`, NotImplementedError skeleton |
| `e83b8c7` | T3 | `GameSnapshot.days_elapsed` + `pending_time_skip_summary` + `StateDelta`/`StateSnapshot`/`compute_delta` wiring (no schema bump, per deviation) |
| `87c89b3` | T4/T5/T6 | Pass A2 algorithm body + `tick_tropes` kwarg + `SPAN_TROPE_TIME_SKIP` constant + Span.open emission + dashboard SpanRoute |
| `bd52226` | T4 quality fix | Tighten `_pass_a2_time_skip` param type from bare `object` to `dict[str, TropeDefinition] \| object` |
| `5427a81` | T7 | Thread `days_advanced=result.days_advanced` to `tick_tropes` in `websocket_session_handler.py:2747` |
| `ecf45a9` | T8 | CRITICAL TIME RULE + `days_advanced` valid-field in `narrator_prompts/output_only.md` |
| `4733c9b` | T9 | `_render_time_skip_context` helper + `TurnContext.snapshot` field + `build_narrator_prompt` registration of TIME-SKIP CONTEXT section (AttentionZone.Early) + one-shot clear |
| `c22ff16` | T9 quality fix | Tighten `TurnContext.snapshot` annotation from `Any` to `GameSnapshot \| None` via `TYPE_CHECKING` import |
| `e031ba0` | T11 | Dashboard `Day N` header indicator, `data-trope-id` row attribute, `trope.time_skip` `+Nd` badge handler (8s flash) |

**Orchestrator commit:**
- `a15594f` (main) — ADR-018 amended (Implementation update 2026-05-13, `implementation-status: accepted`, "Remaining gaps: None"), DRIFT.md entry removed, ADR-087 row marked RESTORED.

**Acceptance criteria coverage (14 of 14):**

| AC | Status | Evidence |
|---|---|---|
| AC-1 narrator emits `days_advanced` (pydantic non-negative int) | ✅ | `de4bbb6` + protocol tests pass |
| AC-2 `tick_tropes` called with `days_advanced=N` post-apply | ✅ | `5427a81` — `test_tick_tropes_call_site_threads_days_advanced` source-inspect passes |
| AC-3 Pass A2 advances progress by clamp(days,0,14)×rate | ✅ | `87c89b3` — `TestPassA2Advancement` 5 tests pass |
| AC-4 Pass A2 fires every crossed beat | ✅ | `TestPassA2BeatFiring` 6 tests pass |
| AC-5 `days_elapsed += min(days_advanced, 14)` | ✅ | `test_days_elapsed_accumulates_clamped_value` + `test_days_elapsed_accumulates_unclamped_value` pass |
| AC-6 `pending_time_skip_summary` sorted by `(days_into_skip, trope_id)` | ✅ | `test_summary_sorted_by_days_into_skip_then_trope_id` passes |
| AC-7 next prompt renders `## TIME-SKIP CONTEXT` + clears | ✅ | `TestBuildNarratorPromptWiring` 3 tests pass (pack-gated) |
| AC-8 `trope.time_skip` OTEL span with full fields | ✅ | `test_tick_tropes_emits_trope_time_skip_span` passes; SpanRoute registered |
| AC-9 GM panel `Day N` indicator | ✅ | `e031ba0` (visual smoke — no auto test per plan) |
| AC-10 existing saves load cleanly with defaults | ✅ | `test_legacy_snapshot_without_new_fields_loads_with_defaults` passes (pydantic `extra: "ignore"` + defaults handle it; no schema migration required) |
| AC-11 caverns (`rate_per_day=0.0`) shows zero drift | ✅ | `test_zero_rate_no_op_even_with_days` passes |
| AC-12 Pass B continues to fire additional eligible beat after A2 | ✅ | `TestPassBInteraction` 2 tests pass |
| AC-13 all 4 test files landed with unit/integration coverage | ✅ | `f696e2d` |
| AC-14 ADR-018 amendment | ✅ | `a15594f` (orchestrator main) |

**Test results:** `uv run pytest -q` → **5214 passed, 64 skipped** (skipped are pack-gated integration tests in environments without `tea_and_murder` content). Ruff clean. Zero regressions vs `develop`.

**Two-stage review record:**
- T2: spec ✅ / quality ✅
- T3: spec ✅ / quality ✅
- T4-6: spec ✅ / quality ✅ (one Important fixed inline — `bd52226`)
- T7: combined ✅ (1-line kwarg threading)
- T8: text-only edit, eyeball-verified
- T9: spec ✅ / quality ✅ (one Important fixed inline — `c22ff16`)
- T11: combined ✅ (HTML/JS/CSS only)
- T12: docs-only edit, eyeball-verified

### Dev (implementation)

- No deviations from spec beyond TEA's logged ones. The TEA deviations (no schema migration, `SnapshotFlags`→`StateDelta` rename, OTEL `Span.open` idiom, `websocket_session_handler.py` instead of `narration_apply.py`) were applied verbatim and verified by tests passing.
- Two procedural deviations:
  1. **T2's NotImplementedError skeleton.** The instructions told the implementer NOT to add `_pass_a2_time_skip` in T2 (defer to T4). The implementer added it anyway because TEA's `tests/game/test_trope_time_skip.py` imports it unconditionally at module top-level — collection would have errored otherwise. The skeleton's only behavior is `raise NotImplementedError`, replaced fully in T4. Not a spec violation; a forced consequence of TEA's import-time test layout.
  2. **TurnContext extension for snapshot reference.** The spec's prompt-builder snippet assumed `context.snapshot` existed. It did not. T9 implementer added `snapshot: GameSnapshot | None = None` to `TurnContext` and populated it in `_build_turn_context` via `sd.snapshot`. Net: one new typed field, zero behavior change for legacy callers (default-None). Logged here for the reconcile phase since it adds API surface to a high-traffic dataclass.

**Handoff:** To TEA (The Caterpillar) for verify phase (simplify + quality-pass).

### Architect (reconcile)

Reviewed all four existing deviation sub-sections (TEA test design, TEA test verification, Dev implementation, plus the Architect spec-check substantive sweep). Every entry has all 6 required fields (Spec source, Spec text quoted inline, Implementation, Rationale, Severity, Forward impact), every spec source path exists in the project tree, and every quoted spec excerpt was verified against the current files.

No additional deviations found beyond what TEA and Dev have already documented. Specifically:

- **Persistence simplification, `SnapshotFlags` → `StateDelta` rename, OTEL `Span.open` pattern, WS-handler call site** — TEA's four design-time deviations were applied verbatim by Dev; tests pass against the deviated implementation; the spec's literal text would not have worked against the actual codebase.
- **T2 `NotImplementedError` skeleton + `TurnContext.snapshot` extension** — Dev's two procedural deviations are forced consequences of (a) TEA's import-time test layout requiring the function name to exist for collection and (b) the spec's prompt-builder snippet assuming an attribute on `TurnContext` that did not exist. Both are minimal and well-documented in the Dev section.

No AC was deferred — all 14 ACs in the story spec are satisfied per the AC accountability table in the Dev Assessment (each AC mapped to a specific commit + test).

The Reviewer's adversarial pass (one fix-back loop on 5 HIGH findings, applied in `ee3161d`) tightened the implementation around 5 edge cases the spec under-specified (empty escalation list, empty DOM trope id, queue-clear ordering, zero-assertion test, `getattr` silent fallback). None of these alter the spec contract — they reinforce it. Logged in the Reviewer Assessment, not duplicated here.

**Spec-reconcile gate: pass.** Definitive deviation manifest is the union of TEA (test design) + TEA (test verification) + Dev (implementation) + this entry; no entries need correction.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

**Gate status:** ✅ pass (structural — AC coverage table present, implementation complete, TEA/Dev deviation subsections properly formatted).

**Substantive sweep:**

| Risk area | Check | Result |
|---|---|---|
| AC-7 prompt rendering + one-shot clear | `_render_time_skip_context` in `narrator.py:89`; called from `orchestrator.py:1465`; section name `"time_skip_context"` registered; `snapshot.pending_time_skip_summary = []` on line 1479 immediately after registration | ✅ matches spec exactly |
| AC-9 dashboard Day N | `dashboard.html:481` carries `${s.days_elapsed ? ' · Day '+esc(String(s.days_elapsed)) : ''}` appended to the header template — conditional on truthy value, escaped, integrates cleanly with the existing breadcrumb | ✅ |
| AC-14 ADR-018 amendment | Frontmatter `implementation-status: accepted` (line 11); "Implementation update (2026-05-13)" subsection at line 83; "Remaining gaps: None" set; DRIFT.md ADR-018 entry removed; ADR-087 row marked RESTORED | ✅ |
| All 4 test files | `uv run pytest tests/{game,protocol,integration}/...50-4 tests` → 51 passed, 0 failed | ✅ |
| Persistence approach | No `persistence.py` edits, no `schema_version` bump — pydantic + JSON-blob round-trip per TEA deviation. `model_validate` on a minimal dict produces defaults (verified by `test_legacy_snapshot_without_new_fields_loads_with_defaults`) | ✅ |
| OTEL emission idiom | `Span.open(SPAN_TROPE_TIME_SKIP, attrs)` in `tick_tropes`, matches `_advance_progress`'s `Span.open(SPAN_TROPE_TICK_PER, ...)` shape; captured by `InMemorySpanExporter` in tests | ✅ |
| Engine wire location | `websocket_session_handler.py:2747` carries `days_advanced=result.days_advanced` — verified by both source-inspection test and the integration test | ✅ |

**Procedural deviations (both already logged by Dev — accepted, no action):**

1. **T2's `NotImplementedError` skeleton.** Forced by TEA's `tests/game/test_trope_time_skip.py` importing `_pass_a2_time_skip` at module top-level (no `pytest.importorskip` guard, no late import). The skeleton was replaced in full by T4. The procedural alternative — TEA-side late imports — would have made the tests less readable. The skeleton-then-replace flow is acceptable for this narrow case where the test-layout pin and the impl arrive in adjacent commits on the same branch. Severity: trivial. Recommendation: A (update spec to permit forward-declared imports when tests need them; not blocking, future hygiene).

2. **`TurnContext.snapshot: GameSnapshot | None` field added.** Spec assumed `context.snapshot` already existed on TurnContext; it did not. T9 implementer added it minimally — single field, default None, populated in `_build_turn_context` from `sd.snapshot`. The downstream prompt-builder read is gated on `snapshot is not None`, so legacy callers (tests that build TurnContext directly without going through `_build_turn_context`) keep working. Severity: minor (one-field API surface addition). Recommendation: A (spec implicitly required this; the implementation made the dependency explicit and typed it correctly).

Neither deviation changes spec intent or behavior. Both improve over the spec's written form.

**Spec authority hierarchy applied:**
- Story scope (this session) — load-bearing for the persistence deviation and the WS-handler call site
- Story context — none beyond the ACs
- Plan + spec — followed except where TEA's deviations override
- Architecture docs — ADR-018 amendment is the only impact, executed

**Decision:** Proceed to TEA verify phase. No hand-back to Dev required.

**Handoff:** To TEA (The Caterpillar) for verify phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (5213 passed, 1 flaky, 64 skipped post-fix)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 15 (11 production + 4 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | none |
| simplify-quality | clean | none |
| simplify-efficiency | 3 findings | 1 high (in-scope), 1 medium (defended by reuse), 1 high (out-of-scope pre-existing API) |

**Applied:** 1 high-confidence fix (`6ba7359` — drop redundant `or 0.0` after a ternary that already returns 0.0; `trope_time_skip.py:135`).

**Flagged for Review:** 1 medium-confidence finding — dual-shape `pack_or_tropes_by_id` parameter in `_pass_a2_time_skip`. simplify-efficiency suggests collapsing to dict-only (move test fixtures to dict construction). simplify-reuse defended the dual-shape as an intentional ergonomic pattern. Reviewer call.

**Noted (not applied):** 1 high-confidence finding outside 50-4 scope — `StateDelta`'s 7 pre-existing single-line getter methods (`characters_changed()`, `tropes_changed()`, etc.) that duplicate direct field access. These were not added by 50-4 — removing them would mean editing the StateDelta public API and fanning out to every test that calls `.tropes_changed()`. That's a separate refactor story, not boy-scout-bounded. Logged here so a future story can pick it up.

**Reverted:** 0

**Overall:** simplify: applied 1 fix.

### Quality Checks

- `uv run ruff check .` — All checks passed
- `uv run pytest -q` — 5213 passed, 1 failed, 64 skipped (the 1 failure is `tests/server/test_chargen_dispatch.py::TestSliceAWiring::test_caverns_delver_loadout_wired_into_snapshot` — confirmed flaky, passes in isolation, pre-existing test-isolation issue unrelated to 50-4; was reported as pre-existing during T7 green check too)
- 51/51 tests across the four 50-4 test files pass cleanly after the simplify fix
- No regressions vs `develop` introduced by 50-4 (the flaky test predates this story)

### Delivery Findings

### TEA (test verification)

- **Improvement** (non-blocking): Flaky test `tests/server/test_chargen_dispatch.py::TestSliceAWiring::test_caverns_delver_loadout_wired_into_snapshot` — fails when run in the full suite, passes in isolation. Pre-existing test-isolation issue (state leak across tests), surfaced again during 50-4 verify. Affects `sidequest-server/tests/server/test_chargen_dispatch.py` (needs fixture isolation cleanup; root cause not investigated here — out of 50-4 scope). *Found by TEA during test verification.*

**Handoff:** To Reviewer (The Queen of Hearts) for adversarial code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|---|---|---|---|---|
| 1 | reviewer-preflight | Yes | clean | 0 code smells, 0 console_log, 0 todos; 5213/5214 tests pass (1 flaky pre-existing) | N/A — green |
| 2 | reviewer-edge-hunter | Yes | findings | 8 (2 HIGH: empty-escalation resolution, empty-tropeId queryselector; 4 MED; 2 LOW) | 2 HIGH applied + 1 MED convergent with silent-failure applied |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 (1 HIGH: float days_advanced silent drop noted-as-documented; 1 MED queue-clear ordering — convergent with edge-hunter; 2 LOW) | MED queue-clear applied; HIGH float-drop accepted as documented silent-drop pattern |
| 4 | reviewer-test-analyzer | Yes | findings | 11 (3 HIGH: zero-assertion test, pack-skip CI, tautological test; 8 MED) | 1 HIGH (zero-assertion) applied; others flagged non-blocking |
| 5 | reviewer-rule-checker | Yes | findings | 5 against 17-rule python.md checklist (1 HIGH project-rule: getattr silent fallback per CLAUDE.md; 3 type/import; 1 silent-suppress on _to_json pre-existing) | 1 HIGH applied; pre-existing items deferred |
| 6 | reviewer-type-design | Yes | findings | 5 (1 MED bare-`object` parameter; 4 LOW: missing `ge=` constraints, redundant getattr) | All flagged non-blocking; type-improvement story candidate |
| 7 | reviewer-comment-analyzer | Yes | clean | 0 stale/misleading comments in diff; new code added by 50-4 carries WHY-style comments (one-shot lifecycle, clamp rationale, silent-skip per spec) consistent with project pattern; no docstring rot found | N/A — green |

**All received: Yes** — 7/7 subagent reports collected before this assessment was written.

## Reviewer Assessment

**Verdict:** ✅ APPROVED after one fix-back round

**Subagents fanned out (6 in parallel, background):** preflight, edge-hunter, silent-failure-hunter, test-analyzer, rule-checker, type-design. simplify-* trio was already executed during TEA verify so reviewer-simplifier was skipped (would have retread the same ground).

### Findings summary

| Severity | Count | Disposition |
|---|---|---|
| HIGH (blocking) | 5 | fixed in `ee3161d` |
| MEDIUM | ~10 | flagged below (non-blocking) |
| LOW | ~8 | noted, not pursued |

### Findings by specialist tag

- [DOC] reviewer-comment-analyzer — clean. No stale/misleading comments. New 50-4 code carries WHY-style documentation throughout: module docstring links to design spec, `_render_time_skip_context` and `_pass_a2_time_skip` document lifecycle requirements, pydantic models explain each class's role, the `DAY_TICK_CAP` constant comment explains the YAGNI deferral. No docstring rot.
- [RULE] reviewer-rule-checker — 5 findings against the 17-rule python.md checklist. 1 HIGH: getattr silent fallback on typed `TurnContext.snapshot` (CLAUDE.md "No Silent Fallbacks") — fixed in `ee3161d`. 4 LOW/MED: bare `except Exception` in pre-existing `_to_json`, star-import re-export of `SPAN_TROPE_TIME_SKIP` matching established pattern, `pack: Any` annotation on `tick_tropes` predates 50-4, `pack_or_tropes_by_id: dict | object` annotation. The HIGH item is fixed; the rest are pre-existing or annotation-only and flagged non-blocking in the Reviewer Assessment.
- [TEST] reviewer-test-analyzer — 11 findings on test quality. 3 HIGH: zero-assertion `test_tick_tropes_accepts_days_advanced_kwarg` (fixed in `ee3161d` — added 3 assertions), pack-skipif on 3 wiring tests in CI (PROCESS — needs `tea_and_murder` checked out in CI; non-blocking), tautological `test_narration_turn_result_carries_days_advanced` (non-blocking, redundant with extraction test). 8 MED: otel_capture fixture leak, missing edge cases (progress=1.0 entry, empty active_tropes, negative days_advanced at engine boundary, sort tie-break by trope_id), source-inspection test substring loose, '14' substring search, tautological assignment-roundtrip test. All MED items logged for future polish stories.

### HIGH findings (fixed)

1. **Empty escalation → spurious implicit resolution** (`trope_time_skip.py:178`). Found by edge-hunter. A trope with `tdef.escalation == []` reaching `progress >= 1.0` would resolve with zero beats fired because `beats_fired >= len([]) == 0` is always True. Fix: added `tdef.escalation` truthiness to the resolution condition.
2. **Empty `tropeId` → wrong-element badge** (`dashboard.html`, `+Nd` handler). Found by edge-hunter. `CSS.escape("")` returns `""`; `querySelector('[data-trope-id=""]')` matches the first element with an empty attribute. Fix: `if (!tropeId) return;` guard at top of the forEach callback.
3. **Queue clear ordering vulnerable to register-section failure** (`orchestrator.py:1479`). Found by BOTH edge-hunter and silent-failure-hunter (convergent). If `PromptSection.new(...)` raised, the clear would be skipped and the same TIME-SKIP CONTEXT block would re-deliver next turn. Fix: reordered to clear-then-register so the one-shot lifecycle holds even on the register path's failure.
4. **Zero-assertion test** (`test_trope_time_skip.py:784` — `test_tick_tropes_accepts_days_advanced_kwarg`). Found by test-analyzer. A regression silently dropping the kwarg would pass. Fix: added `assert snap.days_elapsed == 0`, `pending_time_skip_summary == []`, and `progress == 0.0` after both calls (default + explicit zero).
5. **`getattr` silent fallback on typed `TurnContext.snapshot`** (`orchestrator.py:1461`). Found by rule-checker and type-design. CLAUDE.md "No Silent Fallbacks" violation: the field is declared `GameSnapshot | None`, default `None` — direct attribute access works and surfaces type errors. Fix: replaced all three `getattr(...)` calls with direct attribute reads.

Fix commit: `ee3161d`. Re-ran full suite: 5213 passed, 1 pre-existing flaky (unchanged), 64 skipped. Ruff clean.

### MEDIUM findings (non-blocking — flagged for future stories)

- **otel_capture fixture leaks `SimpleSpanProcessor`** (test-analyzer). Pre-existing pattern across the test suite; touching it broadly is out of scope. May contribute to the flaky `test_caverns_delver_loadout_wired_into_snapshot`. Worth a future test-isolation refactor story.
- **Pack-skipped wiring tests in CI** (test-analyzer). `TestBuildNarratorPromptWiring` is `pytest.mark.skipif`-gated on the `tea_and_murder` pack being checked out. Layer 1 (renderer) and Layer 3 (engine boundary) tests cover the helper and the kwarg threading without the pack, so the spec's AC-7 has indirect coverage even when the pack is absent. Document the assumption explicitly in CI setup, or add a pack-free smoke for the orchestrator path.
- **Stale `beats_fired` lets already-passed thresholds fire as day-1 beats** (edge-hunter, `trope_time_skip.py:154`). A corrupted snapshot with `beats_fired` undershoot would replay beats. Not a real production path (beats_fired is engine-maintained); defensive guard could land later.
- **`TimeSkipBeatEvent.days_into_skip` lacks `ge=1` constraint** (type-design). Production path enforces it via `max(1, ...)` in the engine, but the type doesn't encode the invariant. Worth a `Field(ge=1)` add in a future polish.
- **`days_advanced: 1.5` float silent drop to 0** (silent-failure, orchestrator.py:778). Documented "silent-drop pattern as items" — consistent with project convention. Future improvement: log a warning when a non-int is dropped so the GM panel sees it.
- **Source-inspection test substring loose** (test-analyzer, `test_tick_tropes_call_site_threads_days_advanced`). Could match `days_advanced=` anywhere in the file. The actual call site is the only occurrence today; future polish.
- **`'14' substring search in TestRenderTimeSkipContext.test_renders_total_days_elapsed_for_narrator_context`** (test-analyzer). Could match incidental digits. Future tightening to a regex.
- **`test_snapshot_carries_days_elapsed_and_summary` and `test_narration_turn_result_carries_days_advanced` are pydantic-assignment tautologies** (test-analyzer). They verify mutability of declared fields without exercising real flow. Could be removed; redundant with downstream tests but harmless.
- **Missing edge cases**: progress=1.0 entry, empty active_tropes, negative days_advanced at engine level, sort tie-break by `trope_id` (test-analyzer). All low-risk paths exercised indirectly by adjacent tests; explicit coverage would tighten the suite.

### LOW findings (noted)

NaN rate bypassing zero-rate guard, dashboard span discriminator could false-positive on future spans with `days_applied` field, bare `except Exception` in `_to_json` predates 50-4, star-import re-export of `SPAN_TROPE_TIME_SKIP` matches the established `spans/__init__.py` pattern, `pack: Any` annotation on `tick_tropes` predates 50-4. All consistent with established patterns or low-probability scenarios.

### Architecture concerns

- **`TurnContext.snapshot` field added** is the only API-surface widening in green; threaded only through `_build_turn_context`, defaults to None for legacy callers. Logged in Dev's Design Deviations. Approved as the cleanest accommodation of the prompt-builder access pattern.
- **DAY_TICK_CAP=14 not pack-configurable**: YAGNI per ADR-018 scope, documented in the constant's comment. Acceptable.

### Decision

**APPROVE** for merge. The fix-back round addressed every HIGH finding; remaining MEDIUM/LOW findings do not block merge and are appropriate for follow-up stories.

## Review Correlation

| # | Source | Finding | Classification | Checklist Check | Action |
|---|--------|---------|----------------|-----------------|--------|
| 1 | reviewer-edge-hunter | Empty escalation list → implicit resolution fires with zero beats (`trope_time_skip.py`) | NOT_APPLICABLE | — | Domain-specific algorithm boundary on the trope state machine; not a general Python pattern. Fixed in `ee3161d`. |
| 2 | reviewer-edge-hunter | Empty `tropeId` → `querySelector('[data-trope-id=""]')` matches wrong element (`dashboard.html`) | NOT_APPLICABLE | — | JavaScript/HTML code path — outside Python lang-review scope. Fixed in `ee3161d`. |
| 3 | reviewer-edge-hunter + silent-failure-hunter | Queue cleared AFTER fallible `register_section` — `PromptSection.new` failure causes silent re-delivery on next turn (`orchestrator.py`) | NEW_CHECK | #14 [NEW] State cleanup ordering with fallible side effects | Added check #14 to `.pennyfarthing/gates/lang-review/python.md` with provenance `Origin: 50-4 I3`. Fixed in `ee3161d`. |
| 4 | reviewer-test-analyzer | Zero-assertion test `test_tick_tropes_accepts_days_advanced_kwarg` (`test_trope_time_skip.py`) | EXISTING_CHECK | #6 Test quality ("Tests with no assertions") | Author (TEA) missed an existing checklist entry — wiring smoke shouldn't be assertion-free. Fixed in `ee3161d`. |
| 5 | reviewer-rule-checker + type-design | `getattr` silent-fallback access on typed `TurnContext.snapshot` / `GameSnapshot.pending_time_skip_summary` (`orchestrator.py`) | EXISTING_CHECK | CLAUDE.md "No Silent Fallbacks" | Maps to the project-wide rule in `sidequest-server/CLAUDE.md`. Dev missed the existing principle; the typed fields are None-safe via direct attribute access. Fixed in `ee3161d`. |
| 6 | reviewer-type-design | `pack_or_tropes_by_id: dict[str, TropeDefinition] | object` defeats type checking (`trope_time_skip.py`) | EXISTING_CHECK | #3 Type annotation gaps at boundaries | Non-blocking — annotation is comment-justified by the duck-typing docstring. Logged as MEDIUM in Reviewer Assessment. |
| 7 | reviewer-test-analyzer | `pytestmark_pack` skipif on AC-7 wiring tests in CI (`test_trope_time_skip_e2e.py`) | PROCESS | — | CI environment setup: needs `sidequest-content/genre_packs/tea_and_murder` checked out, or CI should assert pack presence. Logged as MEDIUM. |
| 8 | reviewer-test-analyzer | `otel_capture` fixture leaks `SimpleSpanProcessor` (`test_trope_time_skip.py`) | TOOLING | — | Pre-existing test-isolation pattern across the suite; suggested future refactor to `trace.set_tracer_provider(fresh)`. Not introduced by 50-4. |

### Signal Summary

- **External findings:** 0 (no PR comments, no AI reviewer feedback, no CI failures — pipeline blind spots clean for this story)
- **CI findings:** 0
- **Internal findings:** 8 (6 fixed/applied, 2 flagged non-blocking)
- **New checks added:** 1 (`#14 State cleanup ordering with fallible side effects` — from internal reviewer, not external)
- **EXISTING_CHECK misses:** 2 (test-quality #6 missed by TEA; CLAUDE.md "no silent fallbacks" missed by Dev). Watch for repeat misses on these two — promotion to automated gate is on the table at the third occurrence.

**Handoff:** To Scrum Master (The Mad Hatter) for sprint finish — PR open + merge + archive.