---
story_id: "71-7"
jira_key: null
epic: "71"
workflow: "tdd"
---

# Story 71-7: Authored chassis crew silently skipped when chapter seeds placeholder PC

## Story Details
- **ID:** 71-7
- **Title:** Authored chassis crew silently skipped when chapter seeds placeholder PC
- **Workflow:** tdd
- **Stack Parent:** none
- **Repo:** sidequest-server
- **Base Branch:** develop

## Problem Summary

The Kestrel's authored crew (Wainu/Hubo/Kuna-Mikkaan/Kanga + matriarch Dura Mendes) from `sidequest-content/genre_packs/space_opera/worlds/coyote_star/npcs.yaml` never hydrate into the live NPC roster at game start. Live session evidence (session_id=76, world coyote_star, 2026-05-27):
- `npcs[]` holds only 7 chapter-authored NPCs (Demiloslava Chop, Troy Goda, Cmdr. Yarya, Virki, Vesper, Ther Path, Deckonone) — the *wrong* cast.
- The real crew (Wainu, Kanga, Kestrel) sits as narrator-invented stubs in `npc_pool` with no disposition/OCEAN/last_seen tracking.
- ZERO `npc.authored_loaded` spans across 999 telemetry rows.

**Downstream symptom:** the crew the player engages for hours has no persistent state backing, so once the narration window rolls past their last mention they evaporate. Violates SOUL "Living World" + "Diamonds and Coal".

## Root Cause (File:Line Pinned)

Ordering/gate bug in the chargen first-commit path:

### `sidequest-server/websocket_handlers/chargen_mixin.py:728-789` (is_first_commit branch)
1. **Line 740:** `materialize_from_genre_pack(history_value, CampaignMaturity.Fresh, ...)` returns a snapshot ALREADY containing:
   - A chapter-authored "Adventurer" placeholder *character*
   - The 7 chapter NPCs (the wrong cast)
2. **Line 786:** `preload_authored_npcs(materialized, world.authored_npcs)` is called
3. **Line 789:** The "Adventurer" placeholder is discarded — but AFTER the preload call

### `sidequest-server/game/world_materialization.py:785-866` (preload_authored_npcs)
- **Gate logic (lines 807-812):** `is_fresh = not state.characters AND turn_manager.interaction == 0`
- **Bug:** Because `materialized.characters` is non-empty (holds the placeholder from `WorldBuilder._apply_chapter`, line 335: `name = char_data.name if char_data.name else "Adventurer"`), `is_fresh` evaluates to False
- **Result:** Silent early `return`. Crew never loads; **no span fires**

## Defects

1. **Wrong-cast/no-hydration bug:** authored crew is not materialized into the live roster
2. **Silent fallback:** The skip emits nothing — both defects are forbidden by CLAUDE.md

## Acceptance Criteria

1. **Fresh chargen crew materialization:** On a fresh `coyote_star` chargen-confirm (first commit), the authored chassis crew (kestrel_captain/engineer/doc/cook = Wainu/Hubo/Kuna-Mikkaan/Kanga) AND Dura Mendes are materialized into `snapshot.npcs` as runtime `Npc` instances carrying their authored `initial_disposition` (60/55/50/60/0 respectively) — NOT left as `npc_pool` narrator_invented stubs.

2. **Fix freshness gate:** `preload_authored_npcs` no longer false-negatives when the materialized snapshot carries only a chapter-authored placeholder character. Fix the ordering or the freshness gate (e.g., gate on `turn_manager.interaction == 0` and absence of a real chargen/player character, or discard the placeholder before the preload call) — do NOT regress resumed-session skip behavior (resumed sessions must still skip preload).

3. **Coexistence:** The chapter-authored NPCs and the authored crew must coexist correctly — the fix must not drop the chapter NPCs nor double-register the crew.

4. **OTEL observability (CLAUDE.md Observability Principle + No Silent Fallbacks):**
   - `npc.authored_loaded` (`SPAN_NPC_AUTHORED_LOADED`) fires once per crew member + Dura Mendes on fresh chargen
   - When `preload_authored_npcs` skips (resumed session OR gate-not-fresh), emit `npc.authored_load_skipped` with a `reason` field so the GM panel never goes blind on a silent no-op

