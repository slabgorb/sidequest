---
story_id: "45-12"
jira_key: "none"
epic: "45"
workflow: "tdd"
---

# Story 45-12: Chargen double-init dedup of starting kit

## Story Details

- **ID:** 45-12
- **Jira Key:** None (manual sprint story)
- **Epic:** 45 — Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup
- **Workflow:** tdd
- **Type:** Bug
- **Priority:** P1
- **Points:** 2
- **Stack Parent:** none (independent)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-29T00:46:03Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T21:00:00Z | 2026-04-29T00:10:43Z | 3h 10m |
| red | 2026-04-29T00:10:43Z | 2026-04-29T00:20:40Z | 9m 57s |
| green | 2026-04-29T00:20:40Z | 2026-04-29T00:29:41Z | 9m 1s |
| spec-check | 2026-04-29T00:29:41Z | 2026-04-29T00:32:05Z | 2m 24s |
| verify | 2026-04-29T00:32:05Z | 2026-04-29T00:37:18Z | 5m 13s |
| review | 2026-04-29T00:37:18Z | 2026-04-29T00:45:07Z | 7m 49s |
| spec-reconcile | 2026-04-29T00:45:07Z | 2026-04-29T00:46:03Z | 56s |
| finish | 2026-04-29T00:46:03Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Improvement** (non-blocking): Pack-side intra-list duplication is a broader bug surface
  the dedup keys catch as a side effect.
  Affects `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml:294-305`
  (`starting_equipment[Delver]` lists 3 torches and 2 rations). The dedup span will
  fire on every chargen-confirm in production until packs are swept for intra-list
  duplicates. Filed as observation, not blocking 45-12.
  *Found by TEA during test design.*
- **Improvement** (non-blocking): Story Out-of-Scope explicitly defers multi-quantity
  stack consolidation; the Blutka 24-item evidence (6 torches, 4 rations, etc.) suggests
  the builder also emits intra-batch quantity duplicates as separate items. The 45-12
  dedup keys collapse these by id, but a future "stack consolidation" story would clean
  up the 6→1 quantity reduction case.
  Affects `sidequest-server/sidequest/game/builder.py:1407-1422`
  (equipment_tables emission path).
  *Found by TEA during test design.*

### Dev (implementation)

- **Gap** (non-blocking): Pre-existing test isolation bug surfaces 3 failures unrelated
  to this story — `test_status_apply.py::test_status_change_appends_to_named_actor`,
  `test_status_clear.py::test_wiring_narration_apply_clear_and_add_in_same_turn`,
  `test_stale_slot_reinit_wire.py::test_post_chargen_turn_manager_is_fresh_after_stale_slot_reinit`
  all fail with `sqlite3.ProgrammingError: Cannot operate on a closed database`
  inside `sidequest/telemetry/watcher_hub.py:191` (`_maybe_persist_encounter_row`).
  Reproduces on `main` without my changes (verified via `git stash`); the watcher
  hub event store from a prior test is being closed before later tests publish
  state-transition events. Affects `sidequest-server/sidequest/telemetry/watcher_hub.py:185-200`
  (event-store lifetime not coupled to fixture scope).
  *Found by Dev during green phase.*
- **Improvement** (non-blocking): Three pre-existing lint findings in files touched
  by this story were left in place — they precede 45-12 and are out of scope:
  `websocket_session_handler.py:295` UP037 (quotes in type annotation),
  `websocket_session_handler.py:385` SIM105 (try/except/pass instead of contextlib.suppress),
  `tests/server/test_chargen_persist_and_play.py:43` E402 (module-level import after
  code, already carries `# noqa: E402` but ruff flags it anyway). Each is a 1-2 line
  fix worth boy-scouting in a follow-up sweep.
  *Found by Dev during green phase.*

### TEA (test verification)

- **Improvement** (non-blocking): SpanRoute extractors for sibling-shape spans
  (`chargen.archetype_gate_*`, `chargen.starting_kit_dedup_*`, `scrapbook.coverage_*`)
  share an identical `(span.attributes or {}).get(key, default)` lambda boilerplate.
  A factory helper (e.g. `make_state_transition_route(component, fields)`) would
  consolidate all three pairs and reduce extractor LOC by ~60%. Out of scope for
  45-12 (touches 8+ unrelated span definitions); flag for an architecture-led
  refactor.
  Affects `sidequest-server/sidequest/telemetry/spans/{chargen,scrapbook}.py`.
  *Found by TEA during test verification.*
- **Improvement** (non-blocking): Test class docstrings in `test_chargen_loadout.py`
  and `test_chargen_persist_and_play.py` reference "AC1–AC4" / "AC6 wire-test"
  without cross-referencing the test class housing AC5. Cosmetic; readers
  navigating the AC list have to scan three classes across two files. A
  module-level docstring or single AC index comment would fix.
  *Found by TEA during test verification.*

### Reviewer (code review)

- **Improvement** (non-blocking): Wire-test `assert len(evaluated) >= 1` at
  `tests/server/test_chargen_persist_and_play.py:1252` is under-constrained.
  Tightening to `== 1` would catch a hypothetical double-emission regression.
  Mitigated by sibling unit tests (`test_evaluated_span_fires_on_disjoint_path`,
  `test_three_chargen_runs_evaluated_three_fired_two`) that pin exact-count
  cardinality. Affects `sidequest-server/tests/server/test_chargen_persist_and_play.py`.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `_builder_hint_dict` docstring at
  `tests/server/test_chargen_loadout.py:401` references `builder.py:1407–1422`;
  comment-analyzer reports actual `equipment_tables` stub emission lives at
  `builder.py:1328–1344`. The fixture body is correct; only the line-number
  annotation is stale. Not verified line-by-line by Reviewer to avoid scope creep.
  Affects `sidequest-server/tests/server/test_chargen_loadout.py:401`.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `apply_starting_loadout` docstring prescribes
  `sd.snapshot.genre_slug` while the same handler uses `sd.genre_slug` directly
  in 10+ sibling call sites. Either align the call site or document why the
  snapshot path is preferred at chargen-confirm.
  Affects `sidequest-server/sidequest/server/dispatch/chargen_loadout.py:152`.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Block comment at `spans/chargen.py:80-86` references
  `CharacterBuilder.equipment_tables` as if public; the field is private
  (`_equipment_tables`, set via `with_equipment_tables()`). Cosmetic precision.
  Affects `sidequest-server/sidequest/telemetry/spans/chargen.py`.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Four unit tests in `test_chargen_loadout.py`
  discard the `(items_added, gold_added)` return tuple. Capturing and asserting
  it would close a small contract-coverage gap. Tests affected: lines 504, 537,
  637, 696 (return values) and 696 (`items_upgraded == 0`).
  Affects `sidequest-server/tests/server/test_chargen_loadout.py`.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Wire-test `torch_count <= 3` at
  `test_chargen_persist_and_play.py:334` has only an upper bound; an over-dedup
  regression suppressing builder torches would silently pass. Adding `>= 1`
  lower bound (or asserting the persisted inventory contains a torch from the
  builder walk) would close the over-dedup blind spot.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Wire-test
  `test_chargen_confirm_persists_deduped_inventory` does not assert the
  `chargen.starting_kit_dedup_fired` span fires, even though the grimvault
  pack always has overlap (3× torch in starting_equipment). The `fired`-span
  contract is unverified at the wire level.
  *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No deviations at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- No deviations from spec. All six ACs covered by discrete tests:
  AC1 → `test_partial_overlap_yields_union_blutka_regression`,
  AC2 → `test_disjoint_case_appends_all`,
  AC3 → `test_full_overlap_skips_all`,
  AC4 → `test_name_fallback_collision_id_differs` (+ case-insensitive sibling),
  AC5 → `TestStartingKitDedupSpans` class (8 tests including
  `test_three_chargen_runs_evaluated_three_fired_two`) +
  `TestStartingKitDedupSpanRouting` class (4 tests pinning SPAN_ROUTES),
  AC6 → `test_chargen_confirm_persists_deduped_inventory` +
  `test_chargen_confirm_emits_starting_kit_dedup_evaluated_span`.

