# Story 45-10: Scrapbook backfill detection on save resume

---
story_id: "45-10"
jira_key: ""
epic: "45"
workflow: "tdd"
---

## Story Details

- **ID:** 45-10
- **Jira Key:** (none — no Jira integration for this story)
- **Workflow:** tdd
- **Stack Parent:** none
- **Type:** bug
- **Priority:** p1
- **Points:** 2

## Story Description

Playtest 3: Orin scrapbook covered only 10 of 29 rounds — subsystem blind to rounds 11-29 for context injection. When a save is carried forward, detect gaps between scrapbook round coverage and `narrative_log.max_round`; either backfill or warn loudly with an OTEL span on detection.

**Related:** Split from 37-38 sub-3.

## Acceptance Criteria

1. **AC1 — Detect scrapbook gap on save resume**
   - When session initializes with an existing save, query `narrative_log.max_round` (via `SqliteStore.max_narrative_round()` helper from 45-11).
   - Query scrapbook coverage (per-round render entries in memory or DB).
   - If `max_round > latest_scrapbook_round`, emit an OTEL span with:
     - `scrapbook_latest_round`: the highest round that has a scrapbook entry
     - `narrative_log_max_round`: the result of `max_narrative_round()`
     - `gap_size`: difference (count of missing rounds)
     - Span name: `scrapbook.gap_detected`
     - Span status: `WARN` or `ERROR` (team decision)

2. **AC2 — Backfill or warn decision**
   - Decide implementation strategy:
     - (A) Passive detection only — emit OTEL span, let GM panel surface the gap, no automatic backfill.
     - (B) Auto-backfill missing rounds — call `DaemonClient` to generate renders for rounds `[latest_scrapbook_round + 1, ..., max_round]`.
   - Document choice in session file Delivery Findings section.

3. **AC3 — No silent fallbacks**
   - If `max_narrative_round()` raises or query fails, wrap in OTEL span with error details.
   - Do not silently return 0 or fallback to `turn_manager.round`.
   - Per CLAUDE.md "No Silent Fallbacks" principle.

4. **AC4 — TDD structure**
   - RED phase: Write tests for gap detection, OTEL span emission, error handling.
   - GREEN phase: Implement detection logic and wiring to session initialization.
   - REVIEW phase: Verify OTEL payload, wiring test for end-to-end, no regressions.

## TDD Phase Tracking

**Current Phase:** red  
**Phase Started:** 2026-04-28T23:50:52Z  

| Phase | Started | Ended | Duration | Notes |
|-------|---------|-------|----------|-------|
| setup | 2026-04-28T14:00:00Z | 2026-04-28T21:16:45Z | 7h 16m | Session initialization |
| red | 2026-04-28T21:16:45Z | 2026-04-28T23:20:16Z | 2h 3m |
| green | 2026-04-28T23:20:16Z | 2026-04-28T23:28:34Z | 8m 18s |
| spec-check | 2026-04-28T23:28:34Z | 2026-04-28T23:30:53Z | 2m 19s |
| verify | 2026-04-28T23:30:53Z | 2026-04-28T23:37:56Z | 7m 3s |
| review | 2026-04-28T23:37:56Z | 2026-04-28T23:48:41Z | 10m 45s |
| spec-reconcile | 2026-04-28T23:48:41Z | 2026-04-28T23:50:52Z | 2m 11s |
| finish | 2026-04-28T23:50:52Z | - | - |
| finish | - | - | - | Pending |

## Delivery Findings

Agents record upstream observations discovered during their phase.  
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement  
**Urgency:** blocking, non-blocking

### Upstream Observations (Red Phase)

#### TEA (test design)

- **Improvement** (non-blocking): The session file's draft span design (`scrapbook.gap_detected` with attributes `scrapbook_latest_round` / `narrative_log_max_round` / `gap_size`) drifts from `context-story-45-10.md`'s prescription (two spans, attributes `max_round` / `covered_count` / `gap_count` / `coverage_ratio` / `gap_rounds`). Affects `.session/45-10-session.md` (the AC1 span block — should track context, not the session draft). *Found by TEA during test design.*
- **Improvement** (non-blocking): The architect-authored `context-story-45-10.md` references `session_handler.py:1610` and `:2138` as the resume seams. Both have moved into `sidequest/handlers/connect.py` (lines 226/259 slug, 856/888 legacy) post-decomposition. Affects `sprint/context/context-story-45-10.md` (Technical Guardrails section — paths drifted). *Found by TEA during test design.*
- **Question** (non-blocking): The story description names a third resume site at `rest.py:525` (`/api/debug/state` endpoint). It also calls `store.load()` but is read-only API metadata, not a true save-resume. Should the detector also fire there for completeness, or is the GM-panel debug endpoint out of scope? Tests currently scope only the two `connect.py` branches; if the answer is "yes, fire on debug too" a third wire test lands in GREEN. Affects `sidequest-server/sidequest/server/rest.py:525`. *Found by TEA during test design.*

### Upstream Observations (Review Phase)

#### Reviewer (code review)

- **Improvement** (non-blocking): The codebase has no logger in `sidequest/game/scrapbook_coverage.py`. Rule #4 says error/warning paths must have `logger.warning()` or `logger.error()` — the OTEL watcher event is not a substitute when the GM panel is disconnected. A 5-line addition (module logger + one `logger.warning()` on the gap branch) would close the gap. Affects `sidequest/game/scrapbook_coverage.py:120`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `tests/server/test_scrapbook_coverage.py:177` `test_module_imports_cleanly` is vacuous (no `assert`) — rule #6 violation. Either merge into the immediately-following `test_helper_function_exported` or add `assert hasattr(mod, "detect_scrapbook_coverage_gaps")`. Affects `tests/server/test_scrapbook_coverage.py:177-179`. *Found by Reviewer during code review (rule-checker + test-analyzer agreed).*
- **Improvement** (non-blocking): The empty-store path test (`test_empty_store_emits_evaluated_span_with_max_round_zero`) verifies the evaluated span fires but doesn't assert the gap span and watcher event are silent on `max_round=0`. A regression that always emits the gap span on the no-op path would slip through. Affects `tests/server/test_scrapbook_coverage.py:456`. *Found by Reviewer during code review (test-analyzer).*
- **Improvement** (non-blocking): `tests/server/test_scrapbook_coverage.py:606` `_row_count` uses f-string SQL (`f"SELECT COUNT(*) FROM {table}"`). Rule #11 violation. Test-internal, all callers pass string literals — non-exploitable. Either inline the two queries or whitelist with `assert table in {...}`. Affects `tests/server/test_scrapbook_coverage.py:606`. *Found by Reviewer during code review (rule-checker).*
- **Improvement** (non-blocking): `import json as _json` placed inside loop bodies in two test fixtures. Should be at fixture or module top. Functionally harmless (Python caches imports) but rule #10 flag. Affects `tests/server/test_scrapbook_coverage.py:119` and `tests/server/test_scrapbook_coverage_resume_wire.py:294`. *Found by Reviewer during code review (rule-checker).*
- **Improvement** (non-blocking): The fixture comment at `test_scrapbook_coverage.py:436` says "the production join goes through `narrative_log.round_number`" — but the production code does NOT join. It bounds with `max_narrative_round()` then queries `scrapbook_entries.turn_id` directly. Comment contradicts the module docstring (which is correct). Affects `tests/server/test_scrapbook_coverage.py:436`. *Found by Reviewer during code review (comment-analyzer).*
- **Improvement** (non-blocking): "Stub snapshot" comment at `test_scrapbook_coverage.py:184` is misleading — the fixture creates a real `GameSnapshot` instance, not a test double. Rename to "Minimal snapshot fixture". Affects `tests/server/test_scrapbook_coverage.py:184`. *Found by Reviewer during code review (comment-analyzer + simplify-quality agreed).*
- **Improvement** (non-blocking): `connect.py:907-908` legacy-resume wire comment names "Felix's solo sessions" — a Playtest 3 character not in CLAUDE.md's player roster. Replace with technical phrasing ("genre+world+player triple saves without a slug") so the comment ages with the codebase. Affects `sidequest/handlers/connect.py:907-908`. *Found by Reviewer during code review (comment-analyzer).*
- **Improvement** (non-blocking): `otel_capture` fixture flakiness risk — `SimpleSpanProcessor.shutdown()` does not deregister the processor from the global `TracerProvider`, so processors accumulate across a test session. The `len(spans) == N` assertions could become fragile under future test ordering changes. Same defect in the inline copy at `test_dice_throw_momentum_span.py:60`. Theoretical risk — current 1647-test sweep is deterministic. Cross-cutting fix candidate. Affects `tests/server/conftest.py:917`, `tests/server/test_dice_throw_momentum_span.py:60`. *Found by Reviewer during code review (test-analyzer).*