## Test Guidance (TEA Red Phase)

### Fixture-driven behavior test
- Construct a fresh coyote_star-like genre pack + history with a Fresh-tier chapter that seeds a placeholder character
- Drive the chargen first-commit seam through the real handler path
- Assert: authored crew present in `snapshot.npcs` with correct dispositions
- Assert: `npc.authored_loaded` spans fired (use OTEL span assertion)
- Reference canonical shape: `tests/server/test_location_description_emit.py`

### Wiring test
- Assert the preload is reached and the span fires end-to-end through the production chargen path, not just a unit call to `preload_authored_npcs`

### Regression guard
- A resumed session (characters present, interaction>0) still skips preload AND now emits the skip span with reason

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-28T00:53:59Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27T19:45:00Z | 2026-05-27T23:43:18Z | 3h 58m |
| red | 2026-05-27T23:43:18Z | 2026-05-28T00:11:43Z | 28m 25s |
| green | 2026-05-28T00:11:43Z | 2026-05-28T00:19:44Z | 8m 1s |
| spec-check | 2026-05-28T00:19:44Z | 2026-05-28T00:21:18Z | 1m 34s |
| verify | 2026-05-28T00:21:18Z | 2026-05-28T00:26:59Z | 5m 41s |
| review | 2026-05-28T00:26:59Z | 2026-05-28T00:52:12Z | 25m 13s |
| spec-reconcile | 2026-05-28T00:52:12Z | 2026-05-28T00:53:59Z | 1m 47s |
| finish | 2026-05-28T00:53:59Z | - | - |

## Delivery Findings

### TEA (test design)
- **Conflict** (blocking): The pinned root cause in the story context is imprecise — the real trigger is the `TurnManager` interaction baseline, not a chapter-authored placeholder character. Empirically verified during red phase: a fresh `coyote_star` materialization yields `characters == []`, `npcs == []`, and **`turn_manager.interaction == 1`** (a bare `GameSnapshot()` also baselines `interaction == 1`). The gate `is_fresh = not state.characters AND turn_manager.interaction == 0` therefore fails on the `interaction == 0` clause (1 != 0), not on a non-empty `characters` list — coyote_star has no placeholder. Affects `sidequest/game/world_materialization.py` (the `preload_authored_npcs` freshness gate, lines ~807-812 must stop requiring `interaction == 0`; discriminate fresh-vs-resumed by absence of a real player character, since the chargen seam appends the PC *after* preload). The "discard placeholder before the call" fix route from AC2 does NOT fix coyote_star. *Found by TEA during test design.*
- **Improvement** (non-blocking): Pre-existing tests fabricate `interaction=0` (`_StubTurnManager.interaction = 0` in `tests/e2e/test_authored_npcs_preloaded.py`; `MagicMock(interaction=0)` in `tests/game/test_world_materialization_authored_npcs.py`), a value that never occurs in a real fresh session — which is why the bug shipped green. Dev should re-point those fixtures to the real baseline (`interaction == 1`) when fixing, so they stop masking the regression. *Found by TEA during test design.*
- **Improvement** (non-blocking): The `CreatureCore` + `Npc` construction block is duplicated between `_apply_npc` (`sidequest/game/world_materialization.py:~516`) and `preload_authored_npcs` (`:~846`) — ~30 lines of identical boilerplate (HP pool 10/10, level 1, the 13 nullable/default `Npc` fields), differing only in source-field mapping (`ChapterNpc` vs `AuthoredNpc`) and `location`. A `_build_runtime_npc(...)` helper would consolidate it so future HP/advancement changes land in one place. Not applied here: both loci pre-date story 71-7 and `_apply_npc` is outside this story's diff (the chapter-NPC path) — extracting it is a standalone refactor needing its own tests. Affects `sidequest/game/world_materialization.py`. *Found by TEA during test verification.*

