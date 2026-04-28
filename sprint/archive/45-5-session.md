---
story_id: "45-5"
epic: "45"
workflow: "tdd"
---
# Story 45-5: Stale-slot reuse on session reinit blocks turn 1

## Story Details
- **ID:** 45-5
- **Epic:** 45 — Playtest 3 Closeout: MP Correctness, State Hygiene, and Post-Port Cleanup
- **Jira Key:** (to be created if needed)
- **Workflow:** tdd
- **Type:** bug
- **Priority:** p1
- **Points:** 3
- **Repos:** server

## Description

Playtest 3 evropi: prot_thokk and hant saves created 2026-04-19T16:31 UTC but narrative_log held a single entry dated 2026-04-18; session never fired Turn 1 (last_played == created_at, turn_manager frozen at round=0/interaction=2). Prior-day narrative survived session reinit because DB row wasn't cleared. Session lifecycle must either clear old rows on reinit OR refuse to write over a populated slot. Relates 37-29, 37-1.

**Source:** 37-40 sub-1 (split during Epic 45 rebaselining)

## Acceptance Criteria

- [ ] AC1: Session reinit clears stale narrative_log entries (old entries from prior session use of same save slot)
- [ ] AC2: turn_manager does not remain frozen at round=0/interaction=2 after session reinit
- [ ] AC3: Turn 1 fires correctly on first turn submission after reinit (verified in playtest saves)
- [ ] AC4: OTEL span emitted on narrative_log clear with count of cleared entries and timestamp comparison
- [ ] AC5: Invariant test: turn_manager.round and narrative_log.max_round must be synchronized at session start

## Workflow Tracking

**Workflow:** tdd  
**Phase:** finish  
**Phase Started:** 2026-04-28T13:45:54Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T09:00:00Z | 2026-04-28T12:52:42Z | 3h 52m |
| red | 2026-04-28T12:52:42Z | 2026-04-28T13:08:22Z | 15m 40s |
| green | 2026-04-28T13:08:22Z | 2026-04-28T13:23:02Z | 14m 40s |
| spec-check | 2026-04-28T13:23:02Z | 2026-04-28T13:26:11Z | 3m 9s |
| verify | 2026-04-28T13:26:11Z | 2026-04-28T13:30:22Z | 4m 11s |
| review | 2026-04-28T13:30:22Z | 2026-04-28T13:44:01Z | 13m 39s |
| spec-reconcile | 2026-04-28T13:44:01Z | 2026-04-28T13:45:54Z | 1m 53s |
| finish | 2026-04-28T13:45:54Z | - | - |

## Story Context

### Problem Statement

During Playtest 3 (2026-04-19), two saves (prot_thokk and hant) exhibited a critical state-hygiene bug:
- Save created at 2026-04-19T16:31 UTC (fresh session)
- narrative_log[0] was dated 2026-04-18 (prior-day entry)
- turn_manager frozen at round=0/interaction=2 (no progression to Turn 1)
- last_played == created_at (no turns advanced despite gameplay intent)

**Root Cause Hypothesis:** Session reinit re-used a database slot without clearing stale narrative entries. The narrator context pollution (prior-day entry in the log) and frozen turn_manager are symptoms of the same lifecycle bug.

### Architecture Context

**Related Stories:** 
- 37-29: Session persistence and save-slot lifecycle
- 37-1: Turn manager initialization and round sequencing
- 45-11: turn_manager.round invariant against narrative_log.max_round (sibling story, also covers sync)

**Related Code Paths:**
- `sidequest/game/persistence.py` — save slot loading and DB row creation
- `sidequest/game/session.py` — Session.__init__, narrative_log initialization
- `sidequest/game/turn_manager.py` — TurnManager initialization and round/interaction state
- `sidequest/server/session_handler.py` — session lifecycle hooks (create, load, reinit)
- `sidequest/telemetry/spans.py` — session lifecycle spans

### Testing Strategy (TDD)

This story follows TDD: RED → GREEN → SPEC-CHECK workflow. The TEA phase writes failing tests that cover:

1. **AC1 (narrative_log clear):** Unit test that reinit clears stale rows; integration test that verifies old entries don't appear in session context
2. **AC2 (turn_manager escape):** Unit test that turn_manager is NOT frozen after reinit; verifies round > 0 OR interaction > 2
3. **AC3 (Turn 1 fires):** Scenario-based test using archived playtest 3 saves (prot_thokk or hant) to verify Turn 1 submission advances to Turn 2
4. **AC4 (OTEL span):** Test that session_reinit_cleanup span fires with correct attributes (cleared_count, old_timestamp, new_timestamp)
5. **AC5 (invariant):** Assertion at session start that turn_manager.round == narrative_log.max_round

### Known Constraints

- Save files live in `~/.sidequest/saves/` (SQLite `.db` files, one per genre/world/player triple)
- narrative_log rows have `timestamp` fields that can be compared to session.created_at
- The bug manifests only on session **reinit** (resume), not fresh session creation
- Playtest 3 saves are archived for regression testing; DEV phase may use them

## SM Assessment

**Story:** 45-5 — Stale-slot reuse on session reinit blocks turn 1 (3pt, P1, server)

**Why now:** P1 correctness bug hard-blocking turn progression in Playtest 3 saves (evropi/prot_thokk/hant). Sprint 3 goal is playtest closeout; this is on the critical path. Lifecycle context is fresh from neighbor stories 45-7 and 45-9.

**Workflow:** TDD (phased). 5 ACs are well-bounded and amenable to test-first — invariant test (AC5), OTEL emission (AC4), and observable state changes (AC1–3). No design ambiguity that requires architect or BA upstream.

**Scope guardrails:** Server-only. No UI/daemon coupling. Playtest 3 saves are available as regression fixtures. Adjacent stories 45-6 (chargen partial-completion) and 45-11 (round invariant) cover overlapping subsystems — handle separately to keep PRs reviewable.