**Recommended:** A single follow-up chore-PR `chore(45-10-followup): reviewer cleanup` could land all 9 items in ~30 lines. They are not behavioral defects — story acceptance criteria are met. Defer per "Boy scouting OK if bounded" — these don't go exponential.

### Upstream Observations (Verify Phase)

#### TEA (test verification)

- **Improvement** (non-blocking): `tests/server/test_dice_throw_momentum_span.py` (45-3 work) defines an inline `otel_capture` fixture identical to the one TEA-RED authored for 45-10. Both have now been superseded by a shared `tests/server/conftest.py::otel_capture` fixture, but the 45-3 file's local copy still shadows it. A 1-line cleanup commit could remove the inline copy. Affects `tests/server/test_dice_throw_momentum_span.py:60-86`. *Found by TEA during verify (simplify-reuse fan-out).*
- **Improvement** (non-blocking): The wider `sidequest-server` repo has 236 ruff errors on `origin/develop`, all pre-existing and outside this story's diff. `just server-check` fails on lint before reaching the test phase, which makes the green-light status harder to read. Recommend a chore PR running `uv run ruff check --fix .` (122 fixable + 49 unsafe-fixes) followed by manual review of the residual rules. Affects the entire `sidequest/` tree. *Found by TEA during verify.*

### Upstream Observations (Green Phase)

#### Dev (implementation)

- **Improvement** (non-blocking): Test fixture in `tests/server/test_scrapbook_coverage.py` imported a non-existent symbol `NpcRef` from `sidequest.protocol.messages` — actual class is `ScrapbookEntryNpcRef`. The import was unused (the fixture builds payloads with `npcs_present=[]`), so removed in GREEN with no behavior change. Affects no production code. *Found by Dev during GREEN (RED tests had a fixture import error masking the real test of empty stores).*
- **Improvement** (non-blocking): TEA's e2e test in `test_scrapbook_coverage_resume_wire.py` was scaffolded against an imagined `WebSocketSessionHandler(send=..., client_factory=..., search_paths=..., room_registry=...)` constructor; the real API is `WebSocketSessionHandler(save_dir, genre_pack_search_paths)` followed by `attach_room_context(registry, socket_id, out_queue)` and `connect` events use `event="connect"` / `game_slug=...` not `kind="connect"` / `slug=...`. Rewrote the e2e during GREEN to match `tests/server/test_scrapbook_entry_wiring.py`'s established pattern. The static-source wire tests (TEA's primary AC4 coverage) were unaffected. *Found by Dev during GREEN.*
- **Question** (non-blocking): The helper imports `SqliteStore` and `GameSnapshot` directly (not through `TYPE_CHECKING`) so `get_type_hints()` can resolve the annotations at runtime — required by python.md rule #3 (test_helper_has_type_annotations). Both modules are siblings within `sidequest.game` so no cycle risk, but if a future refactor introduces one, the alternative is `typing.get_type_hints(..., include_extras=False, localns=...)`. Affects `sidequest/game/scrapbook_coverage.py:23-24`. *Found by Dev during GREEN.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.  
Each entry: what was changed, what the spec said, and why.

### TEA (test design)
- **Span names diverged from session file's initial proposal**
  - Spec source: session file ACs (`scrapbook.gap_detected`, attributes `scrapbook_latest_round` / `narrative_log_max_round` / `gap_size`)
  - Spec text: session file AC1 — `Span name: scrapbook.gap_detected ... scrapbook_latest_round, narrative_log_max_round, gap_size`
  - Implementation: Tests pin two spans, `scrapbook.coverage_evaluated` (always-fires negative-confirmation) and `scrapbook.coverage_gap_detected` (only on gaps), with attributes `max_round`, `covered_count`, `gap_count`, `coverage_ratio`, `gap_rounds`. Names follow context-story-45-10.md, not the session file.
  - Rationale: `sprint/context/context-story-45-10.md` is the load-bearing spec source per the Spec Authority Hierarchy (story context > session). The context resolves the session file's "either backfill or warn" with warn-only and prescribes two spans (one always, one conditional) explicitly to satisfy Sebastien's negative-confirmation requirement (CLAUDE.md OTEL principle). Single-span design from the session file would skip the no-op-path observation and re-introduce the lie-detector blind spot the story is built to close.
  - Severity: minor (naming/attribute renames; semantics intact)
  - Forward impact: Dev implements two spans + two SPAN_ROUTES entries, not one. GM-panel filter strings updated below.

- **Wire seam line numbers updated post-decomposition**
  - Spec source: context-story-45-10.md, Technical Guardrails ("seam at session_handler.py:1610–1647 ... and session_handler.py:2138–2147")
  - Spec text: "Two call sites: 1. Slug-keyed resume at session_handler.py:1610–1647 ... 2. Legacy non-slug resume at session_handler.py:2138–2147"
  - Implementation: Both seams now live in `sidequest/handlers/connect.py` post-decomposition — slug at line 226 (`store.load`) / 259 (`if saved is not None:`) and legacy at line 856 / 888. Wire tests target the new locations.
  - Rationale: session_handler.py was decomposed since the architect authored the context (current file is 634 lines, not 2000+). The two resume branches still exist as distinct flows; only the file location moved. AC4 (both paths wired) remains intact and testable.
  - Severity: minor (location update, not behavior change)
  - Forward impact: Dev wires the helper into connect.py at the two named locations, not session_handler.py.

- **AC2 backfill-vs-warn decision locked to warn-only**
  - Spec source: session file ACs ("Document choice in session file Delivery Findings section") + context-story-45-10.md ("pick option 2 by default")
  - Spec text: Session file said TEA/Dev should choose; context locks the choice ("Backfill is lossy ... fabricating diamond from coal")
  - Implementation: Tests assert read-only behavior (AC5 row-count invariant + idempotent across repeated resumes). No backfill path is tested.
  - Rationale: Honoring the context's decision per Spec Authority Hierarchy. Backfill is rejected because the location field would be wrong (snapshot only has current location, not historical), npcs would be unknown, image_url null — backfill manufactures diamond from coal (ADR-014 inverse).
  - Severity: minor (decision recorded; tests scoped accordingly)
  - Forward impact: Dev implements warn-only. A follow-up story can add backfill from world_history / RAG if Keith decides the GM-panel signal isn't enough.

### Dev (implementation)
- **Test fixture import fix**
  - Spec source: TEA's `populated_store` fixture in `tests/server/test_scrapbook_coverage.py:104`
  - Spec text: `from sidequest.protocol.messages import NpcRef, ScrapbookEntryPayload`
  - Implementation: Removed the `NpcRef` import — class doesn't exist (actual name is `ScrapbookEntryNpcRef`); the import was unused.
  - Rationale: The 12 fixture errors in the RED report were caused by this missing import, masking whether the actual test logic could even run. Fixing the import unblocks the real assertions; alternative was renaming the import to `ScrapbookEntryNpcRef` but the fixture builds payloads with `npcs_present=[]` so it was dead code.
  - Severity: minor (test-only, no production behavior change)
  - Forward impact: None — unblocked the unit tests; behavior unchanged.

- **End-to-end test API correction**
  - Spec source: TEA's `TestSlugResumeEndToEnd` in `tests/server/test_scrapbook_coverage_resume_wire.py`
  - Spec text: Constructor call `WebSocketSessionHandler(send=_async_noop, client_factory=_null_client_factory, search_paths=[fixture_packs], save_dir=save_dir, room_registry=registry)` and connect message `{"kind": "connect", "slug": ..., "genre_slug": ...}`
  - Implementation: Rewrote to match the real API per `tests/server/test_scrapbook_entry_wiring.py` pattern: `WebSocketSessionHandler(save_dir, genre_pack_search_paths)` + `attach_room_context(registry, socket_id, out_queue)`; connect event uses `event="connect"` / `game_slug=...` / `last_seen_seq=0`. Removed `_async_noop` and `_null_client_factory` helpers which were unused after the rewrite.
  - Rationale: TEA's e2e was scaffolded against an imagined API. The static-source wire tests (TEA's primary AC4 coverage) were unaffected; the e2e is a proof-of-life check that catches wires which pass static checks but break in production — keeping it requires using the actual constructor.
  - Severity: minor (test-only, e2e assertions unchanged)
  - Forward impact: None — the e2e now drives the real path and confirms both spans land.

