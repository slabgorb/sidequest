---
story_id: "45-45"
jira_key: null
epic: "45"
workflow: "tdd"
---
# Story 45-45: Wave 1 — snapshot split-brain dedup & rename (S1+S4+S5)

## Story Details
- **ID:** 45-45
- **Jira Key:** (not applicable — local sprint work)
- **Workflow:** tdd (phased)
- **Stack Parent:** none
- **Repos:** sidequest-server (single repo)

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-05-04T15:50:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04T15:50:00Z | - | - |

## Story Context

**Epic:** 45 — Playtest 3 Closeout (MP Correctness, State Hygiene, Post-Port Cleanup)

**Source Spec:** `docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md` (commit b910399)

**Implementation Plan:** `docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-1.md` (commit f599c58)

The plan is already TDD-shaped with 8 concrete tasks (Task 1, 1.5 architect amendment, 2, 3, 4, 5, 6, 7). Each task contains RED/GREEN/REFACTOR/COMMIT structure and explicit test bodies. TEA will consume this plan directly in the red phase.

## Acceptance Criteria

All acceptance criteria are defined in `sprint/epic-45.yaml` (story 45-43, id range). Verified at commit f599c58:

1. S1: `snapshot.world_confrontations` field removed; chassis loader writes intimate confrontations to `magic_state.confrontations`; `room_movement.process_room_entry` reads from there.
2. S4: `game/session.py` defines `NpcEncounterLogTag` (renamed from `EncounterTag`); `game/__init__.py` re-exports both names for one release window; `game/encounter_tag.py:EncounterTag` unchanged.
3. S5: `MagicState.pending_status_promotions`, `GameSnapshot.pending_magic_auto_fires`, `GameSnapshot.pending_magic_confrontation_outcome` are `Field(exclude=True)`; `model_dump_json()` never contains them.
4. Migration: `SqliteStore.load` calls `migrate_legacy_snapshot(data)` before `GameSnapshot.model_validate`; legacy fixture round-trips successfully.
5. Safety net: `SqliteStore.save` copies `.db` → `.db.canonicalize.bak` once on first canonical write per save (idempotent, never reaped).
6. OTEL: `snapshot.canonicalize` span fires once per migrated load with per-field attributes.
7. Wiring tests: end-to-end integration tests for each subsystem (load legacy → exercise → confirm canonical).
8. `just check-all` passes.

## Task Breakdown (from plan)

The plan defines 8 implementation tasks, all with concrete test bodies pre-written:

- **Task 1:** Migration scaffolding (no-op pass-through, OTEL wired) — 7 subtasks including fixture capture
- **Task 1.5:** Sibling-file safety net (.db.canonicalize.bak) — architect amendment
- **Task 2:** S1 — collapse `world_confrontations` into `magic_state.confrontations`
- **Task 3:** S4 — rename `EncounterTag` → `NpcEncounterLogTag`
- **Task 4:** S5 — exclude transient magic queues from snapshots
- **Task 5:** Wiring test for S1 (chassis → room_movement end-to-end)
- **Task 6:** Wiring test for S4 (log persistence round-trip)
- **Task 7:** Wiring test for S5 (queue exclusion from save/load)

## Handoff: TEA (Red Phase)

**Routing:** TEA (Fezzik) will write the RED tests directly from the plan's concrete test bodies at `docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-1.md`.

**Key Reference Points:**

- Plan specifies exact test structure (fixtures, assertions, parametrization) — TEA should transcribe from the markdown plan into `.py` files.
- Task 1.3 requires capturing a legacy save fixture BEFORE any source changes. The plan documents the exact `sqlite3` + `python -m json.tool` command.
- Fixtures go in `tests/fixtures/legacy_snapshots/` (new directory).
- OTEL constant `SPAN_SNAPSHOT_CANONICALIZE` added to `telemetry/spans/__init__.py` before the test runs.
- All 8 tasks have RED-only scope (no implementation, just failing tests that document the contract).

**Test Files Created by TEA (all in sidequest-server):**

- `tests/game/test_migrations.py` — unit tests per migration sub-function + fixture round-trip
- `tests/game/test_canonicalize_backup.py` — safety net (.bak file) tests
- `tests/fixtures/legacy_snapshots/pre_cleanup.json` — legacy save snapshot fixture (captured before code changes)

**Dev (Green Phase) Will Implement:**