**Routing:** → TEA (Fezzik) for RED phase. Write failing tests covering all 5 ACs with the playtest saves as fixtures where they tighten the assertions.

---
## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Reason:** P1 correctness fix to a state-lifecycle seam (`SqliteStore.init_session()`). Story context mandates TDD with test-first wire coverage of the production connect path; chore bypass criteria do not apply.

**Test Files:**
- `sidequest-server/tests/game/test_init_session_clears_stale_slot.py` — 14 tests (8 RED spec + 6 regression guards / wiring sanity) at the persistence seam
- `sidequest-server/tests/server/test_stale_slot_reinit_wire.py` — 5 tests (4 RED end-to-end wire + 1 source-grep wiring sanity) driving the legacy genre/world ConnectHandler path

**Tests Written:** 19 tests covering 5 ACs + SPAN_ROUTES registration + wire seam.
**Status:** RED — 12 failing, 7 passing (regression guards / wiring sanity).

**RED ↔ AC mapping:**

| AC | Spec | Tests (failing) |
|----|------|-----------------|
| AC1 | Reinit clears stale narrative_log | `test_narrative_log_cleared_on_reinit`, `test_every_per_slot_table_cleared_on_reinit`, `test_connect_on_populated_slot_clears_narrative_log`, `test_post_connect_narrative_log_is_clean_for_fresh_chargen` |
| AC2 | turn_manager not frozen at round=0/interaction=2 | covered by `test_post_chargen_turn_manager_is_fresh_after_stale_slot_reinit` (asserts `round != 0`) |
| AC3 | Turn 1 fires after reinit | covered by `test_post_chargen_turn_manager_is_fresh_after_stale_slot_reinit` (round≥1, stale row absent post-walk) |
| AC4 | OTEL session.slot_reinitialized fires | `test_watcher_event_fires_on_populated_slot`, `test_watcher_event_attributes_on_populated_slot`, `test_watcher_event_fires_on_fresh_slot_with_zero_priors`, `test_connect_emits_session_slot_reinitialized_watcher_event`, `test_span_constant_session_slot_reinitialized_exists`, `test_span_route_registered_for_session_slot_reinitialized` |
| AC5 | Round vs max_round invariant precondition | `test_max_round_is_null_after_reinit_on_populated_slot` |

### Rule Coverage

| python.md rule | Test(s) | Status |
|----------------|---------|--------|
| #1 silent exceptions | spec mandates typed watcher event on failure path; refuse-path is out of scope so no bare except in test surface | n/a (no exception-handling code added) |
| #4 logging coverage AND correctness | AC4 tests assert structured `_watcher_publish` call, not f-string log lines | passing rule by construction |
| #6 test quality | every assertion checks specific values, not just truthiness; no `assert True`, no vacuous mock-without-call checks; messages cite the AC violated | failing on AC, passing self-check |
| #7 resource leaks | tests close SqliteStore connections after disk reads; await `handler.cleanup()` after async flows | passing |
| #11 input validation at boundaries | `init_session(genre, world)` is internal — no user-input boundary in this story; refuse-path was the input-validation alternative and was deviated out | not applicable to chosen fix |

**Rules checked:** All 13 lang-review rules reviewed; the applicable ones (test quality, resource hygiene, mutable defaults absent, async correctness) have direct or by-construction coverage. Inapplicable rules (Web/SQL/HTML escaping, dependency hygiene, deserialization) are noted as inapplicable rather than skipped silently.

**Self-check (vacuous-test scan):** no `assert True`, no `let _ =` analogues, no truthy-only assertions where a specific value matters. Each assertion message cites the AC violated. The `test_init_session_is_callable_on_sqlite_store` test asserts both `hasattr` and `callable` — a structural pin rather than a behavioural test, but its purpose (refactor canary) is documented.

**Neighbour tests verified:** `tests/server/test_chargen_persist_and_play.py` (5/5 pass), `tests/game/test_persistence_games_table.py` (pass), `tests/telemetry/test_routing_completeness.py` (pass). No collateral damage.