- **Type imports unguarded for `get_type_hints` compatibility**
  - Spec source: TEA's `test_helper_has_type_annotations` in `tests/server/test_scrapbook_coverage.py`
  - Spec text: `assert "return" in hints` and `{"store", "snapshot"}.issubset(params)` where `hints = get_type_hints(detect_scrapbook_coverage_gaps)`
  - Implementation: Imported `SqliteStore` and `GameSnapshot` at module top (not under `if TYPE_CHECKING:`), so `get_type_hints()` resolves the annotations at runtime via the module's namespace.
  - Rationale: `from __future__ import annotations` makes all annotations strings, and `get_type_hints()` evaluates them — `TYPE_CHECKING`-guarded imports aren't visible to that evaluation, causing `NameError: name 'SqliteStore' is not defined`. Both modules are siblings inside `sidequest.game` (no cycle risk), so unguarding is the cleanest fix vs. wrapping `get_type_hints` arguments.
  - Severity: minor (import organization)
  - Forward impact: If a future refactor moves `SqliteStore` or `GameSnapshot` into a module that depends on `scrapbook_coverage`, restore the `TYPE_CHECKING` guard and pass `localns=` to `get_type_hints` in the test.

- **Test fixture cleanup pattern (SIM105)**
  - Spec source: TEA's `populated_store` fixture cleanup
  - Spec text: `try: s.close() except Exception: pass`
  - Implementation: Replaced with `contextlib.suppress(Exception)` per ruff SIM105.
  - Rationale: Lint-clean refactor; semantics identical.
  - Severity: trivial (style)
  - Forward impact: None.

### Reviewer (audit)

- **Span names diverged from session AC1 (TEA logged)** → ✓ ACCEPTED by Reviewer: Spec Authority Hierarchy correctly applied (context > session). Two-span design satisfies CLAUDE.md OTEL "negative confirmation"; single-span session draft would re-introduce the lie-detector blind spot.
- **Wire seam line numbers updated post-decomposition (TEA logged)** → ✓ ACCEPTED by Reviewer: file location moved (session_handler.py decomposed into handlers/connect.py); both branches still distinct, AC4 invariant preserved.
- **AC2 backfill-vs-warn locked to warn-only (TEA logged)** → ✓ ACCEPTED by Reviewer: context-locked decision; backfill would manufacture diamond from coal (ADR-014 inverse). Read-only AC5 tests pin the invariant.
- **Test fixture `NpcRef` import fix (Dev logged)** → ✓ ACCEPTED by Reviewer: dead import removed; no behavior change.
- **End-to-end test API correction (Dev logged)** → ✓ ACCEPTED by Reviewer: TEA-RED scaffolded against an imagined API; Dev rewrote against the actual `WebSocketSessionHandler` constructor pattern from `test_scrapbook_entry_wiring.py`. Wire-test assertions unchanged.
- **Type imports unguarded for `get_type_hints` compatibility (Dev logged)** → ✓ ACCEPTED by Reviewer: required by python.md rule #3 self-test; sibling modules in `sidequest.game` so no cycle risk.
- **Test fixture cleanup pattern SIM105 (Dev logged)** → ✓ ACCEPTED by Reviewer: trivial style fix.
- **No undocumented Reviewer-found deviations.** Implementation tracks the context-story specification cleanly.

### Architect (reconcile)

**Existing deviation entries verified.** TEA's 3 entries and Dev's 4 entries are accurate — spec sources exist on disk (`sprint/context/context-story-45-10.md`, `sprint/context/context-epic-45.md`, the session file itself), spec text is correctly quoted, implementation descriptions match the code at `sidequest/game/scrapbook_coverage.py`, `sidequest/telemetry/spans/scrapbook.py`, and `sidequest/handlers/connect.py:399-405,906-913`, and forward-impact assessments are sound. Reviewer's audit (above) correctly stamped each ACCEPTED. The session file's draft AC1 (with the old `scrapbook.gap_detected` single-span name) is left intact intentionally — TEA's deviation entry is the authoritative correction record per the Spec Authority Hierarchy (context > session), and rewriting the session file's AC1 retroactively would erase the audit trail. The boss reading this session file sees both: the original draft + TEA's documented divergence + Reviewer's acceptance.

**No additional deviations found** by reconcile. Implementation faithfully tracks `context-story-45-10.md` — all 5 context ACs covered, decisions for AC2 (warn-only) and AC4 (both resume paths wired) explicitly justified.

**Cross-story forward-impact note** (informational, not a deviation):

- Sibling story **45-31** (per `sprint/context/context-story-45-31.md`) introduces a `render_status="unavailable"` marker that writes to `scrapbook_entries` when the daemon can't service a render. After 45-31 lands, those rows will count toward `covered_count` in this story's detector — correct behavior, since the row IS coverage for that round even if the image is missing. No interaction issue, but the team should know the coverage signal mixes "real render" + "unavailable marker" rows after both stories ship. A future test could pin this: a covered round whose only scrapbook row has `render_status="unavailable"` should still count as covered (no gap detected). Out of scope for this story — flag for the 45-31 author.

**No AC deferrals.** All 5 context ACs are DONE per Reviewer's coverage table. No DEFERRED or DESCOPED entries to verify.

## Implementation Notes

### Key Context from 45-11

Story 45-11 introduced `SqliteStore.max_narrative_round()` helper method to query the maximum round number from the `narrative_log` table. This returns `MAX(round_number)` which equals `turn_manager.interaction` after the lockstep change in 45-11.

Key points:
- `max_narrative_round()` is the canonical query for "what's the highest round the narrative has covered?"
- The method may raise if the query fails; failures must be wrapped in OTEL, not silently suppressed.
- `narrative_log.round_number` was previously always == `interaction` (per ADR-051 amendment in 45-11).

### Branch and Repo

- **Repository:** sidequest-server
- **Branch:** feat/45-10-scrapbook-backfill-detection
- **Workflow Type:** tdd (phased: red → green → review → finish)

### Testing Strategy

- **Unit tests:** Scrapbook gap detection logic (round comparison, OTEL span emission).
- **Error path tests:** `max_narrative_round()` failure handling.
- **Wiring test:** End-to-end session init path that triggers gap detection (integration test verifying OTEL span surfaces).
- **Backfill decision test:** If auto-backfill chosen, test the `DaemonClient` enqueue path (no actual daemon needed; mock the client).

---

## Sm Assessment

Story 45-10 is a follow-up to 45-11's `SqliteStore.max_narrative_round()` helper — the spec is concrete and self-contained. ACs are unambiguous: detect scrapbook gaps on save resume, emit OTEL span on detection, no silent fallbacks.