### Dev (implementation)
- **Improvement** (non-blocking): `sidequest/game/world_materialization.py` carries 3 pre-existing pyright errors (lines ~502, ~531, ~860) — `int` assigned to the `Disposition`-typed `Npc.disposition` field, which works at runtime via pydantic coercion pyright can't see. Not introduced by this story (verified against HEAD baseline) and left untouched per minimalist discipline. Affects `sidequest/game/world_materialization.py` (a `Disposition`-or-int union on the field, or wrapping at the call sites, would clear them). *Found by Dev during implementation.*
- **Gap** (non-blocking): This story fixes go-forward fresh-chargen hydration only. Already-broken live saves (e.g. session_id=76) keep their narrator-invented crew stubs in `npc_pool`; no migration/backfill is performed (explicitly out of scope per context). Affects existing `~/.sidequest` PG sessions (a one-shot backfill would need its own story). *Found by Dev during implementation.*

### Reviewer (code review)
- No upstream findings during code review. (The two non-blocking Improvements — pyright baseline and the `_build_runtime_npc` duplication — are already captured by Dev/TEA above; I concur with deferring both to standalone work.)

## Design Deviations

### TEA (test design)
- **Tested the chargen seam via its two production functions in order, not by driving the full async `_chargen_confirmation` handler**
  - Spec source: context-story-71-7.md, "Test Guidance — Wiring test"
  - Spec text: "Drive the chargen first-commit seam through the real handler path."
  - Implementation: The wiring test (`tests/e2e/test_71_7_chargen_crew_wiring.py`) replays the exact production sequence — `materialize_from_genre_pack(...)` then `preload_authored_npcs(...)` against real shipping coyote_star content — rather than invoking `CharGenMixin._chargen_confirmation`, which is a large async method requiring a built `CharacterBuilder`, full `_SessionData`, fake websocket, and span. The codebase itself skips driving this e2e (`test_chargen_complete_resolves_opening.py` is a `pytest.skip`).
  - Rationale: Driving the full handler needs disproportionate harness for no added coverage of THIS defect — the bug lives entirely in the materialize→preload seam, which the integration test reproduces faithfully with real content. Unit tests pin the gate contract deterministically.
  - Severity: minor
  - Forward impact: minor — if Dev fixes by reordering *inside* `_chargen_confirmation` rather than correcting the freshness gate, the wiring test (which calls the functions directly) would not exercise that reorder. But see Delivery Findings: the corrected root cause (interaction baseline == 1, no placeholder for coyote_star) means the gate itself must change — the reorder route does not fix coyote_star.
- **Declined a high-confidence simplify-reuse finding rather than auto-applying it (verify phase)**
  - Spec source: tea agent verify-workflow, Step 5 ("For each finding with confidence: high: apply the suggestion")
  - Spec text: "For each finding with `confidence: high`: 1. Read the file 2. Apply the suggestion 3. Track what was changed."
  - Implementation: Did NOT apply the high-confidence reuse finding (extract `_build_runtime_npc` to deduplicate `_apply_npc` ↔ `preload_authored_npcs` Npc construction). Logged it as a non-blocking Improvement delivery finding instead.
  - Rationale: The finding's primary locus (`_apply_npc`, line ~516) is pre-existing code outside this story's diff; both construction blocks pre-date 71-7. Applying the helper extraction would pull the untouched chapter-NPC path into a focused bugfix and risks regression (the two sites differ on `location` handling). TEA triage judgment (per delegation: "Triage findings by confidence level… Revert if regression detected") overrides mechanical application when the fix exceeds story scope.
  - Severity: minor
  - Forward impact: none for 71-7 — duplication is unchanged from base; flagged for a future standalone refactor story with its own coverage.

### Dev (implementation)
- **Fixed the freshness gate by dropping the `interaction` clause, not by handling a placeholder character**
  - Spec source: context-story-71-7.md, AC-2
  - Spec text: "Fix the ordering or the freshness gate (e.g., gate on `turn_manager.interaction == 0` and absence of a real chargen/player character, or discard the placeholder before the preload call)."
  - Implementation: Changed `preload_authored_npcs`'s gate from `not characters AND interaction == 0` to keying solely on the absence of a seated player character (`not state.characters`); the `interaction` clause was removed entirely.
  - Rationale: Per Radar's blocking Delivery Finding (empirically verified), a real fresh snapshot baselines at `interaction == 1`, never 0 — and coyote_star seeds NO placeholder character. Both the "placeholder" framing and any "discard placeholder" route are inapplicable; the only defect is the unsatisfiable `interaction == 0` clause. The sole caller (chargen first-commit) appends the PC *after* preload, so `not characters` is the exact, sufficient fresh signal.
  - Severity: minor
  - Forward impact: none — go-forward chargen behavior only; resumed sessions still skip (now observably, via `npc.authored_load_skipped`). A future world whose history chapter seeds a placeholder *character* would re-trip `not characters` (out of scope per context Assumptions; new story if it appears).