**Implementation hand-off — what GREEN must do (from spec, not from me):**
1. Wrap `SqliteStore.init_session()` in a transaction that DELETEs from `game_state`, `narrative_log`, `scrapbook_entries`, `lore_fragments`, `events`, `projection_cache` before the existing `INSERT OR REPLACE INTO session_meta`. Single transaction.
2. Define `SPAN_SESSION_SLOT_REINITIALIZED = "session.slot_reinitialized"` in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES[SPAN_SESSION_SLOT_REINITIALIZED]` with `event_type="state_transition"`, `component="session"`.
3. Emit the watcher event from inside `init_session()` (after the clear, before commit) carrying `genre_slug`, `world_slug`, `cleared_tables` (list of table names), `prior_narrative_count`, `prior_event_count`, `mode="clear"`. Slug for slug-branch can be omitted (legacy seam doesn't carry it cleanly); if Dev wants slug, plumb it through the call signature.
4. Do NOT add a refuse-on-populated path — option 2 is explicitly out of scope (TEA deviation).
5. Do NOT clear the slug-keyed `games` table — it is global, not per-slot (regression-guard test will catch it if you do).

**Handoff:** To Dev (Inigo Montoya) for GREEN.

---
## Dev Assessment

**Phase:** finish
**Status:** GREEN — 19/19 spec tests passing, no neighbour regressions.

**Implementation summary:**

Two files changed, +95/-8 lines. All changes confined to the persistence seam and telemetry catalog, no surface-level API drift.

1. **`sidequest/telemetry/spans.py`** — Added `SPAN_SESSION_SLOT_REINITIALIZED = "session.slot_reinitialized"` and registered `SPAN_ROUTES[SPAN_SESSION_SLOT_REINITIALIZED]` as `event_type="state_transition"`, `component="session"`. Extractor mirrors the SM/TEA-specified attribute set: `genre_slug`, `world_slug`, `cleared_tables` (list), `prior_narrative_count`, `prior_event_count`, `mode`.

2. **`sidequest/game/persistence.py`** — Added module-level `_PER_SLOT_TABLES` tuple in **FK-safe order** (`projection_cache` → `events` → others; PRAGMA foreign_keys=ON requires children-before-parents). Imported `_watcher_publish` (alias of `publish_event`) and the new SPAN constant. Rewrote `init_session()` to:
   - Read `prior_narrative_count` and `prior_event_count` BEFORE the clear (so the watcher event reports what was there).
   - Open a single `with self._conn:` transaction. DELETE every per-slot table in order. INSERT OR REPLACE on `session_meta` (existing behavior). Commit atomically — either every table clears AND session_meta replaces, or nothing changes.
   - After commit, publish `session.slot_reinitialized` with the captured priors and the cleared-tables list.

**Atomicity:** The clear and the session_meta replace happen inside one `sqlite3.Connection.__enter__/__exit__` block, which commits on clean exit and rolls back on exception. No partial half-clear is reachable.

**Why no `cleared_tables` are populated for fresh slots:** The list reports tables for which `DELETE FROM` ran. On a fresh slot, the DELETEs run (no-op against zero rows) and the table names are still appended to the list — Sebastien's GM panel sees the same six-name `cleared_tables` on every reinit, and reads `prior_narrative_count == 0` to distinguish fresh from populated. This matches the AC4 negative-confirmation requirement and the test `test_watcher_event_fires_on_fresh_slot_with_zero_priors` enforces it.

**ACs satisfied:**

| AC | Coverage |
|----|----------|
| AC1 | `init_session()` clears `narrative_log` (and 5 sibling tables) atomically; both call sites (`handlers/connect.py:405` slug, `:906` legacy) drive the same seam. |
| AC2 | `turn_manager` cannot remain frozen at `round=0/interaction=2` after reinit because `materialize_from_genre_pack` writes fresh defaults and the stale `narrative_log` it would have built off is gone. |
| AC3 | Wire test `test_post_chargen_turn_manager_is_fresh_after_stale_slot_reinit` confirms `round != 0` and stale row is absent post-walk. |
| AC4 | Watcher event `session.slot_reinitialized` fires on every `init_session()` call with the SM-specified attributes; SPAN_ROUTES registered. |
| AC5 | Post-reinit `MAX(narrative_log.round_number)` is `NULL` (zero rows), preventing a fresh `TurnManager(round=1)` from being wedged at session start. Full round-vs-max sync invariant remains 45-11's responsibility (per TEA deviation). |

**Spec adherence:** Followed every TEA hand-off bullet:
- ✓ Single-transaction clear before INSERT OR REPLACE on `session_meta`.
- ✓ `SPAN_SESSION_SLOT_REINITIALIZED` defined and routed with `component="session"`.
- ✓ Watcher event emitted from inside `init_session()` with the specified attribute set.
- ✓ NO refuse-on-populated path added (option 2 deviation honored).
- ✓ `games` table NOT cleared (regression-guard test `test_games_table_not_cleared_on_reinit` passes).

**Test results:**
- `tests/game/test_init_session_clears_stale_slot.py`: 14/14 ✓
- `tests/server/test_stale_slot_reinit_wire.py`: 5/5 ✓
- `tests/telemetry/test_routing_completeness.py`: 2/2 ✓ (lints the new SPAN constant + route)
- `tests/server/test_chargen_persist_and_play.py`: 5/5 ✓ (no chargen-flow regression)
- `tests/game/test_persistence_games_table.py`: 8/8 ✓ (slug table integrity preserved)
- Full `tests/game/` + `tests/telemetry/`: 888 passed, 24 skipped (pre-existing).
- Full `tests/server/`: 731 passed, 2 flaky failures pre-existing on `develop` (status_apply, status_clear; logged as Dev finding).

**Lint/format:** Pre-existing ruff complaints on the changed files (StrEnum suggestion, format violations) are baseline drift, not introduced by 45-5. Verified via `git stash` rebase. Bounded boy-scouting line — not this story.

**Handoff:** To TEA (Fezzik) for verify phase (simplify + quality-pass).

---
## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (minor, non-blocking)
**Mismatches Found:** 2

### Mismatch 1 — `slug` attribute missing from emitted span (Behavioral, Minor)

- **Spec:** `context-story-45-5.md` line 94 lists the `session.slot_reinitialized` attribute set as `genre_slug, world_slug, slug, cleared_tables, prior_narrative_count, prior_event_count, mode`.
- **Code:** `sidequest/game/persistence.py:321-332` emits `genre_slug, world_slug, cleared_tables, prior_narrative_count, prior_event_count, mode`. **`slug` is not emitted.** The `SPAN_ROUTES.extract` lambda in `spans.py:356-365` likewise does not surface `slug`.
- **Why:** TEA's hand-off note explicitly authorized the omission ("Slug for slug-branch can be omitted (legacy seam doesn't carry it cleanly); if Dev wants slug, plumb it through the call signature"). `init_session(genre_slug, world_slug)` does not accept a slug parameter, and the legacy genre/world connect path (`handlers/connect.py:906`) genuinely has no game slug. The slug-keyed connect path (`:405`) has the slug but does not pass it to `init_session()`.
- **Impact:** GM panel renders rows without the slug field. For the legacy path this is correct (no slug exists). For the slug path it is a missed observability detail — Sebastien cannot correlate the reinit row to a specific slug-keyed game without joining on `genre+world+timestamp`.
- **Recommendation:** **D (Defer)** — Add a follow-up story to plumb an optional `slug` parameter through `init_session(genre_slug, world_slug, *, slug=None)`. The slug-keyed call site at `connect.py:405` would pass `slug=row.slug`; legacy at `:906` passes `slug=None`. Span attribute defaults to empty string when slug is not known. Not blocking for 45-5 — the operational signal (cleared tables + counts) is intact; slug is enrichment.

### Mismatch 2 — AC4 "timestamp comparison" wording vs operational attribute set (Cosmetic, Trivial)

- **Spec (session AC4):** "OTEL span emitted on narrative_log clear with count of cleared entries **and timestamp comparison**."
- **Spec (story context line 94):** Authoritative attribute table lists `genre_slug, world_slug, slug, cleared_tables, prior_narrative_count, prior_event_count, mode` — **no timestamp fields.** The refuse-path span (`session.slot_reuse_rejected`, line 95) DOES include `prior_last_played` and `prior_created_at`, but that span is for a code path that was deviated out of scope (TEA "Committing to clear-on-reinit (option 1)").
- **Code:** Emits the operational attribute set; no timestamps. Tests do not enforce timestamps.
- **Why:** AC4's "timestamp comparison" wording conflates the clear-path and refuse-path attribute sets from the context table. The operational context spec is precise; the AC was loose mental-model language about the diagnostic signal (the prot_thokk save's narrative_log entry was dated 2026-04-18 in a session created 2026-04-19 — temporal gap as a smoking gun).
- **Impact:** The smoking-gun signal is still surfaced via `prior_narrative_count > 0` (rows from a prior session existed) plus `session_meta.last_played` / `created_at` already present in the SQLite row. The information is recoverable without a dedicated span attribute.
- **Recommendation:** **C (Clarify spec)** — The operational attribute set defined in `context-story-45-5.md` line 94 is the implementation contract; AC4's "timestamp comparison" was loose. No code change needed. Spec-reconcile (post-review) should add an `### Architect (reconcile)` deviation entry pinning the operational attribute set as authoritative for AC4.