### Dev (implementation)

- **Two test fixtures relaxed to match story Out-of-Scope.** The TEA RED
  tests in `test_partial_overlap_yields_union_blutka_regression` and
  `test_chargen_confirm_persists_deduped_inventory` originally asserted
  global id/name uniqueness across the final inventory. The story's
  Out-of-Scope explicitly carves out builder-side intra-list duplicates:
  *"Multi-quantity dedup (e.g., consolidating 6 torches into 1)... If
  the builder produced 6 torches as separate items, the dedup will
  collapse the catalogue's 1 torch against any of them — net result is
  the catalogue copy is dropped. A separate follow-up could
  quantity-merge sibling items, but that's a different shape of fix."*
  - Spec source: sprint/context/context-story-45-12.md → "Out of scope" §,
    paragraph 3.
  - Spec text: "If the builder produced 6 torches as separate items, the
    dedup will collapse the catalogue's 1 torch against any of them —
    net result is the catalogue copy is dropped."
  - Implementation: relaxed `test_partial_overlap_yields_union_blutka_regression`
    to assert per-id post-state counts (builder torch×3 stays; catalogue
    torch is skipped) and `len(items) == 14` (11 builder + 3 disjoint
    catalogue) instead of `len(items) == 13` and global id-uniqueness.
    Relaxed `test_chargen_confirm_persists_deduped_inventory` to assert
    that catalogue ids do not exceed their pack-list quantity AND that
    in-memory `final_count` matches persisted item count (the actual
    half-wired regression invariant the AC describes).
  - Rationale: TEA's stricter assertion would fail on real production
    pack content even with a correct (story-scope) implementation, since
    `caverns_and_claudes/grimvault` has 3 torch entries in
    `starting_equipment[Delver]` itself and the builder also emits
    intra-batch dupes from `equipment_tables`. The relaxed tests still
    pin every behavior the story scope asserts: catalogue overlap is
    skipped, disjoint catalogue ids land, dedup spans fire correctly,
    persisted state matches in-memory state.
  - Severity: minor — no AC was dropped; test assertions were narrowed
    to story scope.
  - Forward impact: when the follow-up multi-quantity stack-consolidation
    story lands, the relaxed assertions can be tightened back; the
    intent (no broader dedup) is documented in the test docstrings.
  → ✓ ACCEPTED by Reviewer: agrees with Dev reasoning. The story Out-of-Scope
    §3 is unambiguous — builder-side intra-list duplicates are explicitly not
    in scope. TEA's original assertion was a coverage over-reach; Dev's
    relaxation reconciles the test with the spec without dropping any AC.
    Architect's spec-check independently confirmed the same conclusion.

### Reviewer (audit)

- **TEA test design:** No deviations to flag. All 6 ACs have discrete test
  coverage; `TestStartingKitDedupSpanRouting` adds extract-shape regression
  locks beyond the AC list, which is positive over-coverage, not drift.
- **Dev implementation:** No undocumented deviations spotted. The simplify-pass
  refactor (commit `41cd715`) consolidating the two evaluated-span emit blocks
  into a single emission point is a TEA verify decision, not a spec deviation
  — behavior is unchanged (verified by 37/37 GREEN tests post-refactor).
- **Test relaxations** logged by Dev → ACCEPTED (see above).

### Architect (reconcile)

Final deviation manifest for the auditor's read. All in-flight entries
reviewed against `sprint/context/context-story-45-12.md`,
`sprint/context/context-epic-45.md`, `docs/plans/phase-2-chargen-port.md`
(ADR-085 IOU), and the chargen-confirm code path.

**Verification of existing entries:**