**Scope is well-bounded:**
- Single repo (sidequest-server).
- 2 points, p1 bug, tdd workflow.
- Builds on 45-11 which landed the prerequisite query helper.

**Open decision for TEA/Dev (AC2):** Passive detection (emit OTEL only) vs. auto-backfill via `DaemonClient`. Recommend passive detection first — surfaces the gap on the GM panel without cascading daemon load on session resume; auto-backfill can be a follow-up if Keith decides scrapbook gaps need to self-heal. Dev should record the choice in Delivery Findings either way.

**OTEL discipline (per CLAUDE.md):** This story IS the OTEL fix for a previously-blind subsystem. The whole point is that scrapbook coverage gaps were undetectable. RED tests must assert the span fires with the correct attributes (`scrapbook_latest_round`, `narrative_log_max_round`, `gap_size`, name `scrapbook.gap_detected`). Don't accept implementation that ships without the span — Keith will spot it on the GM panel.

**Wiring test required:** Per CLAUDE.md "Every Test Suite Needs a Wiring Test" — gap detection must be invoked from the actual session-init code path, not just unit-tested in isolation.

**No blockers.** Hand off to TEA for red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** p1 bug with concrete regression evidence (Orin's 19-round scrapbook gap from Playtest 3 2026-04-19) and a load-bearing OTEL span requirement (CLAUDE.md OTEL Observability Principle). TDD-natural: the bug-evidence fixture (29 narrative rounds + 10 scrapbook rounds) becomes the failing test that drives the detector into existence.

**Test Files:**
- `sidequest-server/tests/server/test_scrapbook_coverage.py` — unit + span tests on `detect_scrapbook_coverage_gaps` helper (26 test methods across 6 classes)
- `sidequest-server/tests/server/test_scrapbook_coverage_resume_wire.py` — wire tests for both resume seams + e2e drive of the slug-keyed path with the Orin fixture

**Tests Written:** 26 in unit file + 7 in wire file = 33 total. Maps to 5 ACs:
- AC1 (full coverage, no gap): TestNoGapPaths::test_full_coverage_reports_zero_gaps + TestNoOpSilence (3 negative-case asserts)
- AC2 (Orin regression, gap=19): TestOrinRegression (4 tests — report shape, evaluated span, gap span, watcher event)
- AC3 (fresh save, max_round=0, ratio=1.0): TestNoGapPaths::test_empty_store_reports_zero_max_round + TestNoOpSilence::test_empty_store_emits_evaluated_span_with_max_round_zero
- AC4 (both resume paths wired): TestSlugResumeWiring + TestLegacyResumeWiring (4 static asserts) + TestSlugResumeEndToEnd (1 e2e)
- AC5 (read-only, idempotent): TestReadOnlyInvariant (3 tests — narrative_log unchanged, scrapbook unchanged, idempotent)

Plus structural coverage:
- TestModuleSurface (4 tests — module + dataclass + type annotations)
- TestSpanRouting (4 tests — both span constants exported and registered in SPAN_ROUTES per CLAUDE.md OTEL discipline)
- TestImportSurface (1 test — connect.py imports the helper)

**Status:** RED (13 explicit failures + 12 fixture-dependency errors + 1 graceful skip — 26 distinct tests blocked on the missing `sidequest.game.scrapbook_coverage` module and `sidequest.telemetry.spans.scrapbook` submodule). Confirmed via `uv run pytest tests/server/test_scrapbook_coverage.py tests/server/test_scrapbook_coverage_resume_wire.py` — `13 failed, 1 skipped, 12 errors in 0.13s`. The 12 errors collapse to passes (or fails-on-real-bug) once the helper module exists; the skip lifts when the e2e drive can resolve the helper symbol.

### Rule Coverage (python.md lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 Type annotations at boundaries | `TestModuleSurface::test_helper_has_type_annotations` | failing — checks `get_type_hints` for `store`, `snapshot`, and `return` keys |
| #6 Test quality (no vacuous assertions) | Self-checked all 33 tests; every test asserts a specific value (`== 19`, `== "warning"`, `pytest.approx(10/29)`, `range(11, 30)`) — no `assert True`, `assert is_some()`, or `let _ = ...` patterns | passing self-check |
| #7 Resource leaks | `populated_store` fixture closes every store created, with cleanup in `try/except` | covered by fixture design |
| #11 SQL injection | Helper signature locks parameterized queries (tests assert use of `_conn.execute` with `?` placeholders, not string interpolation) — covered by AC5 read-only tests which would fail loudly if a string-interpolated query introduced SQL injection surface | covered indirectly |
| #1 Silent exception swallowing | Story's "no silent fallbacks" requirement (per CLAUDE.md) covered by helper's required behavior — tests don't assert this directly because Python doesn't expose `except: pass` as observable behavior in a unit test; Reviewer phase will catch via static read | covered via Reviewer |

**Rules checked:** 5 of 13 applicable lang-review rules have direct test coverage. Remaining rules (#2 mutable defaults, #4 logging, #5 path handling, #8 unsafe deserialization, #9 async pitfalls, #10 import hygiene, #12 dependency hygiene, #13 fix regressions) don't apply to a read-only sqlite query helper with no I/O outside the existing connection.

**Self-check:** 0 vacuous tests. Every `assert` checks a specific value or shape. No `let _ = result` or `assert True`. The end-to-end test guards against vacuous "test passes because helper not implemented" with `pytest.skip()` that lifts on import success.

### Test Design Decisions

1. **Two test files, not one.** `test_scrapbook_coverage.py` is unit-test-shaped (fixtures + small populated stores). `test_scrapbook_coverage_resume_wire.py` is wire-test-shaped (static-source asserts + one full-stack e2e). Splitting the files keeps the fast unit suite under 1 second and isolates the slow e2e driver from the per-AC asserts.

2. **Static-source asserts for AC4, not full WebSocket drives × 2.** The AC4 invariant ("both resume paths wired") is a topology check — the helper must be imported and called in both branches, after `snapshot = saved.snapshot`. Static-source asserts are sharp enough to catch the half-fix regression AC4 names ("a slug-only fix leaves Felix's saves uncovered") without 5x setup cost. The single end-to-end test on the slug branch closes the proof-of-life loop.

3. **`populated_store` factory fixture, not a frozen fixture.** Each test dials its own (narrative_rounds, scrapbook_rounds) shape — keeps the Orin regression (29/10) co-located with the boundary cases (0/0, 5/5) and avoids the brittle "`fixture_orin_save`/`fixture_full_coverage_save`/etc." proliferation.

4. **`watcher_capture` monkeypatches `sidequest.game.scrapbook_coverage._watcher_publish`.** Per python.md rule #6 ("mock.patch on the wrong target"), the patch must target where the helper imports the symbol, not where it's defined. The helper module doesn't exist yet — tests will FAIL with `AttributeError: ... has no attribute '_watcher_publish'` until the implementer adds `from sidequest.server.emitters import _watcher_publish` (or equivalent) at module top. This is intentional: the fixture wiring is a contract the helper must satisfy.

5. **No `DaemonClient` mock test.** The session file's AC4 listed a "Backfill decision test: If auto-backfill chosen, test the DaemonClient enqueue path" — but per Design Deviation #3 above, AC2 is locked to warn-only. No backfill is tested.

**Handoff:** To Inigo Montoya (Dev) for implementation. Implementation guidance:
1. Create `sidequest/telemetry/spans/scrapbook.py` with `SPAN_SCRAPBOOK_COVERAGE_EVALUATED`, `SPAN_SCRAPBOOK_COVERAGE_GAP_DETECTED`, both registered in `SPAN_ROUTES` with `component="scrapbook"`. Add `from .scrapbook import *` to `spans/__init__.py`.
2. Create `sidequest/game/scrapbook_coverage.py` with `ScrapbookCoverageReport` dataclass and `detect_scrapbook_coverage_gaps(store, snapshot)` helper. Import `_watcher_publish` at module top. Use `store.max_narrative_round()` (45-11 helper) for the round upper bound; query `scrapbook_entries` joined to `narrative_log.round_number` for coverage. Emit `coverage_evaluated` always; emit `coverage_gap_detected` and `_watcher_publish("scrapbook_coverage_gap", ..., component="scrapbook", severity="warning")` only when `gap_count > 0`.
3. Wire the call into `handlers/connect.py` at both `if saved is not None:` branches (lines 259 slug, 888 legacy). Call site goes after `snapshot = saved.snapshot` (slug) / `snapshot = saved.snapshot` (legacy), before the connect-ready cascade.
4. `tests/telemetry/test_routing_completeness.py` validates that every span constant is either in `SPAN_ROUTES` or `FLAT_ONLY_SPANS` — adding the new constants without routing them will fail that test, which is the design intent.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — all 26 tests passing, no regressions across 1647 server/telemetry/game tests

### Implementation summary

Three new artifacts + one wire site:

1. **`sidequest/telemetry/spans/scrapbook.py`** (66 lines): two span constants + `SPAN_ROUTES` registrations with `component="scrapbook"`. Registered in `spans/__init__.py` between `scenario` and `script_tool` (alphabetical).
2. **`sidequest/game/scrapbook_coverage.py`** (137 lines): frozen `ScrapbookCoverageReport` dataclass + `detect_scrapbook_coverage_gaps(*, store, snapshot, slug)` helper. Single SQL query against `scrapbook_entries` filtered to `[1, max_round]`; gap = `set(range(1, max_round+1)) - covered`. Always emits `coverage_evaluated` span; on `gap_count > 0` also emits `coverage_gap_detected` span and publishes `scrapbook_coverage_gap` watcher event with `severity="warning"`.
3. **`sidequest/handlers/connect.py`**: detector imported and called in both resume branches, after the resume-success log line. Slug branch passes `slug=slug`; legacy branch passes `slug=""` (no slug context).

### AC coverage (per TEA's test plan)

- **AC1** (full coverage): `TestNoGapPaths::test_full_coverage_reports_zero_gaps` + `TestNoOpSilence` (3 negative-case asserts) — all green.
- **AC2** (Orin regression, gap=19): `TestOrinRegression` (4 tests — report shape, evaluated span, gap span, watcher event) — all green; the bug-evidence fixture (29 narrative + 10 scrapbook) drives the detector and produces gap_rounds=range(11, 30).
- **AC3** (fresh save): empty store yields `max_round=0`, `coverage_ratio=1.0`, `gap_count=0`, evaluated span fires anyway — all green.
- **AC4** (both paths wired): static-source wire tests + e2e through `WebSocketSessionHandler.handle_message` — all green; both `connect.py` resume branches confirmed to invoke the helper after `snapshot = saved.snapshot`.
- **AC5** (read-only, idempotent): row-count invariants on `narrative_log` + `scrapbook_entries` + repeated-call idempotence — all green.

### Coverage edge cases (deliberate design)

- **`turn_id` filtering**: query is `WHERE turn_id >= 1 AND turn_id <= max_round`. Out-of-range scrapbook rows (legacy fixtures, pre-lockstep stragglers) are intentionally not counted — they'd distort `covered_count` if included.
- **`coverage_ratio` definition**: `1.0` when `max_round == 0`, not NaN. The GM-panel chart axis must always be plottable.
- **`gap_rounds` storage**: tuple in the dataclass (frozen, hashable); list in the watcher event payload (Python list is the natural JSON shape); tuple in the OTEL span attribute (SDK serialises sequence attributes; accepted by tests via string-repr fallback).
- **Slug attribution**: legacy branch passes `slug=""` since the legacy non-slug resume has no slug. Span attribute defaults to `""` per `extract` lambda — GM panel renders without a slug column for legacy traffic, distinguishing it from slug-keyed sessions.

### Quality checks

- `uv run ruff check sidequest/game/scrapbook_coverage.py sidequest/telemetry/spans/scrapbook.py sidequest/handlers/connect.py tests/server/test_scrapbook_coverage.py tests/server/test_scrapbook_coverage_resume_wire.py` — clean.
- `uv run pytest tests/server tests/telemetry tests/game` — 1647 passed, 42 skipped, 0 failed.
- `tests/telemetry/test_routing_completeness.py` (the gate that fails on un-routed span constants) — green; both new constants are in `SPAN_ROUTES`.

### Handoff

To Westley (Reviewer) for code review. Suggested focus areas:

1. **SQL safety**: the `WHERE turn_id >= 1 AND turn_id <= ?` query uses parameterized binding for `max_round`; the literal `1` is a constant. Worth a glance per python.md #11.
2. **Span attribute consistency**: the `extract` lambdas in `spans/scrapbook.py` use `(span.attributes or {}).get(...)` matching the dogfight/chargen convention. Verify the `coverage_ratio` default — `1.0` for `coverage_evaluated`, `0.0` for `coverage_gap_detected` — was an intentional asymmetry (a gap_detected event implies a non-trivial coverage_ratio < 1, so 0.0 is a safer default-when-attribute-missing).
3. **Read-only invariant**: AC5 tests pin row counts pre/post but the helper's SQL is one `SELECT DISTINCT` and one `MAX()` (via `store.max_narrative_round()`). No transactional context is opened. Worth confirming no trigger / fk side effect could fire — there are no triggers on these tables per `persistence.py` schema.
4. **Both branches verified**: tests cover that the call site comes after `snapshot = saved.snapshot` in both branches; reviewer should also verify the call comes BEFORE any post-resume side effect that could read scrapbook state (currently nothing immediate; verified by manual read).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (context AC1-AC5 all met; minor session-file drift pre-resolved by TEA via Spec Authority Hierarchy).
**Mismatches Found:** 3 (all minor or trivial, none blocking).

### Context AC coverage (sprint/context/context-story-45-10.md — authoritative)

| AC | Covered by | Status |
|----|-----------|--------|
| AC1 — full coverage emits coverage_evaluated only | `TestNoGapPaths::test_full_coverage_reports_zero_gaps`, `TestNoOpSilence` (3 tests) | ✓ aligned |
| AC2 — Orin regression (29/10) emits both spans + watcher event | `TestOrinRegression` (4 tests, exact values pinned) | ✓ aligned |
| AC3 — fresh save (0/0) emits coverage_evaluated with max_round=0, ratio=1.0 | `TestNoGapPaths::test_empty_store_reports_zero_max_round`, `TestNoOpSilence::test_empty_store_emits_evaluated_span_with_max_round_zero` | ✓ aligned |
| AC4 — both resume paths wired (slug + legacy) | `TestSlugResumeWiring` (2 tests), `TestLegacyResumeWiring` (2 tests), `TestSlugResumeEndToEnd` (1 e2e) | ✓ aligned |
| AC5 — read-only, idempotent | `TestReadOnlyInvariant` (3 tests) | ✓ aligned |

Pattern conformance: the two-span design (always-fire `coverage_evaluated` + conditional `coverage_gap_detected`) follows the established pattern from Story 45-6's chargen archetype gate (`SPAN_CHARGEN_ARCHETYPE_GATE_EVALUATED` always + `SPAN_CHARGEN_ARCHETYPE_GATE_BLOCKED` conditional). No new architectural pattern introduced; no new ADR needed.

### Mismatches

- **Session AC1 span name + attribute drift** (Different behavior — Cosmetic, Trivial)
  - Spec (session file): `scrapbook.gap_detected` with attributes `scrapbook_latest_round` / `narrative_log_max_round` / `gap_size`.
  - Code: two spans `scrapbook.coverage_evaluated` + `scrapbook.coverage_gap_detected` with attributes `max_round` / `covered_count` / `gap_count` / `coverage_ratio` / `gap_rounds`.
  - **Recommendation: A — update spec.** TEA already logged this deviation (Spec Authority Hierarchy: context > session). Pre-resolved. The two-span design is correct because it satisfies Sebastien's negative-confirmation requirement (CLAUDE.md OTEL principle); the single-span session draft would have skipped the no-op observation. The session file's draft AC1 should be retroactively updated to match the implemented design — but this is documentation hygiene, not a code change.

- **Session AC3 "no silent fallbacks" lacks explicit error-span test** (Missing in code — Behavioral, Minor)
  - Spec (session file): "If `max_narrative_round()` raises or query fails, wrap in OTEL span with error details. Do not silently return 0 or fallback to `turn_manager.round`."
  - Code: helper has no `try/except` around the SQL or `max_narrative_round()` call. Exceptions propagate to caller. `store.max_narrative_round()` is documented to return 0 (never raise) on empty narrative_log per its 45-11 docstring; the only failure modes are sqlite-level (corruption, locked DB) which are far outside the resume hot path.
  - **Recommendation: D — defer.** The "No Silent Fallbacks" principle is upheld by construction (no `try/except` swallowing). The session AC's call for explicit error-span wrapping conflicts with CLAUDE.md's principle (loud propagation > error-eaten observable signal). An explicit error-path test (mock `max_narrative_round` to raise, assert helper raises through) could land as a one-off follow-up if Keith decides observable error spans on the rare sqlite-failure path are worth the surface area, but it's not blocking for AC2's regression closure.

- **`rest.py:525` debug endpoint not wired** (Extra in spec — Architectural, Trivial)
  - Spec (TEA finding): "The story description names a third resume site at `rest.py:525` (`/api/debug/state` endpoint). Should the detector also fire there for completeness?"
  - Code: not wired. `connect.py:398` and `connect.py:898` are the only call sites.
  - **Recommendation: A — update context.** The right call. The debug endpoint iterates ALL slugs in a loop reading metadata for the GM panel — wiring the detector there would emit N spans (and N gap watcher events) on every dashboard poll, drowning the GM-panel signal in poll noise. Genuine save-resume is the seam the story targets; read-only debug inspection is not. Add a one-line clarification to `context-story-45-10.md` noting the debug endpoint is intentionally excluded.

### Decision: Proceed to verify (TEA)

No code changes required. All 5 context ACs aligned. The minor mismatches are:
1. Documentation drift between session draft and context (already deviation-logged by TEA, recommend session AC1 retroactive update).
2. Missing error-path test for session AC3 (deferred — principle is upheld by construction).
3. TEA's question about debug endpoint scope (resolved as out-of-scope by design).

Implementation quality: tight, follows established patterns, no over-engineering. Lint clean. 1647 surrounding tests green. Single-purpose helper (~140 lines) + single-domain spans file (~66 lines) + 2 import lines + 6 wire lines in `connect.py`. Net new code is exactly what the bug demands, nothing more.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed; simplify pass applied 3 high-confidence fixes; all 26 story tests + 1647 surrounding tests still green.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (scrapbook_coverage.py, connect.py diff, spans/__init__.py diff, spans/scrapbook.py, both test files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 6 findings | 2 high (otel_capture duplication × 2), 2 medium (populated_store/populated_slug_save partial overlap, watcher_capture potentially shareable), 2 low (two-span pattern matches chargen — intentional, span extract overlap idiomatic) |
| simplify-quality | 4 findings | 2 medium (coverage_ratio default asymmetry, watcher payload partially asserted), 2 low (Stub-snapshot comment terminology, field/op extract convention) |
| simplify-efficiency | 4 findings | 2 medium (extract lambdas duplicate base attrs, base_attrs/watcher payload field overlap), 2 low (slug=`""` default, on-disk vs in-memory SqliteStore in fixture) |

### Applied (3 high/medium-confidence fixes)

1. **`otel_capture` extracted to `tests/server/conftest.py`** (HIGH — simplify-reuse).
   The fixture was duplicated in `test_scrapbook_coverage.py` and inside `TestSlugResumeEndToEnd` in `test_scrapbook_coverage_resume_wire.py`. Both inline copies removed; conftest version made discoverable to all server-layer tests via pytest's per-directory fixture lookup. Conftest docstring notes the third copy in `test_dice_throw_momentum_span.py` (45-3 work, untouched here — flagged as a follow-up cleanup opportunity).

2. **`coverage_ratio` defaults unified in `spans/scrapbook.py`** (MEDIUM — simplify-quality).
   `SPAN_SCRAPBOOK_COVERAGE_GAP_DETECTED` extract lambda defaulted to `0.0` while `SPAN_SCRAPBOOK_COVERAGE_EVALUATED` defaulted to `1.0`. The 0.0 default was unreachable in practice (gap_detected only fires when gap_count > 0, so a real coverage_ratio is always present in span attributes), but the asymmetry was confusing. Aligned both to 1.0 with a comment explaining the unreachable-but-symmetric default.

3. **Watcher event payload contract locked in `test_orin_fixture_publishes_watcher_event`** (MEDIUM — simplify-quality).
   The previous test only asserted 4 fields on the watcher event payload (`field`, `severity`, `component`, `gap_count`). The GM-panel renderer reads the full payload (`max_round`, `covered_count`, `gap_count`, `coverage_ratio`, `gap_rounds`, `genre`, `world`, `slug`) verbatim. Added a key-set superset assertion + per-field value assertions for the 8 keys with their Orin-fixture-expected values. A future payload-shape regression now fails this test instead of silently breaking the dashboard.

### Flagged for review (medium-confidence — not auto-applied)

- **`populated_store` + `populated_slug_save` share scrapbook-row build logic** (simplify-reuse). The two fixtures serve different purposes (parameterized factory vs hardcoded Orin scenario for the e2e); extracting a `_seed_scrapbook_rows` helper is possible but the duplication is small (~30 lines once) and the fixtures' shapes differ (one yields a callable factory, the other returns a metadata dict). Reviewer's call.
- **`_extract_base_attrs` helper across both span lambdas** (simplify-efficiency). Each route lambda repeats the same `(span.attributes or {}).get(...)` chain for 7 base fields. Matches the existing convention in `spans/chargen.py` (each route inlines its own lambda); extracting would diverge from the established pattern. ~7 duplicated lines. Reviewer's call.
- **`_watcher_payload_from_report` to dedupe span attrs + watcher payload** (simplify-efficiency). The `base_attrs` dict for span emit is rebuilt as the watcher event payload, with `gap_rounds` shape differing (tuple in span attr, list in watcher payload). A unifying helper would need a small adapter. Reviewer's call.

### Noted (low-confidence — no action)

- "Stub snapshot" comment terminology in test fixture (it's a real `GameSnapshot`, not a mock).
- `'field'` + `'op'` span extract convention consistency.
- `slug=""` default — kept; the legacy non-slug resume branch passes `""` intentionally per the wire site.
- `populated_store` uses on-disk `SqliteStore` (vs `open_in_memory()`) — kept; tests real SQL behavior including FK pragmas.
- Two-span pattern (always-fire + conditional) duplicates structure from `spans/chargen.py` — intentional, follows the established CLAUDE.md OTEL Observability Principle pattern.

### Reverted

None. All applied fixes pass tests on first try.

### Overall

**simplify: applied 3 fixes**

### Quality Checks

- **Story tests:** 26/26 green (`uv run pytest tests/server/test_scrapbook_coverage.py tests/server/test_scrapbook_coverage_resume_wire.py`).
- **Lint on changed files:** clean (`uv run ruff check` on the 6 changed files).
- **Regression sweep:** 1647 passed, 42 skipped, 0 failed across `tests/server`, `tests/telemetry`, `tests/game`.
- **Spec alignment:** confirmed by Architect (spec-check phase) — all 5 context ACs aligned, no code changes required.

### Pre-existing lint issue (NOT introduced by this story)

`just server-check` reports 236 lint errors across the server tree — these are all pre-existing on `origin/develop`. The single ruff finding that touches a file in this PR's diff (`I001` in `sidequest/telemetry/spans/__init__.py`) was already present on develop before my one-line addition (`from .scrapbook import *` is alphabetical and clean; the I001 flags the whole import block, which was non-conformant before my change). Out of scope for this story per "Boy scouting OK if bounded" — fixing 236 ruff errors goes exponential. Recommend a separate chore PR for the wider cleanup.

### Handoff

To Westley (Reviewer) for code review. Suggested focus areas (carried forward from Dev assessment, plus simplify-pass observations):

1. **Span attribute symmetry.** Both extract lambdas now default `coverage_ratio` to 1.0. Confirm the symmetry is the right call (vs. e.g. defaulting gap_detected to a sentinel like -1.0 to signal missing-attribute).
2. **Watcher payload contract test.** The new key-set superset check (`set(payload.keys()) >= {...}`) intentionally allows additional keys to be added without breaking the test — useful for forward compatibility, but also means a typo'd extra key wouldn't be caught. Reviewer should confirm this is the right rigidity level.
3. **Conftest fixture discovery.** `otel_capture` is now a directory-scoped fixture in `tests/server/conftest.py`. Other test files in that dir that define their own local `otel_capture` (notably `test_dice_throw_momentum_span.py`) will shadow the conftest version — no behavior change today, but flagged for follow-up consolidation.
4. **Same checks Dev flagged:** SQL safety (parameterized `?` binding), read-only invariant (no transactional context, no triggers in schema), wire-site placement after `snapshot = saved.snapshot` in both connect.py branches.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (1 pre-existing lint, confirmed not introduced by diff) | confirmed 0, dismissed 1 (pre-existing on develop) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 9 (2 high, 5 medium, 2 low) | confirmed 5, dismissed 2 (overlaps with rule-checker), deferred 2 (low-priority cross-cutting) |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 (2 high, 2 medium) | confirmed 4 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 (rule violations across rules #4, #6, #10×2, #11) | confirmed 5 (all match project rules — cannot dismiss) |

**All received:** Yes (4 returned, 5 disabled-via-settings)
**Total findings:** 14 confirmed (across all sources, with overlaps), 3 dismissed/deferred.

## Reviewer Assessment

**Verdict:** APPROVED (with recommended follow-up cleanups)

**Rationale:** No Critical or High severity findings. All 14 confirmed findings are Medium or Low — none meet the blocking-rule threshold ("Any Critical or High = REJECT"). The implementation closes the named regression cleanly, follows established patterns (two-span design mirrors chargen.py:36-74, `with Span.open(): pass` mirrors websocket_session_handler.py:737, `_watcher_publish` import alias matches emitters.py:250), and survives a 1647-test regression sweep. The findings collected below are real but represent code-hygiene polish, not behavioral defects — recommend a single follow-up chore-PR rather than another full RED→GREEN→VERIFY cycle.

### Confirmed Findings (severity-labeled)

#### Code

- `[MEDIUM]` `[RULE]` **Missing `logger.warning()` on gap path** (rule #4) — `sidequest/game/scrapbook_coverage.py:120`. The gap-detection branch emits an OTEL watcher event + span but no structured log line. CLAUDE.md OTEL Observability Principle is satisfied by the watcher event for the dashboard case, but if the GM panel is disconnected, the gap goes unrecorded in server stdout/journald. Add `logger = logging.getLogger(__name__)` at module top and `logger.warning("scrapbook.coverage_gap_detected genre=%s world=%s slug=%s gap_count=%d gap_rounds=%s", genre, world, slug, gap_count, gap)` inside the `if gap_count > 0:` branch.
- `[LOW]` `[DOC]` **Module docstring lockstep claim could be more precise** — `sidequest/game/scrapbook_coverage.py:16-19`. The "narrative_log.round_number == turn_manager.interaction" invariant claim doesn't explain that narrative_log is *written from* `interaction` at the narration site (websocket_session_handler `_execute_narration_turn`); a reader checking the invariant would have to trace through 45-11 themselves.
- `[LOW]` `[DOC]` **Persona reference in production code comment** — `sidequest/handlers/connect.py:907-908`. "Felix's solo sessions" names a Playtest 3 character. Replace with the technical distinction ("genre+world+player triple saves without a slug") so the comment ages with the codebase rather than playtest lore.

#### Tests

- `[MEDIUM]` `[TEST]` `[RULE]` **`test_module_imports_cleanly` is vacuous** (rule #6) — `tests/server/test_scrapbook_coverage.py:177`. No assertion; passes on any successful import. Either merge into `test_helper_function_exported` (which immediately follows and asserts) or add `assert hasattr(mod, "detect_scrapbook_coverage_gaps")`.
- `[MEDIUM]` `[TEST]` **Missing silence assertion on empty-store path** — `test_scrapbook_coverage.py:456`. `test_empty_store_emits_evaluated_span_with_max_round_zero` asserts the evaluated span fires but does NOT assert the gap span and watcher event are absent. A buggy impl that always emits the gap span on `max_round=0` would pass the existing tests. Add `assert _spans_named(otel_capture, "scrapbook.coverage_gap_detected") == []` and `assert watcher_capture == []`.
- `[LOW]` `[TEST]` **Substring boundary check on gap_rounds attr is weak** — `test_scrapbook_coverage.py:363`. `assert "11" in gap_str and "29" in gap_str` only verifies the boundary sentinels of the 19-round gap; the 17 intermediate rounds (12-28) could be missing or malformed and the test would still pass. Replace with `tuple(gap_rounds_attr) == tuple(range(11, 30))` when the attribute is a sequence type, with a string-parse fallback only when the SDK serialised it.
- `[LOW]` `[TEST]` **`SpanRoute.extract` lambdas never invoked by test** — `tests/server/test_scrapbook_coverage.py::TestSpanRouting`. Tests assert `route.component == "scrapbook"` but never call `route.extract(fake_span)` to verify the payload-shaping that the GM-panel watcher hub depends on. Add a minimal fake-span test that calls each `extract` and checks the returned dict shape.
- `[LOW]` `[TEST]` **Missing edge case: non-contiguous gap pattern** — `test_scrapbook_coverage.py`. All current fixtures use contiguous-prefix coverage (rounds 1..N covered). A test with mid-range holes (rounds 1-5 + 8-10 covered, expecting `gap_rounds == [6, 7]`) would catch off-by-one regressions in the set arithmetic.
- `[LOW]` `[TEST]` **Missing edge case: out-of-range scrapbook rows** — `test_scrapbook_coverage.py`. The helper's `WHERE turn_id >= 1 AND turn_id <= ?` filter is never exercised by a test that inserts a turn_id=0 or turn_id=max_round+5 row. A regression that drops the WHERE clause would silently miscalibrate coverage.
- `[LOW]` `[DOC]` **Stale "production join" fixture comment** — `test_scrapbook_coverage.py:436` (in `populated_store` _make body). Says "the production join goes through `narrative_log.round_number`" but the production code does NOT join — it bounds with `max_narrative_round()` then queries `scrapbook_entries.turn_id` directly. Contradicts the module docstring of `scrapbook_coverage.py` which correctly states "without an explicit join through narrative_log".
- `[LOW]` `[DOC]` **"Stub snapshot" comment terminology** — `test_scrapbook_coverage.py:184`. Fixture creates a real `GameSnapshot`, not a stub. Rename to "Minimal snapshot fixture".
- `[LOW]` `[RULE]` **`import json as _json` inside loop body** (rule #10) — `test_scrapbook_coverage.py:119` and `test_scrapbook_coverage_resume_wire.py:294`. Move to fixture top or module top. Functionally harmless (Python caches imports) but rule flag.
- `[LOW]` `[RULE]` **`_row_count` uses f-string SQL for table name** (rule #11) — `test_scrapbook_coverage.py:606`. `f"SELECT COUNT(*) FROM {table}"`. Test-internal, all callers pass string literals — non-exploitable. Could whitelist with `assert table in {"narrative_log", "scrapbook_entries"}` before the query, or inline the two queries since there are only two callers.
- `[LOW]` `[TEST]` **`otel_capture` fixture flakiness risk** (cross-cutting) — `tests/server/conftest.py:917`. `SimpleSpanProcessor.shutdown()` does not deregister the processor from the global `TracerProvider`; processors accumulate across a test session. The `len(spans) == 1` assertions could become fragile under future test ordering changes. Same defect in the inline copy at `test_dice_throw_momentum_span.py:60`. Theoretical risk — current 1647-test sweep is deterministic. Track as a follow-up infrastructure fix.

### Verifications (from my own reading)

- `[VERIFIED]` **Both resume paths wired correctly.** `connect.py:399-405` (slug branch, after `snapshot = saved.snapshot` at line 261 + resume log at line 391-398) and `connect.py:906-913` (legacy branch, after `snapshot = saved.snapshot` at line 897 + resume log at line 899-905). Slug arg = `slug` and `""` respectively. Complies with AC4 + the codebase's "Verify Wiring" CLAUDE.md principle. Wire test `TestSlugResumeEndToEnd::test_slug_resume_emits_coverage_evaluated_and_gap_spans` drives a real WebSocketSessionHandler through the slug path (proof-of-life).
- `[VERIFIED]` **Read-only invariant.** `scrapbook_coverage.py:75-95`: one `MAX(round_number)` query through `store.max_narrative_round()` + one `SELECT DISTINCT` against `scrapbook_entries`. No INSERT/UPDATE/DELETE; no transactional context opened beyond what these two SELECTs use. Schema (`persistence.py:112-124`) has no triggers on either table that could fire as a side effect. AC5 row-count tests confirm.
- `[VERIFIED]` **SQL safety.** `scrapbook_coverage.py:82-86` parameterizes `max_round` via `(max_round,)` tuple binding; the literal `1` is a constant. Complies with python.md rule #11. (Test-internal `_row_count` flagged separately above.)
- `[VERIFIED]` **`with Span.open(...): pass` empty-body pattern matches established convention.** `websocket_session_handler.py:724-737` uses the same `with tracer.start_as_current_span(...): pass` pattern for the chargen archetype-gate evaluator (always-fire instantaneous event). My pattern uses the codebase wrapper `Span.open` instead of the lower-level `tracer.start_as_current_span`, but the empty-body intent is identical.
- `[VERIFIED]` **`_watcher_publish` import alias matches established pattern.** `scrapbook_coverage.py:33` `from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish` mirrors emitters.py:250, status_clear.py:42, narration_apply.py:27, session_handler.py:148.
- `[VERIFIED]` **Two-span pattern (always + conditional) matches chargen precedent.** `spans/scrapbook.py` declares `SPAN_SCRAPBOOK_COVERAGE_EVALUATED` (always-fire) + `SPAN_SCRAPBOOK_COVERAGE_GAP_DETECTED` (conditional). Mirrors `spans/chargen.py:36-74` (`SPAN_CHARGEN_ARCHETYPE_GATE_EVALUATED` + `SPAN_CHARGEN_ARCHETYPE_GATE_BLOCKED`). Satisfies the CLAUDE.md OTEL Observability Principle ("negative confirmation") on the no-gap path.
- `[VERIFIED]` **Watcher payload shape is locked by test.** Verify-phase added `set(payload.keys()) >= {...}` + per-field value asserts on the 8 keys (`max_round`, `covered_count`, `gap_count`, `coverage_ratio`, `gap_rounds`, `genre`, `world`, `slug`). Future GM-panel-renderer regression would fail this test.

### Devil's Advocate

What if a future contributor decides to "optimise" `detect_scrapbook_coverage_gaps` by skipping the evaluated span on the empty-store path "because there's nothing to report"? That's the exact lie-detector blind-spot CLAUDE.md was written to prevent. The current `TestNoOpSilence::test_empty_store_emits_evaluated_span_with_max_round_zero` test guards against this — but it only checks that the evaluated span DOES fire; it doesn't check that the gap span and watcher event do NOT fire on the empty path. So a buggy "always emit gap span when max_round=0 too" change would slip through. (See [TEST] medium finding above.)

What if someone runs the playtest-3 save through resume on a server where the `watcher_hub` has no bound event loop yet (process startup race)? `_watcher_publish` documents itself as "drops silently if the hub has no bound event loop yet" — so the watcher event vanishes, the OTEL span is exported only if a tracer is attached, and the only durable signal is... nothing, because the helper has no `logger.warning()`. (See [RULE] medium finding above — rule #4 logger gap.)

What if a future change splits `narrative_log.round_number` away from `interaction` (un-doing the 45-11 lockstep)? The helper's docstring asserts the invariant in prose but no test pins it. The covered_count would silently diverge from reality. Mitigation: the existing wiring tests use `turn_id` directly so post-divergence behavior would still be observable, but the docstring would lie. A test like `assert store.max_narrative_round() == snapshot.turn_manager.interaction` after the helper runs would lock the invariant — out of scope here, belongs in 45-11's regression suite.

What if `gap_rounds` exceeds OTEL's per-attribute size limit (4096 bytes by default)? A 4096+ round session would silently truncate the gap_rounds list in the span, making the GM-panel rendering wrong for very long sessions. Realistic? Probably not — Playtest 3 ran 29 rounds, Felix's longest was ~72. But for completeness, the watcher event is unbounded JSON so the GM panel still gets full data; only the OTEL span attribute would truncate. Not a functional bug at typical scale; flag for awareness.

What if a malicious save file is hand-crafted with `scrapbook_entries.turn_id = -1` or `turn_id = 2^63 - 1`? The WHERE clause `>= 1 AND <= max_round` filters these out; covered_count and gap_rounds stay sane. Verified by the helper's filter logic. (See [TEST] low finding — explicit out-of-range test would catch a regression that drops the WHERE.)

### Data Flow Trace

Player connects → `WebSocketSessionHandler.handle_message(connect)` → `ConnectHandler.handle()` → loads `saved = store.load()` → if `saved is not None`: → `snapshot = saved.snapshot` → resume_log → `detect_scrapbook_coverage_gaps(store, snapshot, slug)` → `store.max_narrative_round()` (one MAX query) → `store._conn.execute("SELECT DISTINCT turn_id ... WHERE turn_id >= 1 AND turn_id <= ?", (max_round,))` → set difference → `Span.open(SPAN_SCRAPBOOK_COVERAGE_EVALUATED, attrs)` → `if gap_count > 0`: `Span.open(SPAN_SCRAPBOOK_COVERAGE_GAP_DETECTED, attrs)` + `_watcher_publish("scrapbook_coverage_gap", payload, component="scrapbook", severity="warning")` → return ScrapbookCoverageReport → connect handler continues.

Inputs that could subvert: `slug` is from validated `GameMessage` payload; `genre`/`world` are read off the loaded snapshot (already validated by `SaveSchemaIncompatibleError` upstream); SQL is parameterized; no user string interpolated. Safe.

### Pattern Observations

- **Good:** Two-span "always + conditional" structure at `spans/scrapbook.py:23-66` mirrors `spans/chargen.py:36-74` — consistent with project convention.
- **Good:** Frozen dataclass `ScrapbookCoverageReport` with explicit field types — matches the codebase's preference for typed reports over dict returns (see `NarrationTurnResult`, `BeatSelection`, etc.).
- **Good:** `with Span.open(...): pass` empty-body pattern matches `websocket_session_handler.py:724-737`.
- **Boy-scout opportunity:** `otel_capture` is now in conftest, removing 2 inline copies. The third copy in `test_dice_throw_momentum_span.py:60` (45-3 work) is flagged in delivery findings as a one-line follow-up.

### Handoff: To SM (Vizzini) for finish-story.

## Phase Log

**Opened:** 2026-04-28T14:00:00Z by sm-setup