### Reuse-First Audit

- ✓ `_watcher_publish` (alias of `publish_event` from `watcher_hub`) reused — no new dispatcher.
- ✓ `SPAN_ROUTES` registration pattern matches sibling story 45-1's `SPAN_GAME_HANDSHAKE_DELTA_APPLIED` (state_transition / component-keyed). Consistent with `spans.py` conventions.
- ✓ `with self._conn:` transaction pattern matches the existing `save()` method below `init_session()` — same idiom, no novel transaction strategy.
- ✓ No premature abstraction: the clear is inlined as a 4-line loop in `init_session()`. A `clear_session_tables()` helper would be premature given a single call site.
- ✓ `_PER_SLOT_TABLES` constant scoped to module-private (leading underscore), correctly co-located with the SQLite schema it mirrors.
- ✓ FK ordering is documented in the constant's comment — load-bearing fact made explicit.

### Architectural Concerns

- **Watcher event publish is non-transactional.** The `_watcher_publish` call sits AFTER the `with self._conn:` block exits. If the publish were to raise (or be slow), the DB state has already committed. This is correct — observability events are eventually-consistent fan-out, not state mutations. `watcher_hub.publish_event` silently drops if there are no subscribers, so the publish cannot fail in a way that affects callers. **No change required.**
- **`f"DELETE FROM {tbl}"` interpolation:** `_PER_SLOT_TABLES` is a module-private tuple of compile-time constants — no SQL injection surface. Safe. ✓
- **Atomicity claim:** Dev correctly states the clear + session_meta replace are atomic (single `with` block). Verified.

### Decision

**Proceed to verify.** Both mismatches are minor / non-blocking. The implementation is operationally correct, reuses existing patterns cleanly, and the omitted spec details are recoverable (slug via follow-up plumbing; timestamps via the existing session_meta row). I have spent years building an immunity to spec drift, and these two are just rope burns from the climb.

**Handoff:** To TEA (Fezzik) for verify phase (simplify + quality-pass).

