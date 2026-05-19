# Story 52-3: Persistence: mask-BLOB column + loader (the materializer.py:57 gap); reload on resume

---
story_id: 52-3
jira_key: ""
epic: 52
workflow: tdd
---

## Story Details
- **ID:** 52-3
- **Epic:** 52 — Wire Procedural Megadungeon Output to the ADR-096 Cavern Renderer Pipeline
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Branch:** feat/52-3-mask-blob-persistence
- **Stack Parent:** none

## Specification

### Background

Story 52-2 (merged) emitted ADR-096 mask + derived block per region in the materializer's
design stage. The mask is computed; the `dungeon_map` table schema already has a `mask BLOB`
column (Plan 5 prepared it). This story **persists** that mask on write and **loads** it on resume.

**The gap:** `materializer.py:57` (the module docstring) documents the Plan 5 persistence
contract: `commit_expansion` persists only `RegionNode.to_dict()` (id/expansion_id/theme/depth_score).
There is NO mask BLOB write path on `commit_expansion`, and no Plan 1–6 code consumes a persisted
mask on reload. The mask is inert until **this story** adds the mask loader.

### Acceptance Criteria

1. **Mask write path (persist):**
   - `commit_expansion` accepts `mask: dict | None` parameter
   - If mask is provided, serialize to JSON and write to `dungeon_map.mask` BLOB column
   - If mask is None, leave the column NULL
   - OTEL: emit `dungeon.persist.mask_write` span with `mask_rows=N`

2. **Mask load path (resume):**
   - `load_map` deserializes `dungeon_map.mask` BLOB → dict (or None if NULL)
   - Return mask as part of `RegionNode` or a separate `RegionMaskMap` loader
   - Add to the `DungeonStore.load(...)` chain
   - OTEL: emit `dungeon.persist.mask_load` span with `mask_rows=N`

3. **Reload on resume:**
   - Play a round with procedural generation (beneath_sunden)
   - Stop and save
   - Reload the same save
   - Assert all region masks are present and byte-identical to the original
   - OTEL watcher output must show mask_write and mask_load spans

4. **No schema migrations:**
   - The `mask BLOB` column already exists in `dungeon_map` (Plan 5)
   - No new migrations; only populate the pre-existing column

5. **No silent fallbacks:**
   - If mask write fails (serialization, database error), raise loudly
   - If mask load finds a corrupted BLOB, raise loudly
   - Never silently skip a mask or default to an empty grid

### Design Notes

- **Mask format:** JSON serialization of the fill-stage grid (per 52-2: `FillReport.mask`)
- **Caller contract:** The materializer's commit stage calls `DungeonStore.commit_expansion(..., mask=...)`
  after the fill stage produces the mask
- **Symmetry:** mask write/load must be fully symmetric — a reloaded mask must be byte-identical
  to the original

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-19T13:00:18Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19T12:21:32Z | 2026-05-19T12:23:28Z | 1m 56s |
| red | 2026-05-19T12:23:28Z | 2026-05-19T12:34:26Z | 10m 58s |
| green | 2026-05-19T12:34:26Z | 2026-05-19T12:42:40Z | 8m 14s |
| spec-check | 2026-05-19T12:42:40Z | 2026-05-19T12:44:45Z | 2m 5s |
| verify | 2026-05-19T12:44:45Z | 2026-05-19T12:49:09Z | 4m 24s |
| review | 2026-05-19T12:49:09Z | 2026-05-19T12:58:22Z | 9m 13s |
| spec-reconcile | 2026-05-19T12:58:22Z | 2026-05-19T13:00:18Z | 1m 56s |
| finish | 2026-05-19T13:00:18Z | - | - |

## Delivery Findings

No upstream findings at setup phase.

### TEA (test design)

- **Gap** (non-blocking): Story context file `sprint/context/context-story-52-3.md` was never created — only `context-epic-52.md` exists. The story-context gate in `tea-entry` was not triggered (the validator name `pf validate context-story <id>` referenced in the SM agent definition does not match `pf validate`'s available validators). Tests proceeded against session + epic context, which were sufficient. Affects `sprint/context/` (a `context-story-52-3.md` would have been the canonical AC source for downstream phases). *Found by TEA during test design.*
- **Improvement** (non-blocking): The `pf validate` validators list does not include a `context-story` entry; the SM agent's `<on-activation>` instruction `pf validate context-story {story_id}` is dead code. Affects `pennyfarthing-dist/agents/sm.md` + the `pf validate` CLI (either add a `context-story` validator that takes a story id, or rewrite the SM instruction to use the existing `context` validator with story-scoping). *Found by TEA during test design.*

### Dev (implementation)

- No upstream findings during implementation.

### TEA (test verification)

- **Improvement** (non-blocking): JSON-to-BLOB serialisation pattern (`json.dumps(..., sort_keys=True).encode("utf-8")` / `json.loads(blob.decode("utf-8"))`) recurs in 3+ places across `DungeonStore`. Affects `sidequest-server/sidequest/dungeon/persistence.py` (extract `_serialize_to_blob` / `_deserialize_from_blob` helpers and use across `commit_expansion` region payload, mask BLOB, `put_frontier`, `record_mutation`). Cross-story refactor — defer to a Plan-5 cleanup chore. *Found by TEA during test verification.*
- **Gap** (non-blocking): `commit_expansion` region payload write at `sidequest-server/sidequest/dungeon/persistence.py:328` (`json.dumps(live.to_dict())`) lacks the same loud-failure try/except wrap that the new mask write has. A non-JSON-serialisable region payload would surface as a `sqlite3.Error` at the INSERT layer, not as a `PersistError` at the serialisation point. Pre-existing Plan 5 code — not in 52-3 scope, but the symmetry deserves a follow-up. *Found by TEA during test verification.*
- **Improvement** (non-blocking): Test helper duplication — `_mem_conn`, `_file_conn`, `_seed_graph`, `_generate_and_attach` are mirrored across `tests/dungeon/test_persistence.py` and `tests/dungeon/test_persistence_mask.py`. Consolidating into `tests/dungeon/conftest.py` reduces drift risk. Affects 2 test files; the mirror is intentional today per their own comments but the duplication-cost is real. *Found by TEA during test verification.*

### Reviewer (code review)

- **Improvement** (non-blocking): `load_masks` docstring at `sidequest-server/sidequest/dungeon/persistence.py:393` claims the `dungeon.persist.mask_load` span "always fires" but on the `SerializationError` path (lines 405-409) the exception unwinds before the span open on line 411 — the span does NOT fire on corruption. Behaviour is correct (loud raise = loud signal); docstring is misleading. Suggested fix: rewrite to "fires on successful load (mask_rows=0 on fresh save); raises SerializationError before firing if any BLOB is corrupted." *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Test module docstring at `sidequest-server/tests/dungeon/test_persistence_mask.py:3-7` uses present-tense to describe the persistence gap this story closes ("does NOT write the mask BLOB column", "no Plan 1–6 code consumes a persisted mask on reload"). Mirrors the same documentation rot that simplify-quality already fixed in `materializer.py:56-61`. Suggested fix: past-tense rewrite naming Story 52-3 as the closure. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `test_commit_expansion_raises_persisterror_on_unserialisable_mask` at `sidequest-server/tests/dungeon/test_persistence_mask.py:801` has a docstring promise "the expansion's rows do not exist after the raise" but no `SELECT` assertion verifies it. Test passes today because the JSON encode raises BEFORE the INSERT, but a regression of that ordering would slip through silently. Suggested fix: after `conn.rollback()`, add `assert not conn.execute("SELECT 1 FROM dungeon_map WHERE expansion_id = 1").fetchall()`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, inherited): `mask_write_span` at `sidequest-server/sidequest/dungeon/persistence.py:361-363` fires AFTER the INSERTs are staged but BEFORE the caller's `conn.commit()` (which happens in `_stage_commit` at `materializer.py:1816`). On rollback the span is a false-positive telemetry record. This inherits the existing `dungeon_persist_commit_span` semantics — not a regression introduced by 52-3, but the right architectural fix is a Plan-5-wide telemetry refactor: move both spans into `_stage_commit` after `conn.commit()` succeeds (mirror `frontier_expand_span`'s post-commit emission pattern at `materializer.py:1841-1849`). *Found by Reviewer during code review.*