- **Dev — Two test fixtures relaxed to match story Out-of-Scope** —
  Spec source path `sprint/context/context-story-45-12.md` exists and
  resolves; "Out of scope" §, ¶3 quote ("If the builder produced 6
  torches as separate items...") matches the file at lines 211–215
  (verified during spec-check). Implementation description matches
  the actual test diff (`test_chargen_loadout.py:454, 504`,
  `test_chargen_persist_and_play.py:268`). Forward-impact is
  accurate — when the stack-consolidation follow-up lands, the
  relaxed assertions tighten naturally. Reviewer audit ACCEPTED.
  No correction needed.

- **TEA — "No deviations from spec"** — Verified. All 6 ACs map to
  discrete tests in the diff; `TestStartingKitDedupSpanRouting` adds
  routing-completeness coverage beyond the AC list, which is positive
  over-coverage. No correction needed.

**Missed deviations (added here):**

- No additional deviations found. The simplify-pass refactor
  (commit `41cd715`) consolidating the two evaluated-span emission
  blocks into a single emission point is a verify-phase quality
  improvement, not a spec deviation — the spec specifies span
  emission semantics (fires-on-every-call, fires-only-on-overlap),
  not the syntactic structure of the emit blocks. Behavior preserved
  per 37/37 GREEN test suite. Per `pennyfarthing-dist/guides/deviation-format.md`
  rubric: "deviations are spec → code mismatches"; refactors that
  preserve spec-described behavior are not deviations.

- The wire-test `>= 1` cardinality finding raised by Reviewer is a
  test-quality observation, not a spec deviation. The spec (AC5)
  requires "fires on every chargen-confirm" — the test verifies
  fires (≥1) but doesn't pin exactly-once. The spec did not specify
  exactly-once cardinality at the wire-test level, so the looser
  assertion is consistent with spec, just under-specifying a
  related invariant. Filed as upstream improvement under Reviewer
  Delivery Findings, not as a spec deviation.

**AC deferral table:** No ACs were deferred during this story. All 6
ACs reached DONE status with passing tests and no DESCOPED entries.
This step is therefore a no-op for spec-reconcile.

**Reconcile verdict:** Deviation manifest complete and auditable from
this session file alone. The boss can read 45-12 from setup → finish
without external lookups.

## Story Context Summary

**Bug evidence (Playtest 3, 2026-04-19, Blutka save):** Starting kit shipped 24 items (6 torches, 4 rations, 2 waterskins, 2 chalk, 2 ten-foot poles) where the catalogue specifies 13. The 24 breaks down as:
- 11 items in stub form (`"Starting equipment (slot): X"`) from `CharacterBuilder` emitting hints via `equipment_tables`
- 13 items in canonical catalogue form (rich descriptions, real categories) from `apply_starting_loadout()` emitting `starting_equipment[class]`

Both batches appended to `character.core.inventory.items` without dedup — this is the **canonical write-back-symmetry failure** of Epic 45.

### Technical Approach

**Option selected:** Identity-aware append (dedup at the seam). Do not refactor the builder or designate a single source of truth — that's a follow-up larger story.

The fix lives at **`apply_starting_loadout()`** in `sidequest/server/dispatch/chargen_loadout.py:119–184`. Current flow:
1. `_upgrade_hint_items_from_catalog()` upgrades builder-hint dicts in-place (preserving slot index).
2. Unconditionally appends the full `starting_equipment[class]` list without checking for overlap.

New flow:
1. Same upgrade pass (mutate builder hints in-place).
2. Build a set of existing ids and names already in the inventory.
3. For each id in `starting_equipment[class]`, skip if id (case-insensitive) or name (case-insensitive) already present.
4. Track skipped ids for OTEL telemetry.

**Dedup keys:** `id` (case-insensitive) + `name` (case-insensitive) fallback.

**OTEL spans (load-bearing for GM panel observability):**
- `chargen.starting_kit_dedup_evaluated` — fires on every call, attributes: `class_name`, `pre_dedup_count`, `equipment_ids_count`, `skipped_count`, `items_added`, `items_upgraded`, `final_count`, `genre`, `world`, `player_id`.
- `chargen.starting_kit_dedup_fired` — fires only when `skipped_count > 0`, same attributes + `skipped_ids` list.

### Acceptance Criteria

1. **Overlap between `equipment_tables` rolls and `starting_equipment[class]` is deduplicated; final inventory reflects the union, not the sum.**
2. **Pure-disjoint case behaves identically pre- and post-fix.**
3. **Pure-overlap case skips everything in the second batch.**
4. **Name-fallback collision detection (id differs, name matches).**
5. **OTEL `chargen.starting_kit_dedup_evaluated` fires on every chargen-confirm; `chargen.starting_kit_dedup_fired` fires only on overlap. SPAN_ROUTES registration verified.**
6. **Wire-test: end-to-end chargen confirms produce a deduplicated inventory and persist the deduped result.**

### Test Files

- **Extended:** `tests/server/test_chargen_loadout.py` — 18 new tests across 3 classes.
- **Extended:** `tests/server/test_chargen_persist_and_play.py` — 2 new wire-tests.

### Out of Scope

- The larger refactor that designates one extractor as authoritative.
- Changing the builder's item-hint emission.
- Multi-quantity dedup (e.g., consolidating 6 torches into 1).
- Migrating existing saves.
- UI changes.

### Relates

- Epic 45 theme §4 (write-back-symmetry failures).
- ADR-085 (port-drift) — chargen-port IOU explicitly noted this overlap as deferred.
- Story 37-29, 37-39.

## Sm Assessment

**Story routed for TDD red phase. Setup complete and gates clear.**

- **Scope:** 2pt P1 bug, single repo (server). Localized fix at `apply_starting_loadout()` seam. No cross-repo coordination.
- **Workflow:** TDD is correct — Blutka regression provides concrete failing-state evidence (24 items vs. 13 expected), and the AC list is test-shaped.
- **Risk surface:** Low. Identity-aware dedup at one function. No data migration, no UI, no multiplayer touch points.
- **Branch:** `feat/45-12-chargen-double-init-dedup` ready in sidequest-server.

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD-natural fix with concrete bug evidence; six ACs map to discrete test cases.

**Test Files:**
- `sidequest-server/tests/server/test_chargen_loadout.py` — 18 new tests in 3 classes (TestStartingKitDedup, TestStartingKitDedupSpans, TestStartingKitDedupSpanRouting).
- `sidequest-server/tests/server/test_chargen_persist_and_play.py` — 2 new wire-tests.

**Tests Written:** 20 tests covering 6 ACs + telemetry registration discipline.
**Status:** RED — 18 fail with expected signatures, 13 pre-existing pass, 0 collateral damage.

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (union, not sum) | `test_partial_overlap_yields_union_blutka_regression` | failing |
| AC2 (pure-disjoint) | `test_disjoint_case_appends_all` | failing |
| AC3 (pure-overlap) | `test_full_overlap_skips_all` | failing |
| AC4 (name-fallback collision) | `test_name_fallback_collision_id_differs`, `test_name_dedup_is_case_insensitive` | failing |
| AC5 (OTEL spans) | `TestStartingKitDedupSpans` (8 tests) + `TestStartingKitDedupSpanRouting` (4 tests, including extract-shape lock) | failing (ImportError on SPAN_* constants is the canonical RED signature) |
| AC6 (wire-test, persist deduped) | `test_chargen_confirm_persists_deduped_inventory`, `test_chargen_confirm_emits_starting_kit_dedup_evaluated_span` | failing |

### Rule Coverage (python.md lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 type annotations at boundaries | implicit — Dev's helper signature change must keep return type and `*` kwarg style | (enforced by gate in green phase) |
| #4 logging coverage AND correctness | `apply_starting_loadout` already logs at info-level on success; new spans cover the negative-confirmation path explicitly | covered by AC5 |
| #6 test quality (no vacuous assertions) | All 20 new tests assert specific values, not truthy/none — `_spans_named()` returns `list`, `len() ==` is the assertion shape | self-checked |
| Routing completeness lint | `test_routing_completeness_lint_still_passes` (meta-test) — adding SPAN_* without registration trips the lint | covered |
| OTEL Observability Principle (CLAUDE.md, repeated as "load-bearing") | Both negative-confirmation tests (`test_evaluated_span_fires_on_disjoint_path`, `test_evaluated_span_fires_when_inventory_config_is_none`) + the no-fire-on-disjoint negative case + the wire-test span emission assertion | failing as expected |

**Rules checked:** 5 of 13 lang-review rules are pertinent to this story (it's a behavioral change, not a security/import/path/async story). Remaining rules (1, 2, 5, 7, 8, 9, 10, 11, 12, 13) are non-applicable.

**Self-check:** No vacuous assertions. Every test asserts specific values (counts, attribute keys, list contents, span fire counts). The `TestStartingKitDedupSpanRouting.test_*_span_registered_in_routes` tests construct synthetic spans and assert the route's `extract()` returns the correct keys — this pins the SpanRoute *contract* at GM-panel render time, not just the route's existence.

### Witness Examples (for Dev)

- `test_partial_overlap_yields_union_blutka_regression` — fails with assertion that `len(items) < 19` (current code path produces 19 from 11 builder + 8 catalogue with no dedup). Post-fix: 8 items (5 unique builder + 3 disjoint catalogue).
- `test_intra_batch_dedup_collapses_pack_duplicates` — fails because current code path produces `["torch", "torch", "torch", "rations_day", "rations_day", "waterskin"]` (the literal grimvault `starting_equipment[Delver]` shape).
- `test_evaluated_span_fires_on_disjoint_path` — fails because no span emitted; current helper has no tracer call.
- `test_chargen_confirm_persists_deduped_inventory` — fails on real grimvault content with witness `['dagger_iron', 'shield_wood', 'torch', 'torch', 'torch', 'rations_day', 'rations_day', ...]`.

### Implementation Hints for Dev (Inigo Montoya)

The failing tests give a complete spec. The shape the dev should match:

1. **Helper signature expansion:** `apply_starting_loadout(character, inventory_config, *, genre="", world="", player_id="")`. Backwards-compat (kwarg-only with defaults) — existing callers and tests don't break.
2. **SPAN_* constants:** Add to `sidequest/telemetry/spans/chargen.py`, sibling-shape with `SPAN_CHARGEN_ARCHETYPE_GATE_*`. Register both in `SPAN_ROUTES` with `event_type="state_transition"`, `component="character_creation"`.
3. **Wire site:** `websocket_session_handler.py:879` — pass `genre=sd.snapshot.genre_slug, world=sd.snapshot.world_slug, player_id=...` from the session context.
4. **Span emission:** Use `tracer.start_as_current_span(SPAN_X)` pattern (sibling-shape with archetype-gate spans). Set attributes on the span before exit. The evaluated span MUST fire on every call including `inventory_config is None` and `equipment_key is None`.
5. **Reuse, don't reinvent:** `_item_dict_from_catalog` and `_item_dict_minimal` stay as canonical shapes. Dedup wraps the append, doesn't replace the dict-build.

### Test Run Witness

```
=== 17 passed, 18 failed (RED), 0 skipped — 0.56s ===

Failure breakdown:
  TestStartingKitDedup           : 5 failures (helper not implemented)
  TestStartingKitDedupSpans      : 8 failures (spans not emitted)
  TestStartingKitDedupSpanRouting: 4 failures (ImportError on SPAN_* constants)
  TestChargenPersistAndPlay      : 2 failures (wire path not connected)

Pre-existing (collateral damage check):
  test_chargen_loadout.py        : 8/8 PASS
  test_chargen_persist_and_play  : 5/5 PASS
  test_routing_completeness.py   : 2/2 PASS (will fail post-implementation
                                    if SPAN_* constants are added without
                                    SPAN_ROUTES entry — by design)
```

**Handoff:** To Inigo Montoya (Dev) for GREEN implementation.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — 37/37 target tests pass, 2759/2762 in full server suite (3 pre-existing failures unrelated to this story; see Delivery Findings).

### Implementation Summary

Three files changed beyond tests:

1. **`sidequest/telemetry/spans/chargen.py`** — added `SPAN_CHARGEN_STARTING_KIT_DEDUP_EVALUATED` and `SPAN_CHARGEN_STARTING_KIT_DEDUP_FIRED` constants and registered both in `SPAN_ROUTES` with `event_type="state_transition"`, `component="character_creation"`. Sibling-shape with `SPAN_CHARGEN_ARCHETYPE_GATE_*`. The extract lambdas pass through every load-bearing attribute the GM panel renders (class_name, pre_dedup_count, equipment_ids_count, skipped_count, items_added, items_upgraded, final_count, genre, world, player_id; plus skipped_ids on the fired span).

2. **`sidequest/server/dispatch/chargen_loadout.py`** — `apply_starting_loadout()` now accepts `*, genre="", world="", player_id=""` kwarg-only and emits both spans. The `inventory_config is None` short-circuit branch ALSO emits `evaluated` (with zero counts) so Sebastien gets negative confirmation that the dedup pass ran. Dedup logic mirrors the spec from context-story-45-12.md verbatim: build `existing_ids` and `existing_names` sets from `character.core.inventory.items` (post-upgrade), then for each id in `equipment_ids` skip when `cand_id in existing_ids` or `cand_name in existing_names`. `skipped_ids` accumulates for the fired-span payload. The `items_added` return value reflects the post-dedup count (skipped items NOT counted), matching the existing test_class_equipment_and_gold_appended contract.

3. **`sidequest/server/websocket_session_handler.py:879`** — call site updated to pass `genre=sd.snapshot.genre_slug, world=sd.snapshot.world_slug, player_id=player_id`. The kwarg-only addition is backwards-compat — no other caller breaks.

### Reuse, Not Reinvent

- `_item_dict_from_catalog()` and `_item_dict_minimal()` stayed unchanged — dedup wraps the append, doesn't replace the dict-build (per spec).
- `_upgrade_hint_items_from_catalog()` runs first; the dedup uses the post-upgrade item ids/names so renamed builder items are matched against the catalogue.
- The OTEL pattern follows `chargen.archetype_gate_*` (sibling spans live a few lines above in the same file).

### What I Did NOT Change

- Did NOT touch `CharacterBuilder.build()` or the `equipment_tables` emission path (`builder.py:1366-1422`). Story explicitly out-of-scope.
- Did NOT collapse builder-side intra-list duplicates (3 torches → 1 torch). Story Out-of-Scope §3 explicitly defers stack consolidation as a separate fix.
- Did NOT migrate existing saves. New chargens get the dedup; Blutka's 24-item kit stays.
- Did NOT touch UI. The fix surfaces in the GM panel via the new spans.

### OTEL Discipline

- Both spans MUST be in `SPAN_ROUTES` — pinned by `TestStartingKitDedupSpanRouting` (4 tests, including extract-shape regression locks). The static lint at `tests/telemetry/test_routing_completeness.py` independently verifies the routing decision is explicit.
- `evaluated` fires on EVERY call path — including `inventory_config is None` (verified by `test_evaluated_span_fires_when_inventory_config_is_none`). This is the negative-confirmation contract per CLAUDE.md OTEL Observability Principle.
- `fired` fires only when `skipped_count > 0` (verified by `test_fired_span_does_not_fire_on_disjoint_path`). Without this guard the GM panel would cry wolf on every chargen-confirm.
- Wire-test `test_chargen_confirm_emits_starting_kit_dedup_evaluated_span` proves the production caller is wired with span emission, not just helper changes.

### Test Run Witness (post-fix)

```
=== 37/37 PASS — 0.45s ===

tests/server/test_chargen_loadout.py:        28/28 PASS
  TestStartingKitDedup           : 7/7 PASS
  TestStartingKitDedupSpans      : 8/8 PASS
  TestStartingKitDedupSpanRouting: 5/5 PASS
  Pre-existing                   : 8/8 PASS

tests/server/test_chargen_persist_and_play.py: 7/7 PASS
  Pre-existing                   : 5/5 PASS
  New wire-tests                 : 2/2 PASS

tests/telemetry/test_routing_completeness.py:  2/2 PASS
```

Full server suite: 2759/2762 PASS, 44 skipped. The 3 failures
(`test_status_apply.py::test_status_change_appends_to_named_actor`,
`test_status_clear.py::test_wiring_narration_apply_clear_and_add_in_same_turn`,
`test_stale_slot_reinit_wire.py::test_post_chargen_turn_manager_is_fresh_after_stale_slot_reinit`)
all hit `sqlite3.ProgrammingError: Cannot operate on a closed database`
in `watcher_hub.py:191` and reproduce on `main` without my changes
(verified via `git stash`). Filed under Delivery Findings.

### Lint Status

`uv run ruff check` on the 5 changed files reports 3 errors, all
pre-existing in code I did not author (verified via `git stash`):

- `websocket_session_handler.py:295` UP037 (pre-existing)
- `websocket_session_handler.py:385` SIM105 (pre-existing)
- `tests/server/test_chargen_persist_and_play.py:43` E402 (pre-existing,
  carries a `# noqa: E402` already; ruff still flags — likely tooling
  drift)

`uv run ruff format` applied to the 5 changed files (5 files reformatted).
Tests still pass post-format.

### Handoff

To **The Man in Black (Architect)** for `spec-check` phase. The implementation
matches the story's Technical Approach verbatim (identity-aware append, no
larger refactor, reuse helpers, sibling-shape spans). Two test relaxations
documented as Design Deviations — both narrow over-strict assertions to
match the story's Out-of-Scope carve-out, no AC dropped.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None requiring code change. Two test relaxations already
logged as Dev deviations — confirmed correctly scoped against story
Out-of-Scope §3.

### AC-by-AC Verification

| AC | Spec | Implementation | Status |
|----|------|----------------|--------|
| AC1 | Catalogue overlap with builder dedup'd; final reflects union, not sum | `existing_ids`/`existing_names` initialized from `character.core.inventory.items` post-upgrade; loop skips `cand_id in existing_ids or cand_name in existing_names` (`chargen_loadout.py:201-227`) | Aligned |
| AC2 | Pure-disjoint case appends all catalogue items unchanged | Skip predicate is `id-or-name match`; disjoint inputs flow through the append branch (verified by `test_disjoint_case_appends_all`) | Aligned |
| AC3 | Pure-overlap case skips everything in second batch | Same skip predicate; full overlap → `items_added=0`, `skipped_count=len(equipment_ids)` (verified by `test_full_overlap_skips_all`) | Aligned |
| AC4 | Name-fallback collision (id differs, name matches) | Skip predicate explicitly OR's `cand_name in existing_names`; case-insensitive via `.strip().lower()` | Aligned |
| AC5 | `evaluated` fires on every confirm (incl. `inventory_config=None`); `fired` only on overlap; SPAN_ROUTES registered | `inventory_config is None` branch emits evaluated span explicitly (`chargen_loadout.py:155-167`); main path emits unconditionally before the `if skipped_count > 0` fired-span guard. Both registered in `spans/chargen.py:75-117` with `state_transition`/`character_creation`. | Aligned |
| AC6 | End-to-end persist returns deduped result | Wire site at `websocket_session_handler.py:879-887` passes session identity; `_chargen_confirmation` runs loadout before snapshot.persist. Wire-test pins span emission + final_count↔persisted_count parity. | Aligned |

### Architectural Review

- **Reuse-first.** No new infrastructure. The spans piggyback on the existing `SPAN_ROUTES` / watcher_hub pipeline (sibling-shape with `chargen.archetype_gate_*` introduced for Story 45-6). The dedup wraps the existing append path; `_item_dict_from_catalog` and `_item_dict_minimal` are unchanged.
- **Backwards compatible.** `apply_starting_loadout()` signature change is kwarg-only with empty-string defaults. The 8 existing callers in `tests/server/test_chargen_loadout.py` all use positional args and remain green.
- **OTEL discipline upheld.** The `evaluated` span fires on every code path including `inventory_config is None` and `equipment_key is None`, satisfying CLAUDE.md OTEL Observability Principle's negative-confirmation requirement. The `fired` span is correctly gated to `skipped_count > 0` to prevent GM-panel signal-to-noise pollution. SpanRoute extract lambdas surface every load-bearing attribute.
- **ADR-014 (Diamonds and Coal) preserved.** Builder-side item_hint stubs are upgraded in place via `_upgrade_hint_items_from_catalog` BEFORE dedup runs — so a player's chargen-scene choice ("Mystery Compass") gets the catalogue's rich metadata, then the catalogue's redundant copy is skipped. The flavor stays with the player's pick.
- **ADR-085 (port-drift) closed.** This was an explicit IOU in `docs/plans/phase-2-chargen-port.md` — the chargen-port plan flagged the equipment_tables/starting_equipment overlap and deferred resolution. Now resolved.

### Design Deviation Review

Both Dev deviations are confirmed correctly scoped:

- **Test relaxation 1** (`test_partial_overlap_yields_union_blutka_regression`): TEA's original assertion of global id-uniqueness conflicts with story Out-of-Scope §3 ("Multi-quantity dedup... is a separate fix. If the builder produced 6 torches as separate items, the dedup will collapse the catalogue's 1 torch against any of them — net result is the catalogue copy is dropped"). The relaxed test asserts `len(items) == 14` (11 builder + 3 disjoint catalogue) and per-id count invariants — pinning the exact behavior the story scope describes. **Recommendation: A (spec stays, code/test updated already).** No further action.
- **Test relaxation 2** (`test_chargen_confirm_persists_deduped_inventory`): Original asserted no global duplicates in persisted state; same Out-of-Scope conflict. The relaxed test asserts that catalogue ids do not exceed pack-list quantity AND in-memory `final_count` matches persisted `len(items)` — the actual half-wired regression invariant AC6 calls out. **Recommendation: A.** No further action.

### Sibling-Story Forward Impact

- **Story 45-9** (sibling of 45-12, "total_beats_fired increment + OTEL"): Same Lane B "extractor fires but applier doesn't observe" shape, same always-fire-on-success-path span pattern. Coordinated discipline maintained — no contract conflict.
- **Future stack-consolidation story** (referenced in Out-of-Scope): When that lands, the relaxed test docstrings should guide the tightening. The `final_count == persisted_count` invariant in the wire-test will naturally tighten without modification.
- **Pack-content sweep** (TEA finding): `caverns_and_claudes/inventory.yaml:294-305` ships 3 torch entries in `starting_equipment[Delver]`. The dedup span will fire `dedup_fired` on every grimvault chargen-confirm in production. Not a bug per story scope, but worth a content sweep follow-up — the GM panel will show steady dedup_fired noise that should be quiet on cleanly-authored packs.

### Watcher-Hub Pre-Existing Failure (Out of Scope)

The Dev's Delivery Finding about `sqlite3.ProgrammingError: Cannot operate on a closed database` in `watcher_hub.py:191` is NOT introduced by this story — verified independently. The `_event_store._conn` lifetime is decoupled from pytest fixture scope, surfacing when state_transition events fire after another test closed the store. Should be a separate sprint story; not blocking 45-12.

### Decision

**Proceed to TEA verify.** No mismatches require code change. Implementation matches Technical Approach. Test relaxations are correctly bounded by Out-of-Scope. ADR-014 and ADR-085 honored.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — 37/37 target tests pass, simplify pass applied 1 high-confidence fix, no regressions.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | 1 HIGH (duplicated span emission) — APPLIED. 1 MEDIUM (SpanRoute factory abstraction) — DEFERRED out of story scope. 1 LOW (`_spans_named` staticmethod hoist) — NOTED. |
| simplify-quality | 7 findings | 1 HIGH (`skipped_ids` extractor default) — DISMISSED (intentional sibling-shape with `scrapbook.gap_rounds`). 2 MEDIUM (test docstring AC fragmentation) — NOTED. 4 LOW (magic literals 0.3/0.2 pre-existing, redundant comment, variable rename) — NOTED/dismissed. |
| simplify-efficiency | 2 findings | 1 MEDIUM (redundant `str().strip().lower()`) — NOTED but NOT applied (defensive pattern matches CLAUDE.md "No Silent Fallbacks"). 1 LOW (defensive guard layering) — NOTED. |

**Applied:** 1 high-confidence fix
- `sidequest/server/dispatch/chargen_loadout.py` — collapsed the two `chargen.starting_kit_dedup_evaluated` span-emission blocks into a single emission point past the no-config early return. Default zero-counts flow through. 133 lines refactored to 62, behavior unchanged. Commit `41cd715`.

**Dismissed:** 2 findings
- `simplify-quality #4` (`skipped_ids` default): The `""` default is intentional sibling-shape with `scrapbook.coverage_gap_detected.gap_rounds`'s extractor in `spans/scrapbook.py:60` — OTEL serializes sequence attributes as strings on the wire, and downstream consumers handle both empty-string and list shapes. Not a type bug; matches established pattern.
- `simplify-quality #1, #2` (magic literals 0.3, 0.2 narrative_weight): Pre-existing in `chargen_loadout.py:61, 117` (verified via `git stash`); not introduced by 45-12. Out of scope per "boy scouting bounded" memory rule.

**Flagged for Review:** 0 medium-confidence findings requiring reviewer attention.

**Noted (deferred to follow-up sprint):**
- `simplify-quality #5, #6` — Test docstrings reference "AC1–AC4" / "AC6 wire-test" without cross-referencing the test class housing AC5. Cosmetic; tests are functionally complete.
- `simplify-efficiency #1` — `str().strip().lower()` chain is defensive against unknown dict shapes. Pre-existing pattern in this file.
- `simplify-reuse #2` — SpanRoute factory abstraction would consolidate sibling-shape extractors across all `chargen.*` and `scrapbook.*` spans. Out of scope; would touch 8+ unrelated span definitions.

**Reverted:** 0

**Overall:** simplify: applied 1 fix, no regressions

### Quality Checks

- **Target tests:** `uv run pytest tests/server/test_chargen_loadout.py tests/server/test_chargen_persist_and_play.py tests/telemetry/test_routing_completeness.py` → **37/37 PASS** (post-simplify, post-format).
- **Full server suite:** `uv run pytest` → **2759/2762 PASS, 44 skipped, 3 failures** — all 3 pre-existing in `watcher_hub.py:191` (`sqlite3.ProgrammingError: Cannot operate on a closed database`) and reproduce on `develop` without 45-12 changes (verified by Dev via `git stash`). Tracked under Delivery Findings; not blocking.
- **Lint (changed files):** `uv run ruff check sidequest/server/dispatch/chargen_loadout.py sidequest/telemetry/spans/chargen.py` → **All checks passed.** The 3 pre-existing findings in `websocket_session_handler.py` and `tests/server/test_chargen_persist_and_play.py` reported by Dev are still present and out of scope.
- **Format:** `uv run ruff format` applied; tests still pass.

### Wire-Test Discipline (CLAUDE.md)

The story's wire-test guards hold:
- `test_chargen_confirm_persists_deduped_inventory` asserts in-memory `final_count` matches persisted `len(items)` — catches the half-wired regression where dedup runs in memory but the persisted snapshot still has stale items.
- `test_chargen_confirm_emits_starting_kit_dedup_evaluated_span` asserts the production confirm path emits the span — proves call-site wiring, not just helper changes.
- `test_routing_completeness.py` static lint enforces all new SPAN_* constants are explicitly routed in `SPAN_ROUTES` or `FLAT_ONLY_SPANS` — adding a span without registration trips the lint.

### Refactor Note

The collapse of the two evaluated-span blocks (commit `41cd715`) consolidates the no-config and main-config paths into a shared default-zero pre-init. The negative-confirmation contract is preserved: the evaluated span fires exactly once per `apply_starting_loadout()` call, regardless of which branch the function takes. Verified by re-running the 8-test `TestStartingKitDedupSpans` class and the 3 wire-tests post-refactor.

### Handoff

To **Westley (Reviewer)** for `review` phase. Implementation matches story spec, simplify pass applied 1 high-confidence reuse fix with full test coverage. Two test relaxations and the refactor commit are documented in Design Deviations. Pre-existing failures (`watcher_hub` sqlite teardown bug) and pre-existing lint findings are filed under Delivery Findings as out-of-scope work for follow-up sprints.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (0 new lint, 0 smells, 37/37 targeted GREEN, 2759/2762 full GREEN with 3 pre-existing fails) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 1, dismissed 1, deferred 5 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 0, dismissed 0, deferred 3 |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | No | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes | findings | 3 (1 real, 2 pre-existing or test-tolerance) | confirmed 1, dismissed 2, deferred 0 |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled per settings)
**Total findings:** 2 confirmed, 3 dismissed (with rationale), 8 deferred (non-blocking improvements for follow-up)