- `sidequest/game/migrations.py` — the actual migration logic
- Modifications to `persistence.py`, `session.py`, `__init__.py`, `chassis.py`, `room_movement.py`, `magic/state.py`
- All per-AC fixes per the plan document

**No Scope for TEA Red Phase:**

- Do NOT implement the migrations.
- Do NOT modify source code (except adding the OTEL constant).
- Do NOT run `just check-all` yet (it will fail until Dev lands green).

**Exit Protocol:**

When RED tests are written and pushed (branch `feat/45-43-snapshot-split-brain-wave-1`), TEA records the test-run output and transitions to Dev via standard exit protocol.

---

## TEA Assessment

**Tests Required:** Yes
**Reason:** Wave 1 split-brain cleanup is a multi-step refactor of pydantic models, persistence, and game-state plumbing. Each step has observable behavior changes that need pinning before Dev edits production code.

**Test Files:**
- `sidequest-server/tests/fixtures/legacy_snapshots/pre_cleanup.json` — legacy fixture captured from `~/.sidequest/saves/games/2026-05-03-coyote_star-mp/save.db` (1687 lines of canonical-form JSON; carries `world_confrontations` (6 entries), `pending_magic_auto_fires`, and `magic_state.pending_status_promotions` — all three legacy split-brain shapes are present).
- `sidequest-server/tests/game/test_migrations.py` — 7 assertions across 7 tests (migration scaffold + S1 sub-function tests + integration round-trip).
- `sidequest-server/tests/game/test_canonicalize_backup.py` — 3 tests (canonical-no-backup, legacy-load-creates-backup, idempotency).
- `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py` — 4 tests (new name + NarrativeEntry annotation + alias + scene-momentum sentinel).
- `sidequest-server/tests/game/test_transient_queue_exclusion.py` — 4 tests (3 fields excluded from dump + reload re-init empty).
- `sidequest-server/tests/game/test_chassis_init.py` — 2 new tests appended (writer targets magic_state + raises when magic_state absent).
- `sidequest-server/tests/game/test_room_movement_chassis_filter.py` — 2 tests (intimate-only filter + non-intimate exclusion).
- `sidequest-server/tests/game/test_world_confrontations_field_removed.py` — 2 tests (attribute absent + legacy save still loads).

**Tests Written:** 24 tests across 7 files (incl. 2 appended to existing chassis test file). 1 fixture captured.

**Status:** RED — all per-AC tests fail for the right reasons.

| Test file | Run output | RED reason |
|-----------|-----------|-----------|
| test_migrations.py | collection error (ModuleNotFoundError: sidequest.game.migrations) | migrations module not yet created |
| test_canonicalize_backup.py | 2 passed, 1 skipped | scaffold-no-op state per plan; meaningful after Task 3 lands |
| test_npc_encounter_log_tag_rename.py | 3 failed, 1 passed | NpcEncounterLogTag not yet defined; sentinel passes |
| test_transient_queue_exclusion.py | 4 failed | three fields not yet `exclude=True` |
| test_chassis_init.py (new tests) | 2 failed | chassis writer still targets `world_confrontations`; no RuntimeError raised |
| test_room_movement_chassis_filter.py | 2 failed | reader still hits `snap.world_confrontations` |
| test_world_confrontations_field_removed.py | 2 failed | field still present; second test blocked on missing migrations module |

**Aggregate (run together): 13 failed, 7 passed, 1 skipped + 1 collection error.** Exactly matches the plan's red-phase expectations.

**Handoff:** To Dev for green-phase implementation per the 8-task plan walkthrough. The first failing test Dev should make pass is the import in `tests/game/test_migrations.py` — creating `sidequest/game/migrations.py` with `migrate_legacy_snapshot` (per Task 1 Step 1.6 + 1.2 OTEL constant) unblocks collection of `test_migrations.py` and `test_world_confrontations_field_removed.py::test_legacy_save_with_world_confrontations_loads_clean`.

---

## Delivery Findings

