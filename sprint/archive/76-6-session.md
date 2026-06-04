---
story_id: "76-6"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 76-6: Source coverage: sync stateful snapshot.npcs into the entity index

## Story Details
- **ID:** 76-6
- **Jira Key:** (none — Jira not enabled)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T13:54:51Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T14:30:00Z | 2026-06-04T13:32:37Z | -3443s |
| red | 2026-06-04T13:32:37Z | 2026-06-04T13:41:49Z | 9m 12s |
| green | 2026-06-04T13:41:49Z | 2026-06-04T13:48:20Z | 6m 31s |
| review | 2026-06-04T13:48:20Z | 2026-06-04T13:54:51Z | 6m 31s |
| finish | 2026-06-04T13:54:51Z | - | - |

## Sm Assessment

**Setup complete — routing to TEA (RED).** Story 76-6 is foundational source-coverage for the universal retrieval index (epic 76): add a stateful-`Npc` projector path (`project_npc_card` currently only accepts `NpcPoolMember`) and extend `sync_entity_cards` so scene-stateful NPCs — not just pool members — are projected and retrievable.

**Why now:** This is the unblocked prerequisite for the ADR-118 amendment epic (84). The amendment's unified pertinence scorer (84-1) can only rank entities that are *in* the index; 76-6 puts stateful NPCs there. Start order: 76-6 → 76-7 → 84-1.