### Confirmed Findings

| # | Tag | Severity | Issue | Location | Disposition |
|---|-----|----------|-------|----------|-------------|
| 1 | [TEST]/[RULE] | MEDIUM | Wire-test `assert len(evaluated) >= 1` is under-constrained — exactly 1 span should fire per chargen-confirm; `>= 1` would silently pass a double-emission regression. Test-analyzer raised the same shape independently. | `tests/server/test_chargen_persist_and_play.py:1252` | Logged as upstream finding; not blocking — single-emission is verified by the unit-level `test_evaluated_span_fires_on_disjoint_path` (`len(evaluated) == 1`) and by `test_three_chargen_runs_evaluated_three_fired_two`. The wire-test purpose is "the wire fires AT LEAST once," and tightening to `== 1` is a minor improvement, not a correctness bug. |
| 2 | [DOC] | LOW | `_builder_hint_dict` docstring at `tests/server/test_chargen_loadout.py:401` claims to mirror `builder.py:1407–1422` — comment-analyzer reports those lines are backstory/abilities code; the equipment_tables stub is at lines 1328–1344. | `tests/server/test_chargen_loadout.py:401` | Logged as upstream finding; not verified line-by-line by Reviewer (would expand scope). The docstring is informational; the test fixture body is the load-bearing contract. |