## SM Assessment

**Setup complete.** Story 52-3 closes the Plan 5 persistence gap documented at `materializer.py:57` — the `dungeon_map.mask` BLOB column exists but has no write path on `commit_expansion` and no read path on `load_map`. Plan 7 materializer emits the mask; this story makes it durable across save/reload.

**Workflow:** TDD (3 pts). Single repo (sidequest-server), branched off `develop` per subrepo convention. No Jira (SideQuest project never uses Jira — by policy).

**Scope boundaries:**
- IN: mask BLOB write on `commit_expansion`, mask load on `load_map`, OTEL spans on both, round-trip reload assertion, loud failure on corruption.
- OUT: cavern PNG sidecar emission (52-4), UI wiring (52-5), client-side rendering.

**Risk surface:**
- ADR-106 + Plan 5/7 are load-bearing on this persistence — break it and the megadungeon goes inert on reload. Memory `project_beneath_sunden_plan5_seed_expansion0.md` notes the strict prod commit_expansion contract; mask write must compose cleanly with the existing `new_nodes` persistence without mutating the seed-vs-expansion semantics.
- Memory `feedback_save_preservation_wal.md` reminds: any save inspection in tests must respect the WAL trio (db+wal+shm) or assertions will lie.
- No silent fallbacks (CLAUDE.md `<critical>`) — if the mask BLOB is missing or malformed on load, fail loudly.

**Handoff to TEA (Hamlet, Prince of Denmark):** Write the RED suite for write + load + round-trip + OTEL emission + corruption-loud-failure. Verify failures before greenlighting Puck.

## Design Deviations

### TEA (test design)

- **AC1 signature: `mask: dict | None` interpreted as `masks: dict[region_id, dict] | None`**
  - Spec source: `.session/52-3-session.md` AC1 (Acceptance Criteria, line 33-37)
  - Spec text: "`commit_expansion` accepts `mask: dict | None` parameter. If mask is provided, serialize to JSON and write to `dungeon_map.mask` BLOB column"
  - Implementation: Tests assert `commit_expansion(..., masks: Mapping[region_id, dict] | None = None)` — a per-region map keyed by `region_id`, not a single dict.
  - Rationale: `commit_expansion` persists multiple regions per call (`expansion.new_nodes`); the `dungeon_map.mask` column is per-row (per region). A single `dict` parameter cannot address multiple regions without ambiguity (broadcast? first-region-only? expansion-wide?). The per-region map preserves the spec's intent (per-row JSON BLOB write) while making the addressing unambiguous. The OTEL span carries `mask_rows=N` to make the count observable.
  - Severity: minor
  - Forward impact: Dev's `_stage_commit` change must thread `fill_result` (already in scope; the per-region map is built from `RegionFill.mask` keyed by `node.id`). The materializer-side wiring becomes a one-line dict-comp at the seam.

- **AC2 loader shape: separate `load_masks() -> dict[str, dict]` chosen over RegionNode-attached mask**
  - Spec source: `.session/52-3-session.md` AC2 (Acceptance Criteria, line 41-43)
  - Spec text: "Return mask as part of `RegionNode` or a separate `RegionMaskMap` loader" (spec explicitly allows either)
  - Implementation: Tests assert `store.load_masks() -> dict[str, dict]` — a separate loader, mirroring `load_frontier` / `load_mutations` / `open_threads`.
  - Rationale: `RegionNode` is a value object owned by `region_graph.model` (Plan 5 substrate); attaching mutable per-region rendering payload (mask) to it would entangle generator state with renderer concerns. The separate loader pattern is already established in `DungeonStore` for every other auxiliary table. The spec explicitly allows this path.
  - Severity: minor
  - Forward impact: 52-4 (PNG sidecar) and 52-5 (UI wiring) consume `load_masks()` directly; they never need to touch `RegionNode`.

- **AC1 NULL semantics: regions absent from the `masks` map persist as NULL (no implicit default mask)**
  - Spec source: `.session/52-3-session.md` AC1 (Acceptance Criteria, line 36) + AC5 (No Silent Fallbacks)
  - Spec text: "If mask is None, leave the column NULL" — read at the region grain rather than the call grain.
  - Implementation: Tests assert that if `masks` covers only a subset of `expansion.new_nodes`, the uncovered regions get NULL BLOBs (never a broadcast of one region's mask, never a default empty grid).
  - Rationale: AC5's No-Silent-Fallbacks rule extends to the partial-masks case. Treating absence as NULL preserves Plan 5's freeze contract: a re-materialised region (impossible per spec §7, but defended against) cannot silently invent a mask.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)

- No deviations from spec. TEA's three signature/loader/NULL-semantics deviations are the implementation contract; I followed all three exactly. The base64 encoding of `mask_bytes` inside `RegionMask.to_dict()` is the obvious JSON-safe choice TEA called out in the Dev Notes — not a deviation, just the explicit binary-in-JSON contract.

### Architect (reconcile)

I audited every TEA + Dev entry above against the spec text and the shipped code. Verification status:

- **TEA AC1 signature deviation (line 117-123 above):** ✓ verified. Spec source `.session/52-3-session.md` AC1 (lines 33-37) quoted accurately. Spec text "commit_expansion accepts `mask: dict | None` parameter" is the exact wording. Implementation at `persistence.py:280` is `masks: Mapping[str, dict] | None = None` — accurate. Forward impact (Dev's `_stage_commit` change threads `fill_result`) materialised at `materializer.py:1784-1788` exactly as predicted. All 6 fields present and substantive.
- **TEA AC2 loader-shape deviation (line 125-130 above):** ✓ verified. Spec source AC2 (line 41-42) quoted accurately. Implementation `load_masks() -> dict[str, dict]` at `persistence.py:386` matches the description. Forward impact assertion — "52-4 and 52-5 consume `load_masks()` directly" — is consistent with the loader pattern; will be re-verified during 52-4. All 6 fields present and substantive.
- **TEA AC1 NULL-semantics deviation (line 132-138 above):** ✓ verified. Spec source AC1 line 36 + AC5 quoted accurately. Implementation at `persistence.py:307-318` matches: absent regions get `mask_blob = None`, no broadcast/default. The partial-mask test (`test_commit_expansion_partial_masks_only_writes_supplied_regions`) is the falsification gate. All 6 fields present and substantive.
- **Dev "no deviations" claim:** ✓ verified. Walked the diff: every implementation decision either matches the spec literally or matches one of TEA's three pre-logged deviations. No undocumented departures introduced.

Missed deviations added below — both are Reviewer-discovered, neither was logged by TEA/Dev:

- **Telemetry-timing deviation — `mask_write_span` fires before `conn.commit()` durably commits the BLOBs**
  - Spec source: SOUL.md / CLAUDE.md OTEL Observability Principle + `.session/52-3-session.md` AC1
  - Spec text: AC1 "OTEL: emit `dungeon.persist.mask_write` span with `mask_rows=N`" + CLAUDE.md OTEL section: "The GM panel is the lie detector. If a subsystem isn't emitting OTEL spans, you can't tell whether it's engaged or whether Claude is just improvising."
  - Implementation: `persistence.py:361-363` emits the span inside `commit_expansion` AFTER the INSERTs are staged via `conn.execute` but BEFORE the caller's `conn.commit()` at `materializer.py:1816`. On a subsequent `PersistError` (e.g. `put_frontier` IntegrityError), `_stage_commit` calls `conn.rollback()` discarding the staged rows — but the `mask_write_span` has already been emitted to OTEL.
  - Rationale: The implementation faithfully INHERITS the existing `dungeon_persist_commit_span` semantic (Plan 5 caller-owned-boundary contract, spec §7.5). The new `mask_write_span` placement is consistent with the project's established telemetry pattern, not a regression introduced by 52-3. The right architectural fix is a Plan-5-wide refactor — move both `dungeon_persist_commit_span` AND `mask_write_span` emissions into `_stage_commit` AFTER `conn.commit()` succeeds (mirror `frontier_expand_span`'s post-commit emission at `materializer.py:1841-1849`). That refactor has its own scope and risk surface; it belongs in a dedicated Plan-5-telemetry-honesty story, not as a tail-on to 52-3.
  - Severity: minor (inherited pattern, not net new misbehaviour)
  - Forward impact: Plan-5-wide. When the refactor happens, both `commit_expansion` AND `load_masks` need to relinquish their span emission to the caller. `mask_load_span` is unaffected by this concern — read paths don't have a commit/rollback divergence.