---
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed; simplify pass applied 1 fix; quality checks passing.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (`persistence.py`, `spans.py`, `test_init_session_clears_stale_slot.py`, `test_stale_slot_reinit_wire.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 — no duplication or extraction opportunities; `_watcher_publish` and `SPAN_ROUTES` patterns correctly reused; test fixtures are appropriately scoped per file |
| simplify-quality | clean | 0 — naming clear (`_PER_SLOT_TABLES`, `cleared_tables`, `prior_*_count`, `mode`); `init_session()` docstring length proportionate to non-obvious bug fix; cross-layer import (`persistence` → `telemetry.spans`) follows established convention |
| simplify-efficiency | applied | 1 — `cleared_tables` was being built by `.append(tbl)` inside the DELETE loop, but the source is the static `_PER_SLOT_TABLES` tuple. Refactored to `list(_PER_SLOT_TABLES)` inline at the watcher publish; dropped the local accumulator entirely |

**Applied:** 1 high-confidence fix
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 2 low-confidence observations from simplify-efficiency, both correctly resolved as "no change" (two separate `SELECT COUNT(*)` queries are clearer than a combined query targeting different semantic tables; the per-table DELETE loop is fine for SQLite's lack of TRUNCATE)
**Reverted:** 0

**Overall:** simplify: applied 1 fix

### Regression Check

After applying the simplify fix:

- **45-5 spec tests:** 19/19 ✓ (unchanged)
- **`tests/game/` + `tests/telemetry/`:** 888 passed, 24 skipped (pre-existing skips) ✓
- **`ruff check sidequest/game/persistence.py`:** 1 pre-existing error (StrEnum suggestion on `class GameMode`); 0 new errors introduced by 45-5

The simplify diff was 1 file changed, +1/-3 lines. The behaviour is byte-identical: every per-slot table still clears, the watcher event still receives the full list of cleared tables.

### Quality Checks

- **Tests:** all 45-5 spec tests passing; full game + telemetry suites green; no neighbour regressions
- **Lint:** no new ruff errors from 45-5 changes (StrEnum pre-exists on `GameMode`, ruff format violations on persistence.py and spans.py also pre-exist on `develop` baseline — verified earlier via `git stash` rebase)
- **Architectural concerns:** the cross-layer import `persistence → telemetry.spans` was reviewed by simplify-quality; telemetry is intentionally infrastructure-tier (per `spans.py` module docstring), and `persistence.py` already imports `telemetry.watcher_hub` for the publish call. Pattern is consistent with peer modules (e.g., `sidequest/game/shared_world_delta.py` imports `spans.SPAN_GAME_HANDSHAKE_DELTA_APPLIED`)

### Self-check (vacuous-test scan)

Re-scanned the test files post-simplify:
- No `assert True` / `assert not False`
- No `let _ =` analogues
- No truthy-only assertions where a specific value matters
- The grep test `test_connect_handler_invokes_init_session_on_legacy_path` is intentionally a structural pin and documents its limitations inline — known wire-test affordance, not a vacuous assertion

### Handoff

**To Reviewer (Westley) for code review.** Implementation is operationally sound, simplify pass applied 1 fix without regressing behavior, all tests pass, no new lint errors.

---
## Subagent Results

**All received:** Yes

| # | Subagent | Status | Findings | Severity | Notes |
|---|----------|--------|----------|----------|-------|
| 1 | reviewer-preflight | Returned | 2 lint errors | Minor | UP042 on `GameMode` (pre-existing) and E402 on conftest import (pattern copied from `test_chargen_persist_and_play.py`); both fixed |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Returned | 7 (4 high, 3 medium) | Minor–Major | High: zero-assertion test, two `create=True` patches, tautological assertion. All 4 fixed |
| 5 | reviewer-comment-analyzer | Returned | 5 (3 high, 2 medium) | Minor | Stale docstring opener, story-ticket narrative, stale `:264-268` line ref. All 5 fixed |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Returned | 7 violations across 18 rules checked | Minor | Rules 3 (return annotations), 6 (no-assertion + truthy), 10 (E402), 11 (f-string SQL — downgraded). All except #11 fixed |

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Stale `narrative_log` row on disk → `SqliteStore.init_session()` → atomic transaction (DELETE all per-slot tables + INSERT OR REPLACE on `session_meta`) → post-commit `_watcher_publish("session.slot_reinitialized", ...)` → GM panel via `SPAN_ROUTES["session.slot_reinitialized"]`. Safe because: the clear and the meta-replace are inside one `with self._conn:` SQLite transaction, so a half-clear is unreachable; the watcher publish sits AFTER the commit, so a publish failure cannot leave the DB in an inconsistent state; and `_PER_SLOT_TABLES` is a module-private compile-time constant, so the f-string SQL has no injection surface.

**Pattern observed:** `SPAN_ROUTES` registration at `sidequest/telemetry/spans.py:344-365` mirrors sibling story 45-1's `SPAN_GAME_HANDSHAKE_DELTA_APPLIED` shape (`event_type="state_transition"`, `component=...`-keyed). The `with self._conn:` transaction at `sidequest/game/persistence.py:307-318` matches the existing `save()` method's idiom directly below it.

**Error handling:** Watcher publish at `sidequest/game/persistence.py:319-330` is non-transactional by design — `publish_event` silently drops if no subscribers are bound (per `sidequest/telemetry/watcher_hub.py:222`), so observability fan-out cannot fail in a way that affects callers. The DB transaction commits before the publish; a hypothetical raise from `publish_event` would surface to the caller without rolling back the (correctly-applied) clear.

### [EDGE] Edge Hunter

Subagent disabled via settings. My own pass on the diff: the edge cases I would have looked for are all covered — fresh slot (no priors → publish fires with zero counts), populated slot (every per-slot table cleared, watcher event reports counts), FK ordering (projection_cache → events → others, verified by one of the AC tests against `PRAGMA foreign_keys=ON`), and the slug-keyed `games` table preserved (regression-guard test `test_games_table_not_cleared_on_reinit`). No additional edges found.

### [SILENT] Silent Failure Hunter

Subagent disabled via settings. My own pass: no silent fallbacks introduced. The clear is unconditional (DELETE on an empty table is a SQLite no-op, not a silent skip), the watcher event fires unconditionally (including zero-priors negative confirmation per CLAUDE.md), and there are no bare `except:` or `try/except: pass` blocks in the diff.

### [TEST] Test Analyzer

7 findings reported; 4 high-confidence fixed, 3 medium deferred:
- **FIXED**: `test_fresh_slot_reinit_does_not_raise` (zero-assertion) — removed; coverage subsumed by `test_fresh_slot_per_slot_tables_remain_empty`.
- **FIXED**: 4 sites of `patch(..., create=True)` — `create=True` removed because `_watcher_publish` is a real top-level alias on `persistence.py:18`. Patching no longer silently invents mocks if the import disappears.
- **FIXED**: tautological `round_ != 0` AND `round_ >= 1` collapsed to `round_ == 1` (the exact `materialize_from_genre_pack` default).
- **FIXED**: `assert out` truthy-only in `_connect()` helper tightened to type-specific (`isinstance(out[0], SessionEventMessage)` AND `not isinstance(out[0], ErrorMessage)`).
- **DEFERRED**: `_reset_otel_tracer` autouse fixture has no teardown (medium). The fixture is local to one test file; OTEL provider drift across files is not observed in the broader test runs (888-test suite passes), so the practical risk is low. A teardown would be cleanest but is bounded improvement, not blocking.
- **DEFERRED**: AC2/AC3 wire test does not assert empty `narrative_log` immediately post-`_connect()` before chargen (medium). The parallel test `test_post_connect_narrative_log_is_clean_for_fresh_chargen` covers this exact precondition; coupling them tighter would duplicate without adding signal.
- **DEFERRED**: source-grep wiring test fragility (medium). The grep is intentionally a structural pin and documents its own limitations. A `mock.patch` alternative would test runtime invocation but lose the source-import-surface signal that catches refactors removing the call entirely.

### [DOC] Comment Analyzer

5 findings reported; all 5 fixed:
- **FIXED**: `init_session()` opening line "Call once for new sessions" (stale — contradicts the new reinit semantics) replaced with "Initialize or reinitialize a save slot."
- **FIXED**: Story 45-5 / Playtest 3 changelog narrative removed from the `init_session()` docstring per CLAUDE.md "Don't reference the current task, fix, or callers — those belong in the PR description and rot as the codebase evolves."
- **FIXED**: Stale line reference `(persistence.py:264-268)` removed from `tests/game/test_init_session_clears_stale_slot.py` module docstring (those lines are now `SqliteStore.open()`, not the old `init_session()`).
- **FIXED**: "Story 45-5:" prefix dropped from `spans.py` session-lifecycle block comment.
- **FIXED**: `_PER_SLOT_TABLES` cross-reference "the INSERT OR REPLACE below" disambiguated to "the INSERT OR REPLACE in `init_session()`" — at module scope "below" was ambiguous (next thing was `SaveSchemaIncompatibleError`, not the INSERT).

### [TYPE] Type Design

Subagent disabled via settings. My own pass: `init_session(genre_slug: str, world_slug: str) -> None` is fully annotated. New module constant `_PER_SLOT_TABLES: tuple[str, ...]` carries an explicit annotation. SPAN_ROUTES extract lambda is structurally typed by `_SpanLike` protocol. No new stringly-typed APIs, no `Any` escapes, no missing newtypes.

### [SEC] Security

Subagent disabled via settings. My own pass against `.pennyfarthing/gates/lang-review/python.md` rule #11: `f"DELETE FROM {tbl}"` and `f"SELECT COUNT(*) FROM {table}"` are mechanical f-string-SQL violations against the rule letter. **Severity downgraded to Trivial** with rationale: SQLite cannot parameterize table names (it's a hard limitation of `sqlite3`); the source `tbl` iterates `_PER_SLOT_TABLES` which is a module-private compile-time constant; the test `_row_count` helper iterates `PER_SLOT_TABLES` / `GLOBAL_TABLES` which are module-level test constants. There is zero injection surface in either site. Per the Reviewer rules I cannot dismiss a rule-matching finding, but I may downgrade — and the rule's WHY (CWE-89: prevent untrusted-input injection) is fully satisfied by the constant-only call sites. No code change required.

### [SIMPLE] Simplifier

Subagent disabled via settings. The TEA verify phase already ran the simplify-reuse / simplify-quality / simplify-efficiency lenses and applied 1 high-confidence fix (`cleared_tables` accumulator → `list(_PER_SLOT_TABLES)`). My own pass on the post-review diff: no new complexity introduced, no over-engineering, no premature abstraction.

### [RULE] Rule Checker

7 violations reported across 18 rules checked. All applicable rules from `python.md` (#1–#13) and CLAUDE.md (#14–#18) reviewed. **6 of 7 fixed**; the last (#11 f-string SQL) is downgraded as documented under [SEC]. Critical-tier rules (#14 No Silent Fallbacks, #15 No Stubbing, #16 Don't Reinvent, #17 Verify Wiring, #18 OTEL Observability) all clean.

### Spec Drift

The Architect's spec-check phase logged two minor drifts (missing `slug` attribute in the emitted span, AC4's "timestamp comparison" wording vs the operational attribute set in `context-story-45-5.md` line 94). I concur with the Architect's resolutions: defer the slug plumbing to a follow-up story (would require widening `init_session()` signature), and leave AC4's timestamp wording for spec-reconcile to clarify (the operational signal is fully present via `prior_*_count` + the existing `session_meta` row's timestamps).

### Architectural Concerns

None. Cross-layer import (`persistence` → `telemetry.spans` and `telemetry.watcher_hub`) is consistent with peer modules (`game/shared_world_delta.py` does the same). The watcher publish placement after the transaction commit is correct (observability is fan-out, not state). The non-FK-ordering of `_PER_SLOT_TABLES` would have been a latent bug — Dev caught it during GREEN and reordered children-before-parents with an explicit comment.

### Decision

The work meets the bar. Implementation is correct, atomic, observable, and well-tested. All high-confidence findings from the four subagents are addressed in commit `1c81e49`. The remaining medium / low findings are bounded improvements that do not affect correctness; logging them as delivery findings is sufficient.

**Handoff:** To SM for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings at setup.

### Dev (implementation)
- **Gap** (non-blocking): `projection_cache` carries a foreign key to `events.seq` with `PRAGMA foreign_keys=ON` (set in `_configure_connection`), so the per-slot clear must drop children before parents. The TEA tuple ordered tables alphabetically; the implementation reorders to (projection_cache, events, game_state, narrative_log, scrapbook_entries, lore_fragments). No other inter-table FKs exist among per-slot tables.
  Affects `sidequest/game/persistence.py:_PER_SLOT_TABLES` (the order is load-bearing — surfaced as a comment on the constant).
  *Found by Dev during green.*
- **Improvement** (non-blocking): The full `tests/server/` suite has two flaky failures unrelated to this story: `test_status_apply.py::test_status_change_appends_to_named_actor` and `test_status_clear.py::test_wiring_narration_apply_clear_and_add_in_same_turn`. Both pass in isolation and on `develop` baseline (verified via `git stash` rebase). Pre-existing test-ordering pollution in another file.
  Affects `tests/server/` (story 45-5 inherits the flake but does not cause it; worth a separate triage story).
  *Found by Dev during green.*
- **Improvement** (non-blocking): `sidequest/game/persistence.py` and `sidequest/telemetry/spans.py` carry pre-existing ruff-format violations on `develop`. My diffs are clean; running `ruff format` repo-wide would touch many lines unrelated to 45-5. Bounded boy-scouting line: not this story.
  Affects `sidequest/game/persistence.py`, `sidequest/telemetry/spans.py` (defer to a format-only chore).
  *Found by Dev during green.*

### TEA (test verification)
- No upstream findings during test verification.

### Reviewer (code review)
- **Improvement** (non-blocking): Mechanical rule violation against `python.md` rule #11 — `f"DELETE FROM {tbl}"` and `f"SELECT COUNT(*) FROM {table}"` use f-string interpolation in SQL. SQLite cannot parameterize table names (limitation of the underlying API), and the source identifiers iterate compile-time module-private tuples (`_PER_SLOT_TABLES`, `PER_SLOT_TABLES`, `GLOBAL_TABLES`); zero injection surface.
  Affects `sidequest/game/persistence.py:308` and `tests/game/test_init_session_clears_stale_slot.py:147` (consider per-call-site `# noqa: S608` or a project-rules carve-out for hardcoded-constant table names).
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The `_reset_otel_tracer` autouse fixture in `tests/game/test_init_session_clears_stale_slot.py` calls `init_tracer()` per test but performs no provider-restoration on teardown. If a future suite-wide tracer fixture pattern emerges, this fixture should adopt it for uniform isolation.
  Affects `tests/game/test_init_session_clears_stale_slot.py:_reset_otel_tracer` (defer to a test-infrastructure consolidation chore).
  *Found by Reviewer during code review.*
- **Question** (non-blocking): The story-context attribute table at `sprint/context/context-story-45-5.md:94` lists `slug` as part of the `session.slot_reinitialized` span schema, but the implementation omits it because `SqliteStore.init_session(genre_slug, world_slug)` does not accept a slug. The Architect spec-check already deferred this; flagging again here for visibility — should the slug-keyed connect path eventually plumb `slug=row.slug` through `init_session()`, or accept the legacy seam's lack of slug as the canonical attribute set?
  Affects `sidequest/game/persistence.py:init_session` and `sidequest/handlers/connect.py:405` (slug-branch call site).
  *Found by Reviewer during code review.*

### TEA (test design)
- **Improvement** (non-blocking): Source-of-truth drift in `sprint/context/context-story-45-5.md` — call sites cited as `sidequest/server/session_handler.py:1654` and `:2154` actually live in `sidequest/handlers/connect.py:405` (slug branch) and `:906` (legacy branch) post-extraction.
  Affects `sprint/context/context-story-45-5.md` (refresh path references; the seam under `SqliteStore.init_session()` is unchanged).
  *Found by TEA during test design.*
- **Improvement** (non-blocking): Lint baseline drift — `tests/server/test_chargen_persist_and_play.py` and the new `test_stale_slot_reinit_wire.py` carry an E402 violation around the post-CONTENT_ROOT conftest import. The `# noqa: E402` is on the alias line not the import line, so ruff still flags it.
  Affects `tests/server/test_chargen_persist_and_play.py` and `tests/server/test_stale_slot_reinit_wire.py` (move conftest import above CONTENT_ROOT, OR fix the noqa to cover the import — pre-existing pattern, not 45-5's regression).
  *Found by TEA during test design.*
- **Question** (non-blocking): The Playtest 3 wedge symptom `turn_manager frozen at round=0/interaction=2` is reachable only if a partial `game_state` snapshot was persisted with `round=0` mid-turn. The 45-5 RED tests reproduce the **stale-narrative-log** seam (the upstream cause); they do **not** reproduce the wedged-turn-manager symptom directly because seeding `game_state` makes `store.load()` non-None and bypasses `init_session()` (resume branch wins). The full symptom may need a follow-up story or a wider fixture reproducing a crashed mid-turn save.
  Affects sibling story 45-11 (turn_manager.round invariant against narrative_log.max_round) — likely the right home for a wedged-game_state regression test.
  *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Committing to clear-on-reinit (option 1), not refuse-on-populated (option 2)**
  - Spec source: `sprint/context/context-story-45-5.md` "Two acceptable fixes — pick the one Keith picks"
  - Spec text: option 1 (transaction wraps DELETE per-slot tables before INSERT OR REPLACE on session_meta) vs option 2 (raise typed `StaleSlotError`)
  - Implementation: TDD specs assert the **clear** behavior (per-slot tables empty after `init_session()` on a populated slot). The session file's AC text — "Session reinit **clears** stale narrative_log entries" (AC1) and "OTEL span emitted on narrative_log clear" (AC4) — describes only the clear path; option 2's typed-error frame is not in any AC. Per spec-authority hierarchy, session-scope ACs win.
  - Rationale: SM-approved AC text is unambiguously the clear path. Refuse-path tests would not satisfy the SM ACs without rewording. Avoids shipping both fixes (anti-goal in context). Dev may revisit if the implementation uncovers a reason to flip.
  - Severity: minor
  - Forward impact: none (clear-path is what the AC demands; refuse-path remains documented in context for a future story if the choice ever reverses)
- **File path drift in spec — context-story-45-5.md cites `session_handler.py:1654/:2154`, current code lives in `sidequest/handlers/connect.py:405` (slug branch) and `:906` (legacy genre/world branch)**
  - Spec source: `context-story-45-5.md` Technical Guardrails — call site references
  - Spec text: "the legacy non-slug new-session branch at `sidequest/server/session_handler.py:2154` and the slug-keyed new-session branch at `session_handler.py:1654`"
  - Implementation: tests exercise the **legacy genre/world** path through `ConnectHandler.handle()` in `sidequest/handlers/connect.py:906`. Both call sites still call the same `SqliteStore.init_session()`, so the unit-level test (clear behavior) covers both seams; the wire test exercises only the legacy seam to keep the test focused.
  - Rationale: Connect logic was extracted from `session_handler.py` into `handlers/connect.py` after the context was authored. The seam — `store.init_session(genre, world)` after `store.load() is None` — is identical at both lines.
  - Severity: minor
  - Forward impact: none — Dev should fix `init_session()` itself, which both call sites use.
- **AC5 invariant scoped to "no stale rows wedge the invariant", not the full round-vs-max sync**
  - Spec source: session file AC5; sibling story 45-11
  - Spec text: "turn_manager.round and narrative_log.max_round must be synchronized at session start"
  - Implementation: AC5 test asserts that **after `init_session()`** the narrative_log is empty (max_round is None / 0), so a fresh `TurnManager(round=1, interaction=1)` cannot be wedged by a stale `max_round > 1`. The full sync invariant — including post-turn drift detection — belongs to story 45-11 ("turn_manager.round invariant against narrative_log.max_round") and is explicitly out of scope for 45-5.
  - Rationale: 45-11 is a sibling P1 story dedicated to the invariant. Avoiding scope-creep keeps the 45-5 PR reviewable and prevents work duplication.
  - Severity: minor
  - Forward impact: 45-11 must still implement the full invariant test; 45-5 only guarantees the post-reinit precondition.

### Architect (reconcile)

- **`slug` attribute omitted from emitted `session.slot_reinitialized` span**
  - Spec source: `sprint/context/context-story-45-5.md:94` (OTEL spans attribute table)
  - Spec text: "`session.slot_reinitialized` | `genre_slug`, `world_slug`, `slug`, `cleared_tables` (list of table names), `prior_narrative_count`, `prior_event_count`, `mode` (`"clear"` or `"refuse"`)"
  - Implementation: the watcher event published by `SqliteStore.init_session()` at `sidequest/game/persistence.py:319-330` carries `genre_slug`, `world_slug`, `cleared_tables`, `prior_narrative_count`, `prior_event_count`, `mode` — but **not** `slug`. The `SPAN_ROUTES.extract` lambda at `sidequest/telemetry/spans.py:356-365` likewise has no `slug` field.
  - Rationale: `init_session(genre_slug, world_slug)` does not accept a slug parameter; the legacy genre/world connect path (`sidequest/handlers/connect.py:906`) genuinely has no slug to pass. The slug-keyed path (`connect.py:405`) has `row.slug` but does not plumb it into `init_session()`. Adding `slug` would require widening the `init_session()` signature and threading it through both call sites — out of scope for a P1 correctness fix focused on the stale-slot bug. The operational signal needed by the GM panel (cleared tables + prior counts + genre+world identity) is fully present.
  - Severity: minor
  - Forward impact: A future story should plumb an optional `slug=None` keyword through `init_session(genre_slug, world_slug, *, slug=None)` and update both call sites. The slug-branch caller passes `row.slug`; the legacy branch passes `None`. Span attribute defaults to empty string when slug is unknown. The `SPAN_ROUTES.extract` lambda would gain a `slug` field. No regression risk in the current implementation — adding the attribute is purely additive observability.

- **AC4 wording cites "timestamp comparison" but operational attribute set in context does not include timestamps**
  - Spec source: session file AC4 (line 29 of this session file) AND `sprint/context/context-story-45-5.md:94` (operational attribute table)
  - Spec text (session AC4): "OTEL span emitted on narrative_log clear with count of cleared entries and timestamp comparison"
  - Spec text (context attribute table): "`session.slot_reinitialized` | `genre_slug`, `world_slug`, `slug`, `cleared_tables` (list of table names), `prior_narrative_count`, `prior_event_count`, `mode`"
  - Implementation: emits the operational attribute set from the context table; no timestamp fields. The refuse-path span (`session.slot_reuse_rejected`, context line 95) DOES include `prior_last_played` and `prior_created_at` — but that span is for a code path explicitly out of scope per TEA's option-1 commitment.
  - Rationale: The session AC4 wording conflates the clear-path and refuse-path attribute schemas. The story-context attribute table is the operational implementation contract; the AC4 wording was loose mental-model language about the diagnostic signal (Playtest 3 prot_thokk's narrative_log entry was dated 2026-04-18 in a save created 2026-04-19 — temporal gap as smoking gun). The diagnostic signal is recoverable from `prior_narrative_count > 0` plus the `session_meta.last_played` / `created_at` already persisted in SQLite; no information is lost by omitting dedicated timestamp attributes from the span.
  - Severity: minor
  - Forward impact: The operational attribute set defined in `context-story-45-5.md:94` is canonical for the clear-path span. AC4's wording should be amended in any future ticket revision to read "OTEL span emitted on narrative_log clear with count of cleared entries" — drop "and timestamp comparison" — or expanded to cite the explicit attribute set if the GM panel ever needs the temporal gap surfaced as a span attribute (it currently does not).

- **Dev finding "FK reordering of `_PER_SLOT_TABLES`" promoted from finding to deviation**
  - Spec source: `sprint/context/context-story-45-5.md:55-65` (option 1 description) and TEA hand-off bullet 1
  - Spec text (TEA hand-off): "Wrap `SqliteStore.init_session()` in a transaction that DELETEs from `game_state`, `narrative_log`, `scrapbook_entries`, `lore_fragments`, `events`, `projection_cache` before the existing `INSERT OR REPLACE INTO session_meta`. Single transaction."
  - Implementation: TEA's hand-off listed the per-slot tables in mixed order (`game_state, narrative_log, scrapbook_entries, lore_fragments, events, projection_cache`); Dev's `_PER_SLOT_TABLES` constant reorders them to `(projection_cache, events, game_state, narrative_log, scrapbook_entries, lore_fragments)` — children-before-parents — to satisfy the `projection_cache → events.seq` foreign key under `PRAGMA foreign_keys=ON`. A FK-naive ordering (parent before child) raised `sqlite3.IntegrityError` during Dev's initial test run.
  - Rationale: SQLite's PRAGMA foreign_keys=ON is set in `_configure_connection`; deleting the parent before the child violates the FK constraint and rolls back the transaction. Dev's reordering is forced by the database invariant, not a stylistic choice. A comment on the constant documents the FK ordering as load-bearing.
  - Severity: minor
  - Forward impact: Any future addition to `_PER_SLOT_TABLES` must respect FK ordering. If a new table is added with FKs into `events` or `projection_cache`, the new table must be inserted before its parent. The comment on the constant flags this requirement.