### Dismissed Findings

- **[TEST] Tautological span-constant assertions** (`test_chargen_loadout.py:932, 944`): `assert SPAN_X == "chargen.starting_kit_dedup_evaluated"` — test-analyzer flags as vacuous. **Dismissed:** these tests pin the *string contract* the GM panel filters on. A rename of the constant value (e.g. to `"chargen.dedup.starting_kit"`) would silently break the dashboard; this assertion catches that. The constant *name* would have to be renamed alongside, which the import-level test would catch. The combination is regression-pinning, not vacuous.
- **[RULE] Star-import pattern in `spans/__init__.py`** (rule #10): pre-existing across all 38 span-domain submodules; not introduced by 45-12. Adding `__all__` would touch 8+ unrelated domain modules and require coordination with the routing-completeness lint (which uses `vars(spans_pkg)` to enumerate constants). Dismissed per "boy scouting bounded" memory rule.
- **[RULE] Substring-in-`str(repr)` assertion in `test_fired_span_carries_skipped_ids_payload`** (line 822): rule-checker flags as fragile. **Dismissed:** the test docstring explicitly documents this tolerance ("OTEL stringifies sequence attributes; accept any repr that names both skipped ids") — the OTEL SDK serializes sequence attributes as strings, and downstream consumers accept either repr. Sibling-shape with `scrapbook.coverage_gap_detected.gap_rounds` extractor at `spans/scrapbook.py:60`.

### Deferred (non-blocking, filed under Delivery Findings for follow-up)

- **[TEST] Missing `items_added` return-value assertions** in `test_partial_overlap_yields_union_blutka_regression` (line 504), `test_disjoint_case_appends_all` (line 537), `test_intra_batch_dedup_collapses_pack_duplicates` (line 637). The function contract returns `(items_added, gold_added)`; tests discard the return value and assert via `len(items)`. The len assertions catch the production failure modes; capturing the return tuple is incremental coverage.
- **[TEST] Missing `items_upgraded == 0` value assertion** in `test_evaluated_span_attributes_carry_full_set` (line 696). Required-key set is asserted; one specific value isn't.
- **[TEST] Wire-test torch_count `<= 3` is upper-bound only** (line 334). Doesn't catch over-dedup regressions that suppress builder-placed torches. Adding `>= 1` lower bound or asserting persisted contains a torch would close it. Builder walk is non-deterministic for grimvault, so the lower bound has to be loose.
- **[TEST] Missing `dedup_fired` span assertion** in `test_chargen_confirm_persists_deduped_inventory` (line 312). The grimvault pack always has overlap, so `fired` MUST emit on this path; not asserting it leaves a wire-level coverage gap for the AC5 fired-span contract.
- **[DOC] Documentation precision**: `apply_starting_loadout` docstring prescribes `sd.snapshot.genre_slug` while sibling code in the same handler uses `sd.genre_slug` directly. Either align the call site or document why snapshot path is preferred.
- **[DOC] `CharacterBuilder.equipment_tables`** referenced as if public; it's `_equipment_tables` set via `with_equipment_tables()`. Update `chargen.py` block comment for precision.

## Reviewer Assessment

**Verdict:** APPROVED

### Rule Compliance (python.md exhaustive check)

Rule-checker walked all 13 lang-review rules across 67 instances in the diff. Summary:

| Rule | # Instances | Compliant | Violations |
|------|-------------|-----------|------------|
| 1 silent-exceptions | 6 | 6 | 0 |
| 2 mutable-defaults | 5 | 5 | 0 |
| 3 type-annotations | 8 | 6 | 2 (private helpers — exempt) |
| 4 logging | 5 | 5 | 0 (skipped-item path uses span as primary signal, info-level for normal) |
| 5 path-handling | 1 | 1 | 0 |
| 6 test-quality | 22 | 21 | 1 (wire-test `>= 1` — confirmed finding) |
| 7 resource-leaks | 4 | 4 | 0 (all `with` context-managed) |
| 8 unsafe-deserialization | 2 | 2 | 0 |
| 9 async-pitfalls | 4 | 4 | 0 |
| 10 import-hygiene | 6 | 5 | 1 (pre-existing star-import; dismissed) |
| 11 input-validation | 3 | 3 | 0 (genre/world/player_id are session-scoped, server-controlled) |
| 12 dependency-hygiene | 3 | 3 | 0 (no new deps) |
| 13 fix-regressions | 5 | 5 | 0 |

**Net:** 1 confirmed rule violation (under-specified wire-test assertion), 2 dismissals with rationale.

### Reviewer Observations

**Data flow traced.** User input flows: WebSocket `CharacterCreationMessage` → `_chargen_confirmation()` → `builder.build()` → `_resolve_character_archetype()` → `_gate_archetype_resolution()` → `apply_starting_loadout(character, sd.genre_pack.inventory, genre=sd.snapshot.genre_slug, world=sd.snapshot.world_slug, player_id=player_id)` (`websocket_session_handler.py:879-887`) → mutates `character.core.inventory.items` in place → `replace_with` snapshot mutation → `room.save()` → SQLite persistence. The dedup runs **before** snapshot persistence. Wire-test `test_chargen_confirm_persists_deduped_inventory` confirms in-memory `final_count` matches persisted `len(items)`. Safe because all data is server-controlled (genre pack YAML + builder rolls); no user-tainted input reaches the dedup keys.

**[VERIFIED] Pattern: SPAN_ROUTES sibling-shape with `chargen.archetype_gate_*` and `scrapbook.coverage_*`** — `sidequest/telemetry/spans/chargen.py:75-138` declares both new spans as routed `state_transition` events with `component="character_creation"`, matching the precedent set by Story 45-6 (archetype gate) and Story 45-10 (scrapbook coverage). Rule-checker confirmed routing-completeness lint passes. ADR / OTEL Observability Principle complied with.

**[VERIFIED] Error handling on the dedup path** — `apply_starting_loadout()` has no try/except; exceptions in span emission, attribute setting, or list mutation propagate to `_chargen_confirmation()` which catches `BuilderError` (line 822) and returns `_error_msg(...)` to the WebSocket. The dedup logic itself is exception-free: dict `.get()` with defaults, sets/list operations on guaranteed types. Evidence: `chargen_loadout.py:177-228` has zero try blocks; OTEL spans (`with _tracer.start_as_current_span(...) as span`) properly close on any exception via context manager. Complies with python.md #1 (silent-exception rule) and #7 (resource-leak rule).

**[VERIFIED] Wiring end-to-end** — Wire site at `websocket_session_handler.py:879-887` is reached on every chargen-confirm; integration test `test_chargen_confirm_emits_starting_kit_dedup_evaluated_span` at `tests/server/test_chargen_persist_and_play.py:1230` proves the production path emits the span (test passes against the real `caverns_and_claudes/grimvault` content pack). Per CLAUDE.md "Verify Wiring, Not Just Existence" rule.

**[VERIFIED] Span attribute contract for GM panel** — All 10 attributes (`class_name`, `pre_dedup_count`, `equipment_ids_count`, `skipped_count`, `items_added`, `items_upgraded`, `final_count`, `genre`, `world`, `player_id`) appear in both the emit site (`chargen_loadout.py:236-261`) and the SpanRoute extractor (`spans/chargen.py:80-117`). `test_evaluated_span_attributes_carry_full_set` pins the contract. The fired-span variant adds `skipped_ids` payload, also matched in extractor and emit site.

**[SIMPLE] Single emission point refactor** — Verify commit `41cd715` collapsed the two evaluated-span emit blocks correctly. Re-read `chargen_loadout.py:163-275`: defaults flow through the `inventory_config is None` branch (skipping the if-block), then the single emission point fires with zero counts on the no-config path. Verified the test `test_evaluated_span_fires_when_inventory_config_is_none` covers this branch and passes post-refactor (37/37 GREEN).

**[TEST] Wire-test under-specifies cardinality** — `tests/server/test_chargen_persist_and_play.py:1252` uses `>= 1` instead of `== 1`. **Severity: MEDIUM (non-blocking).** A double-emission regression would silently pass this assertion. Mitigated by sibling unit tests (`test_evaluated_span_fires_on_disjoint_path` asserts `== 1`) and by `test_three_chargen_runs_evaluated_three_fired_two`. Filed as Delivery Finding for follow-up.

**[RULE] python.md #6 (test quality) — under-constrained assertion** — Same finding as `[TEST]` above, independently confirmed by rule-checker against `python.md #6` ("`assert result` without checking specific value — truthy check misses wrong values"). The wire-test uses an inequality where exact-equality would pin the contract. Severity: MEDIUM. Non-blocking; mitigated by sibling unit-level tests with `== 1`.

**[RULE] python.md #10 (import hygiene) — pre-existing** — Star-import pattern in `sidequest/telemetry/spans/__init__.py` exists across all 38 domain submodules without `__all__` declarations. Pre-existing on develop; not introduced by 45-12. The routing-completeness lint at `tests/telemetry/test_routing_completeness.py` enumerates `vars(spans_pkg)` and depends on the current pattern. Dismissed per "boy scouting bounded" — a sweep would touch 8+ unrelated modules and require coordinated lint changes.

**[RULE] python.md #3 (type annotations) — private-helper exemption** — Two private helpers (`_item_dict_from_catalog`, `_item_dict_minimal`) return bare `dict` rather than `dict[str, object]`. Per python.md #3: "Internal/private helpers are exempt." Pre-existing pattern in this file; not introduced by 45-12. Dismissed.

**[DOC] Stale line-number references** — `_builder_hint_dict` docstring claims to mirror `builder.py:1407–1422`. Comment-analyzer reports the actual equipment_tables stub is at `builder.py:1328–1344`. **Severity: LOW (non-blocking).** Cosmetic; the test fixture body matches the actual builder shape regardless of the line-number annotation. Filed as Delivery Finding.

**[DOC] Documentation drift on session-identity access pattern** — `apply_starting_loadout` docstring prescribes `sd.snapshot.genre_slug` while the same handler uses `sd.genre_slug` directly elsewhere. **Severity: LOW (non-blocking).** Either the snapshot path is authoritative post-materialization (load-bearing) and should be documented, or both paths are equivalent and the docstring should align. Filed as Delivery Finding.

### Devil's Advocate

The story claims to fix the canonical write-back-symmetry failure of Epic 45. What could go wrong?

**Could a malicious or weird genre pack break the dedup?** A pack with `starting_equipment[Class]` containing the empty string `""` as an id would produce `cand_id == ""`, which `if cand_id and cand_id in existing_ids` correctly short-circuits. A pack with `id=null` in the catalog hits `_item_dict_minimal(item_id)` which uses the `equipment_ids` value verbatim. Edge case: what if `equipment_ids` contains `None`? `_item_dict_minimal(None)` would fail at `display = item_id.replace("_", " ")` with `AttributeError`. **VERDICT:** Pre-existing pack-validation responsibility; not introduced by 45-12. The Pydantic genre pack model rejects null ids at load.

**Could a confused user hit a path where the span doesn't fire?** Re-read all branches:
- `inventory_config is None` → defaults flow → single emit → ✓ fires
- `inventory_config is not None`, `equipment_key is None` → `equipment_ids = []` → loop doesn't execute → emit fires with zero counts → ✓
- `inventory_config is not None`, `equipment_key is not None`, `len(equipment_ids) == 0` → loop doesn't execute → emit fires with zero counts → ✓
- All overlap → loop executes, items_added=0, skipped_count=N → emit fires → fired-span also fires → ✓
- All disjoint → loop executes, items_added=N, skipped_count=0 → emit fires → fired-span does NOT fire → ✓

All paths covered. Spans fire correctly. The wire-test `>= 1` constraint is the only weakness, already filed.

**Race conditions?** `apply_starting_loadout` mutates `character.core.inventory.items` in place. The `_chargen_confirmation` flow runs synchronously inside a single WebSocket message handler; no concurrent mutation possible. The character is a fresh build, not yet shared. ✓

**What if OTEL's `set_attribute("skipped_ids", list)` fails?** Per opentelemetry-api docs, `set_attribute` accepts homogeneous sequences of primitives. `skipped_ids` is `list[str]` of lowercased ids. Safe.

**What if `gold` is a negative integer in the pack?** `character.core.inventory.gold += gold` would subtract. Pre-existing concern; not introduced by 45-12. Pack validation responsibility.

**What if the builder ALREADY emits items with empty-string ids?** The dedup filter `if it.get("id")` excludes them from `existing_ids`. They remain in `character.core.inventory.items` but don't poison the dedup. Then catalogue items with non-empty ids land normally. ✓

**Has the story missed any AC?** Cross-checking AC1–AC6 against test names: all six have direct test coverage. Architect's spec-check confirmed alignment. Two Dev deviations relaxed test assertions to match story Out-of-Scope §3 — not AC drops.

**No blocking issues uncovered.**

### Severity Table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| (none CRITICAL) | — | — | — |
| (none HIGH) | — | — | — |
| MEDIUM | Wire-test `assert len(evaluated) >= 1` should be `== 1` (under-specified cardinality) | `tests/server/test_chargen_persist_and_play.py:1252` | Filed as upstream finding; non-blocking |
| LOW | `_builder_hint_dict` docstring references `builder.py:1407–1422` (actual: 1328–1344) | `tests/server/test_chargen_loadout.py:401` | Filed as upstream finding; non-blocking |
| LOW | Docstring prescribes `sd.snapshot.genre_slug` without rationale vs sibling `sd.genre_slug` pattern | `chargen_loadout.py:152` | Filed as upstream finding; non-blocking |
| LOW | Block comment references `CharacterBuilder.equipment_tables` (private `_equipment_tables`) | `spans/chargen.py:315` | Filed as upstream finding; non-blocking |
| LOW | Test return-value coverage gaps (4 tests) | `test_chargen_loadout.py:504, 537, 637, 696` | Filed as upstream finding; non-blocking |
| LOW | Wire-test `torch_count <= 3` lacks lower-bound regression guard | `test_chargen_persist_and_play.py:334` | Filed as upstream finding; non-blocking |
| LOW | Wire-test missing `dedup_fired` span assertion | `test_chargen_persist_and_play.py:312` | Filed as upstream finding; non-blocking |

**No CRITICAL or HIGH issues. APPROVED.**

### Handoff

To **Vizzini (SM)** for `finish` phase. All 6 ACs covered, all four enabled subagent specialists returned, 1 confirmed MEDIUM finding + 7 LOW filed as upstream improvements. Implementation matches Architect's spec-check sign-off. Pre-existing failures and lint findings (Dev/Verify) remain out-of-scope and tracked in Delivery Findings.