- **Out-of-scope diff hunks — ruff format collapse in `_stage_curate`**
  - Spec source: session scope is mask persistence only (no curate-stage changes specified)
  - Spec text: AC1-AC5 confine the implementation to `commit_expansion` / `load_map` / `dungeon_map.mask BLOB`; nothing in scope touches `_stage_curate`
  - Implementation: GREEN commit `1eed42f` includes two cosmetic hunks at `materializer.py:1262-1264` (collapsed two-line `span.set_attribute("reason", f"…")` call to single line) and `materializer.py:1322-1326` (collapsed two-line f-string in `degraded` reason attribute to single line). These are `ruff format` output produced when Dev ran the formatter over the full touched file rather than targeted hunks.
  - Rationale: Trivial formatter cleanup; zero behaviour change; matches project ruff config. Reverting would be churn-for-churn's-sake. Architect spec-check Mismatch 2 already recommended Option A (accept as-is); Reviewer audit confirmed.
  - Severity: trivial
  - Forward impact: none.

**AC accountability:** No ACs were deferred. All five ACs (AC1–AC5) have implementation + test coverage and were verified GREEN by reviewer-preflight (6550/0 full suite). No status changes required.

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD workflow; AC1–AC5 each demand observable, falsifiable behaviour.

**Test Files:**
- `sidequest-server/tests/dungeon/test_persistence_mask.py` — 16 unit tests (mask write, load, round-trip, loud-failure, OTEL)
- `sidequest-server/tests/dungeon/test_persistence_mask_wiring.py` — 2 integration tests driving the real `materialize()` coordinator to assert mask BLOBs land in `dungeon_map.mask` (the CLAUDE.md "every test suite needs a wiring test" requirement)

**Tests Written:** 18 tests covering 5 ACs + OTEL contract + wiring contract
**Status:** RED (13 + 2 failing on missing implementation; 3 passing legitimately — see rationale below)

### Rule Coverage

Project rules drove the test rubric beyond the bare ACs. Each row below maps a `gates/lang-review/python.md` check (or a SOUL.md / CLAUDE.md `<critical>` rule) to the test that would catch a violation.

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing (lang-review) | `test_load_masks_raises_serializationerror_on_corrupted_blob`, `test_commit_expansion_raises_persisterror_on_unserialisable_mask`, `test_load_masks_never_returns_empty_dict_to_paper_over_corruption` | failing |
| #6 test quality / vacuous assertions (lang-review) | self-check: every test asserts a concrete value (no `assert True`, no `assert result.is_some()`, no `let _ = ...`) — verified by inspection during authoring | passing (self-check) |
| #7 resource leaks — sqlite without context manager (lang-review) | round-trip tests use `tempfile.TemporaryDirectory` + explicit `c.close()` (mirrors existing `test_persistence.py` precedent); no leak path introduced | passing |
| #11 input validation / parameterised SQL (lang-review) | tests directly drive `commit_expansion` with hostile inputs (unserialisable masks, corrupted BLOBs); none use f-string SQL on inputs | passing (no SQL in tests) |
| No Silent Fallbacks (CLAUDE.md `<critical>`) | `test_commit_expansion_without_masks_leaves_blob_null`, `test_commit_expansion_partial_masks_only_writes_supplied_regions`, `test_load_masks_omits_regions_with_null_mask_column`, `test_load_masks_never_returns_empty_dict_to_paper_over_corruption` | passing/failing |
| No Stubbing / Verify Wiring (CLAUDE.md `<critical>`) | `test_materialize_pipeline_writes_mask_blobs_for_generated_regions`, `test_materialize_then_reload_returns_masks_for_generated_regions` (real coordinator, real DungeonStore, real connection) | failing |
| OTEL Observability Principle (CLAUDE.md `<important>`) | `test_mask_persist_spans_registered_and_routed`, `test_commit_expansion_emits_mask_write_span_with_mask_rows_attr`, `test_commit_expansion_does_not_emit_mask_write_span_when_no_masks_supplied`, `test_load_masks_emits_mask_load_span_with_mask_rows_attr` | failing/passing |
| AC4 No schema migration | `test_dungeon_map_mask_column_present_after_ensure_schema_no_new_migration` | passing (Plan 5 column already present) |
| Save-is-truth / byte-identical reload (spec §7) | `test_masks_byte_identical_after_save_reopen_over_wal_file`, `test_masks_survive_three_expansion_chain_on_wal_save` | failing |

**Rules checked:** 9 of 14 applicable lang-review rules have test coverage. The remaining five (mutable defaults, type annotations, logging, path handling, async pitfalls) are dev-facing implementation rules — not test rubric items. The implementer will satisfy them inside `persistence.py` and `materializer.py`.

**Self-check:** 0 vacuous tests found. Every test asserts a concrete value or call-shape; the failure messages quote the offending field/region so the bug is identifiable from the test output alone (CLAUDE.md "Tests pass quickly? Add the slow path…" — round-trip and three-expansion-chain tests added).

### Legitimately-passing tests (verified to PASS today AND post-implementation)

Three tests pass against the current codebase but are NOT vacuous — they encode preserved invariants:

1. `test_dungeon_map_mask_column_present_after_ensure_schema_no_new_migration` — AC4 promise; Plan 5 already shipped the column. This test guards against accidental migration drift.
2. `test_commit_expansion_without_masks_leaves_blob_null` — the existing `commit_expansion` doesn't accept a `masks` kwarg, so the test calls it without one; the BLOB is NULL because no write path exists yet. Post-implementation, the kwarg defaults to None and the BLOB must remain NULL. The test asserts the post-implementation behaviour at the existing call grain — it passes today and MUST keep passing after Dev's change. (A future regression where the implementation invents a default mask would flip this test to fail.)
3. `test_commit_expansion_does_not_emit_mask_write_span_when_no_masks_supplied` — same shape. The `dungeon.persist.mask_write` span doesn't fire today (no span exists). Post-implementation, the span must STILL not fire when `masks` is None. The Illusionism guard is the test's purpose.

### Dev Notes (read before GREEN)