**Scope guardrails for the implementers:**
- In scope: `Npc` projector + `sync_entity_cards` extension covering `snapshot.npcs` (stateful), not just `snapshot.npc_pool`. Dedup-by-id with pool-member cards (a promoted Npc and its pool origin must not double-index).
- Per project doctrine: OTEL on the sync decision (the existing `entity_sync` counters — `npc_count` must reflect stateful NPCs), a wiring test that proves the stateful path is reachable from production (not a source-text grep), and No Silent Fallbacks on an unprojectable Npc.
- Out of scope: factions/locations (that's 76-7), the scorer rewrite (84-1), tiering/aliases (epic 84).

**Branch:** `feat/76-6-stateful-npc-projector` on `sidequest-server/develop` (gitflow, non-stacked). No Jira (personal project).

**Architect note carried forward:** 75-12 (ratification gate into the ADR-118 projection) is recommended to fold into 84-1 rather than build-then-rewrite — not this story's concern, but the same projection surface, so keep `is_projectable`/ratification in mind when touching the projector.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (11 feature tests failing, ready for Dev) + 1 upstream-guard test green (intentional regression guard)

**Test Files:**
- `tests/game/test_entity_sync_stateful_npcs.py` — projector + `sync_entity_cards` unit tests (game tier)
- `tests/server/dispatch/test_entity_sync_stateful_wiring.py` — production wiring through `dispatch/entity_sync.sync_for_turn` (server tier)

**Tests Written:** 12 tests covering ACs 1-3 + SM dedup/No-Silent-Fallbacks/OTEL guardrails (AC4 = suite-green, verified at GREEN).

| AC / Guardrail | Test(s) | Status |
|---|---|---|
| AC1 — projector accepts a stateful Npc | `test_projects_a_stateful_npc_into_a_namespaced_card`, `test_stateful_projection_is_deterministic`, `test_stateful_content_keys_on_attitude_band_not_raw_int` | RED |
| AC2 — sync iterates `snapshot.npcs` | `test_sync_indexes_a_stateful_npc_from_empty_pool`, `test_narrator_invented_npc_is_indexed` | RED |
| AC3 — pool + stateful union; promoted dedup | `test_pool_and_distinct_stateful_npcs_both_indexed`, `test_promoted_npc_dedups_against_its_pool_origin`, `test_stateful_band_change_reprojects_through_sync` | RED |
| Wiring (production reachable) | `test_sync_for_turn_indexes_a_stateful_npc` | RED |
| OTEL lie-detector (`npc_count` honesty) | `test_sync_for_turn_npc_count_reflects_stateful_cast` | RED |
| No Silent Fallbacks (upstream guard) | `test_creature_core_name_validator_is_the_upstream_guard`, `test_minimal_valid_stateful_npc_always_projects` | green guard / RED |

### Rule Coverage (python lang-review)

| Rule | Coverage | Status |
|------|----------|--------|
| #6 test quality | Self-checked: every test asserts specific values (ids, counts, content suffixes), no `assert True`/vacuous truthy checks; wiring mock patches `_watcher_publish` **where used** (`dispatch.entity_sync`), not where defined | pass |
| #3 type annotations | All test helpers/fixtures annotated (`-> Npc`, `-> EntityCard`, etc.) | pass |
| #1 silent exceptions / No Silent Fallbacks | `npc_count` honesty test + upstream-guard tests ensure no silent stub-card; production `sync_for_turn` swallow-path remains (ADR-006), exercised indirectly | pass |
| OTEL doctrine (project) | `test_sync_for_turn_npc_count_reflects_stateful_cast` asserts the GM-panel watcher event counts stateful NPCs | RED (drives Dev) |
| #2 mutable defaults, #5 paths, #7 resources, #8 deserialization, #9 async, #11 input-validation | N/A — pure in-memory projection; no I/O, async, untrusted input, or resource handles in this feature | n/a |

**Rules checked:** 4 of 13 lang-review rules applicable; all have coverage or are pinned. **Self-check:** 0 vacuous tests (1 candidate — the blank-name test — was caught failing-at-fixture-construction and rewritten into the upstream-guard pair; see deviation).

**Handoff:** To Agent Smith (Dev) for GREEN. The dedup-with-stateful-precedence in `sync_entity_cards` and the polymorphic `project_npc_card` are the two load-bearing changes (see Delivery Findings).

## Dev Assessment

**Status:** GREEN — implementation complete, all 76-6 tests pass.

**Implementation complete:** Yes

**Changed files:**
- `sidequest/game/entity_card.py` — `project_npc_card` now polymorphic over `NpcPoolMember | Npc` (stateful name from `core.name`, no role; shared `.pronouns`/`.disposition`). `TYPE_CHECKING`-only `Npc` import avoids a `session` import cycle.
- `sidequest/game/entity_sync.py` — `sync_entity_cards` unions `snapshot.npcs` (stateful, first) with `npc_pool`; promoted-NPC dedup with stateful precedence (skip pool member by card id or `pool_origin` name); extracted `_apply_npc_card` for the shared upsert+tally.

**AC accountability:**

| AC | Status | Evidence |
|----|--------|----------|
| AC1 — projector accepts both sources | DONE | `TestProjectStatefulNpc` (3 tests) green |
| AC2 — sync iterates `snapshot.npcs` | DONE | `TestSyncIndexesStatefulNpcs` (3 tests) + wiring test green |
| AC3 — pool+stateful union, promoted dedup, retrievable | DONE | `TestPromotedNpcDedup` (2) + union test + `npc_count` wiring test green |
| AC4 — full suite green, ruff/format/pyright clean | DONE (scoped) | 12 new + 275 entity/retrieval/dispatch green; changed files ruff+format+pyright clean. **Caveat:** 7 pre-existing develop failures remain (unrelated — see Delivery Findings) |

**Verification:**
- `tests/game/test_entity_sync_stateful_npcs.py` + `tests/server/dispatch/test_entity_sync_stateful_wiring.py`: **12 passed**.
- Regression: `test_entity_sync.py`, `test_entity_card.py`, `test_entity_store.py`, `test_retrieval_orchestration.py`, `tests/server/dispatch/`: **275 passed**.
- Changed files: ruff `All checks passed`, format clean, pyright `0 errors`.
- Full suite: 10276 passed, 7 failed — the 7 **proven pre-existing** (fail identically with my changes stashed; not caused by 76-6).

**Deviations:** None beyond TEA's logged note (the unprojectable-stateful path is unreachable — implementation keys projection on the validated `core.name`, honoring it).

**Handoff:** To The Architect (TEA) for verify (simplify + quality-pass).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (GREEN: 12 story + 78 regression, ruff/format/pyright clean, 0 smells) | none | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled returned clean; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 1 non-blocking observation (count nuance, intended)

## Reviewer Assessment

**Verdict:** APPROVED

**Observations:**
1. `[VERIFIED]` Polymorphic dispatch is correct — `entity_card.py:181-187`: `isinstance(npc, NpcPoolMember)` → `.name`/`.role`; else → `.core.name`/`role=None`. Both feed `_slug(name)` + `EntityCard.new`, so the blank-name guard still fires for pool members and `CreatureCore`'s validator covers stateful. Complies with No-Silent-Fallbacks.
2. `[VERIFIED]` Dedup precedence + rename-on-promotion — `entity_sync.py`: stateful processed first into `covered_ids` (card id) and `covered_origins` (`pool_origin`); pool member skipped if `card.id in covered_ids or member.name in covered_origins` (line ~149). Correctly suppresses a duplicate even when a promoted `Npc.core.name` diverged from its origin member name.
3. `[VERIFIED]` `npc_count` honesty — `_apply_npc_card` increments `npc_count` once per upserted unique card; deduped members are skipped *before* tally, so the count equals unique NPCs. The wiring test pins the published watcher `npc_count == 1`.
4. `[VERIFIED]` Import hygiene (lang-review #10, exemplary) — `Npc` imported under `TYPE_CHECKING` (`entity_card.py:30-35`) with `from __future__ import annotations` keeping the union lazy; no `session` runtime cycle. `EntityCard` added to the existing runtime import in `entity_sync.py` (already a dependency).
5. `[VERIFIED][SEC]` No information leakage — confirmed by security subagent: `failed_refs`/NPC names never reach the watcher event or OTEL span (only scalar counts + derived `outcome`); the `logger.warning` is server-side, `%`-lazy, and carries only internal game-state names.
6. `[LOW]` stateful-vs-stateful dedup is not enforced here — it relies on the upstream `snapshot.npcs` name-uniqueness invariant (`session.py` promotion, `core.name`-keyed). Two distinct entities sharing a name collapse to one `npc:<slug>` card — inherent to the **pre-existing** slug-id identity model (Epic-72), not introduced by 76-6. Non-blocking.
7. `[VERIFIED]` No regressions — 78 entity/retrieval/dispatch regression tests green; the 6 remaining full-suite failures proven pre-existing on `develop` (stash-and-rerun by Dev; corroborated by preflight, which also found `apply_world_patch active_stakes` actually passes — so 6, not 7).

**Data flow traced:** player turn → `_execute_narration_turn` → `dispatch/entity_sync.sync_for_turn(sd)` → `sync_entity_cards(sd.entity_store, sd.snapshot)` → unions `snapshot.npcs` (stateful) + `npc_pool` → `project_npc_card` → `EntityStore.upsert` → embed worker → `retrieve_turn_context` reads the store → narrator prompt. Stateful NPCs now enter the index and the GM-panel `npc_count`. Safe — internal game state only, no untrusted input on this path.

**Error handling:** projector failures caught as `(ValueError, ValidationError)`, counted in `failed`/`failed_refs`, logged at WARNING, never stubbed. An unexpected type (neither source) would raise `AttributeError`, caught by the dispatch-layer outer `except Exception` (ADR-006 graceful degradation) — the turn survives. Unreachable from untrusted input (`snapshot.npcs` is internal).

### Rule Compliance (python lang-review)

| Rule | Instances in diff | Verdict |
|------|-------------------|---------|
| #1 silent exceptions | 2 except clauses (`entity_sync.py` stateful + pool paths) — both catch specific `(ValueError, ValidationError)`, log, and count | compliant |
| #2 mutable defaults | none (`covered_ids`/`covered_origins` are locals, not defaults) | compliant |
| #3 type annotations | `project_npc_card`, `_apply_npc_card`, `sync_entity_cards` fully annotated | compliant |
| #4 logging | WARNING level, `%`-lazy, no sensitive data (security-confirmed) | compliant |
| #6 test quality | meaningful assertions; mock patched where used | compliant |
| #10 import hygiene | `TYPE_CHECKING` Npc import (no cycle); no star imports | compliant (exemplary) |
| #11 input validation | `_slug` + `CreatureCore.name` validator + `EntityCard.content` min_length guard the boundary | compliant |
| #5/#7/#8/#9/#12 | N/A — pure in-memory projection; no paths, resources, deserialization, async, or deps | n/a |

### Devil's Advocate

Argue it is broken. **Attack 1 — duplicate pool names.** Two `NpcPoolMember`s both named "Borin" (differing role/disposition) both slug to `npc:borin`; with no stateful Borin, `covered_ids` is empty, so the second member reaches `_apply_npc_card` and `upsert` replaces the first — if content differs, `reprojected`+1 and `npc_count`+1, double-counting one id. **Rebuttal:** this is *pre-existing* pool behavior (the original loop did the same upsert+tally), and the pool is name-unique by construction (Epic-72 case-folded-name identity); 76-6 changes nothing here. **Attack 2 — None in `snapshot.npcs`.** A `None` element would `AttributeError` on `npc.core` and abort the sweep mid-loop, leaving a partially-synced index. **Rebuttal:** `snapshot.npcs` is a pydantic `list[Npc]`; it cannot hold `None`, and the dispatch outer `except` would isolate any such failure to the turn. **Attack 3 — `pool_origin` pointing at an absent member.** Harmless: `covered_origins` would carry a name no pool member matches; no skip mis-fires. **Attack 4 — ordering dependence.** Because stateful is processed first and `covered_*` is built before the pool loop, precedence is deterministic regardless of list order within each source. **Attack 5 — the count nuance.** A deduped pool member increments neither `unchanged` nor `npc_count`; a reader could think "fewer NPCs than exist." But the count is *unique* NPCs by design — a promoted NPC and its pool origin are one entity; counting once is the honest measure. No break survives scrutiny.

**Handoff:** To SM (Morpheus) for finish-story. I did NOT create or merge a PR — SM owns PR creation + merge in the finish phase.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The trickiest part of GREEN is the promoted-NPC dedup, not the projector. A naive union of `npc_pool` + `npcs` double-counts a promoted NPC (same `npc:<slug>` id) and inflates `npc_count`. Affects `sidequest/game/entity_sync.py` (`sync_entity_cards` must dedup by id with **stateful precedence** — the `Npc` wins over its `pool_origin` member — and count each unique NPC once). *Found by TEA during test design.*
- **Improvement** (non-blocking): `project_npc_card` must become polymorphic over `NpcPoolMember | Npc`. The two carry their name differently (`member.name` vs `npc.core.name`) and `Npc` has no `.role`. Affects `sidequest/game/entity_card.py` (extend the projector; keep output deterministic and band-keyed for both sources so the 75-6 reproject still works). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): 7 test failures pre-exist on `develop`, unrelated to 76-6 — proven by stashing the 76-6 implementation and re-running (they fail identically). They block a literal "full suite green" reading of AC4. Affects `tests/agents/test_61_12_output_format_compaction.py::test_output_only_prose_under_byte_budget`, `tests/agents/tools/test_apply_world_patch.py::test_active_stakes_path_applies`, and all 5 in `tests/server/test_narration_clue_discovery_wiring.py` (each needs its own triage — compaction byte-budget, active_stakes apply path, and clue-discovery/known-fact minting respectively). Recommend a separate bug story; 76-6 does not touch these paths. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): A pool member skipped by dedup increments neither `unchanged` nor `npc_count`, so `EntitySyncResult` counts *unique* NPCs (intended/honest) but does not surface how many duplicates were suppressed. Affects `sidequest/game/entity_sync.py` (optional: add a `deduped` counter + span attribute if the GM panel later wants dedup visibility). Not a defect — the unique count is correct. *Found by Reviewer during code review.*
- **Gap** (non-blocking): Confirms Dev's finding — 6 (not 7) pre-existing develop failures unrelated to 76-6 (`apply_world_patch active_stakes` actually passes on this branch). Affects `tests/agents/test_61_12_output_format_compaction.py` + `tests/server/test_narration_clue_discovery_wiring.py` (separate bug story). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **No sync-level failure-count test for an unprojectable stateful Npc**
  - Spec source: `.session/76-6-session.md`, SM Assessment → Scope guardrails ("No Silent Fallbacks on an unprojectable Npc")
  - Spec text: "No Silent Fallbacks on an unprojectable Npc"
  - Implementation: Instead of a sync-level `failed`-count test (as exists for `NpcPoolMember` in the 75-6 suite), the stateful path is covered by `test_creature_core_name_validator_is_the_upstream_guard` (asserts `CreatureCore(name="   ")` raises `ValidationError`) plus `test_minimal_valid_stateful_npc_always_projects`.
  - Rationale: A stateful `Npc` is **structurally always projectable** — `CreatureCore` validates `name` non-blank at construction, and the projector derives id/content from `core.name`. The `_slug` blank-name failure path that exists for `NpcPoolMember` (which has no such validator) is **unreachable** for an `Npc`. Writing a sync test that can never construct its bad fixture would be a vacuous/red-herring test. The No-Silent-Fallbacks intent is enforced one layer up, at the model boundary, and is pinned as a regression guard.
  - Severity: minor
  - Forward impact: Dev's `Npc` projector must derive content from `core.name` (validated non-blank) so projection cannot silently produce a blank-id/blank-content card. If a future `Npc` field that the projector reads is nullable and used unguarded, the unprojectable path could reappear — keep projection keyed on the validated `core.name`.
  → ✓ ACCEPTED by Reviewer: sound. `CreatureCore.name` validator makes a blank-named stateful `Npc` unconstructable; the security subagent independently confirmed the projector keys on `core.name` and no silent stub is possible. Writing a test whose bad fixture cannot be built would be vacuous. The upstream-guard pair (`test_creature_core_name_validator_is_the_upstream_guard` + `test_minimal_valid_stateful_npc_always_projects`) is the correct coverage.

### Reviewer (audit)
- No undocumented spec deviations found. The implementation matches the story scope (stateful `snapshot.npcs` sync, dedup-by-id with stateful precedence, OTEL `npc_count` honesty); factions/locations correctly left out of scope (76-7).