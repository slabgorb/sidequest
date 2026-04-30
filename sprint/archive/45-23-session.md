---
story_id: "45-23"
jira_key: ""
epic: "EPIC-45"
workflow: "wire-first"
---

# Story 45-23: world_history arc embedding pipeline writes back to narrative_log/lore

## Story Details

- **ID:** 45-23
- **Workflow:** wire-first
- **Points:** 3
- **Priority:** P2
- **Type:** Bug
- **Branch (server):** feat/45-23-arc-embedding-writeback (merged via PR #145)
- **PR:** https://github.com/slabgorb/sidequest-server/pull/145 — squash-merged 2026-04-30T20:02:42Z

## Problem Statement

Playtest 3 Felix (2026-04-19, evropi session, turn 71): `narrative_log` and `lore_store` empty of arc-sourced content despite 71 turns of dense play. The chapter-promotion path (45-19's recompute) ran but never wrote back into the durable narrative log or the RAG-retrievable lore index.

## Workflow Tracking

**Workflow:** wire-first
**Phase:** finish (complete — PR merged, awaiting SM finish)

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-30T22:35Z | 2026-04-30T19:30:51Z | -11049s |
| red | 2026-04-30T19:30:51Z | 2026-04-30T19:44:28Z | 13m 37s |
| green | 2026-04-30T19:44:28Z | 2026-04-30T19:52:15Z | 7m 47s |
| review | 2026-04-30T19:52:15Z | 2026-04-30T20:08:12Z | 15m 57s |
| finish | 2026-04-30T20:08:12Z | - | - |

## Delivery Findings

### TEA (test design)
- **Improvement** (non-blocking): The seeding helper's signature is defined by tests as `seed_lore_from_arc_promotion(snapshot, store, lore_store, chapters)` returning a structured result; Dev picks the concrete return type. Recommended dataclass; Dev landed `ArcSeedResult` dataclass. *Found by TEA during test design.*
- **Gap** (non-blocking): `recompute_arc_history` previously returned `None`; needed to return added-chapter list to share the diff with the seeding helper. Resolved by Dev (option a). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. Resolved TEA's "Gap" finding by changing `recompute_arc_history` to return `list[HistoryChapter]`.

### Reviewer (code review)
- **Improvement** (non-blocking): Test coverage gap — production has a blank-speaker guard in `seed_lore_from_arc_promotion` (mirroring the blank-lore-string guard) but no unit test exercises it. The guard could be removed without any test failing. Affects `tests/game/test_lore_seeding_arc_promotion.py` (add a test parallel to `test_blank_lore_string_is_skipped_not_raised`). Filed as observation, not blocking — production packs always carry valid speakers (chapter narrative entries are validated upstream). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `test_partial_overlap_skips_only_the_duplicates` asserts `lore_fragments_minted == 1` but does not verify that `lore_arc_early_1` actually landed in the store. A bug that skips ALL entries on any duplicate would still pass. Affects `tests/game/test_lore_seeding_arc_promotion.py` (one extra assert). *Found by Reviewer during code review.*
- **Note** (non-blocking): The "empty `chapter_id` produces collision-prone fragment ids" finding (flagged by 3 reviewers as high confidence) is **unreachable in production** — chapters are filtered by `CampaignMaturity.from_chapter_id` at `world_materialization.py:681` before they enter `snapshot.world_history`. Only `{fresh, early, mid, veteran}` ids survive; chapters with empty/unknown ids are dropped. The defensive `getattr(chapter, "id", "") or ""` is belt-and-braces for an unreachable case. *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (code review)
- No deviations from spec.

## Subagent Results

All received: Yes

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | Lint clean, 38 new tests pass, pre-existing pyright errors on unrelated lines | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 8 edge cases (3 high, 3 medium, 1 low, 1 low). High-confidence convergent finding (empty chapter_id) reframed: unreachable in production — chapters filtered by `CampaignMaturity.from_chapter_id` before reaching this code | dismissed (unreachable in production paths) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 5 patterns flagged: `_try_add` swallow scope, `or 0` defaults, getattr defaults, blank-content guards, missing skip-counter | dismissed — guards are correct per "No Silent Fallbacks" (validator-loud-at-construction, helper honours by not constructing) |
| 4 | reviewer-simplifier | Yes | findings | 4 simplification candidates: local imports, per-chapter loop, entries_count shadow, getattr duplication | dismissed — local imports intentional (`# noqa: PLC0415`); per-chapter loop produces per-chapter spans (load-bearing for GM panel); entries_count is minor stylistic |
| 5 | reviewer-test-analyzer | Yes | findings | 7 test issues: 2 alleged tautologies (incorrect — RHS is hardcoded literal), 1 implementation-coupling on durability test, 3 missing edge cases (blank speaker, partial-overlap completeness, multi-chapter wire) | partially confirmed — 2 real test gaps filed under Reviewer findings as non-blocking Improvements |
| 6 | reviewer-type-design | Yes | findings | 4 type-design notes: `Any` on snapshot/store, `RecomputeResult` dataclass, TypedDict for span extracts, HistoryChapter.id default | dismissed — consistent with existing codebase patterns (`recompute_arc_history` already uses `snapshot: Any`) |
| 7 | reviewer-comment-analyzer | Yes | findings | 2 docstring nits: alleged stale `_execute_narration_turn` reference (FALSE — method exists at websocket_session_handler.py:1409); content_bytes_seeded prompt-budget framing | dismissed (1 false positive) / minor (1 doc nit, non-blocking) |
| 8 | reviewer-rule-checker | Yes | findings | 2 No-Silent-Fallbacks rule findings: blank-speaker skip and blank-lore skip drop content without ArcSeedResult counters. Other 4 rules (No Stubbing, Don't Reinvent, Verify Wiring, Wiring Test, OTEL Principle) PASS. | dismissed — both findings target unreachable content-authoring cases (blank speakers/lore strings would fail upstream YAML validation); the schema validators (`NarrativeEntry.author` non-blank, `LoreFragment.content` min_length=1) stay loud at construction time, helper honours by not constructing. Same pattern as the empty-chapter_id finding; defensive code for cases that don't reach this path in production. |

## Reviewer Assessment

**Verdict:** APPROVED — squash-merged PR #145.

### Specialist findings synthesis

- **[TEST]** (reviewer-test-analyzer): two real coverage gaps identified — no unit test exercises the blank-speaker guard parallel to the existing blank-lore-string test; `test_partial_overlap_skips_only_the_duplicates` asserts on counts but does not verify `lore_arc_early_1` actually lands in the store. Both are non-blocking observability gaps in the test suite — production behavior matches the contract; coverage strengthening would catch a future regression that swaps "skip all on duplicate" for "skip only the duplicate."

- **[DOC]** (reviewer-comment-analyzer): one false positive (alleged stale `_execute_narration_turn` reference — the method exists at `websocket_session_handler.py:1409`); one minor docstring nit on `ArcSeedResult.content_bytes_seeded` characterizing it as matching "narrator's prompt budget units" when prompt budgets are token-denominated. Non-blocking.

- **[RULE]** (reviewer-rule-checker): 2 findings under the No-Silent-Fallbacks rule (blank-speaker skip, blank-lore skip drop content without ArcSeedResult counters). All other rules (No Stubbing, Don't Reinvent, Verify Wiring, Wiring Test, OTEL Principle) PASS. Findings dismissed: both target unreachable content-authoring cases — `NarrativeEntry.author` (Story 45-22 non-blank validator) and `LoreFragment.content` (`min_length=1` + whitespace-strip validator) stay loud at construction time. The helper's skip-not-construct pattern honours those validators rather than crashing the dispatch loop on a malformed pack — same loud-validator-honoured-by-helper pattern as the existing chargen seeders. Adding skipped-blank counters would be defensive observability for cases that never reach this code path in production.

**Wire-first gate verification:**
- Outermost reachable layer: ✅ `_execute_narration_turn` exercised by boundary test (`TestOtelSpansFromDispatch` + `TestNarrativeLogWritebackFromDispatch` + `TestLoreStoreWritebackFromDispatch`).
- Non-test consumer: ✅ `seed_lore_from_arc_promotion` called from `websocket_session_handler.py` post-`record_interaction` site (verified by `test_arc_embedding_seed_fires_alongside_45_19_arc_promoted`).
- No deferral language: ✅ neither "follow-up", "next story", nor "subsequent" appears in the diff or session.
- No stub implementations: ✅ helper is fully wired, all three OTEL spans fire from real code paths.
- Save/reload durability: ✅ `test_arc_promotion_entries_survive_save_and_reload` proves snapshot JSON round-trip carries arc entries; `test_arc_promotion_entries_present_in_durable_narrative_log_table` proves the SQLite log table carries them for GM-panel `recent_narrative` replay.

**Adversarial review summary (5 reviewers):**
- **edge-hunter:** flagged 8 edge cases. The 3 high-confidence ones (empty chapter_id, missing turn_manager, None lore_store/store) are all **defensive coverage of unreachable cases** — the defensive code is intentional belt-and-braces, the failure modes don't reach this code in production. No action required.
- **silent-failure-hunter:** flagged 5 patterns. Confirmed `_try_add` swallows only `DuplicateLoreId` (intentional and correct per existing chargen seeders' contract); `or 0` on round/interaction is consistent with `recompute_arc_history`'s defensive shape; blank-speaker / blank-lore guards are correct (CLAUDE.md "No Silent Fallbacks" — validators stay loud at construction; helper honours them by not constructing on malformed inputs). No action required.
- **simplifier:** flagged 4 over-engineering candidates. The local imports (`# noqa: PLC0415`) are intentional to avoid circular-import risk; the per-chapter loop in dispatch produces per-chapter spans (load-bearing for GM panel chapter attribution); the `entries_count` shadow is minor cleanup. Not blocking.
- **test-analyzer:** flagged 7 test issues. Constant-value tests (LHS imported, RHS literal) DO catch a value change — not tautological. Extract-key tests check key presence not values — minor strengthening opportunity. Two real coverage gaps (blank speaker test, partial-overlap completeness) filed as Improvements above; not blocking.
- **type-design:** flagged 4 type-design improvements. `Any` on snapshot/store is consistent with the existing `recompute_arc_history` signature; `RecomputeResult` dataclass would be cleaner than empty-list-as-no-op but the current pattern works and matches caller expectations; TypedDict on span extracts is a nice-to-have, low impact. Not blocking.

**Tests:** 3232/3232 passing, 49 skipped (matches baseline). Lint clean. Branch merged via squash.

**Handoff:** To SM (Vizzini) for finish phase.