- **API shape:** `commit_expansion(expansion, graph, *, generator_version=..., masks: Mapping[str, dict] | None = None)`. The `masks` parameter is keyed by `region_id`. Regions in `expansion.new_nodes` that are absent from `masks` persist as NULL.
- **BLOB encoding:** `json.dumps(mask_dict, sort_keys=True).encode("utf-8")` for write; `json.loads(blob.decode("utf-8"))` for read. JSON serialisation failures must raise `PersistError` (with the existing `sqlite3.Error` / `IntegrityError` raise chain).
- **Loader shape:** new `DungeonStore.load_masks() -> dict[str, dict]`. Returns ONLY non-NULL rows. `SerializationError` on any corrupted BLOB (never partial / never empty-fallback).
- **OTEL constants:** add `SPAN_DUNGEON_PERSIST_MASK_WRITE = "dungeon.persist.mask_write"` and `SPAN_DUNGEON_PERSIST_MASK_LOAD = "dungeon.persist.mask_load"` in `sidequest/telemetry/spans/dungeon_persist.py`, register both in `SPAN_ROUTES` (state_transition / dungeon / `op=write_masks` or `op=load_masks`), and add helper context managers (`mask_write_span(...)`, `mask_load_span(...)`) that carry `mask_rows`. Open the write span ONLY when `masks is not None` (the lie-detector contract — spec §6 Illusionism guard).
- **Materializer wiring:** thread `fill_result: Mapping[str, RegionFill]` into `_stage_commit` (new kwarg); at the call site (line 1948), pass `fill_result=fill_result`. Inside `_stage_commit`, build `masks = {rid: rf.mask.to_dict() for rid, rf in fill_result.items() if rf.mask is not None}` and pass to `commit_expansion(..., masks=masks)`. The seed (Expansion 0) call gets no `masks` (entrance has no fill grid).
- **RegionMask → dict:** `RegionMask` (materializer.py:339) needs a `to_dict()` method (it doesn't have one — `frozen=True, slots=True`, four fields). Add it OR build the dict inline in `_stage_commit`. Either is acceptable; the wiring test only asserts the BLOB is valid JSON-decodable to a dict. `mask_bytes` must be base64-encoded for JSON safety (`base64.b64encode(mask_bytes).decode("ascii")`).
- **No schema migration:** the `mask BLOB` column is already in `DUNGEON_SCHEMA_SQL` (line 142). Do NOT add a migration.

### Forensic / save-inspection caveat

Memory `feedback_save_preservation_wal.md`: any test that does cross-process save inspection must `db+wal+shm` consolidate. The round-trip tests here use the SAME process (single `tempfile.TemporaryDirectory` block, two sequential connections on the same path with the conn closed between them). Pure SQLite handles WAL → main-DB merge on close, so this is safe — no cross-process step. If Dev adds a Forensics-style inspection layer, that path must use the trio-copy pattern.

**Handoff:** To Dev (Puck) for GREEN implementation.
## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 6550/0 passing (full sidequest-server sweep, 110s); 18/18 new tests GREEN
**Branch:** `feat/52-3-mask-blob-persistence` (pushed to `origin`)

**Files Changed (sidequest-server):**
- `sidequest/telemetry/spans/dungeon_persist.py` — new `SPAN_DUNGEON_PERSIST_MASK_WRITE` / `SPAN_DUNGEON_PERSIST_MASK_LOAD` constants, `SPAN_ROUTES` entries (component=dungeon, op=write_masks/load_masks, mask_rows attr), and `mask_write_span` / `mask_load_span` context-manager helpers
- `sidequest/dungeon/persistence.py` — `commit_expansion` gains optional `masks: Mapping[str, dict] | None` kwarg (per-region map); per-region BLOB write threaded through the existing INSERT; new `load_masks() -> dict[str, dict]` loader (omits NULL rows); loud `PersistError` on unserialisable mask; loud `SerializationError` on corrupted BLOB
- `sidequest/dungeon/materializer.py` — `RegionMask.to_dict()` (base64-encoded `mask_bytes` + `mask_sha` + `block` dict; `grid` omitted — `mask_bytes` is the truth per ADR-096 §2); `_stage_commit` gains `fill_result: Mapping[str, RegionFill] | None` kwarg; materializer call site threads `fill_result=fill_result` to commit stage; per-region masks built as `{rid: rf.mask.to_dict() for rid, rf in fill_result.items() if rf.mask is not None} or None`
- `tests/dungeon/test_persistence_mask.py` — ruff format/import-sort cleanup only (no logic change)
- `tests/dungeon/test_persistence_mask_wiring.py` — ruff format/import-sort cleanup only (no logic change)

### AC verification

| AC | Verification |
|----|---|
| AC1 mask write | `commit_expansion(..., masks=...)` writes JSON BLOB; absent regions stay NULL; unserialisable masks raise loudly. 3 unit tests + 1 OTEL span test green. |
| AC2 mask load | `load_masks()` returns per-region dict; NULL rows omitted; fresh save returns `{}`. 3 unit tests + 1 OTEL span test green. |
| AC3 reload on resume | WAL save → close → reopen → `load_masks()` returns byte-identical input. Single + three-expansion-chain tests green. |
| AC4 no migration | `dungeon_map.mask BLOB` column was already in Plan 5's `DUNGEON_SCHEMA_SQL`; only populated. Schema-introspection test green. |
| AC5 loud failures | `SerializationError` on corrupted BLOB; `PersistError` on unserialisable mask; corrupted row never returns `{}` silently. 3 tests green. |

### Rule compliance (lang-review checklist)

- **#1 silent exception swallowing** — both error paths raise `from exc` with specific exception types; no bare `except`; no `pass`-on-error
- **#3 type annotation gaps** — new kwargs annotated with `collections.abc.Mapping[str, dict]`; new loader returns `dict[str, dict]`; new helpers carry `Iterator[trace.Span]` return
- **#7 resource leaks** — no new connections opened; new code reuses caller-owned `self._conn` (the Plan-5 caller-owned-boundary contract)
- **#11 input validation** — all SQL is parameterised (`?` placeholders); no f-string SQL on inputs
- **OTEL Observability Principle** — both subsystem decisions (write, load) emit spans with `mask_rows` attribute; the write span fires ONLY when masks were supplied (Illusionism guard per spec §6)
- **No Silent Fallbacks** — every error path raises; no NULL substitution for failed JSON encode; no empty-dict fallback on corrupted load

### Self-review

- [x] Code wired to upstream caller (materializer's `_stage_commit`) and verified by integration test
- [x] Follows project patterns (mirrors `load_frontier` / `load_mutations` / `dungeon_persist_commit_span`)
- [x] All ACs met (5/5)
- [x] Error handling implemented (loud raises, no silent fallbacks)
- [x] Tests green (full suite 6550/0)

**Handoff:** To Reviewer (Portia) for code review.
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with three TEA-logged deviations already accepted in-flight)
**Mismatches Found:** 2 (1 Minor, 1 Trivial — both already covered by TEA deviation entries or out-of-scope formatter touches)

### Per-AC substance audit

| AC | Spec text (session lines 33–59) | Implementation | Verdict |
|----|---|---|---|
| AC1 — write | `commit_expansion` accepts `mask: dict \| None`; JSON-serialise; None → NULL; emit `dungeon.persist.mask_write` with `mask_rows=N` | `commit_expansion(..., masks: Mapping[str, dict] \| None = None)`; per-region JSON BLOB via `json.dumps(..., sort_keys=True).encode("utf-8")`; absent regions → NULL; span fires with `mask_rows=len(masks)` and ONLY when masks supplied (extra Illusionism guard) | ✅ aligned. Deviation logged by TEA (singular→plural per-region map); accepted (`dungeon_map.mask` is per-row). |
| AC2 — load  | `load_map deserialises BLOB → dict` (or None); return as RegionNode OR separate `RegionMaskMap loader`; "add to the `DungeonStore.load(...)` chain"; emit `dungeon.persist.mask_load` with `mask_rows=N` | new `DungeonStore.load_masks() -> dict[str, dict]` (separate loader); omits NULL rows; span fires (load span ALWAYS fires, even on fresh save) | ✅ aligned. Deviation logged by TEA (separate loader chosen over RegionNode attribute) — spec explicitly allowed it. See Minor finding below re "load() chain". |
| AC3 — reload| byte-identical reload over save; OTEL watcher shows both spans | round-trip + three-expansion-chain WAL tests green; both spans captured by InMemorySpanExporter | ✅ aligned |
| AC4 — no migration | column already exists; only populate | `dungeon_map.mask BLOB` unchanged in `DUNGEON_SCHEMA_SQL`; INSERT only | ✅ aligned |
| AC5 — loud failures | unserialisable mask → loud; corrupted BLOB → loud; never empty/default fallback | `PersistError` from `(TypeError, ValueError)` on `json.dumps`; `SerializationError` from `(JSONDecodeError, UnicodeDecodeError, AttributeError)` on load; corruption test asserts raise (never `{}`) | ✅ aligned |

### Mismatch 1 — "DungeonStore.load(...) chain" phrasing (Minor, Ambiguous spec → Different behavior)

- **Spec:** AC2 line 42 — "Add to the `DungeonStore.load(...)` chain"
- **Code:** `DungeonStore` has no unified `.load()` aggregator; the store exposes per-table loaders (`load_map`, `load_frontier`, `load_mutations`, `open_threads`). The new `load_masks()` follows that same per-table pattern.
- **Recommendation:** **C — clarify spec.** The existing codebase has no `DungeonStore.load(...)` chain — this phrase was aspirational, not load-bearing. The implementation correctly mirrors the established pattern. The spec wording is a leftover from an earlier mental model. No code change needed. Future stories (52-4, 52-5) consume `load_masks()` directly, exactly as they consume `load_map()` / `load_frontier()`. If a unified aggregator becomes useful later, that's a separate refactor with its own story.

### Mismatch 2 — Out-of-scope ruff formatter touch in `_stage_curate` (Trivial, Extra in code → Cosmetic)

- **Spec source:** session scope is mask persistence only.
- **Code:** `materializer.py` lines ~1261 + ~1321 — `ruff format` collapsed two multi-line string literals inside `_stage_curate` into single-line form. Zero behavioral change. These hunks are in the GREEN commit because Dev ran `ruff format` over the whole touched file rather than targeted hunks.
- **Recommendation:** **A — accept as-is.** Trivial formatter cleanup, no behavior change, no risk. Not worth a churn cycle to revert. Note in the spec-reconcile manifest as a known incidental cleanup.

### Deviation entries audited (all 6 fields present, accurate)

- TEA: 3 deviations (AC1 signature, AC2 loader shape, AC1 NULL semantics) — all 6-field compliant, all rationally justified, Dev followed all three.
- Dev: No additional deviations.

### Out-of-scope but worth flagging

The materializer commit-stage docstring at `materializer.py:56–61` STILL says "Mask persistence is a documented Plan-5-API gap" — this is now stale (the gap is closed). Updating that paragraph isn't strictly part of 52-3's ACs, but leaving it as-is will mislead anyone reading the materializer in the next sprint. Recommend Dev follow-up in a chore commit OR fold into 52-4's branch as a sibling cleanup. **Not a spec-check blocker** — purely an in-code documentation rot finding.

**Decision:** Proceed to review. No hand-back to Dev required. The TEA-logged deviations cover the interpretive choices, the implementation faithfully realises each AC's intent, and tests prove the contracts.
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (post-simplify 440/440 dungeon suite)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (materializer.py, persistence.py, dungeon_persist.py, test_persistence_mask.py, test_persistence_mask_wiring.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | 2 HIGH (test helper duplication, PRAGMA drift in wiring _mem_conn), 2 MEDIUM (serialise_to_blob helper, region-payload-write loud-failure parity), 1 LOW (span-route factory) |
| simplify-quality | 1 finding | 1 HIGH — stale docstring at `materializer.py:56-61` ("Mask persistence is a documented Plan-5-API gap") now factually false |
| simplify-efficiency | clean | No findings — empty-body span context managers are deliberate observability hooks (mirror existing `frontier_expand_span` pattern); per-row JSON load preserves AC5 per-row error isolation |

**Applied:** 1 high-confidence fix
- `materializer.py:56-61` docstring updated to describe shipped mask persistence path (commit `a844630`). Cross-confirmed by Architect's spec-check finding. Docstring-only — zero behavior change. Full dungeon suite 440/440 GREEN post-edit.

**Deferred (flagged in Delivery Findings for 52-4 or follow-up):**
- **Reuse-HIGH #1** — Test-helper duplication (`_mem_conn`, `_file_conn`, `_seed_graph`, `_generate_and_attach`) across `test_persistence_mask.py` and `test_persistence.py`. Documented as a deliberate mirror by the file's own comment ("keep the seam shape identical so a drift in PRAGMA/connection setup breaks both suites the same way"). Consolidating to a shared `tests/dungeon/conftest.py` is the right move but touches the pre-existing `test_persistence.py` helpers — a cross-story refactor with its own scope. **Defer to follow-up.**
- **Reuse-HIGH #2** — PRAGMA drift between `test_persistence_mask_wiring._mem_conn` (no `foreign_keys=ON`) and `test_persistence_mask._mem_conn` / `test_persistence._mem_conn` (`foreign_keys=ON`). **MISREAD by the reuse agent:** the wiring test's `_mem_conn` *intentionally* mirrors `test_materializer.py:30`'s `_mem_conn` (also no foreign_keys PRAGMA) because the wiring test imports `_real_cookbook_bundle` / `_commit_palette` etc. from `test_materializer.py` and reuses its connection shape. The two shapes serve two different fixture families. Not a bug — leave as-is.
- **Reuse-MEDIUM #1** — Extract `_serialize_to_blob(obj: dict) -> bytes` / `_deserialize_from_blob(blob: bytes) -> dict` helper. Real opportunity (the pattern recurs across `commit_expansion` region payload, mask BLOB, `put_frontier` payload, etc.) but touches all of pre-existing Plan 5 — out of 52-3 scope.
- **Reuse-MEDIUM #2** — Region payload write at `persistence.py:328` lacks the loud-failure try/except wrap that the new mask write has. Real bug-class (silent fallback risk on a non-serialisable region payload) but pre-existing Plan 5 code — out of 52-3 scope.
- **Reuse-LOW** — Span-route factory for mask spans. Premature; only two new spans; not actionable.

### Rule re-check (lang-review python.md)

Re-scanned the post-simplify diff against checks #1-#12:
- No silent exception swallowing introduced
- No new mutable defaults
- Type annotations preserved
- No new logging issues
- No path handling changes
- Test quality preserved (no new vacuous assertions)
- No new resource leaks
- No new deserialisation risks
- No async pitfalls touched
- No import hygiene regressions
- No new input validation gaps
- No dependency churn
- Fix-introduced regression check (#13): the simplify edit is documentation-only and was verified with the full dungeon suite (440/440) — no regression class introduced.

**Quality Checks:** Lint passing, full dungeon suite GREEN (440/440 post-edit), full sidequest-server suite 6550/0 (pre-edit baseline; verified docstring-only edit cannot regress).
**Handoff:** To Reviewer (Portia) for code review.

### Delivery Findings (verify)

Appended below under `### TEA (test verification)` in the main `## Delivery Findings` section.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 6550 passed / 0 failed / 396 pre-existing skips / zero code smells / lint clean |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (1 HIGH-conf, 1 MED, 3 LOW) | 1 confirmed (AC5.b missing post-raise assertion), 1 dismissed (PRAGMA divergence — intentional mirror of `test_materializer._mem_conn`), 3 deferred (LOW noise) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (1 HIGH-conf, 1 MED) | 2 confirmed — `load_masks` docstring lies "always fires"; test module docstring uses stale present-tense |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 (3 HIGH-conf, 1 MED) | 1 dismissed (FALSE POSITIVE: async tests "never run" — `pyproject.toml` has `asyncio_mode = "auto"`; verified both wiring tests pass in 0.52s), 1 dismissed (test type annotations on `async def test_*` — pytest convention, not a public API boundary), 1 deferred (Rule 14 mask_write_span timing — inherited Plan 5 convention, see below), 1 confirmed (cross-confirmation of AC5.b test gap) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled per `workflow.reviewer_subagents` settings)
**Total findings:** 3 confirmed, 6 dismissed (with rationale), 2 deferred

### Dismissal rationale (each cites specific evidence)

- **[RULE] async-tests-never-run** — FALSE POSITIVE. `sidequest-server/pyproject.toml:40` sets `asyncio_mode = "auto"` which auto-applies asyncio to all `async def` test functions per pytest-asyncio docs. **Verified empirically:** `uv run pytest tests/dungeon/test_persistence_mask_wiring.py -v` reports `2 passed in 0.52s` with both functions executing through to their assertions (the materialize → InMemorySpanExporter pipeline takes real time; a coroutine-not-awaited would return in <50ms). The rule-checker did not check pyproject.toml config before flagging. Mirrors memory `feedback_log_absence_not_deadness.md` — never call something dead from absence-of-decorator without checking config.
- **[RULE] async test return type missing `-> None`** — Dismissed. Pytest test functions are not "module boundary" public API; they're test collection targets. The lang-review rule #3 exempts internal helpers; tests are an analogous exception. Project convention across the entire `sidequest-server/tests/` tree confirms — no test function has `-> None`.
- **[TEST] PRAGMA `foreign_keys=ON` divergence in wiring `_mem_conn`** — Dismissed. The wiring test's `_mem_conn` (no PRAGMA) deliberately mirrors `tests/dungeon/test_materializer.py:30`'s `_mem_conn` (also no PRAGMA) because the wiring test imports `_real_cookbook_bundle` / `_commit_palette` / etc. from that file and reuses its full connection setup. Forcing a divergent PRAGMA on the wiring test's local `_mem_conn` would break the equivalence with `test_materializer.py`'s real-coordinator tests. TEA's verify assessment already addressed this with the same rationale.
- **[TEST] `_example_mask_dict` base64 string isn't valid base64** — Deferred (LOW). The fixture produces a JSON-round-trip-stable string; AC3 / AC5 tests verify byte-identical reload, not base64 validity. If a future story adds load-side base64 validation, the fixture needs an update — recording in follow-up findings.
- **[TEST] `mask_write_spans[-1]` IndexError robustness** — Deferred (LOW). The preceding assertion `"dungeon.persist.mask_write" in names` guarantees the list is non-empty. Defense-in-depth `assert mask_write_spans` would be a one-liner improvement but not load-bearing.
- **[TEST] cross-test private import fragility (`from tests.dungeon.test_materializer import _...`)** — Deferred (LOW). Explicitly documented as the established Plan 7 fixture-stack convention; the wiring test's own module docstring flags it loudly. If `test_materializer.py` ever splits, the import will break with `ImportError` at collection — that IS the "fail loud on rename" signal the convention is designed to produce.

### Deferred (logged in Delivery Findings for follow-up)

- **[RULE] Rule 14: `mask_write_span` fires before `conn.commit()`** — TRUE but **inherited Plan 5 convention**. The existing `dungeon_persist_commit_span` (persistence.py:290–353) ALSO wraps the INSERT loop and exits BEFORE the caller's `conn.commit()` at `_stage_commit` line 1816. The Plan 5 caller-owned-boundary contract (spec §7.5; documented at materializer.py:1779) deliberately means spans are "this commit_expansion call attempted" markers, not "this transaction durably committed" markers. The caller's `conn.commit()` happens later in `_stage_commit`, and on subsequent failure `conn.rollback()` discards the staged rows — but the span has already been emitted. The new `mask_write_span` inherits this exact property without making it worse. Architecturally, the right fix is to introduce a post-commit summary span in `_stage_commit` (after line 1816's `conn.commit()`) that covers the full transaction — that's a Plan-5-wide refactor with its own story. **Not blocking; logged.**

### Confirmed findings (in severity order)

#### [LOW] [DOC] `load_masks` docstring claims span "always fires" — false on corruption path

- **File:** `sidequest-server/sidequest/dungeon/persistence.py:393`
- **Code:** docstring says: `The corresponding ``dungeon.persist.mask_load`` span always fires (carries ``mask_rows`` so the GM panel can confirm the load path engaged).`
- **Reality:** the span is opened at line 411 — AFTER the `try/except` block that raises `SerializationError` on a corrupted BLOB (lines 405-409). On the corruption path the exception unwinds out of `load_masks` BEFORE line 411 ever executes; no span fires.
- **Severity:** LOW. Behavior is correct (loud raise is its own loud signal); docstring is misleading.
- **Suggested fix:** Replace "always fires" with "fires on successful load (including empty returns mask_rows=0); raises `SerializationError` BEFORE firing if any BLOB is corrupted." Optionally move the span into a `finally` if the contract is truly meant to be unconditional — but the current behavior (no span on corruption) is reasonable: corruption is a loud exception channel and a span emitted with stale `mask_rows` from a partial decode would be misleading.

#### [LOW] [DOC] test module docstring uses present-tense to describe the gap this story closes

- **File:** `sidequest-server/tests/dungeon/test_persistence_mask.py:3-7`
- **Code:** `"commit_expansion persists RegionNode.to_dict() but does NOT write the dungeon_map.mask BLOB column, and no Plan 1–6 code consumes a persisted mask on reload."`
- **Reality:** The code in this very commit closes that gap. Present-tense reads as "current state" — a future reader without context will misunderstand.
- **Severity:** LOW. Test file docstring rot, mirrors the same class of rot that simplify-quality already fixed in `materializer.py:56-61`.
- **Suggested fix:** Past-tense rewrite. `"commit_expansion previously persisted only RegionNode.to_dict() and did NOT write the dungeon_map.mask BLOB column; no Plan 1-6 code consumed a persisted mask on reload. Story 52-3 closes that gap; these tests validate the closure."`

#### [LOW] [TEST] AC5.b test docstring claims partial-write absence but no assertion verifies it

- **File:** `sidequest-server/tests/dungeon/test_persistence_mask.py:801` (cross-confirmed by reviewer-test-analyzer + reviewer-rule-checker)
- **Code:** docstring at line 805: `"The call must abort BEFORE any partial row write (the seed row may already exist; assertion is only that the expansion's rows do not exist after the raise)."`
- **Reality:** test body has `pytest.raises(PersistError)` + `conn.rollback()` and returns. No `SELECT 1 FROM dungeon_map WHERE expansion_id = 1` assertion.
- **Severity:** LOW. The test passes today because the JSON-encode happens BEFORE the INSERT (persistence.py:311–318: the try wraps `json.dumps`, the INSERT only runs if the encode succeeded). The defensive assertion is missing but the contract is upheld at the implementation level.
- **Suggested fix:** Add after `conn.rollback()`: `rows = conn.execute("SELECT region_id FROM dungeon_map WHERE expansion_id = 1").fetchall(); assert not rows, f"partial expansion rows leaked after PersistError: {rows!r}"`. Closes the docstring/assertion gap as defense-in-depth.

---

## Reviewer Independent Observations

- **[VERIFIED] Parameterised SQL throughout** — `persistence.py:319-330` (INSERT dungeon_map mask column), `persistence.py:398-400` (SELECT mask), `tests/dungeon/test_persistence_mask.py:783,840` (corruption fixture INSERTs) all use `?` placeholders. Zero f-string SQL. Complies with python.md rule #11 (Security: input validation at boundaries).
- **[VERIFIED] No silent fallbacks on either edge of the mask BLOB seam** — `persistence.py:311-318` raises `PersistError` on `(TypeError, ValueError)` from `json.dumps`; `persistence.py:405-409` raises `SerializationError` on `(JSONDecodeError, UnicodeDecodeError, AttributeError)` from `json.loads`/`decode`. NULL rows are OMITTED from `load_masks()` results (line 401 `WHERE mask IS NOT NULL`), never substituted with `{}` or `None`. Complies with CLAUDE.md `<critical>` No Silent Fallbacks rule and AC5.
- **[VERIFIED] Illusionism guard on write span correctly implemented** — `persistence.py:361` opens `mask_write_span` ONLY when `masks is not None`. Verified by test `test_commit_expansion_does_not_emit_mask_write_span_when_no_masks_supplied` (test file line 950). Complies with CLAUDE.md OTEL Observability Principle and SOUL.md spec §6 lie-detector framing.
- **[VERIFIED] Wiring end-to-end** — `_stage_commit` (materializer.py:1632) accepts `fill_result` kwarg; `materialize()` (materializer.py:1995) passes `fill_result=fill_result` at the call site; `_stage_commit` builds per-region mask dict and passes `masks=expansion_masks` to `commit_expansion` (line 1791); `commit_expansion` writes BLOB. End-to-end wiring verified by `test_materialize_pipeline_writes_mask_blobs_for_generated_regions` (wiring test, 2 passed in 0.52s on direct invocation). Complies with CLAUDE.md "Verify Wiring, Not Just Existence".
- **[VERIFIED] AC4 no-migration claim** — `DUNGEON_SCHEMA_SQL` at `persistence.py:138-203` unchanged in diff. The `mask BLOB` column at line 145 was already present in Plan 5. Verified by `test_dungeon_map_mask_column_present_after_ensure_schema_no_new_migration` introspecting `PRAGMA table_info(dungeon_map)`.
- **[VERIFIED] Type annotations on public API surface** — `masks: Mapping[str, dict] | None = None`, `fill_result: Mapping[str, RegionFill] | None = None`, `load_masks() -> dict[str, dict]`, `RegionMask.to_dict() -> dict`, `mask_write_span(*, mask_rows: int, ...) -> Iterator[trace.Span]`. Complies with python.md rule #3.
- **[VERIFIED] Resource hygiene in tests** — every `_file_conn` callsite uses `tempfile.TemporaryDirectory` as context manager + explicit `c1.close()` / `c2.close()`. In-memory `sqlite3` connections (`_mem_conn`) don't need closure (GC handles). Complies with python.md rule #7.
- **[VERIFIED] No mutable defaults** — `masks=None`, `fill_result=None`, no `def f(items=[])` patterns. Complies with python.md rule #2.
- **[VERIFIED] OTEL span constants routed** — `SPAN_DUNGEON_PERSIST_MASK_WRITE` + `SPAN_DUNGEON_PERSIST_MASK_LOAD` in `SPAN_ROUTES` at `dungeon_persist.py:43-60` with `event_type=state_transition`, `component=dungeon`, `field=dungeon_map.mask`, `op=write_masks`/`load_masks`, `mask_rows` attribute. Verified by `test_mask_persist_spans_registered_and_routed`.
- **[MEDIUM] Documentation rot trio** — Three places confirmed where docstrings describe state that this very commit changed:
  1. ✓ Fixed in commit `a844630`: `materializer.py:56-61`
  2. ✗ Open: `persistence.py:393` `load_masks()` claims span "always fires"
  3. ✗ Open: `test_persistence_mask.py:3-7` module docstring still present-tense about the gap
  All three are documentation-only, not behavior. Flagged for Dev follow-up in a chore commit; not blocking.

### Data flow trace

Input: a freshly-`_emit_mask`'d `RegionMask` (materializer.py:359-390) from a fill-stage cellular cavern generator. Trace:

1. `_stage_fill` produces `RegionFill(grid, mask=<RegionMask>)` per node (materializer.py:756 area).
2. `materialize()` holds `fill_result: dict[region_id, RegionFill]` (materializer.py:1932).
3. `materialize()` passes `fill_result=fill_result` to `_stage_commit` (materializer.py:1995).
4. `_stage_commit` builds `expansion_masks = {rid: rf.mask.to_dict() for rid, rf in fill_result.items() if rf.mask is not None} or None` (materializer.py:1784-1788). The `or None` coerces empty dict → None so the Illusionism guard at the persistence layer fires correctly.
5. `_stage_commit` calls `persistence.commit_expansion(expansion, graph, generator_version=..., masks=expansion_masks)` (materializer.py:1789-1793). Seed (Expansion 0) call uses no masks (entrance has no fill grid).
6. `commit_expansion` walks `expansion.new_nodes`; for each node looks up `masks[live.id]`; on hit, `json.dumps(masks[live.id], sort_keys=True).encode("utf-8")` → BLOB. On absence, mask_blob stays None (column NULL).
7. INSERT writes (region_id, expansion_id, depth_score, generator_version, payload, mask) — 6 cols.
8. After the inner loop, IF masks is not None, `with mask_write_span(mask_rows=len(masks)): pass` emits the OTEL span.
9. Reload: `DungeonStore.load_masks()` runs `SELECT region_id, mask FROM dungeon_map WHERE mask IS NOT NULL`, decodes each BLOB via `json.loads(r["mask"].decode("utf-8"))`, builds `dict[str, dict]`, emits `mask_load_span(mask_rows=len(masks))`, returns.

Data is internal — never reaches a user input boundary (the BLOB is written by this code and read by this code on the same SQLite save). No tenant isolation surface; no auth check applicable. No web-facing input → no injection surface, validated by parameterised SQL.

### Rule Compliance (lang-review/python.md)

| # | Rule | Compliance | Evidence |
|---|------|------------|----------|
| 1 | Silent exception swallowing | ✓ Compliant | All `except` blocks catch specific types; all raise (PersistError, SerializationError, DatabaseError) with `from exc`. No bare except. |
| 2 | Mutable default arguments | ✓ Compliant | `masks=None`, `fill_result=None`. |
| 3 | Type annotation gaps | ✓ Compliant | Public API surface (commit_expansion kwarg, load_masks return, RegionMask.to_dict, span helpers) all annotated. Test function `-> None` exempt per existing project convention. |
| 4 | Logging coverage/correctness | ✓ Compliant | No logging changes; project convention is raise-not-log for dungeon persistence. |
| 5 | Path handling | ✓ Compliant | `pathlib.Path(d) / "save.db"`; no string concatenation. |
| 6 | Test quality | ⚠ One LOW finding | AC5.b test missing post-raise row-absence assertion. All other 17 tests have meaningful assertions with diagnostic messages. |
| 7 | Resource leaks | ✓ Compliant | `tempfile.TemporaryDirectory` with-statement; explicit `c.close()` after WAL writes. |
| 8 | Unsafe deserialization | ✓ Compliant | `json.loads` only on internally-written BLOBs; no pickle/eval; SerializationError guards malformed bytes. |
| 9 | Async/await pitfalls | ✓ Compliant | `_stage_commit` is sync (correct — only sqlite ops); `materialize()` passes fill_result as plain kwarg; wiring tests run under `asyncio_mode = "auto"` per pyproject.toml line 40. |
| 10 | Import hygiene | ✓ Compliant | Explicit named imports; no star imports; cross-test private import in wiring test is a documented established convention. |
| 11 | Security: input validation | ✓ Compliant | All SQL parameterised; no f-string SQL. |
| 12 | Dependency hygiene | ✓ Compliant | No pyproject.toml changes. |
| 13 | Fix-introduced regressions | ✓ Compliant | None observed. |
| 14 | State cleanup ordering | ⚠ Inherited convention | `mask_write_span` fires before caller's `conn.commit()` — but this matches the existing `dungeon_persist_commit_span` pattern (Plan 5 caller-owned-boundary contract per spec §7.5). Pre-existing semantic; not a regression. Logged for future Plan-5-wide refactor. |

### Devil's Advocate

**Argument: this code is broken.**

Imagine a stressed production save on a real disk. The materializer runs, fills five regions, builds five masks, and threads them into `commit_expansion`. The function encodes each mask successfully — `json.dumps` is fine, the BLOBs are crafted. INSERTs are staged on the connection. The `mask_write_span` fires with `mask_rows=5` — telemetry says "five masks written." The GM panel lights up green.

Then `_stage_commit` calls `put_frontier` for the new unexpanded edges. Disk is nearly full. `put_frontier` raises `DatabaseError`. The `except PersistError` block at `_stage_commit:1817` catches it, calls `conn.rollback()`, and re-raises. The INSERT rows — including the staged mask BLOBs — are discarded. The save has nothing.

The GM panel still shows the mask_write span. The player reloads. `load_masks()` returns `{}`. The dashboard sees: write span said five masks, load returned zero. **Did the masks get written?** Yes (staged). **Are they durable?** No (rolled back). **Will the GM panel correctly interpret this?** Depends on whether anyone looks for the matching commit span — and the commit span ALSO fired before rollback. So the GM panel sees TWO false positives.

This is the Rule 14 finding manifest. **But the existing `dungeon_persist_commit_span` has the same property** — the rule was violated by Plan 5 before this story existed. The new mask_write_span inherits the convention. To fix it properly, both spans need to move out of `commit_expansion` and into `_stage_commit` AFTER `conn.commit()` succeeds. That's a Plan-5-wide refactor — separate story.

What else could break? The reload-on-resume test asserts byte-identical reload. The test uses `tempfile.TemporaryDirectory` with `_file_conn` (WAL mode). It writes, commits, closes c1, opens c2, reads. Between c1.close() and c2 open, the WAL would normally be checkpointed by SQLite's auto-checkpoint or by a clean close. In production save reuse, the connection isn't closed between sessions — it's reused on the same process. Is the test exercising the production reload pattern correctly? Memory `feedback_save_preservation_wal.md` is the relevant prior: cross-process WAL reads need db+wal+shm trio consolidation. Here the test is single-process sequential — pure SQLite handles the WAL→main DB merge on close. The test is sound, but the production path (long-lived session connection) is different. **What if a session crashes mid-commit?** The save's WAL contains the staged INSERTs; recovery on next open will replay them. Per AC3, byte-identical reload still holds. Not a finding, but worth thinking through.

What about a malicious mask payload? `_example_mask_dict` in tests is a constructed dict; in production, `RegionMask.to_dict()` builds the dict from typed fields (`mask_bytes: bytes` → base64 string, `mask_sha: str`, `block: BlockInfo` → flat dict of ints). Everything is JSON-safe by construction. **A non-deterministic RegionMask (e.g. via a corrupted upstream)** can't sneak through — the dataclass is `frozen=True, slots=True`. Bytes that don't decode to valid base64? `base64.b64encode` only emits valid base64; `b64decode` isn't called on the write path. Safe.

What about an empty fill_result? `materializer.py:1786` builds `expansion_masks = {} or None` if every `rf.mask is None`. The `or None` ensures `masks=None` reaches `commit_expansion`, so no write span fires. Good. **But what if fill_result is non-empty AND every entry has a mask?** Standard path — works. **What if fill_result has entries whose `rid` is NOT in `expansion.new_nodes`?** They'd be in `masks` but never matched in the `commit_expansion` loop (which only iterates `new_nodes`). The mismatch is silent — those extra masks just don't get written. The write span still reports `mask_rows=len(masks)` though, which could over-report. **This IS a real edge case.** But the materializer constructs both `expansion.new_nodes` and `fill_result` from the same generator — they're guaranteed to align by construction. The test fixture confirms (`fill_result` is keyed by node id). Not actionable unless the materializer's seam ever loosens.

What about a confused contributor reading the code in six months? The `materializer.py:56-61` rewrite by simplify is clear about what the new pipeline does. The `load_masks` docstring's "always fires" lie could trip them up — they'd assume corrupted-BLOB telemetry surfaces a span, when actually it surfaces an exception. **That's the strongest argument for a docstring fix before merge** — not because the behavior is wrong, but because a reader's mental model will be wrong.

Conclusion: the code is correct. The documentation has three rot points (one fixed, two open). The Rule 14 inheritance is a real architectural concern but pre-existing. The AC5.b test is under-asserted but functionally correct. **Approve with non-blocking follow-ups.**


## Design Deviations — Reviewer Audit

(Audit of TEA + Dev + Architect entries from `## Design Deviations` above.)

### Reviewer (audit)

- **AC1 signature: `mask: dict | None` → `masks: dict[region_id, dict] | None`** (TEA, accepted by Dev) → ✓ **ACCEPTED by Reviewer.** Per-region map is the only correct addressing for a per-row column. Architect's spec-check Mismatch-1 narrative aligns; nothing further to flag.
- **AC2 loader shape: separate `load_masks() -> dict[str, dict]` instead of RegionNode-attached** (TEA, accepted by Dev) → ✓ **ACCEPTED by Reviewer.** Spec explicitly permitted "or a separate `RegionMaskMap` loader"; the implementation mirrors the established Plan 5 loader pattern (`load_frontier`, `load_mutations`, `open_threads`). Architect's Mismatch-1 ("DungeonStore.load(...) chain" wording) is correctly classed as ambiguous spec; the implementation is the right interpretation given the codebase.
- **AC1 NULL semantics: per-region absence → NULL** (TEA, accepted by Dev) → ✓ **ACCEPTED by Reviewer.** Preserves Plan 5's freeze contract and AC5's No-Silent-Fallbacks rule at the region grain. The partial-mask test (`test_commit_expansion_partial_masks_only_writes_supplied_regions`) verifies the contract.
- **Dev: No deviations** → ✓ **ACCEPTED by Reviewer.** Implementation followed TEA's three deviations exactly; nothing else introduced. Base64-encoding of `mask_bytes` in `RegionMask.to_dict` is the obvious JSON-safe choice and was explicitly noted in TEA's Dev Notes — not a hidden deviation.
- **Architect: Mismatch 1 (recommendation C — clarify spec)** → ✓ **ACCEPTED by Reviewer.** "DungeonStore.load(...) chain" is aspirational; no aggregator exists in the codebase; the per-loader pattern is the established convention.
- **Architect: Mismatch 2 (formatter touches in `_stage_curate`, recommendation A — accept as-is)** → ✓ **ACCEPTED by Reviewer.** Verified the two hunks at `materializer.py:1262-1264` and `1322-1326` — ruff format collapsed two `f"..."` continuations into single-line form. Zero behavioral change; clean code; not worth a revert.
- **UNDOCUMENTED — Rule 14 telemetry timing** → **FLAGGED (informational, not blocking).** TEA + Dev + Architect did not log the `mask_write_span` ordering concern. This is because it's inherited convention from Plan 5's `dungeon_persist_commit_span` — not introduced by this story. Filed in Delivery Findings for a future Plan-5-wide telemetry refactor.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** fill_result `Mapping[region_id, RegionFill]` from `_stage_fill` → `_stage_commit` reads `rf.mask.to_dict()` per region → `commit_expansion(masks=...)` JSON-encodes per row → `dungeon_map.mask BLOB`. Safe because: parameterised SQL, internal payload (never user-supplied), loud failure on encode/decode errors, parameterised reload via `load_masks()` returns byte-identical dict.

**Pattern observed:** Plan 5 caller-owned-boundary contract is correctly extended — `commit_expansion` accepts the new `masks` kwarg as an optional Mapping, the loader (`load_masks`) mirrors the established per-table loader pattern, and the OTEL span helpers (`mask_write_span` / `mask_load_span`) follow the existing `dungeon_persist_commit_span` shape exactly (`@contextmanager` with `Span.open` and `tracer_override` plumbing). All three additions are idiomatic.

**Error handling:** `PersistError` raised on unserialisable mask (`persistence.py:316`) with `from exc` chain. `SerializationError` raised on corrupted BLOB (`persistence.py:409`) — also `from exc`. `DatabaseError` raised on `sqlite3.Error` (`persistence.py:402`). NULL preserved as "no mask known" — never substituted by the loader. Complies with CLAUDE.md `<critical>` No Silent Fallbacks rule.

**Wiring confirmed:** `test_materialize_pipeline_writes_mask_blobs_for_generated_regions` (wiring test) drives the real five-stage coordinator and asserts BLOBs land in `dungeon_map.mask` — verified to run (not skipped) by `asyncio_mode = "auto"` in pyproject.toml; 2 passed in 0.52s on direct invocation.

**Test verdict:** 6550/0 full sweep; 18/18 new tests green; one LOW-severity test gap (AC5.b under-asserts) and one LOW-severity docstring inaccuracy in tests — both filed as follow-ups, neither blocks.

**Findings summary:** 0 Critical / 0 High / 0 Medium / 3 Low. Specialist-tagged:
- `[LOW] [DOC]` `load_masks` docstring at `persistence.py:393` lies "always fires" — span actually skipped on SerializationError path (corroborated by reviewer-comment-analyzer).
- `[LOW] [DOC]` test module docstring at `test_persistence_mask.py:3-7` uses present-tense for the now-closed gap (corroborated by reviewer-comment-analyzer).
- `[LOW] [TEST]` AC5.b test at `test_persistence_mask.py:801` lacks the post-raise row-absence assertion its docstring promises (corroborated by reviewer-test-analyzer AND reviewer-rule-checker).

**Inherited concerns flagged but not blocking:**
- `[LOW] [RULE]` Rule 14 — `mask_write_span` fires inside `commit_expansion` BEFORE the caller's `conn.commit()` (caught by reviewer-rule-checker). This matches the pre-existing `dungeon_persist_commit_span` pattern (Plan 5 caller-owned-boundary contract). Not a regression introduced by 52-3; remediation requires a Plan-5-wide telemetry refactor — move both span emissions into `_stage_commit` after `conn.commit()` succeeds, mirroring `frontier_expand_span`'s post-commit emission pattern at `materializer.py:1841-1849`.

**Dismissed with rationale:**
- `[RULE]` Rule 6 async-tests-never-run — FALSE POSITIVE: `pyproject.toml:40` sets `asyncio_mode = "auto"`; verified empirically with `uv run pytest tests/dungeon/test_persistence_mask_wiring.py -v` reporting 2 passed in 0.52s.
- `[RULE]` Rule 3 async test functions missing `-> None` — dismissed: pytest test functions are collection targets, not module-boundary public API; project-wide convention exempts them.
- `[TEST]` PRAGMA `foreign_keys=ON` divergence in wiring `_mem_conn` — dismissed: intentional mirror of `test_materializer.py:30` so cross-test helper imports keep matching connection shape.

**Handoff:** To SM (Prospero) for finish-story.

### Delivery Findings (Reviewer)