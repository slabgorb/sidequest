---
story_id: "76-11"
jira_key: ""
epic: "76"
workflow: "tdd"
---
# Story 76-11: Location source coverage v2 — wire room-graph + world_materialization adapters into the entity index

## Story Details
- **ID:** 76-11
- **Jira Key:** (none — personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Type:** feature
- **Points:** 5
- **Priority:** p3
- **Repos:** sidequest-server

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T20:10:22Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T20:45:00Z | 2026-06-04T19:37:39Z | -4041s |
| red | 2026-06-04T19:37:39Z | 2026-06-04T19:50:38Z | 12m 59s |
| green | 2026-06-04T19:50:38Z | 2026-06-04T20:04:30Z | 13m 52s |
| review | 2026-06-04T20:04:30Z | 2026-06-04T20:10:22Z | 5m 52s |
| finish | 2026-06-04T20:10:22Z | - | - |

## Story Overview

Extends the entity index (ADR-118) location source coverage beyond v1 (PG `location_promotions` only) to wire room-graph rooms and world_materialization outputs as adapters. Additionally batches the per-region promotion read (perf) and surfaces per-region read failures as watcher events (observability).

**Carryover source:** 76-7 Reviewer/Dev Delivery Findings (see `sprint/archive/76-7-session.md` lines 66–142), where Dev v1-partial implementation (PG promotions only) was approved with a documented follow-up for the remaining two sources + perf/observability improvements.

## Technical Details
- **Repos:** sidequest-server (github-flow: feature branch off develop)
- **Branch Strategy:** gitflow
- **Branch:** feat/76-11-location-source-coverage-v2
- **Base:** develop
- **Core file:** `sidequest/server/dispatch/entity_sync.py::_collect_location_views` + `sidequest/game/entity_card.py`
- **Tests Required:** 
  - Room-graph room locations end-to-end flow to location_count (source-tagged "room").
  - World_materialization location outputs end-to-end flow to location_count (source-tagged "materialization").
  - Per-region promotion read batched into a single DB call (perf assertion).
  - Per-region read failures increment `result.failed` AND publish a watcher event (observability).
  - Wiring test: all three sources integrated into production `sync_for_turn(handler, sd)` seam.

## Acceptance Criteria

**AC1: room-graph room locations flow end-to-end to non-zero location_count**
- Behavioral test (mirroring 76-7's `TestPromotionLocationFlowsEndToEnd`):
  - Seed a snapshot with a real room in interior state.
  - Call `sync_for_turn(handler, sd)`.
  - Assert `entity_sync_result.location_count >= 1` AND at least one card has `source="room"`.
  - Use fixture world `caverns_and_claudes/flickering_reach` (no live content).

**AC2: world_materialization location outputs flow end-to-end to location_count**
- Behavioral test (same shape as AC1):
  - Seed a materialization that emits a location context (region, scene, etc.).
  - Call `sync_for_turn(handler, sd)`.
  - Assert `location_count >= 1` AND at least one card has `source="materialization"`.

**AC3: Per-region promotion read is batched into a single DB read**
- Performance assertion:
  - Discover N regions.
  - Verify `list_location_promotions` is called **once** with a batched input (not N separate calls).
  - Spy/mock assertion: `list_location_promotions.call_count == 1`.

**AC4: Per-region read failures increment result.failed AND publish a watcher event**
- Observability test:
  - Mock `list_location_promotions` to raise an exception for region X.
  - Call `sync_for_turn(...)`.
  - Assert `result.failed >= 1`.
  - Assert watcher event published with detail (e.g., `op="sync_failed"` + region id + error).

**AC5: Each new source has a non-test consumer (wiring test)**
- Reachability assertion:
  - From `sync_for_turn(handler, sd)` (production dispatch seam), trace to both room-graph and materialization adapters in `_collect_location_views`.
  - No half-wired adapters; if an adapter exists but is never called from production, the story is incomplete.

## Key References & Dependencies
- **ADR-118 — Universal Retrieval Layer:** entity card sync/reproject pattern (§D2), per-source adaptation belongs to consumer (§D3).
- **Story 76-7 context:** Promotion-location v1 wiring + projector + `LocationSyncView` dataclass (template for extending).
- **Story 76-7 Delivery Findings:** `sprint/archive/76-7-session.md` lines 66–142 (the source of this story's three threads).
- **Epic 76 context:** full scope and cross-story dependencies.

**Files to Review:**
- `sidequest-server/sidequest/server/dispatch/entity_sync.py` — `_collect_location_views` (extend with room-graph + materialization adapters), `sync_for_turn`, `sync_entity_cards`, `_apply_typed_card`, `_watcher_publish`.
- `sidequest-server/sidequest/game/entity_card.py` — `project_location_card` projector, `LocationSyncView` normalized-view dataclass.
- `sidequest-server/sidequest/game/location_view.py` — `get_location_prose`, `get_location_manifest` (use existing contract, do not modify).
- `sidequest-server/tests/server/dispatch/test_entity_sync_sources_wiring.py` — existing faction + promotion e2e tests (mirror for room-graph + materialization).
- Interior state models (`snapshot.interior.rooms`).
- World_materialization module (location context generation).

## Sm Assessment

**Story is well-scoped and ready for RED.** 76-11 is a clean, single-repo (`sidequest-server`), single-file-centric follow-up whose entire scope was pre-defined by 76-7's Reviewer/Dev/TEA Delivery Findings (`sprint/archive/76-7-session.md` lines 66–142). The title carries the spec; there is no ambiguity about what's owed.

**Three independent threads, all converging on `_collect_location_views`:**
1. **Source coverage v2 (core, ~3pt):** Wire the two deferred location sources — room-graph rooms + world_materialization — as adapters feeding the *existing* source-agnostic projector/`LocationSyncView`/`sync_entity_cards(locations=)` plumbing 76-7 already built. The lift is the authored-prose resolution (`location_view.get_location_prose`/`get_location_manifest`), since neither source carries prose natively. The projector's blank-description guard MUST stay — no synthesized/stub descriptions (No Silent Fallbacks / No Stubbing).
2. **Batch the per-region read (perf):** Collapse the O(N) per-turn `list_location_promotions` DB round-trips into one batched read. Pin with a call-count assertion.
3. **Watcher event on read failure (observability):** The current silent `continue` under-reports `location_count` with no GM-panel signal — violates the OTEL Observability Principle. Increment `result.failed` AND publish a watcher event. This is mandatory, not optional.

**Risk notes for TEA/Dev:**
- The largest unknown is THREAD 1's adapter shape — what a room-graph room and a materialization output expose as a resolvable `region_id`/authored-description into `location_view`. ADR-118 §D3 puts this design squarely on the consumer (Dev), so TEA should pin behavior through the stable `sync_for_turn(handler, sd)` seam + the `source=` tag, NOT force an inner adapter signature (this is exactly how 76-7's TEA handled the diffuse faction/location sources — follow that precedent).
- Tests MUST use fixture packs (`caverns_and_claudes/flickering_reach`); `tests/server/` autouse `_fixture_pack_search_paths` makes live `sidequest-content` unreachable. Do not point tests at live world slugs.
- Mirror the existing e2e shapes in `tests/server/dispatch/test_entity_sync_sources_wiring.py` (`TestRealWorldFactionsFlowEndToEnd`, `TestPromotionLocationFlowsEndToEnd`).

**Routing:** Handing to TEA (Igor) for the RED phase. No blockers, no open design questions that should hold setup.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5pt feature story — three behavioral threads (two new location source adapters + a perf refactor + an observability fix), all with concrete acceptance criteria.

**Test Files:**
- `sidequest-server/tests/server/dispatch/test_entity_sync_location_sources_v2.py` — 6 RED tests driving the production `sync_for_turn` seam against the `flickering_reach` fixture world (real authored cartography prose; no live-content coupling).

**Tests Written:** 6 tests covering 5 ACs
**Status:** RED (all 6 failing — verified — ready for Dev)

**AC → test map:**
| AC | Test | RED failure (verified) |
|----|------|------------------------|
| AC1 room-graph e2e | `test_discovered_region_indexes_as_room_graph_sourced_card` | `got []` — no `room_graph` card |
| AC1 idempotency | `test_unchanged_room_graph_location_does_not_rearm_on_resync` | precondition `[]` — no card to settle |
| AC2 materialization e2e | `test_materialized_chapter_location_indexes_as_materialization_sourced_card` | `got []` — no `world_materialization` card |
| AC3 batch | `test_promotion_read_does_not_scale_with_region_count` | `assert 3 == 1` — one read per region |
| AC4 watcher event | `test_read_failure_publishes_a_watcher_event_referencing_the_region` | only `synced` captured — failure swallowed |
| AC4 failed count | `test_read_failure_increments_the_failed_count` | `failed: 0`, `assert 0 >= 1` |
| AC5 wiring | (satisfied by AC1/AC2/AC4 driving `sync_for_turn`) | n/a — e2e seam IS the wiring proof |

**Verification note:** the RED `synced` payloads show `faction_count: 5` (flickering_reach's authored factions flowing through the existing 76-7 seam) with `location_count: 0` — confirming `sync_for_turn` is genuinely wired end-to-end and ONLY the location sources are absent. No collection/import/phantom-DB errors; every failure is a real assertion miss.

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|---|---|---|
| #1 silent exception swallowing | `test_read_failure_publishes_a_watcher_event...` (the per-region read failure must NOT be a silent `except/continue`) | failing |
| #4 logging/observability on error paths | `test_read_failure_increments_the_failed_count` + watcher test (error path surfaces a counted, observable event) | failing |
| #6 test quality | self-checked: every test has ≥1 meaningful value assertion (card presence + real-prose substring + count/call_count), watcher patched **where used** (`dispatch_entity_sync._watcher_publish`), no `assert True`, no truthy-only acceptance of wrong values | pass (own tests) |

**Rules checked:** 3 of 13 lang-review rules are directly applicable to this test-only RED diff (the rest govern production-code shape Dev will write — #2 mutable defaults, #5 path handling, #7 resource leaks, etc.).
**Self-check:** 0 vacuous assertions found in my tests.

**Source isolation:** every test stubs `repository.list_location_promotions` (the factory ships a bare `MagicMock(spec=SaveRepository)` whose default return is non-iterable and would crash the sweep) and keeps the two new sources on DISTINCT regions so each `source` tag is asserted unambiguously (room-graph `glass_flat`, materialization `vault_echo`).

**Handoff:** To Dev (Ponder Stibbons) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed (sidequest-server):**
- `sidequest/server/dispatch/entity_sync.py` — added `_resolve_region_view` (authored-prose resolution via `location_view.get_location_prose`); rewrote `_collect_location_views` to assemble three sources (promotion/room_graph/world_materialization) with first-source-wins dedup, a single batched promotion read, and a `location_read_failed` watcher event + `failed` count on read failure; `sync_for_turn` threads the count into `result.failed`.
- `sidequest/game/repository.py` — widened `SaveRepository.list_location_promotions` protocol with optional `region_ids`.
- `sidequest/game/pg/save_repository.py` — delegate the widened signature.
- `sidequest/game/pg/promotions.py` — implement the batched `region_id = ANY(%s)` read; require exactly one selector (fail loud).
- `tests/server/dispatch/test_entity_sync_location_sources_v2.py` — (TEA) the 6 AC tests, now green.
- `tests/server/dispatch/test_entity_sync_sources_wiring.py` — updated the 76-7 promotion stub to the batched call shape.
- `tests/persistence/test_pg_promotions.py` — 3 new real-DB tests for the batched read + selector validation.

**Tests:** GREEN.
- 6/6 new 76-11 AC tests pass (`test_entity_sync_location_sources_v2.py`).
- 10/10 sibling 76-7 tests pass (no regression).
- 3/3 new real-DB batched-read tests pass; 17/17 PG promotion+repository tests pass.
- **Full server suite: 10350 passed, 343 skipped, 8 failed — all 8 failures are pre-existing baseline debt, independently verified as unrelated to this diff:**
  - `test_message_type_complete_count`: `assert 55 == 54` — develop added a 55th `MessageType`; the count test wasn't bumped (this story adds no message type).
  - `test_narration_clue_discovery_wiring` (×5): `TypeError: '<=' between MagicMock and int` in `progression.py` from a `genre_pack=MagicMock()` fixture — a loader/fixture issue in an untouched subsystem.
  - `test_apply_world_patch::test_active_stakes_path_applies`, `test_61_12_output_format_compaction`: world-patch / narrator-format, untouched.
- Lint: `ruff check` + `ruff format --check` clean on all 7 changed files. (The repo's 11 pre-existing `I001` import-order errors are in untouched files — separate backlog story 76-10.)

**Branch:** `feat/76-11-location-source-coverage-v2` (pushed to origin, 4 commits).

**AC status:** AC1 ✅ (room_graph e2e + idempotency) · AC2 ✅ (world_materialization e2e) · AC3 ✅ (single batched read, real-DB verified) · AC4 ✅ (watcher event + failed count) · AC5 ✅ (all sources reach production via `sync_for_turn`).

**Handoff:** To next phase (verify / review).

## Subagent Results

Reviewer subagents are gated by `workflow.reviewer_subagents` settings — only `preflight` is enabled in this project; the other 8 are disabled, so their domains were assessed by the Reviewer (Granny) directly via manual diff analysis (recorded in the assessment with the corresponding dispatch tags).

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 cosmetic (unused-`exc` nit — actually used in `type(exc).__name__`) | confirmed 0, dismissed 1, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — boundary paths assessed manually (see [EDGE]) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — swallow/fallback paths assessed manually (see [SILENT]) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — test quality assessed manually (see [TEST]) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — docstrings assessed manually (see [DOC]) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — type design assessed manually (see [TYPE]) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — security assessed manually (see [SEC]) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — complexity assessed manually (see [SIMPLE]) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — lang-review rules enumerated manually (see Rule Compliance + [RULE]) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via settings, assessed manually)
**Total findings:** 0 confirmed blocking, 1 dismissed (cosmetic, with rationale), 3 LOW noted as non-blocking observations

### Rule Compliance

Enumerated against `.pennyfarthing/gates/lang-review/python.md` + CLAUDE.md/SOUL.md, every changed type/function:

- **#1 Silent exception swallowing** — `_collect_location_views`'s `except Exception as exc` is NOT silent: it `logger.exception`s, publishes a `location_read_failed` watcher event naming the regions, AND counts `failed += len(regions)`. `# noqa: BLE001` justified (a bad read must not cost the turn — ADR-006). `PgPromotionStore` raises (not swallows) on a bad selector. **COMPLIANT** (this story is the FIX for the 76-7 silent-`continue` finding).
- **#2 Mutable default arguments** — `region_id: str | None = None`, `region_ids: list[str] | None = None` across all 3 signatures — None defaults, not `[]`. **COMPLIANT**.
- **#3 Type annotations at boundaries** — every new/changed public signature is annotated (`_resolve_region_view -> LocationSyncView | None`, `_collect_location_views -> tuple[list[LocationSyncView], int]`, the 3 protocol/impl signatures). **COMPLIANT**.
- **#4 Logging coverage/correctness** — the error path logs via `logger.exception` (inside `except`, correct), `%s` lazy-format, `severity="warning"` on the watcher event (a degraded-but-survivable read = warning, correct level). No PII/secrets. **COMPLIANT**.
- **#6 Test quality** — new tests assert specific values (card presence + real-prose substring + source tag + counts + set equality + `pytest.raises(ValueError)`); watcher patched **where used**; no vacuous assertions; no skips. The 76-7 stub update preserves intent. **COMPLIANT**.
- **#8 Unsafe deserialization / #11 SQL injection** — the batched query uses a **parameterized** `region_id = ANY(%s)` with `targets` bound (psycopg3 list→array adaptation), never an f-string. **COMPLIANT** (CWE-89 safe).
- **#10 Import hygiene** — one new top-level import `get_location_prose`; no star imports; full suite imports clean (no cycle). **COMPLIANT**.
- **SOUL — No Silent Fallbacks / No Stubbing** — exactly-one-selector raises; blank prose → skip not stub; the projector's blank-description guard is preserved. **COMPLIANT**.
- **CLAUDE.md — OTEL Observability** — the dropped-read path emits a GM-panel watcher event; the existing span/synced telemetry carries the merged `failed`/`location_count`. **COMPLIANT**.
- **CLAUDE.md — Verify Wiring / Every suite needs a wiring test** — all three sources reach production via `sync_for_turn` (the per-turn dispatch seam), proven by the e2e AC tests against the real fixture pack. **COMPLIANT**.

### Devil's Advocate

Let me argue this code is broken. **First, the batched `ANY(%s)` ordering.** The single-region query ordered by `promoted_at_turn, entity_id` within one region; the batched query orders globally across regions, and the docstring claims "the batched consumer regroups by region_id." But the consumer (`_collect_location_views`) does NOT regroup — it iterates all rows flat and keys each card by `entity_id`. Is that a bug? No: each promotion row becomes an independent `loc:<entity_id>` card upserted into a store keyed by card id; inter-region row order is irrelevant to the final index. The docstring overstates ("regroups") what is really "iterates" — a doc imprecision, not a correctness bug. **Second, a malicious/huge input:** what if `discovered_regions` holds 10,000 regions? The batched read is now ONE query with a 10k-element array (fine for Postgres `ANY`), but the room_graph loop then calls `_resolve_region_view` 10k times, each doing a dict lookup + `get_location_prose` (pure, no I/O) — O(N) in-memory, no per-item DB hit. Acceptable; far better than the old O(N) DB round-trips. **Third, the failure path:** if the batched read raises, `failed = len(regions)` and ALL promotions drop — but room_graph/materialization prose still index (they don't touch the repo). A confused operator might read `failed: 50` and panic — but the `location_read_failed` watcher event names the regions and the `error` type, so the GM panel disambiguates. **Fourth, a stressed filesystem / partial session:** `_resolve_region_view`'s seven `getattr(..., None)` reads return None at the first missing layer → the region is skipped, never a crash. The one fragility: a *bare* `MagicMock()` genre_pack (not a duck-typed stub) would make every getattr truthy and feed a MagicMock into `get_location_prose` → eventually a projector `ValidationError` caught as `failed`. But this requires `discovered_regions` non-empty AND a MagicMock pack — a combination that exists in NO test and NEVER in production (production always loads a real `GenrePack`). **Fifth, config with unexpected fields:** a region whose `description` is None or whitespace → `get_location_prose` returns it → `if not prose.strip(): return None` → skipped. No stub card. The devil finds nothing blocking — only the docstring imprecision and the documented MagicMock-fragility, both LOW.

## Reviewer Assessment

**Verdict:** APPROVED

This is a clean, disciplined extension of the 76-7 location-sync seam that closes exactly the three Reviewer/Dev follow-ups it was scoped to (the two deferred sources + the perf batch + the observability fix), with no Critical or High findings.

**Data flow traced:** `snapshot.discovered_regions` / `snapshot.world_history` → `_collect_location_views` (batched promotion read + per-region authored-prose resolution via `location_view.get_location_prose`) → `LocationSyncView(source=…)` → `sync_entity_cards` → `EntityStore` (the universal-retrieval index the narrator reads). Safe: authored prose only (No Stubbing), parameterized SQL (no injection), and a read failure degrades to fewer cards + a watcher event rather than a lost turn (ADR-006).

**Pattern observed:** first-source-wins dedup via a `seen_ids` set keyed on the full `loc:<id>` card id — `entity_sync.py:124-131` — mirrors the `covered_ids` cross-type dedup in `sync_entity_cards`. Good, consistent pattern.

**Error handling:** the dropped-read path at `entity_sync.py:141-155` logs, publishes `op="location_read_failed"` with the region list + error type, counts `failed`, and continues — verified loud, not silent.

**Dispatch-tag observations (8 disabled subagents assessed manually by Granny):**
- `[EDGE]` Boundary paths enumerated: empty `discovered_regions` (promotion block guarded by `and regions`), empty `world_history` (loop no-ops), blank region description (`get_location_prose` → `if not prose.strip(): return None`), region absent from cartography (early None), `region_ids=[]` (early `return []`, no degenerate `ANY('{}')`). All handled. **No issue.**
- `[SILENT]` The new `except` is the antithesis of a silent fallback — watcher event + `failed` count + `logger.exception`. This story REMOVES the 76-7 silent `continue`. **VERIFIED loud — `entity_sync.py:141-155`.**
- `[TEST]` 6 AC tests + 3 real-DB batched tests, all asserting specific values; the AC4 failure tests pin both the watcher event (referencing the region) and `synced[0]["failed"] >= 1`; 10 sibling 76-7 tests still pass. No vacuous assertions. **VERIFIED.**
- `[DOC]` `[LOW]` `_collect_location_views`/`PgPromotionStore` docstrings say the batched consumer "regroups by region_id" — it actually iterates flat (correctness unaffected since cards key on `entity_id`). Minor imprecision at `entity_sync.py:111` / `promotions.py:91`. **Non-blocking.**
- `[TYPE]` Signatures correctly annotated; `tuple[list[LocationSyncView], int]` return threaded to the one caller; `region_ids: list[str] | None`. No stringly-typed regressions. **VERIFIED.**
- `[SEC]` Parameterized `ANY(%s)` — no SQL injection (CWE-89 safe); region ids are internal world-authored slugs, not user free-text; no secrets/PII logged. **VERIFIED — `promotions.py:113`.**
- `[SIMPLE]` `[LOW]` The `failed` counter now spans two semantics (projector-rejections + dropped-region reads); acceptable because the `location_read_failed` watcher event disambiguates for the GM panel. The seven-getattr defensive chain in `_resolve_region_view` is justified (duck-typed/partial sessions). No over-engineering. **Non-blocking.**
- `[RULE]` Full lang-review enumeration above — all applicable checks COMPLIANT.

**LOW (non-blocking) — carried as Delivery Findings, not fix-required:**
1. Docstring "regroups by region_id" imprecision (`[DOC]`).
2. Per-room-YAML-mode worlds (`load_room_payload.settlement_description`) are not covered by `_resolve_region_view` (cartography-only) — Dev already logged this as a follow-up Improvement.

**Preflight (Nanny Ogg):** targeted 27/27 GREEN, full suite 10349 passed / 8 failed (all 8 CONFIRMED pre-existing, zero overlap with `entity_sync`/`promotions`/`location_view`/`repository`), ruff check + format clean on all 7 files. The one cosmetic "unused `exc`" note is dismissed — `exc` IS used in `type(exc).__name__`.

**Handoff:** To SM (Captain Carrot) for finish-story.

## Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): `_collect_location_views`/`PgPromotionStore.list_location_promotions` docstrings state the batched consumer "regroups by region_id"; the consumer actually iterates rows flat and keys each card by `entity_id` (correctness is unaffected). Affects `sidequest/server/dispatch/entity_sync.py` + `sidequest/game/pg/promotions.py` (tighten the docstring wording on a future touch). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The `EntitySyncResult.failed` counter now aggregates two failure kinds — projector rejections and dropped-region promotion reads — under one number; the `location_read_failed` watcher event disambiguates for the GM panel, but a future change could split a dedicated `location_read_failed` count if forensics need it. Affects `sidequest/server/dispatch/entity_sync.py::sync_for_turn`. *Found by Reviewer during code review.*

### Dev (implementation)
- **Improvement** (non-blocking): `_resolve_region_view` resolves authored prose from `world.cartography.regions` only. A world in per-room-YAML mode (`load_room_payload`'s `settlement_description`, the Path-1 source `map_emit.py` uses) is NOT covered — those worlds' room-graph locations won't index until a follow-up adds that resolution branch. Affects `sidequest/server/dispatch/entity_sync.py::_resolve_region_view` (add a per-room-YAML prose branch mirroring `map_emit.py` Path 1). *Found by Dev during implementation.*
- **Improvement** (non-blocking): On a batched promotion-read failure the whole batch is lost, so `failed` is counted as `len(regions)` and ALL regions' promotions drop for the turn (room_graph/materialization prose still index — graceful degradation). True per-region isolation would require N queries (reintroducing the O(N) cost AC3 removed); the batch-or-nothing trade-off is intentional. If finer-grained recovery is ever needed, a chunked read (e.g. fall back to per-region only on the failing batch) is the path. Affects `sidequest/server/dispatch/entity_sync.py::_collect_location_views`. *Found by Dev during implementation.*

### TEA (test design)
- **Conflict** (non-blocking): The location `source` tag values are specified two ways — context-story-76-11 AC1/AC2 say `"room"` / `"materialization"`, but the live projector docstring (`entity_card.py::project_location_card`, written in 76-7) names `"room_graph"` / `"world_materialization"` (matching the shipped `"promotion"` style). Tests pin the code's documented contract (`"room_graph"` / `"world_materialization"`). Affects `sidequest/game/entity_card.py::project_location_card` (docstring) + the new adapters in `sidequest/server/dispatch/entity_sync.py::_collect_location_views` (must emit these exact tags) — Dev/Reviewer pick one and keep test + docstring in lockstep. *Found by TEA during test design.*
- **Improvement** (non-blocking): AC3 (batch) and AC4 (per-region failure observability) are in mild tension — fully batching the promotion read into one call removes the "per-region" failure granularity. The RED tests resolve this by seeding a SINGLE discovered region for the AC4 cases (batched == per-region when N=1), so the failure cleanly references one region. Dev should ensure a batched-read failure still (a) isolates — does not crash the sweep, the `synced` event still fires; (b) counts — increments `result.failed`; (c) is observable — emits a region-referencing watcher event. Affects `sidequest/server/dispatch/entity_sync.py::_collect_location_views` + `sync_for_turn`. *Found by TEA during test design.*
- **Question** (non-blocking): `_collect_location_views` currently returns only `list[LocationSyncView]`, but AC4 requires a per-region read failure to increment `result.failed` — and `result` is created downstream in `sync_entity_cards`, AFTER collection. Dev must thread collection-time failures into the result (e.g. return a `(views, failed_count)` pair, or publish the failure event from inside collection and merge the count before the `synced` publish). The tests pin the observable (`synced[0]["failed"] >= 1` + a failure event), not the threading mechanism. Affects `sidequest/server/dispatch/entity_sync.py`. *Found by TEA during test design.*

## Design Deviations

### TEA (test design)
- **Pinned source tags to the projector's documented contract (`"room_graph"` / `"world_materialization"`), NOT the context's shorthand (`"room"` / `"materialization"`)**
  - Spec source: context-story-76-11.md, AC1/AC2 ("`source="room"`" / "`source="materialization"`")
  - Spec text: AC1 "at least one card has `source="room"`"; AC2 "at least one card has `source="materialization"`"
  - Implementation: Tests assert `metadata["source"] == "room_graph"` and `== "world_materialization"`. The live projector `entity_card.py::project_location_card` docstring (written in 76-7) already names the three intended tags as `"room_graph"` / `"world_materialization"` / `"promotion"`, and the shipped promotion source uses the literal `"promotion"`. The context's `"room"` / `"materialization"` is a casual shorthand that conflicts with the code's own stated contract.
  - Rationale: Align provenance tags with the projector's documented intent + the live `"promotion"` tag for consistency and least churn; a contested naming detail should be surfaced loudly (a failing pin), not papered over. Dev: if you deliberately choose the shorthand `"room"`/`"materialization"`, update the two assertions and the projector docstring together — but the firmer signal is the existing code.
  - Severity: minor
  - Forward impact: Dev must emit exactly these two tag strings (or change test + projector docstring in lockstep). Logged as a Delivery Finding (Conflict) so Reviewer sees it.
- **AC2 materialization seed = `snapshot.world_history` (a located `HistoryChapter`); the precise source field is Dev's to confirm (ADR-118 §D3)**
  - Spec source: context-story-76-11.md, AC2 + Technical Approach Thread 1.2 ("Extract region context")
  - Spec text: "Seed a materialization that emits a location context (region, scene, etc.)"
  - Implementation: The behavioral test seeds `sd.snapshot.world_history = [HistoryChapter(id="early", location="vault_echo")]` — `world_history` is written ONLY by `world_materialization.materialize_world`, so it is the materialization-exclusive signal (unlike `character_locations`, which normal movement also writes). The contract pinned is firm: a materialization-originated region's authored prose → a `source="world_materialization"` card with `location_count >= 1`. The exact snapshot field the adapter reads is a Dev design decision per ADR-118 §D3 ("per-source adaptation belongs to the consumer").
  - Rationale: Mirrors 76-7 TEA's precedent — drive the stable `sync_for_turn` seam, pin behavior + provenance, leave the inner adapter shape to Dev. If Dev's materialization adapter reads a different field, adjust the AC2 seed to populate it; the assertions (source tag + real prose + count) stay.
  - Severity: minor
  - Forward impact: Dev may re-point the AC2 seed field; the behavioral contract is unchanged.
- **AC3 batch pin is a call-count spy on `repository.list_location_promotions`, argument-shape-agnostic**
  - Spec source: context-story-76-11.md, AC3 ("`list_location_promotions.call_count == 1`")
  - Spec text: "Verify `list_location_promotions` is called **once** with a batched input (not N separate calls)"
  - Implementation: The spy asserts `call_count == 1` for 3 discovered regions and does NOT constrain the call arguments, so Dev may switch the signature from per-region `region_id=` to a batched `region_ids=[...]` freely. NOTE for Dev: AC3 constrains the TOTAL number of promotion reads in the collection path — if the room-graph/materialization adapters resolve manifests via `location_view.get_location_manifest` (which itself calls `list_location_promotions` per region), those reads also count. Use `get_location_prose` (no promotions read) for prose, and batch the promotion SOURCE's read.
  - Rationale: Pin the perf contract (no O(N) round-trips) without dictating the batched method's argument shape.
  - Severity: minor
  - Forward impact: If Dev introduces a differently-named batched method, the spy target updates; the "one read for N regions" contract holds.

### Dev (implementation)
- **Adopted TEA's resolution of the source-tag Conflict: tags are `"room_graph"` / `"world_materialization"`**
  - Spec source: TEA Delivery Finding (Conflict) + context-story-76-11.md AC1/AC2
  - Spec text: AC1 "`source="room"`" / AC2 "`source="materialization"`" vs. the projector docstring's `"room_graph"` / `"world_materialization"`
  - Implementation: `_resolve_region_view` emits `source="room_graph"` and `source="world_materialization"`, matching the live `project_location_card` docstring + the shipped `"promotion"` style (and TEA's test pins). The context shorthand is NOT used.
  - Rationale: Consistency with the existing code contract; the projector already documents these exact tags as the intended values. One source of truth.
  - Severity: minor
  - Forward impact: none — projector docstring, adapters, and tests are now all in lockstep on `room_graph` / `world_materialization`.
- **Widened `list_location_promotions` to a batched `region_ids=` selector (one `region_id = ANY(%s)` query) across the protocol + both impls**
  - Spec source: context-story-76-11.md AC3 (Thread 2 — batch the per-region read)
  - Spec text: "Read all promotions once: `list_location_promotions(discovered_regions_list)` (if available) OR manually batch."
  - Implementation: Added an optional `region_ids: list[str] | None` param to `SaveRepository.list_location_promotions` (protocol), `PgSaveRepository`, and `PgPromotionStore`. Both the single (`region_id=`) and batched (`region_ids=`) paths route through one `region_id = ANY(%s)` SQL shape; exactly one selector is required (raises `ValueError` otherwise — No Silent Fallbacks). Existing single-region callers (`location_view`, `location_resolver`) are unchanged.
  - Rationale: AC3's spy is on `list_location_promotions` itself, so the batched read must go *through* that method (not a new one). `ANY(%s)` unifies both paths with no behavior change for the single-region case.
  - Severity: minor
  - Forward impact: additive (defaults preserve the old single-region call); the batched path is covered by 3 new real-DB tests in `tests/persistence/test_pg_promotions.py`.
- **`_collect_location_views` now returns `(views, failed_count)`; `sync_for_turn` adds the count to `result.failed`**
  - Spec source: TEA Delivery Finding (Question) + AC4
  - Spec text: "Dev must thread collection-time failures into the result … the tests pin the observable (`synced[0]["failed"] >= 1` + a failure event)"
  - Implementation: A failed batched promotion read is caught inside `_collect_location_views`, which (a) publishes a `op="location_read_failed"` watcher event naming the dropped `regions`, (b) returns `failed = len(regions)`. `sync_for_turn` adds that to `result.failed` before the span/synced publish, so the GM panel sees the under-report and `outcome` degrades to `"partial"`.
  - Rationale: `result` is built in `sync_entity_cards` after collection; the tuple is the least-coupled way to merge the collection-time failure into the published count.
  - Severity: minor
  - Forward impact: `_collect_location_views` is a private dispatch helper with one caller (`sync_for_turn`, updated); no external consumers.
- **Source precedence on a shared `loc:<id>` card id is first-source-wins: promotion → room_graph → world_materialization**
  - Spec source: context-story-76-11.md (Technical Approach — "Dev picks the source priority/merge order")
  - Spec text: "Dev picks the source priority/merge order; the wiring remains clean."
  - Implementation: A local `seen_ids` set dedups by `loc:<location_id>` so a region surfaced by more than one source is indexed once, from the first source in promotion→room_graph→materialization order.
  - Rationale: Promotions are the most specific (authored Yes-And canon); a discovered region beats a merely-materialized backstory region. Mirrors the `covered_ids` dedup `sync_entity_cards` already applies across types.
  - Severity: minor
  - Forward impact: none — the AC tests isolate sources on distinct regions, so precedence is unobservable to them; it only governs the production multi-source overlap case.
- **Updated the 76-7 `TestPromotionLocationFlowsEndToEnd` stub to accept the batched `region_ids=` call**
  - Spec source: 76-7 `tests/server/dispatch/test_entity_sync_sources_wiring.py` (sibling test) + AC3 API change
  - Spec text: the stub `lambda *, region_id: …` matched the old per-region call
  - Implementation: Widened the lambda to `lambda *, region_id=None, region_ids=None: [row] if region_id == "rusted_junction" or (region_ids and "rusted_junction" in region_ids) else []` so it answers both call shapes; the test's intent (a promoted location flows to a card) is unchanged and still passes.
  - Rationale: The production promotion read genuinely changed from per-region to batched; the monkeypatch must reflect the new call. Not a weakening — both shapes return the same row.
  - Severity: minor
  - Forward impact: none — purely a stub adapting to the new (additive) API.

### Reviewer (audit)
- **TEA-1 (source tags pinned to `room_graph`/`world_materialization`, not the context shorthand)** → ✓ ACCEPTED by Reviewer: the pin matches the live `project_location_card` docstring (the immediate predecessor's documented contract) and the shipped `"promotion"` style; pinning the firmer source and surfacing the conflict as a failing test (rather than silently choosing) is correct. Dev adopted it — projector docstring, adapters, and tests are now in lockstep. Verified `entity_card.py:253` names these exact tags.
- **TEA-2 (AC2 materialization seed = `snapshot.world_history`; field choice left to Dev)** → ✓ ACCEPTED by Reviewer: `world_history` is written only by `materialize_world` (verified `world_materialization.py:251,762`), so it is the materialization-exclusive signal — the right seam. Dev read exactly that field; no re-pointing needed.
- **TEA-3 (AC3 batch pin = argument-shape-agnostic call-count spy)** → ✓ ACCEPTED by Reviewer: pins the perf contract (one read for N regions) without dictating the batched signature; Dev satisfied it via `region_ids=` and the spy correctly counted 1. Real-DB batched coverage was additionally added (`test_pg_promotions.py`), closing the mock-only gap.
- **Dev-1 (adopted `room_graph`/`world_materialization` tags)** → ✓ ACCEPTED by Reviewer: resolves the TEA Conflict in favor of the code's own documented contract. One source of truth.
- **Dev-2 (widened `list_location_promotions` with batched `region_ids=` ANY query)** → ✓ ACCEPTED by Reviewer: additive (existing `region_id=` callers in `location_view.py:56` / `location_resolver.py:242` unchanged), exactly-one-selector enforced with a loud `ValueError` (No Silent Fallbacks), and the batched path is verified against real Postgres (3 new tests). The protocol + both impls were updated in lockstep — no half-wired interface.
- **Dev-3 (`_collect_location_views` returns `(views, failed)`; `sync_for_turn` adds to `result.failed`)** → ✓ ACCEPTED by Reviewer: the least-coupled way to thread a collection-time failure into the published count, satisfying the TEA Question finding. Private helper, single caller (`sync_for_turn`) updated — verified no other callers via grep.
- **Dev-4 (source precedence: promotion → room_graph → world_materialization, first-source-wins)** → ✓ ACCEPTED by Reviewer: a sound priority (authored Yes-And canon beats a discovered region beats a merely-materialized backstory region), mirrors the `covered_ids` cross-type dedup `sync_entity_cards` already applies. The `seen_ids` set is keyed on the full `loc:<id>` card id, so distinct entity/region ids never falsely collide.
- **Dev-5 (updated the 76-7 `TestPromotionLocationFlowsEndToEnd` stub to the batched shape)** → ✓ ACCEPTED by Reviewer: a necessary, intent-preserving stub update (the production call signature genuinely changed); the lambda answers both shapes and the test still asserts the same behavior. Not a weakening.

No undocumented deviations found — the diff matches what TEA and Dev logged.

---

**Phase Notes:**
- Jira integration is disabled for this personal project; `JIRA_KEY` is null/empty.
- No Jira steps (create epic, claim) are executed.
- Workflow type is **phased** (TDD has setup → red → green → review → finish agents).
- Next phase: **RED** (TEA writes failing tests).