No upstream findings — plan is concrete and self-consistent. One mechanical drift logged in Design Deviations (WorldMagicConfig schema). Plan's test snippets used a stripped-down constructor; current model requires more fields. Test files use a small local helper to mint a minimum-valid config — no plan re-spec needed.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): The integration `make_minimal_coyote_star_magic_state` helper now lives in `tests/integration/conftest.py`. It's a candidate to promote into `tests/magic/conftest.py` (or a new `tests/_helpers/world_magic.py`) so unit tests under `tests/game/` and `tests/server/` don't duplicate the WorldMagicConfig builder. Out of scope for Wave 1 — flag for an opportunistic refactor sweep. Affects `tests/game/test_chassis_init.py:_make_coyote_star_magic_config`, `tests/game/test_room_movement_chassis_filter.py:_make_world_magic_config`, `tests/game/test_transient_queue_exclusion.py:_make_minimal_world_magic_config`. *Found by Dev during implementation.*
- **Gap** (non-blocking): The current `find_eligible_room_autofire` API filters by `register == "intimate"` internally. After Task 6, we ALSO filter on the call site. The internal filter is now dead-code defense — should be either removed (single source of truth) or kept with an assertion that the input is pre-filtered. Affects `sidequest/magic/confrontations.py:find_eligible_room_autofire`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Conflict** (blocking): The `SPAN_SNAPSHOT_CANONICALIZE` `extract` lambda at `sidequest/telemetry/spans/persistence.py:48-53` reports `s4_encounter_tag_renamed` and `s5_pending_queues_dropped` to the GM panel, but no migration sub-function emits these attributes. `_migrate_s1_world_confrontations` is the only registered sub-function (`migrations.py:85`); S4 is a Python class rename (no per-save migration), and S5 uses `Field(exclude=True)` so transient queues are simply absent — there is no field-counting migration. The `extract` lambda's `.get(..., 0)` / `.get(..., False)` defaults will ALWAYS be reported on every legacy load, telling Sebastien the GM panel "0 pending queues dropped" and "S4 not migrated" as if those migrations ran and reported zero. That contradicts the design's stated lie-detector contract: *"`snapshot.canonicalize` span fires once per migrated save with per-field migration attributes"* (spec §OTEL). Affects `sidequest/telemetry/spans/persistence.py:36-55` — either drop the bogus s4/s5 keys from the extractor (recommended; they're not migrations) or add explicit no-op sub-functions in `migrations.py` that emit `s4_encounter_tag_renamed: false` / `s5_pending_queues_dropped: 0` so the attribute origin is honest. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `tests/game/test_canonicalize_backup.py::test_backup_is_idempotent` does not actually test idempotency. It (a) seeds an empty file, (b) saves a CANONICAL snapshot, (c) writes SENTINEL to the .bak path, then (d) loads. Because the saved snapshot has no legacy fields, `migrate_legacy_snapshot` returns identical dict → `migrated == raw` is True → the .bak code path at `persistence.py:412` doesn't even execute. The SENTINEL survival isn't proving the `if not bak_path.exists():` guard works; it's proving the entire backup block is skipped when there's nothing to migrate (already covered by `test_canonical_load_does_not_create_backup`). The actual idempotency claim — *"a second legacy load on a save that already has a .bak does not overwrite it"* — is uncovered. To genuinely test it, seed a legacy snapshot via `_write_raw_save`, write SENTINEL to `.bak`, load, then assert SENTINEL survives. Affects `tests/game/test_canonicalize_backup.py:93-108`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The transitional `EncounterTag = NpcEncounterLogTag` alias at `sidequest/game/__init__.py:188` has no deprecation timer or warning. Spec §S4 says *"export both names for one release window, then drops it"* — but there's no scheduled removal date, no `DeprecationWarning`, and no follow-up story documented. The deprecation will be silently inherited by Wave 2A and may stay forever. Suggest one of: (a) wrap the alias in a `__getattr__` module hook that emits `DeprecationWarning`, (b) file a follow-up story to remove the alias, or (c) add a sprint comment with a target removal date. Affects `sidequest/game/__init__.py:185-189`. *Found by Reviewer during code review.*

## Reviewer Assessment

**Verdict:** APPROVED WITH OBSERVATIONS (no Critical/High; 1 Medium blocking-flagged finding)

After full preflight + adversarial walkthrough, the implementation cleanly resolves S1+S4+S5 of the snapshot split-brain spec. Test suite is GREEN (3955 passed, 57 skipped); ruff clean. No production consumer of `snapshot.world_confrontations` was missed. The bind-path swap in `websocket_session_handler.py:1374` is necessary (without it, `init_chassis_registry` would raise the new `RuntimeError` because `magic_state` is None when chassis init runs).

**Severity table:**

| Severity | Finding | Location | Required action |
|----------|---------|----------|-----------------|
| [MEDIUM] | OTEL `extract` lambda reports S4/S5 fields no migration emits — lie-detector lies by saying `"s4_encounter_tag_renamed: false"` on every load when no S4 migration is registered. | `sidequest/telemetry/spans/persistence.py:36-55` | Drop the s4/s5 keys from the extractor (preferred), OR add no-op sub-functions in `migrations.py` so the attribute origin is honest. |
| [LOW] | `test_backup_is_idempotent` is a tautology — doesn't exercise the `if not bak_path.exists():` guard; covers the canonical-load case redundantly. | `tests/game/test_canonicalize_backup.py:93-108` | Reseed with a legacy fixture so the migration path runs with a pre-existing .bak. |
| [LOW] | Deprecation alias has no removal timer / warning. | `sidequest/game/__init__.py:185-189` | Add `DeprecationWarning` via module `__getattr__`, or file a follow-up. |

**Adversarial-attention checklist (per Reviewer prompt):**

1. **`.bak` correctness.** WAL checkpoint claim is verified: `PRAGMA journal_mode=WAL` is set in `_configure_connection` (`persistence.py:237`), so without `PRAGMA wal_checkpoint(TRUNCATE)` the on-disk `.db` would lag the WAL. The checkpoint is run on `self._conn` immediately before `shutil.copy2`. There is no race window in production: `store.load()` is called from `connect.py:303` once at session bind, BEFORE any other writer is bound to the slug — there is no concurrent connection open against the file. `try/except (OSError, sqlite3.Error)` is a defensible failure mode (warn-and-continue: backup is defense-in-depth, not a primary gate). VERIFIED CORRECT.
2. **OTEL span attributes / counts.** `s1_world_confrontations_merged` is correctly an integer (line counter at `migrations.py:65`). `s1_world_confrontations_dropped_no_target` correctly counts the legacy entries when `magic_state` is absent. The empty-list path emits `merged: 0, dropped: 0` (per `migrations.py:40-43`); span fires whenever the legacy key is even present, which is the correct semantics for "this save was canonicalized." S4/S5 attributes — see Medium finding above.
3. **EncounterTag alias.** `EncounterTag = NpcEncounterLogTag` at `__init__.py:188` resolves correctly; test confirms `DeprecatedAlias is NpcEncounterLogTag`. The OTHER `EncounterTag` (`game/encounter_tag.py:EncounterTag`) is unaffected — only one external import path resolves to the alias (the old `from sidequest.game import EncounterTag`), and no production code uses it. VERIFIED.
4. **Missed `world_confrontations` consumer (spec risk #3).** `grep -rn world_confrontations sidequest/` returns only comment references (in `session.py`, `chassis.py`, `websocket_session_handler.py`, `migrations.py`) and the migration code itself. No live read/write outside the migration path. VERIFIED — no sixth call site.
5. **Wiring discipline.** Migration is called from `SqliteStore.load()` (`persistence.py:398`), which is itself called from production paths `connect.py:303` (websocket bind) and `rest.py:309` (debug-state endpoint) and `rest.py:300` (slug-resume). Chassis writer flip is observable because `init_chassis_registry` raises if `magic_state` is None — the bind path swap at `websocket_session_handler.py:1374` is the real fix that makes the production path satisfy the new invariant.
6. **`test_canonicalize_backup` legacy fixture extension.** Adding `"world_confrontations": []` to the legacy dict makes the migration trigger (because the key presence alone satisfies `_migrate_s1_world_confrontations`'s gate at line 34, and popping empty list still mutates `out`). `migrated != raw` is True even when the list is empty. The test still semantically validates "a load that rewrites any field copies the .db to a sibling .bak" — VERIFIED CORRECT.
7. **Bootstrap-update scope (boy-scouting bound).** Six bootstrap test updates are mechanically necessary because `init_chassis_registry` now raises when `magic_state` is None and `worlds/<world>/confrontations.yaml` exists (a new invariant). They are not refactors — they are test-side parity updates for the new bind-path ordering. The integration `conftest.py` helper consolidates the WorldMagicConfig builder for those tests; the three `tests/game/` tests retain local helpers (Dev's own non-blocking improvement note). Scope is appropriate.

**Data flow traced:** A legacy save loaded from `~/.sidequest/saves/games/<slug>/save.db` → `connect.py:303` `store.load()` → `persistence.py:390` deserialize JSON → `persistence.py:398` `migrate_legacy_snapshot(raw)` → S1 sub-function pops `world_confrontations`, merges into `magic_state.confrontations` dict → `migrated != raw` → WAL checkpoint + `shutil.copy2` to `.canonicalize.bak` (idempotent via `if not bak_path.exists()`) → `GameSnapshot.model_validate(migrated)` → snapshot is canonical → first save writes back without legacy field. Span `snapshot.canonicalize` fires with `s1_world_confrontations_merged` count. Safe.

**Pattern observed:** "Deprecation alias for one release window" at `__init__.py:188` follows the spec's stated migration policy but lacks the timer to enforce removal — this is the only structural gap in an otherwise tight implementation.

**Error handling:** Migration failures don't have a graceful path — if `_migrate_s1_world_confrontations` raised on a malformed entry, the load would fail before `model_validate` ran. Acceptable: the migration's only mutating step (dedupe append) skips non-dict entries silently (`migrations.py:60`), and the broader `try` around `model_validate` raises `SaveSchemaIncompatibleError` which the connect handler catches. Backup creation has explicit `try/except (OSError, sqlite3.Error)` — backup failure does NOT block load. CORRECT.

**Security analysis:** N/A — local-file persistence, no external input changes. Migration accepts only data that was previously a valid snapshot from this server, not untrusted JSON.

**Test verification:** 3955 passed, 57 skipped, 84.77s; ruff check clean. The 28 tests directly added/touched by this story all pass; no regressions in adjacent test files.

**Handoff:** To SM for finish-story. The MEDIUM finding (OTEL extract lambda) should be addressed before the GM panel is consulted for Wave 2 work — Sebastien needs a clean signal — but it does not block merge of Wave 1 since the s4/s5 zero/false defaults will not corrupt state. Recommend filing a fast-follow ticket if not addressed pre-merge.

## Pull Request Description (for SM finish-time use)

**Title:** Wave 1 — snapshot split-brain dedup & rename (S1 + S4 + S5)

**Branch:** `feat/45-43-snapshot-split-brain-wave-1` → `develop`

**Body:**

```markdown
## Summary

Wave 1 of the snapshot split-brain cleanup (spec 2026-05-04) — collapses three
duplicated/misnamed snapshot fields into a single canonical store each, with
read-old-write-new migration so existing saves promote silently on first load.

- **S1**: `snapshot.world_confrontations` → `magic_state.confrontations`. Field removed; chassis loader writes into `magic_state` directly; `room_movement` reads/filters `magic_state.confrontations`. Saves migrated on load by `migrate_legacy_snapshot`.
- **S4**: `game/session.py:EncounterTag` → `NpcEncounterLogTag` (the docstring already called it that). One-release deprecation alias retained at `sidequest.game.EncounterTag`. The OTHER `EncounterTag` (`game/encounter_tag.py`, scene-momentum) is unchanged.
- **S5**: `MagicState.pending_status_promotions`, `GameSnapshot.pending_magic_auto_fires`, `GameSnapshot.pending_magic_confrontation_outcome` are now `Field(exclude=True)`. Transient handler-local queues never reach the persisted JSON; reload re-initializes them empty (correct because they're recomputed from snapshot state on the next narration turn).

Architect amendment 2026-05-04: sibling-file safety net. On any migrated load,
`SqliteStore.load` runs `PRAGMA wal_checkpoint(TRUNCATE)` and copies `<save>.db`
to `<save>.db.canonicalize.bak` once. The `.bak` is durable (never reaped, per
Keith's playstyle).

OTEL: new `snapshot.canonicalize` span (`SPAN_SNAPSHOT_CANONICALIZE`) routed to
the GM panel via `SpanRoute(component="persistence", event_type="state_transition")`.

## Scope

- Wave 2A (S2: NPC pool / state split) is deferred — separate sequenced story.
- Pool-promotion semantics (one-shot vs re-cite-able) is Wave 2A's call.
- S6 (Combatant body duplication) is documented as a tripwire only — no story.

## Test plan

- [x] `just server-check` clean (3955 passed, 57 skipped, ruff clean)
- [x] Migration round-trips a legacy fixture (`tests/fixtures/legacy_snapshots/pre_cleanup.json`, captured pre-cleanup from `~/.sidequest/saves/games/2026-05-03-coyote_star-mp/save.db`)
- [x] `.canonicalize.bak` is created once on first migrated load and is durable
- [x] `pending_magic_*` and `pending_status_promotions` never appear in `model_dump_json`
- [x] `snapshot.canonicalize` span fires with `s1_world_confrontations_merged: int` per migrated load
- [x] Wiring tests cover chassis-loader → magic_state → room_movement end-to-end (galley → tea_brew auto-fire)
- [ ] Manual smoke: load a real pre-cleanup save from `~/.sidequest/saves/`, confirm `.canonicalize.bak` appears, confirm session boots cleanly

## Risks

1. **Migration bug corrupts save** — mitigated by `.canonicalize.bak` safety net (durable, never reaped).
2. **Hidden `world_confrontations` consumer** — `grep -rn` confirms no live consumer outside the migration path itself. Risk closed.
3. **Deprecation alias drift** — `EncounterTag = NpcEncounterLogTag` has no removal timer. Reviewer flagged as non-blocking; suggest a fast-follow chore.

## Reviewer notes (open observations)

1. **MEDIUM**: `SPAN_SNAPSHOT_CANONICALIZE` `extract` lambda reports `s4_encounter_tag_renamed` and `s5_pending_queues_dropped`, but no sub-function emits them. The GM panel will see hardcoded `false` / `0` on every load — fast-follow to either drop the keys or honestly report no-op sub-functions.
2. **LOW**: `test_backup_is_idempotent` doesn't actually test idempotency (canonical save = no migration = no backup code path runs).
3. **LOW**: Deprecation alias has no timer/warning — file follow-up to remove after the next release.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/migrations.py` (new) — `migrate_legacy_snapshot` + `_migrate_s1_world_confrontations`
- `sidequest/game/persistence.py` — wire migration into `SqliteStore.load`; .bak safety net w/ WAL checkpoint
- `sidequest/game/session.py` — rename `EncounterTag` → `NpcEncounterLogTag`; mark transient queues `exclude=True`; drop `world_confrontations` field
- `sidequest/game/__init__.py` — export `NpcEncounterLogTag`; deprecation alias for `EncounterTag`
- `sidequest/game/chassis.py` — chassis loader writes into `magic_state.confrontations`; raises if magic_state is None
- `sidequest/game/room_movement.py` — reader filters `magic_state.confrontations` by `register=="intimate"`; hoisted imports
- `sidequest/magic/state.py` — `pending_status_promotions` excluded from dump
- `sidequest/server/websocket_session_handler.py` — bind-path order swap (magic-init before chassis-init)
- `sidequest/telemetry/spans/persistence.py` — `SPAN_SNAPSHOT_CANONICALIZE` constant + route
- `tests/integration/conftest.py` — `make_minimal_coyote_star_magic_state` helper
- `tests/integration/{test_galley_autofires_tea_brew, test_kestrel_chassis_registry, test_kestrel_tea_brew_outputs, test_narration_apply_room_entry_wiring}.py` — magic_state-first bootstrap
- `tests/game/test_canonicalize_backup.py` — legacy fixture now includes `world_confrontations` to trigger migration
- `tests/game/test_chassis_init.py` — kestrel tests initialize magic_state first
- `tests/game/test_transient_queue_exclusion.py` — minimum-valid WorldMagicConfig builder

**Tests:** 3955 passed, 57 skipped (GREEN — full server suite + lint clean)
**Branch:** feat/45-43-snapshot-split-brain-wave-1 (pushed)

**Acceptance Criteria Status:**
1. S1 (collapse `world_confrontations` → `magic_state.confrontations`): PASS — field removed, writer/reader switched, migration round-trips legacy fixture cleanly (6 confrontations preserved end-to-end).
2. S4 (rename `EncounterTag` → `NpcEncounterLogTag`): PASS — alias retained at `sidequest.game.__init__.EncounterTag` for one release.
3. S5 (`Field(exclude=True)` on three transient fields): PASS — `model_dump_json` never contains the queues; reload re-initializes empty.
4. Migration on load: PASS — wired in `SqliteStore.load` before pydantic validate; fixture round-trips.
5. `.canonicalize.bak` safety net: PASS — idempotent, never reaped, WAL-checkpoint hardened.
6. OTEL `snapshot.canonicalize` span: PASS — routed via `SpanRoute` for GM-panel surfacing; per-field attrs (`s1_world_confrontations_merged`, `s1_world_confrontations_dropped_no_target`, `s4_encounter_tag_renamed`, `s5_pending_queues_dropped`).
7. Wiring tests: PASS — `test_sqlite_store_load_calls_migrate`, `test_galley_autofires_tea_brew`, `test_narration_apply_galley_location_fires_tea_brew` cover end-to-end.
8. `just server-check` passes.

**Handoff:** To Reviewer.

## Design Deviations

### TEA (test design)
- **WorldMagicConfig fixture builder:** Plan snippets in Tasks 5 and 6 use `WorldMagicConfig(world_slug="coyote_star", ledger_bars=[])`. The current model requires `genre_slug`, `allowed_sources`, `active_plugins`, `intensity`, `world_knowledge`, `visibility`, `hard_limits`, `cost_types`, `narrator_register` as well. Tests use a minimum-valid local helper (`_make_coyote_star_magic_config` in test_chassis_init.py; `_make_world_magic_config` in test_room_movement_chassis_filter.py) that mirrors `tests/magic/conftest.py`'s shape with empties where allowed. Reason: keep tests self-contained and plan-faithful in intent (a non-magical magic_state for the chassis-init invariant) while satisfying pydantic.
- **ConfrontationDefinition fixture in test_room_movement_chassis_filter.py:** Plan snippet uses `ConfrontationDefinition(id="the_bleeding_through", register=None, outcomes={...})`. Added the required `label`, `plugin_tie_ins`, `rounds`, `resource_pool`, `description` to match the current model. The plan explicitly anticipated this ("If `ConfrontationDefinition` requires additional fields beyond what's shown — read its model definition and add the minimum required fields").

### Dev (implementation)
- **WAL checkpoint before .bak copy:** Plan Step 1.5.3 specifies `shutil.copy2(<save>.db, <save>.db.canonicalize.bak)`. Naked copy was insufficient because `PRAGMA journal_mode=WAL` is on by default — the most recent rows live in `<save>.db-wal` until checkpoint. The `.bak` was being copied empty (no `game_state` table when reopened). Added `PRAGMA wal_checkpoint(TRUNCATE)` immediately before `shutil.copy2` so the .bak is a self-contained file and Keith's recovery story is single-file (matches the durable-retention principle — no WAL/SHM siblings to keep track of). Failure of the checkpoint is treated identically to OSError on copy: warn and continue (don't block load).
- **Hoisted imports in room_movement.py:** Plan Step 6.3 doesn't mention import hoisting, but TEA's spy-based test `monkeypatch.setattr(rm, "find_eligible_room_autofire", _spy_find)` only works if the symbol is a module attribute. The pre-existing local `from sidequest.magic.confrontations import find_eligible_room_autofire` inside `process_room_entry` made the spy a no-op. Hoisted both `find_eligible_room_autofire` and `apply_mandatory_outputs` to module top.
- **Bind-path swap in websocket_session_handler.py:** Plan Step 5.6 calls this out as conditional ("if not, swap them"). The current bind path was indeed chassis-then-magic; swapped to magic-then-chassis around line 1374 with an explanatory comment naming the S1 invariant. This is the production fix that makes the integration tests pass without contortions.
- **Test fixture extensions for S1 invariant:** Six tests outside the plan's scope had to be updated to initialize `magic_state` before `init_chassis_registry`: `test_chassis_init.py` (existing kestrel tests), `test_galley_autofires_tea_brew.py`, `test_kestrel_chassis_registry.py`, `test_kestrel_tea_brew_outputs.py`, `test_narration_apply_room_entry_wiring.py`, plus the integration conftest got a `make_minimal_coyote_star_magic_state()` helper. Plan Step 5.5 anticipated this ("If a test fails for that reason, update it to initialize magic_state first — the test is reproducing the legacy bug").
- **`test_canonicalize_backup::test_legacy_load_creates_backup_once` legacy fixture:** TEA's handoff predicted this would unblock naturally once Task 3 landed; that turned out to be incorrect because Task 3 (S5 exclude=True) is a serialization change, not a per-field migration. The actual unblock is Task 4 (S1 strips `world_confrontations`). Updated the test fixture to include `"world_confrontations": []` so the migration triggers — this matches the plan's intent (the SKIP becomes meaningful once a migration sub-function is registered).
- **OTEL routing for `snapshot.canonicalize`:** Plan said "add to `__init__.py` if `__all__` exists". The spans package uses per-domain submodules with `SPAN_ROUTES[...] = SpanRoute(...)` registration; the constant lives in `spans/persistence.py` and is auto-exported via the `from .persistence import *` line in `spans/__init__.py`. Routed it (component=`persistence`, event_type=`state_transition`) rather than flat-only — Sebastien-targeted GM-panel signal per the design.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Reviewer Findings Addressed

Reviewer verdict was APPROVED WITH OBSERVATIONS (1 MEDIUM, 2 LOW). All three
addressed in a single follow-up commit on top of `bb804d8`.

**Resolution commit:** `e253950` (`fix(45-43): address reviewer findings — OTEL honesty, real idempotency test, deprecation warning`)

**Test counts after fix:** 3957 passed (was 3955; +2 net new tests), 57 skipped, ruff clean.

### Finding 1 (MEDIUM) — OTEL extractor lying about S4/S5 — RESOLVED

**File:** `sidequest/telemetry/spans/persistence.py:36-55`
**Fix:** Replaced the inline `extract` lambda with a named function
`_extract_snapshot_canonicalize` that forwards ONLY keys an actual migration
sub-function set on the span. Dropped `s4_encounter_tag_renamed` and
`s5_pending_queues_dropped` from the extractor entirely — S4 is a Python
class rename and S5 uses `Field(exclude=True)`, neither is a per-save
migration. The GM panel now sees `{field: snapshot, op: canonicalize,
s1_world_confrontations_merged: <int>, s1_world_confrontations_dropped_no_target: <int>}`
on a real S1 migration, and just `{field: snapshot, op: canonicalize}` if
the span fires with empty attributes — never invented zero/false markers.
**Test:** `tests/game/test_migrations.py::test_canonicalize_extract_only_forwards_keys_from_active_migrations`
exercises three cases (S1 attrs present, empty attrs, attributes=None) and
asserts no `s4_*` / `s5_*` keys appear in any payload.

### Finding 2 (LOW) — tautological idempotency test — RESOLVED

**File:** `tests/game/test_canonicalize_backup.py:93-108`
**Fix:** Rewrote `test_backup_is_idempotent` to seed a LEGACY snapshot via
`_write_raw_save` (with `world_confrontations: []` — the same trigger
`test_legacy_load_creates_backup_once` uses), pre-write SENTINEL bytes to
the `.bak` BEFORE `store.load()` runs, then assert the SENTINEL survives
byte-for-byte. The migration path now actually executes during this test
(legacy field present → `migrated != raw` → `.bak` code path entered),
which is the only way to genuinely exercise the `if not bak_path.exists():`
guard.

### Finding 3 (LOW) — missing DeprecationWarning on EncounterTag — RESOLVED

**File:** `sidequest/game/__init__.py:185-189`
**Fix:** Replaced the bare `EncounterTag = NpcEncounterLogTag` alias with
a module-level `__getattr__` shim that emits
`DeprecationWarning("sidequest.game.EncounterTag was renamed to NpcEncounterLogTag in story 45-43 (Wave 1); the legacy name will be removed in Wave 2.")`
on every access, then returns `NpcEncounterLogTag`. Unknown attribute names
fall through to `AttributeError` — no silent fallback.
**Tests:** Added `test_old_name_alias_emits_deprecation_warning` in
`tests/game/test_npc_encounter_log_tag_rename.py` (asserts the warning
fires AND that unknown attrs still raise AttributeError); updated the
existing `test_old_name_alias_still_works` to wrap the import in
`pytest.warns(DeprecationWarning, ...)`.

**Note for SM (Wave 2 cleanup):** Reviewer recommended filing a follow-up
chore so the alias removal doesn't outlive its single-release window.
SM should run before finish-story:

```
pf sprint story add 45 "Wave 1 cleanup — drop EncounterTag deprecation alias" 1 --type chore --priority p3 --workflow trivial --repos server
```

Description should reference 45-43 and the spec's "one release window"
promise (`docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md`
§S4). Removal target: Wave 2 — drop the `__getattr__` shim and the
`__all__.append("EncounterTag")` line.