### Reviewer (audit)
- **TEA: "Tested the seam via its two functions, not the full async handler"** → ✓ ACCEPTED by Reviewer: sound — driving `_chargen_confirmation` needs disproportionate harness (the codebase itself `pytest.skip`s that e2e), and the integration test reproduces the exact production sequence against real coyote_star content. The corrected root cause (gate, not reorder) makes the direct-call wiring faithful.
- **TEA: "Declined the high-confidence simplify-reuse finding"** → ✓ ACCEPTED by Reviewer: correct triage — the `_build_runtime_npc` extraction touches `_apply_npc` (the chapter-NPC path), which is outside this story's diff and pre-dates it. Refactoring it here would broaden a focused bugfix and risk the `location`-handling difference. Proper to defer with its own tests.
- **Dev: "Fixed the gate by dropping the `interaction` clause, not handling a placeholder"** → ✓ ACCEPTED by Reviewer: agrees with author reasoning and the Architect's Option-A spec update — the `interaction == 0` clause was unsatisfiable (baseline is 1) and coyote_star has no placeholder, so `not characters` is the exact fresh signal. Endorsed.
- No undocumented deviations found: the diff matches the logged deviations; nothing slipped through.

### Architect (reconcile)

Verification of existing entries: TEA (test design) ×2, Dev (implementation) ×1 — all carry the full 6 fields, quoted spec text is accurate against `sprint/context/context-story-71-7.md` (TEA#1 quote at context line 146; Dev#1 AC-2 quote at context lines 124-129), and the implementation descriptions match the diff. Reviewer (audit) stamped all three ✓ ACCEPTED. No epic context exists (`sprint/context/context-epic-71.md` absent); story context is the governing spec. No ACs were deferred — AC-deferral verification is a no-op.

Two deviations the in-flight logs implied but did not formally record, added here for manifest completeness:

- **Replaced/repurposed a pre-existing test and re-pointed two fixtures rather than leaving them untouched**
  - Spec source: context-story-71-7.md, "Scope Boundaries → Out of scope"
  - Spec text: "Redesigning the chargen flow, the `WorldBuilder._apply_chapter` placeholder mechanism, or the authored-NPC YAML schema." (the out-of-scope list does not mention pre-existing tests)
  - Implementation: `test_past_turn_zero_skips_preload` (which asserted skip on no-characters + `interaction=5`) was removed and replaced with `test_interaction_count_does_not_gate_preload` (asserts load); `_StubTurnManager.interaction` (test_authored_npcs_preloaded.py) and the `MagicMock(interaction=...)` fixtures (test_world_materialization_authored_npcs.py) were re-pointed from the fabricated `0` to the real baseline `1`.
  - Rationale: those tests encoded the buggy contract (interaction as a freshness gate). After the corrected gate, the old assertions were false; leaving them would have failed green. TEA flagged this as a non-blocking Improvement and Dev documented it in the assessment — formalized here so the audit shows a pre-existing test was intentionally changed, not silently broken.
  - Severity: minor
  - Forward impact: none — the replacement test is a 71-7 regression guard; no sibling story depends on the removed assertion.

- **AC4's skip-span requirement was interpreted to exclude the empty-`authored` early return**
  - Spec source: context-story-71-7.md, AC-4
  - Spec text: "When `preload_authored_npcs` skips (resumed session OR gate-not-fresh), emit `npc.authored_load_skipped` with a `reason` field so the GM panel never goes blind on a silent no-op."
  - Implementation: the `if not authored: return` early path emits no span; only the resumed-session (characters-present) skip emits `npc.authored_load_skipped`.
  - Rationale: AC4 scopes the skip span to "resumed session OR gate-not-fresh." Empty `authored` is neither — it is "nothing to load," not a suppressed decision; a world with zero authored NPCs legitimately loads nothing, and authored-list validation is the loader's responsibility, not this seam's. Reviewer ([SEC] + assessment) and the security subagent both judged this compliant, not a silent fallback. This is a spec clarification (spec-check Option C), recorded so a future auditor sees the empty-authored silence is intentional.
  - Severity: trivial
  - Forward impact: none — observable behavior is unchanged for any world that ships authored NPCs.

## Technical Notes

### Files to Modify
- `sidequest/websocket_handlers/chargen_mixin.py` — chargen first-commit handler
- `sidequest/game/world_materialization.py` — `preload_authored_npcs` freshness gate and skip span
- `sidequest/telemetry/span_definitions.py` — add `SPAN_NPC_AUTHORED_LOAD_SKIPPED` definition (or reuse existing skip span)

### Current Behavior (Broken)
1. Chargen commit materializes a fresh world with chapter NPCs + "Adventurer" placeholder
2. `preload_authored_npcs` sees non-empty `state.characters`, skips silently
3. Authored crew never loads; zero observability

### Fixed Behavior (Expected)
1. Chargen commit materializes a fresh world
2. Placeholder character is identified and excluded from the freshness gate
3. `preload_authored_npcs` correctly detects fresh state and loads authored crew
4. Authored crew members appear in `snapshot.npcs` with correct dispositions
5. `npc.authored_loaded` spans fire for each crew member
6. Skip scenarios emit `npc.authored_load_skipped` with reason

## Sm Assessment

**Setup complete.** Story 71-7 created under epic 71 (coyote_star MP playtest bugfix), branch `feat/71-7-authored-crew-hydration` on sidequest-server (base: develop). Status → in_progress.

**Provenance:** Diagnosed by GM (live save audit) then root-caused by Dev (Winchester) against a live PostgreSQL reproduction — session_id=76, world coyote_star, 2026-05-27. The defect reproduces on HEAD; this is not a stale-save artifact. Root cause is pinned to file:line in the story context (chargen_mixin.py:728-789 ordering + preload_authored_npcs freshness gate at world_materialization.py:807-812).

**Why p1 / bug / tdd:** Load-bearing SOUL failure (Living World + Diamonds and Coal) — the crew the player engages for hours has no persistent state, producing the "forget-the-NPCs" symptom. Compounded by a silent fallback (skip emits no span), which CLAUDE.md forbids. Small surgical fix but carries an OTEL observability requirement and a wiring assertion, so TDD is the right theatre.

**Scope guard for the pipeline:** four ACs in the context. Do not let the fix drop chapter-authored NPCs or double-register the crew, and do not regress resumed-session skip behavior — the skip path must now emit a reason span rather than no-op.

**Handoff:** To Radar (TEA) for the red phase — write the failing fixture-driven behavior test + OTEL span assertions per the test guidance.
## TEA Assessment

**Tests Required:** Yes

**Test Files:**
- `sidequest-server/tests/game/test_71_7_authored_crew_fresh_gate.py` — deterministic gate-contract + span tests (6 tests)
- `sidequest-server/tests/e2e/test_71_7_chargen_crew_wiring.py` — wiring against real shipping coyote_star content (3 tests)

**Tests Written:** 9 tests covering all 4 ACs. **Status:** RED (2 behavior-anchor tests pass; 6 fail on assertions proving the bug; verified no collection/import/fixture errors).

RED breakdown:
- AC1/AC2 crew hydration: `test_preload_loads_crew_on_real_fresh_snapshot`, `test_chargen_seam_loads_authored_crew_into_npcs` — FAIL (crew not loaded).
- AC3 coexistence: `test_chapter_npcs_and_crew_coexist_without_duplicates` — FAIL (crew not added).
- AC4 load spans: `test_preload_emits_authored_loaded_span_per_crew_on_fresh`, `test_chargen_seam_emits_authored_loaded_span_per_crew` — FAIL (0 spans).
- AC4 skip span / No Silent Fallbacks: `test_resumed_session_still_skips_but_emits_reason_span` — FAIL (no `npc.authored_load_skipped` span).
- Anchors (PASS, by design): `test_fresh_snapshot_default_interaction_is_one_not_zero`, `test_coyote_star_fresh_precondition_interaction_is_one` — pin the corrected root cause (real fresh interaction baseline == 1).

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|---|---|---|
| #1 Silent exception/fallback swallowing | `test_resumed_session_still_skips_but_emits_reason_span` (skip path must emit a `reason` span — No Silent Fallbacks) | failing |
| #6 Test quality (meaningful assertions) | Self-check: all assertions check specific values — dict-equality on dispositions, exact span counts, name membership, non-empty `reason`. No `assert True`, no truthy-on-always-None. | pass |
| OTEL Observability Principle (CLAUDE.md) | both `*_emits_authored_loaded_span_*` + skip-span test | failing |
| No source-text wiring tests (CLAUDE.md) | Wiring proven via `Span.open` assertions + real-content fixture behavior, not source grep | pass |

**Rules checked:** Applicable lang-review rules for this seam (#1, #6) have coverage; #14 (state-cleanup ordering) is thematically adjacent but the corrected root cause (gate predicate, not ordering) makes it non-applicable.
**Self-check:** 0 vacuous tests found in new files.

**Handoff:** To Dev (Major Winchester) for implementation. Read the Delivery Findings first — the root cause is the `interaction == 0` gate clause (real fresh baseline is 1), NOT a placeholder character; discriminate fresh-vs-resumed by absence of a real player character.
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/world_materialization.py` — `preload_authored_npcs` freshness gate now keys on absence of a seated player character (`not state.characters`); dropped the unsatisfiable `interaction == 0` clause. Resumed-session skip now emits `npc.authored_load_skipped` with a `reason`.
- `sidequest/telemetry/spans/opening.py` — added `SPAN_NPC_AUTHORED_LOAD_SKIPPED = "npc.authored_load_skipped"`, registered in `FLAT_ONLY_SPANS`.
- `tests/game/test_71_7_authored_crew_fresh_gate.py`, `tests/e2e/test_71_7_chargen_crew_wiring.py` — TEA's red tests (fixture corrected to read `disposition.value`).
- `tests/game/test_world_materialization_authored_npcs.py`, `tests/e2e/test_authored_npcs_preloaded.py` — re-pointed fabricated `interaction=0` fixtures to the real baseline (1); replaced the fictional `test_past_turn_zero_skips_preload` with `test_interaction_count_does_not_gate_preload` (71-7 regression guard).

**Tests:** 31/31 passing (GREEN) — 13 in the story + modified suites, 18 in the chargen/opening regression sweep (7 pre-existing skips). 0 failures.

**Quality gates:** ruff check clean, ruff format clean. Pyright: 3 errors, all pre-existing baseline (verified against HEAD) — none introduced by this change.

**AC coverage:** AC1 (crew hydrates on fresh chargen, real-content wiring) ✓ · AC2 (gate fixed, resumed still skips) ✓ · AC3 (chapter NPCs + crew coexist, no dupes) ✓ · AC4 (`npc.authored_loaded` per crew + `npc.authored_load_skipped` with reason) ✓.

**Branch:** feat/71-7-authored-crew-hydration (pushed to origin)

**Handoff:** To Colonel Potter (Reviewer) for review.
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (one minor spec-framing drift, already logged)
**Mismatches Found:** 1

- **Gate keys on `not characters` alone; spec framed it around a placeholder character + `interaction == 0`** (Ambiguous spec — Behavioral, Minor)
  - Spec: AC2 framed the trigger as a chapter-authored placeholder character and offered "gate on `turn_manager.interaction == 0` and absence of a real chargen/player character, or discard the placeholder before the preload call."
  - Code: `preload_authored_npcs` gates solely on the absence of a seated player character (`not state.characters`); the `interaction` clause is removed entirely.
  - Recommendation: **A — Update spec.** The spec's placeholder/interaction framing rested on an inaccurate root cause; TEA empirically verified (blocking Conflict finding) that a real fresh snapshot baselines at `interaction == 1` and coyote_star seeds no placeholder, so the code's approach is the correct one. Already captured under `### Dev (implementation)` in Design Deviations — traceable, no further action.

**Structural integrity verified:** Exactly one production caller (`chargen_mixin.py:786`), which seats the PC at line 789 *after* preload — so `not state.characters` is the exact, sufficient fresh discriminator at that seam. No other call site depends on the dropped `interaction` clause.

**Notes (non-blocking, not mismatches):**
- The preload appends crew without name-dedup against chapter NPCs; in production the name sets are disjoint (Wainu/Hubo/… vs Demiloslava/Yarya/…), so AC3 holds. A same-name collision is a theoretical edge outside this story's scope.
- 3 pre-existing pyright errors on `Disposition`/`int` (already noted by Dev) are baseline, not introduced here.

**Decision:** Proceed to review (via TEA verify).
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (13/13 in the story + modified suites, 0 failures, re-run at verify)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (2 source, 4 test — the full 71-7 diff vs `develop`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding (high) | `CreatureCore`+`Npc` construction duplicated between `_apply_npc` and `preload_authored_npcs` |
| simplify-quality | clean | naming/layering/error-handling/type-safety sound; fixtures use real baseline |
| simplify-efficiency | clean | complexity load-bearing (defensive Npc construction, required OTEL spans, duck-typed getattr) |

**Applied:** 0 high-confidence fixes.
**Flagged for Review:** 1 (the reuse duplication — declined as out-of-scope; see Design Deviations + Delivery Findings).
**Noted:** 0 low-confidence.
**Reverted:** 0.

**Overall:** simplify: clean (1 valid finding flagged, not applied — pre-existing duplication outside the story diff; extracting `_build_runtime_npc` touches the untouched `_apply_npc` chapter-NPC path and belongs in a standalone refactor).

**Quality Checks:** Story + modified + regression suites GREEN. ruff/format clean (per Dev). 3 pre-existing pyright baseline errors unchanged (not introduced).

**Handoff:** To Colonel Potter (Reviewer) for code review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (13 tests GREEN, ruff clean, 0 new pyright, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 enabled returned, both clean; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred (from subagents). Disabled-domain analysis performed by Reviewer directly (below).

## Reviewer Assessment

**Verdict:** APPROVED

The diff is small (2 source files, +57/-23), surgical, and matches the corrected root cause exactly. The two enabled subagents (preflight, security) returned clean. Seven subagents are disabled via project settings — I covered their domains directly below rather than claim coverage I don't have.

**Data flow traced:** `state` (internal `GameSnapshot`) + `authored` (`list[AuthoredNpc]` pre-parsed from pack YAML by the genre loader) → the gate `if getattr(state, "characters", None)` → either the skip span or the Npc-construction loop. No user-controlled / WebSocket / HTTP input reaches this branch; the sole caller is `chargen_mixin.py:_chargen_confirmation` (line 786). Safe.

**Load-bearing sequencing (preflight flagged this):** [VERIFIED] The fresh-vs-resumed discriminator depends on the PC being seated *after* preload — `chargen_mixin.py:786` calls `preload_authored_npcs(materialized, ...)`, then `:789` `materialized.characters = [character]`. Evidence: confirmed both line numbers on-branch. So at preload time a fresh snapshot's `characters` is genuinely empty; a resumed snapshot (loaded from save) always carries a PC. The discriminator is exact.

**Observations (≥5):**
- [VERIFIED] Gate correctness — `world_materialization.py:825` `if getattr(state, "characters", None): return` (skip). The old `interaction == 0` conjunction was unsatisfiable (TurnManager baselines interaction at 1; anchored by `test_fresh_snapshot_default_interaction_is_one_not_zero`). Dropping it is the fix, not a regression.
- [VERIFIED] No silent fallback (CLAUDE.md / python rule #1) — the resumed skip emits `npc.authored_load_skipped` with a `reason` before returning (`:826-836`). The remaining silent return is the empty-`authored` no-op (`:814`), which is genuinely nothing to load and is documented in the docstring — not a masked config problem (the loader owns authored-list validation). Compliant.
- [VERIFIED] OTEL observability (CLAUDE.md) — load path emits `npc.authored_loaded` per NPC; skip path emits the new span. New constant `SPAN_NPC_AUTHORED_LOAD_SKIPPED` is registered in `FLAT_ONLY_SPANS` (`opening.py:38`), so the GM-panel fan-out picks it up. [SEC]-confirmed: span attrs (`reason`, `authored_count`, `genre_slug`, `world_slug`) are world-authored static metadata — no PII/secrets.
- [VERIFIED] AC3 coexistence — the loop appends crew to `state.npcs`; pre-existing entries are untouched. Test `test_chapter_npcs_and_crew_coexist_without_duplicates` proves chapter NPCs survive and no dup names arise. Preload runs once (first commit only), so no double-registration.
- [MEDIUM→noted] No name-dedup between chapter NPCs and crew. In production the name sets are disjoint (Demiloslava/Yarya… vs Wainu/Hubo…), and the loop is unchanged from base, so this is pre-existing behavior outside the story's surface. Not a blocker; a same-name world would need its own handling.
- [VERIFIED] Import hygiene (python rule #10) — span constants are lazily imported inside the function (`:817-821`), a pre-existing pattern that avoids the session→world_materialization circular import. Correct.
- [VERIFIED] Defensive access — `getattr(state, "characters", None)` and `getattr(state, "genre_slug", "") or ""` are safe given `state: Any`; absent attrs degrade to load/empty-string, no crash.

### Rule Compliance (python lang-review)
- **#1 Silent swallowing:** Compliant — skip path observable; empty-authored no-op documented/intentional.
- **#2 Mutable defaults:** N/A — no new defaults.
- **#3 Type annotations at boundaries:** Compliant — `preload_authored_npcs(state: Any, authored: list[AuthoredNpc]) -> None` annotated (pre-existing).
- **#4 Logging coverage/correctness:** Compliant — observability via OTEL spans (project idiom), no logger misuse, no sensitive data.
- **#6 Test quality:** Compliant — tests assert specific values (dict-equality on dispositions, exact span counts, non-empty reason); verified across TEA red + Dev green.
- **#8 Unsafe deserialization:** N/A — no pickle/yaml.load/eval/exec.
- **#10 Import hygiene:** Compliant — lazy import avoids circular dep; no star imports added in source.
- **#11 Input validation at boundaries:** N/A — no user-input boundary opened.
- **#13 Fix-introduced regressions:** None — diff confined to the gate + span; regression sweep GREEN.
- **#14 State-cleanup ordering:** N/A — no consume-then-clear queue/buffer in the change.

### Devil's Advocate
Let me argue this code is broken. **Claim 1: the gate is now too permissive — it loads crew for ANY characterless snapshot, even mid-game.** Could a resumed session ever present with `characters == []`? Only if a save were corrupted/emptied — but then `preload` re-adding authored crew is benign repair, not harm, and a characterless mid-game state is already unplayable. The real call site only invokes preload at first-commit, so this is theoretical. **Claim 2: the empty-`authored` silent return masks a loader bug.** If a world *should* have authored NPCs but the loader silently returned `[]`, this function hides it. True — but that's the loader's validation responsibility, not this seam's; this function cannot distinguish "legitimately zero" from "erroneously zero," and inventing a span for an empty list would fire on every authored-NPC-free world (noise). Correct boundary. **Claim 3: the skip span fires on every resumed turn's chargen path — span spam.** No: preload is only called inside the `is_first_commit` branch (`chargen_mixin.py:728`), which a resumed session never enters, so the skip span fires at most rarely (e.g., a second chargen attempt). **Claim 4: dropping `interaction` loses a safety signal.** It was never a signal — it was always 1, never 0; it gated nothing correctly. **Claim 5: a malicious player can't reach this** — input is internal `GameSnapshot` + pack YAML, no player-controlled path. **Claim 6: race condition?** Chargen first-commit is single-threaded per session; no concurrency on `state.npcs` here. The devil finds only the pre-existing name-dedup gap and the (correct) empty-authored no-op — neither blocks.

**Pattern observed:** Gate-on-true-invariant (absence of seated PC) replacing a gate-on-fabricated-constant (`interaction == 0`) — a textbook "test the real precondition" fix, at `world_materialization.py:825`.
**Error handling:** Defensive `getattr` with safe defaults; no exceptions introduced; failure modes degrade to load-or-skip, never crash.
**Handoff:** To SM for finish-story.